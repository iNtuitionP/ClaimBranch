"""Personal local files, explicitly separate from encrypted/protected custody."""
import os

from claimbranch.core.canonical import ContractError, MAX_BYTES, identifier
from .paper_work_store import PaperWorkStore, WorkReopenRequired
from .project_work import ProjectAssociationStore, ProjectWork
from .tui_project import ProjectRecovery


PERSONAL_MAGIC = b'CBPP\x00\x01'
PAPER_PERSONAL_MAGIC = b'CBPP\x00\x02'
IMPORT_PERSONAL_MAGIC = b'CBPP\x00\x03'
ANCHOR_PERSONAL_MAGIC = b'CBPP\x00\x04'
WORDING_PERSONAL_MAGIC = b'CBPP\x00\x05'
CO_REPORT_PERSONAL_MAGIC = b'CBPP\x00\x06'
MEASUREMENT_PERSONAL_MAGIC = b'CBPP\x00\x07'
PROTOCOL_PERSONAL_MAGIC = b'CBPP\x00\x08'
METADATA_PERSONAL_MAGIC = b'CBPP\x00\x0a'
CRITIQUE_PERSONAL_MAGIC = b'CBPP\x00\x09'
from claimbranch.core.paper_capacity import PROJECT_BYTES
from .paper_storage_codec import decode as storage_decode


