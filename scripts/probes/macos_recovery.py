"""Disposable encrypted candidate recovery; no real-source CLI or product custody.

The native helper uses internal binary pipes. Never run it with a real recovery
key in shell arguments, a file, diagnostics or provider context. This experiment
generates throwaway keys, persists ciphertext only and restores no authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile

from claimbranch.core.canonical import ContractError, decode, digest_text, identifier
from claimbranch.core.recovery import pack_history, unpack_history
from claimbranch.fixtures import replay_example
from .macos_authorization import ProbeError, temporary_root


SOURCE = Path(__file__).with_name("native") / "MacRecovery.swift"
MAGIC = b"CBRE\x00\x01"
MAX_PLAINTEXT = 270336
OVERHEAD = 66
MAX_CIPHERTEXT = MAX_PLAINTEXT + OVERHEAD
FILES = {"backup.cbr", "restored.cbr"}


class RecoveryRejected(ProbeError):
    """The bounded recovery input was rejected without recovered output."""


class AuthenticationRejected(RecoveryRejected):
    """The native AEAD authentication check rejected this input."""


def build(root):
    binary = root / "recovery-helper"
    result = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(binary)],
                            capture_output=True, timeout=90, check=False)
    if result.returncode:
        raise ProbeError("Native recovery helper could not be built")
    return binary


def check_crypto(binary):
    result = subprocess.run([str(binary), "check"], input=b"", capture_output=True, timeout=15, check=False)
    if (result.returncode, result.stdout, result.stderr) != (0, b"recovery-crypto-ok\n", b""):
        raise ProbeError("Native recovery known-answer check failed")


def crypt(binary, mode, payload, key):
    if (mode not in ("seal", "open") or type(key) is not bytes or len(key) != 32
            or type(payload) is not bytes or not payload
            or len(payload) > (MAX_PLAINTEXT if mode == "seal" else MAX_CIPHERTEXT)):
        raise RecoveryRejected("Invalid bounded recovery input")
    result = subprocess.run([str(binary), mode], input=key + payload,
                            capture_output=True, timeout=15, check=False)
    if (result.returncode, result.stdout, result.stderr) == (2, b"", b"authentication-rejected\n"):
        raise AuthenticationRejected("Recovery authentication rejected")
    if (result.returncode, result.stdout, result.stderr) == (1, b"", b"recovery-rejected\n"):
        raise RecoveryRejected("Recovery input rejected")
    expected = len(payload) + (OVERHEAD if mode == "seal" else -OVERHEAD)
    if (result.returncode or result.stderr or not 0 < len(result.stdout) == expected
            or (mode == "seal" and not result.stdout.startswith(MAGIC))):
        raise ProbeError("Native recovery result violated its protocol")
    return result.stdout


def _directory(root, name):
    root = Path(root)
    if (name not in FILES or root.parent != temporary_root()
            or not root.name.startswith("claimbranch-recovery-") or root.resolve(strict=True) != root):
        raise ProbeError("An owned recovery experiment directory and fixed filename are required")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise ProbeError("Recovery experiment directory is not private")
    return fd


def _ciphertext(raw):
    if type(raw) is not bytes or not OVERHEAD < len(raw) <= MAX_CIPHERTEXT or not raw.startswith(MAGIC):
        raise RecoveryRejected("Unknown or unbounded encrypted archive")


def write_archive(root, name, ciphertext, *, before_publish=None):
    """Publish ciphertext without replacing any existing destination, even a link.

    A handled pre-publication interruption removes only its owned staging file.
    A hard process crash may leave staging ciphertext; it is not a valid restore.
    A failure after publication is reported, never rolled back over a new file.
    This bounded POSIX experiment is not a worker-isolation implementation.
    """
    _ciphertext(ciphertext)
    directory = _directory(root, name)
    staging = ".pending-" + secrets.token_hex(16)
    owned = False
    try:
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        owned = True
        with os.fdopen(fd, "wb") as stream:
            stream.write(ciphertext)
            stream.flush()
            os.fsync(stream.fileno())
        if before_publish is not None:
            before_publish()
        # Same-directory hard-link publication is atomic and cannot clobber.
        os.link(staging, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.unlink(staging, dir_fd=directory)
        owned = False
        os.fsync(directory)
    finally:
        try:
            if owned:
                os.unlink(staging, dir_fd=directory)
        finally:
            os.close(directory)


def read_archive(root, name):
    directory = _directory(root, name)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or not OVERHEAD < info.st_size <= MAX_CIPHERTEXT):
                raise RecoveryRejected("Archive is not a bounded private regular file")
            raw = stream.read(MAX_CIPHERTEXT + 1)
        _ciphertext(raw)
        return raw
    finally:
        os.close(directory)


def restore_candidate(root, binary, recovery_key, local_key, *, expected_project_id,
                      expected_manifest_digest, before_publish=None):
    """Recover a pinned candidate and publish only reencrypted bytes, never authority."""
    identifier(expected_project_id)
    digest_text(expected_manifest_digest)
    if type(local_key) is not bytes or len(local_key) != 32 or local_key == recovery_key:
        raise RecoveryRejected("A distinct disposable local key is required")
    plaintext = crypt(binary, "open", read_archive(root, "backup.cbr"), recovery_key)
    history = unpack_history(plaintext, expected_project_id=expected_project_id,
                             expected_manifest_digest=expected_manifest_digest)
    encrypted = crypt(binary, "seal", pack_history(history), local_key)
    write_archive(root, "restored.cbr", encrypted, before_publish=before_publish)
    return history


def exercise_recovery(root, binary):
    history = replay_example("recorded", series=True)
    plaintext = pack_history(history)
    project = decode(history.seed)["project_id"]
    expected = hashlib.sha256(history.manifest()).hexdigest()
    recovery, local = secrets.token_bytes(32), secrets.token_bytes(32)
    backup = crypt(binary, "seal", plaintext, recovery)
    write_archive(root, "backup.cbr", backup)

    def rejected(action, kind):
        try:
            action()
        except kind:
            return True
        raise ProbeError("An invalid recovery input was not rejected")

    wrong_key = rejected(lambda: crypt(binary, "open", backup, secrets.token_bytes(32)), AuthenticationRejected)
    tampered = backup[:-1] + bytes([backup[-1] ^ 1])
    tamper = rejected(lambda: crypt(binary, "open", tampered, recovery), AuthenticationRejected)
    cross_project = rejected(lambda: restore_candidate(root, binary, recovery, local,
        expected_project_id="another-project", expected_manifest_digest=expected), ContractError)
    snapshot = rejected(lambda: restore_candidate(root, binary, recovery, local,
        expected_project_id=project, expected_manifest_digest="0" * 64), ContractError)

    def interrupt():
        raise InterruptedError("synthetic interruption")

    interrupted = rejected(lambda: restore_candidate(root, binary, recovery, local,
        expected_project_id=project, expected_manifest_digest=expected, before_publish=interrupt), InterruptedError)
    if (root / "restored.cbr").exists() or list(root.glob(".pending-*")):
        raise ProbeError("Interrupted recovery left a published or staged result")
    restored = restore_candidate(root, binary, recovery, local,
        expected_project_id=project, expected_manifest_digest=expected)
    destination = read_archive(root, "restored.cbr")
    if crypt(binary, "open", destination, local) != plaintext or restored.manifest() != history.manifest():
        raise ProbeError("Recovered candidate differs from the original history")
    rejected(lambda: crypt(binary, "open", destination, recovery), AuthenticationRejected)
    existing = rejected(lambda: restore_candidate(root, binary, recovery, local,
        expected_project_id=project, expected_manifest_digest=expected), FileExistsError)
    if read_archive(root, "restored.cbr") != destination or read_archive(root, "backup.cbr") != backup:
        raise ProbeError("Recovery overwrote an existing archive")
    return {"status": "recovery_observed", "operations": len(history.commands),
            "history_roundtrip_verified": True, "encrypted_destination_verified": True,
            "wrong_key_rejected": wrong_key, "tamper_rejected": tamper,
            "cross_project_rejected": cross_project, "snapshot_mismatch_rejected": snapshot,
            "interrupted_restore_unpublished": interrupted, "existing_destination_preserved": existing,
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
            "status": "available", "known_answers_verified": True, "authorization_verified": False,
            "product_custody_verified": False, "cross_device_verified": False}
    if root.exists():
        raise ProbeError("Recovery experiment cleanup is incomplete")
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
        # No exception strings: subprocess errors may contain input/output.
        result = {"status": "error", "reason": "Recovery experiment could not complete",
                  "authorization_verified": False, "product_custody_verified": False,
                  "cross_device_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("available", "recovery_observed") else (3 if result["status"] == "unsupported" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
