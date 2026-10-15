"""Read-only paper association and encrypted unaccepted project work.

Association records file identity, not scientific fidelity or write authority.
No source is imported into evidence, no manuscript is changed, and unavailable
sources never prevent reading the retained work. Paths are encoded as exact
filesystem bytes so canonical Unicode normalization cannot redirect them.
"""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass
from functools import cached_property
import hashlib
import os
from pathlib import Path
import stat
import subprocess

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.marked_text import preview_marked_text
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, ID, array, normalize, obj
from .device_work_store import DevicePaperWorkStore
from .paper_work_store import PaperWork, PaperWorkStore, WORK, WORK_V2, WORK_V3, WORK_V4, WORK_V5, WORK_V6, WORK_V7, WORK_V8, WORK_V9, WORK_V10, WORK_V11, WORK_V12, WORK_V13


HEX_PATH = {'type': 'string', 'minLength': 2, 'maxLength': 8192, 'pattern': '^(?:[0-9a-f]{2})+$'}
NUMBER = {'type': 'string', 'minLength': 1, 'maxLength': 24, 'pattern': '^(0|[1-9][0-9]*)$'}
ASSOCIATION_LIMIT = 16
IDENTITY = obj(device=NUMBER, inode=NUMBER)
from claimbranch.core.research_schema import MANUSCRIPT_SOURCE as SOURCE

PROJECT = obj(schema={'const': 'claimbranch.project-work/v1'}, project_id=ID,
              associations=array(SOURCE, ASSOCIATION_LIMIT, 1), work={'oneOf': [WORK, WORK_V2, WORK_V3, WORK_V4, WORK_V5, WORK_V6]},
              authority={'const': 'unaccepted-work'}, authorization_verified={'const': False})
TRANSITION = obj(kind={'enum': ['relocation', 'source-refresh']}, before=HASH, after=HASH)
PROJECT_V2 = obj(**{**PROJECT['properties'], 'schema': {'const': 'claimbranch.project-work/v2'},
                    'transitions': array(TRANSITION, 15)})
PROJECT_V3 = deepcopy(PROJECT_V2)
PROJECT_V3['properties']['schema'] = {'const': 'claimbranch.project-work/v3'}
PROJECT_V3['properties']['work'] = WORK_V7
PROJECT_V4 = deepcopy(PROJECT_V3)
PROJECT_V4['properties']['schema'] = {'const': 'claimbranch.project-work/v4'}
PROJECT_V4['properties']['work'] = WORK_V8
PROJECT_V5 = deepcopy(PROJECT_V4)
PROJECT_V5['properties']['schema'] = {'const':'claimbranch.project-work/v5'}
PROJECT_V5['properties']['work'] = WORK_V9
PROJECT_V6 = deepcopy(PROJECT_V5)
PROJECT_V6['properties']['schema'] = {'const':'claimbranch.project-work/v6'}
PROJECT_V6['properties']['work'] = WORK_V10
PROJECT_V7 = deepcopy(PROJECT_V6)
PROJECT_V7['properties']['schema'] = {'const':'claimbranch.project-work/v7'}
PROJECT_V7['properties']['work'] = WORK_V11
PROJECT_V8 = deepcopy(PROJECT_V7)
PROJECT_V8['properties']['schema'] = {'const':'claimbranch.project-work/v8'}
PROJECT_V8['properties']['work'] = WORK_V12
PROJECT_V9 = deepcopy(PROJECT_V8)
PROJECT_V9['properties']['schema'] = {'const':'claimbranch.project-work/v9'}
PROJECT_V9['properties']['work'] = WORK_V13
PROJECT_V10 = deepcopy(PROJECT_V9)
from .paper_work_store import WORK_V14
PROJECT_V10['properties']['schema'] = {'const':'claimbranch.project-work/v10'}
PROJECT_V10['properties']['work'] = WORK_V14
from claimbranch.core.research_schema import TEXT
PROJECT_V10['properties']['sources'] = array(obj(sha256=HASH, bytes={'type':'integer','minimum':0,'maximum':4194304}, chunks=array({'type':'string','minLength':1,'maxLength':16384,'x-utf8-maxBytes':16384,'pattern':'^[A-Za-z0-9+/]+={0,2}$'},342)),1024)
PROJECT_V10['properties']['public_ids'] = array(obj(private_id=ID,public_id={'type':'string','minLength':39,'maxLength':39,'pattern':'^record-[0-9a-f]{32}$'}),2048)
PROJECT_V10['required'] += ['sources','public_ids']

PROJECT_V11 = deepcopy(PROJECT_V10)
from .paper_work_store import WORK_V15
from claimbranch.core.argument_import import import_schema
PROJECT_V11['properties']['schema'] = {'const':'claimbranch.project-work/v11'}
PROJECT_V11['properties']['work'] = WORK_V15
PROJECT_V11['properties']['import_input_sha256'] = HASH
PROJECT_V11['required'].append('import_input_sha256')

