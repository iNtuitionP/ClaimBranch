"""Volatile paper-bound drafting for adapters; no accepted history or transport.

The source remains PaperService's immutable candidate history. A new draft does
not copy its previous judgment or pretend to start/merge a canonical episode.
An optional constructor-supplied frozen response exercises the offline broker;
neither a UI request nor model output can choose a destination or authority.
"""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import secrets
from threading import RLock
import time

from claimbranch.core.canonical import ContractError, bounded_text, canonical_bytes, decode, digest, identifier, integer
from claimbranch.core.context import ContextRecord, Destination, OfflineBroker, RESULT_BYTE_LIMIT, compile_context, review_outbound
from claimbranch.core.lifecycle import ProposalAttempt
from claimbranch.core.review import Judgment, validate_explanation
from claimbranch.core.paper_changes import request_schema as changes_request_schema
from claimbranch.core.research_schema import normalize
from .paper_service import PaperService
from .paper_branch import judgment_value


class PaperDraftSession:
    def _bytes(self, value):
        service = getattr(self, '_service', None)
        return service._bytes(value) if service else canonical_bytes(value)

    def _decode(self, raw):
        service = getattr(self, '_service', None)
        return service._decode(raw) if service else decode(raw)

    def _digest(self, value):
        service = getattr(self, '_service', None)
        return service._digest(value) if service else digest(value)

    def __init__(self, service, *, ref="main", episode_id=None, frozen_response=None, frozen_result=None, clock=None):
        if not isinstance(service, PaperService):
            raise ContractError("paper draft requires a versioned paper service")
        if frozen_response is not None:
            bounded_text(frozen_response)
            if frozen_result is not None:
                raise ContractError("choose one frozen response source")
            frozen_result = self._bytes({"schema": "claimbranch.provider-result/v1", "status": "ok", "text": frozen_response})
        if frozen_result is not None and (type(frozen_result) is not bytes or len(frozen_result) > RESULT_BYTE_LIMIT):
            raise ContractError("bounded frozen provider bytes required")
        view = service.query(ref, episode_id=episode_id)
        self._service, self._ref = service, ref
        self._project, self._episode = view["project_id"], view["episode_id"]
        self._view_digest = view["digest"]
        self._response = frozen_result
        self._clock = clock or (lambda: int(time.time()))
        self._lock = RLock()
        self._broker = OfflineBroker()
        self._destination = Destination("offline://frozen", "paper-example-v1")
        self._judgment = Judgment.start(self._project, self._episode)
        self._draft_id = "draft-" + secrets.token_hex(16)
        self._include_draft = False
        self._text = self._rationale = ""
        self._revision = 0
        self._before_proposal = None
        self._request = self._outbound = self._attempt = self._proposal = None
        self._attempts = {}
        self._prior_dispatches = 0
        self._adopted = set()
        self._changes_request = self._changes_preview = self._changes_review = None
        self._branch_request = self._branch_preview = None

    def _clear_changes(self):
        self._changes_request = self._changes_preview = self._changes_review = None
        self._branch_request = self._branch_preview = None

    def _invalidate(self, state):
        if self._attempt and self._attempt.state in ("pending", "proposed"):
            self._attempt = replace(self._attempt, state=state, text=None)
            if self._attempt.request_id in self._attempts:
                self._attempts[self._attempt.request_id] = self._attempt
        self._outbound = self._proposal = None

    def _expire(self):
        if self._attempt and self._attempt.state in ("pending", "proposed"):
            if not self._attempt.created_at <= self._clock() < self._attempt.expires_at:
                self._invalidate("expired")
        if self._changes_preview:
            preview = self._decode(self._changes_preview)
            if not preview["created_at"] <= self._clock() < preview["expires_at"]:
                self._clear_changes()
        if self._branch_preview:
            preview = self._decode(self._branch_preview)
            if not preview["created_at"] <= self._clock() < preview["expires_at"]:
                self._clear_changes()

    def state(self):
        with self._lock:
            self._expire()
            return self._decode(self._bytes({
                "schema": "claimbranch.paper-draft/v1", "mode": "synthetic-volatile",
                "draft_id": self._draft_id, "revision": self._revision, "paper": {"project_id": self._project, "episode_id": self._episode,
                    "ref": self._ref, "view_digest": self._view_digest},
                "draft": {"text": self._text, "rationale": self._rationale,
                    "ai_influenced": self._judgment.ai_influenced,
                    "contributions": [asdict(item) for item in self._judgment.history]},
                "before_proposal": self._before_proposal, "ai_available": self._response is not None,
                "outbound": {"request": self._decode(self._outbound.payload), "digest": self._outbound.digest,
                             "draft_revision": self._revision} if self._outbound else None,
                "attempt": self._attempt_state(self._attempt) if self._attempt else None,
                "attempts": [self._attempt_state(item) for item in self._attempts.values()],
                "proposal": {**asdict(self._proposal), "adopted": self._proposal.id in self._adopted} if self._proposal else None,
                "traces": [{**{key: value for key, value in asdict(trace).items() if key != "payload"},
                            "digest": trace.digest} for trace in self._broker.sent],
                "changes_preview": {key: self._decode(self._changes_preview)[key] for key in ("digest", "expires_at")} if self._changes_preview else None,
                "changes_review": {key: self._decode(self._changes_review)[key] for key in ("digest", "disposition")} if self._changes_review else None,
                "branch_preview": {key: self._decode(self._branch_preview)[key] for key in ("digest", "expires_at")} if self._branch_preview else None,
                "accepted_writes": 0, "authorization_verified": False}))

    def _attempt_state(self, attempt):
        started = next((item for item in self._broker.dispatched if item.request_id == attempt.request_id), None)
        return {"request_id": attempt.request_id, "state": attempt.state,
                "context_digest": attempt.context_digest, "created_at": attempt.created_at,
                "expires_at": attempt.expires_at, "dispatched": started is not None,
                "dispatched_at": started.dispatched_at if started else None}

    def edit(self, text, rationale):
        raw = self._decode(self._bytes({"text": text, "rationale": rationale}))
        if any(type(value) is not str for value in raw.values()):
            raise ContractError("draft fields must be bounded text, including empty drafts")
        with self._lock:
            if (raw["text"], raw["rationale"]) != (self._text, self._rationale):
                self._text, self._rationale = raw["text"], raw["rationale"]
                self._revision += 1
                self._invalidate("stale")
                self._clear_changes()
            return self.state()

    def update_source(self, service):
        if not isinstance(service, PaperService):
            raise ContractError("paper source requires a versioned service")
        with self._lock:
            view = service.query(self._ref, episode_id=self._episode)
            if (view["project_id"], view["episode_id"]) != (self._project, self._episode):
                raise ContractError("a draft cannot be moved into a different research context")
            if view["digest"] != self._view_digest:
                self._service, self._view_digest = service, view["digest"]
                self._revision += 1
                self._invalidate("stale")
                self._clear_changes()
            return self.state()

    def _attempt_binding(self, bundle):
        # Even an edit followed by a textual revert invalidates a preview.
        return self._digest({"paper_context": bundle.digest, "draft_revision": self._revision})

    def _with_draft(self, bundle, include_draft):
        if not include_draft:
            return bundle
        fields = {"statement": self._text if self._text.strip() else None,
                  "rationale": self._rationale if self._rationale.strip() else None,
                  "origin": {"ai_influenced": self._judgment.ai_influenced,
                             "contributions_digest": self._digest([asdict(item) for item in self._judgment.history])}}
        record = ContextRecord.create(self._project, self._draft_id, "draft", "private", fields, schema_version=2)
        selection = replace(bundle.selection, fields=(*bundle.selection.fields, (record.id, tuple(fields))))
        return compile_context((*bundle.records, record), selection)

    def _current_context(self):
        return self._with_draft(self._service.compile_context(self._decode(self._request)), self._include_draft)

    def compile_proposal_context(self, request, *, include_draft=False):
        """Read selected science with optional unfinished writing; no dispatch.

        Reuses the existing context screen and exact owner/view binding. Reading
        does not enable AI, replace an outstanding request or create consent.
        """
        with self._lock:
            if type(include_draft) is not bool:
                raise ContractError("explicit Boolean draft selection required")
            bundle = self._service.compile_context(request)
            if bundle.selection.binding != self._bytes({"ref": self._ref, "view_digest": self._view_digest}):
                raise ContractError("request must use the draft's exact paper view")
            return self._with_draft(bundle, include_draft)

    def prepare_request(self, request, *, include_draft=False):
        with self._lock:
            if type(include_draft) is not bool:
                raise ContractError("explicit Boolean draft selection required")
            if self._response is None:
                raise ContractError("AI is off; manual drafting remains available")
            if self._prior_dispatches + len(self._broker.dispatched) >= 3:
                raise ContractError("the example allows one proposal and two requested revisions")
            raw = self._bytes(request)
            bundle = self.compile_proposal_context(self._decode(raw), include_draft=include_draft)
            review = review_outbound(bundle, self._destination, request_id="request-" + secrets.token_hex(16),
                                     nonce=secrets.token_hex(24), now=self._clock())
            self._invalidate("stale")
            self._request, self._outbound = raw, review
            self._include_draft = include_draft
            self._attempt = ProposalAttempt(review.request_id, self._attempt_binding(bundle), review.created_at, review.expires_at)
            self._proposal = None
            return self.state()

    def cancel_request(self):
        with self._lock:
            self._invalidate("cancelled")
            return self.state()

    def begin_proposal(self, request_id, review_digest):
        """Consume exact consent, leaving the response outstanding and editable."""
        with self._lock:
            self._expire()
            if (not self._outbound or not self._attempt or self._attempt.state != "pending"
                    or (request_id, review_digest) != (self._outbound.request_id, self._outbound.digest)):
                raise ContractError("review the current exact request before offline dispatch")
            if self._prior_dispatches + len(self._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            bundle = self._current_context()
            if self._attempt.context_digest != self._attempt_binding(bundle):
                self._invalidate("stale")
                raise ContractError("draft or paper context changed after the request review")
            try:
                self._broker.begin(bundle, self._destination, self._outbound, now=self._clock())
            except ContractError:
                self._invalidate("failed")
                raise
            self._outbound = None
            self._attempts[request_id] = self._attempt
            return self.state()

    def complete_proposal(self, request_id):
        """Deliver only the constructor-owned frozen result, never UI output.

        There is no thread, network or blocking wait. An adapter schedules this
        separately from begin; discarded arrivals remain visible in traces.
        """
        identifier(request_id)
        with self._lock:
            if request_id not in self._attempts:
                raise ContractError("response requires this session's dispatched request")
            self._expire()
            proposal = self._broker.complete(request_id, self._response)
            attempt = self._attempts[request_id]
            current = self._attempt.request_id == request_id
            if attempt.state == "pending":
                if proposal is None:
                    attempt = replace(attempt, state="failed")
                else:
                    try:
                        binding = self._attempt_binding(self._current_context())
                    except ContractError:
                        attempt = replace(attempt, state="stale")
                    else:
                        attempt = attempt.complete(proposal.text, current_digest=binding, now=self._clock())
            self._attempts[request_id] = attempt
            if current:
                self._attempt = attempt
                self._proposal = proposal if attempt.state == "proposed" else None
            return self.state()

    def request_proposal(self, request_id, review_digest):
        """Synchronous convenience for existing offline callers."""
        self.begin_proposal(request_id, review_digest)
        state = self.complete_proposal(request_id)
        if (not state["proposal"] or state["proposal"]["id"] != "proposal-" + self._digest(request_id)):
            raise ContractError("offline response failed, expired or no longer matches the draft")
        return state

    def _current_judgment(self):
        if (self._text, self._rationale) == (self._judgment.text, self._judgment.rationale):
            return self._judgment
        return self._judgment.edit(self._text, self._rationale)

    def use_proposal(self, proposal_id):
        with self._lock:
            self._expire()
            if (not self._proposal or self._proposal.id != proposal_id or proposal_id in self._adopted
                    or self._attempt.state != "proposed"):
                raise ContractError("a current unused proposal is required")
            bundle = self._current_context()
            self._attempt = self._attempt.complete(self._proposal.text, current_digest=self._attempt_binding(bundle), now=self._clock())
            self._attempts[self._attempt.request_id] = self._attempt
            if self._attempt.state != "proposed":
                self._proposal = None
                raise ContractError("proposal context changed or expired before adoption")
            judgment = self._current_judgment() if self._text.strip() and self._rationale.strip() else self._judgment
            judgment = judgment.use_proposal(self._proposal)
            # Keep the replaced edit buffer, even before a complete human
            # contribution exists. This is volatile recovery, not accepted history.
            self._before_proposal = {"text": self._text, "rationale": self._rationale}
            self._judgment, self._text = judgment, judgment.text
            self._adopted.add(proposal_id)
            self._revision += 1
            self._clear_changes()
            return self.state()

    def review_draft(self):
        """Materialize one complete candidate without another rationale form."""
        with self._lock:
            bounded_text(self._text)
            bounded_text(self._rationale)
            judgment = self._current_judgment()
            value = {"schema": "claimbranch.paper-draft-review/v1", "project_id": self._project,
                     "episode_id": self._episode, "ref": self._ref, "view_digest": self._view_digest,
                     "draft_revision": self._revision, "judgment": asdict(judgment),
                     "authority": "unverified-candidate", "authorization_verified": False}
            result = {**value, "digest": self._digest(value)}
            self._judgment = judgment
            return result

    def not_now(self):
        # This is an unaccepted draft. It does not open or resolve debt.
        with self._lock:
            self._clear_changes()
            return self.cancel_request()

    def invalidate_change_reviews(self):
        """Revoke changed amendment scope without cancelling independent AI work."""
        with self._lock:
            self._clear_changes()

    def _check_changes_request(self, request):
        request = normalize(request, changes_request_schema())
        if (request["draft_id"], request["draft_revision"], request["ref"], request["view_digest"]) != (
                self._draft_id, self._revision, self._ref, self._view_digest):
            raise ContractError("scientific selection must match the current draft and paper view")
        return request

    def prepare_branch(self, request):
        """Inspect a complete draft's selected branch commands, without saving.

        Recording a candidate alternative does not require AI teach-back; the
        separate exact merge review checks inherited influence and explanation.
        """
        with self._lock:
            request = self._check_changes_request(request)
            now = integer(self._clock())
            operation_id = "record-" + secrets.token_hex(16)
            created_at = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _, result = self._service.branch_candidate(request, self._current_judgment(),
                operation_id=operation_id, created_at=created_at, source_node_id=getattr(self, '_imported_subject', None))
            value = {"schema": "claimbranch.prepared-paper-branch/v1", "operation_id": operation_id,
                     "operation_created_at": created_at, "created_at": now, "expires_at": now + 300, **result,
                     "authority": "unaccepted-preview", "acceptance_available": False, "authorization_verified": False}
            prepared = self._bytes({**value, "digest": self._digest(value)})
            joined = judgment_value(result["preview"]["provenance"]["judgment"])
            if joined != self._judgment:
                self._invalidate("stale")
            self._clear_changes()
            self._judgment = joined
            self._branch_request, self._branch_preview = self._bytes(request), prepared
            return self._decode(prepared)

    def get_branch_preview(self):
        with self._lock:
            self._expire()
            return self._decode(self._branch_preview) if self._branch_preview else None

    def branch_candidate(self, preview_digest):
        """Reconstruct a reviewed value; do not update this session or its owner."""
        with self._lock:
            self._expire()
            prepared = self._decode(self._branch_preview) if self._branch_preview else None
            if not prepared or prepared["digest"] != preview_digest:
                raise ContractError("inspect the exact current branch preview first")
            candidate, result = self._service.branch_candidate(self._decode(self._branch_request), self._current_judgment(),
                operation_id=prepared["operation_id"], created_at=prepared["operation_created_at"], source_node_id=getattr(self, '_imported_subject', None))
            if any(prepared[key] != value for key, value in result.items()):
                self._clear_changes()
                raise ContractError("draft or source changed after the branch preview")
            return candidate

    def prepare_changes(self, request):
        """Inspect selected scientific effects; no explanation/approval needed yet."""
        with self._lock:
            request = self._check_changes_request(request)
            judgment = self._current_judgment()
            preview = self._service.preview_changes(request, judgment, source_node_id=getattr(self, '_imported_subject', None))
            now = integer(self._clock())
            value = {"schema": "claimbranch.prepared-paper-changes/v1", "id": "review-" + secrets.token_hex(16),
                     "created_at": now, "expires_at": now + 300, "preview": preview}
            prepared = self._bytes({**value, "digest": self._digest(value)})
            # Validate/encode before replacing any prior review or draft snapshot.
            self._clear_changes()
            self._changes_request = self._bytes(request)
            self._changes_preview, self._changes_review = prepared, None
            self._judgment = judgment
            return self._decode(prepared)

    def get_changes_preview(self):
        with self._lock:
            self._expire()
            return self._decode(self._changes_preview) if self._changes_preview else None

    def get_changes_review(self):
        with self._lock:
            self._expire()
            return self._decode(self._changes_review) if self._changes_review else None

    def finish_changes_review(self, preview_digest, *, disposition, answers):
        """Finish a current review; its digest is not an authorization receipt."""
        with self._lock:
            self._expire()
            prepared = self._decode(self._changes_preview) if self._changes_preview else None
            if not prepared or preview_digest != prepared["digest"]:
                raise ContractError("a current exact scientific change preview is required")
            judgment = self._current_judgment()
            current = self._service.preview_changes(self._decode(self._changes_request), judgment, source_node_id=getattr(self, '_imported_subject', None))
            if current != prepared["preview"]:
                self._clear_changes()
                raise ContractError("the scientific preview changed; inspect the new scope")
            if type(answers) is not list:
                raise ContractError("explicit bounded explanation answers required")
            validate_explanation(judgment, disposition, tuple(answers), inherited_ai=current["provenance"]["ai_influenced"] or current['provenance'].get('origin_uncertain', False))
            value = {"schema": "claimbranch.paper-change-review/v1", "preview_digest": prepared["digest"],
                     "scientific_digest": current["digest"], "draft_id": self._draft_id, "draft_revision": self._revision,
                     "project_id": self._project, "episode_id": self._episode, "ref": self._ref,
                     "view_digest": self._view_digest, "expires_at": prepared["expires_at"],
                     "disposition": disposition, "answers": answers,
                     "consequences_if_accepted": {"understanding_debt": disposition == "deferred",
                         "manuscript_review_anchor_ids": current["impact"]["potentially_affected_anchor_ids"]},
                     "authority": "unaccepted-review", "acceptance_available": False, "authorization_verified": False}
            reviewed = self._bytes({**value, "digest": self._digest(value)})
            self._changes_review = reviewed
            return self._decode(reviewed)

    def erase_trace(self, request_id):
        with self._lock:
            self._broker.erase_payload(request_id)
            return self.state()
