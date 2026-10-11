"""Whole saved personal work, original-preserving rescue and public commands."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import unittest

from claimbranch.application.cli import main
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.personal_archive import PersonalArchive, PersonalExport, split_personal_backup
from claimbranch.application.tui_project import project_workspace
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from tests.application import test_personal_research as fixture


class PersonalArchiveTests(unittest.TestCase):
    setUp=fixture.PersonalResearchTests.setUp
    result=fixture.PersonalResearchTests.result
    confirm_result=fixture.PersonalResearchTests.confirm_result
    author=fixture.PersonalResearchTests.author

    def folder(self,name):
        path=self.directory.parent/name
        path.mkdir(mode=0o700)
        return path

    def invoke(self,*args):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err): code=main(['project',*args])
        return code,out.getvalue(),err.getvalue()

    def complete_work(self):
        observation=self.confirm_result(); self.author(observation)
        self.research.commit(self.research.prepare('reasoning'))
        self.research.commit(self.research.prepare('next',question='Does another device reproduce this?'))
        self.app.keep_note('A separate note with 한글')
        self.app.unfinished[(*self.app.context_key(),'note')]=['Unfinished 한글']
        self.app.recovery.save(self.app)
        return self.store.load()

    def test_public_status_backup_export_restore_whole_saved_work_without_terminal(self):
        project=self.complete_work(); original=(self.directory/'personal.cbp').read_bytes()
        self.app.keep_note('Unsaved newer text must not enter backup')
        self.store.close()
        archive,export,destination=self.folder('backup'),self.folder('export'),self.folder('restored')
        for action,extra in [('status',[]),('backup',['--archive-directory',str(archive)]),
                             ('export',['--archive-directory',str(export)])]:
            code,out,err=self.invoke(action,'--directory',str(self.directory),'--json',*extra)
            self.assertEqual((0,''),(code,err)); value=json.loads(out)
            self.assertFalse(value['authorization_verified'])
            self.assertFalse(value['encrypted'])
            self.assertEqual(hashlib.sha256(project.payload).hexdigest(),value['saved_digest'])
        self.assertEqual(project.payload,canonical_bytes(json.loads((export/'project.json').read_text())))
        before=list(destination.iterdir())
        code,out,err=self.invoke('restore','--directory',str(destination),'--archive-directory',str(archive),'--dry-run','--json')
        self.assertEqual((0,''),(code,err)); self.assertEqual(before,list(destination.iterdir()))
        absent=self.paper.with_name('removed-paper')
        self.paper.rename(absent)
        code,out,err=self.invoke('restore','--directory',str(destination),'--archive-directory',str(archive),'--json')
        self.assertEqual((0,''),(code,err)); self.assertFalse(json.loads(out)['authorization_verified'])
        with PersonalProjectStore(destination) as store:
            restored=store.load(); self.assertEqual(project.payload,restored.payload)
            app=project_workspace(restored)
            self.assertIn(['Unfinished 한글'],app.unfinished.values())
            self.assertIn('A separate note with 한글',app.notes.values())
            self.assertNotIn('Unsaved newer text must not enter backup',app.notes.values())
            self.assertTrue(app.service.pending_work()['items'])
            self.assertFalse(restored.work.history.authorization_verified)
        self.assertEqual(original,(self.directory/'personal.cbp').read_bytes())
        self.assertEqual(self.source,(absent/'paper.tex').read_bytes())
        self.assertEqual(0o600,(archive/'backup.cbp').stat().st_mode&0o777)
        self.assertEqual(0o600,(export/'project.json').stat().st_mode&0o777)

    def test_corrupt_newer_wrong_project_and_export_are_not_restore_backups(self):
        backup=self.store.backup(); project=self.store.load()
        destination=self.folder('new')
        changed=bytearray(backup); changed[-1]^=1
        for raw in (bytes(changed),backup[:-1],b'CBPB\0\2'+backup[6:],project.payload):
            with self.subTest(raw=raw[:6]):
                with self.assertRaises(ContractError):
                    PersonalProjectStore.restore_backup(raw,destination)
                self.assertEqual([],list(destination.iterdir()))
        with self.assertRaises(ContractError):
            PersonalProjectStore.restore_backup(backup,destination,project_id='different-project')
        self.assertEqual([],list(destination.iterdir()))
        inner=decode(project.payload); inner['schema']='claimbranch.project-work/v999'
        from claimbranch.application.personal_project import PERSONAL_MAGIC
        body=PERSONAL_MAGIC+canonical_bytes(inner)
        forged=backup[:6]+hashlib.sha256(body).digest()+body
        with self.assertRaises(ContractError): PersonalProjectStore.restore_backup(forged,destination)
        self.assertEqual([],list(destination.iterdir()))

    def test_corrupt_original_is_preserved_while_backup_restores_changed_source_context(self):
        project=self.complete_work(); raw=self.store.backup(); self.store.close()
        damaged=b'Damaged original must stay available for inspection'
        (self.directory/'personal.cbp').write_bytes(damaged)
        changed=self.source.replace(b'Undecided.',b'Edited outside ClaimBranch.')
        (self.paper/'paper.tex').write_bytes(changed)
        archive=self.folder('rescue-backup')
        with PersonalArchive(archive) as destination: destination.write(raw)
        code,_,err=self.invoke('restore','--directory',str(self.directory),'--archive-directory',str(archive))
        self.assertEqual(1,code); self.assertTrue(err)
        restored=self.folder('rescued')
        code,out,err=self.invoke('restore','--directory',str(restored),'--archive-directory',str(archive),'--json')
        self.assertEqual((0,''),(code,err))
        self.assertEqual('source-changed-reconciliation-required',json.loads(out)['source_status'])
        with PersonalProjectStore(restored) as store:
            self.assertEqual(project.payload,store.load().payload)
            app=project_workspace(store.load())
            self.assertIn(['Unfinished 한글'],app.unfinished.values())
        self.assertEqual(damaged,(self.directory/'personal.cbp').read_bytes())
        self.assertEqual(changed,(self.paper/'paper.tex').read_bytes())

    def test_copy_is_create_only_and_private_links_never_overwrite(self):
        raw=self.store.backup(); folder=self.folder('copy')
        with PersonalArchive(folder) as archive:
            archive.write(raw); self.assertEqual(raw,archive.read())
            with self.assertRaises(ContractError): archive.write(raw)
        with self.assertRaises(ContractError): PersonalProjectStore.restore_backup(raw,self.directory)
        target=self.folder('target')/'keep'; target.write_bytes(b'keep')
        for kind in ('symlink','hardlink','public','git'):
            path=self.folder(kind)
            if kind=='symlink': (path/'backup.cbp').symlink_to(target)
            elif kind=='hardlink': os.link(target,path/'backup.cbp')
            elif kind=='public': path.chmod(0o755)
            else: (path/'.git').mkdir()
            with self.assertRaises(ContractError):
                with PersonalArchive(path) as archive: archive.write(raw)
            self.assertEqual(b'keep',target.read_bytes())

    def test_failed_copy_preserves_original_and_requires_new_destination(self):
        raw=self.store.backup(); original=(self.directory/'personal.cbp').read_bytes()
        path=self.folder('incomplete')
        with PersonalArchive(path) as archive:
            with patch.object(archive,'_sync',side_effect=OSError('disk failure')):
                with self.assertRaisesRegex(ContractError,'incomplete'): archive.write(raw)
            with self.assertRaises(ContractError): archive.write(raw)
        self.assertEqual(original,(self.directory/'personal.cbp').read_bytes())

    def test_backup_preserves_retained_ai_origin_without_restoring_review_authority(self):
        from claimbranch.core.review import Judgment, Proposal
        self.app.keep_draft('Human first reading','A human reason')
        session=self.app.review.session()
        judgment=Judgment.start('new-study',self.app.episode_id).edit('Human first reading','A human reason')
        judgment=judgment.use_proposal(Proposal('prior-proposal','new-study',self.app.episode_id,'Previously adopted AI wording','a'*64))
        session._judgment=judgment; session._prior_dispatches=1
        session.edit(judgment.text,judgment.rationale)
        self.app.recovery.save(self.app)
        project=self.store.load(); destination=self.folder('origin-restored')
        PersonalProjectStore.restore_backup(self.store.backup(),destination)
        with PersonalProjectStore(destination) as store:
            self.assertEqual(project.payload,store.load().payload)
            restored=project_workspace(store.load())
            state=restored.review.session().state()
            self.assertTrue(state['draft']['ai_influenced'])
            self.assertFalse(restored.paper.ai_available)
            self.assertIsNone(state['changes_review'])
            self.assertIsNone(state['proposal'])

    def test_interrupted_restore_preserves_original_and_can_reopen_complete_destination(self):
        from claimbranch.application.paper_work_store import WorkReopenRequired
        backup=self.store.backup(); original=(self.directory/'personal.cbp').read_bytes()
        destination=self.folder('uncertain-restore')
        original_sync=PersonalProjectStore._sync
        def sync(descriptor):
            import stat
            if stat.S_ISDIR(os.fstat(descriptor).st_mode): raise OSError('directory flush failure')
            return original_sync(descriptor)
        with patch.object(PersonalProjectStore,'_sync',side_effect=sync):
            with self.assertRaises(WorkReopenRequired): PersonalProjectStore.restore_backup(backup,destination)
        self.assertEqual(original,(self.directory/'personal.cbp').read_bytes())
        with PersonalProjectStore(destination) as store: self.assertEqual(self.store.load().payload,store.load().payload)
        with self.assertRaises(ContractError): PersonalProjectStore.restore_backup(backup,destination)

    def test_restore_refuses_an_archive_destination_including_observed_path_aliases(self):
        raw=self.store.backup(); archive_path=self.folder('Archive')
        with PersonalArchive(archive_path) as archive: archive.write(raw)
        before=(archive_path/'backup.cbp').read_bytes()
        with self.assertRaises(ContractError): PersonalProjectStore.restore_backup(raw,archive_path)
        candidates=[archive_path.with_name('archive'),Path('/System/Volumes/Data')/archive_path.resolve().relative_to('/')]
        for alias in candidates:
            if not alias.exists() or not os.path.samefile(alias,archive_path): continue
            code,_,err=self.invoke('restore','--directory',str(alias),'--archive-directory',str(archive_path))
            self.assertEqual(1,code); self.assertIn('separate',err.lower())
        self.assertEqual(before,(archive_path/'backup.cbp').read_bytes())
        self.assertEqual(['backup.cbp'],sorted(p.name for p in archive_path.iterdir()))

    def test_archive_reentry_preserves_specific_error_and_interrupted_export_warning(self):
        archive=PersonalArchive(self.directory)
        with self.assertRaisesRegex(ContractError,'separate'):
            with archive: pass
        archive._path=self.folder('new-archive')
        with archive: pass
        destination=self.folder('interrupted-export')
        with PersonalExport(destination) as export:
            with patch.object(export,'_sync',side_effect=KeyboardInterrupt):
                with self.assertRaisesRegex(KeyboardInterrupt,'export.*incomplete'):
                    export.write(self.store.load().payload)
        self.assertTrue((destination/'project.json').exists())

    def test_public_actions_refuse_busy_or_same_archive_destination(self):
        before=(self.directory/'personal.cbp').read_bytes()
        for action,extra in [('status',[]),('backup',['--archive-directory',str(self.directory)])]:
            code,_,err=self.invoke(action,'--directory',str(self.directory),*extra)
            self.assertEqual(1,code); self.assertTrue(err)
        self.store.close()
        code,_,err=self.invoke('backup','--directory',str(self.directory),'--archive-directory',str(self.directory))
        self.assertEqual(1,code); self.assertTrue(err)
        self.assertEqual(before,(self.directory/'personal.cbp').read_bytes())

    def test_public_uncertain_restore_names_destination_without_claiming_success(self):
        import stat
        archive=self.folder('uncertain-archive'); destination=self.folder('uncertain-public-restore')
        original=(self.directory/'personal.cbp').read_bytes()
        with PersonalArchive(archive) as target: target.write(self.store.backup())
        sync=PersonalProjectStore._sync
        def fail_directory(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode): raise OSError('injected flush failure')
            return sync(descriptor)
        with patch.object(PersonalProjectStore,'_sync',side_effect=fail_directory):
            code,out,err=self.invoke('restore','--directory',str(destination),'--archive-directory',str(archive))
        self.assertEqual(1,code); self.assertEqual('',out)
        self.assertIn('not confirmed',err)
        self.assertIn(str(destination),err)
        self.assertEqual(original,(self.directory/'personal.cbp').read_bytes())
        with PersonalProjectStore(destination) as store:
            self.assertEqual(self.store.load().payload,store.load().payload)

    def test_public_prewrite_restore_refusal_does_not_claim_uncertain_save(self):
        archive=self.folder('restore-source'); destination=self.folder('already-an-export')
        with PersonalArchive(archive) as target: target.write(self.store.backup())
        exported=destination/'project.json'; exported.write_bytes(b'Existing human export')
        code,out,err=self.invoke('restore','--directory',str(destination),'--archive-directory',str(archive))
        self.assertEqual(1,code); self.assertEqual('',out)
        self.assertIn('separate fresh directory',err)
        self.assertNotIn('Saving is not confirmed',err)
        self.assertEqual([exported],list(destination.iterdir()))

    def test_actual_process_loss_before_after_replace_restores_whole_workspace(self):
        project=self.complete_work(); backup=self.store.backup(); self.store.close()
        script='''import os,sys
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.tui_work_recovery import snapshot_value
with PersonalProjectStore(sys.argv[1]) as store:
 p=store.load(); app=project_workspace(p); app.keep_note('Newest full workspace')
 p=p.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
 replace=os.replace
 def crash(*a,**kw):
  if sys.argv[2]=='after': replace(*a,**kw)
  os._exit(77)
 os.replace=crash
 store.save(p)
'''
        for cut in ('before','after'):
            destination=self.folder('crash-'+cut)
            PersonalProjectStore.restore_backup(backup,destination)
            result=subprocess.run([sys.executable,'-B','-c',script,str(destination),cut],capture_output=True,timeout=30)
            self.assertEqual(77,result.returncode,result.stderr)
            with PersonalProjectStore(destination) as store:
                restored=store.load(); app=project_workspace(restored)
                self.assertEqual(project.work.history.manifest(),restored.work.history.manifest())
                self.assertIn(['Unfinished 한글'],app.unfinished.values())
                self.assertIn('Newest full workspace' if cut=='after' else 'A separate note with 한글',app.notes.values())
            self.assertEqual([],list(destination.glob('.personal-*')))
