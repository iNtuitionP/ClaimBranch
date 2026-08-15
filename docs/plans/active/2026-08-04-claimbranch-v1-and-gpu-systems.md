---
kind: exec-plan
status: active
owners: maintainers
last_reviewed: 2026-08-14
---

# ExecPlan: ClaimBranch graph contract to live-paper validation

This is a living plan. Keep `Progress`, `Surprises & Discoveries`, `Decision
Log`, and `Outcomes & Retrospective` current as work proceeds.

The filename is retained for link stability. The 2026-08-14 scope review
removed GPU systems mastery and a full v1.0 build as co-equal outcomes. The
pre-review plan remains recoverable from Git history. GPU learning may
continue in its own repository and plan, but it does
not block ClaimBranch.

## Purpose and big picture

ClaimBranch is a local-first personal research agent that preserves human
authorship while making AI available throughout empirical research.

Its single product promise is:

> When an unexpected result challenges an important claim, ClaimBranch
> preserves the lineage from evidence through AI contribution and human
> judgment to manuscript consequence, and accepts only changes that the
> researcher knowingly authorizes.

The first wedge is deliberately concrete: one real saturation truth packet,
three confirmed Observations, one central Claim, one reasoning branch, one
selective merge, one marked LaTeX block, one compile cycle, and one human debt
closure. Two named variants exercise it: `H0-manual` runs with AI disabled and
contains no Proposal or model trace, while `H0-recorded` consumes a frozen,
normalized proposal without calling a provider. Each variant must replay to
its own byte-identical full-audit golden manifest. Their manifests are not
expected to match because their contribution, review, trace, and debt history
is intentionally different.

The graph-first choice means the semantics and authority contract for this
wedge are complete before product UI implementation. It does not mean a full
ontology, generalized semantic version control, a graph database, GraphRAG, or
a graph canvas is built first.

### Definition of this plan being done

This plan is complete when:

1. canonical documents agree on the product promise, F0 boundary, authority
   model, and release gates;
2. the F0 contract has executable normal, forbidden, interrupted, recovery,
   replay, and privacy fixtures;
3. a minimal headless kernel completes `H0-manual` and `H0-recorded`, then
   replays each operation log to its own byte-identical golden manifest without
   making a provider call;
4. a supported native-Windows builder can bootstrap the repository, run
   `doctor`, and reach the isolated offline saturation demo in at most five
   minutes without administrator access, a provider, or a LaTeX installation;
5. the smallest local review surface supports real human authorization,
   contextual teach-back, deferral, and visible debt;
6. V0 observes the first three qualifying result-to-decision episodes on the
   next real paper or reaches its eight-week horizon, compares them with the
   Markdown decision-log/checklist baseline, and assigns the frozen outcome;
   and
7. evidence from that live gate determines whether OpenClaw integration, local
   serving work, broader UI, and generalized graph behavior proceed.

Passing the retrospective fixture means `foundation validated`, not product
success. Do not call the product v1.0 before the live-paper gate passes.

## Progress

- [x] 2026-08-14 - Completed builder-mode office hours and approved the
      human-authorship-preserving, graph-contract-first direction.
- [x] 2026-08-14 - CEO scope synthesis removed the co-equal GPU curriculum,
      full UI, generalized semantic VCS, and premature v1.0 target. A
      three-round independent specification review converged at 9/10 after 17
      fixes; Engineering must revalidate the three post-cap mechanical fixes.
- [x] 2026-08-14 - Completed design, engineering, and developer-experience
      plan reviews. The plan now distinguishes validation harnesses from the
      public CLI, moves clean-checkout onboarding before H0 completion, and
      gives the local-provider learning lane an explicit boundary.
- [x] 2026-08-14 - Reconciled the root orientation, product/release contracts,
      target architecture, finite domain design, saturation case, accepted ADRs
      0005-0007, indexes, and external-research references. P0 remains open for
      the redacted truth packet and frozen Markdown/checklist baseline.
- [ ] P0 - Reconcile canonical product, architecture, release, validation, ADR,
      and plan documents; assemble the real saturation truth packet.
- [ ] P1 - Close the F0 graph and authority contract with readable fixtures.
- [ ] P2 - Implement and verify the minimal headless kernel.
- [ ] P3 - Add provider-neutral proposals and the minimum local review surface.
- [ ] P4 - Run and evaluate three prospective episodes on the next real paper.
- [ ] P5 - Admit only expansions whose gates pass.

The executable milestone names used throughout this plan are:

| Milestone | Deliverable | Entry gate | Exit gate |
|---|---|---|---|
| `H0` | deterministic headless F0 kernel plus the `H0-manual` and `H0-recorded` goldens | P0 scope lock and P1 contract fixtures pass | both variants complete, forbidden paths fail closed, and each log replays to its own golden |
| `H1` | minimum local review experience plus a provider-neutral proposal boundary | `H0` passes | review/authorization negative tests pass and the bounded provider smoke test changes no accepted state |
| `V0` | preregistered live-paper evaluation with the Markdown/checklist baseline | `H1` passes and the restore drill succeeds | an outcome is assigned by the frozen decision rule: `VALIDATED`, `VALUE_NOT_DEMONSTRATED`, `NOT_VALIDATED`, or `INCONCLUSIVE` |

## Surprises & Discoveries

- 2026-08-14 - The prior plan was four efforts joined by scheduling: a research
  product, a graph platform, a GPU curriculum, and a local-serving study. Two
  independent CEO reviews identified this as the dominant execution risk.
- 2026-08-14 - OpenClaw's durable advantage is the assistant experience,
  onboarding, existing-channel reach, control plane, skills, and replaceable
  model boundary. ClaimBranch should integrate with that runtime later rather
  than reproduce it.
- 2026-08-14 - OpenClaw's official local-model guidance warns that small or
  heavily quantized models raise context, quality, and prompt-injection risks.
  An 8 GB local GPU is suitable for bounded tasks and learning, not an assumed
  default for the complete research agent.
- 2026-08-14 - “Graph engineering” names several different problems. The
  canonical scientific graph, disposable retrieval/context projections, and
  agent execution trace require different authority and retention rules.
- 2026-08-14 - A graph can prove recorded lineage, authorization, integrity,
  and replay equivalence. It cannot prove scientific truth or certify human
  understanding.
- 2026-08-14 - Replay equivalence needs separate complete goldens for the
  manual and recorded-proposal histories; comparing unlike histories to one
  manifest would erase provenance rather than validate it.
- 2026-08-14 - A fixture-bounded contract still needs numeric maxima. The V0
  inventory now caps every record family, proposal revision, trace, review,
  receipt, contribution, and authorized operation so `out_of_f0` is decidable.
- 2026-08-14 - A complete internal graph contract is not a usable first run.
  Both DX outside voices found that the prior plan could pass its fixtures while
  leaving a fresh Windows builder without a bootstrap, readiness check, safe
  demo, public command language, or first-project path.
- 2026-08-14 - The lowest-effort product demonstration is the existing
  saturation fixture rendered as an isolated AI-off lineage walkthrough. It
  shows the distinctive evidence-to-manuscript consequence without requiring a
  provider, a real paper, or a compiler.

## Decision Log

- 2026-08-14 - **Human-owned research agent is the product; semantic version
  control is a mechanism.** This supersedes the plan's product framing, not ADR
  0001 or ADR 0003.
- 2026-08-14 - **Approach B, complete F0 graph contract first.** “Complete” is
  bounded to the first wedge's record inventory, authority, time, provenance,
  transitions, failure behavior, replay, and privacy.
- 2026-08-14 - **AI is continuously available but proposal-only.** Provenance
  and understanding are independent. High-impact deferral creates visible
  understanding debt that only a human can resolve.
- 2026-08-14 - **Human authority is technical, not a caller-supplied actor
  field.** Model-facing ports cannot confirm evidence, materialize reasoning,
  merge, apply patches, or close debt. Raw durable-state writes by an agent are
  outside the trusted boundary.
- 2026-08-14 - **The product uses three planes:** canonical scientific state,
  disposable context/retrieval projections, and append-only execution trace.
  Derived similarity or extraction never becomes accepted science implicitly.
- 2026-08-14 - **GPU systems mastery moves outside this plan.** ClaimBranch may
  later supply real prompt shapes and an evaluation set, but product stages do
  not wait for kernel, training, distributed, rental, or capacity labs.
- 2026-08-14 - **No implementation stack is settled before bounded spikes.** A
  repository-local Python package and CLI are the distribution hypothesis.
  SQLite is the first storage baseline; a graph-native store is considered only
  if correctness or measured budgets fail.
- 2026-08-14 - **No local model default is chosen in advance.** AI-off is the
  safe baseline. One local and one hosted provider may later share a proposal
  contract; task quality and privacy policy determine defaults.
- 2026-08-14 - **OpenClaw/MCP is an adapter, not the kernel.** It follows a live
  need and a least-privilege tool contract.
- 2026-08-14 - **The retrospective fixture is a contract test, not market
  evidence.** A live paper and a Markdown/checklist comparison are required.
- 2026-08-14 - **Manual core first; AI remains one explicit action away.** The
  first run uses `AI: off` and `Network: deny`; H1 adds a bring-your-own-endpoint
  learning path without making inference a correctness or availability
  dependency.
- 2026-08-14 - **One public command language, separate from kernel and test
  operations.** User-facing commands use stable task-oriented nouns, typed
  exit codes, human and JSON output contracts, and one executable rescue action
  per handled failure. Internal operation names remain implementation detail.
- 2026-08-14 - **The first visual direction is a quiet editorial lab notebook.**
  Evidence, scientific consequence, and manuscript diff carry the hierarchy;
  AI and graph machinery remain visibly attributable but visually secondary.

## Outcomes & Retrospective

Pending. Record whether the graph contract survived implementation, whether the
live paper produced repeated voluntary use, which material omissions surfaced,
what understanding debt remained open, and which planned expansions were
rejected by evidence.

## Context and orientation

### Canonical sources this plan must obey

- [Product specification](../../product/product-spec.md)
- [Validation prototype](../../product/releases/validation-prototype.md)
- [Candidate MVP](../../product/releases/candidate-mvp.md)
- [Saturation validation case](../../validation/cases/saturation.md)
- [Target architecture](../../../ARCHITECTURE.md)
- [Draft domain model](../../designs/2026-08-03-domain-model.md)
- [ADR index](../../architecture/decisions/README.md)
- [Human authority and understanding debt](../../architecture/decisions/0005-human-authority-provenance-and-understanding-debt.md)
- [Three graph planes and provider boundary](../../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md)
- [Research episode and manuscript saga](../../architecture/decisions/0007-research-episode-and-manuscript-saga.md)
- [Research-agent, graph, and local-serving references](../../references/research-agent-runtime-and-graph.md)
- [Native-Windows trust and recovery references](../../references/windows-local-trust-and-recovery.md)

The repository is still in specification and validation-design stage. There is
no usable application and no settled implementation stack.

The linked product, architecture, domain, ADR, and validation documents are the
canonical homes for durable behavior and constraints. The detailed review
material later in this ExecPlan records how execution scope was derived; it
does not supersede those sources.

### Primary operator and support hypothesis

The primary H0/H1 operator is one empirical researcher-builder maintaining one
Git-tracked LaTeX paper on a native-Windows workstation. They can clone a
repository, run a documented PowerShell command, read a relative path, and
make scientific judgments. They are not expected to manage Python virtual
environments, inspect SQLite, edit `.claimbranch/`, configure ACLs, debug
provider JSON, or understand the internal graph schema. The secondary H1
persona is an unfamiliar researcher with the same scientific context and less
ClaimBranch knowledge. The maintainer implementing the kernel is a third,
distinct persona and may use the validation harness hidden from normal help.

| Concern | H0/H1 support hypothesis to freeze in the P1 toolchain ADR |
|---|---|
| host | native Windows 11 x64, standard user, local NTFS volume; exact supported build is recorded by `doctor` |
| shell and source | PowerShell from a clean Git checkout; no WSL, Docker, administrator shell, or global editable environment required |
| paper | one local Git-tracked LaTeX project, one marked source block, one pinned noninteractive compiler workflow for H1/V0 |
| browser and presence | one supported current Windows browser plus an OS-backed foreground-presence mechanism proven by the P1 spike |
| inference | optional; AI-off always works, and any H1 local provider is already running behind an OpenAI-compatible loopback endpoint |
| privacy | no remote telemetry or implicit outbound request; exact content review precedes any remote-capable egress |
| initially unsupported | macOS/Linux, WSL/UNC/network/synced roots, ARM64, collaboration, non-LaTeX manuscripts, unattended authorization, and managed model installation |

The spike must explicitly decide rather than assume behavior for Windows
editions/builds, PowerShell versions and execution policy, runtime ownership,
Git, Edge/browser lifecycle, Windows Hello or fallback presence, NTFS/reparse
points, controlled-folder access, antivirus sharing violations, long paths,
spaces, Korean/non-ASCII names, case collisions, compiler discovery, and
MiKTeX/TeX Live package prompts. Unsupported or unproven combinations fail
before a real project is initialized; `doctor` labels every probe `required`,
`optional`, `unsupported`, or `unknown` in both human and JSON output.

The filesystem topology remains legible and separated:

```text
[ClaimBranch source/install]       read-only program and lockfile
             |
             +--> [paper Git root] source controlled by the researcher
                    |-- .claimbranch/   canonical/project-local metadata
                    |-- manuscript/     researcher-owned LaTeX source
                    `-- build output    compiler policy decides location

[Windows user profile]            credentials, signing key, bounded logs
[owner-only temp/saga area]        encrypted snapshots and isolated compile
[disposable demo root]             never aliases or follows links into a paper
```

P1 freezes what may be copied, backed up, ignored by Git, or safely deleted.
Secrets never enter the paper tree. Demo cleanup rejects symlinks/reparse
points and refuses any path that resolves inside a real project.

### Vocabulary and authority boundary

- **Evidence ledger** - global, append-only accepted artifacts, runs,
  observations, corrections, invalidations, and retractions.
- **Reasoning state** - branchable Claims, Interpretations, scientific
  relationships, Experiment Plans, Decisions, manuscript anchors, patches, and
  debt.
- **Contribution chain** - ordered AI proposal, human edit, human adoption,
  deterministic derivation, and later correction records. Human editing does
  not erase AI influence.
- **ReviewBundle** - mutable exact operation, rationale, impact, expected state,
  and teach-back answer or deferral. Sealing it creates the digest that a human
  authorizes.
- **Understanding debt** - an open human-review obligation created when a
  high-impact AI-influenced operation proceeds with teach-back deferred. It is
  not a score and AI cannot close it.
- **Manuscript debt** - a recorded mismatch between accepted research state and
  the manuscript.
- **Current view** - a branch/ref view resolved against the latest evidence
  ledger.
- **Historical view** - a branch/ref commit resolved at its stored evidence
  watermark. Re-evaluating it with current evidence creates a new analysis.
- **Accepted state** - canonical episode metadata, evidence, reasoning,
  decision, debt, and manuscript records reachable after a valid
  DomainOperation. Episode membership is workflow provenance, not scientific
  endorsement. A Proposal, trace payload, projection, or unsealed ReviewBundle
  is never accepted state.
- **Materialize** - convert selected proposal content into a new human-reviewed
  DomainOperation while retaining the Proposal and Contribution links. It is
  not an in-place promotion of a Proposal.
- **Selected merge** - the single F0 operation that copies an explicit,
  dependency-closed set from one non-nested reasoning branch into current
  `main`; it is not a general three-way merge.
- **Impact closure** - the typed transitive set of accepted Claims, Decisions,
  anchors, and debts reachable from a changed item under the F0 relationship
  rules and evidence watermark.
- **Trace completeness** - every accepted AI-influenced operation has an
  immutable Proposal reference, ordered Contribution chain, sealed review
  digest, human AuthorizationReceipt, Decision/rationale, and either completed
  teach-back or open UnderstandingDebt; every manuscript consequence has an
  anchor and patch saga outcome.
- **Research episode** - the durable unit that binds one unexpected-result
  workflow to a project, eligibility-rule version, starting Ref heads, starting
  evidence watermark, and ordered DomainOperations. It groups provenance and
  evaluation without claiming that all referenced scientific records were
  created inside the episode.
- **Qualifying live episode** - a prospective result that meets the frozen V0
  eligibility rule and enters both baseline and ClaimBranch capture before the
  researcher records the final interpretation or manuscript decision.

### Three graph planes

```text
                         human-authorized operations only
                                      |
                                      v
  +------------------------------------------------------------------+
  | Canonical scientific state                                       |
  | global evidence ledger + branchable reasoning/manuscript state   |
  +------------------------------------------------------------------+
                  | durable IDs/hashes                 ^ proposals are
                  v                                    | materialized only
  +--------------------------------------+  +--------------------------+
  | Context/retrieval projections        |  | Execution trace          |
  | FTS, neighborhoods, embeddings,      |  | requests, inputs, model, |
  | summaries; disposable and rebuildable|  | outputs, edits, outcomes |
  +--------------------------------------+  +--------------------------+
                  | read-only context                   ^
                  +-------------------> AI provider ----+
