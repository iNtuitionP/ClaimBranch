from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.model import (
    JournalDraft,
    JournalError,
    PathState,
    Snapshot,
    SnapshotDelta,
    VerificationItem,
    canonical_json,
)
from scripts.notion_journal.store import (
    JournalConfig,
    JournalStore,
    PendingEnvelope,
    iso_seoul,
    make_decision_key,
    make_journal_key,
    state_root,
)


SEOUL_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone(timedelta(hours=9)))


def path_state(path: str, digest_character: str = "d") -> PathState:
    return PathState(path, "tracked", digest_character * 64)


def snapshot(
    head: str, digest: str, paths: tuple[PathState, ...], branch: str = "main"
) -> Snapshot:
    return Snapshot("ClaimBranch", branch, head, paths, digest)


def delta(start: Snapshot, end: Snapshot, paths: tuple[str, ...]) -> SnapshotDelta:
    return SnapshotDelta(
        paths=paths,
        start_head=start.head,
        end_head=end.head,
        start_digest=start.digest,
        end_digest=end.digest,
        commit_stat="",
        worktree_stat="\n".join(f"{path}: +1/-0" for path in paths),
        includes_pre_session_edits=False,
    )


def draft(title: str = "Record the journal outcome") -> JournalDraft:
    return JournalDraft(
        title=title,
        purpose="Keep a bounded coding record",
        outcome="The local outbox retained the result",
        key_decisions=("Keep remote writes approval-gated",),
        verification=(VerificationItem("python unit tests", "Passed"),),
        risks=("OAuth remains interactive",),
        next_safe_action="Review the pending entry",
        task_status="Completed",
        change_types=("tooling", "test", "tooling"),
        ai_contribution="AI-assisted",
        verification_status="Passed",
    )


def config() -> JournalConfig:
    return JournalConfig(
        schema_version=1,
        workspace_id="workspace-fixture",
        workspace_name="Private Workspace",
        journal_page_id="page-fixture",
        database_id="database-fixture",
        data_source_id="source-fixture",
        database_url="https://www.notion.so/database-fixture",
        read_tool_name="notion-fetch",
        query_tool_name="notion-query-data-source",
        create_tool_name="notion-create-pages",
        update_tool_name="notion-update-page",
    )


