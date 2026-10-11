from dataclasses import replace
import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.core.lifecycle import EpisodeEntry, EpisodeLedger, ProposalAttempt, ManuscriptSaga
from claimbranch.core.debt import CompileResult


class LifecycleTests(unittest.TestCase):
    def test_only_one_episode_can_be_active_and_product_failure_cannot_invalidate(self):
        ledger = EpisodeLedger("project", "protocol-v1").start("episode", "head", 3)
        with self.assertRaises(ContractError):
            ledger.start("second", "head", 3)
        for reason in ("provider-failed", "out-of-f0", "abandoned", "authorization-failed"):
            with self.subTest(reason=reason), self.assertRaises(ContractError):
                ledger.invalidate("episode", reason)
        closed = ledger.close("episode", completed=False)
        self.assertEqual("incomplete", closed.entries[0].outcome)
        self.assertEqual("active", ledger.entries[0].state)

    def test_protocol_replacements_and_valid_starts_are_finite(self):
        ledger = EpisodeLedger("project", "protocol-v1")
        for i in range(3):
            ledger = ledger.start(f"invalid-{i}", "head", 0).invalidate(f"invalid-{i}", "eligibility-error")
        ledger = ledger.start("fourth", "head", 0)
        exhausted = ledger.invalidate("fourth", "corrupted-timing")
        self.assertEqual("inconclusive", exhausted.status)
        self.assertEqual(3, sum(item.state == "invalidated" for item in exhausted.entries))
        with self.assertRaises(ContractError):
            exhausted.start("extra", "head", 0)
        valid = EpisodeLedger("project", "protocol-v1")
        for i in range(3):
            valid = valid.start(f"valid-{i}", "head", 0).close(f"valid-{i}", completed=True)
        with self.assertRaises(ContractError):
            valid.start("fourth", "head", 0)

    def test_cancelled_expired_and_changed_context_cannot_adopt_a_proposal(self):
        attempt = ProposalAttempt("request", "a" * 64, 100, 130)
        for pending, digest, now, status in ((attempt.cancel(), "a" * 64, 101, "cancelled"),
                                           (attempt, "a" * 64, 130, "expired"),
                                           (attempt, "b" * 64, 101, "stale")):
            result = pending.complete("suggestion", current_digest=digest, now=now)
            self.assertEqual(status, result.state)
            self.assertIsNone(result.text)
        self.assertEqual("proposed", attempt.complete("suggestion", current_digest="a" * 64, now=101).state)

    def test_ready_response_is_rechecked_for_expiry_and_changed_context_before_adoption(self):
        ready = ProposalAttempt("request", "a" * 64, 100, 130).complete("suggestion", current_digest="a" * 64, now=101)
        for digest, now, expected in (("a" * 64, 130, "expired"), ("b" * 64, 102, "stale")):
            result = ready.complete("suggestion", current_digest=digest, now=now)
            self.assertEqual(expected, result.state)
            self.assertIsNone(result.text)

    def test_rehydrated_ledger_cannot_exceed_the_valid_start_budget(self):
        entries = tuple(EpisodeEntry(f"episode-{i}", "head", 0, "closed", "complete") for i in range(4))
        with self.assertRaises(ContractError):
            EpisodeLedger("project", "protocol-v1", entries)
        with self.assertRaises(ContractError):
            EpisodeLedger("project", "protocol-v1", status="inconclusive")
        with self.assertRaises(ContractError):
            EpisodeLedger("project", "protocol-v1", (EpisodeEntry("active", "head", 0), entries[0]))

    def saga(self):
        return ManuscriptSaga("project", "debt", "anchor", "head", "patch", "attempt", 1,
                              "a" * 64, "b" * 64, "c" * 64, "d" * 64)

    def test_manuscript_requires_each_phase_and_exact_fence_and_hashes(self):
        saga = self.saga()
        with self.assertRaises(ContractError):
            saga.advance("applied", observed_hash="b" * 64, head="head", fence=1)
        for head, fence in (("stale", 1), ("head", 2)):
            with self.assertRaises(ContractError):
                saga.advance("prepare", observed_hash="a" * 64, head=head, fence=fence)
        for event, observed in (("prepare", "a" * 64), ("begin-apply", "a" * 64), ("applied", "b" * 64), ("begin-compile", "b" * 64)):
            saga = saga.advance(event, observed_hash=observed, head="head", fence=1)
        proof = CompileResult("debt", "anchor", "patch", "attempt", "a" * 64, "b" * 64,
                              "e" * 64, "c" * 64, "d" * 64, "head", 1, "verified")
        with self.assertRaises(ContractError):
            saga.verify(replace(proof, attempt_id="other"))
        verified = saga.verify(proof)
        self.assertEqual("verified", verified.phase)
        self.assertFalse(verified.debt_closed)

    def test_rehydrated_verified_saga_requires_an_exact_typed_observation(self):
        saga = self.saga()
        with self.assertRaises(ContractError):
            replace(saga, phase="verified", compile_result={"status": "verified"})
        foreign = CompileResult("other-debt", "anchor", "patch", "attempt", "a" * 64, "b" * 64,
                                "e" * 64, "c" * 64, "d" * 64, "head", 1, "verified")
        with self.assertRaises(ContractError):
            replace(saga, phase="verified", compile_result=foreign)

    def test_restore_proves_original_bytes_and_unknown_bytes_enter_recovery(self):
        saga = self.saga().advance("prepare", observed_hash="a" * 64, head="head", fence=1)
        saga = saga.advance("begin-apply", observed_hash="a" * 64, head="head", fence=1)
        failed = saga.advance("applied", observed_hash="f" * 64, head="head", fence=1)
        self.assertEqual("recovery-required", failed.phase)
        with self.assertRaises(ContractError):
            failed.advance("begin-compile", observed_hash="b" * 64, head="head", fence=1)
        restored = failed.restore(observed_hash="a" * 64, head="head", fence=1)
        self.assertEqual("restored", restored.phase)
        self.assertFalse(restored.debt_closed)
        self.assertEqual("recovery-required", failed.restore(observed_hash="b" * 64, head="head", fence=1).phase)


if __name__ == "__main__":
    unittest.main()
