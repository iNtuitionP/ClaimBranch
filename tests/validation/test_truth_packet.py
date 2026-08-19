from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from scripts import check_truth_packet


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPOSITORY_ROOT / "scripts" / "check_truth_packet.py"
CANONICAL_PACKET = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "saturation" / "truth-packet"
)


class TruthPacketCliTests(unittest.TestCase):
    def run_checker(self, packet: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(CHECKER)]
        if packet is not None:
            command.extend(("--packet", str(packet)))
        return subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def create_windows_junction(self, junction: Path, target: Path) -> None:
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            self.skipTest("Windows junction creation is unavailable")

    def write_json_and_refresh_manifest(
        self, packet: Path, name: str, value: object
    ) -> None:
        target = packet / name
        target.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest_path = packet / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["files"] if item["path"] == name)
        entry["sha256"] = sha256(target.read_bytes()).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_canonical_redacted_packet_validates(self) -> None:
        result = self.run_checker()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "P0 source fixture valid: saturation-operator-damage-redacted-v1 "
            "(6 artifacts, 3 observations)\n",
            result.stdout,
        )

    def test_digest_tampering_fails_closed_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            with (packet / "result-summary.json").open("a", encoding="utf-8") as stream:
                stream.write("\n")

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("ERROR: result-summary.json: sha256 mismatch", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unlisted_file_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            (packet / "private-notes.txt").write_text(
                "must not enter a committed packet\n", encoding="utf-8"
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: private-notes.txt: unexpected file", result.stderr)

    def test_symlinked_artifact_is_rejected_without_following_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            target = root / "outside.json"
            target.write_text('{"outside":true}\n', encoding="utf-8")
            artifact = packet / "result-summary.json"
            artifact.unlink()
            try:
                os.symlink(target, artifact)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item for item in manifest["files"] if item["path"] == artifact.name
            )
            entry["sha256"] = sha256(target.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json: symlink or junction is forbidden",
            result.stderr,
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_junctioned_packet_root_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "real-packet"
            shutil.copytree(CANONICAL_PACKET, target)
            junction = root / "junction-packet"
            self.create_windows_junction(junction, target)

            result = self.run_checker(junction)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: truth packet directory cannot be a symlink or junction",
            result.stderr,
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_junctioned_artifact_is_rejected_without_following_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            artifact = packet / "result-summary.json"
            artifact.unlink()
            target = root / "outside-directory"
            target.mkdir()
            (target / "private.json").write_text(
                '{"outside":true}\n', encoding="utf-8"
            )
            self.create_windows_junction(artifact, target)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json: symlink or junction is forbidden",
            result.stderr,
        )

    def test_oversized_artifact_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            artifact = packet / "result-summary.json"
            artifact.write_text(
                artifact.read_text(encoding="utf-8") + (" " * 65536),
                encoding="utf-8",
            )
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item for item in manifest["files"] if item["path"] == artifact.name
            )
            entry["sha256"] = sha256(artifact.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json: exceeds 65536-byte limit", result.stderr
        )

    def test_oversized_manifest_is_rejected_before_content_read(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest = packet / "manifest.json"
            manifest.write_bytes(b"x" * (check_truth_packet.MAX_ARTIFACT_BYTES + 1))
            validator = check_truth_packet.TruthPacketValidator(packet)

            with mock.patch.object(
                Path,
                "open",
                side_effect=AssertionError("oversized file content was read"),
            ):
                value = validator.load_json("manifest.json")

        self.assertIsNone(value)
        self.assertEqual(
            ["manifest.json: exceeds 65536-byte limit"], validator.errors
        )

    def test_verified_bytes_are_reused_for_semantic_validation(self) -> None:
        validator = check_truth_packet.TruthPacketValidator(CANONICAL_PACKET)
        manifest = validator.load_json("manifest.json")
        entries = validator.validate_manifest(manifest)
        verified = validator.validate_inventory(entries)
        self.assertIn("truth-packet.json", verified)

        with mock.patch.object(
            validator,
            "read_bounded_bytes",
            side_effect=AssertionError("verified artifact was read a second time"),
        ):
            packet = validator.load_json("truth-packet.json")

        self.assertIsInstance(packet, dict)

    def test_manifest_path_cannot_escape_packet_directory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            outside = root / "outside.txt"
            outside.write_text("outside packet\n", encoding="utf-8")
            manifest_path = packet / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["path"] = "../outside.txt"
            manifest["files"][0]["sha256"] = sha256(outside.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: ../outside.txt: unsafe relative path", result.stderr)

    def test_duplicate_json_key_is_rejected_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest_path = packet / "manifest.json"
            text = manifest_path.read_text(encoding="utf-8").replace(
                '"schema_version": 1,',
                '"schema_version": 1,\n  "schema_version": 1,',
                1,
            )
            manifest_path.write_text(text, encoding="utf-8")

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: manifest.json: duplicate key 'schema_version'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_excessive_json_nesting_fails_closed_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest_path = packet / "manifest.json"
            manifest_text = manifest_path.read_text(encoding="utf-8").rstrip()
            nested_value = ("[" * 1100) + "null" + ("]" * 1100)
            manifest_path.write_text(
                manifest_text[:-1] + f',\n  "deep": {nested_value}\n}}\n',
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: manifest.json: JSON nesting is too deep", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_manifest_rejects_unknown_fields(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest_path = packet / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["remote_url"] = "https://example.invalid/private"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: manifest.json: unexpected keys: remote_url", result.stderr)

    def test_malformed_manifest_entry_fails_closed_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest_path = packet / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0] = "truth-packet.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: manifest.json files[0]: expected an object", result.stderr
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_manifest_requires_the_exact_artifact_role_map(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            manifest_path = packet / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["role"] = "result-artifact"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: truth-packet.json: role must be truth-contract", result.stderr
        )

    def test_unexpected_directory_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            (packet / "private-material").mkdir()

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR: private-material: unexpected entry", result.stderr)

    def test_schema_version_must_be_exact_integer_one(self) -> None:
        for invalid in (2, True):
            with self.subTest(invalid=invalid), TemporaryDirectory() as directory:
                packet = Path(directory) / "truth-packet"
                shutil.copytree(CANONICAL_PACKET, packet)
                manifest_path = packet / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["schema_version"] = invalid
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_checker(packet)

            self.assertEqual(1, result.returncode)
            self.assertIn(
                f"ERROR: manifest.json: unsupported schema_version {invalid}",
                result.stderr,
            )

    def test_requires_exactly_three_observations(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["observations"].pop()
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: truth-packet.json observations: expected exactly 3, found 2",
            result.stderr,
        )

    def test_observation_must_reference_the_single_run(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["observations"][0]["run_id"] = "R-OTHER"
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: observation O-01: run_id does not match R-01", result.stderr
        )

    def test_result_summary_must_match_truth_packet_observations(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            summary = json.loads(
                (packet / "result-summary.json").read_text(encoding="utf-8")
            )
            summary["measurements"][0]["expected"] = True
            self.write_json_and_refresh_manifest(packet, "result-summary.json", summary)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json O-01: expected does not match truth packet",
            result.stderr,
        )

    def test_baseline_must_remain_blank_and_suggestion_free(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            baseline = packet / "decision-log-baseline.md"
            baseline.write_text(
                baseline.read_text(encoding="utf-8").replace("- [ ]", "- [x]", 1),
                encoding="utf-8",
            )
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item
                for item in manifest["files"]
                if item["path"] == "decision-log-baseline.md"
            )
            entry["sha256"] = sha256(baseline.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: decision-log-baseline.md: checked answers are forbidden",
            result.stderr,
        )

    def test_baseline_requires_the_suggestion_free_contract_marker(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            baseline = packet / "decision-log-baseline.md"
            baseline.write_text(
                baseline.read_text(encoding="utf-8").replace(
                    "<!-- claimbranch-suggestions: forbidden -->\n", ""
                ),
                encoding="utf-8",
            )
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item
                for item in manifest["files"]
                if item["path"] == "decision-log-baseline.md"
            )
            entry["sha256"] = sha256(baseline.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: decision-log-baseline.md: required marker is missing: "
            "claimbranch-suggestions: forbidden",
            result.stderr,
        )

    def test_baseline_requires_every_frozen_response_field(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            baseline = packet / "decision-log-baseline.md"
            baseline.write_text(
                baseline.read_text(encoding="utf-8").replace(
                    "- Local artifact digest:\n", ""
                ),
                encoding="utf-8",
            )
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item
                for item in manifest["files"]
                if item["path"] == "decision-log-baseline.md"
            )
            entry["sha256"] = sha256(baseline.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: decision-log-baseline.md: response fields do not match "
            "the frozen template",
            result.stderr,
        )

    def test_crlf_baseline_is_semantically_equivalent(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            baseline = packet / "decision-log-baseline.md"
            baseline.write_bytes(baseline.read_bytes().replace(b"\n", b"\r\n"))
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item
                for item in manifest["files"]
                if item["path"] == "decision-log-baseline.md"
            )
            entry["sha256"] = sha256(baseline.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(0, result.returncode, result.stderr)

    def test_absolute_user_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["run"]["method_ref"] = "C:\\Users\\researcher\\private.py"
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: truth-packet.json $.run.method_ref: absolute path is forbidden",
            result.stderr,
        )

    def test_embedded_absolute_user_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            proposal = json.loads(
                (packet / "frozen-proposal.json").read_text(encoding="utf-8")
            )
            proposal["normalized_text"] = (
                "Redacted result copied from C:\\Users\\researcher\\private.txt"
            )
            self.write_json_and_refresh_manifest(packet, "frozen-proposal.json", proposal)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: frozen-proposal.json $.normalized_text: absolute path is forbidden",
            result.stderr,
        )

    def test_rooted_windows_and_file_uri_paths_are_rejected(self) -> None:
        unsafe_paths = (
            "\\Users\\researcher\\private.txt",
            "file:///C:/Users/researcher/private.txt",
            "file:///home/researcher/private.txt",
        )
        for unsafe_path in unsafe_paths:
            with self.subTest(path=unsafe_path), TemporaryDirectory() as directory:
                packet = Path(directory) / "truth-packet"
                shutil.copytree(CANONICAL_PACKET, packet)
                contract = json.loads(
                    (packet / "truth-packet.json").read_text(encoding="utf-8")
                )
                contract["run"]["method_ref"] = unsafe_path
                self.write_json_and_refresh_manifest(
                    packet, "truth-packet.json", contract
                )

                result = self.run_checker(packet)

            self.assertEqual(1, result.returncode)
            self.assertIn(
                "ERROR: truth-packet.json $.run.method_ref: absolute path is forbidden",
                result.stderr,
            )

    def test_secret_like_content_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            proposal = json.loads(
                (packet / "frozen-proposal.json").read_text(encoding="utf-8")
            )
            proposal["normalized_text"] = "Bearer sk-example-secret-value-1234567890"
            self.write_json_and_refresh_manifest(packet, "frozen-proposal.json", proposal)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: frozen-proposal.json $.normalized_text: secret-like content is forbidden",
            result.stderr,
        )

    def test_frozen_proposal_cannot_require_a_live_provider(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            proposal = json.loads(
                (packet / "frozen-proposal.json").read_text(encoding="utf-8")
            )
            proposal["live_provider_required"] = True
            self.write_json_and_refresh_manifest(packet, "frozen-proposal.json", proposal)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: frozen-proposal.json: live_provider_required must be false",
            result.stderr,
        )

    def test_frozen_proposal_requires_a_json_boolean_provider_flag(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            proposal = json.loads(
                (packet / "frozen-proposal.json").read_text(encoding="utf-8")
            )
            proposal["live_provider_required"] = 0
            self.write_json_and_refresh_manifest(packet, "frozen-proposal.json", proposal)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: frozen-proposal.json: live_provider_required must be false",
            result.stderr,
        )

    def test_manuscript_files_require_the_same_complete_marker_pair(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            after = packet / "manuscript-after.tex"
            after.write_text(
                after.read_text(encoding="utf-8").replace(
                    "claimbranch:end id=anchor-central-claim",
                    "claimbranch:end id=other-anchor",
                ),
                encoding="utf-8",
            )
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item for item in manifest["files"] if item["path"] == after.name
            )
            entry["sha256"] = sha256(after.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: manuscript-after.tex: expected exactly one complete marker pair "
            "for anchor-central-claim",
            result.stderr,
        )

    def test_manuscript_replacement_must_change_the_marked_content(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            before = packet / "manuscript-before.tex"
            after = packet / "manuscript-after.tex"
            after.write_bytes(before.read_bytes())
            manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item for item in manifest["files"] if item["path"] == after.name
            )
            entry["sha256"] = sha256(after.read_bytes()).hexdigest()
            (packet / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: manuscript-after.tex: marked replacement must differ from before",
            result.stderr,
        )

    def test_compiler_command_is_part_of_the_frozen_contract(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["manuscript"]["compiler_argv"] = [
                "pdflatex",
                "manuscript-before.tex",
            ]
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: manuscript: compiler_argv does not match the frozen command",
            result.stderr,
        )

    def test_expected_impact_relationships_must_match_observations(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["expected_impact"]["relationship_truth_set"][0]["type"] = (
                "supports"
            )
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: expected impact relationship for O-01 does not match observation",
            result.stderr,
        )

    def test_expected_impact_must_cover_every_observation_exactly_once(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["expected_impact"]["relationship_truth_set"].pop()
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: expected impact relationships must cover O-01, O-02, O-03 "
            "exactly once",
            result.stderr,
        )

    def test_unhashable_nested_id_fails_closed_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            contract = json.loads(
                (packet / "truth-packet.json").read_text(encoding="utf-8")
            )
            contract["expected_impact"]["relationship_truth_set"][0][
                "source_id"
            ] = []
            self.write_json_and_refresh_manifest(packet, "truth-packet.json", contract)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: expected impact relationship 1: source_id must be a string",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_result_summary_run_and_operators_must_match_truth_packet(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            summary = json.loads(
                (packet / "result-summary.json").read_text(encoding="utf-8")
            )
            summary["run_id"] = "R-OTHER"
            summary["measurements"][0]["operator"] = "compression"
            self.write_json_and_refresh_manifest(packet, "result-summary.json", summary)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json: run_id does not match truth packet",
            result.stderr,
        )
        self.assertIn(
            "ERROR: result-summary.json O-01: operator does not match truth packet",
            result.stderr,
        )

    def test_unhashable_result_observation_id_fails_closed_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            packet = Path(directory) / "truth-packet"
            shutil.copytree(CANONICAL_PACKET, packet)
            summary = json.loads(
                (packet / "result-summary.json").read_text(encoding="utf-8")
            )
            summary["measurements"][0]["observation_id"] = {}
            self.write_json_and_refresh_manifest(packet, "result-summary.json", summary)

            result = self.run_checker(packet)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "ERROR: result-summary.json measurement 1: observation_id must be a string",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
