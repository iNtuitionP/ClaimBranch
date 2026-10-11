from dataclasses import asdict
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.paper_work_store import PaperWork, PaperWorkStore, WorkReopenRequired
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.application.paper_service import PaperService
from claimbranch.application.paper_understanding import PaperUnderstandingSession
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from tests.application.test_paper_operation import NOW, BINDINGS
from tests.application.test_paper_review_policy import ai_draft
from tests.contract.test_paper_episodes import first_episode


class PaperWorkContractTests(unittest.TestCase):
    def test_own_empty_paper_round_trip_does_not_fabricate_evidence(self):
        history = ResearchHistory.start_paper_series('own-project', 'My paper', 'thesis',
                                                    'My untested central argument.', 'anchor')
        work = PaperWork.create(history)
        restored = PaperWork(work.payload)
        self.assertEqual(history.manifest(), restored.history.manifest())
        self.assertEqual((), restored.history.commands)
        self.assertEqual(0, restored.history.watermark)
        self.assertFalse(restored.history.authorization_verified)
        self.assertIsNone(restored.review)

    def test_ai_text_without_reason_stays_unfinished_on_return(self):
        history = first_episode(merge=False, close=False)
        work = PaperWork.create(history, episode_id='episode', judgment=ai_draft())
        self.assertTrue(work.judgment.ai_influenced)
        self.assertIsNone(work.judgment.rationale)
        self.assertEqual(ai_draft(), PaperWork(work.payload).judgment)

    def test_unknown_version_accepted_flag_duplicate_and_foreign_origins_rejected(self):
        history = first_episode(merge=False, close=False)
        policy = PaperReviewPolicy(history, episode_id='episode')
        edge = next(r for r in history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        policy.revise_amendment(edge, sources=(ai_draft(),))
        work = PaperWork.from_policy(policy)
        for field, replacement in (('schema', 'claimbranch.paper-work/v2'),
                                   ('authorization_verified', True), ('project_id', 'foreign')):
            value = decode(work.payload)
            value[field] = replacement
            with self.subTest(field=field), self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))
        value = decode(work.payload)
        value['origins'] *= 2
        with self.assertRaises(ContractError):
            PaperWork(canonical_bytes(value))
        value['origins'] = value['origins'][:1]
        value['origins'][0]['episode_id'] = 'foreign'
        with self.assertRaises(ContractError):
            PaperWork(canonical_bytes(value))


