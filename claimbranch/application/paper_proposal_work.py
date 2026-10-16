"""Owned typed incorporation and historical origin in one workspace.

Only a live owner can stage a compared dependency batch. Serialized attempts
are reading material, never consent or a restored incorporation capability.
The terminal's existing checkpoint supplies the aggregate storage boundary.
"""
from claimbranch.core.argument_import import reference_origins
from copy import deepcopy
from dataclasses import asdict, replace
from functools import lru_cache
import secrets

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.context import ContextRecord, Destination, compile_context, review_outbound
from claimbranch.core.paper_changes import AmendmentLineage, lineage_schema, request_schema as changes_schema
from claimbranch.core.paper_context import FIELDS, request_schema
from claimbranch.core.paper_proposals import _references, provider_typed_result, provider_edit_result, result_schema
from claimbranch.core.advisory import ADVICE, DISCUSSION, AdvisoryReply, checked_advice
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, ID, JUDGMENT, array, normalize, nullable, obj
from .paper_authoring_snapshot import SOURCE
from .paper_workspace_snapshot import NUMBER, OWNER
from .paper_service import PaperService
from .provider_contract import (WIRE_MODEL_V1, WIRE_DESTINATION_URL_V1, WIRE_REQUEST,
    CODEX_RETAINED_MODEL_V1, CODEX_RETAINED_REQUEST)


DESTINATION = obj(url=FIELDS['claim']['statement'], model=ID)
DRAFT_FIELDS = obj(**FIELDS['draft'])
ATTEMPT = obj(owner=OWNER, source=SOURCE, request=request_schema(), draft_id=ID,
    draft_revision=nullable(NUMBER), draft_fields=nullable(DRAFT_FIELDS), request_id=ID, nonce=ID,
    created_at=NUMBER, expires_at=NUMBER, destination=DESTINATION, request_digest=HASH, context_digest=HASH,
    dispatched={'enum': [False, True]}, disposition={'enum': ['pending', 'proposed', 'cancelled', 'expired', 'stale', 'refused', 'failed', 'malformed']},
    response_digest=nullable(HASH), trace_digest=nullable(HASH), normalized_digest=nullable(HASH),
    provider_disposition=nullable({'enum': ['proposed', 'refused', 'failed', 'malformed']}),
    reservation={'type': 'string', 'pattern': '^r{0,1024}$', 'minLength': 0, 'maxLength': 1024},
    payload_availability={'enum': ['available', 'not-retained', 'erased']}, result=nullable(result_schema()))
LINEAGE = {'oneOf': [lineage_schema(), lineage_schema(2)]}
ORIGINS = obj(owner=OWNER, lineages=array(LINEAGE, 64))
EXPLANATION = obj(state={'enum': ['not-reviewed', 'partial', 'reviewed', 'leave-for-later']},
    entries=array(obj(topic_id=ID, text={**FIELDS['claim']['statement'], 'minLength': 0},
                      reuse_rationale={'enum': [False, True]}), 3))
# Keep causal context by replayable source and exact amendments, rather than
# trusting stored graph rows or fabricating an AI-written source Judgment.
CAUSE = obj(owner=OWNER, source=SOURCE, request=changes_schema(),
            judgment=JUDGMENT, origin_digests=array(HASH, 64, unique=True))
RECORDED = obj(operation_id=ID, cause=CAUSE, lineages=array(LINEAGE, 64),
               source_judgments=array(JUDGMENT, 8), explanation=EXPLANATION)
EXPLANATION_WORK = obj(cause=CAUSE, explanation=EXPLANATION)
PROPOSALS = obj(attempts=array(ATTEMPT, 48), origins=array(ORIGINS, 16),
                recorded=array(RECORDED, 8), explanations=array(EXPLANATION_WORK, 16))
OUTCOME = obj(disposition={'enum':['completed', 'cancelled', 'timed_out', 'connection_failed',
    'tls_verification_failed', 'malformed_response', 'response_too_large', 'redirect_refused', 'http_error', 'credential_echo']},
    elapsed_ms=NUMBER, http_status=nullable({'type':'integer', 'minimum':100, 'maximum':599}),
    reported_model=nullable({'type':'string', 'minLength':0, 'maxLength':128, 'pattern':'^[!-~]*$'}))
LIVE_ATTEMPT = deepcopy(ATTEMPT)
LIVE_ATTEMPT['properties']['destination'] = obj(url=WIRE_DESTINATION_URL_V1, model=WIRE_MODEL_V1)
LIVE_ATTEMPT['properties']['provider'] = obj(request=WIRE_REQUEST, outcome=nullable(OUTCOME))
LIVE_ATTEMPT['required'].append('provider')
PROPOSALS_V2 = obj(**{**PROPOSALS['properties'], 'attempts':array({'oneOf':[ATTEMPT, LIVE_ATTEMPT]},48)})
CODEX_OUTCOME = obj(disposition={'enum':['completed','cancelled','timed_out','start_failed',
    'auth_required','policy_refused','protocol_error','client_failed','malformed_response','response_too_large']},
    elapsed_ms=NUMBER, reported_model=nullable(CODEX_RETAINED_MODEL_V1),
    client_version=nullable({'type':'string','minLength':1,'maxLength':128,'pattern':'^[!-~]+$'}),
    thread_id=nullable(ID), turn_id=nullable(ID), cleanup_complete={'enum':[False,True]})
CODEX_ATTEMPT = deepcopy(ATTEMPT)
CODEX_ATTEMPT['properties']['destination'] = obj(url={'const':'https://chatgpt.com'},model=CODEX_RETAINED_MODEL_V1)
CODEX_ATTEMPT['properties']['codex'] = obj(request=CODEX_RETAINED_REQUEST,outcome=nullable(CODEX_OUTCOME))
CODEX_ATTEMPT['required'].append('codex')
PROPOSALS_V3 = obj(**{**PROPOSALS['properties'], 'attempts':array({'oneOf':[ATTEMPT,LIVE_ATTEMPT,CODEX_ATTEMPT]},48)})


EXTERNAL_SOURCE = obj(kind={'const':'external-diagnostic'}, verification={'const':'unverified-import'},
    model=CODEX_RETAINED_MODEL_V1, request_id=ID, request_body_digest=HASH, reported_response_digest=HASH)
EXTERNAL_ATTEMPT = deepcopy(ATTEMPT)
EXTERNAL_ATTEMPT['properties']['external'] = EXTERNAL_SOURCE
EXTERNAL_ATTEMPT['required'].append('external')
EXTERNAL_ATTEMPT['properties']['dispatched'] = {'const':False}
EXTERNAL_ATTEMPT['properties']['destination'] = obj(url={'const':'offline://frozen'}, model=CODEX_RETAINED_MODEL_V1)
PROPOSALS_V4 = obj(**{**PROPOSALS['properties'],
    'attempts':array({'oneOf':[ATTEMPT,LIVE_ATTEMPT,CODEX_ATTEMPT,EXTERNAL_ATTEMPT]},64)})

from .provider_contract import CODEX_ADVISORY_REQUEST, CODEX_EDIT_REQUEST
ADVISORY_ATTEMPT = deepcopy(CODEX_ATTEMPT)
ADVISORY_ATTEMPT['properties'].update(result=nullable(ADVICE), discussion=DISCUSSION,
    codex=obj(request=CODEX_ADVISORY_REQUEST, outcome=nullable(CODEX_OUTCOME)))
ADVISORY_ATTEMPT['required'].append('discussion')
PROPOSALS_V5 = obj(**{**PROPOSALS_V4['properties'],
    'attempts':array({'oneOf':[ATTEMPT,LIVE_ATTEMPT,CODEX_ATTEMPT,EXTERNAL_ATTEMPT,ADVISORY_ATTEMPT]},64)})
EDIT_ATTEMPT = deepcopy(CODEX_ATTEMPT)
EDIT_ATTEMPT['properties'].update(edit=DISCUSSION, codex=obj(request=CODEX_EDIT_REQUEST,outcome=nullable(CODEX_OUTCOME)))
EDIT_ATTEMPT['required'].append('edit')
LINEAGE_V3 = {'oneOf':[lineage_schema(),lineage_schema(2),lineage_schema(3)]}
PROPOSALS_V6 = deepcopy(PROPOSALS_V5)
PROPOSALS_V6['properties']['attempts']['items']['oneOf'].append(EDIT_ATTEMPT)
PROPOSALS_V6['properties']['origins']['items']['properties']['lineages']['items'] = LINEAGE_V3
PROPOSALS_V6['properties']['recorded']['items']['properties']['lineages']['items'] = LINEAGE_V3


def imported_proposals_schema(version=1):
    if type(version) is not int or version not in (1,2):raise ContractError('Unsupported imported retention version')
    from claimbranch.core.paper_capacity import lifecycle_schema
    result = lifecycle_schema(PROPOSALS_V6)
    result['properties']['recorded']['maxItems'] = 128 if version == 2 else 32
    result['properties']['recorded']['items']['properties']['source_judgments']['maxItems'] = 32
    result['properties']['explanations']['maxItems'] = 128 if version == 2 else 64
    return result


