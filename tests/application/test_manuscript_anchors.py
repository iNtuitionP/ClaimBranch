from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned read-only paper locations; no real manuscript/provider/native key."""
import unittest
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
from application import test_argument_registration as imported_tests
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode, encode
from claimbranch.application.manuscript_anchors import prepare_registration, recheck_registration, inspect_anchor
from claimbranch.application.personal_project import PersonalProjectStore, ANCHOR_PERSONAL_MAGIC
from claimbranch.application.personal_archive import split_personal_backup, ANCHOR_BACKUP_MAGIC
from claimbranch.application.paper_service import PaperService
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui_work_recovery import snapshot_value


class ManuscriptAnchorTests(unittest.TestCase):
    setUp = imported_tests.ImportedProjectTests.setUp

    def register(self, name, kind='text', expresses=('C',), plots=(), parents=(), project=None):
        filename=name+'.tex'
        (self.paper/filename).write_text(f'% claimbranch:start id={name}\nSynthetic {kind} only.\n% claimbranch:end id={name}\n')
        result,preview=prepare_registration(project or self.project,manuscript=filename,anchor_id=name,kind=kind,
            expresses=expresses,plots=plots,parents=parents,rationale='Explicit synthetic manuscript use.')
        return result,preview

    def test_claim_and_observation_reach_all_named_locations_with_witnesses_and_no_parent_inference(self):
        project=self.project
        for name,kind,expresses,plots,parents in [('abstract','text',('C',),(),()),('figure','figure',('C',),('O',),()),('table','table',(),('O',),()),('caption','caption',(),(),('figure',)),('unrelated','text',('T',),(),())]:
            project,_=self.register(name,kind,expresses,plots,parents,project)
        service=PaperService(project.work.history)
        claim=service.anchor_impact(['C'])
        self.assertEqual(['abstract','caption','figure'],claim['potentially_affected_anchor_ids'])
        observation=service.anchor_impact(['O'])
        self.assertEqual(['abstract','caption','figure','table'],observation['potentially_affected_anchor_ids'])
        self.assertIn('unrelated',observation['outside_impact_anchor_ids'])
        self.assertTrue(any(w['node_ids']==['O','figure','caption'] for w in observation['anchor_witness_paths']))
        self.assertEqual(self.manuscript,(self.paper/'paper.tex').read_bytes())

    def test_source_refresh_and_removed_associations_keep_old_reach(self):
        first,_=self.register('abstract')
        old_id=decode(first.work.history.commands[-1],purpose='history')['id']
        second,preview=prepare_registration(first,manuscript='abstract.tex',anchor_id='abstract',kind='text',expresses=[],
            rationale='The claim was removed from this location.')
        impact=PaperService(second.work.history).anchor_impact(['C'],at_operation=old_id)
        self.assertTrue(any(w['anchor_id']=='abstract' and w['phase']=='before' for w in impact['anchor_witness_paths']))
        self.assertFalse(any(w['anchor_id']=='abstract' and w['phase']=='after' for w in impact['anchor_witness_paths']))
        self.assertEqual(first.work.history.seed,second.work.history.seed)
        self.assertEqual(first.work.history.commands,second.work.history.commands[:-1])

    def test_freshness_distinguishes_block_file_and_missing_source_and_stale_registration_refuses(self):
        project,preview=self.register('abstract'); anchor=preview['registration']
        self.assertEqual('unchanged',inspect_anchor(anchor)['status'])
        path=self.paper/'abstract.tex';raw=path.read_bytes();path.write_bytes(b'% unrelated edit\n'+raw)
        self.assertEqual('unchanged-block-file-changed',inspect_anchor(anchor)['status'])
        with self.assertRaisesRegex(ContractError,'source changed'):recheck_registration(self.project,preview)
        path.write_bytes(raw.replace(b'Synthetic text',b'Different text'))
        self.assertEqual('block-changed',inspect_anchor(anchor)['status'])
        path.unlink();self.assertEqual('unavailable-or-unsupported',inspect_anchor(anchor)['status'])
        self.assertIn('abstract',PaperService(project.work.history).anchor_impact(['C'])['potentially_affected_anchor_ids'])

    def test_anchored_frame_writing_prior_origin_and_backup_return(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            app=project_workspace(self.project);app.select('C');app.notes[app.context_key()]='Keep the source limitation.'
            original=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            store.save(original)
            project,_=self.register('abstract',project=original);store.save(project)
            self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC))
            backup=store.backup();self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC))
        restored=split_personal_backup(backup);returned=project_workspace(restored)
        self.assertIn('abstract',returned.nodes)
        self.assertIn('Keep the source limitation.',returned.notes.values())
        self.assertEqual(project.payload,restored.payload)
        returned.select('abstract');self.assertIn('Synthetic text only.',str(returned.detail()))

    def test_duplicate_marker_symlink_bad_endpoint_and_kind_change_refuse(self):
        path=self.paper/'bad.tex';path.write_text('% claimbranch:start id=bad\n% claimbranch:start id=bad\n% claimbranch:end id=bad\n')
        with self.assertRaises(ContractError):prepare_registration(self.project,manuscript='bad.tex',anchor_id='bad',kind='text',rationale='Test')
        project,_=self.register('figure','figure',plots=('O',))
        with self.assertRaisesRegex(ContractError,'immutable'):prepare_registration(project,manuscript='figure.tex',anchor_id='figure',kind='table',rationale='Test')
        with self.assertRaisesRegex(ContractError,'unavailable'):prepare_registration(project,manuscript='figure.tex',anchor_id='figure',kind='figure',expresses=['missing'],rationale='Test')
        (self.paper/'link.tex').symlink_to(self.paper/'figure.tex')
        with self.assertRaises(ContractError):prepare_registration(project,manuscript='link.tex',anchor_id='figure',kind='figure',rationale='Test')

    def test_manual_paper_profile_keeps_seed_and_prior_bytes(self):
        from claimbranch.application.paper_profile_project import new_paper_project
        original=new_paper_project(self.preview,'manual-paper','Synthetic','A manual thesis.','What remains unknown?')
        project,_=self.register('abstract',expresses=('thesis',),project=original)
        self.assertEqual(original.work.history.seed,project.work.history.seed)
        self.assertEqual(original.work.history.commands,project.work.history.commands[:-1])
        self.assertEqual('claimbranch.project-work/v18',decode(project.payload,purpose='project')['schema'])
        self.assertIsNone(decode(project.payload,purpose='project')['import_input_sha256'])

    def test_prior_ai_origin_and_new_reasoning_return_survive_anchor_registration(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            app=project_workspace(self.project);app.recovery=PersonalProjectRecovery(store,app,self.project)
            app.select('C');app.keep_draft('Keep a limited reading.','A rubric is not a verifier.')
            service=PersonalResearch(app)
            service.commit(service.prepare('reasoning',explanation_state='leave-for-later'))
            before=store.load();before_view=PaperService(before.work.history).query('main')
            anchored,_=self.register('abstract',project=before);store.save(anchored)
            historical=PaperService(anchored.work.history).query('main',at_operation=decode(before.work.history.commands[-1],purpose='history')['id'])
            self.assertEqual(before_view['nodes'],historical['nodes'])
            prefix=type(before.work.history)(anchored.work.history.seed,anchored.work.history.commands[:len(before.work.history.commands)])
            self.assertEqual(before_view,PaperService(prefix).query('main'))
            returned=project_workspace(store.load());returned.recovery=PersonalProjectRecovery(store,returned,store.load())
            self.assertEqual(1,len(returned.paper._recorded_origins))
            service=PersonalResearch(returned);service.commit(service.prepare('next',question='What changes next?'))
            returned.select('C');returned.keep_draft('Reconsider the writing claim.','Keep the earlier AI source.')
            returned.review.candidates().put(dict(id='C',kind='claim',body=dict(role='main',statement='A rubric can reward superficial features under these conditions.',scope='Synthetic writing task only',parent_ids=['T'])))
            preview=service.prepare('reasoning',explanation_state='leave-for-later')
            self.assertIn('abstract',preview.display['impact']['potentially_affected_anchor_ids'])
            self.assertTrue(preview.display['ai_origin_retained'])
            service.commit(preview)
            self.assertEqual(2,len(project_workspace(split_personal_backup(store.backup())).paper._recorded_origins))

    def test_intervening_source_edit_refuses_personal_commit_and_preserves_writing(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        anchored,_=self.register('abstract')
        with PersonalProjectStore.create(self.work,project_id=anchored.project_id) as store:
            # Fresh store creation still checks its original paper association.
            store.save(anchored,preview=self.preview)
            app=project_workspace(anchored);app.recovery=PersonalProjectRecovery(store,app,anchored)
            app.select('C');app.keep_draft('Keep the limitation.','The registered source must not drift.')
            service=PersonalResearch(app);preview=service.prepare('reasoning',explanation_state='leave-for-later')
            previous=(self.work/'personal.cbp').read_bytes()
            path=self.paper/'abstract.tex';path.write_text(path.read_text().replace('Synthetic','Changed'))
            with self.assertRaisesRegex(ContractError,'changed or expired'):service.commit(preview)
            self.assertEqual(previous,(self.work/'personal.cbp').read_bytes())
            self.assertIn('Keep the limitation.',str(snapshot_value(app)))

    def test_exact_capacity_invalid_encoding_and_scientific_identity_collision(self):
        from copy import deepcopy
        anchored,preview=self.register('abstract')
        base=self.project.work.history
        def cmd(payload,key):
            return dict(schema_version=6,id=key,project_id='synthetic-paper',episode_id='local',
                created_at='2026-10-14T00:00:00Z',operation_type='register-manuscript-anchor',expected_heads=dict(base.heads),
                evidence_watermark=base.watermark,payload=payload)
        bad=deepcopy(preview['registration']);bad['block']=['A']
        with self.assertRaises(ContractError):base.append(cmd(bad,'bad-encoding'))
        bad=deepcopy(preview['registration']);bad['id']='C';bad['source']['anchor_id']='C'
        with self.assertRaisesRegex(ContractError,'aliases'):base.append(cmd(bad,'bad-identity'))
        from claimbranch.core.research_history import _reduce,_register_anchor
        state=deepcopy(_reduce(base.seed,base.commands))
        for i in range(63):
            payload=deepcopy(preview['registration']);payload['id']=f'location-{i}';payload['source']['anchor_id']=payload['id']
            _register_anchor(state,payload)
        payload=deepcopy(preview['registration']);payload['id']='overflow';payload['source']['anchor_id']='overflow'
        with self.assertRaisesRegex(ContractError,'capacity anchors: 65 / 64'):_register_anchor(state,payload)
        self.assertEqual(self.project.work.history.manifest(),base.manifest())

    def test_large_selected_file_and_multi_chunk_block_read_exactly(self):
        path=self.paper/'large.tex';block=('αβγ '+('z'*80)+'\n')*180
        path.write_text('% outside coverage\n'*6000+'% claimbranch:start id=large\n'+block+'% claimbranch:end id=large\n')
        self.assertGreater(path.stat().st_size,65536)
        result,preview=prepare_registration(self.project,manuscript='large.tex',anchor_id='large',kind='text',expresses=['C'],rationale='Large explicitly selected block.')
        app=project_workspace(result);app.select('large')
        self.assertEqual(block,preview['marked_text'])
        self.assertIn(block.strip(),'\n'.join(row[0] for row in app.detail()))


    def test_public_registration_cancel_stale_confirmation_and_query(self):
        from claimbranch.application.cli import main
        class TTY(io.StringIO):
            def isatty(self): return True
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
        (self.paper/'abstract.tex').write_text('% claimbranch:start id=abstract\nSynthetic text only.\n% claimbranch:end id=abstract\n')
        args=['project','anchor-register','--directory',str(self.work),'--manuscript','abstract.tex','--anchor','abstract','--kind','text','--expresses','C','--reason','Synthetic manuscript use']
        previous=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdin',TTY()),patch('sys.stdout',TTY()),patch('builtins.input',return_value=''):
            self.assertEqual(0,main(args))
        self.assertEqual(previous,(self.work/'personal.cbp').read_bytes())
        def answer(_):
            path=self.paper/'abstract.tex';path.write_text(path.read_text().replace('Synthetic','Changed'))
            return 'register'
        with patch('sys.stdin',TTY()),patch('sys.stdout',TTY()),patch('sys.stderr',TTY()),patch('builtins.input',side_effect=answer):
            self.assertEqual(1,main(args))
        self.assertEqual(previous,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin',TTY()),patch('sys.stdout',TTY()),patch('builtins.input',return_value='register'):
            self.assertEqual(0,main(args))
        output=io.StringIO()
        with patch('sys.stdout',output):self.assertEqual(0,main(['project','anchor-impact','--directory',str(self.work),'--nodes','C']))
        self.assertEqual(['abstract'],json.loads(output.getvalue())['potentially_affected_anchor_ids'])

    def test_actual_terminal_registration_plot_and_caption_navigation_then_fresh_open(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        (self.paper/'figure.tex').write_text('% claimbranch:start id=figure\nSynthetic measured plot reference.\n% claimbranch:end id=figure\n')
        arguments=['project','anchor-register','--directory',str(self.work),'--manuscript','figure.tex','--anchor','figure','--kind','figure','--expresses','C','--plots','O','--reason','Synthetic explicit use.']
        def terminal(args,registration=False):
            master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
            process=subprocess.Popen([sys.executable,'-m','claimbranch',*args],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'))
            os.close(slave);output=b'';pending=b'';quit_sent=False;deadline=time.monotonic()+25
            try:
                while process.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        output+=chunk;pending+=chunk
                        if registration:
                            if b'Enter: next page' in pending:os.write(master,b'\n');pending=b''
                            elif b'Type register to save' in pending:os.write(master,b'register\n');pending=b''
                        elif b'ClaimBranch' in output and not quit_sent:os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-3000:].decode(errors='replace'))
                if registration:self.assertIn(b'Manuscript anchors saved',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(arguments,True);terminal(['project','open','--directory',str(self.work)])
        with PersonalProjectStore(self.work) as store:
            returned=project_workspace(store.load());returned.select('O')
            from claimbranch.application.tui_graph import relation_phrase
            plots=[e for e in returned.view['relations'] if e['type']=='plots']
            self.assertEqual(1,len(plots));self.assertIn('declared in',relation_phrase(plots[0],'O','figure'))
            self.assertEqual(['figure'],returned.service.anchor_impact(['O'])['potentially_affected_anchor_ids'])

    def test_older_frame_reader_refuses_without_changing_checkpoint(self):
        import subprocess
        from types import ModuleType
        anchored,_=self.register('abstract')
        with PersonalProjectStore.create(self.work,project_id=anchored.project_id) as store:store.save(anchored,preview=self.preview)
        raw=(self.work/'personal.cbp').read_bytes()
        old=__import__('pathlib').Path(__file__).with_name('legacy_personal_project.py').read_text()
        module=ModuleType('claimbranch.application.anchor_old_reader');module.__package__='claimbranch.application'
        exec(compile(old,'legacy-personal-project','exec'),module.__dict__)
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_strict_schema_and_global_inactive_observations_are_not_hidden(self):
        from copy import deepcopy
        from claimbranch.core.research_history import _register_anchor,_reduce
        project,preview=self.register('figure','figure',plots=('O',))
        for field,value in [('expresses',['C','C']),('kind','Figure'),('block',[123])]:
            payload=deepcopy(preview['registration']);payload[field]=value
            with self.assertRaises(ContractError):_register_anchor(deepcopy(_reduce(project.work.history.seed,project.work.history.commands)),payload)
        h=project.work.history;event=h.view('main')['evidence'][0]['history'][-1]['event_id']
        h=h.append(dict(schema_version=5,id='invalidate-o',project_id='synthetic-paper',episode_id='local',created_at='2026-10-14T23:59:59Z',operation_type='record-evidence-event',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=dict(event_id='invalid-o',target_id='O',run_id='X',action='invalidate',statement=None,value=None,rationale='Synthetic source invalidation.',supersedes_id=event)))
        view=PaperService(h).query('main');self.assertIn('O',{n['id'] for n in view['nodes']})
        self.assertIn('figure',PaperService(h).anchor_impact(['O'])['potentially_affected_anchor_ids'])
        with self.assertRaises(ContractError):PaperService(h).anchor_impact(['missing'])


    def test_untyped_seed_kind_is_explicit_then_immutable_and_blank_before_refuses(self):
        first,preview=prepare_registration(self.project,manuscript='paper.tex',anchor_id='anchor',kind='figure',plots=['O'],rationale='First explicit seed kind.')
        self.assertEqual('figure',first.work.history.view('main')['manuscript_anchors']['anchor']['kind'])
        caption,_=self.register('caption',kind='caption',expresses=(),parents=('anchor',),project=first)
        self.assertIn('caption',PaperService(caption.work.history).anchor_impact(['O'])['potentially_affected_anchor_ids'])
        with self.assertRaisesRegex(ContractError,'immutable'):prepare_registration(first,manuscript='paper.tex',anchor_id='anchor',kind='text',rationale='Invalid kind change.')
        with self.assertRaises(ContractError):PaperService(first.work.history).anchor_impact(['O'],at_operation='')
