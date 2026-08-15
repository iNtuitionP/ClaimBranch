---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-08-14
---

# ADR 0007: Bind one research episode to a fenced manuscript saga

Basis: finite-contract and recovery review

## Context

The first live evaluation needs to distinguish eligible starts, invalid
protocol attempts, product failures, retries, provenance, and timing. Without a
durable episode identity, per-workflow limits and V0 outcomes are ambiguous.

The same workflow may accept a graph decision before an external LaTeX write,
compile, restore, and human debt closure finish. Treating those effects as one
transaction would report false success and make crash recovery unsafe.

## Decision drivers

- Each prospective workflow and its limits must be deterministically
  partitioned.
- A graph commit must never imply that manuscript bytes or compiled output are
  verified.
- External edits, two processes, crashes, key loss, and disk failure must not
  cause a blind overwrite.
- Recovery must prefer a visible hard stop over guessed state.

## Options considered

- Infer episodes from timestamps and nearby operations. Rejected because
  eligibility, retries, and limits become nondeterministic.
- Treat graph and filesystem changes as one conceptual commit with a backup.
  Rejected because the filesystem and compiler do not share the canonical
  transaction.
- Add a durable ResearchEpisode and a separate fenced write-ahead manuscript
  saga. Selected.

## Decision

A ResearchEpisode is the durable workflow identity for one unexpected-result
case. It records the project, eligibility-rule version, baseline ref heads and
evidence watermark, opened/closed clocks, status, and invalidation reason. Every
accepted DomainOperation carries an episode ID. H0 variants use isolated stores;
V0 uses one cumulative project with at most one active episode and the finite
counts defined by the domain contract.

Graph acceptance, manuscript debt, patch preparation, file application,
compile verification, restoration, and debt closure are distinct visible
phases. A manuscript saga:

- has one active writer per project/file/anchor and a monotonic fencing token;
- seals the expected graph head, file identity/hash, debt, PatchIntent, compile
  plan, and postimage digest;
- durably verifies an authenticated encrypted preimage before mutation;
- writes and flushes a temporary postimage before an atomic replace;
- compiles in an isolated output tree with a pinned argument vector and no
  unapproved shell escape;
- promotes only verified named outputs; and
- restores exact preimage bytes or enters recovery_required.

Every boundary rechecks the fencing token, file hash, graph head, and
supersession state. Divergent bytes, missing key, disk full, unaccounted
compiler effects, or interrupted restore lock manuscript and accepted-state
mutation to a recovery-only surface. Debt closure requires a separate sealed
human receipt bound to the exact debt, patch, attempt, source/output/compiler
digests, graph head, and non-restored saga state.

## Consequences

- Episode identity supports reproducible validation and bounded resource rules.
- Users see honest partial progress instead of one ambiguous committed state.
- File safety needs platform-specific flush/replace and isolation spikes before
  the implementation stack is accepted.
- Recovery can be conservative and occasionally require manual inspection, but
  never guesses or overwrites divergent newer work.
- General multi-file/repository-wide manuscript editing remains outside F0.

## Validation

Fixtures must cover episode creation/closure/invalidation, zero valid starts,
invalid-replacement limits, every journal/replace/compile/restore cut point,
two tabs/processes, external edits at each boundary, supersession, key loss,
disk full, stale closure receipts, exact restore, and the sole
recovery_required hard stop.

## Supersession

None.
