"""Versioned prior-record absence, identity and declaration rules. No I/O/authority."""
from copy import deepcopy
from datetime import date
import hashlib
import re
from .canonical import ContractError
from .research_schema import ID,TEXT,METRIC,obj,array,nullable,_check

TOKEN={**TEXT,'pattern':r'^[^\r\n]+$'}
DAY={'type':'string','pattern':r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$','minLength':10,'maxLength':10}
EXPERIMENT_FIELDS=('question','method','conditions','metric','source_ref')


def extend_schema(result):
    """Only called for import-v4. Earlier closed schema objects are untouched."""
    from .argument_import import DATE,ORIGIN
    from .argument_import_v2 import optional
    result=deepcopy(result)
    result['properties']['structural_defaults']=array({'enum':['thesis','claim','experiment','observation','scientific-edge','experiment-plan','historical-decision']},7,unique=True)
    variants=result['properties']['records']['items']['oneOf']
    for variant in variants:
        fields=variant['properties'];kind=fields['kind']['const'];body=fields['body']
        fields['id']=TOKEN;fields['display_label']=TOKEN
        fields['recorded_at']=nullable({'oneOf':[DATE,DAY]})
        fields['mappings']['minItems']=0
        item=fields['mappings']['items']['items']
        item['oneOf'].append(optional(obj(target=item['oneOf'][0]['properties']['target'],source_silent={'const':True},origin=ORIGIN,transformation=TEXT),'origin'))
        if kind=='experiment':
            metric=obj(**{key:nullable(value) for key,value in METRIC['properties'].items()});metric['required']=[]
            fields['body']=obj(**{key:nullable(metric if key=='metric' else TEXT) for key in EXPERIMENT_FIELDS})
            fields['body']['required']=[]
        elif kind=='historical-decision':
            body['properties']['title']=nullable(TEXT)
        # Original record tokens and scientific references may contain spaces/slashes.
        bodies=body.get('oneOf',[body]) if kind!='experiment' else []
        for b in bodies:
            for key,field in b['properties'].items():
                if key in ('parent_ids','basis_ids','record_ids'):field['items']=TOKEN
                elif key in ('experiment_id','claim_id','source_id','target_id'):b['properties'][key]=TOKEN
    result['properties']['selected_ids']['items']=TOKEN
    return result


def identities(records):
    aliases={};labels=set();used=set();namespace={}
    for record in records:
        token=record['id'];label=record.get('display_label',token)
        if token in aliases or label in labels:raise ContractError('Duplicate original record identity/display label')
        try:_check(token,ID);key=token
        except ContractError:key='import-'+hashlib.sha256(token.encode()).hexdigest()[:32]
        if key in used:raise ContractError('Original-to-internal identity collision; choose distinct explicit ids')
        for spelling in (token,label,key):
            if spelling in namespace and namespace[spelling]!=token:
                raise ContractError('Display label/original/internal identity collision')
            namespace[spelling]=token
        aliases[token]=key;labels.add(label);used.add(key)
        when=record['recorded_at']
        if when is not None and len(when)==10:
            try:date.fromisoformat(when)
            except ValueError as error:raise ContractError('recorded_at must be a real calendar date') from error
    return aliases


def translated_body(record,aliases):
    body=deepcopy(record['body']);kind=record['kind']
    if kind=='experiment':
        for field in EXPERIMENT_FIELDS:body.setdefault(field,None)
        if body['metric'] is not None:
            for field in METRIC['properties']:body['metric'].setdefault(field,None)
    if kind=='historical-decision':body.setdefault('title',None)
    for field in ('parent_ids','basis_ids','record_ids'):
        if field in body:body[field]=[aliases.get(key,key) for key in body[field]]
    for field in ('experiment_id','claim_id','source_id','target_id'):
        if field in body:body[field]=aliases.get(body[field],body[field])
    return body


def absent_fields(record):
    if record['kind']!='experiment':return []
    body=record['body'];result=[]
    for key in EXPERIMENT_FIELDS:
        if body.get(key) is None:result.append('/'+key)
        elif key=='metric':result.extend('/metric/'+field for field in METRIC['properties'] if body[key].get(field) is None)
    return result


def bookkeeping(record,target,value):
    from .argument_import_v2 import _structural
    if _structural(target):
        binding=re.fullmatch(r'/measurement/rows/[0-9]+/cells/([0-9]+)/column_id',target)
        if binding:
            columns=record['body']['measurement']['columns'];index=int(binding[1])
            return index<len(columns) and value==columns[index]['id']
        return True
    if target=='/basis_ids' and value==[] and record['kind']=='claim' and record['body']['status']=='proposed':return True
    if target=='/group_id' and value is None and record['kind']=='historical-decision':return True
    if target=='/measurement/artifact_refs' and value==[]:return True
    return value is None and bool(re.fullmatch(r'/measurement/artifact_refs/[0-9]+/(tool_sha256|commit)',target))


def augmented_origin(origin, declarations):
    flags={key:origin[key] for key in ('human','ai','unknown')}
    labels={'human':('human',),'ai':('ai',),'mixed':('human','ai'),'unknown':('unknown',)}
    for declaration in declarations:
        for flag in labels[declaration['contributor']]:flags[flag]=True
    label='mixed' if flags['human'] and flags['ai'] else 'ai' if flags['ai'] else 'unknown' if flags['unknown'] else 'human'
    return {**origin,**flags,'contributor':label,'independent_declarations':declarations}


def seed_schema():
    from .argument_import_v2 import seed_schema as old_schema,import_schema
    from .argument_import import POINTER,ORIGIN,DATE
    result=old_schema();result['properties']['schema_version']={'const':18}
    variants=deepcopy(import_schema(4)['properties']['records']['items']['oneOf'])
    for variant in variants:
        fields=variant['properties']
        for key in ('mappings','joint_origin','source_origins'):fields.pop(key)
        fields.update(id=ID,origin=ORIGIN,source_pointer=POINTER,external_id=TEXT,
            not_recorded=array(POINTER,16),origin_flags=obj(human={'enum':[False,True]},ai={'enum':[False,True]},unknown={'enum':[False,True]}))
        variant['required']=list(fields)
    result['properties']['initial_argument']['properties']['records']=array({'oneOf':variants},2048,1)
    return result


def validate_source_free(record,target,origin,value):
    """New writing cannot masquerade as a prior empirical observation."""
    if record['kind']=='observation' and not bookkeeping(record,target,value):
        raise ContractError('Source-free observation science cannot supply a historical result; map the retained result or leave it unregistered')
    if record['kind']=='claim' and record['body']['status']!='proposed' and target in ('/statement','/scope'):
        raise ContractError('A changed unsupported statement/scope cannot inherit a historical supported or contested status; retain a proposed claim instead')
    nonhuman=origin['contributor']!='human'
    if nonhuman and (record['kind']=='experiment' or record['kind']=='claim' and record['body']['status']!='proposed' or record['kind']=='historical-decision' and target!='/title'):
        raise ContractError('Source-free AI/mixed/unknown writing is a proposal, not a historical experiment, supported claim or past decision reason')
