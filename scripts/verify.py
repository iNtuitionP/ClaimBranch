"""Explicit-scope, offline contributor checks. No agent loop or persistent log.

Exit codes: 0 clean success, 1 failed check, 2 invalid input/empty test suite,
3 completed with skips/expected failures, 130 interrupted. This is not a sandbox or
an authorization gate: it executes repository code that the operator trusts.
"""

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
SCOPES = ("docs", "core", "journal", "harness", "all")
TEST_ROOTS = ("tests", "tests/contract", "tests/probes", "tests/validation",
              "tests/notion_journal", "tests/skills", "tests/harness")


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
    if selected.intersection(("core", "all")):
        checks.append(Check("fixture", (*python, "scripts/check_truth_packet.py")))

    def tests(name, directory):
        checks.append(Check(name, (*python, "scripts/verify.py", "--_tests", directory)))

    if "all" in selected:
        tests("all-tests", "tests")
    else:
        if "core" in selected:
            tests("contract", "tests/contract")
            tests("probes", "tests/probes")
            tests("validation", "tests/validation")
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
    if args._tests:
        if args.scope or args.plan or args.temp_root:
            parser.error("Internal test dispatch cannot be combined with other options")
        sys.path.insert(0, str(ROOT))
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
            set(args.scope).intersection(("core", "all"))))
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
