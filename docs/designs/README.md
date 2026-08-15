# Design proposals

This area is for substantial unresolved technical work, not every feature or
refactor.

## Proposals

- [Domain and versioning model](2026-08-03-domain-model.md) — draft kernel semantics for
  the first contract spike.
- [Notion MCP coding-journal automation](2026-08-15-notion-coding-journal-automation.md)
  — accepted; safe, resumable task-level developer records without making
  Notion repository truth.

Create `YYYY-MM-DD-short-name.md` from the
[design template](../_meta/templates/design.md) when a change is expensive to
reverse or crosses storage, public contracts, security/privacy boundaries,
core invariants, or several components. Compare credible alternatives and
define validation before treating the proposal as a direction.

Every proposal must keep its purpose, current context, goals/non-goals,
drivers, options, proposed design, migration/rollback, validation, open
questions, and outcome explicit. CI checks those sections so a large technical
model cannot bypass the proposal lifecycle.

A design status does not say whether code exists. When a design is implemented,
update current product and architecture sources, add an ADR for durable
significant choices, and use an [ExecPlan](../PLANS.md) for multi-session work.
