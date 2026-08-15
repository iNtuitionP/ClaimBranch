import unittest

from scripts.notion_journal.model import (
    JournalDraft,
    PathState,
    ValidationError,
    VerificationItem,
    canonical_json,
    sanitize_agent_text,
)


class ModelTest(unittest.TestCase):
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
