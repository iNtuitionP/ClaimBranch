"""Read-only prior-argument interchange. Never generates historical commands.

Declared transformations and authorship are source claims, not verified facts.
Publication/retention uses separate personal storage; protected authority stays unavailable.
"""
from .graph_vocabulary import SCIENTIFIC_EDGE_TYPES
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
import re
import unicodedata

from .canonical import ContractError
from .paper_capacity import decode, encode, source_bytes, HISTORY_BYTES, LIMITS
from .research_schema import ID, TEXT, HASH, METRIC, obj, array, nullable, _check

DATE = {"type": "string", "format": "date-time", "minLength": 20, "maxLength": 20,
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"}
ORIGIN = obj(contributor={"enum": ["human", "ai", "mixed", "unknown"]}, detail=nullable(TEXT))
POINTER = {"type": "string", "minLength": 0, "maxLength": 2048, "x-utf8-maxBytes": 2048}
MAPPING = obj(target=POINTER, source=POINTER, transformation=nullable(TEXT))
BODIES = {
    "thesis": obj(statement=TEXT),
    "claim": obj(role={"enum": ["main", "subclaim"]}, statement=TEXT, scope=TEXT,
                 parent_ids=array(ID, 3, 1, True), status={"enum": ["proposed", "supported", "contested"]},
                 basis_ids=array(ID, 1024, unique=True)),
    "experiment": obj(question=TEXT, method=TEXT, conditions=TEXT, metric=METRIC, source_ref=TEXT),
    "observation": obj(experiment_id=ID, statement=TEXT, value=nullable(TEXT),
                       status={"enum": ["confirmed", "corrected", "invalidated", "retracted"]}),
    "scientific-edge": obj(edge_type={"enum": list(SCIENTIFIC_EDGE_TYPES)},
                           source_id=ID, target_id=ID, rationale=TEXT),
    "experiment-plan": obj(claim_id=ID, objective=TEXT, status={"const": "planned"}, conditions=TEXT, metric=METRIC),
    "historical-decision": obj(group_id=nullable(ID), rationale=nullable(TEXT), record_ids=array(ID, 1024, unique=True)),
}
SOURCE = obj(sha256=HASH, bytes={"type": "integer", "minimum": 0, "maximum": HISTORY_BYTES},
             chunks=array({"type": "string", "minLength": 1, "maxLength": 16384}, 342))


class _Diagnostics(list):
    """Keep a bounded diagnostic sample while counting every detected error."""
    def __init__(self):
        super().__init__()
        self.count = 0

    def append(self, value):
        self.count += 1
        if self.count <= 512:
            super().append(value)

    def __len__(self):
        return self.count

    def fields(self):
        return dict(errors=self[:512], error_count=self.count, diagnostics_truncated=self.count > 512)


def import_schema():
    records = {"oneOf": [obj(id=ID, kind={"const": kind}, body=body, source_pointer=POINTER,
                origin=ORIGIN, recorded_at=nullable(DATE), mappings=array(MAPPING, 128, 1))
                for kind, body in BODIES.items()]}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:claimbranch:argument-import:v1", **obj(
                schema={"const": "claimbranch.argument-import/v1"}, profile={"const": "paper"},
                project_id=ID, title=TEXT, source=SOURCE, records=array(records, 2048, 1),
                selected_ids=array(ID, 2048, 1, True))}


def imported_seed_schema():
    from .research_schema import LIFECYCLE_SEED
    result = deepcopy(LIFECYCLE_SEED)
    result['properties']['schema_version'] = {'const': 5}
    result['properties']['initial_argument'] = obj(source_sha256=HASH, envelope_sha256=HASH,
        preview_digest=HASH, registered_at=nullable(DATE),
        records=import_schema()['properties']['records'],
        unresolved_source_pointers=array(array(POINTER, 128), 64))
    result['required'].append('initial_argument')
    return result


