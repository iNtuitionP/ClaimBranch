"""Checksummed personal backup and separate readable, create-only export.

The digest detects accidental damage, not authorship, authenticity or encryption.
Neither supplied backups nor JSON exports confer protected authority.
"""
import hashlib
import os

from claimbranch.core.canonical import ContractError, MAX_BYTES
from .personal_project import PERSONAL_MAGIC, PAPER_PERSONAL_MAGIC, IMPORT_PERSONAL_MAGIC, ANCHOR_PERSONAL_MAGIC, WORDING_PERSONAL_MAGIC, CO_REPORT_PERSONAL_MAGIC, MEASUREMENT_PERSONAL_MAGIC, PROTOCOL_PERSONAL_MAGIC, CRITIQUE_PERSONAL_MAGIC, METADATA_PERSONAL_MAGIC, _PersonalCodec
from claimbranch.core.paper_capacity import PROJECT_BYTES
from .project_work import ProjectWork
from .work_archive import WorkArchive


BACKUP_MAGIC = b'CBPB\x00\x01'
PAPER_BACKUP_MAGIC = b'CBPB\x00\x02'
IMPORT_BACKUP_MAGIC = b'CBPB\x00\x03'
ANCHOR_BACKUP_MAGIC = b'CBPB\x00\x04'
WORDING_BACKUP_MAGIC = b'CBPB\x00\x05'
CO_REPORT_BACKUP_MAGIC = b'CBPB\x00\x06'
MEASUREMENT_BACKUP_MAGIC = b'CBPB\x00\x07'
PROTOCOL_BACKUP_MAGIC = b'CBPB\x00\x08'
CRITIQUE_BACKUP_MAGIC = b'CBPB\x00\x09'
METADATA_BACKUP_MAGIC=b'CBPB\x00\x0a'
MAX_BACKUP_BYTES = PROJECT_BYTES + len(PERSONAL_MAGIC) + len(BACKUP_MAGIC) + 32


def split_personal_backup(raw):
    if (type(raw) is not bytes or not raw.startswith((BACKUP_MAGIC, PAPER_BACKUP_MAGIC, IMPORT_BACKUP_MAGIC, ANCHOR_BACKUP_MAGIC, WORDING_BACKUP_MAGIC, CO_REPORT_BACKUP_MAGIC, MEASUREMENT_BACKUP_MAGIC, PROTOCOL_BACKUP_MAGIC, CRITIQUE_BACKUP_MAGIC, METADATA_BACKUP_MAGIC))
            or not len(BACKUP_MAGIC)+32 < len(raw) <= MAX_BACKUP_BYTES):
        raise ContractError('Unsupported or incomplete personal backup; original retained.')
    checksum=raw[len(BACKUP_MAGIC):len(BACKUP_MAGIC)+32]
    checkpoint=raw[len(BACKUP_MAGIC)+32:]
    if hashlib.sha256(checkpoint).digest()!=checksum:
        raise ContractError('Personal backup checksum mismatch; original retained.')
    expected = METADATA_BACKUP_MAGIC if checkpoint.startswith(METADATA_PERSONAL_MAGIC) else CRITIQUE_BACKUP_MAGIC if checkpoint.startswith(CRITIQUE_PERSONAL_MAGIC) else PROTOCOL_BACKUP_MAGIC if checkpoint.startswith(PROTOCOL_PERSONAL_MAGIC) else MEASUREMENT_BACKUP_MAGIC if checkpoint.startswith(MEASUREMENT_PERSONAL_MAGIC) else CO_REPORT_BACKUP_MAGIC if checkpoint.startswith(CO_REPORT_PERSONAL_MAGIC) else WORDING_BACKUP_MAGIC if checkpoint.startswith(WORDING_PERSONAL_MAGIC) else ANCHOR_BACKUP_MAGIC if checkpoint.startswith(ANCHOR_PERSONAL_MAGIC) else IMPORT_BACKUP_MAGIC if checkpoint.startswith(IMPORT_PERSONAL_MAGIC) else PAPER_BACKUP_MAGIC if checkpoint.startswith(PAPER_PERSONAL_MAGIC) else BACKUP_MAGIC
    if not raw.startswith(expected):
        raise ContractError('personal backup frame/profile mismatch')
    if raw.startswith(BACKUP_MAGIC) and len(raw)>MAX_BYTES+len(PERSONAL_MAGIC)+len(BACKUP_MAGIC)+32:
        raise ContractError('legacy backup byte budget exceeded')
    return ProjectWork(_PersonalCodec().open(checkpoint))


def personal_backup(project):
    checked=ProjectWork(project.payload)
    checkpoint=_PersonalCodec().seal(checked.payload)
    return (METADATA_BACKUP_MAGIC if checkpoint.startswith(METADATA_PERSONAL_MAGIC) else CRITIQUE_BACKUP_MAGIC if checkpoint.startswith(CRITIQUE_PERSONAL_MAGIC) else PROTOCOL_BACKUP_MAGIC if checkpoint.startswith(PROTOCOL_PERSONAL_MAGIC) else MEASUREMENT_BACKUP_MAGIC if checkpoint.startswith(MEASUREMENT_PERSONAL_MAGIC) else CO_REPORT_BACKUP_MAGIC if checkpoint.startswith(CO_REPORT_PERSONAL_MAGIC) else WORDING_BACKUP_MAGIC if checkpoint.startswith(WORDING_PERSONAL_MAGIC) else ANCHOR_BACKUP_MAGIC if checkpoint.startswith(ANCHOR_PERSONAL_MAGIC) else IMPORT_BACKUP_MAGIC if checkpoint.startswith(IMPORT_PERSONAL_MAGIC) else PAPER_BACKUP_MAGIC if checkpoint.startswith(PAPER_PERSONAL_MAGIC) else BACKUP_MAGIC)+hashlib.sha256(checkpoint).digest()+checkpoint


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


def _check_private_export(raw):
    project=ProjectWork(raw)
    if project.work.history.has_critiques:raise ContractError('Private critique originals cannot enter a full JSON export; use private backup or the separately reviewed sharing path')
    if project.work.history.has_metadata_origins:raise ContractError('Extended metadata originals require private backup or selected canonical sharing; no full JSON export was written')
    return project


class PersonalExport(PersonalArchive):
    archive_file = checkpoint_file = 'project.json'
    max_bytes = PROJECT_BYTES
    copy_label = 'export'
    validate_raw = staticmethod(_check_private_export)
