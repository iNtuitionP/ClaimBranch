"""R3 portable judgment, provenance, selected closure and exact review contracts.

All results are immutable candidate values. This module neither issues nor
verifies human authority, writes accepted history, reads manuscripts, nor calls
a provider. A future trusted gateway must independently reload context and
atomically consume real authorization before committing any candidate.
"""
from dataclasses import asdict, dataclass, replace

from .canonical import (ContractError, bounded_text, canonical_bytes,
                        digest, digest_text, identifier, integer)


def _tuple(value, limit=128):
    if type(value) is not tuple or len(value) > limit:
        raise ContractError("bounded immutable tuple required")


@dataclass(frozen=True)
class Proposal:
    id: str
    project_id: str
    episode_id: str
    text: str
    trace_digest: str

    def __post_init__(self):
        for value in (self.id, self.project_id, self.episode_id):
            identifier(value)
        bounded_text(self.text)
        digest_text(self.trace_digest)

    @classmethod
    def from_payload(cls, payload):
        fields = {"schema_version", "id", "project_id", "episode_id", "text", "trace_digest", "intended_operation"}
        if type(payload) is not dict or set(payload) != fields:
            raise ContractError("unknown or missing proposal field")
        if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
            raise ContractError("unknown proposal version")
        if payload["intended_operation"] != "record-interpretation":
            raise ContractError("proposal cannot request authoritative operations")
        canonical_bytes(payload)
        return cls(*(payload[key] for key in ("id", "project_id", "episode_id", "text", "trace_digest")))


