from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import socket
import time
import unittest
from unittest.mock import patch

from claimbranch.application import mac_review_delivery as delivery
from claimbranch.application.mac_runtime import build_runtime, check_runtime, _run
from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.core.canonical import ContractError
from tests.contract.test_paper_episodes import first_episode


class ReviewDeliveryBindingTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(ai=True, merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        self.context = dict(manuscript_digest='b' * 64, session_nonce='delivery-session', now=1800000000)
        self.review = self.policy.prepare_operation(self.policy.merge(['edge-pruning']),
            disposition='deferred', entries=[], operation_id='delivery-merge',
            sealed_at=self.context['now'], expires_at=self.context['now'] + 300, **self.context)

    def send(self):
        return delivery.deliver_operation_review('/unused', 'a' * 64, self.policy, self.review,
                                                 current_context=lambda: deepcopy(self.context))

    def test_exact_owned_review_is_delivered_without_accepting_history(self):
        before = self.history.manifest()
        with patch.object(delivery, '_exchange', return_value=None) as exchange:
            result = self.send()
        raw = exchange.call_args.args[2]
        self.assertEqual(self.review.payload, raw[32:])
        self.assertEqual(32, len(raw[:32]))
        self.assertEqual(self.review.digest, result['review_digest'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result['exchange_digest'])
        self.assertFalse(result['authorization_verified'])
        self.assertFalse(result['protected_acceptance_available'])
        self.assertEqual(before, self.history.manifest())

    def test_replacement_review_and_deserialized_review_cannot_start_delivery(self):
        other = PaperReviewPolicy(self.history, episode_id='episode')
        other.restore_operation(self.review.payload, **self.context)
        for policy in (other, self.policy):
            if policy is self.policy:
                policy.merge(['replication'])
            with patch.object(delivery, '_exchange') as exchange, self.assertRaises(ContractError):
                delivery.deliver_operation_review('/unused', 'a' * 64, policy, self.review,
                                                  current_context=lambda: self.context)
            exchange.assert_not_called()

    def test_changed_scope_source_or_expiry_during_delivery_refuses_success(self):
        for key, value in [('manuscript_digest', 'c' * 64), ('session_nonce', 'new-session'),
                           ('now', 1800000300)]:
            original = deepcopy(self.context)
            with patch.object(delivery, '_exchange', side_effect=lambda *a: self.context.update({key: value})):
                with self.subTest(key=key), self.assertRaises(ContractError): self.send()
            self.context = original
        with patch.object(delivery, '_exchange', side_effect=lambda *a: self.policy.merge(['replication'])):
            with self.assertRaises(ContractError): self.send()

    def test_new_exchange_has_fresh_nonce_and_never_reuses_authority(self):
        with patch.object(delivery, '_exchange', return_value=None):
            first, second = self.send(), self.send()
        self.assertEqual(first['review_digest'], second['review_digest'])
        self.assertNotEqual(first['exchange_digest'], second['exchange_digest'])
        self.assertEqual('delivered-unaccepted-review', first['status'])

    def test_invalid_context_shape_fails_before_transport(self):
        for context in (None, [], {**self.context, 'accepted': True}):
            with patch.object(delivery, '_exchange') as exchange, self.assertRaises(ContractError):
                delivery.deliver_operation_review('/unused', 'a' * 64, self.policy, self.review,
                                                  current_context=lambda: context)
            exchange.assert_not_called()


@unittest.skipUnless(sys.platform == 'darwin', 'native delivery requires macOS')
class NativeReviewDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='cb-delivery-tests-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name).resolve()
        cls.runtime = cls.root / 'runtime'
        cls.runtime.mkdir(mode=0o700)
        cls.pin = build_runtime(cls.runtime)

    def test_actual_roles_exchange_full_bounded_payload_without_persisting_it(self):
        before = {p.name: p.read_bytes() for p in self.runtime.iterdir()}
        delivery._exchange(self.runtime, self.pin, b'n' * 32 + b'x' * 262144)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})

    def test_current_scientific_review_reaches_native_roles_without_acceptance(self):
        case = ReviewDeliveryBindingTests()
        case.setUp()
        before = case.history.manifest()
        result = delivery.deliver_operation_review(self.runtime, self.pin, case.policy, case.review,
                                                   current_context=lambda: case.context)
        self.assertEqual(case.review.digest, result['review_digest'])
        self.assertEqual('delivered-unaccepted-review', result['status'])
        self.assertFalse(result['authorization_verified'])
        self.assertEqual(before, case.history.manifest())

    def test_wrong_pin_and_invalid_payload_do_not_launch(self):
        with patch.object(delivery, '_run') as execute:
            for raw in (b'', b'n' * (262144 + 33)):
                with self.assertRaises(ContractError): delivery._exchange(self.runtime, self.pin, raw)
            with self.assertRaises(ContractError): delivery._exchange(self.runtime, '0' * 64, b'n' * 33)
            execute.assert_not_called()

    def test_fresh_application_process_uses_packaged_roles(self):
        script = ('import sys; from claimbranch.application.mac_review_delivery import _exchange; '
                  '_exchange(sys.argv[1], sys.argv[2], b"n" * 32 + b"retained review")')
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.runtime), self.pin],
                                capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b'', result.stdout)

    def test_compile_time_roles_cannot_swap_send_and_receive(self):
        for role, action in [('broker', 'receive-review'), ('gateway', 'send-review')]:
            result = subprocess.run([str(self.runtime / role), action, '/unused', 'a' * 40],
                                    input=b'n' * 33, capture_output=True, timeout=5)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b'', result.stdout)

    def test_runner_drains_large_input_and_output_with_one_deadline(self):
        raw = b'x' * 262176
        out, _ = _run([sys.executable, '-I', '-S', '-c',
                      'import sys; b=sys.stdin.buffer.read(); print(len(b))'],
                      cwd=self.root, input_bytes=raw)
        self.assertEqual(b'262176\n', out)
        with self.assertRaisesRegex(ContractError, 'timed out'):
            _run([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(10)'],
                 cwd=self.root, input_bytes=raw, timeout=.1)

    def pair(self, *, receiver_input, sender_input, receiver_pin=None, sender_pin=None, python_peer=False):
        roles = check_runtime(self.runtime, self.pin)['roles']
        with tempfile.TemporaryDirectory(prefix='cb-neg-', dir='/private/tmp') as temporary:
            path = Path(temporary) / 's'
            with ThreadPoolExecutor(max_workers=1) as pool:
                receiving = pool.submit(_run, [str(self.runtime / 'gateway'), 'receive-review', str(path),
                    receiver_pin or roles['broker']['code_hash']], cwd=temporary, input_bytes=receiver_input,
                    timeout=12, limit=4096)
                until = time.monotonic() + 5
                while not path.exists():
                    if receiving.done(): receiving.result()
                    if time.monotonic() >= until: self.fail('receiver never created socket')
                    time.sleep(.01)
                if python_peer:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                        peer.settimeout(3)
                        peer.connect(str(path))
                        self.assertEqual(b'', peer.recv(4))
                else:
                    with self.assertRaises(ContractError):
                        _run([str(self.runtime / 'broker'), 'send-review', str(path),
                              sender_pin or roles['gateway']['code_hash']], cwd=temporary,
                              input_bytes=sender_input, timeout=12, limit=4096)
                with self.assertRaises(ContractError): receiving.result()
            self.assertFalse(path.exists())

    def test_both_peers_enforce_exact_code_identity(self):
        for pins in ({'receiver_pin': '0' * 40}, {'sender_pin': '0' * 40}):
            with self.subTest(pins=pins): self.pair(receiver_input=b'n' * 33, sender_input=b'n' * 33, **pins)

    def test_same_user_python_process_cannot_read_or_deliver_review(self):
        self.pair(receiver_input=b'n' * 33, sender_input=b'n' * 33, python_peer=True)

    def test_other_review_or_prior_nonce_cannot_match_current_exchange(self):
        for other in (b'n' * 32 + b'other project', b'o' * 32 + b'current review'):
            with self.subTest(other=other):
                self.pair(receiver_input=b'n' * 32 + b'current review', sender_input=other)

    def test_pipe_input_limit_rejected_by_native_code(self):
        result = subprocess.run([str(self.runtime / 'broker'), 'send-review', '/unused', 'a' * 40],
                                input=b'x' * 262177, capture_output=True, timeout=12)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b'', result.stdout)

    def test_successful_early_exit_is_not_misreported_as_unavailable_tool(self):
        with self.assertRaisesRegex(ContractError, 'input was not fully delivered'):
            _run(['/usr/bin/true'], cwd=self.root, input_bytes=b'x' * 262176)

    def test_broker_waits_for_receiver_readiness_within_bound(self):
        roles = check_runtime(self.runtime, self.pin)['roles']
        with tempfile.TemporaryDirectory(prefix='cb-ready-', dir='/private/tmp') as temporary:
            path = Path(temporary) / 's'
            with ThreadPoolExecutor(max_workers=1) as pool:
                sending = pool.submit(_run, [str(self.runtime / 'broker'), 'send-review', str(path),
                    roles['gateway']['code_hash']], cwd=temporary, input_bytes=b'n' * 33, timeout=12)
                time.sleep(.15)
                _run([str(self.runtime / 'gateway'), 'receive-review', str(path),
                      roles['broker']['code_hash']], cwd=temporary, input_bytes=b'n' * 33, timeout=12)
                self.assertEqual('delivered-unaccepted-review', json.loads(sending.result()[0])['status'])

    def test_delivery_does_not_require_shared_world_writable_temp_root(self):
        original = tempfile.TemporaryDirectory
        def private_directory(*args, **kwargs):
            base = Path(kwargs.get('dir') or tempfile.gettempdir())
            if base.stat().st_mode & 0o022:
                raise PermissionError('shared temporary root unavailable')
            return original(*args, **kwargs)
        with patch.object(delivery.tempfile, 'TemporaryDirectory', side_effect=private_directory):
            delivery._exchange(self.runtime, self.pin, b'n' * 33)

    def test_direct_native_invocation_does_not_change_terminal_flags(self):
        import fcntl
        import os
        import pty
        master, slave = pty.openpty()
        try:
            before = fcntl.fcntl(slave, fcntl.F_GETFL)
            result = subprocess.run([str(self.runtime / 'broker'), 'send-review', '/unused', 'a' * 40],
                                    stdin=slave, capture_output=True, timeout=5)
            self.assertEqual(2, result.returncode)
            self.assertEqual(before, fcntl.fcntl(slave, fcntl.F_GETFL))
            self.assertEqual(b'', result.stdout)
        finally:
            os.close(master)
            os.close(slave)
