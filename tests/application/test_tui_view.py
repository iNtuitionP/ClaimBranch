import unittest
from claimbranch.application.tui import Terminal, Frame, compose
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_graph import graph_scene
from claimbranch.fixtures import replay_example


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('manual', paper=True))
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None
        self.app.select('obs-1')
        self.app.keep_note('간격을 조절해도 남는 메모')
        self.app.keep_draft('The observed loss is limited to this split.', 'No second mask was run.')
        compose(self.app, 144, 42)

    def test_settings_preview_and_cancel_restore_graph_and_writing_context(self):
        self.app.graph_follow = False
        before, draft = self.app._navigation(), self.app.draft()
        original = self.app.paper.history.manifest()
        self.terminal.key(',')
        self.assertEqual('view-settings', self.terminal.modal)
        self.terminal.key('right')
        self.assertEqual('spacious', self.app.graph_spacing)
        self.terminal.key('down'); self.terminal.key('right')
        self.terminal.key('down'); self.terminal.key('right')
        self.assertEqual('comfortable', self.app.density)
        self.assertTrue(self.app.graph_pinned)
        self.assertIn('VIEW SETTINGS', self.terminal.draw_modal(compose(self.app, 80, 24)).plain())
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())
        self.assertEqual('balanced', self.app.graph_spacing)
        self.assertFalse(self.app.graph_pinned)
        self.assertEqual(draft, self.app.draft())
        self.assertEqual('간격을 조절해도 남는 메모', self.app.note())
        self.assertEqual(original, self.app.paper.history.manifest())

    def test_keep_and_reset_are_explicit_and_spacing_survives_navigation(self):
        base = graph_scene(self.app)
        self.terminal.key(','); self.terminal.key('right'); self.terminal.key('enter')
        compose(self.app, 144, 42)
        self.assertGreater(graph_scene(self.app).height, base.height)
        self.assertEqual('spacious', self.app.graph_spacing)
        self.terminal.key('l'); self.terminal.key('escape')
        self.assertEqual('spacious', self.app.graph_spacing)
        self.terminal.key(','); self.terminal.key('r'); self.terminal.key('escape')
        self.assertEqual('spacious', self.app.graph_spacing)
        self.terminal.key(','); self.terminal.key('r'); self.terminal.key('enter')
        self.assertEqual('balanced', self.app.graph_spacing)
        compose(self.app, 144, 42)
        self.assertEqual(base.boxes, graph_scene(self.app).boxes)

    def test_pin_roundtrip_preserves_an_existing_fullscreen_view(self):
        self.app.graph_pinned = True
        self.app.fit_graph()
        before = self.app._navigation()
        self.terminal.key(',')
        self.terminal.key('down'); self.terminal.key('down')
        self.terminal.key(' '); self.terminal.key(' '); self.terminal.key('enter')
        self.assertTrue(self.app.graph_pinned)
        self.assertEqual(before, self.app._navigation())

    def test_undersized_settings_explain_cancel_and_pause_hidden_controls(self):
        self.terminal.key(',')
        small = self.terminal.draw_modal(compose(self.app, 44, 16)).plain()
        self.assertIn('Esc cancel', small)
        self.terminal.key('right'); self.terminal.key('enter')
        self.assertEqual('balanced', self.app.graph_spacing)
        self.assertEqual('view-settings', self.terminal.modal)
        self.terminal.draw_modal(compose(self.app, 80, 24))
        self.terminal.key('right'); self.terminal.key('enter')
        self.assertEqual('spacious', self.app.graph_spacing)

    def test_paste_and_unintended_keys_cannot_keep_settings_or_execute_actions(self):
        self.terminal.key(',')
        self.terminal.key(('paste', 'q b M C'))
        self.terminal.key('q')
        self.assertEqual('view-settings', self.terminal.modal)
        self.assertEqual('main', self.app.ref)
        self.terminal.key('escape')


if __name__ == '__main__':
    unittest.main()
