from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import unittest
from unittest.mock import patch

from claimbranch.application.cli import main
from claimbranch.application.tui_model import TerminalWorkspace, cell_width, clip, wrap
from claimbranch.application.tui import Terminal, edge_segments, render_snapshot
from claimbranch.fixtures import replay_example


class TerminalWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example("manual", paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history, navigation="outline")

    def test_shared_observation_has_one_identity_and_both_claim_links(self):
        self.app.select("obs-1")
        links = self.app.links()
        targets = {link.target_id for link in links if link.kind == "supports"}
        self.assertEqual({"claim-comparison", "claim-pruning-detail"}, targets)
        self.app.follow(next(link for link in links if link.target_id == "claim-comparison"))
        self.assertEqual("claim-comparison", self.app.selected_id)
        self.app.back()
        self.assertEqual("obs-1", self.app.selected_id)
        self.assertEqual(self.original, self.history.manifest())

    def test_evidence_uses_count_distinct_claims_and_keep_relation_types(self):
        self.app.view["relations"].extend([
            {"key": "second-kind", "source_id": "obs-1", "target_id": "claim-comparison",
             "type": "challenges", "scientific": True, "rationale": "Different scope"},
            {"key": "structural-only", "source_id": "obs-1", "target_id": "thesis",
             "type": "references", "scientific": False, "rationale": None},
            {"key": "incoming-only", "source_id": "claim-pruning", "target_id": "obs-1",
             "type": "qualifies", "scientific": True, "rationale": "Incoming relation"},
        ])
        uses = self.app.claim_uses("obs-1")
        self.assertEqual(3, len(uses))
        self.assertEqual({"claim-comparison", "claim-pruning-detail"}, {link.target_id for link in uses})
        self.assertEqual({"supports", "challenges"}, {link.kind for link in uses})
        self.assertTrue(all(link.outgoing for link in uses))
        self.assertEqual("E1 · 2 claims", self.app.evidence_label("obs-1"))
        self.app.select("obs-1")
        detail = "\n".join(text for text, _ in self.app.detail(include_links=False))
        self.assertIn("supports → C1", detail)
        self.assertIn("supports → C3", detail)
        for i, link in enumerate(self.app.display_links()):
            self.app.link_index = i
            self.assertIn((self.app.title(link.target_id), "body"), self.app.relationship_detail())
        self.assertIn("challenges →", detail)
        self.assertEqual(self.original, self.history.manifest())

    def test_evidence_view_shows_direct_uses_then_expandable_recorded_argument_paths(self):
        self.app.select("obs-1")
        self.app.switch_lens("evidence")
        rows = self.app.rows()
        self.assertEqual(["obs-1"], [row.node_id for row in rows if row.depth == 0])
        self.assertEqual({"claim-comparison", "claim-pruning-detail", "run-accuracy", "interpretation"},
                         {row.node_id for row in rows if row.depth == 1})
        self.assertNotIn("thesis", [row.node_id for row in rows])
        self.assertTrue(all(edge_segments(row)[0][0] == "↓ supports" for row in rows
                            if row.depth == 1 and self.app.nodes[row.node_id]['kind'] == 'claim'))
        self.app.collapsed.clear()
        self.assertIn("thesis", [row.node_id for row in self.app.rows()])
        for row in self.app.rows():
            for edge in row.edges:
                self.assertIn(edge, self.app.view["relations"])
                self.assertEqual({row.node_id, row.parent_id}, {edge["source_id"], edge["target_id"]})
        self.assertEqual(self.original, self.history.manifest())

    def test_direct_evidence_use_keeps_primary_position_when_it_is_also_reached_indirectly(self):
        self.app.view["relations"].append({"key": "direct-thesis", "source_id": "obs-1",
            "target_id": "thesis", "type": "supports", "scientific": True, "rationale": "Synthetic direct use"})
        self.app.select("obs-1")
        self.app.switch_lens("evidence")
        direct = next(row for row in self.app.rows() if row.node_id == "thesis")
        self.assertEqual(1, direct.depth)
        self.assertFalse(direct.reference)
        self.app.collapsed.clear()
        indirect = [row for row in self.app.rows() if row.node_id == "thesis" and row.depth > 1]
        self.assertTrue(indirect)
        self.assertTrue(all(row.reference for row in indirect))
        self.assertEqual(self.original, self.history.manifest())

    def test_lens_switch_and_follow_restore_occurrence_fold_draft_and_scenario(self):
        self.app.collapsed.clear()
        shared = next(row for row in self.app.rows() if row.node_id == "obs-1" and row.reference)
        self.app.select("obs-1", path=shared.path)
        self.app.collapsed.add("claim-pruning")
        folded = set(self.app.collapsed)
        self.app.keep_draft("같은 근거의 판단", "사용처마다 관계 확인")
        self.app.preview_scenario("replication", "challenges")
        scenario = self.app.scenario
        self.app.switch_lens("evidence")
        self.assertEqual(("obs-1",), self.app.selected_path)
        self.assertEqual("같은 근거의 판단", self.app.draft()["text"])
        self.app.switch_lens("argument")
        self.assertEqual(shared.path, self.app.selected_path)
        self.assertEqual(folded, self.app.collapsed)
        self.app.back()
        self.assertEqual("evidence", self.app.lens)
        source = next(link for link in self.app.links() if link.target_id == "run-accuracy")
        self.app.follow(source)
        self.assertEqual(("evidence", "run-accuracy"), (self.app.lens, self.app.selected_id))
        self.app.back()
        self.assertEqual(("evidence", "obs-1"), (self.app.lens, self.app.selected_id))
        self.assertEqual(scenario, self.app.scenario)
        self.assertEqual(self.original, self.history.manifest())

    def test_usage_picker_follows_exact_edge_and_returns_to_evidence(self):
        self.app.select("obs-1")
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key("u")
        self.assertEqual("links", self.app.focus)
        self.assertEqual({"claim-comparison", "claim-pruning-detail"},
                         {link.target_id for link in self.app.display_links()})
        link = self.app.display_links()[self.app.link_index]
        self.assertIn(link.rationale, [text for text, _ in self.app.relationship_detail()])
        terminal.key("enter")
        self.assertEqual(link.target_id, self.app.selected_id)
        terminal.key("escape")
        self.assertEqual("obs-1", self.app.selected_id)
        terminal.key("2")
        terminal.key("]")
        self.assertEqual(("evidence", "obs-2"), (self.app.lens, self.app.selected_id))
        terminal.key("escape")
        self.assertEqual("obs-1", self.app.selected_id)
        terminal.key("1")
        self.assertEqual("argument", self.app.lens)

    def test_evidence_view_handles_unlinked_evidence_and_branch_bound_drafts(self):
        self.app.select("obs-2")
        self.app.switch_lens("evidence")
        self.app.keep_draft("Main draft", "Main reason")
        self.app.switch_ref()
        self.assertEqual(("evidence", "obs-2"), (self.app.lens, self.app.selected_id))
        self.assertEqual("", self.app.draft()["text"])
        self.app.switch_ref()
        self.assertEqual("Main draft", self.app.draft()["text"])
        self.app.view["relations"] = [edge for edge in self.app.view["relations"]
                                      if "obs-2" not in (edge["source_id"], edge["target_id"])]
        self.app._build_outline()
        self.assertEqual(["obs-2"], [row.node_id for row in self.app.rows()])
        self.assertEqual("E2 · 0 claims", self.app.evidence_label("obs-2"))
        self.assertEqual(self.original, self.history.manifest())

    def test_evidence_entry_from_thesis_focuses_evidence_and_escape_restores_thesis(self):
        self.app.switch_lens("evidence")
        self.assertEqual("run-accuracy", self.app.selected_id)
        self.assertEqual(("run-accuracy",), self.app.selected_path)
        self.app.back()
        self.assertEqual(("argument", "thesis"), (self.app.lens, self.app.selected_id))
        self.app.nodes = {key: node for key, node in self.app.nodes.items() if node["kind"] != "observation"}
        self.app.view["relations"] = [edge for edge in self.app.view["relations"]
                                      if edge["source_id"] in self.app.nodes and edge["target_id"] in self.app.nodes]
        self.app._build_outline()
        self.app.switch_lens("evidence")
        self.assertEqual("evidence", self.app.lens)
        self.assertEqual("run-accuracy", self.app.evidence_root)
        self.assertNotIn('observation', {self.app.nodes[key]['kind'] for key in self.app.graph_ids()})

    def test_evidence_labels_survive_new_earlier_ids_and_both_views_fit_small_terminals(self):
        self.assertEqual("E1 · 2 claims", self.app.evidence_label("obs-1"))
        extra = deepcopy(self.app.nodes["obs-2"])
        extra["id"] = "earlier-observation"
        self.app.nodes[extra["id"]] = extra
        self.assertEqual("E1 · 2 claims", self.app.evidence_label("obs-1"))
        self.assertEqual("E3 · 0 claims", self.app.evidence_label(extra["id"]))
        self.app.select("obs-1")
        self.app.collapsed.clear()
        shared_frame = render_snapshot(self.app, 144, 90)
        self.assertIn("↔", shared_frame)
        self.assertGreaterEqual(shared_frame.count("E1 · 2 claims"), 2)
        self.app.switch_lens("evidence")
        for width, height in ((48, 18), (80, 24), (132, 38), (144, 46)):
            for layout in ("two", "three"):
                self.app.layout = layout
                rendered = render_snapshot(self.app, width, height)
                self.assertEqual(height, len(rendered.splitlines()))
                self.assertTrue(all(cell_width(line) <= width for line in rendered.splitlines()))
                self.assertIn("Experiments", rendered)
        self.assertEqual(self.original, self.history.manifest())

    def test_hypothetical_impact_uses_service_without_accepting_state(self):
        self.app.preview_scenario("replication", "challenges")
        self.assertEqual({"thesis", "claim-pruning", "claim-pruning-detail"},
                         set(self.app.scenario["potentially_affected_claim_ids"]))
        self.assertEqual(["claim-comparison"], self.app.scenario["unaffected_claim_ids"])
        self.assertEqual("hypothetical", self.app.scenario["authority"])
        self.assertFalse(self.app.scenario["authorization_verified"])
        self.assertEqual(self.original, self.history.manifest())
        self.app.switch_ref()
        self.assertIsNone(self.app.scenario)

    def test_drafts_stay_bound_to_branch_and_node_and_do_not_change_provenance(self):
        recorded = replay_example("recorded", paper=True)
        app = TerminalWorkspace(recorded)
        original = recorded.manifest()
        contribution = app.view["judgment"]["history"]
        self.assertTrue(any(item["contributor"] == "ai" for item in contribution))
        app.keep_draft("가설을 다시 검토합니다.", "공유 근거의 범위를 확인했습니다.")
        app.layout = "three"
        self.assertEqual("가설을 다시 검토합니다.", app.draft()["text"])
        app.select("claim-comparison")
        self.assertEqual("", app.draft()["text"])
        app.select("thesis")
        app.switch_ref()
        self.assertEqual("", app.draft()["text"])
        app.switch_ref()
        self.assertEqual("가설을 다시 검토합니다.", app.draft()["text"])
        self.assertEqual(contribution, app.view["judgment"]["history"])
        self.assertEqual(original, recorded.manifest())

    def test_notes_belong_to_one_node_and_branch_without_replacing_research_or_judgment(self):
        self.app.select("obs-1")
        source = self.app.title("obs-1")
        self.app.keep_draft("판단 초안", "판단 이유")
        self.app.keep_note("재현 메모\nseed 43으로 다시 확인")
        self.assertEqual(source, self.app.title("obs-1"))
        self.assertEqual("판단 초안", self.app.draft()["text"])
        self.assertIn(("재현 메모\nseed 43으로 다시 확인", "body"), self.app.detail("detail"))
        self.app.follow(next(link for link in self.app.claim_uses() if link.target_id == "claim-comparison"))
        self.assertEqual("", self.app.note())
        self.app.back()
        self.app.switch_lens("evidence")
        self.assertEqual("재현 메모\nseed 43으로 다시 확인", self.app.note())
        self.app.switch_ref()
        self.assertEqual("", self.app.note())
        self.app.switch_ref()
        self.assertEqual("재현 메모\nseed 43으로 다시 확인", self.app.note())
        self.app.search = "재현 메모"
        self.assertIn("obs-1", self.app.matching_ids())
        self.assertEqual(self.original, self.history.manifest())

    def test_note_is_visible_inside_its_graph_box_and_full_text_remains_readable(self):
        self.app.navigation = "graph"
        self.app.select("obs-1")
        self.app.keep_note("재현 필요\n다른 시드로 확인해야 한다.")
        self.app.focus = "outline"
        graph = render_snapshot(self.app, 156, 48)
        self.assertIn("✎ 재현 필요", graph)
        self.assertIn("0.4", graph)
        self.assertIn("다른 시드로 확인해야 한다.", "\n".join(text for text, _ in self.app.detail("detail")))
        self.app.keep_note("")
        self.assertNotIn("✎ 재현 필요", render_snapshot(self.app, 156, 48))
        self.assertEqual(self.original, self.history.manifest())

    def test_follow_reveals_a_node_hidden_by_collapse_or_search(self):
        self.app.select("claim-pruning")
        self.app.toggle_collapsed()
        self.assertNotIn("claim-pruning-detail", [row.node_id for row in self.app.rows()])
        self.app.search = "0.7"
        self.app.select("claim-pruning-detail")
        self.assertEqual("", self.app.search)
        self.assertIn("claim-pruning-detail", [row.node_id for row in self.app.rows()])

    def test_empty_search_does_not_change_scientific_selection(self):
        self.app.search = "no matching scientific term"
        self.assertEqual([], self.app.rows())
        self.app.move(1)
        self.assertEqual("thesis", self.app.selected_id)

    def test_argument_has_only_thesis_at_root_and_every_connection_is_recorded(self):
        self.app.collapsed.clear()
        rows = self.app.rows()
        self.assertEqual(["thesis"], [row.node_id for row in rows if row.depth == 0])
        self.assertEqual(set(self.app.nodes), {row.node_id for row in rows})
        actual = {edge["key"] for edge in self.app.view["relations"]}
        projected = {edge["key"] for row in rows for edge in row.edges}
        self.assertEqual(actual, projected)
        for row in rows[1:]:
            self.assertEqual(row.depth, len(row.path) - 1)
            self.assertEqual(row.parent_id, row.path[-2])
            for edge in row.edges:
                self.assertEqual({row.node_id, row.parent_id}, {edge["source_id"], edge["target_id"]})
        self.assertEqual(self.original, self.history.manifest())

    def test_shared_evidence_has_distinct_occurrences_but_one_draft_and_return_path(self):
        self.app.collapsed.clear()
        shared = [row for row in self.app.rows() if row.node_id == "obs-1"]
        self.assertEqual({"claim-comparison", "claim-pruning-detail"}, {row.parent_id for row in shared})
        self.assertEqual(1, sum(row.reference for row in shared))
        first, second = shared
        self.app.select(first.node_id, path=first.path)
        self.app.keep_draft("Same evidence, one judgment", "Keep its scope")
        self.app.select(second.node_id, path=second.path)
        self.assertEqual("Same evidence, one judgment", self.app.draft()["text"])
        self.assertEqual(second.path, self.app.selected_path)
        self.app.back()
        self.assertEqual(first.path, self.app.selected_path)
        self.app.select(second.node_id, path=second.path)
        self.app.jump_to_original()
        self.assertEqual(first.path, self.app.selected_path)
        self.app.back()
        self.assertEqual(second.path, self.app.selected_path)
        self.assertEqual(self.original, self.history.manifest())

    def test_fold_and_search_retain_actual_graph_ancestry(self):
        self.app.collapsed.clear()
        self.app.select("thesis")
        self.app.toggle_collapsed()
        self.assertEqual(["thesis"], [row.node_id for row in self.app.rows()])
        self.app.search = "replication"
        self.assertEqual(["thesis", "claim-pruning", "claim-pruning-detail", "replication"],
                         [row.node_id for row in self.app.rows()])
        self.app.select("replication")
        row = self.app.selected_row()
        self.assertEqual("claim-pruning-detail", row.parent_id)
        self.assertEqual(["tests"], [edge["type"] for edge in row.edges])
        self.app.left()
        self.assertEqual("claim-pruning-detail", self.app.selected_id)
        self.app.left()
        self.assertNotIn("replication", [row.node_id for row in self.app.rows()])
        self.app.right()
        self.assertIn("replication", [row.node_id for row in self.app.rows()])

    def test_selected_connection_opens_exact_parent_edge_with_parallel_structure_visible(self):
        self.app.select("claim-pruning-detail")
        row = self.app.selected_row()
        self.assertEqual({"supports", "part-of"}, {edge["type"] for edge in row.edges})
        self.app.inspect_parent_edge()
        link = self.app.links()[self.app.link_index]
        self.assertEqual(("claim-pruning", "supports", True), (link.target_id, link.kind, link.outgoing))
        self.assertTrue(self.app.reading_relation)

    def test_search_navigation_keeps_match_ancestry_and_does_not_toggle_hidden_state(self):
        self.app.search = "replication"
        self.app.select("claim-pruning-detail", reveal=False)
        collapsed = set(self.app.collapsed)
        self.app.toggle_collapsed()
        self.assertEqual(collapsed, self.app.collapsed)
        self.app.right()
        self.assertEqual("replication", self.app.selected_id)
        self.assertEqual("replication", self.app.search)
        self.app.left()
        self.assertEqual("claim-pruning-detail", self.app.selected_id)
        self.assertEqual("replication", self.app.search)

    def test_projection_does_not_invent_edges_for_unlinked_nodes_or_reverse_outgoing_edges(self):
        # Deliberately synthetic projection inputs, not accepted history edits.
        orphan = deepcopy(self.app.nodes["anchor"])
        orphan["id"] = "unlinked-anchor"
        self.app.nodes[orphan["id"]] = orphan
        outward = deepcopy(self.app.nodes["anchor"])
        outward["id"] = "outward-anchor"
        self.app.nodes[outward["id"]] = outward
        edge = {"key": "outward-test", "source_id": "thesis", "target_id": "outward-anchor",
                "type": "references", "scientific": False, "rationale": None}
        self.app.view["relations"].append(edge)
        self.app._build_outline()
        self.app.collapsed.clear()
        rows = self.app.rows()
        unlinked = next(row for row in rows if row.node_id == orphan["id"])
        attached = next(row for row in rows if row.node_id == outward["id"])
        self.assertTrue(unlinked.unlinked)
        self.assertIsNone(unlinked.parent_id)
        self.assertEqual((), unlinked.edges)
        self.assertEqual("thesis", attached.parent_id)
        self.assertEqual((edge,), attached.edges)
        self.assertEqual("↓ references", edge_segments(attached)[0][0])
        self.assertEqual(self.original, self.history.manifest())

    def test_graph_cycle_is_a_finite_reference_and_search_selects_match_not_ancestor(self):
        self.app.view["relations"].append({"key": "cycle-test", "source_id": "thesis",
            "target_id": "run-accuracy", "type": "references", "scientific": False, "rationale": None})
        self.app._build_outline()
        self.app.collapsed.clear()
        rows = self.app.rows()
        self.assertEqual(2, sum(row.node_id == "thesis" for row in rows))
        self.assertTrue(next(row for row in rows if row.node_id == "thesis" and row.depth).reference)
        self.assertLess(len(rows), 20)
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key("/")
        terminal.buffers[0].insert("replication")
        terminal.key("enter")
        self.assertEqual("replication", self.app.selected_id)
        self.assertEqual("thesis", self.app.rows()[0].node_id)
        self.assertEqual(self.original, self.history.manifest())

    def test_reading_surfaces_retain_measurement_and_do_not_invent_manuscript(self):
        self.app.select("obs-1")
        detail = "\n".join(text for text, _ in self.app.detail())
        self.assertIn("percentage points", detail)
        self.assertIn("2000", detail)
        self.assertIn("seed 42", detail)
        writing = "\n".join(text for text, _ in self.app.detail("writing"))
        self.assertIn("No manuscript source", writing)
        self.assertEqual(self.original, self.history.manifest())

    def test_both_layouts_render_with_full_content_in_a_narrow_terminal(self):
        self.app.select("obs-1")
        for layout, width in (("two", 100), ("three", 150), ("three", 62)):
            self.app.layout = layout
            rendered = render_snapshot(self.app, width, 32)
            self.assertEqual(32, len(rendered.splitlines()))
            self.assertTrue(all(cell_width(line) <= width for line in rendered.splitlines()))
            self.assertIn("ClaimBranch", rendered)
            self.assertNotIn("\x1b", rendered)

    def test_unicode_wrap_and_clip_do_not_overrun_terminal_cells(self):
        text = "한글 근거와 claim e\u0301 0.4 percentage points"
        for width in (6, 13, 32):
            self.assertTrue(all(cell_width(line) <= width for line in wrap(text, width)))
            self.assertLessEqual(cell_width(clip(text, width)), width)
        self.assertEqual(4, cell_width("한글"))
        self.assertNotIn("\x1b", clip("untrusted\x1b[2Jtext", 80))

    def test_reading_relation_preserves_source_direction_and_complete_rationale(self):
        self.app.select("claim-pruning-detail")
        link = next(link for link in self.app.links() if link.target_id == "obs-1")
        self.assertFalse(link.outgoing)
        self.app.link_index = self.app.links().index(link)
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key("r")
        self.assertTrue(self.app.reading_relation)
        detail = [text for text, _ in self.app.relationship_detail()]
        self.assertEqual(self.app.title("obs-1"), detail[detail.index("FROM / E1") + 1])
        self.assertEqual(self.app.title("claim-pruning-detail"), detail[detail.index("TO / C3") + 1])
        self.assertIn(link.rationale, detail)
        terminal.key("tab")
        self.assertEqual("detail", self.app.focus)
        self.assertTrue(self.app.reading_relation)
        terminal.key("d")
        self.assertFalse(self.app.reading_relation)
        terminal.key("r")
        terminal.key("enter")
        self.assertEqual("obs-1", self.app.selected_id)
        self.assertFalse(self.app.reading_relation)
        self.assertEqual(self.original, self.history.manifest())

    def test_density_and_layout_changes_preserve_research_context(self):
        self.app.select("obs-1")
        self.app.keep_draft("검토 중인 근거", "두 주장과 관계 확인")
        self.app.preview_scenario("replication", "challenges")
        scenario = self.app.scenario
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key("z")
        self.assertEqual("compact", self.app.density)
        terminal.key("v")
        for width, height in ((48, 18), (80, 24), (132, 38), (160, 44)):
            rendered = render_snapshot(self.app, width, height)
            self.assertTrue(all(cell_width(line) <= width for line in rendered.splitlines()))
        terminal.key("z")
        self.assertEqual("comfortable", self.app.density)
        self.assertEqual("obs-1", self.app.selected_id)
        self.assertEqual("검토 중인 근거", self.app.draft()["text"])
        self.assertEqual(scenario, self.app.scenario)
        self.assertEqual(self.original, self.history.manifest())


