from dataclasses import replace
import hashlib
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application import mac_key_registration as keys
from claimbranch.core.canonical import ContractError, canonical_bytes, decode


@unittest.skipUnless(sys.platform == 'darwin', 'private runtime directories require macOS')
class KeyPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cb-key-intent-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir(mode=0o700)
        self.destination = self.root / 'new-key'
        self.destination.mkdir(mode=0o700)
        self.pin = 'a' * 64
        self.runtime_report = {'build_pin': self.pin, 'roles': {
            'broker': {'code_hash': 'b' * 40}, 'gateway': {'code_hash': 'c' * 40}},
            'authorization_verified': False, 'protected_acceptance_available': False}
        self.check = patch.object(keys, 'check_runtime', return_value=self.runtime_report)
        self.check.start()
        self.addCleanup(self.check.stop)

    def preview(self):
        return keys.preview_key_preparation(self.runtime, self.pin, self.destination, project_id='synthetic-project')

    def test_preview_binds_project_code_destination_without_creating_files(self):
        preview = self.preview()
        value = decode(preview.payload)
        self.assertEqual('synthetic-project', value['project_id'])
        self.assertEqual(self.pin, value['build_pin'])
        self.assertEqual('b' * 40, value['broker_code_hash'])
        self.assertNotIn(str(self.root), preview.payload.decode())
        self.assertEqual([], list(self.destination.iterdir()))
        self.assertEqual(hashlib.sha256(preview.payload).hexdigest(), preview.digest)
        self.assertNotEqual(preview.payload, self.preview().payload)
        self.assertFalse(preview.display()['authorization_verified'])

    def test_existing_destination_is_never_reused_or_overwritten(self):
        (self.destination / 'keep').write_bytes(b'original')
        with patch.object(keys, '_run') as run, self.assertRaises(ContractError): self.preview()
        run.assert_not_called()
        self.assertEqual(b'original', (self.destination / 'keep').read_bytes())

    def test_changed_runtime_or_directory_blocks_before_prompt(self):
        preview = self.preview()
        self.destination.rename(self.root / 'old')
        self.destination.mkdir(mode=0o700)
        with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
            keys.prepare_key(self.runtime, self.pin, self.destination, preview)
        run.assert_not_called()
        preview = self.preview()
        self.runtime_report['roles']['broker']['code_hash'] = 'd' * 40
        with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
            keys.prepare_key(self.runtime, self.pin, self.destination, preview)
        run.assert_not_called()

    def test_changed_preview_digest_and_unknown_fields_are_refused(self):
        original = self.preview()
        bad = decode(original.payload)
        bad['accepted'] = True
        raw = canonical_bytes(bad)
        for preview in (replace(original, digest='f' * 64),
                        replace(original, payload=raw, digest=hashlib.sha256(raw).hexdigest())):
            with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
                keys.prepare_key(self.runtime, self.pin, self.destination, preview)
            run.assert_not_called()

    def test_cancelled_native_preparation_never_reports_registration(self):
        preview = self.preview()
        result = {'schema': 'claimbranch.key-preparation-result/v1', 'status': 'cancelled',
                  'stop_source': 'os-authentication',
                  'request_digest': preview.digest, 'authorization_verified': False,
                  'product_custody_verified': False}
        def cancelled(*args, **kwargs):
            reservation = self.destination / keys.NAME
            reservation.touch(mode=0o600)
            return canonical_bytes(result), b''
        with patch.object(keys, '_run', side_effect=cancelled):
            self.assertEqual(result, keys.prepare_key(self.runtime, self.pin, self.destination, preview))
        self.assertEqual(b'', (self.destination / keys.NAME).read_bytes())

    def test_cancelled_or_expired_nonempty_reservation_requires_inspection(self):
        for status, source in [('cancelled', 'review-window'), ('expired', 'deadline')]:
            with self.subTest(status=status):
                preview = self.preview()
                result = {'schema': 'claimbranch.key-preparation-result/v1', 'status': status,
                          'request_digest': preview.digest, 'authorization_verified': False,
                          'product_custody_verified': False, 'stop_source': source}
                def partial(*args, **kwargs):
                    self.save_record(self.record(preview))
                    return canonical_bytes(result), b''
                with patch.object(keys, '_run', side_effect=partial), self.assertRaisesRegex(ContractError, 'reservation'):
                    keys.prepare_key(self.runtime, self.pin, self.destination, preview)
                self.assertGreater((self.destination / keys.NAME).stat().st_size, 0)
                (self.destination / keys.NAME).unlink()

    def test_native_success_without_matching_private_artifact_is_refused(self):
        preview = self.preview()
        result = {'schema': 'claimbranch.key-preparation-result/v1', 'status': 'prepared',
                  'request_digest': preview.digest, 'registration_digest': 'd' * 64,
                  'public_key_digest': 'e' * 64, 'authorization_verified': False,
                  'product_custody_verified': False}
        with patch.object(keys, '_run', return_value=(canonical_bytes(result), b'')), self.assertRaises(ContractError):
            keys.prepare_key(self.runtime, self.pin, self.destination, preview)

    def record(self, preview):
        import base64
        encode = lambda raw: base64.b64encode(raw).decode('ascii')
        representation = b'not-a-real-device-key'
        value = {'schema': 'claimbranch.key-registration/v1',
                 'body': {'schema': 'claimbranch.key-registration-body/v1',
                          'request': decode(preview.payload), 'public_key_x963': encode(b'\x04' + b'p' * 64),
                          'representation_digest': hashlib.sha256(representation).hexdigest()},
                 'representation': encode(representation), 'signature_der': encode(b'not-a-signature'),
                 'authority': 'unaccepted-key-registration'}
        return value

    def save_record(self, value):
        raw = canonical_bytes(value)
        path = self.destination / keys.NAME
        path.write_bytes(raw)
        path.chmod(0o600)
        return hashlib.sha256(raw).hexdigest()

    def test_wrong_project_code_destination_and_record_pin_refused_before_native(self):
        preview = self.preview()
        value = self.record(preview)
        pin = self.save_record(value)
        cases = [(pin, 'other-project'), ('0' * 64, 'synthetic-project')]
        for expected, project in cases:
            with self.subTest(project=project), patch.object(keys, '_run') as run, self.assertRaises(ContractError):
                keys.reopen_key(self.runtime, self.pin, self.destination, expected, project_id=project)
            run.assert_not_called()
        value['body']['request']['broker_code_hash'] = '0' * 40
        pin = self.save_record(value)
        with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
            keys.reopen_key(self.runtime, self.pin, self.destination, pin, project_id='synthetic-project')
        run.assert_not_called()

    def test_invalid_encoding_digest_authority_and_private_file_refused(self):
        import copy
        value = self.record(self.preview())
        variants = []
        bad = copy.deepcopy(value); bad['representation'] = '!!!!'; variants.append(bad)
        bad = copy.deepcopy(value); bad['body']['representation_digest'] = '0' * 64; variants.append(bad)
        bad = copy.deepcopy(value); bad['authority'] = 'accepted'; variants.append(bad)
        bad = copy.deepcopy(value); bad['signature_der'] = 'YQ=='; variants.append(bad)
        bad = copy.deepcopy(value); bad['receipt'] = True; variants.append(bad)
        for bad in variants:
            expected = self.save_record(bad)
            with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
                keys.reopen_key(self.runtime, self.pin, self.destination, expected, project_id='synthetic-project')
            run.assert_not_called()
        expected = self.save_record(value)
        (self.destination / keys.NAME).chmod(0o644)
        with patch.object(keys, '_run') as run, self.assertRaises(ContractError):
            keys.reopen_key(self.runtime, self.pin, self.destination, expected, project_id='synthetic-project')
        run.assert_not_called()

    def test_reopen_requires_actual_native_verdict_and_rereads_afterwards(self):
        value = self.record(self.preview())
        pin = self.save_record(value)
        result = {'schema': 'claimbranch.key-preparation-result/v1', 'status': 'reopened',
                  'request_digest': hashlib.sha256(canonical_bytes(value['body']['request'])).hexdigest(),
                  'registration_digest': pin, 'public_key_digest': hashlib.sha256(b'\x04' + b'p' * 64).hexdigest(),
                  'noninteractive_signing_denied': True, 'authorization_verified': False,
                  'product_custody_verified': False}
        with patch.object(keys, '_run', return_value=(canonical_bytes(result), b'')):
            self.assertEqual(result, keys.reopen_key(self.runtime, self.pin, self.destination, pin,
                                                   project_id='synthetic-project'))
        with patch.object(keys, '_run', side_effect=ContractError('device refused')), self.assertRaises(ContractError):
            keys.reopen_key(self.runtime, self.pin, self.destination, pin, project_id='synthetic-project')
        def changed(*args, **kwargs):
            (self.destination / keys.NAME).write_bytes(b'changed')
            return canonical_bytes(result), b''
        with patch.object(keys, '_run', side_effect=changed), self.assertRaises(ContractError):
            keys.reopen_key(self.runtime, self.pin, self.destination, pin, project_id='synthetic-project')


