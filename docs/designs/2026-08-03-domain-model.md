---
kind: design
status: draft
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: proposed domain types semantics and invariants for the contract spike
---

# Domain and versioning model

Version: 0.1
Scope: implementation hypothesis for the contract spike

This document proposes kernel semantics for the first contract spike. `MUST`,
`SHOULD`, and `MAY` describe conformance to this draft, but the exact taxonomy,
serialization, event model, and branch algorithm remain revisable until the
vertical slice is exercised.

## Purpose

Define a falsifiable domain contract for the first vertical slice: what is
global evidence, what may branch, which changes are auditable, and what must be
rebuildable. This document is a design input to a contract spike, not evidence
that any storage or merge implementation exists.

## Context and current state

The product contract requires immutable accepted evidence, branchable reasoning,
selective semantic merge, proposal-only AI, manuscript debt, and an AI-free
deterministic core. ADRs [0001](../architecture/decisions/0001-evidence-and-reasoning.md)
and [0003](../architecture/decisions/0003-ai-proposals.md) accept the two central
trust boundaries. There is no implemented schema, event log, ref algorithm, or
cache yet.

## Goals and non-goals

Goals:

- make the accepted product constraints enforceable by a small deterministic
  kernel;
- support aggregate experiments without inventing synthetic runs;
- preserve relationship scope, provenance, and human review;
- make partial merge and revert auditable; and
- make every disposable projection rebuildable from repository state.

Non-goals:

- lock a programming language, database binding, wire format, or UI schema;
- prove every proposed node and status is necessary before the vertical slice;
- replace Git's transport and file history; or
- authorize AI to create accepted state.

## Decision drivers

- The evidence/reasoning boundary must remain visible even if the UI projects
  both as one graph.
- Branch diff and merge must operate on scientific meaning rather than file
  hunks.
- State must survive restart, remain inspectable, and work with AI disabled.
- Corrections, invalidation, partial merge, and revert must preserve provenance.
- Early serialization choices must remain cheap to change after fixture tests.

## Options considered

- Use Git files and branches as the complete domain model. This cannot enforce
  global evidence visibility or semantic dependency closure and conflicts with
  the proposed semantic-branch direction.
- Store one mutable graph snapshot per reasoning branch, including evidence.
  This conflicts with accepted ADR 0001 and risks hiding or duplicating
  evidence.
- Use a global append-only evidence layer plus branchable reasoning state,
  durable semantic operations, refs, and a rebuildable projection. This is the
  proposed model elaborated below.
- Require a fully event-sourced physical implementation immediately. Deferred:
  the spike may use a snapshot or simple log until replay, migration, and
  profiling evidence justify a permanent format.

## Proposed design

The following numbered sections define the logical contract. Normative words
apply to the draft contract only; unresolved physical choices remain open.

## 1. Two connected graphs

ClaimBranch presents one research graph but preserves two different kinds of
truth internally.

### 1.1 Evidence Provenance Graph

This graph records executed work and direct observations. It is global across
all semantic branches, append-only after human confirmation, and normally a
directed acyclic provenance graph.

```text
ExperimentSpec version -> 0..N Run -> Artifact/Metric/Observation
                      `-----------> aggregate Artifact/Metric/Observation
```

A Run is optional. Some researchers manage aggregate experiment results only;
the model MUST NOT require synthetic Run records merely to attach evidence.

### 1.2 Reasoning and Manuscript Graph

This versioned multigraph records how evidence is understood and expressed.
Objects and relationships can be active in one branch and absent, superseded,
or differently scoped in another.

```text
Observation -> Interpretation -> Claim -> Narrative
                         |             |
                         v             v
               Experiment Plan   Manuscript Anchor
                                          |
                                          v
                                      Patch / Debt
