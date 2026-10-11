from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.mac_runtime import build_runtime, check_runtime, _run, _directory, _create, SOURCE
from claimbranch.core.canonical import ContractError, canonical_bytes, decode


@unittest.skipUnless(sys.platform == 'darwin', 'native runtime requires macOS')
class NativeRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='claimbranch-runtime-test-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name).resolve() / 'built'
        cls.base.mkdir(mode=0o700)
        cls.pin = build_runtime(cls.base)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='claimbranch-runtime-case-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.runtime = self.root / 'runtime'
        shutil.copytree(self.base, self.runtime)

    def test_build_and_reopen_has_distinct_roles_without_authority(self):
        result = check_runtime(self.runtime, self.pin)
        self.assertEqual({'broker', 'gateway'}, set(result['roles']))
        self.assertNotEqual(result['roles']['broker']['code_hash'], result['roles']['gateway']['code_hash'])
        self.assertTrue(all(role['running_hardened'] for role in result['roles'].values()))
        self.assertFalse(result['authorization_verified'])
        self.assertFalse(result['protected_acceptance_available'])
        self.assertEqual({'broker', 'gateway', 'runtime.json'}, {p.name for p in self.runtime.iterdir()})

    def test_enrolled_modes_refuse_missing_native_registration_and_cwd_import(self):
        import secrets
        local_id = secrets.token_hex(32)
        imported = self.root / local_id; imported.mkdir(mode=0o700)
        (imported/'entry.json').write_text('{"schema":"claimbranch.local-enrollment/v1"}')
        before = (imported/'entry.json').read_bytes()
        for role, mode in [('broker','sign-enrolled-review'), ('gateway','receive-enrolled-review')]:
            result = subprocess.run([str(self.runtime/role), mode, str(self.root/'s'), local_id],
                                    cwd=self.root, input=b'untrusted imported review', capture_output=True, timeout=10)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b'', result.stdout)
            self.assertFalse((self.root/'s').exists())
        for role in ('broker','gateway'):
            result = subprocess.run([str(self.runtime/role), 'enrollment-status', local_id],
                                    cwd=self.root, input=b'', capture_output=True, timeout=10)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b'', result.stdout)
        self.assertEqual(before, (imported/'entry.json').read_bytes())

    def test_untrusted_enrollment_input_cannot_open_foreground_or_create_root(self):
        packets = [b'{}', b'not-json', b'{"schema":"claimbranch.enrollment-request/v1","authorization_verified":true}']
        for raw in packets:
            result = subprocess.run([str(self.runtime/'broker'), 'enroll-project'], cwd=self.root,
                                    input=raw, capture_output=True, timeout=10)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b'', result.stdout)

    def test_fresh_process_reopens_with_retained_pin_and_no_native_prompt(self):
        script = '''import json, sys
from claimbranch.application.mac_runtime import check_runtime
print(json.dumps(check_runtime(sys.argv[1], sys.argv[2])))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.runtime), self.pin],
                                input=b'', capture_output=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(json.loads(result.stdout)['protected_acceptance_available'])

    def test_wrong_pin_and_modified_executable_fail_before_native_launch(self):
        with patch('claimbranch.application.mac_runtime._run') as execute:
            with self.assertRaises(ContractError):
                check_runtime(self.runtime, '0' * 64)
            execute.assert_not_called()
        binary = self.runtime / 'broker'
        binary.write_bytes(binary.read_bytes() + b'changed')
        with patch('claimbranch.application.mac_runtime._run') as execute:
            with self.assertRaises(ContractError):
                check_runtime(self.runtime, self.pin)
            execute.assert_not_called()

    def test_manifest_cannot_be_its_own_trust_root(self):
        manifest = self.runtime / 'runtime.json'
        value = decode(manifest.read_bytes())
        value['source_sha256'] = '0' * 64
        manifest.write_bytes(canonical_bytes(value))
        with patch('claimbranch.application.mac_runtime._run') as execute:
            with self.assertRaises(ContractError):
                check_runtime(self.runtime, self.pin)
            execute.assert_not_called()

    def test_unknown_manifest_fields_or_authority_fail_even_with_matching_pin(self):
        manifest = self.runtime / 'runtime.json'
        original = decode(manifest.read_bytes())
        for update in ({'schema': 'claimbranch.mac-runtime-build/v2'}, {'authorization_verified': True},
                       {'accepted': True}):
            raw = canonical_bytes({**original, **update})
            manifest.write_bytes(raw)
            with self.subTest(update=update), self.assertRaises(ContractError):
                check_runtime(self.runtime, hashlib.sha256(raw).hexdigest())

    def test_role_swap_is_rejected_by_signature_not_only_manifest_hashes(self):
        value = decode((self.runtime / 'runtime.json').read_bytes())
        broker = (self.runtime / 'broker').read_bytes()
        (self.runtime / 'gateway').write_bytes(broker)
        value['gateway'] = value['broker']
        raw = canonical_bytes(value)
        (self.runtime / 'runtime.json').write_bytes(raw)
        with self.assertRaises(ContractError):
            check_runtime(self.runtime, hashlib.sha256(raw).hexdigest())

    def test_signature_removed_is_not_accepted_as_matching_file(self):
        binary = self.runtime / 'gateway'
        subprocess.run(['/usr/bin/codesign', '--remove-signature', str(binary)], check=True, capture_output=True)
        manifest = self.runtime / 'runtime.json'
        value = decode(manifest.read_bytes())
        value['gateway']['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
        raw = canonical_bytes(value)
        manifest.write_bytes(raw)
        with self.assertRaises(ContractError):
            check_runtime(self.runtime, hashlib.sha256(raw).hexdigest())

    def test_link_hardlink_permissions_and_extra_files_are_refused(self):
        broker = self.runtime / 'broker'
        backup = broker.read_bytes()
        broker.unlink()
        broker.symlink_to(self.base / 'broker')
        with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)
        broker.unlink()
        os.link(self.base / 'broker', broker)
        with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)
        broker.unlink()
        broker.write_bytes(backup); broker.chmod(0o755)
        with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)
        broker.chmod(0o700)
        (self.runtime / 'unexpected').write_text('preserve me')
        with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)
        self.assertEqual('preserve me', (self.runtime / 'unexpected').read_text())

    def test_existing_build_and_in_git_directory_are_not_modified(self):
        before = {p.name: p.read_bytes() for p in self.runtime.iterdir()}
        with self.assertRaises(ContractError): build_runtime(self.runtime)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})
        (self.root / '.git').mkdir()
        with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})

    def test_failed_build_is_incomplete_and_not_automatically_overwritten(self):
        target = self.root / 'failed'
        target.mkdir(mode=0o700)
        with patch('claimbranch.application.mac_runtime._run', side_effect=ContractError('tool failed')):
            with self.assertRaises(ContractError): build_runtime(target)
        self.assertEqual(b'', (target / 'runtime.json').read_bytes())
        with self.assertRaises(ContractError): build_runtime(target)
        with self.assertRaises(ContractError): check_runtime(target, self.pin)

    def test_native_helper_has_no_generic_execution_or_approval_mode(self):
        result = subprocess.run([str(self.runtime / 'broker'), 'approve'], capture_output=True, timeout=5)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b'', result.stdout)
        self.assertEqual({'broker', 'gateway', 'runtime.json'}, {p.name for p in self.runtime.iterdir()})

    def test_native_key_modes_reject_bad_requests_without_prompt_or_write(self):
        from claimbranch.application.mac_key_registration import preview_key_preparation
        destination = self.root / 'keys'
        destination.mkdir(mode=0o700)
        preview = preview_key_preparation(self.runtime, self.pin, destination, project_id='synthetic')
        original = decode(preview.payload)
        for change in ({'broker_code_hash': '0' * 40}, {'directory_identity': '0:0'},
                       {'project_id': '../bad'}, {'authority': 'accepted'}, {'nonce': 'x'}):
            with self.subTest(change=change):
                result = subprocess.run([str(self.runtime / 'broker'), 'prepare-key'],
                    input=canonical_bytes({**original, **change}), cwd=destination, capture_output=True, timeout=10)
                self.assertEqual(2, result.returncode, result.stdout)
                self.assertEqual([], list(destination.iterdir()))
        for mode in ('prepare-key', 'reopen-key'):
            result = subprocess.run([str(self.runtime / 'gateway'), mode], input=preview.payload,
                cwd=destination, capture_output=True, timeout=10)
            self.assertEqual(2, result.returncode)
            self.assertEqual([], list(destination.iterdir()))

    def test_native_key_existing_reservation_and_corrupt_record_are_preserved(self):
        from claimbranch.application.mac_key_registration import preview_key_preparation, NAME
        destination = self.root / 'keys'
        destination.mkdir(mode=0o700)
        preview = preview_key_preparation(self.runtime, self.pin, destination, project_id='synthetic')
        record = destination / NAME
        record.write_bytes(b'original-incomplete-reservation'); record.chmod(0o600)
        pin = hashlib.sha256(record.read_bytes()).hexdigest()
        for args in (['prepare-key'], ['reopen-key', pin]):
            result = subprocess.run([str(self.runtime / 'broker'), *args], input=preview.payload,
                cwd=destination, capture_output=True, timeout=10)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b'', result.stdout)
            self.assertEqual(b'original-incomplete-reservation', record.read_bytes())

    def test_native_key_lifecycle_denies_late_duplicate_and_unreviewed_completion(self):
        source = SOURCE.read_text()
        gate = source[source.index('struct KeyPreparationGate {'):source.index('final class KeyPreparationController:')]
        program = self.root / 'gate.swift'
        program.write_text(gate + '''
