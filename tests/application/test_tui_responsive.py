import unittest
from unittest.mock import patch
from types import SimpleNamespace

from claimbranch.application.tui import Terminal, compose
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example
from claimbranch.application.tui_input import Wheel, sgr_wheel
from claimbranch.application.tui_graph import graph_scene


class ResponsiveReadingTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('manual', paper=True))
        self.app.select('obs-1')
        self.app.open_view()
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None

    def test_reader_reuses_projection_and_clamps_before_paint(self):
        with patch.object(self.app, 'detail', wraps=self.app.detail) as detail:
            compose(self.app, 144, 42)
            for _ in range(12):
                self.terminal.key('down')
                compose(self.app, 144, 42)
            self.assertEqual(1, detail.call_count)
            self.terminal.key('end')
            bottom = self.app.scroll
            self.assertGreater(bottom, 0)
            for _ in range(30):
                self.terminal.key('down')
            self.assertEqual(bottom, self.app.scroll)
            self.terminal.key('up')
            self.assertEqual(bottom - 1, self.app.scroll)
            self.terminal.key('home')
            self.assertEqual(0, self.app.scroll)

    def test_note_change_invalidates_reader(self):
        compose(self.app, 144, 42)
        self.app.keep_note('새로 기록한 메모')
        self.terminal.key('end')
        compose(self.app, 144, 42)
        self.assertTrue(any('새로 기록한 메모' in text for text, _ in self.app._reading[1].rows))

    def test_wheel_reversal_at_bottom_and_modal_capture(self):
        self.app.mouse_scroll = True
        self.terminal.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        compose(self.app, 80, 24)
        self.terminal.key('end')
        bottom = self.app.scroll
        for _ in range(200): self.terminal.key(Wheel(30, 10, dy=1))
        self.assertEqual(bottom, self.app.scroll)
        self.terminal.key(Wheel(30, 10, dy=-1))
        self.assertEqual(max(0, bottom - 3), self.app.scroll)
        self.terminal.modal = 'note'
        before = self.app._navigation()
        self.terminal.key(Wheel(30, 10, dy=-1))
        self.assertEqual(before, self.app._navigation())

    def test_sgr_wheel_is_distinct_and_rejects_clicks_or_unbounded_fields(self):
        self.assertEqual(Wheel(9, 19, dy=1), sgr_wheel('[<65;10;20M'))
        self.assertEqual(Wheel(9, 19, dx=-1), sgr_wheel('[<66;10;20M'))
        for report in ('[<0;10;20M', '[<65;10;20m', '[<65;0;20M', '[<65;999999;1M'):
            self.assertIsNone(sgr_wheel(report))

    def test_fragmented_mouse_suffix_cannot_become_commands(self):
        from collections import deque
        from unittest.mock import Mock
        names = ('KEY_UP KEY_DOWN KEY_LEFT KEY_RIGHT KEY_HOME KEY_END KEY_BACKSPACE '
                 'KEY_DC KEY_NPAGE KEY_PPAGE KEY_BTAB KEY_ENTER KEY_RESIZE').split()
        self.terminal.curses = SimpleNamespace(error=TimeoutError,
            **{name: i + 1000 for i, name in enumerate(names)})
        self.terminal.pending, self.terminal.discard_sequence = deque(), False
        self.terminal.mouse = SimpleNamespace(enabled=True, owner='sgr')
        self.terminal.screen = SimpleNamespace(timeout=Mock(), get_wch=Mock(side_effect=[
            '\x1b', '[', '<', '6', TimeoutError(), '5', ';', '1', ';', '2', 'M', '\x13']))
        self.assertIsNone(self.terminal.read(0))
        self.terminal.screen.timeout.assert_called_with(0)
        for _ in range(6): self.assertIsNone(self.terminal.read(0))
        self.assertEqual('keep', self.terminal.read(0))

    def test_split_paste_introducer_retains_the_body_as_text(self):
        from collections import deque
        from unittest.mock import Mock
        names = ('KEY_UP KEY_DOWN KEY_LEFT KEY_RIGHT KEY_HOME KEY_END KEY_BACKSPACE '
                 'KEY_DC KEY_NPAGE KEY_PPAGE KEY_BTAB KEY_ENTER KEY_RESIZE').split()
        self.terminal.curses = SimpleNamespace(error=TimeoutError,
            **{name: i + 1000 for i, name in enumerate(names)})
        self.terminal.pending, self.terminal.discard_sequence = deque(), False
        self.terminal.screen = SimpleNamespace(timeout=Mock(), get_wch=Mock(side_effect=[
            '\x1b', '[', '2', '0', '0', TimeoutError(), '~', *'qM;12', *'\x1b[201~']))
        self.assertIsNone(self.terminal.read(0))
        self.assertEqual(('paste', 'qM;12'), self.terminal.read(0))
        self.terminal.screen.timeout.assert_called_with(0)

    def test_idle_paste_prefix_preserves_controls_and_late_paste_safety(self):
        from collections import deque
        from unittest.mock import Mock
        names = ('KEY_UP KEY_DOWN KEY_LEFT KEY_RIGHT KEY_HOME KEY_END KEY_BACKSPACE '
                 'KEY_DC KEY_NPAGE KEY_PPAGE KEY_BTAB KEY_ENTER KEY_RESIZE').split()
        self.terminal.curses = SimpleNamespace(error=TimeoutError,
            **{name: i + 1000 for i, name in enumerate(names)})
        for control, expected in (('\x03', 'interrupt'), ('\n', 'enter'), ('\x13', 'keep'),
                                  (self.terminal.curses.KEY_LEFT, 'left')):
            self.terminal.pending, self.terminal.discard_sequence = deque(), False
            self.terminal._paste_prefix = '[2'
            self.terminal.screen = SimpleNamespace(timeout=Mock(), get_wch=Mock(side_effect=[TimeoutError(), control]))
            self.assertIsNone(self.terminal.read(0))
            self.assertEqual(expected, self.terminal.read(0))
            self.assertEqual('', self.terminal._paste_prefix)
            self.terminal.screen.timeout.assert_called_with(0)
        self.terminal._paste_prefix = '[2'
        self.terminal.screen.get_wch = Mock(side_effect=['1', '~', 'q'])
        self.assertIsNone(self.terminal.read(0))
        self.assertEqual('q', self.terminal.read(0))
        for sequence, expected in (('\x1b[200~qs\x1b[201~', ('paste', 'qs')),
                                   ('\x1b[<65;10;20M', Wheel(9, 19, dy=1)),
                                   ('\x1b[A', 'up')):
            self.terminal._paste_prefix = '[2'
            self.terminal.mouse = SimpleNamespace(enabled=True, owner='sgr')
            self.terminal.screen.get_wch = Mock(side_effect=list(sequence))
            self.assertEqual(expected, self.terminal.read(0))
        self.terminal._paste_prefix = '[2'
        self.terminal.screen.get_wch = Mock(side_effect=['\x1b', TimeoutError(), 'q'])
        self.assertEqual('escape', self.terminal.read(0))
        self.assertEqual('q', self.terminal.read(0))
        self.terminal.curses.KEY_MOUSE = 2000
        self.terminal.mouse.read = Mock(return_value=Wheel(4, 5, dy=-1))
        self.terminal._paste_prefix = '['
        self.terminal.screen.get_wch = Mock(side_effect=[2000])
        self.assertEqual(Wheel(4, 5, dy=-1), self.terminal.read(0))
        self.assertEqual('[', self.terminal._paste_prefix)
        self.terminal._paste_prefix = '[200'
        self.terminal.screen.get_wch = Mock(side_effect=[self.terminal.curses.KEY_RESIZE,
            '~', *'qM;12', *'\x1b[201~'])
        self.assertEqual('resize', self.terminal.read(0))
        self.assertEqual('[200', self.terminal._paste_prefix)
        self.assertEqual(('paste', 'qM;12'), self.terminal.read(0))
        for control in ('\r', '\t', '\x13', '\x7f'):
            self.terminal.screen.get_wch = Mock(side_effect=['\x1b', control])
            self.assertIsNone(self.terminal.read(0), 'Alt+control must not become an unmodified command')


