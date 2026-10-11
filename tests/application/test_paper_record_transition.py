from dataclasses import replace
import json
from pathlib import Path
import unittest

from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.paper_record_transition import TRANSITION, transition_schema
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import normalize
from tests.application.test_paper_operation import BINDINGS, NOW
from tests.application.test_paper_review_policy import ai_draft, human
from tests.contract.test_paper_episodes import first_episode


class PaperRecordTransitionTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(merge=False, close=False)
        self.policy = PaperReviewPolicy(self.history, episode_id='episode')

    def seal(self, *, first=False, ai=False):
        if first:
            index = next(i for i, raw in enumerate(self.history.commands)
                         if decode(raw)['operation_type'] == 'create-reasoning-branch')
            self.history = ResearchHistory(self.history.seed, self.history.commands[:index])
            self.policy = PaperReviewPolicy(self.history, episode_id='episode')
        record = {'id': 'fresh-interpretation' if first else 'interpretation',
                  'kind': 'interpretation', 'body': {'statement': human().text, 'observation_ids': ['obs-1']}}
        self.policy.revise_amendment(record, sources=(ai_draft(),) if ai else ())
        assessment = self.policy.record('main' if first else 'alternative', [record['id']], [record['id']], human())
        return self.policy.prepare_operation(assessment, disposition='not-required',
            operation_id='record-transition', sealed_at=NOW, expires_at=NOW + 300, bind_origins=True, **BINDINGS)

    def apply(self, review):
        return self.policy.record_transition(review, **BINDINGS)

    def test_record_replays_exact_effect_without_changing_evidence_main_or_source(self):
        before = self.history.manifest()
        review = self.seal()
        result = self.apply(review)
        value = decode(result.payload)
        self.assertEqual(decode(review.payload), value['review'])
        self.assertEqual(1, len(value['commands']))
        self.assertEqual('record-interpretation', value['commands'][0]['operation_type'])
        self.assertEqual(dict(self.history.heads)['main'], dict(result.history.heads)['main'])
        self.assertEqual('record-transition', dict(result.history.heads)['alternative'])
        self.assertEqual(self.history.watermark, result.history.watermark)
        self.assertEqual(self.history.view('main'), result.history.view('main'))
        self.assertEqual(human().text, result.history.view('alternative')['judgment']['text'])
        self.assertEqual(before, self.history.manifest())
        self.assertEqual(result.history.manifest(), ResearchHistory.replay(
            result.history.seed, result.history.commands).manifest())
        self.assertFalse(result.authorization_verified)
        self.assertEqual(0, value['accepted_writes'])
        self.assertEqual(0, value['accepted_debts_created'])
        self.assertEqual(result, self.apply(review))
        self.assertEqual(result, self.policy.restore_record_transition(result.payload, review, **BINDINGS))

    def test_first_record_creates_branch_and_interpretation_as_one_replay(self):
        review = self.seal(first=True)
        result = self.apply(review)
        commands = decode(result.payload)['commands']
        self.assertEqual(['create-reasoning-branch', 'record-interpretation'],
                         [c['operation_type'] for c in commands])
        self.assertEqual('record-transition-branch', commands[0]['id'])
        self.assertEqual({**dict(self.history.heads), 'alternative': commands[0]['id']}, commands[1]['expected_heads'])
        self.assertEqual('record-transition', dict(result.history.heads)['alternative'])
        self.assertEqual(dict(self.history.heads)['main'], dict(result.history.heads)['main'])

    def test_amendment_only_ai_remains_in_next_merge_without_inventing_judgment_ai(self):
        review = self.seal(ai=True)
        result = self.apply(review)
        self.assertTrue(result.origins[0].ai_influenced)
        self.assertTrue(all(c['contributor'] == 'human'
                            for c in result.history.view('alternative')['judgment']['history']))
        reopened = PaperReviewPolicy.from_record_transition(result, expected_review_digest=review.digest)
        assessment = reopened.merge(['interpretation'])
        self.assertTrue(decode(assessment.payload)['ai_influenced'])
        with self.assertRaises(ContractError):
            reopened.prepare_operation(assessment, disposition='not-required', operation_id='merge-transition',
                sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        merged_review = reopened.prepare_operation(assessment, disposition='deferred', operation_id='merge-transition',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.assertEqual('opens-if-accepted', decode(merged_review.payload)['decision']['understanding_debt'])

    def test_omitted_draft_origins_stay_available_but_do_not_enter_recorded_changes(self):
        omitted = {'id': 'unselected-claim', 'kind': 'claim', 'body': {
            'role': 'main', 'statement': 'An unselected alternative.', 'scope': 'Not measured.', 'parent_ids': ['thesis']}}
        self.policy.revise_amendment(omitted, sources=(ai_draft(),))
        result = self.apply(self.seal())
        self.assertEqual({'unselected-claim', 'interpretation'}, {o.amendment['id'] for o in result.origins})
        self.assertNotIn('unselected-claim', {r['id'] for r in result.history.view('alternative')['changes']})
        self.assertFalse(decode(result.payload)['review']['assessment']['ai_influenced'])

    def test_merge_cannot_be_translated_into_a_legacy_transition(self):
        assessment = self.policy.merge(['edge-pruning'])
        review = self.policy.prepare_operation(assessment, disposition='not-required', operation_id='merge-transition',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        with self.assertRaises(ContractError):
            self.apply(review)

    def test_expiry_changed_source_and_no_current_seal_refuse_replay(self):
        review = self.seal()
        result = self.apply(review)
        fresh = PaperReviewPolicy.from_work_sources(self.history, episode_id='episode', origins=result.origins)
        with self.assertRaises(ContractError):
            fresh.restore_record_transition(result.payload, review, **BINDINGS)
        for changes in [{'now': NOW + 300}, {'manuscript_digest': 'c' * 64}, {'session_nonce': 'other'}]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.policy.record_transition(review, **{**BINDINGS, **changes})
        self.policy.update_source(result.history)
        with self.assertRaises(ContractError):
            self.apply(review)

    def test_coordinated_command_and_digest_forgery_is_rejected(self):
        review = self.seal()
        result = self.apply(review)
        value = decode(result.payload)
        value['commands'][0]['id'] = 'forged-record'
        forged = self.history.append(value['commands'][0])
        import hashlib
        value['result_history_digest'] = hashlib.sha256(forged.manifest()).hexdigest()
        self.assertEqual(value, normalize(value, TRANSITION))
        with self.assertRaises(ContractError):
            self.policy.restore_record_transition(canonical_bytes(value), review, **BINDINGS)

    def test_fresh_process_rederives_from_independent_sources_without_reviving_seal(self):
        import subprocess
        import sys
        import hashlib
        review = self.seal(first=True, ai=True)
        result = self.apply(review)
        source = canonical_bytes({'seed': decode(self.history.seed),
            'commands': [decode(raw) for raw in self.history.commands],
            'origins': [decode(origin.payload) for origin in result.origins],
            'transition': decode(result.payload), 'bindings': BINDINGS})
        code = '''
import sys
from claimbranch.core.canonical import canonical_bytes, decode, ContractError
from claimbranch.core.paper_changes import AmendmentLineage
from claimbranch.core.research_history import ResearchHistory
from claimbranch.application.paper_review_policy import PaperReviewPolicy, _judgment
data = decode(sys.stdin.buffer.read())
history = ResearchHistory.replay(canonical_bytes(data['seed']), tuple(canonical_bytes(c) for c in data['commands']))
origins = tuple(AmendmentLineage.restore(canonical_bytes(o)) for o in data['origins'])
policy = PaperReviewPolicy.from_work_sources(history, episode_id='episode', origins=origins)
value = data['transition']['review']
old = policy.restore_operation(canonical_bytes(value), **data['bindings'])
try:
    policy.record_transition(old, **data['bindings'])
except ContractError:
    pass
else:
    raise AssertionError('replay restored a current seal')
prep = value['preparation']
assessment = policy.record(prep['ref'], prep['amendment_ids'], prep['selected_ids'], _judgment(prep['judgment']))
fresh = policy.prepare_operation(assessment, disposition=value['decision']['disposition'],
    entries=value['decision']['entries'], operation_id=value['operation']['id'],
    sealed_at=value['sealed_at'], expires_at=value['expires_at'], bind_origins=True, **data['bindings'])
result = policy.restore_record_transition(canonical_bytes(data['transition']), fresh, **data['bindings'])
sys.stdout.buffer.write(result.history.manifest())
'''
        child = subprocess.run([sys.executable, '-c', code], input=source, capture_output=True,
                               cwd=Path(__file__).resolve().parents[2], timeout=30)
        self.assertEqual(0, child.returncode, child.stderr.decode())
        self.assertEqual(result.history.manifest(), child.stdout)
        self.assertEqual(decode(result.payload)['result_history_digest'], hashlib.sha256(child.stdout).hexdigest())

    def test_generated_closed_schema_matches(self):
        path = Path(__file__).resolve().parents[2] / 'schemas/paper-record-transition-v1.json'
        self.assertEqual(transition_schema(), json.loads(path.read_text()))

    def test_omitted_draft_edits_after_sealing_do_not_change_retry_snapshot(self):
        review = self.seal(ai=True)
        original = self.apply(review)
        omitted = {'id': 'later-draft', 'kind': 'claim', 'body': {
            'role': 'main', 'statement': 'Written after the seal.', 'scope': 'Unreviewed.', 'parent_ids': ['thesis']}}
        self.policy.revise_amendment(omitted, sources=(ai_draft(),))
        self.assertEqual(original, self.apply(review))
        self.assertEqual(original, self.policy.restore_record_transition(original.payload, review, **BINDINGS))
        self.assertIn('later-draft', {o.amendment['id'] for o in self.policy.work_sources()[2]})

    def test_incomplete_or_substituted_bound_origins_cannot_continue(self):
        from claimbranch.core.paper_changes import AmendmentLineage
        from claimbranch.core.canonical import digest
        result = self.apply(self.seal(ai=True))
        fake = AmendmentLineage.start('project', 'episode', result.origins[0].amendment)
        for origins in [(), (fake,)]:
            with self.subTest(origins=origins):
                value = decode(result.payload)
                value['origins'] = [decode(o.payload) for o in origins]
                forged = replace(result, payload=canonical_bytes(value), digest=digest(value), origins=origins)
                with self.assertRaises(ContractError):
                    PaperReviewPolicy.from_record_transition(forged,
                        expected_review_digest=decode(result.payload)['review_digest'])

    def test_transition_budget_checked_before_installing_new_seal(self):
        review = self.seal()
        original = self.apply(review)
        for i in range(32):
            self.policy.revise_amendment({'id': 'large-omitted-' + str(i), 'kind': 'claim', 'body': {
                'role': 'main', 'statement': 'x' * 10000, 'scope': 'Unselected.', 'parent_ids': ['thesis']}})
        with self.assertRaisesRegex(ContractError, 'canonical JSON byte limit exceeded'):
            self.seal()
        self.assertEqual(original, self.apply(review))
        assessment = self.policy.merge(['edge-pruning'])
        merged = self.policy.prepare_operation(assessment, disposition='not-required', operation_id='budget-merge',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.assertEqual('claimbranch.paper-operation-review/v1', decode(merged.payload)['schema'])

    def test_unselected_ai_origin_is_bound_even_when_review_science_is_manual(self):
        from claimbranch.core.canonical import digest
        omitted = {'id': 'omitted-ai', 'kind': 'claim', 'body': {
            'role': 'main', 'statement': 'An unselected suggestion.', 'scope': 'Not measured.', 'parent_ids': ['thesis']}}
        self.policy.revise_amendment(omitted, sources=(ai_draft(),))
        result = self.apply(self.seal())
        self.assertFalse(decode(result.payload)['review']['assessment']['ai_influenced'])
        kept = tuple(o for o in result.origins if o.amendment['id'] != 'omitted-ai')
        value = decode(result.payload)
        value['origins'] = [decode(o.payload) for o in kept]
        forged = replace(result, payload=canonical_bytes(value), digest=digest(value), origins=kept)
        with self.assertRaises(ContractError):
            PaperReviewPolicy.from_record_transition(forged,
                expected_review_digest=decode(result.payload)['review_digest'])
        value['review']['origin_registry_digest'] = digest(value['origins'])
        value['review_digest'] = digest(value['review'])
        fully_rehashed = replace(result, payload=canonical_bytes(value), digest=digest(value), origins=kept)
        with self.assertRaisesRegex(ContractError, 'independently retained review'):
            PaperReviewPolicy.from_record_transition(fully_rehashed,
                expected_review_digest=decode(result.payload)['review_digest'])

    def test_legacy_review_cannot_supply_bound_transition(self):
        review = self.seal()
        value = decode(review.payload)
        descriptor = value['preparation']
        assessment = self.policy.record(descriptor['ref'], descriptor['amendment_ids'],
                                         descriptor['selected_ids'], human())
        legacy = self.policy.prepare_operation(assessment, disposition='not-required', operation_id='legacy-record',
            sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.assertEqual('claimbranch.paper-operation-review/v1', decode(legacy.payload)['schema'])
        with self.assertRaises(ContractError):
            self.apply(legacy)

    def test_v2_registry_commitment_is_closed_and_old_review_reader_refuses_it(self):
        from claimbranch.core.canonical import digest
        from claimbranch.core.paper_operation import review_schema
        result = self.apply(self.seal())
        value = decode(result.payload)
        reviewed = value['review']
        self.assertEqual(digest(value['origins']), reviewed['origin_registry_digest'])
        self.assertEqual(reviewed, normalize(reviewed, review_schema(2)))
        with self.assertRaises(ContractError):
            normalize(reviewed, review_schema())
