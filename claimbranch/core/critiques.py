"""Private sourced questions and non-empirical associations."""
from copy import deepcopy
from .canonical import ContractError
from .research_schema import ID,TEXT,HASH,array,obj,nullable

ORIGIN={'enum':['human','ai','mixed','unknown']}
OPAQUE={'type':'string','pattern':'^critique-[0-9a-f]{32}$','minLength':41,'maxLength':41}
SOURCE_ID={'type':'string','pattern':'^private-source-[0-9a-f]{32}$','minLength':47,'maxLength':47}
QUESTION=obj(id=OPAQUE,source_id=SOURCE_ID,source_sha256=HASH,source_kind={'enum':['review','colleague','self-audit']},
    question=TEXT,question_origin=ORIGIN,source_origin=ORIGIN)
REVISION=obj(critique_id=OPAQUE,expected_revision_id=ID,question=TEXT,question_origin=ORIGIN,rationale=TEXT)
LINK=obj(id=ID,critique_id=OPAQUE,relation={'enum':['questions','addressed-by']},target_id=ID,consequence_operation_id=nullable(ID),rationale=TEXT)
PAYLOADS={'record-critique':QUESTION,'revise-critique-question':REVISION,'link-critique':LINK}
CAPTURE=obj(source_kind={'enum':['review','colleague','self-audit']},question=TEXT,question_origin=ORIGIN,source_origin=ORIGIN,
    private_original={'type':'string','minLength':1,'maxLength':262144,'x-utf8-maxBytes':262144},private_identity=nullable(TEXT),private_label=nullable(TEXT))
INPUT={'oneOf':[obj(schema={'const':'claimbranch.critique-input/v1'},operation_type={'const':'capture-critique'},payload=CAPTURE),
    *[obj(schema={'const':'claimbranch.critique-input/v1'},operation_type={'const':kind},payload=payload) for kind,payload in PAYLOADS.items() if kind!='record-critique']]}


def apply_critique(state,command):
    from .research_history import _record_ids
    if state['seed']['schema_version'] not in (4,5) or state['active_episode'] is None:raise ContractError('Critiques require an active personal paper episode')
    kind=command['operation_type'];payload=command['payload'];questions=state.setdefault('critiques',{});links=state.setdefault('critique_links',{})
    if kind=='record-critique':
        if len(questions)>=128:raise ContractError(f'capacity critiques: {len(questions)+1} / 128')
        if payload['id'] in _record_ids(state) or payload['source_id'] in _record_ids(state):raise ContractError('Critique/source identity reused')
        record=deepcopy(payload);record.update(created_operation_id=command['id'],revision_id=command['id'],recorded_at=command['created_at'],
            revisions=[],classification='sourced-question-not-empirical-evidence',anonymity_verified=False,resolution='unresolved')
        questions[payload['id']]=record
        origins={payload['question_origin'],payload['source_origin']};key=payload['id']
    elif kind=='revise-critique-question':
        record=questions.get(payload['critique_id'])
        if not record or record['revision_id']!=payload['expected_revision_id']:raise ContractError('Stale or unknown critique question revision')
        if payload['question']==record['question'] and payload['question_origin']==record['question_origin']:raise ContractError('Question revision must change question or declared origin')
        if len(record['revisions'])>=32:raise ContractError(f'capacity critique-revisions: {len(record["revisions"])+1} / 32')
        record['revisions'].append(dict(question=record['question'],question_origin=record['question_origin'],revision_id=record['revision_id'],rationale=record.get('rationale')))
        record.update(question=payload['question'],question_origin=payload['question_origin'],revision_id=command['id'],rationale=payload['rationale'])
        origins={record['source_origin'],payload['question_origin']}|{r['question_origin'] for r in record['revisions']};key=record['id']
    else:
        if len(links)>=512:raise ContractError(f'capacity critique-links: {len(links)+1} / 512')
        if payload['id'] in _record_ids(state):raise ContractError('Critique link identity reused')
        if payload['critique_id'] not in questions:raise ContractError('Unknown critique question')
        main=state['branches']['main'];claims={state['seed']['claim_id']}|{k for k,c in main['changes'].items() if c['kind']=='claim'}
        plans={k for k,c in main['changes'].items() if c['kind']=='experiment-plan'}
        target=payload['target_id'];cause=payload['consequence_operation_id']
        if payload['relation']=='questions':
            if target not in claims or cause is not None:raise ContractError('Questioning references a current claim, never empirical support')
        elif target in plans or target in state['experiments']:
            if cause is not None:raise ContractError('Plan/experiment reference is not a claimed accepted claim change')
        elif target in claims:
            changed=False
            for merge in state['merges']:
                if merge['operation_id']==cause:
                    actual=set(merge['preview']['amendments']['selected'])|set(merge['preview']['amendments']['required'])
                    changed=any(c['id'] in actual and ((c['kind']=='claim' and c['id']==target) or (c['kind']=='claim-status' and c['body']['claim_id']==target)) for c in merge['preview']['changes'])
            if state.get('wording_policies',{}).get(target,{}).get('operation_id')==cause and cause is not None:changed=True
            if not changed:raise ContractError('Claim consequence needs a recorded selected claim/wording change for this target')
        else:raise ContractError('Addressed-by needs a current plan, recorded experiment or exact claim consequence')
        if any(all(old[field]==payload[field] for field in ('critique_id','relation','target_id','consequence_operation_id')) for old in links.values()):raise ContractError('This critique association is already recorded')
        positions=state.get('operation_positions',{})
        capture_position=positions.get(questions[payload['critique_id']]['created_operation_id'])
        consequence_position=positions.get(cause) if cause is not None else None
        timing='existing-record-reference-no-causality-claim' if cause is None else 'change-before-app-capture' if capture_position is not None and consequence_position is not None and consequence_position<capture_position else 'change-after-app-capture' if capture_position is not None and consequence_position is not None else 'unknown'
        links[payload['id']]={**deepcopy(payload),'operation_id':command['id'],'recorded_at':command['created_at'],'scientific':False,'resolved':False,'association_timing':timing,'chronology_verified':False}
        key=payload['critique_id'];record=questions[key];origins={record['source_origin'],record['question_origin']}|{r['question_origin'] for r in record['revisions']}
    for branch in state['branches'].values():branch.setdefault('critique_origins',{})[key]=sorted(origins)
    state['branches']['main']['head']=command['id']


def placeholder_projection(view,public_ids):
    """Default public reference allowlist: no question, origin, raw hash or prose."""
    public={m['private_id']:m['public_id'] for m in public_ids}
    required=set(view.get('critiques',{}))|set(view.get('critique_links',{}))|{l[field] for l in view.get('critique_links',{}).values() for field in ('critique_id','target_id')}
    if not required<=set(public):raise ContractError('Public critique reference mapping is incomplete')
    return dict(schema='claimbranch.private-critique-references/v1',
        placeholders=[dict(id=public[key],kind='private-critique',content='omitted') for key in sorted(view.get('critiques',{}))],
        references=[dict(id=public[key],source_id=public[link['critique_id']],target_id=public[link['target_id']],relation=link['relation'],scientific=False) for key,link in sorted(view.get('critique_links',{}).items())],
        omission=dict(originals=True,identities=True,questions=True,private_paths=True,reasons=True,source_hashes=True),anonymity_verified=False)
