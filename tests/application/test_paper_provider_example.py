import hashlib
import unittest
from unittest.mock import patch

from claimbranch.fixtures import replay_example
from claimbranch.core.canonical import digest


class PaperProviderExampleTests(unittest.TestCase):
    def test_five_independent_runs_keep_science_and_show_manual_continuation(self):
        from claimbranch.application.paper_provider_example import workflow
        for variant in ("manual", "recorded"):
            with self.subTest(variant=variant), patch("socket.socket", side_effect=AssertionError("network used")), patch("subprocess.run", side_effect=AssertionError("worker started")):
                result = workflow(variant)
            self.assertEqual(hashlib.sha256(replay_example(variant, paper=True).manifest()).hexdigest(), result["history_digest"])
            self.assertEqual("synthetic-example", result["classification"])
            self.assertTrue(result["source_unchanged"])
            self.assertFalse(result["authorization_verified"])
            self.assertEqual(["adopted", "cancelled", "edited", "expired", "refused"], [case["name"] for case in result["cases"]])
            self.assertEqual(["proposed", "cancelled", "stale", "expired", "failed"], [case["arrival"]["attempt"]["state"] for case in result["cases"]])
            for case in result["cases"]:
                state = case["state"]
                self.assertTrue(case["manual_review_available"])
                self.assertTrue(case["trace_identity_retained"])
                self.assertEqual("erased", state["traces"][0]["payload_availability"])
                self.assertEqual(1, len(state["attempts"]))
                self.assertEqual(0, state["accepted_writes"])
                self.assertFalse(state["authorization_verified"])
                authors = [c["contributor"] for c in case["review"]["judgment"]["history"]]
                self.assertEqual(["ai", "human"] if case["name"] == "adopted" else ["human"], authors)
                self.assertEqual(case["name"] == "adopted", state["draft"]["ai_influenced"])
                if case["name"] != "adopted":
                    self.assertIsNone(case["arrival"]["proposal"])
                self.assertIn("seed 43", case["question"])
                records = {r["id"]: r for r in case["outbound"]["request"]["context"]["records"]}
                questions = [r["fields"] for r in records.values() if r["kind"] == "draft"]
                self.assertEqual(1, len(questions))
                self.assertEqual(case["question"], questions[0]["statement"])
                self.assertIsNone(questions[0]["rationale"])
                self.assertFalse(questions[0]["origin"]["ai_influenced"])
                self.assertIn("interpretation", records)
                self.assertEqual(digest(case["outbound"]["request"]), case["outbound"]["digest"])
                if case["name"] == "adopted":
                    self.assertEqual({"text": case["question"], "rationale": ""}, state["before_proposal"])
                self.assertEqual("0.4", records["obs-1"]["fields"]["value"])
                self.assertIn("replication", records)
                self.assertEqual("offline://frozen", case["outbound"]["request"]["destination"]["url"])
                self.assertEqual("refused" if case["name"] == "refused" else "proposed", state["traces"][0]["disposition"])


if __name__ == "__main__":
    unittest.main()
