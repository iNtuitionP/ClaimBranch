"""A2 capability discovery only; no enrollment or user-presence simulation."""

from contextlib import redirect_stdout
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class WindowsAuthorizationCapabilityTests(unittest.TestCase):
    def setUp(self):
        name = "scripts.probes.windows_authorization"
        self.assertIsNotNone(importlib.util.find_spec(name), "A2 capability probe is missing")
        self.probe = importlib.import_module(name)

    def test_other_platform_never_loads_windows_or_claims_authorization(self):
        with patch.object(self.probe.os, "name", "posix"), \
                patch.object(self.probe, "_read_capabilities", side_effect=AssertionError("DLL loaded")):
            result = self.probe.probe_capabilities()
        self.assertEqual("unsupported", result["status"])
        self.assertIsNone(result["api_version"])
        self.assertIsNone(result["platform_authenticator_available"])
        self.assertFalse(result["authorization_verified"])

    def test_api_floor_and_missing_authenticator_are_not_authorization(self):
        # Reporting these cases as available would start an unsuitable later probe.
        for version, available, status in ((3, True, "unavailable"),
                                           (4, False, "unavailable"),
                                           (4, True, "available"),
                                           (9, True, "available")):
            with self.subTest(version=version, available=available), \
                    patch.object(self.probe.os, "name", "nt"), \
                    patch.object(self.probe, "_read_capabilities", return_value=(version, available)):
                result = self.probe.probe_capabilities()
            self.assertEqual(status, result["status"])
            self.assertEqual(version, result["api_version"])
            self.assertIs(available, result["platform_authenticator_available"])
            self.assertFalse(result["authorization_verified"])

    def test_windows_api_failure_is_an_error_not_absence_or_success(self):
        for error in (OSError("missing DLL"), AttributeError("missing export"),
                      self.probe.ProbeError("HRESULT 0x80004005")):
            with self.subTest(error=type(error).__name__), \
                    patch.object(self.probe.os, "name", "nt"), \
                    patch.object(self.probe, "_read_capabilities", side_effect=error):
                result = self.probe.probe_capabilities()
            self.assertEqual("error", result["status"])
            self.assertFalse(result["authorization_verified"])

    def test_native_adapter_uses_fixed_width_types_and_system_dll(self):
        # Replace only the absent Windows loader, retaining the real adapter.
        # The fake also fails if unplanned enrollment/write APIs are accessed.
        class Function:
            def __init__(self, body):
                self.body = body

            def __call__(self, *arguments):
                return self.body(*arguments)

        def availability(target):
            target._obj.value = 1
            return 0

        library = SimpleNamespace(
            WebAuthNGetApiVersionNumber=Function(lambda: 4),
            WebAuthNIsUserVerifyingPlatformAuthenticatorAvailable=Function(availability),
        )

        def load(name, **options):
            self.assertEqual("webauthn.dll", name)
            self.assertEqual(0x00000800, options["winmode"])
            return library

        with patch.object(self.probe.ctypes, "WinDLL", side_effect=load, create=True):
            self.assertEqual((4, True), self.probe._read_capabilities())
        self.assertEqual(4, self.probe.ctypes.sizeof(library.WebAuthNGetApiVersionNumber.restype))
        self.assertEqual(4, self.probe.ctypes.sizeof(
            library.WebAuthNIsUserVerifyingPlatformAuthenticatorAvailable.restype))
        library.WebAuthNIsUserVerifyingPlatformAuthenticatorAvailable.body = lambda target: -2147467259
        with patch.object(self.probe.ctypes, "WinDLL", side_effect=load, create=True):
            with self.assertRaisesRegex(self.probe.ProbeError, "80004005"):
                self.probe._read_capabilities()
        # An availability-call failure must not erase an already observed version.
        with patch.object(self.probe.ctypes, "WinDLL", side_effect=load, create=True), \
                patch.object(self.probe.os, "name", "nt"):
            report = self.probe.probe_capabilities()
        self.assertEqual("error", report["status"])
        self.assertEqual(4, report["api_version"])
        self.assertIsNone(report["platform_authenticator_available"])
        self.assertFalse(report["authorization_verified"])

    def test_cli_separates_availability_from_unsupported_and_api_failure(self):
        for status, code in (("available", 0), ("unavailable", 3),
                             ("unsupported", 3), ("error", 1)):
            report = {"status": status, "authorization_verified": False}
            output = io.StringIO()
            with self.subTest(status=status), redirect_stdout(output), \
                    patch.object(self.probe, "probe_capabilities", return_value=report):
                self.assertEqual(code, self.probe.main(["--check"]))
            self.assertEqual(report, json.loads(output.getvalue()))

    @unittest.skipIf(os.name == "nt", "Non-Windows CLI guard")
    def test_real_unsupported_cli_has_one_report_and_writes_nothing(self):
        script = Path(__file__).resolve().parents[2] / "scripts/probes/windows_authorization.py"
        with tempfile.TemporaryDirectory() as scratch:
            result = subprocess.run([sys.executable, "-B", str(script), "--check"],
                                    cwd=scratch, capture_output=True, text=True, timeout=10)
            self.assertEqual([], list(Path(scratch).iterdir()))
        self.assertEqual(3, result.returncode)
        self.assertEqual("", result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("unsupported", report["status"])
        self.assertFalse(report["authorization_verified"])

    @unittest.skipUnless(os.name == "nt", "Real WebAuthn capability query requires Windows")
    def test_real_windows_query_without_enrollment_or_prompt(self):
        result = self.probe.probe_capabilities()
        self.assertIn(result["status"], ("available", "unavailable"), result)
        self.assertIsInstance(result["api_version"], int)
        self.assertIsInstance(result["platform_authenticator_available"], bool)
        self.assertFalse(result["authorization_verified"])


if __name__ == "__main__":
    unittest.main()
