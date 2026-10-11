"""Portable episode, provider-attempt and manuscript state transitions.

These immutable values validate supplied observations. They do not read files,
run a compiler, authorize a person, close debt or admit real V0 data.
"""
from dataclasses import dataclass, replace

from .canonical import ContractError, bounded_text, digest_text, identifier, integer
from .debt import CompileResult


@dataclass(frozen=True)
class EpisodeEntry:
    id: str
    baseline_head: str
    baseline_watermark: int
    state: str = "active"
    outcome: str | None = None

    def __post_init__(self):
        identifier(self.id)
        identifier(self.baseline_head)
        integer(self.baseline_watermark)
        allowed = {"active": (None,), "closed": ("complete", "incomplete", "protocol-limit"),
                   "invalidated": ("eligibility-error", "corrupted-timing")}
        if self.state not in allowed or self.outcome not in allowed[self.state]:
            raise ContractError("invalid episode state/outcome")


@dataclass(frozen=True)
class EpisodeLedger:
    project_id: str
    protocol_version: str
    entries: tuple[EpisodeEntry, ...] = ()
    status: str = "open"

    def __post_init__(self):
        identifier(self.project_id)
        identifier(self.protocol_version)
        if type(self.entries) is not tuple or len(self.entries) > 6 or not all(isinstance(e, EpisodeEntry) for e in self.entries):
            raise ContractError("bounded episode history required")
        if len({e.id for e in self.entries}) != len(self.entries) or sum(e.state == "active" for e in self.entries) > 1:
            raise ContractError("episode identities and active slot must be unique")
        if any(e.state == "active" for e in self.entries[:-1]):
            raise ContractError("the active episode must be the latest start")
        if sum(e.state == "invalidated" for e in self.entries) > 3 or self.status not in ("open", "inconclusive"):
            raise ContractError("protocol replacement budget exceeded")
        valid = sum(e.state == "active" or (e.state == "closed" and e.outcome != "protocol-limit") for e in self.entries)
        limited = [e for e in self.entries if e.outcome == "protocol-limit"]
        if valid > 3 or bool(limited) != (self.status == "inconclusive"):
            raise ContractError("invalid valid-start budget or terminal status")
        if limited and (len(limited) != 1 or self.entries[-1] != limited[0]
                        or sum(e.state == "invalidated" for e in self.entries) != 3):
            raise ContractError("inconclusive requires exhausted replacements")

    def start(self, episode_id, baseline_head, baseline_watermark):
        if self.status != "open" or any(e.state == "active" for e in self.entries):
            raise ContractError("another episode is active or the run has ended")
        if sum(e.state == "closed" and e.outcome in ("complete", "incomplete") for e in self.entries) >= 3:
            raise ContractError("three valid starts have already completed")
        return replace(self, entries=(*self.entries, EpisodeEntry(episode_id, baseline_head, baseline_watermark)))

    def _finish(self, episode_id, state, outcome, status="open"):
        if self.status != "open" or not any(e.id == episode_id and e.state == "active" for e in self.entries):
            raise ContractError("exact active episode required")
        return replace(self, entries=tuple(replace(e, state=state, outcome=outcome) if e.id == episode_id else e
                                          for e in self.entries), status=status)

    def close(self, episode_id, *, completed):
        if type(completed) is not bool:
            raise ContractError("explicit completion outcome required")
        return self._finish(episode_id, "closed", "complete" if completed else "incomplete")

    def invalidate(self, episode_id, reason):
        if reason not in ("eligibility-error", "corrupted-timing"):
            raise ContractError("product failure cannot invalidate a valid start")
        if sum(e.state == "invalidated" for e in self.entries) == 3:
            return self._finish(episode_id, "closed", "protocol-limit", "inconclusive")
        return self._finish(episode_id, "invalidated", reason)


