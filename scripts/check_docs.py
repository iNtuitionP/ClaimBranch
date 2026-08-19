#!/usr/bin/env python3
"""Validate ClaimBranch's repository documentation contract."""

from __future__ import annotations

import re
import sys
import os
import html
import subprocess
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPO_SKILLS = ROOT / ".agents" / "skills"
REQUIRED_FILES = {
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "ARCHITECTURE.md",
    DOCS / "README.md",
    DOCS / "AGENTS.md",
    DOCS / "CLAUDE.md",
    DOCS / "PLANS.md",
}
ALLOWED_ROOT_MARKDOWN = {
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
}
LOCAL_SPECIAL_NAMES = {"README.md", "AGENTS.md", "CLAUDE.md"}
SPECIAL_NAMES = {"README.md", "AGENTS.md", "CLAUDE.md", "PLANS.md"}
METADATA_KEYS = {"kind", "status", "owners", "last_reviewed"}
CANONICAL_KINDS = {
    "product-spec",
    "release-scope",
    "target-architecture",
    "architecture",
    "domain-model",
    "policy",
    "development",
    "validation-case",
}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".claimbranch-cache",
    ".venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
}
LEGACY_MINIMAL_ADRS = {
    "0001-evidence-and-reasoning.md",
    "0003-ai-proposals.md",
}
STALE_AFTER_DAYS = 120
REVIEW_TODAY = datetime.now(timezone(timedelta(hours=9))).date()

KIND_STATES = {
    "product-spec": {"draft", "active", "deprecated"},
    "release-scope": {"draft", "proposed", "active", "retired"},
    "target-architecture": {"draft", "active", "deprecated"},
    "architecture": {"draft", "active", "deprecated"},
    "domain-model": {"draft", "active", "deprecated"},
    "policy": {"draft", "active", "deprecated"},
    "reference": {"draft", "active", "deprecated"},
    "development": {"draft", "active", "deprecated"},
    "adr": {"proposed", "accepted", "rejected", "superseded"},
    "design": {
        "draft",
        "in-review",
        "accepted",
        "rejected",
        "withdrawn",
        "superseded",
    },
    "exec-plan": {"planned", "active", "completed", "abandoned"},
    "validation-case": {"draft", "active", "retired"},
    "generated": {"generated"},
}
HISTORICAL_KIND_STATES = {
    ("adr", "accepted"),
    ("adr", "rejected"),
    ("adr", "superseded"),
    ("design", "rejected"),
    ("design", "withdrawn"),
    ("design", "superseded"),
    ("exec-plan", "completed"),
    ("exec-plan", "abandoned"),
    ("validation-case", "retired"),
    ("release-scope", "retired"),
}

LINK_RE = re.compile(
    r"!?\[[^\]\n]*\]\((<[^>\n]+>|(?:\\.|[^()\n]|\([^()\n]*\))+?)\)"
)
REFERENCE_DEFINITION_RE = re.compile(
    r"^\s*\[(?!\^)[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", re.MULTILINE
)
NORMAL_FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
ADR_FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
PLAN_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$")
DESIGN_FILENAME_RE = PLAN_FILENAME_RE
ADR_INDEX_ROW_RE = re.compile(
    r"^\|\s*\[(\d{4})\]\(([^)]+)\)\s*\|\s*([a-z-]+)\s*\|",
    re.MULTILINE,
)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def markdown_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        names = result.stdout.decode("utf-8").split("\0")
        return sorted(
            {
                ROOT / name
                for name in names
                if name and (ROOT / name).is_file() and Path(name).suffix.lower() == ".md"
            },
            key=relative,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        pass

    files: list[Path] = []
    for current, directory_names, file_names in os.walk(ROOT):
        directory_names[:] = [
            name for name in directory_names if name not in EXCLUDED_DIRECTORY_NAMES
        ]
        current_path = Path(current)
        for name in file_names:
            path = current_path / name
            if path.suffix.lower() == ".md":
                files.append(path)
    return sorted(set(files), key=relative)


def is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def is_repo_skill_instruction(path: Path) -> bool:
    try:
        parts = path.relative_to(REPO_SKILLS).parts
    except ValueError:
        return False
    return (
        len(parts) == 2
        and parts[1] == "SKILL.md"
        and re.fullmatch(r"[a-z0-9][a-z0-9-]*", parts[0]) is not None
    )


def check_required_files(errors: list[str]) -> None:
    for path in sorted(REQUIRED_FILES, key=relative):
        if not path.is_file():
            errors.append(f"{relative(path)}: required documentation control file is missing")
            continue
        try:
            if not path.read_text(encoding="utf-8").strip():
                errors.append(f"{relative(path)}: required documentation control file is empty")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative(path)}: cannot read required control file: {exc}")


