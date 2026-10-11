"""Owned selective proposal incorporation and ordinary-file origin return."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.paper_proposal_work import PaperProposalWork
from claimbranch.application.tui_work_recovery import snapshot, restore
from tests.application.test_paper_proposals import response


def fixture():
    history = ResearchHistory.start_paper_series('cache-study', 'Cache study', 'thesis',
        'Caching improves latency on CPU-A and CPU-B.', 'anchor')
    def append(kind, payload):
        nonlocal history
        history = history.append({'schema_version': 3, 'id': 'op-'+str(len(history.commands)+1),
            'project_id': 'cache-study', 'episode_id': 'episode-a', 'created_at': '2026-10-09T00:00:00Z',
            'operation_type': kind, 'expected_heads': dict(history.heads),
            'evidence_watermark': history.watermark, 'payload': payload})
    append('open-episode', {'title': 'CPU-A result', 'question': 'Can CPU-A support the CPU-B claim?'})
    append('record-experiment', {'id': 'run-a', 'question': 'Does caching reduce CPU-A latency?',
        'method': 'Ten repetitions with and without caching', 'conditions': 'CPU-A, fixed workload',
        'metric': {'name': 'latency', 'definition': 'Mean elapsed time', 'unit': 'ms', 'comparison': '15 ms without caching'},
        'source_ref': 'synthetic:cpu-a'})
    append('record-evidence-event', {'event_id': 'event-a', 'target_id': 'obs-a', 'run_id': 'run-a',
        'action': 'confirm', 'statement': 'Caching took 6 ms versus 15 ms on CPU-A.', 'value': '6',
        'rationale': 'Invented fixture result', 'supersedes_id': None})
    app = TerminalWorkspace(history, ai_off=True)
    app.keep_draft('CPU-B is still unmeasured.', 'Only CPU-A was tested.')
    return app


def request(app):
    return {'schema_version': 1, 'project_id': 'cache-study', 'episode_id': 'episode-a',
        'ref': 'main', 'view_digest': app.view['digest'], 'purpose': 'critique-interpretation',
        'selections': [{'record_id': 'thesis', 'fields': ['statement', 'role']},
            {'record_id': 'obs-a', 'fields': ['statement', 'status', 'value', 'conditions', 'metric']}],
        'scientific_edge_ids': []}


def ready(app, *, include_draft=False, value=None, clock=None):
    worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(value or response()), clock=clock or (lambda: 100))
    outbound = worker.prepare(request(app), include_draft=include_draft)
    worker.begin(outbound)
    worker.complete(outbound.request_id)
    return worker


class SelectiveProposalWorkTests(unittest.TestCase):
    def test_one_relationship_keeps_manual_judgment_and_independent_sibling(self):
        app = fixture(); before = app.paper.history.manifest(); worker = ready(app)
        sibling = worker.compare(['narrow'])
        compared = worker.compare(['limit'])
        staged = worker.stage(compared)
        work = app.paper.candidates(*app.context_key())
        self.assertEqual(1, len(work.records)); self.assertEqual(1, len(staged))
        self.assertEqual('scientific-edge', next(iter(work.records.values()))['kind'])
        self.assertTrue(next(iter(work.origins.values())).ai_influenced)
        self.assertFalse(app.review.session().state()['draft']['ai_influenced'])
        self.assertEqual(before, app.paper.history.manifest())
        worker.stage(sibling)
        self.assertEqual(2, len(work.records))

    def test_complete_dependency_batch_and_changed_dependency_comparison(self):
        app = fixture(); worker = ready(app)
        compared = worker.compare(['repeat'])
        self.assertEqual(['narrow'], compared['required_item_ids'])
        ids = worker.stage(compared)
        self.assertEqual(2, len(ids))
        work = app.paper.candidates(*app.context_key())
        plan = next(record for record in work.records.values() if record['kind'] == 'experiment-plan')
        claim = work.records[plan['body']['claim_id']]
        compared = worker.compare(['repeat'])
        claim['body']['statement'] = 'A human-narrowed CPU-A claim.'
        work.put(claim)
        with self.assertRaises(ContractError): worker.stage(compared)
        self.assertTrue(work.origins[claim['id']].ai_influenced)
        self.assertEqual(2, len(decode(work.origins[claim['id']].payload)['revisions']))

    def test_comparison_tampering_and_editor_change_cannot_stage(self):
        app = fixture(); worker = ready(app)
        compared = worker.compare(['limit']); altered = deepcopy(compared)
        altered['records'][0]['body']['rationale'] = 'Tampered content'
        with self.assertRaises(ContractError): worker.stage(altered)
        app.keep_draft('Further manual thought', 'Same measured source')
        with self.assertRaises(ContractError): worker.stage(compared)
        worker.stage(worker.compare(['limit']))
        self.assertEqual('Further manual thought', app.draft()['text'])

    def test_included_draft_change_and_cancel_leave_response_historical(self):
        app = fixture(); worker = ready(app, include_draft=True)
        app.keep_draft('Changed input', 'Same reason')
        with self.assertRaises(ContractError): worker.compare(['limit'])
        self.assertIsNotNone(worker.historical()[0]['result'])
        app = fixture(); worker = ready(app)
        compared = worker.compare(['limit']); worker.cancel()
        with self.assertRaises(ContractError): worker.stage(compared)
        self.assertEqual({}, app.paper.candidates(*app.context_key()).records)

    def test_restart_retains_item_origin_and_count_without_staging_capability(self):
        app = fixture(); worker = ready(app); worker.stage(worker.compare(['repeat']))
        saved = snapshot(app)
        self.assertEqual('claimbranch.paper-work/v8', decode(saved.payload)['schema'])
        reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        work = reopened.paper.candidates(*reopened.context_key())
        self.assertEqual(2, len(work.origins))
        self.assertEqual(1, reopened.review.session()._prior_dispatches)
        historical = reopened.paper.proposal_history()
        self.assertEqual(1, len(historical)); self.assertFalse(historical[0]['staging_available'])
        self.assertEqual(3, len(historical[0]['result']['items']))
        self.assertFalse(reopened.paper.ai_available)
        record = next(iter(work.records.values())); record['body']['statement'] = 'Kept after return'
        work.put(record)
        self.assertTrue(work.origins[record['id']].ai_influenced)

    def test_revision_limit_and_atomic_capacity_failure_keep_prior_candidates(self):
        app = fixture(); worker = ready(app)
        compared = worker.compare(['repeat'])
        with patch('claimbranch.application.paper_proposal_work.check_capacity', side_effect=ContractError('full checkpoint')):
            with self.assertRaises(ContractError): worker.stage(compared)
        self.assertEqual({}, worker.work.records); self.assertEqual({}, worker.work.origins)
        worker.stage(compared)
        key = next(key for key, r in worker.work.records.items() if r['kind'] == 'claim')
        for number in range(7):
            record = worker.work.records[key]; record['body']['statement'] = 'Human revision '+str(number)
            worker.work.put(record)
        previous = worker.work.records; origin = worker.work.origins[key]
        record['body']['statement'] = 'Ninth kept revision'
        with self.assertRaises(ContractError): worker.work.put(record)
        self.assertEqual(previous, worker.work.records); self.assertEqual(origin, worker.work.origins[key])

    def test_payload_erasure_preserves_required_item_material_and_editability(self):
        app = fixture(); worker = ready(app); ids = worker.stage(worker.compare(['repeat']))
        origins = worker.work.origins
        worker.erase_payload(worker._current)
        self.assertEqual('erased', worker.historical()[0]['payload_availability'])
        self.assertIsNone(worker.historical()[0]['result'])
        saved = snapshot(app); reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        self.assertEqual(origins, reopened.paper.candidates(*reopened.context_key()).origins)
        with self.assertRaises(ContractError): worker.compare(['limit'])
        self.assertEqual(set(ids), set(reopened.paper.candidates(*reopened.context_key()).records))

    def test_new_optional_payload_quota_preserves_session_reading_and_saved_writing(self):
        app = fixture()
        worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(response()), clock=lambda:100)
        outbound = worker.prepare(request(app)); worker.begin(outbound)
        with patch('claimbranch.application.paper_proposal_work.check_capacity', side_effect=ContractError('raw quota')):
            worker.complete(outbound.request_id)
        self.assertEqual('not-retained', app.paper.proposal_history()[0]['payload_availability'])
        self.assertIsNotNone(worker.historical()[0]['result'])
        saved = snapshot(app)
        self.assertEqual('Only CPU-A was tested.', decode(saved.payload)['workspace']['drafts'][0]['rationale'])
        self.assertIsNone(decode(saved.payload)['workspace']['proposals']['attempts'][0]['result'])

    def test_cancelled_late_and_malformed_arrivals_keep_manual_path(self):
        for raw in (canonical_bytes(response()), b'{bad'):
            app = fixture(); worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=raw, clock=lambda:100)
            outbound = worker.prepare(request(app)); worker.begin(outbound); worker.cancel(); worker.complete(outbound.request_id)
            snapshot(app)
            self.assertEqual('CPU-B is still unmeasured.', app.draft()['text'])
            with self.assertRaises(ContractError): worker.compare(['limit'])

    def test_pending_restart_and_duplicate_arrival_never_restore_consent(self):
        app = fixture(); worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(response()), clock=lambda:100)
        outbound = worker.prepare(request(app)); worker.begin(outbound)
        saved = snapshot(app); reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        self.assertFalse(reopened.paper.proposal_history()[0]['staging_available'])
        self.assertEqual((), reopened.review.session()._broker.dispatched)
        worker.complete(outbound.request_id)
        with self.assertRaises(ContractError): worker.complete(outbound.request_id)
        self.assertEqual(1, len(app.paper.proposal_history()))

    def test_unkeep_keeps_last_origin_beside_unfinished_candidate(self):
        app = fixture(); worker = ready(app); key = worker.stage(worker.compare(['narrow']))[0]
        record = worker.work.unkeep(key)
        app.review.candidate_works[app.review.key] = worker.work
        app.review.candidate_inputs[app.review.key] = {key: record}
        saved = snapshot(app); reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
        self.assertTrue(reopened.paper.candidates(*reopened.context_key()).origins[key].ai_influenced)

    def test_replacement_preserves_late_trace_and_revokes_old_comparison(self):
        app = fixture(); first = ready(app); compared = first.compare(['limit'])
        second = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(response()), clock=lambda:100)
        outbound = second.prepare(request(app)); second.begin(outbound)
        with self.assertRaises(ContractError): first.stage(compared)
        third = second.prepare(request(app)); second.begin(third)
        second.complete(outbound.request_id); second.complete(third.request_id)
        self.assertEqual(3, len(app.paper.proposal_history())); snapshot(app)
        self.assertEqual('cancelled', app.paper.proposal_history()[1]['disposition'])
        self.assertTrue(app.paper.proposal_history()[1]['trace_digest'])
        with self.assertRaises(ContractError): second.prepare(request(app))

    def test_source_change_and_expiry_preserve_live_and_historical_writing(self):
        app = fixture(); clock = [100]; worker = ready(app, clock=lambda:clock[0])
        compared = worker.compare(['limit']); clock[0] = 220
        with self.assertRaises(ContractError): worker.stage(compared)
        self.assertEqual({}, worker.work.records)
        app = fixture(); worker = ready(app); compared = worker.compare(['limit'])
        history = app.paper.history
        command = {'schema_version':3, 'id':'correction', 'project_id':'cache-study', 'episode_id':'episode-a',
            'created_at':'2026-10-09T00:00:00Z', 'operation_type':'record-evidence-event',
            'expected_heads':dict(history.heads), 'evidence_watermark':history.watermark,
            'payload':{'event_id':'event-corrected','target_id':'obs-a','run_id':'run-a','action':'correct',
                'statement':'Corrected elapsed time is 8 ms.', 'value':'8','rationale':'Timer calibration','supersedes_id':'event-a'}}
        app.paper.update_history(history.append(command))
        with self.assertRaises(ContractError): worker.stage(compared)
        self.assertEqual('CPU-B is still unmeasured.', worker.session.state()['draft']['text'])

    def test_unknown_workspace_and_tampered_trace_refuse_without_conversion(self):
        from claimbranch.application.paper_work_store import PaperWork
        app = fixture(); ready(app); saved = snapshot(app); value = decode(saved.payload)
        value['workspace']['proposals']['attempts'][0]['trace_digest'] = 'a'*64
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(value))
        value = decode(saved.payload)['workspace']; value['schema'] = 'claimbranch.proposal-workspace/v8'
        with self.assertRaises(ContractError): PaperWork.create(saved.history, workspace=value)

    def test_unselected_collision_is_refused_before_publishing_any_dependency(self):
        app = fixture(); worker = ready(app)
        with patch.object(worker.work, 'allocate_id', return_value='thesis'):
            with self.assertRaises(ContractError): worker.compare(['repeat'])
        self.assertEqual({}, worker.work.records)

    def test_retained_origin_cannot_attribute_different_content_to_provider(self):
        from claimbranch.application.paper_work_store import PaperWork
        app = fixture(); worker = ready(app); worker.stage(worker.compare(['limit']))
        value = decode(snapshot(app).payload)
        value['workspace']['authoring']['candidates'][0]['records'][0]['body']['rationale'] = 'Different scientific reason'
        origin = value['workspace']['proposals']['origins'][0]['lineages'][0]
        origin['revisions'][0]['amendment']['body']['rationale'] = 'Different scientific reason'
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(value))

    def test_real_whole_checkpoint_quota_prioritizes_writing_over_new_payload(self):
        value = response(); value['critique'] = 'c'*16000
        value['items'][0]['body']['statement'] = 's'*16000
        value['items'][0]['body']['scope'] = 'q'*16000
        app = fixture(); worker = ready(app, value=value)
        for index in range(13):
            worker.work.create('claim', {'role':'main', 'statement':'m'*15300, 'scope':'CPU-A', 'parent_ids':['thesis']})
        app.notes[app.context_key()] = 'n'*12000
        saved = snapshot(app)
        attempt = decode(saved.payload)['workspace']['proposals']['attempts'][0]
        self.assertLessEqual(len(saved.payload), 262144)
        self.assertEqual('not-retained', attempt['payload_availability'])
        self.assertIsNone(attempt['result']); self.assertEqual(13, len(worker.work.records))
        self.assertIsNotNone(worker.historical()[0]['result'])
        from claimbranch.application.paper_proposal_work import mark_saved
        app = fixture(); worker = ready(app, value=value)
        mark_saved(app.paper, decode(snapshot(app).payload)['workspace'])
        for index in range(13):
            worker.work.create('claim', {'role':'main', 'statement':'m'*15300, 'scope':'CPU-A', 'parent_ids':['thesis']})
        app.notes[app.context_key()] = 'n'*12000
        with self.assertRaisesRegex(ContractError, 'byte limit'): snapshot(app)
        self.assertEqual('available', app.paper.proposal_history()[0]['payload_availability'])

    def test_minimal_attempt_reservation_refuses_before_consuming_request(self):
        app = fixture(); worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(response()), clock=lambda:100)
        outbound = worker.prepare(request(app))
        with patch('claimbranch.application.paper_proposal_work.check_capacity', side_effect=ContractError('full checkpoint')):
            with self.assertRaises(ContractError): worker.begin(outbound)
        self.assertEqual([], app.paper.proposal_history()); self.assertEqual((), worker.session._broker.dispatched)
        worker.begin(outbound); self.assertEqual(1, len(app.paper.proposal_history()))

    def test_repeated_item_ids_in_new_response_create_independent_candidates(self):
        app = fixture(); worker = ready(app)
        first = worker.stage(worker.compare(['narrow']))[0]
        human = worker.work.records[first]; human['body']['statement'] = 'My retained narrower claim'
        worker.work.put(human)
        outbound = worker.prepare(request(app)); worker.begin(outbound); worker.complete(outbound.request_id)
        second = worker.stage(worker.compare(['narrow']))[0]
        self.assertNotEqual(first, second)
        self.assertEqual(human, worker.work.records[first])

    def test_failed_identity_allocation_can_be_compared_again(self):
        app = fixture(); worker = ready(app)
        with patch.object(worker.work, 'allocate_id', return_value='thesis'):
            with self.assertRaises(ContractError): worker.compare(['repeat'])
        worker.stage(worker.compare(['repeat']))
        self.assertEqual(2, len(worker.work.records))

    def test_attempt_reader_refuses_inconsistent_unspent_response(self):
        from claimbranch.application.paper_work_store import PaperWork
        app = fixture(); ready(app); value = decode(snapshot(app).payload)
        entry = value['workspace']['proposals']['attempts'][0]
        entry.update(dispatched=False, trace_digest=None, response_digest=None, provider_disposition=None)
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(value))

    def test_required_staging_can_drop_only_a_never_saved_optional_payload(self):
        value = response(); value['critique'] = 'c'*16000
        app = fixture(); worker = ready(app, value=value)
        for node in ('thesis', 'obs-a', 'run-a'):
            owner = ('episode-a', 'main', node)
            app.notes[owner] = 'n'*12000
            app.drafts[owner] = {'text':'t'*12000, 'rationale':'r'*12000}
            app.review.buffers[owner] = {'text':'b'*12000, 'rationale':'r'*12000}
            app.unfinished[(*owner, 'note')] = ['u'*12000]
            app.unfinished[(*owner, 'edit')] = ['e'*3000, 'r'*3000]
        app.unfinished[(*app.context_key(), 'edit')][0] = 'e'*10356
        # Fit valid writing immediately below the aggregate envelope boundary,
        # including the enclosing work, rather than only the workspace object.
        import json
        raw = decode(snapshot(app).payload)
        raw['workspace']['proposals']['attempts'][0].update(result=value, payload_availability='available')
        size = len(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
        app.unfinished[(*app.context_key(), 'edit')][0] = 'e'*(10356 - (size - (262144-64)))
        self.assertEqual('available', decode(snapshot(app).payload)['workspace']['proposals']['attempts'][0]['payload_availability'])
        worker.stage(worker.compare(['limit']))
        self.assertEqual(1, len(worker.work.records)); self.assertTrue(worker.work.origins)
        record = next(iter(worker.work.records.values())); record['body']['rationale'] = 'Human scope correction'
        worker.work.put(record)
        self.assertEqual('not-retained', decode(snapshot(app).payload)['workspace']['proposals']['attempts'][0]['payload_availability'])

    def test_ai_edit_preserves_prior_kept_human_candidate_and_comparison(self):
        from dataclasses import asdict
        app = fixture(); history = app.paper.history
        for kind, payload in [('create-reasoning-branch', {}), ('record-interpretation', {
            'changes':[{'id':'claim-a','kind':'claim','body':{'role':'main','statement':'Recorded CPU-A claim',
                'scope':'CPU-A','parent_ids':['thesis']}}, {'id':'reading-a','kind':'interpretation',
                'body':{'statement':app.draft()['text'],'observation_ids':['obs-a']}}],
            'judgment':asdict(app.review.session()._current_judgment())})]:
            history = history.append({'schema_version':3,'id':'setup-'+str(len(history.commands)),
                'project_id':'cache-study','episode_id':'episode-a','created_at':'2026-10-09T00:00:00Z',
                'operation_type':kind,'expected_heads':dict(history.heads),'evidence_watermark':history.watermark,'payload':payload})
        app = TerminalWorkspace(history, ai_off=True); app.switch_context('episode-a','alternative')
        app.keep_draft('A human judgment', 'My existing reason')
        value = response(); value['items'] = [value['items'][0]]
        value['items'][0].update(action='edit', target_id='claim-a')
        worker = PaperProposalWork(app.paper, app.context_key(), frozen_result=canonical_bytes(value), clock=lambda:100)
        query = request(app); query.update(ref='alternative',view_digest=app.view['digest'])
        query['selections'].append({'record_id':'claim-a','fields':['statement','role']})
        human = {'id':'claim-a','kind':'claim','body':{'role':'main','statement':'My kept human wording',
            'scope':'CPU-A','parent_ids':['thesis']}}
        worker.work.put(human)
        outbound = worker.prepare(query); worker.begin(outbound); worker.complete(outbound.request_id)
        compared = worker.compare(['narrow']); self.assertEqual([human], compared['previous_records'])
        worker.stage(compared)
        revisions = decode(worker.work.origins['claim-a'].payload)['revisions']
        self.assertEqual(human, revisions[0]['amendment']); self.assertIsNone(revisions[0]['proposal_origin'])
        self.assertEqual('edit', revisions[1]['proposal_origin']['item']['action'])
        snapshot(app)

    def test_existing_recovery_marks_payload_saved_only_after_success(self):
        from unittest.mock import Mock
        from claimbranch.application.tui_work_recovery import JudgmentRecovery
        app = fixture(); store = Mock(); store.load.return_value = None
        recovery = JudgmentRecovery(store, app); app.recovery = recovery
        worker = ready(app); key = worker._current
        store.save.side_effect = ContractError('injected save failure')
        with self.assertRaises(ContractError): recovery.save(app)
        self.assertNotIn(key, app.paper._saved_proposal_payloads)
        store.save.side_effect = None; recovery.save(app)
        self.assertIn(key, app.paper._saved_proposal_payloads)


class PersonalProposalReturnTests(unittest.TestCase):
    from tests.application.test_personal_research import PersonalResearchTests as _fixture
    setUp = _fixture.setUp
    result = _fixture.result
    confirm_result = _fixture.confirm_result

    def stage_relationship(self, *, full=False):
        observation = self.confirm_result()
        self.app.select('thesis'); self.app.keep_draft('The tested input changes latency.', 'Only this hardware was measured.')
        value = response()
        if not full: value['items'] = [value['items'][1]]
        next(i for i in value['items'] if i['id']=='limit')['body']['source_id']['id'] = observation
        query = {'schema_version':1, 'project_id':self.app.view['project_id'], 'episode_id':self.app.episode_id,
            'ref':'main', 'view_digest':self.app.view['digest'], 'purpose':'compare-evidence',
            'selections':[{'record_id':'thesis','fields':['statement','role']},
                          {'record_id':observation,'fields':['statement','status','value','conditions','metric']}],
            'scientific_edge_ids':[]}
        worker = PaperProposalWork(self.app.paper, self.app.context_key(), frozen_result=canonical_bytes(value), clock=lambda:100)
        outbound = worker.prepare(query); worker.begin(outbound); worker.complete(outbound.request_id)
        key = worker.stage(worker.compare(['limit']))[0]
        self.app.review.candidate_works[self.app.review.key] = worker.work
        return observation, worker, key

    def test_manual_judgment_ai_relationship_record_correct_backup_and_fresh_process(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        observation, worker, key = self.stage_relationship()
        record = worker.work.records[key]; record['body']['rationale'] = 'A human edit keeps the measurement scope.'
        worker.work.put(record)
        preview = self.research.prepare('reasoning')
        self.assertTrue(preview.display['ai_origin_retained']); self.assertFalse(preview.display['recording_available'])
        with self.assertRaises(ContractError): self.research.commit(preview)
        preview = self.research.prepare('reasoning', explanation_state='leave-for-later')
        self.research.commit(preview)
        self.assertEqual('not-required', decode(self.app.paper.history.commands[-1])['payload']['disposition'])
        self.assertEqual('leave-for-later', self.app.paper.recorded_origins()[0]['explanation']['state'])
        self.assertTrue(self.app.paper.recorded_origins()[0]['lineages'])
        self.app.select(observation)
        correction = self.app.intake.create(self.app.context_key())
        for field, text in {'observation':'Corrected latency: 23 ms', 'value':'23', 'rationale':'Timer offset corrected.'}.items():
            self.app.intake.keep(correction, field, text)
        self.research.commit(self.research.prepare('correct', item_id=correction))
        before = self.app.paper.recorded_origins(); backup = self.store.backup()
        destination = self.directory.parent/'restored'; destination.mkdir(mode=0o700)
        restored_project = PersonalProjectStore.restore_backup(backup, destination)
        reopened = project_workspace(restored_project)
        self.assertEqual(before, reopened.paper.recorded_origins()); self.assertFalse(reopened.paper.ai_available)
        self.assertEqual('Only this hardware was measured.', reopened.paper.recorded_origins()[0]['cause']['judgment']['rationale'])
        script = 'from claimbranch.application.personal_project import PersonalProjectStore\nfrom claimbranch.application.tui_project import project_workspace\nimport sys\nwith PersonalProjectStore(sys.argv[1]) as store:\n app=project_workspace(store.load()); r=app.paper.recorded_origins(); assert len(r)==1; assert len(r[0]["lineages"][0]["revisions"])==2; assert not app.paper.ai_available; print("origin-return-ok")'
        run = subprocess.run([sys.executable, '-B', '-c', script, str(destination)], capture_output=True, text=True, timeout=30)
        self.assertEqual(0, run.returncode, run.stderr); self.assertIn('origin-return-ok', run.stdout)
        self.assertEqual(self.source, (self.paper/'paper.tex').read_bytes())

    def test_partial_explanation_returns_original_basis_without_comprehension_or_closure(self):
        self.stage_relationship()
        preview = self.research.prepare('reasoning')
        topic = preview.display['explanation_topics'][0]['id']
        self.research.keep_explanation(preview, entries=[{'topic_id':topic,'text':'아직 조건의 범위를 생각하는 중','reuse_rationale':False}])
        self.app.recovery.save(self.app)
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_research import PersonalResearch
        reopened = project_workspace(self.store.load())
        context = PersonalResearch(reopened).explanation_contexts()[0]
        self.assertEqual('partial', context['explanation']['state'])
        self.assertEqual('아직 조건의 범위를 생각하는 중', context['explanation']['entries'][0]['text'])
        self.assertFalse(context['closure_available'])

    def test_failed_ai_record_preserves_live_origin_and_saved_original(self):
        self.stage_relationship(); before = self.app.paper.history.manifest(); saved = self.store.load().payload
        preview = self.research.prepare('reasoning', explanation_state='leave-for-later')
        with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('injected')):
            with self.assertRaises(ContractError): self.research.commit(preview)
        self.assertEqual(before, self.app.paper.history.manifest()); self.assertEqual(saved, self.store.load().payload)
        self.assertEqual([], self.app.paper.recorded_origins())

    def test_existing_saved_origin_cannot_be_dropped_by_workspace_downgrade(self):
        self.stage_relationship(); self.research.commit(self.research.prepare('reasoning', explanation_state='leave-for-later'))
        project = self.store.load(); value = decode(project.work.payload)['workspace']
        value.pop('proposals'); value['schema'] = 'claimbranch.review-pool-workspace/v6'
        from claimbranch.application.paper_work_store import PaperWork
        with self.assertRaises(ContractError): project.with_work(PaperWork.create(project.work.history, workspace=value))

    def test_changed_explanation_cause_retains_earlier_partial_writing(self):
        self.stage_relationship()
        preview = self.research.prepare('reasoning')
        self.research.keep_explanation(preview, entries=[{'topic_id':preview.display['explanation_topics'][0]['id'],
            'text':'Earlier scope explanation', 'reuse_rationale':False}])
        earlier = deepcopy(self.app.paper._personal_explanations[0])
        self.app.keep_draft('A different interpretation of the same result.', 'Changed research reason.')
        preview = self.research.prepare('reasoning')
        self.research.keep_explanation(preview, entries=[{'topic_id':preview.display['explanation_topics'][0]['id'],
            'text':'Later reasoning remains separate', 'reuse_rationale':False}])
        contexts = self.research.explanation_contexts()
        self.assertEqual(2, len(contexts))
        self.assertEqual(earlier['cause'], contexts[0]['cause'])
        self.assertEqual('Earlier scope explanation', contexts[0]['explanation']['entries'][0]['text'])
        self.app.recovery.save(self.app)

    def test_recorded_original_reason_must_match_its_actual_history_command(self):
        from claimbranch.application.paper_work_store import PaperWork
        self.stage_relationship(); self.research.commit(self.research.prepare('reasoning', explanation_state='leave-for-later'))
        value = decode(self.store.load().work.payload)
        judgment = value['workspace']['proposals']['recorded'][0]['cause']['judgment']
        judgment['rationale'] = 'A reason never recorded by the person'
        judgment['history'][-1]['rationale'] = judgment['rationale']
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(value))

    def test_saved_kept_candidate_cannot_drop_or_truncate_its_ai_origin(self):
        from claimbranch.application.paper_work_store import PaperWork
        self.stage_relationship(); self.app.recovery.save(self.app)
        project = self.store.load(); value = decode(project.work.payload)['workspace']
        value['proposals']['origins'] = []
        with self.assertRaises(ContractError): project.with_work(PaperWork.create(project.work.history, workspace=value))

    def test_omitted_plan_stays_unrecorded_and_later_derivation_inherits_claim_origin(self):
        _, worker, _ = self.stage_relationship(full=True)
        worker.stage(worker.compare(['repeat']))
        plan = next(r for r in worker.work.records.values() if r['kind']=='experiment-plan')
        claim = worker.work.records[plan['body']['claim_id']]
        worker.work.toggle(plan['id'])
        self.research.commit(self.research.prepare('reasoning', explanation_state='leave-for-later'))
        first = self.app.paper.recorded_origins()[0]
        self.assertEqual(2, len(first['lineages']))
        self.assertNotIn(plan['id'], {r['id'] for r in self.app.paper.history.view('main')['changes']})
        self.assertEqual(3, len(self.app.paper.proposal_history()[0]['result']['items']))
        from claimbranch.core.canonical import digest
        from claimbranch.application.paper_work_store import PaperWork
        bad = decode(self.store.load().work.payload)
        record = bad['workspace']['proposals']['recorded'][0]
        record['lineages'].append(decode(worker.work.origins[plan['id']].payload))
        record['cause']['origin_digests'] = sorted(digest(o) for o in record['lineages'])
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(bad))
        self.research.commit(self.research.prepare('next', question='Does that narrowed claim hold on CPU-B?'))
        self.app.select(claim['id']); self.app.keep_draft('The earlier claim remains limited.', 'CPU-B has no new measurement.')
        work = self.app.review.candidates()
        work.create('claim', {'role':'subclaim','statement':'The CPU-A scope needs a distinct CPU-B check.',
            'scope':'CPU-B untested','parent_ids':[claim['id']]})
        preview = self.research.prepare('reasoning')
        self.assertTrue(preview.display['ai_origin_retained']); self.assertFalse(preview.display['recording_available'])
        self.research.commit(self.research.prepare('reasoning', explanation_state='leave-for-later'))
        second = self.app.paper.recorded_origins()[1]
        self.assertIn(claim['id'], {o['revisions'][-1]['amendment']['id'] for o in second['lineages']})
        self.app.recovery.save(self.app)

    def test_personal_review_can_explicitly_reuse_original_reason(self):
        self.stage_relationship(); preview = self.research.prepare('reasoning')
        entries = [{'topic_id':t['id'],'text':'','reuse_rationale':True} for t in preview.display['explanation_topics']]
        self.research.commit(self.research.prepare('reasoning', explanation_state='reviewed', explanation_entries=entries))
        record = self.app.paper.recorded_origins()[0]
        self.assertEqual('reviewed', record['explanation']['state'])
        self.assertEqual('Only this hardware was measured.', record['cause']['judgment']['rationale'])
        self.assertTrue(all(e['reuse_rationale'] and not e['text'] for e in record['explanation']['entries']))

    def test_saved_raw_payload_requires_explicit_erasure_instead_of_quota_eviction(self):
        from claimbranch.application.paper_work_store import PaperWork
        self.stage_relationship(); self.app.recovery.save(self.app)
        project = self.store.load(); value = decode(project.work.payload)['workspace']
        value['proposals']['attempts'][0].update(result=None, payload_availability='not-retained')
        with self.assertRaises(ContractError): project.with_work(PaperWork.create(project.work.history, workspace=value))
        self.app.paper.erase_proposal_payload(value['proposals']['attempts'][0]['request_id'])
        self.app.recovery.save(self.app)
        self.assertEqual('erased', self.app.paper.proposal_history()[0]['payload_availability'])


if __name__ == '__main__': unittest.main()
