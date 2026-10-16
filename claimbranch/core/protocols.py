"""Personal registered rules and assessments; no evaluator or execution."""
from .argument_import import reference_origins
from copy import deepcopy
import hashlib
from .canonical import ContractError
from .paper_capacity import encode
from .research_schema import ID,TEXT,HASH,array,obj,nullable

ORIGIN={'enum':['human','ai','mixed','unknown']}
BASIS=array(obj(observation_id=ID,event_id=ID),256,1)
GATE=obj(id=ID,name=TEXT,tolerance=TEXT,reference=TEXT)
PROTOCOL=obj(id=ID,plan_id=ID,expected_plan_digest=HASH,supersedes_id=nullable(ID),prediction=TEXT,falsifier=TEXT,
    prewritten_wording=obj(pass_wording=TEXT,fail_wording=TEXT),
    committed_ref=nullable(obj(reference=TEXT,claimed_at=nullable(TEXT))),
    inspected_before_registration={'enum':['seen','unseen','unknown']},origin=ORIGIN,source_context=TEXT,gates=array(GATE,16),rationale=TEXT)
ASSOCIATION=obj(id=ID,protocol_id=ID,experiment_id=ID,expected_plan_digest=HASH,rationale=TEXT)
AMENDMENT=obj(id=ID,protocol_id=ID,gate_id=ID,expected_rule_id=ID,new_tolerance=TEXT,new_reference=TEXT,
    decided_after_result={'enum':['before','after','unknown']},origin=ORIGIN,source_context=TEXT,rationale=TEXT)
GATE_RESULT=obj(id=ID,association_id=ID,gate_id=ID,rule_id=ID,status={'enum':['passed','failed','unknown']},
    observation_revisions=BASIS,source_context=TEXT,origin=ORIGIN,rationale=TEXT)
OUTCOME=obj(id=ID,association_id=ID,rule_ids=array(ID,16,unique=True),gate_result_ids=array(ID,16,unique=True),observation_revisions=BASIS,
    classification={'enum':['consistent','not-consistent','inconclusive','stopped-at-gate']},
    discrimination={'enum':['discriminating','non-discriminating','unknown']},limitations=array(TEXT,16,unique=True),
    source_context=TEXT,origin=ORIGIN,rationale=TEXT)
PAYLOADS={'register-protocol':PROTOCOL,'associate-experiment':ASSOCIATION,'amend-gate-rule':AMENDMENT,'record-gate-result':GATE_RESULT,'record-outcome':OUTCOME}
INPUT={'oneOf':[obj(schema={'const':'claimbranch.protocol-input/v1'},operation_type={'const':kind},payload=payload) for kind,payload in PAYLOADS.items()]}
LIMITS={'protocols':128,'experiment_associations':128,'gate_amendments':256,'gate_results':512,'outcome_assessments':256}


def plan_digest(plan):
    scientific={key:plan[key] for key in ('id','kind','body')}
    return hashlib.sha256(encode(scientific,purpose='history')).hexdigest()


def basis_identity(references):
    return sorted((r['observation_id'],r['event_id']) for r in references)


