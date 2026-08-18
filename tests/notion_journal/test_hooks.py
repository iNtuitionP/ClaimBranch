from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.hooks import dispatch_hook
from scripts.notion_journal.model import (
    JournalDraft,
    JournalError,
    ValidationError,
    VerificationItem,
    canonical_json,
)
from scripts.notion_journal.store import JournalConfig, JournalStore
from tests.notion_journal.support import TemporaryGitRepository


SEOUL_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone(timedelta(hours=9)))


class HookTest(unittest.TestCase):
    def setUp(self):
        self.repo_context = TemporaryGitRepository()
        self.repo = self.repo_context.__enter__()
        self.addCleanup(self.repo_context.__exit__, None, None, None)
        self.repo.write_text("README.md", "baseline\n")
        self.repo.commit_all("baseline")
        self.state_context = TemporaryDirectory()
        self.addCleanup(self.state_context.cleanup)
        self.state_root = Path(self.state_context.name)
        self.store = JournalStore(self.state_root)
        dispatch_hook(self._session_event("startup"), self.repo.path, self.store)

    def test_second_stop_does_not_loop_when_stop_hook_active(self):
        event = {
            "session_id": "session-1",
            "turn_id": "turn-2",
            "cwd": str(self.repo.path),
            "hook_event_name": "Stop",
            "stop_hook_active": True,
        }
        self.repo.write_text("changed.md", "material change\n")
        result = dispatch_hook(event, self.repo.path, self.store)
        self.assertEqual({}, result)
        self.assertEqual(1, len(self.store.list_pending()))

    def test_session_start_captures_once_and_reports_pending_count(self):
        original = self.store.read_session("session-1")
        pending = self._capture_pending(active=True)

        result = dispatch_hook(
            self._session_event("resume"), self.repo.path, self.store
        )

        self.assertEqual(original.baseline, self.store.read_session("session-1").baseline)
        output = result["hookSpecificOutput"]
        self.assertEqual("SessionStart", output["hookEventName"])
        self.assertIn("Pending entries: 1.", output["additionalContext"])
        self.assertIn(pending.journal_key, output["additionalContext"])
        self.assertIn("Retry at most one old key", output["additionalContext"])
        self.assertNotIn(str(self.state_root), output["additionalContext"])

    def test_stop_with_no_material_delta_returns_empty_object(self):
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        self.assertEqual({}, result)
        self.assertEqual((), self.store.list_pending())

    def test_first_stop_creates_pending_and_returns_block_decision(self):
        self.repo.write_text("changed.md", "material change\n")
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        envelope = self.store.list_pending()[0]
        reason = (
            f"A ClaimBranch coding-journal envelope is pending: {envelope.journal_key}. "
            "Use only the configured Notion journal data source. Read it with "
            "`python -m scripts.notion_journal.cli pending --journal-key "
            f"{envelope.journal_key} --format json`, attach the structured draft with "
            "`python -m scripts.notion_journal.cli draft --journal-key "
            f"{envelope.journal_key} --input-json -`, query the exact Journal Key, and "
            "ask for approval before one create or update. Do not search the workspace. "
            "If Notion is unavailable, report `Notion journal: pending`."
        )
        self.assertEqual({"decision": "block", "reason": reason}, result)
        self.assertEqual(1, len(self.store.list_pending()))

    def test_cursor_advances_after_pending_before_remote_sync(self):
        envelope = self._capture_pending(active=True)
        session = self.store.read_session("session-1")
        self.assertEqual(envelope.end_snapshot, session.cursor)
        self.assertEqual((), self.store.list_receipts())

    def test_unconfigured_notion_still_leaves_pending(self):
        self.repo.write_text("changed.md", "material change\n")
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        envelope = self.store.list_pending()[0]
        self.assertEqual("block", result["decision"])
        self.assertIn("Notion journal: pending", result["reason"])
        self.assertEqual("pending", envelope.sync_state)
        with self.assertRaises(JournalError):
            self.store.read_config()

    def test_non_notion_post_tool_use_is_ignored(self):
        envelope = self._capture_drafted()
        before = canonical_json(envelope.to_storage_dict())
        event = self._tool_event(
            "PostToolUse", "mcp__other__write", {"value": "safe"}
        )
        event["tool_response"] = {"id": "other", "url": "https://example.com"}

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual(
            before,
            canonical_json(self.store.read_envelope(envelope.journal_key).to_storage_dict()),
        )

    def test_valid_pre_tool_use_defers_to_normal_approval(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PreToolUse", self._create_tool(), self._create_input(envelope)
        )

        result = dispatch_hook(event, self.repo.path, self.store)

        self.assertEqual({}, result)
        self.assertNotIn("allow", json.dumps(result))
        self.assertNotIn("approve", json.dumps(result))

    def test_valid_pre_tool_use_accepts_expanded_sqlite_date_keys(self):
        self._configure()
        envelope = self._capture_drafted()
        tool_input = self._create_input(envelope)

        result = dispatch_hook(
            self._tool_event("PreToolUse", self._create_tool(), tool_input),
            self.repo.path,
            self.store,
        )

        self.assertEqual({}, result)

    def test_pre_tool_use_requires_attached_draft(self):
        self._configure()
        envelope = self._capture_pending(active=True)
        event = self._tool_event(
            "PreToolUse",
            self._create_tool(),
            {
                "parent": {"data_source_id": "source-fixture"},
                "pages": [
                    {
                        "properties": {"Journal Key": envelope.journal_key},
                        "content": envelope.journal_key,
                    }
                ],
                "allow_async": False,
            },
        )
        self.assertEqual(self._denied(), dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual("pending", self.store.read_envelope(envelope.journal_key).sync_state)

    def test_unknown_key_secret_and_absolute_path_are_denied_before_write(self):
        self._configure()
        envelope = self._capture_drafted()
        safe = self._create_input(envelope)
        unknown = "cbj-v1-" + "f" * 24
        cases = []
        unknown_input = json.loads(json.dumps(safe).replace(envelope.journal_key, unknown))
        cases.append(unknown_input)
        secret_input = json.loads(json.dumps(safe))
        secret_input["pages"][0]["content"] += "\nAPI_KEY=fixture"
        cases.append(secret_input)
        absolute_input = json.loads(json.dumps(safe))
        absolute_input["pages"][0]["content"] += "\nC:\\Users\\alice"
        cases.append(absolute_input)

        before = self._state_bytes()
        for tool_input in cases:
            with self.subTest(tool_input=tool_input):
                event = self._tool_event("PreToolUse", self._create_tool(), tool_input)
                self.assertEqual(
                    self._denied(), dispatch_hook(event, self.repo.path, self.store)
                )
                self.assertEqual(before, self._state_bytes())

    def test_success_requires_matching_key_page_id_and_page_url(self):
        self._configure()
        envelope = self._capture_drafted()
        create_event = self._tool_event(
            "PostToolUse", self._create_tool(), self._create_input(envelope)
        )
        create_event["tool_response"] = {
            "pages": [
                {"id": "page-result", "url": "https://www.notion.so/page-result"}
            ]
        }

        self.assertEqual({}, dispatch_hook(create_event, self.repo.path, self.store))
        receipt = self.store.list_receipts()[0]
        self.assertEqual("page-result", receipt.page_id)

        synced = self.store.read_envelope(envelope.journal_key)
        update_event = self._tool_event(
            "PostToolUse",
            self._update_tool(),
            self._update_input(synced, "page-result"),
        )
        update_event["tool_response"] = {
            "page": {
                "id": "page-result",
                "url": "https://www.notion.so/page-result",
            }
        }
        self.assertEqual({}, dispatch_hook(update_event, self.repo.path, self.store))
        self.assertEqual(1, len(self.store.list_receipts()))

    def test_existing_page_update_can_create_first_receipt(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PostToolUse",
            self._update_tool(),
            self._update_input(envelope, "existing-page"),
        )
        event["tool_response"] = {
            "page": {
                "id": "existing-page",
                "url": "https://www.notion.so/existing-page",
            }
        }

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual("existing-page", self.store.list_receipts()[0].page_id)

    def test_update_result_page_id_must_match_input(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PostToolUse",
            self._update_tool(),
            self._update_input(envelope, "existing-page"),
        )
        event["tool_response"] = {
            "page": {
                "id": "different-page",
                "url": "https://www.notion.so/different-page",
            }
        }

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual((), self.store.list_receipts())
        self.assertEqual("pending", self.store.read_envelope(envelope.journal_key).sync_state)

    def test_wrong_create_parent_is_denied_before_write(self):
        self._configure()
        envelope = self._capture_drafted()
        tool_input = self._create_input(envelope)
        tool_input["parent"] = {"data_source_id": "other-source"}
        event = self._tool_event("PreToolUse", self._create_tool(), tool_input)

        self.assertEqual(self._denied(), dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual((), self.store.list_receipts())

    def test_mismatched_key_or_error_response_stays_pending(self):
        self._configure()
        envelope = self._capture_drafted()
        valid_input = self._create_input(envelope)
        valid_result = {
            "pages": [
                {"id": "page-result", "url": "https://www.notion.so/page-result"}
            ]
        }
        wrong_key = "cbj-v1-" + "f" * 24
        cases = [
            (
                json.loads(json.dumps(valid_input).replace(envelope.journal_key, wrong_key)),
                valid_result,
            ),
            (valid_input, {"isError": True, **valid_result}),
            (valid_input, {"error": "remote failure", **valid_result}),
            (valid_input, {"failed": True, **valid_result}),
            (valid_input, {"status": "failed", **valid_result}),
        ]

        for tool_input, tool_response in cases:
            with self.subTest(tool_response=tool_response):
                event = self._tool_event("PostToolUse", self._create_tool(), tool_input)
                event["tool_response"] = tool_response
                self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
                self.assertEqual((), self.store.list_receipts())
                self.assertEqual(
                    "pending", self.store.read_envelope(envelope.journal_key).sync_state
                )

    def test_unknown_tool_response_shape_stays_pending(self):
        self._configure()
        envelope = self._capture_drafted()
        marker = "UNRECOGNIZED-REMOTE-CONTENT"
        event = self._tool_event(
            "PostToolUse", self._create_tool(), self._create_input(envelope)
        )
        event["tool_response"] = {
            "content": [{"type": "text", "text": marker}]
        }

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual((), self.store.list_receipts())
        self.assertNotIn(marker.encode("utf-8"), b"".join(self._state_bytes().values()))

    def test_live_text_wrapped_app_notion_result_is_accepted(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PostToolUse", self._create_tool(), self._create_input(envelope)
        )
        page_id = "12345678-1234-1234-1234-123456789abc"
        page_url = "https://app.notion.com/p/12345678123412341234123456789abc?pvs=4"
        event["tool_response"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "pages": [
                                {
                                    "id": page_id,
                                    "url": page_url,
                                    "properties": {
                                        "title": "Redacted live-shape fixture"
                                    },
                                }
                            ]
                        }
                    ),
                }
            ]
        }

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        receipts = self.store.list_receipts()
        self.assertEqual(1, len(receipts))
        self.assertEqual(page_id, receipts[0].page_id)
        self.assertEqual(page_url, receipts[0].page_url)

    def test_async_and_multiple_page_writes_are_denied(self):
        self._configure()
        envelope = self._capture_drafted()
        async_input = self._create_input(envelope)
        async_input["allow_async"] = True
        multi_input = self._create_input(envelope)
        multi_input["pages"].append(json.loads(json.dumps(multi_input["pages"][0])))

        for tool_input in (async_input, multi_input):
            with self.subTest(tool_input=tool_input):
                event = self._tool_event("PreToolUse", self._create_tool(), tool_input)
                self.assertEqual(
                    self._denied(), dispatch_hook(event, self.repo.path, self.store)
                )

    def test_projection_uses_only_public_changed_path_limit(self):
        self._configure()
        for index in range(205):
            self.repo.write_text(f"generated/path-{index:03}.txt", "bounded fixture\n")
        dispatch_hook(self._stop_event(True), self.repo.path, self.store)
        pending = self.store.list_pending()[0]
        envelope = self.store.attach_draft(pending.journal_key, self._draft())
        event = self._tool_event(
            "PreToolUse", self._create_tool(), self._create_input(envelope)
        )

        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        body = event["tool_input"]["pages"][0]["content"]
        self.assertIn("- ... 5 path(s) omitted", body)
        self.assertNotIn("path-204.txt", body)

    def test_result_url_must_be_a_real_notion_domain(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PostToolUse", self._create_tool(), self._create_input(envelope)
        )
        event["tool_response"] = {
            "pages": [
                {"id": "page-result", "url": "https://evilnotion.so/page-result"}
            ]
        }
        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual((), self.store.list_receipts())

    def test_notion_site_result_is_accepted(self):
        self._configure()
        envelope = self._capture_drafted()
        event = self._tool_event(
            "PostToolUse", self._create_tool(), self._create_input(envelope)
        )
        event["tool_response"] = {
            "pages": [
                {
                    "id": "page-result",
                    "url": "https://claimbranch.notion.site/page-result",
                }
            ]
        }
        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual(1, len(self.store.list_receipts()))

    def test_unknown_hook_event_is_invalid(self):
        event = {
            "session_id": "session-1",
            "cwd": str(self.repo.path),
            "hook_event_name": "UnknownHook",
        }
        with self.assertRaises(ValidationError):
            dispatch_hook(event, self.repo.path, self.store)

    def _session_event(self, source: str):
        return {
            "session_id": "session-1",
            "cwd": str(self.repo.path),
            "hook_event_name": "SessionStart",
            "source": source,
        }

    def _stop_event(self, active: bool):
        return {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": str(self.repo.path),
            "hook_event_name": "Stop",
            "stop_hook_active": active,
        }

    def _tool_event(self, hook: str, tool_name: str, tool_input):
        return {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": str(self.repo.path),
            "hook_event_name": hook,
            "tool_name": tool_name,
            "tool_use_id": "tool-use-fixture",
            "tool_input": tool_input,
        }

    def _capture_pending(self, *, active: bool):
        self.repo.write_text("changed.md", "material change\n")
        dispatch_hook(self._stop_event(active), self.repo.path, self.store)
        return self.store.list_pending()[0]

    def _capture_drafted(self):
        envelope = self._capture_pending(active=True)
        return self.store.attach_draft(envelope.journal_key, self._draft())

    def _configure(self):
        self.store.write_config(
            JournalConfig(
                schema_version=1,
                workspace_id="workspace-fixture",
                workspace_name="Private Workspace",
                journal_page_id="journal-page-fixture",
                database_id="database-fixture",
                data_source_id="source-fixture",
                database_url="https://www.notion.so/database-fixture",
                read_tool_name="notion-fetch",
                query_tool_name="notion-query-data-sources",
                create_tool_name="notion-create-pages",
                update_tool_name="notion-update-page",
            )
        )

    def _draft(self):
        return JournalDraft(
            title="Capture a safe coding outcome",
            purpose="Keep a bounded local-first coding journal",
            outcome="The journal candidate is ready for approval",
            key_decisions=("Keep Git as the source of truth",),
            verification=(VerificationItem("python journal tests", "Passed"),),
            risks=("OAuth remains interactive",),
            next_safe_action="Query the exact journal key",
            task_status="Completed",
            change_types=("test", "tooling"),
            ai_contribution="AI-assisted",
            verification_status="Passed",
        )

    def _properties(self, envelope):
        draft = envelope.draft
        assert draft is not None
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

    def _body(self, envelope):
        draft = envelope.draft
        assert draft is not None
        visible_paths = envelope.delta.paths[:200]
        paths = "\n".join(f"- `{path}`" for path in visible_paths)
        omitted = ""
        if len(envelope.delta.paths) > len(visible_paths):
            omitted = (
                f"\n- ... {len(envelope.delta.paths) - len(visible_paths)} path(s) omitted"
            )
        decisions = "\n".join(f"- {item}" for item in draft.key_decisions)
        verification = "\n".join(
            f"- {item.command} — {item.outcome}" for item in draft.verification
        )
        risks = "\n".join(f"- {item}" for item in draft.risks)
        return (
            f"## Purpose\n\n{draft.purpose}\n\n"
            f"## Outcome\n\n{draft.outcome}\n\n"
            f"## Changed paths\n\n{paths}{omitted}\n\n"
            f"Commit stat:\n{envelope.delta.commit_stat or '(none)'}\n\n"
            f"Worktree stat:\n{envelope.delta.worktree_stat or '(none)'}\n\n"
            f"Pre-session edits included: {'yes' if envelope.delta.includes_pre_session_edits else 'no'}\n\n"
            f"## Key decisions\n\n{decisions or '- None'}\n\n"
            f"## Verification\n\n{verification or '- Not run'}\n\n"
            f"## Risks or unresolved work\n\n{risks or '- None'}\n\n"
            f"## Next safe action\n\n{draft.next_safe_action}\n\n"
            f"## Journal Key\n\n`{envelope.journal_key}`"
        )

    def _create_input(self, envelope):
        return {
            "parent": {"data_source_id": "source-fixture"},
            "pages": [
                {
                    "properties": self._properties(envelope),
                    "content": self._body(envelope),
                }
            ],
            "allow_async": False,
        }

    def _update_input(self, envelope, page_id: str):
        return {
            "page_id": page_id,
            "command": "replace_content",
            "new_str": self._body(envelope),
            "properties": self._properties(envelope),
            "allow_async": False,
        }

    def _create_tool(self):
        return "mcp__notion__notion-create-pages"

    def _update_tool(self):
        return "mcp__notion__notion-update-page"

    def _denied(self):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "ClaimBranch Notion journal write failed local policy validation.",
            }
        }

    def _state_bytes(self):
        return {
            path.relative_to(self.state_root).as_posix(): path.read_bytes()
            for path in self.state_root.rglob("*")
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
