"""Encrypted, unaccepted paper work checkpoints outside Git.

This is not the accepted operation log, a trusted backup, or key custody.
Imported candidate history stays unverified. Restore never installs a current
review seal, consumes consent, opens debt or writes a manuscript. TUI checkpoint
selection and editor integration remain with their separate adapter.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import cached_property
import hashlib
import errno
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from claimbranch.core.canonical import ContractError, MAX_BYTES, canonical_bytes, decode, identifier
from claimbranch.core.paper_changes import AmendmentLineage, lineage_schema
from claimbranch.core.paper_operation import REVIEW, PaperOperationReview
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import (CONTRIBUTION, ID, TEXT, PAPER_SERIES_SEED,
                                              array, command_schema, normalize, nullable, obj)
from claimbranch.core.review import Contribution, Judgment
from .paper_review_policy import PaperReviewPolicy
from .paper_understanding import DRAFT, PaperUnderstandingSession
from .work_cipher import OVERHEAD
from .paper_workspace_snapshot import WORKSPACE, validate_workspace, workspace_schema


class WorkReopenRequired(ContractError):
    """Checkpoint state cannot safely continue under this store session."""


JUDGMENT_DRAFT = obj(project_id=ID, episode_id=ID, text=nullable(TEXT), rationale=nullable(TEXT),
                     history=array(CONTRIBUTION, 8))
WORK = obj(schema={'const': 'claimbranch.paper-work/v1'}, project_id=ID, episode_id=nullable(ID),
           seed=PAPER_SERIES_SEED, commands=array(command_schema(3), 64),
           origins=array(lineage_schema(), 64), judgment=nullable(JUDGMENT_DRAFT),
           review=nullable(REVIEW), explanations=array(DRAFT, 24),
           authority={'const': 'unaccepted-work'}, authorization_verified={'const': False})


WORK_V2 = deepcopy(WORK)
WORK_V2['properties']['schema'] = {'const': 'claimbranch.paper-work/v2'}
WORK_V2['properties']['workspace'] = WORKSPACE
WORK_V2['required'].append('workspace')


WORK_V3 = deepcopy(WORK_V2)
WORK_V3['properties']['schema'] = {'const': 'claimbranch.paper-work/v3'}
WORK_V3['properties']['workspace'] = workspace_schema(2)


WORK_V4 = deepcopy(WORK_V3)
WORK_V4['properties']['schema'] = {'const': 'claimbranch.paper-work/v4'}
WORK_V4['properties']['workspace'] = workspace_schema(3)


WORK_V5 = deepcopy(WORK_V4)
WORK_V5['properties']['schema'] = {'const': 'claimbranch.paper-work/v5'}
WORK_V5['properties']['workspace'] = workspace_schema(4)


WORK_V6 = deepcopy(WORK_V5)
WORK_V6['properties']['schema'] = {'const': 'claimbranch.paper-work/v6'}
WORK_V6['properties']['workspace'] = workspace_schema(5)


WORK_V7 = deepcopy(WORK_V6)
WORK_V7['properties']['schema'] = {'const': 'claimbranch.paper-work/v7'}
WORK_V7['properties']['workspace'] = workspace_schema(6)

WORK_V8 = deepcopy(WORK_V7)
WORK_V8['properties']['schema'] = {'const': 'claimbranch.paper-work/v8'}
WORK_V8['properties']['workspace'] = workspace_schema(7)

WORK_V9 = deepcopy(WORK_V8)
WORK_V9['properties']['schema'] = {'const':'claimbranch.paper-work/v9'}
WORK_V9['properties']['workspace'] = workspace_schema(8)

WORK_V10 = deepcopy(WORK_V9)
WORK_V10['properties']['schema'] = {'const':'claimbranch.paper-work/v10'}
WORK_V10['properties']['workspace'] = workspace_schema(9)

WORK_V11 = deepcopy(WORK_V10)
WORK_V11['properties']['schema'] = {'const':'claimbranch.paper-work/v11'}
WORK_V11['properties']['workspace'] = workspace_schema(10)

WORK_V12 = deepcopy(WORK_V11)
WORK_V12['properties']['schema'] = {'const':'claimbranch.paper-work/v12'}
WORK_V12['properties']['workspace'] = workspace_schema(11)

WORK_V13 = deepcopy(WORK_V12)
WORK_V13['properties']['schema'] = {'const':'claimbranch.paper-work/v13'}
WORK_V13['properties']['workspace'] = workspace_schema(12)

WORK_V14 = deepcopy(WORK_V13)
WORK_V14['properties']['schema'] = {'const':'claimbranch.paper-work/v14'}
from claimbranch.core.research_schema import LIFECYCLE_SEED
WORK_V14['properties']['seed'] = LIFECYCLE_SEED
WORK_V14['properties']['commands'] = array(command_schema(4), 2048)
WORK_V14['properties']['workspace'] = nullable(workspace_schema(13))
WORK_V15 = deepcopy(WORK_V14)
WORK_V15['properties']['schema'] = {'const': 'claimbranch.paper-work/v15'}
from claimbranch.core.research_schema import seed_schema
WORK_V15['properties']['seed'] = seed_schema(5)
WORK_V15['properties']['commands'] = array(command_schema(5), 2048)
WORK_V15['properties']['workspace'] = nullable(workspace_schema(14))

WORK_V16 = deepcopy(WORK_V15)
WORK_V16['properties']['schema']={'const':'claimbranch.paper-work/v16'}
WORK_V16['properties']['seed']={'oneOf':[seed_schema(4),seed_schema(5)]}
WORK_V16['properties']['commands']=array({'oneOf':[command_schema(4),command_schema(5),command_schema(6)]},2048)
WORK_V16['properties']['workspace']=nullable(workspace_schema(15))

WORK_V17 = deepcopy(WORK_V16)
WORK_V17['properties']['schema']={'const':'claimbranch.paper-work/v17'}
WORK_V17['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7)]},2048)
WORK_V17['properties']['workspace']=nullable({'oneOf':[workspace_schema(v) for v in (13,14,15)]})

WORK_V18 = deepcopy(WORK_V17)
WORK_V18['properties']['schema']={'const':'claimbranch.paper-work/v18'}
WORK_V18['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7,8)]},2048)

WORK_V19 = deepcopy(WORK_V18)
WORK_V19['properties']['schema']={'const':'claimbranch.paper-work/v19'}
WORK_V19['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7,8,9)]},2048)

WORK_V20 = deepcopy(WORK_V19)
WORK_V20['properties']['schema']={'const':'claimbranch.paper-work/v20'}
WORK_V20['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7,8,9,10)]},2048)

WORK_V21 = deepcopy(WORK_V20)
WORK_V21['properties']['schema']={'const':'claimbranch.paper-work/v21'}
WORK_V21['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7,8,9,10,11)]},2048)

WORK_V22=deepcopy(WORK_V21)
WORK_V22['properties']['schema']={'const':'claimbranch.paper-work/v22'}
WORK_V22['properties']['commands']=array({'oneOf':[command_schema(v) for v in (4,5,6,7,8,9,10,11,12)]},2048)

from .paper_storage_codec import encode as canonical_bytes, decode, normalize

def work_schema(version=1):
    if type(version) is not int or version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22):
        raise ContractError("unknown work schema")
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': f'urn:claimbranch:paper-work:v{version}',
            '$comment': 'Generated by scripts/export_research_schema.py. Runtime also checks canonical NFC '
                        + ('JSON, a '+('16 MiB' if version in (14,15,16,17,18,19,20,21,22) else '256 KiB')+' aggregate limit, source replay, independent origin and review ')
                        + 'bindings, explanation causes and absent resumed authorization.', **deepcopy({1: WORK, 2: WORK_V2, 3: WORK_V3, 4: WORK_V4, 5: WORK_V5, 6: WORK_V6, 7: WORK_V7, 8: WORK_V8, 9:WORK_V9, 10:WORK_V10, 11:WORK_V11, 12:WORK_V12, 13:WORK_V13, 14:WORK_V14, 15:WORK_V15,16:WORK_V16,17:WORK_V17,18:WORK_V18,19:WORK_V19,20:WORK_V20,21:WORK_V21,22:WORK_V22}[version])}


def _judgment(value):
    return Judgment(value['project_id'], value['episode_id'], value['text'], value['rationale'],
                    tuple(Contribution(**item) for item in value['history']))


@dataclass(frozen=True)
class PaperWork:
    payload: bytes

    def __post_init__(self):
        value = normalize(decode(self.payload), {'oneOf': [WORK, WORK_V2, WORK_V3, WORK_V4, WORK_V5, WORK_V6, WORK_V7, WORK_V8, WORK_V9, WORK_V10, WORK_V11, WORK_V12, WORK_V13, WORK_V14, WORK_V15, WORK_V16, WORK_V17, WORK_V18, WORK_V19, WORK_V20, WORK_V21, WORK_V22]})
        if canonical_bytes(value) != self.payload:
            raise ContractError('work requires canonical bytes')
        history = self.history
        project, episode = value['project_id'], value['episode_id']
        if value.get('workspace') is not None:
            if any(value[key] for key in ('origins', 'judgment', 'review', 'explanations')) or episode is not None:
                raise ContractError('workspace work cannot mix a separate singular review context')
            validate_workspace(history, value['workspace'])
        if decode(history.seed)['project_id'] != project:
            raise ContractError('work belongs to another project')
        if history.schema_version in (4, 5) and (episode is not None or any(value[key] for key in ('origins','judgment','review','explanations'))):
            raise ContractError('personal-paper work cannot carry protected review authority')
        if episode is not None:
            policy = self.new_policy()
        elif value['origins'] or value['judgment'] or value['review']:
            raise ContractError('episode work requires an active episode')
        if value['judgment']:
            judgment = _judgment(value['judgment'])
            if (judgment.project_id, judgment.episode_id) != (project, episode):
                raise ContractError('judgment belongs to another work context')
        if value['review']:
            review = value['review']
            # Historical inspection uses the original clock, never current
            # consent. This fresh owner has no prepared assessment or seal.
            policy.restore_operation(canonical_bytes(review), manuscript_digest=review['manuscript_digest'],
                                     session_nonce=review['session_nonce'], now=review['sealed_at'])
        identities = [draft['work_id'] for draft in value['explanations']]
        if len(set(identities)) != len(identities):
            raise ContractError('duplicate explanation work')
        for draft in value['explanations']:
            PaperUnderstandingSession(history, project_id=project, work_id=draft['work_id'],
                                      draft=canonical_bytes(draft))

    @classmethod
    def create(cls, history, *, episode_id=None, origins=(), judgment=None, review=None, explanations=(), workspace=None):
        if type(history) is not ResearchHistory or history.schema_version not in (3, 4, 5):
            raise ContractError('cumulative candidate history required')
        if judgment is not None and type(judgment) is not Judgment:
            raise ContractError('typed judgment required')
        if review is not None and type(review) is not PaperOperationReview:
            raise ContractError('typed operation review required')
        if type(origins) not in (tuple, list) or any(type(o) is not AmendmentLineage for o in origins):
            raise ContractError('typed origin registry required')
        if type(explanations) not in (tuple, list):
            raise ContractError('bounded explanation drafts required')
        versions = {'claimbranch.judgment-workspace/v1': 2, 'claimbranch.authoring-workspace/v2': 3,
            'claimbranch.explanation-workspace/v3': 4, 'claimbranch.review-writing-workspace/v4': 5,
            'claimbranch.wording-workspace/v5': 6, 'claimbranch.review-pool-workspace/v6': 7,
            'claimbranch.proposal-workspace/v7': 8, 'claimbranch.provider-workspace/v8':9,
            'claimbranch.codex-workspace/v9':10,'claimbranch.external-workspace/v10':11,
            'claimbranch.advisory-workspace/v11':12,'claimbranch.edit-workspace/v12':13, 'claimbranch.paper-workspace/v13':14, 'claimbranch.paper-workspace/v14':15,'claimbranch.paper-workspace/v15':16}
        if workspace is not None and (type(workspace) is not dict or workspace.get('schema') not in versions):
            raise ContractError('unsupported workspace version; no conversion was made')
        if history.schema_version in (4, 5):
            if workspace is not None:
                workspace = deepcopy(workspace)
                workspace['schema'] = 'claimbranch.paper-workspace/v15' if history.has_manuscript_anchors else 'claimbranch.paper-workspace/v14' if history.schema_version == 5 else 'claimbranch.paper-workspace/v13'
        return cls(canonical_bytes({'schema': ('claimbranch.paper-work/v22' if history.has_metadata_origins else 'claimbranch.paper-work/v21' if history.has_critiques else 'claimbranch.paper-work/v20' if history.has_protocols else 'claimbranch.paper-work/v19' if history.has_measurements else 'claimbranch.paper-work/v18' if history.has_co_reports else 'claimbranch.paper-work/v17' if history.has_wording_policies else 'claimbranch.paper-work/v16' if history.has_manuscript_anchors else 'claimbranch.paper-work/v15' if history.schema_version == 5 else 'claimbranch.paper-work/v14' if history.schema_version == 4 else
                f'claimbranch.paper-work/v{versions[workspace["schema"]]}' if workspace is not None else 'claimbranch.paper-work/v1'),
            **({'workspace': workspace} if workspace is not None or history.schema_version in (4, 5) else {}),
            'project_id': decode(history.seed)['project_id'], 'episode_id': episode_id,
            'seed': decode(history.seed), 'commands': [decode(cmd) for cmd in history.commands],
            'origins': [decode(origin.payload) for origin in origins],
            'judgment': asdict(judgment) if judgment else None,
            'review': decode(review.payload) if review else None,
            'explanations': [decode(raw) for raw in explanations],
            'authority': 'unaccepted-work', 'authorization_verified': False}))

    @classmethod
    def from_policy(cls, policy, **work):
        if type(policy) is not PaperReviewPolicy:
            raise ContractError('owned paper review policy required')
        history, episode, origins = policy.work_sources()
        return cls.create(history, episode_id=episode, origins=origins, **work)

    @property
    def project_id(self):
        return decode(self.payload)['project_id']

    @cached_property
    def history(self):
        value = decode(self.payload)
        return ResearchHistory.replay(canonical_bytes(value['seed']),
                                      tuple(canonical_bytes(cmd) for cmd in value['commands']))

    @property
    def origins(self):
        return tuple(AmendmentLineage.restore(canonical_bytes(o)) for o in decode(self.payload)['origins'])

    @property
    def judgment(self):
        value = decode(self.payload)['judgment']
        return _judgment(value) if value else None

    @property
    def review(self):
        from claimbranch.core.canonical import digest
        value = decode(self.payload)['review']
        return PaperOperationReview(canonical_bytes(value), digest(value)) if value else None

    @property
    def explanations(self):
        value, history = decode(self.payload), self.history
        return tuple(PaperUnderstandingSession(history, project_id=value['project_id'],
            work_id=draft['work_id'], draft=canonical_bytes(draft)) for draft in value['explanations'])

    def new_policy(self):
        return PaperReviewPolicy.from_work_sources(self.history,
            episode_id=decode(self.payload)['episode_id'], origins=self.origins)


class _RawKeyCodec:
    max_bytes = MAX_BYTES + OVERHEAD

    def __init__(self, cipher, key):
        if type(key) is not bytes or len(key) != 32:
            raise ContractError('work encryption requires a 32-byte key')
        self.cipher, self.key = cipher, key

    def seal(self, raw):
        return self.cipher.seal(raw, self.key)

    def open(self, raw):
        return self.cipher.open(raw, self.key)


class PaperWorkStore:
    """One private checkpoint and an exclusive session, no automatic key storage.

    Existing data must load successfully before replacement. A detected external
    file change requires explicit reload. Failures after replace are uncertain
    commits: close and reopen before deciding which writing is durable.
    """
    work_type = PaperWork
    checkpoint_file = 'work.cbw'
    staging_prefix = '.work-'

    def __init__(self, directory, *, cipher, key, project_id):
        self._configure(directory, codec=_RawKeyCodec(cipher, key), project_id=project_id)

    def _configure(self, directory, *, codec, project_id):
        identifier(project_id)
        self._path = Path(directory)
        self._codec, self._project = codec, project_id
        self._dir = self._lock = None
        self._loaded, self._last = False, None
        self._uncertain = False
        self._reopen_error = None

    def __enter__(self):
        import fcntl
        if self._dir is not None:
            raise ContractError('work store session is already open')
        self._reopen_error = None
        try:
            if self._path.is_symlink():
                raise ContractError('work directory cannot be a symbolic link')
            self._path = self._path.resolve(strict=True)
            self._outside_git()
            self._dir = os.open(self._path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self._check_directory()
            self._lock = self._open('work.lock', create=True)
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._uncertain = False
            self._clean_staging()
        except ContractError:
            self.close()
            raise
        except OSError:
            self.close()
            raise ContractError('work directory must be private, outside Git and not open in another session') from None
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        for name in ('_lock', '_dir'):
            if getattr(self, name) is not None:
                os.close(getattr(self, name))
                setattr(self, name, None)
        self._loaded = False
        self._last = None

    def _outside_git(self):
        for parent in (self._path, *self._path.parents):
            marker = parent / '.git'
            if marker.exists() or marker.is_symlink():
                raise ContractError('work directory must be outside Git')

    def _check_directory(self):
        if getattr(self, '_reopen_error', None) is not None:
            raise self._reopen_error
        if self._dir is None:
            raise ContractError('work store is closed')
        if self.checkpoint_file != 'provider.json':
            try:
                os.stat('provider.json', dir_fd=self._dir, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                self._require_reopen('Provider configuration needs a separate directory from research and backups; existing files retained.')
        if self.checkpoint_file == 'work.cbw':
            try:
                os.stat('personal.cbp', dir_fd=self._dir, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                self._require_reopen('personal work belongs to a separate destination; no conversion was made')
        info = os.fstat(self._dir)
        try:
            current = self._path.lstat()
        except FileNotFoundError:
            self._require_reopen('private work directory is missing')
        if (not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
            self._require_reopen('private work directory changed')
        try:
            self._outside_git()
        except ContractError as error:
            self._require_reopen(str(error))
        if self._lock is not None:
            try:
                lock = os.stat('work.lock', dir_fd=self._dir, follow_symlinks=False)
            except FileNotFoundError:
                self._require_reopen('work session lock is missing')
            held = os.fstat(self._lock)
            if (lock.st_dev, lock.st_ino) != (held.st_dev, held.st_ino):
                self._require_reopen('work session lock changed')

    def _require_reopen(self, message):
        self._reopen_error = WorkReopenRequired(message)
        raise self._reopen_error

    def _open(self, name, *, create=False, exclusive=False):
        flags = os.O_RDWR if create else os.O_RDONLY
        try:
            descriptor = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_CREAT if create else 0)
                                 | (os.O_EXCL if exclusive else 0), 0o600, dir_fd=self._dir)
        except OSError as error:
            if error.errno == errno.ELOOP:
                self._require_reopen('work file changed to an unsupported symbolic link')
            raise
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600):
            os.close(descriptor)
            self._require_reopen('work files must be owned private regular files')
        return descriptor

    def _clean_staging(self):
        """Reclaim only reserved private staging files under the exclusive lock.

        They were never reported as a completed checkpoint. A bounded scan
        precedes deletion; unrelated names and linked/non-private files stay.
        """
        candidates = []
        with os.scandir(self._dir) as entries:
            for count, entry in enumerate(entries):
                if count >= 128:
                    raise ContractError('work directory inventory exceeds its limit')
                if re.fullmatch(re.escape(self.staging_prefix) + r'[0-9a-f]{32}', entry.name) is None:
                    continue
                info = entry.stat(follow_symlinks=False)
                if (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                        and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= self._codec.max_bytes):
                    candidates.append(entry.name)
        for name in candidates:
            os.unlink(name, dir_fd=self._dir)

    @staticmethod
    def _sync(descriptor):
        os.fsync(descriptor)
        if sys.platform == 'darwin':
            import fcntl
            # No silent downgrade on unsupported filesystems. A failure before
            # replace preserves the old checkpoint; afterward it is uncertain.
            fcntl.fcntl(descriptor, fcntl.F_FULLFSYNC)

    def _read(self):
        try:
            descriptor = self._open(self.checkpoint_file)
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor, 'rb') as stream:
            raw = stream.read(self._codec.max_bytes + 1)
        if len(raw) > self._codec.max_bytes:
            self._require_reopen('saved work exceeds its limit')
        return raw

    @staticmethod
    def _fingerprint(raw):
        return hashlib.sha256(raw).digest() if raw is not None else None

    def load(self):
        try:
            self._check_directory()
            if self._uncertain:
                self._require_reopen('save outcome uncertain; close and reopen work')
            raw = self._read()
            if self._loaded and self._fingerprint(raw) != self._last:
                self._require_reopen('work changed outside this session; close and reopen before saving')
            if raw is None:
                if self._last is not None:
                    raise ContractError('previous work file is missing')
                work = None
            else:
                work = self.work_type(self._codec.open(raw))
                if work.project_id != self._project:
                    raise ContractError('work belongs to another project')
            self._last, self._loaded = self._fingerprint(raw), True
            return work
        except OSError:
            raise ContractError('work could not be read; original files retained') from None

    def verify_unchanged(self):
        """Check a cached checkpoint without decrypting or rewriting it."""
        try:
            self._check_directory()
            if self._uncertain:
                self._require_reopen('save outcome uncertain; close and reopen work')
            if not self._loaded:
                raise ContractError('load work before checking its checkpoint')
            if self._fingerprint(self._read()) != self._last:
                self._require_reopen('work changed outside this session; close and reopen before saving')
        except OSError:
            raise ContractError('work could not be checked; original files retained') from None

    def save(self, work):
        temporary = None
        replaced = False
        try:
            self._check_directory()
            if self._uncertain:
                self._require_reopen('save outcome uncertain; close and reopen work')
            if type(work) is not self.work_type or work.project_id != self._project:
                raise ContractError('typed work for this project required')
            # Do not overwrite unknown, wrong-key or unreadable previous work.
            if not self._loaded:
                self.load()
            raw = self._read()
            if self._fingerprint(raw) != self._last:
                self._require_reopen('work changed outside this session; close and reopen before saving')
            checked = self.work_type(work.payload)
            encrypted = self._codec.seal(checked.payload)
            temporary = self.staging_prefix + secrets.token_hex(16)
            descriptor = self._open(temporary, create=True, exclusive=True)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(encrypted)
                stream.flush()
                self._sync(stream.fileno())
            self._check_directory()
            if self._fingerprint(self._read()) != self._last:
                self._require_reopen('work changed while saving; close and reopen before saving')
            os.replace(temporary, self.checkpoint_file, src_dir_fd=self._dir, dst_dir_fd=self._dir)
            replaced, temporary = True, None
            self._sync(self._dir)
            self._last = self._fingerprint(encrypted)
        except OSError:
            if replaced:
                self._uncertain = True
                self._require_reopen('save outcome uncertain; close and reopen work')
            raise ContractError('work save failed; prior checkpoint retained') from None
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary, dir_fd=self._dir)
                except OSError:
                    pass
