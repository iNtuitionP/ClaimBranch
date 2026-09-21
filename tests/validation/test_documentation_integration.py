from __future__ import annotations

from pathlib import Path
import unittest

from scripts import check_docs


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "saturation"
    / "truth-packet"
    / "decision-log-baseline.md"
)


class TruthPacketDocumentationIntegrationTests(unittest.TestCase):
    def test_committed_decision_log_baseline_is_an_allowed_fixture(self) -> None:
        errors: list[str] = []

        check_docs.check_managed_location(BASELINE, errors)

        self.assertEqual([], errors)

    def test_other_test_markdown_remains_rejected(self) -> None:
        errors: list[str] = []

        check_docs.check_managed_location(
            REPOSITORY_ROOT / "tests" / "fixtures" / "other-notes.md", errors
        )

        self.assertEqual(1, len(errors))
        self.assertIn("outside docs", errors[0])


if __name__ == "__main__":
    unittest.main()
