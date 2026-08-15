"""Command-line and Codex-hook adapter for the local Notion journal outbox."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import os
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence
from uuid import uuid4

from . import SCHEMA_VERSION
from .git_state import capture_snapshot
from .hooks import dispatch_hook
from .model import (
    GitStateError,
    JournalDraft,
    JournalError,
    ValidationError,
    VerificationItem,
    canonical_json,
)
from .store import JournalConfig, JournalStore, state_root


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_NOT_CONFIGURED = 3
EXIT_NOT_FOUND = 4
EXIT_CORRUPT = 5
EXIT_GIT = 6
_KEY = re.compile(r"cbj-v1-[0-9a-f]{24}\Z")
_CAPTURE_FAILED = {
    "systemMessage": (
        "ClaimBranch Notion journal local capture failed; run the journal doctor command."
    )
}
_ACK_FAILED = {
    "systemMessage": (
        "ClaimBranch Notion journal acknowledgement failed; run the journal doctor command."
    )
}
_DENIED = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "ClaimBranch Notion journal write failed local policy validation.",
    }
}


class CliInputError(Exception):
    pass


def resolve_state_root(env: Mapping[str, str]) -> Path:
    """Honor an injected state root only in an explicit test process."""

    if env.get("CLAIMBRANCH_NOTION_JOURNAL_TESTING") == "1":
        override = env.get("CLAIMBRANCH_NOTION_JOURNAL_STATE")
        if override:
            return Path(override)
    return state_root(env)


def _store(env: Mapping[str, str]) -> JournalStore:
    try:
        return JournalStore(resolve_state_root(env))
    except OSError as error:
        raise JournalError("local journal state is unavailable") from error


def _git_root(cwd: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        decoded = completed.stdout.decode("utf-8", errors="surrogateescape").strip()
        root = Path(decoded)
        if not decoded or not root.is_dir():
            raise GitStateError("Git root is unavailable")
        return root
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        raise GitStateError("Git root is unavailable") from error


def _read_one_json(stream: Any) -> dict[str, Any]:
    try:
        raw = stream.read()
        decoder = json.JSONDecoder()
        stripped = raw.lstrip()
        value, end = decoder.raw_decode(stripped)
        if stripped[end:].strip():
            raise CliInputError("trailing JSON value")
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise CliInputError("invalid JSON input") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CliInputError("input must be one JSON object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise CliInputError("journal draft has unexpected fields")


def _draft_from_value(value: dict[str, Any]) -> JournalDraft:
    expected = {
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
    _exact_keys(value, expected)
    for field in ("key_decisions", "verification", "risks", "change_types"):
        if not isinstance(value[field], list):
            raise CliInputError(f"{field} must be an array")
    verification: list[VerificationItem] = []
    for item in value["verification"]:
        if not isinstance(item, dict):
            raise CliInputError("verification item must be an object")
        _exact_keys(item, {"command", "outcome"})
        try:
            verification.append(VerificationItem(item["command"], item["outcome"]))
        except (KeyError, TypeError, JournalError) as error:
            raise CliInputError("verification item is invalid") from error
    try:
        return JournalDraft(
            title=value["title"],
            purpose=value["purpose"],
            outcome=value["outcome"],
            key_decisions=tuple(value["key_decisions"]),
            verification=tuple(verification),
            risks=tuple(value["risks"]),
            next_safe_action=value["next_safe_action"],
            task_status=value["task_status"],
            change_types=tuple(value["change_types"]),
            ai_contribution=value["ai_contribution"],
            verification_status=value["verification_status"],
        )
    except (KeyError, TypeError, JournalError) as error:
        raise CliInputError("journal draft is invalid") from error


def _write_json(value: object) -> None:
    sys.stdout.buffer.write(canonical_json(value) + b"\n")


def _write_text(value: str) -> None:
    sys.stdout.write(value.rstrip() + "\n")


def _diagnostic(value: str) -> None:
    sys.stderr.write(value.rstrip() + "\n")


def _emit_public(value: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        _write_json(value)
        return
    state = value.get("sync_state", "pending")
    key = value.get("journal_key", "unknown")
    _write_text(f"Notion journal: {state} {key}")


def _pending_path(root: Path, key: str) -> Path:
    if not _KEY.fullmatch(key):
        raise CliInputError("journal key is invalid")
    return root / "pending" / f"{key}.json"


def _quarantine_count(root: Path) -> int:
    directory = root / "quarantine"
    return len(tuple(directory.glob("*.json"))) if directory.is_dir() else 0


def _state_writable(root: Path) -> bool:
    probe = root / f".doctor-{uuid4().hex}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(descriptor, b"ok")
        os.fsync(descriptor)
        return True
    except OSError:
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            probe.unlink()
        except FileNotFoundError:
            pass


def _doctor(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    root = resolve_state_root(env)
    store = _store(env)
    configured = False
    config_path = root / "config.json"
    if config_path.is_file():
        store.read_config()
        configured = True
    pending_count = len(store.list_pending())
    receipt_count = len(store.list_receipts())
    writable = _state_writable(root)
    result = {
        "schema_version": SCHEMA_VERSION,
        "configured": configured,
        "state_writable": writable,
        "official_mcp_expected": True,
        "pending_count": pending_count,
        "receipt_count": receipt_count,
        "quarantined_count": _quarantine_count(root),
    }
    if args.format == "json":
        _write_json(result)
    else:
        _write_text(
            "\n".join(
                (
                    f"Configured: {'yes' if configured else 'no'}",
                    f"State writable: {'yes' if writable else 'no'}",
                    f"Pending: {pending_count}",
                    f"Receipts: {receipt_count}",
                    f"Quarantined: {result['quarantined_count']}",
                )
            )
        )
    if not writable:
        return EXIT_CORRUPT
    return EXIT_OK if configured else EXIT_NOT_CONFIGURED


def _status(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    root = resolve_state_root(env)
    store = _store(env)
    configured = (root / "config.json").is_file()
    if configured:
        store.read_config()
    result = {
        "schema_version": SCHEMA_VERSION,
        "configured": configured,
        "pending_count": len(store.list_pending()),
        "receipt_count": len(store.list_receipts()),
        "quarantined_count": _quarantine_count(root),
    }
    if args.format == "json":
        _write_json(result)
    else:
        _write_text(
            f"Notion journal: {result['pending_count']} pending, "
            f"{result['receipt_count']} synced, "
            f"{result['quarantined_count']} quarantined."
        )
    return EXIT_OK


def _pending(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    root = resolve_state_root(env)
    path = _pending_path(root, args.journal_key)
    if not path.is_file():
        return EXIT_NOT_FOUND
    store = _store(env)
    envelope = store.read_envelope(args.journal_key)
    _emit_public(envelope.to_public_dict(), args.format)
    return EXIT_OK


def _draft(args: argparse.Namespace, env: Mapping[str, str], stdin: Any) -> int:
    if args.input_json != "-":
        raise CliInputError("draft input must come from stdin")
    draft = _draft_from_value(_read_one_json(stdin))
    root = resolve_state_root(env)
    path = _pending_path(root, args.journal_key)
    if not path.is_file():
        return EXIT_NOT_FOUND
    store = _store(env)
    before_quarantine = _quarantine_count(root)
    try:
        envelope = store.attach_draft(args.journal_key, draft)
    except JournalError as error:
        if _quarantine_count(root) > before_quarantine:
            raise
        raise CliInputError("journal draft conflicts with existing state") from error
    _emit_public(envelope.to_public_dict(), args.format)
    return EXIT_OK


def _record_decision(
    args: argparse.Namespace, env: Mapping[str, str], stdin: Any
) -> int:
    if args.input_json != "-":
        raise CliInputError("decision input must come from stdin")
    draft = _draft_from_value(_read_one_json(stdin))
    repo = _git_root(Path.cwd())
    snapshot = capture_snapshot(repo)
    envelope = _store(env).capture_explicit_decision(
        snapshot, draft, datetime_now_seoul()
    )
    _emit_public(envelope.to_public_dict(), args.format)
    return EXIT_OK


def datetime_now_seoul():
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone(timedelta(hours=9)))


def _configure(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    try:
        config = JournalConfig(
            schema_version=SCHEMA_VERSION,
            workspace_id=args.workspace_id,
            workspace_name=args.workspace_name,
            journal_page_id=args.journal_page_id,
            database_id=args.database_id,
            data_source_id=args.data_source_id,
            database_url=args.database_url,
            read_tool_name=args.read_tool,
            query_tool_name=args.query_tool,
            create_tool_name=args.create_tool,
            update_tool_name=args.update_tool,
        )
    except JournalError as error:
        raise CliInputError("configuration input is invalid") from error
    _store(env).write_config(config)
    _write_text("ClaimBranch Notion journal configured.")
    return EXIT_OK


def _hook(env: Mapping[str, str], stdin: Any) -> int:
    event = _read_one_json(stdin)
    hook_name = event.get("hook_event_name")
    try:
        cwd = Path(event.get("cwd", ""))
        repo = _git_root(cwd)
        store = _store(env)
        tool_name = event.get("tool_name")
        if (
            hook_name == "PostToolUse"
            and isinstance(tool_name, str)
            and tool_name.startswith("mcp__notion__")
            and re.search(r"(?i)(?:create|update)", tool_name)
        ):
            store.read_config()
        result = dispatch_hook(event, repo, store)
    except (JournalError, ValidationError, OSError):
        if hook_name in {"SessionStart", "Stop"}:
            result = _CAPTURE_FAILED
        elif hook_name == "PreToolUse":
            result = _DENIED
        elif hook_name == "PostToolUse":
            result = _ACK_FAILED
        else:
            raise CliInputError("hook input is invalid")
    _write_json(result)
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claimbranch-notion-journal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("hook")

    for name in ("doctor", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--format", choices=("text", "json"), default="text")

    pending = subparsers.add_parser("pending")
    pending.add_argument("--journal-key", required=True)
    pending.add_argument("--format", choices=("text", "json"), default="text")

    draft = subparsers.add_parser("draft")
    draft.add_argument("--journal-key", required=True)
    draft.add_argument("--input-json", required=True)
    draft.add_argument("--format", choices=("text", "json"), default="text")

    decision = subparsers.add_parser("record-decision")
    decision.add_argument("--input-json", required=True)
    decision.add_argument("--format", choices=("text", "json"), default="text")

    configure = subparsers.add_parser("configure")
    configure.add_argument("--workspace-id", required=True)
    configure.add_argument("--workspace-name", required=True)
    configure.add_argument("--journal-page-id", required=True)
    configure.add_argument("--database-id", required=True)
    configure.add_argument("--data-source-id", required=True)
    configure.add_argument("--database-url", required=True)
    configure.add_argument("--read-tool", required=True)
    configure.add_argument("--query-tool", required=True)
    configure.add_argument("--create-tool", required=True)
    configure.add_argument("--update-tool", required=True)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    stdin: Any = None,
) -> int:
    parser = _parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    active_env = os.environ if env is None else env
    active_stdin = sys.stdin if stdin is None else stdin
    try:
        if args.command == "hook":
            return _hook(active_env, active_stdin)
        if args.command == "doctor":
            return _doctor(args, active_env)
        if args.command == "status":
            return _status(args, active_env)
        if args.command == "pending":
            return _pending(args, active_env)
        if args.command == "draft":
            return _draft(args, active_env, active_stdin)
        if args.command == "record-decision":
            return _record_decision(args, active_env, active_stdin)
        if args.command == "configure":
            return _configure(args, active_env)
        raise CliInputError("unknown command")
    except CliInputError:
        _diagnostic("Invalid journal command input.")
        return EXIT_INVALID
    except GitStateError:
        _diagnostic("Git state is unavailable for the journal.")
        return EXIT_GIT
    except JournalError:
        _diagnostic("Notion journal local state is corrupt; run doctor.")
        return EXIT_CORRUPT
    except OSError:
        _diagnostic("Notion journal local state is unavailable; run doctor.")
        return EXIT_CORRUPT


if __name__ == "__main__":
    raise SystemExit(main())
