"""Deterministic Codex hook decisions for the Notion journal boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .model import (
    JudgmentDraft,
    JournalDraft,
    JournalError,
    ValidationError,
    canonical_json,
    sanitize_agent_text,
)
from .presentation import render_judgment_body
from .store import JournalConfig, JournalStore, PendingEnvelope, Receipt


_SEOUL = timezone(timedelta(hours=9))
_KEY_PATTERN = re.compile(r"(?<![0-9a-z])cbj-v[12]-[0-9a-f]{24}(?![0-9a-z])")
_NOTION_PAGE_QUERY = re.compile(r"pvs=[0-9]+\Z")
_DENIED = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "ClaimBranch Notion journal write failed local policy validation.",
    }
}
_TURN_EVENTS = frozenset({"Stop", "PreToolUse", "PostToolUse"})


def _required_string(event: dict[str, Any], field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value or len(value) > 2000 or not value.isprintable():
        raise ValidationError(f"hook {field} is invalid")
    return value


def validate_common_event(event: object) -> dict[str, Any]:
    if not isinstance(event, dict) or not all(isinstance(key, str) for key in event):
        raise ValidationError("hook input must be a JSON object")
    _required_string(event, "session_id")
    _required_string(event, "cwd")
    hook_name = _required_string(event, "hook_event_name")
    if hook_name in _TURN_EVENTS:
        _required_string(event, "turn_id")
    return event


def handle_session_start(
    event: dict[str, Any], repo: Path, store: JournalStore
) -> dict[str, object]:
    _ = event, repo, store
    return {}


def handle_stop(
    event: dict[str, Any], repo: Path, store: JournalStore
) -> dict[str, object]:
    _ = event, repo, store
    return {}


def _canonical_tool_names(config: JournalConfig) -> tuple[str, str]:
    return (
        "mcp__notion__" + config.create_tool_name,
        "mcp__notion__" + config.update_tool_name,
    )


def _walk_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)


def _validate_string_leaves(value: object) -> None:
    for leaf in _walk_strings(value):
        sanitize_agent_text(leaf, field="Notion write input")


def _keys_in(value: object) -> set[str]:
    keys: set[str] = set()
    for leaf in _walk_strings(value):
        keys.update(_KEY_PATTERN.findall(leaf))
    return keys


def _projected_journal_key(tool_input: dict[str, Any]) -> str:
    pages = tool_input.get("pages")
    if not isinstance(pages, list) or len(pages) != 1 or not isinstance(pages[0], dict):
        raise JournalError("create must contain exactly one page")
    properties = pages[0].get("properties")
    if not isinstance(properties, dict):
        raise JournalError("journal properties are invalid")
    journal_key = properties.get("Journal Key")
    if not isinstance(journal_key, str) or _KEY_PATTERN.fullmatch(journal_key) is None:
        raise JournalError("projected journal key is invalid")
    return journal_key


def _expected_properties(envelope: PendingEnvelope) -> dict[str, object]:
    draft = envelope.draft
    if draft is None:
        raise JournalError("pending envelope has no structured draft")
    if isinstance(draft, JudgmentDraft):
        return {
            "Title": draft.title,
            "Journal Key": envelope.journal_key,
            "date:Recorded At:start": envelope.recorded_at,
            "date:Recorded At:is_datetime": 1,
            "AI Contribution": draft.ai_contribution,
        }
    if not isinstance(draft, JournalDraft):
        raise JournalError("pending envelope has an unsupported draft")
    return {
        "Title": draft.title,
        "Journal Key": envelope.journal_key,
        "date:Recorded At:start": envelope.recorded_at,
        "date:Recorded At:is_datetime": 1,
        "Status": draft.task_status,
        "Repository": envelope.repository,
        "Branch": envelope.end_snapshot.branch,
        "Start HEAD": envelope.delta.start_head,
        "End HEAD": envelope.delta.end_head,
        "Worktree Digest": envelope.delta.end_digest,
        "Change Type": list(draft.change_types),
        "AI Contribution": draft.ai_contribution,
        "Verification": draft.verification_status,
    }


def _bullets(values: Iterable[str], *, empty: str) -> str:
    rendered = "\n".join(f"- {value}" for value in values)
    return rendered or empty


def _expected_body(envelope: PendingEnvelope) -> str:
    draft = envelope.draft
    if draft is None:
        raise JournalError("pending envelope has no structured draft")
    if isinstance(draft, JudgmentDraft):
        return render_judgment_body(draft, envelope.journal_language)
    if not isinstance(draft, JournalDraft):
        raise JournalError("pending envelope has an unsupported draft")
    visible_paths = envelope.delta.paths[:200]
    paths = _bullets((f"`{path}`" for path in visible_paths), empty="- None")
    decisions = _bullets(draft.key_decisions, empty="- None")
    verification = _bullets(
        (f"{item.command} — {item.outcome}" for item in draft.verification),
        empty="- Not run",
    )
    risks = _bullets(draft.risks, empty="- None")
    omitted = ""
    if len(envelope.delta.paths) > len(visible_paths):
        omitted = (
            f"\n- ... {len(envelope.delta.paths) - len(visible_paths)} path(s) omitted"
        )
    return (
        f"## Purpose\n\n{draft.purpose}\n\n"
        f"## Outcome\n\n{draft.outcome}\n\n"
        f"## Changed paths\n\n{paths}{omitted}\n\n"
        f"Commit stat:\n{envelope.delta.commit_stat or '(none)'}\n\n"
        f"Worktree stat:\n{envelope.delta.worktree_stat or '(none)'}\n\n"
        "Pre-session edits included: "
        f"{'yes' if envelope.delta.includes_pre_session_edits else 'no'}\n\n"
        f"## Key decisions\n\n{decisions}\n\n"
        f"## Verification\n\n{verification}\n\n"
        f"## Risks or unresolved work\n\n{risks}\n\n"
        f"## Next safe action\n\n{draft.next_safe_action}\n\n"
        f"## Journal Key\n\n`{envelope.journal_key}`"
    )


def _bounded_page_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or not value.isprintable()
        or any(character in "/\\?#" or character.isspace() for character in value)
    ):
        raise JournalError("Notion page ID is invalid")
    return value


def _validate_create_input(
    tool_input: dict[str, Any], config: JournalConfig, envelope: PendingEnvelope, receipt: Receipt | None
) -> None:
    if receipt is not None or envelope.sync_state == "synced":
        raise JournalError("a synced journal entry cannot be created again")
    if set(tool_input) - {"parent", "pages", "allow_async"}:
        raise JournalError("create input contains unsupported fields")
    if tool_input.get("allow_async", False) is not False:
        raise JournalError("asynchronous journal writes are not supported")
    parent = tool_input.get("parent")
    if not isinstance(parent, dict):
        raise JournalError("create parent is invalid")
    allowed_parent_keys = {"data_source_id"} | (
        {"type"} if parent.get("type") == "data_source_id" else set()
    )
    if set(parent) != allowed_parent_keys or parent.get("data_source_id") != config.data_source_id:
        raise JournalError("create parent is not the configured data source")
    pages = tool_input.get("pages")
    if not isinstance(pages, list) or len(pages) != 1 or not isinstance(pages[0], dict):
        raise JournalError("create must contain exactly one page")
    page = pages[0]
    if set(page) != {"properties", "content"}:
        raise JournalError("create page contains unsupported fields")
    if page.get("properties") != _expected_properties(envelope):
        raise JournalError("create properties do not match the journal projection")
    if page.get("content") != _expected_body(envelope):
        raise JournalError("create content does not match the journal projection")


def _validate_write_event(
    event: dict[str, Any], store: JournalStore
) -> tuple[str, dict[str, Any], PendingEnvelope, Receipt | None]:
    config = store.read_config()
    tool_name = event.get("tool_name")
    create_name, _ = _canonical_tool_names(config)
    if tool_name != create_name:
        raise JournalError("journal pages are human-owned; only configured creates are allowed")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        raise JournalError("Notion tool input must be an object")
    try:
        payload_size = len(canonical_json(tool_input))
    except (TypeError, ValueError, UnicodeError) as error:
        raise JournalError("Notion tool input is not canonical JSON") from error
    if payload_size > 64 * 1024:
        raise JournalError("Notion tool input is too large")
    _validate_string_leaves(tool_input)
    journal_key = _projected_journal_key(tool_input)
    envelope = store.read_envelope(journal_key)
    if envelope.draft is None:
        raise JournalError("journal draft must be attached before a write")
    allowed_keys = {journal_key}
    if isinstance(envelope.draft, JudgmentDraft) and envelope.draft.supersedes:
        allowed_keys.add(envelope.draft.supersedes)
    keys = _keys_in(tool_input)
    if keys != allowed_keys:
        raise JournalError("Notion tool input contains unexpected journal keys")
    receipt = store.read_receipt(journal_key)
    _validate_create_input(tool_input, config, envelope, receipt)
    return journal_key, tool_input, envelope, receipt


def handle_pre_tool_use(
    event: dict[str, Any], store: JournalStore
) -> dict[str, object]:
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__notion__"):
        return {}
    try:
        _validate_write_event(event, store)
    except (JournalError, ValidationError):
        return _DENIED
    return {}


def _response_failed(value: object) -> bool:
    if isinstance(value, list):
        return any(_response_failed(item) for item in value)
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        lowered = key.casefold()
        if lowered == "iserror" and item is True:
            return True
        if lowered in {"error", "failed"} and bool(item):
            return True
        if lowered == "status" and isinstance(item, str) and item.casefold() == "failed":
            return True
        if _response_failed(item):
            return True
    return False


def _result_page(tool_response: object) -> tuple[str, str] | None:
    if not isinstance(tool_response, dict) or _response_failed(tool_response):
        return None
    payload: object = tool_response.get("structuredContent", tool_response)
    if payload is tool_response and "content" in tool_response:
        content = tool_response.get("content")
        if not isinstance(content, list) or len(content) != 1:
            return None
        block = content[0]
        if (
            not isinstance(block, dict)
            or block.get("type") != "text"
            or set(block) - {"type", "text", "annotations", "_meta"}
        ):
            return None
        text = block.get("text")
        if not isinstance(text, str) or len(text.encode("utf-8")) > 64 * 1024:
            return None
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, UnicodeError):
            return None
    if not isinstance(payload, dict) or _response_failed(payload):
        return None
    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != 1:
        return None
    page = pages[0]
    if not isinstance(page, dict):
        return None
    page_id = page.get("id", page.get("page_id"))
    page_url = page.get("url", page.get("page_url"))
    try:
        return _bounded_page_id(page_id), _validated_result_url(page_url)
    except JournalError:
        return None


def _validated_result_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2000 or not value.isprintable():
        raise JournalError("Notion result URL is invalid")
    from urllib.parse import urlparse

    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    allowed = host == "app.notion.com" or any(
        host == domain or host.endswith("." + domain)
        for domain in ("notion.so", "notion.site")
    )
    if (
        parsed.scheme != "https"
        or not allowed
        or parsed.username
        or parsed.password
        or parsed.fragment
        or (parsed.query and not _NOTION_PAGE_QUERY.fullmatch(parsed.query))
    ):
        raise JournalError("Notion result URL is invalid")
    return value


def handle_post_tool_use(
    event: dict[str, Any], store: JournalStore
) -> dict[str, object]:
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__notion__"):
        return {}
    try:
        journal_key, _, _, _ = _validate_write_event(event, store)
    except (JournalError, ValidationError):
        return {}
    result = _result_page(event.get("tool_response"))
    if result is None:
        return {}
    page_id, page_url = result
    try:
        store.record_receipt(journal_key, page_id, page_url, datetime.now(_SEOUL))
    except JournalError:
        return {
            "systemMessage": (
                "Notion journal acknowledgement failed; inspect the local pending "
                "entry before retrying."
            )
        }
    return {}


HANDLERS = {
    "SessionStart": handle_session_start,
    "Stop": handle_stop,
    "PreToolUse": handle_pre_tool_use,
    "PostToolUse": handle_post_tool_use,
}


def dispatch_hook(
    event: object, repo: Path, store: JournalStore
) -> dict[str, object]:
    validated = validate_common_event(event)
    try:
        handler = HANDLERS[validated["hook_event_name"]]
    except KeyError as error:
        raise ValidationError("unsupported hook event") from error
    if handler in (handle_session_start, handle_stop):
        return handler(validated, repo, store)
    return handler(validated, store)


__all__ = [
    "dispatch_hook",
    "handle_post_tool_use",
    "handle_pre_tool_use",
    "handle_session_start",
    "handle_stop",
    "validate_common_event",
]
