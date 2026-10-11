from pathlib import Path
import subprocess
import tempfile
import unittest

from claimbranch.application.project_work import preview_association, initialize_project

import os
import shutil
import sys
from unittest.mock import patch

from claimbranch.application.project_work import ProjectWork, ProjectWorkStore
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.device_work_store import DevicePaperWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from tests.application.test_paper_review_policy import ai_draft
from tests.contract.test_paper_episodes import first_episode



class ProjectAssociationTests(unittest.TestCase):
    def test_preview_is_read_only_and_initialization_has_no_fabricated_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            paper, workspace = root / 'paper', root / 'work'
            paper.mkdir()
            workspace.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True)
            source = b'% claimbranch:start id=anchor\nAn unresolved thesis.\n% claimbranch:end id=anchor\n'
            (paper / 'paper.tex').write_bytes(source)
            preview = preview_association(paper, 'paper.tex', 'anchor', workspace)
            self.assertEqual([], list(workspace.iterdir()))
            project = initialize_project(preview, project_id='project', title='New paper',
                                         thesis_id='thesis', thesis='An untested argument.')
            self.assertEqual((), project.work.history.commands)
            self.assertFalse(project.work.history.authorization_verified)
            self.assertEqual(source, (paper / 'paper.tex').read_bytes())
            self.assertEqual([], list(workspace.iterdir()))


class AssociationFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='claimbranch-association-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.paper, self.workspace = self.root / 'paper', self.root / 'work'
        self.paper.mkdir()
        self.workspace.mkdir(mode=0o700)
        subprocess.run(['/usr/bin/git', 'init', '-q', str(self.paper)], check=True)
        self.source = b'% claimbranch:start id=anchor\nA synthetic statement.\n% claimbranch:end id=anchor\n'
        self.manuscript = self.paper / 'paper.tex'
        self.manuscript.write_bytes(self.source)

    def preview(self, **changes):
        return preview_association(**{'paper_root': self.paper, 'manuscript': 'paper.tex',
                                     'anchor_id': 'anchor', 'workspace': self.workspace, **changes})

    def project(self, preview=None):
        return initialize_project(preview or self.preview(), project_id='project', title='A new paper',
                                  thesis_id='thesis', thesis='An unresolved argument.')