```

The “graph” is a semantic contract, not a database choice. The F0 baseline is
an operation log plus relational records and typed relationships. Similarity,
GraphRAG communities, embeddings, and AI-extracted links remain projections.

### Closed F0 contract

F0 is a closed vocabulary. Every canonical record except `DomainOperation`
uses the common envelope `{id, project_id, schema_version,
created_operation_id, created_at, content_hash}`. A DomainOperation uses its
own `id` as the creation boundary and therefore omits the circular
`created_operation_id` field. Time is RFC 3339 UTC; IDs and hashes are stable
strings; payloads use versioned canonical JSON. State changes append a
DomainOperation or event rather than editing prior accepted records. The fields
below are the only type-specific required fields; implementations may add
indexes, never new semantic fields, without changing this contract.

Every record and command payload validates against a versioned JSON Schema
with `additionalProperties: false`. Those schemas close primitive types,
enums, nullability, string/collection bounds, and numeric ranges.
`DomainOperation.payload` must match the schema selected by the finite
`operation_type` enum; it is not an extension bag. The immutable
DomainOperation/event log is authoritative. Current Ref heads and lifecycle
status/resolution values for Proposal, debt, patch, and merge records are
deterministic projections over that log, not fields updated inside hashed
canonical records.

| Record kind | Required type-specific fields | Saturation-fixture cardinality |
|---|---|---|
| `ResearchEpisode` | `kind`, `eligibility_rule_version`, `baseline_ref_heads`, `baseline_evidence_watermark`, `opened_at` | each H0 store: exactly 1; V0 live project: 0-6 total, at most 3 invalidated and the first 3 valid starts when available |
| `ArtifactRef` | `uri_or_relpath`, `sha256`, `media_type`, `sensitivity` | exactly 2: result artifact and manuscript source |
| `Run` | `run_key`, `method_ref`, `started_at`, `completed_at`, `status` | exactly 1 completed run |
| `Observation` | `statement`, `value_or_category`, `units`, `run_id` | exactly 3 |
| `EvidenceEvent` | `action`, `target_id`, `rationale`, `supersedes_id` | exactly 3 confirmations plus at most 3 correction/invalidation/retraction events; total 3-6 |
| `Claim` | `statement`, `scope`, `status` | exactly 1 central claim |
| `Interpretation` | `statement`, `branch_ref`, `evidence_watermark` | exactly 1 branch interpretation |
| `ScientificEdge` | `edge_type`, `source_id`, `target_id`, `rationale` | 3-6, using only the edge table below |
| `ExperimentPlan` | `objective`, `claim_id`, `status` | zero or one; present only if the truth packet needs it |
| `Decision` | `decision_type`, `selected_ids`, `rationale`, `branch_ref` | 1-3, including the selected-merge decision |
| `ManuscriptAnchor` | `file_relpath`, `marker_id`, `fingerprint`, `expected_file_hash` | exactly 1 |
| `PatchIntent` | `anchor_id`, `expected_file_hash`, `replacement_digest`, `reason` | exactly 1 |
| `PatchAttempt` | `patch_intent_id`, `snapshot_digest`, `result_file_hash`, `compile_config_id` | 1-3 attempts; projected lifecycle has exactly one verified result in the happy path |
| `ManuscriptDebt` | `anchor_id`, `cause_id` | exactly 1 identity; open/closed and resolution operation are projected from commands |
| `UnderstandingDebt` | `accepted_operation_id`, `review_bundle_id` | `H0-manual`: 0; `H0-recorded`: exactly 1; open/closed and resolution are projected |
| `DomainOperation` | `episode_id`, `operation_type`, `actor_class`, `expected_ref_heads`, `evidence_watermark`, `payload`, `idempotency_key` | 1-32 accepted transitions per episode, of which at most 24 are receipt-authorized |
| `Ref` | `name` | exactly 2: `main` and one non-nested branch; head and evidence watermark are projected from operations |
| `SelectedMerge` | `source_ref`, `target_ref`, `base_operation_id`, `selected_ids`, `closure_ids`, `expected_heads` | exactly 1 |
| `Proposal` | `episode_id`, `parent_proposal_id`, `intended_command`, `normalized_payload`, `trace_manifest_id` | `H0-manual`: 0; `H0-recorded`: 1 root and 0 revisions; H1/V0: 0-3 total, one root plus at most 2 human-requested revisions |
| `Contribution` | `target_operation_id`, `sequence`, `contributor_class`, `action`, nullable `proposal_id` | 1-64 per episode and at most 8 per target operation; `proposal_id` is null only for purely human contribution and required for every AI-influenced contribution |
| `ReviewBundle` | `episode_id`, `revision`, `parent_bundle_id`, `draft_operation_digest`, `expected_heads`, `impact_digest`, `provenance_digest`, `rationale`, `teachback_disposition`, `sealed_at` | one immutable sealed revision per authorized command, at most 3 revisions per command and 72 per episode |
| `AuthorizationReceipt` | `review_digest`, `project_id`, `episode_id`, `session_nonce`, `authorized_operation_id`, `expected_heads`, `issued_at`, `expires_at`, `signature` | exactly one per authorized command and at most 24 per episode; a unique operation reference proves single consumption |
| `ExecutionTraceManifest` | `request_digest`, `response_digest`, `model_identity`, `tool_context_digest`, `payload_availability`, `retention_class` | `H0-manual`: 0; `H0-recorded`: 1; H1/V0: 0-3, exactly one for each provider-produced Proposal or revision |

Record cardinality counts identities created by an episode, not preexisting
records it references or append-only transition events. Every operation has an
`episode_id`; records derive their episode from `created_operation_id`.
`start-episode` atomically creates the preallocated ResearchEpisode identity and
its root operation, so there is no circular hash. H0 variants use separate
stores. V0 uses one cumulative live project, permits at most one active episode,
and records each episode's starting heads/watermark; an episode may reference
earlier accepted Claims without recreating them.

The fixture may omit the optional ExperimentPlan; no other record kind or extra
branch is admitted. At most three post-start protocol-invalid episodes may be
replaced; a fourth makes V0 `INCONCLUSIVE`. Product failure after a valid start
never invalidates or replaces it. A need outside these bounds changes F0 and
requires an ADR or a later trigger-gated phase.

The same saturation cardinalities are the maximum admitted by each V0 valid
start. A prospective episode that exceeds them is logged as `out_of_f0`, counts
as an incomplete product flow rather than an invalid/replaced episode, and
cannot expand the contract during V0.

#### Closed F0 resource limits

These are proposed safety bounds for the contract spike, not measured product
capacity. The schemas and ingress gateway enforce them before allocation or
append; the spike may lower them but cannot silently raise them.

| Resource | F0 maximum |
|---|---:|
| stable ID / enum / hash text | 128 UTF-8 bytes / 64 bytes / 128 bytes respectively |
| relative path or URI text | 1,024 UTF-8 bytes after normalization |
| one statement, rationale, answer, or diagnostic message | 16,384 UTF-8 bytes |
| any semantic collection | 128 items unless a smaller cardinality is named above |
| one canonical DomainOperation JSON payload | 262,144 bytes |
| one truth-packet manifest, normalized Proposal, or outbound context | 1 MiB / 256 KiB / 256 KiB respectively |
| one retained provider request or response blob | 2 MiB; 8 MiB total per Proposal revision and 24 MiB per episode |
| one manuscript source, encrypted snapshot, or postimage | 16 MiB each; exactly one marked file in F0 |
| proposal provider calls | 2 attempts per revision, at most 6 per episode |
| patch/compile attempts | at most 3 per PatchIntent |
| rejected validation/authorization diagnostics | first 128 detailed attempts per episode, then a saturating per-code counter with no further payload append |
| live-project episode identities during V0 | 6 total: at most 3 valid plus 3 protocol-invalid replacements |
| retained non-authoritative trace/snapshot ledger | 256 MiB per project; overflow rejects new provider/patch work without changing accepted state |

`ResourceLimitError` is the single overflow outcome. Once a detailed-attempt or
ledger cap is reached, repeated untrusted calls do not append more records; the
human may inspect/export and explicitly start a new bounded episode or archive
eligible raw payloads. Artifact bytes remain externally referenced and are not
silently copied into the store. Every exact fixture count and every V0 maximum
has a distinct schema rule so “exactly” is never reused as an accidental live
minimum.

#### Allowed graph relationships

Each relationship is a `ScientificEdge` or the named structural reference in
its owning record. No free-form edge label is accepted.

| Relationship | Source -> target | F0 cardinality/invariant |
|---|---|---|
| `uses_artifact` | `Run -> ArtifactRef` | run has one or more; result artifact has one incoming use |
| `produced` | `Run -> Observation` | the one run has exactly 3; each Observation has exactly one producer |
| `evidence_targets` | `EvidenceEvent -> ArtifactRef|Run|Observation` | each event has exactly one target |
| `interprets` | `Interpretation -> Observation` | 1-3 targets; all resolve at its watermark |
| `supports`, `challenges`, `qualifies` | `Observation|Interpretation -> Claim` | at least one `challenges`; rationale required |
| `tests` | `ExperimentPlan -> Claim` | exactly one when the optional plan exists |
| `decides` | `Decision -> Claim|Interpretation|SelectedMerge|PatchIntent` | one or more selected targets |
| `expresses` | `ManuscriptAnchor -> Claim` | exactly one central Claim |
| `patch_targets` | `PatchIntent -> ManuscriptAnchor` | exactly one |
| `attempts` | `PatchAttempt -> PatchIntent` | exactly one; attempts are ordered |
| `debt_concerns` | `ManuscriptDebt|UnderstandingDebt -> accepted record or operation` | exactly one direct cause; transitive impact is derived |
| `proposes` | `Proposal -> draft DomainOperation` | exactly one intended command; draft is not accepted state |
| `contributes_to` | `Contribution -> DomainOperation` | exactly one target; sequence is gap-free and immutable |
| `reviews` | `ReviewBundle -> draft DomainOperation` | exactly one digest-bound draft |
| `authorizes` | `AuthorizationReceipt -> ReviewBundle` | exactly one; receipt is single-use |
| `records` | `ExecutionTraceManifest -> Proposal` | exactly one root Proposal |
| `selects` | `SelectedMerge -> accepted reasoning records` | explicit IDs plus complete mandatory dependency closure |

#### Allowed commands and authority

| Command | Caller/capability | Canonical effect |
|---|---|---|
| `inspect`, `compute-impact`, `diagnose` | human read capability, or field/sensitivity-scoped model query capability | none; model queries return bounded redacted projections, never raw artifact bytes or general paths |
| `export` | human-only out-of-band export capability | none in source; produce an explicit bounded manifest outside model reach |
| `rebuild-projection` | maintenance capability | replaces only disposable projection state |
| `capture-proposal`, `revise-proposal`, `reject-proposal`, `cancel-proposal` | model/agent proposal-ingress capability or human | trusted ingress validates and appends only bounded non-authoritative Proposal/trace/disposition data |
| `start-episode`, `close-episode`, `invalidate-episode` | foreground human or frozen V0 runner | create/project the bounded episode lifecycle; invalidation requires a preregistered protocol reason |
| `import-truth-packet` | human authorization | create bounded initial accepted records |
| `record-evidence-event` | human authorization | append confirmation/correction/invalidation/retraction; never rewrite evidence |
| `create-reasoning-branch`, `record-interpretation`, `record-decision` | human authorization | change only branchable reasoning state |
| `prepare-review`, `seal-review` | foreground review session | create/seal ReviewBundle; no accepted-state change |
| `authorize-review` | human authorization broker only | issue one short-lived receipt after an explicit foreground gesture |
| `materialize-proposal` | kernel plus unconsumed receipt | create a new accepted DomainOperation and Contribution chain |
| `apply-selected-merge` | kernel plus unconsumed receipt | copy the one dependency-closed selection into current `main` |
| `answer-teachback`, `defer-teachback`, `close-understanding-debt` | human authorization | record answer/deferral or human-only closure; AI cannot grade or close |
| `derive-manuscript-debt` | deterministic kernel inside a receipt-authorized commit | atomically open/update debt from that operation's accepted impact closure; it is not a standalone mutation path |
| `prepare-patch`, `apply-patch`, `verify-compile`, `restore-patch` | human authorization for prepare/apply; bounded manuscript saga thereafter | journal, write, compile, finalize or restore; graph/file atomicity is never claimed |
| `close-manuscript-debt` | kernel plus closure-specific unconsumed receipt after verified compile | close only the exact debt/patch/compile tuple sealed for human authorization |
| `replay`, `import`, `verify-manifest` | maintenance capability against a new isolated destination | reconstruct/verify trusted or explicitly untrusted history; never append to the source or an existing live project |

Any command not listed is forbidden in F0. `actor_class="human"` in a request
does not confer authority.

The trusted kernel command gateway is the only writer to the accepted operation
store. Proposal and model processes receive no database handle: their narrow
IPC endpoint accepts only versioned Proposal/trace schemas, fixed operation
intent enums, bounded sizes, and gateway-assigned actor/episode data, then
writes a separately permissioned non-authoritative inbox/ledger. Callers cannot
select a canonical operation type or accepted-state table. Materialization
copies only the sealed normalized digest and contribution references through
the regular human-authorized kernel path.

Model-readable query capability is distinct from human export. The context
compiler enforces project, record-type, field, sensitivity, count, and byte
allowlists; it withholds artifact bytes, secrets, absolute paths, raw retained
payloads, and manuscript text not explicitly selected for this request. Every
provider egress passes one trusted broker. A loopback endpoint counts as
local-only only when its address is pinned, redirects are disabled, DNS is not
used, and the process is OS-denied external network; otherwise it is treated as
remote and requires the exact one-shot outbound review.

#### Public operator command contract

The command table above is the internal kernel capability inventory, not the
researcher's CLI. P1 freezes one public task language; validation-only commands
remain under `claimbranch dev` and are absent from normal help.

```text
claimbranch doctor [--scope core|manuscript|provider]
claimbranch demo saturation
claimbranch project init|status
claimbranch episode template|start|list|show|review|close
claimbranch provider add|list|show|probe|test|explain|remove
claimbranch manuscript doctor|anchor add|anchor verify|check|prepare|apply
claimbranch recovery status|inspect|restore|verify
claimbranch audit show|export|verify
claimbranch store status|migrate
claimbranch diagnose <diagnostic-id>
claimbranch dev fixture run|manifest verify
```

The grammar is noun-first except the universal root tasks `doctor`, `demo`, and
`diagnose`. All examples use the full `claimbranch` name; an optional `cb`
alias may follow only after collision and discoverability tests. Commands infer
the project and sole active episode only when unambiguous, otherwise they list
the candidates and the exact resolving flag. Every successful human-mode
command prints one safe next action. Mutating help states whether a command can
write project state, change a manuscript, use the network, or require
foreground presence.

| Global option | Contract |
|---|---|
| `--project <path>` | explicit paper root; otherwise search parents for one validated project marker |
| `--format human|json` | human is default on a terminal; JSON is one versioned document and never prompts |
| `--ai off|configured` | separates inference availability from network policy; default is `off` until a profile exists |
| `--network deny|local-only|consented` | `deny` forbids even provider probing; `local-only` requires proven loopback isolation; remote use still needs exact foreground consent |
| `--no-color`, `NO_COLOR` | remove ANSI without changing meaning; statuses never rely on color alone |
| `--quiet`, `--verbose` | suppress progress or add redacted diagnostics; neither changes operation semantics |
| `--help`, `--version` | succeed without opening a project or store |

Human mode writes the requested result or receipt to stdout and progress,
warnings, and handled errors to stderr. Redirected output has no pager,
interactive prompt, or ANSI. JSON mode writes exactly one UTF-8 JSON document
to stdout for success or a handled failure, with no secret, progress prose, or
stack trace; an unhandled runtime crash may use stderr. Automation can inspect
or prepare work but cannot synthesize user presence or consume a human-only
receipt.

The minimum JSON envelope is versioned and stable through H0:

```json
{
  "schema_version": "claimbranch.cli/v1",
  "ok": false,
  "code": "CBR-STATE-001",
  "exit_code": 4,
  "diagnostic_id": "attempt-id",
  "message": "This review is out of date.",
  "unchanged": ["accepted_state", "manuscript"],
  "next_actions": [{"command": "claimbranch episode review --refresh"}]
}
```

| Exit | Closed class |
|---:|---|
| 0 | requested operation completed |
| 2 | CLI usage or input/schema error |
| 3 | unsupported environment or missing prerequisite |
| 4 | stale state, conflict, or changed review |
| 5 | authorization, presence, or consent required/denied |
| 6 | recoverable provider or external dependency failure |
| 7 | manuscript/compile failure; debt remains open |
| 8 | integrity failure or `recovery_required`; mutation locked |
| 9 | incompatible software/store/schema version |
| 10 | resource limit reached |
| 130 | user interruption normalized on the supported shell/runtime |

Configuration precedence is explicit flag, project config, user config, then
built-in default. Project configuration is a validated
`.claimbranch/config.toml`; user secrets and the authorization key live in the
Windows credential store and never appear in a command argument, project file,
log, trace, or diagnostic bundle. `provider show --effective` redacts secrets
and records only effective nonsecret configuration in the trace.

Every handled error has stable code, plain title, state-change guarantee,
preserved-work statement, one copy-paste next action, diagnostic ID, and a
version-matched help topic. Golden fixtures include at least these three paths:

```text
CBR-STATE-001 This review is out of date.
Nothing was authorized, and no manuscript file was changed.
Your rationale and edits are saved.
Next: claimbranch episode review --refresh
Diagnostic: <id>
```

```text
CBR-PROVIDER-001 The AI provider did not return a usable suggestion.
Nothing was accepted. The request manifest and failure details are saved.
You can continue without AI.
Next: claimbranch provider probe <name>
Diagnostic: <id>
```

```text
CBR-RECOVERY-001 ClaimBranch cannot prove which manuscript bytes are current.
Accepted-state and manuscript mutation are locked; ClaimBranch will not guess.
Your audit state and recovery evidence are preserved.
Next: claimbranch recovery status
Diagnostic: <id>
```

Compile copy may say `restored` only after byte equality is proved. Public
recovery remains available when normal store opening fails and never tells the
operator to edit `.claimbranch/`, a database, journal, or encrypted snapshot.

Operational observability is local-only by default. One correlation ID spans
CLI, review session, provider attempt, DomainOperation, and patch saga. P1
freezes bounded locations, field sensitivity, rotation, retention, and deletion
for operational logs, provider traces, compiler logs, and diagnostic bundles.
`claimbranch diagnose`, `status --format json`, and
`audit export --diagnostics --preview` reveal the included/excluded fields,
size, retention class, and digest before creating a local redacted bundle.
Sending it is always a separate human action.

#### Allowed minimum UI states

H1 uses a finite product of four visible state dimensions instead of one flat
`committed` state that could falsely imply manuscript safety:

| Dimension | Closed values |
|---|---|
| `workspace_mode` | `opening`, `empty`, `manual_ready`, `proposal_review`, `review_editing`, `review_sealed`, `authorization_pending`, `stale_review`, `pending_unaccepted`, `accepted_review_pending`, `accepted`, `rejected`, `typed_error` |
| `provider_phase` | `not_requested`, `outbound_review`, `loading`, `cancelled`, `ready`, `offline`, `failed` |
| `manuscript_phase` | `not_applicable`, `debt_open`, `patch_prepared`, `applying`, `applied_unverified`, `compiling`, `verified`, `restored_after_failure`, `recovery_required` |
| `projection_health` | `ready`, `rebuilding`, `degraded` |

Only `review_editing` can change rationale or teach-back. Sealing moves the
workspace to `review_sealed`; any bound head or file change moves it to
`stale_review` and disables authorization. `Not now` creates
`pending_unaccepted` without accepted mutation. `Authorize now; review
explanation later` may create `accepted_review_pending` only in the same atomic
operation that opens UnderstandingDebt. `accepted` describes the graph
operation only; the separate manuscript phase remains visible until
`verified`. Provider failure always offers `manual_ready`.
`manuscript_phase = recovery_required` or a canonical-integrity failure derives
a dominant `recovery_only` surface lock; that lock is not a second persisted
state and permits only inspect, export, or restore.

None of these UI dimensions is authoritative persisted state. The UI derives
them from Proposal, review, receipt, operation, patch-saga, and projection
events. Four independent transition tables define legal events; a generated
reachability set, not the raw Cartesian product, is the contract:

| Dimension | Legal transition outline |
|---|---|
| workspace | `opening -> empty|manual_ready|proposal_review`; `manual_ready|proposal_review -> review_editing|pending_unaccepted|rejected`; `review_editing -> review_sealed|pending_unaccepted|rejected|stale_review`; `review_sealed -> authorization_pending|review_editing|stale_review`; `authorization_pending -> accepted|accepted_review_pending|stale_review|typed_error`; `accepted_review_pending -> accepted` only after human debt closure |
| provider | `not_requested -> outbound_review|loading`; `outbound_review -> loading|cancelled`; `loading -> ready|cancelled|offline|failed`; a retry starts a new bounded attempt |
| manuscript | `not_applicable -> debt_open -> patch_prepared -> applying -> applied_unverified -> compiling -> verified`; `applying|applied_unverified|compiling -> restored_after_failure|recovery_required`; supersession returns an unchanged file to `debt_open` or requires restore/hard stop |
| projection | `ready -> rebuilding -> ready|degraded`; `degraded -> rebuilding`; the last valid projection remains readable |

Cross-dimension invariants forbid authorization before a sealed review, remote
loading before exact consent, `accepted_review_pending` without open
UnderstandingDebt, manuscript progress without an accepted PatchIntent, and
`verified` without a matching pinned compile record. A model-based generator
enumerates every reachable tuple and event, tests all legal transitions, and
proves every other tuple/event is rejected during load or render. Two tabs see
the same derived state; they do not own independent writable state machines.

#### Human authorization broker protocol

The command-launched review server binds only to a random loopback port and
creates a 256-bit one-use bootstrap secret. It exchanges that secret for a
`Secure`, `HttpOnly`, `SameSite=Strict` session cookie, immediately redirects to
a clean URL, sets `Referrer-Policy: no-referrer`, accepts only an exact pinned
Host/Origin, has no wildcard CORS, and rejects requests without a per-session
CSRF token. CSP uses `frame-ancestors 'none'`; provider calls originate in the
trusted backend rather than browser JavaScript.

The browser may prepare and seal a review but never receives signing material
or a portable receipt. On authorization, the broker independently reloads the
sealed ReviewBundle, recomputes its digest and expected state, and requests an
OS-backed user-presence operation with a non-exportable key. It delivers the
single-use receipt directly to the kernel over an ACL-protected private IPC
channel; JavaScript receives only a result/receipt ID. The model/provider
process runs under an AppContainer, sandbox, or distinct identity that cannot
connect to that IPC endpoint or read the key/store.

The target-Windows spike must demonstrate strict Host/Origin/CSRF handling,
frame denial, direct-IPC denial, broker-key non-exportability, hostile local
page denial, receipt replay denial, and a user-presence cancellation. If the
target OS cannot demonstrate the process and presence boundary, H1 falls back
to the separate foreground CLI/native helper and cannot claim browser-mediated
technical authorization.

#### Cross-record invariants

1. Accepted mutation requires a valid receipt whose ID is uniquely consumed by
   one DomainOperation and which is bound to the sealed
   ReviewBundle digest, project, session nonce, expected Ref/file hashes,
   schema/rule version, impact/provenance digests, rationale, and
   teach-back disposition. A review edit appends a new revision and invalidates
   any receipt for an earlier digest.
2. Evidence is global and append-only; a reasoning Ref cannot hide an accepted
   EvidenceEvent. Historical views use their stored evidence watermark.
3. A Proposal is never a Claim, Decision, edge, merge, patch, or debt closure.
   Materialization creates new accepted records and preserves its contribution
   chain transitively.
4. A high-impact, AI-influenced accepted operation atomically records either a
   human teach-back answer or an open UnderstandingDebt. Only a later
   human-authorized answer can close that debt.
5. The selected merge is non-nested, has one source and current `main` target,
   and includes all mandatory edge endpoints and provenance dependencies.
6. ManuscriptDebt closes only after the exact PatchIntent reaches a verified,
   version-pinned compile result. Its closure-specific sealed bundle and
   receipt bind project/debt/cause IDs, PatchIntent and verified PatchAttempt,
   source and output hashes, compiler/config/rule fingerprints, current Ref
   heads/evidence watermark, and a non-restored saga state. Any source, output,
   head, config, impact, restore, or supersession change invalidates the
   receipt. Failure or uncertainty leaves debt open.
7. Canonical accepted replay depends only on operations, versioned rules, and
   retained canonical records. Projection contents and raw provider bytes are
   disposable and cannot change the result.
8. Every durable reference resolves; deletion is represented by a retained
   event or payload-unavailable marker, never a dangling identifier.
9. Golden-fixture execution injects a deterministic clock, ID/nonce generator,
   test signing key, schema/rule versions, and compiler fingerprint.
   `content_hash` is SHA-256 over canonical JSON with the `content_hash` field
   excluded. Production entropy is recorded once; replay consumes those
   recorded values and never regenerates time, IDs, nonces, or signatures.
10. A trusted import verifies a signed manifest chain, schema/rule versions,
    content hashes, and every receipt against an enrolled project-authority
    public key. An untrusted import remains labeled historical claims in a new
    isolated store and cannot become accepted local authority.

#### Hypothesis firewall

| Product hypothesis | Minimum admitted in F0 | Explicitly excluded until a trigger passes |
|---|---|---|
| Semantic branching makes changed reasoning legible | one non-nested branch and one dependency-closed selected merge | nested/criss-cross branches, rebase, general LCA merge, conflict solver |
| A graph earns its capture cost | finite typed records/edges and deterministic impact closure | universal ontology, graph-native database, canvas-first interaction |
| Provenance protects human authorship | ordered contribution chain retained through materialization | file-level “AI generated” tag as the sole provenance mechanism |
| Teach-back limits understanding debt | 1-3 contextual prompts, explicit deferral, one visible Inbox, human-only closure | scoring, automatic grading, forced blocking on all AI use |
| Manuscript consequences can be kept aligned | one marked block and a recoverable patch/compile saga | arbitrary LaTeX AST rewriting or repository-wide auto-editing |
| Provider portability supports always-available AI | one frozen envelope and one bounded two-provider smoke test after H0 | model installation, routing, fallback orchestration, serving operations |
| Derived retrieval can remain disposable | deterministic neighborhood plus optional FTS projection | embeddings, GraphRAG, AI-extracted canonical relationships |

The Markdown/checklist “sentinel” is only the V0 comparison artifact. F0 does
not build separate sentinel software.

## Plan of work

```text
P0 scope lock + truth packet
  -> P1 complete F0 contract and fixtures
      -> P2 headless deterministic kernel
          -> P3 provider boundary + minimal review surface
              -> P4 three live-paper episodes + baseline comparison
                  -> P5 conditional expansion gates
