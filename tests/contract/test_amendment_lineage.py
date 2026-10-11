from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.paper_changes import AmendmentLineage, lineage_schema
from claimbranch.core.research_schema import normalize
from claimbranch.core.review import Judgment, Proposal
from claimbranch.core.review_policy import assessment_schema, decision_schema, requirements


def record():
    return {'id': 'new-edge', 'kind': 'scientific-edge', 'body': {
        'edge_type': 'qualifies', 'source_id': 'obs-1', 'target_id': 'claim-1',
        'rationale': 'The result covers only this experimental condition.'}}


def source():
    return Judgment.start('project', 'episode').use_proposal(Proposal(
        'proposal-1', 'project', 'episode', 'Qualify this claim by its measured condition.', 'a' * 64))


class AmendmentLineageTests(unittest.TestCase):
    def test_unfinished_source_and_later_manual_edits_retain_exact_contributions(self):
        origin = AmendmentLineage.start('project', 'episode', record(), sources=(source(),))
        revised = record()
        revised['body']['rationale'] = 'Only seed 42 was measured; seed 43 is still a plan.'
        edited = origin.revise(revised)
        self.assertTrue(edited.ai_influenced)
        value = decode(edited.payload)
        self.assertEqual(asdict(source())['history'][0]['trace_digest'],
                         value['revisions'][0]['sources'][0]['history'][0]['trace_digest'])
        self.assertIsNone(value['revisions'][0]['sources'][0]['rationale'])
        self.assertEqual([], value['revisions'][1]['sources'])
        self.assertEqual(edited, AmendmentLineage.restore(edited.payload))
        self.assertEqual(record(), origin.amendment)
        detached = edited.amendment
        detached['body']['rationale'] = 'Changed detached value'
        self.assertEqual(revised, edited.amendment)

    def test_parent_chain_record_identity_kind_and_project_cannot_change(self):
        origin = AmendmentLineage.start('project', 'episode', record(), sources=(source(),))
        edited = record()
        edited['body']['rationale'] = 'Revised limitation.'
        good = decode(origin.revise(edited).payload)
        variants = []
        wrong_parent = deepcopy(good)
        wrong_parent['revisions'][1]['parent_digest'] = 'b' * 64
        variants.append(wrong_parent)
        wrong_identity = deepcopy(good)
        wrong_identity['revisions'][1]['amendment']['id'] = 'other-edge'
        variants.append(wrong_identity)
        wrong_kind = deepcopy(good)
        wrong_kind['revisions'][1]['amendment'] = {'id': 'new-edge', 'kind': 'interpretation',
            'body': {'statement': 'Different kind.', 'observation_ids': ['obs-1']}}
        variants.append(wrong_kind)
        wrong_project = deepcopy(good)
        wrong_project['project_id'] = 'other'
        variants.append(wrong_project)
        broken_source = decode(origin.payload)
        broken_source['revisions'][0]['sources'][0]['history'][0]['parent_digest'] = 'c' * 64
        variants.append(broken_source)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ContractError):
                AmendmentLineage.restore(canonical_bytes(value))

    def test_closed_version_and_canonical_bytes_are_required(self):
        origin = AmendmentLineage.start('project', 'episode', record())
        for update in ({'schema': 'claimbranch.paper-amendment-lineage/v2'}, {'authorization_verified': True},
                       {'ai_influenced': False}, {'episode_id': 'bad episode'}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                AmendmentLineage.restore(canonical_bytes({**decode(origin.payload), **update}))
        with self.assertRaises(ContractError):
            AmendmentLineage.restore(json.dumps(decode(origin.payload)).encode())
        with self.assertRaises(ContractError):
            AmendmentLineage.restore(b' ' * 262145)
        unicode_record = record()
        unicode_record['body']['rationale'] = 'é'
        raw = AmendmentLineage.start('project', 'episode', unicode_record).payload
        with self.assertRaises(ContractError):
            AmendmentLineage.restore(raw.replace('é'.encode(), 'e\u0301'.encode()))

    def test_revision_source_and_byte_limits_preserve_last_good_value(self):
        origin = AmendmentLineage.start('project', 'episode', record())
        self.assertIs(origin, origin.revise(record()))
        for i in range(7):
            changed = record()
            changed['body']['rationale'] = f'Edit {i}.'
            origin = origin.revise(changed)
        raw = origin.payload
        changed['body']['rationale'] = 'Ninth revision.'
        with self.assertRaises(ContractError):
            origin.revise(changed)
        self.assertEqual(raw, origin.payload)
        with self.assertRaises(ContractError):
            AmendmentLineage.start('project', 'episode', record(), sources=(source(),) * 9)
        with self.assertRaises(ContractError):
            AmendmentLineage.start('project', 'episode', record(), sources=(source(), source()))
        with self.assertRaises(ContractError):
            AmendmentLineage.start('project', 'episode', {**record(), 'accepted': True})
        large = Judgment.start('project', 'episode')
        for i in range(7):
            large = large.edit(str(i) + 'x' * 16000, 'y' * 16000)
        other = Judgment('project', 'prior-episode', large.text, large.rationale, large.history)
        with self.assertRaises(ContractError):
            AmendmentLineage.start('project', 'episode', record(), sources=(large, other))

    def test_manual_history_has_no_ai_but_previous_episode_origin_is_retained(self):
        manual = Judgment.start('project', 'episode').edit('A manual interpretation.', 'Its human reason.')
        self.assertFalse(AmendmentLineage.start('project', 'episode', record(), sources=(manual,)).ai_influenced)
        inherited = AmendmentLineage.start('project', 'episode-two', record(), sources=(source(),))
        self.assertTrue(inherited.ai_influenced)
        self.assertEqual('episode', decode(inherited.payload)['revisions'][0]['sources'][0]['episode_id'])

    def test_finite_action_table_rejects_unknown_actions_and_caller_flags(self):
        for ai in (False, True):
            self.assertEqual(('low', None, 'none'), requirements('capture-draft', ai_influenced=ai))
            self.assertEqual(('medium', 'alternative', 'rationale'), requirements('record-interpretation', ai_influenced=ai))
        self.assertEqual(('high', 'main', 'rationale'), requirements('apply-selected-merge', ai_influenced=False))
        self.assertEqual(('high', 'main', 'contextual-explanation'), requirements('apply-selected-merge', ai_influenced=True))
        for action in ('record-evidence-event', 'apply-manuscript', 'accept', 'low', []):
            with self.subTest(action=action), self.assertRaises(ContractError):
                requirements(action, ai_influenced=False)
        with self.assertRaises(ContractError):
            requirements('capture-draft', ai_influenced=1)

    def test_generated_contracts_match_the_owned_schemas(self):
        root = Path(__file__).resolve().parents[2] / 'schemas'
        for name, schema in (('paper-amendment-lineage-v1.json', lineage_schema()),
                             ('paper-review-assessment-v1.json', assessment_schema()),
                             ('paper-review-decision-v1.json', decision_schema())):
            self.assertEqual(schema, json.loads((root / name).read_text()))
        origin = AmendmentLineage.start('project', 'episode', record(), sources=(source(),))
        self.assertEqual(decode(origin.payload), normalize(decode(origin.payload), lineage_schema()))


if __name__ == '__main__':
    unittest.main()