def _check_import_limits(entries):
    imported = [e for e in entries if 'external' in e]
    if len(imported) > 16 or len({tuple(e['owner']) for e in imported}) != len(imported):
        raise ContractError('Only one external response per judgment and sixteen per workspace can be retained')
    if len({e['external']['request_id'] for e in imported}) != len(imported):
        raise ContractError('This external request identity is already retained in this workspace')
    if len(entries) - len(imported) > 48:
        raise ContractError('Proposal attempt history is full')


def _external_binding(entry):
    return digest({'kind':'external-proposal-import/v1','context_digest':entry['context_digest'],
        'normalized_digest':entry['normalized_digest'],'external':entry['external'],
        'created_at':entry['created_at'],'owner':entry['owner'],'source':entry['source'],
        'request':entry['request']})


def preview_external_proposal(workspace, owner, request, raw, source):
    """Local preview; may allocate an empty draft in memory, never save or send."""
    source = normalize(source, EXTERNAL_SOURCE)
    session = workspace.draft(*owner)
    if (request['episode_id'],request['ref']) != tuple(owner)[:2]:
        raise ContractError('Import must belong to the current judgment context')
    bundle = session.compile_proposal_context(request, include_draft=False)
    value = provider_typed_result(raw, bundle)
    if value['status'] != 'ok': raise ContractError('Only a successful typed response can be imported')
    preview = {'owner':list(owner), 'request':deepcopy(request), 'context':decode(bundle.payload),
        'context_digest':bundle.digest, 'result':value, 'external':source,
        'draft_id':session._draft_id, 'editor_revision':session._revision}
    preview['digest'] = digest(preview)
    return preview


def import_external_proposal(workspace, owner, request, raw, source, *, confirmed_digest, now):
    """Explicit local history import; no inference, staging or human judgment."""
    with workspace._lock:
        preview = preview_external_proposal(workspace,owner,request,raw,source)
        if preview['digest'] != confirmed_digest or type(now) is not int or now < 0:
            raise ContractError('Review this exact external response and current context before import')
        if any(e.get('external') == preview['external'] and e['owner'] == list(owner)
               for e in workspace._proposal_entries):
            raise ContractError('This external response is already retained for this judgment')
        normalized = digest(preview['result'])
        entry = {'owner':list(owner),'source':{'commands':len(workspace.history.commands),'digest':request['view_digest']},
            'request':deepcopy(request),'draft_id':preview['draft_id'],'draft_revision':None,'draft_fields':None,
            'request_id':'import-'+secrets.token_hex(16),'nonce':'local-import','created_at':now,'expires_at':now,
            'destination':{'url':'offline://frozen','model':preview['external']['model']},
            'context_digest':preview['context_digest'],'dispatched':False,'disposition':'proposed',
            'response_digest':normalized,'normalized_digest':normalized,'provider_disposition':'proposed',
            'reservation':'','payload_availability':'available','result':preview['result'],'external':preview['external']}
        entry['request_digest'] = _external_binding(entry)
        entry['trace_digest'] = digest(_trace_value(entry))
        normalize(entry,EXTERNAL_ATTEMPT)
        _check_import_limits([*workspace._proposal_entries,entry])
        try:
            check_capacity(workspace,proposal_snapshot(workspace,entries=[*workspace._proposal_entries,entry]), allow_eviction=False)
        except ContractError as error:
            if str(error) == 'canonical JSON byte limit exceeded':
                raise ContractError('External response cannot fit in saved work; no import was saved') from error
            raise
        workspace._proposal_entries.append(entry)
        return entry['request_id']


def proposal_workspace_schema(proposals):
    if any('edit' in e for e in proposals['attempts']): return 'claimbranch.edit-workspace/v12'
    if any(lineage['schema'].endswith('/v3') for row in [*proposals['origins'],*proposals['recorded']]
           for lineage in row['lineages']): return 'claimbranch.edit-workspace/v12'
    if any('discussion' in e for e in proposals['attempts']): return 'claimbranch.advisory-workspace/v11'
    if any('external' in e for e in proposals['attempts']): return 'claimbranch.external-workspace/v10'
    if any('codex' in e for e in proposals['attempts']): return 'claimbranch.codex-workspace/v9'
    return 'claimbranch.provider-workspace/v8' if any('provider' in e for e in proposals['attempts']) else 'claimbranch.proposal-workspace/v7'


def _trace_value(entry):
    value = {'request_id':entry['request_id'], 'request_digest':entry['request_digest'],
             'response_digest':entry['response_digest'], 'model':entry['destination']['model'],
             'disposition':entry['provider_disposition']}
    if 'provider' in entry: value['provider'] = entry['provider']
    if 'codex' in entry: value['codex'] = entry['codex']
    if 'external' in entry: value['external'] = entry['external']
    return value


def _check_wire_outcome(entry):
    outcome = entry['provider']['outcome']
    if outcome is None:
        raise ContractError('Received provider trace lacks its outcome')
    wire = outcome['disposition']
    if wire == 'completed':
        if (entry['response_digest'] is None or outcome['http_status'] is None
                or not 200 <= outcome['http_status'] < 300
                or entry['provider_disposition'] not in ('proposed', 'refused', 'failed')):
            raise ContractError('Completed provider return requires its raw response and successful HTTP status')
    else:
        expected = 'malformed' if wire in ('malformed_response', 'response_too_large', 'credential_echo') else 'failed'
        if (entry['provider_disposition'] != expected or entry['normalized_digest'] is not None
                or entry['result'] is not None or outcome['reported_model'] is not None):
            raise ContractError('Failed provider return cannot supply proposal content')


def _check_codex_outcome(entry):
    outcome = entry['codex']['outcome']
    if outcome is None: raise ContractError('Received Codex trace lacks its outcome')
    if outcome['disposition'] == 'completed':
        if (entry['response_digest'] is None or not outcome['cleanup_complete']
                or outcome['client_version'] != entry['codex']['request']['client_version']
                or outcome['reported_model'] != entry['destination']['model']
                or outcome['thread_id'] is None or outcome['turn_id'] is None
                or entry['provider_disposition'] not in ('proposed','refused','failed')):
            raise ContractError('Completed Codex return requires its checked client, model, turn and cleanup')
    else:
        expected = 'malformed' if outcome['disposition'] in ('protocol_error','malformed_response','response_too_large') else 'failed'
        if (entry['provider_disposition'] != expected or entry['normalized_digest'] is not None
                or entry['result'] is not None or outcome['reported_model'] is not None):
            raise ContractError('Failed Codex return cannot supply proposal content')


def consequence_limit(history):
    return 128 if history.schema_version == 14 else 32 if history.schema_version == 5 else 8


def check_retained_causes(history, proposals):
    if history.schema_version != 14:return
    from .paper_storage_codec import encode as storage_bytes
    import hashlib
    causes={hashlib.sha256(storage_bytes(row['cause'])).digest()
            for key in ('recorded','explanations') for row in proposals[key]}
    if len(causes)>128:
        raise ContractError(f'capacity retained-review-causes: {len(causes)} / 128; earlier causes and writing remain preserved')


def proposal_snapshot(workspace, *, origins=None, entries=None, recorded=None):
    origins = origins or {}
    return {'attempts': deepcopy(workspace._proposal_entries if entries is None else entries),
        'origins': [{'owner': list(owner), 'lineages': [decode(o.payload) for _, o in sorted(origins.get(owner, work.origins).items())]}
                    for owner, work in sorted(workspace._candidates.items()) if origins.get(owner, work.origins)],
        'recorded': deepcopy(workspace._recorded_origins if recorded is None else recorded),
        'explanations': deepcopy(workspace._personal_explanations)}


def check_capacity(workspace, proposals, *, records=None, selected=None, unfinished=None, allow_eviction=True):
    """Check prospective complete writing before publishing an atomic batch."""
    check_retained_causes(workspace.history, proposals)
    _check_import_limits(proposals['attempts'])
    app = workspace._checkpoint_app
    if app is None:
        # Backend-only owners still obey the same bound; the real terminal uses
        # its complete workspace/project envelope below, including all writing.
        version = workspace.history.schema_version
        from .paper_storage_codec import encode as storage_bytes, decode as storage_decode
        from claimbranch.core.paper_capacity import lifecycle_schema
        normalize(proposals, imported_proposals_schema(2 if version == 14 else 1) if version in (5,14) else lifecycle_schema(PROPOSALS_V6) if version == 4 else PROPOSALS_V6,
                  profile='paper' if version in (4, 5, 14) else 'episode')
        value = {'seed': storage_decode(workspace.history.seed), 'commands': [storage_decode(c) for c in workspace.history.commands],
                 'proposals': proposals, 'candidates': list((records or {}).values()), 'unfinished':list((unfinished or {}).values())}
        if version in (4, 5, 14): value['schema_version'] = version
        storage_bytes(value)
        return
    from .tui_work_recovery import snapshot_value
    from .paper_work_store import PaperWork
    value = snapshot_value(app, proposals=False)
    value['schema'] = proposal_workspace_schema(proposals)
    value['proposals'] = proposals
    for item in value['paper']['drafts']:
        count = sum(e['dispatched'] for e in proposals['attempts'] if e['owner'] == item['owner'])
        item['session']['dispatched'] = max(item['session']['dispatched'], count)
    for entry in value['authoring']['candidates']:
        owner = tuple(entry['owner'])
        if unfinished and owner in unfinished:
            entry['unfinished'] = list(unfinished[owner].values())
        if records and owner in records:
            previous = set(r['id'] for r in entry['records'])
            entry['records'] = list(records[owner].values())
            new = sorted(set(records[owner]) - previous)
            entry['selected'] = sorted(set(entry['selected']) | set(new))
            for key in new:
                entry['aliases'].append({'id': key, 'alias': 'D'+str(entry['next_alias'])})
                entry['next_alias'] += 1
            if selected and owner in selected:
                entry['selected'] = sorted(selected[owner])
                entry['omitted'] = sorted(set(entry['omitted']) - set(selected[owner]))
    if allow_eviction:
        fit_new_payloads(app, value)
    else:
        work = PaperWork.create(app.paper.history, workspace=value)
        project = getattr(app.recovery, 'project', None)
        if project is not None: project.with_work(work)


