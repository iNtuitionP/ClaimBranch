"""One-shot exact HTTP egress, with the login file consumed only by the CLI.

The trusted stdlib child sees one frozen body and one opaque authentication
header. It receives no research handle, profile file or login-file path.
The Codex child can reach only this per-request loopback peer. Public support
still requires actual access/egress and connected-return validation.
"""
import base64
import hashlib
import http.client
import http.server
import json
import re
import socket
import ssl
import sys
import threading
import time

MAX_PACKET=400000
MAX_GENERATED_BODY=1048576
MAX_STREAM=1048576
MAX_SNIFF=2048
SNIFF_SECONDS=15
HOST='chatgpt.com'
PATH='/backend-api/codex/responses'
FAILURE_PHASES=('local_request','tls_connect','send_request','response_headers','response_stream')
FAILURE_CATEGORIES=('tls_certificate','tls_protocol','timeout','remote_closed','header_count_limit',
    'header_line_limit','header_bytes_limit','http_status_line','http_protocol','connection','validation','internal_error',
    'response_status','response_framing','response_media_type','response_encoding','response_stream_format')


class _ResponseRefused(ValueError):
    """Only a fixed response guard name, never a service header value."""
    def __init__(self,category):
        if category not in FAILURE_CATEGORIES:raise ValueError('Unknown response guard')
        self.category=category
        super().__init__('Unsupported response')


def _sniff_sse(reply,wire_socket,state):
    """Inspect a bounded prefix; preserve every byte for the same stream.

    Native Codex can omit its media header or label real SSE as JSON. Header
    compatibility grants no proposal authority; the owned CLI/typed checks
    still validate the entire response. Never publish inspected bytes here.
    """
    prefix=b'';deadline=time.monotonic()+SNIFF_SECONDS;expired=threading.Event()
    def expire():
        expired.set()
        try:wire_socket.shutdown(socket.SHUT_RDWR)
        except OSError:pass
    # HTTPResponse.read1 can perform several recv calls while decoding chunk
    # metadata. An idle socket timeout alone cannot bound that whole operation.
    watchdog=threading.Timer(SNIFF_SECONDS,expire);watchdog.daemon=True;watchdog.start()
    try:
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0 or expired.is_set():raise TimeoutError('Stream-prefix deadline')
            probe=prefix.removeprefix(b'\xef\xbb\xbf').lstrip(b'\r\n')
            if re.match(rb'(?::|(?:data|event|id|retry)(?::|\r|\n))',probe):return prefix
            if probe.startswith((b'<',b'{',b'[')) or len(prefix)>=MAX_SNIFF:
                raise _ResponseRefused('response_stream_format')
            # The watchdog bounds sniffing without shortening the body's idle
            # timeout or touching a socket already closed by HTTPResponse.
            try:part=reply.read1(MAX_SNIFF-len(prefix))
            except Exception:
                if expired.is_set():raise TimeoutError('Stream-prefix deadline') from None
                raise
            if expired.is_set():raise TimeoutError('Stream-prefix deadline')
            if not part:raise _ResponseRefused('response_stream_format')
            state['response_bytes']+=len(part)
            prefix+=part
    finally:
        watchdog.cancel();watchdog.join(.25)
        # Expiry may race with the last successful prefix check. Do not hand
        # off a socket already closed, or still owned by a pending watchdog.
        if watchdog.is_alive() or expired.is_set():
            raise TimeoutError('Stream-prefix deadline')


