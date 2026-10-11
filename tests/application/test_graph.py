import unittest

from claimbranch.application.workspace import DemoWorkspace
from claimbranch.core.canonical import ContractError


class ArgumentGraphTests(unittest.TestCase):
    def test_example_reuses_recorded_judgment_without_creating_accepted_science(self):
        workspace = DemoWorkspace(clock=lambda: 1000, example=True)
        state = workspace.state()
        graph = state["review"]["graph"]
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertTrue(state["example_loaded"])
        self.assertEqual(8, len(nodes))
        self.assertEqual(workspace.example_judgment["text"], nodes["I-01"]["body"])
        self.assertEqual(workspace.packet["claim"]["statement"], nodes["C-01"]["body"])
        self.assertEqual("unverified-candidate", graph["authority"])
        self.assertFalse(state["authorization_verified"])
        self.assertEqual(0, state["accepted_writes"])

    def test_mixed_evidence_relations_and_unrun_plan_remain_distinct(self):
        state = DemoWorkspace(clock=lambda: 1000, example=True).state()
        graph = state["review"]["graph"]
        scientific = {edge["source"]: edge["kind"] for edge in graph["edges"] if edge["scientific"]}
        self.assertEqual({"O-01": "challenges", "O-02": "challenges", "O-03": "qualifies"}, scientific)
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual("계획 · 미실행", nodes["optional-experiment"]["status"])
        for edge in graph["edges"]:
            self.assertIn(edge["source"], nodes)
            self.assertIn(edge["target"], nodes)
            if edge["source"] == "optional-experiment":
                self.assertEqual("tests", edge["kind"])
                self.assertFalse(edge["scientific"])

    def test_selected_closure_controls_included_relations_and_omitted_nodes(self):
        workspace = DemoWorkspace(clock=lambda: 1000, example=True)
        graph = workspace.prepare(["claim-status"], "not-required", [])["review"]["graph"]
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual("required", nodes["I-01"]["scope"])
        self.assertEqual("omitted", nodes["optional-experiment"]["scope"])
        self.assertFalse(next(edge for edge in graph["edges"] if edge["kind"] == "tests")["included"])
        graph = workspace.prepare(["optional-experiment"], "not-required", [])["review"]["graph"]
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual("omitted", nodes["I-01"]["scope"])
        self.assertEqual("context", nodes["C-01"]["scope"])
        self.assertTrue(all(not edge["included"] for edge in graph["edges"] if edge["scientific"]))

    def test_example_is_opt_in_and_never_overwrites_entered_work(self):
        workspace = DemoWorkspace(clock=lambda: 1000)
        self.assertFalse(workspace.state()["example_loaded"])
        self.assertIsNone(workspace.state()["review"])
        workspace.edit("My interpretation", "My reason")
        before = workspace.state()
        with self.assertRaises(ContractError):
            workspace.load_example()
        self.assertEqual(before, workspace.state())

    def test_editing_invalidates_the_prepared_graph_and_refresh_uses_current_prose(self):
        workspace = DemoWorkspace(clock=lambda: 1000, example=True)
        workspace.edit("Changed interpretation", "Changed reason")
        self.assertIsNone(workspace.state()["review"])
        graph = workspace.prepare(["claim-status"], "not-required", [])["review"]["graph"]
        interpretation = next(node for node in graph["nodes"] if node["kind"] == "interpretation")
        self.assertEqual("Changed interpretation", interpretation["caption"])
        self.assertEqual("Changed interpretation", interpretation["body"])


if __name__ == "__main__":
    unittest.main()
