"""Build a reproducible personal terminal alpha; never commit or publish it."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from scripts.export_runtime_resources import ROOT, check_resources, require_unlinked

MAX_SOURCE_MEMBERS = 155

README = """ClaimBranch experimental personal terminal alpha

Prerequisites: Python 3.13, Python curses, system Git (/usr/bin/git) and a Unix terminal.
No third-party Python packages, native Mac tools, keys, browser or AI account.
macOS is locally verified. Linux portability/CI checks are supplied; remote
CI, SSH/tmux, physical IME and unfamiliar-user observations remain separate.
Unzip into a new folder and open a terminal there:

    python3.13 -m claimbranch doctor
    python3.13 -m claimbranch project init --help

If Python 3.13 is missing, choose an already installed tool (manual download):

    conda create -n claimbranch python=3.13
    conda run -n claimbranch python -m claimbranch doctor

Or:

    uv python install 3.13
    uv run --no-project --python 3.13 --no-python-downloads python -m claimbranch doctor

Run from this extracted folder. Python 3.8+ can display prerequisite guidance
with python3 -m claimbranch doctor (3.9.6 verified; 3.8 grammar checked); only
Python 3.13 runs the application. On Macs without Command Line Tools,
/usr/bin/python3 itself may open Apple's installer; use an installed Python.
Doctor checks importable curses/_curses, Git on PATH and executable /usr/bin/git.
Conda Git alone is insufficient; install/repair system Git through OS tools.
On Mac, doctor also checks developer Git behind the system shim without running
it. Xcode-selected tools need their license accepted; doctor does not probe this.
Do not use /usr/bin/git to probe missing tools: it can open Apple's installer.
A missing _curses requires a Python build with ncurses, not pip or a venv alone.
No setup command is executed automatically. Windows TUI is unsupported.
After conda doctor: conda activate claimbranch, then use python -m claimbranch
for all interactive commands; conda run captures output by default. With uv,
use the same uv run prefix above for init/open and all later commands. Setup
routes are documentation-verified, not locally installation-tested.

Use an existing local Git paper and a relative UTF-8 .tex file (at most 64 KiB)
with one marked block, written by you:

    % claimbranch:start id=anchor
    Your paper wording.
    % claimbranch:end id=anchor

Choose a NEW owner-private directory outside all Git trees:

    mkdir -m 700 /path/to/private-work
    python3.13 -m claimbranch project init --directory /path/to/private-work --paper-root /path/to/paper --manuscript paper.tex
    python3.13 -m claimbranch project open --directory /path/to/private-work

Init asks for your title, thesis and unresolved question; type create only after
reading its preview. For --dry-run, supply --title, --thesis and --question.
The app reads the paper and never adds markers, changes wording or compiles it.
; opens named actions, ? shows keys, n writes a note and e writes a judgment.
Manual claim/connection/plan forms work before your judgment is complete.
Draft a result and source, keep its measurement fields, then c previews personal
confirmation. End/PgDn reads the preview, Enter records, Esc cancels. Source
references are not opened or verified automatically. Typed relationships state
support/challenge/qualification and your reason. Record selected reasoning
personally reuses your judgment/reason; G compares the argument graphs.
A separate result draft at an observation permits a to append statement/value
correction with a reason, keeping earlier values. Units/conditions require a
separate run/result. Start the next research question keeps earlier work.
Ctrl+S keeps writing, Esc retains unfinished editor input separately, q saves
and exits. Failed/uncertain saves retain live writing and give reopen guidance.

Personal work and backups are ordinary UNENCRYPTED private local files.
They are personal history, not signed protected authority. Permissions reduce
accidental disclosure but do not stop another unrestricted same-user program.
AI is off unless you explicitly attach your private provider profile. Retained
AI origin stays visible. No protected acceptance, automatic manuscript write,
debt closure, Windows AI support or authority migration is enabled.
provider configure/inspect/preview prepare API profiles without reading keys or
sending requests; generic API and unsupported Codex model routes are preview-only.
The current Mac Codex route is a release candidate. An actual discussion reply
has been received and saved; complete connected-use/release validation is pending.
Use a user-owned direct Codex CLI 0.158.0 executable and its existing private
~/.codex/auth.json ChatGPT login. Keychain-only login, npm wrappers, other client
versions and non-Mac live execution are unsupported; manual work remains usable.
Never copy tokens into profiles. Select the supported model explicitly:

    python3.13 -m claimbranch provider configure-codex --directory /path/to/new-private-config --model gpt-6-sol
    python3.13 -m claimbranch project open --directory /path/to/private-work --provider-directory /path/to/new-private-config

For readable advice, use ; -> Discuss this argument with AI. Write your question
and Ctrl+S opens the context picker. Select recorded science; d explicitly adds
the draft and h explicitly selects earlier replies. No previous reply is included
automatically. Enter prepares complete HTTP content; End reads, Esc cancels, Enter sends only
that reviewed content after runtime checks. Account usage may apply; actual
service retention is unknown. Each request has a 60-second limit, no automatic
retry; at most three attempts per judgment. During the request, m continues
manual writing. A readable answer makes no graph change. In its reader, 1 starts
a claim, 2 an unrun plan and 3 a connection: select an exact passage, inspect the
preview, then prepare an unfinished form. Complete missing fields yourself. A
planned experiment tests its target claim; it supplies no observed result.
For a natural-language edit instruction, use ; -> Prepare a small edit with AI.
This is a separate reviewed request, returning at most four candidate items or
a clarification. This edit route has owned-test coverage but remains unverified
against the actual service. Select items, c compares, G shows graphs and Enter
stages only that batch. Personal recording still needs your judgment/reason and review.
Inspect AI item origins retains the original question, answer, selected passage
or item and later edits. Return to personal explanations preserves partial work.
Local history re-review works with AI off; no saved request consent restores.

