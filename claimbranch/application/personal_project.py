"""Personal local files, explicitly separate from encrypted/protected custody."""
import os

from claimbranch.core.canonical import ContractError, MAX_BYTES, identifier
from .paper_work_store import PaperWorkStore, WorkReopenRequired
from .project_work import ProjectAssociationStore, ProjectWork
from .tui_project import ProjectRecovery


PERSONAL_MAGIC = b'CBPP\x00\x01'


class _PersonalCodec:
    max_bytes = MAX_BYTES + len(PERSONAL_MAGIC)

    def seal(self, raw):
        # This is framing, not encryption or an authenticated authority record.
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise ContractError('personal work exceeds its limit')
        return PERSONAL_MAGIC + raw

    def open(self, raw):
        if (type(raw) is not bytes or not raw.startswith(PERSONAL_MAGIC)
                or not len(PERSONAL_MAGIC) < len(raw) <= self.max_bytes):
            raise ContractError('unsupported or invalid personal checkpoint; original retained')
        return raw[len(PERSONAL_MAGIC):]


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