class _BoundedHeaders:
    """Per-parser wire bounds, without changing shared HTTP module globals."""
    def __init__(self,stream,limit,*,status_first=False):
        self.stream,self.limit=stream,limit
        self.count=self.size=0;self.status_first=status_first
        self.failure=None;self.phase='response_headers' if status_first else 'local_request'
    def refuse(self,error):
        self.failure=safe_failure(error,self.phase)
        raise error
    def readline(self,size=-1):
        line=self.stream.readline(min(8193,size) if size>=0 else 8193)
        if len(line)>8192:self.refuse(http.client.LineTooLong('header line'))
        self.size+=len(line)
        if self.size>16384:self.refuse(http.client.HTTPException('header bytes exceed limit'))
        if self.status_first:self.status_first=False
        elif line not in (b'\r\n',b'\n',b''):
            self.count+=1
            if self.count>self.limit:self.refuse(http.client.HTTPException('got more than '+str(self.limit)+' headers'))
        return line
    def __getattr__(self,name):return getattr(self.stream,name)


class _BoundedResponse(http.client.HTTPResponse):
    def begin(self):
        raw=self.fp
        self.fp=_BoundedHeaders(raw,64,status_first=True)
        try:super().begin()
        finally:self.fp=raw


def safe_failure(error, phase):
    """Ephemeral category only; never retain exception text, headers or paths."""
    if isinstance(error,_ResponseRefused) and error.category in FAILURE_CATEGORIES: category=error.category
    elif isinstance(error,ssl.SSLCertVerificationError): category='tls_certificate'
    elif isinstance(error,ssl.SSLError): category='tls_protocol'
    elif isinstance(error,TimeoutError): category='timeout'
    elif isinstance(error,http.client.RemoteDisconnected): category='remote_closed'
    elif isinstance(error,http.client.LineTooLong): category='header_line_limit'
    elif isinstance(error,http.client.BadStatusLine): category='http_status_line'
    elif isinstance(error,http.client.HTTPException):
        category=('header_count_limit' if re.fullmatch(r'got more than [0-9]{1,4} headers',str(error)) else
            'header_bytes_limit' if str(error)=='header bytes exceed limit' else 'http_protocol')
    elif isinstance(error,OSError): category='connection'
    elif isinstance(error,(ValueError,UnicodeError)): category='validation'
    else: category='internal_error'
    return {'phase':phase,'category':category}


def valid_failure(value):
    return value is None or (type(value) is dict and set(value)=={'phase','category'}
        and type(value['phase']) is str and value['phase'] in FAILURE_PHASES
        and type(value['category']) is str and value['category'] in FAILURE_CATEGORIES)


