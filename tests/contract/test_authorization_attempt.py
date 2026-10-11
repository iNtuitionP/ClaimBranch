"""A2 event-order reference tests; fake responses never prove OS authority."""

from dataclasses import asdict, FrozenInstanceError, replace
import importlib
import importlib.util
import unittest

from scripts.contracts.first_pass import (
    ContractError, EvidenceLedger, EvidenceRevision, ManuscriptTarget,
    prepare_review, record_judgment, start_draft,
)
from scripts.contracts.review_binding import bind_review


class AuthorizationAttemptTests(unittest.TestCase):
    def setUp(self):
        module = "scripts.contracts.authorization_attempt"
        self.assertIsNotNone(importlib.util.find_spec(module), "A2 attempt lifecycle is missing")
        self.Attempt = importlib.import_module(module).AuthorizationAttempt
        self.draft = record_judgment(
            start_draft("project-one", "episode-one", "synthetic context", "prior claim"),
            "  잠정 해석 🧪  ", "이유 — λ\n두 번째 줄",
        )
        self.review = prepare_review(
            self.draft,
            evidence=EvidenceLedger("project-one", (
                EvidenceRevision("event-one", "observation-one", "synthetic result"),)),
            manuscript_target=ManuscriptTarget("anchor-one", "c" * 64, 1),
        )
        self.binding = bind_review(self.review, operation_digest="a" * 64,
                                   session_nonce="session-one", expires_at=20)
        self.current = self.review
        self.now = 1
        self.events = []

    def read_review(self):
        self.events.append("read")
        return self.current

    def verify_fixture(self, request, response):
        # Only a synthetic challenge echo: deliberately NOT a signature verifier.
        self.events.append("verify")
        return type(response) is bytes and response == request.challenge

    def make_attempt(self, **overrides):
        arguments = dict(binding=self.binding, nonce=b"n" * 32,
                         load_review=self.read_review, verify_response=self.verify_fixture,
                         clock=lambda: self.now)
        arguments.update(overrides)
        return self.Attempt(**arguments)

    def assert_terminal(self, attempt, status):
        self.assertEqual(status, attempt.result.status)
        self.assertFalse(attempt.result.authorization_verified)
        before = list(self.events)
        with self.assertRaises(ContractError):
            attempt.finish(attempt.request.challenge)
        self.assertEqual(before, self.events)
        self.assertEqual(status, attempt.cancel().status)

    def test_matching_response_reloads_review_and_never_issues_authority(self):
        before = asdict(self.review)
        attempt = self.make_attempt()
        self.assertEqual("pending", attempt.result.status)
        result = attempt.finish(attempt.request.challenge)
        self.assertEqual("matched", result.status)
        self.assertEqual(["read", "verify", "read"], self.events)
        self.assertFalse(result.authorization_verified)
        self.assertEqual(before, asdict(self.review))
        self.assertEqual("이유 — λ\n두 번째 줄", attempt.request.binding.review.draft.rationale)
        with self.assertRaises(FrozenInstanceError):
            attempt.request.challenge = b"changed"
        with self.assertRaises(FrozenInstanceError):
            result.authorization_verified = True
        self.assert_terminal(attempt, "matched")

    def test_response_cannot_cross_action_session_review_expiry_or_attempt(self):
        original = self.make_attempt().request.challenge
        changed_review = prepare_review(replace(self.draft, rationale="changed", revision=2))
        changes = (
            dict(operation_digest="b" * 64), dict(session_nonce="session-two"),
            dict(expires_at=21), dict(review=changed_review),
        )
        for change in changes:
            arguments = dict(review=self.review, operation_digest="a" * 64,
                             session_nonce="session-one", expires_at=20)
            arguments.update(change)
            binding = bind_review(**arguments)
            with self.subTest(change=tuple(change)):
                attempt = self.make_attempt(binding=binding, load_review=lambda: binding.review)
                self.assertNotEqual(original, attempt.request.challenge)
                self.assertEqual("rejected", attempt.finish(original).status)
        attempt = self.make_attempt(nonce=b"x" * 32)
        self.assertNotEqual(original, attempt.request.challenge)
        self.assertEqual("rejected", attempt.finish(original).status)

    def test_invalid_setup_never_creates_an_attempt(self):
        cases = [dict(nonce=value) for value in (None, "n" * 32, b"", b"n" * 31,
                                                b"n" * 33, bytearray(b"n" * 32))]
        cases += [dict(binding=None), dict(binding=replace(self.binding, binding_digest="b" * 64)),
                  dict(load_review=None), dict(verify_response=True), dict(clock=1),
                  dict(load_review=lambda: None)]
        cases += [dict(clock=lambda value=value: value) for value in (True, -1, 1.5, 20, 21)]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ContractError):
                self.make_attempt(**case)

    def test_setup_rechecks_time_after_reader_and_wraps_reader_failure(self):
        for after_read in (0, 20):
            self.now = 1
            def reader():
                self.now = after_read
                return self.review
            with self.subTest(time=after_read), self.assertRaises(ContractError):
                self.make_attempt(load_review=reader)

        def broken_reader():
            raise OSError("synthetic read failure")
        with self.assertRaises(ContractError):
            self.make_attempt(load_review=broken_reader)

    def test_changed_or_missing_review_after_prompt_is_stale(self):
        changed = (
            None,
            prepare_review(replace(self.draft, revision=2)),
            prepare_review(self.draft, evidence=self.review.evidence,
                           manuscript_target=replace(self.review.manuscript_target, revision=2)),
            prepare_review(self.draft, evidence=EvidenceLedger("project-one"),
                           manuscript_target=self.review.manuscript_target),
        )
        for current in changed:
            self.current = self.review
            attempt = self.make_attempt()
            self.current = current
            with self.subTest(current=current):
                self.assertEqual("stale", attempt.finish(attempt.request.challenge).status)
                self.assert_terminal(attempt, "stale")

    def test_review_change_during_verification_is_seen_by_final_reader(self):
        def verifier(request, response):
            self.current = prepare_review(replace(self.draft, revision=2))
            return True
        attempt = self.make_attempt(verify_response=verifier)
        self.assertEqual("stale", attempt.finish(b"fixture").status)

    def test_cancellation_before_response_is_terminal_without_verification(self):
        attempt = self.make_attempt()
        self.assertEqual("cancelled", attempt.cancel().status)
        self.assert_terminal(attempt, "cancelled")
        self.assertEqual(["read"], self.events)

    def test_cancellation_during_verifier_wins_over_late_success_or_failure(self):
        for raises in (False, True):
            def verifier(request, response):
                attempt.cancel()
                if raises:
                    raise OSError("late failure")
                return True
            attempt = self.make_attempt(verify_response=verifier)
            with self.subTest(raises=raises):
                self.assertEqual("cancelled", attempt.finish(b"fixture").status)
                self.assert_terminal(attempt, "cancelled")

    def test_cancellation_during_final_review_read_cannot_be_overwritten(self):
        calls = 0
        def reader():
            nonlocal calls
            calls += 1
            if calls == 2:
                attempt.cancel()
            return self.review
        attempt = self.make_attempt(load_review=reader)
        self.assertEqual("cancelled", attempt.finish(attempt.request.challenge).status)
        self.assert_terminal(attempt, "cancelled")

    def test_expiry_before_response_skips_verification(self):
        attempt = self.make_attempt()
        self.now = 20
        self.assertEqual("expired", attempt.finish(attempt.request.challenge).status)
        self.assertEqual(["read"], self.events)
        self.assert_terminal(attempt, "expired")

    def test_expiry_during_verifier_or_reader_is_not_extended(self):
        for boundary in ("verify", "read"):
            self.now = 1
            reads = 0
            def verifier(request, response):
                if boundary == "verify":
                    self.now = 20
                return True
            def reader():
                nonlocal reads
                reads += 1
                if boundary == "read" and reads == 2:
                    self.now = 20
                return self.review
            attempt = self.make_attempt(load_review=reader, verify_response=verifier)
            with self.subTest(boundary=boundary):
                self.assertEqual("expired", attempt.finish(b"fixture").status)
                self.assert_terminal(attempt, "expired")

    def test_only_exact_verifier_success_can_reach_final_review(self):
        for verdict in (False, None, 1, "verified", {"actor_class": "human"}):
            self.events = []
            attempt = self.make_attempt(verify_response=lambda request, response: verdict)
            with self.subTest(verdict=verdict):
                self.assertEqual("rejected", attempt.finish(b"fixture").status)
                self.assertEqual(["read"], self.events)
                self.assert_terminal(attempt, "rejected")

    def test_dependency_failure_is_terminal_and_not_a_verified_denial(self):
        for boundary in ("verify", "read", "clock"):
            reads = 0
            def reader():
                nonlocal reads
                reads += 1
                if boundary == "read" and reads == 2:
                    raise OSError("private source path must not become output")
                return self.review
            def verifier(request, response):
                if boundary == "verify":
                    raise ValueError("bad response")
                return True
            def clock():
                if boundary == "clock" and self.now == 2:
                    raise RuntimeError("clock unavailable")
                return self.now
            self.now = 1
            attempt = self.make_attempt(load_review=reader, verify_response=verifier, clock=clock)
            self.now = 2
            with self.subTest(boundary=boundary):
                self.assertEqual("failed", attempt.finish(b"fixture").status)
                self.assert_terminal(attempt, "failed")

    def test_invalid_or_backwards_clock_cannot_extend_attempt(self):
        for value in (0, True, -1, 1.5, None):
            self.now = 1
            attempt = self.make_attempt()
            self.now = value
            with self.subTest(value=value):
                self.assertEqual("failed", attempt.finish(attempt.request.challenge).status)
                self.assert_terminal(attempt, "failed")

    def test_reentrant_response_cannot_start_a_second_verification(self):
        calls = 0
        def verifier(request, response):
            nonlocal calls
            calls += 1
            with self.assertRaises(ContractError):
                attempt.finish(response)
            return True
        attempt = self.make_attempt(verify_response=verifier)
        self.assertEqual("matched", attempt.finish(b"fixture").status)
        self.assertEqual(1, calls)


if __name__ == "__main__":
    unittest.main()
