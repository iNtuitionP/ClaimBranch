"""Restart review must bind identity, bytes and a fresh challenge, never authority."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.probes.macos_authorization import ProbeError, temporary_root
from scripts.probes.macos_key_reopen import SOURCE, assess_review, decode_result, probe, review_message
from tests.probes.test_macos_key_reopen import native, observations


NONCE = "d" * 64
PUBLIC = b"\x04" + b"p" * 64  # Parser fixture only; not a valid crypto proof.


def cancellation(source):
    return {"cancel_source": source, "cancel_trigger": "native_callback" if source == "native" else "review_button",
            "cancel_error_domain": "com.apple.LocalAuthentication" if source == "native" else None,
            "cancel_error_code": -2 if source == "native" else None}


def review_observations():
    created, reopened, denied, _, after = observations()
    created["mode"] = "prepare"
    public_digest = hashlib.sha256(PUBLIC).hexdigest()
    for value in (created, reopened, denied, after):
        value["public_key_digest"] = public_digest
    binding = {"public_key_digest": public_digest, "representation_digest": "b" * 64,
               "review_digest": "c" * 64}
    binding["challenge_digest"] = hashlib.sha256(review_message(**binding, nonce=NONCE)).hexdigest()
    result = native("review", "matched", process_id=104, **binding, signature_verified=True,
                    explicit_authentication_succeeded=True, signing_started=True,
                    public_key_x963=base64.b64encode(PUBLIC).decode(),
                    signature_der=base64.b64encode(b"s" * 70).decode())
    verified = native("verify", "verified", process_id=105, **binding, signature_verified=True)
    after = dict(denied, process_id=106)
    return [created, reopened, denied, result, verified, after]


class ReopenReviewTests(unittest.TestCase):
    def test_review_binds_exact_challenge_and_requires_independent_verification_and_denial(self):
        expected = ("claimbranch:key-reopen-review:v1\n" + "c" * 64 + "\n" +
                    hashlib.sha256(PUBLIC).hexdigest() + "\n" + "b" * 64 + "\n" + NONCE).encode()
        values = review_observations()
        self.assertEqual(expected, review_message("c" * 64, values[0]["public_key_digest"], "b" * 64, NONCE))
        result = assess_review(*values, nonce=NONCE)
        self.assertEqual("review_observed", result["status"])
        self.assertTrue(result["signature_after_restart_verified"])
        self.assertTrue(result["explicit_authentication_succeeded"])
        self.assertTrue(result["signing_started"])
        self.assertFalse(result["authorization_verified"])
        self.assertFalse(result["product_custody_verified"])
        self.assertFalse({"signature_der", "public_key_x963", "nonce"} & result.keys())

    def test_changed_binding_failed_crypto_reused_pid_or_reused_authentication_is_rejected(self):
        changes = ((0, {"public_key_digest": "a" * 64}), (1, {"representation_digest": "a" * 64}),
                   (3, {"challenge_digest": "a" * 64}), (3, {"review_digest": "a" * 64}),
                   (3, {"process_id": 101}), (4, {"status": "rejected", "signature_verified": False}),
                   (3, {"explicit_authentication_succeeded": False}), (3, {"signing_started": False}),
                   (4, {"challenge_digest": "a" * 64}), (5, {"error_domain": "wrong"}))
        for index, change in changes:
            values = review_observations()
            values[index].update(change)
            with self.subTest(index=index, change=change), self.assertRaises(ProbeError):
                assess_review(*values, nonce=NONCE)
        with self.assertRaises(ProbeError):
            assess_review(*review_observations(), nonce="e" * 64)

    def test_terminal_results_do_not_keep_signature_or_claim_approval(self):
        created, reopened, denied, matched, _, _ = review_observations()
        for status in ("cancelled", "expired"):
            result = {k: v for k, v in matched.items() if k not in ("public_key_x963", "signature_der")}
            result.update(status=status, signature_verified=False,
                          explicit_authentication_succeeded=False, signing_started=False)
            if status == "cancelled":
                result.update(cancellation("native"))
            value = assess_review(created, reopened, denied, result, None, None, nonce=NONCE)
            self.assertEqual(status, value["status"])
            self.assertFalse(value["signature_after_restart_verified"])
            self.assertFalse(value["signing_started"])
            with self.assertRaises(ProbeError):
                assess_review(created, reopened, denied, dict(result, signature_der=matched["signature_der"]),
                              None, None, nonce=NONCE)

    def test_review_output_is_closed_and_bounds_public_material(self):
        original = review_observations()[3]
        def decode(value):
            return decode_result(subprocess.CompletedProcess([], 0, json.dumps(value), ""), "review")
        self.assertEqual(original, decode(original))
        for update in ({"signature_verified": 1}, {"signature_der": "s" * 300},
                       {"explicit_authentication_succeeded": 1}, {"signing_started": 1},
                       {"public_key_x963": base64.b64encode(b"x" * 65).decode()},
                       {"public_key_digest": "a" * 64}, {"authorization_verified": True},
                       {"product_custody_verified": True}, {"blob": "private"}):
            with self.subTest(update=update), self.assertRaises(ProbeError):
                decode(dict(original, **update))

    def test_no_review_or_native_tool_runs_on_an_unsupported_host(self):
        with patch("scripts.probes.macos_key_reopen.sys.platform", "win32"), \
                patch("scripts.probes.macos_key_reopen.subprocess.run") as run:
            self.assertEqual("unsupported", probe(review=True)["status"])
            run.assert_not_called()
        with self.assertRaises(ProbeError):
            probe(review=True, exercise=True)

    def test_driver_cleans_up_and_never_verifies_after_terminal_review(self):
        for terminal in (None, "cancelled", "expired"):
            values = review_observations()
            if terminal:
                result = values[3]
                result.pop("public_key_x963")
                result.pop("signature_der")
                result.update(status=terminal, signature_verified=False,
                              explicit_authentication_succeeded=False, signing_started=False)
                if terminal == "cancelled":
                    result.update(cancellation("review"))
            expected = ["check", "prepare", "reopen", "deny", "review"] + ([] if terminal else ["verify", "deny"])
            outputs = [native("check", "available", secure_enclave_available=True), *values[:4]]
            if not terminal:
                outputs.extend(values[4:])
            calls, roots = [], []
            def run(argv, **kwargs):
                if "cwd" not in kwargs:
                    roots.append(Path(argv[-1]).parent)
                    return subprocess.CompletedProcess(argv, 0, "", "")
                calls.append(argv[1])
                if argv[1] in ("review", "verify"):
                    self.assertEqual([values[0]["public_key_digest"], "b" * 64, NONCE], argv[2:])
                if argv[1] == "verify":
                    payload = json.loads(kwargs["input"])
                    self.assertEqual({"public_key_x963", "signature_der"}, set(payload))
                return subprocess.CompletedProcess(argv, 0, json.dumps(outputs.pop(0)), "")
            with self.subTest(terminal=terminal), patch("scripts.probes.macos_key_reopen.sys.platform", "darwin"), \
                    patch("scripts.probes.macos_key_reopen.subprocess.run", side_effect=run), \
                    patch("scripts.probes.macos_key_reopen.secrets.token_hex", return_value=NONCE):
                result = probe(review=True)
            self.assertEqual(expected, calls)
            self.assertEqual(terminal or "review_observed", result["status"])
            self.assertTrue(result["cleanup_verified"])
            self.assertTrue(all(not root.exists() for root in roots))

    def test_bad_preflight_never_opens_the_human_review(self):
        for index, change in ((1, {"public_key_digest": "e" * 64}), (1, {"process_id": 101}),
                              (2, {"error_domain": "unrelated"})):
            values = review_observations()
            values[index].update(change)
            outputs = [native("check", "available", secure_enclave_available=True), *values]
            calls = []
            def run(argv, **kwargs):
                if "cwd" not in kwargs:
                    return subprocess.CompletedProcess(argv, 0, "", "")
                calls.append(argv[1])
                return subprocess.CompletedProcess(argv, 0, json.dumps(outputs.pop(0)), "")
            with self.subTest(index=index, change=change), patch("scripts.probes.macos_key_reopen.sys.platform", "darwin"), \
                    patch("scripts.probes.macos_key_reopen.subprocess.run", side_effect=run), \
                    patch("scripts.probes.macos_key_reopen.secrets.token_hex", return_value=NONCE):
                with self.assertRaises(ProbeError):
                    probe(review=True)
            self.assertNotIn("review", calls)

    def test_preparation_cancel_or_expiry_stops_before_reopen_and_reports_no_identity(self):
        for status in ("cancelled", "expired"):
            output = native("prepare", status)
            if status == "cancelled":
                output.update(cancellation("review"))
            calls, roots = [], []
            def run(argv, **kwargs):
                if "cwd" not in kwargs:
                    roots.append(Path(argv[-1]).parent)
                    return subprocess.CompletedProcess(argv, 0, "", "")
                calls.append(argv[1])
                value = native("check", "available", secure_enclave_available=True) if argv[1] == "check" else output
                return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
            with self.subTest(status=status), patch("scripts.probes.macos_key_reopen.sys.platform", "darwin"), \
                    patch("scripts.probes.macos_key_reopen.subprocess.run", side_effect=run):
                result = probe(review=True)
            self.assertEqual(["check", "prepare"], calls)
            self.assertEqual(status, result["status"])
            self.assertEqual("prepare", result["phase"])
            self.assertFalse(result["signature_after_restart_verified"])
            self.assertFalse({"public_key_digest", "signature_der"} & result.keys())
            self.assertTrue(result["cleanup_verified"])
            self.assertTrue(all(not root.exists() for root in roots))

    def test_preparation_terminal_output_cannot_keep_key_material(self):
        cancelled = native("prepare", "cancelled", **cancellation("native"))
        def decoded(value):
            return decode_result(subprocess.CompletedProcess([], 0, json.dumps(value), ""), "prepare")
        self.assertEqual(cancelled, decoded(cancelled))
        for change in ({"public_key_digest": "a" * 64}, {"representation_digest": "a" * 64},
                       {"blob": "opaque-key"}, {"signature_der": "late"},
                       {"signature_verified": True}, {"cancel_source": "unknown"}):
            with self.subTest(change=change), self.assertRaises(ProbeError):
                decoded(dict(cancelled, **change))

    def test_cancellation_keeps_bounded_callback_and_trigger_without_inventing_origin(self):
        value = native("prepare", "cancelled", **cancellation("native"))
        def decoded(item):
            return decode_result(subprocess.CompletedProcess([], 0, json.dumps(item), ""), "prepare")
        raced = dict(value, cancel_trigger="window_close")
        self.assertEqual("native", decoded(raced)["cancel_source"])
        app = native("prepare", "cancelled", **cancellation("review"))
        self.assertIsNone(decoded(app)["cancel_error_code"])
        for change in ({"cancel_error_code": True}, {"cancel_error_domain": "x" * 129},
                       {"cancel_error_code": None}, {"cancel_trigger": "assumed_native"},
                       {"cancel_source": "review"}):
            with self.subTest(change=change), self.assertRaises(ProbeError):
                decoded(dict(value, **change))


@unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/xcrun").exists(), "macOS SDK check")
class NativeReopenReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="claimbranch-review-test-", dir=temporary_root())
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.binary = cls.root / "reopen"
        built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(cls.binary)],
                               capture_output=True, text=True, timeout=90)
        if built.returncode:
            raise AssertionError(built.stderr)

    def native(self, mode, *args, input=None):
        result = subprocess.run([str(self.binary), mode, *args], input=input, cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        return decode_result(result, mode)

    def test_real_native_lifecycle_rejects_cancelled_and_late_success_without_ui(self):
        result = self.native("gate-check")
        self.assertTrue(all(result["checks"].values()), result)
        self.assertTrue({"unauthenticated_success_rejected", "failed_authentication_does_not_sign",
                         "cancelled_authentication_does_not_sign", "late_authentication_does_not_sign",
                         "authentication_callback_once"} <= result["checks"].keys())
        self.assertFalse((self.root / "enclave-key.bin").exists())

    def test_independent_native_crypto_verifies_exact_message_and_rejects_tampering(self):
        openssl = os.environ.get("CLAIMBRANCH_TEST_OPENSSL")
        if openssl is not None:
            path = Path(openssl)
            if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
                self.fail("CLAIMBRANCH_TEST_OPENSSL must be an executable absolute path")
        else:
            openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("Installed OpenSSL required for independent crypto oracle")
        def crypto(*args, input=None):
            result = subprocess.run([openssl, *args], input=input, capture_output=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout
        # This is a disposable software test key, never an OS credential or a
        # fallback in the Secure Enclave review path.
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            key = Path(directory) / "test.pem"
            crypto("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(key))
            key.chmod(0o600)
            spki = crypto("pkey", "-in", str(key), "-pubout", "-outform", "DER")
            self.assertEqual(bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200"), spki[:-65])
            public = spki[-65:]
            public_digest = hashlib.sha256(public).hexdigest()
            args = (public_digest, "b" * 64, NONCE)
            binding = self.native("verify", *args, input="{}")
            self.assertEqual("rejected", binding["status"])
            message = review_message(binding["review_digest"], *args)
            signature = crypto("dgst", "-sha256", "-sign", str(key), input=message)
            payload = {"public_key_x963": base64.b64encode(public).decode(),
                       "signature_der": base64.b64encode(signature).decode()}
            value = self.native("verify", *args, input=json.dumps(payload))
            self.assertEqual("verified", value["status"])
            self.assertEqual(hashlib.sha256(message).hexdigest(), value["challenge_digest"])
            self.assertFalse(value["authorization_verified"])
            for changed in ((public_digest, "b" * 64, "e" * 64), ("e" * 64, "b" * 64, NONCE),
                            (public_digest, "e" * 64, NONCE)):
                self.assertEqual("rejected", self.native("verify", *changed, input=json.dumps(payload))["status"])
            altered = signature[:-1] + bytes([signature[-1] ^ 1])
            payload["signature_der"] = base64.b64encode(altered).decode()
            self.assertEqual("rejected", self.native("verify", *args, input=json.dumps(payload))["status"])
        self.assertFalse((self.root / "enclave-key.bin").exists())


if __name__ == "__main__":
    unittest.main()
