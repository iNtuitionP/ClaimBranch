#!/usr/bin/env python3
"""Validate the committed partial P0 saturation source fixture."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "tests" / "fixtures" / "saturation" / "truth-packet"
MAX_ARTIFACT_BYTES = 65_536
SCHEMA_VERSION = 1

ARTIFACT_ROLES = {
    "truth-packet.json": "truth-contract",
    "result-summary.json": "result-artifact",
    "manuscript-before.tex": "manuscript-before",
    "manuscript-after.tex": "manuscript-after",
    "frozen-proposal.json": "frozen-proposal",
    "decision-log-baseline.md": "v0-baseline",
}
OPERATORS = ("pruning", "quantization", "compression")
OBSERVATION_TRUTH = {
    "O-01": ("pruning", False, "challenges", "challenge"),
    "O-02": ("quantization", False, "challenges", "challenge"),
    "O-03": ("compression", True, "qualifies", "conditional-support"),
}
BASELINE_MARKERS = (
    "claimbranch-baseline-version: 1",
    "claimbranch-suggestions: forbidden",
)
BASELINE_HEADINGS = (
    "# V0 decision-log baseline",
    "## Eligibility",
    "## Evidence and interpretation",
    "## Decision and manuscript consequence",
    "## Measurements",
    "## Privacy-safe completion record",
)
BASELINE_CHECKBOXES = (
    "- [ ] The result was produced after preregistration.",
    "- [ ] It may change an accepted claim or the marked manuscript block.",
    "- [ ] Capture began before the final interpretation or manuscript decision.",
    "- [ ] The required artifacts may be handled under the applicable policy.",
)
BASELINE_RESPONSE_FIELDS = (
    "- Observation identifiers reviewed:",
    "- Claim scope affected:",
    "- Alternative interpretation considered:",
    "- Smallest discriminating follow-up, if any:",
    "- Decision and rationale:",
    "- Exact manuscript block affected:",
    "- Expected wording consequence:",
    "- Known dependency, provenance, or debt omitted from this checklist:",
    "- Baseline active seconds:",
    "- Wall-clock interruption seconds:",
    "- Setup seconds:",
    "- Wait seconds:",
    "- Copied command count:",
    "- Help invocation count:",
    "- Recoverable error count:",
    "- Abandoned attempt count:",
    "- Recorded-at timestamp:",
    "- Eligibility-rule version:",
    "- Template version:",
    "- Completion status:",
    "- Local artifact digest:",
)
FROZEN_COMPILER_ARGV = (
    "latexmk",
    "-pdf",
    "-interaction=nonstopmode",
    "manuscript-before.tex",
)


class DuplicateKeyError(ValueError):
    """A JSON object repeated a key and is therefore non-canonical."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_PACKET,
        help="truth-packet directory (defaults to the committed P0 fixture)",
    )
    return parser


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction and is_junction():
        return True
    try:
        file_attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(file_attributes & reparse_point)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key '{key}'")
        result[key] = value
    return result


def _is_safe_packet_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and len(path.parts) == 1
        and path.parts[0] not in {".", ".."}
        and path.as_posix() == value
    )


