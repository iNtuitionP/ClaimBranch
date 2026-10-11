"""Map comprehension prerequisites and reversible graph scope, using real frames."""
from copy import deepcopy
import unittest

from claimbranch.application.tui import Terminal, panes, render_snapshot
from claimbranch.application.tui_graph import graph_scene
from claimbranch.application.tui_model import TerminalWorkspace, cell_width
from claimbranch.fixtures import replay_example


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None

    def test_full_map_initially_shows_all_ten_nodes_at_research_terminal_sizes(self):
        for width, height in ((144, 42), (120, 32)):
            for selected in ('thesis', 'obs-1'):
                with self.subTest(size=(width, height), selected=selected):
                    self.app.select(selected)
                    frame = render_snapshot(self.app, width, height)
                    self.assertEqual(['outline'], [p[0] for p in panes(self.app, width, height)])
                    self.assertEqual(10, frame.count('╭'))
                    self.assertIn('10/10 visible', frame)
                    self.assertIn('UNRUN', frame)
                    self.assertIn('0.4 pp', frame)
                    self.assertIn('0.7 pp', frame)
                    self.assertTrue(all(cell_width(line) <= width for line in frame.splitlines()))
        self.assertEqual(self.original, self.history.manifest())

    def test_note_presence_never_replaces_overview_subject_or_result(self):
        self.app.select('obs-1')
        self.app.keep_note('한글 메모 ' * 100)
        frame = render_snapshot(self.app, 120, 30)
        self.assertIn('20% pruning', frame)
        self.assertIn('loss 0.4 pp', frame)
        self.assertIn('✎', frame)
        self.assertNotIn('한글 메모', frame)
        self.terminal.key('enter')
        self.assertIn('한글 메모', '\n'.join(text for text, _ in self.app.detail()))
        self.assertEqual(self.original, self.history.manifest())

    def test_compact_display_copy_does_not_survive_a_source_change(self):
        self.app.nodes['claim-comparison']['content']['statement'] = '새 비교: 가지치기가 더 나쁘다.'
        self.app.select('claim-comparison')
        frame = render_snapshot(self.app, 144, 42)
        self.assertIn('새 비교', frame)
        self.assertNotIn('Prune vs 8-bit', frame)
        self.terminal.key('enter')
        self.assertIn('새 비교: 가지치기가 더 나쁘다.', render_snapshot(self.app, 144, 42))

    def test_search_matches_the_visible_compact_caption(self):
        self.app.search = 'loss 0.4 pp'
        self.assertIn('obs-1', self.app.matching_ids())
        self.assertNotIn('obs-2', self.app.matching_ids())

    def test_fit_opens_full_map_and_escape_restores_reading_and_pan(self):
        self.app.select('obs-1')
        self.terminal.key('enter')
        self.app.graph_pan, self.app.graph_follow = (9, 2), False
        self.app.scroll = 4
        before = self.app._navigation()
        self.terminal.key('f')
        frame = render_snapshot(self.app, 144, 42)
        self.assertIn('10/10 visible', frame)
        self.assertEqual((0, 0), self.app.graph_pan)
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())

    def test_optional_pinned_reader_and_selection_do_not_rearrange_graph(self):
        self.terminal.key('P')
        self.assertEqual(['outline', 'detail'], [p[0] for p in panes(self.app, 156, 48)])
        render_snapshot(self.app, 156, 48)
        scene = graph_scene(self.app)
        self.app.select('obs-1')
        render_snapshot(self.app, 156, 48)
        self.assertEqual(scene, graph_scene(self.app))
        self.terminal.key('enter')
        self.terminal.key('escape')
        self.assertEqual(['outline', 'detail'], [p[0] for p in panes(self.app, 156, 48)])
        self.terminal.key('P')
        self.assertEqual(['outline'], [p[0] for p in panes(self.app, 156, 48)])

    def test_pin_while_reading_survives_close_and_resize(self):
        self.terminal.key('enter')
        self.terminal.key('P')
        self.terminal.key('escape')
        self.assertEqual(['outline', 'detail'], [p[0] for p in panes(self.app, 156, 48)])
        self.assertEqual(['outline'], [p[0] for p in panes(self.app, 80, 24)])
        self.assertTrue(self.app.graph_pinned)

    def test_pin_preference_survives_scope_and_lens_returns_and_fit(self):
        self.app.select('obs-1')
        self.terminal.key('l')
        self.terminal.key('P')
        self.terminal.key('escape')
        self.assertTrue(self.app.graph_pinned)
        self.terminal.key('2')
        self.terminal.key('1')
        self.terminal.key('2')
        self.assertTrue(self.app.graph_pinned)
        self.terminal.key('f')
        self.assertEqual(['outline'], [p[0] for p in panes(self.app, 144, 42)])
        self.assertTrue(self.app.graph_pinned)
        self.terminal.key('escape')
        self.assertEqual(['outline', 'detail'], [p[0] for p in panes(self.app, 144, 42)])

    def test_local_shared_evidence_routes_vertically_to_adjacent_claim(self):
        self.app.select('obs-1')
        self.terminal.key('l')
        render_snapshot(self.app, 80, 24)
        scene = graph_scene(self.app)
        route = next(r for r in scene.routes if r.edge['source_id'] == 'obs-1'
                     and r.edge['target_id'] == 'claim-pruning-detail')
        source, target = scene.boxes['obs-1'], scene.boxes['claim-pruning-detail']
        above = source.y > target.y
        self.assertEqual(source.y - 1 if above else source.y + source.height, route.points[0][1])
        self.assertEqual(target.y + target.height if above else target.y - 1, route.points[-1][1])
        self.assertEqual(1, len({x for x, _ in route.points}))

    def test_j_and_k_keep_the_local_root_and_scope(self):
        self.app.select('obs-1')
        self.terminal.key('l')
        scene = graph_scene(self.app)
        for key in 'jjjjjjkkkkkk':
            self.terminal.key(key)
            self.assertEqual(scene, graph_scene(self.app))

    def test_reciprocal_claim_edges_do_not_overwrite_each_others_target_arrows(self):
        self.app.select('obs-1')
        self.app.switch_lens('evidence')
        edge = next(e for e in self.app.view['relations'] if e['source_id'] == 'claim-pruning'
                    and e['target_id'] == 'thesis' and e['scientific'])
        self.app.view['relations'].append(dict(edge, key='reverse', source_id='thesis', target_id='claim-pruning'))
        self.app._build_outline()
        render_snapshot(self.app, 80, 24)
        routes = [r for r in graph_scene(self.app).routes if
                  {r.edge['source_id'], r.edge['target_id']} == {'thesis', 'claim-pruning'}]
        targets = {}
        for route in routes:
            targets.setdefault(route.points[-1], set()).add(route.edge['target_id'])
        self.assertTrue(all(len(nodes) == 1 for nodes in targets.values()))

    def test_run_to_other_evidence_does_not_merge_with_interpretation_target_leg(self):
        self.app.select('obs-1')
        render_snapshot(self.app, 120, 30)
        scene = graph_scene(self.app)
        cells = []
        for source, target in (('interpretation', 'obs-1'), ('run-accuracy', 'obs-2')):
            route = next(r for r in scene.routes if (r.edge['source_id'], r.edge['target_id']) == (source, target))
            cells.append({(x, a[1]) for a, b in zip(route.points, route.points[1:]) if a[1] == b[1]
                          for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)})
        self.assertFalse(cells[0] & cells[1])

    def test_local_depth_scope_counts_and_home_do_not_silently_reveal_everything(self):
        self.app.select('obs-1')
        self.terminal.key('l')
        small = render_snapshot(self.app, 80, 24)
        # Readable vertical shafts take priority over fitting a short screen.
        self.assertEqual(4, small.count('╭'))
        self.assertIn('4/5 visible', small)
        self.assertIn('Offscreen:', small)
        taller = render_snapshot(self.app, 80, 26)
        self.assertEqual(5, taller.count('╭'))
        self.assertIn('5/5 visible', taller)
        self.terminal.key('+')
        larger = set(graph_scene(self.app).boxes)
        self.assertIn('thesis', larger)
        self.terminal.key('home')
        self.assertEqual(larger, set(graph_scene(self.app).boxes))
        self.terminal.key('-')
        self.assertEqual('obs-1', self.app.selected_id)
        self.assertEqual(5, len(graph_scene(self.app).boxes))

    def test_full_relations_and_both_evidence_uses_stay_named(self):
        from claimbranch.application.tui import compose
        self.app.select('obs-1')
        frame = compose(self.app, 120, 30)
        self.assertIn('supported by E1', frame.plain())
        self.assertIn('produced E1', frame.plain())
        self.assertIn('supports → C1,C3', frame.plain())
        self.terminal.key('r')
        keys = {link.key for link in self.app.display_links()}
        self.assertEqual({edge['key'] for edge in self.app.view['relations'] if 'obs-1' in
                          (edge['source_id'], edge['target_id'])}, keys)

    def test_local_scope_is_explicit_rooted_and_reversible(self):
        self.app.select('obs-1')
        before = self.app._navigation()
        self.terminal.key('l')
        expected = {'obs-1', 'claim-comparison', 'claim-pruning-detail', 'interpretation', 'run-accuracy'}
        self.assertEqual(expected, set(graph_scene(self.app).boxes))
        frame = render_snapshot(self.app, 144, 42)
        self.assertIn('5 hidden', frame)
        scene = graph_scene(self.app)
        self.app.select('claim-comparison')
        self.assertEqual(scene, graph_scene(self.app))
        self.terminal.key('escape')
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())
        self.assertEqual(self.original, self.history.manifest())

    def test_following_an_edge_outside_local_scope_reveals_target_and_back_restores_scope(self):
        self.app.select('obs-1')
        self.terminal.key('l')
        self.app.select('claim-comparison')
        before = self.app._navigation()
        link = next(link for link in self.app.links() if link.target_id == 'thesis')
        self.app.follow(link)
        self.assertIn('thesis', graph_scene(self.app).boxes)
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())

    def test_connected_fifty_node_paper_retains_shared_edges_and_reports_hidden_scope(self):
        original = deepcopy(self.app.view)
        for index in range(1, 5):
            ids = {node['id']: f'copy{index}-{node["id"]}' for node in original['nodes']}
            for source in original['nodes']:
                node = deepcopy(source)
                node['id'] = ids[source['id']]
                if node['content'].get('role') == 'thesis':
                    node['content']['role'] = 'main'
                self.app.view['nodes'].append(node)
            for edge in original['relations']:
                self.app.view['relations'].append(dict(edge, key=f'copy{index}-{edge["key"]}',
                    source_id=ids[edge['source_id']], target_id=ids[edge['target_id']]))
            self.app.view['relations'].append(dict(original['relations'][1], key=f'bridge-{index}',
                source_id=ids['thesis'], target_id='thesis'))
            self.app.view['relations'].append(dict(original['relations'][5], key=f'shared-{index}',
                source_id='obs-1', target_id=ids['claim-pruning-detail']))
        self.app.nodes = {node['id']: node for node in self.app.view['nodes']}
        self.app._build_outline()
        scene = graph_scene(self.app)
        self.assertEqual(50, len(scene.boxes))
        self.assertEqual(83, len(scene.routes))
        directions = {}
        for route in scene.routes:
            for node, point, direction in ((route.edge['source_id'], route.points[0], 'out'),
                                           (route.edge['target_id'], route.points[-1], 'in')):
                self.assertTrue(scene.boxes[node].beside(*point))
                directions.setdefault((node, point), set()).add(direction)
            for first, last in zip(route.points, route.points[1:]):
                for x in range(min(first[0], last[0]), max(first[0], last[0]) + 1):
                    for y in range(min(first[1], last[1]), max(first[1], last[1]) + 1):
                        self.assertFalse(any(box.x <= x < box.x + box.width and box.y <= y < box.y + box.height
                                             for box in scene.boxes.values()))
        self.assertTrue(all(len(values) == 1 for values in directions.values()))
        self.app.select('obs-1')
        self.terminal.key('l')
        local = graph_scene(self.app)
        self.assertEqual(9, len(local.boxes))
        self.assertEqual(6, sum(r.edge['source_id'] == 'obs-1' and r.edge['scientific'] for r in local.routes))
        for width, height in ((80, 24), (120, 30), (144, 42)):
            frame = render_snapshot(self.app, width, height)
            self.assertIn('41 hidden', frame)
            self.assertTrue(all(cell_width(line) <= width for line in frame.splitlines()))
            self.assertIn(self.app.node_label('obs-1'), frame)
        self.terminal.key('a')
        self.assertEqual(50, len(graph_scene(self.app).boxes))
        self.assertEqual(self.original, self.history.manifest())


if __name__ == '__main__':
    unittest.main()
