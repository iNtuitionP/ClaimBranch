"""Experimental signed-candidate framing, without trust bootstrapping or approval.

Parsing is not signature verification. A native verifier must check the returned
message/public key/signature before use. External pins never come from this file.
Neither a verified signature nor restored bytes confer scientific acceptance.
"""
from dataclasses import dataclass
import hashlib
import struct

from .canonical import ContractError, canonical_bytes, decode, digest_text, identifier
from .recovery import MAX_ARCHIVE_BYTES, pack_history, unpack_history
from .research_history import ResearchHistory


MAGIC = b"CBRS\x00\x01"
MAX_CHECKPOINT_BYTES = 1024
MAX_SIGNED_BYTES = 79 + MAX_ARCHIVE_BYTES + MAX_CHECKPOINT_BYTES + 72


def checkpoint_message(history, checkpoint_id):
    identifier(checkpoint_id)
    archive = pack_history(history)
    message = canonical_bytes({
        "format": "claimbranch-recovery-checkpoint/v1", "classification": "candidate-history",
        "project_id": decode(history.seed)["project_id"], "checkpoint_id": checkpoint_id,
        "archive_digest": hashlib.sha256(archive).hexdigest(),
        "manifest_digest": hashlib.sha256(history.manifest()).hexdigest(),
        "operation_count": len(history.commands)})
    if len(message) > MAX_CHECKPOINT_BYTES:
        raise ContractError("recovery checkpoint exceeds its byte limit")
    return message


def signature_fields(public_key, signature):
    if (type(public_key) is not bytes or len(public_key) != 65 or public_key[0] != 4
            or type(signature) is not bytes or not 8 <= len(signature) <= 72):
        raise ContractError("bounded uncompressed P-256 public key and DER signature required")


@dataclass(frozen=True, repr=False)
class ParsedSignedHistory:
    history: ResearchHistory
    message: bytes
    public_key: bytes
    signature: bytes

    @property
    def signature_verified(self):
        return False

    @property
    def authorization_verified(self):
        return False


def pack_signed_history(history, checkpoint_id, public_key, signature):
    """Frame an unverified signature supplied by an explicit signer; never sign."""
    signature_fields(public_key, signature)
    archive = pack_history(history)
    message = checkpoint_message(history, checkpoint_id)
    return (MAGIC + struct.pack(">IHH", len(archive), len(message), len(signature))
            + public_key + archive + message + signature)


def unpack_signed_history(raw, *, expected_project_id, expected_signer_digest,
                          expected_checkpoint_digest):
    identifier(expected_project_id)
    digest_text(expected_signer_digest)
    digest_text(expected_checkpoint_digest)
    if (type(raw) is not bytes or not 134 <= len(raw) <= MAX_SIGNED_BYTES
            or not raw.startswith(MAGIC)):
        raise ContractError("unknown or unbounded signed candidate archive")
    archive_size, message_size, signature_size = struct.unpack(">IHH", raw[6:14])
    if (not 46 <= archive_size <= MAX_ARCHIVE_BYTES or not 1 <= message_size <= MAX_CHECKPOINT_BYTES
            or not 8 <= signature_size <= 72 or 79 + archive_size + message_size + signature_size != len(raw)):
        raise ContractError("signed candidate framing is malformed")
    public_key = raw[14:79]
    archive_end, message_end = 79 + archive_size, 79 + archive_size + message_size
    archive, message, signature = raw[79:archive_end], raw[archive_end:message_end], raw[message_end:]
    signature_fields(public_key, signature)
    if hashlib.sha256(public_key).hexdigest() != expected_signer_digest:
        raise ContractError("archive signer differs from the trusted external key")
    if hashlib.sha256(message).hexdigest() != expected_checkpoint_digest:
        raise ContractError("archive differs from the expected signed checkpoint")
    value = decode(message)
    if type(value) is not dict:
        raise ContractError("checkpoint must be an object")
    history = unpack_history(archive, expected_project_id=expected_project_id)
    if message != checkpoint_message(history, value.get("checkpoint_id")):
        raise ContractError("checkpoint does not bind this exact candidate history")
    return ParsedSignedHistory(history, message, public_key, signature)
