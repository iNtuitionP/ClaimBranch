from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.device_work_store import DevicePaperWorkStore, project_binding, split_device_checkpoint
from claimbranch.application.paper_work_store import PaperWork, PaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.application.work_cipher import MAX_KEY_BYTES
from claimbranch.core.canonical import ContractError
from tests.application.test_paper_review_policy import ai_draft
from tests.contract.test_paper_episodes import first_episode


class DeviceFrameTests(unittest.TestCase):
    def test_malformed_unknown_and_oversized_frames_fail(self):
        for raw in (b'', b'CBWD\x00\x02', b'CBWD\x00\x01' + b'\xff' * 4,
                    b'x' * 300000, 'not bytes'):
            with self.subTest(size=len(raw)), self.assertRaises(ContractError):
                split_device_checkpoint(raw)

    def test_complete_frames_exercise_each_length_and_magic_boundary(self):
        envelope = b'CBKY\x00\x01' + bytes(226) + b'\x00\x01' + bytes(153)
        encrypted = b'CBWK\x00\x01' + bytes(61)
        prefix = b'CBWD\x00\x01' + len(envelope).to_bytes(4, 'big')
        valid = prefix + envelope + encrypted
        self.assertEqual((envelope, encrypted), split_device_checkpoint(valid))
        cases = [b'CBWD\x00\x02' + valid[6:],
                 valid[:6] + (386).to_bytes(4, 'big') + valid[10:],
                 valid[:6] + (MAX_KEY_BYTES + 1).to_bytes(4, 'big') + valid[10:],
                 valid[:6] + (1000).to_bytes(4, 'big') + valid[10:],
                 prefix + b'BADKEY' + envelope[6:] + encrypted,
                 prefix + envelope + b'BADBOX' + encrypted[6:],
                 prefix + envelope + encrypted[:66],
                 prefix + envelope + b'CBWK\x00\x01' + bytes(262205),
                 prefix + envelope[:232] + b'\x00\x00' + envelope[234:] + encrypted,
                 prefix + envelope[:232] + b'\x00\x02' + envelope[234:] + encrypted]
        for index, raw in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ContractError):
                split_device_checkpoint(raw)


