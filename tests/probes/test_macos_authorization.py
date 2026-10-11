"""Probe reporting cannot turn capabilities or partial native output into authority."""
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import patch

from scripts.probes.macos_authorization import ProbeError, decode_result, probe, temporary_root


class MacAuthorizationTests(unittest.TestCase):
    def result(self, value, code=0):
        return subprocess.CompletedProcess([], code, json.dumps(value), "")

    def test_non_mac_host_never_invokes_native_tools(self):
        with patch("scripts.probes.macos_authorization.sys.platform", "win32"), \
                patch("scripts.probes.macos_authorization.subprocess.run") as run:
            self.assertEqual("unsupported", probe(review=True)["status"])
            run.assert_not_called()

    def test_capability_discovery_cannot_claim_product_authorization(self):
        with self.assertRaises(ProbeError):
            decode_result(self.result({"status": "available", "authorization_verified": True}))

    def test_partial_match_or_failed_native_exit_is_rejected(self):
        result = {"status": "matched", "authorization_verified": False,
                  "presence_verified": True, "signature_verified": True,
                  "private_export_denied": True, "key_storage": "ephemeral",
                  "persistent_custody_verified": False}
        for key in ("presence_verified", "signature_verified", "private_export_denied"):
            with self.subTest(key=key), self.assertRaises(ProbeError):
                decode_result(self.result(dict(result, **{key: False})))
        with self.assertRaises(ProbeError):
            decode_result(self.result(result, code=1))

    def test_invalid_native_json_and_unknown_status_are_not_success(self):
        for stdout in ("not json", "[]", "{}", '{"status":"invented","authorization_verified":false}'):
            with self.subTest(stdout=stdout), self.assertRaises(ProbeError):
                decode_result(subprocess.CompletedProcess([], 0, stdout, ""))

    def test_cancelled_result_never_retains_successful_signature(self):
        with self.assertRaises(ProbeError):
            decode_result(self.result({"status": "cancelled", "authorization_verified": False,
                                       "presence_verified": True, "signature_verified": True}))

    def test_temp_root_in_git_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            child = root / "child"
            child.mkdir()
            with patch("scripts.probes.macos_authorization.tempfile.gettempdir", return_value=str(child)):
                with self.assertRaises(ProbeError):
                    temporary_root()

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/xcrun").exists(), "macOS SDK check")
    def test_native_capability_query_and_domain_specific_cancellation_mapping(self):
        result = probe()
        self.assertIn(result["status"], ("available", "unavailable"))
        self.assertFalse(result["authorization_verified"])
        self.assertTrue(result["cancellation_mapping_verified"])


if __name__ == "__main__":
    unittest.main()
