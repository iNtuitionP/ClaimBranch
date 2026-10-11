"""Portable history tests: scientific state and replay, never OS authority."""
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes
from claimbranch.core.review import Judgment, Proposal
from claimbranch.core.research_history import ResearchHistory, command_schema


def command(history, op, payload, name=None):
    return {"schema_version": 1, "id": name or f"op-{len(history.commands) + 1}",
            "project_id": "project", "episode_id": "episode",
            "created_at": f"2026-09-22T00:00:{len(history.commands):02d}Z",
            "operation_type": op, "expected_heads": dict(history.heads),
            "evidence_watermark": history.watermark, "payload": payload}


def initial():
    history = ResearchHistory.start("project", "episode", "claim", "Original claim", "anchor")
    for i in range(1, 4):
        history = history.append(command(history, "record-evidence-event", {
            "event_id": f"event-{i}", "target_id": f"obs-{i}", "run_id": "run",
            "action": "confirm", "statement": f"Original observation {i}",
            "rationale": "Checked source", "supersedes_id": None}))
    return history


def branch(*, ai=False):
    history = initial()
    history = history.append(command(history, "create-reasoning-branch", {}))
    judgment = Judgment.start("project", "episode").edit("Limited interpretation", "Mixed evidence")
    if ai:
        judgment = judgment.use_proposal(Proposal("proposal", "project", "episode", "AI original", "a" * 64))
        judgment = judgment.edit("Limited interpretation", "AI causal explanation remains untested")
    changes = [
        {"id": "interpretation", "kind": "interpretation", "body": {
            "statement": judgment.text, "observation_ids": ["obs-1", "obs-2", "obs-3"]}},
        {"id": "edge", "kind": "scientific-edge", "body": {
            "edge_type": "challenges", "source_id": "interpretation", "target_id": "claim", "rationale": "Mixed result"}},
        {"id": "claim-status", "kind": "claim-status", "body": {
            "claim_id": "claim", "status": "contested", "basis_ids": ["edge"]}},
        {"id": "experiment", "kind": "experiment-plan", "body": {
            "claim_id": "claim", "objective": "Discriminate causes", "status": "planned"}},
    ]
    payload = {"changes": changes, "judgment": asdict(judgment)}
    history = history.append(command(history, "record-interpretation", payload))
    return history, judgment


def merge_command(history, judgment, selected=None):
    return command(history, "apply-selected-merge", {
        "selected_ids": selected or ["claim-status"], "judgment": asdict(judgment),
        "disposition": "deferred" if judgment.ai_influenced else "not-required", "answers": []})


