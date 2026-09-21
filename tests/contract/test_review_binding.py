"""Synthetic review/action matching; deliberately not human authorization."""

from dataclasses import asdict, FrozenInstanceError, replace
import hashlib
import unittest

from scripts.contracts.first_pass import (
    ContractError, EvidenceLedger, EvidenceRevision, ManuscriptTarget, Review,
    append_evidence, prepare_review, receive_model_proposal, record_judgment,
    revise_context, start_draft,
)

try:
    from scripts.contracts.review_binding import (
        BoundReview, bind_review, matches_bound_review,
    )
except ModuleNotFoundError:
    BoundReview = bind_review = matches_bound_review = None


class ReviewBindingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(bind_review, "Review/action binding is not implemented")
        self.draft = record_judgment(
            start_draft("project-one", "episode-one", "synthetic context", "prior claim"),
            "  잠정 해석 🧪  ", "이유 — λ\n두 번째 줄",
        )
        self.review = prepare_review(self.draft)
        self.arguments = dict(operation_digest="a" * 64,
                              session_nonce="synthetic-session", expires_at=20)

    def matches(self, binding, current=None, **changes):
        arguments = dict(operation_digest="a" * 64,
                         session_nonce="synthetic-session", now=19)
        arguments.update(changes)
        return matches_bound_review(binding, self.review if current is None else current,
                                    **arguments)

    def test_exact_binding_matches_repeatedly_without_issuing_or_consuming_authority(self):
        binding = bind_review(self.review, **self.arguments)
        self.assertTrue(self.matches(binding))
        self.assertTrue(self.matches(binding))  # not a single-use receipt
        self.assertEqual(binding, bind_review(self.review, **self.arguments))

    def test_digest_uses_versioned_canonical_utf8_and_full_review(self):
        binding = bind_review(self.review, **self.arguments)
        # Literal independently specified bytes, not the implementation's serializer.
        canonical = (
            '{"expires_at":20,"operation_digest":"' + "a" * 64 + '",'
            '"review":{"content_digest":"506da1ce2ad9c1b99f123143828a3a941de346ca8938c1a4407b5ff2ee00dc4a",'
            '"draft":{"episode_id":"episode-one","existing_claim":"prior claim",'
            '"interpretation":"  잠정 해석 🧪  ","project_id":"project-one",'
            '"rationale":"이유 — λ\\n두 번째 줄","revision":1,"source_context":"synthetic context"},'
            '"evidence":null,"manuscript_target":null},"schema_version":1,'
            '"session_nonce":"synthetic-session"}'
        )
        self.assertEqual(hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                         binding.binding_digest)

    def test_action_and_session_are_exact_not_normalized(self):
        binding = bind_review(self.review, **self.arguments)
        self.assertFalse(self.matches(binding, operation_digest="b" * 64))
        self.assertFalse(self.matches(binding, session_nonce="other-session"))
        self.assertFalse(self.matches(binding, session_nonce=" synthetic-session "))
        for changes in ({"operation_digest": "b" * 64},
                        {"session_nonce": "other-session"}, {"expires_at": 21}):
            changed = bind_review(self.review, **dict(self.arguments, **changes))
            self.assertNotEqual(binding.binding_digest, changed.binding_digest)

    def test_expiry_boundary_and_zero_are_not_extended(self):
        binding = bind_review(self.review, **self.arguments)
        for now, expected in ((0, True), (19, True), (20, False), (21, False)):
            with self.subTest(now=now):
                self.assertEqual(expected, self.matches(binding, now=now))
        zero = bind_review(self.review, **dict(self.arguments, expires_at=0))
        self.assertFalse(self.matches(zero, now=0))

    def test_other_project_episode_and_reverted_context_do_not_match(self):
        binding = bind_review(self.review, **self.arguments)
        changed = revise_context(self.draft, "changed context", "prior claim")
        reverted = revise_context(changed, "synthetic context", "prior claim")
        for draft in (replace(self.draft, project_id="other-project"),
                      replace(self.draft, episode_id="other-episode"), changed, reverted,
                      record_judgment(self.draft, "new interpretation", "new rationale")):
            with self.subTest(draft=draft):
                current = prepare_review(draft)
                self.assertFalse(self.matches(binding, current))
                self.assertNotEqual(binding.binding_digest,
                                    bind_review(current, **self.arguments).binding_digest)

    def test_evidence_target_changes_and_omissions_invalidate_binding(self):
        evidence = EvidenceLedger("project-one", (
            EvidenceRevision("event-one", "observation-one", "synthetic result"),))
        target = ManuscriptTarget("anchor-one", "c" * 64, 1)
        review = prepare_review(self.draft, evidence=evidence, manuscript_target=target)
        binding = bind_review(review, **self.arguments)
        self.assertTrue(self.matches(binding, review))
        corrected = append_evidence(evidence, EvidenceRevision(
            "event-two", "observation-one", "corrected result", "event-one"))
        for ledger, manuscript in ((None, target), (evidence, None), (corrected, target),
                                   (evidence, replace(target, revision=2)),
                                   (evidence, replace(target, content_digest="d" * 64)),
                                   (evidence, replace(target, anchor_id="other-anchor"))):
            with self.subTest(ledger=ledger, manuscript=manuscript):
                current = prepare_review(self.draft, evidence=ledger, manuscript_target=manuscript)
                self.assertFalse(self.matches(binding, current))
                self.assertNotEqual(binding.binding_digest,
                                    bind_review(current, **self.arguments).binding_digest)

    def test_substituted_binding_fields_cannot_reuse_old_digest(self):
        binding = bind_review(self.review, **self.arguments)
        for field, value in (("operation_digest", "b" * 64), ("session_nonce", "other"),
                             ("expires_at", 100), ("binding_digest", "0" * 64),
                             ("review", prepare_review(replace(self.draft, revision=9)))):
            with self.subTest(field=field):
                # Simulate corrupted transport without relying on constructor checks.
                tampered = replace(binding)
                object.__setattr__(tampered, field, value)
                self.assertFalse(self.matches(tampered))

    def test_invalid_bind_inputs_raise_contract_error(self):
        invalids = {
            "operation_digest": (None, True, 12, "", "a" * 63, "A" * 64, "g" * 64),
            "session_nonce": (None, 3, "", " \n", "\ud800"),
            "expires_at": (None, True, -1, 1.0, "20"),
        }
        for field, values in invalids.items():
            for value in values:
                with self.subTest(field=field, value=repr(value)), self.assertRaises(ContractError):
                    bind_review(self.review, **dict(self.arguments, **{field: value}))

    def test_invalid_match_inputs_are_false_instead_of_exceptions(self):
        binding = bind_review(self.review, **self.arguments)
        for field, values in {
            "operation_digest": (None, True, "bad", "A" * 64),
            "session_nonce": (None, 5, " ", "\ud800"),
            "now": (None, True, -1, 19.0, "19"),
        }.items():
            for value in values:
                with self.subTest(field=field, value=repr(value)):
                    self.assertFalse(self.matches(binding, **{field: value}))
        for value in (None, {}, self.review, object()):
            self.assertFalse(self.matches(value))
        self.assertFalse(matches_bound_review(binding, None, operation_digest="a" * 64,
                                             session_nonce="synthetic-session", now=19))

    def test_incomplete_and_corrupt_review_cannot_be_bound_or_matched(self):
        binding = bind_review(self.review, **self.arguments)
        invalids = (None, {}, replace(self.review, content_digest="0" * 64),
                    Review(start_draft("project-one", "episode-one", "context", "claim"), "0" * 64))
        for review in invalids:
            with self.subTest(review=review):
                with self.assertRaises(ContractError):
                    bind_review(review, **self.arguments)
                self.assertFalse(matches_bound_review(binding, review, operation_digest="a" * 64,
                                                     session_nonce="synthetic-session", now=19))

    def test_corrupt_binding_shapes_fail_closed(self):
        binding = bind_review(self.review, **self.arguments)
        for field, value in (("review", None), ("expires_at", True), ("binding_digest", None),
                             ("session_nonce", []), ("operation_digest", {})):
            with self.subTest(field=field):
                corrupted = replace(binding)
                object.__setattr__(corrupted, field, value)
                self.assertFalse(self.matches(corrupted))
        missing = object.__new__(BoundReview)
        self.assertFalse(self.matches(missing))

    def test_matching_preserves_judgment_and_does_not_adopt_proposal(self):
        proposal = receive_model_proposal(self.draft, {"operation": "propose", "text": "alternative"})
        evidence = EvidenceLedger("project-one", (
            EvidenceRevision("event-one", "observation-one", "synthetic result"),))
        target = ManuscriptTarget("anchor-one", "c" * 64, 1)
        review = prepare_review(self.draft, evidence=evidence, manuscript_target=target)
        before = (asdict(review), asdict(proposal))
        binding = bind_review(review, **self.arguments)
        self.assertTrue(self.matches(binding, review))
        self.assertEqual(before, (asdict(review), asdict(proposal)))
        self.assertIs(review, binding.review)
        self.assertEqual("이유 — λ\n두 번째 줄", binding.review.draft.rationale)
        self.assertFalse(proposal.accepted)
        with self.assertRaises(FrozenInstanceError):
            binding.expires_at = 100
        with self.assertRaises(ContractError):
            receive_model_proposal(self.draft, {"operation": "accept_judgment", "text": binding.binding_digest})


if __name__ == "__main__":
    unittest.main()
