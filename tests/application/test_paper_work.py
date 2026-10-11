from dataclasses import asdict
import unittest

from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError, MAX_BYTES, canonical_bytes, decode, digest
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_episodes import command, first_episode, second_episode
from tests.contract.test_paper_history import experiment


class PaperWorkTests(unittest.TestCase):
    def test_replay_preserves_each_episodes_conditional_work_and_ai_origin(self):
        for variant in ("manual", "recorded"):
            with self.subTest(variant=variant):
                history = replay_example(variant, series=True)
                before = history.manifest()
                work = PaperService(history).pending_work()
                self.assertEqual(2 if variant == "manual" else 4, len(work["items"]))
                self.assertEqual({"episode", "episode-two"}, {item["episode_id"] for item in work["items"]})
                self.assertTrue(all(item["status"] == "pending-if-accepted" for item in work["items"]))
                self.assertTrue(all(item["authorization_verified"] is False and item["closure_available"] is False for item in work["items"]))
                self.assertEqual(before, history.manifest())
                replayed = ResearchHistory.replay(history.seed, history.commands)
                self.assertEqual(work, PaperService(replayed).pending_work())
                latest = next(item for item in work["items"] if item["episode_id"] == "episode-two" and item["kind"] == "manuscript")
                self.assertEqual(variant == "recorded", latest["ai_influenced"])
                self.assertEqual(["human"], [c["contributor"] for c in latest["judgment"]["history"]])
                self.assertEqual(["anchor"], latest["potentially_affected_anchor_ids"])

    def test_unmerged_drafts_open_no_work_and_close_does_not_resolve_recorded_work(self):
        draft = first_episode(merge=False, close=False)
        self.assertEqual([], PaperService(draft).pending_work()["items"])
        merged = first_episode(ai=True, close=False)
        before = PaperService(merged).pending_work()["items"]
        closed = merged.append(command(merged, "close-episode", {}))
        self.assertEqual(before, PaperService(closed).pending_work()["items"])
        self.assertEqual(["manuscript", "understanding"], [item["kind"] for item in before])

    def test_later_episode_keeps_causal_ids_and_flags_changed_head_and_evidence(self):
        first = first_episode(ai=True)
        before = PaperService(first).pending_work()["items"]
        next_, judgment = second_episode(first)
        after = PaperService(next_).pending_work(episode_id="episode")["items"]
        self.assertEqual([item["id"] for item in before], [item["id"] for item in after])
        self.assertTrue(all(item["evidence_changed_since_merge"] for item in after))
        self.assertFalse(any(item["main_changed_since_merge"] for item in after))
        merged = next_.append(command(next_, "apply-selected-merge", {
            "selected_ids": ["status-pruning"], "judgment": asdict(judgment), "disposition": "deferred", "answers": []}, "episode-two"))
        items = PaperService(merged).pending_work(episode_id="episode")["items"]
        self.assertTrue(all(item["main_changed_since_merge"] for item in items))
        self.assertEqual([item["id"] for item in before], [item["id"] for item in items])
        self.assertEqual(before[0]["judgment"], items[0]["judgment"])

    def test_read_projection_is_detached_and_rejects_unknown_or_legacy_context(self):
        history = first_episode()
        service = PaperService(history)
        work = service.pending_work()
        work["items"][0]["judgment"]["history"].clear()
        self.assertTrue(service.pending_work()["items"][0]["judgment"]["history"])
        for episode in ("unknown", True):
            with self.subTest(episode=episode), self.assertRaises(ContractError):
                service.pending_work(episode_id=episode)
        with self.assertRaises(ContractError):
            PaperService(replay_example("manual", paper=True)).pending_work()

    def test_plan_only_merge_retains_impact_review_without_inventing_wording_or_unanswered_debt(self):
        history = first_episode(ai=True, merge=False, close=False)
        history = history.append(command(history, "apply-selected-merge", {
            "selected_ids": ["replication"], "judgment": history.view("alternative")["judgment"],
            "disposition": "answered", "answers": ["The plan has not run; it supplies no new evidence."]}))
        work = PaperService(history).pending_work()["items"]
        self.assertEqual(["manuscript"], [item["kind"] for item in work])
        self.assertEqual([], work[0]["potentially_affected_anchor_ids"])
        self.assertEqual([], history.view("main")["interpretations"])
        self.assertEqual(["replication"], work[0]["selection"]["selected"])
        self.assertTrue(work[0]["ai_influenced"])


