"""Explicit work references reuse an owner without merging scientific drafts."""
import unittest

from claimbranch.application.paper_workspace import PaperWorkspace
from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example


class WorkLinkTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.manifest = self.history.manifest()
        self.paper = PaperWorkspace(self.history)
        self.episode = self.paper.service.query('main')['episode_id']
        self.owner = (self.episode, 'main', 'obs-1')

    def test_one_judgment_shared_across_evidence_and_claims_keeps_other_work(self):
        original = self.paper.draft(*self.owner)
        original.edit(text='Only one mask is measured.', rationale='Other conditions are unresolved.')
        other = self.paper.draft(self.episode, 'main', 'claim-pruning')
        other.edit(text='Separate judgment.', rationale='A different question.')
        self.paper.link_work(self.owner, ['obs-1', 'claim-pruning', 'claim-comparison'])
        self.assertEqual(self.owner, self.paper.work_owner(self.episode, 'main', 'claim-pruning'))
        self.assertEqual('Separate judgment.', other.state()['draft']['text'])
        self.assertEqual(2, len(self.paper._drafts))
        self.paper.activate_work((self.episode, 'main', 'claim-pruning'), 'claim-pruning')
        self.assertEqual((self.episode, 'main', 'claim-pruning'), self.paper.work_owner(self.episode, 'main', 'claim-pruning'))
        self.assertEqual({'obs-1', 'claim-pruning', 'claim-comparison'}, set(self.paper.work_nodes(self.owner)))
        self.assertEqual(self.manifest, self.history.manifest())

    def test_invalid_link_or_foreign_activation_preserves_previous_work(self):
        self.paper.link_work(self.owner, ['obs-1', 'claim-pruning'])
        for targets in (['obs-1', 'missing'], ['claim-pruning'], ['obs-1', 'obs-1']):
            with self.assertRaises(ContractError):
                self.paper.link_work(self.owner, targets)
        with self.assertRaises(ContractError):
            self.paper.activate_work(self.owner, 'claim-comparison')
        self.assertEqual((self.episode, 'alternative', 'claim-pruning'),
                         self.paper.work_owner(self.episode, 'alternative', 'claim-pruning'))
        self.assertEqual({'obs-1', 'claim-pruning'}, set(self.paper.work_nodes(self.owner)))

    def test_link_changes_invalidate_exact_review_without_erasing_candidates(self):
        work = self.paper.candidates(*self.owner)
        key = work.create('claim', {'role': 'subclaim', 'parent_ids': ['claim-pruning'],
                                  'statement': 'Another condition.', 'scope': 'One mask.'})
        session = self.paper.draft(*self.owner)
        session.edit(text='Measured scope only.', rationale='Other masks not measured.')
        state = session.state()
        session.prepare_changes({'schema_version': 1, **state['paper'], 'draft_id': state['draft_id'],
                                 'draft_revision': state['revision'], 'amendments': list(work.records.values()),
                                 'selected_ids': [key]})
        self.paper.link_work(self.owner, ['obs-1', 'claim-pruning'])
        self.assertIsNone(session.get_changes_preview())
        self.assertIn(key, work.project()['authored_ids'])
        self.paper.link_work(self.owner, ['obs-1'])
        self.assertEqual((self.episode, 'main', 'claim-pruning'), self.paper.work_owner(self.episode, 'main', 'claim-pruning'))

    def test_capacity_invalid_shape_and_revision_fail_before_changing_links(self):
        for invalid in (None, ['episode'], ['episode', 'main', None]):
            with self.assertRaises(ContractError):
                self.paper.link_work(invalid, ['obs-1'])
        revision = self.paper.work_revision
        self.paper.link_work(self.owner, ['obs-1', 'claim-pruning'])
        with self.assertRaises(ContractError):
            self.paper.link_work(self.owner, ['obs-1'], expected_revision=revision)
        with self.assertRaises(ContractError):
            self.paper.link_work(self.owner, ['obs-1'], activate_ids='obs-1')
        with self.assertRaises(ContractError):
            self.paper.link_work(self.owner, ['obs-1'] + [f'missing-{i}' for i in range(16)])
        for ref in ('main', 'alternative'):
            for node in self.paper.service.query(ref)['nodes']:
                key = (self.episode, ref, node['id'])
                if key in self.paper._drafts:
                    continue
                if len(self.paper._drafts) == 16:
                    before = self.paper.work_revision
                    with self.assertRaises(ContractError):
                        other = 'obs-1' if node['id'] != 'obs-1' else 'claim-pruning'
                        self.paper.link_work(key, [node['id'], other])
                    self.assertEqual(before, self.paper.work_revision)
                    self.assertEqual({'obs-1', 'claim-pruning'}, set(self.paper.work_nodes(self.owner)))
                    return
                self.paper.draft(*key)
        self.fail('Fixture must expose enough contexts to exercise capacity.')

    def test_source_refresh_retains_links_and_text_but_rejects_old_link_preview(self):
        from tests.contract.test_paper_episodes import first_episode, second_episode
        first = first_episode()
        later, _ = second_episode(first)
        paper = PaperWorkspace(first)
        owner = ('episode', 'main', 'obs-1')
        session = paper.draft(*owner)
        session.edit(text='Original thought.', rationale='Original reason.')
        paper.link_work(owner, ['obs-1', 'claim-pruning'])
        revision = paper.work_revision
        paper.update_history(later)
        with self.assertRaises(ContractError):
            paper.link_work(owner, ['obs-1'], expected_history=first, expected_revision=revision)
        self.assertEqual({'obs-1', 'claim-pruning'}, set(paper.work_nodes(owner)))
        self.assertEqual('Original thought.', session.state()['draft']['text'])
        self.assertEqual(owner, paper.work_owner('episode', 'main', 'claim-pruning'))
        self.assertEqual(('episode-two', 'main', 'claim-pruning'),
                         paper.work_owner('episode-two', 'main', 'claim-pruning'))
