"""One AI-off PTY authoring journey returns together; no accepted writes."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

from tests.application import test_tui_terminal as terminal_helpers


@unittest.skipUnless(terminal_helpers.SUPPORTED and sys.platform == 'darwin',
                     'requires a Mac device work key and Unix PTY')
class MixedTerminalRecoveryTests(unittest.TestCase):
    setUp = terminal_helpers.TerminalProcessTests.setUp
    tearDown = terminal_helpers.TerminalProcessTests.tearDown
    resize = terminal_helpers.TerminalProcessTests.resize
    launch = terminal_helpers.TerminalProcessTests.launch
    expect = terminal_helpers.TerminalProcessTests.expect
    send = terminal_helpers.TerminalProcessTests.send
    assert_restored = terminal_helpers.TerminalProcessTests.assert_restored

    def action(self, index, heading):
        self.send(';', 'ACTIONS /')
        self.send('\x1b[B' * index + '\r', heading)

    def paste(self, text, heading):
        self.send('\x1b[200~' + text + '\x1b[201~\x13', heading)

    def back(self, *headings):
        for heading in headings:
            self.send('\x1b', heading)  # Each parent heading differs from the editor.
            self.send('\x0c', heading)

    def assert_clean_exit_output(self):
        for message in (b'Traceback', b'Exception ignored', b'DRAFT SAVE FAILED',
                        b'Writing checkpoint not saved', b'Writing save not confirmed',
                        b'Saving is blocked'):
            self.assertNotIn(message, self.output)

    def assert_manual_payload(self, work):
        from claimbranch.core.canonical import decode
        workspace = decode(work.payload)['workspace']
        self.assertEqual([], workspace['review_writing']['inputs'])
        for item in workspace['paper']['drafts']:
            session = item['session']
            self.assertEqual(0, session['dispatched'])
            self.assertIsNone(session['before_proposal'])
            self.assertTrue(all(c['contributor'] == 'human' for c in session['judgment']['history']))

    def test_manual_mixed_writing_interrupt_reopen_and_continue(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot, restore, snapshot_value
        from claimbranch.fixtures import replay_merge_example
        from claimbranch.core.canonical import decode

        history = replay_merge_example('recorded')
        initial = TerminalWorkspace(history, ai_off=True)
        initial.select('obs-1')
        owner = initial.context_key()
        source_nodes = initial.view['nodes']
        source_choices = [n['id'] for n in source_nodes
                          if n['kind'] in ('claim', 'interpretation', 'observation')]
        source_index = source_choices.index('obs-1')
        pending = initial.service.pending_work()['items']
        expected_explanation = next(item for item in pending if item['kind'] == 'understanding')
        expected_manuscript = next(item for item in pending if item['kind'] == 'manuscript')
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'work'
            directory.mkdir(mode=0o700)
            source = Path(folder) / 'source.tex'
            original = b'% Cafe\xcc\x81\r\n% claimbranch:start id=anchor\nOriginal.\n% claimbranch:end id=anchor\n'
            source.write_bytes(original)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher,
                        project_id=initial.view['project_id'], recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(initial))
            self.launch(navigation='graph', merge_example=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.expect('AI OFF')
            self.send('e', 'YOUR JUDGMENT')
            self.send('\x1b[200~측정한 조건에서만 판단한다.\x1b[201~\t')
            self.paste('다른 조건은 아직 측정하지 않았다.', 'Draft kept')
            self.send('n', 'MY NOTE')
            self.paste('개인 노트 / 판단과 구별', 'Note kept')

            self.action(2, 'WRITE A CLAIM')
            self.send('\r\r', 'Main claim')
            self.send('\x1b[B\r\r', 'Parent in the argument')
            self.send('\x1b[B\r', 'CLAIM STATEMENT')
            self.paste('새 조건은 아직 비교하지 않았다.', 'WRITE A CLAIM')
            self.send('\x1b[B\r', 'SCOPE / CONDITIONS')
            self.paste('One measured split', 'WRITE A CLAIM')
            self.send('\x13', 'YOUR ARGUMENT DRAFTS')
            self.send('l\r', 'SOURCE')
            self.send('\x1b[B' * source_index + '\r', 'WRITE A SCIENTIFIC CHANGE')
            self.send('\x1b[B\r\x1b[F\r', 'WRITE A SCIENTIFIC CHANGE')
            self.send('\x1b[B\r\x1b[B\x1b[B\r', 'WRITE A SCIENTIFIC CHANGE')
            self.send('\x1b[B\r', 'WHY THIS CONNECTION?')
            self.paste('이 관찰은 측정한 조건에만 해당한다.', 'WRITE A SCIENTIFIC CHANGE')
            self.send('\x13', 'YOUR ARGUMENT DRAFTS')
            self.send(' \x0c', 'YOUR ARGUMENT DRAFTS')  # Omit the edge, retaining its writing.
            self.send('\x1b[H\r\x1b[B\x1b[B\r', 'CLAIM STATEMENT')
            self.send('\x7f' * len('새 조건은 아직 비교하지 않았다.') + '\x0c', '0/12000 chars')
            self.back('WRITE A CLAIM', 'YOUR ARGUMENT DRAFTS', '; actions')

            self.action(5, 'DRAFT A RESULT')
            self.send('\r', 'OBSERVED CONTENT')
            self.paste('새 결과 / 미확인', 'Kept')
            self.send('\x1b[B\x1b[B\r', 'RESULT SOURCE')
            self.paste('ssh://synthetic-host/result.csv', 'Kept')
            self.send('\x1b[F\x1b[A\r', 'TENTATIVE JUDGMENT')
            self.paste('아직 잠정적인 해석', 'Kept')
            self.send('\r', 'TENTATIVE JUDGMENT')
            self.send('\x7f' * len('아직 잠정적인 해석') + '\x0c', '0/12,000')
            self.back('DRAFT A RESULT', 'RESULT DRAFTS', '; actions')

            self.send('W', 'PENDING WORK')
            self.send('\x1b[B\re\r', 'YOUR PARTIAL EXPLANATION')
            self.send('r', 'linked without copying')
            self.send('e', 'Ctrl+S keep')
            self.paste('원래 판단을 설명하는 글', 'Explanation kept')
            self.send('e', 'Ctrl+S keep')
            self.send('\x7f' * len('원래 판단을 설명하는 글') + '\x0c', '0/12,000 chars')
            self.back('YOUR PARTIAL EXPLANATION', 'EXPLANATION /',
                      'PENDING WORK / READ', 'PENDING WORK', '; actions')

            self.send('W\x1b[H\r', 'PENDING WORK / READ')
            self.send('m', 'MANUSCRIPT / REVIEW')
            self.send('s', 'SOURCE FILE')
            self.paste(str(source), 'SOURCE / source.tex')
            self.send('e', 'YOUR WORDING')
            self.send('\x1b[200~Measured conditions only.\x1b[201~\t')
            self.paste('다른 조건을 일반화하지 않는다.', 'MANUSCRIPT / REVIEW')
            self.send('e', 'YOUR WORDING')
            self.send('\x7f' * len('Measured conditions only.') + '\x0f', 'SCIENTIFIC BASIS')
            self.resize(80, 24)
            self.send('\x0c', 'SCIENTIFIC BASIS')
            self.send('\x03')
            self.assert_restored(130)
            self.assert_clean_exit_output()
            self.assertEqual(original, source.read_bytes())
            self.assertEqual(['source.tex', 'work'], sorted(p.name for p in Path(folder).iterdir()))
            source.unlink()  # Reopening must use retained exact bytes, not require this file.

            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=initial.view['project_id']) as store:
                    saved = store.load()
            self.assert_manual_payload(saved)
            again = TerminalWorkspace(saved.history, ai_off=True)
            restore(again, saved)
            self.assertEqual(history.manifest(), saved.history.manifest())
            self.assertEqual(owner, again.context_key())
            self.assertEqual('개인 노트 / 판단과 구별', again.note())
            self.assertEqual({'text': '측정한 조건에서만 판단한다.',
                             'rationale': '다른 조건은 아직 측정하지 않았다.'}, again.draft())
            candidates = again.review.candidates()
            self.assertEqual(2, len(candidates.records))
            claim = next(r for r in candidates.records.values() if r['kind'] == 'claim')
            edge = next(r for r in candidates.records.values() if r['kind'] == 'scientific-edge')
            self.assertEqual({'role': 'main', 'parent_ids': ['thesis'],
                'statement': '새 조건은 아직 비교하지 않았다.', 'scope': 'One measured split'}, claim['body'])
            self.assertEqual({'source_id': 'obs-1', 'target_id': claim['id'], 'edge_type': 'qualifies',
                'rationale': '이 관찰은 측정한 조건에만 해당한다.'}, edge['body'])
            self.assertEqual({claim['id']}, set(candidates.selected))
            self.assertEqual({**claim['body'], 'statement': ''},
                             again.review.candidate_inputs[owner][claim['id']]['body'])
            result, = again.intake.items()
            self.assertEqual(owner, result['owner'])
            self.assertEqual('새 결과 / 미확인', result['kept']['observation'])
            self.assertEqual('ssh://synthetic-host/result.csv', result['kept']['source_ref'])
            self.assertEqual('아직 잠정적인 해석', result['kept']['judgment'])
            self.assertEqual({'judgment': ''}, result['unfinished'])
            explanation, = again.understanding.sessions.values()
            entry = next(row for row in decode(explanation.snapshot())['entries']
                         if row['text'] == '원래 판단을 설명하는 글')
            self.assertEqual('원래 판단을 설명하는 글', entry['text'])
            self.assertTrue(entry['reuse_rationale'])
            explanation_id, = again.understanding.sessions
            self.assertEqual(expected_explanation['id'], explanation_id)
            self.assertEqual(expected_explanation['judgment'], explanation.state()['context']['work']['judgment'])
            self.assertEqual('', again.understanding.buffers[explanation_id, entry['topic_id']])
            self.assertTrue(explanation.state()['source_ai_influenced'])
            self.assertFalse(explanation.state()['closure_available'])
            manuscript_id, = again.manuscript.sessions
            self.assertEqual(expected_manuscript['id'], manuscript_id)
            manuscript = again.manuscript.sessions[manuscript_id]
            self.assertEqual(expected_manuscript['judgment'], manuscript.state()['work']['judgment'])
            self.assertEqual(original, manuscript._source)
            self.assertEqual('Measured conditions only.', manuscript.draft.state()['draft']['text'])
            self.assertEqual('다른 조건을 일반화하지 않는다.', manuscript.draft.state()['draft']['rationale'])
            self.assertEqual(['', '다른 조건을 일반화하지 않는다.'],
                             again.manuscript.buffers[manuscript_id, 'wording'])
            self.assertIsNone(manuscript.get_preview())
            self.assertIsNone(manuscript.get_review())
            self.assertIsNone(again.review.session().state()['changes_review'])
            before = snapshot_value(again)

            self.output = b''
            # Keep the narrow 80×24 terminal for the real restart.
            self.launch(navigation='graph', merge_example=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.expect('AI OFF')
            self.action(11, 'MANUSCRIPT DRAFTS')
            self.send('\re', 'YOUR WORDING')
            self.paste('Resumed wording.', 'MANUSCRIPT / REVIEW')
            self.back('MANUSCRIPT DRAFTS', '; actions')
            self.send('q')
            self.assert_restored(0)
            self.assert_clean_exit_output()
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=initial.view['project_id']) as store:
                    final = store.load()
            self.assert_manual_payload(final)
            resumed = TerminalWorkspace(final.history, ai_off=True)
            restore(resumed, final)
            self.assertEqual(history.manifest(), final.history.manifest())
            final_wording = resumed.manuscript.sessions[manuscript_id]
            self.assertEqual({manuscript_id}, set(resumed.manuscript.sessions))
            self.assertEqual(original, final_wording._source)
            self.assertEqual(manuscript.state()['work'], final_wording.state()['work'])
            self.assertEqual('Resumed wording.', final_wording.draft.state()['draft']['text'])
            self.assertEqual('다른 조건을 일반화하지 않는다.', final_wording.draft.state()['draft']['rationale'])
            self.assertNotIn((manuscript_id, 'wording'), resumed.manuscript.buffers)
            self.assertIsNone(final_wording.get_preview())
            self.assertIsNone(final_wording.get_review())
            self.assertFalse(resumed.paper.ai_available)
            before['manuscript'] = snapshot_value(resumed)['manuscript']
            self.assertEqual(before, snapshot_value(resumed))
            self.assertFalse(source.exists())
            self.assertEqual(['work'], sorted(p.name for p in Path(folder).iterdir()))
