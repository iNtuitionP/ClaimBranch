"""Manual interpretation construction with exact source and judgment reuse."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from claimbranch.application.tui import Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example, replay_merge_example
from tests.application import test_tui_candidates as authoring


class InterpretationTests(unittest.TestCase):
    action, ui, field = authoring.AuthoringTests.action, authoring.AuthoringTests.ui, authoring.AuthoringTests.field

    def setUp(self):
        authoring.AuthoringTests.setUp(self)
        self.history = replay_merge_example('manual')
        self.original = self.history.manifest()
        self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.app.select('obs-1')

    def write(self, text='측정 조건 안에서만 해석한다.'):
        self.action('Write an interpretation')
        self.assertEqual('candidate-form', self.t.modal)
        self.field('statement', text)
        ui = self.ui()
        ui.index = ui.fields.index('observation_ids')
        self.t.key('enter')
        self.assertEqual({'obs-1', 'obs-2'}, {key for key, _ in ui.choices})
        for key in ('obs-1', 'obs-2'):
            ui.index = next(i for i, item in enumerate(ui.choices) if item[0] == key)
            self.t.key(' ')
        self.t.key('enter')
        key = ui.record['id']
        self.t.key('keep')
        return key

    def test_manual_interpretation_graph_before_judgment_and_no_new_evidence(self):
        key = self.write()
        ui = self.ui()
        self.assertEqual(['obs-1', 'obs-2'], ui.work.records[key]['body']['observation_ids'])
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        links = [r for r in ui.graph.view['relations'] if r['source_id'] == key]
        self.assertEqual({('interprets', 'obs-1'), ('interprets', 'obs-2')},
                         {(r['type'], r['target_id']) for r in links})
        self.assertTrue(all(r['draft'] and not r['scientific'] for r in links))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('DRAFT GRAPH', self.t.draw_modal(Frame(width, height)).plain())
        self.assertEqual('', self.t.app.draft()['text'])
        self.assertFalse(self.t.app.review.session().state()['traces'])
        self.assertEqual(self.original, self.history.manifest())

    def test_picker_cancel_and_intentionally_empty_basis_are_distinct(self):
        self.action('Write an interpretation')
        ui = self.ui()
        self.t.key('escape')
        self.assertFalse(ui.inputs)
        self.t.key('i')
        self.field('statement', 'An unresolved explanation without linked observations.')
        ui.index = ui.fields.index('observation_ids')
        self.t.key('enter')
        self.t.key(' ')
        self.t.key('escape')
        self.assertEqual([], ui.record['body']['observation_ids'])
        self.t.key('enter')
        self.t.key('enter')  # Explicitly confirm the empty selection too.
        self.assertEqual([], ui.record['body']['observation_ids'])
        self.t.key('keep')
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        self.assertFalse([r for r in ui.graph.view['relations'] if r['source_id'] == ui.record['id']])

    def test_occupied_context_blocks_duplicate_and_retains_unfinished_form(self):
        self.t.app = TerminalWorkspace(replay_example('manual', paper=True), ai_off=True)
        self.action('Write an interpretation')
        self.assertEqual('actions', self.t.modal)
        self.assertIn('Edit scientific changes', self.t.draw_modal(Frame(144, 42)).plain())
        self.t.key('escape')
        self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.app.select('obs-1')
        self.action('Write an interpretation')
        self.field('statement', 'Unfinished interpretation.')
        self.t.key('escape')
        ui = self.ui()
        before = deepcopy(ui.inputs)
        self.t.key('i')
        self.assertEqual('candidate-list', self.t.modal)
        self.assertEqual(before, ui.inputs)
        self.assertIn('Open argument drafts', ui.notice)

    def test_explicit_reuse_preserves_reason_prior_contributions_and_invalidates_review(self):
        key = self.write()
        ui = self.ui()
        self.t.app.keep_draft('A different earlier judgment.', 'Retain this reason.')
        self.t.app.review.session().review_draft()
        previous = self.t.app.review.session()._judgment
        self.t.key('J')
        self.assertEqual('candidate-judgment', self.t.modal)
        self.t.key('escape')
        self.assertEqual(previous, self.t.app.review.session()._judgment)
        self.t.key('J')
        self.t.key('enter')
        self.assertEqual(ui.work.records[key]['body']['statement'], self.t.app.draft()['text'])
        self.assertEqual('Retain this reason.', self.t.app.draft()['rationale'])
        self.t.app.review.session().review_draft()
        current = self.t.app.review.session()._judgment
        self.assertEqual(previous.history, current.history[:len(previous.history)])
        self.t.key('R')
        self.assertIsNotNone(self.t.app.review.session().get_changes_preview())
        changed = ui.work.records[key]
        changed['body']['statement'] = 'A later interpretation.'
        ui.work.put(changed)
        self.assertIsNone(self.t.app.review.session().get_changes_preview())
        self.assertEqual(self.original, self.history.manifest())

    def test_connection_review_requires_draft_interpretation_even_when_omitted(self):
        key = self.write('An interpretation of the measured conditions.')
        ui = self.ui()
        link = ui.work.create('scientific-edge', {'source_id': key, 'target_id': 'claim-pruning',
            'edge_type': 'qualifies', 'rationale': 'Only the measured conditions apply.'})
        ui.work.toggle(key)
        self.t.app.keep_draft(ui.work.records[key]['body']['statement'], 'A bounded interpretation.')
        self.t.key('R')
        selection = self.t.app.review.session().get_changes_preview()['preview']['selection']
        self.assertIn(key, selection['required'])
        self.assertIn(link, selection['selected'])
        self.assertEqual(self.original, self.history.manifest())

    def test_partial_and_kept_interpretation_stay_out_of_manual_checkpoint(self):
        key = self.write()
        self.t.key('enter')
        self.field('statement', ' Unkept writing.')
        self.t.key('escape')
        from claimbranch.application.tui_recovery import DraftRecovery
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'draft.json'
            store = DraftRecovery(path, self.t.app)
            try:
                store.save(self.t.app)
            finally:
                store.close()
            self.assertNotIn(key, path.read_text())
            self.assertNotIn('Unkept writing', path.read_text())
        self.assertTrue(self.t.app.review.volatile_work())

    def test_ai_contributions_survive_explicit_reuse(self):
        self.t.app = TerminalWorkspace(self.history)
        self.t.app.select('obs-1')
        key = self.write()
        app = self.t.app
        app.keep_draft('My initial reading.', 'My retained reason.')
        request = app.review.prepare_ai(['obs-1'], include_draft=True)
        app.review.begin_ai(request)
        app.review.complete_ai(app.review.key, request['request']['request_id'])
        app.review.session().use_proposal(app.review.session().state()['proposal']['id'])
        before = deepcopy(app.review.session().state()['draft']['contributions'])
        self.assertTrue(app.review.influenced())
        self.t.key('J')
        self.t.key('enter')
        self.assertEqual(self.ui().work.records[key]['body']['statement'], app.draft()['text'])
        self.assertEqual('My retained reason.', app.draft()['rationale'])
        app.review.prepare_changes()
        self.assertEqual(before, app.review.session().state()['draft']['contributions'][:len(before)])
        self.assertTrue(app.review.influenced())

    def test_reuse_rejects_unfinished_stale_or_changed_work_without_losing_text(self):
        key = self.write()
        ui = self.ui()
        self.t.app.keep_draft('Keep the current judgment.', '')
        self.t.key('enter')
        self.field('statement', ' Pending addition.')
        self.t.key('escape')
        self.t.key('J')
        self.assertEqual('candidate-list', self.t.modal)
        self.assertIn('unfinished', ui.notice)
        self.t.key('enter')
        self.t.key('keep')
        self.t.key('J')
        changed = ui.work.records[key]
        changed['body']['statement'] = 'Changed after the displayed comparison.'
        ui.work.put(changed)
        self.t.key('enter')
        self.assertEqual('candidate-judgment', self.t.modal)
        self.assertIn('Work changed', ui.notice)
        self.assertEqual('Keep the current judgment.', self.t.app.draft()['text'])
        self.t.key('escape')
        self.t.key('J')
        self.t.app.paper.update_history(replay_example('manual', series=True))
        self.t.key('enter')
        self.assertEqual('candidate-judgment', self.t.modal)
        self.assertIn('Source changed', ui.notice)
        self.assertEqual('Keep the current judgment.', self.t.app.draft()['text'])

    def test_tiny_terminal_blocks_picker_and_reuse_but_escape_preserves_work(self):
        key = self.write()
        self.t.key('J')
        self.t.screen.getmaxyx = lambda: (12, 36)
        self.t.key('enter')
        self.assertEqual('', self.t.app.draft()['text'])
        self.assertIn('paused', self.t.draw_modal(Frame(36, 12)).plain())
        self.t.key('escape')
        self.assertIn(key, self.ui().work.records)

    def test_domain_rejects_unknown_basis_and_duplicate_interpretation(self):
        key = self.write()
        work = self.ui().work
        with self.assertRaises(ContractError):
            work.create('interpretation', {'statement': 'Duplicate.', 'observation_ids': []})
        invalid = work.records[key]
        invalid['body']['observation_ids'] = ['claim-pruning']
        work.put(invalid)
        with self.assertRaises(ContractError):
            work.project()
        self.assertEqual(['claim-pruning'], work.records[key]['body']['observation_ids'])
        self.assertEqual(self.original, self.history.manifest())

    def test_unrelated_review_explains_the_domain_requirement_for_omitted_interpretation(self):
        key = self.write()
        work = self.ui().work
        work.toggle(key)
        work.create('claim', {'role': 'main', 'parent_ids': ['thesis'],
            'statement': 'Another bounded claim.', 'scope': 'The measured conditions.'})
        self.t.app.keep_draft('A different judgment.', 'A different reason.')
        self.t.key('R')
        self.assertIn('unkeep', self.t.app.message)
        self.assertIsNone(self.t.app.review.session().get_changes_preview())
        work.unkeep(key)
        self.t.app.review.prepare_changes()
        self.assertIsNotNone(self.t.app.review.session().get_changes_preview())

    def test_reuse_refuses_oversized_existing_reason_without_changing_judgment(self):
        self.write()
        self.t.app.keep_draft('Retain the existing judgment.', '가' * 6000)
        before = self.t.app.draft()
        self.t.key('J')
        self.assertEqual('candidate-list', self.t.modal)
        self.assertIn('reason', self.ui().notice)
        self.assertEqual(before, self.t.app.draft())

    def test_observation_picker_keeps_status_visible_and_reads_full_source(self):
        self.write()
        self.t.key('enter')
        ui = self.ui()
        ui.index = ui.fields.index('observation_ids')
        self.t.key('enter')
        self.assertIn('corrected', self.t.draw_modal(Frame(48, 18)).plain())
        chosen = set(ui.picked)
        self.t.key('r')
        self.assertEqual('candidate-observation', self.t.modal)
        self.assertIn('READ OBSERVATION', self.t.draw_modal(Frame(80, 24)).plain())
        self.t.key(('paste', 'q\n'))
        self.t.key('keep')
        self.t.key('escape')
        self.assertEqual('candidate-pick', self.t.modal)
        self.assertEqual(chosen, ui.picked)

    def test_independent_work_can_explore_its_own_alternative_without_merging_drafts(self):
        first = self.write('First work interpretation.')
        old = self.ui().work
        self.t.key('escape')
        self.t.app.select('obs-2')
        second = self.write('Second work interpretation.')
        self.assertNotEqual(first, second)
        self.assertNotIn(first, self.ui().work.records)
        self.assertNotIn(second, old.records)
        self.assertEqual(self.original, self.history.manifest())

    def test_cancelling_an_intentionally_empty_edit_retains_it_apart_from_kept_text(self):
        self.action('Write an interpretation')
        self.field('statement', 'A tentative interpretation.')
        self.t.key('keep')
        key = self.ui().record['id']
        self.t.key('enter')
        self.ui().index = 0
        self.t.key('enter')
        self.t.key('home')
        for _ in range(len(self.t.buffers[0].text)):
            self.t.key('delete')
        self.t.key('escape')
        self.t.key('escape')
        self.assertEqual('A tentative interpretation.', self.ui().work.records[key]['body']['statement'])
        self.assertEqual('', self.ui().inputs[key]['body']['statement'])
        self.t.key('J')
        self.assertEqual('candidate-list', self.t.modal)
        self.t.key('enter')
        self.assertEqual('', self.ui().record['body']['statement'])


if __name__ == '__main__':
    unittest.main()
