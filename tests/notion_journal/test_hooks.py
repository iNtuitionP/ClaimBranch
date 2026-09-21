from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.git_state import capture_snapshot, compare_snapshots
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class HookRegistrationTest(unittest.TestCase):
    def test_only_write_guard_and_receipt_hooks_are_registered(self):
        manifest = json.loads(
            (REPOSITORY_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        )

        self.assertEqual({"PreToolUse", "PostToolUse"}, set(manifest["hooks"]))


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
        self.baseline = capture_snapshot(self.repo.path)

    def test_stop_never_creates_state_without_a_user_record_request(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        self.repo.write_text("changed.md", "material change\n")

        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)

        self.assertEqual({}, result)
        self.assertEqual((), self.store.list_pending())

    def test_stop_is_noop_when_stop_hook_is_already_active(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
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
        self.assertEqual((), self.store.list_pending())
        self.assertEqual(self.baseline, self.store.read_session("session-1").cursor)

    def test_session_start_is_noop_even_when_a_legacy_pending_entry_exists(self):
        pending = self._capture_pending(active=True)
        before = self._state_bytes()

        result = dispatch_hook(
            self._session_event("resume"), self.repo.path, self.store
        )

        self.assertEqual({}, result)
        self.assertEqual(before, self._state_bytes())
        self.assertEqual(pending, self.store.read_envelope(pending.journal_key))

    def test_stop_with_no_material_delta_returns_empty_object(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        self.assertEqual({}, result)
        self.assertEqual((), self.store.list_pending())

    def test_first_stop_does_not_create_pending_or_block(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        self.repo.write_text("changed.md", "material change\n")
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        self.assertEqual({}, result)
        self.assertEqual((), self.store.list_pending())

    def test_stop_does_not_advance_a_legacy_capture_cursor(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        self.repo.write_text("changed.md", "material change\n")

        dispatch_hook(self._stop_event(True), self.repo.path, self.store)

        session = self.store.read_session("session-1")
        self.assertEqual(self.baseline, session.cursor)
        self.assertEqual((), self.store.list_pending())
        self.assertEqual((), self.store.list_receipts())

    def test_unconfigured_notion_does_not_create_pending(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        self.repo.write_text("changed.md", "material change\n")
        result = dispatch_hook(self._stop_event(False), self.repo.path, self.store)
        self.assertEqual({}, result)
        self.assertEqual((), self.store.list_pending())
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

    def test_exact_key_write_ignores_unrelated_corrupt_receipts(self):
        self._configure()
        envelope = self._capture_drafted()
        unrelated = [
            self.store.receipts / ("cbj-v1-" + "f" * 24 + ".json"),
            self.store.v2_receipts / ("cbj-v2-" + "f" * 24 + ".json"),
        ]
        for path in unrelated:
            path.write_bytes(b"{broken-unrelated-receipt")
        before = self._state_bytes()
        tool_input = self._create_input(envelope)
        pre = self._tool_event("PreToolUse", self._create_tool(), tool_input)
        self.assertEqual({}, dispatch_hook(pre, self.repo.path, self.store))
        self.assertEqual(before, self._state_bytes())

        post = self._tool_event("PostToolUse", self._create_tool(), tool_input)
        post["tool_response"] = {"pages": [{
            "id": "page-result", "url": "https://www.notion.so/page-result",
        }]}
        self.assertEqual({}, dispatch_hook(post, self.repo.path, self.store))
        self.assertEqual("synced", self.store.read_envelope(envelope.journal_key).sync_state)
        for path in unrelated:
            self.assertEqual(b"{broken-unrelated-receipt", path.read_bytes())
        self.assertEqual([], list(self.store.quarantine.iterdir()))

        # The matching receipt must still prevent a duplicate create and a wrong-page update.
        self.assertEqual(self._denied(), dispatch_hook(pre, self.repo.path, self.store))
        wrong_page = self._tool_event(
            "PreToolUse", self._update_tool(), self._update_input(envelope, "wrong-page"),
        )
        self.assertEqual(self._denied(), dispatch_hook(wrong_page, self.repo.path, self.store))

    def test_exact_key_write_denies_a_corrupt_matching_receipt(self):
        self._configure()
        envelope = self._capture_drafted()
        receipt_path = self.store.receipts / f"{envelope.journal_key}.json"
        receipt_path.write_bytes(b"{broken-matching-receipt")
        event = self._tool_event(
            "PreToolUse", self._create_tool(), self._create_input(envelope),
        )
        self.assertEqual(self._denied(), dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual("pending", self.store.read_envelope(envelope.journal_key).sync_state)
        self.assertFalse(receipt_path.exists())
        self.assertEqual(1, len(list(self.store.quarantine.iterdir())))

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

    def test_existing_page_update_without_receipt_is_denied_without_state_change(self):
        self._configure()
        envelope = self._capture_drafted()
        before = self._state_bytes()
        pre = self._tool_event(
            "PreToolUse", self._update_tool(), self._update_input(envelope, "existing-page"),
        )
        self.assertEqual(self._denied(), dispatch_hook(pre, self.repo.path, self.store))
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
        self.assertEqual((), self.store.list_receipts())
        self.assertEqual(before, self._state_bytes())

    def test_existing_receipt_does_not_authorize_overwriting_a_human_owned_page(self):
        self._configure()
        envelope = self._capture_drafted()
        self.store.record_receipt(
            envelope.journal_key, "existing-page", "https://www.notion.so/existing-page", SEOUL_NOW,
        )
        before = self._state_bytes()
        event = self._tool_event(
            "PreToolUse", self._update_tool(), self._update_input(envelope, "existing-page"),
        )
        self.assertEqual(self._denied(), dispatch_hook(event, self.repo.path, self.store))
        event["hook_event_name"] = "PostToolUse"
        event["tool_response"] = {"page": {
            "id": "existing-page", "url": "https://www.notion.so/existing-page",
        }}
        self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
        self.assertEqual(before, self._state_bytes())

    def test_update_result_cannot_acknowledge_an_unrelated_page(self):
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

    def test_text_wrapped_failure_never_records_a_receipt(self):
        self._configure()
        envelope = self._capture_drafted()
        before = self._state_bytes()
        identity = {"pages": [{"id": "page-result", "url": "https://www.notion.so/page-result"}]}
        for failure in ({"isError": True}, {"error": "write failed"},
                        {"failed": True}, {"status": "failed"}):
            with self.subTest(failure=failure):
                event = self._tool_event("PostToolUse", self._create_tool(), self._create_input(envelope))
                event["tool_response"] = {"content": [{
                    "type": "text", "text": json.dumps({**identity, **failure}),
                }]}
                self.assertEqual({}, dispatch_hook(event, self.repo.path, self.store))
                self.assertEqual(before, self._state_bytes())
                self.assertEqual((), self.store.list_receipts())
                self.assertEqual("pending", self.store.read_envelope(envelope.journal_key).sync_state)

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
        pending = self._capture_current_pending()
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
        return self._capture_current_pending()

    def _capture_current_pending(self):
        self.store.create_session("session-1", self.baseline, SEOUL_NOW)
        current = capture_snapshot(self.repo.path)
        changes = compare_snapshots(self.repo.path, self.baseline, current)
        return self.store.capture_pending("session-1", current, changes, SEOUL_NOW)

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
