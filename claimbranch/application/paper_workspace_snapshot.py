"""Closed, unaccepted judgment-writing snapshot; no revived execution or consent."""
from dataclasses import asdict
from copy import deepcopy

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_schema import CONTRIBUTION, HASH, ID, TEXT, array, normalize, nullable, obj
from claimbranch.core.review import Contribution, Judgment

EMPTY_TEXT = {**TEXT, 'minLength': 0}
EDITOR_TEXT = {**EMPTY_TEXT, 'maxLength': 12000}
OWNER = array(ID, 3, 3)
NUMBER = {'type': 'integer', 'minimum': 0, 'maximum': 2**53 - 1}
JUDGMENT_DRAFT = obj(project_id=ID, episode_id=ID, text=nullable(TEXT), rationale=nullable(TEXT),
                     history=array(CONTRIBUTION, 8))
PAIR = obj(text=EMPTY_TEXT, rationale=EMPTY_TEXT)
SESSION = obj(draft_id=ID, revision=NUMBER, view_digest=HASH, judgment=JUDGMENT_DRAFT,
              dispatched={"type": "integer", "minimum": 0, "maximum": 3},
              text=EMPTY_TEXT, rationale=EMPTY_TEXT, before_proposal=nullable(PAIR))
PAPER = obj(drafts=array(obj(owner=OWNER, session=SESSION), 16),
            links=array(obj(owner=OWNER, nodes=array(ID, 16, 1, True)), 16),
            choices=array(obj(node=OWNER, owner=OWNER), 256), revision=NUMBER)
WORKSPACE = obj(schema={'const': 'claimbranch.judgment-workspace/v1'}, paper=PAPER,
    notes=array(obj(owner=OWNER, text=EDITOR_TEXT), 1024),
    drafts=array(obj(owner=OWNER, text=EDITOR_TEXT, rationale=EDITOR_TEXT), 1024),
    buffers=array(obj(owner=OWNER, text=EDITOR_TEXT, rationale=EDITOR_TEXT), 1024),
    unfinished=array(obj(owner=OWNER, mode={'enum': ['note', 'edit']},
                         texts=array(EDITOR_TEXT, 2, 1)), 2048), selection=OWNER)


def session_snapshot(session):
    with session._lock:
        return {'draft_id': session._draft_id, 'revision': session._revision,
                'view_digest': session._view_digest, 'judgment': asdict(session._judgment),
                'dispatched': session._prior_dispatches + len(session._broker.dispatched),
                'text': session._text, 'rationale': session._rationale,
                'before_proposal': session._before_proposal}


def restore_session(session, value):
    value = normalize(value, SESSION)
    raw = value['judgment']
    judgment = Judgment(raw['project_id'], raw['episode_id'], raw['text'], raw['rationale'],
                        tuple(Contribution(**item) for item in raw['history']))
    if ((judgment.project_id, judgment.episode_id) != (session._project, session._episode)
            or value['view_digest'] != session._view_digest):
        raise ContractError('Judgment source differs from its saved paper context.')
    # Called only on a newly allocated session. No outgoing consent, active
    # attempt, adoption capability or review is installed from historical data.
    if value['dispatched'] < sum(item.contributor == 'ai' for item in judgment.history):
        raise ContractError('Saved request count cannot omit adopted AI contributions.')
    session._prior_dispatches = value['dispatched']
    session._judgment = judgment
    session._draft_id, session._revision = value['draft_id'], value['revision']
    session._text, session._rationale = value['text'], value['rationale']
    session._before_proposal = value['before_proposal']


def paper_snapshot(workspace):
    with workspace._lock:
        return {'drafts': [{'owner': list(key), 'session': session_snapshot(session)}
                           for key, session in sorted(workspace._drafts.items())],
                'links': [{'owner': list(key), 'nodes': sorted(nodes)}
                          for key, nodes in sorted(workspace._work_links.items())],
                'choices': [{'node': list(key), 'owner': list(owner)}
                            for key, owner in sorted(workspace._work_choices.items())],
                'revision': workspace.work_revision}


