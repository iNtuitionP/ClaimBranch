from copy import deepcopy
import hashlib
import struct
import unittest
from unittest.mock import patch
from claimbranch.application import mac_review_signing as signing
from claimbranch.core.canonical import ContractError, decode
from tests.application import test_mac_review_delivery as fixtures


class ReviewSigningBindingTests(unittest.TestCase):
    setUp = fixtures.ReviewDeliveryBindingTests.setUp
    # Reuse the independent existing scientific fixture, not its delivery tests.
    def send(self):
        return signing.sign_operation_review('/runtime', 'a' * 64, '/keys', 'd' * 64,
            self.policy, self.review, current_context=lambda: deepcopy(self.context))

    def test_exact_review_reuses_judgment_and_private_result_only(self):
        before = self.history.manifest()
        with patch.object(signing, '_sign', return_value={'status': 'signed-unaccepted-review'}) as native:
            result = self.send()
        self.assertEqual(self.review.payload, native.call_args.args[4].payload)
        self.assertEqual('signed-unaccepted-review', result['status'])
        self.assertFalse(result['authorization_verified'])
        self.assertFalse(result['protected_acceptance_available'])
        self.assertEqual(before, self.history.manifest())

    def test_context_change_after_native_signature_refuses_success(self):
        for change in ({'manuscript_digest': 'c' * 64}, {'session_nonce': 'changed'}, {'now':1800000300}):
            original = deepcopy(self.context)
            def changed(*args):
                self.context.update(change)
                return {'status':'signed-unaccepted-review'}
            with patch.object(signing, '_sign', side_effect=changed), self.assertRaises(ContractError): self.send()
            self.context = original

    def test_unowned_review_never_launches_signer(self):
        self.policy.merge(['replication'])
        with patch.object(signing, '_sign') as native, self.assertRaises(ContractError): self.send()
        native.assert_not_called()



    def test_bad_context_cannot_enter_native_signing(self):
        for context in (None, [], {**self.context, 'accepted': True}):
            with patch.object(signing, '_sign') as native, self.assertRaises(ContractError):
                signing.sign_operation_review('/runtime','a'*64,'/keys','d'*64,self.policy,self.review,
                                              current_context=lambda: context)
            native.assert_not_called()

    def test_cancel_result_never_acquires_authority_or_changes_history(self):
        before = self.history.manifest()
        with patch.object(signing, '_sign', return_value={'status':'cancelled','stop_source':'os-authentication'}):
            result = self.send()
        self.assertEqual('cancelled', result['status'])
        self.assertFalse(result['authorization_verified'])
        self.assertEqual(before, self.history.manifest())

    def test_cancel_or_expiry_keeps_its_terminal_reason_when_context_expires(self):
        for status, source in [('cancelled','os-authentication'),('expired','deadline')]:
            original = deepcopy(self.context)
            def stopped(*args):
                self.context['now'] = 1800000300
                return {'status':status,'stop_source':source,'signature_verified':False}
            with patch.object(signing, '_sign', side_effect=stopped):
                result = self.send()
            self.assertEqual(status,result['status'])
            self.assertFalse(result['authorization_verified'])
            self.context = original


def public_record(review, roles=None):
    import base64
    point = bytes.fromhex('04' + '6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296' +
                          '4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5')
    return {'body': {'public_key_x963': base64.b64encode(point).decode(), 'request': {
        'schema':'claimbranch.key-preparation/v1', 'project_id':decode(review.payload)['operation']['project_id'],
        'build_pin':'a'*64, 'nonce':'e'*64, 'directory_identity':'1:2',
        'broker_code_hash': roles['broker']['code_hash'] if roles else 'b'*40,
        'gateway_code_hash':roles['gateway']['code_hash'] if roles else 'c'*40}}}


