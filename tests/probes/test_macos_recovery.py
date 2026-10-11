"""Real encryption of synthetic bytes, never production custody or enrollment."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.recovery import pack_history
from claimbranch.fixtures import replay_example
from scripts.probes.macos_authorization import ProbeError, temporary_root
from scripts.probes.macos_recovery import (MAX_CIPHERTEXT, MAX_PLAINTEXT, AuthenticationRejected,
    RecoveryRejected, build, crypt, main, probe, read_archive, restore_candidate, write_archive)


@unittest.skipUnless(sys.platform == "darwin", "real CryptoKit recovery requires macOS")
class NativeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root())
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.binary = build(cls.root)
        cls.history = replay_example("recorded", series=True)
        cls.plain = pack_history(cls.history)
        cls.project = decode(cls.history.seed)["project_id"]
        cls.expected = hashlib.sha256(cls.history.manifest()).hexdigest()

    def test_native_known_answer_vectors(self):
        result = subprocess.run([str(self.binary), "check"], input=b"", capture_output=True, timeout=15)
        self.assertEqual((0, b"recovery-crypto-ok\n", b""), (result.returncode, result.stdout, result.stderr))

    def test_separate_processes_decrypt_identical_history_with_randomized_ciphertext(self):
        key = secrets.token_bytes(32)
        first = crypt(self.binary, "seal", self.plain, key)
        second = crypt(self.binary, "seal", self.plain, key)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first[6:38], second[6:38])
        self.assertNotIn(self.history.seed, first)
        self.assertEqual(self.plain, crypt(self.binary, "open", first, key))
        self.assertEqual(self.plain, crypt(self.binary, "open", second, key))

    def test_wrong_keys_and_changed_authenticated_bytes_release_no_plaintext(self):
        key = secrets.token_bytes(32)
        archive = crypt(self.binary, "seal", self.plain, key)
        with self.assertRaises(AuthenticationRejected):
            crypt(self.binary, "open", archive, secrets.token_bytes(32))
        for index in (6, 37, 38, 49, 50, len(archive) - 1):
            changed = bytearray(archive)
            changed[index] ^= 1
            with self.subTest(index=index), self.assertRaises(AuthenticationRejected):
                crypt(self.binary, "open", bytes(changed), key)
        for changed in (archive[:-1], archive + b"x", b"CBRE\x00\x02" + archive[6:]):
            with self.subTest(length=len(changed)), self.assertRaises(RecoveryRejected):
                crypt(self.binary, "open", changed, key)

    def test_native_request_limits_and_errors_do_not_echo_input(self):
        sentinel = b"private-synthetic-sentinel"
        cases = [(["unknown"], sentinel), (["seal", sentinel.decode()], sentinel),
                 (["check"], sentinel), (["seal"], bytes(32)),
                 (["seal"], bytes(32) + b"a" * (MAX_PLAINTEXT + 1)),
                 (["open"], bytes(32) + b"a" * (MAX_CIPHERTEXT + 1))]
        for arguments, raw in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run([str(self.binary), *arguments], input=raw, capture_output=True, timeout=15)
                self.assertEqual(1, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertEqual(b"recovery-rejected\n", result.stderr)
        for key in (b"", bytes(31), bytes(33), "not-bytes"):
            with self.subTest(key_type=type(key).__name__), self.assertRaises(ProbeError):
                crypt(self.binary, "seal", sentinel, key)

    def test_maximum_payload_and_chunked_pipe_are_supported(self):
        key = secrets.token_bytes(32)
        plain = b"x" * MAX_PLAINTEXT
        archive = crypt(self.binary, "seal", plain, key)
        self.assertEqual(MAX_CIPHERTEXT, len(archive))
        self.assertEqual(plain, crypt(self.binary, "open", archive, key))
        with subprocess.Popen([str(self.binary), "seal"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            for part in (key[:8], key[8:], b"chunk-", b"one"):
                process.stdin.write(part)
                process.stdin.flush()
            process.stdin.close()
            process.stdin = None
            output, error = process.communicate(timeout=15)
            self.assertEqual((0, b""), (process.returncode, error))
        self.assertEqual(b"chunk-one", crypt(self.binary, "open", output, key))

    def test_restore_validates_before_writing_and_reencrypts_under_a_new_local_key(self):
        with tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
            root = Path(directory)
            recovery, local = secrets.token_bytes(32), secrets.token_bytes(32)
            archive = crypt(self.binary, "seal", self.plain, recovery)
            write_archive(root, "backup.cbr", archive)
            history = restore_candidate(root, self.binary, recovery, local,
                expected_project_id=self.project, expected_manifest_digest=self.expected)
            self.assertEqual(self.history.manifest(), history.manifest())
            self.assertFalse(history.authorization_verified)
            destination = read_archive(root, "restored.cbr")
            self.assertEqual(self.plain, crypt(self.binary, "open", destination, local))
            with self.assertRaises(AuthenticationRejected):
                crypt(self.binary, "open", destination, recovery)
            self.assertEqual(archive, read_archive(root, "backup.cbr"))
            with self.assertRaises(FileExistsError):
                restore_candidate(root, self.binary, recovery, local,
                    expected_project_id=self.project, expected_manifest_digest=self.expected)
            self.assertEqual(destination, read_archive(root, "restored.cbr"))

    def test_invalid_key_project_snapshot_and_authenticated_payload_cannot_publish(self):
        for case in ("key", "project", "snapshot", "missing-snapshot", "payload"):
            with self.subTest(case=case), tempfile.TemporaryDirectory(
                    prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
                root = Path(directory)
                recovery = secrets.token_bytes(32)
                raw = self.plain if case != "payload" else b"authenticated but invalid history"
                archive = crypt(self.binary, "seal", raw, recovery)
                write_archive(root, "backup.cbr", archive)
                with self.assertRaises((RecoveryRejected, ContractError)):
                    restore_candidate(root, self.binary, secrets.token_bytes(32) if case == "key" else recovery,
                        secrets.token_bytes(32), expected_project_id="another-project" if case == "project" else self.project,
                        expected_manifest_digest=(None if case == "missing-snapshot" else
                                                  "0" * 64 if case == "snapshot" else self.expected))
                self.assertEqual(["backup.cbr"], sorted(p.name for p in root.iterdir()))
                self.assertEqual(archive, read_archive(root, "backup.cbr"))

    def test_interrupted_restore_preserves_backup_and_leaves_no_destination(self):
        with tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root()) as directory:
            root = Path(directory)
            recovery = secrets.token_bytes(32)
            archive = crypt(self.binary, "seal", self.plain, recovery)
            write_archive(root, "backup.cbr", archive)
            def interrupt():
                self.assertFalse((root / "restored.cbr").exists())
                raise InterruptedError("synthetic interruption")
            with self.assertRaises(InterruptedError):
                restore_candidate(root, self.binary, recovery, secrets.token_bytes(32),
                    expected_project_id=self.project, expected_manifest_digest=self.expected, before_publish=interrupt)
            self.assertEqual(["backup.cbr"], sorted(p.name for p in root.iterdir()))
            self.assertEqual(archive, read_archive(root, "backup.cbr"))


@unittest.skipUnless(os.name == "posix", "descriptor-relative probe files require POSIX")
class RecoveryFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claimbranch-recovery-", dir=temporary_root())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cipher = b"CBRE\x00\x01" + bytes(61)

    def test_private_files_are_new_only_and_destination_race_never_overwrites(self):
        write_archive(self.root, "backup.cbr", self.cipher)
        self.assertEqual(0o600, stat.S_IMODE((self.root / "backup.cbr").stat().st_mode))
        self.assertEqual(self.cipher, read_archive(self.root, "backup.cbr"))
        with self.assertRaises(FileExistsError):
            write_archive(self.root, "backup.cbr", self.cipher)
        def occupy():
            (self.root / "restored.cbr").write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            write_archive(self.root, "restored.cbr", self.cipher, before_publish=occupy)
        self.assertEqual(b"existing", (self.root / "restored.cbr").read_bytes())
        self.assertFalse(list(self.root.glob(".pending-*")))

    def test_aliases_permissions_special_files_and_unsafe_names_are_rejected(self):
        write_archive(self.root, "backup.cbr", self.cipher)
        target = self.root / "restored.cbr"
        for kind in ("symlink", "hardlink", "fifo", "directory"):
            with self.subTest(kind=kind):
                if kind == "symlink": target.symlink_to("backup.cbr")
                elif kind == "hardlink": os.link(self.root / "backup.cbr", target)
                elif kind == "fifo": os.mkfifo(target, 0o600)
                else: target.mkdir()
                with self.assertRaises((ProbeError, OSError)):
                    read_archive(self.root, "restored.cbr")
                with self.assertRaises(FileExistsError):
                    write_archive(self.root, "restored.cbr", self.cipher)
                target.rmdir() if kind == "directory" else target.unlink()
        (self.root / "backup.cbr").chmod(0o644)
        with self.assertRaises(ProbeError): read_archive(self.root, "backup.cbr")
        for name in ("../escape", "/tmp/escape", "nested/file", "key.txt"):
            with self.subTest(name=name), self.assertRaises(ProbeError):
                write_archive(self.root, name, self.cipher)
        self.root.chmod(0o755)
        with self.assertRaises(ProbeError): read_archive(self.root, "backup.cbr")
        self.root.chmod(0o700)


class RecoveryDriverTests(unittest.TestCase):
    def test_unsupported_host_does_not_build_or_create_files(self):
        with patch("scripts.probes.macos_recovery.sys.platform", "win32"), \
                patch("scripts.probes.macos_recovery.build") as compile_native:
            self.assertEqual("unsupported", probe(exercise=True)["status"])
            compile_native.assert_not_called()

    def test_public_errors_never_print_subprocess_input_or_secret_exception_text(self):
        failure = subprocess.TimeoutExpired(["secret-path"], 15, output=b"private-payload", stderr=b"private-key")
        with patch("scripts.probes.macos_recovery.probe", side_effect=failure), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(1, main(["--exercise"]))
        result = json.loads(output.getvalue())
        self.assertEqual("error", result["status"])
        self.assertFalse(result["authorization_verified"])
        self.assertNotIn("private", output.getvalue())
        self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
