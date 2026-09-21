"""Real Windows process checks; no model, credential, or research data."""

import importlib
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class WindowsIsolationTests(unittest.TestCase):
    def setUp(self):
        # A missing implementation is an explicit RED, not an import crash.
        name = "scripts.probes.windows_isolation"
        self.assertIsNotNone(importlib.util.find_spec(name), "Windows probe is not implemented")
        self.probe = importlib.import_module(name)

    def test_git_temporary_root_is_rejected_without_changes(self):
        # Removing the non-Git boundary would let a probe alter repository ACLs.
        repository = Path(__file__).resolve().parents[2]
        before = set(repository.iterdir())
        with patch.object(tempfile, "tempdir", str(repository)):
            with self.assertRaises(self.probe.ProbeError):
                self.probe.run_probe()
        self.assertEqual(set(repository.iterdir()), before)

    def test_missing_temporary_root_is_not_created(self):
        # Validation must precede mkdir and ACL changes.
        missing = Path(tempfile.gettempdir()) / "claimbranch-must-not-create-isolation-root"
        self.assertFalse(missing.exists())
        with patch.object(tempfile, "tempdir", str(missing)):
            with self.assertRaises(self.probe.ProbeError):
                self.probe.run_probe()
        self.assertFalse(missing.exists())

    def test_volume_root_cannot_be_selected_as_temporary_root(self):
        # A malicious TMP override must not permit filesystem-root placement.
        volume = Path(tempfile.gettempdir()).anchor
        with patch.object(tempfile, "tempdir", volume):
            with self.assertRaises(self.probe.ProbeError):
                self.probe._temporary_root()

    def test_unconfirmed_child_termination_is_a_distinct_hard_failure(self):
        # Fault-inject only the unavailable OS-error branch; no real child is
        # created. Ignoring failed termination would permit unsafe cleanup.
        windows = self.probe._Windows.__new__(self.probe._Windows)

        def system_directory(buffer, size):
            buffer.value = "C:\\Windows\\System32"
            return len(buffer.value)

        def create_process(*arguments):
            process = arguments[-1]._obj
            process.process, process.thread = 100, 101
            return True

        windows.kernel = SimpleNamespace(
            GetSystemDirectoryW=system_directory, CreateProcessW=create_process,
            TerminateProcess=lambda *args: False, WaitForSingleObject=lambda *args: 258,
            CloseHandle=lambda *args: True,
        )
        with patch.object(windows, "token_info", side_effect=self.probe.ProbeError("injected inspection failure")):
            with self.assertRaisesRegex(self.probe.ProbeError, "termination not confirmed"):
                windows.launch(Path("C:/synthetic/child.exe"), Path("C:/synthetic"))

    @unittest.skipUnless(os.name == "nt", "Real AppContainer proof requires Windows")
    def test_real_appcontainer_denies_protected_paths_but_writes_proposal(self):
        # Omitting SECURITY_CAPABILITIES, broadening a protected ACL, or failing
        # to launch must all fail: ordinary-process access is the positive control.
        result = self.probe.run_probe()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["mechanism"], "windows-appcontainer")
        self.assertEqual(result["control"], {
            "appcontainer": False, "accepted_write": True,
            "manuscript_write": True, "secret_read": True, "proposal_write": True,
        })
        self.assertEqual(result["isolated"], {
            "appcontainer": True, "accepted_write": False,
            "manuscript_write": False, "secret_read": False, "proposal_write": True,
        })
        self.assertTrue(result["protected_unchanged"])
        self.assertTrue(result["cleanup_complete"])
        self.assertTrue(result.get("profile_cleanup_complete"), "Profile removal needs observable verification")
        self.assertEqual(result["access_errors"]["isolated"], {
            "accepted_write": 5, "manuscript_write": 5, "secret_read": 5, "proposal_write": 0,
        })


if __name__ == "__main__":
    unittest.main()