def historical_entries(workspace):
    return [{**deepcopy(item), 'staging_available': False,
             'notice': 'Historical response; explicitly review its original and current context before selecting items.'}
            for item in workspace._proposal_entries]


def required_advice_ids(proposals):
    return {revision['advisory_origin']['request_id']
        for row in [*proposals['origins'],*proposals['recorded']] for lineage in row['lineages']
        for revision in lineage['revisions'] if revision.get('advisory_origin')}


def check_payload_erasure(workspace, request_id):
    """Required origins and copied follow-up input survive live and saved return."""
    if request_id in required_advice_ids(proposal_snapshot(workspace)):
        raise ContractError('This answer is required by retained passage origins and cannot be erased separately')
    if any(message['request_id'] == request_id for entry in workspace._proposal_entries
           for message in entry.get('discussion', entry.get('edit', {})).get('previous', [])):
        raise ContractError('This reply is included in a retained follow-up input and cannot be erased separately')


def fit_new_payloads(app, value, *, project=None):
    """Only never-saved optional responses yield to otherwise valid writing."""
    from .paper_work_store import PaperWork
    while True:
        try:
            work = PaperWork.create(app.paper.history, workspace=value)
            project = project or getattr(app.recovery, 'project', None)
            if project is not None:
                project.with_work(work)
            return value
        except ContractError as error:
            if str(error) != 'canonical JSON byte limit exceeded':
                raise
            removable = [e for e in value['proposals']['attempts'] if e['result'] is not None
                         and e['request_id'] not in app.paper._saved_proposal_payloads and 'external' not in e
                         and e['request_id'] not in required_advice_ids(value['proposals'])]
            if not removable:
                raise
            entry = removable[-1]
            entry['result'] = None; entry['payload_availability'] = 'not-retained'


def mark_saved(workspace, value):
    proposals = value.get('proposals')
    if proposals is None: return
    for saved in proposals['attempts']:
        if saved['result'] is not None:
            workspace._saved_proposal_payloads.add(saved['request_id'])
        else:
            current = next((e for e in workspace._proposal_entries if e['request_id'] == saved['request_id']), None)
            if current is not None:
                current['result'] = None; current['payload_availability'] = saved['payload_availability']


def _prefix(history, source, owner):
    if source['commands'] > len(history.commands):
        raise ContractError('Proposal source is outside retained history')
    if history.schema_version in (5, 14):
        return _imported_prefix(history.seed, history.commands[:source['commands']], source['digest'], tuple(owner))
    original = ResearchHistory.replay(history.seed, history.commands[:source['commands']])
    view = PaperService(original).query(owner[1], episode_id=owner[0])
    if view['digest'] != source['digest'] or owner[2] not in {node['id'] for node in view['nodes']}:
        raise ContractError('Proposal original owner/context differs from replayed source')
    return original


@lru_cache(maxsize=16)
def _imported_prefix(seed, commands, source_digest, owner):
    original = ResearchHistory.replay(seed, commands)
    view = _imported_source_service(original).query(owner[1], episode_id=owner[0])
    if view['digest'] != source_digest or owner[2] not in {node['id'] for node in view['nodes']}:
        raise ContractError('Proposal original owner/context differs from replayed source')
    return original


@lru_cache(maxsize=2)
def _imported_source_service(history):
    # Only exact immutable, freshly replayed history values can share a reader.
    # query() returns detached data; neither reviews nor consent live here.
    return PaperService(history)


def _bundle(history, entry):
    original = _prefix(history, entry['source'], entry['owner'])
    bundle = PaperService(original).compile_context(entry['request'])
    if entry['draft_fields'] is not None:
        record = ContextRecord.create(entry['request']['project_id'], entry['draft_id'], 'draft', 'private',
                                      entry['draft_fields'], schema_version=2)
        selection = replace(bundle.selection, fields=(*bundle.selection.fields, (record.id, tuple(entry['draft_fields']))))
        bundle = compile_context((*bundle.records, record), selection)
    return bundle


def _origin_check(history, origin, attempts):
    value = decode(origin.payload)
    from .paper_storage_codec import decode as storage_decode
    if value['project_id'] != storage_decode(history.seed)['project_id']:
        raise ContractError('Item origin belongs to another project')
    for revision in value['revisions']:
        advice = revision.get('advisory_origin')
        if advice:
            attempt = attempts.get(advice['request_id'])
            if (attempt is None or 'discussion' not in attempt or not attempt['dispatched']
                    or attempt['provider_disposition'] != 'proposed' or value['episode_id'] != attempt['owner'][0]
                    or any(advice[k] != attempt[k] for k in ('request_digest','context_digest','response_digest','trace_digest'))
                    or advice['reply_digest'] != attempt['normalized_digest']):
                raise ContractError('Advice origin lacks its owned historical response binding')
            if (attempt['result'] is None or attempt['payload_availability'] != 'available'
                    or attempt['result']['text'][advice['start']:advice['end']] != advice['passage']):
                raise ContractError('Selected passage requires its retained exact original answer')
        item = revision.get('proposal_origin')
        if not item:
            continue
        attempt = attempts.get(item['request_id'])
        if (attempt is None or 'discussion' in attempt or (not attempt['dispatched'] and 'external' not in attempt) or attempt['normalized_digest'] is None
                or value['episode_id'] != attempt['owner'][0]
                or any(item[k] != attempt[k] for k in ('request_digest', 'context_digest', 'response_digest', 'trace_digest'))
                or item['proposal_id'] != 'proposal-'+digest(attempt['request_id'])):
            raise ContractError('Item origin lacks its owned historical request/trace binding')
        if attempt['result'] is not None and item['item'] not in attempt['result']['items']:
            raise ContractError('Adopted item differs from its retained response')
        # Recheck required item content even after optional raw-payload erasure.
        # Dependencies may be absent here; their full response was checked at
        # live adoption, and mapped scientific records are checked in the cause.
        if item['item_digest'] != digest(item['item']):
            raise ContractError('Retained item digest changed')
        bindings = {b['item_id']: b['record_id'] for b in item['item_bindings']}
        bundle = _bundle(history, attempt)
        context_ids = {r['id'] for r in decode(bundle.payload)['records']}
        def mapped(value):
            if isinstance(value, dict):
                if set(value) == {'domain', 'id'}:
                    if value['domain'] == 'context':
                        if value['id'] not in context_ids:
                            raise ContractError('Origin reference was not selected for this request')
                        return value['id']
                    if value['id'] not in bindings:
                        raise ContractError('Origin lacks its proposed dependency identity')
                    return bindings[value['id']]
                return {k: mapped(v) for k, v in value.items()}
            return [mapped(v) for v in value] if isinstance(value, list) else value
        expected = {'id': bindings[item['item']['id']], 'kind': item['item']['kind'],
                    'body': mapped(item['item']['body'])}
        if revision['amendment'] != expected:
            raise ContractError('Provider-origin revision differs from its mapped proposal item')


