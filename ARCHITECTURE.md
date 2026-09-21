---
kind: target-architecture
status: draft
owners: maintainers
last_reviewed: 2026-09-21
canonical_for: target pre-implementation system boundaries and quality constraints
---

# ClaimBranch target architecture

ClaimBranch has no usable application or settled stack. Repository contract
models and disposable probes provide bounded evidence, not the implemented
target architecture. This document defines boundaries and quality constraints
that the first finite slice must test; it does not claim a production store,
authorization broker, or provider isolation boundary exists.

Intended behavior lives in the
[product specification](docs/product/product-spec.md), the closed logical
records and relationships in the
[domain design](docs/designs/2026-08-03-domain-model.md), accepted constraints
in the [ADR index](docs/architecture/decisions/README.md), and observable
outcomes in the [validation case](docs/validation/cases/saturation.md).

## Architecture priorities

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

## System context

    Researcher on supported native Windows
        |
        | foreground review, rationale, teach-back, authorization
        v
    ClaimBranch local operator surfaces
        |-- public CLI
        `-- command-launched Episode Review
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

The preferred H1 review surface is a short-lived loopback server launched by a
public command. Its required protocol is:

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

If the Windows spike cannot prove meaningful user presence and private receipt
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
preimage, known postimage digest, Windows-tested write/replace/flush ordering,
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
- a short-lived loopback browser is the H1 surface hypothesis; and
- one pinned native-Windows LaTeX workflow is selected only after marker and
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

The initial support hypothesis is one standard-user native Windows 11 x64
workstation, local NTFS paper repository, PowerShell source checkout, Git-
tracked LaTeX paper, and one current supported browser. Exact builds,
runtime/compiler versions, OS presence, AppContainer or fallback isolation,
path and reparse behavior, controlled-folder access, antivirus sharing, and
credential storage are frozen by the P1 platform spike.

The public H0 path is one repository-owned bootstrap, doctor, and disposable
offline demo. It requires no administrator, provider, compiler, or real-paper
write and targets five minutes from the declared clean-checkout state. Planned
commands are not working instructions until implementation and validation land.

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

Current implementation coverage is zero. The only executable check today is
the documentation checker. The [active ExecPlan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns sequencing, planned commands, failure matrices, and trigger thresholds.

## Deferred architecture

General semantic VCS, arbitrary branch merge/revert, a universal ontology,
graph canvas, GraphRAG, graph-native storage, background daemon, OpenClaw/MCP
adapter, public packaging, model-server operations, cross-platform support,
collaboration, mobile, SaaS, and multi-tenant permissioning all require
post-validation evidence and a new or updated ADR/ExecPlan.

When code establishes real containers or deployment units, reconcile this
draft with observed structure before changing its status or presenting it as
current architecture.
