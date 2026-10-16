"""Original-ledger preview v2. Kept separate from legacy import/seed authority."""
from copy import deepcopy
import hashlib
import re

from .canonical import ContractError
from .paper_capacity import encode, decode, source_bytes, source_record, HISTORY_BYTES
from .research_schema import ID, TEXT, obj, array, nullable, _check
from .argument_sources import LOCATOR, NORMALIZATIONS, LOCATOR_V2, NORMALIZATIONS_V2, SourceResolver, normalized, text

MAX_FILES = 32
MAX_EXPANDED_MAPPINGS = 65536
MAX_RECORD_MAPPINGS = 32768
# Derived references identify app structure, never scientific status or quantities.
DERIVED = {'/measurement/id'}


def optional(schema, *names):
    result=deepcopy(schema)
    result['required']=[name for name in result['required'] if name not in names]
    return result


def import_schema(version=2):
    if version not in (2,3,4,5):raise ContractError("Unknown original-ledger import version")
    from .argument_import import ORIGIN, SOURCE, POINTER, DATE, BODIES
    from .typed_observations import TABLE, VOCABULARY
    mapping={'oneOf':[
        obj(target=POINTER,derived={'const':'structure-v1'}),
        optional(obj(target=POINTER,file_id=ID,locator=LOCATOR if version==2 else LOCATOR_V2,normalization={'enum':NORMALIZATIONS if version==2 else NORMALIZATIONS_V2},transformation=nullable(TEXT),source_silent={'const':True}),'source_silent')]}
    bodies=deepcopy(BODIES)
    bodies['observation']={'oneOf':[bodies['observation'],obj(experiment_id=ID,statement=TEXT,
        measurement=TABLE,status={'enum':['confirmed','corrected','invalidated','retracted']})]}
    records={'oneOf':[optional(obj(id=ID,kind={'const':kind},body=body,recorded_at=nullable(DATE),
        mappings=array(array(mapping,1024,1),32,1),origin=ORIGIN,joint_origin=ORIGIN,
        source_origins=array(obj(file_id=ID,origin=ORIGIN),MAX_FILES)),
        'origin','joint_origin','source_origins') for kind,body in bodies.items()]}
    file=optional(obj(id=ID,name=TEXT,media={'enum':['markdown','text','latex','json']},source=SOURCE,origin_default=ORIGIN),'origin_default')
    result={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':f'urn:claimbranch:argument-import:v{version}',
        **optional(obj(schema={'const':f'claimbranch.argument-import/v{version}'},profile={'const':'paper'},project_id=ID,
            title=TEXT,files=array(file,MAX_FILES,1),origin_default=ORIGIN,
            condition_vocabulary=array(VOCABULARY,32),records=array(records,2048,1),selected_ids=array(ID,2048,1,True)), 'origin_default')}
    if version>=4:
        from .historical_argument import extend_schema
        result=extend_schema(result)
    if version==5:
        from .historical_argument import TOKEN
        for variant in result['properties']['records']['items']['oneOf']:
            if variant['properties']['kind']['const']=='observation':
                variant['properties']['replacement']=obj(previous_id=TOKEN,origin={'enum':['human','ai','mixed','unknown']},source_context=TEXT,rationale=TEXT)
    return result


def manifest_schema(version=1):
    if version not in (1,2,3,4):raise ContractError("Unknown source manifest version")
    result=import_schema(version+1)
    result['$id']=f'urn:claimbranch:argument-source-manifest:v{version}'
    result['properties']['schema']={'const':f'claimbranch.argument-source-manifest/v{version}'}
    file=result['properties']['files']['items']
    del file['properties']['source'];file['required'].remove('source')
    file['properties']['path']=TEXT;file['required'].append('path')
    return result


def _structural(target):
    if target in DERIVED: return True
    import re
    return bool(re.fullmatch(r'/measurement/(columns/[0-9]+/id|rows/[0-9]+/(id|cells/[0-9]+/(id|column_id)))',target))


