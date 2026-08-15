"""Capture bounded Git metadata without persisting repository content."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

from .model import (
    GitStateError,
    PathState,
    Snapshot,
    SnapshotDelta,
    ValidationError,
    canonical_json,
    normalize_repository_path,
)


_DELETED_DIGEST = sha256(b"<deleted>").hexdigest()
_PATH_BATCH_SIZE = 32
_STAT_LIMIT = 4000


def _git(repo: Path, arguments: Sequence[str], *, allow_failure: bool = False) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=not allow_failure,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise GitStateError("unable to inspect Git repository safely") from error
    if allow_failure and completed.returncode:
        return b""
    return completed.stdout


def _decode_path(raw: bytes) -> str | None:
    value = raw.decode("utf-8", errors="surrogateescape")
    try:
        return normalize_repository_path(value)
    except ValidationError:
        return None


def _nul_paths(raw: bytes) -> tuple[str, ...]:
    paths = {
        path
        for item in raw.split(b"\0")
        if item and (path := _decode_path(item)) is not None
    }
    return tuple(sorted(paths))


def _batches(paths: Sequence[str]) -> Iterable[tuple[str, ...]]:
    for offset in range(0, len(paths), _PATH_BATCH_SIZE):
        yield tuple(paths[offset : offset + _PATH_BATCH_SIZE])


def _safe_content_target(repo: Path, relative: str) -> Path:
    target = repo.joinpath(*relative.split("/"))
    current = repo
    for part in relative.split("/")[:-1]:
        current = current / part
        if os.path.islink(current):
            raise GitStateError("refusing to follow a symlinked repository directory")
    return target


def content_sha256(path: Path) -> str:
    """Hash file bytes, or a symlink's own link text, in bounded chunks."""

    digest = sha256()
    if os.path.islink(path):
        digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        return digest.hexdigest()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise GitStateError("unable to hash an eligible repository path") from error
    return digest.hexdigest()


def capture_snapshot(repo: Path) -> Snapshot:
    """Capture HEAD plus content digests for eligible dirty paths."""

    repository_path = Path(repo).resolve()
    if not repository_path.is_dir():
        raise GitStateError("repository path is not a directory")

    head = _git(repository_path, ["rev-parse", "HEAD"]).decode("ascii").strip()
    branch_bytes = _git(
        repository_path,
        ["symbolic-ref", "--short", "-q", "HEAD"],
        allow_failure=True,
    )
    branch = branch_bytes.decode("utf-8", errors="surrogateescape").strip() or "(detached)"

    tracked = _nul_paths(
        _git(
            repository_path,
            ["diff", "--name-only", "-z", "--diff-filter=ACDMRTUXB", "HEAD", "--"],
        )
    )
    untracked = _nul_paths(
        _git(repository_path, ["ls-files", "--others", "--exclude-standard", "-z", "--"])
    )

    states: list[PathState] = []
    for relative in sorted(set(tracked) | set(untracked)):
        target = _safe_content_target(repository_path, relative)
        if relative in tracked and not os.path.lexists(target):
            states.append(PathState(relative, "deleted", _DELETED_DIGEST))
            continue
        state = "untracked" if relative in untracked else "tracked"
        states.append(PathState(relative, state, content_sha256(target)))

    repository = repository_path.name
    if not repository or any(ord(character) < 32 for character in repository):
        raise GitStateError("repository basename is unsafe")
    digest_input = {
        "repository": repository,
        "branch": branch,
        "head": head,
        "paths": [asdict(item) for item in states],
    }
    digest = sha256(canonical_json(digest_input)).hexdigest()
    return Snapshot(repository, branch, head, tuple(states), digest)


def _parse_numstat(raw: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        fields = record.split(b"\t", 2)
        if len(fields) != 3:
            continue
        additions, deletions, raw_path = fields
        path = _decode_path(raw_path)
        if path is None:
            continue
        if additions == b"-" or deletions == b"-":
            result[path] = "binary"
            continue
        try:
            added = int(additions.decode("ascii"))
            deleted = int(deletions.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            continue
        if added < 0 or deleted < 0:
            continue
        result[path] = f"+{added}/-{deleted}"
    return result


def _numstat(repo: Path, revision: str, paths: Sequence[str]) -> dict[str, str]:
    stats: dict[str, str] = {}
    for batch in _batches(paths):
        if not batch:
            continue
        raw = _git(
            repo,
            ["diff", "--numstat", "-z", "--no-renames", revision, "--", *batch],
        )
        stats.update(_parse_numstat(raw))
    return stats


def _render_stat(stats: dict[str, str]) -> str:
    lines = [f"{path}: {stats[path]}" for path in sorted(stats)]
    if not lines:
        return ""
    rendered: list[str] = []
    for index, line in enumerate(lines):
        candidate = "\n".join([*rendered, line])
        remaining = len(lines) - index - 1
        suffix = f"... {remaining} path(s) omitted" if remaining else ""
        projected = "\n".join(part for part in (candidate, suffix) if part)
        if len(projected) <= _STAT_LIMIT:
            rendered.append(line)
            continue
        break

    omitted = len(lines) - len(rendered)
    if omitted:
        suffix = f"... {omitted} path(s) omitted"
        while rendered and len("\n".join([*rendered, suffix])) > _STAT_LIMIT:
            rendered.pop()
            omitted += 1
            suffix = f"... {omitted} path(s) omitted"
        rendered.append(suffix)
    return "\n".join(rendered)


def compare_snapshots(repo: Path, start: Snapshot, end: Snapshot) -> SnapshotDelta:
    """Return paths whose safe metadata changed during the capture interval."""

    if start.repository != end.repository:
        raise GitStateError("snapshots belong to different repositories")
    repository_path = Path(repo).resolve()
    start_paths = {item.path: item for item in start.paths}
    end_paths = {item.path: item for item in end.paths}
    changed = {
        path
        for path in set(start_paths) | set(end_paths)
        if start_paths.get(path) != end_paths.get(path)
    }

    commit_stats: dict[str, str] = {}
    if start.head != end.head:
        revision = f"{start.head}..{end.head}"
        commit_candidates = _nul_paths(
            _git(
                repository_path,
                ["diff", "--name-only", "-z", "--diff-filter=ACDMRTUXB", revision, "--"],
            )
        )
        commit_stats = _numstat(repository_path, revision, commit_candidates)
        changed.update(commit_candidates)

    paths = tuple(sorted(changed))
    tracked_paths = tuple(path for path in paths if end_paths.get(path, None) is None or end_paths[path].state != "untracked")
    worktree_stats = _numstat(repository_path, "HEAD", tracked_paths)
    for path in paths:
        state = end_paths.get(path)
        if state is not None and state.state == "untracked":
            worktree_stats[path] = "untracked"

    return SnapshotDelta(
        paths=paths,
        start_head=start.head,
        end_head=end.head,
        start_digest=start.digest,
        end_digest=end.digest,
        commit_stat=_render_stat(commit_stats),
        worktree_stat=_render_stat(worktree_stats),
        includes_pre_session_edits=any(path in start_paths for path in paths),
    )


__all__ = ["capture_snapshot", "compare_snapshots", "content_sha256"]
