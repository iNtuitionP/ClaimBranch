---
kind: release-scope
status: proposed
owners: maintainers
last_reviewed: 2026-09-21
canonical_for: smallest product-validation release scope
---

# Validation prototype: finite graph contract to live-paper evidence

This is the smallest release sequence permitted before the conditional
[candidate MVP](candidate-mvp.md). It validates a human-owned research-agent
workflow, not a generic graph platform, complete semantic VCS, model-serving
stack, or public application.

The [saturation case](../../validation/cases/saturation.md) owns the observable
scientific scenario. The [domain model](../../designs/2026-08-03-domain-model.md)
owns the closed F0 records, relationships, operations, states, cardinalities,
and resource bounds. The active ExecPlan owns implementation order and commands.

## 1. Goal

Validate this promise:

> When an unexpected result challenges an important claim, ClaimBranch
> preserves the lineage from evidence through AI contribution and human
> judgment to manuscript consequence, and accepts only changes that the
> researcher knowingly authorizes.

Passing a retrospective fixture means **foundation validated**, not product
success. The release requires both deterministic contract evidence and a
preregistered prospective live-paper evaluation.

### 1.1 Development and real-use gates

Private original-source verification remains an unchecked P0 requirement. It
must pass before **any real research use**: writing real workspace records,
adopting research judgments, editing a real manuscript, or running a real-use
pilot. It is no longer a prerequisite for starting explicitly synthetic
development. Passing synthetic tests neither confirms the private case nor
closes P0. P1 trust/toolchain decisions, OS isolation, H0 safety requirements,
and all applicable H1/V0 release gates remain unchanged.

While the real source case is unavailable, the user-approved
[source-independent storage probe](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-independent-storage-probe)
may test external placement, synthetic judgment save/read, and interrupted
retry using disposable data only. It does not close P0, select the application
stack, authorize real research storage, or satisfy any H0/H1/V0 release gate.