```

Reasoning can revisit earlier interpretations, so this graph is not required to
be acyclic.

## 2. Global invariants

### INV-1: accepted evidence is branch-independent

A completed Run, raw Artifact, Metric, or human-confirmed Observation MUST be
visible from every semantic branch. Creating, deleting, or merging a reasoning
branch MUST NOT hide accepted evidence.

### INV-2: evidence corrections preserve history

Accepted evidence MUST NOT be edited in place. A parser correction, invalid
run, or revised observation creates a new record linked with `supersedes` or an
invalidation event containing a reason. The original remains addressable.

### INV-3: artifacts are content-addressed

An imported raw artifact MUST retain its content hash, source path or external
reference, import time, and mapping version. ClaimBranch MUST NOT rewrite the
source file during import.

### INV-4: scientific relationships are reviewable records

An edge such as `supports` or `challenges` MUST be a first-class record with
scope, conditions, rationale, provenance, and review status. Its existence
cannot be inferred solely from graph topology.

### INV-5: AI output starts unaccepted

AI-created nodes, edges, conflicts, debt candidates, and patches MUST begin as
proposals. They MUST NOT affect accepted branch state until a human accepts or
edits them.

### INV-6: merge is selective and auditable

A merge MUST record the source and target refs, base commit, selected semantic
changes, omitted changes, dependency closure, author, time, and rationale.

### INV-7: revert appends history

Revert MUST create a new domain commit with inverse reasoning changes. It MUST
NOT erase previous commits or accepted evidence.

### INV-8: debt follows accepted state

Manuscript Debt MUST be derived from accepted research/manuscript divergence.
AI MAY propose impact, but only deterministic state or human-confirmed semantic
links may create accepted debt.

### INV-9: repository data works without AI

All accepted objects, refs, diffs, merges, anchors, debt, and deterministic
checks MUST remain usable with every AI provider disabled.

## 3. Common record envelope

Every node has a common envelope. Serialization syntax remains subject to an
implementation RFC, but the logical fields are stable.

```yaml
id: claim_01J...
type: claim
schema_version: 1
title: Joint distortion-sensitivity factorization
body: >
  Operator damage is jointly determined by operator-induced logit
  distortion and score sensitivity.
created_at: 2026-08-03T12:00:00Z
created_by:
  kind: human
  id: local-user
provenance:
  domain_commit: commit_01J...
  source_refs: []
