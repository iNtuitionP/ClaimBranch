"""Explicit personal table review and read-only condition/artifact queries."""
import hashlib
import json
import os
import secrets
import stat
import sys
from datetime import datetime,timezone
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from claimbranch.core.research_schema import normalize
from claimbranch.core.typed_observations import INPUT
from .paper_work_store import PaperWork
from .manuscript_anchors import source_statuses


def current_source(project):
    from .project_work import _source,_path
    source=decode(project.payload,purpose='project')['associations'][-1]
    try:return dict(source=_source(_path(source['root']),_path(source['manuscript'],relative=True),source['anchor_id']),status='available')
    except (ContractError,OSError):return dict(source=None,status='unavailable-or-unsupported')


def prepare_measurement(project,request,*,contribution_origin=None):
    from .paper_service import PaperService
    history=project.work.history
    if history.schema_version not in (4,5):raise ContractError('Structured measurements require a personal paper profile')
    request=normalize(request,INPUT,profile='paper');view=history.view('main')
    if view['episode_id'] is None:raise ContractError('Open a question before measurement review')
    command=dict(schema_version=9,id='measurement-'+secrets.token_hex(12),project_id=project.project_id,episode_id=view['episode_id'],
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),operation_type=request['operation_type'],
        expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=request['payload'])
    from .metadata_batch import origin_command
    command=origin_command(command,contribution_origin)
    candidate=history.append(command);workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);selected=request['payload'].get('target_id',app.selected_id)
        _install(app,candidate,app.episode_id,app.ref,selected);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    before=PaperService(history).query('main');after=PaperService(candidate).query('main')
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=command,before=before,after=after,
        impact=PaperService(candidate).anchor_impact([request['payload']['target_id']]) if 'target_id' in request['payload'] else None,
        freshness=source_statuses(history),source_binding=current_source(project),artifact_fidelity_verified=False,write_available=False,protected_approval=False)


def recheck_measurement(project,preview):
    if hashlib.sha256(project.payload).hexdigest()!=preview['project_digest'] or source_statuses(project.work.history)!=preview['freshness'] or current_source(project)!=preview['source_binding']:
        raise ContractError('Measurement review changed; preview again')