```

## Concrete steps

Execute P0 through V0 strictly in the order below. The exact planned commands,
artifacts, and pass oracles are in `Validation and acceptance`; a later phase
does not start because code exists, only because the preceding named gate
passes.

### P0 - Scope lock and research truth packet

- Update the canonical product promise and release sequence.
- Add one primary-operator card, one secondary unfamiliar-user card, the
  support/exclusion hypothesis, and the nine-stage journey to the canonical
  product and validation sources. Keep internal `P0`/`H0`/`V0` names out of
  user copy; use `offline demo`, `episode review`, and `live-paper evaluation`.
- Extend the accepted AI-proposal decision with a new ADR for human-only
  authorization, contribution provenance, and understanding debt.
- Record the three-plane boundary and derived-state rule as an ADR.
- Reconcile the draft domain model with the approved office-hours design.
- Assemble one redaction-aware truth packet: pre-result claim, run artifact,
  three observations, unaided human interpretation, affected marked LaTeX
  block, compile command, and expected manuscript-impact truth set.
- Define the Markdown decision-log/checklist baseline that the live product
  must beat or match.
- Define the DX stopwatch and privacy-safe local measurement fields before any
  onboarding implementation: clean-checkout prerequisites, bootstrap start,
  first demo screen, demo completion, active/wall time, copied commands, help
  invocations, recoverable errors, and abandoned attempts.

Exit: documentation checks pass; one fact has one canonical home; the F0
inventory and exclusions are explicit; no unresolved authority ambiguity is
left to implementation.

### P1 - F0 graph and authority contract

- Freeze the public CLI contract separately from internal DomainOperations and
  the validation harness: command grammar, project/episode discovery, global
  options, help snapshots, streams, UTF-8/color rules, JSON envelope, exit
  codes, configuration precedence, idempotency, noninteractive limits, and
  stable next actions.
- Freeze canonical handled-error copy and rescue commands for stale review,
  provider failure, privacy digest change, compiler restore, integrity hard
  stop, unsupported environment, resource overflow, and version skew. A
  diagnostic ID resolves through a read-only path even in recovery-only mode.
- Define stable identity, canonical serialization, operation ordering, schema
  version, evidence watermark, and rule-version behavior.
- Define contribution-level provenance and transitive `AI-influenced` status.
- Define complete transition tables for proposal, teach-back, understanding
  debt, patch, merge, correction, and recovery states.
- Define typed dependency closure for the exact selected merge shape.
- Define human capability creation, binding, expiry, consumption, and replay
  protection. The foreground review broker alone holds a signing key from the
  OS credential store and issues a receipt only after a direct user gesture.
  The model/agent process has a read/proposal capability, no signing material,
  no writable store handle, and no filesystem permission to the canonical
  store. Passing `actor_class=human` is a negative test, not authentication.
  If the operating system cannot enforce this separation for processes under
  one identity, H0 requires an AppContainer/sandbox or distinct local identity;
  the plan cannot claim raw-write isolation without a demonstrated denial.
- Define the loopback review/broker protocol above, including bootstrap,
  session, Host/Origin/CSRF/frame defenses, OS user presence, private receipt
  delivery, IPC ACL, and the tested native-helper fallback.
- Make the kernel gateway the only accepted-state writer; place bounded
  Proposal/trace ingress behind a schema-only IPC port and separately
  permissioned non-authoritative store. Fuzz caller-selected type, actor,
  episode, size, and schema/version inputs.
- Split human export from model query. Define the context compiler's project,
  record, field, sensitivity, count, and byte allowlists and route every
  provider egress through the digest-bound consent broker. Test prompt-injected
  export, indirect tool use, redirect, DNS rebinding, and a loopback process
  that still has external network.
- Bind each receipt to the canonical ReviewBundle digest, project, session
  nonce, expected Ref and file hashes, schema/rule version, exact operation,
  impact/provenance digests, rationale, teach-back answer or deferral, expiry,
  and one consumption record. Test missing, forged, expired, replayed,
  cross-project, stale-head, changed-file, and digest-mismatch receipts.
- Bound privacy to this single-user local wedge: canonical state is local;
  journals, snapshots, and retained raw trace payloads are encrypted with an OS
  credential-store key; remote requests require an exact outbound preview,
  redaction manifest, and per-request opt-in; loopback local endpoints do not
  imply permission to send remotely. Hard erasure applies only to unreferenced
  raw payloads and preserves a payload-unavailable audit marker. Cloud backup,
  key recovery, legal retention, multi-user access, and general privacy
  compliance are explicitly outside F0.
- Run two bounded spikes before locking implementation choices:
  1. operation-log/relational traversal and replay with SQLite; and
  2. LaTeX marker/fingerprint behavior under move, duplicate, split, rewrite,
      stale file, compile failure, and interrupted recovery.
- Run a third bounded native-Windows spike and record its toolchain ADR:
  standard-user bootstrap, runtime and lockfile ownership, supported OS/shell/
  filesystem/browser/compiler matrix, OS presence, credential storage,
  AppContainer or fallback isolation, loopback lifecycle, Korean/spaced/long
  paths, reparse points, controlled folders, and antivirus sharing failures.
  No Python, SQLite, browser, or TeX choice becomes product truth before this
  evidence exists.
- Define import trust modes: verify-only untrusted history and trusted restore
  into a new empty destination. Trusted restore requires a signed manifest
  chain and explicitly enrolled authority public-key fingerprint; F0 never
  merges an import into an existing live project.
- Define copy-on-write schema migration before any live accepted data exists:
  `store migrate --check` and `store migrate` create and verify a new store,
  acquire a migration lock, retain the original, and atomically select the new
  store only after manifest verification. Fixtures interrupt every durable
  boundary, check disk-space failure and version skew, and leave a newer store
  available to read-only status, diagnosis, and export. Destruction of the old
  store is never part of migration.
- Freeze local logs and diagnostics: locations, size ceilings, rotation,
  retention, sensitivity taxonomy, project-relative path display, redacted
  bundle preview, and the rule that no telemetry, crash report, or feedback is
  transmitted automatically.

Exit: every closed-F0 definition has a readable fixture, allowed transition,
invalid transition, and named assertion; authorization, read scope, egress,
proposal ingress, and raw-write denials are enforced outside caller-controlled
request data. SQLite is only the measured storage-spike baseline; adopting it
for P2 requires a proposed/accepted implementation ADR after the spike passes.
The illustrative Python/pytest commands below likewise become executable only
after the toolchain decision is recorded. The anchor contract narrows to
manual application when deterministic relocation is unsafe.

### P2 - Minimal headless kernel (`H0`)

- After the toolchain ADR, provide one repository-owned, standard-user
  PowerShell bootstrap from a clean checkout. It creates an isolated pinned
  environment, installs the `claimbranch` entry point, prints
  `claimbranch --version`, and then prints the exact `claimbranch doctor` next
  action. It must not edit the user's shell profile or require administrator
  access.
- Implement `claimbranch doctor`, public root/topic help, version, stable
  streams/exit codes/JSON, `diagnose`, audit export/verify, and recovery status/
  inspect/restore/verify before treating H0 as usable. Test redirected output,
  PowerShell piping, no color, interruption, Korean/spaced paths, ambiguous
  project discovery, and every golden error message.
- Add `claimbranch demo saturation --ai off --network deny`. It creates a
  disposable non-project store, uses the existing saturation truth packet,
  requires neither a provider nor LaTeX, shows three observations challenging
  one Claim and one exact manuscript consequence, labels the frozen AI text
  `Not accepted`, verifies its audit manifest, and proves no user project or
  manuscript changed. Cleanup prints the retained path or removes only the
  verified disposable root.
- Implement pure deterministic domain validation separately from storage,
  projection, provider, manuscript I/O, and CLI adapters.
- Load the saturation fixture and expose only commands needed for observation
  confirmation, proposal review/materialization, branch inspection, selected
  merge, debt derivation, patch intent/application, compile verification, debt
  closure, replay, export/import, and diagnostic explanation.
- Preserve atomic graph operations with idempotency keys and expected heads.
- Use a durable saga for external manuscript writes; never claim graph/file
  atomicity.
- Delete and rebuild all projections; verify the accepted-state manifest is
  unchanged.
- Run `H0-manual` with every provider disabled. It contains no Proposal,
  ExecutionTraceManifest, AI Contribution, or UnderstandingDebt.
- Run `H0-recorded` from the frozen normalized proposal and trace manifest.
  Initial execution and replay make zero network/provider calls and retain AI
  contribution plus the open-and-human-closed UnderstandingDebt.
- Replay each variant into a fresh isolated store and compare its full audit
  manifest with that variant's own golden. A separately named scientific-state
  projection may be compared across variants only if its excluded audit fields
  are documented; it is never called the accepted-state manifest.
- Exercise `store migrate --check` plus interrupted copy-on-write migration
  against disposable H0 stores before any H1 or V0 data may be retained.

Exit: unauthorized accepted-state mutations and dangling references are zero;
`H0-manual` and `H0-recorded` each replay byte-for-byte to their own golden;
the recorded path proves no live-provider call occurred; compile failure
restores the manuscript byte-for-byte; every closure-specific stale/forged/
model/replay case fails and the exact post-verification human closure succeeds;
the browser/IPC/read/egress denials pass; and trusted plus untrusted
isolated-store restore drills assign the correct authority.
From the declared clean-checkout starting state on the named supported Windows
machine, bootstrap through the verified offline demo completes in at most 300
seconds wall time and 90 seconds human active time across three cold-cache
trials; the demo itself completes in at most 60 seconds after bootstrap. A
compiler-installed full marked-LaTeX fixture has a separate ten-minute budget
and cannot make the provider-free demo depend on LaTeX.

### P3 - Proposal providers and minimum review experience (`H1`)

- Add a safe real-project path before the review UI:
  `project init --dry-run`, `project init`, `episode template`, `episode start`,
  `manuscript doctor`, and marker add/verify. The generated episode template
  uses researcher concepts rather than store schemas. Initialization reports
  intended paths, Git state, compiler policy, marker state, egress state, and
  rollback; a failure leaves the paper and accepted state unchanged.
- Add one provider-neutral proposal request/response contract and durable
  request manifest. Raw provider bytes are retention-policy dependent; replay
  uses normalized captured proposals.
- After H0 passes, run one bounded portability smoke test: at most five frozen,
  privacy-safe request fixtures against one hosted endpoint and one already
  running loopback OpenAI-compatible endpoint. Validate only envelope/schema,
  cancellation, and accepted-state non-mutation. The local endpoint may be
  `llama.cpp`-compatible, but model download, installation, quantization,
  process supervision, routing, fallback, throughput benchmarking, and serving
  operations are outside H1. Neither endpoint is a correctness or authority
  dependency and deterministic CI calls neither one.
- Turn that bounded smoke test into a visible bring-your-own-endpoint learning
  lane without taking over the server: `provider add`, `probe`, `test`, and
  `explain` report endpoint/trust classification, redirects, model ID, context
  ceiling, structured-output compatibility, request/response schema, TTFT,
  token usage/throughput when available, cancellation, and whether the process
  is externally network-capable. `test` shows the exact normalized request and
  a visibly unaccepted Proposal; any failure returns to the manual path. The
  operator can complete one deterministic stub-provider exercise and one
  already-running loopback exercise in ten active minutes. ClaimBranch does not
  download, quantize, start, stop, route, update, or benchmark model servers.
- Build the minimum direct local review experience:
  - a command-launched local `Episode Review` workspace for the current
    research situation; conversational chat is deferred;
  - one linear decision sheet ordered by situation, not-yet-accepted AI
    suggestion, scientific before/after, dependency closure, manuscript
    consequence, human rationale/teach-back, and action-scoped authorization;
  - an explicit `Request AI suggestion` action and a digest-bound outbound
    review step before any remote request;
  - two distinct deferrals: `Not now` makes no accepted change, while
    `Authorize now; review explanation later` opens visible UnderstandingDebt;
    and
  - a small `Review pending` list/session recap that resumes the exact episode.
- Keep only non-authoritative capture quiet. Medium-impact AI-influenced
  acceptance requires a one-line rationale; high-impact AI-influenced work
  requires 1-3 contextual prompts or an explicit debt-opening deferral. Every
  accepted mutation still has action-specific authorization. Do not display a
  punitive score or let AI grade understanding.
- Complete the normal loopback lifecycle: random-port collision retry, one
  server lease per project, `episode review --no-open`, a clean copyable URL,
  default-browser failure, session expiry/reconnect, browser close during
  authorization, explicit stop, and corporate proxy/firewall diagnostics.
- Before V0, an unfamiliar supported-Windows researcher completes bootstrap,
  doctor, offline demo, project dry run, one manual episode, one deferred
  review resume, and recovery inspection without coaching or direct
  `.claimbranch/` edits. The artifact records success thresholds and every help
  or rescue step; failure blocks V0 rather than becoming a qualitative note.

Exit: model-facing ports cannot obtain human capabilities or mutate accepted
state; local/hosted/frozen inputs validate against the same versioned proposal
envelope (their proposal content need not match);
provider timeout, refusal, empty output, malformed JSON, schema violation, and
cancellation are visible and leave accepted state unchanged.

### P4 - Prospective live-paper validation (`V0`)

Freeze the protocol, checklist, clocks, evaluator prompts, and decision rule in
version control before the first episode. V0 observes the first three
consecutive qualifying valid starts within eight weeks; it is not a randomized
or causal study. A valid start is an eligible, correctly timed episode after
baseline capture begins; later product failure still belongs to that start.

An episode qualifies only when all of these are true: the result was produced
after preregistration; it may change an already accepted central/supporting
Claim or its marked manuscript block; it is entered before the final
interpretation or manuscript decision; and the researcher is legally and
ethically permitted to capture the required artifacts locally. Eligibility is
decided before and independently of whether ClaimBranch's current schema,
limits, or adapters can represent them. A representability or size failure
after a valid start is `out_of_f0` and counts against the product. Retrospective
rehearsals, formatting-only changes, known-answer demo cases, and results with
no claim/manuscript consequence are ineligible.

For every eligible episode, the researcher first completes the frozen plain
Markdown checklist/decision log without ClaimBranch suggestions and records a
timestamped baseline artifact. This checklist is the sentinel; no sentinel
software is built. ClaimBranch then receives the raw episode artifacts, not the
baseline answer, and runs H1. Baseline active time runs from opening the blank
template to its saved decision; ClaimBranch active time runs from opening the
episode context to its recorded decision. Deliberate pauses are excluded from
active time but captured as wall-clock interruption time; provider and compile
wait are reported separately, not silently removed.
Separately report the setup funnel from discovery through bootstrap, doctor,
project initialization, first review, help use, rescue attempts, and
abandonment; setup friction is not hidden by the episode active-time clock.

The same-episode order creates a learning effect, so V0 may show directional
utility and workflow noninferiority, not causal prevention. A `material
omission surfaced` means a concrete claim dependency, rationale, provenance
link, debt, or manuscript consequence absent from the frozen baseline was
raised by ClaimBranch before the final decision and the researcher attested in
writing that it changed what they checked, recorded, or wrote. Report that
language; never report “ClaimBranch prevented an omission” from V0 alone.

An attempted capture can be marked invalid only for a preregistered eligibility failure
discovered after capture or corrupted timing instrumentation; log it with the
reason and take the next consecutive eligible episode. Provider failure,
abandonment, anchor failure, authorization failure, or any product failure
after a valid start counts against the product and is not replaceable. Stop at
three valid starts, a fourth protocol-invalid replacement, or eight weeks,
whichever comes first; the fourth invalidation makes the run `INCONCLUSIVE`.
Keep the real
repository in an isolated Git worktree or verified copy; require compile and
manifest verification before an explicit human promotion; run the exact
byte-restore drill before V0. ClaimBranch never commits, pushes, or promotes
the live manuscript automatically.

For each episode record trace completeness, baseline and product active time,
wait/interruption time, accepted AI contribution, human edits/rationale,
teach-back/debt state, manuscript consequence, attested material omissions,
false alarms, anchor repair, abandonment, and promotion/restore outcome. After
self-use, repeat the already-gated unfamiliar-user path only when a V0 change
invalidated it; this observation never replaces the three scientific episodes.
Freeze application, lockfile, store/schema/rule, compiler, and fixture versions
before V0. Rehearse clean checkout, first real project, verified export,
copy-on-write migration, rollback selection, and diagnostics on a second clean
user profile or supported machine before the first qualifying episode.

Assign exactly one outcome by evaluating the rows in order and taking the first
match. This makes the outcomes mutually exclusive and exhaustive:

Global catastrophic predicates in row 1 are evaluated even when no valid start
exists. The completion-ratio and trace-count predicates are evaluated only when
`valid_starts > 0`; with zero valid starts and no catastrophic breach they are
false and row 2 assigns `INCONCLUSIVE`. The checker freezes the equivalent
truth table and tests zero starts both with and without every row-1 breach.

| Order/outcome | Frozen decision rule |
|---|---|
| 1. `NOT_VALIDATED` | any unauthorized accepted mutation, unrecovered manuscript loss, or silent promotion; completion ratio across valid starts is below 2/3; or at least two valid starts have incomplete trace |
| 2. `INCONCLUSIVE` | fewer than 3 valid starts occur by eight weeks, or timing/protocol corruption makes the frozen comparison unusable |
| 3. `VALUE_NOT_DEMONSTRATED` | all trust/file rules pass and 3 valid starts exist, but any one of the three product flows or trace sets is incomplete (including `out_of_f0`), median ClaimBranch active time exceeds baseline median +10%, or no attested material omission is surfaced |
| 4. `VALIDATED` | all 3 flows complete voluntarily; trace completeness is 100%; trust/file rules pass; median ClaimBranch active time <= baseline median +10%; and at least one attested material omission is surfaced |

Only `VALIDATED` permits P5 product expansion. Other outcomes permit fixes to
the failed gate and a newly preregistered V0 run, not adjacent features.

### P5 - Conditional expansion

Only the maintainer may admit an expansion, in a dated plan/ADR entry that
links the named evidence artifact and confirms V0 is `VALIDATED`:

The measurement configuration is frozen before qualifying evidence is seen:
`provider_wait_budget_ms=30000`, `local_ttft_p95_ms=3000`,
`local_decode_median_tps=12`, and `clean_checkout_demo_ceiling_seconds=300` on the
named target Windows machine. Changing a value requires a preregistered plan
revision and discards evidence collected under the old value for that trigger.

| Expansion | Numeric admission trigger after V0 | Evidence artifact |
|---|---|---|
| OpenClaw/MCP adapter | at least 2 manual transfer events occur in each of at least 2 episodes, and a tool-capability test denies all human-only commands and raw writes | episode friction log plus capability test |
| broader local-serving study | at least 30 frozen real/privacy-safe proposals exist **and** either privacy rejection is >=20% across at least 20 frozen remote opportunities **or** provider wait p95 is >=30,000 ms under the frozen population rule below; a purely educational track gets a separate repository/time budget | frozen corpus and provider report |
| vLLM/SGLang/rental benchmarks | at least 30 cases exist and the already-running local baseline misses the frozen target by >20%: TTFT p95 >3,600 ms or median decode <9.6 tokens/s | benchmark preregistration |
| embeddings or GraphRAG | on at least 30 frozen retrieval questions, typed neighborhood plus FTS recall is below 90% after two bounded tuning attempts | retrieval error analysis |
| graph-native database | a correctness invariant cannot be implemented in SQLite, or a design budget is missed by >20% after two profiled query/index attempts | profiles and failed-gate report |
| generalized merge/revert | two independent prospective cases require the same out-of-F0 branch/merge shape | two redacted case manifests |
| full graph canvas/dashboards | after exactly one focused context/Inbox correction pass, at least 5 recorded navigation failures remain across at least 3 qualifying starts | UX event and interview log |
| broad import mapping | two independent real result formats cannot be represented without manual re-entry | adapter failure fixtures |
| public packaging/v1.0 | V0 is `VALIDATED`; the pre-V0 unfamiliar-user and clean-checkout gates remain passing; and export/import reproduces both H0 goldens | release-gate report |

### Failed-gate scope firewall

When P0, P1, H0, H1, or V0 fails, work may change only the failing contract,
fixture, safety mechanism, or minimum surface and its tests. It may not add a
provider, channel, graph type, database, general merge behavior, canvas,
dashboard, serving stack, or packaging. Widening the boundary requires an
updated ExecPlan, applicable ADR, independent review, and an observed P5
trigger; “the fix would be easier with the larger platform” is not a trigger.

## Validation and acceptance

The fixture and pytest rows below are the planned validation harness, not the
normal researcher CLI. Public operator rows are labeled explicitly. The
toolchain ADR may replace an illustrative runner prefix, but it must update
this plan before renaming an oracle, changing the public command language, or
weakening a gate.

| Gate | Command/artifact | Pass oracle |
|---|---|---|
| P0 scope lock | `python scripts/check_docs.py` and redacted `tests/fixtures/saturation/truth-packet/` | exit 0; all canonical indexes resolve; packet schema and expected impact truth set are present |
| P1 contract | `python -m pytest tests/contract -q` | every closed record, edge, command, state, invariant, authorization denial, temporal/privacy rule, and invalid transition has a named passing fixture |
| H0 clean checkout (public) | `pwsh -NoProfile -File .\scripts\bootstrap.ps1`, then `claimbranch doctor --format json` | standard user, declared prerequisites only, isolated pinned environment, version printed, all core probes pass; three cold trials reach the demo gate within 300 seconds wall/90 seconds active |
| H0 offline demo (public) | `claimbranch demo saturation --ai off --network deny` | first meaningful output within 60 seconds after bootstrap; verified lineage from 3 Observations to 1 Claim and 1 manuscript consequence; AI text remains unaccepted; no provider/compiler/user-project write |
| H0 CLI contract | `python -m pytest tests/cli -q` | root/topic help, unknown-command suggestion, public/dev separation, stdout/stderr, UTF-8, `NO_COLOR`, JSON schemas, exit codes, interruption, discovery, and golden rescue copy pass |
| H0 manual | `claimbranch dev fixture run tests/fixtures/saturation/h0-manual.json --ai off --network deny --out .claimbranch-test/h0-manual` then `claimbranch dev manifest verify .claimbranch-test/h0-manual tests/fixtures/saturation/h0-manual.golden.json` | exit 0; full manifest byte-matches its golden; Proposal/trace/AI Contribution/UnderstandingDebt counts are zero; network-call counter is zero |
| H0 recorded | `claimbranch dev fixture run tests/fixtures/saturation/h0-recorded.json --ai off --network deny --out .claimbranch-test/h0-recorded` then the equivalent manifest verification against `h0-recorded.golden.json` | exit 0; full manifest byte-matches its distinct golden; frozen proposal digest matches; network-call counter is zero; contribution and human debt closure are retained |
| H0 replay/recovery | `python -m pytest tests/f0/test_replay.py tests/f0/test_crash_matrix.py tests/f0/test_manuscript_saga.py -q` | fresh-store replay matches each respective golden; RPO/RTO assertions below pass; failed write/compile restores exact bytes or enters the sole hard stop |
| H0 migration | `python -m pytest tests/migration -q` and `claimbranch store migrate --check` against a disposable older fixture | export and copy-on-write destination verify before selection; every interrupted boundary retains the original; newer-store status/diagnose/export remain read-only |
| H1 first project (public) | `claimbranch project init --dry-run <paper>`, then the frozen unfamiliar-user script | dry run is non-mutating; supported paper initializes without internal edits; marker/compiler/browser rescues are actionable; the full path passes before V0 |
| H1 authority/UX | `python -m pytest tests/h1 -q` | forged/stale/replayed/cross-project receipts and direct model/store writes are denied; all allowed UI states and error rescues pass; non-authoritative actions leave accepted manifest unchanged |
| H1 provider learning (public) | `claimbranch provider probe <name>` and `claimbranch provider test <name> --fixture saturation` | deterministic stub plus one already-running loopback endpoint report compatibility, trust, schema, timing, cancellation, and visibly unaccepted output within ten active minutes; accepted-state hash is unchanged |
| H1 provider smoke | `python scripts/run_provider_smoke.py --fixtures tests/fixtures/provider --max-cases 5` | configured local/hosted endpoints return or visibly fail the same versioned envelope; no accepted-state hash changes; deterministic tests invoke only the stub |
| V0 preregistration/result | frozen `docs/validation/live/v0-protocol.yaml`, private episode manifests, and redacted `v0-result.json` checked by `python scripts/check_live_protocol.py` | protocol hash predates all episodes; eligibility/replacement/time fields are complete; checker assigns exactly one frozen outcome |

The paths are deliverables, not claims about files that already exist.

### Scope-lock gate

- Canonical documents use the same product promise and milestone order.
- F0 records and operations are enumerated; everything else is excluded or
  trigger-gated.
- Primary operator, supported environment, public command grammar, first
  success, first-project path, provider-learning boundary, and upgrade policy
  each have one canonical contract and no machine-local dependency.
- `python scripts/check_docs.py` passes.

### Contract and headless gate

- A fresh supported checkout reaches a verified offline demo within the frozen
  budget, with no administrator, provider, compiler, or real-project mutation.
- `doctor` detects every declared required/optional/unsupported/unknown host
  condition, including non-ASCII/spaced paths and unproven security primitives,
  and JSON output matches the same result.
- Public help shows researcher tasks and safe next actions while internal
  operations are discoverable only under `claimbranch dev`; handled failures
  match their golden code/copy/exit/stream contract.
- Every human-authority transition has successful, forbidden, stale,
  interrupted, replayed, and recovery cases.
- Model-facing commands cannot change the accepted-state manifest.
- Current and historical evidence views match their specified watermarks.
- Selected merge is dependency closed and leaves no dangling reference.
- Replay from durable operations is byte-stable under canonical serialization;
  each named H0 variant compares only with its own full-audit golden.
- Missing/expired trace payloads remain visibly unavailable without preventing
  accepted-state replay.
- The marked-block patch restores byte-for-byte on write or compile failure.
- Matching post-crash output bytes resume at `applied_unverified` and rerun the
  version-pinned compile; they never imply compile verification.
- The saturation manuscript-impact truth set has 100% recall and at most one
  false-positive Debt Bundle. These bounded numbers apply only to the fixture.
- Authorization fixtures prove that a model process cannot obtain the broker
  key or writable store handle and that the OS boundary denies a direct raw
  write. A caller-supplied human actor value never changes this result.
- Broker fixtures cover hostile loopback origins/Hosts, CSRF, framing,
  bootstrap replay, direct IPC, presence cancellation, two tabs, and receipt
  delivery that never exposes the portable receipt to browser JavaScript.
- Read/egress fixtures prove model queries cannot invoke human export or read
  disallowed fields/artifact bytes and cover prompt-injected indirect export,
  redirects, DNS rebinding, remote-capable loopback endpoints, and exact
  consent-digest invalidation.
- Manuscript-debt closure fixtures deny model/agent closure, wrong or
  cross-project debt, stale source/output/head/config, forged projected
  verification, restored/superseded PatchIntent, double close, and receipt
  replay. The positive case binds the exact verified tuple and records a human
  Decision.
- Privacy fixtures cover no-consent remote egress, exact-preview digest
  mismatch, referenced raw-payload deletion, unreferenced hard erasure, and
  replay with an unavailable-payload marker.
- Import fixtures distinguish trusted empty-store restore from verify-only
  untrusted history, reject unknown key lineage/schema/rules/receipt chains,
  and prove F0 cannot merge an import into an existing live project.
- Migration fixtures prove copy-on-write verification, original-store
  retention, atomic selection, bounded interruption recovery, and read-only
  diagnosis/export across version skew before live accepted state exists.

### Design-scale budgets

Initial budgets are hypotheses to verify, not product promises:

- a seeded `design-scale-1x` fixture with 1,000 canonical records, 5,000 typed
  relationships, and 100 historical episode/ref snapshots, plus an exact 10x
  fixture with 10,000/50,000/1,000;
- focused current-branch traversal p95 under 100 ms;
- historical as-of query p95 under 250 ms;
- local canonical mutation under 200 ms excluding provider/compile work;
- full projection rebuild under 5 seconds; and
- saturation replay under 2 seconds on the target Windows development machine.

The frozen workload uses 40% current typed-neighborhood queries, 20%
historical as-of views, 10% current-evidence re-evaluation, 10% contribution
trace, 10% impact closure, 5% bounded context compilation, and 5% manifest
verification. Run cold and warm trials with one writer plus four readers,
record p50/p95/max, peak RSS, database/WAL/temp sizes, and projection-rebuild
degradation, and cap peak RSS at 512 MiB, durable database at 256 MiB, WAL at
64 MiB after checkpoint, and rebuild temporary space at 2x the durable store.
The fixture generator seed, query IDs, machine fingerprint, and five measured
runs after one warm-up are artifacts. A limit breach yields a profiled failed
gate, not OOM, unbounded WAL growth, silent query truncation, or automatic graph
database adoption.

Failure first triggers query/index/representation analysis. It does not
automatically authorize a graph database.

### Live-use gate

- Apply the preregistered V0 eligibility, order, timing, invalidation, safety,
  and frozen outcome rules; do not reinterpret the result retrospectively.
- Report “material omission surfaced” only under the attestation rule, never
  causal prevention.
- False alarms, deferrals, open understanding debt, invalid episodes, and
  abandoned proposals remain visible in the episode-level report.
- Only `VALIDATED` opens P5; no full UI, OpenClaw release, serving expansion, or
  v1.0 claim precedes it.

### Serving gate

- Freeze at least 30 real or privacy-safe derived proposal cases first.
- A `remote opportunity` is a frozen case that passes request schema and
  technical policy and for which the preregistered evaluator would offer the
  hosted provider before the human privacy decision. A privacy rejection is a
  denied exact outbound preview for that reason; the denominator is all such
  opportunities and must contain at least 20 cases.
- Provider wait is measured from trusted-broker dispatch until the first valid
  envelope or terminal timeout/refusal/error. Timeouts contribute the frozen
  30,000 ms budget, cancellations are reported but excluded from the latency
  percentile, and missing observations fail the trigger rather than disappear.
  The p95 population is every non-cancelled dispatch in the named corpus and
  collection period, not only successful responses.
- Measure schema validity, unsupported scientific-edge rate, human
  accept/edit/reject disposition, human edit distance, TTFT, throughput, and
  p95 latency.
- A local model becomes a default candidate only after passing pre-agreed
  quality and security thresholds. Hardware ownership is not evidence.

## Idempotence and recovery

- Every durable operation has an idempotency key, expected ref/file state, and
  canonical digest. Repeated application returns the prior result or a visible
  conflict.
- Failed validation and stale authorization append an attempt without changing
  accepted state.
- Projection rebuild writes beside the prior valid projection and swaps only
  after validation.
- A patch saga obtains a monotonic fencing token and exclusive writer lease for
  `(project_id, canonical_file_identity, anchor_id)`. Before every side effect
  and finalization it rechecks the token, current file hash, Ref heads, debt,
  PatchIntent, and compile fingerprint. Two tabs or processes may review, but
  only the newest valid token can write; restore never overwrites divergent
  newer bytes.
- Before mutation, the saga creates and verifies an AEAD-encrypted preimage in
  the owner-only ledger, then fsyncs a write-ahead record containing saga/token,
  key version, nonce/tag, preimage size/digest, expected full postimage
  size/digest, file identity, expected state, and the version-pinned compile
  plan. An orphan encrypted blob is cleanup-only; a journal record without a
  readable verified snapshot is `recovery_required`.
- The postimage is generated in an owner-only temporary path, hashed and
  fsynced, and the journal advances before atomic replace. Replace is followed
  by file and parent-directory flush before `applied_unverified` is durable.
  Platform adapters must demonstrate Windows `FlushFileBuffers`/replace
  semantics rather than assume POSIX `fsync` equivalence.
- Compile runs with a fixed argument vector, environment allowlist, shell escape
  disabled, resource/time limits, and an isolated owner-only copy/output
  directory. It cannot mutate the live project beyond the one already-replaced
  source file. Only named verified output digests are retained; transient
  plaintext is cleanup-scanned and requires an OS-encrypted volume for an
  at-rest confidentiality claim.
- Success durably records source/output/config/compiler digests before snapshot
  cleanup. Failure atomically restores the verified preimage, flushes file and
  directory, and records `restored_after_failure`; missing key, disk full,
  divergent bytes, interrupted restore, or unaccounted compiler side effect
  enters `recovery_required`. Matching post-crash output bytes resume only at
  `applied_unverified` and rerun the pinned compile.
- A new accepted impact on the same anchor supersedes an unstarted PatchIntent.
  During an active saga it cancels before write or restores the old file; after
  verification it opens a new debt rather than rewriting history. External
  editor changes at any boundary yield stale/recovery behavior, never blind
  retry.
- Crash fixtures interrupt: before canonical transaction commit; after commit
  before response; before/after snapshot and journal flush; before/after
  temporary-file flush; before/after replace and directory flush; during
  compile; after compile success before saga finalization; during cleanup; and
  during restore. Receipt consumption and accepted operation commit share one
  transaction.
- F0 recovery objectives are narrow: canonical accepted operations have
  `RPO=0` once commit acknowledgment is returned; an interrupted local restart
  reaches a readable state or explicit `recovery_required` within 60 seconds;
  manuscript recovery is exact byte restoration or that hard stop. Regional
  disaster recovery, automated off-device backup, OS-loss recovery, and key
  escrow are outside this plan.
- Schema changes require a tested copy-on-write forward migration to a new
  store. `store migrate --check` validates compatibility and space before a
  write; apply obtains an exclusive lock, creates a verified export, builds and
  verifies the destination, and only then atomically changes the selected-store
  pointer. The original is retained until a separate explicit deletion outside
  F0. An interruption resumes or discards only the unselected destination.
  Older software may provide read-only status, diagnosis, and export for a
  newer store but never mutates it. There is no generalized bidirectional
  migration or automatic update framework in F0.
- The verified pre-migration export contains a signed manifest chain and
  project-authority public key, never private signing material. Restore targets
  a new empty store, verifies key fingerprint/schema/rules/receipts, and
  requires explicit human trust enrollment. Unverified imports remain visibly
  untrusted and cannot be promoted in F0. Raw evidence remains at its linked
  source.

## Artifacts and notes

- Git history is the portable recovery source for earlier plan revisions.
  gstack restore, review, and task artifacts are local review aids, not project
  truth and are intentionally not linked from this repository.
- The research truth packet may contain private material. Commit only redacted
  fixtures and retain a local manifest connecting fixture substitutions to the
  real episode.
- GPU curriculum details belong in `gpu-systems-lab` or another explicitly
  separate plan. Do not copy them back into this product plan.

## NOT in scope

- co-equal GPU kernel, training, distributed, rental, or capacity curriculum;
- a complete web application, daemon, desktop shell, command palette, or
  projection suite before live validation;
- arbitrary/nested/criss-cross semantic branches, general LCA merge, or an
  automatic semantic conflict solver;
- a universal scientific ontology or plugin ecosystem;
- GraphRAG, embeddings, graph-native storage, or a full graph canvas without a
  measured trigger;
- `.bib` related-work management, collaboration, mobile, SaaS, or multi-tenant
  permissions;
- autonomous agent mutation of accepted state;
- automatic proof or model grading of human understanding; and
- public installers, automatic updates, model download/quantization/server
  supervision, hosted telemetry, a provider marketplace, or cross-platform
  support before the live gate;
- a v1.0/public-release claim based only on the retrospective saturation case.

## What already exists

| Sub-problem | Existing asset | Reuse decision |
|---|---|---|
| product constraints | product spec plus ADR 0001 and ADR 0003 | preserve and extend; do not reconstruct accepted rationale |
| semantic design vocabulary | draft domain model | revise in place; remove generalized behavior not required by F0 |
| bounded scientific scenario | saturation validation case and release prototype | convert into truth packet plus executable normal/negative fixtures |
| local names and marker syntax | proposed ADR 0004 | validate through the bounded spike before acceptance |
| branch hypothesis | proposed ADR 0002 | retain as proposed until the selected-merge fixture and live comparison justify it |
| documentation governance | docs policy, indexes, and `scripts/check_docs.py` | use as the current executable quality gate |
| implementation | none | no code or settled stack exists to reuse yet |
| agent runtime/channels | OpenClaw and MCP ecosystems | integrate later; do not rebuild inside ClaimBranch |
| local inference transport | OpenAI-compatible servers such as `llama.cpp` | use only behind the provider contract after P2 |

## Autoplan review

In task labels throughout this review, `P1`, `P2`, and `P3` mean task priority,
not execution phases `P0` through `P5`. Each task body names its actual phase or
gate; new task lists spell both fields out.

### Phase 1 - CEO review

Mode: `SELECTIVE EXPANSION`. The user's approved office-hours premises and
explicit choice of Approach B satisfy the premise and approach gates.

#### 0A - Premise challenge

| Premise | Evaluation | Decision |
|---|---|---|
| The problem is transparent AI assistance in research | Too weak; transparency alone does not preserve authorship or understanding | Reframe as human-owned research with traceable AI contribution and review obligations |
| Complete graph contract should precede UI | Valid only when `complete` is fixture-bounded | Keep B with an explicit F0 inventory and kill gates |
| Semantic branching is necessarily the primary value | Unproven; a change-impact sentinel/checklist may capture much of the value | Keep one fixture branch, compare against a non-graph baseline, leave ADR 0002 proposed |
| A retrospective case proves product value | False | Use it for contract validity only; require three prospective episodes |
| Local inference should be the default because an 8 GB GPU exists | False | AI-off baseline; select providers from measured task quality and privacy |
| GPU mastery and product delivery reinforce each other enough to share gates | False | Separate plans; only real ClaimBranch serving work may feed the learning track |
| A graph proves understanding | False | Claim only lineage, authorization, integrity, and observable review/debt |

Doing nothing leaves the current manual failure intact: rationale and
manuscript consequences can be lost as experiments revise claims. It does not,
however, prove a new graph/VCS product is worth its capture cost. That is the
purpose of the baseline and live gates.

#### 0B - Existing-code leverage

There is no application code. The plan reuses accepted ADR constraints, the
draft domain vocabulary, the saturation case, proposed marker syntax, and the
documentation checker. It delegates agent runtime, channels, model transport,
Git file history, and LaTeX compilation to existing systems rather than
building parallel implementations.

#### 0C - Dream state

```text
CURRENT
specification-only repo; retrospective case; broad unstarted plan
   |
   v
