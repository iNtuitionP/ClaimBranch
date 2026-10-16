"""Create-only private original-ledger envelopes from explicitly named local files."""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import secrets
import hashlib
import sys

from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode,encode,source_record,HISTORY_BYTES
from claimbranch.core.argument_import_v2 import manifest_schema,preview_import
from claimbranch.core.argument_import import _errors,_Diagnostics


def _fingerprint(info):
    return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns


def _read_at(root,relative):
    path=Path(relative)
    if not relative or path.is_absolute() or path.as_posix()!=relative or any(part in ('.','..') or part.casefold()=='.git' for part in relative.split('/')) or '\\' in relative:
        raise ContractError('Sources require explicit relative paths without links, .git or parent traversal')
    directory=os.dup(root)
    try:
        for part in path.parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>HISTORY_BYTES:
                raise ContractError('Select a regular source file at most 4 MiB')
            with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(HISTORY_BYTES+1)
            if len(raw)>HISTORY_BYTES or _fingerprint(os.fstat(fd))!=_fingerprint(before):
                raise ContractError('Source changed during preparation; prepare a fresh snapshot')
            return raw
        finally:os.close(fd)
    finally:os.close(directory)


def prepare(manifest,source_root):
    """Manifest is private JSON; originals may be explicit Git-tracked ledgers."""
    value=decode(manifest,purpose='project');errors=_Diagnostics()
    version={'claimbranch.argument-source-manifest/v2':2,'claimbranch.argument-source-manifest/v3':3,'claimbranch.argument-source-manifest/v4':4}.get(value.get('schema'),1) if type(value) is dict else 1
    _errors(value,manifest_schema(version),'',errors)
    if errors:raise ContractError('Invalid source manifest: '+json.dumps(errors.fields(),ensure_ascii=False))
    root=Path(source_root).absolute()
    if any(part.casefold()=='.git' for part in root.parts):raise ContractError('Source root cannot be Git metadata (.git)')
    if root.resolve(strict=True)!=root:raise ContractError('Source root must be an exact directory without symlink aliases')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        result=deepcopy(value);result['schema']=f'claimbranch.argument-import/v{version+1}';total=0
        for file in result['files']:
            raw=_read_at(fd,file.pop('path'));total+=len(raw)
            if total>HISTORY_BYTES:raise ContractError(f'capacity original-source-bytes: {total} / {HISTORY_BYTES}')
            file['source']=source_record(raw)
    finally:os.close(fd)
    raw=encode(result,purpose='project');review=preview_import(raw)
    return raw,review


