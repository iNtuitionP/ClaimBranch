---
kind: exec-plan
status: planned
owners: maintainers
last_reviewed: 2026-08-04
---

# ExecPlan: ClaimBranch v1.0 and GPU systems mastery

This plan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

The plan is **checklist-driven, not schedule-driven**. Stages are ordered by
dependency and closed by observable exit checks. No stage carries an hour
estimate or a calendar date.

## Purpose and big picture

Two outcomes are pursued together, and neither is a byproduct of the other.

1. **ClaimBranch v1.0** — a finished single-user application covering the whole
   experiment-to-manuscript loop in the
   [product specification](../../product/product-spec.md), including semantic
   branch, diff, and partial merge, at control-plane interaction quality.
2. **GPU systems mastery** — the ability to explain and optimize the path from
   an application request down to warps and memory bandwidth, and back up
   through training, inference serving, and multi-GPU distribution.

The honest relationship: **building ClaimBranch does not teach GPUs.**
ClaimBranch supplies a real, personally owned LLM workload — a reason to care
about time-to-first-token, KV cache size, quantization quality, and local
inference privacy. The GPU knowledge is acquired in a dedicated track and fed
back into the product.

Observable end state:

- `claimbranch` runs on a real paper repository, and the
  [saturation acceptance case](../../validation/cases/saturation.md) completes
  end to end with an AI provider both enabled and disabled.
- Local inference is the product default for unpublished manuscript content,
  and its latency profile is explained down to prefill/decode and kernel level
  with measurements from this application's own workload.
- Each GPU stage has a committed write-up: hypothesis, measurement, what
  dominates, and where the explanation stops holding.

### Definition of v1.0 done

Maximum scope invites endless polish, which would starve the GPU track. v1.0 is
complete when every item in `Validation and acceptance` passes. Anything
discovered after that goes to the `v1.1 backlog` in `Artifacts and notes` — it
does not reopen a stage.

## Progress

- [ ] 2026-08-04 - Plan created and revised after a self-directed adversarial
      review. Stack and budget decisions confirmed. No stage started; S0 is next.

## Surprises & Discoveries

- 2026-08-04 - The originating design conversation is not in the repository.
  Its execution framing, competitor analysis, and adversarial risk list were
  never transcribed. This plan restores the execution framing; the rest is
  scheduled into S0 as reference documents.
- 2026-08-04 - Known contradiction: the
  [validation prototype](../../product/releases/validation-prototype.md) places
  semantic branch and partial merge in the smallest slice while excluding
  marker insertion, patch application, and compile verification. This plan
  orders the manuscript verification loop first. Resolved in S0, not silently.
- 2026-08-04 - Known contradiction: [ARCHITECTURE.md](../../../ARCHITECTURE.md)
  records the local projection technology as undecided, while
  [product-spec.md](../../product/product-spec.md) and the
  [domain model](../../designs/2026-08-03-domain-model.md) both name SQLite.
  Resolved in S0.
- 2026-08-04 - Adversarial review of this plan's first revision found seven
  defects in the plan itself. Each is recorded in `Decision Log` with the
  change made. The two that mattered most: the manuscript write guard as first
  drafted would have refused to run during normal editing, and the GPU track
  had no forcing function and would have been starved by product work.

## Decision Log

- 2026-08-04 - **Stage-based, not time-based.** Effort is elastic here and
  calendar estimates were the least reliable part of earlier drafts.
  Alternative: weekly blocks with hour budgets; rejected because one missed
  week silently invalidates every later block.
- 2026-08-04 - **Tracks interleave by dependency, not by weekly ratio.** Product
  work is local and continuous; GPU work is bursty and rental-bound. A fixed
  weekly split wastes rental time and fragments both.
- 2026-08-04 - **The manuscript verification loop precedes the semantic VCS
  kernel.** The product's claim is that manuscript omissions decrease; a slice
  that never recompiles the paper cannot demonstrate that. Branching is still
  required for v1.0, just not first.
- 2026-08-04 - **Full product scope retained.** Related-work import, daemon,
  mapping UI, graph canvas, projection screens, and semantic merge all stay in
  v1.0.
- 2026-08-04 - **Stack: Python 3.12 kernel/CLI/API, FastAPI local server,
  React + Vite + TypeScript UI, SQLite projection.** Rationale: the GPU track
  is entirely Python, so provider adapters, profiling hooks, and benchmark
  harnesses are native to the product; LaTeX and JSON handling are comfortable;
  the UI stays an independent layer. Cost: one API boundary and type
  duplication, mitigated by generating TypeScript types from the OpenAPI
  schema. Alternative: single-language TypeScript, which removes the boundary
  but strands the GPU track outside the product. To be transcribed into an ADR
  in S0.
- 2026-08-04 - **GPU labs live in a separate repository**, `gpu-systems-lab`.
  Only `bench/`, which benchmarks this application's own workload, lives here.
  Rationale: the product must not accumulate CUDA code it does not need. This
  was an explicit constraint of the original design discussion.
- 2026-08-04 - **GPU spend is prepaid and capped.** Instances are destroyed,
  never left stopped. Code is written and debugged locally and synced; rented
  time is for execution and measurement only.
- 2026-08-04 - **A local NVIDIA RTX 2080 SUPER with 8 GB is available**
  (Turing, compute capability 7.5; verified with `nvidia-smi`, driver 591.86,
  CUDA 13.1). This changes the hardware strategy substantially: the
  highest-iteration labs run locally, unmetered, at zero marginal cost. Rentals
  become surgical rather than routine. Turing's limits are firm — no bf16, no
  fp8, no asynchronous copy, no NVLink, and 8 GB shared with the desktop — so
  the labs that require Ampere or newer are the only ones that must be rented.
- 2026-08-04 - **The two tracks live in different environments.** ClaimBranch is
  developed and run **natively on Windows**, because that is where the user's
  manuscripts, LaTeX toolchain, and compile command already are; running the
  product inside WSL2 would force path translation and cross-boundary process
  invocation for every compile. The GPU labs run **under WSL2**, because the
  kernel toolchain targets Linux and the local card is reachable there through
  the same driver. The only shared artifact is the inference provider interface.
- 2026-08-04 - **Toolchain baseline checked 2026-08-04**: Python 3.10.11 and
  Git 2.49 present on Windows; WSL2 with Ubuntu 22.04 already installed and
  stopped; Node.js absent. Node is required from S2 onward, not for S0 or S1.
  Python is managed per environment rather than globally; pin the interpreter
  in the project rather than relying on whatever is on `PATH`.
