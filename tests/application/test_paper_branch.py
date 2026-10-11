from copy import deepcopy
from datetime import datetime
import unittest

from claimbranch.application.paper_draft import PaperDraftSession
from claimbranch.application.paper_merge import PaperMergeSession
from claimbranch.application.paper_service import PaperService
from claimbranch.application.paper_workspace import PaperWorkspace
from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.research_history import ResearchHistory
from tests.contract.test_paper_episodes import command, first_episode, second_episode
from tests.contract.test_paper_history import experiment, paper


NOW = int(datetime.fromisoformat("2026-09-23T00:00:00+00:00").timestamp())


def request(session, changes, selected):
    state = session.state()
    return {"schema_version": 1, **state["paper"], "draft_id": state["draft_id"],
            "draft_revision": state["revision"], "amendments": deepcopy(changes), "selected_ids": selected}


def unrecorded_second(*, ai=False):
    recorded, judgment = second_episode(first_episode(ai=ai))
    changes = decode(recorded.commands[-1])["payload"]["changes"]
    return ResearchHistory(recorded.seed, recorded.commands[:-2]), judgment, changes


class PaperBranchTests(unittest.TestCase):
    def setUp(self):
        self.now = NOW
        self.history, self.judgment, self.changes = unrecorded_second()
        self.workspace = PaperWorkspace(self.history, clock=lambda: self.now)
        self.session = self.workspace.draft("episode-two", "main", "obs-1")
        self.session.edit(self.judgment.text, self.judgment.rationale)

    def test_draft_builds_selected_branch_then_exact_merge_without_mutating_owners(self):
        original = self.history.manifest()
        plan = deepcopy(next(item for item in self.history.view("main")["changes"] if item["id"] == "replication"))
        plan["body"]["objective"] = "An omitted proposal for a different follow-up."
        prepared = self.session.prepare_branch(request(self.session, [*self.changes, plan], ["status-pruning"]))
        self.assertEqual(["replication"], prepared["preview"]["selection"]["omitted"])
        candidate = self.session.branch_candidate(prepared["digest"])
        self.assertEqual(candidate, self.session.branch_candidate(prepared["digest"]))
        self.assertEqual(["create-reasoning-branch", "record-interpretation"],
                         [decode(raw)["operation_type"] for raw in candidate.commands[-2:]])
        recorded = decode(candidate.commands[-1])["payload"]["changes"]
        self.assertEqual({item["id"] for item in self.changes}, {item["id"] for item in recorded})
        self.assertEqual(self.history.view("main"), candidate.view("main"))
        self.assertEqual(self.history.view("main")["evidence"], candidate.view("alternative")["evidence"])
        graph = PaperService(candidate).query("alternative")
        for key in ("nodes", "relations"):
            self.assertEqual(prepared["preview"]["graphs"]["after"][key], graph[key])
        self.assertEqual(original, self.workspace.history.manifest())
        self.assertEqual(original, self.history.manifest())
        self.workspace.update_history(candidate)
        self.assertEqual(self.judgment.text, self.session.state()["draft"]["text"])
        self.assertIsNone(self.session.get_branch_preview())
        merge = PaperMergeSession(candidate, episode_id="episode-two", manuscript_digest="b" * 64, clock=lambda: self.now)
        preview = merge.prepare(["status-pruning"])
        reviewed = merge.finish(preview["digest"], disposition="not-required", answers=[])
        merged, obligations = merge.candidate(reviewed["digest"])
        self.assertEqual("contested", next(item for item in merged.view("main")["claims"] if item["id"] == "claim-pruning-detail")["status"])
        self.assertFalse(obligations.authorization_verified)
        self.assertEqual(0, self.session.state()["accepted_writes"])

    def test_existing_alternative_retains_ai_prefix_and_repeated_preparation_never_duplicates(self):
        history = first_episode(ai=True, merge=False, close=False)
        source = history.view("alternative")["judgment"]
        workspace = PaperWorkspace(history, clock=lambda: self.now)
        session = workspace.draft("episode", "alternative", "obs-1")
        session.edit("A refined reading of the same results.", "The observed settings still need replication.")
        interp = deepcopy(history.view("alternative")["interpretations"][0])
        interp["body"]["statement"] = session.state()["draft"]["text"]
        req = request(session, [interp], [interp["id"]])
        prepared = session.prepare_branch(req)
        again = session.prepare_branch(req)
        self.assertNotEqual(prepared["digest"], again["digest"])
        with self.assertRaises(ContractError):
            session.branch_candidate(prepared["digest"])
        candidate = session.branch_candidate(again["digest"])
        joined = candidate.view("alternative")["judgment"]
        self.assertEqual(source["history"], joined["history"][:len(source["history"])])
        self.assertEqual(len(source["history"]) + 1, len(joined["history"]))
        self.assertEqual(1, len(candidate.commands) - len(history.commands))
        workspace.update_history(candidate)
        session.edit("A further refinement.", "No new evidence was recorded.")
        interp["body"]["statement"] = session.state()["draft"]["text"]
        final = session.prepare_branch(request(session, [interp], [interp["id"]]))
        next_ = session.branch_candidate(final["digest"])
        self.assertEqual(len(joined["history"]) + 1, len(next_.view("alternative")["judgment"]["history"]))
        merge = PaperMergeSession(next_, episode_id="episode", manuscript_digest="b" * 64, clock=lambda: self.now)
        preview = merge.prepare(["interpretation"])
        with self.assertRaises(ContractError):
            merge.finish(preview["digest"], disposition="not-required", answers=[])
        merge.finish(preview["digest"], disposition="deferred", answers=[])

    def test_closed_merged_old_or_wrong_ref_cannot_stage_but_draft_survives(self):
        older, _ = paper()
        for history, episode, ref in ((first_episode(), "episode", "main"),
                (first_episode(close=False), "episode", "alternative"), (older, "episode", "alternative"),
                (first_episode(merge=False, close=False), "episode", "main"),
                (self.history, "episode", "main")):
            with self.subTest(episode=episode, ref=ref, version=history.schema_version):
                session = PaperDraftSession(PaperService(history), ref=ref, episode_id=episode, clock=lambda: self.now)
                session.edit("A hypothetical reading.", "Keep it for later.")
                interp = {"id": "reading", "kind": "interpretation", "body": {
                    "statement": session.state()["draft"]["text"], "observation_ids": ["obs-1"]}}
                with self.assertRaises(ContractError):
                    session.prepare_branch(request(session, [interp], ["reading"]))
                self.assertEqual("A hypothetical reading.", session.state()["draft"]["text"])
                self.assertIsNone(session.get_branch_preview())

    def test_edit_not_now_expiry_source_change_and_other_review_reject_old_candidate(self):
        for event in ("edit", "not-now", "expiry", "clock-reversal", "source", "other-review"):
            with self.subTest(event=event):
                self.setUp()
                req = request(self.session, self.changes, ["status-pruning"])
                prepared = self.session.prepare_branch(req)
                if event == "edit":
                    self.session.edit("Revised text.", "Revised reason.")
                elif event == "not-now":
                    self.session.not_now()
                elif event == "expiry":
                    self.now += 300
                elif event == "clock-reversal":
                    self.now -= 1
                elif event == "other-review":
                    self.session.prepare_changes(req)
                else:
                    changed = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="new-run"), "episode-two"))
                    self.assertEqual(self.history.heads, changed.heads)
                    self.assertEqual(self.history.watermark, changed.watermark)
                    self.workspace.update_history(changed)
                with self.assertRaises(ContractError):
                    self.session.branch_candidate(prepared["digest"])
                self.assertTrue(self.session.state()["draft"]["text"])
                self.assertEqual(0, self.session.state()["accepted_writes"])

    def test_review_binds_owned_draft_and_commands_and_returns_detached_data(self):
        req = request(self.session, self.changes, ["status-pruning"])
        prepared = self.session.prepare_branch(req)
        for extra in ({"draft_revision": 0}, {"draft_id": "wrong"}, {"authorized": True},
                      {"view_digest": "a" * 64}, {"episode_id": "episode"}):
            with self.subTest(extra=extra), self.assertRaises(ContractError):
                self.session.prepare_branch(dict(req, **extra))
        other = PaperDraftSession(self.workspace.service, episode_id="episode-two", clock=lambda: self.now)
        with self.assertRaises(ContractError):
            other.branch_candidate(prepared["digest"])
        prepared["commands"][-1]["payload"]["judgment"]["text"] = "Caller substitution"
        prepared["preview"]["graphs"]["after"]["nodes"].clear()
        candidate = self.session.branch_candidate(prepared["digest"])
        self.assertEqual(self.judgment.text, candidate.view("alternative")["judgment"]["text"])
        self.assertTrue(self.session.get_branch_preview()["preview"]["graphs"]["after"]["nodes"])

    def test_incomplete_or_unselected_interpretation_cannot_be_inferred(self):
        self.session.edit("Unfinished", "")
        with self.assertRaises(ContractError):
            self.session.prepare_branch(request(self.session, self.changes, ["status-pruning"]))
        self.session.edit(self.judgment.text, self.judgment.rationale)
        with self.assertRaises(ContractError):
            self.session.prepare_branch(request(self.session, self.changes, ["edge-pruning"]))
        self.assertEqual(self.history, self.workspace.history)

    def test_offline_adoption_retains_new_ai_original_and_old_episode_sources(self):
        from claimbranch.application.paper_example import context_request
        service = PaperService(self.history)
        session = PaperDraftSession(service, episode_id="episode-two", frozen_response="A synthetic proposed interpretation.", clock=lambda: self.now)
        session.edit("My unfinished reading", "")
        outbound = session.prepare_request(context_request(service), include_draft=True)["outbound"]
        proposal = session.request_proposal(outbound["request"]["request_id"], outbound["digest"])["proposal"]
        session.use_proposal(proposal["id"])
        session.edit(self.judgment.text, self.judgment.rationale)
        prepared = session.prepare_branch(request(session, self.changes, ["status-pruning"]))
        candidate = session.branch_candidate(prepared["digest"])
        chain = candidate.view("alternative")["judgment"]["history"]
        self.assertEqual(["ai", "human"], [item["contributor"] for item in chain])
        self.assertEqual(proposal["text"], chain[0]["text"])
        self.assertEqual(proposal["trace_digest"], chain[0]["trace_digest"])
        self.assertEqual(proposal["id"], chain[0]["proposal_id"])
        self.assertEqual("My unfinished reading", session.state()["before_proposal"]["text"])
        self.assertEqual(self.history.view("main")["judgments"][0], candidate.view("alternative")["judgments"][0])
        merge = PaperMergeSession(candidate, episode_id="episode-two", manuscript_digest="b" * 64, clock=lambda: self.now)
        preview = merge.prepare(["status-pruning"])
        with self.assertRaises(ContractError):
            merge.finish(preview["digest"], disposition="not-required", answers=[])

    def test_history_overflow_does_not_truncate_authors_or_mutate_draft(self):
        from dataclasses import asdict
        history = first_episode(merge=False, close=False)
        from claimbranch.application.paper_branch import judgment_value
        judgment = judgment_value(history.view("alternative")["judgment"])
        for index in range(7):
            judgment = judgment.edit(f"Reading {index}", "The same bounded measurements.")
        interp = deepcopy(history.view("alternative")["interpretations"][0])
        interp["body"]["statement"] = judgment.text
        history = history.append(command(history, "record-interpretation", {"changes": [interp], "judgment": asdict(judgment)}))
        session = PaperDraftSession(PaperService(history), ref="alternative", clock=lambda: self.now)
        session.edit("One more complete reading.", "Needs all earlier authors retained.")
        interp["body"]["statement"] = session.state()["draft"]["text"]
        before = session.state()
        with self.assertRaises(ContractError):
            session.prepare_branch(request(session, [interp], [interp["id"]]))
        self.assertEqual(before, session.state())
        self.assertEqual(8, len(history.view("alternative")["judgment"]["history"]))

    def test_source_refresh_retains_both_independent_drafts_in_reviewed_chain(self):
        history = first_episode(merge=False, close=False)
        workspace = PaperWorkspace(history, clock=lambda: self.now)
        left = workspace.draft("episode", "alternative", "obs-1")
        right = workspace.draft("episode", "alternative", "obs-2")
        interp = deepcopy(history.view("alternative")["interpretations"][0])
        left.edit("Left reading", "Left reason")
        right.edit("Right reading", "Right reason")
        interp["body"]["statement"] = "Left reading"
        first = left.prepare_branch(request(left, [interp], [interp["id"]]))
        interp["body"]["statement"] = "Right reading"
        right.prepare_branch(request(right, [interp], [interp["id"]]))
        workspace.update_history(left.branch_candidate(first["digest"]))
        self.assertIsNone(right.get_branch_preview())
        prepared = right.prepare_branch(request(right, [interp], [interp["id"]]))
        candidate = right.branch_candidate(prepared["digest"])
        chain = candidate.view("alternative")["judgment"]["history"]
        self.assertEqual(["Left reading", "Right reading"], [item["text"] for item in chain[-2:]])
        self.assertEqual("Right reason", candidate.view("alternative")["judgment"]["rationale"])

    def test_joining_an_independent_ai_draft_reparents_without_losing_its_identity(self):
        history = first_episode(ai=True, merge=False, close=False)
        service = PaperService(history)
        original = history.view("alternative")["judgment"]["history"]
        session = PaperDraftSession(service, ref="alternative", frozen_response="An independent AI reading.", clock=lambda: self.now)
        view = service.query("alternative")
        outbound = session.prepare_request({"schema_version": 1, "project_id": "project", "episode_id": "episode",
            "ref": "alternative", "view_digest": view["digest"], "purpose": "critique-interpretation",
            "selections": [{"record_id": "obs-1", "fields": ["statement", "status"]}], "scientific_edge_ids": []})["outbound"]
        proposal = session.request_proposal(outbound["request"]["request_id"], outbound["digest"])["proposal"]
        session.use_proposal(proposal["id"])
        session.edit("My edited reading.", "My explanation of the selected evidence.")
        standalone = session.review_draft()["judgment"]["history"]
        interp = deepcopy(history.view("alternative")["interpretations"][0])
        interp["body"]["statement"] = session.state()["draft"]["text"]
        prepared = session.prepare_branch(request(session, [interp], [interp["id"]]))
        candidate = session.branch_candidate(prepared["digest"])
        chain = candidate.view("alternative")["judgment"]["history"]
        self.assertEqual(original, chain[:len(original)])
        self.assertEqual(len(original) + 2, len(chain))
        for before, after in zip(standalone, chain[len(original):]):
            self.assertEqual({key: val for key, val in before.items() if key != "parent_digest"},
                             {key: val for key, val in after.items() if key != "parent_digest"})
        self.assertIsNone(standalone[0]["parent_digest"])
        self.assertIsNotNone(chain[len(original)]["parent_digest"])


if __name__ == "__main__":
    unittest.main()
