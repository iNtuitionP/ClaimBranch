"""Explicit project-source changes keep scientific writing on its original basis."""
from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.project_work import preview_association
from claimbranch.application.tui_project import prepare_project, project_workspace, ProjectRecovery
from claimbranch.application.tui_project_source import prepare_source_change, apply_source_change, ProjectSourceUI
from claimbranch.application.tui import Terminal, Frame
from claimbranch.core.canonical import ContractError, decode


class ProjectSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.paper, self.directory = self.root / 'paper', self.root / 'work'
        self.paper.mkdir(); self.directory.mkdir(mode=0o700)
        subprocess.run(['git', 'init', '-q', str(self.paper)], check=True)
        self.raw = b'% claimbranch:start id=anchor\nOriginal.\n% claimbranch:end id=anchor\n'
        (self.paper / 'paper.tex').write_bytes(self.raw)
        preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
        self.project = prepare_project(preview, project_id='new-paper', title='Study', thesis='Tentative thesis', question='Which condition?')
        self.app = project_workspace(self.project)
        self.saved = []
        self.store = SimpleNamespace(_path=self.directory, save=lambda value, **kwargs: self.saved.append(value), verify_unchanged=lambda: None)
        self.app.recovery = ProjectRecovery(self.store, self.app, self.project)
        self.app.keep_note('기존 노트')
        self.app.recovery.save(self.app)
        self.project = self.app.recovery.project
        self.saved.clear()
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal, self.terminal.buffers = self.app, None, []
        self.size = (24, 80)
        self.terminal.screen = SimpleNamespace(getmaxyx=lambda: self.size)
        self.ui = ProjectSourceUI(self.terminal)

    def test_relocation_and_refresh_preserve_exact_nested_work(self):
        moved = self.root / 'moved'; self.paper.rename(moved)
        change = prepare_source_change(self.project, self.directory, 'relocate', paper_root=moved, manuscript='paper.tex')
        self.assertEqual(self.project.work.payload, change.project.work.payload)
        self.assertEqual([], self.saved)
        apply_source_change(self.app, change)
        self.assertEqual(change.project.payload, self.app.recovery.project.payload)
        self.assertEqual('기존 노트', self.app.note())
        (moved / 'paper.tex').write_bytes(self.raw + b'% edit\n')
        old = self.app.recovery.project
        refresh = prepare_source_change(old, self.directory, 'refresh')
        self.assertNotEqual(refresh.before['source_digest'], refresh.after['source_digest'])
        self.assertEqual(old.work.payload, refresh.project.work.payload)
        apply_source_change(self.app, refresh)
        self.assertEqual('unchanged-since-refresh', self.app.project_source_status)
        self.assertEqual(old.work.payload, self.app.recovery.project.work.payload)

    def test_stale_source_and_work_refuse_before_save(self):
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% edit\n')
        change = prepare_source_change(self.project, self.directory, 'refresh')
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% another edit\n')
        with self.assertRaises(ContractError): apply_source_change(self.app, change)
        self.assertEqual([], self.saved)
        change = prepare_source_change(self.project, self.directory, 'refresh')
        self.app.keep_note('Later writing'); self.app.recovery.save(self.app); self.saved.clear()
        with self.assertRaises(ContractError): apply_source_change(self.app, change)
        self.assertEqual([], self.saved)
        self.assertEqual('Later writing', self.app.note())

    def test_ui_cancel_tiny_screen_paste_and_explicit_apply(self):
        before = self.app._navigation()
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% edit\n')
        self.ui.open(); self.ui.key('f')
        self.assertEqual('project-source-preview', self.terminal.modal)
        self.ui.key(('paste', 'a')); self.ui.key('enter')
        self.assertEqual([], self.saved)
        self.ui.draw(Frame(80, 24)); self.ui.key('end'); self.ui.draw(Frame(80, 24))
        self.size = (16, 40); self.ui.key('a')
        self.assertEqual([], self.saved)
        self.assertIn('paused', self.ui.draw(Frame(40, 16)).plain())
        self.size = (24, 80); self.ui.key('escape')
        self.assertEqual([], self.saved)
        self.ui.key('f'); self.ui.draw(Frame(80, 24)); self.ui.key('end'); self.ui.draw(Frame(80, 24)); self.ui.key('a')
        self.assertEqual(1, len(self.saved))
        self.ui.key('escape')
        self.assertIsNone(self.terminal.modal)
        self.assertEqual(before, self.app._navigation())
        self.assertEqual('기존 노트', self.app.note())

    def test_changed_bytes_cannot_be_relocated_and_save_failure_keeps_project(self):
        moved = self.root / 'moved'; self.paper.rename(moved)
        (moved / 'paper.tex').write_bytes(self.raw + b'% edit\n')
        with self.assertRaises(ContractError):
            prepare_source_change(self.project, self.directory, 'relocate', paper_root=moved, manuscript='paper.tex')
        (moved / 'paper.tex').write_bytes(self.raw)
        change = prepare_source_change(self.project, self.directory, 'relocate', paper_root=moved, manuscript='paper.tex')
        with patch.object(self.store, 'save', side_effect=ContractError('save refused')):
            with self.assertRaises(ContractError): apply_source_change(self.app, change)
        self.assertEqual(self.project.payload, self.app.recovery.project.payload)
        self.assertEqual('기존 노트', self.app.note())

    def test_exact_path_input_preserves_unicode_and_rejects_pasted_commands(self):
        from claimbranch.application.tui_project_source import exact_path_buffer
        name = 'e\u0301-paper'
        moved = self.root / name; self.paper.rename(moved)
        buffer = exact_path_buffer('')
        buffer.key(('paste', str(moved)), 72)
        self.assertEqual(os.fsencode(moved), os.fsencode(buffer.text))
        buffer.key(('paste', '\na\x1b[31m'), 72)
        self.assertEqual(str(moved), buffer.text)
        self.assertIn('nothing was inserted', buffer.notice)
        change = prepare_source_change(self.project, self.directory, 'relocate', paper_root=buffer.text, manuscript='paper.tex')
        self.assertEqual(os.fsencode(moved.resolve()), os.fsencode(change.after['paper_root']))
        self.assertEqual(self.raw, (moved / 'paper.tex').read_bytes())

    def test_named_action_and_dispatch_failure_keep_graph_and_preview_cancel(self):
        from claimbranch.application.tui_actions import actions_ui
        self.terminal.key(';')
        ui = actions_ui(self.terminal)
        ui.index = next(i for i, item in enumerate(ui.items()) if item.title == 'Paper connection')
        self.terminal.key('enter')
        self.assertEqual('project-source', self.terminal.modal)
        self.terminal.key('f')
        self.assertIn('not confirmed', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('r')
        self.terminal.key(('paste', str(self.paper)))
        self.terminal.key('enter')
        self.assertEqual('project-source-location', self.terminal.modal)
        self.assertEqual([], self.saved)
        self.terminal.key('escape'); self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)

    @unittest.skipUnless(__import__('sys').platform == 'darwin', 'Mac device work required')
    def test_native_source_changes_reopen_same_writing_and_refuse_stale_preview(self):
        from claimbranch.application.project_work import ProjectWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        with MacWorkCipher() as cipher:
            with ProjectWorkStore.create(self.directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
                store.save(self.project, preview=preview)
                self.app.recovery = ProjectRecovery(store, self.app, self.project)
                original_work = self.project.work.payload
                moved = self.root / 'moved'; self.paper.rename(moved)
                before = (self.directory / 'work.cbw').read_bytes()
                change = prepare_source_change(self.project, self.directory, 'relocate', paper_root=moved, manuscript='paper.tex')
                self.assertEqual(before, (self.directory / 'work.cbw').read_bytes())
                apply_source_change(self.app, change)
                (moved / 'paper.tex').write_bytes(self.raw + b'% first edit\n')
                refresh = prepare_source_change(self.app.recovery.project, self.directory, 'refresh')
                before = (self.directory / 'work.cbw').read_bytes()
                (moved / 'paper.tex').write_bytes(self.raw + b'% second edit\n')
                with self.assertRaises(ContractError): apply_source_change(self.app, refresh)
                self.assertEqual(before, (self.directory / 'work.cbw').read_bytes())
                refresh = prepare_source_change(self.app.recovery.project, self.directory, 'refresh')
                apply_source_change(self.app, refresh)
                self.assertEqual(original_work, self.app.recovery.project.work.payload)
            with ProjectWorkStore(self.directory, cipher=cipher, project_id='new-paper') as store:
                reopened = store.load()
                self.assertEqual(original_work, reopened.work.payload)
                self.assertEqual(3, len(decode(reopened.payload)['associations']))
                self.assertEqual('기존 노트', project_workspace(reopened).note())
                self.assertEqual('unchanged-since-refresh', reopened.source_status())

    def test_failed_apply_needs_new_preview_and_check_updates_source_warning(self):
        from claimbranch.application.tui import compose
        self.ui.open()
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% changed\n')
        self.ui.key('c')
        self.assertIn('SOURCE CHECK:', compose(self.app, 80, 24).plain())
        self.ui.key('f'); self.ui.draw(Frame(80, 24)); self.ui.key('end'); self.ui.draw(Frame(80, 24))
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% later change\n')
        self.ui.dispatch('a')
        self.assertIsNone(self.ui.change)
        self.assertIn('not confirmed', self.ui.notice)
        self.ui.dispatch('a')
        self.assertEqual([], self.saved)
        self.assertEqual(self.project.payload, self.app.recovery.project.payload)
        self.ui.key('escape'); self.ui.key('f')
        self.assertFalse(self.ui.seen_end)

    def test_minimum_width_keeps_all_connection_shortcuts_visible(self):
        self.ui.open()
        self.assertIn('r relocate · f refresh · c check · Esc', self.ui.draw(Frame(48, 18)).plain())

    def test_long_path_cursor_stays_visible_without_changing_exact_text(self):
        from claimbranch.application.tui_project_source import quoted
        self.ui.open(); self.ui.key('r')
        raw = '/' + '한글경로/' * 45
        self.ui.key(('paste', raw))
        frame = self.ui.draw(Frame(80, 24))
        self.assertTrue(5 <= frame.cursor[0] <= 7)
        for _ in range(100): self.ui.key('left')
        frame = self.ui.draw(Frame(80, 24))
        self.assertTrue(5 <= frame.cursor[0] <= 7)
        self.assertEqual(raw, self.ui.paths[0].text)
        self.assertIn('한글', quoted('한글\x1b\u202e'))
        self.assertIn('\\u202e', quoted('한글\x1b\u202e'))

    @unittest.skipUnless(__import__('sys').platform == 'darwin', 'Mac device work required')
    def test_uncertain_native_save_never_claims_not_applied_or_retries(self):
        from claimbranch.application.project_work import ProjectWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        with MacWorkCipher() as cipher:
            with ProjectWorkStore.create(self.directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                preview = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
                store.save(self.project, preview=preview)
                self.app.recovery = ProjectRecovery(store, self.app, self.project)
                (self.paper / 'paper.tex').write_bytes(self.raw + b'% edited\n')
                self.ui.open(); self.ui.key('f'); self.ui.draw(Frame(80, 24)); self.ui.key('end'); self.ui.draw(Frame(80, 24))
                sync = store._sync
                def fail_directory_sync(fd):
                    if fd == store._dir: raise OSError('Injected directory durability failure')
                    return sync(fd)
                with patch.object(store, '_sync', side_effect=fail_directory_sync):
                    self.ui.dispatch('a')
                self.assertIn('not confirmed', self.ui.notice)
                self.assertIn('uncertain', self.ui.notice)
                self.assertIsNone(self.ui.change)
                with self.assertRaisesRegex(ContractError, 'uncertain'): store.verify_unchanged()
                self.assertEqual(self.project.payload, self.app.recovery.project.payload)
            with ProjectWorkStore(self.directory, cipher=cipher, project_id='new-paper') as store:
                reopened = store.load()
                self.assertEqual(self.project.work.payload, reopened.work.payload)
                self.assertEqual(2, len(decode(reopened.payload)['associations']))

    def test_path_home_uses_displayed_row_width(self):
        self.size = (30, 120)
        self.ui.open(); self.ui.key('r'); self.ui.key(('paste', '/' + 'x' * 114))
        self.ui.draw(Frame(120, 30)); self.ui.key('home')
        self.assertEqual(100, self.ui.paths[0].cursor)
        self.assertEqual((6, 3), self.ui.draw(Frame(120, 30)).cursor)

    def test_joiner_path_and_line_separator_handling_is_exact(self):
        from claimbranch.application.tui_project_source import exact_path_buffer, quoted
        buffer = exact_path_buffer('')
        text = '/paper\u200cname'
        buffer.key(('paste', text), 74)
        self.assertEqual(text, buffer.text)
        buffer.key(('paste', '\u2028stray'), 74)
        self.assertEqual(text, buffer.text)
        self.assertIn('\\u2028', quoted('/paper\u2028name'))
        self.assertIn('\\u00a0', quoted('/paper\u00a0name'))

    def test_second_refresh_keeps_format_and_shows_remaining_capacity(self):
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% first\n')
        self.ui.open(); self.ui.key('f')
        self.assertIn('v3 project reader', '\n'.join(self.ui.content()))
        self.assertIn('Source changes remaining after this: 14', self.ui.content())
        self.ui.draw(Frame(144, 42)); self.ui.key('a')
        (self.paper / 'paper.tex').write_bytes(self.raw + b'% second\n')
        self.ui.key('f')
        self.assertNotIn('Older v1-only', '\n'.join(self.ui.content()))
        self.assertIn('Source changes remaining after this: 13', self.ui.content())

    def test_interrupt_is_not_swallowed_by_connection_modals(self):
        self.ui.open()
        for mode in ('project-source', 'project-source-location', 'project-source-preview'):
            self.terminal.modal = mode
            self.assertEqual(130, self.terminal.key('interrupt'))
        self.assertEqual([], self.saved)
