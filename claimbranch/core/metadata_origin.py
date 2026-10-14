"""Declared new-input origin is independent of the confirming human actor."""
from .canonical import ContractError


def retain_origin(state, command):
    origin=command['contribution_origin'];payload=command['payload'];kind=command['operation_type']
    subjects=[]
    if kind=='set-claim-wording':subjects=[payload['claim_id']]
    elif kind=='set-anchor-context':subjects=[payload['anchor_id']]
    elif kind=='record-measurement':
        subjects=[payload['target_id']]
        if payload['table']:subjects.append(payload['table']['id'])
    elif kind=='revise-critique-question':subjects=[payload['critique_id']]
    elif kind=='record-co-report':subjects=[payload['id']]+payload['selected_ids']+[r['edge_id'] for r in payload['candidates'] if r['id'] in payload['selected_ids']]
    elif kind=='declare-condition':subjects=[] # Vocabulary provenance remains inspectable by operation.
    else:subjects=[payload['id']]
    records=state.setdefault('metadata_origins',{})
    if len(records)>=2048:raise ContractError('capacity metadata-origins: 2049 / 2048')
    records[command['id']]=dict(operation_id=command['id'],operation_type=kind,origin=origin,
        subject_ids=subjects,recorded_at=command['created_at'],confirming_actor='human-personal-confirmation',source_fidelity_verified=False)
    records[command['id']]['confirming_actor_verified']=False
    if kind=='declare-condition':records[command['id']]['condition_key']=payload['key']
    for branch in state['branches'].values():
        branch['metadata_origin_uncertain']=any(r['origin']=='unknown' for r in records.values())
    # Explicit origin changes the comparison context even for vocabulary capture.
    state['branches']['main']['head']=command['id']
