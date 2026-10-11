"""Bounded session-only manual authoring owned by an existing paper context.

Incomplete fields are retained as text. Only the domain may project them as
valid science; neither selection nor projection changes source history.
"""
from copy import deepcopy
import secrets

from claimbranch.core.canonical import ContractError, canonical_bytes
from claimbranch.core.paper_changes import amendment_schema


FIELDS = {item['properties']['kind']['const']: tuple(item['properties']['body']['properties'])
          for item in amendment_schema()['items']['oneOf']}


def interpretation_unavailable(workspace, owner, records=()):
    """Explain the existing domain limit without allocating a draft session."""
    episode, ref, _ = owner
    view = workspace.history.view(ref, episode_id=episode)
    owners = view.get('interpretation_episode_ids', {})
    if any(item['kind'] == 'interpretation' and owners.get(item['id'], episode) == episode
           for item in view['changes']):
        return 'This episode already has an interpretation here. Use Edit scientific changes to revise it.'
    if any(item['kind'] == 'interpretation' for item in records):
        return 'This work already has an interpretation draft. Use Open argument drafts to continue it.'
    return ''


class PaperCandidates:
    def __init__(self, workspace, owner, session):
        self.workspace, self._owner, self.session = workspace, tuple(owner), session
        self._records, self._selected = {}, set()
        self._origins = {}
        self._omitted = set()
        self._aliases = {}
        self._next_alias = 1
        self._revision = 0
        self._binding = self._source_binding()
        self._bound_history = workspace.history
        self._source_records = self._current_records()

    @property
    def owner(self):
        return self._owner

    @property
    def revision(self):
        return self._revision

    @property
    def records(self):
        return deepcopy(self._records)

    @property
    def selected(self):
        return frozenset(self._selected)

    @property
    def origins(self):
        return dict(self._origins)

    def _source_binding(self):
        episode, ref, node = self.owner
        view = self.workspace.service.query(ref, episode_id=episode)
        if node not in {item['id'] for item in view['nodes']}:
            raise ContractError('The owning source is missing; candidate text is retained.')
        return view['digest'], self.workspace.history.manifest()

    def require_current(self):
        if self._bound_history is self.workspace.history:
            return
        if self._binding != self._source_binding():
            raise ContractError('Source changed. Candidate text is retained; refresh its source before graph or review.')

    def _current_records(self):
        episode, ref, _ = self.owner
        return {item['id']: item for item in self.workspace.history.view(ref, episode_id=episode)['changes']}

    def source_changes(self, unfinished=()):
        if self._bound_history is self.workspace.history:
            return []
        current = self._current_records()
        changes = []
        for layer, records in (('kept', self.records.values()), ('unfinished', unfinished)):
            for record in records:
                key = record['id']
                old, new = self._source_records.get(key), current.get(key)
                if old and old != new:
                    changes.append({'id': key, 'layer': layer, 'previous': deepcopy(old['body']),
                                    'current': deepcopy(new['body']) if new else None,
                                    'candidate': deepcopy(record['body'])})
        return changes

    def refresh_source(self, *, expected_changes=None, unfinished=()):
        binding = self._source_binding()
        changes = self.source_changes(unfinished)
        if changes and changes != expected_changes:
            raise ContractError('Source records changed. Compare current source with retained drafts before rebinding.')
        if binding != self._binding:
            self._binding = binding
            self._bound_history = self.workspace.history
            self._source_records = self._current_records()
            self._changed()

    def _changed(self):
        self._revision += 1
        self.session.invalidate_change_reviews()

    def create(self, kind, body):
        if kind not in ('claim', 'scientific-edge', 'experiment-plan', 'interpretation'):
            raise ContractError('This authoring path creates claims, interpretations, scientific connections and unrun plans only.')
        if kind == 'interpretation':
            reason = interpretation_unavailable(self.workspace, self.owner, self.records.values())
            if reason:
                raise ContractError(reason)
        key = self.allocate_id()
        self.put({'id': key, 'kind': kind, 'body': body})
        return key

    @staticmethod
    def allocate_id():
        return 'draft-' + secrets.token_hex(16)

    def put(self, record):
        # Bound incomplete editor input without silently normalizing its meaning.
        if not isinstance(record, dict) or set(record) != {'id', 'kind', 'body'}:
            raise ContractError('A candidate requires an id, kind and body.')
        kind, body, key = record['kind'], record['body'], record['id']
        if kind not in FIELDS or not isinstance(body, dict) or set(body) != set(FIELDS[kind]):
            raise ContractError('Candidate fields do not match their scientific kind.')
        if kind == 'experiment-plan':
            metric = body['metric']
            if (not isinstance(metric, dict) or set(metric) != {'name', 'definition', 'unit', 'comparison'}
                    or any(not isinstance(value, str) for value in metric.values())):
                raise ContractError('Plan measurement requires name, definition, unit and comparison text; blanks may be kept.')
        if not isinstance(key, str) or not key or len(key) > 128:
            raise ContractError('Candidate identity is invalid.')
        size = len(canonical_bytes(record))  # Always enforces the shared canonical byte/string bounds.
        if kind != 'experiment-plan' and size > 70_000:
            raise ContractError('Candidate text is too large; shorten the fields. Existing work is retained.')
        if key not in self._records and len(self._records) >= 64:
            raise ContractError('This work holds at most 64 candidates; existing work is retained.')
        new = key not in self._records
        previous = self._origins.get(key) or self.workspace.origin_for(key)
        revised = previous.revise(record) if previous else None
        if revised is not None:
            from .paper_proposal_work import check_capacity, proposal_snapshot
            origins = {**self._origins, key: revised}
            check_capacity(self.workspace, proposal_snapshot(self.workspace, origins={self.owner: origins}),
                           records={self.owner: {**self._records, key: record}})
        self._records[key] = deepcopy(record)
        if revised is not None:
            self._origins[key] = revised
        if key not in self._aliases:
            self._aliases[key] = 'D' + str(self._next_alias)
            self._next_alias += 1
        if new and key not in self._omitted:
            self._selected.add(key)
        self._changed()

    def alias(self, key):
        """Session-stable draft alias; removed candidates never renumber survivors."""
        return self._aliases[key]

    def toggle(self, key):
        if key not in self._records:
            raise ContractError('Keep the candidate before selecting it for review.')
        if key in self._selected:
            self._selected.remove(key)
            self._omitted.add(key)
        else:
            self._selected.add(key)
            self._omitted.discard(key)
        self._changed()

    def dependents(self, key):
        return self.dependent_ids(list(self._records.values()), key)

    @staticmethod
    def dependent_ids(records, key):
        found, pending = set(), [key]
        while pending:
            target = pending.pop()
            for record in records:
                candidate = record['id']
                body = record['body']
                refs = [body.get(field) for field in ('source_id', 'target_id', 'claim_id')]
                refs += body.get('parent_ids', []) + body.get('observation_ids', []) + body.get('basis_ids', [])
                if target in refs and candidate != key and candidate not in found:
                    found.add(candidate)
                    pending.append(candidate)
        return sorted(found)

    def unkeep(self, key):
        record = self.records[key]
        self._records.pop(key)
        self._selected.discard(key)
        self._changed()
        return record

    def discard_identity(self, key):
        if key not in self._records:
            self._aliases.pop(key, None)
            self._omitted.discard(key)
            self._origins.pop(key, None)

    def remove(self, key, *, with_dependents=False):
        if key not in self._records:
            raise ContractError('This candidate is no longer in the work.')
        keys = {key, *(self.dependents(key) if with_dependents else [])}
        for item in keys:
            self._records.pop(item)
            self._selected.discard(item)
            self._aliases.pop(item, None)
            self._omitted.discard(item)
            self._origins.pop(item, None)
        self._changed()

    def project(self):
        self.require_current()
        episode, ref, _ = self.owner
        return self.workspace.service.project_draft(ref, list(self.records.values()), episode_id=episode)
