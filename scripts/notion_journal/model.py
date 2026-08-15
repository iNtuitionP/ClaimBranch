"""Validated, deterministic data primitives for the coding journal."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import PurePosixPath
import re
from typing import Any

from . import SCHEMA_VERSION


ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|tmp)/)")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|token|password|secret|authorization)\s*[:=]\s*\S+"
)
BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:/")
_SECRET_BASENAME = re.compile(
    r"(?i)(?:^\.env(?:\..*)?$|^id_rsa(?:\..*)?$|\.pem$|token|secret)"
)
_ALLOWED_PATH_STATES = frozenset({"tracked", "untracked", "deleted"})
_ALLOWED_CHANGE_TYPES = frozenset(
    {"feature", "fix", "docs", "test", "refactor", "tooling", "research"}
)
_ALLOWED_TASK_STATUSES = frozenset({"Completed", "Blocked"})
_ALLOWED_AI_CONTRIBUTIONS = frozenset({"AI-assisted", "Human-only"})
_ALLOWED_VERIFICATION_OUTCOMES = frozenset({"Passed", "Failed", "Not run"})
_ALLOWED_VERIFICATION_STATUSES = frozenset(
    {"Passed", "Failed", "Partial", "Not run"}
)


class JournalError(Exception):
    """Base error for safe, user-actionable journal failures."""


class ValidationError(JournalError):
    """Raised when data would violate the journal's privacy contract."""


class GitStateError(JournalError):
    """Raised when a repository snapshot cannot be captured safely."""


def _contains_unsafe_codepoint(value: str) -> bool:
    return any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in value)


def normalize_repository_path(value: str) -> str:
    """Return a safe, repository-relative, slash-normalized path."""

    if not isinstance(value, str) or not value:
        raise ValidationError("repository path must be a non-empty string")
    normalized = value.replace("\\", "/")
    if len(normalized) > 512 or _contains_unsafe_codepoint(normalized):
        raise ValidationError("repository path contains unsafe characters")
    if normalized.startswith("/") or _WINDOWS_DRIVE.match(normalized):
        raise ValidationError("repository path must be relative")

    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValidationError("repository path must not traverse directories")
    lowered = tuple(part.casefold() for part in parts)
    if lowered[0] in {".git", ".vscode"}:
        raise ValidationError("repository path is excluded")
    if any(_SECRET_BASENAME.search(part) for part in parts):
        raise ValidationError("repository path resembles secret-bearing data")
    return "/".join(parts)


def sanitize_agent_text(value: str, *, field: str) -> str:
    """Validate agent-authored prose without silently changing its meaning."""

    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if _contains_unsafe_codepoint(value):
        raise ValidationError(f"{field} contains control characters")
    if ABSOLUTE_PATH.search(value) or SECRET_ASSIGNMENT.search(value) or BEARER.search(value):
        raise ValidationError(f"{field} contains private or secret-like text")
    return value.strip()


