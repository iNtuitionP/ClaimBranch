from copy import deepcopy
import unittest

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.review import Judgment
from claimbranch.fixtures import replay_example


def new_records():
    return [
        {'id': 'new-claim', 'kind': 'claim', 'body': {'role': 'subclaim',
         'statement': 'A different pruning mask remains untested.',
         'scope': 'Only the measured mask.', 'parent_ids': ['claim-pruning']}},
        {'id': 'new-link', 'kind': 'scientific-edge', 'body': {'source_id': 'obs-1',
         'target_id': 'new-claim', 'edge_type': 'qualifies', 'rationale': 'One mask was measured.'}},
    ]


class DraftProjectionTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)

    def project(self, items):
        return decode(self.history.project_paper_draft('main', items).payload)

    def test_new_claim_and_connection_need_no_judgment_and_never_append(self):
        original = self.history.manifest()
        result = self.project(new_records())
        self.assertEqual('unaccepted-draft', result['authority'])
        self.assertFalse(result['authorization_verified'])
        self.assertIn('new-claim', [c['id'] for c in result['after']['claims']])
        self.assertEqual(self.history.view('main')['evidence'], result['after']['evidence'])
        self.assertEqual(self.history.view('main')['judgment'], result['source_judgment'])
        self.assertEqual(original, self.history.manifest())
        with self.assertRaises(ContractError):
            self.history.preview_paper_changes('main', new_records(), ['new-link'], Judgment.start('paper-project', 'episode'))

    def test_empty_draft_is_a_readable_projection_without_fabricated_records(self):
        result = self.project([])
        self.assertEqual(self.history.view('main'), result['after'])
        self.assertEqual([], result['amendments'])

    def test_duplicate_dangling_partial_and_evidence_aliases_are_rejected(self):
        records = new_records()
        partial = deepcopy(records); partial[0]['body']['statement'] = ''
        aliased = deepcopy(records); aliased[0]['id'] = 'obs-1'
        for items in ([records[0], records[0]], [records[1]], partial, aliased):
            with self.subTest(items=items), self.assertRaises(ContractError):
                self.project(items)

    def test_hierarchy_cycles_self_support_and_limits_share_domain_rules(self):
        records = new_records()
        for field, value in (('parent_ids', ['new-claim']), ('role', 'main')):
            items = deepcopy(records); items[0]['body'][field] = value
            with self.assertRaises(ContractError):
                self.project(items)
        items = deepcopy(records); items[1]['body']['source_id'] = 'new-claim'
        with self.assertRaises(ContractError):
            self.project(items)
        items = [dict(records[0], id='new-' + str(i)) for i in range(65)]
        with self.assertRaises(ContractError):
            self.project(items)

    def test_old_episode_interpretation_is_still_protected(self):
        self.history = replay_example('recorded', series=True)
        item = deepcopy(next(c for c in self.history.view('main', episode_id='episode-two')['changes']
                             if c['id'] == 'interpretation'))
        item['body']['statement'] = 'Rewrite the earlier episode.'
        with self.assertRaises(ContractError):
            self.history.project_paper_draft('main', [item], episode_id='episode-two')


if __name__ == '__main__':
    unittest.main()
