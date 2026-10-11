import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from claimbranch.application import mac_enrollment as enrollment
from claimbranch.core.canonical import ContractError
from claimbranch.application.mac_runtime import _source_bytes, _run
from tests.application import test_mac_review_signing as signing_fixtures
from copy import deepcopy


class EnrollmentContractTests(unittest.TestCase):
    def test_native_absolute_paths_fit_the_binding_contract(self):
        from claimbranch.core.research_schema import normalize
        for field in ('runtime_directory', 'worker_directory', 'key_directory'):
            schema = enrollment.BINDING['properties'][field]
            for value in ('/private/var/synthetic/runtime', '/Users/researcher/한글 프로젝트/keys'):
                self.assertEqual(value, normalize(value, schema))
            for value in ('relative/keys', '/keys\x00/other'):
                with self.assertRaises(ContractError): normalize(value, schema)

    def test_local_identity_is_not_a_project_name_or_import_path(self):
        for value in ('paper', '../other', '/tmp/import.json', 'a' * 63, 'A' * 64):
            with self.subTest(value=value), self.assertRaises(ContractError):
                enrollment.enrollment_status('/unused', 'a' * 64, value)

    def test_missing_registry_cannot_be_replaced_by_caller_pins(self):
        with patch.object(enrollment, 'check_runtime') as checked, patch.object(enrollment, '_run',
                side_effect=ContractError('not enrolled')):
            checked.return_value = {}
            with self.assertRaises(ContractError):
                enrollment.enrollment_status('/unused', 'a' * 64, 'b' * 64)

    def test_status_rejects_a_self_asserted_authorization_result(self):
        from claimbranch.core.canonical import canonical_bytes
        forged = canonical_bytes({'status': 'enrolled', 'authorization_verified': True})
        with patch.object(enrollment, 'check_runtime'), patch.object(enrollment, '_run', return_value=(forged, b'')):
            with tempfile.TemporaryDirectory() as root, self.assertRaises(ContractError):
                enrollment.enrollment_status(root, 'a' * 64, 'b' * 64)


class EnrolledSigningTests(unittest.TestCase):
    def setUp(self):
        case = signing_fixtures.ReviewSigningBindingTests(); case.setUp()
        self.policy, self.review, self.context, self.history = case.policy, case.review, case.context, case.history
        self.entry = {'binding': {'local_id':'f'*64, 'project_id':'paper', 'key_directory':'/registered-keys',
                                  'registration_digest':'d'*64}, 'entry_digest':'e'*64}
        from claimbranch.core.canonical import decode
        self.entry['binding']['project_id'] = decode(self.review.payload)['operation']['project_id']

    def sign(self):
        return enrollment.sign_enrolled_operation_review('/runtime', 'a'*64, 'f'*64, self.policy, self.review,
                                                         current_context=lambda: deepcopy(self.context))

    def test_registered_key_and_full_review_are_reused_without_changing_history(self):
        before = self.history.manifest()
        with patch.object(enrollment, 'enrollment_status', return_value=self.entry), \
             patch('claimbranch.application.mac_review_signing._sign_checked', return_value={'status':'signed-unaccepted-review'}) as native:
            self.sign()
        self.assertEqual('/registered-keys', native.call_args.args[2])
        self.assertEqual('d'*64, native.call_args.args[3])
        self.assertEqual(self.review.payload, native.call_args.args[4].payload)
        self.assertEqual(self.entry, native.call_args.kwargs['enrollment'])
        self.assertEqual(before, self.history.manifest())

    def test_foreign_project_and_changed_registration_cannot_report_success(self):
        foreign = deepcopy(self.entry); foreign['binding']['project_id'] = 'foreign'
        with patch.object(enrollment, 'enrollment_status', return_value=foreign), \
             patch('claimbranch.application.mac_review_signing._sign_checked') as native, self.assertRaises(ContractError):
            self.sign()
        native.assert_not_called()
        changed = {**self.entry, 'entry_digest':'0'*64}
        with patch.object(enrollment, 'enrollment_status', side_effect=[self.entry, changed]), \
             patch('claimbranch.application.mac_review_signing._sign_checked', return_value={'status':'signed-unaccepted-review'}), \
             self.assertRaises(ContractError):
            self.sign()

    def test_changed_science_blocks_success_but_preserves_native_cancel(self):
        for status in ('signed-unaccepted-review', 'cancelled'):
            original = deepcopy(self.context)
            def native(*args, **kwargs):
                self.context['now'] += 500
                return {'status':status, 'authorization_verified':False}
            with patch.object(enrollment, 'enrollment_status', return_value=self.entry), \
                 patch('claimbranch.application.mac_review_signing._sign_checked', side_effect=native):
                if status == 'cancelled':
                    self.assertEqual('cancelled', self.sign()['status'])
                else:
                    with self.assertRaises(ContractError): self.sign()
            self.context = original


