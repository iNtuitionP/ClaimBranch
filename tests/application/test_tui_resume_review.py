import tempfile
from pathlib import Path
from unittest.mock import Mock
import unittest

from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_review_ui import review_ui
from claimbranch.application.tui_recovery import DraftRecovery
from claimbranch.fixtures import replay_example


class ResumeReviewTests(unittest.TestCase):
    def setUp(self):
        self.app = TerminalWorkspace(replay_example('recorded', series=True))
        self.app.select('obs-1')
        self.terminal = Terminal.__new__(Terminal)
        self.terminal.app, self.terminal.modal = self.app, None
        self.terminal.screen = Mock()
        self.terminal.screen.getmaxyx.return_value = (42, 144)
        self.original = self.app.paper.history.manifest()

    def prepare(self):
        self.app.keep_draft('Limit the comparison to the measured split.', 'The second mask has not run.')
        self.app.review.stage('claim-pruning-detail', {'statement': 'A limited synthetic claim.', 'scope': 'Only this split.'})
        self.app.review.prepare_changes()
        self.terminal.key('w')
        self.terminal.key('enter'); self.terminal.key('1')
        self.assertEqual('review-answer', self.terminal.modal)

    def test_explanation_cancel_reopen_and_completion_keep_the_authored_text(self):
        self.prepare()
        self.terminal.key(('paste', ' 한글로 적어 둔 한계.'))
        text = self.terminal.buffers[0].text
        self.terminal.key('escape')
        self.terminal.key('enter'); self.terminal.key('1')
        self.assertEqual(text, self.terminal.buffers[0].text)
        self.terminal.key('keep')
        self.assertIsNotNone(self.app.review.session().get_changes_review())
        self.assertEqual(self.original, self.app.paper.history.manifest())

    def test_unstaged_change_can_resume_from_another_episode_and_warns_on_quit(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        self.terminal.key(('paste', ' 명시적으로 작성한 변경'))
        text = self.terminal.buffers[0].text
        self.terminal.key('escape'); self.terminal.key('escape')
        self.assertTrue(self.app.review.volatile_work())
        self.assertFalse(self.app.review.amendments)
        self.app.switch_context('episode', 'alternative')
        self.terminal.key('U')
        self.assertIn('Scientific change', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('enter')
        self.assertEqual('episode-two', self.app.episode_id)
        self.assertEqual('main', self.app.ref)
        self.assertEqual('obs-1', self.app.selected_id)
        self.assertEqual('review-fields', self.terminal.modal)
        self.assertEqual(text, self.terminal.buffers[0].text)
        self.terminal.key('escape'); self.terminal.key('escape')
        self.terminal.key('q')
        self.assertEqual('quit', self.terminal.modal)

    def test_read_only_editor_browsing_does_not_create_pending_work(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        self.terminal.key('escape'); self.terminal.key('escape')
        self.terminal.key('U')
        self.assertEqual([], self.terminal.recovery_items)
        self.assertFalse(self.app.review.volatile_work())

    def test_expired_explanation_resumes_but_requires_a_fresh_review(self):
        self.prepare()
        session = self.app.review.session()
        expiry = session.get_changes_preview()['expires_at']
        self.terminal.key(('paste', ' Retained explanation.'))
        text = self.terminal.buffers[0].text
        self.terminal.key('escape')
        session._clock = lambda: expiry
        self.app.switch_context('episode', 'alternative')
        self.terminal.key('U'); self.terminal.key('enter')
        self.assertEqual(text, self.terminal.buffers[0].text)
        self.assertIn('stale', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('keep')
        self.assertEqual('review-answer', self.terminal.modal)
        self.assertIsNone(session.get_changes_review())
        self.terminal.key('escape'); self.terminal.key('R')
        self.terminal.key('enter'); self.terminal.key('1')
        self.assertEqual(text, self.terminal.buffers[0].text)
        self.terminal.key('keep')
        self.assertEqual('answered', session.get_changes_review()['disposition'])
        self.assertFalse(self.app.review.unfinished)

    def test_expired_comparison_hides_graph_and_restores_navigation(self):
        self.prepare()
        self.terminal.key('escape'); self.terminal.key('G')
        ui = review_ui(self.terminal)
        prior = ui.compare_return.copy()
        self.app.review.session()._clock = lambda: ui.prepared['expires_at']
        frame = self.terminal.draw_modal(Frame(80, 24)).plain()
        self.assertIn('EXPIRED OR CHANGED', frame)
        self.assertNotIn('UNACCEPTED COMPARISON', frame)
        self.terminal.key('tab')
        self.assertEqual('after', ui.phase)
        self.terminal.key('escape')
        self.assertEqual(prior, self.app._navigation())

    def test_empty_edit_survives_resume_without_becoming_staged(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        for buffer in self.terminal.buffers:
            buffer.text, buffer.cursor = '', 0
        self.terminal.key('escape'); self.terminal.key('escape')
        self.terminal.key('U')
        self.assertIn('(empty edit)', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('enter'); self.terminal.key('keep')
        self.assertEqual('review-fields', self.terminal.modal)
        self.assertTrue(all(b.text == '' for b in self.terminal.buffers))
        self.assertFalse(self.app.review.amendments)
        self.terminal.key('escape'); self.terminal.key('escape')
        self.assertTrue(self.app.review.volatile_work())

    def test_review_text_is_excluded_from_checkpoints_and_still_warns_on_quit(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        self.terminal.key(('paste', ' PRIVATE-REVIEW-TEXT'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'drafts.json'
            self.app.recovery = DraftRecovery(path, self.app)
            self.addCleanup(self.app.recovery.close)
            self.assertTrue(self.terminal.checkpoint())
            self.terminal.key('escape'); self.terminal.key('escape')
            self.terminal.key('q')
            self.assertEqual('quit', self.terminal.modal)
            self.assertNotIn('PRIVATE-REVIEW-TEXT', path.read_text())
            self.assertTrue(self.app.review.unfinished)
        self.assertEqual(self.original, self.app.paper.history.manifest())

    def test_unkept_edits_are_visibly_separate_from_staged_content(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        record = review_ui(self.terminal).record_id
        self.terminal.key(('paste', ' First staged wording.'))
        self.terminal.key('keep')
        staged = self.app.review.amendments[self.app.context_key()][record]['body'].copy()
        self.terminal.key('enter'); self.terminal.key(('paste', ' Pending revision.'))
        self.terminal.key('escape')
        self.assertIn('unfinished', self.terminal.draw_modal(Frame(144, 42)).plain())
        self.assertEqual(staged, self.app.review.amendments[self.app.context_key()][record]['body'])
        self.terminal.key('escape')
        self.assertIn('excluded', ' '.join(text for text, _ in self.app.review.lines()))

    def test_tiny_terminal_pauses_invisible_controls_but_keeps_escape(self):
        self.prepare()
        self.terminal.key(('paste', ' Keep this text.'))
        text = self.terminal.buffers[0].text
        self.terminal.screen.getmaxyx.return_value = (16, 44)
        self.assertIn('controls paused', self.terminal.draw_modal(Frame(44, 16)).plain())
        self.terminal.key('keep'); self.terminal.key(('paste', 'hidden input'))
        self.assertIsNone(self.app.review.session().get_changes_review())
        self.assertEqual(text, self.terminal.buffers[0].text)
        self.terminal.key('escape')
        self.terminal.screen.getmaxyx.return_value = (24, 80)
        self.terminal.key('U'); self.terminal.key('enter')
        self.assertEqual(text, self.terminal.buffers[0].text)

    def test_discard_requires_confirmation_and_leaves_staged_change_intact(self):
        self.terminal.key('w'); self.terminal.key('c'); self.terminal.key('enter')
        record = review_ui(self.terminal).record_id
        self.terminal.key('keep')
        staged = self.app.review.amendments[self.app.context_key()][record]['body'].copy()
        self.terminal.key('enter'); self.terminal.key(('paste', ' Abandon this revision.'))
        self.terminal.key('escape'); self.terminal.key('escape')
        self.terminal.key('U'); self.terminal.key('x')
        self.assertTrue(self.app.review.unfinished)
        self.assertIn('x again', self.terminal.draw_modal(Frame(80, 24)).plain())
        self.terminal.key('escape')
        self.assertEqual('recovery', self.terminal.modal)
        self.terminal.key('x'); self.terminal.key('x')
        self.assertFalse(self.app.review.unfinished)
        self.assertEqual([], self.terminal.recovery_items)
        self.assertEqual(staged, self.app.review.amendments[self.app.context_key()][record]['body'])

    def test_tiny_navigation_and_discard_cannot_act_without_visible_content(self):
        self.prepare()
        self.terminal.key(('paste', ' retain'))
        self.terminal.key('escape'); self.terminal.key('U'); self.terminal.key('x')
        self.terminal.screen.getmaxyx.return_value = (16, 44)
        self.terminal.key('x')
        self.assertTrue(self.app.review.unfinished)
        self.assertIn('controls paused', self.terminal.draw_modal(Frame(44, 16)).plain())
        self.terminal.key('escape'); self.terminal.key('escape')
        self.terminal.key('t')
        original = self.app.context_key()
        self.terminal.key('k'); self.terminal.key('tab'); self.terminal.key('enter')
        self.assertEqual('context-episodes', self.terminal.modal)
        self.assertEqual(original, self.app.context_key())
        self.terminal.key('escape')
        self.assertIsNone(self.terminal.modal)

    def test_discard_confirmation_does_not_follow_selection(self):
        self.app.review.unfinished[(*self.app.context_key(), 'change:claim-pruning-detail')] = ['pending', 'scope']
        self.app.review.unfinished[(*self.app.context_key(), 'explanation')] = ['pending explanation']
        self.terminal.key('U'); self.terminal.key('x'); self.terminal.key('down'); self.terminal.key('x')
        self.assertEqual(2, len(self.app.review.unfinished))
        self.terminal.key('x')
        self.assertEqual(1, len(self.app.review.unfinished))
        self.assertIn((*self.app.context_key(), 'change:claim-pruning-detail'), self.app.review.unfinished)


if __name__ == '__main__':
    unittest.main()
