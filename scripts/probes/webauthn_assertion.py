"""Restricted A2 assertion validation; not an authenticator or approval broker.

The trusted caller pins the credential and supplies an established ES256
signature verifier. No enrollment, key custody, native presence, I/O, receipt,
replay protection, or accepted write is implemented here. Synthetic valid
signatures can exercise this code without any human gesture.
"""

import base64
from dataclasses import dataclass
import hashlib
import json
import re

from scripts.contracts.authorization_attempt import AttemptRequest
from scripts.contracts.first_pass import ContractError


# DER SubjectPublicKeyInfo: id-ecPublicKey, prime256v1, uncompressed point.
_P256_SPKI_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d03010703420004")
_DNS_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"


@dataclass(frozen=True)
class PinnedCredential:
    credential_id: bytes
    user_handle: bytes
    rp_id: str
    origin: str
    public_key_spki: bytes


@dataclass(frozen=True)
class Assertion:
    credential_id: bytes
    client_data_json: bytes
    authenticator_data: bytes
    signature: bytes
    user_handle: bytes | None = None


def _bytes(value, minimum, maximum):
    return type(value) is bytes and minimum <= len(value) <= maximum


def _valid_pin(credential):
    if type(credential) is not PinnedCredential:
        return False
    try:
        return (
            _bytes(credential.credential_id, 1, 1024)
            and _bytes(credential.user_handle, 1, 64)
            and type(credential.rp_id) is str and len(credential.rp_id) <= 253
            and re.fullmatch(_DNS_LABEL + r"(?:\." + _DNS_LABEL + r")*", credential.rp_id) is not None
            and type(credential.origin) is str
            and credential.origin == "https://" + credential.rp_id
            and _bytes(credential.public_key_spki, 91, 91)
            and credential.public_key_spki.startswith(_P256_SPKI_PREFIX)
        )
    except AttributeError:
        return False


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate client-data key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("non-JSON numeric constant")


class AssertionVerifier:
    """A2.1 callback: validate a narrow ES256 profile, then verify original bytes."""

    def __init__(self, credential, *, verify_signature):
        if not _valid_pin(credential) or not callable(verify_signature):
            raise ContractError("a pinned P-256 credential and signature verifier are required")
        self._credential = credential
        self._verify_signature = verify_signature

    def _signed_bytes(self, request, response):
        if type(request) is not AttemptRequest or type(response) is not Assertion:
            return None
        try:
            if not (_bytes(request.challenge, 32, 32)
                    and _bytes(response.credential_id, 1, 1024)
                    and _bytes(response.client_data_json, 1, 8192)
                    and _bytes(response.authenticator_data, 37, 37)
                    and _bytes(response.signature, 8, 72)):
                return None
            pin = self._credential
            if response.credential_id != pin.credential_id:
                return None
            if response.user_handle is not None and (
                    not _bytes(response.user_handle, 1, 64) or response.user_handle != pin.user_handle):
                return None
            client = json.loads(response.client_data_json.decode("utf-8"),
                                object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            if type(client) is not dict or set(client) - {"type", "challenge", "origin", "crossOrigin"}:
                return None
            expected_challenge = base64.urlsafe_b64encode(request.challenge).rstrip(b"=").decode("ascii")
            if (client.get("type") != "webauthn.get"
                    or client.get("challenge") != expected_challenge
                    or client.get("origin") != pin.origin
                    or client.get("crossOrigin", False) is not False):
                return None
            auth = response.authenticator_data
            if auth[:32] != hashlib.sha256(pin.rp_id.encode("ascii")).digest() or auth[32] != 0x05:
                return None
            # Preserve the exact wire JSON. Normalizing it would verify another message.
            return auth + hashlib.sha256(response.client_data_json).digest()
        except (AttributeError, UnicodeError, ValueError, RecursionError):
            return None

    def __call__(self, request, response):
        signed_bytes = self._signed_bytes(request, response)
        if signed_bytes is None:
            return False
        # Backend errors must reach A2.1's failed state, not masquerade as denial.
        verified = self._verify_signature(self._credential.public_key_spki,
                                          signed_bytes, response.signature)
        if type(verified) is not bool:
            raise ContractError("signature verifier must return an exact boolean")
        return verified
