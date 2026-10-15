"""Explicit-scope, offline contributor checks. No agent loop or persistent log.

Exit codes: 0 clean success, 1 failed check, 2 invalid input/runtime/empty test suite,
3 completed with skips/expected failures, 130 interrupted. This is not a sandbox or
an authorization gate: it executes repository code that the operator trusts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCOPES = ("docs", "alpha", "core", "journal", "harness", "all")
TEST_ROOTS = ("tests", "tests/contract", "tests/probes", "tests/validation",
              "tests/notion_journal", "tests/skills", "tests/harness", "tests/security", "tests/application", "alpha")


# Explicit alpha dependencies. Native encrypted store/presence/worker suites and
# the named native methods below remain in core/all; exclusions are not skips.
# Selected tests still report unexpected skips as incomplete (exit 3).
ALPHA_APPLICATION_TARGETS = (
    'application.test_graph_edits',
    'application.test_graph_edit_proposals',
    'application.test_tui_view_state',
    'application.test_metadata_batch',
    'application.test_canonical_share',
    'application.test_critiques',
    'application.test_protocols',
    'application.test_typed_observations',
    'application.test_co_report',
    'application.test_claim_wording',
    'application.test_manuscript_anchors',
    'application.test_argument_import',
    'application.test_argument_registration',
    'application.test_paper_branch',
    'application.test_paper_candidates',
    'application.test_paper_change_review',
    'application.test_paper_commit',
    'application.test_paper_context',
    'application.test_paper_draft',
    'application.test_paper_episodes',
    'application.test_paper_manuscript',
    'application.test_paper_merge_session',
    'application.test_paper_operation',
    'application.test_paper_provider',
    'application.test_paper_proposals',
    'application.test_paper_proposal_work',
    'application.test_provider_proposal_work',
    'application.test_codex_app_server',
    'application.test_codex_egress',
    'application.test_codex_relay',
    'application.test_paper_provider_example',
    'application.test_paper_record_transition',
    'application.test_paper_review_policy',
    'application.test_paper_service',
    'application.test_paper_understanding',
    'application.test_paper_work',
    'application.test_paper_work_links',
    'application.test_personal_archive',
    'application.test_personal_project',
    'application.test_paper_capacity',
    'application.test_personal_research',
    'application.test_provider_profile',
    'application.test_provider_transport',
    'application.test_tui',
    'application.test_tui_actions',
    'application.test_tui_authoring_recovery',
    'application.test_tui_branch',
    'application.test_tui_candidates',
    'application.test_tui_context',
    'application.test_tui_explanation_recovery',
    'application.test_graph_vocabulary',
    'application.test_tui_folding',
    'application.test_tui_graph',
    'application.test_tui_intake',
    'application.test_tui_integrated_recovery',
    'application.test_tui_interpretation',
    'application.test_tui_judgment_context',
    'application.test_tui_manuscript',
    'application.test_tui_overview',
    'application.test_tui_personal',
    'application.test_tui_proposals',
    'application.test_tui_proposals_terminal',
    'application.test_tui_ports',
    'application.test_tui_project',
    'application.test_tui_project_source',
    'application.test_tui_recovery',
    'application.test_tui_resume_review',
    'application.test_tui_review',
    'application.test_tui_review_writing_recovery',
    'application.test_tui_terminal',
    'application.test_tui_understanding',
    'application.test_tui_view',
    'application.test_tui_wording_link',
    'application.test_tui_wording_recovery',
    'application.test_tui_work_links',
    'application.test_tui_workflow',
    'application.test_cli',
    'application.test_graph',
    'application.test_workspace',
    'application.test_review_session',
    'application.test_project_initialization',
    'application.test_project_source_refresh.SourceRefreshTests',
    'application.test_project_work.ProjectAssociationTests',
    'application.test_project_work.AssociationBoundaryTests',
    'application.test_project_work.RetainedWorkTests',
    'application.test_project_work.ReviewRegressionTests',
    'application.test_paper_work_store.PaperWorkContractTests',
    'application.test_tui_work_recovery.WorkRecoveryTests',
    'application.test_work_commands.ArchiveFileTests',
    'application.test_source_artifact',
)
ALPHA_EXCLUDED_TESTS = frozenset((
    'application.test_tui_integrated_recovery.IntegratedRecoveryTests.test_injected_seal_failure_and_oversize_preserve_native_checkpoint',
    'application.test_tui_project.ProjectTerminalTests.test_last_source_recheck_failure_leaves_no_orphan_checkpoint',
    'application.test_tui_project.ProjectTerminalTests.test_first_question_refuses_external_checkpoint_change_during_prompt',
    'application.test_tui_project.ProjectTerminalTests.test_empty_saved_project_cancel_interrupt_save_failure_and_start',
    'application.test_tui_project.ProjectTerminalTests.test_confirmed_cli_creation_and_wrong_identity_reopen',
    'application.test_tui_project_source.ProjectSourceTests.test_native_source_changes_reopen_same_writing_and_refuse_stale_preview',
    'application.test_tui_project_source.ProjectSourceTests.test_uncertain_native_save_never_claims_not_applied_or_retries',
    'application.test_tui_review_writing_recovery.ReviewWritingRecoveryTests.test_long_shared_originals_reopen_from_device_in_a_fresh_process',
    'application.test_tui_terminal.TerminalProcessTests.test_external_checkpoint_failure_details_and_live_writing_in_real_terminal',
    'application.test_tui_terminal.TerminalProcessTests.test_project_connection_relocation_refresh_and_restart_in_terminal',
    'application.test_tui_terminal.TerminalProcessTests.test_empty_project_first_question_cancel_start_and_reopen',
    'application.test_tui_terminal.TerminalProcessTests.test_selected_project_manual_writing_and_restart_in_real_terminal',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_judgment_reopens_in_actual_terminal',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_checkpoint_interrupt_retains_active_result_editor',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_checkpoint_interrupt_retains_active_claim_editor',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_review_answer_interrupt_keeps_original_context',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_scientific_field_interrupt_keeps_unstaged_input',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_wording_interrupt_retains_original_source',
    'application.test_tui_terminal.TerminalProcessTests.test_encrypted_explanation_interrupt_and_reopen_in_actual_terminal',
    'application.test_tui_work_recovery.WorkRecoveryTests.test_native_uncertain_and_external_checkpoint_keep_live_text_and_require_reopen',
))


def alpha_suite():
    sys.path.insert(0, str(ROOT / "tests"))
    loader=unittest.TestLoader()
    suite=loader.loadTestsFromNames(ALPHA_APPLICATION_TARGETS)
    def cases(value):
        for test in value:
            if isinstance(test,unittest.TestSuite): yield from cases(test)
            else: yield test
    tests=list(cases(suite))
    missing=ALPHA_EXCLUDED_TESTS-{test.id() for test in tests}
    if missing:
        raise HarnessError("Alpha exclusion no longer matches a test: "+", ".join(sorted(missing)))
    return unittest.TestSuite(test for test in tests if test.id() not in ALPHA_EXCLUDED_TESTS)


class HarnessError(ValueError):
    """A selected verification configuration cannot safely run."""


@dataclass(frozen=True)
class Check:
    name: str
    argv: tuple[str, ...]


def make_plan(scopes):
    """Select explicit checks without reading Git, importing tests, or writing."""
    selected = set(scopes)
    if not selected or not selected.issubset(SCOPES):
        raise HarnessError("Select at least one known scope explicitly")

    python = (sys.executable, "-X", "utf8")
    checks = [Check("docs", (*python, "scripts/check_docs.py"))]
    if selected.intersection(("alpha", "core", "all")):
        checks.append(Check("fixture", (*python, "scripts/check_truth_packet.py")))

    def tests(name, directory):
        checks.append(Check(name, (*python, "scripts/verify.py", "--_tests", directory)))

    if selected.intersection(("alpha", "all")):
        checks.append(Check("schemas", (*python, "-m", "scripts.export_research_schema", "--check")))
        checks.append(Check("resources", (*python, "-m", "scripts.export_runtime_resources", "--check")))
    if "all" in selected:
        tests("all-tests", "tests")
    else:
        if selected.intersection(("alpha", "core")):
            tests("contract", "tests/contract")
        if "alpha" in selected:
            tests("alpha-application", "alpha")
        if "core" in selected:
            tests("probes", "tests/probes")
            tests("validation", "tests/validation")
            tests("security", "tests/security")
            tests("application", "tests/application")
        if "journal" in selected:
            tests("journal", "tests/notion_journal")
            tests("skills", "tests/skills")
        if "harness" in selected:
            tests("harness", "tests/harness")
    checks.append(Check("whitespace", ("git", "-c", "core.safecrlf=false", "diff", "--check")))
    return tuple(checks)


def build_environment(temp_root=None, needs_probe=False):
    """Change only child environment; never create or silently choose a root."""
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    if temp_root is not None or needs_probe:
        try:
            root = Path(temp_root if temp_root is not None else tempfile.gettempdir()).resolve(strict=True)
        except (OSError, ValueError, TypeError) as exc:
            raise HarnessError("An existing temporary directory is required") from exc
        if not root.is_dir():
            raise HarnessError("Temporary root must be a directory")
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise HarnessError("Temporary root is inside Git; supply --temp-root outside Git")
        environment["TMP"] = str(root)
        environment["TEMP"] = str(root)
        environment["TMPDIR"] = str(root)
    return environment


def run_suite(suite, stream):
    """Run real tests and preserve the difference between passed and untested."""
    if suite.countTestCases() == 0:
        print("NO TESTS: verification did not run", flush=True)
        return 2
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if result.skipped or result.expectedFailures:
        if result.skipped:
            print(f"SKIPPED COVERAGE: {len(result.skipped)} test(s); see reasons above", flush=True)
        if result.expectedFailures:
            print(f"EXPECTED FAILURES: {len(result.expectedFailures)} test(s); not verified", flush=True)
        return 3
    return 0


def run_checks(checks, root=ROOT, env=None):
    """Run argument vectors sequentially, fail fast, and keep output visible."""
    incomplete = False
    for index, check in enumerate(checks):
        print(f"RUN: {check.name}", flush=True)
        try:
            result = subprocess.run(check.argv, cwd=root, env=env, shell=False)
            code = result.returncode
        except OSError as exc:
            print(f"ERROR: {check.name}: {exc}", flush=True)
            code = 1
        if code == 3:
            incomplete = True
            print(f"INCOMPLETE COVERAGE: {check.name} (skips or expected failures)", flush=True)
        elif code != 0:
            print(f"FAIL: {check.name} (exit {code})", flush=True)
            for later in checks[index + 1:]:
                print(f"NOT RUN: {later.name}", flush=True)
            return 1
        else:
            print(f"PASS: {check.name}", flush=True)
    print("CHECKS COMPLETED WITH INCOMPLETE COVERAGE" if incomplete else "SELECTED CHECKS PASSED", flush=True)
    return 3 if incomplete else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=SCOPES, action="append", help="Repeat to combine scopes")
    parser.add_argument("--plan", action="store_true", help="Print check commands only; do not execute")
    parser.add_argument("--temp-root", type=Path, help="Existing non-Git temporary root for child checks")
    parser.add_argument("--_tests", choices=TEST_ROOTS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.plan and sys.version_info < (3, 10):
        version = ".".join(str(part) for part in sys.version_info[:3])
        print(f"ERROR: Python 3.10 or newer is required; running {version}. "
              "Rerun with a supported interpreter. No checks were run.", file=sys.stderr)
        return 2
    if args._tests:
        if args.scope or args.plan or args.temp_root:
            parser.error("Internal test dispatch cannot be combined with other options")
        sys.path.insert(0, str(ROOT))
        if args._tests=="alpha":
            print("ALPHA COVERAGE: personal/portable application + actual PTY/source artifact; native/encrypted features explicitly excluded.",flush=True)
            try:
                suite=alpha_suite()
            except HarnessError as error:
                print(f"ERROR: {error}",file=sys.stderr)
                return 2
        else:
            suite = unittest.TestLoader().discover(str(ROOT / args._tests), pattern="test_*.py",
                                                   top_level_dir=str(ROOT / "tests"))
        return run_suite(suite, sys.stderr)
    if not args.scope:
        parser.error("--scope is required; use --scope all only for a full regression")
    try:
        checks = make_plan(args.scope)
        if args.plan:
            print(json.dumps({"checks": [{"name": check.name, "argv": check.argv}
                                         for check in checks]}, ensure_ascii=False, indent=2))
            return 0
        environment = build_environment(args.temp_root, needs_probe=bool(
            set(args.scope).intersection(("alpha", "core", "all"))))
        return run_checks(checks, ROOT, environment)
    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("INTERRUPTED: no completed-verification claim", file=sys.stderr)
        sys.exit(130)
