from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


class TemporaryGitRepository:
    def __init__(self) -> None:
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path

    def __enter__(self) -> "TemporaryGitRepository":
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self._temporary_directory.name)
        self.git("init")
        self.git("config", "user.name", "ClaimBranch Test")
        self.git("config", "user.email", "claimbranch-test@invalid.example")
        return self

    def __exit__(self, *_: object) -> None:
        assert self._temporary_directory is not None
        self._temporary_directory.cleanup()

    def write_text(self, relative: str, content: str) -> None:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")

    def remove(self, relative: str) -> None:
        (self.path / relative).unlink()

    def commit_all(self, message: str) -> None:
        self.git("add", "--all")
        self.git("commit", "-m", message)

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return completed.stdout.decode("utf-8", errors="surrogateescape").strip()
