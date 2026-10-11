"""Portable R3 review semantics; no OS approval or accepted-state writer."""
from dataclasses import replace
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.review import (Change, Judgment, Proposal, ReviewContext,
                                    acceptance_candidate, seal_review, select_changes)


class ResearchReviewTests(unittest.TestCase):
    def setUp(self):
        self.judgment = Judgment.start("project", "episode").edit("한정된 해석", "서로 다른 세 관찰을 보존한다.")
        self.proposal = Proposal("proposal", "project", "episode", "AI의 원래 설명", "a" * 64)
        self.changes = (Change("claim-status", "claim-status", ("interpretation",)),
                        Change("interpretation", "interpretation", ("edge", "observation")),
                        Change("edge", "scientific-edge", ("observation",)))
        self.selection = select_changes(self.changes, ("claim-status",), ("observation",))
        self.context = ReviewContext("project", "episode", "operation", "apply-selected-merge",
                                     "b" * 64, (("main", "head-1"), ("alternative", "head-2")),
                                     3, "anchor", "c" * 64, "session", 100, 160)

    def seal(self, judgment=None, disposition="not-required", answers=()):
        return seal_review(judgment or self.judgment, self.context, self.selection,
                           disposition=disposition, answers=answers)

    def test_undecided_entry_has_no_proposal_or_approved_interpretation(self):
        draft = Judgment.start("project", "episode")
        self.assertIsNone(draft.text)
        self.assertEqual((), draft.history)
        with self.assertRaises(ContractError):
            self.seal(draft)

    def test_human_edit_retains_ai_original_trace_and_intermediate_edits(self):
        draft = self.judgment.use_proposal(self.proposal).edit("限定された解釈", "AIの説明は未検証。")
        self.assertTrue(draft.ai_influenced)
        self.assertEqual("AI의 원래 설명", draft.history[1].text)
        self.assertEqual("a" * 64, draft.history[1].trace_digest)
        self.assertEqual("한정된 해석", draft.history[0].text)
        self.assertEqual(("human", "ai", "human"), tuple(item.contributor for item in draft.history))

    def test_cross_project_or_episode_proposal_is_rejected(self):
        for field in ("project_id", "episode_id"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.judgment.use_proposal(replace(self.proposal, **{field: "other"}))

    def test_proposal_ingress_cannot_request_acceptance_or_debt_closure(self):
        payload = {"schema_version": 1, "id": "proposal", "project_id": "project",
                   "episode_id": "episode", "text": "AI 원문", "trace_digest": "a" * 64,
                   "intended_operation": "record-interpretation"}
        self.assertEqual("proposal", Proposal.from_payload(payload).id)
        for update in ({"actor_class": "human"}, {"intended_operation": "close-understanding-debt"},
                       {"schema_version": True}, {"extra": "value"}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                Proposal.from_payload(dict(payload, **update))

    def test_selected_merge_closes_dependencies_without_copying_global_evidence(self):
        self.assertEqual(("claim-status",), self.selection.selected)
        self.assertEqual(("edge", "interpretation"), self.selection.required)
        self.assertEqual(("observation",), self.selection.evidence_references)
        self.assertNotIn("observation", self.selection.closure)
        self.assertEqual((), self.selection.omitted)

    def test_missing_dependency_unknown_selection_and_evidence_mutation_are_rejected(self):
        for changes, selected, evidence in ((self.changes, ("unknown",), ("observation",)),
                                             (self.changes, ("claim-status",), ()),
                                             (self.changes, ("claim-status", "claim-status"), ("observation",))):
            with self.subTest(selected=selected), self.assertRaises(ContractError):
                select_changes(changes, selected, evidence)
        with self.assertRaises(ContractError):
            Change("observation", "observation", ())

    def test_review_reuses_rationale_and_expires_at_exact_deadline(self):
        review = self.seal()
        self.assertEqual(self.judgment.rationale, review.rationale)
        self.assertTrue(review.is_current(self.context, now=159))
        self.assertFalse(review.is_current(self.context, now=160))
        self.assertFalse(review.is_current(self.context, now=99))

    def test_every_bound_context_change_invalidates_review(self):
        review = self.seal()
        changes = {"operation_digest": "d" * 64, "heads": (("main", "new-head"),),
                   "evidence_watermark": 4, "manuscript_digest": "e" * 64,
                   "session_nonce": "new-session", "episode_id": "new-episode"}
        for field, value in changes.items():
            with self.subTest(field=field):
                self.assertFalse(review.is_current(replace(self.context, **{field: value}), now=101))

    def test_ai_impact_requires_answer_or_explicit_deferral(self):
        draft = self.judgment.use_proposal(self.proposal).edit("限定された解釈", "AIは未検証。")
        with self.assertRaises(ContractError):
            self.seal(draft)
        review = self.seal(draft, "answered", ("支持範囲を限定し、原因は未検証とする。",))
        self.assertEqual("answered", review.disposition)

    def test_not_now_has_no_acceptance_or_debt_and_deferral_opens_both_obligations(self):
        draft = self.judgment.use_proposal(self.proposal).edit("한정된 해석", "추가 검증이 필요하다.")
        review = self.seal(draft, "deferred")
        pending = acceptance_candidate(review, decision="not-now")
        self.assertFalse(pending.requires_authorization)
        self.assertEqual((), pending.debts)
        accepted = acceptance_candidate(review, decision="accept")
        self.assertTrue(accepted.requires_authorization)
        self.assertFalse(accepted.authorization_verified)
        self.assertEqual(("manuscript", "understanding"), tuple(item.kind for item in accepted.debts))
        self.assertEqual(draft.history, accepted.contributions)

    def test_manual_and_answered_ai_have_no_understanding_debt(self):
        manual = acceptance_candidate(self.seal(), decision="accept")
        self.assertEqual(("manuscript",), tuple(item.kind for item in manual.debts))
        draft = self.judgment.use_proposal(self.proposal).edit("限定", "理由")
        answered = acceptance_candidate(self.seal(draft, "answered", ("説明",)), decision="accept")
        self.assertEqual(("manuscript",), tuple(item.kind for item in answered.debts))

    def test_canonical_encoding_is_unicode_stable_and_rejects_ambiguity(self):
        self.assertEqual(canonical_bytes({"b": 1, "a": "é"}), canonical_bytes({"a": "e\u0301", "b": 1}))
        for raw in (b'{"a":1,"a":2}', b'{"value":NaN}', b'{"value":1.0}'):
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                decode(raw)
        with self.assertRaises(ContractError):
            canonical_bytes({"é": 1, "e\u0301": 2})

    def test_resource_overflow_and_history_tampering_fail_before_review(self):
        with self.assertRaises(ContractError):
            self.judgment.edit("한" * 6000, "이유")
        with self.assertRaises(ContractError):
            replace(self.judgment, text="unrecorded edit")
        with self.assertRaises(ContractError):
            replace(self.context, evidence_watermark=True)

    def test_identifiers_cannot_alias_through_unicode_normalization(self):
        for value in ("é", "e\u0301", "project\nother"):
            with self.subTest(value=value), self.assertRaises(ContractError):
                Judgment.start(value, "episode")

    def test_tampered_review_is_not_current_and_cannot_produce_an_acceptance_candidate(self):
        altered = replace(self.seal(), payload=b'{"changed":true}')
        self.assertFalse(altered.is_current(self.context, now=101))
        with self.assertRaises(ContractError):
            acceptance_candidate(altered, decision="accept")


if __name__ == "__main__":
    unittest.main()
