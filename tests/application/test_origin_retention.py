"""One current review preserves known/unknown influence and bounded prior causes."""
from copy import deepcopy
import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.project_work import ProjectWork
from claimbranch.application.personal_project import PersonalProjectStore,PersonalProjectRecovery
from claimbranch.application.personal_archive import split_personal_backup
from claimbranch.application.personal_research import PersonalResearch
from claimbranch.application.tui_project import project_workspace
from .test_original_registration import fixture,history


def compound_fixture(kind='ai'):
    value=fixture();other=deepcopy(value['files'][0]);other['id']='ledger2';value['files'].append(other)
    record=value['records'][1];record['origin']=dict(contributor=kind,detail=None)
    record['mappings'][0][0]['file_id']='ledger2'
    record['source_origins']=[dict(file_id='ledger',origin=dict(contributor=kind,detail=None)),dict(file_id='ledger2',origin=dict(contributor='unknown',detail=None))]
    record['joint_origin']=dict(contributor=kind,detail='Known contribution does not settle the other source.')
    return value


class OriginRetentionTests(unittest.TestCase):
    def setUp(self):
        from .test_original_registration import OriginalProjectTests
        OriginalProjectTests.setUp(self)
        self.raw=encode(compound_fixture(),purpose='project')
        self.project=ProjectWork.create(PaperWork.create(history(compound_fixture())),self.preview,import_input=self.raw)

    def app(self):
        store=self.enterContext(PersonalProjectStore.create(self.work,project_id=self.project.project_id))
        store.save(self.project,preview=self.preview);app=project_workspace(self.project)
        app.recovery=PersonalProjectRecovery(store,app,self.project);app.select('C')
        return app

    def test_compound_ai_unknown_has_one_current_review_and_survives_record_return(self):
        app=self.app();service=PersonalResearch(app,clock=lambda:2000000000)
        self.assertEqual([],app.paper._recorded_origins);self.assertEqual([],app.paper._personal_explanations)
        app.keep_draft('Blind quality remains a separate question.','The original source does not settle validity.')
        preview=service.prepare('reasoning')
        self.assertTrue(preview.display['origin_uncertain']);self.assertTrue(preview.display['ai_origin_retained'])
        self.assertFalse(preview.display['recording_available']);self.assertLessEqual(len(preview.display['explanation_topics']),3)
        self.assertTrue(any(r['origin_flags']['ai'] and r['origin_flags']['unknown'] for r in preview.display['imported_sources']))
        with self.assertRaises(ContractError):service.commit(preview)
        self.assertEqual(self.project.payload,app.recovery.store.load().payload)
        preview=service.prepare('reasoning',explanation_state='leave-for-later');service.commit(preview)
        returned=project_workspace(split_personal_backup(app.recovery.store.backup()))
        self.assertEqual(1,len(returned.paper._recorded_origins))
        record=returned.paper._recorded_origins[0];self.assertEqual('leave-for-later',record['explanation']['state'])
        self.assertEqual('The original source does not settle validity.',record['cause']['judgment']['rationale'])
        self.assertTrue(all(c['contributor']=='human' for c in record['cause']['judgment']['history']))
        from claimbranch.core.research_history import _reduce,_branch_ai,_branch_uncertain
        state=_reduce(returned.paper.history.seed,returned.paper.history.commands)
        self.assertTrue(_branch_ai(state['branches']['main'],state));self.assertTrue(_branch_uncertain(state['branches']['main']))

    def test_source14_retention_schema_is_128_without_changing_legacy(self):
        from claimbranch.application.paper_proposal_work import imported_proposals_schema
        self.assertEqual(128,imported_proposals_schema(2)['properties']['recorded']['maxItems'])
        self.assertEqual(128,imported_proposals_schema(2)['properties']['explanations']['maxItems'])
        self.assertEqual(32,imported_proposals_schema()['properties']['recorded']['maxItems'])
        self.assertEqual(64,imported_proposals_schema()['properties']['explanations']['maxItems'])

    def test_128_distinct_partial_review_causes_return_and_129_refuses_without_loss(self):
        import time
        from claimbranch.application.tui_work_recovery import snapshot_value
        app=self.app();service=PersonalResearch(app,clock=lambda:2000000000);initial=app.paper.history.manifest()
        started=time.monotonic()
        for index in range(128):
            app.keep_draft(f'Unresolved interpretation {index}.',f'Synthetic reason {index}: blind evidence is still required.')
            preview=service.prepare('reasoning');topic=preview.display['explanation_topics'][0]['id']
            service.keep_explanation(preview,entries=[dict(topic_id=topic,text=f'Partial comparison {index}; still unresolved.',reuse_rationale=False)])
            if index==39:self.assertEqual(40,len(app.paper._personal_explanations))
        self.assertEqual(128,len(app.paper._personal_explanations));self.assertEqual([],app.paper._recorded_origins)
        self.assertEqual(initial,app.paper.history.manifest());self.assertEqual(1,len(app.paper.history.episodes()))
        app.recovery.save(app);saved=app.recovery.store.load();backup=app.recovery.store.backup()
        returned=project_workspace(split_personal_backup(backup))
        self.assertEqual(128,len(returned.paper._personal_explanations));self.assertEqual(saved.payload,split_personal_backup(backup).payload)
        self.assertEqual('Partial comparison 0; still unresolved.',returned.paper._personal_explanations[0]['explanation']['entries'][0]['text'])
        before=deepcopy(app.paper._personal_explanations);checkpoint=(self.work/'personal.cbp').read_bytes()
        app.keep_draft('Another unresolved interpretation.','Do not discard earlier causes.')
        preview=service.prepare('reasoning')
        with self.assertRaisesRegex(ContractError,'retained-review-causes: 129 / 128'):service.keep_explanation(preview)
        self.assertEqual(before,app.paper._personal_explanations);self.assertEqual(checkpoint,(self.work/'personal.cbp').read_bytes())
        self.assertEqual(initial,app.paper.history.manifest());self.assertFalse(returned.paper.history.authorization_verified)

    def test_unknown_without_known_ai_can_choose_review_later_in_terminal(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_personal import PersonalUI
        self.raw=encode(compound_fixture('human'),purpose='project')
        self.project=ProjectWork.create(PaperWork.create(history(compound_fixture('human'))),self.preview,import_input=self.raw)
        app=self.app();app.keep_draft('Keep this conclusion limited.','One contributing source remains unknown.')
        terminal=SimpleNamespace(app=app,modal=None,screen=SimpleNamespace(getmaxyx=lambda:(40,140)))
        ui=PersonalUI(terminal);ui.prepare('reasoning')
        self.assertFalse(ui.preview.display['ai_origin_retained']);self.assertTrue(ui.preview.display['origin_review_required'])
        self.assertGreater(ui.preview.display['source_review_summary']['known_and_unknown'],0)
        ui.painted=ui.seen_end=True;ui.key('2')
        self.assertEqual('leave-for-later',ui.preview.display['explanation']['state']);self.assertTrue(ui.preview.display['recording_available'])
        ui.service.commit(ui.preview)
        record=app.paper._recorded_origins[0];self.assertEqual('leave-for-later',record['explanation']['state'])
        self.assertTrue(all(c['contributor']=='human' for c in record['cause']['judgment']['history']))

    def test_reviewed_reason_reuse_does_not_approve_next_change_and_partial_survives_correction(self):
        import time
        from claimbranch.application.typed_observations import prepare_measurement
        app=self.app();service=PersonalResearch(app,clock=lambda:int(time.time()))
        app.keep_draft('Rubric quality is a limited proxy.','Blind evidence is needed independently.')
        preview=service.prepare('reasoning');topics=preview.display['explanation_topics']
        with self.assertRaisesRegex(ContractError,'Reviewed choice requires'):service.prepare('reasoning',explanation_state='reviewed')
        entries=[dict(topic_id=t['id'],text='',reuse_rationale=True) for t in topics]
        service.commit(service.prepare('reasoning',explanation_state='reviewed',explanation_entries=entries))
        recorded=deepcopy(app.paper._recorded_origins[0]);cause=recorded['cause']
        service.keep_retained_explanation(cause,entries=[dict(topic_id=topics[0]['id'],text='New partial explanation, still unfinished.',reuse_rationale=False)])
        app.recovery.save(app);project=app.recovery.store.load();o=project.work.history.view('main')['evidence'][0]
        request=dict(schema='claimbranch.measurement-input/v1',operation_type='record-measurement',payload=dict(event_id='later-cell-correction',target_id='O',run_id='X',expected_revision=o['measurement_revision'],action='correct-cells',statement=o['statement'],rationale='A later source-cell correction.',source_context='Synthetic source.',table=None,corrections=[dict(cell_id='primary-low-s1-direct',value=dict(type='decimal',value='0.25'))]))
        corrected,_=prepare_measurement(project,request);app.recovery.store.save(corrected)
        returned=project_workspace(split_personal_backup(app.recovery.store.backup()))
        self.assertEqual(recorded,returned.paper._recorded_origins[0]);self.assertIn('New partial explanation, still unfinished.',str(returned.paper._personal_explanations))
        returned.recovery=PersonalProjectRecovery(app.recovery.store,returned,corrected)
        again=PersonalResearch(returned,clock=lambda:int(time.time()));again.commit(again.prepare('next',question='What does the corrected cell change?'))
        returned.select('C');returned.keep_draft('Reassess the narrow conclusion.','The later value must be considered afresh.')
        fresh=again.prepare('reasoning');self.assertFalse(fresh.display['recording_available']);self.assertEqual('not-reviewed',fresh.display['explanation']['state'])
        self.assertTrue(fresh.display['origin_uncertain']);self.assertTrue(fresh.display['ai_origin_retained'])

    def test_old_i02_frames_and_schemas_remain_readable_without_silent_reinterpretation(self):
        from claimbranch.application.personal_project import _PersonalCodec,ORIGINAL_PERSONAL_MAGIC,RETAINED_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import ORIGINAL_BACKUP_MAGIC,personal_backup
        value=decode(self.project.payload,purpose='project');value['schema']='claimbranch.project-work/v20';value['work']['schema']='claimbranch.paper-work/v24'
        old=ProjectWork(encode(value,purpose='project'));raw=_PersonalCodec().seal(old.payload)
        self.assertTrue(raw.startswith(ORIGINAL_PERSONAL_MAGIC));self.assertEqual(old.payload,_PersonalCodec().open(raw))
        self.assertTrue(personal_backup(old).startswith(ORIGINAL_BACKUP_MAGIC))
        self.assertEqual(old.payload,split_personal_backup(personal_backup(old)).payload)
        self.assertTrue(_PersonalCodec().seal(self.project.payload).startswith(RETAINED_PERSONAL_MAGIC))
        with self.assertRaisesRegex(ContractError,'frame/profile'):_PersonalCodec().open(ORIGINAL_PERSONAL_MAGIC+self.project.payload)

    def test_over_128_source_dependencies_share_one_review_with_defaults_and_overrides(self):
        import json
        from claimbranch.core.argument_import import _leaves
        from claimbranch.core.paper_capacity import source_record
        value=compound_fixture();records=value['records']
        for index in range(1,70):
            for template in (2,3,4):
                record=deepcopy(records[template]);record['id']+='-'+str(index)
                if template==3:
                    record['body'].pop('measurement');record['body']['value']='0.35';record['body']['experiment_id']='X-'+str(index)
                if template==4:record['body']['source_id']='O-'+str(index)
                records.append(record)
        records[1]['body']['basis_ids']=['E']+['E-'+str(i) for i in range(1,70)]
        raw=json.dumps(dict(entries=[r['body'] for r in records]),ensure_ascii=False,separators=(',',':')).encode()
        for file in value['files']:file['source']=source_record(raw)
        value['origin_default']=dict(contributor='mixed',detail='Synthetic source-level default.');overrides=0
        for index,record in enumerate(records):
            if record['id']!='C':
                record.pop('origin',None)
                if overrides<10:record['origin']=dict(contributor='human',detail='Explicit synthetic source exception.');overrides+=1
            mappings=[dict(target=target,file_id='ledger2' if record['id']=='C' and n==0 else 'ledger',locator=dict(kind='json-pointer',pointer='/entries/'+str(index)+target),normalization='literal-v1',transformation=None) for n,(target,_) in enumerate(_leaves(record['body']))]
            record['mappings']=[mappings[i:i+1024] for i in range(0,len(mappings),1024)]
        value['selected_ids']=[r['id'] for r in records];self.raw=encode(value,purpose='project');self.project=ProjectWork.create(PaperWork.create(history(value)),self.preview,import_input=self.raw)
        app=self.app();app.keep_draft('Preserve the blind-quality limitation.','One grouped judgment considers all registered dependent sources.')
        work=app.review.candidates();child=work.create('claim',dict(role='subclaim',statement='An independent blind test remains necessary.',scope='Synthetic writing conditions.',parent_ids=['C']))
        service=PersonalResearch(app,clock=lambda:2000000000);preview=service.prepare('reasoning',explanation_state='leave-for-later')
        self.assertGreater(len(preview.display['imported_sources']),128);self.assertLessEqual(len(preview.display['explanation_topics']),3)
        self.assertEqual(len(preview.display['imported_sources']),preview.display['source_review_summary']['records'])
        self.assertTrue(preview.display['origin_uncertain']);self.assertTrue(preview.display['ai_origin_retained'])
        service.commit(preview);returned=project_workspace(split_personal_backup(app.recovery.store.backup()))
        self.assertEqual(1,len(returned.paper._recorded_origins));self.assertTrue(any(r['origin_flags']['unknown'] and r['origin_flags']['ai'] for r in returned.nodes[child]['content']['imported_dependencies']))
        records=returned.paper.history.view('main')['imported_records']
        self.assertEqual(10,sum(r['origin']['contributor']=='human' for r in records));self.assertTrue(any(r['origin']['contributor']=='mixed' for r in records))

    def test_shared_cause_counts_once_but_new_record_at_128_refuses_before_append(self):
        from claimbranch.application.paper_proposal_work import check_retained_causes
        app=self.app();service=PersonalResearch(app,clock=lambda:2000000000)
        app.keep_draft('A scoped interpretation.','Synthetic evidence still needs scrutiny.')
        preview=service.prepare('reasoning');row=deepcopy(preview.origin_record)
        rows=[dict(cause=dict(row['cause'],fixture_distinct=i)) for i in range(128)]
        # Cardinality accounting is independent of semantic validation; real
        # causes are exercised by the full 128-review/save/return test.
        check_retained_causes(app.paper.history,dict(recorded=[rows[0]],explanations=rows))
        with self.assertRaisesRegex(ContractError,'129 / 128'):
            check_retained_causes(app.paper.history,dict(recorded=[row],explanations=rows))
        old=deepcopy(app.paper._personal_explanations)
        app.paper._personal_explanations=rows;before=app.paper.history.manifest()
        with self.assertRaisesRegex(ContractError,'129 / 128'):
            service.prepare('reasoning',explanation_state='leave-for-later')
        self.assertEqual(before,app.paper.history.manifest());app.paper._personal_explanations=old

    def test_old_work24_rejects_65_partial_entries_before_reinterpretation(self):
        from claimbranch.application.tui_work_recovery import snapshot_value
        app=self.app();app.keep_draft('Keep the source caveat.','Do not infer fresh approval.')
        service=PersonalResearch(app,clock=lambda:2000000000);p=service.prepare('reasoning');service.keep_explanation(p)
        value=snapshot_value(app);value['schema']='claimbranch.paper-workspace/v16'
        value['proposals']['explanations']*=65
        outer=decode(PaperWork.create(app.paper.history).payload,purpose='project');outer['schema']='claimbranch.paper-work/v24';outer['workspace']=value
        with self.assertRaises(ContractError):PaperWork(encode(outer,purpose='project'))

    def test_legacy_unknown_only_review_explicitly_discloses_uncertainty(self):
        from types import SimpleNamespace
        from .test_argument_registration import ImportedProjectTests
        from claimbranch.application.tui_personal import PersonalUI
        helper=ImportedProjectTests();helper.setUp();self.addCleanup(helper.doCleanups)
        app=helper.personal_app();app.select('O')
        app.keep_draft('The conclusion remains bounded.','Authorship of this source is unknown.')
        ui=PersonalUI(SimpleNamespace(app=app,modal=None,screen=SimpleNamespace(getmaxyx=lambda:(40,140))))
        ui.prepare('reasoning')
        self.assertTrue(ui.preview.display['origin_uncertain']);self.assertFalse(ui.preview.display['ai_origin_retained'])
        self.assertIn('SOURCE AUTHORSHIP / uncertainty retained',ui.rows(120))
        ui.painted=ui.seen_end=True;ui.key('2')
        self.assertEqual('leave-for-later',ui.preview.display['explanation']['state'])

    def test_unknown_source_review_resize_choice_and_return_in_actual_pty(self):
        from types import SimpleNamespace
        from .test_tui_terminal import TerminalProcessTests
        from claimbranch.application.tui_actions import ActionsUI
        from claimbranch.application.tui_work_recovery import snapshot_value
        self.raw=encode(compound_fixture('human'),purpose='project')
        self.project=ProjectWork.create(PaperWork.create(history(compound_fixture('human'))),self.preview,import_input=self.raw)
        app=project_workspace(self.project);app.select('C');app.keep_draft('결론은 독립 검증이 필요하다.','출처 불명과 AI 기여는 다른 질문이다.')
        self.project=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        app.recovery=SimpleNamespace(personal_project=True)
        index=next(i for i,a in enumerate(ActionsUI(SimpleNamespace(app=app)).items()) if a.key=='personal:reasoning')
        tty=TerminalProcessTests();tty.setUp();self.addCleanup(tty.tearDown)
        tty.launch(personal_arguments=['open','--directory',str(self.work)])
        tty.expect('ARGUMENT GRAPH');tty.send(';'+('\x1b[B'*index)+'\r','PERSONAL RECORD PREVIEW')
        tty.send('\x1b[F\x0c','uncertainty retained');tty.resize(80,24);tty.send('\x0c','2 later')
        tty.send('\x1b[F','STORAGE / AUTHORITY')
        # Wait for the newly prepared comparison's first-page footer before
        # sending navigation; its first paint deliberately flushes queued keys.
        tty.send('2','1–17')
        tty.send('\x1b[F','leave-for-later');tty.send('\r','Personal research recorded')
        tty.send('q');tty.assert_restored(0)
        with PersonalProjectStore(self.work) as store:
            returned=project_workspace(store.load());self.assertEqual('leave-for-later',returned.paper._recorded_origins[0]['explanation']['state'])
            self.assertTrue(all(c['contributor']=='human' for c in returned.paper._recorded_origins[0]['cause']['judgment']['history']))
