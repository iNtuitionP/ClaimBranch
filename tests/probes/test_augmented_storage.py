"""End-to-end synthetic judgment-to-storage crash/retry, not accepted state."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from scripts.contracts.first_pass import prepare_review, record_judgment, start_draft
from scripts.probes.workspace_storage import ProbeError, WorkspaceProbe


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/saturation/augmented-cases.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
CHILD = """
import json, os, sys
from pathlib import Path
from scripts.contracts.first_pass import prepare_review, record_judgment, start_draft
from scripts.probes.workspace_storage import WorkspaceProbe
fixture = json.loads(Path(sys.argv[5]).read_text(encoding='utf-8'))
draft = record_judgment(start_draft('synthetic-project', 'episode-one',
    fixture['context'], fixture['claim']), fixture['judgment'], fixture['rationale'])
review = prepare_review(draft)
probe = WorkspaceProbe.for_project(*(Path(value) for value in sys.argv[1:4]), 'synthetic-project')
def checkpoint(phase):
    if phase == sys.argv[4]:
        os._exit(23)
probe.save_judgment('synthetic-project', fixture['cases']['crash-and-retry']['key'],
    review.draft.interpretation, review.draft.rationale, checkpoint)
"""


class AugmentedStorageTests(unittest.TestCase):
    def test_first_pass_judgment_survives_crash_and_retry_without_second_entry(self):
        case = FIXTURE["cases"]["crash-and-retry"]
        for cut in case["cuts"]:
            with self.subTest(phase=cut["phase"]), tempfile.TemporaryDirectory(
                prefix="claimbranch-storage-probe-"
            ) as scratch:
                sandbox = Path(scratch).resolve()
                paper = sandbox / "paper"
                paper.mkdir()
                (paper / ".git").mkdir()
                manuscript = paper / "paper.tex"
                manuscript.write_bytes(b"synthetic manuscript, never modified")
                workspaces = sandbox / "workspaces"
                workspaces.mkdir()
                probe = WorkspaceProbe.for_project(sandbox, workspaces, paper, "synthetic-project")
                probe.initialize("synthetic-project")
                probe.save_judgment("synthetic-project", "prior", "previous choice", "previous reason")

                child = subprocess.run(
                    [sys.executable, "-c", CHILD, str(sandbox), str(workspaces), str(paper),
                     cut["phase"], str(FIXTURE_PATH)], cwd=ROOT, capture_output=True, timeout=20,
                )
                self.assertEqual(23, child.returncode, child.stderr.decode(errors="replace"))
                reopened = WorkspaceProbe.for_project(sandbox, workspaces, paper, "synthetic-project")
                expected = (FIXTURE["judgment"], FIXTURE["rationale"])
                self.assertEqual(expected if cut["expected_present"] else None,
                                 reopened.read_judgment("synthetic-project", case["key"]))
                self.assertEqual(("previous choice", "previous reason"),
                                 reopened.read_judgment("synthetic-project", "prior"))

                draft = record_judgment(start_draft("synthetic-project", "episode-one",
                    FIXTURE["context"], FIXTURE["claim"]), *expected)
                review = prepare_review(draft)
                for _ in range(2):
                    reopened.save_judgment("synthetic-project", case["key"],
                                           review.draft.interpretation, review.draft.rationale)
                with self.assertRaises(ProbeError):
                    reopened.save_judgment("synthetic-project", case["key"], "replacement", expected[1])
                self.assertEqual(expected, reopened.read_judgment("synthetic-project", case["key"]))
                with closing(sqlite3.connect(reopened.workspace / "probe.sqlite3")) as connection:
                    self.assertEqual(case["expected_rows_after_retry"],
                                     connection.execute("SELECT COUNT(*) FROM judgments").fetchone()[0])
                self.assertEqual(b"synthetic manuscript, never modified", manuscript.read_bytes())


if __name__ == "__main__":
    unittest.main()
