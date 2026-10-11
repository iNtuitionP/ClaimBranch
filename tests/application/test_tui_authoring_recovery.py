"""Return to authored science and provisional results without accepting them."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from claimbranch.application.tui import Terminal, Buffer
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import snapshot, restore, JudgmentRecovery, excluded_work
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_merge_example


class AuthoringRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_merge_example('manual')
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.app.select('obs-1')

    def claim(self):
        work = self.app.review.candidates()
        key = work.create('claim', {'role': 'main', 'parent_ids': ['thesis'],
            'statement': '측정되지 않은 조건은 남겨 둔다.', 'scope': 'One split only'})
        return work, key

    def reopen(self, saved=None):
        saved = snapshot(self.app) if saved is None else saved
        app = TerminalWorkspace(saved.history, ai_off=True)
        restore(app, saved)
        return app

    def test_candidates_keep_identity_omission_unfinished_and_graph_without_judgment(self):
        work, key = self.claim()
        work.toggle(key)
        other = work.create('scientific-edge', {'source_id': 'obs-1', 'target_id': key,
            'edge_type': 'qualifies', 'rationale': ''})
        unkept = work.unkeep(other)
        edited = deepcopy(work.records[key]); edited['body']['statement'] = ''
        self.app.review.candidate_inputs[self.app.work_key()] = {key: edited, other: unkept}
        saved = snapshot(self.app)
        self.assertEqual('claimbranch.paper-work/v7', decode(saved.payload)['schema'])
        app = self.reopen(saved)
        again = app.review.candidates()
        self.assertEqual(work.records, again.records)
        self.assertEqual(work.selected, again.selected)
        self.assertEqual(work.revision, again.revision)
        self.assertEqual('D1', again.alias(key)); self.assertEqual('D2', again.alias(other))
        self.assertEqual(self.app.review.candidate_inputs, app.review.candidate_inputs)
        self.assertEqual('', app.draft()['text'])
        again.project()
        again.put(unkept)
        self.assertNotIn(key, again.selected)
        self.assertIsNone(app.review.session().state()['changes_review'])
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())

    def test_result_kept_and_empty_unfinished_with_original_source_are_independent(self):
        owner = self.app.context_key()
        key = self.app.intake.create(owner)
        self.app.intake.keep(key, 'observation', '새로운 결과 / 미확인')
        self.app.intake.keep(key, 'judgment', 'Earlier tentative judgment')
        self.app.intake.retain(key, 'judgment', '')
        second = self.app.intake.create(owner)
        self.app.intake.keep(second, 'source_ref', 'ssh://host/result.csv')
        app = self.reopen()
        self.assertEqual(self.app.intake.items(), app.intake.items())
        self.assertEqual('', app.intake.get(key)['unfinished']['judgment'])
        self.assertEqual('Earlier tentative judgment', app.intake.get(key)['kept']['judgment'])
        self.assertEqual([], app.review.pending)
        self.assertFalse(app.paper._drafts)
        self.assertEqual(3, app.intake.get(app.intake.create(owner))['number'])

    def test_original_basis_survives_a_later_source_change(self):
        # Start at a legitimate prefix, then append the original remaining events.
        earlier = ResearchHistory.replay(self.history.seed, self.history.commands[:-1])
        self.app = TerminalWorkspace(earlier, ai_off=True)
        self.app.select('obs-1')
        work, key = self.claim()
        intake = self.app.intake.create(self.app.context_key())
        self.app.intake.keep(intake, 'observation', 'Before source update')
        original = self.app.intake.get(intake)['source']
        binding = work._binding
        self.app.paper.update_history(self.history)
        app = self.reopen()
        again = app.review.candidates()
        self.assertEqual(binding, again._binding)
        with self.assertRaisesRegex(ContractError, 'Source changed'): again.require_current()
        self.assertEqual(original, app.intake.get(intake)['source'])
        self.assertIn('changed', app.intake.context(intake)['status'])
        self.assertEqual(work.records, again.records)

    def test_active_candidate_and_result_edits_checkpoint_without_keeping(self):
        captured = []
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None,
            save=captured.append, verify_unchanged=lambda: None), self.app)
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = self.app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        from claimbranch.application.tui_candidates_ui import candidates_ui
        ui = candidates_ui(t); ui.enter('claim')
        ui.index = ui.fields.index('statement'); ui.edit_field()
        t.buffers[0].insert('아직 저장 버튼을 누르지 않은 주장')
        self.assertTrue(t.checkpoint(), self.app.recovery_error)
        app = self.reopen(captured[-1])
        self.assertFalse(app.review.candidates().records)
        self.assertEqual('아직 저장 버튼을 누르지 않은 주장',
            next(iter(app.review.candidate_inputs[app.work_key()].values()))['body']['statement'])
        self.assertFalse(ui.inputs)
        from claimbranch.application.tui_intake_ui import intake_ui
        intake = intake_ui(t); intake.enter('new'); intake.key('enter')
        t.buffers[0].insert('아직 확인하지 않은 결과')
        self.assertTrue(t.checkpoint(), self.app.recovery_error)
        app = self.reopen(captured[-1])
        result = app.intake.items()[0]
        self.assertEqual('', result['kept']['observation'])
        self.assertEqual('아직 확인하지 않은 결과', result['unfinished']['observation'])
        self.assertNotIn('result drafts', excluded_work(self.app))

    def test_malformed_sources_selections_and_duplicates_fail_closed(self):
        work, key = self.claim()
        result = self.app.intake.create(self.app.context_key())
        self.app.intake.keep(result, 'value', '0.4')
        saved = snapshot(self.app)
        for mutation in ('source', 'selection', 'alias', 'duplicate', 'result-source', 'field'):
            value = decode(saved.payload); layer = value['workspace']['authoring']
            candidate = layer['candidates'][0]
            if mutation == 'source': candidate['source']['commands'] = 99
            elif mutation == 'selection': candidate['selected'] = ['missing']
            elif mutation == 'alias': candidate['aliases'][0]['alias'] = 'D999'
            elif mutation == 'duplicate': layer['candidates'] *= 2
            elif mutation == 'result-source': layer['intake']['items'][0]['source']['digest'] = '0' * 64
            else: layer['intake']['items'][0]['kept']['confirmed'] = 'yes'
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        self.assertEqual(work.records[key]['body']['statement'], '측정되지 않은 조건은 남겨 둔다.')

    def test_result_original_ai_history_survives_ai_off_and_failed_save_keeps_text(self):
        self.app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        result = self.app.intake.create(self.app.context_key())
        self.app.intake.keep(result, 'judgment', 'My tentative reading')
        original = self.app.intake.get(result)['source']
        self.assertTrue(any(c['contributor'] == 'ai' for j in original['judgments'] for c in j['history']))
        app = self.reopen()
        self.assertEqual(original, app.intake.get(result)['source'])
        self.assertFalse(app.paper.ai_available)
        self.app.intake.retain(result, 'judgment', '한' * 12000)
        with self.assertRaises(ContractError): snapshot(self.app)
        self.assertEqual('한' * 12000, self.app.intake.get(result)['unfinished']['judgment'])

    def test_recovered_forms_explain_retention_at_wide_and_narrow_sizes(self):
        from claimbranch.application.tui import Frame
        from claimbranch.application.tui_candidates_ui import candidates_ui
        from claimbranch.application.tui_intake_ui import intake_ui
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None), self.app)
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = self.app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            candidates_ui(t).enter('claim')
            self.assertIn('encrypted recovery', candidates_ui(t).draw(Frame(width, height)).plain())
            intake_ui(t).enter('new')
            self.assertIn('encrypted recovery', intake_ui(t).draw(Frame(width, height)).plain())

    def test_nullable_original_scope_stays_missing_on_return(self):
        self.app.review.stage('claim-pruning', {'statement': 'Partial revision', 'scope': None})
        app = self.reopen()
        self.assertIsNone(app.review.candidates().records['claim-pruning']['body']['scope'])

    def test_returned_form_does_not_report_retained_text_as_discarded(self):
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None,
            save=lambda work: None, verify_unchanged=lambda: None), self.app)
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = self.app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        from claimbranch.application.tui_intake_ui import intake_ui
        ui = intake_ui(t); ui.enter('new'); ui.key('enter')
        t.buffers[0].insert('Retained unfinished observation')
        ui.key('escape')
        self.assertEqual('intake-form', t.modal)
        self.assertTrue(t.checkpoint())
        self.assertNotIn('unfinished research editor text', excluded_work(self.app))

    def test_active_candidate_returned_to_kept_value_drops_redundant_unfinished(self):
        work, key = self.claim()
        record = deepcopy(work.records[key])
        earlier = deepcopy(record); earlier['body']['statement'] = 'Earlier unfinished writing'
        self.app.review.candidate_inputs[self.app.work_key()] = {key: earlier}
        app = self.reopen(snapshot(self.app, ('candidate', (self.app.work_key(), record))))
        self.assertFalse(app.review.candidate_inputs)

    def test_ai_on_counters_and_new_owner_after_restore_roundtrip(self):
        self.app = TerminalWorkspace(self.history, ai_off=False)
        work, key = self.claim()
        before = (work.revision, self.app.paper.work_revision, self.app.review.session().state()['revision'])
        saved = snapshot(self.app)
        app = TerminalWorkspace(self.history, ai_off=False)
        restore(app, saved)
        again = app.review.candidates()
        self.assertEqual(before, (again.revision, app.paper.work_revision, app.review.session().state()['revision']))
        self.assertTrue(app.paper.ai_available)
        app.select('claim-pruning')
        app.review.candidates().create('claim', {'role': '', 'parent_ids': [], 'statement': 'e\u0301', 'scope': ''})
        after = self.reopen(snapshot(app))
        self.assertEqual(2, len(after.review.candidate_works))
        self.assertEqual('é', next(iter(after.review.candidates().records.values()))['body']['statement'])

    def test_old_judgment_workspace_remains_readable(self):
        self.app.keep_draft('Old judgment', 'Old reason')
        value = decode(snapshot(self.app).payload)
        value['schema'] = 'claimbranch.paper-work/v2'
        value['workspace']['schema'] = 'claimbranch.judgment-workspace/v1'
        value['workspace'].pop('authoring', None)
        value['workspace'].pop('understanding', None)
        value['workspace'].pop('review_writing', None)
        value['workspace'].pop('manuscript', None)
        app = self.reopen(PaperWork(canonical_bytes(value)))
        self.assertEqual('Old judgment', app.draft()['text'])
        self.assertFalse(app.intake.items()); self.assertFalse(app.review.candidate_inputs)


if __name__ == '__main__': unittest.main()
