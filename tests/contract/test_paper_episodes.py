from copy import deepcopy
from dataclasses import asdict
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import Judgment
from tests.contract.test_paper_history import paper


def command(history, kind, payload, episode="episode", *, operation_id=None):
    return {"schema_version": 3, "id": operation_id or f"series-op-{len(history.commands) + 1}",
            "project_id": "project", "episode_id": episode, "created_at": "2026-09-23T00:00:00Z",
            "operation_type": kind, "expected_heads": dict(history.heads),
            "evidence_watermark": history.watermark, "payload": payload}


def first_episode(*, ai=False, merge=True, close=True):
    source, judgment = paper(ai=ai)
    seed = decode(source.seed)
    history = ResearchHistory.start_paper_series(seed["project_id"], seed["paper_title"],
        seed["claim_id"], seed["claim_statement"], seed["anchor_id"])
    history = history.append(command(history, "open-episode", {
        "title": "Initial pruning and quantization comparison", "question": "Do these settings meet the accuracy budget?"}))
    for raw in source.commands:
        original = decode(raw)
        history = history.append(command(history, original["operation_type"], original["payload"]))
    if merge:
        history = history.append(command(history, "apply-selected-merge", {
            "selected_ids": [item["id"] for item in source.view("alternative")["changes"]],
            "judgment": asdict(judgment), "disposition": "deferred" if ai else "not-required", "answers": []}))
    if close:
        history = history.append(command(history, "close-episode", {}))
    return history


def second_episode(history, *, correction=True):
    history = history.append(command(history, "open-episode", {
        "title": "Recount of the pruning result", "question": "Does the corrected seed-42 loss change the claim?"}, "episode-two"))
    if correction:
        history = history.append(command(history, "record-evidence-event", {
            "event_id": "recount", "target_id": "obs-1", "run_id": "run-accuracy", "action": "correct",
            "statement": "Synthetic recount: seed-42 pruning loses 1.2 percentage points of accuracy.",
            "value": "1.2", "rationale": "Illustrative corrected count on the same split, not another experiment.",
            "supersedes_id": "event-1"}, "episode-two"))
    history = history.append(command(history, "create-reasoning-branch", {}, "episode-two"))
    judgment = Judgment.start("project", "episode-two").edit(
        "The corrected seed-42 pruning loss exceeds the one-point budget; quantization remains within it.",
        "The same observation was corrected to 1.2 percentage points; the separate 0.7-point quantization result is unchanged.")
    edge = deepcopy(next(item for item in history.view("alternative")["changes"] if item["id"] == "edge-pruning"))
    edge["body"].update(edge_type="challenges", rationale="The corrected 1.2-point loss exceeds the stated one-point budget.")
    changes = [{"id": "interpretation-two", "kind": "interpretation", "body": {
        "statement": judgment.text, "observation_ids": ["obs-1", "obs-2"]}}, edge,
        {"id": "status-pruning", "kind": "claim-status", "body": {
            "claim_id": "claim-pruning-detail", "status": "contested", "basis_ids": ["edge-pruning", "interpretation-two"]}}]
    history = history.append(command(history, "record-interpretation", {"changes": changes, "judgment": asdict(judgment)}, "episode-two"))
    return history, judgment


