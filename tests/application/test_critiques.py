from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned private source boundaries, references and durable local return."""
import io
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from application import test_claim_wording as prior
from application import test_protocols as protocol_tests
from claimbranch.application.critiques import prepare_critique,recheck_critique,read_original
from claimbranch.core.critiques import placeholder_projection
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode,source_bytes
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.project_work import ProjectWork
from claimbranch.application.personal_project import PersonalProjectStore,CRITIQUE_PERSONAL_MAGIC
from claimbranch.application.personal_archive import personal_backup,split_personal_backup,CRITIQUE_BACKUP_MAGIC,PersonalExport
from claimbranch.application.paper_service import PaperService
from claimbranch.application.tui_project import project_workspace

SECRET='PRIVATE_REVIEWER_IDENTITY_4c81'
ORIGINAL='PRIVATE_ORIGINAL_7e31: please distinguish grouping sensitivity from primary evidence.'

class CritiqueTests(unittest.TestCase):
    setUp=prior.ClaimWordingTests.setUp

    def request(self,**changes):
        payload=dict(source_kind='review',question='Does the grouping definition alter the main conclusion?',question_origin='human',source_origin='human',private_original=ORIGINAL,private_identity=SECRET,private_label='/private/confidential-review/path')
        payload.update(changes);return dict(schema='claimbranch.critique-input/v1',operation_type='capture-critique',payload=payload)

    def capture(self,project=None,**changes):
        request=self.request(**changes);raw=json.dumps(request,ensure_ascii=False,indent=2).encode();return prepare_critique(project or self.project,request,original_input=raw)

    def key(self,project):return next(iter(project.work.history.view('main')['critiques']))

    def link(self,project,target='C',relation='questions',**changes):
        payload=dict(id='link',critique_id=self.key(project),relation=relation,target_id=target,consequence_operation_id=None,rationale='This concern motivates the named work.')
        payload.update(changes);return prepare_critique(project,dict(schema='claimbranch.critique-input/v1',operation_type='link-critique',payload=payload))

    def test_raw_original_is_private_and_graph_question_not_evidence(self):
        before=self.project.work.history.view('main');project,preview=self.capture();after=project.work.history.view('main')
        self.assertEqual(before['evidence'],after['evidence']);self.assertEqual(before['claims'],after['claims'])
        self.assertEqual(self.project.work.history.commands,project.work.history.commands[:-1]);self.assertEqual(self.project.work.history.seed,project.work.history.seed)
        self.assertNotIn(SECRET,str(preview));self.assertNotIn(ORIGINAL,str(preview));self.assertNotIn(SECRET,project.work.history.manifest().decode());self.assertNotIn(ORIGINAL,project.work.history.manifest().decode())
        original=read_original(project,self.key(project));self.assertEqual(SECRET,original['original']['payload']['private_identity']);self.assertEqual(ORIGINAL,original['original']['payload']['private_original'])
        self.assertEqual('claimbranch.project-work/v18',decode(project.payload,purpose='project')['schema'])
        node=next(n for n in preview['after']['nodes'] if n['kind']=='critique-question');self.assertEqual('sourced-question-not-empirical-evidence',node['content']['classification'])
        app=project_workspace(project);app.select(self.key(project));self.assertIn('NOT EMPIRICAL EVIDENCE',str(app.detail()));self.assertNotIn(SECRET,str(app.detail()))

    def test_questioning_and_completed_experiment_associations_never_support_or_resolve(self):
        project,_=self.capture();project,_=self.link(project);project,_=self.link(project,target='X',relation='addressed-by',id='experiment-link')
        graph=PaperService(project.work.history).query('main');links=[r for r in graph['relations'] if r['source_id']==self.key(project)]
        self.assertEqual({'questions','addressed-by'},{r['type'] for r in links});self.assertTrue(all(not r['scientific'] for r in links))
        self.assertEqual('unresolved',project.work.history.view('main')['critiques'][self.key(project)]['resolution'])
        self.assertEqual([],PaperService(project.work.history).anchor_impact([self.key(project)])['potentially_affected_anchor_ids'])

    def test_plan_and_exact_claim_wording_consequence_are_distinct(self):
        base=protocol_tests.ProtocolTests.base(self);project,_=self.capture(base);project,_=self.link(project,target='P',relation='addressed-by')
        self.assertEqual('P',project.work.history.view('main')['critique_links']['link']['target_id'])
        imported,_=self.capture();worded,_=prior.ClaimWordingTests.policy(self,imported);policy=worded.work.history.view('main')['wording_policies']['C']
        linked,_=self.link(worded,target='C',relation='addressed-by',consequence_operation_id=policy['operation_id'])
        self.assertEqual(policy['operation_id'],linked.work.history.view('main')['critique_links']['link']['consequence_operation_id'])
        with self.assertRaisesRegex(ContractError,'exact claim|recorded selected'):self.link(imported,target='C',relation='addressed-by')

    def test_invalid_alias_duplicate_and_evidence_target_refuse_entire_change(self):
        project,_=self.capture();original=project.payload
        for change in (dict(target='O'),dict(target='missing'),dict(target='C',relation='addressed-by',consequence_operation_id='fake')):
            with self.assertRaises(ContractError):self.link(project,**change)
        linked,_=self.link(project)
        with self.assertRaises(ContractError):self.link(linked,id='second-link')
        with self.assertRaises(ContractError):self.link(project,id='C')
        self.assertEqual(original,project.payload)

    def test_default_placeholder_projection_excludes_nested_original_identity_hash_and_question(self):
        project,_=self.capture(question=SECRET+' copied into an owner-provided question.');project,_=self.link(project,id='PRIVATE_LINK_NAME')
        value=decode(project.payload,purpose='project');projection=placeholder_projection(project.work.history.view('main'),value['public_ids']);text=json.dumps(projection)
        for secret in (SECRET,ORIGINAL,'confidential-review','PRIVATE_LINK_NAME',self.key(project)):self.assertNotIn(secret,text)
        self.assertTrue(all(p['id'].startswith('record-') for p in projection['placeholders']));self.assertFalse(projection['anonymity_verified'])
        self.assertEqual(projection,placeholder_projection(project.work.history.view('main'),value['public_ids']))
        self.assertNotIn(project.work.history.view('main')['critiques'][self.key(project)]['source_sha256'],text)

    def test_provider_context_refuses_instead_of_accidentally_transmitting_raw_or_neutral_text(self):
        project,_=self.capture();service=PaperService(project.work.history)
        with self.assertRaisesRegex(ContractError,'Private critique'):service.compile_context({})
        from claimbranch.application.cli import main
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('claimbranch.application.provider_commands.PersonalProviderConnection',side_effect=AssertionError('Provider opened')),patch('sys.stderr',new_callable=io.StringIO):self.assertEqual(1,main(['project','open','--directory',str(self.work),'--provider-directory',str(self.root/'never-open')]))

    def test_full_export_refuses_before_file_creation_while_private_backup_restores_original(self):
        project,_=self.capture();folder=self.root/'export';folder.mkdir(mode=0o700)
        with PersonalExport(folder) as export:
            with self.assertRaisesRegex(ContractError,'Private critique'):export.write(project.payload)
        self.assertFalse((folder/'project.json').exists())
        backup=personal_backup(project);self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC));restored=split_personal_backup(backup)
        self.assertEqual(project.payload,restored.payload);self.assertEqual(SECRET,read_original(restored,self.key(restored))['original']['payload']['private_identity'])

    def test_private_blob_digest_association_and_orphan_tampering_refuse(self):
        project,_=self.capture();value=decode(project.payload,purpose='project')
        broken=deepcopy(value);broken['critique_sources']=[]
        with self.assertRaisesRegex(ContractError,'incomplete'):ProjectWork(encode(broken,purpose='project'))
        broken=deepcopy(value);broken['critique_sources'][0]['source']['sha256']='0'*64
        with self.assertRaises(ContractError):ProjectWork(encode(broken,purpose='project'))
        broken=deepcopy(value);broken['critique_sources'].append(broken['critique_sources'][0])
        with self.assertRaises(ContractError):ProjectWork(encode(broken,purpose='project'))
        self.assertEqual(value,decode(project.payload,purpose='project'))

    def test_question_revisions_keep_original_and_cannot_erase_declared_ai(self):
        project,_=self.capture(question_origin='ai');key=self.key(project);q=project.work.history.view('main')['critiques'][key]
        request=dict(schema='claimbranch.critique-input/v1',operation_type='revise-critique-question',payload=dict(critique_id=key,expected_revision_id=q['revision_id'],question='Which definition should be reported?',question_origin='human',rationale='Keep the new scope explicit.'))
        changed,_=prepare_critique(project,request);question=changed.work.history.view('main')['critiques'][key]
        self.assertEqual('ai',question['revisions'][0]['question_origin']);self.assertEqual(self.request(question_origin='ai'),read_original(changed,key)['original'])
        with self.assertRaisesRegex(ContractError,'Stale'):prepare_critique(changed,request)
        from claimbranch.core.research_history import _reduce,_branch_ai
        state=_reduce(changed.work.history.seed,changed.work.history.commands);self.assertTrue(_branch_ai(state['branches']['main'],state))

    def test_exact_capture_input_is_required_and_duplicate_source_not_reimported(self):
        with self.assertRaisesRegex(ContractError,'Exact original'):prepare_critique(self.project,self.request())
        project,_=self.capture()
        with self.assertRaisesRegex(ContractError,'already retained'):self.capture(project)

    def test_note_restart_backup_return_does_not_expose_original_in_graph(self):
        from claimbranch.application.tui_work_recovery import snapshot_value
        app=project_workspace(self.project);app.select('C');app.notes[app.context_key()]='Keep the existing limitation.'
        base=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)));project,_=self.capture(base)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview);self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC))
        with PersonalProjectStore(self.work) as store:returned=store.load();backup=store.backup()
        restored=split_personal_backup(backup);self.assertEqual(project.payload,restored.payload);app=project_workspace(restored);self.assertIn('Keep the existing limitation.',app.notes.values());app.select(self.key(restored));self.assertNotIn(SECRET,str(app.detail()))

    def test_cli_preview_cancel_confirm_original_is_explicit_and_reference_output_safe(self):
        from claimbranch.application.cli import main
        path=self.root/'critique.json';path.write_text(json.dumps(self.request()));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        args=['project','critique','--directory',str(self.work),'--input',str(path)];before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(args+['--dry-run']))
        self.assertNotIn(SECRET,output.getvalue());self.assertNotIn(ORIGINAL,output.getvalue());self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value='q'),patch('builtins.print'):self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def answer(prompt):return 'record' if prompt.startswith('Type record') else ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):self.assertEqual(0,main(args))
        with PersonalProjectStore(self.work) as store:key=self.key(store.load())
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','critique-original','--directory',str(self.work),'--id',key]))
        self.assertIn(SECRET,output.getvalue())
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','critique-references','--directory',str(self.work)]))
        self.assertNotIn(SECRET,output.getvalue());self.assertNotIn(key,output.getvalue())

    def test_scientific_edge_cannot_treat_critique_as_confirmed_basis(self):
        from dataclasses import asdict
        from claimbranch.core.review import Judgment
        base=protocol_tests.ProtocolTests.base(self);project,_=self.capture(base);h=project.work.history;stamp=decode(h.commands[-1],purpose='history')['created_at']
        h=h.append(dict(schema_version=4,id='new-alt',project_id=project.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='create-reasoning-branch',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload={}))
        judgment=Judgment.start(project.project_id,'protocol-episode').edit('A tentative interpretation.','The critique is a question, not evidence.')
        changes=[dict(id='I-new',kind='interpretation',body=dict(statement=judgment.text,observation_ids=[self.key(project)])),dict(id='bad-edge',kind='scientific-edge',body=dict(source_id=self.key(project),target_id='T',edge_type='supports',rationale='This must refuse.'))]
        with self.assertRaises(ContractError):h.append(dict(schema_version=4,id='bad-record',project_id=project.project_id,episode_id='protocol-episode',created_at=stamp,operation_type='record-interpretation',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(changes=changes,judgment=asdict(judgment))))

    def test_known_private_original_or_identity_in_question_and_reason_still_omitted_by_default(self):
        project,_=self.capture(question=SECRET+' '+ORIGINAL);project,_=self.link(project,rationale=SECRET+' '+ORIGINAL)
        value=decode(project.payload,purpose='project');projection=placeholder_projection(project.work.history.view('main'),value['public_ids']);text=json.dumps(projection)
        self.assertNotIn(SECRET,text);self.assertNotIn(ORIGINAL,text)
        self.assertEqual('omitted',projection['placeholders'][0]['content'])

    def test_save_source_registry_cannot_drop_add_or_replace_private_original(self):
        project,_=self.capture();value=decode(project.payload,purpose='project')
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview)
            broken=deepcopy(value);broken['critique_sources'][0]['source']['chunks']=['eA==']
            with self.assertRaises(ContractError):ProjectWork(encode(broken,purpose='project'))
            self.assertEqual(project.payload,store.load().payload)
        # Even an empty-command newer envelope may not smuggle orphan private sources.
        empty=decode(self.project.payload,purpose='project');empty['schema']='claimbranch.project-work/v17';empty['work']['schema']='claimbranch.paper-work/v21';empty['critique_sources']=value['critique_sources']
        with self.assertRaisesRegex(ContractError,'orphan'):ProjectWork(encode(empty,purpose='project'))

    def test_changed_exact_input_and_source_refuse_without_persisting_any_original(self):
        from claimbranch.application.cli import main
        project,preview=self.capture();recheck_critique(self.project,preview)
        path=self.root/'critique.json';request=self.request();path.write_text(json.dumps(request));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        before=(self.work/'personal.cbp').read_bytes()
        def answer(prompt):
            if prompt.startswith('Type record'):
                request['payload']['private_identity']='Changed identity';path.write_text(json.dumps(request));return 'record'
            return ''
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'),patch('sys.stderr',new_callable=io.StringIO) as output:self.assertEqual(1,main(['project','critique','--directory',str(self.work),'--input',str(path)]))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes());self.assertNotIn(SECRET,output.getvalue())
        (self.paper/'paper.tex').write_bytes(self.manuscript+b'% changed')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_critique(self.project,preview)

    def test_unknown_and_ai_question_history_remain_in_independent_explanation_policy(self):
        from claimbranch.core.research_history import _reduce,_branch_ai,_branch_uncertain
        for origin in ('ai','mixed','unknown'):
            project,_=self.capture(source_origin=origin);state=_reduce(project.work.history.seed,project.work.history.commands)
            self.assertTrue(_branch_uncertain(state['branches']['main']) if origin=='unknown' else _branch_ai(state['branches']['main'],state))

    def test_actual_pty_capture_fresh_open_and_shipped_old_reader_refusal(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        from types import ModuleType
        path=self.root/'critique.json';path.write_text(json.dumps(self.request()));path.chmod(0o600)
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
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
                            elif b'Type record to keep' in pending:os.write(master,b'record\n');pending=b''
                        elif b'ClaimBranch' in output and not quit_sent:os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-3000:].decode(errors='replace'));self.assertNotIn(SECRET.encode(),output);self.assertNotIn(ORIGINAL.encode(),output)
                if record:self.assertIn(b'Private critique operation saved',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(['project','critique','--directory',str(self.work),'--input',str(path)],True);terminal(['project','open','--directory',str(self.work)])
        old=__import__('pathlib').Path(__file__).with_name('legacy_personal_project.py').read_text();module=ModuleType('claimbranch.application.critique_old');module.__package__='claimbranch.application';exec(compile(old,'old-reader','exec'),module.__dict__)
        raw=(self.work/'personal.cbp').read_bytes()
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_public_export_refuses_and_private_backup_fresh_restore_keep_exact_original_bytes(self):
        from claimbranch.application.cli import main
        project,_=self.capture();before=decode(project.payload,purpose='project')['critique_sources'][0]['source'];raw=source_bytes(before)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        exported=self.root/'forbidden-export';archive=self.root/'private-archive';restored=self.root/'restored'
        for path in (exported,archive,restored):path.mkdir(mode=0o700)
        with patch('sys.stdout',new_callable=io.StringIO),patch('sys.stderr',new_callable=io.StringIO) as error:
            self.assertEqual(1,main(['project','export','--directory',str(self.work),'--archive-directory',str(exported)]))
            self.assertNotIn(SECRET,error.getvalue())
            self.assertEqual(0,main(['project','backup','--directory',str(self.work),'--archive-directory',str(archive)]));self.assertEqual(0,main(['project','restore','--directory',str(restored),'--archive-directory',str(archive)]))
        self.assertFalse((exported/'project.json').exists())
        with PersonalProjectStore(restored) as store:returned=store.load()
        self.assertEqual(project.payload,returned.payload);self.assertEqual(raw,source_bytes(decode(returned.payload,purpose='project')['critique_sources'][0]['source']))

    def test_equivalent_capture_reformatting_is_refused_and_default_inspection_omits_source_hash(self):
        from claimbranch.application.cli import main
        project,_=self.capture();raw=json.dumps(self.request(),sort_keys=True,separators=(',',':')).encode()
        with self.assertRaisesRegex(ContractError,'already retained'):prepare_critique(project,self.request(),original_input=raw)
        q=project.work.history.view('main')['critiques'][self.key(project)]
        self.assertNotIn(q['source_sha256'],str(self.capture()[1]))
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:store.save(project,preview=self.preview)
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','critiques','--directory',str(self.work)]))
        self.assertNotIn(q['source_sha256'],output.getvalue());self.assertNotIn(q['source_id'],output.getvalue())

    def test_critique_to_plan_completed_record_and_reviewed_claim_limitation_stays_inspectable(self):
        project,_=self.capture(protocol_tests.ProtocolTests.base(self));project,_=self.link(project,target='T');project,_=self.link(project,target='P',relation='addressed-by',id='plan-link');project,_=self.link(project,target='X',relation='addressed-by',id='run-link')
        changed,_=prior.ClaimWordingTests.policy(self,project,claim_id='T');operation=changed.work.history.view('main')['wording_policies']['T']['operation_id']
        result,_=self.link(changed,target='T',relation='addressed-by',consequence_operation_id=operation,id='consequence-link')
        links=result.work.history.view('main')['critique_links'];self.assertEqual({'T','P','X'},{l['target_id'] for l in links.values()});self.assertTrue(all(not l['scientific'] and not l['resolved'] for l in links.values()))
        self.assertEqual(project.work.history.view('main')['evidence'],result.work.history.view('main')['evidence'])
        self.assertEqual(SECRET,read_original(split_personal_backup(personal_backup(result)),self.key(result))['original']['payload']['private_identity'])

    def test_unchanged_dependency_in_merge_is_not_a_claim_consequence(self):
        from dataclasses import asdict
        from claimbranch.core.review import Judgment
        base=protocol_tests.ProtocolTests.base(self);project,_=self.capture(base);h=project.work.history;stamp=decode(h.commands[-1],purpose='history')['created_at']
        # New metadata input has unknown origin; preserve that independent review requirement.
        def append(kind,payload,key,episode='protocol-episode'):
            nonlocal h
            h=h.append(dict(schema_version=4,id=key,project_id=project.project_id,episode_id=episode,created_at=stamp,operation_type=kind,expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload))
        j=Judgment.start(project.project_id,'protocol-episode').edit('A limited new claim.','Add the claim with its observation.')
        claim=dict(id='C',kind='claim',body=dict(role='main',statement='A limited synthetic claim.',scope='Synthetic only',parent_ids=['T']))
        interpretation=dict(id='I-new',kind='interpretation',body=dict(statement=j.text,observation_ids=['O']))
        append('create-reasoning-branch',{},'alt');append('record-interpretation',dict(changes=[interpretation,claim],judgment=asdict(j)),'record-claim');append('apply-selected-merge',dict(selected_ids=['C','I-new'],judgment=asdict(j),disposition='deferred',answers=[]),'merge-claim')
        append('close-episode',{},'close-new');append('open-episode',dict(title='Follow-up',question='Which plan follows?'),'open-next','next')
        j=Judgment.start(project.project_id,'next').edit('A follow-up test.','Use the existing claim without changing it.')
        plan=deepcopy(next(c for c in h.view('main')['changes'] if c['id']=='P'));plan['id']='P-next';plan['body']['claim_id']='C'
        interpretation=dict(id='I-next',kind='interpretation',body=dict(statement=j.text,observation_ids=['O']))
        append('create-reasoning-branch',{},'next-alt','next');append('record-interpretation',dict(changes=[interpretation,plan],judgment=asdict(j)),'next-record','next');append('apply-selected-merge',dict(selected_ids=['P-next','I-next'],judgment=asdict(j),disposition='deferred',answers=[]),'merge-plan','next')
        current=project.with_work(PaperWork.create(h))
        with self.assertRaisesRegex(ContractError,'recorded selected'):self.link(current,target='C',relation='addressed-by',consequence_operation_id='merge-plan')
        linked,_=self.link(current,target='C',relation='addressed-by',consequence_operation_id='merge-claim');self.assertEqual('merge-claim',linked.work.history.view('main')['critique_links']['link']['consequence_operation_id'])

    def test_128_critique_capacity_then_overflow_refuses_without_appending(self):
        import hashlib
        from claimbranch.core.research_history import ResearchHistory
        h=self.project.work.history;heads=dict(h.heads);commands=list(h.commands);stamp=decode(h.commands[-1],purpose='history')['created_at']
        for index in range(128):
            command=dict(schema_version=11,id='capture-'+str(index),project_id=self.project.project_id,episode_id='local',created_at=stamp,operation_type='record-critique',expected_heads=dict(heads),evidence_watermark=h.watermark,
                payload=dict(id='critique-'+format(index,'032x'),source_id='private-source-'+format(index,'032x'),source_sha256=hashlib.sha256(str(index).encode()).hexdigest(),source_kind='review',question='Independent synthetic question '+str(index),question_origin='human',source_origin='human'))
            commands.append(encode(command,purpose='history'));heads={'main':command['id']}
        combined=ResearchHistory(h.seed,tuple(commands));self.assertEqual(128,combined.capacity()['resources']['critiques']['used']);original=combined.manifest()
        command.update(id='overflow',expected_heads=dict(combined.heads));command['payload'].update(id='critique-'+'f'*32,source_id='private-source-'+'f'*32)
        with self.assertRaisesRegex(ContractError,'critiques: 129 / 128'):combined.append(command)
        self.assertEqual(original,combined.manifest())

    def test_capture_preview_omits_private_source_reference_and_revision_reasons_survive(self):
        project,preview=self.capture();q=project.work.history.view('main')['critiques'][self.key(project)]
        self.assertNotIn(q['source_id'],str(preview));self.assertNotIn(q['source_sha256'],str(preview))
        def revise(base,text,reason):
            record=base.work.history.view('main')['critiques'][self.key(base)]
            return prepare_critique(base,dict(schema='claimbranch.critique-input/v1',operation_type='revise-critique-question',payload=dict(critique_id=self.key(base),expected_revision_id=record['revision_id'],question=text,question_origin='human',rationale=reason)))[0]
        first=revise(project,'Does the primary definition agree?','Narrow the question to primary units.')
        second=revise(first,'Do grouped units reverse this conclusion?','Keep the sensitivity definition separate.')
        record=second.work.history.view('main')['critiques'][self.key(second)]
        self.assertEqual('Narrow the question to primary units.',record['revisions'][1]['rationale']);self.assertEqual('Keep the sensitivity definition separate.',record['rationale'])
        app=project_workspace(second);app.select(self.key(second));self.assertIn('Narrow the question',str(app.detail()));self.assertIn('Keep the sensitivity',str(app.detail()))
        with self.assertRaisesRegex(ContractError,'mapping is incomplete'):placeholder_projection(second.work.history.view('main'),[])

    def test_prior_claim_change_can_be_referenced_without_fabricating_app_chronology(self):
        # A critique may already exist outside the app; later capture cannot erase prior work.
        changed,_=prior.ClaimWordingTests.policy(self,self.project);cause=changed.work.history.view('main')['wording_policies']['C']['operation_id']
        project,_=self.capture(changed);linked,_=self.link(project,target='C',relation='addressed-by',consequence_operation_id=cause)
        link=linked.work.history.view('main')['critique_links']['link'];self.assertEqual('change-before-app-capture',link['association_timing']);self.assertFalse(link['chronology_verified']);self.assertFalse(link['resolved'])
        app=project_workspace(linked);app.select(self.key(linked));self.assertIn('change-before-app-capture',str(app.detail()))
        with self.assertRaisesRegex(ContractError,'identity reused'):self.link(linked,target='X',relation='addressed-by')
