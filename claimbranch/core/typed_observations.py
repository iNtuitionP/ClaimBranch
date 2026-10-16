"""Bounded exact measurement tables in the global append-only evidence stream."""
from copy import deepcopy
from .canonical import ContractError
from .paper_capacity import encode
from .research_schema import ID, TEXT, HASH, array, obj, nullable, normalize, ROOT_JSON_POINTER

EXACT = {'type':'string','minLength':1,'maxLength':128}
VALUE = {'oneOf':[
    obj(type={'const':'integer'},value={**EXACT,'pattern':'^-?(0|[1-9][0-9]*)$'}),
    obj(type={'const':'decimal'},value={**EXACT,'pattern':'^-?(0|[1-9][0-9]*)(\\.[0-9]+)?$'}),
    obj(type={'const':'text'},value=TEXT),obj(type={'const':'missing'},reason=TEXT)]}
TAG = obj(key=ID,value=ID)
VOCABULARY = obj(key=ID,values=array(ID,64,1,True),groups=array(obj(id=ID,ascending_values=array(ID,64,1,True)),16),rationale=TEXT)
ARTIFACT = obj(id=ID,path=TEXT,sha256=HASH,json_pointer=ROOT_JSON_POINTER,tool_sha256=nullable(HASH),commit=nullable(TEXT))
TABLE = obj(id=ID,estimand=TEXT,conditions=array(TAG,32,unique=True),
    columns=array(obj(id=ID,name=TEXT,type={'enum':['integer','decimal','text']},raw_unit=TEXT,display_unit=TEXT),32,1),
    rows=array(obj(id=ID,conditions=array(TAG,32,unique=True),cells=array(obj(id=ID,column_id=ID,value=VALUE),32,1)),256,1),
    artifact_refs=array(ARTIFACT,16))
MEASUREMENT = obj(event_id=ID,target_id=ID,run_id=ID,expected_revision=nullable(ID),
    action={'enum':['confirm','transform','correct-cells','transition']},statement=TEXT,rationale=TEXT,source_context=TEXT,
    table=nullable(TABLE),corrections=array(obj(cell_id=ID,value=VALUE),2048))
PAYLOADS = {'declare-condition':VOCABULARY,'record-measurement':MEASUREMENT}
INPUT = {'oneOf':[obj(schema={'const':'claimbranch.measurement-input/v1'},operation_type={'const':kind},payload=payload) for kind,payload in PAYLOADS.items()]}
TABLE_BYTES=262144


def validate_table(table,vocabulary):
    if len(encode(table,purpose='history'))>TABLE_BYTES:raise ContractError(f'capacity measurement-table-bytes: {len(encode(table,purpose="history"))} / {TABLE_BYTES}')
    def tags(values):
        result={v['key']:v['value'] for v in values}
        if len(result)!=len(values):raise ContractError('Duplicate condition key')
        for key,value in result.items():
            if key not in vocabulary or value not in vocabulary[key]['values']:raise ContractError('Unknown declared condition key/value: '+key+'='+value)
        return result
    global_tags=tags(table['conditions']);columns={c['id']:c for c in table['columns']}
    if len(columns)!=len(table['columns']):raise ContractError('Duplicate column identity')
    rows=set();cells=set()
    for row in table['rows']:
        if row['id'] in rows:raise ContractError('Duplicate row identity')
        rows.add(row['id']);local=tags(row['conditions'])
        if any(key in global_tags and global_tags[key]!=value for key,value in local.items()):raise ContractError('Row condition conflicts with table condition')
        if len(row['cells'])!=len(columns) or {c['column_id'] for c in row['cells']}!=set(columns):raise ContractError('Every row needs exactly one cell per column; use explicit missing values')
        for cell in row['cells']:
            if cell['id'] in cells:raise ContractError('Duplicate stable cell identity')
            cells.add(cell['id']);value=cell['value']
            if value['type']!='missing' and value['type']!=columns[cell['column_id']]['type']:raise ContractError('Cell type differs from declared column')
    if len(cells)>2048:raise ContractError(f'capacity measurement-cells: {len(cells)} / 2048')
    refs=table['artifact_refs']
    if len({r['id'] for r in refs})!=len(refs):raise ContractError('Duplicate artifact reference identity')
    for ref in refs:
        pointer=ref['json_pointer']
        if pointer and not pointer.startswith('/'):raise ContractError('Artifact JSON pointer must be empty or start with /')
        import re
        if re.search(r'~(?![01])',pointer):raise ContractError('Invalid artifact JSON pointer escape')


