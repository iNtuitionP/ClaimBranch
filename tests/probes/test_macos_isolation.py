"""Observation/cleanup rules without creating an OS application container."""
from copy import deepcopy
import errno
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.probes.macos_authorization import ProbeError
from scripts.probes.macos_isolation import assess, probe


class MacIsolationTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {kind: {"allowed": True, "errno": 0} for kind in ("read", "write", "network")}
        self.denied = {kind: {"allowed": False, "errno": errno.EPERM} for kind in self.baseline}

    def test_observed_denial_never_claims_provider_or_approval_protection(self):
        result = assess(self.baseline, self.denied, True)
        self.assertEqual("denial_observed", result["status"])
        self.assertFalse(result["provider_isolation_verified"])
        self.assertFalse(result["authorization_verified"])

    def test_absent_file_or_refused_connection_is_not_an_access_denial(self):
        for code in (errno.ENOENT, errno.ECONNREFUSED, 0, True):
            denied = deepcopy(self.denied)
            denied["read"]["errno"] = code
            with self.subTest(code=code), self.assertRaises(ProbeError):
                assess(self.baseline, denied, True)

    def test_each_resource_needs_baseline_access_and_denied_restricted_access(self):
        for kind in self.baseline:
            with self.subTest(kind=kind):
                baseline = deepcopy(self.baseline)
                baseline[kind]["allowed"] = False
                with self.assertRaises(ProbeError):
                    assess(baseline, self.denied, True)
                denied = deepcopy(self.denied)
                denied[kind] = self.baseline[kind]
                with self.assertRaises(ProbeError):
                    assess(self.baseline, denied, True)

    def test_changed_protected_bytes_reject_the_result(self):
        with self.assertRaises(ProbeError):
            assess(self.baseline, self.denied, False)

    def test_pending_cleanup_prevents_build_sign_or_another_container(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            container = root / "Library/Containers/org.claimbranch.sandboxprobe.owned"
            container.mkdir(parents=True)
            with patch("scripts.probes.macos_isolation.sys.platform", "darwin"), \
                    patch("scripts.probes.macos_isolation.Path.home", return_value=root), \
                    patch("scripts.probes.macos_isolation.subprocess.run") as run:
                self.assertEqual("blocked_cleanup", probe()["status"])
                run.assert_not_called()
                self.assertTrue(container.exists())


if __name__ == "__main__":
    unittest.main()
