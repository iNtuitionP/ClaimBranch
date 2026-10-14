---
kind: release-scope
status: proposed
owners: maintainers
last_reviewed: 2026-10-14
canonical_for: smallest product-validation release scope
---

# Validation prototype: finite graph contract to live-paper evidence

This describes the protected validation sequence before the conditional
[candidate MVP](candidate-mvp.md). The user's 2026-10-07 request prioritizes
the manual own-project source baseline in [section 5.5](#55-source-delivery-readiness).
On 2026-10-10 the owner required working optional AI before GitHub publication;
the [publication milestone](#ai-connected-github-publication-milestone) adds the
existing personal-AI live gate to that completed baseline.
On 2026-10-11 the owner explicitly authorized publishing the current source now,
with live AI unavailable. This manual experimental source preview does not pass
or remove the later AI-connected milestone.
The personal terminal alpha is now selected under
[ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md);
the protected validation sequence below remains later work.
This sequence validates a human-owned research-agent
workflow and the minimum usable source-delivered app. It does not establish a
generic graph platform, complete semantic VCS, model-serving stack or a v1.0
product claim.

The [saturation case](../../validation/cases/saturation.md) owns the observable
scientific scenario. The [domain model](../../designs/2026-08-03-domain-model.md)
owns the closed F0 records, relationships, operations, states, cardinalities,
and resource bounds. The active ExecPlan owns implementation order and commands.

The user-required [paper argument workspace](../product-spec.md#7-interaction-and-visual-character)
is admitted during current development by
[ADR 0011](../../architecture/decisions/0011-paper-argument-graph-workspace.md).
The original single-claim F0 remains a regression baseline. Paper-level model
extensions need versioned contracts and acceptance evidence before real use;
they are not silently added to a running V0 protocol. This is a pre-V0 product
direction change, not an observed V0 failure or a completed release gate.

## 1. Goal

Validate this promise:

> When an unexpected result challenges an important claim, ClaimBranch
> preserves the lineage from evidence through AI contribution and human
> judgment to manuscript consequence, and accepts only changes that the
> researcher knowingly authorizes.

Passing a retrospective fixture means **foundation validated**, not product
success. The release requires both deterministic contract evidence and a
preregistered prospective live-paper evaluation.

The first usable GitHub delivery is a narrower milestone within this sequence,
defined in [section 5.5](#55-source-delivery-readiness) and
[ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md).
It retains own-project save/resume, while later features pass their own gates.
Its completion does not complete this full validation prototype or V0.

### 1.1 Development and real-use gates

Private original-source verification remains an unchecked P0 requirement for
the protected H0/H1/V0 workflow. Under ADR 0017 it does not block unrelated
personal-alpha feedback; that person supplies and checks their own sources.
The selected alpha's exact requirements are in section 5.5. P0 must pass before
protected real research use: writing protected workspace records,
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

1. run one repository-owned bootstrap for the declared target (PowerShell on
   Windows; the Mac path must be independently implemented and verified);
2. run doctor and understand core versus optional manuscript/provider readiness;
   and
3. run the disposable saturation demo with AI off and network denied.

Three cold trials on the named supported target machine must reach the verified
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

The command-launched local workspace implements the product's PG-1 through
PG-5 paper-graph requirements. Episode Review is contextual to the selected
argument: scientific before/after, selected closure and omissions, manuscript
consequence, AI provenance, human rationale and authorization remain available
without requiring a separate linear decision sheet. A graph-only illustration
with no durable research workflow does not satisfy H1.

The later terminal selection in
[ADR 0012](../../architecture/decisions/0012-terminal-research-workspace.md)
makes the experiment host's terminal the primary daily interaction. The
synthetic TUI is an exploration increment, not evidence of protected Linux/SSH
deployment, durable resumption, or completed H1.

The [paper workspace oracles](../../validation/cases/saturation.md#102-paper-argument-workspace-oracles)
own observable graph acceptance. Exact expand/collapse, emphasis and scenario
controls remain under design review; their depiction is not scientific or
authorization evidence.

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
- the paper workspace oracles pass against an explicitly versioned extended
  model, alongside the unchanged original F0 regression fixtures;
- one unfamiliar researcher on the supported target completes bootstrap, doctor,
  offline demo, project dry run, a manual episode, deferred review resume, and
  recovery inspection without coaching or internal edits;
- one second clean user profile or supported machine rehearses checkout, first
  project, export, migration, rollback selection, and diagnostics;
- the provider-learning exercise completes within ten active minutes without an
  accepted-state change; and
- application, lockfile, store/schema/rule, compiler, and fixture versions are
  frozen for V0.


### 5.5 Source-delivery readiness

The user explicitly selected the key-free personal terminal alpha on 2026-10-07
and requested fast implementation, feedback and iteration.
[ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md)
supersedes the first-release protected Mac requirement in ADR 0016. The
[four-outcome ExecPlan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#first-release-outcome-ledger)
owns implementation. This is a usable own-project manual workspace, not another
bundled demo, protected H0/H1 completion, scientific-value validation or v1.0.

#### First feedback and alpha completion

Show the local version for feedback as soon as the person can enter their own
thesis, add claims/results/typed relations, record one judgment, quit and reopen
that same work. Do not wait for live AI, formal V0 or another unfamiliar user
before showing it. Collect concrete friction: where they cannot find an action,
understand a connection, record their reason once or recover their writing.
Fix observed defects before expanding capability.

Before calling the alpha ready for source distribution, verify:

- Public init/open starts from human-written content with AI off, no fabricated
  observations and no internal JSON edits. Provisional result capture and explicit
  personal confirmation are distinct; measurements/source references remain
  honest about missing fields. Typed relations retain their rationale, shared
  evidence has one identity, corrections append and alternatives remain readable.
- Notes, graph/history, judgment/reason, kept/unfinished input, origin and open
  manuscript follow-up survive a fresh process. One judgment is reused at review;
  no mandatory second narrative or routine comprehension quiz is introduced.
- Ordinary files live in an owner-private directory outside Git. Bounded schema
  validation, exclusive locking, expected-state checks and atomic replacement
  refuse corrupt/newer data, conflicting sessions and failed saves without blind
  overwrites. Uncertain saving remains visible and live text is preserved.
- Explicit local backup/export and fresh-destination restore reproduce the
  verified saved contents and retain the original. No backup is claimed to
  contain unsaved writing. Missing/changed manuscript source preserves the
  original basis; manuscript files remain read-only.
- Wide/narrow actual PTY input, Korean pasted text, resize and exit restore a
  usable shell. Declare only tested hosts/runtime versions. Prepare Linux CI
  checks for the portable path; missing actual SSH/tmux, physical IME or remote
  CI observations remain explicit and do not delay local feedback.
- Clean source extraction/checkout runs init/open and the manual loop without
  untracked resources, maintainer paths or native Mac tools. Help/doctor explain
  personal storage, supported versions and unavailable features. A license is
  selected by the owner before claiming licensed open source. The owner's
  2026-10-11 instruction authorizes current-source publication, and the owner
  selected MIT for the repository and shipped runtime ZIP. Verification alone
  authorizes no push/release.

#### Selected personal storage and authority

Ordinary private local files and backups have no application-level encryption.
No device key, Secure Enclave, native enrollment or OS presence check is required.
Explicit terminal review records personal intent; it provides no signed protected
approval or defense against an unrestricted same-user process. Personal history
uses a distinct format/destination and cannot confer protected accepted authority.
Existing encrypted/native work is neither converted nor weakened automatically.
Imports cannot erase origin, manufacture confirmation or grant protected authority.

The person supplies and checks their own sources for this alpha; source references
never imply actual access, verified fidelity or scientific truth. The historical
private-source P0 mapping remains a gate for the later protected H0/H1/V0 program,
not a prerequisite for feedback on an unrelated personal project under ADR 0017.
Do not promise preservation of irreplaceable data before save/recovery is tested.

#### Deferred capabilities

The next optional personal-AI version is selected under
[ADR 0018](../../architecture/decisions/0018-optional-personal-ai.md), using the
[L01–L04 order](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#optional-ai-follow-up-implementation-plan).
It retains ordinary private storage and no native keys; selective item origin,
explanation choice/return and actual provider/egress checks precede live use.
This does not add first-alpha completion prerequisites. Portable typed ingress
and the [offline selective-staging/return backend](../../development/workflow.md#selective-proposal-staging-and-origin-return)
now exercise that origin/explanation checkpoint. Its separate [offline terminal
rehearsal](../../development/workflow.md#selective-ai-items-in-the-terminal) connects
contextual selection, editing and return on invented content. The current public
personal version remains AI-off; actual provider/egress still gates live enablement.

Live AI, selective typed AI incorporation, protected accepted operations and debt
closure, hardware-backed custody/recovery, automatic manuscript apply/compile,
schema/native authority migration, Windows support, installers and formal V0
are deferred. AI remains off by default; retained origin stays inspectable.
Manuscript wording and unresolved follow-up support the person's existing editor;
reviewing them cannot imply that a file was applied or an obligation closed.
Enable later capabilities only with their owning authority/privacy/recovery evidence.

#### Planned personal paper migration follow-up

The owner's 2026-10-13 issue-planning request and selected
[ADR 0023](../../architecture/decisions/0023-personal-argument-import-and-sharing.md)
policies concern a next personal version. Its explicit manual whole-paper capacity
subset is now implemented under the [versioned capacity contract](../../designs/2026-08-03-domain-model.md#personal-paper-lifecycle-extension-planned);
verification does not qualify public AI for this new profile. Exact-reviewed
prior-argument registration and source-aware personal reasoning now retain
unsupported originals, historical authorship/reasons and new human judgment
through private return. Read-only registered anchors, human wording/companion restrictions and scoped
co-reported readings, exact structured measurements and original/amended protocol
records and private sourced questions now connect to inspection
and private return. Selected current-science sharing now has explicit dependency
preview, reason opt-in, opaque IDs and exact private-revision verification;
[sharing coverage](../../development/workflow.md#selected-canonical-git-sharing)
excludes private originals and historical backups. They do not reopen the completed manual
alpha or declare the full protected candidate MVP/V0 admitted. The
[per-issue execution plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan)
and [planned personal acceptance oracles](../../validation/cases/saturation.md#personal-paper-migration-and-revision-acceptance-planned)
record what must pass before those capabilities are advertised. Private-source
fidelity, scientific correctness and actual user benefit are independent from
synthetic capacity/import checks. Native keys, Windows participation and an
extra provider request are not prerequisites for this personal planning/fixture
work; existing protected authority and live-provider gates retain their scope.

#### AI-connected GitHub publication milestone

Selected by the owner on 2026-10-10, then made a later milestone by the explicit
2026-10-11 instruction to publish the current source now. The immediate manual
experimental preview may ship with live AI unavailable; it must not claim this
AI-connected milestone is complete. A release that advertises working optional
personal AI still follows [ADR 0018](../../architecture/decisions/0018-optional-personal-ai.md).
AI remains off by default and users explicitly connect their own provider/account.
The current instruction authorizes source commit/publication, not an additional
model request or an arbitrary license grant. The owner separately selected MIT
on 2026-10-11; include its complete notice in the repository and runtime ZIP.

Before declaring this milestone ready, pass the existing
[personal-AI live checkpoint](../../validation/cases/saturation.md#131-optional-ai-follow-up-acceptance-proposal):
qualify the selected actual provider/access/egress, obtain a checked live
proposal, and exercise contextual comparison, selective human editing/recording,
retained origin, fresh-process/backup return and manual continuation on failure.
Under [ADR 0022](../../architecture/decisions/0022-contextual-advice-and-explicit-edits.md),
the new route may first return readable advice and then prepare only an explicit
small edit or locally selected passage. Whole-answer graph conversion is not a
gate. Actual advice alone still does not complete selective human recording and
origin return; the complete new path must pass those same researcher outcomes.
An authenticated thread, internal test response or unsent preview is insufficient.
Observe a researcher-authored new task with explicit outbound choice, reporting
its actual benefit or lack of benefit without claiming comprehension or V0.

The existing [L04 execution order](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#ai-connected-github-publication-order)
owns this work; do not reopen completed S01–S04 or add a second implementation
ledger. Verify the final source/terminal journey and applicable alpha regression,
then complete the owner-directed source/license/commit/publication process above.
No hardware key, protected custody, Windows support, installer or manuscript
automation is added to this milestone. Current public AI remains unavailable
until its actual gate passes.

### 5.6 Proposed personal terminal alpha

The former proposal is selected under [ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md).
This heading remains for link stability. [Section 5.5](#55-source-delivery-readiness)
now owns the current alpha scope; there is no second release backlog or pending
storage approval. The protected product remains later work with its original
scientific, provider, manuscript and authorization gates.

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
- daemon, chat home, full Inbox product, command palette, unrestricted graph
  editor or dashboard suite; the bounded paper argument workspace is in scope;
- OpenClaw/MCP adapter, channels, skills runtime, or agent platform;
- model download, quantization, supervision, routing, fallback, or broad serving
  benchmarks;
- embeddings, GraphRAG, graph-native storage, or generalized retrieval;
- related-work and PDF workflows;
- public installer, auto-update, broader platform support, hosted telemetry,
  collaboration, SaaS, or mobile; and
- v1.0 or market-success claims based on H0/H1 alone.

The numeric admission triggers for ordinary expansion live in the active
ExecPlan and require VALIDATED V0 evidence. ADR 0011 explicitly admits the
user-required paper argument workspace in the current baseline. Apart from
that recorded direction change, the bounded hypothesis-revision rule above
governs evidence-driven pre-success expansion; it does not admit unrelated
excluded capabilities.
