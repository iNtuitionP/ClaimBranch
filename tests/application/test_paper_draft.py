from copy import deepcopy
import unittest
from unittest.mock import patch

from claimbranch.application.paper_draft import PaperDraftSession
from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError
from claimbranch.core.context import OfflineBroker
from tests.application.test_paper_context import selection
from tests.contract.test_paper_history import paper, command, experiment


RESPONSE = "Repeat the 20 percent pruning evaluation with mask seed 43; its result remains unknown."


class PaperDraftTests(unittest.TestCase):
    def setUp(self):
        self.history, _ = paper(ai=True)
        self.service = PaperService(self.history)
        self.now = 100
        self.session = PaperDraftSession(self.service, ref="alternative", frozen_response=RESPONSE, clock=lambda: self.now)

    def preview(self):
        return self.session.prepare_request(selection(self.service))["outbound"]

    def dispatch(self, outbound):
        return self.session.request_proposal(outbound["request"]["request_id"], outbound["digest"])

    def test_first_pass_ai_preview_does_not_require_or_copy_a_complete_judgment(self):
        state = self.session.state()
        self.assertEqual("", state["draft"]["text"])
        self.assertEqual([], state["draft"]["contributions"])
        self.assertFalse(state["draft"]["ai_influenced"])
        self.assertEqual(self.service.query("alternative")["digest"], state["paper"]["view_digest"])
        outbound = self.preview()
        self.assertEqual(2, outbound["request"]["context"]["schema_version"])
        self.assertEqual("offline://frozen", outbound["request"]["destination"]["url"])
        self.assertEqual([], self.session.state()["traces"])
        self.assertEqual("", self.session.state()["draft"]["text"])

    def test_adoption_human_revision_review_and_not_now_preserve_lineage_without_writes(self):
        before = self.history.manifest()
        with patch("socket.socket", side_effect=AssertionError("network used")):
            outbound = self.preview()
            proposed = self.dispatch(outbound)
            self.assertEqual(RESPONSE, proposed["proposal"]["text"])
            self.assertEqual("", proposed["draft"]["text"])
            self.session.use_proposal(proposed["proposal"]["id"])
            self.session.edit("Limit the claim to mask seed 42 until seed 43 is measured.", "One recorded mask cannot establish replication.")
            review = self.session.review_draft()
            self.assertEqual(["ai", "human"], [item["contributor"] for item in review["judgment"]["history"]])
            self.assertEqual(RESPONSE, review["judgment"]["history"][0]["text"])
            self.assertEqual(review, self.session.review_draft())
            state = self.session.not_now()
            self.assertTrue(state["draft"]["ai_influenced"])
            self.assertEqual(0, state["accepted_writes"])
            self.assertFalse(review["authorization_verified"])
            self.assertEqual(before, self.history.manifest())

    def test_ai_off_manual_work_and_incomplete_text_remain_available(self):
        manual = PaperDraftSession(self.service, ref="alternative", clock=lambda: self.now)
        manual.edit("An incomplete interpretation", "")
        self.assertEqual("An incomplete interpretation", manual.not_now()["draft"]["text"])
        with self.assertRaises(ContractError):
            manual.review_draft()
        with self.assertRaises(ContractError):
            manual.prepare_request(selection(self.service))
        manual.edit("Keep both interpretations open.", "The planned replication has no result.")
        review = manual.review_draft()
        self.assertEqual(["human"], [item["contributor"] for item in review["judgment"]["history"]])
        self.assertEqual([], manual.state()["traces"])

    def test_partial_draft_is_recoverable_after_explicit_proposal_adoption(self):
        self.session.edit("Could this be pruning-mask variance?", "")
        proposal = self.dispatch(self.preview())["proposal"]
        state = self.session.use_proposal(proposal["id"])
        self.assertEqual({"text": "Could this be pruning-mask variance?", "rationale": ""}, state["before_proposal"])
        self.assertEqual(RESPONSE, state["draft"]["text"])
        self.assertTrue(state["draft"]["ai_influenced"])

    def test_cancel_edit_expiry_repreview_and_digest_mismatch_cannot_dispatch(self):
        for change in ("cancel", "edit", "expire", "preview", "digest"):
            with self.subTest(change=change):
                self.setUp()
                outbound = self.preview()
                if change == "cancel":
                    self.session.cancel_request()
                elif change == "edit":
                    self.session.edit("Changed then reverted", "")
                    self.session.edit("", "")
                elif change == "expire":
                    self.now = 220
                elif change == "preview":
                    self.preview()
                else:
                    outbound = deepcopy(outbound)
                    outbound["digest"] = "a" * 64
                with self.assertRaises(ContractError):
                    self.dispatch(outbound)
                self.assertEqual([], self.session.state()["traces"])

    def test_changed_source_or_expired_result_cannot_be_adopted(self):
        for change in ("source", "edit", "expire", "cancel"):
            with self.subTest(change=change):
                self.setUp()
                proposal = self.dispatch(self.preview())["proposal"]
                if change == "source":
                    updated = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="second-run")))
                    self.session.update_source(PaperService(updated))
                elif change == "edit":
                    self.session.edit("Keep my draft", "")
                elif change == "expire":
                    self.now = 220
                else:
                    self.session.cancel_request()
                with self.assertRaises(ContractError):
                    self.session.use_proposal(proposal["id"])
                self.assertFalse(self.session.state()["draft"]["ai_influenced"])

    def test_repeated_dispatch_adoption_and_exhausted_budget_fail_without_extra_effect(self):
        first = self.preview()
        proposal = self.dispatch(first)["proposal"]
        self.session.use_proposal(proposal["id"])
        for action in (lambda: self.dispatch(first), lambda: self.session.use_proposal(proposal["id"])):
            with self.assertRaises(ContractError):
                action()
        for _ in range(2):
            self.dispatch(self.preview())
        with self.assertRaises(ContractError):
            self.preview()
        self.assertEqual(3, len(self.session.state()["traces"]))
        self.assertEqual(1, len(self.session.state()["draft"]["contributions"]))

    def test_erasure_detached_state_and_wrong_source_do_not_erase_provenance(self):
        proposal = self.dispatch(self.preview())["proposal"]
        self.session.use_proposal(proposal["id"])
        before = self.session.state()["draft"]["contributions"]
        request_id = self.session.state()["traces"][0]["request_id"]
        self.session.erase_trace(request_id)
        state = self.session.state()
        self.assertEqual(before, state["draft"]["contributions"])
        self.assertEqual("erased", state["traces"][0]["payload_availability"])
        state["draft"]["contributions"].clear()
        self.assertEqual(before, self.session.state()["draft"]["contributions"])
        other = type(self.history).start_paper("other", "episode", "Other paper", "t", "Thesis", "a")
        with self.assertRaises(ContractError):
            self.session.update_source(PaperService(other))

    def test_complete_human_draft_precedes_ai_and_failed_adoption_is_atomic_at_history_bound(self):
        self.session.edit("A human first interpretation.", "Only one pruning seed was observed.")
        self.session.review_draft()
        for index in range(6):
            self.session.edit(f"Human revision {index}", "Keep the scope limited.")
            self.session.review_draft()
        proposal = self.dispatch(self.preview())["proposal"]
        self.session.use_proposal(proposal["id"])
        contributions = self.session.state()["draft"]["contributions"]
        self.assertEqual(["human"] * 7 + ["ai"], [item["contributor"] for item in contributions])
        proposal = self.dispatch(self.preview())["proposal"]
        before = self.session.state()["draft"]
        with self.assertRaises(ContractError):
            self.session.use_proposal(proposal["id"])
        self.assertEqual(before, self.session.state()["draft"])

    def test_response_that_arrives_after_expiry_is_traced_but_never_adoptable(self):
        original = OfflineBroker.complete

        def late(broker, *args, **kwargs):
            result = original(broker, *args, **kwargs)
            self.now = 220
            return result

        outbound = self.preview()
        with patch.object(OfflineBroker, "complete", autospec=True, side_effect=late), self.assertRaises(ContractError):
            self.dispatch(outbound)
        state = self.session.state()
        self.assertEqual("expired", state["attempt"]["state"])
        self.assertIsNone(state["proposal"])
        self.assertEqual(1, len(state["traces"]))
        self.assertEqual("", state["draft"]["text"])
        self.session.edit("Continue manually.", "The response was late.")
        self.session.review_draft()

    def test_current_incomplete_draft_is_shared_only_by_explicit_selection(self):
        self.session.edit("Could mask variance explain this?", "")
        without = self.preview()["request"]["context"]
        self.assertFalse(any(item["kind"] == "draft" for item in without["records"]))
        outbound = self.session.prepare_request(selection(self.service), include_draft=True)["outbound"]
        fields = next(item["fields"] for item in outbound["request"]["context"]["records"] if item["kind"] == "draft")
        self.assertEqual("Could mask variance explain this?", fields["statement"])
        self.assertIsNone(fields["rationale"])
        self.assertFalse(fields["origin"]["ai_influenced"])
        proposal = self.dispatch(outbound)["proposal"]
        self.session.use_proposal(proposal["id"])
        self.session.edit("Limit the interpretation.", "The new mask is untested.")
        outbound = self.session.prepare_request(selection(self.service), include_draft=True)["outbound"]
        fields = next(item["fields"] for item in outbound["request"]["context"]["records"] if item["kind"] == "draft")
        self.assertTrue(fields["origin"]["ai_influenced"])

    def test_private_draft_screening_does_not_prevent_manual_or_paper_only_work(self):
        self.session.edit("Results are at /Users/researcher/private/data.csv", "")
        for include in (True, "true", 1):
            with self.subTest(include=include), self.assertRaises(ContractError):
                self.session.prepare_request(selection(self.service), include_draft=include)
        self.assertEqual([], self.session.state()["traces"])
        self.preview()
        self.session.not_now()
        self.assertIn("/Users/researcher", self.session.state()["draft"]["text"])


if __name__ == "__main__":
    unittest.main()
