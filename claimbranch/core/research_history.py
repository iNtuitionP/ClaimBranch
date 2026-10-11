"""Immutable scientific-history candidates with global evidence and exact replay.

All transitions are pure calculations. No receipt, accepted-state persistence,
filesystem, provider, OS identity or wall clock exists in this module. A future
trusted gateway must authorize and persist them; replay does not confer trust.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace

from .canonical import ContractError, canonical_bytes, decode, digest, identifier
from .research_schema import SEED, PAPER_SEED, PAPER_SERIES_SEED, PAPER_LIMITS, PAPER_SERIES_LIMITS, JUDGMENT, ID, array, obj, command_schema, normalize, seed_schema
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
    return state["active_episode"] if state["seed"]["schema_version"] == 3 else state["seed"]["episode_id"]


def _context(state, episode_id=None):
    return {"project_id": state["seed"]["project_id"], "episode_id": episode_id or _episode_id(state)}


def _branch_judgments(branch, state):
    if state["seed"]["schema_version"] == 3:
        return [deepcopy(branch["judgments"][key]) for key in state["episodes"] if key in branch["judgments"]]
    return [deepcopy(branch["judgment"])] if branch["judgment"] else []


def _branch_ai(branch, state):
    return any(_judgment(value, _context(state, value["episode_id"])).ai_influenced
               for value in _branch_judgments(branch, state))


def _episode_branches(state, episode_id=None):
    if episode_id is not None:
        identifier(episode_id)
    if state["seed"]["schema_version"] != 3:
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
    old = original["changes"].get(item["id"])
    if (old and old["kind"] != item["kind"]) or (old is None and item["id"] in _record_ids(state)):
        raise ContractError("amendment cannot alias an existing identity or change its kind")
    if state["seed"]["schema_version"] == 3 and item["kind"] == "interpretation":
        owner = state["interpretation_owners"].get(item["id"])
        if owner is not None and owner != episode_id:
            raise ContractError("a previous episode's interpretation cannot be rewritten")


def _amended_branch(state, original, amendments, episode_id, *, allow_empty=False):
    schema = amendment_schema()
    if allow_empty:
        schema['minItems'] = 0
    normalized = normalize(amendments, schema)
    proposed = {item['id']: item for item in normalized}
    if len(proposed) != len(normalized):
        raise ContractError('select unique proposed amendments only')
    full = deepcopy(original)
    for key, item in proposed.items():
        _validate_amendment_identity(state, original, item, episode_id)
        if original['changes'].get(key) == item:
            raise ContractError('amendment does not change the current scientific record')
        full['changes'][key] = deepcopy(item)
    if state['seed']['schema_version'] == 3:
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
        row["status"] = {"confirm": "confirmed", "correct": "corrected", "invalidate": "invalidated", "retract": "retracted"}[event["action"]]
        if event["statement"] is not None:
            row["statement"] = event["statement"]
        if "value" in event:
            if event["value"] is not None:
                row["value"] = event["value"]
    return [result[key] for key in sorted(result)]


def _append_evidence(state, event):
    events = state["events"]
    paper = state["seed"]["schema_version"] >= 2
    if len(events) >= (PAPER_LIMITS["events"] if paper else 6) or any(old["event_id"] == event["event_id"] for old in events):
        raise ContractError("evidence identity reused or episode event limit reached")
    previous = [old for old in events if old["target_id"] == event["target_id"]]
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
        if len({old["target_id"] for old in events}) >= (PAPER_LIMITS["observations"] if paper else 3):
            raise ContractError("F0 has at most three observations")
    else:
        if not previous or event["supersedes_id"] != previous[-1]["event_id"]:
            raise ContractError("event must name the latest event for this observation")
        if previous[-1]["action"] == "retract":
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
    for event in state["events"]:
        ids.update((event["event_id"], event["target_id"]))
    for branch in state["branches"].values():
        ids.update(branch["changes"])
    if state["seed"]["schema_version"] == 3:
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
    root = state["seed"]["claim_id"]
    evidence = {item["id"] for item in _evidence(state["events"])}
    globals_ = {root, state["seed"]["anchor_id"], *state["experiments"], *evidence,
                *(event["event_id"] for event in state["events"])}
    if set(changes) & globals_ or len(changes) > PAPER_LIMITS["changes"]:
        raise ContractError("reasoning identity collision or change limit exceeded")
    limits = {"claim": PAPER_LIMITS["claims"] - 1, "claim-status": PAPER_LIMITS["claims"],
              "interpretation": PAPER_SERIES_LIMITS["interpretations"] if state["seed"]["schema_version"] == 3 else 1,
              "scientific-edge": PAPER_LIMITS["edges"], "experiment-plan": PAPER_LIMITS["plans"]}
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
        result.append(Change(key, kind, tuple(sorted(dependencies))))
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
    closure = select_changes(_paper_changes(full, state), tuple(selected), active)
    included = set(closure.closure) & set(proposed_ids)
    selected_branch = deepcopy(original)
    selected_branch["changes"].update({key: deepcopy(full["changes"][key]) for key in included})
    after_changes = _paper_changes(selected_branch, state)
    all_evidence = tuple(item["id"] for item in evidence)
    for item in selected_branch["changes"].values():
        if item["kind"] != "claim-status":
            continue
        basis = select_changes(after_changes, (item["id"],), all_evidence)
        if not set(basis.closure) & included:
            continue
        checked = select_changes(after_changes, tuple(sorted(included | {item["id"]})), active)
        if item["body"]["status"] == "contested" and not any(
                selected_branch["changes"][key]["kind"] == "scientific-edge"
                and selected_branch["changes"][key]["body"]["edge_type"] == "challenges"
                and selected_branch["changes"][key]["body"]["target_id"] == item["body"]["claim_id"]
                for key in checked.closure):
            raise ContractError("contested amendment requires an explicit challenge to the same claim")
    return selected_branch, closure, included


def _preview(state, selected):
    series = state["seed"]["schema_version"] == 3
    merged = any(item.get("episode_id") == _episode_id(state) for item in state["merges"]) if series else bool(state["merges"])
    if "alternative" not in state["branches"] or merged or (series and not state["active_episode"]):
        raise ContractError("one existing non-nested branch and one selected merge are supported")
    paper = state["seed"]["schema_version"] >= 2
    if type(selected) not in (list, tuple) or not 1 <= len(selected) <= (PAPER_LIMITS["changes"] if paper else 9):
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
        selection = select_changes(_changes(source, state), tuple(selected), evidence)
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
    return MergePreview(selection, canonical_bytes(value), digest(value))


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


def _apply(state, cmd):
    series = state["seed"]["schema_version"] == 3
    opening = series and cmd["operation_type"] == "open-episode"
    if cmd["project_id"] != state["seed"]["project_id"] or (not opening and cmd["episode_id"] != _episode_id(state)):
        raise ContractError("command belongs to another project or episode")
    if cmd["expected_heads"] != _heads(state) or cmd["evidence_watermark"] != len(state["events"]):
        raise ContractError("stale heads or evidence watermark")
    if state["time"] is not None and cmd["created_at"] < state["time"]:
        raise ContractError("operation clock moved backwards")
    state["time"] = cmd["created_at"]
    kind, payload = cmd["operation_type"], cmd["payload"]
    paper = state["seed"]["schema_version"] >= 2
    if kind == "open-episode":
        if (state["active_episode"] is not None or len(state["episodes"]) >= PAPER_SERIES_LIMITS["episodes"]
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
        merged = any(item["episode_id"] == cmd["episode_id"] for item in state["merges"])
        episode.update(status="closed", outcome="merged" if merged else "unmerged",
                       closed_at=cmd["created_at"], close_operation_id=cmd["id"],
                       final_heads=_heads(state), final_watermark=len(state["events"]),
                       branches=deepcopy(state["branches"]))
        state["active_episode"] = None
    elif kind == "record-experiment":
        if len(state["experiments"]) >= PAPER_LIMITS["experiments"] or payload["id"] in _record_ids(state):
            raise ContractError("experiment identity reused or finite limit exceeded")
        state["experiments"][payload["id"]] = deepcopy(payload)
    elif kind == "record-evidence-event":
        _append_evidence(state, payload)
    elif kind == "create-reasoning-branch":
        if "alternative" in state["branches"] or (not paper and len(_evidence(state["events"])) != 3):
            raise ContractError("one alternative branch requires three original observations")
        source = deepcopy(state["branches"]["main"])
        source.update(base_head=source["head"], head=cmd["id"], watermark=len(state["events"]))
        if series:
            source["judgment"] = None
        state["branches"]["alternative"] = source
    elif kind == "record-interpretation":
        merged = any(item["episode_id"] == cmd["episode_id"] for item in state["merges"]) if series else bool(state["merges"])
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
        select_changes(changes, selected, active_evidence)
        branch.update(head=cmd["id"], watermark=len(state["events"]), judgment=deepcopy(payload["judgment"]))
        if series:
            branch["judgments"][cmd["episode_id"]] = deepcopy(payload["judgment"])
    elif kind == "apply-selected-merge":
        preview = _preview(state, payload["selected_ids"])
        source = state["branches"]["alternative"]
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
                             inherited_ai=series and _branch_ai(source, state))
        target = state["branches"]["main"]
        target["changes"].update({key: deepcopy(source["changes"][key]) for key in preview.selection.closure})
        target.update(head=cmd["id"], watermark=len(state["events"]), judgment=deepcopy(payload["judgment"]))
        state["merges"].append({"operation_id": cmd["id"], "preview": decode(preview.payload),
                                "judgment": deepcopy(payload["judgment"]),
                                "disposition": payload["disposition"], "answers": payload["answers"]})
        if series:
            target["judgments"][cmd["episode_id"]] = deepcopy(payload["judgment"])
            state["merges"][-1]["episode_id"] = cmd["episode_id"]


def _reduce(seed, commands):
    value = decode(seed)
    if type(value) is not dict:
        raise ContractError("research seed must be an object")
    seed = normalize(value, seed_schema(value.get("schema_version")))
    paper = seed["schema_version"] >= 2
    if len(commands) > (PAPER_LIMITS["commands"] if paper else 32):
        raise ContractError("history operation limit exceeded")
    if len({seed["claim_id"], seed["anchor_id"]}) != 2:
        raise ContractError("base identities must be distinct")
    root = "root-" + digest(seed)
    state = {"seed": seed, "events": [], "merges": [], "time": None,
             "branches": {"main": {"head": root, "base_head": root, "watermark": 0, "changes": {}, "judgment": None}}}
    if paper:
        state["experiments"] = {}
    if seed["schema_version"] == 3:
        state.update(active_episode=None, episodes={}, interpretation_owners={}, operation_ids={root})
        state["branches"]["main"]["judgments"] = {}
    seen = set()
    for raw in commands:
        cmd = normalize(decode(raw), command_schema(seed["schema_version"]))
        if canonical_bytes(cmd) != raw:
            raise ContractError("history must use canonical command bytes")
        if cmd["id"] in seen or cmd["id"] == root or (seed["schema_version"] == 3 and cmd["id"] in _record_ids(state)):
            raise ContractError("operation identity reused in history")
        seen.add(cmd["id"])
        if seed["schema_version"] == 3:
            state["operation_ids"].add(cmd["id"])
        _apply(state, cmd)
    return state


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
    if state["seed"]["schema_version"] == 3:
        result.update(episode_id=episode_id, episode=_episode_info(state["episodes"][episode_id]) if episode_id else None,
                      judgments=_branch_judgments(branch, state),
                      interpretation_episode_ids={item["id"]: state["interpretation_owners"][item["id"]] for item in result["interpretations"]})
    return result


def _manifest(state, commands):
    value = {"schema_version": state["seed"]["schema_version"], "authority": "unverified-candidate", "seed": state["seed"],
        "commands": [decode(raw) for raw in commands], "evidence_events": state["events"],
        "views": {ref: _view(state, ref) for ref in sorted(state["branches"])}, "selected_merges": state["merges"]}
    if state["seed"]["schema_version"] == 3:
        value.update(active_episode_id=state["active_episode"], episodes=[_episode_info(item) for item in state["episodes"].values()])
    return canonical_bytes(value)


@dataclass(frozen=True)
class ResearchHistory:
    seed: bytes
    commands: tuple[bytes, ...] = ()

    def __post_init__(self):
        if type(self.seed) is not bytes or type(self.commands) is not tuple or len(self.commands) > PAPER_LIMITS["commands"]:
            raise ContractError("bounded immutable history required")
        if any(type(raw) is not bytes for raw in self.commands) or sum(map(len, self.commands)) + len(self.seed) > 262144:
            raise ContractError("history byte limit exceeded")
        state = _reduce(self.seed, self.commands)
        if canonical_bytes(state["seed"]) != self.seed:
            raise ContractError("history seed is not canonical")
        _manifest(state, self.commands)

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

    def episodes(self):
        if self.schema_version != 3:
            raise ContractError("episode browsing requires the version-three paper profile")
        return [_episode_info(item) for item in _reduce(self.seed, self.commands)["episodes"].values()]

    @property
    def schema_version(self):
        return decode(self.seed)["schema_version"]

    @classmethod
    def replay(cls, seed, commands):
        return cls(seed, commands)

    @property
    def heads(self):
        return tuple(sorted(_heads(_reduce(self.seed, self.commands)).items()))

    @property
    def watermark(self):
        return len(_reduce(self.seed, self.commands)["events"])

    def append(self, command):
        cmd = normalize(command, command_schema(self.schema_version))
        raw = canonical_bytes(cmd)
        for previous in self.commands:
            if decode(previous)["id"] == cmd["id"]:
                if previous != raw:
                    raise ContractError("changed retry cannot overwrite an operation")
                return self
        return replace(self, commands=(*self.commands, raw))

    def check_operation_identity(self, operation_id):
        """Check a fresh v3 candidate ID against all owned records and operations.

        This is only an identity check, not permission to append a new format.
        """
        identifier(operation_id)
        if self.schema_version != 3:
            raise ContractError('paper operation identity requires cumulative history')
        if operation_id in _record_ids(_reduce(self.seed, self.commands)):
            raise ContractError('operation identity reused in history')

    def view(self, ref, *, at_operation=None, episode_id=None):
        commands = self.commands
        if at_operation is not None:
            identifier(at_operation)
            positions = [i for i, raw in enumerate(commands) if decode(raw)["id"] == at_operation]
            root = "root-" + digest(decode(self.seed))
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
        if self.schema_version != 3:
            raise ContractError("cumulative merge projection requires v3")
        selected = normalize(selected, array(ID, PAPER_LIMITS["changes"], 1, True))
        state = _reduce(self.seed, self.commands)
        preview = _preview(state, selected)
        source, target = state["branches"]["alternative"], state["branches"]["main"]
        if source["judgment"] is None:
            raise ContractError("merge requires recorded reasoning")
        before = _view(state, "main")
        merged = decode(preview.payload)
        selection = {**merged["amendments"], "evidence_references": list(preview.selection.evidence_references)}
        selected_ids, required = set(selection["selected"]), set(selection["required"])
        amendments = [{"id": key, "kind": item["kind"], "before": deepcopy(target["changes"].get(key)),
                       "after": deepcopy(item), "disposition": "selected" if key in selected_ids else
                       "required" if key in required else "omitted"}
                      for key, item in sorted(source["changes"].items()) if target["changes"].get(key) != item]
        target["changes"].update({key: deepcopy(source["changes"][key]) for key in preview.selection.closure})
        target["judgment"] = deepcopy(source["judgment"])
        target["judgments"][_episode_id(state)] = deepcopy(source["judgment"])
        value = {"schema_version": 1, "project_id": state["seed"]["project_id"], "episode_id": _episode_id(state),
                 "ref": "main", "source_ref": "alternative", "selection": selection, "amendments": amendments,
                 "before": before, "after": _view(state, "main"),
                 "source_judgment": deepcopy(source["judgment"]), "judgment": deepcopy(source["judgment"]),
                 "source_judgments": _branch_judgments(source, state), "ai_influenced": _branch_ai(source, state),
                 "authority": "unaccepted-preview", "authorization_verified": False}
        return PaperChangesPreview(canonical_bytes(value), digest(value))

    def project_paper_draft(self, ref, amendments, *, episode_id=None):
        """Validate all authored candidates without inventing a complete judgment.

        This is a disposable graph projection, not a selected review or a command.
        Incomplete editor values must remain with their caller on validation error.
        """
        if self.schema_version not in (2, 3):
            raise ContractError('draft projection requires a paper history')
        state = _reduce(self.seed, self.commands)
        before = _view(state, ref, episode_id)
        branches, episode_id = _episode_branches(state, episode_id)
        if episode_id is None:
            raise ContractError('open a paper episode before drafting')
        original = branches[ref]
        proposed, full = _amended_branch(state, original, amendments, episode_id, allow_empty=True)
        if proposed:
            full, _, _ = _select_paper_amendments(state, original, full, proposed, sorted(proposed))
        branches[ref] = full
        if self.schema_version == 3:
            state['interpretation_owners'].update({key: episode_id for key, item in proposed.items()
                                                  if item['kind'] == 'interpretation'})
        value = {'schema': 'claimbranch.paper-draft-projection/v1', 'project_id': state['seed']['project_id'],
                 'episode_id': episode_id, 'ref': ref, 'amendments': [proposed[key] for key in sorted(proposed)],
                 'after': _view(state, ref, episode_id), 'source_judgment': before['judgment'],
                 'source_ai_influenced': _branch_ai(original, state),
                 'authority': 'unaccepted-draft', 'authorization_verified': False}
        return PaperDraftProjection(canonical_bytes(value), digest(value))

    def preview_paper_changes(self, ref, amendments, selected, judgment, *, episode_id=None):
        """Validate a selected overlay using this history's versioned paper rules.

        This projection can inspect amendments after a previous candidate merge.
        It does not append a command, start an episode, rewrite a seed or supply
        a persistent/multi-episode transition. Both provenance chains survive.
        """
        if self.schema_version not in (2, 3) or not isinstance(judgment, Judgment):
            raise ContractError("paper amendments require a paper history and typed complete judgment")
        state = _reduce(self.seed, self.commands)
        before = _view(state, ref, episode_id)
        branches, episode_id = _episode_branches(state, episode_id)
        if episode_id is None:
            raise ContractError("open a paper episode before drafting")
        judgment = _judgment(normalize(asdict(judgment), JUDGMENT), _context(state, episode_id))
        request = normalize({"amendments": amendments, "selected_ids": selected},
                            obj(amendments=amendment_schema(), selected_ids=array(ID, PAPER_LIMITS["changes"], 1, True)))
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
            if self.schema_version == 3:
                selected_branch["judgments"][episode_id] = asdict(judgment)
        after_state = deepcopy(state)
        _episode_branches(after_state, episode_id)[0][ref] = selected_branch
        if self.schema_version == 3:
            after_state["interpretation_owners"].update({key: episode_id for key in included if proposed[key]["kind"] == "interpretation"})
        source_judgment = original["judgment"]
        source_ai = _branch_ai(original, state)
        selected_ids = set(request["selected_ids"])
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
        if self.schema_version == 3:
            value["source_judgments"] = _branch_judgments(original, state)
        return PaperChangesPreview(canonical_bytes(value), digest(value))

    def prepare_merge_review(self, command, *, manuscript_digest, session_nonce, sealed_at, expires_at):
        cmd = normalize(command, command_schema(self.schema_version))
        if cmd["operation_type"] != "apply-selected-merge":
            raise ContractError("merge command required")
        self.append(cmd)  # Revalidate the proposed transition without mutating history.
        preview = self.merge_preview(cmd["payload"]["selected_ids"])
        seed = decode(self.seed)
        episode_context = {"project_id": seed["project_id"], "episode_id": cmd["episode_id"]}
        source_judgments = ()
        binding = {"command": cmd, "merge": decode(preview.payload), "history_digest": digest([decode(raw) for raw in self.commands])}
        if self.schema_version == 3:
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
        return _manifest(_reduce(self.seed, self.commands), self.commands)
