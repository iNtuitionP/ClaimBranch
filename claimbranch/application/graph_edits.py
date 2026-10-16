"""Detached exact graph comparison; personal confirmation is owned by the TUI."""
from datetime import datetime,timezone
import hashlib
import secrets
from copy import deepcopy
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode
from .paper_service import PaperService
from .paper_work_store import PaperWork
from .manuscript_anchors import source_statuses


def editable_record(project,key):
    history=project.work.history;view=history.view('main');root=decode(history.seed,purpose='history')['claim_id']
    title=view.get('titles',{}).get(key)
    if key==root:kind,body='thesis',{'statement':view['claim']['statement']}
    else:
        change=next((r for r in view['changes'] if r['id']==key),None)
        run=next((r for r in view['experiments'] if r['id']==key),None)
        obs=next((r for r in view['evidence'] if r['id']==key),None)
        anchor=view.get('manuscript_anchors',{}).get(key)
        critique=view.get('critiques',{}).get(key)
        if change:kind,body=change['kind'],deepcopy(change['body'])
        elif run:kind,body='experiment-record',{k:v for k,v in run.items() if k not in ('id','imported_source')}
        elif obs:kind,body='observation',dict(statement=obs['statement'],value=obs.get('value'))
        elif anchor:kind,body='manuscript-anchor',{k:deepcopy(anchor[k]) for k in ('kind','expresses','plots','parents','rationale')}
        elif critique:kind,body='critique-question',dict(question=critique['question'])
        else:raise ContractError('Choose a recorded node or scientific connection; register manuscript blocks before editing')
    from claimbranch.core.graph_vocabulary import relation_label
    fallback=('Registered '+body['kind']+' block') if kind=='manuscript-anchor' else (relation_label(body['edge_type'])+' connection') if kind=='scientific-edge' else kind
    title=title or body.get('statement') or body.get('objective') or body.get('question') or fallback
    return dict(id=key,kind=kind,body=body,title=title.replace('\n',' ').replace('\r',' ')[:240],replaces=None)


def prepare_edits(project,edits,rationale,origin='human',proposal_source=None):
    history=project.work.history
    if history.schema_version not in (4, 5, 14):raise ContractError('Use a saved personal paper profile for direct editing')
    command=dict(schema_version=13,id='graph-'+secrets.token_hex(12),project_id=project.project_id,
        episode_id=history.view('main')['episode_id'],created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        operation_type='revise-graph',expected_heads=dict(history.heads),evidence_watermark=history.watermark,
        payload=dict(edits=deepcopy(edits),rationale=rationale,origin=origin,proposal_source=deepcopy(proposal_source)))
    candidate=history.append(command)
    workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);_install(app,candidate,app.episode_id,app.ref,app.selected_id);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    roots={e['id'] for e in edits}|{e['replaces'] for e in edits if e['replaces']}
    service=PaperService(candidate)
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=command,
        before=PaperService(history).query('main'),after=service.query('main'),impact=service.anchor_impact(sorted(roots),at_operation=decode(history.commands[-1],purpose='history')['id']) if history.commands else service.anchor_impact(sorted(roots)),
        freshness=source_statuses(history),authority='Explicit personal revision. Prior records/origins retained; manuscript read-only.',
        review_required=True,writes=False)


def recheck_edits(project,review):
    if hashlib.sha256(project.payload).hexdigest()!=review['project_digest'] or source_statuses(project.work.history)!=review['freshness']:
        raise ContractError('Project or manuscript changed; retain input and prepare a fresh comparison')


def proposal_edit(project,entry,item_id):
    """Adapt one retained typed edit, never natural-language advice or create items.

    The owning response controller checks freshness before this adapter is used.
    Scope-local item dependencies continue through the existing selective stage.
    """
    from claimbranch.core.research_schema import normalize
    from claimbranch.core.paper_proposals import ITEM
    from claimbranch.core.canonical import canonical_bytes
    result=entry.get('result')
    if not isinstance(result,dict) or result.get('status')!='ok':raise ContractError('Choose an available checked typed response')
    selected=next((r for r in result.get('items',[]) if r.get('id')==item_id),None)
    if selected is None:raise ContractError('Choose an existing response item')
    selected=normalize(selected,ITEM)
    if selected['action']!='edit' or selected['target_id'] is None:raise ContractError('Create items use the existing selected draft staging path; this editor revises a recorded identity')
    record=editable_record(project,selected['target_id'])
    if selected['kind']!=record['kind']:raise ContractError('AI cannot retag an existing identity; use explicit manual replacement')
    body=deepcopy(selected['body'])
    def reference(r):
        if r['domain']!='context':raise ContractError('Item-local dependencies require selected staging together')
        return r['id']
    for key in ('source_id','target_id','claim_id'):
        if key in body:body[key]=reference(body[key])
    for key in ('parent_ids','observation_ids'):
        if key in body:body[key]=[reference(r) for r in body[key]]
    record['body']=body
    record['title']=(body.get('statement') or body.get('objective') or record['title']).replace('\n',' ')[:240]
    source=dict(request_id=entry['request_id'],response_sha256=hashlib.sha256(canonical_bytes(result)).hexdigest(),
        item_id=item_id,original_item=deepcopy(selected))
    return record,source
