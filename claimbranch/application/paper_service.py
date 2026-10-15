"""Versioned paper queries for UI/CLI adapters; no layout or accepted writes.

The sole history owner remains ResearchHistory. Scenarios are immutable derived
answers tied to exact history/ref content, never a second scientific log.
"""
from collections import deque
from copy import deepcopy
import hashlib

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest, identifier
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, ID, TEXT, normalize, obj
from claimbranch.core.context import ContextRecord, ContextSelection, compile_context
from claimbranch.core.paper_context import FIELDS, request_schema
from claimbranch.core.paper_changes import request_schema as changes_request_schema
from .paper_branch import build_branch


SCENARIO = obj(schema_version={"type": "integer", "const": 1}, project_id=ID, episode_id=ID,
               ref={"enum": ["main", "alternative"]}, view_digest=HASH, plan_id=ID,
               outcome={"enum": ["supports", "challenges", "inconclusive"]},
               assumed_observation=TEXT, rationale=TEXT)


def scenario_schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:claimbranch:paper-scenario:v1", **deepcopy(SCENARIO)}


def _graph(seed, view):
    """One projection for current views and explicitly unaccepted overlays."""
    nodes, relations = [], []
    from claimbranch.core.protocols import protocol_context
    registered_context=protocol_context(view)
    initial = seed.get('initial_argument')
    imported = {record['id']: record for record in initial['records']} if initial else {}
    unresolved = sum(initial['unresolved_source_pointers'], []) if initial else []
    annotation_bytes = 0

    def source_mark(record):
        nonlocal annotation_bytes
        pointer = record['source_pointer']
        pointers = [p for p in unresolved if not pointer or p == pointer or p.startswith(pointer + '/')]
        annotation_bytes += sum(len(p.encode('utf-8')) + 4 for p in pointers)
        if annotation_bytes > 8388608:
            raise ContractError('capacity import-source-graph-bytes: %s / 8388608; narrow source record pointers' % annotation_bytes)
        return dict(authority='imported-source-claim', transport='imported', contributor=record['origin']['contributor'],
            detail=record['origin']['detail'], recorded_at=record['recorded_at'],
            source_digest=initial['source_sha256'], source_pointer=pointer,
            original_body=deepcopy(record['body']),
            unresolved_pointer_pages=[pointers[i:i+128] for i in range(0, len(pointers), 128)])

    def node(record_id, kind, content):
        content = deepcopy(content)
        if record_id in registered_context:content['protocol_context']=deepcopy(registered_context[record_id])
        record = imported.get(record_id)
        if record:
            content['imported_source'] = source_mark(record)
        dependencies = view.get('imported_dependencies', {}).get(record_id, [])
        if dependencies:
            content['imported_dependencies'] = deepcopy(dependencies)
        if initial and record_id == seed['claim_id']:
            content['historical_decisions'] = [deepcopy(r) for r in initial['records'] if r['kind'] == 'historical-decision']
        if record_id in view.get('titles',{}):content['title']=view['titles'][record_id]
        edits=[r for r in view.get('graph_revisions',[]) if any(e['id']==record_id or e['replaces']==record_id for e in r['edits'])]
        if edits:content['graph_revisions']=deepcopy(edits);content['review_required']=True
        nodes.append({'id': record_id, 'kind': kind, 'content': content})

    def relation(source, target, kind, *, record_id=None, rationale=None, scientific=False):
        value = {"source_id": source, "target_id": target, "type": kind,
                 "record_id": record_id, "rationale": rationale, "scientific": scientific}
        revisions=[r for r in view.get('graph_revisions',[]) if any(e['id']==record_id for e in r['edits'])]
        if revisions:value['graph_revisions']=deepcopy(revisions);value['review_required']=True
        relation_key = "relation-" + digest(value)
        if record_id in imported: value["imported_source"] = source_mark(imported[record_id])
        dependencies = view.get('imported_dependencies', {}).get(record_id, [])
        if dependencies: value['imported_dependencies'] = deepcopy(dependencies)
        relations.append({"key": relation_key, **value})

    for claim in view["claims"]:
        content=deepcopy(claim)
        policy=view.get('wording_policies',{}).get(claim['id'])
        if policy:content['wording_policy']=deepcopy(policy)
        companions=[deepcopy(d) for d in view.get('companion_dependencies',{}).values() if d['target_id']==claim['id']]
        if companions:content['companion_dependencies']=companions
        node(claim["id"], "claim", content)
        for parent in claim["parent_ids"]:
            relation(claim["id"], parent, "part-of")
    experiments = {item["id"]: item for item in view["experiments"]}
    for run in experiments.values():
        node(run["id"], "experiment-record", {**run, "status": "recorded"})
    for observation in view["evidence"]:
        run = experiments[observation["run_id"]]
        node(observation["id"], "observation", {**observation, "metric": run["metric"],
             "conditions": run["conditions"], "source_ref": run["source_ref"]})
        relation(observation["run_id"], observation["id"], "produced")
    for item in view["changes"]:
        key, body, kind = item["id"], item["body"], item["kind"]
        if kind == "scientific-edge":
            relation(body["source_id"], body["target_id"], body["edge_type"],
                     record_id=key, rationale=body["rationale"], scientific=True)
        elif kind == "interpretation":
            content = {**body, "episode_id": view["interpretation_episode_ids"][key]} if "interpretation_episode_ids" in view else body
            matches=[d for d in view.get('co_reports',{}).values() if key in d['selected_ids']]
            if matches:
                decision=matches[-1];reading=next(r for r in decision['readings'] if r['id']==key)
                content={**content,'scope':reading['scope'],'co_report':deepcopy(decision),'declared_origin':reading['origin']}
            node(key, kind, content)
            for observation in body["observation_ids"]:
                relation(key, observation, "interprets")
        elif kind == "experiment-plan":
            node(key, kind, body)
            relation(key, body["claim_id"], "tests")
    for key,question in view.get('critiques',{}).items():
        node(key,'critique-question',dict(statement=question['question'],question_origin=question['question_origin'],source_origin=question['source_origin'],source_kind=question['source_kind'],classification=question['classification'],revision_id=question['revision_id'],resolution='unresolved',original_available=True,anonymity_verified=False,revisions=deepcopy(question['revisions']),rationale=question.get('rationale'),associations=[deepcopy(l) for l in view.get('critique_links',{}).values() if l['critique_id']==key]))
    available={n['id'] for n in nodes}
    for link in view.get('critique_links',{}).values():
        if link['target_id'] in available:relation(link['critique_id'],link['target_id'],link['relation'],record_id=link['id'],rationale=link['rationale'],scientific=False)
    present={n['id'] for n in nodes}
    for decision in view.get('co_reports',{}).values():
        members=[key for key in decision['selected_ids'] if key in present]
        for reading in decision['readings']:
            if reading['id'] in present and reading['source_id'] in present:
                relation(reading['id'],reading['source_id'],'revises-reading',rationale=decision['judgment']['rationale'])
        for first,second in zip(members,members[1:]):relation(first,second,'co-reported-with',record_id=decision['id'],rationale=decision['judgment']['rationale'])
    unrepresented=[]
    available={item['id'] for item in nodes}
    for dependency in view.get('companion_dependencies',{}).values():
        if dependency['status']=='active' and not {dependency['companion_id'],dependency['target_id']}<=available:
            unrepresented.append(dependency['id']);continue
        if dependency['status']=='active':
            relation(dependency['companion_id'],dependency['target_id'],'must-co-report',record_id=dependency['id'],rationale=dependency['rationale'])
    anchors=view.get('manuscript_anchors',{})
    if seed['anchor_id'] not in anchors:
        node(seed["anchor_id"], "manuscript-anchor", {"claim_id": seed["claim_id"], "applied": False})
        relation(seed["anchor_id"], seed["claim_id"], "expresses")
    for key,anchor in sorted(anchors.items()):
        node(key,'manuscript-anchor',{**anchor,'reporting_context':view.get('anchor_contexts',{}).get(key),'applied':False,'claim_id':anchor['expresses'][0] if anchor['expresses'] else None,
            'statement':anchor['kind']+' / '+key+' / '+bytes.fromhex(anchor['source']['manuscript']).decode('utf-8',errors='replace'),'source_fidelity_verified':False})
        for target in anchor['expresses']: relation(key,target,'expresses',rationale=anchor['rationale'])
        for target in anchor['plots']: relation(key,target,'plots',rationale=anchor['rationale'])
        for target in anchor['parents']: relation(key,target,'caption-of',rationale=anchor['rationale'])
    # Changed dependency meaning invalidates prior review even if a dependent
    # claim keeps its historical supported label. This is reach, never truth.
    review_subjects={key for revision in view.get('graph_revisions',[]) for key in revision.get('review_subject_ids',[])}
    outgoing={}
    for edge in relations:
        source,target=edge['source_id'],edge['target_id']
        if edge['type'] in ('interprets','expresses','plots','caption-of'):source,target=target,source
        outgoing.setdefault(source,set()).add(target)
        if edge['type']=='co-reported-with':outgoing.setdefault(target,set()).add(source)
    pending=deque(review_subjects)
    while pending:
        for target in outgoing.get(pending.popleft(),()):
            if target not in review_subjects:review_subjects.add(target);pending.append(target)
    for item in nodes:
        if item['id'] in review_subjects:item['content']['review_required']=True
    for item in nodes:
        declared=[r for r in view.get('metadata_origins',{}).values() if item['id'] in r['subject_ids']]
        if declared:item['content']['metadata_contributions']=deepcopy(declared)
    return {**({"reporting_dependencies_outside_view":sorted(unrepresented)} if unrepresented else {}), "nodes": sorted(nodes, key=lambda item: item["id"]),
            "relations": sorted(relations, key=lambda item: item["key"])}


