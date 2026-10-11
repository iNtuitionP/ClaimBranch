"""Internal post-review wire I/O; no public provider enablement or topology verdict.

The future application caller must first qualify the actual deployment and own
the human review, attempt history and stale-arrival rules. This component only
checks the exact prepared request and runs bounded I/O. It cannot stage science.
The same-user child is cancellable, NOT a provider sandbox or authority boundary.
"""
import base64
import hashlib
import http.client
import json
import os
import socket
import ssl
import sys
import time
from urllib.parse import unquote, urlsplit

MAX_BYTES = 65_536
MAX_PACKET = 131_072
# At most one progress frame per body read (<=65536), plus bounded final body.
# Frames are consumed immediately; the response/body cap remains 65536 bytes.
MAX_OUTPUT = 2 * 1024 * 1024


def _emit(value):
    sys.stdout.write(json.dumps(value, separators=(',', ':'))+'\n')
    sys.stdout.flush()


def _wire_worker():
    """Standard-library-only child: frozen wire data in stdin, coded output only."""
    conn = None
    try:
        packet_raw = sys.stdin.buffer.read(MAX_PACKET+1)
        if len(packet_raw) > MAX_PACKET: raise ValueError('bounded packet required')
        packet = json.loads(packet_raw)
        raw = base64.b64decode(packet['body'], validate=True)
        if len(raw) > MAX_BYTES:
            raise ValueError('bounded body required')
        url = urlsplit(packet['endpoint'])
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('invalid wire destination')
        connect, read = packet['connect_seconds'], packet['read_seconds']
        headers = packet['headers']
        credential = packet['credential']
        if credential is not None:
            headers['x-api-key' if packet['api'] == 'anthropic-messages' else 'Authorization'] = (
                credential if packet['api'] == 'anthropic-messages' else 'Bearer '+credential)
        if packet['api'] == 'anthropic-messages': headers['anthropic-version'] = '2023-06-01'
        # Direct connections: no proxy environment, redirect handler or retries.
        if url.scheme == 'https':
            conn = http.client.HTTPSConnection(url.hostname, url.port, timeout=connect,
                                               context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(url.hostname, url.port, timeout=connect)
        conn.connect()
        wire_socket = conn.sock
        # Non-streaming generation can precede headers. The parent still caps
        # the whole job, including this wait; body idle starts after headers.
        wire_socket.settimeout(packet['header_seconds'])
        _emit({'phase': 'connected'})
        conn.request('POST', url.path or '/', body=raw, headers=headers)
        # Header parsing is also time- and size-bounded in this isolated child.
        http.client._MAXLINE = 8192
        http.client._MAXHEADERS = 32
        reply = conn.getresponse()
        wire_socket.settimeout(read)
        _emit({'phase': 'headers'})
        status = reply.status
        if 300 <= status < 400:
            _emit({'disposition': 'redirect_refused', 'http_status': status}); return
        if status != 200:
            _emit({'disposition': 'http_error', 'http_status': status}); return
        if sum(len(k)+len(v) for k, v in reply.getheaders()) > 8192:
            _emit({'disposition': 'malformed_response', 'http_status': status}); return
        lengths = reply.headers.get_all('Content-Length', [])
        transfers = reply.headers.get_all('Transfer-Encoding', [])
        if (len(lengths) > 1 or len(transfers) > 1 or (lengths and transfers)
                or (transfers and transfers[0].lower() != 'chunked')
                or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit()))
                or reply.getheader('Content-Encoding', 'identity').lower() != 'identity'
                or reply.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json'):
            _emit({'disposition': 'malformed_response', 'http_status': status}); return
        declared = int(lengths[0]) if lengths else None
        if declared is not None and declared > MAX_BYTES:
            _emit({'disposition': 'response_too_large', 'http_status': status}); return
        body = bytearray()
        while True:
            part = reply.read1(min(8192, MAX_BYTES+1-len(body)))
            if not part: break
            body.extend(part)
            if len(body) > MAX_BYTES:
                _emit({'disposition': 'response_too_large', 'http_status': status}); return
            _emit({'phase': 'read'})
        if declared is not None and len(body) != declared:
            _emit({'disposition': 'malformed_response', 'http_status': status}); return
        if credential and credential.encode('ascii') in body:
            _emit({'disposition': 'credential_echo', 'http_status': status}); return
        _emit({'disposition': 'received', 'http_status': status,
               'body': base64.b64encode(body).decode('ascii')})
    except (socket.timeout, TimeoutError):
        _emit({'disposition': 'timed_out', 'http_status': None})
    except (ConnectionError, http.client.RemoteDisconnected):
        _emit({'disposition': 'connection_failed', 'http_status': None})
    except ssl.SSLCertVerificationError:
        _emit({'disposition': 'tls_verification_failed', 'http_status': None})
    except (http.client.HTTPException, ValueError, TypeError, KeyError, UnicodeError):
        _emit({'disposition': 'malformed_response', 'http_status': None})
    except (OSError, ssl.SSLError):
        _emit({'disposition': 'connection_failed', 'http_status': None})
    finally:
        if conn is not None: conn.close()