class OriginBoundSigningBindingTests(ReviewSigningBindingTests):
    def setUp(self):
        from tests.application.test_paper_record_transition import PaperRecordTransitionTests
        from tests.application.test_paper_operation import BINDINGS
        case = PaperRecordTransitionTests(); case.setUp()
        self.review = case.seal(ai=True)
        self.history, self.policy = case.history, case.policy
        self.context = deepcopy(BINDINGS)

    def test_selected_origin_change_during_signature_refuses_success(self):
        def changed(*args):
            amendment = decode(self.review.payload)['lineages'][0]['revisions'][-1]['amendment']
            amendment['body']['statement'] += ' Changed interpretation.'
            self.policy.revise_amendment(amendment)
            return {'status':'signed-unaccepted-review'}
        with patch.object(signing, '_sign', side_effect=changed), self.assertRaises(ContractError):
            self.send()

    def test_later_omitted_draft_keeps_fixed_signed_origin_snapshot(self):
        def changed(*args):
            self.policy.revise_amendment({'id':'later-omitted', 'kind':'claim', 'body':{
                'role':'main', 'statement':'New unselected writing.', 'scope':'Not measured.', 'parent_ids':['thesis']}})
            return {'status':'signed-unaccepted-review'}
        with patch.object(signing, '_sign', side_effect=changed):
            result = self.send()
        self.assertFalse(result['authorization_verified'])
        # No record_transition call preceded signing: preparation already kept
        # the registry snapshot. Later writing cannot replace signed sources.
        transition = decode(self.policy.record_transition(self.review, **self.context).payload)
        self.assertEqual(decode(self.review.payload), transition['review'])
        self.assertNotIn('later-omitted', [o['revisions'][-1]['amendment']['id'] for o in transition['origins']])


