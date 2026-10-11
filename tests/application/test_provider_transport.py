"""Owned synthetic peers test wire I/O, never qualify a real provider."""
import json
import os
import subprocess
import ssl
import sys
from dataclasses import replace
from pathlib import Path
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from claimbranch.application.provider_transport import ProviderTransport
from claimbranch.application.provider_profile import prepare_provider_request
from claimbranch.application.provider_profile import POLICY
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.context import ContextRecord, compile_context
from tests.application.test_provider_profile import prepared, profile, wrapper
from tests.application.test_paper_proposals import response


class Peer:
    def __init__(self, reply=None, *, status=200, delay=0, headers=None, declared=True, body_delay=0,
                 tls=None, chunk_delay=0, disconnect=False):
        self.requests = []
        self.arrived = threading.Event()
        self.release = threading.Event()
        self.reply = reply if reply is not None else json.dumps(wrapper('openai-chat', canonical_bytes(response()).decode())).encode()
        self.status, self.delay = status, delay
        self.headers = headers or {}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                owner.requests.append((self.path, dict(self.headers), body))
                owner.arrived.set()
                if disconnect:
                    self.close_connection = True
                    return
                if owner.delay:
                    owner.release.wait(owner.delay)
                try:
                    self.send_response(owner.status)
                    self.send_header('Content-Type', 'application/json')
                    if declared: self.send_header('Content-Length', str(len(owner.reply)))
                    for key, value in owner.headers.items(): self.send_header(key, value)
                    self.end_headers()
                    if body_delay: time.sleep(body_delay)
                    if chunk_delay:
                        for start in range(0, len(owner.reply), 250):
                            self.wfile.write(owner.reply[start:start+250]); self.wfile.flush(); time.sleep(chunk_delay)
                    else: self.wfile.write(owner.reply)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *_): pass
        class OwnedHTTPServer(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                if isinstance(sys.exception(), (ConnectionResetError, BrokenPipeError)): return
                super().handle_error(request, client_address)
        self.server = OwnedHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.scheme = 'https' if tls else 'http'
        if tls: self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def endpoint(self): return f'{self.scheme}://127.0.0.1:{self.server.server_port}/v1/chat/completions'
    def close(self):
        self.release.set(); self.server.shutdown(); self.server.server_close(); self.thread.join(2)


class ProviderTransportTests(unittest.TestCase):
    def setUp(self):
        self.transport = ProviderTransport()
        self.addCleanup(self.transport.wait_closed, 2)
        self.addCleanup(self.transport.close)

    @contextmanager
    def synthetic_deadlines(self, limits):
        # Accelerate owned test I/O after the exact v1 request passes preflight;
        # do not label a modified public request policy as historical v1.
        from claimbranch.application.provider_transport import ProviderJob
        def start_job(prepared, credential, packet, current):
            changed={**current,**limits}
            wire=json.loads(packet);wire.update(changed)
            return ProviderJob(prepared,credential,json.dumps(wire).encode(),changed)
        with patch('claimbranch.application.provider_transport.ProviderJob',side_effect=start_job):
            yield

    def peer(self, **kwargs):
        peer = Peer(**kwargs); self.addCleanup(peer.close); return peer

    def request(self, peer, *, api='openai-chat', credential_env=None, request_id='request-1'):
        base = prepared(api)
        config = profile(api, endpoint=peer.endpoint, credential_env=credential_env)
        return prepare_provider_request(config, base.context, request_id=request_id,
                                        nonce='nonce-'+request_id, now=100)

    def start(self, item, **kwargs):
        return self.transport.start(item, confirmed_digest=item.digest,
            current_profile=item.profile, current_context=item.context, now=100, **kwargs)

    def finish(self, job):
        deadline = time.monotonic()+4
        while job.poll() is None and time.monotonic() < deadline: time.sleep(.01)
        self.assertIsNotNone(job.poll(), 'owned request did not finish')
        self.assertTrue(job.wait_closed(2), 'child was not reaped')
        return job.poll()

    def test_exact_wire_round_trip_returns_typed_bytes_without_scientific_writes(self):
        peer = self.peer(); item = self.request(peer)
        job = self.start(item); result = self.finish(job)
        self.assertEqual('completed', result.disposition)
        self.assertEqual(response(), decode(result.typed_result))
        self.assertEqual(item.digest, result.request_digest)
        self.assertEqual(item.body, peer.requests[0][2])
        self.assertEqual('/v1/chat/completions', peer.requests[0][0])
        self.assertNotIn('Authorization', peer.requests[0][1])
        for key, value in item.preview()['headers_without_credentials'].items():
            self.assertEqual(value, peer.requests[0][1][key])

    def test_missing_or_changed_confirmation_refuses_before_network_and_key_lookup(self):
        peer = self.peer(); item = self.request(peer, credential_env='MY_LLM_KEY')
        with patch('os.environ.get', side_effect=AssertionError('no key lookup')):
            for digest in (None, '', 'other'):
                with self.assertRaises(ContractError):
                    self.transport.start(item, confirmed_digest=digest,
                        current_profile=item.profile, current_context=item.context, now=100)
            with self.assertRaises(ContractError):
                self.transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=prepared(include_draft=True).context, now=100)
            with self.assertRaises(ContractError):
                self.transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=item.context, now=220)
        self.assertEqual([], peer.requests)

    def test_cancel_is_immediate_and_late_reply_cannot_replace_it(self):
        peer = self.peer(delay=3); item = self.request(peer)
        start = time.monotonic(); job = self.start(item)
        self.assertLess(time.monotonic()-start, .5)
        self.assertTrue(peer.arrived.wait(2))
        start = time.monotonic(); self.assertTrue(job.cancel())
        self.assertLess(time.monotonic()-start, .2)
        peer.release.set()
        result = self.finish(job)
        self.assertEqual('cancelled', result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertFalse(job.cancel())
        self.assertIsNotNone(job._process.returncode)

    def test_redirect_and_http_errors_are_terminal_and_never_retried(self):
        sink = self.peer()
        for status in (302, 401, 429, 500):
            peer = self.peer(status=status, headers={'Location': sink.endpoint})
            item = self.request(peer, request_id='r-'+str(status))
            with ProviderTransport() as transport:
                job = transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=item.context, now=100)
                result = self.finish(job)
            self.assertEqual('redirect_refused' if status == 302 else 'http_error', result.disposition)
            self.assertEqual(status, result.http_status)
            self.assertEqual(1, len(peer.requests))
            self.assertIsNone(result.typed_result)
        self.assertEqual([], sink.requests)

    def test_malformed_and_oversized_response_never_reaches_typed_ingress(self):
        for raw, disposition in ((b'{', 'malformed_response'), (b'x'*65537, 'response_too_large')):
            peer = self.peer(reply=raw); result = self.finish(self.start(self.request(peer, request_id=disposition)))
            self.assertEqual(disposition, result.disposition)
            self.assertIsNone(result.typed_result)

    def test_credentials_are_resolved_only_after_review_and_not_in_environment_argv_or_results(self):
        secret = 'unit-test-secret-value'
        peer = self.peer(); item = self.request(peer, credential_env='MY_LLM_KEY')
        real_popen = subprocess.Popen
        launches = []
        def spawn(argv, **kwargs):
            launches.append((argv, kwargs))
            return real_popen(argv, **kwargs)
        with patch.dict(os.environ, {'MY_LLM_KEY': secret, 'UNRELATED_SECRET': 'must-not-inherit',
                                     'HTTP_PROXY': 'http://invalid:1', 'HTTPS_PROXY': 'http://invalid:1'}), \
                patch('subprocess.Popen', side_effect=spawn):
            result = self.finish(self.start(item))
        self.assertEqual('completed', result.disposition)
        self.assertEqual('Bearer '+secret, peer.requests[0][1]['Authorization'])
        self.assertEqual({}, launches[0][1]['env'])
        self.assertTrue(launches[0][1]['close_fds'])
        self.assertNotIn(secret, repr(launches[0]))
        self.assertNotIn(secret, repr(result))
        self.assertNotIn(secret.encode(), peer.requests[0][2])

    def test_anthropic_request_uses_its_own_headers_and_closed_typed_decoder(self):
        peer = self.peer(reply=json.dumps(wrapper('anthropic-messages', canonical_bytes(response()).decode())).encode())
        item = self.request(peer, api='anthropic-messages', credential_env='MY_LLM_KEY')
        with patch.dict(os.environ, {'MY_LLM_KEY': 'test-anthropic-key'}):
            result = self.finish(self.start(item))
        self.assertEqual('completed', result.disposition)
        self.assertEqual(response(), decode(result.typed_result))
        self.assertEqual('test-anthropic-key', peer.requests[0][1]['x-api-key'])
        self.assertEqual('2023-06-01', peer.requests[0][1]['anthropic-version'])
        self.assertNotIn('Authorization', peer.requests[0][1])

    def test_absent_empty_or_header_injection_credential_is_not_sent(self):
        peer = self.peer(); item = self.request(peer, credential_env='MY_LLM_KEY')
        for credential in (None, '', 'secret\r\nInjected: header', '한글', 'x'*4097):
            with patch('os.environ.get', return_value=credential), self.assertRaises(ContractError):
                self.start(item)
        self.assertEqual([], peer.requests)

    def test_exact_replay_nonce_reuse_and_session_budget_refuse_without_extra_network(self):
        peer = self.peer(); first = self.request(peer)
        self.finish(self.start(first))
        with self.assertRaises(ContractError): self.start(first)
        changed_id = prepare_provider_request(first.profile, first.context, request_id='other', nonce=first.review.nonce, now=100)
        with self.assertRaises(ContractError): self.start(changed_id)
        for name in ('request-2', 'request-3'): self.finish(self.start(self.request(peer, request_id=name)))
        with self.assertRaises(ContractError): self.start(self.request(peer, request_id='request-4'))
        with patch.dict(POLICY, {'attempts_per_judgment': 100}), self.assertRaises(ContractError):
            self.start(self.request(peer, request_id='changed-budget'))
        self.assertEqual(3, len(peer.requests))
        self.transport.close()
        with self.assertRaises(ContractError): self.start(self.request(peer, request_id='request-5'))

    def test_read_and_total_timeouts_are_enforced_off_thread_and_reap_the_child(self):
        for limits in ({'read_seconds': 1}, {'total_seconds': 1}):
            with self.synthetic_deadlines(limits):
                peer = self.peer(body_delay=3) if 'read_seconds' in limits else self.peer(delay=3)
                item = self.request(peer, request_id=next(iter(limits)))
                start = time.monotonic(); job = self.start(item)
                self.assertTrue(peer.arrived.wait(2))
                result = self.finish(job)
                self.assertEqual('timed_out', result.disposition)
                self.assertLess(time.monotonic()-start, 2.5)
                self.assertIsNone(result.typed_result)
                peer.release.set()

    def test_connect_including_a_stuck_resolver_is_bounded_by_the_parent(self):
        real_popen = subprocess.Popen
        def stuck(argv, **kwargs):
            return real_popen([sys.executable, '-I', '-c', 'import time;time.sleep(10)'], **kwargs)
        with self.synthetic_deadlines({'connect_seconds': 1}):
            item = self.request(self.peer())
            with patch('subprocess.Popen', side_effect=stuck):
                job = self.start(item); result = self.finish(job)
        self.assertEqual('timed_out', result.disposition)
        self.assertIsNotNone(job._process.returncode)

    def test_unknown_length_overflow_and_ambiguous_or_compressed_framing_refuse(self):
        for extra, raw, declared, disposition in (
                ({}, b'x'*65537, False, 'response_too_large'),
                ({'Content-Length': '0'}, b'{}', True, 'malformed_response'),
                ({'Transfer-Encoding': 'chunked'}, b'{}', True, 'malformed_response'),
                ({'Content-Encoding': 'gzip'}, b'{}', True, 'malformed_response')):
            peer = self.peer(headers=extra, reply=raw, declared=declared)
            with ProviderTransport() as transport:
                item = self.request(peer)
                job = transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=item.context, now=100)
                result = self.finish(job)
            self.assertEqual(disposition, result.disposition)
            self.assertIsNone(result.typed_result)

    def test_credential_echo_even_through_escaped_json_never_enters_returned_content(self):
        secret = 'test-secret-echo'
        for escaped in (False, True):
            value = response(); value['critique'] = secret
            body = json.dumps(wrapper('openai-chat', canonical_bytes(value).decode())).encode()
            if escaped: body = body.replace(secret.encode(), b'\\u0074est-secret-echo')
            peer = self.peer(reply=body)
            with patch.dict(os.environ, {'MY_LLM_KEY': secret}), ProviderTransport() as transport:
                item = self.request(peer, credential_env='MY_LLM_KEY')
                result = self.finish(transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=item.context, now=100))
            self.assertEqual('credential_echo', result.disposition)
            self.assertIsNone(result.typed_result)
            self.assertNotIn(secret, repr(result))

    def test_shutdown_cancels_outstanding_job_and_a_cancel_consumes_its_one_shot(self):
        peer = self.peer(delay=3); item = self.request(peer)
        job = self.start(item); self.assertTrue(peer.arrived.wait(2))
        self.transport.close()
        self.assertEqual('cancelled', self.finish(job).disposition)
        self.assertTrue(self.transport.wait_closed(1))
        self.assertFalse(job.cancel())

    def test_changed_endpoint_settings_and_tampered_wire_refuse_before_dispatch(self):
        peer = self.peer(); item = self.request(peer)
        for changed in (profile(endpoint='https://another.example/v1/chat/completions', credential_env=None),
                        profile(endpoint=peer.endpoint, output_tokens=99, credential_env=None)):
            with self.assertRaises(ContractError):
                self.transport.start(item, confirmed_digest=item.digest,
                    current_profile=changed, current_context=item.context, now=100)
        with self.assertRaises(ContractError): self.start(replace(item, body=item.body+b' '))
        self.assertEqual([], peer.requests)

    def test_valid_chunked_body_and_truncated_declared_body_are_distinguished(self):
        body = json.dumps(wrapper('openai-chat', canonical_bytes(response()).decode())).encode()
        chunked = hex(len(body))[2:].encode()+b'\r\n'+body+b'\r\n0\r\n\r\n'
        peer = self.peer(reply=chunked, declared=False, headers={'Transfer-Encoding': 'chunked'})
        result = self.finish(self.start(self.request(peer)))
        self.assertEqual('completed', result.disposition)
        self.assertEqual(response(), decode(result.typed_result))
        peer = self.peer(reply=body, declared=False, headers={'Content-Length': str(len(body)+10)})
        result = self.finish(self.start(self.request(peer, request_id='truncated')))
        self.assertEqual('malformed_response', result.disposition)
        self.assertIsNone(result.typed_result)

    def test_cancel_during_process_creation_still_kills_the_later_child(self):
        entered = threading.Event(); release = threading.Event()
        real_popen = subprocess.Popen
        def delayed(argv, **kwargs):
            entered.set(); release.wait(2); return real_popen(argv, **kwargs)
        peer = self.peer(); item = self.request(peer)
        with patch('subprocess.Popen', side_effect=delayed):
            job = self.start(item)
            self.assertTrue(entered.wait(2)); self.assertTrue(job.cancel()); release.set()
            self.assertEqual('cancelled', self.finish(job).disposition)
        self.assertIsNotNone(job._process.returncode)
        self.assertEqual([], peer.requests)

    def test_connection_failure_is_coded_once_and_completed_result_cannot_be_cancelled(self):
        peer = self.peer(); item = self.request(peer); peer.server.shutdown(); peer.server.server_close()
        result = self.finish(self.start(item))
        self.assertEqual('connection_failed', result.disposition)
        peer = self.peer(); job = self.start(self.request(peer, request_id='completed'))
        result = self.finish(job)
        self.assertFalse(job.cancel()); self.assertIs(result, job.poll())

    def test_escaped_credential_in_reported_model_is_not_returned(self):
        secret = 'test-secret-echo'
        value = wrapper('openai-chat', canonical_bytes(response()).decode())
        value['model'] = secret
        raw = json.dumps(value).encode().replace(secret.encode(), b'\\u0074est-secret-echo')
        peer = self.peer(reply=raw)
        with patch.dict(os.environ, {'MY_LLM_KEY': secret}):
            result = self.finish(self.start(self.request(peer, credential_env='MY_LLM_KEY')))
        self.assertEqual('credential_echo', result.disposition)
        self.assertNotIn(secret, repr(result))

    def test_header_progress_starts_a_new_read_interval(self):
        with self.synthetic_deadlines({'read_seconds': 1}):
            peer = self.peer(delay=.8, body_delay=.5); item = self.request(peer)
            result = self.finish(self.start(item))
        self.assertEqual('completed', result.disposition)

    def test_cancel_during_typed_validation_wins_over_the_received_result(self):
        from claimbranch.application.provider_profile import decode_provider_response
        entered = threading.Event(); release = threading.Event()
        def decode_late(*args):
            entered.set(); release.wait(2); return decode_provider_response(*args)
        with patch('claimbranch.application.provider_transport.decode_provider_response', side_effect=decode_late):
            job = self.start(self.request(self.peer()))
            self.assertTrue(entered.wait(2)); self.assertTrue(job.cancel()); release.set()
            result = self.finish(job)
        self.assertEqual('cancelled', result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertIsNotNone(job._process.returncode)

    def test_slow_chunked_reads_reset_idle_deadline_but_total_deadline_still_applies(self):
        value = wrapper('openai-chat', canonical_bytes(response()).decode())
        value['padding'] = 'x'*1024
        body = json.dumps(value).encode()
        with self.synthetic_deadlines({'read_seconds': 1}):
            peer = self.peer(reply=body, declared=False, chunk_delay=.25)
            result = self.finish(self.start(self.request(peer)))
        self.assertEqual('completed', result.disposition)
        self.assertGreater(result.elapsed_ms, 1000)
        with self.synthetic_deadlines({'read_seconds': 1, 'total_seconds': 1}):
            peer = self.peer(reply=body, declared=False, chunk_delay=.25)
            result = self.finish(self.start(self.request(peer, request_id='total')))
        self.assertEqual('timed_out', result.disposition)

    def test_https_rejects_untrusted_certificate_and_does_not_inherit_a_private_ca_override(self):
        fixtures = Path(__file__).resolve().parents[1]/'fixtures'/'providers'
        cert = fixtures/'synthetic-ca.pem'
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, fixtures/'synthetic-server-key.pem')
        peer = self.peer(tls=context)
        # Demonstrate the private CA works when explicitly selected in Python.
        trusted = ssl.create_default_context(cafile=str(cert))
        import socket
        with socket.create_connection(('127.0.0.1', peer.server.server_port), timeout=1) as sock:
            with trusted.wrap_socket(sock, server_hostname='127.0.0.1'): pass
        # The narrow current wire policy deliberately uses default roots, with
        # no implicit import of a CA file or bypass. This is not hosted support.
        with patch.dict(os.environ, {'SSL_CERT_FILE': str(cert)}):
            result = self.finish(self.start(self.request(peer)))
        self.assertEqual('tls_verification_failed', result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertEqual([], peer.requests)

    def test_non_streaming_header_wait_is_bounded_by_total_not_body_idle(self):
        with self.synthetic_deadlines({'read_seconds': 1}):
            peer = self.peer(delay=1.2)
            result = self.finish(self.start(self.request(peer)))
        self.assertEqual('completed', result.disposition)

    def test_credential_mistakenly_used_as_model_id_is_not_transmitted_in_body(self):
        secret = 'opaque-token-model'
        peer = self.peer(); base = self.request(peer, credential_env='MY_LLM_KEY')
        config = profile(endpoint=peer.endpoint, model=secret, credential_env='MY_LLM_KEY')
        item = prepare_provider_request(config, base.context, request_id='r', nonce='n', now=100)
        with patch.dict(os.environ, {'MY_LLM_KEY': secret}), self.assertRaises(ContractError): self.start(item)
        self.assertEqual([], peer.requests)

    def test_spawn_failure_is_redacted_and_closes_without_network(self):
        peer = self.peer()
        with patch('subprocess.Popen', side_effect=OSError('private error text')):
            job = self.start(self.request(peer)); result = self.finish(job)
        self.assertEqual('connection_failed', result.disposition)
        self.assertNotIn('private error text', repr(result))
        self.assertEqual([], peer.requests)

    def test_garbage_crashed_duplicate_and_oversized_worker_protocol_fail_closed(self):
        import claimbranch.application.provider_transport as wire
        real_popen = subprocess.Popen
        scripts = ['raise SystemExit(3)', 'print("not-json")',
                   'print(\'{"disposition":"http_error","http_status":500}\');print(\'{"disposition":"http_error","http_status":500}\')',
                   'import sys;sys.stdout.buffer.write(b"x"*'+str(wire.MAX_OUTPUT+1)+')']
        peer = self.peer()
        for script in scripts:
            def faulty(argv, **kwargs): return real_popen([sys.executable, '-I', '-c', script], **kwargs)
            with ProviderTransport() as transport, patch('subprocess.Popen', side_effect=faulty):
                item = self.request(peer)
                result = self.finish(transport.start(item, confirmed_digest=item.digest,
                    current_profile=item.profile, current_context=item.context, now=100))
            self.assertEqual('connection_failed', result.disposition)
        self.assertEqual([], peer.requests)

    def test_a_late_body_progress_frame_does_not_renew_an_expired_interval(self):
        from claimbranch.application.provider_transport import ProviderJob
        job = ProviderJob.__new__(ProviderJob)
        job._prepared = self.request(self.peer())
        job._lock = threading.Lock(); job._result = None; job._process = None
        now = time.monotonic()
        job._started = now-20; job._connected = job._body_started = True
        job._last_progress = now-POLICY['read_seconds']-1
        job._limits = dict(POLICY)
        before = job._last_progress
        self.assertFalse(job._progress('read'))
        self.assertEqual('timed_out', job.poll().disposition)
        self.assertEqual(before, job._last_progress)

    def test_credential_in_endpoint_or_percent_encoded_path_refuses_before_network(self):
        secret = 'opaque-token-path'
        peer = self.peer(); base = self.request(peer, credential_env='MY_LLM_KEY')
        for component in (secret, '%6Fpaque-token-path'):
            config = profile(endpoint=peer.endpoint+'/'+component, credential_env='MY_LLM_KEY')
            item = prepare_provider_request(config, base.context, request_id='r', nonce='n', now=100)
            with patch.dict(os.environ, {'MY_LLM_KEY': secret}), self.assertRaises(ContractError): self.start(item)
        self.assertEqual([], peer.requests)

    def test_running_total_limit_is_frozen_despite_later_policy_changes(self):
        with self.synthetic_deadlines({'total_seconds': 1}):
            peer = self.peer(delay=3); item = self.request(peer)
            job = self.start(item)
            with patch.dict(POLICY, {'total_seconds': 60}): result = self.finish(job)
        self.assertEqual('timed_out', result.disposition)
        self.assertLess(result.elapsed_ms, 2500)

    def test_peer_disconnect_before_headers_is_connection_failure(self):
        peer = self.peer(disconnect=True)
        result = self.finish(self.start(self.request(peer)))
        self.assertEqual('connection_failed', result.disposition)
        self.assertEqual(1, len(peer.requests))
        self.assertIsNone(result.typed_result)

    def test_resolved_credential_embedded_in_science_refuses_before_network(self):
        secret = 'opaque-token-with-quote"and-backslash\\'
        peer = self.peer(); base = self.request(peer, credential_env='MY_LLM_KEY')
        records = []
        for record in base.context.records:
            fields = decode(record.fields)
            if record.id == 'thesis': fields['statement'] += ' '+secret
            records.append(ContextRecord.create(record.project_id, record.id, record.kind,
                record.sensitivity, fields, schema_version=record.schema_version))
        context = compile_context(tuple(records), base.context.selection)
        item = prepare_provider_request(base.profile, context, request_id='r', nonce='n', now=100)
        with patch.dict(os.environ, {'MY_LLM_KEY': secret}), self.assertRaises(ContractError): self.start(item)
        self.assertEqual([], peer.requests)
