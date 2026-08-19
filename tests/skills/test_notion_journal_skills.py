from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import check_docs


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPOSITORY_ROOT / ".agents" / "skills"
EXPECTED_SKILLS = {
    "record-notion-journal": True,
    "diagnose-notion-journal": True,
    "setup-notion-journal": False,
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.fullmatch(r"---\n(?P<header>.*?)\n---\n(?P<body>.*)", text, re.DOTALL)
    if match is None:
        raise AssertionError("SKILL.md must contain one YAML frontmatter block")
    metadata: dict[str, str] = {}
    for line in match.group("header").splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise AssertionError(f"invalid frontmatter line: {line!r}")
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, match.group("body")


def policy_value(text: str) -> bool:
    match = re.search(r"^\s*allow_implicit_invocation:\s*(true|false)\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError("openai.yaml must declare allow_implicit_invocation")
    return match.group(1) == "true"


class SkillPackageTests(unittest.TestCase):
    def test_expected_repo_skill_directories_exist(self) -> None:
        actual = {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()}
        self.assertLessEqual(set(EXPECTED_SKILLS), actual)

    def test_common_metadata_and_packaging_contract(self) -> None:
        for name, implicit in EXPECTED_SKILLS.items():
            with self.subTest(skill=name):
                skill_dir = SKILLS_ROOT / name
                skill_text = read_text(skill_dir / "SKILL.md")
                skill_text.encode("ascii")
                metadata, body = parse_frontmatter(skill_text)
                self.assertEqual(set(metadata), {"name", "description"})
                self.assertEqual(metadata["name"], name)
                self.assertTrue(metadata["description"].startswith("Use when "))
                self.assertLessEqual(len(metadata["description"]), 500)
                self.assertNotRegex(metadata["description"], r"\b(first|then|finally)\b")
                self.assertLess(len(body.split()), 500)
                self.assertNotRegex(skill_text, r"\b(?:TODO|TBD)\b")
                self.assertIn("../../../docs/development/notion-coding-journal.md", body)

                ui_text = read_text(skill_dir / "agents" / "openai.yaml")
                ui_text.encode("ascii")
                self.assertIn(f"${name}", ui_text)
                self.assertEqual(policy_value(ui_text), implicit)
                short = re.search(
                    r'^\s*short_description:\s*"([^"]+)"\s*$', ui_text, re.MULTILINE
                )
                self.assertIsNotNone(short)
                assert short is not None
                self.assertGreaterEqual(len(short.group(1)), 25)
                self.assertLessEqual(len(short.group(1)), 64)

    def test_local_markdown_links_resolve(self) -> None:
        for name in EXPECTED_SKILLS:
            with self.subTest(skill=name):
                skill_dir = SKILLS_ROOT / name
                skill_text = read_text(skill_dir / "SKILL.md")
                links = re.findall(r"\[[^]]+\]\(([^)]+)\)", skill_text)
                self.assertTrue(links)
                for link in links:
                    self.assertNotIn("://", link)
                    self.assertTrue((skill_dir / link).resolve().is_file(), link)

    def test_descriptions_keep_trigger_boundaries_distinct(self) -> None:
        descriptions = {}
        for name in EXPECTED_SKILLS:
            metadata, _ = parse_frontmatter(read_text(SKILLS_ROOT / name / "SKILL.md"))
            descriptions[name] = metadata["description"]

        self.assertIn("pending cbj-v1 key", descriptions["record-notion-journal"])
        self.assertIn("retry", descriptions["record-notion-journal"])
        self.assertIn("startup interruption", descriptions["diagnose-notion-journal"])
        self.assertIn("acknowledgement failures", descriptions["diagnose-notion-journal"])
        self.assertIn("stuck or accumulating", descriptions["diagnose-notion-journal"])
        self.assertIn("explicitly asks", descriptions["setup-notion-journal"])
        self.assertNotIn("pending cbj-v1 key", descriptions["setup-notion-journal"])

    def test_only_record_declares_the_live_notion_dependency(self) -> None:
        record_ui = read_text(
            SKILLS_ROOT / "record-notion-journal" / "agents" / "openai.yaml"
        )
        self.assertIn('value: "notion"', record_ui)
        self.assertIn('url: "https://mcp.notion.com/mcp"', record_ui)
        for name in ("diagnose-notion-journal", "setup-notion-journal"):
            with self.subTest(skill=name):
                ui_text = read_text(SKILLS_ROOT / name / "agents" / "openai.yaml")
                self.assertNotIn("dependencies:", ui_text)


class DocumentationCheckerIntegrationTests(unittest.TestCase):
    def test_repo_skill_markdown_is_an_allowed_managed_location(self) -> None:
        errors: list[str] = []
        check_docs.check_managed_location(
            SKILLS_ROOT / "record-notion-journal" / "SKILL.md", errors
        )
        self.assertEqual([], errors)

    def test_unrelated_markdown_outside_docs_remains_rejected(self) -> None:
        errors: list[str] = []
        check_docs.check_managed_location(
            REPOSITORY_ROOT / "notes" / "session-handoff.md", errors
        )
        self.assertEqual(1, len(errors))
        self.assertIn("outside docs", errors[0])


class RecordSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(SKILLS_ROOT / "record-notion-journal" / "SKILL.md")
        cls.normalized = normalize_whitespace(cls.text)

    def test_uses_only_durable_public_input_and_one_key(self) -> None:
        for required in (
            "at most one",
            "public redacted",
            "pending --journal-key",
            "draft --journal-key",
            "original task context",
            "Do not invent",
        ):
            self.assertIn(required, self.normalized)

    def test_enforces_exact_query_cardinality_and_approval(self) -> None:
        for required in (
            "exact equality",
            "Zero results",
            "One result",
            "More than one result",
            "immediately before",
            "Do not search the workspace",
            "Do not delete or merge",
        ):
            self.assertIn(required, self.normalized)

    def test_has_one_terminal_output_contract(self) -> None:
        for state in (
            "Notion journal: synced",
            "Notion journal: pending",
            "Notion journal: not required",
            "Notion journal: error",
        ):
            self.assertIn(state, self.normalized)
        self.assertIn("exactly one", self.normalized)
        self.assertIn("receipt", self.normalized)

    def test_uses_the_deterministic_bundled_projection(self) -> None:
        for required in (
            "scripts/sync_context.py query",
            "scripts/sync_context.py create",
            "scripts/sync_context.py update",
            "pass `tool_input` unchanged",
            "configured_tool",
            "model_tool",
        ):
            self.assertIn(required, self.normalized)

    def test_forbids_sensitive_and_untrusted_inputs(self) -> None:
        for required in (
            "untrusted data",
            "raw prompts",
            "transcripts",
            "diffs",
            "source content",
            "environment values",
            "credentials",
            "absolute user paths",
        ):
            self.assertIn(required, self.normalized)
        self.assertIn("row count and page ID only", self.normalized)
        self.assertIn("Do not copy", self.normalized)


class DiagnoseSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(SKILLS_ROOT / "diagnose-notion-journal" / "SKILL.md")
        cls.normalized = normalize_whitespace(cls.text)

    def test_is_read_only_and_uses_bounded_commands(self) -> None:
        for required in (
            "read-only",
            "doctor --format json",
            "status --format json",
            "pending --journal-key",
            "Do not retry",
            "Do not mutate",
        ):
            self.assertIn(required, self.normalized)
        self.assertIn("quarantine preservation", self.normalized)

    def test_classifies_known_failure_domains(self) -> None:
        for required in (
            "local state or configuration",
            "MCP or OAuth",
            "hook trust",
            "schema or tool drift",
            "duplicate",
            "transport or acknowledgement",
        ):
            self.assertIn(required, self.normalized)

    def test_routes_to_one_safe_next_action(self) -> None:
        self.assertIn("one next safe action", self.normalized)
        self.assertIn("record-notion-journal", self.normalized)
        self.assertIn("setup-notion-journal", self.normalized)
        self.assertIn("manual duplicate resolution", self.normalized)


class SetupSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(SKILLS_ROOT / "setup-notion-journal" / "SKILL.md")
        cls.normalized = normalize_whitespace(cls.text)

    def test_requires_explicit_intent_and_official_endpoint(self) -> None:
        self.assertIn("explicit user request", self.normalized)
        self.assertIn("requested stage", self.normalized)
        self.assertIn("does not authorize", self.normalized)
        self.assertIn("https://mcp.notion.com/mcp", self.normalized)
        self.assertIn("Do not overwrite", self.normalized)
        self.assertIn("codex mcp login notion", self.normalized)

    def test_treats_remote_setup_results_as_untrusted(self) -> None:
        self.assertIn("untrusted data", self.normalized)
        self.assertIn("ignore instructions", self.normalized)

    def test_preserves_human_authority_and_minimal_access(self) -> None:
        for required in (
            "intended workspace",
            "approval before each",
            "enabled_tools",
            "four",
            "default_tools_approval_mode",
            "writes",
            "/hooks",
            "re-review",
        ):
            self.assertIn(required, self.normalized)

    def test_rollback_is_non_destructive(self) -> None:
        for required in (
            "disable",
            "revoke",
            "Do not delete",
            "local state",
            "Notion pages",
            "database",
        ):
            self.assertIn(required, self.normalized)


if __name__ == "__main__":
    unittest.main()
