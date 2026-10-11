"""Retain open explanation writing; reconstruct cause and basis from history."""
import unicodedata

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import ID, array, normalize, nullable, obj
from .paper_authoring_snapshot import SOURCE, source_reference
from .paper_understanding import DRAFT, PaperUnderstandingSession
from .paper_workspace_snapshot import EDITOR_TEXT

UNDERSTANDING = obj(
    sessions=array(obj(source=SOURCE, draft=DRAFT), 16),
    buffers=array(obj(work_id=ID, topic_id=ID, text=EDITOR_TEXT), 48),
    positions=array(obj(work_id=ID, index={'type': 'integer', 'minimum': 0, 'maximum': 2}), 16),
    work_id=nullable(ID))


def explanation_snapshot(app, active=None):
    work = app.understanding
    buffers = dict(work.buffers)
    if active and active[0] == 'understanding':
        work_id, topic_id, text = active[1]
        if work_id not in work.sessions:
            raise ContractError('Explanation editor requires its original work.')
        buffers[work_id, topic_id] = text
    sessions, positions, retained = [], [], set()
    # A pristine read is not pending work. Empty edits differing from kept text
    # are writing, while typing back to the kept value clears redundant input.
    for work_id, session in work.sessions.items():
        draft = decode(session.snapshot())
        entries = {entry['topic_id']: entry for entry in draft['entries']}
        for key in [key for key in buffers if key[0] == work_id]:
            if key[1] not in entries:
                raise ContractError('Unfinished explanation requires an owned topic.')
            if unicodedata.normalize('NFC', buffers[key]) == entries[key[1]]['text']:
                del buffers[key]
        if not (any(entry['text'] or entry['reuse_rationale'] for entry in entries.values())
                or any(key[0] == work_id for key in buffers)):
            continue
        retained.add(work_id)
        sessions.append({'source': source_reference(app.paper.history, session._history, session._context['digest']),
                         'draft': draft})
        positions.append({'work_id': work_id, 'index': work.positions.get(work_id, 0)})
    if any(key[0] not in retained for key in buffers):
        raise ContractError('Unfinished explanation requires a retained work.')
    return {'sessions': sessions,
            'buffers': [{'work_id': key[0], 'topic_id': key[1], 'text': text}
                        for key, text in sorted(buffers.items())],
            'positions': positions, 'work_id': work.work_id if work.work_id in retained else None}


def restore_explanations(history, value):
    """Build detached services and text; no closure, review, provider or file I/O."""
    value = normalize(value, UNDERSTANDING)
    sessions, sources, buffers, positions = {}, {}, {}, {}
    prefixes = {len(history.commands): history}
    project = decode(history.seed)['project_id']
    groups, seen = {}, set()
    for item in value['sessions']:
        draft, source = item['draft'], item['source']
        key, count = draft['work_id'], source['commands']
        if key in seen or count > len(history.commands):
            raise ContractError('Duplicate explanation or source outside saved history.')
        seen.add(key)
        if count not in prefixes:
            prefixes[count] = ResearchHistory.replay(history.seed, history.commands[:count])
        groups.setdefault(count, []).append(canonical_bytes(draft))
    restored = {}
    for count, drafts in groups.items():
        for session in PaperUnderstandingSession.restore_many(prefixes[count], project_id=project, drafts=drafts):
            restored[session._work_id] = session
    # Preserve the original session order even when source prefixes interleave.
    for item in value['sessions']:
        source, key = item['source'], item['draft']['work_id']
        session, original = restored[key], prefixes[source['commands']]
        if session._context['digest'] != source['digest']:
            raise ContractError('Saved explanation source differs from its original context.')
        sessions[key], sources[key] = session, original
    for item in value['buffers']:
        key = item['work_id'], item['topic_id']
        if key in buffers or key[0] not in sessions:
            raise ContractError('Duplicate or unowned unfinished explanation.')
        entries = {entry['topic_id']: entry for entry in decode(sessions[key[0]].snapshot())['entries']}
        if key[1] not in entries or entries[key[1]]['text'] == item['text']:
            raise ContractError('Unfinished explanation requires a distinct owned topic edit.')
        buffers[key] = item['text']
    for item in value['positions']:
        key = item['work_id']
        if (key in positions or key not in sessions
                or item['index'] >= len(decode(sessions[key].snapshot())['entries'])):
            raise ContractError('Explanation return position requires one existing topic.')
        positions[key] = item['index']
    if set(positions) != set(sessions) or (value['work_id'] is not None and value['work_id'] not in sessions):
        raise ContractError('Explanation return context differs from saved work.')
    for key, session in sessions.items():
        if not (any(entry['text'] or entry['reuse_rationale'] for entry in decode(session.snapshot())['entries'])
                or any(owner == key for owner, _ in buffers)):
            raise ContractError('Pristine explanation browsing is not saved pending work.')
    return {'sessions': sessions, 'sources': sources, 'buffers': buffers,
            'positions': positions, 'work_id': value['work_id']}
