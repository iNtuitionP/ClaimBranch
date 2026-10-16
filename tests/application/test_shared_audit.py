"""Opted-in audit encoding preserves full logical content and legacy prefixes."""
from copy import deepcopy
import hashlib
import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from .test_original_registration import history


class SharedAuditTests(unittest.TestCase):
    def opted(self,h=None):
        h=history() if h is None else h;return h,h.append(dict(schema_version=16,id='select-shared-audit',project_id='synthetic-paper',episode_id='local',created_at='2026-10-16T00:00:00Z',operation_type='set-audit-encoding',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(encoding='shared-values/v1')))

    def test_full_logical_audit_and_old_prefix_are_unchanged(self):
        from claimbranch.core.research_history import ResearchHistory,_reduce,_manifest_value
        from claimbranch.core.paper_capacity import expand_shared_audit,verify_shared_audit
        old,new=self.opted();self.assertEqual(old.seed,new.seed);self.assertEqual(old.commands,new.commands[:-1])
        self.assertEqual(old.manifest(),ResearchHistory(new.seed,new.commands[:-1]).manifest())
        self.assertEqual(old.view('main'),new.view('main'))
        logical=_manifest_value(_reduce(new.seed,new.commands),new.commands)
        self.assertEqual(logical,expand_shared_audit(new.manifest()))
        self.assertEqual(logical,verify_shared_audit(new.manifest()))
        self.assertEqual(new.manifest(),ResearchHistory.replay(new.seed,new.commands).manifest())
        self.assertIn('shared_values',decode(new.manifest(),purpose='manifest'))

    def test_reference_tampering_unused_values_and_forged_view_refuse(self):
        from claimbranch.core.paper_capacity import expand_shared_audit,verify_shared_audit,pack_shared_audit
        _,h=self.opted();raw=h.manifest();value=decode(raw,purpose='manifest')
        key=next(iter(value['shared_values']))
        bad=deepcopy(value);bad['shared_values'][key]=[]
        with self.assertRaises(ContractError):expand_shared_audit(encode(bad,purpose='manifest'))
        bad=deepcopy(value);bad['shared_values']['0'*64]=[]
        with self.assertRaises(ContractError):expand_shared_audit(encode(bad,purpose='manifest'))
        logical=expand_shared_audit(raw);logical['views']['main']['paper_title']='Forged view'
        with self.assertRaises(ContractError):verify_shared_audit(pack_shared_audit(logical))

    def test_expansion_bound_refuses_before_materializing_repeated_values(self):
        from claimbranch.core.paper_capacity import pack_shared_audit,expand_shared_audit
        _,h=self.opted();value=decode(h.manifest(),purpose='manifest');key=next(iter(value['shared_values']))
        # A small wire representation must not authorize unbounded expansion.
        value['views']['main']={str(i):dict(ref=key) for i in range(2048)}
        value['expanded_bytes']=1;value['expanded_sha256']='0'*64
        with self.assertRaises(ContractError):expand_shared_audit(encode(value,purpose='manifest'))

    def test_unused_valid_value_and_actual_expansion_overflow_refuse(self):
        from claimbranch.core.paper_capacity import expand_shared_audit,PROJECT_BYTES
        _,h=self.opted();value=decode(h.manifest(),purpose='manifest')
        item='x'*1024;key=hashlib.sha256(encode(item,purpose='project')).hexdigest()
        value['shared_values'][key]=item
        with self.assertRaisesRegex(ContractError,'unused shared audit'):expand_shared_audit(encode(value,purpose='manifest'))
        value=decode(h.manifest(),purpose='manifest');large=['x'*16384]*256;key=hashlib.sha256(encode(large,purpose='project')).hexdigest()
        value['shared_values']={key:large};value['views']={'main':{str(i):dict(ref=key) for i in range(5)}};value['expanded_bytes']=PROJECT_BYTES
        with self.assertRaisesRegex(ContractError,'expanded byte bound'):expand_shared_audit(encode(value,purpose='manifest'))

    def test_unicode_replay_and_wrapper_named_user_data_are_lossless(self):
        from .test_original_registration import fixture
        from claimbranch.core.paper_capacity import verify_shared_audit,pack_shared_audit,expand_shared_audit
        value=fixture();value['title']='독립 검증과 판단'
        _,h=self.opted(history(value));self.assertEqual('독립 검증과 판단',verify_shared_audit(h.manifest())['views']['main']['paper_title'])
        logical=expand_shared_audit(h.manifest());logical['views']['main']['opaque']={'ref':'원문','inline':{'ref':'literal'}}
        self.assertEqual(logical,expand_shared_audit(pack_shared_audit(logical)))


