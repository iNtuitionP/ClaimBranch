"""Source-grounded manual writing; no provider, artifact read or accepted write."""
from unittest.mock import Mock
import unittest

from claimbranch.application.tui import Frame, Terminal, render_snapshot
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_history import command


def novel_history():
    history = ResearchHistory.start_paper('novel', 'novel-episode', 'Synthetic cooling study',
        'cooling-thesis', 'Cooling may reduce settling time.', 'cooling-anchor')
    history = history.append(command(history, 'record-experiment', {
        'id': 'cooling-run', 'question': 'How long does the sensor take to settle?',
        'method': 'Record the time to reach the specified tolerance.',
        'conditions': '한국어 조건: chamber 12 C; sensor batch B; three synthetic runs.',
        'metric': {'name': 'settling time', 'unit': 'seconds',
                   'definition': 'Elapsed seconds until deviation is below 0.1 C.',
                   'comparison': 'Compare with the same sensor at 20 C.'},
        'source_ref': 'synthetic:unopened-cooling.csv'}))
    return history.append(command(history, 'record-evidence-event', {
        'event_id': 'cooling-confirm', 'target_id': 'cooling-observation', 'run_id': 'cooling-run',
        'action': 'confirm', 'statement': 'Sensor batch B settled in 18 seconds at 12 C.',
        'value': '18', 'rationale': 'Invented test content, not a measurement.', 'supersedes_id': None}))