class TerminalCliTests(unittest.TestCase):
    def invoke(self, args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(args)
        return code, output.getvalue(), error.getvalue()

    def test_snapshot_has_no_browser_listener_or_network_dependency(self):
        with patch("webbrowser.open", side_effect=AssertionError("browser opened")), \
             patch("socket.socket", side_effect=AssertionError("network used")):
            code, output, error = self.invoke(["demo", "tui", "--snapshot", "--layout", "three"])
        self.assertEqual((0, ""), (code, error))
        self.assertIn("ClaimBranch", output)
        self.assertIn("SYNTHETIC", output)
        self.assertNotIn("\x1b", output)

    def test_noninteractive_launch_explains_how_to_get_a_terminal(self):
        code, output, error = self.invoke(["demo", "tui"])
        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertIn("--snapshot", error)
        self.assertIn("TTY", error)


class EscapeSuffixTests(unittest.TestCase):
    def test_encoded_modified_key_is_not_a_standalone_escape(self):
        from collections import deque
        from types import SimpleNamespace
        from unittest.mock import Mock
        from claimbranch.application.tui import Terminal

        names = ('KEY_UP KEY_DOWN KEY_LEFT KEY_RIGHT KEY_HOME KEY_END '
                 'KEY_BACKSPACE KEY_DC KEY_NPAGE KEY_PPAGE KEY_BTAB '
                 'KEY_ENTER KEY_RESIZE').split()
        keys = SimpleNamespace(error=TimeoutError,
                               **{name: index + 1000 for index, name in enumerate(names)})
        for suffix in (keys.KEY_BACKSPACE, keys.KEY_LEFT):
            with self.subTest(suffix=suffix):
                terminal = Terminal.__new__(Terminal)
                terminal.curses, terminal.pending, terminal.discard_sequence = keys, deque(), False
                terminal.screen = SimpleNamespace(timeout=Mock(),
                    get_wch=Mock(side_effect=['\x1b', suffix, '\x13']))
                self.assertIsNone(terminal.read())
                self.assertEqual('keep', terminal.read())

        terminal.screen.get_wch = Mock(side_effect=['\x1b', TimeoutError()])
        self.assertEqual('escape', terminal.read())


if __name__ == "__main__":
    unittest.main()