class SigningPacketTests(unittest.TestCase):
    def setUp(self):
        case = ReviewSigningBindingTests(); case.setUp()
        self.review = case.review
        self.record = public_record(self.review)

    def test_wire_contains_complete_review_and_fresh_nonce_not_key_material(self):
        first = signing._packet(self.record, 'd'*64, self.review)
        second = signing._packet(self.record, 'd'*64, self.review)
        count = struct.unpack('>I', first[:4])[0]
        header = decode(first[4:4+count])
        self.assertEqual(self.review.payload, first[4+count:])
        self.assertEqual(self.review.digest, header['review_digest'])
        self.assertNotEqual(first, second)
        self.assertNotIn(b'representation', first[:4+count])
        self.record['body']['request']['project_id'] = 'other-project'
        with self.assertRaises(ContractError): signing._packet(self.record, 'd'*64, self.review)

    def test_origin_bound_v2_packet_and_enrolled_frame_preserve_complete_review(self):
        from tests.application.test_paper_record_transition import PaperRecordTransitionTests
        case = PaperRecordTransitionTests(); case.setUp()
        review = case.seal(ai=True)
        record = public_record(review)
        for enrollment in (None, {'binding': {'local_id': 'f' * 64}}):
            packet = signing._packet(record, 'd' * 64, review, enrollment)
            count = struct.unpack('>I', packet[:4])[0]
            header = decode(packet[4:4+count])
            self.assertEqual(review.payload, packet[4+count:])
            self.assertEqual(review.digest, header['review_digest'])
            self.assertEqual('claimbranch.paper-operation-review/v2', decode(packet[4+count:])['schema'])
            if enrollment:
                self.assertEqual('f' * 64, header['local_id'])

    def test_invalid_v2_review_is_refused_before_key_fields_are_read(self):
        from dataclasses import replace
        from claimbranch.core.canonical import canonical_bytes, digest
        from tests.application.test_paper_record_transition import PaperRecordTransitionTests
        case = PaperRecordTransitionTests(); case.setUp()
        review = case.seal()
        self.assertEqual('claimbranch.paper-operation-review/v2', decode(review.payload)['schema'])
        invalid = [{**decode(review.payload), **change} for change in
                   ({'origin_registry_digest':'bad'}, {'schema':'claimbranch.paper-operation-review/v3'},
                    {'accepted':True}, {'origin_registry_digest':None},
                    {'schema':'claimbranch.paper-operation-review/v1'}, {'operation_digest':'0' * 64})]
        missing = decode(review.payload); del missing['origin_registry_digest']; invalid.append(missing)
        merge = decode(review.payload); merge['operation']['action'] = 'apply-selected-merge'
        merge['operation_digest'] = digest(merge['operation']); invalid.append(merge)
        for value in invalid:
            broken = replace(review, payload=canonical_bytes(value), digest=digest(value))
            with self.assertRaises(ContractError): signing._packet({}, 'd' * 64, broken)
        with self.assertRaises(ContractError):
            signing._packet({}, 'd' * 64, replace(review, digest='0' * 64))

    def test_result_cannot_expose_receipt_or_claim_authority(self):
        from claimbranch.core.canonical import canonical_bytes
        packet = signing._packet(self.record, 'd'*64, self.review)
        value = {'schema':'claimbranch.native-review-signing/v1','role':'gateway','status':'signed-unaccepted-review',
                 'exchange_digest':hashlib.sha256(packet).hexdigest(), 'review_digest':self.review.digest,
                 'operation_digest':decode(self.review.payload)['operation_digest'], 'peer_verified':True,
                 'signature_verified':True, 'authorization_verified':False,'protected_acceptance_available':False}
        self.assertEqual(value, signing._native_result(canonical_bytes(value),'gateway',packet,self.review))
        for change in ({'signature_der':'secret'}, {'authorization_verified':True}, {'peer_verified':1},
                       {'signature_verified':False}, {'exchange_digest':'0'*64}, {'role':'broker'}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                signing._native_result(canonical_bytes({**value,**change}),'gateway',packet,self.review)
        for status, source in [('cancelled','os-authentication'),('cancelled','review-window'),('expired','deadline')]:
            cancelled = {**value,'status':status,'signature_verified':False,'stop_source':source}
            self.assertEqual(cancelled, signing._native_result(canonical_bytes(cancelled),'gateway',packet,self.review))
            with self.assertRaises(ContractError):
                signing._native_result(canonical_bytes({**cancelled,'signature_der':'receipt'}),'gateway',packet,self.review)


import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from claimbranch.application.mac_runtime import SOURCE, _run, check_runtime
from claimbranch.core.canonical import canonical_bytes
from tests.application import test_mac_runtime as runtime_fixtures


@unittest.skipUnless(sys.platform == 'darwin', 'native review signing requires macOS')
class NativeSigningTests(unittest.TestCase):
    setUpClass = classmethod(runtime_fixtures.NativeRuntimeTests.setUpClass.__func__)
    setUp = runtime_fixtures.NativeRuntimeTests.setUp

    def packet(self):
        case = ReviewSigningBindingTests(); case.setUp()
        case.context['now'] = int(time.time())
        case.review = case.policy.prepare_operation(case.policy.merge(['edge-pruning']),
            disposition='deferred', entries=[], operation_id='signing-merge', sealed_at=case.context['now'],
            expires_at=case.context['now']+300, **case.context)
        roles = check_runtime(self.runtime,self.pin)['roles']
        record = public_record(case.review,roles)
        return signing._packet(record,'d'*64,case.review), roles

    def test_invalid_request_is_refused_before_socket_or_foreground_window(self):
        packet, roles = self.packet()
        count = struct.unpack('>I',packet[:4])[0]
        header, raw = decode(packet[4:4+count]), packet[4+count:]
        for change in ({'nonce':'bad'}, {'review_digest':'0'*64}, {'accepted':True}):
            altered = canonical_bytes({**header,**change})
            bad = struct.pack('>I',len(altered))+altered+raw
            for role, mode in [('broker','sign-review'),('gateway','receive-signed-review')]:
                other = 'gateway' if role=='broker' else 'broker'
                result = subprocess.run([str(self.runtime/role), mode, str(self.root/'s'), roles[other]['code_hash']],
                    input=bad, cwd=self.root, capture_output=True,timeout=10)
                self.assertEqual(2,result.returncode,result.stdout)
                self.assertEqual(b'',result.stdout)
                self.assertFalse((self.root/'s').exists())

    def test_expired_review_never_opens_channel(self):
        packet, roles = self.packet()
        count=struct.unpack('>I',packet[:4])[0]
        head, review = decode(packet[4:4+count]), decode(packet[4+count:])
        review.update(sealed_at=1,expires_at=2)
        raw=canonical_bytes(review); head['review_digest']=hashlib.sha256(raw).hexdigest()
        header=canonical_bytes(head); packet=struct.pack('>I',len(header))+header+raw
        result=subprocess.run([str(self.runtime/'gateway'),'receive-signed-review',str(self.root/'s'),roles['broker']['code_hash']],
                              input=packet,cwd=self.root,capture_output=True,timeout=10)
        self.assertEqual(2,result.returncode); self.assertFalse((self.root/'s').exists())

    def test_changed_review_contract_is_refused_by_both_roles(self):
        packet, roles = self.packet()
        count=struct.unpack('>I',packet[:4])[0]
        head, original=decode(packet[4:4+count]),decode(packet[4+count:])
        for update in ({'authority':'accepted'}, {'acceptance_available':True}, {'authorization_verified':0},
                       {'expires_at':original['sealed_at']+301}, {'operation_digest':'0'*64}):
            raw=canonical_bytes({**original,**update})
            header=canonical_bytes({**head,'review_digest':hashlib.sha256(raw).hexdigest()})
            changed=struct.pack('>I',len(header))+header+raw
            for role, mode, other in [('broker','sign-review','gateway'),('gateway','receive-signed-review','broker')]:
                with self.subTest(update=update,role=role):
                    result=subprocess.run([str(self.runtime/role),mode,str(self.root/'s'),roles[other]['code_hash']],
                        input=changed,cwd=self.root,capture_output=True,timeout=10)
                    self.assertEqual(2,result.returncode)
                    self.assertEqual(b'',result.stdout)
                    self.assertFalse((self.root/'s').exists())

    def test_broker_rejects_same_user_python_listener_before_window(self):
        from concurrent.futures import ThreadPoolExecutor
        packet,roles=self.packet()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
            server.bind(str(self.root/'s')); server.listen(1); server.settimeout(3)
            with ThreadPoolExecutor(max_workers=1) as pool:
                broker=pool.submit(_run,[str(self.runtime/'broker'),'sign-review',str(self.root/'s'),roles['gateway']['code_hash']],
                                   cwd=self.root,input_bytes=packet,timeout=8)
                peer,_=server.accept()
                with peer:
                    peer.settimeout(3)
                    try: data=peer.recv(1024)
                    except ConnectionResetError: data=b''
                    self.assertEqual(b'',data)
                with self.assertRaises(ContractError): broker.result()

    def test_same_user_python_cannot_collect_a_signature(self):
        from concurrent.futures import ThreadPoolExecutor
        packet, roles=self.packet()
        with ThreadPoolExecutor(max_workers=1) as pool:
            receiver=pool.submit(_run,[str(self.runtime/'gateway'),'receive-signed-review',str(self.root/'s'),roles['broker']['code_hash']],
                                 cwd=self.root,input_bytes=packet,timeout=8)
            deadline=time.monotonic()+4
            while not (self.root/'s').exists():
                if receiver.done(): receiver.result()
                self.assertLess(time.monotonic(),deadline)
                time.sleep(.01)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
                peer.settimeout(3); peer.connect(str(self.root/'s'))
                try: data=peer.recv(1024)
                except ConnectionResetError: data=b''
                self.assertEqual(b'',data)
            with self.assertRaises(ContractError): receiver.result()
        self.assertFalse((self.root/'s').exists())

    def test_actual_peers_reject_missing_key_without_window_or_signature(self):
        from concurrent.futures import ThreadPoolExecutor
        packet, roles = self.packet()
        before = {p.name:p.read_bytes() for p in self.runtime.iterdir()}
        with ThreadPoolExecutor(max_workers=1) as pool:
            receiver = pool.submit(_run, [str(self.runtime/'gateway'),'receive-signed-review',str(self.root/'s'),roles['broker']['code_hash']],
                                   cwd=self.root,input_bytes=packet,timeout=10)
            deadline=time.monotonic()+4
            while not (self.root/'s').exists():
                if receiver.done(): receiver.result()
                self.assertLess(time.monotonic(),deadline); time.sleep(.01)
            with self.assertRaises(ContractError):
                _run([str(self.runtime/'broker'),'sign-review',str(self.root/'s'),roles['gateway']['code_hash']],
                     cwd=self.root,input_bytes=packet,timeout=8)
            with self.assertRaises(ContractError): receiver.result()
        self.assertFalse((self.root/'s').exists())
        self.assertFalse((self.root/'key-registration.json').exists())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.runtime.iterdir()})

    def test_actual_v2_peers_refuse_missing_key_without_foreground_prompt(self):
        from dataclasses import replace
        from tests.application.test_paper_record_transition import PaperRecordTransitionTests
        case = PaperRecordTransitionTests(); case.setUp()
        original = case.seal(ai=True)
        value = decode(original.payload)
        now = int(time.time()); value.update(sealed_at=now, expires_at=now + 300)
        raw = canonical_bytes(value)
        review = replace(original, payload=raw, digest=hashlib.sha256(raw).hexdigest())
        roles = check_runtime(self.runtime, self.pin)['roles']
        packet = signing._packet(public_record(review, roles), 'd' * 64, review)
        with patch.object(self, 'packet', return_value=(packet, roles)):
            self.test_actual_peers_reject_missing_key_without_window_or_signature()

    def test_native_signature_binds_full_packet_and_rejects_replay(self):
        packet, roles = self.packet()
        # Exercise legal prose escapes at both the review and operation digest.
        count = struct.unpack('>I', packet[:4])[0]
        header, review = decode(packet[4:4+count]), decode(packet[4+count:])
        review['operation']['effect']['judgment']['text'] += '\b\f\x01\x1f\x7f\u2028/\\"😀각é'
        review['operation_digest'] = hashlib.sha256(canonical_bytes(review['operation'])).hexdigest()
        raw = canonical_bytes(review)
        header.update(review_digest=hashlib.sha256(raw).hexdigest(), operation_digest=review['operation_digest'])
        head = canonical_bytes(header); packet = struct.pack('>I',len(head))+head+raw
        source=SOURCE.read_text()
        helpers=source[source.index('func hashHex('):source.index('let signingLimit =')]
        contract=source[source.index('let signingLimit ='):source.index('func signingResult()')]
        enrollment_source = SOURCE.with_name('Enrollment.swift').read_text()
        enrollment_type = enrollment_source[enrollment_source.index('struct NativeEnrollment {'):
                                            enrollment_source.index('func enrollmentRecord(')]
        program=self.root/'signature.swift'
        program.write_text('import Foundation\nimport Security\nimport CryptoKit\nlet role="broker"\n' +
            'enum DeliveryError: Error { case invalid, timeout }\nfunc inspect() -> [String: Any]? { ["code_hash":"'+roles['broker']['code_hash']+'"] }\n'+
            helpers + enrollment_type +
            'func enrollmentRoot() throws -> String { throw DeliveryError.invalid }\n' +
            'func loadEnrollment(_ id: String, forRevocation: Bool = false) throws -> NativeEnrollment { throw DeliveryError.invalid }\n' + contract+'''
let raw = try FileHandle.standardInput.readToEnd()!
let request = try ReviewSigningRequest(raw)
try request.fresh()
precondition(!finiteJSON("e\\u{0301}"))
precondition(finiteJSON("é"))
precondition(visibleReviewText("a\\u{200b}b\\n각") == "a\\\\u{200b}b\\n각")
precondition(visibleReviewText("\\u{3164}\\u{2028}\\u{0001}") == "\\\\u{3164}\\\\u{2028}\\\\u{1}")
let key = try P256.Signing.PrivateKey(rawRepresentation: Data(repeating: 0, count: 31) + Data([1]))
precondition(key.publicKey.x963Representation == request.publicKey.x963Representation)
let signature = try key.signature(for: request.message)
let reply = try encoded(["status":"signed-unaccepted-review", "signature_der": signature.derRepresentation.base64EncodedString()])
precondition(try request.verifiedReply(reply).0 == "signed-unaccepted-review")
let count = Int(raw.prefix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) })
var head = request.header; head["nonce"] = String(repeating: "0", count: 64)
let header = try encoded(head)
var length = UInt32(header.count).bigEndian
let packet = withUnsafeBytes(of: &length) { Data($0) } + header + Data(raw[(4+count)...])
let replacement = try ReviewSigningRequest(packet)
var denied = false
do { _ = try replacement.verifiedReply(reply) } catch { denied = true }
precondition(denied)
var bad = ["status":"signed-unaccepted-review", "signature_der": Data(repeating: 0, count: 70).base64EncodedString()]
denied = false
do { _ = try request.verifiedReply(encoded(bad)) } catch { denied = true }
precondition(denied)
print("signature verified; different nonce and invalid signature denied")
'''.replace('precondition(try request.verifiedReply(reply).0 == "signed-unaccepted-review")',
            'let verified = try request.verifiedReply(reply)\nprecondition(verified.0 == "signed-unaccepted-review")'))
        output,errors=_run(['/usr/bin/xcrun','swift','-module-cache-path',str(self.root/'cache'),str(program)],
                           cwd=self.root,input_bytes=packet,timeout=90)
        self.assertEqual(b'',errors)
        self.assertEqual(b'signature verified; different nonce and invalid signature denied\n',output)

    def test_native_v2_signature_binds_registry_and_closed_record_version(self):
        from tests.application.test_paper_record_transition import PaperRecordTransitionTests
        case = PaperRecordTransitionTests(); case.setUp()
        case_review = case.seal(ai=True)
        value = decode(case_review.payload)
        value.update(sealed_at=int(time.time()), expires_at=int(time.time()) + 300)
        from dataclasses import replace
        review = replace(case_review, payload=canonical_bytes(value), digest=hashlib.sha256(canonical_bytes(value)).hexdigest())
        roles = check_runtime(self.runtime, self.pin)['roles']
        packet = signing._packet(public_record(review, roles), 'd' * 64, review)
        source = SOURCE.read_text()
        helpers = source[source.index('func hashHex('):source.index('let signingLimit =')]
        contract = source[source.index('let signingLimit ='):source.index('func signingResult()')]
        enrollment_source = SOURCE.with_name('Enrollment.swift').read_text()
        enrollment_type = enrollment_source[enrollment_source.index('struct NativeEnrollment {'):
                                            enrollment_source.index('func enrollmentRecord(')]
        program = self.root / 'v2-signature.swift'
        program.write_text('import Foundation\nimport Security\nimport CryptoKit\nlet role="broker"\n' +
            'enum DeliveryError: Error { case invalid, timeout }\nfunc inspect() -> [String: Any]? { ["code_hash":"' + roles['broker']['code_hash'] + '"] }\n' +
            helpers + enrollment_type +
            'func enrollmentRoot() throws -> String { throw DeliveryError.invalid }\n' +
            'func loadEnrollment(_ id: String, forRevocation: Bool = false) throws -> NativeEnrollment { throw DeliveryError.invalid }\n' + contract + '''
let raw = try FileHandle.standardInput.readToEnd()!
let request = try ReviewSigningRequest(raw)
try request.fresh()
let key = try P256.Signing.PrivateKey(rawRepresentation: Data(repeating: 0, count: 31) + Data([1]))
let signature = try key.signature(for: request.message)
let reply = try encoded(["status":"signed-unaccepted-review", "signature_der":signature.derRepresentation.base64EncodedString()])
let verified = try request.verifiedReply(reply)
precondition(verified.0 == "signed-unaccepted-review")
func packetFor(_ review: [String: Any]) throws -> Data {
    var head = request.header
    let bytes = try encoded(review)
    head["review_digest"] = hashHex(bytes)
    head["operation_digest"] = try hashHex(encoded(review["operation"]!))
    let header = try encoded(head)
    var length = UInt32(header.count).bigEndian
    return withUnsafeBytes(of: &length) { Data($0) } + header + bytes
}
var changed = request.review
changed["origin_registry_digest"] = String(repeating: "0", count: 64)
let replacement = try ReviewSigningRequest(packetFor(changed))
var refused = false
do { _ = try replacement.verifiedReply(reply) } catch { refused = true }
precondition(refused)
var invalid = [[String: Any]]()
changed = request.review; changed.removeValue(forKey: "origin_registry_digest"); invalid.append(changed)
changed = request.review; changed["origin_registry_digest"] = "bad"; invalid.append(changed)
changed = request.review; changed["origin_registry_digest"] = true; invalid.append(changed)
changed = request.review; changed["extra"] = false; invalid.append(changed)
changed = request.review; changed["schema"] = "claimbranch.paper-operation-review/v3"; invalid.append(changed)
changed = request.review; changed["schema"] = "claimbranch.paper-operation-review/v1"; invalid.append(changed)
changed = request.review
var operation = request.operation; operation["action"] = "apply-selected-merge"
changed["operation"] = operation; changed["operation_digest"] = try hashHex(encoded(operation)); invalid.append(changed)
for review in invalid {
    refused = false
    do { _ = try ReviewSigningRequest(packetFor(review)) } catch { refused = true }
    precondition(refused)
}
let observation = request.observation(verified)
precondition(nativeFalse(observation["authorization_verified"]))
precondition(nativeFalse(observation["protected_acceptance_available"]))
print("v2 signature verified; changed registry and invalid versions denied; no authority")
''')
        output, errors = _run(['/usr/bin/xcrun', 'swift', '-module-cache-path', str(self.root/'cache'), str(program)],
                              cwd=self.root, input_bytes=packet, timeout=90)
        self.assertEqual(b'', errors)
        self.assertEqual(b'v2 signature verified; changed registry and invalid versions denied; no authority\n', output)

    def test_cancellation_terminates_waiting_native_child(self):
        from threading import Event, Timer
        event=Event(); timer=Timer(.1,event.set); timer.start()
        try:
            started=time.monotonic()
            with self.assertRaisesRegex(ContractError,'cancelled'):
                _run([sys.executable,'-I','-S','-c','import time; time.sleep(20)'],cwd=self.root,
                     timeout=30,cancel_event=event)
            self.assertLess(time.monotonic()-started,3)
        finally: timer.cancel()