def apply_protocol(state,command):
    from .research_history import _record_ids,_evidence
    if state['seed']['schema_version'] not in (4, 5, 14) or state['active_episode'] is None:raise ContractError('Protocol work requires an active personal paper episode')
    kind=command['operation_type'];payload=command['payload'];key=payload['id'];main=state['branches']['main']
    bucket={'register-protocol':'protocols','associate-experiment':'experiment_associations','amend-gate-rule':'gate_amendments','record-gate-result':'gate_results','record-outcome':'outcome_assessments'}[kind]
    records=state.setdefault(bucket,{})
    if key in _record_ids(state):raise ContractError('Protocol record identity reused or aliases a record')
    if len(records)>=LIMITS[bucket]:raise ContractError(f'capacity {bucket}: {len(records)+1} / {LIMITS[bucket]}')
    record=deepcopy(payload);record.update(operation_id=command['id'],recorded_at=command['created_at'],chronology_verified=False,source_fidelity_verified=False)
    if kind=='register-protocol':
        plan=main['changes'].get(payload['plan_id'])
        if not plan or plan['kind']!='experiment-plan':raise ContractError('Protocol requires a current main experiment plan')
        if payload['expected_plan_digest']!=plan_digest(plan):raise ContractError('Plan changed; preview the exact registered plan again')
        previous=[p for p in state.get('protocols',{}).values() if p['plan_id']==payload['plan_id']]
        if payload['supersedes_id']!=(previous[-1]['id'] if previous else None):raise ContractError('Protocol revision must name the latest protocol for this plan')
        ids=[g['id'] for g in payload['gates']]
        if len(set(ids))!=len(ids) or any(g in _record_ids(state) or g==key for g in ids):raise ContractError('Gate identities must be fresh and unique')
        record['plan_snapshot']=deepcopy(plan)
        record['observations_known_at_registration']={e['id']:e['run_id'] for e in _evidence(state['events'])}
        associations=state.get('experiment_associations',{})
        prior_runs={a['experiment_id'] for a in associations.values() if a['protocol_id'] in {p['id'] for p in previous}}
        record['app_observations_already_recorded']=[e['id'] for e in _evidence(state['events']) if e['run_id'] in prior_runs]
        record['prior_protocol_ids']=[p['id'] for p in previous]
        if state['seed']['schema_version'] in (5, 14):
            from .argument_import import source_references
            record['source_refs']=source_references(state,main,[plan],payload['plan_id'])
        else:record['source_refs']=[]
    elif kind=='associate-experiment':
        protocol=state.get('protocols',{}).get(payload['protocol_id'])
        if not protocol:raise ContractError('Unknown registered protocol')
        if any(p['supersedes_id']==protocol['id'] for p in state.get('protocols',{}).values()):raise ContractError('Superseded protocol cannot receive a new association or rule amendment')
        plan=main['changes'].get(protocol['plan_id'])
        if plan is None or payload['expected_plan_digest']!=protocol['expected_plan_digest'] or plan_digest(plan)!=payload['expected_plan_digest']:raise ContractError('Current plan differs from registered rules; explicitly register a new protocol revision')
        if any(a['protocol_id']==protocol['id'] for a in state.get('experiment_associations',{}).values()):raise ContractError('Protocol already has a completed-record association')
        experiment=state['experiments'].get(payload['experiment_id'])
        if not experiment:raise ContractError('Association requires a recorded experiment; this does not execute it')
        record['experiment_snapshot']=deepcopy(experiment)
        record['metric_differs_from_registered_plan']=experiment['metric']!=plan['body']['metric']
        record['app_observations_already_recorded']=[e['id'] for e in _evidence(state['events']) if e['run_id']==experiment['id']]
        record['app_observations_known_before_registration']=[key for key,run in protocol['observations_known_at_registration'].items() if run==experiment['id']]
        record['preinspection_disclosure_conflict']=protocol['inspected_before_registration']=='unseen' and bool(record['app_observations_known_before_registration'])
        record['amendment_disclosure_conflicts']=[a['id'] for a in state.get('gate_amendments',{}).values() if a['protocol_id']==protocol['id'] and a['decided_after_result']=='before' and any(run==experiment['id'] for run in a['observations_known_at_amendment'].values())]
    elif kind=='amend-gate-rule':
        protocol=state.get('protocols',{}).get(payload['protocol_id'])
        if not protocol:raise ContractError('Unknown registered protocol')
        if any(p['supersedes_id']==protocol['id'] for p in state.get('protocols',{}).values()):raise ContractError('Superseded protocol cannot receive a new association or rule amendment')
        plan=main['changes'].get(protocol['plan_id'])
        if plan is None or plan_digest(plan)!=protocol['expected_plan_digest']:raise ContractError('Current plan differs from registered rules; explicitly register a new protocol revision')
        record['observations_known_at_amendment']={e['id']:e['run_id'] for e in _evidence(state['events'])}
        rule=current_rules(state,protocol).get(payload['gate_id'])
        if not rule or rule['id']!=payload['expected_rule_id']:raise ContractError('Stale or unknown gate rule revision')
        if (payload['new_tolerance'],payload['new_reference'])==(rule['tolerance'],rule['reference']):raise ContractError('Rule amendment must change tolerance or reference')
        record['before_rule']=deepcopy(rule);record['decision_id']=command['id']
        associated={a['id'] for a in state.get('experiment_associations',{}).values() if a['protocol_id']==protocol['id']}
        observed=any(r['association_id'] in associated for r in state.get('gate_results',{}).values()) or any(r['association_id'] in associated for r in state.get('outcome_assessments',{}).values())
        associated_runs={a['experiment_id'] for a in state.get('experiment_associations',{}).values() if a['id'] in associated}
        observed|=any(e['run_id'] in associated_runs for e in state['events'])
        record['app_result_precedes_amendment']=observed
        record['chronology_conflict']=observed and payload['decided_after_result']=='before'
    else:
        association=state.get('experiment_associations',{}).get(payload['association_id'])
        if not association:raise ContractError('Assessment requires an explicit completed-record association')
        protocol=state['protocols'][association['protocol_id']]
        observations={o['id']:o for o in _evidence(state['events'])};basis=payload['observation_revisions']
        if len({r['observation_id'] for r in basis})!=len(basis):raise ContractError('Unique observation revision basis required')
        for reference in basis:
            observation=observations.get(reference['observation_id'])
            if not observation or observation['run_id']!=association['experiment_id'] or observation['status'] not in ('confirmed','corrected') or observation['history'][-1]['event_id']!=reference['event_id']:raise ContractError('Assessment requires current active observations from the associated experiment')
        record['observation_snapshots']=[deepcopy(observations[r['observation_id']]) for r in basis]
        versions=rule_versions(state,protocol)
        if kind=='record-gate-result':
            rule=versions.get(payload['rule_id'])
            if not rule or rule['gate_id']!=payload['gate_id']:raise ContractError('Gate result must name its exact protocol gate and rule version')
            record['rule_snapshot']=deepcopy(rule)
        else:
            selected=[versions.get(r) for r in payload['rule_ids']]
            if any(r is None for r in selected) or {r['gate_id'] for r in selected}!={g['id'] for g in protocol['gates']} or len(selected)!=len(protocol['gates']):raise ContractError('Outcome must name exactly one rule version for every registered gate')
            gates=[state.get('gate_results',{}).get(r) for r in payload['gate_result_ids']]
            if any(r is None or r['association_id']!=association['id'] or r['rule_id'] not in payload['rule_ids'] or basis_identity(r['observation_revisions'])!=basis_identity(basis) for r in gates):raise ContractError('Outcome gate results must share its exact association, rules and evidence basis')
            if len({r['gate_id'] for r in gates})!=len(gates):raise ContractError('Select one assessment per gate; retain other attempts in history')
            if payload['classification']=='stopped-at-gate' and not any(g['status']=='failed' for g in gates):raise ContractError('Stopped-at-gate requires a recorded failed gate on this basis')
            if payload['discrimination']=='non-discriminating' and not payload['limitations']:raise ContractError('Non-discriminating outcome needs its reported limitation')
            record['rule_snapshots']=deepcopy(selected)
            missing=sorted({g['id'] for g in protocol['gates']}-{g['gate_id'] for g in gates})
            record['unassessed_gate_ids']=missing
            record['gate_validity']='failed-gate' if any(g['status']=='failed' for g in gates) else 'incomplete-gate-assessment' if missing else 'unknown-gate-result' if any(g['status']=='unknown' for g in gates) else 'reported-gates-passed' if gates else 'no-gates-declared'
            record['validity_verified']=False
    records[key]=record
    origins={record.get('origin',command.get('contribution_origin','human'))}|set().union(*(reference_origins(ref) for ref in record.get('source_refs',[])))
    for branch in state['branches'].values():branch.setdefault('protocol_origins',{})[key]=sorted(origins)
    # A rule/assessment changes review context without rewriting values or claim status.
    main['head']=command['id']


