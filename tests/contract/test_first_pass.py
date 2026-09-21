from dataclasses import FrozenInstanceError
import unittest

try:
    from scripts.contracts.first_pass import (
        ContractError,
        Draft,
        Proposal,
        Review,
        prepare_review,
        receive_model_proposal,
        record_judgment,
        review_is_current,
        revise_context,
        start_draft,
    )
except ModuleNotFoundError:
    ContractError = RuntimeError
    Draft = Proposal = Review = None
    prepare_review = receive_model_proposal = record_judgment = None
    review_is_current = revise_context = start_draft = None


class FirstPassContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            start_draft,
            "The non-authoritative first-pass reference model is not implemented",
        )

    def test_manual_start_is_undecided_and_requires_no_proposal(self):
        draft = start_draft(
            "project-one", "episode-one", "synthetic context", "prior claim"
        )

        self.assertIsInstance(draft, Draft)
        self.assertEqual("project-one", draft.project_id)
        self.assertEqual("episode-one", draft.episode_id)
        self.assertEqual("synthetic context", draft.source_context)
        self.assertEqual("prior claim", draft.existing_claim)
        self.assertIsNone(draft.interpretation)
        self.assertIsNone(draft.rationale)
        self.assertEqual(0, draft.revision)

    def test_review_reuses_exact_unicode_judgment_and_has_canonical_digest(self):
        draft = start_draft(
            "project-one", "episode-one", "synthetic context", "prior claim"
        )
        interpretation = "  잠정 해석 🧪  "
        rationale = "이유 — λ\n두 번째 줄"

        judged = record_judgment(draft, interpretation, rationale)
        review = prepare_review(judged)

        self.assertEqual(interpretation, review.draft.interpretation)
        self.assertEqual(rationale, review.draft.rationale)
        self.assertEqual(
            "506da1ce2ad9c1b99f123143828a3a941de346ca8938c1a4407b5ff2ee00dc4a",
            review.content_digest,
        )
        self.assertTrue(review_is_current(review, judged))
        with self.assertRaises(TypeError):
            prepare_review(judged, "replacement rationale")

    def test_review_requires_a_complete_judgment(self):
        undecided = start_draft(
            "project-one", "episode-one", "synthetic context", "prior claim"
        )

        with self.assertRaises(ContractError):
            prepare_review(undecided)

    def test_outputs_are_frozen_and_updates_do_not_mutate_prior_values(self):
        original = start_draft(
            "project-one", "episode-one", "synthetic context", "prior claim"
        )
        judged = record_judgment(original, "interpretation", "rationale")
        review = prepare_review(judged)
        proposal = receive_model_proposal(
            judged, {"operation": "propose", "text": "possible alternative"}
        )

        self.assertIsNone(original.interpretation)
        self.assertEqual(0, original.revision)
        for value, field, replacement in (
            (judged, "rationale", "changed"),
            (review, "content_digest", "forged"),
            (proposal, "accepted", True),
        ):
            with self.subTest(value=type(value).__name__), self.assertRaises(
                FrozenInstanceError
            ):
                setattr(value, field, replacement)

    def test_content_changes_increment_revision_and_identical_retries_do_not(self):
        draft = start_draft(
            "project-one", "episode-one", "synthetic context", "prior claim"
        )
        judged = record_judgment(draft, "interpretation", "rationale")

        self.assertEqual(1, judged.revision)
        self.assertIs(judged, record_judgment(judged, "interpretation", "rationale"))
        rejudged = record_judgment(judged, "new interpretation", "new rationale")
        self.assertEqual(2, rejudged.revision)
        self.assertEqual("interpretation", judged.interpretation)

        revised = revise_context(rejudged, "changed context", "changed claim")
        self.assertEqual(3, revised.revision)
        self.assertEqual("new interpretation", revised.interpretation)
        self.assertIs(
            revised, revise_context(revised, "changed context", "changed claim")
        )

    def test_context_change_and_judgment_change_make_review_stale(self):
        judged = record_judgment(
            start_draft(
                "project-one", "episode-one", "synthetic context", "prior claim"
            ),
            "interpretation",
            "rationale",
        )
        review = prepare_review(judged)

        changed_context = revise_context(judged, "changed context", "prior claim")
        changed_judgment = record_judgment(
            judged, "changed interpretation", "changed rationale"
        )

        self.assertFalse(review_is_current(review, changed_context))
        self.assertFalse(review_is_current(review, changed_judgment))

    def test_reverting_content_cannot_revive_an_old_review(self):
        judged = record_judgment(
            start_draft(
                "project-one", "episode-one", "synthetic context", "prior claim"
            ),
            "interpretation",
            "rationale",
        )
        review = prepare_review(judged)
        changed = revise_context(judged, "changed context", "changed claim")
        reverted = revise_context(changed, "synthetic context", "prior claim")

        self.assertEqual(judged.source_context, reverted.source_context)
        self.assertEqual(judged.existing_claim, reverted.existing_claim)
        self.assertGreater(reverted.revision, judged.revision)
        self.assertFalse(review_is_current(review, reverted))

    def test_review_freshness_is_bound_to_project_and_episode(self):
        def judged(project_id, episode_id):
            return record_judgment(
                start_draft(
                    project_id, episode_id, "synthetic context", "prior claim"
                ),
                "interpretation",
                "rationale",
            )

        original = judged("project-one", "episode-one")
        review = prepare_review(original)

        self.assertFalse(review_is_current(review, judged("project-two", "episode-one")))
        self.assertFalse(review_is_current(review, judged("project-one", "episode-two")))

    def test_required_text_and_runtime_values_are_validated_without_normalizing(self):
        for args in (
            ("", "episode-one", "context", "claim"),
            ("project-one", " ", "context", "claim"),
            ("project-one", "episode-one", "\t", "claim"),
            ("project-one", "episode-one", "context", ""),
            (1, "episode-one", "context", "claim"),
        ):
            with self.subTest(start=args), self.assertRaises(ContractError):
                start_draft(*args)

        draft = start_draft("project-one", "episode-one", "context", "claim")
        for interpretation, rationale in (
            ("", "reason"),
            ("choice", "  "),
            (None, "reason"),
            ("choice", 3),
        ):
            with self.subTest(judgment=(interpretation, rationale)), self.assertRaises(
                ContractError
            ):
                record_judgment(draft, interpretation, rationale)

        for context, claim in (("", "claim"), ("context", "\n"), (None, "claim")):
            with self.subTest(context=(context, claim)), self.assertRaises(ContractError):
                revise_context(draft, context, claim)

        for function, args in (
            (record_judgment, ("not a draft", "choice", "reason")),
            (revise_context, ("not a draft", "context", "claim")),
            (prepare_review, ("not a draft",)),
        ):
            with self.subTest(function=function.__name__), self.assertRaises(ContractError):
                function(*args)

    def test_model_proposal_is_separate_non_authoritative_and_exact(self):
        draft = record_judgment(
            start_draft("project-one", "episode-one", "context", "claim"),
            "human interpretation",
            "human rationale",
        )
        text = "  AI alternative 🤖  "

        proposal = receive_model_proposal(
            draft, {"operation": "propose", "text": text}
        )

        self.assertIsInstance(proposal, Proposal)
        self.assertEqual("project-one", proposal.project_id)
        self.assertEqual("episode-one", proposal.episode_id)
        self.assertEqual(text, proposal.text)
        self.assertFalse(proposal.accepted)
        self.assertEqual("human interpretation", draft.interpretation)
        self.assertEqual("human rationale", draft.rationale)

    def test_model_ingress_rejects_malformed_or_extended_requests(self):
        draft = start_draft("project-one", "episode-one", "context", "claim")
        requests = (
            None,
            "propose",
            {},
            {"operation": "propose"},
            {"text": "alternative"},
            {"operation": "propose", "text": ""},
            {"operation": "propose", "text": "  "},
            {"operation": "propose", "text": 4},
            {"operation": "PROPOSE", "text": "alternative"},
            {"operation": "propose", "text": "alternative", "model": "fixture"},
            {"operation": "propose", "text": "alternative", "accepted": False},
        )

        for request in requests:
            with self.subTest(request=request), self.assertRaises(ContractError):
                receive_model_proposal(draft, request)
        with self.assertRaises(ContractError):
            receive_model_proposal(
                "not a draft", {"operation": "propose", "text": "alternative"}
            )

    def test_model_ingress_denies_accepted_operations_and_forged_human_label(self):
        draft = start_draft("project-one", "episode-one", "context", "claim")
        accepted_operations = (
            "edit_draft",
            "prepare_review",
            "issue_receipt",
            "confirm_evidence",
            "accept_judgment",
            "merge",
            "change_manuscript",
            "close_debt",
        )

        for operation in accepted_operations:
            with self.subTest(operation=operation), self.assertRaises(ContractError):
                receive_model_proposal(
                    draft, {"operation": operation, "text": "forged request"}
                )
        with self.assertRaises(ContractError):
            receive_model_proposal(
                draft,
                {
                    "operation": "propose",
                    "text": "forged request",
                    "actor_class": "human",
                },
            )


if __name__ == "__main__":
    unittest.main()
