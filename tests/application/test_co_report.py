from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned scoped reading bundles; global evidence, origin and exact review."""
import unittest
import json
import io
from copy import deepcopy
from unittest.mock import patch
from application import test_claim_wording as wording_tests
from claimbranch.application.co_report import prepare_co_report,recheck_co_report
from claimbranch.application.paper_service import PaperService
from claimbranch.application.personal_project import PersonalProjectStore,CO_REPORT_PERSONAL_MAGIC
from claimbranch.application.personal_archive import split_personal_backup,CO_REPORT_BACKUP_MAGIC
from claimbranch.application.tui_project import project_workspace
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode,encode

class CoReportTests(unittest.TestCase):
    setUp=wording_tests.ClaimWordingTests.setUp
    companion=wording_tests.ClaimWordingTests.companion
    register=wording_tests.ClaimWordingTests.register

    def request(self,**changes):
        result=dict(schema='claimbranch.co-report/v1',id='decision',candidates=[
            dict(id='primary',statement='The unit-level rubric result is positive.',scope='Primary unit-level definition only',observation_ids=['O'],claim_id='C',edge_id='primary-edge',edge_type='supports',source_id=None,origin='human'),
            dict(id='sensitivity',statement='The grouped reading limits the primary conclusion.',scope='Grouped sensitivity definition only',observation_ids=['O'],claim_id='T',edge_id='sensitivity-edge',edge_type='qualifies',source_id=None,origin='unknown')],
            selected_ids=['primary','sensitivity'],companion_ids=['co-report'],judgment='Report both definition-specific readings.',rationale='The sensitivity must accompany the primary reading.',disposition='deferred',answers=[])
        result.update(changes);return result

    def base(self):return self.companion(self.project,companion_id='T')[0]

    def test_both_scoped_readings_reach_main_once_without_changing_evidence_status(self):
        base=self.base();before=base.work.history.view('main');project,preview=prepare_co_report(base,self.request())
        after=project.work.history.view('main')
        self.assertEqual(before['evidence'],after['evidence']);self.assertEqual(before['claims'],after['claims'])
        self.assertEqual({'primary','sensitivity'},{i['id'] for i in after['interpretations']})
        self.assertEqual('co-reported',preview['decision']['disposition'])
        self.assertEqual('deferred',preview['decision']['explanation_disposition'])
        self.assertFalse(preview['decision']['understanding_verified'])
        self.assertEqual(base.work.history.commands,project.work.history.commands[:-1]);self.assertEqual(base.work.history.seed,project.work.history.seed)
        graph=PaperService(project.work.history).query('main')
        relation=next(e for e in graph['relations'] if e['type']=='co-reported-with');self.assertFalse(relation['scientific'])
        app=project_workspace(project);app.select('sensitivity');self.assertIn('Grouped sensitivity definition only',str(app.detail()))
        self.assertEqual('claimbranch.project-work/v18',decode(project.payload,purpose='project')['schema'])

    def test_membership_companion_and_basis_failures_refuse_entire_transaction(self):
        base=self.base();original=base.payload
        for change in (dict(selected_ids=['primary']),dict(selected_ids=['primary','missing']),dict(companion_ids=[]),dict(companion_ids=['missing'])):
            with self.assertRaises(ContractError):prepare_co_report(base,self.request(**change))
        request=self.request();request['candidates'][1]['observation_ids']=['missing']
        with self.assertRaises(ContractError):prepare_co_report(base,request)
        request=self.request();request['candidates'][1]['id']='C';request['selected_ids']=['primary','C']
        with self.assertRaises(ContractError):prepare_co_report(base,request)
        self.assertEqual(original,base.payload)

    def test_omitted_independent_candidate_is_retained_without_becoming_science(self):
        base=self.base();request=self.request()
        extra={**request['candidates'][0],'id':'unused','edge_id':'unused-edge','statement':'An omitted AI idea.','origin':'ai'}
        request['candidates'].append(extra)
        project,preview=prepare_co_report(base,request)
        self.assertEqual(['unused'],preview['decision']['omitted_ids'])
        self.assertNotIn('unused',{n['id'] for n in preview['after']['nodes']})
        self.assertIn('An omitted AI idea.',str(decode(project.work.history.commands[-1],purpose='history')))
        self.assertNotIn('unused',preview['decision']['reading_origins'])
        request['selected_ids']=['primary','unused']
        with self.assertRaisesRegex(ContractError,'companion reading'):prepare_co_report(base,request)

    def test_companion_change_or_stale_basis_refuses_old_command_and_preview(self):
        base=self.base();project,preview=prepare_co_report(base,self.request());recheck_co_report(base,preview)
        changed,_=self.companion(base,companion_id='T',status='retired')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_co_report(changed,preview)
        command=decode(project.work.history.commands[-1],purpose='history')
        # Exercise context staleness independently of elapsed wall-clock seconds.
        command['created_at']=decode(changed.work.history.commands[-1],purpose='history')['created_at']
        command['expected_heads']=dict(changed.work.history.heads)
        with self.assertRaisesRegex(ContractError,'context'):changed.work.history.append(command)
        command['evidence_watermark']=999
        with self.assertRaises(ContractError):base.work.history.append(command)

    def test_repeat_selected_transaction_refuses_and_next_episode_preserves_original_scopes(self):
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.personal_project import PersonalProjectRecovery
        base=self.base();project,_=prepare_co_report(base,self.request())
        request=self.request(id='second')
        with self.assertRaisesRegex(ContractError,'previous selected'):prepare_co_report(project,request)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);app=project_workspace(project);app.recovery=PersonalProjectRecovery(store,app,project)
            service=PersonalResearch(app);service.commit(service.prepare('next',question='Does another sensitivity apply?'))
            later=store.load();request=self.request(id='later')
            for reading in request['candidates']:
                reading['source_id']=reading['id'];reading['id']='new-'+reading['id'];reading['edge_id']='new-'+reading['edge_id'];reading['statement']+=' Revised.';reading['origin']='human'
            request['selected_ids']=['new-primary','new-sensitivity']
            revised,_=prepare_co_report(later,request)
            view=revised.work.history.view('main');self.assertEqual(4,len(view['interpretations']))
            self.assertIn('unknown',view['co_reports']['later']['reading_origins']['new-sensitivity'])
            self.assertEqual('Grouped sensitivity definition only',view['co_reports']['decision']['readings'][1]['scope'])
            self.assertEqual('co-reported',revised.work.history.episodes()[0]['outcome'])

    def test_backup_return_keeps_sources_notes_and_explanation_choice(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui_work_recovery import snapshot_value
        base=self.base();app=project_workspace(base);app.select('C');app.notes[app.context_key()]='Keep an unfinished companion sentence.'
        base=base.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        project,_=prepare_co_report(base,self.request())
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC))
            backup=store.backup();self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC))
            returned=split_personal_backup(backup);self.assertEqual(project.payload,returned.payload)
            app=project_workspace(returned);self.assertIn('Keep an unfinished companion sentence.',app.notes.values())
            app.select('primary');self.assertIn('deferred',str(app.detail()));self.assertIn('ai',str(app.detail()))

    def test_unknown_or_ai_sources_cannot_become_not_required_by_declaring_human(self):
        base=self.base();request=self.request(disposition='not-required')
        for reading in request['candidates']:reading['origin']='human'
        with self.assertRaisesRegex(ContractError,'requires answer or deferral'):prepare_co_report(base,request)
        project,preview=prepare_co_report(base,self.request(disposition='answered',answers=['Both definitions and the shared source need separate inspection.']))
        self.assertFalse(preview['decision']['understanding_verified'])

    def test_cli_complete_preview_cancel_stale_input_and_confirm(self):
        from claimbranch.application.cli import main
        base=self.base();path=self.root/'co-report.json';path.write_bytes(encode(self.request(),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        args=['project','co-report','--directory',str(self.work),'--input',str(path)];before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(args+['--dry-run']))
        self.assertIn('Grouped sensitivity',output.getvalue());self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value=''),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def answer(prompt):return 'record' if prompt.startswith('Type record') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):self.assertEqual(0,main(args))
        with PersonalProjectStore(self.work) as store:self.assertEqual(2,len(store.load().work.history.view('main')['interpretations']))

    def manual_base(self):
        from claimbranch.core.research_history import ResearchHistory
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        history=ResearchHistory.start_lifecycle('manual-co','Synthetic','T','A limited thesis.','anchor')
        def append(kind,payload,key,version=4):
            nonlocal history
            history=history.append(dict(schema_version=version,id=key,project_id='manual-co',episode_id='local',created_at='2026-10-14T00:00:00Z',
                operation_type=kind,expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload))
        append('open-episode',dict(title='Two definitions',question='What does each definition show?'),'open')
        run=self.project.work.history.view('main')['experiments'][0]
        append('record-experiment',{key:run[key] for key in ('id','question','method','conditions','metric','source_ref')},'run')
        append('record-evidence-event',dict(event_id='event',target_id='O',run_id='X',action='confirm',statement='A synthetic observation.',value='0.5',rationale='Entered from owned synthetic data.',supersedes_id=None),'observe')
        append('set-claim-companion',dict(id='co-report',target_id='T',companion_id='O',scope='anchor',status='active',rationale='State the observation with this thesis.'),'companion',7)
        return ProjectWork.create(PaperWork.create(history),self.preview)

    def test_four_human_readings_and_omitted_ai_do_not_invent_ai_adoption(self):
        base=self.manual_base();request=self.request(disposition='not-required')
        for r in request['candidates']:r['claim_id']='T';r['origin']='human'
        for i in (3,4):request['candidates'].append({**request['candidates'][0],'id':f'reading-{i}','edge_id':f'edge-{i}','scope':f'Definition {i}'})
        request['selected_ids']=[r['id'] for r in request['candidates']]
        project,preview=prepare_co_report(base,request,contribution_origin='human');self.assertEqual(4,len(project.work.history.view('main')['interpretations']))
        self.assertFalse(preview['decision']['origin_review_required'])
        request['selected_ids']=['primary','sensitivity'];request['candidates'][2]['origin']='ai'
        project,preview=prepare_co_report(base,request,contribution_origin='human');self.assertFalse(preview['decision']['origin_review_required'])
        self.assertEqual(['reading-3','reading-4'],preview['decision']['omitted_ids'])

    def test_retracted_basis_and_original_reading_references_refuse_without_changing_source(self):
        base=self.manual_base();history=base.work.history
        command=dict(schema_version=4,id='retract',project_id=base.project_id,episode_id='local',created_at='2026-10-14T00:00:00Z',
            operation_type='record-evidence-event',expected_heads=dict(history.heads),evidence_watermark=history.watermark,
            payload=dict(event_id='retracted',target_id='O',run_id='X',action='retract',statement=None,value=None,rationale='The source was withdrawn.',supersedes_id='event'))
        from claimbranch.application.paper_work_store import PaperWork
        retracted=base.with_work(PaperWork.create(history.append(command)))
        request=self.request(disposition='not-required')
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human'
        with self.assertRaisesRegex(ContractError,'active global'):prepare_co_report(retracted,request)
        request['candidates'][0]['source_id']='missing'
        with self.assertRaisesRegex(ContractError,'Original reading'):prepare_co_report(base,request)

    def test_combined_128_readings_replay_deterministically_then_episode_budget_refuses(self):
        from claimbranch.core.research_history import ResearchHistory
        base=self.manual_base();history=base.work.history
        from dataclasses import asdict
        from claimbranch.core.review import Judgment
        def append(kind,payload,key,episode,version=4):
            nonlocal history
            history=history.append(dict(schema_version=version,id=key,project_id='manual-co',episode_id=episode,created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload))
        for i in range(32):
            episode='local' if i==0 else f'episode-{i}'
            if i:append('open-episode',dict(title='Another definition',question='What must be reported together?'),f'open-{i}',episode)
            readings=[dict(id=f'reading-{i}-{j}',statement=f'Explicit reading {i} {j}.',scope=f'Definition {j}',observation_ids=['O'],claim_id='T',edge_id=f'edge-{i}-{j}',edge_type='qualifies',source_id=None,origin='human') for j in range(4)]
            view=history.view('main')
            payload=dict(id=f'decision-{i}',candidates=readings,selected_ids=[r['id'] for r in readings],companion_ids=['co-report'],
                context_digest=__import__('hashlib').sha256(encode(view,purpose='project')).hexdigest(),judgment=asdict(Judgment.start('manual-co',episode).edit('Keep all scoped readings.','Every definition has its own scope.')),disposition='not-required',answers=[])
            append('record-co-report',payload,f'co-operation-{i}',episode,8);append('close-episode',{},f'close-{i}',episode)
        self.assertEqual(128,len(history.view('main')['interpretations']))
        self.assertEqual(128,history.capacity()['resources']['interpretations']['limit'])
        graph=PaperService(history).query('main');self.assertEqual(128,len([n for n in graph['nodes'] if n['kind']=='interpretation']))
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.personal_archive import personal_backup
        combined=base.with_work(PaperWork.create(history));self.assertEqual(combined.payload,split_personal_backup(personal_backup(combined)).payload)
        self.assertEqual(history.manifest(),ResearchHistory(history.seed,history.commands).manifest())
        before=history.manifest()
        with self.assertRaisesRegex(ContractError,'episodes: 33 / 32'):append('open-episode',dict(title='Overflow',question='Too many rounds.'),'overflow','overflow')
        self.assertEqual(before,history.manifest())

    def test_omitted_ids_are_reserved_and_old_reading_cannot_be_rewritten_in_later_episode(self):
        from claimbranch.core.research_history import _validate_amendment_identity,_reduce
        request=self.request();request['candidates'].append({**request['candidates'][0],'id':'omitted','edge_id':'omitted-edge'})
        project,_=prepare_co_report(self.base(),request);h=project.work.history
        run=self.project.work.history.view('main')['experiments'][0];run={k:run[k] for k in ('id','question','method','conditions','metric','source_ref')};run['id']='omitted'
        with self.assertRaises(ContractError):h.append(dict(schema_version=5,id='new-run',project_id=project.project_id,episode_id='local',created_at=decode(h.commands[-1],purpose='history')['created_at'],operation_type='record-experiment',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=run))
        state=_reduce(h.seed,h.commands)
        amended=deepcopy(state['branches']['main']['changes']['primary']);amended['body']['statement']='Unreviewed replacement.'
        with self.assertRaisesRegex(ContractError,'previous episode'): _validate_amendment_identity(state,state['branches']['main'],amended,'future')

    def test_legacy_ai_reasoning_origin_survives_a_human_merge_judgment(self):
        from claimbranch.core.review import Judgment,Proposal
        from dataclasses import asdict
        from claimbranch.application.paper_work_store import PaperWork
        base=self.manual_base();history=base.work.history
        def append(kind,payload,key,episode='local'):
            nonlocal history
            history=history.append(dict(schema_version=4,id=key,project_id=base.project_id,episode_id=episode,created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload))
        append('create-reasoning-branch',{},'branch')
        judgment=Judgment.start(base.project_id,'local').use_proposal(Proposal('proposal',base.project_id,'local','The original AI reading.','a'*64)).edit('The original AI reading.','Keep its limited interpretation.')
        append('record-interpretation',dict(changes=[dict(id='original',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))],judgment=asdict(judgment)),'record')
        human=judgment.edit(judgment.text,'Human selection preserves the original source.')
        append('apply-selected-merge',dict(selected_ids=['original'],judgment=asdict(human),disposition='deferred',answers=[]),'merge')
        append('close-episode',{},'close');append('open-episode',dict(title='Definitions',question='Which readings must coexist?'),'open-new','new')
        later=base.with_work(PaperWork.create(history));request=self.request()
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human';reading['source_id']='original'
        project,preview=prepare_co_report(later,request)
        self.assertIn('ai',preview['decision']['reading_origins']['primary']);self.assertTrue(preview['decision']['origin_review_required'])

    def test_actual_pty_record_open_and_old_reader_refusal(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        from types import ModuleType
        base=self.base();path=self.root/'co-report.json';path.write_bytes(encode(self.request(),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        def terminal(arguments,record=False):
            master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
            process=subprocess.Popen([sys.executable,'-m','claimbranch',*arguments],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'))
            os.close(slave);output=b'';pending=b'';quit_sent=False;deadline=time.monotonic()+25
            try:
                while process.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        output+=chunk;pending+=chunk
                        if record:
                            if b'Enter: next page' in pending:os.write(master,b'\n');pending=b''
                            elif b'Type record to keep' in pending:os.write(master,b'record\n');pending=b''
                        elif b'ClaimBranch' in output and not quit_sent:os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-3000:].decode(errors='replace'))
                if record:self.assertIn(b'Co-reported readings saved',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(['project','co-report','--directory',str(self.work),'--input',str(path)],True)
        terminal(['project','open','--directory',str(self.work)])
        raw=(self.work/'personal.cbp').read_bytes()
        old=__import__('pathlib').Path(__file__).with_name('legacy_personal_project.py').read_text()
        module=ModuleType('claimbranch.application.co_report_old');module.__package__='claimbranch.application';exec(compile(old,'old-reader','exec'),module.__dict__)
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_co_report_edges_and_same_episode_alternative_cannot_be_rewritten(self):
        from claimbranch.core.research_history import _validate_amendment_identity,_reduce
        project,_=prepare_co_report(self.base(),self.request());h=project.work.history;state=_reduce(h.seed,h.commands)
        edge=deepcopy(state['branches']['main']['changes']['primary-edge']);edge['body']['edge_type']='challenges'
        with self.assertRaisesRegex(ContractError,'relationships are immutable'):_validate_amendment_identity(state,state['branches']['main'],edge,'future')
        with self.assertRaisesRegex(ContractError,'already co-reported'):h.append(dict(schema_version=5,id='dead-alternative',project_id=project.project_id,episode_id='local',created_at=decode(h.commands[-1],purpose='history')['created_at'],operation_type='create-imported-reasoning-branch',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload={}))

    def test_companion_claim_needs_a_selected_reading_even_when_not_supplied(self):
        request=self.request();request['candidates'][1]['claim_id']='C'
        with self.assertRaisesRegex(ContractError,'not supplied'):prepare_co_report(self.base(),request)

    def test_invalid_omitted_input_is_disclosed_and_cannot_become_reviewed_science(self):
        request=self.request();request['candidates'].append({**request['candidates'][0],'id':'unkept','edge_id':'unkept-edge','claim_id':'missing','observation_ids':['missing'],'source_id':'missing'})
        project,preview=prepare_co_report(self.base(),request)
        omitted=preview['decision']['omitted_candidates'][0]
        self.assertEqual('unadopted-input-not-science',omitted['status'])
        self.assertEqual({'unknown-claim','unknown-observation','unavailable-original-reading'},set(omitted['validation_problems']))
        self.assertNotIn('unkept',{n['id'] for n in preview['after']['nodes']})
        request['selected_ids']=['primary','unkept']
        with self.assertRaises(ContractError):prepare_co_report(self.base(),request)

    def test_input_changed_during_cli_confirmation_preserves_original_checkpoint(self):
        from claimbranch.application.cli import main
        base=self.base();path=self.root/'co-report.json';path.write_bytes(encode(self.request(),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        before=(self.work/'personal.cbp').read_bytes()
        def answer(prompt):
            if prompt.startswith('Type record'):
                path.write_bytes(path.read_bytes()+b'\n');return 'record'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):
            self.assertNotEqual(0,main(['project','co-report','--directory',str(self.work),'--input',str(path)]))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())

    def test_corrected_observation_reaches_scoped_reading_and_claim_manuscript_without_direct_support(self):
        from claimbranch.application.paper_work_store import PaperWork
        base=self.manual_base();h=base.work.history
        h=h.append(dict(schema_version=4,id='observation-two',project_id=base.project_id,episode_id='local',created_at='2026-10-14T00:00:00Z',operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='event-two',target_id='O2',run_id='X',action='confirm',statement='Independent sensitivity result.',value='0.4',rationale='Owned synthetic source.',supersedes_id=None)))
        base=base.with_work(PaperWork.create(h));base,_=self.register('location',expresses=('T',),project=base)
        request=self.request(disposition='deferred')
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human'
        request['candidates'][1]['observation_ids']=['O2']
        project,_=prepare_co_report(base,request);impact=PaperService(project.work.history).anchor_impact(['O2'])
        self.assertIn('location',impact['potentially_affected_anchor_ids'])
        witness=next(w for w in impact['anchor_witness_paths'] if w['anchor_id']=='location')
        self.assertEqual(['O2','sensitivity','T','location'],witness['node_ids'])
        observation=next(n for n in PaperService(project.work.history).query('main')['nodes'] if n['id']=='O2')
        self.assertEqual('confirmed',observation['content']['status'])

    def test_one_selected_companion_reading_does_not_force_every_alternative_on_same_claim(self):
        request=self.request();request['candidates'].append({**request['candidates'][1],'id':'another-sensitivity','edge_id':'another-sensitivity-edge','scope':'Another definition not selected.'})
        project,preview=prepare_co_report(self.base(),request)
        self.assertEqual(['another-sensitivity'],preview['decision']['omitted_ids'])
        self.assertEqual(['primary','sensitivity'],preview['decision']['selected_ids'])

    def test_companion_reporting_does_not_require_reverse_target_from_other_obligation(self):
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.personal_project import PersonalProjectRecovery
        base=self.base()
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:
            store.save(base,preview=self.preview);app=project_workspace(base);app.recovery=PersonalProjectRecovery(store,app,base)
            app.select('C');app.keep_draft('Add an independent claim.','It belongs to another reporting context.')
            app.review.candidates().put(dict(id='U',kind='claim',body=dict(role='main',statement='Another bounded claim.',scope='Separate synthetic case.',parent_ids=['T'])))
            service=PersonalResearch(app);service.commit(service.prepare('reasoning',explanation_state='leave-for-later'));service.commit(service.prepare('next',question='Which definitions apply here?'))
            later=store.load()
        later,_=self.companion(later,id='other-use',target_id='U',companion_id='T')
        project,preview=prepare_co_report(later,self.request())
        self.assertEqual(['co-report'],preview['decision']['companion_ids'])
        request=self.request(companion_ids=['co-report','other-use'])
        with self.assertRaises(ContractError):prepare_co_report(later,request)

    def test_inactive_mandatory_observation_explains_inspection_and_explicit_retirement(self):
        from claimbranch.application.paper_work_store import PaperWork
        base=self.manual_base();history=base.work.history
        def event(key,target,action,previous,value):
            nonlocal history
            history=history.append(dict(schema_version=4,id=key,project_id=base.project_id,episode_id='local',created_at='2026-10-14T00:00:00Z',operation_type='record-evidence-event',expected_heads=dict(history.heads),evidence_watermark=history.watermark,
                payload=dict(event_id=key+'-event',target_id=target,run_id='X',action=action,statement='Alternative owned result.' if action=='confirm' else None,value=value,rationale='Owned synthetic source change.',supersedes_id=previous)))
        event('other','O2','confirm',None,'0.6');event('retract','O','retract','event',None)
        base=base.with_work(PaperWork.create(history));request=self.request(disposition='not-required')
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human';reading['observation_ids']=['O2']
        with self.assertRaisesRegex(ContractError,'inspect.*retire dependency co-report'):prepare_co_report(base,request)
        self.assertEqual(2,len(base.work.history.view('main')['evidence']))

    def test_actual_basis_correction_invalidates_preview_and_historical_basis_remains_readable(self):
        from claimbranch.application.paper_work_store import PaperWork
        base=self.manual_base();request=self.request(disposition='deferred')
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human'
        project,preview=prepare_co_report(base,request);h=base.work.history
        correction=dict(schema_version=4,id='actual-correction',project_id=base.project_id,episode_id='local',created_at=preview['operation']['created_at'],operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='corrected-event',target_id='O',run_id='X',action='correct',statement='Corrected owned value.',value='0.6',rationale='A checked synthetic correction.',supersedes_id='event'))
        corrected=base.with_work(PaperWork.create(h.append(correction)))
        with self.assertRaisesRegex(ContractError,'changed'):recheck_co_report(corrected,preview)
        with self.assertRaisesRegex(ContractError,'stale'):corrected.work.history.append(preview['operation'])
        fresh,_=prepare_co_report(corrected,request)
        self.assertEqual('0.6',fresh.work.history.view('main')['evidence'][0]['value'])
        old=PaperService(project.work.history).query('main',at_operation=preview['operation']['id'])
        self.assertEqual('0.5',next(n['content']['value'] for n in old['nodes'] if n['id']=='O'))
        self.assertEqual('0.5',base.work.history.view('main')['evidence'][0]['value'])
