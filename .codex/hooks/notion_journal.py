"""Repository-root launcher for the ClaimBranch Notion journal hook."""

from pathlib import Path
import subprocess
import sys


def _repository_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return Path(completed.stdout.decode("utf-8", errors="surrogateescape").strip())


root = _repository_root()
sys.path.insert(0, str(root))

from scripts.notion_journal.cli import main


raise SystemExit(main(["hook"]))