def check_managed_location(path: Path, errors: list[str]) -> None:
    if path.suffix != ".md":
        errors.append(f"{relative(path)}: Markdown extension must be lowercase '.md'")
    if path.parent == ROOT and path.name not in ALLOWED_ROOT_MARKDOWN:
        errors.append(
            f"{relative(path)}: unmanaged root Markdown; place durable knowledge under docs/"
        )
        return
    if DOCS in path.parents or path.parent == ROOT:
        return
    if ".github" in path.relative_to(ROOT).parts:
        return
    if is_repo_skill_instruction(path):
        return
    if path.name not in LOCAL_SPECIAL_NAMES:
        errors.append(
            f"{relative(path)}: only local README/AGENTS/CLAUDE files may live outside docs/"
        )


def check_kind_location(path: Path, kind: str, errors: list[str]) -> None:
    locations = {
        "product-spec": lambda: path.parent == DOCS / "product",
        "release-scope": lambda: is_within(path, DOCS / "product" / "releases"),
        "target-architecture": lambda: path == ROOT / "ARCHITECTURE.md",
        "architecture": lambda: is_within(path, DOCS / "architecture")
        and not is_within(path, DOCS / "architecture" / "decisions"),
        "domain-model": lambda: is_within(path, DOCS / "architecture")
        and not is_within(path, DOCS / "architecture" / "decisions"),
        "policy": lambda: path == DOCS / "PLANS.md" or is_within(path, DOCS / "_meta"),
        "reference": lambda: is_within(path, DOCS / "references"),
        "development": lambda: is_within(path, DOCS / "development"),
        "adr": lambda: path.parent == DOCS / "architecture" / "decisions",
        "design": lambda: path.parent == DOCS / "designs",
        "exec-plan": lambda: path.parent
        in {DOCS / "plans" / "active", DOCS / "plans" / "completed"},
        "validation-case": lambda: is_within(path, DOCS / "validation"),
        "generated": lambda: is_within(path, DOCS / "generated"),
    }
    location_check = locations.get(kind)
    if location_check is not None and not location_check():
        errors.append(f"{relative(path)}: kind '{kind}' is stored in the wrong area")


def without_fenced_code(text: str) -> str:
    output: list[str] = []
    fence_char: str | None = None
    fence_length = 0

    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            output.append("")
            continue
        if fence_char is None and (line.startswith("    ") or line.startswith("\t")):
            output.append("")
            continue
        output.append(line if fence_char is None else "")

    return "\n".join(output)


def without_hidden_markdown(text: str) -> str:
    visible = without_fenced_code(text)
    return re.sub(r"<!--.*?-->", "", visible, flags=re.DOTALL)


def visible_markdown(text: str) -> str:
    visible = without_hidden_markdown(text)
    code_span = re.compile(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", re.DOTALL)
    return code_span.sub("", visible)


def is_template(path: Path) -> bool:
    try:
        parts = path.relative_to(DOCS).parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == "_meta" and parts[1] == "templates"


def needs_front_matter(path: Path) -> bool:
    if path == ROOT / "ARCHITECTURE.md":
        return True
    if DOCS not in path.parents:
        return False
    if path.name in {"README.md", "AGENTS.md", "CLAUDE.md"}:
        return False
    return not is_template(path)


def parse_front_matter(path: Path, text: str, errors: list[str]) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"{relative(path)}: missing YAML front matter")
        return {}

    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        errors.append(f"{relative(path)}: unclosed YAML front matter")
        return {}

    metadata: dict[str, str] = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            errors.append(
                f"{relative(path)}:{number}: front matter must use flat 'key: value' fields"
            )
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"\'')
        if not key or not value:
            errors.append(f"{relative(path)}:{number}: empty front-matter key or value")
            continue
        if key in metadata:
            errors.append(f"{relative(path)}:{number}: duplicate front-matter key '{key}'")
        metadata[key] = value

    return metadata