var a = KeyPreparationGate(deadline: 10)
precondition(!a.mayPersist(0) && !a.authenticated(true, 0))
precondition(a.begin(1) && !a.begin(2))
precondition(!a.authenticated(false, 3) && !a.mayPersist(4))
precondition(a.authenticated(true, 5) && !a.authenticated(true, 6))
precondition(a.mayPersist(9) && !a.mayPersist(10))
precondition(a.stop() && !a.stop() && !a.mayPersist(8))
var b = KeyPreparationGate(deadline: 10)
precondition(b.begin(1) && b.stop() && !b.authenticated(true, 2))
var c = KeyPreparationGate(deadline: 10)
precondition(!c.begin(10) && !c.mayPersist(9))
var d = KeyPreparationGate(deadline: 10)
precondition(d.begin(1) && !d.authenticated(true, 10) && !d.mayPersist(10))
precondition(resolvedKeyStop("cancelled", "review-window", true).1 == "os-authentication")
precondition(resolvedKeyStop("cancelled", "review-window", false).1 == "review-window")
precondition(resolvedKeyStop("expired", "deadline", true).0 == "expired")
precondition(resolvedKeyStop("expired", "deadline", true).1 == "deadline")
print("lifecycle cases passed")
''')
        output, errors = _run(['/usr/bin/xcrun', 'swift', '-module-cache-path', str(self.root / 'cache'),
                              str(program)], cwd=self.root, timeout=90)
        self.assertEqual(b'lifecycle cases passed\n', output)
        self.assertEqual(b'', errors)

    def test_native_reopen_rejects_self_signed_software_key_as_device_custody(self):
        import base64
        from claimbranch.application.mac_key_registration import preview_key_preparation, reopen_key, NAME
        destination = self.root / 'keys'
        destination.mkdir(mode=0o700)
        preview = preview_key_preparation(self.runtime, self.pin, destination, project_id='synthetic')
        # Test fixture only: a valid signature cannot turn an imported software
        # key or caller-chosen opaque bytes into a Secure Enclave registration.
        private = self.root / 'fixture.pem'
        openssl = os.environ.get('CLAIMBRANCH_TEST_OPENSSL', '/usr/bin/openssl')
        subprocess.run([openssl, 'ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', str(private)],
                       capture_output=True, check=True, timeout=10)
        public = subprocess.run([openssl, 'ec', '-in', str(private), '-pubout', '-outform', 'DER'],
                                capture_output=True, check=True, timeout=10).stdout[-65:]
        body = {'schema': 'claimbranch.key-registration-body/v1', 'request': decode(preview.payload),
                'public_key_x963': base64.b64encode(public).decode(),
                'representation_digest': hashlib.sha256(b'fake-device-representation').hexdigest()}
        signature = subprocess.run([openssl, 'dgst', '-sha256', '-sign', str(private)],
            input=b'ClaimBranch synthetic key registration v1\n' + canonical_bytes(body),
            capture_output=True, check=True, timeout=10).stdout
        value = {'schema': 'claimbranch.key-registration/v1', 'body': body,
                 'representation': base64.b64encode(b'fake-device-representation').decode(),
                 'signature_der': base64.b64encode(signature).decode(), 'authority': 'unaccepted-key-registration'}
        raw = canonical_bytes(value)
        record = destination / NAME
        record.write_bytes(raw); record.chmod(0o600)
        pin = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ContractError):
            reopen_key(self.runtime, self.pin, destination, pin, project_id='synthetic')
        self.assertEqual(raw, record.read_bytes())

    def test_native_registration_signature_and_python_canonical_bytes_agree(self):
        from claimbranch.application import mac_key_registration as keys
        destination = self.root / 'keys'
        destination.mkdir(mode=0o700)
        preview = keys.preview_key_preparation(self.runtime, self.pin, destination, project_id='synthetic.A_-:1')
        source = SOURCE.read_text()
        # Keep this standalone fixture limited to registration serialization;
        # review signing has separate native dependencies and tests.
        helpers = source[source.index('let keyFile ='):source.index('let signingLimit =')]
        validator = source[source.index('func checkedKeyRecord('):source.index('func readKeyRecord(')]
        program = self.root / 'parity.swift'
        program.write_text('import Foundation\nimport CryptoKit\nenum DeliveryError: Error { case invalid }\n' +
                          helpers + validator + '''
