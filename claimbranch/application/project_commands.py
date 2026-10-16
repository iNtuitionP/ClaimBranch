"""Public personal-project init/open over existing paper and terminal services."""
import json
import hashlib
import os
from pathlib import Path
import secrets
import sys
import stat
import time

from claimbranch.core.canonical import ContractError
from .paper_work_store import PaperWork, WorkReopenRequired
from .personal_project import PersonalProjectStore, PersonalProjectRecovery
from .tui_model import clean
from .tui_project import setup_preview, project_workspace, first_episode_prompt
from .tui_work_recovery import snapshot_value


def add_personal_project_commands(commands):
    project = commands.add_parser('project', help='Create, resume or recover your personal paper workspace; local files, AI off')
    actions = project.add_subparsers(dest='project_action', required=True)
    extended=actions.add_parser('import-metadata',help='Review selected extended records together; source originals and declared origins retained')
    extended.add_argument('--directory',required=True)
    extended.add_argument('--input',required=True)
    extended.add_argument('--dry-run',action='store_true')
    preparation=actions.add_parser('prepare-import',help='Retain exact original ledger files and mappings in a new private preview envelope; no project registration')
    preparation.add_argument('--manifest',required=True,help='Owner-private argument-source-manifest/v1 JSON')
    preparation.add_argument('--source-root',required=True,help='Explicit local source directory; only manifest paths are read')
    preparation.add_argument('--output',help='Create-only file in an existing private directory outside Git')
    preparation.add_argument('--dry-run',action='store_true',help='Validate sources/mappings without creating a file')
    argument = actions.add_parser('import-argument', help='Review and register a prior argument in a fresh private project; source origins retained')
    argument.add_argument('--input', required=True, help='Owner-private regular argument-import/v1 or v2 JSON envelope; maximum 16 MiB')
    argument.add_argument('--dry-run', action='store_true', help='Read-only mapping/graph preview; creates no project')
    argument.add_argument('--json', action='store_true', help='Complete private preview including original source chunks; not a share export')
    argument.add_argument('--directory', help='Fresh owner-private destination outside Git; required to register')
    argument.add_argument('--paper-root', help='Existing paper Git root, read-only')
    argument.add_argument('--manuscript', help='Relative marked TeX source, read-only')
    argument.add_argument('--anchor', default='anchor')
    argument.add_argument('--label',help='Existing literal LaTeX label for the initial read-only connection')
    argument.add_argument('--shared-audit',action='store_true',help='Review opt-in lossless shared audit encoding for v2 original ledgers')
    argument.add_argument('--question', help='New unresolved question after migration; not a historical decision')
    for name in ('critique','critiques','critique-original','critique-references'):
        action=actions.add_parser(name,help='Private sourced question or explicit local original; close TUI first')
        action.add_argument('--directory',required=True)
        if name=='critique':
            action.add_argument('--input',required=True)
            action.add_argument('--origin',choices=['human','ai','mixed','unknown'])
            action.add_argument('--dry-run',action='store_true')
        elif name=='critique-original':action.add_argument('--id',required=True)
    for name in ('protocol','protocols'):
        action=actions.add_parser(name,help='Review registered rules/results or inspect their dependent paths; close TUI first')
        action.add_argument('--directory',required=True)
        if name=='protocol':
            action.add_argument('--input',required=True)
            action.add_argument('--origin',choices=['human','ai','mixed','unknown'])
            action.add_argument('--dry-run',action='store_true')
        else:action.add_argument('--node')
    for name in ('measurement','observations','artifact-check'):
        action=actions.add_parser(name,help='Structured measurement review or read-only condition/artifact query; close TUI first')
        action.add_argument('--directory',required=True)
        if name=='measurement':
            action.add_argument('--input',required=True)
            action.add_argument('--origin',choices=['human','ai','mixed','unknown'])
            action.add_argument('--dry-run',action='store_true')
        elif name=='observations':
            action.add_argument('--claim',required=True)
            action.add_argument('--condition',action='append',default=[])
            action.add_argument('--group',action='append',default=[])
        else:
            for flag in ('observation','artifact','path','cell'):action.add_argument('--'+flag,required=True)
    co=actions.add_parser('co-report',help='Review scoped readings together in one personal transaction; close TUI first')
    co.add_argument('--directory',required=True)
    co.add_argument('--origin',choices=['human','ai','mixed','unknown'])
    co.add_argument('--input',required=True,help='Owner-private claimbranch.co-report/v1 JSON')
    co.add_argument('--dry-run',action='store_true')
    for name in ('claim-policy','claim-companion','anchor-context','wording-lint'):
        action=actions.add_parser(name,help='Human reporting restrictions or read-only marked-block warnings; close TUI first')
        action.add_argument('--directory',required=True)
        if name=='wording-lint':continue
        action.add_argument('--origin',choices=['human','ai','mixed','unknown'])
        action.add_argument('--reason',required=True)
        action.add_argument('--dry-run',action='store_true')
        if name=='claim-policy':
            action.add_argument('--claim',required=True)
            action.add_argument('--grade',required=True)
            action.add_argument('--limitation',required=True)
            for flag in ('allowed','caveat','ban'):action.add_argument('--'+flag,action='append',default=[])
            action.add_argument('--placement',action='append',choices=('main','appendix','abstract'),required=True)
        elif name=='claim-companion':
            action.add_argument('--id',required=True)
            action.add_argument('--claim',required=True)
            action.add_argument('--companion',required=True)
            action.add_argument('--scope',choices=('anchor','paragraph'),default='anchor')
            action.add_argument('--retire',action='store_true')
        else:
            action.add_argument('--anchor',required=True)
            if name=='anchor-register':action.add_argument('--label',help='Existing literal LaTeX label; source stays read-only')
            action.add_argument('--placement',choices=('main','appendix','abstract','unknown'),required=True)
            action.add_argument('--paragraphs',help='Private JSON list of index/expresses/plots declarations; original registered block indices')
    for name in ('anchor-register','anchors','anchor-impact'):
        action=actions.add_parser(name,help='Read-only registered manuscript locations and explicit scientific uses')
        action.add_argument('--directory',required=True)
        if name=='anchor-register':
            action.add_argument('--manuscript',required=True)
            action.add_argument('--anchor',required=True)
            if name=='anchor-register':action.add_argument('--label',help='Existing literal LaTeX label; source stays read-only')
            action.add_argument('--kind',choices=('text','figure','table','caption'),required=True)
            action.add_argument('--expresses',nargs='*',default=[])
            action.add_argument('--plots',nargs='*',default=[])
            action.add_argument('--parents',nargs='*',default=[])
            action.add_argument('--origin',choices=['human','ai','mixed','unknown'])
            action.add_argument('--reason',required=True)
            action.add_argument('--dry-run',action='store_true')
        elif name=='anchor-impact':
            action.add_argument('--nodes',nargs='+',required=True)
            action.add_argument('--before',help='Earlier operation ID for old/new association reach')
    imported = actions.add_parser('import-proposal', help='Review an external AI response locally; no inference or scientific acceptance')
    imported.add_argument('--directory', required=True)
    imported.add_argument('--project-id')
    imported.add_argument('--input', required=True, help='Private regular JSON file containing the explicit external proposal envelope')
    imported.add_argument('--dry-run', action='store_true')
    audit=actions.add_parser('enable-shared-audit',help='Review lossless shared audit encoding; preserve originals and scientific state')
    audit.add_argument('--directory',required=True)
    audit.add_argument('--dry-run',action='store_true')
    converted = actions.add_parser('convert-profile', help='Preview legacy personal work conversion into a fresh paper-profile destination; original retained')
    converted.add_argument('--directory', required=True, help='Existing legacy personal project; close TUI first')
    converted.add_argument('--destination', required=True, help='Separate existing fresh owner-private directory outside Git')
    converted.add_argument('--dry-run', action='store_true')
    converted.add_argument('--json', action='store_true')
    for name in ('init', 'open'):
        action = actions.add_parser(name)
        action.add_argument('--directory', required=True, help='Existing owner-private directory outside Git')
        action.add_argument('--project-id', help='Optional expected identity; generated on init and read on open')
        action.add_argument('--provider-directory', help='Private personal LLM configuration; Mac Codex gpt-6-sol supports reviewed requests, other routes preview only')
        if name == 'init':
            action.add_argument('--profile', choices=('episode','paper'), default='episode', help='Registered capacity: legacy episode or personal paper lifecycle (manual AI-off)')
            action.add_argument('--paper-root', required=True, help='Existing local Git paper; source stays read-only')
            action.add_argument('--manuscript', required=True, help='Relative marked .tex source')
            action.add_argument('--anchor', default='anchor')
            action.add_argument('--label',help='Existing literal LaTeX label; requires --profile paper')
            action.add_argument('--title', help='Paper title; prompts when omitted')
            action.add_argument('--thesis', help='Human working thesis; prompts when omitted')
            action.add_argument('--question', help='First unresolved question; prompts when omitted')
            action.add_argument('--dry-run', action='store_true', help='Preview only; writes nothing')
    for name in ('status','backup','export','restore'):
        action=actions.add_parser(name,help={
            'status':'Inspect saved personal work; close its TUI first',
            'backup':'Copy complete saved work into a separate private directory; unencrypted',
            'export':'Create readable JSON; not a restore backup; unencrypted',
            'restore':'Restore a verified personal backup into a fresh private directory'}[name])
        action.add_argument('--directory',required=True,help='Existing owner-private work directory outside Git')
        action.add_argument('--project-id',help='Optional expected project identity')
        action.add_argument('--json',action='store_true',help='Structured saved-work summary; no private writing')
        if name!='status':
            action.add_argument('--archive-directory',required=name!='export',help='Separate existing private directory outside Git')
        if name=='export':
            action.add_argument('--canonical',action='store_true',help='Selected public projection; never a backup')
            action.add_argument('--selection',help='share-selection/v1 JSON: record_ids and separate reason_ids')
            action.add_argument('--output',help='Create-only shared file, including inside Git')
            action.add_argument('--dry-run',action='store_true',help='Show exact shared content without writing')
        if name=='restore':
            action.add_argument('--dry-run',action='store_true',help='Validate backup and basic destination checks; writes nothing and reserves no session')

    sharing=actions.add_parser('verify-export',help='Compare a canonical share with its exact saved private revision')
    sharing.add_argument('--directory',required=True)
    sharing.add_argument('--project-id')
    sharing.add_argument('--input',required=True)