THIS PLAN
fixture-bounded graph/authority contract -> headless proof -> minimal review
surface -> three live-paper episodes -> evidence-triggered expansion
   |
   v
12-MONTH IDEAL
an always-available personal research agent that reconstructs scientific
lineage, keeps AI contribution legible, asks the smallest useful human-review
question, and fits the researcher's existing work without owning every tool
```

Dream-state delta: this plan establishes the trusted semantic kernel and one
validated human loop. It deliberately does not deliver multi-channel reach,
collaboration, broad ingestion, or serving infrastructure; those remain
adapters and evidence-triggered phases.

#### 0C-bis - Implementation alternatives

| Approach | Summary | Completeness | Effort | Risk | Reuse | Decision |
|---|---|---:|---|---|---|---|
| A. Disposable change-impact sentinel | Generate a traceable manuscript-impact checklist around existing Git/LaTeX with no durable semantic branch kernel | 6/10 | M | low | Git, Markdown, LaTeX | retain as baseline, not the architecture |
| B. Fixture-bounded complete graph contract | Close authority, time, provenance, typed closure, replay, and failure semantics for one wedge, then implement headlessly | 10/10 | L | medium | ADRs, domain draft, saturation case | **selected by user** |
| C. Full semantic research platform | Generalized VCS, ontology, graph-native store, full UI, OpenClaw, and serving stack before validation | 10/10 coverage, 3/10 evidence discipline | XL | high | little | reject |

Approach B remains selected because it protects the load-bearing trust contract
without requiring the whole platform. Approach A is the comparison needed to
falsify whether B's extra structure earns its cost.

#### 0D - Selective expansion decisions

| # | Candidate | Decision | Classification | Principle | Rationale |
|---|---|---|---|---|---|
| 1 | Real truth packet and Markdown/checklist baseline | accepted | auto | P1/P3 | directly strengthens falsification for less than one day of agent work |
| 2 | Human capability plus raw-write isolation threat model | accepted | auto | P1/P5 | required for “AI cannot mutate accepted state” to be technically true |
| 3 | Provider-neutral trace manifest and replay | accepted in P3 | auto | P2/P5 | supports always-available AI without coupling authority to a model |
| 4 | Minimal contextual review card and deferred Inbox | accepted after P2 | auto | P2/P3 | required to test the user's UX premise on a live paper |
| 5 | OpenClaw/MCP adapter | deferred to trigger | auto | P3/P4 | duplicates an integration surface before a live need exists |
| 6 | Broad local-serving/GPU curriculum | deferred to separate plan | auto | P3/P4 | educationally useful but unrelated to the first product gate |
| 7 | GraphRAG, embeddings, graph-native database | deferred to measured failure | auto | P3/P5 | canonical graph semantics do not imply these technologies |
| 8 | Full UI, canvas, dashboards, related work, public packaging | deferred to live use | auto | P3/P4 | large blast radius and no evidence they are load-bearing |

#### 0E - Temporal interrogation

| Implementation time | Human-team scale | CC + gstack scale | Decision that must already be closed |
|---|---:|---:|---|
| foundations | hour 1 | 5-10 min | F0 inventory, authority, temporal axes, canonical serialization |
| core logic | hours 2-3 | 10-20 min | atomic operation boundary, typed closure, replay equivalence, invalid transitions |
| integration | hours 4-5 | 10-20 min | file/graph saga, provider failure semantics, raw-write isolation, privacy retention |
| polish/tests | hour 6+ | 10-20 min | hostile fixtures, budgets, diagnostic export, live baseline protocol |

#### 0F - Mode confirmation

`SELECTIVE EXPANSION` and Approach B were explicitly approved. The review holds
the F0 semantics firm, accepts only load-bearing validation/safety additions,
and trigger-gates the rest.

#### CEO dual voices

`CLAUDE SUBAGENT (CEO - strategic independence)` found the prior plan to be
four projects, retained the graph-first wedge when fixture-bounded, and called
for GPU separation, live-paper gates, a non-graph baseline, raw-write isolation,
and no local-model default.

`CODEX SAYS (CEO - strategy challenge)` found twelve blind spots: co-equal
objectives, reversed falsification order, candidate hypotheses promoted to
requirements, no kill gates, circular retrospective validation, late external
evidence, an unproven Git/branch metaphor, unevidenced market assumptions,
hardware-driven product strategy, incomplete workflow-cost metrics, weak
substitute testing, and a premature v1.0 rule. It proposed a disposable
scientific change-impact sentinel before generalized semantic VCS.

| Dimension | Subagent | Codex | Consensus |
|---|---|---|---|
| premises valid? | core pain yes; plan premises no | plan premises largely assumed | CONFIRMED |
| right problem? | human-owned research agent | change-impact sentinel | CONFIRMED on wedge; DISAGREE on graph-first sequence |
| scope calibrated? | no, four projects | no, three joined projects | CONFIRMED |
| alternatives explored? | add Markdown/checklist baseline | compare notes/checklists/Git-native report | CONFIRMED |
| competitive/substitute risk covered? | no | no | CONFIRMED |
| six-month trajectory sound? | only after cuts | likely unused platform without cuts | CONFIRMED |

The sequencing disagreement is a taste decision. This plan honors the user's B
choice while adopting the sentinel/checklist as a mandatory comparison and
keeping generalized semantic VCS out of F0.

#### Section 1 - Architecture review

The prior architecture coupled unrelated product, UI, provider, GPU, and
deployment work. The revised architecture uses a pure deterministic kernel,
durable store port, disposable projection port, provider proposal port,
human-only authorization port, manuscript adapter, and thin CLI/review
adapters. No provider or agent adapter receives raw durable-store access.

```text
truth packet / CLI / review UI
             |
             v
       validation + ReviewBundle --local human auth--> sealed operation
             |                                      |
             v                                      v
   deterministic domain kernel --------------> durable store
             |                                      |
             +--> projection rebuild                +--> trace/blob ledger
             |
             +--> manuscript patch saga --> compiler

context compiler --> local/hosted provider --> Proposal + trace
        ^                                      |
        +------ read-only projections ----------+
