"""Exact unaccepted review delivery through the source-built native roles.

The build pin is still caller-held, not enrolled trust. Transport observations
never establish key custody, human presence, receipt consumption or accepted
storage. Only synthetic reviews are currently supported. Nothing is persisted.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from .mac_runtime import _directory, _run, check_runtime
from .paper_review_policy import PaperReviewPolicy


def deliver_operation_review(directory, expected_build, policy, review, *, current_context):
    """Recheck owned review and caller-observed context before/after transport.

    current_context reloads manuscript_digest, session_nonce and now on each
    call. This API does not itself read a manuscript or confer source fidelity.
    A changed or expired review cannot produce a successful application result,
    even if the earlier bytes reached the other process. Later acceptance must
    independently reload trusted sources and obtain a fresh human receipt.
    """
    if type(policy) is not PaperReviewPolicy or not callable(current_context):
        raise ContractError('owned review policy and current context reader required')
    def current():
        context = current_context()
        if type(context) is not dict or set(context) != {'manuscript_digest', 'session_nonce', 'now'}:
            raise ContractError('exact current review context required')
        return policy.operation_candidate(review, **context)
    candidate = current()
    raw = secrets.token_bytes(32) + review.payload
    _exchange(directory, expected_build, raw)
    if current() != candidate:
        raise ContractError('operation review changed during delivery')
    return {'status': 'delivered-unaccepted-review', 'review_digest': review.digest,
            'operation_digest': candidate.digest, 'exchange_digest': hashlib.sha256(raw).hexdigest(),
            'authorization_verified': False, 'protected_acceptance_available': False}


def _exchange(directory, expected_build, raw):
    try:
        _exchange_checked(directory, expected_build, raw)
    except OSError:
        raise ContractError('native review delivery I/O failed; no authority was granted') from None


def _exchange_checked(directory, expected_build, raw):
    if type(raw) is not bytes or not 33 <= len(raw) <= 262176:
        raise ContractError('bounded review and fresh exchange nonce required')
    checked = check_runtime(directory, expected_build)
    path = Path(directory).resolve(strict=True)
    # Darwin unistd.h: _CS_DARWIN_USER_TEMP_DIR=65537. Python does not expose
    # its symbolic name. Do not depend on shared /tmp or inherited TMPDIR.
    base = os.confstr(65537)
    if not base:
        raise ContractError('private native temporary root is unavailable')
    with _directory(base):
        pass
    with tempfile.TemporaryDirectory(prefix='cb-ipc-', dir=base) as temporary:
        root = Path(temporary)
        with _directory(root):
            socket_path = root / 's'
            expected = hashlib.sha256(raw).hexdigest()
            def command(role):
                other = 'broker' if role == 'gateway' else 'gateway'
                return [str(path / role), 'receive-review' if role == 'gateway' else 'send-review',
                        str(socket_path), checked['roles'][other]['code_hash']]
            with ThreadPoolExecutor(max_workers=1) as pool:
                receiver = pool.submit(_run, command('gateway'), cwd=root, input_bytes=raw,
                                       timeout=12, limit=4096)
                deadline = time.monotonic() + 5
                while True:
                    if receiver.done():
                        receiver.result()
                        raise ContractError('native review receiver exited before delivery')
                    try:
                        info = socket_path.lstat()
                    except FileNotFoundError:
                        if time.monotonic() >= deadline:
                            raise ContractError('native review receiver did not become ready')
                        time.sleep(.01)
                        continue
                    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
                            or stat.S_IMODE(info.st_mode) != 0o700):
                        raise ContractError('native review socket identity is invalid')
                    break
                # Keep expensive code-signing preflight outside the eight-second
                # native exchange. Both peers enforce the exact observed code
                # at connect; recheck disk/source identity after completion.
                if receiver.done():
                    receiver.result()
                    raise ContractError('native review receiver exited before delivery')
                sender = _run(command('broker'), cwd=root, input_bytes=raw, timeout=12, limit=4096)
                received = receiver.result()
            for role, (output, errors) in [('broker', sender), ('gateway', received)]:
                wanted = {'schema': 'claimbranch.native-review-delivery/v1', 'role': role,
                          'status': 'delivered-unaccepted-review', 'exchange_digest': expected,
                          'byte_count': len(raw), 'peer_verified': True,
                          'authorization_verified': False, 'protected_acceptance_available': False}
                if errors or canonical_bytes(decode(output)) != canonical_bytes(wanted):
                    raise ContractError('native review delivery did not match the exact exchange')
            if socket_path.exists() or socket_path.is_symlink():
                raise ContractError('native review channel cleanup is incomplete')
            check_runtime(path, expected_build)
