"""Explicit manuscript association refresh; never scientific acceptance."""
from copy import deepcopy
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from claimbranch.application import project_work as module
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.paper_review_policy import PaperReviewPolicy
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_schema import normalize
from tests.application.test_paper_operation import NOW, BINDINGS
from tests.application.test_project_work import AssociationFixture
from tests.application.test_paper_review_policy import ai_draft
from tests.contract.test_paper_episodes import first_episode


class SourceRefreshTests(AssociationFixture, unittest.TestCase):
    def changed(self, project):
        self.manuscript.write_bytes(self.source + b'% edited outside ClaimBranch\n')
        return module.preview_source_refresh(project, self.preview())

    def test_refresh_preserves_exact_writing_and_both_source_snapshots(self):
        work = PaperWork.create(first_episode(ai=True, merge=False, close=False),
                                episode_id='episode', judgment=ai_draft())
        project = module.ProjectWork.create(work, self.preview())
        review = self.changed(project)
        display = review.display(project)
        self.assertNotEqual(display['before_source_digest'], display['after_source_digest'])
        self.assertEqual([], display['writes'])
        self.assertFalse(display['authorization_verified'])
        self.assertFalse(display['scientific_reconciliation_verified'])
        self.assertFalse(display['v1_readers_can_open_result'])
        self.assertEqual('claimbranch.project-work/v2', display['result_work_schema'])
        self.assertEqual(14, display['remaining_source_snapshots'])
        refreshed = project.refresh_source(review)
        value = decode(refreshed.payload)
        self.assertEqual('claimbranch.project-work/v2', value['schema'])
        self.assertEqual('source-refresh', value['transitions'][0]['kind'])
        self.assertEqual(decode(project.payload)['associations'][0], value['associations'][0])
        self.assertEqual(work.payload, refreshed.work.payload)
        self.assertTrue(refreshed.work.judgment.ai_influenced)
        self.assertFalse(refreshed.work.history.authorization_verified)
        self.assertEqual('unchanged-since-refresh', module.ProjectWork(refreshed.payload).source_status())
        self.assertEqual('source-changed-reconciliation-required', project.source_status())
        self.assertEqual([], list(self.workspace.iterdir()))

    def test_noop_wrong_paper_or_anchor_cannot_be_refresh(self):
        project = self.project()
        with self.assertRaises(ContractError):
            module.preview_source_refresh(project, self.preview())
        moved = self.root / 'moved'
        self.paper.rename(moved)
        (moved / 'paper.tex').write_bytes(self.source + b'% edited\n')
        with self.assertRaises(ContractError):
            module.preview_source_refresh(project, self.preview(paper_root=moved))
        with self.assertRaises(ContractError):
            project.relocate(self.preview(paper_root=moved))

    def test_old_review_remains_historical_and_cannot_follow_new_file(self):
        history = first_episode(ai=True, merge=False, close=False)
        policy = PaperReviewPolicy(history, episode_id='episode')
        original_digest = decode(self.preview().payload)['source']['source_digest']
        bindings = {**BINDINGS, 'manuscript_digest': original_digest}
        review = policy.prepare_operation(policy.merge(['edge-pruning']), disposition='deferred',
            entries=[], operation_id='merge', sealed_at=NOW, expires_at=NOW + 300, **bindings)
        work = PaperWork.from_policy(policy, judgment=ai_draft(), review=review)
        project = module.ProjectWork.create(work, self.preview())
        refresh = self.changed(project)
        result = project.refresh_source(refresh)
        self.assertEqual(work.payload, result.work.payload)
        self.assertEqual(review, result.work.review)
        changed_bindings = {**bindings, 'manuscript_digest': refresh.display(project)['after_source_digest']}
        with self.assertRaises(ContractError):
            policy.operation_candidate(review, **changed_bindings)
        with self.assertRaises(ContractError):
            result.work.new_policy().operation_candidate(review, **bindings)
        changed_work = project.with_work(PaperWork.from_policy(policy,
            judgment=ai_draft().edit('Changed judgment', 'New reason'), review=review))
        with self.assertRaises(ContractError):
            changed_work.refresh_source(refresh)

    def test_snapshot_bound_does_not_truncate_history(self):
        project = self.project()
        for index in range(15):
            self.manuscript.write_bytes(self.source + f'% edit {index}\n'.encode())
            project = project.refresh_source(module.preview_source_refresh(project, self.preview()))
        original = project.payload
        self.manuscript.write_bytes(self.source + b'% over bound\n')
        with self.assertRaisesRegex(ContractError, 'association history is full'):
            project.refresh_source(module.preview_source_refresh(project, self.preview()))
        self.assertEqual(original, project.payload)
        self.assertEqual(16, len(decode(project.payload)['associations']))

    def test_legacy_schema_rejects_refresh_and_v2_schema_is_closed(self):
        project = self.project()
        value = decode(project.refresh_source(self.changed(project)).payload)
        with self.assertRaises(ContractError):
            normalize(value, module.project_work_schema())
        self.assertEqual(value, normalize(value, module.project_work_schema(2)))
        value['authority'] = 'accepted'
        with self.assertRaises(ContractError):
            module.ProjectWork(canonical_bytes(value))

    def test_forged_noop_v2_relocation_is_not_a_valid_transition(self):
        project = self.project()
        value = decode(project.refresh_source(self.changed(project)).payload)
        last = value['associations'][-1]
        value['associations'].append(deepcopy(last))
        from claimbranch.core.canonical import digest
        value['transitions'].append({'kind': 'relocation', 'before': digest(last), 'after': digest(last)})
        with self.assertRaises(ContractError):
            module.ProjectWork(canonical_bytes(value))

    def test_legacy_moves_share_explicit_refresh_capacity(self):
        project = self.project()
        for index in range(15):
            moved = self.root / f'location-{index}'
            self.paper.rename(moved)
            self.paper = moved
            project = project.relocate(self.preview())
        self.manuscript = self.paper / 'paper.tex'
        self.manuscript.write_bytes(self.source + b'% edit after moves\n')
        preview = self.preview()
        with patch.object(module, '_source', side_effect=AssertionError('must refuse before source read')):
            with self.assertRaisesRegex(ContractError, 'association history is full'):
                module.preview_source_refresh(project, preview)

    def test_review_rejects_changed_project_source_and_workspace(self):
        project = self.project()
        review = self.changed(project)
        other = module.initialize_project(self.preview(), project_id='other', title='Other',
                                           thesis_id='thesis', thesis='Other argument')
        with self.assertRaises(ContractError):
            other.refresh_source(review)
        self.manuscript.write_bytes(self.source + b'% another edit\n')
        for action in (lambda: review.display(project), lambda: project.refresh_source(review)):
            with self.assertRaises(ContractError):
                action()
        review = module.preview_source_refresh(project, self.preview())
        self.workspace.rename(self.root / 'old-work')
        self.workspace.mkdir(mode=0o700)
        with self.assertRaises(ContractError):
            project.refresh_source(review)

    def test_v1_move_then_refresh_then_v2_move_retains_chain(self):
        project = self.project()
        moved = self.root / 'moved'
        self.paper.rename(moved)
        self.paper, self.manuscript = moved, moved / 'paper.tex'
        relocated = project.relocate(self.preview())
        refreshed = relocated.refresh_source(self.changed(relocated))
        self.paper.rename(self.root / 'again')
        self.paper = self.root / 'again'
        final = refreshed.relocate(self.preview())
        self.assertEqual(['relocation', 'source-refresh', 'relocation'],
                         [entry['kind'] for entry in decode(final.payload)['transitions']])
        self.assertEqual(project.work.payload, final.work.payload)
        self.assertEqual('unchanged-since-refresh', final.source_status())
        os.utime(self.paper / 'paper.tex', ns=(1000000000, 1000000000))
        self.assertEqual('unchanged-content-since-refresh', final.source_status())

    def test_tampered_transition_and_legacy_downgrade_are_refused(self):
        project = self.project()
        value = decode(project.refresh_source(self.changed(project)).payload)
        for edit in ('kind', 'before', 'after', 'missing', 'foreign-source', 'downgrade'):
            bad = deepcopy(value)
            if edit in ('kind', 'before', 'after'):
                bad['transitions'][0][edit] = 'relocation' if edit == 'kind' else '0' * 64
            elif edit == 'missing':
                bad['transitions'] = []
            elif edit == 'foreign-source':
                bad['associations'][-1]['root'] = os.fsencode(self.root / 'foreign').hex()
            else:
                bad['schema'] = 'claimbranch.project-work/v1'
                del bad['transitions']
            with self.subTest(edit=edit), self.assertRaises(ContractError):
                module.ProjectWork(canonical_bytes(bad))


