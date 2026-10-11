"""Full relationship phrases remain inside cards, separate from route lanes."""
import unittest

from claimbranch.application.tui import compose
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_graph import graph_scene
from claimbranch.fixtures import replay_example


class PortTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.app = TerminalWorkspace(self.history)

    def test_relationship_phrases_state_both_directions(self):
        from claimbranch.application.tui_graph import relation_phrase
        expected = {
            'supports': ('supports E1', 'supported by E1'),
            'challenges': ('challenges E1', 'challenged by E1'),
            'qualifies': ('qualifies E1', 'qualified by E1'),
            'part-of': ('part of E1', 'contains E1'),
            'produced': ('produced E1', 'produced by E1'),
            'interprets': ('interprets E1', 'interpreted by E1'),
            'tests': ('tests E1', 'tested by E1'),
            'expresses': ('expresses E1', 'expressed by E1'),
        }
        for kind, (active, passive) in expected.items():
            edge = {'type': kind, 'source_id': 'a', 'target_id': 'b'}
            self.assertEqual(active, relation_phrase(edge, 'a', 'E1'))
            self.assertEqual(passive, relation_phrase(edge, 'b', 'E1'))

    def test_parallel_relations_get_separate_full_phrases_without_moving_cards(self):
        from claimbranch.application.tui_graph import relation_lines, header_relations, node_heading
        compose(self.app, 144, 42)
        before = graph_scene(self.app).boxes
        self.app.select('claim-pruning-detail')
        scene = graph_scene(self.app)
        _, focused = scene.focus(self.app.selected_id)
        rows = relation_lines(self.app, scene, 'claim-pruning', focused)
        self.assertIn('supported by C3', [text for text, style in rows])
        self.assertIn('contains C3', [text for text, style in rows])
        self.assertGreaterEqual(scene.boxes['claim-pruning'].relation_rows, len(rows))
        for route in scene.routes:
            if route.edge['source_id'] == 'claim-pruning-detail' and route.edge['target_id'] == 'claim-pruning':
                exact = relation_lines(self.app, scene, 'claim-pruning', {route.edge['key']})
                self.assertEqual(1, len(exact))
        compose(self.app, 144, 42)
        self.assertEqual(before, graph_scene(self.app).boxes)

    def test_neighbor_cards_explain_relations_without_a_code_key(self):
        self.app.select('obs-1')
        frame = compose(self.app, 144, 42)
        text = frame.plain()
        self.assertIn('supported by E1', text)
        self.assertIn('produced E1', text)
        self.assertIn('interprets E1', text)
        self.assertNotIn('S supports', text)
        self.assertNotIn('╳', text)
        self.assertEqual(self.history.manifest(), self.app.paper.history.manifest())
        scene = graph_scene(self.app)
        for box in scene.boxes.values():
            self.assertGreaterEqual(box.height - box.relation_rows - 2, 2)

    def test_run_relation_is_beside_title_and_source_stays_below_header(self):
        self.app.select('obs-1')
        frame = compose(self.app, 144, 42)
        lines = frame.plain().splitlines()
        heading = next(index for index, text in enumerate(lines) if 'R1 RUN' in text)
        self.assertIn('produced E1', lines[heading])
        self.assertIn('Prune / 8-bit', lines[heading + 1])
        self.assertNotIn('produced E1', lines[heading + 1])
        self.assertTrue(any(style == 'relation_accent' and char.isalpha() for char, style in frame.cells[heading]))

    def test_header_fallback_preserves_full_parallel_phrases(self):
        from claimbranch.application.tui_graph import header_relations
        phrases = [('supported by E1', 'supports'), ('contains E1', 'accent')]
        positions = header_relations(' C3 SUBCLAIM', phrases, 24)
        self.assertEqual([(0, 1, 'supported by E1', 'supports'), (0, 2, 'contains E1', 'accent')], positions)

    def test_corrected_evidence_names_its_challenge_in_full(self):
        app = TerminalWorkspace(replay_example('recorded', series=True))
        app.select('obs-1')
        self.assertIn('challenged by E1', compose(app, 144, 42).plain())

    def test_vertical_routes_keep_a_visible_shaft_at_wide_and_narrow_sizes(self):
        for size, local in (((144, 42), False), ((120, 30), False), ((80, 24), True)):
            for series in (False, True):
                with self.subTest(size=size, series=series):
                    app = TerminalWorkspace(replay_example('recorded', series=series, paper=not series))
                    app.select('obs-1')
                    if local:
                        app.scope_graph('obs-1')
                    frame = compose(app, *size)
                    if series and size == (144, 42):
                        self.assertTrue(any(frame.cells[y][x] == ('▲', 'challenges') and
                                            frame.cells[y + 1][x] == ('│', 'challenges')
                                            for y in range(frame.height - 1) for x in range(frame.width)))
                    scene = graph_scene(app)
                    route = next(r for r in scene.routes if r.edge['source_id'] == 'obs-1'
                                 and r.edge['target_id'] == 'claim-pruning-detail')
                    self.assertEqual(1, len({x for x, y in route.points}))
                    self.assertGreaterEqual(abs(route.points[-1][1] - route.points[0][1]), 2)
                    before = scene.boxes
                    app.select('claim-pruning-detail')
                    compose(app, *size)
                    self.assertEqual(before, graph_scene(app).boxes)

    def test_selected_route_wins_over_an_unrelated_crossing_without_a_false_junction(self):
        from claimbranch.application.tui_graph import visible_stroke
        strokes = {'horizontal': 10, 'vertical': 5}
        self.assertEqual(('vertical', '│'), visible_stroke(strokes, {'vertical'}, 'vertical'))
        self.assertEqual(('horizontal', '─'), visible_stroke(strokes, {'horizontal'}, None))
        self.assertEqual(('horizontal', '─'), visible_stroke(strokes, set(), None))
        self.assertEqual(('turn', '└'), visible_stroke({'turn': 3, 'other': 12}, {'turn'}, 'turn'))

    def test_only_a_recorded_common_port_stub_can_join_turns(self):
        from claimbranch.application.tui_graph import visible_stroke
        strokes = {'a': 10, 'b': 12}
        self.assertEqual(('a', '┬'), visible_stroke(strokes, {'a', 'b'}, None, [frozenset({'a', 'b'})]))
        self.assertEqual(('b', '┐'), visible_stroke(strokes, {'a', 'b'}, 'b', [frozenset({'a', 'b'})]))
        self.assertEqual(('a', '─'), visible_stroke(strokes, {'a', 'b'}, None))

    def test_shared_stub_detection_stops_at_each_routes_first_turn(self):
        from claimbranch.application.tui_graph import Box, Route, Scene, shared_stubs
        a = {'key': 'a', 'source_id': 'source', 'target_id': 'one'}
        b = {'key': 'b', 'source_id': 'source', 'target_id': 'two'}
        scene = Scene({'source': Box(-18, 0, 18, 4), 'one': Box(9, 2, 18, 4), 'two': Box(9, 6, 18, 4)},
                      (Route(a, ((0, 1), (4, 1), (4, 3), (8, 3)), 0, 0),
                       Route(b, ((0, 1), (2, 1), (2, 7), (8, 7)), 0, 0)), 30, 12)
        stubs = shared_stubs(scene, (0, 0, 30, 12))
        self.assertEqual([frozenset({'a', 'b'})], stubs[(2, 1)])
        self.assertNotIn((3, 1), stubs)
        self.assertNotIn((4, 3), stubs)

    def test_long_aliases_wrap_inside_reserved_rows_without_changing_source_capacity(self):
        from claimbranch.application.tui_graph import relation_lines, header_relations, node_heading
        compose(self.app, 120, 42)  # Populate the cache before aliases change.
        original_label = self.app.node_label
        self.app.node_label = lambda key: original_label(key) + '12345678901234567890'
        self.app.select('obs-1')
        compose(self.app, 120, 42)
        scene = graph_scene(self.app)
        _, focused = scene.focus('obs-1')
        rows = relation_lines(self.app, scene, 'claim-comparison', focused)
        self.assertEqual('supportedbyE112345678901234567890', ''.join(text.replace(' ', '') for text, _ in rows))
        positions = header_relations(node_heading(self.app, 'claim-comparison'), rows, scene.boxes['claim-comparison'].width - 2)
        self.assertGreater(len(positions), 1)
        for key, box in scene.boxes.items():
            self.assertLessEqual(max((dy for _, dy, _, _ in header_relations(node_heading(self.app, key), relation_lines(self.app, scene, key, focused), box.width - 2)), default=0), box.relation_rows)
            self.assertEqual(2, box.height - box.relation_rows - 2)

    def test_live_resize_uses_the_same_geometry_as_a_fresh_frame(self):
        compose(self.app, 120, 32)
        compose(self.app, 120, 30)
        fresh = TerminalWorkspace(self.history)
        compose(fresh, 120, 30)
        self.assertEqual(graph_scene(fresh).boxes, graph_scene(self.app).boxes)

    def test_cached_scene_does_not_rewrap_every_relation(self):
        from unittest.mock import patch
        compose(self.app, 144, 42)
        scene = graph_scene(self.app)
        self.app.select('obs-1')
        compose(self.app, 144, 42)
        with patch('claimbranch.application.tui_graph.wrap', side_effect=AssertionError('cached layout rewrapped')):
            self.assertIs(scene, graph_scene(self.app))

    def test_unlinked_node_never_claims_an_outside_connection(self):
        from copy import deepcopy
        node = deepcopy(self.app.nodes['obs-1'])
        node['id'] = 'unlinked'
        self.app.nodes[node['id']] = node
        self.app.view['nodes'].append(node)
        self.app._build_outline()
        self.app.select('unlinked')
        text = compose(self.app, 144, 42).plain()
        self.assertIn('No recorded connections', text)
        self.assertNotIn('Connection outside this view', text)


if __name__ == '__main__':
    unittest.main()
