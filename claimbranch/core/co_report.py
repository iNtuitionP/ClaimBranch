"""One explicit personal disposition preserving several scoped readings."""
from .argument_import import reference_origins
from copy import deepcopy
import hashlib
from .canonical import ContractError
from .paper_capacity import encode
from .research_schema import normalize, CO_REPORT
from .review import validate_explanation


def context_digest(state):
    from .research_history import _view
    return hashlib.sha256(encode(_view(state,'main'),purpose='project')).hexdigest()


def apply_co_report(state,command):
    from .research_history import _record_ids,_judgment,_context,_changes,_select,_branch_ai,_branch_uncertain,_evidence
    if state['seed']['schema_version'] not in (4, 5, 14) or state['active_episode'] is None:
        raise ContractError('Co-report requires an active personal paper episode')
    if 'alternative' in state['branches'] or any(m['episode_id']==state['active_episode'] for m in state['merges']) or any(d['episode_id']==state['active_episode'] for d in state.get('co_reports',{}).values()):
        raise ContractError('Co-report needs an episode without a staged alternative or previous selected transaction')
    payload=normalize(command['payload'],CO_REPORT,profile='paper')
    if payload['context_digest']!=context_digest(state):raise ContractError('Co-report context or companion membership changed')
    if payload['id'] in _record_ids(state):raise ContractError('Co-report decision identity reused')
    candidates={r['id']:r for r in payload['candidates']}
    if len(candidates)!=len(payload['candidates']) or not set(payload['selected_ids'])<=set(candidates):raise ContractError('Unique candidates and consistent selected membership required')
    chosen=[candidates[key] for key in sorted(payload['selected_ids'])]
    main=state['branches']['main'];claims={state['seed']['claim_id']}|{key for key,item in main['changes'].items() if item['kind']=='claim'}
    active={o['id'] for o in _evidence(state['events']) if o['status'] in ('confirmed','corrected')}
    used=set(_record_ids(state));used.add(payload['id']);changes=[];origins={};source_refs={}
    for reading in payload['candidates']:
        if reading['id'] in used or reading['edge_id'] in used or reading['id']==reading['edge_id']:raise ContractError('Reading/edge identity aliases an existing record')
        used.update((reading['id'],reading['edge_id']))
    for reading in chosen:
        if reading['claim_id'] not in claims or not set(reading['observation_ids'])<=active:raise ContractError('Selected reading needs a current claim and active global observation basis')
        original=None
        if reading['source_id'] is not None:
            original=main['changes'].get(reading['source_id'])
            if not original or original['kind']!='interpretation':raise ContractError('Original reading must already exist on current main')
        interpretation=dict(id=reading['id'],kind='interpretation',body=dict(statement=reading['statement'],observation_ids=reading['observation_ids']))
        edge=dict(id=reading['edge_id'],kind='scientific-edge',body=dict(source_id=reading['id'],target_id=reading['claim_id'],edge_type=reading['edge_type'],rationale=payload['judgment']['rationale']))
        changes.extend((interpretation,edge))
        refs=[]
        if state['seed']['schema_version'] in (5, 14):
            from .argument_import import source_references
            refs=source_references(state,main,[interpretation,edge],reading['source_id'] or reading['claim_id'])
        inherited=main.get('co_report_origins',{}).get(reading['source_id'],[])
        contributors=set(inherited)|{reading['origin']}|set().union(*(reference_origins(r) for r in refs))
        if original:
            contributors.update(set().union(*(reference_origins(r) for r in main.get('source_lineages',{}).get(reading['source_id'],[]))))
            owner=state['interpretation_owners'].get(reading['source_id'])
            branches=state['episodes'].get(owner,{}).get('branches',state['branches'])
            judgments=[b['judgments'][owner] for b in branches.values() if owner in b.get('judgments',{})]
            if any(_judgment(j,_context(state,owner)).ai_influenced for j in judgments):contributors.add('ai')
            if not judgments and not inherited and not main.get('source_lineages',{}).get(reading['source_id']):contributors.add('unknown')
        origins[reading['id']]=sorted(contributors)
        source_refs[reading['id']]=refs
    targets={r['claim_id'] for r in chosen}
    required={key:d for key,d in state.get('companion_dependencies',{}).items() if d['status']=='active' and d['target_id'] in targets}
    if not required:raise ContractError('Co-report requires a declared active reporting companion; create one first')
    if set(payload['companion_ids'])!=set(required):raise ContractError('Select exactly all active companion dependencies of the chosen target claims')
    for dependency in required.values():
        companion=dependency['companion_id']
        if companion in claims:
            if not any(r['claim_id']==companion for r in chosen):raise ContractError('Required companion reading was omitted or not supplied')
        elif companion not in {o for r in chosen for o in r['observation_ids']}:
            if companion not in active:
                raise ContractError('Required companion observation '+companion+' is inactive; inspect its retained history and explicitly revise or retire dependency '+dependency['id']+' before co-reporting')
            raise ContractError('Required companion observation is absent from the selected basis')
    for reading in chosen:
        if not any(reading['claim_id'] in (d['target_id'],d['companion_id']) for d in required.values()):raise ContractError('Selected reading is outside the declared co-report group')
    judgment=_judgment(payload['judgment'],_context(state))
    inherited_ai=command.get('contribution_origin') in ('ai','mixed','unknown') or any(value in ('ai','mixed','unknown') for values in origins.values() for value in values) or _branch_ai(main,state) or _branch_uncertain(main)
    validate_explanation(judgment,payload['disposition'],tuple(payload['answers']),inherited_ai=inherited_ai)
    all_readings=set(state['interpretation_owners'])|{r['id'] for r in chosen}
    if len(all_readings)>128:raise ContractError(f'capacity interpretations: {len(all_readings)} / 128')
    decisions=state.setdefault('co_reports',{})
    if len(decisions)>=32:raise ContractError(f'capacity co-report decisions: {len(decisions)+1} / 32')
    omitted=[]
    for reading in payload['candidates']:
        if reading['id'] in payload['selected_ids']:continue
        problems=[]
        if reading['claim_id'] not in claims:problems.append('unknown-claim')
        if not set(reading['observation_ids'])<={e['target_id'] for e in state['events']}:problems.append('unknown-observation')
        elif not set(reading['observation_ids'])<=active:problems.append('inactive-observation')
        if reading['source_id'] is not None and main['changes'].get(reading['source_id'],{}).get('kind')!='interpretation':problems.append('unavailable-original-reading')
        omitted.append(dict(candidate=deepcopy(reading),status='unadopted-input-not-science',validation_problems=problems))
    decision=dict(omitted_candidates=omitted,id=payload['id'],episode_id=state['active_episode'],operation_id=command['id'],recorded_at=command['created_at'],
        disposition='co-reported',candidate_ids=sorted(candidates),candidate_edge_ids=sorted(r['edge_id'] for r in payload['candidates']),selected_ids=sorted(payload['selected_ids']),omitted_ids=sorted(set(candidates)-set(payload['selected_ids'])),
        readings=deepcopy(chosen),source_refs=deepcopy(source_refs),reading_origins=deepcopy(origins),
        companion_ids=sorted(required),judgment=deepcopy(payload['judgment']),explanation_disposition=payload['disposition'],answers=deepcopy(payload['answers']),
        manuscript_follow_up='unresolved',origin_review_required=inherited_ai,understanding_verified=False,source_fidelity_verified=False)
    decisions[payload['id']]=decision
    target=deepcopy(main)
    target['changes'].update({c['id']:c for c in changes})
    for reading in chosen:state['interpretation_owners'][reading['id']]=state['active_episode']
    _select(state,_changes(target,state),tuple(c['id'] for c in changes),tuple(sorted(active)))
    target.setdefault('co_report_origins',{}).update(origins)
    if state['seed']['schema_version'] in (5, 14):
        for reading in chosen:
            for key in (reading['id'],reading['edge_id']):target.setdefault('source_lineages',{})[key]=deepcopy(source_refs[reading['id']])
    target.update(head=command['id'],watermark=len(state['events']),judgment=deepcopy(payload['judgment']))
    target['judgments'][state['active_episode']]=deepcopy(payload['judgment'])
    state['branches']['main']=target