def serve_once(body, capability, emit, *, connection_factory=None, observer=None):
    """Internal owned-peer seam; production worker supplies no override."""
    if type(body) is not bytes or len(body)>262144 or not re.fullmatch('[0-9a-f]{64}',capability):
        raise ValueError('Bounded frozen request required')
    state={'disposition':'refused','attempts':0,'http_status':None,
        'body_sha256':hashlib.sha256(body).hexdigest(),'response_bytes':0,'failure':None}
    factory=connection_factory or http.client.HTTPSConnection
    connected=False
    class RequestReader:
        def __init__(self,stream):self.stream=stream
        def readline(self,size=-1):
            try:line=self.stream.readline(size)
            except Exception as error:
                state['failure']=safe_failure(error,'local_request')
                raise
            if not line:state['failure']={'phase':'local_request','category':'remote_closed'}
            return line
        def __getattr__(self,name):return getattr(self.stream,name)
    class Peer(http.server.BaseHTTPRequestHandler):
        protocol_version='HTTP/1.0'
        def log_message(self,*_): pass
        def setup(self):
            nonlocal connected
            connected=True
            super().setup(); self.connection.settimeout(5)
            self.rfile=RequestReader(self.rfile)
        def send_error(self,code,message=None,explain=None):
            if 400<=code<=599 and state['attempts']==0 and state['failure'] is None:
                state['failure']={'phase':'local_request','category':'validation'}
            return super().send_error(code,message,explain)
        def parse_request(self):
            raw=self.rfile;reader=_BoundedHeaders(raw,32);self.rfile=reader
            try:
                parsed=super().parse_request()
                if not parsed:state['failure']=reader.failure or {'phase':'local_request','category':'validation'}
                return parsed
            finally:self.rfile=raw
        def do_POST(self):
            upstream=None; started=False; phase='local_request'
            try:
                if observer is not None:
                    observer({'method':self.command,'path':self.path.replace(capability,'<capability>'),
                        'header_names':sorted({k.lower() for k in self.headers}),
                        'bearer_present':self.headers.get('Authorization','').startswith('Bearer ')})
                names={k.lower() for k in self.headers}
                if (self.path!='/'+capability+'/responses'
                    or self.headers.get_all('Host')!=['127.0.0.1:'+str(self.server.server_port)]
                    or sum(len(k)+len(v) for k,v in self.headers.items())>16384
                    or any(len(self.headers.get_all(k))!=1 for k in names)
                    or 'transfer-encoding' in names or 'expect' in names):
                    raise ValueError('Invalid local request')
                length=self.headers.get('Content-Length','')
                auth=self.headers.get('Authorization','')
                account=self.headers.get('ChatGPT-Account-Id')
                if (not length.isascii() or not length.isdigit() or len(length)>7
                    or not 0<int(length)<=MAX_GENERATED_BODY
                    or not auth.startswith('Bearer ') or not 1<=len(auth[7:])<=16384
                    or any(not 33<=ord(c)<=126 for c in auth[7:])
                    or account is not None and (not 1<=len(account)<=256
                        or any(not 33<=ord(c)<=126 for c in account))):
                    raise ValueError('Invalid local framing or authentication')
                # Consume and discard the generated wrapper. Never parse, log,
                # hash for authority, forward or save its messages/tools/env.
                remaining=int(length)
                while remaining:
                    part=self.rfile.read(min(8192,remaining))
                    if not part: raise ValueError('Incomplete local request')
                    remaining-=len(part)
                headers={'Content-Type':'application/json','Accept':'text/event-stream',
                    'Accept-Encoding':'identity','Connection':'close','Authorization':auth}
                if account is not None: headers['ChatGPT-Account-Id']=account
                state['attempts']=1
                phase='tls_connect'
                upstream=factory(HOST,timeout=5,context=ssl.create_default_context())
                upstream.response_class=_BoundedResponse
                upstream.connect(); wire_socket=upstream.sock; wire_socket.settimeout(45)
                phase='send_request'
                upstream.request('POST',PATH,body=body,headers=headers)
                phase='response_headers'
                reply=upstream.getresponse(); state['http_status']=reply.status
                fields=reply.getheaders()
                lengths=[v for k,v in fields if k.lower()=='content-length']
                transfers=[v for k,v in fields if k.lower()=='transfer-encoding']
                media=[v for k,v in fields if k.lower()=='content-type']
                encodings=[v for k,v in fields if k.lower()=='content-encoding']
                media_type=media[0].split(';')[0].strip().lower() if len(media)==1 else ''
                refusal=None
                if reply.status!=200:refusal='response_status'
                elif sum(len(k)+len(v) for k,v in fields)>16384:refusal='header_bytes_limit'
                elif (len(lengths)>1 or len(transfers)>1 or lengths and transfers
                    # Match HTTPResponse.begin's actual chunk decoder decision.
                    # It does not strip trailing whitespace from this token.
                    or transfers and transfers[0].lower()!='chunked'
                    or lengths and (not lengths[0].isascii() or not lengths[0].isdigit()
                        or len(lengths[0])>8 or int(lengths[0])>MAX_STREAM)):refusal='response_framing'
                elif len(media)>1 or media_type not in ('','text/event-stream','application/json'):
                    refusal='response_media_type'
                elif len(encodings)>1 or encodings and encodings[0].strip().lower()!='identity':
                    refusal='response_encoding'
                if refusal is not None:
                    state['disposition']='upstream_refused'; raise _ResponseRefused(refusal)
                wire_socket.settimeout(15)
                prefix=b''
                if media_type!='text/event-stream':
                    phase='response_stream';prefix=_sniff_sse(reply,wire_socket,state)
                self.send_response(200); self.send_header('Content-Type','text/event-stream')
                self.send_header('Connection','close'); self.end_headers(); started=True
                phase='response_stream'
                # Hold a credential-length tail to prevent an echo split across
                # reads from being forwarded. Headers/token values never leave
                # this child except as the permitted upstream auth headers.
                secrets_to_check=[auth[7:].encode('ascii')]
                if account is not None: secrets_to_check.append(account.encode('ascii'))
                tail=b''
                for _ in range(MAX_STREAM+1):
                    if prefix:part,prefix=prefix,b''
                    else:
                        part=reply.read1(8192)
                        if not part: break
                        state['response_bytes']+=len(part)
                    if state['response_bytes']>MAX_STREAM: raise ValueError('Response exceeds limit')
                    tail+=part
                    if any(secret in tail for secret in secrets_to_check):
                        state['disposition']='credential_echo'; raise ValueError('Credential echo')
                    hold=max(map(len,secrets_to_check))-1
                    if len(tail)>hold:
                        chunk,tail=(tail[:-hold],tail[-hold:]) if hold else (tail,b'')
                        self.wfile.write(chunk); self.wfile.flush()
                if lengths and state['response_bytes']!=int(lengths[0]):
                    raise ValueError('Incomplete upstream response')
                if tail: self.wfile.write(tail); self.wfile.flush()
                state['disposition']='relayed'
            except Exception as error:
                if isinstance(error,_ResponseRefused):state['disposition']='upstream_refused'
                state['failure']=safe_failure(error,phase)
                if not started:
                    try: self.send_error(502 if state['attempts'] else 400)
                    except OSError: pass
            finally:
                if upstream is not None: upstream.close()
                self.close_connection=True
        def do_GET(self):
            if observer is not None:
                observer({'method':'GET','path':self.path.replace(capability,'<capability>')})
            state['failure']={'phase':'local_request','category':'validation'}
            self.send_error(404); self.close_connection=True
    with http.server.HTTPServer(('127.0.0.1',0),Peer) as server:
        server.timeout=55
        emit({'phase':'ready','port':server.server_port})
        server.handle_request()
    if state['disposition']=='refused' and state['failure'] is None:
        state['failure']={'phase':'local_request','category':'remote_closed' if connected else 'timeout'}
    emit(state)