def _change_impact(graphs, amendments):
    affected, witnesses = set(), []
    for phase, graph in graphs.items():
        nodes = {item["id"]: item for item in graph["nodes"]}
        outgoing = {}
        for relation in graph["relations"]:
            if relation["scientific"]:
                outgoing.setdefault(relation["source_id"], []).append(relation)
        queue, seen = deque(), set()
        for item in amendments:
            record = item[phase]
            if item["disposition"] == "omitted" or record is None:
                continue
            kind, body = record["kind"], record["body"]
            relation_keys = []
            if kind == "scientific-edge":
                start = body["target_id"]
                path = [body["source_id"], start]
                relation_keys = [edge["key"] for edge in graph["relations"] if edge["record_id"] == item["id"]]
            elif kind in ("claim-status", "experiment-plan"):
                start = body["claim_id"]
                path = [item["id"], start] if kind == "experiment-plan" else [start]
                if kind == "experiment-plan":
                    relation_keys = [edge["key"] for edge in graph["relations"] if edge["type"] == "tests" and edge["source_id"] == item["id"]]
            else:
                start, path = item["id"], [item["id"]]
            if start not in seen:
                seen.add(start)
                queue.append((start, item["id"], path, relation_keys))
        # A deterministic witness per reached claim/phase bounds output even
        # when many edits share paths. Reach is a review cue, not a truth rule.
        while queue:
            node, change_id, path, keys = queue.popleft()
            if nodes[node]["kind"] == "claim":
                affected.add(node)
                witnesses.append({"phase": phase, "change_id": change_id, "claim_id": node,
                                  "node_ids": path, "relation_keys": keys})
            for edge in outgoing.get(node, ()):
                target = edge["target_id"]
                if target not in seen:
                    seen.add(target)
                    queue.append((target, change_id, [*path, target], [*keys, edge["key"]]))
    before = {item["id"]: item for item in graphs["before"]["nodes"]}
    after = {item["id"]: item for item in graphs["after"]["nodes"]}
    claim_ids = {key for key, node in after.items() if node["kind"] == "claim"}
    return {"requires_human_judgment": True,
            "directly_changed_claim_ids": sorted(key for key in claim_ids if before.get(key) != after[key]),
            "unchanged_claim_ids": sorted(key for key in claim_ids if before.get(key) == after[key]),
            "potentially_affected_claim_ids": sorted(affected),
            "outside_impact_claim_ids": sorted(claim_ids - affected),
            "unchanged_evidence_ids": sorted(key for key, node in before.items() if node["kind"] == "observation" and after.get(key) == node),
            "potentially_affected_anchor_ids": sorted(key for key, node in after.items()
                if node["kind"] == "manuscript-anchor" and node["content"]["claim_id"] in affected),
            "witness_paths": witnesses}


