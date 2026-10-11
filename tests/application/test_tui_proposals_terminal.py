"""Actual wide/narrow PTY offline selective-incorporation and ordinary return."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.application import test_tui_terminal as helper


@unittest.skipUnless(helper.SUPPORTED,'requires Unix PTY and Python curses')
class ProposalTerminalTests(unittest.TestCase):
    setUp=helper.TerminalProcessTests.setUp
    tearDown=helper.TerminalProcessTests.tearDown
    resize=helper.TerminalProcessTests.resize
    expect=helper.TerminalProcessTests.expect
    send=helper.TerminalProcessTests.send
    assert_restored=helper.TerminalProcessTests.assert_restored

    def launch(self,*arguments,cwd=helper.ROOT):
        self.output=b''
        self.process=subprocess.Popen([sys.executable,'-B','-m','claimbranch',*arguments],cwd=cwd,
            env={**os.environ,'TERM':'xterm-256color','PYTHONUTF8':'1'},
            stdin=self.slave,stdout=self.slave,stderr=self.slave,process_group=0)

    def request(self):
        self.send('A','SELECT EXACT AI CONTEXT')
        # Observation is the first row; the thesis is initially checked.
        self.send(' \n','REVIEW EXACT OFFLINE INPUT')
        self.send('\x1b[F\x0c','Request digest:')
        self.send('\n','SELECT AI ITEMS')

    def select(self,item_index):
        self.send('\x1b[H'+'\x1b[B'*item_index+' c','COMPARE SELECTED AI ITEMS')
        self.send('\x1b[F\x0c','Enter stages only this batch')

    def test_wide_narrow_select_edit_record_restart_backup_and_history(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.core.canonical import decode
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); root.chmod(0o700)
            self.launch('demo','proposals','--directory',str(root),'--create')
            self.expect('Type create'); self.send('create\r','ARGUMENT GRAPH')
            self.request()
            self.select(1)
            self.send('G','AI ITEM COMPARISON')
            self.send('\t\x0c','BEFORE')
            self.resize(80,24); self.send('\x0c','AI ITEM COMPARISON')
            self.send('\x1b','COMPARE SELECTED AI ITEMS'); self.send('\x1b[F\x0c','Enter stages only this batch')
            self.send('\n','Selected batch staged')
            self.send('e','YOUR ARGUMENT DRAFTS')
            self.send('\n','WRITE A SCIENTIFIC CHANGE')
            self.send('\x1b[H'+'\x1b[B'*3+'\n','WHY THIS CONNECTION?')
            self.send('\x1b[200~ CPU-B는 미측정이다.\x1b[201~\x13','WRITE A SCIENTIFIC CHANGE')
            self.send('\x13','Draft kept')
            self.send('\x1b'); self.send('e','YOUR JUDGMENT')
            self.send('\x1b[200~CPU-B remains untested.\x1b[201~\tOnly CPU-A was measured.\x13','Draft kept')
            # Menu personal reasoning precedes next/ask/current/history/origins.
            self.send(';\x1b[F'+'\x1b[A'*5+'\n','PERSONAL RECORD PREVIEW')
            self.send('\x1b[F\x0c','1 explain')
            self.send('1','PERSONAL EXPLANATION')
            self.send('\n','PARTIAL TEXT')
            self.send('\x1b[200~이 관찰은 CPU-B를 검증하지 않는다.\x1b[201~\x13','no science')
            self.send('\x1b','PERSONAL RECORD PREVIEW'); self.send('\x1b[F\x0c','Enter record')
            self.send('2','DISPLAYED PERSONAL EFFECT')
            self.send('\x1b[F\x0c','Enter record')
            self.send('\n','Personal research recorded and saved')
            self.send('q'); self.assert_restored(0)
            for bad in (b'Traceback',b'Draft save failed',b'Writing checkpoint not saved'):
                self.assertNotIn(bad,self.output)
            with PersonalProjectStore(root/'work') as store:
                project=store.load(); app=project_workspace(project)
                origin=app.paper.recorded_origins()[0]
                self.assertEqual('leave-for-later',origin['explanation']['state'])
                self.assertEqual(2,len(origin['lineages'][0]['revisions']))
                self.assertIn('CPU-B는 미측정이다.',origin['lineages'][0]['revisions'][-1]['amendment']['body']['rationale'])
                self.assertEqual('Only CPU-A was measured.',origin['cause']['judgment']['rationale'])
                self.assertFalse(app.paper.ai_available)
                archive=store.backup()
            restored=root/'restored'; restored.mkdir(mode=0o700)
            PersonalProjectStore.restore_backup(archive,restored)
            self.launch('project','open','--directory',str(restored))
            self.expect('AI OFF'); self.expect('ARGUMENT GRAPH')
            # End is personal explanation; one up = item origins, another = response history.
            self.send(';\x1b[F\x1b[A\x1b[A\n','AI RESPONSE HISTORY')
            self.send('\n','HISTORICAL AI RESPONSE')
            self.send('\x1b[F\x0c','staging_available')
            self.send('\x1b','AI RESPONSE HISTORY'); self.send('\x1b','ARGUMENT GRAPH'); self.send('q'); self.assert_restored(0)

    def test_request_cancel_reject_tiny_resize_and_manual_path(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); root.chmod(0o700)
            self.resize(80,24)
            self.launch('demo','proposals','--directory',str(root),'--create')
            self.expect('Type create'); self.send('create\r','ARGUMENT GRAPH')
            self.send('A','SELECT EXACT AI CONTEXT'); self.send(' \n','REVIEW EXACT OFFLINE INPUT')
            self.resize(40,12); self.send('\x0c','Proposal controls paused')
            self.send('\n'); self.send('\x1b')
            self.resize(132,38); self.send('\x0c','ARGUMENT GRAPH')
            self.request(); self.send('x','Response declined')
            self.send('e','YOUR JUDGMENT'); self.send('\x1b[200~직접 판단 중이다.\x1b[201~\x13','Draft kept')
            self.send('q'); self.assert_restored(0)
            with PersonalProjectStore(root/'work') as store:
                app=project_workspace(store.load())
                self.assertEqual(1,len(app.paper.proposal_history()))
                self.assertEqual('cancelled',app.paper.proposal_history()[0]['disposition'])
                self.assertEqual({},app.review.candidates().records)
                self.assertEqual('직접 판단 중이다.',app.draft()['text'])


@unittest.skipUnless(helper.SUPPORTED,'requires Unix PTY and Python curses')
class ProviderPreviewTerminalTests(unittest.TestCase):
    setUp=helper.TerminalProcessTests.setUp
    tearDown=helper.TerminalProcessTests.tearDown
    resize=helper.TerminalProcessTests.resize
    expect=helper.TerminalProcessTests.expect
    send=helper.TerminalProcessTests.send
    assert_restored=helper.TerminalProcessTests.assert_restored
    launch=ProposalTerminalTests.launch

    def test_owned_wire_selection_edit_and_fresh_process_origin_return(self):
        import json
        from claimbranch.application.paper_assistance_example import history, SOURCE, frozen_response
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork, preview_association
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.provider_profile import ProviderProfile, ProviderProfileStore
        from tests.application.test_provider_transport import Peer
        from tests.application.test_provider_profile import wrapper
        peer=Peer(json.dumps(wrapper('openai-chat',frozen_response().decode())).encode(),delay=3); self.addCleanup(peer.close)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); paper=root/'paper'; work=root/'work'; config=root/'llm'
            paper.mkdir(); work.mkdir(mode=0o700); config.mkdir(mode=0o700)
            subprocess.run(['git','init','-q',str(paper)],check=True); (paper/'paper.tex').write_bytes(SOURCE)
            association=preview_association(paper,'paper.tex','anchor',work)
            with PersonalProjectStore.create(work,project_id='cache-study') as store:
                store.save(ProjectWork.create(PaperWork.create(history()),association),preview=association)
            with ProviderProfileStore(config) as store:
                store.write(ProviderProfile.create(api='openai-chat',endpoint=peer.endpoint,model='owned/test-model').payload)
            # Test-owned bypass is confined to this child, never a public option or persisted verdict.
            driver='''from unittest.mock import patch
import sys
from claimbranch.application.cli import main
from claimbranch.application.provider_commands import PersonalProviderConnection
with patch.object(PersonalProviderConnection, 'require_qualification'):
    raise SystemExit(main(['project','open','--directory',sys.argv[1],'--provider-directory',sys.argv[2]]))
'''
            self.output=b''
            self.process=subprocess.Popen([sys.executable,'-B','-c',driver,str(work),str(config)],cwd=helper.ROOT,
                env={**os.environ,'TERM':'xterm-256color','PYTHONUTF8':'1'},
                stdin=self.slave,stdout=self.slave,stderr=self.slave,process_group=0)
            self.expect('ARGUMENT GRAPH'); self.send('A','SELECT EXACT AI CONTEXT')
            self.send(' \n','REVIEW EXACT API REQUEST'); self.send('\x1b[F\x0c','Enter check live gate')
            self.send('\n','PERSONAL API REQUEST PENDING'); self.send('m','Request still pending')
            self.send('e','YOUR JUDGMENT'); self.send('\x1b[200~내가 직접 해석하는 중이다.\x1b[201~\x13','Draft kept')
            peer.release.set(); self.expect('API response ready')
            self.send(';\x1b[F\x1b[A\x1b[A\n','SELECT AI ITEMS')
            self.send('\x1b[H\x1b[B c','COMPARE SELECTED AI ITEMS')
            self.send('\x1b[F\x0c','Enter stages only this batch'); self.send('\n','Selected batch staged')
            self.send('e','YOUR ARGUMENT DRAFTS'); self.send('\n','WRITE A SCIENTIFIC CHANGE')
            self.send('\x1b[H'+'\x1b[B'*3+'\n','WHY THIS CONNECTION?')
            self.resize(80,24)
            self.send('\x1b[200~ CPU-B는 미측정이다.\x1b[201~\x13','WRITE A SCIENTIFIC CHANGE')
            self.send('\x13','Draft kept'); self.send('\x1b','YOUR JUDGMENT'); self.send('q'); self.assert_restored(0)
            self.assertEqual(1,len(peer.requests))
            with PersonalProjectStore(work) as store:
                app=project_workspace(store.load())
                self.assertFalse(app.paper.ai_available); self.assertFalse(hasattr(app,'provider_connection'))
                self.assertEqual('내가 직접 해석하는 중이다.',app.draft()['text'])
                entry=app.paper.proposal_history()[0]; self.assertIsNotNone(entry['provider']['outcome'])
                owner=tuple(entry['owner']); candidates=app.paper.candidates(*owner)
                origin=next(iter(candidates.origins.values()))
                self.assertTrue(origin.ai_influenced)
                self.assertIn('CPU-B는 미측정이다.',origin.amendment['body']['rationale'])
                backup=store.backup()
            restored=root/'restored'; restored.mkdir(mode=0o700)
            PersonalProjectStore.restore_backup(backup,restored)
            self.launch('project','open','--directory',str(restored)); self.expect('AI OFF')
            self.send(';\x1b[F\x1b[A\n','AI RESPONSE HISTORY')
            self.send('\n','HISTORICAL AI RESPONSE'); self.send('\x1b[F\x0c','staging_available')
            self.send('\x1b','AI RESPONSE HISTORY'); self.send('\x1b','ARGUMENT GRAPH')
            self.send('q'); self.assert_restored(0)
            self.assertEqual(SOURCE,(paper/'paper.tex').read_bytes()); self.assertEqual(1,len(peer.requests))

    def test_public_codex_preview_manual_restart_without_client_or_attempt(self):
        from claimbranch.application.paper_assistance_example import history, SOURCE
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork, preview_association
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.provider_profile import CodexProfile, ProviderProfileStore
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); paper=root/'paper'; work=root/'work'; config=root/'llm'
            paper.mkdir(); work.mkdir(mode=0o700); config.mkdir(mode=0o700)
            subprocess.run(['git','init','-q',str(paper)],check=True)
            (paper/'paper.tex').write_bytes(SOURCE)
            association=preview_association(paper,'paper.tex','anchor',work)
            with PersonalProjectStore.create(work,project_id='cache-study') as store:
                store.save(ProjectWork.create(PaperWork.create(history()),association),preview=association)
            with ProviderProfileStore(config) as store:
                store.write(CodexProfile.create(model='gpt-6.1-sol').payload)
            self.launch('project','open','--directory',str(work),'--provider-directory',str(config))
            self.expect('AI preview'); self.expect('ARGUMENT GRAPH')
            self.send('A','SELECT EXACT AI CONTEXT'); self.send(' \n','REVIEW CODEX APPLICATION INPUT')
            self.resize(40,12); self.send('\x0c','Proposal controls paused')
            self.resize(80,24); self.send('\x0c','REVIEW CODEX APPLICATION INPUT')
            self.send('\x1b[F\x0c','Enter check live gate'); self.send('\n','Actual Codex client not qualified')
            self.send('\x1b','ARGUMENT GRAPH'); self.send('e','YOUR JUDGMENT')
            self.send('\x1b[200~AI 없이 판단을 이어간다.\x1b[201~\t원래 측정 범위를 확인한다.\x13','Draft kept')
            self.send('q'); self.assert_restored(0)
            with PersonalProjectStore(work) as store:
                app=project_workspace(store.load())
                self.assertEqual('AI 없이 판단을 이어간다.',app.draft()['text'])
                self.assertEqual([],app.paper.proposal_history())
                self.assertNotIn(b'codex-profile',store.load().payload)
            self.launch('project','open','--directory',str(work)); self.expect('AI OFF')
            self.send('q'); self.assert_restored(0)
            self.assertEqual(SOURCE,(paper/'paper.tex').read_bytes())

    def test_public_profile_preview_narrow_resize_manual_restart_and_no_dispatch(self):
        from claimbranch.application.paper_assistance_example import history, SOURCE
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.project_work import ProjectWork, preview_association
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.provider_profile import ProviderProfile, ProviderProfileStore
        from tests.application.test_provider_transport import Peer
        peer=Peer(); self.addCleanup(peer.close)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); paper=root/'paper'; work=root/'work'; config=root/'llm'
            paper.mkdir(); work.mkdir(mode=0o700); config.mkdir(mode=0o700)
            subprocess.run(['git','init','-q',str(paper)],check=True)
            (paper/'paper.tex').write_bytes(SOURCE)
            association=preview_association(paper,'paper.tex','anchor',work)
            with PersonalProjectStore.create(work,project_id='cache-study') as store:
                store.save(ProjectWork.create(PaperWork.create(history()),association),preview=association)
            with ProviderProfileStore(config) as store:
                store.write(ProviderProfile.create(api='openai-chat',endpoint=peer.endpoint,model='owned/test-model',
                    credential_env='KEY_NOT_PREPARED').payload)
            self.launch('project','open','--directory',str(work),'--provider-directory',str(config))
            self.expect('AI preview'); self.expect('ARGUMENT GRAPH')
            self.send('A','SELECT EXACT AI CONTEXT'); self.send(' \n','REVIEW EXACT API REQUEST')
            self.resize(40,12); self.send('\x0c','Proposal controls paused'); self.send('\n')
            self.assertEqual([],peer.requests)
            self.resize(80,24); self.send('\x0c','REVIEW EXACT API REQUEST')
            self.send('\x1b[F\x0c','Enter check live gate'); self.send('\n','Actual provider not qualified')
            self.send('\x1b','ARGUMENT GRAPH'); self.send('e','YOUR JUDGMENT')
            self.send('\x1b[200~내가 판단하고 이유를 남긴다.\x1b[201~\t측정 범위를 확인했다.\x13','Draft kept')
            self.send('q'); self.assert_restored(0)
            self.assertEqual([],peer.requests)
            with PersonalProjectStore(work) as store:
                app=project_workspace(store.load())
                self.assertEqual('내가 판단하고 이유를 남긴다.',app.draft()['text'])
                self.assertEqual([],app.paper.proposal_history())
                self.assertFalse(hasattr(app,'provider_connection'))
            self.launch('project','open','--directory',str(work)); self.expect('AI OFF')
            self.send('q'); self.assert_restored(0)
            self.assertEqual(SOURCE,(paper/'paper.tex').read_bytes())
            self.assertNotIn(b'Traceback',self.output)


if __name__=='__main__': unittest.main()
