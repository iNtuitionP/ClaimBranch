"""Independent scientific oracles for frozen portable histories and audit goldens."""
from contextlib import redirect_stdout
from io import StringIO
import json
from unittest.mock import patch
import unittest

from claimbranch.core.canonical import ContractError
from scripts.replay_research_history import main, replay_fixture


class ResearchReplayTests(unittest.TestCase):
    def test_manual_and_recorded_goldens_preserve_the_mixed_scientific_result(self):
        for variant in ("manual", "recorded"):
            with self.subTest(variant=variant):
                history = replay_fixture(variant)
                view = history.view("main")
                self.assertEqual("contested", view["claim"]["status"])
                self.assertEqual(["O-01", "O-02", "O-03"], [item["id"] for item in view["evidence"]])
                relations = {item["body"]["source_id"]: item["body"]["edge_type"] for item in view["changes"] if item["kind"] == "scientific-edge"}
                self.assertEqual({"O-01": "challenges", "O-02": "challenges", "O-03": "qualifies"}, relations)
                self.assertEqual([], view["experiment_plans"])
                manifest = json.loads(history.manifest())
                self.assertEqual(["optional-experiment"], manifest["selected_merges"][0]["preview"]["selection"]["omitted"])
                self.assertIn(["I-01", "claim-status", "C-01", "A-01"], manifest["selected_merges"][0]["preview"]["impact_paths"])
                self.assertEqual("unverified-candidate", manifest["authority"])

    def test_ai_original_and_human_revision_survive_replay_and_explanation_deferral(self):
        recorded = json.loads(replay_fixture("recorded").manifest())
        merge = recorded["selected_merges"][0]
        history = merge["judgment"]["history"]
        self.assertEqual(["ai", "human"], [item["contributor"] for item in history])
        self.assertEqual("P-01", history[0]["proposal_id"])
        self.assertIn("may also depend", history[0]["text"])
        self.assertIn("also depends", history[1]["text"])
        self.assertEqual("deferred", merge["disposition"])
        manual = json.loads(replay_fixture("manual").manifest())
        self.assertEqual("not-required", manual["selected_merges"][0]["disposition"])
        self.assertEqual(["human"], [item["contributor"] for item in manual["views"]["main"]["judgment"]["history"]])

    def test_cli_verifies_both_without_a_provider_or_authorization(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main([]))
        result = json.loads(output.getvalue())
        self.assertEqual(["manual", "recorded"], [item["variant"] for item in result])
        self.assertTrue(all(item["golden_match"] for item in result))
        self.assertTrue(all(item["authorization_verified"] is False for item in result))

    def test_cli_reports_failure_instead_of_success_when_a_golden_differs(self):
        output = StringIO()
        with patch("scripts.replay_research_history.replay_fixture", side_effect=ContractError("golden differs")), redirect_stdout(output):
            self.assertEqual(1, main(["--variant", "manual"]))
        self.assertEqual("error", json.loads(output.getvalue())["status"])

    def test_malformed_fixture_containers_return_an_error_without_traceback(self):
        for raw in (b'[{}]', b'{"profile":"portable-research/v1","seed":{},"commands":42}'):
            output = StringIO()
            with self.subTest(raw=raw), patch("pathlib.Path.read_bytes", return_value=raw), redirect_stdout(output):
                self.assertEqual(1, main(["--variant", "manual"]))
                self.assertEqual("error", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
