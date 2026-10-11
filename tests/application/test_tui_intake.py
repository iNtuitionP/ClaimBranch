"""Provisional source capture must never manufacture evidence or lose writing."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.paper_intake import PaperResultIntake
from claimbranch.application.paper_workspace import PaperWorkspace
from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example


class ResultIntakeTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.workspace = PaperWorkspace(self.history)
        self.intake = PaperResultIntake(self.workspace)
        view = self.workspace.service.query()
        self.owner = (view['episode_id'], 'main', 'claim-pruning')

    def test_partial_capture_is_detached_from_science_and_other_results(self):
        key = self.intake.create(self.owner)
        other = self.intake.create(self.owner)
        self.intake.keep(key, 'observation', '새 조건에서는 결과를 아직 해석하지 못했다.')
        self.intake.keep(key, 'source_ref', 'ssh://experiment-host/results/new.csv')
        state = self.intake.get(key)
        self.assertEqual('', state['kept']['judgment'])
        self.assertEqual('', self.intake.get(other)['kept']['observation'])
        state['kept']['observation'] = 'tampered'
        state['source']['nodes'].clear()
        self.assertIn('새 조건', self.intake.get(key)['kept']['observation'])
        self.assertTrue(self.intake.get(key)['source']['nodes'])
        self.assertEqual(self.original, self.history.manifest())
        self.assertFalse(self.workspace._drafts)

    def test_cancelled_empty_text_and_keep_are_separate(self):
        key = self.intake.create(self.owner)
        self.intake.keep(key, 'judgment', 'Tentative reading')
        self.intake.retain(key, 'judgment', '')
        state = self.intake.get(key)
        self.assertEqual('Tentative reading', state['kept']['judgment'])
        self.assertEqual('', state['unfinished']['judgment'])
        self.intake.retain(key, 'judgment', 'Tentative reading')
        self.assertNotIn('judgment', self.intake.get(key)['unfinished'])
        self.intake.keep(key, 'judgment', '')
        self.assertEqual('', self.intake.get(key)['kept']['judgment'])

    def test_capacity_validation_and_pristine_cleanup_do_not_evict(self):
        key = self.intake.create(self.owner)
        self.intake.drop_empty(key)
        self.assertEqual([], self.intake.items())
        for i in range(16):
            key = self.intake.create(self.owner)
            self.intake.keep(key, 'observation', str(i))
        before = self.intake.items()
        with self.assertRaises(ContractError):
            self.intake.create(self.owner)
        with self.assertRaises(ContractError):
            self.intake.keep(key, 'value', 'x' * 12001)
        with self.assertRaises(ContractError):
            self.intake.keep(key, 'confirmed', 'yes')
        self.assertEqual(before, self.intake.items())
        self.intake.remove(key)
        self.assertEqual(15, len(self.intake.items()))

    def test_series_contexts_retain_recorded_ai_without_new_contributions(self):
        history = replay_example('recorded', paper=True, series=True)
        workspace = PaperWorkspace(history)
        intake = PaperResultIntake(workspace)
        episodes = workspace.service.episodes()['episodes']
        keys = []
        for episode in episodes:
            view = workspace.service.query('main', episode_id=episode['id'])
            key = intake.create((episode['id'], 'main', view['thesis_id']))
            intake.keep(key, 'judgment', 'Unresolved result for ' + episode['id'])
            keys.append(key)
        self.assertGreater(len(keys), 1)
        first, second = (intake.get(key) for key in keys[:2])
        self.assertNotEqual(first['owner'], second['owner'])
        self.assertNotEqual(first['kept']['judgment'], second['kept']['judgment'])
        self.assertTrue(any(c['contributor'] == 'ai' for j in first['source']['judgments'] for c in j['history']))
        self.assertFalse(workspace._drafts)

    def test_normalized_length_limit_preserves_previous_text(self):
        key = self.intake.create(self.owner)
        self.intake.keep(key, 'observation', 'Previous writing')
        with self.assertRaises(ContractError):
            self.intake.keep(key, 'observation', '\u0344' * 12000)
        self.assertEqual('Previous writing', self.intake.get(key)['kept']['observation'])


class ResultIntakeUITests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.t = Terminal.__new__(Terminal)
        self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.app.select('claim-pruning')
        self.t.modal, self.t.buffers, self.t.field = None, [], 0
        self.t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))

    def action(self, name):
        from claimbranch.application.tui_actions import actions_ui
        self.t.key(';')
        ui = actions_ui(self.t)
        ui.index = next(i for i, action in enumerate(ui.items()) if action.title == name)
        self.t.key('enter')

    def ui(self):
        from claimbranch.application.tui_intake_ui import intake_ui
        return intake_ui(self.t)

    def field(self, name, text, *, keep=True):
        ui = self.ui()
        ui.index = ui.fields.index(name)
        self.t.key('enter')
        self.t.key(('paste', text))
        self.t.key('keep' if keep else 'escape')

    def test_result_and_tentative_judgment_keep_context_without_confirming_evidence(self):
        before = self.t.app._navigation()
        self.action('Draft a result and source')
        self.field('observation', '추가 조건의 관찰 초안')
        self.field('conditions', 'Another evaluation split; interpretation remains open.')
        self.field('judgment', '지금은 결론을 유보한다.')
        self.t.key('r')
        self.assertEqual('intake-read', self.t.modal)
        state = self.t.app.intake.get(self.ui().entry_id)
        self.assertEqual('', state['kept']['run_ref'])
        self.assertEqual('', self.t.app.draft()['text'])
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('UNCONFIRMED', self.t.draw_modal(Frame(width, height)).plain())
        self.t.key('escape')
        self.t.key('escape')
        self.t.key('escape')
        self.assertIsNone(self.t.modal)
        self.assertEqual(before, self.t.app._navigation())
        self.assertEqual(self.original, self.history.manifest())
        self.assertFalse(self.t.app.paper._drafts)

    def test_source_peek_resize_and_resume_preserve_editor_and_empty_cancel(self):
        self.action('Draft a result and source')
        self.field('observation', 'Kept result')
        ui = self.ui()
        ui.index = ui.fields.index('observation')
        self.t.key('enter')
        self.t.key(('paste', ' / 미완성'))
        buffer = self.t.buffers[0]
        before = (buffer.text, buffer.cursor, list(buffer.undo))
        self.t.key('source')
        self.t.key(('paste', 'must not enter'))
        self.t.key('keep')
        self.t.screen.getmaxyx = lambda: (18, 48)
        self.t.draw_modal(Frame(48, 18))
        self.t.key('escape')
        self.assertIs(buffer, self.t.buffers[0])
        self.assertEqual(before, (buffer.text, buffer.cursor, list(buffer.undo)))
        self.t.key('escape')
        state = self.t.app.intake.get(ui.entry_id)
        self.assertEqual('Kept result', state['kept']['observation'])
        self.assertEqual(before[0], state['unfinished']['observation'])
        self.t.key('enter')
        self.assertEqual(before[0], self.t.buffers[0].text)
        self.t.buffers[0].text = ''
        self.t.key('escape')
        self.assertEqual('', self.t.app.intake.get(ui.entry_id)['unfinished']['observation'])

    def test_unavailable_or_changed_source_keeps_original_context_and_editable_text(self):
        self.action('Draft a result and source')
        self.field('observation', 'Original captured observation')
        ui = self.ui()
        initial = self.t.app.intake.get(ui.entry_id)['source']
        with patch.object(self.t.app.paper.service, 'query', side_effect=ContractError('Source unavailable')):
            self.t.key('r')
            self.t.key('tab')
            self.assertIn('unavailable', self.t.draw_modal(Frame(144, 42)).plain().lower())
            self.t.key('escape')
            self.field('rationale', 'Retained-context reasoning only')
        changed = {**initial, 'digest': '0' * 64}
        with patch.object(self.t.app.paper.service, 'query', return_value=changed):
            self.assertIn('changed', self.t.app.intake.context(ui.entry_id)['status'])
        self.assertEqual(initial, self.t.app.intake.get(ui.entry_id)['source'])

    def test_result_drafts_stay_out_of_checkpoints_and_warn_on_quit(self):
        from claimbranch.application.tui_recovery import DraftRecovery
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'manual.json'
            self.t.app.recovery = DraftRecovery(path, self.t.app)
            try:
                self.action('Draft a result and source')
                self.t.key('enter')
                self.t.key(('paste', 'UNCONFIRMED_RESULT_SENTINEL'))
                self.assertTrue(self.t.checkpoint())
                self.assertNotIn('UNCONFIRMED_RESULT_SENTINEL', path.read_text())
                self.t.key('source')
                self.assertTrue(self.t.checkpoint())
                self.assertNotIn('UNCONFIRMED_RESULT_SENTINEL', path.read_text())
                self.t.key('escape')
                self.t.key('escape')
                self.t.key('escape')
                self.t.key('escape')
                self.assertIsNone(self.t.modal)
                self.assertTrue(self.t.checkpoint())
                self.assertNotIn('UNCONFIRMED_RESULT_SENTINEL', path.read_text())
                self.t.key('n')
                self.assertTrue(self.t.checkpoint())
                self.assertNotIn('UNCONFIRMED_RESULT_SENTINEL', path.read_text())
                self.t.key('escape')
                self.t.key('q')
                self.assertEqual('quit', self.t.modal)
                self.assertIn('result drafts', self.t.draw_modal(Frame(144, 42)).plain())
                self.t.key('escape')
            finally:
                self.t.app.recovery.close()
            fresh = TerminalWorkspace(self.history, ai_off=True)
            restore = DraftRecovery(path, fresh)
            self.assertFalse(fresh.intake.items())
            restore.close()

    def test_pristine_cancel_resume_from_another_node_and_confirmed_discard(self):
        self.action('Draft a result and source')
        self.t.key('escape')
        self.assertFalse(self.t.app.intake.items())
        self.t.key('escape')
        self.action('Draft a result and source')
        self.field('observation', 'One result with stable ownership')
        key = self.ui().entry_id
        self.t.key('escape')
        self.t.key('escape')
        self.t.app.select('obs-1')
        before = self.t.app._navigation()
        self.action('Resume result drafts')
        self.t.key('enter')
        self.assertEqual(key, self.ui().entry_id)
        self.assertEqual('claim-pruning', self.t.app.intake.get(key)['owner'][2])
        self.t.key('escape')
        self.t.key('d')
        self.t.key('escape')
        self.assertEqual(1, len(self.t.app.intake.items()))
        self.t.key('d')
        self.t.key('enter')
        self.assertFalse(self.t.app.intake.items())
        self.t.key('escape')
        self.assertEqual(before, self.t.app._navigation())

    def test_tiny_view_pauses_input_and_source_references_never_open(self):
        self.action('Draft a result and source')
        ui = self.ui()
        ui.index = ui.fields.index('source_ref')
        self.t.key('enter')
        with patch.object(Path, 'open', side_effect=AssertionError('Source reference opened')):
            self.t.key(('paste', 'ssh://host/results/a.csv'))
            self.t.screen.getmaxyx = lambda: (12, 36)
            self.t.key(('paste', 'must not enter'))
            self.t.key('keep')
            self.assertIn('paused', self.t.draw_modal(Frame(36, 12)).plain())
            self.assertEqual('intake-text', self.t.modal)
            self.t.key('escape')
        state = self.t.app.intake.get(ui.entry_id)
        self.assertEqual('', state['kept']['source_ref'])
        self.assertEqual('ssh://host/results/a.csv', state['unfinished']['source_ref'])

    def test_peek_distinguishes_live_editor_from_stored_unfinished_text(self):
        self.action('Draft a result and source')
        self.field('observation', 'Kept observation')
        self.t.key('enter')
        self.t.key(('paste', ' OLD'))
        self.t.key('escape')
        self.t.key('enter')
        self.t.key(('paste', ' LIVE'))
        buffer = self.t.buffers[0]
        before = (buffer.text, buffer.cursor, list(buffer.undo))
        self.t.key('source')
        text = self.t.draw_modal(Frame(144, 42)).plain()
        self.assertIn('IN EDITOR / not kept', text)
        self.assertIn('Kept observation OLD LIVE', text)
        state = self.t.app.intake.get(self.ui().entry_id)
        self.assertEqual('Kept observation OLD', state['unfinished']['observation'])
        self.t.key('escape')
        self.assertEqual(before, (buffer.text, buffer.cursor, list(buffer.undo)))

    def test_cancel_discard_and_return_preserve_the_selected_result(self):
        for text in ('First result', 'Second result'):
            self.action('Draft a result and source')
            self.field('observation', text)
            self.t.key('escape')
            self.t.key('escape')
        self.action('Resume result drafts')
        self.t.key('end')
        self.t.key('d')
        second = self.ui().entry_id
        self.t.key('escape')
        self.t.key('d')
        self.assertEqual(second, self.ui().entry_id)
        self.t.key('escape')
        self.t.key('enter')
        self.t.key('escape')
        self.t.key('enter')
        self.assertEqual(second, self.ui().entry_id)


if __name__ == '__main__':
    unittest.main()