attributes: {}
```

Identifiers MUST be stable and globally unique inside a research repository.
Human-readable short IDs such as `C-12` are display aliases, not durable keys.

## 4. Node types

### 4.1 Evidence layer

| Type | Purpose | Mutability rule |
|---|---|---|
| `experiment_spec` | Versioned protocol, parameters, and measurement intent | New version on accepted change |
| `run` | One execution with code, environment, parameters, and status | Append events; never rewrite completed payload |
| `artifact` | JSON, plot, log, checkpoint, or external artifact reference | Content-addressed and immutable |
| `metric` | A named measurement from a Run or aggregate ExperimentSpec result | Supersede on correction |
| `observation` | Human-confirmed statement directly grounded in evidence | Supersede on correction |

An Experiment planned only for a branch is an `experiment_plan`. It becomes a
global `experiment_spec` when the user accepts it for execution. Evidence MAY
attach to that ExperimentSpec directly or through zero or more Runs; completed
Runs are never branch-local.

### 4.2 Reasoning and publication layer

| Type | Purpose |
|---|---|
| `research_question` | The question the work tries to answer |
| `hypothesis` | A testable pre-experiment proposition |
| `scenario` | Expected or alternative result pattern and its implications |
| `interpretation` | A candidate explanation of observations |
| `claim` | A proposition the manuscript may communicate |
| `narrative` | A coherent selection and ordering of claims |
| `decision` | Human adoption, rejection, deferral, or override rationale |
| `experiment_plan` | A proposed follow-up experiment and its scientific purpose |
| `manuscript_anchor` | A stable link to a sentence, paragraph, section, table, or figure |
| `patch_proposal` | A bounded candidate manuscript change |
| `debt_bundle` | A group of related synchronization obligations from one change |
| `debt_item` | One independently reviewable and resolvable manuscript obligation |
| `literature_item` | A cited or candidate external work |
| `note` | Low-friction capture pending optional structure |
| `ai_proposal` | Durable review record of structured changes proposed by AI |

## 5. Edge model

### 5.1 Base relations

| Relation | Meaning |
|---|---|
| `contains` | A node structurally contains another |
| `produces` | An ExperimentSpec, Run, or process produces evidence |
| `derived_from` | A record is derived from another source |
| `tests` | An experiment evaluates a hypothesis, claim, or interpretation |
| `supports` | Evidence raises support for a target proposition |
| `challenges` | Evidence weakens or conflicts with a target proposition |
| `qualifies` | Evidence or reasoning restricts the scope or conditions of a proposition |
| `motivates` | A result or interpretation creates a question or planned action |
| `supersedes` | A new record replaces an older record without erasing it |
| `expressed_in` | A Claim or Narrative is expressed at a Manuscript Anchor |
| `affects` | A change has a reviewed impact on another record or anchor |
| `cites` | A literature item relates to a Claim or Anchor |
| `resolves` | A decision, experiment, or patch resolves debt |

Experiment purposes such as `replication`, `validation`, `falsification`,
`ablation`, `generalization`, `robustness`, `discrimination`, and `measurement`
are values of `tests.intent`, not additional top-level relation types.

Literature purposes such as `supports`, `challenges`, `contrasts`,
`uses_similar_method`, `reports_conflicting_evidence`, and `defines_metric` are
values of `cites.intent`.

### 5.2 Edge record

```yaml
id: edge_01J...
relation: supports
source: observation_controlled_noise
target: claim_joint_factorization
scope: sensitivity component only
conditions:
  - fixed absolute endpoint noise
strength: partial
review_status: human_reviewed
created_by:
  kind: human
rationale: >
  This result shows a sensitivity difference under controlled distortion,
  but does not establish the operator-induced distortion component.
```

`scope`, `conditions`, and `rationale` SHOULD be visible in the inspector and
semantic diff. The UI MAY offer simpler labels but MUST preserve this detail.

## 6. Independent status axes

A single `status` field is insufficient. Applicable axes are independent.

### 6.1 Lifecycle

```text
draft | active | resolved | superseded | rejected | archived
```

### 6.2 Scientific maturity

```text
speculative | provisional | supported | contested | validated | manuscript_ready
```

This is advisory metadata, never an automatic merge permission.

### 6.3 Review

```text
human_created | ai_proposed | human_reviewed | accepted | rejected
```

### 6.4 Manuscript integration

```text
unlinked | linked | debt_open | patch_proposed | applied | compile_verified | waived
```

### 6.5 Proposal disposition

```text
pending | accepted | accepted_with_edits | rejected | dismissed | expired
```

Every proposal remains durable regardless of disposition.

### 6.6 Debt disposition

```text
open | triaged | patch_proposed | applied | verified | waived |
explicitly_deferred | superseded
```

### 6.7 Run execution

```text
planned | queued | running | completed | failed | invalidated
```

## 7. Domain commits

A domain commit is an atomic, ordered set of semantic operations. It is distinct
from, but may reference, a Git commit.

```yaml
id: commit_01J...
parents: [commit_previous]
ref: refs/branches/joint-distortion-sensitivity
author: local-user
created_at: 2026-08-03T12:30:00Z
message: Record real-operator mismatch and competing interpretations
rationale: Real operator results challenge the saturation-only scope.
operations:
  - op: create_node
    object: interpretation_delta_magnitude
  - op: create_edge
    object: edge_pruning_challenges_claim01
  - op: set_branch_state
    object: claim01
    field: scientific_maturity
    value: contested