def imported_reference_schema(version=1):
    result=obj(record_id=ID, source_sha256=HASH, contributor={'enum':['human','ai','mixed','unknown']},
               unresolved_count={'type':'integer','minimum':0,'maximum':8192})
    if version == 1:return result
    if version != 2:raise ContractError('Unsupported imported source reference version')
    result['properties'].update(schema={'const':'claimbranch.imported-source-reference/v2'},
        source_digest_scope={'const':'argument-envelope/v2'},
        origin_flags=obj(human={'enum':[False,True]},ai={'enum':[False,True]},unknown={'enum':[False,True]}))
    result['properties']['unresolved_count']['maximum']=65536
    result['required']=list(result['properties']);return result


def reference_origins(reference):
    """Retained contribution labels and uncertainty, with unchanged v1 meaning."""
    labels={reference['contributor']}
    labels.update(key for key in ('human','ai','unknown') if reference.get('origin_flags',{}).get(key))
    return labels


def source_references(state, branch, changes, source_node_id):
    """Exact imported context/ancestry, independent of the new human's authorship."""
    subjects = {state['seed']['claim_id'], state['seed']['anchor_id'], *state.get('experiments', {})}
    subjects.update(state.get('manuscript_anchors', {}))
    subjects.update(event['target_id'] for event in state['events'])
    subjects.update(key for key, item in branch['changes'].items() if item['kind'] in ('claim','interpretation','experiment-plan'))
    if source_node_id not in subjects:
        raise ContractError('imported reasoning needs an existing source subject')
    initial = state['seed']['initial_argument']
    records = {record['id']:record for record in initial['records']}
    pointers = sum(initial['unresolved_source_pointers'], [])
    replacement_pointers={link['source_pointer'] for link in state.get('observation_replacements',{}).values() if link.get('origin_kind')=='imported-declaration'}
    lineage = branch.get('source_lineages', {})
    found, pending, seen = {}, [source_node_id], set()
    for item in changes:
        pending.append(item['id'])
        body = item['body']
        pending.extend(body.get('parent_ids', [])); pending.extend(body.get('observation_ids', []))
        pending.extend(body.get('basis_ids', []))
        pending.extend(body[name] for name in ('claim_id','source_id','target_id') if name in body)
    while pending:
        key = pending.pop()
        if key in seen: continue
        seen.add(key)
        for ref in lineage.get(key, []): found[ref['record_id']] = ref
        if key in records:
            record = records[key]; pointer = record['source_pointer']
            found[key] = dict(record_id=key, source_sha256=initial['source_sha256'], contributor=record['origin']['contributor'],
                unresolved_count=sum((not pointer or p == pointer or p.startswith(pointer + '/')) and p not in replacement_pointers for p in pointers))
            if state['seed']['schema_version'] in (14,18):
                found[key].update(schema='claimbranch.imported-source-reference/v2',source_digest_scope='argument-envelope/v2',origin_flags=deepcopy(record['origin_flags']))
            original = record['body']
            pending.extend(original.get('parent_ids', [])); pending.extend(original.get('basis_ids', []))
            pending.extend(original[name] for name in ('claim_id','source_id','target_id','experiment_id') if name in original)
        for dependency in state.get('companion_dependencies',{}).values():
            if dependency['status']=='active' and dependency['target_id']==key:
                pending.append(dependency['companion_id'])
                for ref in dependency['source_refs']:found[ref['record_id']]=ref
        for link in state.get('observation_replacements',{}).values():
            if key in (link['previous_id'],link['replacement_id']):
                pending.extend((link['previous_id'],link['replacement_id']))
                for ref in link.get('source_refs',[]):found[ref['record_id']]=ref
                if link.get('origin_kind')=='imported-declaration':
                    from .observation_lineage import imported_reference
                    found[link['id']]=imported_reference(state,link)
        policy=state.get('wording_policies',{}).get(key)
        if policy:
            for ref in policy['source_refs']:found[ref['record_id']]=ref
        anchor=state.get('manuscript_anchors',{}).get(key)
        if anchor:
            pending.extend(anchor['expresses']);pending.extend(anchor['plots']);pending.extend(anchor['parents'])
        old = branch['changes'].get(key)
        if old:
            body = old['body']
            pending.extend(body.get('parent_ids', [])); pending.extend(body.get('observation_ids', []))
            pending.extend(body.get('basis_ids', []))
            pending.extend(body[name] for name in ('claim_id','source_id','target_id') if name in body)
    return [found[key] for key in sorted(found)]


