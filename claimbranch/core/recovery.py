"""Bounded, exact-byte candidate-history archive for recovery experiments.

This codec provides neither encryption nor accepted-history authentication.
Successful replay and the embedded digest only check internal consistency.
An external expected digest can pin a known snapshot, but supplies no authority.
No private signing key, raw artifact, UI draft or active approval is included.
"""
import hashlib
import struct

from .canonical import ContractError, MAX_BYTES, decode, digest_text, identifier
from .research_history import ResearchHistory
from .research_schema import PAPER_LIMITS


MAGIC = b"CBRH\x00\x01"
MAX_ARCHIVE_BYTES = MAX_BYTES + len(MAGIC) + 8 + 4 * PAPER_LIMITS["commands"] + 32


def pack_history(history):
    if type(history) is not ResearchHistory:
        raise ContractError("a finite candidate history is required")
    frames = [MAGIC, struct.pack(">II", len(history.seed), len(history.commands)), history.seed]
    for command in history.commands:
        frames.extend((struct.pack(">I", len(command)), command))
    frames.append(hashlib.sha256(history.manifest()).digest())
    raw = b"".join(frames)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ContractError("candidate recovery archive exceeds its bound")
    return raw


def unpack_history(raw, *, expected_project_id, expected_manifest_digest=None):
    identifier(expected_project_id)
    if expected_manifest_digest is not None:
        digest_text(expected_manifest_digest)
    if type(raw) is not bytes or not 46 <= len(raw) <= MAX_ARCHIVE_BYTES or not raw.startswith(MAGIC):
        raise ContractError("unknown or unbounded candidate recovery archive")
    seed_size, count = struct.unpack(">II", raw[6:14])
    if not 0 < seed_size <= MAX_BYTES or count > PAPER_LIMITS["commands"]:
        raise ContractError("candidate archive frame limit exceeded")
    end = len(raw) - 32
    offset = 14

    def take(size):
        nonlocal offset
        if not 0 < size <= MAX_BYTES or offset + size > end:
            raise ContractError("candidate archive is truncated or malformed")
        value = raw[offset:offset + size]
        offset += size
        return value

    seed = take(seed_size)
    commands = []
    for _ in range(count):
        size = struct.unpack(">I", take(4))[0]
        commands.append(take(size))
    if offset != end:
        raise ContractError("candidate archive has trailing data")
    # Replay validates every schema and transition; framing cannot supply trust.
    history = ResearchHistory.replay(seed, tuple(commands))
    if decode(history.seed)["project_id"] != expected_project_id:
        raise ContractError("candidate archive belongs to another project")
    actual = hashlib.sha256(history.manifest()).digest()
    if actual != raw[end:]:
        raise ContractError("candidate replay differs from the archived manifest")
    if expected_manifest_digest is not None and actual.hex() != expected_manifest_digest:
        raise ContractError("candidate archive differs from the expected snapshot")
    return history
