"""Synthetic SQLite storage experiment, NOT a ClaimBranch application store.

Only explicitly supplied probe-prefixed temporary sandboxes are accepted.
No real source evidence, authentication, encryption, or power-loss guarantee.
Run through tests/probes; there is intentionally no user-data CLI.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import quote


class ProbeError(RuntimeError):
    """An experiment precondition or stored identity could not be verified."""


class WorkspaceProbe:
    _WINDOWS_RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }

    def __init__(
        self, sandbox: Path, workspace: Path, paper: Path,
        expected_project_id=None,
    ):
        self.sandbox = Path(sandbox).resolve()
        self.workspace = Path(workspace).resolve()
        self.paper = Path(paper).resolve()
        self._expected_project_id = expected_project_id
        self._validate_paths()

    @classmethod
    def for_project(cls, sandbox, workspace_root, paper, project_id):
        cls._validate_project_id(project_id)
        try:
            root = Path(workspace_root)
            root_is_valid = root.resolve() == root and root.is_dir()
        except (TypeError, ValueError, OSError):
            root_is_valid = False
        if not root_is_valid:
            raise ProbeError("An existing normalized workspace root is required")
        return cls(
            sandbox, root / project_id, paper,
            expected_project_id=project_id,
        )

    @classmethod
    def _validate_project_id(cls, project_id):
        if (not isinstance(project_id, str)
                or not project_id
                or not project_id.isascii()
                or project_id != project_id.lower()
                or any(not (character.isalnum() or character == "-")
                       for character in project_id)
                or project_id.upper() in cls._WINDOWS_RESERVED_NAMES):
            raise ProbeError("A probe-safe synthetic project identity is required")

    def _check_expected_project(self, project_id):
        if (self._expected_project_id is not None
                and project_id != self._expected_project_id):
            raise ProbeError("Project identity differs from the selected workspace")

    def _validate_paths(self):
        temporary = Path(tempfile.gettempdir()).resolve()
        if (self.sandbox.parent != temporary
                or not self.sandbox.name.startswith("claimbranch-storage-probe-")
                or not self.sandbox.is_dir()):
            raise ProbeError("An explicit probe-created temporary sandbox is required")
        for path in (self.workspace, self.paper):
            if path.resolve() != path or not path.is_relative_to(self.sandbox) or path == self.sandbox:
                raise ProbeError("Locations must remain strictly inside the synthetic sandbox")
        if not self.paper.is_dir():
            raise ProbeError("The synthetic paper directory is unavailable")
        if self.paper.is_relative_to(self.workspace) or self.workspace.is_relative_to(self.paper):
            raise ProbeError("Paper and workspace must be separate")
        for ancestor in (self.workspace, *self.workspace.parents):
            if (ancestor / ".git").exists():
                raise ProbeError("Workspace cannot be inside a Git working tree")

    def preview(self):
        self._validate_paths()
        return {"sandbox": str(self.sandbox), "workspace": str(self.workspace), "paper": str(self.paper)}

    @contextmanager
    def _connect(self):
        self._validate_paths()
        database = self.workspace / "probe.sqlite3"
        if not database.is_file() or database.resolve() != database:
            raise ProbeError("Existing probe database is required; nothing was created")
        connection = None
        try:
            uri = "file:" + quote(database.as_posix(), safe="/:") + "?mode=rw"
            connection = sqlite3.connect(uri, uri=True, timeout=2)
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        except sqlite3.Error as exc:
            raise ProbeError("Probe database could not be verified; preserve it") from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _check_identity(connection, project_id, paper=None):
        rows = connection.execute("SELECT format, project_id, paper FROM identity").fetchall()
        if len(rows) != 1 or rows[0][:2] != ("synthetic-probe-v1", project_id):
            raise ProbeError("Stored synthetic project identity does not match")
        if paper is not None and rows[0][2] != str(paper):
            raise ProbeError("Paper association changed; explicitly rebind it")

    def initialize(self, project_id):
        self._check_expected_project(project_id)
        self._validate_paths()
        if not isinstance(project_id, str) or not project_id:
            raise ProbeError("A synthetic project identity is required")
        if self.workspace.exists():
            raise ProbeError("Workspace already exists; reopen rather than replace")
        if not self.workspace.parent.is_dir():
            raise ProbeError("An existing workspace parent directory is required")
        self.workspace.mkdir()
        database = self.workspace / "probe.sqlite3"
        database.touch(exist_ok=False)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE identity (slot INTEGER PRIMARY KEY CHECK(slot=1), "
                "format TEXT NOT NULL, project_id TEXT NOT NULL, paper TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO identity VALUES (1, 'synthetic-probe-v1', ?, ?)",
                (project_id, str(self.paper)),
            )
            connection.execute(
                "CREATE TABLE judgments (key TEXT PRIMARY KEY, text TEXT NOT NULL, rationale TEXT NOT NULL)"
            )
            connection.commit()

    def reopen(self, project_id):
        self._check_expected_project(project_id)
        with self._connect() as connection:
            self._check_identity(connection, project_id, self.paper)
        return project_id

    def rebind(self, project_id, paper):
        self._check_expected_project(project_id)
        candidate = WorkspaceProbe(
            self.sandbox, self.workspace, paper,
            expected_project_id=self._expected_project_id,
        )
        with candidate._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_identity(connection, project_id)
            connection.execute("UPDATE identity SET paper=? WHERE slot=1", (str(candidate.paper),))
            connection.commit()
        self.paper = candidate.paper

    def save_judgment(self, project_id, key, text, rationale, checkpoint=None):
        self._check_expected_project(project_id)
        if any(not isinstance(value, str) or not value for value in (key, text, rationale)):
            raise ProbeError("The synthetic key, judgment, and rationale must be nonempty text")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_identity(connection, project_id, self.paper)
            previous = connection.execute("SELECT text, rationale FROM judgments WHERE key=?", (key,)).fetchone()
            if previous is not None:
                if previous != (text, rationale):
                    raise ProbeError("A changed retry cannot overwrite a judgment")
            else:
                connection.execute("INSERT INTO judgments VALUES (?, ?, ?)", (key, text, rationale))
            if checkpoint is not None:
                checkpoint("before_commit")
            connection.commit()
            if checkpoint is not None:
                checkpoint("after_commit")

    def read_judgment(self, project_id, key):
        self._check_expected_project(project_id)
        with self._connect() as connection:
            self._check_identity(connection, project_id, self.paper)
            return connection.execute("SELECT text, rationale FROM judgments WHERE key=?", (key,)).fetchone()