def restore_proposals(workspace, value, *, unfinished=None):
    from .provider_profile import check_retained_provider_request, check_retained_codex_request
    from claimbranch.core.paper_capacity import lifecycle_schema
    schema = imported_proposals_schema(2 if workspace.history.schema_version == 14 else 1) if workspace.history.schema_version in (5, 14) else lifecycle_schema(PROPOSALS_V6) if workspace.history.schema_version==4 else PROPOSALS_V6
    value = normalize(value,schema, profile="paper" if workspace.history.schema_version in (4, 5, 14) else "episode")
    check_retained_causes(workspace.history,value)
    _check_import_limits(value['attempts'])
    attempts = {}
    for entry in value['attempts']:
        key = entry['request_id']; owner = tuple(entry['owner'])
        if key in attempts or owner not in workspace._drafts or (not entry['dispatched'] and 'external' not in entry):
            raise ContractError('Unique attempt requires its saved judgment owner')
        live = entry.get('provider') or entry.get('codex')
        if 'discussion' in entry or 'edit' in entry:
            from .paper_advisory import check_discussion_sources
            check_discussion_sources(entry, attempts)
        if entry['trace_digest'] is None:
            if (any(entry[k] is not None for k in ('response_digest', 'normalized_digest', 'provider_disposition', 'result'))
                    or entry['reservation'] != 'r'*1024 or entry['payload_availability'] != 'not-retained'
                    or entry['disposition'] not in ('pending', 'cancelled')):
                raise ContractError('Pending attempt cannot manufacture a response or spent trace')
            if live and live['outcome'] is not None:
                raise ContractError('Pending provider attempt cannot claim an outcome')
        else:
            provider = entry['provider_disposition']
            proposed = provider == 'proposed'
            if ((entry['response_digest'] is None and not live) or provider is None or entry['reservation']
                    or proposed != (entry['normalized_digest'] is not None)
                    or entry['result'] is not None and (not proposed or entry['result']['status'] != 'ok')
                    or proposed and entry['disposition'] not in ('proposed', 'cancelled', 'stale', 'expired')
                    or not proposed and entry['disposition'] not in (provider, 'cancelled', 'stale', 'expired')):
                raise ContractError('Received response requires its spent request and consistent disposition')
        bundle = _bundle(workspace.history, entry)
        destination = Destination(**entry['destination'])
        if 'external' in entry:
            if (entry['request_digest'] != _external_binding(entry) or entry['dispatched']
                    or (entry['request']['episode_id'],entry['request']['ref']) != tuple(entry['owner'][:2])
                    or entry['source']['digest'] != entry['request']['view_digest']
                    or entry['expires_at'] != entry['created_at'] or entry['draft_fields'] is not None
                    or entry['destination']['model'] != entry['external']['model']
                    or entry['provider_disposition'] != 'proposed' or entry['trace_digest'] is None
                    or entry['response_digest'] != entry['normalized_digest']):
                raise ContractError('External response import binding changed')
            review = None
        else:
            review = (check_retained_codex_request(bundle, entry) if 'codex' in entry else
            check_retained_provider_request(bundle, entry) if live else
            review_outbound(bundle, destination, request_id=key, nonce=entry['nonce'], now=entry['created_at'], result_format='typed'))
        if ((review is not None and not live and review.digest != entry['request_digest']) or bundle.digest != entry['context_digest']
                or (review is not None and review.expires_at != entry['expires_at'])
                or (entry['draft_fields'] is None) != (entry['draft_revision'] is None)):
            raise ContractError('Retained request/context/lifetime changed')
        if destination.remote_capable and not live:
            raise ContractError('Only offline historical topology is implemented here')
        if entry['result'] is not None:
            result = (checked_advice(canonical_bytes(entry['result'])) if 'discussion' in entry else
                (provider_edit_result if 'edit' in entry else provider_typed_result)(canonical_bytes(entry['result']), bundle))
            if entry['normalized_digest'] != digest(result) or entry['payload_availability'] != 'available':
                raise ContractError('Retained response digest or availability changed')
        elif entry['payload_availability'] == 'available':
            raise ContractError('Available payload is missing')
        if entry['trace_digest'] is not None:
            if live:
                (_check_codex_outcome if 'codex' in entry else _check_wire_outcome)(entry)
            # Provider disposition and local cancellation/staleness are separate.
            if digest(_trace_value(entry)) != entry['trace_digest'] or (not entry['dispatched'] and 'external' not in entry):
                raise ContractError('Retained trace identity differs')
        attempts[key] = entry
    for owner in workspace._drafts:
        dispatched = sum(e['dispatched'] for e in attempts.values() if tuple(e['owner']) == owner)
        if dispatched > workspace._drafts[owner]._prior_dispatches:
            raise ContractError('Saved response items cannot manufacture or omit spent requests')
    seen = set()
    for entry in value['origins']:
        owner = tuple(entry['owner'])
        if owner in seen or owner not in workspace._candidates:
            raise ContractError('Item origin requires one retained candidate owner')
        seen.add(owner); work = workspace._candidates[owner]
        origins = {}
        for raw in entry['lineages']:
            origin = AmendmentLineage.restore(canonical_bytes(raw)); key = origin.amendment['id']
            kept = work.records.get(key)
            editing = (unfinished or {}).get(owner, {}).get(key)
            if key in origins or (kept is not None and origin.amendment != kept) or (kept is None and
                    (editing is None or origin.amendment['kind'] != editing['kind'])):
                raise ContractError('Item origin differs from its kept candidate')
            _origin_check(workspace.history, origin, attempts)
            origins[key] = origin
        work._origins = origins
    from .paper_storage_codec import decode as storage_decode
    commands = [storage_decode(c) for c in workspace.history.commands]
    operations = {c['id']: c for c in commands}
    seen = set()
    for record in value['recorded']:
        key = record['operation_id']; command = operations.get(key)
        if key in seen or command is None or command['operation_type'] not in ('apply-selected-merge','apply-imported-merge'):
            raise ContractError('Recorded item origin requires its unique personal consequence')
        seen.add(key)
        science = _cause_validation(workspace.history, record['cause'])
        if command['episode_id'] != record['cause']['owner'][0] or command['payload']['selected_ids'] != sorted(
                set(science['selection']['selected']) | set(science['selection']['required'])):
            raise ContractError('Recorded origin selection differs from its cause')
        # Rebuild the exact personally recorded branch from its original source.
        # Matching only selected IDs would allow a different reason or body to
        # masquerade as the recorded explanation after restart.
        cause = record['cause']; original = _prefix(workspace.history, cause['source'], cause['owner'])
        index = commands.index(command)
        start = cause['source']['commands']
        if index <= start or commands[index-1]['operation_type'] not in ('record-interpretation','record-imported-interpretation'):
            raise ContractError('Recorded origin lacks its immediate reasoning command')
        branch_command = commands[index-1]
        from .paper_branch import judgment_value
        rebuilt, branch = PaperService(original).branch_candidate(cause['request'], judgment_value(cause['judgment']),
            operation_id=branch_command['id'], created_at=branch_command['created_at'], source_node_id=cause['owner'][2] if workspace.history.schema_version in (5, 14) else None)
        if ([storage_decode(c) for c in rebuilt.commands[start:]] != commands[start:index]
                or command['payload']['judgment'] != branch_command['payload']['judgment']
                or record['source_judgments'] != science['provenance'].get('source_judgments', [])):
            raise ContractError('Recorded origin reason, changes or inherited judgments differ from history')
        included = {item['id']: item['after'] for item in science['amendments'] if item['disposition'] != 'omitted'}
        lineages = [AmendmentLineage.restore(canonical_bytes(o)) for o in record['lineages']]
        if record['cause']['origin_digests'] != sorted(o.digest for o in lineages):
            raise ContractError('Recorded origin registry commitment differs')
        references = set(science['selection']['selected']) | set(science['selection']['required']) | set(science['selection']['existing_references'])
        identities = [o.amendment['id'] for o in lineages]
        if len(set(identities)) != len(identities) or not set(identities) <= references:
            raise ContractError('Recorded item origins require unique chosen or inherited references; omitted items stay unrecorded')
        for origin in lineages:
            _origin_check(workspace.history, origin, attempts)
            if origin.amendment['id'] in included and included[origin.amendment['id']] != origin.amendment:
                raise ContractError('Recorded item differs from its selected contribution')
        _validate_explanation_topics(science['topics'], record['explanation'])
        ai = (judgment_value(cause['judgment']).ai_influenced or science['provenance']['ai_influenced']
              or science['provenance'].get('origin_uncertain', False) or any(o.ai_influenced for o in lineages))
        explanation = record['explanation']
        if ai and explanation['state'] not in ('reviewed', 'leave-for-later'):
            raise ContractError('Recorded AI influence requires an explicit personal explanation choice')
        inherited = rebuilt.view('alternative', episode_id=cause['owner'][0])
        judgment_ai = any(c['contributor']=='ai' for j in inherited['judgments'] for c in j['history'])
        if workspace.history.schema_version in (5, 14):
            judgment_ai |= any(bool(reference_origins(r) & {'ai','mixed','unknown'}) for r in command['payload']['source_refs'])
        disposition = ('deferred' if explanation['state']=='leave-for-later' else 'answered') if judgment_ai else 'not-required'
        answers = [e['text'] if e['text'].strip() else cause['judgment']['rationale'] for e in explanation['entries']] if judgment_ai and explanation['state']=='reviewed' else []
        if command['payload']['disposition'] != disposition or command['payload']['answers'] != answers:
            raise ContractError('Recorded personal explanation choice differs from its consequence')
    seen = set()
    for entry in value['explanations']:
        identity = digest(entry['cause'])
        if identity in seen:
            raise ContractError('Partial explanation context must be unique')
        seen.add(identity)
        science = _cause_validation(workspace.history, entry['cause'])
        _validate_explanation_topics(science['topics'], entry['explanation'])
    workspace._proposal_entries = value['attempts']
    workspace._recorded_origins = value['recorded']
    workspace._personal_explanations = value['explanations']
    workspace._saved_proposal_payloads = {e['request_id'] for e in value['attempts'] if e['result'] is not None}