```

Allowed logical operations include create object, create or supersede edge,
change branch-local state, add a decision, create/defer/waive debt, and accept or
reject a proposal. Evidence import uses global events and is referenced from the
domain commit that interprets it.

## 8. Refs and branch state

The default semantic ref is `refs/main`. A branch ref points to the head domain
commit of a competing reasoning state.

```text
.claimbranch/
|-- objects/
|-- events/
|-- refs/
|   |-- main
|   `-- branches/
|       `-- joint-distortion-sensitivity
|-- proposals/
|-- anchors/
|-- adapters/
`-- config.toml
```

A branch controls:

- selected interpretations, claims, narratives, and their independent status
  axes;
- branch-local relationships and their scope;
- planned experiments;
- decisions;
- manuscript patch proposals; and
- debt dispositions.

A branch does not own completed Runs, raw Artifacts, Metrics, or confirmed
Observations. Removing a branch from the active UI archives or tombstones its
ref; it MUST NOT garbage-collect its reasoning commits or make rejected and
superseded histories unreachable.

## 9. Semantic diff

A diff compares two refs or commits and groups changes by domain meaning:

```text
Claims
Evidence relationships
Interpretations and narratives
Follow-up experiment plans
Manuscript impact and patches
Debt
Decisions and human rationale
```

Property-level changes MUST retain before and after values. Relationship changes
MUST show scope, conditions, rationale, and review status. Evidence objects may
appear as context but are not merged between reasoning branches.

## 10. Merge request and partial merge

A merge request is calculated from the lowest common domain ancestor of source
and target refs. Its selectable unit is a semantic change, not a file.

Example selection:

```text
[x] Mark Claim C-01 contested
[x] Add two follow-up experiment plans
[x] Open the manuscript-impact Debt Bundle
[ ] Adopt Claim C-02 as the central claim
[ ] Apply the Abstract patch
```

The kernel MUST compute dependencies between selected changes. If a selected
edge references a new reasoning node, that node must also be selected or the
edge must be omitted. Global evidence dependencies are already available and do
not require selection.

Referential-integrity dependencies are mandatory. Higher-level semantic
dependencies are advisory: the user may omit them by recording an override
rationale.

A partial merge creates one new commit on the target ref containing only the
selected change closure, plus a Decision recording omitted changes. It MUST NOT
mutate or delete the source branch.

## 11. Conflicts

### 11.1 Deterministic conflicts

The kernel can enforce or block on:

- the same branch-local property changed differently on both sides;
- overlapping accepted patches for one anchor;
- an anchor unresolved by label, marker, and exact fingerprint;
- conflicting mappings for the same metric source;
- use of a superseded observation as current without explicit override; and
- manuscript compile failure after patch application.

Blocking is scoped to the affected operation. A property conflict blocks that
selected change; an anchor, patch, or compile conflict blocks only patch
application and debt verification; an import-mapping conflict blocks only the
affected import. Unrelated Claim, relationship, Experiment Plan, and Debt
changes remain eligible for partial merge.

### 11.2 Semantic conflict proposals

AI may flag:

- manuscript language broader than supporting evidence;
- a mixed result inconsistent with `always` or `consistently`;
- a new claim incompatible with an accepted conclusion;
- evidence that supports only one component of a compound claim; or
- literature that may weaken a novelty claim.

These remain `ai_proposed_possible_conflict` records. They do not block a merge
unless a human accepts a conflict and the selected merge policy requires it.

## 12. Revert and invalidation

Reverting a reasoning commit appends inverse operations to the current ref.
Reverting an accepted manuscript patch restores the previous bounded content in
a new patch commit and reruns compile verification.

Evidence is never reverted out of existence. A bad Run is invalidated with a
reason; a mistaken Observation is superseded. Branches continue to see the full
history and can filter invalid evidence from active reasoning.

## 13. Manuscript anchors

An anchor record includes:

