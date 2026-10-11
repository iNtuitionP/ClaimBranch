"""Conditional explanation stays human-written, source-bound and unaccepted."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_context_ui import context_ui
from claimbranch.application.tui_recovery import DraftRecovery
from claimbranch.fixtures import replay_example
from claimbranch.application.tui_understanding_ui import understanding_ui
from tests.contract.test_paper_episodes import command, first_episode


class UnderstandingUITests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('recorded', series=True)
        self.t = Terminal.__new__(Terminal)
        self.app = self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.modal, self.t.buffers, self.t.field = None, [], 0
        self.t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        self.before = self.history.manifest()

    def open(self, index=0):
        self.t.modal = None
        self.t.key('W')
        ui = context_ui(self.t)
        indexes = [i for i, item in enumerate(ui.items) if item['kind'] == 'understanding']
        ui.index = indexes[index]
        self.t.key('enter')
        self.t.key('e')
        self.assertEqual('understanding-topics', self.t.modal)
        self.t.key('enter')
        return self.app.understanding.session

    def test_return_reuses_reason_keeps_partial_text_and_restores_graph(self):
        original = self.app._navigation()
        session = self.open()
        self.t.key('r')
        self.assertTrue(session.state()['draft']['entries'][0]['reuse_rationale'])
        self.t.key('e')
        self.t.key(('paste', '측정한 조건만 해석한다.'))
        self.t.key('keep')
        self.assertEqual('측정한 조건만 해석한다.', session.state()['draft']['entries'][0]['text'])
        self.assertFalse(session.state()['closure_available'])
        for _ in range(4):
            self.t.key('escape')
        self.assertIsNone(self.t.modal)
        self.assertEqual(original, self.app._navigation())
        self.open()
        self.assertEqual('측정한 조건만 해석한다.', session.state()['draft']['entries'][0]['text'])
        self.assertEqual(self.before, self.history.manifest())

    def test_cancelled_input_is_separate_and_survives_other_work_and_checkpoint(self):
        first = self.open()
        self.t.key('e')
        self.t.key(('paste', '아직 정리 중인 이유'))
        self.t.key('escape')
        self.assertEqual('', first.state()['draft']['entries'][0]['text'])
        self.open(1)
        self.t.key('e')
        self.assertEqual('', self.t.buffers[0].text)
        self.t.key('escape')
        self.open()
        self.t.key('e')
        self.assertEqual('아직 정리 중인 이유', self.t.buffers[0].text)
        self.t.key('escape')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manual.json'
            store = DraftRecovery(path, self.app)
            store.save(self.app)
            store.close()
            self.assertNotIn('아직 정리 중인 이유', path.read_text())
        self.assertTrue(self.app.review.volatile_work())
        self.t.modal = None
        self.t.key('q')
        self.assertEqual('quit', self.t.modal)

    def test_source_views_keep_full_science_and_ai_without_changing_editor(self):
        self.open()
        ui = understanding_ui(self.t)
        self.t.key('e')
        self.t.key(('paste', '아직 확인할 조건'))
        buffer = self.t.buffers[0]
        self.t.key('left')
        cursor = buffer.cursor
        self.t.key('source')
        self.assertEqual('understanding-source', self.t.modal)
        for view in ('explanation', 'original', 'current', 'draft basis', 'AI history'):
            ui.view = view
            self.assertTrue(ui.lines(ui.state()))
            for w, h in ((144, 42), (80, 24), (48, 18)):
                self.assertIn('EXPLANATION', self.t.draw_modal(Frame(w, h)).plain())
        for event in (('paste', 'should not enter'), 'keep', 'r', 's', ']'):
            self.t.key(event)
        self.t.key('escape')
        self.assertEqual('understanding-edit', self.t.modal)
        self.assertIs(buffer, self.t.buffers[0])
        self.assertEqual(cursor, buffer.cursor)
        self.assertEqual('아직 확인할 조건', buffer.text)
        self.t.key('undo')
        self.assertEqual('', buffer.text)

    def test_original_and_current_evidence_are_independently_readable(self):
        self.open()
        ui = understanding_ui(self.t)
        ui.index = 1
        state = ui.state()
        ui.view = 'original'
        original = '\n'.join(text for text, _ in ui.lines(state))
        ui.view = 'current'
        current = '\n'.join(text for text, _ in ui.lines(state))
        self.assertIn('Recorded value: 0.4 percentage points', original)
        self.assertIn('Recorded value: 1.2 percentage points', current)
        self.assertIn('Measurement definition:', original)
        self.assertIn('CONNECTION', original)
        self.assertIn('Source reference (not opened)', current)

    def test_basis_refresh_is_explicit_stale_checked_and_keeps_writing(self):
        history = first_episode(ai=True, close=False)
        self.app = self.t.app = TerminalWorkspace(history, ai_off=True)
        session = self.open()
        self.t.key('e')
        self.t.key(('paste', 'Earlier explanation.'))
        self.t.key('keep')
        corrected = history.append(command(history, 'record-evidence-event', {
            'event_id': 'explanation-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'Synthetic recount: pruning loses 1.2 percentage points.',
            'value': '1.2', 'rationale': 'Synthetic correction.', 'supersedes_id': 'event-1'}))
        self.app.paper.update_history(corrected)
        self.assertIn('EARLIER DRAFT BASIS', self.t.draw_modal(Frame(80, 24)).plain())
        self.assertFalse(session.state()['context_current'])
        self.t.key('s')
        self.assertEqual('understanding-rebind', self.t.modal)
        self.app.paper = SimpleNamespace(history=replay_example('manual', series=True))
        self.t.key('enter')
        self.assertEqual('understanding-rebind', self.t.modal)
        self.assertFalse(session.state()['context_current'])
        self.app.paper = SimpleNamespace(history=corrected)
        later = corrected.append(command(corrected, 'close-episode', {}))
        self.app.paper.history = later
        self.t.key('enter')
        self.assertEqual('understanding-rebind', self.t.modal)
        self.assertFalse(session.state()['context_current'])
        self.assertIn('exact current', understanding_ui(self.t).notice)
        self.t.key('escape')
        self.t.key('s')
        self.t.key('enter')
        self.assertTrue(session.state()['context_current'])
        self.assertEqual('Earlier explanation.', session.state()['draft']['entries'][0]['text'])
        self.assertEqual(corrected.heads, history.heads)

    def test_limits_keep_buffer_and_success_normalizes_unicode(self):
        session = self.open()
        self.t.key('e')
        self.t.key(('paste', '가' * 6000))
        self.t.key('keep')
        self.assertEqual('understanding-edit', self.t.modal)
        self.assertEqual('가' * 6000, self.t.buffers[0].text)
        self.assertEqual('', session.state()['draft']['entries'][0]['text'])
        self.assertIn('18,000/16,384 B', self.t.draw_modal(Frame(80, 24)).plain())
        self.assertIn('UTF-8', understanding_ui(self.t).notice)
        self.t.key('escape')
        self.t.key('e')
        self.t.buffers[0].text = 'e\u0301'
        self.t.key('keep')
        self.assertEqual('é', session.state()['draft']['entries'][0]['text'])
        self.assertFalse(self.app.understanding.buffers)

    def test_pristine_browsing_has_no_volatile_work_and_tiny_controls_pause(self):
        self.open()
        self.t.key('e')
        self.t.key('escape')
        self.assertFalse(self.app.understanding.volatile_work())
        self.t.key('e')
        self.t.key(('paste', 'Retained on resize.'))
        self.t.screen.getmaxyx = lambda: (12, 36)
        for event in ('keep', ('paste', 'hidden'), 'source'):
            self.t.key(event)
        self.assertIn('paused', self.t.draw_modal(Frame(36, 12)).plain())
        self.assertEqual('Retained on resize.', self.t.buffers[0].text)
        self.t.key('escape')
        self.t.screen.getmaxyx = lambda: (24, 80)
        self.t.key('e')
        self.assertEqual('Retained on resize.', self.t.buffers[0].text)

    def test_cancelled_empty_edit_is_separate_until_explicit_keep(self):
        session = self.open()
        self.t.key('e')
        self.t.key(('paste', 'Kept earlier.'))
        self.t.key('keep')
        self.t.key('e')
        self.t.buffers[0].text = ''
        self.t.key('escape')
        self.assertEqual('Kept earlier.', session.state()['draft']['entries'][0]['text'])
        self.assertEqual([''], list(self.app.understanding.buffers.values()))
        self.t.key('e')
        self.assertEqual('', self.t.buffers[0].text)
        self.t.key('keep')
        self.assertEqual('', session.state()['draft']['entries'][0]['text'])
        self.assertFalse(self.app.understanding.buffers)

    def test_other_topics_do_not_inherit_explanation_or_reuse_flag(self):
        session = self.open()
        self.t.key('r')
        self.t.key('e')
        self.t.key(('paste', 'First topic only.'))
        self.t.key('keep')
        self.t.key(']')
        self.t.key('e')
        self.assertEqual('', self.t.buffers[0].text)
        self.t.key('escape')
        self.assertFalse(session.state()['draft']['entries'][1]['reuse_rationale'])
        self.assertEqual(self.before, self.history.manifest())

    def test_unavailable_source_preserves_manual_writing_but_cannot_rebind(self):
        session = self.open()
        self.t.key('e')
        self.t.key(('paste', 'Earlier '))
        # Simulate an unavailable/replaced adapter source. Normal workspace
        # updates reject this replacement before it can reach the UI.
        self.app.paper = SimpleNamespace(history=replay_example('manual', series=True))
        self.t.key(('paste', 'context.'))
        self.assertEqual('Earlier context.', self.t.buffers[0].text)
        self.t.key('source')
        self.assertEqual('understanding-source', self.t.modal)
        frame = self.t.draw_modal(Frame(80, 24)).plain()
        self.assertIn('Source unavailable', frame)
        self.assertIn('LAST AVAILABLE', frame)
        self.t.key('escape')
        self.t.key('keep')
        self.assertEqual('Earlier context.', session.state()['draft']['entries'][0]['text'])
        digest = session.state()['draft']['context_digest']
        self.t.key('s')
        self.t.key('enter')
        self.assertEqual(digest, session.state()['draft']['context_digest'])
        self.assertEqual('understanding-read', self.t.modal)
        self.assertIn('unavailable', understanding_ui(self.t).notice)

    def test_reverting_unfinished_input_clears_it_without_changing_kept_text(self):
        session = self.open()
        self.t.key('e')
        self.t.key(('paste', 'Unfinished'))
        self.t.key('escape')
        self.t.key('e')
        self.t.buffers[0].text = ''
        self.t.key('escape')
        self.assertFalse(self.app.understanding.buffers)
        self.assertEqual('', session.state()['draft']['entries'][0]['text'])
        self.assertFalse(self.app.understanding.volatile_work())

    def test_science_names_missing_connections_and_ai_judgment_identity(self):
        self.open()
        ui = understanding_ui(self.t)
        state = ui.state()
        topic = state['topics'][0]
        self.assertTrue(topic['relation_ids'])
        current = state['context']['current']
        current['relations'] = []
        text = '\n'.join(text for text, _ in ui.science(state, current, topic))
        for key in topic['relation_ids']:
            self.assertIn(key + ': connection absent', text)
        ui.view = 'AI history'
        text = '\n'.join(text for text, _ in ui.lines(state))
        self.assertIn('THIS JUDGMENT', text)
        self.assertIn(state['context']['work']['cause_operation_id'], text)
        for index, source in enumerate(state['context']['work']['source_judgments'], 1):
            self.assertIn('SOURCE JUDGMENT ' + str(index) + ' / ' + source['episode_id'], text)
