"""Keyboard-only manual construction before a complete judgment exists."""
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest

from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example
from claimbranch.core.research_history import ResearchHistory


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.t = Terminal.__new__(Terminal)
        self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.app.select('obs-1')
        self.t.modal, self.t.buffers, self.t.field = None, [], 0
        self.t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))

    def action(self, title):
        from claimbranch.application.tui_actions import actions_ui
        self.t.key(';')
        ui = actions_ui(self.t)
        ui.index = next(i for i, item in enumerate(ui.items()) if item.title == title)
        self.t.key('enter')

    def ui(self):
        from claimbranch.application.tui_candidates_ui import candidates_ui
        return candidates_ui(self.t)

    def field(self, name, text):
        ui = self.ui()
        ui.index = ui.fields.index(name)
        self.t.key('enter')
        self.t.key(('paste', text))
        self.t.key('escape')

    def new_claim(self):
        self.action('Add a claim or subclaim')
        ui = self.ui()
        ui.index = ui.fields.index('role')
        self.t.key('enter')
        self.t.key('enter')  # main claim, with an explicit parent selection
        ui.index = ui.fields.index('parent_ids')
        self.t.key('enter')
        self.t.key('enter')  # sole thesis
        self.field('statement', '다른 pruning mask는 아직 측정하지 않았다.')
        self.field('scope', 'A single measured mask only.')
        self.t.key('keep')
        return next(iter(ui.work.records))

    def test_create_connect_project_and_return_without_judgment_or_ai(self):
        key = self.new_claim()
        ui = self.ui()
        self.assertEqual('candidate-list', self.t.modal)
        self.t.key('l')
        for field, wanted in (('source_id', 'obs-1'), ('target_id', key), ('edge_type', 'qualifies')):
            ui.index = ui.fields.index(field)
            self.t.key('enter')
            ui.index = next(i for i, choice in enumerate(ui.choices) if choice[0] == wanted)
            self.t.key('enter')
        self.field('rationale', 'The existing observation covers only one mask.')
        self.t.key('keep')
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        self.assertIn(key, ui.graph.nodes)
        self.assertEqual('E1', ui.graph.node_label('obs-1'))
        self.assertEqual(self.t.app.node_label('claim-pruning'), ui.graph.node_label('claim-pruning'))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('DRAFT GRAPH', self.t.draw_modal(Frame(width, height)).plain())
        self.t.key('e')  # unsupported candidate judgment cannot become a checkpoint target
        self.assertEqual('candidate-graph', self.t.modal)
        self.assertFalse(ui.graph.paper._drafts)
        self.t.key('escape')
        self.t.key('escape')
        self.t.app.select('claim-comparison')
        self.action('Return to authored work')
        self.t.key('enter')
        self.assertEqual('obs-1', self.t.app.selected_id)
        self.assertIn(key, ui.work.records)
        self.assertEqual('', self.t.app.draft()['text'])
        self.assertEqual([], self.t.app.review.session().state()['traces'])
        self.assertEqual(self.original, self.history.manifest())

    def plan(self, target='claim-pruning'):
        self.action('Plan a follow-up experiment')
        ui = self.ui()
        self.assertEqual('candidate-form', self.t.modal)
        ui.index = ui.fields.index('claim_id')
        self.t.key('enter')
        self.assertNotIn('obs-1', [choice[0] for choice in ui.choices])
        ui.index = next(i for i, choice in enumerate(ui.choices) if choice[0] == target)
        self.t.key('enter')
        for field, text in (
            ('objective', '새 mask에서도 같은 범위가 유지되는가?'),
            ('conditions', 'Model A, a new fixed mask, the same evaluation split.'),
            ('metric.name', 'Classification accuracy loss'),
            ('metric.definition', '100 times the correct-count difference divided by 2000.'),
            ('metric.unit', 'percentage points'),
            ('metric.comparison', 'Unchanged Model A on the same split.')):
            self.field(field, text)
        key = ui.record['id']
        self.t.key('keep')
        return key

    def test_new_plan_without_judgment_has_explicit_measurement_and_unrun_graph(self):
        from claimbranch.application.tui_graph import node_heading
        key = self.plan()
        ui = self.ui()
        record = ui.work.records[key]
        self.assertEqual('planned', record['body']['status'])
        self.assertEqual('percentage points', record['body']['metric']['unit'])
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        self.assertEqual('D1', ui.graph.node_label(key))
        self.assertIn('DRAFT UNRUN PLAN', node_heading(ui.graph, key))
        links = [edge for edge in ui.graph.view['relations'] if edge['source_id'] == key]
        self.assertEqual(1, len(links))
        self.assertEqual(('tests', 'claim-pruning', True, False),
                         tuple(links[0][field] for field in ('type', 'target_id', 'draft', 'scientific')))
        ui.graph.select(key)
        self.t.key('enter')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            frame = self.t.draw_modal(Frame(width, height)).plain()
            self.assertIn('DRAFT GRAPH', frame)
        self.assertFalse(ui.graph.paper._drafts)
        self.assertEqual('', self.t.app.draft()['text'])
        self.assertEqual([], self.t.app.review.session().state()['traces'])
        self.assertEqual(self.original, self.history.manifest())

    def test_empty_plan_creates_no_pending_work_and_missing_metric_is_repairable(self):
        self.action('Plan a follow-up experiment')
        ui = self.ui()
        self.t.key('escape')
        self.assertFalse(ui.inputs)
        self.assertFalse(ui.work.records)
        self.t.key('p')
        self.field('metric.definition', '미완성 측정 정의')
        self.t.key('escape')
        self.assertFalse(ui.work.records)
        key = next(iter(ui.inputs))
        self.t.key('enter')
        self.t.key('keep')
        self.t.key('g')
        self.assertEqual('candidate-list', self.t.modal)
        self.assertIn('Metric name', ui.notice)
        self.assertIn('Comparison / baseline', ui.notice)
        self.assertEqual('미완성 측정 정의', ui.work.records[key]['body']['metric']['definition'])
        self.assertEqual(self.original, self.history.manifest())

    def test_plan_on_draft_claim_preserves_omission_and_requires_claim_at_review(self):
        claim = self.new_claim()
        self.t.key('escape')
        plan = self.plan(claim)
        ui = self.ui()
        self.assertEqual([plan], ui.work.dependents(claim))
        ui.work.toggle(claim)
        self.t.app.keep_draft('Need a discriminating experiment.', 'The new mask remains unmeasured.')
        self.t.key('R')
        preview = self.t.app.review.session().get_changes_preview()['preview']
        self.assertIn(claim, preview['selection']['required'])
        self.assertIn(plan, preview['selection']['selected'])
        lines = '\n'.join(text for text, _ in self.t.app.review.lines())
        self.assertIn('CLAIM TO TEST', lines)
        self.assertIn('Proposed: D1', lines)
        self.assertIn('MEASUREMENT UNIT', lines)
        self.assertNotIn("{'name'", lines)
        self.t.key('G')
        from claimbranch.application.tui_review_ui import review_ui
        self.assertEqual(ui.work.alias(plan), review_ui(self.t).graphs['after'].node_label(plan))
        compared = review_ui(self.t).graphs['after']
        compared.select(plan)
        self.assertNotIn('Press s', '\n'.join(text for text, _ in compared.detail()))
        self.t.draw_modal(Frame(80, 24))
        self.t.key('escape')
        self.t.key('enter')
        self.assertFalse(self.t.app.review.session().get_changes_review()['acceptance_available'])
        record = ui.work.records[plan]
        record['body']['metric']['comparison'] = 'A newly chosen baseline, still unmeasured.'
        ui.work.put(record)
        self.assertIsNone(self.t.app.review.session().get_changes_review())
        self.assertIn(plan, ui.work.project()['authored_ids'])
        self.assertEqual(self.original, self.history.manifest())

    def test_plan_edit_retains_omission_fields_and_draft_identity(self):
        key = self.plan()
        ui = self.ui()
        self.t.key(' ')
        self.t.key('enter')
        self.field('metric.unit', ' per evaluation split')
        self.t.key('keep')
        self.assertNotIn(key, ui.work.selected)
        self.assertEqual('D1', ui.work.alias(key))
        self.assertEqual('percentage points per evaluation split', ui.work.records[key]['body']['metric']['unit'])
        self.assertEqual('Classification accuracy loss', ui.work.records[key]['body']['metric']['name'])
        self.t.key('g')
        ui.graph.select(key)
        detail = '\n'.join(text for text, _ in ui.graph.detail())
        self.assertIn('percentage points per evaluation split', detail)
        self.assertIn('NOT RUN', detail)
        self.assertNotIn('Press s', detail)

    def test_existing_plan_keeps_objective_only_edit_policy(self):
        plan = next(key for key, item in self.t.app.review.records().items() if item['kind'] == 'experiment-plan')
        self.t.app.review.stage(plan, {'objective': 'A revised question.'})
        self.action('Open argument drafts')
        self.t.key('enter')
        self.assertEqual(('objective',), self.ui().fields)
        self.assertIn('UNRUN', self.t.draw_modal(Frame(48, 18)).plain())

    def test_reopening_plan_target_picker_preserves_current_target(self):
        key = self.plan()
        self.assertIn(self.t.app.node_label('claim-pruning'), self.ui().record_text(self.ui().work.records[key]))
        self.t.key('enter')
        self.ui().index = 0
        self.t.key('enter')
        self.assertEqual('claim-pruning', self.ui().choices[self.ui().index][0])
        self.t.key('enter')
        self.t.key('keep')
        self.assertEqual('claim-pruning', self.ui().work.records[key]['body']['claim_id'])

    def test_incomplete_input_cancel_and_omit_are_distinct(self):
        self.action('Add a claim or subclaim')
        self.field('statement', '미완성 주장')
        self.t.key('escape')
        self.assertEqual({}, self.ui().work.records)
        self.assertTrue(self.t.app.review.volatile_work())
        self.t.key('enter')
        self.t.key('keep')
        self.assertEqual('candidate-list', self.t.modal)
        self.t.key('g')
        self.assertEqual('candidate-list', self.t.modal)
        self.assertTrue(self.ui().notice)
        self.assertIn('미완성 주장', self.t.draw_modal(Frame(80, 24)).plain())
        self.assertEqual(self.original, self.history.manifest())

    def test_resize_pauses_edits_and_delete_requires_confirmation(self):
        key = self.new_claim()
        self.t.key('d')
        self.assertEqual('candidate-remove', self.t.modal)
        self.t.key('escape')
        self.assertIn(key, self.ui().work.records)
        self.t.key('enter')
        self.t.screen.getmaxyx = lambda: (12, 36)
        before = self.ui().record.copy()
        self.t.key('keep')
        self.assertEqual('candidate-form', self.t.modal)
        self.assertIn('paused', self.t.draw_modal(Frame(36, 12)).plain())
        self.assertEqual(before, self.ui().record)
        self.t.key('escape')
        self.assertIn(key, self.ui().work.records)

    def test_new_claim_reaches_final_review_and_keeps_its_alias(self):
        from claimbranch.application.tui import compose
        from claimbranch.application.tui_review_ui import review_ui
        key = self.new_claim()
        ui = self.ui()
        ui.work.create('scientific-edge', {'source_id': 'obs-1', 'target_id': key,
            'edge_type': 'qualifies', 'rationale': 'Only one measured mask.'})
        self.t.key('b')
        self.t.app.keep_draft('Measured condition only.', 'Other masks remain untested.')
        self.t.key('w')
        self.t.key('R')
        self.assertIsNotNone(self.t.app.review.session().get_changes_preview())
        compose(self.t.app, 80, 24)
        self.t.key('G')
        self.assertEqual(ui.work.alias(key), review_ui(self.t).graphs['after'].node_label(key))
        self.t.draw_modal(Frame(144, 42))
        self.t.key('escape')
        self.t.key('enter')
        self.assertFalse(self.t.app.review.session().get_changes_review()['acceptance_available'])
        self.assertEqual(self.original, self.history.manifest())

    def test_candidate_and_unkept_fields_never_enter_manual_checkpoint(self):
        from claimbranch.application.tui_recovery import DraftRecovery
        key = self.new_claim()
        self.t.key('enter')
        self.field('statement', ' Unkept extra text.')
        self.t.key('escape')
        self.t.key('escape')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'draft.json'
            store = DraftRecovery(path, self.t.app)
            try:
                store.save(self.t.app)
            finally:
                store.close()
            self.assertNotIn(key, path.read_text())
            self.assertNotIn('Unkept extra text', path.read_text())
        self.assertTrue(self.t.app.review.volatile_work())

    def test_unkeep_preserves_incomplete_text_and_unblocks_other_candidates(self):
        key = self.new_claim()
        ui = self.ui()
        self.t.key('n')
        self.field('statement', 'An unfinished second thought.')
        self.t.key('keep')
        second = next(k for k in ui.work.records if k != key)
        ui.index = list(ui.items()).index(second)
        self.t.key('u')
        self.assertNotIn(second, ui.work.records)
        self.assertIn('An unfinished', ui.inputs[second]['body']['statement'])
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        self.assertIn(key, ui.graph.nodes)
        self.assertNotIn(second, ui.graph.nodes)

    def test_kept_selection_is_visible_beside_unkept_edits_and_review_uses_kept_text(self):
        key = self.new_claim()
        ui = self.ui()
        self.t.key('enter')
        self.field('statement', 'Unkept additional wording.')
        self.t.key('escape')
        text = self.t.draw_modal(Frame(80, 24)).plain()
        self.assertIn('SELECTED', text)
        self.assertIn('UNKEPT', text)
        self.t.key('b')
        self.t.app.keep_draft('My judgment.', 'My reason.')
        self.t.key('w')
        self.t.key('R')
        preview = self.t.app.review.session().get_changes_preview()['preview']
        self.assertNotIn('Unkept additional', str(preview['amendments']))
        self.assertIn('UNKEPT CANDIDATE', '\n'.join(t for t, _ in self.t.app.review.lines()))

    def test_existing_record_form_preserves_its_original_editable_fields(self):
        self.t.app.review.stage('claim-pruning', {'statement': 'A changed claim.', 'scope': 'One mask.'})
        self.action('Open argument drafts')
        self.t.key('enter')
        self.assertEqual(('statement', 'scope'), self.ui().fields)

    def test_remove_lists_and_explicitly_removes_unkept_dependent_forms(self):
        key = self.new_claim()
        ui = self.ui()
        self.t.key('l')
        self.field('rationale', 'A connection still being written.')
        ui.record['body']['target_id'] = key
        self.t.key('escape')
        dependency = next(iter(ui.inputs))
        ui.index = 0
        self.t.key('d')
        self.assertIn(dependency, ui.dependencies(key))
        self.t.key('2')
        self.assertFalse(ui.inputs)
        self.assertFalse(ui.work.records)

    def test_source_refresh_displays_newer_source_and_requires_explicit_choice(self):
        history = replay_example('manual', series=True)
        self.t.app = TerminalWorkspace(ResearchHistory(history.seed, history.commands[:11]), ai_off=True)
        self.t.app.select('obs-1')
        self.t.app.review.stage('edge-pruning', {'edge_type': 'supports', 'rationale': 'Tentative reason.'})
        self.action('Open argument drafts')
        self.t.app.paper.update_history(history)
        self.t.key('s')
        self.assertEqual('candidate-source', self.t.modal)
        text = self.t.draw_modal(Frame(144, 42)).plain()
        self.assertIn('Current source: challenges', text)
        self.assertIn('Your draft: supports', text)
        self.t.key('escape')
        self.t.key('g')
        self.assertEqual('candidate-list', self.t.modal)
        self.t.key('s')
        self.t.key('enter')
        self.ui().work.require_current()
        self.assertEqual('supports', self.ui().work.records['edge-pruning']['body']['edge_type'])

    def test_unchanged_nullable_field_does_not_create_pending_work(self):
        self.t.app.review.stage('claim-pruning', {'statement': 'A changed claim.', 'scope': None})
        self.action('Open argument drafts')
        self.t.key('enter')
        self.ui().index = self.ui().fields.index('scope')
        self.t.key('enter')
        self.t.key('escape')
        self.assertIsNone(self.ui().record['body']['scope'])
        self.assertFalse(self.ui().inputs)

    def test_existing_claim_projection_and_domain_limits_agree(self):
        from claimbranch.core.canonical import ContractError
        self.t.app.review.stage('claim-pruning', {'statement': 'A revised claim.', 'scope': 'One mask.'})
        self.action('Open argument drafts')
        self.t.key('g')
        self.assertEqual('candidate-graph', self.t.modal)
        self.t.key('escape')
        self.t.app.review.stage('claim-pruning', {'statement': 'A revised claim.', 'scope': None})
        with self.assertRaises(ContractError):
            self.ui().work.project()
        self.t.app.keep_draft('A judgment.', 'A reason.')
        with self.assertRaises(ContractError):
            self.t.app.review.prepare_changes()
        with self.assertRaises(ContractError):
            self.t.app.review.stage('thesis', {'statement': 'Changed thesis.', 'scope': 'One condition.'})


if __name__ == '__main__':
    unittest.main()