def effective_origin(record, files, bundle, used):
    """Fallback labels are replaceable; explicit contributing assertions are not."""
    unknown=dict(contributor='unknown',detail=None)
    overrides={entry['file_id']:entry['origin'] for entry in record.get('source_origins',[])}
    if len(overrides)!=len(record.get('source_origins',[])) or not set(overrides)<=set(used):
        raise ContractError('Source-origin assertions must name unique contributing files')
    entries=[]; labels=set(); flags=set()
    def add(label):
        flags.update({'human':{'human'},'ai':{'ai'},'mixed':{'human','ai'},'unknown':{'unknown'}}[label])
    for key in sorted(used):
        file=files[key]
        fallback=file.get('origin_default',bundle or unknown)
        if key in overrides: origin,declaration=overrides[key],'source-record'
        elif 'origin' in record: origin,declaration=record['origin'],'record'
        else: origin,declaration=fallback,('file' if 'origin_default' in file else 'bundle' if bundle else 'absent')
        labels.add(origin['contributor']);add(origin['contributor'])
        entries.append(dict(file_id=key,sha256=file['source']['sha256'],origin=origin,declaration=declaration,fallback=fallback))
    if 'origin' in record: add(record['origin']['contributor'])
    joint=record.get('joint_origin')
    if len(labels)>1 and joint is None:
        raise ContractError('Conflicting source origins require an explicit joint_origin declaration')
    if joint:
        joint_flags={'human':{'human'},'ai':{'ai'},'mixed':{'human','ai'},'unknown':{'unknown'}}[joint['contributor']]
        # A joint label cannot declare AI-free when any contributing effective source is AI.
        if 'ai' in flags and 'ai' not in joint_flags:
            raise ContractError('Joint origin cannot clear retained AI influence')
        # Unknown stays a separate flag even when joint authorship is mixed/AI.
        add(joint['contributor'])
    if not used: raise ContractError('Each imported record needs at least one retained scientific source')
    label='mixed' if {'human','ai'}<=flags else 'ai' if 'ai' in flags else 'unknown' if 'unknown' in flags else 'human'
    return dict(contributor=label,human='human' in flags,ai='ai' in flags,unknown='unknown' in flags,
        declaration='joint' if joint else (entries[0]['declaration'] if len({entry['declaration'] for entry in entries})==1 else 'mixed-declarations'),
        declared=joint or record.get('origin'),sources=entries)


def _display(value):
    from decimal import Decimal
    if isinstance(value,Decimal):return {'source_decimal':str(value)}
    if isinstance(value,str) and len(value.encode('utf-8'))>1024:
        raw=value.encode('utf-8')
        return {'excerpt':raw[:1024].decode('utf-8',errors='ignore'),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'truncated':True}
    if isinstance(value,list):return [_display(item) for item in value]
    if isinstance(value,dict):return {key:_display(item) for key,item in value.items()}
    return value