def _worker():
    packet=sys.stdin.buffer.read(MAX_PACKET+1)
    if len(packet)>MAX_PACKET: raise ValueError('Bounded relay packet required')
    value=json.loads(packet)
    if set(value)!={'body','capability'}: raise ValueError('Closed relay packet required')
    body=base64.b64decode(value['body'],validate=True)
    def emit(event):
        print(json.dumps(event,separators=(',',':')),flush=True)
    # Local request and service-response bounds belong to their own parser.
    # A shared global limit would wrongly reject bounded service responses.
    serve_once(body,value['capability'],emit)


if __name__=='__main__':
    if sys.argv[1:]!=['--relay-worker']: raise SystemExit(2)
    try: _worker()
    except Exception: raise SystemExit(1) from None
    raise SystemExit(0)


import atexit
from dataclasses import replace
import os
from pathlib import Path
import secrets
import selectors
import shutil
import stat
import subprocess
import tempfile
import threading
import signal

from claimbranch.core.canonical import ContractError
from .codex_app_server import CodexAppServerTransport, CodexResult, DISABLED_FEATURES, mac_codex_policy
from .codex_egress import compile_codex_http
from .provider_profile import PreparedCodexRequest


def installed_runtime():
    """Inspect identities/permissions only, never credential bytes."""
    if sys.platform!='darwin': raise ContractError('This Codex connection currently requires macOS; continue manually.')
    selected=shutil.which('codex')
    if not selected: raise ContractError('Install Codex 0.158.0 and run codex login first; no API key is required.')
    client=Path(selected).resolve(strict=True)
    auth=Path.home()/'.codex/auth.json'
    for path,private in ((client,False),(auth,True)):
        info=path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
            or info.st_nlink!=1 or info.st_mode & (0o077 if private else 0o022)):
            raise ContractError('Codex executable/login file must be owned, regular and privately writable; continue manually.')
    roots=ssl.get_default_verify_paths().cafile
    if not roots or not Path(roots).is_file(): raise ContractError('Public TLS roots unavailable; continue manually.')
    return client,auth,Path(roots)


