"""Owned wire-result incorporation/return; no actual provider qualification."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.application.provider_profile import ProviderProfile, decode_provider_response
from claimbranch.application.provider_transport import ProviderTransport, TransportResult
from claimbranch.application.paper_proposal_work import ProviderProposalWork
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import snapshot, restore
from tests.application.test_paper_proposal_work import fixture, request
from tests.application.test_paper_proposals import response


def profile():
    return ProviderProfile.create(api='openai-chat', endpoint='https://llm.example/v1/chat/completions',
                                  model='owner/model:variant', credential_env='PERSONAL_LLM_KEY')


class Job:
    def __init__(self, prepared, value=None):
        self.prepared = prepared
        raw = json.dumps({'model':'reported/model', 'choices':[{'finish_reason':'stop',
            'message':{'role':'assistant','content':canonical_bytes(value or response()).decode()}}]}).encode()
        self.result = TransportResult(prepared.review.request_id, prepared.digest, 'completed', 42,
            200, hashlib.sha256(raw).hexdigest(), decode_provider_response(prepared, raw), 'reported/model')
    def poll(self): return self.result
    def cancel(self): return False


def ready(app, *, clock=None, include_draft=False):
    worker = ProviderProposalWork(app.paper, app.context_key(), clock=clock or (lambda:100))
    prepared = worker.prepare(request(app), profile=profile(), include_draft=include_draft)
    transport = ProviderTransport()
    try:
        with patch.object(transport, 'start', return_value=Job(prepared)):
            worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=prepared.profile)
        worker.complete(prepared.review.request_id)
    finally: transport.close()
    return worker


class ProviderProposalRetentionTests(unittest.TestCase):
    def test_wire_response_stages_existing_items_and_restores_only_origin(self):
        app = fixture(); worker = ready(app); worker.stage(worker.compare(['repeat']))
        saved = snapshot(app)
        self.assertEqual('claimbranch.paper-work/v9', decode(saved.payload)['schema'])
        entry = app.paper.proposal_history()[0]
        self.assertEqual('owner/model:variant', entry['destination']['model'])
        self.assertEqual('reported/model', entry['provider']['outcome']['reported_model'])
        self.assertEqual(42, entry['provider']['outcome']['elapsed_ms'])
        self.assertNotEqual(entry['response_digest'], entry['normalized_digest'])
        self.assertNotIn(b'PERSONAL_LLM_KEY', saved.payload)
        reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        self.assertEqual(worker.work.origins, reopened.paper.candidates(*reopened.context_key()).origins)
        self.assertEqual(1, reopened.review.session()._prior_dispatches)
        self.assertEqual({}, reopened.paper._proposal_active)
        self.assertFalse(reopened.paper.ai_available)
        self.assertFalse(reopened.paper.proposal_history()[0]['staging_available'])

    def pending(self, app, *, clock=None, include_draft=False):
        worker = ProviderProposalWork(app.paper, app.context_key(), clock=clock or (lambda:100))
        prepared = worker.prepare(request(app), profile=profile(), include_draft=include_draft)
        job = Job(prepared)
        transport = ProviderTransport(); self.addCleanup(transport.close)
        with patch.object(transport, 'start', return_value=job):
            worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=prepared.profile)
        return worker, prepared, job

    def test_wrong_digest_changed_profile_and_quota_refuse_before_network(self):
        app = fixture(); worker = ProviderProposalWork(app.paper, app.context_key(), clock=lambda:100)
        prepared = worker.prepare(request(app), profile=profile())
        with ProviderTransport() as transport, patch.object(transport, 'start') as start:
            for digest_value in ('a'*64, None):
                with self.assertRaises(ContractError):
                    worker.begin(prepared, transport=transport, confirmed_digest=digest_value, current_profile=prepared.profile)
            with patch('claimbranch.application.paper_proposal_work.check_capacity', side_effect=ContractError('full')):
                with self.assertRaises(ContractError):
                    worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=prepared.profile)
            start.assert_not_called()
        with ProviderTransport() as transport:
            changed = replace(
                prepared.profile, payload=canonical_bytes(prepared.profile.value | {'model':'different/model'}))
            with self.assertRaises(ContractError):
                worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=changed)
        self.assertEqual([], app.paper.proposal_history())
        self.assertEqual(0, worker.session._prior_dispatches)

    def test_wire_offline_and_reopened_attempts_share_three_request_limit(self):
        from tests.application.test_paper_proposal_work import ready as offline
        from claimbranch.application.paper_proposal_work import PaperProposalWork
        app = fixture(); ready(app); offline(app); ready(app)
        self.assertEqual(3, decode(snapshot(app).payload)['workspace']['paper']['drafts'][0]['session']['dispatched'])
        for constructor in (lambda:ProviderProposalWork(app.paper, app.context_key(), clock=lambda:100),
                            lambda:PaperProposalWork(
                                app.paper, app.context_key(), frozen_result=canonical_bytes(response()), clock=lambda:100)):
            with self.assertRaises(ContractError):
                worker = constructor()
                if isinstance(worker, ProviderProposalWork): worker.prepare(request(app), profile=profile())
                else: worker.prepare(request(app))
        saved = snapshot(app); reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened,saved)
        with self.assertRaises(ContractError): ready(reopened)

    def test_prepared_whole_judgment_request_cannot_bypass_later_wire_budget(self):
        from tests.application.test_paper_proposal_work import ready as offline
        app = fixture(); session = app.review.session(); session._response = 'Unused synthetic text'
        state = session.prepare_request(request(app)); outbound = session._outbound
        ready(app); offline(app); ready(app)
        with self.assertRaises(ContractError): session.begin_proposal(outbound.request_id,outbound.digest)
        self.assertEqual(3, len(app.paper.proposal_history()))

    def test_included_draft_edit_expiry_and_cancel_keep_return_historical(self):
        for changed in ('draft','expiry','cancel'):
            with self.subTest(changed=changed):
                app = fixture(); clock=[100]
                worker, prepared, job = self.pending(app,clock=lambda:clock[0],include_draft=True)
                if changed=='draft': app.keep_draft('Newer human interpretation','The same recorded source')
                if changed=='expiry': clock[0]=220
                if changed=='cancel': worker.cancel()
                worker.complete(prepared.review.request_id)
                with self.assertRaises(ContractError): worker.compare(['limit'])
                self.assertIsNotNone(worker.historical()[0]['result'])
                self.assertTrue(worker.historical()[0]['trace_digest'])
                snapshot(app)

    def test_omitted_draft_typing_requires_new_comparison_and_preserves_reason(self):
        app = fixture(); worker=ready(app); compared=worker.compare(['limit'])
        app.keep_draft('Current human judgment','Original measured conditions')
        with self.assertRaises(ContractError): worker.stage(compared)
        worker.stage(worker.compare(['limit']))
        self.assertEqual('Original measured conditions', app.draft()['rationale'])
        self.assertFalse(worker.session._current_judgment().ai_influenced)
        snapshot(app)

    def test_pending_restart_cannot_resume_job_or_consume_another_response(self):
        app=fixture(); worker,prepared,job=self.pending(app)
        saved=snapshot(app); reopened=TerminalWorkspace(saved.history,ai_off=True); restore(reopened,saved)
        self.assertIsNone(reopened.paper.proposal_history()[0]['trace_digest'])
        self.assertEqual({}, reopened.paper._proposal_active)
        worker.complete(prepared.review.request_id)
        with self.assertRaises(ContractError): worker.complete(prepared.review.request_id)
        self.assertEqual(1,len(app.paper.proposal_history()))

    def test_failed_malformed_refused_and_cancelled_results_preserve_manual_work(self):
        for disposition in ('cancelled','timed_out','connection_failed','malformed_response','credential_echo','http_error','refused'):
            with self.subTest(disposition=disposition):
                app=fixture(); worker,prepared,job=self.pending(app)
                if disposition=='refused':
                    job.result=replace(job.result,typed_result=canonical_bytes({'schema':'claimbranch.provider-result/v2',
                        'status':'refused','critique':None,'items':[]}))
                else: job.result=TransportResult(prepared.review.request_id,prepared.digest,disposition,73,
                    http_status=503 if disposition=='http_error' else None)
                worker.complete(prepared.review.request_id)
                self.assertIsNone(worker.historical()[0]['result'])
                with self.assertRaises(ContractError): worker.compare(['limit'])
                self.assertEqual('CPU-B is still unmeasured.',app.draft()['text'])
                saved=snapshot(app); reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
                self.assertEqual(1,reopened.review.session()._prior_dispatches)

    def test_unselected_result_and_wrong_request_identity_cannot_supply_origin(self):
        app=fixture();worker,prepared,job=self.pending(app)
        job.result=replace(job.result, request_digest='b'*64)
        with self.assertRaises(ContractError):worker.complete(prepared.review.request_id)
        job.result=replace(job.result,request_digest=prepared.digest,typed_result=b'{malformed')
        worker.complete(prepared.review.request_id)
        self.assertEqual('malformed',worker.historical()[0]['provider_disposition'])
        self.assertEqual({},worker.work.origins);snapshot(app)

    def test_retained_wire_binding_replays_independently_of_later_defaults(self):
        from claimbranch.application.provider_profile import POLICY
        from claimbranch.application.paper_work_store import PaperWork
        app=fixture();ready(app);saved=snapshot(app)
        with patch.dict(POLICY,{'read_seconds':1,'provider_retention':'A later default'}):
            self.assertEqual(saved.payload,PaperWork(saved.payload).payload)
        with patch('claimbranch.application.provider_profile.result_schema',return_value={'type':'object'}), patch(
                'claimbranch.application.provider_profile.provider_request_headers',return_value={'Changed':'header'}):
            self.assertEqual(saved.payload,PaperWork(saved.payload).payload)
        for field in ('wire_body_digest','context_review_digest','profile_digest'):
            value=decode(saved.payload);value['workspace']['proposals']['attempts'][0]['provider']['request'][field]='a'*64
            with self.assertRaises(ContractError):PaperWork(canonical_bytes(value))
        value=decode(saved.payload);value['workspace']['proposals']['attempts'][0]['provider']['outcome']['elapsed_ms']=99
        with self.assertRaises(ContractError):PaperWork(canonical_bytes(value))
        value=decode(saved.payload);value['workspace']['schema']='claimbranch.proposal-workspace/v7'
        with self.assertRaises(ContractError):PaperWork(canonical_bytes(value))

    def test_inconsistent_transport_metadata_refuses_atomically_without_poisoning_saves(self):
        for changed in ({'disposition':'http_error','http_status':503,'typed_result':None}, {'http_status':None}):
            with self.subTest(changed=changed):
                app=fixture();worker,prepared,job=self.pending(app)
                valid=job.result;job.result=replace(valid,**changed)
                with self.assertRaises(ContractError):worker.complete(prepared.review.request_id)
                self.assertIsNone(app.paper.proposal_history()[0]['trace_digest'])
                app.keep_draft('Retain newer writing','The original recorded source remains.')
                snapshot(app)
                job.result=valid;worker.complete(prepared.review.request_id);snapshot(app)

    def test_fresh_reader_keeps_v1_history_when_running_connection_defaults_change(self):
        import subprocess
        import sys
        app=fixture();worker=ready(app);worker.stage(worker.compare(['limit']))
        saved=snapshot(app)
        # Simulate an upgraded module before its schemas and dependent readers
        # initialize. Patching a default after import misses source-level coupling.
        script='''
import ast, sys, types
from pathlib import Path
import claimbranch
name, target, change = sys.argv[1:]
source = Path(claimbranch.__file__).parent / (name.removeprefix("claimbranch.").replace(".", "/") + ".py")
tree = ast.parse(source.read_text(), filename=str(source))
body = []
changed = False
for node in tree.body:
    body.append(node)
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == target for t in node.targets):
        body.extend(ast.parse(change).body)
        changed = True
assert changed, "The simulated upgrade must change its named running default"
tree.body = body
module = types.ModuleType(name)
sys.modules[name] = module
exec(compile(ast.fix_missing_locations(tree), str(source), "exec"), module.__dict__)
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import restore
raw = sys.stdin.buffer.read()
saved = PaperWork(raw)
assert saved.payload == raw
app = TerminalWorkspace(saved.history, ai_off=True)
restore(app, saved)
assert not app.paper._proposal_active and not app.paper.ai_available
assert app.paper.proposal_history()[0]["provider"]["outcome"]["elapsed_ms"] == 42
assert next(iter(app.paper.candidates(*app.context_key()).origins.values())).ai_influenced
print("v1-history-return-ok")
'''
        changes=(('application.provider_contract','POLICY', "POLICY.update(read_seconds=20, provider_retention='A later service policy')"),
                 ('application.provider_contract','PROFILE_SCHEMA', "PROFILE_SCHEMA['properties']['model']['pattern']='^[A-Z]+$'"),
                 ('application.provider_contract','PROFILE_SCHEMA', "PROFILE_SCHEMA['properties']['output_tokens']['maximum']=1"),
                 ('core.paper_context','FIELDS', "FIELDS['claim']['statement']={**FIELDS['claim']['statement'], 'pattern':'^[^/]+$'}"))
        for module, target, change in changes:
            with self.subTest(change=change):
                run=subprocess.run([sys.executable,'-B','-c',script,'claimbranch.'+module,target,change],input=saved.payload,
                                   capture_output=True,timeout=30)
                self.assertEqual(0,run.returncode,run.stderr.decode())
                self.assertIn(b'v1-history-return-ok',run.stdout)

    def test_retained_anthropic_v1_settings_remain_closed_without_current_profile(self):
        from claimbranch.application.provider_profile import check_retained_provider_request
        from claimbranch.core.canonical import digest
        app=fixture();worker=ProviderProposalWork(app.paper,app.context_key(),clock=lambda:100)
        config=ProviderProfile.create(api='anthropic-messages',endpoint='https://llm.example/v1/messages',
                                      model='owner/model:variant')
        prepared=worker.prepare(request(app),profile=config)
        entry=deepcopy(worker._entry)
        self.assertEqual(prepared.review,check_retained_provider_request(prepared.context,entry))
        for field, value in (('output_limit_field','max_completion_tokens'),('json_mode','json-object')):
            changed=deepcopy(entry);changed['provider']['request']['settings'][field]=value
            changed['request_digest']=digest(changed['provider']['request'])
            with self.subTest(field=field), self.assertRaises(ContractError):
                check_retained_provider_request(prepared.context,changed)
        changed=deepcopy(entry);changed['destination']['url']='offline://frozen'
        with self.assertRaises(ContractError):check_retained_provider_request(prepared.context,changed)

    def test_endpoint_inline_secrets_already_refuse_before_any_retention(self):
        for endpoint in ('https://llm.example/v1/chat/completions?key=sk-SECRET',
                         'https://u:sk-SECRET@llm.example/v1/chat/completions',
                         'https://llm.example/v1/chat/completions#sk-SECRET'):
            with self.assertRaises(ContractError):
                ProviderProfile.create(api='openai-chat',endpoint=endpoint,model='model',credential_env=None)

    def test_erase_keeps_adopted_item_origin_and_cannot_revive_payload(self):
        app=fixture();worker=ready(app);worker.stage(worker.compare(['limit']))
        app.paper.erase_proposal_payload(worker._current)
        with self.assertRaises(ContractError):worker.compare(['narrow'])
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertEqual('erased',reopened.paper.proposal_history()[0]['payload_availability'])
        self.assertTrue(next(iter(reopened.paper.candidates(*reopened.context_key()).origins.values())).ai_influenced)

    def test_new_payload_quota_keeps_session_reading_and_minimal_wire_trace(self):
        app=fixture();worker,prepared,job=self.pending(app)
        with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full payload')):
            worker.complete(prepared.review.request_id)
        self.assertIsNotNone(worker.historical()[0]['result'])
        self.assertEqual('not-retained',app.paper.proposal_history()[0]['payload_availability'])
        saved=snapshot(app)
        self.assertEqual(42,decode(saved.payload)['workspace']['proposals']['attempts'][0]['provider']['outcome']['elapsed_ms'])

    def test_real_owned_peer_round_trip_then_fresh_origin_return(self):
        import time
        from tests.application.test_provider_transport import Peer
        app=fixture(); worker=ProviderProposalWork(app.paper,app.context_key(),clock=lambda:100)
        peer = Peer(); self.addCleanup(peer.close)
        with ProviderTransport() as transport:
            configured=ProviderProfile.create(api='openai-chat',endpoint=peer.endpoint,model='owner/model:variant')
            prepared=worker.prepare(request(app),profile=configured)
            worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=configured)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and worker.historical()[0]['trace_digest'] is None:
                worker.complete(prepared.review.request_id);time.sleep(.01)
            self.assertEqual(1,len(peer.requests));self.assertEqual(prepared.body,peer.requests[0][2])
            worker.stage(worker.compare(['limit']))
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertTrue(next(iter(reopened.paper.candidates(*reopened.context_key()).origins.values())).ai_influenced)


class PersonalProviderReturnTests(unittest.TestCase):
    from tests.application.test_personal_research import PersonalResearchTests as _fixture
    setUp = _fixture.setUp
    result = _fixture.result
    confirm_result = _fixture.confirm_result

    def live_relationship(self, *, stage=True):
        observation=self.confirm_result(); self.app.select('thesis')
        self.app.keep_draft('Only this hardware has been measured.','Retain the original experimental conditions.')
        value=response();value['items']=[value['items'][1]]
        value['items'][0]['body']['source_id']['id']=observation
        query={'schema_version':1,'project_id':self.app.view['project_id'],'episode_id':self.app.episode_id,
            'ref':'main','view_digest':self.app.view['digest'],'purpose':'compare-evidence',
            'selections':[{'record_id':'thesis','fields':['statement','role']},
                {'record_id':observation,'fields':['statement','status','value','conditions','metric']}],
            'scientific_edge_ids':[]}
        worker=ProviderProposalWork(self.app.paper,self.app.context_key(),clock=lambda:100)
        prepared=worker.prepare(query,profile=profile())
        with ProviderTransport() as transport,patch.object(transport,'start',return_value=Job(prepared,value)):
            worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=prepared.profile)
        worker.complete(prepared.review.request_id)
        if stage:
            key=worker.stage(worker.compare(['limit']))[0]
            record=worker.work.records[key];record['body']['rationale']='Human-edited measurement scope.';worker.work.put(record)
            self.app.review.candidate_works[self.app.review.key]=worker.work
        return worker

    def test_personal_record_restart_and_backup_keep_live_item_and_original_reason(self):
        from pathlib import Path
        import subprocess
        import sys
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        worker=self.live_relationship()
        preview=self.research.prepare('reasoning',explanation_state='leave-for-later')
        self.assertTrue(preview.display['ai_origin_retained']);self.research.commit(preview)
        project=self.store.load()
        self.assertEqual('claimbranch.project-work/v5',decode(project.payload)['schema'])
        before=self.app.paper.recorded_origins()
        destination=self.directory.parent/'restored-provider';destination.mkdir(mode=0o700)
        restored=PersonalProjectStore.restore_backup(self.store.backup(),destination)
        reopened=project_workspace(restored)
        self.assertEqual(before,reopened.paper.recorded_origins())
        self.assertEqual('Retain the original experimental conditions.',before[0]['cause']['judgment']['rationale'])
        self.assertFalse(reopened.paper.ai_available)
        self.assertEqual('leave-for-later',before[0]['explanation']['state'])
        script='from claimbranch.application.personal_project import PersonalProjectStore\nfrom claimbranch.application.tui_project import project_workspace\nimport sys\nwith PersonalProjectStore(sys.argv[1]) as s:\n a=project_workspace(s.load()); r=a.paper.recorded_origins(); assert len(r)==1; assert len(r[0]["lineages"][0]["revisions"])==2; assert not a.paper._proposal_active; assert not a.paper.ai_available; assert a.paper.proposal_history()[0]["provider"]["outcome"]["elapsed_ms"]==42; print("provider-origin-return-ok")'
        run=subprocess.run([sys.executable,'-B','-c',script,str(destination)],capture_output=True,text=True,timeout=30)
        self.assertEqual(0,run.returncode,run.stderr);self.assertIn('provider-origin-return-ok',run.stdout)
        self.assertEqual(self.source,(self.paper/'paper.tex').read_bytes())
        self.assertNotIn(b'PERSONAL_LLM_KEY',restored.payload)

    def test_failed_record_preserves_saved_project_and_live_ai_origin(self):
        self.live_relationship();previous=self.store.load().payload
        preview=self.research.prepare('reasoning',explanation_state='leave-for-later')
        with patch('claimbranch.application.paper_work_store.os.replace',side_effect=OSError('injected')):
            with self.assertRaises(ContractError):self.research.commit(preview)
        self.assertEqual(previous,self.store.load().payload)
        self.assertTrue(next(iter(self.app.paper.candidates(*self.app.context_key()).origins.values())).ai_influenced)
        self.assertEqual([],self.app.paper.recorded_origins())

    def test_saved_wire_metadata_cannot_be_rewritten_even_with_new_hash(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.core.canonical import digest
        self.live_relationship(stage=False);self.app.recovery.save(self.app);project=self.store.load()
        value=decode(project.work.payload);entry=value['workspace']['proposals']['attempts'][0]
        entry['provider']['outcome']['elapsed_ms']=900
        trace={'request_id':entry['request_id'],'request_digest':entry['request_digest'],
            'response_digest':entry['response_digest'],'model':entry['destination']['model'],
            'disposition':entry['provider_disposition'],'provider':entry['provider']}
        entry['trace_digest']=digest(trace)
        rewritten=PaperWork(canonical_bytes(value))
        with self.assertRaises(ContractError):project.with_work(rewritten)
        self.assertEqual(project.payload,self.store.load().payload)


class CodexProposalRetentionTests(unittest.TestCase):
    def test_selected_advice_prefills_once_and_retains_origin_through_edit_and_return(self):
        from claimbranch.application.paper_advisory import AdviceEdits
        from claimbranch.core.advisory import advice_from_text
        app,worker,prepared,_=self.pending(prompt='What is missing?',
            value=advice_from_text('CPU-A만 측정했습니다.\nCPU-B에서 재검증이 필요합니다.'.encode()))
        worker.complete(prepared.review.request_id)
        editor=AdviceEdits(app.paper,app.context_key(),prepared.review.request_id,clock=lambda:100)
        comparison=editor.preview('claim',0,len('CPU-A만 측정했습니다.'))
        self.assertEqual({},editor.work.records)
        before=app.paper.history.manifest()
        key=editor.prefill(comparison)
        self.assertEqual('CPU-A만 측정했습니다.',editor.inputs[key]['body']['statement'])
        self.assertEqual('',editor.inputs[key]['body']['scope'])
        editor.work.project()  # Unfinished input does not block the existing graph.
        self.assertEqual({},editor.work.records)
        with self.assertRaises(ContractError):editor.prefill(comparison)
        record=deepcopy(editor.inputs[key])
        record['body'].update(role='main',parent_ids=['thesis'],scope='CPU-A only',statement='Caching helps on CPU-A only.')
        editor.work.put(record);editor.inputs.pop(key);editor.work.project()
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        lineage=reopened.paper.candidates(*reopened.context_key()).origins[key]
        self.assertTrue(lineage.ai_influenced)
        self.assertEqual('CPU-A만 측정했습니다.',decode(lineage.payload)['revisions'][0]['advisory_origin']['passage'])
        self.assertEqual('Caching helps on CPU-A only.',lineage.amendment['body']['statement'])
        self.assertEqual(before,reopened.paper.history.manifest())

    def test_explicit_edit_uses_typed_candidates_and_retains_instruction(self):
        app,worker,prepared,_=self.pending(prompt='Make the limited claim and its unrun test.',edit=True)
        self.assertTrue(prepared.edit)
        self.assertIsNotNone(json.loads(prepared.body)['output_schema'])
        worker.complete(prepared.review.request_id)
        preview=worker.compare(['repeat'])
        self.assertEqual(['narrow'],preview['required_item_ids'])
        before=worker.work.records
        with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full')):
            with self.assertRaises(ContractError):worker.stage(preview)
        self.assertEqual(before,worker.work.records)
        worker.stage(preview)
        saved=snapshot(app);returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        entry=returned.paper.proposal_history()[0]
        self.assertEqual('Make the limited claim and its unrun test.',entry['edit']['prompt'])
        self.assertNotIn('discussion',entry)
        self.assertEqual(2,len(returned.paper.candidates(*returned.context_key()).origins))

    def test_unfinished_passage_does_not_block_independent_edit_and_keeps_one_source(self):
        from claimbranch.application.paper_advisory import AdviceEdits
        from claimbranch.core.advisory import advice_from_text
        app,worker,prepared,_=self.pending(prompt='Next?',value=advice_from_text(b'Test CPU-B.'))
        worker.complete(prepared.review.request_id)
        editor=AdviceEdits(app.paper,app.context_key(),prepared.review.request_id,clock=lambda:100)
        key=editor.prefill(editor.preview('scientific-edge',0,11))
        self.assertEqual('Test CPU-B.',editor.inputs[key]['body']['rationale'])
        self.assertEqual({},editor.work.records)
        with self.assertRaisesRegex(ContractError,'required'):worker.erase_payload(prepared.review.request_id)
        app,edit,request_edit,_=self.pending(app,prompt='Make the limited claim',edit=True)
        edit.complete(request_edit.review.request_id);edit.stage(edit.compare(['narrow']))
        self.assertEqual(1,len(edit.work.records))
        saved=snapshot(app);returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        self.assertIn(key,returned.review.candidate_inputs[returned.context_key()])
        self.assertNotIn('reply_text',decode(editor.work.origins[key].payload)['revisions'][0]['advisory_origin'])

    def test_clarification_can_be_explicitly_selected_for_next_edit_and_return(self):
        value={'schema':'claimbranch.provider-result/v2','status':'ok','critique':'Which claim is B?', 'items':[]}
        app,worker,prepared,_=self.pending(prompt='Connect A to B',edit=True,value=value)
        worker.complete(prepared.review.request_id)
        app,second,next_edit,_=self.pending(app,prompt='B means thesis',edit=True,
            previous_requests=[prepared.review.request_id])
        self.assertEqual('Which claim is B?',decode(next_edit.discussion)['previous'][0]['text'])
        second.complete(next_edit.review.request_id)
        saved=snapshot(app);returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        self.assertEqual(2,len(returned.paper.proposal_history()))

    def test_edit_can_ask_for_clarification_without_creating_anything(self):
        value={'schema':'claimbranch.provider-result/v2','status':'ok','critique':'Which claim is B?', 'items':[]}
        app,worker,prepared,_=self.pending(prompt='Connect A and B.',edit=True,value=value)
        worker.complete(prepared.review.request_id)
        self.assertEqual(value,worker.historical()[0]['result'])
        self.assertEqual({},worker.work.records)
        with self.assertRaises(ContractError):worker.compare([])

    def test_passage_cancel_tampering_quota_and_expiry_preserve_science(self):
        from claimbranch.application.paper_advisory import AdviceEdits
        from claimbranch.core.advisory import advice_from_text
        now=[100];app,worker,prepared,_=self.pending(prompt='Next test?',value=advice_from_text(b'Test CPU-B.'))
        worker.complete(prepared.review.request_id)
        editor=AdviceEdits(app.paper,app.context_key(),prepared.review.request_id,clock=lambda:now[0])
        for kind in ('claim','experiment-plan','scientific-edge'):
            preview=editor.preview(kind,0,11)
            bad=deepcopy(preview);bad['passage']='Forged'
            with self.assertRaises(ContractError):editor.prefill(bad)
            with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full')):
                with self.assertRaises(ContractError):editor.prefill(preview)
            self.assertEqual({},editor.work.records)
        now[0]=160
        with self.assertRaises(ContractError):editor.prefill(preview)
        self.assertEqual({},editor.work.records)
        self.assertEqual('Test CPU-B.',app.paper.proposal_history()[0]['result']['text'])

    def test_unfinished_advice_plan_reopens_with_missing_fields_and_tamper_refusal(self):
        from claimbranch.application.paper_advisory import AdviceEdits
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.core.advisory import advice_from_text
        app,worker,prepared,_=self.pending(prompt='Next?',value=advice_from_text(b'Test CPU-B.'))
        worker.complete(prepared.review.request_id)
        editor=AdviceEdits(app.paper,app.context_key(),prepared.review.request_id,clock=lambda:100)
        key=editor.prefill(editor.preview('experiment-plan',0,11))
        saved=snapshot(app);returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        body=returned.review.candidate_inputs[returned.context_key()][key]['body']
        self.assertEqual('planned',body['status']);self.assertEqual('',body['metric']['definition'])
        self.assertNotIn('value',body)
        bad=decode(saved.payload)
        origin=bad['workspace']['proposals']['origins'][0]['lineages'][0]['revisions'][0]['advisory_origin']
        origin['passage']='Invented AI text.'
        with self.assertRaises(ContractError):PaperWork(canonical_bytes(bad))

    def pending(self, app=None, *, clock=None, include_draft=False, value=None, prompt=None, previous_requests=(), edit=False):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.codex_app_server import CodexAppServerTransport, CodexResult
        from claimbranch.application.provider_profile import CodexProfile
        import tempfile
        from pathlib import Path
        import sys
        app = app or fixture()
        worker = CodexProposalWork(app.paper, app.context_key(), clock=clock or (lambda:100))
        prepared = worker.prepare(request(app), profile=CodexProfile.create(model='gpt-6.1-sol'),
            include_draft=include_draft, prompt=prompt, previous_requests=previous_requests, edit=edit)
        raw = canonical_bytes(value or response())
        job = Job.__new__(Job)
        job.result = CodexResult(prepared.review.request_id, prepared.digest, 'completed', 42,
            hashlib.sha256(raw).hexdigest(), raw, 'gpt-6.1-sol', '0.158.0', 'thread-owned', 'turn-owned')
        scratch = tempfile.TemporaryDirectory(prefix='claimbranch-codex-retention-')
        self.addCleanup(scratch.cleanup)
        transport = CodexAppServerTransport((sys.executable,'-I','-c','pass'), cwd=Path(scratch.name), environment={})
        self.addCleanup(transport.close)
        with patch.object(transport, 'start', return_value=job):
            worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=prepared.profile)
        return app, worker, prepared, job

    def test_advice_reads_reopens_and_never_becomes_graph_items(self):
        from claimbranch.core.advisory import advice_from_text
        from claimbranch.application.paper_proposal_work import RetainedProposalReview
        value=advice_from_text('CPU-A 결과만으로 CPU-B를 일반화할 수 없습니다.\n추가 측정이 필요합니다.'.encode())
        app,worker,prepared,_=self.pending(prompt='어떤 주장이 아직 불확실한가요?',value=value)
        before=app.paper.history.manifest()
        worker.complete(prepared.review.request_id)
        self.assertEqual(value,worker.historical()[0]['result'])
        with self.assertRaises(ContractError): worker.compare([])
        saved=snapshot(app)
        self.assertEqual('claimbranch.paper-work/v12',decode(saved.payload)['schema'])
        reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        entry=reopened.paper.proposal_history()[0]
        self.assertEqual(value,entry['result'])
        self.assertEqual('어떤 주장이 아직 불확실한가요?',entry['discussion']['prompt'])
        self.assertEqual(1,reopened.review.session()._prior_dispatches)
        self.assertEqual({},reopened.paper._proposal_active)
        self.assertEqual(before,reopened.paper.history.manifest())
        with self.assertRaises(ContractError):
            RetainedProposalReview(reopened.paper,reopened.context_key(),entry['request_id'])

    def test_follow_up_includes_only_chosen_owned_messages_and_keeps_the_budget(self):
        from claimbranch.core.advisory import advice_from_text
        from claimbranch.application.paper_proposal_work import CodexProposalWork,restore_proposals,proposal_snapshot
        from claimbranch.application.provider_profile import CodexProfile
        value=advice_from_text(b'Test CPU-B before generalizing.')
        app,worker,first,_=self.pending(prompt='What is missing?',value=value)
        worker.complete(first.review.request_id)
        app,second,prepared,_=self.pending(app,prompt='How could we test that?',
            value=value,previous_requests=[first.review.request_id])
        selected=decode(prepared.discussion)
        self.assertEqual('Test CPU-B before generalizing.',selected['previous'][0]['text'])
        self.assertEqual('What is missing?',selected['previous'][0]['prompt'])
        second.complete(prepared.review.request_id)
        saved=snapshot(app); returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        entry=returned.paper.proposal_history()[1]
        self.assertEqual(selected,entry['discussion'])
        with self.assertRaisesRegex(ContractError,'included'):
            second.erase_payload(first.review.request_id)
        for mutate in ('prompt','text','request_id'):
            bad=proposal_snapshot(returned.paper)
            if mutate=='prompt': bad['attempts'][1]['discussion']['prompt']='Forged question'
            else: bad['attempts'][1]['discussion']['previous'][0][mutate]='forged'
            with self.assertRaises(ContractError): restore_proposals(returned.paper,bad)
        app,third,last,_=self.pending(returned,prompt='Third question',value=value)
        third.complete(last.review.request_id)
        with self.assertRaisesRegex(ContractError,'three'):
            CodexProposalWork(app.paper,app.context_key()).prepare(request(app),profile=CodexProfile.create(model='gpt-6-sol'))

    def test_an_action_failure_does_not_erase_saved_advice(self):
        from claimbranch.core.advisory import advice_from_text
        value=advice_from_text(b'No graph edit is necessary yet.')
        app,first,prepared,_=self.pending(prompt='Discuss this result',value=value)
        first.complete(prepared.review.request_id)
        app,second,next_request,_=self.pending(app,value={'invalid':'graph-item'})
        second.complete(next_request.review.request_id)
        saved=snapshot(app);returned=TerminalWorkspace(saved.history,ai_off=True);restore(returned,saved)
        entries=returned.paper.proposal_history()
        self.assertEqual(value,entries[0]['result'])
        self.assertEqual('malformed',entries[1]['provider_disposition'])

    def test_erasing_selected_reply_invalidates_unsent_follow_up(self):
        from claimbranch.core.advisory import advice_from_text
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        app,first,original,_=self.pending(prompt='What remains unknown?',
            value=advice_from_text(b'Only CPU-A was measured.'))
        first.complete(original.review.request_id)
        follow_up=CodexProposalWork(app.paper,app.context_key(),clock=lambda:100)
        prepared=follow_up.prepare(request(app),profile=original.profile,
            prompt='What should we measure next?',previous_requests=[original.review.request_id])
        first.erase_payload(original.review.request_id)
        with self.assertRaisesRegex(ContractError,'unavailable'):
            follow_up.recheck_preview(prepared,original.profile)
        self.assertEqual(1,len(app.paper.proposal_history()))
        self.assertEqual('erased',app.paper.proposal_history()[0]['payload_availability'])

    def test_checked_items_stage_edit_and_restore_without_capability(self):
        app, worker, prepared, _ = self.pending()
        worker.complete(prepared.review.request_id)
        worker.stage(worker.compare(['repeat']))
        key = next(k for k,r in worker.work.records.items() if r['kind']=='claim')
        record = worker.work.records[key]; record['body']['statement']='Caching reduced latency on the measured CPU only.'
        worker.work.put(record)
        saved = snapshot(app)
        self.assertEqual('claimbranch.paper-work/v10', decode(saved.payload)['schema'])
        entry = app.paper.proposal_history()[0]
        self.assertEqual('https://chatgpt.com', entry['destination']['url'])
        self.assertNotIn('provider', entry)
        self.assertEqual('turn-owned', entry['codex']['outcome']['turn_id'])
        self.assertNotIn('http_status', entry['codex']['outcome'])
        reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        self.assertEqual(worker.work.origins, reopened.paper.candidates(*reopened.context_key()).origins)
        self.assertEqual(1, reopened.review.session()._prior_dispatches)
        self.assertEqual({}, reopened.paper._proposal_active)
        self.assertFalse(reopened.paper.ai_available)
        self.assertFalse(reopened.paper.proposal_history()[0]['staging_available'])

    def test_preview_and_failed_begin_preserve_previous_comparison_and_count(self):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        from claimbranch.application.codex_app_server import CodexAppServerTransport
        app=fixture(); old=ready(app); comparison=old.compare(['limit'])
        worker=CodexProposalWork(app.paper, app.context_key(), clock=lambda:100)
        prepared=worker.prepare(request(app), profile=CodexProfile.create(model='gpt-6.1-sol'))
        self.assertEqual(old, app.paper._proposal_active[app.context_key()])
        before=deepcopy(app.paper.proposal_history())
        with patch.object(CodexAppServerTransport,'start') as start:
            with self.assertRaises(ContractError):
                worker.begin(prepared,transport=None,confirmed_digest=prepared.digest,current_profile=prepared.profile)
            start.assert_not_called()
        self.assertEqual(before, app.paper.proposal_history()); old.stage(comparison)

    def test_preflight_digest_profile_capacity_and_expiry_refuse_without_attempt(self):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        from claimbranch.application.codex_app_server import CodexAppServerTransport
        import tempfile, sys
        from pathlib import Path
        app=fixture(); clock=[100]
        worker=CodexProposalWork(app.paper,app.context_key(),clock=lambda:clock[0])
        prepared=worker.prepare(request(app),profile=CodexProfile.create(model='gpt-6.1-sol'))
        with tempfile.TemporaryDirectory() as scratch:
            transport=CodexAppServerTransport((sys.executable,'-I','-c','pass'),cwd=Path(scratch),environment={})
            self.addCleanup(transport.close)
            with patch.object(transport,'start') as start:
                for confirmed, config in (('a'*64,prepared.profile), (prepared.digest,CodexProfile.create(model='other'))):
                    with self.assertRaises(ContractError):
                        worker.begin(prepared,transport=transport,confirmed_digest=confirmed,current_profile=config)
                with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full')):
                    with self.assertRaises(ContractError):
                        worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=prepared.profile)
                clock[0]=220
                with self.assertRaises(ContractError):
                    worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=prepared.profile)
                start.assert_not_called()
        self.assertEqual([],app.paper.proposal_history()); self.assertEqual(0,worker.session._prior_dispatches)

    def test_cancelled_and_changed_input_keep_late_trace_but_cannot_stage(self):
        for action in ('cancel','draft','expire'):
            with self.subTest(action=action):
                clock=[100];app,worker,prepared,_=self.pending(clock=lambda:clock[0],include_draft=True)
                if action=='cancel': worker.cancel()
                elif action=='draft': app.keep_draft('New judgment','New reason')
                else: clock[0]=220
                worker.complete(prepared.review.request_id);snapshot(app)
                self.assertEqual({'cancel':'cancelled','draft':'stale','expire':'expired'}[action],worker.historical()[0]['disposition'])
                self.assertIsNotNone(worker.historical()[0]['trace_digest'])
                with self.assertRaises(ContractError):worker.compare(['limit'])

    def test_owned_inconsistent_metadata_records_terminal_failure_without_staging(self):
        changes=({'reported_model':'other'}, {'client_version':'0.160.0'}, {'cleanup_complete':False},
                 {'thread_id':None}, {'response_digest':None}, {'elapsed_ms':True})
        for changed in changes:
            with self.subTest(changed=changed):
                app,worker,prepared,job=self.pending();job.result=replace(job.result,**changed)
                worker.complete(prepared.review.request_id)
                entry=worker.historical()[0]
                self.assertEqual('protocol_error',entry['codex']['outcome']['disposition'])
                self.assertEqual('malformed',entry['provider_disposition']);self.assertIsNone(entry['result'])
                self.assertIsNotNone(entry['trace_digest']);self.assertNotIn(prepared.review.request_id,worker._jobs)
                snapshot(app)
                with self.assertRaises(ContractError):worker.compare(['limit'])

    def test_foreign_request_metadata_refuses_without_claiming_ownership(self):
        app,worker,prepared,job=self.pending();job.result=replace(job.result,request_digest='a'*64)
        with self.assertRaises(ContractError):worker.complete(prepared.review.request_id)
        self.assertIsNone(worker.historical()[0]['trace_digest']);snapshot(app)

    def test_started_replacement_remains_tracked_and_spent_if_prior_cancel_raises(self):
        from claimbranch.application.codex_app_server import CodexAppServerTransport
        import tempfile,sys
        from pathlib import Path
        app,worker,prepared,old=self.pending()
        replacement=worker.prepare(request(app),profile=prepared.profile)
        new=Job.__new__(Job);new.result=replace(old.result,request_id=replacement.review.request_id,request_digest=replacement.digest)
        with tempfile.TemporaryDirectory() as scratch:
            transport=CodexAppServerTransport((sys.executable,'-I','-c','pass'),cwd=Path(scratch),environment={})
            try:
                with patch.object(transport,'start',return_value=new),patch.object(old,'cancel',side_effect=RuntimeError('cancel failed')):
                    with self.assertRaises(RuntimeError):
                        worker.begin(replacement,transport=transport,confirmed_digest=replacement.digest,current_profile=replacement.profile)
                self.assertEqual(2,worker.session._prior_dispatches)
                self.assertIs(new,worker._jobs[replacement.review.request_id])
                self.assertEqual('cancelled',worker.historical()[-1]['disposition']);snapshot(app)
                worker.complete(replacement.review.request_id)
                self.assertIsNotNone(worker.historical()[-1]['trace_digest'])
                with self.assertRaises(ContractError):worker.compare(['limit'])
            finally:transport.close()

    def test_invalid_scientific_return_is_retained_as_malformed_only(self):
        app,worker,prepared,job=self.pending(); value=response()
        value['items'][0]['body']['parent_ids'][0]['id']='outside'
        raw=canonical_bytes(value);job.result=replace(job.result,typed_result=raw,response_digest=hashlib.sha256(raw).hexdigest())
        worker.complete(prepared.review.request_id);snapshot(app)
        entry=worker.historical()[0]
        self.assertEqual('malformed',entry['disposition']);self.assertEqual('malformed_response',entry['codex']['outcome']['disposition'])
        self.assertIsNone(entry['result']);self.assertIsNone(entry['normalized_digest'])
        with self.assertRaises(ContractError):worker.compare(['limit'])

    def test_transport_failures_preserve_writing_and_spent_request(self):
        for status in ('cancelled','timed_out','auth_required','policy_refused','protocol_error','start_failed','client_failed','response_too_large'):
            with self.subTest(status=status):
                app,worker,prepared,job=self.pending()
                job.result=replace(job.result,disposition=status,typed_result=None,reported_model=None,response_digest=None)
                worker.complete(prepared.review.request_id)
                saved=snapshot(app);self.assertEqual(1,worker.session._prior_dispatches)
                self.assertEqual('CPU-B is still unmeasured.',app.draft()['text'])
                self.assertIsNone(worker.historical()[0]['result'])
                self.assertEqual(saved.payload, type(saved)(saved.payload).payload)

    def test_three_request_budget_spans_offline_codex_and_restart(self):
        app=fixture();ready(app)
        app,worker,prepared,_=self.pending(app);worker.complete(prepared.review.request_id)
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        app,worker,prepared,_=self.pending(reopened);worker.complete(prepared.review.request_id)
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        fourth=CodexProposalWork(app.paper,app.context_key(),clock=lambda:100)
        with self.assertRaises(ContractError):fourth.prepare(request(app),profile=CodexProfile.create(model='gpt-6.1-sol'))
        self.assertEqual(3,len(app.paper.proposal_history()))

    def test_history_does_not_depend_on_current_prompt_or_binding_compiler(self):
        app,worker,prepared,_=self.pending();worker.complete(prepared.review.request_id)
        worker.stage(worker.compare(['limit']));saved=snapshot(app)
        with patch('claimbranch.application.provider_profile.prepare_codex_request',side_effect=AssertionError('Do not recompile old wrappers')):
            self.assertEqual(saved.payload,type(saved)(saved.payload).payload)
            reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertTrue(next(iter(reopened.paper.candidates(*reopened.context_key()).origins.values())).ai_influenced)

    def test_fresh_reader_keeps_frozen_history_after_live_profile_rule_changes(self):
        import subprocess,sys
        app,worker,prepared,_=self.pending();worker.complete(prepared.review.request_id);saved=snapshot(app)
        script='''
import ast,sys,types
from pathlib import Path
import claimbranch
name='claimbranch.application.provider_contract'
source=Path(claimbranch.__file__).parent/'application/provider_contract.py'
tree=ast.parse(source.read_text());body=[]
for node in tree.body:
 body.append(node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CODEX_PROFILE_SCHEMA' for t in node.targets):
  body.extend(ast.parse("CODEX_PROFILE_SCHEMA['properties']['model']['pattern']='^[A-Z]+$'").body)
tree.body=body;module=types.ModuleType(name);sys.modules[name]=module
exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),module.__dict__)
from claimbranch.application.paper_work_store import PaperWork
raw=sys.stdin.buffer.read();assert PaperWork(raw).payload==raw
print('codex-frozen-history-ok')
'''
        run=subprocess.run([sys.executable,'-B','-c',script],input=saved.payload,capture_output=True,timeout=30)
        self.assertEqual(0,run.returncode,run.stderr.decode());self.assertIn(b'codex-frozen-history-ok',run.stdout)

    def test_pending_return_and_erased_response_never_restore_live_owner(self):
        app,worker,prepared,_=self.pending();pending=snapshot(app)
        reopened=TerminalWorkspace(pending.history,ai_off=True);restore(reopened,pending)
        self.assertEqual({},reopened.paper._proposal_active)
        worker.complete(prepared.review.request_id);worker.stage(worker.compare(['limit']))
        origins=worker.work.origins;worker.erase_payload(prepared.review.request_id)
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertEqual(origins,reopened.paper.candidates(*reopened.context_key()).origins)
        self.assertEqual('erased',reopened.paper.proposal_history()[0]['payload_availability'])

    def test_real_owned_stdio_peer_connects_checked_return_and_restart(self):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        from claimbranch.application.codex_app_server import CodexAppServerTransport
        from tests.application.test_codex_app_server import PEER
        import tempfile, sys, time
        from pathlib import Path
        app=fixture();worker=CodexProposalWork(app.paper,app.context_key(),clock=lambda:100)
        prepared=worker.prepare(request(app),profile=CodexProfile.create(model='gpt-6.1-sol'))
        with tempfile.TemporaryDirectory() as scratch:
            transport=CodexAppServerTransport((sys.executable,'-I','-c',PEER),cwd=Path(scratch),
                environment={'CB_ANSWER':json.dumps(response()),'CB_CONTEXT':prepared.context.digest,'CB_REQUEST':prepared.review.request_id})
            try:
                worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=prepared.profile)
                deadline=time.monotonic()+3
                while worker.historical()[0]['trace_digest'] is None and time.monotonic()<deadline:
                    worker.complete(prepared.review.request_id);time.sleep(.01)
                worker.stage(worker.compare(['limit']))
            finally:transport.close();self.assertTrue(transport.wait_closed(3))
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertTrue(next(iter(reopened.paper.candidates(*reopened.context_key()).origins.values())).ai_influenced)

    def test_same_owner_preview_preserves_live_comparison_until_explicit_replacement(self):
        app,worker,prepared,_=self.pending();worker.complete(prepared.review.request_id)
        comparison=worker.compare(['limit']);old_id=worker._current
        replacement=worker.prepare(request(app),profile=prepared.profile)
        worker.recheck_preview(replacement,prepared.profile)
        self.assertEqual(old_id,worker._current);worker.stage(comparison)
        worker.recheck_preview(replacement,prepared.profile)
        self.assertEqual(1,len(app.paper.proposal_history()))

    def test_payload_quota_preserves_session_reading_and_minimal_trace(self):
        app,worker,prepared,_=self.pending()
        with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full payload')):
            worker.complete(prepared.review.request_id)
        self.assertIsNotNone(worker.historical()[0]['result'])
        self.assertEqual('not-retained',app.paper.proposal_history()[0]['payload_availability'])
        saved=snapshot(app);reopened=TerminalWorkspace(saved.history,ai_off=True);restore(reopened,saved)
        self.assertIsNone(reopened.paper.proposal_history()[0]['result'])
        self.assertEqual('Only CPU-A was tested.',app.draft()['rationale'])

    def test_typed_refusal_and_failure_and_duplicate_arrival_cannot_stage(self):
        for status in ('refused','failed'):
            value=response();value.update(status=status,critique=None,items=[])
            app,worker,prepared,_=self.pending(value=value);worker.complete(prepared.review.request_id)
            snapshot(app);self.assertEqual(status,worker.historical()[0]['disposition'])
            with self.assertRaises(ContractError):worker.compare(['limit'])
            with self.assertRaises(ContractError):worker.complete(prepared.review.request_id)

    def test_retained_bindings_and_cross_format_widening_refuse(self):
        app,worker,prepared,_=self.pending();worker.complete(prepared.review.request_id);saved=snapshot(app)
        for field in ('application_input_digest','context_review_digest','profile_digest'):
            value=decode(saved.payload);value['workspace']['proposals']['attempts'][0]['codex']['request']['binding'][field]='a'*64
            with self.assertRaises(ContractError):type(saved)(canonical_bytes(value))
        value=decode(saved.payload);value['schema']='claimbranch.paper-work/v9';value['workspace']['schema']='claimbranch.provider-workspace/v8'
        with self.assertRaises(ContractError):type(saved)(canonical_bytes(value))


class PersonalCodexReturnTests(unittest.TestCase):
    from tests.application.test_personal_research import PersonalResearchTests as _fixture
    setUp = _fixture.setUp
    result = _fixture.result
    confirm_result = _fixture.confirm_result

    def relationship(self, *, stage=True):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        from claimbranch.application.codex_app_server import CodexAppServerTransport, CodexResult
        import sys
        observation=self.confirm_result();self.app.select('thesis')
        self.app.keep_draft('Only this hardware has been measured.','Retain the original experimental conditions.')
        value=response();value['items']=[value['items'][1]];value['items'][0]['body']['source_id']['id']=observation
        query={'schema_version':1,'project_id':self.app.view['project_id'],'episode_id':self.app.episode_id,
            'ref':'main','view_digest':self.app.view['digest'],'purpose':'compare-evidence',
            'selections':[{'record_id':'thesis','fields':['statement','role']},
                {'record_id':observation,'fields':['statement','status','value','conditions','metric']}],
            'scientific_edge_ids':[]}
        worker=CodexProposalWork(self.app.paper,self.app.context_key(),clock=lambda:100)
        prepared=worker.prepare(query,profile=CodexProfile.create(model='gpt-6.1-sol'))
        raw=canonical_bytes(value);job=Job.__new__(Job)
        job.result=CodexResult(prepared.review.request_id,prepared.digest,'completed',42,
            hashlib.sha256(raw).hexdigest(),raw,'gpt-6.1-sol','0.158.0','thread-owned','turn-owned')
        transport=CodexAppServerTransport((sys.executable,'-I','-c','pass'),cwd=self.directory.parent,environment={})
        try:
            with patch.object(transport,'start',return_value=job):
                worker.begin(prepared,transport=transport,confirmed_digest=prepared.digest,current_profile=prepared.profile)
            worker.complete(prepared.review.request_id)
            if stage:
                key=worker.stage(worker.compare(['limit']))[0]
                record=worker.work.records[key];record['body']['rationale']='Human-edited measurement scope.';worker.work.put(record)
                self.app.review.candidate_works[self.app.review.key]=worker.work
        finally:transport.close()
        return worker

    def test_personal_record_fresh_process_and_backup_keep_origin_reason_and_choice(self):
        import subprocess,sys
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        self.relationship();preview=self.research.prepare('reasoning',explanation_state='leave-for-later')
        self.assertTrue(preview.display['ai_origin_retained']);self.research.commit(preview)
        project=self.store.load();self.assertEqual('claimbranch.project-work/v6',decode(project.payload)['schema'])
        before=self.app.paper.recorded_origins()
        destination=self.directory.parent/'restored-codex';destination.mkdir(mode=0o700)
        restored=PersonalProjectStore.restore_backup(self.store.backup(),destination)
        reopened=project_workspace(restored)
        self.assertEqual(before,reopened.paper.recorded_origins())
        self.assertEqual('Retain the original experimental conditions.',before[0]['cause']['judgment']['rationale'])
        self.assertEqual('leave-for-later',before[0]['explanation']['state']);self.assertFalse(reopened.paper.ai_available)
        script='''
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.tui_project import project_workspace
import sys
with PersonalProjectStore(sys.argv[1]) as store:
 app=project_workspace(store.load()); recorded=app.paper.recorded_origins()
 assert len(recorded)==1 and len(recorded[0]['lineages'][0]['revisions'])==2
 assert not app.paper._proposal_active and not app.paper.ai_available
 assert app.paper.proposal_history()[0]['codex']['outcome']['turn_id']=='turn-owned'
 print('codex-origin-return-ok')
'''
        run=subprocess.run([sys.executable,'-B','-c',script,str(destination)],capture_output=True,text=True,timeout=30)
        self.assertEqual(0,run.returncode,run.stderr);self.assertIn('codex-origin-return-ok',run.stdout)
        self.assertEqual(self.source,(self.paper/'paper.tex').read_bytes())
        for secret in (b'credential_env',b'auth.json',b'email',b'CB_ANSWER'):self.assertNotIn(secret,restored.payload)

    def test_failed_save_preserves_saved_project_and_live_origin(self):
        self.relationship();previous=self.store.load().payload
        preview=self.research.prepare('reasoning',explanation_state='leave-for-later')
        with patch('claimbranch.application.paper_work_store.os.replace',side_effect=OSError('injected')):
            with self.assertRaises(ContractError):self.research.commit(preview)
        self.assertEqual(previous,self.store.load().payload)
        self.assertTrue(next(iter(self.app.paper.candidates(*self.app.context_key()).origins.values())).ai_influenced)
        self.assertEqual([],self.app.paper.recorded_origins())

    def test_saved_codex_metadata_cannot_be_rewritten_with_rehashed_trace(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.core.canonical import digest
        self.relationship(stage=False);self.app.recovery.save(self.app);project=self.store.load()
        value=decode(project.work.payload);entry=value['workspace']['proposals']['attempts'][0]
        entry['codex']['outcome']['elapsed_ms']=900
        trace={'request_id':entry['request_id'],'request_digest':entry['request_digest'],
            'response_digest':entry['response_digest'],'model':entry['destination']['model'],
            'disposition':entry['provider_disposition'],'codex':entry['codex']}
        entry['trace_digest']=digest(trace);rewritten=PaperWork(canonical_bytes(value))
        with self.assertRaises(ContractError):project.with_work(rewritten)
        self.assertEqual(project.payload,self.store.load().payload)


class PersonalContextualReturnTests(unittest.TestCase):
    from tests.application.test_personal_research import PersonalResearchTests as _fixture
    setUp = _fixture.setUp
    result = _fixture.result
    confirm_result = _fixture.confirm_result

    def receive(self, query, value, *, prompt, edit=False, previous=()):
        import sys
        from contextlib import closing
        from types import SimpleNamespace
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.provider_profile import CodexProfile
        from claimbranch.application.codex_app_server import CodexAppServerTransport, CodexResult
        worker = CodexProposalWork(self.app.paper, self.app.context_key(), clock=lambda:100)
        prepared = worker.prepare(query, profile=CodexProfile.create(model='gpt-6-sol'),
            prompt=prompt, edit=edit, previous_requests=previous)
        raw = canonical_bytes(value)
        result = CodexResult(prepared.review.request_id, prepared.digest, 'completed', 42,
            hashlib.sha256(raw).hexdigest(), raw, 'gpt-6-sol', '0.158.0', 'thread-owned', 'turn-owned')
        job = SimpleNamespace(poll=lambda:result, cancel=lambda:False)
        with closing(CodexAppServerTransport((sys.executable,'-I','-c','pass'), cwd=self.directory.parent, environment={})) as transport:
            with patch.object(transport, 'start', return_value=job):
                worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=prepared.profile)
            worker.complete(prepared.review.request_id)
        return worker, prepared.review.request_id

    def advice(self):
        from claimbranch.core.advisory import advice_from_text
        observation = self.confirm_result()
        self.app.select('thesis')
        self.app.keep_draft('The measured effect is conditional.', 'Only the input changed on this hardware.')
        query = {'schema_version':1, 'project_id':self.app.view['project_id'], 'episode_id':self.app.episode_id,
            'ref':'main', 'view_digest':self.app.view['digest'], 'purpose':'compare-evidence',
            'selections':[{'record_id':'thesis','fields':['statement','role']},
                {'record_id':observation,'fields':['statement','status','value','conditions','metric']}],
            'scientific_edge_ids':[]}
        text = '이 조건에서는 잡음이 지연을 늘릴 수 있습니다.\n관찰은 이 장치에 한정됩니다.\n다른 장치에서 비교하세요.\n모든 장치에서도 같을까요?'
        worker, request_id = self.receive(query, advice_from_text(text.encode()), prompt='이 관찰로 무엇을 말할 수 있나요?')
        return observation, query, worker, request_id, text

    def candidates(self):
        from claimbranch.application.paper_advisory import AdviceEdits
        observation, query, worker, request_id, text = self.advice()
        editor = AdviceEdits(self.app.paper, self.app.context_key(), request_id, clock=lambda:100)
        keys = []
        for kind, passage in zip(('claim','scientific-edge','experiment-plan','claim'), text.splitlines()):
            start = text.index(passage)
            key = editor.prefill(editor.preview(kind,start,start+len(passage)))
            record = deepcopy(editor.inputs[key])
            if kind == 'claim':
                record['body'].update(role='main', parent_ids=['thesis'], scope='This measured hardware only',
                    statement='Human: noise increases latency here.' if not keys else 'Omitted generalization.')
            elif kind == 'scientific-edge':
                record['body'].update(edge_type='supports',source_id=observation,target_id=keys[0],
                    rationale='Human: 24 ms exceeds the clean 20 ms baseline.')
            else:
                record['body'].update(claim_id=keys[0],conditions='Another device; identical input and repetitions',
                    metric={'name':'latency','definition':'input to output time','unit':'ms','comparison':'clean input'})
            editor.work.put(record); editor.inputs.pop(key); keys.append(key)
        editor.work.toggle(keys[0])  # Required by the selected connection and plan.
        editor.work.toggle(keys[-1])  # Independent suggestion remains omitted.
        self.app.review.candidate_works[self.app.review.key] = editor.work
        return observation, query, editor.work, request_id, keys

    def test_passage_record_correction_fresh_process_backup_and_readable_origin(self):
        import subprocess,sys
        from types import SimpleNamespace
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_proposals import ProposalsUI
        observation, _, work, request_id, keys = self.candidates()
        preview = self.research.prepare('reasoning')
        self.assertFalse(preview.display['recording_available'])
        self.assertEqual(3,len(preview.display['item_origins']))
        entries = [{'topic_id':preview.display['explanation_topics'][0]['id'],
                    'text':'다른 장치의 조건은 아직 생각하는 중입니다.','reuse_rationale':False}]
        self.research.keep_explanation(preview,entries=entries)
        preview = self.research.prepare('reasoning',explanation_state='leave-for-later',explanation_entries=entries)
        self.research.commit(preview)
        first = self.app.paper.recorded_origins()[0]
        self.assertEqual('Only the input changed on this hardware.',first['cause']['judgment']['rationale'])
        recorded = {r['id']:r for r in self.app.paper.history.view('main')['changes']}
        self.assertNotIn(keys[-1],recorded)
        self.assertEqual('planned',recorded[keys[2]]['body']['status'])
        self.app.select(observation)
        correction = self.app.intake.create(self.app.context_key())
        for field,value in {'observation':'Corrected latency: 23 ms','value':'23','rationale':'Clock offset corrected.'}.items():
            self.app.intake.keep(correction,field,value)
        self.research.commit(self.research.prepare('correct',item_id=correction))
        later = [{'topic_id':entries[0]['topic_id'],'text':'수정 후에도 다른 장치는 미검증입니다.','reuse_rationale':False}]
        self.research.keep_retained_explanation(first['cause'],entries=later)
        self.app.recovery.save(self.app)
        destination = self.directory.parent/'restored-contextual'; destination.mkdir(mode=0o700)
        restored = PersonalProjectStore.restore_backup(self.store.backup(),destination)
        returned = project_workspace(restored)
        self.assertEqual(first,returned.paper.recorded_origins()[0])
        self.assertEqual('claimbranch.project-work/v9',decode(restored.payload)['schema'])
        from claimbranch.application.personal_research import PersonalResearch
        context = PersonalResearch(returned).explanation_contexts()[0]
        self.assertEqual(later,context['explanation']['entries'])
        self.assertEqual(entries,context['recorded_explanation']['entries'])
        self.assertTrue(context['changed_context']); self.assertFalse(context['closure_available'])
        with self.assertRaises(ContractError):returned.paper.erase_proposal_payload(request_id)
        ui = ProposalsUI(SimpleNamespace(app=returned)); ui.owner = returned.work_key()
        shown = '\n'.join(ui.content('origins'))
        self.assertIn('ORIGINAL QUESTION / 이 관찰로 무엇을 말할 수 있나요?',shown)
        self.assertIn('REQUESTED MODEL / gpt-6-sol',shown)
        self.assertIn('REPORTED MODEL / gpt-6-sol / provider-reported, not independently verified',shown)
        self.assertIn('SELECTED AI PASSAGE',shown)
        self.assertIn('Human: noise increases latency here.',shown)
        script = '''
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.tui_project import project_workspace
import sys
with PersonalProjectStore(sys.argv[1]) as store:
 app=project_workspace(store.load()); record=app.paper.recorded_origins()[0]
 assert len(record['lineages'])==3
 assert all(o['revisions'][0]['advisory_origin'] for o in record['lineages'])
 assert not app.paper.ai_available and not app.paper._proposal_active
 assert app.paper.history.view('main')['evidence'][0]['value']=='23'
 assert not any(e['staging_available'] for e in app.paper.proposal_history())
 print('contextual-origin-return-ok')
'''
        run = subprocess.run([sys.executable,'-B','-c',script,str(destination)],capture_output=True,text=True,timeout=30)
        self.assertEqual(0,run.returncode,run.stderr); self.assertIn('contextual-origin-return-ok',run.stdout)
        self.assertEqual(self.source,(self.paper/'paper.tex').read_bytes())

    def test_explicit_edit_keeps_selected_earlier_advice_with_recorded_origin(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_proposals import ProposalsUI
        from claimbranch.application.tui_project import project_workspace
        observation, query, _, advice_id, text = self.advice()
        value = response(); value['items'] = [value['items'][1]]
        value['items'][0]['body']['source_id']['id'] = observation
        worker, edit_id = self.receive(query,value,prompt='이 관찰로 논제의 범위를 한정하는 연결을 만들어줘.',edit=True,previous=[advice_id])
        key = worker.stage(worker.compare(['limit']))[0]
        record = worker.work.records[key]; record['body']['rationale'] = 'Human: the observation covers one device only.'
        worker.work.put(record)
        self.app.review.candidate_works[self.app.review.key] = worker.work
        preview = self.research.prepare('reasoning')
        entries = [{'topic_id':t['id'],'text':'','reuse_rationale':True} for t in preview.display['explanation_topics']]
        self.research.commit(self.research.prepare('reasoning',explanation_state='reviewed',explanation_entries=entries))
        returned = project_workspace(self.store.load())
        ui = ProposalsUI(SimpleNamespace(app=returned)); ui.owner = returned.work_key()
        shown = '\n'.join(ui.content('origins'))
        self.assertIn('ORIGINAL EDIT INSTRUCTION / 이 관찰로 논제의 범위를 한정하는 연결을 만들어줘.',shown)
        self.assertIn('EXPLICITLY INCLUDED EARLIER REPLY / '+advice_id,shown)
        self.assertIn(text,shown)
        self.assertIn(edit_id,shown)
        self.assertEqual('reviewed',returned.paper.recorded_origins()[0]['explanation']['state'])
        before = returned.paper.proposal_history()
        with self.assertRaises(ContractError):returned.paper.erase_proposal_payload(advice_id)
        self.assertEqual(before,returned.paper.proposal_history())
        # Optional typed payload can still be erased; the selected item and
        # instruction remain readable from the recorded contribution.
        returned.paper.erase_proposal_payload(edit_id)
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui_work_recovery import snapshot_value
        saved = self.store.load().with_work(PaperWork.create(returned.paper.history,workspace=snapshot_value(returned)))
        self.store.save(saved)
        again = project_workspace(self.store.load())
        self.assertEqual('erased',again.paper.proposal_history()[1]['payload_availability'])
        self.assertTrue(again.paper.origin_for(key).ai_influenced)
        ui = ProposalsUI(SimpleNamespace(app=again)); ui.owner = again.work_key()
        self.assertIn('Human: the observation covers one device only.','\n'.join(ui.content('origins')))

    def test_later_human_derivation_inherits_recorded_passage_origin(self):
        from claimbranch.application.tui_project import project_workspace
        _, _, _, request_id, keys = self.candidates()
        self.research.commit(self.research.prepare('reasoning',explanation_state='leave-for-later'))
        first = self.app.paper.recorded_origins()[0]
        self.research.commit(self.research.prepare('next',question='Do those conditions also hold on another device?'))
        self.app.select(keys[0]); self.app.keep_draft('Generalization remains open.','Only the original device has a measurement.')
        work = self.app.review.candidates()
        child = work.create('claim',{'role':'subclaim','statement':'A second device needs an independent check.',
            'scope':'Not yet measured','parent_ids':[keys[0]]})
        preview = self.research.prepare('reasoning')
        self.assertTrue(preview.display['ai_origin_retained']); self.assertFalse(preview.display['recording_available'])
        self.research.commit(self.research.prepare('reasoning',explanation_state='leave-for-later'))
        returned = project_workspace(self.store.load())
        second = returned.paper.recorded_origins()[1]
        inherited = next(o for o in second['lineages'] if o['revisions'][-1]['amendment']['id']==keys[0])
        self.assertIn(inherited,first['lineages'])
        self.assertEqual(request_id,inherited['revisions'][0]['advisory_origin']['request_id'])
        self.assertIn(child,{r['id'] for r in returned.paper.history.view('main')['changes']})

    def test_stale_cancel_failed_save_and_tampered_origin_preserve_personal_work(self):
        from claimbranch.application.paper_work_store import PaperWork
        _, _, work, request_id, keys = self.candidates()
        self.app.recovery.save(self.app)
        original = self.store.load().payload
        from contextlib import nullcontext
        for failure in ('cancel','expiry','edit','save'):
            with self.subTest(failure=failure):
                self.research.clock = lambda:2000000000
                preview = self.research.prepare('reasoning',explanation_state='leave-for-later')
                if failure == 'cancel':self.research.cancel()
                if failure == 'expiry':self.research.clock = lambda:2000000300
                if failure == 'edit':self.app.keep_note('Newer writing')
                with patch('claimbranch.application.paper_work_store.os.replace',side_effect=OSError('injected')) if failure=='save' else nullcontext():
                    with self.assertRaises(ContractError):self.research.commit(preview)
                self.assertEqual(original,self.store.load().payload)
                self.assertEqual([],self.app.paper.recorded_origins())
                self.assertTrue(work.origins[keys[0]].ai_influenced)
        self.research.commit(self.research.prepare('reasoning',explanation_state='leave-for-later'))
        project = self.store.load()
        for field in ('passage','action_id'):
            value = decode(project.work.payload)
            origin = value['workspace']['proposals']['recorded'][0]['lineages'][0]['revisions'][0]['advisory_origin']
            origin[field] = 'rewritten'
            with self.assertRaises(ContractError):project.with_work(PaperWork(canonical_bytes(value)))
        self.assertEqual(project.payload,self.store.load().payload)


if __name__ == '__main__': unittest.main()