def check_front_matter(
    path: Path,
    text: str,
    errors: list[str],
    warnings: list[str],
) -> dict[str, str]:
    if not needs_front_matter(path):
        return {}

    metadata = parse_front_matter(path, text, errors)
    missing = sorted(METADATA_KEYS - metadata.keys())
    if missing:
        errors.append(f"{relative(path)}: missing front-matter fields: {', '.join(missing)}")
        return metadata

    kind = metadata["kind"]
    status = metadata["status"]
    allowed = KIND_STATES.get(kind)
    if allowed is None:
        errors.append(f"{relative(path)}: unknown document kind '{kind}'")
    elif status not in allowed:
        errors.append(
            f"{relative(path)}: status '{status}' is invalid for kind '{kind}'; "
            f"expected one of {', '.join(sorted(allowed))}"
        )
    check_kind_location(path, kind, errors)

    if kind in CANONICAL_KINDS and not metadata.get("canonical_for"):
        errors.append(f"{relative(path)}: kind '{kind}' requires canonical_for")

    try:
        reviewed = date.fromisoformat(metadata["last_reviewed"])
    except ValueError:
        errors.append(f"{relative(path)}: last_reviewed must be YYYY-MM-DD")
    else:
        age = (REVIEW_TODAY - reviewed).days
        if age < 0:
            errors.append(
                f"{relative(path)}: last_reviewed is in the future for Asia/Seoul"
            )
        elif age > STALE_AFTER_DAYS and (kind, status) not in HISTORICAL_KIND_STATES:
            warnings.append(
                f"{relative(path)}: last reviewed {age} days ago; verify during related work"
            )

    return metadata


def check_heading(path: Path, text: str, errors: list[str]) -> None:
    if path.name == "CLAUDE.md":
        return
    visible = visible_markdown(text)
    h1_count = len(re.findall(r"^# [^#].*$", visible, flags=re.MULTILINE))
    if h1_count != 1:
        errors.append(f"{relative(path)}: expected exactly one H1, found {h1_count}")


def check_filename(path: Path, errors: list[str]) -> None:
    if DOCS not in path.parents or path.name in SPECIAL_NAMES:
        return
    if not NORMAL_FILENAME_RE.fullmatch(path.name):
        errors.append(
            f"{relative(path)}: use a lowercase kebab-case Markdown filename"
        )


def extract_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return re.split(r"\s+[\"']", target, maxsplit=1)[0]


