"""Explicit private capture, local original reading and default omissions."""
import hashlib
import json
import secrets
import sys
from datetime import datetime,timezone
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode,source_record,source_bytes
from claimbranch.core.research_schema import normalize
from claimbranch.core.critiques import INPUT,placeholder_projection
from .typed_observations import current_source
from .manuscript_anchors import source_statuses
from .paper_work_store import PaperWork


def validate_private_sources(history,sources):
    questions=history.view('main').get('critiques',{});by_id={s['id']:s['source'] for s in sources}
    if len(by_id)!=len(sources) or set(by_id)!={q['source_id'] for q in questions.values()}:raise ContractError('Private critique source registry is incomplete or has orphan records')
    normalized_captures=set()
    for question in questions.values():
        raw=source_bytes(by_id[question['source_id']])
        if hashlib.sha256(raw).hexdigest()!=question['source_sha256']:raise ContractError('Retained private critique digest mismatch')
        # The blob is the exact owner-provided capture input, never a science payload.
        capture=normalize(decode(raw,purpose='project'),INPUT,profile='paper')
        if capture['operation_type']!='capture-critique':raise ContractError('Private critique original is not its capture input')
        fingerprint=hashlib.sha256(encode(capture,purpose='project')).hexdigest()
        if fingerprint in normalized_captures:raise ContractError('Duplicate normalized critique capture')
        normalized_captures.add(fingerprint)
        original=capture['payload'];first=question['revisions'][0] if question['revisions'] else question
        if any(first[k]!=original[k] for k in ('question','question_origin')) or any(question[k]!=original[k] for k in ('source_origin','source_kind')):raise ContractError('Question/source association does not match its retained original')


def read_original(project,critique_id):
    value=decode(project.payload,purpose='project');question=project.work.history.view('main').get('critiques',{}).get(critique_id)
    if not question:raise ContractError('Unknown private critique')
    source=next((s for s in value['critique_sources'] if s['id']==question['source_id']),None)
    if source is None:raise ContractError('Private critique original is unavailable')
    return dict(classification='private-original-not-science',original=json.loads(source_bytes(source['source']).decode('utf-8')),
        confidentiality_verified=False,write_available=False)


def prepare_critique(project,request,*,original_input=None,contribution_origin=None):
    from .paper_service import PaperService
    h=project.work.history
    if h.schema_version not in (4, 5, 14, 18):raise ContractError('Critiques require a personal paper profile')
    request=normalize(request,INPUT,profile='paper');view=h.view('main')
    if view['episode_id'] is None:raise ContractError('Open a question before recording a critique')
    source=None;kind=request['operation_type'];payload=request['payload']
    if kind=='capture-critique':
        if type(original_input) is not bytes or normalize(decode(original_input,purpose='project'),INPUT,profile='paper')!=request:raise ContractError('Exact original critique input required')
        blob=source_record(original_input)
        if any(normalize(decode(source_bytes(s['source']),purpose='project'),INPUT,profile='paper')==request for s in decode(project.payload,purpose='project').get('critique_sources',[])):raise ContractError('Identical critique input already retained; revise or link its question')
        key='critique-'+secrets.token_hex(16);source_id='private-source-'+secrets.token_hex(16)
        source=dict(id=source_id,source=blob);kind='record-critique'
        payload=dict(id=key,source_id=source_id,source_sha256=blob['sha256'],**{k:payload[k] for k in ('source_kind','question','question_origin','source_origin')})
    command=dict(schema_version=11,id='critique-op-'+secrets.token_hex(12),project_id=project.project_id,episode_id=view['episode_id'],
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),operation_type=kind,
        expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=payload)
    from .metadata_batch import origin_command
    command=origin_command(command,contribution_origin)
    candidate=h.append(command);workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);_install(app,candidate,app.episode_id,app.ref,app.selected_id);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace),critique_source=source)
    # Preview is local; never copies raw originals, identities or source labels.
    fields=('id','source_kind','question','question_origin','source_origin') if kind=='record-critique' else tuple(payload)
    safe_operation={**command,'payload':{k:payload[k] for k in fields}}
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=safe_operation,
        before=PaperService(h).query('main'),after=PaperService(candidate).query('main'),
        retained_original=bool(source),
        freshness=source_statuses(h),source_binding=current_source(project),scientific=False,resolved=False,protected_approval=False)


def recheck_critique(project,preview):
    if hashlib.sha256(project.payload).hexdigest()!=preview['project_digest'] or source_statuses(project.work.history)!=preview['freshness'] or current_source(project)!=preview['source_binding']:
        raise ContractError('Critique review changed; preview again')


def run_critique_command(args):
    from .personal_project import PersonalProjectStore
    from .project_commands import _read_argument_input
    from .tui_model import clean
    with PersonalProjectStore(args.directory) as store:
        project=store.load()
        if args.project_action=='critique-original':result=read_original(project,args.id)
        elif args.project_action=='critique-references':result=placeholder_projection(project.work.history.view('main'),decode(project.payload,purpose='project')['public_ids'])
        elif args.project_action=='critiques':
            view=project.work.history.view('main');questions={key:{**{field:q[field] for field in ('id','question','question_origin','source_origin','source_kind','classification','revision_id','revisions','resolution','anonymity_verified')},'rationale':q.get('rationale')} for key,q in view.get('critiques',{}).items()};result=dict(questions=questions,links=view.get('critique_links',{}),originals='Excluded; use explicit critique-original',scientific=False)
        else:
            raw=_read_argument_input(args.input);candidate,result=prepare_critique(project,decode(raw,purpose='project'),original_input=raw,contribution_origin=args.origin)
            if not args.dry_run:
                if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Critique recording requires an interactive terminal; use --dry-run')
                from .import_review import confirm_operation
                if not confirm_operation(result,'record'):return 0
                if _read_argument_input(args.input)!=raw:raise ContractError('Critique input changed; preview again')
                recheck_critique(store.load(),result);store.verify_unchanged();recheck_critique(project,result);store.save(candidate)
                print('Private critique operation saved. Associations are not empirical evidence or resolution.');return 0
        print(clean(json.dumps({k:v for k,v in result.items() if k!='project_digest'},ensure_ascii=False,indent=2)))
    return 0