def relay_policy(client, root, *, auth=None, port=None):
    policy=mac_codex_policy(str(client),str(root),credential_file=None if auth is None else str(auth),proxy_port=port)
    policy='\n'.join(line for line in policy.splitlines()
        if 'com.apple.SecurityServer' not in line and 'com.apple.trustd.agent' not in line)
    # The pinned client's managed-preference synchronization needs these two
    # exact OS cache channels even with preference value access denied. Names
    # were observed on an owned, unauthenticated CLI under a deny-all IPC rule.
    # Do not permit a prefix, arbitrary user domain, shared-memory write or sem.
    return policy+'\n(deny user-preference-read user-preference-write signal ipc-posix* iokit-open process-fork)'+\
        '\n(allow ipc-posix-shm-read-data (ipc-posix-name "apple.cfprefs.daemonv1")'+\
        f' (ipc-posix-name "apple.cfprefs.{os.getuid()}v1"))'


def client_launch(root, client, auth, roots, port, capability):
    for part in ('cwd','tmp','client'): (root/part).mkdir(mode=0o700)
    (root/'client/auth.json').symlink_to(auth)
    public=roots.read_bytes()
    if len(public)>1048576: raise ContractError('Public TLS roots exceed their bound.')
    (root/'public-roots.pem').write_bytes(public)
    (root/'empty-certs').mkdir(mode=0o700)
    # Required shape/capabilities checked against rust-v0.158.0's public
    # ModelInfo and models.json. These bounded local metadata suppress remote
    # catalog fetching. They establish no account/model entitlement.
    catalog={'models':[{'slug':'gpt-6-sol','display_name':'GPT-6-Sol',
        'description':'ClaimBranch bounded text proposal connection',
        'default_reasoning_level':'medium',
        'supported_reasoning_levels':[{'effort':effort,'description':effort}
            for effort in ('low','medium','high','xhigh')],
        'shell_type':'disabled','visibility':'list','supported_in_api':True,
        'priority':0,'support_verbosity':True,'default_verbosity':'low',
        'truncation_policy':{'mode':'tokens','limit':10000},
        'experimental_supported_tools':[],'input_modalities':['text'],
        'base_instructions':'','include_apps_usage_instructions':False,
        'use_responses_lite':False,'multi_agent_version':None}]}
    (root/'catalog.json').write_text(json.dumps(catalog,separators=(',',':')))
    policy=relay_policy(client,root,auth=auth,port=port)
    (root/'policy.sb').write_text(policy)
    config={**{'features.'+k:False for k in DISABLED_FEATURES},
        'features.skip_host_skill_discovery':True,'web_search':'disabled',
        'project_doc_max_bytes':0,'mcp_servers':{},'analytics.enabled':False,
        'otel.exporter':'none','otel.metrics_exporter':'none','history.persistence':'none',
        'sqlite_home':str(root/'tmp'),'log_dir':str(root/'tmp'),
        'model_catalog_json':str(root/'catalog.json'),
        'suppress_unstable_features_warning':True,'model_provider':'claimbranch-chatgpt',
        'model_providers.claimbranch-chatgpt.name':'ClaimBranch reviewed ChatGPT request',
        'model_providers.claimbranch-chatgpt.base_url':f'http://127.0.0.1:{port}/{capability}',
        'model_providers.claimbranch-chatgpt.wire_api':'responses',
        'model_providers.claimbranch-chatgpt.requires_openai_auth':True,
        'model_providers.claimbranch-chatgpt.request_max_retries':0,
        'model_providers.claimbranch-chatgpt.stream_max_retries':0,
        'model_providers.claimbranch-chatgpt.supports_websockets':False}
    args=['/usr/bin/sandbox-exec','-f',str(root/'policy.sb'),str(client),
        '--no-daemon','--strict-config','-a','never','-C',str(root/'cwd')]
    for key,value in config.items(): args+=['-c',key+'='+json.dumps(value,separators=(',',':'))]
    args+=['app-server','--listen','stdio://']
    env={'HOME':str(root),'CODEX_HOME':str(root/'client'),'TMPDIR':str(root/'tmp'),
        'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','SSL_CERT_FILE':str(root/'public-roots.pem'),
        'SSL_CERT_DIR':str(root/'empty-certs')}
    return tuple(args),root/'cwd',env


