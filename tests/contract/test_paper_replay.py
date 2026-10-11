from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import unittest

from claimbranch.application.cli import main
from claimbranch.core.canonical import decode
from scripts.replay_paper_history import replay_fixture


class PaperReplayTests(unittest.TestCase):
    def test_manual_and_recorded_are_distinct_audits_of_the_same_synthetic_paper(self):
        manual, recorded = (replay_fixture(variant) for variant in ("manual", "recorded"))
        self.assertNotEqual(manual.manifest(), recorded.manifest())
        for key in ("claims", "evidence", "experiments"):
            self.assertEqual(manual.view("main")[key], recorded.view("main")[key])
        self.assertEqual(["human", "ai", "human"], [item["contributor"] for item in recorded.view("main")["judgment"]["history"]])
        self.assertEqual("deferred", decode(recorded.manifest())["selected_merges"][0]["disposition"])
        self.assertEqual("percentage points", manual.view("main")["experiments"][0]["metric"]["unit"])
        self.assertEqual(4, len(manual.view("main")["claims"]))

    def test_cli_returns_paper_or_hypothetical_impact_without_an_endpoint(self):
        for scenario in (None, "supports", "challenges", "inconclusive"):
            output = StringIO()
            args = ["demo", "paper", "--variant", "recorded", "--json"]
            if scenario:
                args += ["--scenario", scenario]
            with self.subTest(scenario=scenario), redirect_stdout(output):
                self.assertEqual(0, main(args))
            value = json.loads(output.getvalue())
            self.assertFalse(value["authorization_verified"])
            self.assertEqual("hypothetical" if scenario else "unverified-candidate", value["authority"])

    def test_generated_schemas_match_the_contract(self):
        result = subprocess.run([sys.executable, "-m", "scripts.export_research_schema", "--check"],
                                cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
