import unittest

from claimbranch.application.paper_draft import PaperDraftSession
from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError
from tests.application.test_paper_context import selection
from tests.contract.test_paper_history import paper, command, experiment
from tests.security.test_provider_output import reply


class PaperProviderTests(unittest.TestCase):
    def setUp(self):
        self.history, _ = paper()
        self.service = PaperService(self.history)
        self.before = self.history.manifest()
        self.now = 100
        self.session = PaperDraftSession(self.service, ref="alternative", frozen_response="A second seed is still unmeasured.", clock=lambda: self.now)

    def begin(self):
        outbound = self.session.prepare_request(selection(self.service))["outbound"]
        key = outbound["request"]["request_id"]
        result = self.session.begin_proposal(key, outbound["digest"])
        self.assertIsNone(result["proposal"])
        self.assertIsNone(result["outbound"])
        self.assertEqual("pending", result["attempt"]["state"])
        self.assertTrue(result["attempt"]["dispatched"])
        return key

    def test_edit_and_manual_review_work_while_waiting_and_late_result_cannot_replace_them(self):
        key = self.begin()
        self.session.edit("Keep the conclusion limited.", "Only mask 42 was measured.")
        self.session.review_draft()
        before = self.session.state()["draft"]
        state = self.session.complete_proposal(key)
        self.assertEqual("stale", state["attempt"]["state"])
        self.assertEqual(before, state["draft"])
        self.assertIsNone(state["proposal"])
        self.assertEqual("proposed", state["traces"][0]["disposition"])
        self.assertEqual(self.before, self.history.manifest())

    def test_cancel_timeout_clock_reversal_and_source_refresh_keep_response_unadoptable(self):
        for reason in ("cancel", "expire", "reverse", "source"):
            with self.subTest(reason=reason):
                self.setUp()
                key = self.begin()
                if reason == "cancel":
                    self.session.cancel_request()
                elif reason == "expire":
                    self.now = 220
                elif reason == "reverse":
                    self.now = 99
                else:
                    history = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="run-two")))
                    self.session.update_source(PaperService(history))
                state = self.session.complete_proposal(key)
                self.assertEqual({"cancel": "cancelled", "expire": "expired", "reverse": "expired", "source": "stale"}[reason], state["attempt"]["state"])
                self.assertIsNone(state["proposal"])
                self.assertEqual(1, len(state["traces"]))
                with self.assertRaises(ContractError):
                    self.session.complete_proposal(key)
                self.assertEqual(self.before, self.history.manifest())

    def test_old_completion_cannot_replace_new_proposal_or_consume_new_consent(self):
        old = self.begin()
        new = self.begin()
        newer = self.session.complete_proposal(new)["proposal"]
        state = self.session.complete_proposal(old)
        self.assertEqual(newer, state["proposal"])
        self.assertEqual(new, state["attempt"]["request_id"])
        self.assertEqual(["stale", "proposed"], [item["state"] for item in state["attempts"]])
        self.session.use_proposal(newer["id"])
        self.session.edit("Only one mask supports the narrow conclusion.", "Replication remains open.")
        reviewed = self.session.review_draft()
        self.session.erase_trace(new)
        self.assertEqual(list(reviewed["judgment"]["history"]), self.session.state()["draft"]["contributions"])
        self.assertEqual(self.before, self.history.manifest())

    def test_old_completion_preserves_a_new_undispatched_preview(self):
        old = self.begin()
        preview = self.session.prepare_request(selection(self.service))["outbound"]
        state = self.session.complete_proposal(old)
        self.assertEqual(preview, state["outbound"])
        self.assertEqual("pending", state["attempt"]["state"])
        self.assertFalse(state["attempt"]["dispatched"])

    def test_refused_and_malformed_results_are_visible_and_do_not_block_manual_work(self):
        for raw, expected in ((reply("refused", None), "refused"), (b"broken", "malformed"), (reply("failed", None), "failed")):
            with self.subTest(expected=expected):
                self.session = PaperDraftSession(self.service, ref="alternative", frozen_result=raw, clock=lambda: self.now)
                key = self.begin()
                state = self.session.complete_proposal(key)
                self.assertEqual("failed", state["attempt"]["state"])
                self.assertEqual(expected, state["traces"][0]["disposition"])
                self.assertIsNone(state["proposal"])
                self.session.edit("Continue manually.", "The provider was unavailable.")
                self.assertFalse(self.session.review_draft()["judgment"]["history"][0]["contributor"] == "ai")

    def test_unfinished_and_cancelled_dispatches_consume_the_three_attempt_limit(self):
        for _ in range(3):
            self.begin()
            self.session.cancel_request()
        with self.assertRaises(ContractError):
            self.begin()
        state = self.session.state()
        self.assertEqual(3, len(state["attempts"]))
        self.assertEqual([], state["traces"])
        state["attempts"][0]["state"] = "proposed"
        self.assertEqual("cancelled", self.session.state()["attempts"][0]["state"])
        self.session.edit("Manual continuation", "No AI required.")
        self.session.review_draft()

    def test_forged_dispatch_unknown_response_and_duplicate_completion_have_no_effect(self):
        preview = self.session.prepare_request(selection(self.service))["outbound"]
        with self.assertRaises(ContractError):
            self.session.begin_proposal(preview["request"]["request_id"], "a" * 64)
        with self.assertRaises(ContractError):
            self.session.complete_proposal(preview["request"]["request_id"])
        self.assertEqual([], self.session.state()["attempts"])
        key = self.begin()
        before = self.session.complete_proposal(key)
        with self.assertRaises(ContractError):
            self.session.complete_proposal(key)
        self.assertEqual(before, self.session.state())


if __name__ == "__main__":
    unittest.main()
