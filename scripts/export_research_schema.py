"""Regenerate/check the owned portable research-command JSON Schema."""
import argparse
import json
from pathlib import Path

from claimbranch.core.paper_capacity import shared_audit_schema
from claimbranch.core.research_schema import seed_schema
from claimbranch.core.research_history import command_schema
from claimbranch.core.research_schema import PAPER_SEED, PAPER_SERIES_SEED
from claimbranch.application.paper_service import scenario_schema
from claimbranch.core.paper_context import request_schema, fields_schema
from claimbranch.core.paper_proposals import result_schema as typed_result_schema
from claimbranch.core.advisory import advice_result_schema
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
from claimbranch.core.argument_import import import_schema, imported_reference_schema
from claimbranch.application.co_report import INPUT as CO_REPORT_INPUT
from claimbranch.core.typed_observations import INPUT as MEASUREMENT_INPUT
from claimbranch.core.protocols import INPUT as PROTOCOL_INPUT,input_schema as protocol_input_schema
from claimbranch.core.critiques import INPUT as CRITIQUE_INPUT
from claimbranch.application.canonical_share import share_schema
from claimbranch.application.metadata_batch import batch_schema


def compact_schema(value, *, inline_single_use=False):
    """Self-contained $defs for new exports; runtime/legacy schemas stay inline.

    Absolute root references retain meaning even inside nested schema $id scopes.
    This changes presentation only, avoiding tens of MiB of repeated contracts.
    """
    import hashlib
    root_id=value['$id'];definitions={}
    def visit(node):
        if isinstance(node,list):return [visit(child) for child in node]
        if not isinstance(node,dict):return node
        result={}
        for key,child in node.items():
            if key in ('properties','patternProperties','$defs','definitions','dependentSchemas'):
                result[key]={name:visit(schema) for name,schema in child.items()}
            elif key in ('oneOf','anyOf','allOf','prefixItems'):
                result[key]=[visit(schema) for schema in child]
            elif key in ('items','additionalProperties','unevaluatedProperties','not','if','then','else','contains','propertyNames'):
                result[key]=visit(child)
            else:result[key]=child
        encoded=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
        if len(encoded)<256:return result
        key='s'+hashlib.sha256(encoded).hexdigest()
        if key in definitions and definitions[key]!=result:raise ValueError('Schema definition hash collision')
        definitions[key]=result
        return {'$ref':root_id+'#/$defs/'+key}
    metadata={key:value[key] for key in ('$schema','$id','$comment') if key in value}
    body=visit({key:child for key,child in value.items() if key not in metadata})
    result={**metadata,**body,'$defs':definitions}
    if not inline_single_use:return result
    # New exports can inline one-use definitions; older wire files stay fixed.
    # Traverse schema positions only: literal const/enum user data is untouched.
    from collections import Counter
    counts=Counter();prefix=root_id+'#/$defs/'
    def walk(node, transform):
        if not isinstance(node,dict):return node
        output={}
        for key,child in node.items():
            if key in ('properties','patternProperties','$defs','definitions','dependentSchemas'):
                output[key]={name:walk(schema,transform) for name,schema in child.items()}
            elif key in ('oneOf','anyOf','allOf','prefixItems'):
                output[key]=[walk(schema,transform) for schema in child]
            elif key in ('items','additionalProperties','unevaluatedProperties','not','if','then','else','contains','propertyNames'):
                output[key]=walk(child,transform)
            else:output[key]=child
        return transform(output)
    def count(node):
        if node.get('$ref','').startswith(prefix):counts[node['$ref'][len(prefix):]]+=1
        return node
    walk(result,count)
    def inline(node):
        reference=node.get('$ref','')
        if reference.startswith(prefix) and counts[reference[len(prefix):]]==1:
            return {**walk(definitions[reference[len(prefix):]],inline),**{key:child for key,child in node.items() if key!='$ref'}}
        return node
    return {**walk({key:child for key,child in result.items() if key!='$defs'},inline),
        '$defs':{key:walk(schema,inline) for key,schema in definitions.items() if counts[key]>1}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "schemas"
    from claimbranch.core.argument_import_v2 import import_schema as ledger_schema, manifest_schema
    schemas = {"research-command-v20.json":command_schema(20),"paper-work-v32.json":work_schema(32),"project-work-v28.json":project_work_schema(28),"metadata-batch-v4.json":batch_schema(4),"argument-import-v5.json":ledger_schema(5),"argument-source-manifest-v4.json":manifest_schema(4),"research-command-v19.json":command_schema(19),"protocol-input-v2.json":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:claimbranch:protocol-input:v2",**protocol_input_schema(2)},"metadata-batch-v3.json":batch_schema(3),"paper-work-v31.json":work_schema(31),"project-work-v27.json":project_work_schema(27),"canonical-share-v4.json":share_schema(4),"argument-import-v4.json":ledger_schema(4),"argument-source-manifest-v3.json":manifest_schema(3),"paper-seed-v18.json":{"$schema":"https://json-schema.org/draft/2020-12/schema",**seed_schema(18)},"research-command-v18.json":command_schema(18),"paper-work-v30.json":work_schema(30),"project-work-v26.json":project_work_schema(26),"shared-audit-manifest-v2.json":shared_audit_schema(2),"canonical-share-v3.json":share_schema(3),"argument-import-v3.json":ledger_schema(3),"argument-source-manifest-v2.json":manifest_schema(2),"paper-work-v29.json":work_schema(29),"project-work-v25.json":project_work_schema(25),"metadata-batch-v2.json":batch_schema(2),"research-command-v17.json":command_schema(17),"paper-work-v28.json":work_schema(28),"project-work-v24.json":project_work_schema(24),"shared-audit-manifest-v1.json":shared_audit_schema(),"research-command-v16.json":command_schema(16), "paper-work-v27.json":work_schema(27), "project-work-v23.json":project_work_schema(23),"research-command-v15.json":command_schema(15), "paper-work-v26.json":work_schema(26), "project-work-v22.json":project_work_schema(22),"paper-work-v25.json":work_schema(25), "project-work-v21.json":project_work_schema(21),"imported-source-reference-v2.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", **imported_reference_schema(2)},"paper-seed-v14.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", **seed_schema(14)}, "research-command-v14.json":command_schema(14), "paper-work-v24.json":work_schema(24), "project-work-v20.json":project_work_schema(20),"argument-import-v2.json":ledger_schema(),"argument-source-manifest-v1.json":manifest_schema(),"metadata-batch-v1.json": batch_schema(),"canonical-share-v1.json": share_schema(),"canonical-share-v2.json": share_schema(2),"critique-input-v1.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", "$id":"urn:claimbranch:critique-input:v1", **CRITIQUE_INPUT},"protocol-input-v1.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", "$id":"urn:claimbranch:protocol-input:v1", **PROTOCOL_INPUT},"measurement-input-v1.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", "$id":"urn:claimbranch:measurement-input:v1", **MEASUREMENT_INPUT}, "co-report-input-v1.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", "$id":"urn:claimbranch:co-report-input:v1", **CO_REPORT_INPUT}, "argument-import-v1.json": import_schema(), "research-command-v1.json": command_schema(), "research-command-v2.json": command_schema(2),
               "research-command-v3.json": command_schema(3),
               "research-command-v4.json": command_schema(4),
               "research-command-v5.json": command_schema(5),
               "research-command-v6.json": command_schema(6),
               "research-command-v7.json": command_schema(7),
               "research-command-v8.json": command_schema(8),
               "research-command-v9.json": command_schema(9),
               "research-command-v10.json": command_schema(10),
               "research-command-v11.json": command_schema(11),
               "research-command-v12.json": command_schema(12),
               "research-command-v13.json": command_schema(13),
               "paper-seed-v5.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", **seed_schema(5)},
               "paper-seed-v4.json": {"$schema":"https://json-schema.org/draft/2020-12/schema", **seed_schema(4)},
               "paper-seed-v2.json": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                      "$id": "urn:claimbranch:paper-seed:v2", **PAPER_SEED},
               "paper-seed-v3.json": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                      "$id": "urn:claimbranch:paper-seed:v3", **PAPER_SERIES_SEED},
               "paper-scenario-v1.json": scenario_schema(),
               "paper-context-request-v1.json": request_schema(), "paper-context-fields-v2.json": fields_schema(),
               "provider-result-v2.json": typed_result_schema(),
               "provider-advice-v1.json": advice_result_schema(),
               "paper-changes-request-v1.json": changes_request_schema(),
               "paper-amendment-lineage-v1.json": lineage_schema(),
               "paper-amendment-lineage-v2.json": lineage_schema(2),
               "paper-amendment-lineage-v3.json": lineage_schema(3),
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
               "paper-work-v11.json": work_schema(11),
               "paper-work-v12.json": work_schema(12),
               "paper-work-v13.json": work_schema(13),
               "paper-work-v14.json": work_schema(14),
               "paper-work-v15.json": work_schema(15),
               "paper-work-v16.json": work_schema(16),
               "paper-work-v17.json": work_schema(17),
               "paper-work-v18.json": work_schema(18),
               "paper-work-v19.json": work_schema(19),
               "paper-work-v20.json": work_schema(20),
               "paper-work-v21.json": work_schema(21),
               "paper-work-v22.json": work_schema(22),
               "paper-work-v23.json": work_schema(23),
               "project-work-v1.json": project_work_schema(),
               "project-work-v2.json": project_work_schema(2),
               "project-work-v3.json": project_work_schema(3),
               "project-work-v4.json": project_work_schema(4),
               "project-work-v5.json": project_work_schema(5),
               "project-work-v6.json": project_work_schema(6),
               "project-work-v7.json": project_work_schema(7),
               "project-work-v8.json": project_work_schema(8),
               "project-work-v9.json": project_work_schema(9),
               "project-work-v10.json": project_work_schema(10),
               "project-work-v11.json": project_work_schema(11),
               "project-work-v12.json": project_work_schema(12),
               "project-work-v13.json": project_work_schema(13),
               "project-work-v14.json": project_work_schema(14),
               "project-work-v15.json": project_work_schema(15),
               "project-work-v16.json": project_work_schema(16),
               "project-work-v17.json": project_work_schema(17),
               "project-work-v18.json": project_work_schema(18),
               "project-work-v19.json": project_work_schema(19),
               "mac-runtime-build-v1.json": runtime_schema(),
               "key-registration-v1.json": key_registration_schema(),
               "review-signing-request-v1.json": signing_request_schema(),
               "proposal-worker-build-v1.json": worker_schema(),
               "local-enrollment-v1.json": enrollment_schema(),
               "paper-understanding-draft-v1.json": understanding_draft_schema(),
               "understanding-closure-review-v1.json": understanding_closure_schema()}
    for name, value in schemas.items():
        if name in ('paper-work-v28.json','project-work-v24.json','paper-work-v29.json','project-work-v25.json','paper-work-v30.json','project-work-v26.json','paper-work-v31.json','project-work-v27.json','paper-work-v32.json','project-work-v28.json'):value=compact_schema(value,inline_single_use=name in ('paper-work-v31.json','project-work-v27.json','paper-work-v32.json','project-work-v28.json'))
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
