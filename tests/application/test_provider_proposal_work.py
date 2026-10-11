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
    def pending(self, app=None, *, clock=None, include_draft=False, value=None):
        from claimbranch.application.paper_proposal_work import CodexProposalWork
        from claimbranch.application.codex_app_server import CodexAppServerTransport, CodexResult
        from claimbranch.application.provider_profile import CodexProfile
        import tempfile
        from pathlib import Path
        import sys
        app = app or fixture()
        worker = CodexProposalWork(app.paper, app.context_key(), clock=clock or (lambda:100))
        prepared = worker.prepare(request(app), profile=CodexProfile.create(model='gpt-6.1-sol'), include_draft=include_draft)
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


if __name__ == '__main__': unittest.main()