@unittest.skipUnless(sys.platform == 'darwin', 'macOS Secure Enclave required')
class DeviceWorkStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cipher = MacWorkCipher().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cipher.__exit__(None, None, None)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claimbranch-device-work-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.original, self.restored = self.root / 'original', self.root / 'restored'
        self.original.mkdir(mode=0o700)
        self.restored.mkdir(mode=0o700)
        self.recovery = os.urandom(32)
        self.work = PaperWork.create(first_episode(ai=True, merge=False, close=False),
                                    episode_id='episode', judgment=ai_draft())

    def create(self):
        return DevicePaperWorkStore.create(self.original, cipher=self.cipher,
                                          project_id='project', recovery_key=self.recovery)

    def reopen(self, **overrides):
        return DevicePaperWorkStore(self.original, cipher=self.cipher,
                                   **{'project_id': 'project', **overrides})

    def test_device_reopen_keeps_work_without_retaining_raw_data_key(self):
        with patch.object(self.cipher, 'create_work_key', wraps=self.cipher.create_work_key) as wrapping:
            with self.create() as store:
                store.save(self.work)
                backup = store.backup()
            self.assertNotIn(wrapping.call_args.args[0], backup)
        with self.reopen() as store:
            restored = store.load()
            self.assertEqual(self.work.payload, restored.payload)
            self.assertTrue(restored.judgment.ai_influenced)
            self.assertFalse(restored.history.authorization_verified)
            self.assertEqual(backup, store.backup())
        self.assertEqual({'work.cbw', 'work.lock'}, {p.name for p in self.original.iterdir()})
        self.assertNotIn(self.recovery, backup)
        self.assertNotIn(b'proposal-policy', backup)
        with self.reopen(project_id='other') as store, self.assertRaises(ContractError):
            store.load()

    def test_fresh_process_reopens_without_key_on_stdin_or_argv(self):
        with self.create() as store:
            store.save(self.work)
        code = '''import sys
from claimbranch.application.device_work_store import DevicePaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
with MacWorkCipher() as cipher:
    with DevicePaperWorkStore(sys.argv[1], cipher=cipher, project_id='project') as store:
        sys.stdout.buffer.write(store.load().payload)
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.original)],
                                input=b'', capture_output=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.work.payload, result.stdout)

    def test_backup_restore_uses_recovery_without_opening_old_device_key(self):
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
        with patch.object(self.cipher, 'open_work_key', side_effect=ContractError('device unavailable')):
            restored = DevicePaperWorkStore.restore_backup(backup, self.restored,
                cipher=self.cipher, project_id='project', recovery_key=self.recovery)
        self.assertEqual(self.work.payload, restored.payload)
        with DevicePaperWorkStore(self.restored, cipher=self.cipher, project_id='project') as store:
            self.assertEqual(self.work.payload, store.load().payload)
            new_backup = store.backup()
        self.assertNotEqual(split_device_checkpoint(backup)[0], split_device_checkpoint(new_backup)[0])
        self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())
        envelope, _ = split_device_checkpoint(backup)
        recovered_key = self.cipher.recover_work_key(envelope, self.recovery, project_binding('project'))
        for directory in (self.original, self.restored):
            for path in directory.iterdir():
                self.assertNotIn(recovered_key, path.read_bytes())
                self.assertNotIn(self.recovery, path.read_bytes())

    def test_wrong_project_key_corruption_and_existing_destination_preserve_original(self):
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
        for raw, project, recovery in ((backup, 'other', self.recovery),
            (backup, 'project', os.urandom(32)), (backup[:-1] + bytes([backup[-1] ^ 1]), 'project', self.recovery)):
            with self.assertRaises(ContractError):
                DevicePaperWorkStore.restore_backup(raw, self.restored, cipher=self.cipher,
                    project_id=project, recovery_key=recovery)
            self.assertFalse((self.restored / 'work.cbw').exists())
            self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())
        with self.assertRaises(ContractError):
            DevicePaperWorkStore.restore_backup(backup, self.original, cipher=self.cipher,
                project_id='project', recovery_key=self.recovery)
        self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())

    def test_no_auto_create_downgrade_recovery_or_existing_key_replacement(self):
        with self.assertRaises(ContractError):
            with self.reopen():
                pass
        self.assertFalse((self.original / 'work.cbw').exists())
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
        with self.assertRaises(ContractError):
            with self.create():
                pass
        with PaperWorkStore(self.original, cipher=self.cipher, key=self.recovery, project_id='project') as store:
            with self.assertRaises(ContractError):
                store.load()
        with patch.object(self.cipher, 'open_work_key', side_effect=ContractError('device unavailable')):
            with self.reopen() as store:
                with self.assertRaises(ContractError):
                    store.load()
        self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())

    def test_failed_save_retains_complete_key_and_work_envelope(self):
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
            with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('injected')):
                with self.assertRaises(ContractError):
                    store.save(self.work)
            self.assertEqual(backup, store.backup())
        with self.reopen() as store:
            self.assertEqual(self.work.payload, store.load().payload)

    def test_both_unlock_routes_authenticate_the_entire_key_envelope(self):
        with self.create() as store:
            store.save(self.work)
            envelope, _ = split_device_checkpoint(store.backup())
        header_size = 234 + int.from_bytes(envelope[232:234], 'big')
        for position in (6, 38, 103, 168, 200, 234, header_size, header_size + 60, len(envelope) - 1):
            changed = envelope[:position] + bytes([envelope[position] ^ 1]) + envelope[position + 1:]
            with self.subTest(position=position, route='device'), self.assertRaises(ContractError):
                self.cipher.open_work_key(changed, project_binding('project'))
            with self.subTest(position=position, route='recovery'), self.assertRaises(ContractError):
                self.cipher.recover_work_key(changed, self.recovery, project_binding('project'))

    def test_interrupted_restore_does_not_replace_source_or_publish_partial_target(self):
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
        with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('injected')):
            with self.assertRaises(ContractError):
                DevicePaperWorkStore.restore_backup(backup, self.restored, cipher=self.cipher,
                    project_id='project', recovery_key=self.recovery)
        self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())
        self.assertFalse((self.restored / 'work.cbw').exists())
        DevicePaperWorkStore.restore_backup(backup, self.restored, cipher=self.cipher,
            project_id='project', recovery_key=self.recovery)
        with DevicePaperWorkStore(self.restored, cipher=self.cipher, project_id='project') as store:
            self.assertEqual(self.work.payload, store.load().payload)

    def test_restored_envelope_cannot_be_spliced_with_original_work_ciphertext(self):
        with self.create() as store:
            store.save(self.work)
            backup = store.backup()
        DevicePaperWorkStore.restore_backup(backup, self.restored, cipher=self.cipher,
            project_id='project', recovery_key=self.recovery)
        target = self.restored / 'work.cbw'
        envelope, _ = split_device_checkpoint(target.read_bytes())
        _, old_work = split_device_checkpoint(backup)
        mixed = b'CBWD\x00\x01' + len(envelope).to_bytes(4, 'big') + envelope + old_work
        target.write_bytes(mixed)
        with DevicePaperWorkStore(self.restored, cipher=self.cipher, project_id='project') as store:
            with self.assertRaises(ContractError):
                store.load()
        self.assertEqual(backup, (self.original / 'work.cbw').read_bytes())

    def test_optional_recovery_verification_and_empty_backup_report_exact_state(self):
        with self.create() as store:
            with self.assertRaisesRegex(ContractError, 'no saved work'):
                store.backup()
            store.save(self.work)
            raw = store.backup(verify_recovery_key=self.recovery)
            with self.assertRaises(ContractError):
                store.backup(verify_recovery_key=os.urandom(32))
            self.assertEqual(raw, store.backup())

    def test_deleted_checkpoint_after_open_cannot_silently_create_a_new_key(self):
        with self.create() as store:
            store.save(self.work)
        with self.reopen() as store, patch.object(self.cipher, 'create_work_key', wraps=self.cipher.create_work_key) as create:
            (self.original / 'work.cbw').unlink()
            with self.assertRaises(ContractError):
                store.save(self.work)
            create.assert_not_called()
            self.assertFalse((self.original / 'work.cbw').exists())

    def test_raw_key_reader_bounds_input_before_decryption(self):
        path = self.original / 'work.cbw'
        raw = b'x' * 262211
        path.write_bytes(raw)
        path.chmod(0o600)
        with PaperWorkStore(self.original, cipher=self.cipher, key=self.recovery, project_id='project') as store:
            with self.assertRaisesRegex(ContractError, 'exceeds its limit'):
                store.load()
        self.assertEqual(raw, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
