"""Exact volatile wording review against supplied bytes, with no file access.

Byte fingerprints bind the supplied source; they do not verify a filesystem
identity or authorize an apply/compile/restore/debt-closure operation.
"""
from difflib import unified_diff
import hashlib
import secrets
from threading import RLock
import time

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest, identifier, integer
from claimbranch.core.marked_text import preview_marked_text
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import validate_explanation
from .paper_branch import judgment_value
from .paper_draft import PaperDraftSession
from .paper_service import PaperService


def _source(value):
    if value is not None:
        if type(value) is not bytes or not value or len(value) > 65536:
            raise ContractError("supplied manuscript requires at most 64 KiB of nonempty UTF-8 bytes")
        try:
            value.decode("utf-8")
        except UnicodeError as error:
            raise ContractError("supplied manuscript is not UTF-8") from error
    return value


def _wording_binding(state):
    return digest({key: state[key] for key in ("draft_id", "revision", "paper", "draft")})


def _paper_context(view):
    return {"project_id": view["project_id"], "episode_id": view["episode_id"],
            "ref": "main", "view_digest": view["digest"]}


class PaperManuscriptSession:
    def __init__(self, history, *, work_id, source=None, frozen_response=None, clock=None):
        identifier(work_id)
        self._service = PaperService(history)
        self._work(self._service, work_id)
        self._history, self._work_id, self._source = history, work_id, _source(source)
        self._clock = clock or (lambda: int(time.time()))
        self._lock = RLock()
        self.draft = PaperDraftSession(self._service, frozen_response=frozen_response, clock=self._clock)
        self._clear()

    @staticmethod
    def _work(service, work_id):
        work = service.pending_work()
        item = next((item for item in work["items"] if item["id"] == work_id), None)
        if not item or item["kind"] != "manuscript":
            raise ContractError("select an existing conditional manuscript work item")
        return work, item

    def _clear(self):
        self._prepared = self._reviewed = self._after = None

    def _fresh(self):
        now = integer(self._clock())
        if self._prepared:
            value = decode(self._prepared)
            if (not value["created_at"] <= now < value["expires_at"]
                    or value["wording_binding"] != _wording_binding(self.draft.state())):
                self._clear()
        return now

    def state(self):
        with self._lock:
            self._fresh()
            work, item = self._work(self._service, self._work_id)
            draft = self.draft.state()
            return {"schema": "claimbranch.paper-manuscript-session/v1", "draft": draft,
                    "work": item, "history_digest": work["history_digest"],
                    "source_available": self._source is not None, "source_verified": False,
                    "source_digest": hashlib.sha256(self._source).hexdigest() if self._source is not None else None,
                    "context_current": draft["paper"] == _paper_context(self._service.query()),
                    "preview_digest": decode(self._prepared)["digest"] if self._prepared else None,
                    "review_digest": decode(self._reviewed)["digest"] if self._reviewed else None,
                    "accepted_writes": 0, "write_available": False, "compile_available": False,
                    "closure_available": False, "authorization_verified": False}

    def _build(self, *, operation_id, created_at, expires_at):
        if self._source is None:
            raise ContractError("manuscript source is unavailable; retain the wording draft")
        current = self._service.query()
        if self.draft.state()["paper"] != _paper_context(current):
            raise ContractError("wording requires this exact current paper context; the old draft is retained")
        work, item = self._work(self._service, self._work_id)
        draft = self.draft.review_draft()
        source_digest = hashlib.sha256(self._source).hexdigest()
        after = preview_marked_text(self._source, item["anchor_id"], draft["judgment"]["text"], source_digest)
        if len(after) > 65536:
            raise ContractError("candidate manuscript exceeds the 64 KiB source bound")
        influenced = any(c["contributor"] == "ai" for judgment in [draft["judgment"], *current["judgments"]]
                         for c in judgment["history"])
        value = {"schema": "claimbranch.prepared-paper-manuscript/v1", "operation_id": operation_id,
                 "created_at": created_at, "expires_at": expires_at,
                 "project_id": current["project_id"], "episode_id": current["episode_id"],
                 "work_id": self._work_id, "work_digest": digest(item),
                 "cause_episode_id": item["episode_id"], "cause_operation_id": item["cause_operation_id"],
                 "cause_judgment": item["judgment"], "history_digest": work["history_digest"],
                 "main_head": current["head"], "evidence_watermark": current["evidence_watermark"],
                 "anchor_id": item["anchor_id"], "source_digest": source_digest,
                 "postimage_digest": hashlib.sha256(after).hexdigest(),
                 "draft": draft, "wording_binding": _wording_binding(self.draft.state()),
                 "source_judgments": current["judgments"], "ai_influenced": influenced,
                 "source_verified": False, "authority": "unaccepted-preview",
                 "acceptance_available": False, "write_available": False, "authorization_verified": False}
        return canonical_bytes({**value, "digest": digest(value)}), after

    def prepare(self):
        with self._lock:
            now = integer(self._clock())
            prepared, after = self._build(operation_id="manuscript-" + secrets.token_hex(16),
                                          created_at=now, expires_at=now + 300)
            self._prepared, self._after, self._reviewed = prepared, after, None
            return self.get_preview()

    def get_preview(self):
        with self._lock:
            self._fresh()
            if not self._prepared:
                return None
            before, after = self._source.decode("utf-8"), self._after.decode("utf-8")
            # Artifact text is rendered from the original bytes, outside canonical
            # JSON normalization. Hashes in the sealed metadata bind exact bytes,
            # including mixed line endings and decomposed Unicode surrounding the block.
            return {**decode(self._prepared), "source": {"before": before, "after": after,
                    "diff": "".join(unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                                  fromfile="supplied manuscript", tofile="candidate manuscript"))}}

    def _current(self):
        self._fresh()
        if not self._prepared:
            raise ContractError("inspect the exact current manuscript preview first")
        prepared = decode(self._prepared)
        current, after = self._build(operation_id=prepared["operation_id"], created_at=prepared["created_at"],
                                      expires_at=prepared["expires_at"])
        if current != self._prepared or after != self._after:
            self._clear()
            raise ContractError("manuscript source, wording or paper context changed")
        return prepared

    def finish(self, preview_digest, *, disposition, answers):
        with self._lock:
            prepared = self._current()
            if prepared["digest"] != preview_digest:
                raise ContractError("the exact current manuscript preview is required")
            if type(answers) is not list:
                raise ContractError("explicit bounded explanation answers required")
            validate_explanation(judgment_value(prepared["draft"]["judgment"]), disposition, tuple(answers),
                                 inherited_ai=prepared["ai_influenced"])
            value = {"schema": "claimbranch.paper-manuscript-review/v1", "preview_digest": preview_digest,
                     "operation_id": prepared["operation_id"], "work_id": self._work_id,
                     "history_digest": prepared["history_digest"], "wording_binding": prepared["wording_binding"],
                     "source_digest": prepared["source_digest"], "postimage_digest": prepared["postimage_digest"],
                     "expires_at": prepared["expires_at"], "disposition": disposition, "answers": answers,
                     "consequences_if_accepted": {"understanding_review_required": disposition == "deferred"},
                     "authority": "unaccepted-review", "write_available": False, "acceptance_available": False,
                     "compile_available": False, "closure_available": False, "authorization_verified": False}
            self._reviewed = canonical_bytes({**value, "digest": digest(value)})
            return decode(self._reviewed)

    def get_review(self):
        with self._lock:
            self._fresh()
            return decode(self._reviewed) if self._reviewed else None

    def postimage(self, review_digest):
        """Return candidate bytes without writing or resolving work."""
        with self._lock:
            self._current()
            if not self._reviewed or decode(self._reviewed)["digest"] != review_digest:
                raise ContractError("complete the exact current manuscript review first")
            return self._after

    def not_now(self):
        with self._lock:
            self._clear()
            self.draft.not_now()

    def update_source(self, history, *, source):
        with self._lock:
            source = _source(source)
            if (not isinstance(history, ResearchHistory) or history.seed != self._history.seed
                    or history.commands[:len(self._history.commands)] != self._history.commands):
                raise ContractError("manuscript refresh requires an append-only extension of the same history")
            service = PaperService(history)
            self._work(service, self._work_id)
            self.draft.update_source(service)
            if history != self._history or source != self._source:
                self._clear()
            self._history, self._service, self._source = history, service, source
