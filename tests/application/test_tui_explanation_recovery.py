"""Encrypted return to partial explanation must preserve context, never close it."""
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import snapshot, restore, JudgmentRecovery, excluded_work
from claimbranch.application.tui_understanding_ui import understanding_ui
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.application.paper_service import PaperService
from claimbranch.application.paper_understanding import PaperUnderstandingSession
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_episodes import command, first_episode


class ExplanationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('recorded', series=True)
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.items = [item for item in self.app.service.pending_work()['items'] if item['kind'] == 'understanding']

    def open(self, index=0):
        session = self.app.understanding.open(self.items[index]['id'])
        return session, session.state()['topics'][0]['id']

    def reopen(self, saved=None):
        saved = snapshot(self.app) if saved is None else saved
        app = TerminalWorkspace(saved.history, ai_off=True)
        restore(app, saved)
        return app

    def test_kept_rationale_empty_unfinished_and_independent_topics_survive(self):
        session, topic = self.open()
        session.edit(topic, '이 조건에 한정한 설명', reuse_rationale=True)
        key = (self.items[0]['id'], topic)
        self.app.understanding.buffers[key] = ''
        self.app.understanding.positions[key[0]] = 1
        other, second_topic = self.open(1)
        other.edit(second_topic, '별개의 설명')
        saved = snapshot(self.app)
        self.assertEqual('claimbranch.paper-work/v7', decode(saved.payload)['schema'])
        app = self.reopen(saved)
        again = app.understanding.open(key[0])
        self.assertEqual(session.snapshot(), again.snapshot())
        self.assertEqual('', app.understanding.buffers[key])
        self.assertEqual(1, app.understanding.positions[key[0]])
        self.assertEqual(other.snapshot(), app.understanding.sessions[self.items[1]['id']].snapshot())
        self.assertEqual(session.state()['context']['original'], again.state()['context']['original'])
        self.assertTrue(again.state()['source_ai_influenced'])
        self.assertFalse(again.state()['closure_available'])
        self.assertFalse(again.state()['authorization_verified'])
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())

    def test_checkpoint_reconstructs_current_once_and_older_basis_independently(self):
        for index in range(2):
            session, topic = self.open(index)
            session.edit(topic, 'Independent retained explanation')
        original = PaperService.understanding_return
        calls = []
        def observe(service, *args, **kwargs):
            calls.append(service._history.commands)
            return original(service, *args, **kwargs)
        with patch.object(PaperService, 'understanding_return', observe):
            current = snapshot(self.app)
        self.assertEqual([self.history.commands] * 2, calls)
        self.assertEqual(current.payload, snapshot(self.app).payload)

        # The last command closes the second episode. Write just before it,
        # then observe the later source without silently rebinding that writing.
        prefix = ResearchHistory.replay(self.history.seed, self.history.commands[:-1])
        key = self.items[1]['id']
        older = PaperUnderstandingSession(prefix, project_id=self.items[1]['project_id'], work_id=key)
        older.edit(older.state()['topics'][0]['id'], 'Written before closure')
        before = older.snapshot(), older.state()['draft_basis']
        older.update_source(self.history)
        self.app.understanding.sessions[key] = older
        calls.clear()
        with patch.object(PaperService, 'understanding_return', observe):
            saved = snapshot(self.app)
        self.assertEqual([self.history.commands, self.history.commands, prefix.commands], calls)
        restored = self.reopen(saved).understanding.sessions[key]
        self.assertEqual(before, (restored.snapshot(), restored.state()['draft_basis']))
        self.assertFalse(restored.state()['context_current'])

    def test_shared_source_pending_projection_is_built_once_per_checkpoint(self):
        for index in range(2):
            session, topic = self.open(index)
            session.edit(topic, 'Separate writing ' + str(index))
        expected = snapshot(self.app).payload
        original = PaperService._all_pending_work
        calls = []
        def observe(service):
            calls.append(service._history.commands)
            return original(service)
        with patch.object(PaperService, '_all_pending_work', observe):
            saved = snapshot(self.app)
        self.assertEqual([self.history.commands], calls)

        self.assertEqual(expected, saved.payload)
        # Sharing a projection must not share mutable writing or leak into the
        # next validation. Both sessions and subsequent reads remain independent.
        restored = self.reopen(saved)
        first, second = [restored.understanding.sessions[x['id']] for x in self.items]
        before = second.state()
        first.edit(first.state()['topics'][0]['id'], 'Only the first changed')
        exposed = first.state(); exposed['context']['current']['nodes'].clear()
        self.assertEqual(before, second.state())
        calls.clear()
        with patch.object(PaperService, '_all_pending_work', observe):
            self.assertEqual(expected, snapshot(self.app).payload)
        self.assertEqual([self.history.commands], calls)

    def test_distinct_source_prefixes_and_failed_second_draft_remain_independent(self):
        first, topic = self.open(0); first.edit(topic, 'Current source')
        prefix = ResearchHistory.replay(self.history.seed, self.history.commands[:-1])
        key = self.items[1]['id']
        second = PaperUnderstandingSession(prefix, project_id=self.items[1]['project_id'], work_id=key)
        second.edit(second.state()['topics'][0]['id'], 'Earlier source')
        self.app.understanding.sessions[key] = second
        saved = snapshot(self.app)
        expected = [first.snapshot(), second.snapshot()]
        restored = self.reopen(saved)
        self.assertEqual(expected, [s.snapshot() for s in restored.understanding.sessions.values()])
        self.assertEqual([14, 13], [len(s._history.commands) for s in restored.understanding.sessions.values()])
        from claimbranch.application.paper_explanation_snapshot import restore_explanations
        value = decode(saved.payload)['workspace']['understanding']
        value['sessions'].reverse()
        detached = restore_explanations(self.history, value)
        self.assertEqual(list(reversed(expected)), [s.snapshot() for s in detached['sessions'].values()])
        for mutation in ('cause', 'source', 'duplicate'):
            value = decode(saved.payload)['workspace']['understanding']
            if mutation == 'cause': value['sessions'][1]['draft']['cause_digest'] = '0' * 64
            elif mutation == 'source': value['sessions'][1]['source']['digest'] = '0' * 64
            else: value['sessions'][1] = value['sessions'][0]
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                restore_explanations(self.history, value)
            self.assertEqual(expected, [s.snapshot() for s in self.app.understanding.sessions.values()])
        self.assertEqual(saved.payload, snapshot(self.app).payload)

    def test_batch_api_limits_parity_detached_state_and_late_refusal(self):
        project = self.items[0]['project_id']
        prefix = ResearchHistory.replay(self.history.seed, self.history.commands[:-1])
        for source in (self.history, prefix):
            drafts = []
            for item in self.items:
                session = PaperUnderstandingSession(source, project_id=project, work_id=item['id'])
                session.edit(session.state()['topics'][0]['id'], 'Independent writing')
                drafts.append(session.snapshot())
            expected = [PaperUnderstandingSession(self.history, project_id=project,
                        work_id=item['id'], draft=raw).state() for item, raw in zip(self.items, drafts)]
            original, calls = PaperService._all_pending_work, []
            def observe(service):
                calls.append(service._history.commands)
                return original(service)
            with patch.object(PaperService, '_all_pending_work', observe):
                restored = PaperUnderstandingSession.restore_many(self.history, project_id=project, drafts=drafts)
            self.assertEqual(expected, [s.state() for s in restored])
            self.assertEqual([self.history.commands] + ([prefix.commands] if source is prefix else []), calls)
            first, second = restored
            self.assertIsNot(first._context, second._context)
            self.assertIsNot(first._context['current'], second._context['current'])
            self.assertIsNot(first._topics, second._topics)
            self.assertIsNot(first._bound, second._bound)
            self.assertIsNot(first._bound['current'], second._bound['current'])
            self.assertFalse(any(isinstance(v, PaperService) for s in restored for v in vars(s).values()))
            bad = decode(drafts[1]); bad['cause_digest'] = '0' * 64
            with self.assertRaises(ContractError):
                PaperUnderstandingSession.restore_many(self.history, project_id=project,
                                                       drafts=[drafts[0], canonical_bytes(bad)])
            self.assertEqual(expected, [s.state() for s in restored])
        class CustomHistory(ResearchHistory): pass
        for history, values in ((self.history, drafts * 9), (self.history, iter(drafts)),
                (self.history, ['text']), (self.history, [b' ' * 65537]),
                (self.history, [drafts[0]] * 2),
                (CustomHistory(self.history.seed, self.history.commands), drafts)):
            with self.subTest(values=type(values).__name__), self.assertRaises(ContractError):
                PaperUnderstandingSession.restore_many(history, project_id=project, drafts=values)

    def test_distinct_earlier_bases_remain_distinct_within_one_batch(self):
        drafts, sources = [], []
        for item, count in zip(self.items, (8, 13)):
            source = ResearchHistory.replay(self.history.seed, self.history.commands[:count])
            sources.append(source)
            session = PaperUnderstandingSession(source, project_id=item['project_id'], work_id=item['id'])
            session.edit(session.state()['topics'][0]['id'], 'Written at operation ' + str(count))
            drafts.append(session.snapshot())
        project = self.items[0]['project_id']
        expected = [PaperUnderstandingSession(self.history, project_id=project, work_id=item['id'], draft=raw).state()
                    for item, raw in zip(self.items, drafts)]
        original, calls = PaperService._all_pending_work, []
        def observe(service):
            calls.append(service._history.commands)
            return original(service)
        with patch.object(PaperService, '_all_pending_work', observe):
            restored = PaperUnderstandingSession.restore_many(self.history, project_id=project, drafts=drafts)
        self.assertEqual([self.history.commands, *(s.commands for s in sources)], calls)
        self.assertEqual(expected, [s.state() for s in restored])
        self.assertNotEqual(restored[0].state()['draft_basis']['digest'], restored[1].state()['draft_basis']['digest'])

    def test_shared_older_basis_replays_once_and_still_checks_each_fingerprint(self):
        prefix = ResearchHistory.replay(self.history.seed, self.history.commands[:-1])
        for item in self.items:
            session = PaperUnderstandingSession(prefix, project_id=item['project_id'], work_id=item['id'])
            session.edit(session.state()['topics'][0]['id'], 'Earlier writing for ' + item['id'], reuse_rationale=True)
            session.update_source(self.history)
            self.app.understanding.sessions[item['id']] = session
            self.app.understanding.positions[item['id']] = 0
        expected = [s.state() for s in self.app.understanding.sessions.values()]
        original, calls = PaperService._all_pending_work, []
        def observe(service):
            calls.append(service._history.commands)
            return original(service)
        with patch.object(PaperService, '_all_pending_work', observe):
            saved = snapshot(self.app)
        self.assertEqual([self.history.commands, prefix.commands], calls)
        restored = self.reopen(saved)
        self.assertEqual(expected, [s.state() for s in restored.understanding.sessions.values()])
        self.assertTrue(all(not s.state()['context_current'] for s in restored.understanding.sessions.values()))
        # A shared earlier projection never substitutes for each draft's digest.
        for field in ('context_digest', 'bound_operation_id'):
            value = decode(saved.payload)
            row = value['workspace']['understanding']['sessions'][1]['draft']
            row[field] = '0' * 64 if field == 'context_digest' else 'absent-operation'
            with self.subTest(field=field), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        calls.clear()
        with patch.object(PaperService, '_all_pending_work', observe):
            self.assertEqual(saved.payload, snapshot(self.app).payload)
        self.assertEqual([self.history.commands, prefix.commands], calls)
        self.assertEqual(expected, [s.state() for s in self.app.understanding.sessions.values()])

    def test_changed_current_source_does_not_rebind_original_writing(self):
        old = first_episode(ai=True, close=False)
        self.app = TerminalWorkspace(old, ai_off=True)
        work = next(item for item in self.app.service.pending_work()['items'] if item['kind'] == 'understanding')
        session = self.app.understanding.open(work['id'])
        topic = session.state()['topics'][0]['id']
        session.edit(topic, 'Before later evidence')
        original = session.state()
        changed = old.append(command(old, 'record-evidence-event', {
            'event_id': 'explanation-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'A corrected synthetic loss.', 'value': '1.2',
            'rationale': 'Synthetic correction.', 'supersedes_id': 'event-1'}))
        self.app.paper.update_history(changed)
        app = self.reopen()
        again = app.understanding.open(work['id']).state()
        self.assertEqual(original['draft'], again['draft'])
        self.assertEqual(original['draft_basis'], again['draft_basis'])
        self.assertFalse(again['context_current'])
        self.assertEqual('Before later evidence', again['draft']['entries'][0]['text'])

    def test_active_editor_in_source_view_is_unfinished_and_not_kept(self):
        stored = []
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=stored.append,
            verify_unchanged=lambda: None), self.app)
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = self.app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        ui = understanding_ui(t); ui.open(self.items[0]); ui.key('enter'); ui.key('e')
        t.buffers[0].insert('작성 중인 설명'); ui.key('source')
        self.assertTrue(t.checkpoint())
        app = self.reopen(stored[-1])
        session = app.understanding.open(self.items[0]['id'])
        topic = session.state()['topics'][0]['id']
        self.assertEqual('', session.state()['draft']['entries'][0]['text'])
        self.assertEqual('작성 중인 설명', app.understanding.buffers[(self.items[0]['id'], topic)])
        self.assertNotIn('explanation drafts', excluded_work(self.app))
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('encrypted recovery', ui.draw(Frame(width, height)).plain())
        ui.key('escape'); ui.key('escape'); ui.key('escape'); ui.key('escape')
        self.assertTrue(t.checkpoint())
        self.assertNotIn('unfinished research editor text', excluded_work(self.app))

    def test_pristine_and_edited_back_text_do_not_create_pending_work(self):
        session, topic = self.open()
        app = self.reopen()
        self.assertFalse(app.understanding.sessions)
        session.edit(topic, 'Kept')
        key = (self.items[0]['id'], topic)
        self.app.understanding.buffers[key] = 'Earlier input'
        app = self.reopen(snapshot(self.app, ('understanding', (*key, 'Kept'))))
        self.assertFalse(app.understanding.buffers)
        self.assertEqual('Kept', app.understanding.open(key[0]).state()['draft']['entries'][0]['text'])

    def test_unknown_topic_duplicate_work_and_wrong_basis_fail_before_install(self):
        session, topic = self.open(); session.edit(topic, 'Retain me')
        self.app.understanding.buffers[(self.items[0]['id'], topic)] = ''
        saved = snapshot(self.app)
        for mutation in ('topic', 'duplicate', 'source', 'basis', 'position', 'current'):
            value = decode(saved.payload); layer = value['workspace']['understanding']
            if mutation == 'topic': layer['buffers'][0]['topic_id'] = 'missing'
            elif mutation == 'duplicate': layer['sessions'] *= 2
            elif mutation == 'source': layer['sessions'][0]['source']['digest'] = '0' * 64
            elif mutation == 'basis': layer['sessions'][0]['draft']['context_digest'] = '0' * 64
            elif mutation == 'position': layer['positions'][0]['index'] = 99
            else: layer['work_id'] = 'missing'
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        target = TerminalWorkspace(self.history)
        target.keep_note('Existing text')
        with self.assertRaises(ContractError): restore(target, saved)
        self.assertEqual('Existing text', target.note())

    def test_old_v3_workspace_remains_readable(self):
        self.app.keep_note('Old note')
        value = decode(snapshot(self.app).payload)
        value['schema'] = 'claimbranch.paper-work/v3'
        value['workspace']['schema'] = 'claimbranch.authoring-workspace/v2'
        value['workspace'].pop('understanding', None)
        value['workspace'].pop('review_writing', None)
        value['workspace'].pop('manuscript', None)
        app = self.reopen(PaperWork(canonical_bytes(value)))
        self.assertEqual('Old note', app.note())
        self.assertFalse(app.understanding.sessions)

    def test_equivalent_unicode_editor_does_not_block_other_writing(self):
        session, topic = self.open()
        session.edit(topic, 'café')
        key = (self.items[0]['id'], topic)
        self.app.keep_note('Keep this later note too')
        self.app.understanding.buffers[key] = 'cafe\u0301'
        app = self.reopen()
        self.assertFalse(app.understanding.buffers)
        self.assertEqual('Keep this later note too', app.note())
        app = self.reopen(snapshot(self.app, ('understanding', (*key, 'cafe\u0301'))))
        self.assertFalse(app.understanding.buffers)
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = self.app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (24, 80))
        ui = understanding_ui(t); ui.open(self.items[0]); ui.key('enter'); ui.key('e')
        # Return to the kept spelling through a different Unicode composition.
        t.buffers[0].text, t.buffers[0].initial = 'cafe\u0301', 'Earlier input'
        ui.key('escape')
        self.assertFalse(self.app.understanding.buffers)

    def test_restore_refuses_existing_explanation_only_writing(self):
        saved = snapshot(self.app)
        session, topic = self.open()
        for kept in (True, False):
            with self.subTest(kept=kept):
                session.edit(topic, 'Existing explanation' if kept else '')
                if not kept:
                    self.app.understanding.buffers[(self.items[0]['id'], topic)] = 'Still writing'
                before = session.snapshot(), dict(self.app.understanding.buffers)
                self.assertTrue(self.app.review.volatile_work())
                with self.assertRaises(ContractError): restore(self.app, saved)
                self.assertEqual(before, (session.snapshot(), self.app.understanding.buffers))

    def test_failed_or_oversized_checkpoint_retains_explanation_and_previous_save(self):
        saved = []
        recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append,
            verify_unchanged=lambda: None), self.app)
        session, topic = self.open()
        session.edit(topic, 'Earlier writing')
        recovery.save(self.app)
        previous = recovery.previous
        key = (self.items[0]['id'], topic)
        self.app.understanding.buffers[key] = '추가 작성 중'
        def fail(work): raise OSError('Synthetic pre-replacement failure')
        recovery.store.save = fail
        with self.assertRaises(OSError): recovery.save(self.app)
        self.assertEqual(previous, recovery.previous)
        self.assertEqual(previous, saved[0].payload)
        self.assertEqual('추가 작성 중', self.app.understanding.buffers[key])
        recovery.store.save = saved.append
        self.app.understanding.buffers[key] = '한' * 6000
        with self.assertRaises(ContractError): recovery.save(self.app)
        self.assertEqual('한' * 6000, self.app.understanding.buffers[key])
        self.assertEqual(previous, recovery.previous)
        self.assertEqual(1, len(saved))

    def test_project_association_carries_v4_explanation_unchanged(self):
        from claimbranch.application.project_work import ProjectWork, preview_association
        session, topic = self.open(); session.edit(topic, 'Original explanation', reuse_rationale=True)
        saved = snapshot(self.app)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            paper, work = root / 'paper', root / 'work'
            paper.mkdir(); work.mkdir(mode=0o700)
            subprocess.run(['/usr/bin/git', 'init', '-q', str(paper)], check=True)
            anchor = decode(self.history.seed)['anchor_id']
            (paper / 'paper.tex').write_text(f'% claimbranch:start id={anchor}\nSynthetic source.\n% claimbranch:end id={anchor}\n')
            project = ProjectWork.create(saved, preview_association(paper, 'paper.tex', anchor, work))
            restored = ProjectWork(project.payload)
            self.assertEqual(saved.payload, restored.work.payload)
            self.assertEqual(session.snapshot(), self.reopen(restored.work).understanding.sessions[self.items[0]['id']].snapshot())


if __name__ == '__main__': unittest.main()
