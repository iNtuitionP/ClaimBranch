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


# New targets are purpose-bound; the v1 request and command10/12 stay closed.
COMPLETED_PROTOCOL=deepcopy(PROTOCOL)
for _key in ('plan_id','expected_plan_digest'):
    del COMPLETED_PROTOCOL['properties'][_key];COMPLETED_PROTOCOL['required'].remove(_key)
for _key,_schema in dict(experiment_id=ID,expected_experiment_digest=HASH,association_id=ID).items():
    COMPLETED_PROTOCOL['properties'][_key]=_schema;COMPLETED_PROTOCOL['required'].append(_key)


def input_schema(version=1):
    if version==1:return deepcopy(INPUT)
    if version!=2:raise ContractError('Unknown protocol input version')
    from .observation_lineage import REPLACEMENT
    payloads={**PAYLOADS,'register-experiment-protocol':COMPLETED_PROTOCOL,'record-observation-replacement':REPLACEMENT}
    return {'oneOf':[obj(schema={'const':'claimbranch.protocol-input/v2'},operation_type={'const':kind},payload=payload) for kind,payload in payloads.items()]}


def experiment_digest(experiment):
    scientific={key:experiment[key] for key in ('id','question','method','conditions','metric','source_ref')}
    return hashlib.sha256(encode(scientific,purpose='history')).hexdigest()


def target_id(protocol):
    return protocol.get('experiment_id',protocol.get('plan_id'))


def target_matches(state,protocol):
    if 'experiment_id' in protocol:
        target=state['experiments'].get(protocol['experiment_id'])
        return target is not None and experiment_digest(target)==protocol['expected_experiment_digest']
    target=state['branches']['main']['changes'].get(protocol['plan_id'])
    return target is not None and plan_digest(target)==protocol['expected_plan_digest']


def plan_digest(plan):
    scientific={key:plan[key] for key in ('id','kind','body')}
    return hashlib.sha256(encode(scientific,purpose='history')).hexdigest()


def basis_identity(references):
    return sorted((r['observation_id'],r['event_id']) for r in references)


