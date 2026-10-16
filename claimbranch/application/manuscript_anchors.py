"""Explicit read-only manuscript uses, replayable registration and freshness."""
import base64
import hashlib
import json
import os
import stat
from copy import deepcopy
from datetime import datetime, timezone

from claimbranch.core.canonical import ContractError
from claimbranch.core.marked_text import selected_block
from claimbranch.core.paper_capacity import decode, encode
from .project_work import _source, _path, _identity
from .paper_work_store import PaperWork


def read_binding(source):
    root, relative = _path(source['root']), _path(source['manuscript'], relative=True)
    current = _source(root, relative, source['anchor_id'], maximum=2097152,selector=source.get('selector'))
    from contextlib import ExitStack
    with ExitStack() as held:
        def opened(name,parent=None,directory=False):
            flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_DIRECTORY if directory else 0)
            fd=os.open(name,flags,dir_fd=parent);held.callback(os.close,fd);return fd
        parent=opened(root,directory=True)
        if _identity(os.fstat(parent))!=current['root_identity']:raise ContractError('anchor root identity changed')
        entries=[]
        for component in relative.parts[:-1]:
            child=opened(component,parent,True);entries.append((parent,component,child));parent=child
        fd=opened(relative.name,parent);entries.append((parent,relative.name,fd))
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or _identity(info)!=current['file_identity']:
            raise ContractError('anchor source identity changed')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(2097153)
        after=os.fstat(fd)
        stamp=lambda value:(_identity(value),value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        if stamp(info)!=stamp(after):raise ContractError('anchor source changed during read')
        for owner,name,fd in entries:
            if _identity(os.stat(name,dir_fd=owner,follow_symlinks=False))!=_identity(os.fstat(fd)):
                raise ContractError('anchor path changed during read')
    if len(raw)>2097152 or hashlib.sha256(raw).hexdigest()!=current['source_digest'] or _source(root,relative,source['anchor_id'],maximum=2097152,selector=source.get('selector'))!=current:
        raise ContractError('anchor source changed during inspection')
    return current, selected_block(raw,source['anchor_id'],source.get('selector'))


def inspect_anchor(anchor):
    try:
        current,raw=read_binding(anchor['source'])
        identity_same=all(current[key]==anchor['source'][key] for key in ('root_identity','git_identity','git_common_identity','file_identity'))
        block_same=hashlib.sha256(raw).hexdigest()==anchor['block_digest']
        return dict(status='identity-changed' if not identity_same else 'block-changed' if not block_same else 'unchanged' if current==anchor['source'] else 'unchanged-block-file-changed',
                    block_matches=block_same,source_matches=current==anchor['source'],current=current,
                    source_fidelity_verified=False,write_available=False)
    except (ContractError,OSError,UnicodeError):
        return dict(status='unavailable-or-unsupported',block_matches=False,source_matches=False,current=None,
                    source_fidelity_verified=False,write_available=False)


def source_statuses(history):
    return {key:inspect_anchor(anchor) for key,anchor in history.view('main').get('manuscript_anchors',{}).items()}


def prepare_registration(project, *, manuscript, anchor_id, kind, expresses=(), plots=(), parents=(), rationale, contribution_origin=None, selector=None):
    history=project.work.history
    if history.schema_version not in (4, 5, 14, 18):
        raise ContractError('Multiple anchors require a paper profile; convert into a fresh paper-profile destination first.')
    source=decode(project.payload,purpose='project')['associations'][-1]
    provisional={k:v for k,v in source.items() if k not in ('selector','span_digest')}
    if selector is not None:provisional['selector']=selector
    provisional={**provisional,'manuscript':os.fsencode(manuscript).hex(),'anchor_id':anchor_id}
    current,block=read_binding(provisional)
    payload=dict(id=anchor_id,kind=kind,source=current,block_digest=hashlib.sha256(block).hexdigest(),
        block=[base64.b64encode(block[i:i+8192]).decode() for i in range(0,len(block),8192)],
        expresses=sorted(expresses),plots=sorted(plots),parents=sorted(parents),rationale=rationale)
    import secrets
    cmd=dict(schema_version=17 if selector is not None and selector.get('schema')=='claimbranch.tex-selector/v2' else 15 if selector is not None else 6,id='anchor-register-'+secrets.token_hex(12),project_id=project.project_id,
        episode_id=history.view('main')['episode_id'],created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        operation_type='register-manuscript-anchor',expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload)
    from .metadata_batch import origin_command
    cmd=origin_command(cmd,contribution_origin)
    candidate=history.append(cmd)
    from .paper_service import PaperService
    PaperService(candidate).query("main")
    workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project)
        _install(app,candidate,app.episode_id,app.ref,app.selected_id)
        workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=cmd,registration=payload,after=payload,
        before=history.view('main').get('manuscript_anchors',{}).get(anchor_id),
        marked_text=block.decode('utf-8'),write_available=False,source_fidelity_verified=False,
        result_project_schema=decode(result.payload,purpose='project')['schema'],older_build_rollback='Keep a private backup before registration; label formats require this build or newer.',
        coverage='Explicit registered blocks only; includes, graphics, unregistered passages and scientific fidelity are outside coverage.')


def recheck_registration(project, display):
    if hashlib.sha256(project.payload).hexdigest()!=display['project_digest']:
        raise ContractError('anchor registration project changed; preview again')
    payload=display['registration'];current,raw=read_binding(payload['source'])
    if current!=payload['source'] or hashlib.sha256(raw).hexdigest()!=payload['block_digest']:
        raise ContractError('anchor registration source changed; preview again')


def run_anchor_command(args):
    from .personal_project import PersonalProjectStore
    from .paper_service import PaperService
    import sys
    with PersonalProjectStore(args.directory) as store:
        project=store.load()
        if args.project_action=='anchors':
            value=dict(anchors=project.work.history.view('main').get('manuscript_anchors',{}),freshness=source_statuses(project.work.history),
                       coverage='Registered blocks only; no recursive includes or graphics verification.',write_available=False)
        elif args.project_action=='anchor-impact':
            value=PaperService(project.work.history).anchor_impact(args.nodes,at_operation=args.before)
        else:
            result,value=prepare_registration(project,manuscript=args.manuscript,anchor_id=args.anchor,
                kind=args.kind,expresses=args.expresses or (),plots=args.plots or (),parents=args.parents or (),rationale=args.reason,contribution_origin=args.origin,selector=(dict(schema='claimbranch.tex-selector/v'+str(getattr(args,'label_version',2)),kind='label',value=args.label) if args.label else None))
            if not args.dry_run:
                if not sys.stdin.isatty() or not sys.stdout.isatty(): raise ContractError('Anchor registration requires an interactive terminal; use --dry-run.')
                from .import_review import confirm_operation
                if not confirm_operation(value,'register'):return 0
                recheck_registration(store.load(),value)
                store.verify_unchanged()
                recheck_registration(project,value)
                store.save(result)
                print('Manuscript anchors saved. Source files were not written.');return 0
        print(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
    return 0