```

The first scaling limit is projection/replay cost, not distributed serving.
Single points of failure are durable-state integrity and manuscript recovery;
export/import, manifest hashes, encrypted journals, and last-valid projections
are mandatory. Rollback is append-only inverse/correction operations plus code
rollback; accepted history is never rewritten.

#### Section 2 - Error and rescue registry

| Codepath | Failure | Typed error | Rescue | User-visible result |
|---|---|---|---|---|
| truth-packet load | missing/empty/malformed/oversized input | `FixtureInputError` | reject before operation creation; name field/path | actionable validation message |
| domain validation | invalid record or transition | `DomainInvariantError` | return all bounded violations; no commit | exact invalid fields/transitions |
| operation commit | stale head or duplicate idempotency key | `StateConflictError` | return prior result or require re-review against new head | reviewable conflict, never overwrite |
| closure computation | missing mandatory dependency | `DependencyClosureError` | omit selected item or fail declared atomic command | missing dependency list |
| authorization | missing/expired/replayed/digest mismatch | `AuthorizationError` | reject, append attempt, require new sealed review | authorization expired/changed |
| durable store | lock/I/O/corruption | `DurableStoreError` | rollback transaction, preserve diagnostic, offer verified export/recovery | accepted state unchanged; recovery steps |
| projection rebuild | bad derived record or swap failure | `ProjectionBuildError` | keep last valid projection; report operation | degraded search with rebuild status |
| provider call | timeout/rate limit/unavailable | `ProviderTransportError` | bounded retry/cancel; preserve request manifest | proposal unavailable, core still works |
| provider output | empty/refusal/malformed/schema-invalid | `ProposalValidationError` | store non-authoritative attempt; never materialize | specific provider-output failure |
| trace payload | expired/redacted/missing | `TracePayloadUnavailable` | preserve audit manifest and availability state | explanation notes missing raw payload |
| anchor resolution | absent/ambiguous/stale | `AnchorResolutionError` | block auto-apply; request relink/manual application | exact anchor problem |
| patch write | path/symlink/hash/write failure | `PatchApplyError` | refuse escape, restore encrypted snapshot | file restored or recovery-required |
| compile | timeout/nonzero/missing output | `CompileVerificationError` | restore or preserve policy-defined failed attempt | compile diagnostics; debt remains open |
| recovery | snapshot unavailable or bytes diverge | `RecoveryRequiredError` | stop mutation; require human recovery flow | high-priority recovery state |

No catch-all may swallow these errors. Logs include operation ID and safe
context, not sensitive payload bytes.

#### Section 3 - Security and threat model

| Threat | Likelihood | Impact | Mitigation in plan |
|---|---|---|---|
| prompt-injected model requests accepted mutation | high | high | model ports expose proposal/query only; human capability is out of model context |
| same-user agent writes `.claimbranch/` directly | medium | high | sandbox/process boundary and filesystem ACL; no strong claim without isolation |
| capability theft or replay | medium | high | single-use, short-lived receipt bound to review digest/session/expected state |
| path traversal or symlink escape | medium | high | canonicalize against project allowlist; no follow outside root |
| compile-command injection or hostile LaTeX | medium | high | configured argument vector, no shell interpolation, resource-bounded process |
| remote-provider manuscript leakage | medium | high | exact outbound preview, redaction manifest, opt-in policy, OS secret store |
| sensitive trace/snapshot disclosure | medium | high | encryption, keyed digests, reference ledger, retention and hard erasure |
| malicious imported repository text | high | medium | treat as untrusted data, never as instructions or authority |
| dependency/supply-chain compromise | low | high | minimal dependencies, pinned lock/checksums, later security review |

The first product is single-user, so multi-tenant IDOR is outside scope. Project
path boundaries and local process identity are still enforced.

#### Section 4 - Data and interaction edge cases

```text
INPUT -> VALIDATE -> NORMALIZE -> PREPARE/SEAL -> AUTHORIZE -> COMMIT -> PROJECT
  |         |           |              |              |         |         |
 nil     wrong type   encoding      stale head     expired   I/O fail  rebuild fail
 empty   too large    duplicate     changed review replayed rollback  keep last valid
```

Tests cover nil, empty, wrong type, oversized text, Unicode normalization,
duplicate import, current versus historical evidence, correction/invalidation,
stale review cards, double-submit, navigation/cancellation, provider completion
after cancellation, deferral after a partial answer, ambiguous anchors,
concurrent ref changes, compile failure, and crash recovery. Every asynchronous
provider result remains a proposal even when the user has left the screen.

#### Section 5 - Code quality review

No application code exists. The implementation must keep the domain kernel
pure and use named adapters rather than a generic `GraphManager` or
`RepositoryService`. Durable operations, derived projections, provider traces,
and manuscript I/O need separate modules and typed errors. F0 rejects generic
plugin systems, arbitrary schema factories, duplicated state flags, and any
method that combines validation, authorization, persistence, projection, and
external I/O.

#### Section 6 - Test review

```text
NEW UX: review card; teach-back answer/defer; deferred Inbox; recovery notice
NEW DATA: truth packet; operation log; projections; trace blobs; patch journal
NEW PATHS: confirm; materialize; selected merge; patch; compile; close; replay
NEW ASYNC: provider request/cancel; projection rebuild; compile subprocess
NEW EXTERNAL: local/hosted provider; filesystem; Git metadata; LaTeX compiler
NEW ERRORS: every typed path in the Error and Rescue Registry
```

Unit tests cover invariants, serialization, transitions, closure, impact, and
rule versions. Integration tests cover store transactions, projections,
authorization consumption, provider envelopes, and patch sagas. System tests
run the exact headless scenario. A small E2E layer covers the review card.
Property tests generate invalid operation sequences; crash tests interrupt each
durability boundary; golden fixtures pin manifests and semantic diffs. External
providers are never required in deterministic CI.

#### Section 7 - Performance review

The top expected slow paths are projection rebuild, historical traversal, and
context compilation; provider and LaTeX latency are measured separately. Every
branch/ref/time query needs an explicit index or measured recursive-query plan.
Bounded context compilation must never load the whole graph or raw trace corpus.
The design-scale budgets above are the initial acceptance thresholds; no
concurrency-16 or hundred-user serving target belongs in this plan.

#### Section 8 - Observability and debuggability review

Every command emits an operation/attempt ID, expected and resulting manifest
hashes, state transition, elapsed phase, and typed outcome. Diagnostic export
reconstructs contribution chain, request manifest, human Decision, debt, and
patch saga without exporting secrets or expired payloads. Key counters include
unauthorized attempts, stale reviews, invalid proposals, open debt age,
projection failures, anchor failures, restoration failures, and provider
dispositions. Local use favors a human-readable diagnostics command over a
remote dashboard or alerting service.

#### Section 9 - Deployment and rollout review

The first artifact is repository-local and opt-in. It never migrates or writes
a manuscript without export, expected hashes, a local authorization, and a
verified rollback path. Schema migration ships before code that requires it;
old readers fail loudly on unsupported versions. AI and automatic patch apply
are independently disableable. Public installation, background daemons, and
auto-update are deferred until live validation and fresh-install measurement.

#### Section 10 - Long-term trajectory review

Reversibility is 4/5 if canonical serialization, export/import, append-only
history, provider ports, and derived projections remain explicit. The largest
path dependency is inventing a semantic VCS before branching proves useful;
keeping ADR 0002 proposed and limiting F0 to one selected merge preserves an
exit. The next platform capabilities should be adapters over the contract, not
new authority paths.

#### Section 11 - Design and UX review

The experience starts with the research situation, not a graph canvas. A
command opens one local `Episode Review` decision sheet; accepted, edited,
deferred, or rejected outcomes return the researcher to work. Deferred
high-impact items appear in a small `Review pending` list/session recap.
Internal `understanding_debt` is presented as `Review pending`, without scores
or shame.

```text
unexpected result -> Episode Review -> optional AI suggestion (not accepted)
                                  | inspect/edit/reason -> scoped authorization
                                  | Not now -> pending proposal, no mutation
                                  | authorize + defer explanation -> Review pending debt
                                  | reject -> auditable close
                                  ` provider unavailable -> manual AI-off flow
```

Loading, empty, error, stale, success, partial, offline, privacy-consent,
compile, restore, and recovery states are required. Keyboard operation,
screen-reader labels, visible focus, reduced motion, and measured contrast are
part of the minimum surface. The complete hierarchy, state-rescue matrix, and
responsive acceptance are fixed in Phase 2 below.

#### Failure Modes Registry

| Codepath | Failure mode | Rescued? | Test? | User sees? | Logged? |
|---|---|---:|---:|---:|---:|
| model-facing port | attempts accepted mutation | yes | yes | explicit denial | yes |
| authorization | stale or replayed capability | yes | yes | re-review required | yes |
| durable commit | crash before/after commit | yes | yes | recovered prior result/state | yes |
| selected merge | missing dependency | yes | yes | omitted/blocked item list | yes |
| replay | rule/schema drift | yes | yes | incompatible version, no silent rewrite | yes |
| projection | rebuild fails | yes | yes | degraded but usable last projection | yes |
| provider | timeout/refusal/malformed output | yes | yes | provider-specific failure, manual path | yes |
| trace retention | raw payload expired | yes | yes | unavailable marker | yes |
| anchor | marker duplicate/split/rewritten | yes | yes | relink/manual apply | yes |
| patch saga | file changes during apply | yes | yes | stale-file conflict | yes |
| compiler | failure/timeout | yes | yes | diagnostics and open debt | yes |
| recovery | snapshot/bytes inconsistent | partial | yes | recovery-required hard stop | yes |
| privacy deletion | shared blob still referenced | yes | yes | retained-reference report | yes |
| import | path escape/symlink | yes | yes | rejected unsafe path | yes |

The one intentionally hard-stop state is `recovery_required`: the system must
not guess which manuscript bytes are authoritative.

#### CEO implementation tasks

- [ ] **CEO-01 (P1, human: 1-2 days / CC: 1-2 hours) - Product/docs** -
  Reconcile product promise, release gates, domain model, validation case, ADRs,
  and this ExecPlan.
- [ ] **CEO-02 (P1, human: 2-4 hours / CC: 20-40 min) - Validation** -
  Assemble the redacted truth packet and Markdown/checklist baseline.
- [ ] **CEO-03 (P1, human: 2-3 days / CC: 2-4 hours) - Contract** -
  Specify F0 inventory, state tables, typed closure, temporal views,
  authorization, replay, privacy, and invalid cases.
- [ ] **CEO-04 (P2, human: 2-4 days / CC: 3-6 hours) - Spikes** -
  Run the SQLite operation-log and LaTeX anchor/recovery spikes.
- [ ] **CEO-05 (P1, human: 1 day / CC: 1-2 hours) - Security** -
  Prove the model/agent process cannot raw-write durable accepted state.
- [ ] **CEO-06 (P2, human: 3-5 days / CC: 4-8 hours) - Validation** -
  Encode the headless happy, forbidden, crash, replay, and recovery fixtures.

#### CEO completion summary

| Review item | Result |
|---|---|
| mode | SELECTIVE EXPANSION; Approach B already user-approved |
| Step 0 | 7 premises evaluated; 8 scope candidates decided |
| architecture | 4 former project tracks separated; 3-plane/port boundary defined |
| errors | 14 typed paths mapped; no silent-rescue policy |
| security | 9 threats mapped; raw-write isolation is the critical gate |
| data/UX | 14 edge-case families made explicit |
| quality | 4 over-engineering constraints added; no code exists yet |
| tests | unit/integration/system/E2E/property/crash layers defined |
| performance | 5 design budgets; unrelated serving scale removed |
| observability | operation/attempt diagnostics and privacy-safe export required |
| rollout | repository-local opt-in; v1/public/daemon deferred |
| future | reversibility 4/5; semantic-VCS path dependency bounded |
| design | focused card + calm deferred Inbox; full review follows |
| outside voices | 5/6 dimensions confirmed; 1 graph-first sequencing taste decision |
| NOT in scope | 8 families written |
| failure modes | 14 mapped; `recovery_required` is the only intentional hard stop |
| unresolved CEO decisions | 0 blockers; 1 taste decision retained for the final autoplan gate |

**Phase 1 complete.** Codex raised 12 concerns; the independent subagent raised
9 material issues. Five of six consensus dimensions were fully confirmed; the
graph-first sequence remains a taste decision, bounded by the user's approved
Approach B and a mandatory simple baseline. Independent specification review
moved from 5/10 to 7/10 to 9/10 and closed all 17 findings. The last three
mechanical corrections -- finite V0 bounds, a zero-start outcome rule, and
explicit Boolean grouping for the serving trigger -- landed after the
iteration cap and are mandatory Engineering revalidation targets. Phase 2 may
proceed.

### Phase 2 - Design review

#### System audit and Step 0

UI scope exists because H1 adds a local review workspace, provider consent,
human authorization, manuscript progress, error rescue, and deferred review.
The repository has no implemented UI, `DESIGN.md`, component library, earlier
design-review cycle, or `TODOS.md`; the only reusable visual input is the
fixture's semantic merge checklist and the product's established language.
The gstack designer binary is unavailable, so this review uses annotated text
wireframes and requires visual exploration before H1 implementation.

Initial design completeness was **5/10**. The plan already protected human
authority and named important states, but it specified domain records more
precisely than the researcher's decision flow. A 10/10 H1 plan needs one
unambiguous entry surface, ordered scientific information, complete visible
states and rescues, action-specific authorization, a non-shaming debt flow,
and testable responsive/accessibility behavior.

#### Design dual voices

`CLAUDE SUBAGENT (design - independent review)` found 16 issues: six critical,
nine high, and one medium. It identified review-card hierarchy, mutation-target
legibility, manuscript consequences, authorization scope, patch/compile
progress, and remote privacy consent as the most dangerous ambiguities.

`CODEX SAYS (design - UX challenge)` found 12 issues: four critical, seven
high, and one medium. It independently found conflicting canonical navigation,
an undefined CLI/UI boundary, a record-shaped review card, ambiguous deferral,
an unsafe global `committed` state, missing privacy UX, and non-testable
responsive/accessibility language.

| Design dimension | Independent | Codex | Consensus |
|---|---:|---:|---|
| researcher-centered hierarchy | 3/10 | 4/10 | CONFIRMED |
| end-to-end interaction specificity | 3/10 | 3/10 | CONFIRMED |
| state and recovery coverage | 4/10 | 4/10 | CONFIRMED |
| emotional journey and interruption recovery | 4/10 | 3/10 | CONFIRMED |
| human authorization legibility | 6/10 | 6/10 | CONFIRMED |
| privacy and manuscript consequence | 4/10 | 4/10 | CONFIRMED |
| responsive/accessibility readiness | 4/10 | 2/10 | CONFIRMED |

All seven dimensions agree on the direction. The fixes refine the already
approved H1 rather than add a dashboard, chat product, or graph canvas, so they
are accepted automatically under safety, completeness, and scope-discipline
principles. The visual character remains one taste decision for the final
autoplan gate.

#### Pass 1 - Information architecture

**Rating: 3/10 -> 9/10.** The prior phrase “review card” named fields without
stating what the researcher should understand first. H1 is now a single
command-launched `Episode Review` workspace whose primary object is the
research episode, not a Proposal, ReviewBundle, branch graph, or Inbox row.

`python -m claimbranch review open <episode-id>` opens the local workspace. The
first three visible facts are: what happened and why it matters; what change is
suggested and that it is not accepted; and exactly which research and
manuscript targets would change. Provenance internals, hashes, receipts, and
trace manifests remain available under `Audit details`, never ahead of the
scientific decision.

```text
+ ClaimBranch / project / episode ------------------ AI: local | Pending: 2 +
|                                                                     |
|  1. Situation                                                       |
|     Unexpected result / accepted evidence / claim at risk           |
|     Target: branch X -> main; manuscript anchor Y                    |
|                                                                     |
|  2. AI suggestion                                      NOT ACCEPTED |
|     Scientific before -> after / human edits / evidence basis       |
|                                                                     |
|  3. What will change                                                |
|     Selected changes / required dependencies / left unchanged       |
|     Exact manuscript source diff and current compile status         |
|                                                                     |
|  4. Your decision                                                   |
|     Rationale / 1-3 contextual prompts or explicit deferral         |
|                                                                     |
|  [Not now]                  [Authorize N named changes]              |
|                                                                     |
|  Audit details (collapsed): contribution chain / digests / trace    |
+---------------------------------------------------------------------+
```

The `Review pending` list is a secondary destination in the context strip, not
the home screen or a permanent sidebar. Each row shows the episode, affected
claim or manuscript location, whether nothing was accepted or debt is open,
age in neutral language, and `Resume review`. Returning from a receipt or a
pending item restores the exact episode and reviewed-versus-current context.

#### Pass 2 - Interaction state coverage

**Rating: 3/10 -> 9/10.** A single `committed` state was unsafe because graph
acceptance, file application, compile verification, and debt closure are a
saga rather than one transaction. The four-dimensional closed state model
above makes partial success explicit and keeps provider and projection health
from impersonating accepted research state.

| Feature | Loading | Empty | Error | Success | Partial / stale |
|---|---|---|---|---|---|
| episode context | skeleton preserves project/episode identity and says what is being loaded | “No reviewable episode” plus `Return to manual work` | names unreadable input and confirms accepted state is unchanged | Situation and exact target are visible | projection degradation uses last valid context with a dated warning |
| AI suggestion | progress names provider and offers `Cancel`; leaving the page is safe | “No suggestion requested” plus `Request AI suggestion` and manual path | refusal, timeout, malformed output, or offline status names the failure and preserves the draft request | suggestion is labeled `Not accepted` | a late result is marked stale and must be diffed against current heads before review |
| remote outbound review | exact preview is assembled locally; nothing has left the machine | no remote provider configured offers local/manual alternatives | consent or transport failure leaves no accepted mutation | one-shot `Send this exact request` receipt shows destination and digest | any input edit invalidates consent and returns to preview |
| decision sheet | dependency and impact calculations show bounded progress | no selectable change explains why authorization is unavailable | typed message states what failed, what work is preserved, and the safe next action | action-specific receipt lists accepted graph changes | stale head/file preserves edits, shows reviewed-versus-current diff, disables authorization, and offers `Refresh and re-review` |
| manuscript saga | distinct `applying` and `compiling` status lines include cancel policy | no manuscript consequence says `No manuscript change in this operation` | diagnostics name the failing command; restoration status is separate | only `verified` says the exact source and output hashes passed | `applied_unverified`, `debt_open`, and `restored_after_failure` never use global success styling |
| Review pending | rows retain episode, consequence, and deferral kind while context loads | warm neutral message: “Nothing is waiting for your review” plus `Return to episode` | unreadable item stays visible with diagnostic ID and export action | closure receipt says what human review closed | accepted-with-debt and unaccepted-pending rows use different labels and actions |
| recovery | completed recovery steps remain visible | not applicable | dominant `recovery_required` view names the at-risk file and only permits inspect/export/restore | verified restore returns to the prior manuscript phase | missing or divergent snapshot never guesses or enables new mutation |

`Not now` means no accepted mutation and creates `pending_unaccepted`.
`Authorize now; review explanation later` is a separate high-friction choice
that may commit only while opening visible UnderstandingDebt. Cancellation and
late provider results remain non-authoritative; a background result never
opens an authorization prompt or changes accepted state by itself.

Every typed error presentation has five fixed parts: plain-language title,
what remained unchanged, preserved work, recommended recovery, and a copyable
diagnostic ID behind disclosure. `recovery_required` uses a blocking landmark
and no unrelated navigation. Success is always an operation-specific receipt,
never a project-wide green state.

#### Pass 3 - User journey and emotional arc

**Rating: 4/10 -> 9/10.** The user begins with uncertainty because an
unexpected result may challenge their paper, so the product must orient before
asking for provenance or understanding work. Progressive disclosure follows
the emotional sequence `orient me -> show what matters -> let me inspect ->
record my judgment -> reassure me -> return me to the paper`.

| Step | User does | Intended feeling | Plan support |
|---|---|---|---|
| 1 | opens the episode from a command | oriented, not trapped in a new tool | project, episode, evidence status, target branch/main, and AI status stay visible |
| 2 | reads the surprising result and claim at risk | scientifically grounded | Situation leads with accepted evidence and why the claim is affected |
| 3 | continues manually or requests AI help | in control of assistance | manual path is primary-safe; AI action is explicit and proposal-only |
| 4 | reviews remote data if applicable | informed about privacy | destination, exact bytes, redactions, retention, and alternatives precede one-shot consent |
| 5 | compares suggestion, human edits, dependencies, and omissions | able to disagree | before/after and selected/required/deferred groups are visually distinct |
| 6 | writes rationale and answers or defers contextual prompts | reflective, not examined | no score, AI grading, celebration, or shame; prompt explains why it was asked |
| 7 | performs an action-specific authorization | certain about scope | button names the count/effect; sealed diff and target remain adjacent |
| 8 | watches manuscript verification and receives a receipt | reassured without false success | graph acceptance, patch, compile, restore, and open debt remain separate |
| 9 | returns to research or resumes a pending review | continuity | exact context is resumable; correction appends history rather than pretending undo |

At five seconds, the researcher can identify the episode, risk, AI/accepted
boundary, and next action. At five minutes, they can complete the decision
without reading raw records or keeping an external checklist. At five years,
the receipt and audit details answer who contributed what, what was authorized,
which manuscript bytes were verified, and which human review remained open.

Interruption is treated as normal, not failure. Draft rationale and teach-back
answers are preserved locally but an old seal or capability is not. On resume,
the UI says whether the operation is unaccepted, accepted with review pending,
or accepted with manuscript verification still pending.

#### Pass 4 - AI slop risk and intentional visual language

**Rating: 5/10 -> 9/10.** This is task-focused app UI, not a landing page or a
generic SaaS dashboard. Its visual anchor is the scientific before/after and
manuscript consequence, not a hero, graph animation, chat transcript, metric
grid, or collection of rounded cards.

| Litmus check | Result | Constraint |
|---|---|---|
| product unmistakable in first screen | YES | ClaimBranch, project, episode, and human/AI boundary occupy the context strip |
| one strong visual anchor | YES | the scientific before/after and exact source diff share the central reading column |
| understandable by scanning headings | YES | Situation, AI suggestion, What will change, Your decision, Manuscript status |
| each section has one job | YES | orientation, comparison, consequence, judgment, or outcome; no mixed dashboard tiles |
| cards necessary | YES, one only | the decision sheet is the interaction; nested and decorative cards are forbidden |
| motion improves hierarchy | LIMITED | only progress, disclosure, and focus transitions; reduced motion removes them |
| premium without shadows | YES | typography, rules, spacing, and content contrast carry hierarchy; shadows and gradients are unnecessary |

User-facing language uses `Evidence`, `AI suggestion`, `Your edits`, `What
will change`, `Left unchanged`, `Your decision`, `Manuscript status`, `Review
pending`, and `Audit details`. It does not expose `ReviewBundle`, `Ref`,
`AuthorizationReceipt`, `watermark`, or state-enum names outside audit or
diagnostics. Primary actions name consequences: `Record interpretation`,
`Authorize 4 selected changes`, `Apply this manuscript patch`, and `Close
manuscript review`; a generic `Accept` is forbidden.

