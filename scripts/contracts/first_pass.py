"""Synthetic, non-authoritative first-pass contract reference model.

The immutable values in this module are disposable validation artifacts. They
are not canonical ResearchEpisode state, authorization receipts, accepted
evidence, or a persistence API.
"""

from dataclasses import asdict, dataclass, field, replace
import hashlib
import json


class ContractError(ValueError):
    """An input does not satisfy the bounded first-pass contract."""


def _require_nonblank(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be nonblank text")


def _require_digest(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ContractError("content_digest must be a lowercase SHA-256 digest")


@dataclass(frozen=True)
class EvidenceRevision:
    """One hypothetical observation revision, not evidence acceptance."""

    event_id: str
    observation_id: str
    statement: str
    supersedes: str | None = None

    def __post_init__(self):
        for name in ("event_id", "observation_id", "statement"):
            _require_nonblank(name, getattr(self, name))
        if self.supersedes is not None:
            _require_nonblank("supersedes", self.supersedes)


@dataclass(frozen=True)
class EvidenceLedger:
    """Project-wide synthetic history, independent of reasoning drafts.

    This immutable value models append-only transitions; it is not a durable
    store or an enforcement boundary against arbitrary Python callers.
    """

    project_id: str
    entries: tuple[EvidenceRevision, ...] = ()

    def __post_init__(self):
        _require_nonblank("project_id", self.project_id)
        if not isinstance(self.entries, tuple):
            raise ContractError("evidence history must be an immutable tuple")
        seen = set()
        latest = {}
        for event in self.entries:
            if not isinstance(event, EvidenceRevision):
                raise ContractError("history must contain EvidenceRevision values")
            if event.event_id in seen:
                raise ContractError("evidence event identity must be unique")
            if event.supersedes != latest.get(event.observation_id):
                raise ContractError("correction must name the current revision of its observation")
            seen.add(event.event_id)
            latest[event.observation_id] = event.event_id


def append_evidence(ledger, event):
    """Append a synthetic revision; exact event retries leave history intact."""

    if not isinstance(ledger, EvidenceLedger) or not isinstance(event, EvidenceRevision):
        raise ContractError("an EvidenceLedger and EvidenceRevision are required")
    for previous in ledger.entries:
        if previous.event_id == event.event_id:
            if previous != event:
                raise ContractError("a changed retry cannot overwrite evidence")
            return ledger
    return replace(ledger, entries=(*ledger.entries, event))


@dataclass(frozen=True)
class ManuscriptTarget:
    """Caller-supplied synthetic target version; never a verified file read.

    A future trusted reader must supply the anchor, digest and monotonic
    revision. No external edit detection or manuscript write occurs here.
    """

    anchor_id: str
    content_digest: str
    revision: int = 0

    def __post_init__(self):
        _require_nonblank("anchor_id", self.anchor_id)
        _require_digest(self.content_digest)
        if (isinstance(self.revision, bool) or not isinstance(self.revision, int)
                or self.revision < 0):
            raise ContractError("revision must be a nonnegative integer")


@dataclass(frozen=True)
class Draft:
    """A non-authoritative snapshot of one synthetic first-pass draft."""

    project_id: str
    episode_id: str
    source_context: str
    existing_claim: str
    interpretation: str | None = None
    rationale: str | None = None
    revision: int = 0

    def __post_init__(self):
        _require_nonblank("project_id", self.project_id)
        _require_nonblank("episode_id", self.episode_id)
        _require_nonblank("source_context", self.source_context)
        _require_nonblank("existing_claim", self.existing_claim)
        if (self.interpretation is None) != (self.rationale is None):
            raise ContractError("interpretation and rationale must be recorded together")
        if self.interpretation is not None:
            _require_nonblank("interpretation", self.interpretation)
            _require_nonblank("rationale", self.rationale)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise ContractError("revision must be a nonnegative integer")
        if self.revision < 0:
            raise ContractError("revision must be a nonnegative integer")


@dataclass(frozen=True)
class Review:
    """A freshness snapshot, never an authorization or acceptance record."""

    draft: Draft
    content_digest: str
    evidence: EvidenceLedger | None = None
    manuscript_target: ManuscriptTarget | None = None

    def __post_init__(self):
        if not isinstance(self.draft, Draft):
            raise ContractError("review must contain a Draft")
        _require_digest(self.content_digest)
        _require_review_context(self.draft, self.evidence, self.manuscript_target)


@dataclass(frozen=True)
class Proposal:
    """Model-originated text with no accepted-state authority."""

    project_id: str
    episode_id: str
    text: str
    accepted: bool = field(default=False, init=False)

    def __post_init__(self):
        _require_nonblank("project_id", self.project_id)
        _require_nonblank("episode_id", self.episode_id)
        _require_nonblank("text", self.text)


def _require_draft(draft):
    if not isinstance(draft, Draft):
        raise ContractError("a Draft value is required")


def _draft_payload(draft):
    return {
        "project_id": draft.project_id,
        "episode_id": draft.episode_id,
        "source_context": draft.source_context,
        "existing_claim": draft.existing_claim,
        "interpretation": draft.interpretation,
        "rationale": draft.rationale,
        "revision": draft.revision,
    }


def _require_review_context(draft, evidence, manuscript_target):
    if evidence is not None:
        if not isinstance(evidence, EvidenceLedger) or evidence.project_id != draft.project_id:
            raise ContractError("review evidence must belong to the draft project")
    if manuscript_target is not None and not isinstance(manuscript_target, ManuscriptTarget):
        raise ContractError("review target must be a ManuscriptTarget")


def _content_digest(draft, evidence=None, manuscript_target=None):
    payload = _draft_payload(draft)
    if evidence is not None:
        payload["evidence"] = asdict(evidence)
    if manuscript_target is not None:
        payload["manuscript_target"] = asdict(manuscript_target)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def start_draft(project_id, episode_id, source_context, existing_claim):
    """Start an undecided synthetic draft without creating accepted state."""

    return Draft(project_id, episode_id, source_context, existing_claim)


def record_judgment(draft, interpretation, rationale):
    """Return a new draft containing exact judgment text, or the same retry."""

    _require_draft(draft)
    _require_nonblank("interpretation", interpretation)
    _require_nonblank("rationale", rationale)
    if (draft.interpretation, draft.rationale) == (interpretation, rationale):
        return draft
    return replace(
        draft,
        interpretation=interpretation,
        rationale=rationale,
        revision=draft.revision + 1,
    )


def revise_context(draft, source_context, existing_claim):
    """Return a new draft when source context or the existing claim changes."""

    _require_draft(draft)
    _require_nonblank("source_context", source_context)
    _require_nonblank("existing_claim", existing_claim)
    if (draft.source_context, draft.existing_claim) == (
        source_context,
        existing_claim,
    ):
        return draft
    return replace(
        draft,
        source_context=source_context,
        existing_claim=existing_claim,
        revision=draft.revision + 1,
    )


def prepare_review(draft, *, evidence=None, manuscript_target=None):
    """Freeze exact entered judgment text into a freshness-only review."""

    _require_draft(draft)
    if draft.interpretation is None or draft.rationale is None:
        raise ContractError("a complete judgment is required for review")
    _require_review_context(draft, evidence, manuscript_target)
    return Review(draft, _content_digest(draft, evidence, manuscript_target),
                  evidence, manuscript_target)


def review_is_current(review, draft, *, evidence=None, manuscript_target=None):
    """Check content freshness without granting permission or authority."""

    if not isinstance(review, Review) or not isinstance(draft, Draft):
        return False
    try:
        _require_review_context(draft, evidence, manuscript_target)
    except ContractError:
        return False
    return (
        review.draft.project_id == draft.project_id
        and review.draft.episode_id == draft.episode_id
        and review.draft.revision == draft.revision
        and review.draft == draft
        and review.evidence == evidence
        and review.manuscript_target == manuscript_target
        and review.content_digest == _content_digest(
            review.draft, review.evidence, review.manuscript_target)
        and review.content_digest == _content_digest(draft, evidence, manuscript_target)
    )


def receive_model_proposal(draft, request):
    """Accept only model proposal text; expose no accepted operation."""

    _require_draft(draft)
    if not isinstance(request, dict) or set(request) != {"operation", "text"}:
        raise ContractError("model request must contain exactly operation and text")
    if request["operation"] != "propose":
        raise ContractError("models may only propose text")
    _require_nonblank("text", request["text"])
    return Proposal(draft.project_id, draft.episode_id, request["text"])
