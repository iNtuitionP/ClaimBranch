"""Exact prior tables enter once, retaining sources through personal save/return."""
from copy import deepcopy
import json
import unittest
from claimbranch.core.paper_capacity import encode,source_record,source_bytes
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
                if b'next page / q' in pending:os.write(master,b'\n');pending=b''
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
