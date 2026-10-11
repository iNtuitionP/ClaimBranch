import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.application.workspace import DemoWorkspace, Unavailable, preview_marked_text
import hashlib


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.workspace = DemoWorkspace(clock=lambda: self.now)

    def write(self):
        self.workspace.edit("Sensitivity alone is insufficient.", "The three operator results differ.")

    def test_entry_is_undecided_and_manual_review_reuses_the_entered_rationale(self):
        self.assertEqual("", self.workspace.state()["draft"]["text"])
        self.assertIsNone(self.workspace.state()["proposal"])
        self.write()
        state = self.workspace.prepare(["claim-status"], "not-required", [])
        self.assertEqual("The three operator results differ.", state["review"]["rationale"])
        self.assertIn("I-01", state["review"]["required"])
        self.assertEqual(["optional-experiment"], state["review"]["omitted"])
        self.assertEqual(0, state["accepted_writes"])

    def test_not_now_retains_draft_but_does_not_create_debt_or_accepted_state(self):
        self.write()
        self.workspace.prepare(["claim-status"], "not-required", [])
        state = self.workspace.not_now()
        self.assertEqual("Sensitivity alone is insufficient.", state["draft"]["text"])
        self.assertIsNone(state["review"])
        self.assertEqual([], state["pending_debts"])
        self.assertEqual(0, state["accepted_writes"])

    def test_provider_preview_can_be_cancelled_and_changed_content_cannot_dispatch(self):
        preview = self.workspace.preview_request()
        self.workspace.edit("Different draft", "Different reason")
        with self.assertRaises(ContractError):
            self.workspace.request_proposal(preview["outbound"]["request_id"])
        self.assertEqual(0, len(self.workspace.broker.sent))
        self.workspace.preview_request()
        self.workspace.cancel_request()
        self.assertIsNone(self.workspace.state()["outbound"])

    def test_ai_editing_preserves_original_and_explicit_deferral_in_candidate(self):
        state = self.workspace.preview_request()
        state = self.workspace.request_proposal(state["outbound"]["request_id"])
        original = state["proposal"]["text"]
        self.workspace.use_proposal()
        self.write()
        state = self.workspace.prepare(["claim-status"], "deferred", [])
        history = state["review"]["contributions"]
        self.assertEqual(original, history[0]["text"])
        self.assertEqual(["ai", "human"], [item["contributor"] for item in history])
        result = self.workspace.preview_result()
        self.assertEqual(["manuscript", "understanding"], result["result"]["candidate_debts"])
        self.assertEqual([], result["pending_debts"])
        self.assertEqual(0, result["accepted_writes"])

    def test_proposal_adoption_preserves_incomplete_human_buffer_for_recovery(self):
        original = {"text": "My unfinished reading of the operator results", "rationale": ""}
        self.workspace.edit(**original)
        request_id = self.workspace.preview_request()["outbound"]["request_id"]
        self.workspace.request_proposal(request_id)
        state = self.workspace.use_proposal()
        self.assertEqual(original, state["before_proposal"])
        self.assertNotEqual(original["text"], state["draft"]["text"])
        self.assertEqual(["ai"], [item.contributor for item in self.workspace.judgment.history])
        state["before_proposal"]["text"] = "Mutated outside the workspace"
        self.workspace.edit(**original)
        self.assertEqual(original, self.workspace.not_now()["before_proposal"])
        self.assertTrue(self.workspace.state()["draft"]["ai_influenced"])
        self.assertEqual(0, self.workspace.state()["accepted_writes"])

    def test_edit_expiry_and_wrong_revision_invalidate_prepared_review(self):
        self.write()
        self.workspace.prepare(["claim-status"], "not-required", [])
        self.now = 1300
        with self.assertRaises(ContractError):
            self.workspace.preview_result()
        self.now = 1400
        self.workspace.prepare(["claim-status"], "not-required", [])
        self.workspace.edit("Changed meaning", "Changed reason")
        with self.assertRaises(ContractError):
            self.workspace.preview_result()

    def test_real_acceptance_and_project_import_remain_unavailable(self):
        self.write()
        with self.assertRaises(Unavailable):
            self.workspace.accept()
        self.assertEqual(0, self.workspace.state()["accepted_writes"])

    def test_source_preview_escapes_tex_commands_and_keeps_original_bytes(self):
        before = self.workspace.source_before
        self.workspace.edit(r"Claim \input{/tmp/private} & 50%", "Review exact text")
        state = self.workspace.prepare(["claim-status"], "not-required", [])
        after = state["review"]["manuscript_after"]
        self.assertNotIn(r"\input{", after)
        self.assertIn(r"\&", after)
        self.assertEqual(before, self.workspace.source_before)

    def test_omitted_or_unconnected_interpretation_cannot_become_manuscript_wording(self):
        self.write()
        for selected in (["optional-experiment"], ["I-01"], ["edge-O-01"]):
            with self.subTest(selected=selected):
                state = self.workspace.prepare(selected, "not-required", [])
                self.assertEqual(self.workspace.source_before.decode(), state["review"]["manuscript_after"])
                self.assertFalse(state["review"]["has_manuscript_candidate"])
                self.assertFalse(self.workspace.preview_result()["result"]["has_manuscript_candidate"])
        connected = self.workspace.prepare(["claim-status"], "not-required", [])
        self.assertTrue(connected["review"]["has_manuscript_candidate"])
        self.assertIn(self.workspace.text, connected["review"]["manuscript_after"])

    def test_errors_and_repeated_preview_do_not_exhaust_human_edit_history(self):
        self.write()
        for _ in range(12):
            self.workspace.prepare(["claim-status"], "not-required", [])
        self.assertEqual(1, len(self.workspace.state()["review"]["contributions"]))
        with self.assertRaises(ContractError):
            self.workspace.prepare(["unknown"], "not-required", [])
        self.assertEqual("Sensitivity alone is insufficient.", self.workspace.state()["draft"]["text"])

    def test_marked_preview_preserves_surrounding_bytes_and_rejects_ambiguous_source(self):
        source = b"untouched prefix\n% claimbranch:start id=anchor\nold\n% claimbranch:end id=anchor\nuntouched suffix\n"
        result = preview_marked_text(source, "anchor", "new & exact", hashlib.sha256(source).hexdigest())
        self.assertEqual(source.replace(b"old\n", b"new \\& exact\n"), result)
        for bad_source, expected in ((source, "a" * 64), (source + source, hashlib.sha256(source + source).hexdigest()),
                                     (b"no marker", hashlib.sha256(b"no marker").hexdigest())):
            with self.assertRaises(ContractError):
                preview_marked_text(bad_source, "anchor", "new", expected)

    def test_expired_proposal_and_removed_trace_payload_do_not_change_authority(self):
        state = self.workspace.preview_request()
        key = state["outbound"]["request_id"]
        self.workspace.request_proposal(key)
        trace = self.workspace.broker.sent[0]
        self.workspace.erase_trace(key)
        self.assertEqual(trace.digest, self.workspace.broker.sent[0].digest)
        self.assertEqual("erased", self.workspace.state()["traces"][0]["payload_availability"])
        self.now = 1120
        with self.assertRaises(ContractError):
            self.workspace.use_proposal()
        self.assertEqual("", self.workspace.state()["draft"]["text"])
        self.assertEqual(0, self.workspace.state()["accepted_writes"])


if __name__ == "__main__":
    unittest.main()
