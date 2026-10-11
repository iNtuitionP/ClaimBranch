"""Synthetic signed-candidate recovery; no device enrollment or write authority.

The signing fixture exists only in native process memory. Restore requires
external signer/checkpoint pins and preserves the original signed bytes. The
CLI accepts no private sources, key material, paths or production credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import tempfile

from claimbranch.core.canonical import ContractError, decode, digest_text, identifier
from claimbranch.core.recovery import pack_history
from claimbranch.core.recovery_checkpoint import (MAX_CHECKPOINT_BYTES, checkpoint_message,
    pack_signed_history, signature_fields, unpack_signed_history)
from claimbranch.fixtures import replay_example
from .macos_authorization import ProbeError, temporary_root
from .macos_recovery import (AuthenticationRejected, RecoveryRejected, build, check_crypto,
    crypt, read_archive, write_archive)


class SignatureRejected(RecoveryRejected):
    """Native P-256 verification rejected the key, signature or message."""


def _message(message):
    if type(message) is not bytes or not 1 <= len(message) <= MAX_CHECKPOINT_BYTES:
        raise RecoveryRejected("A bounded checkpoint message is required")


def verify_signature(binary, message, public_key, signature):
    _message(message)
    signature_fields(public_key, signature)
    request = struct.pack(">H", len(signature)) + public_key + signature + message
    result = subprocess.run([str(binary), "verify-checkpoint"], input=request,
                            capture_output=True, timeout=15, check=False)
    outcome = result.returncode, result.stdout, result.stderr
    if outcome == (2, b"", b"signature-rejected\n"):
        raise SignatureRejected("Recovery checkpoint signature rejected")
    if outcome == (1, b"", b"recovery-rejected\n"):
        raise RecoveryRejected("Recovery checkpoint input rejected")
    if outcome != (0, b"signature-verified\n", b""):
        raise ProbeError("Native checkpoint verifier violated its protocol")
    return True


def fixture_signature(binary, message):
    """Generate disposable software test material, never a device signature."""
    _message(message)
    result = subprocess.run([str(binary), "fixture-sign"], input=message,
                            capture_output=True, timeout=15, check=False)
    if result.returncode or result.stderr or not 73 <= len(result.stdout) <= 137:
        raise ProbeError("Native signature fixture violated its protocol")
    public_key, signature = result.stdout[:65], result.stdout[65:]
    verify_signature(binary, message, public_key, signature)
    return public_key, signature


def restore_signed_candidate(root, binary, recovery_key, local_key, *, expected_project_id,
                             expected_signer_digest, expected_checkpoint_digest, before_publish=None):
    """Verify external pins and signature, then publish reencrypted candidate bytes.

    No unsigned fallback, accepted receipts, new signing key or authority change
    is supplied. The caller must obtain both expectations outside the backup.
    """
    identifier(expected_project_id)
    digest_text(expected_signer_digest)
    digest_text(expected_checkpoint_digest)
    if type(local_key) is not bytes or len(local_key) != 32 or local_key == recovery_key:
        raise RecoveryRejected("A distinct disposable local key is required")
    plaintext = crypt(binary, "open", read_archive(root, "backup.cbr"), recovery_key)
    parsed = unpack_signed_history(plaintext, expected_project_id=expected_project_id,
        expected_signer_digest=expected_signer_digest, expected_checkpoint_digest=expected_checkpoint_digest)
    verify_signature(binary, parsed.message, parsed.public_key, parsed.signature)
    encrypted = crypt(binary, "seal", plaintext, local_key)
    write_archive(root, "restored.cbr", encrypted, before_publish=before_publish)
    return parsed.history


def exercise_recovery(root, binary):
    history = replay_example("recorded", series=True)
    checkpoint_id = "synthetic-checkpoint-1"
    message = checkpoint_message(history, checkpoint_id)
    public_key, signature = fixture_signature(binary, message)
    plaintext = pack_signed_history(history, checkpoint_id, public_key, signature)
    pins = {"expected_project_id": decode(history.seed)["project_id"],
            "expected_signer_digest": hashlib.sha256(public_key).hexdigest(),
            "expected_checkpoint_digest": hashlib.sha256(message).hexdigest()}
    recovery, local = secrets.token_bytes(32), secrets.token_bytes(32)
    backup = crypt(binary, "seal", plaintext, recovery)
    write_archive(root, "backup.cbr", backup)

    def rejected(action, kind):
        try:
            action()
        except kind:
            return True
        raise ProbeError("Invalid signed recovery input was not rejected")

    other_public, other_signature = fixture_signature(binary, message)
    rejected(lambda: verify_signature(binary, message, public_key, other_signature), SignatureRejected)
    rejected(lambda: verify_signature(binary, message + b" ", public_key, signature), SignatureRejected)
    substituted = pack_signed_history(history, checkpoint_id, other_public, other_signature)
    rejected(lambda: unpack_signed_history(substituted, **pins), ContractError)
    rejected(lambda: unpack_signed_history(pack_history(history), **pins), ContractError)
    for field, value in (("expected_project_id", "another-project"),
                         ("expected_checkpoint_digest", "0" * 64)):
        rejected(lambda: restore_signed_candidate(root, binary, recovery, local,
            **{**pins, field: value}), ContractError)
    rejected(lambda: crypt(binary, "open", backup, secrets.token_bytes(32)), AuthenticationRejected)
    tampered = backup[:-1] + bytes([backup[-1] ^ 1])
    rejected(lambda: crypt(binary, "open", tampered, recovery), AuthenticationRejected)

    def interrupt():
        raise InterruptedError("synthetic interruption")

    rejected(lambda: restore_signed_candidate(root, binary, recovery, local,
        **pins, before_publish=interrupt), InterruptedError)
    if (root / "restored.cbr").exists() or list(root.glob(".pending-*")):
        raise ProbeError("Interrupted signed recovery left a published or staged result")
    restored = restore_signed_candidate(root, binary, recovery, local, **pins)
    destination = read_archive(root, "restored.cbr")
    readback = crypt(binary, "open", destination, local)
    if (readback != plaintext or restored.manifest() != history.manifest()
            or restored.authorization_verified):
        raise ProbeError("Signed candidate recovery changed history or authority")
    parsed = unpack_signed_history(readback, **pins)
    verify_signature(binary, parsed.message, parsed.public_key, parsed.signature)
    rejected(lambda: crypt(binary, "open", destination, recovery), AuthenticationRejected)
    rejected(lambda: restore_signed_candidate(root, binary, recovery, local, **pins), FileExistsError)
    if read_archive(root, "restored.cbr") != destination or read_archive(root, "backup.cbr") != backup:
        raise ProbeError("Signed recovery overwrote an existing archive")
    return {"status": "signed_recovery_observed", "operations": len(history.commands),
            "signer_scope": "disposable-software-fixture", "signature_verified": True,
            "original_signed_bytes_preserved": True, "history_roundtrip_verified": True,
            "encrypted_destination_verified": True, "forged_signature_rejected": True,
            "changed_message_rejected": True, "signer_substitution_rejected": True,
            "unsigned_downgrade_rejected": True, "cross_project_rejected": True,
            "checkpoint_mismatch_rejected": True, "wrong_key_rejected": True, "tamper_rejected": True,
            "interrupted_restore_unpublished": True, "existing_destination_preserved": True,
            "authorization_verified": False, "product_custody_verified": False,
            "cross_device_verified": False}


def probe(*, exercise=False):
    if sys.platform != "darwin":
        return {"status": "unsupported", "authorization_verified": False,
                "product_custody_verified": False, "cross_device_verified": False}
    with tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
        root = Path(directory)
        binary = build(root)
        check_crypto(binary)
        result = exercise_recovery(root, binary) if exercise else {
            "status": "available", "known_answers_verified": True, "signature_verified": False,
            "authorization_verified": False, "product_custody_verified": False,
            "cross_device_verified": False}
    if root.exists():
        raise ProbeError("Signed recovery experiment cleanup is incomplete")
    return {**result, "cleanup_verified": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--exercise", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = probe(exercise=args.exercise)
    except (OSError, subprocess.TimeoutExpired, ProbeError, ContractError):
        result = {"status": "error", "reason": "Signed recovery experiment could not complete",
                  "signature_verified": False, "authorization_verified": False,
                  "product_custody_verified": False, "cross_device_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("available", "signed_recovery_observed") else (3 if result["status"] == "unsupported" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
