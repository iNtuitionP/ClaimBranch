---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-08-03
format: legacy-minimal
---

# ADR 0003: AI produces proposals, never accepted state

Basis: user-confirmed product constraint

## Context

LLMs can help find mismatches, propose interpretations, identify manuscript
impact, and draft patches. Letting them silently confirm evidence or change the
paper would undermine the researcher's understanding and make accepted state
dependent on a nondeterministic service.

## Decision

All AI output will enter an explicit proposal lifecycle. A proposal records its
model, inputs, time, structured changes, and later human edits and disposition.
Only a human acceptance action can convert proposed changes into a domain
commit.

AI may propose conflicts, Observations, relationships, interpretations,
Experiment Plans, anchors, Debt Bundles, and manuscript patches. It may not
alter raw evidence, confirm an Observation, merge or revert a branch, apply a
patch, or resolve debt.

Core repository operations and deterministic checks must work with AI disabled.
Remote providers are opt-in. The proposal record identifies the provider and
the repository inputs sent to it; configured secret paths are never implicit
context.

## Consequences

- The provider interface returns proposals rather than invoking domain writes.
- The UI needs a first-class Proposal Inbox and review/edit/reject paths.
- Tests can replace the AI provider with deterministic fixtures.
- High-impact acceptance records a human rationale; low-impact capture remains
  lightweight to avoid review fatigue.
