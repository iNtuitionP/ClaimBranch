"""Native signature checks preserve provenance, never accepted write authority."""
import base64
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.recovery import pack_history
from claimbranch.core.recovery_checkpoint import checkpoint_message, pack_signed_history, unpack_signed_history
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example
from scripts.probes.macos_authorization import ProbeError, temporary_root
from scripts.probes.macos_recovery import build, crypt, read_archive, write_archive, AuthenticationRejected
from scripts.probes.macos_signed_recovery import (SignatureRejected, fixture_signature, main, probe,
    restore_signed_candidate, verify_signature)


@unittest.skipUnless(sys.platform == "darwin", "native signed recovery requires macOS")
class SignedRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root())
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.binary = build(cls.root)
        cls.history = replay_example("recorded", series=True)
        cls.checkpoint_id = "synthetic-checkpoint-1"
        cls.message = checkpoint_message(cls.history, cls.checkpoint_id)
        cls.public, cls.signature = fixture_signature(cls.binary, cls.message)
        cls.raw = pack_signed_history(cls.history, cls.checkpoint_id, cls.public, cls.signature)
        cls.pins = {"expected_project_id": decode(cls.history.seed)["project_id"],
                    "expected_signer_digest": hashlib.sha256(cls.public).hexdigest(),
                    "expected_checkpoint_digest": hashlib.sha256(cls.message).hexdigest()}

    def test_signature_agrees_with_independent_openssl_verifier(self):
        self.assertTrue(verify_signature(self.binary, self.message, self.public, self.signature))
        # SubjectPublicKeyInfo prefix for id-ecPublicKey + prime256v1; only public data.
        der = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200") + self.public
        encoded = base64.b64encode(der).decode()
        pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(encoded[i:i+64] for i in range(0, len(encoded), 64)) + "\n-----END PUBLIC KEY-----\n"
        public_path, signature_path = self.root / "fixture-public.pem", self.root / "fixture-signature.der"
        public_path.write_text(pem)
        signature_path.write_bytes(self.signature)
        openssl = os.environ.get("CLAIMBRANCH_TEST_OPENSSL", "/usr/bin/openssl")
        result = subprocess.run([openssl, "dgst", "-sha256", "-verify", str(public_path),
            "-signature", str(signature_path)], input=self.message, capture_output=True, timeout=15)
        self.assertEqual(0, result.returncode)
        self.assertIn(b"Verified OK", result.stdout)

    def test_signature_message_and_key_substitutions_are_rejected(self):
        other_public, other_signature = fixture_signature(self.binary, self.message)
        for message, public, signature in (
                (self.message + b" ", self.public, self.signature),
                (self.message, other_public, self.signature),
                (self.message, self.public, other_signature),
                (self.message, self.public, bytes(8)),
                (self.message, b"\x04" + bytes(64), self.signature)):
            with self.assertRaises(SignatureRejected):
                verify_signature(self.binary, message, public, signature)
        for request in (b"", bytes(2 + 65 + 72 + 1025), struct.pack(">H", 65535) + self.public):
            result = subprocess.run([str(self.binary), "verify-checkpoint"], input=request,
                                     capture_output=True, timeout=15)
            self.assertEqual(1, result.returncode)
            self.assertEqual(b"", result.stdout)
            self.assertEqual(b"recovery-rejected\n", result.stderr)

    def test_restore_preserves_signed_bytes_and_original_key_without_authority(self):
        with tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
            root = Path(directory)
            recovery, local = secrets.token_bytes(32), secrets.token_bytes(32)
            backup = crypt(self.binary, "seal", self.raw, recovery)
            write_archive(root, "backup.cbr", backup)
            restored = restore_signed_candidate(root, self.binary, recovery, local, **self.pins)
            self.assertEqual(self.history.manifest(), restored.manifest())
            self.assertFalse(restored.authorization_verified)
            rewritten = read_archive(root, "restored.cbr")
            self.assertEqual(self.raw, crypt(self.binary, "open", rewritten, local))
            self.assertEqual(backup, read_archive(root, "backup.cbr"))
            with self.assertRaises(AuthenticationRejected):
                crypt(self.binary, "open", rewritten, recovery)
            parsed = unpack_signed_history(self.raw, **self.pins)
            self.assertEqual(self.public, parsed.public_key)
            self.assertEqual(self.signature, parsed.signature)
            with self.assertRaises(FileExistsError):
                restore_signed_candidate(root, self.binary, recovery, local, **self.pins)
            self.assertEqual(rewritten, read_archive(root, "restored.cbr"))

    def test_valid_encryption_does_not_bypass_signature_or_external_pins(self):
        other_public, other_signature = fixture_signature(self.binary, self.message)
        modified = ResearchHistory.start(self.pins["expected_project_id"], "other-episode", "claim", "Altered synthetic history", "anchor")
        altered_message = checkpoint_message(modified, self.checkpoint_id)
        cases = [
            (pack_signed_history(self.history, self.checkpoint_id, self.public, other_signature), self.pins, SignatureRejected),
            (pack_signed_history(self.history, self.checkpoint_id, other_public, other_signature), self.pins, ContractError),
            (pack_signed_history(modified, self.checkpoint_id, self.public, self.signature),
             {**self.pins, "expected_checkpoint_digest": hashlib.sha256(altered_message).hexdigest()}, SignatureRejected),
            (pack_history(self.history), self.pins, ContractError),
            (self.raw, {**self.pins, "expected_project_id": "another-project"}, ContractError),
            (self.raw, {**self.pins, "expected_checkpoint_digest": "0" * 64}, ContractError),
            (self.raw, {**self.pins, "expected_signer_digest": None}, ContractError),
            (self.raw, {**self.pins, "expected_checkpoint_digest": None}, ContractError),
        ]
        for index, (raw, pins, error) in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
                root, recovery = Path(directory), secrets.token_bytes(32)
                archive = crypt(self.binary, "seal", raw, recovery)
                write_archive(root, "backup.cbr", archive)
                with self.assertRaises(error):
                    restore_signed_candidate(root, self.binary, recovery, secrets.token_bytes(32), **pins)
                self.assertEqual(["backup.cbr"], sorted(p.name for p in root.iterdir()))
                self.assertEqual(archive, read_archive(root, "backup.cbr"))

    def test_interrupted_signed_restore_leaves_original_and_no_destination(self):
        with tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
            root, recovery = Path(directory), secrets.token_bytes(32)
            archive = crypt(self.binary, "seal", self.raw, recovery)
            write_archive(root, "backup.cbr", archive)
            def interrupt():
                raise InterruptedError("synthetic interruption")
            with self.assertRaises(InterruptedError):
                restore_signed_candidate(root, self.binary, recovery, secrets.token_bytes(32),
                    **self.pins, before_publish=interrupt)
            self.assertEqual(["backup.cbr"], sorted(p.name for p in root.iterdir()))
            self.assertEqual(archive, read_archive(root, "backup.cbr"))


