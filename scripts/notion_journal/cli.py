"""Command-line and Codex-hook adapter for the local Notion journal outbox."""

from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import replace
import hashlib
import hmac
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
    JudgmentDraft,
    JournalError,
    JournalNotFoundError,
    ValidationError,
    canonical_json,
    judgment_draft_to_dict,
    validate_journal_language,
)
from .presentation import render_judgment_preview
from .store import (
    JournalConfig,
    JournalStore,
    pending_envelope_path,
    read_config_file,
    state_root,
)


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_NOT_CONFIGURED = 3
EXIT_NOT_FOUND = 4
EXIT_CORRUPT = 5
EXIT_GIT = 6
_KEY = re.compile(r"cbj-v[12]-[0-9a-f]{24}\Z")
_CAPTURE_TOKEN = re.compile(
    r"cbj-capture-v3\.([A-Za-z0-9_-]+)\.([0-9a-f]{64})\Z"
)
_CAPTURE_TOKEN_PREFIX = "cbj-capture-v3"
_MAX_CAPTURE_TOKEN_LENGTH = 8192
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
        if raw.startswith("\ufeff"):
            raw = raw[1:]
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


def _judgment_from_value(value: dict[str, Any]) -> JudgmentDraft:
    expected = {
        "title",
        "background",
        "why_now",
        "understanding_shift",
        "human_judgment",
        "tradeoff_boundary",
        "revisit_signal",
        "evidence_pointers",
        "ai_contribution",
        "supersedes",
    }
    _exact_keys(value, expected)
    if value["background"] is None:
        raise CliInputError("judgment background is invalid")
    if not isinstance(value["evidence_pointers"], list):
        raise CliInputError("evidence_pointers must be an array")
    try:
        return JudgmentDraft(
            title=value["title"],
            background=value["background"],
            why_now=value["why_now"],
            understanding_shift=value["understanding_shift"],
            human_judgment=value["human_judgment"],
            tradeoff_boundary=value["tradeoff_boundary"],
            revisit_signal=value["revisit_signal"],
            evidence_pointers=tuple(value["evidence_pointers"]),
            ai_contribution=value["ai_contribution"],
            supersedes=value["supersedes"],
        )
    except (KeyError, TypeError, JournalError) as error:
        raise CliInputError("judgment draft is invalid") from error


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
    return pending_envelope_path(root, key)


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


def _record_judgment(
    args: argparse.Namespace, env: Mapping[str, str], stdin: Any
) -> int:
    if args.input_token != "-":
        raise CliInputError("judgment input must come from stdin")
    draft, journal_language = _judgment_from_capture_token(stdin)
    repo = _git_root(Path.cwd())
    snapshot = capture_snapshot(repo)
    envelope = _store(env).capture_explicit_judgment(
        snapshot,
        draft,
        datetime_now_seoul(),
        journal_language=journal_language,
    )
    _emit_public(envelope.to_public_dict(), args.format)
    return EXIT_OK


def _judgment_to_value(draft: JudgmentDraft) -> dict[str, Any]:
    if draft.background is None:
        raise CliInputError("judgment background is invalid")
    value = judgment_draft_to_dict(draft)
    value["evidence_pointers"] = list(draft.evidence_pointers)
    return value


def _capture_token_for(draft: JudgmentDraft, journal_language: str) -> str:
    language = validate_journal_language(journal_language)
    payload = canonical_json(
        {
            "draft": _judgment_to_value(draft),
            "journal_language": language,
        }
    )
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(payload).hexdigest()
    return f"{_CAPTURE_TOKEN_PREFIX}.{encoded}.{digest}"


