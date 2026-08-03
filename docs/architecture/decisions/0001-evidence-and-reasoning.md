---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-08-03
format: legacy-minimal
---

# ADR 0001: Separate immutable evidence from branchable reasoning

Basis: user-confirmed product constraint

## Context

The motivating workflow uses Git-like branches for competing scientific
interpretations. If completed results are owned by those branches, abandoning a
branch can hide inconvenient evidence and different branches can appear to have
different experimental histories.

## Decision

ClaimBranch will maintain two connected layers:

- a global, append-only Evidence Provenance Graph for completed Runs, raw
  Artifacts, Metrics, and confirmed Observations; and
- a branchable Reasoning and Manuscript Graph for Scenarios, Interpretations,
  Claims, Narratives, Experiment Plans, Decisions, relationships, patches, and
  debt dispositions.

Evidence corrections use invalidation or `supersedes`; they never erase the
original. Every semantic branch sees the same accepted evidence history.

## Consequences

- A merge adopts an interpretation, not an observation.
- A branch can be archived without losing scientific evidence; its rejected or
  superseded reasoning history remains addressable.
- Some relationships from evidence to claims are branchable even though their
  source evidence is global.
- Storage, cache, and APIs must enforce this boundary explicitly.
- The UI can present one graph, but must not conceal the two truth semantics.
