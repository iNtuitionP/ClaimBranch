"""Synthetic selected-paper entry over the existing project association store."""
from datetime import datetime, timezone
import json
import sys

from claimbranch.core.canonical import ContractError, bounded_text, canonical_bytes, decode
from .paper_work_store import PaperWork
from .project_work import initialize_project, preview_association, ProjectWorkStore
from .tui_model import TerminalWorkspace, clean
from .tui_work_recovery import JudgmentRecovery, WritingInputError, checkpoint_input, restore, snapshot_value


def prepare_project(preview, *, project_id, title, thesis, question):
    project = initialize_project(preview, project_id=project_id, title=title,
                                 thesis_id='thesis', thesis=thesis)
    return prepare_first_episode(project, question)


def _first_episode_history(project):
    history = project.work.history
    if history.episodes():
        raise ContractError('This project already has research episodes; reopen its existing work.')
    if project.work.payload != PaperWork.create(history).payload:
        raise ContractError('This empty project contains unsupported retained work; nothing was replaced.')
    return history


def prepare_first_episode(project, question):
    """Build detached first work; the caller must preview and explicitly save it."""
    history = _first_episode_history(project)
    bounded_text(question, 'Research question')
    seed = decode(history.seed)
    used = {seed['claim_id'], seed['anchor_id']}
    def unused(base):
        value, index = base, 1
        while value in used:
            value = f'{base}-{index}'
            index += 1
        used.add(value)
        return value
    episode_id, command_id = unused('first-episode'), unused('open-first-episode')
    history = history.append({'schema_version': 3, 'id': command_id,
        'project_id': project.project_id, 'episode_id': episode_id,
        'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'operation_type': 'open-episode', 'expected_heads': dict(history.heads),
        'evidence_watermark': history.watermark,
        'payload': {'title': seed['paper_title'], 'question': question}})
    return project.with_work(PaperWork.create(history))


def first_episode_prompt(project, *, personal=False):
    seed = decode(_first_episode_history(project).seed)
    print('Start work in this saved ' + ('personal' if personal else 'synthetic') + ' project. AI is off.', flush=True)
    print(clean(json.dumps({'project': project.project_id, 'title': seed['paper_title'],
        'working_thesis': seed['claim_statement'], 'source_at_opening': source_notice(project.source_status())},
        ensure_ascii=False, indent=2)), flush=True)
    print('The existing paper connection stays unchanged. No evidence or judgment is supplied.\n'
          'Question input is not saved until you type start. Ctrl+C leaves without saving.', flush=True)
    while True:
        question = input('First unresolved research question: ')
        try:
            bounded_text(question, 'Research question')
        except ContractError as error:
            print('Question not ready: ' + clean(error), flush=True)
            continue
        candidate = prepare_first_episode(project, question)
        command = decode(candidate.work.history.commands[-1])
        print('First question preview (unaccepted work):', flush=True)
        print(clean(json.dumps(command['payload'], ensure_ascii=False, indent=2)), flush=True)
        while True:
            choice = input('Type start to save and open, edit to revise, or Enter to cancel: ').strip().lower()
            if choice in ('start', 'edit', ''):
                break
            print('Choose start, edit, or Enter. Your question is still in the preview.', flush=True)
        if choice == 'start':
            return candidate
        if choice != 'edit':
            print('Cancelled. Existing project and saved writing are unchanged.', flush=True)
            return None


def source_notice(status):
    return {
        'unchanged': 'file matches the saved connection',
        'unchanged-content': 'file matches the saved connection',
        'source-changed-reconciliation-required': 'file changed; writing retains its earlier basis',
        'unavailable-or-unsupported': 'file unavailable; retained writing stays editable',
        'relocation-required': 'check the paper location; original connection retained',
        'unchanged-since-refresh': 'connection refreshed; earlier writing basis retained',
        'unchanged-content-since-refresh': 'connection refreshed; earlier writing basis retained',
    }.get(status, 'source status unknown; retained writing unchanged')


def project_workspace(project):
    # Fixed examples cannot supply AI text to a person's separately authored paper.
    if not project.work.history.episodes():
        raise ContractError('Saved project has no research episode. Use demo project open to write and confirm its first question; retained work is unchanged.')
    app = TerminalWorkspace(project.work.history, ai_off=True)
    if 'workspace' in decode(project.work.payload):
        restore(app, project.work)
    else:
        app.message = 'Press ";" for Add a claim or Draft a result. No evidence or judgment was supplied for you.'
    app.project_source_status = project.source_status()
    app.project_source_notice = source_notice(app.project_source_status)
    if app.project_source_status not in ('unchanged', 'unchanged-content'):
        app.message += ' Source at opening: ' + app.project_source_notice + '.'
    return app


class ProjectRecovery(JudgmentRecovery):
    """Retain the complete typed association while saving terminal writing."""
    def __init__(self, store, app, project):
        self.store, self.project, self.resources = store, project, None
        self.previous_input = None

    def save(self, app, active=None):
        self._check_writable()
        value, current = checkpoint_input(app, active)
        if current == self.previous_input:
            self._store_call(self.store.verify_unchanged)
            return
        try:
            project = self.project.with_work(PaperWork.create(app.paper.history, workspace=value))
        except ContractError as error:
            raise WritingInputError(str(error)) from error
        if project.payload != self.project.payload:
            self._store_call(lambda: self.store.save(project))
            self.project = project
        else:
            self._store_call(self.store.verify_unchanged)
        self.previous_input = current
        from .paper_proposal_work import mark_saved
        mark_saved(app.paper, value)