def _anchor_reach(graph, roots, phase):
    outgoing={}
    scoped={n['id'] for n in graph['nodes'] if n['content'].get('co_report')}
    for edge in graph['relations']:
        if edge['type']=='interprets' and edge['source_id'] in scoped:
            outgoing.setdefault(edge['target_id'],[]).append((edge['source_id'],edge));continue
        if edge['scientific'] or edge['type']=='must-co-report': outgoing.setdefault(edge['source_id'],[]).append((edge['target_id'],edge))
        elif edge['type'] in ('expresses','plots','caption-of'):
            outgoing.setdefault(edge['target_id'],[]).append((edge['source_id'],edge))
    nodes={n['id']:n for n in graph['nodes']}; queue=deque((key,[key],[]) for key in sorted(set(roots)) if key in nodes);seen=set();witnesses=[]
    while queue:
        key,path,links=queue.popleft()
        if key in seen or key not in nodes:continue
        seen.add(key)
        if nodes[key]['kind']=='manuscript-anchor':witnesses.append(dict(phase=phase,anchor_id=key,node_ids=path,relation_keys=links))
        for target,edge in sorted(outgoing.get(key,[]),key=lambda pair:pair[1]['key']):
            queue.append((target,[*path,target],[*links,edge['key']]))
    return witnesses


