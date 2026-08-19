from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.hooks import _validate_write_event
from scripts.notion_journal.model import JournalDraft, Snapshot, VerificationItem
from scripts.notion_journal.store import JournalConfig, JournalStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPOSITORY_ROOT
    / ".agents"
    / "skills"
    / "record-notion-journal"
    / "scripts"
    / "sync_context.py"
)
SEOUL_NOW = datetime(2026, 8, 19, 20, 0, 0, tzinfo=timezone(timedelta(hours=9)))


class SyncContextScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state_context = TemporaryDirectory()
        self.addCleanup(self.state_context.cleanup)
        self.state_root = Path(self.state_context.name)
        self.store = JournalStore(self.state_root)
        self.config = JournalConfig(
            schema_version=1,
            workspace_id="private-workspace-fixture",
            workspace_name="Private Workspace",
            journal_page_id="private-parent-fixture",
            database_id="private-database-fixture",
            data_source_id="source-fixture",
            database_url="https://www.notion.so/private-database-fixture",
            read_tool_name="notion-fetch",
            query_tool_name="notion-query-data-sources",
            create_tool_name="notion-create-pages",
            update_tool_name="notion-update-page",
        )
        self.store.write_config(self.config)
        snapshot = Snapshot(
            repository="ClaimBranch",
            branch="main",
            head="1" * 40,
            paths=(),
            digest="2" * 64,
        )
        draft = JournalDraft(
            title="Package Notion journal skills",
            purpose="Make the workflow reusable",
            outcome="Added three bounded repository skills",
            key_decisions=("Keep remote writes approval-gated",),
            verification=(VerificationItem("skill contract tests", "Passed"),),
            risks=("Live writes remain interactive",),
            next_safe_action="Review the exact pending key",
            task_status="Completed",
            change_types=("tooling", "test"),
            ai_contribution="AI-assisted",
            verification_status="Passed",
        )
        self.envelope = self.store.capture_explicit_decision(snapshot, draft, SEOUL_NOW)
        self.env = os.environ.copy()
        self.env["CLAIMBRANCH_NOTION_JOURNAL_TESTING"] = "1"
        self.env["CLAIMBRANCH_NOTION_JOURNAL_STATE"] = str(self.state_root)

    def run_script(self, action: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                action,
                "--journal-key",
                self.envelope.journal_key,
                *extra,
            ],
            cwd=REPOSITORY_ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def state_bytes(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.state_root).as_posix(): path.read_bytes()
            for path in self.state_root.rglob("*")
            if path.is_file()
        }

    def test_query_is_parameterized_and_discloses_only_bounded_routing_data(self) -> None:
        result = self.run_script("query")

        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            {
                "schema_version",
                "journal_key",
                "configured_tool",
                "model_tool",
                "tool_input",
            },
            set(output),
        )
        self.assertEqual("notion-query-data-sources", output["configured_tool"])
        self.assertEqual(
            "mcp__notion__notion_query_data_sources", output["model_tool"]
        )
        self.assertEqual(
            ["collection://source-fixture"],
            output["tool_input"]["data"]["data_source_urls"],
        )
        self.assertEqual([self.envelope.journal_key], output["tool_input"]["data"]["params"])
        self.assertIn('WHERE "Journal Key" = ?', output["tool_input"]["data"]["query"])
        self.assertIn("LIMIT 2", output["tool_input"]["data"]["query"])
        for forbidden in (
            "private-workspace-fixture",
            "Private Workspace",
            "private-parent-fixture",
            "private-database-fixture",
            "explicit-decision",
            str(self.state_root),
        ):
            self.assertNotIn(forbidden, result.stdout)

    def test_create_payload_passes_the_existing_pre_write_guard(self) -> None:
        result = self.run_script("create")

        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("notion-create-pages", output["configured_tool"])
        self.assertEqual("mcp__notion__notion_create_pages", output["model_tool"])
        event = {
            "tool_name": "mcp__notion__" + self.config.create_tool_name,
            "tool_input": output["tool_input"],
        }
        validated = _validate_write_event(event, self.store)
        self.assertEqual(self.envelope.journal_key, validated[0])
        self.assertFalse(output["tool_input"]["allow_async"])

    def test_update_payload_passes_the_guard_for_the_selected_page(self) -> None:
        result = self.run_script("update", "--page-id", "page-result-fixture")

        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("notion-update-page", output["configured_tool"])
        self.assertEqual("mcp__notion__notion_update_page", output["model_tool"])
        event = {
            "tool_name": "mcp__notion__" + self.config.update_tool_name,
            "tool_input": output["tool_input"],
        }
        validated = _validate_write_event(event, self.store)
        self.assertEqual("page-result-fixture", validated[-1])
        self.assertFalse(output["tool_input"]["allow_async"])

    def test_invalid_page_id_fails_closed_without_output(self) -> None:
        result = self.run_script("update", "--page-id", "https://notion.so/wrong")

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("Journal sync context input is invalid.\n", result.stderr)

    def test_corrupt_state_is_not_quarantined_or_rewritten_by_the_skill_script(self) -> None:
        config_path = self.state_root / "config.json"
        config_path.write_bytes(b"{broken")

        result = self.run_script("query")

        self.assertEqual(5, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("Journal sync context is unavailable; run doctor.\n", result.stderr)
        self.assertEqual(b"{broken", config_path.read_bytes())
        self.assertEqual((), tuple((self.state_root / "quarantine").iterdir()))

    def test_successful_generation_does_not_mutate_live_state(self) -> None:
        before = self.state_bytes()

        for action, extra in (
            ("query", ()),
            ("create", ()),
            ("update", ("--page-id", "page-result-fixture")),
        ):
            result = self.run_script(action, *extra)
            self.assertEqual(0, result.returncode, result.stderr)

        self.assertEqual(before, self.state_bytes())

    def test_synced_key_cannot_generate_another_write(self) -> None:
        self.store.record_receipt(
            self.envelope.journal_key,
            "page-result-fixture",
            "https://app.notion.com/p/" + "a" * 32,
            SEOUL_NOW,
        )

        result = self.run_script("create")

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("Journal sync context input is invalid.\n", result.stderr)

    def test_configured_tools_must_match_their_locked_roles(self) -> None:
        cases = (
            ("query", replace(self.config, query_tool_name="notion-search")),
            ("create", replace(self.config, create_tool_name="notion-move-page")),
            ("create", replace(self.config, create_tool_name="notion-create-pager")),
            ("update", replace(self.config, update_tool_name="notion-delete-page")),
        )
        for action, config in cases:
            with self.subTest(action=action):
                self.store.write_config(config)
                extra = ("--page-id", "page-result-fixture") if action == "update" else ()
                result = self.run_script(action, *extra)
                self.assertEqual(5, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual(
                    "Journal sync context is unavailable; run doctor.\n",
                    result.stderr,
                )
                self.store.write_config(self.config)


if __name__ == "__main__":
    unittest.main()
