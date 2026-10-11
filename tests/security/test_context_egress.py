from dataclasses import replace
import unittest

from claimbranch.core.canonical import ContractError
from claimbranch.core.context import (ContextRecord, ContextSelection, Destination,
    compile_context, review_outbound, OfflineBroker)


class ContextEgressTests(unittest.TestCase):
    def setUp(self):
        self.records = (ContextRecord.create("project", "obs", "observation", "redacted",
                        {"statement": "Mixed result", "status": "confirmed"}),)
        self.selection = ContextSelection("project", "episode", "compare-evidence", (("obs", ("statement", "status")),))
        self.context = compile_context(self.records, self.selection)
        self.destination = Destination("offline://frozen", "frozen-v1")

    def test_exact_fields_only_and_no_human_export_or_raw_artifact_capability(self):
        self.assertIn(b"Mixed result", self.context.payload)
        for fields in (("artifact_bytes",), ("statement", "absolute_path"), ("export",)):
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                compile_context(self.records, replace(self.selection, fields=(("obs", fields),)))

    def test_other_project_duplicate_or_unknown_records_are_rejected(self):
        for update in ({"project_id": "other"}, {"fields": (("unknown", ("statement",)),)},
                       {"fields": (("obs", ("statement",)), ("obs", ("status",)))}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                compile_context(self.records, replace(self.selection, **update))

    def test_secret_classification_and_sensitive_material_never_enter_context(self):
        for fields in ({"statement": "-----BEGIN PRIVATE KEY-----"},
                       {"statement": "Bearer abcdefghijklmnopqrstuvwxyz"},
                       {"statement": "/Users/person/private/data.csv"}):
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                record = ContextRecord.create("project", "obs", "observation", "redacted", fields)
                compile_context((record,), replace(self.selection, fields=(("obs", ("statement",)),)))
        with self.assertRaises(ContractError):
            compile_context((ContextRecord.create("project", "obs", "observation", "secret", {"statement": "hidden"}),),
                            replace(self.selection, fields=(("obs", ("statement",)),)))

    def test_context_revision_destination_and_expiry_invalidate_consent(self):
        broker = OfflineBroker()
        review = review_outbound(self.context, self.destination, request_id="request", nonce="nonce", now=100)
        for context, destination, now in (
                (replace(self.context, payload=b"changed"), self.destination, 101),
                (self.context, Destination("offline://frozen", "other-model"), 101),
                (self.context, self.destination, 400)):
            with self.subTest(now=now), self.assertRaises(ContractError):
                broker.dispatch(context, destination, review, now=now, response="frozen text")
        self.assertEqual((), broker.sent)

    def test_one_shot_consent_is_consumed_before_the_offline_dispatch(self):
        broker = OfflineBroker()
        review = review_outbound(self.context, self.destination, request_id="request", nonce="nonce", now=100)
        proposal = broker.dispatch(self.context, self.destination, review, now=101, response="frozen text")
        self.assertEqual("frozen text", proposal.text)
        self.assertEqual(1, len(broker.sent))
        with self.assertRaises(ContractError):
            broker.dispatch(self.context, self.destination, review, now=102, response="again")

    def test_loopback_is_remote_capable_until_proven_and_live_dispatch_is_disabled(self):
        for url in ("http://127.0.0.1:11434/v1/chat/completions", "https://example.org/v1/chat/completions"):
            destination = Destination(url, "model")
            self.assertTrue(destination.remote_capable)
            broker = OfflineBroker()
            review = review_outbound(self.context, destination, request_id="request", nonce="nonce", now=100)
            with self.assertRaises(ContractError):
                broker.dispatch(self.context, destination, review, now=101, response="text")
            self.assertEqual((), broker.sent)

    def test_credentials_redirect_targets_and_non_http_schemes_are_not_endpoints(self):
        for url in ("file:///etc/passwd", "https://user:pass@example.org/v1", "https://example.org/v1?key=secret",
                    "http://example.org/v1", "http://localhost:11434/v1", "https://example.org/v1#other"):
            with self.subTest(url=url), self.assertRaises(ContractError):
                Destination(url, "model")

    def test_manuscript_requires_an_explicit_selected_excerpt(self):
        record = ContextRecord.create("project", "anchor", "manuscript", "private", {"excerpt": "Selected sentence"})
        with self.assertRaises(ContractError):
            compile_context((record,), ContextSelection("project", "episode", "compare-evidence", (("anchor", ("excerpt",)),)))
        result = compile_context((record,), ContextSelection("project", "episode", "draft-manuscript", (("anchor", ("excerpt",)),)))
        self.assertIn(b"Selected sentence", result.payload)

    def test_erasure_retains_the_trace_referenced_by_the_proposal(self):
        broker = OfflineBroker()
        review = review_outbound(self.context, self.destination, request_id="request", nonce="nonce", now=100)
        proposal = broker.dispatch(self.context, self.destination, review, now=101, response="text")
        broker.erase_payload("request")
        self.assertIsNone(broker.sent[0].payload)
        self.assertEqual("erased", broker.sent[0].payload_availability)
        self.assertEqual(proposal.trace_digest, broker.sent[0].digest)

    def test_malformed_response_consumes_the_review_and_cannot_be_retried_silently(self):
        broker = OfflineBroker()
        review = review_outbound(self.context, self.destination, request_id="request", nonce="nonce", now=100)
        with self.assertRaises(ContractError):
            broker.dispatch(self.context, self.destination, review, now=101, response="")
        with self.assertRaises(ContractError):
            broker.dispatch(self.context, self.destination, review, now=102, response="later")
        self.assertEqual("malformed", broker.sent[0].disposition)


if __name__ == "__main__":
    unittest.main()
