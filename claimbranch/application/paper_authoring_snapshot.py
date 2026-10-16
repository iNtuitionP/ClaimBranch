"""Closed unaccepted authoring state, bound to replayable source prefixes.

History is stored once by PaperWork. A prefix plus its query digest reconstructs
original scientific content and contributions; no projection is trusted on load.
"""
from copy import deepcopy

from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_changes import partial_amendment_schema
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, ID, array, normalize, nullable, obj
from .paper_intake import FIELDS, PaperResultIntake
from .paper_workspace_snapshot import EDITOR_TEXT, NUMBER, OWNER


RECORD = partial_amendment_schema()
SOURCE = obj(commands={'type': 'integer', 'minimum': 0, 'maximum': 64}, digest=HASH)
CANDIDATE = obj(owner=OWNER, source=SOURCE, records=array(RECORD, 64),
    selected=array(ID, 64, unique=True), omitted=array(ID, 64, unique=True),
    aliases=array(obj(id=ID, alias={'type': 'string', 'pattern': '^D[1-9][0-9]*$', 'maxLength': 17}), 64),
    next_alias=NUMBER, revision=NUMBER, unfinished=array(RECORD, 64))
INTAKE = obj(sequence=NUMBER, items=array(obj(id=ID, number=NUMBER, owner=OWNER, source=SOURCE,
    kept=obj(**dict.fromkeys(FIELDS, EDITOR_TEXT)),
    unfinished=array(obj(field={'enum': list(FIELDS)}, text=EDITOR_TEXT), len(FIELDS))), 16))
AUTHORING = obj(candidates=array(CANDIDATE, 16), intake=INTAKE)


def source_reference(current, source, digest):
    if source.seed != current.seed or current.commands[:len(source.commands)] != source.commands:
        raise ContractError('Draft source is not a prefix of this paper history; writing is retained.')
    return {'commands': len(source.commands), 'digest': digest}


def authoring_snapshot(app, active=None):
    candidates = []
    inputs = deepcopy(app.review.candidate_inputs)
    if active and active[0] == 'candidate':
        owner, record = active[1]
        inputs.setdefault(tuple(owner), {})[record['id']] = deepcopy(record)
    if set(inputs) - set(app.paper._candidates):
        raise ContractError('Unfinished candidates require their original owning work.')
    for owner, work in sorted(app.paper._candidates.items()):
        unfinished = [record for key, record in inputs.get(owner, {}).items()
                      if record != work.records.get(key)]
        candidates.append({'owner': list(owner),
            'source': source_reference(app.paper.history, work._bound_history, work._binding[0]),
            'records': list(work.records.values()), 'selected': sorted(work._selected),
            'omitted': sorted(work._omitted),
            'aliases': [{'id': key, 'alias': alias} for key, alias in work._aliases.items()],
            'next_alias': work._next_alias, 'revision': work.revision,
            'unfinished': unfinished})
    items = []
    for key, original in app.intake._items.items():
        item = deepcopy(original)
        if active and active[0] == 'intake' and active[1][0] == key:
            _, field, text = active[1]
            text = app.intake._text(field, text)
            if text == item['kept'][field]: item['unfinished'].pop(field, None)
            else: item['unfinished'][field] = text
        if not app.intake._written(item):
            continue
        item['source'] = source_reference(app.paper.history, app.intake._sources[key], item['source']['digest'])
        item['owner'] = list(item['owner'])
        item['unfinished'] = [{'field': field, 'text': text} for field, text in sorted(item['unfinished'].items())]
        items.append(item)
    return {'candidates': candidates, 'intake': {'sequence': app.intake._sequence, 'items': items}}