class SignedDriverTests(unittest.TestCase):
    def test_public_errors_never_echo_payloads_or_exception_details(self):
        secret = "synthetic-secret-must-not-escape"
        timeout = subprocess.TimeoutExpired(["helper", secret], 15, output=secret.encode(), stderr=secret.encode())
        for error in (timeout, OSError(secret), ProbeError(secret), ContractError(secret)):
            output = io.StringIO()
            with patch("scripts.probes.macos_signed_recovery.probe", side_effect=error), redirect_stdout(output):
                self.assertEqual(1, main(["--exercise"]))
            self.assertNotIn(secret, output.getvalue())
            result = json.loads(output.getvalue())
            self.assertEqual("error", result["status"])
            self.assertFalse(result["signature_verified"])
            self.assertFalse(result["authorization_verified"])

    def test_unsupported_host_does_not_generate_fixture_or_compile(self):
        with patch("scripts.probes.macos_signed_recovery.sys.platform", "win32"), \
                patch("scripts.probes.macos_signed_recovery.build") as compile_native:
            result = probe(exercise=True)
            self.assertEqual("unsupported", result["status"])
            self.assertFalse(result["authorization_verified"])
            compile_native.assert_not_called()

    def test_unexpected_verifier_output_cannot_be_accepted(self):
        public, signature = b"\x04" + bytes(64), bytes(70)
        for result in (subprocess.CompletedProcess([], 0, b"true", b""),
                       subprocess.CompletedProcess([], 2, b"signature-verified\n", b"signature-rejected\n"),
                       subprocess.CompletedProcess([], 0, b"signature-verified\n", b"unexpected")):
            with patch("scripts.probes.macos_signed_recovery.subprocess.run", return_value=result), self.assertRaises(ProbeError):
                verify_signature(Path("unused"), b"message", public, signature)


if __name__ == "__main__":
    unittest.main()