@unittest.skipUnless(sys.platform == 'darwin', 'macOS CryptoKit adapter required')
class PaperWorkStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cipher = MacWorkCipher()
        cls.cipher.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cipher.__exit__(None, None, None)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claimbranch-work-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.key = os.urandom(32)
        history = first_episode(ai=True, merge=False, close=False)
        self.policy = PaperReviewPolicy(history, episode_id='episode')
        edge = next(r for r in history.view('alternative')['changes'] if r['id'] == 'edge-pruning')
        self.origin = self.policy.revise_amendment(edge, sources=(ai_draft(),))
        assessment = self.policy.merge(['edge-pruning'])
        self.review = self.policy.prepare_operation(assessment, disposition='deferred',
            operation_id='saved-merge', sealed_at=NOW, expires_at=NOW + 300, **BINDINGS)
        self.judgment = ai_draft().edit('아직 검토하는 중이다.', '추가 조건 확인이 필요하다.')
        self.work = PaperWork.from_policy(self.policy, judgment=self.judgment, review=self.review)

    def store(self, **overrides):
        return PaperWorkStore(self.root, cipher=self.cipher, key=self.key,
                             **{'project_id': 'project', **overrides})

    def test_restart_retains_full_ai_work_but_revokes_review_ownership(self):
        with self.store() as store:
            self.assertIsNone(store.load())
            store.save(self.work)
        with self.store() as store:
            restored = store.load()
            self.assertEqual(self.work.payload, restored.payload)
            self.assertEqual(asdict(self.judgment), asdict(restored.judgment))
            self.assertEqual(self.origin, restored.origins[0])
            self.assertFalse(restored.history.authorization_verified)
            self.assertEqual(self.review, restored.review)
            with self.assertRaises(ContractError):
                restored.new_policy().operation_candidate(restored.review, **BINDINGS)
        for path in self.root.iterdir():
            if path.is_file():
                self.assertNotIn('아직 검토하는 중이다.'.encode(), path.read_bytes())
                self.assertNotIn(b'proposal-policy', path.read_bytes())

    def test_partial_explanation_round_trip_retains_original_context(self):
        history = first_episode(ai=True, close=False)
        work_id = next(item['id'] for item in PaperService(history).pending_work()['items']
                       if item['kind'] == 'understanding')
        session = PaperUnderstandingSession(history, project_id='project', work_id=work_id)
        session.edit(session.state()['topics'][0]['id'], '조건은 더 확인해야 한다.')
        work = PaperWork.create(history, episode_id='episode', explanations=(session.snapshot(),))
        with self.store() as store:
            store.save(work)
        with self.store() as store:
            returned = store.load().explanations[0]
            self.assertEqual(session.snapshot(), returned.snapshot())
            self.assertFalse(returned.state()['closure_available'])
            self.assertEqual(0, returned.state()['accepted_debts_created'])

    def test_new_process_reads_same_checkpoint_with_key_only_on_stdin(self):
        with self.store() as store:
            store.save(self.work)
        code = '''import sys
from claimbranch.application.paper_work_store import PaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
with MacWorkCipher() as cipher:
    with PaperWorkStore(sys.argv[1], cipher=cipher, key=sys.stdin.buffer.read(32), project_id='project') as store:
        sys.stdout.buffer.write(store.load().payload)
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)],
                                input=self.key, capture_output=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.work.payload, result.stdout)

    def test_wrong_key_project_and_corruption_do_not_replace_file(self):
        with self.store() as store:
            store.save(self.work)
        path = self.root / 'work.cbw'
        good = path.read_bytes()
        for key, project in ((os.urandom(32), 'project'), (self.key, 'other')):
            with PaperWorkStore(self.root, cipher=self.cipher, key=key, project_id=project) as store:
                with self.assertRaises(ContractError):
                    store.load()
                with self.assertRaises(ContractError):
                    store.save(self.work)
            self.assertEqual(good, path.read_bytes())
        path.write_bytes(good[:-1] + bytes([good[-1] ^ 1]))
        bad = path.read_bytes()
        with self.store() as store, self.assertRaises(ContractError):
            store.load()
        self.assertEqual(bad, path.read_bytes())

    def test_failed_replace_preserves_prior_checkpoint_and_input(self):
        with self.store() as store:
            store.save(self.work)
            before = (self.root / 'work.cbw').read_bytes()
            with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('injected')):
                with self.assertRaises(ContractError):
                    store.save(self.work)
            self.assertEqual(before, (self.root / 'work.cbw').read_bytes())
            self.assertEqual(self.work.payload, store.load().payload)
            self.assertEqual({'work.cbw', 'work.lock'}, {p.name for p in self.root.iterdir()})

    def test_competing_session_and_external_replacement_are_rejected(self):
        with self.store() as store:
            store.save(self.work)
            with self.assertRaises(ContractError):
                with self.store():
                    pass
            path = self.root / 'work.cbw'
            different = self.cipher.seal(self.work.payload, self.key)
            path.write_bytes(different)
            with self.assertRaises(WorkReopenRequired):
                store.save(self.work)
            with self.assertRaises(WorkReopenRequired):
                store.verify_unchanged()
            self.assertEqual(different, path.read_bytes())

    def test_external_change_cannot_be_adopted_by_loading_same_session(self):
        with self.store() as store:
            store.save(self.work)
            path = self.root / 'work.cbw'; prior = path.read_bytes()
            path.write_bytes(self.cipher.seal(self.work.payload, self.key))
            with self.assertRaises(WorkReopenRequired): store.load()
            path.write_bytes(prior)
            for action in (store.load, store.verify_unchanged, lambda: store.save(self.work)):
                with self.assertRaises(WorkReopenRequired): action()
        with store:
            self.assertEqual(self.work.payload, store.load().payload)

    def test_changed_file_privacy_requires_reopen_even_after_shape_is_restored(self):
        with self.store() as store:
            store.save(self.work)
            path = self.root / 'work.cbw'; prior = path.read_bytes()
            path.chmod(0o644)
            with self.assertRaises(WorkReopenRequired): store.verify_unchanged()
            path.chmod(0o600)
            with self.assertRaises(WorkReopenRequired): store.load()
            with self.assertRaises(WorkReopenRequired): store.save(self.work)
            self.assertEqual(prior, path.read_bytes())
        with store:
            self.assertEqual(self.work.payload, store.load().payload)

    def test_cleanup_failure_preserves_typed_external_change_error(self):
        with self.store() as store:
            store.save(self.work)
            external = self.cipher.seal(self.work.payload, self.key)
            sync = store._sync
            def change_after_sync(descriptor):
                sync(descriptor)
                (self.root / 'work.cbw').write_bytes(external)
            with patch.object(store, '_sync', side_effect=change_after_sync), patch(
                    'claimbranch.application.paper_work_store.os.unlink', side_effect=OSError('cleanup failed')):
                with self.assertRaisesRegex(WorkReopenRequired, 'changed while saving'):
                    store.save(self.work)
            self.assertEqual(external, (self.root / 'work.cbw').read_bytes())
            with self.assertRaises(WorkReopenRequired): store.load()
            self.assertTrue(list(self.root.glob('.work-*')))
        with store:
            self.assertEqual(self.work.payload, store.load().payload)
            self.assertFalse(list(self.root.glob('.work-*')))

    def test_missing_independent_origin_or_unknown_version_rejects_review(self):
        for mutate in (lambda v: v.update(origins=[]), lambda v: v.update(schema='claimbranch.paper-work/v2')):
            value = decode(self.work.payload)
            mutate(value)
            with self.assertRaises(ContractError):
                PaperWork(canonical_bytes(value))

    def test_non_private_symlink_and_git_paths_fail_before_writing(self):
        for kind in ('mode', 'symlink', 'git'):
            with self.subTest(kind=kind):
                path = self.root / kind
                path.mkdir(mode=0o700)
                if kind == 'mode':
                    path.chmod(0o755)
                if kind == 'git':
                    (path / '.git').mkdir()
                if kind == 'symlink':
                    link = self.root / 'alias'
                    link.symlink_to(path, target_is_directory=True)
                    path = link
                with self.assertRaises(ContractError):
                    with PaperWorkStore(path, cipher=self.cipher, key=self.key, project_id='project'):
                        pass
                self.assertFalse((path / 'work.cbw').exists())

    def test_killed_writer_before_and_after_replace_reopens_complete_checkpoint(self):
        changed = PaperWork.from_policy(self.policy, judgment=ai_draft())
        code = '''import os, sys
