"""Explicit result replacement context, never an evidence/status transition."""
from copy import deepcopy
from datetime import date, datetime
import hashlib

from .canonical import ContractError
from .research_schema import ID,TEXT,obj

ORIGIN={'enum':['human','ai','mixed','unknown']}
REPLACEMENT=obj(id=ID,previous_id=ID,replacement_id=ID,expected_previous_event_id=ID,
    expected_replacement_event_id=ID,origin=ORIGIN,source_context=TEXT,rationale=TEXT)
LIMIT=512


def chronology(previous,replacement):
    """Only compare like precision; never synthesize midnight for a calendar day."""
    if previous is None or replacement is None:return 'unknown'
    try:
        if len(previous)==len(replacement)==10:
            left,right=date.fromisoformat(previous),date.fromisoformat(replacement)
        elif len(previous)>10 and len(replacement)>10:
            left,right=datetime.fromisoformat(previous.replace('Z','+00:00')),datetime.fromisoformat(replacement.replace('Z','+00:00'))
            if left.tzinfo is None or right.tzinfo is None:return 'unknown'
        else:return 'unknown'
    except (ValueError,TypeError):raise ContractError('Replacement chronology requires a real recorded calendar date')
    if right<left:raise ContractError('Replacement observation predates its previous observation')
    return 'same-recorded-time' if right==left else 'source-claimed-order'


def validate_link(records,previous,replacement):
    if previous==replacement:raise ContractError('Replacement cannot refer to itself')
    if len(records)>=LIMIT:raise ContractError(f'capacity observation_replacements: {len(records)+1} / {LIMIT}')
    if any(r['previous_id']==previous for r in records.values()):raise ContractError('Previous observation already has an explicit replacement')
    # Directed previous -> replacement: a later link may extend, never loop.
    pending=[replacement];seen=set()
    while pending:
        node=pending.pop()
        if node==previous:raise ContractError('Observation replacement cycle')
        if node in seen:continue
        seen.add(node);pending.extend(r['replacement_id'] for r in records.values() if r['previous_id']==node)


def imported_links(value,aliases):
    """Validate the entire declared input before any compact state/save exists."""
    by_id={r['id']:r for r in value['records']};links={}
    for index,record in enumerate(value['records']):
        declaration=record.get('replacement')
        if declaration is None:continue
        old=by_id.get(declaration['previous_id'])
        if record['kind']!='observation' or not old or old['kind']!='observation':raise ContractError(f'/records/{index}/replacement/previous_id: both endpoints must be observations')
        previous,replacement=aliases[old['id']],aliases[record['id']]
        validate_link(links,previous,replacement)
        order=chronology(old['recorded_at'],record['recorded_at'])
        key='replacement-'+hashlib.sha256((previous+'\x00'+replacement).encode()).hexdigest()[:32]
        if key in set(aliases.values()):raise ContractError('Imported replacement identity aliases a scientific record')
        links[key]=dict(id=key,previous_id=previous,replacement_id=replacement,**{k:deepcopy(declaration[k]) for k in ('origin','source_context','rationale')},
            source_pointer=f'/records/{index}/replacement',unresolved_source_fields=1,recorded_at=record['recorded_at'],chronology=order,
            chronology_verified=False,source_fidelity_verified=False,origin_kind='imported-declaration')
    return links


def initialize(state):
    from .argument_import_v2 import _source_version,unpack_snapshot
    from .paper_capacity import decode,encode
    from .historical_argument import identities
    if state['seed']['schema_version']!=18 or _source_version(encode(state['seed'],purpose='history'))!=5:return
    value=decode(unpack_snapshot(state['seed']['initial_argument']['snapshot']),purpose='project')
    links=imported_links(value,identities(value['records']))
    observations={e['target_id']:e for e in state['events']}
    for key,link in links.items():
        if link['replacement_id'] not in observations:continue
        if link['previous_id'] not in observations:raise ContractError('Imported replacement previous observation omitted')
        from .research_history import _record_ids
        if key in _record_ids(state):raise ContractError('Imported replacement identity aliases an existing record')
        link.update(previous_event_id=observations[link['previous_id']]['event_id'],replacement_event_id=observations[link['replacement_id']]['event_id'])
        state.setdefault('observation_replacements',{})[key]=link


