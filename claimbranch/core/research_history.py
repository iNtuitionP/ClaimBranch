"""Immutable scientific-history candidates with global evidence and exact replay.

All transitions are pure calculations. No receipt, accepted-state persistence,
filesystem, provider, OS identity or wall clock exists in this module. A future
trusted gateway must authorize and persist them; replay does not confer trust.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from functools import lru_cache

from .canonical import ContractError, canonical_bytes, decode, digest, identifier
from .research_schema import SEED, PAPER_SEED, PAPER_SERIES_SEED, PAPER_LIMITS, PAPER_SERIES_LIMITS, JUDGMENT, ID, array, obj, command_schema, normalize, seed_schema, paper_payloads
from .paper_capacity import LIMITS as LIFECYCLE_LIMITS, HISTORY_BYTES, MANIFEST_BYTES, encode as paper_encode, decode as paper_decode, PaperChange, select_paper_changes


def _select(state, changes, selected, evidence):
    return (select_paper_changes if state["seed"]["schema_version"] in (4, 5) else select_changes)(changes, selected, evidence)


def _limits(state):
    return {**LIFECYCLE_LIMITS,"interpretations":128} if state.get("co_reports") else LIFECYCLE_LIMITS if state["seed"]["schema_version"] in (4, 5) else PAPER_SERIES_LIMITS


def _bytes(value, version):
    return paper_encode(value, purpose="manifest") if version in (4, 5) else canonical_bytes(value)


def _read(raw, version):
    return paper_decode(raw, purpose="manifest") if version in (4, 5) else decode(raw)


def _norm(value, schema, version):
    return normalize(value, schema, profile="paper" if version in (4, 5) else "episode")


def _hash(value, version):
    import hashlib
    return hashlib.sha256(_bytes(value, version)).hexdigest()


def _capacity(state, name, count):
    maximum = _limits(state)[name]
    if count > maximum:
        raise ContractError("capacity %s: %s / %s" % (name, count, maximum))


from .paper_changes import PaperChangesPreview, PaperDraftProjection, amendment_schema
from .review import (Change, Contribution, Judgment, ReviewContext, SealedReview, Selection,
                     acceptance_candidate, seal_review, select_changes, validate_explanation)


def _judgment(value, seed):
    judgment = Judgment(value["project_id"], value["episode_id"], value["text"], value["rationale"],
                        tuple(Contribution(**item) for item in value["history"]))
    if (judgment.project_id, judgment.episode_id) != (seed["project_id"], seed["episode_id"]):
        raise ContractError("judgment belongs to another context")
    return judgment


def _retain_history(previous, current):
    if previous is not None and current.history[:len(previous.history)] != previous.history:
        raise ContractError("human editing cannot erase contribution history")


def _episode_id(state):
    return state["active_episode"] if state["seed"]["schema_version"] >= 3 else state["seed"]["episode_id"]


def _context(state, episode_id=None):
    return {"project_id": state["seed"]["project_id"], "episode_id": episode_id or _episode_id(state)}


def _branch_judgments(branch, state):
    if state["seed"]["schema_version"] >= 3:
        return [deepcopy(branch["judgments"][key]) for key in state["episodes"] if key in branch["judgments"]]
    return [deepcopy(branch["judgment"])] if branch["judgment"] else []


def _branch_ai(branch, state):
    if any(record['origin'] in ('ai', 'mixed') for record in state.get('metadata_origins', {}).values()):
        return True
    return any(_judgment(value, _context(state, value["episode_id"])).ai_influenced
               for value in _branch_judgments(branch, state)) or any(
               ref['contributor'] in ('ai','mixed') for refs in branch.get('source_lineages', {}).values() for ref in refs) or any(value in ('ai','mixed') for values in branch.get('co_report_origins',{}).values() for value in values) or any(origin in ('ai','mixed') for origins in branch.get('protocol_origins',{}).values() for origin in origins) or any(origin in ('ai','mixed') for origins in branch.get('critique_origins',{}).values() for origin in origins)


def _branch_uncertain(branch):
    return any(ref['contributor'] == 'unknown' for refs in branch.get('source_lineages', {}).values() for ref in refs) or any('unknown' in values for values in branch.get('co_report_origins',{}).values()) or any('unknown' in origins for origins in branch.get('protocol_origins',{}).values()) or any('unknown' in origins for origins in branch.get('critique_origins',{}).values()) or branch.get('metadata_origin_uncertain',False)


def _episode_branches(state, episode_id=None):
    if episode_id is not None:
        identifier(episode_id)
    if state["seed"]["schema_version"] < 3:
        if episode_id is not None and episode_id != state["seed"]["episode_id"]:
            raise ContractError("unknown paper episode")
        return state["branches"], state["seed"]["episode_id"]
    episode_id = episode_id or state["active_episode"] or next(reversed(state["episodes"]), None)
    if episode_id is None:
        return state["branches"], None
    if episode_id not in state["episodes"]:
        raise ContractError("unknown paper episode")
    episode = state["episodes"][episode_id]
    return episode.get("branches", state["branches"]), episode_id


def _episode_info(episode):
    return {key: deepcopy(value) for key, value in episode.items() if key != "branches"}


def _validate_amendment_identity(state, original, item, episode_id):
    if any(item["id"] in decision["candidate_edge_ids"] for decision in state.get("co_reports",{}).values()):
        raise ContractError("co-reported relationships are immutable; use a new reading and relationship identity")
    old = original["changes"].get(item["id"])
    if (old and old["kind"] != item["kind"]) or (old is None and item["id"] in _record_ids(state)):
        raise ContractError("amendment cannot alias an existing identity or change its kind")
    if state["seed"]["schema_version"] >= 3 and item["kind"] == "interpretation":
        owner = state["interpretation_owners"].get(item["id"])
        if owner is not None and owner != episode_id:
            raise ContractError("a previous episode's interpretation cannot be rewritten")


def _amended_branch(state, original, amendments, episode_id, *, allow_empty=False):
    schema = paper_payloads(state["seed"]["schema_version"])["record-interpretation"]["properties"]["changes"]
    if allow_empty:
        schema['minItems'] = 0
    normalized = _norm(amendments, schema, state["seed"]["schema_version"])
    proposed = {item['id']: item for item in normalized}
    if len(proposed) != len(normalized):
        raise ContractError('select unique proposed amendments only')
    full = deepcopy(original)
    for key, item in proposed.items():
        _validate_amendment_identity(state, original, item, episode_id)
        if original['changes'].get(key) == item:
            raise ContractError('amendment does not change the current scientific record')
        full['changes'][key] = deepcopy(item)
    if state['seed']['schema_version'] >= 3:
        current = [item for item in full['changes'].values() if item['kind'] == 'interpretation'
                   and state['interpretation_owners'].get(item['id'], episode_id) == episode_id]
        if len(current) > 1:
            raise ContractError('one interpretation per paper episode is supported')
    return proposed, full


def _evidence(events):
    result = {}
    for event in events:
        key = event["target_id"]
        if key not in result:
            result[key] = {"id": key, "run_id": event["run_id"], "original_statement": event["statement"],
                           "statement": event["statement"], "history": []}
        row = result[key]
        row["history"].append(deepcopy(event))
        if "measurement" in event:
            row["measurement"] = deepcopy(event["measurement"])
            row["measurement_revision"] = event["event_id"]
            row["artifact_fidelity_verified"] = False
        row["status"] = event["imported_status"] if event["action"] == "import" else {"confirm": "confirmed", "correct": "corrected", "invalidate": "invalidated", "retract": "retracted"}[event["action"]]
        if event["statement"] is not None:
            row["statement"] = event["statement"]
        if "value" in event:
            if event["value"] is not None:
                row["value"] = event["value"]
    return [result[key] for key in sorted(result)]


def _append_evidence(state, event):
    events = state["events"]
    if state["seed"]["schema_version"] in (4, 5):
        _capacity(state, "events", len(events)+1)
        if event["action"] == "confirm":
            _capacity(state, "observations", len({old["target_id"] for old in events})+1)
    paper = state["seed"]["schema_version"] >= 2
    if len(events) >= (_limits(state)["events"] if paper else 6) or any(old["event_id"] == event["event_id"] for old in events):
        raise ContractError("evidence identity reused or episode event limit reached")
    previous = [old for old in events if old["target_id"] == event["target_id"]]
    if event["action"] == "correct" and any("measurement" in old for old in previous) and "measurement" not in event:
        raise ContractError("Structured observations require explicit cell correction or measurement transition")
    if event["target_id"] in (state["seed"]["claim_id"], state["seed"]["anchor_id"]):
        raise ContractError("evidence cannot alias a reasoning identity")
    if any(event["target_id"] in branch["changes"] for branch in state["branches"].values()):
        raise ContractError("evidence cannot alias a reasoning change")
    if not paper and events and event["run_id"] != events[0]["run_id"]:
        raise ContractError("F0 has one completed run")
    if paper:
        if event["run_id"] not in state["experiments"]:
            raise ContractError("observation requires a recorded experiment and metric")
        if event["event_id"] in _record_ids(state) or event["event_id"] == event["target_id"]:
            raise ContractError("evidence event identity cannot alias an existing record")
        if previous and previous[-1]["run_id"] != event["run_id"]:
            raise ContractError("correction cannot move an observation to another experiment")
        if (event["action"] in ("confirm", "correct")) != (event["value"] is not None):
            raise ContractError("only confirmation/correction carries a measured value")
    if event["action"] == "confirm":
        if previous or event["supersedes_id"] is not None or event["statement"] is None:
            raise ContractError("confirmation must introduce an original observation")
        if paper and event["target_id"] in _record_ids(state):
            raise ContractError("new observation aliases an existing record")
        if len({old["target_id"] for old in events}) >= (_limits(state)["observations"] if paper else 3):
            maximum = _limits(state)["observations"] if paper else 3
            raise ContractError("capacity observations: %s / %s" % (len({old["target_id"] for old in events})+1,maximum))
    else:
        if not previous or event["supersedes_id"] != previous[-1]["event_id"]:
            raise ContractError("event must name the latest event for this observation")
        if previous[-1]["action"] == "retract" or (previous[-1]["action"] == "import" and previous[-1]["imported_status"] == "retracted"):
            raise ContractError("retracted evidence cannot be revived by this contract")
        if (event["action"] == "correct") != (event["statement"] is not None):
            raise ContractError("only correction carries a replacement statement")
    events.append(deepcopy(event))


def _changes(branch, state):
    if state["seed"]["schema_version"] >= 2:
        return _paper_changes(branch, state)
    changes = branch["changes"]
    evidence = {item["id"] for item in _evidence(state["events"])}
    if set(changes) & (evidence | {state["seed"]["claim_id"], state["seed"]["anchor_id"]}):
        raise ContractError("reasoning IDs cannot alias evidence or base records")
    limits = {"claim-status": 1, "interpretation": 1, "scientific-edge": 6, "experiment-plan": 1}
    for kind, maximum in limits.items():
        if sum(item["kind"] == kind for item in changes.values()) > maximum:
            raise ContractError("reasoning cardinality exceeded")
    result = []
    for key, item in sorted(changes.items()):
        body, kind = item["body"], item["kind"]
        if kind == "interpretation":
            dependencies = tuple(body["observation_ids"])
            if not set(dependencies).issubset(evidence):
                raise ContractError("interpretation requires existing observations")
        elif kind == "scientific-edge":
            if body["target_id"] != state["seed"]["claim_id"]:
                raise ContractError("edge targets another claim")
            source = body["source_id"]
            if source not in evidence and changes.get(source, {}).get("kind") != "interpretation":
                raise ContractError("edge source must be an observation or interpretation")
            dependencies = (source,)
        else:
            if body["claim_id"] != state["seed"]["claim_id"]:
                raise ContractError("change targets another claim")
            dependencies = tuple(body.get("basis_ids", ()))
            if any(changes.get(key, {}).get("kind") not in ("interpretation", "scientific-edge") for key in dependencies):
                raise ContractError("claim status needs explicit scientific dependencies")
        result.append(Change(key, kind, dependencies))
    return tuple(result)


def _record_ids(state):
    ids = {state["seed"]["claim_id"], state["seed"]["anchor_id"]}
    ids.update(state.get("experiments", {}))
    ids.update(state.get("manuscript_anchors", {}))
    ids.update(state.get("companion_dependencies", {}))
    ids.update(state.get("co_reports", {}))
    ids.update(state.get("critiques",{}));ids.update(state.get("critique_links",{}))
    ids.update(c["source_id"] for c in state.get("critiques",{}).values())
    for name in ("protocols","experiment_associations","gate_amendments","gate_results","outcome_assessments"):ids.update(state.get(name,{}))
    for protocol in state.get("protocols",{}).values():ids.update(g["id"] for g in protocol["gates"])
    for decision in state.get("co_reports",{}).values():
        ids.update(decision["candidate_ids"]);ids.update(decision["candidate_edge_ids"])
    if state['seed']['schema_version'] == 5:
        ids.update(record['id'] for record in state['seed']['initial_argument']['records'])
    for event in state["events"]:
        ids.update((event["event_id"], event["target_id"]))
        if "measurement" in event: ids.add(event["measurement"]["id"])
    for branch in state["branches"].values():
        ids.update(branch["changes"])
    if state["seed"]["schema_version"] >= 3:
        ids.update(state["episodes"])
        ids.update(state["operation_ids"])
        for episode in state["episodes"].values():
            for branch in episode.get("branches", {}).values():
                ids.update(branch["changes"])
    return ids


def _acyclic(outgoing):
    """Bounded DAG validation; count depth without enumerating possible paths."""
    visiting, depths = set(), {}

    def visit(node):
        if node in visiting:
            raise ContractError("cyclic claim relationship")
        if node in depths:
            return depths[node]
        visiting.add(node)
        depth = 1 + max((visit(other) for other in sorted(outgoing.get(node, ()))), default=0)
        visiting.remove(node)
        if depth > PAPER_LIMITS["depth"]:
            raise ContractError("claim relationship depth exceeded")
        depths[node] = depth
        return depth

    for node in sorted(outgoing):
        visit(node)


def _paper_changes(branch, state):
    changes = branch["changes"]
    if state["seed"]["schema_version"] in (4, 5):
        _capacity(state, "changes", len(changes))
        for kind, resource in (("claim", "claims"), ("scientific-edge", "edges"), ("experiment-plan", "plans"), ("interpretation", "interpretations")):
            _capacity(state, resource, sum(x["kind"] == kind for x in changes.values()) + (kind == "claim"))
    root = state["seed"]["claim_id"]
    evidence = {item["id"] for item in _evidence(state["events"])}
    globals_ = {root, state["seed"]["anchor_id"], *state["experiments"], *evidence,
                *(event["event_id"] for event in state["events"])}
    if set(changes) & globals_ or len(changes) > _limits(state)["changes"]:
        raise ContractError("reasoning identity collision or change limit exceeded")
    limits = {"claim": _limits(state)["claims"] - 1, "claim-status": _limits(state)["claims"],
              "interpretation": _limits(state)["interpretations"] if state["seed"]["schema_version"] >= 3 else 1,
              "scientific-edge": _limits(state)["edges"], "experiment-plan": _limits(state)["plans"]}
    for kind, maximum in limits.items():
        if sum(item["kind"] == kind for item in changes.values()) > maximum:
            raise ContractError("paper reasoning cardinality exceeded")
    claims = {root, *(key for key, value in changes.items() if value["kind"] == "claim")}
    structural, scientific, statuses = {}, {}, set()
    result = []
    for key, item in sorted(changes.items()):
        body, kind = item["body"], item["kind"]
        if kind == "claim":
            parents = set(body["parent_ids"])
            if not parents.issubset(claims) or key in parents:
                raise ContractError("claim requires existing distinct parents")
            if (body["role"] == "main" and parents != {root}) or (body["role"] == "subclaim" and root in parents):
                raise ContractError("main and subclaim roles disagree with their structural parents")
            structural[key] = parents
            dependencies = parents - {root}
        elif kind == "interpretation":
            dependencies = set(body["observation_ids"])
            if not dependencies.issubset(evidence):
                raise ContractError("interpretation requires existing observations")
        elif kind == "scientific-edge":
            source, target = body["source_id"], body["target_id"]
            if target not in claims or (source not in evidence | claims and changes.get(source, {}).get("kind") != "interpretation"):
                raise ContractError("scientific relation has an unknown or invalid endpoint")
            if source == target:
                raise ContractError("self-support is invalid")
            if source in claims:
                scientific.setdefault(source, set()).add(target)
            dependencies = {source, target} - {root}
        else:
            target = body["claim_id"]
            if target not in claims:
                raise ContractError("unknown target claim")
            dependencies = ({target} - {root}) | set(body.get("basis_ids", ()))
            if kind == "claim-status":
                if target in statuses:
                    raise ContractError("conflicting status changes target one claim")
                statuses.add(target)
                for basis in body["basis_ids"]:
                    if changes.get(basis, {}).get("kind") not in ("interpretation", "scientific-edge"):
                        raise ContractError("claim status requires scientific basis")
                    if changes[basis]["kind"] == "scientific-edge" and changes[basis]["body"]["target_id"] != target:
                        raise ContractError("status basis targets a different claim")
        result.append((PaperChange if state["seed"]["schema_version"] in (4, 5) else Change)(key, kind, tuple(sorted(dependencies))))
    _acyclic(structural)
    _acyclic(scientific)
    return tuple(result)


@dataclass(frozen=True)
class MergePreview:
    selection: Selection
    payload: bytes
    digest: str


def _select_paper_amendments(state, original, full, proposed_ids, selected):
    evidence = _evidence(state["events"])
    active = tuple(item["id"] for item in evidence if item["status"] in ("confirmed", "corrected"))
    closure = _select(state, _paper_changes(full, state), tuple(selected), active)
    included = set(closure.closure) & set(proposed_ids)
    selected_branch = deepcopy(original)
    selected_branch["changes"].update({key: deepcopy(full["changes"][key]) for key in included})
    after_changes = _paper_changes(selected_branch, state)
    all_evidence = tuple(item["id"] for item in evidence)
    for item in selected_branch["changes"].values():
        if item["kind"] != "claim-status":
            continue
        basis = _select(state, after_changes, (item["id"],), all_evidence)
        if not set(basis.closure) & included:
            continue
        checked = _select(state, after_changes, tuple(sorted(included | {item["id"]})), active)
        if item["body"]["status"] == "contested" and not any(
                selected_branch["changes"][key]["kind"] == "scientific-edge"
                and selected_branch["changes"][key]["body"]["edge_type"] == "challenges"
                and selected_branch["changes"][key]["body"]["target_id"] == item["body"]["claim_id"]
                for key in checked.closure):
            raise ContractError("contested amendment requires an explicit challenge to the same claim")
    return selected_branch, closure, included


def _preview(state, selected):
    series = state["seed"]["schema_version"] >= 3
    merged = any(item.get("episode_id") == _episode_id(state) for item in state["merges"]) if series else bool(state["merges"])
    merged = merged or any(item["episode_id"]==_episode_id(state) for item in state.get("co_reports",{}).values())
    if "alternative" not in state["branches"] or merged or (series and not state["active_episode"]):
        raise ContractError("one existing non-nested branch and one selected merge are supported")
    paper = state["seed"]["schema_version"] >= 2
    if type(selected) not in (list, tuple) or not 1 <= len(selected) <= (_limits(state)["changes"] if paper else 9):
        raise ContractError("explicit nonempty selection required")
    source = state["branches"]["alternative"]
    evidence = tuple(item["id"] for item in _evidence(state["events"]) if item["status"] in ("confirmed", "corrected"))
    if series:
        target = state["branches"]["main"]
        proposed = {key for key, item in source["changes"].items() if target["changes"].get(key) != item}
        if not set(selected).issubset(proposed):
            raise ContractError("select changed records from the active episode only")
        _, selection, included = _select_paper_amendments(state, target, source, proposed, selected)
    else:
        selection = _select(state, _changes(source, state), tuple(selected), evidence)
    chosen = [source["changes"][key] for key in selection.closure]
    for item in chosen:
        if item["kind"] != "claim-status" or item["body"]["status"] != "contested" or (series and item["id"] not in included):
            continue
        if not any(edge["kind"] == "scientific-edge" and edge["body"]["edge_type"] == "challenges"
                   and (not paper or edge["body"]["target_id"] == item["body"]["claim_id"]) for edge in chosen):
            raise ContractError("contested claim requires a selected challenge edge")
    value = {"project_id": state["seed"]["project_id"], "episode_id": _episode_id(state),
             "base_head": source["base_head"], "heads": _heads(state), "evidence_watermark": len(state["events"]),
             "selection": asdict(selection), "changes": chosen,
             "source_judgment": source["judgment"], "impact_paths": _impact(state, selection, chosen)}
    if series:
        value.update(amendments={"selected": sorted(selected), "required": sorted(included - set(selected)),
                                "omitted": sorted(proposed - included),
                                "existing_references": sorted(set(selection.closure) - included)},
                     source_judgments=_branch_judgments(source, state), ai_influenced=_branch_ai(source, state))
    return MergePreview(selection, _bytes(value, state["seed"]["schema_version"]), _hash(value, state["seed"]["schema_version"]))


def _impact(state, selection, chosen):
    """Only typed scientific dependencies lead to the one manuscript anchor."""
    claim, anchor = state["seed"]["claim_id"], state["seed"]["anchor_id"]
    outgoing = {claim: {anchor}}
    for item in chosen:
        key, kind, body = item["id"], item["kind"], item["body"]
        if kind == "interpretation":
            for source in body["observation_ids"]:
                outgoing.setdefault(source, set()).add(key)
        elif kind == "scientific-edge":
            outgoing.setdefault(body["source_id"], set()).add(key)
            outgoing.setdefault(key, set()).add(body["target_id"])
        elif kind in ("claim-status", "experiment-plan"):
            outgoing.setdefault(key, set()).add(body["claim_id"])
            for basis in body.get("basis_ids", ()):
                outgoing.setdefault(basis, set()).add(key)
    paths = []

    if state["seed"]["schema_version"] >= 2:
        # One deterministic witness per start; avoid exponential path expansion.
        from collections import deque
        for start in sorted((*selection.closure, *selection.evidence_references)):
            queue, seen = deque([[start]]), {start}
            while queue:
                path = queue.popleft()
                if path[-1] == anchor:
                    paths.append(path)
                    break
                for target in sorted(outgoing.get(path[-1], ())):
                    if target not in seen:
                        seen.add(target)
                        queue.append([*path, target])
        return paths

    def visit(path):
        if path[-1] == anchor:
            paths.append(path)
            return
        for target in sorted(outgoing.get(path[-1], ())):
            if target not in path:
                visit([*path, target])

    for start in sorted((*selection.closure, *selection.evidence_references)):
        visit([start])
    return paths


def _heads(state):
    return {key: value["head"] for key, value in sorted(state["branches"].items())}



def _register_anchor(state, payload):
    import base64
    import hashlib
    from .research_schema import ANCHOR
    payload=normalize(payload,ANCHOR,profile='paper')
    anchor=payload['id']; current=state.setdefault('manuscript_anchors',{})
    if anchor not in current and anchor != state['seed']['anchor_id'] and anchor in _record_ids(state):
        raise ContractError('manuscript anchor aliases a scientific identity')
    if payload['source']['anchor_id'] != anchor:
        raise ContractError('anchor marker identity differs')
    if anchor in current and current[anchor]['kind'] != payload['kind']:
        raise ContractError('anchor kind is immutable; register a separate identity')
    try: pieces=[base64.b64decode(part,validate=True) for part in payload['block']]
    except ValueError: raise ContractError('invalid anchor block encoding') from None
    raw=b''.join(pieces)
    if len(raw)>65536 or [base64.b64encode(raw[i:i+8192]).decode() for i in range(0,len(raw),8192)]!=payload['block'] or hashlib.sha256(raw).hexdigest()!=payload['block_digest']:
        raise ContractError('anchor block bytes/digest differ')
    try: raw.decode('utf-8')
    except UnicodeError: raise ContractError('invalid anchor block UTF-8') from None
    main=state['branches']['main']
    claims={state['seed']['claim_id']} | {key for key,item in main['changes'].items() if item['kind']=='claim'}
    observations={e['target_id'] for e in state['events']}
    if not set(payload['expresses'])<=claims or not set(payload['plots'])<=observations:
        raise ContractError('anchor references unavailable main claims or observations')
    if payload['kind']=='text' and (payload['plots'] or payload['parents']):
        raise ContractError('text anchors express claims; only captions have parent figures/tables')
    if payload['parents'] and (payload['kind']!='caption' or any(parent not in current or current[parent]['kind'] not in ('figure','table') for parent in payload['parents'])):
        raise ContractError('caption parent must be a registered figure or table')
    if anchor in payload['parents']:
        raise ContractError('anchor cannot parent itself')
    if not payload['expresses'] and not payload['plots'] and not payload['parents']:
        # An explicit disconnected revision is valid; it never deletes history.
        pass
    candidate={**current,anchor:payload}
    count=1+len(set(candidate)-{state['seed']['anchor_id']})
    if count>64: raise ContractError(f'capacity anchors: {count} / 64')
    associations=sum(len(a['expresses'])+len(a['plots'])+len(a['parents']) for a in candidate.values())
    if associations>2048: raise ContractError(f'capacity anchor-associations: {associations} / 2048')
    current[anchor]=deepcopy(payload)


def _apply(state, cmd):
    if state['seed']['schema_version'] == 5 and cmd['operation_type'] in ('create-reasoning-branch', 'record-interpretation', 'apply-selected-merge'):
        raise ContractError('Imported-source reasoning origin propagation is not yet qualified for legacy operations; use the imported-source review path. No reasoning was changed.')
    series = state["seed"]["schema_version"] >= 3
    opening = series and cmd["operation_type"] == "open-episode"
    if cmd["project_id"] != state["seed"]["project_id"] or (not opening and cmd["episode_id"] != _episode_id(state)):
        raise ContractError("command belongs to another project or episode")
    if cmd["expected_heads"] != _heads(state) or cmd["evidence_watermark"] != len(state["events"]):
        raise ContractError("stale heads or evidence watermark")
    if state["time"] is not None and cmd["created_at"] < state["time"]:
        raise ContractError("operation clock moved backwards")
    state["time"] = cmd["created_at"]
    kind, payload = cmd["operation_type"], cmd["payload"]
    imported_operation = kind in ('create-imported-reasoning-branch','record-imported-interpretation','apply-imported-merge')
    if imported_operation:
        kind = {'create-imported-reasoning-branch':'create-reasoning-branch', 'record-imported-interpretation':'record-interpretation', 'apply-imported-merge':'apply-selected-merge'}[kind]
    paper = state["seed"]["schema_version"] >= 2
    if kind in ('record-critique','revise-critique-question','link-critique'):
        from .critiques import apply_critique
        apply_critique(state,cmd)
    elif kind in ('register-protocol','associate-experiment','amend-gate-rule','record-gate-result','record-outcome'):
        from .protocols import apply_protocol
        apply_protocol(state,cmd)
    elif kind in ('declare-condition','record-measurement'):
        from .typed_observations import apply_measurement
        apply_measurement(state,cmd)
    elif kind == 'record-co-report':
        from .co_report import apply_co_report
        apply_co_report(state,cmd)
    elif kind in ('set-claim-wording','set-claim-companion','set-anchor-context'):
        from .wording_policy import apply_revision
        apply_revision(state,cmd)
    elif kind == "register-manuscript-anchor":
        if state["seed"]["schema_version"] not in (4,5): raise ContractError("anchors require a personal paper profile")
        _register_anchor(state,payload)
    elif kind == "open-episode":
        if state["seed"]["schema_version"] in (4, 5):
            _capacity(state, "episodes", len(state["episodes"])+1)
        if (state["active_episode"] is not None or len(state["episodes"]) >= _limits(state)["episodes"]
                or cmd["episode_id"] in _record_ids(state) or cmd["episode_id"] == cmd["id"]):
            raise ContractError("one active episode, distinct identity and finite episode budget required")
        state["episodes"][cmd["episode_id"]] = {
            "id": cmd["episode_id"], **deepcopy(payload), "status": "active", "outcome": None,
            "baseline_heads": _heads(state), "baseline_watermark": len(state["events"]),
            "opened_at": cmd["created_at"], "open_operation_id": cmd["id"],
            "closed_at": None, "close_operation_id": None, "final_heads": None, "final_watermark": None}
        state["active_episode"] = cmd["episode_id"]
        state["branches"] = {"main": state["branches"]["main"]}
    elif kind == "close-episode":
        episode = state["episodes"][cmd["episode_id"]]
        merged = any(item["episode_id"] == cmd["episode_id"] for item in state["merges"]) or any(item["episode_id"]==cmd["episode_id"] for item in state.get("co_reports",{}).values())
        co_reported=any(item["episode_id"]==cmd["episode_id"] for item in state.get("co_reports",{}).values())
        episode.update(status="closed", outcome="co-reported" if co_reported else "merged" if merged else "unmerged",
                       closed_at=cmd["created_at"], close_operation_id=cmd["id"],
                       final_heads=_heads(state), final_watermark=len(state["events"]),
                       branches=deepcopy(state["branches"]))
        state["active_episode"] = None
    elif kind == "record-experiment":
        if state["seed"]["schema_version"] in (4, 5):
            _capacity(state, "experiments", len(state["experiments"])+1)
        if len(state["experiments"]) >= _limits(state)["experiments"] or payload["id"] in _record_ids(state):
            raise ContractError("experiment identity reused or finite limit exceeded")
        state["experiments"][payload["id"]] = deepcopy(payload)
    elif kind == "record-evidence-event":
        _append_evidence(state, payload)
    elif kind == "create-reasoning-branch":
        if any(d["episode_id"]==cmd["episode_id"] for d in state.get("co_reports",{}).values()):
            raise ContractError("This episode is already co-reported; open a next question before another alternative")
        if "alternative" in state["branches"] or (not paper and len(_evidence(state["events"])) != 3):
            raise ContractError("one alternative branch requires three original observations")
        source = deepcopy(state["branches"]["main"])
        source.update(base_head=source["head"], head=cmd["id"], watermark=len(state["events"]))
        if series:
            source["judgment"] = None
        state["branches"]["alternative"] = source
    elif kind == "record-interpretation":
        merged = any(item["episode_id"] == cmd["episode_id"] for item in state["merges"]) or any(item["episode_id"]==cmd["episode_id"] for item in state.get("co_reports",{}).values()) if series else bool(state["merges"])
        if "alternative" not in state["branches"] or merged:
            raise ContractError("reasoning requires the unmerged alternative branch")
        branch = state["branches"]["alternative"]
        judgment = _judgment(payload["judgment"], _context(state))
        previous = _judgment(branch["judgment"], _context(state)) if branch["judgment"] else None
        _retain_history(previous, judgment)
        if len({item["id"] for item in payload["changes"]}) != len(payload["changes"]):
            raise ContractError("duplicate changed identity")
        for item in payload["changes"]:
            if series:
                _validate_amendment_identity(state, branch, item, judgment.episode_id)
            old = branch["changes"].get(item["id"])
            if old and old["kind"] != item["kind"]:
                raise ContractError("reasoning identity cannot change kind")
            branch["changes"][item["id"]] = deepcopy(item)
            if series and item["kind"] == "interpretation":
                state["interpretation_owners"][item["id"]] = cmd["episode_id"]
        interpretations = [item for item in branch["changes"].values() if item["kind"] == "interpretation"]
        if series:
            interpretations = [item for item in interpretations if state["interpretation_owners"][item["id"]] == cmd["episode_id"]]
        if len(interpretations) != 1 or interpretations[0]["body"]["statement"] != judgment.text:
            raise ContractError("reasoning and judgment text must agree")
        active_evidence = tuple(item["id"] for item in _evidence(state["events"]) if item["status"] in ("confirmed", "corrected"))
        changes = _changes(branch, state)
        selected = tuple(item["id"] for item in payload["changes"]) if series else tuple(item.id for item in changes)
        _select(state, changes, selected, active_evidence)
        if imported_operation:
            from .argument_import import source_references
            expected = source_references(state, branch, payload['changes'], payload['source_node_id'])
            if payload['source_refs'] != expected:
                raise ContractError('imported source references changed or omitted')
            branch.setdefault('source_lineages', {})
            for item in payload['changes']:
                branch['source_lineages'][item['id']] = deepcopy(expected)
            branch['source_node_id'] = payload['source_node_id']
        branch.update(head=cmd["id"], watermark=len(state["events"]), judgment=deepcopy(payload["judgment"]))
        if series:
            branch["judgments"][cmd["episode_id"]] = deepcopy(payload["judgment"])
    elif kind == "apply-selected-merge":
        preview = _preview(state, payload["selected_ids"])
        source = state["branches"]["alternative"]
        if imported_operation:
            from .argument_import import source_references
            if payload['source_node_id'] != source.get('source_node_id'):
                raise ContractError('imported merge source subject changed')
            expected = source_references(state, source, [source['changes'][key] for key in preview.selection.closure], payload['source_node_id'])
            if payload['source_refs'] != expected:
                raise ContractError('imported merge lost source provenance')
        judgment = _judgment(payload["judgment"], _context(state))
        if source["judgment"] is None:
            raise ContractError("merge requires recorded reasoning")
        _retain_history(_judgment(source["judgment"], _context(state)), judgment)
        for key in preview.selection.closure:
            item = source["changes"][key]
            current = not series or state["interpretation_owners"].get(key) == cmd["episode_id"]
            if item["kind"] == "interpretation" and current and item["body"]["statement"] != judgment.text:
                raise ContractError("edited interpretation must be recorded before merging")
        validate_explanation(judgment, payload["disposition"], tuple(payload["answers"]),
                             inherited_ai=series and (_branch_ai(source, state) or _branch_uncertain(source)))
        target = state["branches"]["main"]
        target["changes"].update({key: deepcopy(source["changes"][key]) for key in preview.selection.closure})
        if imported_operation:
            target.setdefault('source_lineages', {}).update({key:deepcopy(source.get('source_lineages', {}).get(key, [])) for key in preview.selection.closure})
        target.update(head=cmd["id"], watermark=len(state["events"]), judgment=deepcopy(payload["judgment"]))
        state["merges"].append({"operation_id": cmd["id"], "preview": _read(preview.payload, state["seed"]["schema_version"]),
                                "judgment": deepcopy(payload["judgment"]),
                                "disposition": payload["disposition"], "answers": payload["answers"]})
        if series:
            target["judgments"][cmd["episode_id"]] = deepcopy(payload["judgment"])
            state["merges"][-1]["episode_id"] = cmd["episode_id"]
        if imported_operation:
            state['merges'][-1]['imported_sources'] = deepcopy(expected)


def _reduce_uncached(seed, commands):
    value = paper_decode(seed, purpose="history")
    if type(value) is not dict:
        raise ContractError("research seed must be an object")
    seed = _norm(value, seed_schema(value.get("schema_version")), value.get("schema_version"))
    paper = seed["schema_version"] >= 2
    if len(commands) > ((LIFECYCLE_LIMITS if seed["schema_version"] in (4, 5) else PAPER_LIMITS)["commands"] if paper else 32):
        raise ContractError("history operation limit exceeded")
    if len({seed["claim_id"], seed["anchor_id"]}) != 2:
        raise ContractError("base identities must be distinct")
    root = "root-" + (_hash(seed, 5) if seed["schema_version"] == 5 else digest(seed))
    state = {"seed": seed, "events": [], "merges": [], "time": None,
             "branches": {"main": {"head": root, "base_head": root, "watermark": 0, "changes": {}, "judgment": None}}}
    if paper:
        state["experiments"] = {}
    if seed["schema_version"] >= 3:
        state.update(active_episode=None, episodes={}, interpretation_owners={}, operation_ids={root})
        state["branches"]["main"]["judgments"] = {}
    if seed["schema_version"] == 5:
        from .argument_import import initialize_imported_state
        initialize_imported_state(state)
    seen = set()
    for position,raw in enumerate(commands):
        value = _read(raw, seed["schema_version"])
        command_version = value.get("schema_version")
        if command_version != seed["schema_version"] and not (command_version in (6,7,8,9,10,11,12) and seed["schema_version"] in (4,5)):
            raise ContractError("command version does not belong to this history")
        cmd = _norm(value, command_schema(command_version), seed["schema_version"])
        if _bytes(cmd, seed["schema_version"]) != raw:
            raise ContractError("history must use canonical command bytes")
        if cmd["id"] in seen or cmd["id"] == root or (seed["schema_version"] >= 3 and cmd["id"] in _record_ids(state)):
            raise ContractError("operation identity reused in history")
        seen.add(cmd["id"])
        if seed["schema_version"] >= 3:
            state["operation_ids"].add(cmd["id"])
            state.setdefault("operation_positions",{})[cmd["id"]]=position
        _apply(state, cmd)
        if command_version == 12:
            from .metadata_origin import retain_origin
            retain_origin(state,cmd)
    return state


@lru_cache(maxsize=2)
def _paper_reduce(seed, commands):
    return _reduce_uncached(seed, commands)


def _reduce(seed, commands):
    # Cached scientific calculations are immutable internal inputs, not authority.
    return _paper_reduce(seed, commands) if paper_decode(seed, purpose="history").get('schema_version') in (4, 5) else _reduce_uncached(seed, commands)


def _view(state, ref, episode_id=None):
    branches, episode_id = _episode_branches(state, episode_id)
    if type(ref) is not str or ref not in branches:
        raise ContractError("unknown reasoning ref")
    branch = branches[ref]
    claim = {"id": state["seed"]["claim_id"], "statement": state["seed"]["claim_statement"], "status": "supported"}
    items = [branch["changes"][key] for key in sorted(branch["changes"])]
    for item in items:
        if item["kind"] == "claim-status":
            claim["status"] = item["body"]["status"]
    result = {"ref": ref, "head": branch["head"], "claim": claim,
            "evidence_watermark": len(state["events"]), "reasoning_evidence_watermark": branch["watermark"],
            "evidence_changed_since_reasoning": len(state["events"]) != branch["watermark"],
            "evidence": _evidence(state["events"]), "changes": deepcopy(items),
            "interpretations": [deepcopy(item) for item in items if item["kind"] == "interpretation"],
            "experiment_plans": [deepcopy(item) for item in items if item["kind"] == "experiment-plan"],
            "judgment": deepcopy(branch["judgment"]), "authorization_verified": False}
    if state["seed"]["schema_version"] >= 2:
        claim["role"] = "thesis"
        claim["parent_ids"] = []
        claim["status"] = "proposed"
        claims = {claim["id"]: claim}
        for item in items:
            if item["kind"] == "claim":
                claims[item["id"]] = {"id": item["id"], **deepcopy(item["body"]), "status": "proposed"}
        for item in items:
            if item["kind"] == "claim-status":
                claims[item["body"]["claim_id"]]["status"] = item["body"]["status"]
        result.update(schema_version=state["seed"]["schema_version"], paper_title=state["seed"]["paper_title"],
                      claims=[claims[key] for key in sorted(claims)],
                      experiments=[deepcopy(state["experiments"][key]) for key in sorted(state["experiments"])])
    if state["seed"]["schema_version"] >= 3:
        result.update(episode_id=episode_id, episode=_episode_info(state["episodes"][episode_id]) if episode_id else None,
                      judgments=_branch_judgments(branch, state),
                      interpretation_episode_ids={item["id"]: state["interpretation_owners"][item["id"]] for item in result["interpretations"]})
    if state["seed"]["schema_version"] == 5:
        imported = deepcopy(state["seed"]["initial_argument"]["records"])
        originals = {record['id']: record for record in imported}
        unresolved = sum(state['seed']['initial_argument']['unresolved_source_pointers'], [])
        pointer_size_used = 0
        def source_mark(record):
            nonlocal pointer_size_used
            pointer = record['source_pointer']
            pointers = [p for p in unresolved if not pointer or p == pointer or p.startswith(pointer + '/')]
            pointer_size_used += sum(len(p.encode('utf-8')) + 4 for p in pointers)
            if pointer_size_used > MANIFEST_BYTES:
                raise ContractError('capacity import-source-view-bytes: %s / %s; narrow source record pointers' % (pointer_size_used, MANIFEST_BYTES))
            return dict(authority='imported-source-claim', contributor=record['origin']['contributor'],
                recorded_at=record['recorded_at'], source_pointer=pointer,
                unresolved_pointer_pages=[pointers[i:i+128] for i in range(0, len(pointers), 128)],
                unresolved_leaf_count=len(pointers))
        for row in result['claims'] + result['evidence'] + result['experiments']:
            record = originals.get(row['id'])
            if record: row['imported_source'] = source_mark(record)
        for item in result['changes']:
            key = item['body']['claim_id'] if item['kind'] == 'claim-status' else item['id']
            if key in originals: item['imported_source'] = source_mark(originals[key])
        result.update(imported_records=imported, historical_decisions=[r for r in imported if r["kind"] == "historical-decision"],
                      imported_dependencies=deepcopy(branch.get('source_lineages', {})),
                      import_source_digest=state["seed"]["initial_argument"]["source_sha256"],
                      unresolved_source_pointers=deepcopy(state["seed"]["initial_argument"]["unresolved_source_pointers"]))
    for name in ('wording_policies','companion_dependencies','anchor_contexts','co_reports','condition_vocabulary','protocols','experiment_associations','gate_amendments','gate_results','outcome_assessments','critiques','critique_links','metadata_origins'):
        if state.get(name): result[name]=deepcopy(state[name])
    if state.get('protocols'):
        from .protocols import plan_digest
        current_main=state['branches']['main']['changes']
        result['protocol_plan_digests']={p['plan_id']:plan_digest(current_main[p['plan_id']]) if p['plan_id'] in current_main else None for p in state['protocols'].values()}
    if state.get('manuscript_anchors'):
        result['manuscript_anchors'] = deepcopy(state['manuscript_anchors'])
    return result


def _manifest(state, commands):
    value = {"schema_version": state["seed"]["schema_version"], "authority": "unverified-candidate", "seed": state["seed"],
        "commands": [_read(raw, state["seed"]["schema_version"]) for raw in commands], "evidence_events": state["events"],
        "views": {ref: _view(state, ref) for ref in sorted(state["branches"])}, "selected_merges": state["merges"]}
    if state["seed"]["schema_version"] >= 3:
        value.update(active_episode_id=state["active_episode"], episodes=[_episode_info(item) for item in state["episodes"].values()])
    return _bytes(value, state["seed"]["schema_version"])


@lru_cache(maxsize=2)
def _paper_manifest(seed, commands):
    return _manifest(_reduce(seed, commands), commands)


@dataclass(frozen=True)
class ResearchHistory:
    seed: bytes
    commands: tuple[bytes, ...] = ()

    def __post_init__(self):
        if type(self.seed) is not bytes or type(self.commands) is not tuple:
            raise ContractError("bounded immutable history required")
        version = self.schema_version
        maximum = LIFECYCLE_LIMITS['commands'] if version in (4, 5) else PAPER_LIMITS['commands']
        if len(self.commands) > maximum:
            raise ContractError('capacity commands: %s / %s' % (len(self.commands), maximum))
        if any(type(raw) is not bytes for raw in self.commands):
            raise ContractError("bounded immutable command bytes required")
        used = sum(map(len, self.commands)) + len(self.seed)
        byte_limit = HISTORY_BYTES if version in (4, 5) else 262144
        if used > byte_limit:
            raise ContractError('capacity history-bytes: %s / %s' % (used, byte_limit))
        state = _reduce(self.seed, self.commands)
        if (paper_encode(state['seed'], purpose='history') if version == 5 else canonical_bytes(state['seed'])) != self.seed:
            raise ContractError('history seed is not canonical')
        self.manifest()

    @property
    def authorization_verified(self):
        return False

    @classmethod
    def start(cls, project_id, episode_id, claim_id, claim_statement, anchor_id):
        return cls(canonical_bytes(normalize({"schema_version": 1, "project_id": project_id,
            "episode_id": episode_id, "claim_id": claim_id, "claim_statement": claim_statement, "anchor_id": anchor_id}, SEED)))

    @classmethod
    def start_paper(cls, project_id, episode_id, paper_title, thesis_id, thesis_statement, anchor_id):
        return cls(canonical_bytes(normalize({"schema_version": 2, "project_id": project_id,
            "episode_id": episode_id, "paper_title": paper_title, "claim_id": thesis_id,
            "claim_statement": thesis_statement, "anchor_id": anchor_id}, PAPER_SEED)))

    @classmethod
    def start_paper_series(cls, project_id, paper_title, thesis_id, thesis_statement, anchor_id):
        return cls(canonical_bytes(normalize({"schema_version": 3, "project_id": project_id,
            "paper_title": paper_title, "claim_id": thesis_id, "claim_statement": thesis_statement,
            "anchor_id": anchor_id}, PAPER_SERIES_SEED)))

    @classmethod
    def start_lifecycle(cls, project_id, paper_title, thesis_id, thesis_statement, anchor_id):
        value = dict(schema_version=4, profile='paper', project_id=project_id,
                     paper_title=paper_title, claim_id=thesis_id,
                     claim_statement=thesis_statement, anchor_id=anchor_id)
        return cls(canonical_bytes(_norm(value, seed_schema(4), 4)))

    def capacity(self):
        state = _reduce(self.seed, self.commands)
        limits = _limits(state)
        branches = list(state['branches'].values())
        changes = {key: value for branch in branches for key, value in branch['changes'].items()}
        counts = dict(commands=len(self.commands), events=len(state['events']),
            observations=len({e['target_id'] for e in state['events']}),
            experiments=len(state.get('experiments', {})), claims=1+sum(x['kind']=='claim' for x in changes.values()),
            edges=sum(x['kind']=='scientific-edge' for x in changes.values()),
            plans=sum(x['kind']=='experiment-plan' for x in changes.values()), changes=len(changes),
            episodes=len(state.get('episodes', {})),
            interpretations=len(state.get('interpretation_owners', {})))
        for name in ('wording_policies','companion_dependencies','anchor_contexts','co_reports','condition_vocabulary','protocols','experiment_associations','gate_amendments','gate_results','outcome_assessments','critiques','critique_links','metadata_origins'):
            if state.get(name): counts[name]=len(state[name])
        if state.get('manuscript_anchors'):
            counts['anchors']=1+len(set(state['manuscript_anchors'])-{state['seed']['anchor_id']})
            counts['anchor-associations']=sum(len(a['expresses'])+len(a['plots'])+len(a['parents']) for a in state['manuscript_anchors'].values())
        counts['history-bytes'] = len(self.seed)+sum(map(len,self.commands))
        counts['manifest-bytes'] = len(self.manifest())
        if self.schema_version == 5:
            counts['historical-decisions'] = sum(record['kind'] == 'historical-decision' for record in state['seed']['initial_argument']['records'])
        maxima = {**limits, 'wording_policies':64,'companion_dependencies':256,'anchor_contexts':64,'co_reports':32,'condition_vocabulary':32,'protocols':128,'experiment_associations':128,'gate_amendments':256,'gate_results':512,'outcome_assessments':256,'critiques':128,'critique_links':512,'metadata_origins':2048, 'history-bytes': HISTORY_BYTES if self.schema_version in (4, 5) else 262144,
                  'manifest-bytes': MANIFEST_BYTES if self.schema_version in (4, 5) else 262144}
        maxima.update(anchors=64, **{'anchor-associations':2048})
        if self.schema_version == 5: maxima['historical-decisions'] = 256
        return {'profile': 'paper' if self.schema_version in (4, 5) else 'episode', 'schema_version': self.schema_version,
            'resources': {key: {'used': count, 'limit': maxima[key], 'remaining': maxima[key]-count}
                          for key,count in counts.items()}}

    def episodes(self):
        if self.schema_version < 3:
            raise ContractError("episode browsing requires the version-three paper profile")
        return [_episode_info(item) for item in _reduce(self.seed, self.commands)["episodes"].values()]

    @property
    def schema_version(self):
        value=paper_decode(self.seed, purpose="history")
        if type(value) is not dict or type(value.get("schema_version")) is not int:
            raise ContractError("research seed requires an explicit version")
        seed_schema(value["schema_version"])
        return value["schema_version"]

    @classmethod
    def replay(cls, seed, commands):
        return cls(seed, commands)

    @property
    def has_metadata_origins(self):
        return any(_read(raw,self.schema_version).get('schema_version')==12 for raw in self.commands)

    @property
    def has_critiques(self):
        return any(_read(raw,self.schema_version).get("operation_type") in ('record-critique','revise-critique-question','link-critique') for raw in self.commands)

    @property
    def has_protocols(self):
        return any(_read(raw,self.schema_version).get("operation_type") in ('register-protocol','associate-experiment','amend-gate-rule','record-gate-result','record-outcome') for raw in self.commands)

    @property
    def has_measurements(self):
        return any(_read(raw,self.schema_version).get("operation_type") in ('declare-condition','record-measurement') for raw in self.commands)

    @property
    def has_co_reports(self):
        return any(_read(raw,self.schema_version).get('operation_type') in ('record-co-report',) for raw in self.commands)

    @property
    def has_wording_policies(self):
        return any(_read(raw,self.schema_version).get('operation_type') in ('set-claim-wording','set-claim-companion','set-anchor-context') for raw in self.commands)

    @property
    def has_manuscript_anchors(self):
        return any(_read(raw,self.schema_version).get('operation_type') in ('register-manuscript-anchor',) for raw in self.commands)

    @property
    def heads(self):
        return tuple(sorted(_heads(_reduce(self.seed, self.commands)).items()))

    @property
    def watermark(self):
        return len(_reduce(self.seed, self.commands)["events"])

    def append(self, command):
        if self.schema_version in (4, 5) and type(command) is dict and type(command.get("payload")) is dict:
            changes=command["payload"].get("changes")
            if type(changes) is list and len(changes)>LIFECYCLE_LIMITS["changes"]:
                raise ContractError("capacity changes: %s / %s" % (len(changes),LIFECYCLE_LIMITS["changes"]))
        cmd = _norm(command, command_schema(command["schema_version"] if command.get("schema_version") in (6,7,8,9,10,11,12) and self.schema_version in (4,5) else self.schema_version), self.schema_version)
        raw = _bytes(cmd, self.schema_version)
        for previous in self.commands:
            if _read(previous, self.schema_version)["id"] == cmd["id"]:
                if previous != raw:
                    raise ContractError("changed retry cannot overwrite an operation")
                return self
        return replace(self, commands=(*self.commands, raw))

    def check_operation_identity(self, operation_id):
        """Check a fresh v3 candidate ID against all owned records and operations.

        This is only an identity check, not permission to append a new format.
        """
        identifier(operation_id)
        if self.schema_version < 3:
            raise ContractError('paper operation identity requires cumulative history')
        if operation_id in _record_ids(_reduce(self.seed, self.commands)):
            raise ContractError('operation identity reused in history')

    def view(self, ref, *, at_operation=None, episode_id=None):
        commands = self.commands
        if at_operation is not None:
            identifier(at_operation)
            positions = [i for i, raw in enumerate(commands) if _read(raw, self.schema_version)["id"] == at_operation]
            root = "root-" + digest(paper_decode(self.seed, purpose="history"))
            if not positions and at_operation != root:
                raise ContractError("unknown historical operation")
            commands = commands[:positions[0] + 1] if positions else ()
        return _view(_reduce(self.seed, commands), ref, episode_id)

    def merge_preview(self, selected):
        return _preview(_reduce(self.seed, self.commands), selected)

    def preview_merge_changes(self, selected):
        """Project the active v3 alternative's exact effect on main, without append.

        Keep this richer projection separate from the frozen command/manifest
        format. Its after-view is hypothetical; heads and evidence stay intact.
        """
        if self.schema_version < 3:
            raise ContractError("cumulative merge projection requires v3")
        selected = _norm(selected, array(ID, (LIFECYCLE_LIMITS if self.schema_version in (4, 5) else PAPER_LIMITS)["changes"], 1, True), self.schema_version)
        state = deepcopy(_reduce(self.seed, self.commands))
        preview = _preview(state, selected)
        source, target = state["branches"]["alternative"], state["branches"]["main"]
        if source["judgment"] is None:
            raise ContractError("merge requires recorded reasoning")
        before = _view(state, "main")
        merged = _read(preview.payload, self.schema_version)
        selection = {**merged["amendments"], "evidence_references": list(preview.selection.evidence_references)}
        selected_ids, required = set(selection["selected"]), set(selection["required"])
        amendments = [{"id": key, "kind": item["kind"], "before": deepcopy(target["changes"].get(key)),
                       "after": deepcopy(item), "disposition": "selected" if key in selected_ids else
                       "required" if key in required else "omitted"}
                      for key, item in sorted(source["changes"].items()) if target["changes"].get(key) != item]
        target["changes"].update({key: deepcopy(source["changes"][key]) for key in preview.selection.closure})
        if self.schema_version == 5:
            target.setdefault('source_lineages', {}).update({key:deepcopy(source.get('source_lineages', {}).get(key, [])) for key in preview.selection.closure})
        target["judgment"] = deepcopy(source["judgment"])
        target["judgments"][_episode_id(state)] = deepcopy(source["judgment"])
        value = {"schema_version": 1, "project_id": state["seed"]["project_id"], "episode_id": _episode_id(state),
                 "ref": "main", "source_ref": "alternative", "selection": selection, "amendments": amendments,
                 "before": before, "after": _view(state, "main"),
                 "source_judgment": deepcopy(source["judgment"]), "judgment": deepcopy(source["judgment"]),
                 "source_judgments": _branch_judgments(source, state), "ai_influenced": _branch_ai(source, state),
                 "authority": "unaccepted-preview", "authorization_verified": False}
        if self.schema_version == 5:
            from .argument_import import source_references
            refs = source_references(state, source, [source['changes'][key] for key in preview.selection.closure], source['source_node_id'])
            value.update(imported_sources=refs, source_node_id=source['source_node_id'],
                         origin_uncertain=any(ref['contributor']=='unknown' for ref in refs))
        return PaperChangesPreview(_bytes(value, self.schema_version), _hash(value, self.schema_version))

    def project_paper_draft(self, ref, amendments, *, episode_id=None):
        """Validate all authored candidates without inventing a complete judgment.

        This is a disposable graph projection, not a selected review or a command.
        Incomplete editor values must remain with their caller on validation error.
        """
        if self.schema_version not in (2, 3, 4, 5):
            raise ContractError('draft projection requires a paper history')
        state = deepcopy(_reduce(self.seed, self.commands))
        before = _view(state, ref, episode_id)
        branches, episode_id = _episode_branches(state, episode_id)
        if episode_id is None:
            raise ContractError('open a paper episode before drafting')
        original = branches[ref]
        proposed, full = _amended_branch(state, original, amendments, episode_id, allow_empty=True)
        if proposed:
            full, _, _ = _select_paper_amendments(state, original, full, proposed, sorted(proposed))
        branches[ref] = full
        if self.schema_version >= 3:
            state['interpretation_owners'].update({key: episode_id for key, item in proposed.items()
                                                  if item['kind'] == 'interpretation'})
        value = {'schema': 'claimbranch.paper-draft-projection/v1', 'project_id': state['seed']['project_id'],
                 'episode_id': episode_id, 'ref': ref, 'amendments': [proposed[key] for key in sorted(proposed)],
                 'after': _view(state, ref, episode_id), 'source_judgment': before['judgment'],
                 'source_ai_influenced': _branch_ai(original, state),
                 'authority': 'unaccepted-draft', 'authorization_verified': False}
        return PaperDraftProjection(_bytes(value, self.schema_version), _hash(value, self.schema_version))

    def preview_paper_changes(self, ref, amendments, selected, judgment, *, episode_id=None, source_node_id=None):
        """Validate a selected overlay using this history's versioned paper rules.

        This projection can inspect amendments after a previous candidate merge.
        It does not append a command, start an episode, rewrite a seed or supply
        a persistent/multi-episode transition. Both provenance chains survive.
        """
        if self.schema_version not in (2, 3, 4, 5) or not isinstance(judgment, Judgment):
            raise ContractError("paper amendments require a paper history and typed complete judgment")
        state = deepcopy(_reduce(self.seed, self.commands))
        before = _view(state, ref, episode_id)
        branches, episode_id = _episode_branches(state, episode_id)
        if episode_id is None:
            raise ContractError("open a paper episode before drafting")
        judgment = _judgment(normalize(asdict(judgment), JUDGMENT), _context(state, episode_id))
        request = _norm({"amendments": amendments, "selected_ids": selected},
                            obj(amendments=paper_payloads(self.schema_version)["record-interpretation"]["properties"]["changes"], selected_ids=array(ID, (LIFECYCLE_LIMITS if self.schema_version in (4, 5) else PAPER_LIMITS)["changes"], 1, True)), self.schema_version)
        proposed = {item["id"]: item for item in request["amendments"]}
        if len(proposed) != len(request["amendments"]) or not set(request["selected_ids"]).issubset(proposed):
            raise ContractError("select unique proposed amendments only")
        original = branches[ref]
        proposed, full = _amended_branch(state, original, request['amendments'], episode_id)
        for key, item in proposed.items():
            if item["kind"] == "interpretation" and item["body"]["statement"] != judgment.text:
                raise ContractError("interpretation amendment must use the reviewed draft text")
        # Closure runs over the entire prospective argument so changed
        # dependencies cannot be omitted by relabeling them as existing records.
        # A valid all-amendments graph does not imply a valid partial selection.
        selected_branch, closure, included = _select_paper_amendments(
            state, original, full, proposed, request["selected_ids"])
        if any(proposed[key]["kind"] == "interpretation" for key in included):
            selected_branch["judgment"] = asdict(judgment)
            if self.schema_version >= 3:
                selected_branch["judgments"][episode_id] = asdict(judgment)
        after_state = deepcopy(state)
        _episode_branches(after_state, episode_id)[0][ref] = selected_branch
        if self.schema_version >= 3:
            after_state["interpretation_owners"].update({key: episode_id for key in included if proposed[key]["kind"] == "interpretation"})
        source_judgment = original["judgment"]
        source_ai = _branch_ai(original, state)
        selected_ids = set(request["selected_ids"])
        imported_sources = []
        if self.schema_version == 5:
            from .argument_import import source_references
            source_node_id = source_node_id or state['seed']['claim_id']
            imported_sources = source_references(state, selected_branch, [proposed[key] for key in included], source_node_id)
            selected_branch.setdefault('source_lineages', {}).update({key:deepcopy(imported_sources) for key in included})
            _episode_branches(after_state, episode_id)[0][ref] = selected_branch
        value = {"schema_version": 1, "authority": "unaccepted-preview", "authorization_verified": False,
                 "project_id": state["seed"]["project_id"], "episode_id": episode_id, "ref": ref,
                 "selection": {"selected": sorted(selected_ids), "required": sorted(included - selected_ids),
                     "omitted": sorted(set(proposed) - included),
                     "existing_references": sorted(set(closure.closure) - included),
                     "evidence_references": list(closure.evidence_references)},
                 "amendments": [{"id": key, "kind": item["kind"],
                     "before": deepcopy(original["changes"].get(key)), "after": deepcopy(item),
                     "disposition": "selected" if key in selected_ids else "required" if key in included else "omitted"}
                     for key, item in sorted(proposed.items())],
                 "before": before, "after": _view(after_state, ref, episode_id),
                 "source_judgment": deepcopy(source_judgment), "judgment": asdict(judgment),
                 "ai_influenced": source_ai or judgment.ai_influenced}
        if self.schema_version == 5:
            value.update(imported_sources=imported_sources, source_node_id=source_node_id,
                origin_uncertain=any(r['contributor']=='unknown' for r in imported_sources))
            value['ai_influenced'] |= any(r['contributor'] in ('ai','mixed') for r in imported_sources)
        if self.schema_version >= 3:
            value["source_judgments"] = _branch_judgments(original, state)
        return PaperChangesPreview(_bytes(value, self.schema_version), _hash(value, self.schema_version))

    def prepare_merge_review(self, command, *, manuscript_digest, session_nonce, sealed_at, expires_at):
        if self.schema_version in (4, 5):
            raise ContractError("personal-paper history has no protected merge authority")
        cmd = _norm(command, command_schema(self.schema_version), self.schema_version)
        if cmd["operation_type"] != "apply-selected-merge":
            raise ContractError("merge command required")
        self.append(cmd)  # Revalidate the proposed transition without mutating history.
        preview = self.merge_preview(cmd["payload"]["selected_ids"])
        seed = paper_decode(self.seed, purpose="history")
        episode_context = {"project_id": seed["project_id"], "episode_id": cmd["episode_id"]}
        source_judgments = ()
        binding = {"command": cmd, "merge": decode(preview.payload), "history_digest": digest([_read(raw, self.schema_version) for raw in self.commands])}
        if self.schema_version >= 3:
            binding["seed_digest"] = digest(seed)
            binding["scientific_preview_digest"] = self.preview_merge_changes(cmd["payload"]["selected_ids"]).digest
            source_judgments = tuple(_judgment(value, {"project_id": seed["project_id"], "episode_id": value["episode_id"]})
                                    for value in decode(preview.payload)["source_judgments"])
        context = ReviewContext(seed["project_id"], cmd["episode_id"], cmd["id"], cmd["operation_type"], digest(binding),
            self.heads, self.watermark, seed["anchor_id"], manuscript_digest, session_nonce, sealed_at, expires_at,
            schema_version=self.schema_version, rule_version={1: "f0-review-v1", 2: "paper-review-v2", 3: "paper-review-v3"}[self.schema_version])
        return seal_review(_judgment(cmd["payload"]["judgment"], episode_context), context, preview.selection,
                           disposition=cmd["payload"]["disposition"], answers=tuple(cmd["payload"]["answers"]),
                           source_judgments=source_judgments)

    def append_reviewed_merge(self, command, review, *, manuscript_digest, now):
        if not isinstance(review, SealedReview):
            raise ContractError("sealed review required")
        current = self.prepare_merge_review(command, manuscript_digest=manuscript_digest,
            session_nonce=review.context.session_nonce, sealed_at=review.context.sealed_at, expires_at=review.context.expires_at)
        if review != current or not review.is_current(current.context, now=now):
            raise ContractError("merge review changed or expired")
        return self.append(command), acceptance_candidate(review, decision="accept")

    def manifest(self):
        return _paper_manifest(self.seed,self.commands) if self.schema_version in (4, 5) else _manifest(_reduce(self.seed,self.commands),self.commands)
