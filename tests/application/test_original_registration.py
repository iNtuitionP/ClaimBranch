"""Exact prior tables enter once, retaining sources through personal save/return."""
from copy import deepcopy
import json
import unittest
from claimbranch.core.paper_capacity import encode,decode,source_record,source_bytes
from claimbranch.core.argument_import import history_from_import,_leaves
from claimbranch.core.canonical import ContractError
from .test_argument_import import fixture as scalar_fixture


def fixture():
    from .test_typed_observations import TypedObservationTests
    old=scalar_fixture();bodies=[deepcopy(record['body']) for record in old['records']]
    bodies[3].pop('value');bodies[3]['measurement']=TypedObservationTests().table()
    bodies[3]['measurement']['artifact_refs']=[dict(id='source-artifact',path='private/results.json',sha256='f'*64,json_pointer='/results',tool_sha256=None,commit=None)]
    raw=json.dumps(dict(entries=bodies),ensure_ascii=False,separators=(',',':')).encode()
    records=[]
    for index,original in enumerate(old['records']):
        record={key:deepcopy(original[key]) for key in ('id','kind','recorded_at','origin')}
        record['body']=bodies[index]
        mappings=[dict(target=target,file_id='ledger',locator=dict(kind='json-pointer',pointer=f'/entries/{index}'+target),normalization='literal-v1',transformation=None) for target,_ in _leaves(record['body'])]
        record['mappings']=[mappings[i:i+1024] for i in range(0,len(mappings),1024)];records.append(record)
    vocabulary=[dict(key=key,values=values,groups=[],rationale='Source taxonomy declared for this migration.') for key,values in [('model',['M1','M2']),('seed',['s1','s2','s3']),('dose',['low','mid','high']),('leg',['primary','sensitivity'])]]
    return dict(schema='claimbranch.argument-import/v2',profile='paper',project_id=old['project_id'],title=old['title'],
        files=[dict(id='ledger',name='results.json',media='json',source=source_record(raw))],
        condition_vocabulary=vocabulary,records=records,selected_ids=old['selected_ids'])


def history(value=None):
    h=history_from_import(encode(value or fixture(),purpose='project'),anchor_id='anchor',registered_at='2026-10-15T00:00:00Z')
    return h.append(dict(schema_version=14,id='open-local',project_id='synthetic-paper',episode_id='local',created_at='2026-10-15T00:00:00Z',operation_type='open-episode',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(title='Next question',question='Does the effect generalize?')))


class OriginalTableHistoryTests(unittest.TestCase):
    def test_one_import_is_historical_not_fresh_confirmation_and_replays(self):
        h=history();self.assertEqual(14,h.schema_version)
        self.assertEqual(1,len(h.commands));self.assertEqual(1,h.watermark)
        observation=h.view('main')['evidence'][0]
        self.assertEqual('import',observation['history'][0]['action']);self.assertEqual(54,sum(len(row['cells']) for row in observation['measurement']['rows']))
        self.assertFalse(observation['artifact_fidelity_verified'])
        self.assertEqual('private/results.json',observation['measurement']['artifact_refs'][0]['path'])
        self.assertEqual('f'*64,observation['measurement']['artifact_refs'][0]['sha256'])
        self.assertEqual('0.123456789012345678901234567890',observation['measurement']['rows'][0]['cells'][0]['value']['value'])
        self.assertEqual(h.manifest(),type(h)(h.seed,h.commands).manifest());self.assertFalse(h.authorization_verified)
        self.assertEqual(1,len(h.view('main')['historical_decisions']))

    def test_bad_cell_refuses_before_seed_or_commands(self):
        value=fixture();value['records'][3]['body']['measurement']['rows'][0]['cells'][0]['value']['value']='NaN'
        with self.assertRaises(ContractError):history(value)



    def test_legacy_reference_bytes_and_seed_command_discriminators_stay_fixed(self):
        from claimbranch.core.argument_import import source_references
        from claimbranch.core.research_history import _reduce,ResearchHistory
        old=history_from_import(encode(scalar_fixture(),purpose='project'),anchor_id='anchor');state=_reduce(old.seed,old.commands)
        refs=source_references(state,state['branches']['main'],[],'C')
        expected=[dict(record_id=key,source_sha256='05b8a0be2cce9f5edcef18df26dbfb55757c3a066e561bb4b4004bd8f54c1de3',contributor='ai' if key=='C' else 'unknown',unresolved_count=count) for key,count in [('C',1),('E',0),('O',2),('T',0),('X',0)]]
        self.assertEqual(encode(expected,purpose='history'),encode(refs,purpose='history'))
        from claimbranch.application.paper_service import PaperService
        opened_old=old.append(dict(schema_version=5,id='open-old',project_id='synthetic-paper',episode_id='local',created_at='2026-10-15T00:00:00Z',operation_type='open-episode',expected_heads=dict(old.heads),evidence_watermark=old.watermark,payload=dict(title='Next question',question='What is still unknown?')))
        legacy_mark=next(n for n in PaperService(opened_old).query('main')['nodes'] if n['id']=='C')['content']['imported_source']
        self.assertNotIn('origin_flags',legacy_mark);self.assertNotIn('source_digest_scope',legacy_mark)
        new=history();command=__import__('json').loads(new.commands[0]);command['schema_version']=5
        with self.assertRaises(ContractError):ResearchHistory(new.seed,(encode(command,purpose='history'),))
        command['schema_version']=14
        with self.assertRaises(ContractError):ResearchHistory(old.seed,(encode(command,purpose='history'),))

    def test_derived_column_binding_cannot_swap_scientific_variables(self):
        from claimbranch.core.argument_import_v2 import preview_import
        value=fixture();record=value['records'][3];row=record['body']['measurement']['rows'][0]
        row['cells'][0]['column_id'],row['cells'][1]['column_id']=row['cells'][1]['column_id'],row['cells'][0]['column_id']
        targets={'/measurement/rows/0/cells/0/column_id','/measurement/rows/0/cells/1/column_id'}
        for page in record['mappings']:
            for index,mapping in enumerate(page):
                if mapping['target'] in targets:page[index]=dict(target=mapping['target'],derived='structure-v1')
        result=preview_import(encode(value,purpose='project'));self.assertFalse(result['valid'])
        self.assertTrue(any('preserve declared column order' in item['error'] for item in result['errors']))

    def test_compound_human_unknown_is_retained_in_consequential_reference(self):
        from claimbranch.core.argument_import import source_references
        from claimbranch.core.research_history import _reduce
        value=fixture();record=value['records'][3];other=deepcopy(value['files'][0]);other['id']='ledger2';value['files'].append(other)
        record['mappings'][0][0]['file_id']='ledger2'
        record['source_origins']=[dict(file_id='ledger',origin=dict(contributor='human',detail=None)),dict(file_id='ledger2',origin=dict(contributor='unknown',detail=None))]
        record['joint_origin']=dict(contributor='unknown',detail='One source remains unknown.')
        h=history(value);mark=h.view('main')['evidence'][0]['imported_source']
        self.assertTrue(mark['origin_flags']['human']);self.assertTrue(mark['origin_flags']['unknown'])
        from claimbranch.application.paper_service import PaperService
        graph_mark=next(n for n in PaperService(h).query('main')['nodes'] if n['id']=='O')['content']['imported_source']
        self.assertEqual(mark['origin_flags'],graph_mark['origin_flags'])
        self.assertEqual('argument-envelope/v2',graph_mark['source_digest_scope'])
        from claimbranch.application.tui_model import TerminalWorkspace
        app=TerminalWorkspace(h,ai_off=True);app.select('O');rendered=str(app.detail())
        self.assertIn('RETAINED SOURCE INFLUENCE',rendered);self.assertIn('HUMAN, UNKNOWN',rendered)
        state=_reduce(h.seed,h.commands)
        refs=source_references(state,state['branches']['main'],[],'O')
        self.assertTrue(next(r for r in refs if r['record_id']=='O')['origin_flags']['unknown'])

    def test_extra_derived_cell_returns_diagnostics_instead_of_index_error(self):
        from claimbranch.core.argument_import_v2 import preview_import
        value=fixture();record=value['records'][3];row=record['body']['measurement']['rows'][0]
        row['cells'].append(dict(id='extra-cell',column_id='direct',value=dict(type='decimal',value='0.5')))
        for key in ('id','column_id'):
            record['mappings'][0].append(dict(target='/measurement/rows/0/cells/3/'+key,derived='structure-v1'))
        record['mappings'][0].append(dict(target='/measurement/rows/0/cells/3/value/type',file_id='ledger',locator=dict(kind='json-pointer',pointer='/entries/3/measurement/rows/0/cells/0/value/type'),normalization='literal-v1',transformation=None))
        record['mappings'][0].append(dict(target='/measurement/rows/0/cells/3/value/value',file_id='ledger',locator=dict(kind='json-pointer',pointer='/entries/3/measurement/rows/0/cells/0/value/value'),normalization='literal-v1',transformation='Changed source value'))
        result=preview_import(encode(value,purpose='project'));self.assertFalse(result['valid']);self.assertGreater(result['error_count'],0)
        self.assertTrue(any('no declared column' in e['error'] for e in result['errors']))

    def test_valid_mapping_preview_discloses_unstorable_input_before_registration(self):
        import random
        from claimbranch.core.argument_import_v2 import preview_import
        value=fixture();source=bytes(33+b%94 for b in random.Random(73).randbytes(3900000))
        value['files'].append(dict(id='unmapped-private',name='private-original.txt',media='text',source=source_record(source)))
        result=preview_import(encode(value,purpose='project'));self.assertTrue(result['valid']);self.assertFalse(result['registration_available'])
        self.assertIn('capacity',result['registration_failure'])


