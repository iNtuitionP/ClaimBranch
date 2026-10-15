"""Closed schema for portable research-history candidates, not accepted writes.

The local validator supports only the vocabulary used by these owned schemas.
It is not a general JSON Schema engine; no remote schema is loaded.
"""
from .graph_vocabulary import SCIENTIFIC_EDGE_TYPES
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
    "scientific-edge": obj(edge_type={"enum": list(SCIENTIFIC_EDGE_TYPES)},
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
LIFECYCLE_SEED = obj(schema_version={"const": 4}, profile={"const": "paper"}, project_id=ID,
    paper_title=TEXT, claim_id=ID, claim_statement=TEXT, anchor_id=ID)

PAPER_SERIES_SEED = obj(schema_version={"type": "integer", "const": 3}, project_id=ID,
                       paper_title=TEXT, claim_id=ID, claim_statement=TEXT, anchor_id=ID)


def seed_schema(version):
    if type(version) is not int or version not in (1, 2, 3, 4, 5):
        raise ContractError("unknown research contract version")
    if version == 5:
        from .argument_import import imported_seed_schema
        return imported_seed_schema()
    return deepcopy({1: SEED, 2: PAPER_SEED, 3: PAPER_SERIES_SEED, 4: LIFECYCLE_SEED}[version])


def paper_payloads(version=3):
    from .paper_capacity import LIMITS
    limits = LIMITS if version in (4, 5) else PAPER_LIMITS
    bodies = deepcopy(BODIES)
    bodies["claim"] = obj(role={"enum": ["main", "subclaim"]}, statement=TEXT, scope=TEXT,
                          parent_ids=array(ID, 3, 1, True))
    bodies["interpretation"] = obj(statement=TEXT, observation_ids=array(ID, limits["observations"], unique=True))
    bodies["claim-status"]["properties"]["basis_ids"] = array(ID, limits["changes"], 1, True)
    bodies["experiment-plan"] = obj(claim_id=ID, objective=TEXT, status={"const": "planned"}, conditions=TEXT, metric=METRIC)
    change = {"oneOf": [obj(id=ID, kind={"const": kind}, body=body) for kind, body in bodies.items()]}
    payloads = deepcopy(PAYLOADS)
    payloads["record-experiment"] = EXPERIMENT
    payloads["record-evidence-event"]["properties"]["value"] = nullable(TEXT)
    payloads["record-evidence-event"]["required"].append("value")
    payloads["record-interpretation"] = obj(changes=array(change, limits["changes"], 1), judgment=JUDGMENT)
    payloads["apply-selected-merge"]["properties"]["selected_ids"] = array(ID, limits["changes"], 1, True)
    if version == 5:
        from .argument_import import imported_reference_schema
        payloads['create-imported-reasoning-branch'] = obj()
        for old, new in (('record-interpretation', 'record-imported-interpretation'), ('apply-selected-merge', 'apply-imported-merge')):
            payloads[new] = deepcopy(payloads[old])
            payloads[new]['properties'].update(source_node_id=ID, source_refs=array(imported_reference_schema(), 2048))
            payloads[new]['required'].extend(['source_node_id', 'source_refs'])
    return payloads


# Source identities are private read-only bindings, never scientific evidence.
ANCHOR_PATH = {'type':'string','minLength':2,'maxLength':8192,'pattern':'^(?:[0-9a-f]{2})+$'}
ANCHOR_NUMBER = {'type':'string','minLength':1,'maxLength':24,'pattern':'^(0|[1-9][0-9]*)$'}
ANCHOR_IDENTITY = obj(device=ANCHOR_NUMBER, inode=ANCHOR_NUMBER)
MANUSCRIPT_SOURCE = obj(root=ANCHOR_PATH,root_identity=ANCHOR_IDENTITY,
    git_dir=ANCHOR_PATH,git_identity=ANCHOR_IDENTITY,git_common_dir=ANCHOR_PATH,git_common_identity=ANCHOR_IDENTITY,
    manuscript=ANCHOR_PATH,anchor_id=ID,file_identity=ANCHOR_IDENTITY,size=ANCHOR_NUMBER,
    mtime_ns=ANCHOR_NUMBER,ctime_ns=ANCHOR_NUMBER,source_digest=HASH)
ANCHOR = obj(id=ID,kind={'enum':['text','figure','table','caption']},source=MANUSCRIPT_SOURCE,
    block_digest=HASH,block=array({'type':'string','minLength':1,'maxLength':10924,'pattern':'^[A-Za-z0-9+/]+={0,2}$'},8),
    expresses=array(ID,64,unique=True),plots=array(ID,256,unique=True),parents=array(ID,4,unique=True),rationale=TEXT)

WORDING_POLICY = obj(claim_id=ID, grade=TEXT, limitation=TEXT,
    allowed_wording=array(TEXT,16,unique=True), required_caveats=array(TEXT,16,unique=True),
    banned_phrases=array(TEXT,32,unique=True), placement=array({'enum':['main','appendix','abstract']},3,1,True), rationale=TEXT)
COMPANION = obj(id=ID, target_id=ID, companion_id=ID, scope={'enum':['anchor','paragraph']},
    status={'enum':['active','retired']}, rationale=TEXT)
ANCHOR_CONTEXT = obj(anchor_id=ID, placement={'enum':['main','appendix','abstract','unknown']},
    paragraphs=array(obj(index={'type':'integer','minimum':1,'maximum':256},
        expresses=array(ID,64,unique=True),plots=array(ID,256,unique=True)),256), rationale=TEXT)
REVISION_PAYLOADS = {'set-claim-wording':WORDING_POLICY,'set-claim-companion':COMPANION,'set-anchor-context':ANCHOR_CONTEXT}

CO_READING = obj(id=ID, statement=TEXT, scope=TEXT, observation_ids=array(ID,256,1,True),
    claim_id=ID, edge_id=ID, edge_type={'enum':list(SCIENTIFIC_EDGE_TYPES)},
    source_id=nullable(ID), origin={'enum':['human','ai','mixed','unknown']})
CO_REPORT = obj(id=ID,candidates=array(CO_READING,4,2),selected_ids=array(ID,4,2,True),
    companion_ids=array(ID,256,1,True),context_digest=HASH,judgment=JUDGMENT,
    disposition={'enum':['not-required','answered','deferred']},answers=array(TEXT,3,unique=True))

def command_schema(version=1):
    if version not in (6,7,8,9,10,11,12,13): seed_schema(version)
    if version == 11:
        from .critiques import PAYLOADS as CRITIQUE_PAYLOADS
    if version == 10:
        from .protocols import PAYLOADS as PROTOCOL_PAYLOADS
    if version == 9:
        from .typed_observations import PAYLOADS as MEASUREMENT_PAYLOADS
    payloads = {} if version == 12 else CRITIQUE_PAYLOADS if version == 11 else PROTOCOL_PAYLOADS if version == 10 else MEASUREMENT_PAYLOADS if version == 9 else {"record-co-report":CO_REPORT} if version == 8 else REVISION_PAYLOADS if version == 7 else {"register-manuscript-anchor":ANCHOR} if version == 6 else PAYLOADS if version == 1 else paper_payloads(version)
    if version == 12:
        from .critiques import PAYLOADS as C
        from .protocols import PAYLOADS as P
        from .typed_observations import PAYLOADS as M
        payloads={**C,**P,**M,**REVISION_PAYLOADS,'register-manuscript-anchor':ANCHOR,'record-co-report':CO_REPORT}
    if version == 13:
        from .graph_edits import payload_schema
        payloads={'revise-graph':payload_schema()}
    if 3 <= version <= 5:
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
            **({"contribution_origin":{"enum":["human","ai","mixed","unknown"]}} if version==12 else {}),
            evidence_watermark={"type": "integer", "minimum": 0, "maximum": 6 if version == 1 else (1024 if version in (4, 5, 6, 7, 8, 9, 10, 11, 12, 13) else PAPER_LIMITS["events"])}, payload=payload)
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


def normalize(value, schema, *, profile="episode"):
    if profile == "paper":
        from .paper_capacity import encode as paper_encode, decode as paper_decode
        normalized = paper_decode(paper_encode(value, purpose="project"), purpose="project")
    elif profile == "episode":
        normalized = decode(canonical_bytes(value))
    else:
        raise ContractError("unknown capacity profile")
    _check(normalized, schema)
    return normalized