The user also approved the [bounded P1 early slice](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#p1-early-slice-first-pass-and-placement-contracts):
synthetic first-pass draft/review contracts, project placement/association,
and model-originated acceptance denial. It leaves P0 source fidelity open and
does not authorize a production trust, storage, or recovery choice. The
[augmented synthetic cases](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#augmented-synthetic-contract-cases)
extend invariant checks without modifying the original truth packet. Wider
synthetic development and release completion retain their phase-local gates;
source verification cannot be deferred beyond the first real research use.

The [read-only graph walkthrough](../../development/workflow.md#read-only-graph-walkthrough)
may precede the real foreground-authorization experiment. It exposes the
existing fixture's typed relationships, hypothetical branch differences, and
selected-change preview without persistence or authority. It does not replace
the H0 demo or prove any release gate; A1 remains complete and A2 remains open.

## 2. Product question

Does the focused workflow preserve important reasoning, AI provenance,
understanding obligations, and manuscript consequences better than the
researcher's existing Markdown/checklist process without adding more than 10%
median active-time overhead?

The user selected ClaimBranch as the primary workspace for the bounded
result-to-paper judgment. Compare the full first-pass interpretation and
recording workflow, not an added review after a completed external decision.
This changes the evaluation design, not the admitted product features.

A schema, graph viewer, chat demo, AI answer, or passing unit suite cannot
answer this alone.

## 3. Closed foundation F0

F0 admits only one bounded saturation shape:

- one ResearchEpisode;
- two ArtifactRefs: result and manuscript;
- one completed Run;
- three confirmed Observations;
- one central Claim;
- one non-nested reasoning branch with one Interpretation;
- three to six closed typed ScientificEdges;
- zero or one ExperimentPlan;
- one selected dependency-closed merge;
- one marked ManuscriptAnchor, PatchIntent, and ManuscriptDebt;
- bounded Decisions, Contributions, ReviewBundles, receipts, attempts, and
  operations; and
- zero Proposals on the manual path or one frozen root Proposal and trace on the
  recorded path.

No extra record kind, free-form edge, nested branch, second manuscript file,
general merge, or arbitrary plugin data is admitted. The implementation rejects
unknown fields and operations. A live eligible episode that needs more is
out-of-F0 and counts as an incomplete product flow rather than expanding the
contract.

## 4. H0: deterministic headless foundation

### 4.1 H0-manual

The AI-off fixture completes:

1. start the episode;
2. import the bounded truth packet;
3. append three human evidence-confirmation events;
4. create the one reasoning branch and Interpretation;
5. record the reviewed relationships and optional ExperimentPlan;
6. compute impact and authorize the selected merge;
7. derive the one manuscript debt;
8. prepare/apply the exact marked-block patch;
9. compile or restore safely;
10. close manuscript debt through a separate human authorization; and
11. close and replay the episode.

Proposal, model trace, AI Contribution, and UnderstandingDebt counts are zero.
No provider or network call occurs.

### 4.2 H0-recorded

The second isolated history starts from one frozen, normalized Proposal and
ExecutionTraceManifest without contacting a provider. The researcher may edit
and selectively materialize its content.

The history must retain:

- Proposal and trace identity;
- ordered AI and human Contributions;
- sealed review and human receipt;
- the human rationale;
- high-impact teach-back deferral;
- one UnderstandingDebt opened with acceptance; and
- a later separately authorized human closure.

It has its own byte-identical full-audit golden. It is not compared with the
manual history as though provenance should match. A separately named
scientific-state projection may match only when its excluded audit fields are
explicit.

### 4.3 Authority, privacy, and recovery proof

H0 must deny:

- raw or gateway accepted-state writes from a model process;
- a caller-provided human actor field;
- forged, stale, expired, replayed, cross-project, or changed-bundle receipts;
- model use of human export or disallowed artifact/manuscript fields;
- provider egress without an exact matching consent digest;
- untrusted imported history gaining local accepted authority; and
- model/agent closure of understanding or manuscript debt.

Every interrupted canonical append and manuscript journal/replace/compile/
restore boundary either resumes from durable evidence, proves exact restoration,
or enters one visible recovery-required hard stop. Two tabs/processes, an
external editor, supersession, missing key, disk full, and compiler side effects
cannot cause a blind overwrite.

### 4.4 H0 operator readiness

From a clean supported source checkout with declared prerequisites, a standard-
user researcher-builder must:

1. run one repository-owned PowerShell bootstrap;
2. run doctor and understand core versus optional manuscript/provider readiness;
   and
3. run the disposable saturation demo with AI off and network denied.

Three cold trials on the named supported Windows machine must reach the verified
demo within 300 seconds wall time and 90 seconds active time. The demo itself
finishes within 60 seconds after bootstrap, needs no provider or LaTeX
installation, and cannot touch a real project.

Public help, streams, UTF-8, no-color, JSON envelope, exit codes, stable error
copy, diagnosis, local redacted export, recovery commands, copy-on-write
migration, path matrix, and version-skew behavior are H0 gates rather than
post-validation packaging work.

### 4.5 H0 exit

H0 passes only when:

- both isolated histories replay to their respective full-audit goldens;
- accepted-state and raw-write authority tests fail closed;
- context and egress tests prove least privilege;
- the marked file compiles and verifies or restores exact prior bytes;
- human-only debt closure tests pass;
- projection rebuild changes no accepted manifest;
- trusted restore and verify-only untrusted import remain distinct;
- copy-on-write migration retains the original and survives every durable cut;
  and
- the clean-checkout demo gate passes.

## 5. H1: minimum human review and optional provider

H1 adds only the surfaces required to operate the wedge on a real compatible
paper.

### 5.1 First-project path

The public flow provides:

- project initialization dry run and reviewed apply;
- researcher-language episode template;
- episode start/status/review/close;
- marker add/verify;
- manuscript and compiler doctor;
- diagnosis and recovery that never require internal storage edits; and
- one clear safe next action after every handled result.

Failure leaves the paper and accepted state unchanged.

### 5.2 Episode Review

The command-launched local workspace is one quiet editorial decision sheet:

1. situation;
2. optional AI suggestion labeled Not accepted;
3. scientific before/after and evidence;
4. exact selected dependency closure and omissions;
5. marked manuscript consequence and source diff;
6. human rationale and teach-back or explicit deferral;
7. action-specific authorization; and
8. collapsed audit details.

Not now makes no accepted change. Authorize now and review explanation later
may create accepted state only while atomically opening visible
UnderstandingDebt. A small Review Pending list restores the exact episode and
distinguishes understanding debt from manuscript debt.

Graph acceptance, patch preparation/application, compile verification, restore,
and debt closure are separate visible phases. Provider timeout, malformed
output, cancellation, late arrival, and staleness return to a manual or re-review
path and never imply acceptance.

### 5.3 Provider and local-serving learning

One deterministic stub, one already-running loopback OpenAI-compatible endpoint,
and at most one hosted endpoint use the same bounded Proposal envelope.

The visible add/probe/test/explain flow reports compatibility, trust
classification, model identity, context ceiling, structured output,
cancellation, request/response schema, timing, token usage, and throughput when
available. Exact outbound content is reviewed before remote-capable use. Every
result is visibly unaccepted and the accepted-state hash does not change.

ClaimBranch does not download, quantize, supervise, route, update, or benchmark
model servers. Deterministic CI invokes only the stub.

The [external-inference decision](../../architecture/decisions/0009-external-inference-and-local-authority.md)
retains this operational boundary. H0 manual/frozen-proposal authority comes
before live integration. The live loopback and hosted targets above are gated
deployments, not permission to trust any compatible endpoint: the
[provider authority oracle](../../validation/cases/saturation.md#13-provider-authority-and-support-oracle)
must pass for the actual topology. Unknown same-user isolation cannot be waived
by a warning; AI-off remains available, but does not itself close H1's live
provider-learning gate. No provider has passed that gate yet.

### 5.4 H1 exit

Before V0:

- initialization and reopening satisfy the external-private-workspace cases
  in the [operator oracle](../../validation/cases/saturation.md#10-operator-experience-oracle);
  relocation, export ownership, and the declared restore boundary are tested;
- all browser/IPC/presence/receipt hostile cases pass, or the reviewed native/
  CLI helper satisfies the same authority contract;
- one unfamiliar supported-Windows researcher completes bootstrap, doctor,
  offline demo, project dry run, a manual episode, deferred review resume, and
  recovery inspection without coaching or internal edits;
- one second clean user profile or supported machine rehearses checkout, first
  project, export, migration, rollback selection, and diagnostics;
- the provider-learning exercise completes within ten active minutes without an
  accepted-state change; and
- application, lockfile, store/schema/rule, compiler, and fixture versions are
  frozen for V0.

## 6. V0: prospective live-paper evaluation

V0 observes the first three consecutive qualifying valid starts within eight
weeks after a protocol, baseline template, timing rules, evaluator prompts,
privacy fields, and decision checker are frozen in version control.

V0 is not ready to preregister: the primary-workspace choice retires the
baseline-first, same-episode comparison. The three-start/eight-week budget and
outcome thresholds below remain existing planning constraints, not a completed
replacement comparison design. Resolve section 6.2 before freezing any run.

### 6.1 Eligibility

An episode qualifies only when:

- the result was produced after preregistration;
- it may change an already accepted central/supporting Claim or the marked
  manuscript block;
- it is entered before the final interpretation or manuscript decision; and
- required artifacts may be captured locally under legal and ethical policy.

Eligibility is frozen before and independently of ClaimBranch representation.
An eligible episode that exceeds F0 is out-of-F0 and counts against the product.
Formatting-only work, retrospective known-answer cases, and results with no
claim/manuscript consequence are ineligible.

At most three post-start protocol-invalid episodes may be replaced. A fourth
invalid replacement makes V0 inconclusive. Provider, anchor, authorization,
abandonment, representation, or other product failure after a valid start stays
with that start.

### 6.2 Baseline and observation

Each compared workflow must start before its research judgment has been made
and use equivalent start/end boundaries: interpretation of the eligible result
through recorded decision and manuscript consequence. Include context entry,
review, corrections, and recording in active work; report manuscript execution
and verification consistently in both workflows. Do not require a completed
Markdown answer before ClaimBranch use or treat a repeat attempt as first-pass
time, even if the model never receives that answer.

Before preregistration, obtain user approval for comparison allocation, the
number of baseline and product episodes, treatment of prior knowledge and
episode difficulty, and equivalent completion/timing boundaries. Reconcile
eligibility, stopping rules, and the outcome checker with that approved design.
Do not silently select an allocation or change thresholds. The committed blank
P0 baseline remains a historical source-fixture artifact, not an authorized
prospective protocol; revise its version and integrity manifest only after the
replacement design is approved.

Record:

- baseline and ClaimBranch active time;
- setup, wait, interruption, provider, and compile time separately;
- trace completeness;
- accepted AI Contribution and human edits/rationale;
- teach-back and debt state;
- false alarms and anchor repair;
- manuscript, promotion, and restore outcome; and
- any material omission surfaced.

A material omission surfaced is a concrete missing claim dependency, rationale,
provenance link, debt, or manuscript consequence raised before the final
decision that the researcher attests changed what they checked, recorded, or
wrote. V0 must not claim causal prevention.

### 6.3 Frozen outcome rule

Evaluate rows in order and take the first match. Global catastrophic predicates
apply even with zero valid starts. Completion-ratio and incomplete-trace
predicates apply only when at least one valid start exists; zero starts with no
catastrophe is inconclusive.

| Order | Outcome | Rule |
|---:|---|---|
| 1 | NOT_VALIDATED | any unauthorized accepted mutation, unrecovered manuscript loss, or silent promotion; or, when valid starts exist, completion below two thirds or at least two incomplete traces |
| 2 | INCONCLUSIVE | fewer than three valid starts by eight weeks, or timing/protocol corruption makes comparison unusable |
| 3 | VALUE_NOT_DEMONSTRATED | three starts and all trust/file rules pass, but any flow/trace is incomplete including out-of-F0, median active time exceeds baseline median by more than 10%, or no attested material omission is surfaced |
| 4 | VALIDATED | all three flows complete voluntarily, trace completeness is 100%, trust/file rules pass, median active time is at most baseline median plus 10%, and at least one attested material omission is surfaced |

Only VALIDATED opens the candidate MVP and ordinary conditional integration/
serving/graph/UI expansions. Other outcomes preserve the failed result and
permit failed-gate repairs followed by a newly preregistered V0. A necessary
change to the initial representation hypothesis follows the separate revision
rule below; it is not a successful validation or an ordinary expansion.

### 6.4 Bounded revision after a failed hypothesis

A failed initial shape must be learnable without admitting an adjacent feature
program. If observed evidence shows that a frozen representation or technical
hypothesis prevents the intended workflow, the maintainer may authorize one
minimum, evidence-backed revision before VALIDATED. Before implementation:

- retain the original failure, artifacts, and assigned outcome unchanged;
- identify the falsified hypothesis and show why an in-scope repair cannot
  address it; satisfy the applicable existing admission evidence threshold
  in the ExecPlan, without requiring V0 success for this revision;
- obtain explicit user approval of the exact revised boundary, update the
  canonical scope and ExecPlan, create any required superseding ADR, and obtain
  independent review.

After implementing that approved revision, repeat every affected foundation
and safety gate, then freeze a new protocol before collecting a new prospective
run. Old episodes may support the revision but never count as new prospective
validation episodes.

For example, two independent prospective eligible cases that need the same unsupported
branch shape can justify considering that one shape. They do not authorize a
general merge engine, other graph features, or a wider platform. No revision
waives human authority, privacy, recovery, or manuscript-safety requirements,
changes a running evaluation's goalposts, or relabels a failed run successful.

## 7. Explicitly outside this release

- arbitrary/nested semantic branching, general LCA merge, revert, and conflict
  resolution;
- generalized ingestion, adapter marketplace, broad ontology, or multiple
  manuscript files;
- daemon, chat home, full Inbox product, command palette, graph canvas, or
  dashboard suite;
- OpenClaw/MCP adapter, channels, skills runtime, or agent platform;
- model download, quantization, supervision, routing, fallback, or broad serving
  benchmarks;
- embeddings, GraphRAG, graph-native storage, or generalized retrieval;
- related-work and PDF workflows;
- public installer, auto-update, cross-platform support, hosted telemetry,
  collaboration, SaaS, or mobile; and
- v1.0 or market-success claims based on H0/H1 alone.

The numeric admission triggers for ordinary expansion live in the active
ExecPlan and require VALIDATED V0 evidence. The bounded hypothesis-revision
rule above is the only pre-success scope-change route; no excluded capability
is admitted merely because this route exists.
