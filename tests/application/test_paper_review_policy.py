from dataclasses import replace
import unittest

from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.review import Judgment, Proposal
from tests.contract.test_paper_changes import amendments
from tests.contract.test_paper_episodes import command, first_episode, second_episode


def ai_draft(episode='episode'):
    return Judgment.start('project', episode).use_proposal(Proposal(
        'proposal-policy', 'project', episode, 'Limit the claim to the observed mask.', 'a' * 64))


def human(episode='episode'):
    return Judgment.start('project', episode).edit(
        'The pruning result is limited to one mask.', 'Only seed 42 was measured; another mask remains unrun.')


class PaperReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')

    def register(self, *, ai_id=None):
        records = amendments(self.history, 'alternative')
        for record in records:
            self.policy.revise_amendment(record, sources=(ai_draft(),) if record['id'] == ai_id else ())
        return [r['id'] for r in records]

    def test_ai_capture_is_quiet_before_a_human_judgment_exists(self):
        ids = self.register(ai_id='edge-pruning')
        assessment = self.policy.capture('alternative', ids, judgment=ai_draft())
        value = decode(assessment.payload)
        self.assertEqual(('capture-draft', 'low', 'none'),
                         (value['action'], value['impact'], value['requirement']))
        self.assertTrue(value['ai_influenced'])
        self.assertEqual([], value['topics'])
        self.assertIsNone(value['rationale'])
        result = self.policy.finish(assessment, disposition='not-required')
        self.assertEqual('none', result['understanding_debt'])
        self.assertFalse(result['authorization_verified'])

    def test_medium_ai_record_reuses_reason_without_teachback_or_debt(self):
        ids = self.register(ai_id='edge-pruning')
        assessment = self.policy.record('alternative', ids, ['edge-pruning'], human())
        value = decode(assessment.payload)
        self.assertEqual(('medium', 'rationale', 'alternative'),
                         (value['impact'], value['requirement'], value['target_ref']))
        self.assertEqual(human().rationale, value['rationale'])
        self.assertTrue(value['ai_influenced'])
        self.assertEqual([], value['topics'])
        self.assertEqual('none', self.policy.finish(assessment, disposition='not-required')['understanding_debt'])
        with self.assertRaises(ContractError):
            self.policy.finish(assessment, disposition='deferred')
        with self.assertRaises(ContractError):
            self.policy.record('alternative', ids, ['edge-pruning'], ai_draft())

    def test_high_ai_merge_binds_topics_and_allows_existing_rationale(self):
        policy = PaperReviewPolicy(first_episode(ai=True, merge=False, close=False), episode_id='episode')
        assessment = policy.merge(['edge-pruning', 'replication'])
        value = decode(assessment.payload)
        self.assertEqual(('high', 'contextual-explanation', 'main'),
                         (value['impact'], value['requirement'], value['target_ref']))
        self.assertEqual(['claim-scope', 'evidence-interpretation', 'followup-experiment'],
                         [t['kind'] for t in value['topics']])
        entries = [{'topic_id': t['id'], 'text': '', 'reuse_rationale': True} for t in value['topics']]
        result = policy.finish(assessment, disposition='answered', entries=entries)
        self.assertEqual(entries, result['entries'])
        self.assertEqual('none', result['understanding_debt'])
        self.assertEqual('opens-if-accepted', policy.finish(assessment, disposition='deferred')['understanding_debt'])
        self.assertEqual('none', policy.finish(assessment, disposition='not-now')['understanding_debt'])
        with self.assertRaises(ContractError):
            policy.finish(assessment, disposition='not-required')

    def test_manual_merge_has_no_ai_explanation_requirement(self):
        before = self.history.manifest()
        assessment = self.policy.merge(['edge-pruning'])
        value = decode(assessment.payload)
        self.assertFalse(value['ai_influenced'])
        self.assertEqual('high', value['impact'])
        self.assertEqual('rationale', value['requirement'])
        self.assertEqual([], value['topics'])
        result = self.policy.finish(assessment, disposition='not-required')
        self.assertEqual('none', result['understanding_debt'])
        self.assertEqual(before, self.history.manifest())

    def test_manual_new_episode_keeps_inherited_ai_without_a_provider(self):
        history, judgment = second_episode(first_episode(ai=True))
        self.assertFalse(judgment.ai_influenced)
        policy = PaperReviewPolicy(history, episode_id='episode-two')
        value = decode(policy.merge(['status-pruning']).payload)
        self.assertTrue(value['inherited_ai'])
        self.assertTrue(value['ai_influenced'])
        self.assertEqual('contextual-explanation', value['requirement'])

    def test_omitted_new_ai_origin_does_not_taint_selected_manual_change(self):
        ids = self.register(ai_id='replication')
        assessment = self.policy.record('alternative', ids, ['edge-pruning'], human())
        value = decode(assessment.payload)
        self.assertIn('replication', value['selection']['omitted'])
        self.assertFalse(value['ai_influenced'])
        self.assertEqual(['claim-pruning-detail', 'edge-pruning'],
                         [r['record_id'] for r in value['lineages']])

    def test_required_amendment_retains_ai_after_manual_revision(self):
        ids = self.register(ai_id='claim-pruning-detail')
        record = amendments(self.history, 'alternative')[0]
        record['body']['scope'] = 'The observation only tests one pruning mask.'
        self.policy.revise_amendment(record)
        value = decode(self.policy.record('alternative', ids, ['edge-pruning'], human()).payload)
        self.assertEqual(['claim-pruning-detail'], value['selection']['required'])
        self.assertTrue(value['ai_influenced'])

    def test_merge_rejects_unrecorded_amendment_origin(self):
        self.register(ai_id='edge-pruning')
        with self.assertRaisesRegex(ContractError, 'record'):
            self.policy.merge(['edge-pruning'])

    def test_registered_record_ai_survives_current_manual_merge_judgment(self):
        record = next(r for r in self.history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        self.policy.revise_amendment(record, sources=(ai_draft(),))
        value = decode(self.policy.merge(['edge-pruning']).payload)
        self.assertFalse(value['inherited_ai'])
        self.assertTrue(value['ai_influenced'])
        self.assertEqual('contextual-explanation', value['requirement'])

    def test_changed_evidence_at_same_heads_invalidates_prepared_review(self):
        assessment = self.policy.merge(['edge-pruning'])
        changed = self.history.append(command(self.history, 'record-evidence-event', {
            'event_id': 'policy-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'The corrected pruning loss is 1.2 percentage points.',
            'value': '1.2', 'rationale': 'Corrected synthetic count.', 'supersedes_id': 'event-1'}))
        self.assertEqual(self.history.heads, changed.heads)
        self.policy.update_source(changed)
        with self.assertRaisesRegex(ContractError, 'stale'):
            self.policy.finish(assessment, disposition='not-required')
        current = self.policy.merge(['edge-pruning'])
        self.assertNotEqual(assessment.digest, current.digest)
        with self.assertRaises(ContractError):
            self.policy.update_source(self.history)

    def test_selection_lineage_and_supplied_topic_changes_require_fresh_assessment(self):
        ids = self.register()
        old = self.policy.record('alternative', ids, ['edge-pruning'], human())
        self.policy.record('alternative', ids, ['replication'], human())
        with self.assertRaises(ContractError):
            self.policy.finish(old, disposition='not-required')
        old = self.policy.record('alternative', ids, ['edge-pruning'], human())
        self.policy.revise_amendment(amendments(self.history, 'alternative')[1], sources=(ai_draft(),))
        with self.assertRaises(ContractError):
            self.policy.finish(old, disposition='not-required')

    def test_answers_must_cover_owned_topics_without_empty_or_extra_claims(self):
        policy = PaperReviewPolicy(first_episode(ai=True, merge=False, close=False), episode_id='episode')
        assessment = policy.merge(['edge-pruning'])
        topics = decode(assessment.payload)['topics']
        good = [{'topic_id': t['id'], 'text': 'The evidence covers one mask.', 'reuse_rationale': False} for t in topics]
        cases = [[], good[:-1], good + [good[0]],
                 [dict(e, topic_id='foreign-topic') for e in good],
                 [dict(e, text='') for e in good], [dict(e, reuse_rationale=1) for e in good]]
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(ContractError):
                policy.finish(assessment, disposition='answered', entries=entries)
        with self.assertRaises(ContractError):
            policy.finish(assessment, disposition='deferred', entries=good)

    def test_wrong_episode_and_unknown_record_fail_without_mutation(self):
        before = self.history.manifest()
        with self.assertRaises(ContractError):
            PaperReviewPolicy(self.history, episode_id='unknown')
        with self.assertRaises(ContractError):
            self.policy.capture('alternative', ['unknown'])
        ids = self.register()
        with self.assertRaises(ContractError):
            self.policy.record('alternative', ids, ['edge-pruning'], human('other-episode'))
        self.assertEqual(before, self.history.manifest())

    def test_empty_capture_and_failed_lineage_edit_preserve_owned_work(self):
        value = decode(self.policy.capture('main', []).payload)
        self.assertEqual('none', value['requirement'])
        self.assertIsNone(value['judgment_digest'])
        ids = self.register(ai_id='edge-pruning')
        old = self.policy.record('alternative', ids, ['edge-pruning'], human())
        bad = amendments(self.history, 'alternative')[1]
        bad['body']['target_id'] = ''
        with self.assertRaises(ContractError):
            self.policy.revise_amendment(bad)
        self.assertEqual('none', self.policy.finish(old, disposition='not-required')['understanding_debt'])

    def test_record_cannot_bypass_the_existing_alternative_source(self):
        policy = PaperReviewPolicy(first_episode(ai=True, merge=False, close=False), episode_id='episode')
        new_claim = {'id': 'new-claim', 'kind': 'claim', 'body': {
            'role': 'main', 'parent_ids': ['thesis'], 'statement': 'A newly drafted manual claim.',
            'scope': 'One synthetic condition.'}}
        policy.revise_amendment(new_claim)
        with self.assertRaises(ContractError):
            policy.record('main', ['new-claim'], ['new-claim'], human())

    def test_modified_assessment_cannot_downgrade_high_review(self):
        policy = PaperReviewPolicy(first_episode(ai=True, merge=False, close=False), episode_id='episode')
        original = policy.merge(['edge-pruning'])
        value = decode(original.payload)
        for updates in ({'requirement': 'rationale'}, {'impact': 'low'}, {'ai_influenced': False},
                        {'topics': []}, {'target_ref': 'alternative'}, {'rules_version': 'future'}):
            changed = {**value, **updates}
            forged = replace(original, payload=canonical_bytes(changed), digest=digest(changed))
            with self.subTest(updates=updates), self.assertRaises(ContractError):
                policy.finish(forged, disposition='not-required')
        self.assertEqual('opens-if-accepted', policy.finish(original, disposition='deferred')['understanding_debt'])

    def test_topics_cover_each_admitted_merge_kind_without_omitted_plan(self):
        history = first_episode(ai=True, merge=False, close=False)
        later, _ = second_episode(first_episode(ai=True))
        for current, key, episode in [(history, key, 'episode') for key in
                ('claim-comparison', 'interpretation', 'edge-pruning', 'replication')] + [(later, 'status-pruning', 'episode-two')]:
            with self.subTest(key=key):
                value = decode(PaperReviewPolicy(current, episode_id=episode).merge([key]).payload)
                self.assertTrue(1 <= len(value['topics']) <= 3)
                if key == 'interpretation':
                    self.assertEqual(['evidence-interpretation'], [t['kind'] for t in value['topics']])
                elif key == 'replication':
                    self.assertNotIn('manuscript-consequence', [t['kind'] for t in value['topics']])
                else:
                    self.assertTrue(all('replication' not in t['node_ids'] for t in value['topics']))

    def test_record_binds_the_same_joined_contributions_as_the_branch_candidate(self):
        history = first_episode(ai=True, merge=False, close=False)
        policy = PaperReviewPolicy(history, episode_id='episode')
        draft = human()
        interpretation = next(r for r in history.view('alternative')['changes'] if r['kind'] == 'interpretation')
        interpretation['body']['statement'] = draft.text
        policy.revise_amendment(interpretation)
        assessment = policy.record('alternative', [interpretation['id']], [interpretation['id']], draft)
        service = PaperService(history)
        view = service.query('alternative')
        candidate, review = service.branch_candidate({
            'schema_version': 1, 'project_id': 'project', 'episode_id': 'episode', 'ref': 'alternative',
            'view_digest': view['digest'], 'draft_id': 'review-policy', 'draft_revision': 0,
            'amendments': [interpretation], 'selected_ids': [interpretation['id']]}, draft,
            operation_id='policy-record', created_at='2026-09-28T00:00:00Z')
        joined = candidate.view('alternative')['judgment']
        self.assertEqual(['human', 'ai', 'human', 'human'], [c['contributor'] for c in joined['history']])
        self.assertEqual(digest(joined), decode(assessment.payload)['judgment_digest'])
        self.assertEqual(joined, review['preview']['provenance']['judgment'])
        self.assertEqual(assessment, policy.record('alternative', [interpretation['id']], [interpretation['id']], draft))

    def test_unchanged_merge_dependencies_are_references_and_cannot_be_selected(self):
        history, _ = second_episode(first_episode(ai=True))
        policy = PaperReviewPolicy(history, episode_id='episode-two')
        record = next(r for r in history.view('alternative')['changes'] if r['id'] == 'claim-pruning-detail')
        policy.revise_amendment(record)
        value = decode(policy.merge(['edge-pruning']).payload)
        self.assertIn('claim-pruning-detail', value['selection']['existing_references'])
        self.assertNotIn('claim-pruning-detail', value['selection']['required'])
        self.assertEqual([], value['lineages'])
        with self.assertRaisesRegex(ContractError, 'select changed records'):
            policy.merge(['claim-pruning-detail', 'edge-pruning'])
        merged = first_episode(ai=True, close=False)
        with self.assertRaisesRegex(ContractError, 'one selected merge'):
            PaperReviewPolicy(merged, episode_id='episode').merge(['edge-pruning'])


if __name__ == '__main__':
    unittest.main()
