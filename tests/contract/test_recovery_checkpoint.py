"""A parsed or signed candidate never establishes scientific acceptance."""
import hashlib
import json
import struct
import unittest

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.recovery import pack_history
from claimbranch.core.recovery_checkpoint import (MAX_SIGNED_BYTES, checkpoint_message,
    pack_signed_history, unpack_signed_history)
from claimbranch.fixtures import replay_example


class CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = replay_example("recorded", series=True)
        cls.public = b"\x04" + bytes(64)  # Structural fixture; NOT a valid curve point.
        cls.signature = b"\x30" + bytes(69)  # Parsing does not verify this signature.
        cls.message = checkpoint_message(cls.history, "checkpoint-1")
        cls.raw = pack_signed_history(cls.history, "checkpoint-1", cls.public, cls.signature)
        cls.expected = {"expected_project_id": decode(cls.history.seed)["project_id"],
            "expected_signer_digest": hashlib.sha256(cls.public).hexdigest(),
            "expected_checkpoint_digest": hashlib.sha256(cls.message).hexdigest()}

    def test_checkpoint_binds_exact_history_and_immutable_original_signature(self):
        parsed = unpack_signed_history(self.raw, **self.expected)
        value = decode(parsed.message)
        self.assertEqual("claimbranch-recovery-checkpoint/v1", value["format"])
        self.assertEqual("candidate-history", value["classification"])
        self.assertEqual(hashlib.sha256(pack_history(self.history)).hexdigest(), value["archive_digest"])
        self.assertEqual(hashlib.sha256(self.history.manifest()).hexdigest(), value["manifest_digest"])
        self.assertEqual(len(self.history.commands), value["operation_count"])
        self.assertEqual(self.history.commands, parsed.history.commands)
        self.assertEqual(self.public, parsed.public_key)
        self.assertEqual(self.signature, parsed.signature)
        self.assertFalse(parsed.authorization_verified)
        self.assertFalse(parsed.signature_verified)

    def test_trust_and_snapshot_pins_cannot_be_adopted_from_archive(self):
        for field, wrong in (("expected_project_id", "other-project"),
                             ("expected_signer_digest", "0" * 64),
                             ("expected_checkpoint_digest", "0" * 64),
                             ("expected_signer_digest", None),
                             ("expected_checkpoint_digest", None)):
            with self.subTest(field=field, wrong=wrong), self.assertRaises(ContractError):
                unpack_signed_history(self.raw, **{**self.expected, field: wrong})

    def test_unsigned_downgrade_and_malformed_frames_are_rejected(self):
        invalid = [pack_history(self.history), b"", bytearray(self.raw), self.raw[:-1],
                   self.raw + b"x", bytes(MAX_SIGNED_BYTES + 1), b"CBRS\x00\x02" + self.raw[6:],
                   self.raw[:6] + struct.pack(">IHH", 2**32 - 1, 1, 8) + self.raw[14:]]
        for index, raw in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(ContractError):
                unpack_signed_history(raw, **self.expected)

    def test_recomputed_external_hash_does_not_make_inconsistent_checkpoint_valid(self):
        archive = pack_history(self.history)
        for field, value in (("archive_digest", "0" * 64), ("manifest_digest", "0" * 64),
                             ("operation_count", True), ("classification", "accepted-history"),
                             ("unexpected", "extra")):
            message = json.loads(self.message)
            message[field] = value
            raw_message = json.dumps(message, sort_keys=True, separators=(",", ":")).encode()
            raw = (b"CBRS\x00\x01" + struct.pack(">IHH", len(archive), len(raw_message), len(self.signature))
                   + self.public + archive + raw_message + self.signature)
            with self.subTest(field=field), self.assertRaises(ContractError):
                unpack_signed_history(raw, **{**self.expected,
                    "expected_checkpoint_digest": hashlib.sha256(raw_message).hexdigest()})

    def test_noncanonical_checkpoint_and_duplicate_fields_are_rejected(self):
        archive = pack_history(self.history)
        for message in (json.dumps(json.loads(self.message), indent=2).encode(),
                        self.message[:-1] + b',"checkpoint_id":"checkpoint-1"}'):
            raw = (b"CBRS\x00\x01" + struct.pack(">IHH", len(archive), len(message), len(self.signature))
                   + self.public + archive + message + self.signature)
            with self.assertRaises(ContractError):
                unpack_signed_history(raw, **{**self.expected,
                    "expected_checkpoint_digest": hashlib.sha256(message).hexdigest()})

    def test_signature_parser_bounds_do_not_validate_cryptography(self):
        for public, signature in ((bytes(65), self.signature), (self.public[:-1], self.signature),
                                  (self.public, b""), (self.public, bytes(73))):
            with self.assertRaises(ContractError):
                pack_signed_history(self.history, "checkpoint-1", public, signature)
        parsed = unpack_signed_history(self.raw, **self.expected)
        self.assertFalse(parsed.signature_verified)


if __name__ == "__main__":
    unittest.main()