def _looks_absolute(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:^|[\s(\"'=])file:(?://+|\\+)",
            value,
        )
        or
        re.search(
            r"(?:^|[\s(\"'=])"
            r"(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/]|"
            r"\\(?!\\)[^\\/\s]+[\\/]|//[^/\s]+/|~[\\/]|/(?!/)[^\s]+)",
            value,
        )
    )


def _looks_secret(value: str) -> bool:
    return bool(
        re.search(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}", value)
        or re.search(r"\bsk-[A-Za-z0-9_-]{16,}", value)
        or re.search(r"\bAKIA[0-9A-Z]{16}\b", value)
        or "-----BEGIN PRIVATE KEY-----" in value
    )


def _is_exact_integer(value: object, expected: int) -> bool:
    return type(value) is int and value == expected


def _string_leaves(value: object, path: str = "$"):
    pending = [(path, value)]
    while pending:
        current_path, current = pending.pop()
        if isinstance(current, str):
            yield current_path, current
        elif isinstance(current, list):
            pending.extend(
                (f"{current_path}[{index}]", item)
                for index, item in reversed(list(enumerate(current)))
            )
        elif isinstance(current, dict):
            pending.extend(
                (f"{current_path}.{key}", item)
                for key, item in reversed(list(current.items()))
            )


class TruthPacketValidator:
    """Fail-closed validator for the single committed P0 fixture contract."""

    def __init__(self, packet_root: Path) -> None:
        self.packet_root = packet_root
        self.errors: list[str] = []
        self.verified_bytes: dict[str, bytes] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def exact_object(
        self, value: object, expected: set[str], label: str
    ) -> dict[str, object] | None:
        if not isinstance(value, dict):
            self.error(f"{label}: expected an object")
            return None
        missing = sorted(expected - value.keys())
        unexpected = sorted(value.keys() - expected)
        if missing:
            self.error(f"{label}: missing keys: {', '.join(missing)}")
        if unexpected:
            self.error(f"{label}: unexpected keys: {', '.join(unexpected)}")
        return value

    def read_bounded_bytes(self, name: str) -> bytes | None:
        path = self.packet_root / name
        if _is_link(path):
            self.error(f"{name}: symlink or junction is forbidden")
            return None
        try:
            metadata = path.stat()
        except OSError as error:
            self.error(f"{name}: unavailable: {error}")
            return None
        if not stat.S_ISREG(metadata.st_mode):
            self.error(f"{name}: expected a regular file")
            return None
        if metadata.st_size > MAX_ARTIFACT_BYTES:
            self.error(f"{name}: exceeds {MAX_ARTIFACT_BYTES}-byte limit")
            return None
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_ARTIFACT_BYTES + 1)
        except OSError as error:
            self.error(f"{name}: unavailable: {error}")
            return None
        if len(raw) > MAX_ARTIFACT_BYTES:
            self.error(f"{name}: exceeds {MAX_ARTIFACT_BYTES}-byte limit")
            return None
        return raw

    def load_json(self, name: str) -> object | None:
        raw = self.verified_bytes.get(name)
        if raw is None:
            raw = self.read_bounded_bytes(name)
        if raw is None:
            return None
        try:
            text = raw.decode("utf-8")
            return json.loads(text, object_pairs_hook=_unique_object)
        except DuplicateKeyError as error:
            self.error(f"{name}: {error}")
        except RecursionError:
            self.error(f"{name}: JSON nesting is too deep")
        except (UnicodeError, json.JSONDecodeError) as error:
            self.error(f"{name}: invalid JSON: {error}")
        return None

    def read_text(self, name: str) -> str | None:
        raw = self.verified_bytes.get(name)
        if raw is None:
            raw = self.read_bounded_bytes(name)
        if raw is None:
            return None
        try:
            return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeError as error:
            self.error(f"{name}: invalid UTF-8: {error}")
            return None

    def scan_json(self, name: str, value: object) -> None:
        for field_path, leaf in _string_leaves(value):
            if _looks_absolute(leaf):
                self.error(f"{name} {field_path}: absolute path is forbidden")
            if _looks_secret(leaf):
                self.error(f"{name} {field_path}: secret-like content is forbidden")

    def scan_text(self, name: str, text: str) -> None:
        for number, line in enumerate(text.splitlines(), start=1):
            if _looks_absolute(line.strip()):
                self.error(f"{name}:{number}: absolute path is forbidden")
        if _looks_secret(text):
            self.error(f"{name}: secret-like content is forbidden")

    def validate_manifest(self, value: object) -> dict[str, dict[str, object]]:
        manifest = self.exact_object(
            value,
            {"schema_version", "packet_id", "classification", "private_mapping", "files"},
            "manifest.json",
        )
        if manifest is None:
            return {}
        if not _is_exact_integer(manifest.get("schema_version"), SCHEMA_VERSION):
            self.error(
                "manifest.json: unsupported schema_version "
                f"{manifest.get('schema_version')}"
            )
        if manifest.get("packet_id") != "saturation-operator-damage-redacted-v1":
            self.error("manifest.json: unexpected packet_id")
        if manifest.get("classification") != "redacted-substitution":
            self.error("manifest.json: classification must be redacted-substitution")
        if manifest.get("private_mapping") != "required-local-only":
            self.error("manifest.json: private_mapping must be required-local-only")

        files = manifest.get("files")
        if not isinstance(files, list):
            self.error("manifest.json files: expected an array")
            return {}

        entries: dict[str, dict[str, object]] = {}
        for index, value_entry in enumerate(files):
            label = f"manifest.json files[{index}]"
            entry = self.exact_object(value_entry, {"path", "role", "sha256"}, label)
            if entry is None:
                continue
            path_value = entry.get("path")
            if not _is_safe_packet_path(path_value):
                self.error(f"{path_value}: unsafe relative path")
                continue
            assert isinstance(path_value, str)
            if path_value in entries:
                self.error(f"{path_value}: duplicate manifest entry")
                continue
            expected_role = ARTIFACT_ROLES.get(path_value)
            if expected_role is None:
                self.error(f"{path_value}: unexpected manifest artifact")
            elif entry.get("role") != expected_role:
                self.error(f"{path_value}: role must be {expected_role}")
            digest = entry.get("sha256")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                self.error(f"{path_value}: sha256 must be 64 lowercase hex characters")
            entries[path_value] = entry

        missing = sorted(set(ARTIFACT_ROLES) - entries.keys())
        if missing:
            self.error(f"manifest.json: missing artifacts: {', '.join(missing)}")
        if len(files) != len(ARTIFACT_ROLES):
            self.error(
                f"manifest.json files: expected exactly {len(ARTIFACT_ROLES)}, "
                f"found {len(files)}"
            )
        return entries

    def validate_inventory(self, entries: dict[str, dict[str, object]]) -> set[str]:
        expected = {"manifest.json", *ARTIFACT_ROLES}
        try:
            children = {child.name: child for child in self.packet_root.iterdir()}
        except OSError as error:
            self.error(f"truth packet is unavailable: {error}")
            return set()
        for name in sorted(children.keys() - expected):
            kind = "file" if children[name].is_file() else "entry"
            self.error(f"{name}: unexpected {kind}")
        for name in sorted(expected - children.keys()):
            self.error(f"{name}: missing file")

        verified: set[str] = set()
        for name, entry in entries.items():
            raw = self.read_bounded_bytes(name)
            if raw is None:
                continue
            actual = sha256(raw).hexdigest()
            if actual != entry.get("sha256"):
                self.error(f"{name}: sha256 mismatch")
                continue
            self.verified_bytes[name] = raw
            verified.add(name)
        return verified

    def validate_packet(self, value: object, manifest: object) -> dict[str, object] | None:
        packet = self.exact_object(
            value,
            {
                "schema_version",
                "packet_id",
                "source_case",
                "classification",
                "private_mapping",
                "claim",
                "run",
                "observations",
                "unaided_human_interpretation",
                "artifacts",
                "manuscript",
                "expected_impact",
                "frozen_proposal_path",
                "baseline_path",
                "privacy",
            },
            "truth-packet.json",
        )
        if packet is None:
            return None
        manifest_object = manifest if isinstance(manifest, dict) else {}
        if not _is_exact_integer(packet.get("schema_version"), SCHEMA_VERSION):
            self.error(
                "truth-packet.json: unsupported schema_version "
                f"{packet.get('schema_version')}"
            )
        if packet.get("packet_id") != manifest_object.get("packet_id"):
            self.error("truth-packet.json: packet_id does not match manifest")
        if packet.get("source_case") != "saturation-and-operator-damage":
            self.error("truth-packet.json: unexpected source_case")
        for field in ("classification", "private_mapping"):
            if packet.get(field) != manifest_object.get(field):
                self.error(f"truth-packet.json: {field} does not match manifest")

        claim = self.exact_object(
            packet.get("claim"), {"id", "statement", "scope", "initial_status"}, "claim"
        )
        if claim is not None:
            if claim.get("id") != "C-01":
                self.error("claim: id must be C-01")
            if claim.get("scope") != list(OPERATORS):
                self.error("claim: scope must list pruning, quantization, compression")
            if claim.get("initial_status") != "supported":
                self.error("claim: initial_status must be supported")
            if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
                self.error("claim: statement must be non-empty text")

        run = self.exact_object(
            packet.get("run"), {"id", "artifact_id", "method_ref", "status"}, "run"
        )
        run_id = run.get("id") if run is not None else None
        if run is not None:
            if run_id != "R-01":
                self.error("run: id must be R-01")
            if run.get("artifact_id") != "ART-RESULT-01":
                self.error("run: artifact_id must be ART-RESULT-01")
            if run.get("status") != "completed":
                self.error("run: status must be completed")
            if not isinstance(run.get("method_ref"), str) or not run["method_ref"].strip():
                self.error("run: method_ref must be non-empty text")

        observations_value = packet.get("observations")
        observations: list[object] = (
            observations_value if isinstance(observations_value, list) else []
        )
        if not isinstance(observations_value, list):
            self.error("truth-packet.json observations: expected an array")
        elif len(observations) != 3:
            self.error(
                "truth-packet.json observations: expected exactly 3, "
                f"found {len(observations)}"
            )
        observation_by_id: dict[str, dict[str, object]] = {}
        for index, observation_value in enumerate(observations):
            observation = self.exact_object(
                observation_value,
                {"id", "run_id", "operator", "expected", "relationship_to_claim", "rationale"},
                f"observation {index + 1}",
            )
            if observation is None:
                continue
            observation_id = observation.get("id")
            display_id = observation_id if isinstance(observation_id, str) else f"#{index + 1}"
            if isinstance(observation_id, str):
                if observation_id in observation_by_id:
                    self.error(f"observation {observation_id}: duplicate id")
                observation_by_id[observation_id] = observation
            if observation.get("run_id") != run_id:
                self.error(f"observation {display_id}: run_id does not match {run_id}")
            truth = OBSERVATION_TRUTH.get(str(observation_id))
            if truth is None:
                self.error(f"observation {display_id}: unexpected id")
            else:
                operator, expected, relationship, _ = truth
                if observation.get("operator") != operator:
                    self.error(f"observation {display_id}: operator must be {operator}")
                if observation.get("expected") is not expected:
                    self.error(f"observation {display_id}: expected flag does not match truth")
                if observation.get("relationship_to_claim") != relationship:
                    self.error(
                        f"observation {display_id}: relationship_to_claim must be {relationship}"
                    )
            if (
                not isinstance(observation.get("rationale"), str)
                or not observation["rationale"].strip()
            ):
                self.error(f"observation {display_id}: rationale must be non-empty text")
        if set(observation_by_id) != set(OBSERVATION_TRUTH):
            self.error("observations must contain O-01, O-02, O-03 exactly once")

        interpretation = self.exact_object(
            packet.get("unaided_human_interpretation"),
            {"id", "contributor", "statement", "observation_ids"},
            "unaided_human_interpretation",
        )
        if interpretation is not None:
            if interpretation.get("id") != "I-01":
                self.error("unaided_human_interpretation: id must be I-01")
            if interpretation.get("contributor") != "human":
                self.error("unaided_human_interpretation: contributor must be human")
            if interpretation.get("observation_ids") != list(OBSERVATION_TRUTH):
                self.error(
                    "unaided_human_interpretation: observation_ids must cover O-01, O-02, O-03"
                )
            if (
                not isinstance(interpretation.get("statement"), str)
                or not interpretation["statement"].strip()
            ):
                self.error("unaided_human_interpretation: statement must be non-empty text")

        self.validate_packet_artifacts(packet)
        self.validate_expected_impact(packet, observation_by_id)
        self.validate_privacy_contract(packet)
        self.scan_json("truth-packet.json", packet)
        return packet

    def validate_packet_artifacts(self, packet: dict[str, object]) -> None:
        artifacts = self.exact_object(
            packet.get("artifacts"), {"result", "manuscript"}, "artifacts"
        )
        if artifacts is not None:
            expected = {
                "result": ("ART-RESULT-01", "result-summary.json"),
                "manuscript": ("ART-MANUSCRIPT-01", "manuscript-before.tex"),
            }
            for name, (artifact_id, path) in expected.items():
                artifact = self.exact_object(
                    artifacts.get(name), {"id", "path"}, f"artifacts.{name}"
                )
                if artifact is not None and (
                    artifact.get("id"), artifact.get("path")
                ) != (artifact_id, path):
                    self.error(f"artifacts.{name}: expected {artifact_id} at {path}")

        manuscript = self.exact_object(
            packet.get("manuscript"),
            {
                "anchor_id",
                "claim_id",
                "marker_id",
                "before_path",
                "after_path",
                "compiler_argv",
                "compiler_contract",
            },
            "manuscript",
        )
        if manuscript is not None:
            expected = {
                "anchor_id": "A-01",
                "claim_id": "C-01",
                "marker_id": "anchor-central-claim",
                "before_path": "manuscript-before.tex",
                "after_path": "manuscript-after.tex",
                "compiler_contract": "redacted-substitution",
            }
            for field, expected_value in expected.items():
                if manuscript.get(field) != expected_value:
                    self.error(f"manuscript: {field} must be {expected_value}")
            argv = manuscript.get("compiler_argv")
            if (
                not isinstance(argv, list)
                or not argv
                or not all(isinstance(item, str) and item for item in argv)
            ):
                self.error("manuscript: compiler_argv must be a non-empty string array")
            elif argv != list(FROZEN_COMPILER_ARGV):
                self.error("manuscript: compiler_argv does not match the frozen command")

        if packet.get("frozen_proposal_path") != "frozen-proposal.json":
            self.error("truth-packet.json: frozen_proposal_path is invalid")
        if packet.get("baseline_path") != "decision-log-baseline.md":
            self.error("truth-packet.json: baseline_path is invalid")

    def validate_expected_impact(
        self,
        packet: dict[str, object],
        observation_by_id: dict[str, dict[str, object]],
    ) -> None:
        impact = self.exact_object(
            packet.get("expected_impact"),
            {
                "claim_id",
                "claim_status_after",
                "interpretation_id",
                "relationship_truth_set",
                "manuscript_anchor_id",
                "manuscript_debt_count",
            },
            "expected_impact",
        )
        if impact is None:
            return
        expected_scalars: dict[str, object] = {
            "claim_id": "C-01",
            "claim_status_after": "contested",
            "interpretation_id": "I-01",
            "manuscript_anchor_id": "A-01",
            "manuscript_debt_count": 1,
        }
        for field, expected in expected_scalars.items():
            actual = impact.get(field)
            if field == "manuscript_debt_count":
                matches = _is_exact_integer(actual, 1)
            else:
                matches = actual == expected
            if not matches:
                self.error(f"expected_impact: {field} must be {expected}")
        relationships_value = impact.get("relationship_truth_set")
        if not isinstance(relationships_value, list):
            self.error("expected_impact relationship_truth_set: expected an array")
            return
        source_ids: list[object] = []
        for index, relationship_value in enumerate(relationships_value):
            relationship = self.exact_object(
                relationship_value,
                {"source_id", "target_id", "type"},
                f"expected impact relationship {index + 1}",
            )
            if relationship is None:
                continue
            source_id = relationship.get("source_id")
            if not isinstance(source_id, str):
                self.error(
                    f"expected impact relationship {index + 1}: "
                    "source_id must be a string"
                )
                source_ids.append(f"<invalid-{index + 1}>")
                continue
            source_ids.append(source_id)
            observation = observation_by_id.get(source_id)
            if observation is None:
                self.error(f"expected impact relationship has unknown source {source_id}")
                continue
            if (
                relationship.get("target_id") != "C-01"
                or relationship.get("type") != observation.get("relationship_to_claim")
            ):
                self.error(
                    f"expected impact relationship for {source_id} does not match observation"
                )
        if Counter(source_ids) != Counter(OBSERVATION_TRUTH.keys()):
            self.error(
                "expected impact relationships must cover O-01, O-02, O-03 exactly once"
            )

    def validate_privacy_contract(self, packet: dict[str, object]) -> None:
        privacy = self.exact_object(
            packet.get("privacy"),
            {"contains_private_source", "contains_absolute_paths", "local_mapping_required"},
            "privacy",
        )
        if privacy is not None:
            if not (
                privacy.get("contains_private_source") is False
                and privacy.get("contains_absolute_paths") is False
                and privacy.get("local_mapping_required") is True
            ):
                self.error(
                    "privacy: expected redacted packet flags are false, false, true"
                )

    def validate_result_summary(
        self, value: object, packet: dict[str, object] | None
    ) -> None:
        summary = self.exact_object(
            value, {"schema_version", "run_id", "measurements"}, "result-summary.json"
        )
        if summary is None:
            return
        if not _is_exact_integer(summary.get("schema_version"), SCHEMA_VERSION):
            self.error("result-summary.json: unsupported schema_version")
        run = packet.get("run") if packet is not None else None
        run_id = run.get("id") if isinstance(run, dict) else None
        if summary.get("run_id") != run_id:
            self.error("result-summary.json: run_id does not match truth packet")
        observations = packet.get("observations") if packet is not None else None
        by_id = {
            item.get("id"): item
            for item in observations or []
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        } if isinstance(observations, list) else {}
        measurements_value = summary.get("measurements")
        if not isinstance(measurements_value, list):
            self.error("result-summary.json measurements: expected an array")
            return
        ids: list[object] = []
        for index, measurement_value in enumerate(measurements_value):
            measurement = self.exact_object(
                measurement_value,
                {"observation_id", "operator", "expected", "category"},
                f"result-summary.json measurement {index + 1}",
            )
            if measurement is None:
                continue
            observation_id = measurement.get("observation_id")
            if not isinstance(observation_id, str):
                self.error(
                    f"result-summary.json measurement {index + 1}: "
                    "observation_id must be a string"
                )
                ids.append(f"<invalid-{index + 1}>")
                continue
            ids.append(observation_id)
            observation = by_id.get(observation_id)
            if observation is None:
                self.error(f"result-summary.json {observation_id}: unknown observation")
                continue
            if measurement.get("operator") != observation.get("operator"):
                self.error(
                    f"result-summary.json {observation_id}: operator does not match truth packet"
                )
            if measurement.get("expected") is not observation.get("expected"):
                self.error(
                    f"result-summary.json {observation_id}: expected does not match truth packet"
                )
            truth = OBSERVATION_TRUTH.get(str(observation_id))
            if truth is not None and measurement.get("category") != truth[3]:
                self.error(
                    f"result-summary.json {observation_id}: category must be {truth[3]}"
                )
        if Counter(ids) != Counter(OBSERVATION_TRUTH.keys()):
            self.error(
                "result-summary.json: measurements must cover O-01, O-02, O-03 "
                "exactly once"
            )
        self.scan_json("result-summary.json", summary)

    def validate_proposal(self, value: object) -> None:
        proposal = self.exact_object(
            value,
            {
                "schema_version",
                "proposal_id",
                "trace_id",
                "intended_operation",
                "normalized_text",
                "payload_availability",
                "live_provider_required",
            },
            "frozen-proposal.json",
        )
        if proposal is None:
            return
        expected = {
            "proposal_id": "P-01",
            "trace_id": "T-01",
            "intended_operation": "record-interpretation",
            "payload_availability": "frozen-redacted",
        }
        if not _is_exact_integer(proposal.get("schema_version"), SCHEMA_VERSION):
            self.error("frozen-proposal.json: schema_version has an unexpected value")
        for field, expected_value in expected.items():
            if proposal.get(field) != expected_value:
                self.error(f"frozen-proposal.json: {field} has an unexpected value")
        if proposal.get("live_provider_required") is not False:
            self.error("frozen-proposal.json: live_provider_required must be false")
        if (
            not isinstance(proposal.get("normalized_text"), str)
            or not proposal["normalized_text"].strip()
        ):
            self.error("frozen-proposal.json: normalized_text must be non-empty text")
        self.scan_json("frozen-proposal.json", proposal)

    def validate_manuscripts(
        self, packet: dict[str, object] | None, before: str, after: str
    ) -> None:
        manuscript = packet.get("manuscript") if packet is not None else None
        marker_id = manuscript.get("marker_id") if isinstance(manuscript, dict) else None
        if not isinstance(marker_id, str):
            self.error("truth-packet.json: manuscript marker_id is unavailable")
            return

        bodies: dict[str, str] = {}
        for name, text in (
            ("manuscript-before.tex", before),
            ("manuscript-after.tex", after),
        ):
            start = re.findall(
                rf"^% claimbranch:start id={re.escape(marker_id)}$", text, re.MULTILINE
            )
            end = re.findall(
                rf"^% claimbranch:end id={re.escape(marker_id)}$", text, re.MULTILINE
            )
            match = re.search(
                rf"^% claimbranch:start id={re.escape(marker_id)}\r?\n"
                rf"(?P<body>.*?)"
                rf"^% claimbranch:end id={re.escape(marker_id)}$",
                text,
                re.MULTILINE | re.DOTALL,
            )
            if len(start) != 1 or len(end) != 1 or match is None:
                self.error(
                    f"{name}: expected exactly one complete marker pair for {marker_id}"
                )
            else:
                bodies[name] = match.group("body")
            self.scan_text(name, text)
        if len(bodies) == 2 and bodies["manuscript-before.tex"] == bodies["manuscript-after.tex"]:
            self.error("manuscript-after.tex: marked replacement must differ from before")

    def validate_baseline(self, text: str) -> None:
        for marker in BASELINE_MARKERS:
            if text.count(f"<!-- {marker} -->") != 1:
                self.error(
                    f"decision-log-baseline.md: required marker is missing: {marker}"
                )
        for heading in BASELINE_HEADINGS:
            if len(re.findall(rf"^{re.escape(heading)}$", text, re.MULTILINE)) != 1:
                self.error(f"decision-log-baseline.md: required heading is missing: {heading}")
        if re.search(r"^- \[[xX]\]", text, re.MULTILINE):
            self.error("decision-log-baseline.md: checked answers are forbidden")
        checkboxes = tuple(re.findall(r"^- \[ \] .+$", text, re.MULTILINE))
        if checkboxes != BASELINE_CHECKBOXES:
            self.error(
                "decision-log-baseline.md: eligibility checks do not match "
                "the frozen template"
            )
        response_fields = tuple(
            line
            for line in text.splitlines()
            if line.startswith("- ") and not line.startswith("- [ ] ")
        )
        if response_fields != BASELINE_RESPONSE_FIELDS:
            self.error(
                "decision-log-baseline.md: response fields do not match "
                "the frozen template"
            )
        self.scan_text("decision-log-baseline.md", text)

    def validate(self) -> None:
        if _is_link(self.packet_root):
            self.error("truth packet directory cannot be a symlink or junction")
            return
        if not self.packet_root.is_dir():
            self.error("truth packet directory is unavailable")
            return

        manifest = self.load_json("manifest.json")
        entries = self.validate_manifest(manifest)
        verified = self.validate_inventory(entries)

        packet_value = (
            self.load_json("truth-packet.json")
            if "truth-packet.json" in verified
            else None
        )
        packet = self.validate_packet(packet_value, manifest) if packet_value is not None else None

        if "result-summary.json" in verified:
            result = self.load_json("result-summary.json")
            if result is not None:
                self.validate_result_summary(result, packet)
        if "frozen-proposal.json" in verified:
            proposal = self.load_json("frozen-proposal.json")
            if proposal is not None:
                self.validate_proposal(proposal)

        before = (
            self.read_text("manuscript-before.tex")
            if "manuscript-before.tex" in verified
            else None
        )
        after = (
            self.read_text("manuscript-after.tex")
            if "manuscript-after.tex" in verified
            else None
        )
        if before is not None and after is not None:
            self.validate_manuscripts(packet, before, after)
        if "decision-log-baseline.md" in verified:
            baseline = self.read_text("decision-log-baseline.md")
            if baseline is not None:
                self.validate_baseline(baseline)


def main(argv: Sequence[str] | None = None) -> int:
    packet_root = _parser().parse_args(argv).packet
    validator = TruthPacketValidator(packet_root)
    validator.validate()
    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "P0 source fixture valid: saturation-operator-damage-redacted-v1 "
        "(6 artifacts, 3 observations)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
