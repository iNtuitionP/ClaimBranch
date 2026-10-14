from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned 18×3 tables, exact revisions, condition queries and private return."""
import hashlib
import io
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from application import test_claim_wording as prior
from claimbranch.application.typed_observations import prepare_measurement,recheck_measurement,condition_query,check_artifact
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.personal_project import PersonalProjectStore,MEASUREMENT_PERSONAL_MAGIC
from claimbranch.application.personal_archive import personal_backup,split_personal_backup,MEASUREMENT_BACKUP_MAGIC
from claimbranch.application.tui_project import project_workspace
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode

class TypedObservationTests(unittest.TestCase):
    setUp=prior.ClaimWordingTests.setUp

    def declaration(self,key,values,groups=()):
        return dict(schema='claimbranch.measurement-input/v1',operation_type='declare-condition',payload=dict(key=key,values=list(values),groups=list(groups),rationale='Explicit synthetic condition vocabulary.'))

    def base(self):
        result=self.project
        for key,values,groups in [('model',['M1','M2'],[]),('seed',['s1','s2','s3'],[]),('dose',['low','mid','high'],[dict(id='protocol-dose',ascending_values=['low','mid','high'])]),('leg',['primary','sensitivity'],[])]:
            result,_=prepare_measurement(result,self.declaration(key,values,groups))
        return result

    def table(self):
        return dict(id='measurement-1',estimand='Attribution fractions for each synthetic leg/dose/seed cell.',conditions=[dict(key='model',value='M1')],
            columns=[dict(id=key,name=key,type='decimal',raw_unit='fraction',display_unit='percent (display label only)') for key in ('direct','mediated','residual')],
            rows=[dict(id=f'{leg}-{dose}-{seed}',conditions=[dict(key='leg',value=leg),dict(key='dose',value=dose),dict(key='seed',value=seed)],
                cells=[dict(id=f'{leg}-{dose}-{seed}-{key}',column_id=key,value=dict(type='decimal',value='0.123456789012345678901234567890')) for key in ('direct','mediated','residual')])
                for leg in ('primary','sensitivity') for dose in ('low','mid','high') for seed in ('s1','s2','s3')],artifact_refs=[])

    def request(self,project,action='transform',**changes):
        observation=project.work.history.view('main')['evidence'][0]
        payload=dict(event_id='typed-event',target_id='O',run_id='X',expected_revision=observation['history'][-1]['event_id'],action=action,
            statement=observation['statement'],rationale='Preserve the synthetic source values exactly.',source_context='Owned synthetic source; not independently verified.',table=self.table(),corrections=[])
        payload.update(changes)
        return dict(schema='claimbranch.measurement-input/v1',operation_type='record-measurement',payload=payload)

    def measured(self):
        base=self.base();return prepare_measurement(base,self.request(base))[0]

    def test_18_by_3_exact_values_and_original_imported_origin_are_global(self):
        base=self.base();result,preview=prepare_measurement(base,self.request(base));e=result.work.history.view('main')['evidence'][0]
        self.assertEqual(18,len(e['measurement']['rows']));self.assertEqual(54,sum(len(r['cells']) for r in e['measurement']['rows']))
        self.assertEqual('0.123456789012345678901234567890',e['measurement']['rows'][0]['cells'][0]['value']['value'])
        self.assertEqual('import',e['history'][0]['action']);self.assertFalse(e['artifact_fidelity_verified'])
        self.assertEqual(base.work.history.commands,result.work.history.commands[:-1]);self.assertEqual(base.work.history.seed,result.work.history.seed)
        self.assertEqual(base.work.history.view('main')['claims'],result.work.history.view('main')['claims'])
        self.assertEqual('claimbranch.project-work/v18',decode(result.payload,purpose='project')['schema'])
        app=project_workspace(result);app.select('O');self.assertIn('EXACT MEASUREMENT TABLE',str(app.detail()));self.assertIn('unknown',str(app.detail()).lower())
        self.assertEqual('measurement-1',next(n for n in preview['after']['nodes'] if n['id']=='O')['content']['measurement']['id'])

    def test_cell_correction_preserves_others_and_history_and_refuses_stale_revision(self):
        base=self.measured();before=base.work.history.view('main')['evidence'][0];cell=before['measurement']['rows'][0]['cells'][0]['id']
        request=self.request(base,'correct-cells',event_id='correction',table=None,corrections=[dict(cell_id=cell,value=dict(type='decimal',value='0.25'))])
        corrected,_=prepare_measurement(base,request);after=corrected.work.history.view('main')['evidence'][0]
        self.assertEqual('0.25',after['measurement']['rows'][0]['cells'][0]['value']['value'])
        self.assertEqual(before['measurement']['rows'][1:],after['measurement']['rows'][1:]);self.assertEqual(before['measurement'],after['history'][-2]['measurement'])
        request['payload']['event_id']='stale'
        with self.assertRaisesRegex(ContractError,'Stale measurement'):prepare_measurement(corrected,request)
        self.assertEqual(before,base.work.history.view('main')['evidence'][0])

    def test_units_estimand_conditions_require_explicit_transition_not_cell_edit(self):
        base=self.measured();request=self.request(base,'correct-cells',event_id='wrong',corrections=[dict(cell_id='primary-low-s1-direct',value=dict(type='decimal',value='1'))])
        with self.assertRaises(ContractError):prepare_measurement(base,request)
        table=self.table();table['id']='measurement-2';table['estimand']='New grouped estimand';table['columns'][0]['raw_unit']='percentage-points';table['conditions'][0]['value']='M2'
        for row in table['rows']:
            for cell in row['cells']:cell['id']='new-'+cell['id']
        transitioned,_=prepare_measurement(base,self.request(base,'transition',event_id='transition',table=table))
        e=transitioned.work.history.view('main')['evidence'][0];self.assertEqual('New grouped estimand',e['measurement']['estimand']);self.assertEqual('transition',e['history'][-1]['measurement_action'])
        self.assertEqual('measurement-1',e['history'][-2]['measurement']['id'])
        with self.assertRaises(ContractError):prepare_measurement(base,self.request(base,'transition',event_id='no-new-id'))

    def test_legacy_text_correction_cannot_erase_table_but_invalidation_keeps_it(self):
        base=self.measured();h=base.work.history;before=h.view('main')['evidence'][0]
        command=dict(schema_version=5,id='generic',project_id=base.project_id,episode_id='local',created_at=decode(h.commands[-1],purpose='history')['created_at'],
            operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='generic-event',target_id='O',run_id='X',action='correct',statement='Replace with text',value='bad',rationale='Test refusal',supersedes_id='typed-event'))
        with self.assertRaisesRegex(ContractError,'Structured observations'):h.append(command)
        command['payload'].update(action='invalidate',statement=None,value=None)
        changed=h.append(command);e=changed.view('main')['evidence'][0];self.assertEqual(before['measurement'],e['measurement']);self.assertEqual('invalidated',e['status'])
        with self.assertRaisesRegex(ContractError,'Inactive'):prepare_measurement(base.with_work(PaperWork.create(changed)),self.request(base.with_work(PaperWork.create(changed)),'transition',event_id='revive',table={**self.table(),'id':'new-table'}))

    def test_condition_query_declared_maximum_filters_rows_and_preserves_scope(self):
        base=self.measured();h=base.work.history;original=h.manifest();result=condition_query(h,'C',[dict(key='dose',group='protocol-dose',extreme='maximum'),dict(key='model',value='M1')])
        self.assertEqual({'dose':'high','model':'M1'},result['resolved_conditions']);self.assertEqual(6,len(result['observations'][0]['rows']))
        self.assertEqual(['high'],result['condition_coverage']['dose']);self.assertFalse(result['claim_scope_changed']);self.assertEqual(original,h.manifest())
        self.assertEqual(1,len([n for n in result['graph']['nodes'] if n['id']=='O']))
        with self.assertRaises(ContractError):condition_query(h,'C',[dict(key='dose',group='unknown',extreme='maximum')])
        with self.assertRaises(ContractError):condition_query(h,'C',[dict(key='dose',value='max')])

    def test_type_missingness_duplicates_unknown_tags_and_capacity_refuse_without_append(self):
        base=self.base();original=base.payload
        table=self.table();table['rows'][0]['cells'][0]['value']=dict(type='missing',reason='Not measured')
        good,_=prepare_measurement(base,self.request(base,table=table));self.assertEqual('missing',good.work.history.view('main')['evidence'][0]['measurement']['rows'][0]['cells'][0]['value']['type'])
        for mutate in (lambda t:t['rows'][0]['cells'][0].update(value=dict(type='integer',value='1')),lambda t:t['rows'][1].update(id=t['rows'][0]['id']),lambda t:t['rows'][1]['cells'][0].update(id=t['rows'][0]['cells'][0]['id']),lambda t:t['conditions'][0].update(value='unknown'),lambda t:t['rows'][0]['cells'].pop(),lambda t:t['rows'][0]['cells'][0].update(value=dict(type='decimal',value='NaN'))):
            invalid=self.table();mutate(invalid)
            with self.assertRaises(ContractError):prepare_measurement(base,self.request(base,table=invalid))
        huge=self.table();huge['rows']=[deepcopy(huge['rows'][0]) for _ in range(257)]
        with self.assertRaises(ContractError):prepare_measurement(base,self.request(base,table=huge))
        self.assertEqual(original,base.payload)

    def test_condition_vocabulary_immutable_invalid_group_and_budget(self):
        base=self.base()
        with self.assertRaisesRegex(ContractError,'immutable'):prepare_measurement(base,self.declaration('dose',['new']))
        with self.assertRaises(ContractError):prepare_measurement(base,self.declaration('setting',['a'],[dict(id='group',ascending_values=['missing'])]))
        self.assertEqual(4,base.work.history.capacity()['resources']['condition_vocabulary']['used'])

    def test_artifact_hash_pointer_value_missing_and_symlink_are_read_only(self):
        base=self.base();path=self.root/'artifact.json';raw=b'{"values":[0.123456789012345678901234567890]}';path.write_bytes(raw)
        table=self.table();table['artifact_refs']=[dict(id='artifact',path='declared/result.json',sha256=hashlib.sha256(raw).hexdigest(),json_pointer='/values/0',tool_sha256=None,commit=None)]
        result,_=prepare_measurement(base,self.request(base,table=table));h=result.work.history;original=h.manifest()
        check=check_artifact(h,'O','artifact',path,'primary-low-s1-direct');self.assertEqual('hash-and-cell-match',check['status']);self.assertFalse(check['scientific_validity_verified'])
        path.write_bytes(raw+b' ');self.assertEqual('hash-mismatch',check_artifact(h,'O','artifact',path,'primary-low-s1-direct')['status'])
        link=self.root/'link.json';link.symlink_to(path);self.assertEqual('unavailable-or-unsupported',check_artifact(h,'O','artifact',link,'primary-low-s1-direct')['status'])
        path.unlink();self.assertEqual('unavailable-or-unsupported',check_artifact(h,'O','artifact',path,'primary-low-s1-direct')['status']);self.assertEqual(original,h.manifest())

    def test_save_restart_backup_retains_original_notes_and_typed_history(self):
        from claimbranch.application.tui_work_recovery import snapshot_value
        base=self.base();app=project_workspace(base);app.select('C');app.notes[app.context_key()]='Preserve the original limitation.'
        base=base.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)));result,_=prepare_measurement(base,self.request(base))
        with PersonalProjectStore.create(self.work,project_id=result.project_id) as store:
            store.save(result,preview=self.preview);self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC));backup=store.backup()
        self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC));returned=split_personal_backup(backup);self.assertEqual(result.payload,returned.payload)
        app=project_workspace(returned);self.assertIn('Preserve the original limitation.',app.notes.values());app.select('O');self.assertIn('0.123456789',str(app.detail()))
        with PersonalProjectStore(self.work) as store:self.assertEqual(result.payload,store.load().payload)

    def test_cli_preview_cancel_changed_input_confirm_and_condition_query(self):
        from claimbranch.application.cli import main
        base=self.base();path=self.root/'measurement.json';path.write_bytes(encode(self.request(base),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        args=['project','measurement','--directory',str(self.work),'--input',str(path)];before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(args+['--dry-run']))
        self.assertIn('raw_unit',output.getvalue());self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value='q'),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def answer(prompt):return 'record' if prompt.startswith('Type record') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):self.assertEqual(0,main(args))
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','observations','--directory',str(self.work),'--claim','C','--condition','dose=max','--group','dose=protocol-dose']))
        self.assertIn('high',output.getvalue())

    def test_fresh_manual_observation_uses_confirm_not_import_and_old_frames_refuse(self):
        from application import test_co_report as co
        base=co.CoReportTests.manual_base(self)
        base,_=prepare_measurement(base,self.declaration('model',['M1']))
        table=self.table();table['rows']=[dict(id='r',conditions=[],cells=[dict(id='cell-'+c['id'],column_id=c['id'],value=dict(type='decimal',value='0')) for c in table['columns']])]
        result,_=prepare_measurement(base,self.request(base,'confirm',target_id='O-new',expected_revision=None,table=table))
        e=next(e for e in result.work.history.view('main')['evidence'] if e['id']=='O-new');self.assertEqual('confirm',e['history'][0]['action'])
        from claimbranch.application.personal_project import _PersonalCodec,CO_REPORT_PERSONAL_MAGIC
        with self.assertRaisesRegex(ContractError,'mismatch'):_PersonalCodec().open(CO_REPORT_PERSONAL_MAGIC+result.payload)
        self.assertEqual('claimbranch.project-work/v18',decode(result.payload,purpose='project')['schema'])

    def test_integer_and_text_columns_and_retracted_history_are_exact(self):
        base=self.base();table=self.table();table['columns'][0]['type']='integer';table['columns'][1]['type']='text'
        for row in table['rows']:
            row['cells'][0]['value']=dict(type='integer',value='1234567890123456789012345678901234567890')
            row['cells'][1]['value']=dict(type='text',value='한글 조건별 결과')
        result,_=prepare_measurement(base,self.request(base,table=table));h=result.work.history
        self.assertIn('1234567890123456789012345678901234567890',h.manifest().decode())
        command=dict(schema_version=5,id='retract',project_id=result.project_id,episode_id='local',created_at=decode(h.commands[-1],purpose='history')['created_at'],operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,
            payload=dict(event_id='retracted',target_id='O',run_id='X',action='retract',statement=None,value=None,rationale='Withdraw the synthetic observation.',supersedes_id='typed-event'))
        withdrawn=h.append(command);query=condition_query(withdrawn,'C',[])
        self.assertEqual(['O'],query['inactive_basis_ids']);self.assertEqual([],query['observations']);self.assertIn('measurement',withdrawn.view('main')['evidence'][0])
        self.assertNotIn('O',{n['id'] for n in query['graph']['nodes']})

    def test_import_transform_leaves_unresolved_original_and_ai_influence_inspectable(self):
        base=self.base();before=base.work.history.view('main');result,_=prepare_measurement(base,self.request(base));after=result.work.history.view('main')
        self.assertEqual(before['imported_records'],after['imported_records']);self.assertEqual(before['unresolved_source_pointers'],after['unresolved_source_pointers'])
        self.assertEqual(before['import_source_digest'],after['import_source_digest']);self.assertEqual(before['evidence'][0]['imported_source'],after['evidence'][0]['imported_source'])
        self.assertEqual('transform',after['evidence'][0]['history'][-1]['measurement_action'])

    def test_table_budget_and_declaration_budget_name_limit_and_count(self):
        base=self.base();table=self.table()
        table['estimand']='x'*16384
        for row in table['rows']:
            for cell in row['cells']:cell['value']=dict(type='missing',reason='x'*16384)
        with self.assertRaisesRegex(ContractError,'measurement-table-bytes: .* / 262144'):prepare_measurement(base,self.request(base,table=table))
        for i in range(28):base,_=prepare_measurement(base,self.declaration('condition-'+str(i),['v']))
        with self.assertRaisesRegex(ContractError,'condition-keys: 33 / 32'):prepare_measurement(base,self.declaration('overflow',['v']))

    def test_changed_project_source_and_exact_input_refuse_save(self):
        from claimbranch.application.cli import main
        base=self.base();candidate,preview=prepare_measurement(base,self.request(base));recheck_measurement(base,preview)
        changed,_=prepare_measurement(base,self.declaration('setting',['S']))
        with self.assertRaisesRegex(ContractError,'changed'):recheck_measurement(changed,preview)
        path=self.root/'measurement.json';path.write_bytes(encode(self.request(base),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        before=(self.work/'personal.cbp').read_bytes()
        def answer(prompt):
            if prompt.startswith('Type record'):
                path.write_bytes(encode(self.request(base,event_id='changed'),purpose='project'));return 'record'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','measurement','--directory',str(self.work),'--input',str(path)]))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        (self.paper/'paper.tex').write_bytes(self.manuscript+b'% changed')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_measurement(base,preview)

    def test_malformed_cli_selector_is_handled_without_traceback(self):
        from claimbranch.application.cli import main
        base=self.measured()
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        with patch('sys.stderr',new_callable=io.StringIO) as output:self.assertEqual(1,main(['project','observations','--directory',str(self.work),'--claim','C','--condition','dose']))
        self.assertNotIn('Traceback',output.getvalue())

    def test_actual_pty_record_fresh_open_and_source_artifact_frame_refusal(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        base=self.base();path=self.root/'measurement.json';path.write_bytes(encode(self.request(base),purpose='project'));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        def terminal(arguments,record=False):
            master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
            process=subprocess.Popen([sys.executable,'-m','claimbranch',*arguments],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'));os.close(slave)
            output=b'';sent=0;quit_sent=False;deadline=time.monotonic()+30
            try:
                while process.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],0.1)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        output+=chunk
                        if record:
                            pages=output.count(b'Enter: next page / q: cancel: ')
                            while sent<pages:os.write(master,b'\n');sent+=1
                            if b'Type record' in output and sent<10000:os.write(master,b'record\n');sent=10000
                        elif not quit_sent and (b'CLAIM' in output or b'ClaimBranch' in output):
                            os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-1500:].decode(errors='replace'))
                self.assertNotIn(b'Traceback',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(['project','measurement','--directory',str(self.work),'--input',str(path)],True)
        with PersonalProjectStore(self.work) as store:
            project=store.load();self.assertEqual(18,len(project.work.history.view('main')['evidence'][0]['measurement']['rows']))
        terminal(['project','open','--directory',str(self.work)])
        from types import ModuleType
        old=subprocess.run(['/usr/bin/git','show','HEAD:claimbranch/application/personal_project.py'],capture_output=True,text=True,check=True).stdout
        module=ModuleType('claimbranch.application.measurement_old');module.__package__='claimbranch.application';exec(compile(old,'old-reader','exec'),module.__dict__)
        raw=(self.work/'personal.cbp').read_bytes()
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_transitions_cannot_reuse_old_cells_with_changed_meaning_or_after_retirement(self):
        base=self.measured();table=self.table();table['id']='measurement-2';table['columns'][0]['raw_unit']='g'
        with self.assertRaisesRegex(ContractError,'Stable cell identity'):prepare_measurement(base,self.request(base,'transition',event_id='transition-2',table=table))
        table=self.table();table['id']='measurement-2';table['rows']=table['rows'][1:]
        second,_=prepare_measurement(base,self.request(base,'transition',event_id='transition-2',table=table))
        table=self.table();table['id']='measurement-3';table['rows'][0]['conditions'][0]['value']='sensitivity'
        with self.assertRaisesRegex(ContractError,'Stable cell identity'):prepare_measurement(second,self.request(second,'transition',event_id='transition-3',table=table))

    def test_query_uses_interpretation_support_basis_with_one_global_observation_identity(self):
        from application import test_co_report as co
        base=co.CoReportTests.manual_base(self);base,_=prepare_measurement(base,self.declaration('model',['M1']))
        table=self.table();table['rows']=[dict(id='r',conditions=[],cells=[dict(id='cell-'+c['id'],column_id=c['id'],value=dict(type='decimal',value='0')) for c in table['columns']])]
        base,_=prepare_measurement(base,self.request(base,table=table));request=co.CoReportTests.request(self,disposition='deferred')
        for reading in request['candidates']:reading['claim_id']='T';reading['origin']='human'
        from claimbranch.application.co_report import prepare_co_report
        base,_=prepare_co_report(base,request);result=condition_query(base.work.history,'T',[dict(key='model',value='M1')])
        self.assertEqual(['O'],[r['observation_id'] for r in result['observations']]);self.assertEqual(1,len([n for n in result['graph']['nodes'] if n['id']=='O']))
        self.assertTrue(any(n['kind']=='interpretation' for n in result['graph']['nodes']))

    def test_artifact_changed_during_read_and_pointer_mismatch_keep_history_unchanged(self):
        import os
        base=self.base();path=self.root/'artifact-race.json';raw=b'{"values":[0.2]}';path.write_bytes(raw);table=self.table()
        table['artifact_refs']=[dict(id='artifact',path='result.json',sha256=hashlib.sha256(raw).hexdigest(),json_pointer='/values/0',tool_sha256=None,commit=None)]
        result,_=prepare_measurement(base,self.request(base,table=table));h=result.work.history;original=h.manifest()
        self.assertEqual('cell-mismatch',check_artifact(h,'O','artifact',path,'primary-low-s1-direct')['status'])
        reading=os.read;changed=False
        def raced(fd,size):
            nonlocal changed
            part=reading(fd,size)
            if part and not changed:path.write_bytes(raw+b' ');changed=True
            return part
        with patch('claimbranch.application.typed_observations.os.read',side_effect=raced):check=check_artifact(h,'O','artifact',path,'primary-low-s1-direct')
        self.assertEqual('unavailable-or-unsupported',check['status']);self.assertIn('changed during',check['reason']);self.assertEqual(original,h.manifest())

    def test_public_provider_attachment_refuses_before_profile_or_credential_access(self):
        from claimbranch.application.cli import main
        base=self.measured()
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('claimbranch.application.provider_commands.PersonalProviderConnection.__enter__',side_effect=AssertionError('Provider profile must not be opened')),patch('sys.stderr',new_callable=io.StringIO) as output:
            self.assertEqual(1,main(['project','open','--directory',str(self.work),'--provider-directory',str(self.root/'never-open')]))
        self.assertIn('not qualified',output.getvalue())

    def test_upper_cell_count_and_evidence_identity_limits(self):
        base=self.base();table=self.table();table['conditions']=[];table['columns']=[dict(id='c'+str(i),name='Term '+str(i),type='decimal',raw_unit='fraction',display_unit='fraction') for i in range(8)]
        table['rows']=[dict(id='r'+str(i),conditions=[],cells=[dict(id=f'x{i}-{j}',column_id='c'+str(j),value=dict(type='decimal',value='0')) for j in range(8)]) for i in range(256)]
        result,_=prepare_measurement(base,self.request(base,table=table));self.assertEqual(2048,sum(len(row['cells']) for row in result.work.history.view('main')['evidence'][0]['measurement']['rows']))
        table['columns'].append(dict(id='ninth',name='Extra term',type='decimal',raw_unit='fraction',display_unit='fraction'))
        for i,row in enumerate(table['rows']):row['cells'].append(dict(id=f'new{i}',column_id='ninth',value=dict(type='decimal',value='0')))
        with self.assertRaisesRegex(ContractError,'measurement-cells: 2304 / 2048'):prepare_measurement(base,self.request(base,table=table))
        request=self.request(base);request['payload']['table']['id']='C'
        with self.assertRaisesRegex(ContractError,'identity'):prepare_measurement(base,request)

    def test_public_backup_and_fresh_directory_restore_preserve_saved_tables(self):
        from claimbranch.application.cli import main
        base=self.measured()
        with PersonalProjectStore.create(self.work,project_id=base.project_id) as store:store.save(base,preview=self.preview)
        backup=self.root/'table-backup';restored=self.root/'table-restored';backup.mkdir(mode=0o700);restored.mkdir(mode=0o700)
        with patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(0,main(['project','backup','--directory',str(self.work),'--archive-directory',str(backup)]))
            self.assertEqual(0,main(['project','restore','--directory',str(restored),'--archive-directory',str(backup)]))
        with PersonalProjectStore(self.work) as original,PersonalProjectStore(restored) as returned:self.assertEqual(original.load().payload,returned.load().payload)
