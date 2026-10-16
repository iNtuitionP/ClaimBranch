---
kind: target-architecture
status: draft
owners: maintainers
last_reviewed: 2026-10-14
canonical_for: target pre-implementation system boundaries and quality constraints
---

# ClaimBranch target architecture

ClaimBranch has a synthetic interactive prototype and a separate experimental
personal terminal alpha. Its protected research app and production stack remain
unfinished. Repository contract models and disposable probes
provide bounded evidence, not the implemented target architecture. This
document defines boundaries and quality constraints
that the first finite slice must test; it does not claim a production store,
authorization broker, or provider isolation boundary exists.

Intended behavior lives in the
[product specification](docs/product/product-spec.md), the closed logical
records and relationships in the
[domain design](docs/designs/2026-08-03-domain-model.md), accepted constraints
in the [ADR index](docs/architecture/decisions/README.md), and observable
outcomes in the [validation case](docs/validation/cases/saturation.md).

## Architecture priorities

The immediate deliverable follows [ADR 0017](docs/architecture/decisions/0017-personal-terminal-alpha.md):
ordinary private personal persistence and a complete terminal manual loop before
protected custody. The architecture below describes the deferred protected
target; alpha records cannot satisfy its accepted-authority guarantees.
The next optional personal-AI scope is selected under
[ADR 0018](docs/architecture/decisions/0018-optional-personal-ai.md), retaining
ordinary private storage. Portable typed ingress now validates scoped response
items. The [offline selective-staging backend](docs/development/workflow.md#selective-proposal-staging-and-origin-return)
now retains item origins, minimal traces and personal explanation with the
existing versioned workspace/project checkpoint through personal recording and
return. The separate [offline terminal rehearsal](docs/development/workflow.md#selective-ai-items-in-the-terminal)
now connects contextual comparison/editing and personal explanation/return. Actual
provider/egress remains a prerequisite before live enablement. The
[BYO connection preparation](docs/development/workflow.md#personal-llm-configuration-and-unsent-preview)
now keeps endpoint/API/model/credential reference outside research checkpoints,
compiles complete bounded wire previews and validates untrusted API text through
the typed contract. Its separate configuration file stores no research history
or credentials. It opens no socket and confers no dispatch capability. This
supplies no protected authority or second research store.
The separate [internal asynchronous transport](docs/development/workflow.md#internal-asynchronous-transport)
now checks prepared requests and handles bounded cancellable I/O. Its short-lived
same-user child is a cancellation mechanism, not provider isolation. No public
live entry is enabled; public init/open can explicitly attach a private profile
for contextual unsent previews. Actual provider qualification and foreground review still
precede application dispatch. Its separate
[checked API controller](docs/development/workflow.md#checked-api-proposal-retention)
now reuses selective incorporation and versioned workspace v8/work v9/project v5
retention with owned synthetic returns. Restored history grants no live capability.
The existing contextual TUI now connects that controller's asynchronous polling,
selection/editing and terminal shutdown. The public qualification check refuses
before transport creation/key lookup; only owned tests replace it. No persisted
trust flag or command-line bypass qualifies a deployment.
The same private profile store now reads a separate closed Codex-login format,
without widening API v1. Its contextual preview binds exact application input;
CLI-generated HTTP content/destinations and runtime access are explicitly
unverified. It creates no client, consent, dispatched attempt or retained trace.
The Codex route refuses independently before API transport creation. A separate
[internal app-server adapter](docs/development/workflow.md#internal-codex-app-server-adapter)
now checks owned stdio returns through the existing typed ingress. It creates
a separate internal Codex controller for selective origin return, with distinct
workspace v9/work v10/project v6 retention alongside unchanged API/offline formats.
It restores no launch/consent capability. Actual authenticated access/egress and
useful live return remain L04 checkpoints. These paragraphs describe the earlier
component increments; the current checkout now connects the fixed Mac Codex
relay through the public personal entry, subject to runtime and exact request
checks. Final connected-use verification remains pending. The
[current candidate workflow](docs/development/workflow.md#mac-codex-connection-release-candidate)
owns setup and the [execution plan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#ai-connected-github-publication-order)
owns observed qualification; the published alpha.2 still has no live connection.

The contextual discussion slice under [ADR 0022](docs/architecture/decisions/0022-contextual-advice-and-explicit-edits.md)
adds a separately versioned advisory response to that same fixed relay. It
shares exact request ownership, attempt limits and cancellation with typed
proposals, while retaining question/answer and selected prior-message origin
in workspace v11/work v12/project v8. Advice has no graph staging capability.
Selected-passage origin v3 and explicit edit-request bindings now extend the same
store to workspace v12/work v13/project v9. Local forms retain incomplete fields
and AI origin; instruction returns use the unchanged typed v2 semantic validator
plus a four-item limit. The existing personal cause/origin registry now exercises
selected recording, correction and later derivation with this lineage; no new
schema is needed. Shared erasure checks protect required source text in both
live and reopened workspaces. The origin reader reconstructs historical input
from retained sources without I/O. Owned return/terminal/backup tests do not
qualify an actual live response or establish connected usefulness.

The planned personal-paper extension under
[ADR 0023](docs/architecture/decisions/0023-personal-argument-import-and-sharing.md)
separates reviewed prior-record registration and private raw-source retention
from scientific validation, provider context and a selected Git-share projection.
Its [domain contract and planned type extensions](docs/designs/2026-08-03-domain-model.md#personal-paper-lifecycle-extension-planned)
uses new purpose-bound profile/encoding/retention versions, preserving legacy
bytes and the protected authority boundary. Source originals and unknown origin
remain explicit; the share output is a reproducible projection of a saved
private revision, not a second writer or restore authority. The explicit manual paper-capacity subset now uses purpose-bound codecs and
separate personal frames with raw-source/public-ID registries. Source-claimed import and explicit source-aware personal reasoning now preserve
foreign origin independently of local Contributions. Replayable command-v6 source registrations now extend those same seed histories
without rebasing historical judgment context. Source identity/block freshness
is separate from scientific state and truth; private return uses distinct newer
envelopes/frames. Later protected integrations remain planned; larger storage qualifies no provider or
protected operation. The
[per-issue execution plan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan)
owns next-version sequencing and tests.

In order:

1. preserve accepted evidence and complete contribution provenance;
2. make human scientific and manuscript authority technically enforceable;
3. keep the accepted repository readable, recoverable, and useful with AI and
   the network disabled;
4. distinguish canonical science from derived context and execution traces;
5. make file failure, provider failure, and partial progress honest and
   recoverable; and
6. keep the first daily workflow fast enough that the graph reduces rather than
   creates research bookkeeping.

Personal command7 reporting revisions now use work17/project13/frame5 while
retaining old seed/command bytes and existing workspace fields. Human policies,
one companion record and source-bound placement/paragraph declarations remain
separate from scientific support; derived lint cannot create authority or close
debt. The [current workflow](docs/development/workflow.md#human-wording-limits-and-reporting-companions)
owns usage and coverage.

Personal command8 adds an exact co-report disposition with first-class scoped
Interpretations, one shared reason and the existing companion dependency store.
It advances the personal main head in one selected operation, without simulating
a branch merge. Work18/project14/frame6 retain old bytes and source influence;
[the current workflow](docs/development/workflow.md#co-reported-interpretations)
owns admission, origins and continued-review boundaries.

Personal command9 appends typed measurement revisions to the same global evidence
stream, with work19/project15/frame7 and unchanged legacy history bytes. Condition
queries/local graph coverage are disposable and cannot rewrite claim scope;
explicit one-file artifact checks cannot confirm scientific fidelity. The
[measurement workflow](docs/development/workflow.md#structured-measurements-and-condition-queries)
owns usage and bounds. No new provider/native authority is enabled.

Personal command10 adds immutable original protocol/rule versions, explicit
completed-record association and observation-revision-bound assessments.
Work20/project16/frame8 retains private return and older history bytes. Metadata
changes revoke exact review by advancing context without changing measured values;
chronology and consistency/validity stay separate, source-claimed and inspectable.
The [protocol workflow](docs/development/workflow.md#registered-protocols-outcomes-and-gate-amendments)
owns its current manual boundaries; no provider or protected authority is enabled.

Personal command11 adds non-empirical private sourced questions and associations.
Work21/project17/frame9 retains exact private capture inputs outside scientific
history in a typed source registry, with neutral/revision content in the graph.
Default reference projection is an opaque allowlist; full JSON export and provider
context refuse critique-bearing histories. Private backup is separately explicit
and retains originals. The [critique workflow](docs/development/workflow.md#private-critiques-and-sourced-questions)
owns the current boundary; selected sharing is a separate read-only public projection.

Canonical-share/v1 now projects explicitly selected seed4/5 science with disclosed
dependency closure, separate reason selection and saved opaque record IDs.
Per-kind allowlists exclude private source/critique/payload/path/manuscript state.
Keyed private-revision commitment plus exact recomputation verifies a projection;
it is not a signature, backup or standalone public-history proof. Reviewed
create-only output may live in Git while the canonical private workspace remains
outside it. No automatic commit, upload, provider request or import-back follows.
The [sharing workflow](docs/development/workflow.md#selected-canonical-git-sharing)
owns coverage and limitations.

The metadata registration boundary uses command12/work22/project18/frame10 to
separate new-input origin from human confirmation and preserve legacy command
meaning. A selected ordered batch reuses type handlers in detached candidates,
retains raw input privately and publishes once through existing saved-work storage.
Its graph action supplies local foreground comparison. Focused owned checks and
an actual Mac terminal rehearsal cover origin/authority separation, detached
registration, source/input rechecks and private return; the existing plan records
the broader release checks and their coverage. It grants no additional
provider or manuscript capability; see the
[registration workflow](docs/development/workflow.md#extended-metadata-registration).

The conditional-aware read-only association subset under
[ADR0028](docs/architecture/decisions/0028-conditional-aware-manuscript-selectors.md)
uses selector v2/source binding v3, command17/work28/project24 and private frame16.
Existing source bindings keep their original lexer until an explicit same-label
refresh. Metadata-batch/v2 selects labels without widening older formats; no TeX
execution or manuscript writer is introduced. The
[label workflow](docs/development/workflow.md#existing-latex-labels-without-manuscript-edits)
owns supported syntax and actual controls.

The precise-source subset under
[ADR0029](docs/architecture/decisions/0029-versioned-original-source-comparisons.md)
uses opt-in argument-import/v3, source-manifest/v2 and resolver/v2. Exact nested
source replay keeps compact scientific seed14/command14 unchanged; mandatory
work29/project25 and private frame17 prevent older formats acquiring new resolver
meaning. Shared-audit/conditional-label operations compose without format downgrade.
The [comparison workflow](docs/development/workflow.md#precise-source-comparison-and-markdown-sections)
owns narrow numeric, line and Markdown-section semantics; none verifies science.

Partial historical import under
[ADR0030](docs/architecture/decisions/0030-source-faithful-partial-historical-records.md)
uses separate seed18/ordinary command18 and work30/project26/private frame18.
[ADR0031](docs/architecture/decisions/0031-completed-experiment-protocols-and-result-replacements.md)
adds completed-target protocols and explicit observation replacements, carried by
command19 or exact nested import5, through work31/project27/private frame19.
Replacement is read-only scientific context until a separate evidence review;
its link origin is separate from numerical origin. Old prefixes stay unchanged.
[ADR0032](docs/architecture/decisions/0032-iterative-preparation-and-proportional-metadata-review.md)
adds private iterative preparation, proportional metadata review and scoped lexical
acknowledgements via command20/work32/project28/frame20, without scientific approval.
It retains source-bound compact nulls/absence pointers, collision-checked original
labels and independent declarations without widening older contracts. Shared-auditv2
and selected canonical-sharev3 carry honest missing fields through private/public
projections respectively; source originals remain private. No new authority or
manuscript capability follows from successful replay or saving.

## System context

    Researcher on the supported local workstation
        |
        | foreground review, rationale, teach-back, authorization
        v
    ClaimBranch local operator surfaces
        |-- public CLI
        `-- paper argument workspace with contextual Episode Review
                 |
                 v
          trusted command gateway
            |         |          |
            |         |          `--> manuscript saga --> isolated compiler
            |         |
            |         `--> proposal/context broker --> optional provider
            |
            `--> canonical operation store --> disposable projections

The paper Git repository remains researcher-owned. ClaimBranch's default
durable research workspace is project-specific and outside the application
and paper/code Git trees, under [ADR 0008](docs/architecture/decisions/0008-private-research-workspaces.md).
Project association and physical layout are P1 contracts, not implemented
storage. Raw artifacts remain at their linked source unless explicitly imported.
Git is transport and file history rather than the scientific authorization
mechanism or an implicit backup of private records. ClaimBranch never commits,
pushes, or promotes a live manuscript automatically.

## Three graph planes

The accepted [three-plane decision](docs/architecture/decisions/0006-three-graph-planes-and-provider-boundary.md)
prevents derived or model-generated relationships from acquiring scientific
authority.

| Plane | Contains | Authority and retention |
|---|---|---|
| Canonical scientific | append-only evidence events, branchable reasoning, Decisions, Contributions, debt, anchors, receipts, DomainOperations | only scientific source of truth; accepted writes pass the trusted gateway |
| Context/retrieval | typed neighborhoods, full-text index, summaries, future embeddings or communities | disposable and rebuildable; output is context, never implicit acceptance |
| Execution trace | Proposal revisions, request/response digests, model/tool identity, attempts, timings, cancellation, payload availability | append-only audit context; not scientific endorsement |

The UI may combine the planes, but it must display which plane and authority a
record belongs to. Projection loss or provider loss cannot make accepted state
unreadable or change its manifest.

Under [ADR 0011](docs/architecture/decisions/0011-paper-argument-graph-workspace.md),
the primary UI projects the paper thesis, main/subclaims, shared evidence and
experiments. The [model extension](docs/designs/2026-08-03-domain-model.md#paper-argument-extension-under-review)
now has a versioned portable candidate implementation; protected persistence
and complete operation/receipt integration remain open. Layout and
hover are disposable projections; hypothetical result/impact state is separate
from accepted observations. The UI cannot infer new scientific authority from
visual containment, connectivity or a scenario. Source-bound summaries and
human reasoning remain inspectable alongside the graph.
[ADR 0012](docs/architecture/decisions/0012-terminal-research-workspace.md)
places daily interaction in the experiment host's terminal. Keyboard focus,
typed-neighbor navigation and impact marks are terminal projections of the
same service; a separate graphical viewer is optional and unselected.

## Logical responsibility boundaries

These are responsibilities, not committed packages or processes.

| Boundary | Owns | Must not own |
|---|---|---|
| Domain kernel | closed records, invariants, impact closure, legal transitions, canonical hashing | storage, provider, browser, filesystem, global clock/entropy |
| Command gateway | capability checks, resource limits, idempotency, dispatch, receipt consumption | hidden business mutations outside domain handlers |
| Canonical store | atomic accepted operation append, replay, refs, verified restore | provider writes, derived projections, caller-selected actor authority |
| Proposal ingress | bounded non-authoritative Proposal/trace schemas | accepted operation types, human receipt, canonical database handle |
| Projection builder | rebuildable current, historical, search, and context views | source-of-truth status or fallback accepted writes |
| Authorization broker | sealed ReviewBundle verification, OS presence, receipt issue and private delivery | browser-held signing key or portable receipt |
| Context/egress broker | scoped reads, redaction, exact outbound preview, provider envelope and trace | human export, accepted commands, general filesystem access |
| Manuscript saga | anchor verification, fenced patch journal, isolated compile, exact restore | semantic merge or claims of graph/file atomicity |
| Operator adapters | public CLI and Episode Review translation | duplicate state machines or direct store writes |
| Validation | fixtures, model/state generators, crash matrices, V0 checker, workload measurements | production mutation outside an isolated destination |

The first implementation remains a modular single-user local program unless a
security spike proves that one or more model, broker, or compiler processes
must be separately sandboxed. A daemon, distributed service, plugin runtime, or
microservice boundary requires post-V0 evidence.

## Accepted-state path

Only the trusted command gateway can create an accepted DomainOperation.

    capture manually or receive Proposal
        -> prepare mutable ReviewBundle
        -> show exact operation, impact, provenance, rationale, and consequence
        -> seal immutable digest
        -> broker reloads and verifies sealed bundle
        -> foreground OS-backed human presence
        -> short-lived single-use receipt delivered privately to gateway
        -> validate expected heads, file hash, rules, limits, and receipt
        -> append operation plus receipt consumption atomically
        -> rebuild or update disposable views

A request field that says the actor is human does nothing. Model/provider
processes have no accepted-store handle, human export capability, signing key,
or human-only command. The saturation fixtures must prove those denials outside
caller-controlled request data.

## Research episode boundary

One ResearchEpisode partitions a single unexpected-result workflow. It records
the project, eligibility-rule version, initial refs and evidence watermark,
clocks, lifecycle, and ordered operations. H0 histories use isolated stores.
V0 uses one cumulative project with at most one active episode, so later
episodes may reference earlier accepted claims without recreating them.

The exact finite record inventory, relationship set, operations, cardinalities,
and resource limits are canonical in the
[domain design](docs/designs/2026-08-03-domain-model.md). Anything outside that
contract becomes an explicit out-of-F0 product result during V0 rather than an
automatic schema expansion.

## Read and provider boundary

Human export and model-readable context are separate capabilities. The context
compiler applies project, record-kind, field, sensitivity, count, and byte
allowlists. It withholds raw artifact bytes, secrets, absolute paths, retained
provider payloads, and manuscript text that was not selected for the request.

Every provider attempt produces or visibly fails one versioned Proposal
envelope and trace manifest. Provider output cannot invoke a canonical command.
Remote-capable egress requires a one-shot review of exact destination, content,
redactions, and digest. A loopback endpoint is local-only only when its address
is pinned, redirects and DNS are disabled, and the process is denied external
network access; otherwise the same outbound-review policy applies.

The H1 local-serving path connects to an already-running OpenAI-compatible
endpoint and explains compatibility, model identity, context ceiling,
structured output, cancellation, time to first token, usage, and throughput
when available. ClaimBranch does not install, download, quantize, supervise,
route, update, or choose models. AI-off and a deterministic stub remain the
correctness baseline.

[ADR 0009](docs/architecture/decisions/0009-external-inference-and-local-authority.md)
separates the externally operated inference service from any restricted local
tool worker and the trusted accepted-state writer. These responsibilities do
not prescribe three services or add a generic agent runtime. A sandbox around
the connector proves nothing about an unrestricted external server's file
permissions. Before live use, validate the actual server topology separately
from API compatibility and egress consent; unavailable protection must not
downgrade the authority gate. The current disposable helper is not that proof.

## Browser authorization boundary

The existing browser prototype and any retained graphical adapter use a
short-lived loopback server launched by a public command. The daily workspace
is now terminal-based under ADR 0012; its protected server authority is not
implemented. If a browser participates in protected review, its required
protocol remains:

- random loopback port and one-use high-entropy bootstrap;
- immediate exchange for a secure, HttpOnly, same-site session and a clean URL;
- exact Host and Origin checks, no wildcard CORS, per-session CSRF defense,
  frame denial, and no referrer disclosure;
- no signing material or portable authorization receipt in browser JavaScript;
- broker-side reload and digest verification of the sealed ReviewBundle;
- OS-backed foreground presence plus an ACL-protected private receipt path to
  the kernel; and
- explicit session expiry, reconnect, no-open, browser-launch failure, port
  collision, multiple-instance, and clean-stop behavior.

If the target-platform spike cannot prove meaningful user presence and private receipt
delivery, H1 uses a native or CLI foreground helper. It does not downgrade to a
plain browser click.

## Manuscript path and partial progress

Graph acceptance does not imply manuscript success. The visible phases are:

    graph accepted
      -> manuscript debt open
      -> patch prepared
      -> applying
      -> applied, not verified
      -> compiling
      -> verified
      -> separate human debt closure

Failure may restore exact original bytes or enter recovery_required. It never
shows global success merely because the graph operation committed.

The [episode and saga decision](docs/architecture/decisions/0007-research-episode-and-manuscript-saga.md)
requires one active writer per project/file/anchor, a monotonic fencing token,
expected graph/file/debt state at every boundary, an authenticated encrypted
preimage, known postimage digest, target-tested write/replace/flush ordering,
and a compiler isolated to an owner-only copy/output tree with a pinned argument
vector and shell escape disabled.

External edits, competing processes, supersession, missing key, disk full,
unexpected compiler side effects, or divergent bytes stop blind retry. Exact
restoration is verified byte-for-byte; otherwise only inspect, export, and
evidence-backed restore remain available.

## Storage, projection, and migration hypotheses

The logical operation log is authoritative and canonical serialization must be
deterministic. Physical choices remain hypotheses until bounded spikes:

- a repository-local package and public CLI are the distribution hypothesis;
- SQLite is the first atomic-store and traversal baseline;
- typed neighborhood plus optional full-text search is the first retrieval
  baseline;
- the daily terminal workspace follows ADR 0012; a graphical adapter remains
  optional rather than a required loopback surface; and
- one pinned target-platform LaTeX workflow is selected only after marker and
  compiler tests.

SQLite or another store is accepted only after replay, crash, concurrency,
resource, workload, import, and migration fixtures pass. A graph database is
not implied by the logical graph. Embeddings and GraphRAG are admitted only by
the retrieval trigger in the active ExecPlan.

Before live data, schema migration is copy-on-write: check compatibility and
space, lock, create a verified export, build and verify a new store, atomically
select it, and retain the original. Older code may inspect status, diagnosis,
and export for a newer store but cannot mutate it. No automatic updater,
destructive in-place migration, or bidirectional framework exists in F0.

## Operator and deployment boundary

The first implementation target is the available Apple Silicon Mac under
[ADR 0010](docs/architecture/decisions/0010-macos-first-platform-adapters.md);
Windows 11 x64 follows with separate platform evidence. Each uses a standard
user, a local paper repository and source checkout, Git-tracked LaTeX paper,
and one supported review surface. Exact builds,
runtime/compiler versions, OS presence, platform-specific process isolation,
path and reparse behavior, controlled-folder access, antivirus sharing, and
credential storage are frozen by the P1 platform spike.

The public H0 path is one repository-owned bootstrap, doctor, and disposable
offline demo. It requires no administrator, provider, compiler, or real-paper
write and targets five minutes from the declared clean-checkout state. Planned
commands are not working instructions until implementation and validation land.

The [source-delivery gate](docs/product/releases/validation-prototype.md#55-source-delivery-readiness)
requires a reproducible GitHub checkout/artifact and independent research use,
including durable restart and recovery on the supported Mac. It does not depend
on completing the deferred Windows adapter or adding a public installer. The
current volatile synthetic surface does not meet that gate.

[ADR 0017](docs/architecture/decisions/0017-personal-terminal-alpha.md)
now makes first delivery a personal manual terminal workspace with ordinary
private files, explicit personal confirmation, restart and local backup/restore.
It has no application encryption, device keys or signed protected authority.
The protected boundaries above remain future targets; personal records cannot
acquire their authority by importing or relabeling. Live inference, automatic
manuscript writing, hardware custody and authority migration are deferred.

No remote service, public installer, auto-update, daemon, OpenClaw gateway,
MCP server, model manager, or hosted telemetry belongs to H0/H1.

## Quality and verification

The implementation must provide:

- 100% branch coverage for deterministic domain/gateway code plus property and
  model tests for all legal and illegal finite transitions;
- byte-stable replay for separate AI-off and frozen-proposal goldens;
- authority, exfiltration, loopback, import, and prompt-injection negative tests;
- fault injection at every canonical append and patch/replace/compile/restore
  durability boundary;
- exact human-only understanding and manuscript debt closure tests;
- clean-checkout, path-matrix, CLI/help/error, unfamiliar-user, and migration
  journeys before V0;
- seeded 1x and 10x graph workloads with explicit latency, memory, database,
  journal, and temporary-space budgets; and
- a preregistered live-paper checker that assigns exactly one frozen outcome.

Executable evidence now includes the source-fixture checker, synthetic contract
models, a portable review/provenance/debt-candidate core with global evidence,
temporal reasoning views, selected merges and frozen-history replay, disposable
platform/storage probes and a synthetic A1–A4 integration. The Mac presence
experiment uses an ephemeral key; persistent custody, private delivery and
complete isolation remain unproven.
The source-checkout application now connects that candidate core to a volatile
Episode Review and offline-only context broker. Its loopback HTTP session has
one-use fragment bootstrap, exact Host/Origin, CSRF, expiry, bounded requests
and revision conflict checks. It cannot issue approval or accepted writes.
This synthetic surface does not satisfy the production HTTPS/Secure-cookie,
private IPC or durable-state requirements above. Episode/provider/manuscript
lifecycle values validate supplied transitions; they do not observe OS effects.
The [contributor workflow](docs/development/workflow.md) owns their commands and
limits. These do not establish production coverage of the target above. The
[active ExecPlan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns observed results, sequencing, planned commands, failure matrices and
trigger thresholds.

## Deferred architecture

General semantic VCS, arbitrary branch merge/revert, a universal ontology,
unrestricted graph editing, GraphRAG, graph-native storage, background daemon,
OpenClaw/MCP adapter, public installers/auto-update, model-server operations, broader platform support,
collaboration, mobile, SaaS, and multi-tenant permissioning all require
post-validation evidence and a new or updated ADR/ExecPlan.

The bounded paper argument workspace and reproducible source-delivery path are
current requirements; they are not deferred by this list.

When code establishes real containers or deployment units, reconcile this
draft with observed structure before changing its status or presenting it as
current architecture.