class ResponsiveGraphTests(unittest.TestCase):
    def test_width_grows_content_and_rank_spacing_without_focus_reflow(self):
        app = TerminalWorkspace(replay_example('manual', paper=True))
        app.collapsed.clear()
        compose(app, 144, 42); normal = graph_scene(app)
        compose(app, 280, 52); wide = graph_scene(app)
        self.assertGreater(wide.boxes['thesis'].width, normal.boxes['thesis'].width)
        self.assertGreater(wide.width, normal.width)
        self.assertTrue(all(box.relation_rows == 0 for box in wide.boxes.values()))
        app.select('obs-1'); compose(app, 280, 52)
        self.assertEqual(wide.boxes, graph_scene(app).boxes)

    def test_source_conditions_and_missing_metrics_are_not_rewritten(self):
        app = TerminalWorkspace(replay_example('manual', paper=True))
        source = 'With noise seed 43, 정확도 차이는 0.004이다.'
        app.nodes['obs-1']['content'].update(statement=source, metric=None)
        app.collapsed.clear(); app.select('obs-1')
        self.assertEqual(source, app.caption('obs-1'))
        text = compose(app, 220, 52).plain()
        self.assertIn('With noise seed 43', text)

    def test_oversized_card_falls_back_to_selected_source_instead_of_empty_map(self):
        from claimbranch.application.tui import Frame
        from claimbranch.application.tui_graph import graph
        app = TerminalWorkspace(replay_example('manual', paper=True))
        frame = Frame(30, 18)
        graph(frame, app, 0, 0, 30, 18)
        self.assertIn('THESIS', frame.plain())
        self.assertIn('Map needs more room', frame.plain())


class ReadableDetailsTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('manual', paper=True))
        self.app.select('obs-1')
        self.table = dict(id='table', estimand='Accuracy change', conditions=[dict(key='seed', value='s1')],
            columns=[dict(id='change', name='Change', type='decimal', raw_unit='fraction', display_unit='percent label')],
            rows=[dict(id='r1', conditions=[], cells=[dict(id='cell-one', column_id='change', value=dict(type='decimal', value='-0.010800'))]),
                  dict(id='r2', conditions=[], cells=[dict(id='cell-two', column_id='change', value=dict(type='missing', reason='artifact not available'))])],
            artifact_refs=[dict(id='artifact', path='owned.json', sha256='a'*64, json_pointer='', commit=None, tool_sha256=None)])
        self.app.nodes['obs-1']['content'].update(measurement=self.table, measurement_revision='revision')

    def test_exact_table_and_missing_reason_in_wide_and_narrow_reading(self):
        for width in (30, 72, 180):
            text = '\n'.join(t for t, _ in self.app.detail(include_links=False, width=width))
            for value in ('-0.010800', 'fraction', 'seed=s1', 'artifact not available', 'owned.json', 'a'*64):
                self.assertIn(value, text)
            self.assertNotIn('"column_id":', text)
            self.assertNotIn('"measurement":', text)
        narrow = '\n'.join(t for t, _ in self.app.detail(width=30))
        self.assertIn('cell-one', narrow)
        self.assertNotIn('artifact not available fraction', narrow)

    def test_table_alignment_survives_reader_wrapping_and_text_cells_are_explicit(self):
        from claimbranch.application.tui_presenters import measurement
        from claimbranch.application.tui_reading import Reading
        reading = Reading(measurement(self.table, 180), 180)
        reading.ensure()
        rows = [text for text, _ in reading.rows if ' │ ' in text]
        self.assertEqual(3, len(rows))
        self.assertEqual(1, len({row.index('│') for row in rows}))
        self.assertIn('[change; fraction]', rows[0])
        self.table['columns'][0]['raw_unit'] = 'fraction\nper trial'
        self.assertNotIn('table', [style for _, style in measurement(self.table, 180)])
        self.table['columns'][0]['raw_unit'] = 'fraction'
        self.table['columns'][0]['type'] = 'text'
        self.table['rows'][0]['cells'][0]['value'] = dict(type='text', value='Missing: quoted text\nsecond line')
        text = '\n'.join(t for t, _ in measurement(self.table, 180))
        self.assertIn('Text: Missing: quoted text', text)
        self.assertNotIn('│', text)

    def test_retained_original_is_requested_only_in_audit_and_unknown_metadata_remains_readable(self):
        c = self.app.nodes['obs-1']['content']
        c['imported_source'] = dict(contributor='mixed', recorded_at=None,
            original_body={'measurement': self.table}, unresolved_pointer_pages=[['/unknown']],
            origin_flags={'human': True, 'ai': True, 'unknown': True})
        c['future_qualification'] = {'reason': 'Must accompany every use'}
        with patch.object(self.app, 'imported_original_source', create=True, return_value='retained original') as original:
            text = '\n'.join(t for t, _ in self.app.detail())
            original.assert_not_called()
            self.assertIn('IMPORTED SOURCE / MIXED', text)
            self.assertIn('/unknown', text)
            self.assertIn('HUMAN, AI, UNKNOWN', text)
            self.assertIn('Must accompany every use', text)
            audit = '\n'.join(t for t, _ in self.app.detail(mode='raw'))
            original.assert_called_once_with('obs-1')
            self.assertIn('retained original', audit)
            self.assertIn('"column_id":', audit)

    def test_raw_connection_reader_retains_each_revision(self):
        edge = next(e for e in self.app.view['relations'] if e['scientific'] and e['source_id'] == 'obs-1')
        edge['graph_revisions'] = [{'rationale': 'Exact earlier connection reason'}]
        edge['imported_source'] = dict(contributor='unknown', recorded_at=None, original_body={},
            unresolved_pointer_pages=[], origin_flags={'human': True, 'ai': False, 'unknown': True})
        self.app.reading_relation = True
        self.app.link_index = next(i for i, link in enumerate(self.app.display_links()) if link.key == edge['key'])
        with patch.object(self.app, 'imported_original_source', create=True, return_value='Original edge ledger') as original:
            self.assertIn('HUMAN, UNKNOWN', str(self.app.relationship_detail()))
            original.assert_not_called()
            audit = '\n'.join(t for t, _ in self.app.detail(mode='raw'))
            self.assertIn('Exact earlier connection reason', audit)
            self.assertIn('Original edge ledger', audit)
            original.assert_called_once_with(edge['record_id'])