No violet gradient, decorative blob, emoji, icon-in-circle feature, centered
composition, three-column card grid, thick chrome, ornamental graph, or bubbly
radius is admitted. Status always uses text plus shape/icon, never color alone.
Copy is concise utility language and never praises the user for authorizing a
scientific claim.

#### Pass 5 - Design-system alignment

**Rating: 2/10 -> 8/10.** No repository design system exists, so these are
provisional H1 tokens rather than a project-wide brand claim. A dedicated
design consultation and annotated visual variants must validate them before UI
implementation; the graph contract and H0 work do not wait on that exercise.

| Element | Provisional contract |
|---|---|
| character | quiet editorial lab notebook: serious, local, legible, and visibly human-owned |
| typography | Source Serif 4 for scientific prose and IBM Plex Sans for navigation, status, forms, and actions; native monospace only inside source/digest blocks |
| surfaces | `paper #F5F2E9`, `ink #202622`, `muted-ink #525B55`, `rule #B9B4A8`; freeze only after automated contrast verification |
| semantic color | `action #005A4E`, `proposal #7A4E00`, `danger #8B1E2D`, `focus #006C9B`; pair every color with words and an icon/shape |
| spacing | 4/8/12/20/32 px scale, 960 px reading measure, section rules rather than nested containers |
| shape/depth | 2-4 px radius only where an interactive boundary needs it; no decorative shadow or gradient |
| motion | 120-160 ms for disclosure/progress/focus continuity; no decorative motion; instant under reduced-motion preference |

The component vocabulary is intentionally small: context strip, section
heading, status line, scientific diff, source diff, dependency checklist,
provenance disclosure, rationale field, contextual prompt, scoped action row,
operation receipt, pending-review row, and rescue banner. One component owns
one semantic job. A later `DESIGN.md` may tune tokens but may not collapse the
proposal/accepted boundary or the separate manuscript phases.

The recommended quiet editorial direction is a **TASTE DECISION** because a
more austere command-console treatment could also satisfy the interaction
contract. The recommendation favors long scientific reading and makes the
researcher's prose louder than system chrome. Final autoplan approval chooses
or rejects that visual character without reopening H1 scope.

#### Pass 6 - Responsive behavior and accessibility

**Rating: 2/10 -> 9/10.** H1 is desktop-first but must reflow for split-screen
research and zoom; “mobile is out of scope” is not permission for horizontal
page scrolling. Test at 1440x900, 1024x768, and a 640 CSS-pixel-wide 200%-zoom
view, plus WCAG reflow at 320 CSS pixels.

The decision sheet is single-column at every width. Above 900 CSS pixels,
scientific and manuscript diffs may use aligned before/after panes; below that
they switch to a unified diff. The page never scrolls horizontally; only exact
source or digest blocks may scroll inside a labeled region. The context strip
wraps into two rows, the action row stacks with the safest action first in
reading order, and `Audit details` stays after the decision rather than moving
ahead of it.

H1 targets WCAG 2.2 AA: at least 4.5:1 normal-text contrast, 3:1 component and
focus contrast, 44x44 CSS-pixel pointer targets, visible persistent labels, no
color-only meaning, semantic headings/landmarks, and a logical keyboard order.
No action is a default form submit; Enter outside the focused authorization
button cannot authorize, while a focused native button remains operable by
Enter or Space. Focus moves to the first error, stale-review banner,
operation receipt, or recovery heading after the corresponding transition and
returns predictably when disclosures close.

Provider and compile progress use a polite live region; recovery and potential
data-loss messages use an assertive region once, without repeated announcements.
Reduced motion disables transitions, and all information survives 200% zoom.
Acceptance includes automated accessibility checks, keyboard-only completion
of the full wedge, and one NVDA walkthrough on the target Windows machine.

#### Pass 7 - Resolved and deferred design decisions

The review closes decisions that would otherwise create different products.
They are fixture-bounded and do not establish a general application shell.
Anything outside this table remains deferred unless another canonical contract
requires it.

| Decision | Resolution | If it had remained ambiguous |
|---|---|---|
| H1 entry | command-launched local `Episode Review`; no chat home | implementers would split the wedge across CLI, Inbox, and chat |
| primary object | research episode and consequence, not Proposal or graph | the domain model would lead the human decision |
| first three facts | situation, not-accepted suggestion, exact targets/consequences | audit metadata would hide scientific meaning |
| authorization | action label names exact effect/count and sits beside the sealed diff | generic acceptance could authorize an unintended scope |
| deferral | `Not now` is unaccepted; `Authorize now; review explanation later` opens debt | one Inbox state would conceal whether accepted state changed |
| success | operation receipt plus separate manuscript phase; no global `committed` | graph acceptance could masquerade as compile verification |
| remote request | dedicated digest-bound outbound preview and one-shot consent | architecture-level privacy would have no usable control |
| pending review | small secondary list with neutral age and exact resume context | Inbox could become a guilt dashboard or a second home |
| internal language | jargon lives under `Audit details` | researchers would have to understand storage and receipt names |
| responsive model | desktop-first single column with unified-diff reflow | split-screen and zoom would break the central workflow |

Impact is deterministic and can be escalated by a human but never downgraded:

| Impact | Closed F0 meaning | Review burden |
|---|---|---|
| non-authoritative | capture, request, cancellation, rejection, or proposal revision that changes no accepted state | quiet provenance and no authorization |
| medium | branch-local follow-up plan with no central-claim, accepted-evidence, selected-merge, manuscript, or debt consequence | explicit scoped authorization and one-line rationale; show AI contribution |
| high | evidence confirmation/correction/invalidation; central Claim or relationship change; selected merge; manuscript prepare/apply; or debt closure | action-specific authorization; if AI-influenced, 1-3 contextual prompts or debt-opening deferral |

One visual-character choice remains for the final gate: the recommended quiet
editorial lab notebook versus a stricter command-console treatment. The former
is recorded as the default recommendation because it supports long-form
scientific comparison without making AI or graph machinery the visual hero.

#### What already exists

- Product language already distinguishes accepted evidence, proposals,
  contribution chains, human rationale, and review debt.
- The saturation fixture already supplies the selected/required/deferred merge
  checklist and exact manuscript consequence used by the decision sheet.
- Typed domain errors, closed operation states, and recovery rules already
  supply the inputs to visible rescue copy.
- No UI code, component library, `DESIGN.md`, mockup, or prior design-review
  artifact exists in the repository; nothing visual can be claimed as reused.

#### Design work not in scope

- conversational chat home, command palette, graph canvas, dashboards, and
  multi-pane research IDE;
- native mobile/tablet applications, collaboration, notifications, and SaaS
  account or tenancy surfaces;
- decorative graph animation, gamification, scores, streaks, or automated
  celebration of scientific acceptance;
- provider installation, model management, routing, benchmarking, or a
  serving-operations console; and
- public marketing/brand pages or a project-wide design system before H0 and
  the H1 design consultation gate.

There is no separate `TODOS.md` update. Every actionable design gap is either a
blocking H1 task below or an explicitly gated post-V0 non-goal, so creating a
second debt list would duplicate the active ExecPlan.

#### Design implementation tasks

- [ ] **DESIGN-01 (P1, human: 1 day / CC: 1-2 hours) - Canonical UX** -
  Reconcile the Episode Review hierarchy, language, deferral meanings, impact
  tiers, and separate manuscript phases across product, release, validation,
  domain-design, and architecture documents.
- [ ] **DESIGN-02 (P1, human: 1-2 days / CC: 2-4 hours) - Interaction contract** -
  Specify annotated proposal-ready, stale-review, outbound-review,
  patch/compile, receipt, pending, and recovery wireframes plus the complete
  state/rescue matrix before selecting a frontend stack.
- [ ] **DESIGN-03 (P1, human: 2-3 days / CC: 4-8 hours) - H1 shell** -
  Build the command-launched local Episode Review and secondary Review pending
  list only after H0 passes.
- [ ] **DESIGN-04 (P1, human: 1-2 days / CC: 2-4 hours) - Authority UX** -
  Implement sealed-diff-adjacent, action-specific authorization, distinct
  deferrals, stale invalidation, and operation receipts.
- [ ] **DESIGN-05 (P1, human: 1-2 days / CC: 2-4 hours) - Privacy UX** -
  Implement exact outbound preview, redaction/retention explanation,
  one-request consent, cancellation, and local/manual alternatives.
- [ ] **DESIGN-06 (P1, human: 2-3 days / CC: 4-8 hours) - Manuscript UX** -
  Implement patch, compile, restore, debt, and recovery-required phases without
  a false global success state.
- [ ] **DESIGN-07 (P2, human: 1-2 days / CC: 2-4 hours) - Design/a11y gate** -
  Run design consultation, freeze tokens and annotated mockups, and encode
  viewport, contrast, keyboard, live-region, reduced-motion, and NVDA checks.
- [ ] **DESIGN-08 (P1, human: 1 day setup plus walkthrough / CC: 1-2 hours) - UX validation** -
  Require one unfamiliar researcher to identify evidence, AI contribution,
  exact authorized changes, dependencies, deferred items, outbound data, and
  manuscript verification state before authorization.

#### Design completion summary

| Review item | Result |
|---|---|
| system audit | UI scope confirmed; no implementation, design system, or mockup exists |
| Step 0 | 5/10; authority intent strong, human interaction underspecified |
| Pass 1 - information architecture | 3/10 -> 9/10 |
| Pass 2 - interaction states | 3/10 -> 9/10 |
| Pass 3 - journey | 4/10 -> 9/10 |
| Pass 4 - AI slop | 5/10 -> 9/10 |
| Pass 5 - design system | 2/10 -> 8/10; visual consultation remains an H1 entry task |
| Pass 6 - responsive/accessibility | 2/10 -> 9/10 |
| Pass 7 - decisions | 10 resolved; 1 taste decision retained for final gate |
| dual voices | 7/7 dimensions confirmed; no scope disagreement |
| NOT in scope | 5 design families written |
| What already exists | written; no visual implementation truth claimed |
| `TODOS.md` | 0 items; no duplicate debt list created |
| mockups | 0 generated because designer is unavailable; visual gate is explicit |
| overall design score | 5/10 -> 9/10 |

**Phase 2 complete.** Codex raised 12 concerns and the independent subagent
raised 16 issues. Seven of seven dimensions converged. All structural issues
are fixed in the plan; the quiet editorial visual character remains a taste
decision for the final gate. Phase 3 may proceed after Engineering revalidates
the finite UI-state product and the separate graph/manuscript transitions.

### Phase 3 - Engineering review

#### Step 0 - Scope and implementation reality

No application code, runtime manifest, test framework, or settled stack exists;
only canonical documents, the documentation checker, the saturation case, and
the docs-only CI workflow are reusable implementation assets. The plan touches
more than eight future files and names more than two responsibility boundaries,
so the normal complexity smell fires. The response is not to remove required
authority, recovery, or test boundaries: keep one trusted local application
process plus one minimal OS-backed authorization helper, build in strict phases,
and treat every named “module” as a logical seam rather than a deployable
service.

Python, pytest, SQLite, and a loopback browser are spike/default hypotheses,
not implemented truth. P1 must record a toolchain/storage implementation ADR
after the bounded spikes; planned commands become executable oracles only then.
Public packaging is intentionally absent until V0, while native Windows is the
only claimed F0 target because the authorization and file-durability gates are
platform-specific.

The engineering search check used primary platform sources. Microsoft documents
AppContainer as a file, network, process, credential, and IPC isolation boundary;
MDN documents secure localhost contexts plus the need for cookie, Origin, CSRF,
and frame defenses; SQLite documents journal/WAL durability assumptions; and
Microsoft documents replace/flush failure modes. These are feasibility inputs
for spikes, not evidence that ClaimBranch has implemented any guarantee.

#### Engineering dual voices

`CLAUDE SUBAGENT (engineering - independent review)` found 14 issues: four
critical, eight high, and two medium. Its critical findings were missing episode
partitioning, read/export exfiltration, an incomplete foreground-gesture broker
protocol, and a non-crash-safe patch/compile saga. It also found incomplete
resource bounds, eligibility/outcome ambiguity, proposal-ingress confusion,
debt-closure binding gaps, impossible UI-state tuples, manuscript concurrency,
load-test ambiguity, and import trust.

`CODEX SAYS (engineering - architecture challenge)` timed out after the
12-minute outer limit and is tagged `[codex-unavailable]`. Per the autoplan
degradation rule it was not retried. A missing voice is not agreement; every
critical independent finding was therefore verified against exact current plan
clauses and corrected by the primary review.

| Engineering dimension | Independent | Codex | Dual-voice consensus |
|---|---:|---:|---|
| architecture sound | 6/10 | N/A | NOT CONFIRMED |
| test coverage sufficient | 5/10 | N/A | NOT CONFIRMED |
| performance risks addressed | 5/10 | N/A | NOT CONFIRMED |
| security threats covered | 4/10 | N/A | NOT CONFIRMED |
| error/recovery paths handled | 4/10 | N/A | NOT CONFIRMED |
| deployment risk manageable | 5/10 | N/A | NOT CONFIRMED |

This phase is `[single-model]` for outside-voice consensus, with no taste
disagreement to surface. The primary engineering review re-rates the amended
plan below but does not mislabel that work as cross-model confirmation.

#### Post-cap contract revalidation

| Required revalidation | Engineering disposition after fixes |
|---|---|
| finite F0/V0 bounds | PASS at plan level: ResearchEpisode partitions deltas; every record family plus payload, retry, attempt, blob, and project resource has a numeric maximum and typed overflow |
| zero-valid-start outcome | PASS: global catastrophic breach remains NOT_VALIDATED; otherwise zero starts is INCONCLUSIVE; checker truth-table cases are named |
| serving Boolean and population | PASS: `30 cases AND (20-case privacy denominator OR frozen all-terminal wait p95)` is executable and missing data fails closed |
| sealed ReviewBundle and foreground authority | PASS at contract level: exact review digest plus Host/Origin/CSRF/frame/session/IPC/OS-presence protocol; implementation proof remains an H0 gate |
| human manuscript-debt closure | PASS at contract level: debt/patch/source/output/compiler/head/saga tuple is sealed; model, stale, forged, restored, cross-project, double, and replay denials are named |
| encrypted patch recovery | PASS at contract level: AEAD write-ahead metadata, flush ordering, fencing, isolated compile, exhaustive reconciliation, key-loss hard stop, and cleanup are explicit |
| four-dimensional UI state product | PASS at contract level: dimensions are derived, duplicate recovery state is removed, legal transition tables and reachable-tuple generation replace the raw Cartesian product |

“PASS at contract level” means implementation may begin after P1 fixtures prove
the clause; it does not claim the guarantee exists today.

#### Section 1 - Architecture review

**Rating: 6/10 -> 9/10.** The architecture keeps all authoritative work inside
one trusted local process and uses ports for testability, not microservices.
The OS-backed helper is the only additional trusted process because keeping its
key and user-presence operation outside browser/model context is the safety
claim. Provider/model processes remain external and untrusted.

```text
UNTRUSTED / RESTRICTED                         TRUSTED LOCAL BOUNDARY

browser UI -- session/CSRF -----------------> HTTP/review adapter
                                                    |
model/agent -- bounded Proposal IPC ----------> proposal ingress gateway
                                                    |       |
local/hosted provider <--- consented bytes --- context compiler  proposal ledger
       ^                                            |          (non-authoritative)
       |                                            v
       +---- provider gateway <--------------- command gateway
                                                    |
                                                    v
                                             deterministic domain core
                                               |        |        |
                                               v        v        v
                                         canonical   projection  trace/blob
                                         operation   builder     ledger
                                         store       (derived)   (encrypted)
                                               |
                                               +--> manuscript saga --> isolated compiler
                                               |
                                               `--> receipt verify/consume
                                                          ^
                                                          |
OS user presence --> authorization helper -- private ACL IPC
                     (non-exportable key; receipt goes to kernel, not JS)
```

The command gateway assigns project, episode, actor class, and operation type;
no untrusted caller chooses accepted-table writes. The proposal ledger is
durable but non-authoritative and separately permissioned. Context queries are
field/sensitivity/byte scoped; human export is a different capability; every
network egress reaches the provider gateway only after its exact policy and
digest gate.

The manuscript adapter is a fenced saga because the graph database and LaTeX
file cannot be one transaction. A single active writer per project/file/anchor,
pre/post digests, write-ahead metadata, exact replace/flush order, isolated
compile, and state rechecks prevent a restore from overwriting a newer editor
change. Startup either proves a next step from durable state or enters the one
hard stop.

Import/replay has no live-project merge path in F0. Verify-only untrusted
history and trusted restore both target a new empty store; only a signed chain,
enrolled public-key lineage, known schema/rules, and valid receipts produce a
trusted restored view. Future foreign-history promotion needs a new authority
contract and is not smuggled through `import`.

#### Section 2 - Code-quality review

**Rating: 6/10 -> 9/10.** There is no code to inspect for duplication or naming
defects. The plan prevents the likely ones by making schemas, operation enums,
typed errors, transitions, and UI reachability generated from one versioned
contract source; adapters consume generated types rather than restating status
strings by hand.

| Logical module | One responsibility | Must not absorb |
|---|---|---|
| `domain` | pure records, invariants, closure, transitions, canonical hashing | storage, browser, provider, filesystem, clock/entropy globals |
| `gateway` | capability checks, resource limits, idempotency, command dispatch | business-state mutation outside domain handlers |
| `canonical_store` | atomic operation/receipt consumption and trusted replay | proposal/provider writes or projections |
| `proposals` | bounded non-authoritative ingress and contribution references | materialization or human authorization |
| `projection` | rebuildable current/historical/context views | source-of-truth status or silent fallback writes |
| `authorization` | sealed digest verification, OS presence, receipt issue/consume protocol | browser-owned key or caller-provided human flag |
| `context_provider` | scoped context, consent broker, provider envelope/trace | accepted-state commands or general export |
| `manuscript` | anchor, fenced patch journal, isolated compile, restore | semantic merge or graph transaction claims |
| `adapters` | CLI and local Episode Review translation | duplicate state machines or direct store access |
| `validation` | fixture runners, model/state generators, V0 checker, performance workloads | product mutations outside a new isolated destination |

Every error is a closed typed outcome with a safe payload; no `GraphManager`,
generic event-sourcing framework, plugin registry, arbitrary JSON extension
bag, catch-all rescue, or class that combines validate/authorize/write/project/
external-I/O is allowed. Deterministic time, entropy, signatures, compiler
fingerprints, and rule versions are injected ports. Logging and diagnostic
export use IDs/digests and redacted metadata, never sensitive payload bytes.

The implementation uses complete handlers for the finite command inventory
and exhaustive matches that fail on unknown values. Code generation outputs are
checked into or reproducibly generated by the selected toolchain and verified
against schemas in CI; hand-edited generated reference is forbidden. Inline
ASCII comments belong only beside the receipt transaction, reachable-state
generator, and patch journal reconciliation because their ordering is not
obvious from individual functions.

#### Section 3 - Test review

**Rating: 5/10 -> 9/10.** No test framework or application tests exist, so
current implementation coverage is 0%. The docs checker is the only passing
test today. The toolchain ADR must create the framework before P1/P2 commands
are treated as real; the target remains 100% branch coverage for deterministic
domain/gateway code plus explicit integration, security, crash, E2E, and eval
oracles where branch coverage cannot prove the claim.

```text
CONTRACT / CODE PATHS                              USER / EXTERNAL FLOWS

[PLANNED UNIT+PROPERTY] episode start/close         [PLANNED E2E] H0-manual full wedge
  |- eligibility independent of representability     |- no Proposal/trace/network/debt
  |- <=3 invalid replacements; product failure kept   `- own golden + rebuild + restore
  `- per-episode identity/resource bounds

[PLANNED UNIT+PROPERTY] schema/operation kernel     [PLANNED E2E] H0-recorded full wedge
  |- nil/empty/type/Unicode/max/overflow              |- frozen Proposal + trace + contributions
  |- every legal/illegal transition                    `- teach-back/debt open-close + own golden
  |- evidence watermark + temporal views
  `- merge dependency closure                       [PLANNED SECURITY] authority and egress
                                                       |- raw-write/store/key/IPC denied
[PLANNED INTEGRATION] proposal ingress                |- Host/Origin/CSRF/frame/bootstrap denied
  |- gateway assigns actor/episode/type                |- prompt-injected read/export denied
  |- schema/size/version fuzz                           `- exact outbound digest, redirect/DNS tests
  `- accepted manifest unchanged

[PLANNED MODEL TEST] reachable H1 tuples            [PLANNED E2E] Episode Review
  |- every legal event/tuple generated                 |- manual/provider/offline paths
  |- every impossible persisted tuple rejected         |- edit/seal/stale/two deferrals/receipt
  `- two tabs derive one state                          |- late result, two tabs, interruption/resume
                                                       `- keyboard/NVDA/reflow/error rescue
[PLANNED INTEGRATION+CRASH] receipt transaction
  |- exact digest/presence/expiry/single consume      [PLANNED CRASH E2E] manuscript saga
  `- stale/forged/cross-project/double-submit           |- every journal/replace/compile/restore cut
                                                       |- external edit + competing token/supersede
[PLANNED INTEGRATION+CRASH] manuscript saga             `- exact restore or recovery-only hard stop
  |- AEAD/key loss/disk full/divergent bytes
  |- compiler sandbox and side-effect allowlist       [PLANNED E2E] trusted/untrusted restore
  `- closure receipt exact tuple                        `- no import into existing live project

[PLANNED UNIT] V0 truth-table checker                [PLANNED EVAL] proposal boundary
  |- zero starts +/- every catastrophic breach         |- structured envelope and authority refusal
  |- out_of_f0, invalid cap, all four outcomes          |- prompt injection cannot emit accepted command
  `- serving denominator/missing/timeout rules          `- quality is observed, not an authority gate

[PLANNED PERF] seeded 1x/10x workloads              [PLANNED MANUAL] target Windows proofs
  `- cold/warm, 1 writer+4 readers, RSS/disk/WAL        `- AppContainer/ACL/presence/replace/flush/NVDA
