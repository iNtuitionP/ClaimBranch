from copy import deepcopy
from dataclasses import asdict
import unittest

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import Judgment
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_history import paper, command


def amendments(history, ref="main"):
    records = {item["id"]: deepcopy(item) for item in history.view(ref)["changes"]}
    claim = records["claim-pruning-detail"]
    claim["body"]["statement"] = "The measured 0.4 percentage-point loss applies only to Model A pruning-mask seed 42 on these 2000 synthetic examples."
    claim["body"]["scope"] = "Seed 42 only; the result does not establish performance for seed 43."
    relation = records["edge-pruning"]
    relation["body"].update(edge_type="qualifies", rationale="One pruning mask limits the scope; another mask has not been observed.")
    plan = records["replication"]
    plan["body"]["objective"] = "Repeat the 20 percent pruning evaluation with seed 43 and compare its accuracy loss to the same unchanged baseline."
    return [claim, relation, plan]


def judgment(history):
    seed = decode(history.seed)
    return Judgment.start(seed["project_id"], seed["episode_id"]).edit(
        "Limit the pruning claim to the recorded mask until another mask is measured.",
        "The 0.4 percentage-point loss is observed only for seed 42; seed 43 remains an unrun plan.")


class PaperChangesTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example("manual", paper=True)
        self.judgment = judgment(self.history)
        self.amendments = amendments(self.history)

    def preview(self, amendments_=None, selected=("edge-pruning",), *, history=None):
        return decode((history or self.history).preview_paper_changes("main",
            self.amendments if amendments_ is None else amendments_, list(selected), self.judgment).payload)

    def test_only_selected_and_required_amendments_change_the_candidate(self):
        before = self.history.manifest()
        result = self.preview()
        self.assertEqual(["edge-pruning"], result["selection"]["selected"])
        self.assertEqual(["claim-pruning-detail"], result["selection"]["required"])
        self.assertEqual(["replication"], result["selection"]["omitted"])
        self.assertEqual(["claim-pruning"], result["selection"]["existing_references"])
        self.assertEqual(["obs-1"], result["selection"]["evidence_references"])
        old = {item["id"]: item for item in result["before"]["changes"]}
        new = {item["id"]: item for item in result["after"]["changes"]}
        self.assertEqual("qualifies", new["edge-pruning"]["body"]["edge_type"])
        self.assertEqual(old["replication"], new["replication"])
        self.assertEqual(old["edge-shared"], new["edge-shared"])
        self.assertEqual(result["before"]["evidence"], result["after"]["evidence"])
        self.assertEqual(result["before"]["experiments"], result["after"]["experiments"])
        self.assertEqual(before, self.history.manifest())

    def test_full_selection_and_plan_only_have_distinct_effects(self):
        full = self.preview(selected=("edge-pruning", "replication"))
        plan = self.preview(selected=("replication",))
        # The plan's changed target claim is a real required amendment.
        self.assertEqual(["claim-pruning-detail"], plan["selection"]["required"])
        self.assertEqual(["edge-pruning"], plan["selection"]["omitted"])
        self.assertNotEqual(full["after"]["changes"], plan["after"]["changes"])
        only_plan = self.preview(amendments_=[self.amendments[2]], selected=("replication",))
        self.assertEqual([], only_plan["selection"]["required"])
        self.assertEqual(["claim-pruning", "claim-pruning-detail"], only_plan["selection"]["existing_references"])
        self.assertEqual(only_plan["before"]["claims"], only_plan["after"]["claims"])

    def test_source_ai_lineage_and_new_human_judgment_remain_separate(self):
        history = replay_example("recorded", paper=True)
        value = self.preview(history=history)
        self.assertTrue(value["ai_influenced"])
        self.assertEqual(["human", "ai", "human"], [item["contributor"] for item in value["source_judgment"]["history"]])
        self.assertEqual(["human"], [item["contributor"] for item in value["judgment"]["history"]])
        self.assertEqual(value["source_judgment"], history.view("main")["judgment"])

    def test_amended_interpretation_must_match_draft_and_omission_keeps_the_old_text(self):
        item = deepcopy(next(item for item in self.history.view("main")["changes"] if item["kind"] == "interpretation"))
        item["body"]["statement"] = self.judgment.text
        result = self.preview([item, self.amendments[2]], ("interpretation",))
        self.assertEqual(self.judgment.text, result["after"]["interpretations"][0]["body"]["statement"])
        result = self.preview([item, self.amendments[2]], ("replication",))
        self.assertEqual(result["before"]["interpretations"], result["after"]["interpretations"])
        item["body"]["statement"] = "An unrelated automatically generated interpretation."
        with self.assertRaises(ContractError):
            self.preview([item], ("interpretation",))

    def test_unknown_duplicate_noop_evidence_and_root_edits_are_rejected(self):
        old = next(item for item in self.history.view("main")["changes"] if item["id"] == "edge-pruning")
        cases = [([], []), (self.amendments, ["missing"]), (self.amendments, ["edge-pruning", "edge-pruning"]),
                 ([old], [old["id"]]), ([self.amendments[0]] * 2, [self.amendments[0]["id"]]),
                 ([dict(self.amendments[0], id="obs-1")], ["obs-1"]),
                 ([dict(self.amendments[0], id="thesis")], ["thesis"]),
                 ([{"id": "obs-1", "kind": "observation", "body": {"value": "1"}}], ["obs-1"])]
        for items, selected in cases:
            with self.subTest(selected=selected), self.assertRaises(ContractError):
                self.preview(items, selected)
        with self.assertRaises(ContractError):
            self.history.preview_paper_changes("main", self.amendments, ["edge-pruning"], Judgment.start("other", "e").edit("x", "y"))
        with self.assertRaises(ContractError):
            ResearchHistory.start("p", "e", "c", "Claim", "a").preview_paper_changes("main", self.amendments, ["edge-pruning"], self.judgment)

    def test_cycles_and_partial_selection_cannot_leave_an_invalid_graph(self):
        cyclic = deepcopy(self.amendments)
        cyclic[0]["body"]["parent_ids"] = ["claim-pruning-detail"]
        with self.assertRaises(ContractError):
            self.preview(cyclic)
        changes = deepcopy(self.amendments)
        # Moving this existing edge is only valid if a dependent status moves
        # with it; selecting just the edge must not silently move that status.
        history, source_judgment = paper()
        status = {"id": "status", "kind": "claim-status", "body": {
            "claim_id": "claim-pruning-detail", "status": "supported", "basis_ids": ["edge-pruning"]}}
        history = history.append(command(history, "record-interpretation", {"changes": [status], "judgment": asdict(source_judgment)}))
        changes = [dict(changes[1], body=dict(changes[1]["body"], target_id="claim-comparison")),
                   dict(status, body=dict(status["body"], claim_id="claim-comparison"))]
        with self.assertRaises(ContractError):
            history.preview_paper_changes("alternative", changes, ["edge-pruning"], self.judgment)

    def test_retracted_selected_basis_fails_but_unrelated_plan_remains_reviewable(self):
        history = self.history.append(command(self.history, "record-evidence-event", {
            "event_id": "retract", "target_id": "obs-1", "run_id": "run-accuracy", "action": "retract",
            "statement": None, "value": None, "rationale": "Invalid synthetic source.", "supersedes_id": "event-1"}))
        with self.assertRaises(ContractError):
            self.preview(history=history)
        result = self.preview([self.amendments[2]], ["replication"], history=history)
        self.assertEqual("retracted", result["after"]["evidence"][0]["status"])

    def test_new_claim_and_edge_close_dependencies_without_creating_a_history_command(self):
        claim = {"id": "new-subclaim", "kind": "claim", "body": {"role": "subclaim",
            "statement": "No evidence yet supports generalizing beyond seed 42.", "scope": "Pruning mask scope only.",
            "parent_ids": ["claim-pruning"]}}
        edge = {"id": "new-relation", "kind": "scientific-edge", "body": {"source_id": "obs-1", "target_id": "new-subclaim",
            "edge_type": "qualifies", "rationale": "The observation was obtained with one mask."}}
        result = self.preview([claim, edge], ["new-relation"])
        self.assertEqual(["new-subclaim"], result["selection"]["required"])
        self.assertEqual(5, len(result["after"]["claims"]))
        self.assertEqual(4, len(self.history.view("main")["claims"]))
        self.assertFalse(result["authorization_verified"])

    def test_contested_status_requires_a_challenge_to_its_own_claim(self):
        status = {"id": "new-status", "kind": "claim-status", "body": {
            "claim_id": "claim-pruning-detail", "status": "contested", "basis_ids": ["edge-pruning"]}}
        with self.assertRaises(ContractError):
            self.preview([*self.amendments, status], ["new-status"])
        challenge = deepcopy(self.amendments[1])
        challenge["body"]["edge_type"] = "challenges"
        result = self.preview([challenge, status], ["new-status"])
        self.assertEqual(["edge-pruning"], result["selection"]["required"])
        after = next(item for item in result["after"]["claims"] if item["id"] == "claim-pruning-detail")
        self.assertEqual("contested", after["status"])
        other = deepcopy(challenge)
        other["id"], other["body"]["target_id"] = "wrong-challenge", "claim-comparison"
        with self.assertRaises(ContractError):
            self.preview([self.amendments[1], other, status], ["new-status", "wrong-challenge"])

    def test_partial_selection_is_revalidated_for_new_scientific_cycles(self):
        records = {item["id"]: deepcopy(item) for item in self.history.view("main")["changes"]}
        top, detail = records["edge-thesis"], records["edge-detail"]
        top["body"]["target_id"] = "claim-pruning-detail"
        detail["body"]["target_id"] = "thesis"
        self.preview([top, detail], ["edge-thesis", "edge-detail"])
        with self.assertRaisesRegex(ContractError, "cyclic"):
            self.preview([top, detail], ["edge-thesis"])

    def test_an_existing_contested_status_cannot_lose_its_selected_challenge(self):
        history, source = paper()
        challenge = deepcopy(self.amendments[1])
        challenge["body"]["edge_type"] = "challenges"
        status = {"id": "status", "kind": "claim-status", "body": {
            "claim_id": "claim-pruning-detail", "status": "contested", "basis_ids": ["edge-pruning"]}}
        history = history.append(command(history, "record-interpretation", {
            "changes": [challenge, status], "judgment": asdict(source)}))
        with self.assertRaisesRegex(ContractError, "challenge"):
            history.preview_paper_changes("alternative", [self.amendments[1]], ["edge-pruning"], self.judgment)

    def test_declared_finite_and_closed_amendment_limits_apply(self):
        for items in (self.amendments * 22, [dict(self.amendments[0], accepted=True)],
                      [dict(self.amendments[0], body=dict(self.amendments[0]["body"], statement="x" * 16385))]):
            with self.subTest(size=len(items)), self.assertRaises(ContractError):
                self.preview(items, ["claim-pruning-detail"])


if __name__ == "__main__":
    unittest.main()