@unittest.skipUnless(sys.platform == 'darwin', 'private native directories require macOS')
class SigningOrchestrationTests(unittest.TestCase):
    def setUp(self):
        from threading import Event
        self.temporary = tempfile.TemporaryDirectory(prefix='cb-sign-orchestration-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.runtime = self.root/'runtime'; self.runtime.mkdir(mode=0o700)
        self.keys = self.root/'keys'; self.keys.mkdir(mode=0o700)
        case = ReviewSigningBindingTests(); case.setUp(); self.review = case.review
        self.record = public_record(self.review)
        self.report = {'build_pin':'a'*64,'roles':{'broker':{'code_hash':'b'*40},'gateway':{'code_hash':'c'*40}}}
        self.started = Event(); self.mode = 'success'; self.cancellation_seen = False

    def native(self, args, **kwargs):
        role = Path(args[0]).name
        if self.mode == 'receiver-early' and role == 'gateway': raise ContractError('receiver failed')
        if self.mode == 'never-ready' and role == 'gateway':
            self.cancellation_seen = kwargs['cancel_event'].wait(2)
            if not self.cancellation_seen: raise AssertionError('unready receiver was not cancelled')
            raise ContractError('unready receiver cancelled')
        packet = kwargs['input_bytes']
        value = {'schema':'claimbranch.native-review-signing/v1','role':role,'status':'signed-unaccepted-review',
                 'exchange_digest':hashlib.sha256(packet).hexdigest(),'review_digest':self.review.digest,
                 'operation_digest':decode(self.review.payload)['operation_digest'], 'peer_verified':True,
                 'signature_verified':True,'authorization_verified':False,'protected_acceptance_available':False}
        if role == 'gateway':
            server = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            path = Path(args[2])
            try:
                # Publish the intended fixture mode atomically. The real native
                # receiver sets umask before bind; a bind/chmod test race is not
                # a product readiness failure.
                preparing = path.with_name('preparing')
                server.bind(str(preparing)); preparing.chmod(0o777 if self.mode=='wrong-mode' else 0o700)
                preparing.rename(path)
                if self.mode in ('sender-fails','wrong-mode'):
                    self.cancellation_seen = kwargs['cancel_event'].wait(2)
                    if not self.cancellation_seen: raise AssertionError('receiver was not cancelled')
                    raise ContractError('receiver cancelled')
                self.assertTrue(self.started.wait(2),'sender did not start')
                if self.mode == 'receiver-dies': raise ContractError('receiver died during signing')
                if self.mode == 'disagree': value.update(status='cancelled',signature_verified=False,stop_source='review-window')
            finally:
                server.close()
                if self.mode != 'leftover': path.unlink(missing_ok=True)
        else:
            self.started.set()
            if self.mode=='sender-fails': raise ContractError('sender failed')
            if self.mode=='receiver-dies':
                self.cancellation_seen=kwargs['cancel_event'].wait(2)
                if not self.cancellation_seen: raise AssertionError('sender was not cancelled')
                raise ContractError('sender cancelled')
        return canonical_bytes(value), b'framework noise' if self.mode=='stderr' else b''

    def run_case(self, mode):
        self.mode = mode
        changed = deepcopy(self.record); changed['body']['public_key_x963'] = 'changed'
        records = [self.record,changed] if mode=='key-changed' else [self.record,self.record]
        with patch.object(signing,'check_runtime',return_value=self.report), \
             patch.object(signing,'_current'), patch.object(signing,'reopen_key'), \
             patch.object(signing,'_read_registration',side_effect=records), patch.object(signing,'_run',side_effect=self.native):
            return signing._sign_checked(self.runtime,'a'*64,self.keys,'d'*64,self.review)

    def test_success_is_digest_only_and_key_is_rechecked(self):
        result=self.run_case('success')
        self.assertEqual('signed-unaccepted-review',result['status'])
        self.assertNotIn('signature_der',result)
        self.assertFalse(result['authorization_verified'])

    def test_failed_peers_cancel_each_other_promptly(self):
        for mode in ('sender-fails','receiver-dies','wrong-mode'):
            with self.subTest(mode=mode):
                self.started.clear(); self.cancellation_seen=False
                with self.assertRaises(ContractError): self.run_case(mode)
                self.assertTrue(self.cancellation_seen)

    def test_readiness_timeout_cancels_receiver_without_waiting_for_auth_deadline(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        clock=SimpleNamespace(monotonic=Mock(side_effect=[0,100]),sleep=lambda _: None)
        with patch.object(signing,'time',clock), self.assertRaisesRegex(ContractError,'did not become ready'):
            self.run_case('never-ready')
        self.assertTrue(self.cancellation_seen)

    def test_inconsistent_or_changed_completion_is_rejected(self):
        for mode in ('receiver-early','disagree','stderr','leftover','key-changed'):
            with self.subTest(mode=mode):
                self.started.clear()
                with self.assertRaises(ContractError): self.run_case(mode)
