"""Closed schema for portable research-history candidates, not accepted writes.

The local validator supports only the vocabulary used by these owned schemas.
It is not a general JSON Schema engine; no remote schema is loaded.
"""
from copy import deepcopy
from datetime import datetime
import re

from .canonical import ContractError, bounded_text, canonical_bytes, decode


ID = {"type": "string", "minLength": 1, "maxLength": 128,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]*$"}
TEXT = {"type": "string", "minLength": 1, "maxLength": 16384, "x-utf8-maxBytes": 16384}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$", "minLength": 64, "maxLength": 64}
NULL = {"type": "null"}


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def array(items, maximum, minimum=0, unique=False):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum, "uniqueItems": unique}


def nullable(value):
    return {"oneOf": [value, NULL]}


CONTRIBUTION = obj(contributor={"enum": ["human", "ai"]}, text=TEXT, rationale=nullable(TEXT),
                   proposal_id=nullable(ID), trace_digest=nullable(HASH), parent_digest=nullable(HASH))
JUDGMENT = obj(project_id=ID, episode_id=ID, text=TEXT, rationale=TEXT,
               history=array(CONTRIBUTION, 8, 1))
BODIES = {
    "interpretation": obj(statement=TEXT, observation_ids=array(ID, 3, 1, True)),
    "scientific-edge": obj(edge_type={"enum": ["supports", "challenges", "qualifies"]},
                           source_id=ID, target_id=ID, rationale=TEXT),
    "claim-status": obj(claim_id=ID, status={"enum": ["supported", "contested"]},
                        basis_ids=array(ID, 6, 1, True)),
    "experiment-plan": obj(claim_id=ID, objective=TEXT, status={"const": "planned"}),
}
CHANGE = {"oneOf": [obj(id=ID, kind={"const": kind}, body=body) for kind, body in BODIES.items()]}
HEADS = {"oneOf": [obj(main=ID), obj(main=ID, alternative=ID)]}
PAYLOADS = {
    "record-evidence-event": obj(event_id=ID, target_id=ID, run_id=ID,
        action={"enum": ["confirm", "correct", "invalidate", "retract"]},
        statement=nullable(TEXT), rationale=TEXT, supersedes_id=nullable(ID)),
    "create-reasoning-branch": obj(),
    "record-interpretation": obj(changes=array(CHANGE, 9, 1), judgment=JUDGMENT),
    "apply-selected-merge": obj(selected_ids=array(ID, 9, 1, True), judgment=JUDGMENT,
        disposition={"enum": ["not-required", "answered", "deferred"]}, answers=array(TEXT, 3)),
}
SEED = obj(schema_version={"type": "integer", "const": 1}, project_id=ID, episode_id=ID,
           claim_id=ID, claim_statement=TEXT, anchor_id=ID)

PAPER_LIMITS = {"commands": 64, "events": 32, "observations": 16, "experiments": 8,
                "claims": 16, "edges": 32, "plans": 8, "changes": 64, "depth": 8}
METRIC = obj(name=TEXT, definition=TEXT, unit=TEXT, comparison=TEXT)
EXPERIMENT = obj(id=ID, question=TEXT, method=TEXT, conditions=TEXT, metric=METRIC, source_ref=TEXT)
PAPER_SEED = obj(schema_version={"type": "integer", "const": 2}, project_id=ID, episode_id=ID,
                paper_title=TEXT, claim_id=ID, claim_statement=TEXT, anchor_id=ID)
PAPER_SERIES_LIMITS = {**PAPER_LIMITS, "episodes": 8, "interpretations": 8}
PAPER_SERIES_SEED = obj(schema_version={"type": "integer", "const": 3}, project_id=ID,
                       paper_title=TEXT, claim_id=ID, claim_statement=TEXT, anchor_id=ID)


def seed_schema(version):
    if type(version) is not int or version not in (1, 2, 3):
        raise ContractError("unknown research contract version")
    return deepcopy({1: SEED, 2: PAPER_SEED, 3: PAPER_SERIES_SEED}[version])


