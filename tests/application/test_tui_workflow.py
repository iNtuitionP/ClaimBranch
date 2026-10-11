"""Research reading/editing outcomes, independent of a pixel-perfect layout."""
import unittest
from unittest.mock import Mock

from claimbranch.application.tui import Buffer, Terminal, compose, panes, render_snapshot
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example


class ReadingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('manual', paper=True))
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None
        self.terminal.screen = Mock()
        self.terminal.screen.getmaxyx.return_value = (24, 80)

    def test_read_then_back_closes_view_before_undoing_node_traversal(self):
        self.terminal.key('j')
        selected = self.app.selected_id
        self.app.graph_pan, self.app.graph_follow = (12, 4), False
        self.terminal.key('enter')
        self.app.scroll = 9
        self.terminal.key('escape')
        self.assertEqual((selected, 'outline', (12, 4), False),
                         (self.app.selected_id, self.app.focus, self.app.graph_pan, self.app.graph_follow))
        self.terminal.key('escape')
        self.assertEqual('thesis', self.app.selected_id)

    def test_reader_opens_on_demand_and_narrow_reader_uses_full_width(self):
        before = panes(self.app, 156, 48)
        self.assertEqual(['outline'], [p[0] for p in before])
        self.terminal.key('enter')
        opened = panes(self.app, 156, 48)
        self.assertEqual(['outline', 'detail'], [p[0] for p in opened])
        self.terminal.key('d')
        self.assertEqual(opened, panes(self.app, 156, 48))
        self.assertEqual(['detail'], [p[0] for p in panes(self.app, 80, 24)])

    def test_small_evidence_reader_exposes_result_and_both_named_uses_before_scrolling(self):
        self.app.select('obs-1')
        self.terminal.key('enter')
        frame = render_snapshot(self.app, 80, 24)
        self.assertIn('0.4 percentage points', frame)
        for link in self.app.claim_uses():
            self.assertIn('supports → ' + self.app.node_label(link.target_id), frame)
        self.assertIn('conditions', frame.lower())

    def test_editor_cancel_retains_unapplied_buffer_without_changing_kept_note(self):
        class Screen:
            def getmaxyx(self): return 48, 156
        self.terminal.screen = Screen()
        self.app.keep_note('kept')
        self.terminal.key('n')
        self.terminal.key(('paste', ' 새 생각'))
        self.terminal.key('escape')
        self.assertEqual('kept', self.app.note())
        self.terminal.key('N')
        self.assertEqual('kept 새 생각', self.terminal.buffers[0].text)
        self.terminal.key('keep')
        self.assertEqual('kept 새 생각', self.app.note())

    def test_edit_undo_redo_and_limit_feedback(self):
        buffer = Buffer('한글')
        buffer.key(('paste', '\ncontext'), 40)
        buffer.key('undo', 40)
        self.assertEqual('한글', buffer.text)
        buffer.key('redo', 40)
        self.assertEqual('한글\ncontext', buffer.text)
        buffer.insert('x' * 12000)
        self.assertEqual(12000, len(buffer.text))
        self.assertIn('12,000', buffer.notice)
        buffer.key('undo', 40)
        self.assertEqual('한글\ncontext', buffer.text)

    def test_checkpoint_failure_is_visible_inside_editor_and_normal_quit_stays_open(self):
        class Recovery:
            def save(self, app, active): raise OSError('full disk')
        self.app.recovery = Recovery()
        self.terminal.key('n')
        self.terminal.buffers[0].insert('keep this text')
        self.assertFalse(self.terminal.checkpoint())
        frame = self.terminal.draw_modal(compose(self.app, 156, 48)).plain()
        self.assertIn('Draft save failed', frame)
        self.assertEqual('keep this text', self.terminal.buffers[0].text)
        self.terminal.key('escape')
        self.assertIsNone(self.terminal.key('q'))
        self.assertIn('keep this text', self.app.unfinished[('main', 'thesis', 'note')])

    def test_note_cancel_restores_overview_pan_and_tab_read_has_a_return_step(self):
        self.terminal.key('f')
        self.app.graph_pan, self.app.graph_follow = (12, 2), False
        before = self.app._navigation()
        self.terminal.key('n')
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())
        self.terminal.key('tab')
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())

    def test_unchanged_cancel_does_not_replace_previous_unfinished_text(self):
        self.terminal.key('n')
        self.terminal.buffers[0].insert('recover me')
        self.terminal.key('escape')
        self.terminal.key('n')
        self.terminal.key('escape')
        self.terminal.key('N')
        self.assertEqual('recover me', self.terminal.buffers[0].text)
        self.terminal.key('escape')
        self.app.unfinished.clear()
        self.terminal.key('n')
        self.terminal.key('escape')
        self.assertEqual(0, self.terminal.key('q'))

    def test_search_then_read_returns_to_graph_before_clearing_search(self):
        self.app.search = 'obs-1'
        self.app.select('obs-1', reveal=False)
        self.assertIn('Search: obs-1', render_snapshot(self.app, 80, 24))
        self.terminal.key('enter')
        self.terminal.key('escape')
        self.assertEqual(('outline', 'obs-1', 'obs-1'),
                         (self.app.focus, self.app.selected_id, self.app.search))
        self.terminal.key('escape')
        self.assertEqual('', self.app.search)

    def test_unfinished_picker_finds_other_nodes_and_branches(self):
        self.app.unfinished[('alternative', 'obs-2', 'note')] = ['다른 노드의 초안']
        self.terminal.key('U')
        frame = self.terminal.draw_modal(compose(self.app, 80, 24)).plain()
        self.assertIn('alternative / obs-2', frame)
        self.assertIn('Note', frame)
        self.assertIn('다른 노드의 초안', frame)
        self.terminal.key('enter')
        self.assertEqual(('alternative', 'obs-2', 'note'), (self.app.ref, self.app.selected_id, self.terminal.modal))
        self.assertEqual('다른 노드의 초안', self.terminal.buffers[0].text)


if __name__ == '__main__':
    unittest.main()
