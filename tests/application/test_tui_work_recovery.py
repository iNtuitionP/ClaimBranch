"""Versioned judgment checkpoints never turn recovered text into authority."""
from copy import deepcopy
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.fixtures import replay_merge_example


class WorkRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_merge_example('manual')
        self.app = TerminalWorkspace(self.history)
        self.app.select('obs-1')

    def snapshot(self, active=None):
        from claimbranch.application.tui_work_recovery import snapshot
        return snapshot(self.app, active)

    def restore(self, work, *, ai_off=True):
        from claimbranch.application.tui_work_recovery import restore
        app = TerminalWorkspace(self.history, ai_off=ai_off)
        restore(app, work)
        return app

    def many_source_notes(self):
        for episode in self.history.episodes():
            for ref in ('main', 'alternative'):
                view = self.app.service.query(ref, episode_id=episode['id'])
                for node in view['nodes']:
                    owner = (episode['id'], ref, node['id'])
                    self.app.notes[owner] = '개인 노트 ' + node['id']
                    self.app.drafts[owner] = {'text': 'Partial judgment', 'rationale': ''}
                    self.app.review.buffers[owner] = {'text': 'Unkept judgment', 'rationale': ''}
                    self.app.unfinished[(*owner, 'note')] = ['미완성 노트']
                    self.app.unfinished[(*owner, 'edit')] = ['', 'Unfinished reason']

    def test_many_writing_owners_share_only_current_context_membership(self):
        from claimbranch.application import paper_workspace_snapshot as module
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.tui_work_recovery import snapshot_value
        self.many_source_notes()
        value = snapshot_value(self.app)
        # Independent old-style checks prove every row against its own source.
        workspace = module.restore_paper(self.history, value['paper'])
        for name in ('notes', 'drafts', 'buffers', 'unfinished'):
            for item in value[name]:
                module._check_owner(workspace, item['owner'])
        module._check_owner(workspace, value['selection'])
        for reverse in (False, True):
            ordered = deepcopy(value)
            if reverse:
                for name in ('notes', 'drafts', 'buffers', 'unfinished'):
                    ordered[name].reverse()
            with patch.object(PaperService, 'query', autospec=True, side_effect=PaperService.query) as queries:
                self.assertEqual(ordered, module.validate_workspace(self.history, ordered))
            self.assertEqual(4, queries.call_count)
        # The next call starts again; no source cache survives validation.
        with patch.object(PaperService, 'query', autospec=True, side_effect=PaperService.query) as queries:
            module.validate_workspace(self.history, value)
        self.assertEqual(4, queries.call_count)
        restored = self.restore(self.snapshot())
        self.assertEqual(self.app.notes, restored.notes)
        self.assertEqual(self.app.drafts, restored.drafts)
        self.assertEqual(self.app.unfinished, restored.unfinished)
        restored.unfinished[next(iter(restored.unfinished))][0] = 'Only restored text'
        self.assertNotEqual(self.app.unfinished, restored.unfinished)

    def test_shared_owner_projection_still_refuses_later_invalid_writing(self):
        from claimbranch.application.paper_workspace_snapshot import validate_workspace
        from claimbranch.application.tui_work_recovery import snapshot_value
        self.many_source_notes()
        value = snapshot_value(self.app)
        for damage in ('node', 'episode', 'ref', 'duplicate', 'shape', 'selection'):
            bad = deepcopy(value)
            if damage in ('node', 'episode', 'ref'):
                bad['unfinished'][-1]['owner'][{'episode': 0, 'ref': 1, 'node': 2}[damage]] = 'missing'
            elif damage == 'duplicate':
                bad['notes'].append(deepcopy(bad['notes'][0]))
            elif damage == 'shape':
                bad['unfinished'][-1]['texts'] = ['one field', 'second field']
            else:
                bad['selection'][2] = 'missing'
            with self.subTest(damage=damage), self.assertRaises(ContractError):
                validate_workspace(self.history, bad)
        self.assertEqual(value, snapshot_value(self.app))

    def test_fresh_process_retains_ai_chain_links_and_unfinished_separately(self):
        self.app.keep_draft('Before AI', 'My reason')
        outbound = self.app.review.prepare_ai(['obs-1'], include_draft=True)
        self.app.review.begin_ai(outbound)
        self.app.review.complete_ai(self.app.work_key(), outbound['request']['request_id'])
        self.app.review.adopt_ai()
        self.app.keep_draft('Human revision after AI', 'My revised reason')
        owner = self.app.full_context(self.app.work_key())
        self.app.paper.link_work(owner, ['obs-1', 'claim-pruning'])
        self.app.select('claim-pruning')
        self.app.keep_note('한글 개인 노트')
        work = self.snapshot(('edit', ['', 'unfinished reason']))
        restored = self.restore(work)
        self.assertEqual('claim-pruning', restored.selected_id)
        self.assertEqual('Human revision after AI', restored.draft()['text'])
        self.assertEqual('한글 개인 노트', restored.note())
        self.assertEqual(['', 'unfinished reason'], restored.unfinished[(*owner, 'edit')])
        state = restored.review.session().state()
        self.assertTrue(state['draft']['ai_influenced'])
        self.assertEqual(self.app.review.session().state()['draft'], state['draft'])
        self.assertEqual({'text': 'Before AI', 'rationale': 'My reason'}, state['before_proposal'])
        self.assertIsNone(state['outbound']); self.assertIsNone(state['proposal'])
        self.assertIsNone(state['changes_review']); self.assertFalse(state['authorization_verified'])
        script = '''import sys
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import restore
w = PaperWork(sys.stdin.buffer.read())
a = TerminalWorkspace(w.history, ai_off=True)
restore(a, w)
assert a.draft()['text'] == 'Human revision after AI'
assert a.review.session().state()['draft']['ai_influenced']
assert a.review.session().state()['outbound'] is None
print('restored')
'''
        result = subprocess.run([sys.executable, '-c', script], input=work.payload, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b'restored\n', result.stdout)

    def test_invalid_owner_or_contribution_cannot_partially_restore(self):
        self.app.keep_draft('kept', 'reason')
        work = self.snapshot()
        from claimbranch.application.paper_work_store import PaperWork
        for change in ('owner', 'contribution', 'unknown'):
            value = decode(work.payload)
            workspace = value['workspace']
            if change == 'owner': workspace['paper']['drafts'][0]['owner'][2] = 'missing'
            elif change == 'contribution':
                workspace['paper']['drafts'][0]['session']['judgment']['text'] = 'unrecorded'
            else: workspace['approved'] = True
            with self.subTest(change=change), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        self.assertEqual('kept', self.app.draft()['text'])

    def test_separate_judgments_survive_choices_without_copying_notes(self):
        self.app.keep_draft('Observation judgment', '')
        owner = self.app.full_context(self.app.work_key())
        self.app.select('claim-pruning')
        self.app.keep_draft('Separate claim judgment', 'Reason')
        self.app.paper.link_work(owner, ['obs-1', 'claim-pruning'])
        restored = self.restore(self.snapshot())
        self.assertEqual('Observation judgment', restored.draft()['text'])
        restored.paper.activate_work((*owner[:2], 'claim-pruning'), 'claim-pruning')
        self.assertEqual('Separate claim judgment', restored.draft()['text'])
        self.assertEqual(self.history.manifest(), restored.paper.history.manifest())

    def test_wrong_fixture_preserves_target_and_version_one_stays_readable(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui_work_recovery import restore
        self.app.keep_draft('kept', 'reason')
        work = self.snapshot()
        wrong = TerminalWorkspace(replay_merge_example('recorded'))
        wrong.keep_note('untouched')
        with self.assertRaises(ContractError): restore(wrong, work)
        self.assertEqual('untouched', wrong.note())
        old = PaperWork.create(self.history)
        self.assertEqual('claimbranch.paper-work/v1', decode(old.payload)['schema'])
        with self.assertRaises(ContractError): self.restore(old)

    def test_dispatch_budget_does_not_reset_when_writing_is_reopened(self):
        for _ in range(3):
            outbound = self.app.review.prepare_ai(['obs-1'], include_draft=False)
            self.app.review.begin_ai(outbound)
            self.app.review.complete_ai(self.app.work_key(), outbound['request']['request_id'])
        restored = self.restore(self.snapshot(), ai_off=False)
        with self.assertRaisesRegex(ContractError, 'one proposal and two'):
            restored.review.prepare_ai(['obs-1'], include_draft=False)

    def test_manual_capacity_fallback_is_retained_without_a_review_session(self):
        for ref in ('main', 'alternative'):
            view = self.app.service.query(ref, episode_id=self.app.episode_id)
            for node in view['nodes']:
                self.app.open_context_key((self.app.episode_id, ref, node['id']))
                self.app.keep_draft('Manual text ' + node['id'], 'reason')
        self.assertTrue(self.app.review.buffers)
        restored = self.restore(self.snapshot())
        self.assertEqual(self.app.review.buffers, restored.review.buffers)
        self.assertEqual(self.app.draft(), restored.draft())

    def test_excluded_live_editor_and_uncertain_save_are_disclosed(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal, Buffer
        from claimbranch.application.tui_work_recovery import JudgmentRecovery, excluded_work
        from claimbranch.application.paper_work_store import WorkReopenRequired
        store = SimpleNamespace(load=lambda: None, save=lambda work: None)
        self.app.recovery = JudgmentRecovery(store, self.app)
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, 'manuscript-text'
        terminal.buffers = [Buffer('')]
        terminal.buffers[0].insert('Unkept observation')
        self.assertTrue(terminal.checkpoint())
        self.assertIn('unfinished research editor text', excluded_work(self.app))
        terminal.modal, terminal.buffers = None, []
        self.app.keep_draft('changed', 'reason')
        with patch.object(store, 'save', side_effect=WorkReopenRequired('save outcome uncertain; close and reopen work')):
            self.assertFalse(terminal.checkpoint())
        self.assertIn('reopen', self.app.recovery_error.lower())
        self.assertNotIn('last checkpoint', self.app.recovery_error.lower())

    def test_storage_error_does_not_advise_editing_or_closing_live_text(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        store = SimpleNamespace(load=lambda: None, save=lambda work: None)
        self.app.recovery = JudgmentRecovery(store, self.app)
        self.app.keep_note('Live writing')
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal, terminal.buffers = self.app, None, []
        for error in (ContractError('work encryption failed'), OSError('disk full')):
            with self.subTest(error=error), patch.object(store, 'save', side_effect=error):
                self.assertFalse(terminal.checkpoint())
                self.assertIn('Keep this session open', self.app.recovery_error)
                self.assertIn(str(error), self.app.recovery_error)
                self.assertIn('not confirmed', self.app.recovery_error)
                self.assertNotIn('shorten', self.app.recovery_error)
                self.assertNotIn('close and reopen', self.app.recovery_error)
                self.assertEqual('Live writing', self.app.note())

    def test_failed_save_details_are_readable_from_actions_without_changing_writing(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal, Frame
        from claimbranch.application.tui_actions import actions_ui
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal, terminal.buffers = self.app, None, []
        terminal.screen = SimpleNamespace(getmaxyx=lambda: (18, 48))
        self.app.recovery_error = ('Keep this session open. ' * 40 + 'END OF DIAGNOSTIC')
        self.app.keep_note('Retained note')
        before = self.app._navigation()
        terminal.key(';')
        ui = actions_ui(terminal)
        self.assertEqual('Inspect writing save status', ui.items()[0].title)
        terminal.key('enter')
        self.assertEqual('save-status', terminal.modal)
        rendered = terminal.draw_modal(Frame(48, 18)).plain()
        self.assertIn('Keep this session open', rendered)
        for _ in range(20):
            terminal.key('page-down')
            rendered = terminal.draw_modal(Frame(48, 18)).plain()
        self.assertIn('END OF DIAGNOSTIC', ' '.join(rendered.replace('│', ' ').split()))
        terminal.key('escape')
        self.assertIsNone(terminal.modal)
        self.assertEqual(before, self.app._navigation())
        self.assertEqual('Retained note', self.app.note())

    def test_reopen_failure_blocks_both_changed_and_unchanged_retry(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        from claimbranch.application.paper_work_store import WorkReopenRequired
        for changed in (False, True):
            with self.subTest(changed=changed):
                app = TerminalWorkspace(self.history, ai_off=True)
                app.select('obs-1')
                store = SimpleNamespace(load=lambda: None, save=lambda work: None,
                                        verify_unchanged=lambda: None)
                app.recovery = JudgmentRecovery(store, app)
                app.keep_note('Last checkpoint'); app.recovery.save(app)
                previous, previous_input = app.recovery.previous, app.recovery.previous_input
                if changed: app.keep_note('New writing')
                terminal = Terminal.__new__(Terminal)
                terminal.app, terminal.modal, terminal.buffers = app, None, []
                name = 'save' if changed else 'verify_unchanged'
                with patch.object(store, name, side_effect=WorkReopenRequired('Checkpoint state changed')) as failed:
                    self.assertFalse(terminal.checkpoint())
                    self.assertFalse(terminal.checkpoint())
                    failed.assert_called_once()
                app.keep_note('Still editable')
                with patch.object(store, 'save') as retry:
                    self.assertFalse(terminal.checkpoint())
                    retry.assert_not_called()
                self.assertEqual(previous, app.recovery.previous)
                self.assertEqual(previous_input, app.recovery.previous_input)
                self.assertEqual('Still editable', app.note())
                self.assertIn('copy newer writing', app.recovery_error)
                self.assertIn('reopen', app.recovery_error)
                self.assertIn('blocked', app.recovery_error)
                self.assertIn('Ctrl+C exits without saving newer input', app.recovery_error)
                self.assertIsNone(terminal.key('q'))
                self.assertIsNone(terminal.modal)
                self.assertEqual(130, terminal.key('interrupt'))
                self.assertNotIn('shorten', app.recovery_error)
                self.assertNotIn('prior checkpoint retained', app.recovery_error)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS work cipher required')
    def test_native_uncertain_and_external_checkpoint_keep_live_text_and_require_reopen(self):
        import stat
        from claimbranch.application.paper_work_store import PaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        from claimbranch.application.tui import Terminal
        with tempfile.TemporaryDirectory() as root, MacWorkCipher() as cipher:
            for outcome in ('directory-flush', 'external-replace'):
                with self.subTest(outcome=outcome):
                    directory = Path(root) / outcome; directory.mkdir(mode=0o700)
                    key = os.urandom(32)
                    app = TerminalWorkspace(self.history, ai_off=True); app.select('obs-1')
                    app.keep_note('Previous writing')
                    store = PaperWorkStore(directory, cipher=cipher, key=key,
                                           project_id=app.view['project_id'])
                    with store:
                        app.recovery = JudgmentRecovery(store, app); app.recovery.save(app)
                        previous = app.recovery.previous
                        app.keep_note('New writing remains editable')
                        terminal = Terminal.__new__(Terminal)
                        terminal.app, terminal.modal, terminal.buffers = app, None, []
                        if outcome == 'directory-flush':
                            sync = os.fsync
                            def fail_directory(descriptor):
                                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                                    raise OSError('synthetic directory flush failure')
                                return sync(descriptor)
                            with patch('claimbranch.application.paper_work_store.os.fsync', side_effect=fail_directory) as injected:
                                self.assertFalse(terminal.checkpoint())
                                self.assertTrue(injected.called)
                            self.assertIn('uncertain', app.recovery_error)
                        else:
                            path = directory / 'work.cbw'
                            path.write_bytes(cipher.seal(previous, key))
                            external = path.read_bytes()
                            self.assertFalse(terminal.checkpoint())
                            self.assertEqual(external, path.read_bytes())
                            self.assertIn('changed outside', app.recovery_error)
                        after_failure = (directory / 'work.cbw').read_bytes()
                        with patch.object(store, 'save') as retry:
                            self.assertFalse(terminal.checkpoint()); retry.assert_not_called()
                        self.assertEqual(after_failure, (directory / 'work.cbw').read_bytes())
                        self.assertEqual(previous, app.recovery.previous)
                        self.assertEqual('New writing remains editable', app.note())
                        self.assertIn('copy newer writing', app.recovery_error)
                        self.assertNotIn('shorten', app.recovery_error)
                    reopened = TerminalWorkspace(self.history, ai_off=True); reopened.select('obs-1')
                    with store:
                        reopened.recovery = JudgmentRecovery(store, reopened)
                        expected = 'New writing remains editable' if outcome == 'directory-flush' else 'Previous writing'
                        self.assertEqual(expected, reopened.note())
                        self.assertTrue(reopened.recovery.save(reopened) is None)

    def test_repeated_save_failure_preserves_newer_action_feedback(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        store = SimpleNamespace(load=lambda: None, save=lambda work: None)
        self.app.recovery = JudgmentRecovery(store, self.app)
        self.app.keep_note('Live note')
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal, terminal.buffers = self.app, None, []
        with patch.object(store, 'save', side_effect=ContractError('encryption unavailable')):
            self.assertFalse(terminal.checkpoint())
            self.app.message = 'Editing cancelled; unfinished input retained.'
            self.assertFalse(terminal.checkpoint())
            self.assertEqual('Editing cancelled; unfinished input retained.', self.app.message)
            self.assertIn('Ctrl+C exits without saving newer input', self.app.recovery_error)

    def test_passive_modal_does_not_reclassify_kept_editor_buffer_as_unsaved(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal, Buffer
        from claimbranch.application.tui_work_recovery import JudgmentRecovery, excluded_work
        store = SimpleNamespace(load=lambda: None, save=lambda work: None, verify_unchanged=lambda: None)
        self.app.recovery = JudgmentRecovery(store, self.app)
        buffer = Buffer(''); buffer.insert('Kept note'); self.app.keep_note(buffer.text)
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.buffers = self.app, [buffer]
        for modal in ('help', 'actions', 'quit', 'recovery', 'save-status'):
            terminal.modal = modal
            self.assertTrue(terminal.checkpoint())
            self.assertFalse(self.app.uncheckpointed_editor)
            self.assertNotIn('unfinished research editor text', excluded_work(self.app))

    def test_cli_rejects_incompatible_options_before_creating_state(self):
        for args in (['--create-work'], ['--work-dir', '/unused'],
                     ['--series', '--work-dir', '/unused', '--snapshot'],
                     ['--series', '--work-dir', '/unused', '--draft-file', '/unused']):
            result = subprocess.run([sys.executable, '-m', 'claimbranch', 'demo', 'tui', *args],
                                    capture_output=True)
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertIn(b'--work-dir', result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)

    def test_unknown_versions_and_duplicate_links_reject_without_overwrite(self):
        from claimbranch.application.paper_work_store import PaperWork
        self.app.keep_draft('kept', 'reason')
        owner = self.app.full_context(self.app.work_key())
        self.app.paper.link_work(owner, ['obs-1', 'claim-pruning'])
        work = self.snapshot()
        for mutation in ('version', 'links', 'selection', 'review'):
            value = decode(work.payload)
            if mutation == 'version': value['schema'] = 'claimbranch.paper-work/v99'
            elif mutation == 'links': value['workspace']['paper']['links'] *= 2
            elif mutation == 'selection': value['workspace']['selection'][2] = 'missing'
            else: value['episode_id'] = owner[0]
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))

    def test_oversized_text_fails_instead_of_truncating(self):
        self.app.keep_note('한' * 12000)
        with self.assertRaises(ContractError): self.snapshot()
        self.assertEqual('한' * 12000, self.app.note())


@unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
class EncryptedWorkRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from claimbranch.application.work_cipher import MacWorkCipher
        cls.cipher = MacWorkCipher().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cipher.__exit__(None, None, None)

    def test_creation_reuses_shared_key_entry_and_refuses_recreation(self):
        from contextlib import redirect_stdout
        import io
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        history = replay_merge_example('manual')
        key = os.urandom(32)
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            with patch('claimbranch.application.work_commands.recovery_key', return_value=key) as prompt:
                app = TerminalWorkspace(history, ai_off=True)
                recovery = JudgmentRecovery.open(directory, app, create=True)
                recovery.close()
                prompt.assert_called_once_with(from_stdin=False, create=True)
                original = (Path(directory) / 'work.cbw').read_bytes()
                with self.assertRaises(ContractError):
                    JudgmentRecovery.open(directory, TerminalWorkspace(history), create=True)
                self.assertEqual(original, (Path(directory) / 'work.cbw').read_bytes())
            reopened = TerminalWorkspace(history, ai_off=True)
            recovery = JudgmentRecovery.open(directory, reopened)
            recovery.close()
        self.assertNotIn(key.hex(), output.getvalue())

    def test_encrypted_reopen_failed_replace_and_unchanged_checkpoint(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        history = replay_merge_example('manual')
        app = TerminalWorkspace(history, ai_off=True)
        app.keep_draft('보존할 판단', 'Reason')
        with tempfile.TemporaryDirectory() as directory:
            with DevicePaperWorkStore.create(directory, cipher=self.cipher,
                    project_id=app.view['project_id'], recovery_key=os.urandom(32)) as store:
                recovery = JudgmentRecovery(store, app)
                app.recovery = recovery
                recovery.save(app, ('edit', ['Unfinished', '']))
                original = (Path(directory) / 'work.cbw').read_bytes()
                self.assertNotIn('보존할 판단'.encode(), original)
                with patch.object(store, 'save', side_effect=AssertionError('unchanged data rewritten')):
                    recovery.save(app, ('edit', ['Unfinished', '']))
                # A no-op must still notice external file replacement/deletion.
                damaged = original[:-1] + bytes([original[-1] ^ 1])
                (Path(directory) / 'work.cbw').write_bytes(damaged)
                with patch.object(store, 'save', side_effect=AssertionError('no-op encrypted again')):
                    with self.assertRaises(ContractError):
                        recovery.save(app, ('edit', ['Unfinished', '']))
                self.assertEqual(damaged, (Path(directory) / 'work.cbw').read_bytes())
                (Path(directory) / 'work.cbw').write_bytes(original)
                app.keep_draft('New text', 'reason')
                with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('disk full')):
                    with self.assertRaises(ContractError): recovery.save(app)
                self.assertEqual(original, (Path(directory) / 'work.cbw').read_bytes())
            # Open in a genuinely fresh process with device key, no raw/recovery
            # secret in argv, environment, stdin or a plaintext sidecar.
            script = """import sys
from claimbranch.application.device_work_store import DevicePaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import restore
with MacWorkCipher() as cipher:
 with DevicePaperWorkStore(sys.argv[1], cipher=cipher, project_id=sys.argv[2]) as store:
  work = store.load()
  app = TerminalWorkspace(work.history, ai_off=True)
  restore(app, work)
  assert app.draft()['text'] == '보존할 판단'
  assert list(app.unfinished.values()) == [['Unfinished', '']]
  assert app.review.session().state()['changes_review'] is None
  print('device-reopened')
"""
            result = subprocess.run([sys.executable, '-c', script, directory, app.view['project_id']],
                                    capture_output=True, timeout=100)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(b'device-reopened\n', result.stdout)


if __name__ == '__main__': unittest.main()
