"""Exact personal protocol review, record and dependency inspection."""
import hashlib
import json
import secrets
import sys
from datetime import datetime,timezone
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from claimbranch.core.research_schema import normalize
from claimbranch.core.protocols import INPUT,protocol_context,plan_digest
from .typed_observations import current_source
from .manuscript_anchors import source_statuses
from .paper_work_store import PaperWork


def prepare_protocol(project,request,*,contribution_origin=None):
    from .paper_service import PaperService
    history=project.work.history
    if history.schema_version not in (4,5):raise ContractError('Protocols require a personal paper profile')
    request=normalize(request,INPUT,profile='paper');view=history.view('main')
    if view['episode_id'] is None:raise ContractError('Open a question before protocol review')
    command=dict(schema_version=10,id='protocol-'+secrets.token_hex(12),project_id=project.project_id,episode_id=view['episode_id'],
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),operation_type=request['operation_type'],
        expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=request['payload'])
    from .metadata_batch import origin_command
    command=origin_command(command,contribution_origin)
    candidate=history.append(command);workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);_install(app,candidate,app.episode_id,app.ref,app.selected_id);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=command,
        before=PaperService(history).query('main'),after=PaperService(candidate).query('main'),
        context=protocol_context(candidate.view('main')),freshness=source_statuses(history),source_binding=current_source(project),
        write_available=False,protected_approval=False,chronology_verified=False)


def recheck_protocol(project,preview):
    if hashlib.sha256(project.payload).hexdigest()!=preview['project_digest'] or source_statuses(project.work.history)!=preview['freshness'] or current_source(project)!=preview['source_binding']:
        raise ContractError('Protocol review changed; preview again')


def run_protocol_command(args):
    from .personal_project import PersonalProjectStore
    from .project_commands import _read_argument_input
    from .tui_model import clean
    with PersonalProjectStore(args.directory) as store:
        project=store.load()
        if args.project_action=='protocols':
            view=project.work.history.view('main');context=protocol_context(view)
            if args.node and args.node not in context:raise ContractError('No registered protocol dependency at this node')
            plans=[dict(id=c['id'],digest=plan_digest(c),body=c['body']) for c in view['experiment_plans']]
            result=dict(available_plans=plans,context={args.node:context[args.node]} if args.node else context,
                records={name:view.get(name,{}) for name in ('protocols','experiment_associations','gate_amendments','gate_results','outcome_assessments')} if not args.node else {},chronology_verified=False,write_available=False)
        else:
            raw=_read_argument_input(args.input);candidate,result=prepare_protocol(project,decode(raw,purpose='project'),contribution_origin=args.origin)
            if not args.dry_run:
                if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Protocol recording requires an interactive terminal; use --dry-run')
                lines=clean(json.dumps(result,ensure_ascii=False,indent=2)).splitlines()
                for start in range(0,len(lines),60):
                    print('\n'.join(lines[start:start+60]),flush=True)
                    if start+60<len(lines) and input('Enter: next page / q: cancel: ').strip().lower()=='q':return 0
                if input('Type record to save this protocol operation, or Enter to cancel: ').strip()!='record':return 0
                if _read_argument_input(args.input)!=raw:raise ContractError('Protocol input changed; preview again')
                recheck_protocol(store.load(),result);store.verify_unchanged();recheck_protocol(project,result);store.save(candidate)
                print('Protocol operation saved. Original rules/results retained; measured values and manuscript unchanged.');return 0
        print(clean(json.dumps(result,ensure_ascii=False,indent=2)))
    return 0
