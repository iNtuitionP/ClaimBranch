"""An independent native custody measurement cannot grant product authority."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.probes.macos_key_reopen import SOURCE, assess, decode_result, main, probe
from scripts.probes.macos_authorization import ProbeError, temporary_root


def native(mode, status, **fields):
    return {"schema_version": 1, "mode": mode, "status": status,
            "process_id": 101, "authorization_verified": False,
            "product_custody_verified": False, **fields}


def observations():
    identity = {"public_key_digest": "a" * 64, "representation_digest": "b" * 64}
    created = native("create", "created", **identity)
    reopened = native("reopen", "reopened", **identity)
    reopened["process_id"] = 102
    denied = native("deny", "interaction_denied", **identity,
                    error_domain="NSOSStatusErrorDomain", error_code=-25308)
    denied["process_id"] = 103
    tampered = native("reopen", "key_rejected", error_domain="NSOSStatusErrorDomain", error_code=-50)
    tampered["process_id"] = 104
    control = dict(reopened, process_id=105)
    return [created, reopened, denied, tampered, control]


class MacKeyReopenTests(unittest.TestCase):
    def completed(self, value, code=0):
        return subprocess.CompletedProcess([], code, json.dumps(value), "")

    def test_constructor_error_cannot_establish_tamper_integrity(self):
        for domain, code in (("com.apple.LocalAuthentication", -1004),
                             ("NSOSStatusErrorDomain", -25308),
                             ("NSOSStatusErrorDomain", -50), ("unknown", -123)):
            with self.subTest(domain=domain, code=code):
                values = observations()
                values[3].update(error_domain=domain, error_code=code)
                result = assess(*values)
                self.assertEqual("incomplete", result["status"])
                self.assertFalse(result["tamper_integrity_verified"])

    def test_matching_identity_and_denial_are_separate_from_unproved_integrity(self):
        result = assess(*observations())
        self.assertEqual("incomplete", result["status"])
        self.assertTrue(result["same_public_identity"])
        self.assertTrue(result["noninteractive_signing_denied"])
        self.assertEqual("key_rejected", result["tampered_reopen_status"])
        self.assertFalse(result["tamper_integrity_verified"])
        self.assertTrue(result["valid_representation_reopens_after_tamper"])
        self.assertFalse(result["authorization_verified"])
        self.assertFalse(result["product_custody_verified"])

    def test_changed_identity_blob_pid_denial_domain_or_failed_control_cannot_pass(self):
        for index, change in ((1, {"public_key_digest": "c" * 64}),
                (1, {"representation_digest": "c" * 64}), (1, {"process_id": 101}),
                (2, {"error_domain": "unrelated-domain"}), (2, {"error_code": -2}),
                (3, {"status": "reopened"}), (4, {"public_key_digest": "c" * 64})):
            with self.subTest(index=index, change=change):
                values = observations()
                values[index].update(change)
                with self.assertRaises(ProbeError):
                    assess(*values)

    def test_changed_blob_that_reopens_is_an_incomplete_measurement(self):
        values = observations()
        values[3] = dict(values[1], process_id=104, representation_digest="c" * 64)
        result = assess(*values)
        self.assertEqual("incomplete", result["status"])
        self.assertTrue(result["same_public_identity"])
        self.assertTrue(result["noninteractive_signing_denied"])
        self.assertFalse(result["tamper_integrity_verified"])
        self.assertEqual("reopened", result["tampered_reopen_status"])
        self.assertFalse(result["product_custody_verified"])
        # A tamper exercise that submitted the original bytes proves nothing.
        values[3]["representation_digest"] = values[0]["representation_digest"]
        with self.assertRaises(ProbeError):
            assess(*values)

    def test_native_output_is_closed_bounded_and_never_contains_credentials_or_authority(self):
        original = observations()[0]
        self.assertEqual(original, decode_result(self.completed(original), "create"))
        for change in ({"authorization_verified": True}, {"product_custody_verified": True},
                       {"blob": "opaque-but-private"}, {"signature": "unexpected"},
                       {"process_id": True}, {"schema_version": True}, {"public_key_digest": "bad"}):
            with self.subTest(change=change), self.assertRaises(ProbeError):
                decode_result(self.completed(dict(original, **change)), "create")
        with self.assertRaises(ProbeError):
            decode_result(self.completed(original, 1), "create")
        with self.assertRaises(ProbeError):
            decode_result(self.completed(original), "reopen")
        for raw in ('[]', '{}', 'x' * 4097, '{"status":"created","status":"created"}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ProbeError):
                decode_result(subprocess.CompletedProcess([], 0, raw, ""), "create")

    def test_native_rejection_is_an_observation_and_unknown_signing_error_is_not_denial(self):
        rejected = observations()[3]
        self.assertEqual(rejected, decode_result(self.completed(rejected, 1), "reopen"))
        error = native("deny", "error", error_domain="unknown", error_code=-25308)
        self.assertEqual(error, decode_result(self.completed(error, 1), "deny"))
        values = observations()
        values[2] = error
        with self.assertRaises(ProbeError):
            assess(*values)

    def test_non_mac_never_builds_or_creates_a_key(self):
        with patch("scripts.probes.macos_key_reopen.sys.platform", "win32"), \
                patch("scripts.probes.macos_key_reopen.subprocess.run") as run:
            self.assertEqual("unsupported", probe(exercise=True)["status"])
            run.assert_not_called()

    def test_capability_only_and_failed_create_stop_before_key_use(self):
        available = self.completed(native("check", "available", secure_enclave_available=True))
        failed = self.completed(native("create", "error", error_domain="NSOSStatusErrorDomain", error_code=-34018), 1)
        for exercise in (False, True):
            paths = []
            calls = []
            def run(argv, **kwargs):
                calls.append(argv[-1] if "cwd" in kwargs else "build")
                if "cwd" not in kwargs:
                    paths.append(Path(argv[-1]).parent)
                    return subprocess.CompletedProcess(argv, 0, "", "")
                return available if argv[-1] == "check" else failed
            with self.subTest(exercise=exercise), patch("scripts.probes.macos_key_reopen.sys.platform", "darwin"), \
                    patch("scripts.probes.macos_key_reopen.subprocess.run", side_effect=run):
                if exercise:
                    with self.assertRaisesRegex(ProbeError, "custody measurement stopped"):
                        probe(exercise=True)
                else:
                    self.assertEqual("available", probe()["status"])
            self.assertEqual(["build", "check", "create"] if exercise else ["build", "check"], calls)
            self.assertTrue(paths)
            self.assertTrue(all(not path.exists() for path in paths))

    def test_incomplete_observation_has_nonzero_cli_status(self):
        with patch("scripts.probes.macos_key_reopen.probe", return_value={"status": "incomplete"}), \
                patch("builtins.print"):
            self.assertEqual(3, main(["--exercise"]))

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/xcrun").exists(), "macOS SDK check")
    def test_native_capability_path_has_no_key_file_and_no_interaction(self):
        value = probe()
        self.assertIn(value["status"], ("available", "unavailable"))
        self.assertTrue(value["cleanup_verified"])
        self.assertFalse(value["product_custody_verified"])

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/xcrun").exists(), "macOS SDK check")
    def test_native_reopen_rejects_unsafe_files_before_loading_key_material(self):
        with tempfile.TemporaryDirectory(dir=temporary_root()) as directory:
            root = Path(directory)
            binary = root / "reopen"
            built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(binary)],
                                   capture_output=True, text=True, timeout=90)
            self.assertEqual(0, built.returncode, built.stderr)
            for kind in ("symlink", "hardlink", "fifo", "public_file", "large_file", "public_directory"):
                with self.subTest(kind=kind):
                    case = root / kind
                    case.mkdir(mode=0o700)
                    blob = case / "enclave-key.bin"
                    sentinel = case / "sentinel"
                    sentinel.write_bytes(b"owned synthetic bytes, never a key")
                    sentinel.chmod(0o600)
                    if kind == "symlink":
                        blob.symlink_to(sentinel)
                    elif kind == "hardlink":
                        os.link(sentinel, blob)
                    elif kind == "fifo":
                        os.mkfifo(blob, 0o600)
                    else:
                        blob.write_bytes(b"x" * 16_385 if kind == "large_file" else b"synthetic")
                        blob.chmod(0o644 if kind == "public_file" else 0o600)
                    if kind == "public_directory":
                        case.chmod(0o755)
                    completed = subprocess.run([str(binary), "reopen"], cwd=case, capture_output=True,
                                               text=True, timeout=5)
                    result = decode_result(completed, "reopen")
                    self.assertEqual("error", result["status"])
                    self.assertEqual("NSPOSIXErrorDomain", result["error_domain"])
                    self.assertEqual(b"owned synthetic bytes, never a key", sentinel.read_bytes())


if __name__ == "__main__":
    unittest.main()
