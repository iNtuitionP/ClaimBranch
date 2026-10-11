"""The fixed demo joins A1–A4 without touching projects or using a provider."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.authority_demo import run_demo
from scripts.check_truth_packet import DEFAULT_PACKET


ROOT = Path(__file__).resolve().parents[2]


class AuthorityDemoTests(unittest.TestCase):
    def test_two_complete_histories_keep_fixture_and_clean_sandbox(self):
        fixtures = {path: path.read_bytes() for path in Path(DEFAULT_PACKET).iterdir() if path.is_file()}
        before = set(Path(tempfile.gettempdir()).glob("claimbranch-storage-probe-*"))
        with patch("socket.socket.connect", side_effect=AssertionError("no network permitted")):
            result = run_demo()
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["authorization_verified"])
        self.assertFalse(result["compile_verified"])
        self.assertFalse(result["debt_closed"])
        self.assertEqual(["manual", "frozen"], [history["mode"] for history in result["histories"]])
        for history in result["histories"]:
            self.assertEqual(1, history["record_count"])
            self.assertTrue(history["retry_same_record"])
            self.assertTrue(history["manuscript_applied"])
            self.assertTrue(history["manuscript_restored"])
            self.assertEqual("contested", history["graph_after"]["claim"]["status"])
            self.assertEqual(3, len(history["graph_after"]["relationships"]))
            self.assertEqual("restored", history["record"]["patch_state"])
            self.assertEqual(history["rationale"], history["record"]["payload"]["review"]["draft"]["rationale"])
        self.assertIsNone(result["histories"][0]["record"]["payload"]["proposal"])
        self.assertFalse(result["histories"][1]["record"]["payload"]["proposal"]["accepted"])
        self.assertEqual(0, result["provider_calls"])
        self.assertEqual(before, set(Path(tempfile.gettempdir()).glob("claimbranch-storage-probe-*")))
        self.assertEqual(fixtures, {path: path.read_bytes() for path in fixtures})

    def test_cli_json_is_single_machine_readable_result(self):
        result = subprocess.run([sys.executable, "-B", "-m", "scripts.authority_demo", "--format", "json"],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertEqual(2, len(json.loads(result.stdout)["histories"]))

    def test_cli_does_not_accept_a_real_manuscript_or_endpoint(self):
        for option in ("--paper", "--endpoint"):
            result = subprocess.run([sys.executable, "-B", "-m", "scripts.authority_demo", option, "forbidden"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(2, result.returncode)