```

Critical deterministic suites are `tests/contract`, `tests/domain`,
`tests/security`, `tests/f0`, `tests/h1`, `tests/v0`, and `tests/performance`.
Provider smoke never enters deterministic CI. Prompt/provider code adds a
frozen boundary eval for schema validity, unsupported canonical edges,
authority refusal, injection, and trace completeness; scientific usefulness is
recorded through human accept/edit/reject in V0 and only becomes a local-model
default gate after the 30-case corpus exists.

Every bug found after implementation gets a failing regression test before its
fix. Crash testing injects at each durable boundary, not just process start/end.
Property/model tests use fixed seeds plus persisted minimal counterexamples.
The QA matrix in this section is the portable plan evidence; local gstack test-
plan exports are review aids and not repository dependencies.

#### Section 4 - Performance review

**Rating: 5/10 -> 9/10.** The performance target is single-user local research,
not distributed scale. The seeded 1x/10x query mix, cold/warm runs, one writer
plus four readers, memory/database/WAL/temp ceilings, and exact target-machine
fingerprint now make the earlier latency numbers reproducible.

The storage spike must show query plans or equivalent evidence for project and
episode membership, operation order, Ref head, evidence watermark, edge
source/target/type, contribution target/sequence, Proposal digest, and anchor/
debt/saga lookup. A traversal may not issue one query per edge or load raw trace
payloads into context. Context compilation obeys record/count/byte limits and
reports truncation as an explicit trace decision.

Projection rebuild happens beside the last valid projection, is cancellable,
and swaps only after integrity and budget checks. WAL/checkpoint behavior,
reader/writer contention, disk-full behavior, and rebuild temporary space are
part of the workload. A failed budget triggers two measured query/index/
representation attempts before any graph-native spike; it never changes the
authority or semantic contract.

#### Engineering failure-mode registry

| Codepath | Realistic failure | Test | Handling and researcher-visible result |
|---|---|---:|---|
| episode ingress | schema cannot represent an eligible result | yes | record `out_of_f0`; valid start remains; no scope expansion |
| resource limits | malicious retry/blob exhausts storage | yes | bounded ledger/counter, `ResourceLimitError`, accepted state unchanged |
| model query | prompt injects artifact export into provider context | yes | field/sensitivity/byte denial; exact blocked-field explanation |
| proposal ingress | caller selects human actor or accepted operation type | yes | gateway overwrites/rejects caller fields; accepted hash unchanged |
| loopback UI | hostile page CSRF/clickjacks authorization | yes | Host/Origin/CSRF/frame/presence denial; review remains sealed/unspent |
| authorization IPC | model connects directly or replays receipt | yes | ACL and single-consumption denial; diagnostic attempt ID |
| canonical store | crash after commit before response | yes | idempotent prior result; RPO=0 after acknowledgment |
| projection | rebuild corrupts or exceeds budget | yes | keep last valid projection; visible degraded status |
| provider egress | redirect/DNS rebinding changes destination | yes | redirects off, pinned destination, consent invalid; manual path remains |
| manuscript saga | two writers or external edit race | yes | fencing/hash conflict; preserve newer bytes; stale or recovery-only view |
| patch journal | key loss, disk full, or crash at any cut | yes | exact proof-driven resume/restore or `recovery_required`; never infer success |
| compiler | writes outside isolated output or hangs | yes | sandbox/resource kill, discard outputs, restore/debt remains open |
| debt close | stale/forged/project-mismatched verified tuple | yes | closure denied and new review required |
| UI projection | impossible cross-dimension tuple loads | yes | render blocked with typed integrity error; no authorization control |
| import/replay | unknown signing lineage claims human authority | yes | untrusted isolated view only; no live merge/promotion |
| V0 checker | zero start or missing metric changes branch ordering | yes | frozen truth table assigns one deterministic outcome or fails protocol |

No remaining listed mode is silent, untested, and unhandled. Key loss,
divergent manuscript bytes, and canonical integrity failure intentionally stop
mutation because an automatic rescue would be less safe than an explicit hard
stop.

#### Deployment, rollout, and parallelization

The F0 artifact is repository-local, opt-in, and native Windows only. Existing
`.github/workflows/docs.yml` remains the docs gate; the toolchain ADR adds a
Windows CI job for schemas, deterministic unit/property/integration suites,
goldens, and non-platform-specific security tests. AppContainer/user-presence,
filesystem flush, actual LaTeX, and NVDA proofs also run on the named target
machine and produce signed/manual evidence because hosted CI cannot establish
those local guarantees.

No package manager, installer, auto-update, daemon, container, cross-platform
binary, or public release is promised before the P5 packaging trigger. H0 is
invoked from the checked-out repository with pinned dependencies and a lockfile;
the fresh-install measurement later decides whether distribution work is
justified. Schema migration always precedes readers that require it and old
readers fail visibly on a newer schema.

| Workstream | May start | Depends on | Merge point |
|---|---|---|---|
| canonical schemas, episode/bounds, transition generators | after P0 | truth packet and ADR inputs | P1 contract fixtures |
| authorization/AppContainer/broker spike | after sealed ReviewBundle schema | target Windows access | P1 authority denial gate |
| storage/projection spike | after canonical serialization | seeded fixtures | storage ADR before P2 |
| anchor/patch/compiler-recovery spike | after PatchIntent/journal schema | redacted marked manuscript fixture | P1 recovery gate |
| headless domain/gateway/store kernel | after all P1 gates | prior four streams | H0 manual/recorded E2E |
| provider/context and Episode Review | after H0 | proposal/state contracts | H1 E2E/security/a11y |
| V0 checker and baseline artifacts | may prepare after P0; run only after H1 | frozen protocol and H1 gate | one V0 outcome |

Separate worktrees are useful for the three P1 spikes because their code does
not overlap after schemas freeze. H0 integration, H1, and V0 are sequential.
No parallel stream may invent a schema or authority rule independently.

#### What already exists

- canonical documentation governance, indexes, ADR history, and the passing
  `scripts/check_docs.py` plus docs-only CI;
- an approved office-hours design, rewritten active ExecPlan, saturation
  validation case, target architecture, and proposed domain model;
- accepted evidence/reasoning and AI-proposal constraints in ADRs 0001/0003;
  and
- no application code, package manifest, database, UI, test harness, provider
  adapter, compiler adapter, or deploy artifact to reuse or accidentally treat
  as truth.

#### Engineering work not in scope

- distributed services, queues, multi-writer collaboration, remote hosting, or
  multi-tenant authorization;
- generalized event sourcing, schema/plugin frameworks, graph databases,
  GraphRAG, embeddings, or arbitrary graph queries;
- provider/model installation, routing, automatic fallback, throughput serving
  operations, or local-model quality claims;
- package publication, installer, daemon, auto-update, public OpenClaw/MCP
  adapter, or non-Windows support; and
- arbitrary manuscript repositories, multi-file patch transactions, general
  LaTeX AST rewriting, or import/promotion into an existing live project.

Deferred expansion names, predicates, and evidence remain canonical in P5 of
this ExecPlan and the release scopes. Repository governance rejects unmanaged
root Markdown, so no duplicate `TODOS.md` is created.

#### Engineering implementation tasks

- [ ] **ENG-01 (P1, human: 1-2 days / CC: 2-4 hours) - Contract** -
  Add ResearchEpisode partitioning, numeric schemas/resource limits, exact V0
  truth table, and generated legal transition/reachability fixtures.
- [ ] **ENG-02 (P1, human: 2-3 days / CC: 4-8 hours) - Trust gateways** -
  Specify and spike the sole command writer, separated Proposal ingress,
  scoped model reads, human export, and one consented provider-egress path.
- [ ] **ENG-03 (P1, human: 2-4 days / CC: 4-8 hours) - Authorization** -
  Implement the target-Windows loopback/session/CSRF/frame/IPC/OS-presence
  denial spike and native-helper fallback.
- [ ] **ENG-04 (P1, human: 3-5 days / CC: 6-12 hours) - Manuscript saga** -
  Implement and crash-test fencing, AEAD journal, replace/flush, isolated
  compile, supersession, cleanup, restore, and recovery-only reconciliation.
- [ ] **ENG-05 (P1, human: 1-2 days / CC: 2-4 hours) - Debt/import authority** -
  Close the manuscript-debt receipt tuple and trusted/untrusted empty-store
  replay/restore key-lineage contract.
- [ ] **ENG-06 (P1, human: 1-2 days / CC: 2-4 hours) - Toolchain/CI** -
  Record the runtime/storage ADR after spikes, create the package/test harness
  and lockfile, and extend Windows CI without claiming cross-platform support.
- [ ] **ENG-07 (P1, human: 2-3 days / CC: 4-8 hours) - Complete tests** -
  Encode unit, property/model, integration, security, crash, E2E, boundary
  eval, and regression suites mapped above.
- [ ] **ENG-08 (P2, human: 1-2 days / CC: 2-4 hours) - Performance** -
  Generate seeded 1x/10x workloads and record query plans, latency, RSS,
  database/WAL/temp size, contention, and degraded-projection evidence.
- [ ] **ENG-09 (P1, human: 1 day / CC: 1-2 hours) - V0 checker** -
  Implement eligibility, invalid-replacement cap, zero-start/catastrophic
  ordering, out-of-F0, timing, and serving-trigger population truth tables.

#### Engineering completion summary

| Review item | Result |
|---|---|
| Step 0 | complexity smell accepted only with phased single-process architecture; no stack treated as settled |
| architecture | 6/10 -> 9/10 |
| code quality | 6/10 -> 9/10; no code exists, preventative module/type rules fixed |
| tests | 5/10 -> 9/10; 0 current implementation coverage, complete planned coverage map and artifact |
| performance | 5/10 -> 9/10; seeded workloads and resource ceilings fixed |
| security/authority | 4/10 -> 9/10; mutation, read, egress, browser, IPC, import, and file boundaries fixed at plan level |
| recovery | 4/10 -> 9/10; exhaustive fenced journal/compile/restore contract fixed |
| deployment | 5/10 -> 8/10; repo-local Windows is intentional, public distribution gated |
| dual voices | independent review completed; Codex timeout, 0/6 confirmed and 6 N/A |
| post-cap revalidation | 7/7 clauses pass at contract level; implementation proof remains gated |
| failure modes | 16 mapped; no silent untested gap remains in the plan |
| parallelization | 4 P1 streams after schema freeze; H0/H1/V0 sequential |
| `TODOS.md` | not created; repository governance keeps deferred work in canonical P5 |
| overall engineering readiness | 5/10 -> 9/10 for planning; repository remains unimplemented |

**Phase 3 complete in single-model degradation mode.** The independent
subagent raised 14 issues; Codex timed out and supplied no usable output, so no
dual-voice dimension is marked confirmed. The primary review verified and
closed all 14 plan defects, revalidated every post-cap clause, and wrote the
QA test plan. Phase 3.5 may proceed; H0 implementation still waits for P0/P1.

### Phase 3.5 - Developer-experience review

Mode: `DX POLISH`. Product type: local CLI tool with a command-launched browser
review companion. This is a plan-readiness score, not a claim that a lived
experience exists; the repository still has no application. No prior DX review
was found. The installed gstack package did not contain its optional
`dx-hall-of-fame.md`, so this pass used the skill's in-body criteria and current
primary documentation for OpenClaw, uv, and llama.cpp rather than inventing the
missing examples.

#### Step 0 - Developer evidence

##### Target developer persona

| Field | Contract |
|---|---|
| Who | a single empirical researcher-builder on native Windows, maintaining one Git-tracked LaTeX paper |
| Context | an unexpected result may change a claim and marked manuscript block; they want a local, inspectable workflow and optional AI help |
| Tolerance | under five minutes from a clean supported checkout to first meaningful output; one safe next action after failure |
| Expects | one PowerShell bootstrap, `doctor`, no administrator requirement, AI-off operation, relative paths, readable receipts, and no internal-store editing |
| Knows | Git clone, PowerShell command execution, relative paths, scientific interpretation, and their paper's compile command |
| Must not need to know | Python environment management, SQLite, ACLs, AppContainer, provider wire JSON, internal record names, or graph traversal syntax |

The secondary persona is an unfamiliar researcher who shares the scientific
context but has no ClaimBranch vocabulary. The implementation maintainer is a
separate persona; test harnesses and internal operations may serve that person
without becoming the researcher's public interface.

##### Developer perspective

> I open the current README and learn that ClaimBranch is a semantic
> version-control system, then immediately learn that no usable application
> exists. The documentation map can explain product and architecture ideas, but
> it has no installation or first-use path. If I tried to act on the active
> plan, I would encounter Python fixture commands even though Python, packaging,
> and the storage stack are still hypotheses. I would not know which Windows
> version, filesystem, browser, Git state, LaTeX distribution, or local-model
> setup is supported. I could read thousands of lines about receipts and crash
> recovery without finding the first command that proves the product is useful.
> My likely response is not distrust of the safety model; it is uncertainty
> about whether there is anything I can operate. The corrected path starts with
> a single standard-user bootstrap, a `doctor` report that separates core,
> manuscript, authorization, and optional-provider readiness, and an isolated
> saturation demo. The demo shows evidence challenging a claim and reaching a
> manuscript consequence while explicitly saying that AI is off and my files
> were untouched. Only then do I initialize a paper, capture an episode, or
> attach an already-running model endpoint. At every failure I see what changed,
> what did not, what was preserved, and one command to continue.

##### Competitive DX benchmark

No source supports a precise universal TTHW for uv or llama.cpp, so the table
records only observable onboarding shape except where a source publishes a
time. ClaimBranch chooses the competitive 2-5 minute tier rather than a hosted
playground because its safety promise is local and the reusable saturation
fixture makes a copy-paste demo cheaper and more representative.

| Tool | Published/observable first path | Notable choice | Applicability |
|---|---|---|---|
| OpenClaw | official guide targets a working chat in about five minutes | one installer plus guided onboarding verifies inference before optional setup | match its short path, not its requirement that AI be configured first |
| uv | Windows installer/package-manager choices lead directly to `uv init` and `uv run` hello world | isolated tool ownership, explicit install variants, immediate runnable output | copy the predictable bootstrap/next-step shape after the toolchain ADR |
| llama.cpp server | one Windows server command starts the default loopback endpoint; `/v1/models`, structured output, and timing fields are inspectable | replaceable OpenAI-compatible serving surface with observable timings | teach endpoint compatibility; do not absorb model/server management |
| ClaimBranch before review | unbounded; no app, bootstrap, doctor, or hello world | internal fixtures only | adoption blocker |
| ClaimBranch target | at most five minutes from declared clean checkout; at most 60 seconds after bootstrap | offline disposable demo, then optional project/provider paths | competitive tier with a safer first success |

Sources: [OpenClaw getting started](https://docs.openclaw.ai/getting-started),
[OpenClaw onboarding](https://docs.openclaw.ai/start/wizard),
[uv installation](https://docs.astral.sh/uv/getting-started/installation/),
[uv project guide](https://docs.astral.sh/uv/guides/projects/), and
[llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

##### Magical moment specification

The chosen vehicle is the lowest-effort copy-paste demo command, reusing the
already-required saturation packet and golden:

```powershell
claimbranch demo saturation --ai off --network deny
```

Within 60 seconds after bootstrap it creates a verified disposable root and
renders:

```text
Unexpected result mapped.

3 confirmed observations challenge 1 central claim.
1 marked manuscript block would require review.
AI: off.  Network: denied.
Your project and manuscript files were not changed.
Audit manifest: verified.

