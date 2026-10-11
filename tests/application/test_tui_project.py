"""Selected synthetic paper entry; no evidence or accepted-authority shortcuts."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout
import io
import os
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import patch

from claimbranch.application.project_work import preview_association
from claimbranch.application.tui_project import prepare_project, project_workspace, ProjectRecovery, prepare_first_episode, first_episode_prompt
from claimbranch.application.tui import render_snapshot
from claimbranch.core.canonical import decode
from claimbranch.application.cli import main


class ProjectTerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paper, self.directory = root / 'paper', root / 'work'
        self.paper.mkdir(); self.directory.mkdir(mode=0o700)
        subprocess.run(['git', 'init', '-q', str(self.paper)], check=True)
        self.source = b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
        (self.paper / 'paper.tex').write_bytes(self.source)
        self.preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)

    def project(self):
        return prepare_project(self.preview, project_id='new-paper', title='New experiment',
                               thesis='작업 논지는 아직 가설이다.', question='어떤 조건에서 성립할까?')

    def test_initial_entry_contains_only_authored_thesis_and_question(self):
        project = self.project()
        app = project_workspace(project)
        self.assertEqual({'claim', 'manuscript-anchor'}, {n['kind'] for n in app.nodes.values()})
        self.assertEqual('작업 논지는 아직 가설이다.', app.title(app.selected_id))
        self.assertEqual('', app.draft()['text'])
        self.assertFalse(app.paper.ai_available)
        self.assertEqual([], app.service.pending_work()['items'])
        self.assertIn('New experiment', render_snapshot(app))
        self.assertEqual([], list(self.directory.iterdir()))
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())

    def test_selected_project_classifies_input_and_blocks_reopen_required_save(self):
        from claimbranch.application.paper_work_store import WorkReopenRequired
        from claimbranch.application.tui_work_recovery import WritingInputError
        original = self.project(); app = project_workspace(original)
        store = SimpleNamespace(load=lambda: original, save=lambda work: None, verify_unchanged=lambda: None)
        recovery = ProjectRecovery(store, app, original)
        app.keep_note('Live selected-project writing')
        with patch('claimbranch.application.tui_project.checkpoint_input', side_effect=WritingInputError('bounded writing')):
            with self.assertRaises(WritingInputError): recovery.save(app)
        self.assertIs(original, recovery.project)
        with patch.object(store, 'save', side_effect=WorkReopenRequired('Work changed')) as failed:
            with self.assertRaises(WorkReopenRequired): recovery.save(app)
            with self.assertRaises(WorkReopenRequired): recovery.save(app)
            failed.assert_called_once()
        with patch.object(store, 'save') as retry:
            with self.assertRaises(WorkReopenRequired): recovery.save(app)
            retry.assert_not_called()
        self.assertIs(original, recovery.project)
        self.assertIsNone(recovery.previous_input)
        self.assertEqual('Live selected-project writing', app.note())

    def test_save_reopen_keeps_association_and_incomplete_authoring(self):
        original = self.project()
        app = project_workspace(original)
        records = [original]
        store = SimpleNamespace(load=lambda: records[-1], save=records.append, verify_unchanged=lambda: None)
        app.recovery = ProjectRecovery(store, app, original)
        app.notes[app.context_key()] = '직접 작성한 노트'
        app.review.edit_draft({'text': 'Partial judgment', 'rationale': ''})
        work = app.review.candidates()
        work.create('claim', {'role': 'main', 'parent_ids': ['thesis'],
                             'statement': 'A bounded claim', 'scope': 'Only this setting'})
        app.recovery.save(app, ('edit', ['미완성 판단', '']))
        saved = records[-1]
        self.assertEqual(decode(original.payload)['associations'], decode(saved.payload)['associations'])
        reopened = project_workspace(saved)
        self.assertIn('Writing restored', reopened.message)
        self.assertEqual('Partial judgment', reopened.draft()['text'])
        from claimbranch.application.tui_work_recovery import excluded_work
        self.assertEqual([], excluded_work(reopened))
        self.assertEqual(app.notes, reopened.notes)
        self.assertEqual(app.review.candidates().records, reopened.review.candidates().records)
        self.assertEqual(['미완성 판단', ''], reopened.unfinished[(*app.work_key(), 'edit')])
        self.assertEqual(original.work.history.manifest(), reopened.paper.history.manifest())
        self.assertFalse(reopened.paper.ai_available)

    def test_changed_or_missing_source_keeps_writing_and_original_association(self):
        project = self.project()
        for raw, expected in ((self.source + b'% external edit\n', 'source-changed-reconciliation-required'),
                              (None, 'unavailable-or-unsupported')):
            path = self.paper / 'paper.tex'
            if raw is None: path.unlink()
            else: path.write_bytes(raw)
            app = project_workspace(project)
            self.assertEqual(expected, app.project_source_status)
            self.assertEqual('작업 논지는 아직 가설이다.', app.title(app.selected_id))
            self.assertFalse(app.paper.ai_available)
            self.assertEqual([], list(self.directory.iterdir()))
            self.assertIn('SOURCE AT OPEN:', render_snapshot(app))
            self.assertIn('file unavailable' if raw is None else 'file changed', render_snapshot(app, 80, 24))

    def arguments(self):
        return ['demo', 'project', 'init', '--directory', str(self.directory),
                '--paper-root', str(self.paper), '--manuscript', 'paper.tex',
                '--project-id', 'new-paper', '--title', 'New experiment',
                '--thesis', 'An unresolved working claim', '--question', 'Which conditions matter?']

    def test_cli_dry_run_needs_no_native_key_or_tty_and_writes_nothing(self):
        with patch('claimbranch.application.work_cipher.MacWorkCipher') as cipher, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(self.arguments() + ['--dry-run']))
        cipher.assert_not_called()
        self.assertIn('"new_evidence": 0', output.getvalue())
        self.assertIn('Which conditions matter?', output.getvalue())
        self.assertEqual([], list(self.directory.iterdir()))
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())

    def test_cancel_does_not_create_key_or_store(self):
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True), \
             patch.dict(os.environ, {'TERM': 'xterm-256color'}), patch('sys.platform', 'darwin'), \
             patch('builtins.input', return_value=''), patch('claimbranch.application.work_cipher.MacWorkCipher') as cipher, \
             patch('claimbranch.application.work_commands.recovery_key') as key:
            self.assertEqual(0, main(self.arguments()))
        cipher.assert_not_called(); key.assert_not_called()
        self.assertEqual([], list(self.directory.iterdir()))

    def test_changed_preview_refuses_creation_before_key_store(self):
        def change_source(*args, **kwargs):
            (self.paper / 'paper.tex').write_bytes(self.source + b'% changed\n')
            return bytes(32)
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True), \
             patch.dict(os.environ, {'TERM': 'xterm-256color'}), patch('sys.platform', 'darwin'), \
             patch('builtins.input', return_value='create'), patch('claimbranch.application.work_cipher.MacWorkCipher') as cipher, \
             patch('claimbranch.application.work_commands.recovery_key', side_effect=change_source):
            self.assertEqual(1, main(self.arguments()))
        cipher.assert_not_called()
        self.assertEqual([], list(self.directory.iterdir()))

    def test_source_changed_during_confirmation_needs_no_recovery_key(self):
        def confirm(*args):
            (self.paper / 'paper.tex').write_bytes(self.source + b'% changed\n')
            return 'create'
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('sys.platform', 'darwin'), patch('builtins.input', side_effect=confirm), \
             patch('claimbranch.application.work_commands.recovery_key') as key:
            self.assertEqual(1, main(self.arguments()))
        key.assert_not_called()
        self.assertEqual([], list(self.directory.iterdir()))

    def test_failed_checkpoint_keeps_live_writing_and_prior_project(self):
        from claimbranch.core.canonical import ContractError
        project = self.project()
        app = project_workspace(project)
        def fail(work):
            raise ContractError('Synthetic save failure')
        recovery = ProjectRecovery(SimpleNamespace(save=fail), app, project)
        app.notes[app.context_key()] = 'Keep this writing'
        with self.assertRaisesRegex(ContractError, 'save failure'):
            recovery.save(app)
        self.assertIs(project, recovery.project)
        self.assertIsNone(recovery.previous_input)
        self.assertIn('Keep this writing', app.notes.values())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_last_source_recheck_failure_leaves_no_orphan_checkpoint(self):
        from claimbranch.application.project_work import ProjectWorkStore
        save = ProjectWorkStore.save
        def changed(store, work, **kwargs):
            (self.paper / 'paper.tex').write_bytes(self.source + b'% late change\n')
            return save(store, work, **kwargs)
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', return_value='create'), \
             patch('claimbranch.application.work_commands.recovery_key', return_value=os.urandom(32)), \
             patch.object(ProjectWorkStore, 'save', changed):
            self.assertEqual(1, main(self.arguments()))
        self.assertEqual(['work.lock'], [p.name for p in self.directory.iterdir()])
        self.assertEqual(b'', (self.directory / 'work.lock').read_bytes())
        # The reusable session lock is not an encrypted project or orphan key;
        # a new reviewed init can use the same directory without manual deletion.
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', return_value='create'), \
             patch('claimbranch.application.work_commands.recovery_key', return_value=os.urandom(32)), \
             patch('claimbranch.application.tui.run_terminal', return_value=0):
            self.assertEqual(0, main(self.arguments()))

    def test_backend_project_without_episode_is_not_silently_modified(self):
        from claimbranch.application.project_work import initialize_project
        from claimbranch.core.canonical import ContractError
        project = initialize_project(self.preview, project_id='new-paper', title='New experiment',
                                     thesis_id='thesis', thesis='A tentative question')
        original = project.payload
        with self.assertRaisesRegex(ContractError, 'no research episode'):
            project_workspace(project)
        self.assertEqual(original, project.payload)
        self.assertEqual([], list(self.directory.iterdir()))

    def empty_project(self, thesis_id='thesis'):
        from claimbranch.application.project_work import initialize_project
        return initialize_project(self.preview, project_id='new-paper', title='New experiment',
                                  thesis_id=thesis_id, thesis='아직 검증하지 않은 논지')

    def test_first_question_preserves_seed_and_association_without_evidence(self):
        from claimbranch.core.canonical import ContractError
        for thesis_id in ('thesis', 'first-episode', 'open-first-episode'):
            original = self.empty_project(thesis_id)
            started = prepare_first_episode(original, '어떤 조건에서 성립할까?')
            self.assertEqual(original.work.history.seed, started.work.history.seed)
            self.assertEqual(decode(original.payload)['associations'], decode(started.payload)['associations'])
            self.assertEqual([], original.work.history.episodes())
            self.assertEqual(1, len(started.work.history.episodes()))
            self.assertEqual(0, started.work.history.watermark)
            self.assertFalse(project_workspace(started).paper.ai_available)
            self.assertEqual('어떤 조건에서 성립할까?', decode(started.work.history.commands[-1])['payload']['question'])
            with self.assertRaises(ContractError):
                prepare_first_episode(started, 'Never duplicate an episode')
            with patch('builtins.input') as prompt, self.assertRaises(ContractError):
                first_episode_prompt(started)
            prompt.assert_not_called()
        self.assertEqual([], list(self.directory.iterdir()))

    def test_first_question_invalid_retry_edit_and_cancel_are_detached(self):
        project = self.empty_project()
        with redirect_stdout(io.StringIO()) as output, patch('builtins.input', side_effect=[
                '', '   ', '첫 질문', 'edit', '수정한 질문', 'strat', ' Start ']):
            started = first_episode_prompt(project)
        self.assertIn('아직 검증하지 않은 논지', output.getvalue())
        self.assertIn('First question preview', output.getvalue())
        self.assertEqual('수정한 질문', decode(started.work.history.commands[-1])['payload']['question'])
        with redirect_stdout(io.StringIO()), patch('builtins.input', side_effect=['저장하지 않음', '']):
            self.assertIsNone(first_episode_prompt(project))
        self.assertEqual([], project.work.history.episodes())
        self.assertEqual([], list(self.directory.iterdir()))

    def test_setup_preview_reports_actual_episode_when_anchor_uses_default_name(self):
        import json
        (self.paper / 'paper.tex').write_bytes(self.source.replace(b'anchor', b'first-episode'))
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(self.arguments() + ['--anchor', 'first-episode', '--dry-run']))
        self.assertEqual('first-episode-1', json.loads(output.getvalue())['initial_episode'])
        self.assertEqual([], list(self.directory.iterdir()))

    def test_refreshed_association_names_retained_basis_without_missing_source_warning(self):
        from claimbranch.application.project_work import preview_source_refresh
        project = self.project()
        (self.paper / 'paper.tex').write_bytes(self.source + b'% reviewed association refresh\n')
        preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
        refreshed = project.refresh_source(preview_source_refresh(project, preview))
        app = project_workspace(refreshed)
        self.assertEqual('unchanged-since-refresh', app.project_source_status)
        frame = render_snapshot(app)
        self.assertIn('source association refreshed', frame)
        self.assertIn('earlier writing basis retained', frame)
        self.assertNotIn('SOURCE AT OPEN:', frame)
        self.assertEqual(project.work.history.manifest(), app.paper.history.manifest())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_first_question_refuses_external_checkpoint_change_during_prompt(self):
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.project_work import ProjectWorkStore
        project = self.empty_project()
        with MacWorkCipher() as cipher:
            with ProjectWorkStore.create(self.directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                store.save(project, preview=self.preview)
        checkpoint = self.directory / 'work.cbw'
        changed = checkpoint.read_bytes() + b'external-change'
        answers = iter(['Keep the existing file?', 'start'])
        def answer(prompt):
            value = next(answers)
            if value == 'start':
                checkpoint.write_bytes(changed)
            return value
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', side_effect=answer), patch('claimbranch.application.tui.run_terminal') as terminal:
            self.assertEqual(1, main(['demo', 'project', 'open', '--directory', str(self.directory), '--project-id', 'new-paper']))
        terminal.assert_not_called()
        self.assertEqual(changed, checkpoint.read_bytes())
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_empty_saved_project_cancel_interrupt_save_failure_and_start(self):
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.project_work import ProjectWorkStore
        from claimbranch.core.canonical import ContractError
        original = self.empty_project()
        with MacWorkCipher() as cipher:
            with ProjectWorkStore.create(self.directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                store.save(original, preview=self.preview)
        before = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        args = ['demo', 'project', 'open', '--directory', str(self.directory), '--project-id', 'new-paper']
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('claimbranch.application.work_commands.recovery_key') as key, \
             patch('claimbranch.application.tui.run_terminal', return_value=0) as terminal:
            for answers, code in ((['취소할 질문', ''], 0), ([KeyboardInterrupt()], 130), ([EOFError()], 0)):
                with patch('builtins.input', side_effect=answers):
                    self.assertEqual(code, main(args))
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()})
            with patch('builtins.input', side_effect=['실패해도 남는 이전 프로젝트', 'start']), \
                 patch.object(ProjectWorkStore, 'save', side_effect=ContractError('Injected save refusal')):
                self.assertEqual(1, main(args))
            terminal.assert_not_called()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()})
            (self.paper / 'paper.tex').unlink()
            with patch('builtins.input', side_effect=['소스 없이 초안부터 시작할까?', 'start']):
                self.assertEqual(0, main(args))
            self.assertEqual('unavailable-or-unsupported', terminal.call_args.kwargs['workspace'].project_source_status)
            with patch('builtins.input') as prompt:
                self.assertEqual(0, main(args))
            prompt.assert_not_called()
            key.assert_not_called()
        with MacWorkCipher() as cipher:
            with ProjectWorkStore(self.directory, cipher=cipher, project_id='new-paper') as store:
                saved = store.load()
        self.assertEqual(1, len(saved.work.history.episodes()))
        self.assertEqual(original.work.history.seed, saved.work.history.seed)
        self.assertEqual(decode(original.payload)['associations'], decode(saved.payload)['associations'])
        self.assertEqual('소스 없이 초안부터 시작할까?', decode(saved.work.history.commands[-1])['payload']['question'])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_confirmed_cli_creation_and_wrong_identity_reopen(self):
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.project_work import ProjectWorkStore
        def enter(*args, **kwargs):
            frame = sys._getframe(1)
            while frame and frame.f_code.co_name != 'run_project_command':
                frame = frame.f_back
            self.assertIsNotNone(frame)
            self.assertIsNone(frame.f_locals['key'])
            return 0
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', return_value='create'), \
             patch('claimbranch.application.work_commands.recovery_key', return_value=os.urandom(32)), \
             patch('claimbranch.application.tui.run_terminal', side_effect=enter) as terminal:
            self.assertEqual(0, main(self.arguments()))
        app = terminal.call_args.kwargs['workspace']
        self.assertIsInstance(app.recovery, ProjectRecovery)
        self.assertFalse(app.paper.ai_available)
        with MacWorkCipher() as cipher:
            with ProjectWorkStore(self.directory, cipher=cipher, project_id='new-paper') as store:
                saved = store.load()
                self.assertIn('workspace', decode(saved.work.payload))
                self.assertEqual('unchanged', saved.source_status())
        before = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            self.assertEqual(1, main(['demo', 'project', 'open', '--directory', str(self.directory), '--project-id', 'wrong-paper']))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()})
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())