@unittest.skipUnless(sys.platform == 'darwin', 'macOS Secure Enclave required')
class SourceRefreshPersistenceTests(AssociationFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cipher = MacWorkCipher().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cipher.__exit__(None, None, None)

    def test_exact_review_required_save_failure_and_restart_preserve_work(self):
        project, initial = self.project(), self.preview()
        recovery = os.urandom(32)
        with module.ProjectWorkStore.create(self.workspace, cipher=self.cipher,
                                            project_id='project', recovery_key=recovery) as store:
            store.save(project, preview=initial)
            prior = (self.workspace / 'work.cbw').read_bytes()
            self.manuscript.write_bytes(self.source + b'% edited\n')
            preview = self.preview()
            review = module.preview_source_refresh(project, preview)
            refreshed = project.refresh_source(review)
            elsewhere = self.root / 'other-work'
            elsewhere.mkdir(mode=0o700)
            foreign_review = module.preview_source_refresh(project, self.preview(workspace=elsewhere))
            with self.assertRaises(ContractError):
                store.save(project.refresh_source(foreign_review), source_review=foreign_review)
            with self.assertRaises(ContractError):
                store.save(refreshed, preview=preview)
            with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('full')):
                with self.assertRaises(ContractError):
                    store.save(refreshed, source_review=review)
            self.assertEqual(prior, (self.workspace / 'work.cbw').read_bytes())
            store.save(refreshed, source_review=review)
            # Already consumed comparison cannot be replayed against the new checkpoint.
            with self.assertRaises(ContractError):
                store.save(refreshed, source_review=review)
            with self.assertRaises(ContractError):
                store.save(project)
            backup = store.backup(verify_recovery_key=recovery)
        with module.ProjectWorkStore(self.workspace, cipher=self.cipher, project_id='project') as store:
            self.assertEqual(refreshed.payload, store.load().payload)
            store.save(refreshed)
        code = '''import sys
from claimbranch.application.project_work import ProjectWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
with MacWorkCipher() as cipher:
    with ProjectWorkStore(sys.argv[1], cipher=cipher, project_id='project') as store:
        sys.stdout.buffer.write(store.load().payload)
'''
        run = subprocess.run([sys.executable, '-B', '-c', code, str(self.workspace)],
                             input=b'', capture_output=True, timeout=90)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual(refreshed.payload, run.stdout)
        restored = self.root / 'restore'
        restored.mkdir(mode=0o700)
        self.manuscript.unlink()
        result = module.ProjectWorkStore.restore_backup(backup, restored, cipher=self.cipher,
                                                       project_id='project', recovery_key=recovery)
        self.assertEqual(refreshed.payload, result.payload)
        self.assertEqual('unavailable-or-unsupported', result.source_status())

    def test_changed_source_and_external_checkpoint_reject_save(self):
        project, preview = self.project(), self.preview()
        with module.ProjectWorkStore.create(self.workspace, cipher=self.cipher,
                project_id='project', recovery_key=os.urandom(32)) as store:
            store.save(project, preview=preview)
            old = (self.workspace / 'work.cbw').read_bytes()
            self.manuscript.write_bytes(self.source + b'% edited\n')
            review = module.preview_source_refresh(project, self.preview())
            refreshed = project.refresh_source(review)
            self.manuscript.write_bytes(self.source + b'% changed after review\n')
            with self.assertRaises(ContractError):
                store.save(refreshed, source_review=review)
            self.assertEqual(old, (self.workspace / 'work.cbw').read_bytes())
            review = module.preview_source_refresh(project, self.preview())
            refreshed = project.refresh_source(review)
            replaced = old[:-1] + bytes([old[-1] ^ 1])
            (self.workspace / 'work.cbw').write_bytes(replaced)
            with self.assertRaises(ContractError):
                store.save(refreshed, source_review=review)
            self.assertEqual(replaced, (self.workspace / 'work.cbw').read_bytes())

    def test_crafted_v1_noop_cannot_consume_another_snapshot(self):
        project, preview = self.project(), self.preview()
        value = decode(project.payload)
        value['associations'].append(deepcopy(value['associations'][-1]))
        legacy = module.ProjectWork(canonical_bytes(value))  # old v1 remains readable
        with module.ProjectWorkStore.create(self.workspace, cipher=self.cipher,
                project_id='project', recovery_key=os.urandom(32)) as store:
            store.save(project, preview=preview)
            previous = (self.workspace / 'work.cbw').read_bytes()
            with self.assertRaises(ContractError):
                store.save(legacy, preview=preview)
            self.assertEqual(previous, (self.workspace / 'work.cbw').read_bytes())

    def test_editor_after_last_recheck_is_detected_without_authority(self):
        project, preview = self.project(), self.preview()
        with module.ProjectWorkStore.create(self.workspace, cipher=self.cipher,
                project_id='project', recovery_key=os.urandom(32)) as store:
            store.save(project, preview=preview)
            self.manuscript.write_bytes(self.source + b'% reviewed edit\n')
            review = module.preview_source_refresh(project, self.preview())
            refreshed = project.refresh_source(review)
            with self.assertRaises(ContractError):
                store.save(refreshed, source_review=review, preview=self.preview())
            seal = store._codec.seal

            def edit_after_check(raw):
                encrypted = seal(raw)
                self.manuscript.write_bytes(self.source + b'% later external edit\n')
                return encrypted

            with patch.object(store._codec, 'seal', side_effect=edit_after_check):
                store.save(refreshed, source_review=review)
            saved = store.load()
            self.assertEqual(refreshed.payload, saved.payload)
            self.assertEqual('source-changed-reconciliation-required', saved.source_status())
            self.assertFalse(saved.work.history.authorization_verified)


if __name__ == '__main__':
    unittest.main()
