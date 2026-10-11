import hashlib
import json
import unittest

from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError
from claimbranch.core.research_history import ResearchHistory
from claimbranch.fixtures import replay_example
from tests.contract.test_paper_episodes import command
from tests.contract.test_paper_history import experiment


SOURCE = ("% Cafe\u0301: preserve exact decomposed bytes\r\n\\section{Results}\n"
          "% claimbranch:start id=anchor\nPrevious bounded wording.\n"
          "% claimbranch:end id=anchor\n% untouched suffix\r\n").encode()


class PaperManuscriptTests(unittest.TestCase):
    def setUp(self):
        from claimbranch.application.paper_manuscript import PaperManuscriptSession
        self.factory = PaperManuscriptSession
        self.history = replay_example("manual", series=True)
        self.work = PaperService(self.history).pending_work()["items"][-1]
        self.now = 1000
        self.session = self.factory(self.history, work_id=self.work["id"], source=SOURCE, clock=lambda: self.now)

    def write(self, session=None):
        (session or self.session).draft.edit("Pruning loses 1.2 percentage points; quantization loses 0.7.",
            "The corrected measurement exceeds the one-point pruning budget, within the measured split only.")

    def test_blank_wording_requires_human_input_and_only_returns_exact_candidate_bytes(self):
        self.assertEqual("", self.session.draft.state()["draft"]["text"])
        with self.assertRaises(ContractError):
            self.session.prepare()
        self.write()
        before = self.history.manifest()
        prepared = self.session.prepare()
        self.assertEqual(SOURCE.decode(), prepared["source"]["before"])
        reviewed = self.session.finish(prepared["digest"], disposition="not-required", answers=[])
        candidate = self.session.postimage(reviewed["digest"])
        expected = SOURCE.replace(b"Previous bounded wording.\n", (self.session.draft.state()["draft"]["text"] + "\n").encode())
        self.assertEqual(expected, candidate)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), prepared["postimage_digest"])
        self.assertIn("-Previous bounded wording.", prepared["source"]["diff"])
        self.assertFalse(prepared["source_verified"])
        self.assertFalse(reviewed["write_available"])
        self.assertFalse(reviewed["authorization_verified"])
        self.assertEqual(before, self.history.manifest())
        self.assertEqual(2, len(PaperService(self.history).pending_work()["items"]))

    def test_source_ai_survives_manual_wording_and_needs_explanation(self):
        history = replay_example("recorded", series=True)
        work = next(item for item in PaperService(history).pending_work()["items"] if item["kind"] == "manuscript")
        session = self.factory(history, work_id=work["id"], source=SOURCE, clock=lambda: self.now)
        self.write(session)
        preview = session.prepare()
        self.assertFalse(session.draft.state()["draft"]["ai_influenced"])
        self.assertTrue(preview["ai_influenced"])
        self.assertEqual(2, len(preview["source_judgments"]))
        with self.assertRaises(ContractError):
            session.finish(preview["digest"], disposition="not-required", answers=[])
        review = session.finish(preview["digest"], disposition="deferred", answers=[])
        self.assertTrue(review["consequences_if_accepted"]["understanding_review_required"])
        self.assertEqual(4, len(PaperService(history).pending_work()["items"]))
        self.assertTrue(session.postimage(review["digest"]))
        session.not_now()
        self.assertIsNone(session.get_review())
        self.assertTrue(session.draft.state()["draft"]["text"])

    def test_missing_invalid_or_ambiguous_source_never_produces_a_diff(self):
        for source in (None, b"no markers", SOURCE + SOURCE, SOURCE.replace(b"id=anchor", b"id=other"),
                       SOURCE.replace(b"% claimbranch:end", b"% claimbranch:start"), b"\xff" + SOURCE, b"x" * 65537):
            with self.subTest(source=source[:20] if source else None):
                try:
                    session = self.factory(self.history, work_id=self.work["id"], source=source, clock=lambda: self.now)
                except ContractError:
                    continue
                self.write(session)
                with self.assertRaises(ContractError):
                    session.prepare()
                self.assertIsNone(session.get_preview())
                self.assertTrue(session.draft.state()["draft"]["text"])

    def test_source_head_evidence_draft_and_time_changes_revoke_completed_review(self):
        for event in ("source", "source-unavailable", "evidence", "run", "draft", "expiry", "clock-reversal", "not-now", "reprepare"):
            with self.subTest(event=event):
                self.setUp()
                self.write()
                prepared = self.session.prepare()
                reviewed = self.session.finish(prepared["digest"], disposition="not-required", answers=[])
                if event in ("source", "source-unavailable"):
                    self.session.update_source(self.history, source=None if event == "source-unavailable" else SOURCE + b"external edit\n")
                elif event in ("evidence", "run"):
                    # Reopen a new episode only for supplied domain events, retaining
                    # all earlier conditional work and the existing wording buffer.
                    history = self.history.append(command(self.history, "open-episode", {"title": "Next check", "question": "What changed?"}, "next"))
                    if event == "run":
                        history = history.append(command(history, "record-experiment", dict(experiment(), id="new-run"), "next"))
                    else:
                        history = history.append(command(history, "record-evidence-event", {"event_id": "later-correction", "target_id": "obs-1",
                            "run_id": "run-accuracy", "action": "correct", "statement": "Another synthetic correction.", "value": "1.3",
                            "rationale": "Corrected count.", "supersedes_id": "recount"}, "next"))
                    self.session.update_source(history, source=SOURCE)
                elif event == "draft":
                    self.session.draft.edit("Another proposed sentence.", "The scope changed.")
                elif event == "expiry":
                    self.now += 300
                elif event == "clock-reversal":
                    self.now -= 1
                elif event == "not-now":
                    self.session.not_now()
                else:
                    self.session.prepare()
                with self.assertRaises(ContractError):
                    self.session.postimage(reviewed["digest"])
                self.assertTrue(self.session.draft.state()["draft"]["text"])
                self.assertEqual(0, self.session.state()["accepted_writes"])

    def test_tex_is_escaped_and_returned_previews_cannot_replace_owned_content(self):
        self.session.draft.edit(r"Do not run \input{private.tex}; 50% & result.", "Literal prose from the researcher.")
        prepared = self.session.prepare()
        prepared["source"]["after"] = "Caller-injected text"
        prepared["source_judgments"].clear()
        reviewed = self.session.finish(prepared["digest"], disposition="not-required", answers=[])
        candidate = self.session.postimage(reviewed["digest"])
        self.assertNotIn(br"\input{", candidate)
        self.assertIn(br"50\% \&", candidate)
        self.assertNotIn(b"Caller-injected", candidate)
        from claimbranch.core.review import acceptance_candidate
        with self.assertRaises(ContractError):
            acceptance_candidate(reviewed, decision="accept")

    def test_work_identity_other_sessions_and_non_extending_sources_are_rejected(self):
        self.write()
        prepared = self.session.prepare()
        reviewed = self.session.finish(prepared["digest"], disposition="not-required", answers=[])
        other = self.factory(self.history, work_id=self.work["id"], source=SOURCE, clock=lambda: self.now)
        with self.assertRaises(ContractError):
            other.postimage(reviewed["digest"])
        with self.assertRaises(ContractError):
            self.factory(self.history, work_id="missing", source=SOURCE)
        recorded = replay_example("recorded", series=True)
        understanding = next(item for item in PaperService(recorded).pending_work()["items"] if item["kind"] == "understanding")
        with self.assertRaises(ContractError):
            self.factory(recorded, work_id=understanding["id"], source=SOURCE)
        with self.assertRaises(ContractError):
            self.session.update_source(ResearchHistory(self.history.seed, self.history.commands[:-1]), source=SOURCE)
        self.assertEqual(reviewed, self.session.get_review())

    def test_wording_context_cannot_be_refreshed_independently_to_another_history(self):
        self.write()
        earlier = ResearchHistory(self.history.seed, self.history.commands[:-2])
        self.session.draft.update_source(PaperService(earlier))
        with self.assertRaises(ContractError):
            self.session.prepare()
        self.assertTrue(self.session.draft.state()["draft"]["text"])

    def test_same_episode_new_run_invalidates_review_even_with_unchanged_head_and_watermark(self):
        active = ResearchHistory(self.history.seed, self.history.commands[:-1])
        session = self.factory(active, work_id=self.work["id"], source=SOURCE, clock=lambda: self.now)
        self.write(session)
        preview = session.prepare()
        review = session.finish(preview["digest"], disposition="not-required", answers=[])
        later = active.append(command(active, "record-experiment", dict(experiment(), id="new-run"), "episode-two"))
        self.assertEqual(active.heads, later.heads)
        self.assertEqual(active.watermark, later.watermark)
        session.update_source(later, source=SOURCE)
        self.assertIsNone(session.get_preview())
        with self.assertRaises(ContractError):
            session.postimage(review["digest"])
        self.assertTrue(session.state()["context_current"])
        fresh = session.prepare()
        self.assertNotEqual(preview["history_digest"], fresh["history_digest"])
        self.assertEqual(preview["draft"]["judgment"], fresh["draft"]["judgment"])

    def test_offline_wording_adoption_revokes_review_and_preserves_original_after_edit(self):
        from claimbranch.application.paper_example import context_request
        session = self.factory(self.history, work_id=self.work["id"], source=SOURCE,
            frozen_response="Synthetic proposed wording: qualify the pruning result.", clock=lambda: self.now)
        self.write(session)
        first = session.prepare()
        first_review = session.finish(first["digest"], disposition="not-required", answers=[])
        request = dict(context_request(PaperService(self.history)), purpose="draft-manuscript")
        outbound = session.draft.prepare_request(request, include_draft=True)["outbound"]
        self.assertNotIn("% claimbranch:start", json.dumps(outbound))
        self.assertNotIn("preserve exact decomposed bytes", json.dumps(outbound))
        proposal = session.draft.request_proposal(outbound["request"]["request_id"], outbound["digest"])["proposal"]
        session.draft.use_proposal(proposal["id"])
        self.assertIsNone(session.get_preview())
        with self.assertRaises(ContractError):
            session.postimage(first_review["digest"])
        self.write(session)
        prepared = session.prepare()
        chain = prepared["draft"]["judgment"]["history"]
        self.assertEqual(["human", "ai", "human"], [item["contributor"] for item in chain])
        self.assertEqual(proposal["text"], chain[1]["text"])
        self.assertEqual(proposal["trace_digest"], chain[1]["trace_digest"])
        with self.assertRaises(ContractError):
            session.finish(prepared["digest"], disposition="not-required", answers=[])
        reviewed = session.finish(prepared["digest"], disposition="answered", answers=[
            "The proposal only suggests wording; the corrected measurements remain the evidence."])
        self.assertFalse(reviewed["consequences_if_accepted"]["understanding_review_required"])
        self.assertTrue(session.postimage(reviewed["digest"]))


if __name__ == "__main__":
    unittest.main()
