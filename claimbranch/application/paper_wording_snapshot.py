"""Original manuscript writing and supplied bytes; never a resumed review."""
import base64
import hashlib
import unicodedata

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import ID, HASH, array, command_schema, normalize, nullable, obj
from .paper_workspace_snapshot import SESSION, EMPTY_TEXT, session_snapshot, restore_session
from .paper_manuscript import PaperManuscriptSession
from .paper_service import PaperService

# Encode exact artifact/path bytes outside canonical JSON's NFC normalization.
BYTES = array({'type': 'string', 'maxLength': 10924, 'minLength': 1}, 8)
HISTORY = obj(count={'type': 'integer', 'minimum': 0, 'maximum': 64},
              suffix=array(command_schema(3), 2), digest=HASH)
PARENT = obj(owner=array(ID, 4, 2), review_digest=HASH)
WORDING = obj(sessions=array(obj(key=ID, work_id=ID, history=HISTORY, draft=SESSION,
    source_digest=nullable(HASH), path=BYTES,
    parent=nullable(PARENT)), 32),
    sources=array(obj(digest=HASH, content=BYTES), 32),
    buffers=array(obj(key=ID, mode={'enum': ['wording', 'source']},
        texts=array(EMPTY_TEXT, 2, 1), field={'type': 'integer', 'minimum': 0, 'maximum': 1}), 64),
    work_id=nullable(ID))


def pack(raw):
    return [base64.b64encode(raw[i:i + 8192]).decode('ascii') for i in range(0, len(raw), 8192)]


def unpack(chunks):
    try:
        raw = b''.join(base64.b64decode(chunk, validate=True) for chunk in chunks)
        if pack(raw) != chunks or len(raw) > 65536:
            raise ValueError()
        raw.decode('utf-8')
        return raw
    except (ValueError, UnicodeError):
        raise ContractError('Invalid exact manuscript source/path encoding.') from None


def fingerprint(history):
    return digest({'seed': decode(history.seed), 'commands': [decode(c) for c in history.commands]})


def history_reference(current, original):
    if original.seed != current.seed:
        raise ContractError('Wording belongs to another paper.')
    count = 0
    for before, after in zip(current.commands, original.commands):
        if before != after: break
        count += 1
    return {'count': count, 'suffix': [decode(c) for c in original.commands[count:]],
            'digest': fingerprint(original)}


def wording_snapshot(app, active=None):
    work = app.manuscript
    buffers = {key: list(texts) for key, texts in work.buffers.items() if key[1] in ('wording', 'source')}
    positions = dict(work.positions)
    if active and active[0] == 'manuscript':
        key, mode, texts, field = active[1]
        buffers[key, mode], positions[key, mode] = list(texts), field
    sessions, retained, sources = [], set(), {}
    for key, session in work.sessions.items():
        draft = session_snapshot(session.draft)
        defaults = {'wording': [draft['text'], draft['rationale']], 'source': [work.paths.get(key, '')]}
        for mode in defaults:
            pair = key, mode
            if pair in buffers and [unicodedata.normalize('NFC', t) for t in buffers[pair]] == [unicodedata.normalize('NFC', t) for t in defaults[mode]]:
                del buffers[pair]
        if not (draft['text'] or draft['rationale'] or draft['judgment']['history'] or any(k[0] == key for k in buffers)):
            continue
        parent = work.parents.get(key)
        source = session._source
        source_digest = hashlib.sha256(source).hexdigest() if source is not None else None
        if source is not None: sources[source_digest] = pack(source)
        sessions.append({'key': key, 'work_id': session._work_id,
            'history': history_reference(app.paper.history, session._history), 'draft': draft,
            'source_digest': source_digest,
            'path': pack(work.paths.get(key, '').encode('utf-8')),
            'parent': {'owner': list(parent['owner']), 'review_digest': parent['review_digest']} if parent else None})
        retained.add(key)
    if any(key not in retained for key, _ in buffers):
        raise ContractError('Unfinished wording requires its original work.')
    return {'sessions': sessions, 'sources': [{'digest': key, 'content': content} for key, content in sorted(sources.items())],
        'buffers': [{'key': key, 'mode': mode, 'texts': texts,
        'field': positions.get((key, mode), 0)} for (key, mode), texts in sorted(buffers.items())],
        'work_id': work.work_id if work.work_id in retained else None}


