from dataclasses import replace
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.context import ContextRecord, ContextSelection, compile_context
from claimbranch.core.paper_context import request_schema


class PaperContextEgressTests(unittest.TestCase):
    def setUp(self):
        self.binding = canonical_bytes({"ref": "main", "view_digest": "a" * 64})
        self.record = ContextRecord.create("p", "c", "claim", "private",
            {"statement": "A bounded synthetic claim", "status": "proposed", "role": "thesis", "scope": None, "parent_ids": []}, schema_version=2)
        self.selection = ContextSelection("p", "e", "critique-interpretation", (("c", ("statement",)),), schema_version=2, binding=self.binding)

    def test_original_profile_retains_exact_wire_bytes(self):
        record = ContextRecord.create("p", "c", "claim", "redacted", {"statement": "Example", "status": "supported"})
        selection = ContextSelection("p", "e", "critique-interpretation", (("c", ("statement",)),))
        self.assertEqual(b'{"episode_id":"e","project_id":"p","purpose":"critique-interpretation","records":[{"fields":{"statement":"Example"},"id":"c","kind":"claim","sensitivity":"redacted"}],"redactions":[{"field":"status","record_id":"c"}],"schema_version":1}',
                         compile_context((record,), selection).payload)

    def test_versions_binding_and_nested_shapes_cannot_be_coerced(self):
        for version in (True, 0, 3, "2"):
            with self.subTest(version=version), self.assertRaises(ContractError):
                replace(self.selection, schema_version=version)
        for binding in (None, b"{}", canonical_bytes({"ref": "main", "view_digest": "a" * 64, "approved": True})):
            with self.subTest(binding=binding), self.assertRaises(ContractError):
                replace(self.selection, binding=binding)
        v1 = ContextRecord.create("p", "c", "claim", "private", {"statement": "A claim"})
        with self.assertRaises(ContractError):
            compile_context((v1,), self.selection)
        for fields in ({"parent_ids": "c"}, {"scope": False}, {"metric": {"unit": "points"}}, {"status": "accepted"}):
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                ContextRecord.create("p", "c", "claim", "private", fields, schema_version=2)
        exported = request_schema()
        exported["properties"]["project_id"]["maxLength"] = 1000
        self.assertEqual(128, request_schema()["properties"]["project_id"]["maxLength"])

    def test_node_and_utf8_budgets_reject_instead_of_truncating(self):
        records = tuple(replace(self.record, id=f"c-{index}") for index in range(17))
        selection = replace(self.selection, fields=tuple((record.id, ("statement",)) for record in records))
        with self.assertRaises(ContractError):
            compile_context(records, selection)
        records = tuple(ContextRecord.create("p", f"c-{index}", "claim", "private", {"statement": "연" * 5000}, schema_version=2)
                        for index in range(5))
        selection = replace(self.selection, fields=tuple((record.id, ("statement",)) for record in records))
        with self.assertRaisesRegex(ContractError, "byte budget"):
            compile_context(records, selection)
        compile_context(records[:4], replace(selection, fields=selection.fields[:4]))

    def test_measurement_and_plan_status_cannot_be_hidden(self):
        for kind, fields, name in (("observation", {"statement": "Earlier result", "status": "retracted"}, "statement"),
                                   ("experiment-plan", {"objective": "Unrun test", "status": "planned"}, "objective")):
            record = ContextRecord.create("p", "item", kind, "private", fields, schema_version=2)
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                compile_context((record,), replace(self.selection, fields=(("item", (name,)),)))
            value = compile_context((record,), replace(self.selection, fields=(("item", (name, "status")),)))
            self.assertEqual(fields["status"], decode(value.payload)["records"][0]["fields"]["status"])

    def test_secret_nested_paths_and_relation_fields_stay_closed(self):
        with self.assertRaises(ContractError):
            compile_context((replace(self.record, sensitivity="secret"),), self.selection)
        edge = ContextRecord.create("p", "edge", "scientific-relation", "private",
            {"source_id": "c", "target_id": "c", "edge_type": "supports", "rationale": "Some reason"}, schema_version=2)
        with self.assertRaises(ContractError):
            compile_context((self.record, edge), replace(self.selection, fields=(*self.selection.fields, ("edge", ("rationale",)))))
        source = ContextRecord.create("p", "run", "experiment-record", "private",
            {"source": {"reference": "file:///tmp/private-result.csv", "availability": "unverified"}}, schema_version=2)
        with self.assertRaises(ContractError):
            compile_context((source,), replace(self.selection, fields=(("run", ("source",)),)))

    def test_interpretation_support_does_not_admit_non_scientific_endpoints(self):
        kinds = (("interpretation", {"statement": "A reading."}),
                 ("experiment-record", {"question": "A measurement question."}),
                 ("experiment-plan", {"objective": "An unrun plan.", "status": "planned"}))
        for kind, fields in kinds:
            source = ContextRecord.create("p", "source", kind, "private", fields, schema_version=2)
            for reverse in (False, True):
                edge = ContextRecord.create("p", "edge", "scientific-relation", "private", {
                    "source_id": "c" if reverse else "source", "target_id": "source" if reverse else "c",
                    "edge_type": "supports", "rationale": "Explicit relationship."}, schema_version=2)
                selection = replace(self.selection, fields=(*self.selection.fields, ("source", tuple(fields)),
                    ("edge", ("source_id", "target_id", "edge_type", "rationale"))))
                with self.subTest(kind=kind, reverse=reverse):
                    if kind == "interpretation" and not reverse:
                        compile_context((self.record, source, edge), selection)
                    else:
                        with self.assertRaises(ContractError):
                            compile_context((self.record, source, edge), selection)


if __name__ == "__main__":
    unittest.main()