def apply_replacement(state,command):
    from .research_history import _record_ids,_evidence
    if state['seed']['schema_version'] not in (4,5,14,18) or state['active_episode'] is None:raise ContractError('Replacement review requires an active personal paper episode')
    payload=command['payload'];records=state.setdefault('observation_replacements',{})
    if payload['id'] in _record_ids(state):raise ContractError('Replacement identity already exists')
    observations={o['id']:o for o in _evidence(state['events'])}
    for field in ('previous','replacement'):
        observation=observations.get(payload[field+'_id'])
        if observation is None:raise ContractError(field+'_id: unknown observation')
        if observation['history'][-1]['event_id']!=payload['expected_'+field+'_event_id']:raise ContractError(field+'_id: observation changed; review again')
    validate_link(records,payload['previous_id'],payload['replacement_id'])
    originals={r['id']:r for r in state['seed'].get('initial_argument',{}).get('records',[])}
    order=chronology(originals.get(payload['previous_id'],{}).get('recorded_at'),originals.get(payload['replacement_id'],{}).get('recorded_at'))
    record=dict(deepcopy(payload),new_input_origin=command['contribution_origin'],recorded_at=command['created_at'],operation_id=command['id'],chronology=order,chronology_verified=False,source_fidelity_verified=False,origin_kind='personal-declaration')
    if state['seed']['schema_version'] in (5,14,18):
        from .argument_import import source_references
        record['source_refs']=source_references(state,state['branches']['main'],[],payload['previous_id'])+source_references(state,state['branches']['main'],[],payload['replacement_id'])
    records[payload['id']]=record
    from .argument_import import reference_origins
    origins={payload['origin'],command['contribution_origin']}
    for reference in record.get('source_refs',[]):origins.update(reference_origins(reference))
    for branch in state['branches'].values():branch.setdefault('protocol_origins',{})[payload['id']]=sorted(origins)
    # Context changed; no evidence event or eligibility/status mutation occurs.
    state['branches']['main']['head']=command['id']


def context(view):
    links=view.get('observation_replacements',{})
    if not links:return {}
    incoming={}
    for change in view['changes']:
        body=change['body']
        if change['kind']=='scientific-edge':incoming.setdefault(body['target_id'],set()).add(body['source_id'])
        elif change['kind']=='interpretation':incoming.setdefault(change['id'],set()).update(body['observation_ids'])
    evidence={o['id']:o for o in view['evidence']};result={}
    for root in set(evidence)|{c['id'] for c in view['claims']}|{i['id'] for i in view['interpretations']}:
        pending=[root];seen=set()
        while pending:
            node=pending.pop()
            if node in seen:continue
            seen.add(node);pending.extend(incoming.get(node,()))
        relevant=[deepcopy(r) for r in links.values() if {r['previous_id'],r['replacement_id']}&seen]
        if relevant:
            for link in relevant:
                link['status_effect']='none; separate evidence review required'
                link['basis_changed']=any(evidence[key]['history'][-1]['event_id']!=link.get('expected_'+field+'_event_id',link.get(field+'_event_id')) for field,key in (('previous',link['previous_id']),('replacement',link['replacement_id'])))
            result[root]=relevant
    return result


def imported_reference(state,link):
    label=link['origin'];flags={'human':label in ('human','mixed'),'ai':label in ('ai','mixed'),'unknown':label=='unknown'}
    return dict(schema='claimbranch.imported-source-reference/v2',record_id=link['id'],source_sha256=state['seed']['initial_argument']['source_sha256'],
        contributor=label,origin_flags=flags,unresolved_count=1,source_digest_scope='argument-envelope/v2')
