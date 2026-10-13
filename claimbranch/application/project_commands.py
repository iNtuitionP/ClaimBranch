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
    imported = actions.add_parser('import-proposal', help='Review an external AI response locally; no inference or scientific acceptance')
    imported.add_argument('--directory', required=True)
    imported.add_argument('--project-id')
    imported.add_argument('--input', required=True, help='Private regular JSON file containing the explicit external proposal envelope')
    imported.add_argument('--dry-run', action='store_true')
    for name in ('init', 'open'):
        action = actions.add_parser(name)
        action.add_argument('--directory', required=True, help='Existing owner-private directory outside Git')
        action.add_argument('--project-id', help='Optional expected identity; generated on init and read on open')
        action.add_argument('--provider-directory', help='Private personal LLM configuration; Mac Codex gpt-6-sol supports reviewed requests, other routes preview only')
        if name == 'init':
            action.add_argument('--paper-root', required=True, help='Existing local Git paper; source stays read-only')
            action.add_argument('--manuscript', required=True, help='Relative marked .tex source')
            action.add_argument('--anchor', default='anchor')
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
            action.add_argument('--archive-directory',required=True,help='Separate existing private directory outside Git')
        if name=='restore':
            action.add_argument('--dry-run',action='store_true',help='Validate backup and basic destination checks; writes nothing and reserves no session')


def saved_summary(project,kind):
    return {'kind':kind,'project_id':project.project_id,
        'saved_digest':hashlib.sha256(project.payload).hexdigest(),
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
        if action!='status': print('Output directory: '+clean(str(args.directory if action=='restore' else args.archive_directory)))
        if args.project_action=='restore' and args.dry_run: print(result['destination_checks'])
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


def run_personal_project_command(args):
    from .tui import run_terminal
    saving = False
    connection = None
    try:
        if args.project_action == 'import-proposal': return _import_external(args)
        if args.project_action in ('status','backup','export','restore'):
            saving = args.project_action=='restore' and not args.dry_run
            return run_saved_command(args)
        if getattr(args, 'provider_directory', None):
            from .provider_commands import PersonalProviderConnection
            connection = PersonalProviderConnection(args.provider_directory).__enter__()
        if args.project_action == 'init':
            args.project_id = args.project_id or 'paper-' + secrets.token_hex(8)
            preview, project, display = setup_preview(args)
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
        elif args.project_action in ('backup','export'):
            guidance='Copy may be incomplete at '+str(args.archive_directory)+'. Preserve it; retry in a new private archive directory.'
        else:
            guidance='Reopen the personal project to inspect saved writing.'
        print('Interrupted. '+ (clean(error)+' ' if str(error) else '') + clean(guidance), file=sys.stderr)
        return 130
    except (ContractError, OSError, EOFError) as error:
        uncertain=saving and isinstance(error,WorkReopenRequired)
        status = 'Saving is not confirmed. ' if uncertain else ''
        guidance=('Inspect restore destination '+str(args.directory)+' with project open; preserve the backup and do not overwrite this destination.'
                  if uncertain and args.project_action=='restore' else 'Reopen to inspect saved work; no manuscript was written.')
        print('Project unavailable: ' + clean(error) + '\n' + status +
              clean(guidance), file=sys.stderr)
        return 1
    finally:
        if connection and not connection.close():
            print(clean(connection.cleanup_notice()),file=sys.stderr)
            return 2
