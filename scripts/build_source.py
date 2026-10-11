"""Build a reproducible personal terminal alpha; never commit or publish it."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from scripts.export_runtime_resources import ROOT, check_resources, require_unlinked

MAX_SOURCE_MEMBERS = 131

README = """ClaimBranch experimental personal terminal alpha

Prerequisites: Python 3.13, Python curses, system Git (/usr/bin/git) and a Unix terminal.
No third-party Python packages, native Mac tools, keys, browser or AI account.
macOS is locally verified. Linux portability/CI checks are supplied; remote
CI, SSH/tmux, physical IME and unfamiliar-user observations remain separate.
Unzip into a new folder and open a terminal there:

    python3.13 -m claimbranch doctor
    python3.13 -m claimbranch project init --help

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
AI is off. Retained AI origin stays visible. No protected acceptance, automatic
manuscript write, debt closure, provider, Windows support or migration is enabled.
provider configure/inspect/preview prepare your own API format, endpoint, model
and environment-secret NAME in a separate private configuration directory.
Run python3.13 -m claimbranch provider configure --help. These commands do not
read keys or send requests; actual provider qualification/live use is unfinished.
project init/open --provider-directory /path/to/private-llm-config explicitly
attaches that profile for contextual unsent previews. The header says AI preview.
A selects recorded science, d includes kept draft text and p selects the task.
Enter prepares exact API content; End reads, Esc returns to manual writing.
The public live gate refuses before key lookup or I/O. Disable/enable previews
through named actions; neither setup nor a saved checkpoint qualifies a provider.
An existing Codex ChatGPT login is separate from an API key. Use
provider configure-codex --directory /path/to/new-private-config --model YOUR_CODEX_MODEL
for a credential-free profile; attach it with the same --provider-directory.
This previews selected APPLICATION INPUT, not CLI-generated HTTP content or send
consent. Its client version is a supported candidate, not observed at setup.
No Codex client, key, attempt, trace or response is created. Actual restricted
CLI execution/return remains unavailable; do not copy login tokens into profiles.
Finite alpha bounds: 8 episodes/runs, 16 observations, 32 evidence events and
64 commands; one interpretation/selected merge per episode. Unsupported extra
work is refused and your writing stays readable. Try disposable work first.

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