@dataclass(frozen=True)
class Contribution:
    contributor: str
    text: str
    rationale: str | None
    proposal_id: str | None
    trace_digest: str | None
    parent_digest: str | None

    def __post_init__(self):
        if self.contributor not in ("human", "ai"):
            raise ContractError("unknown contributor")
        bounded_text(self.text)
        if self.rationale is not None:
            bounded_text(self.rationale)
        if self.parent_digest is not None:
            digest_text(self.parent_digest)
        if self.contributor == "ai":
            identifier(self.proposal_id)
            digest_text(self.trace_digest)
            if self.rationale is not None:
                raise ContractError("AI cannot supply the human rationale")
        elif self.proposal_id is not None or self.trace_digest is not None:
            raise ContractError("human edit retains AI through its parent, not relabeling")

    @property
    def digest(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class Judgment:
    project_id: str
    episode_id: str
    text: str | None = None
    rationale: str | None = None
    history: tuple[Contribution, ...] = ()

    def __post_init__(self):
        identifier(self.project_id)
        identifier(self.episode_id)
        _tuple(self.history, 8)
        previous = None
        latest_reason = None
        for contribution in self.history:
            if not isinstance(contribution, Contribution) or contribution.parent_digest != previous:
                raise ContractError("broken contribution chain")
            previous = contribution.digest
            if contribution.contributor == "human":
                latest_reason = contribution.rationale
        if self.history:
            if self.text != self.history[-1].text or self.rationale != latest_reason:
                raise ContractError("judgment differs from its contribution history")
        elif self.text is not None or self.rationale is not None:
            raise ContractError("unrecorded judgment")
        canonical_bytes(asdict(self))

    @classmethod
    def start(cls, project_id, episode_id):
        return cls(project_id, episode_id)

    def edit(self, text, rationale):
        bounded_text(text)
        bounded_text(rationale)
        item = Contribution("human", text, rationale, None, None,
                            self.history[-1].digest if self.history else None)
        return replace(self, text=text, rationale=rationale, history=(*self.history, item))

    def use_proposal(self, proposal):
        if not isinstance(proposal, Proposal) or (proposal.project_id, proposal.episode_id) != (self.project_id, self.episode_id):
            raise ContractError("proposal belongs to another research context")
        item = Contribution("ai", proposal.text, None, proposal.id, proposal.trace_digest,
                            self.history[-1].digest if self.history else None)
        return replace(self, text=proposal.text, history=(*self.history, item))

    @property
    def ai_influenced(self):
        return any(item.contributor == "ai" for item in self.history)


@dataclass(frozen=True)
class Change:
    id: str
    kind: str
    dependencies: tuple[str, ...]

    def __post_init__(self):
        identifier(self.id)
        if self.kind not in ("claim", "claim-status", "interpretation", "scientific-edge", "experiment-plan"):
            raise ContractError("only reasoning may be selected; evidence is global")
        _tuple(self.dependencies)
        for value in self.dependencies:
            identifier(value)
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ContractError("duplicate dependency")


@dataclass(frozen=True)
class Selection:
    selected: tuple[str, ...]
    required: tuple[str, ...]
    omitted: tuple[str, ...]
    evidence_references: tuple[str, ...]
    changes: tuple[Change, ...]

    @property
    def closure(self):
        return tuple(sorted((*self.selected, *self.required)))


def select_changes(changes, selected, evidence_ids):
    for value in (changes, selected, evidence_ids):
        _tuple(value)
    if not all(isinstance(change, Change) for change in changes):
        raise ContractError("typed reasoning changes required")
    for value in (*selected, *evidence_ids):
        identifier(value)
    by_id = {change.id: change for change in changes}
    if len(by_id) != len(changes) or len(set(selected)) != len(selected) or len(set(evidence_ids)) != len(evidence_ids):
        raise ContractError("duplicate change or selection")
    if set(by_id).intersection(evidence_ids) or not set(selected).issubset(by_id):
        raise ContractError("invalid reasoning selection")
    closure, evidence = set(), set()
    pending = list(selected)
    while pending:
        current = pending.pop()
        if current in evidence_ids:
            evidence.add(current)
        elif current not in by_id:
            raise ContractError("selected change has a missing dependency")
        elif current not in closure:
            closure.add(current)
            pending.extend(by_id[current].dependencies)
    return Selection(tuple(sorted(selected)), tuple(sorted(closure - set(selected))),
                     tuple(sorted(set(by_id) - closure)), tuple(sorted(evidence)),
                     tuple(sorted(changes, key=lambda item: item.id)))


@dataclass(frozen=True)
class ReviewContext:
    project_id: str
    episode_id: str
    operation_id: str
    operation_type: str
    operation_digest: str
    heads: tuple[tuple[str, str], ...]
    evidence_watermark: int
    anchor_id: str
    manuscript_digest: str
    session_nonce: str
    sealed_at: int
    expires_at: int
    schema_version: int = 1
    rule_version: str = "f0-review-v1"

    def __post_init__(self):
        for value in (self.project_id, self.episode_id, self.operation_id, self.anchor_id, self.session_nonce):
            identifier(value)
        if self.operation_type not in ("record-interpretation", "apply-selected-merge"):
            raise ContractError("operation outside this review increment")
        if (type(self.schema_version) is not int or self.schema_version not in (1, 2, 3)
                or self.rule_version != {1: "f0-review-v1", 2: "paper-review-v2", 3: "paper-review-v3"}[self.schema_version]):
            raise ContractError("unknown schema or rule version")
        if self.schema_version == 3 and self.operation_type != "apply-selected-merge":
            raise ContractError("cumulative review currently supports selected merges only")
        digest_text(self.operation_digest)
        digest_text(self.manuscript_digest)
        integer(self.evidence_watermark, 0, 6 if self.schema_version == 1 else 32)
        integer(self.sealed_at)
        integer(self.expires_at)
        if not self.sealed_at < self.expires_at <= self.sealed_at + 300:
            raise ContractError("review lifetime must be within five minutes")
        _tuple(self.heads, 2)
        names = []
        for pair in self.heads:
            _tuple(pair, 2)
            if len(pair) != 2 or pair[0] not in ("main", "alternative"):
                raise ContractError("unknown ref")
            identifier(pair[1])
            names.append(pair[0])
        if "main" not in names or len(set(names)) != len(names):
            raise ContractError("unique main/alternative heads required")


@dataclass(frozen=True)
class SealedReview:
    judgment: Judgment
    context: ReviewContext
    selection: Selection
    disposition: str
    answers: tuple[str, ...]
    payload: bytes
    digest: str
    source_judgments: tuple[Judgment, ...] = ()

    @property
    def rationale(self):
        return self.judgment.rationale

    def is_current(self, context, *, now):
        integer(now)
        try:
            checked = seal_review(self.judgment, self.context, self.selection,
                                  disposition=self.disposition, answers=self.answers,
                                  source_judgments=self.source_judgments)
        except ContractError:
            return False
        return checked == self and self.context == context and self.context.sealed_at <= now < self.context.expires_at


def validate_explanation(judgment, disposition, answers, *, inherited_ai=False):
    if not isinstance(judgment, Judgment):
        raise ContractError("typed judgment required")
    if type(inherited_ai) is not bool:
        raise ContractError("explicit source provenance classification required")
    _tuple(answers, 3)
    for answer in answers:
        bounded_text(answer)
    if disposition not in ("not-required", "answered", "deferred"):
        raise ContractError("unknown explanation disposition")
    if (disposition == "answered") != bool(answers):
        raise ContractError("answers and explanation disposition disagree")
    ai_influenced = judgment.ai_influenced or inherited_ai
    if ai_influenced and disposition == "not-required":
        raise ContractError("AI-influenced scientific review requires answer or deferral")
    if not ai_influenced and disposition != "not-required":
        raise ContractError("manual review does not open an AI explanation obligation")


def seal_review(judgment, context, selection, *, disposition, answers=(), source_judgments=()):
    if not isinstance(judgment, Judgment) or not isinstance(context, ReviewContext) or not isinstance(selection, Selection):
        raise ContractError("typed judgment, context and selection required")
    if (judgment.project_id, judgment.episode_id) != (context.project_id, context.episode_id):
        raise ContractError("cross-project or episode review")
    bounded_text(judgment.text)
    bounded_text(judgment.rationale)
    if not selection.closure:
        raise ContractError("review requires selected reasoning")
    if context.schema_version == 1 and any(change.kind == "claim" for change in selection.changes):
        raise ContractError("additional claims require the paper review profile")
    # A constructed or altered Selection cannot smuggle in unrelated closure.
    if select_changes(selection.changes, selection.selected, selection.evidence_references) != selection:
        raise ContractError("selection closure changed")
    _tuple(source_judgments, 8)
    if context.schema_version == 3:
        episodes = set()
        current_source = None
        for source in source_judgments:
            if (not isinstance(source, Judgment) or source.project_id != context.project_id
                    or source.episode_id in episodes):
                raise ContractError("unique same-project source judgments required")
            bounded_text(source.text)
            bounded_text(source.rationale)
            episodes.add(source.episode_id)
            if source.episode_id == context.episode_id:
                current_source = source
        if current_source is None or judgment.history[:len(current_source.history)] != current_source.history:
            raise ContractError("review must retain its current episode's source contribution chain")
    elif source_judgments:
        raise ContractError("source episode judgments require the cumulative review profile")
    validate_explanation(judgment, disposition, answers,
                         inherited_ai=any(source.ai_influenced for source in source_judgments))
    value = {"schema_version": context.schema_version, "judgment": asdict(judgment), "context": asdict(context),
             "selection": asdict(selection), "disposition": disposition, "answers": answers}
    if context.schema_version == 3:
        value["source_judgments"] = [asdict(source) for source in source_judgments]
    return SealedReview(judgment, context, selection, disposition, answers,
                        canonical_bytes(value), digest(value), source_judgments)


@dataclass(frozen=True)
class Debt:
    kind: str
    project_id: str
    episode_id: str
    cause_operation_id: str
    review_digest: str
    anchor_id: str | None
    status: str = "open"

    def __post_init__(self):
        if self.kind not in ("manuscript", "understanding") or self.status not in ("open", "closed-by-human", "superseded"):
            raise ContractError("unknown debt kind or status")
        for value in (self.project_id, self.episode_id, self.cause_operation_id):
            identifier(value)
        digest_text(self.review_digest)
        if self.kind == "manuscript":
            identifier(self.anchor_id)
        elif self.anchor_id is not None:
            raise ContractError("understanding debt concerns an operation, not an anchor")

    @property
    def id(self):
        return "debt-" + digest({"kind": self.kind, "project": self.project_id,
                                 "episode": self.episode_id, "cause": self.cause_operation_id})[:32]


@dataclass(frozen=True)
class AcceptanceCandidate:
    review_digest: str
    requires_authorization: bool
    contributions: tuple[Contribution, ...]
    debts: tuple[Debt, ...]
    authorization_verified: bool = False
    source_judgments: tuple[Judgment, ...] = ()


def acceptance_candidate(review, *, decision):
    if not isinstance(review, SealedReview):
        raise ContractError("a proposal cannot substitute for a sealed review")
    checked = seal_review(review.judgment, review.context, review.selection,
                          disposition=review.disposition, answers=review.answers,
                          source_judgments=review.source_judgments)
    if checked != review:
        raise ContractError("sealed review was modified")
    if decision == "not-now":
        return AcceptanceCandidate(review.digest, False, (), ())
    if decision != "accept":
        raise ContractError("unknown decision")
    context = review.context
    debts = []
    if context.operation_type == "apply-selected-merge":
        debts.append(Debt("manuscript", context.project_id, context.episode_id,
                          context.operation_id, review.digest, context.anchor_id))
    if review.disposition == "deferred":
        debts.append(Debt("understanding", context.project_id, context.episode_id,
                          context.operation_id, review.digest, None))
    return AcceptanceCandidate(review.digest, True, review.judgment.history, tuple(debts),
                               source_judgments=review.source_judgments)
