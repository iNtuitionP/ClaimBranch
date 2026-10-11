"""Owned manual candidates are work, not expiring review or accepted history."""
import unittest

from claimbranch.application.paper_workspace import PaperWorkspace
from claimbranch.core.canonical import ContractError
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.workspace = PaperWorkspace(self.history)
        self.episode = self.workspace.service.query('main')['episode_id']
        self.work = self.workspace.candidates(self.episode, 'main', 'obs-1')

    def claim(self, **changes):
        body = {'role': 'subclaim', 'statement': 'Another mask remains untested.',
                'scope': 'Only the measured mask.', 'parent_ids': ['claim-pruning']}
        body.update(changes)
        return self.work.create('claim', body)

    def test_blank_judgment_new_claim_shared_evidence_and_no_source_mutation(self):
        key = self.claim()
        link = self.work.create('scientific-edge', {'source_id': 'obs-1', 'target_id': key,
            'edge_type': 'qualifies', 'rationale': 'Only one mask was measured.'})
        projection = self.work.project()
        self.assertEqual({key, link}, set(projection['authored_ids']))
        self.assertTrue(next(n for n in projection['graph']['nodes'] if n['id'] == key)['draft'])
        self.assertEqual(1, sum(n['id'] == 'obs-1' for n in projection['graph']['nodes']))
        self.assertFalse(projection['acceptance_available'])
        self.assertEqual('', self.workspace.draft(*self.work.owner).state()['draft']['text'])
        self.assertEqual(self.original, self.history.manifest())

    def plan(self, target='claim-pruning', **changes):
        body = {'claim_id': target, 'objective': 'Does a different fixed mask retain this bound?',
                'status': 'planned', 'conditions': 'Model A, mask seed 100, same split.',
                'metric': {'name': 'Accuracy loss', 'definition': '100 times correct-count difference / 2000.',
                           'unit': 'percentage points', 'comparison': 'Unchanged Model A on the same split.'}}
        body.update(changes)
        return self.work.create('experiment-plan', body)

    def test_plan_creation_dependency_removal_and_evidence_identity(self):
        claim = self.claim()
        plan = self.plan(claim)
        projection = self.work.project()
        self.assertEqual([plan], self.work.dependents(claim))
        before = self.workspace.service.query('main')['nodes']
        evidence = lambda nodes: [node for node in nodes if node['kind'] in ('observation', 'experiment-record')]
        after = [{key: value for key, value in node.items() if key != 'draft'} for node in projection['graph']['nodes']]
        self.assertEqual(evidence(before), evidence(after))
        self.work.remove(claim, with_dependents=True)
        self.assertEqual({}, self.work.records)
        self.assertEqual(self.original, self.history.manifest())

    def test_invalid_plan_keeps_input_without_projecting_or_running(self):
        key = self.plan('obs-1')
        with self.assertRaises(ContractError):
            self.work.project()
        record = self.work.records[key]
        record['body']['claim_id'] = 'claim-pruning'
        record['body']['metric']['unit'] = ''
        self.work.put(record)
        with self.assertRaises(ContractError):
            self.work.project()
        record['body']['metric']['unit'] = 'percentage points'
        record['body']['status'] = 'completed'
        self.work.put(record)
        with self.assertRaises(ContractError):
            self.work.project()
        self.assertEqual('completed', self.work.records[key]['body']['status'])
        self.assertEqual(self.original, self.history.manifest())

    def test_plan_count_limit_keeps_authored_fields_without_valid_graph(self):
        for i in range(8):  # the example already contains one unrun plan
            self.plan(objective=f'Different mask {i}?')
        with self.assertRaises(ContractError):
            self.work.project()
        self.assertEqual(8, len(self.work.records))
        self.assertEqual(self.original, self.history.manifest())

    def test_plan_six_bounded_fields_can_exceed_old_claim_sized_cap(self):
        key = self.plan(objective='q' * 12000, conditions='c' * 12000,
                        metric={name: name[0] * 12000 for name in ('name', 'definition', 'unit', 'comparison')})
        self.assertIn(key, self.work.project()['authored_ids'])

    def test_malformed_metric_shape_is_rejected_but_blank_text_is_retainable(self):
        for metric in ({'name': 'Missing remaining fields'}, None, [],
                       {'name': 'x', 'definition': '', 'unit': None, 'comparison': ''}):
            with self.assertRaises(ContractError):
                self.plan(metric=metric)
        key = self.plan(metric={name: '' for name in ('name', 'definition', 'unit', 'comparison')})
        self.assertIn(key, self.work.records)
        with self.assertRaises(ContractError):
            self.work.project()

    def test_partial_fields_are_retained_and_repaired_under_same_id(self):
        key = self.claim(statement='')
        with self.assertRaises(ContractError):
            self.work.project()
        record = self.work.records[key]
        record['body']['statement'] = 'Revised by the researcher.'
        self.work.put(record)
        self.assertEqual([key], self.work.project()['authored_ids'])
        record['body']['statement'] = 'External mutation'
        self.assertNotEqual('External mutation', self.work.records[key]['body']['statement'])

    def test_owner_survives_judgment_edits_and_mutation_revokes_exact_review(self):
        key = self.claim()
        session = self.workspace.draft(*self.work.owner)
        session.edit(text='A manual judgment.', rationale='Only one mask was measured.')
        state = session.state()
        preview = session.prepare_changes({'schema_version': 1, **state['paper'],
            'draft_id': state['draft_id'], 'draft_revision': state['revision'],
            'amendments': list(self.work.records.values()), 'selected_ids': [key]})
        revision = self.work.revision
        self.work.toggle(key)
        self.assertGreater(self.work.revision, revision)
        self.assertIsNone(session.get_changes_preview())
        self.assertEqual([key], self.work.project()['authored_ids'])
        session.edit(text='Still considering.', rationale='')
        self.assertIn(key, self.work.records)
        with self.assertRaises(ContractError):
            session.finish_changes_review(preview['digest'], disposition='answered', answers=[])
        self.assertEqual({}, self.workspace.candidates(self.episode, 'main', 'claim-pruning').records)

    def test_removal_is_distinct_from_omission_and_dependencies_are_explicit(self):
        key = self.claim()
        link = self.work.create('scientific-edge', {'source_id': 'obs-1', 'target_id': key,
            'edge_type': 'supports', 'rationale': 'A tentative connection.'})
        self.assertEqual([link], self.work.dependents(key))
        self.work.toggle(key)
        self.assertIn(key, self.work.project()['authored_ids'])
        self.work.remove(key)
        self.assertIn(link, self.work.records)
        with self.assertRaises(ContractError):
            self.work.project()
        self.work.remove(link)
        self.assertEqual([], self.work.project()['authored_ids'])

    def test_capacity_and_wrong_owner_fail_without_discarding_work(self):
        key = self.claim()
        with self.assertRaises(ContractError):
            self.workspace.candidates(self.episode, 'main', key)
        with self.assertRaises(ContractError):
            self.work.create('observation', {'statement': 'Not confirmed.'})
        self.assertIn(key, self.work.records)
        self.assertEqual(self.original, self.history.manifest())

    def test_history_change_retains_text_and_requires_explicit_source_refresh(self):
        history = replay_example('manual', series=True)
        workspace = PaperWorkspace(ResearchHistory(history.seed, history.commands[:-1]))
        work = workspace.candidates('episode-two', 'main', 'obs-1')
        key = work.create('claim', {'role': 'subclaim', 'statement': 'A new mask remains unmeasured.',
                                  'scope': 'One mask.', 'parent_ids': ['claim-pruning']})
        workspace.update_history(history)
        with self.assertRaisesRegex(ContractError, 'Source changed'):
            work.project()
        self.assertIn(key, work.records)
        work.refresh_source()
        self.assertEqual([key], work.project()['authored_ids'])

    def test_expiring_review_preserves_graph_and_selection(self):
        key = self.claim()
        session = self.workspace.draft(*self.work.owner)
        now = [1000]
        session._clock = lambda: now[0]
        session.edit(text='A manual judgment.', rationale='Only one mask was measured.')
        state = session.state()
        session.prepare_changes({'schema_version': 1, **state['paper'],
            'draft_id': state['draft_id'], 'draft_revision': state['revision'],
            'amendments': list(self.work.records.values()), 'selected_ids': [key]})
        now[0] += 301
        self.assertIsNone(session.get_changes_preview())
        self.assertEqual([key], self.work.project()['authored_ids'])
        self.assertEqual({key}, self.work.selected)

    def test_owner_capacity_never_evicts_previous_candidates(self):
        key = self.claim()
        for ref in ('main', 'alternative'):
            for node in self.workspace.service.query(ref)['nodes']:
                if len(self.workspace._drafts) == 16:
                    with self.assertRaises(ContractError):
                        self.workspace.candidates(self.episode, ref, node['id'])
                    self.assertIn(key, self.work.records)
                    return
                self.workspace.candidates(self.episode, ref, node['id'])
        self.fail('Expected more than 16 distinct source contexts.')

    def test_removed_drafts_never_renumber_or_reuse_another_alias(self):
        first, second = self.claim(), self.claim(statement='An additional condition is untested.')
        alias = self.work.alias(second)
        self.work.remove(first)
        third = self.claim(statement='A third condition.')
        self.assertEqual(alias, self.work.alias(second))
        self.assertNotEqual('D1', self.work.alias(third))
        self.assertEqual(2, len(self.work._aliases))

    def test_editing_an_omitted_candidate_does_not_select_it_again(self):
        key = self.claim()
        self.work.toggle(key)
        record = self.work.records[key]
        record['body']['statement'] = 'Another condition is also untested.'
        self.work.put(record)
        self.assertNotIn(key, self.work.selected)
        self.assertIn(key, self.work.project()['authored_ids'])

    def test_unkeep_and_rekeep_preserve_the_prior_review_choice(self):
        for omitted in (False, True):
            key = self.claim()
            if omitted:
                self.work.toggle(key)
            record = self.work.unkeep(key)
            record['body']['statement'] = 'Resumed unfinished wording.'
            self.work.put(record)
            self.assertEqual(not omitted, key in self.work.selected)

    def test_changed_source_record_needs_exact_comparison_before_refresh(self):
        history = replay_example('manual', series=True)
        earlier = ResearchHistory(history.seed, history.commands[:11])
        workspace = PaperWorkspace(earlier)
        work = workspace.candidates('episode-two', 'main', 'obs-1')
        record = next(c for c in earlier.view('main')['changes'] if c['id'] == 'edge-pruning')
        record['body']['rationale'] = 'My tentative reason.'
        work.put(record)
        workspace.update_history(history)
        with self.assertRaisesRegex(ContractError, 'Compare current source'):
            work.refresh_source()
        changed = work.source_changes()
        self.assertEqual('supports', changed[0]['previous']['edge_type'])
        self.assertEqual('challenges', changed[0]['current']['edge_type'])
        self.assertEqual('supports', changed[0]['candidate']['edge_type'])
        with self.assertRaisesRegex(ContractError, 'Compare current source'):
            work.refresh_source(expected_changes=[])
        work.refresh_source(expected_changes=changed)
        self.assertEqual('My tentative reason.', work.records['edge-pruning']['body']['rationale'])
        work.require_current()


if __name__ == '__main__':
    unittest.main()