class OriginalSnapshotTests(unittest.TestCase):
    def test_bounded_snapshot_refuses_corruption_trailing_concatenation_and_expansion(self):
        import zlib
        from claimbranch.core.argument_import_v2 import pack_snapshot,unpack_snapshot
        raw=b'private synthetic bytes\r\n'*100
        value=pack_snapshot(raw);self.assertEqual(raw,unpack_snapshot(value))
        for changed in ({**value,'sha256':'0'*64},{**value,'bytes':len(raw)-1},{**value,'compressed':source_record(zlib.compress(raw)+b'x')},{**value,'compressed':source_record(zlib.compress(raw)*2)},{**value,'bytes':0},{**value,'compressed':source_record(b'bad')}):
            with self.assertRaises(ContractError):unpack_snapshot(changed)


class OriginalProjectTests(unittest.TestCase):
    def setUp(self):
        import tempfile,sys,subprocess
        from pathlib import Path
        from claimbranch.application.project_work import ProjectWork,preview_association
        from claimbranch.application.paper_work_store import PaperWork
        self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else None);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.paper=self.root/'paper';self.paper.mkdir();self.work=self.root/'work';self.work.mkdir(mode=0o700)
        subprocess.run(['/usr/bin/git','init','-q',str(self.paper)],check=True)
        self.manuscript=b'% claimbranch:start id=anchor\nSynthetic original table.\n% claimbranch:end id=anchor\n'
        (self.paper/'paper.tex').write_bytes(self.manuscript)
        self.raw=encode(fixture(),purpose='project');self.preview=preview_association(self.paper,'paper.tex','anchor',self.work)
        self.project=ProjectWork.create(PaperWork.create(history()),self.preview,import_input=self.raw)

    def test_single_pass_correction_private_source_writing_restart_backup_and_restore(self):
        from claimbranch.application.typed_observations import prepare_measurement,condition_query
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.personal_project import PersonalProjectStore,RETAINED_PERSONAL_MAGIC as ORIGINAL_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import split_personal_backup,RETAINED_BACKUP_MAGIC as ORIGINAL_BACKUP_MAGIC
        from claimbranch.core.argument_import_v2 import unpack_snapshot
        from claimbranch.core.paper_capacity import decode
        project=self.project;h=project.work.history;before=h.view('main')['evidence'][0]
        self.assertNotIn('value',before)
        self.assertEqual([],decode(project.payload,purpose='project')['sources'])
        self.assertEqual(1,len(condition_query(h,'C',[dict(key='dose',value='high')])['observations']))
        app=project_workspace(project);app.select('O');self.assertIn('EXACT MEASUREMENT TABLE',str(app.detail()))
        self.assertIn('json-pointer',app.imported_original_source('O'));app.notes[app.context_key()]='Preserve exact cells and original limits.'
        project=project.with_work(PaperWork.create(h,workspace=snapshot_value(app)))
        request=dict(schema='claimbranch.measurement-input/v1',operation_type='record-measurement',payload=dict(event_id='correct-cell',target_id='O',run_id='X',expected_revision=before['history'][0]['event_id'],action='correct-cells',statement=before['statement'],rationale='Checked a transcribed cell.',source_context='Synthetic test only.',table=None,corrections=[dict(cell_id='primary-low-s1-direct',value=dict(type='decimal',value='0.25'))]))
        corrected,_=prepare_measurement(project,request)
        after=corrected.work.history.view('main')['evidence'][0]
        self.assertEqual('0.25',after['measurement']['rows'][0]['cells'][0]['value']['value']);self.assertEqual(before['measurement'],after['history'][0]['measurement'])
        self.assertEqual(h.seed,corrected.work.history.seed)
        with self.assertRaises(ContractError):prepare_measurement(corrected,request)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);store.save(corrected);backup=store.backup()
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(ORIGINAL_PERSONAL_MAGIC));self.assertTrue(backup.startswith(ORIGINAL_BACKUP_MAGIC))
        returned=split_personal_backup(backup);self.assertEqual(corrected.payload,returned.payload)
        destination=self.root/'restored';destination.mkdir(mode=0o700);PersonalProjectStore.restore_backup(backup,destination)
        with PersonalProjectStore(destination) as store:
            reopened=store.load();self.assertEqual(corrected.payload,reopened.payload)
            self.assertEqual(self.raw,unpack_snapshot(decode(reopened.work.history.seed,purpose='history')['initial_argument']['snapshot']))
            self.assertIn('Preserve exact cells and original limits.',project_workspace(reopened).notes.values())
        self.assertEqual(self.manuscript,(self.paper/'paper.tex').read_bytes())
        self.assertFalse(reopened.work.history.authorization_verified)

    def test_public_registration_cancel_changed_source_interrupt_confirm_and_duplicate(self):
        from .test_argument_registration import ImportedProjectTests
        run=lambda **kw:ImportedProjectTests.run_import(self,**kw)
        self.assertEqual(0,run(answer='')[0]);self.assertFalse((self.work/'personal.cbp').exists())
        self.assertEqual(1,run(mutate=lambda p:p.write_bytes(p.read_bytes()+b' '))[0]);self.assertFalse((self.work/'personal.cbp').exists())
        for stage in ('page','final'):
            self.assertEqual(130,run(interrupt=(stage,KeyboardInterrupt))[0]);self.assertFalse((self.work/'personal.cbp').exists())
        code,out,error=run();self.assertEqual(0,code,error);self.assertIn('argument saved',out)
        saved=(self.work/'personal.cbp').read_bytes();self.assertEqual(1,run()[0]);self.assertEqual(saved,(self.work/'personal.cbp').read_bytes())

    def test_selected_share_omits_raw_sources_and_provider_refuses(self):
        from claimbranch.application.paper_service import PaperService
        with self.assertRaisesRegex(ContractError,'Imported-origin provider context'):PaperService(self.project.work.history).compile_context({})
        # Exercise the ordinary selected-public projection, never the private snapshot.
        from claimbranch.application.canonical_share import prepare_share,verify_share,SELECTION_SCHEMA
        shared=prepare_share(self.project,dict(schema=SELECTION_SCHEMA,record_ids=['C','O'],reason_ids=[]))
        self.assertTrue(verify_share(self.project,shared))
        for secret in ('snapshot','source_pointer','json-pointer','results.json','recorded_at','joint_origin','source_origins','chunks','/entries/'):
            self.assertNotIn(secret,shared.decode())

    def test_table_only_graph_renders_wide_narrow_and_actual_terminal_return(self):
        from .test_tui_terminal import TerminalProcessTests
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui import render_snapshot
        app=project_workspace(self.project);app.select('O')
        for width,height in ((140,40),(80,24)):
            self.assertIn('GRAPH',render_snapshot(app,width=width,height=height))
        project=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        terminal=TerminalProcessTests();terminal.setUp();self.addCleanup(terminal.tearDown)
        terminal.launch(personal_arguments=['open','--directory',str(self.work)])
        terminal.expect('ARGUMENT GRAPH');terminal.resize(80,24);terminal.send('\x0c','PERSONAL');terminal.send('q');terminal.assert_restored(0)
        with PersonalProjectStore(self.work) as store:self.assertEqual(project.work.history.manifest(),store.load().work.history.manifest())

    def test_new_reasoning_preserves_imported_basis_and_returns_without_fake_owned_ai(self):
        from .test_argument_registration import ImportedProjectTests
        ImportedProjectTests.test_new_reasoning_records_imported_basis_without_fake_owned_ai_and_survives_return(self)
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.core.research_history import ResearchHistory
        from claimbranch.core.paper_capacity import decode
        with PersonalProjectStore(self.work) as store:h=store.load().work.history
        commands=[decode(c,purpose='history') for c in h.commands]
        index=next(i for i,c in enumerate(commands) if c['operation_type']=='record-imported-interpretation')
        ref=commands[index]['payload']['source_refs'][0]
        self.assertEqual({'record_id','source_sha256','contributor','unresolved_count','schema','source_digest_scope','origin_flags'},set(ref))
        self.assertEqual('claimbranch.imported-source-reference/v2',ref['schema']);self.assertEqual('argument-envelope/v2',ref['source_digest_scope'])
        for mutate in (lambda r:r.pop('source_digest_scope'),lambda r:r['origin_flags'].update(ai=not r['origin_flags']['ai']),lambda r:r.pop('origin_flags')):
            changed=deepcopy(commands);mutate(changed[index]['payload']['source_refs'][0])
            with self.assertRaises(ContractError):ResearchHistory(h.seed,tuple(encode(c,purpose='history') for c in changed))

    def test_actual_terminal_registers_exact_table_once_before_saved_open(self):
        import os,select,struct,fcntl,termios,subprocess,sys,time
        from claimbranch.application.personal_project import PersonalProjectStore
        path=self.root/'argument.json';path.write_bytes(self.raw);path.chmod(0o600)
        master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
        process=subprocess.Popen([sys.executable,'-m','claimbranch','project','import-argument','--input',str(path),'--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex','--question','What should be tested next?'],stdin=slave,stdout=slave,stderr=slave,env={**os.environ,'TERM':'xterm-256color'})
        os.close(slave);pending=b'';tail=b'';deadline=time.monotonic()+45
        try:
            while process.poll() is None and time.monotonic()<deadline:
                if not select.select([master],[],[],0.1)[0]:continue
                try:chunk=os.read(master,65536)
                except OSError:break
                pending+=chunk;tail=(tail+chunk)[-8192:]
                if b'Review: details / continue to confirmation / cancel:' in pending:os.write(master,b'continue\n');pending=b''
                elif b'Type import to register' in pending:os.write(master,b'import\n');pending=b''
            self.assertEqual(0,process.wait(timeout=5),tail.decode(errors='replace'));self.assertIn(b'Imported personal argument saved',tail)
        finally:
            if process.poll() is None:process.kill();process.wait()
            os.close(master)
        with PersonalProjectStore(self.work) as store:
            h=store.load().work.history;self.assertEqual(14,h.schema_version);self.assertEqual(1,len(h.commands));self.assertEqual(54,sum(len(r['cells']) for r in h.view('main')['evidence'][0]['measurement']['rows']))

    def test_private_science_cannot_be_rebound_to_different_input_or_frame(self):
        from claimbranch.application.project_work import ProjectWork
        from claimbranch.application.personal_project import _PersonalCodec,EDIT_PERSONAL_MAGIC
        from claimbranch.core.paper_capacity import decode
        from claimbranch.core.research_history import ResearchHistory
        seed=decode(self.project.work.history.seed,purpose='history');seed['initial_argument']['records'][1]['body']['statement']='Fabricated'
        with self.assertRaises(ContractError):ResearchHistory(encode(seed,purpose='history'))
        value=decode(self.project.payload,purpose='project');value['import_input_sha256']='0'*64
        with self.assertRaises(ContractError):ProjectWork(encode(value,purpose='project'))
        with self.assertRaisesRegex(ContractError,'frame/profile'):_PersonalCodec().open(EDIT_PERSONAL_MAGIC+self.project.payload)
        with self.assertRaises(ContractError):ProjectWork.create(self.project.work,self.preview,import_input=self.raw+b' ')


