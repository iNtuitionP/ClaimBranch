from copy import deepcopy
from dataclasses import replace
import struct
import sys
import unittest
from unittest.mock import patch

from claimbranch.application import mac_initialization_signing as signing
from claimbranch.application.mac_review_signing import _packet, _native_result
from claimbranch.application.project_initialization import initialization_operation
from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from tests.application import test_project_initialization as initialization_fixtures
from tests.application.test_project_work import AssociationFixture
from tests.application.test_mac_review_signing import public_record
from tests.application import test_mac_review_signing as native_fixtures


@unittest.skipUnless(sys.platform == 'darwin', 'native initialization signing requires macOS')
class NativeInitializationSigningTests(unittest.TestCase):
    setUpClass = classmethod(native_fixtures.NativeSigningTests.setUpClass.__func__)
    setUp = native_fixtures.NativeSigningTests.setUp

    def packet(self):
        import time
        from claimbranch.application.mac_runtime import check_runtime
        fixture = InitializationSigningTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        now = int(time.time())
        review = fixture.initialization.prepare_review(session_nonce='session', sealed_at=now, expires_at=now+300)
        roles = check_runtime(self.runtime, self.pin)['roles']
        record = public_record(self._paper_review(), roles)
        record['body']['request']['project_id'] = 'project'
        return _packet(record, 'd'*64, review, fixture.enrollment), roles

    def _paper_review(self):
        from tests.application.test_mac_review_signing import SigningPacketTests
        case = SigningPacketTests(); case.setUp(); return case.review

    # Reuse actual compiled peer/missing-key check. No software test in this
    # class may assume an interpretation effect in the initialization body.
    def test_unenrolled_initialization_is_refused_by_both_compiled_roles(self):
        import subprocess
        packet, roles = self.packet()
        count = struct.unpack('>I', packet[:4])[0]
        header = decode(packet[4:4+count]); header.pop('local_id')
        header['schema'] = 'claimbranch.review-signing-request/v1'
        record = public_record(self._paper_review(), roles)
        plain_control = _packet(record, 'd'*64, self._paper_review())
        control_count = struct.unpack('>I', plain_control[:4])[0]
        self.assertEqual(set(decode(plain_control[4:4+control_count])), set(header))
        raw = canonical_bytes(header)
        packet = struct.pack('>I', len(raw)) + raw + packet[4+count:]
        for role, mode in [('broker','sign-review'), ('gateway','receive-signed-review')]:
            other = 'gateway' if role=='broker' else 'broker'
            result = subprocess.run([str(self.runtime/role),mode,str(self.root/'s'),roles[other]['code_hash']],
                                    input=packet,cwd=self.root,capture_output=True,timeout=10)
            self.assertEqual(2,result.returncode); self.assertEqual(b'',result.stdout)
            self.assertFalse((self.root/'s').exists())

    def test_native_initial_signature_and_empty_contract(self):
        import json
        from claimbranch.application.mac_runtime import SOURCE, _run
        from tests.application.test_mac_initial_target import enrollment_read_helpers
        packet, roles = self.packet()
        count = struct.unpack('>I', packet[:4])[0]
        local_id = decode(packet[4:4+count])['local_id']
        namespace = self.root/'initial-target'; namespace.mkdir(mode=0o700)
        entry_path = namespace/local_id; entry_path.mkdir(mode=0o700)
        protected = entry_path/'protected'; protected.mkdir(mode=0o700)
        binding = protected/'binding'; binding.write_bytes(local_id.encode());binding.chmod(0o600)
        source = SOURCE.read_text()
        helpers = source[source.index('func hashHex('):source.index('let signingLimit =')]
        contract = source[source.index('let signingLimit ='):source.index('func signingResult()')]
        enrollment = SOURCE.with_name('Enrollment.swift').read_text()
        enrollment_type = enrollment[enrollment.index('struct NativeEnrollment {'):enrollment.index('func enrollmentRecord(')]
        program = self.root/'initial-signature.swift'
        program.write_text('import Foundation\nimport Security\nimport CryptoKit\nimport Darwin\nlet role="broker"\n' +
            'enum DeliveryError: Error { case invalid, io, timeout }\nfunc inspect() -> [String: Any]? { ["code_hash":"'+roles['broker']['code_hash']+'"] }\n'+
            helpers+enrollment_type+enrollment_read_helpers()+
            'func enrollmentRoot() throws -> String { '+json.dumps(str(namespace))+' }\n'+
            'func loadEnrollment(_ id: String, forRevocation: Bool = false) throws -> NativeEnrollment { throw DeliveryError.invalid }\n'+contract+SOURCE.with_name('InitialSource.swift').read_text()+r'''
let raw = try FileHandle.standardInput.readToEnd()!
let count = Int(raw.prefix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) })
let head = try JSONSerialization.jsonObject(with: Data(raw[4..<(4+count)])) as! [String: Any]
let keyRequest = head["key_request"] as! [String: String]
var body = ["local_id":head["local_id"] as! String, "registration_digest":head["registration_digest"] as! String,
            "public_key_x963":head["public_key_x963"] as! String]
let target = try localDirectory(try enrollmentRoot() + "/" + body["local_id"]! + "/protected")
body["protected_identity"] = try localIdentity(target); close(target)
let entry = NativeEnrollment(body: body, bytes: Data(), keyRequest: keyRequest)
// This is a parser/software-signature fixture, not native namespace enrollment.
let request = try ReviewSigningRequest(raw, enrollment: entry)
try request.fresh()
try request.checkInitialSource()
let existing = try enrollmentRoot() + "/" + entry.id + "/protected/genesis.enc"
precondition(FileManager.default.createFile(atPath:existing,contents:Data("preserve".utf8)))
var targetDenied = false
do { try request.checkInitialSource() } catch { targetDenied = true }
precondition(targetDenied)
let preserved = try Data(contentsOf:URL(fileURLWithPath:existing))
precondition(preserved == Data("preserve".utf8))
try FileManager.default.removeItem(atPath:existing)
try request.checkInitialSource()
precondition(request.operation["action"] as? String == "initialize-project")
let key = try P256.Signing.PrivateKey(rawRepresentation: Data(repeating: 0, count: 31) + Data([1]))
let signature = try key.signature(for: request.message)
let reply = try encoded(["status":"signed-unaccepted-review", "signature_der":signature.derRepresentation.base64EncodedString()])
let verified = try request.verifiedReply(reply)
precondition(verified.0 == "signed-unaccepted-review")
func packetFor(_ value: [String: Any]) throws -> Data {
    var header = request.header
    let review = try encoded(value)
    header["review_digest"] = hashHex(review)
    let operation: [String: Any] = ["action":"initialize-project", "project_id":request.operation["project_id"]!,
        "seed":value["seed"]!, "association":value["association"]!, "initial_head":value["initial_head"]!]
    header["operation_digest"] = try hashHex(encoded(operation))
    let head = try encoded(header)
    var length = UInt32(head.count).bigEndian
    return withUnsafeBytes(of: &length) { Data($0) } + head + review
}
var changed = request.review
var seed = changed["seed"] as! [String: Any]
seed["claim_statement"] = "A different initial thesis."
changed["seed"] = seed; changed["initial_head"] = "root-" + (try hashHex(encoded(seed)))
let replacement = try ReviewSigningRequest(packetFor(changed), enrollment: entry)
var denied = false
do { _ = try replacement.verifiedReply(reply) } catch { denied = true }
precondition(denied)
var invalid = [[String: Any]]()
for (field, value): (String, Any) in [("operation_count", 1), ("operation_count", false), ("evidence_watermark", 1), ("initial_head", "wrong"), ("commands", []), ("authorization_verified", true)] {
    changed = request.review; changed[field] = value; invalid.append(changed)
}
changed = request.review; seed = changed["seed"] as! [String: Any]
seed["claim_id"] = seed["anchor_id"]; changed["seed"] = seed
changed["initial_head"] = "root-" + (try hashHex(encoded(seed))); invalid.append(changed)
changed = request.review; var association = changed["association"] as! [String: Any]
var source = association["source"] as! [String: Any]; source["anchor_id"] = "other"
association["source"] = source; changed["association"] = association; invalid.append(changed)
for review in invalid {
    denied = false
    do { _ = try ReviewSigningRequest(packetFor(review), enrollment: entry) } catch { denied = true }
    precondition(denied)
}
let observation = request.observation(verified)
precondition(nativeFalse(observation["authorization_verified"]))
precondition(initialDisplayedPath("2f610a6201") == "\"/a\\nb\\u0001\"")
precondition(initialDisplayedPath("2f615c6e62") == "\"/a\\\\nb\"")
precondition(initialDisplayedPath("2f615c6e62") != initialDisplayedPath("2f610a62"))
precondition(initialQuoted("title\n원고: /fake") == "\"title\\n원고: /fake\"")
precondition(initialDisplayedPath("2fff") == "원래 경로 바이트 (hex): 2fff")
precondition(initialDisplayedPath("2fff") != initialDisplayedPath("ec9b90eb9e9820eab2bdeba19c20ebb094ec9db4ed8ab82028686578293a2032666666"))
for value in ["", "2", "+1", "-1", "2F", "zz"] {
    precondition(!initialPath(value))
    precondition(initialDisplayedPath(value) == "unavailable")
}
var plain = request.header; plain.removeValue(forKey:"local_id")
plain["schema"] = "claimbranch.review-signing-request/v1"
let plainHead = try encoded(plain); var plainSize = UInt32(plainHead.count).bigEndian
let plainPacket = withUnsafeBytes(of:&plainSize) { Data($0) } + plainHead + (try encoded(request.review))
denied = false
do { _ = try ReviewSigningRequest(plainPacket) } catch { denied = true }
precondition(denied)
print("initial signature verified; changed thesis, nonempty target and forged initialization denied")
''')
        output, errors = _run(['/usr/bin/xcrun','swift','-module-cache-path',str(self.root/'cache'),str(program)],
                              cwd=self.root,input_bytes=packet,timeout=90)
        self.assertEqual(b'',errors)
        self.assertEqual(b'initial signature verified; changed thesis, nonempty target and forged initialization denied\n',output)

    def test_absent_local_binding_is_refused_by_both_compiled_roles(self):
        import subprocess
        packet, roles = self.packet()
        count = struct.unpack('>I', packet[:4])[0]
        head, original = decode(packet[4:4+count]), decode(packet[4+count:])
        for update in ({}, {'operation_count':1}, {'initial_head':'root-wrong'}, {'accepted':True}, {'evidence_watermark':False}):
            value = {**original, **update}; raw = canonical_bytes(value)
            header = canonical_bytes({**head, 'review_digest':digest(value)})
            bad = struct.pack('>I', len(header)) + header + raw
            for role, mode in [('broker','sign-enrolled-review'),('gateway','receive-enrolled-review')]:
                result = subprocess.run([str(self.runtime/role),mode,str(self.root/'s'),head['local_id']],
                    input=bad,cwd=self.root,capture_output=True,timeout=10)
                self.assertEqual(2,result.returncode,result.stdout)
                self.assertEqual(b'',result.stdout)
                self.assertFalse((self.root/'s').exists())


