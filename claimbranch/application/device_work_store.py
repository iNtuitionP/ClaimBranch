"""Device-bound encrypted candidate work, with explicit separate-key recovery.

This data-key path cannot sign approvals. It does not make an unrestricted
same-user process safe or confer accepted authority on imported history.
"""
import hashlib
import hmac
import os

from claimbranch.core.canonical import ContractError, MAX_BYTES, canonical_bytes, identifier
from .paper_work_store import PaperWorkStore
from .work_cipher import KEY_MAGIC, MAGIC, MAX_KEY_BYTES, OVERHEAD


DEVICE_MAGIC = b'CBWD\x00\x01'
MAX_DEVICE_BYTES = 10 + MAX_KEY_BYTES + MAX_BYTES + OVERHEAD


def project_binding(project_id):
    identifier(project_id)
    return hashlib.sha256(canonical_bytes({'schema': 'claimbranch.work-key-binding/v1',
                                         'project_id': project_id})).digest()


def split_device_checkpoint(raw):
    if (type(raw) is not bytes or not 10 < len(raw) <= MAX_DEVICE_BYTES
            or not raw.startswith(DEVICE_MAGIC)):
        raise ContractError('unsupported or invalid device work checkpoint')
    size = int.from_bytes(raw[6:10], 'big')
    envelope, encrypted = raw[10:10 + size], raw[10 + size:]
    if (not 387 <= size <= MAX_KEY_BYTES or len(envelope) != size or not envelope.startswith(KEY_MAGIC)
            or not OVERHEAD < len(encrypted) <= MAX_BYTES + OVERHEAD or not encrypted.startswith(MAGIC)):
        raise ContractError('invalid device work framing')
    representation_size = int.from_bytes(envelope[232:234], 'big')
    if not 1 <= representation_size <= 16384 or size != 234 + representation_size + 152:
        raise ContractError('invalid device key representation length')
    return envelope, encrypted


def _content_binding(envelope):
    return hashlib.sha256(DEVICE_MAGIC + len(envelope).to_bytes(4, 'big') + envelope).digest()


class _DeviceCodec:
    max_bytes = MAX_DEVICE_BYTES

    def __init__(self, cipher, project_id, *, recovery_key=None, data_key=None):
        if recovery_key is not None:
            cipher._key(recovery_key)
        if data_key is not None:
            cipher._key(data_key)
        self.cipher, self.binding = cipher, project_binding(project_id)
        self.recovery_key, self.data_key, self.envelope = recovery_key, data_key, None

    def open(self, raw):
        envelope, encrypted = split_device_checkpoint(raw)
        key = self.cipher.open_work_key(envelope, self.binding)
        plaintext = self.cipher.open_device_work(encrypted, key, _content_binding(envelope))
        self.data_key, self.envelope = key, envelope
        return plaintext

    def seal(self, raw):
        if self.envelope is None:
            if self.recovery_key is None:
                raise ContractError('device work must be opened or explicitly initialized')
            key = self.data_key if self.data_key is not None else os.urandom(32)
            envelope = self.cipher.create_work_key(key, self.recovery_key, self.binding)
            self.data_key, self.envelope = key, envelope
            self.recovery_key = None
        encrypted = self.cipher.seal_device_work(raw, self.data_key, _content_binding(self.envelope))
        return DEVICE_MAGIC + len(self.envelope).to_bytes(4, 'big') + self.envelope + encrypted

    def clear(self):
        # Release references, not a claim of Python/native memory zeroization.
        self.data_key = self.recovery_key = self.envelope = None


class DevicePaperWorkStore(PaperWorkStore):
    """Explicit create, ordinary device reopen, or original-preserving restore.

    One ciphertext atomically contains both wrapped-key material and work.
    A missing/locked/unavailable device never silently recreates or recovers it.
    """
    def __init__(self, directory, *, cipher, project_id):
        self._configure(directory, codec=_DeviceCodec(cipher, project_id), project_id=project_id)
        self._expect_new = False

    @classmethod
    def create(cls, directory, *, cipher, project_id, recovery_key):
        result = cls(directory, cipher=cipher, project_id=project_id)
        cipher._key(recovery_key)
        result._codec.recovery_key = recovery_key
        result._expect_new = True
        return result

    def __enter__(self):
        super().__enter__()
        try:
            existing = self._read()
            if self._expect_new and existing is not None:
                raise ContractError('device work creation cannot replace an existing checkpoint')
            if not self._expect_new and existing is None:
                raise ContractError('device work is missing; no key was created')
            self._expect_new = False
        except (OSError, ContractError):
            self.close()
            raise
        return self

    def close(self):
        super().close()
        self._codec.clear()

    def backup(self, *, verify_recovery_key=None):
        """Return only validated encrypted unaccepted work; no automatic export."""
        try:
            self.load()
            raw = self._read()
            if raw is None:
                raise ContractError('no saved work is available for backup')
            if self._fingerprint(raw) != self._last:
                raise ContractError('work changed before backup; reopen and inspect')
            if verify_recovery_key is not None:
                envelope, _ = split_device_checkpoint(raw)
                recovered = self._codec.cipher.recover_work_key(envelope, verify_recovery_key, self._codec.binding)
                if not hmac.compare_digest(recovered, self._codec.data_key):
                    raise ContractError('backup recovery key does not match the open work')
            return raw
        except OSError:
            raise ContractError('encrypted backup could not be read') from None

    @classmethod
    def restore_backup(cls, backup, directory, *, cipher, project_id, recovery_key):
        """Rewrap verified candidate work into a new destination; source stays intact."""
        envelope, encrypted = split_device_checkpoint(backup)
        key = cipher.recover_work_key(envelope, recovery_key, project_binding(project_id))
        work = cls.work_type(cipher.open_device_work(encrypted, key, _content_binding(envelope)))
        if work.project_id != project_id:
            raise ContractError('backup belongs to another project')
        with cls.create(directory, cipher=cipher, project_id=project_id, recovery_key=recovery_key) as store:
            store._codec.data_key = key
            store._save_restored(work)
        return work

    def _save_restored(self, work):
        self.save(work)