def verify_client_version(client, root, cancel):
    """Bounded asynchronous-owner preflight with no login alias or network."""
    policy=root/'version-policy.sb'
    policy.write_text(relay_policy(client,root))
    proc=None; cleanup=True; output=bytearray(); valid=False
    try:
        if cancel.is_set(): return False,True
        proc=subprocess.Popen(('/usr/bin/sandbox-exec','-f',str(policy),str(client),'--version'),
            cwd=root,env={'HOME':str(root),'CODEX_HOME':str(root),'TMPDIR':str(root),
                'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'},
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        deadline=time.monotonic()+5; counts={'stdout':0,'stderr':0}
        with selectors.DefaultSelector() as selector:
            for name in counts:
                pipe=getattr(proc,name); os.set_blocking(pipe.fileno(),False)
                selector.register(pipe,selectors.EVENT_READ,name)
            while selector.get_map() and not cancel.is_set() and time.monotonic()<deadline:
                for key,_ in selector.select(.05):
                    part=os.read(key.fd,4096)
                    if not part: selector.unregister(key.fileobj); continue
                    counts[key.data]+=len(part)
                    if counts[key.data]>16384: raise ValueError('Version output exceeds limit')
                    if key.data=='stdout': output.extend(part)
            if not selector.get_map() and not cancel.is_set():
                valid=proc.wait(timeout=max(.01,deadline-time.monotonic()))==0 and output==b'codex-cli 0.158.0\n'
    except (OSError,ValueError,subprocess.TimeoutExpired): valid=False
    finally:
        if proc is not None:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            except OSError: cleanup=False
            try: proc.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired): cleanup=False
            for pipe in (proc.stdout,proc.stderr):
                try: pipe.close()
                except OSError: cleanup=False
    return valid and cleanup,cleanup


