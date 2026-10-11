"""Bounded assertion validation plus optional real OpenSSL signature tests.

The fixture uses a disposable software key, not an OS-enrolled credential.
"""

import base64
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from scripts.contracts.authorization_attempt import AuthorizationAttempt
from scripts.contracts.first_pass import ContractError, prepare_review, record_judgment, start_draft
from scripts.contracts.review_binding import bind_review
from scripts.verify import build_environment


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/webauthn/assertion-es256.json"


class AssertionFixture:
    def setUp(self):
        name = "scripts.probes.webauthn_assertion"
        self.assertIsNotNone(importlib.util.find_spec(name), "WebAuthn assertion verifier is missing")
        self.module = importlib.import_module(name)
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.credential = self.module.PinnedCredential(
            credential_id=self.blob("credential_id"), user_handle=self.blob("user_handle"),
            rp_id=self.fixture["rp_id"], origin=self.fixture["origin"],
            public_key_spki=self.blob("public_key_spki"),
        )
        self.response = self.module.Assertion(
            credential_id=self.blob("credential_id"), client_data_json=self.blob("client_data_json"),
            authenticator_data=self.blob("authenticator_data"), signature=self.blob("signature"),
        )
        self.review = prepare_review(record_judgment(
            start_draft("demo-project", "demo-episode", "synthetic context", "prior claim"),
            "human interpretation", "human rationale",
        ))
        self.binding = bind_review(self.review, operation_digest="a" * 64,
                                   session_nonce="synthetic-session", expires_at=20)
        self.request = self.attempt(lambda request, response: False).request

    def blob(self, name):
        return base64.b64decode(self.fixture[name + "_b64"], validate=True)

    def attempt(self, verifier, **overrides):
        arguments = dict(binding=self.binding, nonce=b"N" * 32, load_review=lambda: self.review,
                         verify_response=verifier, clock=lambda: 1)
        arguments.update(overrides)
        return AuthorizationAttempt(**arguments)

    def verifier(self, callback, credential=None):
        return self.module.AssertionVerifier(
            self.credential if credential is None else credential, verify_signature=callback)

    def client(self, **changes):
        document = json.loads(self.response.client_data_json)
        document.update(changes)
        return replace(self.response, client_data_json=json.dumps(document).encode("utf-8"))

    def deny_before_crypto(self, response, request=None):
        def forbidden(*args):
            self.fail("Invalid response reached cryptographic verification")
        self.assertIs(False, self.verifier(forbidden)(
            self.request if request is None else request, response))


class AssertionValidationTests(AssertionFixture, unittest.TestCase):
    def test_original_signed_bytes_and_pinned_key_reach_native_boundary(self):
        calls = []
        def capture(key, message, signature):
            calls.append((key, message, signature))
            return True
        self.assertIs(True, self.verifier(capture)(self.request, self.response))
        self.assertEqual([(self.blob("public_key_spki"), self.blob("authenticator_data") +
                           hashlib.sha256(self.blob("client_data_json")).digest(),
                           self.blob("signature"))], calls)
        self.assertEqual(self.fixture["challenge_hex"], self.request.challenge.hex())

    def test_wrong_credential_or_present_user_handle_is_rejected(self):
        for change in (dict(credential_id=b"other"), dict(user_handle=b"other"),
                       dict(user_handle=b""), dict(user_handle="synthetic-user")):
            with self.subTest(change=change):
                self.deny_before_crypto(replace(self.response, **change))
        self.assertTrue(self.verifier(lambda *args: True)(
            self.request, replace(self.response, user_handle=self.credential.user_handle)))

    def test_challenge_type_origin_and_cross_origin_are_exact(self):
        original = json.loads(self.response.client_data_json)
        changes = (
            dict(type="webauthn.create"), dict(type=None),
            dict(challenge=original["challenge"] + "="), dict(challenge="not-base64url"),
            dict(challenge=[original["challenge"]]), dict(origin="https://other.invalid"),
            dict(origin=self.credential.origin + "/"), dict(crossOrigin=True),
            dict(crossOrigin=0), dict(crossOrigin=None), dict(topOrigin=self.credential.origin),
            dict(unrecognized="extension"),
        )
        for change in changes:
            with self.subTest(change=change):
                self.deny_before_crypto(self.client(**change))
        self.deny_before_crypto(self.response, replace(self.request, challenge=b"x" * 32))

    def test_missing_cross_origin_is_allowed_for_this_preselected_credential(self):
        client = json.loads(self.response.client_data_json)
        del client["crossOrigin"]
        response = replace(self.response, client_data_json=json.dumps(client).encode())
        self.assertTrue(self.verifier(lambda *args: True)(self.request, response))

    def test_malformed_or_ambiguous_client_json_is_rejected(self):
        original = self.response.client_data_json
        cases = (b"", b"null", b"[]", b"{", b"\xff", b'"text"', b"{}",
                 original[:-1] + b',"type":"webauthn.get"}',
                 original[:-1] + b',"crossOrigin":NaN}',
                 b"[" * 2000 + b"null" + b"]" * 2000,
                 original + b" " * 8192)
        for value in cases:
            with self.subTest(value=value[:40]):
                self.deny_before_crypto(replace(self.response, client_data_json=value))

    def test_rp_hash_presence_verification_and_profile_flags_are_required(self):
        data = self.response.authenticator_data
        cases = [b"x" * 32 + data[32:], data[:-1], data + b"\0"]
        cases += [data[:32] + bytes([flag]) + data[33:]
                  for flag in (0, 1, 4, 0x07, 0x0D, 0x15, 0x1D, 0x25, 0x45, 0x85)]
        for value in cases:
            with self.subTest(data=value.hex()):
                self.deny_before_crypto(replace(self.response, authenticator_data=value))

    def test_malformed_fields_and_requests_fail_before_native_call(self):
        for field in ("credential_id", "client_data_json", "authenticator_data", "signature"):
            for value in (None, "text", bytearray(b"x"), 1):
                with self.subTest(field=field, value=value):
                    self.deny_before_crypto(replace(self.response, **{field: value}))
        for signature in (b"", b"x" * 7, b"x" * 73):
            self.deny_before_crypto(replace(self.response, signature=signature))
        for request in (True, {}, replace(self.request, challenge=b""),
                        replace(self.request, challenge="x" * 32)):
            self.deny_before_crypto(self.response, request)
        for response in (None, True, {"actor_class": "human"}, object.__new__(self.module.Assertion)):
            self.deny_before_crypto(response)

    def test_invalid_pins_or_missing_native_verifier_cannot_be_configured(self):
        changes = (dict(credential_id=b""), dict(credential_id=b"x" * 1025),
                   dict(user_handle=b""), dict(user_handle=b"x" * 65),
                   dict(rp_id="Other.invalid"), dict(rp_id="a..invalid"),
                   dict(rp_id="-a.invalid"), dict(rp_id="a/invalid"),
                   dict(origin="http://claimbranch.invalid"),
                   dict(origin="https://sub.claimbranch.invalid"),
                   dict(public_key_spki=b""), dict(public_key_spki=b"x" * 91),
                   dict(public_key_spki=self.credential.public_key_spki + b"\0"))
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.verifier(lambda *args: True, replace(self.credential, **change))
        for callback in (None, True):
            with self.assertRaises(ContractError):
                self.verifier(callback)

    def test_backend_failure_is_not_reclassified_as_signature_mismatch(self):
        def broken(*args):
            raise OSError("synthetic native failure")
        verifier = self.verifier(broken)
        with self.assertRaises(OSError):
            verifier(self.request, self.response)
        self.assertEqual("failed", self.attempt(verifier).finish(self.response).status)
        for verdict in (None, 1, "verified"):
            verifier = self.verifier(lambda *args: verdict)
            with self.subTest(verdict=verdict), self.assertRaises(ContractError):
                verifier(self.request, self.response)
        verifier = self.verifier(lambda *args: False)
        self.assertEqual("rejected", self.attempt(verifier).finish(self.response).status)


