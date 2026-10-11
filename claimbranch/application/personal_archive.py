"""Checksummed personal backup and separate readable, create-only export.

The digest detects accidental damage, not authorship, authenticity or encryption.
Neither supplied backups nor JSON exports confer protected authority.
"""
import hashlib
import os

from claimbranch.core.canonical import ContractError, MAX_BYTES
from .personal_project import PERSONAL_MAGIC, _PersonalCodec
from .project_work import ProjectWork
from .work_archive import WorkArchive


BACKUP_MAGIC = b'CBPB\x00\x01'
MAX_BACKUP_BYTES = MAX_BYTES + len(PERSONAL_MAGIC) + len(BACKUP_MAGIC) + 32


def split_personal_backup(raw):
    if (type(raw) is not bytes or not raw.startswith(BACKUP_MAGIC)
            or not len(BACKUP_MAGIC)+32 < len(raw) <= MAX_BACKUP_BYTES):
        raise ContractError('Unsupported or incomplete personal backup; original retained.')
    checksum=raw[len(BACKUP_MAGIC):len(BACKUP_MAGIC)+32]
    checkpoint=raw[len(BACKUP_MAGIC)+32:]
    if hashlib.sha256(checkpoint).digest()!=checksum:
        raise ContractError('Personal backup checksum mismatch; original retained.')
    return ProjectWork(_PersonalCodec().open(checkpoint))


def personal_backup(project):
    checked=ProjectWork(project.payload)
    checkpoint=_PersonalCodec().seal(checked.payload)
    return BACKUP_MAGIC+hashlib.sha256(checkpoint).digest()+checkpoint


class PersonalArchive(WorkArchive):
    archive_file = checkpoint_file = 'backup.cbp'
    max_bytes = MAX_BACKUP_BYTES
    validate_raw = staticmethod(split_personal_backup)

    def _check_directory(self):
        super()._check_directory()
        for name in ('personal.cbp','work.cbw'):
            try: os.stat(name,dir_fd=self._dir,follow_symlinks=False)
            except FileNotFoundError: continue
            self._require_reopen('Archive needs a separate private directory; live work was not replaced.')


class PersonalExport(PersonalArchive):
    archive_file = checkpoint_file = 'project.json'
    max_bytes = MAX_BYTES
    copy_label = 'export'
    validate_raw = staticmethod(ProjectWork)
