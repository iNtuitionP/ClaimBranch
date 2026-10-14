"""Whole-paper limits, unchanged legacy contracts and private return boundaries."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from application.paper_capacity_fixture import combined
from claimbranch.core.canonical import ContractError, canonical_bytes, decode as legacy_decode
from claimbranch.core.paper_capacity import encode, decode, source_record, source_bytes
from claimbranch.core.research_history import ResearchHistory
from claimbranch.application.cli import main
from claimbranch.application.paper_profile_project import new_paper_project, convert_paper_project
from claimbranch.application.paper_work_store import PaperWork, WorkReopenRequired
from claimbranch.application.project_work import ProjectWork, preview_association
from claimbranch.application.personal_project import PersonalProjectStore, PERSONAL_MAGIC, PAPER_PERSONAL_MAGIC
from claimbranch.application.personal_archive import personal_backup, split_personal_backup, PAPER_BACKUP_MAGIC
from claimbranch.application.paper_service import PaperService
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_project import prepare_project, project_workspace
from claimbranch.application.tui_work_recovery import snapshot_value

ROOT = Path(__file__).resolve().parents[2]


class PaperCapacityTests(unittest.TestCase):
    def test_legacy_sized_lifecycle_wording_fingerprint_is_byte_identical(self):
        from claimbranch.core.canonical import digest
        from claimbranch.application.paper_wording_snapshot import fingerprint
        history = ResearchHistory.start_lifecycle('fingerprint-paper', 'Synthetic paper', 'T', 'Retain the scientific reason.', 'anchor')
        expected = digest({'seed':legacy_decode(history.seed), 'commands':[]})
        self.assertEqual(expected, fingerprint(history))
        history = history.append(dict(schema_version=4, id='open', project_id='fingerprint-paper', episode_id='episode',
            created_at='2026-10-13T00:00:00Z', operation_type='open-episode', expected_heads=dict(history.heads),
            evidence_watermark=0, payload=dict(title='New question',question='What should be tested?')))
        expected = digest({'seed':legacy_decode(history.seed), 'commands':[legacy_decode(c) for c in history.commands]})
        self.assertEqual(expected, fingerprint(history))

    @classmethod
    def setUpClass(cls):
        cls.seed,cls.commands = combined()
        cls.history = ResearchHistory(cls.seed,cls.commands)

    def test_combined_maxima_replay_deterministically_without_legacy_codec_expansion(self):
        h=self.history; resources=h.capacity()['resources']
        for name, maximum in dict(claims=64,observations=256,experiments=256,edges=512,plans=64,episodes=32,events=1024,interpretations=32).items():
            self.assertEqual((maximum,maximum,0),tuple(resources[name][key] for key in ('used','limit','remaining')))
        self.assertEqual(h.manifest(),ResearchHistory(h.seed,h.commands).manifest())
        self.assertFalse(h.authorization_verified)
        with self.assertRaises(ContractError): legacy_decode(h.manifest())
        with self.assertRaises(ContractError): canonical_bytes(list(range(129)))

    def test_collection_and_count_overflow_names_limits_before_any_append(self):
        original=self.history.manifest()
        command=decode(self.commands[-1],purpose='history')
        command.update(id='event-overflow',operation_type='record-evidence-event',expected_heads=dict(self.history.heads),evidence_watermark=1024)
        command['payload']=dict(event_id='extra-event',target_id='observation-0',run_id='run-0',action='correct',statement='New reading',value='1',rationale='Explicit correction',supersedes_id='correction-512')
        with self.assertRaisesRegex(ContractError,'capacity events: 1025 / 1024'):self.history.append(command)
        self.assertEqual(original,self.history.manifest())
        for name, arguments, expected in (
            ('claims',dict(claims=64),65),('edges',dict(edges=513),513),('plans',dict(plans=65),65),
            ('experiments',dict(counts=257,corrections=False),257),('episodes',dict(episodes=33),33)):
            with self.subTest(name=name),self.assertRaisesRegex(ContractError,'capacity '+name+': '+str(expected)+' /'):
                ResearchHistory(*combined(**arguments))

    def test_observation_cap_is_independent_of_event_headroom(self):
        h=ResearchHistory(*combined(corrections=False,episodes=1))
        cmd=decode(h.commands[-1],purpose='history')
        cmd.update(id='extra-confirm',operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark)
        cmd['payload']=dict(event_id='extra-event',target_id='observation-extra',run_id='run-0',action='confirm',statement='Another result',value='1',rationale='Separate source',supersedes_id=None)
        with self.assertRaisesRegex(ContractError,'capacity observations: 257 / 256'): h.append(cmd)

    def test_command_cap_and_exact_retry_are_independent_of_scientific_counts(self):
        seed,commands=combined(corrections=False,counts=1,episodes=1,edges=1,claims=1,plans=1)
        commands=list(commands[:-1])  # stay on the unmerged alternative
        template=decode(commands[-1],purpose='history')
        last=template['id']
        while len(commands)<2048:
            value=deepcopy(template);value['id']='repeat-%s'%len(commands)
            value['expected_heads']['alternative']=last
            commands.append(encode(value,purpose='history'));last=value['id']
        history=ResearchHistory(seed,tuple(commands))
        self.assertIs(history,history.append(decode(commands[-1],purpose='history')))
        value=deepcopy(template);value['id']='overflow';value['expected_heads']=dict(history.heads)
        with self.assertRaisesRegex(ContractError,'capacity commands: 2049 / 2048'):history.append(value)

    def test_public_views_and_episode_metadata_cannot_poison_replay_caches(self):
        h=self.history;original=h.manifest()
        view=h.view('main');view['claims'][0]['statement']='Poisoned claim'
        view['changes'][0]['body']['statement']='Poisoned change'
        view['evidence'][0]['history'][0]['rationale']='Poisoned evidence'
        h.episodes()[0]['baseline_heads']['main']='poisoned-head'
        self.assertNotIn('Poisoned',str(h.view('main')))
        self.assertNotEqual('poisoned-head',h.episodes()[0]['baseline_heads']['main'])
        self.assertEqual(original,h.manifest())

    def test_new_workspace_build_does_not_mutate_legacy_schema(self):
        from claimbranch.application.paper_workspace_snapshot import workspace_schema
        before=json.dumps(workspace_schema(12),sort_keys=True)
        workspace_schema(13)
        self.assertEqual(before,json.dumps(workspace_schema(12),sort_keys=True))

    def test_unknown_profile_and_arbitrary_limits_refuse(self):
        seed=legacy_decode(self.seed)
        for key,value in (('profile','unbounded'),('limits',{'claims':9999})):
            changed={**seed,key:value}
            with self.assertRaises(ContractError):ResearchHistory(canonical_bytes(changed))

    def test_history_and_derived_manifest_budgets_refuse_without_truncation(self):
        for padding, limit in ((900,'manifest-bytes'),(5000,'history-bytes')):
            commands=[]
            for raw in self.commands:
                value=decode(raw,purpose='history')
                if value['operation_type']=='record-evidence-event':value['payload']['rationale']+=' x'*padding
                commands.append(encode(value,purpose='history'))
            with self.subTest(limit=limit),self.assertRaisesRegex(ContractError,limit):ResearchHistory(self.seed,tuple(commands))

    def test_sources_roundtrip_non_nfc_large_bytes_and_refuse_changed_or_excessive_chunks(self):
        raw=('e\u0301 原文\n'*6000).encode()+b'\x00\xff'
        record=source_record(raw)
        self.assertGreater(len(raw),16384)
        self.assertEqual(raw,source_bytes(decode(encode(record,purpose='project'),purpose='project')))
        bad=deepcopy(record);bad['bytes']+=1
        with self.assertRaises(ContractError):source_bytes(bad)
        with self.assertRaises(ContractError):source_record(b'x'*(4194304+1))

    def test_large_context_is_readable_but_selected_ai_context_keeps_original_boundaries(self):
        service=PaperService(self.history);view=service.query()
        self.assertGreater(len(view['nodes']),128)
        request=dict(schema_version=1,project_id='capacity-paper',episode_id=view['episode_id'],ref='main',view_digest=view['digest'],purpose='Inspect the synthetic thesis only',
                     selections=[{'record_id':'thesis','fields':['statement','scope']}],scientific_edge_ids=[])
        # Use exactly the closed public request vocabulary from the example.
        from claimbranch.application.paper_example import context_request
        request=context_request(service)
        request['selections']=[{'record_id':'thesis','fields':['statement','scope']}]
        request['scientific_edge_ids']=[]
        bundle=service.compile_context(request)
        payload=legacy_decode(bundle.payload)
        self.assertLess(len(bundle.payload),262144)
        self.assertEqual(['thesis'],[r['id'] for r in payload['records']])
        with self.assertRaises(ContractError):self.history.prepare_merge_review({},manuscript_digest='a'*64,session_nonce='n',sealed_at=0,expires_at=1)


class PaperProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else None)
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.paper=self.root/'paper';self.paper.mkdir();self.work=self.root/'work';self.work.mkdir(mode=0o700)
        subprocess.run(['/usr/bin/git','init','-q',str(self.paper)],check=True)
        self.source=b'% claimbranch:start id=anchor\nSynthetic only.\n% claimbranch:end id=anchor\n'
        (self.paper/'paper.tex').write_bytes(self.source)
        self.preview=preview_association(self.paper,'paper.tex','anchor',self.work)
        self.project=new_paper_project(self.preview,'my-paper','Paper','Working thesis','What differs?')

    def save(self,project=None):
        with PersonalProjectStore.create(self.work,project_id='my-paper') as store:store.save(project or self.project,preview=self.preview)
        return self.work/'personal.cbp'

    def test_new_frames_small_restart_and_backup_keep_writing_and_no_manifest_duplicate(self):
        app=project_workspace(self.project);app.keep_note('내 관찰의 범위');app.keep_draft('아직 미완성','판단 이유')
        project=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        path=self.save(project)
        self.assertTrue(path.read_bytes().startswith(PAPER_PERSONAL_MAGIC))
        self.assertLess(len(path.read_bytes()),262144)
        self.assertNotIn('manifest',decode(project.payload,purpose='project')['work'])
        code="""import sys,json
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.tui_project import project_workspace
with PersonalProjectStore(sys.argv[1]) as s:
 p=s.load();a=project_workspace(p);print(json.dumps([a.note(),a.draft()['text'],p.work.history.schema_version],ensure_ascii=False))