def history_from_import(raw, *, anchor_id, registered_at=None):
    _check(anchor_id, ID)
    _check(registered_at, nullable(DATE))
    if type(raw) is not bytes or len(raw) > 16777216:
        raise ContractError('bounded exact import bytes required')
    return _history_from_import(raw, anchor_id, registered_at)


@lru_cache(maxsize=2)
def _history_from_import(raw, anchor_id, registered_at):
    from .research_history import ResearchHistory
    result = preview_import(raw)
    if not result['valid']:
        raise ContractError('invalid selected argument: registration refused before any append')
    if result['schema'] in ('claimbranch.argument-import-preview/v2','claimbranch.argument-import-preview/v3','claimbranch.argument-import-preview/v4','claimbranch.argument-import-preview/v5'):
        from .argument_import_v2 import make_history
        return make_history(raw, anchor_id, registered_at)
    thesis = next(item for item in result['records'] if item['kind'] == 'thesis')
    seed = dict(schema_version=5, profile='paper', project_id=result['project_id'],
        paper_title=result['title'], claim_id=thesis['id'], claim_statement=thesis['body']['statement'],
        anchor_id=anchor_id, initial_argument=dict(source_sha256=result['source_sha256'],
            envelope_sha256=result['envelope_sha256'], preview_digest=result['preview_digest'],
            registered_at=registered_at, records=result['records'],
            unresolved_source_pointers=result['unresolved_source_pointers']))
    return ResearchHistory(encode(seed, purpose='history'))


def initialize_imported_state(state):
    """Initialize a source-claimed current graph; no prior command/judgment is created."""
    seed = state['seed']; initial = seed['initial_argument']; records = initial['records']
    if seed['schema_version'] in (14,18):
        from .argument_import_v2 import validate_initial
        state['condition_vocabulary']={item['key']:item for item in validate_initial(seed)}
    by_id = {record['id']: record for record in records}
    if len(by_id) != len(records) or seed['anchor_id'] in by_id:
        raise ContractError('import identities collide with each other or the manuscript anchor')
    theses = [record for record in records if record['kind'] == 'thesis']
    if len(theses) != 1 or theses[0]['id'] != seed['claim_id'] or theses[0]['body']['statement'] != seed['claim_statement']:
        raise ContractError('imported thesis does not match the seed')
    used = set(by_id) | {seed['anchor_id'], state['branches']['main']['head']}
    def internal_id(prefix, key):
        counter = 0
        while True:
            token = prefix + hashlib.sha256((key + ':' + str(counter)).encode()).hexdigest()[:32]
            if token not in used:
                used.add(token); return token
            counter += 1
    changes = state['branches']['main']['changes']
    for record in records:
        key, kind, body = record['id'], record['kind'], deepcopy(record['body'])
        if kind == 'experiment':
            state['experiments'][key] = {'id': key, **body, **({k:deepcopy(record[k]) for k in ('display_label','external_id','recorded_at','not_recorded')} if seed['schema_version']==18 else {})}
        elif kind == 'observation':
            if by_id.get(body['experiment_id'], {}).get('kind') != 'experiment':
                raise ContractError('imported observation requires its completed experiment')
            state['events'].append(dict(event_id=internal_id('import-event-', key), target_id=key,
                run_id=body['experiment_id'], action='import', imported_status=body['status'],
                statement=body['statement'], value=body.get('value'), rationale=None, supersedes_id=None,
                **({'measurement':body['measurement']} if 'measurement' in body else {})))
        elif kind == 'claim':
            status, basis = body.pop('status'), body.pop('basis_ids')
            changes[key] = dict(id=key, kind='claim', body=body)
            if status != 'proposed':
                status_id = internal_id('import-status-', key)
                changes[status_id] = dict(id=status_id, kind='claim-status', body=dict(claim_id=key, status=status, basis_ids=basis))
        elif kind in ('scientific-edge', 'experiment-plan'):
            changes[key] = dict(id=key, kind=kind, body=body)
        elif kind == 'historical-decision':
            if any(by_id.get(ref, {}).get('kind') not in ('thesis', 'claim', 'experiment', 'observation', 'scientific-edge', 'experiment-plan') for ref in body['record_ids']):
                raise ContractError('historical decision has an unavailable scientific reference')
    from .research_history import _paper_changes, _capacity
    _paper_changes(state['branches']['main'], state)
    for resource, count in (('events', len(state['events'])), ('observations', len(state['events'])),
                            ('experiments', len(state['experiments']))):
        _capacity(state, resource, count)
    if sum(record['kind'] == 'historical-decision' for record in records) > 256:
        raise ContractError('capacity historical-decisions: exceeds 256')
    if seed['schema_version']==18:
        from .observation_lineage import initialize
        initialize(state)
    state['branches']['main']['watermark'] = len(state['events'])


