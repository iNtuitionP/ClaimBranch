"""Versioned, atomic local outbox storage for the Notion coding journal."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import os
import re
import threading
import time
from typing import Any, Callable, Mapping, TypeVar
from urllib.parse import urlparse
from uuid import uuid4

from . import SCHEMA_VERSION
from .model import (
    JournalDraft,
    JournalError,
    PathState,
    Snapshot,
    SnapshotDelta,
    ValidationError,
    VerificationItem,
    canonical_json,
    normalize_repository_path,
)


_SEOUL = timezone(timedelta(hours=9))
_JOURNAL_KEY = re.compile(r"cbj-v1-[0-9a-f]{24}\Z")
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_HEAD = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_TOOL_NAME = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_ISO_SEOUL = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00\Z")
_LOCKS_GUARD = threading.Lock()
_ROOT_LOCKS: dict[str, threading.RLock] = {}
_T = TypeVar("_T")


def _root_lock(root: Path) -> threading.RLock:
    key = str(root.resolve()).casefold()
    with _LOCKS_GUARD:
        return _ROOT_LOCKS.setdefault(key, threading.RLock())


def _printable(value: str, *, field: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise JournalError(f"{field} is missing or too long")
    if not value.isprintable() or any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise JournalError(f"{field} contains unsafe characters")
    return value


def _notion_url(value: str, *, field: str) -> str:
    value = _printable(value, field=field, limit=2000)
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").casefold()
    allowed = any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ("notion.so", "notion.site")
    )
    if parsed.scheme != "https" or not allowed:
        raise JournalError(f"{field} must be an HTTPS Notion URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise JournalError(f"{field} contains unsupported URL components")
    return value


def _journal_key(value: str) -> str:
    if not isinstance(value, str) or not _JOURNAL_KEY.fullmatch(value):
        raise JournalError("journal key is invalid")
    return value


def _schema_version(value: object) -> int:
    if type(value) is not int or value != SCHEMA_VERSION:
        raise JournalError("state schema version is unsupported")
    return value


def _mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise JournalError(f"{field} must be a JSON object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], *, field: str) -> None:
    if set(value) != expected:
        raise JournalError(f"{field} has unexpected fields")


def _sequence(value: object, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise JournalError(f"{field} must be a JSON array")
    return value


def state_root(env: Mapping[str, str]) -> Path:
    """Locate private user state outside the repository on Windows."""

    local_app_data = env.get("LOCALAPPDATA")
    if not local_app_data:
        raise JournalError("LOCALAPPDATA is required for the Notion journal")
    return Path(local_app_data) / "ClaimBranch" / "NotionJournal"


def iso_seoul(value: datetime) -> str:
    """Render an aware datetime with a deterministic fixed Seoul offset."""

    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise JournalError("journal timestamps must be timezone-aware")
    return value.astimezone(_SEOUL).replace(microsecond=0).isoformat(timespec="seconds")


def make_journal_key(
    repository: str, session_id: str, start_digest: str, end_digest: str
) -> str:
    repository = _printable(repository, field="repository", limit=128)
    session_id = _printable(session_id, field="session ID")
    if not _HEX_64.fullmatch(start_digest) or not _HEX_64.fullmatch(end_digest):
        raise JournalError("snapshot digest is invalid")
    material = (
        f"v{SCHEMA_VERSION}\0{repository}\0{session_id}\0{start_digest}\0{end_digest}"
    )
    return "cbj-v1-" + sha256(material.encode("utf-8")).hexdigest()[:24]


def make_decision_key(repository: str, snapshot_digest: str, draft_digest: str) -> str:
    repository = _printable(repository, field="repository", limit=128)
    if not _HEX_64.fullmatch(snapshot_digest) or not _HEX_64.fullmatch(draft_digest):
        raise JournalError("decision digest is invalid")
    material = (
        f"v{SCHEMA_VERSION}\0{repository}\0explicit-decision\0"
        f"{snapshot_digest}\0{draft_digest}"
    )
    return "cbj-v1-" + sha256(material.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class JournalConfig:
    schema_version: int
    workspace_id: str
    workspace_name: str
    journal_page_id: str
    database_id: str
    data_source_id: str
    database_url: str
    read_tool_name: str
    query_tool_name: str
    create_tool_name: str
    update_tool_name: str

    def __post_init__(self) -> None:
        _schema_version(self.schema_version)
        for field in (
            "workspace_id",
            "workspace_name",
            "journal_page_id",
            "database_id",
            "data_source_id",
        ):
            _printable(getattr(self, field), field=field)
        _notion_url(self.database_url, field="database URL")
        for field in (
            "read_tool_name",
            "query_tool_name",
            "create_tool_name",
            "update_tool_name",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not _TOOL_NAME.fullmatch(value):
                raise JournalError(f"{field} is invalid")


@dataclass(frozen=True)
class SessionState:
    schema_version: int
    session_id: str
    baseline: Snapshot
    cursor: Snapshot
    updated_at: str


@dataclass(frozen=True)
class PendingEnvelope:
    schema_version: int
    journal_key: str
    session_id: str
    repository: str
    recorded_at: str
    sync_state: str
    trigger: str
    start_snapshot: Snapshot
    end_snapshot: Snapshot
    delta: SnapshotDelta
    draft: JournalDraft | None
    page_id: str | None
    page_url: str | None
    synced_at: str | None

    def to_public_dict(self) -> dict[str, Any]:
        visible_paths = self.delta.paths[:200]
        return {
            "schema_version": self.schema_version,
            "journal_key": self.journal_key,
            "recorded_at": self.recorded_at,
            "sync_state": self.sync_state,
            "trigger": self.trigger,
            "repository": self.repository,
            "branch": self.end_snapshot.branch,
            "start_head": self.delta.start_head,
            "end_head": self.delta.end_head,
            "worktree_digest": self.delta.end_digest,
            "changed_paths": list(visible_paths),
            "omitted_path_count": len(self.delta.paths) - len(visible_paths),
            "commit_stat": self.delta.commit_stat,
            "worktree_stat": self.delta.worktree_stat,
            "includes_pre_session_edits": self.delta.includes_pre_session_edits,
            "draft": asdict(self.draft) if self.draft is not None else None,
        }

    def to_storage_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Receipt:
    schema_version: int
    journal_key: str
    page_id: str
    page_url: str
    synced_at: str


def _validate_timestamp(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _ISO_SEOUL.fullmatch(value):
        raise JournalError(f"{field} is not a canonical Seoul timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise JournalError(f"{field} is invalid") from error
    if parsed.utcoffset() != timedelta(hours=9):
        raise JournalError(f"{field} has an unexpected timezone")
    return value


def _validate_snapshot(value: Snapshot) -> Snapshot:
    if not isinstance(value, Snapshot):
        raise JournalError("snapshot has an invalid type")
    repository = _printable(value.repository, field="repository", limit=128)
    if "/" in repository or "\\" in repository:
        raise JournalError("repository must be a basename")
    _printable(value.branch, field="branch")
    if not _GIT_HEAD.fullmatch(value.head):
        raise JournalError("Git HEAD is invalid")
    if not _HEX_64.fullmatch(value.digest):
        raise JournalError("snapshot digest is invalid")
    if not isinstance(value.paths, tuple) or not all(
        isinstance(item, PathState) for item in value.paths
    ):
        raise JournalError("snapshot paths are invalid")
    normalized = tuple(item.path for item in value.paths)
    if normalized != tuple(sorted(set(normalized))):
        raise JournalError("snapshot paths must be unique and sorted")
    return value


def _validate_stat(value: str, *, field: str) -> str:
    if not isinstance(value, str) or len(value) > 4000:
        raise JournalError(f"{field} is too long")
    if "\r" in value or "\t" in value or any(
        (ord(character) < 32 and character != "\n")
        or 0xD800 <= ord(character) <= 0xDFFF
        for character in value
    ):
        raise JournalError(f"{field} contains unsafe characters")
    return value


def _validate_delta(value: SnapshotDelta) -> SnapshotDelta:
    if not isinstance(value, SnapshotDelta):
        raise JournalError("snapshot delta has an invalid type")
    try:
        paths = tuple(normalize_repository_path(path) for path in value.paths)
    except (TypeError, ValidationError) as error:
        raise JournalError("snapshot delta paths are invalid") from error
    if paths != tuple(sorted(set(paths))):
        raise JournalError("snapshot delta paths must be unique and sorted")
    if not _GIT_HEAD.fullmatch(value.start_head) or not _GIT_HEAD.fullmatch(value.end_head):
        raise JournalError("snapshot delta HEAD is invalid")
    if not _HEX_64.fullmatch(value.start_digest) or not _HEX_64.fullmatch(value.end_digest):
        raise JournalError("snapshot delta digest is invalid")
    _validate_stat(value.commit_stat, field="commit stat")
    _validate_stat(value.worktree_stat, field="worktree stat")
    if type(value.includes_pre_session_edits) is not bool:
        raise JournalError("pre-session edit flag is invalid")
    return value


def _validate_session(value: SessionState) -> SessionState:
    if not isinstance(value, SessionState):
        raise JournalError("session state has an invalid type")
    _schema_version(value.schema_version)
    _printable(value.session_id, field="session ID")
    _validate_snapshot(value.baseline)
    _validate_snapshot(value.cursor)
    if value.baseline.repository != value.cursor.repository:
        raise JournalError("session snapshots name different repositories")
    _validate_timestamp(value.updated_at, field="session update time")
    return value


def _validate_envelope(value: PendingEnvelope) -> PendingEnvelope:
    if not isinstance(value, PendingEnvelope):
        raise JournalError("pending envelope has an invalid type")
    _schema_version(value.schema_version)
    _journal_key(value.journal_key)
    _printable(value.session_id, field="session ID")
    _printable(value.repository, field="repository", limit=128)
    _validate_timestamp(value.recorded_at, field="recorded time")
    if value.sync_state not in {"pending", "synced"}:
        raise JournalError("sync state is invalid")
    if value.trigger not in {"material-change", "explicit-decision"}:
        raise JournalError("journal trigger is invalid")
    _validate_snapshot(value.start_snapshot)
    _validate_snapshot(value.end_snapshot)
    _validate_delta(value.delta)
    if not (
        value.repository
        == value.start_snapshot.repository
        == value.end_snapshot.repository
    ):
        raise JournalError("envelope repositories do not match")
    if (
        value.delta.start_digest != value.start_snapshot.digest
        or value.delta.end_digest != value.end_snapshot.digest
        or value.delta.start_head != value.start_snapshot.head
        or value.delta.end_head != value.end_snapshot.head
    ):
        raise JournalError("envelope delta does not match its snapshots")
    if value.draft is not None and not isinstance(value.draft, JournalDraft):
        raise JournalError("journal draft has an invalid type")
    if value.trigger == "material-change" and not value.delta.paths:
        raise JournalError("material-change envelope has no changed paths")
    if value.trigger == "explicit-decision" and (
        value.delta.paths
        or value.start_snapshot != value.end_snapshot
        or value.draft is None
    ):
        raise JournalError("explicit-decision envelope is inconsistent")
    if value.sync_state == "pending":
        if any(item is not None for item in (value.page_id, value.page_url, value.synced_at)):
            raise JournalError("pending envelope contains receipt fields")
    else:
        _printable(value.page_id, field="page ID")
        _notion_url(value.page_url, field="page URL")
        _validate_timestamp(value.synced_at, field="sync time")
    return value


def _validate_receipt(value: Receipt) -> Receipt:
    if not isinstance(value, Receipt):
        raise JournalError("receipt has an invalid type")
    _schema_version(value.schema_version)
    _journal_key(value.journal_key)
    _printable(value.page_id, field="page ID")
    _notion_url(value.page_url, field="page URL")
    _validate_timestamp(value.synced_at, field="sync time")
    return value


def _path_state_from_dict(value: object) -> PathState:
    item = _mapping(value, field="path state")
    _exact_keys(item, {"path", "state", "content_sha256"}, field="path state")
    try:
        return PathState(item["path"], item["state"], item["content_sha256"])
    except (KeyError, TypeError, ValidationError) as error:
        raise JournalError("path state is invalid") from error


def _snapshot_from_dict(value: object) -> Snapshot:
    item = _mapping(value, field="snapshot")
    _exact_keys(item, {"repository", "branch", "head", "paths", "digest"}, field="snapshot")
    paths = tuple(_path_state_from_dict(path) for path in _sequence(item["paths"], field="snapshot paths"))
    try:
        snapshot = Snapshot(
            item["repository"], item["branch"], item["head"], paths, item["digest"]
        )
    except (KeyError, TypeError) as error:
        raise JournalError("snapshot is invalid") from error
    return _validate_snapshot(snapshot)


def _delta_from_dict(value: object) -> SnapshotDelta:
    item = _mapping(value, field="snapshot delta")
    keys = {
        "paths",
        "start_head",
        "end_head",
        "start_digest",
        "end_digest",
        "commit_stat",
        "worktree_stat",
        "includes_pre_session_edits",
    }
    _exact_keys(item, keys, field="snapshot delta")
    try:
        result = SnapshotDelta(
            paths=tuple(_sequence(item["paths"], field="delta paths")),
            start_head=item["start_head"],
            end_head=item["end_head"],
            start_digest=item["start_digest"],
            end_digest=item["end_digest"],
            commit_stat=item["commit_stat"],
            worktree_stat=item["worktree_stat"],
            includes_pre_session_edits=item["includes_pre_session_edits"],
        )
    except (KeyError, TypeError) as error:
        raise JournalError("snapshot delta is invalid") from error
    return _validate_delta(result)


def _verification_from_dict(value: object) -> VerificationItem:
    item = _mapping(value, field="verification item")
    _exact_keys(item, {"command", "outcome"}, field="verification item")
    try:
        return VerificationItem(item["command"], item["outcome"])
    except (KeyError, TypeError, ValidationError) as error:
        raise JournalError("verification item is invalid") from error


def _draft_from_dict(value: object) -> JournalDraft:
    item = _mapping(value, field="journal draft")
    keys = {
        "title",
        "purpose",
        "outcome",
        "key_decisions",
        "verification",
        "risks",
        "next_safe_action",
        "task_status",
        "change_types",
        "ai_contribution",
        "verification_status",
    }
    _exact_keys(item, keys, field="journal draft")
    try:
        return JournalDraft(
            title=item["title"],
            purpose=item["purpose"],
            outcome=item["outcome"],
            key_decisions=tuple(_sequence(item["key_decisions"], field="key decisions")),
            verification=tuple(
                _verification_from_dict(entry)
                for entry in _sequence(item["verification"], field="verification")
            ),
            risks=tuple(_sequence(item["risks"], field="risks")),
            next_safe_action=item["next_safe_action"],
            task_status=item["task_status"],
            change_types=tuple(_sequence(item["change_types"], field="change types")),
            ai_contribution=item["ai_contribution"],
            verification_status=item["verification_status"],
        )
    except (KeyError, TypeError, ValidationError) as error:
        raise JournalError("journal draft is invalid") from error


def _config_from_dict(value: object) -> JournalConfig:
    item = _mapping(value, field="configuration")
    _schema_version(item.get("schema_version"))
    keys = {field.name for field in JournalConfig.__dataclass_fields__.values()}
    _exact_keys(item, keys, field="configuration")
    try:
        return JournalConfig(**item)
    except (TypeError, JournalError) as error:
        raise JournalError("configuration is invalid") from error


def _session_from_dict(value: object) -> SessionState:
    item = _mapping(value, field="session")
    _schema_version(item.get("schema_version"))
    _exact_keys(
        item,
        {"schema_version", "session_id", "baseline", "cursor", "updated_at"},
        field="session",
    )
    try:
        result = SessionState(
            schema_version=item["schema_version"],
            session_id=item["session_id"],
            baseline=_snapshot_from_dict(item["baseline"]),
            cursor=_snapshot_from_dict(item["cursor"]),
            updated_at=item["updated_at"],
        )
    except (KeyError, TypeError) as error:
        raise JournalError("session is invalid") from error
    return _validate_session(result)


def _envelope_from_dict(value: object) -> PendingEnvelope:
    item = _mapping(value, field="pending envelope")
    _schema_version(item.get("schema_version"))
    keys = {field.name for field in PendingEnvelope.__dataclass_fields__.values()}
    _exact_keys(item, keys, field="pending envelope")
    draft_value = item.get("draft")
    try:
        result = PendingEnvelope(
            schema_version=item["schema_version"],
            journal_key=item["journal_key"],
            session_id=item["session_id"],
            repository=item["repository"],
            recorded_at=item["recorded_at"],
            sync_state=item["sync_state"],
            trigger=item["trigger"],
            start_snapshot=_snapshot_from_dict(item["start_snapshot"]),
            end_snapshot=_snapshot_from_dict(item["end_snapshot"]),
            delta=_delta_from_dict(item["delta"]),
            draft=None if draft_value is None else _draft_from_dict(draft_value),
            page_id=item["page_id"],
            page_url=item["page_url"],
            synced_at=item["synced_at"],
        )
    except (KeyError, TypeError) as error:
        raise JournalError("pending envelope is invalid") from error
    return _validate_envelope(result)


def _receipt_from_dict(value: object) -> Receipt:
    item = _mapping(value, field="receipt")
    _schema_version(item.get("schema_version"))
    keys = {field.name for field in Receipt.__dataclass_fields__.values()}
    _exact_keys(item, keys, field="receipt")
    try:
        result = Receipt(**item)
    except (TypeError, JournalError) as error:
        raise JournalError("receipt is invalid") from error
    return _validate_receipt(result)


class JournalStore:
    """Own local versioned state and monotonic pending/receipt transitions."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.sessions = self.root / "sessions"
        self.pending = self.root / "pending"
        self.receipts = self.root / "receipts"
        self.quarantine = self.root / "quarantine"
        for directory in (self.root, self.sessions, self.pending, self.receipts, self.quarantine):
            directory.mkdir(parents=True, exist_ok=True)
        self._lock = _root_lock(self.root)

    def _session_path(self, session_id: str) -> Path:
        session_id = _printable(session_id, field="session ID")
        filename = sha256(session_id.encode("utf-8")).hexdigest()[:32] + ".json"
        return self.sessions / filename

    def _pending_path(self, journal_key: str) -> Path:
        return self.pending / f"{_journal_key(journal_key)}.json"

    def _receipt_path(self, journal_key: str) -> Path:
        return self.receipts / f"{_journal_key(journal_key)}.json"

    def _replace_bytes(self, path: Path, payload: bytes) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except OSError as error:
            raise JournalError("unable to atomically replace local journal state") from error
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _write_exclusive(self, path: Path, payload: bytes) -> bool:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return False
        except OSError as error:
            raise JournalError("unable to create local journal state") from error
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            try:
                path.unlink()
            except OSError:
                pass
            raise JournalError("unable to persist local journal state") from error
        return True

    def _quarantine(self, path: Path) -> None:
        if not path.exists():
            return
        target = self.quarantine / f"{path.stem}-{uuid4().hex}.json"
        try:
            os.replace(path, target)
        except OSError as error:
            raise JournalError("invalid journal state could not be quarantined") from error

    def _read_document(self, path: Path, decoder: Callable[[object], _T]) -> _T:
        if not path.is_file():
            raise JournalError("local journal state was not found")
        last_error: Exception | None = None
        for attempt in range(6):
            try:
                raw = path.read_bytes()
                value = json.loads(raw)
                return decoder(value)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, JournalError) as error:
                last_error = error
                if attempt < 5:
                    time.sleep(0.01)
                    continue
        self._quarantine(path)
        raise JournalError("local journal state was invalid and quarantined") from last_error

    def write_config(self, config: JournalConfig) -> JournalConfig:
        if not isinstance(config, JournalConfig):
            raise JournalError("configuration has an invalid type")
        validated = _config_from_dict(asdict(config))
        with self._lock:
            path = self.root / "config.json"
            if path.exists():
                self._read_document(path, _config_from_dict)
            self._replace_bytes(path, canonical_json(asdict(validated)))
        return validated

    def read_config(self) -> JournalConfig:
        with self._lock:
            return self._read_document(self.root / "config.json", _config_from_dict)

    def create_session(
        self, session_id: str, snapshot: Snapshot, now: datetime
    ) -> SessionState:
        candidate = _validate_session(
            SessionState(
                schema_version=SCHEMA_VERSION,
                session_id=_printable(session_id, field="session ID"),
                baseline=_validate_snapshot(snapshot),
                cursor=snapshot,
                updated_at=iso_seoul(now),
            )
        )
        path = self._session_path(session_id)
        with self._lock:
            if self._write_exclusive(path, canonical_json(asdict(candidate))):
                return candidate
            return self._read_document(path, _session_from_dict)

    def read_session(self, session_id: str) -> SessionState:
        with self._lock:
            session = self._read_document(self._session_path(session_id), _session_from_dict)
            if session.session_id != session_id:
                raise JournalError("session hash collision detected")
            return session

    def _replace_session(self, session: SessionState) -> None:
        validated = _validate_session(session)
        self._replace_bytes(self._session_path(session.session_id), canonical_json(asdict(validated)))

    def _all_envelopes(self) -> tuple[PendingEnvelope, ...]:
        return tuple(
            self._read_document(path, _envelope_from_dict)
            for path in sorted(self.pending.glob("*.json"), key=lambda item: item.name)
        )

    def recover_cursor(self, session_id: str) -> SessionState:
        with self._lock:
            session = self.read_session(session_id)
            relevant = tuple(
                envelope
                for envelope in self._all_envelopes()
                if envelope.trigger == "material-change" and envelope.session_id == session_id
            )
            by_start: dict[str, list[PendingEnvelope]] = {}
            for envelope in relevant:
                by_start.setdefault(envelope.start_snapshot.digest, []).append(envelope)
            if any(len(envelopes) != 1 for envelopes in by_start.values()):
                raise JournalError("pending cursor history is forked")

            cursor = session.cursor
            seen: set[str] = set()
            while cursor.digest in by_start:
                if cursor.digest in seen:
                    raise JournalError("pending cursor history contains a cycle")
                seen.add(cursor.digest)
                envelope = by_start[cursor.digest][0]
                if envelope.start_snapshot != cursor:
                    raise JournalError("pending cursor snapshot does not match session state")
                cursor = envelope.end_snapshot
            if cursor == session.cursor:
                return session
            recovered = replace(session, cursor=cursor, updated_at=iso_seoul(datetime.now(_SEOUL)))
            self._replace_session(recovered)
            return recovered

    def _write_pending_if_absent(self, envelope: PendingEnvelope) -> PendingEnvelope:
        validated = _validate_envelope(envelope)
        path = self._pending_path(validated.journal_key)
        payload = canonical_json(validated.to_storage_dict())
        with self._lock:
            if self._write_exclusive(path, payload):
                return validated
            existing = self._read_document(path, _envelope_from_dict)
            if canonical_json(existing.to_storage_dict()) != payload:
                raise JournalError("journal key conflicts with an existing envelope")
            return existing

    def capture_pending(
        self,
        session_id: str,
        end_snapshot: Snapshot,
        delta: SnapshotDelta,
        now: datetime,
    ) -> PendingEnvelope:
        with self._lock:
            session = self.recover_cursor(session_id)
            _validate_snapshot(end_snapshot)
            _validate_delta(delta)
            if delta.start_digest != session.cursor.digest:
                raise JournalError("delta does not start at the current capture cursor")
            if delta.end_digest != end_snapshot.digest:
                raise JournalError("delta does not end at the supplied snapshot")
            journal_key = make_journal_key(
                end_snapshot.repository,
                session_id,
                session.cursor.digest,
                end_snapshot.digest,
            )
            envelope = PendingEnvelope(
                schema_version=SCHEMA_VERSION,
                journal_key=journal_key,
                session_id=session_id,
                repository=end_snapshot.repository,
                recorded_at=iso_seoul(now),
                sync_state="pending",
                trigger="material-change",
                start_snapshot=session.cursor,
                end_snapshot=end_snapshot,
                delta=delta,
                draft=None,
                page_id=None,
                page_url=None,
                synced_at=None,
            )
            envelope = self._write_pending_if_absent(envelope)
            self._replace_session(
                replace(session, cursor=end_snapshot, updated_at=iso_seoul(now))
            )
            return envelope

    def read_envelope(self, journal_key: str) -> PendingEnvelope:
        with self._lock:
            envelope = self._read_document(
                self._pending_path(journal_key), _envelope_from_dict
            )
            if envelope.journal_key != journal_key:
                raise JournalError("pending envelope key does not match its filename")
            return envelope

    def attach_draft(self, journal_key: str, draft: JournalDraft) -> PendingEnvelope:
        if not isinstance(draft, JournalDraft):
            raise JournalError("journal draft has an invalid type")
        with self._lock:
            envelope = self.read_envelope(journal_key)
            if envelope.draft is not None:
                if canonical_json(asdict(envelope.draft)) == canonical_json(asdict(draft)):
                    return envelope
                raise JournalError("journal draft is already attached with different content")
            if envelope.sync_state != "pending":
                raise JournalError("cannot attach a draft to a synced envelope")
            updated = replace(envelope, draft=draft)
            _validate_envelope(updated)
            self._replace_bytes(
                self._pending_path(journal_key), canonical_json(updated.to_storage_dict())
            )
            return updated

    def capture_explicit_decision(
        self, snapshot: Snapshot, draft: JournalDraft, now: datetime
    ) -> PendingEnvelope:
        _validate_snapshot(snapshot)
        if not isinstance(draft, JournalDraft):
            raise JournalError("journal draft has an invalid type")
        draft_digest = sha256(canonical_json(asdict(draft))).hexdigest()
        key = make_decision_key(snapshot.repository, snapshot.digest, draft_digest)
        empty_delta = SnapshotDelta(
            paths=(),
            start_head=snapshot.head,
            end_head=snapshot.head,
            start_digest=snapshot.digest,
            end_digest=snapshot.digest,
            commit_stat="",
            worktree_stat="",
            includes_pre_session_edits=False,
        )
        candidate = PendingEnvelope(
            schema_version=SCHEMA_VERSION,
            journal_key=key,
            session_id="explicit-decision",
            repository=snapshot.repository,
            recorded_at=iso_seoul(now),
            sync_state="pending",
            trigger="explicit-decision",
            start_snapshot=snapshot,
            end_snapshot=snapshot,
            delta=empty_delta,
            draft=draft,
            page_id=None,
            page_url=None,
            synced_at=None,
        )
        with self._lock:
            path = self._pending_path(key)
            if path.exists():
                existing = self.read_envelope(key)
                if (
                    existing.trigger == candidate.trigger
                    and existing.start_snapshot == snapshot
                    and existing.end_snapshot == snapshot
                    and existing.delta == empty_delta
                    and existing.draft == draft
                ):
                    return existing
                raise JournalError("decision key conflicts with an existing envelope")
            return self._write_pending_if_absent(candidate)

    def record_receipt(
        self,
        journal_key: str,
        page_id: str,
        page_url: str,
        now: datetime,
    ) -> Receipt:
        with self._lock:
            envelope = self.read_envelope(journal_key)
            if envelope.draft is None:
                raise JournalError("a receipt requires an attached journal draft")
            candidate = _validate_receipt(
                Receipt(
                    schema_version=SCHEMA_VERSION,
                    journal_key=_journal_key(journal_key),
                    page_id=_printable(page_id, field="page ID"),
                    page_url=_notion_url(page_url, field="page URL"),
                    synced_at=iso_seoul(now),
                )
            )
            path = self._receipt_path(journal_key)
            payload = canonical_json(asdict(candidate))
            if self._write_exclusive(path, payload):
                receipt = candidate
            else:
                receipt = self._read_document(path, _receipt_from_dict)
                if receipt.page_id != page_id or receipt.page_url != page_url:
                    raise JournalError("journal receipt conflicts with an existing page")
            if envelope.sync_state == "pending":
                envelope = replace(
                    envelope,
                    sync_state="synced",
                    page_id=receipt.page_id,
                    page_url=receipt.page_url,
                    synced_at=receipt.synced_at,
                )
                _validate_envelope(envelope)
                self._replace_bytes(
                    self._pending_path(journal_key), canonical_json(envelope.to_storage_dict())
                )
            elif envelope.page_id != page_id or envelope.page_url != page_url:
                raise JournalError("synced envelope conflicts with the receipt")
            return receipt

    def list_pending(self) -> tuple[PendingEnvelope, ...]:
        with self._lock:
            return tuple(
                envelope for envelope in self._all_envelopes() if envelope.sync_state == "pending"
            )

    def list_receipts(self) -> tuple[Receipt, ...]:
        with self._lock:
            return tuple(
                self._read_document(path, _receipt_from_dict)
                for path in sorted(self.receipts.glob("*.json"), key=lambda item: item.name)
            )


__all__ = [
    "JournalConfig",
    "JournalStore",
    "PendingEnvelope",
    "Receipt",
    "SessionState",
    "iso_seoul",
    "make_decision_key",
    "make_journal_key",
    "state_root",
]
