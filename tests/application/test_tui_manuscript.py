import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_manuscript import TerminalManuscript, read_source
from claimbranch.application.tui_manuscript_ui import manuscript_ui
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example

SOURCE = ('% Cafe\u0301 untouched\r\n% claimbranch:start id=anchor\nOld wording.\n'
          '% claimbranch:end id=anchor\n% unchanged suffix\r\n').encode()


class ManuscriptTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('recorded', series=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)
        self.now = 1000
        self.app.manuscript = TerminalManuscript(self.app, clock=lambda: self.now)
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None
        self.terminal.screen = Mock()
        self.terminal.screen.getmaxyx.return_value = (42, 144)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'paper.tex'
        self.path.write_bytes(SOURCE)
        self.items = [item for item in self.app.service.pending_work()['items'] if item['kind'] == 'manuscript']

    def open(self, index=0):
        self.ui = manuscript_ui(self.terminal)
        self.ui.open(self.items[index])
        return self.app.manuscript.session

    def write(self):
        self.terminal.key('e')
        self.terminal.key(('paste', '한글: pruning loses 1.2 pp; scope remains limited.'))
        self.terminal.key('tab')
        self.terminal.key(('paste', 'The corrected count exceeds the budget on this split only.'))
        self.terminal.key('keep')
        self.assertEqual('manuscript-read', self.terminal.modal)

    def source(self):
        self.terminal.key('s')
        self.terminal.key(('paste', str(self.path)))
        self.terminal.key('keep')
        self.assertEqual('manuscript-read', self.terminal.modal)

    def frame(self, w=144, h=42):
        return self.terminal.draw_modal(Frame(w, h)).plain()

    def test_pending_work_to_exact_diff_ai_review_and_back_keeps_graph_and_source(self):
        self.app.select('obs-1')
        self.app.graph_pan, self.app.graph_follow = (5, 2), False
        navigation = self.app._navigation()
        self.terminal.key('W'); self.terminal.key('enter'); self.terminal.key('m')
        self.assertEqual('manuscript-read', self.terminal.modal)
        self.ui = manuscript_ui(self.terminal)
        self.source(); self.write(); self.terminal.key('R')
        session = self.app.manuscript.session
        preview = session.get_preview()
        self.assertEqual(SOURCE, preview['source']['before'].encode())
        self.assertIn('-Old wording.', self.frame())
        self.assertIn('+한글:', self.frame())
        for tab in ('before', 'after', 'basis'):
            self.terminal.key('tab')
            self.assertEqual(tab, self.ui.tab)
            self.assertTrue(self.frame(80, 24))
        self.terminal.key('enter')
        self.assertEqual('manuscript-complete', self.terminal.modal)
        self.terminal.key('2')
        self.assertEqual('deferred', session.get_review()['disposition'])
        self.assertFalse(session.get_review()['write_available'])
        self.assertEqual(SOURCE, self.path.read_bytes())
        self.assertEqual(self.original, self.app.paper.history.manifest())
        self.terminal.key('escape'); self.terminal.key('escape'); self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)
        self.assertEqual(navigation, self.app._navigation())
        self.terminal.key('q')
        self.assertEqual('quit', self.terminal.modal)

    def test_changed_deleted_or_invalid_file_revokes_current_review_and_retains_wording(self):
        for change in ('changed', 'deleted', 'invalid'):
            with self.subTest(change=change):
                self.path.write_bytes(SOURCE)
                session = self.open()
                self.app.manuscript.load_source(str(self.path))
                session.draft.edit('New wording.', 'Measured scope only.')
                preview = self.app.manuscript.prepare()
                if change == 'deleted':
                    self.path.unlink()
                else:
                    self.path.write_bytes(SOURCE + b'changed' if change == 'changed' else b'\xff')
                with self.assertRaises((ContractError, OSError)):
                    self.app.manuscript.finish(preview['digest'], 'deferred', [])
                self.assertIsNone(session.get_preview())
                self.assertIsNone(session.get_review())
                self.assertEqual('New wording.', session.state()['draft']['draft']['text'])

    def test_expiry_not_now_and_wording_change_revoke_review(self):
        session = self.open()
        self.source(); self.write(); self.terminal.key('R')
        self.now += 300
        self.terminal.key('enter')
        self.assertIn('Use s', self.ui.notice)
        self.terminal.key('R'); self.terminal.key('x')
        self.assertIsNone(session.get_preview())
        self.assertTrue(session.state()['draft']['draft']['text'])
        self.terminal.key('R')
        session.draft.edit('Another wording.', 'Different scope.')
        self.assertIsNone(session.get_preview())

    def test_unfinished_buffers_and_completed_wording_do_not_leak_between_work_items(self):
        first = self.open(0)
        self.terminal.key('e'); self.terminal.key(('paste', 'unfinished first'))
        self.terminal.key('escape')
        self.assertTrue(self.app.review.volatile_work())
        second = self.open(1)
        self.assertEqual('', second.state()['draft']['draft']['text'])
        self.terminal.key('e')
        self.assertEqual('', self.terminal.buffers[0].text)
        self.terminal.key('escape')
        self.open(0); self.terminal.key('e')
        self.assertEqual('unfinished first', self.terminal.buffers[0].text)
        self.assertEqual('', first.state()['draft']['draft']['text'])
        self.terminal.key('escape')
        self.source(); self.terminal.key('R')
        self.assertIsNone(first.get_preview())
        self.assertTrue(self.ui.notice)

    def test_source_views_preserve_indentation_and_repeated_spaces(self):
        self.path.write_bytes(SOURCE.replace(b'Old wording.', b'    Old   wording.'))
        self.open(); self.source(); self.write(); self.terminal.key('R'); self.terminal.key('tab')
        self.assertIn('    Old   wording.', self.frame())

    def test_source_limits_and_invalid_markers_never_produce_a_preview(self):
        session = self.open()
        session.draft.edit('New wording.', 'Bounded scope.')
        for data in (b'', b'x' * 65537, b'\xff', b'no markers', SOURCE + SOURCE):
            with self.subTest(data=data[:8]):
                self.path.write_bytes(data)
                with self.assertRaises(ContractError):
                    self.app.manuscript.load_source(str(self.path))
                    self.app.manuscript.prepare()
                self.assertIsNone(session.get_preview())
        with self.assertRaises((ContractError, OSError)):
            read_source(self.folder.name)
        self.assertEqual(self.original, self.history.manifest())

    def test_manual_review_needs_no_ai_disposition_and_checkpoint_excludes_wording(self):
        from claimbranch.application.tui_recovery import DraftRecovery
        app = TerminalWorkspace(replay_example('manual', series=True))
        self.app = self.terminal.app = app
        self.terminal._manuscript_ui = self.ui = manuscript_ui(self.terminal)
        self.items = [i for i in app.service.pending_work()['items'] if i['kind'] == 'manuscript']
        self.open(); self.source(); self.write(); self.terminal.key('R'); self.terminal.key('enter')
        self.assertEqual('not-required', app.manuscript.session.get_review()['disposition'])
        recovery_path = Path(self.folder.name) / 'drafts.json'
        app.recovery = DraftRecovery(recovery_path, app)
        try:
            app.recovery.save(app)
            self.assertNotIn('pruning loses', recovery_path.read_text())
            self.terminal.key('escape'); self.terminal.modal = None
            self.terminal.key('q')
            self.assertEqual('quit', self.terminal.modal)
        finally:
            app.recovery.close()


if __name__ == '__main__':
    unittest.main()