@unittest.skipUnless(sys.platform == 'darwin', 'native enrollment requires macOS')
class NativeEnrollmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='cb-enrollment-contract-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name).resolve()
        source = _source_bytes().decode()
        # Run actual native validators and file primitives without GUI or any
        # trusted namespace override. Software signatures below test integrity
        # only; they are never inserted into the real registry or called trust.
        source = source[:source.rindex('\ndo {')]
        program = cls.root / 'main.swift'
        program.write_text(source + r'''
// Reproduce a concurrent cleanup at the actual lstat boundary, without adding
// a test switch to the shipped native executable.
func fstatat(_ fd: Int32, _ path: String, _ info: UnsafeMutablePointer<stat>, _ flags: Int32) -> Int32 {
    if CommandLine.arguments.count > 1 && CommandLine.arguments[1] == "inventory-race" && custodyScratch(path) {
        _ = Darwin.unlinkat(fd, path, 0)
        errno = ENOENT
        return -1
    }
    return Darwin.fstatat(fd, path, info, flags)
}
do {
    let command = CommandLine.arguments[1]
    if command == "home" {
        print(try enrollmentRoot())
    } else if command == "runtime-directory" {
        print(try enrollmentRuntimeDirectory())
    } else if command == "worker" {
        print(try localWorker(CommandLine.arguments[2], CommandLine.arguments[3]))
    } else if command == "canonical" {
        FileHandle.standardOutput.write(try encoded(["z": ["_": "한글/\n\t\u{8}", "I": true], "A": [1, NSNull()]]))
    } else if command == "waiting" {
        var descriptors: [Int32] = [0, 0]
        guard pipe(&descriptors) == 0 else { throw DeliveryError.io }
        defer { close(descriptors[0]); close(descriptors[1]) }
        do { try waitReady(descriptors[0], Int16(POLLIN), continuousNow() + 12) }
        catch DeliveryError.timeout { print("deadline") }
    } else if command == "read" {
        do { _ = try localRead(CommandLine.arguments[2]); print("read") }
        catch { print("denied") }
    } else if command == "publish" {
        let dir = try localDirectory(CommandLine.arguments[2]); defer { close(dir) }
        do { try publishEnrollment(dir, Data("synthetic enrollment".utf8)) { CommandLine.arguments[3] == "commit" }; print("published") }
        catch { print("refused") }
    } else if command == "identity" {
        let dir = try localDirectory(CommandLine.arguments[2]); defer { close(dir) }
        print(try localIdentity(dir))
    } else if command == "inventory" || command == "inventory-race" {
        print(try localInventory(CommandLine.arguments[2]).sorted().joined(separator: ","))
    } else if command == "records" {
        let key = P256.Signing.PrivateKey()
        var body = Dictionary(uniqueKeysWithValues: enrollmentFields.map { ($0, "placeholder") })
        body["schema"] = "claimbranch.local-enrollment-body/v1"
        body["local_id"] = String(repeating: "a", count: 64)
        body["public_key_x963"] = key.publicKey.x963Representation.base64EncodedString()
        let signature = try key.signature(for: enrollmentPurpose + encoded(body))
        let record: [String: Any] = ["schema": "claimbranch.local-enrollment/v1", "body": body,
                                   "signature_der": signature.derRepresentation.base64EncodedString()]
        let raw = try encoded(record)
        let parsed = try enrollmentRecord(raw); precondition(parsed == body)
        var changed = body; changed["project_id"] = "substituted"
        var bad = record; bad["body"] = changed
        var rejected = false
        do { _ = try enrollmentRecord(encoded(bad)) } catch { rejected = true }
        precondition(rejected)
        rejected = false; bad = record; bad["authorization_verified"] = true
        do { _ = try enrollmentRecord(encoded(bad)) } catch { rejected = true }
        precondition(rejected)
        rejected = false
        do { _ = try enrollmentRecord(raw, revoked: true) } catch { rejected = true }
        precondition(rejected)
        let revoked = try key.signature(for: revocationPurpose + encoded(body))
        let revocation = try encoded(["schema": "claimbranch.local-enrollment-revocation/v1", "body": body,
                                     "signature_der": revoked.derRepresentation.base64EncodedString()])
        let checked = try enrollmentRecord(revocation, revoked: true); precondition(checked == body)
        print("integrity only; tampering and cross-purpose signature refused")
    } else { throw DeliveryError.invalid }
} catch { exit(2) }
''')
        cls.binary = cls.root / 'validator'
        _run(['/usr/bin/xcrun', 'swiftc', '-D', 'CLAIMBRANCH_BROKER', '-module-cache-path', str(cls.root/'cache'),
              str(program), '-o', str(cls.binary)], cwd=cls.root, timeout=90)

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='case-', dir=self.root))
        self.addCleanup(__import__('shutil').rmtree, self.case)

    def run_native(self, *args):
        result = subprocess.run([str(self.binary), *map(str, args)], cwd=self.case,
                                input=b'', capture_output=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.decode().strip()

    def test_fixed_namespace_uses_os_user_record_not_working_directory(self):
        import pwd
        expected = pwd.getpwuid(os.getuid()).pw_dir + '/Library/Application Support/ClaimBranch/enrollments-v1'
        self.assertEqual(expected, self.run_native('home'))
        self.assertEqual([], list(self.case.iterdir()))

    def test_record_signature_is_integrity_only_and_domain_separated(self):
        self.assertEqual('integrity only; tampering and cross-purpose signature refused', self.run_native('records'))

    def test_native_executable_parent_preserves_posix_canonical_path(self):
        self.assertEqual(str(self.binary.parent.resolve()), self.run_native('runtime-directory'))

    def test_native_json_matches_portable_nested_key_and_escape_contract(self):
        from claimbranch.core.canonical import canonical_bytes
        expected = canonical_bytes({'z': {'_': '한글/\n\t\b', 'I': True}, 'A': [1, None]}).decode()
        self.assertEqual(expected, self.run_native('canonical'))

    def test_poll_interval_does_not_shorten_the_review_deadline(self):
        import time
        start = time.monotonic()
        result = subprocess.run([str(self.binary), 'waiting'], capture_output=True, timeout=18)
        self.assertEqual(0, result.returncode)
        self.assertEqual(b'deadline\n', result.stdout)
        elapsed = time.monotonic()-start
        self.assertGreaterEqual(elapsed, 11.5)
        self.assertLess(elapsed, 15, 'the polling loop must retain its absolute deadline')

    def test_source_built_worker_passes_independent_native_validation(self):
        from claimbranch.application.mac_worker import build_worker, check_worker
        worker = self.case/'worker'; worker.mkdir(mode=0o700)
        pin = build_worker(worker)
        expected = check_worker(worker, pin)['code_hash']
        self.assertEqual(expected, self.run_native('worker', worker, pin))
        extra = worker/'Worker.app/Contents/extra'; extra.write_bytes(b'unsealed'); extra.chmod(0o600)
        result = subprocess.run([str(self.binary), 'worker', str(worker), pin], capture_output=True, timeout=10)
        self.assertEqual(2, result.returncode, 'native verification must reject an unsealed extra file')

    def test_unsafe_files_and_linked_parents_are_refused_without_modification(self):
        path = self.case/'entry.json'; path.write_bytes(b'private'); path.chmod(0o600)
        self.assertEqual('read', self.run_native('read', path))
        path.chmod(0o644)
        self.assertEqual('denied', self.run_native('read', path))
        path.chmod(0o600)
        link = self.case/'link'; link.symlink_to(path)
        self.assertEqual('denied', self.run_native('read', link))
        hard = self.case/'hard'; os.link(path, hard)
        self.assertEqual('denied', self.run_native('read', path))
        hard.unlink()
        parent = self.case/'alias'; parent.symlink_to(self.case, target_is_directory=True)
        self.assertEqual('denied', self.run_native('read', parent/'entry.json'))
        self.assertEqual(b'private', path.read_bytes())

    def test_root_replacement_changes_native_identity(self):
        root = self.case/'resource'; root.mkdir(mode=0o700)
        identity = self.run_native('identity', root)
        root.rename(self.case/'retained'); root.mkdir(mode=0o700)
        self.assertNotEqual(identity, self.run_native('identity', root))

    def test_expired_publish_retains_inert_pending_without_entry(self):
        self.assertEqual('refused', self.run_native('publish', self.case, 'expired'))
        self.assertEqual({'pending'}, {p.name for p in self.case.iterdir()})
        self.assertEqual(b'synthetic enrollment', (self.case/'pending').read_bytes())

    def test_publish_is_create_only_and_never_replaces_existing_record(self):
        self.assertEqual('published', self.run_native('publish', self.case, 'commit'))
        self.assertEqual({'entry.json'}, {p.name for p in self.case.iterdir()})
        record = self.case/'entry.json'; identity = record.stat().st_ino
        self.assertEqual(1, record.stat().st_nlink)
        self.assertEqual('refused', self.run_native('publish', self.case, 'commit'))
        self.assertEqual(identity, record.stat().st_ino)
        self.assertEqual(1, record.stat().st_nlink)
        self.assertEqual(b'synthetic enrollment', record.read_bytes())

    def test_interrupted_private_canaries_do_not_hide_registration_files(self):
        record = self.case/'entry.json'; record.write_bytes(b'registration'); record.chmod(0o600)
        scratch = self.case/('.cb-denial-'+'a'*64+'-canary')
        scratch.write_bytes(b'owned denial control'); scratch.chmod(0o600)
        self.assertEqual('entry.json', self.run_native('inventory', self.case))
        foreign = self.case/'.cb-denial-not-a-nonce-canary'; foreign.write_bytes(b'unknown')
        self.assertEqual('.cb-denial-not-a-nonce-canary,entry.json', self.run_native('inventory', self.case))
        scratch.unlink(); scratch.symlink_to(record)
        result = subprocess.run([str(self.binary), 'inventory', str(self.case)], capture_output=True, timeout=10)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b'registration', record.read_bytes())

    def test_concurrent_canary_cleanup_does_not_reject_the_entry(self):
        record = self.case/'entry.json'; record.write_bytes(b'registration'); record.chmod(0o600)
        scratch = self.case/('.cb-denial-'+'f'*64+'-canary')
        scratch.write_bytes(b'owned denial control'); scratch.chmod(0o600)
        self.assertEqual('entry.json', self.run_native('inventory-race', self.case))
        self.assertFalse(scratch.exists())
        self.assertEqual(b'registration', record.read_bytes())