def source_v3_fixture():
    value=fixture();value['schema']='claimbranch.argument-import/v3'
    table=value['records'][3]['body']['measurement'];table['rows'][0]['cells'][0]['value']['value']='0.0108'
    original=json.loads(source_bytes(value['files'][0]['source']))
    original['entries'][3]['measurement']=deepcopy(table)
    source=json.dumps(original,ensure_ascii=False,separators=(',',':')).encode().replace(b'"0.0108"',b'0.0108',1)
    value['files'][0]['source']=source_record(source)
    for page in value['records'][3]['mappings']:
        for mapping in page:
            if mapping['target']=='/measurement/rows/0/cells/0/value/value':mapping['normalization']='json-number-decimal-v1'
    return value


class SourceV3ProjectTests(unittest.TestCase):
    setUp=OriginalProjectTests.setUp

    def v3(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        raw=encode(source_v3_fixture(),purpose='project')
        h=history(source_v3_fixture())
        return ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw),raw

    def test_new_source_preview_save_reopen_backup_and_source_reader(self):
        from claimbranch.application.personal_project import PersonalProjectStore,SOURCE_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import SOURCE_BACKUP_MAGIC,split_personal_backup
        from claimbranch.application.paper_storage_codec import decode
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.core.argument_import_v2 import unpack_snapshot
        project,raw=self.v3()
        self.assertEqual('claimbranch.project-work/v25',decode(project.payload)['schema'])
        self.assertEqual('claimbranch.paper-work/v29',decode(project.work.payload)['schema'])
        self.assertEqual(raw,unpack_snapshot(json.loads(project.work.history.seed)['initial_argument']['snapshot']))
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);backup=store.backup()
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(SOURCE_PERSONAL_MAGIC))
        self.assertTrue(backup.startswith(SOURCE_BACKUP_MAGIC));self.assertEqual(project.payload,split_personal_backup(backup).payload)
        destination=self.root/'new-v3';destination.mkdir(mode=0o700)
        PersonalProjectStore.restore_backup(backup,destination)
        with PersonalProjectStore(destination) as store:returned=store.load()
        self.assertEqual(project.payload,returned.payload);self.assertEqual(project.work.history.manifest(),returned.work.history.manifest())
        app=project_workspace(returned)
        self.assertEqual('0.0108',returned.work.history.view('main')['evidence'][0]['measurement']['rows'][0]['cells'][0]['value']['value'])
        self.assertFalse(returned.work.history.authorization_verified)
        self.assertIn('json-number-decimal-v1',app.imported_original_source('O'))
        self.assertIn('normalized-exact',app.imported_original_source('O'))
        self.assertEqual(self.manuscript,(self.paper/'paper.tex').read_bytes())

    def test_new_source_cannot_hide_inside_legacy_work_project_or_frame(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        from claimbranch.application.paper_storage_codec import decode,encode as store_encode
        from claimbranch.application.personal_project import _PersonalCodec,CONDITIONAL_PERSONAL_MAGIC,SOURCE_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup,CONDITIONAL_BACKUP_MAGIC
        project,_=self.v3();work=decode(project.work.payload)
        for version in (25,26,27,28):
            changed=deepcopy(work);changed['schema']=f'claimbranch.paper-work/v{version}'
            with self.subTest(work=version),self.assertRaises(ContractError):PaperWork(store_encode(changed))
        changed=decode(project.payload);changed['schema']='claimbranch.project-work/v24'
        with self.assertRaises(ContractError):ProjectWork(store_encode(changed))
        old=decode(self.project.work.payload);old['schema']='claimbranch.paper-work/v29'
        with self.assertRaises(ContractError):PaperWork(store_encode(old))
        checkpoint=_PersonalCodec().seal(project.payload)
        with self.assertRaises(ContractError):_PersonalCodec().open(CONDITIONAL_PERSONAL_MAGIC+checkpoint[len(SOURCE_PERSONAL_MAGIC):])
        backup=personal_backup(project)
        with self.assertRaises(ContractError):split_personal_backup(CONDITIONAL_BACKUP_MAGIC+backup[len(CONDITIONAL_BACKUP_MAGIC):])

    def test_shared_audit_and_new_label_commands_keep_new_source_format(self):
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.paper_storage_codec import decode
        from claimbranch.application.manuscript_anchors import prepare_registration
        project,_=self.v3();shared,display=prepare_shared_audit(project)
        self.assertEqual('claimbranch.project-work/v25',display['result_schema'])
        self.assertEqual(project.work.history.seed,shared.work.history.seed)
        # Existing marker manuscript: marker registration remains legal beside v3 sources.
        candidate,_=prepare_registration(shared,manuscript='paper.tex',anchor_id='anchor',kind='text',expresses=['C'],rationale='Link imported argument to the unchanged manuscript.')
        self.assertEqual('claimbranch.project-work/v25',decode(candidate.payload)['schema'])
        self.assertEqual('claimbranch.paper-work/v29',decode(candidate.work.payload)['schema'])

    def test_nonshared_and_shared_conditional_workspace_preserve_same_writing(self):
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.manuscript_anchors import prepare_registration
        from claimbranch.application.paper_storage_codec import decode
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup
        project,_=self.v3();app=project_workspace(project);app.select('O')
        app.notes[app.context_key()]='Keep exact decimals and the reason for checking them.'
        project=project.with_work(PaperWork.create(project.work.history,workspace=snapshot_value(app)))
        self.assertIn('Keep exact decimals and the reason for checking them.',project_workspace(project).notes.values())
        with (self.paper/'paper.tex').open('ab') as file:file.write(b'\\begin{figure}\\caption{Table result}\\label{fig:result}\\end{figure}\n')
        project,_=prepare_registration(project,manuscript='paper.tex',anchor_id='fig-result',kind='figure',expresses=['C'],plots=['O'],rationale='Declared result use.',selector=dict(schema='claimbranch.tex-selector/v2',kind='label',value='fig:result'))
        self.assertTrue(any(json.loads(command)['schema_version']==17 for command in project.work.history.commands))
        self.assertEqual('claimbranch.project-work/v25',decode(project.payload)['schema'])
        shared,_=prepare_shared_audit(project)
        returned=split_personal_backup(personal_backup(shared))
        self.assertEqual(shared.payload,returned.payload)
        self.assertEqual(project_workspace(project).notes,project_workspace(returned).notes)


class HistoricalV4ProjectTests(unittest.TestCase):
    setUp=OriginalProjectTests.setUp

    def v4(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        value=source_v3_fixture();value['schema']='claimbranch.argument-import/v4';value['structural_defaults']=['observation','historical-decision']
        run=next(record for record in value['records'] if record['kind']=='experiment')
        run['body']={'question':run['body']['question']};run['recorded_at']='2026-10-12';run['display_label']='expA ModelB'
        run['mappings']=[[mapping for page in run['mappings'] for mapping in page if mapping['target']=='/question']]
        decision=next(record for record in value['records'] if record['kind']=='historical-decision')
        decision['body']['title']='Scope after sensitivity check';decision['recorded_at']='2026-10-13'
        decision['mappings'][0].append(dict(target='/title',source_silent=True,origin=dict(contributor='human',detail=None),transformation='Present display title; original historical reason retained.'))
        raw=encode(value,purpose='project');h=history_from_import(raw,anchor_id='anchor')
        h=h.append(dict(schema_version=18,id='open-current',project_id='synthetic-paper',episode_id='current',created_at='2026-10-16T00:00:00Z',operation_type='open-episode',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(title='Next research question',question='Which missing conditions must be checked?')))
        return ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw)

    def test_partial_historical_graph_source_reader_backup_and_return(self):
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_project import PersonalProjectStore,HISTORICAL_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup
        from claimbranch.application.paper_storage_codec import decode
        project=self.v4();self.assertEqual('claimbranch.project-work/v26',decode(project.payload)['schema'])
        app=project_workspace(project);app.select('X');self.assertIn('NOT RECORDED',str(app.detail()))
        self.assertIn('expA ModelB',str(app.detail()));app.select('O');app.detail()
        returned=split_personal_backup(personal_backup(project));self.assertEqual(project.payload,returned.payload)
        self.assertEqual('2026-10-12',returned.work.history.view('main')['experiments'][0]['recorded_at'])
        self.assertIsNone(returned.work.history.view('main')['experiments'][0]['metric'])
        decision=returned.work.history.view('main')['historical_decisions'][0]
        self.assertEqual('Scope after sensitivity check',decision['body']['title'])
        self.assertEqual('2026-10-13',decision['recorded_at'])
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(HISTORICAL_PERSONAL_MAGIC))
        with PersonalProjectStore(self.work) as store:self.assertEqual(project.payload,store.load().payload)

    def test_shared_audit_source_replay_and_selected_canonical_projection(self):
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.core.paper_capacity import expand_shared_audit
        from claimbranch.application.canonical_share import prepare_share,verify_share
        project=self.v4();candidate,_=prepare_shared_audit(project)
        self.assertEqual(18,expand_shared_audit(candidate.work.history.manifest())['schema_version'])
        selected={'schema':'claimbranch.share-selection/v1','record_ids':['X'],'reason_ids':[]}
        preview=prepare_share(candidate,selected)
        self.assertTrue(preview);self.assertTrue(verify_share(candidate,preview))

    def test_new_personal_judgment_retains_partial_source_and_reason_on_return(self):
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_project import PersonalProjectStore,PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.personal_archive import split_personal_backup
        project=self.v4()
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);app=project_workspace(project)
            app.recovery=PersonalProjectRecovery(store,app,project);app.select('C')
            app.keep_draft('The measurement definition remains to be checked.','The imported table is retained but its original metric is not mapped.')
            service=PersonalResearch(app,clock=lambda:2000000000)
            preview=service.prepare('reasoning',explanation_state='leave-for-later')
            service.commit(preview)
            returned=project_workspace(split_personal_backup(store.backup()))
            self.assertEqual(1,len(returned.paper._recorded_origins))
            self.assertIn('not mapped',str(returned.paper._recorded_origins))
            self.assertIsNone(returned.paper.history.view('main')['experiments'][0]['metric'])
            self.assertEqual('2026-10-12',returned.paper.history.view('main')['experiments'][0]['recorded_at'])

    def test_structural_column_defaults_cannot_reassign_scientific_values(self):
        from claimbranch.core.argument_import import preview_import
        from unittest.mock import patch
        from claimbranch.core import historical_argument as rules
        value=source_v3_fixture();value['schema']='claimbranch.argument-import/v4';value['structural_defaults']=['observation']
        record=value['records'][3];row=record['body']['measurement']['rows'][0]
        row['cells'][0]['column_id'],row['cells'][1]['column_id']=row['cells'][1]['column_id'],row['cells'][0]['column_id']
        paths={'/measurement/rows/0/cells/0/column_id','/measurement/rows/0/cells/1/column_id'}
        record['mappings']=[[m for m in page if m['target'] not in paths] for page in record['mappings']]
        original=rules.bookkeeping
        with patch.object(rules,'bookkeeping',side_effect=lambda r,t,v:True if t in paths else original(r,t,v)):
            self.assertTrue(preview_import(encode(value,purpose='project'))['valid'])
        refused=preview_import(encode(value,purpose='project'));self.assertFalse(refused['valid'])
        self.assertTrue(any('column_id' in e['pointer'] for e in refused['errors']))

    def test_source_free_scientific_values_cannot_invent_a_historical_observation(self):
        from claimbranch.core.argument_import import preview_import
        value=source_v3_fixture();value['schema']='claimbranch.argument-import/v4'
        record=value['records'][3]
        for page in record['mappings']:
            for index,mapping in enumerate(page):
                if mapping['target']=='/measurement/rows/0/cells/0/value/value':
                    page[index]=dict(target=mapping['target'],source_silent=True,origin=dict(contributor='ai',detail=None),transformation='New number invented for the example.')
        result=preview_import(encode(value,purpose='project'));self.assertFalse(result['valid'])
        self.assertTrue(any('Source-free observation' in error['error'] for error in result['errors']))

    def test_dummy_locator_cannot_bypass_an_explicit_ai_source_assertion(self):
        from claimbranch.core.argument_import import preview_import
        value=source_v3_fixture();value['schema']='claimbranch.argument-import/v4'
        record=next(r for r in value['records'] if r['kind']=='experiment')
        record['origin']=dict(contributor='human',detail=None)
        record['source_origins']=[dict(file_id='ledger',origin=dict(contributor='ai',detail='Known input influence.'))]
        mapping=next(m for page in record['mappings'] for m in page if m['target']=='/method')
        mapping.update(source_silent=True,transformation='New unrecorded method.')
        result=preview_import(encode(value,purpose='project'));self.assertFalse(result['valid'])

    def test_nonnull_artifact_provenance_is_not_empty_bookkeeping(self):
        from claimbranch.core.argument_import import preview_import
        value=source_v3_fixture();value['schema']='claimbranch.argument-import/v4'
        record=value['records'][3];record['body']['measurement']['artifact_refs'][0]['commit']='a'*40
        for page in record['mappings']:
            for index,mapping in enumerate(page):
                if mapping['target']=='/measurement/artifact_refs/0/commit':
                    page[index]=dict(target=mapping['target'],source_silent=True,origin=dict(contributor='human',detail=None),transformation='Invented artifact commit.')
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_new_historical_seed_requires_its_own_frame_and_commands(self):
        from claimbranch.application.paper_storage_codec import decode,encode as store_encode
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.personal_project import _PersonalCodec,SOURCE_PERSONAL_MAGIC,HISTORICAL_PERSONAL_MAGIC
        from claimbranch.core.research_history import ResearchHistory
        project=self.v4();raw=decode(project.work.payload);raw['schema']='claimbranch.paper-work/v29'
        with self.assertRaises(ContractError):PaperWork(store_encode(raw))
        checkpoint=_PersonalCodec().seal(project.payload)
        with self.assertRaises(ContractError):_PersonalCodec().open(SOURCE_PERSONAL_MAGIC+checkpoint[len(HISTORICAL_PERSONAL_MAGIC):])
        h=project.work.history;command=json.loads(h.commands[0]);command['schema_version']=14
        with self.assertRaises(ContractError):ResearchHistory(h.seed,(encode(command,purpose='history'),))