def _escape(key):
    return str(key).replace("~", "~0").replace("/", "~1")


def _leaves(value, path="", depth=0):
    if depth > 16:
        raise ContractError("source JSON nesting exceeds 16")
    if len(path.encode('utf-8')) > 2048:
        raise ContractError('source pointer exceeds 2048 UTF-8 bytes')
    if type(value) in (dict, list):
        if len(value) > 2048:
            raise ContractError("source JSON collection exceeds 2048")
        if not value:
            yield path, value
        items = value.items() if type(value) is dict else enumerate(value)
        for key, child in items:
            yield from _leaves(child, path + "/" + _escape(unicodedata.normalize('NFC', key) if type(key) is str else key), depth + 1)
    else:
        yield path, value


def _at(value, pointer):
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ContractError("JSON pointer must be empty or begin with /")
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ContractError("invalid JSON pointer escape")
        key = token.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if not key.isascii() or not key.isdecimal() or str(int(key)) != key or int(key) >= len(value):
                raise ContractError("JSON pointer has no array item")
            value = value[int(key)]
        elif type(value) is dict:
            candidates = [candidate for candidate in value if unicodedata.normalize('NFC', candidate) == key]
            if len(candidates) != 1:
                raise ContractError("JSON pointer has no source value")
            value = value[candidates[0]]
        else:
            raise ContractError("JSON pointer has no source value")
    return value


def _original(raw):
    """Raw originals may contain numeric tables; no numbers enter mapped science implicitly."""
    def pairs(items):
        result, seen = {}, set()
        for key, value in items:
            normalized = unicodedata.normalize("NFC", key)
            if normalized in seen:
                raise ContractError("duplicate or NFC-colliding source JSON keys")
            seen.add(normalized)
            result[key] = value
        return result
    def reject(_):
        raise ContractError("nonfinite source JSON number")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_float=Decimal, parse_constant=reject)
        leaves, pointer_bytes = [], 0
        for pointer, child in _leaves(value):
            if len(leaves) >= 8192:
                raise ContractError("source leaf-pointer limit exceeds 8192")
            pointer_bytes += len(pointer.encode('utf-8'))
            if pointer_bytes > 1048576:
                raise ContractError('source pointer inventory exceeds 1 MiB')
            if type(child) is str: child.encode('utf-8')
            leaves.append((pointer, child))
        return value, leaves
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ContractError("invalid bounded original JSON: " + str(error)) from error


