"""Explicit extended-record import; detached candidates publish in one saved write."""
import hashlib
import json
import sys
from copy import deepcopy
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode,encode,source_record
from claimbranch.core.research_schema import obj,array,ID,normalize,TEXT

ORIGIN={'enum':['human','ai','mixed','unknown']}


def origin_command(command, origin=None):
    return {**command,'schema_version':command['schema_version'] if command.get('schema_version') in (15,17,19,20) else 12,'contribution_origin':origin or 'unknown'}


def batch_schema(version=1):
    if version not in (1,2,3,4):raise ContractError('Unknown metadata batch version')
    from .co_report import INPUT as CO
    from claimbranch.core.typed_observations import INPUT as ME
    from claimbranch.core.protocols import INPUT as PR
    from claimbranch.core.critiques import INPUT as CR
    from claimbranch.core.research_schema import REVISION_PAYLOADS
    anchor=obj(manuscript=TEXT,anchor_id=ID,kind={'enum':['text','figure','table','caption']},
        expresses=array(ID,64,unique=True),plots=array(ID,256,unique=True),parents=array(ID,64,unique=True),rationale=TEXT)
    if version >= 2:
        from claimbranch.core.marked_text import selector_schema
        labeled=[]
        for v in (1,2):
            alternative=deepcopy(anchor);alternative['properties']['selector']=selector_schema(v);alternative['required'].append('selector');labeled.append(alternative)
        anchor={'oneOf':[anchor,*labeled]}
    if version>=3:
        from claimbranch.core.protocols import input_schema
        PR=input_schema(2)
    requests={'anchor':anchor,'measurement':ME,'protocol':PR,'co-report':CO,'critique':CR}
    if version==4:
        from claimbranch.core.critiques import LINK
        reference=deepcopy(LINK);del reference['properties']['critique_id'];reference['required'].remove('critique_id')
        reference['properties']['critique_entry_id']=ID;reference['required'].append('critique_entry_id')
        requests['critique-link']=reference
        from claimbranch.core.wording_policy import WORDING_ACK
        requests['acknowledge-wording-warning']=WORDING_ACK
    for kind,payload in REVISION_PAYLOADS.items(): requests[kind]=payload
    entries={'oneOf':[variant for kind,request in requests.items() for variant in (obj(id=ID,origin=ORIGIN,kind={'const':kind},request=request),obj(id=ID,kind={'const':kind},request=request))]}
    return obj(schema={'const':f'claimbranch.metadata-batch/v{version}'},entries=array(entries,256,1),selected_ids=array(ID,256,1,True))


def _prepare(project, entry):
    kind,request,origin=entry['kind'],entry['request'],entry['origin']
    if kind=='anchor':
        from .manuscript_anchors import prepare_registration
        return prepare_registration(project,**request,contribution_origin=origin)
    if kind=='measurement':
        from .typed_observations import prepare_measurement
        return prepare_measurement(project,request,contribution_origin=origin)
    if kind=='protocol':
        from .protocols import prepare_protocol
        return prepare_protocol(project,request,contribution_origin=origin)
    if kind=='co-report':
        from .co_report import prepare_co_report
        return prepare_co_report(project,request,contribution_origin=origin)
    if kind=='critique':
        from .critiques import prepare_critique
        return prepare_critique(project,request,original_input=encode(request,purpose='project') if request['operation_type']=='capture-critique' else None,contribution_origin=origin)
    from .claim_wording import prepare_revision
    return prepare_revision(project,kind,request,contribution_origin=origin)