class InitializationSigningTests(AssociationFixture, unittest.TestCase):
    owner = initialization_fixtures.ProjectInitializationTests.owner

    def setUp(self):
        super().setUp()
        self.initialization = self.owner()
        self.review = self.initialization.prepare_review(session_nonce='session', sealed_at=100, expires_at=400)
        self.context = {'session_nonce':'session', 'now':100}
        self.enrollment = {'binding': {'project_id':'project', 'key_directory':'/synthetic-keys',
                                      'registration_digest':'d' * 64, 'local_id':'e' * 64}}

    def send(self, side_effect=None, status='signed-unaccepted-review'):
        result = {'status':status, 'authorization_verified':False, 'protected_acceptance_available':False}
        with patch.object(signing, 'enrollment_status', return_value=self.enrollment), \
             patch.object(signing, '_sign_checked', side_effect=side_effect, return_value=result) as native:
            returned = signing.sign_enrolled_initialization_review('/runtime', 'a'*64, 'e'*64,
                self.initialization, self.review, current_context=lambda:deepcopy(self.context))
        return returned, native

    def test_owned_initial_fields_reach_enrolled_signer_without_write(self):
        result, native = self.send()
        self.assertIs(self.review, native.call_args.args[4])
        self.assertEqual(self.enrollment, native.call_args.kwargs['enrollment'])
        self.assertFalse(result['authorization_verified'])
        self.assertEqual([], list(self.workspace.iterdir()))
        self.assertEqual(self.source, self.manuscript.read_bytes())

    def test_changed_source_or_session_after_signing_refuses_success(self):
        for kind in ('source', 'session', 'expiry'):
            self.initialization = self.owner()
            self.review = self.initialization.prepare_review(session_nonce='session', sealed_at=100, expires_at=400)
            reached = []
            def changed(*args, **kwargs):
                reached.append(True)
                if kind == 'source': self.manuscript.write_bytes(self.source + b'% changed\n')
                else: self.context.update({'session_nonce':'other'} if kind=='session' else {'now':400})
                return {'status':'signed-unaccepted-review'}
            with self.subTest(kind=kind), self.assertRaises(ContractError): self.send(changed)
            self.assertEqual([True], reached)
            self.manuscript.write_bytes(self.source)
            self.context = {'session_nonce':'session', 'now':100}

    def test_imported_review_wrong_project_and_bad_context_do_not_sign(self):
        original = self.review
        self.review = replace(original)
        def unexpected(*args, **kwargs): self.fail('unowned or foreign initialization reached signer')
        with self.assertRaises(ContractError): self.send(unexpected)
        self.review = original
        self.enrollment['binding']['project_id'] = 'other'
        with self.assertRaises(ContractError): self.send(unexpected)

    def test_bad_context_and_changed_enrollment_refuse(self):
        self.context['accepted'] = True
        with self.assertRaises(ContractError): self.send(lambda *a, **k:self.fail('bad context reached signer'))
        self.context.pop('accepted')
        with patch.object(signing, 'enrollment_status', side_effect=[self.enrollment, {'binding':{}}]), \
             patch.object(signing, '_sign_checked', return_value={'status':'signed-unaccepted-review'}), \
             self.assertRaises(ContractError):
            signing.sign_enrolled_initialization_review('/runtime','a'*64,'e'*64,self.initialization,self.review,
                current_context=lambda:deepcopy(self.context))

    def test_enrollment_io_errors_are_bounded_before_and_after_signing(self):
        for responses in ([OSError('private path')], [self.enrollment, OSError('private path')]):
            with patch.object(signing, 'enrollment_status', side_effect=responses), \
                 patch.object(signing, '_sign_checked', return_value={'status':'signed-unaccepted-review'}), \
                 self.assertRaisesRegex(ContractError, 'I/O') as failure:
                signing.sign_enrolled_initialization_review('/runtime','a'*64,'e'*64,self.initialization,self.review,
                    current_context=lambda:deepcopy(self.context))
            self.assertNotIn('private path', str(failure.exception))

    def test_source_io_error_and_missing_manuscript_never_report_success(self):
        original = self.initialization.candidate(self.review, **self.context)
        for responses in ([OSError('private source')], [original, OSError('private source')]):
            with patch.object(self.initialization, 'candidate', side_effect=responses), \
                 self.assertRaisesRegex(ContractError, 'I/O') as failure:
                self.send()
            self.assertNotIn('private source', str(failure.exception))
        def missing(*args, **kwargs):
            self.manuscript.unlink()
            return {'status':'signed-unaccepted-review'}
        with self.assertRaises(ContractError) as failure: self.send(missing)
        self.assertNotIn(str(self.paper), str(failure.exception))

    def test_cancellation_survives_expiry_without_restored_authority(self):
        def cancelled(*args, **kwargs):
            self.context['now'] = 400
            return {'status':'cancelled', 'stop_source':'os-authentication', 'authorization_verified':False}
        result, _ = self.send(cancelled)
        self.assertEqual('cancelled', result['status'])
        self.assertFalse(result['authorization_verified'])

    def test_packet_contains_exact_review_and_derived_empty_operation(self):
        # The device fixture normally reads a paper operation's project; use the
        # existing known public point, then set this initial project's identity.
        from tests.application.test_mac_review_signing import SigningPacketTests
        fixture = SigningPacketTests(); fixture.setUp()
        record = public_record(fixture.review)
        record['body']['request']['project_id'] = 'project'
        packet = _packet(record, 'd'*64, self.review, self.enrollment)
        count = struct.unpack('>I', packet[:4])[0]
        head = decode(packet[4:4+count])
        self.assertEqual(self.review.payload, packet[4+count:])
        self.assertEqual(digest(initialization_operation(self.review)), head['operation_digest'])
        with self.assertRaisesRegex(ContractError,'enrollment'):
            _packet(record, 'd'*64, self.review)

    def test_forged_nonempty_or_wrong_root_review_refuses_before_key_fields(self):
        for change in ({'initial_head':'root-wrong'}, {'operation_count':1}, {'evidence_watermark':1},
                       {'commands':[]}, {'authorization_verified':True}):
            value = {**decode(self.review.payload), **change}
            forged = replace(self.review, payload=canonical_bytes(value), digest=digest(value))
            with self.subTest(change=change), self.assertRaises(ContractError): _packet({}, 'd'*64, forged)