def saved_summary(project,kind):
    return {'kind':kind,'project_id':project.project_id,
        'saved_digest':hashlib.sha256(project.payload).hexdigest(),
        'capacity': {**project.work.history.capacity(), 'project_bytes': {'used':len(project.payload), 'limit':16777216 if project.work.history.schema_version in (4, 5, 14) else 262144, 'remaining':(16777216 if project.work.history.schema_version in (4, 5, 14) else 262144)-len(project.payload)}},
        'episodes':len(project.work.history.episodes()),'evidence_events':project.work.history.watermark,
        'source_status':project.source_status(),'source_fidelity_verified':False,
        'encrypted':False,'authorization_verified':False,'ai':'off',
        'backup_boundary':'Saved project history, associations and kept/unfinished writing only; external artifacts/manuscript and unsaved input are excluded.'}


def run_saved_command(args):
    from .personal_archive import PersonalArchive, PersonalExport, split_personal_backup
    from .project_work import _workspace
    action=args.project_action
    if action!='status' and os.path.samefile(args.directory,args.archive_directory):
        raise ContractError('Choose a separate archive and work directory; no file was replaced.')
    if action=='restore':
        with PersonalArchive(args.archive_directory) as archive: raw=archive.read()
        project=split_personal_backup(raw)
        if args.project_id and project.project_id!=args.project_id:
            raise ContractError('Backup belongs to another project; no restore was started.')
        if args.dry_run:
            _workspace(args.directory)
            for name in ('personal.cbp','work.cbw','backup.cbp','project.json'):
                path=Path(args.directory)/name
                if path.exists() or path.is_symlink():
                    raise ContractError('Restore needs a fresh work destination; existing files retained.')
        else:
            project=PersonalProjectStore.restore_backup(raw,args.directory,project_id=args.project_id)
        result=saved_summary(project,'personal-restore-preview' if args.dry_run else 'personal-project-restored')
        result['checkpoint_created']=not args.dry_run
        if args.dry_run:
            result['destination_checks']='Private path and no existing work/archive checked; session lock and directory inventory are rechecked when restore starts.'
    else:
        with PersonalProjectStore(args.directory,project_id=args.project_id) as store:
            project=store.load()
            if action!='status':
                raw=store.backup() if action=='backup' else project.payload
                store.verify_unchanged()
                with (PersonalArchive if action=='backup' else PersonalExport)(args.archive_directory) as archive:
                    archive.write(raw)
            result=saved_summary(project,'personal-project-'+action)
    if args.json:
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    else:
        print(result['kind']+' · '+project.project_id+' · saved '+result['saved_digest'])
        print('Source: '+result['source_status']+'. Personal files are unencrypted; no protected approval.')
        print(result['backup_boundary'])
        print('Capacity: '+result['capacity']['profile'])
        for key, value in result['capacity']['resources'].items():
            print('  %s: %s / %s (remaining %s)' % (key,value['used'],value['limit'],value['remaining']))
        if action!='status': print('Output directory: '+clean(str(args.directory if action=='restore' else args.archive_directory)))
        if args.project_action=='restore' and args.dry_run: print(result['destination_checks'])
    return 0