def prepare_batch(project, raw):
    from .paper_service import PaperService
    from .typed_observations import current_source
    from .manuscript_anchors import source_statuses
    value=decode(raw,purpose='project')
    if type(value) is dict and type(value.get('entries')) is list:
        value=deepcopy(value)
        for entry in value['entries']:
            if type(entry) is dict:entry.setdefault('origin','unknown')
    from claimbranch.core.argument_import import _errors,_Diagnostics
    version=4 if type(value) is dict and value.get('schema')=='claimbranch.metadata-batch/v4' else 3 if type(value) is dict and value.get('schema')=='claimbranch.metadata-batch/v3' else 2 if type(value) is dict and value.get('schema')=='claimbranch.metadata-batch/v2' else 1
    schema=batch_schema(version)
    skeleton=deepcopy(schema);skeleton['properties']['entries']['items']={}
    diagnostics=_Diagnostics();_errors(value,skeleton,'',diagnostics)
    if not diagnostics:
        for index,entry in enumerate(value['entries']):_errors(entry,schema['properties']['entries']['items'],f'/entries/{index}',diagnostics)
    if diagnostics:return None,dict(valid=False,writes=False,**diagnostics.fields())
    value=normalize(value,schema,profile='paper')
    ids=[e['id'] for e in value['entries']]
    if len(ids)!=len(set(ids)) or not set(value['selected_ids'])<=set(ids):raise ContractError('Select unique available metadata entries')
    saved=decode(project.payload,purpose='project');digest=hashlib.sha256(raw).hexdigest()
    if any(s['sha256']==digest for s in saved.get('sources',[])):raise ContractError('This exact metadata batch is already retained; compare current work before a new amendment')
    candidate=project;previews=[];errors=[];critique_entries={}
    for index,entry in enumerate(value['entries']):
        if entry['id'] not in value['selected_ids']:continue
        try:
            effective=entry
            if entry['kind']=='critique-link':
                reference=entry['request']['critique_entry_id']
                if reference not in critique_entries:raise ContractError('critique_entry_id: requires an earlier selected successful critique capture')
                request={key:value for key,value in entry['request'].items() if key!='critique_entry_id'};request['critique_id']=critique_entries[reference]
                effective={**entry,'kind':'critique','request':dict(schema='claimbranch.critique-input/v1',operation_type='link-critique',payload=request)}
            result,preview=_prepare(candidate,effective)
            if preview.get('operation',{}).get('operation_type')=='record-critique':critique_entries[entry['id']]=preview['operation']['payload']['id']
            candidate=result
            # Critique preview is already an allowlist. Never render raw requests.
            previews.append(dict(id=entry['id'],kind=entry['kind'],origin=entry['origin'],review={k:v for k,v in preview.items() if k!='project_digest'}))
        except (ContractError,OSError) as error:
            # Prior candidate is only diagnostic; errors forbid the ENTIRE save.
            errors.append(dict(pointer=f'/entries/{index}',code='metadata-entry-invalid-or-blocked',message=str(error)))
    if errors:return None,dict(valid=False,errors=errors,writes=False,selected_ids=value['selected_ids'],prerequisite_note='A later entry depending on a failed earlier entry is also blocked; no prefix is publishable.')
    retained=decode(candidate.payload,purpose='project')
    retained['sources'].append(source_record(raw))
    from .project_work import ProjectWork
    candidate=ProjectWork(encode(retained,purpose='project'))
    from .claim_wording import lint
    review=dict(valid=True,lint=lint(candidate.work.history),project_digest=hashlib.sha256(project.payload).hexdigest(),input_digest=digest,
        selected_ids=value['selected_ids'],omitted_ids=sorted(set(ids)-set(value['selected_ids'])),entries=previews,
        before=PaperService(project.work.history).query('main'),after=PaperService(candidate.work.history).query('main'),
        source_binding=current_source(project),freshness=source_statuses(project.work.history),
        authority='One explicit personal batch confirmation; no past approval or protected authority.',writes=False)
    return candidate,review


def recheck_batch(project,review):
    from .typed_observations import current_source
    from .manuscript_anchors import source_statuses,inspect_anchor
    if hashlib.sha256(project.payload).hexdigest()!=review['project_digest'] or current_source(project)!=review['source_binding'] or source_statuses(project.work.history)!=review['freshness']:
        raise ContractError('Batch source or saved project changed; preview again')
    for entry in review['entries']:
        registration=entry['review'].get('registration')
        if registration and inspect_anchor(registration)['status']!='unchanged':raise ContractError('Selected manuscript block changed; preview again')


def run_batch(args):
    from .project_commands import _read_argument_input
    from .personal_project import PersonalProjectStore
    from .canonical_share import display_json
    raw=_read_argument_input(args.input)
    with PersonalProjectStore(args.directory) as store:
        project=store.load();candidate,review=prepare_batch(project,raw)
        shown={k:v for k,v in review.items() if k!='project_digest'}
        if args.dry_run or not review['valid']:
            print(display_json(shown,indent=2));return 0 if review['valid'] else 1
        if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Metadata registration requires a terminal; use --dry-run')
        from .import_review import confirm_operation
        if not confirm_operation(review,'register'):return 0
        if _read_argument_input(args.input)!=raw:raise ContractError('Batch input changed; preview again')
        recheck_batch(store.load(),review);store.verify_unchanged();recheck_batch(project,review)
        store.save(candidate)
        print('Selected extended records saved together. Originals and earlier judgments retained; manuscript unchanged.')
    return 0
