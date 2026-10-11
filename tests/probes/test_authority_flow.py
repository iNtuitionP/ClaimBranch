"""Synthetic integrated authority/storage/file behavior; no OS authority."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contracts.first_pass import (
    ContractError, ManuscriptTarget, prepare_review, record_judgment, start_draft,
)
from scripts.probes.authority_flow import Operation, SyntheticAuthorityFlow
from scripts.probes.frozen_provider import PendingProposal
from scripts.probes.workspace_storage import ProbeError


ROOT = Path(__file__).resolve().parents[2]
BEFORE, AFTER = b"synthetic before\n", b"synthetic after\n"


def operation(key="first", head=0):
    draft = record_judgment(start_draft("synthetic", "episode", "evidence", "claim"),
                            "human judgment", "근거를 한 번만 입력\nexact rationale")
    review = prepare_review(draft, manuscript_target=ManuscriptTarget(
        "anchor", hashlib.sha256(BEFORE).hexdigest()))
    return Operation(key, head, review, BEFORE, AFTER, ("claim-status",))


class AuthorityFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claimbranch-storage-probe-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.paper = self.root / "paper"
        self.paper.mkdir()
        (self.paper / ".git").mkdir()
        (self.paper / "manuscript.tex").write_bytes(BEFORE)
        (self.root / "workspaces").mkdir()
        self.flow = self.open_flow()
        self.flow.initialize("synthetic")
        self.flow.start_session("synthetic")
        self.now = [1]
        self.op = operation()
        self.current = [self.op.review]

    def open_flow(self):
        return SyntheticAuthorityFlow.for_project(
            self.root, self.root / "workspaces", self.paper, "synthetic")

    def issue(self, op=None, verdict=True):
        op = op or self.op
        return self.flow.begin(op, load_review=lambda: self.current[0],
            verify_response=lambda request, response: verdict,
            clock=lambda: self.now[0], expires_at=10, nonce=b"N" * 32)

    def match(self, op=None):
        token = self.issue(op)
        result = self.flow.respond(token, object())
        self.assertEqual("matched", result.status)
        self.assertFalse(result.authorization_verified)
        return token

    def test_atomic_record_reopen_exact_retry_and_no_file_write_until_apply(self):
        token = self.match()
        result = self.flow.commit(self.op, token)
        self.assertEqual(1, result["head"])
        self.assertEqual("prepared", result["patch_state"])
        self.assertEqual(self.op.review.draft.rationale, result["payload"]["review"]["draft"]["rationale"])
        self.assertEqual(BEFORE, (self.paper / "manuscript.tex").read_bytes())
        reopened = self.open_flow()
        reopened.start_session("synthetic")
        self.assertEqual(result, reopened.commit(self.op, token))
        self.assertEqual(1, len(reopened.records()))
        with self.assertRaises(ProbeError):
            reopened.commit(replace(self.op, after=b"changed"), token)
        with self.assertRaises(ProbeError):
            reopened.commit(self.op, "different-attempt")

    def test_replay_under_new_key_cannot_consume_again(self):
        token = self.match()
        self.flow.commit(self.op, token)
        with self.assertRaises(ProbeError):
            self.flow.commit(replace(self.op, key="second"), token)
        self.assertEqual(1, len(self.flow.records()))

    def test_receiver_cancellation_after_matching_still_prevents_consumption(self):
        token = self.match()
        self.flow.cancel(token)
        with self.assertRaises(ProbeError):
            self.flow.commit(self.op, token)
        self.assertEqual([], self.flow.records())

    def test_final_review_callback_cannot_revoke_then_still_commit(self):
        revoke = [False]
        def changed_reader():
            if revoke[0]:
                self.flow.cancel(token)
            return self.op.review
        token = self.flow.begin(self.op, load_review=changed_reader,
            verify_response=lambda *_: True, clock=lambda: 1, expires_at=10, nonce=b"N" * 32)
        self.flow.respond(token, None)
        revoke[0] = True
        with self.assertRaises(ProbeError):
            self.flow.commit(self.op, token)
        self.assertEqual([], self.flow.records())

    def test_hostile_cancelled_and_valid_proposals_leave_storage_and_file_unchanged(self):
        draft = self.op.review.draft
        for mode in ("hostile", "cancelled", "valid"):
            with self.subTest(mode=mode):
                pending = PendingProposal("request", draft)
                payload = {"operation": "accept" if mode == "hostile" else "propose", "text": "change it"}
                if mode == "cancelled":
                    pending.cancel()
                if mode == "valid":
                    self.assertFalse(pending.deliver("request", payload, current=draft).accepted)
                else:
                    with self.assertRaises(ContractError):
                        pending.deliver("request", payload, current=draft)
                self.assertEqual([], self.flow.records())
                self.assertEqual(BEFORE, (self.paper / "manuscript.tex").read_bytes())
        # Provider failures do not block the separate manual path.
        self.assertEqual(1, self.flow.commit(self.op, self.match())["head"])

    def test_pending_cancelled_rejected_expired_and_rollback_clock_do_not_write(self):
        for mode in ("pending", "cancelled", "rejected", "expired", "clock-rollback"):
            with self.subTest(mode=mode):
                self.now[0] = 1
                token = self.issue(verdict=mode != "rejected")
                if mode == "cancelled":
                    self.flow.cancel(token)
                elif mode != "pending":
                    self.flow.respond(token, None)
                if mode == "expired":
                    self.now[0] = 10
                if mode == "clock-rollback":
                    self.now[0] = 0
                with self.assertRaises(ProbeError):
                    self.flow.commit(self.op, token)
                self.assertEqual([], self.flow.records())

    def test_stale_review_file_head_project_and_substituted_operation_do_not_write(self):
        token = self.match()
        self.current[0] = prepare_review(record_judgment(self.op.review.draft,
            "changed judgment", "changed reason"), manuscript_target=self.op.review.manuscript_target)
        with self.assertRaises(ProbeError):
            self.flow.commit(self.op, token)
        self.current[0] = self.op.review
        for changed in (replace(self.op, expected_head=3), replace(self.op, after=b"other"),
                        replace(self.op, selected=("interpretation",))):
            with self.assertRaises(ProbeError):
                self.flow.commit(changed, token)
        (self.paper / "manuscript.tex").write_bytes(b"external edit")
        with self.assertRaises(ProbeError):
            self.flow.commit(self.op, token)
        foreign = prepare_review(replace(self.op.review.draft, project_id="other"),
                                 manuscript_target=self.op.review.manuscript_target)
        with self.assertRaises(ProbeError):
            self.issue(replace(self.op, review=foreign))
        self.assertEqual([], self.flow.records())

    def test_receiver_restart_invalidates_old_receiver_and_outstanding_requests(self):
        token = self.match()
        reopened = self.open_flow()
        reopened.start_session("synthetic")
        for receiver in (self.flow, reopened):
            with self.assertRaises(ProbeError):
                receiver.commit(self.op, token)
        self.assertEqual([], reopened.records())

    def test_paper_rebinding_cannot_retarget_approval_or_recorded_patch(self):
        other = self.root / "other-paper"
        other.mkdir()
        (other / "manuscript.tex").write_bytes(BEFORE)
        token = self.match()
        with self.assertRaises(ProbeError):
            self.flow.rebind("synthetic", other)
        self.flow.commit(self.op, token)
        with self.assertRaises(ProbeError):
            self.flow.rebind("synthetic", other)
        self.flow.apply(self.op.key)
        self.assertEqual(AFTER, (self.paper / "manuscript.tex").read_bytes())
        self.assertEqual(BEFORE, (other / "manuscript.tex").read_bytes())

    def test_concurrent_consumers_have_one_record_and_one_head(self):
        token = self.match()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.flow.commit(self.op, token), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(1, len(self.flow.records()))
        self.assertEqual(1, results[0]["head"])

    def test_competing_operations_recheck_expected_head_at_transaction(self):
        first = self.match()
        other = replace(self.op, key="other")
        second = self.match(other)
        self.flow.commit(self.op, first)
        self.flow.apply(self.op.key)
        self.flow.restore(self.op.key)
        with self.assertRaises(ProbeError):
            self.flow.commit(other, second)
        self.assertEqual(1, len(self.flow.records()))

    def test_apply_restore_and_retry_preserve_append_only_judgment(self):
        self.flow.commit(self.op, self.match())
        for _ in range(2):
            self.assertEqual("applied", self.flow.apply(self.op.key))
            self.assertEqual(AFTER, (self.paper / "manuscript.tex").read_bytes())
        for _ in range(2):
            self.assertEqual("restored", self.flow.restore(self.op.key))
            self.assertEqual(BEFORE, (self.paper / "manuscript.tex").read_bytes())
        self.assertEqual(1, len(self.flow.records()))

    def test_unexpected_edit_and_symlink_are_preserved(self):
        self.flow.commit(self.op, self.match())
        manuscript = self.paper / "manuscript.tex"
        manuscript.write_bytes(b"unreviewed external edit")
        with self.assertRaises(ProbeError):
            self.flow.apply(self.op.key)
        self.assertEqual(b"unreviewed external edit", manuscript.read_bytes())
        target = self.root / "unrelated.tex"
        target.write_bytes(BEFORE)
        manuscript.unlink()
        try:
            manuscript.symlink_to(target)
        except OSError:
            manuscript.write_bytes(BEFORE)
            return  # Windows may deny unprivileged symlink creation.
        with self.assertRaises(ProbeError):
            self.flow.apply(self.op.key)
        self.assertEqual(BEFORE, target.read_bytes())

    def child(self, action, cut):
        code = """