@dataclass(frozen=True)
class ProposalAttempt:
    request_id: str
    context_digest: str
    created_at: int
    expires_at: int
    state: str = "pending"
    text: str | None = None

    def __post_init__(self):
        identifier(self.request_id)
        digest_text(self.context_digest)
        integer(self.created_at)
        integer(self.expires_at)
        if not self.created_at < self.expires_at <= self.created_at + 300:
            raise ContractError("invalid provider attempt lifetime")
        if self.state not in ("pending", "proposed", "cancelled", "stale", "expired", "failed"):
            raise ContractError("unknown provider state")
        if self.state == "proposed":
            bounded_text(self.text)
        elif self.text is not None:
            raise ContractError("non-proposal states cannot retain adoptable text")

    def cancel(self):
        return replace(self, state="cancelled", text=None)

    def complete(self, text, *, current_digest, now):
        digest_text(current_digest)
        integer(now)
        if self.state in ("cancelled", "stale", "expired", "failed"):
            return self
        if not self.created_at <= now < self.expires_at:
            return replace(self, state="expired", text=None)
        if current_digest != self.context_digest:
            return replace(self, state="stale", text=None)
        if self.state == "proposed":
            if self.text != text:
                raise ContractError("changed provider retry")
            return self
        try:
            bounded_text(text)
        except ContractError:
            return replace(self, state="failed")
        return replace(self, state="proposed", text=text)


@dataclass(frozen=True)
class ManuscriptSaga:
    project_id: str
    debt_id: str
    anchor_id: str
    graph_head: str
    patch_id: str
    attempt_id: str
    fencing_token: int
    source_digest: str
    postimage_digest: str
    compiler_digest: str
    configuration_digest: str
    phase: str = "debt-open"
    compile_result: CompileResult | None = None

    def __post_init__(self):
        for value in (self.project_id, self.debt_id, self.anchor_id, self.graph_head, self.patch_id, self.attempt_id):
            identifier(value)
        for value in (self.source_digest, self.postimage_digest, self.compiler_digest, self.configuration_digest):
            digest_text(value)
        integer(self.fencing_token, 1)
        if self.phase not in ("debt-open", "patch-prepared", "applying", "applied-unverified", "compiling", "verified", "restored", "recovery-required"):
            raise ContractError("unknown manuscript state")
        if (self.phase == "verified") != (self.compile_result is not None):
            raise ContractError("only exact compile verification can carry a result")
        if self.compile_result is not None:
            self._validate_compile(self.compile_result)

    @property
    def debt_closed(self):
        return False

    def _binding(self, head, fence):
        integer(fence, 1)
        if head != self.graph_head or fence != self.fencing_token:
            raise ContractError("stale manuscript head or fencing token")

    def advance(self, event, *, observed_hash, head, fence):
        self._binding(head, fence)
        digest_text(observed_hash)
        transitions = {("debt-open", "prepare"): ("patch-prepared", self.source_digest),
                       ("patch-prepared", "begin-apply"): ("applying", self.source_digest),
                       ("applying", "applied"): ("applied-unverified", self.postimage_digest),
                       ("applied-unverified", "begin-compile"): ("compiling", self.postimage_digest)}
        if (self.phase, event) not in transitions:
            raise ContractError("illegal manuscript transition; inspect or restore if recovery is required")
        phase, expected = transitions[(self.phase, event)]
        return replace(self, phase=phase if observed_hash == expected else "recovery-required")

    def verify(self, result):
        if self.phase != "compiling":
            raise ContractError("compile must actually reach its verification boundary")
        self._validate_compile(result)
        return replace(self, phase="verified", compile_result=result)

    def _validate_compile(self, result):
        if not isinstance(result, CompileResult):
            raise ContractError("typed compile observation required")
        expected = (self.debt_id, self.anchor_id, self.patch_id, self.attempt_id, self.source_digest,
                    self.postimage_digest, self.compiler_digest, self.configuration_digest, self.graph_head, self.fencing_token, "verified")
        actual = (result.debt_id, result.anchor_id, result.patch_id, result.attempt_id, result.source_digest,
                  result.postimage_digest, result.compiler_digest, result.configuration_digest, result.graph_head, result.fencing_token, result.status)
        if actual != expected:
            raise ContractError("compile observation belongs to another exact attempt")

    def restore(self, *, observed_hash, head, fence):
        self._binding(head, fence)
        digest_text(observed_hash)
        if self.phase not in ("applying", "applied-unverified", "compiling", "recovery-required"):
            raise ContractError("restore requires an interrupted or failed manuscript attempt")
        return replace(self, phase="restored" if observed_hash == self.source_digest else "recovery-required")
