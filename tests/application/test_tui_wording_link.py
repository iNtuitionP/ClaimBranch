"""Selected science reaches wording without installing history or retyping judgment."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_branch import TerminalBranches
from claimbranch.application.tui_branch_ui import branch_ui
from claimbranch.application.tui_manuscript import TerminalManuscript
from claimbranch.application.tui_manuscript_ui import manuscript_ui
from claimbranch.application.paper_workspace import PaperWorkspace
from claimbranch.application.tui_recovery import DraftRecovery
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_merge_example


SOURCE = b'% claimbranch:start id=anchor\nOld wording.\n% claimbranch:end id=anchor\n'


class WordingLinkTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_merge_example('recorded')
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.now = 1790208000
        self.app.paper = PaperWorkspace(self.history, clock=lambda: self.now)
        self.app.branches = TerminalBranches(self.app, clock=lambda: self.now)
        self.app.manuscript = TerminalManuscript(self.app, clock=lambda: self.now)
        self.t = Terminal.__new__(Terminal)
        self.t.app, self.t.modal = self.app, None
        self.t.screen = SimpleNamespace(getmaxyx=lambda: (42, 144))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'paper.tex'
        self.path.write_bytes(SOURCE)
        self.original = self.history.manifest()
        self.pending = self.app.service.pending_work()

    def reviewed(self, *, authored=False):
        if authored:
            self.app.switch_ref()
            self.app.select('interpretation-two')
            self.app.keep_draft('I limit this interpretation to the measured mask.', 'Other masks are unmeasured.')
            self.app.review.stage_judgment('interpretation-two')
            flow = self.app.branches.prepare_branch()
            flow.materialize()
        else:
            flow = self.app.branches.open_recorded()
            flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        prepared = flow.prepare_merge()
        reviewed = flow.finish(prepared['digest'], 'deferred' if prepared['preview']['provenance']['ai_influenced'] else 'not-required', [])
        return flow, reviewed

    def open(self, flow):
        branch_ui(self.t).flow = flow
        self.t.modal = 'branch-review'
        self.t.key('m')
        self.assertEqual('manuscript-choose', self.t.modal)
        self.t.key('enter')
        self.assertEqual('manuscript-read', self.t.modal)
        return self.app.manuscript.session

    def test_authored_judgment_to_exact_wording_reuses_reason_and_returns(self):
        flow, reviewed = self.reviewed(authored=True)
        nav = self.app._navigation()
        session = self.open(flow)
        self.assertEqual('', session.state()['draft']['draft']['text'])
        self.assertEqual(self.app.draft()['text'], session.state()['work']['judgment']['text'])
        self.t.key('e')
        self.t.key(('paste', '한글: the conclusion is limited to this mask.'))
        self.t.key('reuse-reason')
        self.assertEqual(self.app.draft()['rationale'], self.t.buffers[1].text)
        self.t.key('keep')
        self.t.key('R')
        preview = session.get_preview()
        self.assertEqual(SOURCE.decode(), preview['source']['before'])
        self.assertIn('+한글:', preview['source']['diff'])
        self.assertTrue(preview['ai_influenced'])
        self.t.key('enter'); self.t.key('1'); self.t.key('keep')
        self.assertIsNotNone(session.get_review())
        self.t.key('escape')
        self.assertEqual('branch-review', self.t.modal)
        self.assertEqual(nav, self.app._navigation())
        self.assertEqual(self.original, self.app.paper.history.manifest())
        self.assertEqual(self.pending, self.app.service.pending_work())
        self.assertEqual(SOURCE, self.path.read_bytes())

    def test_parent_expiry_retains_text_and_blocks_child_review(self):
        flow, _ = self.reviewed()
        session = self.open(flow)
        session.draft.edit('Earlier wording.', 'Measured scope.')
        preview = self.app.manuscript.prepare()
        self.now += 301
        with self.assertRaises(ContractError):
            self.app.manuscript.finish(preview['digest'], 'deferred', [])
        self.assertIsNone(session.get_preview())
        self.assertEqual('Earlier wording.', session.state()['draft']['draft']['text'])
        self.t.key('escape')
        self.t.key('m'); self.t.key('down'); self.t.key('enter')
        self.assertEqual('manuscript-read', self.t.modal)
        self.assertIn('Earlier wording.', self.t.draw_modal(Frame(144, 42)).plain())

    def test_parent_expiring_during_candidate_construction_is_a_notice_not_a_crash(self):
        flow,_=self.reviewed()
        build=flow.build_candidate
        def expire_after_build(review_digest):
            candidate=build(review_digest)
            self.now += 301
            return candidate
        flow.build_candidate=expire_after_build
        with self.assertRaises(ContractError):
            self.app.manuscript.open_candidate(flow)
        self.assertFalse(self.app.manuscript.parents)

    def test_new_review_preserves_separate_earlier_wording_without_scope_transfer(self):
        flow, _ = self.reviewed()
        old = self.open(flow)
        old.draft.edit('Previous wording.', 'Previous reason.')
        old_key = self.app.manuscript.work_id
        flow.toggle('edge-pruning')
        prepared = flow.prepare_merge()
        flow.finish(prepared['digest'], 'deferred', [])
        new = self.open(flow)
        self.assertIsNot(old, new)
        self.assertEqual('', new.state()['draft']['draft']['text'])
        self.assertEqual('Previous wording.', self.app.manuscript.sessions[old_key].state()['draft']['draft']['text'])
        self.assertEqual(2, len(self.app.manuscript.candidate_items(flow)))

    def test_source_changes_reject_candidate_wording_without_writing_files(self):
        flow, _ = self.reviewed()
        session = self.open(flow)
        session.draft.edit('Kept wording.', 'Measured scope.')
        preview = self.app.manuscript.prepare()
        self.path.write_bytes(SOURCE + b'% external edit\n')
        with self.assertRaises(ContractError):
            self.app.manuscript.finish(preview['digest'], 'deferred', [])
        self.assertIsNone(session.get_preview())
        self.assertEqual('Kept wording.', session.state()['draft']['draft']['text'])
        self.assertEqual(SOURCE + b'% external edit\n', self.path.read_bytes())

    def test_context_and_explicit_reason_replacement_preserve_undo_and_editor(self):
        flow, _ = self.reviewed(authored=True)
        session = self.open(flow)
        self.t.key('e')
        self.t.key(('paste', '한글 wording'))
        self.t.key('tab'); self.t.key(('paste', 'A specific wording reason.'))
        buffers = self.t.buffers
        self.t.key('reuse-reason')
        self.assertEqual('manuscript-reason', self.t.modal)
        self.t.key('escape')
        self.assertEqual('A specific wording reason.', buffers[1].text)
        self.t.key('reuse-reason'); self.t.key('enter')
        self.assertEqual('Other masks are unmeasured.', buffers[1].text)
        self.t.key('undo')
        self.assertEqual('A specific wording reason.', buffers[1].text)
        self.t.key('left')
        cursor = buffers[1].cursor
        self.t.key('source')
        for w,h in ((144,42),(80,24),(48,18)):
            self.assertIn('SCIENTIFIC BASIS', self.t.draw_modal(Frame(w,h)).plain())
        for event in ('keep', ('paste','hidden'), 'reuse-reason', 'e'):
            self.t.key(event)
        self.t.key('escape')
        self.assertIs(buffers, self.t.buffers)
        self.assertEqual(cursor, buffers[1].cursor)
        self.assertEqual('', session.state()['draft']['draft']['text'])
        self.t.screen.getmaxyx=lambda:(12,36)
        self.t.key('keep'); self.t.key(('paste','hidden'))
        self.assertEqual('한글 wording', buffers[0].text)
        self.t.key('escape')
        self.assertEqual('manuscript-read',self.t.modal)

    def test_candidate_writing_is_excluded_from_manual_recovery(self):
        flow, _ = self.reviewed()
        self.open(flow)
        self.t.key('e'); self.t.key(('paste','Private candidate wording.')); self.t.key('escape')
        path = Path(self.folder.name) / 'drafts.json'
        store = DraftRecovery(path,self.app)
        self.app.recovery = store
        try:
            self.t.key('e')
            self.assertEqual('manuscript-wording', self.t.modal)
            self.assertTrue(self.t.checkpoint())
            self.t.key('source')
            self.assertTrue(self.t.checkpoint())
            self.t.key('escape'); self.t.key('escape')
        finally:
            store.close()
            self.app.recovery = None
        self.assertNotIn('Private candidate wording.',path.read_text())
        self.assertTrue(self.app.manuscript.volatile_work())
        self.t.modal=None; self.t.key('q')
        self.assertEqual('quit',self.t.modal)

    def test_manual_history_can_review_wording_without_an_ai_explanation(self):
        history = replay_merge_example('manual')
        self.app = self.t.app = TerminalWorkspace(history, ai_off=True)
        flow, _ = self.reviewed()
        session = self.open(flow)
        self.t.key('e'); self.t.key(('paste','Manual wording.')); self.t.key('reuse-reason'); self.t.key('keep')
        self.t.key('R'); self.t.key('enter')
        self.assertEqual('not-required', session.get_review()['disposition'])
        self.assertFalse(session.get_preview()['ai_influenced'])

    def test_reprepared_parent_keeps_old_work_reachable_and_separate_from_recorded_flow(self):
        flow,_=self.reviewed(authored=True)
        session=self.open(flow)
        session.draft.edit('Earlier draft.', 'Earlier reason.')
        self.app.keep_draft('An updated judgment.', 'An updated reason.')
        self.app.review.stage_judgment('interpretation-two')
        newer=self.app.branches.prepare_branch()
        self.assertEqual(1,len(self.app.manuscript.candidate_items(newer)))
        self.assertEqual([],self.app.manuscript.candidate_items(self.app.branches.open_recorded()))
        branch_ui(self.t).flow=newer;self.t.modal='branch-review'
        self.t.key('m');self.t.key('down');self.t.key('enter')
        self.assertIs(session,self.app.manuscript.session)
        self.t.key('R')
        self.assertIsNone(session.get_preview())
        self.assertIn('Earlier draft.',self.t.draw_modal(Frame(144,42)).plain())

    def test_reuse_focuses_reason_for_immediate_undo_without_erasing_wording(self):
        flow,_=self.reviewed()
        self.open(flow);self.t.key('e');self.t.key(('paste','My wording.'))
        self.t.key('reuse-reason');self.t.key('undo')
        self.assertEqual('My wording.',self.t.buffers[0].text)
        self.assertEqual('',self.t.buffers[1].text)

    def test_pristine_browsing_creates_no_unfinished_text_or_duplicate_current_row(self):
        flow,_=self.reviewed()
        self.open(flow);self.t.key('e');self.t.key('source');self.t.key('escape');self.t.key('escape')
        self.assertFalse(self.app.manuscript.buffers)
        self.t.key('escape');self.t.key('m')
        self.assertEqual([None],manuscript_ui(self.t).choices)

    def test_recorded_pending_work_has_the_same_full_basis_reader(self):
        item=next(item for item in self.app.service.pending_work()['items'] if item['kind']=='manuscript')
        manuscript_ui(self.t).open(item)
        self.t.key('e'); self.t.key('source')
        frame=self.t.draw_modal(Frame(80,24)).plain()
        self.assertIn('SCIENTIFIC JUDGMENT',frame)
        self.t.key('escape'); self.t.key('escape')
        self.assertFalse(self.app.manuscript.buffers)

    def test_blank_candidate_sessions_do_not_block_pending_work_or_new_scope(self):
        flow,reviewed=self.reviewed()
        for index in range(16):
            if index:
                p=flow.prepare_merge();flow.finish(p['digest'],'deferred',[])
            self.app.manuscript.open_candidate(flow)
            if index == 0:
                protected = self.app.manuscript.work_id
                self.app.manuscript.session.draft.edit('Retain this writing.', 'Original basis.')
        item=next(item for item in self.app.service.pending_work()['items'] if item['kind']=='manuscript')
        self.app.manuscript.open(item['id'])
        p=flow.prepare_merge();flow.finish(p['digest'],'deferred',[])
        self.app.manuscript.open_candidate(flow)
        self.assertEqual(16,len(self.app.manuscript.parents))
        self.assertIn(item['id'],self.app.manuscript.sessions)
        self.assertEqual('Retain this writing.',self.app.manuscript.sessions[protected].state()['draft']['draft']['text'])
        for key in self.app.manuscript.parents:
            self.app.manuscript.sessions[key].draft.edit('Written candidate.', 'Keep its basis.')
        keys=set(self.app.manuscript.sessions)
        p=flow.prepare_merge();flow.finish(p['digest'],'deferred',[])
        with self.assertRaises(ContractError):
            self.app.manuscript.open_candidate(flow)
        self.assertEqual(keys,set(self.app.manuscript.sessions))
