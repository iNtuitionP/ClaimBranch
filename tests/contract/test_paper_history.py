from copy import deepcopy
from dataclasses import asdict
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import Judgment, Proposal


def command(history, kind, payload, *, operation_id=None):
    seed = decode(history.seed)
    return {"schema_version": 2, "id": operation_id or f"op-{len(history.commands) + 1}",
            "project_id": seed["project_id"], "episode_id": seed["episode_id"],
            "created_at": "2026-09-22T00:00:00Z", "operation_type": kind,
            "expected_heads": dict(history.heads), "evidence_watermark": history.watermark,
            "payload": payload}


def experiment():
    return {"id": "run-accuracy", "question": "Do 20 percent weight pruning and 8-bit weight quantization keep Model A within 1 percentage point of its unchanged accuracy?",
            "method": "Count correct classifications for unchanged and modified Model A on the same synthetic 2000-example split.",
            "conditions": "Same Model A and evaluation split; prune 20 percent of weights with mask seed 42, or quantize weights to 8 bits.",
            "metric": {"name": "classification accuracy loss", "definition": "100 times (unchanged correct count minus modified correct count) divided by 2000.",
                       "unit": "percentage points", "comparison": "At most 1 percentage point loss relative to unchanged Model A on the same split."},
            "source_ref": "synthetic:paper-accuracy-example"}


def paper(*, ai=False):
    history = ResearchHistory.start_paper("project", "episode", "Synthetic accuracy study of weight pruning and quantization",
        "thesis", "On a fixed synthetic 2000-example split, pruning 20 percent of Model A weights or quantizing them to 8 bits loses at most 1 percentage point of accuracy against unchanged Model A.", "anchor")
    history = history.append(command(history, "record-experiment", experiment()))
    for index, text, value in ((1, "Pruning 20 percent of Model A weights with mask seed 42 lost 0.4 percentage points of accuracy against unchanged Model A on the fixed synthetic 2000-example split.", "0.4"),
                               (2, "Quantizing Model A weights to 8 bits lost 0.7 percentage points of accuracy against unchanged Model A on the fixed synthetic 2000-example split.", "0.7")):
        history = history.append(command(history, "record-evidence-event", {
            "event_id": f"event-{index}", "target_id": f"obs-{index}", "run_id": "run-accuracy",
            "action": "confirm", "statement": text, "value": value,
            "rationale": "Explicitly synthetic example, not an actual experiment.", "supersedes_id": None}))
    history = history.append(command(history, "create-reasoning-branch", {}))
    interpretation = "The recorded 20 percent weight pruning and 8-bit weight quantization of Model A each lost less than 1 percentage point of accuracy on the fixed synthetic split; another pruning seed remains untested."
    judgment = Judgment.start("project", "episode").edit(interpretation, "The synthetic losses are 0.4 and 0.7 percentage points against unchanged Model A; neither exceeds the 1-point budget.")
    if ai:
        judgment = judgment.use_proposal(Proposal("proposal", "project", "episode", "Repeat the 20 percent weight-pruning evaluation with a second mask seed before generalizing Model A's accuracy retention.", "a" * 64))
        judgment = judgment.edit(interpretation, "Keep the conclusion limited to the two recorded settings; the planned mask-seed replication is not evidence yet.")
    changes = [
        {"id": "claim-pruning", "kind": "claim", "body": {"role": "main", "statement": "Pruning 20 percent of Model A weights with mask seed 42 stays within 1 percentage point of unchanged accuracy on the fixed synthetic split.", "scope": "Model A; 20 percent weight pruning; mask seed 42; fixed 2000-example split.", "parent_ids": ["thesis"]}},
        {"id": "claim-comparison", "kind": "claim", "body": {"role": "main", "statement": "On the fixed synthetic split, Model A loses less accuracy with 20 percent weight pruning than with 8-bit weight quantization: 0.4 versus 0.7 percentage points.", "scope": "The two recorded settings against unchanged Model A on the same 2000 examples.", "parent_ids": ["thesis"]}},
        {"id": "claim-pruning-detail", "kind": "claim", "body": {"role": "subclaim", "statement": "With pruning-mask seed 42, removing 20 percent of Model A weights causes 8 fewer correct classifications out of 2000, an accuracy loss of 0.4 percentage points.", "scope": "Same unchanged Model A baseline and fixed synthetic split; this pruning mask only.", "parent_ids": ["claim-pruning"]}},
        {"id": "interpretation", "kind": "interpretation", "body": {"statement": judgment.text, "observation_ids": ["obs-1", "obs-2"]}},
        {"id": "replication", "kind": "experiment-plan", "body": {"claim_id": "claim-pruning-detail", "objective": "Does pruning 20 percent of Model A weights with mask seed 43 still lose at most 1 percentage point of accuracy?", "status": "planned", "conditions": "Same Model A, baseline and synthetic 2000-example split; change only pruning-mask seed 42 to 43.", "metric": experiment()["metric"]}},
    ]
    for edge_id, source, target, edge_type in (
        ("edge-pruning", "obs-1", "claim-pruning-detail", "supports"),
        ("edge-shared", "obs-1", "claim-comparison", "supports"),
        ("edge-quantization", "obs-2", "claim-comparison", "supports"),
        ("edge-detail", "claim-pruning-detail", "claim-pruning", "supports"),
        ("edge-thesis", "claim-pruning", "thesis", "supports"),
        ("edge-other", "claim-comparison", "thesis", "qualifies")):
        changes.append({"id": edge_id, "kind": "scientific-edge", "body": {
            "edge_type": edge_type, "source_id": source, "target_id": target,
            "rationale": "Only the explicitly stated settings support this relation."}})
    history = history.append(command(history, "record-interpretation", {"changes": changes, "judgment": asdict(judgment)}))
    return history, judgment


