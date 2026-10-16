"""Unfinished scientific writing and its original inputs, never a restored review."""
from copy import deepcopy
import unicodedata

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.paper_changes import amendment_schema, request_schema
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, array, nullable, obj, normalize
from .paper_authoring_snapshot import SOURCE, source_reference
from .paper_workspace_snapshot import EMPTY_TEXT, OWNER, SESSION, session_snapshot, restore_session
from .paper_service import PaperService

EDIT_FIELDS = {'claim': ('statement', 'scope'), 'interpretation': ('statement',),
               'experiment-plan': ('objective',), 'scientific-edge': ('edge_type', 'rationale')}
BASIS = obj(source=SOURCE, record=nullable(amendment_schema()['items']),
            session=nullable(SESSION), request=nullable(request_schema()))
REVIEW_WRITING = array(obj(owner=OWNER, mode={'type': 'string', 'maxLength': 160},
    basis=BASIS, texts=array(EMPTY_TEXT, 2, 1),
    field={'type': 'integer', 'minimum': 0, 'maximum': 1}), 64)


POOLED_BASIS = obj(source=SOURCE, record=nullable(amendment_schema()['items']),
                   session_digest=nullable(HASH), request=nullable(request_schema()))
POOLED_WRITING = obj(schema={'const': 'claimbranch.review-writing/v2'},
    sessions=array(obj(digest=HASH, session=SESSION), 64),
    inputs=array(obj(owner=OWNER, mode={'type': 'string', 'maxLength': 160},
        basis=POOLED_BASIS, texts=array(EMPTY_TEXT, 2, 1),
        field={'type': 'integer', 'minimum': 0, 'maximum': 1}), 64))


def pack_writing(rows):
    """Share exact original session content; keep each source/request distinct."""
    sessions, inputs = {}, []
    if type(rows) is not list or len(rows) > 64:
        raise ContractError('Bounded original review inputs required.')
    # Validate rows separately: repeated inline origins can exceed the whole
    # checkpoint byte bound even when their pooled representation fits it.
    for row in rows:
        row = normalize(row, REVIEW_WRITING['items'])
        basis = row['basis']
        session = basis.pop('session')
        key = None if session is None else digest(session)
        if session is not None:
            if key in sessions and sessions[key] != session:
                raise ContractError('Conflicting original review session fingerprint.')
            sessions[key] = session
        inputs.append({**row, 'basis': {**basis, 'session_digest': key}})
    return {'schema': 'claimbranch.review-writing/v2', 'inputs': inputs,
            'sessions': [{'digest': key, 'session': sessions[key]} for key in sorted(sessions)]}


def writing_rows(value):
    """Validate the pool before expanding detached per-input historical bases."""
    if type(value) is list:
        return normalize(value, REVIEW_WRITING)
    value = normalize(value, POOLED_WRITING)
    sessions, used, rows = {}, set(), []
    keys = [item['digest'] for item in value['sessions']]
    if keys != sorted(keys):
        raise ContractError('Original review sessions require canonical fingerprint order.')
    for item in value['sessions']:
        key = item['digest']
        if key in sessions or digest(item['session']) != key:
            raise ContractError('Duplicate or invalid original review session fingerprint.')
        sessions[key] = item['session']
    for row in value['inputs']:
        basis = row['basis']
        key = basis.pop('session_digest')
        if key is not None and key not in sessions:
            raise ContractError('Original review session reference is missing.')
        if key is not None: used.add(key)
        rows.append({**row, 'basis': {**basis, 'session': deepcopy(sessions[key]) if key else None}})
    if used != set(sessions):
        raise ContractError('Unreferenced original review session.')
    return rows


def query(history, owner):
    view = PaperService(history).query(owner[1], episode_id=owner[0])
    if owner[2] not in {node['id'] for node in view['nodes']}:
        raise ContractError('Review writing requires its original source owner.')
    return view


def capture_basis(app, *, record=None):
    owner, history = app.full_context(app.review.key), app.paper.history
    view = query(history, owner)
    session = app.review.sessions.get(app.review.key)
    request = None
    if record is None:
        if session is None or session.get_changes_preview() is None:
            raise ContractError('Prepare the exact scientific scope before starting an answer.')
        request = decode(session._changes_request)
    return normalize({'source': source_reference(history, history, view['digest']),
            'record': deepcopy(record), 'session': session_snapshot(session) if session else None,
            'request': request}, BASIS)


def original_history(history, basis):
    count = basis['source']['commands']
    if count > len(history.commands):
        raise ContractError('Review writing source is outside saved history.')
    return history if count == len(history.commands) else ResearchHistory.replay(history.seed, history.commands[:count])


def validate_basis(history, owner, mode, basis):
    original = original_history(history, basis)
    view = query(original, owner)
    return _validate_basis(original, view, owner, mode, basis)