let raw = try FileHandle.standardInput.readToEnd()!
let request = try JSONSerialization.jsonObject(with: raw) as! [String: String]
let canonical = try encoded(request)
precondition(canonical == raw)
let key = P256.Signing.PrivateKey() // Software key is ONLY a serialization/signature fixture.
let representation = Data("fixture-not-a-device-key".utf8)
let body: [String: Any] = ["schema": "claimbranch.key-registration-body/v1", "request": request,
    "public_key_x963": key.publicKey.x963Representation.base64EncodedString(),
    "representation_digest": hashHex(representation)]
let signature = try key.signature(for: keyPurpose + encoded(body))
let record: [String: Any] = ["schema": "claimbranch.key-registration/v1", "body": body,
    "representation": representation.base64EncodedString(),
    "signature_der": signature.derRepresentation.base64EncodedString(), "authority": "unaccepted-key-registration"]
let bytes = try encoded(record)
_ = try checkedKeyRecord(bytes, request)
var changed = request
changed["project_id"] = "another-project"
var denied = false
do { _ = try checkedKeyRecord(bytes, changed) } catch { denied = true }
precondition(denied)
FileHandle.standardOutput.write(bytes)
''')
        raw, errors = _run(['/usr/bin/xcrun', 'swift', '-module-cache-path', str(self.root / 'cache'),
                           str(program)], cwd=self.root, timeout=90, input_bytes=preview.payload)
        self.assertEqual(b'', errors)
        record = destination / keys.NAME
        record.write_bytes(raw); record.chmod(0o600)
        with _directory(destination) as (_, fd):
            value = keys._read_registration(fd, hashlib.sha256(raw).hexdigest())
        self.assertEqual(decode(preview.payload), value['body']['request'])
        self.assertEqual(raw, canonical_bytes(value))

    def test_inherited_injection_environment_is_not_forwarded(self):
        with patch.dict(os.environ, {'DYLD_INSERT_LIBRARIES': '/not/a/library', 'PYTHONPATH': '/untrusted',
                                    'DEVELOPER_DIR': '/untrusted', 'CLAIMBRANCH_SECRET': 'not-forwarded'}):
            result = check_runtime(self.runtime, self.pin)
            self.assertFalse(result['authorization_verified'])
        raw, errors = _run([sys.executable, '-I', '-S', '-c',
            'import os; print(os.environ.get("CLAIMBRANCH_SECRET", "absent"))'], cwd=self.root)
        self.assertEqual(b'absent\n', raw)
        self.assertEqual(b'', errors)

    def test_timeout_and_output_limit_fail_with_bounded_diagnostics(self):
        with self.assertRaisesRegex(ContractError, 'timed out'):
            _run([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(10)'], cwd=self.root, timeout=0.1)
        with self.assertRaisesRegex(ContractError, 'exceeds'):
            _run([sys.executable, '-I', '-S', '-c', 'print("x"*100000)'], cwd=self.root, limit=4096)

    def test_source_artifact_build_and_cli_reopen_do_not_need_repository_scripts(self):
        from scripts.build_source import build_source
        import zipfile
        archive = self.root / 'source.zip'
        build_source(archive)
        unpacked = self.root / 'unpacked'
        with zipfile.ZipFile(archive) as package:
            package.extractall(unpacked)
        self.assertFalse((unpacked / 'scripts').exists())
        self.assertTrue((unpacked / 'claimbranch/application/native/RuntimeIdentity.swift').is_file())
        target = self.root / 'artifact-runtime'
        target.mkdir(mode=0o700)
        environment = os.environ.copy()
        environment.pop('PYTHONPATH', None)
        made = subprocess.run([sys.executable, '-B', '-m', 'claimbranch', 'runtime', 'build',
            '--directory', str(target), '--json'], cwd=unpacked, env=environment, capture_output=True, timeout=420)
        self.assertEqual(0, made.returncode, made.stderr)
        value = json.loads(made.stdout)
        self.assertEqual('built', value['status'])
        checked = subprocess.run([sys.executable, '-B', '-m', 'claimbranch', 'runtime', 'check',
            '--directory', str(target), '--expected-build', value['build_pin'], '--json'], cwd=unpacked,
            env=environment, capture_output=True, timeout=20)
        self.assertEqual(0, checked.returncode, checked.stderr)
        self.assertFalse(json.loads(checked.stdout)['authorization_verified'])
        delivered = subprocess.run([sys.executable, '-B', '-c',
            'import sys; from claimbranch.application.mac_review_delivery import _exchange; '
            '_exchange(sys.argv[1], sys.argv[2], b"n" * 32 + b"source artifact review")',
            str(target), value['build_pin']], cwd=unpacked, env=environment, capture_output=True, timeout=30)
        self.assertEqual(0, delivered.returncode, delivered.stderr)
        self.assertEqual(b'', delivered.stdout)

    def test_source_manifest_and_permissions_are_not_modified_on_check(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.runtime.iterdir()}
        directory_time = self.runtime.stat().st_mtime_ns
        check_runtime(self.runtime, self.pin)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.runtime.iterdir()})
        self.assertEqual(directory_time, self.runtime.stat().st_mtime_ns)

    def test_integer_flags_cannot_masquerade_as_boolean_native_result(self):
        actual = _run
        def changed(arguments, **kwargs):
            output, errors = actual(arguments, **kwargs)
            if arguments[-1] == 'check':
                value = decode(output)
                value['authorization_verified'] = 0
                output = canonical_bytes(value)
            return output, errors
        with patch('claimbranch.application.mac_runtime._run', side_effect=changed):
            with self.assertRaises(ContractError): check_runtime(self.runtime, self.pin)


    def test_changed_packaged_source_requires_explicit_rebuild(self):
        source = self.root / 'changed.swift'
        source.write_bytes(SOURCE.read_bytes() + b'\n// source update\n')
        source.with_name('Enrollment.swift').write_bytes(SOURCE.with_name('Enrollment.swift').read_bytes())
        source.with_name('InitialSource.swift').write_bytes(SOURCE.with_name('InitialSource.swift').read_bytes())
        with patch('claimbranch.application.mac_runtime.SOURCE', source), \
                patch('claimbranch.application.mac_runtime._run') as execute:
            with self.assertRaisesRegex(ContractError, 'different packaged source'):
                check_runtime(self.runtime, self.pin)
            execute.assert_not_called()

    def test_unsafe_parent_is_refused_before_launch(self):
        parent = self.root / 'shared'
        parent.mkdir(mode=0o700)
        parent.chmod(0o777)
        destination = parent / 'runtime'
        shutil.copytree(self.base, destination)
        with patch('claimbranch.application.mac_runtime._run') as execute:
            with self.assertRaisesRegex(ContractError, 'parent directories'):
                check_runtime(destination, self.pin)
            execute.assert_not_called()

    def test_created_file_modes_ignore_restrictive_umask(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        old = os.umask(0o377)
        try:
            _create(fd, 'executable', b'own data', 0o700)
            _create(fd, 'manifest', b'own metadata', 0o600)
        finally:
            os.umask(old)
            os.close(fd)
        self.assertEqual(0o700, (self.root / 'executable').stat().st_mode & 0o777)
        self.assertEqual(0o600, (self.root / 'manifest').stat().st_mode & 0o777)

    def test_process_group_is_cleaned_before_reaping(self):
        events = []
        wait, kill = subprocess.Popen.wait, os.killpg
        def waiting(process, *args, **kwargs):
            events.append('wait')
            return wait(process, *args, **kwargs)
        def killing(*args, **kwargs):
            events.append('kill')
            return kill(*args, **kwargs)
        with patch.object(subprocess.Popen, 'wait', waiting), patch('os.killpg', killing):
            _run(['/usr/bin/true'], cwd=self.root)
        self.assertEqual(['kill', 'wait'], events)

    def test_owned_straggler_is_terminated_after_leader_exit(self):
        import time
        sentinel = self.root / 'unexpected-child-write'
        script = """import os, sys, time
if os.fork() == 0:
    os.close(1); os.close(2)
    time.sleep(.3)
    open(sys.argv[1], 'w').write('escaped cleanup')
else:
    os._exit(0)
"""
        _run([sys.executable, '-I', '-S', '-c', script, str(sentinel)], cwd=self.root)
        time.sleep(.5)
        self.assertFalse(sentinel.exists())


class RuntimeCommandTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'darwin', 'native process cleanup requires macOS')
    def test_failed_group_cleanup_still_closes_pipes_and_reaps_owned_child(self):
        processes = []
        original = subprocess.Popen
        def spawned(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        try:
            with patch('subprocess.Popen', side_effect=spawned), \
                    patch('os.killpg', side_effect=PermissionError('injected denial')):
                with self.assertRaisesRegex(ContractError, 'cleanup failed'):
                    _run([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(10)'],
                         cwd=Path.cwd(), input_bytes=b'x', timeout=.05)
            child = processes[0]
            self.assertTrue(child.stdin.closed and child.stdout.closed and child.stderr.closed)
            self.assertIsNotNone(child.poll())
        finally:
            for child in processes:
                if child.poll() is None:
                    child.kill()
                child.wait()
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None: stream.close()

    def test_commands_are_explicit_and_doctor_remains_nonexecuting(self):
        from claimbranch.application.cli import main
        with redirect_stdout(io.StringIO()), patch('claimbranch.application.mac_runtime.build_runtime') as build, \
                patch('subprocess.Popen', side_effect=AssertionError('doctor launched a process')):
            self.assertEqual(3, main(['doctor', '--json']))
            build.assert_not_called()
        output = io.StringIO()
        with redirect_stdout(output), patch('claimbranch.application.mac_runtime.build_runtime', return_value='a'*64):
            self.assertEqual(0, main(['runtime', 'build', '--directory', '/synthetic', '--json']))
        self.assertFalse(json.loads(output.getvalue())['protected_acceptance_available'])

    def test_failed_command_sanitizes_paths_and_preserves_completed_output_failure(self):
        from claimbranch.application.cli import main
        errors = io.StringIO()
        with redirect_stderr(errors), patch('claimbranch.application.mac_runtime.build_runtime',
                side_effect=ContractError('/private/path/secret')):
            self.assertEqual(1, main(['runtime', 'build', '--directory', '/synthetic', '--json']))
        self.assertNotIn('/private/path', errors.getvalue())
        class Broken:
            def write(self, _): raise BrokenPipeError()
            def flush(self): raise BrokenPipeError()
            def close(self): pass
        errors = io.StringIO()
        with redirect_stdout(Broken()), redirect_stderr(errors), \
                patch('claimbranch.application.mac_runtime.build_runtime', return_value='b'*64):
            self.assertEqual(1, main(['runtime', 'build', '--directory', '/synthetic', '--json']))
        self.assertIn('after completion', errors.getvalue())
