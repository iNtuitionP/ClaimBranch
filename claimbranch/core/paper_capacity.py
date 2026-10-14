"""Registered personal-paper budgets; never provider or protected authority."""
import base64
import hashlib
import json
import unicodedata

from .canonical import ContractError, _normalize

LIMITS = dict(commands=2048, events=1024, observations=256, experiments=256,
              claims=64, edges=512, plans=64, changes=1024, depth=8,
              episodes=32, interpretations=32)
HISTORY_BYTES = 4 * 1024 * 1024
MANIFEST_BYTES = 8 * 1024 * 1024
PROJECT_BYTES = 16 * 1024 * 1024


def lifecycle_schema(schema):
    """Version-4 writing references can name the larger retained history prefix."""
    from copy import deepcopy
    result = deepcopy(schema)
    def walk(value):
        if type(value) is dict:
            properties = value.get('properties', {})
            if set(properties) == {'commands','digest'}:
                properties['commands']['maximum'] = LIMITS['commands']
            for child in value.values(): walk(child)
        elif type(value) is list:
            for child in value: walk(child)
    walk(result)
    return result


def select_paper_changes(changes, selected, evidence_ids):
    from .canonical import identifier
    from .review import Selection
    for values in (changes, selected, evidence_ids):
        if type(values) is not tuple or len(values) > 2048:
            raise ContractError('bounded personal-paper selection required')
    if not all(isinstance(change, PaperChange) for change in changes):
        raise ContractError('typed personal-paper changes required')
    for value in (*selected, *evidence_ids): identifier(value)
    by_id = {change.id: change for change in changes}
    if len(by_id)!=len(changes) or len(set(selected))!=len(selected) or len(set(evidence_ids))!=len(evidence_ids):
        raise ContractError('duplicate personal-paper selection')
    if set(by_id)&set(evidence_ids) or not set(selected)<=set(by_id):
        raise ContractError('invalid personal-paper selection')
    closure, evidence, pending = set(), set(), list(selected)
    while pending:
        current = pending.pop()
        if current in evidence_ids: evidence.add(current)
        elif current not in by_id: raise ContractError('missing personal-paper dependency')
        elif current not in closure:
            closure.add(current)
            pending.extend(by_id[current].dependencies)
    return Selection(tuple(sorted(selected)), tuple(sorted(closure-set(selected))),
        tuple(sorted(set(by_id)-closure)), tuple(sorted(evidence)), tuple(sorted(changes,key=lambda c:c.id)))


from .review import Change


class PaperChange(Change):
    def __post_init__(self):
        from .canonical import identifier
        identifier(self.id)
        if self.kind not in ('claim','claim-status','interpretation','scientific-edge','experiment-plan'):
            raise ContractError('only personal-paper reasoning may be selected')
        if type(self.dependencies) is not tuple or len(self.dependencies)>1024:
            raise ContractError('personal-paper dependency bound exceeded')
        for value in self.dependencies: identifier(value)
        if len(set(self.dependencies))!=len(self.dependencies): raise ContractError('duplicate dependency')


def encode(value, *, purpose):
    maximum = {'history': HISTORY_BYTES, 'manifest': MANIFEST_BYTES, 'project': PROJECT_BYTES}[purpose]
    raw = json.dumps(_normalize(value, collection_limit=2048), ensure_ascii=False,
                     sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw) > maximum:
        raise ContractError('capacity %s-bytes: %s / %s' % (purpose, len(raw), maximum))
    return raw


def decode(raw, *, purpose):
    maximum = {'history': HISTORY_BYTES, 'manifest': MANIFEST_BYTES, 'project': PROJECT_BYTES}[purpose]
    if type(raw) is not bytes or len(raw) > maximum:
        raise ContractError('capacity %s-bytes: bounded bytes <= %s required' % (purpose, maximum))
    def pairs(items):
        result = {}
        for key, value in items:
            key = unicodedata.normalize('NFC', key)
            if key in result: raise ContractError('duplicate normalized object key')
            result[key] = value
        return result
    def reject(_): raise ContractError('floating/nonfinite values refused')
    try:
        return _normalize(json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
            parse_float=reject, parse_constant=reject), collection_limit=2048)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ContractError('invalid personal-paper JSON') from error


def source_record(raw):
    if type(raw) is not bytes or len(raw) > HISTORY_BYTES:
        raise ContractError('retained source requires bounded original bytes')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'chunks': [base64.b64encode(raw[i:i+12288]).decode('ascii')
                       for i in range(0, len(raw), 12288)]}


def source_bytes(record):
    if type(record) is not dict or set(record) != {'sha256', 'bytes', 'chunks'}:
        raise ContractError('invalid retained source')
    if type(record['bytes']) is not int or not 0 <= record['bytes'] <= HISTORY_BYTES:
        raise ContractError('retained source byte limit exceeded')
    chunks = record['chunks']
    if type(chunks) is not list or len(chunks) > 342:
        raise ContractError('retained source chunk limit exceeded')
    try:
        pieces = [base64.b64decode(chunk, validate=True) for chunk in chunks
                  if type(chunk) is str and len(chunk) <= 16384]
    except (ValueError, UnicodeError) as error: raise ContractError('invalid source base64') from error
    if len(pieces) != len(chunks) or any(len(p) != 12288 for p in pieces[:-1]):
        raise ContractError('noncanonical retained source chunks')
    raw = b''.join(pieces)
    if source_record(raw) != record: raise ContractError('retained source digest/length/chunks mismatch')
    return raw
