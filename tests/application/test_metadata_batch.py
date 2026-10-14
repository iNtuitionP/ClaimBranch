"""Prepared verification cases; execute only when the verification stage starts."""
import io
import unittest
from copy import deepcopy
from unittest.mock import patch
from application import test_claim_wording as prior
from application import test_protocols as protocol_tests
from claimbranch.application.metadata_batch import prepare_batch,origin_command
from claimbranch.core.paper_capacity import encode,decode,source_bytes
from claimbranch.core.canonical import ContractError
from claimbranch.application.personal_archive import personal_backup,split_personal_backup
from claimbranch.application.canonical_share import prepare_share
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.cli import main

class MetadataBatchTests(unittest.TestCase):
    setUp=prior.ClaimWordingTests.setUp

    def policy(self):
        return dict(claim_id='C',grade='Direction only',limitation='Only the owned synthetic conditions.',allowed_wording=['The rubric increased under these conditions.'],required_caveats=['Only these conditions.'],banned_phrases=['guarantees'],placement=['appendix'],rationale='Keep the limitation with the claim.')

    def batch(self,origin='ai'):
        return dict(schema='claimbranch.metadata-batch/v1',entries=[dict(id='wording',origin=origin,kind='set-claim-wording',request=self.policy()),dict(id='companion',origin='human',kind='set-claim-companion',request=dict(id='companion',target_id='C',companion_id='O',scope='anchor',status='active',rationale='Keep the sensitivity observation beside the claim.'))],selected_ids=['wording','companion'])

    def test_origin_actor_and_original_input_survive_return(self):
        raw=encode(self.batch(),purpose='project');before=self.project.payload;p,review=prepare_batch(self.project,raw)
        self.assertTrue(review['valid']);self.assertEqual(before,self.project.payload)
        self.assertEqual('claimbranch.project-work/v18',decode(p.payload,purpose='project')['schema'])
        v=p.work.history.view('main');declared=list(v['metadata_origins'].values());self.assertEqual({'human','ai'},{r['origin'] for r in declared});self.assertTrue(all(r['confirming_actor']=='human-personal-confirmation' for r in declared))
        restored=split_personal_backup(personal_backup(p));self.assertEqual(p.payload,restored.payload)
        self.assertTrue(any(source_bytes(s)==raw for s in decode(restored.payload,purpose='project')['sources']))
        output=decode(prepare_share(restored,dict(schema='claimbranch.share-selection/v1',record_ids=['C'],reason_ids=[])),purpose='project')
        claim=next(r for r in output['records'] if r['kind']=='claim' and r['content'].get('role')=='main');self.assertIn('ai',claim['content']['origins'])

    def test_unknown_default_and_failed_entry_publish_no_prefix(self):
        request=self.batch();request['entries'][0].pop('origin');p,preview=prepare_batch(self.project,encode(request,purpose='project'));self.assertTrue(preview['valid']);self.assertIn('unknown',{r['origin'] for r in p.work.history.view('main')['metadata_origins'].values()})
        request=self.batch();request['entries'][1]['request']['companion_id']='missing';p,preview=prepare_batch(self.project,encode(request,purpose='project'));self.assertIsNone(p);self.assertFalse(preview['valid']);self.assertEqual('/entries/1',preview['errors'][0]['pointer'])
        self.assertNotIn('wording_policies',self.project.work.history.view('main'))

    def test_retry_refuses_and_missing_selection_refuses(self):
        raw=encode(self.batch(),purpose='project');p,_=prepare_batch(self.project,raw)
        with self.assertRaises(ContractError):prepare_batch(p,raw)
        request=self.batch();request['selected_ids']=['absent']
        with self.assertRaises(ContractError):prepare_batch(self.project,encode(request,purpose='project'))

    def test_new_association_missing_input_origin_is_unknown_in_review_policy(self):
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups);p=helper.associated()
        from claimbranch.core.research_history import _reduce,_branch_uncertain
        state=_reduce(p.work.history.seed,p.work.history.commands);self.assertEqual(['unknown'],state['branches']['main']['protocol_origins']['association']);self.assertTrue(_branch_uncertain(state['branches']['main']))

    def test_cli_dry_run_cancel_then_register_single_saved_write(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        path=self.root/'extended.json';path.write_bytes(encode(self.batch(),purpose='project'));path.chmod(0o600)
        args=['project','import-metadata','--directory',str(self.work),'--input',str(path)];before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO):self.assertEqual(0,main(args+['--dry-run']))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def cancel(prompt):return 'q'
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=cancel),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def accept(prompt):return 'register' if prompt.startswith('Type register') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=accept),patch('builtins.print'):self.assertEqual(0,main(args))
        with PersonalProjectStore(self.work) as store:self.assertEqual(2,len(store.load().work.history.view('main')['metadata_origins']))
    def test_legacy_command_bytes_are_not_rewritten_by_new_origin_entry(self):
        before=self.project.work.history.commands;p,_=prepare_batch(self.project,encode(self.batch(),purpose='project'))
        self.assertEqual(before,p.work.history.commands[:len(before)])
        self.assertTrue(all(decode(c,purpose='history')['schema_version']==12 for c in p.work.history.commands[len(before):]))

    def test_co_report_ai_input_requires_explanation_choice_before_recording(self):
        from application import test_co_report as co
        from claimbranch.application.co_report import prepare_co_report
        helper=co.CoReportTests();helper.setUp();self.addCleanup(helper.doCleanups)
        request=helper.request(disposition='not-required')
        for r in request['candidates']:r['origin']='human'
        with self.assertRaises(ContractError):prepare_co_report(helper.base(),request,contribution_origin='ai')

    def test_all_invalid_schema_entries_are_reported_without_candidate(self):
        request=self.batch();request['entries'][0]['request'].pop('grade');request['entries'][1]['request'].pop('rationale')
        candidate,preview=prepare_batch(self.project,encode(request,purpose='project'));self.assertIsNone(candidate)
        self.assertEqual(2,preview['error_count']);self.assertEqual({'/entries/0','/entries/1'},{e['pointer'] for e in preview['errors']})

    def test_new_registration_invalidates_source_bound_review(self):
        from claimbranch.application.metadata_batch import recheck_batch
        raw=encode(self.batch(),purpose='project');candidate,preview=prepare_batch(self.project,raw)
        with self.assertRaises(ContractError):recheck_batch(candidate,preview)

    def test_tui_confirmation_requires_complete_review_and_literal_word(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_metadata import MetadataUI
        term=SimpleNamespace(app=SimpleNamespace(),modal='metadata-preview',screen=SimpleNamespace(getmaxyx=lambda:(40,140)))
        ui=MetadataUI(term);ui.candidate=object();ui.review={'valid':True};ui.seen_end=False;ui.key('r')
        self.assertEqual('metadata-preview',term.modal)
        ui.seen_end=True;ui.key('r');self.assertEqual('metadata-confirm',term.modal)
        ui.key('r');ui.key('e');self.assertEqual('re',ui.confirmation.text)
        ui.key('escape');self.assertIsNone(term.modal);self.assertIsNone(ui.candidate)
    def test_input_origin_does_not_infer_human_from_source_record_origin(self):
        command={'schema_version':10,'payload':{'origin':'human'}}
        self.assertEqual('unknown',origin_command(command)['contribution_origin'])
        self.assertEqual('ai',origin_command(command,'ai')['contribution_origin'])
        self.assertEqual('human',command['payload']['origin'])

    def test_declared_ai_and_mixed_origins_require_later_review(self):
        from application import test_co_report as co
        from claimbranch.application.co_report import prepare_co_report
        from claimbranch.application.claim_wording import prepare_revision
        from claimbranch.core.research_history import _reduce,_branch_ai
        helper=co.CoReportTests();helper.setUp();self.addCleanup(helper.doCleanups)
        for origin in ('ai','mixed'):
            base=helper.manual_base();policy=self.policy();policy['claim_id']='T'
            changed,_=prepare_revision(base,'set-claim-wording',policy,contribution_origin=origin)
            state=_reduce(changed.work.history.seed,changed.work.history.commands)
            self.assertTrue(_branch_ai(state['branches']['main'],state))
            request=helper.request(disposition='not-required')
            for reading in request['candidates']:reading.update(claim_id='T',origin='human')
            with self.assertRaisesRegex(ContractError,'requires answer or deferral'):
                prepare_co_report(changed,request,contribution_origin='human')

    def test_omitted_critique_private_literal_cannot_leak_through_selected_wording(self):
        from application import test_critiques as critiques
        request=self.batch('human');request['entries'][0]['request']['allowed_wording']=[critiques.SECRET]
        request['entries'].append(dict(id='omitted-critique',kind='critique',origin='human',request=critiques.CritiqueTests.request(self)))
        candidate,preview=prepare_batch(self.project,encode(request,purpose='project'));self.assertTrue(preview['valid'])
        with self.assertRaisesRegex(ContractError,'known private'):
            prepare_share(candidate,dict(schema='claimbranch.share-selection/v1',record_ids=['C'],reason_ids=[]))

    def test_shared_measurement_includes_ai_condition_label_origin(self):
        from application import test_typed_observations as measurements
        from claimbranch.application.typed_observations import prepare_measurement
        helper=measurements.TypedObservationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        base=helper.base();request=helper.declaration('ai-label',['generated'])
        base,_=prepare_measurement(base,request,contribution_origin='ai')
        table=helper.table();table['conditions'].append(dict(key='ai-label',value='generated'))
        candidate,_=prepare_measurement(base,helper.request(base,table=table),contribution_origin='human')
        result=decode(prepare_share(candidate,dict(schema='claimbranch.share-selection/v1',record_ids=['O'],reason_ids=[])),purpose='project')
        observation=next(r for r in result['records'] if r['kind']=='observation')
        self.assertIn('ai',observation['content']['origins'])

    def test_mixed_typed_batch_preserves_private_sources_and_reopens_exactly(self):
        from application import test_typed_observations as measurements
        from application import test_critiques as critiques
        from claimbranch.application.protocols import prepare_protocol
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups)
        base=helper.base()
        protocol_request=helper.register(base)[1]['operation']['payload']
        (helper.paper/'figure.tex').write_text('% claimbranch:start id=figure\nSynthetic figure.\n% claimbranch:end id=figure\n')
        measure=measurements.TypedObservationTests()
        entries=[dict(id='protocol',kind='protocol',origin='human',request=helper.request('register-protocol',protocol_request)),
            dict(id='association',kind='protocol',origin='unknown',request=helper.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=protocol_request['expected_plan_digest'],rationale='Associate existing synthetic experiment.'))),
            dict(id='figure',kind='anchor',origin='human',request=dict(manuscript='figure.tex',anchor_id='figure',kind='figure',expresses=['T'],plots=['O'],parents=[],rationale='Show the registered observation.')),
            dict(id='critique',kind='critique',origin='mixed',request=critiques.CritiqueTests.request(self))]
        # Vocabulary entries precede the measurement that refers to them.
        for key,values in [('model',['M1']),('seed',['s1','s2','s3']),('dose',['low','mid','high']),('leg',['primary','sensitivity'])]:
            entries.append(dict(id=key,kind='measurement',origin='human',request=measure.declaration(key,values)))
        entries.append(dict(id='measurement',kind='measurement',origin='ai',request=measure.request(base)))
        raw=encode(dict(schema='claimbranch.metadata-batch/v1',entries=entries,selected_ids=[e['id'] for e in entries]),purpose='project')
        candidate,preview=prepare_batch(base,raw);self.assertTrue(preview['valid'],preview)
        self.assertNotIn(critiques.SECRET,str(preview));self.assertNotIn(critiques.ORIGINAL,str(preview))
        with PersonalProjectStore.create(helper.work,project_id=base.project_id) as store:
            store.save(base,preview=helper.preview);store.save(candidate)
        with PersonalProjectStore(helper.work) as store:
            returned=store.load();backup=store.backup()
        self.assertEqual(candidate.payload,returned.payload);self.assertEqual(candidate.payload,split_personal_backup(backup).payload)
        view=returned.work.history.view('main')
        self.assertEqual(18,len(view['evidence'][0]['measurement']['rows']))
        self.assertEqual('unknown',view['metadata_origins'][next(k for k,v in view['metadata_origins'].items() if v['operation_type']=='associate-experiment')]['origin'])

    def test_tui_real_saved_boundary_cancel_resize_stale_and_confirm(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_metadata import MetadataUI
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.tui import Frame
        path=self.root/'metadata.json';path.write_bytes(encode(self.batch(),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            app=project_workspace(self.project);app.recovery=PersonalProjectRecovery(store,app,self.project)
            size=[40,140];term=SimpleNamespace(app=app,modal=None,screen=SimpleNamespace(getmaxyx=lambda:tuple(size)))
            ui=MetadataUI(term);ui.open();ui.path.key(('paste',str(path)),100);ui.key('enter')
            before=store.load().work.history.commands
            ui.key('escape');self.assertEqual(before,store.load().work.history.commands)
            ui.open();ui.path.key(('paste',str(path)),100);ui.key('enter');ui.key('end');ui.draw(Frame(140,40))
            size[:]=[16,40];ui.key('r');self.assertEqual('metadata-preview',term.modal)
            size[:]=[40,140];ui.key('r');ui.confirmation.key(('paste','register'),100)
            path.write_bytes(path.read_bytes()+b' ');ui.dispatch('enter')
            self.assertEqual('metadata-input',term.modal);self.assertEqual(before,store.load().work.history.commands)
            path.write_bytes(encode(self.batch(),purpose='project'));ui.key('enter');ui.key('end');ui.draw(Frame(140,40));ui.key('r')
            for letter in 'register':ui.key(letter)
            ui.dispatch('enter');self.assertIsNone(term.modal)
            self.assertEqual(2,len(store.load().work.history.view('main')['metadata_origins']))
            self.assertEqual(store.load().work.history.commands,app.paper.history.commands)
