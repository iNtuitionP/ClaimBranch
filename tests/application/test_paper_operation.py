from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
import unicodedata

from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.paper_operation import PaperOperationReview, operation_schema, review_schema
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import normalize
from claimbranch.core.review import Judgment, Proposal
from tests.application.test_paper_review_policy import ai_draft, human
from tests.contract.test_paper_changes import amendments
from tests.contract.test_paper_episodes import command, first_episode, second_episode


NOW = 1_800_000_000
BINDINGS = dict(manuscript_digest='b' * 64, session_nonce='operation-session', now=NOW)


class PaperOperationTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(ai=True, merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')

    def prepare(self, assessment=None, **overrides):
        if assessment is None:
            assessment = self.policy.merge(['edge-pruning'])
        args = dict(disposition='deferred', entries=[], operation_id='reviewed-merge',
                    sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        args.update(overrides)
        return self.policy.prepare_operation(assessment, **args)

    def test_exact_merge_round_trip_preserves_sources_topics_and_conditional_debt(self):
        before = self.history.manifest()
        review = self.prepare()
        value = decode(review.payload)
        operation = value['operation']
        self.assertEqual('apply-selected-merge', operation['action'])
        self.assertEqual(['edge-pruning'], operation['effect']['selected_ids'])
        self.assertEqual(dict(self.history.heads), operation['expected_heads'])
        self.assertEqual(self.history.watermark, operation['evidence_watermark'])
        self.assertEqual(['human', 'ai', 'human'],
                         [c['contributor'] for c in value['source_judgments'][0]['history']])
        self.assertEqual('opens-if-accepted', value['decision']['understanding_debt'])
        self.assertTrue(value['assessment']['topics'])
        self.assertEqual(review, self.policy.restore_operation(review.payload, **BINDINGS))
        candidate = self.policy.operation_candidate(review, **BINDINGS)
        self.assertEqual(operation, decode(candidate.payload))
        self.assertEqual(review.digest, candidate.review_digest)
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)
        self.assertEqual(before, self.history.manifest())

    def test_record_effect_contains_only_reviewed_changes_and_actual_joined_judgment(self):
        records = amendments(self.history, 'alternative')
        interpretation = next(r for r in self.history.view('alternative')['changes'] if r['kind'] == 'interpretation')
        interpretation['body']['statement'] = human().text
        for record in [*records, interpretation]:
            self.policy.revise_amendment(record, sources=(ai_draft(),) if record['id'] == 'edge-pruning' else ())
        assessment = self.policy.record('alternative', [r['id'] for r in [*records, interpretation]],
                                        ['interpretation', 'edge-pruning'], human())
        review = self.prepare(assessment, disposition='not-required', operation_id='record-new-judgment')
        value = decode(review.payload)
        effect = value['operation']['effect']
        self.assertEqual(['claim-pruning-detail', 'edge-pruning', 'interpretation'], [r['id'] for r in effect['changes']])
        self.assertIsNone(effect['branch_operation_id'])
        self.assertEqual(['human', 'ai', 'human', 'human'], [c['contributor'] for c in effect['judgment']['history']])
        self.assertEqual('none', value['decision']['understanding_debt'])
        self.assertEqual(3, len(value['lineages']))
        self.assertEqual('proposal-policy', value['lineages'][1]['revisions'][0]['sources'][0]['history'][0]['proposal_id'])

    def test_ai_only_in_amendment_lineage_is_not_flattened_into_legacy_merge(self):
        self.history = first_episode(merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        edge = next(r for r in self.history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        origin = self.policy.revise_amendment(edge, sources=(ai_draft(),))
        review = self.prepare()
        value = decode(review.payload)
        self.assertTrue(value['assessment']['ai_influenced'])
        self.assertFalse(value['assessment']['inherited_ai'])
        self.assertEqual(decode(origin.payload), value['lineages'][0])
        self.assertEqual('deferred', value['decision']['disposition'])
        self.assertEqual('opens-if-accepted', value['decision']['understanding_debt'])
        fresh = PaperReviewPolicy(self.history, episode_id='episode')
        with self.assertRaises(ContractError):
            fresh.restore_operation(review.payload, **BINDINGS)
        self.assertEqual(review, self.policy.restore_operation(review.payload, **BINDINGS))

    def test_answer_reuses_reason_and_manual_merge_needs_no_ai_answer(self):
        assessment = self.policy.merge(['edge-pruning'])
        entries = [{'topic_id': t['id'], 'text': '', 'reuse_rationale': True}
                   for t in decode(assessment.payload)['topics']]
        reviewed = self.prepare(assessment, disposition='answered', entries=entries)
        self.assertEqual(entries, decode(reviewed.payload)['decision']['entries'])
        self.assertEqual('none', decode(reviewed.payload)['decision']['understanding_debt'])
        self.policy = PaperReviewPolicy(first_episode(merge=False, close=False), episode_id='episode')
        review = self.prepare(disposition='not-required')
        self.assertFalse(decode(review.payload)['assessment']['ai_influenced'])

    def test_quiet_capture_and_not_now_cannot_become_operation_requests(self):
        assessment = self.policy.capture('main', [])
        with self.assertRaises(ContractError):
            self.prepare(assessment, disposition='not-required')
        with self.assertRaises(ContractError):
            self.prepare(disposition='not-now')

    def test_changed_same_head_evidence_file_session_and_expiry_refuse_reuse(self):
        review = self.prepare()
        for updates in ({'manuscript_digest': 'c' * 64}, {'session_nonce': 'different-session'},
                        {'now': NOW - 1}, {'now': NOW + 300}):
            with self.subTest(updates=updates), self.assertRaises(ContractError):
                self.policy.operation_candidate(review, **{**BINDINGS, **updates})
        self.policy.operation_candidate(review, **{**BINDINGS, 'now': NOW + 299})
        changed = self.history.append(command(self.history, 'record-evidence-event', {
            'event_id': 'operation-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy', 'action': 'correct',
            'statement': 'The corrected loss is 1.2 percentage points.', 'value': '1.2',
            'rationale': 'Correct synthetic count.', 'supersedes_id': 'event-1'}))
        self.assertEqual(self.history.heads, changed.heads)
        self.policy.update_source(changed)
        with self.assertRaises(ContractError):
            self.policy.restore_operation(review.payload, **BINDINGS)

    def test_restore_does_not_replace_a_current_draft_assessment(self):
        review = self.prepare()
        newer = self.policy.merge(['replication'])
        self.assertEqual(review, self.policy.restore_operation(review.payload, **BINDINGS))
        self.policy.finish(newer, disposition='deferred')

    def test_final_candidate_requires_the_current_owned_review_scope(self):
        review = self.prepare()
        self.policy.merge(['replication'])
        with self.assertRaises(ContractError):
            self.policy.operation_candidate(review, **BINDINGS)
        reopened = PaperReviewPolicy(self.history, episode_id='episode')
        self.assertEqual(review, reopened.restore_operation(review.payload, **BINDINGS))
        with self.assertRaises(ContractError):
            reopened.operation_candidate(review, **BINDINGS)
        assessment = reopened.merge(['edge-pruning'])
        with self.assertRaises(ContractError):
            reopened.operation_candidate(review, **BINDINGS)
        renewed = reopened.prepare_operation(assessment, disposition='deferred', operation_id='reviewed-merge',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.assertEqual(review, renewed)
        self.assertTrue(reopened.operation_candidate(review, **BINDINGS).requires_authorization)

    def test_not_now_and_changed_explanation_revoke_a_prepared_operation(self):
        assessment = self.policy.merge(['edge-pruning'])
        for disposition in ('not-now', 'answered'):
            review = self.prepare(assessment)
            entries = ([{'topic_id': t['id'], 'text': '', 'reuse_rationale': True}
                        for t in decode(assessment.payload)['topics']] if disposition == 'answered' else [])
            self.policy.finish(assessment, disposition=disposition, entries=entries)
            with self.subTest(disposition=disposition), self.assertRaises(ContractError):
                self.policy.operation_candidate(review, **BINDINGS)

    def test_replacement_seal_invalidates_old_metadata_and_failed_prepare_keeps_current(self):
        assessment = self.policy.merge(['edge-pruning'])
        first = self.prepare(assessment)
        current = self.prepare(assessment, operation_id='replacement-merge', parent_review_digest=first.digest)
        with self.assertRaises(ContractError):
            self.policy.operation_candidate(first, **BINDINGS)
        with self.assertRaises(ContractError):
            self.prepare(assessment, session_nonce='invalid nonce')
        self.assertTrue(self.policy.operation_candidate(current, **BINDINGS).requires_authorization)
        self.policy.finish(assessment, disposition='deferred')
        self.assertTrue(self.policy.operation_candidate(current, **BINDINGS).requires_authorization)

    def test_other_valid_decision_cannot_replace_the_owners_current_seal(self):
        review = self.prepare()
        other = PaperReviewPolicy(self.history, episode_id='episode')
        assessment = other.merge(['edge-pruning'])
        entries = [{'topic_id': t['id'], 'text': '', 'reuse_rationale': True}
                   for t in decode(assessment.payload)['topics']]
        alternative = other.prepare_operation(assessment, disposition='answered', entries=entries,
            operation_id='reviewed-merge', sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.assertEqual(alternative, self.policy.restore_operation(alternative.payload, **BINDINGS))
        with self.assertRaises(ContractError):
            self.policy.operation_candidate(alternative, **BINDINGS)
        self.assertTrue(self.policy.operation_candidate(review, **BINDINGS).requires_authorization)

    def test_invalid_selection_preserves_the_explicit_previous_owned_scope(self):
        self.history, _ = second_episode(first_episode(ai=True))
        self.policy = PaperReviewPolicy(self.history, episode_id='episode-two')
        review = self.prepare()
        with self.assertRaises(ContractError):
            self.policy.merge(['claim-pruning-detail', 'edge-pruning'])
        self.assertTrue(self.policy.operation_candidate(review, **BINDINGS).requires_authorization)

    def test_ai_last_text_can_reuse_reason_without_inventing_a_human_edit(self):
        draft = human().use_proposal(Proposal('wording-help', 'project', 'episode', 'Keep the pruning claim narrow.', 'e' * 64))
        interpretation = next(r for r in self.history.view('alternative')['changes'] if r['kind'] == 'interpretation')
        interpretation['body']['statement'] = draft.text
        self.policy.revise_amendment(interpretation)
        assessment = self.policy.record('alternative', ['interpretation'], ['interpretation'], draft)
        review = self.prepare(assessment, disposition='not-required')
        value = decode(review.payload)
        self.assertEqual('ai', value['operation']['effect']['judgment']['history'][-1]['contributor'])
        self.assertEqual(human().rationale, value['assessment']['rationale'])
        candidate = self.policy.operation_candidate(review, **BINDINGS)
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)

    def test_non_nfc_source_review_is_not_silently_rewritten_on_restore(self):
        draft = Judgment.start('project', 'episode').edit('Café 조건의 관찰.', '동일한 측정 범위를 유지한다.')
        interpretation = next(r for r in self.history.view('alternative')['changes'] if r['kind'] == 'interpretation')
        interpretation['body']['statement'] = draft.text
        self.policy.revise_amendment(interpretation)
        assessment = self.policy.record('alternative', ['interpretation'], ['interpretation'], draft)
        review = self.prepare(assessment, disposition='not-required')
        raw = unicodedata.normalize('NFD', review.payload.decode()).encode()
        self.assertNotEqual(raw, review.payload)
        with self.assertRaises(ContractError):
            self.policy.restore_operation(raw, **BINDINGS)

    def test_operation_cannot_reserve_a_known_unselected_draft_identity(self):
        self.policy.revise_amendment({'id': 'unselected-claim', 'kind': 'claim', 'body': {
            'role': 'main', 'parent_ids': ['thesis'], 'statement': 'An unfinished comparison.', 'scope': 'One condition.'}})
        with self.assertRaises(ContractError):
            self.prepare(operation_id='unselected-claim')

    def test_first_record_carries_required_branch_creation_and_human_authorship(self):
        self.history = ResearchHistory(self.history.seed, self.history.commands[:-2])
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        record = {'id': 'first-reading', 'kind': 'interpretation',
                  'body': {'statement': human().text, 'observation_ids': ['obs-1']}}
        self.policy.revise_amendment(record)
        assessment = self.policy.record('main', ['first-reading'], ['first-reading'], human())
        review = self.prepare(assessment, disposition='not-required', operation_id='first-record')
        effect = decode(review.payload)['operation']['effect']
        self.assertEqual('first-record-branch', effect['branch_operation_id'])
        self.assertEqual([record], effect['changes'])
        self.assertEqual(['human'], [c['contributor'] for c in effect['judgment']['history']])
        self.assertNotIn('alternative', dict(self.history.heads))
        self.policy.operation_candidate(review, **BINDINGS)
        self.policy.revise_amendment({'id': 'alias-branch', 'kind': 'claim', 'body': {
            'role': 'main', 'parent_ids': ['thesis'], 'statement': 'An unfinished comparison.', 'scope': 'One condition.'}})
        for key in ('alias', 'x' * 128, 'run-accuracy'):
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.prepare(assessment, disposition='not-required', operation_id=key)

    def test_record_preview_without_matching_interpretation_cannot_be_sealed(self):
        records = amendments(self.history, 'alternative')
        for record in records:
            self.policy.revise_amendment(record)
        assessment = self.policy.record('alternative', [r['id'] for r in records], ['edge-pruning'], human())
        with self.assertRaisesRegex(ContractError, 'judgment text'):
            self.prepare(assessment, disposition='not-required')

    def test_changed_origins_fail_without_importing_or_discarding_their_revisions(self):
        record = next(r for r in self.history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        self.policy.revise_amendment(record, sources=(ai_draft(),))
        review = self.prepare()
        self.policy.revise_amendment(record, sources=(human(),))
        with self.assertRaises(ContractError):
            self.policy.restore_operation(review.payload, **BINDINGS)
        latest = self.prepare()
        self.assertEqual(2, len(decode(latest.payload)['lineages'][0]['revisions']))
        self.assertTrue(decode(latest.payload)['assessment']['ai_influenced'])

    def test_total_review_limit_refuses_to_truncate_individually_valid_lineages(self):
        source = Judgment.start('project', 'episode').use_proposal(Proposal(
            'large-proposal', 'project', 'episode', 'x' * 16000, 'a' * 64))
        records = [r for r in self.history.view('alternative')['changes'] if r['id'] in
                   ('edge-pruning', 'claim-pruning-detail')]
        for record in records:
            for _ in range(5):
                self.policy.revise_amendment(record, sources=(source,))
        assessment = self.policy.merge(['edge-pruning'])
        with self.assertRaises(ContractError):
            self.prepare(assessment)
        self.assertEqual(2, len(decode(assessment.payload)['lineages']))

    def test_parent_is_only_a_revision_reference_and_invalid_metadata_is_rejected(self):
        review = self.prepare(parent_review_digest='d' * 64)
        self.assertEqual('d' * 64, decode(review.payload)['parent_review_digest'])
        self.assertFalse(self.policy.operation_candidate(review, **BINDINGS).authorization_verified)
        for updates in ({'parent_review_digest': 'not-a-hash'}, {'manuscript_digest': 'bad'},
                        {'sealed_at': 0, 'expires_at': 300, 'now': 0}):
            with self.subTest(updates=updates), self.assertRaises(ContractError):
                self.prepare(**updates)

    def test_supplied_hashes_do_not_validate_modified_operation_review_or_lineage(self):
        review = self.prepare()
        base = decode(review.payload)
        cases = []
        for key, replacement in [('operation', {**base['operation'], 'action': 'record-evidence-event'}),
                                 ('assessment', {**base['assessment'], 'ai_influenced': False}),
                                 ('decision', {**base['decision'], 'understanding_debt': 'none'}),
                                 ('source_judgments', []), ('authorization_verified', True)]:
            cases.append({**base, key: replacement})
        changed = deepcopy(base)
        changed['operation']['effect']['selected_ids'] = ['replication']
        changed['operation_digest'] = digest(changed['operation'])
        cases.append(changed)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.policy.restore_operation(canonical_bytes(value), **BINDINGS)
        for forged in (replace(review, digest='f' * 64), replace(review, payload=canonical_bytes(cases[-1]))):
            with self.assertRaises(ContractError):
                self.policy.operation_candidate(forged, **BINDINGS)

    def test_canonical_version_size_and_legacy_reader_boundaries(self):
        review = self.prepare()
        value = decode(review.payload)
        for raw in (json.dumps(value).encode(), b' ' * 262145,
                    canonical_bytes({**value, 'schema': 'claimbranch.paper-operation-review/v2'}),
                    self.history.commands[-1]):
            with self.assertRaises(ContractError):
                self.policy.restore_operation(raw, **BINDINGS)
        with self.assertRaises(ContractError):
            self.history.append(value['operation'])
        other = ResearchHistory.start_paper_series('other', 'Other paper', 'thesis', 'Other claim', 'anchor')
        wrong = PaperReviewPolicy(other.append({'schema_version': 3, 'id': 'open', 'project_id': 'other', 'episode_id': 'episode',
                     'created_at': '2026-09-28T00:00:00Z', 'operation_type': 'open-episode',
                     'expected_heads': dict(other.heads), 'evidence_watermark': 0,
                     'payload': {'title': 'Other', 'question': 'Other?'}}), episode_id='episode')
        with self.assertRaises(ContractError):
            wrong.restore_operation(review.payload, **BINDINGS)

    def test_operation_identity_and_seal_lifetime_are_checked_before_request(self):
        for key in ('episode', 'edge-pruning', decode(self.history.commands[-1])['id']):
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.prepare(operation_id=key)
        for updates in ({'expires_at': NOW + 301}, {'expires_at': NOW}, {'sealed_at': NOW + 1},
                        {'sealed_at': True}, {'session_nonce': 'bad nonce'}):
            with self.subTest(updates=updates), self.assertRaises(ContractError):
                self.prepare(**updates)

    def test_generated_schemas_are_current_and_review_shape_is_closed(self):
        root = Path(__file__).resolve().parents[2] / 'schemas'
        for name, schema in (('paper-operation-v1.json', operation_schema()), ('paper-operation-review-v1.json', review_schema())):
            self.assertEqual(schema, json.loads((root / name).read_text()))
        value = decode(self.prepare().payload)
        self.assertEqual(value, normalize(value, review_schema()))


if __name__ == '__main__':
    unittest.main()