class ConciseHelpTests(unittest.TestCase):
    def test_keys_fit_small_terminal_topics_are_opt_in_and_return_preserves_context(self):
        from claimbranch.application.tui import Frame
        app = TerminalWorkspace(replay_example('manual', paper=True))
        app.select('obs-1'); app.keep_note('보존할 메모')
        term = Terminal.__new__(Terminal); term.app, term.modal = app, None
        before = app._navigation()
        term.key('?')
        frame = term.draw_modal(Frame(80, 24)).plain()
        for value in ('KEYS', 'Enter', 'Argument / experiments', 'Write note / judgment', 'Tab topics'):
            self.assertIn(value, frame)
        self.assertNotIn('HELP TOPICS', frame)
        term.key(';'); self.assertEqual('actions', term.modal)
        term.key('escape'); term.key('?')
        term.key('tab'); self.assertIn('HELP TOPICS', term.draw_modal(Frame(80, 24)).plain())
        term.key('enter'); term.draw_modal(Frame(80, 24))
        term.key('escape'); term.key('escape'); term.key('escape')
        self.assertIsNone(term.modal)
        self.assertEqual(before, app._navigation())
        self.assertEqual('보존할 메모', app.note())

    def test_relation_text_is_never_clipped_like_a_graph_preview(self):
        from claimbranch.application.tui_reading import Reading
        text = 'supports → ' + 'full source rationale ' * 20
        reading = Reading([(text, 'body')], 30, relation=True)
        reading.ensure()
        self.assertNotIn('…', ''.join(t for t, _ in reading.rows))
        self.assertIn('rationale', reading.rows[-1][0])


if __name__ == '__main__':
    unittest.main()
