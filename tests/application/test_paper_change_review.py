from copy import deepcopy
import unittest

from claimbranch.application.paper_draft import PaperDraftSession
from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_changes import amendments, judgment
from tests.contract.test_paper_history import command, experiment, paper


def request(session, history, *, ref="main", selected=None):
    state = session.state()
    return {"schema_version": 1, **state["paper"], "draft_id": state["draft_id"],
            "draft_revision": state["revision"], "amendments": amendments(history, ref),
            "selected_ids": selected or ["edge-pruning"]}


class PaperChangeReviewTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example("manual", paper=True)
        self.service = PaperService(self.history)
        self.now = 100
        self.session = PaperDraftSession(self.service, clock=lambda: self.now)
        draft = judgment(self.history)
        self.session.edit(draft.text, draft.rationale)

    def test_preview_connects_the_draft_to_before_after_and_omitted_effects(self):
        original = self.history.manifest()
        prepared = self.session.prepare_changes(request(self.session, self.history))
        preview = prepared["preview"]
        self.assertEqual("claimbranch.paper-changes/v1", preview["schema"])
        self.assertEqual(["replication"], preview["selection"]["omitted"])
        self.assertEqual(["claim-pruning-detail"], preview["impact"]["directly_changed_claim_ids"])
        self.assertEqual(["claim-pruning", "claim-pruning-detail", "thesis"], preview["impact"]["potentially_affected_claim_ids"])
        self.assertEqual(["claim-comparison"], preview["impact"]["outside_impact_claim_ids"])
        self.assertEqual(["obs-1", "obs-2"], preview["impact"]["unchanged_evidence_ids"])
        self.assertEqual(["anchor"], preview["impact"]["potentially_affected_anchor_ids"])
        self.assertFalse(preview["manuscript"]["source_verified"])
        self.assertFalse(preview["acceptance_available"])
        self.assertEqual(self.session.state()["draft"]["rationale"], preview["provenance"]["judgment"]["rationale"])
        self.assertEqual(original, self.history.manifest())
        self.assertEqual(prepared, self.session.get_changes_preview())
        prepared["preview"]["graphs"]["after"]["nodes"].clear()
        self.assertTrue(self.session.get_changes_preview()["preview"]["graphs"]["after"]["nodes"])

    def test_manual_review_reuses_rationale_and_not_now_preserves_draft(self):
        prepared = self.session.prepare_changes(request(self.session, self.history))
        reviewed = self.session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        self.assertEqual(reviewed, self.session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[]))
        self.assertEqual(prepared["digest"], reviewed["preview_digest"])
        self.assertFalse(reviewed["authorization_verified"])
        self.assertFalse(reviewed["acceptance_available"])
        self.assertFalse(reviewed["consequences_if_accepted"]["understanding_debt"])
        before = self.session.state()["draft"]
        state = self.session.not_now()
        self.assertIsNone(state["changes_preview"])
        self.assertIsNone(state["changes_review"])
        self.assertEqual(before, state["draft"])
        self.assertEqual(0, state["accepted_writes"])

    def test_source_ai_requires_explanation_even_when_the_new_draft_is_human(self):
        history = replay_example("recorded", paper=True)
        session = PaperDraftSession(PaperService(history), clock=lambda: self.now)
        draft = judgment(history)
        session.edit(draft.text, draft.rationale)
        prepared = session.prepare_changes(request(session, history))
        self.assertFalse(session.state()["draft"]["ai_influenced"])
        self.assertTrue(prepared["preview"]["provenance"]["ai_influenced"])
        with self.assertRaises(ContractError):
            session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        reviewed = session.finish_changes_review(prepared["digest"], disposition="deferred", answers=[])
        self.assertTrue(reviewed["consequences_if_accepted"]["understanding_debt"])
        answered = session.finish_changes_review(prepared["digest"], disposition="answered", answers=["Only seed 42 was observed; seed 43 is still a plan."])
        self.assertNotEqual(reviewed["digest"], answered["digest"])
        self.assertFalse(answered["consequences_if_accepted"]["understanding_debt"])

    def test_edit_reselection_not_now_expiry_and_source_change_invalidate_review(self):
        for event in ("edit", "selection", "not-now", "expiry", "clock-reversal", "source"):
            with self.subTest(event=event):
                self.setUp()
                prepared = self.session.prepare_changes(request(self.session, self.history))
                if event == "edit":
                    self.session.edit("A new interpretation.", "A different explanation.")
                elif event == "selection":
                    self.session.prepare_changes(request(self.session, self.history, selected=["replication"]))
                elif event == "not-now":
                    self.session.not_now()
                elif event == "expiry":
                    self.now = 400
                elif event == "clock-reversal":
                    self.now = 99
                else:
                    changed = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="second-run")))
                    self.session.update_source(PaperService(changed))
                with self.assertRaises(ContractError):
                    self.session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
                self.assertEqual(0, self.session.state()["accepted_writes"])

    def test_ai_adoption_invalidates_review_even_when_proposal_text_matches(self):
        from claimbranch.application.paper_example import context_request
        draft = judgment(self.history)
        session = PaperDraftSession(self.service, frozen_response=draft.text, clock=lambda: self.now)
        session.edit(draft.text, draft.rationale)
        prepared = session.prepare_changes(request(session, self.history))
        session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        outbound = session.prepare_request(context_request(self.service))["outbound"]
        proposal = session.request_proposal(outbound["request"]["request_id"], outbound["digest"])["proposal"]
        session.use_proposal(proposal["id"])
        self.assertEqual(draft.text, session.state()["draft"]["text"])
        self.assertTrue(session.state()["draft"]["ai_influenced"])
        self.assertIsNone(session.get_changes_review())
        with self.assertRaises(ContractError):
            session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])

    def test_changed_cross_session_or_injected_requests_preserve_the_previous_review(self):
        req = request(self.session, self.history)
        prepared = self.session.prepare_changes(req)
        for override in ({"draft_id": "another-draft"}, {"draft_revision": 0}, {"view_digest": "a" * 64},
                         {"project_id": "other"}, {"episode_id": "other"}, {"ref": "alternative"},
                         {"authorized": True}, {"schema_version": True}):
            with self.subTest(override=override), self.assertRaises(ContractError):
                self.session.prepare_changes(dict(req, **override))
        self.assertEqual(prepared, self.session.get_changes_preview())
        other = PaperDraftSession(self.service)
        other.edit(self.session.state()["draft"]["text"], self.session.state()["draft"]["rationale"])
        with self.assertRaises(ContractError):
            other.prepare_changes(req)

    def test_structural_parents_do_not_infer_impact_and_omitted_interpretation_stays_put(self):
        history, _ = paper()
        last = decode(history.commands[-1])
        last["payload"]["changes"] = [item for item in last["payload"]["changes"] if item["id"] not in ("edge-detail", "edge-thesis")]
        history = ResearchHistory(history.seed, history.commands[:-1]).append(last)
        session = PaperDraftSession(PaperService(history), ref="alternative", clock=lambda: self.now)
        draft = judgment(history)
        session.edit(draft.text, draft.rationale)
        req = request(session, history, ref="alternative")
        interp = deepcopy(history.view("alternative")["interpretations"][0])
        interp["body"]["statement"] = draft.text
        req["amendments"].append(interp)
        result = session.prepare_changes(req)["preview"]
        self.assertIn("interpretation", result["selection"]["omitted"])
        self.assertEqual(["claim-pruning-detail"], result["impact"]["potentially_affected_claim_ids"])
        self.assertEqual([], result["impact"]["potentially_affected_anchor_ids"])
        before = next(item for item in result["graphs"]["before"]["nodes"] if item["id"] == "interpretation")
        after = next(item for item in result["graphs"]["after"]["nodes"] if item["id"] == "interpretation")
        self.assertEqual(before, after)

    def test_retargeted_relation_shows_old_and_new_reach_without_changing_status(self):
        req = request(self.session, self.history)
        req["amendments"] = [deepcopy(req["amendments"][1])]
        req["amendments"][0]["body"]["target_id"] = "claim-comparison"
        result = self.session.prepare_changes(req)["preview"]
        self.assertEqual(["claim-comparison", "claim-pruning", "claim-pruning-detail", "thesis"], result["impact"]["potentially_affected_claim_ids"])
        self.assertEqual([], result["impact"]["directly_changed_claim_ids"])
        self.assertEqual({"before", "after"}, {path["phase"] for path in result["impact"]["witness_paths"]})
        self.assertTrue(result["impact"]["requires_human_judgment"])

    def test_same_scope_reprepared_and_changed_history_still_reject_old_bindings(self):
        req = request(self.session, self.history)
        first = self.session.prepare_changes(req)
        second = self.session.prepare_changes(req)
        self.assertNotEqual(first["digest"], second["digest"])
        with self.assertRaises(ContractError):
            self.session.finish_changes_review(first["digest"], disposition="not-required", answers=[])
        added = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="second-run")))
        self.assertEqual(added.heads, self.history.heads)
        self.assertEqual(added.watermark, self.history.watermark)
        with self.assertRaises(ContractError):
            PaperService(added).preview_changes(req, judgment(self.history))

    def test_review_completion_rejects_tampering_and_cannot_be_a_core_receipt(self):
        from claimbranch.core.review import acceptance_candidate
        prepared = self.session.prepare_changes(request(self.session, self.history))
        with self.assertRaises(ContractError):
            self.session.finish_changes_review("a" * 64, disposition="not-required", answers=[])
        for disposition, answers in (("answered", []), ("deferred", ["answer"]), ("not-required", ["x"]),
                                     ("not-required", "answer"), ("not-required", ["x"] * 4)):
            with self.subTest(disposition=disposition), self.assertRaises(ContractError):
                self.session.finish_changes_review(prepared["digest"], disposition=disposition, answers=answers)
        reviewed = self.session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        with self.assertRaises(ContractError):
            acceptance_candidate(reviewed, decision="accept")
        reviewed["authorization_verified"] = True
        self.assertFalse(self.session.get_changes_review()["authorization_verified"])

    def test_incomplete_judgment_keeps_manual_work_and_opens_no_preview(self):
        self.session.edit("Still deciding.", "")
        with self.assertRaises(ContractError):
            self.session.prepare_changes(request(self.session, self.history))
        self.assertEqual("Still deciding.", self.session.state()["draft"]["text"])
        self.assertIsNone(self.session.get_changes_preview())


if __name__ == "__main__":
    unittest.main()
