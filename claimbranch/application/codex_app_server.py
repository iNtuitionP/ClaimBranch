"""Internal bounded Codex 0.158.0 stdio adapter, not provider qualification.

The trusted caller supplies the actual isolated command/environment only after
access and egress qualification and foreground consent. No public command does
so today. This module never reads/copies login tokens, installs a CLI, executes
server-requested tools, writes science or persists a live capability. Read-only
RPC policy alone does not restrict the CLI's research-file reads or HTTP egress.
"""
import atexit
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import threading
import time

from claimbranch.core.canonical import ContractError, canonical_bytes, identifier
from claimbranch.core.paper_proposals import provider_typed_result
from .provider_profile import PreparedCodexRequest, POLICY

MAX_LINE = 262144
MAX_STDOUT = 1048576
MAX_STDERR = 65536
MAX_EVENTS = 8192
TRANSPORT_START_LIMIT = 3
DELTA_EVENTS = ['item/agentMessage/delta', 'item/reasoning/textDelta',
    'item/reasoning/summaryTextDelta', 'item/reasoning/summaryPartAdded']
SAFE_ITEMS = {'userMessage', 'agentMessage', 'reasoning'}
PASSIVE_EVENTS = {'thread/started', 'thread/status/changed', 'thread/tokenUsage/updated',
    'account/rateLimits/updated', 'item/agentMessage/delta', 'item/reasoning/textDelta',
    'item/reasoning/summaryTextDelta', 'item/reasoning/summaryPartAdded'}
DISABLED_FEATURES = ('shell_tool', 'unified_exec', 'shell_snapshot', 'view_image', 'apps',
    'browser_use', 'browser_use_external', 'computer_use', 'multi_agent', 'hooks',
    'plugin_hooks', 'remote_plugin', 'skill_search', 'memories', 'goals',
    'unbounded_connection_retries', 'responses_websockets', 'responses_websockets_v2',
    'plugins', 'default_mode_request_user_input', 'auth_elicitation',
    'tool_call_mcp_elicitation', 'sleep_tool', 'tool_suggest')
ACCOUNT_PLANS = {'free', 'go', 'plus', 'pro', 'prolite', 'promax', 'team',
    'self_serve_business_prolite', 'self_serve_business_usage_based', 'business',
    'ent26', 'enterprise_cbp_automation', 'enterprise_cbp_usage_based',
    'enterprise', 'edu', 'edu_plus', 'edu_pro', 'unknown'}
ERROR_CATEGORIES = {'contextWindowExceeded', 'sessionBudgetExceeded', 'usageLimitExceeded',
    'rateLimitExceeded', 'flexUnavailable', 'serverOverloaded', 'cyberPolicy',
    'misalignmentPolicyViolation', 'internalServerError', 'unauthorized', 'badRequest',
    'threadRollbackFailed', 'sandboxError', 'other'}
HTTP_ERROR_CATEGORIES = {'httpConnectionFailed', 'responseStreamConnectionFailed',
    'responseStreamDisconnected', 'responseTooManyFailedAttempts'}
SERVICE_ERROR_CODES = {'invalid_json_schema', 'model_not_found', 'invalid_api_key',
    'insufficient_quota', 'rate_limit_exceeded'}
PROPOSAL_FAILURES = frozenset({'advisory_text', 'proposal_json', 'proposal_schema',
    'proposal_reference', 'proposal_context', 'proposal_semantics'})


def _proposal_failure(raw, error):
    """Closed diagnostic only; never retain rejected text or exception details."""
    from claimbranch.core.canonical import decode
    from claimbranch.core.paper_proposals import result_schema
    from claimbranch.core.research_schema import normalize
    if str(error) in {
        'typed suggestions require compiled paper context v2',
        'typed proposal context or digest changed',
        'manuscript drafting stays on the existing text-only route',
    }:
        return CodexFailure('proposal_context')
    try:
        value = decode(raw)
    except ContractError:
        return CodexFailure('proposal_json')
    try:
        normalize(value, result_schema())
    except ContractError:
        return CodexFailure('proposal_schema')
    # Match only fixed validator messages. Unknown exceptions never become
    # diagnostics, even when they contain provider text or instructions.
    category = {
        'unknown, unselected or wrong-kind proposal reference': 'proposal_reference',
        'reference a proposed edit by its item id, not its old context identity': 'proposal_reference',
        'edit requires one matching explicitly selected target': 'proposal_reference',
    }.get(str(error), 'proposal_semantics')
    return CodexFailure(category)


