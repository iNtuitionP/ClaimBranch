#!/usr/bin/env python3
"""Emit one bounded, deterministic MCP input for a pending journal key."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory
from typing import Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.notion_journal import SCHEMA_VERSION  # noqa: E402
from scripts.notion_journal.cli import (  # noqa: E402
    EXIT_CORRUPT,
    EXIT_INVALID,
    EXIT_NOT_CONFIGURED,
    EXIT_NOT_FOUND,
    EXIT_OK,
    resolve_state_root,
)
from scripts.notion_journal.hooks import (  # noqa: E402
    _expected_body,
    _expected_properties,
)
from scripts.notion_journal.model import JournalError  # noqa: E402
from scripts.notion_journal.store import (  # noqa: E402
    JournalConfig,
    JournalStore,
    PendingEnvelope,
    pending_envelope_path,
)


_JOURNAL_KEY = re.compile(r"cbj-v[12]-[0-9a-f]{24}\Z")
_FORBIDDEN_TOOL_TOKENS = frozenset({"delete", "move", "search", "duplicate"})


class SyncContextInputError(Exception):
    """A caller supplied an unsafe or inapplicable sync request."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SyncContextInputError(message)


def _parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(add_help=True)
    parser.add_argument("action", choices=("query", "create"))
    parser.add_argument("--journal-key", required=True)
    return parser


def _load_pending(
    journal_key: str, env: Mapping[str, str]
) -> tuple[JournalConfig | None, PendingEnvelope | None, int]:
    if not _JOURNAL_KEY.fullmatch(journal_key):
        raise SyncContextInputError("journal key is invalid")
    root = resolve_state_root(env)
    config_path = root / "config.json"
    pending_path = pending_envelope_path(root, journal_key)
    if not config_path.is_file():
        return None, None, EXIT_NOT_CONFIGURED
    if not pending_path.is_file():
        return None, None, EXIT_NOT_FOUND
    with TemporaryDirectory() as directory:
        store = JournalStore(Path(directory))
        shutil.copyfile(config_path, store.root / "config.json")
        shutil.copyfile(
            pending_path,
            pending_envelope_path(store.root, journal_key),
        )
        config = store.read_config()
        envelope = store.read_envelope(journal_key)
    if envelope.sync_state != "pending" or envelope.draft is None:
        raise SyncContextInputError("journal key is not write-eligible")
    return config, envelope, EXIT_OK


def _base(journal_key: str, configured_tool: str, tool_input: object) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "journal_key": journal_key,
        "configured_tool": configured_tool,
        "model_tool": "mcp__notion__" + configured_tool.replace("-", "_"),
        "tool_input": tool_input,
    }


def _require_tool_role(configured_tool: str, action: str) -> None:
    tokens = frozenset(configured_tool.lower().replace("_", "-").split("-"))
    if _FORBIDDEN_TOOL_TOKENS.intersection(tokens):
        raise JournalError("configured tool has a forbidden role")
    if action == "query":
        valid = (
            "query" in tokens
            and "data" in tokens
            and bool({"source", "sources"}.intersection(tokens))
        )
    else:
        valid = action in tokens and bool({"page", "pages"}.intersection(tokens))
    if not valid:
        raise JournalError("configured tool does not match its journal role")


def _query_context(
    config: JournalConfig, envelope: PendingEnvelope
) -> dict[str, object]:
    _require_tool_role(config.query_tool_name, "query")
    source_url = f"collection://{config.data_source_id}"
    quoted_source = source_url.replace('"', '""')
    tool_input = {
        "data": {
            "mode": "sql",
            "data_source_urls": [source_url],
            "query": (
                f'SELECT * FROM "{quoted_source}" '
                'WHERE "Journal Key" = ? LIMIT 2'
            ),
            "params": [envelope.journal_key],
        }
    }
    return _base(envelope.journal_key, config.query_tool_name, tool_input)


def _create_context(
    config: JournalConfig, envelope: PendingEnvelope
) -> dict[str, object]:
    _require_tool_role(config.create_tool_name, "create")
    tool_input = {
        "parent": {"data_source_id": config.data_source_id},
        "pages": [
            {
                "properties": _expected_properties(envelope),
                "content": _expected_body(envelope),
            }
        ],
        "allow_async": False,
    }
    return _base(envelope.journal_key, config.create_tool_name, tool_input)


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    active_env = os.environ if env is None else env
    try:
        args = _parser().parse_args(argv)
        config, envelope, status = _load_pending(args.journal_key, active_env)
        if status == EXIT_NOT_CONFIGURED:
            sys.stderr.write("Notion journal is not configured; run doctor.\n")
            return status
        if status == EXIT_NOT_FOUND:
            return status
        assert config is not None and envelope is not None
        if args.action == "query":
            output = _query_context(config, envelope)
        else:
            output = _create_context(config, envelope)
        sys.stdout.write(json.dumps(output, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        sys.stdout.write("\n")
        return EXIT_OK
    except SyncContextInputError:
        sys.stderr.write("Journal sync context input is invalid.\n")
        return EXIT_INVALID
    except (JournalError, OSError, UnicodeError, ValueError, TypeError):
        sys.stderr.write("Journal sync context is unavailable; run doctor.\n")
        return EXIT_CORRUPT


if __name__ == "__main__":
    raise SystemExit(main())
