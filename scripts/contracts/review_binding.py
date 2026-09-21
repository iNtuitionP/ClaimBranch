"""Pure synthetic review/action binding, NEVER an authorization receipt.

All values and digests can be recreated by any caller. Matching checks content
and expiry only: no human presence, signature, single-use consumption, clock,
filesystem, persistence, or accepted-state write is provided. The caller must
supply a freshly prepared current Review; this cannot detect external edits.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

from scripts.contracts.first_pass import (
    ContractError, Review, prepare_review, review_is_current,
)


@dataclass(frozen=True)
class BoundReview:
    """Non-authoritative test value; construct through bind_review for validation."""

    review: Review
    operation_digest: str
    session_nonce: str
    expires_at: int
    binding_digest: str


def _require_time(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractError("time must be a nonnegative integer")


def _binding_digest(review, operation_digest, session_nonce, expires_at):
    if not isinstance(review, Review):
        raise ContractError("a complete Review is required")
    # A Review can be constructed directly. Recheck completeness and freshness,
    # not merely its type or the caller's supplied content_digest.
    prepare_review(review.draft, evidence=review.evidence,
                   manuscript_target=review.manuscript_target)
    if not review_is_current(review, review.draft, evidence=review.evidence,
                             manuscript_target=review.manuscript_target):
        raise ContractError("review content does not match its digest")
    if (not isinstance(operation_digest, str) or len(operation_digest) != 64
            or any(character not in "0123456789abcdef" for character in operation_digest)):
        raise ContractError("operation_digest must be a lowercase SHA-256 digest")
    if not isinstance(session_nonce, str) or not session_nonce.strip():
        raise ContractError("session_nonce must be nonblank text")
    _require_time(expires_at)
    payload = {"schema_version": 1, "review": asdict(review),
               "operation_digest": operation_digest, "session_nonce": session_nonce,
               "expires_at": expires_at}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def bind_review(review: Review, *, operation_digest: str,
                session_nonce: str, expires_at: int) -> BoundReview:
    """Preserve exact entered meaning while binding the synthetic action scope."""
    try:
        digest = _binding_digest(review, operation_digest, session_nonce, expires_at)
    except (AttributeError, TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("invalid review binding input") from exc
    return BoundReview(review, operation_digest, session_nonce, expires_at, digest)


def matches_bound_review(binding: BoundReview, current_review: Review, *,
                         operation_digest: str, session_nonce: str, now: int) -> bool:
    """Match a fresh current snapshot without granting or consuming authority."""
    if not isinstance(binding, BoundReview):
        return False
    try:
        _require_time(now)
        expected = _binding_digest(binding.review, binding.operation_digest,
                                   binding.session_nonce, binding.expires_at)
        current = _binding_digest(current_review, operation_digest,
                                  session_nonce, binding.expires_at)
        return (binding.binding_digest == expected == current
                and now < binding.expires_at)
    except (AttributeError, TypeError, ValueError, UnicodeError):
        return False