Next: claimbranch episode review --project <demo-path>
```

The walkthrough may display the frozen recorded AI suggestion only as
`Not accepted`, then show the difference between recording a proposal and a
human-authorized interpretation. It cannot require a browser, provider, model,
credential, LaTeX installation, real paper, or graph knowledge. Cleanup either
removes the verified disposable root or prints exactly where it was retained;
it never follows a link or enters a real project.

##### Nine-stage developer journey

| Stage | Researcher does | Previously observed friction | Resolution and gate |
|---:|---|---|---|
| 1. Discover | reads README `For you / Not for you`, status, support summary | semantic-VCS and research-agent identities conflicted | canonical promise plus explicit persona/exclusions in P0 |
| 2. Bootstrap | runs one repository-owned PowerShell command | no runnable environment or entry point | P1 toolchain ADR; standard-user pinned environment; no profile edit |
| 3. Diagnose | runs `claimbranch doctor` | Windows/paths/compiler/browser/presence assumptions were implicit | core, manuscript, authorization, and provider readiness reported separately |
| 4. Learn | runs the offline saturation demo | fixtures were test harnesses, not product learning | meaningful verified lineage in under five minutes with no real writes |
| 5. Initialize | previews and initializes one paper | no public path from a paper to a project | `project init --dry-run`; validated topology, Git, marker, compiler, egress |
| 6. Capture | generates a researcher-language episode template and starts it | raw schema/manual store editing was the implied path | template validation names fields and paths; accepted state remains unchanged on error |
| 7. Review | reviews manually, then optionally requests AI | provider setup and accepted/proposed boundary were obscure | manual path first; exact outbound preview; unaccepted Proposal; resumable debt |
| 8. Authorize/verify/recover | authorizes scoped graph/file steps and follows receipts | internal error classes had no executable rescue | separate phases, stable codes, one copy-paste next action, recovery-only surface |
| 9. Maintain | checks status, exports, migrates, and prepares feedback | upgrade could strand accepted research state | verified copy-on-write migration, retained original, local redacted bundle |

##### First-time developer confusion report

| Time | Pre-review experience | Resolution status |
|---|---|---|
| T+0:00 | README says semantic version control and no usable app; I cannot tell whether the new research-agent direction is canonical | P0 canonical reconciliation |
| T+0:30 | documentation map has no user or source-checkout quickstart | create the user path with H0, not before an executable exists |
| T+1:00 | active plan shows Python fixture commands while the stack is unsettled | distinguish validation harness, toolchain hypothesis, and stable public CLI |
| T+2:00 | no command says whether my Windows, paper path, browser, compiler, or security primitive is supported | `doctor` plus frozen support matrix |
| T+3:00 | I still have not seen evidence-to-manuscript value and would stop | three-step bootstrap/doctor/demo path |
| T+5:00 | provider and real-paper setup would expose many new choices at once | defer them until after the verified offline magical moment |

Every confusion point is addressed in P0-P3. The report is a prediction grounded
in current docs; `/devex-review` must replay and measure it after implementation.

#### DX dual voices

The independent subagent reported 25 issues: 4 critical, 17 high, and 4 medium;
its unweighted initial score was 2.3/10. The Codex voice completed all ten
requested dimensions and grouped the same omissions into ten critical concern
areas; its initial plan score was 3.3/10 and its proposed-contract score was
8.8/10. Neither voice requested model management, public packaging, a hosted
sandbox, or a broader product.

| Dimension | Independent voice | Codex voice | Consensus |
|---|---|---|---|
| persona/product identity | underspecified and conflicting | three personas conflated; README conflicts with plan | confirmed |
| clean checkout and hello world | no bootstrap; no hello world | TTHW undefined/effectively infinite | confirmed |
| real-paper onboarding | no init/template/anchor path | no safe first-project lifecycle | confirmed |
| CLI/help/automation | internal/test/user commands conflated | public grammar, streams, exit codes, JSON absent | confirmed |
| errors and recovery | typed errors are not executable rescue | exact copy and recovery commands missing | confirmed |
| Windows environment | target machine is not a support contract | OS/path/toolchain matrix and `doctor` required | confirmed |
| provider learning | existing endpoint assumed, learning absent | BYO endpoint education belongs in H1; server management does not | confirmed |
| upgrade/migration | accepted state can be stranded | copy-on-write verified migration must precede live data | confirmed |
| docs/observability | no user path; fields lack an operational surface | task IA, local logs, retention, redacted bundle required | confirmed |
| scope | move repository onboarding before H0/V0 | keep installers, auto-update, model management, cross-platform deferred | confirmed |

#### Pass 1 - Getting started experience

**Rating: 1/10 -> 9/10.** Before review, the actual path ended at “there is no
usable application,” and the plan deferred its five-minute criterion until
public packaging after V0. The target now matches the competitive 2-5 minute
tier in one terminal session:

1. `pwsh -NoProfile -File .\scripts\bootstrap.ps1` — at most 240 seconds wall,
   at most 60 seconds human active; prints version and the next command.
2. `claimbranch doctor` — at most 30 seconds; core must pass while manuscript
   and provider readiness may be optional warnings for the demo.
3. `claimbranch demo saturation --ai off --network deny` — at most 60 seconds;
   displays the verified lineage and no-write guarantee.

The combined cold-checkout gate is 300 seconds wall and 90 seconds active over
three trials. A clean checkout assumes the exact prerequisites named by the
toolchain ADR; installing Git or Windows itself is a separately measured
clean-machine journey. The remaining point requires measured implementation,
not more planning.

#### Pass 2 - Public CLI and automation

**Rating: 2/10 -> 9/10.** The old plan exposed DomainOperations, Python module
commands, and one `review open` example as though they formed one interface.
The new contract uses task-oriented noun groups, three universal root tasks,
explicit project/episode inference, safe next actions, normal/dev help
separation, configuration/secret precedence, and AI/network policies that do
not overload `offline`. Human and JSON modes share stable semantic results,
exit codes, and idempotency while JSON cannot bypass authorization. Help,
PowerShell quoting, paths with spaces/Korean text, redirected streams, and
unknown-command suggestions receive snapshot tests. The final point requires
using the CLI after implementation without consulting internal docs.

#### Pass 3 - Errors and debugging

**Rating: 4/10 -> 9/10.** Three concrete paths were traced:

| Path | Prior visible result | Required visible result |
|---|---|---|
| sealed review becomes stale | typed `StaleAuthorization` and abstract retry | `CBR-STATE-001`, no-change guarantee, saved rationale, one refresh command, diagnostic ID |
| provider fails or returns malformed output | provider phase `failed`; manual path promised | `CBR-PROVIDER-001`, nothing accepted, request evidence preserved, manual continuation plus `provider probe` |
| patch/compile state cannot be reconciled | `RecoveryRequired`, inspect/export/restore permitted | `CBR-RECOVERY-001`, exact at-risk relative path, mutation lock, preserved audit evidence, `recovery status` |

Golden copy must state problem, likely cause/context, unchanged state, preserved
work, one fix, stable help topic, and diagnostic ID. Verbose diagnostics remain
redacted and suppress framework traces unless a maintainer explicitly requests
the local crash detail. The last point requires testing whether an unfamiliar
researcher succeeds from the message alone.

#### Pass 4 - Documentation and learning

**Rating: 2/10 -> 9/10.** Current documentation is strong for maintainers but
has no operating path. Repository policy correctly forbids pre-creating empty
user documentation, so each topic lands with the executable it documents:

| Reader task | Canonical topic when useful |
|---|---|
| decide fit and try first result | root README status/support plus `docs/user/windows-quickstart.md` at H0 |
| learn without risk | `docs/user/offline-demo.md` at H0 |
| operate one paper | `docs/user/first-episode.md` at H1 |
| connect existing local inference | `docs/user/provider-setup.md` at H1 |
| resolve errors/recovery | `docs/user/troubleshooting.md` generated/checked against error schema at H0/H1 |
| command and JSON reference | generated from the public parser/schema; not hand-copied |
| understand authority/graphs | product and architecture explanations link to canonical ADRs |
| upgrade safely | versioned migration/recovery how-to before any live accepted data |

Examples are executable in CI, use PowerShell and paths with spaces, show
expected output, and declare the matching ClaimBranch version. The docs map
adds a user reading path only with the first real topic. Search and hosted
interactive docs remain deferred until there is a public corpus to justify
them.

#### Pass 5 - Upgrade and migration

**Rating: 2/10 -> 9/10.** “Export/import or forward migration” did not protect
accepted research state. The plan now requires version/status discovery,
compatibility check, space preflight, exclusive lock, verified export,
copy-on-write destination, full manifest verification, atomic selection, and
retention of the original. Every durable boundary has a restart fixture. Newer
stores permit only read-only status, diagnosis, and export under older code;
they never produce an opaque failure or write. No automatic updater, downgrade
mutation, destructive cleanup, generalized migration framework, or public
semantic-version promise enters F0. The remaining point depends on an actual
schema transition drill.

#### Pass 6 - Developer environment and tooling

**Rating: 3/10 -> 9/10.** Native Windows is now an executable support contract,
not a machine label. P1 freezes OS build/edition/architecture, shell/runtime,
standard-user policy, local filesystem and reparse rules, credential/presence
primitive, browser/loopback lifecycle, Git, pinned LaTeX workflow, antivirus
sharing behavior, and explicit exclusions. `doctor` produces the same
required/optional/unsupported/unknown result in human and JSON modes.
Repository fixtures support deterministic offline CI and local development;
`--format json`, `--network deny`, dry-run, and deterministic provider stubs
create automation escape hatches without automating human authority. Editor
plugins, cross-platform CI, hot reload, containers, and language SDKs do not
serve the current persona and remain outside the wedge.

#### Pass 7 - Community and ecosystem

**Rating: 2/10 -> 8/10.** There is no application, license, contribution guide,
changelog, public support route, example ecosystem, or plugin surface today.
Building a community shell now would be ceremonial. Before V0, ClaimBranch
needs only a versioned issue template, reproduction fixture instructions, and
local `audit export --diagnostics --preview`; sharing remains a separate human
act and never includes manuscript text by default. A license, contributing
guide, changelog, support policy, and examples become public-packaging
requirements after validated V0. Plugins and marketplaces remain trigger-gated
because they would weaken the finite authority surface. A plan-level 10 would
pretend a community exists, so 8 is intentionally honest.

#### Pass 8 - DX measurement and feedback

**Rating: 4/10 -> 9/10.** V0 previously measured only episode active time and
hid setup friction. P0 now freezes a local, previewable funnel: README start,
bootstrap wall/active time, doctor result, first demo output/completion, copied
commands, help use, project-init time, first review, recoverable errors, rescue
attempts, and abandonment. No measurement uploads automatically; fields,
retention, and deletion are declared before V0. The unfamiliar-user gate runs
before V0, and a second profile/machine rehearses clean checkout, first project,
migration, rollback, and diagnostics. `/devex-review` is the boomerang after H0
and H1; measured reality replaces these plan scores.

#### DX `NOT in scope`

- hosted playground or cloud sandbox: contradicts the first local trust proof
  and adds infrastructure for a reusable local fixture;
- public installer, package publication, shell auto-update, or daemon: admit
  only after V0; repository bootstrap is sufficient for validation;
- model catalog, download, quantization advice, process supervision, router,
  or provider marketplace: ClaimBranch teaches the connection boundary, not
  model management;
- editor extensions, SDKs, MCP/OpenClaw tools, graph canvas, or plugin API:
  require observed post-V0 transfer/navigation/integration demand;
- macOS, Linux, WSL, containers, ARM64, UNC/network/synced roots: each expands
  the durability and presence matrix before the native-Windows contract passes;
- hosted telemetry, automatic crash upload, NPS, or in-product feedback send:
  local evidence and a human-shared redacted bundle are enough for V0;
- public community program: license/support/contribution basics belong to
  packaging, while an ecosystem belongs after repeated external use.

#### DX `What already exists`

| Asset | Reuse |
|---|---|
| root README status warning | keep until H0, then replace the dead end with the three-command quickstart while preserving honest stage status |
| documentation map and policy | add user topics only with real executable surfaces; generate reference from schemas |
| repository docs check and CI | extend to command/example/encoding portability once those artifacts exist |
| saturation truth packet/goldens | drive the magical demo instead of creating a second tutorial scenario |
| typed error and failure registries | generate codes, help topics, JSON, and copy fixtures from one source |
| provider envelope and trace timing | expose through `provider probe/test/explain` without adding a server manager |
| recovery/import design | turn internal proof into stable operator recovery and migration commands |

#### DX implementation tasks

Priority and execution phase are separate fields; `priority P1` means blocking,
not plan phase `P1`.

- [ ] **DX-01 (priority P1, phase P0/P1; human: 1 day / CC: 1-2 hours) - Persona/support** - Freeze operator, Windows support, path topology, prerequisites, and exclusions in canonical product/validation documents and the toolchain ADR.
  - Verify: documentation checker plus support-matrix review with no unclassified host dependency.
- [ ] **DX-02 (priority P1, phase P1/P2; human: 1-2 days / CC: 2-4 hours) - Bootstrap/doctor** - Implement one standard-user PowerShell bootstrap and machine-readable readiness probes.
  - Verify: three clean-checkout cold trials, path matrix, no admin/profile edit, `doctor` human/JSON equivalence.
- [ ] **DX-03 (priority P1, phase P1/P2; human: 1-2 days / CC: 2-4 hours) - Public CLI** - Implement the public grammar, help, project discovery, streams, JSON envelope, exit codes, configuration, and dev-command separation.
  - Verify: CLI snapshots and PowerShell redirection/UTF-8/`NO_COLOR` tests.
- [ ] **DX-04 (priority P1, phase P2; human: 1 day / CC: 1-2 hours) - Offline demo** - Render the saturation fixture as a disposable no-write magical moment.
  - Verify: <=60 seconds after bootstrap, zero provider/compiler/user-project access, verified manifest, safe cleanup.
- [ ] **DX-05 (priority P1, phase P1/P2; human: 1-2 days / CC: 2-4 hours) - Errors/recovery** - Generate stable codes, exact rescue copy, help topics, diagnostics, and recovery-only commands from one schema.
  - Verify: golden messages, diagnostic lookup under failed normal open, unfamiliar-user message-only rescue.
- [ ] **DX-06 (priority P1, phase P1/P2; human: 2-3 days / CC: 4-8 hours) - Migration** - Implement verified copy-on-write forward migration and version-skew read-only rescue.
  - Verify: crash at every durable boundary, disk full, retained original, atomic selection, manifest equivalence.
- [ ] **DX-07 (priority P1, phase P3; human: 1-2 days / CC: 2-4 hours) - First project** - Add dry-run initialization, researcher-language episode template, marker/compiler preflight, and safe rollback.
  - Verify: supported paper plus spaces/Korean paths, dirty Git tree, missing marker/compiler, and unchanged failure cases.
- [ ] **DX-08 (priority P2, phase P3; human: 1-2 days / CC: 2-4 hours) - Provider learning** - Add stub and BYO-endpoint add/probe/test/explain flow with trust and serving metrics.
  - Verify: ten-minute target-machine walkthrough, remote-capable loopback classification, accepted manifest unchanged.
- [ ] **DX-09 (priority P1, phase P2/P3; human: 1 day / CC: 1-2 hours) - Documentation** - Land versioned quickstart, demo, first-episode, provider, troubleshooting, command-reference, and upgrade topics with their executable surfaces.
  - Verify: examples run in CI; every topic is indexed and version matched; no duplicated canonical contract.
- [ ] **DX-10 (priority P1, phase H1-to-V0 gate; human: 1 day / CC: 1-2 hours) - Measurement** - Run unfamiliar-user and second-profile journeys and record the local setup funnel before V0.
  - Verify: no coaching/internal edits, explicit thresholds, privacy preview, failure blocks V0.

Repository policy intentionally keeps these tasks in this active ExecPlan; a
root `TODOS.md` is not created.

#### DX scorecard

| Dimension | Before | Planned | Evidence |
|---|---:|---:|---|
| Getting Started | 1/10 | 9/10 | three-command <=5 minute path and isolated demo |
| API/CLI/SDK | 2/10 | 9/10 | stable public grammar, help, streams, JSON, exits, defaults |
| Error Messages | 4/10 | 9/10 | three traced golden rescues plus recovery-only access |
| Documentation | 2/10 | 9/10 | task-oriented topics land with executables; generated reference |
| Upgrade Path | 2/10 | 9/10 | verified copy-on-write migration and retained original |
| Dev Environment | 3/10 | 9/10 | executable native-Windows matrix and `doctor` |
| Community | 2/10 | 8/10 | minimal support artifact now; public ecosystem correctly deferred |
| DX Measurement | 4/10 | 9/10 | setup funnel, unfamiliar user, second profile, boomerang |
| **Overall plan DX** | **2.5/10** | **8.9/10** | no unresolved plan decision; implementation remains 0/unmeasured |

TTHW moves from undefined to a planned <=5 minutes, competitive tier. The
magical moment is designed through the copy-paste offline demo. Principle
coverage: zero friction, learn by doing, fight uncertainty, opinionated defaults
with explicit escape hatches, code in the paper context, and one memorable
lineage result are all covered at plan level.

#### DX implementation checklist

- [ ] Clean supported checkout reaches meaningful output in <=5 minutes.
- [ ] Bootstrap is one standard-user command and does not edit shell profiles.
- [ ] First run produces the verified evidence-to-manuscript result.
- [ ] Offline demo touches no provider, compiler, real paper, or project.
- [ ] Every handled error has code, problem, unchanged state, preserved work,
      one fix, help topic, and diagnostic ID.
- [ ] Public CLI is guessable from one example; internal operations stay under
      `dev`.
- [ ] Human/JSON output, exit codes, UTF-8, redirected streams, and no-color are
      stable.
- [ ] Docs examples run as written and land with the executable they describe.
- [ ] Migration verifies a new store and retains the original before selection.
- [ ] Deterministic CI requires no provider; H1 provider learning changes no
      accepted state.
- [ ] Native-Windows support and unsupported paths are machine-testable.
- [ ] Local diagnostic export previews and redacts before creation; nothing is
      uploaded automatically.
- [ ] Unfamiliar-user and second-profile gates pass before V0.
- [ ] `/devex-review` measures the implemented journey after H0 and H1.

The generic checklist items for TypeScript SDKs, free commercial tiers, hosted
search, public changelog, community channel, and automatic codemods are not H0/
H1 requirements; adding placeholders would violate the scope and documentation
policies.

#### DX completion summary

| Review item | Result |
|---|---|
| mode/persona | DX POLISH; native-Windows researcher-builder plus unfamiliar researcher |
| evidence trace | README/docs currently end before installation; every confusion point mapped to P0-P3 |
| competitive target | 2-5 minute tier; local copy-paste demo, not hosted playground |
| dual voices | 25 independent issues plus 10 Codex concern groups; 10/10 dimensions confirmed |
| passes | all eight completed; plan-level scores 8-9, lived implementation unmeasured |
| scope | bootstrap/doctor/demo/init/provider education/migration admitted; installers/model management/ecosystem deferred |
| unresolved decisions | none; the quiet editorial visual choice was auto-decided per the user's autonomy instruction |
| next gate | reconcile canonical docs, then P0/P1; run live `/devex-review` after H0/H1 |

**Phase 3.5 complete.** Both outside voices agreed that repository onboarding,
safe migration, and a first-project path are prerequisites rather than public-
packaging extras. The plan closes them without adding a hosted service, model
manager, broad UI, or new graph scope.

### Cross-phase themes

| Theme | Independent signals | Plan consequence |
|---|---|---|
| Human authorship needs both technical authority and legible UX | CEO, Design, Engineering, DX | sealed foreground authorization, complete Contributions, distinct deferrals/debts, exact action labels, and hostile negative tests |
| Graph-first must stay finite rather than become a platform program | CEO, Engineering, DX | one ResearchEpisode, one branch/merge/anchor, closed schemas/limits, and out-of-F0 live results instead of silent expansion |
| Always-available AI must remain replaceable and optional | CEO, Engineering, DX | manual core first, proposal-only providers, scoped context/egress, BYO endpoint education, no model manager |
| Recovery is part of product trust, not an internal exception | Design, Engineering, DX | separate graph/file phases, exact restore or one hard stop, public rescue commands, copy-on-write migration |
| Onboarding is a prerequisite for live validation, not packaging polish | CEO, Design, DX | bootstrap, doctor, offline demo, first-project and unfamiliar-user gates before V0 |

These repeated findings are high-confidence because they arose independently
from strategy, interaction, architecture, and operator perspectives.

### Aggregated implementation task disposition

The four phase artifacts contain 35 build-actionable tasks: 29 priority-P1 and
6 priority-P2. Their full wording remains in each phase's implementation-task
section and the local gstack JSONL artifacts; repository execution follows the
deduplicated dependency order rather than task-file order:

1. finish P0's redacted truth packet and frozen Markdown/checklist baseline;
2. freeze P1 schemas, authority, platform/toolchain, migration, and error/CLI
   contracts through bounded spikes;
3. build H0 kernel, recovery, bootstrap, doctor, and offline demo;
4. build H1 first-project, Episode Review, accessibility, and provider-learning
   flows; and
5. pass the unfamiliar-user/second-profile gates before preregistered V0.

Canonical documentation reconciliation tasks completed during this review are
recorded in Progress; implementation, fixtures, visual artifacts, and live
validation remain unchecked.

### Final approval disposition

The user explicitly directed the review to continue without further questions
and to take recommended choices. The final gate is therefore approved as
recommended: the finite graph-first sequence remains, the quiet editorial lab-
notebook direction is selected, and no user challenge changes the stated
product premise. There are no unresolved decisions. The next executable work is
P0 truth-packet/baseline assembly, not feature expansion or a release claim.

## Decision Audit Trail

<!-- AUTONOMOUS DECISION LOG -->

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | office hours | Make ClaimBranch a human-authorship-preserving research agent | user-approved | P6 | preserves the user's actual research goal | semantic VCS as product identity |
| 2 | office hours | Complete the fixture-bounded graph contract before UI | user-approved taste | P5/P6 | load-bearing semantics should not emerge accidentally from UI code | minimal agent-first path |
| 3 | CEO | Remove GPU mastery from ClaimBranch release gates | auto | P3/P4 | independent objective with no product dependency | co-equal interleaved track |
| 4 | CEO | Require a Markdown/checklist baseline and live paper | auto | P1/P3 | prevents circular validation | retrospective-only release |
| 5 | CEO | Keep only one branch/selected-merge shape in F0 | auto | P3/P5 | preserves chosen graph contract without generalized VCS | full LCA/conflict engine |
| 6 | CEO | Keep SQLite as baseline, not an accepted final choice | auto | P3/P5 | measure before adding graph storage | preselected graph DB or fixed stack |
| 7 | CEO | Treat local/hosted models as replaceable proposal providers | auto | P3/P5 | quality and privacy evidence should set defaults | 8 GB local model as default |
| 8 | CEO | Defer OpenClaw/MCP, GraphRAG, broad UI, and public packaging | auto | P3/P4 | no live trigger yet | platform-first expansion |
| 9 | CEO | Add technical human capability and raw-write isolation | auto | P1/P5 | proposal-only is otherwise a convention, not an enforced boundary | caller-supplied human actor flag |
| 10 | CEO | Reserve v1.0 for live validation | auto | P1/P3 | fixture correctness is not product success | checklist-only v1 release |
| 11 | Design | Use one command-launched Episode Review as the H1 primary surface | auto | P2/P3/P5 | preserves the full wedge without creating a chat, canvas, or dashboard product | Inbox home, chat home, four independent surfaces |
| 12 | Design | Split unaccepted deferral from accepted-with-review-debt | auto | P1/P5 | the user must know whether accepted state changed | one ambiguous deferred-to-Inbox state |
| 13 | Design | Show graph acceptance, patch, compile, restore, and debt as separate phases | auto | P1/P5 | a global success state would misrepresent manuscript safety | single committed state |
| 14 | Design | Require exact one-shot outbound review before remote provider use | auto | P1/P2 | turns the privacy contract into a legible human control | settings-only consent or implicit send |
| 15 | Design | Freeze deterministic impact tiers and action-specific authorization labels | auto | P1/P5 | review burden and scope cannot depend on UI convenience | generic Accept and subjective impact |
| 16 | Design | Make reflow, keyboard, contrast, live-region, and NVDA checks H1 acceptance | auto | P1/P5 | accessibility requirements need executable or observable oracles | aspirational accessibility prose |
| 17 | Design | Recommend a quiet editorial lab-notebook visual character | taste decision | P6 | long scientific comparison should be visually louder than AI or graph machinery | command-console character |
| 18 | Engineering | Add ResearchEpisode partitioning and explicit resource/attempt/blob limits | auto | P1/P5 | finite F0/V0 must be computable and resistant to untrusted growth | identity counts without episode or payload bounds |
| 19 | Engineering | Separate model query, human export, Proposal ingress, and accepted-state writer | auto | P1/P5 | mutation-only least privilege still permits exfiltration and confused-deputy writes | shared read/export/write surface |
| 20 | Engineering | Require a broker-verified sealed bundle, OS presence, and private receipt delivery | auto | P1/P5 | a browser click or signature alone does not prove meaningful human authority | JavaScript-held capability or actor flag |
| 21 | Engineering | Use a fenced AEAD write-ahead saga and isolated compiler for manuscript changes | auto | P1/P5 | crash recovery and external-editor races need proof-driven transitions | best-effort backup and in-place compile |
| 22 | Engineering | Generate reachable UI tuples from legal events instead of accepting the Cartesian product | auto | P1/P5 | finite names do not make impossible state combinations safe | persisted duplicated UI flags |
| 23 | Engineering | Limit F0 import to isolated verify-only or trusted empty-store restore | auto | P1/P5 | unknown history cannot inherit local human authority | merge/promote arbitrary import into live project |
| 24 | Engineering | Keep Python, pytest, SQLite, and loopback UI as post-spike hypotheses until ADR acceptance | auto | P3/P5 | documentation must not present illustrative commands as settled stack truth | implicit stack lock-in |
| 25 | DX | Target one native-Windows researcher-builder and name unfamiliar user/maintainer separately | auto | P5 | install tolerance and vocabulary differ across the three personas | generic researcher/developer audience |
| 26 | DX | Move clean-checkout bootstrap, doctor, and <=5 minute demo into H0 | auto | P1/P2 | V0 cannot validate a source checkout nobody can operate | defer all onboarding to public packaging |
| 27 | DX | Reuse the saturation fixture as an AI-off copy-paste magical moment | auto | P3/P4 | shows unique value with no new scenario, provider, compiler, or real write | hosted playground or provider-first onboarding |
| 28 | DX | Separate public task commands from kernel operations and validation harnesses | auto | P4/P5 | one guessable language prevents internal authority concepts from becoming UX | expose DomainOperation names directly |
| 29 | DX | Make every handled failure an exact no-change/preserved-work/next-action contract | auto | P1/P5 | typed exceptions alone do not let an unfamiliar operator recover | code-only errors or internal-edit instructions |
| 30 | DX | Require copy-on-write verified migration before live accepted data | auto | P1/P5 | accepted research state cannot depend on an untested upgrade path | in-place/generalized migration or export-only advice |
| 31 | DX | Teach local serving through BYO endpoint probe/test/explain after the manual path | auto | P2/P3/P4 | satisfies the learning goal while keeping inference replaceable and proposal-only | model manager, downloads, routing, or AI-first correctness dependency |
| 32 | DX | Keep measurements and diagnostics local, previewable, bounded, and manually shareable | auto | P1/P5 | DX evidence must not create hidden manuscript egress | hosted telemetry or automatic crash upload |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---:|---|---|
| CEO Review | /plan-ceo-review | Scope and strategy | 1 | CLEAN via autoplan | 7 premises, 8 scope candidates, and 17 specification findings resolved; one graph-first taste choice retained and approved |
| Codex Review | /codex review | Independent diff review | 0 | not run | phase-specific Codex outside voices ran instead; this was a plan review with no implementation diff |
| Eng Review | /plan-eng-review | Architecture and tests | 1 | CLEAN via autoplan | 14 plan issues closed; 7 post-cap clauses revalidated; implementation proof remains P1/H0 work |
| Design Review | /plan-design-review | Human authority and UI/UX | 1 | CLEAN via autoplan | plan score 5/10 to 9/10; 10 decisions; no visual implementation or mockup claimed |
| DX Review | /plan-devex-review | Operator and developer experience | 2 | CLEAN via autoplan | plan score 2.5/10 to 8.9/10; TTHW unbounded to target <=5 minutes; lived product remains unmeasured |

**CODEX:** CEO, Design, and DX voices completed; the Engineering Codex voice
timed out and that phase correctly used independent-subagent-only degradation.

**CROSS-MODEL:** CEO confirmed 5/6 dimensions with one already approved
graph-first taste difference; Design confirmed 7/7; DX confirmed 6/6; Engineering
has no cross-model consensus claim because the Codex voice was unavailable.

**VERDICT:** CEO, Design, Engineering, and DX plan reviews are clear. The
repository is ready to execute P0/P1 specification, fixture, and spike work; it
is not yet an implemented application and is not ready to ship.

NO UNRESOLVED DECISIONS