class _PersonalCodec:
    max_bytes = PROJECT_BYTES + len(PERSONAL_MAGIC)

    def seal(self, raw):
        value = storage_decode(raw)
        metadata = value.get('schema') == 'claimbranch.project-work/v18'
        critique = value.get('schema') == 'claimbranch.project-work/v17'
        protocol = value.get('schema') == 'claimbranch.project-work/v16'
        measurement = value.get('schema') == 'claimbranch.project-work/v15'
        co_report = value.get('schema') == 'claimbranch.project-work/v14'
        wording = value.get('schema') == 'claimbranch.project-work/v13'
        anchored = value.get('schema') == 'claimbranch.project-work/v12'
        imported = value.get('schema') == 'claimbranch.project-work/v11'
        paper = value.get('schema') in ('claimbranch.project-work/v10', 'claimbranch.project-work/v11', 'claimbranch.project-work/v12','claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18')
        maximum = PROJECT_BYTES if paper else MAX_BYTES
        if len(raw) > maximum:
            raise ContractError('personal work exceeds its limit')
        return (METADATA_PERSONAL_MAGIC if metadata else CRITIQUE_PERSONAL_MAGIC if critique else PROTOCOL_PERSONAL_MAGIC if protocol else MEASUREMENT_PERSONAL_MAGIC if measurement else CO_REPORT_PERSONAL_MAGIC if co_report else WORDING_PERSONAL_MAGIC if wording else ANCHOR_PERSONAL_MAGIC if anchored else IMPORT_PERSONAL_MAGIC if imported else PAPER_PERSONAL_MAGIC if paper else PERSONAL_MAGIC) + raw

    def open(self, raw):
        if type(raw) is not bytes:
            raise ContractError('personal checkpoint requires bytes')
        if raw.startswith(METADATA_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, METADATA_PERSONAL_MAGIC
        elif raw.startswith(CRITIQUE_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, CRITIQUE_PERSONAL_MAGIC
        elif raw.startswith(PROTOCOL_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, PROTOCOL_PERSONAL_MAGIC
        elif raw.startswith(MEASUREMENT_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, MEASUREMENT_PERSONAL_MAGIC
        elif raw.startswith(CO_REPORT_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, CO_REPORT_PERSONAL_MAGIC
        elif raw.startswith(WORDING_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, WORDING_PERSONAL_MAGIC
        elif raw.startswith(ANCHOR_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, ANCHOR_PERSONAL_MAGIC
        elif raw.startswith(IMPORT_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, IMPORT_PERSONAL_MAGIC
        elif raw.startswith(PAPER_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, PAPER_PERSONAL_MAGIC
        elif raw.startswith(PERSONAL_MAGIC):
            maximum, prefix = MAX_BYTES, PERSONAL_MAGIC
        else:
            raise ContractError('unsupported personal checkpoint; original retained')
        if not len(prefix) < len(raw) <= maximum+len(prefix):
            raise ContractError('personal checkpoint exceeds its versioned limit')
        payload = raw[len(prefix):]
        value = storage_decode(payload)
        expected = {'claimbranch.project-work/v10': PAPER_PERSONAL_MAGIC, 'claimbranch.project-work/v11': IMPORT_PERSONAL_MAGIC,'claimbranch.project-work/v12':ANCHOR_PERSONAL_MAGIC,'claimbranch.project-work/v13':WORDING_PERSONAL_MAGIC,'claimbranch.project-work/v14':CO_REPORT_PERSONAL_MAGIC,'claimbranch.project-work/v15':MEASUREMENT_PERSONAL_MAGIC,'claimbranch.project-work/v16':PROTOCOL_PERSONAL_MAGIC,'claimbranch.project-work/v17':CRITIQUE_PERSONAL_MAGIC,'claimbranch.project-work/v18':METADATA_PERSONAL_MAGIC}.get(value.get('schema'), PERSONAL_MAGIC)
        if prefix != expected:
            raise ContractError('personal checkpoint frame/profile mismatch')
        return payload


class PersonalProjectStore(ProjectAssociationStore, PaperWorkStore):
    """One bounded, owner-private personal checkpoint and exclusive session.

    No cipher, key, imported approval, native tool or automatic conversion.
    The validated inner work envelope still grants no protected authority.
    """
    checkpoint_file = 'personal.cbp'
    staging_prefix = '.personal-'

    def __init__(self, directory, *, project_id=None):
        if project_id is not None:
            identifier(project_id)
        self._known_project = project_id is not None
        self._creating = False
        self._configure(directory, codec=_PersonalCodec(), project_id=project_id or 'personal-unselected')

    @classmethod
    def create(cls, directory, *, project_id):
        identifier(project_id)
        result = cls(directory, project_id=project_id)
        result._creating = True
        return result

    def _check_directory(self):
        super()._check_directory()
        # Run before the base creates a lock or reclaims staging. An encrypted
        # destination is not an empty personal project or an implicit import.
        try:
            os.stat('work.cbw', dir_fd=self._dir, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            self._require_reopen('encrypted work belongs to a separate destination; no conversion was made')
        if self._creating:
            for name in ('backup.cbp','project.json'):
                try: os.stat(name,dir_fd=self._dir,follow_symlinks=False)
                except FileNotFoundError: continue
                self._require_reopen('Personal creation or restore needs a separate fresh directory; archive files retained.')

    def __enter__(self):
        super().__enter__()
        try:
            try:
                raw = self._read()
            except OSError as error:
                raise ContractError('personal checkpoint could not be read; no replacement was made') from error
            if self._creating:
                if raw is not None:
                    raise ContractError('personal project creation cannot replace existing work')
            elif raw is None:
                raise ContractError('personal project is missing; no replacement was created')
            else:
                self.load()
        except BaseException:
            self.close()
            raise
        return self

    def load(self):
        if not self._known_project:
            self._check_directory()
            raw = self._read()
            if raw is None:
                raise ContractError('personal project is missing; no replacement was created')
            project = ProjectWork(self._codec.open(raw))
            self._project, self._known_project = project.project_id, True
        return super().load()

    def backup(self):
        """Only the verified saved workspace, never newer live editor buffers."""
        from .personal_archive import personal_backup
        project=self.load()
        raw=personal_backup(project)
        self.verify_unchanged()
        return raw

    def save(self, work, *, preview=None, source_review=None):
        super().save(work,preview=preview,source_review=source_review)
        self._creating = False

    def _save_restored(self, work):
        super()._save_restored(work)
        self._creating = False

    @classmethod
    def restore_backup(cls, raw, directory, *, project_id=None):
        from .personal_archive import split_personal_backup
        project=split_personal_backup(raw)
        if project_id is not None and project.project_id!=project_id:
            raise ContractError('Backup belongs to another project; no restore was started.')
        save_attempted=False
        try:
            with cls.create(directory,project_id=project.project_id) as store:
                save_attempted=True
                store._save_restored(project)
                if store.load().payload!=project.payload:
                    raise ContractError('Restored work does not match; preserve files and inspect the destination.')
        except WorkReopenRequired as error:
            if save_attempted:
                raise
            # Destination refusal before saving is not uncertain replacement.
            raise ContractError(str(error)) from error
        return project


class PersonalProjectRecovery(ProjectRecovery):
    """Use the existing full writing checkpoint with honest personal labeling."""
    personal_project = True
    encrypted_judgments = False