class PaperService:
    def __init__(self, history):
        if not isinstance(history, ResearchHistory) or history.schema_version not in (2, 3, 4, 5):
            raise ContractError("paper service requires a versioned paper history")
        self._history = history
        self._pending_work = None
        self._query_cache = {}

    def _bytes(self, value):
        from claimbranch.core.paper_capacity import encode
        return encode(value, purpose='manifest') if self._history.schema_version in (4, 5) else canonical_bytes(value)

    def _decode(self, raw):
        from claimbranch.core.paper_capacity import decode as paper_decode
        return paper_decode(raw, purpose='manifest') if self._history.schema_version in (4, 5) else decode(raw)

    def _digest(self, value):
        return hashlib.sha256(self._bytes(value)).hexdigest()

    def episodes(self):
        episodes = self._history.episodes()
        value = {"schema": "claimbranch.paper-episodes/v1", "project_id": self._decode(self._history.seed)["project_id"],
                 "history_digest": hashlib.sha256(self._history.manifest()).hexdigest(),
                 "active_episode_id": next((item["id"] for item in episodes if item["status"] == "active"), None),
                 "episodes": episodes, "authority": "unverified-candidate", "authorization_verified": False}
        return {**value, "digest": self._digest(value)}

    def pending_work(self, *, episode_id=None):
        """Reconstruct conditional consequences, never accepted Debt records.

        The v3 history has no native receipts or closure commands. Keeping this
        derived projection separate prevents a closed graph episode, discarded
        preview or freshly reconstructed hash from claiming completed work.
        """
        history = self._history
        if history.schema_version < 3:
            raise ContractError("cumulative work projection requires the version-three paper profile")
        if episode_id is not None:
            identifier(episode_id)
            if episode_id not in {item["id"] for item in history.episodes()}:
                raise ContractError("unknown paper episode")
        if self._pending_work is not None:
            value=self._decode(self._pending_work)
        elif episode_id is None:
            self._pending_work=self._bytes(self._all_pending_work())
            value=self._decode(self._pending_work)
        else:
            cache=getattr(self,'_pending_by_episode',{})
            if episode_id not in cache:cache[episode_id]=self._bytes(self._all_pending_work(episode_id=episode_id))
            self._pending_by_episode=cache
            value=self._decode(cache[episode_id])
        if episode_id is not None:
            value.pop("digest")
            value["episode_id"] = episode_id
            value["items"] = [item for item in value["items"] if item["episode_id"] == episode_id]
            value["digest"] = self._digest(value)
        return value

    def understanding_return(self, work_id, *, project_id):
        """Reopen conditional explanation context, without preparing debt closure.

        The original graph is frozen immediately after its causal merge; the
        current graph is today's main, even when the cause episode is closed.
        This projection digest is a context fingerprint, never a sealed review.
        """
        identifier(work_id)
        identifier(project_id)
        history = self._history
        if project_id != self._decode(history.seed)["project_id"]:
            raise ContractError("understanding work belongs to another project")
        pending = self.pending_work()
        item = next((item for item in pending["items"] if item["id"] == work_id), None)
        if item is None or item["kind"] != "understanding":
            raise ContractError("select an existing conditional understanding work item")

        cause_index = next((index for index, raw in enumerate(history.commands)
                            if self._decode(raw)["id"] == item["cause_operation_id"]), None)
        if cause_index is None:
            raise ContractError("recorded understanding cause is unavailable")
        # Use the causal prefix, rather than a past view fingerprinted against
        # today's whole history, so original context stays stable across return.
        cause_history = ResearchHistory(history.seed, history.commands[:cause_index + 1])
        original = PaperService(cause_history).query("main", at_operation=item["cause_operation_id"],
                                                   episode_id=item["episode_id"])
        current = self.query("main")
        value = {"schema": "claimbranch.paper-understanding-return/v1", "project_id": project_id,
                 "work": item, "original": original, "current": current,
                 "history_changed_since_merge": original["history_digest"] != current["history_digest"],
                 "authority": "conditional-on-acceptance", "cause_review_available": False,
                 "closure_available": False, "closure_unavailable_reason": "accepted-cause-review-unavailable",
                 "acceptance_available": False, "accepted_debts_created": 0, "accepted_writes": 0,
                 "authorization_verified": False}
        # Each view and item already has a bounded canonical representation.
        # Bind their content hashes so two valid full views can return together
        # without truncation or increasing the per-record canonical byte limit.
        binding = {**value, "work": self._digest(item), "original": original["digest"],
                   "current": current["digest"]}
        return {**value, "digest": self._digest(binding)}

    def _all_pending_work(self,*,episode_id=None):
        # The owned history is immutable. Cache only canonical derived bytes;
        # every public read decodes a detached value and refresh uses a new service.
        history = self._history
        seed = self._decode(history.seed)
        main_head, watermark = dict(history.heads)["main"], history.watermark
        items = []
        for index, raw in enumerate(history.commands):
            command = self._decode(raw)
            if command["operation_type"] not in ("apply-selected-merge", "apply-imported-merge"):
                continue
            if episode_id is not None and command['episode_id']!=episode_id:continue
            payload = command["payload"]
            # Reconstruct the whole before/after graph. The older finite merge
            # path list alone can omit reach through unchanged inherited edges.
            prior = ResearchHistory(history.seed, history.commands[:index])
            preview = PaperService(prior).preview_merge(payload["selected_ids"], episode_id=command["episode_id"])
            influenced = preview["provenance"]["ai_influenced"] or any(
                item["contributor"] == "ai" for item in payload["judgment"]["history"])
            for kind in ("manuscript", "understanding") if payload["disposition"] == "deferred" else ("manuscript",):
                identity = {"kind": kind, "project_id": seed["project_id"],
                            "episode_id": command["episode_id"], "cause_operation_id": command["id"]}
                items.append({**identity, "id": "work-" + self._digest(identity)[:32],
                    "status": "pending-if-accepted", "recorded_at": command["created_at"],
                    "cause_main_head": command["id"], "current_main_head": main_head,
                    "main_changed_since_merge": main_head != command["id"],
                    "evidence_changed_since_merge": watermark != command["evidence_watermark"],
                    "anchor_id": seed["anchor_id"] if kind == "manuscript" else None,
                    "selection": preview["selection"],
                    "potentially_affected_claim_ids": preview["impact"]["potentially_affected_claim_ids"],
                    "potentially_affected_anchor_ids": preview["impact"]["potentially_affected_anchor_ids"],
                    "judgment": payload["judgment"], "source_judgments": preview["provenance"]["source_judgments"],
                    "ai_influenced": influenced, "explanation_disposition": payload["disposition"],
                    "explanation_answers": payload["answers"], "closure_available": False,
                    "authorization_verified": False})
        value = {"schema": "claimbranch.paper-work/v1", "project_id": seed["project_id"],
                 "episode_id": None, "history_digest": hashlib.sha256(history.manifest()).hexdigest(),
                 "current_main_head": main_head, "evidence_watermark": watermark, "items": items,
                 "authority": "conditional-on-acceptance", "accepted_debts_created": 0, "authorization_verified": False}
        return {**value, "digest": self._digest(value)}

    def query(self, ref="main", *, at_operation=None, episode_id=None):
        key=(ref,at_operation,episode_id)
        if self._history.schema_version in (4, 5) and key in self._query_cache:
            return deepcopy(self._query_cache[key])
        history = self._history
        view = history.view(ref, at_operation=at_operation, episode_id=episode_id)
        seed = self._decode(history.seed)
        series = history.schema_version >= 3
        episode_id = view["episode_id"] if series else seed["episode_id"]
        if episode_id is None:
            raise ContractError("open a paper episode before querying its argument context")
        value = {"schema": "claimbranch.paper-view/v2" if series else "claimbranch.paper-view/v1", "project_id": seed["project_id"],
                 "episode_id": episode_id, "title": seed["paper_title"], "thesis_id": seed["claim_id"],
                 "ref": ref, "head": view["head"], "evidence_watermark": view["evidence_watermark"],
                 "reasoning_evidence_watermark": view["reasoning_evidence_watermark"],
                 "evidence_changed_since_reasoning": view["evidence_changed_since_reasoning"],
                 "at_operation": at_operation,
                 **_graph(seed, view),
                 "judgment": view["judgment"], "authority": "unverified-candidate",
                 "authorization_verified": False}
        if history.schema_version == 5:
            value['historical_decisions'] = deepcopy(view['historical_decisions'])
            value['import_source_digest'] = view['import_source_digest']
            value['unresolved_source_pointers'] = deepcopy(view['unresolved_source_pointers'])
        if series:
            value.update(episode=view["episode"], judgments=view["judgments"])
        # Bind the entire revision, including an added experiment that did not
        # advance a reasoning head. A matching UI layout is not freshness proof.
        value["history_digest"] = hashlib.sha256(history.manifest()).hexdigest()
        result = {**value, "digest": self._digest(value)}
        if self._history.schema_version in (4, 5) and len(self._query_cache)<64:
            self._query_cache[key]=deepcopy(result)
        return result

    def anchor_impact(self, node_ids, *, at_operation=None):
        current=self.query('main'); old=self.query('main',at_operation=at_operation) if at_operation is not None else current
        roots=set(node_ids)
        known={n['id'] for graph in (old,current) for n in graph['nodes']} | {e['record_id'] for graph in (old,current) for e in graph['relations'] if e['scientific']}
        if not roots or not roots <= known:raise ContractError('Anchor impact needs known nodes or scientific connection IDs; no absence of impact was inferred.')
        for graph in (old,current):
            for edge in graph['relations']:
                if edge['scientific'] and edge['record_id'] in roots:
                    roots.update((edge['source_id'],edge['target_id']))
        witnesses=_anchor_reach(old,roots,'before')+_anchor_reach(current,roots,'after')
        affected=sorted({w['anchor_id'] for w in witnesses})
        anchors={n['id'] for n in current['nodes'] if n['kind']=='manuscript-anchor'}
        return dict(potentially_affected_anchor_ids=affected,outside_impact_anchor_ids=sorted(anchors-set(affected)),
                    anchor_witness_paths=witnesses,requires_human_judgment=True,write_available=False,
                    coverage='Explicit registered relationships only; unregistered passages/includes/graphics and scientific fidelity are outside coverage.')

    def project_draft(self, ref, amendments, *, episode_id=None):
        """Graph of all authored candidates, independent of judgment/review lifetime."""
        view = self.query(ref, episode_id=episode_id)
        domain = self._decode(self._history.project_paper_draft(ref, amendments, episode_id=view['episode_id']).payload)
        graph = _graph(self._decode(self._history.seed), domain['after'])
        ids = {item['id'] for item in domain['amendments']}
        for node in graph['nodes']:
            node['draft'] = node['id'] in ids
        for edge in graph['relations']:
            edge['draft'] = edge['record_id'] in ids or (not edge['scientific'] and edge['source_id'] in ids)
        value = {'schema': 'claimbranch.paper-draft-graph/v1', 'project_id': view['project_id'],
                 'episode_id': view['episode_id'], 'ref': ref, 'view_digest': view['digest'],
                 'history_digest': view['history_digest'], 'graph': graph, 'authored_ids': sorted(ids),
                 'source_ai_influenced': domain['source_ai_influenced'],
                 'authority': 'unaccepted-draft', 'acceptance_available': False, 'authorization_verified': False}
        return {**value, 'digest': self._digest(value)}

    def preview_changes(self, request, judgment, *, source_node_id=None):
        request = normalize(request, changes_request_schema())
        view = self.query(request["ref"], episode_id=request["episode_id"])
        if any(request[key] != view[key] for key in ("project_id", "episode_id")) or request["view_digest"] != view["digest"]:
            raise ContractError("scientific change review is stale or belongs to another paper")
        domain = self._decode(self._history.preview_paper_changes(request["ref"], request["amendments"],
                        request["selected_ids"], judgment, episode_id=request["episode_id"], source_node_id=source_node_id).payload)
        return self._project_changes(domain, view, schema="claimbranch.paper-changes/v1",
                                     identity={"draft_id": request["draft_id"], "draft_revision": request["draft_revision"]})

    def preview_merge(self, selected_ids, *, episode_id):
        """Read the active recorded alternative, never caller-supplied graph rows."""
        view = self.query("main", episode_id=episode_id)
        if self._history.schema_version < 3 or self.episodes()["active_episode_id"] != episode_id:
            raise ContractError("merge review requires the explicit active cumulative episode")
        domain = self._decode(self._history.preview_merge_changes(selected_ids).payload)
        return self._project_changes(domain, view, schema="claimbranch.paper-merge/v1",
            identity={"source_ref": "alternative", "source_view_digest": self.query("alternative", episode_id=episode_id)["digest"]})

    def branch_candidate(self, request, judgment, *, operation_id, created_at, source_node_id=None):
        """Construct exact unverified branch commands from this owned source.

        The session owns the draft/review lifetime. This pure layer verifies the
        source binding and domain transition; it grants no approval or storage.
        """
        request = normalize(request, changes_request_schema())
        view = self.query(request["ref"], episode_id=request["episode_id"])
        if any(request[key] != view[key] for key in ("project_id", "episode_id")) or request["view_digest"] != view["digest"]:
            raise ContractError("draft recording is stale or belongs to another paper")
        candidate, domain = build_branch(self._history, request, judgment, operation_id=operation_id, created_at=created_at, source_node_id=source_node_id)
        preview = self._project_changes(domain, view, schema="claimbranch.paper-branch/v1",
            identity={"draft_id": request["draft_id"], "draft_revision": request["draft_revision"], "target_ref": "alternative"})
        return candidate, {"preview": preview,
            "commands": [self._decode(raw) for raw in candidate.commands[len(self._history.commands):]],
            "candidate_history_digest": hashlib.sha256(candidate.manifest()).hexdigest()}

    def _project_changes(self, domain, view, *, schema, identity):
        seed = self._decode(self._history.seed)
        graphs = {phase: {"schema": "claimbranch.paper-change-graph/v1", "phase": phase,
                         "source_view_digest": view["digest"], "authority": "unaccepted-preview",
                         "authorization_verified": False, **_graph(seed, domain[phase])}
                  for phase in ("before", "after")}
        impact = _change_impact(graphs, domain["amendments"])
        if self._history.has_manuscript_anchors:
            witnesses=[]
            for phase,graph in graphs.items():
                roots=[]
                for amendment in domain['amendments']:
                    record=amendment[phase]
                    if record is None or amendment['disposition']=='omitted':continue
                    if record['kind']=='scientific-edge':roots.extend((record['body']['source_id'],record['body']['target_id']))
                    else:roots.append(record['body'].get('claim_id',record['id']))
                witnesses.extend(_anchor_reach(graph,roots,phase))
            impact['potentially_affected_anchor_ids']=sorted({w['anchor_id'] for w in witnesses})
            impact['anchor_witness_paths']=witnesses
            impact['outside_impact_anchor_ids']=sorted({n['id'] for n in graphs['after']['nodes'] if n['kind']=='manuscript-anchor'}-set(impact['potentially_affected_anchor_ids']))
            impact['coverage']='Explicit registered relationships only; includes/graphics and unregistered passages are outside coverage.'

        value = {"schema": schema, "project_id": view["project_id"],
                 "episode_id": view["episode_id"], "ref": view["ref"], "view_digest": view["digest"],
                 "history_digest": view["history_digest"], **identity, "selection": domain["selection"],
                 "amendments": domain["amendments"], "graphs": graphs, "impact": impact,
                 "provenance": {"source_judgment": domain["source_judgment"], "judgment": domain["judgment"],
                                "ai_influenced": domain["ai_influenced"]},
                 "manuscript": {"source_verified": False, "write_available": False,
                                "potentially_affected_anchor_ids": impact["potentially_affected_anchor_ids"]},
                 "authority": "unaccepted-preview", "acceptance_available": False, "authorization_verified": False}
        if "source_judgments" in domain:
            value["provenance"]["source_judgments"] = domain["source_judgments"]
        if 'imported_sources' in domain:
            value['provenance'].update(imported_sources=domain['imported_sources'], source_node_id=domain['source_node_id'],
                                       origin_uncertain=domain['origin_uncertain'])
        return {**value, "digest": self._digest(value)}

    def compile_context(self, request):
        if self._history.has_critiques:raise ContractError('Private critique context is not qualified for provider projection; continue locally')
        if self._history.schema_version == 5:
            raise ContractError('Imported-origin provider context is not yet qualified; inspect the graph and continue manually.')
        """Project explicit fields from this reader, never caller-supplied rows.

        All candidate data remains conservatively private. Source artifacts are
        not opened; availability/fidelity cannot be established by this adapter.
        """
        request = normalize(request, request_schema())
        view = self.query(request["ref"], episode_id=request["episode_id"])
        if any(request[key] != view[key] for key in ("project_id", "episode_id")) or request["view_digest"] != view["digest"]:
            raise ContractError("paper context is stale or belongs to another project")
        nodes = {node["id"]: node for node in view["nodes"]}
        edges = {edge["record_id"]: edge for edge in view["relations"] if edge["scientific"]}
        records, selected = [], []
        for item in request["selections"]:
            node = nodes.get(item["record_id"])
            if not node or node["kind"] not in FIELDS:
                raise ContractError("unknown or unavailable paper context source")
            kind, content = node["kind"], node["content"]
            if self._history.schema_version >= 3 and kind == "interpretation" and "episode_id" not in item["fields"]:
                raise ContractError("a cumulative interpretation must explicitly disclose its source episode")
            fields = {}
            for name in FIELDS[kind]:
                if name == "source":
                    fields[name] = {"reference": content["source_ref"], "availability": "unverified"}
                elif name == "episode_id":
                    fields[name] = content.get("episode_id", view["episode_id"])
                else:
                    fields[name] = content.get(name) if name == "scope" else content[name]
            records.append(ContextRecord.create(view["project_id"], node["id"], kind, "private", fields, schema_version=2))
            selected.append((node["id"], tuple(item["fields"])))
        for key in request["scientific_edge_ids"]:
            edge = edges.get(key)
            if not edge:
                raise ContractError("only an existing explicit scientific relation can enter context")
            fields = {"source_id": edge["source_id"], "target_id": edge["target_id"],
                      "edge_type": edge["type"], "rationale": edge["rationale"]}
            records.append(ContextRecord.create(view["project_id"], key, "scientific-relation", "private", fields, schema_version=2))
            selected.append((key, tuple(fields)))
        selection = ContextSelection(view["project_id"], view["episode_id"], request["purpose"], tuple(selected),
                                     schema_version=2, binding=self._bytes({"ref": view["ref"], "view_digest": view["digest"]}))
        return compile_context(tuple(records), selection)

    def scenario(self, request):
        request = normalize(request, SCENARIO)
        view = self.query(request["ref"], episode_id=request["episode_id"])
        if any(request[key] != view[key] for key in ("project_id", "episode_id")) or request["view_digest"] != view["digest"]:
            raise ContractError("scenario context is stale or belongs to another project")
        nodes = {node["id"]: node for node in view["nodes"]}
        plan = nodes.get(request["plan_id"])
        if not plan or plan["kind"] != "experiment-plan" or plan["content"]["status"] != "planned":
            raise ContractError("scenario requires an existing unrun experiment plan")
        target = plan["content"]["claim_id"]
        outgoing = {}
        for relation in view["relations"]:
            if relation["scientific"] and nodes[relation["source_id"]]["kind"] == "claim":
                outgoing.setdefault(relation["source_id"], []).append(relation)
        affected, links, witnesses = {target}, set(), {target: [target]}
        queue = deque([target])
        while queue:
            source = queue.popleft()
            for relation in outgoing.get(source, ()):
                destination = relation["target_id"]
                links.add(relation["key"])
                if destination not in affected:
                    affected.add(destination)
                    witnesses[destination] = [*witnesses[source], destination]
                    queue.append(destination)
        result = {"schema": "claimbranch.paper-impact/v1", "authority": "hypothetical",
                  "authorization_verified": False, "requires_human_judgment": True,
                  "project_id": view["project_id"], "episode_id": view["episode_id"], "ref": view["ref"],
                  "view_digest": view["digest"],
                  "assumption": {"plan_id": request["plan_id"], "target_claim_id": target,
                      "outcome": request["outcome"], "observation": request["assumed_observation"],
                      "rationale": request["rationale"],
                      "relation_type": None if request["outcome"] == "inconclusive" else request["outcome"]},
                  "potentially_affected_claim_ids": sorted(affected),
                  "unaffected_claim_ids": sorted(key for key, node in nodes.items() if node["kind"] == "claim" and key not in affected),
                  "unchanged_evidence_ids": sorted(key for key, node in nodes.items() if node["kind"] == "observation"),
                  "potentially_affected_anchor_ids": sorted(edge["source_id"] for edge in view["relations"]
                      if edge["type"] == "expresses" and edge["target_id"] in affected),
                  "impact_relation_keys": sorted(links), "witness_paths": [witnesses[key] for key in sorted(witnesses)],
                  "existing_basis": [edge for edge in view["relations"] if edge["scientific"] and edge["target_id"] in affected]}
        if self._history.has_manuscript_anchors:
            anchor_witnesses=_anchor_reach(view,affected,'hypothetical')
            result['potentially_affected_anchor_ids']=sorted({w['anchor_id'] for w in anchor_witnesses})
            result['anchor_witness_paths']=anchor_witnesses
        self._bytes(result)
        return {**result, "digest": self._digest(result)}