def _errors(value, schema, path, output):
    """Collect field failures across records without treating any failed record as valid."""
    if "oneOf" in schema:
        try:
            _check(value, schema)
            return
        except ContractError:
            pass
        options = schema['oneOf']
        # Diagnose the declared closed variant; never admit a failed union.
        selected = []
        if type(value) is dict:
            for discriminator in ('kind', 'type','operation_type','schema'):
                selected = [option for option in options
                    if discriminator in value and option.get('properties', {}).get(discriminator, {}).get('const') == value[discriminator]]
                if selected:
                    break
                allowed = [option.get('properties', {}).get(discriminator, {}).get('const') for option in options]
                if discriminator in value and all(item is not None for item in allowed):
                    output.append({'pointer':path+'/'+discriminator, 'error':'unknown variant; expected one of '+', '.join(map(str, allowed))})
                    return
            if not selected and ('measurement' in value) != ('value' in value):
                key = 'measurement' if 'measurement' in value else 'value'
                selected = [option for option in options if key in option.get('required', [])]
        else:
            primitive = {str:'string', int:'integer', type(None):'null', list:'array'}.get(type(value))
            selected = [option for option in options if primitive and option.get('type') == primitive]
        if len(selected)>1 and type(value) is dict:
            compatible=[option for option in selected if not set(value)-set(option.get('properties',{}))]
            if len(compatible)==1:selected=compatible
        if len(selected) == 1:
            _errors(value, selected[0], path, output)
        elif type(value) is dict and {key for option in options for key in option.get('required', [])} >= {'measurement', 'value'}:
            for key in ('measurement', 'value'):
                output.append({'pointer':path+'/'+key, 'error':'choose exactly one observation representation: measurement or value'})
        else:
            output.append({"pointer": path, "error": "value does not match exactly one closed schema"})
        return
    kind = schema.get("type")
    if kind == "object" and type(value) is dict:
        fields = schema["properties"]
        for key in sorted(set(value) - set(fields)):
            output.append({"pointer": path + "/" + _escape(key), "error": "unknown field"})
        for key, child in fields.items():
            pointer = path + "/" + _escape(key)
            if key not in value:
                if key in schema.get("required", []):
                    output.append({"pointer": pointer, "error": "missing field"})
            else:
                _errors(value[key], child, pointer, output)
    elif kind == "array" and type(value) is list:
        if not schema["minItems"] <= len(value) <= schema["maxItems"]:
            output.append({"pointer": path, "error": "collection outside finite bounds"})
        for index, child in enumerate(value):
            _errors(child, schema["items"], path + "/" + str(index), output)
        if schema.get("uniqueItems") and len({encode(item, purpose="project") for item in value}) != len(value):
            output.append({"pointer": path, "error": "duplicate collection item"})
    else:
        try:
            _check(value, schema)
        except ContractError as error:
            output.append({"pointer": path, "error": str(error)})


