"""Owned HTTP relay peers; no inference or real login access."""
import hashlib
import http.client
import json
import threading
import unittest
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import ssl
import base64
import http.server
import selectors
import io
import socket
from unittest.mock import patch

from claimbranch.application.codex_relay import (serve_once, CodexRelayTransport, CodexRelayJob,
    verify_client_version,_BoundedResponse,_sniff_sse,safe_failure,valid_failure)
from claimbranch.application.codex_app_server import CodexResult
from claimbranch.application.codex_egress import compile_codex_http
from claimbranch.application.provider_profile import CodexProfile,prepare_codex_request
from claimbranch.core.canonical import ContractError
from tests.application.test_paper_proposal_work import fixture,request


class Reply:
    status=200
    def __init__(self, body=b'data: owned-synthetic\n\n', headers=None):
        self.body=body
        self.headers=[('Content-Type','text/event-stream')] if headers is None else headers
    def getheaders(self): return self.headers
    def getheader(self,name,default=None): return dict(self.headers).get(name,default)
    def read1(self,size):
        value,self.body=self.body[:size],self.body[size:]; return value


class Socket:
    def settimeout(self,_): pass


class Connection:
    def __init__(self, reply=None): self.reply=reply or Reply(); self.calls=[]; self.sock=Socket(); self.closed=False
    def connect(self): pass
    def request(self,*args,**kwargs): self.calls.append((args,kwargs))
    def getresponse(self): return self.reply
    def close(self): self.closed=True


