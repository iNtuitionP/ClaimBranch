"""Terminal journeys use the paper service, preserving scope and origin."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from claimbranch.application.tui import Terminal, compose
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_recovery import DraftRecovery
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example


class TerminalReviewTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)
        self.app.select('obs-1')

    def draft(self):
        self.app.keep_draft('The measured pruning result is limited to seed 42.',
                            'Seed 43 has not run; one mask cannot establish generality.')

    def stage(self):
        self.app.review.stage('claim-pruning-detail', {
            'statement': 'For mask seed 42, pruning lost 0.4 percentage points.',
            'scope': 'Only these 2000 synthetic examples and mask seed 42.'})
        self.app.review.stage('edge-pruning', {
            'edge_type': 'qualifies', 'rationale': 'The observation covers one mask only.'})
        self.app.review.stage('replication', {
            'objective': 'Repeat with mask seed 43 before generalizing.'})
        self.app.review.toggle('replication')

    def proposal(self):
        outbound = self.app.review.prepare_ai(['obs-1', 'claim-pruning-detail'], include_draft=True)
        key = self.app.review.key
        request_id = outbound['request']['request_id']
        self.app.review.begin_ai(outbound)
        self.app.review.complete_ai(key, request_id)
        return key, request_id

    def test_manual_judgment_reaches_exact_selected_review_without_a_write(self):
        self.draft()
        self.stage()
        prepared = self.app.review.prepare_changes()
        preview = prepared['preview']
        self.assertIn('replication', preview['selection']['omitted'])
        self.assertEqual(['claim-pruning-detail'], preview['impact']['directly_changed_claim_ids'])
        self.assertEqual(['obs-1', 'obs-2'], preview['impact']['unchanged_evidence_ids'])
        reviewed = self.app.review.finish_changes(prepared['digest'], 'not-required', [])
        self.assertFalse(reviewed['authorization_verified'])
        self.assertFalse(reviewed['acceptance_available'])
        self.assertEqual(self.original, self.history.manifest())
        self.app.review.not_now()
        self.assertIsNone(self.app.review.session().get_changes_review())
        self.assertIn('limited to seed 42', self.app.draft()['text'])

    def test_context_browsing_and_scientific_edits_preserve_ready_proposal(self):
        self.draft()
        self.proposal()
        proposal = self.app.review.session().state()['proposal']
        terminal = self.terminal()
        terminal.key('w'); terminal.key('A'); terminal.key('escape')
        self.assertEqual(proposal, self.app.review.session().state()['proposal'])
        self.stage()
        self.assertEqual(proposal, self.app.review.session().state()['proposal'])
        self.app.review.prepare_changes()
        self.app.review.toggle('replication')
        self.assertIsNone(self.app.review.session().get_changes_preview())
        self.assertEqual(proposal, self.app.review.session().state()['proposal'])

    def test_staging_during_pending_ai_does_not_make_its_response_late(self):
        self.draft()
        outbound = self.app.review.prepare_ai(['obs-1'], include_draft=True)
        self.app.review.begin_ai(outbound)
        self.stage()
        self.assertEqual('pending', self.app.review.session().state()['attempt']['state'])
        result = self.app.review.complete_ai(self.app.context_key(), outbound['request']['request_id'])
        self.assertIsNotNone(result['proposal'])

    def test_context_is_explicit_and_does_not_include_notes_or_unselected_neighbors(self):
        self.draft()
        self.app.keep_note('private note excluded from AI context')
        outbound = self.app.review.prepare_ai(['obs-1'], include_draft=False)
        records = outbound['request']['context']['records']
        self.assertEqual(['obs-1'], [r['id'] for r in records])
        self.assertEqual('0.4', records[0]['fields']['value'])
        self.assertNotIn('private note', str(outbound))
        self.assertNotIn('limited to seed', str(outbound))
        self.assertEqual([], self.app.review.session().state()['attempts'])
        changed = deepcopy(outbound)
        changed['digest'] = 'a' * 64
        with self.assertRaises(ContractError):
            self.app.review.begin_ai(changed)

    def test_ai_adoption_and_human_edit_keep_contributions_and_node_binding(self):
        self.draft()
        prior = self.app.draft()
        self.proposal()
        self.assertEqual(prior, self.app.draft())
        self.app.review.adopt_ai()
        self.assertNotEqual(prior['text'], self.app.draft()['text'])
        self.assertIn('AI-INFLUENCED', str(self.app.detail('draft')))
        self.app.keep_draft('A revised human judgment.', 'Only the measured mask is known.')
        self.stage()
        prepared = self.app.review.prepare_changes()
        contributions = prepared['preview']['provenance']['judgment']['history']
        self.assertEqual(['human', 'ai', 'human'], [c['contributor'] for c in contributions])
        self.assertEqual(prior, self.app.review.session().state()['before_proposal'])
        self.app.select('obs-2')
        self.assertEqual('', self.app.draft()['text'])
        self.app.select('obs-1')
        self.assertEqual('A revised human judgment.', self.app.draft()['text'])
        self.assertEqual(self.original, self.history.manifest())

    def test_edit_cancel_and_late_reply_preserve_work(self):
        for action in ('edit', 'cancel'):
            with self.subTest(action=action):
                self.setUp()
                self.draft()
                outbound = self.app.review.prepare_ai(['obs-1'], include_draft=True)
                key, request_id = self.app.review.key, outbound['request']['request_id']
                self.app.review.begin_ai(outbound)
                if action == 'edit':
                    self.app.keep_draft('Continue manually.', 'New reasoning.')
                else:
                    self.app.review.not_now()
                before = self.app.draft()
                self.app.review.complete_ai(key, request_id)
                state = self.app.review.session().state()
                self.assertEqual('stale' if action == 'edit' else 'cancelled', state['attempt']['state'])
                self.assertIsNone(state['proposal'])
                self.assertEqual(before, self.app.draft())

    def test_reselection_and_edits_reject_old_review(self):
        self.draft()
        self.stage()
        first = self.app.review.prepare_changes()
        self.app.review.toggle('replication')
        with self.assertRaises(ContractError):
            self.app.review.finish_changes(first['digest'], 'not-required', [])
        self.app.review.prepare_changes()
        self.app.keep_draft('New judgment.', 'New reason.')
        self.assertIsNone(self.app.review.session().get_changes_preview())

    def test_ai_influenced_review_requires_answer_or_visible_deferral(self):
        self.draft()
        self.proposal()
        self.app.review.adopt_ai()
        self.stage()
        prepared = self.app.review.prepare_changes()
        with self.assertRaises(ContractError):
            self.app.review.finish_changes(prepared['digest'], 'not-required', [])
        reviewed = self.app.review.finish_changes(prepared['digest'], 'deferred', [])
        self.assertTrue(reviewed['consequences_if_accepted']['understanding_debt'])
        self.assertFalse(reviewed['acceptance_available'])

    def test_checkpoint_never_restores_ai_work_as_a_manual_judgment(self):
        self.draft()
        manual = self.app.draft()
        self.proposal()
        self.app.review.adopt_ai()
        self.app.keep_draft('AI-influenced edit', 'A later human reason')
        self.app.unfinished[('main', 'obs-1', 'edit')] = ['unfinished AI edit', 'reason']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'drafts.json'
            recovery = DraftRecovery(path, self.app)
            self.app.recovery = recovery
            recovery.save(self.app, ('edit', ['active AI edit', 'reason']))
            recovery.close()
            restored = TerminalWorkspace(self.history)
            loaded = DraftRecovery(path, restored)
            loaded.close()
            self.assertEqual(manual, restored.draft())
            self.assertNotIn(('main', 'obs-1', 'edit'), restored.unfinished)
            self.assertNotIn('AI-influenced edit', path.read_text())
            terminal = Terminal.__new__(Terminal)
            terminal.app, terminal.modal = self.app, None
            # Use a new real lock, as a live terminal would hold.
            self.app.recovery = DraftRecovery(path, TerminalWorkspace(self.history))
            self.assertIsNone(terminal.key('q'))
            self.assertEqual('quit', terminal.modal)
            self.app.recovery.close()

    def test_changed_scope_never_mutates_source_and_unknown_records_are_rejected(self):
        self.draft()
        for record, values in (('obs-1', {'statement': 'Replace evidence'}),
                               ('edge-pruning', {'edge_type': 'confirmed'}),
                               ('claim-pruning-detail', {'parent_ids': []})):
            with self.subTest(record=record), self.assertRaises((ValueError, ContractError)):
                self.app.review.stage(record, values)
        self.assertEqual(self.original, self.history.manifest())

    def test_work_keys_are_reachable_and_review_content_reflows(self):
        self.draft()
        self.stage()
        self.app.review.prepare_changes()
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal = self.app, None
        terminal.key('w')
        self.assertEqual(('detail', 'work'), (self.app.focus, self.app.mode))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            with self.subTest(width=width):
                frame = compose(self.app, width, height)
                self.assertIn('WORK', frame.plain())
                self.assertEqual(height, len(frame.plain().splitlines()))

    def terminal(self):
        class Screen:
            def getmaxyx(self): return 30, 120
        terminal = Terminal.__new__(Terminal)
        terminal.app, terminal.modal, terminal.screen = self.app, None, Screen()
        return terminal

    def test_ui_edits_selects_compares_and_finishes_manual_review(self):
        self.draft()
        terminal = self.terminal()
        terminal.key('w')
        terminal.key('c')
        ui = terminal._review_ui
        ui.index = ui.items.index('claim-pruning-detail')
        terminal.key('enter')
        terminal.buffers[0].text = 'Only this pruning mask is measured.'
        terminal.key('keep')
        self.assertIn('claim-pruning-detail', self.app.review.selected[self.app.review.key])
        self.assertEqual('claim-pruning-detail', ui.items[ui.index])
        self.assertIn('Only this pruning mask', terminal.draw_modal(compose(self.app, 120, 30)).plain())
        terminal.key('R')
        self.assertIsNone(terminal.modal)
        self.assertIsNotNone(self.app.review.session().get_changes_preview())
        position = self.app._navigation()
        terminal.key('G')
        self.assertEqual('Only this pruning mask is measured.', ui.graphs['after'].title('claim-pruning-detail'))
        self.assertNotEqual(ui.graphs['before'].title('claim-pruning-detail'), ui.graphs['after'].title('claim-pruning-detail'))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('UNACCEPTED', terminal.draw_modal(compose(self.app, width, height)).plain())
        terminal.key('tab')
        self.assertEqual('before', ui.phase)
        terminal.key('escape')
        self.assertEqual(position, self.app._navigation())
        terminal.key('enter')
        self.assertIsNotNone(self.app.review.session().get_changes_review())
        self.assertEqual(self.original, self.history.manifest())

    def test_ui_preview_cancel_adopt_and_restore_partial_draft(self):
        self.app.keep_draft('An unfinished idea.', '')
        terminal = self.terminal()
        terminal.key('w')
        terminal.key('A')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('CHOOSE CONTEXT', terminal.draw_modal(compose(self.app, width, height)).plain())
        terminal.key('enter')
        self.assertEqual([], self.app.review.session().state()['attempts'])
        self.assertIn('REVIEW EXACT', terminal.draw_modal(compose(self.app, 80, 24)).plain())
        terminal.key('escape')
        self.assertEqual('cancelled', self.app.review.session().state()['attempt']['state'])
        terminal.key('A')
        terminal.key('enter')
        terminal.key('enter')
        pending = self.app.review.pending[0]
        self.app.review.complete_ai(*pending[:2])
        terminal.key('y')
        self.assertFalse(self.app.review.influenced())
        self.assertEqual('review-adoption', terminal.modal)
        terminal.key('enter')
        self.assertTrue(self.app.review.influenced())
        terminal.key('B')
        terminal.key('enter')
        self.assertEqual({'text': 'An unfinished idea.', 'rationale': ''}, self.app.draft())
        self.assertTrue(self.app.review.influenced())

    def test_restoring_prior_ai_buffer_compares_and_preserves_newer_writing_on_cancel(self):
        self.draft()
        original = self.app.draft()
        self.proposal()
        self.app.review.adopt_ai()
        self.app.keep_draft('Newer human revision.', 'Newer human reason.')
        terminal = self.terminal()
        terminal.key('w')
        newer = self.app.review.session().state()
        terminal.key('B')
        screen = terminal.draw_modal(compose(self.app, 80, 24)).plain()
        self.assertIn('COMPARE EARLIER TEXT', screen)
        self.assertIn('Newer human revision.', screen)
        self.assertEqual(newer, self.app.review.session().state())
        terminal.key('escape')
        self.assertEqual(newer, self.app.review.session().state())
        terminal.key('B')
        self.app.keep_draft('Writing changed during comparison.', 'Changed reason.')
        changed = self.app.review.session().state()
        terminal.key('enter')
        self.assertEqual(changed, self.app.review.session().state())
        self.assertIn('COMPARISON CHANGED OR EXPIRED',
                      terminal.draw_modal(compose(self.app, 80, 24)).plain())
        terminal.key('escape')
        terminal.key('w')
        terminal.key('B')
        terminal.key('enter')
        self.assertEqual(original, self.app.draft())
        self.assertTrue(self.app.review.influenced())

    def test_adoption_comparison_cancel_resize_and_exact_confirmation(self):
        self.draft()
        self.proposal()
        terminal = self.terminal()
        terminal.key('w')
        before = self.app.review.session().state()
        terminal.key('y')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            screen = terminal.draw_modal(compose(self.app, width, height)).plain()
            self.assertIn('COMPARE AI PROPOSAL', screen)
            self.assertIn('YOUR JUDGMENT', screen)
        self.assertEqual(before, self.app.review.session().state())
        terminal.screen = type('Screen', (), {'getmaxyx': lambda _: (16, 44)})()
        terminal.key('enter')
        self.assertEqual(before, self.app.review.session().state())
        position = self.app._navigation()
        terminal.key('escape')
        self.assertEqual(position, self.app._navigation())
        self.assertEqual(before, self.app.review.session().state())
        terminal.screen = type('Screen', (), {'getmaxyx': lambda _: (24, 80)})()
        terminal.key('y')
        terminal.key('end')
        screen = terminal.draw_modal(compose(self.app, 80, 24)).plain()
        self.assertIn('AI ORIGIN', screen)
        terminal.key('enter')
        after = self.app.review.session().state()
        self.assertTrue(after['draft']['ai_influenced'])
        self.assertEqual(before['draft']['rationale'], after['draft']['rationale'])
        self.assertEqual(before['proposal']['text'], after['draft']['text'])
        self.assertEqual(before['proposal']['text'], self.app.draft()['text'])
        self.assertEqual(before['draft']['text'], after['before_proposal']['text'])
        self.assertIsNone(terminal.modal)
        self.assertEqual(self.original, self.history.manifest())

    def test_changed_or_expired_proposal_comparison_cannot_replace_writing(self):
        for change in ('edit', 'expire', 'owner', 'proposal', 'source'):
            with self.subTest(change=change):
                self.setUp()
                self.draft()
                self.proposal()
                terminal = self.terminal()
                terminal.key('w')
                terminal.key('y')
                original_session = self.app.review.session()
                original_state = original_session.state()
                if change == 'edit':
                    self.app.keep_draft('Newer human writing.', 'Newer reason.')
                elif change == 'expire':
                    session = self.app.review.session()
                    expiry = session.state()['attempt']['expires_at']
                    session._clock = lambda: expiry
                elif change == 'owner':
                    self.app.select('claim-pruning-detail')
                elif change == 'proposal':
                    self.proposal()
                else:
                    from claimbranch.application.paper_service import PaperService
                    from tests.contract.test_paper_history import command, experiment
                    updated = self.history.append(command(self.history, 'record-experiment',
                                                          dict(experiment(), id='another-run')))
                    self.app.review.session().update_source(PaperService(updated))
                before = self.app.draft()
                terminal.key('enter')
                self.assertEqual(before, self.app.draft())
                self.assertFalse(self.app.review.influenced())
                self.assertFalse(original_session.state()['draft']['ai_influenced'])
                if change == 'owner':
                    self.assertEqual(original_state, original_session.state())
                self.assertEqual('review-adoption', terminal.modal)
                screen = terminal.draw_modal(compose(self.app, 80, 24)).plain()
                self.assertIn('COMPARISON CHANGED OR EXPIRED', screen)
                terminal.key('escape')

    def test_comparison_replacement_keeps_unfinished_judgment_separate(self):
        self.draft()
        unfinished_key = (*self.app.work_key(), 'edit')
        self.app.unfinished[unfinished_key] = ['Unkept human text.', 'Unkept human reason.']
        self.proposal()
        terminal = self.terminal()
        terminal.key('w')
        terminal.key('y')
        terminal.key('end')
        screen = terminal.draw_modal(compose(self.app, 80, 24)).plain()
        self.assertIn('Unkept judgment writing remains separate', screen)
        terminal.key('enter')
        self.assertEqual(['Unkept human text.', 'Unkept human reason.'],
                         self.app.unfinished[unfinished_key])
        self.assertTrue(self.app.review.influenced())

    def test_ai_answer_reuses_reason_and_expired_completion_is_rejected(self):
        self.draft()
        self.proposal()
        self.app.review.adopt_ai()
        self.stage()
        prepared = self.app.review.prepare_changes()
        terminal = self.terminal()
        terminal.key('w')
        terminal.key('enter')
        self.assertEqual('review-complete', terminal.modal)
        terminal.key('1')
        self.assertEqual(self.app.draft()['rationale'], terminal.buffers[0].text)
        terminal.key('keep')
        self.assertEqual('answered', self.app.review.session().get_changes_review()['disposition'])
        session = self.app.review.session()
        session._clock = lambda: prepared['expires_at']
        terminal.key('enter')
        self.assertIsNone(session.get_changes_review())
        self.assertIsNone(terminal.modal)
        self.assertEqual(self.original, self.history.manifest())

    def test_long_korean_draft_is_kept_but_cannot_review_a_stale_shorter_draft(self):
        self.draft()
        self.stage()
        self.app.review.prepare_changes()
        terminal = self.terminal()
        terminal.key('e')
        text = '한글 초안 ' * 1600
        terminal.buffers[0].text = text
        terminal.key('keep')
        self.assertIsNone(terminal.modal)
        self.assertEqual(text, self.app.draft()['text'])
        self.assertIn('UTF-8', self.app.message)
        self.assertIsNone(self.app.review.session().get_changes_preview())
        for action in (self.app.review.prepare_changes, lambda: self.app.review.prepare_ai(['obs-1'])):
            with self.assertRaises(ContractError):
                action()
        self.app.keep_draft('Shorter judgment.', 'The same reason.')
        self.app.review.prepare_changes()
        self.assertEqual('Shorter judgment.', self.app.draft()['text'])

    def test_long_restored_manual_text_and_long_ai_edit_keep_their_different_origins(self):
        long_text = '측정 결과 ' * 1600
        self.app.drafts[('main', 'obs-1')] = {'text': long_text, 'rationale': 'Human reason'}
        self.assertIn(long_text, str(self.app.review.lines()))
        self.assertEqual(long_text, self.app.draft()['text'])
        self.draft()
        self.proposal()
        self.app.review.adopt_ai()
        self.app.keep_draft(long_text, 'Reason after AI')
        self.assertEqual(long_text, self.app.draft()['text'])
        self.assertTrue(self.app.review.influenced())
        self.assertNotEqual(long_text, self.app.drafts[('main', 'obs-1')]['text'])


if __name__ == '__main__':
    unittest.main()