"""
        result=subprocess.run([sys.executable,'-E','-s','-B','-c',code,str(self.work)],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual((0,''),(result.returncode,result.stderr));self.assertEqual(['내 관찰의 범위','아직 미완성',4],json.loads(result.stdout))
        raw=personal_backup(project);self.assertTrue(raw.startswith(PAPER_BACKUP_MAGIC))
        dest=self.root/'restored';dest.mkdir(mode=0o700)
        PersonalProjectStore.restore_backup(raw,dest)
        with PersonalProjectStore(dest) as s:self.assertEqual(project.payload,s.load().payload)
        self.assertEqual(project.payload,split_personal_backup(raw).payload)
        self.assertEqual(self.source,(self.paper/'paper.tex').read_bytes())

    def test_save_failure_conflict_and_lock_refuse_without_losing_originals(self):
        path=self.save();before=path.read_bytes()
        with PersonalProjectStore(self.work) as store:
            with self.assertRaises(ContractError):
                with PersonalProjectStore(self.work):pass
            app=project_workspace(store.load());app.keep_note('Keep live writing')
            updated=store.load().with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            with patch('claimbranch.application.paper_work_store.os.replace',side_effect=OSError('disk full')):
                with self.assertRaises(ContractError):store.save(updated)
            self.assertEqual(before,path.read_bytes());self.assertEqual('Keep live writing',app.note())
            path.write_bytes(before+b'outside change');path.chmod(0o600)
            with self.assertRaises(WorkReopenRequired):store.save(updated)
        self.assertEqual(before+b'outside change',path.read_bytes())

    def test_interrupted_directory_sync_reports_uncertain_save_and_restores_no_review(self):
        path=self.save()
        with PersonalProjectStore(self.work) as store:
            app=project_workspace(store.load());app.keep_note('Preserve after interrupted sync')
            updated=store.load().with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            sync=store._sync
            def fail(descriptor):
                if descriptor==store._dir:raise OSError('interrupted directory sync')
                return sync(descriptor)
            with patch.object(store,'_sync',side_effect=fail):
                with self.assertRaises(WorkReopenRequired):store.save(updated)
            with self.assertRaises(WorkReopenRequired):store.save(updated)
        with PersonalProjectStore(self.work) as store:
            app=project_workspace(store.load())
            self.assertEqual('Preserve after interrupted sync',app.note())
            self.assertFalse(app.paper.ai_available)
        self.assertTrue(path.read_bytes().startswith(PAPER_PERSONAL_MAGIC))

    def test_sources_and_public_id_mapping_survive_save_and_refuse_erasure(self):
        raw=('e\u0301 source '*4000).encode()
        value=decode(self.project.payload,purpose='project');value['sources']=[source_record(raw)]
        project=ProjectWork(encode(value,purpose='project'));self.save(project)
        with PersonalProjectStore(self.work) as store:
            p=store.load();self.assertEqual(raw,source_bytes(decode(p.payload,purpose='project')['sources'][0]))
            app=project_workspace(p);app.keep_note('New writing')
            new=p.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            self.assertEqual(value['public_ids'],decode(new.payload,purpose='project')['public_ids'])
            bad=decode(new.payload,purpose='project');bad['sources']=[]
            with self.assertRaises(ContractError):store.save(ProjectWork(encode(bad,purpose='project')))

    def test_explicit_conversion_preserves_legacy_science_writing_and_source(self):
        old=prepare_project(self.preview,project_id='my-paper',title='Paper',thesis='Working thesis',question='What differs?')
        app=project_workspace(old);app.keep_note('Original note');app.keep_draft('My thought','My reason')
        old=old.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        path=self.save(old);before=path.read_bytes()
        converted=convert_paper_project(old,before)
        self.assertEqual('Original note',project_workspace(converted).note())
        self.assertEqual('My thought',project_workspace(converted).draft()['text'])
        self.assertEqual(before,source_bytes(decode(converted.payload,purpose='project')['sources'][0]))
        self.assertEqual(before,path.read_bytes())
        dest=self.root/'new';dest.mkdir(mode=0o700)
        with redirect_stdout(io.StringIO()),patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value=''):
            self.assertEqual(0,main(['project','convert-profile','--directory',str(self.work),'--destination',str(dest)]))
        self.assertEqual([],list(dest.iterdir()))
        with redirect_stdout(io.StringIO()),patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value='convert'):
            self.assertEqual(0,main(['project','convert-profile','--directory',str(self.work),'--destination',str(dest)]))
        with PersonalProjectStore(dest) as store:self.assertEqual(4,store.load().work.history.schema_version)
        self.assertEqual(before,path.read_bytes())

    def test_shipped_old_reader_rejects_small_large_near_budget_and_backup_frames(self):
        import tarfile
        artifact=subprocess.run(['/usr/bin/git','archive','HEAD'],cwd=ROOT,capture_output=True,check=True).stdout
        reader=self.root/'shipped-old-reader';reader.mkdir()
        with tarfile.open(fileobj=io.BytesIO(artifact),mode='r:') as archive:archive.extractall(reader,filter='data')
        small=self.project
        large=ProjectWork.create(PaperWork.create(ResearchHistory(*combined())),self.preview)
        maximum=decode(large.payload,purpose='project')
        maximum['sources']=[source_record(bytes([i])* (3500*1024)) for i in range(3)]
        near_budget=ProjectWork(encode(maximum,purpose='project'))
        self.assertGreater(len(near_budget.payload),14*1024*1024)
        from claimbranch.application.personal_project import _PersonalCodec
        for index,project in enumerate((small,large,near_budget)):
            for backup in (False,True):
                directory=self.root/('reader-case-%s-%s'%(index,backup));directory.mkdir(mode=0o700)
                name='backup.cbp' if backup else 'personal.cbp'
                raw=personal_backup(project) if backup else _PersonalCodec().seal(project.payload)
                path=directory/name;path.write_bytes(raw);path.chmod(0o600)
                if backup:
                    code="import sys;from claimbranch.application.personal_archive import PersonalArchive\nwith PersonalArchive(sys.argv[1]) as a:a.read()"
                    args=['-c',code,str(directory)]
                else:args=['-m','claimbranch','project','status','--directory',str(directory),'--json']
                result=subprocess.run([sys.executable,'-E','-s','-B',*args],cwd=reader,capture_output=True,text=True,timeout=15)
                self.assertNotEqual(0,result.returncode,result.stdout)
                self.assertEqual(raw,path.read_bytes())
                self.assertEqual({name} if backup else {name,'work.lock'},set(p.name for p in directory.iterdir()))
                if not backup:
                    import fcntl
                    with (directory/'work.lock').open('rb') as lock:
                        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                        self.assertEqual(b'',lock.read())
                        fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def test_project_aggregate_overflow_and_frame_downgrade_are_refused(self):
        value=decode(self.project.payload,purpose='project')
        value['sources']=[source_record(bytes([i])*4194304) for i in range(3)]
        with self.assertRaisesRegex(ContractError,'project-bytes'):encode(value,purpose='project')
        from claimbranch.application.personal_project import _PersonalCodec
        with self.assertRaisesRegex(ContractError,'frame/profile mismatch'):_PersonalCodec().open(PERSONAL_MAGIC+self.project.payload)

    def test_known_ai_contribution_is_preserved_in_conversion_and_replay(self):
        from dataclasses import asdict
        from claimbranch.core.review import Judgment,Proposal
        old=prepare_project(self.preview,project_id='my-paper',title='Paper',thesis='Working thesis',question='What differs?')
        app=project_workspace(old);session=app.paper.draft(app.episode_id,'main','thesis')
        proposal=Proposal('synthetic-ai','my-paper',app.episode_id,'A synthetic suggested reading.','a'*64)
        judgment=Judgment.start('my-paper',app.episode_id).use_proposal(proposal).edit('Human edited this reading.','My explicit reason')
        session._judgment=judgment;session._text=judgment.text;session._rationale=judgment.rationale;session._prior_dispatches=1
        old=old.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        from claimbranch.application.personal_project import _PersonalCodec
        converted=convert_paper_project(old,_PersonalCodec().seal(old.payload))
        restored=project_workspace(converted)
        later=restored.paper.draft(restored.episode_id,'main','thesis')._judgment
        self.assertEqual(judgment,later);self.assertTrue(later.ai_influenced)

    def test_capacity_notice_preserves_restore_notice_and_provider_refuses_before_open(self):
        app=project_workspace(self.project)
        project=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        from claimbranch.application.tui_work_recovery import restore as real_restore
        def noticed(app,work):
            real_restore(app,work);app.message='Original restored writing notice.'
        with patch('claimbranch.application.tui_project.restore',side_effect=noticed):
            reopened=project_workspace(project)
        self.assertIn('Original restored writing notice.',reopened.message)
        self.assertIn('Paper capacity:',reopened.message)
        self.save(project)
        with redirect_stdout(io.StringIO()),patch('claimbranch.application.provider_commands.PersonalProviderConnection',side_effect=AssertionError('provider opened')):
            self.assertEqual(1,main(['project','open','--directory',str(self.work),'--provider-directory',str(self.root/'missing-config')]))

    def test_doctor_and_status_report_used_limit_and_remaining(self):
        self.save()
        for args in (['doctor','--directory',str(self.work),'--json'],['project','status','--directory',str(self.work),'--json']):
            with redirect_stdout(io.StringIO()) as out:self.assertEqual(0,main(args))
            result=json.loads(out.getvalue());self.assertEqual({'used':1,'limit':64,'remaining':63},result['capacity']['resources']['claims'])

    def test_large_project_reopens_without_serializing_the_derived_manifest(self):
        history=ResearchHistory(*combined())
        large=ProjectWork.create(PaperWork.create(history),self.preview)
        # this test uses its fixture project identity explicitly
        with PersonalProjectStore.create(self.work,project_id=large.project_id) as store:store.save(large,preview=self.preview)
        with PersonalProjectStore(self.work) as store:
            restored=store.load();app=project_workspace(restored)
            self.assertEqual(256,len(restored.work.history.view('main')['evidence']))
            app.keep_note('The maximum graph remains readable')
            updated=restored.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            store.save(updated)
            self.assertIn('maximum graph',project_workspace(store.load()).note())
        self.assertEqual(1024,restored.work.history.watermark)
