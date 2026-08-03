---
kind: adr
status: proposed
owners: maintainers
last_reviewed: 2026-08-03
---

# ADR 0002: Keep semantic branches distinct from Git branches

Basis: implementation hypothesis

## Context

Git branches and diffs operate on files. ClaimBranch must compare and merge
claims, relationship scope, experiment plans, decisions, manuscript impact, and
debt. Creating a Git branch for every interpretation would also pollute the
user's code and manuscript workflow.

## Decision drivers

- Diffs and partial merges must operate on claims, relationships, plans,
  decisions, manuscript impact, and debt rather than file hunks.
- Global accepted evidence must remain visible from every reasoning branch.
- Exploratory interpretations must not create noise in the user's existing Git
  branch workflow.
- Accepted manuscript changes still benefit from ordinary Git review and
  transport when the user requests it.

## Options considered

- Use Git branches and file diffs as the only versioning model. Rejected because
  files cannot enforce global evidence or semantic dependency closure.
- Use semantic refs and prohibit Git materialization. Rejected because it would
  remove an optional, familiar review path for accepted manuscript patches.
- Use semantic refs for research state and optionally materialize an accepted
  manuscript patch in Git. This is the proposed choice.

## Decision

ClaimBranch branches will be domain refs under `.claimbranch/refs`. Domain
commits record semantic operations and may reference Git commits, but do not
require one Git commit per operation.

Merge requests calculate a semantic diff from a common domain ancestor. The
user can merge selected changes and their dependency closure. Revert appends an
inverse domain commit.

An accepted manuscript patch may optionally be materialized on a dedicated Git
branch for normal file review and transport.

## Consequences

- The kernel needs its own commit, ref, diff, conflict, merge, and replay logic.
- Git remains useful for distribution, backup, release tags, and manuscript
  file history.
- CLI and UI must say `research branch` or `semantic branch` where confusion
  with Git is possible.
- Debug exports must connect each domain commit to relevant Git state.

## Validation

The saturation prototype must keep accepted evidence visible across `main` and
one semantic branch, produce a semantic diff, and apply the required partial
merge without creating a Git branch. A later manuscript-adapter test must show
that an explicitly accepted patch can be materialized for Git review without
making Git the domain source of truth.

## Supersession

None.
