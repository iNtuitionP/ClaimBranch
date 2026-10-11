"""Encrypted unfinished scientific writing retains its basis, never a live review."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from claimbranch.application.tui import Terminal, Frame
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_review_ui import review_ui
from claimbranch.application.tui_work_recovery import JudgmentRecovery, snapshot, restore, excluded_work
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.fixtures import replay_example


class ReviewWritingRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('recorded', series=True)
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.app.select('obs-1')
        self.t = self.terminal(self.app)

    def terminal(self, app):
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (42, 144))
        return t

    def fields(self):
        self.t.key('w'); self.t.key('c')
        ui = review_ui(self.t); ui.open_fields('claim-pruning-detail')
        return ui

    def answer(self):
        self.app.keep_draft('Limit the comparison to measured conditions.', 'Another mask has not run.')
        self.app.review.stage('claim-pruning-detail', {'statement': 'A limited claim.', 'scope': 'This split only.'})
        self.app.review.prepare_changes()
        self.t.key('w'); self.t.key('enter'); self.t.key('1')
        self.assertEqual('review-answer', self.t.modal)
        return review_ui(self.t)

    def reopen(self, work=None):
        work = snapshot(self.app) if work is None else work
        app = TerminalWorkspace(work.history, ai_off=True); restore(app, work)
        app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=lambda work: None,
            verify_unchanged=lambda: None), app)
        return app, self.terminal(app)

    def multiple_fields(self, length=9000):
        self.app.keep_draft('J' * length, 'R' * length)
        self.t.key('w'); self.t.key('c')
        ui = review_ui(self.t)
        records = [r['id'] for r in self.app.review.records().values()
                   if r['kind'] in ('claim', 'interpretation', 'experiment-plan', 'scientific-edge')]
        for key in records:
            ui.open_fields(key); self.t.buffers[0].insert(' unfinished'); self.t.key('escape')
        return records

    def test_one_batch_queries_shared_source_once_and_matches_independent_validation(self):
        from claimbranch.application import paper_review_writing_snapshot as module
        self.multiple_fields(length=80)
        rows = module.writing_snapshot(self.app)
        expected = [module.validate_basis(self.history, r['owner'], r['mode'], r['basis']) for r in rows]
        with patch.object(module, 'query', wraps=module.query) as querying:
            inputs, metadata = module.restore_writing(self.history, module.pack_writing(rows))
        self.assertEqual(1, querying.call_count)
        self.assertEqual(len(rows), len(inputs))
        self.assertEqual(expected, [module.baseline(m['basis']) for m in metadata.values()])
        # A new validation must check again; there is no cross-save cache.
        with patch.object(module, 'query', wraps=module.query) as querying:
            module.restore_writing(self.history, module.pack_writing(rows))
        self.assertEqual(1, querying.call_count)

    def test_original_sessions_query_once_each_and_match_workspace_restore(self):
        from claimbranch.application import paper_review_writing_snapshot as module
        from claimbranch.application.paper_workspace import PaperWorkspace
        from claimbranch.application.paper_workspace_snapshot import restore_session, session_snapshot
        from claimbranch.application.paper_service import PaperService
        self.multiple_fields(length=80)
        rows = module.writing_rows(module.pack_writing(module.writing_snapshot(self.app)))
        expected = []
        for row in rows:
            original = module.original_history(self.history, row['basis'])
            session = PaperWorkspace(original).draft(*row['owner'])
            restore_session(session, row['basis']['session'])
            expected.append(session_snapshot(session))
        sessions = []
        def restoring(session, value):
            restore_session(session, value)
            sessions.append(session)
        with patch.object(PaperService, 'query', autospec=True, side_effect=PaperService.query) as querying:
            with patch.object(module, 'restore_session', side_effect=restoring):
                module.restore_writing(self.history, module.pack_writing(rows))
        self.assertEqual(1 + len(rows), querying.call_count)
        self.assertEqual(expected, [session_snapshot(s) for s in sessions])
        self.assertEqual(len(rows), len({id(s) for s in sessions}))
        self.assertEqual(len(rows), len({id(s._service) for s in sessions}))
        self.assertEqual(len(rows), len({id(s._broker) for s in sessions}))
        for session in sessions:
            self.assertIsNone(session._changes_review)
            self.assertIsNone(session._outbound)
            self.assertFalse(session._adopted)
        sessions[0]._text = 'Only this historical session'
        self.assertEqual(expected[1]['text'], sessions[1]._text)

    def test_batch_keeps_distinct_prefixes_refs_and_each_owner_binding(self):
        from claimbranch.application import paper_review_writing_snapshot as module
        from claimbranch.core.research_history import ResearchHistory
        self.multiple_fields(length=80)
        rows = module.writing_snapshot(self.app)[:3]
        original = ResearchHistory.replay(self.history.seed, self.history.commands[:13])
        rows[0]['basis']['source']['commands'] = 13
        view = module.query(original, rows[0]['owner'])
        rows[0]['basis']['source']['digest'] = view['digest']
        rows[0]['basis']['session']['view_digest'] = view['digest']
        rows[1]['owner'][1] = 'alternative'
        view = module.query(self.history, rows[1]['owner'])
        rows[1]['basis']['source']['digest'] = view['digest']
        rows[1]['basis']['session']['view_digest'] = view['digest']
        expected = [module.validate_basis(self.history, r['owner'], r['mode'], r['basis']) for r in rows]
        with patch.object(module, 'query', wraps=module.query) as querying:
            _, metadata = module.restore_writing(self.history, module.pack_writing(rows))
        self.assertEqual(3, querying.call_count)
        self.assertEqual(expected, [module.baseline(m['basis']) for m in metadata.values()])
        # A later row sharing a valid projection must still prove its owner.
        rows = module.writing_snapshot(self.app)[:2]
        rows[-1]['owner'][2] = 'missing-source-owner'
        with self.assertRaises(ContractError): module.restore_writing(self.history, module.pack_writing(rows))

    def test_distinct_branch_groups_replay_each_original_prefix_once(self):
        from claimbranch.application import paper_review_writing_snapshot as module
        from claimbranch.core.research_history import ResearchHistory
        self.multiple_fields(length=80)
        rows = module.writing_snapshot(self.app)[:4]
        for row, count, ref in zip(rows, (13, 13, 12, 14), ('main', 'alternative', 'main', 'main')):
            original = ResearchHistory.replay(self.history.seed, self.history.commands[:count])
            row['owner'][1] = ref
            view = module.query(original, row['owner'])
            row['basis']['source'] = {'commands': count, 'digest': view['digest']}
            row['basis']['session']['view_digest'] = view['digest']
            module.validate_basis(self.history, row['owner'], row['mode'], row['basis'])
        for _ in range(4):
            if self.t.modal is None: break
            self.t.key('escape')
        self.answer(); self.t.buffers[0].insert(' Unfinished explanation'); self.t.key('escape')
        rows.append(next(r for r in module.writing_snapshot(self.app) if r['mode'] == 'explanation'))
        for row in rows:
            kept = module.validate_basis(self.history, row['owner'], row['mode'], row['basis'])
            self.assertEqual(len(kept), len(row['texts']))
            self.assertFalse(module.same_text(row['texts'], kept))
        expected_inputs = {(*r['owner'], r['mode']): r['texts'] for r in rows}
        expected_basis = {(*r['owner'], r['mode']): {'basis': r['basis'], 'field': r['field']} for r in rows}
        pooled = module.pack_writing(rows)
        for ordered in (pooled, module.pack_writing(list(reversed(rows)))):
            with patch.object(ResearchHistory, 'replay', wraps=ResearchHistory.replay) as replaying:
                restored = module.restore_writing(self.history, ordered)
            self.assertEqual(2, replaying.call_count)
            self.assertEqual({12, 13}, {len(c.args[1]) for c in replaying.call_args_list})
            self.assertEqual((expected_inputs, expected_basis), restored)
        # Sharing an immutable prefix cannot share branch projections or trust.
        bad = deepcopy(rows)
        bad[1]['basis']['source']['digest'] = bad[0]['basis']['source']['digest']
        with self.assertRaises(ContractError): module.restore_writing(self.history, module.pack_writing(bad))
        bad = deepcopy(rows)
        bad[2]['basis']['source']['digest'] = bad[0]['basis']['source']['digest']
        with self.assertRaises(ContractError): module.restore_writing(self.history, module.pack_writing(bad))
        bad = deepcopy(rows)
        bad[-1]['basis']['source']['commands'] = len(self.history.commands) + 1
        with self.assertRaises(ContractError): module.restore_writing(self.history, module.pack_writing(bad))

    def test_mixed_fields_answers_match_independent_rows_and_reject_corrupt_later_inputs(self):
        from claimbranch.application import paper_review_writing_snapshot as module
        self.multiple_fields(length=80)
        for _ in range(4):
            if self.t.modal is None: break
            self.t.key('escape')
        self.answer(); self.t.buffers[0].insert(' My unfinished answer'); self.t.key('escape')
        rows = module.writing_snapshot(self.app)
        self.assertEqual(1, sum(r['mode'] == 'explanation' for r in rows))
        self.assertEqual(1, len({(r['basis']['source']['commands'], *r['owner'][:2]) for r in rows}))
        for ordered in (rows, list(reversed(rows))):
            pooled = module.pack_writing(ordered)
            expected_inputs, expected_metadata = {}, {}
            for row in module.writing_rows(pooled):
                kept = module.validate_basis(self.history, row['owner'], row['mode'], row['basis'])
                self.assertEqual(len(kept), len(row['texts']))
                self.assertLess(row['field'], len(kept))
                self.assertFalse(module.same_text(row['texts'], kept))
                key = (*row['owner'], row['mode'])
                expected_inputs[key] = row['texts']
                expected_metadata[key] = {'basis': row['basis'], 'field': row['field']}
            self.assertEqual((expected_inputs, expected_metadata), module.restore_writing(self.history, pooled))
        for name in ('session', 'kind', 'request'):
            bad = deepcopy(rows)
            if name == 'request':
                row = next(r for r in bad if r['mode'] == 'explanation')
                bad.remove(row); bad.append(row)
                row['basis']['request']['selected_ids'] = ['missing-change']
            else:
                row = next(r for r in bad if r['mode'].startswith('change:'))
                bad.remove(row); bad.append(row)
                if name == 'session': row['basis']['session']['view_digest'] = '0' * 64
                else: row['basis']['record']['kind'] = 'interpretation'
            with self.subTest(name=name), self.assertRaises(ContractError):
                module.restore_writing(self.history, module.pack_writing(bad))

    def test_repeated_long_original_sessions_fit_without_dropping_input(self):
        records = self.multiple_fields()
        expected = deepcopy(self.app.review.unfinished_basis), deepcopy(self.app.review.unfinished)
        work = snapshot(self.app)
        value = decode(work.payload)
        self.assertEqual('claimbranch.paper-work/v7', value['schema'])
        layer = value['workspace']['review_writing']
        self.assertEqual(len(records), len(layer['inputs']))
        self.assertEqual(1, len(layer['sessions']))
        app, _ = self.reopen(work)
        self.assertEqual(expected, (app.review.unfinished_basis, app.review.unfinished))
        keys = list(app.review.unfinished_basis)
        app.review.unfinished_basis[keys[0]]['basis']['session']['text'] = 'Only this copy'
        self.assertEqual('J' * 9000, app.review.unfinished_basis[keys[1]]['basis']['session']['text'])
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())

    def test_pool_capacity_uses_stored_bytes_not_expanded_original_copies(self):
        self.multiple_fields(length=12000)
        work = snapshot(self.app)
        self.assertLess(len(work.payload), 262144)
        app, _ = self.reopen(work)
        self.assertEqual(self.app.review.unfinished_basis, app.review.unfinished_basis)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS Secure Enclave required')
    def test_long_shared_originals_reopen_from_device_in_a_fresh_process(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        records = self.multiple_fields()
        work = snapshot(self.app)
        with tempfile.TemporaryDirectory() as directory, MacWorkCipher() as cipher:
            with DevicePaperWorkStore.create(directory, cipher=cipher,
                    project_id=work.project_id, recovery_key=os.urandom(32)) as store:
                store.save(work)
            self.assertNotIn(b'J' * 9000, (Path(directory) / 'work.cbw').read_bytes())
            script = '''import hashlib, sys
from claimbranch.application.device_work_store import DevicePaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_work_recovery import restore
with MacWorkCipher() as cipher:
 with DevicePaperWorkStore(sys.argv[1], cipher=cipher, project_id=sys.argv[2]) as store:
  work = store.load()
  app = TerminalWorkspace(work.history, ai_off=True)
  restore(app, work)
  assert len(app.review.unfinished) == int(sys.argv[3])
  assert all(m['basis']['session']['text'] == 'J' * 9000 for m in app.review.unfinished_basis.values())
  assert app.review.session().get_changes_review() is None
  print(hashlib.sha256(work.payload).hexdigest())
'''
            result = subprocess.run([sys.executable, '-B', '-c', script, directory,
                work.project_id, str(len(records))], capture_output=True, timeout=100)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(hashlib.sha256(work.payload).hexdigest() + '\n', result.stdout.decode())

    def test_same_owner_different_earlier_judgments_stay_separate_and_old_files_read(self):
        self.app.keep_draft('First judgment', 'First reason')
        ui = self.fields(); self.t.buffers[0].insert(' first'); self.t.key('escape')
        self.app.keep_draft('Second judgment', 'Second reason')
        ui.open_fields('claim-comparison'); self.t.buffers[0].insert(' second'); self.t.key('escape')
        expected = deepcopy(self.app.review.unfinished_basis)
        saved = snapshot(self.app); value = decode(saved.payload)
        self.assertEqual(2, len(value['workspace']['review_writing']['sessions']))
        reordered = decode(saved.payload)
        reordered['workspace']['review_writing']['sessions'].reverse()
        with self.assertRaises(ContractError): PaperWork(canonical_bytes(reordered))
        app, _ = self.reopen(saved)
        self.assertEqual(expected, app.review.unfinished_basis)
        from claimbranch.application.paper_review_writing_snapshot import writing_snapshot
        for version in (5, 6):
            legacy = decode(saved.payload)
            legacy['schema'] = 'claimbranch.paper-work/v' + str(version)
            legacy['workspace']['schema'] = ('claimbranch.review-writing-workspace/v4' if version == 5
                                             else 'claimbranch.wording-workspace/v5')
            legacy['workspace']['review_writing'] = writing_snapshot(self.app)
            if version == 5: legacy['workspace'].pop('manuscript')
            raw = canonical_bytes(legacy)
            old = PaperWork(raw)
            self.assertEqual(raw, old.payload)
            reopened, _ = self.reopen(old)
            self.assertEqual(expected, reopened.review.unfinished_basis)
            self.assertEqual(self.app.review.unfinished, reopened.review.unfinished)

    def test_pool_integrity_and_per_input_binding_reject_before_install(self):
        self.multiple_fields(length=80)
        saved = snapshot(self.app)
        for name in ('hash', 'content', 'duplicate', 'dangling', 'unused', 'foreign-session', 'foreign-episode', 'source'):
            value = decode(saved.payload)
            layer = value['workspace']['review_writing']
            entry = layer['sessions'][0]
            if name == 'hash': entry['digest'] = '0' * 64
            elif name == 'content': entry['session']['text'] = 'Changed origin'
            elif name == 'duplicate': layer['sessions'].append(deepcopy(entry))
            elif name == 'dangling': layer['inputs'][-1]['basis']['session_digest'] = '0' * 64
            elif name == 'unused':
                extra = deepcopy(entry); extra['session']['text'] = 'An unused original'
                extra['digest'] = digest(extra['session']); layer['sessions'].append(extra)
            elif name == 'foreign-session':
                entry['session']['view_digest'] = '0' * 64
                entry['digest'] = digest(entry['session'])
                for row in layer['inputs']: row['basis']['session_digest'] = entry['digest']
            elif name == 'foreign-episode':
                from claimbranch.application.paper_workspace import PaperWorkspace
                from claimbranch.application.paper_workspace_snapshot import session_snapshot
                entry['session'] = session_snapshot(PaperWorkspace(self.history).draft('episode', 'main', 'obs-1'))
                self.assertNotEqual(layer['inputs'][0]['owner'][0], entry['session']['judgment']['episode_id'])
                entry['digest'] = digest(entry['session'])
                for row in layer['inputs']: row['basis']['session_digest'] = entry['digest']
            else: layer['inputs'][-1]['basis']['source']['digest'] = '0' * 64
            with self.subTest(name=name), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        # Even a corrupt last row cannot install an otherwise valid prefix.
        from claimbranch.application.paper_review_writing_snapshot import restore_writing
        with self.assertRaises(ContractError): restore_writing(self.history, layer)
        self.assertEqual(saved.payload, snapshot(self.app).payload)

    def test_empty_original_session_and_ai_origin_remain_explicit(self):
        self.fields(); self.t.buffers[0].insert(' pending'); self.t.key('escape')
        saved = snapshot(self.app)
        layer = decode(saved.payload)['workspace']['review_writing']
        self.assertEqual([], layer['sessions'])
        self.assertIsNone(layer['inputs'][0]['basis']['session_digest'])
        app, _ = self.reopen(saved)
        self.assertIsNone(next(iter(app.review.unfinished_basis.values()))['basis']['session'])
        self.app = TerminalWorkspace(self.history)
        self.app.select('obs-1'); self.t = self.terminal(self.app)
        self.app.keep_draft('Before AI', 'My reason')
        outbound = self.app.review.prepare_ai(['obs-1'], include_draft=True)
        self.app.review.begin_ai(outbound)
        self.app.review.complete_ai(self.app.work_key(), outbound['request']['request_id'])
        self.app.review.adopt_ai()
        self.app.keep_draft('Human revision after AI', 'Revised reason')
        session = self.app.review.session()
        from claimbranch.application.paper_workspace_snapshot import session_snapshot
        # Use a real synthetic adopted contribution chain, not an AI flag.
        self.t.key('w'); self.t.key('c')
        ui = review_ui(self.t); ui.open_fields('claim-comparison')
        self.t.buffers[0].insert(' pending'); self.t.key('escape')
        from claimbranch.core.research_schema import normalize
        from claimbranch.application.paper_workspace_snapshot import SESSION
        expected = normalize(session_snapshot(session), SESSION)
        app, _ = self.reopen()
        basis = app.review.unfinished_basis[(*self.app.work_key(), 'change:claim-comparison')]['basis']
        self.assertEqual(expected, basis['session'])
        self.assertTrue(basis['session']['judgment']['history'])

    def test_empty_fields_restore_under_original_owner_without_staging(self):
        self.fields()
        for b in self.t.buffers: b.text, b.cursor = '', 0
        self.t.key('escape'); self.t.key('escape')
        expected = deepcopy(self.app.review.unfinished)
        app, t = self.reopen()
        self.assertEqual(expected, app.review.unfinished)
        self.assertFalse(app.review.amendments)
        t.key('U'); self.assertIn('encrypted', t.draw_modal(Frame(80, 24)).plain())
        t.key('enter'); self.assertEqual(['', ''], [b.text for b in t.buffers])
        t.key('keep'); self.assertEqual('review-fields', t.modal)
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())

    def test_answer_restores_original_judgment_and_requires_new_exact_review(self):
        self.answer(); self.t.key(('paste', ' 추가 해석'))
        text = self.t.buffers[0].text
        self.t.key('escape')
        self.app.keep_draft('Later judgment.', 'Later reason.')
        app, t = self.reopen()
        t.key('U'); t.key('enter')
        self.assertEqual(text, t.buffers[0].text)
        t.key('source')
        self.assertEqual('review-writing-source', t.modal)
        screen = t.draw_modal(Frame(144, 42)).plain()
        self.assertIn('Another mask has not run.', screen)
        self.assertIn('Later reason.', screen)
        t.key(('paste', 'do not insert')); t.key('keep'); t.key('escape')
        self.assertEqual(text, t.buffers[0].text)
        t.key('keep'); self.assertEqual('review-answer', t.modal)
        self.assertIsNone(app.review.session().get_changes_review())
        t.key('escape'); t.key('R'); t.key('enter'); t.key('1')
        t.key('source'); t.key('r'); t.key('enter'); t.key('keep')
        self.assertEqual('answered', app.review.session().get_changes_review()['disposition'])
        self.assertFalse(app.review.unfinished)
        self.assertFalse(app.review.unfinished_basis)

    def test_active_source_inspection_is_checkpointed_and_does_not_apply_fields(self):
        saved = []
        self.app.recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append,
            verify_unchanged=lambda: None), self.app)
        self.fields(); self.t.key(('paste', ' 작성 중'))
        expected = [b.text for b in self.t.buffers]
        self.t.key('tab'); self.t.key('source')
        self.assertTrue(self.t.checkpoint())
        app, t = self.reopen(saved[-1]); t.key('U'); t.key('enter')
        self.assertEqual(expected, [b.text for b in t.buffers])
        self.assertEqual(1, t.field)
        self.assertFalse(app.review.amendments)
        self.assertNotIn('unfinished review writing', excluded_work(app))
        self.assertIn('encrypted', t.draw_modal(Frame(80, 24)).plain())

    def test_pristine_browsing_does_not_save_review_input(self):
        self.fields(); self.t.key('escape'); self.t.key('escape')
        app, _ = self.reopen()
        self.assertFalse(app.review.unfinished)
        self.assertFalse(app.review.unfinished_basis)

    def test_bad_basis_or_field_shape_fails_before_install(self):
        self.fields(); self.t.key(('paste', ' pending')); self.t.key('escape')
        saved = snapshot(self.app)
        for name in ('source', 'owner', 'kind', 'field', 'count', 'missing-field', 'duplicate'):
            value = decode(saved.payload); rows = value['workspace']['review_writing']['inputs']; row = rows[0]
            if name == 'source': row['basis']['source']['digest'] = '0' * 64
            elif name == 'owner': row['owner'][2] = 'missing-owner'
            elif name == 'kind': row['basis']['record']['kind'] = 'interpretation'
            elif name == 'field': row['field'] = 2
            elif name == 'count': row['texts'] = ['Only one field']
            elif name == 'missing-field': del row['basis']['record']['body']['scope']
            else: rows.append(deepcopy(row))
            with self.subTest(name=name), self.assertRaises(ContractError): PaperWork(canonical_bytes(value))
        target = TerminalWorkspace(self.history); target.keep_note('Do not replace')
        with self.assertRaises(ContractError): restore(target, saved)
        self.assertEqual('Do not replace', target.note())

    def test_changed_field_basis_requires_explicit_comparison_and_retains_undo(self):
        ui = self.fields(); self.t.key(('paste', ' Earlier unfinished idea'))
        expected = [b.text for b in self.t.buffers]
        self.t.key('escape'); self.t.key('escape')
        self.app.review.stage('claim-pruning-detail', {'statement': 'Changed elsewhere.', 'scope': 'New scope.'})
        app, t = self.reopen(); t.key('U'); t.key('enter')
        t.key('keep'); self.assertEqual('review-fields', t.modal)
        self.assertEqual('Changed elsewhere.', app.review.amendments[app.work_key()]['claim-pruning-detail']['body']['statement'])
        t.key(('paste', ' More'))
        buffer = t.buffers[0]; state = buffer.text, buffer.cursor, deepcopy(buffer.undo)
        t.key('source')
        for width, height in ((144, 42), (80, 24), (48, 18)):
            self.assertIn('WRITING CONTEXT', t.draw_modal(Frame(width, height)).plain())
        t.key(('paste', 'ignored')); t.key('keep')
        self.assertEqual(state, (buffer.text, buffer.cursor, buffer.undo))
        t.key('r'); self.assertEqual('review-writing-source', t.modal)
        t.key('enter'); t.key('keep')
        self.assertEqual('review-changes', t.modal)
        self.assertEqual(expected[0] + ' More', app.review.amendments[app.work_key()]['claim-pruning-detail']['body']['statement'])
        self.assertFalse(app.review.unfinished_basis)
        self.assertEqual(self.history.manifest(), app.paper.history.manifest())

    def test_unicode_equivalence_and_discard_leave_no_orphan_basis(self):
        self.app.review.stage('claim-pruning-detail', {'statement': 'café', 'scope': 'scope'})
        self.fields(); self.t.buffers[0].text = 'cafe\u0301'
        self.t.key('escape'); self.t.key('escape')
        self.assertFalse(self.app.review.unfinished)
        self.assertFalse(self.app.review.unfinished_basis)
        self.fields(); self.t.key(('paste', ' different')); self.t.key('escape'); self.t.key('escape')
        app, t = self.reopen(); t.key('U'); t.key('x'); t.key('x')
        self.assertFalse(app.review.unfinished)
        self.assertFalse(app.review.unfinished_basis)
        self.assertEqual('café', app.review.amendments[app.work_key()]['claim-pruning-detail']['body']['statement'])

    def test_later_evidence_retains_original_basis_until_explicit_refresh(self):
        from tests.contract.test_paper_episodes import first_episode, command
        self.history = first_episode(ai=True, close=False)
        self.app = TerminalWorkspace(self.history, ai_off=True); self.app.select('obs-1')
        self.t = self.terminal(self.app)
        self.fields(); self.t.key(('paste', ' Earlier idea')); self.t.key('escape'); self.t.key('escape')
        key = next(iter(self.app.review.unfinished))
        basis = deepcopy(self.app.review.unfinished_basis[key]['basis'])
        changed = self.history.append(command(self.history, 'record-evidence-event', {
            'event_id': 'review-input-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'Corrected synthetic loss.', 'value': '1.2',
            'rationale': 'Synthetic correction.', 'supersedes_id': 'event-1'}))
        self.app.paper.update_history(changed)
        app, t = self.reopen(); t.key('U'); t.key('enter')
        self.assertEqual(basis, app.review.unfinished_basis[key]['basis'])
        t.key('keep'); self.assertEqual('review-fields', t.modal)
        self.assertFalse(app.review.amendments)
        t.key('source'); t.key('r'); t.key('enter'); t.key('keep')
        self.assertEqual('review-changes', t.modal)
        self.assertEqual(changed.manifest(), app.paper.history.manifest())

    def test_failed_save_retains_active_review_input_and_prior_checkpoint(self):
        saved = []
        recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append,
            verify_unchanged=lambda: None), self.app)
        self.app.recovery = recovery
        recovery.save(self.app); previous = recovery.previous
        self.fields(); self.t.key(('paste', ' Must survive failure'))
        expected = [b.text for b in self.t.buffers]
        def fail(work): raise OSError('Synthetic pre-replacement failure')
        recovery.store.save = fail
        self.assertFalse(self.t.checkpoint())
        self.assertEqual(expected, [b.text for b in self.t.buffers])
        self.assertEqual(previous, recovery.previous)
        self.assertEqual(1, len(saved))
        self.assertIn('not confirmed', self.t.draw_modal(Frame(80, 24)).plain())
        recovery.store.save = saved.append
        self.assertTrue(self.t.checkpoint())
        app, t = self.reopen(saved[-1]); t.key('U'); t.key('enter')
        self.assertEqual(expected, [b.text for b in t.buffers])

    def test_live_unchanged_review_can_resume_without_creating_a_new_seal(self):
        self.answer(); self.t.key(('paste', ' My explanation'))
        prepared = self.app.review.session().get_changes_preview()
        self.t.key('escape'); self.t.key('U'); self.t.key('enter'); self.t.key('keep')
        reviewed = self.app.review.session().get_changes_review()
        self.assertEqual(prepared['digest'], reviewed['preview_digest'])
        self.assertFalse(reviewed['authorization_verified'])

    def test_merely_opening_new_answer_review_keeps_original_basis(self):
        self.answer(); self.t.key(('paste', ' Earlier answer')); self.t.key('escape')
        key = next(iter(self.app.review.unfinished))
        basis = deepcopy(self.app.review.unfinished_basis[key])
        self.app.keep_draft('Another judgment.', 'A different reason.')
        self.app.review.prepare_changes(); self.t.key('w'); self.t.key('enter'); self.t.key('1')
        self.t.key('escape')
        self.assertEqual(basis, self.app.review.unfinished_basis[key])
        app, _ = self.reopen()
        self.assertEqual(basis, app.review.unfinished_basis[key])

    def test_shortening_long_valid_existing_field_remains_recoverable(self):
        self.app.review.stage('claim-pruning-detail', {'statement': 'a' * 13000, 'scope': 'scope'})
        self.fields(); self.t.key('backspace'); self.t.key('escape'); self.t.key('escape')
        app, t = self.reopen(); t.key('U'); t.key('enter')
        self.assertEqual('a' * 12999, t.buffers[0].text)

    def test_existing_candidate_structure_survives_field_resume_and_keep(self):
        record = self.app.review.records()['claim-pruning-detail']
        record['body']['parent_ids'] = ['thesis']
        self.app.review.candidates().put(record)
        self.fields(); self.t.key(('paste', ' More precise')); self.t.key('escape'); self.t.key('escape')
        app, t = self.reopen(); t.key('U'); t.key('enter'); t.key('keep')
        kept = app.review.amendments[app.work_key()]['claim-pruning-detail']
        self.assertEqual(['thesis'], kept['body']['parent_ids'])
        self.assertTrue(kept['body']['statement'].endswith(' More precise'))

    def test_answer_binding_tamper_and_invalid_field_index_reject(self):
        self.answer(); self.t.key(('paste', ' Original answer')); self.t.key('escape')
        for name in ('selection', 'revision', 'field', 'missing'):
            value = decode(snapshot(self.app).payload); row = value['workspace']['review_writing']['inputs'][0]
            if name == 'selection': row['basis']['request']['selected_ids'] = ['unknown-change']
            elif name == 'revision': row['basis']['request']['draft_revision'] += 1
            elif name == 'field': row['field'] = 1
            else: del value['workspace']['review_writing']['sessions'][0]['session']['judgment']['history']
            with self.subTest(name=name), self.assertRaises(ContractError): PaperWork(canonical_bytes(value))

    def test_aggregate_limit_retains_all_work_and_does_not_advise_closing(self):
        self.app.keep_draft('j' * 12000, 'r' * 12000)
        self.app.review.stage('claim-pruning-detail', {'statement': 'A claim.', 'scope': 'A scope.'})
        self.app.review.prepare_changes()
        saved = []
        recovery = JudgmentRecovery(SimpleNamespace(load=lambda: None, save=saved.append,
            verify_unchanged=lambda: None), self.app)
        self.app.recovery = recovery; recovery.save(self.app); prior = recovery.previous
        self.fields(); self.t.key('escape'); self.t.key('escape')
        ui = review_ui(self.t)
        records = [key for key, record in self.app.review.records().items()
                   if record['kind'] in ('claim', 'interpretation', 'experiment-plan', 'scientific-edge')]
        self.assertGreaterEqual(len(records), 12)
        for index, record in enumerate(records[:12]):
            self.app.keep_draft(str(index).zfill(2) + 'j' * 11998, 'r' * 12000)
            ui.open_fields(record); self.t.key(('paste', ' Unfinished revision')); self.t.key('escape')
        expected = deepcopy(self.app.review.unfinished)
        from claimbranch.application.paper_review_writing_snapshot import writing_snapshot
        layer = writing_snapshot(self.app, pooled=True)
        self.assertEqual(12, len(layer['inputs']))
        self.assertEqual(12, len(layer['sessions']))
        self.assertFalse(self.t.checkpoint())
        self.assertEqual(expected, self.app.review.unfinished)
        self.assertEqual(prior, recovery.previous)
        self.assertEqual(1, len(saved))
        self.assertIn('Keep this session open', self.app.recovery_error)
        self.assertIn('canonical JSON byte limit exceeded', self.app.recovery_error)
        self.assertNotIn('close and reopen', self.app.recovery_error)

    def test_resume_restores_original_owner_after_another_judgment_is_selected(self):
        self.fields(); self.t.key(('paste', ' Original owner input')); self.t.key('escape'); self.t.key('escape')
        key = next(iter(self.app.review.unfinished)); expected = self.app.review.unfinished[key]
        self.app.select('claim-pruning-detail')
        self.app.keep_draft('A separate judgment.', 'A separate reason.')
        other = self.app.work_key()
        self.app.paper.link_work(other, [other[2], 'obs-1'])
        app, t = self.reopen(); t.key('U'); t.key('enter')
        self.assertEqual(key[:-1], app.work_key())
        self.assertEqual(expected, [b.text for b in t.buffers])
        self.assertEqual('A separate judgment.', app.paper._drafts[other].state()['draft']['text'])

    def test_old_v4_and_v3_workspaces_still_read(self):
        self.app.keep_note('Earlier note')
        for version, schema in ((4, 'claimbranch.explanation-workspace/v3'), (3, 'claimbranch.authoring-workspace/v2')):
            value = decode(snapshot(self.app).payload)
            value['schema'] = f'claimbranch.paper-work/v{version}'
            value['workspace']['schema'] = schema
            value['workspace'].pop('review_writing', None)
            value['workspace'].pop('manuscript', None)
            if version == 3: value['workspace'].pop('understanding', None)
            app, _ = self.reopen(PaperWork(canonical_bytes(value)))
            self.assertEqual('Earlier note', app.note())
            self.assertFalse(app.review.unfinished)


if __name__ == '__main__': unittest.main()