def preview_import(raw):
    """Complete selected graph/coverage preview; errors prohibit registration, not inspection."""
    value = decode(raw, purpose="project")
    if type(value) is dict and value.get('schema') in ('claimbranch.argument-import/v2','claimbranch.argument-import/v3','claimbranch.argument-import/v4','claimbranch.argument-import/v5'):
        from .argument_import_v2 import preview_import as preview_v2
        return preview_v2(raw)
    schema = import_schema()
    skeleton = deepcopy(schema)
    skeleton["properties"]["records"]["items"] = {}  # Report each closed record below.
    errors = _Diagnostics()
    _errors(value, skeleton, "", errors)
    if errors:
        return {"schema": "claimbranch.argument-import-preview/v1", "valid": False, **errors.fields(),
                "registration_available": False, "writes": False}
    original = source_bytes(value["source"])
    source, leaves = _original(original)
    leaf_set = {pointer for pointer, _ in leaves}
    records, by_id, indexes, coverage = value["records"], {}, {}, {}
    for index, record in enumerate(records):
        path = "/records/" + str(index)
        if type(record) is not dict or type(record.get('kind')) is not str or record['kind'] not in BODIES:
            errors.append({"pointer": path, "error": "unknown record kind or nonobject record"})
            continue
        record_schema = next(option for option in schema["properties"]["records"]["items"]["oneOf"]
                             if option["properties"]["kind"]["const"] == record["kind"])
        before = len(errors)
        _errors(record, record_schema, path, errors)
        if len(errors) != before:
            continue
        if record["id"] in by_id:
            errors.append({"pointer": path + "/id", "error": "duplicate record identity"})
            continue
        by_id[record["id"]], indexes[record["id"]] = record, path
        coverage[record['id']] = set()
        expected = dict(_leaves(record["body"]))
        targets = set()
        try:
            _at(source, record["source_pointer"])
        except ContractError as error:
            errors.append({"pointer": path + "/source_pointer", "error": str(error)})
        for number, mapping in enumerate(record["mappings"]):
            where = path + "/mappings/" + str(number)
            target, pointer = mapping["target"], mapping["source"]
            try:
                if target not in expected or target in targets:
                    raise ContractError("mapping must name each body leaf exactly once")
                targets.add(target)
                if record["source_pointer"] and not pointer.startswith(record["source_pointer"] + "/") and pointer != record["source_pointer"]:
                    raise ContractError("mapping leaves its declared source record")
                source_value = _at(source, pointer)
                if mapping["transformation"] is None and encode(source_value, purpose="project") != encode(expected[target], purpose="project"):
                    raise ContractError("changed value requires a declared transformation")
                # A summary of a container cannot certify all its unsupported children as mapped.
                if mapping['transformation'] is None and pointer in leaf_set:
                    coverage[record['id']].add(pointer)
            except ContractError as error:
                errors.append({"pointer": where, "source_pointer": pointer, "error": str(error)})
        for missing in sorted(set(expected) - targets):
            errors.append({"pointer": path + "/body" + missing, "error": "missing explicit source mapping"})

    selected, closure, included, counts, limits = graph_consistency(value["selected_ids"], by_id, indexes, errors)
    covered = set().union(*(coverage[key] for key in closure))
    unresolved = [key for key, _ in leaves if key not in covered]
    result = {"schema": "claimbranch.argument-import-preview/v1", "valid": not errors, **errors.fields(),
        "registration_available": False, "writes": False, "source_fidelity_verified": False,
        "envelope_sha256": hashlib.sha256(raw).hexdigest(), "source_sha256": value["source"]["sha256"],
        "source_bytes": len(original), "project_id": value["project_id"], "title": value["title"],
        "selected": sorted(selected), "required": sorted(closure - selected), "omitted": sorted(set(by_id) - closure),
        "counts": {kind: {"used": count, "limit": limits[kind]} for kind, count in counts.items()},
        "records": included, "source": value['source'],
        "unresolved_source_pointers": [unresolved[i:i+128] for i in range(0, len(unresolved), 128)],
        "unresolved_source_leaf_count": len(unresolved),
        "source_leaf_count": len(leaves), "mapped_source_leaf_count": len(covered),
        "boundary": "Read-only mapping preview. Historical dates/origins are unverified source claims; no science or prior app approvals created."}
    # The exact input hash binds every source byte/mapping; do not duplicate a
    # near-limit envelope into another saved-project-sized hash input.
    commitment = {key: result[key] for key in ('schema', 'envelope_sha256', 'source_sha256',
                  'selected', 'required', 'omitted', 'counts', 'valid', 'error_count')}
    result["preview_digest"] = hashlib.sha256(encode(commitment, purpose="project")).hexdigest()
    return result


