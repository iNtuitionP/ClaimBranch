# ClaimBranch

<p align="center">
  <img src="docs/assets/claimbranch-banner.svg" alt="ClaimBranch — Evidence stays. Claims branch. The researcher remains the author." width="100%">
</p>

<p align="center">
  <strong>A research workspace for the argument behind your paper.</strong><br>
  Follow claims to evidence. Keep your reason. Pick up where you left off.
</p>

<p align="center">
  <a href="https://github.com/iNtuitionP/ClaimBranch/actions/workflows/docs.yml"><img src="https://img.shields.io/github/actions/workflow/status/iNtuitionP/ClaimBranch/docs.yml?branch=main&style=flat-square&label=checks" alt="GitHub checks"></a>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.13">
  <img src="https://img.shields.io/badge/status-experimental%20alpha-10B981?style=flat-square" alt="Experimental alpha">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-10B981?style=flat-square" alt="MIT License"></a>
  <a href="https://github.com/iNtuitionP/ClaimBranch/stargazers"><img src="https://img.shields.io/github/stars/iNtuitionP/ClaimBranch?style=flat-square" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://github.com/iNtuitionP/ClaimBranch/releases/tag/v0.1.0-alpha.2">Download alpha</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#your-own-paper">Your own paper</a> ·
  <a href="#what-works-today">Features</a> ·
  <a href="#ai-status">AI status</a> ·
  <a href="docs/README.md">Docs</a> ·
  <a href="https://github.com/iNtuitionP/ClaimBranch/issues">Feedback</a>
</p>

Git remembers which files changed. Experiment trackers remember which run won.
**ClaimBranch helps you remember why you changed your mind.**

Build the paper's argument from its thesis to claims, observations and experiments.
Form your judgment in that context, record your reason once, and return to the
same evidence and unfinished work later.

> **Personal terminal alpha.** Manual research, save/restart and local backup/restore
> work. The Mac Codex connection is a release candidate undergoing final live validation.
> Manuscript files stay read-only.

<p align="center">
  <img src="docs/assets/terminal-preview.svg" alt="Actual synthetic terminal snapshot: thesis, main claims, shared evidence, a run and an unrun experiment plan. AI is off." width="100%">
</p>
<p align="center"><sub>Bundled synthetic example, captured from <code>demo tui --snapshot --ai-off</code>. No real research data.</sub></p>

## Why ClaimBranch?

- **Read the argument.** Follow the thesis through claims to shared evidence and
  experiments, with typed connections and their rationale.
- **Make the judgment once.** Write while interpreting the result; reuse that
  judgment and reason when recording the consequence.
- **Keep inconvenient evidence.** Corrections append history. Another
  interpretation does not make an earlier result disappear.
- **Return without losing the thread.** Notes, judgments, unfinished writing and
  saved history survive a fresh process or a local backup restore.
- **Keep authorship visible.** The AI design preserves proposal origins through
  human edits. A suggestion never becomes evidence or a decision automatically.

**Evidence stays. Claims branch. The researcher remains the author.**

## Quick start

Requires **Python 3.13**, Python's `curses`, working Git at `/usr/bin/git` and a Unix terminal.
The personal workflow uses the Python standard library: no Python packages,
API key, browser, native approval key or model server is needed.

```sh
git clone https://github.com/iNtuitionP/ClaimBranch.git
cd ClaimBranch
python3.13 -m claimbranch doctor
python3.13 -m claimbranch demo tui --ai-off
```

The demo opens a synthetic paper and keeps work only for the running session.
To see plain output without an interactive terminal:

```sh
python3.13 -m claimbranch demo tui --snapshot --ai-off
```

