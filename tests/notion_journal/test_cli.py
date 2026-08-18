import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.store import JournalStore
from tests.notion_journal.support import TemporaryGitRepository


REPO_ROOT = Path(__file__).resolve().parents[2]


class CliTest(unittest.TestCase):
    def setUp(self):
        self.repo_context = TemporaryGitRepository()
        self.repo = self.repo_context.__enter__()
        self.addCleanup(self.repo_context.__exit__, None, None, None)
        self.repo.write_text("README.md", "baseline\n")
        self.repo.commit_all("baseline")
        self.state_context = TemporaryDirectory()
        self.addCleanup(self.state_context.cleanup)
        self.state_root = Path(self.state_context.name)
        self.env = os.environ.copy()
        self.env["CLAIMBRANCH_NOTION_JOURNAL_TESTING"] = "1"
        self.env["CLAIMBRANCH_NOTION_JOURNAL_STATE"] = str(self.state_root)
        existing_python_path = self.env.get("PYTHONPATH")
        self.env["PYTHONPATH"] = (
            str(REPO_ROOT)
            if not existing_python_path
            else str(REPO_ROOT) + os.pathsep + existing_python_path
        )

    def test_hook_subprocess_emits_valid_json(self):
        result = self._run(
            "hook", input_json=self._session_event(), cwd=REPO_ROOT
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("SessionStart", output["hookSpecificOutput"]["hookEventName"])
        self.assertEqual("", result.stderr)

    def test_launcher_executes_real_hook_module(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".codex" / "hooks" / "notion_journal.py")],
            cwd=REPO_ROOT,
            input=json.dumps(self._session_event()),
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "SessionStart", json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"]
        )

    def test_malformed_hook_stdin_is_invalid_input(self):
        result = self._run("hook", input_text="{", cwd=REPO_ROOT)
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("Invalid journal command input.\n", result.stderr)
        self.assertNotIn(str(self.repo.path), result.stderr)

    def test_doctor_reports_missing_configuration_with_exit_three(self):
        result = self._run("doctor", "--format", "json")
        self.assertEqual(3, result.returncode)
        output = json.loads(result.stdout)
        self.assertFalse(output["configured"])
        self.assertTrue(output["state_writable"])
        self.assertEqual(1, output["schema_version"])
        self.assertEqual(0, output["quarantined_count"])

    def test_pending_lookup_and_absent_key_have_exact_exit_codes(self):
        envelope = self._prepare_pending()
        found = self._run(
            "pending", "--journal-key", envelope.journal_key, "--format", "json"
        )
        missing = self._run(
            "pending",
            "--journal-key",
            "cbj-v1-" + "f" * 24,
            "--format",
            "json",
        )

        self.assertEqual(0, found.returncode, found.stderr)
        public = json.loads(found.stdout)
        self.assertEqual(envelope.journal_key, public["journal_key"])
        self.assertNotIn("session_id", public)
        self.assertNotIn("material change", found.stdout)
        self.assertEqual(4, missing.returncode)
        self.assertEqual("", missing.stdout)

    def test_configure_round_trip_keeps_identifiers_out_of_output(self):
        result = self._configure()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("workspace-fixture", result.stdout)
        stored = JournalStore(self.state_root).read_config()
        self.assertEqual("workspace-fixture", stored.workspace_id)
        self.assertEqual("source-fixture", stored.data_source_id)
        doctor = self._run("doctor", "--format", "json")
        self.assertEqual(0, doctor.returncode, doctor.stderr)
        self.assertTrue(json.loads(doctor.stdout)["configured"])

    def test_pre_write_denial_and_pass_through_are_json(self):
        self._configure_ok()
        envelope = self._prepare_pending(attach_draft=True)
        valid_input = self._create_input(envelope)
        invalid_input = json.loads(json.dumps(valid_input))
        invalid_input["parent"] = {"data_source_id": "wrong-source"}

        denied = self._run(
            "hook",
            input_json=self._tool_event("PreToolUse", invalid_input),
            cwd=REPO_ROOT,
        )
        passed = self._run(
            "hook",
            input_json=self._tool_event("PreToolUse", valid_input),
            cwd=REPO_ROOT,
        )

        self.assertEqual(0, denied.returncode, denied.stderr)
        self.assertEqual("deny", json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual(0, passed.returncode, passed.stderr)
        self.assertEqual({}, json.loads(passed.stdout))

    def test_draft_attachment_reads_one_json_object(self):
        envelope = self._prepare_pending()
        draft = self._draft_dict()
        result = self._run(
            "draft",
            "--journal-key",
            envelope.journal_key,
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=draft,
        )
        trailing = self._run(
            "draft",
            "--journal-key",
            envelope.journal_key,
            "--input-json",
            "-",
            "--format",
            "json",
            input_text=json.dumps(draft) + "\n{}",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(draft["title"], json.loads(result.stdout)["draft"]["title"])
        self.assertEqual(draft["title"], JournalStore(self.state_root).read_envelope(envelope.journal_key).draft.title)
        self.assertEqual(2, trailing.returncode)
        self.assertEqual("", trailing.stdout)

    def test_explicit_decision_is_idempotent(self):
        draft = self._draft_dict()
        args = (
            "record-decision",
            "--input-json",
            "-",
            "--format",
            "json",
        )
        first = self._run(*args, input_json=draft, cwd=self.repo.path)
        second = self._run(*args, input_json=draft, cwd=self.repo.path)

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        first_output = json.loads(first.stdout)
        second_output = json.loads(second.stdout)
        self.assertEqual(first_output["journal_key"], second_output["journal_key"])
        self.assertEqual("explicit-decision", first_output["trigger"])
        self.assertEqual((), tuple(first_output["changed_paths"]))
        self.assertEqual(1, len(JournalStore(self.state_root).list_pending()))

    def test_unknown_subcommand_exits_two(self):
        result = self._run("unknown-command")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)

    def test_stop_local_state_error_never_claims_pending(self):
        started = self._run("hook", input_json=self._session_event(), cwd=REPO_ROOT)
        self.assertEqual(0, started.returncode, started.stderr)
        session_file = tuple((self.state_root / "sessions").glob("*.json"))[0]
        session_file.write_bytes(b"{broken")
        self.repo.write_text("changed.md", "material change\n")

        result = self._run("hook", input_json=self._stop_event(), cwd=REPO_ROOT)

        self.assertEqual(0, result.returncode)
        self.assertEqual(
            {
                "systemMessage": "ClaimBranch Notion journal local capture failed; run the journal doctor command."
            },
            json.loads(result.stdout),
        )
        self.assertNotIn("cbj-v1-", result.stdout)
        self.assertEqual((), JournalStore(self.state_root).list_pending())

    def test_pre_tool_use_local_state_error_denies(self):
        (self.state_root / "config.json").write_bytes(b"{broken")
        event = self._tool_event(
            "PreToolUse",
            {
                "parent": {"data_source_id": "source-fixture"},
                "pages": [
                    {
                        "properties": {"Journal Key": "cbj-v1-" + "a" * 24},
                        "content": "cbj-v1-" + "a" * 24,
                    }
                ],
            },
        )

        result = self._run("hook", input_json=event, cwd=REPO_ROOT)

        self.assertEqual(0, result.returncode)
        output = json.loads(result.stdout)
        self.assertEqual("deny", output["hookSpecificOutput"]["permissionDecision"])
        self.assertNotIn("allow", result.stdout.casefold())
        self.assertNotIn("broken", result.stdout)

    def test_post_tool_use_local_state_error_warns_and_keeps_envelope(self):
        self._configure_ok()
        envelope = self._prepare_pending(attach_draft=True)
        tool_input = self._create_input(envelope)
        (self.state_root / "config.json").write_bytes(b"{broken")
        event = self._tool_event("PostToolUse", tool_input)
        event["tool_response"] = {
            "pages": [
                {"id": "page-result", "url": "https://www.notion.so/page-result"}
            ]
        }

        result = self._run("hook", input_json=event, cwd=REPO_ROOT)

        self.assertEqual(0, result.returncode)
        self.assertEqual(
            {
                "systemMessage": "ClaimBranch Notion journal acknowledgement failed; run the journal doctor command."
            },
            json.loads(result.stdout),
        )
        self.assertEqual("pending", JournalStore(self.state_root).read_envelope(envelope.journal_key).sync_state)
        self.assertEqual((), JournalStore(self.state_root).list_receipts())

    def test_corrupt_pending_and_git_failure_use_distinct_exit_codes(self):
        key = "cbj-v1-" + "a" * 24
        pending_dir = self.state_root / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        (pending_dir / f"{key}.json").write_bytes(b"{broken")
        corrupt = self._run("pending", "--journal-key", key, "--format", "json")

        with TemporaryDirectory() as non_repo:
            git_failure = self._run(
                "record-decision",
                "--input-json",
                "-",
                "--format",
                "json",
                input_json=self._draft_dict(),
                cwd=Path(non_repo),
            )

        self.assertEqual(5, corrupt.returncode)
        self.assertEqual(6, git_failure.returncode)
        self.assertEqual("", corrupt.stdout)
        self.assertEqual("", git_failure.stdout)

    def test_state_override_requires_testing_flag(self):
        from scripts.notion_journal.cli import resolve_state_root

        production_env = {
            "LOCALAPPDATA": "C:/Users/alice/AppData/Local",
            "CLAIMBRANCH_NOTION_JOURNAL_STATE": "C:/unsafe/repository-state",
        }
        self.assertEqual(
            Path("C:/Users/alice/AppData/Local") / "ClaimBranch" / "NotionJournal",
            resolve_state_root(production_env),
        )

    def _run(
        self,
        *args: str,
        input_json=None,
        input_text: str | None = None,
        cwd: Path = REPO_ROOT,
    ):
        if input_json is not None:
            input_text = json.dumps(input_json)
        return subprocess.run(
            [sys.executable, "-m", "scripts.notion_journal.cli", *args],
            cwd=cwd,
            input=input_text,
            text=True,
            capture_output=True,
            env=self.env,
        )

    def _configure(self):
        return self._run(
            "configure",
            "--workspace-id",
            "workspace-fixture",
            "--workspace-name",
            "Private Workspace",
            "--journal-page-id",
            "journal-page-fixture",
            "--database-id",
            "database-fixture",
            "--data-source-id",
            "source-fixture",
            "--database-url",
            "https://www.notion.so/database-fixture",
            "--read-tool",
            "notion-fetch",
            "--query-tool",
            "notion-query-data-sources",
            "--create-tool",
            "notion-create-pages",
            "--update-tool",
            "notion-update-page",
        )

    def _configure_ok(self):
        result = self._configure()
        self.assertEqual(0, result.returncode, result.stderr)

    def _prepare_pending(self, *, attach_draft: bool = False):
        started = self._run("hook", input_json=self._session_event(), cwd=REPO_ROOT)
        self.assertEqual(0, started.returncode, started.stderr)
        self.repo.write_text("changed.md", "material change\n")
        stopped = self._run("hook", input_json=self._stop_event(), cwd=REPO_ROOT)
        self.assertEqual(0, stopped.returncode, stopped.stderr)
        store = JournalStore(self.state_root)
        envelope = store.list_pending()[0]
        if attach_draft:
            attached = self._run(
                "draft",
                "--journal-key",
                envelope.journal_key,
                "--input-json",
                "-",
                "--format",
                "json",
                input_json=self._draft_dict(),
            )
            self.assertEqual(0, attached.returncode, attached.stderr)
            envelope = store.read_envelope(envelope.journal_key)
        return envelope

    def _session_event(self):
        return {
            "session_id": "session-cli",
            "cwd": str(self.repo.path),
            "hook_event_name": "SessionStart",
            "source": "startup",
        }

    def _stop_event(self):
        return {
            "session_id": "session-cli",
            "turn_id": "turn-cli",
            "cwd": str(self.repo.path),
            "hook_event_name": "Stop",
            "stop_hook_active": True,
        }

    def _tool_event(self, hook_name: str, tool_input):
        event = {
            "session_id": "session-cli",
            "turn_id": "turn-cli",
            "cwd": str(self.repo.path),
            "hook_event_name": hook_name,
            "tool_name": "mcp__notion__notion-create-pages",
            "tool_use_id": "tool-cli",
            "tool_input": tool_input,
        }
        return event

    def _draft_dict(self):
        return {
            "title": "Capture a safe coding outcome",
            "purpose": "Keep a bounded local-first coding journal",
            "outcome": "The journal candidate is ready for approval",
            "key_decisions": ["Keep Git as the source of truth"],
            "verification": [
                {"command": "python journal tests", "outcome": "Passed"}
            ],
            "risks": ["OAuth remains interactive"],
            "next_safe_action": "Query the exact journal key",
            "task_status": "Completed",
            "change_types": ["test", "tooling"],
            "ai_contribution": "AI-assisted",
            "verification_status": "Passed",
        }

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
        paths = "\n".join(f"- `{path}`" for path in envelope.delta.paths[:200])
        decisions = "\n".join(f"- {item}" for item in draft.key_decisions)
        verification = "\n".join(
            f"- {item.command} — {item.outcome}" for item in draft.verification
        )
        risks = "\n".join(f"- {item}" for item in draft.risks)
        return (
            f"## Purpose\n\n{draft.purpose}\n\n"
            f"## Outcome\n\n{draft.outcome}\n\n"
            f"## Changed paths\n\n{paths}\n\n"
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


if __name__ == "__main__":
    unittest.main()
