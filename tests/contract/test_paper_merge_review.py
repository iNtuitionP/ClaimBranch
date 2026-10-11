from copy import deepcopy
from dataclasses import asdict, replace
import unittest

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.review import acceptance_candidate, seal_review
from tests.contract.test_paper_episodes import command, first_episode, second_episode
from tests.contract.test_paper_history import experiment


def merge_command(history, judgment, *, selected=None, disposition="not-required", answers=None):
    return command(history, "apply-selected-merge", {
        "selected_ids": selected or ["status-pruning"], "judgment": asdict(judgment),
        "disposition": disposition, "answers": answers or []}, "episode-two", operation_id="reviewed-merge")


def seal(history, cmd):
    return history.prepare_merge_review(cmd, manuscript_digest="b" * 64,
        session_nonce="session", sealed_at=100, expires_at=200)


class PaperMergeReviewTests(unittest.TestCase):
    def test_exact_second_episode_review_retains_both_judgments(self):
        history, judgment = second_episode(first_episode())
        original = history.manifest()
        cmd = merge_command(history, judgment)
        review = seal(history, cmd)
        self.assertEqual(3, review.context.schema_version)
        self.assertEqual("paper-review-v3", review.context.rule_version)
        self.assertEqual(["episode", "episode-two"], [item.episode_id for item in review.source_judgments])
        self.assertEqual("episode-two", review.context.episode_id)
        self.assertEqual(["status-pruning"], list(review.selection.selected))
        self.assertEqual(["obs-1", "obs-2"], list(review.selection.evidence_references))
        self.assertEqual(2, len(decode(review.payload)["source_judgments"]))
        merged, candidate = history.append_reviewed_merge(cmd, review, manuscript_digest="b" * 64, now=199)
        self.assertEqual("contested", next(row for row in merged.view("main")["claims"] if row["id"] == "claim-pruning-detail")["status"])
        self.assertEqual(["manuscript"], [item.kind for item in candidate.debts])
        self.assertEqual(review.source_judgments, candidate.source_judgments)
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)
        self.assertEqual(original, history.manifest())

    def test_inherited_ai_survives_manual_judgment_and_requires_explanation(self):
        history, judgment = second_episode(first_episode(ai=True))
        self.assertFalse(judgment.ai_influenced)
        with self.assertRaises(ContractError):
            seal(history, merge_command(history, judgment))
        review = seal(history, merge_command(history, judgment, disposition="deferred"))
        self.assertEqual(["human", "ai", "human"], [item.contributor for item in review.source_judgments[0].history])
        candidate = acceptance_candidate(review, decision="accept")
        self.assertEqual(["manuscript", "understanding"], [item.kind for item in candidate.debts])
        pending = acceptance_candidate(review, decision="not-now")
        self.assertFalse(pending.requires_authorization)
        self.assertEqual((), pending.debts)
        answered = seal(history, merge_command(history, judgment, disposition="answered",
            answers=["The corrected count challenges pruning; the second seed remains untested."]))
        self.assertEqual(["manuscript"], [item.kind for item in acceptance_candidate(answered, decision="accept").debts])

    def test_edited_selection_rationale_answers_file_and_clock_cannot_reuse_review(self):
        history, judgment = second_episode(first_episode(ai=True))
        cmd = merge_command(history, judgment, disposition="deferred")
        review = seal(history, cmd)
        for update in ({"selected_ids": ["edge-pruning"]},
                       {"judgment": asdict(judgment.edit(judgment.text, "A newly supplied rationale."))},
                       {"disposition": "answered", "answers": ["A new explanation."]}):
            altered = deepcopy(cmd)
            altered["payload"].update(update)
            with self.subTest(update=update), self.assertRaises(ContractError):
                history.append_reviewed_merge(altered, review, manuscript_digest="b" * 64, now=101)
        for manuscript, now in (("c" * 64, 101), ("b" * 64, 99), ("b" * 64, 200)):
            with self.subTest(manuscript=manuscript, now=now), self.assertRaises(ContractError):
                history.append_reviewed_merge(cmd, review, manuscript_digest=manuscript, now=now)

    def test_unrelated_experiment_also_invalidates_review_with_same_heads_and_watermark(self):
        history, judgment = second_episode(first_episode())
        cmd = merge_command(history, judgment)
        review = seal(history, cmd)
        changed = history.append(command(history, "record-experiment", dict(experiment(), id="another-run"), "episode-two"))
        self.assertEqual(history.heads, changed.heads)
        self.assertEqual(history.watermark, changed.watermark)
        with self.assertRaises(ContractError):
            changed.append_reviewed_merge(cmd, review, manuscript_digest="b" * 64, now=101)

    def test_new_evidence_and_changed_operation_identity_require_fresh_review(self):
        history, judgment = second_episode(first_episode())
        cmd = merge_command(history, judgment)
        review = seal(history, cmd)
        event = {"event_id": "another-recount", "target_id": "obs-1", "run_id": "run-accuracy",
                 "action": "correct", "statement": "A further synthetic recount gives 1.3 points.",
                 "value": "1.3", "rationale": "Additional counted error.", "supersedes_id": "recount"}
        changed = history.append(command(history, "record-evidence-event", event, "episode-two"))
        updated = dict(cmd, evidence_watermark=changed.watermark)
        with self.assertRaises(ContractError):
            changed.append_reviewed_merge(updated, review, manuscript_digest="b" * 64, now=101)
        for override in ({"id": "different-operation"}, {"project_id": "other"}, {"episode_id": "episode"}):
            with self.subTest(override=override), self.assertRaises(ContractError):
                history.append_reviewed_merge(dict(cmd, **override), review, manuscript_digest="b" * 64, now=101)

    def test_source_chain_current_episode_cannot_be_replaced_by_matching_manual_text(self):
        history, judgment = second_episode(first_episode(ai=True))
        review = seal(history, merge_command(history, judgment, disposition="deferred"))
        changed = judgment.edit(judgment.text, "A later rationale not present in the reviewed judgment.")
        with self.assertRaises(ContractError):
            seal_review(judgment, review.context, review.selection, disposition="deferred",
                        source_judgments=(review.source_judgments[0], changed))
        with self.assertRaises(ContractError):
            seal_review(judgment, replace(review.context, schema_version=2, rule_version="paper-review-v2"),
                        review.selection, disposition="deferred", source_judgments=review.source_judgments)

    def test_erased_or_substituted_source_chains_are_rejected_by_owned_history(self):
        history, judgment = second_episode(first_episode(ai=True))
        cmd = merge_command(history, judgment, disposition="deferred")
        review = seal(history, cmd)
        altered = replace(review, source_judgments=(judgment,))
        self.assertFalse(altered.is_current(review.context, now=101))
        with self.assertRaises(ContractError):
            acceptance_candidate(altered, decision="accept")
        # A caller can hash their own input; only reconstruction from the owned
        # history can establish which source provenance belongs to this merge.
        forged = seal_review(judgment, review.context, review.selection,
            disposition="not-required", source_judgments=(judgment,))
        with self.assertRaises(ContractError):
            history.append_reviewed_merge(cmd, forged, manuscript_digest="b" * 64, now=101)
        for sources in ((), (judgment, judgment), (replace(judgment, project_id="other"),)):
            with self.subTest(sources=sources), self.assertRaises(ContractError):
                seal_review(judgment, review.context, review.selection,
                    disposition="not-required", source_judgments=sources)

    def test_merge_projection_keeps_exact_amendments_separate_from_inherited_references(self):
        history, _ = second_episode(first_episode())
        original = history.manifest()
        value = decode(history.preview_merge_changes(["edge-pruning"]).payload)
        self.assertEqual(["edge-pruning"], value["selection"]["selected"])
        self.assertEqual([], value["selection"]["required"])
        self.assertEqual(["interpretation-two", "status-pruning"], value["selection"]["omitted"])
        self.assertIn("claim-pruning-detail", value["selection"]["existing_references"])
        self.assertEqual(["obs-1"], value["selection"]["evidence_references"])
        self.assertEqual(1, len(value["after"]["interpretations"]))
        self.assertEqual(["episode", "episode-two"], [item["episode_id"] for item in value["after"]["judgments"]])
        self.assertEqual(value["before"]["evidence"], value["after"]["evidence"])
        self.assertEqual(original, history.manifest())


if __name__ == "__main__":
    unittest.main()