def replacement_fixture(link=True):
    """Invented scalar ledgers; no private manuscript or live model input."""
    value=scalar_fixture();records=deepcopy(value['records'])
    first=next(r for r in records if r['kind']=='observation');first['recorded_at']='2026-10-10'
    second=deepcopy(first);second['id']='O2';second['recorded_at']='2026-10-11';second['body']['value']='0.6'
    second['body']['statement']='Replacement replay under the same synthetic conditions.'
    records.append(second)
    source=json.dumps(dict(entries=[r['body'] for r in records]),ensure_ascii=False,separators=(',',':')).encode()
    for index,record in enumerate(records):
        record.pop('source_pointer',None)
        record['mappings']=[[dict(target=target,file_id='ledger',locator=dict(kind='json-pointer',pointer=f'/entries/{index}'+target),normalization='literal-v1',transformation=None) for target,_ in _leaves(record['body'])]]
    if link:second['replacement']=dict(previous_id=first['id'],origin='mixed',source_context='Private imported relation declaration.',rationale='The second replay is the replacement; retain both.')
    return dict(schema='claimbranch.argument-import/v5',profile='paper',project_id=value['project_id'],title=value['title'],files=[dict(id='ledger',name='synthetic.json',media='json',source=source_record(source))],condition_vocabulary=[],records=records,selected_ids=[r['id'] for r in records])