def cause_science(history, cause):
    original = _prefix(history, cause['source'], cause['owner'])
    if history.schema_version in (5, 14):
        from claimbranch.core.paper_capacity import encode, decode
        return decode(_imported_cause_science(original, encode(cause, purpose='history')), purpose='manifest')
    from .paper_branch import judgment_value
    return PaperService(original).preview_changes(cause['request'], judgment_value(cause['judgment']), source_node_id=cause['owner'][2] if history.schema_version in (5, 14) else None)


def _cause_validation(history, cause):
    if history.schema_version not in (5,14):
        science=cause_science(history,cause)
        return {**science,'topics':explanation_topics(cause,science)}
    from claimbranch.core.paper_capacity import encode,decode
    original=_prefix(history,cause['source'],cause['owner'])
    return decode(_imported_cause_validation(original,encode(cause,purpose='history')),purpose='manifest')


@lru_cache(maxsize=128)
def _imported_cause_validation(original,raw):
    from claimbranch.core.paper_capacity import encode,decode
    return encode(_imported_source_service(original)._causal_validation(decode(raw,purpose='history')),purpose='manifest')


@lru_cache(maxsize=128)
def _imported_cause_science(original, raw):
    from claimbranch.core.paper_capacity import encode, decode
    from .paper_branch import judgment_value
    cause = decode(raw, purpose='history')
    return encode(_imported_source_service(original).preview_changes(cause['request'], judgment_value(cause['judgment']),
                  source_node_id=cause['owner'][2]), purpose='manifest')


def explanation_topics(cause, science):
    from .paper_understanding import contextual_topics
    original = {**science['graphs']['after'], 'digest': digest(cause)}
    return contextual_topics({'original': original, 'work': {'selection': science['selection'], **science['impact']}})


def validate_explanation(cause, science, explanation):
    return _validate_explanation_topics(explanation_topics(cause, science),explanation)


def _validate_explanation_topics(topics, explanation):
    explanation = normalize(explanation, EXPLANATION)
    ids = [t['id'] for t in topics]
    entries = explanation['entries']
    if len({e['topic_id'] for e in entries}) != len(entries) or any(e['topic_id'] not in ids for e in entries):
        raise ContractError('Explanation writing requires its exact contextual topic')
    if explanation['state'] == 'reviewed' and ([e['topic_id'] for e in entries] != ids
            or any(not e['text'].strip() and not e['reuse_rationale'] for e in entries)):
        raise ContractError('Reviewed choice requires human text or explicit original reason reuse for each topic')
    return explanation


def record_provenance(workspace, work, science, request, judgment):
    included = set(science['selection']['selected']) | set(science['selection']['required'])
    references = included | set(science['selection']['existing_references'])
    origins = {}
    for record in workspace._recorded_origins:
        for raw in record['lineages']:
            origin = AmendmentLineage.restore(canonical_bytes(raw))
            if origin.amendment['id'] in references:
                origins[origin.amendment['id']] = origin
    for key in included:
        origin = work.origins.get(key)
        if origin:
            if origin.amendment != work.records[key]:
                raise ContractError('Selected item origin changed')
            origins[key] = origin
    lineages = [decode(origin.payload) for _, origin in sorted(origins.items())]
    cause = {'owner': list(work.owner), 'source': {'commands': len(workspace.history.commands), 'digest': request['view_digest']},
             'request': deepcopy(request), 'judgment': asdict(judgment), 'origin_digests': sorted(o.digest for o in origins.values())}
    ai = judgment.ai_influenced or science['provenance']['ai_influenced'] or science['provenance'].get('origin_uncertain', False) or any(o.ai_influenced for o in origins.values())
    from claimbranch.core.paper_capacity import lifecycle_schema
    return normalize(cause,lifecycle_schema(CAUSE) if workspace.history.schema_version in (4, 5, 14) else CAUSE, profile="paper" if workspace.history.schema_version in (4, 5, 14) else "episode"), lineages, ai