def _validate_basis(original, view, owner, mode, basis, changes=None):
    # A shared projection never substitutes for this input's owner or digest.
    if owner[2] not in {node['id'] for node in view['nodes']}:
        raise ContractError('Review writing requires its original source owner.')
    if view['digest'] != basis['source']['digest']:
        raise ContractError('Review writing source fingerprint changed.')
    session = None
    if basis['session'] is not None:
        from .paper_draft import PaperDraftSession
        # Owner membership is checked above. A temporary workspace would query
        # the same source again before the session's own independent query.
        session = PaperDraftSession(PaperService(original), ref=owner[1], episode_id=owner[0])
        restore_session(session, basis['session'])
        if original.schema_version in (5, 14, 18):
            session._imported_subject = owner[2]
    record, request = basis['record'], basis['request']
    if mode.startswith('change:'):
        key = mode.removeprefix('change:')
        if changes is None:
            changes = {item['id']: item for item in original.view(owner[1], episode_id=owner[0])['changes']}
        source = changes.get(key)
        if (record is None or request is not None or source is None
                or record['id'] != key or record['kind'] != source['kind'] or record['kind'] not in EDIT_FIELDS):
            raise ContractError('Unfinished fields require their original editable record.')
        fields = EDIT_FIELDS[record['kind']]
        # This is an unaccepted authored baseline, which may also contain kept
        # structural edits. Identity/kind are bound to the source; semantic
        # validation remains at candidate projection and fresh review.
        return [record['body'][name] or '' for name in fields]
    if mode != 'explanation' or record is not None or request is None or session is None:
        raise ContractError('Unfinished explanation requires its original selected scientific inputs.')
    session._check_changes_request(request)
    PaperService(original).preview_changes(request, session._current_judgment(), source_node_id=owner[2] if original.schema_version in (5, 14, 18) else None)
    return [basis['session']['rationale']]


def baseline(basis):
    record = basis['record']
    return ([record['body'][name] or '' for name in EDIT_FIELDS[record['kind']]] if record
            else [basis['session']['rationale']])


def same_text(texts, other):
    return [unicodedata.normalize('NFC', t) for t in texts] == [unicodedata.normalize('NFC', t) for t in other]


def writing_snapshot(app, active=None, *, pooled=False):
    inputs, metadata = dict(app.review.unfinished), deepcopy(app.review.unfinished_basis)
    if active and active[0] == 'review':
        key, basis, texts, field = active[1]
        key = tuple(key)
        inputs[key], metadata[key] = texts, {'basis': basis, 'field': field}
    rows = []
    for key, texts in sorted(inputs.items()):
        if key not in metadata:
            raise ContractError('Unfinished review writing lacks its original context; live text is retained.')
        meta = metadata[key]
        try:
            texts = normalize(list(texts), array(EMPTY_TEXT, 2, 1))
        except ContractError as error:
            raise ContractError('Unfinished ' + key[-1] + ' at ' + '/'.join(key[:-1]) +
                                ': shorten the input; keep this session open. ' + str(error)) from None
        if same_text(texts, baseline(meta['basis'])):
            continue
        rows.append({'owner': list(app.full_context(key[:-1])), 'mode': key[-1],
                     'texts': list(texts), **meta})
    return pack_writing(rows) if pooled else rows


def restore_writing(history, value):
    inputs, metadata, sources = {}, {}, {}
    prefixes = {len(history.commands): history}
    for row in writing_rows(value):
        key = (*row['owner'], row['mode'])
        if key in inputs:
            raise ContractError('Duplicate unfinished review input.')
        # This map belongs only to this validation over one exact saved history.
        # Different prefixes, episodes and refs cannot borrow a source projection.
        # Shared view/record projections are read-only; never mutate them here.
        owner, basis = row['owner'], row['basis']
        source_key = (basis['source']['commands'], *owner[:2])
        if source_key not in sources:
            count = basis['source']['commands']
            if count not in prefixes:
                prefixes[count] = original_history(history, basis)
            # Only the immutable history is common across branch groups.
            # Their queried projections and every row's checks stay separate.
            original = prefixes[count]
            sources[source_key] = [original, query(original, owner), None]
        context = sources[source_key]
        if row['mode'].startswith('change:') and context[2] is None:
            context[2] = {item['id']: item for item in context[0].view(owner[1], episode_id=owner[0])['changes']}
        kept = _validate_basis(context[0], context[1], owner, row['mode'], basis, context[2])
        if len(row['texts']) != len(kept) or row['field'] >= len(kept) or same_text(row['texts'], kept):
            raise ContractError('Unfinished review fields differ from their owned editor shape or kept text.')
        inputs[key] = row['texts']
        metadata[key] = {'basis': row['basis'], 'field': row['field']}
    return inputs, metadata
