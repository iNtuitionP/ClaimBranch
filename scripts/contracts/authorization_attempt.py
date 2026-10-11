"""Serialized A2 attempt reference model, NEVER an authorization broker.

Injected readers, clocks, nonces and verifiers are synthetic dependencies, not
protected resources. A matching response issues no receipt or write authority.
No native authentication, cryptography beyond challenge hashing, I/O, entropy,
thread safety or durable replay protection is implemented. Callers can rebuild
these objects: terminal-state rejection applies only to one live instance.
"""

from dataclasses import dataclass, field
import hashlib

from scripts.contracts.first_pass import ContractError
from scripts.contracts.review_binding import BoundReview, matches_bound_review


@dataclass(frozen=True)
class AttemptRequest:
    binding: BoundReview
    challenge: bytes


@dataclass(frozen=True)
class AttemptResult:
    status: str
    authorization_verified: bool = field(default=False, init=False)


class AuthorizationAttempt:
    """One synthetic request; callbacks are fixed at construction, never input flags."""

    def __init__(self, binding, *, nonce, load_review, verify_response, clock):
        if not isinstance(binding, BoundReview):
            raise ContractError("a BoundReview is required")
        if type(nonce) is not bytes or len(nonce) != 32:
            raise ContractError("an exact 32-byte attempt nonce is required")
        if not all(callable(dependency) for dependency in (load_review, verify_response, clock)):
            raise ContractError("reader, verifier and clock must be callable")
        self._binding = binding
        self._load_review = load_review
        self._verify_response = verify_response
        self._clock = clock
        self._last_time = -1
        try:
            now = self._read_time()
            if not self._matches(binding.review, now):
                raise ContractError("invalid or expired binding")
            current = load_review()
            if not self._matches(current, self._read_time()):
                raise ContractError("a fresh matching review is required")
        except Exception as error:
            raise ContractError("attempt setup failed") from error
        challenge = hashlib.sha256(
            b"ClaimBranch/A2-attempt/v1\0" + bytes.fromhex(binding.binding_digest) + nonce
        ).digest()
        self._request = AttemptRequest(binding, challenge)
        self._result = AttemptResult("pending")

    @property
    def request(self):
        return self._request

    @property
    def result(self):
        return self._result

    def _read_time(self):
        now = self._clock()
        if type(now) is not int or now < 0 or now < self._last_time:
            raise ContractError("clock must provide nonnegative nondecreasing integers")
        self._last_time = now
        return now

    def _matches(self, review, now):
        return matches_bound_review(
            self._binding, review, operation_digest=self._binding.operation_digest,
            session_nonce=self._binding.session_nonce, now=now,
        )

    def _conclude(self, status):
        # Cancellation inside a dependency must win over its late return/error.
        if self.result.status == "verifying":
            self._result = AttemptResult(status)
        return self.result

    def _still_pending_response(self):
        now = self._read_time()
        if now >= self._binding.expires_at:
            self._conclude("expired")
        return self.result.status == "verifying"

    def finish(self, response):
        """Evaluate once, then reload current context; matched is still non-authoritative."""
        if self.result.status != "pending":
            raise ContractError("attempt is no longer pending")
        self._result = AttemptResult("verifying")
        try:
            if not self._still_pending_response():
                return self.result
            verdict = self._verify_response(self.request, response)
            if self.result.status != "verifying" or not self._still_pending_response():
                return self.result
            if verdict is not True:
                return self._conclude("rejected")
            current = self._load_review()
            if self.result.status != "verifying" or not self._still_pending_response():
                return self.result
            return self._conclude("matched" if self._matches(current, self._last_time) else "stale")
        except Exception:
            # Preserve a bounded failure; raw dependency messages may contain paths.
            return self._conclude("failed")

    def cancel(self):
        """Invalidate locally; the future native adapter must also cancel its own OS call."""
        if self.result.status in ("pending", "verifying"):
            self._result = AttemptResult("cancelled")
        return self.result