def mac_codex_policy(client, scratch, *, credential_file=None, proxy_port=None):
    """Compile bounded file/exec/network/Mach lookup for an owned Mac runtime.

    This pure internal helper neither inspects file ownership/identity nor
    qualifies service APIs, a proxy, credentials or generated HTTP. The trusted
    owner must supply independently checked canonical paths and private scratch.
    No public option or stored observation creates a live capability.
    """
    def path(value):
        if (type(value) is not str or not value.startswith('/') or value=='/'
                or any(ord(c)<32 or ord(c)==127 for c in value)
                or any(part in ('', '.', '..') for part in value.split('/')[1:])):
            raise ContractError('Explicit normalized absolute runtime paths required.')
        return Path(value)
    executable, root=path(client), path(scratch)
    if (root.parent!=Path('/private/tmp') or not root.name.startswith('claimbranch-codex-')
            or executable.is_relative_to(root) or root.is_relative_to(executable)):
        raise ContractError('An independent executable and bounded owned temporary root are required.')
    credential=None if credential_file is None else path(credential_file)
    if credential is not None and (credential.is_relative_to(root) or root.is_relative_to(credential)):
        raise ContractError('The original credential must remain outside writable scratch.')
    if proxy_port is not None and (type(proxy_port) is not int or not 1<=proxy_port<=65535):
        raise ContractError('An explicit owned loopback port is required.')
    quote=lambda value: json.dumps(str(value),ensure_ascii=True)
    rules=['(version 1)', '(allow default)', '(deny network*)',
        '(deny file-read*)', '(allow file-read-metadata)',
        # dyld aborts before main without this exact root lookup. A subpath
        # exception would expose every file and must never replace this literal.
        '(allow file-read-data (literal "/"))',
        '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") '
        '(subpath "/usr/share") (subpath "/private/var/db/timezone") '
        '(literal "/dev/urandom") (literal "/dev/random") (literal "/dev/null"))',
        '(allow file-read* (literal '+quote(executable)+') (subpath '+quote(root)+'))',
        '(deny file-write*)', '(allow file-write* (literal "/dev/null") (subpath '+quote(root)+'))',
        '(deny process-exec)', '(allow process-exec (literal '+quote(executable)+'))',
        '(deny appleevent-send)', '(deny mach-lookup)',
        '(deny authorization-right-obtain)']
    # Observed with the actual pinned CLI's existing-login controls. SecurityServer
    # and trustd.agent are needed for the observed authentication, not proven
    # TLS internals. SecurityServer may expose additional keychain items beyond
    # credential_file. Their key/human-operation APIs and generated HTTP remain
    # unqualified; public qualification stays closed.
    for service in ('com.apple.cfprefsd.daemon', 'com.apple.cfprefsd.agent',
            'com.apple.SecurityServer', 'com.apple.trustd.agent'):
        rules.append('(allow mach-lookup (global-name '+quote(service)+'))')
    if credential is not None:
        rules.append('(allow file-read* (literal '+quote(credential)+'))')
    if proxy_port is not None:
        rules.append('(allow network-outbound (remote tcp "localhost:'+str(proxy_port)+'"))')
    return '\n'.join(rules)


class _Stop(Exception):
    def __init__(self, disposition): self.disposition = disposition


