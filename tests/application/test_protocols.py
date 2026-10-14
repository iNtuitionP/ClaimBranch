from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned protocol failures, rule amendments, provenance and durable return."""
import io
import unittest
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch
from application import test_claim_wording as prior
from application import test_co_report as co
from claimbranch.application.protocols import prepare_protocol,recheck_protocol
from claimbranch.core.protocols import plan_digest,protocol_context
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from claimbranch.core.review import Judgment
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.project_work import ProjectWork
from claimbranch.application.personal_project import PersonalProjectStore,PROTOCOL_PERSONAL_MAGIC
from claimbranch.application.personal_archive import personal_backup,split_personal_backup,PROTOCOL_BACKUP_MAGIC
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.paper_service import PaperService

class ProtocolTests(unittest.TestCase):
    setUp=prior.ClaimWordingTests.setUp

    def base(self):
        project=co.CoReportTests.manual_base(self);h=project.work.history
        def append(kind,payload,key,episode='local'):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=project.project_id,episode_id=episode,created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        run=h.view('main')['experiments'][0]
        judgment=Judgment.start(project.project_id,'local').edit('The synthetic result has limited support.','Compare the prediction against a fixed rule.')
        changes=[dict(id='I',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O'])),dict(id='edge',kind='scientific-edge',body=dict(source_id='O',target_id='T',edge_type='supports',rationale='Synthetic direct support.')),
            dict(id='P',kind='experiment-plan',body=dict(claim_id='T',objective='Does the ordering survive?',status='planned',conditions='Synthetic fixed settings.',metric=run['metric']))]
        append('create-reasoning-branch',{},'branch');append('record-interpretation',dict(changes=changes,judgment=asdict(judgment)),'record')
        append('apply-selected-merge',dict(selected_ids=[c['id'] for c in changes],judgment=asdict(judgment),disposition='not-required',answers=[]),'merge')
        append('close-episode',{},'close');append('open-episode',dict(title='New test',question='Did the registered prediction survive?'),'open-protocol','protocol-episode')
        return project.with_work(PaperWork.create(h))

    def request(self,kind,payload):return dict(schema='claimbranch.protocol-input/v1',operation_type=kind,payload=payload)

    def register(self,project=None,**changes):
        project=project or self.base();plan=next(c for c in project.work.history.view('main')['changes'] if c['id']=='P')
        payload=dict(id='protocol',plan_id='P',expected_plan_digest=plan_digest(plan),supersedes_id=None,prediction='A exceeds B at the fixed dose.',falsifier='B equals or exceeds A.',
            prewritten_wording=dict(pass_wording='Direction retained under this definition.',fail_wording='The registered ordering failed.'),committed_ref=dict(reference='git:claimed-commit',claimed_at='claimed before computation'),
            inspected_before_registration='unseen',origin='human',source_context='Synthetic external preregistration claim.',gates=[dict(id='identity',name='Cross-run identity',tolerance='exact identity',reference='registered estimand')],rationale='Keep the original prediction and gate.')
        payload.update(changes);return prepare_protocol(project,self.request('register-protocol',payload))

    def associated(self):
        project,_=self.register();protocol=project.work.history.view('main')['protocols']['protocol']
        return prepare_protocol(project,self.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=protocol['expected_plan_digest'],rationale='Explicitly associate the synthetic completed record.')))[0]

    def basis(self,project):
        e=project.work.history.view('main')['evidence'][0];return [dict(observation_id=e['id'],event_id=e['history'][-1]['event_id'])]

    def gate(self,project,status='failed',**changes):
        payload=dict(id='gate-result',association_id='association',gate_id='identity',rule_id='identity',status=status,observation_revisions=self.basis(project),source_context='The source record reports this gate result.',origin='human',rationale='Preserve the registered gate result.')
        payload.update(changes);return prepare_protocol(project,self.request('record-gate-result',payload))

    def outcome(self,project,**changes):
        payload=dict(id='outcome',association_id='association',rule_ids=['identity'],gate_result_ids=[],observation_revisions=self.basis(project),classification='not-consistent',discrimination='discriminating',limitations=[],source_context='Synthetic result classification.',origin='human',rationale='The observed ordering contradicted the prediction.')
        payload.update(changes);return prepare_protocol(project,self.request('record-outcome',payload))

    def amendment(self,project,**changes):
        payload=dict(id='new-rule',protocol_id='protocol',gate_id='identity',expected_rule_id='identity',new_tolerance='wider tolerance',new_reference='new estimand',decided_after_result='after',origin='human',source_context='Synthetic rule amendment.',rationale='Disclose the revised gate after its failure.')
        payload.update(changes);return prepare_protocol(project,self.request('amend-gate-rule',payload))

    def test_registration_retains_prediction_falsifier_wording_commit_unknown_chronology(self):
        base=self.base();project,preview=self.register(base);p=project.work.history.view('main')['protocols']['protocol']
        self.assertEqual('B equals or exceeds A.',p['falsifier']);self.assertEqual('git:claimed-commit',p['committed_ref']['reference']);self.assertFalse(p['chronology_verified'])
        self.assertEqual(base.work.history.commands,project.work.history.commands[:-1]);self.assertEqual(base.work.history.seed,project.work.history.seed)
        self.assertEqual(base.work.history.view('main')['evidence'],project.work.history.view('main')['evidence']);self.assertEqual(base.work.history.view('main')['claims'],project.work.history.view('main')['claims'])
        self.assertEqual('claimbranch.project-work/v18',decode(project.payload,purpose='project')['schema'])
        self.assertNotEqual(base.work.history.heads,project.work.history.heads)

    def test_failed_prediction_and_non_discriminating_pass_remain_distinct(self):
        base=self.associated();failure,_=self.outcome(base);self.assertEqual('not-consistent',failure.work.history.view('main')['outcome_assessments']['outcome']['classification'])
        passed,_=self.outcome(failure,id='nondiscriminating',classification='consistent',discrimination='non-discriminating',limitations=['Two predictors made identical calls in every cell.'])
        context=protocol_context(passed.work.history.view('main'))['T'][0]
        self.assertEqual(['not-consistent','consistent'],[o['classification'] for o in context['outcomes']]);self.assertIn('identical calls',str(context))
        with self.assertRaisesRegex(ContractError,'reported limitation'):self.outcome(base,classification='consistent',discrimination='non-discriminating')

    def test_cross_run_identity_failure_new_reference_and_after_result_tolerance_widening(self):
        base=self.associated();failed,_=self.gate(base);stopped,_=self.outcome(failed,classification='stopped-at-gate',gate_result_ids=['gate-result'])
        before=stopped.work.history.view('main')['evidence'];changed,_=self.amendment(stopped)
        passed,_=self.gate(changed,status='passed',id='passed-new-rule',rule_id='new-rule')
        result,_=self.outcome(passed,id='new-outcome',rule_ids=['new-rule'],gate_result_ids=['passed-new-rule'],classification='consistent',limitations=['The original gate failed; the new rule was decided after the result.'])
        context=protocol_context(result.work.history.view('main'))['T'][0]
        self.assertEqual(before,result.work.history.view('main')['evidence']);self.assertEqual('failed',context['gate_results'][0]['status']);self.assertEqual('stopped-at-gate',context['outcomes'][0]['classification'])
        self.assertTrue(context['amendments'][0]['app_result_precedes_amendment']);self.assertEqual('after',context['current_rules']['identity']['decided_after_result'])
        self.assertTrue(context['outcomes'][0]['rule_differs_from_current']);self.assertFalse(context['outcomes'][1]['rule_differs_from_current'])
        self.assertFalse(context['outcomes'][0]['basis_stale'])

    def test_forged_before_result_disclosure_stays_unverified_and_conflict_visible(self):
        base=self.associated();project,_=self.amendment(base,decided_after_result='before')
        a=project.work.history.view('main')['gate_amendments']['new-rule'];self.assertTrue(a['chronology_conflict']);self.assertFalse(a['chronology_verified'])
        self.assertTrue(a['app_result_precedes_amendment']);self.assertEqual('before',a['decided_after_result'])

    def test_unknown_and_exploratory_provenance_have_no_confirmatory_certificate(self):
        for disclosure,expected in [('unknown','unknown'),('seen','exploratory-disclosed'),('unseen','source-claimed')]:
            project,_=self.register(inspected_before_registration=disclosure,committed_ref=None)
            context=protocol_context(project.work.history.view('main'))['P'][0]
            self.assertEqual(expected,context['confirmatory_provenance']);self.assertFalse(context['chronology_verified'])

    def test_rule_and_basis_id_mismatches_refuse_before_append(self):
        base=self.associated();original=base.payload
        for changes in (dict(rule_ids=['missing']),dict(observation_revisions=[dict(observation_id='O',event_id='missing')]),dict(gate_result_ids=['missing']),dict(classification='stopped-at-gate')):
            with self.assertRaises(ContractError):self.outcome(base,**changes)
        with self.assertRaises(ContractError):self.gate(base,rule_id='missing')
        with self.assertRaises(ContractError):self.amendment(base,expected_rule_id='missing')
        self.assertEqual(original,base.payload)

    def test_changed_evidence_marks_old_outcome_stale_and_new_assessment_needs_latest_event(self):
        base,_=self.outcome(self.associated());h=base.work.history;command=dict(schema_version=4,id='correction',project_id=base.project_id,episode_id='protocol-episode',created_at=decode(h.commands[-1],purpose='history')['created_at'],operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='corrected-event',target_id='O',run_id='X',action='correct',statement='Corrected synthetic observation.',value='0.6',rationale='Keep the numerical correction separate.',supersedes_id='event'))
        changed=base.with_work(PaperWork.create(h.append(command)));context=protocol_context(changed.work.history.view('main'))['T'][0];self.assertTrue(context['outcomes'][0]['basis_stale'])
        with self.assertRaises(ContractError):self.outcome(changed,id='stale-assessment',observation_revisions=self.basis(base))
        current,_=self.outcome(changed,id='current-assessment');self.assertEqual('0.6',current.work.history.view('main')['evidence'][0]['value'])
        self.assertEqual('0.5',context['outcomes'][0]['observation_snapshots'][0]['value'])

    def test_gate_changes_invalidate_existing_exact_confirmation(self):
        base=self.associated();candidate,preview=self.outcome(base);changed,_=self.amendment(base)
        with self.assertRaisesRegex(ContractError,'changed'):recheck_protocol(changed,preview)
        command=decode(candidate.work.history.commands[-1],purpose='history')
        with self.assertRaisesRegex(ContractError,'stale heads'):changed.work.history.append(command)

    def test_source_reader_and_claim_dependent_paths_show_original_failure_amendment(self):
        base,_=self.gate(self.associated());project,_=self.amendment(base)
        graph=PaperService(project.work.history).query('main');claim=next(n for n in graph['nodes'] if n['id']=='T')
        self.assertIn('failed',str(claim['content']['protocol_context']));self.assertIn('wider tolerance',str(claim['content']['protocol_context']))
        app=project_workspace(project);app.select('T');self.assertIn('REGISTERED RULES',str(app.detail()));self.assertIn('chronology_verified',str(app.detail()))

    def test_save_restart_backup_keep_notes_rules_originals_and_no_live_provider(self):
        from claimbranch.application.tui_work_recovery import snapshot_value
        base=self.associated();app=project_workspace(base);app.select('T');app.notes[app.context_key()]='Keep the original registered failure.'
        base=base.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)));base,_=self.gate(base);project,_=self.amendment(base)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC));backup=store.backup()
        self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC));returned=split_personal_backup(backup);self.assertEqual(project.payload,returned.payload)
        app=project_workspace(returned);self.assertIn('Keep the original registered failure.',app.notes.values());self.assertIsNone(getattr(app,'provider_connection',None))
        with PersonalProjectStore(self.work) as store:self.assertEqual(project.payload,store.load().payload)

    def test_cli_dry_run_cancel_changed_input_and_confirm(self):
        from claimbranch.application.cli import main
        base=self.base();candidate,preview=self.register(base);request=self.request('register-protocol',preview['operation']['payload']);path=self.root/'protocol.json';path.write_bytes(encode(request,purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        args=['project','protocol','--directory',str(self.work),'--input',str(path)];before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(args+['--dry-run']))
        self.assertIn('falsifier',output.getvalue());self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value='q'),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def answer(prompt):return 'record' if prompt.startswith('Type record') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):self.assertEqual(0,main(args))
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','protocols','--directory',str(self.work),'--node','P']))
        self.assertIn('prediction',output.getvalue())

    def test_sensitivity_reversal_can_be_qualifying_co_report_without_picking_one(self):
        base=self.associated();primary,_=self.outcome(base,classification='consistent',limitations=['Primary definition only.'])
        sensitivity,_=self.outcome(primary,id='sensitivity-outcome',classification='not-consistent',limitations=['Grouped sensitivity reverses the primary reading.'])
        request=co.CoReportTests.request(self,disposition='deferred')
        request['candidates'][0].update(claim_id='T',origin='human',scope='Primary definition only')
        request['candidates'][1].update(claim_id='T',origin='human',scope='Grouped sensitivity definition only')
        from claimbranch.application.co_report import prepare_co_report
        result,_=prepare_co_report(sensitivity,request);view=result.work.history.view('main')
        self.assertEqual('qualifies',next(c for c in view['changes'] if c['id']=='sensitivity-edge')['body']['edge_type'])
        self.assertEqual(['consistent','not-consistent'],[o['classification'] for o in protocol_context(view)['T'][0]['outcomes']])
        self.assertEqual(primary.work.history.view('main')['evidence'],view['evidence'])
        app=project_workspace(result);app.select('sensitivity');self.assertIn('Grouped sensitivity',str(app.detail()));self.assertIn('sensitivity-outcome',str(app.detail()))

    def test_known_ai_and_unknown_protocol_sources_require_an_explanation_choice(self):
        from claimbranch.application.co_report import prepare_co_report
        for origin in ('ai','mixed','unknown'):
            base,_=self.register(origin=origin);request=co.CoReportTests.request(self,disposition='not-required')
            for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human'
            with self.assertRaisesRegex(ContractError,'requires answer or deferral'):prepare_co_report(base,request)
            request['disposition']='deferred';result,preview=prepare_co_report(base,request)
            self.assertTrue(preview['decision']['origin_review_required']);self.assertFalse(preview['decision']['understanding_verified'])
            app=project_workspace(result);app.select('P');self.assertIn(origin,str(app.detail()))

    def test_gate_and_assessment_records_are_immutable_ids_and_revision_chains(self):
        base=self.associated();first,_=self.amendment(base)
        with self.assertRaisesRegex(ContractError,'Stale'):self.amendment(first,id='another-rule')
        second,_=self.amendment(first,id='another-rule',expected_rule_id='new-rule',new_tolerance='third tolerance')
        view=second.work.history.view('main');self.assertEqual('new-rule',view['gate_amendments']['another-rule']['before_rule']['id'])
        for identity in ('T','P','identity','association','protocol'):
            with self.assertRaises(ContractError):self.outcome(base,id=identity)
        with self.assertRaisesRegex(ContractError,'identity'):self.amendment(first)
        self.assertEqual('exact identity',protocol_context(view)['T'][0]['original_and_amended_rules']['identity']['tolerance'])

    def test_multiple_gates_need_one_rule_each_and_matching_result_basis(self):
        base=self.base();project,_=self.register(base,gates=[dict(id='identity',name='Identity',tolerance='exact',reference='source'),dict(id='noise',name='Noise',tolerance='small',reference='noise reference')])
        protocol=project.work.history.view('main')['protocols']['protocol']
        project,_=prepare_protocol(project,self.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=protocol['expected_plan_digest'],rationale='Associate this run.')))
        with self.assertRaisesRegex(ContractError,'exactly one'):self.outcome(project)
        passed,_=self.outcome(project,rule_ids=['identity','noise'],classification='inconclusive')
        self.assertEqual(2,len(passed.work.history.view('main')['outcome_assessments']['outcome']['rule_snapshots']))
        gate,_=self.gate(project);with_gate,_=self.outcome(gate,rule_ids=['identity','noise'],gate_result_ids=['gate-result'])
        with self.assertRaisesRegex(ContractError,'Unique observation'):self.outcome(with_gate,id='wrong-basis',rule_ids=['identity','noise'],gate_result_ids=['gate-result'],observation_revisions=self.basis(project)*2)

    def test_plan_digest_revision_registration_preserves_previous_protocol(self):
        base,_=self.register();p=base.work.history.view('main')['protocols']['protocol']
        with self.assertRaisesRegex(ContractError,'latest protocol'):self.register(base,id='duplicate-protocol')
        revised,_=self.register(base,id='protocol-revision',supersedes_id='protocol',gates=[dict(id='new-gate',name='Revised identity',tolerance='unchanged exact',reference='grouped units')],inspected_before_registration='seen')
        protocols=revised.work.history.view('main')['protocols'];self.assertEqual(p,protocols['protocol']);self.assertEqual(['protocol'],protocols['protocol-revision']['prior_protocol_ids'])
        wrong='0'*64
        with self.assertRaisesRegex(ContractError,'Plan changed'):self.register(base,id='wrong-plan',expected_plan_digest=wrong,supersedes_id='protocol')

    def test_inactive_wrong_experiment_and_retained_revision_context(self):
        base=self.associated();h=base.work.history;old=h.commands[-1]
        command=dict(schema_version=4,id='withdraw',project_id=base.project_id,episode_id='protocol-episode',created_at=decode(old,purpose='history')['created_at'],operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='withdrawn',target_id='O',run_id='X',action='retract',statement=None,value=None,rationale='Source withdrawn.',supersedes_id='event'))
        changed=base.with_work(PaperWork.create(h.append(command)))
        with self.assertRaisesRegex(ContractError,'current active'):self.outcome(changed)
        result,_=self.outcome(base);operation=decode(result.work.history.commands[-1],purpose='history')['id'];prefix=PaperService(result.work.history).query('main',at_operation=operation)
        self.assertIn('outcome',str(prefix));self.assertEqual(h.commands,result.work.history.commands[:-1])

    def test_structured_measurement_cells_do_not_change_when_gate_rules_change(self):
        from claimbranch.application.typed_observations import prepare_measurement
        from application import test_typed_observations as measurements
        base=self.associated();table=measurements.TypedObservationTests.table(self);table['conditions']=[]
        for row in table['rows']:row['conditions']=[]
        observation=base.work.history.view('main')['evidence'][0]
        request=dict(schema='claimbranch.measurement-input/v1',operation_type='record-measurement',payload=dict(event_id='typed',target_id='O',run_id='X',expected_revision=observation['history'][-1]['event_id'],action='transform',statement=observation['statement'],rationale='Retain exact table.',source_context='Synthetic only.',table=table,corrections=[]))
        base,_=prepare_measurement(base,request);result,_=self.amendment(base)
        self.assertEqual(base.work.history.view('main')['evidence'],result.work.history.view('main')['evidence'])

    def test_changed_input_and_source_cancel_before_any_save(self):
        from claimbranch.application.cli import main
        base=self.base();candidate,preview=self.register(base);request=self.request('register-protocol',preview['operation']['payload']);path=self.root/'protocol.json';path.write_bytes(encode(request,purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        before=(self.work/'personal.cbp').read_bytes()
        def answer(prompt):
            if prompt.startswith('Type record'):
                request['payload']['prediction']='Different prediction';path.write_bytes(encode(request,purpose='project'));return 'record'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','protocol','--directory',str(self.work),'--input',str(path)]))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        (self.paper/'paper.tex').write_bytes(self.manuscript+b'% changed')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_protocol(base,preview)

    def test_actual_pty_record_fresh_open_and_shipped_old_reader_refusal(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        from types import ModuleType
        base=self.base();_,preview=self.register(base);path=self.root/'protocol.json';path.write_bytes(encode(self.request('register-protocol',preview['operation']['payload']),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        def terminal(arguments,record=False):
            master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0));process=subprocess.Popen([sys.executable,'-m','claimbranch',*arguments],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'));os.close(slave)
            output=b'';pending=b'';quit_sent=False;deadline=time.monotonic()+30
            try:
                while process.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],0.1)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        output+=chunk;pending+=chunk
                        if record:
                            if b'Enter: next page' in pending:os.write(master,b'\n');pending=b''
                            elif b'Type record to save' in pending:os.write(master,b'record\n');pending=b''
                        elif b'ClaimBranch' in output and not quit_sent:os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-3000:].decode(errors='replace'))
                if record:self.assertIn(b'Protocol operation saved',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(['project','protocol','--directory',str(self.work),'--input',str(path)],True);terminal(['project','open','--directory',str(self.work)])
        old=__import__('pathlib').Path(__file__).with_name('legacy_personal_project.py').read_text();module=ModuleType('claimbranch.application.protocol_old');module.__package__='claimbranch.application';exec(compile(old,'old-reader','exec'),module.__dict__)
        raw=(self.work/'personal.cbp').read_bytes()
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_incomplete_or_failed_gates_do_not_certify_a_consistent_prediction(self):
        base=self.associated();incomplete,_=self.outcome(base,classification='consistent');outcome=incomplete.work.history.view('main')['outcome_assessments']['outcome']
        self.assertEqual('incomplete-gate-assessment',outcome['gate_validity']);self.assertEqual(['identity'],outcome['unassessed_gate_ids']);self.assertFalse(outcome['validity_verified'])
        gate,_=self.gate(base);consistent,_=self.outcome(gate,classification='consistent',gate_result_ids=['gate-result'])
        outcome=consistent.work.history.view('main')['outcome_assessments']['outcome'];self.assertEqual('consistent',outcome['classification']);self.assertEqual('failed-gate',outcome['gate_validity']);self.assertFalse(outcome['validity_verified'])

    def test_superseded_rules_are_inspectable_but_cannot_be_amended_or_newly_associated(self):
        base,_=self.register();revised,_=self.register(base,id='revision',supersedes_id='protocol',gates=[dict(id='revised-gate',name='Revised',tolerance='new',reference='new')])
        with self.assertRaisesRegex(ContractError,'Superseded'):self.amendment(revised)
        p=revised.work.history.view('main')['protocols']['protocol']
        with self.assertRaisesRegex(ContractError,'Superseded'):prepare_protocol(revised,self.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=p['expected_plan_digest'],rationale='Associate old rules.')))
        context=protocol_context(revised.work.history.view('main'))['P'];self.assertEqual(['revision'],context[0]['superseded_by'])

    def test_existing_app_result_disclosed_at_association_but_not_certified_seen(self):
        project=self.associated();association=project.work.history.view('main')['experiment_associations']['association']
        self.assertEqual(['O'],association['app_observations_known_before_registration']);self.assertTrue(association['preinspection_disclosure_conflict']);self.assertFalse(association['chronology_verified'])

    def test_view_annotation_does_not_change_plan_digest_and_imported_sources_remain(self):
        import json
        from application.test_argument_import import fixture
        from claimbranch.core.argument_import import _leaves,history_from_import
        from claimbranch.core.paper_capacity import source_bytes,source_record
        envelope=fixture();original=json.loads(source_bytes(envelope['source']))
        body=dict(claim_id='C',objective='Does the rubric relation survive?',status='planned',conditions='Fixed prompts',metric=envelope['records'][2]['body']['metric'])
        original['entries'].append({**body,'prediction':'A source-only prior prediction.'})
        envelope['records'].append(dict(id='P',kind='experiment-plan',body=body,source_pointer='/entries/6',origin=dict(contributor='ai',detail='A declared original AI suggestion.'),recorded_at=None,
            mappings=[dict(target=pointer,source='/entries/6'+pointer,transformation=None) for pointer,_ in _leaves(body)]))
        envelope['selected_ids'].append('P');envelope['source']=source_record(json.dumps(original).encode())
        raw=encode(envelope,purpose='project');h=history_from_import(raw,anchor_id='anchor')
        h=h.append(dict(schema_version=5,id='open',project_id='synthetic-paper',episode_id='protocol-episode',created_at='2026-10-14T00:00:00Z',operation_type='open-episode',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(title='Protocol',question='What was registered?')))
        project=ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw);before=h.view('main');registered,_=self.register(project)
        context=protocol_context(registered.work.history.view('main'))['P'][0]
        self.assertFalse(context['plan_changed_since_registration']);self.assertTrue(any(r['contributor']=='ai' for r in context['protocol']['source_refs']))
        self.assertEqual(before['imported_records'],registered.work.history.view('main')['imported_records']);self.assertEqual(before['unresolved_source_pointers'],registered.work.history.view('main')['unresolved_source_pointers'])

    def test_unassociated_amendment_conflict_appears_when_run_is_later_associated(self):
        base,_=self.register();amended,_=self.amendment(base,decided_after_result='before');protocol=amended.work.history.view('main')['protocols']['protocol']
        associated,_=prepare_protocol(amended,self.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=protocol['expected_plan_digest'],rationale='Associate the existing result.')))
        association=associated.work.history.view('main')['experiment_associations']['association'];self.assertEqual(['new-rule'],association['amendment_disclosure_conflicts'])
        context=protocol_context(associated.work.history.view('main'))['T'][0];self.assertTrue(context['amendments'][0]['later_association_disclosure_conflict'])
        self.assertFalse(context['amendments'][0]['chronology_verified'])

    def test_plan_test_context_and_digest_available_before_any_result_association(self):
        from claimbranch.application.cli import main
        base=self.base();project,_=self.register(base)
        self.assertIn('T',protocol_context(project.work.history.view('main')))
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','protocols','--directory',str(self.work)]))
        self.assertIn('available_plans',output.getvalue());self.assertIn(plan_digest(next(c for c in base.work.history.view('main')['changes'] if c['id']=='P')),output.getvalue())

    def test_changed_plan_refuses_old_rule_amendment(self):
        base,_=self.register();h=base.work.history;stamp=decode(h.commands[-1],purpose='history')['created_at']
        # New metadata input has unknown origin; preserve that independent review requirement.
        def append(kind,payload,key):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=base.project_id,episode_id='protocol-episode',created_at=stamp,operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        plan=deepcopy(next(c for c in h.view('main')['changes'] if c['id']=='P'));plan['body']['conditions']='Different post-result conditions'
        judgment=Judgment.start(base.project_id,'protocol-episode').edit('A new conditional interpretation.','The current plan was changed deliberately.')
        interpretation=dict(id='I-new',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))
        append('create-reasoning-branch',{},'branch-new');append('record-interpretation',dict(changes=[interpretation,plan],judgment=asdict(judgment)),'record-new');append('apply-selected-merge',dict(selected_ids=['I-new','P'],judgment=asdict(judgment),disposition='deferred',answers=[]),'merge-new')
        changed=base.with_work(PaperWork.create(h))
        self.assertTrue(protocol_context(h.view('main'))['T'][0]['plan_changed_since_registration'])
        with self.assertRaisesRegex(ContractError,'Current plan differs'):self.amendment(changed)
        old=protocol_context(h.view('main',episode_id='local'))['T'][0]
        self.assertTrue(old['plan_changed_since_registration']);self.assertTrue(old['view_plan_matches_registration'])
        newer,_=self.register(changed,id='new-registration',supersedes_id='protocol',gates=[dict(id='new-registration-gate',name='Revised gate',tolerance='exact',reference='Revised plan')])
        prior_view=protocol_context(newer.work.history.view('main',episode_id='local'))['T']
        context=next(c for c in prior_view if c['protocol']['id']=='new-registration')
        self.assertFalse(context['plan_changed_since_registration']);self.assertFalse(context['view_plan_matches_registration'])

    def test_alternative_review_expected_heads_are_revoked_by_global_rule_amendment(self):
        base=self.associated();h=base.work.history;stamp=decode(h.commands[-1],purpose='history')['created_at']
        h=h.append(dict(schema_version=4,id='alt',project_id=base.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='create-reasoning-branch',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload={}))
        base=base.with_work(PaperWork.create(h));judgment=Judgment.start(base.project_id,'protocol-episode').edit('Alternative reading.','Use a current rule.')
        command=dict(schema_version=4,id='old-review',project_id=base.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='record-interpretation',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(changes=[dict(id='new-reading',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))],judgment=asdict(judgment)))
        revised,_=self.amendment(base);command['created_at']=decode(revised.work.history.commands[-1],purpose='history')['created_at']
        with self.assertRaisesRegex(ContractError,'stale heads'):revised.work.history.append(command)

    def test_gate_outcome_basis_is_set_like_not_input_order(self):
        base=self.associated();h=base.work.history;stamp=decode(h.commands[-1],purpose='history')['created_at']
        h=h.append(dict(schema_version=4,id='other-observation',project_id=base.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='event-2',target_id='O2',run_id='X',action='confirm',statement='Another synthetic result.',value='0.2',rationale='Same completed experiment.',supersedes_id=None)))
        base=base.with_work(PaperWork.create(h));basis=[dict(observation_id='O',event_id='event'),dict(observation_id='O2',event_id='event-2')]
        gate,_=self.gate(base,observation_revisions=basis);result,_=self.outcome(gate,observation_revisions=list(reversed(basis)),gate_result_ids=['gate-result'],classification='stopped-at-gate')
        self.assertEqual(2,len(result.work.history.view('main')['outcome_assessments']['outcome']['observation_revisions']))

    def test_outcome_budget_refuses_before_append_with_limit_and_count(self):
        from claimbranch.core.research_history import ResearchHistory
        base=self.associated();h=base.work.history;_,preview=self.outcome(base);payload=preview['operation']['payload'];stamp=preview['operation']['created_at'];commands=list(h.commands);heads=dict(h.heads)
        for index in range(256):
            command=dict(schema_version=10,id='outcome-operation-'+str(index),project_id=base.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='record-outcome',expected_heads=dict(heads),evidence_watermark=h.watermark,payload={**payload,'id':'outcome-'+str(index)})
            commands.append(encode(command,purpose='history'));heads={'main':command['id']}
        combined=ResearchHistory(h.seed,tuple(commands));self.assertEqual(256,combined.capacity()['resources']['outcome_assessments']['used'])
        self.assertEqual(combined.manifest(),ResearchHistory(combined.seed,combined.commands).manifest())
        project=base.with_work(PaperWork.create(combined));before=project.payload
        with self.assertRaisesRegex(ContractError,'outcome_assessments: 257 / 256'):self.outcome(project,id='overflow')
        self.assertEqual(before,project.payload)

    def test_public_backup_restore_and_provider_gate_remain_separate(self):
        from claimbranch.application.cli import main
        project,_=self.amendment(self.associated())
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        archive=self.root/'protocol-backup';restored=self.root/'protocol-restored';archive.mkdir(mode=0o700);restored.mkdir(mode=0o700)
        with patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(0,main(['project','backup','--directory',str(self.work),'--archive-directory',str(archive)]))
            self.assertEqual(0,main(['project','restore','--directory',str(restored),'--archive-directory',str(archive)]))
        with PersonalProjectStore(restored) as store:self.assertEqual(project.payload,store.load().payload)
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('claimbranch.application.provider_commands.PersonalProviderConnection',side_effect=AssertionError('Provider must remain unopened')),patch('sys.stderr',new_callable=io.StringIO) as output:
            self.assertEqual(1,main(['project','open','--directory',str(restored),'--provider-directory',str(self.root/'never-open')]))
        self.assertIn('not qualified',output.getvalue())

    def test_earlier_episode_without_plan_does_not_report_an_unchanged_plan_as_changed(self):
        base=co.CoReportTests.manual_base(self);h=base.work.history
        def append(kind,payload,key,episode='later'):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=base.project_id,episode_id=episode,created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        append('close-episode',{},'close-before-plan','local');append('open-episode',dict(title='Later plan',question='What will the planned test show?'),'open-later')
        judgment=Judgment.start(base.project_id,'later').edit('A later planned test.','Keep its prediction distinct.')
        metric=h.view('main')['experiments'][0]['metric'];plan=dict(id='P',kind='experiment-plan',body=dict(claim_id='T',objective='Test the later plan',status='planned',conditions='Fixed',metric=metric))
        interpretation=dict(id='later-I',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))
        append('create-reasoning-branch',{},'later-branch');append('record-interpretation',dict(changes=[interpretation,plan],judgment=asdict(judgment)),'later-record');append('apply-selected-merge',dict(selected_ids=['P','later-I'],judgment=asdict(judgment),disposition='not-required',answers=[]),'later-merge')
        project,_=self.register(base.with_work(PaperWork.create(h)));p=project.work.history.view('main')['protocols']['protocol']
        project,_=prepare_protocol(project,self.request('associate-experiment',dict(id='association',protocol_id='protocol',experiment_id='X',expected_plan_digest=p['expected_plan_digest'],rationale='Explicitly associate the earlier result.')))
        older=project.work.history.view('main',episode_id='local');context=protocol_context(older)['O'][0]
        self.assertEqual('not-in-this-reasoning-view',context['plan_visibility']);self.assertFalse(context['plan_changed_since_registration']);self.assertIsNone(context['view_plan_matches_registration']);self.assertTrue(context['global_registry'])
        current=protocol_context(project.work.history.view('main'))['O'][0];self.assertEqual('available',current['plan_visibility']);self.assertFalse(current['plan_changed_since_registration'])