class NativeAssertionTests(AssertionFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_root = build_environment(needs_probe=True)["TMPDIR"]
        override = os.environ.get("CLAIMBRANCH_TEST_OPENSSL")
        if override is not None:
            path = Path(override)
            if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
                raise RuntimeError("CLAIMBRANCH_TEST_OPENSSL must be an executable absolute path")
            cls.openssl = str(path)
        else:
            cls.openssl = shutil.which("openssl")
            if cls.openssl is None:
                raise unittest.SkipTest("Native assertion signature checks require an installed OpenSSL")

    def native_verify(self, key, message, signature):
        # Native crypto is a test oracle only; it is not a Windows/product backend.
        with TemporaryDirectory(prefix="claimbranch-assertion-test-", dir=self.temporary_root) as directory:
            root = Path(directory)
            (root / "public.der").write_bytes(key)
            (root / "signature.der").write_bytes(signature)
            result = subprocess.run(
                [self.openssl, "dgst", "-sha256", "-keyform", "DER", "-verify",
                 str(root / "public.der"), "-signature", str(root / "signature.der")],
                input=message, capture_output=True, timeout=10,
            )
        if result.returncode not in (0, 1):
            raise RuntimeError("Native signature verifier could not complete")
        return result.returncode == 0

    def test_real_signature_connects_to_attempt_without_claiming_os_authorization(self):
        verifier = self.verifier(self.native_verify)
        self.assertTrue(verifier(self.request, self.response))
        attempt = self.attempt(verifier)
        result = attempt.finish(self.response)
        self.assertEqual("matched", result.status)
        self.assertFalse(result.authorization_verified)
        with self.assertRaises(ContractError):
            attempt.finish(self.response)

    def test_real_signature_rejects_tampering_even_when_metadata_is_valid(self):
        verifier = self.verifier(self.native_verify)
        data = self.response.authenticator_data
        signature = self.response.signature
        cases = (replace(self.response, signature=signature[:-1] + bytes([signature[-1] ^ 1])),
                 replace(self.response, client_data_json=self.response.client_data_json + b" "),
                 replace(self.response, authenticator_data=data[:-1] + b"\x01"))
        for response in cases:
            with self.subTest(response=response):
                self.assertFalse(verifier(self.request, response))

    def test_response_cannot_replace_the_pinned_public_key(self):
        credential = replace(self.credential, public_key_spki=self.blob("other_public_key_spki"))
        self.assertFalse(self.verifier(self.native_verify, credential)(self.request, self.response))

    def test_valid_signature_cannot_override_late_review_change_or_expiry(self):
        for change in ("review", "expiry", "cancel"):
            current = [self.review]
            now = [1]
            verifier = self.verifier(self.native_verify)
            def verify_then_change(request, response):
                matched = verifier(request, response)
                self.assertTrue(matched)
                if change == "review":
                    current[0] = prepare_review(replace(self.review.draft, revision=2))
                elif change == "expiry":
                    now[0] = 20
                else:
                    attempt.cancel()
                return matched
            attempt = self.attempt(verify_then_change, load_review=lambda: current[0],
                                   clock=lambda: now[0])
            with self.subTest(change=change):
                result = attempt.finish(self.response)
                self.assertEqual({"review": "stale", "expiry": "expired", "cancel": "cancelled"}[change],
                                 result.status)
                self.assertFalse(result.authorization_verified)


if __name__ == "__main__":
    unittest.main()
