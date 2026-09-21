"""Synthetic variations exercise contracts, never certify source fidelity."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import unittest

from scripts.contracts import first_pass as model


FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" /
                      "saturation" / "augmented-cases.json").read_text(encoding="utf-8"))


def judged():
    return model.record_judgment(
        model.start_draft("synthetic-project", "episode-one", FIXTURE["context"], FIXTURE["claim"]),
        FIXTURE["judgment"], FIXTURE["rationale"],
    )


class AugmentedEvidenceTests(unittest.TestCase):
    def setUp(self):
        for name in ("EvidenceRevision", "EvidenceLedger", "append_evidence", "ManuscriptTarget"):
            self.assertTrue(hasattr(model, name), f"Missing synthetic contract: {name}")
        self.case = FIXTURE["cases"]["observation-correction"]
        self.original = model.EvidenceRevision("event-one", "O-03", self.case["original"])
        self.ledger = model.append_evidence(model.EvidenceLedger("synthetic-project"), self.original)
        self.correction = model.EvidenceRevision(
            "event-two", "O-03", self.case["correction"], supersedes="event-one",
        )

    def test_correction_preserves_prior_evidence_and_invalidates_review(self):
        draft = judged()
        review = model.prepare_review(draft, evidence=self.ledger)
        corrected = model.append_evidence(self.ledger, self.correction)

        self.assertEqual(1, len(self.ledger.entries))
        self.assertEqual(self.case["expected_history_length"], len(corrected.entries))
        self.assertEqual(self.case["original"], corrected.entries[0].statement)
        self.assertEqual(self.case["correction"], corrected.entries[1].statement)
        self.assertTrue(model.review_is_current(review, draft, evidence=self.ledger))
        self.assertEqual(self.case["expected_review_current"],
                         model.review_is_current(review, draft, evidence=corrected))
        self.assertFalse(model.review_is_current(review, draft))
        self.assertEqual(FIXTURE["judgment"], draft.interpretation)

    def test_identical_event_retry_is_noop_but_changed_retry_is_rejected(self):
        corrected = model.append_evidence(self.ledger, self.correction)
        self.assertIs(corrected, model.append_evidence(corrected, self.original))
        self.assertIs(corrected, model.append_evidence(corrected, self.correction))
        with self.assertRaises(model.ContractError):
            model.append_evidence(corrected, replace(self.correction, statement="different"))

    def test_correction_must_name_current_revision_of_same_observation(self):
        corrected = model.append_evidence(self.ledger, self.correction)
        bad = (
            model.EvidenceRevision("event-three", "O-03", "unlinked replacement"),
            model.EvidenceRevision("event-three", "O-03", "unknown", supersedes="missing"),
            model.EvidenceRevision("event-three", "O-02", "cross observation", supersedes="event-two"),
            model.EvidenceRevision("event-three", "O-03", "stale", supersedes="event-one"),
        )
        for event in bad:
            with self.subTest(event=event), self.assertRaises(model.ContractError):
                model.append_evidence(corrected, event)

    def test_new_observation_and_reverted_correction_do_not_revive_review(self):
        review = model.prepare_review(judged(), evidence=self.ledger)
        added = model.append_evidence(self.ledger, model.EvidenceRevision("event-other", "O-01", "new"))
        self.assertFalse(model.review_is_current(review, judged(), evidence=added))
        corrected = model.append_evidence(self.ledger, self.correction)
        reverted = model.append_evidence(corrected, model.EvidenceRevision(
            "event-three", "O-03", self.case["original"], supersedes="event-two"))
        self.assertFalse(model.review_is_current(review, judged(), evidence=reverted))

    def test_evidence_is_global_to_project_not_owned_by_reasoning_draft(self):
        second = replace(judged(), episode_id="episode-two")
        first_review = model.prepare_review(judged(), evidence=self.ledger)
        second_review = model.prepare_review(second, evidence=self.ledger)
        corrected = model.append_evidence(self.ledger, self.correction)
        self.assertFalse(model.review_is_current(first_review, judged(), evidence=corrected))
        self.assertFalse(model.review_is_current(second_review, second, evidence=corrected))
        other = replace(self.ledger, project_id="other-project")
        with self.assertRaises(model.ContractError):
            model.prepare_review(judged(), evidence=other)
        self.assertFalse(model.review_is_current(first_review, judged(), evidence=other))

    def test_review_digest_binds_history_and_detects_snapshot_substitution(self):
        review = model.prepare_review(judged(), evidence=self.ledger)
        corrected = model.append_evidence(self.ledger, self.correction)
        new_review = model.prepare_review(judged(), evidence=corrected)
        self.assertNotEqual(review.content_digest, new_review.content_digest)
        forged = replace(review, evidence=corrected)
        self.assertFalse(model.review_is_current(forged, judged(), evidence=corrected))
        self.assertTrue(model.review_is_current(new_review, judged(), evidence=corrected))

    def test_evidence_rejects_mutable_or_invalid_histories(self):
        for args in (("", "O-03", "text"), ("id", " ", "text"), ("id", "O-03", "")):
            with self.subTest(args=args), self.assertRaises(model.ContractError):
                model.EvidenceRevision(*args)
        with self.assertRaises(model.ContractError):
            model.EvidenceRevision("id", "O-03", "text", supersedes="")
        for entries in ([self.original], ("not an event",), (self.correction,),
                        (self.original, self.original)):
            with self.subTest(entries=entries), self.assertRaises(model.ContractError):
                model.EvidenceLedger("synthetic-project", entries)
        with self.assertRaises(model.ContractError):
            model.EvidenceLedger(" ")
        with self.assertRaises(model.ContractError):
            model.append_evidence("not a ledger", self.original)
        with self.assertRaises(model.ContractError):
            model.append_evidence(self.ledger, "not an event")
        with self.assertRaises(FrozenInstanceError):
            self.ledger.entries = ()
        with self.assertRaises(FrozenInstanceError):
            self.original.statement = "overwritten"

    def test_manuscript_change_or_target_omission_invalidates_review(self):
        case = FIXTURE["cases"]["changed-review-target"]
        target = model.ManuscriptTarget(case["anchor"], hashlib.sha256(case["before"].encode()).hexdigest())
        review = model.prepare_review(judged(), evidence=self.ledger, manuscript_target=target)
        self.assertTrue(model.review_is_current(review, judged(), evidence=self.ledger, manuscript_target=target))
        variants = (
            replace(target, content_digest=hashlib.sha256(case["after"].encode()).hexdigest(), revision=1),
            replace(target, anchor_id="other-anchor"),
            replace(target, revision=2),  # Same bytes restored after intervening edits.
            None,
        )
        for changed in variants:
            with self.subTest(target=changed):
                self.assertEqual(case["expected_review_current"], model.review_is_current(
                    review, judged(), evidence=self.ledger, manuscript_target=changed))
        changed = variants[0]
        new_review = model.prepare_review(judged(), evidence=self.ledger, manuscript_target=changed)
        self.assertNotEqual(review.content_digest, new_review.content_digest)
        self.assertFalse(model.review_is_current(replace(review, manuscript_target=changed), judged(),
                                                evidence=self.ledger, manuscript_target=changed))

    def test_invalid_target_or_evidence_fails_closed(self):
        for digest in ("", "g" * 64, "A" * 64, None):
            with self.subTest(digest=digest), self.assertRaises(model.ContractError):
                model.ManuscriptTarget("anchor", digest)
        for revision in (-1, True, "1"):
            with self.subTest(revision=revision), self.assertRaises(model.ContractError):
                model.ManuscriptTarget("anchor", "a" * 64, revision)
        with self.assertRaises(model.ContractError):
            model.ManuscriptTarget(" ", "a" * 64)
        for kwargs in ({"evidence": "fake"}, {"manuscript_target": "fake"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(model.ContractError):
                    model.prepare_review(judged(), **kwargs)
                self.assertFalse(model.review_is_current(model.prepare_review(judged()), judged(), **kwargs))


class AugmentedProposalTests(unittest.TestCase):
    def test_competing_interpretations_remain_unaccepted_and_cannot_merge(self):
        draft = judged()
        case = FIXTURE["cases"]["competing-interpretations"]
        proposals = [model.receive_model_proposal(draft, {"operation": "propose", "text": text})
                     for text in case["proposals"]]
        self.assertEqual(case["proposals"], [proposal.text for proposal in proposals])
        self.assertTrue(all(proposal.accepted == case["expected_accepted"] for proposal in proposals))
        with self.assertRaises(model.ContractError):
            model.receive_model_proposal(draft, {"operation": case["denied_operation"], "text": proposals[0].text})
        self.assertEqual(FIXTURE["judgment"], draft.interpretation)

    def test_overgeneralized_proposal_cannot_confirm_evidence(self):
        # This tests authority, not automatic scientific reasoning or truth detection.
        draft = judged()
        case = FIXTURE["cases"]["conditional-support"]
        proposal = model.receive_model_proposal(draft, {"operation": "propose", "text": case["proposal"]})
        self.assertEqual(case["expected_accepted"], proposal.accepted)
        with self.assertRaises(model.ContractError):
            model.receive_model_proposal(draft, {"operation": case["denied_operation"], "text": proposal.text})
        self.assertEqual(FIXTURE["judgment"], draft.interpretation)
        self.assertEqual(FIXTURE["rationale"], draft.rationale)


if __name__ == "__main__":
    unittest.main()