class AuditConversionTests(unittest.TestCase):
    def setUp(self):
        from .test_original_registration import OriginalProjectTests
        OriginalProjectTests.setUp(self)

    def test_conversion_preserves_old_writing_and_frames_with_explicit_terminal_choice(self):
        import io
        from types import SimpleNamespace
        from contextlib import redirect_stdout
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.paper_storage_codec import decode as storage_decode
        from claimbranch.application.personal_project import PersonalProjectStore,_PersonalCodec,SHARED_PERSONAL_MAGIC,RETAINED_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup
        from claimbranch.application.tui_project import project_workspace
        from .test_tui_terminal import TerminalProcessTests
        before=self.project;converted,preview=prepare_shared_audit(before)
        self.assertEqual(before.work.history.seed,converted.work.history.seed)
        self.assertEqual(before.work.history.commands,converted.work.history.commands[:-1])
        self.assertEqual(before.work.history.view('main'),converted.work.history.view('main'))
        self.assertEqual('claimbranch.project-work/v23',storage_decode(converted.payload)['schema'])
        self.assertEqual(converted.payload,split_personal_backup(personal_backup(converted)).payload)
        with self.assertRaises(ContractError):_PersonalCodec().open(RETAINED_PERSONAL_MAGIC+converted.payload)
        with self.assertRaises(ContractError):prepare_shared_audit(converted)
        with PersonalProjectStore.create(self.work,project_id=before.project_id) as store:store.save(before,preview=self.preview)
        checkpoint=(self.work/'personal.cbp').read_bytes()
        tty=TerminalProcessTests();tty.setUp();self.addCleanup(tty.tearDown)
        tty.launch(personal_arguments=['enable-shared-audit','--directory',str(self.work)])
        tty.expect('Type convert');tty.send('\n');tty.process.wait(timeout=10)
        self.assertEqual(checkpoint,(self.work/'personal.cbp').read_bytes())
        tty=TerminalProcessTests();tty.setUp();self.addCleanup(tty.tearDown)
        tty.launch(personal_arguments=['enable-shared-audit','--directory',str(self.work)])
        tty.expect('Type convert');tty.send('convert\r','Shared audit format saved');tty.process.wait(timeout=10)
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(SHARED_PERSONAL_MAGIC))
        with PersonalProjectStore(self.work) as store:self.assertEqual(before.work.history.view('main'),store.load().work.history.view('main'))

    def test_old_envelopes_reject_new_audit_command_and_new_frame_is_exact(self):
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork
        from claimbranch.application.personal_project import _PersonalCodec,LABEL_PERSONAL_MAGIC
        from claimbranch.application.paper_storage_codec import decode as storage_decode,encode as storage_encode
        converted,_=prepare_shared_audit(self.project)
        value=storage_decode(converted.work.payload);value['schema']='claimbranch.paper-work/v25'
        with self.assertRaises(ContractError):PaperWork(storage_encode(value))
        value=storage_decode(converted.payload);value['schema']='claimbranch.project-work/v21'
        with self.assertRaises(ContractError):ProjectWork(storage_encode(value))
        with self.assertRaises(ContractError):_PersonalCodec().open(LABEL_PERSONAL_MAGIC+converted.payload)
        self.assertEqual(self.project.payload,ProjectWork(self.project.payload).payload)

    def test_public_import_flag_is_reviewed_and_reports_converted_capacity(self):
        import os,select,subprocess,sys,time
        from claimbranch.application.personal_project import PersonalProjectStore,SHARED_PERSONAL_MAGIC
        from claimbranch.core.paper_capacity import verify_shared_audit
        path=self.root/'argument.json';path.write_bytes(self.raw);path.chmod(0o600)
        master,slave=os.openpty()
        args=[sys.executable,'-m','claimbranch','project','import-argument','--shared-audit','--input',str(path),'--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex','--question','What needs independent verification?']
        process=subprocess.Popen(args,stdin=slave,stdout=slave,stderr=slave,env={**os.environ,'TERM':'xterm-256color'});os.close(slave)
        pending=b'';tail=b'';deadline=time.monotonic()+45
        try:
            while process.poll() is None and time.monotonic()<deadline:
                if not select.select([master],[],[],0.1)[0]:continue
                try:chunk=os.read(master,65536)
                except OSError:break
                pending+=chunk;tail=(tail+chunk)[-16384:]
                if b'next page / q' in pending:os.write(master,b'\n');pending=b''
                elif b'Type import to register' in pending:os.write(master,b'import\n');pending=b''
            self.assertEqual(0,process.wait(timeout=5),tail.decode(errors='replace'))
            self.assertIn(b'Imported personal argument saved',tail)
        finally:
            if process.poll() is None:process.kill();process.wait()
            os.close(master)
        with PersonalProjectStore(self.work) as store:
            project=store.load();self.assertEqual(2,len(project.work.history.commands))
            self.assertEqual(16,decode(project.work.history.commands[-1],purpose='history')['schema_version'])
            self.assertEqual('shared-values/v1',decode(project.work.history.commands[-1],purpose='history')['payload']['encoding'])
            verify_shared_audit(project.work.history.manifest())
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(SHARED_PERSONAL_MAGIC))

    def test_v27_schema_really_accepts_legacy_v14_and_pins_encoding(self):
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.paper_work_store import work_schema
        from claimbranch.core.research_schema import normalize,command_schema
        converted,_=prepare_shared_audit(self.project)
        value=decode(converted.work.payload,purpose='project')
        self.assertEqual(value,normalize(value,work_schema(27),profile='paper'))
        self.assertIn(14,[c['schema_version'] for c in value['commands']]);self.assertEqual(16,value['commands'][-1]['schema_version'])
        bad=deepcopy(value['commands'][-1]);bad['payload']['encoding']='unknown-format'
        with self.assertRaises(ContractError):normalize(bad,command_schema(16),profile='paper')

    def test_existing_partial_writing_and_original_cause_survive_conversion(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup
        app=project_workspace(self.project);app.recovery=SimpleNamespace(personal_project=True,project=self.project);app.select('C')
        app.notes[app.context_key()]='이전 원인과 미완성 설명은 남는다.'
        app.keep_draft('Keep the scientific limitation visible.','The source leaves an independent test unresolved.')
        service=PersonalResearch(app,clock=lambda:2000000000);preview=service.prepare('reasoning');topic=preview.display['explanation_topics'][0]['id']
        service.keep_explanation(preview,entries=[dict(topic_id=topic,text='Earlier unfinished explanation.',reuse_rationale=False)])
        before=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        converted,_=prepare_shared_audit(before);returned=project_workspace(split_personal_backup(personal_backup(converted)))
        # Compare every persisted field independently of the converter's
        # snapshot. Only current session bindings/revisions may advance.
        from claimbranch.application.paper_storage_codec import decode as storage_decode
        original=storage_decode(before.work.payload)['workspace']
        updated=storage_decode(converted.work.payload)['workspace']
        for old,new in zip(original['paper']['drafts'],updated['paper']['drafts'],strict=True):
            self.assertEqual(old['session']['revision']+1,new['session']['revision'])
            self.assertNotEqual(old['session']['view_digest'],new['session']['view_digest'])
            new['session']['revision']=old['session']['revision']
            new['session']['view_digest']=old['session']['view_digest']
        self.assertEqual(original,updated)
        self.assertEqual(app.paper._personal_explanations,returned.paper._personal_explanations)
        self.assertEqual(app.draft(),returned.draft());self.assertEqual(app.notes,returned.notes)
        self.assertFalse(PersonalResearch(returned).explanation_contexts()[0]['closure_available'])
        cause=deepcopy(app.paper._personal_explanations[0]['cause'])
        PersonalResearch(returned).keep_retained_explanation(cause,entries=[dict(topic_id=topic,text='Continued after conversion.',reuse_rationale=False)])
        saved=converted.with_work(PaperWork.create(returned.paper.history,workspace=snapshot_value(returned)))
        again=project_workspace(split_personal_backup(personal_backup(saved)))
        retained=PersonalResearch(again).explanation_contexts()[0]
        self.assertEqual(cause,retained['cause'])
        self.assertEqual('Continued after conversion.',retained['explanation']['entries'][0]['text'])
        self.assertFalse(retained['closure_available'])

    def test_dry_run_preserves_every_saved_file(self):
        import subprocess,sys
        from claimbranch.application.personal_project import PersonalProjectStore
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        before={p.name:p.read_bytes() for p in self.work.iterdir() if p.is_file()}
        result=subprocess.run([sys.executable,'-m','claimbranch','project','enable-shared-audit','--directory',str(self.work),'--dry-run'],capture_output=True,text=True,timeout=20)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.work.iterdir() if p.is_file()})