from .paper_work_store import WORK_V16
from claimbranch.core.research_schema import nullable
PROJECT_V12 = deepcopy(PROJECT_V11)
PROJECT_V12['properties']['schema']={'const':'claimbranch.project-work/v12'}
PROJECT_V12['properties']['work']=WORK_V16
PROJECT_V12['properties']['import_input_sha256']=nullable(HASH)

from .paper_work_store import WORK_V17
PROJECT_V13 = deepcopy(PROJECT_V12)
PROJECT_V13['properties']['schema']={'const':'claimbranch.project-work/v13'}
PROJECT_V13['properties']['work']=WORK_V17

from .paper_work_store import WORK_V18
PROJECT_V14=deepcopy(PROJECT_V13)
PROJECT_V14['properties']['schema']={'const':'claimbranch.project-work/v14'}
PROJECT_V14['properties']['work']=WORK_V18

from .paper_work_store import WORK_V19
PROJECT_V15=deepcopy(PROJECT_V14)
PROJECT_V15['properties']['schema']={'const':'claimbranch.project-work/v15'}
PROJECT_V15['properties']['work']=WORK_V19

from .paper_work_store import WORK_V20
PROJECT_V16=deepcopy(PROJECT_V15)
PROJECT_V16['properties']['schema']={'const':'claimbranch.project-work/v16'}
PROJECT_V16['properties']['work']=WORK_V20

from .paper_work_store import WORK_V21
from claimbranch.core.critiques import SOURCE_ID
PROJECT_V17=deepcopy(PROJECT_V16)
PROJECT_V17['properties']['schema']={'const':'claimbranch.project-work/v17'}
PROJECT_V17['properties']['work']=WORK_V21
PROJECT_V17['properties']['critique_sources']=array(obj(id=SOURCE_ID,source=PROJECT_V10['properties']['sources']['items']),128)
PROJECT_V17['required'].append('critique_sources')

from .paper_work_store import WORK_V22
PROJECT_V18=deepcopy(PROJECT_V17)
PROJECT_V18['properties']['schema']={'const':'claimbranch.project-work/v18'}
PROJECT_V18['properties']['work']=WORK_V22

from .paper_work_store import WORK_V23
PROJECT_V19=deepcopy(PROJECT_V18)
PROJECT_V19['properties']['schema']={'const':'claimbranch.project-work/v19'}
PROJECT_V19['properties']['work']=WORK_V23

from .paper_storage_codec import encode as canonical_bytes, decode, normalize

PREVIEW = obj(schema={'const': 'claimbranch.project-association-preview/v1'}, source=SOURCE,
              workspace=HEX_PATH, workspace_identity=IDENTITY)
REFRESH = obj(schema={'const': 'claimbranch.source-refresh-review/v1'}, project_digest=HASH,
              before=SOURCE, preview=PREVIEW)


def project_work_schema(version=1):
    if type(version) is not int or version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19):
        raise ContractError('unsupported project work schema version')
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': f'urn:claimbranch:project-work:v{version}',
            '$comment': 'Generated by scripts/export_research_schema.py. Runtime additionally checks '
                        + ('canonical bytes, '+('16 MiB' if version in (10,11,12,13,14,15,16,17,18,19) else '256 KiB')+' aggregate size, exact paths, source/project/anchor ')
                        + 'bindings and retained work replay. No accepted or resumed authority.',
            **deepcopy({1: PROJECT, 2: PROJECT_V2, 3: PROJECT_V3, 4: PROJECT_V4, 5: PROJECT_V5, 6: PROJECT_V6, 7: PROJECT_V7, 8: PROJECT_V8, 9: PROJECT_V9, 10: PROJECT_V10, 11:PROJECT_V11,12:PROJECT_V12,13:PROJECT_V13,14:PROJECT_V14,15:PROJECT_V15,16:PROJECT_V16,17:PROJECT_V17,18:PROJECT_V18,19:PROJECT_V19}[version])}


def _identity(info):
    return {'device': str(info.st_dev), 'inode': str(info.st_ino)}


def _path(encoded, *, relative=False):
    try:
        raw = bytes.fromhex(encoded)
        value = os.fsdecode(raw)
        path = Path(value)
        if (not raw or b'\0' in raw or b'\n' in raw or b'\r' in raw
                or os.fsencode(path) != raw):
            raise ValueError()
        if relative:
            if (path.is_absolute() or '..' in path.parts
                    or '.git' in (part.casefold() for part in path.parts) or path.suffix != '.tex'):
                raise ValueError()
        elif not path.is_absolute() or '..' in path.parts:
            raise ValueError()
        return path
    except (TypeError, ValueError, UnicodeError):
        raise ContractError('unsupported exact project path') from None


def _encoded(path):
    value = os.fsencode(path).hex()
    _path(value, relative=not Path(path).is_absolute())
    return value