class ResearchHistoryTests(unittest.TestCase):
    def test_evidence_is_global_and_historical_views_keep_their_watermark(self):
        history, _ = branch()
        previous_head = dict(history.heads)["alternative"]
        corrected = history.append(command(history, "record-evidence-event", {
            "event_id": "corrected", "target_id": "obs-1", "run_id": "run", "action": "correct",
            "statement": "Corrected observation", "rationale": "Source correction", "supersedes_id": "event-1"}))
        self.assertEqual(corrected.view("main")["evidence"], corrected.view("alternative")["evidence"])
        current = corrected.view("alternative")
        self.assertEqual("Corrected observation", current["evidence"][0]["statement"])
        self.assertEqual("Original observation 1", current["evidence"][0]["original_statement"])
        self.assertTrue(current["evidence_changed_since_reasoning"])
        historical = corrected.view("alternative", at_operation=previous_head)
        self.assertEqual(3, historical["evidence_watermark"])
        self.assertEqual("Original observation 1", historical["evidence"][0]["statement"])
        self.assertEqual(3, history.watermark)

    def test_event_retry_is_idempotent_and_cannot_rewrite_an_old_event(self):
        history = initial()
        payload = json.loads(history.commands[0])
        self.assertIs(history, history.append(payload))
        payload["payload"]["statement"] = "Rewrite"
        with self.assertRaises(ContractError):
            history.append(payload)
        new = command(history, "record-evidence-event", dict(payload["payload"], action="correct", supersedes_id="event-1"))
        with self.assertRaises(ContractError):
            history.append(new)

    def test_correction_must_reference_latest_event_on_the_same_observation_and_run(self):
        history = initial()
        payload = {"event_id": "correction", "target_id": "obs-1", "run_id": "run", "action": "correct",
                   "statement": "Revised", "rationale": "Rechecked", "supersedes_id": "event-1"}
        for update in ({"supersedes_id": "event-2"}, {"run_id": "other"}, {"target_id": "unknown"}, {"statement": None}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                history.append(command(history, "record-evidence-event", dict(payload, **update)))

    def test_retraction_preserves_history_and_cannot_be_used_as_new_support(self):
        history, _ = branch()
        history = history.append(command(history, "record-evidence-event", {
            "event_id": "retract", "target_id": "obs-1", "run_id": "run", "action": "retract",
            "statement": None, "rationale": "Invalid source", "supersedes_id": "event-1"}))
        item = history.view("main")["evidence"][0]
        self.assertEqual("retracted", item["status"])
        self.assertEqual(["event-1", "retract"], [event["event_id"] for event in item["history"]])
        with self.assertRaises(ContractError):
            history.merge_preview(["claim-status"])

    def test_selection_closes_dependencies_preserves_source_and_reports_omissions(self):
        history, judgment = branch()
        preview = history.merge_preview(["claim-status"])
        self.assertEqual(("edge", "interpretation"), preview.selection.required)
        self.assertEqual(("experiment",), preview.selection.omitted)
        self.assertEqual(("obs-1", "obs-2", "obs-3"), preview.selection.evidence_references)
        source = history.view("alternative")
        result = history.append(merge_command(history, judgment))
        self.assertEqual(source, result.view("alternative"))
        self.assertEqual("supported", history.view("main")["claim"]["status"])
        self.assertEqual("contested", result.view("main")["claim"]["status"])
        self.assertEqual([], result.view("main")["experiment_plans"])
        self.assertEqual(source["evidence"], result.view("main")["evidence"])
        self.assertFalse(result.authorization_verified)

    def test_unknown_commands_actor_flags_versions_fields_and_scopes_are_rejected(self):
        history = initial()
        valid = command(history, "create-reasoning-branch", {})
        for update in ({"operation_type": "raw-write"}, {"actor_class": "human"}, {"schema_version": True},
                       {"schema_version": 2}, {"project_id": "other"}, {"episode_id": "other"},
                       {"payload": {"nested": True}}, {"created_at": "2026-02-30T00:00:00Z"}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                history.append(dict(valid, **update))

    def test_stale_heads_or_watermark_and_nested_or_second_branch_are_rejected(self):
        history, judgment = branch()
        valid = merge_command(history, judgment)
        for update in ({"expected_heads": {"main": "old"}}, {"evidence_watermark": 2}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                history.append(dict(valid, **update))
        with self.assertRaises(ContractError):
            history.append(command(history, "create-reasoning-branch", {}))
        with self.assertRaises(ContractError):
            history.view("invented")

    def test_unknown_missing_or_duplicate_selection_is_rejected(self):
        history, _ = branch()
        for selected in ([], ["unknown"], ["claim-status", "claim-status"], ["obs-1"], [[]], [{}], [True]):
            with self.subTest(selected=selected), self.assertRaises(ContractError):
                history.merge_preview(selected)

    def test_missing_dependencies_unknown_edge_endpoints_and_changed_kind_are_rejected(self):
        history, _ = branch()
        original = json.loads(history.commands[-1])["payload"]
        for change in (
                {"id": "edge", "kind": "scientific-edge", "body": {"edge_type": "supports", "source_id": "unknown", "target_id": "claim", "rationale": "test"}},
                {"id": "claim-status", "kind": "claim-status", "body": {"claim_id": "claim", "status": "contested", "basis_ids": ["missing"]}},
                {"id": "edge", "kind": "experiment-plan", "body": {"claim_id": "claim", "objective": "changed kind", "status": "planned"}}):
            payload = dict(original, changes=[change])
            with self.subTest(change=change), self.assertRaises(ContractError):
                history.append(command(history, "record-interpretation", payload))

    def test_human_revision_cannot_erase_previous_ai_influence(self):
        history, _ = branch(ai=True)
        payload = json.loads(history.commands[-1])["payload"]
        payload["judgment"] = asdict(Judgment.start("project", "episode").edit("Limited interpretation", "No AI claimed"))
        with self.assertRaises(ContractError):
            history.append(command(history, "record-interpretation", payload))

    def test_exact_review_binds_change_bodies_and_requires_real_authorization(self):
        history, judgment = branch(ai=True)
        cmd = merge_command(history, judgment)
        review = history.prepare_merge_review(cmd, manuscript_digest="b" * 64, session_nonce="session", sealed_at=100, expires_at=160)
        result, candidate = history.append_reviewed_merge(cmd, review, manuscript_digest="b" * 64, now=101)
        self.assertEqual(("manuscript", "understanding"), tuple(debt.kind for debt in candidate.debts))
        self.assertEqual(judgment.history, candidate.contributions)
        self.assertFalse(candidate.authorization_verified)
        self.assertFalse(result.authorization_verified)
        for changed in (dict(cmd, payload=dict(cmd["payload"], selected_ids=["experiment"])),):
            with self.assertRaises(ContractError):
                history.append_reviewed_merge(changed, review, manuscript_digest="b" * 64, now=101)
        for kwargs in ({"manuscript_digest": "c" * 64, "now": 101}, {"manuscript_digest": "b" * 64, "now": 160}):
            with self.assertRaises(ContractError):
                history.append_reviewed_merge(cmd, review, **kwargs)

    def test_replay_is_byte_stable_and_returned_views_do_not_alias_history(self):
        for ai in (False, True):
            history, judgment = branch(ai=ai)
            history = history.append(merge_command(history, judgment))
            replayed = ResearchHistory.replay(history.seed, history.commands)
            self.assertEqual(history.manifest(), replayed.manifest())
            self.assertEqual(history.commands, replayed.commands)
            view = history.view("main")
            view["evidence"][0]["statement"] = "outside edit"
            self.assertEqual("Original observation 1", history.view("main")["evidence"][0]["statement"])

    def test_reordered_or_changed_history_is_rejected_by_heads_and_identity(self):
        history, _ = branch()
        commands = list(history.commands)
        commands[0], commands[1] = commands[1], commands[0]
        with self.assertRaises(ContractError):
            ResearchHistory.replay(history.seed, tuple(commands))
        with self.assertRaises(ContractError):
            ResearchHistory.replay(history.seed, history.commands + (history.commands[0],))

    def test_resource_limits_reject_before_returning_a_new_history(self):
        history = initial()
        for i in range(3):
            history = history.append(command(history, "record-evidence-event", {
                "event_id": f"correction-{i}", "target_id": f"obs-{i + 1}", "run_id": "run", "action": "correct",
                "statement": "Corrected", "rationale": "Rechecked", "supersedes_id": f"event-{i + 1}"}))
        with self.assertRaises(ContractError):
            history.append(command(history, "record-evidence-event", {
                "event_id": "extra", "target_id": "obs-1", "run_id": "run", "action": "correct",
                "statement": "Another correction", "rationale": "Rechecked", "supersedes_id": "correction-0"}))
        self.assertEqual(6, history.watermark)

    def test_generated_command_schema_matches_the_closed_runtime_contract(self):
        path = Path(__file__).parents[2] / "schemas/research-command-v1.json"
        self.assertEqual(command_schema(), json.loads(path.read_text()))
        history = initial()
        for payload in ({"unknown": True}, {"ref": "nested"}):
            with self.assertRaises(ContractError):
                history.append(command(history, "create-reasoning-branch", payload))

    def test_changed_body_with_the_same_operation_ids_invalidates_review(self):
        history, judgment = branch()
        cmd = merge_command(history, judgment)
        review = history.prepare_merge_review(cmd, manuscript_digest="b" * 64, session_nonce="session", sealed_at=100, expires_at=160)
        records = list(history.commands)
        altered = json.loads(records[-1])
        altered["payload"]["changes"][1]["body"]["rationale"] = "A different scientific basis"
        records[-1] = canonical_bytes(altered)
        changed = ResearchHistory.replay(history.seed, tuple(records))
        self.assertEqual(history.heads, changed.heads)
        with self.assertRaises(ContractError):
            changed.append_reviewed_merge(cmd, review, manuscript_digest="b" * 64, now=101)

    def test_a_transition_that_would_exceed_export_limits_is_rejected_before_return(self):
        history = ResearchHistory.start("project", "episode", "claim", "Claim", "anchor")
        for i in range(3):
            history = history.append(command(history, "record-evidence-event", {
                "event_id": f"event-{i}", "target_id": f"obs-{i}", "run_id": "run", "action": "confirm",
                "statement": "x" * 16000, "rationale": "Checked", "supersedes_id": None}))
        history.manifest()
        with self.assertRaises(ContractError):
            history.append(command(history, "create-reasoning-branch", {}))

    def test_selected_impact_retains_evidence_to_claim_to_manuscript_paths(self):
        history, _ = branch()
        preview = json.loads(history.merge_preview(["claim-status"]).payload)
        self.assertIn(["obs-1", "interpretation", "edge", "claim", "anchor"], preview["impact_paths"])
        self.assertFalse(any("experiment" in path for path in preview["impact_paths"]))


if __name__ == "__main__":
    unittest.main()
