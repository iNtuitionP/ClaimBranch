"""Owned stdio peers only; protocol checks do not qualify a deployment."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.application.provider_profile import CodexProfile, prepare_codex_request
from claimbranch.application.codex_app_server import CodexAppServerTransport, _failure
from tests.application.test_paper_proposals import context, response


PEER = r'''
import json, os, sys, time
case=os.environ.get('CB_CASE','ok')
if os.environ.get('CB_PID_FILE'):
 with open(os.environ['CB_PID_FILE'],'w') as f: f.write(str(os.getpid()))
answer=json.loads(os.environ['CB_ANSWER'])
def send(value):
 print(json.dumps(value,separators=(',',':')),flush=True)
def reply(msg,value): send({'id':msg['id'],'result':value})
for line in sys.stdin:
 msg=json.loads(line); method=msg['method']; p=msg.get('params',{})
 if method=='initialize':
  assert p['capabilities']['optOutNotificationMethods']==['item/agentMessage/delta','item/reasoning/textDelta','item/reasoning/summaryTextDelta','item/reasoning/summaryPartAdded']
  reply(msg,{'platformOs':'macos','platformFamily':'unix','userAgent':'codex/0.158.0','codexHome':'not-retained'})
  send({'method':'remoteControl/status/changed','params':{'status':'connecting' if case=='remote' else 'disabled','environmentId':None,'installationId':'not-retained','serverName':'not-retained'},'emittedAtMs':1})
 elif method=='initialized': pass
 elif method=='getAuthStatus':
  assert p=={'includeToken':False,'refreshToken':False}
  value={'authMethod':'chatgpt','authToken':None,'requiresOpenaiAuth':True}
  if case=='auth-status-token': value['authToken']='not-requested-secret'
  if case=='auth-status-api': value['authMethod']='apikey'
  if case=='auth-status-null': value['authMethod']=None
  if case=='auth-status-required': value['requiresOpenaiAuth']=1
  if case=='auth-status-extra': value['instructions']='untrusted'
  reply(msg,value)
 elif method=='account/read':
  if case=='rpc-error':
   send({'id':msg['id'],'error':{'code':-32602,'message':'private-token /private/research','data':{'instructions':'untrusted'}}})
   continue
  if case.startswith('account-update'):
   mode={'account-update-api':'apikey','account-update-none':None}.get(case,'chatgpt')
   params={'authMode':mode,'planType':'plus'}
   if case=='account-update-extra': params['instructions']='untrusted'
   send({'method':'account/updated','params':params})
  reply(msg,{'account':None if case=='auth' else {'type':'chatgpt','email':'not-retained@example.test','planType':'plus'},'requiresOpenaiAuth':True})
 elif method=='model/list':
  assert p=={'limit':100,'includeHidden':True}
  row={'id':'gpt-6.1-sol','model':'gpt-6.1-sol','inputModalities':['text'],
       'supportedReasoningEfforts':[{'reasoningEffort':'medium','description':'not retained'}]}
  value={'data':[row],'nextCursor':None}
  if case=='catalog-missing': value['data']=[]
  if case=='catalog-duplicate': value['data']=[row,row]
  if case=='catalog-aliased': row['model']='another-model'
  if case=='catalog-effort': row['supportedReasoningEfforts']=[{'reasoningEffort':'low','description':'not retained'}]
  if case=='catalog-modality': row['inputModalities']=['image']
  if case=='catalog-page': value['nextCursor']='unread-page'
  if case=='catalog-malformed': value['data']={}
  if case=='catalog-extra': value['instructions']='untrusted'
  if case=='catalog-no-cursor': value.pop('nextCursor')
  if case=='catalog-older': row.pop('inputModalities')
  reply(msg,value)
 elif method=='thread/start':
  provider=os.environ.get('CB_PROVIDER','openai')
  assert p['modelProvider']==provider and p['config']['model_provider']==provider
  assert p['ephemeral'] is True and p['environments']==[] and p['dynamicTools']==[]
  assert p['approvalPolicy']=='never' and p['sandbox']=='read-only'
  assert p['runtimeWorkspaceRoots']==[] and p['selectedCapabilityRoots']==[]
  assert p['allowProviderModelFallback'] is False
  value={'thread':{'id':'thread-owned','cliVersion':'0.158.0','ephemeral':True,'cwd':os.getcwd(),'model':p['model'],'modelProvider':provider,'environments':[]},
    'cwd':os.getcwd(),'model':p['model'],'modelProvider':provider,'approvalPolicy':'never','approvalsReviewer':'user',
    'sandbox':{'type':'readOnly','networkAccess':False},'instructionSources':[],'runtimeWorkspaceRoots':[]}
  if case=='model': value['model']='fallback'
  if case=='provider': value['modelProvider']='fallback'
  if case=='provider-builtin': value['modelProvider']='openai'
  if case=='thread-provider': value['thread']['modelProvider']='openai'
  if case=='version': value['thread']['cliVersion']='0.160.0'
  if case=='instructions': value['instructionSources']=[{'path':'unselected.md'}]
  if case=='policy': value['sandbox']['networkAccess']=True
  if case=='duplicate':
   print('{"id":'+str(msg['id'])+',"result":{},"result":'+json.dumps(value)+'}',flush=True)
  else: reply(msg,value)
 elif method=='turn/start':
  if case=='late-account-update': send({'method':'account/updated','params':{'authMode':'chatgpt','planType':'plus'}})
  assert p['environments']==[] and p['approvalPolicy']=='never'
  assert p['sandboxPolicy']=={'type':'readOnly','networkAccess':False}
  assert p['input'][0]['type']=='text'
  if case.startswith('advice'): assert p['outputSchema'] is None
  else: assert p['outputSchema']['properties']['schema']=={'type':'string','enum':['claimbranch.provider-result/v2']}
  selected=json.loads(p['input'][0]['text'])
  assert selected['context_digest']==os.environ['CB_CONTEXT']
  assert selected['request_id']==os.environ['CB_REQUEST']
  reply(msg,{'turn':{'id':'turn-owned','status':'inProgress','items':[]}})
  if case.startswith('error-'):
   error={'message':'private-token /private/research','additionalDetails':'untrusted instructions',
    'codexErrorInfo':{'httpConnectionFailed':{'httpStatusCode':400,'private':'private-token'}}}
   if case=='error-unknown': error['codexErrorInfo']='private-token'
   if case=='error-bool-status': error['codexErrorInfo']['httpConnectionFailed']['httpStatusCode']=True
   send({'method':'error','params':{'threadId':'thread-other' if case=='error-foreign' else 'thread-owned',
    'turnId':'turn-owned','willRetry':True if case=='error-retry' else False,'error':error}})
   continue
  if case.startswith('settings'):
   settings={'activePermissionProfile':None,'approvalPolicy':'never','approvalsReviewer':'user',
    'collaborationMode':{'mode':'default','settings':{'developer_instructions':None,'model':p['model'],'reasoning_effort':p['effort']}},
    'cwd':os.getcwd(),'disabledPluginIds':[],'effort':p['effort'],'model':p['model'],
    'modelProvider':os.environ.get('CB_PROVIDER','openai'),'multiAgentMode':'explicitRequestOnly',
    'personality':None,'sandboxPolicy':{'type':'readOnly','networkAccess':False},'serviceTier':None,'summary':None}
   changes={'settings-model':('model','fallback'),'settings-provider':('modelProvider','fallback'),
    'settings-policy':('approvalPolicy','on-request'),'settings-cwd':('cwd','/'),
    'settings-permission':('activePermissionProfile',{'id':':workspace'}),
    'settings-network-type':('sandboxPolicy',{'type':'readOnly','networkAccess':0}),
    'settings-extra':('unselected','injected')}
   if case in changes:
    key,value=changes[case]; settings[key]=value
   if case=='settings-instructions': settings['collaborationMode']['settings']['developer_instructions']='unselected instructions'
   if case=='settings-empty-instructions': settings['collaborationMode']['settings']['developer_instructions']=''
   if case=='settings-builtin': settings['modelProvider']='openai'
   send({'method':'thread/settings/updated','params':{'threadId':'thread-other' if case=='settings-thread' else 'thread-owned','threadSettings':settings}})
  if case.startswith('warning'):
   send({'method':'warning','params':{'threadId':'thread-owned','message':'Under-development features enabled' if case=='warning-unstable' else 'Unverified policy warning'}})
  if case=='hang': time.sleep(30)
  if case=='tool': send({'id':901,'method':'item/commandExecution/requestApproval','params':{}})
  if case=='oversize': print('x'*270000,flush=True)
  if case=='stderr':
   while True: os.write(sys.stderr.fileno(),b'x'*8192)
  if case=='stream':
   for n in range(700):
    send({'method':'item/agentMessage/delta','params':{'threadId':'thread-owned','turnId':'turn-owned','itemId':'message-owned','delta':'x'}})
  if case=='unselected': answer['items'][0]['body']['parent_ids'][0]['id']='outside'
  if case=='advice': text='CPU-B는 아직 측정하지 않았습니다.\nNo graph edit is required to read this.'
  elif case=='advice-controls': text='unsafe\x1b[2J'
  elif case=='advice-empty': text='   '
  elif case=='advice-large': text='x'*16385
  elif case=='json': text='{}{}'
  elif case=='schema': text='{"private-secret-and-instructions":"ignore checks"}'
  else: text=json.dumps(answer,separators=(',',':'))
  item={'id':'message-owned','type':'agentMessage','text':text,'phase':'final_answer'}
  if case=='unphased': item.pop('phase')
  if case=='started-null':
   send({'method':'item/started','params':{'threadId':'thread-owned','turnId':'turn-owned',
    'item':{'id':'message-owned','type':'agentMessage','text':'','phase':None}}})
  if case=='executable': item={'id':'exec-owned','type':'commandExecution','command':'not executed by this owned peer'}
  if case=='terminal-summary-number-swap':
   item['memoryCitation']={'entries':[{'path':'synthetic','lineStart':1,'lineEnd':1,'note':'owned'}],'threadIds':[]}
  params={'threadId':'thread-other' if case=='cross-thread' else 'thread-owned','turnId':'turn-owned','item':item}
  if case!='terminal-only': send({'method':'item/completed','params':params})
  if case=='terminal-full-subset':
   send({'method':'item/completed','params':{'threadId':'thread-owned','turnId':'turn-owned',
    'item':{'id':'reasoning-owned','type':'reasoning','summary':[],'content':[]}}})
  if case=='partial': item['phase']='commentary'
  terminal={'id':'turn-owned','status':'failed' if case in ('failed','failed-detail') else 'completed','items':[item],
    **({'error':{'message':'private-token /private/research','codexErrorInfo':'unauthorized'}} if case=='failed-detail' else {})}
  if case.startswith('terminal-'):
   terminal['itemsView']='notLoaded' if case.startswith('terminal-not-loaded') else 'summary'
   if case in ('terminal-summary-empty','terminal-not-loaded'): terminal['items']=[]
   if case=='terminal-summary-foreign': terminal['items'][0]['id']='foreign'
   if case=='terminal-summary-changed': terminal['items'][0]['text']='different'
   if case=='terminal-summary-duplicate': terminal['items'].append(dict(item))
   if case=='terminal-summary-number-swap': terminal['items'][0]['memoryCitation']['entries'][0]['lineStart']=True
   if case.startswith('terminal-full-'): terminal['itemsView']='full'
   if case=='terminal-full-empty': terminal['items']=[]
   if case=='terminal-view-unknown': terminal['itemsView']='unreviewed'
   if case=='terminal-no-items': terminal.pop('items')
  send({'method':'turn/completed','params':{'threadId':params['threadId'],'turn':terminal}})
'''


class CodexAppServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claimbranch-codex-rpc-')
        self.addCleanup(self.temp.cleanup)
        self.profile = CodexProfile.create(model='gpt-6.1-sol')
        self.context = context()
        self.prepared = prepare_codex_request(self.profile, self.context,
            request_id='request-owned', nonce='nonce-owned', now=100)

    def transport(self, case='ok', *, timeout=2, provider_id='openai'):
        env={'PATH':'/usr/bin:/bin','CB_CASE':case,'CB_ANSWER':json.dumps(response()),
            'CB_CONTEXT':self.context.digest,'CB_REQUEST':self.prepared.review.request_id,
            'CB_PID_FILE':str(Path(self.temp.name)/'owned-peer-pid'),'CB_PROVIDER':provider_id}
        transport=CodexAppServerTransport((sys.executable,'-I','-c',PEER),
            cwd=Path(self.temp.name), environment=env, total_seconds=timeout, provider_id=provider_id)
        self.addCleanup(transport.close)
        self.addCleanup(lambda: transport.wait_closed(3))
        return transport

    def start(self, transport, *, prepared=None, confirmed=None, now=100):
        prepared=prepared or self.prepared
        return transport.start(prepared, confirmed_digest=confirmed or prepared.digest,
            current_profile=self.profile,current_context=self.context,now=now)

    def result(self, case):
        job=self.start(self.transport(case))
        self.assertTrue(job.wait_closed(3))
        return job.poll()

    def test_exact_context_result_reaches_existing_typed_ingress(self):
        result=self.result('ok')
        self.assertEqual('completed',result.disposition)
        self.assertEqual(response(),decode(result.typed_result))
        self.assertEqual(self.prepared.digest,result.request_digest)
        self.assertEqual('gpt-6.1-sol',result.reported_model)
        self.assertEqual('0.158.0',result.client_version)
        self.assertEqual('thread-owned',result.thread_id)
        self.assertEqual('turn-owned',result.turn_id)
        self.assertNotIn(b'not-retained',canonical_bytes(result.metadata()))

    def test_plain_advice_is_independent_from_graph_json(self):
        self.prepared=prepare_codex_request(self.profile,self.context,
            request_id='request-owned',nonce='nonce-owned',now=100,
            discussion={'prompt':'어떤 점이 불확실한가요?', 'previous':[]})
        result=self.result('advice')
        self.assertEqual('completed',result.disposition)
        value=decode(result.typed_result)
        self.assertEqual({'schema','status','text'},set(value))
        self.assertIn('CPU-B는',value['text'])
        for case in ('advice-controls','advice-empty','advice-large'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('malformed_response',result.disposition)
                self.assertIsNone(result.typed_result)

    def test_owned_error_retains_only_reported_category_status_and_retry(self):
        for case,retry in (('error-http',False),('error-retry',True)):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('client_failed',result.disposition)
                self.assertIsNone(result.typed_result)
                self.assertEqual({'category':'httpConnectionFailed','http_status':400,
                    'client_reports_retry':retry},result.failure.metadata())
                self.assertNotIn('failure',result.metadata())
                self.assertNotIn(b'private-token',canonical_bytes(result.failure.metadata()))

    def test_unknown_or_foreign_error_cannot_leak_details_or_fake_http_status(self):
        unknown=self.result('error-unknown')
        self.assertEqual({'category':'unclassified','client_reports_retry':False},unknown.failure.metadata())
        boolean=self.result('error-bool-status')
        self.assertEqual({'category':'httpConnectionFailed','client_reports_retry':False},boolean.failure.metadata())
        self.assertIsNone(self.result('error-foreign').failure)

    def test_failed_turn_retains_category_without_supplying_a_proposal(self):
        result=self.result('failed-detail')
        self.assertEqual('client_failed',result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertEqual({'category':'unauthorized'},result.failure.metadata())
        self.assertNotIn('failure',result.metadata())

    def test_matching_rpc_failure_keeps_standard_code_without_raw_data(self):
        result=self.result('rpc-error')
        self.assertEqual('client_failed',result.disposition)
        self.assertEqual({'category':'rpcError','rpc_code':-32602},result.failure.metadata())
        self.assertIsNone(result.thread_id)
        self.assertNotIn(b'private-token',canonical_bytes(result.metadata()))

    def test_structured_non_http_failure_discards_continuation_instructions(self):
        result=_failure({'codexErrorInfo':{'activeTurnNotSteerable':{'turnKind':'review',
            'instructions':'private-token'}},'message':'private-token'},retry='true')
        self.assertEqual({'category':'activeTurnNotSteerable'},result.metadata())

    def test_json_error_message_keeps_only_known_service_code(self):
        error={'codexErrorInfo':'other','message':json.dumps({'error':{
            'code':'invalid_json_schema','message':'private-token /private/research',
            'param':'untrusted','instructions':'untrusted'}})}
        result=_failure(error,retry=False)
        self.assertEqual({'category':'other','client_reports_retry':False,
            'service_error_code':'invalid_json_schema'},result.metadata())
        self.assertNotIn('private-token',json.dumps(result.metadata()))
        for text in ('private-token','\ud800','[]','1','['*34+'0'+']'*34,
                     json.dumps({'error':{'code':'private-token'}}),
                     '{"error":{"code":"invalid_json_schema","code":"private-token"}}',
                     json.dumps({'error':{'code':True}}),
                     json.dumps({'error':{'code':'invalid_json_schema','message':'x'*16384}})):
            with self.subTest(text_length=len(text)):
                self.assertEqual({'category':'other'},_failure({'codexErrorInfo':'other','message':text}).metadata())

    def test_generation_subset_does_not_relax_received_scientific_validation(self):
        for field,value in (('id','invalid id'),('scope','x'*16385)):
            answer=response()
            if field=='id': answer['items'][0]['id']=value
            else: answer['items'][0]['body'][field]=value
            with patch(f'{__name__}.response',return_value=answer):
                transport=self.transport()
            job=self.start(transport)
            self.assertTrue(job.wait_closed(3))
            self.assertEqual('malformed_response',job.poll().disposition)
            self.assertIsNone(job.poll().typed_result)

    def test_streamed_notifications_do_not_preempt_an_ordinary_typed_reply(self):
        self.assertEqual('completed',self.result('stream').disposition)

    def test_terminal_display_view_uses_owned_completed_items(self):
        for case in ('terminal-summary','terminal-summary-empty','terminal-not-loaded'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('completed',result.disposition)
                self.assertEqual(response(),decode(result.typed_result))
        for case in ('terminal-summary-foreign','terminal-summary-changed',
                     'terminal-not-loaded-with-items','terminal-view-unknown','terminal-no-items',
                     'terminal-summary-duplicate','terminal-summary-number-swap',
                     'terminal-full-empty','terminal-full-subset','terminal-only'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('protocol_error',result.disposition)
                self.assertIsNone(result.typed_result)

    def test_optional_phase_and_incomplete_started_item_follow_installed_schema(self):
        for case in ('unphased','started-null'):
            with self.subTest(case=case): self.assertEqual('completed',self.result(case).disposition)

    def test_internal_chatgpt_alias_is_bound_without_silently_normalizing_provider_echo(self):
        job=self.start(self.transport(provider_id='claimbranch-chatgpt'))
        self.assertTrue(job.wait_closed(3))
        self.assertEqual('completed',job.poll().disposition)
        for case in ('provider','provider-builtin','thread-provider','settings-builtin'):
            with self.subTest(case=case):
                job=self.start(self.transport(case,provider_id='claimbranch-chatgpt'))
                self.assertTrue(job.wait_closed(3))
                self.assertEqual('policy_refused',job.poll().disposition)
                self.assertIsNone(job.poll().typed_result)

    def test_exact_relay_auth_check_never_exports_token_or_refreshes_login(self):
        for case in ('auth-status-token','auth-status-api','auth-status-null','auth-status-required','auth-status-extra'):
            with self.subTest(case=case):
                job=self.start(self.transport(case,provider_id='claimbranch-chatgpt'))
                self.assertTrue(job.wait_closed(3))
                self.assertEqual('auth_required',job.poll().disposition)
                self.assertIsNone(job.poll().thread_id)
                self.assertIsNone(job.poll().typed_result)

    def test_unrecognized_provider_alias_refuses_before_any_child(self):
        with patch('claimbranch.application.codex_app_server.CodexJob') as job:
            with self.assertRaises(ContractError): self.transport(provider_id='unreviewed')
            job.assert_not_called()

    def test_explicit_thread_configuration_suppresses_its_own_experimental_feature_warning(self):
        from claimbranch.application.codex_app_server import _Protocol
        protocol=_Protocol(self.prepared,Path(self.temp.name))
        protocol.pending=2
        catalog=json.loads(protocol.receive({'id':2,'result':{'account':{'type':'chatgpt'}}}))
        self.assertEqual('model/list',catalog['method'])
        request=json.loads(protocol.receive({'id':5,'result':{'data':[{
            'id':'gpt-6.1-sol','model':'gpt-6.1-sol','inputModalities':['text'],
            'supportedReasoningEfforts':[{'reasoningEffort':'medium'}]}],'nextCursor':None}}))
        self.assertIs(True,request['params']['config'].get('suppress_unstable_features_warning'))

    def test_model_and_effort_must_be_advertised_before_thread_or_turn(self):
        for case in ('catalog-missing','catalog-duplicate','catalog-aliased',
                'catalog-effort','catalog-modality','catalog-page'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('policy_refused',result.disposition)
                self.assertIsNone(result.thread_id)
                self.assertIsNone(result.turn_id)
                self.assertIsNone(result.typed_result)
                self.assertIsNone(result.reported_model)
        for case in ('catalog-malformed','catalog-extra','catalog-no-cursor'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('protocol_error',result.disposition)
                self.assertIsNone(result.thread_id)

    def test_older_catalog_without_modalities_keeps_scoped_typed_return(self):
        result=self.result('catalog-older')
        self.assertEqual('completed',result.disposition)
        self.assertIsNotNone(result.typed_result)
        self.assertEqual('thread-owned',result.thread_id)
        self.assertEqual('turn-owned',result.turn_id)

    def test_mac_file_policy_preserves_loader_access_without_allowing_root_descendants(self):
        from claimbranch.application.codex_app_server import mac_codex_policy
        policy=mac_codex_policy('/opt/owned/codex','/private/tmp/claimbranch-codex-owned')
        self.assertIn('(deny file-read*)',policy)
        self.assertIn('(allow file-read-data (literal "/"))',policy)
        self.assertNotIn('(subpath "/")',policy)
        self.assertNotIn('(subpath "/System")',policy)
        self.assertIn('(deny network*)',policy)
        self.assertNotIn('network-outbound',policy)
        self.assertIn('(deny process-exec)',policy)

    def test_mac_policy_binds_only_the_explicit_credential_and_proxy_port(self):
        from claimbranch.application.codex_app_server import mac_codex_policy
        policy=mac_codex_policy('/opt/owned/codex','/private/tmp/claimbranch-codex-owned',
            credential_file='/Users/owned/.codex/auth.json',proxy_port=32123)
        self.assertIn('(remote tcp "localhost:32123")',policy)
        self.assertIn('(literal "/Users/owned/.codex/auth.json")',policy)
        self.assertNotIn('(subpath "/Users/owned")',policy)
        self.assertIn('(deny file-write*)',policy)
        self.assertNotIn('(allow file-write* (literal "/Users/owned/.codex/auth.json"))',policy)

    def test_mac_policy_closes_mach_lookup_and_authorization_except_observed_os_services(self):
        from claimbranch.application.codex_app_server import mac_codex_policy
        policy=mac_codex_policy('/opt/owned/codex','/private/tmp/claimbranch-codex-owned')
        self.assertIn('(deny mach-lookup)',policy)
        self.assertIn('(deny authorization-right-obtain)',policy)
        self.assertNotIn('(allow mach-lookup)',policy)
        import re
        exceptions=[line for line in policy.splitlines() if line.startswith('(allow mach-lookup ')]
        observed={'com.apple.cfprefsd.daemon','com.apple.cfprefsd.agent',
            'com.apple.SecurityServer','com.apple.trustd.agent'}
        self.assertEqual(observed,set(re.findall(r'\(global-name "([^"]+)"\)', '\n'.join(exceptions))))
        self.assertNotIn('local-name','\n'.join(exceptions))
        self.assertEqual(4,len(exceptions))
        for exception in exceptions:
            self.assertLess(policy.index('(deny mach-lookup)'),policy.index(exception))
        after_rights_denial=policy.split('(deny authorization-right-obtain)',1)[1]
        self.assertFalse(any(line.startswith('(allow ') and 'authorization' in line
            for line in after_rights_denial.splitlines()))
        for forbidden in ('name-prefix','regex','com.apple.securityd.xpc',
                'com.apple.CoreAuthentication.daemon','org.claimbranch'):
            self.assertNotIn(forbidden,'\n'.join(exceptions))

    def test_mac_policy_refuses_broad_or_ambiguous_paths_and_network_exceptions(self):
        from claimbranch.application.codex_app_server import mac_codex_policy
        for root in ('/','/private/tmp','/Users/owned','relative','/private/tmp/claimbranch-codex-a/../b'):
            with self.subTest(root=root), self.assertRaises(ContractError):
                mac_codex_policy('/opt/owned/codex',root)
        for port in (0,65536,True,'443'):
            with self.subTest(port=port), self.assertRaises(ContractError):
                mac_codex_policy('/opt/owned/codex','/private/tmp/claimbranch-codex-owned',proxy_port=port)
        for client,credential in [('relative',None),('/opt/owned/cli\n)',None),
                ('/private/tmp/claimbranch-codex-owned/client',None),('/opt/owned/codex','/'),
                ('/opt/owned/codex','/private/tmp/claimbranch-codex-owned/auth.json')]:
            with self.subTest(client=client,credential=credential), self.assertRaises(ContractError):
                mac_codex_policy(client,'/private/tmp/claimbranch-codex-owned',credential_file=credential)

    def test_observed_thread_settings_must_preserve_the_exact_turn_policy(self):
        self.assertEqual('completed',self.result('settings').disposition)
        for case,expected in [('settings-thread','protocol_error'),('settings-extra','protocol_error'),
                *[(name,'policy_refused') for name in ('settings-model','settings-provider','settings-policy',
                    'settings-cwd','settings-permission','settings-network-type','settings-instructions','settings-empty-instructions')]]:
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual(expected,result.disposition)
                self.assertIsNone(result.typed_result)

    def _normal_exit(self, close_first=False):
        import claimbranch
        package_root=Path(claimbranch.__file__).resolve().parent.parent
        test_root=Path(__file__).resolve().parents[2]
        pid_file=Path(self.temp.name)/'exit-peer-pid'
        script='''
import sys,os,json,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.path.append(sys.argv[2])
from claimbranch.application.codex_app_server import CodexAppServerTransport
from claimbranch.application.provider_profile import CodexProfile,prepare_codex_request
from tests.application.test_paper_proposals import context,response
ctx=context();profile=CodexProfile.create(model='gpt-6.1-sol')
prepared=prepare_codex_request(profile,ctx,request_id='request-owned',nonce='nonce-owned',now=100)
env={'PATH':'/usr/bin:/bin','CB_CASE':'hang','CB_ANSWER':json.dumps(response()),'CB_CONTEXT':ctx.digest,
 'CB_REQUEST':'request-owned','CB_PID_FILE':sys.argv[3]}
transport=CodexAppServerTransport((sys.executable,'-I','-c',sys.argv[4]),cwd=Path(sys.argv[3]).parent,environment=env)
transport.start(prepared,confirmed_digest=prepared.digest,current_profile=profile,current_context=ctx,now=100)
deadline=time.monotonic()+2
while not Path(sys.argv[3]).exists() and time.monotonic()<deadline: time.sleep(.01)
assert Path(sys.argv[3]).exists()
if len(sys.argv)>5: transport.close()
'''
        owner=subprocess.run([sys.executable,'-I','-c',script,str(package_root),str(test_root),str(pid_file),PEER,
                              *(['close'] if close_first else [])],
            capture_output=True,timeout=6)
        self.assertEqual(0,owner.returncode)
        pid=int(pid_file.read_text()); alive=True; deadline=time.monotonic()+1
        while alive and time.monotonic()<deadline:
            try: os.kill(pid,0)
            except ProcessLookupError: alive=False
            if alive: time.sleep(.01)
        if alive: os.kill(pid,9)
        self.assertFalse(alive,'normal owner exit left its owned client running')

    def test_normal_interpreter_exit_cleans_up_its_owned_client(self):
        self._normal_exit()

    def test_interpreter_exit_waits_even_after_nonblocking_close(self):
        self._normal_exit(close_first=True)

    def test_uncertain_reaping_is_visible_and_cannot_report_cleanup_success(self):
        with patch('claimbranch.application.codex_app_server.subprocess.Popen.wait',
                   side_effect=subprocess.TimeoutExpired('owned peer',2)):
            job=self.start(self.transport())
            self.assertTrue(job._done.wait(3))
        self.assertFalse(job.wait_closed(.1))
        self.assertFalse(job.poll().cleanup_complete)
        self.assertEqual('client_failed',job.poll().disposition)
        self.assertIsNone(job.poll().typed_result)

    def test_unexpected_decoder_exception_returns_failure_without_raw_diagnostics(self):
        with patch('claimbranch.application.codex_app_server.provider_typed_result',side_effect=RuntimeError('private input')):
            result=self.result('ok')
        self.assertEqual('protocol_error',result.disposition)
        self.assertIsNone(result.typed_result)

    def test_no_launch_before_exact_current_unexpired_confirmation(self):
        transport=self.transport()
        for prepared,confirmed,now in [(self.prepared,'0'*64,100),
                (replace(self.prepared,body=b'{}'),self.prepared.digest,100),
                (self.prepared,self.prepared.digest,220)]:
            with self.assertRaises(ContractError): self.start(transport,prepared=prepared,confirmed=confirmed,now=now)
        self.assertEqual([],transport._jobs)

    def test_replay_closed_owner_and_attempt_budget(self):
        transport=self.transport(); first=self.start(transport)
        with self.assertRaises(ContractError): self.start(transport)
        self.assertTrue(first.wait_closed(3))
        transport.close()
        other=prepare_codex_request(self.profile,self.context,request_id='another',nonce='another',now=100)
        with self.assertRaises(ContractError): self.start(transport,prepared=other)

    def test_attempt_budget_includes_failed_dispatches_and_reused_nonce(self):
        transport=self.transport()
        with patch('claimbranch.application.codex_app_server.CodexJob') as job:
            for i in range(3):
                prepared=prepare_codex_request(self.profile,self.context,
                    request_id='request-'+str(i),nonce='nonce-'+str(i),now=100)
                self.start(transport,prepared=prepared)
            fourth=prepare_codex_request(self.profile,self.context,request_id='fourth',nonce='fourth',now=100)
            with self.assertRaises(ContractError): self.start(transport,prepared=fourth)
            self.assertEqual(3,job.call_count)
        transport=self.transport()
        with patch('claimbranch.application.codex_app_server.CodexJob'):
            self.start(transport)
            duplicate=prepare_codex_request(self.profile,self.context,request_id='different',nonce='nonce-owned',now=100)
            with self.assertRaises(ContractError): self.start(transport,prepared=duplicate)

    def test_policy_model_version_and_ambient_instructions_fail_before_turn(self):
        for case in ('model','version','instructions','policy'):
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual('policy_refused',result.disposition)
                self.assertIsNone(result.typed_result)
                self.assertIsNone(result.turn_id)

    def test_missing_login_returns_no_proposal_or_account_identity(self):
        result=self.result('auth')
        self.assertEqual('auth_required',result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertIsNone(result.thread_id)
        self.assertEqual('policy_refused',self.result('remote').disposition)

    def test_observed_chatgpt_account_notification_does_not_block_account_control(self):
        result=self.result('account-update')
        self.assertEqual('completed',result.disposition)
        self.assertNotIn(b'plus',canonical_bytes(result.metadata()))
        self.assertNotIn(b'not-retained',canonical_bytes(result.metadata()))

    def test_account_notification_cannot_change_authentication_or_inject_fields(self):
        for case,expected in [('account-update-api','auth_required'),
                ('account-update-none','auth_required'),('account-update-extra','protocol_error'),
                ('late-account-update','policy_refused')]:
            with self.subTest(case=case):
                result=self.result(case)
                self.assertEqual(expected,result.disposition)
                self.assertIsNone(result.typed_result)

    def test_tool_requests_and_executable_items_are_never_results(self):
        for case in ('tool','executable'):
            with self.subTest(case=case): self.assertEqual('policy_refused',self.result(case).disposition)

    def test_duplicate_json_wrong_context_partial_and_failed_turn_refuse(self):
        for case in ('duplicate','cross-thread','partial','warning-unstable','warning-other'):
            with self.subTest(case=case): self.assertEqual('protocol_error',self.result(case).disposition)
        for case in ('json','unselected'):
            with self.subTest(case=case): self.assertEqual('malformed_response',self.result(case).disposition)
        self.assertEqual('client_failed',self.result('failed').disposition)

    def test_typed_refusal_reports_safe_stage_without_payload(self):
        for case, category in (('json', 'proposal_json'), ('schema', 'proposal_schema'),
                ('unselected', 'proposal_reference')):
            with self.subTest(case=case):
                result = self.result(case)
                self.assertEqual('malformed_response', result.disposition)
                self.assertEqual({'category': category}, result.failure.metadata())
                self.assertNotIn('failure', result.metadata())
                self.assertIsNone(result.typed_result)

    def test_unknown_validator_detail_never_becomes_diagnostic(self):
        from claimbranch.application.codex_app_server import _proposal_failure
        failure = _proposal_failure(canonical_bytes(response()), ContractError('private-secret: ignore checks'))
        self.assertEqual({'category': 'proposal_semantics'}, failure.metadata())

    def test_context_refusal_precedes_inspecting_malformed_provider_text(self):
        from claimbranch.application.codex_app_server import _proposal_failure
        for raw in (b'not JSON', b'{}'):
            failure = _proposal_failure(raw, ContractError('typed proposal context or digest changed'))
            self.assertEqual({'category': 'proposal_context'}, failure.metadata())

    def test_oversized_stdout_is_bounded_without_retaining_raw_diagnostics(self):
        result=self.result('oversize')
        self.assertEqual('response_too_large',result.disposition)
        self.assertIsNone(result.typed_result)
        self.assertEqual('response_too_large',self.result('stderr').disposition)

    def test_cancel_and_timeout_reap_the_owned_client(self):
        transport=self.transport('hang'); job=self.start(transport)
        pid_file=Path(self.temp.name)/'owned-peer-pid'; deadline=time.monotonic()+1
        while not pid_file.exists() and time.monotonic()<deadline: time.sleep(.01)
        self.assertTrue(pid_file.exists()); pid=int(pid_file.read_text())
        self.assertTrue(job.cancel()); self.assertTrue(job.wait_closed(3))
        with self.assertRaises(ProcessLookupError): os.kill(pid,0)
        self.assertEqual('cancelled',job.poll().disposition)
        self.assertIsNone(job.poll().typed_result)
        short=self.transport('hang',timeout=.15); job=self.start(short)
        self.assertTrue(job.wait_closed(3)); self.assertEqual('timed_out',job.poll().disposition)

    def test_cancel_after_completion_does_not_erase_checked_return(self):
        job=self.start(self.transport()); self.assertTrue(job.wait_closed(3))
        self.assertFalse(job.cancel()); self.assertEqual('completed',job.poll().disposition)

    def test_incorrect_current_profile_or_context_refuses_without_launch(self):
        transport=self.transport()
        with patch('claimbranch.application.codex_app_server.subprocess.Popen') as launch:
            for profile,selected in [(CodexProfile.create(model='other-model'),self.context),
                    (self.profile,context('plan-experiment'))]:
                with self.assertRaises(ContractError):
                    transport.start(self.prepared,confirmed_digest=self.prepared.digest,
                        current_profile=profile,current_context=selected,now=100)
            launch.assert_not_called()


if __name__=='__main__': unittest.main()
