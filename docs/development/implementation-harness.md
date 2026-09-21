---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-09-19
canonical_for: native agent implementation workflow and grouped verification
---

# Native implementation harness

Build the next useful increment without handing routine mechanics back to the
user or taking ownership of their product judgment. This is the user-selected
workflow for Astra in this repository, not a new agent platform or product
runtime. It consists of the agent entry point in `AGENTS.md`, this procedure,
the existing ExecPlan, and `scripts/verify.py`.

## Execution loop

1. Inspect the dirty checkout and read the documentation map and relevant
   current plan section. Do not reread the entire historical plan by default.
   Separate already approved constraints from unresolved choices.
2. State the next observable outcome, scope, and relevant limitation briefly.
   Continue a requested implementation without another ritual approval of a
   plan, skill, test order, or ordinary code decision. The user explicitly
   excluded the brainstorming approval loop for this workflow.
3. Make the smallest behavior-changing increment. Establish the expected
   failure first when adding a feature or fixing a bug, then implement it.
   Use literal independent expectations; do not test wording merely to freeze
   an implementation. Preserve unrelated changes and existing user edits.
4. Run the affected checks and any required regression suite. Investigate
   failures before changing code; do not weaken an invariant to get green.
   Broaden or repeat checks only after another change, a failure, an uncovered
   risk, or an explicit requirement. A required full suite is not optional.
5. For a significant change, use one focused independent review where tools
   and instructions permit. Delegate only work that can genuinely proceed
   independently, with bounded file ownership and explicit requirements.
   Do not dispatch an agent for each trivial step or automatically apply every
   suggestion. Fix concrete defects, preserving the product's focus.
6. Update the existing plan's progress, evidence, and next safe action. Report
   what now works, what was actually checked, and what remains unverified.
   Continue an authorized next increment when no human-owned choice blocks it.

This is task-scoped autonomy, not an unattended loop. A request to explain or
diagnose does not authorize a fix, publish, migration, or remote write. No
automatic commit, push, dependency installation, machine configuration change,
Notion record, transcript, review queue, or new session log is introduced.

## When to ask

Ask because the answer changes the outcome, not merely because a decision can
be made deterministically. Explain the evidence, consequence, recommendation,
and actual alternative in one focused question.

| Continue within the authorized task | Stop the affected work and ask |
|---|---|
| Choose a private helper name or targeted test | Change what the product promises or deliberately excludes |
| Implement an already agreed invariant | Infer real research meaning or confirm source fidelity |
| Repair a reproduced defect without changing the contract | Adopt an unresolved production stack, trust perimeter, or recovery/key-loss trade-off |
| Run offline tests with synthetic disposable data | Access new private sources, change existing permissions, destroy data, publish, or transmit data |
| Update an existing plan with observed results | Treat an unverified external model server as safe |

Do not ask the user to re-decide a recorded choice. Missing mechanics may be
resolved locally; missing authority may not. Independent safe work can continue
while waiting, but the affected branch must not proceed under an assumed answer.
The [phase-specific checkpoints](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#human-decision-checkpoints)
remain authoritative. The Notion journal keeps its existing separate interview,
semantic confirmation, and exact-write approval workflow; a coding request
does not authorize journal activity.

## Run verification

Use Python 3.10 or newer from any working directory; give the script's full path
when outside the checkout. A scope is mandatory. The runner never infers task
ownership from the many pre-existing dirty files or invents a minimal safe scope.
The agent selects scopes from the files and dependencies actually changed.

```powershell
python scripts/verify.py --scope core --plan
python scripts/verify.py --scope harness
python scripts/verify.py --scope core --scope journal
python scripts/verify.py --scope all
```

| Scope | Checks, in addition to documentation and tracked-diff whitespace |
|---|---|
| `docs` | none |
| `core` | original fixture, contract, dependent storage/isolation probes, validation |
| `journal` | local journal and repository skill suites; no live Notion access |
| `harness` | verification runner tests |
| `all` | original fixture and one complete unittest discovery |

Scopes combine without duplication. `all` subsumes the individual suites.
`--plan` prints argument vectors only; it does not import tests, run commands,
query Notion, create state, or verify that the environment is usable. An exit
code of zero from a preview is not verification evidence.

Core/full runs require an existing non-Git temporary root, including all its
ancestors. If the default fails that check, explicitly supply
`--temp-root <existing-non-git-directory>`. The runner changes only child-process
`TMP`, `TEMP`, and `TMPDIR`; it does not create a root, weaken the check, or alter
machine settings. Actual writability is verified when the tests create data.

The runner executes repository-owned argument vectors without a shell and
streams their output. It stops after a failed check and names remaining checks
as `NOT RUN`; skips and expected failures permit later checks but remain an
incomplete result. A known failed assertion is not a clean pass. Test
discovery with zero tests is rejected. There is no persisted result cache,
automatic retry, background worker, timeout/descendant-process supervisor, or
resume daemon. Use the host execution controls if a command hangs; interrupted
runs are not verification evidence and must not be silently reported as green.

| Exit | Meaning |
|---|---|
| `0` | selected checks completed without skips/expected failures, or a requested preview succeeded |
| `1` | a check failed or could not start; later checks did not run |
| `2` | invalid selection/environment, or internal test dispatch found no tests |
| `3` | checks completed with skips or expected failures; inspect the reasons |
| `130` | runner interrupted |

This tool is not a sandbox, an approval system, or protection against malicious
repository test code. Passing a selected scope does not prove omitted suites,
human understanding, original-source fidelity, OS isolation, or a release gate.
The runner does not modify CI or silently replace CI's existing commands.

## Why this fits Astra

Use the model's judgment to integrate context and resolve routine mechanics;
use executable checks for observable claims. This follows the official
[Astra guidance on initiative, delegation, and proportionate verification](https://developers.openai.com/api/docs/guides/latest-model).
The concise project entry point follows
[Codex's AGENTS.md discovery mechanism](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
These are design inputs, not evidence that this repository workflow outperforms
another model or guarantees adherence. No account-wide setting, API call,
model identifier, or reasoning-effort override is installed by this harness.