def preview_import(raw):
    from .argument_import import _Diagnostics,_errors,_leaves,graph_consistency
    from .typed_observations import validate_table
    value=decode(raw,purpose='project');errors=_Diagnostics()
    version={'claimbranch.argument-import/v3':3,'claimbranch.argument-import/v4':4,'claimbranch.argument-import/v5':5}.get(value.get('schema'),2) if type(value) is dict else 2
    schema=import_schema(version)
    skeleton=deepcopy(schema);skeleton['properties']['records']['items']={}
    _errors(value,skeleton,'',errors)
    result=dict(schema=f'claimbranch.argument-import-preview/v{version}',valid=False,writes=False,
        registration_available=False,source_fidelity_verified=False)
    if errors:return {**result,**errors.fields()}
    file_map={};total=0;originals={};resolvers={};reports=[];projected=[];expanded=0;vocabulary={};index_budget={}
    for index,file in enumerate(value['files']):
        try:
            if file['id'] in file_map:raise ContractError('Duplicate source file identity')
            raw_source=source_bytes(file['source']);text(raw_source);total+=len(raw_source)
            if total>HISTORY_BYTES:raise ContractError(f'capacity original-source-bytes: {total} / {HISTORY_BYTES}')
            file_map[file['id']]=file;originals[file['id']]=raw_source
            resolvers[file['id']]=SourceResolver(raw_source,file['media'],index_budget,version=min(version-1,2))
        except ContractError as error:errors.append(dict(pointer=f'/files/{index}',error=str(error)))
    for item in value['condition_vocabulary']:
        if item['key'] in vocabulary: errors.append(dict(pointer='/condition_vocabulary',error='Duplicate condition key'))
        vocabulary[item['key']]=item
        if len(set(item['values']))!=len(item['values']):errors.append(dict(pointer='/condition_vocabulary',error='Duplicate condition value'))
        groups=item['groups']
        if len({group['id'] for group in groups})!=len(groups) or any(not set(group['ascending_values'])<=set(item['values']) for group in groups):
            errors.append(dict(pointer='/condition_vocabulary',error='Invalid declared condition groups'))
    for index,record in enumerate(value['records']):
        path=f'/records/{index}';before=len(errors)
        variant=next((variant for variant in schema['properties']['records']['items']['oneOf']
            if type(record) is dict and variant['properties']['kind']['const']==record.get('kind')),None)
        if variant is None:errors.append(dict(pointer=path,error='Unknown record kind'));continue
        _errors(record,variant,path,errors)
        if len(errors)!=before:continue
        if version>=4 and record['recorded_at'] is not None and len(record['recorded_at'])==10:
            from datetime import date
            try:date.fromisoformat(record['recorded_at'])
            except ValueError:
                errors.append(dict(pointer=path+'/recorded_at',error='recorded_at must be a real calendar date'));continue
        try:expected=dict(_leaves(record['body']))
        except ContractError as error:
            errors.append(dict(pointer=path+'/body',error=str(error)));continue
        seen=set();coverage=[];used=set();independent=[]
        count=sum(map(len,record['mappings']));expanded+=count
        if count>MAX_RECORD_MAPPINGS or expanded>MAX_EXPANDED_MAPPINGS:
            errors.append(dict(pointer=path+'/mappings',error=f'capacity expanded-mappings: {expanded} / {MAX_EXPANDED_MAPPINGS}'));break
        for page_number,page in enumerate(record['mappings']):
            for number,mapping in enumerate(page):
                target=mapping['target'];where=f'{path}/mappings/{page_number}/{number}'
                try:
                    if target not in expected or target in seen:raise ContractError('Mapping must name each body leaf exactly once')
                    seen.add(target)
                    if 'derived' in mapping:
                        if not _structural(target):raise ContractError('Scientific content cannot be application-derived structure')
                        binding=re.fullmatch(r'/measurement/rows/[0-9]+/cells/([0-9]+)/column_id',target)
                        if binding and int(binding[1]) >= len(record['body']['measurement']['columns']):
                            raise ContractError('Derived cell-column binding has no declared column at this position')
                        if binding and expected[target] != record['body']['measurement']['columns'][int(binding[1])]['id']:
                            raise ContractError('Derived cell-column binding must preserve declared column order; otherwise map the binding to source')
                        coverage.append(dict(target=target,state='derived-structure'));continue
                    if version>=4 and mapping.get('source_silent') and 'file_id' not in mapping:
                        if target=='/status' and expected[target] not in ('proposed','planned'):
                            raise ContractError('A source-silent assertion cannot manufacture historical evidence/claim status')
                        declaration=mapping.get('origin',dict(contributor='unknown',detail=None))
                        from .historical_argument import validate_source_free
                        validate_source_free(record,target,declaration,expected[target]);independent.append(declaration)
                        coverage.append(dict(target=target,state='declared-without-source',origin=declaration,
                            transformation=mapping['transformation'],original=None,normalized=_display(expected[target])))
                        continue
                    key=mapping['file_id'];used.add(key)
                    if key not in originals:raise ContractError('Missing or invalid retained source file')
                    original,span=resolvers[key].resolve(mapping['locator'])
                    normal=normalized(original,mapping['normalization'],mapping['locator'],version=min(version-1,2))
                    if mapping.get('source_silent'):
                        if version>=4:
                            from .historical_argument import validate_source_free
                            overrides={entry['file_id']:entry['origin'] for entry in record.get('source_origins',[])}
                            label=overrides.get(key,record.get('origin',file_map[key].get('origin_default',value.get('origin_default',dict(contributor='unknown',detail=None)))))
                            validate_source_free(record,target,label,expected[target])
                        if mapping['transformation'] is None:raise ContractError('Source-silent assertions need an explicit rationale')
                        if target=='/status' and expected[target] not in ('proposed','planned'):
                            raise ContractError('A source-silent assertion cannot manufacture historical evidence/claim status')
                        state='declared-without-source'
                    elif mapping['transformation'] is not None:state='transformed'
                    elif type(normal)!=type(expected[target]) or normal!=expected[target]:
                        raise ContractError('Changed value requires a declared transformation')
                    else:state='exact' if type(original)==type(normal) and original==normal else 'normalized-exact'
                    coverage.append(dict(target=target,state=state,file_id=key,source_sha256=file_map[key]['source']['sha256'],
                        locator=mapping['locator'],resolved=span,normalization=mapping['normalization'],
                        transformation=mapping['transformation'],original=_display(original),normalized=_display(normal)))
                except ContractError as error:errors.append(dict(pointer=where,target=target,file_id=mapping.get('file_id'),locator=mapping.get('locator'),error=str(error)))
        if version>=4:
            from .historical_argument import bookkeeping,absent_fields
            for target in absent_fields(record):
                if target in seen:
                    errors.append(dict(pointer=path+'/body'+target,error='Not-recorded fields cannot claim a source mapping'));continue
                coverage.append(dict(target=target,state='not-recorded'));seen.add(target)
            if record['kind'] in value.get('structural_defaults',[]):
                for target in sorted(set(expected)-seen):
                    if bookkeeping(record,target,expected[target]):
                        coverage.append(dict(target=target,state='structural-default'));seen.add(target)
        missing=set(expected)-seen
        for target in sorted(missing):errors.append(dict(pointer=path+'/body'+target,error='Unmapped scientific or structural leaf'))
        try:
            if version>=4 and not used and independent:
                if record.get('source_origins'):raise ContractError('Source-origin assertions must name contributing files; source-free records have none')
                origin=dict(contributor='unknown',human=False,ai=False,unknown=False,declaration='joint' if record.get('joint_origin') else 'independent',declared=record.get('joint_origin',record.get('origin')),sources=[])
            else:origin=effective_origin(record,file_map,value.get('origin_default'),used)
            if version>=4:
                from .historical_argument import augmented_origin
                origin=augmented_origin(origin,independent+([record['origin']] if not used and 'origin' in record else [])+([record['joint_origin']] if not used and 'joint_origin' in record else []))
                if origin['ai'] and record.get('joint_origin',{}).get('contributor') in ('human','unknown'):
                    raise ContractError('Joint origin cannot clear retained AI influence')
        except (ContractError,KeyError) as error:
            errors.append(dict(pointer=path+'/origin',error=str(error)));origin=None
        body=record['body']
        if record['kind']=='observation' and 'measurement' in body:
            try:validate_table(body['measurement'],vocabulary)
            except ContractError as error:errors.append(dict(pointer=path+'/body/measurement',error=str(error)))
        projected.append(dict(id=record['id'],kind=record['kind'],body=body))
        reports.append({**record,'coverage':coverage,'effective_origin':origin})
    if errors:return {**result,**errors.fields(),'files':value['files'],'records':reports}
    by_id={};indexes={}
    for index,record in enumerate(projected):
        if record['id'] in by_id:errors.append(dict(pointer=f'/records/{index}/id',error='Duplicate record identity'))
        by_id[record['id']]=record;indexes[record['id']]=f'/records/{index}'
    if version>=4:
        from .historical_argument import identities,translated_body
        try:aliases=identities(value['records'])
        except ContractError as error:
            errors.append(dict(pointer='/records',error=str(error)));return {**result,**errors.fields()}
        by_id={aliases[r['id']]:dict(id=aliases[r['id']],kind=r['kind'],body=translated_body(r,aliases)) for r in projected}
        indexes={aliases[key]:pointer for key,pointer in indexes.items()}
        requested=[aliases.get(key,key) for key in value['selected_ids']]
    else:aliases={key:key for key in by_id};requested=value['selected_ids']
    selected,closure,included,counts,limits=graph_consistency(requested,by_id,indexes,errors)
    if version==5 and not errors:
        from .observation_lineage import imported_links
        try:
            links=imported_links(value,aliases)
            while True:
                needed={r['previous_id'] for r in links.values() if r['replacement_id'] in closure}-closure
                if not needed:break
                _,closure,included,counts,limits=graph_consistency(sorted(closure|needed),by_id,indexes,errors)
                if errors:break
        except ContractError as error:errors.append(dict(pointer='/records',error=str(error)))
    if errors:return {**result,**errors.fields(),'files':value['files'],'records':reports}
    reports=[({**record,'internal_id':aliases[record['id']]} if version>=4 else record) for record in reports if aliases[record['id']] in closure]
    states={name:sum(item['state']==name for record in reports for item in record['coverage'])
        for name in (('exact','normalized-exact','transformed','declared-without-source','derived-structure','structural-default','not-recorded') if version>=4 else ('exact','normalized-exact','transformed','declared-without-source','derived-structure'))}
    # No percent of source meaning: unchanged matched spans cannot certify omitted text.
    commitment=dict(schema=result['schema'],resolver=f'original-source/v{min(version-1,2)}',envelope_schema=value['schema'],envelope_sha256=hashlib.sha256(raw).hexdigest(),selected=sorted(selected),required=sorted(closure-selected))
    answer = dict(**{**result,'valid':True,**errors.fields()},project_id=value['project_id'],title=value['title'],
        files=value['files'],records=reports,condition_vocabulary=value['condition_vocabulary'],
        origin_default=value.get('origin_default'),selected=sorted(selected),required=sorted(closure-selected),omitted=sorted(set(by_id)-closure),
        counts={key:dict(used=count,limit=limits[key]) for key,count in counts.items()},coverage=states,source_bytes=total,
        budgets=dict(original_source_bytes=dict(used=total,limit=HISTORY_BYTES),expanded_mappings=dict(used=expanded,limit=MAX_EXPANDED_MAPPINGS),
            envelope_bytes=dict(used=len(raw),limit=16777216)),
        envelope_sha256=commitment['envelope_sha256'],preview_digest=hashlib.sha256(encode(commitment,purpose='project')).hexdigest(),
        boundary='Private original-ledger preview; mapped history is source-claimed, never historical app approval. Extraction equality does not establish scientific validity.')
    if version==5:answer['replacement_links']=[link for link in links.values() if link['replacement_id'] in closure]
    try:
        candidate = _seed_value(raw, _compact_result(answer,value), 'a'*128, '2000-01-01T00:00:00Z')
        seed_bytes = len(encode(candidate,purpose='history'))
        answer['budgets']['seed_bytes_upper_bound'] = dict(used=seed_bytes,limit=HISTORY_BYTES,remaining=HISTORY_BYTES-seed_bytes)
        answer['registration_available'] = True
        answer['registration_preflight'] = 'Seed fits; complete project/graph/archive and current source/destination are checked before confirmation.'
        answer['budgets']['compressed_snapshot_bytes'] = dict(used=candidate['initial_argument']['snapshot']['compressed']['bytes'],limit=HISTORY_BYTES)
    except ContractError as error:
        answer['registration_available'] = False
        answer['registration_failure'] = str(error)
    return answer


