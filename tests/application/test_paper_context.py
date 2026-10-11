from copy import deepcopy
import unittest

from claimbranch.application.paper_service import PaperService
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.context import Destination, OfflineBroker, review_outbound
from tests.contract.test_paper_history import paper, command, experiment
from tests.contract.test_paper_episodes import first_episode, command as series_command


def selection(service, ref="alternative"):
    view = service.query(ref)
    return {"schema_version": 1, "project_id": view["project_id"], "episode_id": view["episode_id"],
            "ref": ref, "view_digest": view["digest"], "purpose": "plan-experiment",
            "selections": [
                {"record_id": "claim-pruning-detail", "fields": ["statement", "role", "scope", "parent_ids"]},
                {"record_id": "obs-1", "fields": ["statement", "status", "value", "metric", "conditions", "source"]},
                {"record_id": "replication", "fields": ["objective", "status", "conditions", "metric"]}],
            "scientific_edge_ids": ["edge-pruning"]}


class PaperContextTests(unittest.TestCase):
    def setUp(self):
        self.history, _ = paper()
        self.service = PaperService(self.history)
        self.request = selection(self.service)

    def test_selected_scientific_context_has_measurement_scope_and_source_uncertainty(self):
        before = self.history.manifest()
        bundle = self.service.compile_context(self.request)
        value = decode(bundle.payload)
        records = {item["id"]: item for item in value["records"]}
        self.assertEqual(2, value["schema_version"])
        self.assertEqual({"ref": "alternative", "view_digest": self.request["view_digest"]}, value["binding"])
        self.assertEqual("unverified-candidate", value["authority"])
        self.assertEqual({"obs-1", "claim-pruning-detail", "replication", "edge-pruning"}, set(records))
        observation = records["obs-1"]["fields"]
        self.assertEqual("percentage points", observation["metric"]["unit"])
        self.assertEqual("0.4", observation["value"])
        self.assertEqual({"reference": "synthetic:paper-accuracy-example", "availability": "unverified"}, observation["source"])
        self.assertEqual("planned", records["replication"]["fields"]["status"])
        self.assertEqual("supports", records["edge-pruning"]["fields"]["edge_type"])
        self.assertTrue(all(item["sensitivity"] == "private" for item in records.values()))
        self.assertNotIn(b"history", bundle.payload)
        self.assertNotIn(b"original_statement", bundle.payload)
        self.assertEqual(before, self.history.manifest())

    def test_explicit_selection_never_expands_neighbors_or_treats_parents_as_support(self):
        request = dict(self.request, scientific_edge_ids=[])
        bundle = self.service.compile_context(request)
        records = decode(bundle.payload)["records"]
        self.assertEqual(3, len(records))
        self.assertFalse(any(item["kind"] == "scientific-relation" for item in records))
        request["scientific_edge_ids"] = ["edge-shared"]
        with self.assertRaises(ContractError):
            self.service.compile_context(request)
        structural = next(item for item in self.service.query("alternative")["relations"] if item["type"] == "part-of")
        with self.assertRaises(ContractError):
            self.service.compile_context(dict(request, scientific_edge_ids=[structural["key"]]))

    def test_interpretation_to_claim_context_requires_explicit_endpoints_and_episode_origin(self):
        for version in (2, 3):
            with self.subTest(version=version):
                history = self.history if version == 2 else first_episode(merge=False, close=False)
                edge = {"id": "edge-reading", "kind": "scientific-edge", "body": {
                    "source_id": "interpretation", "target_id": "claim-pruning-detail",
                    "edge_type": "supports", "rationale": "This reading connects the measured loss to the claim."}}
                history = history.append((command if version == 2 else series_command)(history,
                    "record-interpretation", {"changes": [edge], "judgment": history.view("alternative")["judgment"]}))
                service = PaperService(history)
                request = dict(selection(service), purpose="critique-interpretation", scientific_edge_ids=["edge-reading"],
                    selections=[{"record_id": "interpretation", "fields": ["statement", "episode_id"]},
                                {"record_id": "claim-pruning-detail", "fields": ["statement", "status"]}])
                records = decode(service.compile_context(request).payload)["records"]
                self.assertEqual({"interpretation", "claim-pruning-detail", "edge-reading"}, {item["id"] for item in records})
                for missing in (0, 1):
                    with self.assertRaises(ContractError):
                        service.compile_context(dict(request, selections=[request["selections"][missing]]))
                if version == 3:
                    hidden_origin = deepcopy(request)
                    hidden_origin["selections"][0]["fields"] = ["statement"]
                    with self.assertRaises(ContractError):
                        service.compile_context(hidden_origin)

    def test_fields_records_identity_and_classification_are_closed(self):
        variants = [dict(self.request, project_id="other"), dict(self.request, episode_id="other"),
                    dict(self.request, ref="main"), dict(self.request, sensitivity="public"),
                    dict(self.request, schema_version=True), dict(self.request, view_digest="a" * 64),
                    dict(self.request, scientific_edge_ids=["edge-pruning", "edge-pruning"])]
        for key, fields in (("obs-1", ["history"]), ("obs-1", ["artifact_bytes"]),
                            ("obs-1", ["metric", "metric"]), ("anchor", ["excerpt"]), ("unknown", ["statement"])):
            variants.append(dict(self.request, selections=[{"record_id": key, "fields": fields}], scientific_edge_ids=[]))
        variants.append(dict(self.request, selections=self.request["selections"] * 2))
        for request in variants:
            with self.subTest(request=request), self.assertRaises(ContractError):
                self.service.compile_context(request)

    def test_corrections_and_new_runs_invalidate_old_view_even_without_head_change(self):
        revised = self.history.append(command(self.history, "record-evidence-event", {
            "event_id": "correction", "target_id": "obs-1", "run_id": "run-accuracy", "action": "correct",
            "statement": "Corrected loss of 0.5 percentage points.", "value": "0.5", "rationale": "Correction", "supersedes_id": "event-1"}))
        added = self.history.append(command(self.history, "record-experiment", dict(experiment(), id="second-run")))
        self.assertEqual(self.history.heads, added.heads)
        self.assertEqual(self.history.watermark, added.watermark)
        for history in (revised, added):
            with self.assertRaises(ContractError):
                PaperService(history).compile_context(self.request)
        service = PaperService(revised)
        records = decode(service.compile_context(selection(service)).payload)["records"]
        self.assertEqual("0.5", next(item for item in records if item["id"] == "obs-1")["fields"]["value"])

    def test_nested_secret_or_absolute_source_is_rejected_only_if_selected(self):
        for location in ("source_ref", "metric"):
            commands = [decode(raw) for raw in self.history.commands]
            run = commands[0]["payload"]
            if location == "source_ref":
                run[location] = "/Users/researcher/private/results.csv"
            else:
                run["metric"]["definition"] = "Bearer abcdefghijklmnopqrstuvwxyz"
            history = type(self.history).replay(self.history.seed, tuple(canonical_bytes(item) for item in commands))
            service = PaperService(history)
            request = selection(service)
            with self.assertRaises(ContractError):
                service.compile_context(request)
            for item in request["selections"]:
                item["fields"] = [field for field in item["fields"] if field not in ("source", "metric")]
            service.compile_context(request)

    def test_version_two_uses_the_existing_exact_one_shot_offline_broker(self):
        bundle = self.service.compile_context(self.request)
        destination = Destination("offline://frozen", "paper-example-v1")
        review = review_outbound(bundle, destination, request_id="request", nonce="nonce", now=100)
        broker = OfflineBroker()
        proposal = broker.dispatch(bundle, destination, review, now=101, response="A synthetic second-seed critique.")
        self.assertEqual("project", proposal.project_id)
        self.assertEqual(1, len(broker.sent))
        with self.assertRaises(ContractError):
            broker.dispatch(bundle, destination, review, now=102, response="Repeated")
        changed = deepcopy(self.request)
        changed["selections"][1]["fields"].remove("metric")
        with self.assertRaises(ContractError):
            OfflineBroker().dispatch(self.service.compile_context(changed), destination, review, now=101, response="Wrong scope")


if __name__ == "__main__":
    unittest.main()