class KeyResultTests(unittest.TestCase):
    def test_expiry_and_reopen_result_cannot_claim_wrong_stage(self):
        expired = {'schema': 'claimbranch.key-preparation-result/v1', 'status': 'expired',
                   'request_digest': 'a' * 64, 'authorization_verified': False,
                   'product_custody_verified': False, 'stop_source': 'deadline'}
        self.assertEqual(expired, keys._result(canonical_bytes(expired), 'a' * 64, {'expired'}))
        with self.assertRaises(ContractError):
            keys._result(canonical_bytes({**expired, 'stop_source': 'review-window'}), 'a' * 64, {'expired'})
        reopened = {k: v for k, v in expired.items() if k != 'stop_source'}
        reopened.update(status='reopened', registration_digest='b' * 64, public_key_digest='c' * 64)
        with self.assertRaises(ContractError): keys._result(canonical_bytes(reopened), 'a' * 64, {'reopened'})
        with self.assertRaises(ContractError): keys._result(canonical_bytes(expired), 'a' * 64, {'prepared'})

    def test_cancel_origin_and_false_authority_are_required(self):
        value = {'schema': 'claimbranch.key-preparation-result/v1', 'status': 'cancelled',
                 'request_digest': 'a' * 64, 'authorization_verified': False,
                 'product_custody_verified': False, 'stop_source': 'os-authentication'}
        for change in ({'stop_source': 'deadline'}, {'authorization_verified': True},
                       {'registration_digest': 'b' * 64}, {'request_digest': 'b' * 64}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                keys._result(canonical_bytes({**value, **change}), 'a' * 64, {'cancelled'})
        for source in ('os-authentication', 'review-window'):
            result = keys._result(canonical_bytes({**value, 'stop_source': source}), 'a' * 64, {'cancelled'})
            self.assertEqual(source, result['stop_source'])

    def test_schema_export_cannot_mutate_runtime_validation(self):
        exported = keys.key_registration_schema()
        exported['properties']['authority']['const'] = 'accepted'
        self.assertEqual('unaccepted-key-registration', keys.RECORD['properties']['authority']['const'])