class PaperProposalWork:
    def __init__(self, workspace, owner, *, frozen_result, clock=None):
        if type(frozen_result) is not bytes or len(frozen_result) > 65536:
            raise ContractError('Bounded constructor-owned offline result required')
        self.workspace, self.owner = workspace, tuple(owner)
        self.session = workspace.draft(*owner)
        self.work = workspace.candidates(*owner)
        self.clock = clock or self.session._clock
        self._frozen = frozen_result
        self._current = self._outbound = self._proposal = self._bundle = None
        self._comparisons, self._ids = {}, {}
        self._request = None
        self._entry = None
        self._owned_requests, self._responses = set(), {}

    def prepare(self, request, *, include_draft=False):
        with self.workspace._lock:
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            bundle = self.session.compile_proposal_context(request, include_draft=include_draft)
            destination = Destination('offline://frozen', 'paper-typed-example-v1')
            review = review_outbound(bundle, destination, request_id='request-'+secrets.token_hex(16),
                                     nonce=secrets.token_hex(24), now=int(self.clock()), result_format='typed')
            return self._install_request(request, bundle, review, include_draft=include_draft)

    def _install_request(self, request, bundle, review, *, include_draft):
        with self.workspace._lock:
            self.cancel()
            self._ids = {}
            previous = self.workspace._proposal_active.get(self.owner)
            if previous is not None and previous is not self: previous.cancel()
            self.workspace._proposal_active[self.owner] = self
            self._current, self._outbound, self._bundle = review.request_id, review, bundle
            self._request = deepcopy(request)
            self._entry = self._request_entry(request, bundle, review, include_draft=include_draft)
            return review

    def _request_entry(self, request, bundle, review, *, include_draft):
        draft = next((r['fields'] for r in decode(bundle.payload)['records'] if r['kind'] == 'draft'), None)
        return {'owner': list(self.owner), 'source': {'commands': len(self.workspace.history.commands), 'digest': request['view_digest']},
            'request': deepcopy(request), 'draft_id': self.session._draft_id,
            'draft_revision': self.session._revision if include_draft else None, 'draft_fields': draft,
            'request_id': review.request_id, 'nonce': review.nonce, 'created_at': review.created_at, 'expires_at': review.expires_at,
            'destination': decode(review.payload)['destination'], 'request_digest': review.digest, 'context_digest': bundle.digest,
            'dispatched': False, 'disposition': 'pending', 'response_digest': None, 'trace_digest': None,
            'provider_disposition': None, 'reservation': 'r'*1024,
            'normalized_digest': None, 'payload_availability': 'not-retained', 'result': None}

    def _fresh(self):
        if self._current is None or self._entry['disposition'] not in ('pending', 'proposed'):
            raise ContractError('A current owned typed request is required; retained responses are historical')
        if self.workspace._proposal_active.get(self.owner) is not self:
            raise ContractError('A replacement request revoked this response\'s incorporation capability')
        if not self._entry['created_at'] <= int(self.clock()) < self._entry['expires_at']:
            raise ContractError('Typed request expired; manual writing and historical response remain')
        if (self.session._draft_id != self._entry['draft_id']
                or self.session._view_digest != self._entry['source']['digest']
                or self._entry['draft_revision'] is not None and self._entry['draft_revision'] != self.session._revision):
            raise ContractError('Typed proposal input changed; original response remains historical')
        bundle = self.session.compile_proposal_context(self._request, include_draft=self._entry['draft_fields'] is not None)
        if bundle != self._bundle:
            raise ContractError('Selected context changed')
        self.work.require_current()

    def begin(self, review):
        with self.workspace._lock:
            self._fresh()
            if review != self._outbound or self._entry['dispatched']:
                raise ContractError('Inspect this owner\'s exact current outbound review')
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            entries = [*self.workspace._proposal_entries, {**self._entry, 'dispatched': True}]
            check_capacity(self.workspace, proposal_snapshot(self.workspace, entries=entries))
            self.session._broker.begin(self._bundle, Destination(**self._entry['destination']), review,
                                       now=int(self.clock()), result_format='typed')
            self._entry['dispatched'] = True
            self.workspace._proposal_entries.append(self._entry)
            self._owned_requests.add(review.request_id)
            self._outbound = None

    def complete(self, request_id):
        with self.workspace._lock:
            entry = next((e for e in self.workspace._proposal_entries if e['request_id'] == request_id), None)
            if entry is None or request_id not in self._owned_requests:
                raise ContractError('Response requires this live owner\'s dispatched request')
            proposal = self.session._broker.complete_typed(request_id, self._frozen)
            trace = self.session._broker.sent[-1]
            entry.update(response_digest=trace.response_digest, trace_digest=trace.digest,
                         provider_disposition=trace.disposition, reservation='')
            if proposal is not None:
                entry['normalized_digest'] = digest(decode(proposal.payload))
                self._responses[request_id] = proposal
                if request_id == self._current:
                    try: self._fresh()
                    except ContractError:
                        if entry['disposition'] in ('pending', 'proposed'):
                            entry['disposition'] = 'stale' if int(self.clock()) < entry['expires_at'] else 'expired'
                    else:
                        entry['disposition'] = 'proposed'; self._proposal = proposal
                elif entry['disposition'] == 'pending': entry['disposition'] = 'stale'
                entry['result'] = decode(proposal.payload); entry['payload_availability'] = 'available'
                try: check_capacity(self.workspace, proposal_snapshot(self.workspace))
                except ContractError:
                    entry['result'] = None; entry['payload_availability'] = 'not-retained'
            elif entry['disposition'] == 'pending':
                entry['disposition'] = trace.disposition
            return self.historical()

    def historical(self):
        history = historical_entries(self.workspace)
        for entry in history:
            if entry['request_id'] in self._responses and entry['result'] is None and entry['payload_availability'] == 'not-retained':
                entry['result'] = decode(self._responses[entry['request_id']].payload)
                entry['notice'] = 'Session-readable response was not retained; minimal trace and human writing take precedence.'
        return history

    def cancel(self):
        with self.workspace._lock:
            if self._entry is not None and self._entry['disposition'] in ('pending', 'proposed'):
                self._entry['disposition'] = 'cancelled'
            self._current = self._outbound = self._proposal = None
            self._comparisons = {}

    def erase_payload(self, request_id):
        with self.workspace._lock:
            entry = next((e for e in self.workspace._proposal_entries if e['request_id'] == request_id), None)
            if entry is None or tuple(entry['owner']) != self.owner or entry['trace_digest'] is None:
                raise ContractError('Choose a received historical payload for this judgment')
            check_payload_erasure(self.workspace, request_id)
            if 'provider' not in entry and 'codex' not in entry and 'external' not in entry: self.session._broker.erase_payload(request_id)
            entry['result'] = None; entry['payload_availability'] = 'erased'
            self._responses.pop(request_id, None)
            if request_id == self._current:
                self._proposal = None; self._comparisons = {}

    def comparison_expiry(self):
        return self._entry['expires_at']

    def compare(self, item_ids):
        with self.workspace._lock:
            if self._entry is not None and 'discussion' in self._entry:
                raise ContractError('This reply is advice, not graph items. Prepare an explicit edit separately.')
            self._fresh()
            if self._proposal is None or type(item_ids) not in (list, tuple) or not item_ids or len(set(item_ids)) != len(item_ids):
                raise ContractError('Select distinct items from this live owned response')
            items = {i['id']: i for i in decode(self._proposal.payload)['items']}
            if not set(item_ids) <= items.keys():
                raise ContractError('Unknown proposal item')
            included = set(item_ids); pending = list(item_ids)
            while pending:
                for ref in _references(items[pending.pop()]):
                    if ref['domain'] == 'item' and ref['id'] not in included:
                        included.add(ref['id']); pending.append(ref['id'])
            mapped_ids = dict(self._ids)
            for key in sorted(included):
                if key not in mapped_ids:
                    mapped_ids[key] = items[key]['target_id'] or self.work.allocate_id()
            def rewrite(value):
                if isinstance(value, dict):
                    if set(value) == {'domain', 'id'}:
                        return mapped_ids[value['id']] if value['domain'] == 'item' else value['id']
                    return {k: rewrite(v) for k, v in value.items()}
                return [rewrite(v) for v in value] if isinstance(value, list) else value
            records, dependencies = [], {}
            for key in sorted(included):
                record_id = mapped_ids[key]
                existing = self.work.records.get(record_id)
                origin = self.work.origins.get(record_id)
                already_staged = origin and any(r.get('proposal_origin', {}).get('proposal_id') == self._proposal.id
                    and r.get('proposal_origin', {}).get('item', {}).get('id') == key
                    for r in decode(origin.payload)['revisions'] if r.get('proposal_origin'))
                if items[key]['action'] == 'create' and existing is not None and not already_staged:
                    raise ContractError('A new proposed item cannot replace a kept candidate identity')
                if existing is not None:
                    dependencies[record_id] = digest({'record': existing, 'origin': origin.digest if origin else None})
                records.append(existing if already_staged else {'id': record_id, 'kind': items[key]['kind'], 'body': rewrite(items[key]['body'])})
            prospective = {**self.work.records, **{r['id']: r for r in records}}
            graph = self.workspace.service.project_draft(self.owner[1], list(prospective.values()), episode_id=self.owner[0])
            value = {'request_id': self._current, 'item_ids': list(item_ids), 'required_item_ids': sorted(included - set(item_ids)),
                'records': records, 'previous_records': [self.work.records[r['id']] for r in records if r['id'] in self.work.records],
                'dependencies': dependencies, 'editor_revision': self.session._revision,
                'work_revision': self.workspace.work_revision, 'view_digest': self.session._view_digest,
                'graph': graph, 'proposal_digest': digest(decode(self._proposal.payload)), 'expires_at': self.comparison_expiry()}
            value['digest'] = digest(value)
            self._comparisons[value['digest']] = canonical_bytes(value)
            self._ids = mapped_ids
            return deepcopy(value)

    def stage(self, comparison):
        with self.workspace._lock:
            self._fresh()
            if (not isinstance(comparison, dict) or self._proposal is None
                    or self._comparisons.get(comparison.get('digest')) != canonical_bytes(comparison)
                    or comparison['request_id'] != self._current
                    or comparison['editor_revision'] != self.session._revision
                    or comparison['work_revision'] != self.workspace.work_revision):
                raise ContractError('Reopen the exact current item comparison; writing is retained')
            for key, binding in comparison['dependencies'].items():
                record, origin = self.work.records.get(key), self.work.origins.get(key)
                if record is None or digest({'record': record, 'origin': origin.digest if origin else None}) != binding:
                    raise ContractError('Referenced proposal dependency changed; compare again')
            items = {i['id']: i for i in decode(self._proposal.payload)['items']}
            origins, records = self.work.origins, self.work.records
            for record in comparison['records']:
                key = record['id']
                item = next(item for item in items.values() if self._ids.get(item['id']) == key)
                if key in origins and any(r.get('proposal_origin', {}).get('proposal_id') == self._proposal.id
                    and r.get('proposal_origin', {}).get('item', {}).get('id') == item['id']
                    for r in decode(origins[key].payload)['revisions'] if r.get('proposal_origin')):
                    continue
                source = {'proposal_id': self._proposal.id, 'request_id': self._current,
                    'request_digest': self._entry['request_digest'], 'context_digest': self._entry['context_digest'],
                    'response_digest': self._entry['response_digest'], 'trace_digest': self._entry['trace_digest'],
                    'item': item, 'item_digest': digest(item),
                    'item_bindings': [{'item_id': k, 'record_id': self._ids[k]} for k in sorted(
                        set(comparison['item_ids']) | set(comparison['required_item_ids']))]}
                previous = origins.get(key) or self.workspace.origin_for(key)
                if previous is None and key in records:
                    previous = AmendmentLineage.start(self.session._project, self.owner[0], records[key], version=2)
                origins[key] = previous.revise(record, proposal_origin=source) if previous else AmendmentLineage.start(
                    self.session._project, self.owner[0], record, proposal_origin=source)
                records[key] = deepcopy(record)
            # Recheck the complete current graph and checkpoint. Nothing is
            # published on any identity, cycle, capacity or origin failure.
            self.workspace.service.project_draft(self.owner[1], list(records.values()), episode_id=self.owner[0])
            check_capacity(self.workspace, proposal_snapshot(self.workspace, origins={self.owner: origins}),
                           records={self.owner: records}, selected={self.owner: self.work._selected | {r['id'] for r in comparison['records']}})
            new = sorted(set(records) - set(self.work.records))
            for key in new:
                self.work._aliases[key] = 'D'+str(self.work._next_alias); self.work._next_alias += 1
                self.work._selected.add(key)
            self.work._selected.update(r['id'] for r in comparison['records'])
            self.work._omitted.difference_update(r['id'] for r in comparison['records'])
            self.work._records, self.work._origins = records, origins
            self.work._changed()
            self._comparisons.pop(comparison['digest'], None)
            return [r['id'] for r in comparison['records']]