def graph_consistency(selected_ids, by_id, indexes, errors):
    """Shared graph semantics; no source extraction, normalization or retention."""
    selected = set(selected_ids)
    for key in sorted(selected - set(by_id)):
        errors.append({"pointer": "/selected_ids", "record_id": key, "error": "selected record absent or malformed"})
    closure, pending = set(), sorted(selected & set(by_id))
    def dependencies(record):
        body, kind = record["body"], record["kind"]
        if kind == "claim": return body["parent_ids"] + body["basis_ids"]
        if kind == "observation": return [body["experiment_id"]]
        if kind == "scientific-edge": return [body["source_id"], body["target_id"]]
        if kind == "experiment-plan": return [body["claim_id"]]
        if kind == 'historical-decision': return body['record_ids']
        return []
    while pending:
        key = pending.pop()
        if key in closure: continue
        closure.add(key)
        for dependency in dependencies(by_id[key]):
            if dependency not in by_id:
                errors.append({"pointer": indexes[key] + "/body", "record_id": key,
                               "error": "missing dependency: " + dependency})
            elif dependency not in closure:
                pending.append(dependency)
    included = [by_id[key] for key in sorted(closure)]
    claims = {item["id"] for item in included if item["kind"] in ("thesis", "claim")}
    theses = {item["id"] for item in included if item["kind"] == "thesis"}
    if len(theses) != 1:
        errors.append({"pointer": "/selected_ids", "error": "selected closure needs exactly one thesis"})
    structural, scientific = {}, {}
    for item in included:
        key, body, kind = item["id"], item["body"], item["kind"]
        where = indexes[key] + "/body"
        if kind == "claim":
            parents = set(body["parent_ids"])
            if not parents <= claims or key in parents or (body["role"] == "main" and parents != theses) or (body["role"] == "subclaim" and parents & theses):
                errors.append({"pointer": where + "/parent_ids", "error": "invalid structural parents for claim role"})
            structural[key] = parents
            if body["status"] != "proposed" and not body["basis_ids"]:
                errors.append({"pointer": where + "/basis_ids", "error": "nonproposed claim requires explicit scientific basis"})
            for basis in body["basis_ids"]:
                other = by_id.get(basis, {})
                if other.get("kind") != "scientific-edge" or other["body"]["target_id"] != key:
                    errors.append({"pointer": where + "/basis_ids", "error": "invalid claim-status basis: " + basis})
                elif by_id.get(other['body']['source_id'], {}).get('kind') == 'observation' and by_id[other['body']['source_id']]['body']['status'] in ('invalidated', 'retracted'):
                    errors.append({'pointer': where + '/basis_ids', 'error': 'inactive observation cannot supply a claim-status basis: ' + basis})
            required_type = {'supported': 'supports', 'contested': 'challenges'}.get(body['status'])
            # Existing paper semantics admit claim-to-claim reasoning. A status
            # mapping is a declared historical judgment, not a proof that its
            # source claim is true or that observational evidence exists.
            if required_type and not any(by_id.get(basis, {}).get('kind') == 'scientific-edge' and by_id[basis]['body']['edge_type'] == required_type and by_id[basis]['body']['target_id'] == key for basis in body['basis_ids']):
                errors.append({'pointer': where + '/basis_ids', 'error': body['status'] + ' requires an explicit ' + required_type + ' basis edge'})
        elif kind == "scientific-edge":
            start, end = body["source_id"], body["target_id"]
            if end not in claims or by_id.get(start, {}).get("kind") not in ("thesis", "claim", "observation") or start == end:
                errors.append({"pointer": where, "error": "invalid scientific endpoints"})
            if start in claims: scientific.setdefault(start, set()).add(end)
        elif kind == "observation" and by_id.get(body["experiment_id"], {}).get("kind") != "experiment":
            errors.append({"pointer": where + "/experiment_id", "error": "observation requires an experiment record, not inventory ID"})
        elif kind == 'observation' and body['status'] in ('confirmed', 'corrected') and body.get('value') is None and 'measurement' not in body:
            errors.append({'pointer': where + '/value', 'error': 'mapped active observation needs its measured scalar value; retain source-only when typed tables are not yet supported'})
        elif kind == "experiment-plan" and body["claim_id"] not in claims:
            errors.append({"pointer": where + "/claim_id", "error": "plan requires a claim"})
        elif kind == 'historical-decision':
            for reference in body['record_ids']:
                if reference not in by_id or by_id[reference]['kind'] == 'historical-decision':
                    errors.append({'pointer': where + '/record_ids', 'error': 'unknown or nonscientific historical reference: ' + reference})
    from .research_history import _acyclic
    for label, graph in (("structural", structural), ("scientific", scientific)):
        # Count overflow is reported below; never recurse into an over-capacity graph.
        if len(claims) <= LIMITS['claims']:
            try: _acyclic(graph)
            except ContractError as error: errors.append({"pointer": "/records", "error": label + ": " + str(error)})
    counts = {kind: sum(item["kind"] == kind for item in included) for kind in BODIES}
    limits = {"thesis": 1, "claim": LIMITS["claims"] - 1, "experiment": LIMITS["experiments"],
              "observation": LIMITS["observations"], "scientific-edge": LIMITS["edges"],
              "experiment-plan": LIMITS["plans"], "historical-decision": 256}
    for kind, count in counts.items():
        if count > limits[kind]:
            errors.append({"pointer": "/records", "error": "capacity %s: %s / %s" % (kind, count, limits[kind])})
    return selected, closure, included, counts, limits
