"""Read-only prerequisite guidance; this bootstrap parses on Python 3.8+."""
import importlib
import json
import os
import shutil
import sys

PYTHON_SETUP = [
    {"tool": "conda", "setup": "conda create -n claimbranch python=3.13",
     "check": "conda run -n claimbranch python -m claimbranch doctor",
     "continue": "conda activate claimbranch; then use python -m claimbranch ... for interactive work"},
    {"tool": "uv", "setup": "uv python install 3.13",
     "check": "uv run --no-project --python 3.13 --no-python-downloads python -m claimbranch doctor",
     "continue": "Use the same uv run prefix with python -m claimbranch project init/open ..."},
]


def _mac_developer_git():
    # The system shim can exist without tools; never invoke it to probe readiness.
    selected = "/var/db/xcode_select_link"
    roots = [os.path.realpath(selected)] if os.path.lexists(selected) else [
        "/Library/Developer/CommandLineTools", "/Applications/Xcode.app/Contents/Developer"]
    return any(os.path.isfile(os.path.join(root, "usr/bin/git")) and
               os.access(os.path.join(root, "usr/bin/git"), os.X_OK) for root in roots)


def prerequisite_report():
    python_ready = sys.version_info[:2] == (3, 13)
    curses_ready = False if python_ready else None
    if python_ready and os.name == "posix":
        try:
            importlib.import_module("curses")
            curses_ready = True
        except (ImportError, OSError):
            pass
    prerequisites = {
        "python-3.13": python_ready,
        "unix-curses": curses_ready,
        "git": shutil.which("git") is not None and os.access("/usr/bin/git", os.X_OK)
               and (sys.platform != "darwin" or _mac_developer_git()),
    }
    missing = [name for name, ready in prerequisites.items() if ready is False]
    guidance = []
    if "python-3.13" in missing:
        guidance.append({"prerequisite": "python-3.13", "message":
            "Use Python 3.13 (running %s.%s). Choose an already installed conda or uv; "
            "setup is manual and may download Python. Run checks from the extracted source folder."
            % sys.version_info[:2], "alternatives": PYTHON_SETUP})
    if "unix-curses" in missing:
        guidance.append({"prerequisite": "unix-curses", "message":
            "Use a Unix terminal and Python 3.13 built with working curses/_curses (ncurses). "
            "A virtual environment alone cannot repair a missing extension. Windows TUI is unsupported.",
            "next_action": 'python3.13 -c "import curses; print(\'curses ready\')"',
            "alternatives": PYTHON_SETUP if os.name == "posix" else []})
    if "git" in missing:
        guidance.append({"prerequisite": "git", "message":
            "Project inspection requires executable /usr/bin/git AND git on PATH. "
            "A conda-only Git does not meet the fixed-path check. Install/repair system Git "
            "using your OS tools (macOS Command Line Tools, or your Unix package manager), "
            "then ensure git is on PATH. On macOS, /usr/bin/git and /usr/bin/python3 "
            "can be installer shims: do not run them to probe missing developer tools. "
            "An Xcode-selected toolchain also requires its license accepted through Apple tools; "
            "license acceptance is not probed here. ClaimBranch does not install tools or invoke the shims.",
            "next_action": "Rerun doctor with your installed Python 3.13 after repairing system Git."})
    return {"prerequisites": prerequisites, "missing_prerequisites": missing,
            "prerequisite_guidance": guidance, "supported_python": "3.13",
            "next_action": "Rerun doctor with your installed Python 3.13; use the conda/uv check command "
                           "in the guidance if python3.13 is not on PATH." if missing else
                           "python3.13 -m claimbranch project init --help"}


def print_guidance(report):
    for item in report["prerequisite_guidance"]:
        print(item["prerequisite"] + ": " + item["message"])
        if "next_action" in item:
            print("  Check: " + item["next_action"])
        for option in item.get("alternatives", []):
            print("  " + option["tool"] + " setup: " + option["setup"])
            print("  " + option["tool"] + " check: " + option["check"])
            print("  Continue: " + option["continue"])


def unsupported_runtime(argv):
    """Refuse before importing application syntax or reading project files."""
    report = prerequisite_report()
    report.update({"status": "personal-alpha-unavailable", "personal_workspace": "unavailable",
                   "synthetic_replay": "not-run", "paper_replay": "not-run",
                   "authorization_verified": False,
                   "reason": "Application requires Python 3.13; no application commands ran."})
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(report["reason"])
        print_guidance(report)
        print("Next action: " + report["next_action"])
    return 3
