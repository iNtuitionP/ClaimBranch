"""Graph projection checks use recorded endpoints, not a screenshot golden."""
import unittest

from claimbranch.application.tui import Frame, Terminal, render_snapshot
from claimbranch.application.tui_model import TerminalWorkspace, cell_width
from claimbranch.fixtures import replay_example


class TerminalGraphTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example("manual", paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)

    def scene(self):
        from claimbranch.application.tui_graph import graph_scene
        return graph_scene(self.app)

    def test_mixed_routes_never_render_a_false_tee_junction(self):
        from claimbranch.application.tui_graph import visible_stroke
        for first, second in ((3, 4), (9, 2), (12, 1), (6, 8), (5, 10)):
            key, glyph = visible_stroke({'a': first, 'b': second}, set(), None)
            self.assertNotIn(glyph, '╳┼├┤┬┴')
        self.assertEqual(('a', '└'), visible_stroke({'a': 3, 'b': 12}, {'a'}, 'a'))

    def test_shared_ports_account_for_every_incident_connection(self):
        self.app.density = 'compact'
        scene = self.scene()
        counts = scene.endpoint_counts()
        self.assertEqual(2 * len(scene.routes), sum(counts.values()))
        self.assertTrue(any(count > 1 for count in counts.values()))
        for key in scene.boxes:
            self.assertEqual(len(self.app.links(key)), sum(count for (node, _), count in counts.items() if node == key))
        directions = {}
        for route in scene.routes:
            for node, point, direction in ((route.edge['source_id'], route.points[0], 'out'),
                                           (route.edge['target_id'], route.points[-1], 'in')):
                directions.setdefault((node, point), set()).add(direction)
        self.assertTrue(all(len(values) == 1 for values in directions.values()))

    def test_fifty_node_projection_keeps_identity_directions_and_reachable_selection(self):
        from copy import deepcopy
        originals = deepcopy(self.app.view)
        for index in range(1, 5):
            ids = {node['id']: f"copy{index}-{node['id']}" for node in originals['nodes']}
            for node in originals['nodes']:
                node = deepcopy(node)
                node['id'] = ids[node['id']]
                if node['content'].get('role') == 'thesis':
                    node['content']['role'] = 'main'
                self.app.view['nodes'].append(node)
            for edge in originals['relations']:
                edge = dict(edge, key=f"copy{index}-{edge['key']}",
                            source_id=ids[edge['source_id']], target_id=ids[edge['target_id']])
                self.app.view['relations'].append(edge)
        self.app.nodes = {node['id']: node for node in self.app.view['nodes']}
        self.app._build_outline()
        scene = self.scene()
        self.assertEqual(50, len(scene.boxes))
        self.assertEqual(50, len({self.app.node_label(key) for key in scene.boxes}))
        self.assertEqual(75, len(scene.routes))
        for key in self.app.evidence_ids():
            self.app.select(key)
            self.app.graph_view = 'overview'
            frame = render_snapshot(self.app, 100, 32)
            label = ('› ! ' + self.app.node_label(key) if self.app.selected_row().unlinked
                     else self.app.evidence_label(key))
            self.assertIn(label, frame)
            self.assertTrue(all(cell_width(line) <= 100 for line in frame.splitlines()))
            nodes, edges = scene.focus(key)
            self.assertEqual({link.key for link in self.app.links()}, edges)
            self.assertEqual({key} | {link.target_id for link in self.app.links()}, nodes)
        self.assertEqual(self.original, self.history.manifest())

    def test_shared_evidence_is_one_box_with_all_recorded_edges(self):
        scene = self.scene()
        self.assertEqual(set(self.app.nodes), set(scene.boxes))
        self.assertEqual(len(self.app.nodes), len(scene.boxes))
        self.assertEqual({edge["key"] for edge in self.app.view["relations"]},
                         {route.edge["key"] for route in scene.routes})
        uses = [route for route in scene.routes if route.edge["source_id"] == "obs-1"
                and route.edge["type"] == "supports"]
        self.assertEqual({"claim-comparison", "claim-pruning-detail"},
                         {route.edge["target_id"] for route in uses})
        for route in scene.routes:
            source = scene.boxes[route.edge["source_id"]]
            target = scene.boxes[route.edge["target_id"]]
            self.assertTrue(source.beside(*route.points[0]))
            self.assertTrue(target.beside(*route.points[-1]))
            for a, b in zip(route.points, route.points[1:]):
                self.assertTrue(a[0] == b[0] or a[1] == b[1])
                points = ((x, y) for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)
                          for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1))
                for x, y in points:
                    self.assertFalse(any(box.x <= x < box.x + box.width and box.y <= y < box.y + box.height
                                         for box in scene.boxes.values()))
        self.assertEqual(self.original, self.history.manifest())

    def test_evidence_graph_retains_unique_claims_and_raw_direction(self):
        self.app.select("obs-1")
        self.app.switch_lens("evidence")
        scene = self.scene()
        self.assertEqual({"obs-1", "claim-comparison", "claim-pruning-detail", "claim-pruning", "thesis"},
                         set(scene.boxes))
        for route in scene.routes:
            self.assertIn(route.edge, self.app.view["relations"])
        self.assertEqual(self.original, self.history.manifest())

    def test_focus_marks_only_direct_neighbors_and_incident_edges(self):
        scene = self.scene()
        nodes, edges = scene.focus("obs-1")
        self.assertEqual({"obs-1", "claim-pruning-detail", "claim-comparison",
                          "run-accuracy", "interpretation"}, nodes)
        self.assertEqual({edge["key"] for edge in self.app.view["relations"]
                          if "obs-1" in (edge["source_id"], edge["target_id"])}, edges)
        self.assertEqual(4, len(edges))
        # The run also produced obs-2. That second result must stay subdued.
        self.assertNotIn("obs-2", nodes)
        self.assertNotIn("thesis", nodes)
        self.assertEqual(self.original, self.history.manifest())

    def test_exact_edge_focus_distinguishes_parallel_types_and_out_of_view_edges(self):
        scene = self.scene()
        parallel = [route.edge for route in scene.routes
                    if route.edge["source_id"] == "claim-pruning-detail"
                    and route.edge["target_id"] == "claim-pruning"]
        self.assertEqual({"supports", "part-of"}, {edge["type"] for edge in parallel})
        for edge in parallel:
            self.assertEqual(({"claim-pruning-detail", "claim-pruning"}, {edge["key"]}),
                             scene.focus("claim-pruning-detail", edge["key"]))
        self.app.select("obs-1")
        self.app.switch_lens("evidence")
        scene = self.scene()
        outside = next(link for link in self.app.links() if link.kind == "produced")
        # An inspected relation outside this lens cannot leave the selection dark
        # or invent a visible edge. Show its visible endpoint only.
        self.assertEqual(({"obs-1"}, set()), scene.focus("obs-1", outside.key))
        self.assertEqual(({"obs-1", "claim-pruning-detail", "claim-comparison"},
                          {link.key for link in self.app.claim_uses("obs-1")}), scene.focus("obs-1"))

    def test_unrelated_cards_dim_without_hiding_content_or_changing_geometry(self):
        from claimbranch.application.tui_graph import graph
        self.app.select("obs-1")
        scene = self.scene()
        frame = Frame(220, 100)
        graph(frame, self.app, 0, 0, frame.width, frame.height)
        # Locate each actual card from its unique rounded corner, independent of
        # the panel's padding; all scene cards fit this viewport.
        first = min(scene.boxes.values(), key=lambda box: (box.x, box.y))
        x, y = min((x, y) for y, row in enumerate(frame.cells)
                   for x, (char, _) in enumerate(row) if char == "╭")
        origin_x, origin_y = x - first.x, y - first.y
        for key, box in scene.boxes.items():
            with self.subTest(node=key):
                x, y = origin_x + box.x, origin_y + box.y
                title_style = frame.cells[y][x][1]
                body_style = frame.cells[y + 1 + box.relation_rows][x + 2][1]
                self.assertTrue(frame.cells[y + 1 + box.relation_rows][x + 2][0].strip())
                if key in {"claim-pruning", "thesis", "obs-2", "replication", "anchor"}:
                    self.assertEqual("graph_dim", body_style)
                    self.assertEqual("graph_dim_border", title_style)
                else:
                    self.assertNotIn(body_style, {"graph_dim", "graph_dim_border"})
                    self.assertNotIn(title_style, {"graph_dim", "graph_dim_border"})
        self.app.select("obs-2")
        self.assertEqual(scene, self.scene())
        self.assertEqual(self.original, self.history.manifest())

    def test_graph_keyboard_read_edge_and_outline_keep_research_context(self):
        self.app.select("obs-1")
        self.app.keep_draft("한 근거의 판단", "두 주장과 연결")
        self.app.preview_scenario("replication", "challenges")
        scenario = self.app.scenario
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key("o")
        self.assertEqual("outline", self.app.navigation)
        terminal.key("o")
        self.assertEqual("graph", self.app.navigation)
        self.assertEqual("한 근거의 판단", self.app.draft()["text"])
        terminal.key("left")
        self.assertNotEqual("obs-1", self.app.selected_id)
        terminal.key("escape")
        self.assertEqual("obs-1", self.app.selected_id)
        terminal.key("enter")
        self.assertEqual(("detail", "detail"), (self.app.focus, self.app.mode))
        terminal.key("r")
        self.assertTrue(self.app.reading_relation)
        terminal.key("f")
        self.assertEqual("outline", self.app.focus)
        self.assertEqual(scenario, self.app.scenario)
        self.assertEqual(self.original, self.history.manifest())

    def test_graph_viewports_keep_cell_bounds_and_selected_content_accessible(self):
        self.app.select("obs-1")
        for lens in ("argument", "evidence"):
            self.app.switch_lens(lens)
            for width, height in ((48, 18), (80, 24), (132, 38), (144, 46)):
                frame = render_snapshot(self.app, width, height)
                self.assertEqual(height, len(frame.splitlines()))
                self.assertTrue(all(cell_width(line) <= width for line in frame.splitlines()))
                self.assertIn("GRAPH", frame)
                self.assertIn("E1", frame)
        self.assertEqual(self.original, self.history.manifest())


if __name__ == "__main__":
    unittest.main()
