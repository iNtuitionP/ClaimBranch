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


EDIT_PERSONAL_MAGIC=b'CBPP\x00\x0b'
ORIGINAL_PERSONAL_MAGIC=b'CBPP\x00\x0c'
RETAINED_PERSONAL_MAGIC=b'CBPP\x00\x0d'
LABEL_PERSONAL_MAGIC=b'CBPP\x00\x0e'
SHARED_PERSONAL_MAGIC=b'CBPP\x00\x0f'
CONDITIONAL_PERSONAL_MAGIC=b'CBPP\x00\x10'
SOURCE_PERSONAL_MAGIC=b'CBPP\x00\x11'
HISTORICAL_PERSONAL_MAGIC=b'CBPP\x00\x12'
HISTORY_PERSONAL_MAGIC=b'CBPP\x00\x13'
ITERATION_PERSONAL_MAGIC=b'CBPP\x00\x14'


class _PersonalCodec:
    max_bytes = PROJECT_BYTES + len(PERSONAL_MAGIC)

    def seal(self, raw):
        value = storage_decode(raw)
        iteration = value.get('schema') == 'claimbranch.project-work/v28'
        new_history = value.get('schema') == 'claimbranch.project-work/v27'
        historical = value.get('schema') == 'claimbranch.project-work/v26'
        source_v3 = value.get('schema') == 'claimbranch.project-work/v25'
        conditional = value.get('schema') == 'claimbranch.project-work/v24'
        shared = value.get('schema') == 'claimbranch.project-work/v23'
        labeled = value.get('schema') == 'claimbranch.project-work/v22'
        retained = value.get('schema') == 'claimbranch.project-work/v21'
        original = value.get('schema') == 'claimbranch.project-work/v20'
        edited = value.get('schema') == 'claimbranch.project-work/v19'
        metadata = value.get('schema') == 'claimbranch.project-work/v18'
        critique = value.get('schema') == 'claimbranch.project-work/v17'
        protocol = value.get('schema') == 'claimbranch.project-work/v16'
        measurement = value.get('schema') == 'claimbranch.project-work/v15'
        co_report = value.get('schema') == 'claimbranch.project-work/v14'
        wording = value.get('schema') == 'claimbranch.project-work/v13'
        anchored = value.get('schema') == 'claimbranch.project-work/v12'
        imported = value.get('schema') == 'claimbranch.project-work/v11'
        paper = value.get('schema') in ('claimbranch.project-work/v10', 'claimbranch.project-work/v11', 'claimbranch.project-work/v12','claimbranch.project-work/v13','claimbranch.project-work/v14','claimbranch.project-work/v15','claimbranch.project-work/v16','claimbranch.project-work/v17','claimbranch.project-work/v18','claimbranch.project-work/v19','claimbranch.project-work/v20','claimbranch.project-work/v21','claimbranch.project-work/v22','claimbranch.project-work/v23','claimbranch.project-work/v24','claimbranch.project-work/v25','claimbranch.project-work/v26','claimbranch.project-work/v27','claimbranch.project-work/v28')
        maximum = PROJECT_BYTES if paper else MAX_BYTES
        if len(raw) > maximum:
            raise ContractError('personal work exceeds its limit')
        return (ITERATION_PERSONAL_MAGIC if iteration else HISTORY_PERSONAL_MAGIC if new_history else HISTORICAL_PERSONAL_MAGIC if historical else SOURCE_PERSONAL_MAGIC if source_v3 else CONDITIONAL_PERSONAL_MAGIC if conditional else SHARED_PERSONAL_MAGIC if shared else LABEL_PERSONAL_MAGIC if labeled else RETAINED_PERSONAL_MAGIC if retained else ORIGINAL_PERSONAL_MAGIC if original else EDIT_PERSONAL_MAGIC if edited else METADATA_PERSONAL_MAGIC if metadata else CRITIQUE_PERSONAL_MAGIC if critique else PROTOCOL_PERSONAL_MAGIC if protocol else MEASUREMENT_PERSONAL_MAGIC if measurement else CO_REPORT_PERSONAL_MAGIC if co_report else WORDING_PERSONAL_MAGIC if wording else ANCHOR_PERSONAL_MAGIC if anchored else IMPORT_PERSONAL_MAGIC if imported else PAPER_PERSONAL_MAGIC if paper else PERSONAL_MAGIC) + raw

    def open(self, raw):
        if type(raw) is not bytes:
            raise ContractError('personal checkpoint requires bytes')
        if raw.startswith(ITERATION_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, ITERATION_PERSONAL_MAGIC
        elif raw.startswith(HISTORY_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, HISTORY_PERSONAL_MAGIC
        elif raw.startswith(HISTORICAL_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, HISTORICAL_PERSONAL_MAGIC
        elif raw.startswith(SOURCE_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, SOURCE_PERSONAL_MAGIC
        elif raw.startswith(CONDITIONAL_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, CONDITIONAL_PERSONAL_MAGIC
        elif raw.startswith(SHARED_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, SHARED_PERSONAL_MAGIC
        elif raw.startswith(LABEL_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, LABEL_PERSONAL_MAGIC
        elif raw.startswith(RETAINED_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, RETAINED_PERSONAL_MAGIC
        elif raw.startswith(ORIGINAL_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, ORIGINAL_PERSONAL_MAGIC
        elif raw.startswith(EDIT_PERSONAL_MAGIC):
            maximum, prefix = PROJECT_BYTES, EDIT_PERSONAL_MAGIC
        elif raw.startswith(METADATA_PERSONAL_MAGIC):
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
        expected = {'claimbranch.project-work/v28':ITERATION_PERSONAL_MAGIC,'claimbranch.project-work/v27':HISTORY_PERSONAL_MAGIC,'claimbranch.project-work/v26':HISTORICAL_PERSONAL_MAGIC,'claimbranch.project-work/v25':SOURCE_PERSONAL_MAGIC,'claimbranch.project-work/v24':CONDITIONAL_PERSONAL_MAGIC,'claimbranch.project-work/v23':SHARED_PERSONAL_MAGIC,'claimbranch.project-work/v22':LABEL_PERSONAL_MAGIC,'claimbranch.project-work/v21':RETAINED_PERSONAL_MAGIC,'claimbranch.project-work/v20':ORIGINAL_PERSONAL_MAGIC,'claimbranch.project-work/v19':EDIT_PERSONAL_MAGIC,'claimbranch.project-work/v10': PAPER_PERSONAL_MAGIC, 'claimbranch.project-work/v11': IMPORT_PERSONAL_MAGIC,'claimbranch.project-work/v12':ANCHOR_PERSONAL_MAGIC,'claimbranch.project-work/v13':WORDING_PERSONAL_MAGIC,'claimbranch.project-work/v14':CO_REPORT_PERSONAL_MAGIC,'claimbranch.project-work/v15':MEASUREMENT_PERSONAL_MAGIC,'claimbranch.project-work/v16':PROTOCOL_PERSONAL_MAGIC,'claimbranch.project-work/v17':CRITIQUE_PERSONAL_MAGIC,'claimbranch.project-work/v18':METADATA_PERSONAL_MAGIC}.get(value.get('schema'), PERSONAL_MAGIC)
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
        try:
            if not self._known_project:
                self._check_directory()
                raw = self._read()
                if raw is None:
                    raise ContractError('personal project is missing; no replacement was created')
                # Select only a provisional ID. The base constructs and fully
                # verifies the project once, checking that ID against its read.
                value=storage_decode(self._codec.open(raw))
                project_id=value.get('project_id') if type(value) is dict else None
                identifier(project_id)
                previous=self._project;self._project=project_id
                try:project=super().load()
                except BaseException:
                    self._project=previous
                    raise
                self._known_project=True
                return project
            return super().load()
        except OSError:
            raise ContractError('work could not be read; original files retained') from None

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


    def __init__(self,store,app,project):
        super().__init__(store,app,project)
        from .tui_view_state import load
        self._previous_view=load(store,app)

    def save(self,app,active=None):
        super().save(app,active)
        from .tui_view_state import save
        try:self._previous_view=save(self.store,app,self._previous_view)
        except (OSError,ContractError):
            app.view_save_notice='Graph view could not be saved; research writing checkpoint is unaffected.'