- 2026-08-04 - **The free Kaggle tier keeps exactly one job: two GPUs.** Its
  T4 is the same Turing generation as the local card, so it adds nothing for
  single-GPU work. Its remaining value is dual-GPU collective work that a single
  local card cannot do.
- 2026-08-04 - **Hardware is tiered; no lab runs on a card more expensive than
  it requires.** Kernel skill comes from iteration count, not card class, so the
  free tiers deliberately absorb the highest-iteration work. In G6, poor
  interconnect is the subject of the measurement rather than an obstacle to it.
  See the hardware tables in `Artifacts and notes`.
- 2026-08-04 - **Dogfooding uses a copy of the saturation manuscript until S7**,
  and a live paper only after v1.0.
- 2026-08-04 - *(from self-audit)* **The write guard is backup-based, not
  worktree-clean-based.** Requiring a clean Git worktree would refuse to work
  during ordinary editing, which is when the tool is actually used. Instead:
  snapshot the exact target file to `.claimbranch/backups/` before any write,
  compile after, restore from the snapshot on failure, and warn — not block —
  when the target file has uncommitted changes.
- 2026-08-04 - *(from self-audit)* **The application shell moves early, to S2.**
  Layout, design tokens, keyboard model, command palette, and background task
  tray constrain every later screen. Building them last produces a shell that
  fights the screens already written. S6 keeps the full projection suite and
  the polish pass.
- 2026-08-04 - *(from self-audit)* **A product stage cannot be closed while its
  paired GPU write-up is missing.** Without this, the GPU track loses every
  scheduling conflict to visible product progress.
- 2026-08-04 - *(from self-audit)* **G5 does not hard-depend on S4.** If the AI
  layer is not ready, G5 runs on recorded synthetic prompt shapes and is re-run
  against the real workload afterwards. Otherwise a product delay silently
  cancels the inference-systems stage.
- 2026-08-04 - *(from self-audit)* **The evaluation set is authored before any
  prompt is written, and frozen.** Building it after prompt design measures the
  prompts against themselves.
- 2026-08-04 - *(from self-audit)* **The retrospective baseline is committed and
  sealed in S0.** By S9 the author will have thought about the saturation case
  for months; an unsealed baseline would be retro-fitted without anyone
  intending to.
- 2026-08-04 - *(from self-audit)* **S3 has a pre-agreed fallback.** Semantic
  merge is the largest technical risk in the plan and every later product stage
  waits behind it. If the general lowest-common-ancestor merge stalls after two
  serious attempts, fall back to the solo-user form: assume the target ref has
  not advanced since the branch point, apply the selected closure directly, and
  block only when the target has in fact advanced. Record the fallback as an
  ADR, keep the general algorithm in the v1.1 backlog, and continue to S4. The
  fallback still satisfies every acceptance item in the canonical case.
- 2026-08-04 - *(from self-audit)* **Schema migration exists from S1.** The
  domain schema changes continuously through S4. Without `claimbranch migrate`
  and an export/reimport escape hatch, dogfooding data dies repeatedly and
  dogfooding stops.

## Outcomes & Retrospective

Pending. Fill this in from measurements and from what actually shipped,
including abandoned stages. Do not fill it in from intention.

## Context and orientation

### Canonical sources this plan must obey

| Question | Source |
|---|---|
| Intended product behavior and boundaries | [product-spec.md](../../product/product-spec.md) |
| First narrow validation slice | [validation-prototype.md](../../product/releases/validation-prototype.md) |
| Full candidate release scope | [candidate-mvp.md](../../product/releases/candidate-mvp.md) |
| Observable acceptance fixture | [saturation.md](../../validation/cases/saturation.md) |
| Proposed kernel semantics | [2026-08-03-domain-model.md](../../designs/2026-08-03-domain-model.md) |
| Accepted constraints | [decision index](../../architecture/decisions/README.md) |
| Target boundaries to test | [ARCHITECTURE.md](../../../ARCHITECTURE.md) |
| Documentation rules | [documentation-policy.md](../../_meta/documentation-policy.md) |

### Vocabulary

- **Domain commit / semantic branch / partial merge** — ClaimBranch's own
  versioning of reasoning, distinct from Git. See
  [ADR 0002](../../architecture/decisions/0002-semantic-branches.md).
- **Manuscript debt** — a traceable mismatch between accepted research state and
  the manuscript, derived from accepted changes rather than typed as a TODO.
- **Anchor** — a stable link from a Claim to a manuscript location, resolved by
  LaTeX label, managed comment marker, or sidecar fingerprint.
- **Proposal** — any AI output. Never accepted state. See
  [ADR 0003](../../architecture/decisions/0003-ai-proposals.md).
- **Track P / Track G** — product stages and GPU stages in this plan.

### Planned repository layout