class UnderstandingReturnTests(unittest.TestCase):
    def setUp(self):
        self.history = first_episode(ai=True)
        self.service = PaperService(self.history)
        self.work = next(item for item in self.service.pending_work()["items"]
                         if item["kind"] == "understanding")

    def returned(self, history=None):
        service = PaperService(history) if history is not None else self.service
        return service.understanding_return(self.work["id"], project_id="project")

    def test_return_restores_causal_argument_and_contributions_without_authority(self):
        manifest = self.history.manifest()
        value = self.returned()
        self.assertEqual("claimbranch.paper-understanding-return/v1", value["schema"])
        self.assertEqual("project", value["project_id"])
        self.assertEqual(self.work, value["work"])
        self.assertEqual("pending-if-accepted", value["work"]["status"])
        self.assertEqual("deferred", value["work"]["explanation_disposition"])
        self.assertEqual(["human", "ai", "human"],
                         [c["contributor"] for c in value["work"]["judgment"]["history"]])
        self.assertEqual(self.work["source_judgments"], value["work"]["source_judgments"])
        self.assertEqual(self.work["cause_operation_id"], value["original"]["at_operation"])
        self.assertEqual(self.work["cause_operation_id"], value["original"]["head"])
        self.assertEqual("active", value["original"]["episode"]["status"])
        self.assertEqual("closed", value["current"]["episode"]["status"])
        self.assertIn("obs-1", value["work"]["selection"]["evidence_references"])
        self.assertTrue(any(r["record_id"] == "edge-pruning" for r in value["original"]["relations"]))
        self.assertEqual("conditional-on-acceptance", value["authority"])
        for field in ("acceptance_available", "authorization_verified", "closure_available", "cause_review_available"):
            self.assertIs(value[field], False)
        self.assertEqual("accepted-cause-review-unavailable", value["closure_unavailable_reason"])
        self.assertEqual(0, value["accepted_debts_created"])
        self.assertEqual(0, value["accepted_writes"])
        self.assertNotIn("debt_id", value)
        self.assertNotIn("review_digest", value)
        self.assertEqual(manifest, self.history.manifest())

    def test_evidence_only_change_keeps_the_original_context_and_changes_the_return_digest(self):
        active = first_episode(ai=True, close=False)
        original = self.returned(active)
        later = active.append(command(active, "record-evidence-event", {
            "event_id": "return-correction", "target_id": "obs-1", "run_id": "run-accuracy",
            "action": "correct", "statement": "Synthetic recount: pruning loses 1.2 percentage points.",
            "value": "1.2", "rationale": "Correct this measurement without changing reasoning.",
            "supersedes_id": "event-1"}))
        value = self.returned(later)
        self.assertEqual(active.heads, later.heads)
        self.assertEqual(original["current"]["episode"], value["current"]["episode"])
        self.assertEqual(original["original"], value["original"])
        self.assertFalse(value["work"]["main_changed_since_merge"])
        self.assertTrue(value["work"]["evidence_changed_since_merge"])
        self.assertEqual(original["current"]["head"], value["current"]["head"])
        self.assertNotEqual(original["current"]["evidence_watermark"], value["current"]["evidence_watermark"])
        self.assertNotEqual(original["digest"], value["digest"])
        old = next(n for n in value["original"]["nodes"] if n["id"] == "obs-1")
        current = next(n for n in value["current"]["nodes"] if n["id"] == "obs-1")
        self.assertEqual("0.4", old["content"]["value"])
        self.assertEqual("1.2", current["content"]["value"])
        self.assertEqual("0.4", current["content"]["history"][0]["value"])
        self.assertEqual("episode", value["work"]["episode_id"])
        self.assertEqual("episode", value["current"]["episode_id"])

    def test_current_argument_follows_later_merge_without_replacing_the_cause(self):
        original = self.returned()
        later, judgment = second_episode(self.history)
        later = later.append(command(later, "apply-selected-merge", {
            "selected_ids": ["status-pruning"], "judgment": asdict(judgment),
            "disposition": "deferred", "answers": []}, "episode-two"))
        value = self.returned(later)
        self.assertEqual(original["original"], value["original"])
        self.assertEqual(original["work"]["judgment"], value["work"]["judgment"])
        self.assertEqual(original["work"]["id"], value["work"]["id"])
        self.assertTrue(value["work"]["main_changed_since_merge"])
        self.assertEqual("episode-two", value["current"]["episode_id"])
        self.assertEqual(dict(later.heads)["main"], value["current"]["head"])
        claim = next(n for n in value["current"]["nodes"] if n["id"] == "claim-pruning-detail")
        self.assertEqual("contested", claim["content"]["status"])
        self.assertFalse(value["closure_available"])
        service = PaperService(later)
        second = next(item for item in service.pending_work()["items"]
                      if item["kind"] == "understanding" and item["episode_id"] == "episode-two")
        returned = service.understanding_return(second["id"], project_id="project")
        self.assertNotEqual(value["work"]["id"], returned["work"]["id"])
        self.assertNotEqual(value["digest"], returned["digest"])
        self.assertEqual("episode-two", returned["original"]["episode_id"])
        self.assertEqual(second["cause_operation_id"], returned["original"]["head"])
        self.assertEqual(decode(canonical_bytes(asdict(judgment))), returned["work"]["judgment"])
        self.assertEqual(["episode", "episode-two"],
                         [item["episode_id"] for item in returned["original"]["judgments"]])
        claim = next(n for n in returned["original"]["nodes"] if n["id"] == "claim-pruning-detail")
        self.assertEqual("contested", claim["content"]["status"])

    def test_episode_close_changes_history_binding_without_closing_or_rewriting_work(self):
        active = first_episode(ai=True, close=False)
        before = self.returned(active)
        after = self.returned()
        self.assertFalse(before["history_changed_since_merge"])
        self.assertTrue(after["history_changed_since_merge"])
        self.assertEqual(before["original"], after["original"])
        self.assertEqual(before["work"], after["work"])
        self.assertEqual(before["current"]["head"], after["current"]["head"])
        self.assertEqual(before["current"]["evidence_watermark"], after["current"]["evidence_watermark"])
        self.assertNotEqual(before["digest"], after["digest"])

    def test_return_is_detached_and_replay_stable(self):
        original = self.returned()
        value = self.returned()
        binding = {k: v for k, v in value.items() if k != "digest"}
        binding["work"] = digest(value["work"])
        for key in ("original", "current"):
            binding[key] = digest({k: v for k, v in value[key].items() if k != "digest"})
            self.assertEqual(value[key]["digest"], binding[key])
        self.assertEqual(value["digest"], digest(binding))
        value["work"]["judgment"]["history"].clear()
        value["original"]["nodes"].clear()
        value["current"]["nodes"][0]["content"].clear()
        for key in ("original", "current"):
            self.assertNotEqual(value[key]["digest"],
                                digest({k: v for k, v in value[key].items() if k != "digest"}))
        self.assertEqual(original, self.returned())
        replayed = ResearchHistory.replay(self.history.seed, self.history.commands)
        self.assertEqual(original, self.returned(replayed))

    def test_documented_series_example_returns_each_cause_after_replay(self):
        history = replay_example("recorded", series=True)
        manifest = history.manifest()
        service = PaperService(history)
        replayed = PaperService(ResearchHistory.replay(history.seed, history.commands))
        pending = service.pending_work()
        items = [item for item in pending["items"] if item["kind"] == "understanding"]
        self.assertEqual(2, len(items))
        for item in items:
            with self.subTest(episode=item["episode_id"]):
                value = service.understanding_return(item["id"], project_id=pending["project_id"])
                self.assertEqual(item, value["work"])
                self.assertEqual(item["cause_operation_id"], value["original"]["head"])
                self.assertEqual(item["episode_id"], value["original"]["episode_id"])
                self.assertEqual(value, replayed.understanding_return(item["id"], project_id=pending["project_id"]))
                self.assertFalse(value["authorization_verified"])
                self.assertFalse(value["closure_available"])
                self.assertEqual(0, value["accepted_writes"])
        self.assertEqual(manifest, history.manifest())

    def test_individually_bounded_views_can_return_together_without_truncation(self):
        history = first_episode(ai=True, close=False)
        run = experiment()
        run.update(id="large-context-run", conditions="Synthetic conditions. " + "x" * 7500)
        run["metric"]["definition"] = "Synthetic metric definition. " + "y" * 7500
        history = history.append(command(history, "record-experiment", run))
        for n in range(14):
            history = history.append(command(history, "record-evidence-event", {
                "event_id": f"additional-event-{n}", "target_id": f"additional-observation-{n}",
                "run_id": run["id"], "action": "confirm", "statement": "An additional synthetic observation.",
                "value": str(n), "rationale": "Synthetic size-boundary fixture.", "supersedes_id": None}))
        manifest = history.manifest()
        self.assertLess(len(manifest), MAX_BYTES)
        service = PaperService(history)
        current = service.query("main")
        self.assertLess(len(canonical_bytes(current)), MAX_BYTES)
        value = self.returned(history)
        self.assertEqual(current, value["current"])
        self.assertGreater(len(canonical_bytes(value["original"])) + len(canonical_bytes(current)), MAX_BYTES)
        observation = next(n for n in value["current"]["nodes"] if n["id"] == "additional-observation-13")
        self.assertEqual(run["conditions"], observation["content"]["conditions"])
        self.assertEqual(run["metric"], observation["content"]["metric"])
        self.assertEqual(manifest, history.manifest())
        self.assertEqual(value, self.returned(ResearchHistory.replay(history.seed, history.commands)))

    def test_unknown_cross_project_wrong_kind_and_legacy_inputs_fail_without_mutation(self):
        manifest = self.history.manifest()
        manuscript = next(item["id"] for item in self.service.pending_work()["items"]
                          if item["kind"] == "manuscript")
        for work_id, project_id in (("unknown", "project"), (manuscript, "project"),
                                    (self.work["id"], "another-project"), (True, "project"),
                                    ({"id": self.work["id"], "actor_class": "human"}, "project"),
                                    (self.work["id"], True)):
            with self.subTest(work_id=work_id, project_id=project_id), self.assertRaises(ContractError):
                self.service.understanding_return(work_id, project_id=project_id)
        foreign = ResearchHistory.start_paper_series("another-project", "Other synthetic paper", "thesis", "Claim", "anchor")
        with self.assertRaises(ContractError):
            PaperService(foreign).understanding_return(self.work["id"], project_id="another-project")
        for history in (first_episode(), first_episode(ai=True, merge=False, close=False),
                        replay_example("recorded", paper=True)):
            with self.subTest(history=decode(history.seed)["schema_version"]), self.assertRaises(ContractError):
                PaperService(history).understanding_return(self.work["id"], project_id=decode(history.seed)["project_id"])
        self.assertEqual(manifest, self.history.manifest())


if __name__ == "__main__":
    unittest.main()