def check_artifact(history,observation_id,artifact_id,path,cell_id):
    """One explicit file and pointer; no traversal of linked sources or write."""
    observation=next((o for o in history.view('main')['evidence'] if o['id']==observation_id),None)
    if not observation or 'measurement' not in observation:raise ContractError('Unknown structured observation')
    table=observation['measurement'];reference=next((r for r in table['artifact_refs'] if r['id']==artifact_id),None)
    cell=next((c for row in table['rows'] for c in row['cells'] if c['id']==cell_id),None)
    if reference is None or cell is None:raise ContractError('Unknown declared artifact or cell')
    result=dict(observation_id=observation_id,measurement_revision=observation['measurement_revision'],artifact_id=artifact_id,cell_id=cell_id,
        declared_path=reference['path'],selected_path=str(path),scientific_validity_verified=False,write_available=False)
    fd=parent=None
    try:
        # Walk without resolving symlinks; an explicit path is not permission to follow substitutions.
        selected=Path(os.path.abspath(path));parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
        for component in selected.parts[1:-1]:
            nxt=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);os.close(parent);parent=nxt
        fd=os.open(selected.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>1048576:raise ContractError('Artifact must be one bounded regular file, at most 1 MiB')
        raw=b''
        while len(raw)<=1048576:
            part=os.read(fd,min(65536,1048577-len(raw)))
            if not part:break
            raw+=part
        after=os.fstat(fd);named=os.stat(selected.name,dir_fd=parent,follow_symlinks=False)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if len(raw)>1048576 or stamp(before)!=stamp(after) or stamp(after)!=stamp(named):raise ContractError('Artifact changed during reading')
        digest=hashlib.sha256(raw).hexdigest();result['actual_sha256']=digest
        if digest!=reference['sha256']:return {**result,'status':'hash-mismatch','value_matches':False}
        def pairs(items):
            value={}
            for key,item in items:
                if key in value:raise ContractError('Duplicate artifact JSON key')
                value[key]=item
            return value
        def refuse(value):raise ContractError('Nonfinite artifact number')
        value=json.loads(raw,parse_float=Decimal,parse_int=int,parse_constant=refuse,object_pairs_hook=pairs)
        def bound(value,depth=0):
            if depth>16:raise ContractError('Artifact JSON depth exceeds 16')
            if type(value) in (list,dict):
                if len(value)>2048:raise ContractError('Artifact JSON collection exceeds 2048')
                for child in value.values() if type(value) is dict else value:bound(child,depth+1)
        bound(value)
        for token in reference['json_pointer'].split('/')[1:]:
            token=token.replace('~1','/').replace('~0','~')
            if type(value) is list:
                if not token.isascii() or not token.isdigit() or (len(token)>1 and token[0]=='0'):raise ContractError('Invalid JSON array pointer')
                value=value[int(token)]
            elif type(value) is dict:value=value[token]
            else:raise ContractError('JSON pointer traverses a scalar')
        expected=cell['value'];kind=expected['type']
        if kind=='decimal':matches=type(value) in (int,Decimal) and Decimal(value)==Decimal(expected['value'])
        elif kind=='integer':matches=type(value) is int and value==int(expected['value'])
        elif kind=='text':matches=type(value) is str and value==expected['value']
        else:matches=value is None
        return {**result,'status':'hash-and-cell-match' if matches else 'cell-mismatch','value_matches':matches,
            'coverage':'Only the named file hash and one cell pointer; units, estimand, conditions and scientific fidelity unverified.'}
    except (OSError,ValueError,KeyError,IndexError,RecursionError,ContractError) as error:
        return {**result,'status':'unavailable-or-unsupported','reason':str(error),'value_matches':False}
    finally:
        if fd is not None:os.close(fd)
        if parent is not None:os.close(parent)


def run_measurement_command(args):
    from .personal_project import PersonalProjectStore
    from .project_commands import _read_argument_input
    from .tui_model import clean
    with PersonalProjectStore(args.directory) as store:
        project=store.load()
        if args.project_action=='observations':
            def pairs(items):
                values={}
                for item in items:
                    if '=' not in item:raise ContractError('Use KEY=VALUE for condition/group selectors')
                    key,value=item.split('=',1)
                    if not key or not value or key in values:raise ContractError('Nonempty unique KEY=VALUE selectors required')
                    values[key]=value
                return values
            groups=pairs(args.group);filters=[]
            for key,value in pairs(args.condition).items():
                if value in ('max','min'):
                    if key not in groups:raise ContractError('min/max requires --group KEY=DECLARED_GROUP; no inferred maximum')
                    filters.append(dict(key=key,group=groups.pop(key),extreme='maximum' if value=='max' else 'minimum'))
                else:filters.append(dict(key=key,value=value))
            if groups:raise ContractError('Every --group must belong to a min/max selector')
            result=condition_query(project.work.history,args.claim,filters)
        elif args.project_action=='artifact-check':result=check_artifact(project.work.history,args.observation,args.artifact,args.path,args.cell)
        else:
            raw=_read_argument_input(args.input);request=decode(raw,purpose='project');candidate,result=prepare_measurement(project,request,contribution_origin=args.origin)
            if not args.dry_run:
                if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Measurement recording requires an interactive terminal; use --dry-run')
                lines=clean(json.dumps(result,ensure_ascii=False,indent=2)).splitlines()
                for start in range(0,len(lines),60):
                    print('\n'.join(lines[start:start+60]),flush=True)
                    if start+60<len(lines) and input('Enter: next page / q: cancel: ').strip().lower()=='q':return 0
                if input('Type record to save this measurement operation, or Enter to cancel: ').strip()!='record':return 0
                if _read_argument_input(args.input)!=raw:raise ContractError('Measurement input changed; preview again')
                recheck_measurement(store.load(),result);store.verify_unchanged();recheck_measurement(project,result);store.save(candidate)
                print('Measurement operation saved. Earlier evidence retained; manuscript unchanged.');return 0
        print(clean(json.dumps(result,ensure_ascii=False,indent=2)))
    return 0

def condition_query(history,claim_id,filters,*,ref='main'):
    """Explicit equality / declared-group extrema; supporting paths, never scope edits."""
    from collections import deque
    from claimbranch.application.paper_service import PaperService
    view=history.view(ref);vocabulary=view.get('condition_vocabulary',{})
    if claim_id not in {c['id'] for c in view['claims']}:raise ContractError('Unknown claim in this reasoning view')
    selected={}
    for condition in filters:
        key=condition['key']
        if key in selected or key not in vocabulary:raise ContractError('Unique declared query condition required')
        if set(condition)=={'key','value'}:
            value=condition['value']
            if value not in vocabulary[key]['values']:raise ContractError('Query value is not declared')
        elif set(condition)=={'key','group','extreme'} and condition['extreme'] in ('minimum','maximum'):
            groups={g['id']:g['ascending_values'] for g in vocabulary[key]['groups']}
            if condition['group'] not in groups:raise ContractError('Extrema require an explicitly declared condition group')
            value=groups[condition['group']][0 if condition['extreme']=='minimum' else -1]
        else:raise ContractError('Invalid condition selector; no inferred maximum')
        selected[key]=value
    graph=PaperService(history).query(ref);back={};interpretations={i['id']:i['body']['observation_ids'] for i in view['interpretations']}
    for edge in graph['relations']:
        if edge['scientific'] and edge['type']=='supports':back.setdefault(edge['target_id'],[]).append(edge['source_id'])
    pending=deque([(claim_id,[claim_id])]);seen=set();basis=set();paths={}
    observations={o['id']:o for o in view['evidence']}
    while pending:
        key,path=pending.popleft()
        if key in seen:continue
        seen.add(key)
        if key in observations:
            basis.add(key);paths.setdefault(key,path)
        if key in interpretations:
            basis.update(interpretations[key])
            for observation in interpretations[key]:paths.setdefault(observation,[*path,observation])
        pending.extend((source,[*path,source]) for source in back.get(key,[]))
    results=[];coverage={};unstructured=[];inactive=[]
    for key in sorted(basis):
        observation=observations[key]
        if observation['status'] not in ('confirmed','corrected'):inactive.append(key);continue
        table=observation.get('measurement')
        if table is None:unstructured.append(key);continue
        defaults={c['key']:c['value'] for c in table['conditions']};matched=[]
        for row in table['rows']:
            conditions={**defaults,**{c['key']:c['value'] for c in row['conditions']}}
            if all(conditions.get(k)==v for k,v in selected.items()):
                matched.append(deepcopy(row))
                for k,v in conditions.items():coverage.setdefault(k,set()).add(v)
        if matched:results.append(dict(observation_id=key,measurement_id=table['id'],revision=observation['history'][-1]['event_id'],status=observation['status'],rows=matched,
            estimand=table['estimand'],columns=deepcopy(table['columns']),conditions=deepcopy(table['conditions']),artifact_refs=deepcopy(table['artifact_refs'])))
    visible={claim_id}|{o['observation_id'] for o in results}
    for o in results:visible.add(observations[o['observation_id']]['run_id'])
    for observation in results:visible.update(paths[observation['observation_id']])
    return dict(claim_id=claim_id,selectors=deepcopy(filters),resolved_conditions=selected,observations=results,
        condition_coverage={k:sorted(v) for k,v in sorted(coverage.items())},unstructured_basis_ids=unstructured,inactive_basis_ids=inactive,
        claim_scope_changed=False,source_fidelity_verified=False,hidden_basis_ids=sorted(basis-{o['observation_id'] for o in results}),graph=dict(nodes=[n for n in graph['nodes'] if n['id'] in visible],relations=[e for e in graph['relations'] if {e['source_id'],e['target_id']}<=visible]))
