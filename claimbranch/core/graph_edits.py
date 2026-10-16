"""Versioned, explicit personal graph revisions. Old commands remain immutable."""
from copy import deepcopy
from .canonical import ContractError


def payload_schema():
    from .research_schema import obj,array,ID,TEXT,nullable,paper_payloads,EXPERIMENT,ANCHOR
    bodies=paper_payloads(4)['record-interpretation']['properties']['changes']['items']['oneOf']
    variants=[v for v in bodies if v['properties']['kind']['const']!='claim-status']
    variants=deepcopy(variants)
    extras={'experiment-record':{k:v for k,v in EXPERIMENT['properties'].items() if k!='id'},
        'observation':dict(statement=TEXT,value=nullable(TEXT)),
        'manuscript-anchor':{k:v for k,v in ANCHOR['properties'].items() if k not in ('id','source','block','block_digest')},
        'thesis':dict(statement=TEXT), 'critique-question':dict(question=TEXT)}
    for kind,fields in extras.items(): variants.append(obj(id=ID,kind={'const':kind},body=obj(**fields)))
    for v in variants:
        v['properties'].update(title={'type':'string','minLength':1,'maxLength':240,'pattern':r'^[^\r\n]+$'},replaces=nullable(ID))
        v['required']+=['title','replaces']
    from .paper_proposals import ITEM
    from .research_schema import HASH
    source=nullable(obj(request_id=ID,response_sha256=HASH,item_id=ID,original_item=ITEM))
    return obj(proposal_source=source,edits=array({'oneOf':variants},32,1),rationale=TEXT,origin={'enum':['human','ai','mixed','unknown']})


