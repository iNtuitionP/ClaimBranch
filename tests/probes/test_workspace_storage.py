from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

try:
    from scripts.probes.workspace_storage import ProbeError, WorkspaceProbe
except ModuleNotFoundError:
    ProbeError = RuntimeError
    WorkspaceProbe = None


class WorkspaceStorageProbeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(WorkspaceProbe, "The storage probe is not implemented")
        self.scratch = tempfile.TemporaryDirectory(prefix="claimbranch-storage-probe-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name).resolve()
        self.paper = self.root / "paper"
        self.paper.mkdir()
        (self.paper / ".git").mkdir()
        self.manuscript = self.paper / "paper.tex"
        self.manuscript.write_text("synthetic paper", encoding="utf-8")
        self.workspace = self.root / "private 연구 #1"
        self.probe = WorkspaceProbe(self.root, self.workspace, self.paper)

    def test_project_factory_is_a_zero_write_selection_independent_of_cwd(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        application = self.root / "application"
        application.mkdir()
        (application / ".git").mkdir()
        original_cwd = Path.cwd()
        self.addCleanup(os.chdir, original_cwd)

        selections = []
        for cwd in (application, self.paper):
            os.chdir(cwd)
            probe = WorkspaceProbe.for_project(
                self.root, workspace_root, self.paper, "project-one"
            )
            selections.append(probe.preview())

        expected = str(workspace_root / "project-one")
        self.assertEqual([expected, expected], [item["workspace"] for item in selections])
        self.assertFalse((workspace_root / "project-one").exists())

    def test_project_factory_keeps_distinct_project_histories(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        first = WorkspaceProbe.for_project(
            self.root, workspace_root, self.paper, "project-one"
        )
        second = WorkspaceProbe.for_project(
            self.root, workspace_root, self.paper, "project-two"
        )

        first.initialize("project-one")
        second.initialize("project-two")
        first.save_judgment("project-one", "j-one", "first", "first reason")
        second.save_judgment("project-two", "j-one", "second", "second reason")

        self.assertEqual(
            ("first", "first reason"), first.read_judgment("project-one", "j-one")
        )
        self.assertEqual(
            ("second", "second reason"), second.read_judgment("project-two", "j-one")
        )

    def test_project_factory_rejects_invalid_ids_without_guessing_or_writing(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        invalid_ids = (
            None, "", "project_one", "project one", "프로젝트", ".", "..",
            "../escape", "project/one", "project\\one", "CON", "con", "Lpt9",
        )

        for project_id in invalid_ids:
            with self.subTest(project_id=project_id), self.assertRaises(ProbeError):
                WorkspaceProbe.for_project(
                    self.root, workspace_root, self.paper, project_id
                )

        self.assertEqual([], list(workspace_root.iterdir()))

    def test_project_factory_rejects_uppercase_case_collision_without_writing(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        lowercase = WorkspaceProbe.for_project(
            self.root, workspace_root, self.paper, "project-one"
        )

        with self.assertRaises(ProbeError):
            WorkspaceProbe.for_project(
                self.root, workspace_root, self.paper, "PROJECT-ONE"
            )

        self.assertEqual(workspace_root / "project-one", lowercase.workspace)
        self.assertEqual([], list(workspace_root.iterdir()))

    def test_project_factory_rejects_invalid_roots_without_writing(self):
        missing = self.root / "missing"
        file_root = self.root / "file-root"
        file_root.write_text("not a directory", encoding="utf-8")
        git_root = self.root / "git-root"
        git_root.mkdir()
        (git_root / ".git").mkdir()
        outside = self.root.parent / f"{self.root.name}-outside"
        normalized = self.root / "workspaces"
        normalized.mkdir()
        traversed = self.root / "unused" / ".." / "workspaces"

        for workspace_root in (
            None, missing, file_root, git_root, self.paper, outside, traversed,
        ):
            with self.subTest(workspace_root=workspace_root), self.assertRaises(ProbeError):
                WorkspaceProbe.for_project(
                    self.root, workspace_root, self.paper, "project-one"
                )

        self.assertFalse(missing.exists())
        self.assertFalse((git_root / "project-one").exists())
        self.assertFalse((self.paper / "project-one").exists())
        self.assertFalse(outside.exists())

    def test_bound_project_rejects_wrong_id_before_every_operation(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        probe = WorkspaceProbe.for_project(
            self.root, workspace_root, self.paper, "project-one"
        )

        with self.assertRaises(ProbeError):
            probe.initialize("project-two")
        self.assertFalse(probe.workspace.exists())
        probe.initialize("project-one")
        database_before = (probe.workspace / "probe.sqlite3").read_bytes()
        paper_before = probe.paper
        moved = self.root / "moved-paper"
        moved.mkdir()

        operations = (
            lambda: probe.initialize("project-two"),
            lambda: probe.reopen("project-two"),
            lambda: probe.rebind("project-two", moved),
            lambda: probe.save_judgment("project-two", "j-one", "choice", "reason"),
            lambda: probe.read_judgment("project-two", "j-one"),
        )
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(ProbeError):
                operation()

        self.assertEqual(database_before, (probe.workspace / "probe.sqlite3").read_bytes())
        self.assertEqual(paper_before, probe.paper)
        self.assertIsNone(probe.read_judgment("project-one", "j-one"))

    def test_bound_project_requires_explicit_relocation_and_preserves_manuscript(self):
        workspace_root = self.root / "workspaces"
        workspace_root.mkdir()
        original_bytes = self.manuscript.read_bytes()
        probe = WorkspaceProbe.for_project(
            self.root, workspace_root, self.paper, "project-one"
        )
        probe.initialize("project-one")
        probe.save_judgment("project-one", "j-one", "choice", "reason")
        moved = self.root / "moved-paper"
        self.paper.rename(moved)
        relocated = WorkspaceProbe.for_project(
            self.root, workspace_root, moved, "project-one"
        )

        with self.assertRaises(ProbeError):
            relocated.reopen("project-one")
        relocated.rebind("project-one", moved)

        self.assertEqual("project-one", relocated.reopen("project-one"))
        self.assertEqual(
            ("choice", "reason"), relocated.read_judgment("project-one", "j-one")
        )
        self.assertEqual(original_bytes, (moved / "paper.tex").read_bytes())

    def test_preview_does_not_create_state_or_touch_paper(self):
        locations = self.probe.preview()
        self.assertEqual(str(self.workspace), locations["workspace"])
        self.assertFalse(self.workspace.exists())
        self.assertEqual("synthetic paper", self.manuscript.read_text(encoding="utf-8"))

    def test_workspace_inside_any_git_root_is_rejected(self):
        application = self.root / "application"
        application.mkdir()
        (application / ".git").write_text("synthetic git marker", encoding="utf-8")
        for target in (self.paper / "state", application / "state"):
            with self.subTest(target=target), self.assertRaises(ProbeError):
                WorkspaceProbe(self.root, target, self.paper).preview()
            self.assertFalse(target.exists())

    def test_path_normalization_cannot_bypass_paper_boundary(self):
        with self.assertRaises(ProbeError):
            WorkspaceProbe(self.root, self.paper / "child" / ".." / "state", self.paper)

    def test_workspace_alias_into_paper_is_rejected(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.paper, target_is_directory=True)
        except OSError:
            self.skipTest("This account cannot create a directory symlink")
        with self.assertRaises(ProbeError):
            WorkspaceProbe(self.root, alias / "state", self.paper)

    def test_non_probe_root_is_rejected_without_writing(self):
        with self.assertRaises(ProbeError):
            WorkspaceProbe(self.paper, self.workspace, self.paper)
        self.assertFalse(self.workspace.exists())

    def test_missing_store_is_not_created_on_reopen(self):
        with self.assertRaises(ProbeError):
            self.probe.reopen("project-one")
        self.assertFalse(self.workspace.exists())

    def test_missing_workspace_parent_is_rejected_without_writing(self):
        missing_parent = self.root / "missing-parent"
        probe = WorkspaceProbe(self.root, missing_parent / "workspace", self.paper)
        with self.assertRaises(ProbeError):
            probe.initialize("project-one")
        self.assertFalse(missing_parent.exists())

    def test_initialization_reopens_exact_identity_and_refuses_replacement(self):
        self.probe.initialize("project-one")
        self.assertEqual("project-one", self.probe.reopen("project-one"))
        with self.assertRaises(ProbeError):
            self.probe.initialize("project-two")
        with self.assertRaises(ProbeError):
            self.probe.reopen("project-two")
        self.assertEqual("project-one", self.probe.reopen("project-one"))

    def test_judgment_survives_reopen_without_second_entry(self):
        self.probe.initialize("project-one")
        self.probe.save_judgment("project-one", "j-one", "가상 판단", "원자료 의미는 가정하지 않음")
        reopened = WorkspaceProbe(self.root, self.workspace, self.paper)
        self.assertEqual(("가상 판단", "원자료 의미는 가정하지 않음"),
                         reopened.read_judgment("project-one", "j-one"))

    def test_identical_retry_is_idempotent_but_changed_retry_is_rejected(self):
        self.probe.initialize("project-one")
        self.probe.save_judgment("project-one", "j-one", "choice", "reason")
        self.probe.save_judgment("project-one", "j-one", "choice", "reason")
        with self.assertRaises(ProbeError):
            self.probe.save_judgment("project-one", "j-one", "different", "reason")
        self.assertEqual(("choice", "reason"), self.probe.read_judgment("project-one", "j-one"))

    def test_wrong_project_cannot_append_or_read(self):
        self.probe.initialize("project-one")
        with self.assertRaises(ProbeError):
            self.probe.save_judgment("project-two", "j-one", "choice", "reason")
        self.assertIsNone(self.probe.read_judgment("project-one", "j-one"))
        with self.assertRaises(ProbeError):
            self.probe.read_judgment("project-two", "j-one")

    def test_moved_paper_requires_explicit_rebind_not_new_history(self):
        self.probe.initialize("project-one")
        self.probe.save_judgment("project-one", "j-one", "choice", "reason")
        moved = self.root / "moved-paper"
        self.paper.rename(moved)
        relocated = WorkspaceProbe(self.root, self.workspace, moved)
        with self.assertRaises(ProbeError):
            relocated.reopen("project-one")
        relocated.rebind("project-one", moved)
        self.assertEqual(("choice", "reason"), relocated.read_judgment("project-one", "j-one"))
        self.assertEqual("synthetic paper", (moved / "paper.tex").read_text(encoding="utf-8"))

    def test_corrupt_store_is_preserved_instead_of_reset(self):
        self.workspace.mkdir()
        database = self.workspace / "probe.sqlite3"
        database.write_bytes(b"not a database")
        with self.assertRaises(ProbeError):
            self.probe.reopen("project-one")
        self.assertEqual(b"not a database", database.read_bytes())

    def test_real_process_exit_before_commit_retains_prior_state(self):
        self._crash_and_reopen("before_commit", None)

    def test_real_process_exit_after_commit_is_safe_to_retry(self):
        self._crash_and_reopen("after_commit", ("choice", "reason"))

    def _crash_and_reopen(self, cut, expected):
        self.probe.initialize("project-one")
        self.probe.save_judgment("project-one", "prior", "old", "kept")
        child = """
import os, sys
from pathlib import Path
from scripts.probes.workspace_storage import WorkspaceProbe
p = WorkspaceProbe(*(Path(value) for value in sys.argv[1:4]))
def checkpoint(phase):
    if phase == sys.argv[4]:
        os._exit(23)
p.save_judgment('project-one', 'j-one', 'choice', 'reason', checkpoint)
"""
        result = subprocess.run(
            [sys.executable, "-c", child, str(self.root), str(self.workspace), str(self.paper), cut],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=20,
        )
        self.assertEqual(23, result.returncode, result.stderr.decode(errors="replace"))
        self.assertEqual(("old", "kept"), self.probe.read_judgment("project-one", "prior"))
        self.assertEqual(expected, self.probe.read_judgment("project-one", "j-one"))
        self.probe.save_judgment("project-one", "j-one", "choice", "reason")
        self.assertEqual(("choice", "reason"), self.probe.read_judgment("project-one", "j-one"))


if __name__ == "__main__":
    unittest.main()
