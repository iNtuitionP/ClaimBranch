"""Owned invented cache study for the offline terminal rehearsal, never user AI."""
from pathlib import Path
import os
import subprocess
import sys

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory


SOURCE = b'% Synthetic offline cache study; invented measurements.\n% claimbranch:start id=anchor\nCaching on CPU-B remains untested.\n% claimbranch:end id=anchor\n'


def history():
    result = ResearchHistory.start_paper_series('cache-study', 'Synthetic cache study', 'thesis',
        'Caching improves latency on CPU-A and CPU-B.', 'anchor')
    def append(kind, payload):
        nonlocal result
        result = result.append({'schema_version': 3, 'id': 'op-'+str(len(result.commands)+1),
            'project_id': 'cache-study', 'episode_id': 'episode-a', 'created_at': '2026-10-09T00:00:00Z',
            'operation_type': kind, 'expected_heads': dict(result.heads),
            'evidence_watermark': result.watermark, 'payload': payload})
    append('open-episode', {'title': 'CPU-A result', 'question': 'Can CPU-A support the CPU-B claim?'})
    append('record-experiment', {'id': 'run-a', 'question': 'Does caching reduce CPU-A latency?',
        'method': 'Ten invented repetitions with and without caching', 'conditions': 'CPU-A, fixed workload',
        'metric': {'name': 'latency', 'definition': 'Mean elapsed time', 'unit': 'ms', 'comparison': '15 ms without caching'},
        'source_ref': 'synthetic:cpu-a'})
    append('record-evidence-event', {'event_id': 'event-a', 'target_id': 'obs-a', 'run_id': 'run-a',
        'action': 'confirm', 'statement': 'Caching took 6 ms versus 15 ms on CPU-A.', 'value': '6',
        'rationale': 'Invented fixture result; no actual measurement or source access.', 'supersedes_id': None})
    return result


def frozen_response(request=None):
    def ref(key, domain='context'):
        return {'domain': domain, 'id': key}
    value = {'schema': 'claimbranch.provider-result/v2', 'status': 'ok',
        'critique': 'CPU-A was measured; CPU-B was not. The result cannot establish the CPU-B part of the thesis.',
        'items': [
            {'id': 'narrow', 'action': 'create', 'kind': 'claim', 'target_id': None,
             'body': {'role': 'main', 'statement': 'Caching reduced CPU-A latency from 15 ms to 6 ms.',
                      'scope': 'The tested CPU-A workload only', 'parent_ids': [ref('thesis')]}},
            {'id': 'limit', 'action': 'create', 'kind': 'scientific-edge', 'target_id': None,
             'body': {'source_id': ref('obs-a'), 'target_id': ref('thesis'), 'edge_type': 'qualifies',
                      'rationale': 'CPU-B remains unmeasured; only CPU-A was tested.'}},
            {'id': 'repeat', 'action': 'create', 'kind': 'experiment-plan', 'target_id': None,
             'body': {'claim_id': ref('narrow', 'item'), 'objective': 'Test caching on CPU-B.', 'status': 'planned',
                      'conditions': 'CPU-B, the same workload and ten repetitions',
                      'metric': {'name': 'latency', 'definition': 'Mean elapsed time', 'unit': 'ms',
                                 'comparison': 'With versus without caching on CPU-B'}}}]}
    if request is not None:
        selected = {s['record_id'] for s in request['selections']}
        if not {'thesis','obs-a'} <= selected:
            value['items'] = []
            value['critique'] = 'This fixed example has incomplete selected context. Select the thesis and CPU-A observation to compare their limits.'
    return canonical_bytes(value)


def enable(app):
    """Attach only to the identical recorded study, with no live provider toggle."""
    from .paper_service import PaperService
    baseline = PaperService(history()).query('main')['digest']
    def available():
        return (app.episode_id == 'episode-a' and app.ref == 'main'
                and app.service.query('main', episode_id='episode-a')['digest'] == baseline)
    app.offline_assistance = available
    app.offline_assistance_result = frozen_response


def add_command(demos):
    parser = demos.add_parser('proposals', help='Rehearse selective AI items on an invented cache study; no network or device keys')
    parser.add_argument('--directory', help='Existing private, external folder; creates separate paper/work children')
    parser.add_argument('--create', action='store_true', help='Preview and explicitly create this disposable study')
    parser.add_argument('--snapshot', action='store_true', help='Print the invented graph; no files or terminal state')
    parser.add_argument('--ai-off', action='store_true', help='Keep the same study and origins with assistance disabled')


def run(args):
    from .tui import run_terminal
    from .tui_model import TerminalWorkspace, clean
    from .paper_work_store import PaperWork
    from .project_work import ProjectWork, preview_association
    from .personal_project import PersonalProjectStore, PersonalProjectRecovery
    from .tui_project import project_workspace
    from .tui_work_recovery import snapshot_value
    if args.snapshot:
        if args.directory or args.create:
            raise ContractError('Snapshot writes nothing; omit directory/create.')
        app = TerminalWorkspace(history(), ai_off=True)
        if not args.ai_off: enable(app)
        from .tui import render_snapshot
        print(render_snapshot(app))
        return 0
    if not args.directory or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ContractError('Supply --directory in a terminal, or use --snapshot. No study was created.')
    if os.environ.get('TERM', 'dumb') in ('', 'dumb', 'unknown'):
        raise ContractError('A cursor-addressable TERM is required; no study was created.')
    root = Path(args.directory)
    from .project_work import _workspace
    _workspace(root)
    root = root.resolve()
    paper, work = root/'paper', root/'work'
    if args.create:
        if paper.exists() or paper.is_symlink() or work.exists() or work.is_symlink():
            raise ContractError('Use a fresh rehearsal folder; existing paper/work children were retained.')
        print('OFFLINE SYNTHETIC STUDY / no provider or real measurements.\n'
              'Creates invented paper/ and ordinary unencrypted work/ in the selected private folder.\n'
              'Enter cancels. Existing projects are not used.', flush=True)
        try:
            choice = input('Type create to create this disposable study: ')
        except EOFError:
            return 0
        if choice != 'create':
            return 0
        try:
            paper.mkdir(mode=0o700); work.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True, capture_output=True)
            (paper/'paper.tex').write_bytes(SOURCE)
            preview = preview_association(paper, 'paper.tex', 'anchor', work)
            project = ProjectWork.create(PaperWork.create(history()), preview)
            with PersonalProjectStore.create(work, project_id='cache-study') as store:
                app = project_workspace(project)
                project = project.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
                store.save(project, preview=preview)
        except (OSError,ValueError,subprocess.CalledProcessError) as error:
            raise ContractError('Rehearsal initialization did not finish. Preserve any created children and retry --create in a fresh private folder. No existing project or manuscript was changed.') from error
    with PersonalProjectStore(work, project_id='cache-study') as store:
        project = store.load()
        owned = history()
        if project.work.history.seed != owned.seed or project.work.history.commands[:len(owned.commands)] != owned.commands:
            raise ContractError('This is not the owned invented study. Reopen personal work with project open; no example was attached.')
        app = project_workspace(project)
        app.recovery = PersonalProjectRecovery(store, app, project)
        if not args.ai_off: enable(app)
        app.message = 'Offline synthetic rehearsal. ; opens selective assistance and saved origins. No live provider.'
        return run_terminal(app.paper.history, workspace=app)
