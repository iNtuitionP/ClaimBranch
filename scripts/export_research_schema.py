"""Regenerate/check the owned portable research-command JSON Schema."""
import argparse
import json
from pathlib import Path

from claimbranch.core.research_history import command_schema
from claimbranch.core.research_schema import PAPER_SEED, PAPER_SERIES_SEED
from claimbranch.application.paper_service import scenario_schema
from claimbranch.core.paper_context import request_schema, fields_schema
from claimbranch.core.paper_proposals import result_schema as typed_result_schema
from claimbranch.core.paper_changes import request_schema as changes_request_schema
from claimbranch.core.paper_changes import lineage_schema
from claimbranch.core.review_policy import assessment_schema, decision_schema
from claimbranch.core.paper_operation import operation_schema, review_schema as operation_review_schema
from claimbranch.core.paper_commit import commit_schema
from claimbranch.core.paper_record_transition import transition_schema
from claimbranch.application.paper_understanding import draft_schema as understanding_draft_schema
from claimbranch.core.debt import understanding_closure_schema
from claimbranch.application.paper_work_store import work_schema
from claimbranch.application.project_work import project_work_schema
from claimbranch.application.mac_runtime import runtime_schema
from claimbranch.application.mac_key_registration import key_registration_schema
from claimbranch.application.mac_review_signing import signing_request_schema
from claimbranch.application.mac_worker import worker_schema
from claimbranch.application.mac_enrollment import enrollment_schema
from claimbranch.application.project_initialization import initialization_schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "schemas"
    schemas = {"research-command-v1.json": command_schema(), "research-command-v2.json": command_schema(2),
               "research-command-v3.json": command_schema(3),
               "paper-seed-v2.json": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                      "$id": "urn:claimbranch:paper-seed:v2", **PAPER_SEED},
               "paper-seed-v3.json": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                      "$id": "urn:claimbranch:paper-seed:v3", **PAPER_SERIES_SEED},
               "paper-scenario-v1.json": scenario_schema(),
               "paper-context-request-v1.json": request_schema(), "paper-context-fields-v2.json": fields_schema(),
               "provider-result-v2.json": typed_result_schema(),
               "paper-changes-request-v1.json": changes_request_schema(),
               "paper-amendment-lineage-v1.json": lineage_schema(),
               "paper-amendment-lineage-v2.json": lineage_schema(2),
               "paper-review-assessment-v1.json": assessment_schema(),
               "paper-review-decision-v1.json": decision_schema(),
               "paper-operation-v1.json": operation_schema(),
               "paper-operation-review-v1.json": operation_review_schema(),
               "paper-operation-review-v2.json": operation_review_schema(2),
               "paper-commit-candidate-v1.json": commit_schema(),
               "paper-record-transition-v1.json": transition_schema(),
               "project-initialization-review-v1.json": initialization_schema(),
               "paper-work-v1.json": work_schema(),
               "paper-work-v2.json": work_schema(2),
               "paper-work-v3.json": work_schema(3),
               "paper-work-v4.json": work_schema(4),
               "paper-work-v5.json": work_schema(5),
               "paper-work-v6.json": work_schema(6),
               "paper-work-v7.json": work_schema(7),
               "paper-work-v8.json": work_schema(8),
               "paper-work-v9.json": work_schema(9),
               "paper-work-v10.json": work_schema(10),
               "project-work-v1.json": project_work_schema(),
               "project-work-v2.json": project_work_schema(2),
               "project-work-v3.json": project_work_schema(3),
               "project-work-v4.json": project_work_schema(4),
               "project-work-v5.json": project_work_schema(5),
               "project-work-v6.json": project_work_schema(6),
               "mac-runtime-build-v1.json": runtime_schema(),
               "key-registration-v1.json": key_registration_schema(),
               "review-signing-request-v1.json": signing_request_schema(),
               "proposal-worker-build-v1.json": worker_schema(),
               "local-enrollment-v1.json": enrollment_schema(),
               "paper-understanding-draft-v1.json": understanding_draft_schema(),
               "understanding-closure-review-v1.json": understanding_closure_schema()}
    for name, value in schemas.items():
        path = root / name
        expected = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                print("Research schema is missing or stale: " + name)
                return 1
        else:
            root.mkdir(exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            print("Generated schemas/" + name)
    if args.check:
        print("Research schemas are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