def restore_wording(history, value, *, clock=None):
    value = normalize(value, WORDING)
    sessions, paths, parents, buffers, positions, restored = {}, {}, {}, {}, {}, {}
    sources = {}
    for row in value['sources']:
        raw = unpack(row['content'])
        if row['digest'] in sources or not raw or hashlib.sha256(raw).hexdigest() != row['digest']:
            raise ContractError('Duplicate or invalid original manuscript source.')
        sources[row['digest']] = raw
    for row in value['sessions']:
        key, ref = row['key'], row['history']
        if key in sessions or ref['count'] > len(history.commands):
            raise ContractError('Duplicate manuscript draft or unavailable original history.')
        original = ResearchHistory.replay(history.seed, history.commands[:ref['count']] +
                                          tuple(canonical_bytes(c) for c in ref['suffix']))
        if fingerprint(original) != ref['digest']:
            raise ContractError('Original manuscript history fingerprint changed.')
        if row['source_digest'] is not None and row['source_digest'] not in sources:
            raise ContractError('Original manuscript source is unavailable in the checkpoint.')
        source = sources.get(row['source_digest'])
        session = PaperManuscriptSession(original, work_id=row['work_id'], source=source, clock=clock)
        restore_session(session.draft, row['draft'])
        parent = row['parent']
        if parent:
            owner = tuple(parent['owner'])
            if (key != 'candidate-' + parent['review_digest'] or not original.commands or source is None
                    or not ((len(owner) == 2 and owner[0] == 'recorded') or
                            (len(owner) == 4 and owner[0] == 'draft' and owner[2] in ('main', 'alternative')))):
                raise ContractError('Detached wording requires its original parent identity.')
            command = decode(original.commands[-1])
            item = session.state()['work']
            if (command['operation_type'] != 'apply-selected-merge' or command['id'] != item['cause_operation_id']
                    or owner[1] != command['episode_id']):
                raise ContractError('Detached wording differs from its scientific cause.')
            before = ResearchHistory.replay(history.seed, original.commands[:-1])
            if len(owner) == 4 and owner[3] not in {n['id'] for n in PaperService(before).query(owner[2], episode_id=owner[1])['nodes']}:
                raise ContractError('Detached wording owner is absent from its source.')
            science = PaperService(before).preview_merge(command['payload']['selected_ids'], episode_id=owner[1])
            parents[key] = {'flow': None, 'owner': owner, 'review_digest': parent['review_digest'],
                            'source_digest': row['source_digest'], 'history': original, 'science': science}
        elif key != row['work_id'] or ref['suffix']:
            raise ContractError('Recorded wording requires a recorded work and history prefix.')
        path = unpack(row['path']).decode('utf-8')
        if path: paths[key] = path
        sessions[key], restored[key] = session, row['source_digest']
    if len(parents) > 16 or len(sessions) - len(parents) > 16:
        raise ContractError('Manuscript draft capacity exceeded.')
    if set(sources) != {v for v in restored.values() if v is not None}:
        raise ContractError('Unreferenced manuscript source in checkpoint.')
    for row in value['buffers']:
        pair = row['key'], row['mode']
        count = 2 if row['mode'] == 'wording' else 1
        if (pair in buffers or pair[0] not in sessions or len(row['texts']) != count or row['field'] >= count):
            raise ContractError('Invalid unfinished manuscript editor ownership or fields.')
        buffers[pair], positions[pair] = row['texts'], row['field']
    if value['work_id'] is not None and value['work_id'] not in sessions:
        raise ContractError('Invalid manuscript return identity.')
    for key, session in sessions.items():
        draft = session.draft.state()['draft']
        if not (draft['text'] or draft['rationale'] or draft['contributions'] or any(k[0] == key for k in buffers)):
            raise ContractError('Pristine manuscript browsing is not saved writing.')
    return dict(sessions=sessions, paths=paths, parents=parents, buffers=buffers,
                positions=positions, restored=restored, work_id=value['work_id'])
