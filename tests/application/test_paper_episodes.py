import unittest

from claimbranch.application.paper_draft import PaperDraftSession
from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError
from tests.contract.test_paper_episodes import command, first_episode, second_episode
from tests.contract.test_paper_changes import amendments


def change_request(session, history):
    state = session.state()
    return {"schema_version": 1, **state["paper"], "draft_id": state["draft_id"],
            "draft_revision": state["revision"], "amendments": [amendments(history)[2]],
            "selected_ids": ["replication"]}


class PaperEpisodeServiceTests(unittest.TestCase):
    def test_episode_query_exposes_tui_graph_contract_and_separate_provenance(self):
        first = first_episode(ai=True)
        history, _ = second_episode(first)
        service = PaperService(history)
        timeline = service.episodes()
        self.assertEqual("episode-two", timeline["active_episode_id"])
        self.assertEqual(["episode", "episode-two"], [row["id"] for row in timeline["episodes"]])
        current = service.query("alternative")
        previous = service.query("alternative", episode_id="episode")
        self.assertEqual("claimbranch.paper-view/v2", current["schema"])
        self.assertEqual("episode-two", current["episode_id"])
        self.assertEqual("closed", previous["episode"]["status"])
        self.assertEqual("1.2", next(node for node in previous["nodes"] if node["id"] == "obs-1")["content"]["value"])
        old_reading = next(node for node in current["nodes"] if node["id"] == "interpretation")
        self.assertEqual("episode", old_reading["content"]["episode_id"])
        self.assertEqual(2, len(current["judgments"]))
        timeline["episodes"].clear()
        self.assertEqual(2, len(service.episodes()["episodes"]))
        self.assertEqual(first.view("main")["judgment"], previous["judgment"])

    def test_draft_stays_in_its_episode_and_new_sources_invalidate_review(self):
        first = first_episode()
        first_service = PaperService(first)
        old = PaperDraftSession(first_service, episode_id="episode", clock=lambda: 100)
        old.edit("Keep considering the first result.", "Seed 43 remains unrun.")
        prepared = old.prepare_changes(change_request(old, first))
        later, _ = second_episode(first)
        service = PaperService(later)
        old.update_source(service)
        self.assertEqual("episode", old.state()["paper"]["episode_id"])
        self.assertEqual("Keep considering the first result.", old.state()["draft"]["text"])
        with self.assertRaises(ContractError):
            old.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        new = PaperDraftSession(service, episode_id="episode-two")
        self.assertEqual("", new.state()["draft"]["text"])
        with self.assertRaises(ContractError):
            new.prepare_changes(change_request(old, first))

    def test_current_manual_review_retains_all_prior_ai_and_sends_only_selected_context(self):
        history, judgment = second_episode(first_episode(ai=True))
        service = PaperService(history)
        session = PaperDraftSession(service, ref="alternative", episode_id="episode-two", clock=lambda: 100)
        session.edit(judgment.text, judgment.rationale)
        request = change_request(session, history)
        prepared = session.prepare_changes(request)
        self.assertFalse(session.state()["draft"]["ai_influenced"])
        self.assertTrue(prepared["preview"]["provenance"]["ai_influenced"])
        self.assertEqual(2, len(prepared["preview"]["provenance"]["source_judgments"]))
        with self.assertRaises(ContractError):
            session.finish_changes_review(prepared["digest"], disposition="not-required", answers=[])
        session.finish_changes_review(prepared["digest"], disposition="deferred", answers=[])
        view = service.query("main", episode_id="episode")
        context = service.compile_context({"schema_version": 1, "project_id": "project", "episode_id": "episode",
            "ref": "main", "view_digest": view["digest"], "purpose": "compare-evidence",
            "selections": [{"record_id": "obs-1", "fields": ["statement", "status", "value"]}], "scientific_edge_ids": []})
        self.assertNotIn(b"interpretation-two", context.payload)
        self.assertNotIn(b"source_judgments", context.payload)

    def test_workspace_keeps_episode_ref_and_node_drafts_separate_across_refresh(self):
        from claimbranch.application.paper_workspace import PaperWorkspace
        first = first_episode()
        workspace = PaperWorkspace(first)
        draft = workspace.draft("episode", "main", "obs-1")
        draft.edit("Earlier text.", "Earlier reason.")
        same = workspace.draft("episode", "main", "obs-1")
        self.assertIs(draft, same)
        self.assertEqual("", workspace.draft("episode", "main", "obs-2").state()["draft"]["text"])
        self.assertEqual("", workspace.draft("episode", "alternative", "obs-1").state()["draft"]["text"])
        later, _ = second_episode(first)
        workspace.update_history(later)
        self.assertEqual("Earlier text.", workspace.draft("episode", "main", "obs-1").state()["draft"]["text"])
        self.assertEqual("", workspace.draft("episode-two", "main", "obs-1").state()["draft"]["text"])
        self.assertEqual("episode-two", workspace.service.query()["episode_id"])
        with self.assertRaises(ContractError):
            workspace.update_history(first)
        with self.assertRaises(ContractError):
            workspace.draft("episode", "main", "unknown")
        self.assertEqual(later.manifest(), workspace.history.manifest())

    def test_same_paper_new_episode_changes_context_even_without_new_evidence_or_heads(self):
        first = first_episode()
        service = PaperService(first)
        view = service.query("main")
        next_ = first.append(command(first, "open-episode", {"title": "Another question", "question": "What next?"}, "episode-two"))
        new_service = PaperService(next_)
        new_view = new_service.query("main")
        self.assertEqual(view["head"], new_view["head"])
        self.assertEqual(view["evidence_watermark"], new_view["evidence_watermark"])
        self.assertNotEqual(view["digest"], new_view["digest"])
        request = {"schema_version": 1, "project_id": "project", "episode_id": "episode", "ref": "main",
            "view_digest": view["digest"], "purpose": "compare-evidence",
            "selections": [{"record_id": "obs-1", "fields": ["status"]}], "scientific_edge_ids": []}
        with self.assertRaises(ContractError):
            new_service.compile_context(request)

    def test_current_tui_can_read_series_graphs_without_owning_the_history(self):
        from claimbranch.application.tui import render_snapshot
        from claimbranch.application.tui_model import TerminalWorkspace
        history, _ = second_episode(first_episode())
        before = history.manifest()
        terminal = TerminalWorkspace(history)
        terminal.select("obs-1")
        self.assertEqual("episode-two", terminal.view["episode_id"])
        self.assertEqual({"claim-pruning-detail", "claim-comparison"},
                         {link.target_id for link in terminal.links() if link.scientific and link.outgoing})
        self.assertEqual("1.2", terminal.nodes["obs-1"]["content"]["value"])
        self.assertIn("ClaimBranch", render_snapshot(terminal, 132, 36))
        self.assertEqual(before, history.manifest())

    def test_ai_context_distinguishes_a_prior_interpretation_from_the_new_episode(self):
        from claimbranch.core.canonical import decode
        history, _ = second_episode(first_episode())
        service = PaperService(history)
        view = service.query("alternative")
        request = {"schema_version": 1, "project_id": "project", "episode_id": "episode-two",
            "ref": "alternative", "view_digest": view["digest"], "purpose": "critique-interpretation",
            "selections": [{"record_id": "interpretation", "fields": ["statement", "observation_ids"]}],
            "scientific_edge_ids": []}
        with self.assertRaises(ContractError):
            service.compile_context(request)
        request["selections"][0]["fields"].append("episode_id")
        value = decode(service.compile_context(request).payload)
        self.assertEqual("episode", value["records"][0]["fields"]["episode_id"])
        self.assertNotIn("judgments", value["records"][0]["fields"])

    def test_query_rejects_nonidentities_and_workspace_capacity_retains_existing_drafts(self):
        from claimbranch.application.paper_workspace import PaperWorkspace
        history = first_episode()
        service = PaperService(history)
        for episode in (False, 0, [], {}, "", "unknown"):
            with self.subTest(episode=episode), self.assertRaises(ContractError):
                service.query(episode_id=episode)
        workspace = PaperWorkspace(history)
        retained = workspace.draft("episode", "main", "obs-1")
        retained.edit("Keep this draft.", "Keep its reason.")
        keys = [(ref, node["id"]) for ref in ("main", "alternative") for node in service.query(ref)["nodes"]
                if (ref, node["id"]) != ("main", "obs-1")]
        for ref, node in keys[:15]:
            workspace.draft("episode", ref, node)
        with self.assertRaises(ContractError):
            workspace.draft("episode", *keys[15])
        self.assertIs(retained, workspace.draft("episode", "main", "obs-1"))
        self.assertEqual("Keep this draft.", retained.state()["draft"]["text"])


if __name__ == "__main__":
    unittest.main()
