import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.git_state import capture_snapshot, compare_snapshots
from scripts.notion_journal.model import JudgmentDraft, JournalDraft, VerificationItem
from scripts.notion_journal.store import JournalStore
from tests.notion_journal.support import TemporaryGitRepository


REPO_ROOT = Path(__file__).resolve().parents[2]
SEOUL_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone(timedelta(hours=9)))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.repo_context = TemporaryGitRepository()
        self.repo = self.repo_context.__enter__()
        self.addCleanup(self.repo_context.__exit__, None, None, None)
        self.repo.write_text("README.md", "baseline\n")
        self.repo.commit_all("baseline")
        self.baseline = capture_snapshot(self.repo.path)
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
        self.assertEqual({}, output)
        self.assertEqual((), tuple((self.state_root / "sessions").glob("*.json")))
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
        self.assertEqual({}, json.loads(result.stdout))

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

    def test_language_lookup_without_configuration_creates_no_state(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory) / "absent-journal-state"
            env = self.env.copy()
            env["CLAIMBRANCH_NOTION_JOURNAL_STATE"] = str(state_root)

            result = self._run(
                "journal-language", "--format", "json", env=env
            )

            self.assertEqual(3, result.returncode, result.stderr)
            self.assertEqual("", result.stdout)
            self.assertFalse(state_root.exists())

    def test_configure_requires_an_explicit_supported_language(self):
        missing = self._run(*self._configuration_args())
        unsupported = self._run(
            *self._configuration_args(), "--journal-language", "auto"
        )

        self.assertEqual(2, missing.returncode)
        self.assertEqual(2, unsupported.returncode)
        self.assertFalse((self.state_root / "config.json").exists())

    def test_journal_language_can_be_read_and_changed_only_explicitly(self):
        self._configure_ok("ko")

        before = self._run("journal-language", "--format", "json")
        changed = self._run(
            "journal-language", "--set", "en", "--format", "json"
        )
        after = self._run("journal-language", "--format", "json")

        self.assertEqual(0, before.returncode, before.stderr)
        self.assertEqual({"journal_language": "ko"}, json.loads(before.stdout))
        self.assertEqual(0, changed.returncode, changed.stderr)
        self.assertEqual({"journal_language": "en"}, json.loads(changed.stdout))
        self.assertEqual(0, after.returncode, after.stderr)
        self.assertEqual({"journal_language": "en"}, json.loads(after.stdout))

    def test_preview_judgment_localizes_exact_korean_and_english_labels(self):
        judgment = self._judgment_dict()
        judgment["title"] = "Stable fields, adaptive questions"
        judgment["evidence_pointers"] = []

        korean = self._run(
            "preview-judgment",
            "--journal-language",
            "ko",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=judgment,
            cwd=self.repo.path,
        )
        english = self._run(
            "preview-judgment",
            "--journal-language",
            "en",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=judgment,
            cwd=self.repo.path,
        )

        self.assertEqual(0, korean.returncode, korean.stderr)
        self.assertEqual(0, english.returncode, english.stderr)
        self.assertEqual(
            "제목: Stable fields, adaptive questions\n"
            "배경: ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n"
            "왜 지금: Automatic pending records became reading debt\n"
            "무엇이 달라졌나: Unknown\n"
            "무엇을 판단했나: Require an explicit user choice before capture\n"
            "무엇을 감수하거나 제외했나: None\n"
            "무엇이 이 판단을 바꿀까: Skipped\n"
            "근거: 없음\n"
            "AI 기여: AI-assisted\n"
            "대체하는 이전 기록: 없음",
            json.loads(korean.stdout)["preview"],
        )
        self.assertEqual(
            "Title: Stable fields, adaptive questions\n"
            "Background: ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n"
            "Why now: Automatic pending records became reading debt\n"
            "What changed: Unknown\n"
            "Human judgment: Require an explicit user choice before capture\n"
            "Tradeoff or boundary: None\n"
            "Revisit signal: Skipped\n"
            "Evidence: None\n"
            "AI contribution: AI-assisted\n"
            "Supersedes: None",
            json.loads(english.stdout)["preview"],
        )
        korean_token = json.loads(korean.stdout)["capture_token"]
        english_token = json.loads(english.stdout)["capture_token"]
        self.assertTrue(korean_token.startswith("cbj-capture-v3."))
        self.assertTrue(english_token.startswith("cbj-capture-v3."))
        self.assertNotEqual(korean_token, english_token)
        self.assertEqual((), tuple(self.state_root.iterdir()))

    def test_configuration_change_does_not_relocalize_a_pending_record(self):
        self._configure_ok("ko")
        preview = self._run(
            "preview-judgment",
            "--journal-language",
            "ko",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=self._judgment_dict(),
            cwd=self.repo.path,
        )
        self.assertEqual(0, preview.returncode, preview.stderr)
        recorded = self._run(
            "record-judgment",
            "--input-token",
            "-",
            "--format",
            "json",
            input_text=json.loads(preview.stdout)["capture_token"],
            cwd=self.repo.path,
        )
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]
        before = self._run_sync_context("create", journal_key)
        self.assertEqual(0, before.returncode, before.stderr)

        changed = self._run(
            "journal-language", "--set", "en", "--format", "json"
        )
        after = self._run_sync_context("create", journal_key)

        self.assertEqual(0, changed.returncode, changed.stderr)
        self.assertEqual(0, after.returncode, after.stderr)
        before_body = json.loads(before.stdout)["tool_input"]["pages"][0]["content"]
        after_body = json.loads(after.stdout)["tool_input"]["pages"][0]["content"]
        self.assertEqual(before_body, after_body)
        self.assertTrue(before_body.startswith("## 배경\n\n"))
        envelope = JournalStore(self.state_root).read_envelope(journal_key)
        self.assertEqual("ko", envelope.journal_language)

    def test_english_token_freezes_the_exact_english_notion_body(self):
        self._configure_ok("en")
        judgment = self._judgment_dict()
        preview = self._run(
            "preview-judgment",
            "--journal-language",
            "en",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=judgment,
            cwd=self.repo.path,
        )
        self.assertEqual(0, preview.returncode, preview.stderr)
        recorded = self._run(
            "record-judgment",
            "--input-token",
            "-",
            "--format",
            "json",
            input_text=json.loads(preview.stdout)["capture_token"],
            cwd=self.repo.path,
        )
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]

        projected = self._run_sync_context("create", journal_key)

        self.assertEqual(0, projected.returncode, projected.stderr)
        content = json.loads(projected.stdout)["tool_input"]["pages"][0]["content"]
        self.assertEqual(
            "## Background\n\n"
            "ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n\n"
            "## Why now\n\n"
            "Automatic pending records became reading debt\n\n"
            "## What changed\n\n"
            "Unknown\n\n"
            "## Human judgment\n\n"
            "Require an explicit user choice before capture\n\n"
            "## Tradeoff or boundary\n\n"
            "None\n\n"
            "## Revisit signal\n\n"
            "Skipped\n\n"
            "## Evidence\n\n"
            "- `docs/designs/journal.md`",
            content,
        )

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

    def test_legacy_semantic_mutation_commands_are_not_exposed(self):
        envelope = self._prepare_pending()
        pending_path = self.state_root / "pending" / f"{envelope.journal_key}.json"
        before = pending_path.read_bytes()
        cases = (
            (
                "draft",
                "--journal-key",
                envelope.journal_key,
                "--input-json",
                "-",
                "--format",
                "json",
            ),
            ("record-decision", "--input-json", "-", "--format", "json"),
        )
        for args in cases:
            with self.subTest(command=args[0]):
                result = self._run(
                    *args,
                    input_json=self._draft_dict(),
                    cwd=self.repo.path,
                )
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual(before, pending_path.read_bytes())
                self.assertIsNone(
                    JournalStore(self.state_root)
                    .read_envelope(envelope.journal_key)
                    .draft
                )
        self.assertEqual(1, len(JournalStore(self.state_root).list_pending()))

    def test_preview_judgment_emits_exact_human_preview_and_capture_token(self):
        judgment = self._judgment_dict()
        judgment["title"] = "  Prefer user-invoked journal entries  "
        judgment["evidence_pointers"] = [
            "docs/designs/journal.md",
            "tests/notion_journal/test_cli.py",
        ]

        result = self._run(
            "preview-judgment",
            "--journal-language",
            "en",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=judgment,
            cwd=self.repo.path,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual({"preview", "capture_token"}, set(output))
        self.assertEqual(
            "Title: Prefer user-invoked journal entries\n"
            "Background: ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n"
            "Why now: Automatic pending records became reading debt\n"
            "What changed: Unknown\n"
            "Human judgment: Require an explicit user choice before capture\n"
            "Tradeoff or boundary: None\n"
            "Revisit signal: Skipped\n"
            "Evidence:\n"
            "- `docs/designs/journal.md`\n"
            "- `tests/notion_journal/test_cli.py`\n"
            "AI contribution: AI-assisted\n"
            "Supersedes: None",
            output["preview"],
        )
        canonical_input = {
            "title": "Prefer user-invoked journal entries",
            "background": (
                "ClaimBranch was defining how one coding judgment reaches its "
                "user-controlled Notion journal"
            ),
            "why_now": "Automatic pending records became reading debt",
            "understanding_shift": "Unknown",
            "human_judgment": "Require an explicit user choice before capture",
            "tradeoff_boundary": "None",
            "revisit_signal": "Skipped",
            "evidence_pointers": [
                "docs/designs/journal.md",
                "tests/notion_journal/test_cli.py",
            ],
            "ai_contribution": "AI-assisted",
            "supersedes": None,
        }
        token = output["capture_token"]
        self.assertIsInstance(token, str)
        token.encode("ascii")
        prefix, payload_text, digest = token.split(".")
        self.assertEqual("cbj-capture-v3", prefix)
        self.assertRegex(payload_text, r"^[A-Za-z0-9_-]+$")
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        padding = "=" * (-len(payload_text) % 4)
        payload = base64.urlsafe_b64decode(payload_text + padding)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
        self.assertEqual(
            json.dumps(
                {"draft": canonical_input, "journal_language": "en"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            payload,
        )
        self.assertEqual((), tuple(self.state_root.iterdir()))

    def test_preview_judgment_is_byte_stable_without_git_or_state(self):
        with TemporaryDirectory() as non_repo, TemporaryDirectory() as temporary_root:
            state_root = Path(temporary_root) / "journal-state"
            env = self.env.copy()
            env["CLAIMBRANCH_NOTION_JOURNAL_STATE"] = str(state_root)
            self.assertFalse(state_root.exists())

            first = self._run(
                "preview-judgment",
                "--journal-language",
                "ko",
                "--input-json",
                "-",
                "--format",
                "json",
                input_json=self._judgment_dict(),
                cwd=Path(non_repo),
                env=env,
            )
            self.assertFalse(state_root.exists())
            second = self._run(
                "preview-judgment",
                "--journal-language",
                "ko",
                "--input-json",
                "-",
                "--format",
                "json",
                input_json=self._judgment_dict(),
                cwd=Path(non_repo),
                env=env,
            )
            self.assertFalse(state_root.exists())

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(first.stdout.encode("utf-8"), second.stdout.encode("utf-8"))
        self.assertEqual(b"", first.stderr.encode("utf-8"))

    def test_preview_judgment_rejects_invalid_input_without_state(self):
        missing_field = self._judgment_dict()
        del missing_field["background"]
        unsafe_evidence = self._judgment_dict()
        unsafe_evidence["evidence_pointers"] = ["C:/Users/alice/evidence.md"]

        for value in (missing_field, unsafe_evidence):
            with self.subTest(value=value):
                result = self._run(
                    "preview-judgment",
                    "--journal-language",
                    "ko",
                    "--input-json",
                    "-",
                    "--format",
                    "json",
                    input_json=value,
                    cwd=self.repo.path,
                )

                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual("Invalid journal command input.\n", result.stderr)

        self.assertEqual((), tuple(self.state_root.iterdir()))

    def test_capture_token_can_be_recorded_in_a_fresh_process_without_prior_state(self):
        preview = self._run(
            "preview-judgment",
            "--journal-language",
            "ko",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=self._judgment_dict(),
            cwd=self.repo.path,
        )
        self.assertEqual(0, preview.returncode, preview.stderr)
        preview_output = json.loads(preview.stdout)
        self.assertIn("capture_token", preview_output)
        capture_token = preview_output["capture_token"]
        self.assertEqual((), tuple(self.state_root.iterdir()))

        recorded = self._run(
            "record-judgment",
            "--input-token",
            "-",
            "--format",
            "json",
            input_text=capture_token,
            cwd=self.repo.path,
        )

        self.assertEqual(0, recorded.returncode, recorded.stderr)
        public = json.loads(recorded.stdout)
        confirmed = self._judgment_dict()
        self.assertEqual(confirmed, public["draft"])
        self.assertEqual("ko", public["journal_language"])
        envelope = JournalStore(self.state_root).read_envelope(public["journal_key"])
        self.assertEqual("ko", envelope.journal_language)
        self.assertEqual(confirmed["background"], envelope.draft.background)
        self.assertEqual(confirmed["title"], envelope.draft.title)
        self.assertEqual(confirmed["why_now"], envelope.draft.why_now)
        self.assertEqual(
            tuple(confirmed["evidence_pointers"]), envelope.draft.evidence_pointers
        )
        self.assertEqual(confirmed["supersedes"], envelope.draft.supersedes)

    def test_record_judgment_rejects_changed_or_wrong_version_capture_tokens_without_state(self):
        preview = self._run(
            "preview-judgment",
            "--journal-language",
            "ko",
            "--input-json",
            "-",
            "--format",
            "json",
            input_json=self._judgment_dict(),
            cwd=self.repo.path,
        )
        self.assertEqual(0, preview.returncode, preview.stderr)
        preview_output = json.loads(preview.stdout)
        self.assertIn("capture_token", preview_output)
        token = preview_output["capture_token"]
        changed_digest = token[:-1] + ("0" if token[-1] != "0" else "1")
        wrong_version = token.replace("cbj-capture-v3", "cbj-capture-v2", 1)
        truncated = token[:-8]

        with TemporaryDirectory() as non_repo:
            for invalid in (changed_digest, wrong_version, truncated):
                with self.subTest(token=invalid[:24]):
                    result = self._run(
                        "record-judgment",
                        "--input-token",
                        "-",
                        "--format",
                        "json",
                        input_text=invalid,
                        cwd=Path(non_repo),
                    )
                    self.assertEqual(2, result.returncode)
                    self.assertEqual("", result.stdout)
                    self.assertEqual(
                        "Invalid journal command input.\n", result.stderr
                    )
                    self.assertEqual((), tuple(self.state_root.iterdir()))

    def test_record_judgment_rejects_noncanonical_or_invalid_token_payloads_without_state(self):
        def token_for(payload: bytes, encoded: str | None = None) -> str:
            payload_text = encoded or (
                base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
            )
            return (
                f"cbj-capture-v3.{payload_text}."
                f"{hashlib.sha256(payload).hexdigest()}"
            )

        valid = {
            "draft": self._judgment_dict(),
            "journal_language": "ko",
        }
        canonical_payload = json.dumps(
            valid,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(canonical_payload) % 3 == 0:
            valid["draft"]["title"] += "!"
            canonical_payload = json.dumps(
                valid,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        canonical_encoding = (
            base64.urlsafe_b64encode(canonical_payload)
            .rstrip(b"=")
            .decode("ascii")
        )
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        final_index = alphabet.index(canonical_encoding[-1])
        noncanonical_encoding = canonical_encoding[:-1] + alphabet[final_index + 1]
        noncanonical_json = json.dumps(
            valid,
            ensure_ascii=False,
            indent=1,
            sort_keys=False,
        ).encode("utf-8")
        invalid_draft = json.loads(json.dumps(valid))
        del invalid_draft["draft"]["revisit_signal"]
        invalid_draft_json = json.dumps(
            invalid_draft,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        invalid_language = json.loads(json.dumps(valid))
        invalid_language["journal_language"] = "auto"
        invalid_language_json = json.dumps(
            invalid_language,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        malformed_base64 = token_for(b"", encoded="A")
        noncanonical_base64 = token_for(
            canonical_payload,
            encoded=noncanonical_encoding,
        )

        with TemporaryDirectory() as non_repo:
            for invalid in (
                malformed_base64,
                noncanonical_base64,
                token_for(noncanonical_json),
                token_for(invalid_draft_json),
                token_for(invalid_language_json),
            ):
                with self.subTest(token=invalid[:24]):
                    result = self._run(
                        "record-judgment",
                        "--input-token",
                        "-",
                        "--format",
                        "json",
                        input_text=invalid,
                        cwd=Path(non_repo),
                    )
                    self.assertEqual(2, result.returncode)
                    self.assertEqual("", result.stdout)
                    self.assertEqual(
                        "Invalid journal command input.\n", result.stderr
                    )
                    self.assertEqual((), tuple(self.state_root.iterdir()))

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell 5.1 is required",
    )
    def test_powershell_51_utf8_preview_token_survives_a_fresh_capture_process(self):
        proposed = {
            "title": "사용자 호출 기록",
            "background": "ClaimBranch의 사용자 통제 코딩 판단 기록을 정하던 상황",
            "why_now": "자동 기록이 사람의 읽기 부채가 되었다",
            "understanding_shift": "작업이 아니라 판단이 기록 단위다",
            "human_judgment": "사용자가 호출하고 확인한 판단만 기록한다",
            "tradeoff_boundary": "자동 후보와 숨은 대기열을 만들지 않는다",
            "revisit_signal": "판단의 경계를 빠르게 찾지 못하면 다시 연다",
            "evidence_pointers": ["docs/designs/journal.md"],
            "ai_contribution": "AI-assisted",
            "supersedes": None,
        }
        preview_script = """
$utf8 = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$proposed = [pscustomobject]@{
  title = '사용자 호출 기록'
  background = 'ClaimBranch의 사용자 통제 코딩 판단 기록을 정하던 상황'
  why_now = '자동 기록이 사람의 읽기 부채가 되었다'
  understanding_shift = '작업이 아니라 판단이 기록 단위다'
  human_judgment = '사용자가 호출하고 확인한 판단만 기록한다'
  tradeoff_boundary = '자동 후보와 숨은 대기열을 만들지 않는다'
  revisit_signal = '판단의 경계를 빠르게 찾지 못하면 다시 연다'
  evidence_pointers = @('docs/designs/journal.md')
  ai_contribution = 'AI-assisted'
  supersedes = $null
}
$proposed | ConvertTo-Json -Depth 10 -Compress |
  & python -X utf8 -m scripts.notion_journal.cli preview-judgment --journal-language ko --input-json - --format json
"""
        with TemporaryDirectory() as non_repo:
            preview = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    preview_script,
                ],
                cwd=non_repo,
                text=True,
                encoding="utf-8",
                capture_output=True,
                env=self.env,
            )

        self.assertEqual(0, preview.returncode, preview.stderr)
        preview_output = json.loads(preview.stdout)
        self.assertIn(proposed["title"], preview_output["preview"])
        self.assertIn(proposed["human_judgment"], preview_output["preview"])
        self.assertIn("capture_token", preview_output)
        token = preview_output["capture_token"]
        token.encode("ascii")
        self.assertEqual((), tuple(self.state_root.iterdir()))

        record_script = """
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
& python -X utf8 -m scripts.notion_journal.cli record-judgment --input-token - --format json
"""
        recorded = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                record_script,
            ],
            cwd=self.repo.path,
            input=token,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=self.env,
        )

        self.assertEqual(0, recorded.returncode, recorded.stderr)
        public = json.loads(recorded.stdout)
        self.assertEqual(proposed, public["draft"])
        self.assertEqual("ko", public["journal_language"])
        self.assertEqual(1, len(JournalStore(self.state_root).list_pending()))

    def test_record_judgment_rejects_direct_json_without_creating_state(self):
        current = self._judgment_dict()
        legacy = dict(current)
        legacy.pop("background")
        for value in (current, legacy):
            with self.subTest(has_background="background" in value):
                with TemporaryDirectory() as directory:
                    state_root = Path(directory) / "absent-journal-state"
                    env = self.env.copy()
                    env["CLAIMBRANCH_NOTION_JOURNAL_STATE"] = str(state_root)
                    result = self._run(
                        "record-judgment", "--input-json", "-", "--format", "json",
                        input_json=value, cwd=self.repo.path, env=env,
                    )
                    self.assertEqual(2, result.returncode)
                    self.assertEqual("", result.stdout)
                    self.assertFalse(state_root.exists())

    def test_record_judgment_is_idempotent_for_exact_confirmed_input(self):
        confirmed = self._judgment_dict()
        preview = self._preview_judgment(confirmed)
        self.assertEqual(0, preview.returncode, preview.stderr)
        token = json.loads(preview.stdout)["capture_token"]
        args = ("record-judgment", "--input-token", "-", "--format", "json")

        first = self._run(*args, input_text=token, cwd=self.repo.path)
        second = self._run(*args, input_text=token, cwd=self.repo.path)

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        first_output = json.loads(first.stdout)
        second_output = json.loads(second.stdout)
        self.assertEqual(first_output["journal_key"], second_output["journal_key"])
        self.assertRegex(first_output["journal_key"], r"^cbj-v2-[0-9a-f]{24}$")
        self.assertEqual("explicit-judgment", first_output["trigger"])
        self.assertEqual([], first_output["changed_paths"])
        self.assertEqual(confirmed, first_output["draft"])
        self.assertEqual(1, len(JournalStore(self.state_root).list_pending()))
        pending_path = (
            self.state_root
            / "v2"
            / "pending"
            / f"{first_output['journal_key']}.json"
        )
        self.assertEqual("ko", json.loads(pending_path.read_bytes())["journal_language"])

    def test_existing_legacy_nine_key_record_keeps_the_former_body(self):
        self._configure_ok("en")
        legacy = self._judgment_dict()
        legacy.pop("background")

        # Seed an old envelope internally; the public CLI cannot create one.
        draft_value = {**legacy, "evidence_pointers": tuple(legacy["evidence_pointers"])}
        envelope = JournalStore(self.state_root).capture_explicit_judgment(
            self.baseline, JudgmentDraft(**draft_value), SEOUL_NOW,
        )
        recorded = self._run("pending", "--journal-key", envelope.journal_key, "--format", "json")
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        public = json.loads(recorded.stdout)
        self.assertEqual(legacy, public["draft"])
        pending_path = (
            self.state_root
            / "v2"
            / "pending"
            / f"{public['journal_key']}.json"
        )
        stored = json.loads(pending_path.read_bytes())
        self.assertNotIn("background", stored["draft"])
        self.assertNotIn("journal_language", stored)
        before = pending_path.read_bytes()

        projected = self._run_sync_context("create", public["journal_key"])
        self.assertEqual(0, projected.returncode, projected.stderr)
        body = json.loads(projected.stdout)["tool_input"]["pages"][0]["content"]
        self.assertTrue(body.startswith("## 왜 지금\n\n"))
        self.assertNotIn("## 배경", body)
        self.assertNotIn("## Background", body)
        self.assertEqual(before, pending_path.read_bytes())

    def test_preview_rejects_unconfirmed_shape_without_creating_state(self):
        missing_field = self._judgment_dict()
        del missing_field["revisit_signal"]
        absolute_evidence = self._judgment_dict()
        absolute_evidence["evidence_pointers"] = ["C:/Users/alice/evidence.md"]

        for value in (missing_field, absolute_evidence):
            with self.subTest(value=value):
                result = self._preview_judgment(value)
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual("Invalid journal command input.\n", result.stderr)

        self.assertEqual((), JournalStore(self.state_root).list_pending())

    def test_record_judgment_rejects_a_missing_superseded_key(self):
        correction = self._judgment_dict()
        correction["supersedes"] = "cbj-v2-" + "f" * 24

        result = self._record_preview(correction)

        self.assertEqual(4, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual((), JournalStore(self.state_root).list_pending())

    def test_record_judgment_rejects_an_undrafted_legacy_superseded_key(self):
        legacy = self._prepare_pending()
        correction = self._judgment_dict()
        correction["supersedes"] = legacy.journal_key

        result = self._record_preview(correction)

        self.assertEqual(4, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual((legacy,), JournalStore(self.state_root).list_pending())

    def test_preview_rejects_private_semantic_text_without_state(self):
        for unsafe in (
            r"\\server\share\record.md",
            "//server/share/record.md",
            "/root/private.txt",
            "AWS_SECRET_ACCESS_" + "KEY=fixture",
            "DATABASE_URL=postgres://alice:fixture@db.example.test/main",
        ):
            with self.subTest(unsafe=unsafe):
                judgment = self._judgment_dict()
                judgment["why_now"] = unsafe
                result = self._preview_judgment(judgment)
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)

        self.assertEqual((), JournalStore(self.state_root).list_pending())

    def test_v2_create_projection_uses_only_the_confirmed_judgment_form(self):
        self._configure_ok()
        recorded = self._record_preview(self._judgment_dict())
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]
        envelope = JournalStore(self.state_root).read_envelope(journal_key)

        projected = self._run_sync_context("create", journal_key)

        self.assertEqual(0, projected.returncode, projected.stderr)
        page = json.loads(projected.stdout)["tool_input"]["pages"][0]
        self.assertEqual(
            {
                "Title": "Prefer user-invoked journal entries",
                "Journal Key": journal_key,
                "date:Recorded At:start": envelope.recorded_at,
                "date:Recorded At:is_datetime": 1,
                "AI Contribution": "AI-assisted",
            },
            page["properties"],
        )
        self.assertEqual(
            "## \ubc30\uacbd\n\n"
            "ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n\n"
            "## \uc65c \uc9c0\uae08\n\n"
            "Automatic pending records became reading debt\n\n"
            "## \ubb34\uc5c7\uc774 \ub2ec\ub77c\uc84c\ub098\n\n"
            "Unknown\n\n"
            "## \ubb34\uc5c7\uc744 \ud310\ub2e8\ud588\ub098\n\n"
            "Require an explicit user choice before capture\n\n"
            "## \ubb34\uc5c7\uc744 \uac10\uc218\ud558\uac70\ub098 \uc81c\uc678\ud588\ub098\n\n"
            "None\n\n"
            "## \ubb34\uc5c7\uc774 \uc774 \ud310\ub2e8\uc744 \ubc14\uafc0\uae4c\n\n"
            "Skipped\n\n"
            "## \uadfc\uac70\n\n"
            "- `docs/designs/journal.md`",
            page["content"],
        )

    def test_v2_write_guard_rejects_a_local_only_property(self):
        self._configure_ok()
        recorded = self._record_preview(self._judgment_dict())
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]
        envelope = JournalStore(self.state_root).read_envelope(journal_key)
        projected = self._run_sync_context("create", journal_key)
        self.assertEqual(0, projected.returncode, projected.stderr)
        tool_input = json.loads(projected.stdout)["tool_input"]
        tool_input["pages"][0]["properties"]["Repository"] = envelope.repository

        denied = self._run(
            "hook",
            input_json=self._tool_event("PreToolUse", tool_input),
            cwd=REPO_ROOT,
        )

        self.assertEqual(0, denied.returncode, denied.stderr)
        self.assertEqual(
            "deny",
            json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"],
        )
        self.assertEqual(
            "pending",
            JournalStore(self.state_root).read_envelope(journal_key).sync_state,
        )

    def test_v2_superseding_projection_passes_the_write_guard(self):
        self._configure_ok()
        original = self._record_preview(self._judgment_dict())
        self.assertEqual(0, original.returncode, original.stderr)
        original_key = json.loads(original.stdout)["journal_key"]
        correction = self._judgment_dict()
        correction["human_judgment"] = "Require a user choice and an exact preview"
        correction["supersedes"] = original_key
        corrected = self._record_preview(correction)
        self.assertEqual(0, corrected.returncode, corrected.stderr)
        corrected_key = json.loads(corrected.stdout)["journal_key"]
        projected = self._run_sync_context("create", corrected_key)
        self.assertEqual(0, projected.returncode, projected.stderr)
        tool_input = json.loads(projected.stdout)["tool_input"]

        guarded = self._run(
            "hook",
            input_json=self._tool_event("PreToolUse", tool_input),
            cwd=REPO_ROOT,
        )

        self.assertEqual(0, guarded.returncode, guarded.stderr)
        self.assertEqual({}, json.loads(guarded.stdout))
        self.assertEqual(
            "## \ubc30\uacbd\n\n"
            "ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n\n"
            "## \uc65c \uc9c0\uae08\n\n"
            "Automatic pending records became reading debt\n\n"
            "## \ubb34\uc5c7\uc774 \ub2ec\ub77c\uc84c\ub098\n\n"
            "Unknown\n\n"
            "## \ubb34\uc5c7\uc744 \ud310\ub2e8\ud588\ub098\n\n"
            "Require a user choice and an exact preview\n\n"
            "## \ubb34\uc5c7\uc744 \uac10\uc218\ud558\uac70\ub098 \uc81c\uc678\ud588\ub098\n\n"
            "None\n\n"
            "## \ubb34\uc5c7\uc774 \uc774 \ud310\ub2e8\uc744 \ubc14\uafc0\uae4c\n\n"
            "Skipped\n\n"
            "## \uadfc\uac70\n\n"
            "- `docs/designs/journal.md`\n\n"
            f"## \ub300\uccb4\ud558\ub294 \uc774\uc804 \uae30\ub85d\n\n`{original_key}`",
            tool_input["pages"][0]["content"],
        )
        self.assertEqual(
            original_key,
            JournalStore(self.state_root)
            .read_envelope(corrected_key)
            .draft.supersedes,
        )

    def test_v2_empty_evidence_projection_is_explicit(self):
        self._configure_ok()
        judgment = self._judgment_dict()
        judgment["evidence_pointers"] = []
        recorded = self._record_preview(judgment)
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]

        projected = self._run_sync_context("create", journal_key)

        self.assertEqual(0, projected.returncode, projected.stderr)
        content = json.loads(projected.stdout)["tool_input"]["pages"][0]["content"]
        self.assertEqual(
            "## \ubc30\uacbd\n\n"
            "ClaimBranch was defining how one coding judgment reaches its user-controlled Notion journal\n\n"
            "## \uc65c \uc9c0\uae08\n\n"
            "Automatic pending records became reading debt\n\n"
            "## \ubb34\uc5c7\uc774 \ub2ec\ub77c\uc84c\ub098\n\n"
            "Unknown\n\n"
            "## \ubb34\uc5c7\uc744 \ud310\ub2e8\ud588\ub098\n\n"
            "Require an explicit user choice before capture\n\n"
            "## \ubb34\uc5c7\uc744 \uac10\uc218\ud558\uac70\ub098 \uc81c\uc678\ud588\ub098\n\n"
            "None\n\n"
            "## \ubb34\uc5c7\uc774 \uc774 \ud310\ub2e8\uc744 \ubc14\uafc0\uae4c\n\n"
            "Skipped\n\n"
            "## \uadfc\uac70\n\n"
            "- \uc5c6\uc74c",
            content,
        )

    def test_v2_existing_page_update_is_denied_without_acknowledgement(self):
        self._configure_ok()
        recorded = self._record_preview(self._judgment_dict())
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]
        projected = self._run_sync_context("create", journal_key)
        self.assertEqual(0, projected.returncode, projected.stderr)
        page = json.loads(projected.stdout)["tool_input"]["pages"][0]
        tool_input = {
            "page_id": "human-edited-page", "command": "replace_content",
            "new_str": page["content"], "properties": page["properties"], "allow_async": False,
        }
        store = JournalStore(self.state_root)
        before = store.read_envelope(journal_key).to_storage_dict()
        event = self._tool_event("PreToolUse", tool_input)
        event["tool_name"] = "mcp__notion__notion-update-page"
        guarded = self._run("hook", input_json=event)
        self.assertEqual(0, guarded.returncode, guarded.stderr)
        self.assertEqual("deny", json.loads(guarded.stdout)["hookSpecificOutput"]["permissionDecision"])

        event["hook_event_name"] = "PostToolUse"
        event["tool_response"] = {"page": {
            "id": "human-edited-page", "url": "https://www.notion.so/human-edited-page",
        }}
        ignored = self._run("hook", input_json=event)
        self.assertEqual(0, ignored.returncode, ignored.stderr)
        self.assertEqual({}, json.loads(ignored.stdout))
        self.assertEqual(before, store.read_envelope(journal_key).to_storage_dict())
        self.assertIsNone(store.read_receipt(journal_key))

    def test_v2_post_write_receipt_marks_the_exact_envelope_synced(self):
        self._configure_ok()
        recorded = self._record_preview(self._judgment_dict())
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        journal_key = json.loads(recorded.stdout)["journal_key"]
        projected = self._run_sync_context("create", journal_key)
        self.assertEqual(0, projected.returncode, projected.stderr)
        tool_input = json.loads(projected.stdout)["tool_input"]
        event = self._tool_event("PostToolUse", tool_input)
        event["tool_response"] = {
            "pages": [
                {
                    "id": "v2-page-result",
                    "url": "https://www.notion.so/v2-page-result",
                }
            ]
        }

        acknowledged = self._run(
            "hook", input_json=event, cwd=REPO_ROOT
        )

        self.assertEqual(0, acknowledged.returncode, acknowledged.stderr)
        self.assertEqual({}, json.loads(acknowledged.stdout))
        store = JournalStore(self.state_root)
        envelope = store.read_envelope(journal_key)
        self.assertEqual("synced", envelope.sync_state)
        receipt = store.list_receipts()[0]
        self.assertEqual(journal_key, receipt.journal_key)
        self.assertEqual("v2-page-result", receipt.page_id)

    def test_unknown_subcommand_exits_two(self):
        result = self._run("unknown-command")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)

    def test_stop_ignores_legacy_local_state_errors_and_never_claims_pending(self):
        store = JournalStore(self.state_root)
        store.create_session("session-cli", self.baseline, SEOUL_NOW)
        session_file = tuple((self.state_root / "sessions").glob("*.json"))[0]
        session_file.write_bytes(b"{broken")
        self.repo.write_text("changed.md", "material change\n")

        result = self._run("hook", input_json=self._stop_event(), cwd=REPO_ROOT)

        self.assertEqual(0, result.returncode)
        self.assertEqual({}, json.loads(result.stdout))
        self.assertEqual((), JournalStore(self.state_root).list_pending())

    def test_legacy_lifecycle_hooks_are_noops_when_the_old_cwd_is_gone(self):
        with TemporaryDirectory() as temporary_root:
            missing_cwd = Path(temporary_root) / "deleted-worktree"
            for hook_name in ("SessionStart", "Stop"):
                with self.subTest(hook_name=hook_name):
                    event = (
                        self._session_event()
                        if hook_name == "SessionStart"
                        else self._stop_event()
                    )
                    event["cwd"] = str(missing_cwd)

                    result = self._run("hook", input_json=event, cwd=REPO_ROOT)

                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual({}, json.loads(result.stdout))
                    self.assertEqual("", result.stderr)
        self.assertEqual((), tuple(self.state_root.iterdir()))

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
            git_failure = self._record_preview(self._judgment_dict(), cwd=Path(non_repo))

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
        env=None,
    ):
        if input_json is not None:
            input_text = json.dumps(input_json)
        return subprocess.run(
            [sys.executable, "-m", "scripts.notion_journal.cli", *args],
            cwd=cwd,
            input=input_text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=self.env if env is None else env,
        )

    def _preview_judgment(self, judgment):
        return self._run(
            "preview-judgment", "--journal-language", "ko",
            "--input-json", "-", "--format", "json",
            input_json=judgment,
        )

    def _record_preview(self, judgment, *, cwd=None):
        preview = self._preview_judgment(judgment)
        self.assertEqual(0, preview.returncode, preview.stderr)
        return self._run(
            "record-judgment", "--input-token", "-", "--format", "json",
            input_text=json.loads(preview.stdout)["capture_token"],
            cwd=self.repo.path if cwd is None else cwd,
        )

    def _configuration_args(self):
        return (
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

    def _configure(self, journal_language: str = "ko"):
        return self._run(
            *self._configuration_args(),
            "--journal-language",
            journal_language,
        )

    def _configure_ok(self, journal_language: str = "ko"):
        result = self._configure(journal_language)
        self.assertEqual(0, result.returncode, result.stderr)

    def _run_sync_context(self, action: str, journal_key: str):
        return subprocess.run(
            [
                sys.executable,
                str(
                    REPO_ROOT
                    / ".agents"
                    / "skills"
                    / "record-notion-journal"
                    / "scripts"
                    / "sync_context.py"
                ),
                action,
                "--journal-key",
                journal_key,
            ],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=self.env,
        )

    def _prepare_pending(self, *, attach_draft: bool = False):
        self.repo.write_text("changed.md", "material change\n")
        store = JournalStore(self.state_root)
        store.create_session("session-cli", self.baseline, SEOUL_NOW)
        current = capture_snapshot(self.repo.path)
        changes = compare_snapshots(self.repo.path, self.baseline, current)
        envelope = store.capture_pending("session-cli", current, changes, SEOUL_NOW)
        if attach_draft:
            envelope = store.attach_draft(envelope.journal_key, self._draft())
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

    def _draft(self):
        value = self._draft_dict()
        return JournalDraft(
            title=value["title"],
            purpose=value["purpose"],
            outcome=value["outcome"],
            key_decisions=tuple(value["key_decisions"]),
            verification=tuple(
                VerificationItem(item["command"], item["outcome"])
                for item in value["verification"]
            ),
            risks=tuple(value["risks"]),
            next_safe_action=value["next_safe_action"],
            task_status=value["task_status"],
            change_types=tuple(value["change_types"]),
            ai_contribution=value["ai_contribution"],
            verification_status=value["verification_status"],
        )

    def _judgment_dict(self):
        return {
            "title": "Prefer user-invoked journal entries",
            "background": (
                "ClaimBranch was defining how one coding judgment reaches its "
                "user-controlled Notion journal"
            ),
            "why_now": "Automatic pending records became reading debt",
            "understanding_shift": "Unknown",
            "human_judgment": "Require an explicit user choice before capture",
            "tradeoff_boundary": "None",
            "revisit_signal": "Skipped",
            "evidence_pointers": ["docs/designs/journal.md"],
            "ai_contribution": "AI-assisted",
            "supersedes": None,
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