Finite alpha bounds: 8 episodes/runs, 16 observations, 32 evidence events and
64 commands; one interpretation/selected merge per episode. Unsupported extra
work is refused and your writing stays readable. Try disposable work first.

For a paper lifecycle, choose project init --profile paper: 64 claims, 256
observations, 256 experiments, 512 scientific edges, 32 episodes, 64 manuscript
anchors and 2048 commands. Existing episode projects retain their original bounds.
project import-argument previews and explicitly registers selected existing
records, preserving original sources, dates, unknown origins and unresolved fields.
project import-metadata --directory /path/to/private-work --input /path/to/private-batch.json
adds ordered typed extensions after complete preview and the literal register.
Use --dry-run to inspect without registration. In the graph, ; -> Register
extended records together opens the same private-file review. Each batch entry
declares human/ai/mixed/unknown content origin; an absent declaration is unknown.
New-input AI influence survives later human edits and save/backup return.
Multiple text/figure/table/caption anchors remain read-only. Wording restrictions,
co-reported interpretations, typed measurement tables, protocol/outcome/gate events
and private critiques have bounded explicit input formats. See repository schemas
and docs/development/workflow.md for formats, scope and unresolved limitations.
Private backup preserves full saved sources. Full readable export refuses histories
with retained metadata/critique input; project share exports explicitly selected
science and project verify-share compares it to that saved private revision.
Sharing never automatically commits, uploads or modifies the paper.

Close the TUI before status/backup/export. Use separate NEW private directories:

    mkdir -m 700 /path/to/private-backup /path/to/private-export /path/to/restored-work
    python3.13 -m claimbranch project status --directory /path/to/private-work --json
    python3.13 -m claimbranch project backup --directory /path/to/private-work --archive-directory /path/to/private-backup
    python3.13 -m claimbranch project export --directory /path/to/private-work --archive-directory /path/to/private-export
    python3.13 -m claimbranch project restore --directory /path/to/restored-work --archive-directory /path/to/private-backup --dry-run
    python3.13 -m claimbranch project restore --directory /path/to/restored-work --archive-directory /path/to/private-backup
    python3.13 -m claimbranch project open --directory /path/to/restored-work

backup.cbp covers verified SAVED project history and kept/unfinished writing;
it excludes unsaved input, manuscript files and external experiment artifacts.
Its checksum detects accidental damage, not authenticity. project.json is a
readable export, not a restore backup. No output or existing work is overwritten.
Dry-run checks backup/basic destination only, reserves no lock and writes nothing.
An interrupted copy may remain incomplete: preserve it and retry in a fresh
private directory. Changed/missing paper leaves original writing/basis intact.
If saving becomes uncertain, copy newer live text before quitting/reopening.
Never edit internal checkpoint files. Research export never uploads automatically.

Optional synthetic examples remain under demo (demo tui, demo saturation,
demo paper); they are separate from your project. Protected/native development
commands remain separate and are not alpha prerequisites.

artifact.json lists each shipped file hash; it is not a publisher signature.
This is an experimental personal alpha, not validated v1.0.
Released under the MIT License; the complete notice is in LICENSE.
For feedback, report the command/task, visible error and where argument meaning,
action discovery, writing reuse or return was difficult. Do not attach private
project/backup content or credentials to a public issue.
""".encode("utf-8")


def build_source(output, *, root=ROOT):
    root = Path(root).resolve(strict=True)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("refusing to replace an existing artifact")
    check_resources(root)
    package = root / "claimbranch"
    require_unlinked(package, root)
    license_path = root / "LICENSE"
    require_unlinked(license_path, root)
    if not license_path.is_file() or license_path.stat().st_size > 64 * 1024:
        raise ValueError("source license is missing or exceeds its budget")
    files = {"START-HERE.txt": README, "LICENSE": license_path.read_bytes()}
    web = {"application/web/" + name for name in ("index.html", "app.js", "graph.js", "app.css")}
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if "__pycache__" in relative.parts or path.name == ".DS_Store":
            continue
        require_unlinked(path, root)
        if path.is_dir():
            continue
        name = relative.as_posix()
        if not path.is_file() or not (path.suffix == ".py" or name in web or name.startswith("data/")
                                     or name in {"application/native/WorkCipher.swift", "application/native/RuntimeIdentity.swift",
                                                 "application/native/ProposalWorker.swift", "application/native/Enrollment.swift",
                                                 "application/native/InitialSource.swift"}):
            raise ValueError("unrecognized runtime file: " + name)
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("runtime file exceeds source-preview budget")
        files["claimbranch/" + name] = path.read_bytes()
    if sum(map(len, files.values())) > 4 * 1024 * 1024:
        raise ValueError("runtime exceeds source-preview budget")
    manifest = {"schema_version": 1, "kind": "personal-terminal-alpha", "python": "3.13",
                "authorization_verified": False,
                "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}}
    files["artifact.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(files) > MAX_SOURCE_MEMBERS:
        raise ValueError("runtime inventory exceeds the source artifact member budget")
    buffer = io.BytesIO()
    # ZIP_STORED also removes zlib-version differences. All metadata is fixed.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    payload = buffer.getvalue()
    with output.open("xb") as handle:
        handle.write(payload)
    return {"kind": manifest["kind"], "sha256": hashlib.sha256(payload).hexdigest(),
            "files": len(files), "authorization_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new ZIP path; parent directory must exist")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_source(args.output), sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
