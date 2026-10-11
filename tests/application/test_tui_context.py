import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui import Terminal, Frame, render_snapshot
from claimbranch.fixtures import replay_example


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('recorded', series=True)
        self.app = TerminalWorkspace(self.history)
        self.before = self.history.manifest()

    def terminal(self):
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.screen = Mock()
        terminal.screen.getmaxyx.return_value = (42, 144)
        return terminal

    def test_episode_ref_node_drafts_and_navigation_are_separate(self):
        app = self.app
        app.select('obs-1')
        app.keep_note('Later note')
        app.keep_draft('Later judgment', 'Corrected measurement')
        app.graph_pan, app.graph_follow = (7, 3), False
        prior = app._navigation()
        app.switch_context('episode', 'main')
        self.assertEqual('', app.note())
        self.assertEqual('', app.draft()['text'])
        self.assertEqual('1.2', app.nodes['obs-1']['content']['value'])
        app.select('obs-1')
        app.keep_note('Earlier context note')
        app.keep_draft('Earlier judgment', 'Earlier context')
        app.switch_ref()
        self.assertEqual('', app.note())
        app.switch_context('episode-two', 'main')
        self.assertEqual(prior, app._navigation())
        self.assertEqual('Later note', app.note())
        self.assertEqual('Later judgment', app.draft()['text'])
        self.assertEqual(self.before, self.history.manifest())

    def test_review_uses_selected_episode_records_and_paper_workspace(self):
        app = self.app
        app.switch_context('episode', 'alternative')
        app.select('obs-1')
        app.keep_draft('Consider the original context', 'Evidence is now corrected')
        self.assertIs(app.review.session(), app.paper.draft('episode', 'alternative', 'obs-1'))
        self.assertNotIn('status-pruning', app.review.records())
        outbound = app.review.prepare_ai(['interpretation'])
        self.assertEqual('episode', outbound['request']['context']['records'][0]['fields']['episode_id'])
        app.review.stage('replication', {'objective': 'Repeat seed 43 before generalizing.'})
        prepared = app.review.prepare_changes()
        self.assertEqual('episode', prepared['preview']['episode_id'])
        app.switch_context('episode-two', 'alternative')
        self.assertFalse(app.review.amendments.get(app.review.key))

    def test_pending_reply_stays_with_its_episode(self):
        app = self.app
        app.select('obs-1')
        outbound = app.review.prepare_ai(['obs-1'])
        key = app.review.key
        request = outbound['request']['request_id']
        app.review.begin_ai(outbound)
        app.switch_context('episode', 'main')
        app.review.complete_ai(key, request)
        self.assertIsNone(app.review.session().state()['proposal'])
        app.switch_context('episode-two', 'main')
        self.assertIsNotNone(app.review.session().state()['proposal'])

    def test_context_picker_cancel_keeps_map_and_enter_selects_explicit_branch(self):
        from claimbranch.application.tui_context_ui import context_ui
        terminal = self.terminal()
        ui = context_ui(terminal)
        before = self.app._navigation()
        ui.dispatch('t')
        ui.dispatch('up')
        ui.dispatch('tab')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            ui.draw(Frame(width, height))
        ui.dispatch('escape')
        self.assertEqual(before, self.app._navigation())
        ui.dispatch('t')
        ui.dispatch('up')
        ui.dispatch('tab')
        ui.dispatch('enter')
        self.assertEqual(('episode', 'alternative'), (self.app.episode_id, self.app.ref))

    def test_pending_work_retains_conditional_status_and_opens_related_context(self):
        from claimbranch.application.tui_context_ui import context_ui
        terminal = self.terminal()
        ui = context_ui(terminal)
        ui.dispatch('W')
        self.assertEqual(4, len(ui.items))
        ui.dispatch('enter')
        text = '\n'.join(line for line, _ in ui.work_lines())
        self.assertIn('PENDING IF ACCEPTED', text)
        self.assertIn('No accepted debt', text)
        self.assertIn('Changed', text)
        ui.dispatch('g')
        ui.dispatch('enter')
        self.assertEqual('episode', self.app.episode_id)
        self.assertIn(self.app.selected_id, ['anchor', 'claim-comparison', 'claim-pruning', 'claim-pruning-detail', 'thesis'])
        self.assertEqual(self.before, self.history.manifest())
        self.assertEqual(4, len(self.app.service.pending_work()['items']))

    def test_series_checkpoint_roundtrip_and_invalid_context_are_atomic(self):
        from claimbranch.application.tui_recovery import DraftRecovery
        app = self.app
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'drafts.json'
            store = DraftRecovery(path, app)
            app.select('obs-1')
            app.keep_note('Later note')
            app.switch_context('episode', 'main')
            app.select('obs-1')
            app.keep_draft('Earlier draft', 'Reason')
            app.unfinished[(*app.context_key(), 'note')] = ['미완료 노트']
            store.save(app)
            store.close()
            restored = TerminalWorkspace(self.history)
            reopened = DraftRecovery(path, restored)
            self.addCleanup(reopened.close)
            self.assertEqual('episode', restored.episode_id)
            self.assertEqual(app.drafts, restored.drafts)
            self.assertEqual(app.notes, restored.notes)
            self.assertEqual(app.unfinished, restored.unfinished)
            broken = json.loads(path.read_text())
            broken['selection'][0] = 'unknown'
            before = restored._navigation()
            with self.assertRaises(ValueError):
                reopened.restore(restored, broken)
            self.assertEqual(before, restored._navigation())

    def test_current_episode_visible_and_legacy_mode_still_works(self):
        text = render_snapshot(self.app, 144, 42)
        self.assertIn('episode-two', text)
        self.assertIn('t Episodes', text)
        old = TerminalWorkspace(replay_example('manual', paper=True))
        self.assertEqual(('main', 'thesis'), old.context_key())
        self.assertIn('ClaimBranch', render_snapshot(old))

    def test_capacity_keeps_manual_editing_available_without_losing_existing_review(self):
        app = self.app
        existing = app.review.session()
        existing.edit('Retain this review draft', 'Its reason')
        for ref in ('main', 'alternative'):
            app.switch_context('episode-two', ref)
            for node in app.nodes:
                app.select(node, remember=False)
                app.keep_draft('Manual text for ' + node, 'Reason')
        self.assertEqual(16, len(app.review.sessions))
        self.assertEqual('Manual text for ' + app.selected_id, app.draft()['text'])
        self.assertIn('Review unavailable', app.message)
        self.assertTrue(app.review.lines())
        app.open_view(mode='work')
        self.assertIn('REVIEW LIMIT', render_snapshot(app))
        app.switch_context('episode-two', 'main')
        app.select('thesis', remember=False)
        self.assertIs(existing, app.review.session())

    def test_series_ai_work_is_not_recovered_as_manual_text(self):
        from claimbranch.application.tui_recovery import DraftRecovery
        app = self.app
        app.keep_draft('Manual checkpoint', 'Reason')
        outbound = app.review.prepare_ai(['thesis'])
        request = outbound['request']['request_id']
        app.review.begin_ai(outbound)
        app.review.complete_ai(app.review.key, request)
        app.review.adopt_ai()
        app.keep_draft('AI-influenced edit', 'Reason')
        app.unfinished[(*app.context_key(), 'edit')] = ['AI-influenced cancelled edit', 'Reason']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'drafts.json'
            store = DraftRecovery(path, app)
            try:
                store.save(app)
                data = path.read_text()
                self.assertIn('Manual checkpoint', data)
                self.assertNotIn('AI-influenced', data)
            finally:
                store.close()

    def test_unfinished_editor_can_resume_across_episodes(self):
        terminal = self.terminal()
        terminal.key('n')
        terminal.buffers[0].insert('한글 unfinished')
        terminal.key('escape')
        self.app.switch_context('episode', 'alternative')
        terminal.key('U')
        terminal.key('enter')
        self.assertEqual(('episode-two', 'main'), (self.app.episode_id, self.app.ref))
        self.assertEqual('note', terminal.modal)
        self.assertEqual('한글 unfinished', terminal.buffers[0].text)

    def test_empty_pending_work_is_safe_and_does_not_invent_obligations(self):
        from claimbranch.application.tui_context_ui import context_ui
        from claimbranch.core.canonical import decode
        from claimbranch.core.research_history import ResearchHistory
        end = next(i for i, raw in enumerate(self.history.commands)
                   if decode(raw)['operation_type'] == 'apply-selected-merge')
        terminal = self.terminal()
        terminal.app = TerminalWorkspace(ResearchHistory(self.history.seed, self.history.commands[:end]))
        ui = context_ui(terminal)
        ui.dispatch('W')
        self.assertEqual([], ui.items)
        for event in ('down', 'enter', 'g'):
            ui.dispatch(event)
        self.assertIn('No items', ui.draw(Frame(80, 24)).plain())
        ui.dispatch('escape')
        self.assertIsNone(terminal.modal)


if __name__ == '__main__':
    unittest.main()