def restore_paper(history, value, *, frozen_response=None, clock=None):
    from .paper_workspace import PaperWorkspace
    schema = deepcopy(PAPER)
    if history.schema_version in (4, 5):
        schema["properties"]["drafts"]["maxItems"] = 32
        schema["properties"]["links"]["maxItems"] = 32
    value = normalize(value, schema, profile="paper" if history.schema_version in (4, 5) else "episode")
    workspace = PaperWorkspace(history, frozen_response=frozen_response, clock=clock)
    seen, ids = set(), set()
    for item in value['drafts']:
        owner, draft_id = tuple(item['owner']), item['session']['draft_id']
        if owner in seen or draft_id in ids:
            raise ContractError('Duplicate judgment owner or identity.')
        seen.add(owner); ids.add(draft_id)
        restore_session(workspace.draft(*owner), item['session'])
    links = set()
    for item in value['links']:
        owner = tuple(item['owner'])
        if owner not in seen or owner in links:
            raise ContractError('Saved links require one existing judgment owner.')
        links.add(owner)
        workspace.link_work(owner, item['nodes'], activate_ids=[])
    choices = set()
    for item in value['choices']:
        node, owner = tuple(item['node']), tuple(item['owner'])
        if node in choices or node[:2] != owner[:2]:
            raise ContractError('Duplicate or cross-context judgment choice.')
        choices.add(node)
        # A separate node's manual draft can exist without a scarce session.
        workspace.draft(*owner) if owner in seen else _check_owner(workspace, owner)
        workspace.activate_work(owner, node[2])
    workspace.work_revision = value['revision']
    return workspace


def _check_owner(workspace, owner, contexts=None):
    # Only validate_workspace supplies this call-local map. Historical session
    # restoration and independent owner checks still query their own sources.
    contexts = {} if contexts is None else contexts
    context = tuple(owner[:2])
    if context not in contexts:
        view = workspace.service.query(owner[1], episode_id=owner[0])
        contexts[context] = frozenset(node['id'] for node in view['nodes'])
    if owner[2] not in contexts[context]:
        raise ContractError('Saved writing requires an existing source node.')


def validate_workspace(history, value):
    expected = 'claimbranch.paper-workspace/v15' if history.has_manuscript_anchors else {4: 'claimbranch.paper-workspace/v13', 5: 'claimbranch.paper-workspace/v14'}.get(history.schema_version)
    if (value.get('schema') in ('claimbranch.paper-workspace/v13', 'claimbranch.paper-workspace/v14', 'claimbranch.paper-workspace/v15')) != bool(expected) or (expected and value.get('schema') != expected):
        raise ContractError("writing workspace capacity/profile mismatch")
    value = normalize(value, workspace_schema(), profile='paper' if history.schema_version in (4, 5) else 'episode')
    workspace = restore_paper(history, value['paper'])
    contexts = {}
    for name in ('notes', 'drafts', 'buffers', 'unfinished'):
        seen = set()
        for item in value[name]:
            owner = tuple(item['owner'])
            _check_owner(workspace, owner, contexts)
            key = (*owner, item['mode']) if name == 'unfinished' else owner
            if key in seen:
                raise ContractError('Duplicate saved writing.')
            seen.add(key)
            if name == 'unfinished' and len(item['texts']) != (1 if item['mode'] == 'note' else 2):
                raise ContractError('Saved editor fields do not match its kind.')
    if 'authoring' in value:
        from .paper_authoring_snapshot import restore_authoring
        unfinished_candidates, _ = restore_authoring(workspace, value['authoring'])
    if 'understanding' in value:
        from .paper_explanation_snapshot import restore_explanations
        restore_explanations(history, value['understanding'])
    if 'review_writing' in value:
        from .paper_review_writing_snapshot import restore_writing
        restore_writing(history, value['review_writing'])
    if 'manuscript' in value:
        from .paper_wording_snapshot import restore_wording
        restore_wording(history, value['manuscript'])
    if 'proposals' in value:
        from .paper_proposal_work import restore_proposals
        restore_proposals(workspace, value['proposals'], unfinished=unfinished_candidates)
    _check_owner(workspace, tuple(value['selection']), contexts)
    return value