import os, sys
from pathlib import Path
from scripts.probes.authority_flow import SyntheticAuthorityFlow
from tests.probes.test_authority_flow import operation
root = Path(sys.argv[1])
flow = SyntheticAuthorityFlow.for_project(root, root/'workspaces', root/'paper', 'synthetic')
flow.start_session('synthetic')
def checkpoint(stage):
    if stage == sys.argv[3]: os._exit(23)
if sys.argv[2] == 'commit':
    op = operation()
    token = flow.begin(op, load_review=lambda: op.review, verify_response=lambda *_: True,
                      clock=lambda: 1, expires_at=10, nonce=b'N'*32)
    flow.respond(token, None)
    flow.commit(op, token, checkpoint=checkpoint)
else:
    getattr(flow, sys.argv[2])('first', checkpoint=checkpoint)
"""
        return subprocess.run([sys.executable, "-c", code, str(self.root), action, cut],
                              cwd=ROOT, capture_output=True, timeout=15)

    def test_process_crash_before_commit_rolls_back_operation_and_consumption(self):
        result = self.child("commit", "before_commit")
        self.assertEqual(23, result.returncode, result.stderr)
        self.flow.start_session("synthetic")
        self.assertEqual([], self.flow.records())
        self.assertEqual(1, self.flow.commit(self.op, self.match())["head"])

    def test_process_crash_after_commit_retains_exact_record_for_status_retry(self):
        result = self.child("commit", "after_commit")
        self.assertEqual(23, result.returncode, result.stderr)
        self.flow.start_session("synthetic")
        records = self.flow.records()
        self.assertEqual(1, len(records))
        self.assertEqual(records[0], self.flow.commit(self.op, records[0]["attempt_id"]))

    def test_apply_and_restore_crashes_recover_from_intent_and_file_replace(self):
        self.flow.commit(self.op, self.match())
        for action, cut, expected in (
            ("apply", "after_apply_intent", AFTER),
            ("restore", "after_restore_intent", BEFORE),
        ):
            result = self.child(action, cut)
            self.assertEqual(23, result.returncode, result.stderr)
            self.flow.start_session("synthetic")
            self.flow.recover(self.op.key)
            self.assertEqual(expected, (self.paper / "manuscript.tex").read_bytes())

    def test_crash_after_file_replace_recovers_without_duplicate_write_or_record(self):
        self.flow.commit(self.op, self.match())
        for action, expected in (("apply", AFTER), ("restore", BEFORE)):
            result = self.child(action, "after_file_replace")
            self.assertEqual(23, result.returncode, result.stderr)
            self.flow.start_session("synthetic")
            self.assertEqual(expected, (self.paper / "manuscript.tex").read_bytes())
            self.flow.recover(self.op.key)
            self.assertEqual(expected, (self.paper / "manuscript.tex").read_bytes())
            self.assertEqual(1, len(self.flow.records()))

    def test_recovery_does_not_overwrite_post_crash_external_edit(self):
        self.flow.commit(self.op, self.match())
        self.assertEqual(23, self.child("apply", "after_apply_intent").returncode)
        self.flow.start_session("synthetic")
        (self.paper / "manuscript.tex").write_bytes(b"preserve my edit")
        with self.assertRaises(ProbeError):
            self.flow.recover(self.op.key)
        self.assertEqual(b"preserve my edit", (self.paper / "manuscript.tex").read_bytes())
        self.assertEqual("applying", self.flow.records()[0]["patch_state"])