def _existing(output,protected):
    from .project_commands import _read_argument_input
    if output.name in ('personal.cbp','work.cbw','backup.cbp','project.json'):
        raise ContractError('Project and backup files are never preparation overwrite targets')
    for source in protected:
        if output==Path(source).absolute() or (output.exists() and os.path.samestat(os.stat(output,follow_symlinks=False),os.stat(source,follow_symlinks=False))):
            raise ContractError('Original sources and manifests cannot be preparation outputs')
    try:info=os.stat(output,follow_symlinks=False)
    except FileNotFoundError:return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise ContractError('Preparation target must be an owner-private regular file')
    if info.st_nlink!=1:raise ContractError('Preparation output must not have hard-link aliases')
    raw=_read_argument_input(output)
    value=decode(raw,purpose='project')
    if type(value) is not dict or value.get('schema') not in tuple(f'claimbranch.argument-import/v{v}' for v in range(2,6)):
        raise ContractError('Only recognized prepared argument envelopes may be overwritten')
    if not preview_import(raw)['valid']:raise ContractError('Existing output is not a valid prepared envelope')
    if _fingerprint(os.stat(output,follow_symlinks=False))!=_fingerprint(info):raise ContractError('Preparation output changed during inspection')
    return dict(fingerprint=_fingerprint(info),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def publish_prepared(raw,output,*,protected,expected_sha256=None,recheck=None):
    """Create-only, or replace the exact reviewed private preparation file."""
    from .project_work import _workspace,_identity
    output=Path(output).absolute();parent=output.parent;_,identity=_workspace(parent)
    old=_existing(output,protected)
    if old is not None and expected_sha256 is None:raise ContractError('Preparation output exists; choose overwrite, save-as or cancel')
    if expected_sha256 is not None and (old is None or old['sha256']!=expected_sha256):raise ContractError('Preparation output differs from the reviewed digest; no replacement')
    directory=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);temporary=None;temp_identity=None;published=False
    try:
        if _identity(os.fstat(directory))!=identity:raise ContractError('Output directory changed')
        temporary='.argument-prepare-'+secrets.token_hex(16)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        try:
            temp_identity=_fingerprint(os.fstat(fd))[:2]
            with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(fd)
            if _fingerprint(os.stat(temporary,dir_fd=directory,follow_symlinks=False))[:2]!=temp_identity:raise ContractError('Prepared temporary file changed')
            if recheck is not None:recheck()
            _,current_identity=_workspace(parent)
            if current_identity!=identity:raise ContractError('Output directory changed before publication')
            current=_existing(output,protected)
            if current!=old:raise ContractError('Preparation output changed; review again')
            if old is None:os.link(temporary,output.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
            else:os.replace(temporary,output.name,src_dir_fd=directory,dst_dir_fd=directory)
            published=True
        finally:os.close(fd)
        try:os.fsync(directory)
        except OSError as error:raise ContractError('Preparation output published but durability is uncertain; inspect before retrying') from error
    except BaseException as error:
        if published:raise ContractError('Preparation output may be published; durability is uncertain. Inspect before retrying.') from error
        if temporary and temp_identity is None:
            raise ContractError('Preparation failed; temporary cleanup is uncertain: '+temporary+'. Inspect before retrying.') from error
        raise
    finally:
        primary=sys.exception()
        try:
            if temporary and temp_identity:
                try:
                    # Create-only publication briefly shares this inode. A
                    # cleanup failure leaves a published output, never a retry.
                    if _fingerprint(os.stat(temporary,dir_fd=directory,follow_symlinks=False))[:2]==temp_identity:os.unlink(temporary,dir_fd=directory)
                except FileNotFoundError:pass
        except OSError as error:
            detail='Temporary cleanup is uncertain: '+temporary+'. Inspect before retrying.'
            if published:raise ContractError('Preparation output may be published; cleanup is uncertain. '+detail) from error
            if primary is None:raise
            primary.add_note(detail)
        finally:os.close(directory)
    return dict(path=str(output),sha256=hashlib.sha256(raw).hexdigest(),replaced=old is not None)


def run_prepare(args):
    from .project_commands import _read_argument_input
    original=_read_argument_input(args.manifest);raw,review=prepare(original,args.source_root)
    summary={key:review.get(key) for key in ('schema','valid','errors','error_count','diagnostics_truncated','project_id','selected','required','omitted','coverage','budgets','preview_digest','registration_available','registration_failure')}
    summary.update(kind='original-ledger-preparation',writes=False,registration_available=summary.get('registration_available',False))
    if not review['valid'] or args.dry_run:
        print(json.dumps(summary,ensure_ascii=False,indent=2));return 0 if review['valid'] else 1
    if not args.output:raise ContractError('Choose --output in an existing private directory outside Git, or --dry-run')
    manifest=decode(original,purpose='project');protected=[Path(args.manifest).absolute(),*[Path(args.source_root).absolute()/f['path'] for f in manifest['files']]]
    output=Path(args.output).absolute();old=_existing(output,protected)
    expected=getattr(args,'expected_output_sha256',None);overwrite=getattr(args,'overwrite',False)
    if bool(expected)!=bool(overwrite):raise ContractError('Noninteractive overwrite requires --overwrite and --expected-output-sha256 together')
    if old is not None and not overwrite:
        if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Output exists; use a new path or explicit overwrite with its expected SHA-256')
        from .import_review import ReviewInput
        from .tui_model import clean
        try:
            with ReviewInput() as read:
                print(clean('Existing preparation: '+str(output)+' / '+old['sha256']+' / '+str(old['bytes'])+' bytes'))
                print('New preparation: '+hashlib.sha256(raw).hexdigest()+' / '+str(len(raw))+' bytes')
                choice=read('Save: overwrite / save-as / Enter: cancel: ').strip()
                if choice=='overwrite':expected=old['sha256']
                elif choice=='save-as':
                    path=read('New file path (must not exist); Enter: cancel: ').strip()
                    if not path or '\x1b' in path:return 0
                    output=Path(path).absolute()
                    if output.exists():raise ContractError('Save-as path already exists; choose a fresh path')
                else:return 0
        except EOFError:return 0
    def recheck():
        if _read_argument_input(args.manifest)!=original or prepare(original,args.source_root)[0]!=raw:raise ContractError('Manifest or source changed; prepare again')
    result=publish_prepared(raw,output,protected=protected,expected_sha256=expected,recheck=recheck)
    summary.update(writes=True,envelope_sha256=review['envelope_sha256'],output=result,next='project import-argument --input <prepared-file> --dry-run')
    print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