def _json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError('duplicate key')
            value[key] = item
        return value
    def constant(_): raise ValueError('non-finite number')
    def check(value, depth=0):
        if depth > 32: raise ValueError('nesting limit')
        if isinstance(value, float) and not math.isfinite(value): raise ValueError('non-finite number')
        if type(value) is dict:
            if len(value)>128: raise ValueError('object limit')
            for item in value.values(): check(item, depth+1)
        elif type(value) is list:
            if len(value)>512: raise ValueError('collection limit')
            for item in value: check(item, depth+1)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        check(value)
        if type(value) is not dict: raise ValueError('object required')
        return value
    except (ValueError, UnicodeError, RecursionError): raise _Stop('protocol_error') from None


def _frame(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw)>MAX_LINE: raise _Stop('response_too_large')
    return raw+b'\n'


@dataclass(frozen=True)
class CodexFailure:
    """Ephemeral client observations, never raw diagnostics or verified HTTP."""
    category: str
    http_status: int | None = None
    client_reports_retry: bool | None = None
    rpc_code: int | None = None
    service_error_code: str | None = None

    def metadata(self):
        return {key:value for key,value in asdict(self).items() if value is not None}


def _failure(error, *, retry=None):
    info=error.get('codexErrorInfo') if type(error) is dict else None
    category, status='unclassified', None
    if type(info) is str and info in ERROR_CATEGORIES:
        category=info
    elif type(info) is dict and len(info)==1:
        code=next(iter(info)); detail=info[code]
        if code in HTTP_ERROR_CATEGORIES and type(detail) is dict:
            category=code
            candidate=detail.get('httpStatusCode')
            if type(candidate) is int and 100<=candidate<=599: status=candidate
        elif code=='activeTurnNotSteerable' and type(detail) is dict:
            category=code
    # The pinned client maps some HTTP errors to "other" and places the JSON
    # error envelope in message. Project only a known machine code; never retain
    # its text, params, paths, instructions or an arbitrary provider-supplied code.
    service_code=None
    message=error.get('message') if type(error) is dict else None
    if type(message) is str and len(message)<=16384:
        try: raw=message.encode('utf-8')
        except UnicodeError: raw=b''
        if len(raw)<=16384:
            try:
                envelope=_json(raw)
                detail=envelope.get('error')
                code=detail.get('code') if type(detail) is dict else None
                if type(code) is str and code in SERVICE_ERROR_CODES: service_code=code
            except _Stop: pass
    return CodexFailure(category,status,retry if type(retry) is bool else None,
        service_error_code=service_code)


@dataclass(frozen=True)
class CodexResult:
    request_id: str
    request_digest: str
    disposition: str
    elapsed_ms: int
    response_digest: str | None = None
    typed_result: bytes | None = None
    reported_model: str | None = None
    client_version: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    cleanup_complete: bool = True
    failure: CodexFailure | None = None

    def metadata(self):
        value=asdict(self); value.pop('typed_result'); value.pop('failure')
        return value