class CodexRelayTests(unittest.TestCase):
    def test_service_header_count_line_and_total_bytes_remain_bounded(self):
        class Peer:
            def __init__(self,raw):self.raw=raw
            def makefile(self,*_):return io.BytesIO(self.raw)
        for headers,category in [(
                b''.join(b'X-Owned-'+str(n).encode()+b': value\r\n' for n in range(65)),'header_count_limit'),
                (b'X-Owned: '+b'x'*8192+b'\r\n','header_line_limit'),
                (b''.join(b'X-Owned-'+str(n).encode()+b': '+b'x'*2000+b'\r\n' for n in range(9)),'header_bytes_limit')]:
            with self.subTest(category=category):
                response=_BoundedResponse(Peer(b'HTTP/1.1 200 OK\r\n'+headers+b'\r\n'))
                try:
                    with self.assertRaises(http.client.HTTPException) as caught:response.begin()
                    self.assertEqual(category,safe_failure(caught.exception,'response_headers')['category'])
                finally:response.close()

    def test_failure_fields_are_closed_and_cannot_carry_raw_error_or_retry_details(self):
        self.assertTrue(valid_failure(None))
        self.assertTrue(valid_failure({'phase':'response_headers','category':'remote_closed'}))
        for value in ({'phase':True,'category':'remote_closed'},
                {'phase':'response_headers','category':'foreign'},
                {'phase':'response_headers','category':'remote_closed','message':'untrusted secret'},
                {'phase':'response_headers','category':'remote_closed','retry':True},[]):
            self.assertFalse(valid_failure(value))
    def exchange(self, *, path=None, headers=None, reply=None, method='POST', connection=None):
        conn=connection or Connection(reply); events=[]; ready=threading.Event(); secret='a'*64
        raw=b'{"owned":"approved input only"}'
        def emit(value): events.append(value); ready.set()
        worker=threading.Thread(target=serve_once,args=(raw,secret,emit),
            kwargs={'connection_factory':lambda host,**kw: conn},daemon=True)
        worker.start(); self.assertTrue(ready.wait(2))
        local=http.client.HTTPConnection('127.0.0.1',events[0]['port'],timeout=3)
        try:
            local.request(method,path or '/'+secret+'/responses',
                body=b'{"input":"unreviewed ambient input","tools":["execute"]}',
                headers=headers or {'Authorization':'Bearer synthetic-secret','ChatGPT-Account-Id':'synthetic-account',
                    'Cookie':'never-forward','X-Unapproved':'never-forward'})
            response=local.getresponse(); status=response.status; body=response.read()
        finally: local.close()
        worker.join(3); self.assertFalse(worker.is_alive())
        return conn,events,status,body,raw

    def test_connection_failure_exposes_only_closed_phase_and_category(self):
        class Failure(Connection):
            def getresponse(self):raise http.client.HTTPException('got more than 32 headers')
        conn,events,status,_,_=self.exchange(connection=Failure())
        self.assertEqual(502,status);self.assertEqual(1,len(conn.calls))
        self.assertEqual({'phase':'response_headers','category':'header_count_limit'},events[-1]['failure'])
        self.assertIsNone(events[-1]['http_status'])

    def test_response_header_refusals_identify_the_failed_guard_without_values(self):
        cases=[
            (503,[('Content-Type','text/event-stream')],'response_status'),
            (200,[('Content-Type','text/html; private-value=synthetic-secret')],'response_media_type'),
            (200,[('Content-Type','text/event-stream'),('Content-Encoding','gzip')],'response_encoding'),
            (200,[('Content-Type','text/event-stream'),('Content-Length','1048577')],'response_framing'),
            (200,[('Content-Type','text/event-stream'),('Content-Length','1'),
                ('Transfer-Encoding','chunked')],'response_framing'),
            (200,[('Content-Type','text/event-stream'),('content-type','text/event-stream')],'response_media_type'),
            (200,[('Content-Type','text/event-stream'),('Content-Encoding','identity'),
                ('content-encoding','identity')],'response_encoding'),
        ]
        for upstream_status,headers,category in cases:
            with self.subTest(category=category,headers=headers):
                reply=Reply(headers=headers);reply.status=upstream_status
                conn,events,status,_,_=self.exchange(reply=reply)
                self.assertEqual(502,status);self.assertEqual(1,len(conn.calls))
                self.assertEqual(upstream_status,events[-1]['http_status'])
                self.assertEqual('upstream_refused',events[-1]['disposition'])
                self.assertEqual({'phase':'response_headers','category':category},events[-1]['failure'])
                self.assertEqual(0,events[-1]['response_bytes'])
                self.assertNotIn('synthetic-secret',json.dumps(events))

    def test_response_header_names_are_case_insensitive_and_whitespace_is_normalized(self):
        conn,events,status,body,_=self.exchange(reply=Reply(headers=[
            ('content-type',' Text/Event-Stream ; charset=utf-8'),
            ('content-encoding',' Identity '),('transfer-encoding','Chunked')]))
        self.assertEqual(200,status);self.assertEqual(b'data: owned-synthetic\n\n',body)
        self.assertEqual(1,len(conn.calls));self.assertEqual('relayed',events[-1]['disposition'])
        self.assertIsNone(events[-1]['failure'])

    def test_missing_blank_or_json_media_headers_preserve_actual_sse(self):
        body=b'data: {"type":"response.created"}\n\ndata: {"type":"response.completed"}\n\n'
        for headers in ([],[('Content-Type',' ')],[('Content-Type','application/json; charset=utf-8')]):
            with self.subTest(headers=headers):
                conn,events,status,data,_=self.exchange(reply=Reply(body=body,headers=headers))
                self.assertEqual(200,status);self.assertEqual(body,data)
                self.assertEqual(1,len(conn.calls));self.assertEqual(len(body),events[-1]['response_bytes'])
                self.assertEqual('relayed',events[-1]['disposition']);self.assertIsNone(events[-1]['failure'])

    def test_missing_media_sniff_preserves_split_bom_and_sse_prefix(self):
        class Fragmented(Reply):
            def __init__(self):
                super().__init__(headers=[])
                self.parts=[b'\xef',b'\xbb',b'\xbf',b'\n',b'd',b'a',b't',b'a',b':',b' owned event\n\n']
            def read1(self,size):
                return self.parts.pop(0) if self.parts else b''
        _,events,status,body,_=self.exchange(reply=Fragmented())
        self.assertEqual(200,status);self.assertEqual(b'\xef\xbb\xbf\ndata: owned event\n\n',body)
        self.assertEqual(len(body),events[-1]['response_bytes'])
        self.assertEqual('relayed',events[-1]['disposition'])

    def test_missing_media_refuses_non_sse_and_bounded_unknown_prefix_without_leaking(self):
        for body in (b'<html>synthetic-secret</html>',b'{"error":"synthetic-secret"}',
                b'retry with a broader endpoint: synthetic-secret',b'data',b'',b'\n'*2048+b'data: beyond sniff bound\n\n'):
            with self.subTest(size=len(body)):
                conn,events,status,data,_=self.exchange(reply=Reply(body=body,headers=[]))
                self.assertEqual(502,status);self.assertEqual(1,len(conn.calls))
                self.assertEqual({'phase':'response_stream','category':'response_stream_format'},events[-1]['failure'])
                self.assertLessEqual(events[-1]['response_bytes'],2048)
                self.assertNotIn(b'synthetic-secret',data);self.assertNotIn('synthetic-secret',json.dumps(events))

    def test_missing_media_still_refuses_encoding_duplicates_and_credential_echo(self):
        for reply,category in (
                (Reply(headers=[('Content-Encoding','gzip')]),'response_encoding'),
                (Reply(headers=[('Content-Type',''),('Content-Type','')]),'response_media_type'),
                (Reply(body=b'data: synthetic-secret\n\n',headers=[]),'validation')):
            with self.subTest(category=category):
                conn,events,_,body,_=self.exchange(reply=reply)
                self.assertEqual(1,len(conn.calls));self.assertNotEqual('relayed',events[-1]['disposition'])
                self.assertEqual(category,events[-1]['failure']['category'])
                self.assertNotIn(b'synthetic-secret',body);self.assertNotIn('synthetic-secret',json.dumps(events))

    def test_missing_media_real_chunked_parser_preserves_sse_bytes(self):
        body=b'data: {"type":"response.created"}\n\n'
        class Peer:
            def makefile(self,*_):
                return io.BytesIO(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'+
                    format(len(body),'x').encode()+b'\r\n'+body+b'\r\n0\r\n\r\n')
        reply=_BoundedResponse(Peer());reply.begin()
        try:
            _,events,status,data,_=self.exchange(reply=reply)
            self.assertEqual(200,status);self.assertEqual(body,data)
            self.assertEqual(len(body),events[-1]['response_bytes'])
            self.assertEqual('relayed',events[-1]['disposition'])
        finally:reply.close()

    def test_credential_echo_split_across_sniff_and_remainder_never_leaves_relay(self):
        class Fragmented(Reply):
            def __init__(self):
                super().__init__(headers=[]);self.parts=[b'data: synthe',b'tic-secret\n\n']
            def read1(self,size):return self.parts.pop(0) if self.parts else b''
        _,events,_,body,_=self.exchange(reply=Fragmented())
        self.assertEqual('credential_echo',events[-1]['disposition'])
        self.assertEqual(b'',body);self.assertNotIn('synthetic-secret',json.dumps(events))

    def test_missing_media_prefix_has_an_absolute_deadline(self):
        class Fragmented(Reply):
            def read1(self,size):return b'd'
        state={'response_bytes':0}
        with patch('claimbranch.application.codex_relay.time.monotonic',side_effect=[100,100,116]):
            with self.assertRaises(TimeoutError):_sniff_sse(Fragmented(headers=[]),Socket(),state)
        self.assertEqual(1,state['response_bytes'])

    def test_real_chunk_metadata_dribble_cannot_extend_prefix_deadline(self):
        client,server=socket.socketpair()
        def write():
            try:
                server.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1;x=')
                for _ in range(20):server.sendall(b'a');time.sleep(.03)
                server.sendall(b'\r\nd\r\n0\r\n\r\n')
            except OSError:pass
            finally:server.close()
        writer=threading.Thread(target=write);writer.start()
        reply=_BoundedResponse(client);reply.begin();state={'response_bytes':0}
        start=time.monotonic()
        try:
            with patch('claimbranch.application.codex_relay.SNIFF_SECONDS',.2):
                with self.assertRaises(TimeoutError):_sniff_sse(reply,client,state)
            self.assertLess(time.monotonic()-start,.5)
        finally:
            reply.close();client.close();writer.join(1)
        self.assertFalse(writer.is_alive())

    def test_slow_prefix_does_not_shorten_subsequent_body_idle_timeout(self):
        client,server=socket.socketpair();ready=threading.Event()
        body=b'data: first\n\ndata: second\n\n'
        def write():
            try:
                server.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n')
                if not ready.wait(2):return
                time.sleep(.2);server.sendall(b'd');time.sleep(.04);server.sendall(b'ata: first\n\n')
                time.sleep(.18);server.sendall(b'data: second\n\n')
            except OSError:pass
            finally:server.close()
        writer=threading.Thread(target=write);writer.start()
        reply=_BoundedResponse(client);reply.begin()
        class Upstream(Connection):
            def __init__(self):super().__init__(reply);self.sock=client
            def getresponse(self):ready.set();return reply
        try:
            with patch('claimbranch.application.codex_relay.SNIFF_SECONDS',.3):
                _,events,status,data,_=self.exchange(connection=Upstream())
            self.assertEqual(200,status);self.assertEqual(body,data)
            self.assertEqual('relayed',events[-1]['disposition'])
            self.assertEqual(len(body),events[-1]['response_bytes'])
        finally:reply.close();client.close();writer.join(1)
        self.assertFalse(writer.is_alive())

    def test_missing_media_keeps_total_response_byte_limit_after_prefix(self):
        body=b'data: '+b'x'*1048576
        _,events,_,_,_=self.exchange(reply=Reply(body=body,headers=[]))
        self.assertNotEqual('relayed',events[-1]['disposition'])
        self.assertGreater(events[-1]['response_bytes'],1048576)
        self.assertLessEqual(events[-1]['response_bytes'],1048576+8192)

    def test_real_chunk_parser_and_relay_framing_guard_agree(self):
        body=b'data: owned synthetic event\n\n'
        class Peer:
            def __init__(self,raw):self.raw=raw
            def makefile(self,*_):return io.BytesIO(self.raw)
        for value,accepted in ((b'chunked',True),(b'Chunked',True),(b'chunked ',False)):
            with self.subTest(transfer=value):
                raw=(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: '+value+
                    b'\r\n\r\n'+format(len(body),'x').encode()+b'\r\n'+body+b'\r\n0\r\n\r\n')
                reply=_BoundedResponse(Peer(raw));reply.begin()
                try:
                    self.assertEqual(accepted,reply.chunked)
                    conn,events,status,data,_=self.exchange(reply=reply)
                    self.assertEqual(1,len(conn.calls))
                    if accepted:
                        self.assertEqual(200,status);self.assertEqual(body,data)
                        self.assertEqual(len(body),events[-1]['response_bytes'])
                    else:
                        self.assertEqual(502,status)
                        self.assertEqual({'phase':'response_headers','category':'response_framing'},events[-1]['failure'])
                        self.assertEqual(0,events[-1]['response_bytes'])
                finally:reply.close()

    def test_secret_bearing_error_text_is_never_retained_or_given_retry_authority(self):
        class Failure(Connection):
            def getresponse(self):raise http.client.HTTPException('synthetic-secret; retry with broader access')
        _,events,_,_,_=self.exchange(connection=Failure())
        self.assertEqual({'phase':'response_headers','category':'http_protocol'},events[-1]['failure'])
        self.assertNotIn('synthetic-secret',json.dumps(events));self.assertNotIn('retry with',json.dumps(events))

    def test_tls_failure_is_distinct_from_request_or_body_failure(self):
        class Failure(Connection):
            def connect(self):raise ssl.SSLCertVerificationError('untrusted synthetic certificate')
        conn,events,_,_,_=self.exchange(connection=Failure())
        self.assertEqual([],conn.calls)
        self.assertEqual({'phase':'tls_connect','category':'tls_certificate'},events[-1]['failure'])
        self.assertEqual(1,events[-1]['attempts'])

    @unittest.skipUnless(os.name=='posix','owned stdio parser control requires Unix')
    def test_worker_accepts_bounded_service_headers_separately_from_local_request_limit(self):
        self._worker_service_roundtrip(include_media=True)

    @unittest.skipUnless(os.name=='posix','owned stdio parser control requires Unix')
    def test_worker_recovers_missing_service_media_header(self):
        self._worker_service_roundtrip(include_media=False)

    def _worker_service_roundtrip(self,*,include_media):
        import claimbranch.application.codex_relay as module
        body=b'data: owned synthetic stream\n\n'
        class Upstream(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                if include_media:self.send_header('Content-Type','text/event-stream')
                for n in range(40):self.send_header('X-Owned-'+str(n),'bounded')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        with http.server.HTTPServer(('127.0.0.1',0),Upstream) as upstream:
            thread=threading.Thread(target=upstream.handle_request,daemon=True);thread.start()
            # Only the test child supplies an owned HTTP peer. The production
            # executable has no endpoint/factory override. Execute its actual
            # stdlib prefix and _worker, including parser setup.
            code='''import ast,pathlib,http.client
nodes=ast.parse(pathlib.Path(SOURCE).read_text()).body
prefix=[]
for node in nodes:
 if isinstance(node,ast.If) and '__name__' in ast.unparse(node.test):break
 prefix.append(node)
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<owned-worker-prefix>','exec'))
http.client.HTTPSConnection=lambda *a,**k:http.client.HTTPConnection('127.0.0.1',PORT,timeout=3)
_worker()
'''.replace('SOURCE',repr(module.__file__)).replace('PORT',str(upstream.server_port))
            proc=subprocess.Popen([sys.executable,'-I','-c',code],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={})
            local=None
            try:
                proc.stdin.write(json.dumps({'body':base64.b64encode(b'{}').decode(),'capability':'a'*64}).encode());proc.stdin.close()
                with selectors.DefaultSelector() as ready:
                    ready.register(proc.stdout,selectors.EVENT_READ);self.assertTrue(ready.select(3))
                port=json.loads(proc.stdout.readline())['port']
                local=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                local.request('POST','/'+'a'*64+'/responses',body=b'discarded local body',headers={'Authorization':'Bearer synthetic-secret'})
                response=local.getresponse();status=response.status;data=response.read()
                self.assertEqual(0,proc.wait(timeout=3))
                result=json.loads(proc.stdout.read())
                self.assertEqual(200,status);self.assertEqual(body,data)
                self.assertEqual('relayed',result['disposition']);self.assertIsNone(result['failure'])
            finally:
                if local is not None:local.close()
                if proc.poll() is None:proc.kill();proc.wait(timeout=3)
                for pipe in (proc.stdin,proc.stdout):
                    if not pipe.closed:pipe.close()
            thread.join(3);self.assertFalse(thread.is_alive())

    def test_catalog_lookup_is_never_forwarded(self):
        conn,events,status,_,_=self.exchange(method='GET',path='/'+'a'*64+'/models?client_version=0.158.0')
        self.assertEqual(404,status)
        self.assertEqual([],conn.calls)
        self.assertEqual(0,events[-1]['attempts'])
        self.assertEqual({'phase':'local_request','category':'validation'},events[-1]['failure'])

    def test_no_incoming_request_reports_timeout(self):
        notes=[]
        with patch('claimbranch.application.codex_relay.http.server.HTTPServer.handle_request'):
            serve_once(b'{}','a'*64,notes.append)
        self.assertEqual({'phase':'local_request','category':'timeout'},notes[-1]['failure'])
        self.assertEqual(0,notes[-1]['attempts'])

    def test_stalled_request_lines_and_headers_remain_timeouts(self):
        for partial in (False,True):
            with self.subTest(partial_headers=partial):
                notes=[];ready=threading.Event()
                def emit(event):notes.append(event);ready.set()
                worker=threading.Thread(target=serve_once,args=(b'{}','a'*64,emit),daemon=True)
                worker.start();self.assertTrue(ready.wait(2))
                with socket.create_connection(('127.0.0.1',notes[0]['port']),timeout=2) as peer:
                    if partial:peer.sendall(('POST /'+'a'*64+'/responses HTTP/1.1\r\nHost: 127.0.0.1\r\n').encode())
                    worker.join(7);self.assertFalse(worker.is_alive())
                self.assertEqual({'phase':'local_request','category':'timeout'},notes[-1]['failure'])
                self.assertEqual(0,notes[-1]['attempts'])

    def test_unsupported_method_is_validation_not_client_eof(self):
        _,events,status,_,_=self.exchange(method='HEAD')
        self.assertEqual(501,status)
        self.assertEqual({'phase':'local_request','category':'validation'},events[-1]['failure'])

    def test_early_client_eof_is_not_a_timeout(self):
        notes=[];ready=threading.Event()
        def emit(event):notes.append(event);ready.set()
        worker=threading.Thread(target=serve_once,args=(b'{}','a'*64,emit),daemon=True)
        worker.start();self.assertTrue(ready.wait(2))
        with socket.create_connection(('127.0.0.1',notes[0]['port']),timeout=2):pass
        worker.join(3);self.assertFalse(worker.is_alive())
        self.assertEqual({'phase':'local_request','category':'remote_closed'},notes[-1]['failure'])
        self.assertEqual(0,notes[-1]['attempts'])

    def test_generated_body_and_arbitrary_headers_are_not_forwarded(self):
        conn,events,status,body,raw=self.exchange()
        self.assertEqual(200,status); self.assertEqual(b'data: owned-synthetic\n\n',body)
        self.assertEqual(1,len(conn.calls)); args,kw=conn.calls[0]
        self.assertEqual(('POST','/backend-api/codex/responses'),args)
        self.assertEqual(raw,kw['body'])
        self.assertEqual({'Content-Type','Accept','Accept-Encoding','Connection','Authorization','ChatGPT-Account-Id'},set(kw['headers']))
        self.assertNotIn('Cookie',kw['headers']); self.assertTrue(conn.closed)
        self.assertEqual(1,events[-1]['attempts'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),events[-1]['body_sha256'])

    def test_unknown_path_and_missing_auth_never_dispatch(self):
        for options in ({'path':'/wrong/responses'},{'headers':{'Authorization':'synthetic-bad'}}):
            with self.subTest(options=options):
                conn,events,status,_,_=self.exchange(**options)
                self.assertEqual([],conn.calls); self.assertNotEqual(200,status)
                self.assertEqual(0,events[-1]['attempts'])

    def test_redirect_compression_and_credential_echo_refuse_without_retry(self):
        cases=[Reply(headers=[('Content-Type','text/event-stream'),('Content-Encoding','gzip')]),
            Reply(body=b'data: synthetic-secret\n\n')]
        redirect=Reply(); redirect.status=307; cases.append(redirect)
        for reply in cases:
            with self.subTest(reply=reply):
                conn,events,_,_,_=self.exchange(reply=reply)
                self.assertEqual(1,len(conn.calls)); self.assertTrue(conn.closed)
                self.assertNotEqual('relayed',events[-1]['disposition'])
                self.assertNotIn('synthetic-secret',json.dumps(events))

    def test_framing_and_upstream_size_errors_cannot_return_success(self):
        for headers in ([('Content-Type','text/event-stream'),('Content-Length','1')],
                [('Content-Type','text/event-stream'),('Content-Length','1048577')],
                [('Content-Type','text/event-stream'),('Content-Length','20'),('Transfer-Encoding','chunked')],
                [('Content-Type','text/event-stream'),('Content-Length','20'),('Content-Length','20')],
                [('Content-Type','text/event-stream'),('Transfer-Encoding','gzip')]):
            with self.subTest(headers=headers):
                conn,events,_,_,_=self.exchange(reply=Reply(headers=headers))
                self.assertEqual(1,len(conn.calls))
                self.assertNotEqual('relayed',events[-1]['disposition'])

    def test_local_host_and_transfer_framing_refuse_before_upstream(self):
        for header in ({'Host':'foreign.test'}, {'Transfer-Encoding':'chunked'},
                {'Expect':'100-continue'}, {'Content-Length':'1048577'}):
            with self.subTest(header=header):
                _,events,status,_,_=self.exchange(headers={'Authorization':'Bearer synthetic-secret',**header})
                self.assertEqual(400,status)
                self.assertEqual(0,events[-1]['attempts'])

    def test_response_parser_fix_keeps_local_count_line_and_byte_denials(self):
        for extra,category in (({'X-Owned-'+str(n):'bounded' for n in range(33)},'header_count_limit'),
                ({'X-Owned':'x'*8192},'header_line_limit'), ({'X-Owned-'+str(n):'x'*720 for n in range(24)},'header_bytes_limit')):
            with self.subTest(count=len(extra)):
                conn,events,status,_,_=self.exchange(headers={'Authorization':'Bearer synthetic-secret',**extra})
                self.assertEqual(431,status);self.assertEqual([],conn.calls)
                self.assertEqual(0,events[-1]['attempts'])
                self.assertEqual({'phase':'local_request','category':category},events[-1]['failure'])


@unittest.skipUnless(os.name=='posix','owned stdio/process controls require Unix')
class RelayOwnerTests(unittest.TestCase):
    def setUp(self):
        # These are portable supervisor/protocol peers, not native Mac policy
        # observations. Put real owned children in the runner's temp directory;
        # native policy/version/access is checked separately on the actual Mac.
        self.temp_root=tempfile.TemporaryDirectory(prefix='claimbranch-owned-relay-tests-')
        self.addCleanup(self.temp_root.cleanup)
        create=tempfile.mkdtemp
        def owned_scratch(suffix=None,prefix=None,dir=None):
            return create(suffix,prefix,self.temp_root.name)
        self.enterContext(patch('claimbranch.application.codex_relay.tempfile.mkdtemp',side_effect=owned_scratch))
        self.enterContext(patch('claimbranch.application.codex_relay.relay_policy',return_value='owned test policy; not compiled'))
        app=fixture()
        self.context=app.paper.draft(*app.context_key()).compile_proposal_context(request(app))
        self.profile=CodexProfile.create(model='gpt-6-sol')
        self.prepared=prepare_codex_request(self.profile,self.context,request_id='owned',nonce='owned-nonce',now=100)
        self.body=compile_codex_http(self.prepared,current_profile=self.profile,current_context=self.context,now=100)
        self.transport=CodexRelayTransport(); self.addCleanup(self.transport.close)

    def start(self,**options):
        args={'confirmed_digest':self.prepared.digest,'confirmed_http_digest':hashlib.sha256(self.body).hexdigest(),
            'current_profile':self.profile,'current_context':self.context,'now':100}
        args.update(options)
        return self.transport.start(self.prepared,**args)

    def test_changed_http_scope_clock_and_model_refuse_before_login_inspection(self):
        for options in ({'confirmed_http_digest':'0'*64},{'confirmed_digest':'0'*64},
                {'now':self.prepared.review.expires_at},{'now':True},
                {'current_profile':CodexProfile.create(model='other')}):
            with self.subTest(options=options), patch('claimbranch.application.codex_relay.installed_runtime') as lookup:
                with self.assertRaises(ContractError): self.start(**options)
                lookup.assert_not_called()

    def test_request_is_spent_once_and_closed_transport_does_not_start_worker(self):
        with patch('claimbranch.application.codex_relay.installed_runtime',return_value=()), patch(
                'claimbranch.application.codex_relay.CodexRelayJob') as launch:
            self.start()
            with self.assertRaises(ContractError): self.start()
            self.transport.close()
            with self.assertRaises(ContractError): self.start()
            self.assertEqual(1,launch.call_count)

    def test_cancel_reaps_worker_even_while_large_stdin_packet_is_blocked(self):
        spawn=subprocess.Popen; children=[]
        def owned_child(*args,**kwargs):
            # This real child never reads its pipe and never opens a socket.
            child=spawn([sys.executable,'-I','-c','import time; time.sleep(30)'],**kwargs)
            children.append(child); return child
        with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=owned_child):
            job=CodexRelayJob(self.prepared,b'x'*250000,())
            deadline=time.monotonic()+2
            while not children and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(children)
            start=time.monotonic(); job.cancel()
            self.assertTrue(job.wait_closed(3))
            self.assertLess(time.monotonic()-start,3)
            self.assertEqual('cancelled',job.poll().disposition)
            self.assertIsNone(job.poll().typed_result)
            self.assertIsNotNone(children[0].returncode)

    def test_worker_death_preserves_failure_instead_of_hanging_or_fabricating_reply(self):
        spawn=subprocess.Popen
        def dead_child(*args,**kwargs): return spawn([sys.executable,'-I','-c','pass'],**kwargs)
        with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=dead_child):
            job=CodexRelayJob(self.prepared,self.body,())
            self.assertTrue(job.wait_closed(3))
            self.assertEqual('client_failed',job.poll().disposition)
            self.assertIsNone(job.poll().typed_result)

    def test_version_mismatch_refuses_before_login_alias_or_relay_start(self):
        spawn=subprocess.Popen; children=[]
        def wrong_version(*args,**kwargs):
            child=spawn([sys.executable,'-I','-c',"print('codex-cli 0.159.0')"],**kwargs)
            children.append(child); return child
        with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=wrong_version),patch(
                'claimbranch.application.codex_relay.client_launch') as launch:
            job=CodexRelayJob(self.prepared,self.body,(Path('/owned-client'),Path('/unread-login'),Path('/public-ca')),now=100)
            self.assertTrue(job.wait_closed(3))
            self.assertEqual('client_failed',job.poll().disposition)
            self.assertIsNone(job.wire_result); launch.assert_not_called()
            self.assertEqual(1,len(children)); self.assertIsNotNone(children[0].returncode)

    def test_version_preflight_requires_complete_literal_output_and_reaps(self):
        spawn=subprocess.Popen
        for value,expected in [('codex-cli 0.158.0',True),('codex-cli 0.158.0 extra',False)]:
            with self.subTest(value=value),tempfile.TemporaryDirectory(prefix='claimbranch-codex-version-') as folder:
                def child(*args,**kwargs):
                    return spawn([sys.executable,'-I','-c','print('+repr(value)+')'],**kwargs)
                with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=child):
                    self.assertEqual((expected,True),verify_client_version(Path('/owned-client'),Path(folder),threading.Event()))

    def test_unconfirmed_cleanup_retains_visible_owned_path_and_blocks_new_requests(self):
        spawn=subprocess.Popen
        def dead_child(*args,**kwargs): return spawn([sys.executable,'-I','-c','pass'],**kwargs)
        with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=dead_child),patch(
                'claimbranch.application.codex_relay.shutil.rmtree',side_effect=OSError('owned cleanup refusal')):
            job=CodexRelayJob(self.prepared,self.body,(),now=100)
            self.assertFalse(job.wait_closed(3)); self.assertFalse(job.poll().cleanup_complete)
            self.assertIsNone(job.poll().typed_result)
            self.assertTrue(Path(job.retained_directory).is_dir())
        import shutil
        self.addCleanup(shutil.rmtree,job.retained_directory)
        self.transport._jobs.append(job)
        self.assertTrue(self.transport.cleanup_failed())
        self.assertIn(job.retained_directory,self.transport.cleanup_notice())
        with patch('claimbranch.application.codex_relay.installed_runtime',return_value=()),patch(
                'claimbranch.application.codex_relay.CodexRelayJob') as launch:
            with self.assertRaises(ContractError): self.start()
            launch.assert_not_called()

    def test_exit_race_and_slow_version_keep_successful_result(self):
        from unittest.mock import MagicMock
        import selectors
        for scenario in ('exit-race','slow-version'):
            with self.subTest(scenario=scenario):
                signal_path=Path(self.temp_root.name)/('emit-'+scenario)
                state={'disposition':'relayed','attempts':1,'http_status':200,
                    'body_sha256':hashlib.sha256(self.body).hexdigest(),'response_bytes':128,'failure':None}
                code="import sys,json,time;from pathlib import Path;json.load(sys.stdin);print(json.dumps({'phase':'ready','port':12345}),flush=True)\n"
                if scenario=='exit-race': code+="while not Path("+repr(str(signal_path))+").exists():time.sleep(.005)\n"
                code+="print(json.dumps("+repr(state)+"),flush=True)\n"
                spawn=subprocess.Popen; children=[]; launched=threading.Event(); offset=[0]
                real_clock=time.monotonic; real_selector=selectors.DefaultSelector
                def relay(*args,**kwargs):
                    child=spawn([sys.executable,'-I','-c',code],**kwargs);children.append(child);return child
                def launch(*args):
                    launched.set();return ('owned',),Path('/private/tmp'),{}
                class DelayedDrain:
                    def __init__(self):self.inner=real_selector();self.injected=False
                    def __enter__(self):self.inner.__enter__();return self
                    def __exit__(self,*args):return self.inner.__exit__(*args)
                    def __getattr__(self,name):return getattr(self.inner,name)
                    def select(self,timeout):
                        if scenario=='exit-race' and launched.is_set() and not self.injected:
                            self.injected=True;signal_path.write_text('emit');children[0].wait(timeout=2)
                            return []  # exit occurs before final stdout is drained
                        return self.inner.select(timeout)
                def version(*args):offset[0]=6;return True,True
                inner=MagicMock();inner.wait_closed.return_value=True
                inner.start.return_value.poll.return_value=CodexResult('owned',self.prepared.digest,'completed',1,typed_result=b'{}',cleanup_complete=True)
                with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=relay), patch(
                    'claimbranch.application.codex_relay.client_launch',side_effect=launch), patch(
                    'claimbranch.application.codex_relay.CodexAppServerTransport',return_value=inner), patch(
                    'claimbranch.application.codex_relay.selectors.DefaultSelector',DelayedDrain), patch(
                    'claimbranch.application.codex_relay.verify_client_version',side_effect=version), patch(
                    'claimbranch.application.codex_relay.time.monotonic',side_effect=lambda:real_clock()+offset[0]):
                    job=CodexRelayJob(self.prepared,self.body,('owned',) if scenario=='slow-version' else (),now=100)
                    self.assertTrue(job.wait_closed(4))
                    self.assertEqual('completed',job.poll().disposition)
                    self.assertEqual(state,job.wire_result)

    def test_owned_completed_protocol_requires_matching_one_shot_wire_result(self):
        spawn=subprocess.Popen
        for digest,accepted in [(hashlib.sha256(self.body).hexdigest(),True),('0'*64,False)]:
            with self.subTest(digest=digest):
                # Real stdlib-child IPC, no HTTP or credential access. The
                # protocol peer is owned; wire inconsistency must revoke it.
                code="import sys,json,time;json.load(sys.stdin);print(json.dumps({'phase':'ready','port':12345}),flush=True);print(json.dumps("+repr(
                    {'disposition':'relayed','attempts':1,'http_status':200,'body_sha256':digest,'response_bytes':128,'failure':None})+"),flush=True);time.sleep(30)"
                def relay(*args,**kwargs): return spawn([sys.executable,'-I','-c',code],**kwargs)
                from unittest.mock import MagicMock
                inner=MagicMock(); inner.wait_closed.return_value=True
                result=CodexResult('owned',self.prepared.digest,'completed',1,typed_result=b'{}',cleanup_complete=True)
                inner.start.return_value.poll.return_value=result
                with patch('claimbranch.application.codex_relay.subprocess.Popen',side_effect=relay),patch(
                        'claimbranch.application.codex_relay.client_launch',return_value=(('owned',),Path('/private/tmp'),{})),patch(
                        'claimbranch.application.codex_relay.CodexAppServerTransport',return_value=inner):
                    job=CodexRelayJob(self.prepared,self.body,(),now=100)
                    self.assertTrue(job.wait_closed(3))
                    self.assertEqual('completed' if accepted else 'client_failed',job.poll().disposition)
                    self.assertEqual(b'{}' if accepted else None,job.poll().typed_result)