class RetainedProposalReview(PaperProposalWork):
    """New local review of retained AI items, never restored dispatch consent.

    Existing history owns provenance. Revalidation against current selected
    science grants only a short-lived comparison/staging capability.
    """
    def __init__(self, workspace, owner, request_id, *, clock=None):
        from claimbranch.core.paper_proposals import TypedProposal
        super().__init__(workspace, owner, frozen_result=b'', clock=clock)
        with workspace._lock:
            entry = next((e for e in workspace._proposal_entries if e['request_id'] == request_id), None)
            if (entry is None or tuple(entry['owner']) != self.owner or entry['result'] is None
                    or 'discussion' in entry or entry['provider_disposition'] != 'proposed' or entry['payload_availability'] != 'available'):
                raise ContractError('A retained proposal for this judgment is required')
            if entry['source']['digest'] != self.session._view_digest:
                raise ContractError('Recorded research changed; inspect existing items instead of reusing this proposal')
            active = workspace._proposal_active.get(self.owner)
            if active is not None and active._current is not None:
                if isinstance(active, RetainedProposalReview) or active._entry['disposition'] not in ('pending','proposed'):
                    pass  # Supersede only after every new-review check succeeds.
                else:
                    raise ContractError('Close the current proposal review before reviewing saved items')
            original = _bundle(workspace.history, entry)
            typed = (provider_edit_result if 'edit' in entry else provider_typed_result)(canonical_bytes(entry['result']), original)
            if digest(typed) != entry['normalized_digest']:
                raise ContractError('Retained proposal content changed')
            self._entry = deepcopy(entry)
            self._entry_digest = digest(entry)
            self._request = deepcopy(entry['request'])
            self._request['view_digest'] = self.session._view_digest
            self._bundle = self.session.compile_proposal_context(self._request,
                include_draft=entry['draft_fields'] is not None)
            if self._bundle.payload != original.payload or self._bundle.digest != original.digest:
                raise ContractError('Original proposal context changed; inspect its history and existing recorded items. Reuse requires a new proposal.')
            (provider_edit_result if 'edit' in entry else provider_typed_result)(canonical_bytes(typed), self._bundle)
            self.work.require_current()
            self._review_started = int(self.clock())
            self.basis = {'original': decode(original.payload), 'current': decode(self._bundle.payload),
                'request_id': request_id, 'destination': deepcopy(entry['destination']),
                'response_digest': entry['response_digest'], 'trace_digest': entry['trace_digest']}
            self._proposal = TypedProposal('proposal-'+digest(request_id), self.session._project,
                self.owner[0], entry['request_digest'], entry['context_digest'], entry['trace_digest'], canonical_bytes(typed))
            self._current = request_id
            for origin in self.work.origins.values():
                for revision in decode(origin.payload)['revisions']:
                    source = revision.get('proposal_origin')
                    if source and source['request_id'] == request_id:
                        for binding in source['item_bindings']:
                            old = self._ids.setdefault(binding['item_id'], binding['record_id'])
                            if old != binding['record_id']:
                                raise ContractError('Retained item has conflicting candidate identities')
            if active is not None and active._current is not None:
                active.cancel()
            workspace._proposal_active[self.owner] = self

    def _fresh(self):
        if self._current is None or self.workspace._proposal_active.get(self.owner) is not self:
            raise ContractError('Open a new local review of the retained proposal')
        if int(self.clock()) < self._review_started:
            raise ContractError('Local review clock changed; reopen its current context')
        entry = next((e for e in self.workspace._proposal_entries if e['request_id'] == self._current), None)
        if entry is None or digest(entry) != self._entry_digest:
            raise ContractError('Retained response changed or was erased; review again')
        current = self.session.compile_proposal_context(self._request,
            include_draft=self._entry['draft_fields'] is not None)
        if current != self._bundle:
            raise ContractError('Current proposal context changed; review again')
        self.work.require_current()

    def comparison_expiry(self):
        return int(self.clock()) + 120

    def stage(self, comparison):
        if (type(comparison) is not dict or type(comparison.get('expires_at')) is not int
                or int(self.clock()) >= comparison['expires_at']):
            raise ContractError('Local item comparison expired; compare the selected items again')
        return super().stage(comparison)

    def cancel(self):
        self._current = self._outbound = self._proposal = None
        self._comparisons = {}

    def prepare(self, *args, **kwargs):
        raise ContractError('Retained review cannot prepare or send a request')

    begin = complete = prepare


class ProviderProposalWork(PaperProposalWork):
    """Internal post-review wire lifecycle, reusing selective item incorporation.

    The personal TUI can prepare this controller. Its trusted caller must
    establish actual deployment qualification and foreground outbound intent
    before begin; a digest/configuration is not either verdict. Tests use only
    owned synthetic peers. Restore never allocates this live owner or its jobs.
    """
    def __init__(self, workspace, owner, *, clock=None):
        super().__init__(workspace, owner, frozen_result=b'', clock=clock)
        self._jobs = {}

    def prepare(self, request, *, profile, include_draft=False):
        from .provider_profile import prepare_provider_request, retained_provider_request
        with self.workspace._lock:
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            bundle = self.session.compile_proposal_context(request, include_draft=include_draft)
            prepared = prepare_provider_request(profile, bundle, request_id='request-'+secrets.token_hex(16),
                nonce=secrets.token_hex(24), now=int(self.clock()))
            metadata = retained_provider_request(prepared)
            self._install_request(request, bundle, prepared.review, include_draft=include_draft)
            self._entry.update(request_digest=prepared.digest, provider={'request':metadata, 'outcome':None})
            self._outbound = prepared
            return prepared

    def begin(self, prepared, *, transport, confirmed_digest, current_profile):
        from .provider_transport import ProviderTransport
        with self.workspace._lock:
            self._fresh()
            if (type(transport) is not ProviderTransport or prepared != self._outbound
                    or self._entry['dispatched'] or confirmed_digest != prepared.digest):
                raise ContractError('Inspect and confirm this owner\'s exact current wire request')
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            entries = [*self.workspace._proposal_entries, {**self._entry, 'dispatched':True}]
            check_capacity(self.workspace, proposal_snapshot(self.workspace, entries=entries))
            job = transport.start(prepared, confirmed_digest=confirmed_digest, current_profile=current_profile,
                current_context=self._bundle, now=int(self.clock()))
            # The offline broker keeps its remote denial. Count wire attempts
            # alongside offline/whole-judgment attempts through the same session.
            self.session._prior_dispatches += 1
            self._entry['dispatched'] = True
            self.workspace._proposal_entries.append(self._entry)
            self._jobs[prepared.review.request_id] = job
            self._owned_requests.add(prepared.review.request_id)
            self._outbound = None

    def complete(self, request_id):
        from .provider_transport import TransportResult
        with self.workspace._lock:
            job = self._jobs.get(request_id)
            entry = next((e for e in self.workspace._proposal_entries if e['request_id']==request_id), None)
            if job is None or entry is None or request_id not in self._owned_requests:
                raise ContractError('Response requires this live owner\'s outstanding wire request')
            result = job.poll()
            if result is None: return self.historical()
            if (type(result) is not TransportResult or result.request_id != request_id
                    or result.request_digest != entry['request_digest']):
                raise ContractError('Wire return differs from its owned request')
            outcome = normalize({k:getattr(result,k) for k in OUTCOME['properties']}, OUTCOME)
            typed, provider = None, 'failed'
            if result.disposition == 'completed':
                if result.response_digest is None:
                    raise ContractError('Completed wire return requires its raw response digest')
                try:
                    typed = provider_typed_result(result.typed_result, _bundle(self.workspace.history, entry))
                    provider = 'proposed' if typed['status']=='ok' else typed['status']
                except ContractError:
                    outcome['disposition'] = 'malformed_response'; outcome['reported_model'] = None
                    provider = 'malformed'
            elif result.disposition in ('malformed_response', 'response_too_large', 'credential_echo'):
                provider = 'malformed'
            prospective = deepcopy(entry)
            prospective.update(response_digest=result.response_digest, provider_disposition=provider, reservation='')
            prospective['provider']['outcome'] = outcome
            prospective['trace_digest'] = digest(_trace_value(prospective))
            normalize(prospective, LIVE_ATTEMPT)
            _check_wire_outcome(prospective)
            return self._retain_return(entry, prospective, request_id, typed, provider)

    def _retain_return(self, entry, prospective, request_id, typed, provider):
        from claimbranch.core.paper_proposals import TypedProposal
        with self.workspace._lock:
            entry.update(prospective)
            self._jobs.pop(request_id)
            if entry['disposition']=='pending':
                try: self._fresh()
                except ContractError:
                    entry['disposition'] = 'stale' if int(self.clock()) < entry['expires_at'] else 'expired'
                else: entry['disposition'] = provider
            if provider == 'proposed':
                proposal = (AdvisoryReply(canonical_bytes(typed)) if 'discussion' in entry else
                    TypedProposal('proposal-'+digest(request_id), self.session._project, self.owner[0],
                        entry['request_digest'], entry['context_digest'], entry['trace_digest'], canonical_bytes(typed)))
                entry['normalized_digest'] = digest(typed)
                self._responses[request_id] = proposal
                if request_id==self._current and entry['disposition']=='proposed': self._proposal = proposal
                entry['result'] = typed; entry['payload_availability'] = 'available'
                try: check_capacity(self.workspace, proposal_snapshot(self.workspace))
                except ContractError:
                    entry['result'] = None; entry['payload_availability'] = 'not-retained'
            return self.historical()

    def cancel(self):
        with self.workspace._lock:
            try:
                for job in getattr(self, '_jobs', {}).values(): job.cancel()
            finally:
                super().cancel()