class StoreTest(unittest.TestCase):
    def test_denied_first_task_does_not_reappear_in_second_task_delta(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            baseline = snapshot("1" * 40, "a" * 64, ())
            first = snapshot("1" * 40, "b" * 64, (path_state("first.md"),))
            first_delta = delta(baseline, first, ("first.md",))
            store.create_session("session-1", baseline, SEOUL_NOW)
            pending = store.capture_pending("session-1", first, first_delta, SEOUL_NOW)

            self.assertEqual("pending", pending.sync_state)
            self.assertEqual(first, store.recover_cursor("session-1").cursor)
            self.assertEqual((), store.list_receipts())

            second = snapshot(
                "1" * 40,
                "c" * 64,
                (path_state("first.md"), path_state("second.md")),
            )
            second_pending = store.capture_pending(
                "session-1", second, delta(first, second, ("second.md",)), SEOUL_NOW
            )
            self.assertEqual(("second.md",), second_pending.delta.paths)
            self.assertNotEqual(pending.journal_key, second_pending.journal_key)

    def test_state_root_prefers_localappdata_and_never_uses_repo(self):
        root = Path("C:/Users/alice/AppData/Local")
        self.assertEqual(root / "ClaimBranch" / "NotionJournal", state_root({"LOCALAPPDATA": str(root)}))
        with self.assertRaises(JournalError):
            state_root({})

    def test_baseline_is_first_write_wins(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            first = snapshot("1" * 40, "a" * 64, ())
            second = snapshot("2" * 40, "b" * 64, ())

            created = store.create_session("same-session", first, SEOUL_NOW)
            winner = store.create_session("same-session", second, SEOUL_NOW)

            self.assertEqual(created, winner)
            self.assertEqual(first, winner.baseline)
            self.assertEqual(first, winner.cursor)

    def test_session_filename_is_hash_not_raw_identifier(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            session_id = "printable/session\\identifier"
            store.create_session(session_id, snapshot("1" * 40, "a" * 64, ()), SEOUL_NOW)

            files = tuple((Path(directory) / "sessions").glob("*.json"))

            self.assertEqual(1, len(files))
            self.assertRegex(files[0].stem, r"^[0-9a-f]{32}$")
            self.assertNotIn(session_id, str(files[0]))

    def test_pending_key_is_stable_for_same_inputs(self):
        first = make_journal_key("ClaimBranch", "session-1", "a" * 64, "b" * 64)
        second = make_journal_key("ClaimBranch", "session-1", "a" * 64, "b" * 64)
        self.assertEqual(first, second)
        self.assertRegex(first, r"^cbj-v1-[0-9a-f]{24}$")

    def test_atomic_write_leaves_no_temp_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            baseline = snapshot("1" * 40, "a" * 64, ())
            end = snapshot("1" * 40, "b" * 64, (path_state("one.md"),))
            store.write_config(config())
            store.create_session("session-1", baseline, SEOUL_NOW)
            store.capture_pending("session-1", end, delta(baseline, end, ("one.md",)), SEOUL_NOW)

            files = tuple(path for path in root.rglob("*") if path.is_file())

            self.assertEqual(3, len(files))
            self.assertTrue(all(path.suffix == ".json" for path in files))
            self.assertFalse(any(".tmp" in path.name for path in files))

    def test_unknown_schema_version_fails_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            original = b'{"schema_version":2}'
            (root / "config.json").write_bytes(original)

            with self.assertRaises(JournalError):
                store.read_config()

            quarantined = tuple((root / "quarantine").glob("*.json"))
            self.assertEqual(1, len(quarantined))
            self.assertEqual(original, quarantined[0].read_bytes())
            self.assertFalse((root / "config.json").exists())

    def test_configure_does_not_overwrite_unknown_schema_version(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            original = b'{"schema_version":2}'
            (root / "config.json").write_bytes(original)

            with self.assertRaises(JournalError):
                store.write_config(config())

            quarantined = tuple((root / "quarantine").glob("*.json"))
            self.assertEqual(1, len(quarantined))
            self.assertEqual(original, quarantined[0].read_bytes())
            self.assertFalse((root / "config.json").exists())

    def test_receipt_moves_pending_to_synced_without_deleting_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            pending = self._capture_drafted(store)

            receipt = store.record_receipt(
                pending.journal_key,
                "page-result",
                "https://www.notion.so/page-result",
                SEOUL_NOW,
            )
            synced = store.read_envelope(pending.journal_key)

            self.assertEqual("synced", synced.sync_state)
            self.assertEqual("page-result", synced.page_id)
            self.assertEqual(receipt.synced_at, synced.synced_at)
            self.assertTrue((root / "pending" / f"{pending.journal_key}.json").exists())
            self.assertEqual((receipt,), store.list_receipts())
            self.assertEqual((), store.list_pending())

    def test_malformed_json_is_quarantined_and_reported(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            key = "cbj-v1-" + "a" * 24
            malformed = root / "pending" / f"{key}.json"
            malformed.write_bytes(b"{not-json")

            with self.assertRaises(JournalError):
                store.read_envelope(key)

            self.assertFalse(malformed.exists())
            quarantined = tuple((root / "quarantine").glob("*.json"))
            self.assertEqual(1, len(quarantined))
            self.assertEqual(b"{not-json", quarantined[0].read_bytes())
            self.assertEqual((), store.list_pending())

    def test_parallel_baseline_create_keeps_one_valid_document(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            submitted = (
                snapshot("1" * 40, "a" * 64, ()),
                snapshot("2" * 40, "b" * 64, ()),
            )
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = tuple(
                    executor.map(
                        lambda candidate: store.create_session(
                            "parallel-session", candidate, SEOUL_NOW
                        ),
                        submitted,
                    )
                )

            stored = store.read_session("parallel-session")
            self.assertIn(stored.baseline, submitted)
            self.assertEqual(stored.baseline, stored.cursor)
            self.assertEqual((stored, stored), results)
            raw = tuple((Path(directory) / "sessions").glob("*.json"))[0].read_bytes()
            self.assertIsInstance(json.loads(raw), dict)

    def test_recover_cursor_replays_pending_after_interrupted_advance(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            baseline = snapshot("1" * 40, "a" * 64, ())
            end = snapshot("1" * 40, "b" * 64, (path_state("one.md"),))
            store.create_session("session-1", baseline, SEOUL_NOW)
            store._write_pending_if_absent(
                self._envelope("session-1", baseline, end, ("one.md",))
            )

            recovered = store.recover_cursor("session-1")

            self.assertEqual(end, recovered.cursor)

    def test_recover_cursor_rejects_forked_envelopes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            baseline = snapshot("1" * 40, "a" * 64, ())
            first = snapshot("1" * 40, "b" * 64, (path_state("first.md"),))
            second = snapshot("1" * 40, "c" * 64, (path_state("second.md"),))
            store.create_session("session-1", baseline, SEOUL_NOW)
            store._write_pending_if_absent(
                self._envelope("session-1", baseline, first, ("first.md",))
            )
            store._write_pending_if_absent(
                self._envelope("session-1", baseline, second, ("second.md",))
            )
            session_path = tuple((root / "sessions").glob("*.json"))[0]
            before = session_path.read_bytes()

            with self.assertRaises(JournalError):
                store.recover_cursor("session-1")

            self.assertEqual(before, session_path.read_bytes())

    def test_conflicting_second_receipt_fails_closed(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            pending = self._capture_drafted(store)
            first = store.record_receipt(
                pending.journal_key,
                "page-one",
                "https://www.notion.so/page-one",
                SEOUL_NOW,
            )
            envelope_before = canonical_json(store.read_envelope(pending.journal_key).to_storage_dict())

            with self.assertRaises(JournalError):
                store.record_receipt(
                    pending.journal_key,
                    "page-two",
                    "https://www.notion.so/page-two",
                    SEOUL_NOW,
                )

            self.assertEqual((first,), store.list_receipts())
            self.assertEqual(
                envelope_before,
                canonical_json(store.read_envelope(pending.journal_key).to_storage_dict()),
            )

    def test_receipt_requires_attached_draft(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            pending = self._capture(store)

            with self.assertRaises(JournalError):
                store.record_receipt(
                    pending.journal_key,
                    "page-one",
                    "https://www.notion.so/page-one",
                    SEOUL_NOW,
                )

            self.assertEqual("pending", store.read_envelope(pending.journal_key).sync_state)
            self.assertEqual((), store.list_receipts())

    def test_attached_draft_survives_denial_and_retry(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            pending = self._capture(store)
            first_draft = draft()

            attached = store.attach_draft(pending.journal_key, first_draft)
            retried = store.attach_draft(pending.journal_key, first_draft)

            self.assertEqual(asdict(first_draft), attached.to_public_dict()["draft"])
            self.assertEqual(attached, retried)
            self.assertEqual((), store.list_receipts())
            with self.assertRaises(JournalError):
                store.attach_draft(pending.journal_key, draft("A different title"))
            self.assertEqual(first_draft, store.read_envelope(pending.journal_key).draft)

    def test_explicit_decision_key_is_stable_without_advancing_cursor(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            baseline = snapshot("1" * 40, "a" * 64, ())
            other = snapshot("2" * 40, "b" * 64, ())
            store.create_session("session-1", baseline, SEOUL_NOW)
            store.create_session("session-2", other, SEOUL_NOW)
            before = {
                path.name: path.read_bytes() for path in (root / "sessions").glob("*.json")
            }

            first = store.capture_explicit_decision(baseline, draft(), SEOUL_NOW)
            second = store.capture_explicit_decision(baseline, draft(), SEOUL_NOW)
            after = {
                path.name: path.read_bytes() for path in (root / "sessions").glob("*.json")
            }
            draft_digest = sha256(canonical_json(asdict(draft()))).hexdigest()

            self.assertEqual(first.journal_key, second.journal_key)
            self.assertEqual(
                make_decision_key("ClaimBranch", baseline.digest, draft_digest),
                first.journal_key,
            )
            self.assertEqual((), first.delta.paths)
            self.assertEqual("explicit-decision", first.trigger)
            self.assertEqual(before, after)

    def test_iso_seoul_requires_aware_time_and_drops_microseconds(self):
        with self.assertRaises(JournalError):
            iso_seoul(datetime(2026, 8, 15, 12, 0))
        utc_value = datetime(2026, 8, 15, 3, 0, 1, 999, tzinfo=timezone.utc)
        self.assertEqual("2026-08-15T12:00:01+09:00", iso_seoul(utc_value))

    def _capture(self, store: JournalStore):
        baseline = snapshot("1" * 40, "a" * 64, ())
        end = snapshot("1" * 40, "b" * 64, (path_state("one.md"),))
        store.create_session("session-1", baseline, SEOUL_NOW)
        return store.capture_pending(
            "session-1", end, delta(baseline, end, ("one.md",)), SEOUL_NOW
        )

    def _capture_drafted(self, store: JournalStore):
        pending = self._capture(store)
        return store.attach_draft(pending.journal_key, draft())

    def _envelope(
        self,
        session_id: str,
        start: Snapshot,
        end: Snapshot,
        paths: tuple[str, ...],
    ) -> PendingEnvelope:
        return PendingEnvelope(
            schema_version=1,
            journal_key=make_journal_key(
                end.repository, session_id, start.digest, end.digest
            ),
            session_id=session_id,
            repository=end.repository,
            recorded_at=iso_seoul(SEOUL_NOW),
            sync_state="pending",
            trigger="material-change",
            start_snapshot=start,
            end_snapshot=end,
            delta=delta(start, end, paths),
            draft=None,
            page_id=None,
            page_url=None,
            synced_at=None,
        )


if __name__ == "__main__":
    unittest.main()
