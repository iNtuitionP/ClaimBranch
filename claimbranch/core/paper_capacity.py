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
    return _encoding(value,purpose=purpose)[1]


def encoding_value(value, *, purpose):
    """Owned, canonically ordered projection input under all encoding checks.

    Shared subvalues belong only to this detached validation tree. Its caller
    treats nested values as read-only and serializes any externally returned data.
    """
    normalized,_=_encoding(value,purpose=purpose);seen=set()
    def order(item):
        if type(item) not in (dict,list) or id(item) in seen:return
        seen.add(id(item))
        if type(item) is dict:
            pairs=sorted(item.items());item.clear();item.update(pairs)
            children=item.values()
        else:children=item
        for child in children:order(child)
    order(normalized)
    return normalized


def _encoding(value, *, purpose):
    maximum = {'history': HISTORY_BYTES, 'manifest': MANIFEST_BYTES, 'project': PROJECT_BYTES}[purpose]
    # Only the private encoding tree may share aliases. Public values are parsed
    # from bytes; traversal-local memoization cannot affect later mutations.
    normalized = _normalize(value, collection_limit=2048,_memo={})
    raw = json.dumps(normalized, ensure_ascii=False,
                     sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw) > maximum:
        raise ContractError('capacity %s-bytes: %s / %s' % (purpose, len(raw), maximum))
    return normalized,raw


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


def encoded_size(value, *, purpose):
    """Exact canonical size/bounds without allocating repeated JSON payloads.

    The memo belongs to this synchronous traversal only. It retains no trust or
    mutable value across calls. NFC keys, escaping and all canonical limits are
    checked exactly as encode(); sorting cannot change the byte count.
    """
    from .canonical import integer
    memo={};strings={}
    def size(item,depth):
        if depth>16:raise ContractError('JSON nesting limit exceeded')
        if item is None:return 4
        if type(item) is bool:return 4 if item else 5
        if type(item) is int:
            integer(item,-(2**53-1));return len(str(item))
        if isinstance(item,str):
            if type(item) is str and item in strings:return strings[item]
            if len(item.encode('utf-8'))>16384:raise ContractError('JSON string limit exceeded')
            total=len(json.dumps(unicodedata.normalize('NFC',item),ensure_ascii=False).encode('utf-8'))
            if type(item) is str and len(item)<=256 and len(strings)<2048:strings[item]=total
            return total
        if type(item) not in (dict,list,tuple):raise ContractError('unsupported JSON value')
        key=(id(item),depth)
        if key in memo:return memo[key]
        if len(item)>2048:raise ContractError('JSON collection limit exceeded')
        if type(item) is dict:
            names=set();total=2+max(0,len(item)-1)
            for name,child in item.items():
                if not isinstance(name,str):raise ContractError('object keys must be text')
                n=unicodedata.normalize('NFC',name)
                if n in names:raise ContractError('normalized object keys collide')
                names.add(n);total+=size(name,depth+1)+1+size(child,depth+1)
        else:total=2+max(0,len(item)-1)+sum(size(child,depth+1) for child in item)
        memo[key]=total;return total
    try:total=size(value,0)
    except UnicodeError as error:raise ContractError('invalid Unicode') from error
    maximum={'history':HISTORY_BYTES,'manifest':MANIFEST_BYTES,'project':PROJECT_BYTES}[purpose]
    if total>maximum:raise ContractError('capacity %s-bytes: %s / %s'%(purpose,total,maximum))
    return total


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


SHARED_AUDIT = 'claimbranch.shared-audit-manifest/v1'
_AUDIT_KEYS = {'schema_version','authority','seed','commands','evidence_events','views',
               'selected_merges','active_episode_id','episodes'}


def pack_shared_audit(value):
    """Lossless explicit field sharing; the stored audit still obeys 8 MiB.

    Expanded logical JSON is independently bounded at 16 MiB. Only view fields
    are shared; seed/commands remain readable and replayable without a decoder.
    """
    if type(value) is not dict or set(value)!=_AUDIT_KEYS or value['schema_version']!=14:
        raise ContractError('shared audit requires the complete imported logical manifest')
    expanded=encode(value,purpose='project')
    result={key:val for key,val in value.items() if key!='views'};pool={};views={}
    for ref,view in sorted(value['views'].items()):
        fields={}
        for field,item in sorted(view.items()):
            raw=encode(item,purpose='project')
            if len(raw)>=1024:
                key=hashlib.sha256(raw).hexdigest()
                if key in pool and pool[key]!=item:raise ContractError('shared audit value hash collision')
                if key not in pool and len(pool)>=2048:raise ContractError('capacity audit-shared-values: 2049 / 2048')
                pool[key]=item;fields[field]={'ref':key}
            else:fields[field]={'inline':item}
        views[ref]=fields
    result.update(schema=SHARED_AUDIT,views=views,shared_values=pool,
        expanded_bytes=len(expanded),expanded_sha256=hashlib.sha256(expanded).hexdigest())
    return encode(result,purpose='manifest')


