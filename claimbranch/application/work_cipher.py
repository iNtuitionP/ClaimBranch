"""macOS encryption and data-key wrapping for unaccepted work. No approval authority.

The raw-key API uses a caller-owned 32-byte key. Separate device methods wrap
that data key with Secure Enclave key agreement and a recovery secret. Secrets
cross stdin/stdout pipes only, never arguments. No signing key is exposed; the
helper has no file, Keychain-search, provider or foreground-approval operations.
Building is explicit through this context manager and requires installed Xcode
command-line tools. No binary, key or plaintext is cached in the workspace.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

from claimbranch.core.canonical import ContractError, MAX_BYTES


MAGIC = b'CBWK\x00\x01'
OVERHEAD = 66
KEY_MAGIC = b'CBKY\x00\x01'
MAX_KEY_BYTES = 16770


class MacWorkCipher:
    def __init__(self):
        self._temporary = None
        self._binary = None

    def __enter__(self):
        if sys.platform != 'darwin' or self._temporary is not None:
            raise ContractError('a fresh macOS work cipher is required')
        self._temporary = tempfile.TemporaryDirectory(prefix='claimbranch-work-cipher-')
        self._binary = Path(self._temporary.name) / 'work-cipher'
        try:
            result = subprocess.run(['/usr/bin/xcrun', 'swiftc',
                str(Path(__file__).with_name('native') / 'WorkCipher.swift'), '-o', str(self._binary)],
                capture_output=True, timeout=90)
            if result.returncode:
                raise ContractError('work encryption helper could not be built')
            if self._run('check', b'') != b'work-crypto-ok\n':
                raise ContractError('work encryption self-check failed')
        except (OSError, subprocess.SubprocessError, ContractError):
            self.__exit__(None, None, None)
            raise ContractError('macOS work encryption is unavailable') from None
        return self

    def __exit__(self, *_):
        if self._temporary is not None:
            self._temporary.cleanup()
        self._temporary = self._binary = None

    def _run(self, mode, raw):
        if self._binary is None:
            raise ContractError('work cipher is closed')
        try:
            result = subprocess.run([str(self._binary), mode], input=raw,
                                    capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            raise ContractError('work encryption failed') from None
        if result.returncode:
            raise ContractError('work encryption or authentication failed')
        return result.stdout

    @staticmethod
    def _key(key):
        if type(key) is not bytes or len(key) != 32:
            raise ContractError('work encryption requires a 32-byte key')

    def seal(self, raw, key):
        self._key(key)
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
            raise ContractError('bounded work bytes required')
        result = self._run('seal', key + raw)
        if len(result) != len(raw) + OVERHEAD or not result.startswith(MAGIC):
            raise ContractError('invalid encrypted work output')
        return result

    def open(self, raw, key):
        self._key(key)
        if (type(raw) is not bytes or not OVERHEAD < len(raw) <= MAX_BYTES + OVERHEAD
                or not raw.startswith(MAGIC)):
            raise ContractError('unsupported or invalid encrypted work')
        result = self._run('open', key + raw)
        if len(result) != len(raw) - OVERHEAD:
            raise ContractError('invalid decrypted work output')
        return result

    def create_work_key(self, data_key, recovery_key, binding):
        """Wrap a data key with a new device key and a separate recovery secret."""
        for value in (data_key, recovery_key, binding):
            self._key(value)
        result = self._run('key-create', binding + data_key + recovery_key)
        self._envelope(result)
        return result

    @staticmethod
    def _envelope(raw):
        if type(raw) is not bytes or not 387 <= len(raw) <= MAX_KEY_BYTES or not raw.startswith(KEY_MAGIC):
            raise ContractError('invalid work key envelope')

    def open_work_key(self, envelope, binding):
        self._key(binding)
        self._envelope(envelope)
        result = self._run('key-open', binding + envelope)
        self._key(result)
        return result

    def recover_work_key(self, envelope, recovery_key, binding):
        self._key(binding)
        self._key(recovery_key)
        self._envelope(envelope)
        result = self._run('key-recover', binding + recovery_key + envelope)
        self._key(result)
        return result

    def _device_work(self, mode, raw, key, binding):
        self._key(key)
        self._key(binding)
        sealing = mode == 'work-seal-bound'
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES + (0 if sealing else OVERHEAD):
            raise ContractError('bounded device work bytes required')
        if not sealing and (len(raw) <= OVERHEAD or not raw.startswith(MAGIC)):
            raise ContractError('invalid device work ciphertext')
        result = self._run(mode, binding + key + raw)
        if len(result) != len(raw) + (OVERHEAD if sealing else -OVERHEAD):
            raise ContractError('invalid device work output')
        if sealing and not result.startswith(MAGIC):
            raise ContractError('invalid device work ciphertext')
        return result

    def seal_device_work(self, raw, key, binding):
        return self._device_work('work-seal-bound', raw, key, binding)

    def open_device_work(self, raw, key, binding):
        return self._device_work('work-open-bound', raw, key, binding)