class CodexRelayJob:
    def __init__(self,prepared,body,runtime,*,now=None):
        self.prepared,self.body,self.runtime=prepared,body,runtime
        self._epoch=int(time.time()) if now is None else now
        self._cancel=threading.Event(); self._done=threading.Event(); self._result=None; self._lock=threading.Lock()
        self.wire_result=None; self.retained_directory=None
        self._thread=threading.Thread(target=self._run,daemon=True); self._thread.start()
    def poll(self):
        with self._lock: return self._result
    def cancel(self):
        with self._lock:
            if self._result is not None: return False
            self._cancel.set(); return True
    def wait_closed(self,timeout=1):
        return self._done.wait(timeout) and self._result.cleanup_complete
    def _run(self):
        started=time.monotonic(); relay=None; inner=None; root=None; result=None; cleanup=True
        try:
            root=Path(tempfile.mkdtemp(prefix='claimbranch-codex-relay-',dir='/private/tmp'))
            if self.runtime:
                valid,reaped=verify_client_version(self.runtime[0],root,self._cancel)
                cleanup=reaped and cleanup
                if not valid: raise ValueError('Pinned client version unavailable')
            capability=secrets.token_hex(32)
            relay_started=time.monotonic()
            relay=subprocess.Popen([sys.executable,'-I',str(Path(__file__).resolve()),'--relay-worker'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                env={},cwd=root,start_new_session=True)
            packet=json.dumps({'body':base64.b64encode(self.body).decode(),'capability':capability}).encode()
            # Bounded packet to a stdlib child that reads stdin before serving.
            os.set_blocking(relay.stdin.fileno(),False)
            os.set_blocking(relay.stdout.fileno(),False)
            pending=bytearray(); events=[]; total=0; sent=0; stdout_closed=False
            with selectors.DefaultSelector() as selector:
                selector.register(relay.stdout,selectors.EVENT_READ)
                selector.register(relay.stdin,selectors.EVENT_WRITE)
                while time.monotonic()-started<60 and not self._cancel.is_set():
                    if not selector.get_map(): self._cancel.wait(.05)
                    for key,_ in selector.select(.05):
                        if key.fileobj is relay.stdin:
                            try: sent+=os.write(key.fd,packet[sent:sent+8192])
                            except BlockingIOError: continue
                            if sent==len(packet):
                                selector.unregister(relay.stdin); relay.stdin.close()
                            continue
                        chunk=os.read(key.fd,8192)
                        if not chunk:
                            selector.unregister(relay.stdout)
                            stdout_closed=True
                            if not events: raise ValueError('Relay startup failed')
                            break
                        total+=len(chunk); pending.extend(chunk)
                        if total>16384: raise ValueError('Relay metadata exceeds limit')
                        while b'\n' in pending:
                            line,_,rest=pending.partition(b'\n'); pending=bytearray(rest)
                            events.append(json.loads(line))
                            if len(events)>2: raise ValueError('Unexpected relay metadata')
                    if inner is None and events:
                        ready=events[0]
                        if (set(ready)!={'phase','port'} or ready['phase']!='ready'
                            or type(ready['port']) is not int or not 1<=ready['port']<=65535):
                            raise ValueError('Invalid relay startup')
                        command,cwd,env=client_launch(root,*self.runtime,ready['port'],capability)
                        inner=CodexAppServerTransport(command,cwd=cwd,environment=env,
                            total_seconds=max(.01,60-(time.monotonic()-started)),provider_id='claimbranch-chatgpt')
                        job=inner.start(self.prepared,confirmed_digest=self.prepared.digest,
                            current_profile=self.prepared.profile,current_context=self.prepared.context,
                            now=self._epoch+int(time.monotonic()-started))
                    if inner is not None and job.poll() is not None:
                        result=job.poll()
                        if result.disposition!='completed' or len(events)==2: break
                    if inner is None and time.monotonic()-relay_started>5:
                        raise ValueError('Relay startup deadline')
                    if stdout_closed and len(events)<2: raise ValueError('Relay stopped without completion')
            if len(events)==2:
                state=events[1]
                if (type(state) is not dict or set(state)!={'disposition','attempts','http_status','body_sha256','response_bytes','failure'}
                    or state['body_sha256']!=hashlib.sha256(self.body).hexdigest()
                    or type(state['attempts']) is not int or state['attempts'] not in (0,1)
                    or state['http_status'] is not None and (type(state['http_status']) is not int or not 100<=state['http_status']<=599)
                    or type(state['response_bytes']) is not int or not 0<=state['response_bytes']<=MAX_STREAM+8192
                    or type(state['disposition']) is not str or state['disposition'] not in ('refused','upstream_refused','credential_echo','relayed')
                    or not valid_failure(state['failure']) or state['disposition']=='relayed' and (
                        state['failure'] is not None or state['attempts']!=1 or state['http_status']!=200 or state['response_bytes']>MAX_STREAM)):
                    raise ValueError('Invalid relay result')
                self.wire_result=state
            if result is not None and result.disposition=='completed':
                if self.wire_result is None or self.wire_result['disposition']!='relayed' or self.wire_result['attempts']!=1:
                    result=replace(result,disposition='client_failed',typed_result=None)
        except Exception: result=None
        finally:
            if inner is not None:
                inner.close(); cleanup=inner.wait_closed(3) and cleanup
            if relay is not None:
                if relay.poll() is None:
                    try: relay.kill()
                    except OSError: cleanup=False
                try: relay.wait(timeout=2)
                except (OSError,subprocess.TimeoutExpired): cleanup=False
                for pipe in (relay.stdin,relay.stdout):
                    if pipe is not None and not pipe.closed: pipe.close()
            if root is not None and cleanup:
                try: shutil.rmtree(root)
                except OSError: cleanup=False
            if root is not None and not cleanup:
                # Revoke our alias even if a child cannot be proved reaped.
                # Preserve potentially live files and report this exact owned
                # scratch, never delete the user's original login or research.
                try: (root/'client/auth.json').unlink(missing_ok=True)
                except OSError: pass
                self.retained_directory=str(root)
            disposition='cancelled' if self._cancel.is_set() else 'timed_out' if time.monotonic()-started>=60 else 'client_failed'
            if result is None:
                result=CodexResult(self.prepared.review.request_id,self.prepared.digest,disposition,
                    int((time.monotonic()-started)*1000),cleanup_complete=cleanup)
            with self._lock:
                if self._cancel.is_set() or not cleanup:
                    result=replace(result,disposition='cancelled' if self._cancel.is_set() else 'client_failed',typed_result=None,cleanup_complete=cleanup)
                self._result=result
            self._done.set()


class CodexRelayTransport:
    """Ephemeral actual route; never reconstructed from saved research state."""
    def __init__(self):
        self._lock=threading.Lock(); self._closed=False; self._jobs=[]; self._ids=set(); self._nonces=set()
        atexit.register(self._exit)
    def start(self,prepared,*,confirmed_digest,current_profile,current_context,now,confirmed_http_digest):
        if type(prepared) is not PreparedCodexRequest or confirmed_digest!=prepared.digest:
            raise ContractError('Inspect the exact current Codex request.')
        body=compile_codex_http(prepared,current_profile=current_profile,current_context=current_context,now=now)
        if confirmed_http_digest!=hashlib.sha256(body).hexdigest():
            raise ContractError('Inspect and confirm the complete current HTTP body.')
        if current_profile.value['model']!='gpt-6-sol':
            raise ContractError('This bounded connection currently supports gpt-6-sol; choose it explicitly or continue manually.')
        runtime=installed_runtime()
        with self._lock:
            if (self._closed or any(job.poll() is not None and not job.poll().cleanup_complete for job in self._jobs)
                or len(self._ids)>=3 or prepared.review.request_id in self._ids or prepared.review.nonce in self._nonces):
                raise ContractError('Request already spent or connection closed; continue manually.')
            self._ids.add(prepared.review.request_id); self._nonces.add(prepared.review.nonce)
            job=CodexRelayJob(prepared,body,runtime,now=now); self._jobs.append(job); return job
    def cleanup_notice(self):
        with self._lock: paths=[job.retained_directory for job in self._jobs if job.retained_directory]
        return ('Request cleanup not confirmed; continue manually and close this session. '
            'Temporary request data retained at '+', '.join(paths)+'. '
            'Remove only these folders after their processes have closed.' if paths else
            'Request cleanup is still pending; continue manually and close this session.')
    def cleanup_failed(self):
        with self._lock:
            return any(job.poll() is not None and job.poll().cleanup_complete is False for job in self._jobs)
    def close(self):
        with self._lock: self._closed=True; jobs=tuple(self._jobs)
        for job in jobs: job.cancel()
    def wait_closed(self,timeout=1):
        deadline=time.monotonic()+timeout
        with self._lock: jobs=tuple(self._jobs)
        closed=all([job.wait_closed(max(0,deadline-time.monotonic())) for job in jobs])
        if closed and self._closed: atexit.unregister(self._exit)
        return closed
    def _exit(self): self.close(); self.wait_closed(5)
