"""Explicit, create-only local archive, separate from the live checkpoint.

An interrupted copy can remain at the destination. Never overwrite it or report
success before full sync. A fresh destination is the safe retry; authenticated
recovery decides whether any supplied copy is usable.
"""
import os
from types import SimpleNamespace

from claimbranch.core.canonical import ContractError
from .device_work_store import MAX_DEVICE_BYTES, split_device_checkpoint
from .paper_work_store import PaperWorkStore


class WorkArchive(PaperWorkStore):
    """Reuse private path checks; read never creates locks or cleans the source.

    Exclusive file creation serializes competing writers without a lock file.
    A simultaneous reader may see incomplete output and must authenticate it
    before recovery. This archive is never a mutable live checkpoint.
    """
    archive_file = 'backup.cbw'
    copy_label = 'backup'
    directory_label = 'archive'
    max_bytes = MAX_DEVICE_BYTES
    validate_raw = staticmethod(split_device_checkpoint)

    def __init__(self, directory):
        self._configure(directory, codec=SimpleNamespace(max_bytes=self.max_bytes), project_id='archive')

    def __enter__(self):
        if self._dir is not None:
            raise ContractError(self.directory_label+' session is already open')
        self._reopen_error = None
        try:
            if self._path.is_symlink():
                raise ContractError(self.directory_label+' directory cannot be a symbolic link')
            self._path = self._path.resolve(strict=True)
            self._outside_git()
            self._dir = os.open(self._path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self._check_directory()
        except ContractError:
            self.close()
            raise
        except OSError:
            self.close()
            raise ContractError(self.directory_label+' directory must be private and outside Git') from None
        return self

    def read(self):
        try:
            self._check_directory()
            descriptor = self._open(self.archive_file)
            with os.fdopen(descriptor, 'rb') as stream:
                raw = stream.read(self.max_bytes + 1)
            self._check_directory()
            self.validate_raw(raw)
            return raw
        except OSError:
            raise ContractError(self.copy_label+' could not be read; source was not changed') from None

    def write(self, raw):
        # The work store checks complete contents; the default validator here
        # only checks encrypted framing. Copies never grant imported authority.
        self.validate_raw(raw)
        started = False
        try:
            self._check_directory()
            descriptor = self._open(self.archive_file, create=True, exclusive=True)
            started = True
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                self._sync(stream.fileno())
            self._check_directory()
            self._sync(self._dir)
        except BaseException as error:
            message = self.copy_label + (' may be incomplete; preserve it and retry in a new private directory' if started else
                       ' destination is unavailable or already exists; nothing was replaced')
            if isinstance(error, KeyboardInterrupt):
                raise KeyboardInterrupt(message) from error
            if started or isinstance(error, OSError):
                raise ContractError(message) from error
            raise
