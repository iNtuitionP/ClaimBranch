from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.notion_journal.model import (
    JudgmentDraft,
    JournalDraft,
    JournalError,
    PathState,
    Snapshot,
    SnapshotDelta,
    VerificationItem,
    canonical_json,
)
from scripts.notion_journal.presentation import render_judgment_body
from scripts.notion_journal.store import (
    JournalConfig,
    JournalStore,
    PendingEnvelope,
    iso_seoul,
    make_decision_key,
    make_journal_key,
    make_judgment_key,
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


def judgment_draft(
    *,
    background: str | None = (
        "ClaimBranch was defining how one coding judgment reaches its "
        "user-controlled Notion journal"
    ),
    human_judgment: str = "Require an explicit user choice before capture",
    supersedes: str | None = None,
) -> JudgmentDraft:
    return JudgmentDraft(
        title="Prefer user-invoked journal entries",
        background=background,
        why_now="Automatic pending records became reading debt",
        understanding_shift="The capture unit is a human judgment",
        human_judgment=human_judgment,
        tradeoff_boundary="No automatic task summaries",
        revisit_signal="Users repeatedly request automatic capture",
        evidence_pointers=("docs/designs/journal.md",),
        ai_contribution="AI-assisted",
        supersedes=supersedes,
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
    def test_config_accepts_current_app_notion_database_url(self):
        current = replace(
            config(),
            database_url="https://app.notion.com/p/" + "a" * 32,
        )

        self.assertEqual(
            "https://app.notion.com/p/" + "a" * 32,
            current.database_url,
        )

    def test_legacy_configuration_without_language_loads_as_explicitly_unset(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            (root / "config.json").write_bytes(canonical_json(asdict(config())))

            loaded = store.read_config()

            self.assertIsNone(loaded.journal_language)

    def test_same_judgment_in_different_languages_has_distinct_frozen_keys(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            current = snapshot("1" * 40, "a" * 64, ())

            korean = store.capture_explicit_judgment(
                current, judgment_draft(), SEOUL_NOW, journal_language="ko"
            )
            english = store.capture_explicit_judgment(
                current, judgment_draft(), SEOUL_NOW, journal_language="en"
            )

            self.assertNotEqual(korean.journal_key, english.journal_key)
            self.assertEqual("ko", korean.journal_language)
            self.assertEqual("en", english.journal_language)
            self.assertEqual(
                "ko", store.read_envelope(korean.journal_key).journal_language
            )
            self.assertEqual(
                "en", store.read_envelope(english.journal_key).journal_language
            )

    def test_legacy_language_less_judgment_envelope_reopens_without_migration(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            current = snapshot("1" * 40, "a" * 64, ())
            envelope = store.capture_explicit_judgment(
                current, judgment_draft(background=None), SEOUL_NOW
            )
            path = root / "v2" / "pending" / f"{envelope.journal_key}.json"
            legacy_value = envelope.to_storage_dict()
            legacy_value.pop("journal_language", None)
            legacy_bytes = canonical_json(legacy_value)
            path.write_bytes(legacy_bytes)

            reopened = JournalStore(root).read_envelope(envelope.journal_key)

            self.assertIsNone(reopened.journal_language)
            self.assertIsNone(reopened.draft.background)
            self.assertNotIn("background", reopened.to_public_dict()["draft"])
            self.assertEqual(legacy_bytes, path.read_bytes())

    def test_receipt_keeps_legacy_language_less_envelope_language_less(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            current = snapshot("1" * 40, "a" * 64, ())
            envelope = store.capture_explicit_judgment(
                current, judgment_draft(background=None), SEOUL_NOW
            )
            path = root / "v2" / "pending" / f"{envelope.journal_key}.json"
            legacy_value = envelope.to_storage_dict()
            legacy_value.pop("journal_language", None)
            path.write_bytes(canonical_json(legacy_value))

            store.record_receipt(
                envelope.journal_key,
                "legacy-page",
                "https://www.notion.so/legacy-page",
                SEOUL_NOW,
            )

            synced_value = json.loads(path.read_bytes())
            self.assertEqual("synced", synced_value["sync_state"])
            self.assertNotIn("journal_language", synced_value)
            self.assertNotIn("background", synced_value["draft"])

    def test_legacy_explicit_language_envelope_keeps_old_body_and_shape(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            current = snapshot("1" * 40, "a" * 64, ())
            envelope = store.capture_explicit_judgment(
                current,
                judgment_draft(background=None),
                SEOUL_NOW,
                journal_language="ko",
            )
            path = root / "v2" / "pending" / f"{envelope.journal_key}.json"
            before = path.read_bytes()

            reopened = JournalStore(root).read_envelope(envelope.journal_key)

            self.assertIsNone(reopened.draft.background)
            self.assertNotIn("background", json.loads(before)["draft"])
            body = render_judgment_body(reopened.draft, reopened.journal_language)
            self.assertTrue(body.startswith("## 왜 지금\n\n"))
            self.assertNotIn("## 배경", body)

            store.record_receipt(
                envelope.journal_key,
                "legacy-language-page",
                "https://www.notion.so/legacy-language-page",
                SEOUL_NOW,
            )
            self.assertNotIn(
                "background", json.loads(path.read_bytes())["draft"]
            )

    def test_literal_nine_key_envelopes_keep_the_exact_former_body(self):
        literal_draft = {
            "title": "Prefer user-invoked journal entries",
            "why_now": "Automatic pending records became reading debt",
            "understanding_shift": "The capture unit is a human judgment",
            "human_judgment": "Require an explicit user choice before capture",
            "tradeoff_boundary": "No automatic task summaries",
            "revisit_signal": "Users repeatedly request automatic capture",
            "evidence_pointers": ["docs/designs/journal.md"],
            "ai_contribution": "AI-assisted",
            "supersedes": None,
        }
        expected_body = (
            "## \uc65c \uc9c0\uae08\n\n"
            "Automatic pending records became reading debt\n\n"
            "## \ubb34\uc5c7\uc774 \ub2ec\ub77c\uc84c\ub098\n\n"
            "The capture unit is a human judgment\n\n"
            "## \ubb34\uc5c7\uc744 \ud310\ub2e8\ud588\ub098\n\n"
            "Require an explicit user choice before capture\n\n"
            "## \ubb34\uc5c7\uc744 \uac10\uc218\ud558\uac70\ub098 \uc81c\uc678\ud588\ub098\n\n"
            "No automatic task summaries\n\n"
            "## \ubb34\uc5c7\uc774 \uc774 \ud310\ub2e8\uc744 \ubc14\uafc0\uae4c\n\n"
            "Users repeatedly request automatic capture\n\n"
            "## \uadfc\uac70\n\n"
            "- `docs/designs/journal.md`"
        )

        for language in (None, "ko"):
            with self.subTest(language=language), TemporaryDirectory() as directory:
                root = Path(directory)
                store = JournalStore(root)
                current = snapshot("1" * 40, "a" * 64, ())
                empty_delta = delta(current, current, ())
                digest_value: object = literal_draft
                if language is not None:
                    digest_value = {
                        "draft": literal_draft,
                        "journal_language": language,
                    }
                draft_digest = sha256(canonical_json(digest_value)).hexdigest()
                key = make_judgment_key(
                    current.repository, current.digest, draft_digest
                )
                literal_envelope = {
                    "schema_version": 1,
                    "journal_key": key,
                    "session_id": "explicit-judgment",
                    "repository": current.repository,
                    "recorded_at": iso_seoul(SEOUL_NOW),
                    "sync_state": "pending",
                    "trigger": "explicit-judgment",
                    "start_snapshot": asdict(current),
                    "end_snapshot": asdict(current),
                    "delta": asdict(empty_delta),
                    "draft": literal_draft,
                    "page_id": None,
                    "page_url": None,
                    "synced_at": None,
                }
                if language is not None:
                    literal_envelope["journal_language"] = language
                path = root / "v2" / "pending" / f"{key}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                literal_bytes = canonical_json(literal_envelope)
                path.write_bytes(literal_bytes)

                reopened = store.read_envelope(key)

                self.assertEqual(literal_bytes, path.read_bytes())
                self.assertIsNone(reopened.draft.background)
                self.assertEqual(
                    expected_body,
                    render_judgment_body(reopened.draft, reopened.journal_language),
                )

                store.record_receipt(
                    key,
                    f"legacy-page-{language or 'unset'}",
                    f"https://www.notion.so/legacy-page-{language or 'unset'}",
                    SEOUL_NOW,
                )
                rewritten = json.loads(path.read_bytes())
                self.assertEqual(literal_draft, rewritten["draft"])
                self.assertEqual(key, rewritten["journal_key"])

    def test_legacy_background_absence_keeps_former_judgment_key_material(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            current = snapshot("1" * 40, "a" * 64, ())
            legacy_draft = judgment_draft(background=None)
            legacy_value = asdict(legacy_draft)
            legacy_value.pop("background")
            draft_digest = sha256(canonical_json(legacy_value)).hexdigest()
            expected_key = make_judgment_key(
                current.repository, current.digest, draft_digest
            )

            envelope = store.capture_explicit_judgment(
                current, legacy_draft, SEOUL_NOW
            )

            self.assertEqual(expected_key, envelope.journal_key)

    def test_explicit_null_background_is_not_legacy_absence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            current = snapshot("1" * 40, "a" * 64, ())
            envelope = store.capture_explicit_judgment(
                current, judgment_draft(background=None), SEOUL_NOW
            )
            path = root / "v2" / "pending" / f"{envelope.journal_key}.json"
            invalid = envelope.to_storage_dict()
            invalid["draft"]["background"] = None
            path.write_bytes(canonical_json(invalid))

            with self.assertRaises(JournalError):
                store.read_envelope(envelope.journal_key)

    def test_background_changes_new_judgment_key_material(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            current = snapshot("1" * 40, "a" * 64, ())

            first = store.capture_explicit_judgment(
                current, judgment_draft(background="First grounded context"), SEOUL_NOW
            )
            second = store.capture_explicit_judgment(
                current, judgment_draft(background="Second grounded context"), SEOUL_NOW
            )

            self.assertNotEqual(first.journal_key, second.journal_key)

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

    def test_receipt_accepts_current_app_notion_page_url_with_query(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            pending = self._capture_drafted(store)
            page_url = "https://app.notion.com/p/" + "a" * 32 + "?pvs=4"

            try:
                receipt = store.record_receipt(
                    pending.journal_key,
                    "page-result",
                    page_url,
                    SEOUL_NOW,
                )
            except JournalError as error:
                self.fail(f"current app Notion page URL should be accepted: {error}")

            self.assertEqual(page_url, receipt.page_url)
            self.assertEqual("synced", store.read_envelope(pending.journal_key).sync_state)
            self.assertEqual((), store.list_pending())

    def test_receipt_lookup_is_key_scoped_for_both_versions(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            legacy = self._capture_drafted(store)
            current = store.capture_explicit_judgment(
                legacy.end_snapshot, judgment_draft(), SEOUL_NOW, journal_language="ko",
            )
            for envelope in (legacy, current):
                with self.subTest(key=envelope.journal_key):
                    self.assertIsNone(store.read_receipt(envelope.journal_key))
                    expected = store.record_receipt(
                        envelope.journal_key, "page-result",
                        "https://www.notion.so/page-result", SEOUL_NOW,
                    )
                    self.assertEqual(expected, store.read_receipt(envelope.journal_key))

            receipt_path = store.v2_receipts / f"{current.journal_key}.json"
            valid_bytes = receipt_path.read_bytes()
            wrong_key = json.loads(valid_bytes)
            wrong_key["journal_key"] = legacy.journal_key
            receipt_path.write_bytes(canonical_json(wrong_key))
            with self.assertRaises(JournalError):
                store.read_receipt(current.journal_key)
            self.assertIsNotNone(store.read_receipt(legacy.journal_key))
            for invalid in ("../config", "cbj-v2-" + "x" * 24):
                with self.subTest(invalid=invalid), self.assertRaises(JournalError):
                    store.read_receipt(invalid)

    def test_receipt_rejects_unrecognized_notion_url_query(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            pending = self._capture_drafted(store)

            with self.assertRaises(JournalError):
                store.record_receipt(
                    pending.journal_key,
                    "page-result",
                    "https://app.notion.com/p/" + "a" * 32 + "?view=compact",
                    SEOUL_NOW,
                )

            self.assertEqual((), store.list_receipts())
            self.assertEqual("pending", store.read_envelope(pending.journal_key).sync_state)

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

    def test_explicit_judgment_is_idempotent_and_does_not_advance_sessions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            baseline = snapshot("1" * 40, "a" * 64, ())
            store.create_session("session-1", baseline, SEOUL_NOW)
            before = {
                path.name: path.read_bytes() for path in (root / "sessions").glob("*.json")
            }

            first = self._capture_judgment(store, baseline, judgment_draft())
            second = self._capture_judgment(store, baseline, judgment_draft())
            after = {
                path.name: path.read_bytes() for path in (root / "sessions").glob("*.json")
            }

            self.assertEqual(first, second)
            self.assertRegex(first.journal_key, r"^cbj-v2-[0-9a-f]{24}$")
            self.assertEqual("explicit-judgment", first.trigger)
            self.assertEqual((), first.delta.paths)
            self.assertEqual(before, after)
            self.assertEqual(judgment_draft(), store.read_envelope(first.journal_key).draft)

    def test_v2_state_is_isolated_from_legacy_directory_scans(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root)
            current = snapshot("1" * 40, "a" * 64, ())
            envelope = self._capture_judgment(store, current, judgment_draft())
            pending_path = root / "v2" / "pending" / f"{envelope.journal_key}.json"

            self.assertTrue(pending_path.is_file())
            self.assertEqual((), tuple((root / "pending").glob("*.json")))

            store.record_receipt(
                envelope.journal_key,
                "v2-page",
                "https://www.notion.so/v2-page",
                SEOUL_NOW,
            )

            receipt_path = root / "v2" / "receipts" / f"{envelope.journal_key}.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual((), tuple((root / "receipts").glob("*.json")))
            synced_envelope_bytes = pending_path.read_bytes()
            synced_receipt_bytes = receipt_path.read_bytes()
            for legacy_directory in (root / "pending", root / "receipts"):
                for path in legacy_directory.glob("*.json"):
                    json.loads(path.read_bytes())
            reopened = JournalStore(root)
            self.assertEqual("synced", reopened.read_envelope(envelope.journal_key).sync_state)
            self.assertEqual(1, len(reopened.list_receipts()))
            self.assertEqual(synced_envelope_bytes, pending_path.read_bytes())
            self.assertEqual(synced_receipt_bytes, receipt_path.read_bytes())

    def test_changed_confirmed_judgment_creates_a_distinct_v2_key(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            baseline = snapshot("1" * 40, "a" * 64, ())

            first = self._capture_judgment(store, baseline, judgment_draft())
            correction = judgment_draft(
                human_judgment="Require a user choice and an exact preview",
                supersedes=first.journal_key,
            )
            second = self._capture_judgment(store, baseline, correction)

            self.assertNotEqual(first.journal_key, second.journal_key)
            self.assertEqual(first.journal_key, second.draft.supersedes)
            self.assertEqual(first, store.read_envelope(first.journal_key))

    def test_correction_requires_a_retained_superseded_record(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            current = snapshot("1" * 40, "a" * 64, ())
            correction = judgment_draft(
                human_judgment="Correct a record that is not retained",
                supersedes="cbj-v2-" + "f" * 24,
            )

            with self.assertRaises(JournalError):
                self._capture_judgment(store, current, correction)

            self.assertEqual((), store.list_pending())

    def test_correction_cannot_supersede_an_undrafted_legacy_envelope(self):
        with TemporaryDirectory() as directory:
            store = JournalStore(Path(directory))
            legacy = self._capture(store)
            correction = judgment_draft(
                human_judgment="Do not legitimize an automatic empty envelope",
                supersedes=legacy.journal_key,
            )

            with self.assertRaises(JournalError):
                self._capture_judgment(store, legacy.end_snapshot, correction)

            self.assertEqual((legacy,), store.list_pending())

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

    def _capture_judgment(
        self, store: JournalStore, current: Snapshot, confirmed: JudgmentDraft
    ) -> PendingEnvelope:
        capture = getattr(store, "capture_explicit_judgment", None)
        self.assertTrue(callable(capture), "store must expose explicit judgment capture")
        return capture(current, confirmed, SEOUL_NOW)

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