class JudgmentContextTests(unittest.TestCase):
    def terminal(self, history=None, width=80, height=24):
        app = TerminalWorkspace(history or replay_example('manual', paper=True))
        term = Terminal.__new__(Terminal)
        term.app, term.modal, term.screen = app, None, Mock()
        term.screen.getmaxyx.return_value = (height, width)
        return term

    def frame(self, term):
        height, width = term.screen.getmaxyx()
        return term.draw_modal(Frame(width, height))

    def test_work_shows_recorded_measurement_and_manual_judgment_before_commands(self):
        term = self.terminal(novel_history())
        term.app.select('cooling-observation')
        term.app.keep_draft('Tentative cooling result.', 'Only sensor batch B was observed.')
        term.key('w')
        screen = render_snapshot(term.app, 80, 24)
        for text in ('18 seconds', '12 C', 'Tentative cooling result.', 'YOUR JUDGMENT'):
            self.assertIn(text, screen)

    def test_source_is_visible_while_writing_at_wide_and_narrow_sizes(self):
        for width, height in ((144, 42), (80, 24)):
            with self.subTest(width=width):
                term = self.terminal(novel_history(), width, height)
                term.app.select('cooling-observation')
                term.key('e')
                term.key(('paste', '조건을 확인하며 작성합니다.'))
                screen = self.frame(term).plain()
                for text in ('18 seconds', '12 C', 'Conditions', 'Ctrl+O', '조건을 확인하며 작성합니다.'):
                    self.assertIn(text, screen)
                y, x = self.frame(term).cursor
                self.assertTrue(0 <= y < height and 0 <= x < width)

    def test_expansion_retains_buffers_cursor_undo_and_checkpoint_mode(self):
        term = self.terminal(novel_history())
        term.app.select('cooling-observation')
        term.app.graph_pan = (7, 3)
        before = term.app.history_digest
        term.key('e')
        term.key(('paste', '한글 판단\n둘째 줄'))
        term.key('left')
        buffers = term.buffers
        state = [(b.text, b.cursor, list(b.undo), list(b.redo)) for b in buffers]
        term.key('source')
        self.assertIn('SOURCE /', self.frame(term).plain())
        for event in ('q', 'keep', ('paste', 'must not be written'), 'enter'):
            term.key(event)
        term.app.recovery = Mock()
        self.assertTrue(term.checkpoint())
        self.assertEqual('edit', term.app.recovery.save.call_args.args[1][0])
        term.screen.getmaxyx.return_value = (42, 144)
        term.key('resize')
        term.key('escape')
        self.assertIs(buffers, term.buffers)
        self.assertEqual(state, [(b.text, b.cursor, list(b.undo), list(b.redo)) for b in buffers])
        self.assertEqual('edit', term.modal)
        term.key('undo')
        self.assertEqual('', buffers[0].text)
        term.key('redo')
        self.assertEqual(state[0][0], buffers[0].text)
        self.assertEqual(before, term.app.history_digest)
        self.assertEqual((7, 3), term.app.graph_pan)

    def test_full_source_has_definition_and_reference_without_opening_an_artifact(self):
        term = self.terminal(novel_history(), 144, 42)
        term.app.select('cooling-observation')
        term.key('e')
        term.key('source')
        screen = self.frame(term).plain()
        self.assertIn('Elapsed seconds until deviation is below 0.1 C.', screen)
        self.assertIn('synthetic:unopened-cooling.csv', screen)
        self.assertIn('not opened', screen)
        self.assertIn('No scientific connections recorded', screen)
        self.assertEqual([], term.app.review.session().state()['traces'])

    def test_claim_and_plan_context_never_substitute_a_synthetic_observation(self):
        term = self.terminal(width=144, height=42)
        for key, subject in (('thesis', 'On a fixed synthetic'), ('replication', 'mask seed 43')):
            term.app.select(key)
            term.key('e')
            term.key('source')
            screen = self.frame(term).plain()
            self.assertIn(subject, screen)
            if key == 'replication':
                self.assertIn('planned', screen)
                self.assertIn('not a measured result', screen)
            term.key('escape')
            term.key('escape')

    def test_switching_nodes_preserves_separate_judgments_and_tiny_screen_pauses_input(self):
        term = self.terminal()
        term.app.select('obs-1')
        term.key('e')
        term.key(('paste', 'Observation judgment.'))
        term.key('keep')
        term.app.select('claim-comparison')
        term.key('e')
        self.assertEqual('', term.buffers[0].text)
        term.screen.getmaxyx.return_value = (16, 44)
        term.key(('paste', 'hidden input'))
        self.assertEqual('', term.buffers[0].text)
        self.assertIn('paused', self.frame(term).plain())
        term.key('escape')
        term.app.select('obs-1')
        term.screen.getmaxyx.return_value = (24, 80)
        term.key('e')
        self.assertEqual('Observation judgment.', term.buffers[0].text)

    def test_episode_evidence_and_hypothetical_context_remain_visible_while_writing(self):
        term = self.terminal(replay_example('recorded', series=True))
        term.app.switch_context('episode', 'main')
        term.app.select('obs-1')
        term.app.preview_scenario('replication', 'challenges')
        term.key('e')
        for expanded in (False, True):
            if expanded:
                term.key('source')
            screen = self.frame(term).plain()
            self.assertIn('current global evidence', screen)
            self.assertIn('HYPOTHETICAL', screen)
            self.assertIn('episode', screen)

    def test_save_failure_is_visible_in_source_and_paused_views(self):
        term = self.terminal()
        term.app.recovery = Mock()
        term.key('e')
        self.assertIn('private draft recovery', self.frame(term).plain())
        term.app.recovery_error = 'Draft save failed. Text remains in memory.'
        term.key('source')
        self.assertIn('Draft save failed', self.frame(term).plain())
        term.screen.getmaxyx.return_value = (16, 44)
        self.assertIn('Draft save failed', self.frame(term).plain())

    def test_tiny_source_escape_leaves_once_and_source_key_cannot_toggle_hidden_view(self):
        term = self.terminal()
        term.key('e')
        term.key(('paste', 'Keep this unfinished.'))
        term.key('source')
        term.screen.getmaxyx.return_value = (16, 44)
        term.key('escape')
        self.assertIsNone(term.modal)
        self.assertEqual('Keep this unfinished.', term.app.unfinished[(*term.app.context_key(), 'edit')][0])
        term.key('E')
        term.key('source')
        term.screen.getmaxyx.return_value = (24, 80)
        self.assertIn('YOUR JUDGMENT', self.frame(term).plain())

    def test_prepared_review_status_is_visible_above_long_authored_work(self):
        term = self.terminal()
        term.app.select('obs-1')
        term.app.keep_draft('A long tentative judgment. ' * 60, 'The observed split is limited.')
        term.app.review.stage('claim-pruning-detail', {'statement': 'Restricted to this measured split.', 'scope': 'One mask.'})
        term.key('w')
        term.key('R')
        screen = render_snapshot(term.app, 80, 24)
        self.assertIn('SCIENTIFIC CHANGE REVIEW', screen)

    def test_length_limit_and_unfinished_notice_precede_long_work_text(self):
        term = self.terminal()
        term.app.keep_draft('긴' * 6000, 'The exact conditions matter.')
        term.app.review.unfinished[(*term.app.context_key(), 'explanation')] = ['Continue review.']
        term.key('w')
        screen = render_snapshot(term.app, 80, 24)
        self.assertIn('REVIEW LENGTH LIMIT', screen)
        self.assertIn('UNFINISHED WRITING', screen)
        self.assertIn('U resumes', screen)

    def test_minimum_width_shows_origin_and_simultaneous_save_and_input_notices(self):
        term = self.terminal(width=48, height=18)
        term.app.review.influenced = lambda *args: True
        term.key('e')
        self.assertIn('AI-influenced · session only', self.frame(term).plain())
        term.app.recovery_error = 'Draft save failed. Text remains in memory.'
        term.buffers[0].insert('x' * 12001)
        screen = self.frame(term).plain()
        self.assertIn('Draft save failed', screen)
        self.assertIn('12,000 character', screen)


if __name__ == '__main__':
    unittest.main()