class CodexProposalPreview(ProviderProposalWork):
    """Unsent CLI input in the existing UI; never a dispatched offline attempt.

    The CLI's tools, generated wrapper and actual boundary have not passed the
    selected provider gate. No job, trace, history or transport is created here.
    """
    def prepare(self, request, *, profile, include_draft=False):
        from .provider_profile import prepare_codex_request
        with self.workspace._lock:
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            bundle = self.session.compile_proposal_context(request, include_draft=include_draft)
            prepared = prepare_codex_request(profile, bundle, request_id='request-'+secrets.token_hex(16),
                nonce=secrets.token_hex(24), now=int(self.clock()))
            self._request, self._include_draft = deepcopy(request), include_draft
            self._outbound = prepared
            return prepared

    def recheck_preview(self, prepared, profile):
        with self.workspace._lock:
            if prepared != self._outbound or self._outbound is None:
                raise ContractError('Inspect this owner\'s current Codex input preview.')
            bundle = self.session.compile_proposal_context(self._request, include_draft=self._include_draft)
            prepared.recheck(profile, bundle, now=int(self.clock()))

    def begin(self, *args, **kwargs):
        raise ContractError('Codex dispatch unavailable; this controller prepares unsent input only.')


class CodexProposalWork(CodexProposalPreview):
    """Internal owned-return controller; no public launcher or provider verdict.

    A trusted caller must qualify authenticated access/egress and foreground
    intent before real dispatch. Tests supply owned peers. The public entry
    retains its independent refusal gate before creating a live transport.
    """
    def prepare(self, request, *, profile, include_draft=False, prompt=None, previous_requests=(), edit=False):
        from .provider_profile import prepare_codex_request
        with self.workspace._lock:
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            bundle = self.session.compile_proposal_context(request, include_draft=include_draft)
            from .paper_advisory import select_discussion
            discussion = select_discussion(self.workspace,self.owner,prompt,previous_requests) if prompt is not None else None
            if prompt is None and previous_requests:
                raise ContractError('Earlier messages require an explicit discussion question')
            prepared = prepare_codex_request(profile, bundle, request_id='request-'+secrets.token_hex(16),
                nonce=secrets.token_hex(24), now=int(self.clock()), discussion=discussion, edit=edit)
            # An unsent preview neither installs an attempt nor revokes the
            # previous response, including one owned by this same controller.
            self._preview = (deepcopy(request), include_draft, prepared)
            return prepared

    def recheck_preview(self, prepared, profile):
        if not getattr(self, '_preview', None) or prepared != self._preview[2]:
            raise ContractError('Inspect this owner\'s current Codex input preview')
        request, include_draft, _ = self._preview
        bundle = self.session.compile_proposal_context(request, include_draft=include_draft)
        if prepared.discussion is not None:
            from .paper_advisory import select_discussion
            discussion = decode(prepared.discussion)
            if canonical_bytes(select_discussion(self.workspace,self.owner,discussion['prompt'],
                    [m['request_id'] for m in discussion['previous']])) != prepared.discussion:
                raise ContractError('Selected previous response changed; review a new request')
        prepared.recheck(profile, bundle, now=int(self.clock()))
        self.work.require_current()

    def http_preview(self, prepared, current_profile):
        from .codex_egress import codex_http_preview
        with self.workspace._lock:
            self.recheck_preview(prepared, current_profile)
            request, include_draft, _ = self._preview
            current = self.session.compile_proposal_context(request, include_draft=include_draft)
            return codex_http_preview(prepared, current_profile=current_profile,
                current_context=current, now=int(self.clock()))

    def begin(self, prepared, *, transport, confirmed_digest, current_profile, confirmed_http_digest=None):
        from .codex_app_server import CodexAppServerTransport
        from .codex_relay import CodexRelayTransport
        from .provider_profile import PreparedCodexRequest, retained_codex_request
        with self.workspace._lock:
            if (type(prepared) is not PreparedCodexRequest or type(transport) not in (CodexAppServerTransport, CodexRelayTransport)
                    or confirmed_digest != prepared.digest):
                raise ContractError('Inspect and confirm this owner\'s exact current Codex input')
            self.recheck_preview(prepared, current_profile)
            if type(transport) is CodexRelayTransport and confirmed_http_digest != self.http_preview(prepared,current_profile)['body_sha256']:
                raise ContractError('Inspect and confirm this owner\'s complete current HTTP request')
            if self.session._prior_dispatches + len(self.session._broker.dispatched) >= 3:
                raise ContractError('This work allows at most three explicit requests')
            request, include_draft, _ = self._preview
            entry = self._request_entry(request, prepared.context, prepared.review, include_draft=include_draft)
            entry.update(request_digest=prepared.digest, dispatched=True,
                codex={'request':retained_codex_request(prepared), 'outcome':None})
            if prepared.discussion is not None: entry['edit' if prepared.edit else 'discussion'] = decode(prepared.discussion)
            normalize(entry, ADVISORY_ATTEMPT if 'discussion' in entry else EDIT_ATTEMPT if 'edit' in entry else CODEX_ATTEMPT)
            check_capacity(self.workspace, proposal_snapshot(self.workspace, entries=[*self.workspace._proposal_entries,entry]))
            current = self.session.compile_proposal_context(request, include_draft=include_draft)
            options = {'confirmed_http_digest':confirmed_http_digest} if type(transport) is CodexRelayTransport else {}
            job = transport.start(prepared, confirmed_digest=confirmed_digest, current_profile=current_profile,
                current_context=current, now=int(self.clock()), **options)
            # Start has consumed the request even if replacing an earlier
            # owner later raises. Retain/count it before cancellation callbacks.
            self.session._prior_dispatches += 1
            self.workspace._proposal_entries.append(entry)
            self._owned_requests.add(prepared.review.request_id)
            try:
                self._install_request(request, prepared.context, prepared.review, include_draft=include_draft)
            except BaseException:
                entry['disposition'] = 'cancelled'
                try: job.cancel()
                except Exception: pass  # Still owned by this controller and transport.
                raise
            finally:
                # Installing must not cancel the newly started job alongside
                # old ones. Track it on every exit, including interrupted install.
                self._jobs[prepared.review.request_id] = job
                self._preview = None
            self._entry = entry
            self._outbound = None

    def complete(self, request_id):
        from .codex_app_server import CodexResult, CodexFailure, PROPOSAL_FAILURES
        with self.workspace._lock:
            job = self._jobs.get(request_id)
            entry = next((e for e in self.workspace._proposal_entries if e['request_id']==request_id),None)
            if job is None or entry is None or request_id not in self._owned_requests:
                raise ContractError('Codex response requires this live owner\'s outstanding request')
            result = job.poll()
            if result is None: return self.historical()
            if (type(result) is not CodexResult or result.request_id != request_id
                    or result.request_digest != entry['request_digest']):
                raise ContractError('Codex return differs from its owned request')
            from .codex_relay import valid_failure
            wire=getattr(job,'wire_result',None)
            failure=wire.get('failure') if type(wire) is dict else None
            self._live_failure=({'request_id':request_id,**failure}
                if result.disposition!='completed' and failure is not None and valid_failure(failure) else None)
            if (result.disposition == 'malformed_response' and type(result.failure) is CodexFailure
                    and type(result.failure.category) is str and result.failure.category in PROPOSAL_FAILURES):
                self._live_failure = {'request_id': request_id, 'phase': 'response_validation',
                    'category': result.failure.category}
            typed, provider = None, 'failed'
            prospective = deepcopy(entry)
            schema = ADVISORY_ATTEMPT if 'discussion' in entry else EDIT_ATTEMPT if 'edit' in entry else CODEX_ATTEMPT
            prospective.update(response_digest=result.response_digest,provider_disposition=provider,reservation='')
            try:
                outcome = normalize({k:getattr(result,k) for k in CODEX_OUTCOME['properties']},CODEX_OUTCOME)
                prospective['codex']['outcome'] = outcome
                if result.disposition == 'completed':
                    # Verify completion metadata before a malformed scientific
                    # result can downgrade the completion branch.
                    _check_codex_outcome(prospective)
                    try:
                        typed = (checked_advice(result.typed_result) if 'discussion' in entry else
                            (provider_edit_result if 'edit' in entry else provider_typed_result)(result.typed_result,_bundle(self.workspace.history,entry)))
                        provider = 'proposed' if typed['status']=='ok' else typed['status']
                    except ContractError:
                        outcome['disposition'] = 'malformed_response'; outcome['reported_model'] = None
                        provider = 'malformed'
                elif result.disposition in ('protocol_error','malformed_response','response_too_large'):
                    provider = 'malformed'
                prospective['provider_disposition'] = provider
                normalize(prospective,schema); _check_codex_outcome(prospective)
            except ContractError:
                # An owned immutable result cannot be repaired by polling it
                # again. Save a terminal sanitized failure, never a stuck attempt.
                typed, provider = None, 'malformed'
                def bounded(value, schema, fallback):
                    try: return normalize(value,schema)
                    except ContractError: return fallback
                prospective.update(response_digest=bounded(result.response_digest,nullable(HASH),None),
                    provider_disposition=provider)
                prospective['codex']['outcome'] = {'disposition':'protocol_error',
                    'elapsed_ms':bounded(result.elapsed_ms,NUMBER,0), 'reported_model':None,
                    'client_version':None,'thread_id':None,'turn_id':None,
                    'cleanup_complete':bounded(result.cleanup_complete,{'enum':[False,True]},False)}
            prospective['trace_digest'] = digest(_trace_value(prospective))
            normalize(prospective,schema); _check_codex_outcome(prospective)
            return self._retain_return(entry,prospective,request_id,typed,provider)