def exact_case_exists(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    current = ROOT
    for part in parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current /= part
    return True


def heading_anchors(text: str) -> set[str]:
    visible = without_hidden_markdown(text)
    anchors: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    for match in re.finditer(
        r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", visible, flags=re.MULTILINE
    ):
        heading = match.group(1)
        heading = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", heading)
        heading = html.unescape(re.sub(r"<[^>]+>", "", heading))
        heading = re.sub(r"[`*_~]", "", heading).strip().lower()
        base = re.sub(r"[^\w\- ]", "", heading)
        base = re.sub(r"\s+", "-", base)
        if not base:
            continue
        count = counts[base]
        anchor = base if count == 0 else f"{base}-{count}"
        counts[base] += 1
        anchors.add(anchor)
    anchors.update(
        match.group(1).lower()
        for match in re.finditer(r"\bid=[\"']([^\"']+)[\"']", visible)
    )
    return anchors


def local_link_targets(
    path: Path,
    text: str,
    errors: list[str],
    anchor_cache: dict[Path, set[str]],
) -> list[Path]:
    targets: list[Path] = []
    visible = visible_markdown(text)
    inline_targets = LINK_RE.findall(visible)
    raw_targets = [(target, True) for target in inline_targets]
    raw_targets.extend(
        (target, False) for target in REFERENCE_DEFINITION_RE.findall(visible)
    )

    for raw_target, discoverable in raw_targets:
        target = extract_link_target(raw_target)
        if not target:
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            if re.match(r"^[a-zA-Z]:[\\/]", target):
                errors.append(f"{relative(path)}: machine-specific absolute link '{target}'")
            continue
        if target.startswith("/"):
            errors.append(f"{relative(path)}: repository links must be relative: '{target}'")
            continue
        if "\\" in target:
            errors.append(f"{relative(path)}: Markdown links must use forward slashes: '{target}'")
            continue

        path_and_query, separator, fragment = target.partition("#")
        file_part = path_and_query.split("?", 1)[0]
        resolved = path if not file_part else (path.parent / unquote(file_part)).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            errors.append(f"{relative(path)}: link escapes the repository: '{target}'")
            continue

        if not resolved.exists():
            errors.append(f"{relative(path)}: broken internal link '{target}'")
            continue
        if resolved.is_dir():
            errors.append(f"{relative(path)}: link to a file index, not directory '{target}'")
            continue
        if not exact_case_exists(resolved):
            errors.append(f"{relative(path)}: internal link has incorrect path casing '{target}'")
            continue

        if separator and fragment and resolved.suffix.lower() == ".md":
            decoded_fragment = unquote(fragment).strip().lower()
            if resolved not in anchor_cache:
                try:
                    anchor_cache[resolved] = heading_anchors(
                        resolved.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError):
                    anchor_cache[resolved] = set()
            if decoded_fragment not in anchor_cache[resolved]:
                errors.append(f"{relative(path)}: missing Markdown anchor in '{target}'")
                continue
        if discoverable:
            targets.append(resolved)

    return targets


def section_headings(text: str) -> set[str]:
    visible = visible_markdown(text)
    return {
        match.group(1).strip().lower()
        for match in re.finditer(r"^##\s+(.+?)\s*$", visible, flags=re.MULTILINE)
    }


def check_adrs(
    texts: dict[Path, str],
    metadata_by_path: dict[Path, dict[str, str]],
    errors: list[str],
) -> None:
    directory = DOCS / "architecture" / "decisions"
    seen_numbers: dict[str, Path] = {}
    core_required = {"context", "decision", "consequences"}
    full_required = core_required | {
        "decision drivers",
        "options considered",
        "validation",
        "supersession",
    }
    index_path = directory / "README.md"
    index_rows: dict[Path, tuple[str, str]] = {}
    for number, raw_target, status in ADR_INDEX_ROW_RE.findall(texts.get(index_path, "")):
        target = (index_path.parent / extract_link_target(raw_target)).resolve()
        if target in index_rows:
            errors.append(f"{relative(index_path)}: duplicate ADR index row for {relative(target)}")
        index_rows[target] = (number, status)

    for path in sorted(directory.rglob("*.md")):
        if path.name == "README.md":
            continue
        match = ADR_FILENAME_RE.fullmatch(path.name)
        if not match:
            errors.append(f"{relative(path)}: ADR filename must be NNNN-kebab-case.md")
            continue
        number = match.group(1)
        if number in seen_numbers:
            errors.append(
                f"{relative(path)}: ADR number {number} is also used by "
                f"{relative(seen_numbers[number])}"
            )
        seen_numbers[number] = path
        metadata = metadata_by_path.get(path, {})
        if metadata.get("kind") != "adr":
            errors.append(f"{relative(path)}: ADR must declare kind: adr")
        legacy = metadata.get("format") == "legacy-minimal"
        if legacy and path.name not in LEGACY_MINIMAL_ADRS:
            errors.append(f"{relative(path)}: legacy-minimal is not allowed for new ADRs")
        if legacy and metadata.get("status") != "accepted":
            errors.append(f"{relative(path)}: legacy-minimal is allowed only for accepted ADRs")
        if path.name in LEGACY_MINIMAL_ADRS and not legacy:
            errors.append(f"{relative(path)}: expected explicit legacy-minimal format marker")
        required = core_required if legacy else full_required
        missing = required - section_headings(texts[path])
        if missing:
            errors.append(f"{relative(path)}: missing ADR sections: {', '.join(sorted(missing))}")

        row = index_rows.get(path)
        if row is None:
            errors.append(f"{relative(path)}: missing from architecture decision index")
        else:
            indexed_number, indexed_status = row
            if indexed_number != number:
                errors.append(f"{relative(path)}: ADR number differs from its index row")
            if indexed_status != metadata.get("status"):
                errors.append(
                    f"{relative(path)}: index status '{indexed_status}' differs from front matter"
                )

    for indexed_path in index_rows:
        if indexed_path.parent != directory or indexed_path.name == "README.md":
            errors.append(
                f"{relative(index_path)}: ADR index row points outside the decision directory"
            )
        elif indexed_path not in metadata_by_path:
            errors.append(
                f"{relative(index_path)}: ADR index row has no corresponding document"
            )


def check_plans(
    texts: dict[Path, str],
    metadata_by_path: dict[Path, dict[str, str]],
    errors: list[str],
) -> None:
    required = {
        "purpose and big picture",
        "progress",
        "surprises & discoveries",
        "decision log",
        "outcomes & retrospective",
        "context and orientation",
        "plan of work",
        "concrete steps",
        "validation and acceptance",
        "idempotence and recovery",
        "artifacts and notes",
    }
    expected_status = {"active": {"planned", "active"}, "completed": {"completed", "abandoned"}}

    for area, allowed_status in expected_status.items():
        directory = DOCS / "plans" / area
        for path in sorted(directory.rglob("*.md")):
            if path.name == "README.md":
                continue
            if not PLAN_FILENAME_RE.fullmatch(path.name):
                errors.append(
                    f"{relative(path)}: plan filename must be YYYY-MM-DD-kebab-case.md"
                )
            metadata = metadata_by_path.get(path, {})
            if metadata.get("kind") != "exec-plan":
                errors.append(f"{relative(path)}: plan must declare kind: exec-plan")
            if metadata.get("status") not in allowed_status:
                errors.append(
                    f"{relative(path)}: status must match its plans/{area}/ lifecycle"
                )
            missing = required - section_headings(texts[path])
            if missing:
                errors.append(
                    f"{relative(path)}: missing ExecPlan sections: {', '.join(sorted(missing))}"
                )


def check_designs(
    texts: dict[Path, str],
    metadata_by_path: dict[Path, dict[str, str]],
    errors: list[str],
) -> None:
    directory = DOCS / "designs"
    required = {
        "purpose",
        "context and current state",
        "goals and non-goals",
        "decision drivers",
        "options considered",
        "proposed design",
        "migration and rollback",
        "validation",
        "open questions",
        "outcome",
    }
    for path in sorted(directory.rglob("*.md")):
        if path.name == "README.md":
            continue
        if path.parent != directory:
            errors.append(f"{relative(path)}: design documents may not be nested")
        if not DESIGN_FILENAME_RE.fullmatch(path.name):
            errors.append(
                f"{relative(path)}: design filename must be YYYY-MM-DD-kebab-case.md"
            )
        if metadata_by_path.get(path, {}).get("kind") != "design":
            errors.append(f"{relative(path)}: design document must declare kind: design")
        missing = required - section_headings(texts[path])
        if missing:
            errors.append(
                f"{relative(path)}: missing design sections: {', '.join(sorted(missing))}"
            )


def check_canonical_claims(
    metadata_by_path: dict[Path, dict[str, str]], errors: list[str]
) -> None:
    claims: dict[str, Path] = {}
    for path, metadata in metadata_by_path.items():
        claim = metadata.get("canonical_for")
        if not claim:
            continue
        normalized = re.sub(r"\s+", " ", claim.strip().lower())
        previous = claims.get(normalized)
        if previous is not None:
            errors.append(
                f"{relative(path)}: canonical_for duplicates {relative(previous)}"
            )
        else:
            claims[normalized] = path


def check_instruction_contract(texts: dict[Path, str], errors: list[str]) -> None:
    imports = {
        ROOT / "CLAUDE.md": "@AGENTS.md",
        DOCS / "CLAUDE.md": "@AGENTS.md",
    }
    for path, expected in imports.items():
        lines = [line.strip() for line in texts.get(path, "").splitlines() if line.strip()]
        if not lines or lines[0] != expected:
            errors.append(
                f"{relative(path)}: first nonblank line must import sibling AGENTS.md as '{expected}'"
            )

    required_tokens = {
        ROOT / "AGENTS.md": {
            "docs/README.md",
            "docs/AGENTS.md",
            "docs/_meta/documentation-policy.md",
            "docs/PLANS.md",
            "python scripts/check_docs.py",
        },
        DOCS / "AGENTS.md": {
            "README.md",
            "_meta/documentation-policy.md",
            "PLANS.md",
            "python scripts/check_docs.py",
        },
    }
    for path, tokens in required_tokens.items():
        visible = without_hidden_markdown(texts.get(path, ""))
        for token in sorted(tokens):
            if token not in visible:
                errors.append(f"{relative(path)}: missing required instruction token '{token}'")


def check_nearest_indexes(
    files: list[Path], graph: dict[Path, set[Path]], errors: list[str]
) -> None:
    for path in files:
        if DOCS not in path.parents:
            continue
        if path in {DOCS / "README.md", DOCS / "AGENTS.md", DOCS / "CLAUDE.md"}:
            continue
        if path.name in {"AGENTS.md", "CLAUDE.md"}:
            continue
        directory = path.parent.parent if path.name == "README.md" else path.parent
        index: Path | None = None
        while is_within(directory, DOCS):
            candidate = directory / "README.md"
            if candidate.is_file():
                index = candidate
                break
            if directory == DOCS:
                break
            directory = directory.parent
        if index is None:
            errors.append(f"{relative(path)}: no governing README.md index found")
        elif path not in graph.get(index, set()):
            errors.append(
                f"{relative(path)}: not linked directly from nearest index {relative(index)}"
            )

    if ROOT / "ARCHITECTURE.md" not in graph.get(DOCS / "README.md", set()):
        errors.append("ARCHITECTURE.md: must be linked directly from docs/README.md")


def check_reachability(
    files: list[Path],
    graph: dict[Path, set[Path]],
    errors: list[str],
) -> None:
    start = DOCS / "README.md"
    reachable: set[Path] = set()
    queue: deque[Path] = deque([start])

    while queue:
        path = queue.popleft()
        if path in reachable:
            continue
        reachable.add(path)
        queue.extend(graph.get(path, set()) - reachable)

    ignored = {DOCS / "AGENTS.md", DOCS / "CLAUDE.md"}
    for path in files:
        if DOCS not in path.parents or path in ignored:
            continue
        if path not in reachable:
            errors.append(
                f"{relative(path)}: orphaned document; link it from an index reachable from docs/README.md"
            )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    check_required_files(errors)
    files = markdown_files()
    texts: dict[Path, str] = {}
    metadata_by_path: dict[Path, dict[str, str]] = {}
    graph: dict[Path, set[Path]] = defaultdict(set)
    anchor_cache: dict[Path, set[str]] = {}

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative(path)}: cannot read as UTF-8: {exc}")
            continue
        texts[path] = text
        check_managed_location(path, errors)
        check_heading(path, text, errors)
        check_filename(path, errors)
        metadata_by_path[path] = check_front_matter(path, text, errors, warnings)
        for target in local_link_targets(path, text, errors, anchor_cache):
            if target.suffix.lower() == ".md":
                graph[path].add(target)

    check_instruction_contract(texts, errors)
    check_canonical_claims(metadata_by_path, errors)
    check_adrs(texts, metadata_by_path, errors)
    check_designs(texts, metadata_by_path, errors)
    check_plans(texts, metadata_by_path, errors)
    check_nearest_indexes(files, graph, errors)
    check_reachability(files, graph, errors)

    for warning in sorted(set(warnings)):
        print(f"WARNING: {warning}")
    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}")
        print(f"Documentation checks failed with {len(set(errors))} error(s).")
        return 1

    print(f"Documentation checks passed for {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