**macOS is locally verified.** Ubuntu/macOS CI is configured for portable checks.
SSH/tmux, physical IME, unfamiliar-user usability and Windows product support
remain unverified. [Setup and support details →](docs/development/workflow.md#personal-terminal-alpha-source)

## Your own paper

Use an existing local Git paper with a UTF-8 `.tex` source. Add one marked block
yourself in your editor; ClaimBranch reads it without changing your manuscript:

```tex
% claimbranch:start id=anchor
Your paper wording goes here.
% claimbranch:end id=anchor
```

Create a new private work directory **outside every Git repository**:

```sh
mkdir -m 700 "$HOME/claimbranch-work"
python3.13 -m claimbranch project init \
  --directory "$HOME/claimbranch-work" \
  --paper-root /path/to/your-paper \
  --manuscript paper.tex
```

Replace the paper path and filename with your own. Init asks for the title,
working thesis and first unresolved question. Read the preview, then type
`create`. Your project starts with your writing and no fabricated observations.
To resume after quitting:

```sh
python3.13 -m claimbranch project open --directory "$HOME/claimbranch-work"
```

| In the terminal | What it does |
|---|---|
| Arrow keys / `Enter` | Move through the graph / read a record |
| `r` | Follow a recorded relationship |
| `;` / `?` | Open named actions / show help |
| `n` / `e` | Write a node note / write your judgment and reason |
| `Ctrl+S` / `Esc` in an editor | Keep writing / retain unfinished input separately |
| `q` | Save personal work and quit |

Start with **Draft a result and source**, then explicitly confirm what you
observed. Add claims and typed relationships with your reason. **Record selected
reasoning personally** reviews the consequence in the same context.
Source references are not opened or scientifically verified automatically.

[Full authoring guide →](docs/development/workflow.md#personal-project-writing-in-the-terminal)
 · [Six tasks to try →](docs/validation/cases/saturation.md#personal-alpha-feedback-tasks)

## Save, back up, return

Close the TUI. Create a new private backup directory outside Git:

```sh
mkdir -m 700 "$HOME/claimbranch-backup"
python3.13 -m claimbranch project backup \
  --directory "$HOME/claimbranch-work" \
  --archive-directory "$HOME/claimbranch-backup"
```

Restore into another new private directory:

```sh
mkdir -m 700 "$HOME/claimbranch-restored"
python3.13 -m claimbranch project restore \
  --directory "$HOME/claimbranch-restored" \
  --archive-directory "$HOME/claimbranch-backup"
python3.13 -m claimbranch project open --directory "$HOME/claimbranch-restored"
```

Backups contain **saved** project history and kept/unfinished writing. They exclude
unsaved input, manuscript files and external experiment artifacts. Personal files
and backups are **unencrypted**; private permissions do not stop another
unrestricted process running as the same user.

[Backup, export and recovery details →](docs/development/workflow.md#personal-project-writing-in-the-terminal)

## What works today

| Capability | Current availability |
|---|---|
| Thesis, main/subclaims, shared evidence and typed relationships | Manual personal workspace |
| Result capture, explicit confirmation and append-only correction | Available |
| Judgment, reason, notes and unfinished writing | Save and resume |
| Local backup/export and fresh-directory restore | Available |
| Hypothetical impact and graph comparison | Available; creates no evidence |
| AI proposal selection, editing and retained origin | Retained responses and explicitly labeled external imports |
| Provider configuration and exact unsent context preview | Available; sends nothing |
| Live AI requests | Mac Codex release candidate; final live validation pending |
| Automatic manuscript editing, protected acceptance and debt closure | Deferred |

This is a finite experimental alpha, not a validated research product. Current
bounds include 8 episodes/runs, 16 observations and one selected reasoning merge
per episode. [Scope and limits →](docs/product/releases/validation-prototype.md#55-source-delivery-readiness)

## AI status

The intended flow: select context, inspect what will be sent, request critique,
compare and edit suggestions, then record **your** judgment. AI stays optional
and proposal-only.

The current checkout connects **Mac + Codex CLI 0.158.0 + gpt-6-sol** through
an exact-request review. Final public-route live verification is pending; the
published alpha.2 remains AI-off. Other API/model profiles are preview-only.
An actual public-route discussion now returns readable advice and retains it
after reopening. Direct edit and complete connected-use/release checks remain
pending; this is not yet a qualified AI release. The earlier typed-response
failure remains recorded in the execution plan.

Use your existing Codex ChatGPT login, with no API key or copied token:

```sh
mkdir -m 700 "$HOME/claimbranch-provider"
python3.13 -m claimbranch provider configure-codex \
  --directory "$HOME/claimbranch-provider" --model gpt-6-sol
python3.13 -m claimbranch project open \
  --directory "$HOME/claimbranch-work" \
  --provider-directory "$HOME/claimbranch-provider"
```

Press `A` in the graph, choose context, read the complete request, then explicitly
send. Requests may use your account allowance; service retention is not verified.
The response is a proposal: choose items, compare, edit and record your own reason.
Without a provider profile, manual work and saved AI origins remain available.
There is no automatic retry, fallback, background request or manuscript write.

The current checkout also offers **Discuss this argument with AI** in `;` actions:
write a question, choose context and inspect the exact request. This candidate
path reads plain-text advice without converting the answer into graph items.
Its answer reader offers explicit passage-to-claim/plan/connection drafts; a
separate **Prepare a small edit with AI** action takes a bounded instruction.
Selected candidates can be recorded with your original reason; their AI source,
human edits and unfinished explanation survive local restart and backup restore.
Owned terminal/save/return checks and one actual discussion reply pass. Actual
service validation of direct edit requests and complete connected-use validation
remain pending.

[Supported setup and current verification →](docs/development/workflow.md#mac-codex-connection-release-candidate)
[Discussion controls and limits →](docs/development/workflow.md#contextual-discussion-candidate)
[Review or import an existing AI response →](docs/development/workflow.md#importing-an-external-typed-ai-response)

## Help shape it

Try the [feedback tasks](docs/validation/cases/saturation.md#personal-alpha-feedback-tasks)
with disposable work, then [open an issue](https://github.com/iNtuitionP/ClaimBranch/issues).
Tell us your task, what happened, and where you lost the argument, your reason
or your writing. Include your OS, Python version and visible error.
Keep research files, backups and credentials private.

If preserving the reasoning behind a paper matters to you, star the repository
and follow its development. Concrete feedback improves the next version.

For contributors:

```sh
python3.13 scripts/verify.py --scope alpha --scope harness --temp-root /private/tmp
```

On Linux, use an existing temporary directory outside Git such as `/tmp`.
Read [the contributor workflow](docs/development/workflow.md) and
[AGENTS.md](AGENTS.md) before changing behavior.

## Documentation

| Path | Contents |
| --- | --- |
| `claimbranch/` | Application and domain code, bundled runtime resources |
| `tests/` | Automated checks and synthetic fixtures |
| `schemas/` | Versioned contracts and checked generated schemas |
| `scripts/` | Validation, schema generation and source packaging tools |
| `docs/` | Product philosophy, ADRs, designs, validation and execution plans |
| `.github/` | CI workflows |
| `.agents/`, `.codex/` | Shared contributor skills and hooks |

Local build output and machine-specific settings stay outside source control.
See [repository layout and local artifacts](docs/development/workflow.md#repository-layout-and-local-artifacts)
for placement and ignore rules.

- [Documentation map](docs/README.md) — canonical sources and reading paths.
- [Product philosophy](docs/product/product-spec.md#1-product-definition) — the
  researcher outcome behind graphs, provenance and understanding.
- [Product contracts](docs/product/product-spec.md) — intended behavior beyond this alpha.
- [Architecture decisions](docs/architecture/decisions/README.md) — boundaries and rationale.
- [Implementation plan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#alpha-feedback-and-publication-sequence)
  — verified progress and remaining work.

## License

Released under the [MIT License](LICENSE).