from claimbranch.application.paper_work_store import PaperWork, PaperWorkStore, WorkReopenRequired
from claimbranch.application.work_cipher import MacWorkCipher
key = sys.stdin.buffer.read(32)
work = PaperWork(sys.stdin.buffer.read())
with MacWorkCipher() as cipher:
    with PaperWorkStore(sys.argv[1], cipher=cipher, key=key, project_id='project') as store:
        store.load()
        original = os.replace
        def crash(*args, **kwargs):
            if sys.argv[2] == 'after':
                original(*args, **kwargs)
            os._exit(77)
        os.replace = crash
        store.save(work)
'''
        for cut in ('before', 'after'):
            with self.subTest(cut=cut):
                with self.store() as store:
                    store.save(self.work)
                result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root), cut],
                    input=self.key + changed.payload, capture_output=True, timeout=90)
                self.assertEqual(77, result.returncode, result.stderr)
                with self.store() as store:
                    expected = self.work if cut == 'before' else changed
                    self.assertEqual(expected.payload, store.load().payload)
                self.assertEqual([], list(self.root.glob('.work-*')))

    def test_directory_sync_failure_requires_reopen_and_never_reports_success(self):
        real_sync = os.fsync
        def fail_directory(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError('injected directory sync failure')
            return real_sync(descriptor)
        with self.store() as store:
            store.save(self.work)
            with patch('claimbranch.application.paper_work_store.os.fsync', side_effect=fail_directory):
                with self.assertRaisesRegex(WorkReopenRequired, 'uncertain'):
                    store.save(self.work)
            with self.assertRaisesRegex(WorkReopenRequired, 'reopen'):
                store.load()
            with self.assertRaisesRegex(WorkReopenRequired, 'reopen'):
                store.save(self.work)
        with store:
            self.assertEqual(self.work.payload, store.load().payload)

    def test_file_symlink_hardlink_fifo_and_permission_changes_reject(self):
        target = self.root / 'untouched'
        target.write_bytes(b'do not replace')
        target.chmod(0o600)
        path = self.root / 'work.cbw'
        for kind in ('symlink', 'hardlink', 'fifo', 'public'):
            with self.subTest(kind=kind):
                if kind == 'symlink':
                    path.symlink_to(target)
                elif kind == 'hardlink':
                    os.link(target, path)
                elif kind == 'fifo':
                    os.mkfifo(path, 0o600)
                else:
                    path.write_bytes(b'invalid')
                    path.chmod(0o644)
                with self.store() as store:
                    with self.assertRaises(ContractError):
                        store.load()
                    with self.assertRaises(ContractError):
                        store.save(self.work)
                self.assertEqual(b'do not replace', target.read_bytes())
                path.unlink()

    def test_unsupported_plaintext_version_and_format_fail_without_overwrite(self):
        value = decode(self.work.payload)
        value['schema'] = 'claimbranch.paper-work/v9'
        encrypted = self.cipher.seal(canonical_bytes(value), self.key)
        path = self.root / 'work.cbw'
        for raw in (encrypted, b'CBRE\x00\x01' + encrypted[6:], encrypted[:20]):
            path.write_bytes(raw)
            path.chmod(0o600)
            with self.store() as store:
                with self.assertRaises(ContractError):
                    store.load()
                with self.assertRaises(ContractError):
                    store.save(self.work)
            self.assertEqual(raw, path.read_bytes())

    def test_stale_review_rejects_checkpoint_without_discarding_prior_saved_work(self):
        with self.store() as store:
            store.save(self.work)
            edge = self.origin.amendment
            edge['body']['rationale'] = 'The source changed after the original review.'
            self.policy.revise_amendment(edge)
            with self.assertRaises(ContractError):
                PaperWork.from_policy(self.policy, review=self.review)
            self.assertEqual(self.work.payload, store.load().payload)

    def test_new_review_must_be_explicit_after_reopen_even_before_expiry(self):
        with self.store() as store:
            store.save(self.work)
        with self.store() as store:
            restored = store.load()
        policy = restored.new_policy()
        self.assertEqual(self.review, policy.restore_operation(self.review.payload, **BINDINGS))
        with self.assertRaises(ContractError):
            policy.operation_candidate(self.review, **BINDINGS)
        assessment = policy.merge(['edge-pruning'])
        fresh = policy.prepare_operation(assessment, disposition='deferred', operation_id='new-merge',
            sealed_at=NOW, expires_at=NOW + 300, **{**BINDINGS, 'session_nonce': 'new-session'})
        candidate = policy.operation_candidate(fresh, **{**BINDINGS, 'session_nonce': 'new-session'})
        self.assertFalse(candidate.authorization_verified)

    def test_cipher_randomizes_ciphertext_and_rejects_oversize_and_bad_key(self):
        first = self.cipher.seal(self.work.payload, self.key)
        second = self.cipher.seal(self.work.payload, self.key)
        self.assertNotEqual(first, second)
        self.assertEqual(self.work.payload, self.cipher.open(second, self.key))
        for raw, key in ((b'x' * 262145, self.key), (b'x', b'short')):
            with self.assertRaises(ContractError):
                self.cipher.seal(raw, key)

    def test_full_sync_failure_before_replace_preserves_previous_checkpoint(self):
        import fcntl
        with self.store() as store:
            store.save(self.work)
            before = (self.root / 'work.cbw').read_bytes()
            with patch('fcntl.fcntl', side_effect=OSError('unsupported flush')) as flush:
                with self.assertRaises(ContractError):
                    store.save(self.work)
            self.assertEqual(fcntl.F_FULLFSYNC, flush.call_args.args[1])
            self.assertEqual(before, (self.root / 'work.cbw').read_bytes())
            self.assertEqual(self.work.payload, store.load().payload)

    def test_staging_cleanup_preserves_unrelated_linked_and_public_files(self):
        unrelated = self.root / '.work-my-notes'
        unrelated.write_bytes(b'keep')
        unrelated.chmod(0o600)
        linked = self.root / ('.work-' + 'a' * 32)
        linked.symlink_to(unrelated)
        hardlinked = self.root / ('.work-' + 'b' * 32)
        os.link(unrelated, hardlinked)
        public = self.root / ('.work-' + 'c' * 32)
        public.write_bytes(b'keep')
        public.chmod(0o644)
        orphan = self.root / ('.work-' + 'd' * 32)
        orphan.write_bytes(self.cipher.seal(self.work.payload, self.key)[:50])
        orphan.chmod(0o600)
        with self.store() as store:
            self.assertIsNone(store.load())
            self.assertFalse(orphan.exists())
            self.assertTrue(linked.is_symlink())
            self.assertTrue(hardlinked.exists())
            self.assertEqual(b'keep', unrelated.read_bytes())
            self.assertEqual(b'keep', public.read_bytes())


if __name__ == '__main__':
    unittest.main()
