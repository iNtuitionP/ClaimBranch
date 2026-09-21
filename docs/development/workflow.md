---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-09-21
canonical_for: repository-local validation commands and documentation enforcement
---

# Repository checks

For the user-selected native execution loop and grouped verification commands,
see the [implementation harness](implementation-harness.md). The individual
commands below remain supported; the harness delegates to these same checkers.

There is no application build or test stack yet. Documentation validation and
the repository-owned Notion journal helper require Python 3.10 or newer; CI
currently uses Python 3.13.

From the repository root, run:

```powershell
python scripts/check_docs.py
```

Validate the committed partial P0 saturation source fixture and its adversarial
contract suite without network access or third-party packages:

```powershell
python scripts/check_truth_packet.py
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

The first command verifies the closed artifact inventory, SHA-256 digests,
cross-file references, expected impact truth set, manuscript markers, blank
baseline, offline frozen proposal, size limits, and privacy guards. The second
command exercises both the valid packet and malformed, tampered, traversal,
link, leakage, and semantic-mismatch cases. A skipped link test on Windows
means the current account could not create a symbolic link; Linux CI exercises
that case.

Run the non-authoritative first-pass contract model:

```powershell
python -m unittest discover -s tests/contract -p "test_*.py" -v
```

This synthetic, in-memory model checks undecided entry, exact rationale reuse,
append-only observation corrections, evidence/manuscript-bound review freshness,
and the proposal-only model ingress. The
[five hypothetical cases](../validation/cases/saturation.md#12-augmented-synthetic-contract-oracles)
extend software-contract coverage, not the original research findings.
Manuscript anchors, hashes, and monotonic revisions are supplied by the caller;
the model does not read files or detect external edits. A draft is not a
canonical ResearchEpisode or accepted judgment; a review digest is not a
human authorization receipt. There is no accepted-write or persistence API.
Passing these tests does not prove user understanding, OS process isolation,
or P1 completion. The [early-slice plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#p1-early-slice-first-pass-and-placement-contracts)
owns the scope. This suite is a local check, not a configured CI job.

The same contract suite now includes `review_binding.py`: a pure synthetic
binding of the complete review to an action digest, session, and expiry. It
reuses the entered rationale and rejects changed or expired context. It reads
no files or clock, writes no state, and issues no human authorization. Callers
must provide a freshly prepared current review; the public digest is forgeable
and repeated matching does not consume a receipt. Run this slice alone with
`python -m unittest tests.contract.test_review_binding -v`.
The [A1 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#a1-bind-one-exact-review-to-one-proposed-action)
owns its enforcement limits and the separate real-authorization work.

## Read-only graph walkthrough

Inspect the fixed synthetic case now, without configuring AI or a workspace:

```powershell
python -B -m scripts.graph_demo show
python -B -m scripts.graph_demo show --view main
python -B -m scripts.graph_demo diff
python -B -m scripts.graph_demo preview --select relation:O-03
python -B -m scripts.graph_demo preview --select claim-status --select interpretation --select relation:O-03
python -B -m scripts.graph_demo diff --format json
```

Run from the repository root. `show` defaults to the candidate view; `main`
and `candidate` are calculated fixture views, not saved research branches.
The Korean presentation retains scientific statements and rationales in their
original fixture language. `diff` lists the five selectable changes. Repeat
`--select` to combine changes; without it, `preview` keeps the initial view.
Selecting the compression relationship does not silently select the competing
interpretation, claim-status change, or the other relationships.

Preview lists selected and omitted changes, required existing records, and
explicit paths to the manuscript anchor. These are structural review paths,
not proof of scientific causality or production merge validity. No path means
no recorded path, not no possible scientific impact. Both views retain the
same observations; this command does not accept evidence or copy it into a
branch. Every invocation verifies the existing fixture integrity first.

This contributor prototype writes no research state, journal, approval, or
manuscript and makes no provider call. It accepts no project, input-file,
output-file, or apply option. Successful `--format json` output is one
deterministic UTF-8 document with `applied: false`; invalid input exits 2 with
an error on stderr and no success output. It is not the planned installed
`claimbranch` CLI, full H0 demo, or a decision about the final UI. Run its
tests with `python -m unittest tests.contract.test_graph_demo -v`.
The [bounded increment](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#read-only-graph-cli-continuity-increment)
owns its remaining gates and retirement point.

## Storage and isolation probes

Run the synthetic storage and Windows-isolation experiments without research
data or Notion access:

```powershell
python -m unittest discover -s tests/probes -p "test_*.py" -v
```

The storage experiment creates and cleans up only probe-prefixed temporary
sandboxes. Its project factory selects distinct project locations under an explicitly
supplied external root and binds later operations to that project identity;
it does not select a production data directory or association format.
Its temporary root must be writable and outside every Git working tree. If
the operating system's default temporary directory is inside a Git tree,
select an existing non-Git temporary directory through `TMP`/`TEMP` for the
test process only; do not weaken the location check or change machine settings.
An unavailable directory-link capability is reported as a skipped test, not
verified protection. The augmented storage test passes the exact synthetic
first-pass judgment through the existing store, kills a real child process
before/after commit, and checks reopen/retry without a second entry or manuscript
modification. The SQLite backend is disposable experimental code, not
the application stack. The two process-exit cut points do not prove power-loss,
initialization-crash, concurrent-writer, or adversarial filesystem-race safety.
See the [bounded probe plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-independent-storage-probe)
for its scope and retirement gate. This suite is currently a local check, not
a configured CI job.

Run only the Windows isolation checks:

```powershell
python -m unittest tests.probes.test_windows_isolation -v
```

This separate experiment uses existing Windows APIs and the installed .NET
Framework C# compiler to run a tiny trusted file-access helper, not a model or
application. The ordinary helper must write fake accepted state and manuscript
text, read a fake signing secret, and write a proposal. A real AppContainer
helper must receive access-denied errors for the first three while still
writing the proposal; launch failure is not a successful denial. Protected
bytes must remain unchanged after the restricted run.

It uses the same non-Git temporary-root requirement, rejects reparse-point
topology, and changes filesystem ACLs only on its newly created sandbox.
Windows also creates a uniquely named per-user AppContainer profile with
OS-managed folders/registry storage; the probe deletes only the exact profile
it successfully created and removes its sandbox. An unsupported OS skips the
real Windows test. Missing compiler or Windows setup/runtime/cleanup failure
fails rather than skips. Host termination can prevent cleanup; never infer a
completed result from an interrupted run or sweep other profiles/directories.

The [isolation probe plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#windows-isolation-probe)
owns its evidence and limits. It proves neither model-server isolation,
network/IPC confinement, human presence, receipt issuance, nor general sandbox
escape resistance. No .NET, Python, or AppContainer production-stack choice is
made by using this disposable helper. The suite remains a local check, not CI.

Run the local-first Notion journal helper suite without contacting Notion:

```powershell
python -m unittest discover -s tests/notion_journal -p "test_*.py" -v
```

This suite uses temporary Git repositories and injected temporary state roots.
It must not use the contributor's real `LOCALAPPDATA` journal state or require
OAuth.

Validate the repository-scoped Notion journal skills:

```powershell
python -m unittest discover -s tests/skills -p "test_*.py" -v
```

This suite verifies skill discovery metadata, invocation policy, documentation
links, platform-safe encoding, adversarial safety contracts, and the record
skill's deterministic query/create projection and update denial. It is offline and uses
only injected temporary journal state.

The documentation checker validates repository-owned Markdown links and
headings, required agent instruction files, canonical-document front matter
and location, nearest index membership, overall reachability, ADR shape/status
index parity, and ExecPlan shape.

GitHub Actions runs the documentation, source-fixture, validation, and skill
checks on every push and pull request. The source-fixture suite runs on both
Ubuntu and Windows so Windows junction rejection is exercised continuously.
Repository administrators must configure both `Documentation / check` and
`Documentation / windows-validation` as required branch-protection checks for
CI failure to block merges. Without that external setting, the workflow
reports violations but cannot by itself prevent a merge.

Agent instructions guide semantic maintenance; static checks cannot prove that
prose matches code or user intent. Review affected canonical documents in the
same change and update `last_reviewed` only after checking their inputs.

When an application implementation stack is selected, add reproducible setup,
build, test, lint, fixture, release, and troubleshooting commands to this area
in the same change. Do not store personal shell aliases or machine-specific
paths here.
