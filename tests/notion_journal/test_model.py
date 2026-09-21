import unittest

from scripts.notion_journal import model
from scripts.notion_journal.model import (
    JournalDraft,
    PathState,
    ValidationError,
    VerificationItem,
    canonical_json,
    sanitize_agent_text,
)


class ModelTest(unittest.TestCase):
    def _judgment_draft_type(self):
        draft_type = getattr(model, "JudgmentDraft", None)
        self.assertIsNotNone(draft_type, "JudgmentDraft must be part of the model API")
        return draft_type

    def test_judgment_draft_accepts_confirmed_sparse_values_and_evidence(self):
        draft_type = self._judgment_draft_type()

        draft = draft_type(
            title="Prefer user-invoked journal entries",
            background=(
                "ClaimBranch was defining how one coding judgment reaches its "
                "user-controlled Notion journal"
            ),
            why_now="Automatic pending records became reading debt",
            understanding_shift="Unknown",
            human_judgment="Require an explicit user choice before capture",
            tradeoff_boundary="None",
            revisit_signal="Skipped",
            evidence_pointers=("docs\\designs\\journal.md",),
            ai_contribution="AI-assisted",
            supersedes=None,
        )

        self.assertEqual(("docs/designs/journal.md",), draft.evidence_pointers)
        self.assertIn("ClaimBranch", draft.background)
        self.assertEqual("Unknown", draft.understanding_shift)
        self.assertIsNone(draft.supersedes)

    def test_legacy_judgment_draft_may_lack_background_in_memory(self):
        draft_type = self._judgment_draft_type()

        legacy = draft_type(
            title="Prefer user-invoked journal entries",
            why_now="Automatic pending records became reading debt",
            understanding_shift="The capture unit is a human judgment",
            human_judgment="Require an explicit user choice before capture",
            tradeoff_boundary="No automatic task summaries",
            revisit_signal="Users repeatedly request automatic capture",
            evidence_pointers=(),
            ai_contribution="AI-assisted",
            supersedes=None,
        )

        self.assertIsNone(legacy.background)

    def test_journal_language_accepts_only_the_explicit_closed_enum(self):
        validate = getattr(model, "validate_journal_language", None)
        self.assertTrue(callable(validate), "model must expose language validation")
        self.assertEqual("ko", validate("ko"))
        self.assertEqual("en", validate("en"))
        self.assertIsNone(validate(None, allow_legacy=True))
        for invalid in (None, "auto", "KO", " Korean ", ""):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    validate(invalid)

    def test_judgment_draft_requires_every_semantic_field(self):
        draft_type = self._judgment_draft_type()

        with self.assertRaises(ValidationError):
            draft_type(
                title="Prefer user-invoked journal entries",
                background="",
                why_now="Automatic pending records became reading debt",
                understanding_shift="The capture unit is a human judgment",
                human_judgment="Require an explicit user choice before capture",
                tradeoff_boundary="No automatic task summaries",
                revisit_signal="Users repeatedly request automatic capture",
                evidence_pointers=(),
                ai_contribution="AI-assisted",
                supersedes=None,
            )

    def test_judgment_draft_rejects_non_tuple_or_unsafe_evidence(self):
        draft_type = self._judgment_draft_type()
        common = {
            "title": "Prefer user-invoked journal entries",
            "background": "ClaimBranch was defining its journal authority boundary",
            "why_now": "Automatic pending records became reading debt",
            "understanding_shift": "The capture unit is a human judgment",
            "human_judgment": "Require an explicit user choice before capture",
            "tradeoff_boundary": "No automatic task summaries",
            "revisit_signal": "Users repeatedly request automatic capture",
            "ai_contribution": "AI-assisted",
            "supersedes": None,
        }

        for evidence in ("docs/design.md", ("../outside.md",), ("C:/Users/a.md",)):
            with self.subTest(evidence=evidence), self.assertRaises(ValidationError):
                draft_type(evidence_pointers=evidence, **common)

    def test_judgment_draft_accepts_only_v1_or_v2_supersedes_keys(self):
        draft_type = self._judgment_draft_type()
        common = {
            "title": "Correct a prior journal entry",
            "background": "A retained ClaimBranch journal judgment needs correction",
            "why_now": "New evidence changed the boundary",
            "understanding_shift": "The earlier boundary was too broad",
            "human_judgment": "Narrow the boundary",
            "tradeoff_boundary": "Keep the original record visible",
            "revisit_signal": "A broader boundary proves necessary",
            "evidence_pointers": (),
            "ai_contribution": "AI-assisted",
        }

        for prefix in ("cbj-v1-", "cbj-v2-"):
            draft = draft_type(supersedes=prefix + "a" * 24, **common)
            self.assertEqual(prefix + "a" * 24, draft.supersedes)

        for invalid in ("cbj-v3-" + "a" * 24, "cbj-v2-short", "not-a-key"):
            with self.subTest(supersedes=invalid), self.assertRaises(ValidationError):
                draft_type(supersedes=invalid, **common)

    def test_path_state_normalizes_repository_path(self):
        state = PathState("docs\\plan.md", "tracked", "a" * 64)
        self.assertEqual("docs/plan.md", state.path)

    def test_absolute_and_parent_paths_are_rejected(self):
        for value in ("C:/Users/alice/secret.txt", "../secret.txt", "/tmp/x"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                PathState(value, "tracked", "a" * 64)

    def test_secret_like_agent_text_is_rejected(self):
        for value in (
            "Authorization" + ": Bearer fixture",
            "API_" + "KEY=fixture",
            "C:\\Users\\alice",
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                sanitize_agent_text(value, field="summary")

    def test_additional_private_paths_and_credential_assignments_are_rejected(self):
        for value in (
            r"\\server\share\record.md",
            "//server/share/record.md",
            "/root/.ssh/id_rsa",
            "Inspect /etc/passwd",
            "AWS_SECRET_ACCESS_" + "KEY=fixture",
            "GH_TOKEN_" + "VALUE=fixture",
            "https://alice:fixture@example.test/private",
            "DATABASE_URL=postgres://alice:fixture@db.example.test/main",
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                sanitize_agent_text(value, field="judgment")

    def test_https_text_is_not_misclassified_as_an_absolute_path(self):
        value = "Use https://docs.example.test/reference for the public contract"
        self.assertEqual(value, sanitize_agent_text(value, field="judgment"))

    def test_judgment_draft_applies_the_private_text_boundary(self):
        draft_type = self._judgment_draft_type()
        common = {
            "title": "Keep private machine context out of the journal",
            "background": "ClaimBranch was defining portable journal context",
            "understanding_shift": "The record must remain portable",
            "human_judgment": "Reject machine-specific context",
            "tradeoff_boundary": "Keep only repository-relative evidence",
            "revisit_signal": "A safe portable reference format is available",
            "evidence_pointers": (),
            "ai_contribution": "AI-assisted",
            "supersedes": None,
        }
        for unsafe in (
            r"\\server\share\record.md",
            "//server/share/record.md",
            "/root/private.txt",
            "https://alice:fixture@example.test/private",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValidationError):
                draft_type(why_now=unsafe, **common)

    def test_judgment_background_uses_the_private_text_boundary(self):
        draft_type = self._judgment_draft_type()
        with self.assertRaises(ValidationError):
            draft_type(
                title="Keep private machine context out of the journal",
                background=r"C:\Users\alice\private context",
                why_now="Machine-specific context is not portable",
                understanding_shift="The record must remain portable",
                human_judgment="Reject machine-specific context",
                tradeoff_boundary="Keep only repository-relative evidence",
                revisit_signal="A safe portable reference format is available",
                evidence_pointers=(),
                ai_contribution="AI-assisted",
                supersedes=None,
            )

    def test_judgment_draft_total_size_budget_does_not_expand_for_background(self):
        draft_type = self._judgment_draft_type()
        with self.assertRaises(ValidationError):
            draft_type(
                title="Keep the fixed reading budget",
                background="b" * 1000,
                why_now="w" * 1000,
                understanding_shift="u" * 1000,
                human_judgment="j" * 1000,
                tradeoff_boundary="t" * 1000,
                revisit_signal="r" * 1000,
                evidence_pointers=(),
                ai_contribution="AI-assisted",
                supersedes=None,
            )

    def test_multiline_markdown_is_allowed_but_other_controls_are_rejected(self):
        self.assertEqual(
            "Purpose\nOutcome",
            sanitize_agent_text("Purpose\nOutcome", field="page body"),
        )
        for value in ("bad\rline", "bad\x00value", "bad\tvalue"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                sanitize_agent_text(value, field="page body")

    def test_canonical_json_is_sorted_utf8_without_ascii_escaping(self):
        self.assertEqual(
            b'{"a":"\xed\x95\x9c\xea\xb8\x80","z":1}',
            canonical_json({"z": 1, "a": "한글"}),
        )

    def test_journal_draft_rejects_secret_like_prose(self):
        with self.assertRaises(ValidationError):
            JournalDraft(
                title="Finish journal plan",
                purpose="Record the coding outcome",
                outcome="Authorization" + ": Bearer fixture",
                key_decisions=("Keep write approval",),
                verification=(VerificationItem("python tests", "Passed"),),
                risks=("OAuth is interactive",),
                next_safe_action="Run the next task",
                task_status="Completed",
                change_types=("docs",),
                ai_contribution="AI-assisted",
                verification_status="Passed",
            )

    def test_journal_draft_rejects_scalar_where_item_tuple_is_required(self):
        with self.assertRaises(ValidationError):
            JournalDraft(
                title="Finish journal plan",
                purpose="Record the coding outcome",
                outcome="The bounded record is ready",
                key_decisions="x",
                verification=(VerificationItem("python tests", "Passed"),),
                risks=("OAuth is interactive",),
                next_safe_action="Run the next task",
                task_status="Completed",
                change_types=("docs",),
                ai_contribution="AI-assisted",
                verification_status="Passed",
            )


if __name__ == "__main__":
    unittest.main()