def workspace_schema(version=None):
    from copy import deepcopy
    from .paper_authoring_snapshot import AUTHORING
    current = deepcopy(WORKSPACE)
    current['properties']['schema'] = {'const': 'claimbranch.authoring-workspace/v2'}
    current['properties']['authoring'] = AUTHORING
    current['required'].append('authoring')
    if version == 1: return WORKSPACE
    if version == 2: return current
    from .paper_explanation_snapshot import UNDERSTANDING
    explanation = deepcopy(current)
    explanation['properties']['schema'] = {'const': 'claimbranch.explanation-workspace/v3'}
    explanation['properties']['understanding'] = UNDERSTANDING
    explanation['required'].append('understanding')
    if version == 3: return explanation
    from .paper_review_writing_snapshot import REVIEW_WRITING
    writing = deepcopy(explanation)
    writing['properties']['schema'] = {'const': 'claimbranch.review-writing-workspace/v4'}
    writing['properties']['review_writing'] = REVIEW_WRITING
    writing['required'].append('review_writing')
    if version == 4: return writing
    from .paper_wording_snapshot import WORDING
    wording = deepcopy(writing)
    wording['properties']['schema'] = {'const': 'claimbranch.wording-workspace/v5'}
    wording['properties']['manuscript'] = WORDING
    wording['required'].append('manuscript')
    if version == 5: return wording
    from .paper_review_writing_snapshot import POOLED_WRITING
    pooled = deepcopy(wording)
    pooled['properties']['schema'] = {'const': 'claimbranch.review-pool-workspace/v6'}
    pooled['properties']['review_writing'] = POOLED_WRITING
    if version == 6: return pooled
    from .paper_proposal_work import PROPOSALS, PROPOSALS_V2, PROPOSALS_V3, PROPOSALS_V4, PROPOSALS_V5, PROPOSALS_V6
    proposals = deepcopy(pooled)
    proposals['properties']['schema'] = {'const': 'claimbranch.proposal-workspace/v7'}
    proposals['properties']['proposals'] = PROPOSALS
    proposals['required'].append('proposals')
    if version == 7: return proposals
    provider = deepcopy(proposals)
    provider['properties']['schema'] = {'const':'claimbranch.provider-workspace/v8'}
    provider['properties']['proposals'] = PROPOSALS_V2
    if version == 8: return provider
    codex = deepcopy(provider)
    codex['properties']['schema'] = {'const':'claimbranch.codex-workspace/v9'}
    codex['properties']['proposals'] = PROPOSALS_V3
    if version == 9: return codex
    external = deepcopy(codex)
    external['properties']['schema'] = {'const':'claimbranch.external-workspace/v10'}
    external['properties']['proposals'] = PROPOSALS_V4
    if version == 10: return external
    advisory = deepcopy(external)
    advisory['properties']['schema'] = {'const':'claimbranch.advisory-workspace/v11'}
    advisory['properties']['proposals'] = PROPOSALS_V5
    if version == 11: return advisory
    edits = deepcopy(advisory)
    edits['properties']['schema'] = {'const':'claimbranch.edit-workspace/v12'}
    edits['properties']['proposals'] = PROPOSALS_V6
    if version == 12: return edits
    lifecycle = deepcopy(pooled)
    lifecycle['properties']['schema'] = {'const':'claimbranch.paper-workspace/v13'}
    lifecycle['properties']['paper']['properties']['drafts']['maxItems'] = 32
    lifecycle['properties']['paper']['properties']['links']['maxItems'] = 32
    from claimbranch.core.paper_capacity import lifecycle_schema
    lifecycle = lifecycle_schema(lifecycle)
    with_proposals = lifecycle_schema(edits)
    with_proposals["properties"]["schema"] = {"const":"claimbranch.paper-workspace/v13"}
    with_proposals["properties"]["paper"]["properties"]["drafts"]["maxItems"] = 32
    with_proposals["properties"]["paper"]["properties"]["links"]["maxItems"] = 32
    lifecycle = {"oneOf":[lifecycle, with_proposals]}
    if version == 13: return lifecycle
    imported = deepcopy(lifecycle)
    for variant in imported['oneOf']:
        variant['properties']['schema'] = {'const': 'claimbranch.paper-workspace/v14'}
        if 'proposals' in variant['properties']:
            from .paper_proposal_work import imported_proposals_schema
            variant['properties']['proposals'] = imported_proposals_schema()
    if version == 14: return imported
    anchored = deepcopy(imported)
    for variant in anchored['oneOf']: variant['properties']['schema']={'const':'claimbranch.paper-workspace/v15'}
    if version == 15: return anchored
    if version is not None: raise ContractError('Unsupported writing workspace version')
    return {'oneOf': [WORKSPACE, current, explanation, writing, wording, pooled, proposals, provider, codex, external, advisory, edits, lifecycle, imported, anchored]}