if __name__ == '__main__':
    # -I script execution loads no application, research or third-party module.
    if sys.argv[1:] != ['--wire-worker']: raise SystemExit(2)
    _wire_worker()
    raise SystemExit(0)


import atexit
from dataclasses import dataclass
from pathlib import Path
import selectors
import subprocess
import threading

from claimbranch.core.canonical import ContractError
from .provider_profile import POLICY, PreparedProviderRequest, decode_provider_response
from .provider_profile import provider_request_headers


def _contains_credential(value, credential):
    if isinstance(value, str): return credential in value
    if isinstance(value, dict):
        return any(_contains_credential(k, credential) or _contains_credential(v, credential)
                   for k, v in value.items())
    if isinstance(value, list): return any(_contains_credential(v, credential) for v in value)
    return False


@dataclass(frozen=True)
class TransportResult:
    request_id: str
    request_digest: str
    disposition: str
    elapsed_ms: int
    http_status: int | None = None
    response_digest: str | None = None
    typed_result: bytes | None = None
    reported_model: str | None = None


class ProviderJob:
    """poll/cancel never wait on DNS, socket reads, child exit or typed ingress."""
    def __init__(self, prepared, credential, packet, limits):
        self._prepared = prepared
        self._limits = dict(limits)
        self._lock = threading.Lock()
        self._result = None
        self._process = None
        self._started = time.monotonic()
        self._connected = False
        self._body_started = False
        self._last_progress = self._started
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(credential, packet), daemon=True)
        try:
            self._thread.start()
        except RuntimeError:
            self._finish('connection_failed'); self._closed.set()

    def _finish(self, disposition, **fields):
        with self._lock:
            if self._result is None:
                self._result = TransportResult(self._prepared.review.request_id,
                    self._prepared.digest, disposition,
                    max(0, int((time.monotonic()-self._started)*1000)), **fields)
        return self._result

    def _stop(self, disposition):
        with self._lock:
            if self._result is not None: return False
            self._result = TransportResult(self._prepared.review.request_id,
                self._prepared.digest, disposition,
                max(0, int((time.monotonic()-self._started)*1000)))
            process = self._process
        if process is not None:
            try: process.kill()
            except ProcessLookupError: pass
        return True

    def _expired_locked(self, now):
        return (now-self._started >= self._limits['total_seconds']
            or (not self._connected and now-self._started >= self._limits['connect_seconds'])
            or (self._connected and now-self._last_progress >= self._limits[
                'read_seconds' if self._body_started else 'header_seconds']))

    def _progress(self, phase):
        # Expiry and progress share one critical section. A late frame cannot
        # renew an already elapsed interval between polling and publication.
        with self._lock:
            now = time.monotonic()
            if self._result is not None: return False
            if not self._expired_locked(now):
                if phase == 'connected' and not self._connected:
                    self._connected = True
                elif phase == 'headers' and self._connected and not self._body_started:
                    self._body_started = True
                elif phase != 'read' or not self._body_started:
                    raise ValueError('ordered worker progress required')
                self._last_progress = now
                return True
            self._result = TransportResult(self._prepared.review.request_id,
                self._prepared.digest, 'timed_out', max(0, int((now-self._started)*1000)))
            process = self._process
        if process is not None:
            try: process.kill()
            except ProcessLookupError: pass
        return False

    def poll(self):
        with self._lock: expired = self._expired_locked(time.monotonic())
        if expired: self._stop('timed_out')
        return self._result

    def cancel(self): return self._stop('cancelled')
    def wait_closed(self, timeout=1): return self._closed.wait(timeout)

    def _run(self, credential, packet):
        process = None
        try:
            process = subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()), '--wire-worker'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={}, cwd=str(Path(__file__).resolve().parent), close_fds=True)
            with self._lock: self._process = process
            if self.poll() is not None:
                process.kill(); return
            output = bytearray(); sent = 0; total_output = 0; final = None
            with selectors.DefaultSelector() as selector:
                for pipe, event in ((process.stdin, selectors.EVENT_WRITE), (process.stdout, selectors.EVENT_READ)):
                    os.set_blocking(pipe.fileno(), False); selector.register(pipe, event)
                eof = False
                while not eof and self.poll() is None:
                    for key, _ in selector.select(.05):
                        if key.fileobj is process.stdin:
                            count = os.write(process.stdin.fileno(), packet[sent:sent+8192]); sent += count
                            if sent == len(packet):
                                selector.unregister(process.stdin); process.stdin.close()
                        else:
                            chunk = os.read(process.stdout.fileno(), 8192)
                            if not chunk: eof = True; break
                            output.extend(chunk); total_output += len(chunk)
                            if total_output > MAX_OUTPUT: raise ValueError('bounded worker output required')
                            while b'\n' in output:
                                line, _, rest = output.partition(b'\n'); output = bytearray(rest)
                                value = json.loads(line)
                                if self.poll() is not None: break
                                if 'phase' in value:
                                    if not self._progress(value['phase']): break
                                elif final is None: final = value
                                else: raise ValueError('one completion required')
                if self.poll() is not None: return
                if output or final is None: raise ValueError('complete worker result required')
            disposition = final['disposition']
            status = final['http_status']
            if disposition != 'received':
                if disposition not in ('redirect_refused', 'http_error', 'malformed_response',
                                       'response_too_large', 'timed_out', 'connection_failed',
                                       'tls_verification_failed', 'credential_echo'):
                    raise ValueError('unknown worker result')
                self._finish(disposition, http_status=status); return
            raw = base64.b64decode(final['body'], validate=True)
            if len(raw) > MAX_BYTES: raise ValueError('bounded response required')
            digest = hashlib.sha256(raw).hexdigest()
            try:
                typed = decode_provider_response(self._prepared, raw)
                if credential and (_contains_credential(json.loads(raw), credential)
                                   or _contains_credential(json.loads(typed), credential)):
                    self._finish('credential_echo', http_status=status); return
            except (ContractError, RecursionError):
                self._finish('malformed_response', http_status=status, response_digest=digest); return
            reported = json.loads(raw).get('model')
            if (not isinstance(reported, str) or not reported.isascii() or len(reported) > 128
                    or any(ord(c) < 33 or ord(c) == 127 for c in reported)):
                reported = None
            if self.poll() is None:
                self._finish('completed', http_status=status, response_digest=digest,
                             typed_result=typed, reported_model=reported)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            self._finish('connection_failed')
        finally:
            if process is not None:
                if process.poll() is None:
                    try: process.kill()
                    except ProcessLookupError: pass
                for pipe in (process.stdin, process.stdout):
                    if pipe is not None and not pipe.closed: pipe.close()
                process.wait()
            self._closed.set()


