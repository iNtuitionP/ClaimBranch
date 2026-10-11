import tempfile
from pathlib import Path
from unittest.mock import Mock
import unittest

from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example
from claimbranch.core.canonical import ContractError


class BranchTests(unittest.TestCase):
    def setUp(self):
        from claimbranch.fixtures import replay_merge_example
        self.history = replay_merge_example('recorded')
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None
        self.terminal.screen = Mock()
        self.terminal.screen.getmaxyx.return_value = (42, 144)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'paper.tex'
        self.path.write_bytes(b'Synthetic manuscript snapshot.\r\n')

    def test_example_is_verified_active_prefix_and_original_series_stays_closed(self):
        self.assertEqual('active', self.app.view['episode']['status'])
        full = replay_example('recorded', series=True)
        self.assertEqual(self.history.commands, full.commands[:len(self.history.commands)])
        self.assertEqual('closed', TerminalWorkspace(full).view['episode']['status'])

    def test_selected_merge_preserves_source_and_inherited_ai(self):
        flow = self.app.branches.open_recorded()
        flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        prepared = flow.prepare_merge()
        self.assertEqual(['status-pruning'], prepared['preview']['selection']['selected'])
        self.assertEqual(['edge-pruning', 'interpretation-two'], prepared['preview']['selection']['required'])
        with self.assertRaises(ContractError):
            flow.finish(prepared['digest'], 'not-required', [])
        reviewed = flow.finish(prepared['digest'], 'deferred', [])
        flow.build_candidate(reviewed['digest'])
        self.assertEqual(self.original, self.app.paper.history.manifest())
        self.assertEqual(['manuscript', 'understanding'], [i.kind for i in flow.candidate[1].debts])
        self.assertFalse(flow.candidate[1].authorization_verified)

    def test_link_membership_change_revokes_authored_branch_and_child_merge(self):
        flow = self.branch_flow()
        flow.materialize()
        flow.load_source(str(self.path))
        prepared = flow.prepare_merge()
        flow.finish(prepared['digest'], 'deferred', [])
        owner = self.app.full_context(self.app.work_key())
        self.app.paper.link_work(owner, [owner[2], 'obs-1'])
        with self.assertRaises(ContractError):
            flow.guard()
        self.assertIsNone(flow.merge.get_review())
        self.assertEqual(self.original, self.app.paper.history.manifest())

    def branch_flow(self):
        self.app.switch_ref()
        self.app.select('interpretation-two')
        self.app.keep_draft('The corrected pruning result exceeds the measured budget.',
                            'The fixed split loses 1.2 pp; the replication is unrun.')
        self.app.review.stage_judgment('interpretation-two')
        return self.app.branches.prepare_branch()

    def prepared_merge(self):
        flow = self.app.branches.open_recorded()
        flow.toggle('status-pruning')
        flow.load_source(str(self.path))
        return flow, flow.prepare_merge()

    def test_authored_candidate_uses_explicit_interpretation_and_retains_ai_origin(self):
        flow = self.branch_flow()
        self.assertEqual(['interpretation-two'], flow.branch['preview']['selection']['selected'])
        self.assertTrue(flow.branch['preview']['provenance']['ai_influenced'])
        candidate = flow.materialize()
        self.assertEqual(len(self.history.commands) + 1, len(candidate.commands))
        self.assertIs(candidate, flow.materialize())
        self.assertEqual(self.original, self.app.paper.history.manifest())
        # The current human draft stays human; earlier AI origin survives in the merge provenance.
        self.assertFalse(self.app.review.influenced())
        flow.load_source(str(self.path))
        preview = flow.prepare_merge()
        self.assertEqual(['interpretation-two'], preview['preview']['selection']['selected'])
        self.assertTrue(preview['preview']['provenance']['ai_influenced'])
        self.assertEqual(self.app.draft()['text'], preview['preview']['provenance']['judgment']['text'])
        flow.finish(preview['digest'], 'deferred', [])
        self.app.review.stage_judgment('interpretation-two')
        with self.assertRaises(ContractError):
            flow.build_candidate('old review')
        self.assertIsNone(flow.candidate)
        self.assertIsNone(flow.merge.get_review())

    def test_parent_expiry_and_context_change_cannot_reuse_detached_draft_candidate(self):
        from claimbranch.application.paper_workspace import PaperWorkspace
        from claimbranch.application.tui_branch import TerminalBranches
        self.now = 1790208000
        self.app.paper = PaperWorkspace(self.history, clock=lambda: self.now)
        self.app.branches = TerminalBranches(self.app, clock=lambda: self.now)
        flow = self.branch_flow()
        flow.materialize(); flow.load_source(str(self.path))
        self.now += 250
        prepared = flow.prepare_merge()
        reviewed = flow.finish(prepared['digest'], 'deferred', [])
        self.now += 50
        with self.assertRaises(ContractError):
            flow.build_candidate(reviewed['digest'])
        self.assertIsNone(flow.merge.get_review())
        self.assertIsNone(flow.candidate)
        self.assertTrue(self.app.draft()['text'])

    def test_reselection_file_change_and_missing_file_revoke_review_and_candidate(self):
        for event in ('selection', 'file', 'deleted', 'invalid'):
            with self.subTest(event=event):
                self.path.write_bytes(b'Original source.')
                self.app.branches.flows.clear()
                flow, prepared = self.prepared_merge()
                reviewed = flow.finish(prepared['digest'], 'deferred', [])
                flow.build_candidate(reviewed['digest'])
                if event == 'selection':
                    flow.toggle('edge-pruning')
                elif event == 'deleted':
                    self.path.unlink()
                else:
                    self.path.write_bytes(b'Changed source.' if event == 'file' else b'\xff')
                with self.assertRaises((ContractError, OSError)):
                    flow.build_candidate(reviewed['digest'])
                self.assertIsNone(flow.candidate)
                self.assertIsNone(flow.merge.get_review())
                self.assertEqual(self.original, self.history.manifest())

    def test_closed_example_and_main_draft_fail_with_actionable_messages(self):
        with self.assertRaisesRegex(ContractError, 'b opens the alternative'):
            self.app.branches.prepare_branch()
        closed = TerminalWorkspace(replay_example('recorded', series=True))
        with self.assertRaisesRegex(ContractError, '--merge-example'):
            closed.branches.open_recorded()
        self.assertFalse(closed.branches.volatile_work())

    def test_ui_complete_graphs_and_return_do_not_move_workspace(self):
        from claimbranch.application.tui_branch_ui import branch_ui
        self.app.select('obs-1')
        self.app.graph_pan, self.app.graph_follow = (5, 2), False
        before = self.app._navigation()
        self.terminal.key('M')
        ui = branch_ui(self.terminal)
        keys = list(ui.flow.choices())
        ui.index = keys.index('status-pruning')
        self.terminal.key(' ')
        self.terminal.key('s'); self.terminal.key(('paste', str(self.path))); self.terminal.key('keep')
        self.terminal.key('R')
        self.assertEqual('branch-review', self.terminal.modal)
        self.assertIn('REQUIRED', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.app.graph_spacing = 'spacious'
        self.terminal.key('G')
        self.assertTrue(all(graph.graph_spacing == 'spacious' for graph in ui.graphs.values()))
        self.terminal.key('tab'); self.terminal.key('right')
        self.assertIn('BEFORE', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('escape'); self.terminal.key('enter')
        self.assertEqual('branch-complete', self.terminal.modal)
        self.terminal.key('1')
        self.terminal.key(('paste', ' Additional bounded explanation.'))
        answer = self.terminal.buffers[0].text
        self.terminal.key('escape'); self.terminal.key('enter'); self.terminal.key('1')
        self.assertEqual(answer, self.terminal.buffers[0].text)
        self.terminal.key('keep'); self.terminal.key('v')
        self.assertIn('CANDIDATE CALCULATED', self.terminal.draw_modal(Frame(144, 42)).plain())
        self.terminal.key('escape'); self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)
        self.assertEqual(before, self.app._navigation())
        self.assertEqual(self.original, self.app.paper.history.manifest())
        self.terminal.key('q')
        self.assertEqual('quit', self.terminal.modal)

    def test_repreparing_same_branch_retains_unfinished_editors_but_not_review(self):
        flow = self.branch_flow()
        flow.materialize()
        flow.load_source(str(self.path))
        prepared = flow.prepare_merge()
        flow.finish(prepared['digest'], 'deferred', [])
        flow.buffers['answer'] = ['An unfinished explanation.']
        flow.buffers['source'] = ['An unfinished source path.']
        self.app.review.stage_judgment('interpretation-two')
        replacement = self.app.branches.prepare_branch()
        self.assertEqual(str(self.path), replacement.path)
        self.assertEqual(flow.buffers, replacement.buffers)
        self.assertIsNone(replacement.review())
        self.assertIsNone(replacement.candidate)
        replacement.buffers['answer'][0] = 'Revised.'
        self.assertEqual(['An unfinished explanation.'], flow.buffers['answer'])

    def test_work_keyboard_stages_interpretation_previews_branch_and_restores_context(self):
        self.app.switch_ref()
        self.app.select('interpretation-two')
        self.app.keep_draft('The corrected count exceeds the measured budget.', 'One fixed split only.')
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('J')
        self.assertEqual(self.app.draft()['text'], self.app.review.amendments[self.app.review.key]['interpretation-two']['body']['statement'])
        self.terminal.key('escape')
        before = self.app._navigation()
        self.terminal.key('C')
        self.assertEqual('branch-preview', self.terminal.modal)
        self.assertIn('NOT RECORDED', self.terminal.draw_modal(Frame(144, 42)).plain())
        self.terminal.key('G')
        self.assertIn('alternative', self.terminal.draw_modal(Frame(144, 42)).plain())
        self.terminal.key('escape'); self.terminal.key('enter')
        self.assertEqual('branch-select', self.terminal.modal)
        self.terminal.key('escape')
        self.assertEqual(before, self.app._navigation())
        self.assertEqual(self.original, self.app.paper.history.manifest())

    def test_expired_preview_cannot_open_explanation_editor(self):
        from claimbranch.application.tui_branch_ui import branch_ui
        self.now = 1790208000
        self.app.branches.clock = lambda: self.now
        flow, prepared = self.prepared_merge()
        ui = branch_ui(self.terminal)
        ui.flow = flow
        self.terminal.modal = 'branch-review'
        self.terminal.key('enter')
        self.now += 300
        self.terminal.key('1')
        self.assertIn('preview', ui.notice)
        self.assertNotEqual('branch-answer', self.terminal.modal)
        self.assertIsNone(flow.review())

    def test_manual_review_requires_no_ai_explanation(self):
        from claimbranch.fixtures import replay_merge_example
        self.app = TerminalWorkspace(replay_merge_example('manual'))
        flow, prepared = self.prepared_merge()
        reviewed = flow.finish(prepared['digest'], 'not-required', [])
        flow.build_candidate(reviewed['digest'])
        self.assertEqual(['manuscript'], [item.kind for item in flow.candidate[1].debts])

    def test_history_refresh_preserves_unfinished_text_without_rebinding_source_or_review(self):
        flow, prepared = self.prepared_merge()
        reviewed = flow.finish(prepared['digest'], 'deferred', [])
        candidate, _ = flow.build_candidate(reviewed['digest'])
        flow.buffers = {'answer': ['A pending explanation.'], 'source': ['A pending file path.']}
        self.app.paper.update_history(candidate)
        replacement = self.app.branches.open_recorded()
        self.assertEqual(flow.buffers, replacement.buffers)
        self.assertEqual('', replacement.path)
        self.assertIsNone(replacement.review())
        self.assertIsNone(flow.merge.get_review())
        self.assertIsNone(flow.candidate)

    def test_escape_hints_describe_authored_preview_and_work_return(self):
        from claimbranch.application.tui_branch_ui import branch_ui
        flow = self.branch_flow()
        ui = branch_ui(self.terminal)
        ui.flow = flow
        self.terminal.modal = 'branch-preview'
        self.terminal.key('G')
        self.app.review.stage_judgment('interpretation-two')
        self.assertIn('Esc returns to preview', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('escape')
        self.assertEqual('branch-preview', self.terminal.modal)
        ui.flow = self.app.branches.prepare_branch()
        self.terminal.key('enter')
        self.assertIn('Esc return', self.terminal.draw_modal(Frame(80, 24)).plain())

    def test_changed_source_history_invalidates_recorded_flow(self):
        flow, prepared = self.prepared_merge()
        reviewed = flow.finish(prepared['digest'], 'deferred', [])
        candidate, _ = flow.build_candidate(reviewed['digest'])
        self.app.paper.update_history(candidate)
        with self.assertRaises(ContractError):
            flow.preview()
        self.assertIsNone(flow.candidate)



if __name__ == '__main__':
    unittest.main()
