"""Explicit manual paper-lifecycle creation; no protected/store conversion."""
from datetime import datetime, timezone

from claimbranch.core.canonical import decode
from claimbranch.core.research_history import ResearchHistory
from .paper_work_store import PaperWork
from .project_work import ProjectWork


def convert_paper_project(project, original_checkpoint):
    """Preserve original bytes; refuse source-bound writing we cannot yet rebind."""
    from copy import deepcopy
    from claimbranch.core.canonical import ContractError, canonical_bytes
    from claimbranch.core.paper_capacity import source_record
    from .paper_storage_codec import decode as storage_decode, encode
    from .personal_project import _PersonalCodec
    from .paper_service import PaperService
    from .tui_model import TerminalWorkspace
    from .tui_work_recovery import snapshot_value
    history = project.work.history
    if history.schema_version != 3 or _PersonalCodec().open(original_checkpoint) != project.payload:
        raise ContractError('conversion requires the exact legacy personal checkpoint; original retained')
    old = storage_decode(project.payload)
    work = old['work']
    workspace = work.get('workspace')
    if workspace:
        allowed = {'schema','paper','notes','drafts','buffers','unfinished','selection',
                   'authoring','understanding','manuscript','review_writing','proposals'}
        if set(workspace)-allowed:
            raise ContractError('Conversion has unmapped workspace fields; original retained')
        review_writing = workspace.get('review_writing', {})
        pending_review = bool(review_writing) if type(review_writing) is list else bool(review_writing.get('inputs') or review_writing.get('sessions'))
        if (any(workspace.get('proposals',{}).values()) or any(workspace.get('understanding',{}).values()) or
                any(workspace.get('manuscript', {}).values()) or
                workspace.get('authoring', {}).get('candidates') or
                workspace.get('authoring', {}).get('intake', {}).get('items') or
                pending_review):
            raise ContractError('Conversion cannot rebind retained proposals or source-bound unfinished scientific work yet; continue the original project. Nothing was published.')
    elif any(work.get(key) for key in ('origins','judgment','review','explanations')):
        raise ContractError('Conversion cannot rebind this singular review work; original retained')
    seed = decode(history.seed)
    migrated = ResearchHistory.start_lifecycle(seed['project_id'],seed['paper_title'],seed['claim_id'],seed['claim_statement'],seed['anchor_id'])
    old_root = dict(ResearchHistory(history.seed).heads)['main']
    new_root = dict(migrated.heads)['main']
    for raw in history.commands:
        command = decode(raw)
        command['schema_version'] = 4
        command['expected_heads'] = {key: new_root if value==old_root else value
                                     for key,value in command['expected_heads'].items()}
        migrated = migrated.append(command)
    # Compare every retained episode/ref, not only the final current projection.
    episodes = history.episodes()
    for episode in episodes:
        for ref in ('main','alternative'):
            try:
                before = history.view(ref,episode_id=episode['id'])
            except ContractError:
                try: migrated.view(ref,episode_id=episode['id'])
                except ContractError: continue
                raise ContractError('conversion introduced a historical branch; nothing was published')
            after = migrated.view(ref,episode_id=episode['id'])
            fields = ('claims','evidence','experiments','changes','judgments','interpretations','interpretation_episode_ids')
            if canonical_bytes({key:before[key] for key in fields}) != canonical_bytes({key:after[key] for key in fields}):
                raise ContractError('conversion changed historical science; nothing was published')
    app = TerminalWorkspace(migrated,ai_off=True)
    fresh = snapshot_value(app)
    if workspace:
        for key in ('paper','notes','drafts','buffers','unfinished','selection'):
            if key in workspace: fresh[key] = deepcopy(workspace[key])
        for entry in fresh['paper']['drafts']:
            owner = entry['owner']
            entry['session']['view_digest'] = PaperService(migrated).query(owner[1],episode_id=owner[0])['digest']
    from .paper_workspace_snapshot import validate_workspace
    validate_workspace(migrated,fresh)
    new_work = PaperWork.create(migrated,workspace=fresh)
    from .project_work import _public_ids
    value = {**old,'schema':'claimbranch.project-work/v10','work':storage_decode(new_work.payload),
        'sources':[source_record(original_checkpoint)], 'public_ids':_public_ids(migrated,[]),
        'transitions':deepcopy(old.get('transitions',[]))}
    return ProjectWork(encode(value))


def new_paper_project(preview, project_id, title, thesis, question):
    anchor = decode(preview.payload)['source']['anchor_id']
    history = ResearchHistory.start_lifecycle(project_id, title, 'thesis', thesis, anchor)
    history = history.append(dict(schema_version=4, id='open-first-episode', project_id=project_id,
        episode_id='first-episode', created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        operation_type='open-episode', expected_heads=dict(history.heads), evidence_watermark=0,
        payload=dict(title=title, question=question)))
    return ProjectWork.create(PaperWork.create(history), preview)
