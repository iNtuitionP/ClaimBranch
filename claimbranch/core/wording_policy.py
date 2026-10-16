"""Human reporting restrictions, distinct from support and understanding."""
from copy import deepcopy
import base64
import hashlib
import re
from .paper_capacity import encode
from .canonical import ContractError
from .research_schema import normalize, REVISION_PAYLOADS


def visible_text(raw):
    """Strip literal comments and their end-of-line; preserve escaped percent."""
    pieces=[];joined=False
    for line in re.findall(r'[^\n]*\n|[^\n]+$',raw.replace('\r\n','\n').replace('\r','\n')):
        if joined:
            # A following physically blank line still starts a TeX paragraph.
            line=('\n' if not line.strip(' \t\r\n') else '')+line.lstrip(' \t')
        joined=False
        for index,char in enumerate(line):
            if char!='%':continue
            slashes=0;previous=index-1
            while previous>=0 and line[previous]=='\\':slashes+=1;previous-=1
            if slashes%2==0:
                line=line[:index];joined=True;break
        pieces.append(line)
    return ''.join(pieces)


def paragraph_count(raw):
    return len([p for p in re.split(r'\n[ \t]*\n',visible_text(raw)) if p.strip(' \t\r\n')])


def anchor_commitment(anchor):
    return hashlib.sha256(encode(anchor,purpose='project')).hexdigest()


def apply_revision(state, command):
    if state['seed']['schema_version'] not in (4, 5, 14, 18):
        raise ContractError('wording restrictions require a personal paper profile')
    kind=command['operation_type']; payload=normalize(command['payload'],REVISION_PAYLOADS[kind],profile='paper')
    text_fields=[payload['rationale']]
    if kind=='set-claim-wording':
        text_fields += [payload['grade'],payload['limitation']]+payload['allowed_wording']+payload['required_caveats']+payload['banned_phrases']
    if any(not value.strip() for value in text_fields):raise ContractError('wording fields cannot be blank')
    main=state['branches']['main']
    claims={state['seed']['claim_id']} | {key for key,item in main['changes'].items() if item['kind']=='claim'}
    observations={event['target_id'] for event in state['events']}
    if kind=='set-claim-wording':
        key=payload['claim_id']; name='wording_policies'; maximum=64
        if key not in claims: raise ContractError('wording target must be a current main claim')
        subjects=[key]
    elif kind=='set-claim-companion':
        key=payload['id'];name='companion_dependencies';maximum=256
        if payload['target_id'] not in claims or payload['companion_id'] not in claims|observations or payload['target_id']==payload['companion_id']:
            raise ContractError('companion needs a main claim and a distinct claim or global observation')
        from .research_history import _record_ids
        if key not in state.get(name,{}) and key in _record_ids(state): raise ContractError('companion identity aliases an existing record')
        old=state.get(name,{}).get(key)
        if old and any(old[field]!=payload[field] for field in ('target_id','companion_id','scope')):
            raise ContractError('companion endpoints/scope are immutable; retire and use a new identity')
        if not old and payload['status']=='retired': raise ContractError('cannot retire an unknown companion')
        subjects=[payload['target_id'],payload['companion_id']]
    else:
        key=payload['anchor_id']; name='anchor_contexts'; maximum=64
        anchor=state.get('manuscript_anchors',{}).get(key)
        if anchor is None: raise ContractError('context needs a registered manuscript anchor')
        raw=b''.join(base64.b64decode(part) for part in anchor['block']).decode('utf-8')
        count=paragraph_count(raw)
        seen=set()
        for paragraph in payload['paragraphs']:
            if paragraph['index'] in seen or paragraph['index']>count:
                raise ContractError('paragraph index is duplicate or outside registered block')
            seen.add(paragraph['index'])
            if not set(paragraph['expresses'])<=set(anchor['expresses']) or not set(paragraph['plots'])<=set(anchor['plots']):
                raise ContractError('paragraph declarations must be covered by anchor associations')
        subjects=[key]
        payload['block_digest']=anchor['block_digest'] # derived binding; not caller authority
        payload['anchor_commitment']=anchor_commitment(anchor)
    current=state.setdefault(name,{})
    if key not in current and len(current)+1>maximum: raise ContractError(f'capacity {name}: {len(current)+1} / {maximum}')
    refs={}
    if state['seed']['schema_version'] in (5, 14, 18):
        from .argument_import import source_references
        for subject in subjects:
            for ref in source_references(state,main,[],subject): refs[ref['record_id']]=ref
    current[key]={**deepcopy(payload),'operation_id':command['id'],'recorded_at':command['created_at'],
        'source_refs':[refs[key] for key in sorted(refs)],'authority':'personal-human-confirmation','coverage':'current-main reporting restriction; not a scientific grade or source verification'}


from .research_schema import obj,ID,HASH,TEXT
WORDING_ACK=obj(id=ID,claim_id=ID,anchor_id=ID,expected_policy_digest=HASH,expected_anchor_digest=HASH,
    rule={'enum':['banned-phrase','caveat-text-not-found']},phrase=TEXT,rationale=TEXT)


def policy_digest(policy):
    return hashlib.sha256(encode(policy,purpose='project')).hexdigest()


def apply_acknowledgement(state,command):
    from .research_history import _record_ids
    payload=command['payload']
    if state['seed']['schema_version'] not in (4,5,14,18) or state['active_episode'] is None:raise ContractError('Wording acknowledgement needs an active personal paper episode')
    records=state.setdefault('wording_acknowledgements',{})
    if payload['id'] in _record_ids(state):raise ContractError('Wording acknowledgement identity reused')
    if len(records)>=128:raise ContractError('capacity wording_acknowledgements: 129 / 128')
    anchor=state.get('manuscript_anchors',{}).get(payload['anchor_id']);policy=state.get('wording_policies',{}).get(payload['claim_id'])
    if not anchor or payload['claim_id'] not in anchor['expresses'] or not policy:raise ContractError('Acknowledgement requires the exact registered anchor and expressed claim policy')
    if payload['expected_anchor_digest']!=anchor_commitment(anchor) or payload['expected_policy_digest']!=policy_digest(policy):raise ContractError('Wording acknowledgement anchor/policy changed; review again')
    phrases=policy['banned_phrases' if payload['rule']=='banned-phrase' else 'required_caveats']
    if payload['phrase'] not in phrases:raise ContractError('Acknowledgement phrase is not a current literal policy rule')
    records[payload['id']]={**deepcopy(payload),'operation_id':command['id'],'recorded_at':command['created_at'],
        'effect':'acknowledged lexical warning only; no scientific authorization or debt closure'}
    state['branches']['main']['head']=command['id']
