from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from unittest import mock
import unittest

from scripts.notion_journal.git_state import (
    capture_snapshot,
    compare_snapshots,
    content_sha256,
)
from scripts.notion_journal.model import PathState, ValidationError, canonical_json
from tests.notion_journal.support import TemporaryGitRepository


class GitStateTest(unittest.TestCase):
    def assert_snapshot_is_private(self, repo, snapshot, *source_texts):
        serialized = canonical_json(asdict(snapshot))
        self.assertNotIn(str(repo.path).encode("utf-8"), serialized)
        self.assertNotIn(str(repo.path).replace("\\", "/").encode("utf-8"), serialized)
        for source_text in source_texts:
            self.assertNotIn(source_text.encode("utf-8"), serialized)

    def test_preexisting_dirty_file_is_not_a_delta_until_content_changes(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("paper.md", "committed\n")
            repo.commit_all("baseline")
            repo.write_text("paper.md", "dirty before session\n")
            start = capture_snapshot(repo.path)
            unchanged = capture_snapshot(repo.path)
            self.assertEqual((), compare_snapshots(repo.path, start, unchanged).paths)

            repo.write_text("paper.md", "changed during session\n")
            end = capture_snapshot(repo.path)
            delta = compare_snapshots(repo.path, start, end)

            self.assertEqual(("paper.md",), delta.paths)
            self.assertTrue(delta.includes_pre_session_edits)
            self.assertNotEqual(start.digest, end.digest)
            self.assert_snapshot_is_private(
                repo, end, "committed", "dirty before session", "changed during session"
            )

    def test_clean_repository_has_stable_empty_snapshot(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("README.md", "baseline\n")
            repo.commit_all("baseline")

            first = capture_snapshot(repo.path)
            second = capture_snapshot(repo.path)

            self.assertEqual((), first.paths)
            self.assertEqual(first, second)
            self.assertRegex(first.digest, r"^[0-9a-f]{64}$")
            self.assert_snapshot_is_private(repo, first, "baseline")

    def test_tracked_edit_changes_digest_and_delta(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("README.md", "baseline\n")
            repo.commit_all("baseline")
            start = capture_snapshot(repo.path)
            repo.write_text("README.md", "edited\n")
            end = capture_snapshot(repo.path)

            delta = compare_snapshots(repo.path, start, end)

            self.assertEqual(("README.md",), delta.paths)
            self.assertNotEqual(start.digest, end.digest)
            self.assert_snapshot_is_private(repo, end, "baseline", "edited")

    def test_untracked_file_is_hashed_without_persisting_content(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("README.md", "baseline\n")
            repo.commit_all("baseline")
            repo.write_text("notes.txt", "DO-NOT-PERSIST")

            snapshot = capture_snapshot(repo.path)
            serialized = canonical_json(asdict(snapshot))

            self.assertEqual("untracked", snapshot.paths[0].state)
            self.assertIn(b"notes.txt", serialized)
            self.assertIn(sha256(b"DO-NOT-PERSIST").hexdigest().encode("ascii"), serialized)
            self.assertNotIn(b"DO-NOT-PERSIST", serialized)
            self.assert_snapshot_is_private(repo, snapshot, "DO-NOT-PERSIST")

    def test_vscode_and_ignored_paths_are_excluded(self):
        with TemporaryGitRepository() as repo:
            repo.write_text(".gitignore", "ignored.txt\n")
            repo.commit_all("baseline")
            start = capture_snapshot(repo.path)
            repo.write_text(".vscode/settings.json", '{"private": true}\n')
            repo.write_text("ignored.txt", "ignored source\n")

            end = capture_snapshot(repo.path)

            self.assertEqual(start, end)
            self.assertEqual((), end.paths)
            self.assert_snapshot_is_private(repo, end, "private", "ignored source")

    def test_deleted_file_uses_deleted_marker(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("old.md", "old source\n")
            repo.commit_all("baseline")
            repo.remove("old.md")

            snapshot = capture_snapshot(repo.path)

            self.assertEqual("deleted", snapshot.paths[0].state)
            self.assertEqual(sha256(b"<deleted>").hexdigest(), snapshot.paths[0].content_sha256)
            self.assert_snapshot_is_private(repo, snapshot, "old source")

    def test_symlink_hashes_link_text_without_following_target(self):
        path = Path("link.txt")
        with (
            mock.patch("scripts.notion_journal.git_state.os.path.islink", return_value=True),
            mock.patch("scripts.notion_journal.git_state.os.readlink", return_value="outside-target"),
            mock.patch.object(Path, "open") as path_open,
        ):
            digest = content_sha256(path)

        self.assertEqual(sha256(b"outside-target").hexdigest(), digest)
        path_open.assert_not_called()

    def test_commit_between_snapshots_reports_commit_paths_and_stat(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("README.md", "baseline\n")
            repo.commit_all("baseline")
            start = capture_snapshot(repo.path)
            repo.write_text("README.md", "baseline\nsecond line\n")
            repo.commit_all("change readme")
            end = capture_snapshot(repo.path)

            delta = compare_snapshots(repo.path, start, end)

            self.assertEqual(("README.md",), delta.paths)
            self.assertNotEqual(start.head, end.head)
            self.assertRegex(delta.commit_stat, r"README\.md: \+\d+/-\d+")
            self.assertLessEqual(len(delta.commit_stat), 4000)
            self.assert_snapshot_is_private(repo, end, "baseline", "second line")

    def test_snapshot_paths_are_sorted_and_relative(self):
        with TemporaryGitRepository() as repo:
            repo.write_text("README.md", "baseline\n")
            repo.commit_all("baseline")
            repo.write_text("z.txt", "z source\n")
            repo.write_text("a.txt", "a source\n")

            snapshot = capture_snapshot(repo.path)

            self.assertEqual(("a.txt", "z.txt"), tuple(item.path for item in snapshot.paths))
            self.assert_snapshot_is_private(repo, snapshot, "a source", "z source")

        with self.assertRaises(ValidationError):
            PathState("bad\nname", "tracked", "a" * 64)


if __name__ == "__main__":
    unittest.main()