def _git_directory(root):
    # rev-parse neither invokes hooks nor examines source through filters.
    # Discard ambient GIT_DIR/WORK_TREE/config injection, optional Git locks.
    environment = {'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_OPTIONAL_LOCKS': '0'}
    try:
        result = subprocess.run(['/usr/bin/git', '-C', str(root), 'rev-parse',
                                 '--show-toplevel', '--absolute-git-dir', '--git-common-dir'],
                                env=environment, capture_output=True, timeout=10, check=True)
        paths = result.stdout.splitlines()
        if len(paths) != 3 or len(result.stdout) > 12288:
            raise ValueError()
        top, git_dir, common = ((root / os.fsdecode(item)).resolve(strict=True) for item in paths)
        if top != root:
            raise ValueError()
        return git_dir, common
    except (OSError, subprocess.SubprocessError, ValueError):
        raise ContractError('selected paper must be an available Git working-tree root') from None


def _source(root, manuscript, anchor_id, *, maximum=65536):
    """Bounded descriptor-relative read; no final/intermediate manuscript links."""
    try:
        root = Path(root).resolve(strict=True)
        relative = _path(_encoded(manuscript), relative=True)
        git_dir, common = _git_directory(root)
        root_identity, git_identity = _identity(root.stat()), _identity(git_dir.stat())
        common_identity = _identity(common.stat())
        with ExitStack() as stack:
            def opened(path, *, parent=None, directory=False):
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if directory:
                    flags |= os.O_DIRECTORY
                fd = os.open(path, flags, dir_fd=parent)
                stack.callback(os.close, fd)
                return fd
            root_fd = opened(root, directory=True)
            if _identity(os.fstat(root_fd)) != root_identity:
                raise ContractError('paper root changed during preview')
            parent, entries = root_fd, []
            for component in relative.parts[:-1]:
                child = opened(component, parent=parent, directory=True)
                try:
                    os.stat('.git', dir_fd=child, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise ContractError('manuscript cannot cross into a nested Git working tree')
                entries.append((parent, component, child))
                parent = child
            fd = opened(relative.name, parent=parent)
            entries.append((parent, relative.name, fd))
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
                raise ContractError('manuscript must be a single-link bounded regular file')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                raw = stream.read(maximum+1)
            after = os.fstat(fd)
            stamp = lambda info: (_identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if len(raw) > maximum or stamp(before) != stamp(after):
                raise ContractError('manuscript changed during preview')
            raw.decode('utf-8')
            source_digest = hashlib.sha256(raw).hexdigest()
            if maximum == 65536: preview_marked_text(raw, anchor_id, 'marker validation', source_digest)
            else:
                from claimbranch.core.marked_text import marked_block
                marked_block(raw,anchor_id)
            for owner, name, held in entries:
                current = os.stat(name, dir_fd=owner, follow_symlinks=False)
                if _identity(current) != _identity(os.fstat(held)) or stat.S_ISLNK(current.st_mode):
                    raise ContractError('manuscript path changed during preview')
            if (_identity(root.stat()) != root_identity or _git_directory(root) != (git_dir, common)
                    or _identity(git_dir.stat()) != git_identity or _identity(common.stat()) != common_identity):
                raise ContractError('paper association changed during preview')
        return {'root': _encoded(root), 'root_identity': root_identity,
                'git_dir': _encoded(git_dir), 'git_identity': git_identity,
                'git_common_dir': _encoded(common), 'git_common_identity': common_identity,
                'manuscript': _encoded(relative), 'anchor_id': anchor_id,
                'file_identity': _identity(after), 'size': str(after.st_size),
                'mtime_ns': str(after.st_mtime_ns), 'ctime_ns': str(after.st_ctime_ns),
                'source_digest': source_digest}
    except (OSError, ValueError, UnicodeError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError('paper source unavailable or unsupported; retained work is unchanged') from None


def _workspace(directory):
    # Reuse exactly the store's private-directory/placement check without its
    # mutating session entry (no lock, staging cleanup, cipher or key creation).
    probe = object.__new__(PaperWorkStore)
    probe._path, probe._dir, probe._lock = Path(directory), None, None
    probe._reopen_error = None
    try:
        if probe._path.is_symlink():
            raise ContractError('workspace cannot be a symbolic link')
        probe._path = probe._path.resolve(strict=True)
        probe._dir = os.open(probe._path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        probe._check_directory()
        return _encoded(probe._path), _identity(os.fstat(probe._dir))
    except OSError:
        raise ContractError('existing private external workspace required') from None
    finally:
        if probe._dir is not None:
            os.close(probe._dir)


@dataclass(frozen=True)
class AssociationPreview:
    payload: bytes

    def __post_init__(self):
        value = normalize(decode(self.payload), PREVIEW)
        if canonical_bytes(value) != self.payload:
            raise ContractError('canonical association preview required')
        _validate_source(value['source'])
        _path(value['workspace'])

    def display(self):
        value = self.recheck()
        source = value['source']
        return {'paper_root': str(_path(source['root'])),
                'manuscript': str(_path(source['manuscript'], relative=True)),
                'workspace': str(_path(value['workspace'])),
                'anchor_id': source['anchor_id'], 'source_digest': source['source_digest'],
                'git_root_verified': True, 'source_fidelity_verified': False,
                'authorization_verified': False, 'writes': []}

    def recheck(self):
        value = decode(self.payload)
        source = value['source']
        current = preview_association(_path(source['root']), _path(source['manuscript'], relative=True),
                                      source['anchor_id'], _path(value['workspace']))
        if current.payload != self.payload:
            raise ContractError('association preview changed; preview again before continuing')
        return value


def _validate_source(source):
    _path(source['root'])
    _path(source['git_dir'])
    _path(source['git_common_dir'])
    _path(source['manuscript'], relative=True)


def preview_association(paper_root, manuscript, anchor_id, workspace):
    source = _source(paper_root, manuscript, anchor_id)
    directory, identity = _workspace(workspace)
    if any(_path(directory).is_relative_to(_path(source[key]))
           for key in ('root', 'git_dir', 'git_common_dir')):
        raise ContractError('workspace must be outside paper and Git administration directories')
    return AssociationPreview(canonical_bytes({'schema': 'claimbranch.project-association-preview/v1',
        'source': source, 'workspace': directory, 'workspace_identity': identity}))


def _scientific_ids(history):
    ids = {decode(history.seed)['claim_id'], decode(history.seed)['anchor_id']}
    for ref, _ in history.heads:
        view = history.view(ref)
        ids.update(x['id'] for x in view['evidence'])
        ids.update(x['id'] for x in view['experiments'])
        ids.update(x['id'] for x in view['changes'])
        ids.update(view.get('manuscript_anchors',{}))
        ids.update(view.get('companion_dependencies',{}))
        ids.update(view.get('co_reports',{}))
        ids.update(view.get('critiques',{}));ids.update(view.get('critique_links',{}))
        for name in ('protocols','experiment_associations','gate_amendments','gate_results','outcome_assessments'):ids.update(view.get(name,{}))
        for protocol in view.get('protocols',{}).values():ids.update(g['id'] for g in protocol['gates'])
        ids.update(e['measurement']['id'] for o in view['evidence'] for e in o['history'] if 'measurement' in e)
    return ids


def _public_ids(history, retained):
    import secrets
    result = list(retained)
    known = {x['private_id'] for x in retained}
    for key in sorted(_scientific_ids(history)-known):
        result.append({'private_id':key,'public_id':'record-'+secrets.token_hex(16)})
    if len(result)>2048:
        raise ContractError('capacity public-identities: %s / 2048' % len(result))
    return sorted(result,key=lambda x:x['private_id'])


@dataclass(frozen=True)
class ProjectWork:
    payload: bytes

    def __post_init__(self):
        value = normalize(decode(self.payload), {'oneOf': [PROJECT, PROJECT_V2, PROJECT_V3, PROJECT_V4, PROJECT_V5, PROJECT_V6, PROJECT_V7, PROJECT_V8, PROJECT_V9, PROJECT_V10, PROJECT_V11, PROJECT_V12, PROJECT_V13, PROJECT_V14, PROJECT_V15, PROJECT_V16, PROJECT_V17, PROJECT_V18, PROJECT_V19]})
        if canonical_bytes(value) != self.payload:
            raise ContractError('canonical project work required')
        work = self.work
        if work.history.has_critiques or 'critique_sources' in value:
            from .critiques import validate_private_sources
            validate_private_sources(work.history,value.get('critique_sources',[]))
        seed = decode(work.history.seed)
        if work.project_id != value['project_id']:
            raise ContractError('project work belongs to another project')
        for source in value['associations']:
            _validate_source(source)
            if source['anchor_id'] != seed['anchor_id']:
                raise ContractError('paper association belongs to another anchor')
        _transitions(value)
        if work.history.schema_version in (4, 5):
            from claimbranch.core.paper_capacity import source_bytes
            for source in value['sources']: source_bytes(source)
            if len({s['sha256'] for s in value['sources']}) != len(value['sources']):
                raise ContractError('duplicate retained source')
            if work.history.schema_version == 5:
                from claimbranch.core.argument_import import history_from_import
                match = [item for item in value['sources'] if item['sha256'] == value['import_input_sha256']]
                if len(match) != 1: raise ContractError('imported work lost its exact input source')
                initial = seed['initial_argument']
                expected = history_from_import(source_bytes(match[0]), anchor_id=seed['anchor_id'], registered_at=initial['registered_at'])
                if expected.seed != work.history.seed:
                    raise ContractError('imported argument does not match its retained source and selection')
            if work.history.has_manuscript_anchors:
                from claimbranch.core.paper_capacity import decode as paper_decode
                roots={item['root'] for item in value['associations']}
                for command in work.history.commands:
                    cmd=paper_decode(command,purpose='history')
                    if cmd['operation_type']=='register-manuscript-anchor':
                        source=cmd['payload']['source']; _validate_source(source)
                        if source['root'] not in roots: raise ContractError('anchor source is outside associated paper roots')
            mappings = value['public_ids']
            if len({m['private_id'] for m in mappings})!=len(mappings) or len({m['public_id'] for m in mappings})!=len(mappings):
                raise ContractError('duplicate public identity mapping')
            if not _scientific_ids(work.history) <= {m['private_id'] for m in mappings}:
                raise ContractError('saved revision is missing scientific public identity mappings')

    @classmethod
    def create(cls, work, preview, *, import_input=None):
        if type(work) is not PaperWork or type(preview) is not AssociationPreview:
            raise ContractError('typed work and association preview required')
        value = preview.recheck()
        if work.history.schema_version == 5:
            from claimbranch.core.paper_capacity import source_record
            retained_import = source_record(import_input)
        retained = decode(work.payload)
        pooled = retained['schema'] in ('claimbranch.paper-work/v7', 'claimbranch.paper-work/v8', 'claimbranch.paper-work/v9', 'claimbranch.paper-work/v10', 'claimbranch.paper-work/v11', 'claimbranch.paper-work/v12', 'claimbranch.paper-work/v13', 'claimbranch.paper-work/v14', 'claimbranch.paper-work/v15', 'claimbranch.paper-work/v16', 'claimbranch.paper-work/v17','claimbranch.paper-work/v18','claimbranch.paper-work/v19','claimbranch.paper-work/v20','claimbranch.paper-work/v21','claimbranch.paper-work/v22','claimbranch.paper-work/v23')
        return cls(canonical_bytes({'schema': ('claimbranch.project-work/v'+str(int(retained['schema'].rsplit('/v',1)[1])-4)) if pooled else 'claimbranch.project-work/v1',
            **({'transitions': []} if pooled else {}),
            **({'sources':([retained_import] if work.history.schema_version==5 else []), 'public_ids':_public_ids(work.history,[])} if work.history.schema_version in (4, 5) else {}),
            **({'import_input_sha256':hashlib.sha256(import_input).hexdigest()} if work.history.schema_version==5 else {'import_input_sha256':None} if work.history.has_manuscript_anchors or work.history.has_wording_policies or work.history.has_co_reports or work.history.has_measurements or work.history.has_protocols or work.history.has_critiques or work.history.has_graph_edits else {}), 'project_id': work.project_id,
            'associations': [value['source']], 'work': retained,
            **({'critique_sources':[]} if work.history.has_critiques or (work.history.has_metadata_origins or work.history.has_graph_edits) else {}),
            'authority': 'unaccepted-work', 'authorization_verified': False}))

    @cached_property
    def work(self):
        return PaperWork(canonical_bytes(decode(self.payload)['work']))

    @property
    def project_id(self):
        return decode(self.payload)['project_id']

    def with_work(self, work, *, critique_source=None):
        _check_history_extension(self.work, work)
        value = decode(self.payload)
        value['work'] = decode(work.payload)
        if (work.history.has_metadata_origins or work.history.has_graph_edits):value.setdefault('critique_sources',[])
        if work.history.has_critiques:
            value.setdefault('critique_sources',[])
            if critique_source is not None:value['critique_sources'].append(critique_source)
        elif critique_source is not None:raise ContractError('Private critique source requires its exact recorded question')
        if work.history.schema_version in (4, 5):
            value['public_ids'] = _public_ids(work.history,value.get('public_ids',[]))
        if value['work']['schema'] in ('claimbranch.paper-work/v7', 'claimbranch.paper-work/v8', 'claimbranch.paper-work/v9', 'claimbranch.paper-work/v10', 'claimbranch.paper-work/v11', 'claimbranch.paper-work/v12', 'claimbranch.paper-work/v13', 'claimbranch.paper-work/v14', 'claimbranch.paper-work/v15', 'claimbranch.paper-work/v16', 'claimbranch.paper-work/v17','claimbranch.paper-work/v18','claimbranch.paper-work/v19','claimbranch.paper-work/v20','claimbranch.paper-work/v21','claimbranch.paper-work/v22','claimbranch.paper-work/v23'):
            value['transitions'] = _transitions(value)
            value['schema'] = 'claimbranch.project-work/v'+str(int(value['work']['schema'].rsplit('/v',1)[1])-4)
            if value['schema'] in ('claimbranch.project-work/v12','claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18','claimbranch.project-work/v19'): value.setdefault('import_input_sha256',None)
        return ProjectWork(canonical_bytes(value))

    def relocate(self, preview):
        if type(preview) is not AssociationPreview:
            raise ContractError('typed relocation preview required')
        _association_capacity(self)
        source = preview.recheck()['source']
        value = decode(self.payload)
        before = value['associations'][-1]
        if source['source_digest'] != before['source_digest']:
            raise ContractError('relocation must retain exact manuscript bytes')
        if _same_association(source, value['associations'][-1]):
            raise ContractError('association is already current')
        value['associations'].append(source)
        if 'transitions' in value:
            value['transitions'].append(_transition('relocation', before, source))
        return ProjectWork(canonical_bytes(value))

    def refresh_source(self, review):
        if type(review) is not SourceRefreshReview:
            raise ContractError('typed source refresh review required')
        _association_capacity(self)
        preview = review.recheck(self)
        value = decode(self.payload)
        transitions = _transitions(value)
        before = value['associations'][-1]
        value['schema'] = value['schema'] if value['schema'] in ('claimbranch.project-work/v3', 'claimbranch.project-work/v4', 'claimbranch.project-work/v5', 'claimbranch.project-work/v6', 'claimbranch.project-work/v7', 'claimbranch.project-work/v8', 'claimbranch.project-work/v9', 'claimbranch.project-work/v10', 'claimbranch.project-work/v11', 'claimbranch.project-work/v12', 'claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18','claimbranch.project-work/v19') else 'claimbranch.project-work/v2'
        value['associations'].append(preview['source'])
        value['transitions'] = transitions + [_transition('source-refresh', before, preview['source'])]
        # Nested writing/reviews retain their exact original context. A refreshed
        # file association is not scientific reconciliation or renewed consent.
        return ProjectWork(canonical_bytes(value))

    def source_status(self):
        value = decode(self.payload)
        source = value['associations'][-1]
        refreshed = any(event['kind'] == 'source-refresh' for event in value.get('transitions', ()))
        try:
            current = _source(_path(source['root']), _path(source['manuscript'], relative=True), source['anchor_id'])
        except ContractError:
            return 'unavailable-or-unsupported'
        if current == source:
            return 'unchanged-since-refresh' if refreshed else 'unchanged'
        if current['source_digest'] != source['source_digest']:
            return 'source-changed-reconciliation-required'
        if _same_association(current, source):
            return 'unchanged-content-since-refresh' if refreshed else 'unchanged-content'
        return 'relocation-required'

    def source_location(self):
        """Retained exact paths, not a fresh source check or a writing grant."""
        source = decode(self.payload)['associations'][-1]
        return {'paper_root': _path(source['root']),
                'manuscript': _path(source['manuscript'], relative=True),
                'anchor_id': source['anchor_id'], 'source_digest': source['source_digest']}


def initialize_project(preview, *, project_id, title, thesis_id, thesis):
    if type(preview) is not AssociationPreview:
        raise ContractError('typed association preview required')
    anchor = decode(preview.payload)['source']['anchor_id']
    history = ResearchHistory.start_paper_series(project_id, title, thesis_id, thesis, anchor)
    return ProjectWork.create(PaperWork.create(history), preview)


@dataclass(frozen=True)
class SourceRefreshReview:
    """Transient exact old-project/new-source comparison, not an authorization."""
    payload: bytes

    def __post_init__(self):
        value = normalize(decode(self.payload), REFRESH)
        if canonical_bytes(value) != self.payload:
            raise ContractError('canonical source refresh review required')
        _validate_source(value['before'])
        AssociationPreview(canonical_bytes(value['preview']))
        _check_refresh(value['before'], value['preview']['source'])

    def recheck(self, project):
        if type(project) is not ProjectWork:
            raise ContractError('typed project work required')
        value = decode(self.payload)
        if (hashlib.sha256(project.payload).hexdigest() != value['project_digest']
                or decode(project.payload)['associations'][-1] != value['before']):
            raise ContractError('saved work changed; review source refresh again')
        return AssociationPreview(canonical_bytes(value['preview'])).recheck()

    def display(self, project):
        preview = self.recheck(project)
        before, after = decode(self.payload)['before'], preview['source']
        return {'paper_root': str(_path(after['root'])),
                'manuscript': str(_path(after['manuscript'], relative=True)),
                'workspace': str(_path(preview['workspace'])), 'anchor_id': after['anchor_id'],
                'before_source_digest': before['source_digest'],
                'after_source_digest': after['source_digest'],
                'current_work_schema': decode(project.payload)['schema'],
                'result_work_schema': (decode(project.payload)['schema'] if decode(project.payload)['schema'] in ('claimbranch.project-work/v3', 'claimbranch.project-work/v4', 'claimbranch.project-work/v5', 'claimbranch.project-work/v6', 'claimbranch.project-work/v7', 'claimbranch.project-work/v8', 'claimbranch.project-work/v9', 'claimbranch.project-work/v10', 'claimbranch.project-work/v11', 'claimbranch.project-work/v12', 'claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18','claimbranch.project-work/v19') else 'claimbranch.project-work/v2'),
                'v1_readers_can_open_result': False,
                'remaining_source_snapshots': ASSOCIATION_LIMIT - len(decode(project.payload)['associations']) - 1,
                'writing_preserved': True, 'source_fidelity_verified': False,
                'scientific_reconciliation_verified': False, 'authorization_verified': False,
                'writes': []}


def preview_source_refresh(project, preview):
    if type(project) is not ProjectWork or type(preview) is not AssociationPreview:
        raise ContractError('typed project work and association preview required')
    _association_capacity(project)
    before = decode(project.payload)['associations'][-1]
    return SourceRefreshReview(canonical_bytes({'schema': 'claimbranch.source-refresh-review/v1',
        'project_digest': hashlib.sha256(project.payload).hexdigest(), 'before': before,
        'preview': preview.recheck()}))


def _transition(kind, before, after):
    return {'kind': kind, 'before': digest(before), 'after': digest(after)}


def _association_capacity(project):
    if len(decode(project.payload)['associations']) >= ASSOCIATION_LIMIT:
        raise ContractError('association history is full; retained work remains readable; no rollover is available')


def _check_refresh(before, after):
    location = ('root', 'root_identity', 'git_dir', 'git_identity', 'git_common_dir',
                'git_common_identity', 'manuscript', 'anchor_id')
    if any(before[key] != after[key] for key in location):
        raise ContractError('source refresh requires the same paper, manuscript and anchor; moved-and-edited sources are unsupported')
    if before['source_digest'] == after['source_digest']:
        raise ContractError('source bytes are already current')


def _transitions(value):
    sources = value['associations']
    pairs = list(zip(sources, sources[1:]))
    if value['schema'] == 'claimbranch.project-work/v1':
        if len({item['source_digest'] for item in sources}) != 1:
            raise ContractError('relocation must retain exact manuscript bytes')
        return [_transition('relocation', before, after) for before, after in pairs]
    events = value['transitions']
    if len(events) != len(pairs):
        raise ContractError('one transition per association change required')
    for event, (before, after) in zip(events, pairs):
        if event != _transition(event['kind'], before, after):
            raise ContractError('source transition does not match its exact associations')
        if event['kind'] == 'source-refresh':
            _check_refresh(before, after)
        elif before['source_digest'] != after['source_digest']:
            raise ContractError('relocation must retain exact manuscript bytes')
        elif _same_association(before, after):
            raise ContractError('relocation must change the paper association')
    return events


class ProjectAssociationStore:
    """Typed association/history guards shared by distinct physical stores."""
    work_type = ProjectWork

    def load(self):
        result = super().load()
        self._project_work = result
        return result

    def save(self, work, *, preview=None, source_review=None):
        if type(work) is not ProjectWork:
            raise ContractError('typed project work required')
        if self._loaded:
            self.verify_unchanged()
            previous = self._project_work
        else:
            previous = self.load()
        after = decode(work.payload)
        if previous is not None and previous.work.history.schema_version in (4, 5):
            before_value = decode(previous.payload)
            if after.get('sources',[])[:len(before_value['sources'])] != before_value['sources']:
                raise ContractError('retained source cannot be erased or rewritten')
            later_ids = {m['private_id']:m['public_id'] for m in after.get('public_ids',[])}
            if any(later_ids.get(m['private_id'])!=m['public_id'] for m in before_value['public_ids']):
                raise ContractError('public identity mappings cannot be erased or rebound')
        association_changed = previous is None
        if previous is None and (len(after['associations']) != 1 or after.get('transitions')):
            raise ContractError('new work requires one checked association; use backup restore for prior history')
        if previous is not None:
            before = decode(previous.payload)
            prior_events, next_events = _transitions(before), _transitions(after)
            if (('transitions' in before and 'transitions' not in after)
                    or next_events[:len(prior_events)] != prior_events):
                raise ContractError('save cannot replace prior source transitions')
            _check_history_extension(previous.work, work.work)
            old_private=decode(previous.payload).get('critique_sources',[])
            if decode(work.payload).get('critique_sources',[])[:len(old_private)]!=old_private:raise ContractError('Retained private critique originals cannot be replaced or dropped')
            if after['associations'][:len(before['associations'])] != before['associations']:
                raise ContractError('save cannot replace project identity or prior associations')
            association_changed = after['associations'] != before['associations']
            if association_changed and len(after['associations']) != len(before['associations']) + 1:
                raise ContractError('one explicit association change per save required')
            refreshing = association_changed and next_events[-1]['kind'] == 'source-refresh'
            if refreshing:
                if (type(source_review) is not SourceRefreshReview or preview is not None
                        or previous.refresh_source(source_review).payload != work.payload):
                    raise ContractError('source refresh requires the exact prior work and reviewed source')
                preview = AssociationPreview(canonical_bytes(decode(source_review.payload)['preview']))
            elif source_review is not None or ('transitions' in after and 'transitions' not in before
                                              and after['schema'] not in ('claimbranch.project-work/v3', 'claimbranch.project-work/v4', 'claimbranch.project-work/v5', 'claimbranch.project-work/v6', 'claimbranch.project-work/v7', 'claimbranch.project-work/v8', 'claimbranch.project-work/v9', 'claimbranch.project-work/v10', 'claimbranch.project-work/v11', 'claimbranch.project-work/v12', 'claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18','claimbranch.project-work/v19')):
                raise ContractError('source review is only valid for an explicit refresh')
            elif association_changed and _same_association(before['associations'][-1], after['associations'][-1]):
                raise ContractError('relocation must change the paper association')
        elif source_review is not None:
            raise ContractError('source refresh requires existing saved work')
        if association_changed:
            if type(preview) is not AssociationPreview:
                raise ContractError('new or relocated association requires its current preview')
            value = preview.recheck()
            if (value['source'] != after['associations'][-1]
                    or value['workspace'] != _encoded(self._path)
                    or value['workspace_identity'] != _identity(os.fstat(self._dir))):
                raise ContractError('association preview targets a different source or workspace')
        super().save(work)
        self._project_work = work

    def _save_restored(self, work):
        # Recovery must retain readable work even without the original paper.
        # This private create-only path never verifies or changes association.
        if self.load() is not None:
            raise ContractError('restore requires an empty checkpoint destination')
        super().save(work)
        self._project_work = work


class ProjectWorkStore(ProjectAssociationStore, DevicePaperWorkStore):
    """Same atomic encrypted checkpoint, typed project envelope, no migration."""


def _check_history_extension(previous, current):
    if type(current) is not PaperWork:
        raise ContractError('typed paper work required')
    before, after = previous.history, current.history
    if before.seed != after.seed or after.commands[:len(before.commands)] != before.commands:
        raise ContractError('retained source history cannot be replaced or truncated')
    retained = (decode(previous.payload).get('workspace') or {}).get('proposals')
    proposed = (decode(current.payload).get('workspace') or {}).get('proposals')
    if retained is not None:
        if proposed is None or proposed['recorded'][:len(retained['recorded'])] != retained['recorded']:
            raise ContractError('Saved personal contribution history cannot be dropped or replaced')
        by_id = {entry['request_id']: entry for entry in proposed['attempts']}
        immutable = ('owner', 'source', 'request', 'draft_id', 'draft_revision', 'draft_fields',
                     'request_id', 'nonce', 'created_at', 'expires_at', 'destination', 'request_digest', 'context_digest')
        for entry in retained['attempts']:
            later = by_id.get(entry['request_id'])
            if (later is None or any(entry[k] != later[k] for k in immutable)
                    or entry.get('provider', {}).get('request') != later.get('provider', {}).get('request')
                    or entry.get('codex', {}).get('request') != later.get('codex', {}).get('request')
                    or entry.get('discussion') != later.get('discussion')
                    or entry.get('edit') != later.get('edit')):
                raise ContractError('Saved request origin cannot be dropped or replaced')
            if entry['trace_digest'] is not None and any(entry[k] != later[k] for k in
                    ('trace_digest', 'response_digest', 'normalized_digest', 'provider_disposition')):
                raise ContractError('Saved response trace cannot be rewritten')
            if entry.get('provider', {}).get('outcome') is not None and entry['provider']['outcome'] != later.get('provider', {}).get('outcome'):
                raise ContractError('Saved response trace cannot be rewritten')
            if entry.get('codex', {}).get('outcome') is not None and entry['codex']['outcome'] != later.get('codex', {}).get('outcome'):
                raise ContractError('Saved response trace cannot be rewritten')
            if entry['trace_digest'] is not None and entry['payload_availability'] != 'available' and later['payload_availability'] == 'available':
                raise ContractError('Unavailable historical payload cannot be resurrected')
            if entry['payload_availability'] == 'available' and later['payload_availability'] == 'not-retained':
                raise ContractError('Saved raw payload requires explicit erasure; it cannot be silently evicted for quota')
        workspace = decode(current.payload)['workspace']
        candidates = {tuple(e['owner']): {r['id'] for r in [*e['records'], *e['unfinished']]}
                      for e in workspace['authoring']['candidates']}
        origins = {tuple(e['owner']): {o['revisions'][-1]['amendment']['id']: o for o in e['lineages']}
                   for e in proposed['origins']}
        for entry in retained['origins']:
            owner = tuple(entry['owner'])
            for origin in entry['lineages']:
                key = origin['revisions'][-1]['amendment']['id']
                if key in candidates.get(owner, set()):
                    later = origins.get(owner, {}).get(key)
                    if later is None or later['revisions'][:len(origin['revisions'])] != origin['revisions']:
                        raise ContractError('Kept or unfinished candidate origin cannot be dropped or truncated')
        causes = {digest(e['cause']) for e in proposed['explanations']}
        if any(digest(e['cause']) not in causes for e in retained['explanations']):
            raise ContractError('Earlier partial explanation context cannot be silently discarded')


def _same_association(left, right):
    # An editor may touch or atomically rewrite identical bytes. Such changes
    # are not paper relocations and must not consume the bounded move history.
    keys = ('root', 'root_identity', 'git_dir', 'git_identity', 'git_common_dir',
            'git_common_identity', 'manuscript', 'anchor_id', 'source_digest')
    return all(left[key] == right[key] for key in keys)
