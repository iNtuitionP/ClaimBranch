"""R1 storyboard checks establish inspectable design, never human approval."""

from copy import deepcopy
from html.parser import HTMLParser
import unittest

from scripts.render_episode_review import ARTIFACT, load_inputs, render, validate


class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.product_buttons = []
        self.external_resources = []
        self.ids = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "button" and attrs.get("class") == "product-action":
            self.product_buttons.append(attrs)
        if tag == "script":
            self.scripts += 1
        if "src" in attrs or (tag == "link" and "href" in attrs):
            self.external_resources.append(attrs)


class EpisodeReviewDesignTests(unittest.TestCase):
    def setUp(self):
        self.examples, self.source = load_inputs()

    def scene(self, name):
        return next(item for item in self.examples["scenes"] if item["id"] == name)

    def test_undecided_entry_requires_no_completed_judgment_or_proposal(self):
        scene = self.scene("undecided")
        draft = self.examples["drafts"][scene["draft"]]
        self.assertIsNone(draft["interpretation"])
        self.assertIsNone(draft["rationale"])
        self.assertEqual("off", scene["provider"])
        self.assertEqual([], scene["selected"])
        self.assertNotIn("authorize", scene["actions"])

    def test_deferral_and_resume_reuse_reason_but_differ_from_not_now(self):
        pending, deferred, resume = (self.scene(name) for name in ("not_now", "deferred", "resume"))
        self.assertEqual("pending", pending["review"])
        self.assertFalse(pending["understanding_open"])
        self.assertEqual("accepted", deferred["review"])
        self.assertTrue(deferred["understanding_open"])
        self.assertEqual(deferred["draft"], resume["draft"])
        self.assertTrue(resume["understanding_open"])
        self.assertEqual("debt_open", resume["manuscript"])

    def test_stale_recovery_and_unverified_states_cannot_offer_wrong_action(self):
        for name in ("stale_review", "provider_stale", "source_unavailable"):
            self.assertNotIn("authorize", self.scene(name)["actions"])
        self.assertEqual({"inspect", "export", "restore"}, set(self.scene("recovery")["actions"]))
        self.assertNotIn("close_manuscript", self.scene("applied_unverified")["actions"])
        mutated = deepcopy(self.examples)
        next(s for s in mutated["scenes"] if s["id"] == "recovery")["actions"].append("authorize")
        with self.assertRaises(ValueError):
            validate(mutated)

    def test_edited_proposal_retains_ai_origin_and_human_judgment(self):
        scene = self.scene("edited_proposal")
        self.assertEqual("edited", scene["proposal"])
        self.assertEqual("reviewable", scene["review"])
        page = render(self.examples, self.source)
        self.assertIn(self.source["proposal"]["normalized_text"], page)
        self.assertIn(self.examples["drafts"][scene["draft"]]["interpretation"], page)

    def test_output_is_offline_with_inert_product_actions_and_escaped_content(self):
        examples = deepcopy(self.examples)
        examples["drafts"]["edited"]["rationale"] = '<script>alert("unsafe")</script>'
        page = render(examples, self.source)
        audit = PageAudit()
        audit.feed(page)
        self.assertGreater(len(audit.product_buttons), 10)
        self.assertTrue(all("disabled" in button for button in audit.product_buttons))
        self.assertEqual([], audit.external_resources)
        self.assertEqual(len(audit.ids), len(set(audit.ids)))
        self.assertEqual(1, audit.scripts)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn('<script>alert("unsafe")</script>', page)

    def test_saved_storyboard_matches_its_sources(self):
        self.assertEqual(render(self.examples, self.source), ARTIFACT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
