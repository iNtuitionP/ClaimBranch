"""Behavior of the implementation harness, not a test of its prose."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import verify
except ImportError:
    verify = None


ROOT = Path(__file__).resolve().parents[2]


class VerificationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(verify, "The implementation verification runner is missing")

    def test_core_checks_dependent_storage_and_original_fixture(self):
        self.assertEqual(
            ["docs", "fixture", "contract", "probes", "validation", "security", "application", "whitespace"],
            [check.name for check in verify.make_plan(["core"])],
        )

    def test_alpha_has_explicit_portable_coverage_and_does_not_replace_core(self):
        self.assertEqual(['docs','fixture','schemas','resources','contract','alpha-application','whitespace'],
                         [c.name for c in verify.make_plan(['alpha'])])
        self.assertEqual(1,sum(c.name=='contract' for c in verify.make_plan(['alpha','core'])))
        self.assertEqual(['docs','fixture','schemas','resources','all-tests','whitespace'],
                         [c.name for c in verify.make_plan(['alpha','all'])])

    def test_alpha_selection_keeps_personal_and_real_terminal_tests_and_names_exclusions(self):
        def cases(suite):
            for case in suite:
                if isinstance(case,unittest.TestSuite): yield from cases(case)
                else: yield case
        selected=list(cases(verify.alpha_suite()))
        ids={t.id() for t in selected}
        self.assertTrue(any('test_personal_archive' in key for key in ids))
        self.assertTrue(any('test_personal_result_record_correction_next_question_and_restart' in key for key in ids))
        self.assertTrue(any('test_writing_checkpoint' in key or 'test_failed' in key for key in ids))
        # Exclude native Mac test modules, not portable policy tests whose
        # method names describe Mac sandbox rules without executing them.
        self.assertFalse(any(key.split('.')[1].startswith('test_mac_') for key in ids))
        self.assertIn('application.test_codex_app_server.CodexAppServerTests.'
                      'test_mac_policy_closes_mach_lookup_and_authorization_except_observed_os_services', ids)
        for excluded in verify.ALPHA_EXCLUDED_TESTS: self.assertNotIn(excluded,ids)
        self.assertFalse(any(getattr(t,'__unittest_skip__',False) or
            getattr(getattr(t,t._testMethodName),'__unittest_skip__',False) for t in selected))

    def test_stale_alpha_exclusion_is_a_configuration_error_before_running(self):
        errors=io.StringIO()
        with patch.object(verify,'ALPHA_EXCLUDED_TESTS',frozenset({'missing.alpha.test'})), \
             patch.object(verify,'run_suite',side_effect=AssertionError('suite started')), \
             redirect_stdout(io.StringIO()), redirect_stderr(errors):
            self.assertEqual(2,verify.main(['--_tests','alpha']))
        self.assertIn('missing.alpha.test',errors.getvalue())

    def test_scopes_are_deduplicated_and_full_discovery_runs_only_once(self):
        plan = verify.make_plan(["journal", "docs", "journal"])
        self.assertEqual(["docs", "journal", "skills", "whitespace"], [c.name for c in plan])
        full = verify.make_plan(["core", "all", "harness", "journal"])
        self.assertEqual(["docs", "fixture", "schemas", "resources", "all-tests", "whitespace"], [c.name for c in full])

    def test_invalid_or_missing_scope_does_not_silently_run_everything(self):
        for scopes in ([], [""], ["made-up"], ["core", "made-up"]):
            with self.subTest(scopes=scopes), self.assertRaises(verify.HarnessError):
                verify.make_plan(scopes)

    def test_temp_root_must_exist_and_not_be_inside_git(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            repo = root / "repository"
            repo.mkdir()
            (repo / ".git").mkdir()
            child = repo / "temporary"
            child.mkdir()
            for location in (repo, child, root / "missing"):
                with self.subTest(location=location), self.assertRaises(verify.HarnessError):
                    verify.build_environment(location, needs_probe=True)
            self.assertFalse((root / "missing").exists())

    def test_explicit_temp_override_is_child_only(self):
        before = dict(os.environ)
        with tempfile.TemporaryDirectory() as scratch:
            # Caller-selected test root must meet the same boundary as the probes.
            root = Path(scratch).resolve()
            if any((parent / ".git").exists() for parent in (root, *root.parents)):
                self.skipTest("Run harness tests with an existing non-Git TMP/TEMP")
            environment = verify.build_environment(root, needs_probe=True)
            self.assertEqual(str(root), environment["TMP"])
            self.assertEqual(str(root), environment["TEMP"])
            self.assertEqual(before, dict(os.environ))

    def test_plan_is_read_only_and_independent_of_invocation_directory(self):
        with tempfile.TemporaryDirectory() as scratch:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/verify.py"), "--scope", "harness", "--plan"],
                cwd=scratch, capture_output=True, text=True, encoding="utf-8", timeout=20,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(["docs", "harness", "whitespace"],
                             [check["name"] for check in json.loads(result.stdout)["checks"]])
            self.assertEqual([], list(Path(scratch).iterdir()))

    def test_cli_requires_explicit_scope(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/verify.py"), "--plan"],
                                cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(2, result.returncode)

    def test_unsupported_python_stops_before_checks_or_test_discovery(self):
        # Without the preflight, an old interpreter launches checks and emits
        # import/setup errors instead of identifying the missing prerequisite.
        for arguments in (["--scope", "all"], ["--_tests", "tests"]):
            output, errors = io.StringIO(), io.StringIO()
            with self.subTest(arguments=arguments), \
                    patch.object(sys, "version_info", (3, 9, 6)), \
                    patch.object(verify, "run_checks", side_effect=AssertionError("checks started")), \
                    patch.object(unittest.TestLoader, "discover", side_effect=AssertionError("discovery started")), \
                    redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(2, verify.main(arguments))
            self.assertEqual("", output.getvalue())
            self.assertIn("3.10", errors.getvalue())
            self.assertIn("3.9.6", errors.getvalue())

    def test_supported_python_boundary_allows_checks(self):
        # Rejecting the documented minimum would incorrectly block supported hosts.
        for version in ((3, 10, 0), (3, 13, 0)):
            with self.subTest(version=version), \
                    patch.object(sys, "version_info", version), \
                    patch.object(verify, "run_checks", return_value=3):
                self.assertEqual(3, verify.main(["--scope", "docs"]))

    def test_plan_still_previews_without_a_supported_test_runtime(self):
        # --plan describes commands only; its success is never test evidence.
        output = io.StringIO()
        with patch.object(sys, "version_info", (3, 9, 6)), redirect_stdout(output):
            self.assertEqual(0, verify.main(["--scope", "core", "--plan"]))
        self.assertEqual(["docs", "fixture", "contract", "probes", "validation", "security", "application", "whitespace"],
                         [check["name"] for check in json.loads(output.getvalue())["checks"]])

    def test_full_discovery_works_with_the_existing_test_directory_layout(self):
        # Discover actual modules but do not recursively execute this suite.
        # tests/ is intentionally not a package; its suite directories are.
        with patch.object(verify, "run_suite", return_value=0) as run:
            self.assertEqual(0, verify.main(["--_tests", "tests"]))
        self.assertGreater(run.call_args.args[0].countTestCases(), 0)

    def test_real_child_failure_stops_later_checks(self):
        with tempfile.TemporaryDirectory() as scratch:
            marker = Path(scratch) / "must-not-exist"
            checks = (
                verify.Check("failure", (sys.executable, "-c", "raise SystemExit(7)")),
                verify.Check("later", (sys.executable, "-c",
                    "from pathlib import Path; import sys; Path(sys.argv[1]).touch()", str(marker))),
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = verify.run_checks(checks, ROOT, dict(os.environ))
            self.assertEqual(1, result)
            self.assertFalse(marker.exists())
            self.assertIn("NOT RUN: later", output.getvalue())

    def test_missing_executable_is_failure_not_success(self):
        with tempfile.TemporaryDirectory() as scratch, redirect_stdout(io.StringIO()):
            checks = (verify.Check("missing", (str(Path(scratch) / "no-program"),)),)
            self.assertEqual(1, verify.run_checks(checks, ROOT, dict(os.environ)))

    def test_skipped_check_does_not_hide_subsequent_failure(self):
        checks = (
            verify.Check("skip", (sys.executable, "-c", "raise SystemExit(3)")),
            verify.Check("failure", (sys.executable, "-c", "raise SystemExit(1)")),
        )
        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, verify.run_checks(checks, ROOT, dict(os.environ)))

    def test_skipped_check_continues_but_cannot_return_clean_success(self):
        checks = (
            verify.Check("skip", (sys.executable, "-c", "raise SystemExit(3)")),
            verify.Check("success", (sys.executable, "-c", "pass")),
        )
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(3, verify.run_checks(checks, ROOT, dict(os.environ)))
        self.assertIn("PASS: success", output.getvalue())
        self.assertIn("INCOMPLETE COVERAGE", output.getvalue())

    def test_child_receives_exact_cwd_environment_and_literal_arguments(self):
        with tempfile.TemporaryDirectory(prefix="harness space ") as scratch:
            root = Path(scratch).resolve()
            code = ("import os,sys; from pathlib import Path; "
                    "assert Path.cwd() == Path(sys.argv[1]); "
                    "assert os.environ['CLAIMBRANCH_HARNESS_TEST'] == 'child-only'; "
                    "assert sys.argv[2] == 'literal ; & value'")
            environment = dict(os.environ, CLAIMBRANCH_HARNESS_TEST="child-only")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, verify.run_checks((verify.Check("arguments", (
                    sys.executable, "-c", code, str(root), "literal ; & value")),), root, environment))

    def test_zero_discovered_tests_is_not_a_pass(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, verify.run_suite(unittest.TestSuite(), io.StringIO()))

    def test_known_failed_assertions_cannot_be_a_clean_pass(self):
        class KnownFailure(unittest.TestCase):
            @unittest.expectedFailure
            def runTest(self):
                self.assertEqual(1, 2)

        output = io.StringIO()
        with redirect_stdout(output):
            result = verify.run_suite(unittest.TestSuite([KnownFailure()]), io.StringIO())
        self.assertEqual(3, result)
        self.assertIn("EXPECTED FAILURES: 1", output.getvalue())

    def test_test_outcomes_remain_distinguishable(self):
        class Examples(unittest.TestCase):
            def succeeds(self):
                self.assertEqual(2, 1 + 1)

            def fails(self):
                self.fail("deliberate controlled failure")

            def skips(self):
                self.skipTest("deliberate unavailable capability")

        for name, expected in (("succeeds", 0), ("fails", 1), ("skips", 3)):
            with self.subTest(name=name), redirect_stdout(io.StringIO()):
                self.assertEqual(expected, verify.run_suite(
                    unittest.TestSuite([Examples(name)]), io.StringIO()))


if __name__ == "__main__":
    unittest.main()
