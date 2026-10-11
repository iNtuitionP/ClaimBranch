"""Propose exact debt closure; no receipt issuance or automatic debt resolution.

The versioned understanding path compares independently supplied cause/current
values. A trusted caller still has to load accepted sources and verify/consume
foreground authority. Matching Python objects or hashes cannot establish that.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace

from .canonical import ContractError, bounded_text, canonical_bytes, decode, digest, digest_text, identifier, integer
from .research_schema import HASH, ID, TEXT, normalize, obj
from .review import Debt, acceptance_candidate


@dataclass(frozen=True)
class CompileResult:
    debt_id: str
    anchor_id: str
    patch_id: str
    attempt_id: str
    source_digest: str
    postimage_digest: str
    output_digest: str
    compiler_digest: str
    configuration_digest: str
    graph_head: str
    fencing_token: int
    status: str

    def __post_init__(self):
        for value in (self.debt_id, self.anchor_id, self.patch_id, self.attempt_id, self.graph_head):
            identifier(value)
        for value in (self.source_digest, self.postimage_digest, self.output_digest,
                      self.compiler_digest, self.configuration_digest):
            digest_text(value)
        integer(self.fencing_token, 1)
        if self.status not in ("applied-unverified", "verified", "restored", "recovery-required"):
            raise ContractError("unknown observed manuscript state")


@dataclass(frozen=True)
class ClosureReview:
    operation_id: str
    debt_id: str
    project_id: str
    episode_id: str
    expected_head: str
    rationale: str
    session_nonce: str
    sealed_at: int
    expires_at: int
    compile_result: CompileResult | None = None

    def __post_init__(self):
        for value in (self.operation_id, self.debt_id, self.project_id, self.episode_id,
                      self.expected_head, self.session_nonce):
            identifier(value)
        bounded_text(self.rationale)
        integer(self.sealed_at)
        integer(self.expires_at)
        if not self.sealed_at < self.expires_at <= self.sealed_at + 300:
            raise ContractError("invalid closure-review lifetime")
        if self.compile_result is not None and not isinstance(self.compile_result, CompileResult):
            raise ContractError("typed compile observation required")
        canonical_bytes(asdict(self))

    @property
    def digest(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class ClosureCandidate:
    review_digest: str
    operation_id: str
    resulting_debt: Debt
    requires_authorization: bool = True
    authorization_verified: bool = False


def closure_candidate(debt, review, *, current_head, now, current_compile=None):
    """Legacy head/time-only candidate helper; not the versioned understanding route."""
    if not isinstance(debt, Debt) or not isinstance(review, ClosureReview):
        raise ContractError("a proposal or actor flag cannot replace closure review")
    integer(now)
    if debt.status != "open":
        raise ContractError("only an open debt can be closed")
    if (review.debt_id, review.project_id, review.episode_id) != (debt.id, debt.project_id, debt.episode_id):
        raise ContractError("closure targets another debt or research context")
    if review.operation_id == debt.cause_operation_id:
        raise ContractError("debt closure needs a separate operation")
    if review.expected_head != current_head or not review.sealed_at <= now < review.expires_at:
        raise ContractError("stale or expired closure review")
    if debt.kind == "understanding":
        if review.compile_result is not None or current_compile is not None:
            raise ContractError("explanation closure cannot substitute manuscript verification")
    else:
        result = review.compile_result
        if not isinstance(result, CompileResult) or result != current_compile:
            raise ContractError("compile result changed or is unavailable")
        if (result.debt_id, result.anchor_id, result.graph_head, result.status) != (
                debt.id, debt.anchor_id, current_head, "verified"):
            raise ContractError("exact non-restored verified manuscript result required")
    return ClosureCandidate(review.digest, review.operation_id, replace(debt, status="closed-by-human"))


_CLOSURE_CONTEXT = obj(project_id=ID, episode_id=ID, debt_id=ID, cause_operation_id=ID,
    cause_review_digest=HASH, expected_head=ID,
    evidence_watermark={"type": "integer", "minimum": 0, "maximum": 32},
    topics_rule_version={"const": "claimbranch.understanding-topics/v1"},
    topics_digest=HASH, displayed_context_digest=HASH)
_CLOCK = {"type": "integer", "minimum": 0, "maximum": 2**53 - 1}
_UNDERSTANDING_REVIEW = obj(schema={"const": "claimbranch.understanding-closure-review/v1"},
    rule_version={"const": "understanding-closure-v1"}, context=_CLOSURE_CONTEXT,
    operation_id=ID, rationale=TEXT, session_nonce=ID, sealed_at=_CLOCK, expires_at=_CLOCK,
    authorization_verified={"const": False})


def understanding_closure_schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:claimbranch:understanding-closure-review:v1",
            "$comment": ("Generated by python -m scripts.export_research_schema. Unverified candidate only. "
                         "Runtime requires canonical NFC UTF-8 bytes, intact sealed cause/debt identity, "
                         "current displayed context and live review timing. Schema validation does not "
                         "verify source authority, topic derivation, human presence or receipt consumption."),
            **deepcopy(_UNDERSTANDING_REVIEW)}


@dataclass(frozen=True)
class UnderstandingClosureContext:
    project_id: str
    episode_id: str
    debt_id: str
    cause_operation_id: str
    cause_review_digest: str
    expected_head: str
    evidence_watermark: int
    topics_rule_version: str
    topics_digest: str
    displayed_context_digest: str

    def __post_init__(self):
        normalize(asdict(self), _CLOSURE_CONTEXT)


@dataclass(frozen=True)
class UnderstandingClosureReview:
    operation_id: str
    context: UnderstandingClosureContext
    rationale: str
    session_nonce: str
    sealed_at: int
    expires_at: int
    payload: bytes
    digest: str


def _understanding_context(debt, cause_review, context):
    if not isinstance(debt, Debt) or debt.kind != "understanding" or debt.status != "open":
        raise ContractError("exact open understanding debt required")
    if not isinstance(context, UnderstandingClosureContext):
        raise ContractError("typed understanding closure context required")
    normalize(asdict(context), _CLOSURE_CONTEXT)
    # Rebuild the sealed cause, including its contribution chain and deferral.
    # An expired historical review remains inspectable; this does not authorize it.
    cause = acceptance_candidate(cause_review, decision="accept")
    if debt not in cause.debts:
        raise ContractError("debt does not match the intact deferred cause review")
    if (context.project_id, context.episode_id, context.debt_id,
            context.cause_operation_id, context.cause_review_digest) != (
            debt.project_id, debt.episode_id, debt.id, debt.cause_operation_id, debt.review_digest):
        raise ContractError("closure context belongs to another debt or cause review")
    if context.evidence_watermark < cause_review.context.evidence_watermark:
        raise ContractError("closure context predates its causal evidence")


def prepare_understanding_closure(debt, cause_review, displayed_context, *, current_context,
                                  operation_id, rationale, session_nonce, sealed_at, expires_at, now):
    """Seal a candidate against displayed/current values; never verify authority."""
    _understanding_context(debt, cause_review, current_context)
    if not isinstance(displayed_context, UnderstandingClosureContext) or displayed_context != current_context:
        raise ContractError("displayed understanding context is stale or belongs elsewhere")
    value = normalize({"schema": "claimbranch.understanding-closure-review/v1",
        "rule_version": "understanding-closure-v1", "context": asdict(current_context),
        "operation_id": operation_id, "rationale": rationale, "session_nonce": session_nonce,
        "sealed_at": sealed_at, "expires_at": expires_at, "authorization_verified": False},
        _UNDERSTANDING_REVIEW)
    integer(now)
    if (not sealed_at <= now < expires_at or expires_at > sealed_at + 300
            or sealed_at < cause_review.context.sealed_at):
        raise ContractError("stale or invalid understanding closure-review lifetime")
    if operation_id == debt.cause_operation_id:
        raise ContractError("understanding closure requires a separate operation")
    return UnderstandingClosureReview(operation_id, current_context, value["rationale"], session_nonce,
                                      sealed_at, expires_at, canonical_bytes(value), digest(value))


def restore_understanding_closure(raw, debt, cause_review, *, current_context, now):
    """Read only this version, rechecking supplied sources; restore no consent."""
    value = normalize(decode(raw), _UNDERSTANDING_REVIEW)
    if canonical_bytes(value) != raw:
        raise ContractError("closure review must use canonical bytes")
    return prepare_understanding_closure(debt, cause_review, UnderstandingClosureContext(**value["context"]),
        current_context=current_context, operation_id=value["operation_id"], rationale=value["rationale"],
        session_nonce=value["session_nonce"], sealed_at=value["sealed_at"], expires_at=value["expires_at"], now=now)


def understanding_closure_candidate(debt, cause_review, review, *, current_context, now):
    """Recheck the sealed review against fresh supplied inputs; no writes/receipts."""
    if not isinstance(review, UnderstandingClosureReview):
        raise ContractError("versioned understanding closure review required")
    checked = prepare_understanding_closure(debt, cause_review, review.context,
        current_context=current_context, operation_id=review.operation_id, rationale=review.rationale,
        session_nonce=review.session_nonce, sealed_at=review.sealed_at, expires_at=review.expires_at, now=now)
    if checked != review:
        raise ContractError("sealed understanding closure review was modified")
    return ClosureCandidate(review.digest, review.operation_id, replace(debt, status="closed-by-human"))