def paper_payloads():
    bodies = deepcopy(BODIES)
    bodies["claim"] = obj(role={"enum": ["main", "subclaim"]}, statement=TEXT, scope=TEXT,
                          parent_ids=array(ID, 3, 1, True))
    bodies["interpretation"] = obj(statement=TEXT, observation_ids=array(ID, PAPER_LIMITS["observations"], unique=True))
    bodies["claim-status"]["properties"]["basis_ids"] = array(ID, PAPER_LIMITS["changes"], 1, True)
    bodies["experiment-plan"] = obj(claim_id=ID, objective=TEXT, status={"const": "planned"}, conditions=TEXT, metric=METRIC)
    change = {"oneOf": [obj(id=ID, kind={"const": kind}, body=body) for kind, body in bodies.items()]}
    payloads = deepcopy(PAYLOADS)
    payloads["record-experiment"] = EXPERIMENT
    payloads["record-evidence-event"]["properties"]["value"] = nullable(TEXT)
    payloads["record-evidence-event"]["required"].append("value")
    payloads["record-interpretation"] = obj(changes=array(change, PAPER_LIMITS["changes"], 1), judgment=JUDGMENT)
    payloads["apply-selected-merge"]["properties"]["selected_ids"] = array(ID, PAPER_LIMITS["changes"], 1, True)
    return payloads


def command_schema(version=1):
    seed_schema(version)
    payloads = PAYLOADS if version == 1 else paper_payloads()
    if version == 3:
        payloads.update({"open-episode": obj(title=TEXT, question=TEXT), "close-episode": obj()})
    return deepcopy({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:claimbranch:research-command:v{version}",
        "$comment": "Generated by python -m scripts.export_research_schema. Candidate contract only; no authority.",
        "title": f"ClaimBranch portable research-history command v{version}",
        "oneOf": [obj(schema_version={"type": "integer", "const": version}, id=ID,
            project_id=ID, episode_id=ID,
            created_at={"type": "string", "format": "date-time", "minLength": 20, "maxLength": 20,
                        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
            operation_type={"const": kind}, expected_heads=HEADS,
            evidence_watermark={"type": "integer", "minimum": 0, "maximum": 6 if version == 1 else PAPER_LIMITS["events"]}, payload=payload)
            for kind, payload in payloads.items()]})


def _check(value, schema):
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            try:
                _check(value, option)
                matches += 1
            except ContractError:
                pass
        if matches != 1:
            raise ContractError("value does not match exactly one closed schema")
        return
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ContractError("unknown constant or version")
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        raise ContractError("unknown enum")
    kind = schema.get("type")
    if kind and type(value) is not {"string": str, "integer": int, "object": dict, "array": list, "null": type(None)}[kind]:
        raise ContractError("incorrect primitive type")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            raise ContractError("unknown or missing field")
        for name, child in schema["properties"].items():
            _check(value[name], child)
    elif kind == "array":
        if not schema["minItems"] <= len(value) <= schema["maxItems"]:
            raise ContractError("collection outside finite bounds")
        for item in value:
            _check(item, schema["items"])
        if schema["uniqueItems"] and len({canonical_bytes(item) for item in value}) != len(value):
            raise ContractError("duplicate collection item")
    elif kind == "string":
        limit = schema.get("x-utf8-maxBytes", schema.get("maxLength", 16384))
        # Only schemas explicitly admitting empty draft text relax nonblank
        # validation. Existing scientific fields keep their required content.
        if schema.get("minLength", 1) != 0:
            bounded_text(value, limit=limit)
        elif len(value.encode("utf-8")) > limit:
            raise ContractError("text exceeds its UTF-8 limit")
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 16384):
            raise ContractError("string outside finite bounds")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContractError("text outside finite format")
        if schema.get("format") == "date-time":
            try:
                datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError as error:
                raise ContractError("invalid UTC timestamp") from error
    elif kind == "integer" and not schema.get("minimum", 0) <= value <= schema.get("maximum", 2**53 - 1):
        raise ContractError("integer outside finite bounds")


def normalize(value, schema):
    normalized = decode(canonical_bytes(value))
    _check(normalized, schema)
    return normalized