def rule_versions(state,protocol):
    versions={g['id']:dict(id=g['id'],gate_id=g['id'],name=g['name'],tolerance=g['tolerance'],reference=g['reference'],kind='registered-original') for g in protocol['gates']}
    for amendment in state.get('gate_amendments',{}).values():
        if amendment['protocol_id']==protocol['id']:
            versions[amendment['id']]=dict(id=amendment['id'],gate_id=amendment['gate_id'],name=versions[amendment['expected_rule_id']]['name'],tolerance=amendment['new_tolerance'],reference=amendment['new_reference'],kind='amended',decision_id=amendment['decision_id'],decided_after_result=amendment['decided_after_result'],app_result_precedes_amendment=amendment['app_result_precedes_amendment'],chronology_conflict=amendment['chronology_conflict'])
    return versions


def current_rules(state,protocol):
    result={}
    for rule in rule_versions(state,protocol).values():result[rule['gate_id']]=rule
    return result


def protocol_context(view):
    """Derived dependent-path context; never a truth/confirmatory verdict."""
    from collections import deque
    protocols=view.get('protocols',{});associations=view.get('experiment_associations',{})
    if not protocols:return {}
    state={name:view.get(name,{}) for name in LIMITS}
    evidence={o['id']:o for o in view['evidence']};incoming={}
    for change in view['changes']:
        body=change['body']
        if change['kind']=='scientific-edge':incoming.setdefault(body['target_id'],[]).append(body['source_id'])
        elif change['kind']=='interpretation':incoming.setdefault(change['id'],[]).extend(body['observation_ids'])
        elif change['kind']=='experiment-plan':incoming.setdefault(body['claim_id'],[]).append(change['id'])
    result={}
    roots={c['id'] for c in view['claims']}|set(evidence)|{i['id'] for i in view['interpretations']}|{c['id'] for c in view['experiment_plans']}
    for root in sorted(roots):
        pending=deque([root]);seen=set()
        while pending:
            node=pending.popleft()
            if node in seen:continue
            seen.add(node);pending.extend(incoming.get(node,[]))
        runs={evidence[n]['run_id'] for n in seen if n in evidence}
        selected={a['protocol_id'] for a in associations.values() if a['experiment_id'] in runs}|{p['id'] for p in protocols.values() if p['plan_id'] in seen}
        if not selected:continue
        contexts=[]
        for protocol in protocols.values():
            if protocol['id'] not in selected:continue
            related={a['id'] for a in associations.values() if a['protocol_id']==protocol['id']}
            outcomes=[deepcopy(o) for o in state['outcome_assessments'].values() if o['association_id'] in related]
            gates=[deepcopy(g) for g in state['gate_results'].values() if g['association_id'] in related]
            for assessment in outcomes+gates:
                assessment['rule_differs_from_current']=any(rule_id not in {r['id'] for r in current_rules(state,protocol).values()} for rule_id in assessment.get('rule_ids',[assessment.get('rule_id')]))
                assessment['basis_stale']=any(r['observation_id'] not in evidence or evidence[r['observation_id']]['history'][-1]['event_id']!=r['event_id'] or evidence[r['observation_id']]['status'] not in ('confirmed','corrected') for r in assessment['observation_revisions'])
            plan=next((c for c in view['changes'] if c['id']==protocol['plan_id']),None)
            amendments=[deepcopy(a) for a in state['gate_amendments'].values() if a['protocol_id']==protocol['id']]
            conflicts={key for a in associations.values() if a['id'] in related for key in a.get('amendment_disclosure_conflicts',[])}
            for amendment in amendments:amendment['later_association_disclosure_conflict']=amendment['id'] in conflicts
            main_digest=view.get('protocol_plan_digests',{}).get(protocol['plan_id'])
            contexts.append(dict(protocol=deepcopy(protocol),view_plan_matches_registration=None if plan is None else plan_digest(plan)==protocol['expected_plan_digest'],plan_visibility='not-in-this-reasoning-view' if plan is None else 'available',
                plan_changed_since_registration=None if main_digest is None else main_digest!=protocol['expected_plan_digest'],
                current_rules=current_rules(state,protocol),original_and_amended_rules=rule_versions(state,protocol),
                associations=[deepcopy(a) for a in associations.values() if a['id'] in related],outcomes=outcomes,gate_results=gates,
                amendments=amendments,
                superseded_by=[p['id'] for p in protocols.values() if p['supersedes_id']==protocol['id']],global_registry=True,
                registry_scope='Global at the requested history prefix; episode views retain current global evidence/rules.',
                confirmatory_provenance='source-claimed' if protocol['inspected_before_registration']=='unseen' else 'exploratory-disclosed' if protocol['inspected_before_registration']=='seen' else 'unknown',chronology_verified=False))
        result[root]=contexts
    return result
