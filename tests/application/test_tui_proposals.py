"""Novel offline UI selection/return in the existing ordinary private project."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import json
import os
import time
import io
from contextlib import redirect_stdout

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.application.paper_assistance_example import history, enable, SOURCE
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.project_work import ProjectWork, preview_association
from claimbranch.application.personal_project import PersonalProjectStore, PersonalProjectRecovery
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.tui import Frame, Terminal, compose
from claimbranch.application.tui_actions import actions_ui
from claimbranch.application.tui_proposals import proposals_ui, available
from claimbranch.application.tui_personal import personal_ui
from claimbranch.application.tui_candidates_ui import candidates_ui


class PersonalProviderUITests(unittest.TestCase):
    """Owned API peers exercise wiring; mocked qualification is not deployment proof."""
    def setUp(self):
        ProposalUITests.setUp(self)
        from claimbranch.application.provider_commands import PersonalProviderConnection
        from claimbranch.application.provider_profile import ProviderProfile, ProviderProfileStore
        from claimbranch.application.paper_assistance_example import frozen_response
        from tests.application.test_provider_transport import Peer
        from tests.application.test_provider_profile import wrapper
        self.peer = Peer(json.dumps(wrapper('openai-chat', frozen_response().decode())).encode())
        self.addCleanup(self.peer.close)
        self.config = self.root/'llm'; self.config.mkdir(mode=0o700)
        with ProviderProfileStore(self.config) as store:
            store.write(ProviderProfile.create(api='openai-chat', endpoint=self.peer.endpoint,
                model='owned/test-model', credential_env='TEST_PERSONAL_PROVIDER_KEY').payload)
        self.connection = PersonalProviderConnection(self.config).__enter__()
        self.addCleanup(self.connection.close)
        self.connection.attach(self.app)

    frame = lambda self: ProposalUITests.frame(self)
    read_end = lambda self: ProposalUITests.read_end(self)
    stage = lambda self, item: ProposalUITests.stage(self, item)

    def preview(self, *, include_draft=False):
        self.terminal.modal=None; self.terminal.key('A')
        self.ui.checked={'thesis','obs-a'}
        if include_draft: self.terminal.key('d')
        self.terminal.key('enter'); self.read_end()

    def send_owned(self, *, include_draft=False):
        self.preview(include_draft=include_draft)
        with patch.object(self.connection, 'require_qualification'), patch.dict(
                os.environ, {'TEST_PERSONAL_PROVIDER_KEY':'synthetic-key'}):
            self.terminal.key('enter')
        self.assertEqual('proposal-wait',self.terminal.modal)
        self.assertTrue(self.peer.arrived.wait(3))

    def finish(self):
        deadline=time.monotonic()+4
        while self.ui.pending and time.monotonic()<deadline:
            self.ui.poll(); time.sleep(.01)
        self.assertEqual([],self.ui.pending)

    def test_unqualified_preview_never_reads_key_dispatches_or_enables_example(self):
        original=self.app.paper.history.manifest()
        self.preview(include_draft=True)
        text='\n'.join(self.ui.content('outbound'))
        self.assertIn(self.peer.endpoint,text); self.assertIn('owned/test-model',text)
        self.assertIn('TEST_PERSONAL_PROVIDER_KEY',text); self.assertNotIn('OFFLINE FIXED EXAMPLE',text)
        self.assertIn('REVIEW EXACT API REQUEST',self.frame())
        with patch('claimbranch.application.provider_transport.ProviderTransport.start') as start:
            self.terminal.key('enter')
        start.assert_not_called()
        self.assertIn('not qualified',self.ui.notice)
        self.assertEqual([],self.peer.requests); self.assertEqual([],self.app.paper.proposal_history())
        self.assertEqual(original,self.app.paper.history.manifest())
        self.assertFalse(self.app.paper.ai_available)
        self.assertNotIn('AI example',compose(self.app,80,24).plain())

    def test_async_poll_retains_pending_and_does_not_replace_manual_input(self):
        self.peer.delay=3
        self.send_owned(); self.assertFalse(self.ui.poll()); self.assertEqual(1,len(self.ui.pending))
        self.terminal.key('escape')
        self.app.keep_draft('직접 생각하는 중','CPU-A만 측정했다.')
        self.peer.release.set(); self.finish()
        self.assertIsNone(self.terminal.modal)
        self.assertEqual('직접 생각하는 중',self.app.draft()['text'])
        self.assertEqual('cancelled',self.app.paper.proposal_history()[0]['disposition'])

    def test_continue_writing_keeps_omitted_draft_request_pending_without_stealing_editor(self):
        self.peer.delay=3; self.send_owned()
        self.terminal.key('m')
        self.assertIsNone(self.terminal.modal); self.assertEqual(1,len(self.ui.pending))
        self.terminal.key('e'); self.terminal.key(('paste','직접 해석하는 중'))
        self.peer.release.set(); self.finish()
        self.assertEqual('edit',self.terminal.modal)
        self.assertEqual('직접 해석하는 중',self.terminal.buffers[0].text)
        self.assertEqual('proposed',self.app.paper.proposal_history()[0]['disposition'])
        self.terminal.key('keep'); self.ui.enter('current'); self.stage('limit')
        self.assertEqual('직접 해석하는 중',self.app.draft()['text'])

    def test_new_unsent_preview_cannot_silently_cancel_same_judgment_pending_request(self):
        self.peer.delay=3; self.send_owned(); worker=self.ui.worker
        self.terminal.key('m'); self.preview()
        self.assertEqual('proposal-context',self.terminal.modal)
        self.assertIn('pending',self.ui.notice)
        self.terminal.key('escape'); self.peer.release.set(); self.finish()
        self.assertEqual('proposed',self.app.paper.proposal_history()[0]['disposition'])
        self.assertIs(worker,self.ui.controllers[self.app.work_key()])
        self.ui.enter('current'); self.assertEqual('proposal-items',self.terminal.modal)

    def test_item_view_failure_keeps_completed_trace_and_does_not_crash_or_cancel(self):
        self.send_owned()
        worker=self.ui.worker
        with patch.object(self.ui,'enter',side_effect=ContractError('synthetic view failure')):
            self.finish()
        self.assertIsNone(self.terminal.modal)
        entry=self.app.paper.proposal_history()[0]
        self.assertIsNotNone(entry['trace_digest']); self.assertEqual('proposed',entry['disposition'])
        self.assertNotIn('trace unavailable',self.app.message)
        self.assertIsNotNone(worker._current); self.ui.enter('current')
        self.assertEqual('proposal-items',self.terminal.modal)

    def test_unsent_preview_preserves_completed_items_until_explicit_decline(self):
        self.send_owned(); self.finish(); worker=self.ui.worker
        self.terminal.key('escape'); self.preview()
        self.assertEqual('proposal-context',self.terminal.modal)
        self.assertIn('decline',self.ui.notice.lower())
        self.assertIs(worker,self.ui.controllers[self.app.work_key()])
        self.assertEqual('proposed',self.app.paper.proposal_history()[0]['disposition'])
        self.terminal.key('escape'); self.ui.enter('current'); self.stage('limit')
        self.terminal.key('escape'); self.ui.enter('current'); self.terminal.key('x')
        self.preview(); self.assertEqual('proposal-outbound',self.terminal.modal)
        self.assertEqual(1,len(self.peer.requests))
        self.assertTrue(next(iter(self.app.review.candidates().origins.values())).ai_influenced)

    def test_failed_history_projection_after_completion_keeps_recorded_trace_and_items(self):
        self.send_owned(); worker=self.ui.worker
        self.assertTrue(next(iter(worker._jobs.values())).wait_closed(3))
        with patch.object(worker,'historical',side_effect=ContractError('synthetic history view failure')):
            self.finish()
        entry=self.app.paper.proposal_history()[0]
        self.assertIsNotNone(entry['trace_digest']); self.assertEqual('proposed',entry['disposition'])
        self.assertNotIn('trace unavailable',self.app.message)
        self.assertIn('Response retained',self.app.message)
        self.assertIsNone(self.terminal.modal); self.assertIsNotNone(worker._current)
        self.ui.enter('current'); self.stage('limit')

    def test_missing_projected_entry_after_completion_preserves_owned_result(self):
        self.send_owned(); worker=self.ui.worker
        self.assertTrue(next(iter(worker._jobs.values())).wait_closed(3))
        with patch.object(worker,'historical',return_value=()):
            self.finish()
        self.assertEqual('proposed',self.app.paper.proposal_history()[0]['disposition'])
        self.assertIsNone(self.terminal.modal)
        self.assertIn('Response retained',self.app.message)
        self.ui.enter('current'); self.assertEqual('proposal-items',self.terminal.modal)

    def test_response_stages_and_records_with_connection_retained_then_reopens_ai_off(self):
        self.send_owned(); self.finish(); self.assertEqual('proposal-items',self.terminal.modal)
        self.assertNotIn('OFFLINE FIXED EXAMPLE','\n'.join(self.ui.content('item')))
        self.stage('limit')
        p=ProposalUITests.reasoning(self); self.terminal.key('2'); self.read_end(); self.terminal.key('enter')
        self.assertIsNone(self.terminal.modal)
        self.assertIs(self.connection,self.app.provider_connection)
        self.assertTrue(available(self.app))
        self.app.recovery.save(self.app)
        saved=self.store.load()
        self.assertNotIn(b'TEST_PERSONAL_PROVIDER_KEY',saved.payload)
        self.assertNotIn(b'synthetic-key',saved.payload)
        reopened=project_workspace(saved)
        self.assertFalse(available(reopened)); self.assertFalse(hasattr(reopened,'provider_connection'))
        self.assertEqual('Only CPU-A was measured.',reopened.paper.recorded_origins()[0]['cause']['judgment']['rationale'])
        self.assertTrue(reopened.paper.proposal_history()[0]['provider']['outcome'])
        self.assertFalse(reopened.paper.proposal_history()[0]['staging_available'])

    def test_wrong_owner_completion_never_moves_focus_or_opens_other_judgment(self):
        self.peer.delay=3; self.send_owned()
        self.app.select('obs-a',remember=False); self.peer.release.set(); self.finish()
        self.assertEqual('obs-a',self.app.selected_id)
        self.assertEqual('proposal-history-detail',self.terminal.modal)
        self.assertIn('reading only','\n'.join(self.ui.content('history-detail')))
        self.assertEqual({'text':'','rationale':''},self.app.draft())

    def test_disabled_connection_revokes_items_but_preserves_origin_and_manual_work(self):
        self.send_owned(); self.finish(); self.stage('limit')
        self.ui.enter('disable')
        self.assertFalse(available(self.app)); self.assertIsNone(self.terminal.modal)
        self.assertEqual(1,len(self.app.review.candidates().records))
        self.assertTrue(next(iter(self.app.review.candidates().origins.values())).ai_influenced)
        self.assertFalse(self.app.paper.proposal_history()[0]['staging_available'])
        self.ui.enter('history'); self.terminal.key('enter')
        self.assertIn('reading only','\n'.join(self.ui.content('history-detail')))
        self.ui.enter('enable'); self.assertTrue(available(self.app))
        self.preview(); self.terminal.key('enter'); self.assertIn('not qualified',self.ui.notice)

    def test_changed_profile_and_included_draft_refuse_before_network(self):
        self.preview(include_draft=True)
        self.app.keep_draft('Changed after review','New reason')
        with patch.object(self.connection,'require_qualification'), patch('claimbranch.application.provider_transport.ProviderTransport.start') as start:
            self.terminal.key('enter')
        start.assert_not_called(); self.assertEqual([],self.app.paper.proposal_history())
        self.preview()
        value=self.connection.profile.value; value['model']='changed/model'
        (self.config/'provider.json').write_bytes(canonical_bytes(value))
        with patch.object(self.connection,'require_qualification'), patch('claimbranch.application.provider_transport.ProviderTransport.start') as start:
            self.terminal.key('enter')
        start.assert_not_called(); self.assertIn('configuration changed',self.ui.notice)
        self.assertEqual([],self.app.paper.proposal_history())

    def test_shutdown_cancels_reaps_and_retains_terminal_trace_before_save(self):
        self.peer.delay=3; self.send_owned()
        jobs=tuple(self.ui.worker._jobs.values())
        self.ui.shutdown(); self.assertEqual([],self.ui.pending)
        self.assertTrue(all(job.wait_closed(2) for job in jobs))
        self.app.recovery.save(self.app)
        reopened=project_workspace(self.store.load())
        outcome=reopened.paper.proposal_history()[0]['provider']['outcome']
        self.assertEqual('cancelled',outcome['disposition'])
        self.assertEqual(SOURCE,(self.paper/'paper.tex').read_bytes())

    def test_repeated_enter_is_single_dispatch_and_read_gate_blocks_first(self):
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}; self.terminal.key('enter')
        with patch.object(self.connection,'require_qualification'), patch('claimbranch.application.provider_transport.ProviderTransport.start') as start:
            self.terminal.key('enter')
        start.assert_not_called(); self.read_end()
        with patch.object(self.connection,'require_qualification'), patch.dict(os.environ,{'TEST_PERSONAL_PROVIDER_KEY':'synthetic-key'}):
            self.terminal.key('enter'); self.terminal.key('enter')
        self.finish(); self.assertEqual(1,len(self.peer.requests))
        self.assertEqual(1,len(self.app.paper.proposal_history()))

    def test_purpose_picker_keeps_selected_context_and_no_complete_judgment(self):
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}; self.terminal.key('p')
        self.terminal.key('enter')
        self.assertEqual('plan-experiment',self.ui.worker._entry['request']['purpose'])
        self.assertEqual({'text':'','rationale':''},self.app.draft())
        self.assertEqual([],self.peer.requests)

    def test_correction_and_next_question_keep_session_connection_but_revoke_old_request(self):
        from claimbranch.application.personal_research import PersonalResearch
        self.preview()
        original_worker=self.ui.worker
        self.terminal.key('escape'); self.app.select('obs-a',remember=False)
        key=self.app.intake.create(self.app.context_key())
        for field,text in {'rationale':'Check corrected synthetic observation.',
                           'observation':'Revised CPU-A observation.', 'value':'7'}.items():
            self.app.intake.keep(key,field,text)
        research=PersonalResearch(self.app)
        research.commit(research.prepare('correct',item_id=key))
        self.assertIs(self.connection,self.app.provider_connection); self.assertTrue(available(self.app))
        with self.assertRaises(ContractError): original_worker._fresh()
        research.commit(research.prepare('next',question='Does the same result hold on CPU-B?'))
        self.assertIs(self.connection,self.app.provider_connection); self.assertTrue(available(self.app))
        self.preview(); self.assertEqual(self.app.episode_id,self.ui.worker._entry['request']['episode_id'])
        self.assertEqual([],self.peer.requests)

    def test_poll_error_is_bounded_and_disable_preserves_newer_writing_without_inventing_trace(self):
        self.peer.delay=3; self.send_owned()
        worker=self.ui.worker; job=next(iter(worker._jobs.values()))
        self.app.keep_draft('새로 쓴 판단','원래 이유 유지')
        with patch.object(job,'poll',side_effect=OSError('synthetic polling failure')):
            self.ui.poll(); self.ui.enter('disable')
        self.assertFalse(available(self.app)); self.assertEqual([],self.ui.pending)
        self.assertIsNone(worker._current); self.assertTrue(self.terminal.checkpoint())
        self.assertIn('trace unavailable',self.app.message.lower())
        reopened=project_workspace(self.store.load())
        self.assertEqual('새로 쓴 판단',reopened.draft()['text'])
        entry=reopened.paper.proposal_history()[0]
        self.assertEqual('cancelled',entry['disposition']); self.assertIsNone(entry['trace_digest'])
        self.assertIsNone(entry['provider']['outcome'])

    def test_final_checkpoint_runs_even_if_cleanup_raises(self):
        self.app.keep_draft('종료 전에 쓴 판단','저장해야 하는 이유')
        self.terminal.screen.scrollok=lambda *_:None
        self.terminal.screen.keypad=lambda *_:None
        self.terminal.screen.timeout=lambda *_:None
        self.terminal.curses.set_escdelay=lambda *_:None
        self.terminal.curses.raw=lambda:None
        self.terminal.curses.typeahead=lambda *_:None
        with redirect_stdout(io.StringIO()), patch.object(self.terminal,'paint'), \
             patch.object(self.terminal,'read',return_value='q'), patch.object(self.terminal,'key',return_value=0), \
             patch.object(self.ui,'shutdown',side_effect=OSError('synthetic cleanup failure')):
            with self.assertRaises(OSError): self.terminal.loop()
        reopened=project_workspace(self.store.load())
        self.assertEqual('종료 전에 쓴 판단',reopened.draft()['text'])

    def test_failed_child_cancel_cannot_leave_incorporation_or_ai_enabled(self):
        self.peer.delay=4; self.send_owned()
        worker=self.ui.worker; job=next(iter(worker._jobs.values()))
        with patch.object(job,'cancel',side_effect=OSError('synthetic child kill failure')):
            self.ui.enter('disable')
        self.assertFalse(available(self.app)); self.assertIsNone(worker._current)
        self.assertIn('cleanup not confirmed',self.app.message)
        self.peer.release.set(); self.finish()
        self.assertEqual('cancelled',self.app.paper.proposal_history()[0]['disposition'])
        with self.assertRaises(ContractError): worker.compare(['limit'])


class CodexPreviewUITests(unittest.TestCase):
    def setUp(self):
        ProposalUITests.setUp(self)
        from claimbranch.application.provider_commands import PersonalProviderConnection
        from claimbranch.application.provider_profile import CodexProfile, ProviderProfileStore
        self.config = self.root/'llm'; self.config.mkdir(mode=0o700)
        with ProviderProfileStore(self.config) as store:
            store.write(CodexProfile.create(model='gpt-6.1-sol').payload)
        self.connection = PersonalProviderConnection(self.config).__enter__()
        self.addCleanup(self.connection.close); self.connection.attach(self.app)

    frame = lambda self: ProposalUITests.frame(self)
    read_end = lambda self: ProposalUITests.read_end(self)

    def preview(self):
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}
        self.terminal.key('d'); self.terminal.key('enter'); self.read_end()

    def test_codex_contextual_preview_and_gate_create_no_attempt_or_live_capability(self):
        original = self.app.paper.history.manifest()
        self.app.keep_draft('내 미완성 판단','Only CPU-A was measured.')
        self.preview()
        text = '\n'.join(self.ui.content('outbound'))
        self.assertIn('CODEX INPUT PREVIEW', text)
        from claimbranch.application.paper_proposal_work import CodexProposalPreview, ProviderProposalWork
        self.assertIs(type(self.ui.worker), CodexProposalPreview)
        self.assertIsInstance(self.ui.worker, ProviderProposalWork)
        self.assertIn('installed/runtime version not observed', text)
        self.assertIn('"runtime_wrapper": "unverified"', text)
        self.assertIn('"transport_destinations": "not qualified"', text)
        self.assertNotIn('PERSONAL API PROPOSAL', text)
        self.assertNotIn('OFFLINE FIXED EXAMPLE', text)
        self.assertIn('not CLI-generated HTTP content', text)
        self.assertNotIn('Retained minimal trace and available response', text)
        self.assertNotIn('three dispatched attempts', text)
        self.assertIn('No attempt, response, trace or consent is saved by this Codex preview.', text)
        self.assertIn('내 미완성 판단', text)
        self.assertIn('REVIEW CODEX APPLICATION INPUT', self.frame())
        with patch('subprocess.Popen',side_effect=AssertionError('no CLI')), patch(
                'claimbranch.application.provider_commands.PersonalProviderConnection.require_qualification'), patch(
                'claimbranch.application.provider_transport.ProviderTransport') as transport:
            self.terminal.key('enter')
        transport.assert_not_called()
        self.assertIn('Actual Codex client not qualified', self.ui.notice)
        self.assertEqual([], self.ui.pending)
        self.assertEqual([], self.app.paper.proposal_history())
        self.assertIsNone(self.ui.worker._entry)
        self.assertEqual(0, self.ui.worker.session._prior_dispatches)
        self.assertFalse(self.app.paper.ai_available)
        self.assertEqual(original, self.app.paper.history.manifest())
        self.terminal.key('escape'); self.app.recovery.save(self.app)
        saved = self.store.load()
        self.assertNotIn(b'codex-profile', saved.payload)
        self.assertNotIn(b'gpt-6.1-sol', saved.payload)
        restored = project_workspace(saved)
        self.assertFalse(available(restored))
        self.assertEqual('내 미완성 판단', restored.draft()['text'])

    def test_changed_included_draft_expiry_and_cancel_revoke_codex_preview(self):
        from claimbranch.application.provider_profile import CodexProfile
        self.preview(); worker, prepared = self.ui.worker, self.ui.outbound
        self.app.keep_draft('New human thinking','New human reason')
        with self.assertRaises(ContractError): worker.recheck_preview(prepared,self.connection.profile)
        self.terminal.key('escape')
        with self.assertRaises(ContractError): worker.recheck_preview(prepared,self.connection.profile)
        self.preview(); worker, prepared = self.ui.worker, self.ui.outbound
        with patch.object(worker,'clock',return_value=prepared.review.expires_at):
            with self.assertRaises(ContractError): worker.recheck_preview(prepared,self.connection.profile)
        with self.assertRaises(ContractError): worker.recheck_preview(prepared,CodexProfile.create(model='another-model'))
        worker.recheck_preview(prepared,self.connection.profile)
        self.terminal.key('escape')
        with self.assertRaises(ContractError): worker.recheck_preview(prepared,self.connection.profile)
        self.assertEqual('New human thinking',self.app.draft()['text'])
        self.assertEqual([],self.app.paper.proposal_history())


class ProposalUITests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root=Path(folder.name); self.paper=self.root/'paper'; self.directory=self.root/'work'
        self.paper.mkdir(); self.directory.mkdir(mode=0o700)
        subprocess.run(['git','init','-q',str(self.paper)],check=True)
        (self.paper/'paper.tex').write_bytes(SOURCE)
        association=preview_association(self.paper,'paper.tex','anchor',self.directory)
        project=ProjectWork.create(PaperWork.create(history()),association)
        self.store=PersonalProjectStore.create(self.directory,project_id='cache-study').__enter__()
        self.addCleanup(self.store.close); self.store.save(project,preview=association)
        self.app=project_workspace(project); self.app.recovery=PersonalProjectRecovery(self.store,self.app,project)
        enable(self.app)
        self.size=[24,80]
        with patch.object(Terminal,'setup_styles'):
            self.terminal=Terminal(SimpleNamespace(getmaxyx=lambda:tuple(self.size)),self.app,SimpleNamespace(flushinp=lambda:None))
        self.ui=proposals_ui(self.terminal)

    def frame(self): return self.terminal.draw_modal(Frame(self.size[1],self.size[0])).plain()

    def read_end(self):
        self.frame(); self.terminal.key('end'); return self.frame()

    def response(self,include_draft=False):
        self.terminal.modal=None
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}
        if include_draft: self.terminal.key('d')
        self.terminal.key('enter'); self.read_end(); self.terminal.key('enter')
        self.ui.worker.complete(self.ui.outbound.request_id)
        self.ui.pending=[]; self.ui.enter('current')

    def stage(self,item):
        self.ui.chosen={item}; self.terminal.key('c'); self.read_end(); self.terminal.key('enter')
        return self.app.review.candidates()

    def reasoning(self):
        self.app.keep_draft('CPU-B remains untested.','Only CPU-A was measured.')
        p=personal_ui(self.terminal); p.enter('reasoning'); self.read_end()
        return p

    def test_blank_judgment_request_exact_context_read_gate_and_cancel(self):
        source=self.app.paper.history.manifest()
        self.terminal.key('A'); self.assertEqual('proposal-context',self.terminal.modal)
        self.ui.checked={'thesis','obs-a'}; self.terminal.key('d'); self.terminal.key('enter')
        self.terminal.key('enter')
        self.assertFalse(self.ui.worker._entry['dispatched'])
        self.assertIn('complete comparison',self.ui.notice)
        request=decode(self.ui.outbound.payload)
        self.assertIn('6 ms versus 15 ms',str(request))
        self.assertIn('Mean elapsed time',str(request))
        self.assertIn('unverified',str(request))
        self.assertEqual({'thesis','obs-a',self.ui.worker.session._draft_id},
                         {r['id'] for r in request['context']['records']})
        self.read_end(); self.terminal.key('escape')
        self.assertEqual([],self.app.paper.proposal_history())
        self.assertEqual({'text':'','rationale':''},self.app.draft())
        self.assertEqual(source,self.app.paper.history.manifest())
        self.assertFalse(self.app.paper.ai_available)

    def test_dependency_comparison_graph_read_and_existing_edit_retains_origin(self):
        self.response(); self.ui.chosen={'repeat'}; self.terminal.key('c')
        self.assertEqual(['narrow'],self.ui.comparison['required_item_ids'])
        self.terminal.key('enter'); self.assertEqual({},self.app.review.candidates().records)
        self.assertIn('OMITTED RESPONSE ITEMS','\n'.join(self.ui.content('compare')))
        self.terminal.key('G'); self.assertIn('AI ITEM COMPARISON',self.frame())
        self.terminal.key('tab'); self.size[:]=[38,132]; self.assertIn('BEFORE',self.frame())
        self.terminal.key('escape'); self.read_end(); self.terminal.key('enter')
        work=self.app.review.candidates(); self.assertEqual(2,len(work.records))
        self.terminal.key('e'); editor=candidates_ui(self.terminal)
        key=next(k for k,r in work.records.items() if r['kind']=='claim')
        editor.index=list(editor.items()).index(key); self.terminal.key('enter')
        editor.index=editor.fields.index('statement'); self.terminal.key('enter')
        self.terminal.key(('paste',' Human qualification.')); self.terminal.key('keep'); self.terminal.key('keep')
        self.assertTrue(work.origins[key].ai_influenced)
        self.assertEqual(2,len(decode(work.origins[key].payload)['revisions']))
        self.assertIn('Human qualification.',work.records[key]['body']['statement'])
        self.assertEqual(1,self.app.paper.history.watermark)
        self.assertEqual(SOURCE,(self.paper/'paper.tex').read_bytes())

    def test_staging_independent_sibling_and_cancelling_comparison(self):
        self.response(); self.stage('limit'); self.ui.chosen={'narrow'}; self.terminal.key('c')
        self.terminal.key('escape'); self.assertEqual(1,len(self.app.review.candidates().records))
        self.stage('narrow'); self.assertEqual(2,len(self.app.review.candidates().records))
        self.terminal.key('x'); self.assertIsNone(self.terminal.modal)
        self.assertEqual(2,len(self.app.review.candidates().records))
        self.assertEqual('cancelled',self.app.paper.proposal_history()[0]['disposition'])

    def test_included_draft_change_and_atomic_stage_failure_keep_writing(self):
        self.response(include_draft=True); self.app.keep_draft('Newer thought.','Newer reason.')
        self.ui.chosen={'limit'}; self.terminal.key('c')
        self.assertEqual('proposal-items',self.terminal.modal)
        self.assertIn('input changed',self.ui.notice)
        self.terminal.key('x')  # Explicitly decline the old items before requesting replacement.
        self.response(); self.ui.chosen={'repeat'}; self.terminal.key('c'); self.read_end()
        with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full checkpoint')):
            self.terminal.key('enter')
        self.assertEqual({},self.app.review.candidates().records)
        self.assertEqual('Newer thought.',self.app.draft()['text'])

    def test_tiny_pause_then_record_requires_explicit_explanation_choice(self):
        self.response(); self.stage('limit'); p=self.reasoning()
        self.assertIn('not-reviewed','\n'.join(p.rows(74)))
        self.assertNotIn('recorded as deferred','\n'.join(p.rows(74)))
        self.terminal.key('enter'); self.assertEqual(3,len(self.app.paper.history.commands))
        self.size[:]=[12,40]; self.terminal.key('2'); self.assertIn('paused',self.frame())
        self.size[:]=[24,80]; self.terminal.key('2')
        self.assertEqual('leave-for-later',p.preview.display['explanation']['state'])
        self.terminal.key('enter'); self.assertEqual(3,len(self.app.paper.history.commands))
        self.read_end(); self.terminal.key('enter')
        self.assertEqual('leave-for-later',self.app.paper.recorded_origins()[0]['explanation']['state'])
        self.assertFalse(self.app.paper.ai_available)
        self.assertFalse(available(self.app))
        self.assertEqual('Only CPU-A was measured.',self.app.paper.history.view('main')['judgment']['rationale'])

    def test_partial_topic_checkpoint_source_cursor_restart_and_explicit_reuse(self):
        self.response(); self.stage('limit'); p=self.reasoning(); self.terminal.key('1'); self.terminal.key('enter')
        self.terminal.key(('paste','CPU-B는 아직 확인하지 않았다.'))
        buffer=self.terminal.buffers[0]; cursor=buffer.cursor
        self.terminal.key('source'); self.assertIn('ORIGINAL / CURRENT',self.frame())
        self.assertTrue(self.terminal.checkpoint())
        self.assertEqual('partial',self.app.paper._personal_explanations[0]['explanation']['state'])
        self.terminal.key('escape'); self.assertIs(buffer,self.terminal.buffers[0]); self.assertEqual(cursor,buffer.cursor)
        self.terminal.key('keep'); self.terminal.key('escape')
        self.assertEqual('personal-preview',self.terminal.modal)
        self.read_end(); self.terminal.key('1')
        for i in range(len(p.topics)):
            p.topic_index=i; self.terminal.key('r')
        self.terminal.key('v'); self.assertEqual('reviewed',p.preview.display['explanation']['state'])
        self.read_end(); self.terminal.key('enter'); self.assertIsNone(self.terminal.modal)
        self.assertEqual('reviewed',self.app.paper.recorded_origins()[0]['explanation']['state'])
        self.app.recovery.save(self.app)
        reopened=project_workspace(self.store.load()); self.assertFalse(reopened.paper.ai_available)
        self.assertEqual('CPU-B는 아직 확인하지 않았다.',reopened.paper._personal_explanations[0]['explanation']['entries'][0]['text'])
        self.terminal.app=reopened; del self.terminal._personal_ui
        p=personal_ui(self.terminal); p.enter('explanations'); self.terminal.key('enter')
        self.assertIn('CPU-B는 아직',str(p.entries)); self.assertTrue(p.historical_explanation)
        self.terminal.key('v'); self.assertEqual('personal-topics',self.terminal.modal)

    def test_history_and_origin_after_restart_never_restore_incorporation(self):
        self.response(); self.stage('limit'); self.app.recovery.save(self.app)
        reopened=project_workspace(self.store.load()); self.terminal.app=reopened
        del self.terminal._proposals_ui; ui=proposals_ui(self.terminal)
        menu=actions_ui(self.terminal)
        self.assertTrue(next(a for a in menu.items() if a.key=='A').unavailable)
        ui.enter('history'); self.terminal.key('enter')
        self.assertIn('reading only','\n'.join(ui.content('history-detail')))
        original=reopened.paper.history.manifest(); self.terminal.key('enter')
        self.assertEqual(original,reopened.paper.history.manifest())
        ui.enter('origins'); rows='\n'.join(ui.content('origins'))
        self.assertIn('CPU-B remains unmeasured',rows)
        self.assertEqual({},ui.controllers)

    def test_failed_partial_save_retains_live_buffer_and_original_scope(self):
        self.response(); self.stage('limit'); p=self.reasoning(); self.terminal.key('1'); self.terminal.key('enter')
        self.terminal.key(('paste','새로운 미완성 설명'))
        with patch('claimbranch.application.paper_proposal_work.check_capacity',side_effect=ContractError('full checkpoint')):
            self.terminal.key('keep')
        self.assertEqual('personal-explanation-edit',self.terminal.modal)
        self.assertEqual('새로운 미완성 설명',self.terminal.buffers[0].text)
        self.assertEqual([],self.app.paper._personal_explanations)
        self.terminal.key('keep'); self.assertEqual('personal-topics',self.terminal.modal)

    def test_historical_partial_edit_cannot_overwrite_recorded_review_choice(self):
        self.response(); self.stage('limit'); p=self.reasoning(); self.terminal.key('2'); self.read_end(); self.terminal.key('enter')
        recorded=deepcopy(self.app.paper.recorded_origins())
        with self.assertRaises(ContractError): p.service.prepare('reasoning',explanation_state='leave-for-later')
        p.enter('explanations'); self.terminal.key('enter'); self.terminal.key('enter')
        self.terminal.key(('paste','Further unanswered question.')); self.terminal.key('keep')
        self.app.recovery.save(self.app)
        self.assertEqual(recorded,self.app.paper.recorded_origins())
        self.assertEqual('partial',self.app.paper._personal_explanations[0]['explanation']['state'])

    def test_cancelled_late_reply_is_history_and_failed_reply_leaves_waiting(self):
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}
        self.terminal.key('enter'); self.read_end(); self.terminal.key('enter')
        self.terminal.key('escape'); worker,request,_=self.ui.pending[0]
        self.ui.pending=[(worker,request,-1)]; self.assertTrue(self.ui.poll())
        self.assertIn('history (cancelled)',self.app.message)
        self.assertIsNone(self.terminal.modal)
        self.app.offline_assistance_result=lambda request:b'{bad'
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}
        self.terminal.key('enter'); self.read_end(); self.terminal.key('enter')
        worker,request,_=self.ui.pending[0]; self.ui.pending=[(worker,request,-1)]
        self.ui.poll(); self.assertEqual('proposal-history-detail',self.terminal.modal)
        self.assertEqual('malformed',self.ui.entry['disposition'])
        self.assertEqual({},self.app.review.candidates().records)

    def test_partial_return_with_changed_judgment_preserves_old_cause_and_can_exit(self):
        self.response(); self.stage('limit'); p=self.reasoning(); self.terminal.key('1'); self.terminal.key('enter')
        self.terminal.key(('paste','Original unfinished explanation.')); self.terminal.key('keep')
        old=deepcopy(self.app.paper._personal_explanations)
        self.app.keep_draft('A different judgment.','A new reason.')
        self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)
        self.assertEqual(old,self.app.paper._personal_explanations)
        self.assertEqual('Only CPU-A was measured.',old[0]['cause']['judgment']['rationale'])

    def test_work_review_routes_item_origin_to_the_complete_personal_consequence(self):
        self.response(); self.stage('limit'); self.terminal.key('escape')
        self.app.keep_draft('CPU-B remains untested.','Only CPU-A was measured.')
        self.terminal.key('w')
        self.assertIn('AI ITEM ORIGIN',str(self.app.review.lines()))
        self.terminal.key('R')
        self.assertEqual('personal-preview',self.terminal.modal)
        self.assertTrue(personal_ui(self.terminal).preview.display['ai_origin_retained'])
        self.assertFalse(personal_ui(self.terminal).preview.display['recording_available'])

    def test_expired_consequence_keeps_first_partial_without_reviving_recording(self):
        self.response(); self.stage('limit'); p=self.reasoning()
        expired=p.preview
        self.terminal.key('1'); self.terminal.key('enter')
        self.terminal.key(('paste','Five minutes later, this question is still unfinished.'))
        p.service.clock=lambda:expired.expires_at+1
        self.assertTrue(self.terminal.checkpoint())
        self.assertFalse(self.app.uncheckpointed_editor)
        self.terminal.key('escape')
        self.assertEqual('personal-topics',self.terminal.modal)
        self.assertIn('Five minutes later',str(self.app.paper._personal_explanations))
        self.assertEqual(3,len(self.app.paper.history.commands))
        with self.assertRaises(ContractError): p.service.commit(expired)
        self.app.recovery.save(self.app)
        self.assertIn('Five minutes later',str(project_workspace(self.store.load()).paper._personal_explanations))

    def test_explanation_return_list_reloads_latest_partial_and_keeps_recorded_choice(self):
        self.response(); self.stage('limit'); p=self.reasoning()
        self.terminal.key('2'); self.read_end(); self.terminal.key('enter')
        recorded=deepcopy(self.app.paper.recorded_origins())
        p.enter('explanations'); self.terminal.key('enter'); self.terminal.key('enter')
        self.terminal.key(('paste','Newer human writing.')); self.terminal.key('keep')
        self.terminal.key('escape')
        self.assertEqual('personal-explanations',self.terminal.modal)
        self.terminal.key('enter'); self.terminal.key('enter')
        self.assertEqual('Newer human writing.',self.terminal.buffers[0].text)
        self.terminal.key('escape'); self.terminal.key('escape')
        self.assertEqual(1,len(p.contexts))
        self.assertEqual('leave-for-later',p.contexts[0]['recorded_explanation']['state'])
        self.assertEqual(recorded,self.app.paper.recorded_origins())
        self.assertEqual('Newer human writing.',self.app.paper._personal_explanations[0]['explanation']['entries'][0]['text'])

    def test_noncurrent_reply_returns_to_a_fresh_history_list(self):
        self.app.offline_assistance_result=lambda request:b'{bad'
        self.terminal.key('A'); self.ui.checked={'thesis','obs-a'}
        self.terminal.key('enter'); self.read_end(); self.terminal.key('enter')
        worker,request,_=self.ui.pending[0]; self.ui.pending=[(worker,request,-1)]
        self.ui.poll(); self.terminal.key('escape')
        self.assertIn('AI RESPONSE HISTORY',self.frame())
        self.assertEqual([request],[e['request_id'] for e in self.ui.history])
        self.assertEqual('malformed',self.ui.history[0]['disposition'])

    def test_reviewed_choice_after_scope_change_retains_original_editable_topics(self):
        self.response(); self.stage('limit'); p=self.reasoning(); self.terminal.key('1')
        for i in range(len(p.topics)):
            p.topic_index=i; self.terminal.key('r')
        cause=deepcopy(p.cause)
        self.app.keep_draft('A different judgment.','Changed reason.')
        self.terminal.key('v')
        self.assertEqual('personal-topics',self.terminal.modal)
        self.assertIsNone(p.preview)
        self.assertIsNone(p.service.pending)
        self.assertEqual(cause,p.cause)
        self.terminal.key('enter'); self.terminal.key(('paste','Still writing on the original cause.'))
        self.terminal.key('keep'); self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)
        self.assertIn('Still writing',str(self.app.paper._personal_explanations))
        self.assertEqual(3,len(self.app.paper.history.commands))

    def test_rehearsal_eof_cancels_and_initialization_failure_preserves_owned_partial(self):
        from claimbranch.application.paper_assistance_example import run
        root=self.root/'rehearsal'; root.mkdir(mode=0o700)
        args=SimpleNamespace(snapshot=False,directory=str(root),create=True,ai_off=False)
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch.dict('os.environ',{'TERM':'xterm'}):
            with patch('builtins.input',side_effect=EOFError):
                self.assertEqual(0,run(args))
            self.assertEqual([],list(root.iterdir()))
            with patch('builtins.input',return_value='create'),patch('subprocess.run',side_effect=OSError('Git unavailable')):
                with self.assertRaisesRegex(ContractError,'fresh private folder'): run(args)
            self.assertEqual({'paper','work'},{p.name for p in root.iterdir()})
            with self.assertRaisesRegex(ContractError,'existing paper/work children'): run(args)


if __name__=='__main__': unittest.main()