def apply_measurement(state,command):
    from .research_history import _record_ids,_append_evidence,_evidence
    if state['seed']['schema_version'] not in (4, 5, 14, 18) or state['active_episode'] is None:raise ContractError('Measurements require an active personal paper episode')
    payload=command['payload'];vocabulary=state.setdefault('condition_vocabulary',{})
    if command['operation_type']=='declare-condition':
        key=payload['key']
        if key in vocabulary:raise ContractError('Condition declarations are immutable; use a new key for a different meaning')
        if len(vocabulary)>=32:raise ContractError(f'capacity condition-keys: {len(vocabulary)+1} / 32')
        groups=payload['groups']
        if len({g['id'] for g in groups})!=len(groups) or any(not set(g['ascending_values'])<=set(payload['values']) for g in groups):raise ContractError('Unique groups must use declared values in explicit ascending order')
        vocabulary[key]=deepcopy(payload);return
    before=next((o for o in _evidence(state['events']) if o['id']==payload['target_id']),None)
    action=payload['action'];table=payload['table'];corrections=payload['corrections']
    if action=='confirm':
        if before or payload['expected_revision'] is not None or table is None or corrections:raise ContractError('Confirmation introduces a new table observation')
    else:
        if before is None or before['history'][-1]['event_id']!=payload['expected_revision']:raise ContractError('Stale measurement revision; name the latest evidence event')
        if before['status'] not in ('confirmed','corrected'):raise ContractError('Inactive evidence cannot be reactivated by measurement edits')
        if payload['run_id']!=before['run_id']:raise ContractError('Measurement cannot move to another experiment')
        old=before.get('measurement')
        if action=='transform':
            if old is not None or table is None or corrections:raise ContractError('Transform attaches a source-reviewed table to an existing text observation')
        elif action=='transition':
            if old is None or table is None or corrections or table['id']==old['id']:raise ContractError('A new declared measurement transition requires a new table identity')
        else:
            if old is None or table is not None or not corrections:raise ContractError('Cell correction requires an existing table and explicit cells only')
            if payload['statement']!=before['statement']:raise ContractError('Cell correction cannot rewrite the observation statement; use a declared transition')
            table=deepcopy(old);cells={c['id']:c for row in table['rows'] for c in row['cells']}
            if len({c['cell_id'] for c in corrections})!=len(corrections):raise ContractError('Duplicate correction cell')
            for correction in corrections:
                if correction['cell_id'] not in cells:raise ContractError('Unknown correction cell')
                if cells[correction['cell_id']]['value']==correction['value']:raise ContractError('Correction must change the cell')
                cells[correction['cell_id']]['value']=deepcopy(correction['value'])
    validate_table(table,vocabulary)
    if action in ('confirm','transform','transition'):
        prior_tables={e['measurement']['id'] for e in state['events'] if 'measurement' in e}
        if table['id'] in _record_ids(state) or table['id'] in prior_tables or table['id'] in (payload['event_id'],payload['target_id']):raise ContractError('Measurement identity reused or aliases a record')
        # Stable cell IDs span this observation's retained history, including retired tables.
        if before:
            previous={}
            def meanings(measurement):
                columns={c['id']:c for c in measurement['columns']}
                defaults={c['key']:c['value'] for c in measurement['conditions']}
                for row in measurement['rows']:
                    conditions={**defaults,**{c['key']:c['value'] for c in row['conditions']}}
                    for cell in row['cells']:
                        yield cell['id'],(measurement['estimand'],row['id'],columns[cell['column_id']],conditions)
            for old_event in before['history']:
                if 'measurement' in old_event:previous.update(meanings(old_event['measurement']))
            for cell_id,meaning in meanings(table):
                if cell_id in previous and previous[cell_id]!=meaning:raise ContractError('Stable cell identity changed its measurement meaning; use a new cell identity')
    event=dict(event_id=payload['event_id'],target_id=payload['target_id'],run_id=payload['run_id'],action='confirm' if action=='confirm' else 'correct',
        statement=payload['statement'],value=f"Structured measurement {table['id']}: {len(table['rows'])} rows × {len(table['columns'])} columns (inspect cells).",
        rationale=payload['rationale'],supersedes_id=payload['expected_revision'],measurement=deepcopy(table),measurement_action=action,source_context=payload['source_context'],
        recorded_at=command['created_at'],operation_id=command['id'],artifact_fidelity_verified=False)
    _append_evidence(state,event)