class PaperHistoryTests(unittest.TestCase):
    def test_paper_keeps_distinct_claims_shared_evidence_and_defined_measurement(self):
        history, _ = paper()
        view = history.view("alternative")
        self.assertEqual(2, view["schema_version"])
        self.assertEqual("thesis", view["claim"]["id"])
        self.assertEqual(4, len(view["claims"]))
        self.assertEqual(2, len(view["evidence"]))
        self.assertEqual("percentage points", view["experiments"][0]["metric"]["unit"])
        self.assertEqual("0.4", view["evidence"][0]["value"])
        self.assertFalse(view["authorization_verified"])

    def test_replay_and_exact_retry_keep_the_same_manifest(self):
        history, _ = paper(ai=True)
        self.assertIs(history, history.append(decode(history.commands[-1])))
        self.assertEqual(history.manifest(), ResearchHistory.replay(history.seed, history.commands).manifest())
        altered = decode(history.commands[-1])
        altered["payload"]["changes"][0]["body"]["statement"] = "Rewritten retry"
        with self.assertRaises(ContractError):
            history.append(altered)

    def test_selecting_shared_edge_requires_claim_but_does_not_select_sibling_argument(self):
        history, _ = paper()
        selection = history.merge_preview(["edge-shared"]).selection
        self.assertEqual(("claim-comparison",), selection.required)
        self.assertEqual(("obs-1",), selection.evidence_references)
        self.assertIn("claim-pruning", selection.omitted)

    def test_evidence_correction_is_global_and_retains_original_measurement(self):
        history, _ = paper()
        before = dict(history.heads)["alternative"]
        revised = history.append(command(history, "record-evidence-event", {
            "event_id": "correction", "target_id": "obs-1", "run_id": "run-accuracy",
            "action": "correct", "statement": "Corrected synthetic loss: 0.5 percentage points.", "value": "0.5",
            "rationale": "Correct the fixture measurement.", "supersedes_id": "event-1"}))
        self.assertEqual(revised.view("main")["evidence"], revised.view("alternative")["evidence"])
        self.assertEqual("0.5", revised.view("main")["evidence"][0]["value"])
        self.assertEqual("0.4", revised.view("main", at_operation=before)["evidence"][0]["value"])
        self.assertEqual("0.4", revised.view("main")["evidence"][0]["history"][0]["value"])

    def test_paper_can_be_drafted_before_results_exist(self):
        history = ResearchHistory.start_paper("p", "e", "Paper", "t", "Undecided thesis", "a")
        history = history.append(command(history, "create-reasoning-branch", {}))
        judgment = Judgment.start("p", "e").edit("A prospective argument", "No results yet.")
        history = history.append(command(history, "record-interpretation", {"judgment": asdict(judgment), "changes": [
            {"id": "i", "kind": "interpretation", "body": {"statement": judgment.text, "observation_ids": []}}]}))
        self.assertEqual([], history.view("alternative")["evidence"])

    def test_unknown_fields_missing_metric_and_cross_context_are_denied(self):
        history, _ = paper()
        valid = command(history, "record-experiment", dict(experiment(), id="second-run"))
        variants = [dict(valid, actor="human"), dict(valid, project_id="other"), dict(valid, schema_version=True)]
        missing = deepcopy(valid)
        del missing["payload"]["metric"]["definition"]
        variants.append(missing)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ContractError):
                history.append(value)

    def test_completed_experiment_cannot_be_rewritten_or_aliased(self):
        history, _ = paper()
        for experiment_id in ("run-accuracy", "obs-1", "thesis", "edge-shared", "anchor"):
            with self.subTest(id=experiment_id), self.assertRaises(ContractError):
                history.append(command(history, "record-experiment", dict(experiment(), id=experiment_id)))

    def test_structural_and_scientific_cycles_and_missing_parents_are_rejected(self):
        history, judgment = paper()
        cases = [
            {"id": "claim-pruning", "kind": "claim", "body": {"role": "subclaim", "statement": "Cycle", "scope": "test", "parent_ids": ["claim-pruning-detail"]}},
            {"id": "claim-pruning", "kind": "claim", "body": {"role": "main", "statement": "Missing", "scope": "test", "parent_ids": ["missing"]}},
            {"id": "cycle", "kind": "scientific-edge", "body": {"edge_type": "supports", "source_id": "thesis", "target_id": "claim-pruning-detail", "rationale": "Cycle"}},
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ContractError):
                history.append(command(history, "record-interpretation", {"changes": [change], "judgment": asdict(judgment)}))

    def test_selected_merge_review_is_exact_and_retains_ai_contributions(self):
        history, judgment = paper(ai=True)
        cmd = command(history, "apply-selected-merge", {"selected_ids": ["edge-thesis", "edge-detail", "edge-pruning", "interpretation"],
            "judgment": asdict(judgment), "disposition": "deferred", "answers": []})
        review = history.prepare_merge_review(cmd, manuscript_digest="b" * 64, session_nonce="nonce", sealed_at=10, expires_at=100)
        merged, candidate = history.append_reviewed_merge(cmd, review, manuscript_digest="b" * 64, now=20)
        self.assertEqual(2, review.context.schema_version)
        self.assertEqual(["human", "ai", "human"], [item.contributor for item in candidate.contributions])
        self.assertEqual(3, len(merged.view("main")["claims"]))
        self.assertFalse(candidate.authorization_verified)
        changed = deepcopy(cmd)
        changed["payload"]["selected_ids"].append("replication")
        with self.assertRaises(ContractError):
            history.append_reviewed_merge(changed, review, manuscript_digest="b" * 64, now=20)

    def test_retraction_cannot_supply_selected_evidence(self):
        history, _ = paper()
        history = history.append(command(history, "record-evidence-event", {"event_id": "retracted", "target_id": "obs-1", "run_id": "run-accuracy",
            "action": "retract", "statement": None, "value": None, "rationale": "Bad source", "supersedes_id": "event-1"}))
        with self.assertRaises(ContractError):
            history.merge_preview(["edge-shared"])

    def test_claim_count_and_depth_are_finite_without_forcing_a_single_parent(self):
        def candidate(changes):
            history = ResearchHistory.start_paper("p", "e", "Paper", "t", "Thesis", "a")
            history = history.append(command(history, "create-reasoning-branch", {}))
            judgment = Judgment.start("p", "e").edit("A prospective argument", "No results yet.")
            return history.append(command(history, "record-interpretation", {"judgment": asdict(judgment), "changes": [
                {"id": "i", "kind": "interpretation", "body": {"statement": judgment.text, "observation_ids": []}}, *changes]}))

        claims = [{"id": f"c-{index}", "kind": "claim", "body": {
            "role": "main", "statement": "Explicit synthetic claim", "scope": "This example", "parent_ids": ["t"]}}
            for index in range(15)]
        self.assertEqual(16, len(candidate(claims).view("alternative")["claims"]))
        with self.assertRaises(ContractError):
            candidate([*claims, dict(claims[0], id="too-many")])
        shared = dict(claims[0], id="shared", body=dict(claims[0]["body"], role="subclaim", parent_ids=["c-0", "c-1"]))
        self.assertEqual(4, len(candidate([*claims[:2], shared]).view("alternative")["claims"]))
        chain = [deepcopy(claims[0])]
        for index in range(1, 8):
            chain.append({"id": f"c-{index}", "kind": "claim", "body": {
                "role": "subclaim", "statement": "Explicit scoped subclaim", "scope": "This example", "parent_ids": [f"c-{index - 1}"]}})
        candidate(chain[:7])
        with self.assertRaises(ContractError):
            candidate(chain)

    def test_conflicting_status_and_wrong_claim_challenge_cannot_be_merged(self):
        history, judgment = paper()
        status = {"id": "status-pruning", "kind": "claim-status", "body": {
            "claim_id": "claim-pruning", "status": "contested", "basis_ids": ["edge-detail"]}}
        challenge = {"id": "challenge-other", "kind": "scientific-edge", "body": {
            "edge_type": "challenges", "source_id": "obs-2", "target_id": "claim-comparison", "rationale": "Challenge the other claim only."}}
        history = history.append(command(history, "record-interpretation", {"changes": [status, challenge], "judgment": asdict(judgment)}))
        with self.assertRaises(ContractError):
            history.merge_preview(["status-pruning", "challenge-other"])
        with self.assertRaises(ContractError):
            history.append(command(history, "record-interpretation", {"changes": [dict(status, id="duplicate-status")], "judgment": asdict(judgment)}))

    def test_review_uses_the_v2_watermark_range_and_experiments_remain_bounded(self):
        history, judgment = paper()
        previous = "event-1"
        for index in range(5):
            event = f"correct-{index}"
            history = history.append(command(history, "record-evidence-event", {"event_id": event, "target_id": "obs-1", "run_id": "run-accuracy",
                "action": "correct", "statement": "Rechecked synthetic loss", "value": "0.4", "rationale": "Synthetic correction", "supersedes_id": previous}))
            previous = event
        cmd = command(history, "apply-selected-merge", {"selected_ids": ["edge-shared"], "judgment": asdict(judgment), "disposition": "not-required", "answers": []})
        review = history.prepare_merge_review(cmd, manuscript_digest="b" * 64, session_nonce="n", sealed_at=1, expires_at=20)
        self.assertEqual(7, review.context.evidence_watermark)
        for index in range(7):
            history = history.append(command(history, "record-experiment", dict(experiment(), id=f"run-{index}")))
        with self.assertRaises(ContractError):
            history.append(command(history, "record-experiment", dict(experiment(), id="run-over-limit")))


if __name__ == "__main__":
    unittest.main()
