from dataclasses import replace
import json
from pathlib import Path
import unittest

from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.paper_commit import COMMIT, commit_schema
from claimbranch.core.research_schema import normalize
from tests.application.test_paper_operation import BINDINGS, NOW
from tests.application.test_paper_review_policy import ai_draft, human
from tests.contract.test_paper_episodes import command, first_episode


class PaperCommitTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(ai=True, merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')

    def seal(self, *, disposition='deferred', selected=('edge-pruning',), entries=()):
        assessment = self.policy.merge(list(selected))
        return self.policy.prepare_operation(assessment, disposition=disposition, entries=entries,
            operation_id='commit-merge', sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)

    def candidate(self, review):
        return self.policy.commit_candidate(review, **BINDINGS)

    def test_deferred_commit_retains_exact_cause_and_forecasts_both_debts(self):
        before = self.history.manifest()
        review = self.seal()
        candidate = self.candidate(review)
        value = decode(candidate.payload)
        self.assertEqual(decode(review.payload), value['review'])
        self.assertEqual(review.digest, value['review_digest'])
        self.assertEqual(dict(self.history.heads), value['review']['operation']['expected_heads'])
        self.assertEqual({**dict(self.history.heads), 'main': 'commit-merge'}, value['resulting_heads'])
        debts = value['debt_openings']
        self.assertEqual(['manuscript', 'understanding'], [d['kind'] for d in debts])
        for debt in debts:
            self.assertEqual('commit-merge', debt['cause_operation_id'])
            self.assertEqual(review.digest, debt['cause_review_digest'])
            self.assertEqual('opens-if-accepted', debt['status'])
            self.assertEqual('commit-merge', debt['cause_main_head'])
            self.assertEqual(self.history.watermark, debt['evidence_watermark'])
        self.assertEqual('anchor', debts[0]['anchor_id'])
        self.assertEqual(BINDINGS['manuscript_digest'], debts[0]['manuscript_digest'])
        self.assertIsNone(debts[1]['anchor_id'])
        self.assertEqual(value['review']['assessment']['topics_digest'], debts[1]['topics_digest'])
        self.assertEqual(2, len({d['id'] for d in debts}))
        self.assertEqual(candidate, self.candidate(review))
        self.assertEqual(candidate, self.policy.restore_commit_candidate(candidate.payload, review, **BINDINGS))
        self.assertEqual(before, self.history.manifest())
        self.assertFalse(candidate.authorization_verified)
        self.assertTrue(candidate.requires_authorization)
        self.assertEqual(0, value['accepted_writes'])
        self.assertEqual(0, value['accepted_debts_created'])

    def test_manual_commit_opens_no_understanding_obligation(self):
        self.history = first_episode(merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        value = decode(self.candidate(self.seal(disposition='not-required')).payload)
        self.assertEqual(['manuscript'], [d['kind'] for d in value['debt_openings']])
        self.assertFalse(value['review']['assessment']['ai_influenced'])

    def test_amendment_only_ai_survives_and_deferral_is_not_flattened(self):
        self.history = first_episode(merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        edge = next(r for r in self.history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        lineage = self.policy.revise_amendment(edge, sources=(ai_draft(),))
        value = decode(self.candidate(self.seal()).payload)
        reviewed = value['review']
        self.assertFalse(reviewed['assessment']['inherited_ai'])
        self.assertTrue(reviewed['assessment']['ai_influenced'])
        self.assertEqual(decode(lineage.payload), reviewed['lineages'][0])
        self.assertTrue(all(c['contributor'] == 'human' for c in reviewed['operation']['effect']['judgment']['history']))
        self.assertEqual('deferred', reviewed['decision']['disposition'])
        self.assertEqual(['manuscript', 'understanding'], [d['kind'] for d in value['debt_openings']])

    def test_explicit_reason_reuse_retains_answers_without_understanding_debt(self):
        assessment = self.policy.merge(['edge-pruning'])
        entries = [{'topic_id': topic['id'], 'text': '', 'reuse_rationale': True}
                   for topic in decode(assessment.payload)['topics']]
        review = self.seal(disposition='answered', entries=entries)
        value = decode(self.candidate(review).payload)
        self.assertEqual(entries, value['review']['decision']['entries'])
        self.assertEqual(['manuscript'], [d['kind'] for d in value['debt_openings']])

    def test_not_now_cannot_create_a_sealed_commit_or_remove_an_obligation(self):
        with self.assertRaises(ContractError):
            self.candidate(self.seal(disposition='not-now'))

    def test_coordinated_schema_valid_forgery_cannot_remove_deferred_understanding(self):
        review = self.seal()
        value = decode(self.candidate(review).payload)
        altered = value['review']
        altered['decision'].update(disposition='not-required', understanding_debt='none')
        altered['operation']['decision_digest'] = digest(altered['decision'])
        altered['operation_digest'] = digest(altered['operation'])
        value['review_digest'] = digest(altered)
        value['debt_openings'] = [d for d in value['debt_openings'] if d['kind'] == 'manuscript']
        debt = value['debt_openings'][0]
        debt['cause_review_digest'] = value['review_digest']
        identity = {key: debt[key] for key in ('kind', 'project_id', 'episode_id',
                                              'cause_operation_id', 'cause_review_digest')}
        debt['id'] = 'debt-' + digest(identity)
        self.assertEqual(value, normalize(value, COMMIT))
        with self.assertRaises(ContractError):
            self.policy.restore_commit_candidate(canonical_bytes(value), review, **BINDINGS)

    def test_record_existing_alternative_does_not_change_main_or_open_debt(self):
        interpretation = next(r for r in self.history.view('alternative')['changes'] if r['kind'] == 'interpretation')
        interpretation['body']['statement'] = human().text
        self.policy.revise_amendment(interpretation)
        assessment = self.policy.record('alternative', ['interpretation'], ['interpretation'], human())
        review = self.policy.prepare_operation(assessment, disposition='not-required', operation_id='commit-record',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        value = decode(self.candidate(review).payload)
        self.assertEqual({**dict(self.history.heads), 'alternative': 'commit-record'}, value['resulting_heads'])
        self.assertEqual([], value['debt_openings'])
        self.assertEqual(['interpretation'], [r['id'] for r in value['review']['operation']['effect']['changes']])

    def test_first_record_forecasts_new_alternative_in_one_plan(self):
        history = self.history
        branch_index = next(i for i, raw in enumerate(history.commands)
                            if decode(raw)['operation_type'] == 'create-reasoning-branch')
        self.history = type(history)(history.seed, history.commands[:branch_index])
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        record = {'id': 'fresh-interpretation', 'kind': 'interpretation',
                  'body': {'statement': human().text, 'observation_ids': ['obs-1']}}
        self.policy.revise_amendment(record)
        assessment = self.policy.record('main', [record['id']], [record['id']], human())
        review = self.policy.prepare_operation(assessment, disposition='not-required', operation_id='first-record',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        value = decode(self.candidate(review).payload)
        self.assertEqual('first-record-branch', value['review']['operation']['effect']['branch_operation_id'])
        self.assertEqual({**dict(self.history.heads), 'alternative': 'first-record'}, value['resulting_heads'])
        self.assertEqual([], value['debt_openings'])

    def test_changed_context_and_expired_review_cannot_restore_commit(self):
        review = self.seal()
        candidate = self.candidate(review)
        for updates in ({'manuscript_digest': 'c' * 64}, {'session_nonce': 'other'}, {'now': NOW + 300}):
            with self.subTest(updates=updates), self.assertRaises(ContractError):
                self.policy.restore_commit_candidate(candidate.payload, review, **{**BINDINGS, **updates})
        corrected = self.history.append(command(self.history, 'record-evidence-event', {
            'event_id': 'commit-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy', 'action': 'correct',
            'statement': 'The corrected loss is 1.2 percentage points.', 'value': '1.2',
            'rationale': 'Correct synthetic count.', 'supersedes_id': 'event-1'}))
        self.policy.update_source(corrected)
        with self.assertRaises(ContractError):
            self.policy.restore_commit_candidate(candidate.payload, review, **BINDINGS)

    def test_restore_cannot_install_a_seal_or_override_newer_selection(self):
        review = self.seal()
        candidate = self.candidate(review)
        fresh = PaperReviewPolicy(self.history, episode_id='episode')
        fresh.restore_operation(review.payload, **BINDINGS)
        with self.assertRaises(ContractError):
            fresh.restore_commit_candidate(candidate.payload, review, **BINDINGS)
        self.policy.merge(['replication'])
        with self.assertRaises(ContractError):
            self.policy.restore_commit_candidate(candidate.payload, review, **BINDINGS)

    def test_forged_effect_debt_origin_heads_and_authority_are_rejected(self):
        review = self.seal()
        candidate = self.candidate(review)
        changes = [lambda v: v['resulting_heads'].update(main='other'),
                   lambda v: v['debt_openings'].clear(),
                   lambda v: v['debt_openings'][1].update(cause_review_digest='a' * 64),
                   lambda v: v['debt_openings'][1].update(topics_digest='a' * 64),
                   lambda v: v['review']['lineages'].append({}),
                   lambda v: v.update(authorization_verified=True),
                   lambda v: v.update(actor='human')]
        for change in changes:
            value = decode(candidate.payload)
            change(value)
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.policy.restore_commit_candidate(canonical_bytes(value), review, **BINDINGS)
        with self.assertRaises(ContractError):
            self.candidate(replace(review, digest='a' * 64))

    def test_generated_schema_matches_and_noncanonical_import_is_refused(self):
        expected = json.loads((Path(__file__).resolve().parents[2] / 'schemas/paper-commit-candidate-v1.json').read_text())
        self.assertEqual(expected, commit_schema())
        review = self.seal()
        candidate = self.candidate(review)
        raw = json.dumps(decode(candidate.payload), ensure_ascii=False).encode()
        with self.assertRaises(ContractError):
            self.policy.restore_commit_candidate(raw, review, **BINDINGS)


if __name__ == '__main__':
    unittest.main()