```yaml
id: anchor_abstract_central_claim
document: main.tex
kind: paragraph
locator:
  marker: anchor-abstract-central-claim
  label: null
fingerprint:
  text_hash: sha256:...
  context_before: ...
  context_after: ...
linked_claims:
  - claim_saturation_only
state: linked
```

Resolution order is LaTeX label, managed marker, exact fingerprint, contextual
candidate, AI-proposed candidate, then human relinking. Only the first three may
resolve deterministically; contextual or AI candidates require confirmation.

## 14. Patch lifecycle

```text
proposed
-> human_reviewed
-> accepted
-> applied
-> compile_tested
-> debt_verified
```

The AI layer MAY create `proposed`. Deterministic code applies an exact accepted
patch to its verified anchor. A content mismatch stops application and requests
review. ClaimBranch MUST NOT silently broaden a patch or write to the active
manuscript before acceptance.

## 15. Debt bundles and items

A `debt_bundle` groups the effects of one accepted source change. It MUST contain
one or more `debt_item` records so individual manuscript locations can be
reviewed and resolved independently.

```yaml
bundle:
  id: debt_bundle_real_operator_results
  source_change: commit_real_operator_review
  central_issue: Saturation-only scope is challenged across operators.
items:
  - id: debt_item_abstract_scope
    affected_anchor: anchor_abstract_central_claim
    reason: The Abstract still generalizes across every operator.
    severity: central_claim
    disposition: open
    resolution_condition: Qualify the scope or explicitly defer the change.
```

Each item MUST retain its source change, affected objects or anchor, reason,
severity, disposition, resolution condition, and transition history. The bundle
MUST report partial completion without hiding open items. `contains` links the
bundle to its items; a reviewed Decision, Experiment, or Patch may `resolve` an
item.

## 16. Projection and cache rule

Repository objects, events, refs, anchors, adapter mappings, and every proposal
with its disposition are the durable source of truth. Rejected, dismissed, and
edited proposals remain available for audit and product metrics. SQLite is a
disposable projection used for search, tables, graph traversal, branch
materialization, and inbox queries.

Deleting `.claimbranch-cache/index.sqlite` and replaying repository state MUST
produce an equivalent accepted graph, refs, and debt state. AI-generated prose
does not have to be reproducible, but its stored proposal, inputs, model
identity, and human disposition do.

## Migration and rollback

There is no existing user data to migrate. The contract spike must use versioned
fixtures and schema identifiers so it can be discarded or migrated without
pretending draft storage is stable. Revert appends inverse reasoning operations;
evidence correction uses invalidation or supersession, never destructive
rollback. A future accepted on-disk format requires a separate migration design
and recovery test.

## Validation

The design advances only if automated fixtures and the
[saturation validation case](../validation/cases/saturation.md) demonstrate:

1. accepted evidence remains visible across `main` and a reasoning branch;
2. the required semantic diff and partial merge preserve dependency closure;
3. relationship scope and rationale survive save, reopen, diff, and merge;
4. deleting the cache and replaying durable state produces an equivalent graph,
   refs, proposals, and debt state; and
5. the complete deterministic path works with every AI provider disabled.

The prototype may simplify serialization, arbitrary conflict handling, and
manuscript patch application when the release scope explicitly defers them.

## Open questions

- Which proposed node, edge, and status types prove necessary in the fixed
  vertical slice?
- Does the first durable format use snapshots, an operation log, or a hybrid?
- What is the smallest dependency model that makes partial merge safe without
  turning semantic advice into a blocking rule?
- Which cache-rebuild and migration benchmarks are required before format
  acceptance?
- How should domain commits reference Git state without coupling one domain
  operation to one Git commit?

## Outcome

Pending. The design remains `draft` until the contract spike supplies the
validation evidence above. Acceptance will require updating the target/current
architecture distinction, recording durable choices as ADRs, and creating an
ExecPlan for implementation; a drafted document alone is not an outcome.