def _convert_profile(args):
    from .paper_profile_project import convert_paper_project
    from .project_work import _workspace
    if os.path.samefile(args.directory,args.destination):
        raise ContractError('Conversion requires a separate fresh destination; source unchanged')
    _, identity = _workspace(args.destination)
    with PersonalProjectStore(args.directory) as source:
        project = source.load()
        raw = source._read()
        candidate = convert_paper_project(project,raw)
        summary = {**saved_summary(candidate,'paper-profile-conversion-preview'),
            'original_checkpoint_sha256':hashlib.sha256(raw).hexdigest(),
            'result_sha256':hashlib.sha256(candidate.payload).hexdigest(),
            'source_retained':True, 'new_history_version':4, 'new_checkpoint_frame':2,
            'science_changed':False, 'provider_connection':'not qualified for new profile',
            'conversion_note':'Original dates and contributions retained; context bindings change, no prior consent restores.'}
        print(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=None if args.json else 2),flush=True)
        if args.dry_run: return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ContractError('Conversion requires an interactive terminal; use --dry-run to inspect')
        if input('Type convert to publish this exact conversion in the fresh destination, or Enter to cancel: ')!='convert':
            print('Cancelled. Source and destination unchanged.',flush=True); return 0
        source.verify_unchanged()
        if _workspace(args.destination)[1]!=identity:
            raise ContractError('Conversion destination changed; preview again')
        try:
            with PersonalProjectStore.create(args.destination,project_id=candidate.project_id) as target:
                from .project_work import _identity
                if _identity(os.fstat(target._dir)) != identity:
                    raise ContractError('Conversion destination identity changed; preview again')
                source.verify_unchanged()
                target._save_restored(candidate)
                source.verify_unchanged()
        except WorkReopenRequired as error:
            raise WorkReopenRequired('Conversion save is not confirmed at '+str(args.destination)+
                '; preserve the original and inspect the destination. '+str(error)) from error
    print('Converted personal paper saved; original checkpoint retained.',flush=True)
    return 0


