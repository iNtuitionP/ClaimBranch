# Architecture documentation

The [root target-architecture map](../../ARCHITECTURE.md) describes boundaries
to validate, while this area owns accepted constraints and the historical
reasons behind significant choices. Treat code and tests as evidence of any
implemented architecture and read each document's front-matter status.

## Draft model

- [Finite F0 domain and versioning design](../designs/2026-08-03-domain-model.md)
  — proposed closed record, edge, operation, authority, state, resource,
  manuscript, and replay semantics. Front matter records its authority and
  lifecycle.

## Decisions

- [Architecture decision index](decisions/README.md) — accepted and proposed
  decisions with status and supersession rules.

## Maintenance boundary

- Reconcile the target map and domain design with code when implementation
  establishes real structure or invariants.
- Use a [design proposal](../designs/README.md) for a substantial unresolved
  approach. A design is not current architecture merely because it was written
  or accepted.
- Create an ADR for a significant durable choice and rationale.
- Start with a C4 system-context or container diagram only after real boundaries
  exist. Avoid long-lived code diagrams that duplicate source structure.