```text
claimbranch/
|-- src/claimbranch/
|   |-- kernel/        objects, edges, events, refs, commits, diff, merge
|   |-- store/         object store, event log, SQLite projection, migration
|   |-- manuscript/    latex scan, anchors, markers, patch, compile runner
|   |-- ingest/        json preview, mapping adapters, artifact hashing
|   |-- ai/            provider interface, proposal records, output schemas
|   |-- api/           FastAPI application
|   `-- cli/           command surface
|-- ui/                React + Vite + TypeScript
|-- bench/             inference benchmark harness over real product workloads
|-- tests/
|   |-- unit/
|   |-- golden/        fixture replay and semantic diff snapshots
|   `-- fixtures/saturation/
|-- docs/
`-- scripts/
```

GPU labs live in a separate `gpu-systems-lab` repository with one directory per
stage: `g1_profiling/`, `g2_triton/`, `g3_matmul_attention/`, `g4_training/`,
`g5_serving/`, `g6_distributed/`, `g7_capacity/`. Every directory contains a
`NOTES.md` with hypothesis, method, measurement, explanation, and limits.

### Planned command surface

```text
claimbranch init | status | log | rebuild | migrate | doctor | serve
claimbranch note add
claimbranch claim add | show | list
claimbranch edge add | show
claimbranch anchor link | list | check | relink
claimbranch adapter new | list
claimbranch ingest <file> [--adapter NAME]
claimbranch observe confirm | supersede | invalidate
claimbranch branch create | list | switch | archive
claimbranch diff <ref> <ref>
claimbranch merge <source> --into <target> --select <ids> --rationale <text>
claimbranch revert <commit>
claimbranch debt list | show | verify | waive | defer
claimbranch patch propose | show | accept | apply
claimbranch propose <kind>
claimbranch export | import
```

### Working rules

- **Understanding gate on AI-generated code.** For kernel, store, manuscript,
  and any state-mutating code, record before implementing: the problem, the
  hypothesis, the interface, and the invariant. After implementing, answer in
  writing: where does data enter, where does state change, what survives a
  failure, is there a race under concurrent requests, which invariant does the
  test guarantee. Code that cannot be explained is not complete. UI styling and
  mechanical refactors are exempt.
- **One measurement per feature.** Correctness, latency, memory, or a failure
  case — at least one, recorded.
- **Rented GPU discipline.** Write and debug locally; rent to execute and
  measure. Destroy instances rather than stopping them. Checkpoint before any
  run longer than a few minutes.
- **Documentation impact is classified in every change**, per
  [AGENTS.md](../../../AGENTS.md), and `python scripts/check_docs.py` passes
  before a stage closes.

### Current repository state

Specification only. No application code, no tests, no chosen stack in the repo
yet. The single runnable check is `python scripts/check_docs.py`.

### The user's situation

No manuscript is currently in progress. The motivating saturation research is
complete, so v1.0 cannot be validated by live daily use during this plan.
Validation uses a **retrospective replay** of that research plus the fixed
fixture; live validation is deferred to the next real paper. This is a genuine
weakness and must never be reported as live-use evidence.

## Plan of work

Ten stages. Track P and Track G interleave where one supplies the other.

```text
S0  Decisions, hygiene, sealed baseline, GPU logistics     (P+G)
S1  Deterministic kernel and the manuscript value loop     (P)   || G1
S2  Evidence intake, reasoning graph, application shell    (P)   || G2
S3  Semantic version control: branch, diff, partial merge  (P)   || G3
S4  Patch pipeline, AI proposal layer, explain-back        (P)   || G4
S5  Inference systems on our own workload                  (G)   -> P
S6  Daily workspace: projections and the polish pass       (P)   || G6
S7  Reliability, privacy, performance                      (P)   || G7
S8  Related work, packaging, onboarding
S9  Retrospective replay, release v1.0, write-up
```

Dependency notes that drive this order:

- S1 precedes everything: the storage contract and safe manuscript writes are
  prerequisites for all later product work.
- The application shell is in S2, not S6, because layout, tokens, keyboard
  model, and the command palette constrain every screen built afterwards.
- S4 normally precedes S5 so the inference track benchmarks this application's
  real prompt shapes — but S5 may start on recorded synthetic shapes if S4 is
  not ready, then re-run.
- The full projection suite is in S6 because those screens read projections
  that are only stable after S3 and S4.
- G2 and G3 are rental-bursty and block no product stage.

**Cross-track gate.** A product stage may not be marked complete while its
paired GPU stage has no committed `NOTES.md`. This is the only mechanism
preventing the GPU track from losing every scheduling conflict.

## Concrete steps

Every item is a checkbox. A stage closes when all non-optional items and all
exit checks pass. `(opt)` items may move to the v1.1 backlog without failing
the stage.

### S0 — Decisions, hygiene, sealed baseline, GPU logistics

**Sealed baseline — do this before writing any application code**

- [ ] Write, from memory and old notes, the list of manuscript revisions that
      were actually missed or delayed during the saturation research. One line
      each, with where in the paper it belonged.
- [ ] Write the recalled elapsed time from a confirmed result to the
      corresponding manuscript update, for at least three results.
- [ ] Count the follow-up experiments whose motivation was never written down.
- [ ] Write the exact measurement procedure S9 will repeat.
- [ ] Commit all of the above under `Artifacts and notes` in this plan, and do
      not edit those entries again. Later corrections go in a dated addendum.

**Decisions to record**

- [ ] Transcribe the stack decision from `Decision Log` into an ADR with
      context, drivers, options, decision, consequences, validation, and
      supersession.
- [ ] Record the GPU spend ceiling and the prepaid amount.
- [ ] Create the `gpu-systems-lab` repository with the seven stage directories
      and a `NOTES.md` template.

**Documentation reconciliation**

- [ ] Update [validation-prototype.md](../../product/releases/validation-prototype.md)
      so the smallest slice contains the manuscript verification loop and
      treats semantic branch exploration as the following increment.
- [ ] Update gate ordering in
      [candidate-mvp.md](../../product/releases/candidate-mvp.md) so the AI
      provider boundary precedes the polished workspace, matching S4 then S6.
- [ ] Define `submission tag` in [product-spec.md](../../product/product-spec.md)
      or rewrite the success measure that depends on it. It is referenced once
      and defined nowhere.
- [ ] Give the ten-minute target one scope, label it a hypothesis, and state
      its measurement method. It currently means three different workloads.
- [ ] Decide the canonical owner of the SQLite projection statement and of the
      marker syntax; remove the duplicates from the other documents; reconcile
      the `technology undecided` line in [ARCHITECTURE.md](../../../ARCHITECTURE.md).
- [ ] Add a positioning reference under `docs/references/` covering
      ResearchClaw, ResearchLoop, XScientist, Curvenote, Manubot, and the
      DVC/W&B/MLflow family, with access dates and what is deliberately not
      copied.
- [ ] Add a reference on cognitive forcing and automation bias, including its
      methodological limits. Explain-back is the least-supported product
      hypothesis and currently has no cited basis.
- [ ] Add a risk register: scope overlap, structured-input burden, graph
      complexity, AI proposals creating new comprehension debt, weak academic
      novelty, and single-user validation.

**Repository hygiene**

- [ ] Pin the project interpreter and scaffold the Python side on Windows:
      `pyproject.toml`, `ruff`, `mypy`, `pytest`.
- [ ] Install Node.js and scaffold the UI side: `vite`, `tsconfig`, `eslint`.
      Required from S2 onward; S0 and S1 do not need it.
- [ ] Extend CI beyond documentation: lint, type check, unit tests, UI build.
- [ ] Add `.claimbranch-cache/`, `.venv/`, `node_modules/`, `dist/`, and
      `ui/dist/` to [.gitignore](../../../.gitignore); it currently ignores only
      Python bytecode.
- [ ] Encode the [saturation case](../../validation/cases/saturation.md) as
      machine-readable fixtures under `tests/fixtures/saturation/`.
- [ ] Create a manuscript copy for dogfooding at `tests/fixtures/manuscript/`
      containing a real multi-section `main.tex` and a working compile command.

**GPU logistics**

- [ ] Set up WSL2 with Ubuntu, CUDA toolkit, PyTorch, Triton, and Nsight; run a
      trivial Triton kernel and one Nsight Compute capture against the local
      RTX 2080 SUPER.
- [ ] Raise the display-driver timeout so long kernels are not reset by the
      Windows driver.
- [ ] Record a local hardware baseline: achieved memory bandwidth, fp32 and
      fp16 peak, and launch overhead. Every later measurement is read against
      these numbers.
- [ ] Establish the reference-implementation-first habit: a PyTorch correctness
      oracle plus Triton interpreter mode for index debugging.
- [ ] Create accounts on one marketplace provider and one fixed-rate provider.
- [ ] Prove a full rental session cycle: boot, sync code, run `nvidia-smi`, run
      a trivial Triton kernel, save results to persistent storage, destroy.
- [ ] Verify the free dual-GPU tier separately: dual-T4 notebook and a
      two-process NCCL all-reduce.
- [ ] Confirm compute capability, memory, and available numeric formats on every
      tier that will be used, and record them. Half the confusion in kernel work
      comes from not knowing which instructions the target supports.
- [ ] Confirm a small quantized model runs locally within 8 GB, so the product's
      offline inference path is real rather than assumed.
- [ ] Write `docs/development/gpu-rental.md`: providers, tier assignment,
      start/sync/checkpoint/destroy procedure, cost log format, the local-debug
      rule, and the per-session question list template.

**Exit checks**

- [ ] Stack ADR merged; `python scripts/check_docs.py` passes; CI green on an
      empty test suite.
- [ ] A rented session was created, used, and destroyed with cost recorded.
- [ ] The sealed baseline is committed.
- [ ] Every documentation conflict above is fixed or has a dated `Decision Log`
      entry explaining why it stands.

### S1 — Deterministic kernel and the manuscript value loop (Track P)

**Kernel and store**

- [ ] Record envelope: `id`, `type`, `schema_version`, `created_at`,
      `created_by`, `provenance`, `attributes`.
- [ ] Canonical serialization with a stable byte encoding, so hashes are
      reproducible across processes and platforms.
- [ ] Content-addressed objects under `.claimbranch/objects`.
- [ ] Append-only event log under `.claimbranch/events`.
- [ ] `refs/main` only, with the ref abstraction already present so S3 adds
      branches with no migration.
- [ ] SQLite projection built purely from durable state, plus a projection
      manifest hash used by the rebuild test.
- [ ] `claimbranch migrate` with numbered schema steps and a dry-run mode.
- [ ] `claimbranch export` and `import` as the escape hatch when migration is
      not worth writing during rapid schema churn.
- [ ] Commands: `init`, `status`, `log`, `rebuild`, `migrate`, `export`,
      `import`, `doctor`.

**Manuscript adapter, minimum safe version**

- [ ] Scan `main.tex` and resolve existing `\label{...}`.
- [ ] Insert `% claimbranch:start id=...` and `% claimbranch:end id=...` on
      their own comment lines, application-managed only.
- [ ] Sidecar anchor record: document, kind, locator, text hash, context before
      and after, linked claims, state.
- [ ] **Write guard**: snapshot the exact target file into
      `.claimbranch/backups/<timestamp>/` before any write; run the configured
      compile command after the write; restore the snapshot on non-zero exit;
      warn if the target file had uncommitted Git changes, but do not refuse.
- [ ] Compile runner with timeout, captured output, and a stored result record.
- [ ] Derive a Debt Item when an accepted change affects a linked anchor.
- [ ] Debt reaches `verified` only after a successful compile.
- [ ] Commands: `claim add/show/list`, `anchor link/list/check`,
      `observe confirm`, `debt list/show/verify/waive/defer`.

**Tests that define this stage**

- [ ] `tests/golden/test_rebuild_identity.py` — delete the cache, rebuild,
      assert an identical projection manifest hash.
- [ ] `tests/unit/test_write_guard.py` — a forced compile failure restores the
      manuscript byte for byte.
- [ ] `tests/unit/test_write_guard.py` — a process kill mid-write leaves either
      the original file or a restorable snapshot, never a truncated file.
- [ ] `tests/unit/test_evidence_append_only.py` — a confirmed Observation
      cannot be edited in place; correction requires supersede or invalidate.

**Exit checks**

- [ ] From `tests/fixtures/manuscript/`: register a result, mark the claim
      contested, generate manuscript debt, edit the sentence, compile, verify
      the debt — entirely from the CLI, with no AI.
- [ ] All four tests above pass in CI.
- [ ] ADR recorded for the durable storage format.
- [ ] `gpu-systems-lab/g1_profiling/NOTES.md` committed.

### S2 — Evidence intake, reasoning graph, application shell (Track P)

**Evidence**

- [ ] `experiment_spec`, optional `run`, `artifact`, `metric`, `observation`.
- [ ] Aggregate experiment results with no synthetic Run records required.
- [ ] JSON tree preview with content hash before any import.
- [ ] Field mapping saved as a reusable adapter under `.claimbranch/adapters/`.
- [ ] Original file never rewritten; hash and source path stored.
- [ ] Idempotent re-import: same content hash is a no-op.
- [ ] Run and metric table with grouping, comparison, and baseline delta.
- [ ] Human confirmation before a proposed Observation becomes accepted.

**Reasoning graph**

- [ ] Node types from the [draft domain model](../../designs/2026-08-03-domain-model.md).
- [ ] First-class edges carrying `scope`, `conditions`, `strength`,
      `rationale`, `review_status`, and provenance.
- [ ] `tests.intent` and `cites.intent` as attributes, not new relation types.
- [ ] Four independent status axes; no collapsed single `status`.
- [ ] Untyped `note` capture that can be structured later.
- [ ] Focused one- and two-hop retrieval with a stable ordering.

**Application shell** — moved here from S6 by the self-audit

- [ ] FastAPI app with an OpenAPI schema; TypeScript types generated from it.
- [ ] `claimbranch serve` starting API and UI together.
- [ ] Three-pane layout: navigation, workspace, context inspector.
- [ ] Design tokens for color, spacing, type scale, radius, elevation; light
      and dark themes from one source.
- [ ] Keyboard model: every action reachable without a mouse, visible focus,
      documented shortcut table.
- [ ] Command palette wired to the real command registry, not a hardcoded list.
- [ ] Background task tray with progress, cancel, retry, and failure detail.
- [ ] Standard empty, loading, error, and partial-failure components used by
      every screen from this point on.
- [ ] First two screens on the shell: Debt Inbox and Claim detail.

**Exit checks**

- [ ] A real anonymized result file imports through a saved adapter, and
      re-importing changes nothing.
- [ ] Selecting the saturation claim shows research question, expected
      scenario, observations, supporting and challenging edges, interpretations,
      anchors, and open debt on one screen.
- [ ] An edge scoped to `sensitivity component only` is never rendered as a
      plain `supports`. Rendering it plainly is an acceptance failure.
- [ ] Every action on both screens is reachable from the keyboard.
- [ ] `gpu-systems-lab/g2_triton/NOTES.md` committed with four kernels.

### S3 — Semantic version control (Track P)

**Algorithm, stated before implementation**

- [ ] The merge unit is a single semantic change: node creation, one property
      change, one edge, one plan, one patch, one debt disposition.
- [ ] The base is the lowest common domain ancestor of the two refs, found by
      walking commit parents.
- [ ] Referential-integrity closure is mandatory and computed transitively: a
      selected edge pulls in the nodes it references, a selected patch pulls in
      its anchor.
- [ ] Higher-level semantic dependencies are advisory and overridable with a
      recorded reason.
- [ ] The result is one new commit on the target containing only the selected
      closure, plus a Decision recording what was omitted.

**Implementation**

- [ ] `branch create/list/switch/archive`; archiving never garbage-collects.
- [ ] Domain commits recording ordered operations, message, and rationale.
- [ ] Semantic diff grouped by claims, relationships, interpretations, plans,
      manuscript impact, debt, and decisions, preserving before and after
      values.
- [ ] Partial merge with the closure above; the source branch is never mutated.
- [ ] `revert` appends an inverse domain commit; nothing is erased.
- [ ] Deterministic conflicts: divergent property edits, overlapping anchor
      patches, unresolved anchors, conflicting metric mappings, use of a
      superseded observation.
- [ ] Conflict blocking is scoped to the affected operation only.
- [ ] **Omission debt**: after a partial merge, surface omitted challenge
      relationships as debt on the target, so accepted evidence cannot become
      argumentatively invisible while remaining formally global.

**Tests that define this stage**

- [ ] `tests/golden/test_saturation_partial_merge.py` — the selection in the
      canonical case produces exactly the expected semantic diff snapshot.
- [ ] `tests/unit/test_evidence_global.py` — no branch operation can hide an
      accepted Observation from any ref.
- [ ] `tests/unit/test_merge_closure.py` — selecting an edge without its node
      either pulls the node in or omits the edge; a dangling reference is
      impossible.
- [ ] `tests/unit/test_conflict_scope.py` — a property conflict blocks that one
      change while unrelated selections still merge.
- [ ] `tests/unit/test_revert_appends.py` — revert adds a commit and removes
      none.

**Exit checks**

- [ ] The canonical partial merge succeeds exactly as specified: claim
      contested, relationships and plans merged, debt bundle opened,
      replacement claim and prose deferred.
- [ ] All five tests pass in CI.
- [ ] [ADR 0002](../../architecture/decisions/0002-semantic-branches.md) moves
      to `accepted`, or is superseded by what was actually built.
- [ ] If the fallback in `Decision Log` was taken, its ADR is recorded and the
      general algorithm is in the v1.1 backlog. Taking the fallback closes this
      stage; it is not a reason to keep it open.
- [ ] `gpu-systems-lab/g3_matmul_attention/NOTES.md` committed.

### S4 — Patch pipeline, AI proposal layer, explain-back (Track P)

**Evaluation set — authored first, then frozen**

- [ ] Build 30 to 50 labeled cases from the S0 retrospective record and
      variants, **before writing any prompt**.
- [ ] Each case: input state, the manuscript locations a competent reader would
      flag, and the ones that would be spurious.
- [ ] Commit the set and freeze it. Later additions go to a separate held-out
      file and are reported separately.

**Patch pipeline**

- [ ] Bounded patch proposal tied to a verified anchor.
- [ ] Side-by-side review with linked evidence and claim scope.
- [ ] Accept, edit, reject, defer.
- [ ] Exact-range application; any content mismatch stops application.
- [ ] Compile verification, then debt verification.
- [ ] Revert of an applied patch restores previous content in a new commit and
      re-runs compile.
- [ ] `(opt)` Materialize an accepted patch on a dedicated Git branch.

**AI proposal layer**

- [ ] Provider interface with cloud, local `transformers`, and
      OpenAI-compatible local server implementations behind one boundary.
- [ ] Structured output with schema validation and bounded retry.
- [ ] Durable `ai_proposal` records: provider, model, input node and file
      references, raw output, human edits, final disposition.
- [ ] Proposal Inbox with review, edit, reject, dismiss.
- [ ] Deterministic checks kept strictly separate from semantic AI checks.
- [ ] Pre-send disclosure of exactly which nodes and files leave the machine;
      configured secret paths excluded and covered by a test.
- [ ] Asynchronous, cancellable, retryable; the UI never blocks.
- [ ] Proposal kinds: mismatch classification, observation wording,
      interpretation candidates, relationships, follow-up experiments,
      manuscript impact, semantic conflicts, bounded patches.

**Explain-back**

- [ ] Soft checkpoint: one-sentence rationale for ordinary accepted proposals.
- [ ] Hard checkpoint on central-claim change, narrative merge, central patch,
      and waiving important debt.
- [ ] Responses stored as Decisions; override always allowed and recorded.
- [ ] Copy never asserts that the researcher failed to understand anything.

**Exit checks**

- [ ] With every provider disabled, the whole deterministic loop still works;
      covered by a CI job that runs the suite with AI hard-disabled.
- [ ] On the frozen evaluation set, rules-only, LLM-only, and hybrid are
      compared on affected-claim and anchor-impact precision and recall, plus
      spurious debt count. Results committed.
- [ ] A real sentence in the manuscript copy is changed through
      propose, edit, accept, apply, compile, verify.
- [ ] `gpu-systems-lab/g4_training/NOTES.md` committed.

### S5 — Inference systems on our own workload (Track G, feeds Track P)

- [ ] Record real prompt shapes from S4 — short structured extraction, long
      manuscript-impact analysis, multi-claim contradiction scan, patch
      generation, branch summary. If S4 is not ready, use synthetic shapes of
      the same token profile and re-run later.
- [ ] Build `bench/` in this repository: reproducible, seeded, and able to
      replay recorded requests.
- [ ] Measure TTFT, inter-token latency, throughput, p50 and p95 at concurrency
      1, 4, and 16 across short, medium, and long contexts.
- [ ] Compare cloud API, naive local generation, and vLLM or SGLang.
- [ ] Read vLLM's scheduler and block manager; produce a diagram and a written
      explanation of continuous batching, paged attention, and chunked prefill.
- [ ] Measure quantization — FP8, AWQ, GPTQ — on latency, memory, and **quality
      using the frozen S4 evaluation set**, so quality loss is measured on the
      real task rather than a generic benchmark.
- [ ] Compute the KV cache budget by hand for each configuration, then compare
      against measurement and explain the gap.
- [ ] Feed back into the product: local inference becomes the default path for
      unpublished manuscript content, with the model choice justified by these
      measurements.

**Exit checks**

- [ ] A written explanation of which regime is prefill-dominated, which is
      decode-dominated, and where batching raises throughput while degrading
      p95 queue latency — from this application's own numbers.
- [ ] Hand-computed KV cache size matches measurement within a stated error
      band, with the discrepancy explained.
- [ ] The product runs its default proposal path against a local model.

### S6 — Daily workspace: projections and the polish pass (Track P)

The shell exists from S2. This stage completes the projection suite and does
the pass that separates a working tool from one that can stay open all day.

**Projections**

- [ ] Task, Debt, and Approval Inbox as the home screen.
- [ ] Focused Graph at one to two hops, with full graph as an advanced mode.
- [ ] Branch view showing claim, plan, relationship, patch, and debt deltas.
- [ ] Claim Dashboard: support, challenge, qualification, maturity, review,
      manuscript integration.
- [ ] Manuscript Impact over sentences, sections, tables, figures, captions.
- [ ] Scenario Board: expected, observed, competing explanations,
      discriminating experiments.
- [ ] Context inspector: evidence, proposals, history, actions.
- [ ] Chat as a contextual capture and query surface only; every structured
      change it produces goes through preview and is never source of truth.

**Polish pass**

- [ ] Optimistic updates with correct rollback on failure.
- [ ] Virtualized lists and tables that stay smooth at fixture scale.
- [ ] Undo for every action that feels destructive.
- [ ] Git, import, compile, and AI status always visible and never blocking.
- [ ] Instrumented latency budgets, measured not asserted, with a committed
      report: navigation, focused graph, first search result, basic branch
      diff, large import preview.
- [ ] Accessibility pass: focus order, labels, contrast, reduced motion.

**Local daemon**

- [ ] Watch configured result paths, manuscript files, and Git state.
- [ ] Background queue with cancel, retry, timeout, crash recovery.
- [ ] Local server plus browser UI; `(opt)` desktop wrapper and system tray.

**Exit checks**

- [ ] A full working day on the manuscript copy without opening a terminal,
      hand-editing storage, or waiting on a blocked UI.
- [ ] Every measured interaction budget is met, or has a recorded reason and a
      v1.1 backlog entry.
- [ ] **A named second person** — not the author — walks through the tool
      unaided while thinking aloud. Their friction list is committed and the top
      three items are fixed. Recruit this person during S4 so the session is not
      skipped for lack of a participant.
- [ ] `gpu-systems-lab/g6_distributed/NOTES.md` committed.

### S7 — Reliability, privacy, performance (Track P)

- [ ] Fault injection: provider killed mid-request, compile fails, process
      killed during import, marker deleted from the manuscript, cache corrupted,
      Git worktree dirty, disk full.
- [ ] Each fault leaves durable state consistent and loses no accepted data.
- [ ] Threat model document: what leaves the machine, what reaches logs, where
      API keys live, what remains functional with AI disabled.
- [ ] Secret path exclusion verified by test.
- [ ] Backup, export, and import of an exported project on a clean machine.
- [ ] Profile one AI proposal request end to end across UI, API, graph query,
      context build, queue, prefill, decode, parse, write, and render.
- [ ] Fix the dominant bottleneck and re-measure.
- [ ] Report realistic single-paper scale and the synthetic design scale from
      [product-spec.md](../../product/product-spec.md) separately and honestly.
- [ ] `gpu-systems-lab/g7_capacity/NOTES.md` committed.

### S8 — Related work, packaging, onboarding

- [ ] `.bib` import producing Literature Items.
- [ ] Literature-to-claim relationships with citation intent.
- [ ] Related-work debt.
- [ ] Onboarding: select an existing Git repository, detect the root manuscript,
      confirm the compile command, create `.claimbranch/` without reorganizing
      the project, first claim, first anchor.
- [ ] Install path verified on a clean machine.
- [ ] User documentation: tutorial, how-to, reference, explanation.
- [ ] `claimbranch doctor` diagnosing environment and repository problems.

### S9 — Retrospective replay, release, write-up

- [ ] Reconstruct the saturation research at the point before the real-operator
      results arrived, using only what was known then.
- [ ] Replay the real results and record how many entries from the **sealed S0
      list** the tool surfaces, and how many spurious items it adds.
- [ ] Repeat the S0 measurement procedure exactly.
- [ ] Full acceptance run of the
      [saturation case](../../validation/cases/saturation.md) with AI enabled
      and disabled.
- [ ] Tag `v1.0`; publish install documentation and a demo recording.
- [ ] Final measurement report and the seven GPU write-ups.
- [ ] Distill durable conclusions into the product spec, architecture
      documents, and ADRs; then move this plan to `plans/completed/`.

### Track G — GPU stages

Each ends with a committed `NOTES.md`: hypothesis, method, measurement,
explanation, limits.

**G1 — Hardware model and measurement** (paired with S1)

- [ ] Streaming multiprocessors, warps, scheduling, occupancy.
- [ ] Memory hierarchy and bandwidth: registers, shared, L1/L2, HBM.
- [ ] Roofline model and arithmetic intensity as the working vocabulary.
- [ ] Nsight Systems, Nsight Compute, and the PyTorch profiler in practice.
- [ ] Place one LLM call from this application on a roofline and decompose its
      timeline.

**G2 — Triton kernel fundamentals** (paired with S2)

- [ ] Memory coalescing, shared-memory tiling, launch overhead.
- [ ] Implement vector add, softmax, layer normalization, fused bias plus
      activation.
- [ ] Benchmark each against PyTorch eager and explain the gap in memory-bound
      versus compute-bound terms with profiler evidence.

**G3 — Matrix multiply and attention** (paired with S3)

- [ ] Tiled matmul on the free tier first: blocking, shared memory, bank
      conflicts, and the fp16 tensor-core path that Turing does support.
- [ ] Move to an Ampere-or-newer rental for the asynchronous-copy pipelining and
      the remaining gap to cuBLAS.
- [ ] Implement a simplified FlashAttention: online softmax and tiling that
      removes HBM round trips. The algorithm can be derived and tested anywhere;
      the pipelined implementation needs Ampere or newer.
- [ ] Read and explain kernels generated by `torch.compile`.

**G4 — Training stack** (paired with S4)

- [ ] Backward-pass kernels; mixed precision. Requires Ampere or newer for bf16
      and Ada or newer for fp8. On the free tier, fp16 with loss scaling shows
      the mechanism but not current practice, so treat free-tier training runs
      as rehearsal and do the measured run on a rental.
- [ ] Gradient accumulation and activation checkpointing.
- [ ] Train a small transformer end to end at deliberately small scale.
- [ ] Compute the memory budget by hand — parameters, gradients, optimizer
      state, activations — then reconcile with measurement.
- [ ] Measure model FLOPs utilization and explain what limits it.

**G5 — see stage S5 above.**

**G6 — Distribution** (paired with S6)

- [ ] Collective operations and their cost: all-reduce, all-gather,
      reduce-scatter; benchmark NCCL.
- [ ] Distinguish data parallel, ZeRO/FSDP, tensor parallel, and pipeline
      parallel by what each shards and what each communicates.
- [ ] Run collectives and two-way tensor parallel on free dual-T4 notebooks
      first. These are PCIe with no NVLink, so tensor parallel will scale badly
      — **measure exactly how badly and explain it from the bandwidth numbers.**
      Poor interconnect is the clearest available demonstration of why tensor
      parallel is interconnect-bound; it is the experiment, not a missing
      prerequisite.
- [ ] Predict, before booking anything, what the same experiment will do on an
      NVLink node. Write the prediction down first.
- [ ] `(opt)` Book a two-way NVLink node once, prepared in advance, and check
      the prediction. If the budget does not allow it, validate the cost model
      against published scaling numbers instead and say so explicitly.
- [ ] Never report a scaling figure without naming the interconnect it came
      from.
- [ ] Explain, in bandwidth terms, why tensor parallel stays inside a node
      while pipeline parallel crosses nodes.

**G7 — Cluster, capacity, cost** (paired with S7)

- [ ] Interconnect topology and the bandwidth hierarchy within and between
      nodes.
- [ ] Capacity planning: model size to GPU count to batch size to throughput to
      cost.
- [ ] Failure handling, checkpointing, and scheduling at cluster scale.
- [ ] Produce a capacity and cost design for serving this application's
      inference to a hypothetical hundred users, grounded in S5 measurements.

## Validation and acceptance

### Product acceptance

The full [saturation case](../../validation/cases/saturation.md) passes, plus
the criteria in [candidate-mvp.md](../../product/releases/candidate-mvp.md).

- [ ] Accepted evidence cannot be hidden or removed by branch operations.
- [ ] Experiment-level results work without mandatory Run decomposition.
- [ ] Free capture can be structured progressively.
- [ ] Relationships retain scientific scope and rationale through save, reopen,
      diff, and merge.
- [ ] Partial merge adopts follow-up plans and debt while deferring the
      replacement central claim and prose.
- [ ] No affected manuscript location in the canonical case is silently missed.
- [ ] Accepted patches require exact anchors and compile before debt
      verification.
- [ ] Every AI change is reviewed and every proposal disposition is auditable.
- [ ] The core workflow works offline with AI disabled, proven by a CI job.
- [ ] CLI and browser UI observe the same repository state.
- [ ] Deleting the cache and replaying durable state reproduces an equivalent
      graph, refs, proposals, and debt state.
- [ ] A project exported on one machine imports and rebuilds on another.

### Measurement

Captured and sealed in S0, repeated in S9 with the same procedure.

- [ ] Recall against the sealed list of previously missed manuscript revisions.
- [ ] Spurious-item count alongside recall, so recall cannot be bought with
      noise.
- [ ] Elapsed time from confirmed result to resolved manuscript debt.
- [ ] Count of follow-up plans lacking motivation, rationale, or a target.
- [ ] Proposal accept, edit, and reject ratios and median review time.
- [ ] Interaction latency report against the budgets in the product spec.

### GPU acceptance

The bar is not that it ran. The bar is answering: why this structure, what were
the alternatives, where does it break, and up to what scale does the
explanation hold.

- [ ] G2 and G3: for each kernel, a stated hypothesis, a measurement, and a
      profiler-supported explanation of the gap to the reference.
- [ ] G4: hand-computed training memory reconciled with measurement; MFU
      measured and its limiter identified.
- [ ] G5: regimes classified as prefill- or decode-dominated using this
      application's own workload.
- [ ] G6: parallelism strategies distinguished by what they shard and what they
      communicate, with a prediction validated against measurement or published
      data, and hardware caveats stated.
- [ ] G7: a capacity and cost model whose assumptions trace to G5 measurements.

## Idempotence and recovery

- **Documentation.** `python scripts/check_docs.py` is safe to repeat and must
  pass before a stage closes.
- **Repository state.** `claimbranch rebuild` is safe at any time. Deleting
  `.claimbranch-cache/` is always recoverable; deleting `.claimbranch/` is not,
  and the CLI must say so before proceeding.
- **Schema churn.** Every schema change ships a numbered migration with a
  dry-run, or an export/reimport path. Dogfooding data must survive S1 through
  S4; if it does not, dogfooding stops and the plan loses its only continuous
  feedback.
- **Manuscript writes.** Snapshot before write, compile after write, restore on
  failure. Snapshots are retained until the corresponding debt is verified.
  Git remains the outer recovery layer.
- **Imports.** Re-importing an artifact with the same content hash is a no-op.
- **Merges.** A partial merge never mutates the source branch; recovery is a
  revert commit, never history rewriting.
- **Evidence.** Corrections use `supersedes` or invalidation with a reason.
  Nothing accepted is ever deleted.
- **GPU sessions.** Assume interruption. Keep source in Git and sync rather than
  editing on the instance; checkpoint to persistent storage before any long
  run. A destroyed instance costs at most the current run, never accumulated
  work.
- **Stage abandonment.** Record why in `Surprises & Discoveries`, move
  unfinished items to a later stage or explicitly out of scope, and never mark
  the stage complete.

## Artifacts and notes

### Local hardware

Verified 2026-08-04 with `nvidia-smi`:

```text
NVIDIA GeForce RTX 2080 SUPER   8192 MiB   driver 591.86   CUDA 13.1   WDDM
```

Turing, compute capability 7.5. Roughly 11 TFLOPS fp32, fp16 tensor cores, and
about 496 GB/s of memory bandwidth. The desktop session already holds around
1.2 GB, so plan for close to 7 GB usable.

What it **has**: CUDA, Triton, Nsight Systems and Nsight Compute, fp16 tensor
cores, shared memory and bank-conflict behavior, warp scheduling and occupancy,
and everything the roofline model needs.

What it **lacks**: bf16 and fp8, asynchronous copy, Hopper features such as TMA
and warp-group instructions, more than 8 GB, and a second GPU.

Practical consequence: this card is the same generation as the free Kaggle T4,
but local and unmetered. The highest-iteration work belongs here.

### Hardware requirement per lab

Assign every lab the cheapest hardware that can actually teach it, and never run
a lab on a card more expensive than it needs.

| Lab | Where it runs | Why |
|---|---|---|
| G1 roofline, profiling | **local** | Occupancy, bandwidth, and roofline are architecture-independent; the profiler works fully |
| G2 Triton fundamentals | **local** | Coalescing, tiling, bank conflicts, and launch overhead are all observable on Turing; this is the highest-iteration lab and it is now free |
| G3a tiled matmul, fp16 tensor cores | **local** | Turing has fp16 tensor cores; codegen quality is weaker than newer parts, which is itself worth measuring |
| G3b asynchronous-copy pipelining, modern attention | rental, Ampere or newer | `cp.async` does not exist before Ampere. Derive and correctness-test locally; measure the pipelined version on rental |
| G4 training, bf16 or fp8, MFU | rental, Ampere or newer; Ada for fp8 | No bf16 on Turing. Rehearse the whole pipeline locally in fp16 with loss scaling, then do the measured run on rental |
| G5 serving, paged attention, long context | rental, Ampere or newer, 24 GB or more | Modern serving stacks assume Ampere-era attention kernels, and long context needs the memory |
| G6 collective semantics, NCCL correctness | **free dual-T4 notebook** | A single local card cannot do this; two T4s over PCIe are enough for correctness and for measuring interconnect-bound behavior |
| G6 NVLink scaling figures | `(opt)` rental, NVLink SXM pair | Optional. The PCIe measurement plus a validated cost model is acceptable if stated as such |
| G7 capacity and cost | **local, no GPU needed** | Modeling built on G5 measurements and published specifications |
| Product local inference | **local** | A small quantized model fits in 8 GB, so the privacy path in S5 is real rather than hypothetical |

### Procurement tiers, rates checked 2026-08-04

Prices move; re-check before booking. Marketplace rates are interruptible.

| Tier | Use | Options | Indicative cost |
|---|---|---|---|
| 0 — local | G1, G2, G3a, G7, product local inference, all correctness testing | RTX 2080 SUPER under WSL2 | $0, unmetered |
| 0b — free | G6 collective work only | Kaggle Notebooks, dual T4, about 30 h/week | $0 |
| 0c — free credits | anything above the free tiers | signup credits and monthly free allowances on hosted-notebook and serverless-GPU platforms; exhaust these before paying | $0 |
| 1 — cheap interruptible | G3b, G4 rehearsal | Vast.ai RTX 4090 ~$0.13-0.37/h, RunPod Community RTX 4090 ~$0.34/h | tens of dollars |
| 2 — fixed rate | G4 measured runs, G5 benchmarking | Vast.ai A100 80GB ~$0.67/h median, RunPod A100 SXM ~$1.49/h, Lambda A100 80GB ~$2.06/h | the largest single line item |
| 3 — one prepared booking | G5 long context, `(opt)` G6 NVLink | Vast.ai H100 SXM ~$2.13/h median, RunPod ~$3.29/h, Lambda ~$2.99/h; NVLink SXM nodes ~$3-4/h per GPU | book once, prepared, short |

Because tier 0 now absorbs the iteration-heavy labs, rentals are surgical. The
dominant cost risk is idle instances and debugging on rented hardware, not the
hourly rate. A prepared session that runs for one hour costs less than an
unprepared session that idles for six.

### Local environment practices

- Do GPU work under WSL2 with an Ubuntu distribution. The kernel toolchain
  targets Linux, and the local card is reachable through the same driver. Keep
  the working copy on the Linux filesystem rather than across the Windows mount.
- Raise the Windows display-driver timeout before running long kernels, or the
  driver resets the device mid-run and the failure looks like a kernel bug.
- Close GPU-consuming desktop applications before measuring. Around 1.2 GB and
  a variable share of the card are otherwise held by the browser and shell.
- Record or pin clocks and report medians with spread. Consumer cards boost and
  throttle, so a single timing number is not a measurement.
- Write the reference implementation in plain PyTorch or NumPy first and make it
  the correctness oracle before any kernel is written.
- Use Triton interpreter mode for index debugging when a kernel is wrong rather
  than merely slow.
- Keep every lab runnable by one command so a rented session is `sync, run,
  collect, destroy`.
- Collect profiler traces on the rented instance and analyze them locally.
- Arrive at every rented session with a written list of what will be measured
  and what result would falsify the current belief.

### Sources

- [GPU Cloud Pricing Comparison 2026 - Spheron](https://www.spheron.network/blog/gpu-cloud-pricing-comparison-2026/)
- [RunPod vs Lambda Labs vs Vast.ai - Klymentiev](https://klymentiev.com/blog/runpod-vs-lambda-vs-vast)
- [Cloud GPU Rental Guide 2026 - PromptQuorum](https://www.promptquorum.com/power-local-llm/cloud-gpu-rental-guide-2026)
- [Best Free Cloud GPU Platforms in 2026 - IoTbyHVM](https://iotbyhvm.ooo/best-free-cloud-gpu-platforms-in-2026-google-colab-kaggle-and-more/)
- [NVIDIA H200 Price Guide 2026 - Jarvis Labs](https://jarvislabs.ai/blog/h200-price)

### Sealed baseline

Written in S0 before any application code. Do not edit after committing;
corrections go in a dated addendum below.

- Pending.

### v1.1 backlog

Items discovered after the v1.0 definition is met. Entries here do not reopen a
stage.

- Pending.

### Cost log

One row per rented session: date, provider, instance, hours, cost, purpose,
what was learned. Reconcile against the spend ceiling in `Decision Log`.

- Pending.

### Running notes

Keep measurements, diffs, and short evidence here. Do not paste long command
output; link to a committed artifact instead.