def add_project_commands(demos):
    project = demos.add_parser('project', help='Create/open a selected synthetic paper in the terminal (Mac)')
    actions = project.add_subparsers(dest='project_action', required=True)
    for name in ('init', 'open'):
        action = actions.add_parser(name)
        action.add_argument('--directory', required=True, help='Existing private directory outside Git')
        action.add_argument('--project-id', required=True, help='Expected synthetic project identity; reuse on open')
        if name == 'init':
            action.add_argument('--paper-root', required=True, help='Existing synthetic Git paper; read-only')
            action.add_argument('--manuscript', required=True, help='Relative marked .tex source')
            action.add_argument('--anchor', default='anchor')
            action.add_argument('--title', help='Paper title; prompts when omitted')
            action.add_argument('--thesis', help='Working thesis/question; prompts when omitted')
            action.add_argument('--question', help='First unresolved research question; prompts when omitted')
            action.add_argument('--dry-run', action='store_true', help='Print exact setup preview; no key/store/terminal creation')


def setup_preview(args):
    fields = {}
    for name, prompt in (('title', 'Paper title'), ('thesis', 'Working thesis (may be tentative)'),
                         ('question', 'First unresolved research question')):
        value = getattr(args, name)
        if value is None:
            if args.dry_run or not sys.stdin.isatty():
                raise ContractError('Supply --title, --thesis and --question for a noninteractive preview.')
            value = input(prompt + ': ')
        fields[name] = value
    preview = preview_association(args.paper_root, args.manuscript, args.anchor, args.directory)
    project = prepare_project(preview, project_id=args.project_id, **fields)
    result = {'kind': 'synthetic-project-preview', **preview.display(),
        'project_id': args.project_id, **fields,
        'initial_episode': decode(project.work.history.commands[-1])['episode_id'],
        'new_evidence': 0, 'ai': 'off', 'accepted_operations': 0,
        'on_confirmation': 'Create encrypted unaccepted work, then open terminal; manuscript unchanged.'}
    return preview, project, result


def run_project_command(args):
    from .tui import run_terminal
    from .work_cipher import MacWorkCipher
    from .work_commands import recovery_key
    try:
        if args.project_action == 'init':
            preview, project, display = setup_preview(args)
            # JSON escapes source-provided terminal controls; print a readable preview.
            print(clean(json.dumps(display, ensure_ascii=False, indent=2)), flush=True)
            if args.dry_run:
                return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ContractError('Interactive project entry requires a TTY; init --dry-run writes nothing.')
        import os
        if os.environ.get('TERM', 'dumb') in ('', 'dumb', 'unknown'):
            raise ContractError('A cursor-addressable TERM is required before opening project work.')
        if sys.platform != 'darwin':
            raise ContractError('Encrypted project entry currently requires macOS; the synthetic TUI remains portable.')
        if args.project_action == 'init':
            if input('Synthetic data only. Type create to create this unaccepted project, or Enter to cancel: ') != 'create':
                print('Cancelled. No project was created.')
                return 0
            preview.recheck()
            key = recovery_key(from_stdin=False, create=True)
            try:
                preview.recheck()
                with MacWorkCipher() as cipher:
                    preview.recheck()
                    with ProjectWorkStore.create(args.directory, cipher=cipher,
                            project_id=args.project_id, recovery_key=key) as store:
                        key = None
                        app = project_workspace(project)
                        project = project.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
                        store.save(project, preview=preview)
                        app.recovery = ProjectRecovery(store, app, project)
                        return run_terminal(app.paper.history, workspace=app)
            finally:
                key = None
        with MacWorkCipher() as cipher:
            with ProjectWorkStore(args.directory, cipher=cipher, project_id=args.project_id) as store:
                project = store.load()
                if project is None:
                    raise ContractError('Saved project missing; no replacement was created.')
                if not project.work.history.episodes():
                    try:
                        candidate = first_episode_prompt(project)
                    except EOFError:
                        print('Cancelled. No question was saved; the existing project is unchanged.', flush=True)
                        return 0
                    except KeyboardInterrupt:
                        print('Interrupted. No question was saved; the existing project is unchanged.', file=sys.stderr)
                        return 130
                    if candidate is None:
                        return 0
                    app = project_workspace(candidate)
                    candidate = candidate.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
                    store.save(candidate)
                    project = candidate
                    print('First question saved as unaccepted work. Opening the graph.', flush=True)
                else:
                    app = project_workspace(project)
                app.recovery = ProjectRecovery(store, app, project)
                return run_terminal(app.paper.history, workspace=app)
    except KeyboardInterrupt:
        print('Project entry interrupted. Reopen an existing checkpoint to inspect saved writing.', file=sys.stderr)
        return 130
    except (ContractError, OSError, EOFError) as error:
        print('Project entry unavailable: ' + clean(error) + '\nNo manuscript file was written.', file=sys.stderr)
        return 1
