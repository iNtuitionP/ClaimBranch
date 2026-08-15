---
kind: design
status: draft
owners: maintainers
last_reviewed: 2026-08-14
canonical_for: proposed finite F0 domain records relationships operations states and resource bounds
---

# Finite F0 domain and versioning model

Version: 0.2

This document is the canonical logical contract proposed for the first
ClaimBranch spike. It defines a finite saturation-shaped graph, authority,
provenance, state, replay, and resource boundary. It is not an implemented
schema and does not settle a programming language, database, package layout,
wire framework, or UI storage.

The [product specification](../product/product-spec.md) owns intended behavior,
the [target architecture](../../ARCHITECTURE.md) owns component and trust
boundaries, the [saturation case](../validation/cases/saturation.md) owns
observable content, and the
[active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns sequencing and planned test commands.

## Purpose

Make the first graph-first foundation closed enough that an implementation can:

- accept only known records, edges, operations, states, and resource sizes;
- keep evidence global and reasoning branchable;
- preserve complete AI/human Contribution provenance;
- prove human authorization without trusting caller data;
- distinguish scientific acceptance from manuscript progress;
- replay deterministic histories without AI;
- reject out-of-F0 live cases visibly; and
- test every allowed and forbidden path before broadening the model.

“Complete” means complete for this fixture-bounded contract, not complete for
science or future ClaimBranch.

## Context and current state

ADRs 0001, 0003, 0005, 0006, and 0007 accept the evidence/reasoning,
proposal-only AI, human-authority, three-plane, episode, and manuscript-saga
constraints. There is no implemented schema, store, gateway, provider adapter,
authorization broker, projection, or patch saga. The earlier broad domain draft
has been narrowed to the one approved saturation wedge so the first spike can
be exhaustive rather than nominally general.

## Goals and non-goals

Goals:

- close every F0 semantic type, relationship, command, state, cardinality, and
  resource boundary;
- make accepted authority and AI Contribution provenance executable;
- make replay, import, projection, migration, and manuscript recovery
  falsifiable; and
- preserve a clear path to record out-of-F0 live evidence without expanding the
  contract during evaluation.

Non-goals:

- universal scientific ontology or arbitrary extension fields;
- general semantic VCS, nested branches, LCA merge, revert, or conflict solver;
- graph database or event-sourcing framework commitment;
- embeddings, GraphRAG, model memory, or graph canvas;
- multi-file manuscript editing;
- collaboration or multi-user authority; and
- model/provider management.

## Decision drivers

- The first foundation must be finite enough for exhaustive positive, negative,
  crash, replay, and resource tests.
- Accepted evidence must remain global while one competing interpretation can
  branch and merge selectively.
- Human authority must not depend on untrusted request metadata or provider
  behavior.
- AI influence and understanding obligations must survive human editing.
- External manuscript writes must not inherit false atomicity from graph
  commits.
- Physical storage and UI technology must remain replaceable until spikes pass.

## Options considered

- Keep the earlier broad ontology and general semantic-VCS model. Rejected
  because exhaustive authority, recovery, and live-evaluation outcomes would
  remain undefined.
- Build a minimal agent flow first and let the schema emerge from UI behavior.
  Rejected because authority and provenance would become accidental interface
  conventions.
- Freeze every future scientific type before implementation. Rejected because
  it would substitute speculation for real episode evidence.
- Close only the saturation-shaped F0 contract and count valid live cases
  outside it as product failures. Selected.

## Proposed design

## 1. Logical planes

The model uses the three planes accepted by
[ADR 0006](../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md).

### 1.1 Canonical scientific plane

Accepted append-only evidence events, branchable reasoning, Decisions,
Contributions, ReviewBundle/receipt references, debt, anchors, patch-saga
results, refs, and DomainOperations. This plane alone defines accepted research
state.

### 1.2 Context/retrieval plane

Rebuildable current/historical views, typed neighborhoods, full-text indexes,
summaries, and future retrieval derivations. It contains no independent
accepted fact.

### 1.3 Execution-trace plane

Non-authoritative Proposals, revisions, request/response/tool manifests,
attempts, timing, cancellation, retention, and payload availability. This
plane is auditable but does not endorse its content.

## 2. Global invariants

### INV-1: accepted evidence is branch-independent

Every accepted ArtifactRef, Run, Observation, and EvidenceEvent is visible from
every reasoning ref at the applicable evidence watermark. Branch creation,
archive, or selected merge cannot hide or delete it.

### INV-2: evidence changes append events

Confirmation, correction, invalidation, and retraction append EvidenceEvents.
No command edits an accepted artifact, Run, Observation, or prior event in
place.

### INV-3: accepted state changes only through a closed operation

The trusted gateway validates and atomically appends a known DomainOperation.
No raw record write, caller-selected actor, provider output, projection, import,
or internal field update is an alternate accepted-write path.

### INV-4: relationships are typed records

Every scientific relationship uses the closed table in section 5 and retains
its source, target, rationale, conditions implicit in the typed fixture fields,
creation operation, and evidence watermark. Topology or similarity alone cannot
create an accepted edge.

### INV-5: AI influence is never erased

Every AI-influenced accepted DomainOperation references the immutable Proposal
and a gap-free ordered Contribution chain. Human edits add Contributions; they
do not relabel the result purely human.

### INV-6: human authority is cryptographic and state-bound

Every human-only accepted action consumes one unexpired, single-use receipt
bound to the sealed review, project, episode, expected heads/file state,
operation, impact, provenance, rationale, and teach-back disposition. Request
metadata never substitutes for the receipt.

### INV-7: selected merge is explicit and dependency closed

F0 copies one named selection plus its mandatory dependencies from one
non-nested branch to main. It records omitted work and does not mutate the
source branch.

### INV-8: graph acceptance and manuscript verification are distinct

A graph operation may open ManuscriptDebt. Patch preparation, file application,
compile verification, restoration, and human closure remain separate durable
phases.

### INV-9: projections and providers are disposable dependencies

Deleting every projection or disabling every provider cannot alter or make
accepted state unreplayable.

### INV-10: import cannot inherit authority implicitly

Untrusted history is verify-only in a new isolated store. Trusted restore
targets a new empty store and verifies a signed manifest chain, enrolled public
key, known schema/rules, hashes, and every receipt. F0 has no import-to-live-
project merge or promotion path.

## 3. Common record contract

Every canonical record has:

| Field | Rule |
|---|---|
| id | stable unique string within the project |
| kind | closed enum selecting its schema |
| schema_version | known version; unknown versions fail before append |
| project_id | exact project authority boundary |
| created_operation_id | immutable creating DomainOperation |
| created_at | RFC 3339 UTC supplied by the deterministic clock port |

Every record and command payload validates against versioned JSON Schema with
additional properties forbidden. Schemas close primitive types, enums,
nullability, numeric ranges, strings, collections, and cross-record
invariants. Indexes may add physical fields outside canonical serialization;
they cannot add semantic fields.

Canonical JSON uses fixed UTF-8 normalization, object-key order, number format,
enum spelling, null treatment, and hash exclusions. Tests inject clock, IDs,
nonces, signing key, compiler fingerprint, schema/rule versions, and production
entropy recordings. Replay never regenerates them.

The immutable operation/event log is authoritative. Ref heads and lifecycle
values are deterministic projections, not mutable fields inside prior hashed
records.

## 4. Closed record inventory and cardinality

| Record kind | Required type-specific fields | H0 exact / V0 per-valid-episode bound |
|---|---|---|
| ResearchEpisode | eligibility_rule_version, baseline_ref_heads, baseline_evidence_watermark, opened_at | H0 exactly 1; V0 project 0-6 total, first 3 valid starts when available and at most 3 invalidated replacements |
| ArtifactRef | uri_or_relpath, sha256, media_type, sensitivity | exactly 2: result and manuscript |
| Run | run_key, method_ref, started_at, completed_at, status | exactly 1 completed |
| Observation | statement, value_or_category, units, run_id | exactly 3 |
| EvidenceEvent | action, target_id, rationale, nullable supersedes_id | exactly 3 confirmations plus at most 3 correction/invalidation/retraction events; total 3-6 |
| Claim | statement, scope, status | exactly 1 central Claim |
| Interpretation | statement, branch_ref, evidence_watermark | exactly 1 |
| ScientificEdge | edge_type, source_id, target_id, rationale | 3-6 from the closed edge table |
| ExperimentPlan | objective, claim_id, status | zero or one |
| Decision | decision_type, selected_ids, rationale, branch_ref | 1-3 including selected-merge Decision |
| ManuscriptAnchor | file_relpath, marker_id, fingerprint, expected_file_hash | exactly 1 |
| PatchIntent | anchor_id, expected_file_hash, replacement_digest, reason | exactly 1 |
| PatchAttempt | patch_intent_id, snapshot_digest, result_file_hash, compile_config_id | 1-3; happy path has exactly one verified result |
| ManuscriptDebt | anchor_id, cause_id | exactly 1 identity; lifecycle is projected |
| UnderstandingDebt | accepted_operation_id, review_bundle_id | manual 0; recorded exactly 1; lifecycle is projected |
| DomainOperation | episode_id, operation_type, actor_class, expected_ref_heads, evidence_watermark, payload, idempotency_key | 1-32 accepted transitions, at most 24 receipt-authorized |
| Ref | name | exactly 2: main and one non-nested branch |
| SelectedMerge | source_ref, target_ref, base_operation_id, selected_ids, closure_ids, expected_heads | exactly 1 |
| Proposal | episode_id, nullable parent_proposal_id, intended_command, normalized_payload, trace_manifest_id | manual 0; recorded 1 root/0 revisions; H1/V0 0-3 total, one root plus at most 2 human-requested revisions |
| Contribution | target_operation_id, sequence, contributor_class, action, nullable proposal_id | 1-64 per episode, at most 8 per target; proposal_id required for AI influence |
| ReviewBundle | episode_id, revision, nullable parent_bundle_id, draft_operation_digest, expected_heads, impact_digest, provenance_digest, rationale, teachback_disposition, sealed_at | one immutable sealed revision per authorization; at most 3 revisions per command and 72 per episode |
| AuthorizationReceipt | review_digest, project_id, episode_id, session_nonce, authorized_operation_id, expected_heads, issued_at, expires_at, signature | exactly one per authorized command, at most 24; unique operation proves single consumption |
| ExecutionTraceManifest | request_digest, response_digest, model_identity, tool_context_digest, payload_availability, retention_class | manual 0; recorded 1; H1/V0 0-3, exactly one per provider-produced Proposal/revision |

Cardinality counts identities created by an episode, not preexisting records it
references or append-only transition attempts. Every DomainOperation carries
episode_id and every canonical record derives its episode from
created_operation_id.

Start-episode atomically creates the preallocated ResearchEpisode ID and its
root operation, avoiding circular identity. H0 variants use separate stores.
V0 uses one cumulative live project, at most one active episode, and recorded
starting refs/watermark. An episode may reference an earlier Claim without
recreating it.

The fixture may omit ExperimentPlan. No other record kind or extra branch is
admitted. A valid episode exceeding any maximum is out-of-F0, incomplete, and
not eligible for replacement.

## 5. Closed relationship inventory

Every relationship is a ScientificEdge or a named structural reference on its
owning record. Free-form labels are invalid.

| Relationship | Source -> target | Cardinality and invariant |
|---|---|---|
| uses_artifact | Run -> ArtifactRef | one or more; result artifact has one incoming use |
| produced | Run -> Observation | exactly 3; each Observation has one producer |
| evidence_targets | EvidenceEvent -> ArtifactRef, Run, or Observation | exactly one target per event |
| interprets | Interpretation -> Observation | 1-3, resolved at its watermark |
| supports, challenges, qualifies | Observation or Interpretation -> Claim | at least one challenges; rationale required |
| tests | ExperimentPlan -> Claim | exactly one when plan exists |
| decides | Decision -> Claim, Interpretation, SelectedMerge, or PatchIntent | one or more selected targets |
| expresses | ManuscriptAnchor -> Claim | exactly one |
| patch_targets | PatchIntent -> ManuscriptAnchor | exactly one |
| attempts | PatchAttempt -> PatchIntent | exactly one; ordered |
| debt_concerns | ManuscriptDebt or UnderstandingDebt -> accepted record/operation | exactly one direct cause; transitive impact derived |
| proposes | Proposal -> draft DomainOperation | exactly one intended operation |
| contributes_to | Contribution -> DomainOperation | exactly one target; sequence gap-free |
| reviews | ReviewBundle -> draft DomainOperation | exactly one digest-bound draft |
| authorizes | AuthorizationReceipt -> ReviewBundle | exactly one; single use |
| records | ExecutionTraceManifest -> Proposal | exactly one root Proposal/revision |
| selects | SelectedMerge -> accepted reasoning record | explicit IDs plus mandatory closure |

The operator conditions in the saturation case live in Observation statements
and edge rationale. F0 does not add a generic condition-node taxonomy.

## 6. Closed operation and capability inventory

| Operation | Capability | Canonical effect |
|---|---|---|
| inspect, compute-impact, diagnose | human read or scoped model query | none; model receives bounded redacted fields, no raw artifact bytes/general paths |
| export | human-only out-of-band export | none in source; creates bounded manifest outside model reach |
| rebuild-projection | maintenance | replaces disposable projection only |
| capture-proposal, revise-proposal, reject-proposal, cancel-proposal | model proposal ingress or human | appends bounded non-authoritative Proposal/trace/disposition data |
| start-episode, close-episode, invalidate-episode | foreground human or frozen V0 runner | changes bounded episode lifecycle; invalidation needs preregistered protocol reason |
| import-truth-packet | human authorization | creates the bounded initial accepted records |
| record-evidence-event | human authorization | appends confirmation/correction/invalidation/retraction |
| create-reasoning-branch, record-interpretation, record-decision | human authorization | changes only branchable reasoning state |
| prepare-review, seal-review | foreground review session | creates/seals ReviewBundle; no accepted mutation |
| authorize-review | human authorization broker only | issues one short-lived receipt after foreground presence |
| materialize-proposal | kernel plus matching unconsumed receipt | creates accepted DomainOperation and Contribution chain |
| apply-selected-merge | kernel plus matching unconsumed receipt | copies the explicit dependency closure into main |
| answer-teachback, defer-teachback, close-understanding-debt | human authorization | records answer/deferral or human-only closure |
| derive-manuscript-debt | deterministic kernel inside accepted operation | atomically opens/updates debt from accepted impact; no public standalone write |
| prepare-patch, apply-patch | human authorization | starts/runs bounded fenced manuscript saga |
| verify-compile, restore-patch | bounded saga with prior human authority | records pinned result or exact restore/hard stop |
| close-manuscript-debt | kernel plus closure-specific receipt | closes exact verified debt/patch/compile tuple |
| replay, import, verify-manifest | maintenance on new isolated destination | reconstructs/verifies trusted or untrusted history, never appends to source/live project |

Anything else is forbidden. The gateway assigns actor, project, episode, schema,
and allowed operation; proposal callers cannot choose a canonical table,
operation type, or human class.

## 7. ResearchEpisode lifecycle

Projected states:

    allocated -> active -> closed
                      `-> invalidated

Only one episode is active per V0 project. Invalidation is allowed only for a
preregistered eligibility error discovered after start or corrupted timing.
Product failure, abandonment, provider failure, anchor failure, authorization
failure, resource overflow, or out-of-F0 after a valid start cannot invalidate
or replace it.

At most three protocol-invalid replacements exist. Attempting a fourth ends V0
as inconclusive without unbounded event append.

## 8. Evidence and temporal views

EvidenceEvent actions are:

    confirm | correct | invalidate | retract

Correction requires supersedes_id. Invalidation/retraction retains reason and
target. Current view resolves a ref against the latest accepted evidence
watermark. Historical view resolves a stored ref/head at its stored watermark.
Re-evaluating historical reasoning with current evidence creates a new
operation; it does not rewrite the historical view.

## 9. Proposal, Contribution, and trace

Proposal disposition is projected from operations:

    pending | revised | rejected | cancelled | selected_for_review | expired

Proposal content is never moved in place into accepted storage. Materialization
creates a new accepted DomainOperation and immutable Contribution sequence.

Contribution contributor_class is:

    human | ai | deterministic

Contribution action is a closed enum covering proposal, edit, adoption,
derivation, and correction. An operation is AI-influenced when any Contribution
in its transitive source chain references a Proposal. That derived status is
not a mutable tag.

ExecutionTraceManifest retains digests, model identity, tool-context digest,
retention class, and payload availability even when raw provider content is
eligible for erasure. Missing payload is explicit and does not prevent accepted
operation replay.

## 10. Review, authorization, and debt

A ReviewBundle is mutable only before sealing. Sealing creates an immutable
revision bound to:

- project and episode;
- exact draft operation digest;
- expected ref heads and evidence watermark;
- expected manuscript file hash when relevant;
- schema and rule versions;
- impact and Contribution/provenance digests;
- human rationale;
- teach-back answer or deferral;
- session nonce and expiry; and
- previous revision identity.

Any bound change makes it stale and requires a new revision. The broker
independently reloads the sealed bundle, recomputes these values, obtains
foreground user presence, and sends the receipt privately to the gateway.
Receipt consumption and accepted operation append share one transaction.

UnderstandingDebt states:

    open -> closed_by_human
        `-> superseded

It exists only when a high-impact AI-influenced accepted operation defers
teach-back. Not now creates no accepted operation and no debt. Closure requires
a separate receipt for the exact debt and current accepted head; AI cannot
grade or close it.

ManuscriptDebt states:

    open -> patch_prepared -> applied_unverified -> verified -> closed_by_human
      |           |                 |
      `-----------+-----------------+-> superseded

Restore does not close debt. Closure binds debt ID, PatchIntent, PatchAttempt,
source/output/compiler/config digests, graph head, fencing token, and
non-restored saga state.

## 11. Ref and selected-merge contract

Refs are main and one non-nested branch. Heads are projections over
DomainOperations. F0 does not compute a general LCA, nested ancestry, rebase,
conflict resolution, or revert.

SelectedMerge contains:

- source and target refs;
- frozen base operation and expected heads;
- explicit selected IDs;
- deterministic mandatory closure IDs;
- omitted IDs;
- evidence watermark;
- Decision/rationale; and
- resulting target head.

Mandatory closure includes referenced new Interpretation/ExperimentPlan,
required ScientificEdges, their endpoints, and resulting ManuscriptDebt. Global
evidence already exists and is referenced, not copied. Higher-level scientific
advice cannot add undeclared records automatically.

## 12. Impact closure

Impact is the deterministic transitive set reachable from a changed F0 record
through the allowed edge/reference directions to:

- the one Claim;
- Decisions and SelectedMerge;
- the ManuscriptAnchor and ManuscriptDebt; and
- applicable UnderstandingDebt.

The traversal uses the sealed ref heads and evidence watermark, returns typed
paths and omitted/blocked items, and never follows Proposal, similarity, or
execution-trace links as accepted science. The saturation truth set requires
100% recall and at most one false-positive debt bundle at fixture scale.

## 13. Manuscript saga

PatchIntent and PatchAttempt project these phases:

    debt_open
      -> patch_prepared
      -> applying
      -> applied_unverified
      -> compiling
      -> verified

Failure from applying, applied_unverified, or compiling moves to
restored_after_failure only after exact byte equality is proved, otherwise to
recovery_required. Recovery_required dominates all other surfaces and permits
only inspect, export, and evidence-backed restore.

One active saga exists per project/canonical-file/anchor. A monotonic fencing
token, expected file identity/hash, ref heads, debt, PatchIntent, and compiler
fingerprint are rechecked before every side effect and finalization. The
write-ahead record is durable before mutation and includes authenticated
encrypted preimage metadata plus expected full postimage digest. Compile uses a
pinned argument vector in an isolated output copy; verified outputs alone may
be promoted.

Detailed platform ordering is owned by
[ADR 0007](../architecture/decisions/0007-research-episode-and-manuscript-saga.md)
and must be proven on the supported Windows filesystem.

## 14. Resource limits

These are safety limits for the contract spike, not measured product capacity.
Schemas and ingress enforce them before allocation or append. A spike may lower
them but cannot silently raise them.

| Resource | F0 maximum |
|---|---:|
| stable ID / enum / hash text | 128 UTF-8 bytes / 64 bytes / 128 bytes |
| normalized relative path or URI | 1,024 UTF-8 bytes |
| statement, rationale, answer, diagnostic message | 16,384 UTF-8 bytes |
| semantic collection | 128 items unless a smaller count is specified |
| canonical DomainOperation JSON | 262,144 bytes |
| truth-packet manifest | 1 MiB |
| normalized Proposal or outbound context | 256 KiB each |
| retained provider request/response blob | 2 MiB each; 8 MiB per revision; 24 MiB per episode |
| manuscript source, encrypted snapshot, or postimage | 16 MiB each; one marked file |
| provider calls | 2 attempts per revision, at most 6 per episode |
| patch/compile attempts | at most 3 per PatchIntent |
| rejected validation/authorization diagnostics | first 128 detailed attempts; then saturating per-code counters without payload append |
| V0 project ResearchEpisodes | 6 total: at most 3 valid and 3 invalid replacements |
| non-authoritative trace/snapshot ledger | 256 MiB per project |

ResourceLimitError is the single overflow result. After a detailed-attempt or
ledger cap, repeated untrusted calls update only a saturating counter and cannot
grow retained payloads. Overflow rejects the new proposal/patch work without
accepted-state change. Artifact bytes remain external references and are never
silently copied into the store.

## 15. Public state derivation

Product UI state is derived, not canonical. Four orthogonal projections cover:

- workspace review phase;
- provider attempt phase;
- manuscript saga phase; and
- projection health.

Legal events generate the reachable tuples. Impossible combinations are
rejected during load and render; no raw Cartesian-product flags are persisted.
Authorization cannot precede a sealed review, remote loading cannot precede
exact consent, accepted-review-pending requires open UnderstandingDebt,
manuscript progress requires an accepted PatchIntent, and verified requires the
matching pinned compile record.

The product specification owns the visible copy and ordering. Model-based tests
own exhaustive transition reachability.

## 16. Projection, import, and migration

Current, historical, search, context, and UI projections rebuild from canonical
operations plus retained non-authoritative trace references. Rebuild writes
beside the last valid projection and swaps only after verification. Failure
keeps the prior valid projection readable and cannot write accepted state.

Trusted export contains a signed manifest chain and project-authority public
key, never private key material. Trusted restore verifies the full chain in a
new empty store. Untrusted import remains labeled historical claims in a new
isolated store. F0 cannot merge either into an existing live project.

Schema migration is copy-on-write to a new store: compatibility and space check,
exclusive lock, verified export, destination build, full manifest
verification, atomic selected-store change, and retained original. Every
durable boundary has an interruption fixture. Older readers may offer read-only
status, diagnosis, and export for newer stores but cannot mutate them.

## Validation

The design advances only when named fixtures prove:

1. every record, edge, operation, enum, field, bound, and cross-invariant accepts
   its valid cases and rejects unknown/invalid cases;
2. H0-manual and H0-recorded each replay to their own full-audit golden without
   a provider call;
3. evidence watermarks and current/historical views are deterministic;
4. selected merge is dependency closed and preserves global evidence;
5. Proposal/Contribution/trace and both debts retain exact authority;
6. model query/export/egress/proposal ingress/accepted store boundaries fail
   under hostile inputs;
7. every reachable UI tuple and legal event is generated and all others reject;
8. every manuscript crash/concurrency/supersession state restores exactly or
   reaches the sole hard stop;
9. projection rebuild, import, restore, and migration preserve the expected
   manifest and trust label; and
10. 1x and 10x seeded workloads meet the active plan's explicit resource and
    latency budgets or fail visibly without expanding technology automatically.

## Migration and rollback

There is no existing ClaimBranch user data. This draft may still change before
the contract spike, but every fixture and schema is versioned. Once an
implementation stores live accepted state, changes follow the copy-on-write
migration contract above; deleting the old store is a separate human action
outside F0. Evidence correction and scientific correction always append history
rather than destructive rollback.

## Open questions

- Which runtime/package implements the public CLI and generated schemas?
- Does SQLite pass the accepted operation, traversal, concurrency, replay, and
  copy-on-write migration spikes?
- Which canonical JSON and signing libraries preserve the specified bytes?
- Which native-Windows presence, process isolation, credential, IPC, and browser
  path proves the authority boundary?
- Which marker/compile configuration survives the real paper's filesystem and
  toolchain behavior?
- Can the short-lived browser surface satisfy the broker contract, or is a
  native/CLI helper required?

These questions may change adapters and physical layout. They cannot weaken the
logical invariants without a superseding ADR and updated validation contract.

## Outcome

Pending. The design remains draft until P1 fixtures and spikes pass. An accepted
ADR may constrain implementation before code exists; this draft is still not
proof that the schema or storage works.
