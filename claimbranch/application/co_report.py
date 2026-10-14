"""Bounded manual co-report input, exact preview and explicit personal save."""
import hashlib
import json
import secrets
import sys
from datetime import datetime,timezone
from dataclasses import asdict
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode,decode
from claimbranch.core.research_schema import CO_READING,ID,TEXT,array,obj,normalize
from claimbranch.core.review import Judgment
from .paper_work_store import PaperWork
from .manuscript_anchors import source_statuses

INPUT=obj(schema={'const':'claimbranch.co-report/v1'},id=ID,candidates=array(CO_READING,4,2),selected_ids=array(ID,4,2,True),
    companion_ids=array(ID,256,1,True),judgment=TEXT,rationale=TEXT,
    disposition={'enum':['not-required','answered','deferred']},answers=array(TEXT,3,unique=True))


def prepare_co_report(project,request,*,contribution_origin=None):
    from .paper_service import PaperService
    history=project.work.history
    if history.schema_version not in (4,5):raise ContractError('Co-report requires a personal paper profile')
    request=normalize(request,INPUT,profile='paper');view=history.view('main')
    if view['episode_id'] is None:raise ContractError('Open a question before co-report review')
    selected=[r for r in request['candidates'] if r['id'] in request['selected_ids']]
    judgment=Judgment.start(project.project_id,view['episode_id']).edit(request['judgment'],request['rationale'])
    payload={k:request[k] for k in ('id','candidates','selected_ids','companion_ids','disposition','answers')}
    payload.update(context_digest=hashlib.sha256(encode(view,purpose='project')).hexdigest(),judgment=asdict(judgment))
    command=dict(schema_version=8,id='co-report-'+secrets.token_hex(12),project_id=project.project_id,episode_id=view['episode_id'],
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),operation_type='record-co-report',
        expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload)
    from .metadata_batch import origin_command
    command=origin_command(command,contribution_origin)
    candidate=history.append(command);before=PaperService(history).query('main');after=PaperService(candidate).query('main')
    workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);_install(app,candidate,app.episode_id,'main',selected[0]['id']);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    roots=[r['claim_id'] for r in selected]+[o for r in selected for o in r['observation_ids']]
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=command,before=before,after=after,
        decision=candidate.view('main')['co_reports'][request['id']],impact=PaperService(candidate).anchor_impact(roots),
        freshness=source_statuses(history),write_available=False,protected_approval=False)


def recheck_co_report(project,preview):
    if hashlib.sha256(project.payload).hexdigest()!=preview['project_digest'] or source_statuses(project.work.history)!=preview['freshness']:
        raise ContractError('Co-report review changed; preview again')


def run_co_report(args):
    from .personal_project import PersonalProjectStore
    from .project_commands import _read_argument_input
    from .tui_model import clean
    raw=_read_argument_input(args.input);request=decode(raw,purpose='project')
    with PersonalProjectStore(args.directory) as store:
        project=store.load();result,preview=prepare_co_report(project,request,contribution_origin=args.origin)
        lines=clean(json.dumps(preview,ensure_ascii=False,indent=2)).splitlines()
        if args.dry_run:print('\n'.join(lines));return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Co-report requires an interactive terminal; use --dry-run')
        for start in range(0,len(lines),60):
            print('\n'.join(lines[start:start+60]),flush=True)
            if start+60<len(lines) and input('Enter: next page / q: cancel: ').strip().lower()=='q':return 0
        if input('Type record to keep these co-reported readings, or Enter to cancel: ').strip()!='record':return 0
        if _read_argument_input(args.input)!=raw:raise ContractError('Co-report input changed; preview again')
        recheck_co_report(store.load(),preview);store.verify_unchanged();recheck_co_report(project,preview);store.save(result)
        print('Co-reported readings saved. Manuscript and understanding work remain unresolved.')
    return 0
