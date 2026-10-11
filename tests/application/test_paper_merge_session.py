import unittest

from claimbranch.application.paper_merge import PaperMergeSession
from claimbranch.core.canonical import ContractError
from claimbranch.core.review import acceptance_candidate
from tests.contract.test_paper_episodes import command, first_episode, second_episode
from tests.contract.test_paper_history import experiment, paper


class PaperMergeSessionTests(unittest.TestCase):
    def setUp(self):
        self.history, self.judgment = second_episode(first_episode(ai=True))
        self.now = 1790121600  # 2026-09-23T00:00:00Z; no implicit wall clock.
        self.session = self.make_session()

    def make_session(self, history=None, episode_id="episode-two"):
        return PaperMergeSession(history or self.history, episode_id=episode_id,
            manuscript_digest="b" * 64, clock=lambda: self.now)

    def finish(self, prepared=None):
        prepared = prepared or self.session.prepare(["status-pruning"])
        return self.session.finish(prepared["digest"], disposition="deferred", answers=[])

    def test_before_after_graphs_show_actual_changes_and_full_scientific_reach(self):
        original = self.history.manifest()
        prepared = self.session.prepare(["status-pruning"])
        preview = prepared["preview"]
        self.assertEqual(["status-pruning"], preview["selection"]["selected"])
        self.assertEqual(["edge-pruning", "interpretation-two"], preview["selection"]["required"])
        self.assertIn("claim-pruning-detail", preview["selection"]["existing_references"])
        self.assertEqual(["claim-pruning", "claim-pruning-detail", "thesis"], preview["impact"]["potentially_affected_claim_ids"])
        self.assertEqual(["anchor"], preview["impact"]["potentially_affected_anchor_ids"])
        self.assertEqual(["obs-1", "obs-2"], preview["impact"]["unchanged_evidence_ids"])
        self.assertFalse(prepared["manuscript"]["source_verified"])
        self.assertTrue(preview["provenance"]["ai_influenced"])
        self.assertEqual(["episode", "episode-two"], [item["episode_id"] for item in preview["provenance"]["source_judgments"]])
        before = {node["id"]: node for node in preview["graphs"]["before"]["nodes"]}
        after = {node["id"]: node for node in preview["graphs"]["after"]["nodes"]}
        self.assertEqual("proposed", before["claim-pruning-detail"]["content"]["status"])
        self.assertEqual("contested", after["claim-pruning-detail"]["content"]["status"])
        self.assertEqual(before["obs-1"], after["obs-1"])
        self.assertEqual(original, self.history.manifest())

    def test_review_finishes_only_the_owned_command_and_returns_unverified_candidate(self):
        original = self.history.manifest()
        prepared = self.session.prepare(["status-pruning"])
        with self.assertRaises(ContractError):
            self.session.finish(prepared["digest"], disposition="not-required", answers=[])
        reviewed = self.finish(prepared)
        self.assertEqual(reviewed, self.finish(prepared))
        self.assertEqual(prepared["digest"], reviewed["preview_digest"])
        self.assertEqual("deferred", reviewed["sealed_review"]["disposition"])
        self.assertEqual(["status-pruning"], reviewed["command"]["payload"]["selected_ids"])
        self.assertEqual(["manuscript", "understanding"], [item["kind"] for item in reviewed["consequences_if_accepted"]["debts"]])
        self.assertFalse(reviewed["acceptance_available"])
        self.assertFalse(reviewed["authorization_verified"])
        candidate_history, candidate = self.session.candidate(reviewed["digest"])
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)
        self.assertEqual(2, len(candidate.source_judgments))
        self.assertEqual(len(self.history.commands) + 1, len(candidate_history.commands))
        self.assertEqual(original, self.history.manifest())
        with self.assertRaises(ContractError):
            acceptance_candidate(reviewed, decision="accept")

    def test_each_stale_event_rejects_candidate_without_appending_anything(self):
        for event in ("reselection", "not-now", "expiry", "clock-reversal", "source", "manuscript"):
            with self.subTest(event=event):
                self.setUp()
                reviewed = self.finish()
                if event == "reselection":
                    self.session.prepare(["edge-pruning"])
                elif event == "not-now":
                    self.session.not_now()
                elif event == "expiry":
                    self.now += 300
                elif event == "clock-reversal":
                    self.now -= 1
                elif event == "source":
                    changed = self.history.append(command(self.history, "record-experiment",
                        dict(experiment(), id="another-run"), "episode-two"))
                    self.assertEqual(self.history.heads, changed.heads)
                    self.session.update_source(changed, manuscript_digest="b" * 64)
                else:
                    self.session.update_source(self.history, manuscript_digest="c" * 64)
                with self.assertRaises(ContractError):
                    self.session.candidate(reviewed["digest"])
                self.assertIsNone(self.session.get_review())

    def test_reprepare_and_changed_explanation_never_reuse_previous_review(self):
        prepared = self.session.prepare(["status-pruning"])
        first = self.finish(prepared)
        second = self.session.finish(prepared["digest"], disposition="answered", answers=["Recount changes pruning only."])
        self.assertNotEqual(first["digest"], second["digest"])
        with self.assertRaises(ContractError):
            self.session.candidate(first["digest"])
        _, candidate = self.session.candidate(second["digest"])
        self.assertEqual(["manuscript"], [item.kind for item in candidate.debts])
        newer = self.session.prepare(["status-pruning"])
        self.assertNotEqual(prepared["digest"], newer["digest"])
        with self.assertRaises(ContractError):
            self.finish(prepared)

    def test_detached_outputs_and_cross_session_review_cannot_supply_authority(self):
        prepared = self.session.prepare(["status-pruning"])
        original = self.session.get_preview()
        prepared["preview"]["graphs"]["after"]["nodes"].clear()
        self.assertEqual(original, self.session.get_preview())
        reviewed = self.finish(original)
        reviewed["command"]["payload"]["selected_ids"] = ["edge-pruning"]
        reviewed["authorization_verified"] = True
        actual = self.session.get_review()
        self.assertFalse(actual["authorization_verified"])
        self.assertEqual(["status-pruning"], actual["command"]["payload"]["selected_ids"])
        other = self.make_session()
        other.prepare(["status-pruning"])
        with self.assertRaises(ContractError):
            other.candidate(actual["digest"])
        with self.assertRaises(ContractError):
            other.finish(original["digest"], disposition="deferred", answers=[])

    def test_invalid_selection_or_source_preserves_previous_review(self):
        reviewed = self.finish()
        for selected in ([], ["status-pruning"] * 2, ["obs-1"], ["claim-pruning-detail"], [True], [{}], "status-pruning"):
            with self.subTest(selected=selected), self.assertRaises(ContractError):
                self.session.prepare(selected)
        for history in (first_episode(), paper()[0], "history"):
            with self.subTest(history=type(history).__name__), self.assertRaises(ContractError):
                self.session.update_source(history, manuscript_digest="b" * 64)
        self.assertEqual(reviewed, self.session.get_review())

    def test_old_or_closed_episode_cannot_become_current_by_refresh(self):
        with self.assertRaises(ContractError):
            self.make_session(episode_id="episode")
        reviewed = self.finish()
        candidate, _ = self.session.candidate(reviewed["digest"])
        closed = candidate.append(command(candidate, "close-episode", {}, "episode-two"))
        self.session.update_source(closed, manuscript_digest="b" * 64)
        with self.assertRaises(ContractError):
            self.session.prepare(["status-pruning"])
        self.assertIsNone(self.session.get_review())
        with self.assertRaises(ContractError):
            self.make_session(closed)

    def test_not_now_leaves_source_and_draft_cache_intact(self):
        from claimbranch.application.paper_workspace import PaperWorkspace
        workspace = PaperWorkspace(self.history)
        draft = workspace.draft("episode-two", "main", "obs-1")
        draft.edit("Still considering the result.", "Check the experimental conditions.")
        before = draft.state()
        self.finish()
        self.session.not_now()
        self.assertIsNone(self.session.get_preview())
        self.assertIsNone(self.session.get_review())
        self.assertEqual(before, draft.state())
        self.assertEqual(self.history, workspace.history)

    def test_invalid_explanation_keeps_last_review_and_has_no_candidate_effect(self):
        prepared = self.session.prepare(["status-pruning"])
        reviewed = self.finish(prepared)
        for disposition, answers in (("not-required", []), ("deferred", ["answer"]),
                                     ("answered", []), ("answered", ["a"] * 4), ("answered", "a")):
            with self.subTest(disposition=disposition, answers=answers), self.assertRaises(ContractError):
                self.session.finish(prepared["digest"], disposition=disposition, answers=answers)
        self.session.update_source(self.history, manuscript_digest="b" * 64)
        self.assertEqual(reviewed, self.session.get_review())
        self.session.candidate(reviewed["digest"])


if __name__ == "__main__":
    unittest.main()