def apply_protocol(state,command):
    from .research_history import _record_ids,_evidence
    if state['seed']['schema_version'] not in (4, 5, 14, 18) or state['active_episode'] is None:raise ContractError('Protocol work requires an active personal paper episode')
    kind=command['operation_type'];payload=command['payload'];key=payload['id'];main=state['branches']['main']
    bucket={'register-protocol':'protocols','register-experiment-protocol':'protocols','associate-experiment':'experiment_associations','amend-gate-rule':'gate_amendments','record-gate-result':'gate_results','record-outcome':'outcome_assessments'}[kind]
    records=state.setdefault(bucket,{})
    if key in _record_ids(state):raise ContractError('Protocol record identity reused or aliases a record')
    if len(records)>=LIMITS[bucket]:raise ContractError(f'capacity {bucket}: {len(records)+1} / {LIMITS[bucket]}')
    record=deepcopy(payload);record.update(operation_id=command['id'],recorded_at=command['created_at'],chronology_verified=False,source_fidelity_verified=False)
    if kind in ('register-protocol','register-experiment-protocol'):
        completed=kind=='register-experiment-protocol'
        plan=state['experiments'].get(payload['experiment_id']) if completed else main['changes'].get(payload['plan_id'])
        if not completed and (not plan or plan['kind']!='experiment-plan'):raise ContractError('Protocol requires a current main experiment plan')
        if completed and not plan:raise ContractError('Protocol requires a recorded completed experiment')
        if not target_matches(state,payload):raise ContractError('Protocol target changed; preview its exact scientific content again' if completed else 'Plan changed; preview the exact registered plan again')
        previous=[p for p in state.get('protocols',{}).values() if target_id(p)==target_id(payload) and ('experiment_id' in p)==completed]
        if payload['supersedes_id']!=(previous[-1]['id'] if previous else None):raise ContractError('Protocol revision must name the latest protocol for this plan')
        ids=[g['id'] for g in payload['gates']]
        if len(set(ids))!=len(ids) or any(g in _record_ids(state) or g==key or (completed and g==payload['association_id']) for g in ids):raise ContractError('Gate identities must be fresh and unique')
        record['experiment_snapshot' if completed else 'plan_snapshot']=deepcopy(plan)
        if completed:
            association_id=payload['association_id']
            if association_id in _record_ids(state) or association_id==key:raise ContractError('Completed association identity must be fresh')
            associations=state.setdefault('experiment_associations',{})
            if len(associations)>=LIMITS['experiment_associations']:raise ContractError('capacity experiment_associations exceeded')
            observations=[e['id'] for e in _evidence(state['events']) if e['run_id']==plan['id']]
            associations[association_id]=dict(id=association_id,protocol_id=key,experiment_id=plan['id'],expected_experiment_digest=payload['expected_experiment_digest'],
                experiment_snapshot=deepcopy(plan),metric_differs_from_registered_plan=None,app_observations_already_recorded=observations,
                app_observations_known_before_registration=observations,preinspection_disclosure_conflict=payload['inspected_before_registration']=='unseen' and bool(observations),
                amendment_disclosure_conflicts=[],rationale=payload['rationale'],operation_id=command['id'],recorded_at=command['created_at'],chronology_verified=False,source_fidelity_verified=False)
        record['observations_known_at_registration']={e['id']:e['run_id'] for e in _evidence(state['events'])}
        associations=state.get('experiment_associations',{})
        prior_runs=({plan['id']} if completed else set())|{a['experiment_id'] for a in associations.values() if a['protocol_id'] in {p['id'] for p in previous}}
        record['app_observations_already_recorded']=[e['id'] for e in _evidence(state['events']) if e['run_id'] in prior_runs]
        record['prior_protocol_ids']=[p['id'] for p in previous]
        if state['seed']['schema_version'] in (5, 14, 18):
            from .argument_import import source_references
            record['source_refs']=source_references(state,main,[] if completed else [plan],target_id(payload))
        else:record['source_refs']=[]
        if completed:
            record['new_input_origin']=command['contribution_origin']
            associations[association_id].update(origin=payload['origin'],new_input_origin=command['contribution_origin'],source_refs=deepcopy(record['source_refs']))
    elif kind=='associate-experiment':
        protocol=state.get('protocols',{}).get(payload['protocol_id'])
        if not protocol:raise ContractError('Unknown registered protocol')
        if 'experiment_id' in protocol and kind=='associate-experiment':raise ContractError('Completed protocol already has its explicit experiment association')
        if any(p['supersedes_id']==protocol['id'] for p in state.get('protocols',{}).values()):raise ContractError('Superseded protocol cannot receive a new association or rule amendment')
        plan=main['changes'].get(protocol['plan_id'])
        if plan is None or payload['expected_plan_digest']!=protocol['expected_plan_digest'] or plan_digest(plan)!=payload['expected_plan_digest']:raise ContractError('Current plan differs from registered rules; explicitly register a new protocol revision')
        if any(a['protocol_id']==protocol['id'] for a in state.get('experiment_associations',{}).values()):raise ContractError('Protocol already has a completed-record association')
        experiment=state['experiments'].get(payload['experiment_id'])
        if not experiment:raise ContractError('Association requires a recorded experiment; this does not execute it')
        record['experiment_snapshot']=deepcopy(experiment)
        if experiment.get('metric') is None or any(value is None for value in experiment['metric'].values()):
            raise ContractError('Experiment metric is not recorded completely; cannot compare it with the registered plan')
        record['metric_differs_from_registered_plan']=experiment['metric']!=plan['body']['metric']
        record['app_observations_already_recorded']=[e['id'] for e in _evidence(state['events']) if e['run_id']==experiment['id']]
        record['app_observations_known_before_registration']=[key for key,run in protocol['observations_known_at_registration'].items() if run==experiment['id']]
        record['preinspection_disclosure_conflict']=protocol['inspected_before_registration']=='unseen' and bool(record['app_observations_known_before_registration'])
        record['amendment_disclosure_conflicts']=[a['id'] for a in state.get('gate_amendments',{}).values() if a['protocol_id']==protocol['id'] and a['decided_after_result']=='before' and any(run==experiment['id'] for run in a['observations_known_at_amendment'].values())]
    elif kind=='amend-gate-rule':
        protocol=state.get('protocols',{}).get(payload['protocol_id'])
        if not protocol:raise ContractError('Unknown registered protocol')
        if any(p['supersedes_id']==protocol['id'] for p in state.get('protocols',{}).values()):raise ContractError('Superseded protocol cannot receive a new association or rule amendment')
        if not target_matches(state,protocol):raise ContractError('Current plan differs from registered rules; explicitly register a new protocol revision')
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
    if kind=='register-experiment-protocol':origins.add(command['contribution_origin'])
    for branch in state['branches'].values():
        branch.setdefault('protocol_origins',{})[key]=sorted(origins)
        if kind=='register-experiment-protocol':branch['protocol_origins'][payload['association_id']]=sorted(origins)
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
    roots={e['id'] for e in view['experiments']}|{c['id'] for c in view['claims']}|set(evidence)|{i['id'] for i in view['interpretations']}|{c['id'] for c in view['experiment_plans']}
    for root in sorted(roots):
        pending=deque([root]);seen=set()
        while pending:
            node=pending.popleft()
            if node in seen:continue
            seen.add(node);pending.extend(incoming.get(node,[]))
        runs={evidence[n]['run_id'] for n in seen if n in evidence}|{e['id'] for e in view['experiments'] if e['id'] in seen}
        selected={a['protocol_id'] for a in associations.values() if a['experiment_id'] in runs}|{p['id'] for p in protocols.values() if target_id(p) in seen}
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
            completed='experiment_id' in protocol
            plan=next((c for c in (view['experiments'] if completed else view['changes']) if c['id']==target_id(protocol)),None)
            amendments=[deepcopy(a) for a in state['gate_amendments'].values() if a['protocol_id']==protocol['id']]
            conflicts={key for a in associations.values() if a['id'] in related for key in a.get('amendment_disclosure_conflicts',[])}
            for amendment in amendments:amendment['later_association_disclosure_conflict']=amendment['id'] in conflicts
            main_digest=view.get('protocol_experiment_digests' if completed else 'protocol_plan_digests',{}).get(target_id(protocol))
            expected=protocol['expected_experiment_digest' if completed else 'expected_plan_digest']
            contexts.append(dict(protocol=deepcopy(protocol),view_plan_matches_registration=None if plan is None else (experiment_digest(plan) if completed else plan_digest(plan))==expected,plan_visibility='not-in-this-reasoning-view' if plan is None else 'available',
                plan_changed_since_registration=None if main_digest is None else main_digest!=expected,
                current_rules=current_rules(state,protocol),original_and_amended_rules=rule_versions(state,protocol),
                associations=[deepcopy(a) for a in associations.values() if a['id'] in related],outcomes=outcomes,gate_results=gates,
                amendments=amendments,
                superseded_by=[p['id'] for p in protocols.values() if p['supersedes_id']==protocol['id']],global_registry=True,
                registry_scope='Global at the requested history prefix; episode views retain current global evidence/rules.',
                confirmatory_provenance='source-claimed' if protocol['inspected_before_registration']=='unseen' else 'exploratory-disclosed' if protocol['inspected_before_registration']=='seen' else 'unknown',chronology_verified=False))
        for context in contexts:
            if 'experiment_id' in context['protocol']:
                context['target_kind']='completed-experiment'
                context['experiment_changed_since_registration']=context.pop('plan_changed_since_registration')
                context['view_experiment_matches_registration']=context.pop('view_plan_matches_registration')
                context['experiment_visibility']=context.pop('plan_visibility')
        result[root]=contexts
    return result
