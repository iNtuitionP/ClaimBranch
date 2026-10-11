"""Volatile exact review of a recorded cumulative alternative's selected merge.

The owned immutable history supplies all scientific content and provenance.
Hashes bind content, not authority: manuscript fingerprints are supplied and
unverified, and candidate() computes a value without committing or saving it.
Unrecorded PaperDraftSession overlays are not silently staged by this adapter.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import secrets
from threading import RLock
import time

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest, digest_text, identifier, integer
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import acceptance_candidate
from .paper_service import PaperService


class PaperMergeSession:
    def __init__(self, history, *, episode_id, manuscript_digest, clock=None):
        identifier(episode_id)
        digest_text(manuscript_digest)
        self._service = PaperService(history)
        if history.schema_version != 3 or self._service.episodes()["active_episode_id"] != episode_id:
            raise ContractError("merge review requires the explicit active cumulative episode")
        self._history, self._episode = history, episode_id
        self._manuscript = manuscript_digest
        self._clock = clock or (lambda: int(time.time()))
        self._nonce = "session-" + secrets.token_hex(16)
        self._lock = RLock()
        self._clear()

    def _clear(self):
        self._prepared = self._review = self._command = self._sealed = None

    def _expire(self):
        now = integer(self._clock())
        if self._prepared:
            value = decode(self._prepared)
            if not value["created_at"] <= now < value["expires_at"]:
                self._clear()
        return now

    def prepare(self, selected_ids):
        """Inspect selection, graphs and inherited contributions before answering."""
        with self._lock:
            preview = self._service.preview_merge(selected_ids, episode_id=self._episode)
            now = integer(self._clock(), 0, 253402300799)
            value = {"schema": "claimbranch.prepared-paper-merge/v1", "id": "review-" + secrets.token_hex(16),
                     "operation_id": "merge-" + secrets.token_hex(16), "created_at": now, "expires_at": now + 300,
                     "operation_created_at": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "manuscript": {"digest": self._manuscript, "source_verified": False}, "preview": preview,
                     "acceptance_available": False, "authorization_verified": False}
            prepared = canonical_bytes({**value, "digest": digest(value)})
            self._clear()
            self._prepared = prepared
            return decode(prepared)

    def get_preview(self):
        with self._lock:
            self._expire()
            return decode(self._prepared) if self._prepared else None

    def get_review(self):
        with self._lock:
            self._expire()
            return decode(self._review) if self._review else None

    def _current(self):
        now = self._expire()
        if not self._prepared:
            raise ContractError("inspect a current exact merge preview first")
        prepared = decode(self._prepared)
        preview = self._service.preview_merge(prepared["preview"]["selection"]["selected"], episode_id=self._episode)
        if preview != prepared["preview"] or self._manuscript != prepared["manuscript"]["digest"]:
            self._clear()
            raise ContractError("merge source changed; inspect the new scope")
        return now, prepared

    def finish(self, preview_digest, *, disposition, answers):
        """Seal the exact owned operation; no caller graph, Judgment or receipt."""
        with self._lock:
            _, prepared = self._current()
            if preview_digest != prepared["digest"]:
                raise ContractError("the exact current merge preview is required")
            if type(answers) is not list:
                raise ContractError("explicit bounded explanation answers required")
            preview = prepared["preview"]
            command = {"schema_version": 3, "id": prepared["operation_id"], "project_id": preview["project_id"],
                       "episode_id": self._episode, "created_at": prepared["operation_created_at"],
                       "operation_type": "apply-selected-merge", "expected_heads": dict(self._history.heads),
                       "evidence_watermark": self._history.watermark,
                       "payload": {"selected_ids": preview["selection"]["selected"],
                           "judgment": preview["provenance"]["judgment"], "disposition": disposition, "answers": answers}}
            sealed = self._history.prepare_merge_review(command, manuscript_digest=self._manuscript,
                session_nonce=self._nonce, sealed_at=prepared["created_at"], expires_at=prepared["expires_at"])
            candidate = acceptance_candidate(sealed, decision="accept")
            value = {"schema": "claimbranch.paper-merge-review/v1", "preview_digest": prepared["digest"],
                     "command": command, "sealed_review": decode(sealed.payload), "sealed_digest": sealed.digest,
                     "expires_at": sealed.context.expires_at,
                     "consequences_if_accepted": {"debts": [asdict(item) for item in candidate.debts]},
                     "authority": "unaccepted-review", "acceptance_available": False, "authorization_verified": False}
            reviewed = canonical_bytes({**value, "digest": digest(value)})
            self._review, self._command, self._sealed = reviewed, canonical_bytes(command), sealed
            return decode(reviewed)

    def candidate(self, review_digest):
        """Calculate (unverified history, obligations), retaining the owned source.

        This is not a submit/approve API or a storage operation. A future trusted
        gateway must independently reload and verify the exact native receipt.
        """
        with self._lock:
            now, _ = self._current()
            if not self._review or decode(self._review)["digest"] != review_digest:
                raise ContractError("the exact current completed merge review is required")
            return self._history.append_reviewed_merge(decode(self._command), self._sealed,
                manuscript_digest=self._manuscript, now=now)

    def not_now(self):
        with self._lock:
            self._clear()

    def update_source(self, history, *, manuscript_digest):
        with self._lock:
            digest_text(manuscript_digest)
            if (not isinstance(history, ResearchHistory) or history.seed != self._history.seed
                    or history.commands[:len(self._history.commands)] != self._history.commands):
                raise ContractError("merge refresh requires an append-only extension of the same history")
            service = PaperService(history)
            service.query("main", episode_id=self._episode)
            if history != self._history or manuscript_digest != self._manuscript:
                self._clear()
            self._history, self._service, self._manuscript = history, service, manuscript_digest
