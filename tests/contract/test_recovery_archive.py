"""Recovery preserves candidate bytes; replay and a checksum grant no authority."""
import hashlib
import struct
import unittest

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.recovery import MAX_ARCHIVE_BYTES, pack_history, unpack_history
from claimbranch.fixtures import replay_example


class RecoveryArchiveTests(unittest.TestCase):
    def test_all_history_profiles_preserve_exact_bytes_and_remain_candidates(self):
        for flags in ({}, {"paper": True}, {"series": True}):
            for variant in ("manual", "recorded"):
                with self.subTest(flags=flags, variant=variant):
                    history = replay_example(variant, **flags)
                    restored = unpack_history(pack_history(history),
                        expected_project_id=decode(history.seed)["project_id"],
                        expected_manifest_digest=hashlib.sha256(history.manifest()).hexdigest())
                    self.assertEqual(history.seed, restored.seed)
                    self.assertEqual(history.commands, restored.commands)
                    self.assertEqual(history.manifest(), restored.manifest())
                    self.assertFalse(restored.authorization_verified)

    def test_wrong_project_or_independent_snapshot_expectation_is_rejected(self):
        history = replay_example()
        raw = pack_history(history)
        project = decode(history.seed)["project_id"]
        for other_project, manifest in (("other-project", None), (project, "0" * 64), (project, True)):
            with self.subTest(project=other_project, manifest=manifest), self.assertRaises(ContractError):
                unpack_history(raw, expected_project_id=other_project, expected_manifest_digest=manifest)

    def test_framing_corruption_and_replay_manifest_changes_are_rejected(self):
        history = replay_example()
        raw = pack_history(history)
        project = decode(history.seed)["project_id"]
        candidates = [b"", bytearray(raw), raw[:-1], raw + b"x", b"CBRH\x00\x02" + raw[6:],
                      raw[:6] + struct.pack(">II", 2**32 - 1, 0) + raw[14:],
                      raw[:10] + struct.pack(">I", 65) + raw[14:],
                      raw[:-32] + bytes(32), bytes(MAX_ARCHIVE_BYTES + 1)]
        # A malformed seed must fail replay even when the framing is intact.
        broken = bytearray(raw)
        broken[14] = ord("!")
        candidates.append(bytes(broken))
        for index, candidate in enumerate(candidates):
            with self.subTest(index=index), self.assertRaises(ContractError):
                unpack_history(candidate, expected_project_id=project)

    def test_every_truncated_frame_is_rejected(self):
        from claimbranch.core.research_history import ResearchHistory
        history = ResearchHistory.start("p", "e", "c", "Synthetic claim", "a")
        raw = pack_history(history)
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(ContractError):
                unpack_history(raw[:size], expected_project_id="p")

    def test_archive_without_external_snapshot_expectation_is_only_a_candidate(self):
        history = replay_example("recorded", series=True)
        restored = unpack_history(pack_history(history), expected_project_id=decode(history.seed)["project_id"])
        self.assertFalse(restored.authorization_verified)
        with self.assertRaises(ContractError):
            pack_history({"authorization_verified": True})


if __name__ == "__main__":
    unittest.main()
