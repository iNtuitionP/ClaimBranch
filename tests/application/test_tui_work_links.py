"""Reuse a judgment explicitly without merging nodes, notes, origin or recovery."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_actions import actions_ui
from claimbranch.application.tui_work_links_ui import work_links_ui
from claimbranch.application.tui_recovery import DraftRecovery
from claimbranch.fixtures import replay_example


class LinkedJudgmentTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.manifest = self.history.manifest()
        self.t = Terminal.__new__(Terminal)
        self.t.app = TerminalWorkspace(self.history, ai_off=True)
        self.t.modal, self.t.buffers, self.t.field = None, [], 0
        self.t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        self.app = self.t.app
        self.app.select('obs-1')
        self.app.keep_draft('직접 작성한 판단', 'One recorded mask only.')
        self.owner = self.app.context_key()

    def action(self, title):
        self.t.key(';')
        ui = actions_ui(self.t)
        ui.index = next(i for i, item in enumerate(ui.items()) if item.title == title)
        self.t.key('enter')

    def link(self, *nodes):
        self.action('Link this judgment to nodes')
        ui = work_links_ui(self.t)
        for key in nodes:
            ui.index = ui.items.index(key)
            self.t.key(' ')
        self.t.key('enter')
        self.assertEqual('work-links-confirm', self.t.modal)
        self.t.key('enter')
        self.assertIsNone(self.t.modal)

    def test_edit_one_judgment_across_three_nodes_without_retyping_or_note_copy(self):
        self.link('claim-pruning', 'claim-comparison')
        session = self.app.review.session()
        for node in ('claim-pruning', 'claim-comparison', 'obs-1'):
            self.app.select(node)
            self.assertEqual('직접 작성한 판단', self.app.draft()['text'])
            self.assertIs(session, self.app.review.session())
        self.app.select('claim-pruning')
        self.app.keep_note('Only this claim has a note.')
        self.t.key('e')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            text = self.t.draw_modal(Frame(width, height)).plain()
            self.assertIn('JUDGMENT / E1', text)
            self.assertIn('Linked:', text)
        self.t.key(('paste', ' · revised'))
        self.t.key('keep')
        self.assertEqual(self.owner, self.app.review.key)
        self.app.select('obs-1')
        self.assertEqual('직접 작성한 판단 · revised', self.app.draft()['text'])
        self.assertEqual('', self.app.note())
        self.assertEqual(1, len(self.app.review.sessions))
        self.assertEqual(self.manifest, self.history.manifest())

    def test_choose_separate_judgment_preserves_both_and_preview_cancel_changes_nothing(self):
        self.app.select('claim-pruning')
        self.app.keep_draft('Independent claim judgment.', 'A distinct question.')
        separate = self.app.context_key()
        self.app.select('obs-1')
        self.link('claim-pruning')
        self.app.select('claim-pruning')
        self.action('Choose a judgment for this node')
        ui = work_links_ui(self.t)
        ui.index = ui.items.index(separate)
        self.t.key('enter')
        text = self.t.draw_modal(Frame(80, 24)).plain()
        self.assertIn('Independent claim judgment.', text)
        self.t.key('escape')
        self.assertEqual(self.owner, self.app.review.key)
        self.t.key('enter')
        self.t.key('enter')
        self.assertEqual(separate, self.app.review.key)
        self.assertEqual('Independent claim judgment.', self.app.draft()['text'])
        self.action('Choose a judgment for this node')
        ui.index = ui.items.index(self.owner)
        self.t.key('enter')
        self.t.key('enter')
        self.assertEqual('직접 작성한 판단', self.app.draft()['text'])
        self.assertEqual('Independent claim judgment.', self.app.review.sessions[separate].state()['draft']['text'])

    def test_unfinished_text_and_candidate_work_stay_with_original_owner(self):
        work = self.app.review.candidates()
        key = work.create('claim', {'role': 'subclaim', 'parent_ids': ['claim-pruning'],
                                  'statement': 'Another condition.', 'scope': 'One mask.'})
        self.link('claim-pruning')
        self.app.select('claim-pruning')
        self.t.key('e')
        self.t.key(('paste', ' unfinished'))
        self.t.key('escape')
        self.assertIn((*self.owner, 'edit'), self.app.unfinished)
        self.assertNotIn((*self.app.context_key(), 'edit'), self.app.unfinished)
        self.action('Open argument drafts')
        self.assertIn(key, self.app.review.candidates().records)
        self.t.key('escape')
        self.app.select('obs-2')
        self.t.key('U')
        self.t.key('enter')
        self.assertEqual('obs-1', self.app.selected_id)
        self.assertEqual('직접 작성한 판단 unfinished', self.t.buffers[0].text)

    def test_checkpoints_keep_manual_text_at_owner_but_restore_no_links(self):
        self.link('claim-pruning')
        self.app.select('claim-pruning')
        self.app.keep_draft('Revised from a linked claim.', 'Same judgment, same owner.')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'draft.json'
            store = DraftRecovery(path, self.app)
            store.save(self.app, ('edit', ['unfinished linked input', '']))
            store.close()
            restored = TerminalWorkspace(self.history, ai_off=True)
            reader = DraftRecovery(path, restored)
            reader.close()
        self.assertFalse(restored.paper.volatile_links)
        self.assertEqual('claim-pruning', restored.selected_id)
        self.assertEqual('', restored.draft()['text'])
        restored.select('obs-1')
        self.assertEqual('Revised from a linked claim.', restored.draft()['text'])
        self.assertEqual(['unfinished linked input', ''], restored.unfinished[(*self.owner, 'edit')])

    def test_tiny_pause_stale_choices_and_cross_branch_are_explicit(self):
        self.action('Link this judgment to nodes')
        ui = work_links_ui(self.t)
        self.t.screen.getmaxyx = lambda: (12, 36)
        self.t.key(' ')
        self.t.key('enter')
        self.assertEqual('work-links-nodes', self.t.modal)
        self.assertIn('paused', self.t.draw_modal(Frame(36, 12)).plain())
        self.t.screen.getmaxyx = lambda: (24, 80)
        self.app.paper.link_work(self.app.full_context(self.owner), ['obs-1', 'claim-pruning'])
        self.t.key('enter')
        self.assertIn('changed', ui.notice)
        self.t.key('escape')
        self.app.switch_ref()
        self.app.select('claim-pruning')
        self.assertEqual('', self.app.draft()['text'])
        self.action('Choose a judgment for this node')
        self.assertNotIn(self.owner, ui.items)

    def test_ai_influence_and_pending_response_stay_with_same_shared_session(self):
        self.app = self.t.app = TerminalWorkspace(self.history)
        self.app.select('obs-1')
        self.app.keep_draft('My first thought.', '')
        work = self.app.review
        outbound = work.prepare_ai(['obs-1'], include_draft=True)
        work.begin_ai(outbound)
        self.link('claim-pruning')
        self.app.select('claim-pruning')
        self.assertEqual(self.owner, work.key)
        work.complete_ai(self.owner, outbound['request']['request_id'])
        work.adopt_ai()
        self.app.keep_draft('I revised the suggestion myself.', 'Only recorded evidence supports this scope.')
        self.assertTrue(work.influenced())
        state = work.session().state()
        self.assertTrue(any(item['contributor'] == 'ai' for item in state['draft']['contributions']))
        self.app.select('obs-1')
        self.assertEqual('I revised the suggestion myself.', self.app.draft()['text'])
        self.assertEqual(state['draft']['contributions'], work.session().state()['draft']['contributions'])
        self.assertEqual('My first thought.', self.app.drafts[self.owner]['text'])
        self.assertNotIn(('main', 'claim-pruning'), self.app.drafts)
        self.t.key('e')
        self.t.key(('paste', ' unfinished assisted wording'))
        self.t.key('escape')
        self.app.select('claim-pruning')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'draft.json'
            store = DraftRecovery(path, self.app)
            store.save(self.app, ('edit', ['AI-derived unfinished content', '']))
            store.close()
            restored = TerminalWorkspace(self.history, ai_off=True)
            reader = DraftRecovery(path, restored)
            reader.close()
        restored.select('obs-1')
        self.assertEqual('My first thought.', restored.draft()['text'])
        self.assertNotIn((*self.owner, 'edit'), restored.unfinished)
        self.assertFalse(restored.paper.volatile_links)
        self.assertEqual(self.manifest, self.history.manifest())

    def test_unlink_viewed_node_returns_to_its_separate_judgment(self):
        self.link('claim-pruning')
        self.app.select('claim-pruning')
        self.link('claim-pruning')
        self.assertEqual(('main', 'claim-pruning'), self.app.review.key)
        self.assertEqual('', self.app.draft()['text'])
        self.assertIn('Judgment C2 selected', self.app.message)
        self.app.select('obs-1')
        self.assertEqual('직접 작성한 판단', self.app.draft()['text'])

    def test_return_preserves_separate_unfinished_work_and_episode_identity(self):
        self.app = self.t.app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        self.app.select('claim-pruning')
        self.t.key('e')
        self.t.key(('paste', 'Independent unfinished thought.'))
        self.t.key('escape')
        separate = self.app.context_key()
        self.app.select('obs-1')
        self.app.keep_draft('Later episode judgment.', '')
        self.link('claim-pruning')
        self.app.switch_context('episode', 'main')
        self.app.select('claim-pruning')
        self.assertEqual('', self.app.draft()['text'])
        self.t.key('U')
        self.t.key('enter')
        self.assertEqual(separate, self.app.review.key)
        self.assertEqual('episode-two', self.app.episode_id)
        self.assertEqual('Independent unfinished thought.', self.t.buffers[0].text)
        self.t.key('escape')
        self.app.select('obs-1')
        self.assertEqual('Later episode judgment.', self.app.draft()['text'])

    def test_resume_manual_fallback_does_not_require_a_free_review_session(self):
        for ref in ('main', 'alternative'):
            self.app.switch_context(self.app.episode_id, ref)
            for node in self.app.nodes:
                self.app.select(node)
                if len(self.app.paper._drafts) < 16:
                    self.app.review.session()
                else:
                    self.t.key('e')
                    self.t.key(('paste', 'Manual work beyond review capacity.'))
                    self.t.key('escape')
                    existing = next(key for key in self.app.paper._drafts if key[1] == ref)
                    self.app.paper.link_work(existing, [existing[2], node])
                    self.t.key('U')
                    self.t.key('enter')
                    self.assertEqual('edit', self.t.modal)
                    self.assertEqual('Manual work beyond review capacity.', self.t.buffers[0].text)
                    return
        self.fail('Need more contexts than review capacity.')

    def test_choosing_own_manual_judgment_at_capacity_requires_no_new_session(self):
        for ref in ('main', 'alternative'):
            self.app.switch_context(self.app.episode_id, ref)
            for node in self.app.nodes:
                self.app.select(node)
                if len(self.app.paper._drafts) < 16:
                    self.app.review.session()
                    continue
                own = self.app.context_key()
                self.app.keep_draft('Independent manual text.', '')
                existing = next(key for key in self.app.paper._drafts if key[1] == ref)
                self.app.paper.link_work(existing, [existing[2], node])
                self.action('Choose a judgment for this node')
                ui = work_links_ui(self.t)
                ui.index = ui.items.index(own)
                self.t.key('enter')
                self.t.key('enter')
                self.assertIsNone(self.t.modal)
                self.assertEqual(own, self.app.review.key)
                self.assertEqual('Independent manual text.', self.app.draft()['text'])
                self.assertEqual(16, len(self.app.paper._drafts))
                return
        self.fail('Need more contexts than review capacity.')

    def test_adding_a_reference_preserves_existing_nodes_independent_choice(self):
        self.link('claim-pruning')
        own = (self.app.episode_id, 'main', 'claim-pruning')
        self.app.paper.activate_work(own, 'claim-pruning')
        self.assertIn('C2 (different judgment)', self.app.work_labels())
        self.link('obs-2')
        self.assertEqual(own, self.app.paper.work_owner(*own))
        self.app.select('obs-2')
        self.assertEqual(self.owner, self.app.review.key)

    def test_choose_explains_link_capacity_before_confirmation(self):
        self.app.select('claim-pruning')
        self.action('Choose a judgment for this node')
        ui = work_links_ui(self.t)
        ui.index = ui.items.index(self.owner)
        full = ('obs-1', *(f'source-{i}' for i in range(15)))
        with patch.object(self.app.paper, 'work_nodes', return_value=full):
            self.t.key('enter')
        self.assertEqual('work-links-choose', self.t.modal)
        self.assertIn('unlink one first', ui.notice)