def canonical_json(value: object) -> bytes:
    """Serialize an object as stable UTF-8 JSON with no incidental whitespace."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class PathState:
    path: str
    state: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", normalize_repository_path(self.path))
        if self.state not in _ALLOWED_PATH_STATES:
            raise ValidationError("path state is not supported")
        if not isinstance(self.content_sha256, str) or not _SHA256.fullmatch(
            self.content_sha256
        ):
            raise ValidationError("content digest must be lowercase SHA-256")


@dataclass(frozen=True)
class Snapshot:
    repository: str
    branch: str
    head: str
    paths: tuple[PathState, ...]
    digest: str


@dataclass(frozen=True)
class SnapshotDelta:
    paths: tuple[str, ...]
    start_head: str
    end_head: str
    start_digest: str
    end_digest: str
    commit_stat: str
    worktree_stat: str
    includes_pre_session_edits: bool


@dataclass(frozen=True)
class VerificationItem:
    command: str
    outcome: str

    def __post_init__(self) -> None:
        command = sanitize_agent_text(self.command, field="verification command")
        if not command or len(command) > 300:
            raise ValidationError("verification command length is invalid")
        if self.outcome not in _ALLOWED_VERIFICATION_OUTCOMES:
            raise ValidationError("verification outcome is not supported")
        object.__setattr__(self, "command", command)


@dataclass(frozen=True)
class JournalDraft:
    title: str
    purpose: str
    outcome: str
    key_decisions: tuple[str, ...]
    verification: tuple[VerificationItem, ...]
    risks: tuple[str, ...]
    next_safe_action: str
    task_status: str
    change_types: tuple[str, ...]
    ai_contribution: str
    verification_status: str

    def __post_init__(self) -> None:
        if not isinstance(self.key_decisions, tuple):
            raise ValidationError("key decisions must be a tuple")
        if not isinstance(self.verification, tuple):
            raise ValidationError("verification items must be a tuple")
        if not isinstance(self.risks, tuple):
            raise ValidationError("risks must be a tuple")
        if not isinstance(self.change_types, tuple):
            raise ValidationError("change types must be a tuple")
        title = _bounded_text(self.title, field="title", limit=120, required=True)
        purpose = _bounded_text(self.purpose, field="purpose", limit=1000, required=True)
        outcome = _bounded_text(self.outcome, field="outcome", limit=1000, required=True)
        next_action = _bounded_text(
            self.next_safe_action, field="next safe action", limit=1000, required=True
        )
        decisions = _bounded_text_items(
            self.key_decisions, field="key decision", count=10, limit=500
        )
        risks = _bounded_text_items(self.risks, field="risk", count=10, limit=500)
        verification = tuple(self.verification)
        if len(verification) > 20 or any(
            not isinstance(item, VerificationItem) for item in verification
        ):
            raise ValidationError("verification items are invalid")
        if self.task_status not in _ALLOWED_TASK_STATUSES:
            raise ValidationError("task status is not supported")
        change_types = tuple(sorted(set(self.change_types)))
        if not change_types or any(item not in _ALLOWED_CHANGE_TYPES for item in change_types):
            raise ValidationError("change types are invalid")
        if self.ai_contribution not in _ALLOWED_AI_CONTRIBUTIONS:
            raise ValidationError("AI contribution is not supported")
        if self.verification_status not in _ALLOWED_VERIFICATION_STATUSES:
            raise ValidationError("verification status is not supported")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "key_decisions", decisions)
        object.__setattr__(self, "verification", verification)
        object.__setattr__(self, "risks", risks)
        object.__setattr__(self, "next_safe_action", next_action)
        object.__setattr__(self, "change_types", change_types)
        if len(canonical_json(asdict(self))) > 6000:
            raise ValidationError("journal draft exceeds the safe size limit")


def _bounded_text(value: str, *, field: str, limit: int, required: bool) -> str:
    normalized = sanitize_agent_text(value, field=field)
    if required and not normalized:
        raise ValidationError(f"{field} must not be empty")
    if len(normalized) > limit:
        raise ValidationError(f"{field} exceeds its size limit")
    return normalized


def _bounded_text_items(
    values: tuple[str, ...], *, field: str, count: int, limit: int
) -> tuple[str, ...]:
    items = tuple(values)
    if len(items) > count:
        raise ValidationError(f"{field} list exceeds its item limit")
    return tuple(
        _bounded_text(value, field=field, limit=limit, required=True) for value in items
    )


def dataclass_dict(value: Any) -> dict[str, Any]:
    """Return a standard dictionary for a validated journal dataclass."""

    return asdict(value)


__all__ = [
    "SCHEMA_VERSION",
    "GitStateError",
    "JournalDraft",
    "JournalError",
    "PathState",
    "Snapshot",
    "SnapshotDelta",
    "ValidationError",
    "VerificationItem",
    "canonical_json",
    "dataclass_dict",
    "normalize_repository_path",
    "sanitize_agent_text",
]
