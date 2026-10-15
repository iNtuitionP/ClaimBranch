"""Selected, reproducible public projection. No accepted writer or provider I/O."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import unicodedata

from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode, encode, PROJECT_BYTES

SCHEMA = 'claimbranch.canonical-share/v1'
POLICY = 'selected-main-science/v1'
SELECTION_SCHEMA = 'claimbranch.share-selection/v1'
OMISSIONS = ['private paths and artifact references', 'raw imported sources and source hashes',
             'critique questions, originals, identities and reasons', 'manuscript text and source bindings',
             'notes, unfinished writing, AI payloads and execution traces',
             'historical evidence values, past decisions and unselected branches',
             'unselected records and unselected judgment reasons',
             'internal record, operation and cell identifiers']


def selection(value):
    if type(value) is not dict or set(value) != {'schema', 'record_ids', 'reason_ids'} or value['schema'] != SELECTION_SCHEMA:
        raise ContractError('Use a share-selection/v1 object with record_ids and reason_ids only.')
    for key in ('record_ids', 'reason_ids'):
        ids = value[key]
        if type(ids) is not list or len(ids) > 2048 or any(type(i) is not str or not i for i in ids) or len(set(ids)) != len(ids):
            raise ContractError('Share selection requires bounded, unique record identifiers.')
    if not value['record_ids']:
        raise ContractError('Select at least one scientific record; nothing was written.')
    return {'schema': SELECTION_SCHEMA, 'record_ids': sorted(value['record_ids']), 'reason_ids': sorted(value['reason_ids'])}


def _catalog(project):
    history = project.work.history
    if history.schema_version not in (4, 5):
        raise ContractError('Canonical sharing requires a saved paper profile with public ID mappings; legacy work is unchanged.')
    view = history.view('main')
    reviewed_dependencies=set()
    if history.has_graph_edits:
        from .paper_service import PaperService
        reviewed_dependencies={n['id'] for n in PaperService(history).query('main')['nodes'] if n['content'].get('review_required')}
    mappings = {m['private_id']: m['public_id'] for m in decode(project.payload, purpose='project')['public_ids']}
    records, dependencies, reasons = {}, {}, {}
    record_origins = {}
    from claimbranch.core.research_history import _reduce
    # Only actually adopted amendments influence main. Unmerged proposals and
    # unchanged dependencies cannot contribute a new record origin.
    for merge in _reduce(history.seed,history.commands)['merges']:
        preview=merge['preview']
        adopted=set(preview['amendments']['selected']+preview['amendments']['required'])
        origins={c['contributor'] for j in (preview['source_judgment'],merge['judgment']) for c in j['history']}
        for change in preview['changes']:
            if change['id'] not in adopted: continue
            key=change['body']['claim_id'] if change['kind']=='claim-status' else change['id']
            record_origins.setdefault(key,set()).update(origins)
    for decision in view.get('co_reports',{}).values():
        for key,origins in decision['reading_origins'].items(): record_origins.setdefault(key,set()).update(origins)
    branch_ai = any(c['contributor']=='ai' for j in view.get('judgments',[]) for c in j.get('history',[]))
    def public(key):
        if key not in mappings:
            raise ContractError('Public identity is missing in the saved revision; no sharing file was created.')
        return mappings[key]
    def add(key, kind, content, refs=(), reason=None, original=None):
        if key in records:
            raise ContractError('Ambiguous sharing record identity.')
        origins = set()
        raw = original or {}
        for r in raw.get('source_refs', []) + view.get('imported_dependencies', {}).get(key, []):
            origins.add(r['contributor'])
        mark = raw.get('imported_source', {})
        if mark.get('contributor'): origins.add(mark['contributor'])
        if raw.get('origin'): origins.add(raw['origin'])
        # No missing origin becomes human. Conservative current judgment influence
        # is disclosed without exposing retained provider/source payloads.
        origins.update(record_origins.get(key,set()))
        for declared in view.get('metadata_origins',{}).values():
            if key in declared['subject_ids']:origins.add(declared['origin'])
        if kind not in ('private-critique','critique-reference') and key in view.get('titles',{}):content['title']=view['titles'][key]
        if kind not in ('private-critique','critique-reference') and (key in reviewed_dependencies or any(any(e['id']==key for e in r['edits']) for r in view.get('graph_revisions',[]))):content['review_required']=True
        content['branch_ai_context_present'] = branch_ai
        content['origins'] = sorted(origins or {'unknown'})
        content['source_fidelity_verified'] = False
        content['unresolved_source_fields'] = mark.get('unresolved_leaf_count', 0) + sum(r.get('unresolved_count', 0) for r in raw.get('source_refs', []) + view.get('imported_dependencies', {}).get(key, []))
        records[key] = {'id': public(key), 'kind': kind, 'content': content}
        dependencies[key] = set(refs)
        if reason is not None: reasons[key] = reason
    def mapped(values): return [public(k) for k in values]
    def fields(raw, names): return {k: raw[k] for k in names if k in raw}
    def metric(raw): return fields(raw, ('name', 'definition', 'unit', 'comparison'))
    for claim in view['claims']:
        c = fields(claim, ('statement', 'status', 'role', 'scope'))
        c['parent_ids'] = mapped(claim['parent_ids'])
        policy = view.get('wording_policies', {}).get(claim['id'])
        if policy: c['wording'] = fields(policy, ('grade', 'limitation', 'allowed_wording', 'required_caveats', 'banned_phrases', 'placement'))
        add(claim['id'], 'claim', c, claim['parent_ids'], policy.get('rationale') if policy else None, claim)
    for run in view['experiments']:
        c = fields(run, ('question', 'method', 'conditions')); c['metric'] = metric(run['metric'])
        add(run['id'], 'experiment', c, original=run)
    for obs in view['evidence']:
        c = fields(obs, ('statement', 'value', 'status')); c['experiment_id'] = public(obs['run_id'])
        c['revision_number'] = len(obs['history'])
        if 'measurement' in obs:
            table = obs['measurement']
            # Local indices preserve exact table joins without disclosing unmapped
            # user-chosen cell/column/row identifiers or allocating private IDs.
            columns = {col['id']: i for i, col in enumerate(table['columns'])}
            vocab = view.get('condition_vocabulary', {})
            keys = sorted(vocab)
            def tags(values):
                return [{'condition_index': keys.index(t['key']), 'value_index': vocab[t['key']]['values'].index(t['value']), 'condition_label': t['key'], 'value_label': t['value']} for t in values]
            c['measurement'] = dict(id=public(table['id']), estimand=table['estimand'], conditions=tags(table['conditions']),
                columns=[dict(index=i, **fields(col, ('name', 'type', 'raw_unit', 'display_unit'))) for i, col in enumerate(table['columns'])],
                rows=[dict(index=i, conditions=tags(row['conditions']), cells=[dict(column_index=columns[cell['column_id']], value=cell['value']) for cell in row['cells']]) for i, row in enumerate(table['rows'])],
                condition_labels_omitted=False, artifact_fidelity_verified=False)
        add(obs['id'], 'observation', c, [obs['run_id']], obs['history'][-1].get('rationale'), obs)
        if 'measurement' in obs:
            table=obs['measurement']
            used_keys={t['key'] for t in table['conditions']}
            used_keys.update(t['key'] for row in table['rows'] for t in row['conditions'])
            declared={r['origin'] for r in view.get('metadata_origins',{}).values() if r.get('condition_key') in used_keys}
            if declared:c['origins']=sorted(set(c['origins'])|declared)
    for change in view['changes']:
        key, kind, body = change['id'], change['kind'], change['body']
        if kind == 'interpretation':
            content = dict(statement=body['statement'], observation_ids=mapped(body['observation_ids']))
            for d in view.get('co_reports', {}).values():
                for reading in d['readings']:
                    if reading['id']==key: content['scope']=reading['scope']
            judgment = next((j for j in view.get('judgments', []) if j['episode_id']==view.get('interpretation_episode_ids', {}).get(key)), None)
            add(key, kind, content, body['observation_ids'], judgment['rationale'] if judgment else None, change)
        elif kind == 'scientific-edge':
            add(key, kind, dict(source_id=public(body['source_id']), target_id=public(body['target_id']), edge_type=body['edge_type']),
                [body['source_id'], body['target_id']], body.get('rationale'), change)
        elif kind == 'experiment-plan':
            c = fields(body, ('objective', 'status', 'conditions')); c.update(claim_id=public(body['claim_id']), metric=metric(body['metric']))
            add(key, kind, c, [body['claim_id']], original=change)
    for change in view['changes']:
        if change['kind']=='scientific-edge':
            target=change['body']['target_id']
            if target in dependencies: dependencies[target].add(change['id'])
        elif change['kind']=='experiment-plan':
            dependencies[change['body']['claim_id']].add(change['id'])
        elif change['kind']=='claim-status':
            target=change['body']['claim_id'];basis=change['body']['basis_ids']
            dependencies[target].update(basis)
            records[target]['content']['status_basis_ids']=mapped(basis)
    for key, dependency in view.get('companion_dependencies', {}).items():
        refs = [dependency['target_id'], dependency['companion_id']]
        add(key, 'reporting-companion', dict(target_id=public(refs[0]), companion_id=public(refs[1]), **fields(dependency, ('scope', 'status'))), refs, dependency['rationale'], dependency)
        if dependency['status'] == 'active': dependencies[refs[0]].add(key)
    for key, anchor in view.get('manuscript_anchors', {}).items():
        refs = anchor['expresses'] + anchor['plots'] + anchor['parents']
        add(key, 'manuscript-anchor', dict(kind=anchor['kind'], expresses=mapped(anchor['expresses']), plots=mapped(anchor['plots']), parents=mapped(anchor['parents']), text='omitted'), refs, original=anchor)
    for key, decision in view.get('co_reports', {}).items():
        refs = decision['selected_ids'] + decision['companion_ids'] + [r['edge_id'] for r in decision['readings']]
        c = dict(disposition='co-reported', interpretation_ids=mapped(decision['selected_ids']), companion_ids=mapped(decision['companion_ids']), edge_ids=mapped([r['edge_id'] for r in decision['readings']]),
                 reading_origins=[dict(id=public(k), origins=v) for k, v in sorted(decision['reading_origins'].items())], understanding_verified=False)
        add(key, 'co-report', c, refs, decision['judgment']['rationale'])
        for reading in decision['selected_ids']: dependencies[reading].add(key)
    for key, protocol in view.get('protocols', {}).items():
        refs = [protocol['plan_id']] + ([protocol['supersedes_id']] if protocol['supersedes_id'] else [])
        c = fields(protocol, ('prediction', 'falsifier', 'prewritten_wording', 'inspected_before_registration'))
        c.update(plan_id=public(protocol['plan_id']), supersedes_id=public(protocol['supersedes_id']) if protocol['supersedes_id'] else None,
                 committed_reference='omitted', chronology_verified=False, plan_changed_since_registration=view.get('protocol_plan_digests',{}).get(protocol['plan_id']) != protocol['expected_plan_digest'], gates=[dict(id=public(g['id']), **fields(g, ('name', 'tolerance', 'reference'))) for g in protocol['gates']])
        add(key, 'protocol', c, refs, protocol['rationale'], protocol)
        for gate in protocol['gates']:
            add(gate['id'], 'registered-gate', dict(protocol_id=public(key), **fields(gate, ('name', 'tolerance', 'reference'))), [key])
        dependencies[key].update(g['id'] for g in protocol['gates'])
        if protocol['plan_id'] in dependencies: dependencies[protocol['plan_id']].add(key)
    for bucket, kind, reference_fields, scalar_fields in (
        ('experiment_associations', 'protocol-experiment', ('protocol_id', 'experiment_id'), ('metric_differs_from_registered_plan', 'preinspection_disclosure_conflict')),
        ('gate_amendments', 'gate-amendment', ('protocol_id', 'gate_id', 'expected_rule_id'), ('new_tolerance', 'new_reference', 'decided_after_result', 'app_result_precedes_amendment', 'chronology_conflict')),
        ('gate_results', 'gate-result', ('association_id', 'gate_id', 'rule_id'), ('status',)),
        ('outcome_assessments', 'outcome', ('association_id',), ('classification', 'discrimination', 'limitations', 'gate_validity', 'validity_verified'))):
        for key, raw in view.get(bucket, {}).items():
            refs = [raw[f] for f in reference_fields]
            c = fields(raw, scalar_fields); c.update({f: public(raw[f]) for f in reference_fields})
            for f in ('rule_ids', 'gate_result_ids'):
                if f in raw: c[f] = mapped(raw[f]); refs += raw[f]
            if 'observation_revisions' in raw:
                c['observation_basis'] = []
                for basis in raw['observation_revisions']:
                    obs = next(o for o in view['evidence'] if o['id'] == basis['observation_id'])
                    event_index = next(i for i, e in enumerate(obs['history']) if e['event_id'] == basis['event_id'])
                    c['observation_basis'].append(dict(observation_id=public(obs['id']), revision_number=event_index+1, current_revision=event_index+1 == len(obs['history'])))
                    refs.append(obs['id'])
            add(key, kind, c, refs, raw['rationale'], raw)
            # Any selected protocol displays all its recorded failures/amendments;
            # selecting an observation also brings its linked protocol assessment.
            owner = raw.get('protocol_id') or view.get('experiment_associations', {}).get(raw.get('association_id'), {}).get('protocol_id')
            if owner: dependencies[owner].add(key)
            if kind=='protocol-experiment': dependencies[raw['experiment_id']].add(key)
            for basis in raw.get('observation_revisions', []): dependencies[basis['observation_id']].add(key)
    for key, q in view.get('critiques', {}).items():
        # Known-private prose is never selected, even with reason opt-in.
        records[key] = dict(id=public(key), kind='private-critique', content=dict(content='omitted', scientific=False, resolved=False))
        dependencies[key] = set()
    for key, link in view.get('critique_links', {}).items():
        refs = [link['critique_id'], link['target_id']]
        records[key] = dict(id=public(key), kind='critique-reference', content=dict(source_id=public(refs[0]), target_id=public(refs[1]), relation=link['relation'], scientific=False, resolved=False))
        dependencies[key] = set(refs)
        if refs[1] in dependencies: dependencies[refs[1]].add(key)
    return records, dependencies, reasons, mappings


def prepare_share(project, requested, *, public_selection=False):
    requested = selection(requested)
    try: records, dependencies, reasons, mappings = _catalog(project)
    except (KeyError, TypeError, ValueError, StopIteration):
        raise ContractError('Saved scientific dependencies cannot be projected by this sharing policy; no file was written.') from None
    reverse = {public: private for private, public in mappings.items()}
    if public_selection:
        try:
            requested = selection(dict(schema=SELECTION_SCHEMA, record_ids=[reverse[k] for k in requested['record_ids']], reason_ids=[reverse[k] for k in requested['reason_ids']]))
        except KeyError: raise ContractError('Unknown public selection identity.') from None
    selected = set(requested['record_ids']); reason_ids = set(requested['reason_ids'])
    if not selected <= records.keys(): raise ContractError('Unavailable selected scientific record; no file was written.')
    if any(records[k]['kind'] in ('private-critique', 'critique-reference') for k in selected):
        raise ContractError('Select scientific records; private critiques enter only as omitted reference placeholders.')
    included, pending = set(), list(selected)
    while pending:
        key = pending.pop()
        if key in included: continue
        if key not in records: raise ContractError('Required scientific dependency is unavailable; no file was written.')
        included.add(key); pending.extend(dependencies[key])
    if not reason_ids <= included or not reason_ids <= reasons.keys():
        raise ContractError('Reasons must explicitly name included records with shareable reasons.')
    output = []
    for key in sorted(included, key=lambda k: mappings[k]):
        record = records[key]
        if key in reason_ids: record = {**record, 'reason': reasons[key]}
        output.append(record)
    policy_selection = dict(schema=SELECTION_SCHEMA, record_ids=sorted(mappings[k] for k in selected), reason_ids=sorted(mappings[k] for k in reason_ids))
    version=2 if project.work.history.has_graph_edits else 1
    base = dict(schema='claimbranch.canonical-share/v'+str(version), policy=POLICY, selection=policy_selection,
                required_record_ids=sorted(mappings[k] for k in included-selected), records=output,
                omissions=OMISSIONS, anonymity_verified=False, authority='read-only personal projection; not a backup or scientific verification')
    # Keyed private-revision commitment publishes neither source hashes nor paths.
    # It is a reproducibility check with the private source, not authentication.
    base['private_revision_commitment'] = hmac.new(hashlib.sha256(project.payload).digest(), encode(base, purpose='project'), hashlib.sha256).hexdigest()
    from claimbranch.core.research_schema import normalize
    normalize(base, share_schema(version), profile='paper')
    raw = encode(base, purpose='project')
    _check_known_private(project, base)
    return raw


def _check_known_private(project, value):
    """Known private literals win over selected prose; no general anonymity claim."""
    from claimbranch.core.paper_capacity import source_bytes
    saved = decode(project.payload, purpose='project')
    protected = set()
    view=project.work.history.view('main')
    for run in view['experiments']:
        if run.get('source_ref'): protected.add(run['source_ref'])
    for observation in view['evidence']:
        for event in observation['history']:
            for artifact in event.get('measurement',{}).get('artifact_refs',[]):
                protected.add(artifact['path'])
    sources = saved.get('associations',[]) + [a['source'] for a in view.get('manuscript_anchors',{}).values()]
    for source in sources:
        for key in ('root','git_dir','git_common_dir','manuscript'):
            if source.get(key): protected.add(os.fsdecode(bytes.fromhex(source[key])))

    for record in saved.get('critique_sources', []):
        source = decode(source_bytes(record['source']), purpose='project')['payload']
        for name in ('private_original', 'private_identity', 'private_label'):
            if source.get(name): protected.add(source[name])
    # Omitted batch entries are retained privately too. Their known private
    # literals cannot be laundered through another selected scientific record.
    for record in saved.get('sources', []):
        raw=source_bytes(record)
        try:source=decode(raw,purpose='project')
        except ContractError:
            # Profile conversion retains a framed binary checkpoint. It is
            # not a metadata batch; its integrity was checked above by source_bytes.
            continue
        if type(source) is not dict or source.get('schema')!='claimbranch.metadata-batch/v1':continue
        for entry in source['entries']:
            request=entry['request']
            if entry['kind']!='critique' or request['operation_type']!='capture-critique':continue
            for name in ('private_original','private_identity','private_label'):
                if request['payload'].get(name):protected.add(request['payload'][name])
    protected={unicodedata.normalize('NFC',literal).casefold() for literal in protected}
    def inspect(item):
        if type(item) is str and any(literal in unicodedata.normalize('NFC',item).casefold() for literal in protected):
            raise ContractError('Selected content contains a known private source/path literal; edit or omit it before sharing.')
        if type(item) is dict:
            for key, child in item.items(): inspect(key); inspect(child)
        elif type(item) is list:
            for child in item: inspect(child)
    inspect(value)


def verify_share(project, raw):
    try:
        value = decode(raw, purpose='project')
        if type(value) is not dict or value.get('schema') not in (SCHEMA,'claimbranch.canonical-share/v2') or value.get('policy') != POLICY:
            raise ContractError('Unsupported sharing policy.')
        expected = prepare_share(project, value['selection'], public_selection=True)
        if not hmac.compare_digest(raw, expected): raise ContractError('Shared bytes or saved private revision differ.')
    except (KeyError, TypeError, ValueError, ContractError):
        raise ContractError('Export does not match this saved private revision and exact selection/policy; no file changed.') from None
    return True


def _parent(path, *, forbidden_identity=None):
    if '..' in Path(path).parts: raise ContractError('Parent traversal is not a sharing destination.')
    path = Path(os.path.abspath(path))
    if path.name in ('', '.', '..'): raise ContractError('Choose a new regular sharing file.')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = next_fd
            info=os.fstat(fd)
            if forbidden_identity == (info.st_dev,info.st_ino): raise ContractError('Keep sharing files outside the live private work directory.')
        return path, fd
    except OSError:
        os.close(fd)
        raise ContractError('Sharing paths need existing real directories without symlinks; on Mac use /private/tmp rather than /tmp.') from None
    except BaseException:
        os.close(fd); raise


def read_file(path):
    path, parent = _parent(path)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > PROJECT_BYTES: raise ContractError('Bounded regular JSON file required.')
        chunks = []
        size = 0
        while True:
            chunk = os.read(fd, min(65536, PROJECT_BYTES+1-size))
            if not chunk: break
            chunks.append(chunk); size += len(chunk)
            if size > PROJECT_BYTES: raise ContractError('Sharing file byte budget exceeded.')
        after=os.fstat(fd)
        if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) != (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns): raise ContractError('Input changed during reading.')
        return b''.join(chunks)
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def write_share(path, raw, *, recheck, expected_parent=None, forbidden_identity=None):
    """Create-only same-directory publication; never overwrite an edited export."""
    path, parent = _parent(path,forbidden_identity=forbidden_identity)
    if expected_parent is not None and (os.fstat(parent).st_dev, os.fstat(parent).st_ino) != expected_parent:
        os.close(parent); raise ContractError('Sharing destination changed after preview; no file created.')
    temporary = '.claimbranch-share-' + secrets.token_hex(16)
    fd = None
    published = False
    try:
        try: os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise ContractError('Destination already exists; choose a new file. Existing content was retained.')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0: raise OSError('Sharing write did not progress.')
            offset += written
        os.fsync(fd); os.close(fd); fd = None
        recheck()
        _, current_parent = _parent(path,forbidden_identity=forbidden_identity)
        try:
            a, b = os.fstat(parent), os.fstat(current_parent)
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino): raise ContractError('Sharing destination moved; preview again.')
        finally: os.close(current_parent)
        os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        published = True
        os.unlink(temporary, dir_fd=parent); os.fsync(parent)
    except BaseException as error:
        if published: raise ContractError('Sharing publication durability is uncertain; preserve the output and verify-export before retrying in a new file.') from error
        raise
    finally:
        if fd is not None: os.close(fd)
        active_error=sys.exception()
        try:
            try: os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError: pass
            except OSError:
                if active_error: active_error.add_note('Temporary sharing cleanup incomplete; preserve any output before retrying.')
        finally: os.close(parent)


def display_json(value, *, indent=None):
    """Complete semantic preview with invisible/control characters escaped."""
    text=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=indent,separators=(',',':') if indent is None else None)
    return ''.join(json.dumps(c,ensure_ascii=True)[1:-1] if unicodedata.category(c).startswith('C') and c not in '\n\t' else c for c in text)


def run_share_command(args):
    from .personal_project import PersonalProjectStore
    from .tui_model import clean
    with PersonalProjectStore(args.directory, project_id=getattr(args, 'project_id', None)) as store:
        project = store.load()
        if args.project_action == 'verify-export':
            verify_share(project, read_file(args.input)); store.verify_unchanged()
            print('Verified against this exact saved private revision and selection; no scientific validity or anonymity certified.')
            return 0
        if not args.selection or not args.output or args.archive_directory:
            raise ContractError('Canonical sharing requires --selection and --output, without --archive-directory.')
        work_info=os.stat(args.directory)
        work_identity=(work_info.st_dev,work_info.st_ino)
        output_path, output_parent = _parent(args.output,forbidden_identity=work_identity)
        try:
            parent_info = os.fstat(output_parent)
            parent_identity = (parent_info.st_dev, parent_info.st_ino)
            if output_path.is_relative_to(Path(args.directory).resolve()):
                raise ContractError('Keep selected sharing files outside the live private work directory.')
            try: os.stat(output_path.name, dir_fd=output_parent, follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise ContractError('Sharing output already exists; choose a new filename.')
        finally: os.close(output_parent)
        requested_raw = read_file(args.selection)
        requested = decode(requested_raw, purpose='project')
        raw = prepare_share(project, requested)
        # Complete exact canonical bytes, safely displayed in pages. Escaped JSON
        # characters, including controls, remain literal rather than terminal code.
        value = decode(raw, purpose='project')
        print('Create-only destination: '+display_json(str(output_path)))
        print('Selected: %s; required dependencies: %s; reasons: %s.' % (len(value['selection']['record_ids']), len(value['required_record_ids']), len(value['selection']['reason_ids'])))
        print('Review every selected/dependency field. Prose is not automatically anonymous. No commit, upload or provider request follows.')
        if args.dry_run:
            print(display_json(value)); return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty(): raise ContractError('Sharing needs an interactive terminal; --dry-run writes nothing.')
        lines = display_json(value, indent=2).splitlines()
        for start in range(0, len(lines), 60):
            print(clean('\n'.join(lines[start:start+60])), flush=True)
            if start+60 < len(lines) and input('Enter: next page / q: cancel: ').strip().lower() == 'q': return 0
        print('Exact canonical output: %s bytes; SHA-256 %s.' % (len(raw), hashlib.sha256(raw).hexdigest()))
        if input('Type export to create this selected sharing file, or Enter to cancel: ').strip() != 'export': return 0
        def recheck():
            store.verify_unchanged()
            if read_file(args.selection) != requested_raw or prepare_share(store.load(), requested) != raw:
                raise ContractError('Sharing source or selection changed; preview again.')
        write_share(args.output, raw, recheck=recheck, expected_parent=parent_identity, forbidden_identity=work_identity)
        print('Selected sharing file created. Private work and manuscript unchanged; Git publication is separate.')
    return 0


def share_schema(version=1):
    if version not in (1,2):raise ContractError('Unsupported sharing format')
    """Closed public field vocabulary; generated with the other owned schemas."""
    from claimbranch.core.research_schema import obj, array, nullable, TEXT, HASH, METRIC
    from claimbranch.core.typed_observations import VALUE
    public = {'type': 'string', 'pattern': '^record-[0-9a-f]{32}$', 'minLength': 39, 'maxLength': 39}
    ids = array(public, 2048, unique=True)
    integer = {'type': 'integer', 'minimum': 0, 'maximum': 2048}
    boolean = {'enum': [False, True]}
    origins = array({'enum': ['human', 'ai', 'mixed', 'unknown']}, 4, 1, True)
    common = dict(branch_ai_context_present=boolean, origins=origins, source_fidelity_verified={'const': False}, unresolved_source_fields={'type':'integer','minimum':0})
    tags = array(obj(condition_index=integer, value_index=integer, condition_label=TEXT, value_label=TEXT), 32)
    table = obj(id=public, estimand=TEXT, conditions=tags,
                columns=array(obj(index=integer, name=TEXT, type={'enum':['integer','decimal','text']}, raw_unit=TEXT, display_unit=TEXT),32,1),
                rows=array(obj(index=integer, conditions=tags, cells=array(obj(column_index=integer,value=VALUE),32,1)),256,1),
                condition_labels_omitted={'const':False}, artifact_fidelity_verified={'const':False})
    wording = obj(grade=TEXT, limitation=TEXT, allowed_wording=array(TEXT,16), required_caveats=array(TEXT,16), banned_phrases=array(TEXT,32), placement=array({'enum':['main','appendix','abstract']},3))
    basis = array(obj(observation_id=public, revision_number=integer, current_revision=boolean),256,1)
    def variant(kind, fields, optional=(), private=False):
        from itertools import combinations
        if version==2 and not private:
            fields={**fields,'title':{'type':'string','minLength':1,'maxLength':240,'pattern':r'^[^\r\n]+$'},'review_required':{'const':True}}
            optional=(*optional,'title','review_required')
        contents = []
        for count in range(len(optional)+1):
            for included in combinations(optional,count):
                content_fields = {k:v for k,v in fields.items() if k not in optional or k in included}
                content=obj(**({} if private else common),**content_fields)
                contents.append(content)
        result = obj(id=public, kind={'const':kind}, content={'oneOf':contents})
        if private: return result
        return {'oneOf':[result,obj(**result['properties'],reason=TEXT)]}
    variants = [
        variant('claim',dict(statement=TEXT,status={'enum':['proposed','supported','contested']},role={'enum':['thesis','main','subclaim']},scope=TEXT,parent_ids=ids,wording=wording,status_basis_ids=ids),('scope','wording','status_basis_ids')),
        variant('experiment',dict(question=TEXT,method=TEXT,conditions=TEXT,metric=METRIC)),
        variant('observation',dict(statement=TEXT,value=nullable(TEXT),status={'enum':['confirmed','corrected','invalidated','retracted']},experiment_id=public,revision_number=integer,measurement=table),('measurement',)),
        variant('interpretation',dict(statement=TEXT,observation_ids=ids,scope=TEXT),('scope',)),
        variant('scientific-edge',dict(source_id=public,target_id=public,edge_type={'enum':['supports','challenges','qualifies']})),
        variant('experiment-plan',dict(objective=TEXT,status={'const':'planned'},conditions=TEXT,claim_id=public,metric=METRIC)),
        variant('reporting-companion',dict(target_id=public,companion_id=public,scope={'enum':['anchor','paragraph']},status={'enum':['active','retired']})),
        variant('manuscript-anchor',dict(kind={'enum':['text','figure','table','caption']},expresses=ids,plots=ids,parents=ids,text={'const':'omitted'})),
        variant('co-report',dict(disposition={'const':'co-reported'},interpretation_ids=ids,companion_ids=ids,edge_ids=ids,reading_origins=array(obj(id=public,origins=origins),4),understanding_verified={'const':False})),
        variant('protocol',dict(prediction=TEXT,falsifier=TEXT,prewritten_wording=obj(pass_wording=TEXT,fail_wording=TEXT),inspected_before_registration={'enum':['seen','unseen','unknown']},plan_id=public,supersedes_id=nullable(public),committed_reference={'const':'omitted'},chronology_verified={'const':False},plan_changed_since_registration=boolean,gates=array(obj(id=public,name=TEXT,tolerance=TEXT,reference=TEXT),16))),
        variant('registered-gate',dict(protocol_id=public,name=TEXT,tolerance=TEXT,reference=TEXT)),
        variant('protocol-experiment',dict(protocol_id=public,experiment_id=public,metric_differs_from_registered_plan=boolean,preinspection_disclosure_conflict=boolean)),
        variant('gate-amendment',dict(protocol_id=public,gate_id=public,expected_rule_id=public,new_tolerance=TEXT,new_reference=TEXT,decided_after_result={'enum':['before','after','unknown']},app_result_precedes_amendment=boolean,chronology_conflict=boolean)),
        variant('gate-result',dict(association_id=public,gate_id=public,rule_id=public,status={'enum':['passed','failed','unknown']},observation_basis=basis)),
        variant('outcome',dict(association_id=public,classification={'enum':['consistent','not-consistent','inconclusive','stopped-at-gate']},discrimination={'enum':['discriminating','non-discriminating','unknown']},limitations=array(TEXT,16),gate_validity={'enum':['failed-gate','incomplete-gate-assessment','unknown-gate-result','reported-gates-passed','no-gates-declared']},validity_verified={'const':False},rule_ids=ids,gate_result_ids=ids,observation_basis=basis)),
        variant('private-critique',dict(content={'const':'omitted'},scientific={'const':False},resolved={'const':False}),private=True),
        variant('critique-reference',dict(source_id=public,target_id=public,relation={'enum':['questions','addressed-by']},scientific={'const':False},resolved={'const':False}),private=True)]
    result = obj(schema={'const':'claimbranch.canonical-share/v'+str(version)},policy={'const':POLICY},selection=obj(schema={'const':SELECTION_SCHEMA},record_ids=ids,reason_ids=ids),required_record_ids=ids,
                 records=array({'oneOf':variants},2048,1),omissions={'const':OMISSIONS},anonymity_verified={'const':False},
                 authority={'const':'read-only personal projection; not a backup or scientific verification'},private_revision_commitment=HASH)
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:claimbranch:canonical-share:v'+str(version),**result}
