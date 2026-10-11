from copy import deepcopy
import unittest

from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.research_history import ResearchHistory
from tests.contract.test_paper_history import paper, command, experiment


def request(view):
    return {"schema_version": 1, "project_id": "project", "episode_id": "episode", "ref": "alternative",
            "view_digest": view["digest"], "plan_id": "replication", "outcome": "challenges",
            "assumed_observation": "Assume replication loses 1.5 percentage points under the same stated conditions.",
            "rationale": "This would challenge reproducibility of the specific pruning result."}


class PaperServiceTests(unittest.TestCase):
    def test_query_exposes_scientific_and_structural_relations_without_layout(self):
        history, _ = paper()
        view = PaperService(history).query("alternative")
        self.assertEqual("claimbranch.paper-view/v1", view["schema"])
        self.assertEqual("thesis", view["thesis_id"])
        self.assertEqual(2, len([node for node in view["nodes"] if node["kind"] == "observation"]))
        shared = [edge for edge in view["relations"] if edge["source_id"] == "obs-1" and edge["scientific"]]
        self.assertEqual({"claim-comparison", "claim-pruning-detail"}, {edge["target_id"] for edge in shared})
        self.assertTrue(any(edge["type"] == "part-of" and not edge["scientific"] for edge in view["relations"]))
        self.assertFalse(view["authorization_verified"])
        self.assertTrue(all("x" not in node and "y" not in node for node in view["nodes"]))

    def test_scenario_reports_reachable_claims_and_existing_basis_without_changing_state(self):
        history, _ = paper(ai=True)
        service = PaperService(history)
        view = service.query("alternative")
        before = history.manifest()
        impact = service.scenario(request(view))
        self.assertEqual(["claim-pruning", "claim-pruning-detail", "thesis"], impact["potentially_affected_claim_ids"])
        self.assertEqual(["claim-comparison"], impact["unaffected_claim_ids"])
        self.assertEqual(["obs-1", "obs-2"], impact["unchanged_evidence_ids"])
        self.assertEqual(["anchor"], impact["potentially_affected_anchor_ids"])
        self.assertTrue(any(edge["source_id"] == "claim-comparison" for edge in impact["existing_basis"]))
        self.assertTrue(impact["requires_human_judgment"])
        self.assertEqual(before, history.manifest())
        self.assertEqual(view, service.query("alternative"))

    def test_structural_parent_does_not_infer_scientific_impact(self):
        history, _ = paper()
        last = decode(history.commands[-1])
        last["payload"]["changes"] = [item for item in last["payload"]["changes"] if item["id"] not in ("edge-detail", "edge-thesis")]
        history = ResearchHistory(history.seed, history.commands[:-1]).append(last)
        service = PaperService(history)
        impact = service.scenario(request(service.query("alternative")))
        self.assertEqual(["claim-pruning-detail"], impact["potentially_affected_claim_ids"])
        self.assertEqual([], impact["potentially_affected_anchor_ids"])

    def test_stale_project_ref_plan_and_injected_authority_are_rejected(self):
        history, _ = paper()
        service = PaperService(history)
        original = request(service.query("alternative"))
        for override in ({"view_digest": "a" * 64}, {"project_id": "other"}, {"episode_id": "other"},
                         {"ref": "main"}, {"plan_id": "run-accuracy"}, {"accepted": True}, {"outcome": "approve"}):
            with self.subTest(override=override), self.assertRaises(ContractError):
                service.scenario(dict(original, **override))
        corrected = history.append(command(history, "record-evidence-event", {
            "event_id": "correction", "target_id": "obs-1", "run_id": "run-accuracy", "action": "correct",
            "statement": "Corrected loss 0.5 percentage points.", "value": "0.5", "rationale": "Correction", "supersedes_id": "event-1"}))
        with self.assertRaises(ContractError):
            PaperService(corrected).scenario(original)
        added_run = history.append(command(history, "record-experiment", dict(experiment(), id="second-run")))
        self.assertEqual(history.heads, added_run.heads)
        self.assertEqual(history.watermark, added_run.watermark)
        with self.assertRaises(ContractError):
            PaperService(added_run).scenario(original)

    def test_all_scenarios_are_hypothetical_and_inconclusive_creates_no_scientific_relation(self):
        history, _ = paper()
        service = PaperService(history)
        original = request(service.query("alternative"))
        for outcome in ("supports", "challenges", "inconclusive"):
            value = service.scenario(dict(original, outcome=outcome))
            self.assertEqual("hypothetical", value["authority"])
            self.assertFalse(value["authorization_verified"])
            self.assertEqual(None if outcome == "inconclusive" else outcome, value["assumption"]["relation_type"])

    def test_returned_values_cannot_mutate_history_or_future_queries(self):
        history, _ = paper()
        service = PaperService(history)
        original = service.query("alternative")
        modified = deepcopy(original)
        modified["nodes"].clear()
        self.assertEqual(original, service.query("alternative"))
        with self.assertRaises(ContractError):
            PaperService(ResearchHistory.start("p", "e", "c", "One claim", "a"))


if __name__ == "__main__":
    unittest.main()
