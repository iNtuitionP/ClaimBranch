"""Create-only private original-ledger envelopes from explicitly named local files."""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import secrets

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
    _errors(value,manifest_schema(),'',errors)
    if errors:raise ContractError('Invalid source manifest: '+json.dumps(errors.fields(),ensure_ascii=False))
    root=Path(source_root).absolute()
    if any(part.casefold()=='.git' for part in root.parts):raise ContractError('Source root cannot be Git metadata (.git)')
    if root.resolve(strict=True)!=root:raise ContractError('Source root must be an exact directory without symlink aliases')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        result=deepcopy(value);result['schema']='claimbranch.argument-import/v2';total=0
        for file in result['files']:
            raw=_read_at(fd,file.pop('path'));total+=len(raw)
            if total>HISTORY_BYTES:raise ContractError(f'capacity original-source-bytes: {total} / {HISTORY_BYTES}')
            file['source']=source_record(raw)
    finally:os.close(fd)
    raw=encode(result,purpose='project');review=preview_import(raw)
    return raw,review


def run_prepare(args):
    from .project_commands import _read_argument_input
    from .project_work import _workspace,_identity
    original=_read_argument_input(args.manifest)
    raw,review=prepare(original,args.source_root)
    summary={key:review.get(key) for key in ('schema','valid','errors','error_count','diagnostics_truncated',
        'project_id','selected','required','omitted','coverage','budgets','preview_digest','registration_available','registration_failure')}
    summary.update(kind='original-ledger-preparation',writes=False,registration_available=summary.get('registration_available',False))
    if not review['valid'] or args.dry_run:
        print(json.dumps(summary,ensure_ascii=False,indent=2));return 0 if review['valid'] else 1
    if not args.output:raise ContractError('Choose --output in an existing private directory outside Git, or --dry-run')
    output=Path(args.output).absolute();parent=output.parent;_,identity=_workspace(parent)
    directory=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        if _identity(os.fstat(directory))!=identity:raise ContractError('Output directory changed')
        if _read_argument_input(args.manifest)!=original:raise ContractError('Manifest changed during preparation; try a fresh preview')
        # Original file bytes are the declared snapshot; later ledger edits are not synced.
        temporary='.argument-prepare-'+secrets.token_hex(16)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        identity=_fingerprint(os.fstat(fd))[:2]
        try:
            with os.fdopen(fd,'wb',closefd=False) as stream:
                stream.write(raw);stream.flush();os.fsync(fd)
            if _fingerprint(os.stat(temporary,dir_fd=directory,follow_symlinks=False))[:2]!=identity:
                raise ContractError('Prepared temporary file changed; no output published')
            # Hard-link publication is atomic and cannot replace an existing name.
            os.link(temporary,output.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
        finally:
            os.close(fd)
            try:
                if _fingerprint(os.stat(temporary,dir_fd=directory,follow_symlinks=False))[:2]==identity:
                    os.unlink(temporary,dir_fd=directory)
            except FileNotFoundError:pass
        os.fsync(directory)
    finally:os.close(directory)
    summary['writes']=True;summary['envelope_sha256']=review['envelope_sha256']
    summary['next']='project import-argument --input <prepared-file> --dry-run; use import-argument with a fresh private project for reviewed registration'
    print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