# Private lossless retention is purpose-bound. It does not widen legacy sources.
def snapshot_schema():
    from .argument_import import SOURCE
    from .research_schema import HASH
    return obj(encoding={'const':'zlib-argument/v1'},sha256=HASH,
        bytes={'type':'integer','minimum':0,'maximum':16777216},compressed=SOURCE)


def pack_snapshot(raw):
    import zlib
    if type(raw) is not bytes or len(raw)>16777216:raise ContractError('capacity import-input-bytes: maximum 16777216')
    packed=zlib.compress(raw,9)
    if len(packed)>HISTORY_BYTES:raise ContractError(f'capacity compressed-import-bytes: {len(packed)} / {HISTORY_BYTES}')
    return dict(encoding='zlib-argument/v1',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),compressed=source_record(packed))


def unpack_snapshot(value):
    import zlib
    _check(value,snapshot_schema());packed=source_bytes(value['compressed'])
    try:
        stream=zlib.decompressobj();raw=stream.decompress(packed,value['bytes']+1)
        if len(raw)!=value['bytes'] or not stream.eof or stream.unused_data or stream.unconsumed_tail:
            raise ContractError('Invalid bounded argument snapshot length or stream boundary')
    except zlib.error as error:raise ContractError('Invalid argument snapshot compression') from error
    if hashlib.sha256(raw).hexdigest()!=value['sha256']:raise ContractError('Argument snapshot digest mismatch')
    return raw