def expand_shared_audit(raw):
    """Checked lossless reading only; replay/source validity is a separate check."""
    value=decode(raw,purpose='manifest')
    extras={'schema','shared_values','expanded_bytes','expanded_sha256'}
    if (type(value) is not dict or set(value)!=_AUDIT_KEYS|extras
            or value['schema']!=SHARED_AUDIT or value['schema_version']!=14
            or type(value['expanded_bytes']) is not int or not 0<=value['expanded_bytes']<=PROJECT_BYTES
            or type(value['views']) is not dict or type(value['shared_values']) is not dict):
        raise ContractError('invalid shared audit envelope')
    from .canonical import digest_text
    digest_text(value['expanded_sha256']);pool=value['shared_values'];lengths={}
    for key,item in pool.items():
        digest_text(key);encoded=encode(item,purpose='project')
        if len(encoded)<1024 or hashlib.sha256(encoded).hexdigest()!=key:
            raise ContractError('shared audit value digest/size mismatch')
        lengths[key]=len(encoded)
    # Predict exact expanded JSON length before copying/encoding repeated values.
    # Nested user objects named ref/inline remain ordinary literal values.
    base={key:item for key,item in value.items() if key not in extras|{'views'}}
    base['views']={};predicted=len(encode(base,purpose='project'))-2
    used=set();views={};view_sizes=[]
    for ref,fields in value['views'].items():
        if type(fields) is not dict:raise ContractError('invalid shared view fields')
        result={};sizes=[]
        for field,wrapper in fields.items():
            if type(wrapper) is not dict or set(wrapper) not in ({'inline'},{'ref'}):raise ContractError('invalid shared field wrapper')
            if 'ref' in wrapper:
                key=wrapper['ref']
                if type(key) is not str or key not in pool:raise ContractError('missing shared audit value')
                used.add(key);item=pool[key];length=lengths[key]
            else:
                item=wrapper['inline'];length=len(encode(item,purpose='project'))
                if length>=1024:raise ContractError('noncanonical inline shared value')
            result[field]=item;sizes.append(len(encode(field,purpose='project'))+1+length)
        view_sizes.append(len(encode(ref,purpose='project'))+1+2+sum(sizes)+max(0,len(sizes)-1))
        views[ref]=result
    predicted+=2+sum(view_sizes)+max(0,len(view_sizes)-1)
    if predicted>PROJECT_BYTES or predicted!=value['expanded_bytes']:
        raise ContractError('shared audit expanded byte bound/length mismatch')
    if used!=set(pool):raise ContractError('unused shared audit values')
    base['views']=views;expanded=encode(base,purpose='project')
    if len(expanded)!=predicted or hashlib.sha256(expanded).hexdigest()!=value['expanded_sha256']:
        raise ContractError('shared audit expanded digest mismatch')
    if pack_shared_audit(base)!=raw:raise ContractError('noncanonical shared audit encoding')
    return decode(expanded,purpose='project')


def verify_shared_audit(raw):
    """Verify the logical audit against fresh source-checked replay, no authority."""
    value=expand_shared_audit(raw)
    from .research_history import ResearchHistory
    history=ResearchHistory(encode(value['seed'],purpose='history'),
        tuple(encode(c,purpose='history') for c in value['commands']))
    if history.manifest()!=raw:raise ContractError('shared audit differs from source-checked replay')
    return value


def shared_audit_schema():
    """Generated wire shape; runtime additionally verifies references and replay."""
    from .research_schema import HASH
    wrapper={'oneOf':[dict(type='object',properties={'ref':HASH},required=['ref'],additionalProperties=False),
        dict(type='object',properties={'inline':{}},required=['inline'],additionalProperties=False)]}
    properties={key:{} for key in _AUDIT_KEYS}
    properties.update(schema={'const':SHARED_AUDIT},schema_version={'const':14},
        expanded_bytes={'type':'integer','minimum':0,'maximum':PROJECT_BYTES},expanded_sha256=HASH,
        views={'type':'object','maxProperties':2048,'additionalProperties':{'type':'object','maxProperties':2048,'additionalProperties':wrapper}},
        shared_values={'type':'object','maxProperties':2048,'propertyNames':HASH,'additionalProperties':{}})
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',
        '$id':'urn:claimbranch:shared-audit-manifest:v1',
        '$comment':'Generated by scripts/export_research_schema.py. Runtime checks canonical bytes, 8 MiB wire/16 MiB expanded bounds, field/value references and fresh source-checked replay. Private audit, no authority.',
        'type':'object','properties':properties,'required':sorted(properties),'additionalProperties':False}