class _Protocol:
    def __init__(self, prepared, cwd, provider_id='openai'):
        self.prepared, self.cwd = prepared, str(cwd)
        self.provider_id = provider_id
        self.body = _json(prepared.body)
        self.profile = prepared.profile.value
        self.pending = None
        self.thread_id = self.turn_id = self.client_version = None
        self.turn_ack = False
        self.items = {}
        self.finished = False
        self.typed = self.response_digest = None
        self.failure = None

    def request(self, request_id, method, params):
        self.pending = request_id
        return _frame({'id':request_id, 'method':method, 'params':params})

    def start(self):
        return self.request(1, 'initialize', {'clientInfo':{'name':'claimbranch', 'version':'0.1'},
            'capabilities':{'experimentalApi':True,'optOutNotificationMethods':DELTA_EVENTS}})

    def _identity(self, params):
        if (self.thread_id is None or params.get('threadId') != self.thread_id
                or self.turn_id is None or params.get('turnId') != self.turn_id):
            raise _Stop('protocol_error')

    def _item(self, item):
        if type(item) is not dict or item.get('type') not in SAFE_ITEMS: raise _Stop('policy_refused')
        try: identifier(item.get('id'))
        except ContractError: raise _Stop('protocol_error') from None
        if item['type']=='agentMessage' and (type(item.get('text')) is not str
                or item.get('phase') not in (None, 'commentary', 'final_answer')):
            raise _Stop('protocol_error')

    def receive(self, message):
        if 'jsonrpc' in message and message['jsonrpc']!='2.0': raise _Stop('protocol_error')
        if 'id' in message:
            # Never fulfill a server tool/approval/auth request. Killing this
            # session is fail-closed handling, not proof of OS tool confinement.
            if 'method' in message: raise _Stop('policy_refused')
            if (type(message['id']) is not int or message['id'] != self.pending
                    or set(message)-{'id','result','error','jsonrpc'}
                    or ('result' in message)==('error' in message)):
                raise _Stop('protocol_error')
            if 'error' in message:
                error=message['error']; code=error.get('code') if type(error) is dict else None
                self.failure=CodexFailure('rpcError',rpc_code=code if type(code) is int
                    and code in (-32700,-32600,-32601,-32602,-32603) else None)
                raise _Stop('client_failed')
            value=message['result']
            if type(value) is not dict: raise _Stop('protocol_error')
            request_id=self.pending; self.pending=None
            if request_id==1:
                # The bounded relay needs login mode, not account discovery.
                # Pinned getAuthStatus(includeToken=false,refreshToken=false)
                # avoids account/read's separate workspace-routing request.
                method,params=('getAuthStatus',{'includeToken':False,'refreshToken':False}) if self.provider_id=='claimbranch-chatgpt' else ('account/read',{'refreshToken':False})
                return _frame({'method':'initialized'})+self.request(2,method,params)
            if request_id==2:
                if self.provider_id=='claimbranch-chatgpt':
                    if (set(value)!={'authMethod','authToken','requiresOpenaiAuth'}
                            or value['authMethod']!='chatgpt' or value['authToken'] is not None
                            or value['requiresOpenaiAuth'] is not True):
                        raise _Stop('auth_required')
                elif type(value.get('account')) is not dict or value['account'].get('type')!='chatgpt':
                    raise _Stop('auth_required')
                return self.request(5,'model/list',{'limit':100,'includeHidden':True})
            if request_id==5:
                # Check client-advertised metadata before a thread or model turn.
                # A matching catalog is not proof of the actual served model.
                rows=value.get('data')
                if (set(value)!={'data','nextCursor'} or type(rows) is not list
                        or len(rows)>100 or any(type(row) is not dict for row in rows)):
                    raise _Stop('protocol_error')
                if value.get('nextCursor') is not None: raise _Stop('policy_refused')
                matches=[row for row in rows if row.get('id')==self.profile['model']]
                if len(matches)!=1: raise _Stop('policy_refused')
                selected=matches[0]
                efforts=selected.get('supportedReasoningEfforts')
                modalities=selected.get('inputModalities',['text','image'])
                if (selected.get('model')!=self.profile['model']
                        or type(efforts) is not list or not 1<=len(efforts)<=8
                        or any(type(option) is not dict or type(option.get('reasoningEffort')) is not str
                            for option in efforts)
                        or self.profile['reasoning_effort'] not in [option['reasoningEffort'] for option in efforts]
                        or type(modalities) is not list or not 1<=len(modalities)<=8
                        or any(type(modality) is not str for modality in modalities) or 'text' not in modalities):
                    raise _Stop('policy_refused')
                config={**{'features.'+key:False for key in DISABLED_FEATURES},
                    'features.skip_host_skill_discovery':True, 'web_search':'disabled',
                    'project_doc_max_bytes':0, 'mcp_servers':{}, 'model_provider':self.provider_id,
                    'suppress_unstable_features_warning':True}
                return self.request(3,'thread/start',{'model':self.profile['model'], 'modelProvider':self.provider_id,
                    'allowProviderModelFallback':False, 'cwd':self.cwd, 'ephemeral':True,
                    'approvalPolicy':'never', 'sandbox':'read-only', 'baseInstructions':self.body['instructions'],
                    'developerInstructions':'',
                    'dynamicTools':[], 'environments':[], 'runtimeWorkspaceRoots':[],
                    'selectedCapabilityRoots':[], 'config':config})
            if request_id==3:
                thread=value.get('thread')
                if (type(thread) is not dict or value.get('model')!=self.profile['model']
                        or value.get('modelProvider')!=self.provider_id or value.get('cwd')!=self.cwd
                        or value.get('approvalPolicy')!='never' or value.get('approvalsReviewer')!='user'
                        or value.get('sandbox')!={'type':'readOnly','networkAccess':False}
                        or value.get('instructionSources',[])!=[] or value.get('runtimeWorkspaceRoots',[])!=[]
                        or thread.get('cliVersion')!=self.profile['client_version']
                        or thread.get('ephemeral') is not True or thread.get('cwd')!=self.cwd
                        or thread.get('modelProvider')!=self.provider_id or thread.get('environments',[])!=[]
                        or thread.get('model',self.profile['model'])!=self.profile['model']):
                    raise _Stop('policy_refused')
                try: self.thread_id=identifier(thread.get('id'))
                except ContractError: raise _Stop('protocol_error') from None
                self.client_version=thread['cliVersion']
                return self.request(4,'turn/start',{'threadId':self.thread_id, 'model':self.profile['model'],
                    'effort':self.profile['reasoning_effort'], 'cwd':self.cwd, 'approvalPolicy':'never',
                    'sandboxPolicy':{'type':'readOnly','networkAccess':False}, 'environments':[],
                    'runtimeWorkspaceRoots':[], 'input':[{'type':'text',
                        'text':json.dumps(self.body['input'],ensure_ascii=False,separators=(',',':'))}],
                    'outputSchema':self.body['output_schema']})
            if request_id==4:
                turn=value.get('turn')
                if type(turn) is not dict or turn.get('status')!='inProgress': raise _Stop('protocol_error')
                try: turn_id=identifier(turn.get('id'))
                except ContractError: raise _Stop('protocol_error') from None
                if self.turn_id is not None and self.turn_id!=turn_id: raise _Stop('protocol_error')
                self.turn_id=turn_id; self.turn_ack=True
                return b''
            raise _Stop('protocol_error')
        if set(message)-{'method','params','jsonrpc','emittedAtMs'}: raise _Stop('protocol_error')
        if 'emittedAtMs' in message and (type(message['emittedAtMs']) is not int or message['emittedAtMs']<0):
            raise _Stop('protocol_error')
        method=message.get('method'); params=message.get('params',{})
        if type(params) is not dict: raise _Stop('protocol_error')
        if method=='account/updated':
            # Observed during account/read on the installed authenticated CLI.
            # This notification is not a substitute for its account response;
            # no identity/plan information enters a proposal or retained trace.
            if self.pending!=2: raise _Stop('policy_refused')
            plan=params.get('planType')
            if (set(params)-{'authMode','planType'}
                    or plan is not None and (type(plan) is not str or plan not in ACCOUNT_PLANS)):
                raise _Stop('protocol_error')
            if params.get('authMode')!='chatgpt': raise _Stop('auth_required')
            return b''
        if method=='thread/settings/updated':
            if (set(params)!={'threadId','threadSettings'} or self.thread_id is None
                    or params.get('threadId')!=self.thread_id or not (self.pending==4 or self.turn_ack)):
                raise _Stop('protocol_error')
            settings=params['threadSettings']
            fields={'activePermissionProfile','approvalPolicy','approvalsReviewer','collaborationMode',
                'cwd','disabledPluginIds','effort','model','modelProvider','multiAgentMode','personality',
                'sandboxPolicy','serviceTier','summary'}
            if type(settings) is not dict or set(settings)!=fields: raise _Stop('protocol_error')
            sandbox=settings['sandboxPolicy']; collaboration=settings['collaborationMode']
            if (settings['model']!=self.profile['model'] or settings['modelProvider']!=self.provider_id
                    or settings['effort']!=self.profile['reasoning_effort'] or settings['cwd']!=self.cwd
                    or settings['approvalPolicy']!='never' or settings['approvalsReviewer']!='user'
                    or settings['activePermissionProfile'] is not None
                    or settings['multiAgentMode']!='explicitRequestOnly' or settings['disabledPluginIds']!=[]
                    or any(settings[key] is not None for key in ('personality','serviceTier','summary'))
                    or type(sandbox) is not dict or set(sandbox)!={'type','networkAccess'}
                    or sandbox['type']!='readOnly' or sandbox['networkAccess'] is not False
                    or type(collaboration) is not dict or set(collaboration)!={'mode','settings'}
                    or collaboration['mode']!='default'):
                raise _Stop('policy_refused')
            inner=collaboration['settings']
            if (type(inner) is not dict or set(inner)!={'developer_instructions','model','reasoning_effort'}
                    or inner['model']!=self.profile['model'] or inner['reasoning_effort']!=self.profile['reasoning_effort']
                    or inner['developer_instructions'] is not None):
                raise _Stop('policy_refused')
            return b''
        if method=='remoteControl/status/changed':
            if params.get('status')!='disabled' or params.get('environmentId') is not None:
                raise _Stop('policy_refused')
            return b''
        if method=='error':
            if (self.thread_id is not None and self.turn_id is not None
                    and params.get('threadId')==self.thread_id and params.get('turnId')==self.turn_id):
                self.failure=_failure(params.get('error'),retry=params.get('willRetry'))
            raise _Stop('client_failed')
        if method in PASSIVE_EVENTS:
            if 'threadId' in params and self.thread_id is not None and params['threadId']!=self.thread_id:
                raise _Stop('protocol_error')
            return b''
        if method=='turn/started':
            turn=params.get('turn',{})
            if (not (self.pending==4 or self.turn_ack) or type(turn) is not dict
                    or params.get('threadId')!=self.thread_id or turn.get('status')!='inProgress'):
                raise _Stop('protocol_error')
            try: turn_id=identifier(turn.get('id'))
            except ContractError: raise _Stop('protocol_error') from None
            if self.turn_id is not None and self.turn_id!=turn_id: raise _Stop('protocol_error')
            self.turn_id=turn_id
            return b''
        if method in ('item/started','item/completed'):
            self._identity(params); item=params.get('item'); self._item(item)
            if method=='item/completed':
                if item['id'] in self.items: raise _Stop('protocol_error')
                self.items[item['id']]=item
            return b''
        if method=='turn/completed':
            turn=params.get('turn')
            if type(turn) is not dict: raise _Stop('protocol_error')
            self._identity({'threadId':params.get('threadId'), 'turnId':turn.get('id')})
            if not self.turn_ack: raise _Stop('protocol_error')
            if turn.get('status')!='completed' or turn.get('error') is not None:
                self.failure=_failure(turn.get('error'))
                raise _Stop('client_failed')
            view=turn.get('itemsView','full')
            if (type(turn.get('items')) is not list or type(view) is not str
                    or view not in ('full','summary','notLoaded')
                    or view=='notLoaded' and turn['items']):
                raise _Stop('protocol_error')
            # The pinned client also emits summary/notLoaded terminal views.
            # Only owned item/completed events supply full proposal content.
            # Every item present in the terminal display must still agree; a
            # summary alone can never manufacture a completed assistant message.
            terminal_ids=set()
            for item in turn['items']:
                self._item(item)
                if item['id'] in terminal_ids or item['id'] not in self.items:
                    raise _Stop('protocol_error')
                terminal_ids.add(item['id'])
                # Stable JSON preserves bool/int/float distinctions that Python
                # container equality erases, without imposing domain string limits
                # on the complete assistant-message envelope.
                encode=lambda value: json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
                if encode(self.items[item['id']])!=encode(item): raise _Stop('protocol_error')
            if view=='full' and terminal_ids!=set(self.items): raise _Stop('protocol_error')
            finals=[i for i in self.items.values() if i['type']=='agentMessage' and i.get('phase')=='final_answer']
            if not finals:
                finals=[i for i in self.items.values() if i['type']=='agentMessage' and i.get('phase') is None]
            if len(finals)!=1: raise _Stop('protocol_error')
            raw=finals[0]['text'].encode('utf-8')
            if len(raw)>65536: raise _Stop('response_too_large')
            self.response_digest=hashlib.sha256(raw).hexdigest()
            try:
                if self.prepared.discussion is not None and not self.prepared.edit:
                    from claimbranch.core.advisory import advice_from_text
                    self.typed=canonical_bytes(advice_from_text(raw))
                else:
                    from claimbranch.core.paper_proposals import provider_edit_result
                    self.typed=canonical_bytes((provider_edit_result if self.prepared.edit else provider_typed_result)(raw,self.prepared.context))
            except ContractError as error:
                self.failure = (CodexFailure('advisory_text') if self.prepared.discussion is not None and not self.prepared.edit else
                    _proposal_failure(raw, error))
                raise _Stop('malformed_response') from None
            self.finished=True; return b''
        raise _Stop('protocol_error')


