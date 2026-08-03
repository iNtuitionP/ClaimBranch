---
kind: target-architecture
status: draft
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: target pre-implementation system boundaries and quality constraints
---

# ClaimBranch target architecture

ClaimBranch has no implementation or settled stack yet. This document describes
the target boundaries the first vertical slice is intended to test, not an
observed current architecture. Accepted constraints live in ADRs; unresolved
domain and serialization details remain a draft design.

## Goals and quality priorities

In priority order, the architecture must preserve:

1. evidence integrity and provenance;
2. human ownership of scientific and manuscript decisions;
3. local-first operation with a deterministic AI-free core;
4. auditable semantic branch, merge, and revert behavior; and
5. a responsive daily workflow that does not turn research into bookkeeping.

The complete intended behavior is in the
[product specification](docs/product/product-spec.md).

## System context

```text
Researcher
    |
    v
ClaimBranch local workspace
    |-- reads/writes --> repository evidence and ClaimBranch state
    |-- reviews -----> LaTeX manuscript and Git state
    |-- invokes -----> configured local import/compile commands
    `-- optionally --> AI provider, returning proposals only
```

The repository is the durable boundary. A remote AI provider is optional and
must never become necessary to read accepted state, navigate the graph, diff or
merge reasoning, apply an already accepted exact patch, or run deterministic
checks.

## Conceptual building blocks

These are responsibility boundaries, not committed packages or processes.

| Building block | Responsibility | Current confidence |
|---|---|---|
| Deterministic domain core | Evidence invariants, objects, relationships, semantic refs, diff, merge, revert, and debt state | Required boundary; serialization is draft |
| Repository adapter | Durable objects, events, refs, configuration, artifacts, and Git references | Required boundary; file layout is proposed |
| Manuscript adapter | Anchors, bounded patch review/application, compile checks, and debt verification | Product requirement; implementation is draft |
| Local projection | Rebuildable search, table, graph, branch, and inbox views | Required disposable boundary; technology undecided |
| Local workspace | Human review and focused workflow surfaces | Product hypothesis to validate |
| AI proposal adapter | Optional provider calls and durable proposal records without accepted-state authority | Required trust boundary; providers undecided |

## Critical runtime paths

- Import preserves the original artifact, then a human confirms any Observation.
- A mismatch creates branchable interpretations and reviewed relationships while
  all accepted evidence remains globally visible.
- Partial merge applies only selected semantic changes and their integrity
  dependencies; omitted reasoning remains on the source branch.
- Manuscript modification follows `propose -> review -> accept -> exact apply ->
  compile -> human verify`. Anchor or compile failure blocks only the affected
  patch and debt verification, not unrelated semantic merges.

## Cross-cutting constraints

- Accepted evidence is append-only; corrections supersede or invalidate it.
- Every scientific relationship retains scope, conditions, rationale, and
  provenance.
- AI output starts as a proposal and cannot directly change accepted state.
- The local index is disposable and must be reconstructible from repository
  state.
- Remote data disclosure is explicit, scoped, and auditable.

## Detailed sources

- [Architecture status and decision map](docs/architecture/README.md)
- [Draft domain and versioning design](docs/designs/2026-08-03-domain-model.md)
- [Architecture decision index](docs/architecture/decisions/README.md)
- [Canonical validation case](docs/validation/cases/saturation.md)

When code establishes real containers or deployment units, reconcile this file
with observed structure and change its kind/status only after verification.
Start with C4 system-context and container views; add lower-level diagrams only
when they answer a recurring question better than code and tests.