class AssociationBoundaryTests(AssociationFixture, unittest.TestCase):
    def test_pooled_work_versions_preserve_association_transitions(self):
        from claimbranch.application.project_work import preview_source_refresh, project_work_schema
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.application.tui_project import prepare_project
        old = prepare_project(self.preview(), project_id='project', title='A new paper',
                              thesis='An unresolved argument.', question='What remains unknown?')
        moved = self.root / 'moved'
        self.paper.rename(moved); self.paper = moved; self.manuscript = moved / 'paper.tex'
        relocated = old.relocate(self.preview())
        app = TerminalWorkspace(relocated.work.history, ai_off=True)
        app.keep_note('Retained Korean note 한글')
        work = snapshot(app)
        upgraded = relocated.with_work(work)
        value = decode(upgraded.payload)
        self.assertEqual('claimbranch.project-work/v3', value['schema'])
        self.assertEqual(work.payload, upgraded.work.payload)
        self.assertEqual(decode(relocated.payload)['associations'], value['associations'])
        self.assertEqual(['relocation'], [row['kind'] for row in value['transitions']])
        self.assertEqual('claimbranch.project-work/v1', decode(relocated.payload)['schema'])
        for version in (1, 2):
            from claimbranch.core.research_schema import normalize
            with self.subTest(version=version), self.assertRaises(ContractError):
                normalize(value, project_work_schema(version))
        self.manuscript.write_bytes(self.source + b'% changed\n')
        review = preview_source_refresh(upgraded, self.preview())
        self.assertEqual('claimbranch.project-work/v3', review.display(upgraded)['result_work_schema'])
        refreshed = upgraded.refresh_source(review)
        self.assertEqual('claimbranch.project-work/v3', decode(refreshed.payload)['schema'])
        self.assertEqual(work.payload, refreshed.work.payload)
        self.assertEqual(['relocation', 'source-refresh'],
                         [row['kind'] for row in decode(refreshed.payload)['transitions']])
        # A v2 original refresh also upgrades only on explicit new-work save.
        legacy_review = preview_source_refresh(relocated, self.preview())
        legacy = relocated.refresh_source(legacy_review)
        self.assertEqual('claimbranch.project-work/v2', decode(legacy.payload)['schema'])
        self.assertEqual(decode(refreshed.payload)['transitions'],
                         decode(legacy.with_work(work).payload)['transitions'])
        created = ProjectWork.create(work, self.preview())
        self.assertEqual([], decode(created.payload)['transitions'])
        target = TerminalWorkspace(created.work.history, ai_off=True)
        restore(target, created.work)
        self.assertEqual('Retained Korean note 한글', target.note())

    def test_preview_rejects_source_and_workspace_replacement(self):
        preview = self.preview()
        self.manuscript.write_bytes(self.source.replace(b'synthetic', b'changed'))
        with self.assertRaises(ContractError):
            self.project(preview)
        self.manuscript.write_bytes(self.source)
        preview = self.preview()
        self.workspace.rename(self.root / 'old-work')
        self.workspace.mkdir(mode=0o700)
        with self.assertRaises(ContractError):
            preview.recheck()
        self.assertEqual([], list(self.workspace.iterdir()))

    def test_git_environment_cannot_redirect_selected_root(self):
        with patch.dict(os.environ, {'GIT_DIR': '/missing', 'GIT_WORK_TREE': '/missing',
                                    'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.bare',
                                    'GIT_CONFIG_VALUE_0': 'true'}):
            self.assertEqual(str(self.paper), self.preview().display()['paper_root'])
        self.manuscript.unlink()
        shutil.rmtree(self.paper / '.git')
        (self.paper / '.git').mkdir()
        with self.assertRaises(ContractError):
            self.preview()

    def test_invalid_placement_and_marker_are_no_write(self):
        inside = self.paper / 'workspace'
        inside.mkdir(mode=0o700)
        for directory in (inside, self.root / 'missing'):
            with self.subTest(directory=directory.name), self.assertRaises(ContractError):
                self.preview(workspace=directory)
        for source in (b'no markers', self.source * 2, self.source.replace(b'\n', b'\r\n'),
                       self.source + b'\xff', b'a' * 65537):
            self.manuscript.write_bytes(source)
            with self.subTest(size=len(source)), self.assertRaises(ContractError):
                self.preview()
            self.assertEqual(source, self.manuscript.read_bytes())
        self.assertEqual([], list(self.workspace.iterdir()))

    def test_rejects_links_special_files_and_escaping_paths(self):
        for path in ('../paper/paper.tex', str(self.manuscript), './paper.tex', '.git/paper.tex'):
            with self.subTest(path=path), self.assertRaises(ContractError):
                self.preview(manuscript=path)
        nested = self.paper / 'nested'
        nested.symlink_to(self.paper, target_is_directory=True)
        with self.assertRaises(ContractError):
            self.preview(manuscript='nested/paper.tex')
        self.manuscript.rename(self.paper / 'original.tex')
        self.manuscript.symlink_to('original.tex')
        with self.assertRaises(ContractError):
            self.preview()
        self.manuscript.unlink()
        os.link(self.paper / 'original.tex', self.manuscript)
        with self.assertRaises(ContractError):
            self.preview()
        self.manuscript.unlink()
        os.mkfifo(self.manuscript)
        with self.assertRaises(ContractError):
            self.preview()

    def test_unicode_path_bytes_survive_canonical_roundtrip(self):
        # Decomposed Korean is intentionally not normalized by our JSON layer.
        moved = self.root / '\u1112\u1161\u11ab paper'
        self.paper.rename(moved)
        self.paper = moved
        project = self.project()
        self.assertEqual('unchanged', ProjectWork(project.payload).source_status())
        self.assertEqual(os.fsencode(moved).hex(), decode(project.payload)['associations'][0]['root'])

    def test_explicit_move_preserves_work_missing_source_stays_readable(self):
        original = self.project()
        moved = self.root / 'moved'
        self.paper.rename(moved)
        self.assertEqual('unavailable-or-unsupported', original.source_status())
        self.assertEqual((), ProjectWork(original.payload).work.history.commands)
        preview = self.preview(paper_root=moved)
        relocated = original.relocate(preview)
        self.assertEqual(original.work.payload, relocated.work.payload)
        self.assertEqual(2, len(decode(relocated.payload)['associations']))
        self.assertEqual('unchanged', relocated.source_status())
        (moved / 'paper.tex').write_bytes(self.source + b'% later edit\n')
        self.assertEqual('source-changed-reconciliation-required', relocated.source_status())
        with self.assertRaises(ContractError):
            relocated.relocate(self.preview(paper_root=moved))

    def test_unknown_and_foreign_envelopes_cannot_change_authority(self):
        project = self.project()
        for field, value in (('schema', 'claimbranch.project-work/v2'), ('project_id', 'foreign'),
                             ('authorization_verified', True), ('authority', 'accepted')):
            malformed = decode(project.payload)
            malformed[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                ProjectWork(canonical_bytes(malformed))
        malformed = decode(project.payload)
        malformed['associations'][0]['anchor_id'] = 'wrong-anchor'
        with self.assertRaises(ContractError):
            ProjectWork(canonical_bytes(malformed))
        with self.assertRaises(ContractError):
            PaperWork(project.payload)
        with self.assertRaises(ContractError):
            ProjectWork(project.work.payload)


@unittest.skipUnless(sys.platform == 'darwin', 'macOS Secure Enclave required')
class ProjectPersistenceTests(AssociationFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cipher = MacWorkCipher().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cipher.__exit__(None, None, None)

    def create(self):
        self.recovery = os.urandom(32)
        return ProjectWorkStore.create(self.workspace, cipher=self.cipher,
                                       project_id='project', recovery_key=self.recovery)

    def open(self):
        return ProjectWorkStore(self.workspace, cipher=self.cipher, project_id='project')

    def test_native_explicit_pooled_save_upgrades_legacy_and_creates_fresh_wrapper(self):
        from claimbranch.application.tui_project import prepare_project, project_workspace
        from claimbranch.application.tui_work_recovery import snapshot
        project = prepare_project(self.preview(), project_id='project', title='A new paper',
                                  thesis='An unresolved argument.', question='What remains unknown?')
        with self.create() as store:
            store.save(project, preview=self.preview())
            moved = self.root / 'moved'
            self.paper.rename(moved); self.paper = moved; self.manuscript = moved / 'paper.tex'
            preview = self.preview(); project = project.relocate(preview)
            store.save(project, preview=preview)
            app = project_workspace(project); app.keep_note('Retained writing')
            upgraded = project.with_work(snapshot(app))
            # Merely adding v2 transitions without refresh stays forbidden.
            invalid = decode(project.payload)
            invalid['schema'] = 'claimbranch.project-work/v2'
            invalid['transitions'] = decode(upgraded.payload)['transitions']
            with self.assertRaises(ContractError): store.save(ProjectWork(canonical_bytes(invalid)))
            store.save(upgraded)
            self.assertEqual(upgraded.payload, store.load().payload)
        with self.open() as store:
            self.assertEqual(upgraded.payload, store.load().payload)
        fresh = self.root / 'fresh'; fresh.mkdir(mode=0o700)
        preview = self.preview(workspace=fresh)
        created = ProjectWork.create(upgraded.work, preview)
        with ProjectWorkStore.create(fresh, cipher=self.cipher, project_id='project',
                                    recovery_key=os.urandom(32)) as store:
            store.save(created, preview=preview)
            self.assertEqual(created.payload, store.load().payload)

    def test_native_restart_ai_retention_backup_missing_source_and_relocation(self):
        # Source-bound AI history is preserved without turning it into authority.
        work = PaperWork.create(first_episode(ai=True, merge=False, close=False),
                                episode_id='episode', judgment=ai_draft())
        preview = self.preview()
        project = ProjectWork.create(work, preview)
        with self.create() as store:
            store.save(project, preview=preview)
            backup = store.backup(verify_recovery_key=self.recovery)
        self.assertNotIn(b'A synthetic statement', backup)
        self.assertNotIn(os.fsencode(self.paper), backup)
        with self.open() as store:
            self.assertEqual(project.payload, store.load().payload)
        with DevicePaperWorkStore(self.workspace, cipher=self.cipher, project_id='project') as old:
            with self.assertRaises(ContractError):
                old.load()
        code = '''import sys
from claimbranch.application.project_work import ProjectWorkStore
from claimbranch.application.work_cipher import MacWorkCipher
with MacWorkCipher() as cipher:
    with ProjectWorkStore(sys.argv[1], cipher=cipher, project_id='project') as store:
        sys.stdout.buffer.write(store.load().payload)
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.workspace)],
                                input=b'', capture_output=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(project.payload, result.stdout)
        moved, restored = self.root / 'moved', self.root / 'restored'
        self.paper.rename(moved)
        restored.mkdir(mode=0o700)
        with patch.object(self.cipher, 'open_work_key', side_effect=ContractError('old device absent')):
            recovered = ProjectWorkStore.restore_backup(backup, restored, cipher=self.cipher,
                project_id='project', recovery_key=self.recovery)
        self.assertEqual(project.payload, recovered.payload)
        self.assertEqual('unavailable-or-unsupported', recovered.source_status())
        self.assertEqual(backup, (self.workspace / 'work.cbw').read_bytes())
        preview = self.preview(paper_root=moved, workspace=restored)
        relocated = recovered.relocate(preview)
        with ProjectWorkStore(restored, cipher=self.cipher, project_id='project') as store:
            store.save(relocated, preview=preview)
            self.assertTrue(store.load().work.judgment.ai_influenced)
            self.assertFalse(store.load().work.history.authorization_verified)
            with self.assertRaises(ContractError):
                store.save(recovered)
        self.assertEqual(self.source, (moved / 'paper.tex').read_bytes())

    def test_wrong_workspace_stale_preview_and_failed_save_leave_checkpoint(self):
        preview, project = self.preview(), self.project()
        with self.create() as store:
            with self.assertRaises(ContractError):
                store.save(project)
            elsewhere = self.root / 'elsewhere'
            elsewhere.mkdir(mode=0o700)
            with self.assertRaises(ContractError):
                store.save(project, preview=self.preview(workspace=elsewhere))
            self.assertFalse((self.workspace / 'work.cbw').exists())
            store.save(project, preview=preview)
            original = (self.workspace / 'work.cbw').read_bytes()
            moved = self.root / 'moved'
            self.paper.rename(moved)
            new_preview = self.preview(paper_root=moved)
            relocated = project.relocate(new_preview)
            (moved / 'paper.tex').write_bytes(self.source + b'% changed')
            with self.assertRaises(ContractError):
                store.save(relocated, preview=new_preview)
            self.assertEqual(original, (self.workspace / 'work.cbw').read_bytes())
            # Writing work remains possible with unavailable/changed source.
            with patch('claimbranch.application.paper_work_store.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(ContractError):
                    store.save(project)
            self.assertEqual(original, (self.workspace / 'work.cbw').read_bytes())
            store.save(project)
            # An unexpected checkpoint replacement cannot be silently loaded by save.
            (self.workspace / 'work.cbw').write_bytes(original)
            with self.assertRaises(ContractError):
                store.save(project)


    def test_first_save_cannot_introduce_unchecked_association_history(self):
        preview, project = self.preview(), self.project()
        value = decode(project.payload)
        prior = dict(value['associations'][0])
        prior['root'] = os.fsencode(self.root / 'unseen-paper').hex()
        value['associations'].insert(0, prior)
        forged = ProjectWork(canonical_bytes(value))
        with self.create() as store:
            with self.assertRaises(ContractError):
                store.save(forged, preview=preview)
            self.assertFalse((self.workspace / 'work.cbw').exists())


class RetainedWorkTests(AssociationFixture, unittest.TestCase):
    def test_work_update_cannot_erase_recorded_context(self):
        history = first_episode(ai=True, merge=False, close=False)
        original = ProjectWork.create(PaperWork.create(history), self.preview())
        truncated = PaperWork.create(type(history).replay(history.seed, ()))
        with self.assertRaises(ContractError):
            original.with_work(truncated)
        updated = original.with_work(PaperWork.create(history, episode_id='episode', judgment=ai_draft()))
        self.assertTrue(updated.work.judgment.ai_influenced)
        self.assertEqual(original.work.history.manifest(), updated.work.history.manifest())

    def test_existing_versioned_workspace_is_retained_byte_for_byte(self):
        # Read-only compatibility exercise; no changes to the other owner's UI.
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.fixtures import replay_merge_example
        app = TerminalWorkspace(replay_merge_example('manual'))
        app.select('obs-1')
        app.keep_draft('아직 판단 중', '')
        app.keep_note('근거를 다시 확인')
        work = snapshot(app, ('edit', ['미완료 문장', '']))
        project = ProjectWork.create(work, self.preview())
        self.assertEqual(work.payload, ProjectWork(project.payload).work.payload)
        reopened = TerminalWorkspace(work.history)
        restore(reopened, project.work)
        self.assertEqual('아직 판단 중', reopened.draft()['text'])
        self.assertEqual(['미완료 문장', ''], reopened.unfinished[(*app.full_context(app.work_key()), 'edit')])


class ReviewRegressionTests(AssociationFixture, unittest.TestCase):
    def test_edited_source_does_not_offer_impossible_relocation(self):
        project = self.project()
        self.manuscript.write_bytes(self.source + b'% later edit')
        self.assertEqual('source-changed-reconciliation-required', project.source_status())

    def test_metadata_only_changes_do_not_consume_relocation_history(self):
        project = self.project()
        os.utime(self.manuscript, ns=(1000000000, 1000000000))
        self.assertEqual('unchanged-content', project.source_status())
        with self.assertRaises(ContractError):
            project.relocate(self.preview())
        replacement = self.paper / 'replacement.tex'
        replacement.write_bytes(self.source)
        os.replace(replacement, self.manuscript)
        self.assertEqual('unchanged-content', project.source_status())
        with self.assertRaises(ContractError):
            project.relocate(self.preview())

    def test_external_git_administration_cannot_be_a_workspace(self):
        other, admin = self.root / 'other', self.root / 'metadata'
        subprocess.run(['/usr/bin/git', 'init', '-q', '--separate-git-dir', str(admin), str(other)], check=True)
        (other / 'paper.tex').write_bytes(self.source)
        private = admin / 'private'
        private.mkdir(mode=0o700)
        with self.assertRaises(ContractError):
            self.preview(paper_root=other, workspace=private)
        self.assertEqual([], list(private.iterdir()))

    def test_nested_git_and_case_variant_administration_are_not_paper_source(self):
        nested = self.paper / 'nested'
        subprocess.run(['/usr/bin/git', 'init', '-q', str(nested)], check=True)
        (nested / 'paper.tex').write_bytes(self.source)
        (self.paper / '.git' / 'paper.tex').write_bytes(self.source)
        for path in ('nested/paper.tex', '.GIT/paper.tex'):
            with self.subTest(path=path), self.assertRaises(ContractError):
                self.preview(manuscript=path)

    def test_stale_display_cannot_report_verified_git_root(self):
        preview = self.preview()
        shutil.rmtree(self.paper / '.git')
        with self.assertRaises(ContractError):
            preview.display()

    def test_unsupported_source_is_not_reported_as_definitely_missing(self):
        project = self.project()
        self.manuscript.write_bytes(b'no more markers')
        self.assertEqual('unavailable-or-unsupported', project.source_status())
