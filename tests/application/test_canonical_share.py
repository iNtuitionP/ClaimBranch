"""Owned selected sharing: privacy, deterministic bindings and create-only files."""
import io
import json
import os
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from application import test_critiques as critique_tests
SECRET, ORIGINAL = critique_tests.SECRET, critique_tests.ORIGINAL
from application import test_typed_observations as measurement_tests
from application import test_protocols as protocol_tests
from application import test_co_report as co_tests
from claimbranch.application.canonical_share import prepare_share, verify_share, write_share, read_file, SELECTION_SCHEMA
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode, encode
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.cli import main

class CanonicalShareTests(unittest.TestCase):
    setUp = critique_tests.CritiqueTests.setUp
    def choose(self, *records, reasons=()):
        return dict(schema=SELECTION_SCHEMA, record_ids=list(records), reason_ids=list(reasons))
    def capture_critique(self, **changes):
        helper = critique_tests.CritiqueTests(); helper.project=self.project
        return helper.capture(**changes)
    def link_critique(self, project, **changes):
        return critique_tests.CritiqueTests().link(project, **changes)
    def save(self, project=None):
        with PersonalProjectStore.create(self.work, project_id=self.project.project_id) as store:
            store.save(project or self.project, preview=self.preview)
    def test_deterministic_opaque_selection_with_source_unknown_and_ai(self):
        before = self.project.payload
        a = prepare_share(self.project, self.choose('C', 'O'))
        self.assertEqual(a, prepare_share(self.project, self.choose('O', 'C')))
        self.assertTrue(verify_share(self.project, a)); self.assertEqual(before, self.project.payload)
        shared = decode(a, purpose='project')
        self.assertEqual(5, len(shared['records']))
        claim = next(r for r in shared['records'] if r['kind']=='claim' and r['content'].get('role')=='main')
        self.assertEqual(['ai'], claim['content']['origins']); self.assertGreater(claim['content']['unresolved_source_fields'], 0)
        observation = next(r for r in shared['records'] if r['kind']=='observation')
        self.assertEqual(['unknown'], observation['content']['origins'])
        for record in shared['records']: self.assertRegex(record['id'], r'^record-[0-9a-f]{32}$')
        self.assertNotIn('source_pointer', a.decode()); self.assertNotIn('source_ref', a.decode())
    def test_malformed_unknown_empty_duplicate_and_reason_outside_closure_refuse(self):
        for choice in ({}, self.choose(), self.choose('missing'), self.choose('C', 'C'), {**self.choose('C'), 'all': True}, self.choose('C', reasons=['X']), self.choose('C', reasons=['C'])):
            with self.subTest(choice=choice), self.assertRaises(ContractError): prepare_share(self.project, choice)
    def test_tampering_policy_selection_output_extra_field_and_stale_source_refuse(self):
        raw=prepare_share(self.project,self.choose('C'))
        for mutate in (lambda x:x.update(policy='other'),lambda x:x['selection']['record_ids'].append('record-'+'0'*32),lambda x:x['records'][0]['content'].update(statement='changed'),lambda x:x.update(extra='private'),lambda x:x.update(private_revision_commitment='0'*64)):
            v=decode(raw,purpose='project');mutate(v)
            with self.assertRaises(ContractError):verify_share(self.project,encode(v,purpose='project'))
        changed,_=self.capture_critique()
        with self.assertRaises(ContractError):verify_share(changed,raw)
        with self.assertRaises(ContractError):verify_share(self.project,raw+b'\n')
    def test_critique_dependencies_are_resolvable_but_private_copies_omitted(self):
        p,_=self.capture_critique( question=SECRET+' '+ORIGINAL)
        p,_=self.link_critique(p,rationale=SECRET+' '+ORIGINAL)
        raw=prepare_share(p,self.choose('C'));v=decode(raw,purpose='project')
        self.assertTrue(verify_share(p,raw));self.assertNotIn(SECRET,raw.decode());self.assertNotIn(ORIGINAL,raw.decode())
        self.assertNotIn('/private/confidential',raw.decode());self.assertNotIn('source_sha256',raw.decode())
        ids={r['id'] for r in v['records']}
        links=[r for r in v['records'] if r['kind']=='critique-reference'];self.assertEqual(1,len(links))
        for r in links:self.assertIn(r['content']['source_id'],ids);self.assertIn(r['content']['target_id'],ids)
        with self.assertRaises(ContractError):prepare_share(p,self.choose(critique_tests.CritiqueTests.key(self,p)))
    def test_known_private_literal_in_explicit_science_is_refused(self):
        p,_=self.capture_critique( private_identity='rubric')
        with self.assertRaisesRegex(ContractError,'known private'):prepare_share(p,self.choose('C'))
    def test_reason_opt_in_and_companion_closure(self):
        from application import test_claim_wording as wording_tests
        p,_=wording_tests.ClaimWordingTests.policy(self);p,_=wording_tests.ClaimWordingTests.companion(self,p)
        raw=prepare_share(p,self.choose('C'));v=decode(raw,purpose='project')
        self.assertTrue(any(r['kind']=='reporting-companion' for r in v['records']))
        self.assertTrue(any(r['kind']=='observation' for r in v['records']))
        self.assertNotIn('reason', {k for r in v['records'] for k in r})
        with_reasons=prepare_share(p,self.choose('C',reasons=['C','co-report']))
        self.assertIn('support does not justify stronger wording',with_reasons.decode());self.assertTrue(verify_share(p,with_reasons))
    def test_measurement_exact_values_and_scoped_indices_without_cell_identifiers(self):
        p=measurement_tests.TypedObservationTests.measured(self);raw=prepare_share(p,self.choose('O'));v=decode(raw,purpose='project')
        measurement=next(r['content']['measurement'] for r in v['records'] if r['kind']=='observation')
        self.assertEqual(18,len(measurement['rows']));self.assertEqual(54,sum(len(r['cells']) for r in measurement['rows']))
        self.assertEqual('0.123456789012345678901234567890',measurement['rows'][0]['cells'][0]['value']['value'])
        self.assertNotIn('primary-low-s1-direct',raw.decode());self.assertFalse(measurement['condition_labels_omitted']);self.assertEqual('model',measurement['conditions'][0]['condition_label']);self.assertEqual('M1',measurement['conditions'][0]['value_label']);self.assertTrue(verify_share(p,raw))
    # Fixture helper methods consumed by other owned scenario builders.
    base=measurement_tests.TypedObservationTests.base
    declaration=measurement_tests.TypedObservationTests.declaration
    request=measurement_tests.TypedObservationTests.request
    table=measurement_tests.TypedObservationTests.table
    def test_protocol_registration_failures_and_rule_amendments_remain_distinct(self):
        scenario=protocol_tests.ProtocolTests();scenario.setUp();self.addCleanup(scenario.doCleanups)
        p,_=scenario.gate(scenario.associated());p,_=scenario.outcome(p,classification='stopped-at-gate',gate_result_ids=['gate-result'])
        raw=prepare_share(p,self.choose('O'));v=decode(raw,purpose='project')
        self.assertTrue({'protocol','registered-gate','protocol-experiment','gate-result','outcome'}<={r['kind'] for r in v['records']})
        outcome=next(r for r in v['records'] if r['kind']=='outcome')
        self.assertEqual('failed-gate',outcome['content']['gate_validity']);self.assertFalse(outcome['content']['validity_verified'])
        self.assertNotIn('source_context',raw.decode());self.assertNotIn('expected_plan_digest',raw.decode());self.assertTrue(verify_share(p,raw))
    def test_existing_and_symlink_destinations_and_stale_review_preserve_files(self):
        raw=prepare_share(self.project,self.choose('C'));path=self.paper/'share.json';path.write_bytes(b'edited')
        with self.assertRaises(ContractError):write_share(path,raw,recheck=lambda:None)
        self.assertEqual(b'edited',path.read_bytes());link=self.paper/'link.json';link.symlink_to(path)
        with self.assertRaises(ContractError):write_share(link,raw,recheck=lambda:None)
        with self.assertRaises(OSError):read_file(link)
        target=self.paper/'new.json'
        def stale():raise ContractError('stale')
        with self.assertRaises(ContractError):write_share(target,raw,recheck=stale)
        self.assertFalse(target.exists());self.assertEqual([],list(self.paper.glob('.claimbranch-share-*')))
    def test_new_git_destination_and_missing_parent_write_no_private_state(self):
        raw=prepare_share(self.project,self.choose('C'));path=self.paper/'share.json';before=self.project.payload
        write_share(path,raw,recheck=lambda:None);self.assertEqual(raw,read_file(path));self.assertTrue(verify_share(self.project,read_file(path)))
        self.assertEqual(before,self.project.payload)
        with self.assertRaises(ContractError):write_share(self.paper/'missing'/'share.json',raw,recheck=lambda:None)
    def test_cli_exact_preview_cancel_confirm_and_verify(self):
        self.save();path=self.root/'selection.json';path.write_text(json.dumps(self.choose('C')));output=self.paper/'argument.json';saved=(self.work/'personal.cbp').read_bytes()
        args=['project','export','--directory',str(self.work),'--canonical','--selection',str(path),'--output',str(output)]
        with patch('sys.stdout',new_callable=io.StringIO) as out:self.assertEqual(0,main(args+['--dry-run']))
        self.assertFalse(output.exists());self.assertIn('required dependencies',out.getvalue());self.assertEqual(saved,(self.work/'personal.cbp').read_bytes())
        def cancel(prompt):return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=cancel),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertFalse(output.exists())
        def confirm(prompt):return 'export' if prompt.startswith('Type export') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=confirm),patch('builtins.print'):self.assertEqual(0,main(args))
        with patch('builtins.print'):self.assertEqual(0,main(['project','verify-export','--directory',str(self.work),'--input',str(output)]))
        self.assertEqual(saved,(self.work/'personal.cbp').read_bytes());output.write_bytes(b'edited')
        with patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','verify-export','--directory',str(self.work),'--input',str(output)]))
    def test_selection_change_after_confirmation_prevents_publication(self):
        self.save();path=self.root/'selection.json';path.write_text(json.dumps(self.choose('C')));output=self.paper/'argument.json'
        def confirm(prompt):
            if prompt.startswith('Type export'):path.write_text(json.dumps(self.choose('O')));return 'export'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=confirm),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):
            self.assertEqual(1,main(['project','export','--directory',str(self.work),'--canonical','--selection',str(path),'--output',str(output)]))
        self.assertFalse(output.exists())
    def test_selected_private_internal_identity_never_enters_output(self):
        from application.test_argument_import import fixture
        from claimbranch.core.argument_import import history_from_import
        from claimbranch.application.project_work import ProjectWork
        label='CONFIDENTIAL_REVIEWER_model_name_8431'
        def replace(value):
            if type(value) is str:return label if value=='C' else value
            if type(value) is list:return [replace(v) for v in value]
            if type(value) is dict:return {k:replace(v) for k,v in value.items()}
            return value
        value=replace(fixture())
        from claimbranch.core.paper_capacity import source_bytes,source_record
        original=json.loads(source_bytes(value['source']))
        value['source']=source_record(json.dumps(replace(original),ensure_ascii=False,indent=2).encode())
        raw=encode(value,purpose='project');h=history_from_import(raw,anchor_id='anchor')
        p=ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw)
        shared=prepare_share(p,self.choose(label));self.assertNotIn(label,shared.decode());self.assertTrue(verify_share(p,shared))
        self.assertEqual(shared,prepare_share(p,self.choose(label)))
    def test_selected_co_report_keeps_scopes_and_both_readings_with_origin(self):
        from claimbranch.application.co_report import prepare_co_report
        helper=co_tests.CoReportTests();helper.setUp();self.addCleanup(helper.doCleanups)
        p,_=prepare_co_report(helper.base(),helper.request());shared=prepare_share(p,self.choose('primary'))
        v=decode(shared,purpose='project');readings=[r for r in v['records'] if r['kind']=='interpretation'];self.assertEqual(2,len(readings))
        self.assertEqual({'Primary unit-level definition only','Grouped sensitivity definition only'},{r['content']['scope'] for r in readings})
        co=next(r for r in v['records'] if r['kind']=='co-report');self.assertTrue(any('unknown' in r['origins'] for r in co['content']['reading_origins']))
        self.assertNotIn('The sensitivity must accompany',shared.decode());self.assertTrue(verify_share(p,shared))
    def test_protocol_later_gate_change_does_not_hide_original_failure(self):
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups)
        p,_=helper.gate(helper.associated());p,_=helper.amendment(p)
        raw=prepare_share(p,self.choose('P'));v=decode(raw,purpose='project')
        amendment=next(r for r in v['records'] if r['kind']=='gate-amendment')
        self.assertEqual('after',amendment['content']['decided_after_result']);self.assertTrue(amendment['content']['app_result_precedes_amendment'])
        self.assertEqual('failed',next(r for r in v['records'] if r['kind']=='gate-result')['content']['status']);self.assertTrue(verify_share(p,raw))
    def test_registered_anchor_is_structure_without_text_or_path(self):
        from application.test_manuscript_anchors import ManuscriptAnchorTests
        p,_=ManuscriptAnchorTests.register(self,'figure',kind='figure',plots=('O',))
        raw=prepare_share(p,self.choose('figure'));v=decode(raw,purpose='project')
        anchor=next(r for r in v['records'] if r['kind']=='manuscript-anchor');self.assertEqual('omitted',anchor['content']['text']);self.assertTrue(anchor['content']['plots'])
        self.assertNotIn(str(self.paper),raw.decode());self.assertNotIn('Synthetic figure only',raw.decode());self.assertNotIn('block_digest',raw.decode())
    def test_parent_swap_after_preview_and_live_work_destination_refuse(self):
        self.save();sel=self.root/'selection.json';sel.write_bytes(encode(self.choose('C'),purpose='project'));folder=self.paper/'exports';folder.mkdir();output=folder/'share.json'
        def confirm(prompt):
            if prompt.startswith('Type export'):
                folder.rename(self.paper/'old-exports');folder.mkdir();return 'export'
            return ''
        args=['project','export','--directory',str(self.work),'--canonical','--selection',str(sel),'--output',str(output)]
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=confirm),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(args))
        self.assertFalse(output.exists());self.assertFalse((self.paper/'old-exports'/'share.json').exists())
        args[-1]=str(self.work/'share.json')
        with patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(args+['--dry-run']))
        self.assertFalse((self.work/'share.json').exists())
    def test_stale_saved_file_after_confirmation_refuses_and_preserves_external_bytes(self):
        self.save();sel=self.root/'selection.json';sel.write_bytes(encode(self.choose('C'),purpose='project'));output=self.paper/'share.json';checkpoint=self.work/'personal.cbp'
        def confirm(prompt):
            if prompt.startswith('Type export'):checkpoint.write_bytes(b'externally changed');return 'export'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=confirm),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','export','--directory',str(self.work),'--canonical','--selection',str(sel),'--output',str(output)]))
        self.assertFalse(output.exists());self.assertEqual(b'externally changed',checkpoint.read_bytes())
    def test_experiment_or_claim_selection_cannot_drop_protocol_failure(self):
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups)
        p,_=helper.gate(helper.associated())
        for key in ('X','T'):
            raw=prepare_share(p,self.choose(key));v=decode(raw,purpose='project')
            self.assertEqual('failed',next(r for r in v['records'] if r['kind']=='gate-result')['content']['status']);self.assertTrue(verify_share(p,raw))
    def test_reading_an_old_atime_file_and_control_preview(self):
        from claimbranch.application.canonical_share import display_json
        path=self.root/'old-input.json';path.write_bytes(b'{}');os.utime(path,(1,1))
        self.assertEqual(b'{}',read_file(path))
        text='Korean 한글 \u009b2J \u202e hidden';preview=display_json(dict(text=text))
        self.assertNotIn('\u009b',preview);self.assertNotIn('\u202e',preview);self.assertEqual(text,json.loads(preview)['text'])
    def test_failed_fsync_before_publication_keeps_no_output(self):
        output=self.paper/'share.json';raw=prepare_share(self.project,self.choose('C'))
        with patch('claimbranch.application.canonical_share.os.fsync',side_effect=OSError('synthetic disk full')):
            with self.assertRaises(OSError):write_share(output,raw,recheck=lambda:None)
        self.assertFalse(output.exists());self.assertEqual([],list(self.paper.glob('.claimbranch-share-*')))
    def test_actual_terminal_export_then_fresh_process_verification(self):
        import select,subprocess,sys,time,struct,fcntl,termios
        p,_=self.capture_critique(question=SECRET+' '+ORIGINAL);p,_=self.link_critique(p,rationale=SECRET+' '+ORIGINAL);self.save(p)
        choice=self.root/'selection.json';choice.write_bytes(encode(self.choose('C'),purpose='project'));output=self.paper/'argument.json';before=(self.work/'personal.cbp').read_bytes()
        master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
        args=[sys.executable,'-m','claimbranch','project','export','--directory',str(self.work),'--canonical','--selection',str(choice),'--output',str(output)]
        process=subprocess.Popen(args,stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'));os.close(slave)
        captured=b'';pending=b'';deadline=time.monotonic()+30
        try:
            while process.poll() is None and time.monotonic()<deadline:
                if select.select([master],[],[],0.1)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError:break
                    captured+=chunk;pending+=chunk
                    if b'Enter: next page' in pending:os.write(master,b'\n');pending=b''
                    elif b'Type export' in pending:os.write(master,b'export\n');pending=b''
            self.assertEqual(0,process.wait(timeout=5),captured[-2000:]);self.assertNotIn(SECRET.encode(),captured);self.assertNotIn(ORIGINAL.encode(),captured)
        finally:
            if process.poll() is None:process.kill();process.wait()
            os.close(master)
        verified=subprocess.run([sys.executable,'-m','claimbranch','project','verify-export','--directory',str(self.work),'--input',str(output)],capture_output=True,timeout=20)
        self.assertEqual(0,verified.returncode,verified.stderr);self.assertIn(b'Verified',verified.stdout);self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
    def test_large_paper_projection_references_and_deterministic_saved_ids(self):
        import time
        from application.paper_capacity_fixture import combined
        from claimbranch.core.research_history import ResearchHistory
        from claimbranch.application.project_work import ProjectWork
        seed,commands=combined(corrections=False,episodes=2)
        h=ResearchHistory(seed,commands);p=ProjectWork.create(PaperWork.create(h),self.preview)
        selected=[c['id'] for c in h.view('main')['claims']]
        started=time.monotonic();raw=prepare_share(p,self.choose(*selected));self.assertEqual(raw,prepare_share(p,self.choose(*reversed(selected))))
        self.assertLess(time.monotonic()-started,30);v=decode(raw,purpose='project');self.assertTrue(verify_share(p,raw))
        self.assertEqual(256,sum(r['kind']=='observation' for r in v['records']));self.assertEqual(512,sum(r['kind']=='scientific-edge' for r in v['records']))
        ids={r['id'] for r in v['records']}
        for r in v['records']:
            for key in ('source_id','target_id','experiment_id','claim_id'):
                if key in r['content']:self.assertIn(r['content'][key],ids)
    def test_private_literal_matching_is_case_and_unicode_normalization_aware(self):
        p,_=self.capture_critique(private_identity='RUBRIC')
        with self.assertRaisesRegex(ContractError,'known private'):prepare_share(p,self.choose('C'))
        from claimbranch.application.canonical_share import _check_known_private
        p,_=self.capture_critique(private_identity='Cafe\u0301')
        with self.assertRaisesRegex(ContractError,'known private'):_check_known_private(p,{'scientific_sentence':'CAFÉ is a private identity.'})
    def test_work_directory_case_alias_cannot_receive_public_output(self):
        self.save();path=self.root/'choice.json';path.write_bytes(encode(self.choose('C'),purpose='project'));alias=self.work.with_name('WORK')
        # Force only the lexical spelling to vary; an actual case-insensitive host
        # resolves it naturally. The identity guard is asserted directly on all hosts.
        from claimbranch.application.canonical_share import _parent
        info=os.stat(self.work)
        with self.assertRaises(ContractError):_parent(self.work/'share.json',forbidden_identity=(info.st_dev,info.st_ino))
        if alias.exists() and os.path.samefile(alias,self.work):
            with patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','export','--directory',str(self.work),'--canonical','--selection',str(path),'--output',str(alias/'share.json'),'--dry-run']))
        self.assertFalse((self.work/'share.json').exists())
    def test_selected_sensitivity_reading_also_retains_coreport_disposition(self):
        from claimbranch.application.co_report import prepare_co_report
        helper=co_tests.CoReportTests();helper.setUp();self.addCleanup(helper.doCleanups)
        p,_=prepare_co_report(helper.base(),helper.request());raw=prepare_share(p,self.choose('sensitivity'))
        v=decode(raw,purpose='project');self.assertEqual(2,sum(r['kind']=='interpretation' for r in v['records']));self.assertTrue(any(r['kind']=='co-report' for r in v['records']))
    def test_status_basis_interpretation_and_record_origin_are_preserved(self):
        from dataclasses import asdict
        from claimbranch.core.review import Judgment
        from claimbranch.application.project_work import ProjectWork
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups);p=helper.base();h=p.work.history
        judgment=Judgment.start(p.project_id,'protocol-episode').edit('A narrower synthetic conclusion.','Use an explicit interpretation basis.')
        def append(kind,payload,key):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=p.project_id,episode_id='protocol-episode',created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        append('create-reasoning-branch',{},'status-alt')
        changes=[dict(id='status-reading',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O'])),dict(id='status-change',kind='claim-status',body=dict(claim_id='T',status='supported',basis_ids=['status-reading']))]
        append('record-interpretation',dict(changes=changes,judgment=asdict(judgment)),'record-status')
        append('apply-selected-merge',dict(selected_ids=['status-change'],judgment=asdict(judgment),disposition='not-required',answers=[]),'merge-status')
        p=p.with_work(PaperWork.create(h));v=decode(prepare_share(p,self.choose('T')),purpose='project')
        claim=next(r for r in v['records'] if r['kind']=='claim');self.assertEqual('supported',claim['content']['status']);self.assertTrue(claim['content']['status_basis_ids'])
        self.assertTrue(any(r['id'] in claim['content']['status_basis_ids'] for r in v['records'] if r['kind']=='interpretation'))
    def test_unmerged_or_omitted_ai_status_cannot_change_main_claim_origin(self):
        from dataclasses import asdict
        from claimbranch.core.review import Judgment,Proposal
        helper=protocol_tests.ProtocolTests();helper.setUp();self.addCleanup(helper.doCleanups);p=helper.base();h=p.work.history
        judgment=Judgment.start(p.project_id,'protocol-episode').edit('A tentative reading.','Review the alternative only.').use_proposal(Proposal('owned-proposal',p.project_id,'protocol-episode','A tentative AI reading.','0'*64)).edit('A tentative AI reading.','An explicit human reason retains source AI.')
        def append(kind,payload,key):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=p.project_id,episode_id='protocol-episode',created_at='2026-10-14T00:00:00Z',operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        append('create-reasoning-branch',{},'unused-alt')
        changes=[dict(id='unused-reading',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O'])),dict(id='unused-status',kind='claim-status',body=dict(claim_id='T',status='supported',basis_ids=['unused-reading']))]
        append('record-interpretation',dict(changes=changes,judgment=asdict(judgment)),'record-unused')
        for merged in (False,True):
            if merged:append('apply-selected-merge',dict(selected_ids=['unused-reading'],judgment=asdict(judgment),disposition='deferred',answers=[]),'merge-only-reading')
            shared=decode(prepare_share(p.with_work(PaperWork.create(h)),self.choose('T')),purpose='project')
            claim=next(r for r in shared['records'] if r['kind']=='claim');self.assertNotIn('ai',claim['content']['origins']);self.assertEqual(merged,claim['content']['branch_ai_context_present'])
            if merged:
                adopted=decode(prepare_share(p.with_work(PaperWork.create(h)),self.choose('unused-reading')),purpose='project')
                reading=next(r for r in adopted['records'] if r['kind']=='interpretation' and r['content']['statement']==judgment.text)
                self.assertIn('ai',reading['content']['origins'])