def seed_schema():
    from .argument_import import DATE,ORIGIN,POINTER
    from .research_schema import HASH,LIFECYCLE_SEED
    bodies=deepcopy(import_schema()['properties']['records']['items']['oneOf'])
    flags=obj(human={'enum':[False,True]},ai={'enum':[False,True]},unknown={'enum':[False,True]})
    for variant in bodies:
        fields=variant['properties']
        for key in ('mappings','joint_origin','source_origins'):fields.pop(key)
        fields.update(origin=ORIGIN,source_pointer=POINTER,origin_flags=flags)
        variant['required']=list(fields)
    result=deepcopy(LIFECYCLE_SEED);result['properties']['schema_version']={'const':14}
    result['properties']['initial_argument']=obj(source_sha256=HASH,envelope_sha256=HASH,preview_digest=HASH,
        registered_at=nullable(DATE),records=array({'oneOf':bodies},2048,1),
        unresolved_source_pointers=array(array(POINTER,128),512),snapshot=snapshot_schema())
    result['required'].append('initial_argument');return result


from functools import lru_cache


@lru_cache(maxsize=2)
def selected_state(raw):
    """Derived only from the exact retained input; cached callers must not mutate."""
    result=preview_import(raw)
    if not result['valid']:raise ContractError('Invalid selected original argument; no registration')
    return _compact_result(result,decode(raw,purpose='project'))