def apply_edits(state,cmd):
    from .research_history import _record_ids,_paper_changes,_evidence,_append_evidence,_register_anchor
    if state['seed']['schema_version'] not in (4, 5, 14):raise ContractError('Graph editing requires a personal paper profile')
    if state['active_episode'] is None:raise ContractError('Choose the active episode before editing')
    merged=any(m.get('episode_id')==state['active_episode'] for m in state['merges']) or any(d['episode_id']==state['active_episode'] for d in state.get('co_reports',{}).values())
    if 'alternative' in state['branches'] and not merged:raise ContractError('Finish the current alternative before revising main; your input is retained')
    branch=state['branches']['main'];root=state['seed']['claim_id'];seen=set();edits=cmd['payload']['edits']
    original_ids=_record_ids(state)
    replaceable={root,*state['experiments'],*state.get('manuscript_anchors',{}),*state.get('critiques',{}),*(e['target_id'] for e in state['events']),*(k for k,r in branch['changes'].items() if r['kind'] in ('claim','interpretation','experiment-plan'))}
    revisions=state.setdefault('graph_revisions',[])
    titles=branch.setdefault('titles',{})
    review_subjects={e['id'] for e in edits}
    for edit in edits:
        old=branch['changes'].get(edit['id'],{}).get('body',{})
        for body in (old,edit['body']):
            for field in ('source_id','target_id','claim_id'):
                if field in body:review_subjects.add(body[field])
            review_subjects.update(body.get('parent_ids',[]))
        anchor=state.get('manuscript_anchors',{}).get(edit['id'],{})
        review_subjects.update(anchor.get('expresses',[]))
    for edit in edits:
        key,kind,body=edit['id'],edit['kind'],deepcopy(edit['body'])
        if key in seen:raise ContractError('Select each record once per revision')
        seen.add(key)
        old=branch['changes'].get(key)
        replacing=edit['replaces']
        if replacing is not None:
            if replacing not in replaceable or key in original_ids or key==replacing:
                raise ContractError('Replacement requires an existing original and a distinct fresh identity')
            if kind not in ('claim','interpretation','experiment-plan'):
                raise ContractError('Kind replacement creates reasoning only; use result confirmation for evidence or completed experiments')
        elif kind in ('claim','interpretation','experiment-plan','scientific-edge'):
            if old is None or old['kind']!=kind:raise ContractError('Keep identity kind; choose explicit replacement for a different kind')
        if kind in ('claim','interpretation','experiment-plan','scientific-edge'):
            if any(key in d['candidate_ids']+d['candidate_edge_ids'] for d in state.get('co_reports',{}).values()):
                raise ContractError('Co-reported readings are immutable; create an explicit replacement')
            if kind=='interpretation':
                owner=state['interpretation_owners'].get(key,state['active_episode'])
                if owner!=state['active_episode']:raise ContractError('Earlier interpretation needs an explicit replacement')
                state['interpretation_owners'][key]=state['active_episode']
            branch['changes'][key]=dict(id=key,kind=kind,body=body)
        elif kind=='thesis':
            if key!=root:raise ContractError('Thesis identity is fixed')
            branch['thesis_statement']=body['statement']
        elif kind=='experiment-record':
            if key not in state['experiments']:raise ContractError('Revision requires an existing experiment')
            # Units/metric/conditions govern already measured values. Reinterpretation
            # requires another run/result, never silently reunit existing numbers.
            oldrun=state['experiments'][key]
            if any(e['run_id']==key for e in state['events']) and any(body[f]!=oldrun[f] for f in ('conditions','metric')):
                raise ContractError('Recorded observations bind metric and conditions; create a separate run/result for changed measurement context')
            state['experiments'][key]={**oldrun,**body}
        elif kind=='observation':
            obs=next((r for r in _evidence(state['events']) if r['id']==key),None)
            if obs is None:raise ContractError('Correction needs an existing observation')
            if obs['statement']==body['statement'] and obs.get('value')==body['value']:
                titles[key]=edit['title'];continue
            if body['value'] is None:raise ContractError('A scientific correction requires a measured value; title-only revision leaves evidence unchanged')
            _append_evidence(state,dict(event_id=cmd['id']+'-e'+str(len(seen)),target_id=key,run_id=obs['run_id'],action='correct',
                statement=body['statement'],value=body['value'],rationale=cmd['payload']['rationale'],supersedes_id=obs['history'][-1]['event_id']))
        elif kind=='manuscript-anchor':
            anchor=state.get('manuscript_anchors',{}).get(key)
            if not anchor:raise ContractError('Register the marked source block before editing its associations')
            _register_anchor(state,{**anchor,**body}) # Retains exact source/block; no filesystem writes.
        elif kind=='critique-question':
            record=state.get('critiques',{}).get(key)
            if record is None:raise ContractError('Unknown critique question')
            if record['question']==body['question']:
                titles[key]=edit['title'];continue
            # Reuse the existing revision path including original/source provenance.
            from .critiques import apply_critique
            apply_critique(state,{**cmd,'operation_type':'revise-critique-question','payload':dict(critique_id=key,expected_revision_id=record['revision_id'],question=body['question'],question_origin=cmd['payload']['origin'],rationale=cmd['payload']['rationale'])})
        titles[key]=edit['title']
    _paper_changes(branch,state)
    current=[i for i in branch['changes'].values() if i['kind']=='interpretation' and state['interpretation_owners'].get(i['id'])==state['active_episode']]
    if len(current)>1:raise ContractError('One current interpretation per episode; co-report using the existing reviewed path')
    revisions.append(dict(operation_id=cmd['id'],episode_id=cmd['episode_id'],edits=deepcopy(edits),review_subject_ids=sorted(review_subjects),rationale=cmd['payload']['rationale'],origin=cmd['payload']['origin'],proposal_source=deepcopy(cmd['payload']['proposal_source']),recorded_at=cmd['created_at'],review_required=True))
    # Never reuse a reviewed judgment/consent for changed wording (including titles).
    branch['head']=cmd['id']
    branch['graph_review_required']=True
    origins=state.setdefault('metadata_origins',{})
    origins[cmd['id']]=dict(operation_id=cmd['id'],operation_type='revise-graph',origin=cmd['payload']['origin'],subject_ids=[e['id'] for e in edits],recorded_at=cmd['created_at'],confirming_actor='human-personal-confirmation',confirming_actor_verified=False,source_fidelity_verified=False)
    if len(origins)>2048:raise ContractError('capacity metadata-origins: 2049 / 2048')
    branch['metadata_origin_uncertain']=any(r['origin']=='unknown' for r in origins.values())