class CodexJob:
    def __init__(self, prepared, command, cwd, environment, total_seconds, provider_id='openai'):
        self._prepared, self._command, self._cwd = prepared, command, cwd
        self._environment, self._seconds = environment, total_seconds
        self._provider_id = provider_id
        self._cancel=threading.Event(); self._done=threading.Event(); self._lock=threading.Lock()
        self._result=None
        self._thread=threading.Thread(target=self._run,daemon=True); self._thread.start()

    def poll(self):
        with self._lock: return self._result

    def cancel(self):
        with self._lock:
            if self._result is not None: return False
            self._cancel.set(); return True

    def wait_closed(self, timeout=1):
        return self._done.wait(timeout) and self.poll().cleanup_complete

    def _run(self):
        started=time.monotonic(); proc=None; protocol=None; disposition='start_failed'
        try:
            if self._cancel.is_set(): raise _Stop('cancelled')
            protocol=_Protocol(self._prepared,self._cwd,self._provider_id)
            proc=subprocess.Popen(self._command,cwd=self._cwd,env=self._environment,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            for pipe in (proc.stdin,proc.stdout,proc.stderr): os.set_blocking(pipe.fileno(),False)
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
                selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
                selector.register(proc.stdin,selectors.EVENT_WRITE,'stdin')
                outgoing=bytearray(protocol.start()); incoming=bytearray(); counts={'stdout':0,'stderr':0}; events=0
                while not protocol.finished:
                    if self._cancel.is_set(): raise _Stop('cancelled')
                    if time.monotonic()-started>=self._seconds: raise _Stop('timed_out')
                    for key,_ in selector.select(.05):
                        channel=key.data
                        if channel=='stdin':
                            if outgoing:
                                try: written=os.write(key.fd,outgoing)
                                except BlockingIOError: continue
                                del outgoing[:written]
                            if not outgoing: selector.unregister(proc.stdin)
                            continue
                        try: part=os.read(key.fd,8192)
                        except BlockingIOError: continue
                        if not part:
                            selector.unregister(key.fileobj)
                            if channel=='stdout': raise _Stop('client_failed')
                            continue
                        counts[channel]+=len(part)
                        if counts[channel]>(MAX_STDOUT if channel=='stdout' else MAX_STDERR): raise _Stop('response_too_large')
                        if channel=='stderr': continue
                        incoming.extend(part)
                        while b'\n' in incoming:
                            line,_,rest=incoming.partition(b'\n'); incoming=bytearray(rest)
                            events+=1
                            if len(line)>MAX_LINE or events>MAX_EVENTS: raise _Stop('response_too_large')
                            message=_json(bytes(line))
                            if protocol.finished and message.get('method') not in PASSIVE_EVENTS:
                                raise _Stop('policy_refused' if 'id' in message and 'method' in message else 'protocol_error')
                            outgoing.extend(protocol.receive(message))
                            if outgoing and proc.stdin not in [k.fileobj for k in selector.get_map().values()]:
                                selector.register(proc.stdin,selectors.EVENT_WRITE,'stdin')
                        if len(incoming)>MAX_LINE: raise _Stop('response_too_large')
                disposition='completed'
        except _Stop as error: disposition=error.disposition
        except Exception:
            disposition='protocol_error' if proc is not None else 'start_failed'
        finally:
            # Always terminate the owned group, including children whose leader
            # already exited. Never retain stderr, RPC input or account email.
            cleanup_complete=True
            if proc is not None:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                except OSError: cleanup_complete=False
                try: proc.wait(timeout=2)
                except (OSError,subprocess.TimeoutExpired): cleanup_complete=False
                for pipe in (proc.stdin,proc.stdout,proc.stderr):
                    try: pipe.close()
                    except OSError: cleanup_complete=False
            with self._lock:
                if not cleanup_complete: disposition='client_failed'
                if self._cancel.is_set(): disposition='cancelled'
                completed=disposition=='completed'
                self._result=CodexResult(self._prepared.review.request_id,self._prepared.digest,disposition,
                    max(0,int((time.monotonic()-started)*1000)),
                    protocol.response_digest if protocol is not None else None,
                    protocol.typed if completed else None,
                    self._prepared.profile.value['model'] if completed else None,
                    protocol.client_version if protocol is not None else None,
                    protocol.thread_id if protocol is not None else None,
                    protocol.turn_id if protocol is not None else None,cleanup_complete,
                    protocol.failure if protocol is not None else None)
                self._done.set()


class CodexAppServerTransport:
    """Internal owned-command seam; not a public trust switch or launcher policy.

    A digest binds application input, not CLI-generated HTTP destinations/body.
    Deployment qualification must happen outside this adapter before real use.
    Ordinary research/private profile files cannot instantiate this live owner.
    """
    def __init__(self, command, *, cwd, environment, total_seconds=POLICY['total_seconds'], provider_id='openai'):
        if (type(command) is not tuple or not command or any(type(v) is not str or not v or '\0' in v for v in command)
                or type(environment) is not dict or any(type(k) is not str or type(v) is not str
                    or '\0' in k+v for k,v in environment.items())
                or isinstance(total_seconds,bool) or not isinstance(total_seconds,(int,float))
                or not math.isfinite(total_seconds) or not 0<total_seconds<=POLICY['total_seconds']
                or type(provider_id) is not str or provider_id not in ('openai','claimbranch-chatgpt')):
            raise ContractError('Explicit bounded internal client command/environment required.')
        self._command, self._cwd, self._environment = command, Path(cwd).resolve(strict=True), dict(environment)
        self._provider_id=provider_id
        self._seconds=total_seconds; self._jobs=[]; self._ids=set(); self._nonces=set()
        self._closed=False; self._lock=threading.Lock(); atexit.register(self._exit)

    def start(self, prepared, *, confirmed_digest, current_profile, current_context, now):
        # Like the existing API/offline boundaries, now is the trusted owner's
        # current review-clock epoch. Serialized/model-supplied time is invalid
        # at application dispatch; this internal library mints no human consent.
        if type(prepared) is not PreparedCodexRequest or confirmed_digest!=prepared.digest:
            raise ContractError('Explicit confirmation of the exact selected Codex input is required.')
        prepared.recheck(current_profile,current_context,now=now)
        with self._lock:
            if self._closed or len(self._ids)>=TRANSPORT_START_LIMIT:
                raise ContractError('Transport closed or session request limit reached; continue manually.')
            review=prepared.review
            if review.request_id in self._ids or review.nonce in self._nonces:
                raise ContractError('A Codex request and nonce can be dispatched only once.')
            self._ids.add(review.request_id); self._nonces.add(review.nonce)
            job=CodexJob(prepared,self._command,self._cwd,self._environment,self._seconds,self._provider_id)
            self._jobs.append(job); return job

    def close(self):
        with self._lock: self._closed=True; jobs=tuple(self._jobs)
        for job in jobs: job.cancel()

    def _exit(self):
        self.close()
        self.wait_closed(3)

    def wait_closed(self, timeout=1):
        deadline=time.monotonic()+timeout
        with self._lock: jobs=tuple(self._jobs)
        closed=[job.wait_closed(max(0,deadline-time.monotonic())) for job in jobs]
        if all(closed) and self._closed: atexit.unregister(self._exit)
        return all(closed)
