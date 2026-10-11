"""Named research actions and an AI-disabled terminal share existing workflows."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from claimbranch.application.tui import Frame, Terminal, compose
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()

    def terminal(self, *, ai_off=False, history=None):
        terminal = Terminal.__new__(Terminal)
        terminal.app = TerminalWorkspace(history or self.history, ai_off=ai_off)
        terminal.app.select('obs-1')
        terminal.modal, terminal.buffers, terminal.field = None, [], 0
        terminal.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        return terminal

    def choose(self, terminal, title):
        from claimbranch.application.tui_actions import actions_ui
        terminal.key(';')
        ui = actions_ui(terminal)
        for _ in range(len(ui.items())):
            if ui.items()[ui.index].title == title:
                terminal.key('enter')
                return
            terminal.key('down')
        self.fail('Missing named action: ' + title)

    def test_failure_appearing_in_open_actions_keeps_selection_and_explains_inspection(self):
        from claimbranch.application.tui_actions import actions_ui
        terminal = self.terminal(); terminal.key(';'); terminal.key('down')
        ui = actions_ui(terminal); selected = ui.items()[ui.index].title
        terminal.app.recovery_error = 'Synthetic save failure'
        self.assertEqual(selected, ui.items()[ui.index].title)
        self.assertIn('Esc, then ; to inspect save failure', ui.draw(Frame(80, 24)).plain())
        terminal.key('escape'); terminal.key(';')
        self.assertEqual('Inspect writing save status', ui.items()[0].title)
        terminal.app.recovery_error = None
        self.assertEqual('Inspect writing save status', ui.items()[0].title)
        terminal.key('enter')
        self.assertIn('WRITING SAVED', terminal.draw_modal(Frame(80, 24)).plain())
        self.assertNotIn('SAVE NOT CONFIRMED', terminal.draw_modal(Frame(80, 24)).plain())

    def test_named_writing_preserves_subject_and_graph_return(self):
        terminal = self.terminal()
        before = terminal.app._navigation()
        self.choose(terminal, 'Write a judgment')
        self.assertEqual('edit', terminal.modal)
        text = terminal.draw_modal(Frame(80, 24)).plain()
        self.assertIn('0.4 percentage points', text)
        terminal.key(('paste', '이 관찰의 범위만 판단한다.'))
        terminal.key('tab')
        terminal.key(('paste', 'Only one mask was measured.'))
        terminal.key('keep')
        self.assertEqual('이 관찰의 범위만 판단한다.', terminal.app.draft()['text'])
        terminal.key('escape')
        self.assertEqual(before, terminal.app._navigation())
        self.assertEqual(self.original, self.history.manifest())

    def test_menu_cancel_resize_and_result_entry_do_not_change_work(self):
        terminal = self.terminal()
        terminal.app.keep_draft('Keep this thought.', '')
        before = terminal.app._navigation()
        for title in ('Draft a result and source',):
            self.choose(terminal, title)
            self.assertEqual('intake-form', terminal.modal)
            for width, height in ((144, 42), (80, 24), (48, 18)):
                frame = terminal.draw_modal(Frame(width, height)).plain()
                self.assertIn('UNCONFIRMED', frame)
            terminal.key('escape')
            terminal.key('escape')
            self.assertFalse(terminal.app.intake.has_writing())
        terminal.key(';')
        terminal.screen.getmaxyx = lambda: (12, 36)
        terminal.key('enter')
        self.assertEqual('actions', terminal.modal)
        terminal.key('escape')
        self.assertEqual(before, terminal.app._navigation())
        self.assertEqual('Keep this thought.', terminal.app.draft()['text'])
        self.assertEqual(self.original, self.history.manifest())

    def test_ai_off_is_a_service_capability_and_blocks_request_entry(self):
        terminal = self.terminal(ai_off=True)
        self.assertIn('AI OFF', compose(terminal.app, 80, 24).plain())
        with patch.object(terminal.app.review, 'prepare_ai', side_effect=AssertionError('request entry')):
            self.choose(terminal, 'Ask AI about this context')
            self.assertEqual('actions', terminal.modal)
            self.assertIn('AI OFF', terminal.draw_modal(Frame(80, 24)).plain())
            terminal.key('escape')
            terminal.key('w')
            terminal.key('A')
            self.assertIsNone(terminal.modal)
        terminal.key('e')
        terminal.key(('paste', 'A manual judgment.'))
        terminal.key('tab')
        terminal.key(('paste', 'Based on this observation.'))
        terminal.key('keep')
        session = terminal.app.review.session()
        with self.assertRaisesRegex(ContractError, 'AI is off'):
            terminal.app.review.prepare_ai(['obs-1'])
        state = session.state()
        self.assertFalse(state['ai_available'])
        self.assertIsNone(state['proposal'])
        self.assertEqual([], state['attempts'])
        self.assertEqual([], state['traces'])
        self.assertEqual('A manual judgment.', state['draft']['text'])
        self.assertFalse(state['draft']['ai_influenced'])
        self.assertNotIn('ai', [c['contributor'] for c in state['draft']['contributions']])
        self.assertEqual(self.original, self.history.manifest())

    def test_default_assistance_is_explicit_before_a_complete_judgment(self):
        terminal = self.terminal()
        terminal.key(';')
        self.assertIn('Fixed example', terminal.draw_modal(Frame(80, 24)).plain())
        terminal.key('escape')
        self.choose(terminal, 'Ask AI about this context')
        self.assertEqual('review-context', terminal.modal)
        self.assertEqual('', terminal.app.draft()['text'])
        self.assertEqual([], terminal.app.review.session().state()['traces'])
        terminal.key('enter')
        self.assertEqual('review-outbound', terminal.modal)

    def test_menu_discloses_shortcut_scope_disabled_rows_and_source_omission(self):
        terminal = self.terminal(ai_off=True)
        terminal.key(';')
        text = terminal.draw_modal(Frame(80, 24)).plain()
        self.assertIn('× Resume unfinished writing', text)
        self.assertTrue(text.splitlines()[4].rstrip().endswith('…'))
        terminal.key('escape')
        self.choose(terminal, 'Review selected changes')
        self.assertRegex(terminal.draw_modal(Frame(80, 24)).plain(), r'(?m)Edit scientific changes\s+w c\s*$')
        self.assertIn('× Review selected changes', terminal.draw_modal(Frame(80, 24)).plain())
        terminal.key('escape')
        self.choose(terminal, 'Resume unfinished writing')
        self.assertEqual('actions', terminal.modal)
        self.assertIn('No unfinished writing', terminal.draw_modal(Frame(48, 18)).plain())
        terminal.key('escape')
        terminal.app.unfinished[(*terminal.app.context_key(), 'edit')] = ['resume me', '']
        self.choose(terminal, 'Resume unfinished writing')
        self.assertEqual('recovery', terminal.modal)
        terminal.key('enter')
        self.assertEqual('resume me', terminal.buffers[0].text)

    def test_narrow_footer_keeps_actions_help_quit_and_unfinished_entry(self):
        terminal = self.terminal(history=replay_example('manual', series=True))
        terminal.app.unfinished[(*terminal.app.context_key(), 'edit')] = ['unfinished', '']
        for width, height in ((48, 18), (80, 24)):
            footer = compose(terminal.app, width, height).plain().splitlines()[-3:-1]
            text = '\n'.join(footer)
            self.assertIn('; actions', text)
            self.assertIn('U unfinished', text)
            self.assertIn('? help', text)
            self.assertIn('q quit', text)

    def test_narrow_ready_proposal_exposes_explicit_session_only_adoption(self):
        terminal = self.terminal()
        outbound = terminal.app.review.prepare_ai(['obs-1'])
        terminal.app.review.begin_ai(outbound)
        terminal.app.review.complete_ai(terminal.app.review.key, outbound['request']['request_id'])
        terminal.key('w')
        for width, height in ((48, 18), (80, 24)):
            footer = '\n'.join(compose(terminal.app, width, height).plain().splitlines()[-3:-1])
            for text in ('y compare', 'SESSION ONLY', 'x reject', '; actions', '? help', 'q quit'):
                self.assertIn(text, footer)

    def test_ai_badge_keeps_current_evidence_context_visible(self):
        for off in (False, True):
            terminal = self.terminal(history=replay_example('recorded', series=True), ai_off=off)
            header = '\n'.join(compose(terminal.app, 80, 24).plain().splitlines()[:2])
            self.assertIn('AI OFF' if off else 'AI example', header)
            self.assertIn('closed reasoning / current global evidence', header)

    def test_named_changes_and_comparison_reuse_service_review(self):
        terminal = self.terminal(ai_off=True)
        terminal.app.keep_draft('Restrict to seed 42.', 'Seed 43 is unmeasured.')
        self.choose(terminal, 'Edit scientific changes')
        self.assertEqual('review-changes', terminal.modal)
        terminal.key('escape')
        terminal.app.review.stage('claim-pruning-detail', {'statement': 'This holds only for seed 42.', 'scope': 'One mask only.'})
        self.choose(terminal, 'Review selected changes')
        self.assertIsNotNone(terminal.app.review.session().get_changes_preview())
        self.choose(terminal, 'Compare before and after')
        self.assertEqual('review-graph', terminal.modal)
        from claimbranch.application.tui_review_ui import review_ui
        self.assertTrue(all(not g.paper.ai_available for g in review_ui(terminal).graphs.values()))
        terminal.key('escape')
        self.choose(terminal, 'Finish change review')
        self.assertFalse(terminal.app.review.session().get_changes_review()['acceptance_available'])
        self.assertEqual(self.original, self.history.manifest())

    def test_ai_off_survives_episode_ref_navigation_without_erasing_source_ai(self):
        history = replay_example('recorded', series=True)
        original = history.manifest()
        terminal = self.terminal(ai_off=True, history=history)
        for episode in terminal.app.paper.service.episodes()['episodes']:
            terminal.app.switch_context(episode['id'], 'main')
            terminal.app.switch_ref()
            self.assertFalse(terminal.app.review.session().state()['ai_available'])
        self.assertEqual(original, history.manifest())


if __name__ == '__main__':
    unittest.main()
