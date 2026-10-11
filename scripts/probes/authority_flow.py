"""Disposable A1–A4 integration experiment, NEVER a production authority store.

Uses caller-injected synthetic approval, ordinary SQLite and unencrypted fixture
copies. Any Python caller can forge the inputs or write the database. No private
IPC, OS authorization, trusted key, compiler or power-loss guarantee exists.
Only WorkspaceProbe's owned temporary sandbox is supported. File recovery assumes
cooperative writers; it does not defend against hostile filesystem races.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
import secrets
import tempfile

from scripts.contracts.authorization_attempt import AuthorizationAttempt
from scripts.contracts.first_pass import ContractError, Proposal, Review
from scripts.contracts.review_binding import bind_review, matches_bound_review
from scripts.probes.workspace_storage import ProbeError, WorkspaceProbe


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Operation:
    """Exact synthetic judgment/selection/patch, not a product DomainOperation."""

    key: str
    expected_head: int
    review: Review
    before: bytes
    after: bytes
    selected: tuple[str, ...]
    proposal: Proposal | None = None

    def payload(self):
        if (type(self.key) is not str or not self.key.strip()
                or type(self.expected_head) is not int or self.expected_head < 0
                or type(self.before) is not bytes or type(self.after) is not bytes
                or not self.before or not self.after
                or max(len(self.before), len(self.after)) > 1024 * 1024
                or type(self.selected) is not tuple or not self.selected
                or any(type(item) is not str or not item.strip() for item in self.selected)
                or len(set(self.selected)) != len(self.selected)):
            raise ProbeError("invalid bounded synthetic operation")
        try:
            # Reuse A1 validation; neither this nor the digest grants authority.
            bind_review(self.review, operation_digest="0" * 64, session_nonce="validation", expires_at=1)
            if (self.review.manuscript_target is None
                    or self.review.manuscript_target.content_digest != _digest(self.before)):
                raise ProbeError("review must name the exact manuscript before bytes")
            if self.proposal is not None and (
                    not isinstance(self.proposal, Proposal) or self.proposal.accepted
                    or self.proposal.project_id != self.review.draft.project_id
                    or self.proposal.episode_id != self.review.draft.episode_id):
                raise ProbeError("proposal provenance must belong to this exact draft")
            return {"key": self.key, "expected_head": self.expected_head,
                    "review": asdict(self.review), "before_sha256": _digest(self.before),
                    "after_sha256": _digest(self.after), "selected": list(self.selected),
                    "proposal": asdict(self.proposal) if self.proposal is not None else None}
        except (ContractError, TypeError, AttributeError) as exc:
            raise ProbeError("invalid synthetic review") from exc

    @property
    def digest(self):
        return _digest(_json(self.payload()).encode("utf-8"))


class SyntheticAuthorityFlow(WorkspaceProbe):
    """Serialized receiver sessions and crash recovery for disposable data only."""

    def rebind(self, project_id, paper):
        # WorkspaceProbe's relocation experiment has no approval or patch scope.
        # Reusing it here would silently redirect outstanding/recorded intents.
        raise ProbeError("this integration probe fixes its paper association; create a new sandbox")

    def initialize(self, project_id):
        super().initialize(project_id)
        with self._connect() as connection:
            connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE flow (slot INTEGER PRIMARY KEY CHECK(slot=1),
                    session TEXT NOT NULL, head INTEGER NOT NULL);
                INSERT INTO flow VALUES (1, '', 0);
                CREATE TABLE operations (key TEXT PRIMARY KEY, digest TEXT NOT NULL,
                    attempt_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
                    head INTEGER UNIQUE NOT NULL, before_bytes BLOB NOT NULL, after_bytes BLOB NOT NULL);
                CREATE TABLE patches (key TEXT PRIMARY KEY, state TEXT NOT NULL);
                COMMIT;
            """)

    def start_session(self, project_id):
        """A receiver restart revokes every prior in-memory attempt, including peers."""
        self.reopen(project_id)
        session = secrets.token_hex(32)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_identity(connection, project_id, self.paper)
            connection.execute("UPDATE flow SET session=? WHERE slot=1", (session,))
            connection.commit()
        self._project_id = project_id
        self._session = session
        self._attempts = {}
        self._revoked = set()

    @contextmanager
    def _transaction(self):
        if not getattr(self, "_session", None):
            raise ProbeError("start a synthetic receiver session first")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_identity(connection, self._project_id, self.paper)
            session, head = connection.execute("SELECT session, head FROM flow WHERE slot=1").fetchone()
            if session != self._session:
                raise ProbeError("receiver session was replaced; outstanding attempts are invalid")
            yield connection, head
            connection.commit()

    def _manuscript(self):
        self._validate_paths()
        path = self.paper / "manuscript.tex"
        if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
            raise ProbeError("an existing unlinked synthetic manuscript copy is required")
        return path

    def begin(self, operation, *, load_review, verify_response, clock, expires_at, nonce):
        digest = operation.digest
        with self._transaction():
            if operation.review.draft.project_id != self._project_id:
                raise ProbeError("operation belongs to another project")
        last_time = [-1]

        def checked_clock():
            now = clock()
            if type(now) is not int or now < 0 or now < last_time[0]:
                raise ContractError("clock must not go backwards")
            last_time[0] = now
            return now

        binding = bind_review(operation.review, operation_digest=digest,
                              session_nonce=self._session, expires_at=expires_at)
        attempt = AuthorizationAttempt(binding, nonce=nonce, load_review=load_review,
                                       verify_response=verify_response, clock=checked_clock)
        attempt_id = secrets.token_hex(32)
        self._attempts[attempt_id] = (attempt, load_review, checked_clock)
        return attempt_id

    def _attempt(self, attempt_id):
        try:
            return self._attempts[attempt_id]
        except (AttributeError, KeyError, TypeError) as exc:
            raise ProbeError("no outstanding attempt in this receiver") from exc

    def request(self, attempt_id):
        return self._attempt(attempt_id)[0].request

    def respond(self, attempt_id, response):
        with self._transaction():
            pass
        return self._attempt(attempt_id)[0].finish(response)

    def cancel(self, attempt_id):
        self._attempt(attempt_id)
        self._revoked.add(attempt_id)
        return self._attempt(attempt_id)[0].cancel()

    @staticmethod
    def _record(connection, key):
        row = connection.execute(
            "SELECT o.digest, o.attempt_id, o.payload, o.head, p.state "
            "FROM operations o JOIN patches p ON p.key=o.key WHERE o.key=?", (key,)).fetchone()
        if row is None:
            return None
        return {"digest": row[0], "attempt_id": row[1], "payload": json.loads(row[2]),
                "head": row[3], "patch_state": row[4], "authorization_verified": False}

    def records(self):
        with self._transaction() as (connection, _):
            return [self._record(connection, row[0]) for row in
                    connection.execute("SELECT key FROM operations ORDER BY head").fetchall()]

    def commit(self, operation, attempt_id, *, checkpoint=None):
        digest = operation.digest
        with self._transaction() as (connection, head):
            prior = self._record(connection, operation.key)
            if prior is not None:
                if prior["digest"] != digest or prior["attempt_id"] != attempt_id:
                    raise ProbeError("changed retry cannot overwrite a recorded operation")
                return prior  # Status recovery: no new mutation or authorization.
            attempt, load_review, clock = self._attempt(attempt_id)
            if attempt.result.status != "matched" or attempt_id in self._revoked:
                raise ProbeError("a matched synthetic attempt is required")
            try:
                current = load_review()
                fresh = matches_bound_review(attempt.request.binding, current,
                    operation_digest=digest, session_nonce=self._session, now=clock())
            except Exception as exc:
                raise ProbeError("final synthetic context could not be verified") from exc
            if not fresh or operation.expected_head != head:
                raise ProbeError("review, operation or expected head changed")
            if connection.execute(
                "SELECT 1 FROM patches WHERE state NOT IN ('applied', 'restored')").fetchone():
                raise ProbeError("finish or restore the prior manuscript intent first")
            if self._manuscript().read_bytes() != operation.before:
                raise ProbeError("manuscript changed since review")
            try:
                if clock() >= attempt.request.binding.expires_at or attempt_id in self._revoked:
                    raise ProbeError("attempt expired or was cancelled before consumption")
            except ContractError as exc:
                raise ProbeError("final attempt time could not be verified") from exc
            connection.execute("INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (operation.key, digest, attempt_id, _json(operation.payload()), head + 1,
                 operation.before, operation.after))
            connection.execute("INSERT INTO patches VALUES (?, 'prepared')", (operation.key,))
            connection.execute("UPDATE flow SET head=? WHERE slot=1", (head + 1,))
            if checkpoint:
                checkpoint("before_commit")
            connection.commit()
            if checkpoint:
                checkpoint("after_commit")
            return self._record(connection, operation.key)

    def _patch(self, connection, key, head):
        row = connection.execute(
            "SELECT o.head, o.before_bytes, o.after_bytes, p.state "
            "FROM operations o JOIN patches p ON p.key=o.key WHERE o.key=?", (key,)).fetchone()
        if row is None or row[0] != head:
            raise ProbeError("only the latest synthetic operation can change its manuscript")
        return row[1:]

    def _intent(self, key, action, checkpoint):
        intent, terminal = ("applying", "applied") if action == "apply" else ("restoring", "restored")
        with self._transaction() as (connection, head):
            before, after, state = self._patch(connection, key, head)
            current = self._manuscript().read_bytes()
            if state == terminal:
                if current != (after if action == "apply" else before):
                    raise ProbeError("manuscript changed after completed operation")
                return terminal
            allowed = ("prepared",) if action == "apply" else ("prepared", "applied")
            if state not in allowed:
                raise ProbeError("pending manuscript intent requires explicit recovery")
            expected = after if state == "applied" else before
            if current != expected:
                raise ProbeError("preserve unexpected manuscript edits")
            connection.execute("UPDATE patches SET state=? WHERE key=?", (intent, key))
        if checkpoint:
            checkpoint("after_" + action + "_intent")
        return self.recover(key, checkpoint=checkpoint)

    def apply(self, key, *, checkpoint=None):
        return self._intent(key, "apply", checkpoint)

    def restore(self, key, *, checkpoint=None):
        return self._intent(key, "restore", checkpoint)

    def recover(self, key, *, checkpoint=None):
        """Finish durable intent only when the file equals one of its known states."""
        with self._transaction() as (connection, head):
            before, after, state = self._patch(connection, key, head)
            if state not in ("applying", "restoring"):
                raise ProbeError("there is no interrupted manuscript intent")
            path = self._manuscript()
            current = path.read_bytes()
            if current not in (before, after):
                raise ProbeError("preserve unexpected manuscript edits; recovery is unresolved")
            target = after if state == "applying" else before
            terminal = "applied" if state == "applying" else "restored"
            if current != target:
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=self.paper, prefix=".synthetic-patch-", delete=False) as output:
                        temporary = output.name
                        output.write(target)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, path)
                finally:
                    if temporary is not None and os.path.exists(temporary):
                        os.unlink(temporary)
                if checkpoint:
                    checkpoint("after_file_replace")
            connection.execute("UPDATE patches SET state=? WHERE key=?", (terminal, key))
        return terminal
