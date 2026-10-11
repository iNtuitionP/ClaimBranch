"""Provisional result capture, before evidence confirmation exists.

These fields are provisional writing, never ResearchHistory records, review
inputs or provider context. Typed recovery preserves them as unaccepted writing. Source snapshots retain their own
judgments/contributions independently of the new tentative writing.
"""
from copy import deepcopy
import secrets
import unicodedata

from claimbranch.core.canonical import ContractError


FIELDS = {
    'observation': 'Observed content / still unconfirmed',
    'run_ref': 'Experiment / run reference',
    'source_ref': 'Result source reference / not opened',
    'conditions': 'Experimental conditions',
    'metric_name': 'Measurement name',
    'metric_definition': 'Measurement definition',
    'value': 'Reported value / text',
    'unit': 'Measurement unit',
    'comparison': 'Comparison / baseline',
    'uncertainty': 'Limitations / what remains unknown',
    'judgment': 'Tentative judgment / optional',
    'rationale': 'Reason for this judgment / optional',
}


class PaperResultIntake:
    def __init__(self, workspace):
        self.workspace = workspace
        self._items = {}
        self._sources = {}
        self._sequence = 0

    def create(self, owner):
        if (not isinstance(owner, (tuple, list)) or len(owner) != 3
                or not all(isinstance(value, str) for value in owner)):
            raise ContractError('Choose an existing episode, branch and source node.')
        if len(self._items) >= 16:
            raise ContractError('At most 16 result drafts per session. Existing writing is retained.')
        episode, ref, node = owner
        source = self.workspace.service.query(ref, episode_id=episode)
        if node not in {item['id'] for item in source['nodes']}:
            raise ContractError('The selected source is unavailable. No draft was created.')
        key = 'result-draft-' + secrets.token_hex(16)
        self._sequence += 1
        self._sources[key] = self.workspace.history
        self._items[key] = {'id': key, 'number': self._sequence, 'owner': tuple(owner),
                            'source': deepcopy(source), 'kept': dict.fromkeys(FIELDS, ''),
                            'unfinished': {}}
        return key

    def _item(self, key):
        if key not in self._items:
            raise ContractError('This result draft is no longer available.')
        return self._items[key]

    @staticmethod
    def _text(field, value):
        if not isinstance(field, str) or field not in FIELDS or not isinstance(value, str):
            raise ContractError('Choose a result-capture text field.')
        if len(value) > 12000:
            raise ContractError('12,000 character limit. Input remains in the editor.')
        try:
            value.encode('utf-8')
        except UnicodeError as error:
            raise ContractError('Invalid Unicode; existing text is retained.') from error
        value = unicodedata.normalize('NFC', value)
        if len(value) > 12000:
            raise ContractError('12,000 character limit after Unicode normalization. Existing text is retained.')
        return value

    def keep(self, key, field, value):
        value = self._text(field, value)
        item = self._item(key)
        item['kept'][field] = value
        item['unfinished'].pop(field, None)

    def retain(self, key, field, value):
        value = self._text(field, value)
        item = self._item(key)
        if value == item['kept'][field]:
            item['unfinished'].pop(field, None)
        else:
            item['unfinished'][field] = value

    def get(self, key):
        return deepcopy(self._item(key))

    @staticmethod
    def _written(item):
        return any(item['kept'].values()) or bool(item['unfinished'])

    def items(self):
        return [deepcopy(item) for item in self._items.values() if self._written(item)]

    def has_writing(self):
        return any(self._written(item) for item in self._items.values())

    def drop_empty(self, key):
        if key in self._items and not self._written(self._items[key]):
            del self._items[key]
            del self._sources[key]

    def remove(self, key):
        self._item(key)
        del self._items[key]
        del self._sources[key]

    def context(self, key):
        """Original context never silently becomes today's context or authority."""
        item = self._item(key)
        episode, ref, node = item['owner']
        try:
            current = self.workspace.service.query(ref, episode_id=episode)
            if (current['project_id'] != item['source']['project_id'] or
                    node not in {entry['id'] for entry in current['nodes']}):
                raise ContractError('Original subject unavailable in this project.')
        except ContractError:
            return {'status': 'Recorded context unavailable; original context retained.', 'current': None}
        return {'status': ('Recorded context unchanged.' if current['digest'] == item['source']['digest']
                           else 'Recorded context changed; writing retains its original basis.'),
                'current': deepcopy(current)}

    def recorded_copy(self,key):
        """Find the separately recorded copy; edited capture remains a draft."""
        item=self._item(key)
        target='observation-'+key.removeprefix('result-draft-')
        episode,ref,_=item['owner']
        return next((o for o in self.workspace.history.view(ref,episode_id=episode)['evidence']
                     if o['id']==target),None)