class PaperEpisodesTests(unittest.TestCase):
    def test_next_episode_keeps_global_evidence_and_previous_interpretation(self):
        first = first_episode()
        original = first.manifest()
        second, judgment = second_episode(first)
        second = second.append(command(second, "apply-selected-merge", {
            "selected_ids": ["status-pruning"], "judgment": asdict(judgment),
            "disposition": "not-required", "answers": []}, "episode-two"))
        second = second.append(command(second, "close-episode", {}, "episode-two"))
        view = second.view("main")
        self.assertEqual(3, view["schema_version"])
        self.assertEqual(["interpretation", "interpretation-two"], [item["id"] for item in view["interpretations"]])
        self.assertEqual(["episode", "episode-two"], [item["episode_id"] for item in view["judgments"]])
        self.assertEqual("1.2", view["evidence"][0]["value"])
        self.assertEqual("0.4", view["evidence"][0]["history"][0]["value"])
        self.assertEqual(["obs-1", "obs-2"], [item["id"] for item in view["evidence"]])
        self.assertEqual("contested", next(item for item in view["claims"] if item["id"] == "claim-pruning-detail")["status"])
        self.assertEqual(original, first.manifest())
        self.assertEqual(second.manifest(), ResearchHistory.replay(second.seed, second.commands).manifest())
        self.assertTrue(all(item["status"] == "closed" for item in second.episodes()))
        self.assertFalse(second.authorization_verified)

    def test_closed_episode_uses_global_evidence_but_explicit_past_view_is_frozen(self):
        first = first_episode()
        closing = decode(first.commands[-1])["id"]
        second, _ = second_episode(first)
        archived = second.view("main", episode_id="episode")
        self.assertEqual("1.2", archived["evidence"][0]["value"])
        self.assertEqual(1, len(archived["interpretations"]))
        self.assertTrue(archived["evidence_changed_since_reasoning"])
        self.assertEqual(first.view("main"), second.view("main", at_operation=closing, episode_id="episode"))
        with self.assertRaises(ContractError):
            second.view("main", at_operation=closing, episode_id="episode-two")

    def test_partial_merge_keeps_omitted_new_interpretation_and_prior_judgment_separate(self):
        history, judgment = second_episode(first_episode(), correction=False)
        preview = history.merge_preview(["edge-pruning"])
        self.assertNotIn("interpretation-two", preview.selection.closure)
        merged = history.append(command(history, "apply-selected-merge", {
            "selected_ids": ["edge-pruning"], "judgment": asdict(judgment),
            "disposition": "not-required", "answers": []}, "episode-two"))
        self.assertEqual(["interpretation"], [item["id"] for item in merged.view("main")["interpretations"]])
        self.assertEqual(2, len(merged.view("main")["judgments"]))
        self.assertEqual(2, len(merged.view("alternative")["interpretations"]))

    def test_inherited_ai_cannot_be_laundered_by_a_new_manual_episode(self):
        history, judgment = second_episode(first_episode(ai=True))
        payload = {"selected_ids": ["status-pruning"], "judgment": asdict(judgment), "disposition": "not-required", "answers": []}
        with self.assertRaises(ContractError):
            history.append(command(history, "apply-selected-merge", payload, "episode-two"))
        merged = history.append(command(history, "apply-selected-merge", dict(payload, disposition="deferred"), "episode-two"))
        self.assertEqual(["human", "ai", "human"], [item["contributor"] for item in merged.view("main")["judgments"][0]["history"]])
        self.assertFalse(judgment.ai_influenced)

    def test_episode_identity_active_slot_context_and_one_merge_are_enforced(self):
        history = first_episode(close=False)
        for kind, payload, episode in (("open-episode", {"title": "x", "question": "y"}, "episode-two"),
                                       ("close-episode", {}, "wrong"), ("create-reasoning-branch", {}, "episode")):
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                history.append(command(history, kind, payload, episode))
        closed = history.append(command(history, "close-episode", {}))
        for kind, payload in (("close-episode", {}), ("record-experiment", {}),
                              ("open-episode", {"title": "x", "question": "y"})):
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                closed.append(command(closed, kind, payload))
        second, judgment = second_episode(closed)
        merge = command(second, "apply-selected-merge", {"selected_ids": ["status-pruning"],
            "judgment": asdict(judgment), "disposition": "not-required", "answers": []}, "episode-two")
        merged = second.append(merge)
        self.assertIs(merged, merged.append(merge))
        with self.assertRaises(ContractError):
            merged.append(command(merged, "apply-selected-merge", merge["payload"], "episode-two"))

    def test_old_interpretations_and_omitted_identities_cannot_be_reassigned(self):
        first = first_episode(merge=False)
        second = first.append(command(first, "open-episode", {"title": "x", "question": "y"}, "episode-two"))
        second = second.append(command(second, "create-reasoning-branch", {}, "episode-two"))
        source = first.view("alternative")["changes"]
        judgment = Judgment.start("project", "episode-two").edit("A new reading.", "A new reason.")
        with self.assertRaises(ContractError):
            second.append(command(second, "record-interpretation", {
                "changes": source, "judgment": asdict(judgment)}, "episode-two"))
        history, judgment = second_episode(first_episode())
        old = deepcopy(history.view("main")["interpretations"][0])
        old["body"]["statement"] = judgment.text
        with self.assertRaises(ContractError):
            history.preview_paper_changes("main", [old], ["interpretation"], judgment)

    def test_unmerged_close_preserves_alternative_without_leaking_it_to_the_next_main(self):
        first = first_episode(merge=False)
        next_ = first.append(command(first, "open-episode", {"title": "Next question", "question": "What remains?"}, "episode-two"))
        self.assertEqual([], next_.view("main")["changes"])
        self.assertTrue(next_.view("alternative", episode_id="episode")["changes"])
        self.assertEqual("unmerged", first.episodes()[0]["outcome"])
        self.assertEqual(dict(first.heads), next_.episodes()[1]["baseline_heads"])
        self.assertEqual(2, next_.episodes()[1]["baseline_watermark"])

    def test_versions_retry_and_closed_schemas_stay_explicit(self):
        old, _ = paper()
        with self.assertRaises(ContractError):
            old.append(command(old, "open-episode", {"title": "x", "question": "y"}))
        first = first_episode()
        with self.assertRaises(ContractError):
            first.append(dict(command(first, "open-episode", {"title": "x", "question": "y"}, "next"), approved=True))
        replayed = first.append(decode(first.commands[0]))
        self.assertIs(first, replayed)
        changed = decode(first.commands[0])
        changed["payload"]["title"] = "Changed retry"
        with self.assertRaises(ContractError):
            first.append(changed)
        bad_seed = dict(decode(first.seed), schema_version=True)
        with self.assertRaises(ContractError):
            ResearchHistory(canonical_bytes(bad_seed))

    def test_new_episode_and_records_cannot_alias_an_operation(self):
        first = first_episode()
        old_operation = decode(first.commands[0])["id"]
        with self.assertRaises(ContractError):
            first.append(command(first, "open-episode", {"title": "x", "question": "y"}, old_operation))
        history, judgment = second_episode(first)
        new = {"id": old_operation, "kind": "claim", "body": {
            "role": "main", "statement": "Another claim.", "scope": "Synthetic only.", "parent_ids": ["thesis"]}}
        with self.assertRaises(ContractError):
            history.preview_paper_changes("alternative", [new], [old_operation], judgment)

    def test_preview_cannot_invent_a_second_interpretation_in_the_same_episode(self):
        history, judgment = second_episode(first_episode())
        extra = {"id": "extra-interpretation", "kind": "interpretation", "body": {
            "statement": judgment.text, "observation_ids": ["obs-2"]}}
        with self.assertRaises(ContractError):
            history.preview_paper_changes("alternative", [extra], ["extra-interpretation"], judgment)

    def test_episode_limit_is_explicit_and_does_not_replace_the_v0_ledger(self):
        history = ResearchHistory.start_paper_series("project", "Synthetic paper", "thesis", "Thesis", "anchor")
        self.assertEqual([], history.episodes())
        for number in range(8):
            episode = f"episode-{number}"
            history = history.append(command(history, "open-episode", {"title": "Question", "question": "What changed?"}, episode))
            history = history.append(command(history, "close-episode", {}, episode))
        with self.assertRaises(ContractError):
            history.append(command(history, "open-episode", {"title": "x", "question": "y"}, "episode-nine"))
        self.assertEqual(8, len(history.episodes()))
        self.assertTrue(all(item["outcome"] == "unmerged" for item in history.episodes()))
        self.assertNotIn("protocol_version", decode(history.manifest()))

    def test_old_retracted_basis_does_not_stop_an_unrelated_new_plan(self):
        history = first_episode()
        history = history.append(command(history, "open-episode", {"title": "New plan", "question": "What should be measured?"}, "episode-two"))
        history = history.append(command(history, "record-evidence-event", {
            "event_id": "retract", "target_id": "obs-1", "run_id": "run-accuracy", "action": "retract",
            "statement": None, "value": None, "rationale": "Synthetic invalid source.", "supersedes_id": "event-1"}, "episode-two"))
        history = history.append(command(history, "create-reasoning-branch", {}, "episode-two"))
        judgment = Judgment.start("project", "episode-two").edit("Recheck the pruning measurement.", "The quantization result alone cannot establish pruning accuracy.")
        plan = deepcopy(next(item for item in history.view("main")["changes"] if item["id"] == "replication"))
        plan["body"]["objective"] = "Measure pruning accuracy on a valid source before drawing another conclusion."
        history = history.append(command(history, "record-interpretation", {
            "changes": [plan, {"id": "interpretation-two", "kind": "interpretation", "body": {
                "statement": judgment.text, "observation_ids": ["obs-2"]}}], "judgment": asdict(judgment)}, "episode-two"))
        merged = history.append(command(history, "apply-selected-merge", {"selected_ids": ["replication"],
            "judgment": asdict(judgment), "disposition": "not-required", "answers": []}, "episode-two"))
        self.assertEqual("retracted", merged.view("main")["evidence"][0]["status"])
        self.assertEqual("0.4", merged.view("main")["evidence"][0]["value"])

    def test_closed_episode_cannot_be_reviewed_as_an_active_merge(self):
        history = first_episode()
        self.assertNotIn("complete", history.episodes()[0].values())
        with self.assertRaises(ContractError):
            history.prepare_merge_review({}, manuscript_digest="a" * 64, session_nonce="nonce", sealed_at=100, expires_at=200)


if __name__ == "__main__":
    unittest.main()
