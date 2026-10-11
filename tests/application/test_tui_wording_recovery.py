"""Wording survives restart under its original source, without review authority."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_manuscript_ui import manuscript_ui
from claimbranch.application.tui_work_recovery import snapshot, restore, JudgmentRecovery
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.fixtures import replay_example, replay_merge_example

SOURCE = '% Cafe\u0301\r\n% claimbranch:start id=anchor\nOriginal.\n% claimbranch:end id=anchor\n% suffix\r\n'.encode()


class WordingRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        self.t = self.terminal(self.app)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'source.tex'
        self.path.write_bytes(SOURCE)

    def terminal(self, app):
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (42, 144))
        return t

    def open(self):
        item = next(x for x in self.app.service.pending_work()['items'] if x['kind'] == 'manuscript')
        manuscript_ui(self.t).open(item)
        self.app.manuscript.load_source(str(self.path))
        return self.app.manuscript.session

    def reopen(self, saved=None):
        saved = saved or snapshot(self.app)
        app = TerminalWorkspace(saved.history, ai_off=True)
        restore(app, saved)
        app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None), app)
        return app, self.terminal(app)

    def test_recorded_wording_source_and_empty_unfinished_input_restore(self):
        session = self.open()
        session.draft.edit('Kept wording.', 'Original reason.')
        self.t.key('e')
        for b in self.t.buffers: b.text, b.cursor = '', 0
        self.t.key('escape')
        app, t = self.reopen()
        manuscript_ui(t).open_saved()
        t.key('enter'); t.key('e')
        self.assertEqual(['', ''], [b.text for b in t.buffers])
        self.assertEqual('Kept wording.', app.manuscript.session.draft.state()['draft']['text'])
        self.assertEqual(SOURCE, app.manuscript.session._source)
        self.assertIsNone(app.manuscript.session.get_preview())
        self.assertIsNone(app.manuscript.session.get_review())
        self.assertEqual(self.app.paper.history.manifest(), app.paper.history.manifest())

    def test_active_basis_view_checkpoint_keeps_input_and_field(self):
        self.open()
        saved = []
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append), self.app)
        self.t.key('e'); self.t.key(('paste', '한글 미완성'))
        self.t.key('tab'); self.t.key(('paste', 'scope')); self.t.key('source')
        self.assertTrue(self.t.checkpoint(), self.app.recovery_error)
        app, t = self.reopen(saved[-1])
        manuscript_ui(t).open_saved(); t.key('enter'); t.key('e')
        self.assertEqual(['한글 미완성', 'scope'], [b.text for b in t.buffers])
        self.assertEqual(1, t.field)

    def test_missing_or_changed_source_keeps_original_bytes_and_writing(self):
        self.open().draft.edit('Retained wording.', 'Reason.')
        saved = snapshot(self.app)
        for source in (None, SOURCE + b'% different\n'):
            if source is None: self.path.unlink()
            else: self.path.write_bytes(source)
            app, t = self.reopen(saved)
            manuscript_ui(t).open_saved(); t.key('enter'); t.key('R')
            self.assertIsNone(app.manuscript.session.get_preview())
            self.assertEqual(SOURCE, app.manuscript.session._source)
            self.assertEqual('Retained wording.', app.manuscript.session.draft.state()['draft']['text'])

    def test_detached_wording_is_reachable_but_original_parent_is_not_revived(self):
        self.app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        self.t = self.terminal(self.app)
        flow = self.app.branches.open_recorded(); flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        preview = flow.prepare_merge(); flow.finish(preview['digest'], 'deferred', [])
        original = self.app.manuscript.open_candidate(flow)
        original.draft.edit('Candidate wording.', 'Candidate reason.')
        key = self.app.manuscript.work_id
        app, t = self.reopen()
        manuscript_ui(t).open_saved(); t.key('enter')
        self.assertEqual(key, app.manuscript.work_id)
        self.assertEqual(original.state()['work'], app.manuscript.session.state()['work'])
        self.assertFalse(app.branches.flows)
        t.key('R'); self.assertIsNone(app.manuscript.session.get_preview())
        self.assertIn('EARLIER SCIENTIFIC BASIS', t.draw_modal(Frame(144, 42)).plain())
        t.key('e'); t.key(('paste', ' More')); t.key('keep')
        self.assertIn('More', app.manuscript.session.draft.state()['draft']['text'])
        self.assertEqual(self.app.service.pending_work(), app.service.pending_work())

    def test_shared_large_source_is_stored_once_across_detached_drafts(self):
        self.app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        source = b'%' + b'x' * (65536 - len(SOURCE) - 2) + b'\n' + SOURCE
        self.path.write_bytes(source)
        flow = self.app.branches.open_recorded(); flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        for index in range(3):
            preview = flow.prepare_merge(); flow.finish(preview['digest'], 'deferred', [])
            self.app.manuscript.open_candidate(flow).draft.edit('Wording ' + str(index), 'Reason.')
        saved = snapshot(self.app)
        self.assertEqual(1, len(decode(saved.payload)['workspace']['manuscript']['sources']))
        app, _ = self.reopen(saved)
        self.assertEqual(3, len(app.manuscript.sessions))
        for session in app.manuscript.sessions.values(): self.assertEqual(source, session._source)

    def test_detached_missing_source_reports_historical_parent_first(self):
        self.app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        flow = self.app.branches.open_recorded(); flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        p = flow.prepare_merge(); flow.finish(p['digest'], 'deferred', [])
        self.app.manuscript.open_candidate(flow).draft.edit('Word.', 'Reason.')
        app, t = self.reopen(); self.path.unlink()
        manuscript_ui(t).open_saved(); t.key('enter'); t.key('R')
        self.assertIn('prepare new science', manuscript_ui(t).notice)

    def test_authored_detached_parent_retains_owner_and_rendering_keeps_draft(self):
        self.app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        self.app.switch_ref(); self.app.select('interpretation-two')
        self.app.keep_draft('My interpretation.', 'Other masks remain unmeasured.')
        self.app.review.stage_judgment('interpretation-two')
        flow = self.app.branches.prepare_branch(); flow.materialize()
        flow.load_source(str(self.path))
        p = flow.prepare_merge(); flow.finish(p['digest'], 'deferred', [])
        session = self.app.manuscript.open_candidate(flow)
        session.draft.edit('Wording.', 'Reason.')
        session.draft._before_proposal = {'text': 'Earlier text', 'rationale': 'Earlier reason'}
        app, t = self.reopen()
        manuscript_ui(t).open_saved(); t.key('enter')
        self.assertEqual(flow.owner_key, app.manuscript.parents[app.manuscript.work_id]['owner'])
        before = app.manuscript.session.draft.state()
        for width, height in ((144, 42), (80, 24), (48, 18)):
            t.draw_modal(Frame(width, height))
        self.assertEqual(before, app.manuscript.session.draft.state())

    def test_active_answer_is_disclosed_and_does_not_break_wording_checkpoint(self):
        from claimbranch.application.tui_work_recovery import excluded_work
        self.open().draft.edit('Word.', 'Reason.')
        self.t.key('R'); self.t.key('enter'); self.t.key('1')
        self.t.key(('paste', ' additional explanation'))
        saved = []
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append), self.app)
        self.assertTrue(self.t.checkpoint())
        self.assertIn('unfinished research editor text', excluded_work(self.app))
        self.assertNotIn('additional explanation', saved[0].payload.decode())
        self.assertIn('Word.', saved[0].payload.decode())

    def test_pristine_reading_creates_no_saved_draft(self):
        self.open(); self.t.key('e'); self.t.key('escape')
        app, _ = self.reopen()
        self.assertFalse(app.manuscript.sessions)

    def test_discard_names_one_draft_and_requires_confirmation(self):
        self.open().draft.edit('Word.', 'Reason.')
        app, t = self.reopen()
        pending = app.service.pending_work()
        ui = manuscript_ui(t); ui.open_saved()
        t.key('d'); t.key('escape')
        self.assertEqual(1, len(app.manuscript.sessions))
        t.key('d'); t.key(('paste', 'enter'))
        self.assertEqual(1, len(app.manuscript.sessions))
        t.key('enter')
        self.assertFalse(app.manuscript.sessions)
        self.assertFalse(app.manuscript.parents)
        self.assertFalse(app.manuscript.restored)
        self.assertEqual(pending, app.service.pending_work())
        self.assertEqual(SOURCE, self.path.read_bytes())
        self.assertFalse(decode(snapshot(app).payload)['workspace']['manuscript']['sources'])

    def test_empty_source_edit_is_retained_work_and_blocks_overwrite(self):
        self.open(); self.t.key('s')
        self.t.buffers[0].text, self.t.buffers[0].cursor = '', 0
        self.t.key('escape')
        self.assertTrue(self.app.manuscript.volatile_work())
        saved = snapshot(self.app)
        with self.assertRaises(ContractError): restore(self.app, saved)
        app, t = self.reopen(saved)
        manuscript_ui(t).open_saved(); t.key('enter'); t.key('s')
        self.assertEqual('', t.buffers[0].text)

    def test_malformed_binding_refuses_before_installation(self):
        self.open().draft.edit('Wording.', 'Reason.')
        value = decode(snapshot(self.app).payload)
        for field, bad in (('work_id', 'unknown'), ('source_digest', '0' * 64)):
            changed = deepcopy(value)
            changed['workspace']['manuscript']['sessions'][0][field] = bad
            with self.assertRaises(ContractError): PaperWork(canonical_bytes(changed))

    def test_unchanged_recorded_source_requires_new_review_and_preserves_ai(self):
        session = self.open(); session.draft.edit('Wording.', 'Reason.')
        old = self.app.manuscript.prepare()
        self.app.manuscript.finish(old['digest'], 'deferred', [])
        app, t = self.reopen()
        manuscript_ui(t).open_saved(); t.key('enter')
        self.assertIsNone(app.manuscript.session.get_review())
        t.key('R')
        fresh = app.manuscript.session.get_preview()
        self.assertIsNotNone(fresh)
        self.assertNotEqual(old['digest'], fresh['digest'])
        self.assertTrue(fresh['ai_influenced'])
        self.assertEqual(SOURCE.decode(), fresh['source']['before'])
        self.assertEqual(SOURCE, self.path.read_bytes())

    def test_legacy_v5_and_unwritten_review_answer_exclusions(self):
        from claimbranch.application.tui_work_recovery import excluded_work
        self.open().draft.edit('Word.', 'Reason.')
        self.t.key('R'); self.t.key('enter'); self.t.key('1')
        self.t.key(('paste', ' explanation')); self.t.key('escape')
        self.assertIn('manuscript review answers', excluded_work(self.app))
        saved = snapshot(self.app)
        app, _ = self.reopen(saved)
        self.assertFalse(any(mode == 'answer' for _, mode in app.manuscript.buffers))
        value = decode(saved.payload)
        value['schema'] = 'claimbranch.paper-work/v5'
        value['workspace']['schema'] = 'claimbranch.review-writing-workspace/v4'
        value['workspace'].pop('manuscript')
        from claimbranch.application.paper_review_writing_snapshot import writing_snapshot
        value['workspace']['review_writing'] = writing_snapshot(self.app)
        app, _ = self.reopen(PaperWork(canonical_bytes(value)))
        self.assertFalse(app.manuscript.sessions)

    def test_failed_save_keeps_live_editor_and_prior_checkpoint(self):
        self.open().draft.edit('Before.', 'Reason.')
        class Store:
            def __init__(self): self.saved, self.fail = None, False
            def load(self): return None
            def save(self, value):
                if self.fail: raise OSError('injected replacement failure')
                self.saved = value
        store = Store(); self.app.recovery = JudgmentRecovery(store, self.app)
        self.assertTrue(self.t.checkpoint())
        prior = store.saved.payload; store.fail = True
        self.t.key('e'); self.t.key(('paste', ' unsaved'))
        self.assertFalse(self.t.checkpoint())
        self.assertEqual(prior, store.saved.payload)
        self.assertEqual('Before. unsaved', self.t.buffers[0].text)
        self.assertIn('injected replacement failure', self.t.draw_modal(Frame(144, 42)).plain())

    def test_source_bytes_and_capacity_fail_without_silent_truncation(self):
        session = self.open(); session.draft.edit('Word.', 'Reason.')
        source = b'% prefix\r\n' * 2000 + SOURCE
        session.update_source(self.app.paper.history, source=source)
        app, _ = self.reopen()
        self.assertEqual(source, app.manuscript.sessions[self.app.manuscript.work_id]._source)
        # Per-field UTF-8 limits also apply to unfinished writing.
        self.app.manuscript.buffers[self.app.manuscript.work_id, 'wording'] = ['가' * 6000, '']
        with self.assertRaises(ContractError): snapshot(self.app)
        self.assertEqual('가' * 6000, self.app.manuscript.buffers[self.app.manuscript.work_id, 'wording'][0])


if __name__ == '__main__': unittest.main()
