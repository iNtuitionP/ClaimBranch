"""A mixed research workspace returns together without accepting its writing."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import JudgmentRecovery, snapshot, snapshot_value, restore
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.core.canonical import ContractError, MAX_BYTES, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example


SOURCE = b'% Cafe\xcc\x81\r\n% claimbranch:start id=anchor\nOriginal.\n% claimbranch:end id=anchor\n'


class IntegratedRecoveryTests(unittest.TestCase):
    def setUp(self):
        completed = replay_example('recorded', series=True)
        self.history = ResearchHistory.replay(completed.seed, completed.commands[:-1])
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.app.select('obs-1')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.source = Path(self.folder.name) / 'source.tex'
        self.source.write_bytes(SOURCE)
        self.owner = self.app.context_key()
        self.app.keep_draft('측정한 조건에서만 판단한다.', '다른 조건은 아직 측정하지 않았다.')
        self.app.keep_note('개인 노트 / 판단과 구별')
        candidates = self.app.review.candidates()
        self.claim = candidates.create('claim', {'role': 'main', 'parent_ids': ['thesis'],
            'statement': '새 조건은 아직 비교하지 않았다.', 'scope': 'One measured split'})
        self.edge = candidates.create('scientific-edge', {'source_id': 'obs-1', 'target_id': self.claim,
            'edge_type': 'qualifies', 'rationale': '이 관찰은 측정한 조건에만 해당한다.'})
        candidates.toggle(self.edge)
        unfinished = deepcopy(candidates.records[self.claim])
        unfinished['body']['statement'] = ''
        self.app.review.candidate_inputs[self.owner] = {self.claim: unfinished}
        self.result = self.app.intake.create(self.owner)
        self.app.intake.keep(self.result, 'observation', '새 결과 / 미확인')
        self.app.intake.keep(self.result, 'source_ref', 'ssh://synthetic-host/result.csv')
        self.app.intake.keep(self.result, 'judgment', '아직 잠정적인 해석')
        self.app.intake.retain(self.result, 'judgment', '')
        self.app.unfinished[(*self.owner, 'note')] = ['다음에 확인할 조건']
        items = self.app.service.pending_work()['items']
        self.explanation = next(x['id'] for x in items if x['kind'] == 'understanding')
        explanation = self.app.understanding.open(self.explanation)
        self.topic = explanation.state()['topics'][0]['id']
        explanation.edit(self.topic, '원래 판단을 설명하는 글', reuse_rationale=True)
        self.app.understanding.buffers[self.explanation, self.topic] = ''
        self.wording = next(x['id'] for x in items if x['kind'] == 'manuscript')
        manuscript = self.app.manuscript.open(self.wording)
        self.app.manuscript.load_source(str(self.source))
        manuscript.draft.edit('Measured conditions only.', '다른 조건을 일반화하지 않는다.')
        self.app.manuscript.buffers[self.wording, 'wording'] = ['', '아직 작성 중인 이유']
        self.app.manuscript.positions[self.wording, 'wording'] = 1

    def assert_return(self, work, *, note='개인 노트 / 판단과 구별'):
        app = TerminalWorkspace(work.history, ai_off=True)
        # Opening saved writing must not read its supplied manuscript file.
        with patch('claimbranch.application.tui_manuscript.read_source', side_effect=AssertionError('file read')):
            restore(app, work)
        self.assertEqual(snapshot_value(self.app), snapshot_value(app))
        self.assertIsNot(self.history, app.paper.history)
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())
        self.assertEqual(note, app.note())
        self.assertEqual({'text': '측정한 조건에서만 판단한다.', 'rationale': '다른 조건은 아직 측정하지 않았다.'}, app.draft())
        self.assertEqual(['다음에 확인할 조건'], app.unfinished[(*self.owner, 'note')])
        self.assertEqual('새 결과 / 미확인', app.intake.get(self.result)['kept']['observation'])
        self.assertEqual('ssh://synthetic-host/result.csv', app.intake.get(self.result)['kept']['source_ref'])
        self.assertEqual('아직 잠정적인 해석', app.intake.get(self.result)['kept']['judgment'])
        self.assertEqual('', app.intake.get(self.result)['unfinished']['judgment'])
        self.assertEqual('', app.review.candidate_inputs[self.owner][self.claim]['body']['statement'])
        self.assertNotIn(self.edge, app.review.candidates().selected)
        self.assertEqual(SOURCE, app.manuscript.sessions[self.wording]._source)
        wording = app.manuscript.sessions[self.wording].draft.state()['draft']
        self.assertEqual('Measured conditions only.', wording['text'])
        self.assertEqual('다른 조건을 일반화하지 않는다.', wording['rationale'])
        self.assertEqual(['', '아직 작성 중인 이유'], app.manuscript.buffers[self.wording, 'wording'])
        self.assertEqual(1, app.manuscript.positions[self.wording, 'wording'])
        self.assertIsNone(app.manuscript.sessions[self.wording].get_review())
        explanation = app.understanding.sessions[self.explanation].state()
        entry = next(x for x in decode(app.understanding.sessions[self.explanation].snapshot())['entries']
                     if x['topic_id'] == self.topic)
        self.assertEqual('원래 판단을 설명하는 글', entry['text'])
        self.assertTrue(entry['reuse_rationale'])
        self.assertEqual('', app.understanding.buffers[self.explanation, self.topic])
        self.assertTrue(self.app.understanding.sessions[self.explanation].state()['source_ai_influenced'])
        self.assertTrue(explanation['source_ai_influenced'])
        self.assertFalse(explanation['closure_available'])
        self.assertFalse(explanation['authorization_verified'])
        self.assertIsNone(app.review.session().state()['changes_review'])
        self.assertFalse(app.paper.ai_available)
        return app

    def test_all_writing_returns_in_a_fresh_process_with_missing_source(self):
        work = snapshot(self.app)
        self.source.unlink()
        restored = self.assert_return(work)
        restored.understanding.buffers[self.explanation, self.topic] = 'Only this restored copy'
        self.assertEqual('', self.app.understanding.buffers[self.explanation, self.topic])
        script = '''import sys
sys.path.insert(0, sys.argv[1])
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import restore, snapshot_value
from claimbranch.core.canonical import canonical_bytes
work = PaperWork(sys.stdin.buffer.read())
app = TerminalWorkspace(work.history, ai_off=True)
restore(app, work)
sys.stdout.buffer.write(canonical_bytes(snapshot_value(app)))
'''
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([sys.executable, '-I', '-c', script, str(root)],
                                input=work.payload, capture_output=True, cwd=root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(canonical_bytes(snapshot_value(self.app)), result.stdout)

    def test_invalid_last_layer_cannot_install_earlier_valid_writing(self):
        work = snapshot(self.app)
        broken = decode(work.payload)
        broken['workspace']['manuscript']['sessions'][0]['source_digest'] = '0' * 64
        with self.assertRaisesRegex(ContractError, 'Original manuscript source is unavailable'):
            PaperWork(canonical_bytes(broken))
        # Even an in-process forged wrapper must validate every layer before install.
        from types import SimpleNamespace
        target = TerminalWorkspace(self.history, ai_off=True)
        before = snapshot_value(target)
        objects = {name: getattr(target, name) for name in ('paper', 'service', 'manuscript', 'understanding',
                   'intake', 'review', 'notes', 'drafts', 'unfinished', 'recovery')}
        message = target.message
        with self.assertRaisesRegex(ContractError, 'Original manuscript source is unavailable'):
            restore(target, SimpleNamespace(history=self.history, payload=canonical_bytes(broken)))
        self.assertEqual(before, snapshot_value(target))
        for name, value in objects.items():
            self.assertIs(value, getattr(target, name))
        self.assertEqual(message, target.message)
        self.assert_return(work)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work encryption required')
    def test_injected_seal_failure_and_oversize_preserve_native_checkpoint(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        directory = Path(self.folder.name) / 'work'
        directory.mkdir(mode=0o700)
        with MacWorkCipher() as cipher:
            with DevicePaperWorkStore.create(directory, cipher=cipher,
                    project_id=self.app.view['project_id'], recovery_key=os.urandom(32)) as store:
                recovery = JudgmentRecovery(store, self.app)
                from claimbranch.application.tui import Terminal
                self.app.recovery = recovery
                terminal = Terminal.__new__(Terminal)
                terminal.app, terminal.modal, terminal.buffers = self.app, None, []
                recovery.save(self.app)
                original = store.load().payload
                ciphertext = (directory / 'work.cbw').read_bytes()
                before = snapshot_value(self.app)
                self.assertIsNone(getattr(self.app, 'recovery_error', None))
                self.app.keep_note('새로 작성한 노트 / 저장 실패해도 유지')
                live = deepcopy(snapshot_value(self.app))
                with patch.object(cipher, 'seal_device_work', side_effect=ContractError('synthetic encryption failure')) as sealing:
                    self.assertFalse(terminal.checkpoint())
                sealing.assert_called_once()
                self.assertIn('synthetic encryption failure', self.app.recovery_error)
                self.assertEqual(live, snapshot_value(self.app))
                self.assertIn('not confirmed', self.app.recovery_error)
                self.assertEqual('새로 작성한 노트 / 저장 실패해도 유지', self.app.note())
                self.assertEqual(original, store.load().payload)
                self.assertEqual(ciphertext, (directory / 'work.cbw').read_bytes())
                self.assertEqual({'work.cbw', 'work.lock'}, {p.name for p in directory.iterdir()})
                for episode in self.history.episodes():
                    for ref in ('main', 'alternative'):
                        for node in self.app.service.query(ref, episode_id=episode['id'])['nodes']:
                            self.app.notes[episode['id'], ref, node['id']] = 'x' * 12000
                live = deepcopy(snapshot_value(self.app))
                encoded = json.dumps(live, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                self.assertGreater(len(encoded), MAX_BYTES)
                with patch.object(cipher, 'seal_device_work', wraps=cipher.seal_device_work) as sealing:
                    self.assertFalse(terminal.checkpoint())
                sealing.assert_not_called()
                self.assertIn('not saved', self.app.recovery_error)
                self.assertIn('canonical JSON byte limit exceeded', self.app.recovery_error)
                self.assertEqual(live, snapshot_value(self.app))
                self.assertEqual(original, store.load().payload)
                self.assertEqual(ciphertext, (directory / 'work.cbw').read_bytes())
                self.assertEqual({'work.cbw', 'work.lock'}, {p.name for p in directory.iterdir()})
                # Return to the last saved writing for a complete independent comparison.
                self.app.notes = {tuple(x['owner']): x['text'] for x in before['notes']}
                self.assertEqual(before, snapshot_value(self.app))
                self.assert_return(store.load())
                self.app.keep_note('Shortened note after refused save')
                self.assertTrue(terminal.checkpoint(), self.app.recovery_error)
                self.assertIsNone(self.app.recovery_error)
                self.assertNotEqual(ciphertext, (directory / 'work.cbw').read_bytes())
                self.assert_return(store.load(), note='Shortened note after refused save')
        self.assertEqual(SOURCE, self.source.read_bytes())