def restore_authoring(workspace, value):
    """Install only in a detached fresh workspace; no review capabilities exist."""
    from claimbranch.core.paper_capacity import lifecycle_schema
    value = normalize(value, lifecycle_schema(AUTHORING) if workspace.history.schema_version in (4, 5, 14, 18) else AUTHORING, profile="paper" if workspace.history.schema_version in (4, 5, 14, 18) else "episode")
    from .paper_service import PaperService
    from .paper_candidates import PaperCandidates
    history = workspace.history
    prefixes = {len(history.commands): history}

    def original(binding, owner):
        count = binding['commands']
        if count > len(history.commands):
            raise ContractError('Draft source is outside saved history.')
        if count not in prefixes:
            prefixes[count] = ResearchHistory.replay(history.seed, history.commands[:count])
        source = prefixes[count]
        query = PaperService(source).query(owner[1], episode_id=owner[0])
        if query['digest'] != binding['digest'] or owner[2] not in {node['id'] for node in query['nodes']}:
            raise ContractError('Draft original source binding differs from replayed context.')
        return source, query

    inputs, seen = {}, set()
    for item in value['candidates']:
        owner = tuple(item['owner'])
        if owner in seen or owner not in workspace._drafts:
            raise ContractError('Candidate owner must be one unique saved judgment work.')
        seen.add(owner)
        source, query = original(item['source'], owner)
        work = PaperCandidates(workspace, owner, workspace._drafts[owner])
        records = {record['id']: record for record in item['records']}
        unfinished = {record['id']: record for record in item['unfinished']}
        aliases = {pair['id']: pair['alias'] for pair in item['aliases']}
        selected, omitted = set(item['selected']), set(item['omitted'])
        if (len(records) != len(item['records']) or len(unfinished) != len(item['unfinished'])
                or len(set(records) | set(unfinished)) > 64 or len(aliases) != len(item['aliases'])
                or len(set(aliases.values())) != len(aliases)
                or not set(records) <= set(aliases) or not set(aliases) <= set(records) | set(unfinished)
                or not selected <= set(records) or not omitted <= set(aliases) or selected & omitted
                or set(records) != selected | (omitted & set(records))
                or item['next_alias'] < 1
                or any(int(alias[1:]) >= item['next_alias'] for alias in aliases.values())):
            raise ContractError('Candidate identities, aliases or selection are inconsistent.')
        # Reuse the service's incomplete-record bounds, then restore historical
        # counters directly; replaying puts against the live owner would revoke work.
        for record in item['records'] + item['unfinished']:
            if record['id'] in records and record['kind'] != records[record['id']]['kind']:
                raise ContractError('Unfinished candidate changed its scientific kind.')
            work.put(record)
        work._records, work._selected, work._omitted = records, selected, omitted
        work._aliases, work._next_alias, work._revision = aliases, item['next_alias'], item['revision']
        work._bound_history, work._binding = source, (query['digest'], source.manifest())
        work._source_records = {record['id']: record for record in source.view(owner[1], episode_id=owner[0])['changes']}
        workspace._candidates[owner] = work
        if unfinished: inputs[owner] = unfinished

    intake = PaperResultIntake(workspace)
    numbers = set()
    intake._sequence = value['intake']['sequence']
    for item in value['intake']['items']:
        key, number, owner = item['id'], item['number'], tuple(item['owner'])
        if key in intake._items or number in numbers or not 1 <= number <= intake._sequence:
            raise ContractError('Result identity or sequence is inconsistent.')
        numbers.add(number)
        source, query = original(item['source'], owner)
        unfinished = {entry['field']: entry['text'] for entry in item['unfinished']}
        if len(unfinished) != len(item['unfinished']):
            raise ContractError('Duplicate unfinished result field.')
        if any(text == item['kept'][field] for field, text in unfinished.items()):
            raise ContractError('Unfinished result text must differ from its kept field.')
        intake._items[key] = {**item, 'owner': owner, 'source': query, 'unfinished': unfinished}
        intake._sources[key] = source
        if not intake._written(intake._items[key]):
            raise ContractError('Pristine result browsing cannot become saved pending work.')
    return inputs, intake
