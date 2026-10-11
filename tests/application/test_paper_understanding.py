from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unicodedata
import unittest
from unittest.mock import patch

from claimbranch.application.paper_service import PaperService
from claimbranch.application.paper_understanding import PaperUnderstandingSession, draft_schema
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import TEXT, normalize
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_episodes import command, first_episode, second_episode


class PaperUnderstandingTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(ai=True, close=False)
        self.work_id = next(item['id'] for item in PaperService(self.history).pending_work()['items']
                            if item['kind'] == 'understanding')

    def session(self, history=None, draft=None, work_id=None):
        return PaperUnderstandingSession(history or self.history, project_id='project',
                                         work_id=work_id or self.work_id, draft=draft)

    def corrected(self):
        return self.history.append(command(self.history, 'record-evidence-event', {
            'event_id': 'explanation-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'Synthetic recount: pruning loses 1.2 percentage points.',
            'value': '1.2', 'rationale': 'Correct the same synthetic observation.', 'supersedes_id': 'event-1'}))

    def test_topics_bind_the_causal_science_without_grading_or_authority(self):
        before = self.history.manifest()
        state = self.session().state()
        self.assertEqual(['claim-scope', 'evidence-interpretation', 'followup-experiment'],
                         [topic['kind'] for topic in state['topics']])
        by_kind = {topic['kind']: topic for topic in state['topics']}
        self.assertIn('claim-pruning-detail', by_kind['claim-scope']['node_ids'])
        self.assertEqual(['interpretation', 'obs-1', 'obs-2'], by_kind['evidence-interpretation']['node_ids'])
        self.assertIn('replication', by_kind['followup-experiment']['node_ids'])
        original = state['context']['original']
        node_ids = {node['id'] for node in original['nodes']}
        relations = {edge['record_id'] for edge in original['relations'] if edge['scientific']}
        for topic in state['topics']:
            self.assertTrue(topic['prompt'].strip())
            self.assertTrue(set(topic['node_ids']) <= node_ids)
            self.assertTrue(set(topic['relation_ids']) <= relations)
            self.assertEqual(original['digest'], topic['cause_digest'])
        self.assertTrue(state['source_ai_influenced'])
        self.assertFalse(state['ai_available'])
        self.assertEqual('memory-only', state['retention'])
        self.assertTrue(all(entry['text'] == '' and entry['reuse_rationale'] is False
                            for entry in state['draft']['entries']))
        self.assertEqual([], state['context']['work']['explanation_answers'])
        self.assertEqual('deferred', state['context']['work']['explanation_disposition'])
        for key in ('closure_available', 'acceptance_available', 'authorization_verified'):
            self.assertIs(state[key], False)
        self.assertEqual(0, state['accepted_writes'])
        self.assertEqual(before, self.history.manifest())

    def test_topic_catalog_uses_selected_consequences_not_omitted_plans(self):
        history = first_episode(ai=True, merge=False, close=False)
        selected = [item['id'] for item in history.view('alternative')['changes'] if item['id'] != 'replication']
        history = history.append(command(history, 'apply-selected-merge', {
            'selected_ids': selected, 'judgment': history.view('alternative')['judgment'],
            'disposition': 'deferred', 'answers': []}))
        work_id = next(item['id'] for item in PaperService(history).pending_work()['items'] if item['kind'] == 'understanding')
        topics = self.session(history, work_id=work_id).state()['topics']
        self.assertEqual(['claim-scope', 'evidence-interpretation', 'manuscript-consequence'],
                         [topic['kind'] for topic in topics])
        self.assertTrue(all('replication' not in topic['node_ids'] for topic in topics))
        self.assertIn('anchor', topics[-1]['node_ids'])

    def test_each_admitted_change_kind_has_a_topic_and_plan_only_has_no_manuscript_topic(self):
        unmerged = first_episode(ai=True, merge=False, close=False)
        later, _ = second_episode(first_episode(ai=True))
        cases = [(unmerged, key, 'episode') for key in
                 ('claim-comparison', 'interpretation', 'edge-pruning', 'replication')]
        cases.append((later, 'status-pruning', 'episode-two'))
        for history, selected, episode in cases:
            with self.subTest(selected=selected):
                history = history.append(command(history, 'apply-selected-merge', {
                    'selected_ids': [selected], 'judgment': history.view('alternative')['judgment'],
                    'disposition': 'deferred', 'answers': []}, episode))
                work = next(i for i in PaperService(history).pending_work()['items']
                            if i['kind'] == 'understanding' and i['episode_id'] == episode)
                topics = self.session(history, work_id=work['id']).state()['topics']
                self.assertTrue(1 <= len(topics) <= 3)
                if selected == 'interpretation':
                    self.assertEqual(['evidence-interpretation'], [t['kind'] for t in topics])
                if selected == 'replication':
                    kinds = {t['kind'] for t in topics}
                    self.assertNotIn('manuscript-consequence', kinds)
                    self.assertNotIn('evidence-interpretation', kinds)
                    plan_topic = next(t for t in topics if t['kind'] == 'followup-experiment')
                    self.assertEqual(['claim-pruning-detail', 'replication'], plan_topic['node_ids'])
        with self.assertRaises(ContractError):
            unmerged.append(command(unmerged, 'apply-selected-merge', {
                'selected_ids': [], 'judgment': unmerged.view('alternative')['judgment'],
                'disposition': 'deferred', 'answers': []}))

    def test_partial_text_and_rationale_reference_survive_leave_open_and_replay(self):
        session = self.session()
        topic_id = session.state()['topics'][0]['id']
        session.edit(topic_id, '', reuse_rationale=True)
        self.assertEqual('', session.state()['draft']['entries'][0]['text'])
        session.edit(topic_id, '이 조건에서는…\n아직 확인할 부분')
        state = session.state()
        self.assertTrue(state['draft']['entries'][0]['reuse_rationale'])
        self.assertEqual('unaccepted-draft', state['draft']['authority'])
        raw = session.leave_open()
        self.assertEqual(raw, session.snapshot())
        restored = self.session(ResearchHistory.replay(self.history.seed, self.history.commands), raw)
        self.assertEqual(state, restored.state())
        self.assertEqual(raw, restored.leave_open())
        self.assertEqual('deferred', restored.state()['context']['work']['explanation_disposition'])
        restored.edit(topic_id, '', reuse_rationale=False)
        self.assertEqual('', restored.state()['draft']['entries'][0]['text'])
        self.assertFalse(restored.state()['draft']['entries'][0]['reuse_rationale'])

    def test_evidence_only_change_retains_text_and_old_basis_until_explicit_rebind(self):
        session = self.session()
        topic = session.state()['topics'][1]['id']
        session.edit(topic, '0.4라서 현재 범위를 유지했다.', reuse_rationale=True)
        raw, old = session.snapshot(), session.state()
        history = self.corrected()
        self.assertEqual(self.history.heads, history.heads)
        session.update_source(history)
        current = session.state()
        self.assertFalse(current['context_current'])
        self.assertEqual(raw, session.snapshot())
        self.assertEqual(old['topics'], current['topics'])
        self.assertEqual(old['context']['current'], current['draft_basis'])
        observation = next(n for n in current['context']['current']['nodes'] if n['id'] == 'obs-1')
        self.assertEqual('1.2', observation['content']['value'])
        self.assertEqual(current, self.session(history, raw).state())
        with self.assertRaises(ContractError):
            session.rebind_context(old['context']['digest'])
        self.assertEqual(current, session.state())
        session.edit(topic, '정정된 값과 기존 판단을 다시 비교해야 한다.')
        self.assertFalse(session.state()['context_current'])
        session.rebind_context(current['context']['digest'])
        rebound = session.state()
        self.assertTrue(rebound['context_current'])
        self.assertEqual(current['context']['current'], rebound['draft_basis'])
        self.assertEqual('정정된 값과 기존 판단을 다시 비교해야 한다.', rebound['draft']['entries'][1]['text'])
        self.assertTrue(rebound['draft']['entries'][1]['reuse_rationale'])
        self.assertFalse(rebound['closure_available'])
        self.assertEqual(rebound, self.session(history, session.snapshot()).state())

    def test_closed_and_later_episodes_keep_the_owned_draft_and_cause(self):
        session = self.session()
        topic_id = session.state()['topics'][0]['id']
        session.edit(topic_id, 'Unfinished claim scope')
        raw, original = session.snapshot(), session.state()['context']['original']
        closed = self.history.append(command(self.history, 'close-episode', {}))
        session.update_source(closed)
        self.assertFalse(session.state()['context_current'])
        self.assertEqual(self.history.heads, closed.heads)
        later, judgment = second_episode(closed)
        later = later.append(command(later, 'apply-selected-merge', {
            'selected_ids': ['status-pruning'], 'judgment': asdict(judgment),
            'disposition': 'deferred', 'answers': []}, 'episode-two'))
        session.update_source(later)
        self.assertEqual(raw, session.snapshot())
        self.assertEqual(original, session.state()['context']['original'])
        self.assertEqual('episode-two', session.state()['context']['current']['episode_id'])
        before = session.state()
        with self.assertRaises(ContractError):
            session.update_source(closed)
        self.assertEqual(before, session.state())
        second = next(item for item in PaperService(later).pending_work()['items']
                      if item['kind'] == 'understanding' and item['episode_id'] == 'episode-two')
        with self.assertRaises(ContractError):
            self.session(later, raw, second['id'])

    def test_documented_fixture_items_reconstruct_independently(self):
        history = replay_example('recorded', series=True)
        before = history.manifest()
        pending = PaperService(history).pending_work()
        for item in pending['items']:
            if item['kind'] != 'understanding':
                continue
            with self.subTest(episode=item['episode_id']):
                session = PaperUnderstandingSession(history, project_id=pending['project_id'], work_id=item['id'])
                included = set(item['selection']['selected']) | set(item['selection']['required'])
                self.assertTrue(all(set(topic['relation_ids']) <= included for topic in session.state()['topics']))
                topic = session.state()['topics'][0]['id']
                session.edit(topic, 'A partial explanation for ' + item['episode_id'])
                restored = PaperUnderstandingSession(ResearchHistory.replay(history.seed, history.commands),
                    project_id=pending['project_id'], work_id=item['id'], draft=session.snapshot())
                self.assertEqual(session.state(), restored.state())
        self.assertEqual(before, history.manifest())

    def test_changed_causal_history_cannot_inherit_a_draft(self):
        session = self.session()
        commands = [decode(raw) for raw in self.history.commands]
        run = next(c for c in commands if c['operation_type'] == 'record-experiment')
        run['payload']['method'] = 'A different synthetic method with reused record IDs.'
        changed = ResearchHistory(self.history.seed, tuple(canonical_bytes(c) for c in commands))
        before = session.state()
        with self.assertRaises(ContractError):
            session.update_source(changed)
        with self.assertRaises(ContractError):
            self.session(changed, session.snapshot())
        self.assertEqual(before, session.state())

    def test_real_but_wrong_historical_prefix_and_invalid_source_updates_fail(self):
        session = self.session()
        value = decode(session.snapshot())
        earlier = {**value, 'bound_operation_id': decode(self.history.commands[0])['id']}
        with self.assertRaises(ContractError):
            self.session(draft=canonical_bytes(earlier))
        corrected = self.corrected()
        later = {**value, 'bound_operation_id': decode(corrected.commands[-1])['id']}
        with self.assertRaises(ContractError):
            self.session(corrected, canonical_bytes(later))
        foreign = ResearchHistory.start_paper_series('foreign', 'Another paper', 'thesis', 'Unresolved thesis', 'anchor')
        before = session.state()
        for history in (None, {}, foreign):
            with self.subTest(source=type(history)), self.assertRaises(ContractError):
                session.update_source(history)
            self.assertEqual(before, session.state())

    def test_snapshot_rejects_wrong_owner_topics_context_versions_and_authority_fields(self):
        session = self.session()
        value = decode(session.snapshot())
        variants = []
        for key, changed in (('schema', 'claimbranch.paper-understanding-draft/v99'),
                             ('rules_version', 'unknown'), ('project_id', 'foreign'), ('work_id', 'unknown'),
                             ('cause_digest', 'f' * 64), ('topics_digest', 'e' * 64),
                             ('context_digest', 'd' * 64), ('bound_operation_id', 'missing'),
                             ('revision', True), ('authority', 'accepted'), ('authorization_verified', True)):
            variants.append({**value, key: changed})
        variants.extend([{**value, 'debt_id': 'forged'}, {**value, 'answers': ['complete']},
                         {**value, 'entries': value['entries'][:-1]}])
        for key, changed in (('topic_id', 'unknown'), ('text', None), ('reuse_rationale', 1)):
            altered = deepcopy(value)
            altered['entries'][0][key] = changed
            variants.append(altered)
        duplicated = deepcopy(value)
        duplicated['entries'][1]['topic_id'] = duplicated['entries'][0]['topic_id']
        variants.append(duplicated)
        for altered in variants:
            with self.subTest(altered=next(k for k in altered if altered[k] != value.get(k))), self.assertRaises(ContractError):
                self.session(draft=canonical_bytes(altered))
        for raw in (value, b'{}', b' ' + session.snapshot(), b' ' * 65537):
            with self.subTest(type=type(raw)), self.assertRaises(ContractError):
                self.session(draft=raw)
        self.assertEqual(canonical_bytes(value), session.snapshot())

    def test_edits_are_bounded_atomic_and_preserve_reference_on_ordinary_revision(self):
        session = self.session()
        topic = session.state()['topics'][0]['id']
        text = '가' * 5461 + 'x'
        self.assertEqual(16384, len(text.encode('utf-8')))
        session.edit(topic, text, reuse_rationale=True)
        before = session.snapshot()
        for topic_id, body, reuse in (('unknown', 'text', None), (topic, text + 'x', None),
                                       (topic, 12, None), (topic, 'text', 1), (True, '', None)):
            with self.subTest(topic=topic_id, reuse=reuse), self.assertRaises(ContractError):
                session.edit(topic_id, body, reuse_rationale=reuse)
            self.assertEqual(before, session.snapshot())
        session.edit(topic, text)
        self.assertEqual(before, session.snapshot())
        value = decode(before)
        value['revision'] = 2**53 - 1
        exhausted = self.session(draft=canonical_bytes(value))
        with self.assertRaises(ContractError):
            exhausted.edit(topic, 'changed')
        self.assertEqual(value, decode(exhausted.snapshot()))

    def test_blank_draft_text_does_not_relax_required_scientific_content(self):
        session = self.session()
        topic = session.state()['topics'][0]['id']
        for text in ('', ' \n\t'):
            session.edit(topic, text)
            self.assertEqual(text, self.session(draft=session.snapshot()).state()['draft']['entries'][0]['text'])
            with self.assertRaises(ContractError):
                normalize(text, TEXT)

    def test_existing_exported_scientific_schemas_do_not_opt_into_blank_text(self):
        root = Path(__file__).resolve().parents[2] / 'schemas'
        names = ('research-command-v1', 'research-command-v2', 'research-command-v3',
                 'paper-seed-v2', 'paper-seed-v3', 'paper-scenario-v1', 'paper-context-request-v1',
                 'paper-context-fields-v2', 'paper-changes-request-v1')
        def check(node):
            if isinstance(node, dict):
                if node.get('type') == 'string':
                    self.assertNotEqual(0, node.get('minLength', 1))
                for value in node.values():
                    check(value)
            elif isinstance(node, list):
                for value in node:
                    check(value)
        for name in names:
            with self.subTest(schema=name):
                check(json.loads((root / (name + '.json')).read_text()))

    def test_nfc_and_escaped_snapshot_budget_are_explicit_and_atomic(self):
        session = self.session()
        topics = [topic['id'] for topic in session.state()['topics']]
        session.edit(topics[0], unicodedata.normalize('NFD', '아직 설명 중'))
        self.assertEqual('아직 설명 중', session.state()['draft']['entries'][0]['text'])
        session.edit(topics[0], '\n' * 16384)
        before = session.snapshot()
        self.assertLess(len(before), 65536)
        with self.assertRaisesRegex(ContractError, '64 KiB'):
            session.edit(topics[1], '\n' * 16384)
        self.assertEqual(before, session.snapshot())
        self.assertEqual(session.state(), self.session(draft=before).state())

    def test_restore_current_basis_reconstructs_once_and_still_checks_digest(self):
        session = self.session()
        topic = session.state()['topics'][0]['id']
        session.edit(topic, 'Keep this explanation', reuse_rationale=True)
        raw, expected = session.snapshot(), session.state()
        original = PaperService.understanding_return
        calls = []
        def observe(service, *args, **kwargs):
            calls.append(service._history.commands)
            return original(service, *args, **kwargs)
        with patch.object(PaperService, 'understanding_return', observe):
            restored = self.session(draft=raw)
        self.assertEqual([self.history.commands], calls)
        self.assertEqual(raw, restored.snapshot())
        self.assertEqual(expected, restored.state())
        forged = decode(raw)
        forged['context_digest'] = '0' * 64
        with self.assertRaises(ContractError):
            self.session(draft=canonical_bytes(forged))

    def test_restore_current_basis_then_update_keeps_prior_basis_and_refuses_old_rebind(self):
        original = self.session()
        original.edit(original.state()['topics'][0]['id'], 'Original writing')
        raw, before = original.snapshot(), original.state()
        history = ResearchHistory.replay(self.history.seed, self.history.commands)
        restored = self.session(history, raw)
        restored.update_source(self.corrected())
        changed = restored.state()
        self.assertEqual(before['context']['current'], changed['draft_basis'])
        self.assertFalse(changed['context_current'])
        self.assertEqual(raw, restored.snapshot())
        with self.assertRaises(ContractError):
            restored.rebind_context(before['context']['digest'])
        self.assertEqual(changed, restored.state())

    def test_custom_history_projection_cannot_replace_independent_basis_validation(self):
        class CustomHistory(ResearchHistory):
            def manifest(self):
                return super().manifest() + b' '
        history = CustomHistory(self.history.seed, self.history.commands)
        raw = self.session(history).snapshot()
        with self.assertRaises(ContractError):
            self.session(history, raw)

    def test_restore_older_basis_reconstructs_both_exact_histories(self):
        session = self.session()
        topic = session.state()['topics'][0]['id']
        session.edit(topic, 'Earlier basis must remain')
        raw, basis = session.snapshot(), session.state()['draft_basis']
        changed = self.corrected()
        original = PaperService.understanding_return
        calls = []
        def observe(service, *args, **kwargs):
            calls.append(service._history.commands)
            return original(service, *args, **kwargs)
        with patch.object(PaperService, 'understanding_return', observe):
            restored = self.session(changed, raw)
        self.assertEqual([changed.commands, self.history.commands], calls)
        self.assertEqual(raw, restored.snapshot())
        self.assertEqual(basis, restored.state()['draft_basis'])
        self.assertFalse(restored.state()['context_current'])

    def test_detached_views_and_schema_cannot_mutate_live_work(self):
        session = self.session()
        original = session.state()
        changed = session.state()
        changed['draft']['entries'][0]['text'] = 'replaced outside the session'
        changed['topics'][0]['node_ids'].clear()
        changed['context']['work']['judgment']['history'].clear()
        changed['draft_basis']['nodes'].clear()
        self.assertEqual(original, session.state())
        schema = draft_schema()
        schema['properties'].clear()
        self.assertTrue(draft_schema()['properties'])

    def test_no_draft_can_be_opened_for_unmerged_manual_or_wrong_kind_work(self):
        manuscript = next(item['id'] for item in PaperService(self.history).pending_work()['items']
                          if item['kind'] == 'manuscript')
        for history, work_id, project_id in ((self.history, manuscript, 'project'),
                                            (self.history, self.work_id, 'other-project'),
                                            (first_episode(), self.work_id, 'project'),
                                            (first_episode(ai=True, merge=False, close=False), self.work_id, 'project')):
            with self.subTest(work=work_id, project=project_id), self.assertRaises(ContractError):
                PaperUnderstandingSession(history, project_id=project_id, work_id=work_id)


if __name__ == '__main__':
    unittest.main()
