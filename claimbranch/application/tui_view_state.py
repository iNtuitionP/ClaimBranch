"""Disposable private presentation only. No writing, review, consent or science."""
import json
import os
import secrets
import stat
from claimbranch.core.canonical import ContractError
from claimbranch.core.research_schema import obj,array,ID,HASH,nullable,normalize

NAME='ui-view.json'
MAX_BYTES=131072
NUMBER={'type':'integer','minimum':-1000000,'maximum':1000000}
PATH=array(ID,32,1)
ENTRY=obj(episode_id=nullable(ID),ref={'enum':['main','alternative']},lens={'enum':['argument','evidence']},root=nullable(ID),
    selected_id=ID,selected_path=PATH,folds=array(obj(id=ID,path=PATH),1024),revision=HASH,
    viewport=obj(x=NUMBER,y=NUMBER),scope_root=nullable(ID),scope_depth={'type':'integer','minimum':1,'maximum':8})
SCHEMA=obj(schema={'const':'claimbranch.graph-view/v1'},project_id=ID,active={'type':'integer','minimum':0,'maximum':127},entries=array(ENTRY,128,1))


def _entry(episode,ref,nav):
    return dict(episode_id=episode,ref=ref,lens=nav['lens'],root=nav['evidence_root'] if nav['lens']=='evidence' else None,selected_id=nav['selected_id'],
        selected_path=list(nav['selected_path']),folds=[dict(id=k,path=list(p)) for k,p in sorted(nav['_fold_paths'].items()) if p],
        revision=nav['_revision'],viewport=dict(zip(('x','y'),(max(-1000000,min(1000000,v)) for v in nav['graph_pan']))),scope_root=nav['graph_root'],scope_depth=nav['graph_depth'])


def snapshot(app):
    contexts={}
    for (ep,ref),(nav,trail,lenses) in app._contexts.items():
        for value in [*lenses.values(),nav]:contexts[(ep,ref,value['lens'],value['evidence_root'])]=_entry(ep,ref,value)
    for nav in [*app._lens_contexts.values(),app._navigation()]:contexts[(app.episode_id,app.ref,nav['lens'],nav['evidence_root'])]=_entry(app.episode_id,app.ref,nav)
    active=(app.episode_id,app.ref,app.lens,app.evidence_root)
    # Discard only oldest presentation caches if there are many entry roots.
    contexts={k:v for k,v in contexts.items() if k!=active}
    entries=[*contexts.values()][-127:]+[_entry(app.episode_id,app.ref,app._navigation())]
    value=dict(schema='claimbranch.graph-view/v1',project_id=app.view['project_id'],active=len(entries)-1,entries=entries)
    def size():return len(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    while size()>MAX_BYTES and len(entries)>1:
        entries.pop(0);value['active']=len(entries)-1
    # Even maximum-length IDs cannot prevent saving the current root/selection.
    # Missing old fold preferences reopen; they never move to another owner.
    while size()>MAX_BYTES and entries[-1]['folds']:
        entries[-1]['folds']=entries[-1]['folds'][:len(entries[-1]['folds'])//2]
    return normalize(value,SCHEMA,profile='paper')


def apply(app,value):
    value=normalize(value,SCHEMA,profile='paper')
    if value['project_id']!=app.view['project_id'] or value['active']>=len(value['entries']):raise ContractError('Presentation belongs to another project')
    original=(app.episode_id,app.ref);active=None
    for index,entry in enumerate(value['entries']):
        try:app.service.query(entry['ref'],episode_id=entry['episode_id'])
        except ContractError:continue
        app.switch_context(entry['episode_id'],entry['ref'])
        nav=app._navigation();nav.update(lens=entry['lens'],evidence_root=entry['root'] if entry['lens']=='evidence' else None,selected_id=entry['selected_id'],selected_path=tuple(entry['selected_path']),
            collapsed={f['id'] for f in entry['folds']},_fold_paths={f['id']:tuple(f['path']) for f in entry['folds']},_revision=entry['revision'],
            graph_pan=(entry['viewport']['x'],entry['viewport']['y']),graph_follow=False,graph_root=entry['scope_root'],graph_depth=entry['scope_depth'],search='')
        app._restore_navigation(nav) # Revalidates root/occurrence/ownership against current graph.
        app._lens_contexts[(app.lens,app.evidence_root)]=app._navigation()
        if app.lens=='evidence':app._last_entry_roots[(app.episode_id,app.ref)]=app.evidence_root
        if index==value['active']:active=(app.episode_id,app.ref,app._navigation())
    app.switch_context(*(active[:2] if active else original))
    if active:app._restore_navigation(active[2])
    app.message='Saved graph presentation revalidated. Writing and scientific history retained; no review restored.'


def load(store,app):
    try:
        store._check_directory()
        fd=os.open(NAME,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=store._dir)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>MAX_BYTES:raise ContractError('Unsupported private view file')
            raw=b''
            while len(raw)<=MAX_BYTES:
                part=os.read(fd,min(8192,MAX_BYTES+1-len(raw)))
                if not part:break
                raw+=part
            if len(raw)>MAX_BYTES:raise ContractError('View file exceeds presentation budget')
        finally:os.close(fd)
        value=json.loads(raw)
        # Validate the full document before touching any presentation.
        normalize(value,SCHEMA,profile='paper');apply(app,value)
        return raw
    except FileNotFoundError:return None
    except (OSError,ValueError,ContractError,UnicodeError,RecursionError):
        app.message='Saved graph presentation unavailable; using defaults. Research and writing retained.'
        return None


def save(store,app,previous=None):
    raw=json.dumps(snapshot(app),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    if len(raw)>MAX_BYTES:raise ContractError('Presentation exceeds its private byte budget')
    if raw==previous:return raw
    store._check_directory()
    try:
        info=os.stat(NAME,dir_fd=store._dir,follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise ContractError('Unsafe existing presentation file; retained')
    except FileNotFoundError:pass
    temporary='.ui-view-'+secrets.token_hex(12)
    fd=None
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=store._dir)
        with os.fdopen(fd,'wb') as out:
            fd=None;out.write(raw);out.flush();os.fsync(out.fileno())
        os.replace(temporary,NAME,src_dir_fd=store._dir,dst_dir_fd=store._dir);os.fsync(store._dir)
        return raw
    finally:
        if fd is not None:os.close(fd)
        try:os.unlink(temporary,dir_fd=store._dir)
        except FileNotFoundError:pass