def _compact_result(result,value):
    positions={record['id']:i for i,record in enumerate(value['records'])}
    v4=value['schema'] in ('claimbranch.argument-import/v4','claimbranch.argument-import/v5')
    if v4:
        from .historical_argument import identities,translated_body,absent_fields
        aliases=identities(value['records'])
    records=[];unresolved=[]
    for record in result['records']:
        pointer='/records/'+str(positions[record['id']]);effective=deepcopy(record['effective_origin'])
        declaration=record.get('replacement')
        if declaration is not None:unresolved.append(pointer+'/replacement')
        records.append(dict(id=aliases[record['id']] if v4 else record['id'],kind=record['kind'],body=translated_body(record,aliases) if v4 else record['body'],recorded_at=record['recorded_at'],
            **(dict(display_label=record.get('display_label',record['id']),external_id=record['id'],not_recorded=absent_fields(record)) if v4 else {}),
            origin=dict(contributor=effective['contributor'],detail=None),source_pointer=pointer,
            origin_flags={key:effective[key] for key in ('human','ai','unknown')}))
        unresolved.extend(pointer+'/body'+item['target'] for item in record['coverage'] if item['state'] in ('transformed','declared-without-source','not-recorded'))
    return dict(records=records,unresolved_source_pointers=[unresolved[i:i+128] for i in range(0,len(unresolved),128)],
        condition_vocabulary=deepcopy(value['condition_vocabulary']),preview_digest=result['preview_digest'],
        project_id=result['project_id'],title=result['title'])


def _seed_value(raw,state,anchor_id,registered_at):
    thesis=next((record for record in state['records'] if record['kind']=='thesis'),None)
    if thesis is None:raise ContractError('Selected argument must retain its thesis')
    digest=hashlib.sha256(raw).hexdigest()
    initial=dict(source_sha256=digest,envelope_sha256=digest,preview_digest=state['preview_digest'],registered_at=registered_at,
        records=state['records'],unresolved_source_pointers=state['unresolved_source_pointers'],snapshot=pack_snapshot(raw))
    seed=dict(schema_version=18 if decode(raw,purpose='project')['schema'] in ('claimbranch.argument-import/v4','claimbranch.argument-import/v5') else 14,profile='paper',project_id=state['project_id'],paper_title=state['title'],
        claim_id=thesis['id'],claim_statement=thesis['body']['statement'],anchor_id=anchor_id,initial_argument=initial)
    return seed


def make_history(raw,anchor_id,registered_at):
    from .research_history import ResearchHistory
    return ResearchHistory(encode(_seed_value(raw,selected_state(raw),anchor_id,registered_at),purpose='history'))


def validate_initial(seed):
    initial=seed['initial_argument'];raw=unpack_snapshot(initial['snapshot']);state=selected_state(raw)
    digest=hashlib.sha256(raw).hexdigest()
    if initial['source_sha256']!=digest or initial['envelope_sha256']!=digest or initial['preview_digest']!=state['preview_digest'] or initial['records']!=state['records'] or initial['unresolved_source_pointers']!=state['unresolved_source_pointers']:
        raise ContractError('Imported science/origin differs from the retained exact snapshot')
    if seed['project_id']!=state['project_id'] or seed['paper_title']!=state['title']:
        raise ContractError('Imported project differs from retained source')
    return deepcopy(state['condition_vocabulary'])


def needs_v3_work_frame(history):
    """Nested source semantics are selected by the exact retained envelope."""
    if history.schema_version!=14:return False
    return _source_version(history.seed)==3


@lru_cache(maxsize=2)
def _source_version(seed_raw):
    seed=decode(seed_raw,purpose='history')
    raw=unpack_snapshot(seed['initial_argument']['snapshot'])
    return {'claimbranch.argument-import/v2':2,'claimbranch.argument-import/v3':3,'claimbranch.argument-import/v4':4,'claimbranch.argument-import/v5':5}[decode(raw,purpose='project')['schema']]


def needs_history_work_frame(history):
    return any(decode(c,purpose='history')['schema_version']==19 for c in history.commands) or (history.schema_version==18 and _source_version(history.seed)==5)


def needs_iteration_work_frame(history):
    return any(decode(c,purpose='history')['schema_version']==20 for c in history.commands)