def _import_external(args):
    from claimbranch.core.canonical import canonical_bytes, decode
    from claimbranch.core.research_schema import normalize, obj
    from claimbranch.core.paper_context import request_schema
    from claimbranch.core.paper_proposals import result_schema
    from .paper_proposal_work import EXTERNAL_SOURCE, OWNER, preview_external_proposal, import_external_proposal
    fd = os.open(args.input, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 131072 or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ContractError('Select an owner-private regular proposal JSON file of at most 128 KiB')
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(131073)
    finally:
        os.close(fd)
    if len(raw) > 131072: raise ContractError('External proposal file exceeds 128 KiB')
    value = normalize(decode(raw), obj(schema={'const':'claimbranch.external-proposal/v1'},
        owner=OWNER, request=request_schema(), source=EXTERNAL_SOURCE, result=result_schema()))
    with PersonalProjectStore(args.directory, project_id=args.project_id) as store:
        project = store.load(); app = project_workspace(project)
        app.recovery = PersonalProjectRecovery(store, app, project)
        result = canonical_bytes(value['result'])
        preview = preview_external_proposal(app.paper, value['owner'], value['request'], result, value['source'])
        print('EXTERNAL AI RESPONSE / imported source claims, not a verified application request. No inference or science recorded.')
        print(clean(json.dumps(preview, ensure_ascii=False, indent=2)))
        if args.dry_run: return 0
        if input('Type import to retain this response for later local review; Enter cancels: ').strip() != 'import':
            print('Cancelled; no checkpoint changed.'); return 0
        key = import_external_proposal(app.paper,value['owner'],value['request'],result,value['source'],
            confirmed_digest=preview['digest'],now=int(time.time()))
        app.recovery.save(app)
        print('External AI response retained: '+key+'. Open AI response history to review; no items recorded.')
    return 0


def _read_argument_input(path):
    from claimbranch.core.paper_capacity import PROJECT_BYTES
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > PROJECT_BYTES or before.st_mode & 0o077 or before.st_uid != os.getuid():
            raise ContractError('Select an owner-private regular argument JSON file of at most 16 MiB')
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(PROJECT_BYTES + 1)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ContractError('Argument source changed during reading; retry a fresh preview')
    finally:
        os.close(fd)
    return raw


def _preview_argument(args, *, raw=None, require_complete=False):
    from claimbranch.core.argument_import import preview_import
    from claimbranch.core.paper_capacity import PROJECT_BYTES, source_bytes
    if not args.dry_run:
        raise ContractError('Argument registration is not yet available. Use import-argument --dry-run; no project was created.')
    raw = _read_argument_input(args.input) if raw is None else raw
    result = preview_import(raw)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        display = {key: child for key, child in result.items() if key not in ('source','files')}
        text = 'PRIOR ARGUMENT / private read-only preview; no records registered.\n' + json.dumps(display, ensure_ascii=False, indent=2)
        if 'source' in result:
            text += '\nCOMPLETE ORIGINAL JSON / retained source claims, not verified science\n' + source_bytes(result['source']).decode('utf-8')
        if 'files' in result:
            for file in result['files']:
                text += '\nCOMPLETE ORIGINAL TEXT / '+file['id']+' / '+file['source']['sha256']+'\n'+source_bytes(file['source']).decode('utf-8')
        lines = clean(text).splitlines()
        for index in range(0, len(lines), 40):
            print('\n'.join(lines[index:index+40]), flush=True)
            if index + 40 < len(lines) and sys.stdin.isatty() and sys.stdout.isatty():
                try:
                    answer = input('Enter: next page / q: leave preview (no writes): ').strip().lower()
                except (EOFError, KeyboardInterrupt) as error:
                    print('Preview interrupted; no records registered.')
                    return 130 if isinstance(error, KeyboardInterrupt) else 1
                if answer == 'q':
                    print('Preview left before all pages; no records registered.')
                    return 2 if require_complete else 0 if result['valid'] else 1
    return 0 if result['valid'] else 1


def _register_argument(args):
    from datetime import datetime, timezone
    from claimbranch.core.argument_import import history_from_import, preview_import
    from .project_work import ProjectWork, preview_association, _workspace, _identity
    if not all((args.directory, args.paper_root, args.manuscript, args.question)):
        raise ContractError('Argument registration is not yet available without --directory, --paper-root, --manuscript and --question; use --dry-run to inspect.')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ContractError('Registration requires an interactive terminal; use --dry-run to inspect.')
    raw = _read_argument_input(args.input)
    inspected = preview_import(raw)
    if inspected['schema'] == 'claimbranch.argument-import-preview/v1' and len(raw) > 4194304:
        raise ContractError('capacity import-input-bytes: %s / 4194304; no project registered. Preview remains available with --dry-run.' % len(raw))
    if not inspected['valid']:
        preview_args = type('PreviewArgs', (), dict(dry_run=True, json=args.json, input=args.input))()
        _preview_argument(preview_args, raw=raw)
        return 1
    preview = preview_association(args.paper_root, args.manuscript, args.anchor, args.directory,selector=dict(schema='claimbranch.tex-selector/v1',kind='label',value=args.label) if args.label else None)
    identity = _workspace(args.directory)[1]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    history = history_from_import(raw, anchor_id=args.anchor, registered_at=now)
    # This is the first local question, not a fabricated earlier judgment round.
    token = secrets.token_hex(16)
    history = history.append(dict(schema_version=history.schema_version, id='open-import-'+token,
        project_id=inspected['project_id'], episode_id='after-import-'+token, created_at=now,
        operation_type='open-episode', expected_heads=dict(history.heads), evidence_watermark=history.watermark,
        payload=dict(title=inspected['title'], question=args.question)))
    candidate = ProjectWork.create(PaperWork.create(history), preview, import_input=raw)
    if args.shared_audit:
        candidate,audit_preview=prepare_shared_audit(candidate)
        print(clean(json.dumps(dict(audit_encoding_review=audit_preview),ensure_ascii=False,indent=2)),flush=True)
    from .personal_archive import personal_backup, split_personal_backup
    archive = personal_backup(candidate)
    if split_personal_backup(archive).payload != candidate.payload:
        raise ContractError('Import backup/restore preflight differs; no project registered')
    # A saved candidate must also open under the actual graph/workspace budgets.
    project_workspace(candidate)
    preview_args = type('PreviewArgs', (), dict(dry_run=True, json=args.json, input=args.input))()
    preview_code = _preview_argument(preview_args, raw=raw, require_complete=True)
    if preview_code != 0:
        print('Registration review stopped; no project registered.')
        return 0 if preview_code == 2 else preview_code
    print(clean(json.dumps(dict(destination=str(args.directory), registered_at=now,
        first_local_question=args.question, saved_bytes=len(candidate.payload), capacity=candidate.work.history.capacity(),
        result_sha256=hashlib.sha256(candidate.payload).hexdigest(), source_status=candidate.source_status(),
        archive_bytes=len(archive), history_version=history.schema_version, encrypted=False, authorization_verified=False), ensure_ascii=False, indent=2)), flush=True)
    try:
        answer = input('Type import to register this exact selection in the fresh personal project; Enter cancels: ')
    except (EOFError, KeyboardInterrupt) as error:
        print('Registration interrupted; no project registered.')
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    if answer != 'import':
        print('Cancelled; no project registered.'); return 0
    if _read_argument_input(args.input) != raw:
        raise ContractError('Import input changed after review; no project registered.')
    preview.recheck()
    if _workspace(args.directory)[1] != identity:
        raise ContractError('Import destination changed after review; no project registered.')
    with PersonalProjectStore.create(args.directory, project_id=candidate.project_id) as store:
        if _identity(os.fstat(store._dir)) != identity:
            raise ContractError('Import destination changed while opening; no project registered.')
        preview.recheck()
        if _read_argument_input(args.input) != raw:
            raise ContractError('Import input changed before publication; no project registered.')
        store.save(candidate, preview=preview)
    print('Imported personal argument saved. Past decisions remain source claims; use project open to continue.', flush=True)
    return 0


def run_personal_project_command(args):
    from .tui import run_terminal
    saving = False
    connection = None
    try:
        if args.project_action == 'prepare-import':
            from .argument_preparation import run_prepare
            return run_prepare(args)
        if args.project_action in ('critique','critiques','critique-original','critique-references'):
            from .critiques import run_critique_command
            return run_critique_command(args)
        if args.project_action in ('protocol','protocols'):
            from .protocols import run_protocol_command
            return run_protocol_command(args)
        if args.project_action in ('measurement','observations','artifact-check'):
            from .typed_observations import run_measurement_command
            return run_measurement_command(args)
        if args.project_action=='co-report':
            from .co_report import run_co_report
            return run_co_report(args)
        if args.project_action in ('claim-policy','claim-companion','anchor-context','wording-lint'):
            from .claim_wording import run_wording_command
            return run_wording_command(args)
        if args.project_action in ('anchor-register','anchors','anchor-impact'):
            from .manuscript_anchors import run_anchor_command
            return run_anchor_command(args)
        if args.project_action == 'import-argument':
            saving = not args.dry_run
            return _preview_argument(args) if args.dry_run else _register_argument(args)
        if args.project_action == 'enable-shared-audit':return _enable_shared_audit(args)
        if args.project_action == 'convert-profile': return _convert_profile(args)
        if args.project_action == 'import-proposal': return _import_external(args)
        if args.project_action=='import-metadata':
            from .metadata_batch import run_batch
            return run_batch(args)
        if args.project_action=='verify-export' or (args.project_action=='export' and args.canonical):
            from .canonical_share import run_share_command
            return run_share_command(args)
        if args.project_action=='export' and (not args.archive_directory or args.selection or args.output or args.dry_run):
            raise ContractError('Private export requires --archive-directory; selected sharing uses --canonical --selection --output.')
        if args.project_action in ('status','backup','export','restore'):
            saving = args.project_action=='restore' and not args.dry_run
            return run_saved_command(args)
        if args.project_action=='init' and args.profile=='paper' and getattr(args,'provider_directory',None):
            raise ContractError('Personal-paper provider connection is not qualified; initialize without a provider profile.')
        if args.project_action=='init' and getattr(args, 'provider_directory', None):
            from .provider_commands import PersonalProviderConnection
            connection = PersonalProviderConnection(args.provider_directory).__enter__()
        if args.project_action == 'init':
            args.project_id = args.project_id or 'paper-' + secrets.token_hex(8)
            preview, project, display = setup_preview(args)
            if args.profile == "paper":
                from .paper_profile_project import new_paper_project
                project = new_paper_project(preview, args.project_id, args.title or display["title"], args.thesis or display["thesis"], args.question or display["question"])
                display["capacity"] = project.work.history.capacity()
                if connection:
                    raise ContractError("Personal-paper provider context is not qualified; open without a provider profile.")
            display.update(kind='personal-project-preview', storage='private local files; not encrypted',
                authorization_verified=False, protected_acceptance='unavailable',
                on_confirmation='Create personal work and open the terminal; manuscript unchanged.')
            if connection:
                display['personal_llm'] = connection.profile.readiness()
            print(clean(json.dumps(display, ensure_ascii=False, indent=2)), flush=True)
            if args.dry_run:
                return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ContractError('Project entry needs an interactive terminal; init --dry-run writes nothing.')
        if os.environ.get('TERM', 'dumb') in ('', 'dumb', 'unknown'):
            raise ContractError('A cursor-addressable TERM is required for the workspace.')
        if args.project_action == 'init':
            if input('Type create to save this personal project, or Enter to cancel: ') != 'create':
                print('Cancelled. No project was created.', flush=True)
                return 0
            preview.recheck()
            with PersonalProjectStore.create(args.directory, project_id=args.project_id) as store:
                app = project_workspace(project)
                project = project.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
                saving = True
                store.save(project, preview=preview)
                saving = False
                app.recovery = PersonalProjectRecovery(store, app, project)
                if connection: connection.attach(app)
                return run_terminal(app.paper.history, workspace=app)
        with PersonalProjectStore(args.directory, project_id=args.project_id) as store:
            project = store.load()
            if project.work.history.schema_version in (4, 5, 14) and getattr(args,'provider_directory',None):
                raise ContractError("Personal-paper provider context is not qualified; reopen without a provider profile.")
            if getattr(args,'provider_directory',None):
                from .provider_commands import PersonalProviderConnection
                connection = PersonalProviderConnection(args.provider_directory).__enter__()
            if project.work.history.schema_version in (4, 5, 14):
                print("Capacity: "+json.dumps(project.work.history.capacity(),sort_keys=True),flush=True)
            if not project.work.history.episodes():
                project = first_episode_prompt(project, personal=True)
                if project is None:
                    return 0
                app = project_workspace(project)
                project = project.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
                saving = True
                store.save(project)
                saving = False
            else:
                app = project_workspace(project)
            app.recovery = PersonalProjectRecovery(store, app, project)
            if connection: connection.attach(app)
            return run_terminal(app.paper.history, workspace=app)
    except KeyboardInterrupt as error:
        if args.project_action=='restore':
            guidance='Restoration is not confirmed. Inspect destination '+str(args.directory)+' with project open; preserve the backup and do not overwrite the destination.'
        elif args.project_action=='export' and args.canonical:
            guidance='Preserve any sharing output and verify-export before retrying into a new file; private work was not written.'
        elif args.project_action in ('backup','export'):
            guidance='Copy may be incomplete at '+str(args.archive_directory)+'. Preserve it; retry in a new private archive directory.'
        elif args.project_action=='prepare-import':
            guidance='Inspect any prepared output before retrying with a new filename; originals and project history are unchanged.'
        else:
            guidance='Reopen the personal project to inspect saved writing.'
        print('Interrupted. '+ (clean(error)+' ' if str(error) else '') + clean(guidance), file=sys.stderr)
        return 130
    except (ContractError, OSError, EOFError) as error:
        uncertain=saving and isinstance(error,WorkReopenRequired)
        status = 'Saving is not confirmed. ' if uncertain else ''
        guidance=('Inspect restore destination '+str(args.directory)+' with project open; preserve the backup and do not overwrite this destination.'
                  if uncertain and args.project_action=='restore' else 'Reopen to inspect saved work; no manuscript was written.')
        if args.project_action=='prepare-import':guidance='Inspect any prepared output; originals and project history are unchanged. Retry with a new output filename.'
        print('Project unavailable: ' + clean(error) + '\n' + status +
              clean(guidance), file=sys.stderr)
        return 1
    finally:
        if connection and not connection.close():
            print(clean(connection.cleanup_notice()),file=sys.stderr)
            return 2


def prepare_shared_audit(project):
    """Opt-in physical audit representation; preserve science and old prefixes."""
    from datetime import datetime,timezone
    from .paper_storage_codec import decode
    history=project.work.history
    if history.schema_version!=14:raise ContractError('Shared audit requires an original-ledger v2 imported project.')
    before=history.manifest()
    candidate=history.append(dict(schema_version=16,id='audit-encoding-'+secrets.token_hex(12),
        project_id=project.project_id,episode_id=history.view('main')['episode_id'],
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        operation_type='set-audit-encoding',expected_heads=dict(history.heads),evidence_watermark=history.watermark,
        payload=dict(encoding='shared-values/v1')))
    workspace=decode(project.work.payload).get('workspace')
    if workspace is not None:
        from .personal_research import _install
        app=project_workspace(project)
        _install(app,candidate,app.episode_id,app.ref,app.selected_id)
        workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    return result,dict(before_project_sha256=hashlib.sha256(project.payload).hexdigest(),
        after_project_sha256=hashlib.sha256(result.payload).hexdigest(),
        before_manifest_bytes=len(before),after_manifest_bytes=len(candidate.manifest()),
        manifest_limit=8388608,added_commands=1,command_limit=2048,source_seed_unchanged=history.seed==candidate.seed,
        prior_commands_unchanged=history.commands==candidate.commands[:-1],science_changed=False,
        authority='personal unprotected history',format='shared-values/v1',result_schema='claimbranch.project-work/v23',
        rollback='Keep a private backup before conversion; older builds refuse the new format.')


def _enable_shared_audit(args):
    with PersonalProjectStore(args.directory) as store:
        project=store.load();candidate,display=prepare_shared_audit(project)
        print(clean(json.dumps(display,ensure_ascii=False,indent=2)),flush=True)
        if args.dry_run:return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Audit conversion needs an interactive terminal; use --dry-run.')
        if input('Type convert to save this exact shared audit format, or Enter to cancel: ')!='convert':
            print('Cancelled. Original saved work retained.');return 0
        store.verify_unchanged()
        if hashlib.sha256(store.load().payload).hexdigest()!=display['before_project_sha256']:raise ContractError('Project changed; preview conversion again')
        store.save(candidate);print('Shared audit format saved. Science, originals and earlier writing retained.');return 0