class ProviderTransport:
    """Ephemeral I/O owner. Its budget is NOT durable per-judgment history.

    No public application entry enables this yet. Qualification and foreground intent
    cannot be established by passing a profile/digest to this internal class.
    """
    def __init__(self):
        self._jobs = []
        self._ids = set()
        self._nonces = set()
        self._closed = False
        self._attempt_limit = POLICY['attempts_per_judgment']
        self._lock = threading.Lock()
        atexit.register(self.close)

    def __enter__(self): return self
    def __exit__(self, *_): self.close(); self.wait_closed(2)

    def start(self, prepared, *, confirmed_digest, current_profile, current_context, now):
        # `now` is the trusted caller's current review-clock epoch, like the
        # existing offline broker API; serialized/model-supplied time is invalid
        # at the future app boundary. This library does not mint human consent.
        if type(prepared) is not PreparedProviderRequest or confirmed_digest != prepared.digest:
            raise ContractError('Explicit confirmation of the exact wire digest is required.')
        prepared.recheck(current_profile, current_context, now=now)
        with self._lock:
            if self._closed or len(self._ids) >= self._attempt_limit:
                raise ContractError('Transport closed or session request limit reached; continue manually.')
            review = prepared.review
            if review.request_id in self._ids or review.nonce in self._nonces:
                raise ContractError('A wire request and nonce can be dispatched only once.')
            config = prepared.profile.value
            credential = None if config['credential_env'] is None else os.environ.get(config['credential_env'])
            if config['credential_env'] is not None and (not isinstance(credential, str) or not credential
                    or len(credential) > 4096 or not credential.isascii()
                    or any(ord(c) < 33 or ord(c) == 127 for c in credential)):
                raise ContractError('Selected credential is missing or invalid; no request was started.')
            if credential and (_contains_credential(json.loads(prepared.context.payload), credential)
                               or _contains_credential(json.loads(prepared.body), credential)
                               or credential in config['endpoint']
                               or credential in unquote(config['endpoint'])):
                raise ContractError('Selected request contains the credential; narrow context or correct connection settings.')
            limits = {key: POLICY[key] for key in ('connect_seconds', 'header_seconds', 'read_seconds', 'total_seconds')}
            packet = json.dumps({'endpoint': config['endpoint'], 'api': config['api'],
                'body': base64.b64encode(prepared.body).decode('ascii'), 'credential': credential,
                'headers': provider_request_headers(prepared.profile),
                **limits},
                separators=(',', ':')).encode('utf-8')
            if len(packet) > MAX_PACKET: raise ContractError('Bounded wire packet required.')
            self._ids.add(review.request_id); self._nonces.add(review.nonce)
            job = ProviderJob(prepared, credential, packet, limits)
            self._jobs.append(job)
            return job

    def close(self):
        with self._lock:
            self._closed = True
            jobs = tuple(self._jobs)
        for job in jobs: job.cancel()
        atexit.unregister(self.close)

    def wait_closed(self, timeout=1):
        deadline = time.monotonic()+timeout
        return all(job.wait_closed(max(0, deadline-time.monotonic())) for job in tuple(self._jobs))
