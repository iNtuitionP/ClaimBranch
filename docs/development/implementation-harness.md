---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-10-12
canonical_for: native agent implementation workflow and grouped verification
---

# Native implementation harness

Build the next useful increment without handing routine mechanics back to the
user or taking ownership of their product judgment. This is the user-selected
workflow for Astra in this repository, not a new agent platform or product
runtime. It consists of the agent entry point in `AGENTS.md`, this procedure,
the existing ExecPlan, and `scripts/verify.py`.

The user explicitly disabled Superpowers skills on 2026-09-22 because of their
token cost. Do not invoke them or reproduce their mandatory rituals. Select
the smallest sufficient workflow for the actual instruction; for implementation
requests, review the plan, implement, and review the result. Reuse context
already read and stop/report material blockers rather than assuming them away.
Scope a blocker to its actual dependencies. A failed OS experiment does not
stop independent domain, schema, projection or offline interaction work already
authorized by the user; report the affected gate and continue those increments.

The current delivery target is the [manual own-project GitHub release](../product/releases/validation-prototype.md#55-source-delivery-readiness),
with its [S01–S04 integration order](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#github-manual-release-implementation-order).
Keep the broader B/R/H/V obligations open; they are not all first-release
prerequisites. Under [ADR 0017](../architecture/decisions/0017-personal-terminal-alpha.md),
the user selected personal local persistence without device keys and wants early
feedback followed by correction. Execute the four selected outcomes, show the
manual loop as soon as it runs, and stop expansion after the alpha is usable.
Do not ask for this storage choice again or resume native work automatically.
Protected accepted writes remain later features with their native guarantees.

## Feedback-first cadence

The user selected quick delivery, feedback and another implementation pass.
Use the existing plan's [three execution batches](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#fast-feedback-and-release-execution).
Finish connected researcher actions, reuse current modules and show a running
checkpoint as soon as it exists. Keep the selected first-release scope fixed;
prioritize preservation, honest lineage and blockers of that journey before
optional polish or new capabilities. Early feedback is not completed release
validation. Do not wait for the full product roadmap before showing it.

Use the review/implementation/result-check loop below, affected checks and one
bounded Opus review per integrated behavior increment. Complete applicable
regression and source/terminal journeys at milestones. Reopen settled plans or
repeat unchanged checks only for a changed requirement, failure or unresolved
risk. Retain the mandatory compaction readings and required safety evidence.

## Resume after context compaction

The user requires a fresh reading after **every** context compaction to avoid
implementation drift. Before further implementation, inspect Git status and
reread the following canonical sources, even if the summary says they were read:

1. [Documentation map](../README.md) and [current availability](../../README.md).
2. The full [product specification](../product/product-spec.md), including
   authorship, understanding, journeys, graph/terminal goals and non-goals;
   both [validation scope](../product/releases/validation-prototype.md) and
   [conditional candidate scope](../product/releases/candidate-mvp.md).
3. [Target architecture](../../ARCHITECTURE.md) and the accepted decisions in
   the [decision index](../architecture/decisions/README.md). Preserve the
   distinction between accepted constraints, draft targets and working code.
4. The existing [ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md):
   purpose, original Dream state, current progress, approved current sequence
   and its dependencies. Historical test logs need not be reread wholesale.
5. For UI work, the [living design](../designs/2026-09-22-episode-review.md)
   purpose/goals, intent audit, human-led construction and current composition;
   the [UI/UX harness](uiux-harness.md) and relevant
   [acceptance oracles](../validation/cases/saturation.md).

Reconcile the next observable researcher action with these sources and the
latest user instruction. Continue previously authorized work without another
approval loop. Ask only if an actual conflict or missing human-owned choice
changes the outcome. Keep progress in the existing plan; do not create a
parallel context or handoff document. This compaction trigger overrides normal
within-session read reuse; it does not require restarting completed work.

## Execution loop

During sustained implementation, revisit the canonical goals at each R
milestone and before a scope, authority or workflow trade-off. After a long
native/security detour, reread the product's
[human outcome](../product/product-spec.md#1-product-definition),
[provenance and understanding contract](../product/product-spec.md#43-provenance-and-understanding-are-independent)
and the plan's [understanding-debt alignment](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#understanding-debt-alignment-review).
State which researcher action the next change improves: forming a judgment
once, inspecting its basis/AI influence, resuming unfinished work or aligning
the manuscript. Do not let a technical test or a growing mechanism list replace
that outcome. Reuse these readings within a coherent increment; periodic
checking is not a timer-driven reread of the entire documentation tree. The
full post-compaction reading above remains mandatory. This implements the
user's 2026-09-29 request to preserve the accumulated philosophy during long work.

1. Inspect the dirty checkout and read the documentation map and relevant
   current plan section. Do not reread the entire historical plan by default.
   Separate already approved constraints from unresolved choices.
2. State the next observable outcome, scope, and relevant limitation briefly.
   In progress updates and the final response, recap the current plan position,
   what is being implemented, and what completing it enables. Distinguish a
   completed increment from remaining platform and product gates.
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
   Group complete relevant integration at outcome milestones and release review;
   do not automatically launch whole-core/native presence tests for every small
   edit. A documentation-only plan change uses docs and relevant documentation
   checks, without a native GUI or fresh key. Hardware/presence observations
   apply to the enabled feature and use one prepared milestone batch. Preserve
   omitted coverage and previous failures; an unavailable host never becomes
   permission to use a software-key fallback or to claim a whole-core pass.
5. Review the result against the intended user outcome and observed checks.
   Use an independent review when a concrete risk justifies its additional cost
   and tools/instructions permit. Delegate only work that can genuinely proceed
   independently, with bounded file ownership and explicit requirements.
   Do not dispatch an agent for each trivial step or automatically apply every
   suggestion. Fix concrete defects, preserving the product's focus.
   The user requires a Claude Opus cross-review after every behavior-changing
   implementation increment, including the L04 continuation and later series.
   They reaffirmed this ongoing requirement on 2026-10-12. Use the available
   pinned Opus model on a bounded, fixed source snapshot with read-only tools,
   skills/hooks/plugins/MCP disabled and no session persistence. Verify the
   actual model in the runtime result; do not silently substitute another
   model. Reproduce actionable findings locally, fix confirmed defects and
   rerun affected checks before advancing. Record scope, model, findings and
   check evidence in the existing ExecPlan, not raw review transcripts. If
   Opus is unavailable, report the missing review rather than claim completion.
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
| `alpha` | original fixture, schema/resources, portable contracts and explicit personal/application/PTY/source-artifact dependencies; native/encrypted coverage stays in core/all |
| `core` | original fixture, contract, dependent storage/isolation probes, validation |
| `journal` | local journal and repository skill suites; no live Notion access |
| `harness` | verification runner tests |
| `all` | original fixture, generated schema/resources and one complete unittest discovery |

Scopes combine without duplication. `all` subsumes the individual suites.
`--plan` prints argument vectors only; it does not import tests, run commands,
query Notion, create state, or verify that the environment is usable. An exit
code of zero from a preview is not verification evidence.

Executing checks or internal test dispatch with Python older than 3.10 exits
2 before any checker or test discovery starts, naming the running and required
versions. `--help` and the non-executing `--plan` remain available. The runner
does not install or silently switch interpreters; rerun using a supported one.

Alpha/core/full runs require an existing non-Git temporary root, including all its
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
