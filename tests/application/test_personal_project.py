"""Own-project personal persistence, with no native key or protected authority."""
from contextlib import redirect_stdout, redirect_stderr
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from claimbranch.application.cli import main
from claimbranch.application.paper_work_store import PaperWork, WorkReopenRequired
from claimbranch.application.project_work import preview_association
from claimbranch.application.tui import render_snapshot
from claimbranch.application.tui_project import prepare_project, project_workspace
from claimbranch.core.canonical import ContractError, decode


class PersonalProjectTests(unittest.TestCase):
    def test_explicit_provider_attaches_on_init_and_open_without_saving_configuration(self):
        from claimbranch.application.provider_profile import ProviderProfile, ProviderProfileStore
        from claimbranch.application.tui_proposals import available
        config=self.root/'llm'; config.mkdir(mode=0o700)
        with ProviderProfileStore(config) as store:
            store.write(ProviderProfile.create(api='openai-chat',endpoint='https://llm.example/v1/chat/completions',
                model='my/personal-model',credential_env='MY_PERSONAL_KEY').payload)
        connections=[]
        def inspect(history, *, workspace):
            connections.append(workspace.provider_connection)
            self.assertTrue(available(workspace)); self.assertFalse(workspace.paper.ai_available)
            workspace.keep_draft('내 판단','내 이유'); workspace.recovery.save(workspace)
            return 0
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty',return_value=True), \
             patch('sys.stdout.isatty',return_value=True), patch.dict(os.environ,{'TERM':'xterm-256color'}), \
             patch('builtins.input',return_value='create'), patch('socket.socket',side_effect=AssertionError('no network')), \
             patch('claimbranch.application.tui.run_terminal',side_effect=inspect):
            self.assertEqual(0,main(self.arguments()+['--provider-directory',str(config)]))
            self.assertEqual(0,main(['project','open','--directory',str(self.directory),'--provider-directory',str(config)]))
        self.assertTrue(all(not c.enabled and c.store._dir is None for c in connections))
        with self.store() as store: saved=store.load()
        self.assertNotIn(b'MY_PERSONAL_KEY',saved.payload); self.assertNotIn(b'my/personal-model',saved.payload)
        reopened=project_workspace(saved); self.assertFalse(available(reopened))
        self.assertEqual('내 판단',reopened.draft()['text'])

    def test_bad_provider_prevents_project_creation_and_dry_run_never_creates_state(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(1,main(self.arguments()+['--provider-directory',str(self.root/'missing'),'--dry-run']))
        self.assertEqual([],list(self.directory.iterdir()))
        from claimbranch.application.provider_profile import ProviderProfile, ProviderProfileStore
        config=self.root/'llm'; config.mkdir(mode=0o700)
        with ProviderProfileStore(config) as store:
            store.write(ProviderProfile.create(api='anthropic-messages',endpoint='https://llm.example/v1/messages',model='mine').payload)
        with redirect_stdout(io.StringIO()) as out, patch('socket.socket',side_effect=AssertionError('no network')):
            self.assertEqual(0,main(self.arguments()+['--provider-directory',str(config),'--dry-run']))
        self.assertFalse(__import__('json').loads(out.getvalue())['personal_llm']['dispatch_available'])
        self.assertEqual([],list(self.directory.iterdir()))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paper, self.directory = self.root / 'paper', self.root / 'personal'
        self.paper.mkdir(); self.directory.mkdir(mode=0o700)
        subprocess.run(['git', 'init', '-q', str(self.paper)], check=True)
        self.source = b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
        (self.paper / 'paper.tex').write_bytes(self.source)
        self.preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
        self.project = prepare_project(self.preview, project_id='my-study', title='My study',
            thesis='훈련 조건에 따라 결과가 달라진다.', question='어떤 조건에서 재현될까?')

    def store(self, *, create=False, project_id=None):
        from claimbranch.application.personal_project import PersonalProjectStore
        return (PersonalProjectStore.create(self.directory, project_id='my-study') if create else
                PersonalProjectStore(self.directory, project_id=project_id))

    def save_initial(self):
        with self.store(create=True) as store:
            store.save(self.project, preview=self.preview)
        return self.directory / 'personal.cbp'

    def test_creation_only_archive_refusal_ends_after_first_successful_save(self):
        from claimbranch.application.tui_work_recovery import snapshot_value
        with self.store(create=True) as store:
            store.save(self.project,preview=self.preview)
            # A later unrelated archive file cannot turn ordinary saves into
            # another project-creation attempt. Public archive still refuses here.
            archive=self.directory/'project.json'; archive.write_bytes(b'unrelated export')
            archive.chmod(0o600)
            app=project_workspace(store.load()); app.keep_note('Later writing survives')
            updated=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            store.save(updated)
            self.assertEqual('Later writing survives',project_workspace(store.load()).note())

    def arguments(self):
        return ['project', 'init', '--directory', str(self.directory),
                '--paper-root', str(self.paper), '--manuscript', 'paper.tex',
                '--project-id', 'my-study', '--title', 'My study',
                '--thesis', '훈련 조건에 따라 결과가 달라진다.', '--question', '어떤 조건에서 재현될까?']

    def test_public_preview_requires_no_key_or_terminal_and_writes_nothing(self):
        with patch('claimbranch.application.work_cipher.MacWorkCipher') as native, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(0, main(self.arguments() + ['--dry-run']))
        native.assert_not_called()
        value = __import__('json').loads(out.getvalue())
        self.assertEqual('personal-project-preview', value['kind'])
        self.assertEqual('off', value['ai'])
        self.assertEqual(0, value['new_evidence'])
        self.assertFalse(value['authorization_verified'])
        self.assertEqual([], list(self.directory.iterdir()))
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())

    def test_cancel_creates_no_project_or_key(self):
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', return_value=''), patch('claimbranch.application.work_cipher.MacWorkCipher') as native:
            self.assertEqual(0, main(self.arguments()))
        native.assert_not_called()
        self.assertEqual([], list(self.directory.iterdir()))

    def test_public_create_and_open_keep_writing_without_native_code(self):
        created_history = []
        def write(history, *, workspace):
            created_history.append(history.manifest())
            workspace.keep_note('직접 쓴 연구 노트')
            workspace.recovery.save(workspace, ('edit', ['미완성 판단', '근거는 확인 중']))
            self.assertIn('PERSONAL', render_snapshot(workspace))
            self.assertNotIn('SYNTHETIC', render_snapshot(workspace))
            return 0
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('builtins.input', return_value='create'), patch('claimbranch.application.work_cipher.MacWorkCipher') as native, \
             patch('claimbranch.application.tui.run_terminal', side_effect=write):
            self.assertEqual(0, main(self.arguments()))
        native.assert_not_called()
        with self.store() as store:
            saved = store.load()
        app = project_workspace(saved)
        self.assertEqual('직접 쓴 연구 노트', app.note())
        self.assertEqual(['미완성 판단', '근거는 확인 중'], app.unfinished[(*app.work_key(), 'edit')])
        self.assertEqual(created_history[0], saved.work.history.manifest())
        self.assertFalse(app.paper.ai_available)
        def inspect(history, *, workspace):
            self.assertEqual('직접 쓴 연구 노트', workspace.note())
            self.assertIn('PERSONAL', render_snapshot(workspace, 80, 24))
            self.assertNotIn('encrypted', render_snapshot(workspace))
            return 0
        with redirect_stdout(io.StringIO()), patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch('claimbranch.application.tui.run_terminal', side_effect=inspect):
            self.assertEqual(0, main(['project', 'open', '--directory', str(self.directory)]))
        self.assertEqual(self.source, (self.paper / 'paper.tex').read_bytes())

    def test_fresh_process_retains_context_writing_and_no_authority(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        with self.store(create=True) as store:
            store.save(self.project, preview=self.preview)
            app = project_workspace(self.project)
            app.recovery = PersonalProjectRecovery(store, app, self.project)
            app.keep_note('독립 프로세스에서 읽을 노트')
            app.recovery.save(app, ('edit', ['아직 끝나지 않은 판단', '']))
        code = '''import json,sys
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.tui_project import project_workspace
from claimbranch.core.canonical import decode
with PersonalProjectStore(sys.argv[1]) as store:
    project=store.load(); app=project_workspace(project)
    print(json.dumps({'note':app.note(),'text':app.unfinished[(*app.work_key(),'edit')],
        'project':project.project_id,'authority':decode(project.payload)['authority'],
        'authorization':decode(project.payload)['authorization_verified'],'ai':app.paper.ai_available},ensure_ascii=False))
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.directory)],
            check=True, capture_output=True, text=True)
        value = __import__('json').loads(result.stdout)
        self.assertEqual('독립 프로세스에서 읽을 노트', value['note'])
        self.assertEqual(['아직 끝나지 않은 판단', ''], value['text'])
        self.assertEqual('my-study', value['project'])
        self.assertEqual('unaccepted-work', value['authority'])
        self.assertFalse(value['authorization']); self.assertFalse(value['ai'])

    def test_corrupt_newer_wrong_project_and_missing_files_never_replace_history(self):
        path = self.save_initial(); original = path.read_bytes()
        for raw in (b'corrupt', original[:5] + b'\x02' + original[6:]):
            path.write_bytes(raw)
            with self.assertRaises(ContractError):
                with self.store() as store: store.load()
            self.assertEqual(raw, path.read_bytes())
        path.write_bytes(original)
        with self.assertRaises(ContractError):
            with self.store(project_id='other-project') as store: store.load()
        self.assertEqual(original, path.read_bytes())
        path.unlink()
        with self.assertRaises(ContractError):
            with self.store(): pass
        self.assertFalse(path.exists())

    def test_competing_open_and_external_changes_preserve_saved_and_live_work(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        path = self.save_initial()
        with self.store() as store:
            saved = store.load(); app = project_workspace(saved)
            app.recovery = PersonalProjectRecovery(store, app, saved)
            with self.assertRaises(ContractError):
                with self.store(): pass
            app.keep_note('새 글은 메모리에 남는다')
            path.write_bytes(b'external change')
            with self.assertRaises(WorkReopenRequired): app.recovery.save(app)
            with self.assertRaises(WorkReopenRequired): app.recovery.save(app)
            self.assertEqual('새 글은 메모리에 남는다', app.note())
            self.assertEqual(b'external change', path.read_bytes())

    def test_failed_replace_and_uncertain_flush_do_not_report_success(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        path = self.save_initial(); original = path.read_bytes()
        with self.store() as store:
            saved = store.load(); app = project_workspace(saved)
            app.recovery = PersonalProjectRecovery(store, app, saved)
            app.keep_note('살려야 할 글')
            with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(ContractError): app.recovery.save(app)
            self.assertEqual(original, path.read_bytes())
            self.assertEqual('살려야 할 글', app.note())
            sync = store._sync
            def fail_after_replace(descriptor):
                if descriptor == store._dir: raise OSError('directory sync failed')
                return sync(descriptor)
            with patch.object(store, '_sync', side_effect=fail_after_replace):
                with self.assertRaises(WorkReopenRequired): app.recovery.save(app)
            with self.assertRaises(WorkReopenRequired): app.recovery.save(app)
        with self.store() as reopened:
            self.assertEqual('살려야 할 글', project_workspace(reopened.load()).note())

    def test_encrypted_workspace_and_linked_or_public_file_are_not_adopted(self):
        legacy = self.directory / 'work.cbw'; legacy.write_bytes(b'CBWD\x00\x01owned legacy work')
        legacy.chmod(0o600)
        with self.assertRaises(ContractError):
            with self.store(create=True): pass
        self.assertEqual({'work.cbw'}, {p.name for p in self.directory.iterdir()})
        legacy.unlink()
        path = self.save_initial(); original = path.read_bytes()
        path.chmod(0o644)
        with self.assertRaises(ContractError):
            with self.store() as store: store.load()
        path.chmod(0o600); path.unlink()
        target = self.root / 'target'; target.write_bytes(original); target.chmod(0o600)
        path.symlink_to(target)
        with self.assertRaises(ContractError):
            with self.store() as store: store.load()
        self.assertEqual(original, target.read_bytes())

    def test_native_checkpoint_namespace_cannot_strand_personal_work(self):
        from claimbranch.application.paper_work_store import PaperWorkStore
        path = self.save_initial(); original = path.read_bytes()
        store = PaperWorkStore.__new__(PaperWorkStore)
        store._configure(self.directory, codec=SimpleNamespace(), project_id='my-study')
        with self.assertRaisesRegex(ContractError, 'personal'):
            with store: pass
        self.assertEqual(original, path.read_bytes())
        self.assertFalse((self.directory / 'work.cbw').exists())

    def test_uncertain_public_create_does_not_claim_files_retained(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err, \
             patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True), \
             patch.dict(os.environ, {'TERM': 'xterm-256color'}), patch('builtins.input', return_value='create'), \
             patch.object(PersonalProjectStore, 'save', side_effect=WorkReopenRequired('save outcome uncertain')):
            self.assertEqual(1, main(self.arguments()))
        self.assertIn('not confirmed', err.getvalue())
        self.assertNotIn('Original files retained', err.getvalue())

    def test_wrong_storage_mode_names_its_reason_without_claiming_a_save_attempt(self):
        legacy = self.directory / 'work.cbw'
        legacy.write_bytes(b'legacy checkpoint'); legacy.chmod(0o600)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err, \
             patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True), \
             patch.dict(os.environ, {'TERM': 'xterm-256color'}), patch('builtins.input', return_value='create'):
            self.assertEqual(1, main(self.arguments()))
        self.assertIn('separate destination', err.getvalue())
        self.assertNotIn('Saving is not confirmed', err.getvalue())
        self.assertEqual({'work.cbw'}, {p.name for p in self.directory.iterdir()})

    def test_personal_ui_retention_does_not_rewrite_scientific_or_user_text(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.tui import Terminal, Frame
        from claimbranch.application.tui_intake_ui import intake_ui
        app = project_workspace(self.project)
        app.recovery = PersonalProjectRecovery(SimpleNamespace(), app, self.project)
        app.keep_note('encrypted samples are a scientific condition')
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal, terminal.buffers = app, None, []
        terminal.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        intake_ui(terminal).enter('new')
        text = intake_ui(terminal).draw(Frame(80, 24)).plain()
        self.assertIn('Personal draft', text)
        self.assertIn('local recovery', text)
        self.assertNotIn('encrypted recovery', text)
        terminal.modal = 'help'; terminal.help_scroll = 0
        text = terminal.draw_modal(Frame(132, 38)).plain()
        self.assertIn('PERSONAL WRITING', text)
        self.assertEqual('encrypted samples are a scientific condition', app.note())

    def test_changed_missing_source_preserves_prior_context_and_writing(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        with self.store(create=True) as store:
            store.save(self.project, preview=self.preview)
            app = project_workspace(self.project)
            app.recovery = PersonalProjectRecovery(store, app, self.project)
            app.keep_note('원래 관찰을 다시 확인해야 한다')
            app.recovery.save(app)
        source = self.paper / 'paper.tex'
        for raw, status in ((self.source + b'% edit\n', 'source-changed-reconciliation-required'),
                            (None, 'unavailable-or-unsupported')):
            if raw is None: source.unlink()
            else: source.write_bytes(raw)
            with self.store() as store:
                saved = store.load(); app = project_workspace(saved)
                self.assertEqual(status, app.project_source_status)
                self.assertEqual('원래 관찰을 다시 확인해야 한다', app.note())
                self.assertEqual(decode(self.project.payload)['associations'], decode(saved.payload)['associations'])