def _judgment_from_capture_token(stream: Any) -> tuple[JudgmentDraft, str]:
    try:
        raw = stream.read()
    except (AttributeError, TypeError) as error:
        raise CliInputError("capture token input is invalid") from error
    if not isinstance(raw, str):
        raise CliInputError("capture token input is invalid")
    token = raw.strip()
    if not token or len(token) > _MAX_CAPTURE_TOKEN_LENGTH:
        raise CliInputError("capture token input is invalid")
    match = _CAPTURE_TOKEN.fullmatch(token)
    if match is None:
        raise CliInputError("capture token input is invalid")

    encoded_text, received_digest = match.groups()
    if len(encoded_text) % 4 == 1:
        raise CliInputError("capture token input is invalid")
    padding = b"=" * (-len(encoded_text) % 4)
    try:
        payload = base64.b64decode(
            encoded_text.encode("ascii") + padding,
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, binascii.Error, ValueError) as error:
        raise CliInputError("capture token input is invalid") from error
    canonical_encoding = (
        base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    )
    if not hmac.compare_digest(encoded_text, canonical_encoding):
        raise CliInputError("capture token input is invalid")
    if not hmac.compare_digest(received_digest, hashlib.sha256(payload).hexdigest()):
        raise CliInputError("capture token input is invalid")

    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CliInputError("capture token input is invalid") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CliInputError("capture token input is invalid")
    _exact_keys(value, {"draft", "journal_language"})
    draft_value = value["draft"]
    if not isinstance(draft_value, dict) or not all(
        isinstance(key, str) for key in draft_value
    ):
        raise CliInputError("capture token input is invalid")
    try:
        journal_language = validate_journal_language(value["journal_language"])
    except ValidationError as error:
        raise CliInputError("capture token input is invalid") from error
    draft = _judgment_from_value(draft_value)
    canonical_value = {
        "draft": _judgment_to_value(draft),
        "journal_language": journal_language,
    }
    if not hmac.compare_digest(payload, canonical_json(canonical_value)):
        raise CliInputError("capture token input is invalid")
    return draft, journal_language


def _preview_judgment(
    args: argparse.Namespace, stdin: Any
) -> int:
    if args.input_json != "-":
        raise CliInputError("judgment input must come from stdin")
    draft = _judgment_from_value(_read_one_json(stdin))
    journal_language = validate_journal_language(args.journal_language)
    _write_json(
        {
            "preview": render_judgment_preview(draft, journal_language),
            "capture_token": _capture_token_for(draft, journal_language),
        }
    )
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
            journal_language=args.journal_language,
        )
    except JournalError as error:
        raise CliInputError("configuration input is invalid") from error
    _store(env).write_config(config)
    _write_text("ClaimBranch Notion journal configured.")
    return EXIT_OK


def _journal_language(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    root = resolve_state_root(env)
    try:
        config = read_config_file(root)
    except JournalNotFoundError:
        return EXIT_NOT_CONFIGURED
    if args.set_language is not None:
        config = replace(config, journal_language=args.set_language)
        _store(env).write_config(config)
    _write_json({"journal_language": config.journal_language})
    return EXIT_OK


def _hook(env: Mapping[str, str], stdin: Any) -> int:
    event = _read_one_json(stdin)
    if not isinstance(event, dict):
        raise CliInputError("hook input must be a JSON object")
    hook_name = event.get("hook_event_name")
    if hook_name in {"SessionStart", "Stop"}:
        _write_json({})
        return EXIT_OK
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
        if hook_name == "PreToolUse":
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

    judgment = subparsers.add_parser("record-judgment")
    judgment.add_argument("--input-token", required=True)
    judgment.add_argument("--format", choices=("text", "json"), default="text")

    preview = subparsers.add_parser("preview-judgment")
    preview.add_argument("--journal-language", choices=("ko", "en"), required=True)
    preview.add_argument("--input-json", required=True)
    preview.add_argument("--format", choices=("json",), default="json")

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
    configure.add_argument("--journal-language", choices=("ko", "en"), required=True)

    language = subparsers.add_parser("journal-language")
    language.add_argument("--set", dest="set_language", choices=("ko", "en"))
    language.add_argument("--format", choices=("json",), default="json")
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
        if args.command == "record-judgment":
            return _record_judgment(args, active_env, active_stdin)
        if args.command == "preview-judgment":
            return _preview_judgment(args, active_stdin)
        if args.command == "configure":
            return _configure(args, active_env)
        if args.command == "journal-language":
            return _journal_language(args, active_env)
        raise CliInputError("unknown command")
    except CliInputError:
        _diagnostic("Invalid journal command input.")
        return EXIT_INVALID
    except JournalNotFoundError:
        return EXIT_NOT_FOUND
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