class CompletedHistoryTests(unittest.TestCase):
    setUp=OriginalProjectTests.setUp

    def make_project(self,value=None):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        value=value or replacement_fixture();raw=encode(value,purpose='project');h=history_from_import(raw,anchor_id='anchor')
        h=h.append(dict(schema_version=18,id='open-current',project_id=value['project_id'],episode_id='current',created_at='2026-10-16T00:00:00Z',operation_type='open-episode',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(title='Inspect prior history',question='What did the replacement change?')))
        return ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw)

    def replacement(self,project,**changes):
        from claimbranch.application.protocols import prepare_protocol
        evidence={o['id']:o for o in project.work.history.view('main')['evidence']}
        payload=dict(id='new-replacement',previous_id='O',replacement_id='O2',expected_previous_event_id=evidence['O']['history'][-1]['event_id'],expected_replacement_event_id=evidence['O2']['history'][-1]['event_id'],origin='mixed',source_context='Present declared relationship; not an evidence correction.',rationale='Follow the corrected replay without erasing the old result.')
        payload.update(changes)
        return prepare_protocol(project,dict(schema='claimbranch.protocol-input/v2',operation_type='record-observation-replacement',payload=payload),contribution_origin='human')

    def test_imported_replacement_retains_values_status_events_and_honest_origin(self):
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.tui_project import project_workspace
        project=self.make_project();view=project.work.history.view('main');link=next(iter(view['observation_replacements'].values()))
        evidence={o['id']:o for o in view['evidence']}
        self.assertEqual('O',link['previous_id']);self.assertEqual('O2',link['replacement_id']);self.assertEqual('source-claimed-order',link['chronology'])
        self.assertEqual('2026-10-11',link['recorded_at']);self.assertFalse(link['chronology_verified'])
        self.assertEqual('0.35',evidence['O']['value']);self.assertEqual('0.6',evidence['O2']['value'])
        self.assertEqual(1,len(evidence['O']['history']));self.assertEqual('import',evidence['O2']['history'][0]['action']);self.assertIsNone(evidence['O2']['history'][0]['supersedes_id'])
        self.assertFalse(evidence['O2']['imported_source']['origin_flags']['ai']);self.assertEqual('mixed',link['origin'])
        graph=PaperService(project.work.history).query('main');edge=next(r for r in graph['relations'] if r['type']=='replaces')
        self.assertEqual(('O2','O',False),(edge['source_id'],edge['target_id'],edge['scientific']))
        claim=next(n for n in graph['nodes'] if n['id']=='C');self.assertEqual('none; separate evidence review required',claim['content']['replacement_context'][0]['status_effect'])
        app=project_workspace(project);app.select('O');self.assertIn('RESULT REPLACEMENTS',str(app.detail()))
        self.assertEqual(project.work.history.manifest(),type(project.work.history)(project.work.history.seed,project.work.history.commands).manifest())

    def test_preview_shows_relation_unresolved_and_required_previous_endpoint(self):
        from claimbranch.core.argument_import import preview_import
        from claimbranch.application.import_review import unresolved_items,summary_lines
        value=replacement_fixture();value['selected_ids']=['T','O2'];preview=preview_import(encode(value,purpose='project'))
        self.assertTrue(preview['valid'],preview.get('errors'));self.assertIn('O',preview['required']);self.assertEqual(1,len(preview['replacement_links']))
        self.assertTrue(any(item.get('record_metadata') for item in unresolved_items(preview)))
        self.assertTrue(any('Explicit replacement links: 1' in line for line in summary_lines(preview)))

    def test_import_refuses_self_cycle_unknown_endpoint_and_reverse_dates(self):
        from claimbranch.core.argument_import import preview_import
        for case in ('self','cycle','missing','date'):
            value=replacement_fixture();first=next(r for r in value['records'] if r['id']=='O');second=value['records'][-1]
            if case=='self':second['replacement']['previous_id']='O2'
            elif case=='missing':second['replacement']['previous_id']='missing'
            elif case=='cycle':
                first['recorded_at']=second['recorded_at']=None;first['replacement']=dict(second['replacement'],previous_id='O2')
            else:second['recorded_at']='2026-10-09'
            preview=preview_import(encode(value,purpose='project'));self.assertFalse(preview['valid'],case)
            self.assertGreater(preview['error_count'],0)

    def test_missing_or_mixed_date_precision_remains_unknown(self):
        value=replacement_fixture();value['records'][-1]['recorded_at']=None
        project=self.make_project(value);self.assertEqual('unknown',next(iter(project.work.history.view('main')['observation_replacements'].values()))['chronology'])
        value['records'][-1]['recorded_at']='2026-10-11T00:00:00Z';project=self.make_project(value)
        self.assertEqual('unknown',next(iter(project.work.history.view('main')['observation_replacements'].values()))['chronology'])

    def test_current_explicit_link_is_exact_no_status_change_and_rejects_duplicate(self):
        base=self.make_project(replacement_fixture(False));candidate,review=self.replacement(base)
        self.assertEqual(base.work.history.view('main')['evidence'],candidate.work.history.view('main')['evidence'])
        self.assertEqual(base.work.history.view('main')['claims'],candidate.work.history.view('main')['claims'])
        self.assertEqual(19,review['operation']['schema_version']);self.assertEqual('human',review['operation']['contribution_origin'])
        self.assertEqual('mixed',candidate.work.history.view('main')['observation_replacements']['new-replacement']['origin'])
        with self.assertRaises(ContractError):self.replacement(candidate,id='again')
        with self.assertRaises(ContractError):self.replacement(base,expected_previous_event_id='stale')
        self.assertNotIn('observation_replacements',base.work.history.view('main'))

    def test_replacement_and_protocol_keep_new_frame_backup_and_opaque_share(self):
        from claimbranch.application.personal_project import PersonalProjectStore,HISTORY_PERSONAL_MAGIC,_PersonalCodec
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup,HISTORY_BACKUP_MAGIC
        from claimbranch.application.canonical_share import prepare_share,verify_share
        project=self.make_project();saved=self.work
        with PersonalProjectStore.create(saved,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        self.assertTrue((saved/'personal.cbp').read_bytes().startswith(HISTORY_PERSONAL_MAGIC))
        with PersonalProjectStore(saved) as store:self.assertEqual(project.payload,store.load().payload)
        backup=personal_backup(project);self.assertTrue(backup.startswith(HISTORY_BACKUP_MAGIC));self.assertEqual(project.payload,split_personal_backup(backup).payload)
        with self.assertRaises(ContractError):_PersonalCodec().open(b'CBPP\x00\x12'+_PersonalCodec().seal(project.payload)[6:])
        selection=dict(schema='claimbranch.share-selection/v1',record_ids=['O'],reason_ids=[])
        shared=prepare_share(project,selection);self.assertEqual('claimbranch.canonical-share/v4',decode(shared,purpose='project')['schema'])
        self.assertIn('observation-replacement',shared.decode());self.assertNotIn('Private imported relation declaration',shared.decode());self.assertNotIn('The second replay',shared.decode())
        self.assertTrue(verify_share(project,shared))

    def test_completed_protocol_on_incomplete_import_needs_no_invented_metric(self):
        from application.test_protocols import CompletedProtocolTests
        from claimbranch.application.protocols import prepare_protocol
        from claimbranch.core.protocols import experiment_digest,protocol_context
        project=HistoricalV4ProjectTests.v4(self);run=project.work.history.view('main')['experiments'][0]
        self.assertIsNone(run['metric'])
        from unittest.mock import patch
        # Reuse only the synthetic payload factory, retaining this exact source project.
        captured=[]
        with patch('application.test_protocols.prepare_protocol',side_effect=lambda p,r:(captured.append(r) or p,{})):
            CompletedProtocolTests.completed(self,project)
        request=captured[0];candidate,_=prepare_protocol(project,request,contribution_origin='human')
        self.assertEqual(0,len(candidate.work.history.view('main')['experiment_plans']))
        self.assertIn(run['id'],protocol_context(candidate.work.history.view('main')))
        self.assertEqual(project.work.history.view('main')['evidence'],candidate.work.history.view('main')['evidence'])


    def test_relation_origin_and_unresolved_mapping_stay_on_the_relation(self):
        from claimbranch.core.argument_import import source_references
        from claimbranch.core.research_history import _reduce
        from claimbranch.application.canonical_share import prepare_share
        from claimbranch.application.tui_project import project_workspace
        value=replacement_fixture();value['records'][-1]['origin']=dict(contributor='human',detail=None);value['records'][-1]['replacement']['origin']='ai'
        project=self.make_project(value);state=_reduce(project.work.history.seed,project.work.history.commands);view=project.work.history.view('main')
        link=next(iter(view['observation_replacements'].values()));observation=next(o for o in view['evidence'] if o['id']=='O2')
        self.assertFalse(observation['imported_source']['origin_flags']['ai']);self.assertEqual(0,observation['imported_source']['unresolved_leaf_count'])
        refs=source_references(state,state['branches']['main'],[],'O2');relation_ref=next(r for r in refs if r['record_id']==link['id'])
        self.assertTrue(relation_ref['origin_flags']['ai']);self.assertEqual(1,relation_ref['unresolved_count'])
        app=project_workspace(project);self.assertIn('Private imported relation declaration',app.imported_original_source(link['id']))
        raw=prepare_share(project,dict(schema='claimbranch.share-selection/v1',record_ids=['O2'],reason_ids=[]));shared=decode(raw,purpose='project')['records']
        relation=next(r for r in shared if r['kind']=='observation-replacement');self.assertEqual(['ai'],relation['content']['origins']);self.assertEqual(1,relation['content']['unresolved_source_fields'])

    def test_new_contract_cannot_hide_in_older_work_or_project_envelope(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        project=self.make_project();work=decode(project.work.payload,purpose='project');work['schema']='claimbranch.paper-work/v30'
        with self.assertRaises(ContractError):PaperWork(encode(work,purpose='project'))
        changed=decode(project.payload,purpose='project');changed['schema']='claimbranch.project-work/v26'
        with self.assertRaises(ContractError):ProjectWork(encode(changed,purpose='project'))


    def test_personal_link_keeps_legacy_unresolved_replacement_text_and_endpoint_ai(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        from claimbranch.core.argument_import import source_references
        from claimbranch.core.research_history import _reduce
        value=scalar_fixture();original=json.loads(source_bytes(value['source']))
        original['entries'][3]['replacement']='Uninterpreted legacy ledger text; not a typed link.'
        record=deepcopy(value['records'][3]);record['id']='O2';record['source_pointer']='/entries/6';original['entries'].append(deepcopy(record['body']))
        record['mappings']=[dict(target=target,source='/entries/6'+target,transformation=None) for target,_ in _leaves(record['body'])]
        value['records'][3]['origin']=dict(contributor='ai',detail=None);value['records'].append(record);value['selected_ids'].append('O2')
        value['source']=source_record(json.dumps(original).encode());raw=encode(value,purpose='project');h=history_from_import(raw,anchor_id='anchor')
        h=h.append(dict(schema_version=5,id='open-legacy',project_id=value['project_id'],episode_id='current',created_at='2026-10-16T00:00:00Z',operation_type='open-episode',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(title='Inspect prior records',question='What does this replacement mean?')))
        project=ProjectWork.create(PaperWork.create(h),self.preview,import_input=raw)
        before=_reduce(h.seed,h.commands);refs=source_references(before,before['branches']['main'],[],'O');old=next(r for r in refs if r['record_id']=='O')
        changed,_=self.replacement(project,origin='human');state=_reduce(changed.work.history.seed,changed.work.history.commands)
        after=source_references(state,state['branches']['main'],[],'O');self.assertEqual(old['unresolved_count'],next(r for r in after if r['record_id']=='O')['unresolved_count'])
        self.assertIn('ai',state['branches']['main']['protocol_origins']['new-replacement'])
        observation=next(o for o in changed.work.history.view('main')['evidence'] if o['id']=='O')
        self.assertIn('/entries/3/replacement',sum(observation['imported_source']['unresolved_pointer_pages'],[]))
