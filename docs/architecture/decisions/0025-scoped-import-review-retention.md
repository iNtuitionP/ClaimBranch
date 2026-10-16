---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0025: Retain bounded scoped import reviews without blanket deferral

## Context

The owner selected source defaults, existing grouped judgment review and improved
retention for issue #14, without a new import-wide deferral. ADRs
[0005](0005-human-authority-provenance-and-understanding-debt.md) and
[0023](0023-personal-argument-import-and-sharing.md) separate lineage from
understanding. [ADR 0024](0024-bounded-original-ledger-retention.md) retains
independent human/AI/unknown source flags in imported seed14. Its initial work
format still has the older 32-recorded/64-partial review bounds.

## Decision drivers

Keep a single current judgment and original reason. Preserve known AI influence
and uncertainty together, retain earlier causes/writing without pruning, and keep
legacy formats and byte limits unchanged. No imported record becomes a present
human contribution or evidence of comprehension.

## Options considered

- One explanation per imported record: repeats work and encourages false origins.
- An import-wide explanation waiver: would replace later consequential review;
  not selected by the owner.
- Raise all legacy array and byte bounds: unnecessary compatibility change.
- A new seed14 retention envelope with scoped review and finite cause count:
  selected within the approved retention increment.

## Decision

Review combines the selected change's dependencies in the existing contextual
one-to-three-topic choice, reusing the person's reason explicitly. Known AI and
unknown authorship are independent, including when both occur in one source.
Unknown-only review exposes the same explanation/later controls. Reading or
import registration creates no explanation obligation per record; a consequential
new change still requires its own exact review. Deferral remains visible as
unfinished explanation, never a reviewed answer or protected debt closure.

New workspace17/work25/project21/personal and backup frame13 applies only to
seed14. Retain at most 128 distinct causal contexts across immutable recorded
choices and current partial explanations. A cause in both counts once; both
copies remain stored and consume the existing serialized-byte budgets. Each
physical array is also bounded at 128. Refuse a new cause with used/limit before
publishing; never discard old causes or writing to make room. Optional response
payload fitting cannot prune these records. The earlier history/manifest/project
byte bounds remain 4/8/16 MiB; positive count headroom is no promise of byte fit.

The 32-episode, one-selected-merge-per-episode and 2,048-command boundaries stay
unchanged. 128 is retention capacity, not an enabled 128-merge workflow. More
than 40 saved unaccepted comparisons can exercise retention; report actual
recorded judgments separately.

## Consequences

Old workspace16/work24/project20/frame12 remains readable with old limits.
Read-only opening does not rewrite it. Saving seed14 work in this build writes
the new format, which older builds refuse. Keep an explicit private backup
before saving if rollback to an older build is needed; this is an alpha format
advance, not a protected copy-on-write migration. New format/profile mismatches
refuse. No encryption, key, provider capability or manuscript writer is added.

Current partial writing is independent from an immutable recorded explanation
choice. Later corrections preserve both and their original science; returning
never revives consent or certifies understanding.

## Validation

Exercise compound AI/unknown and unknown-only review, original-reason reuse,
fresh review after changed science, more than 128 dependencies in one choice,
128 retained partial causes and the 129th refusal without saved-state changes.
Check shared-cause counting, older envelope refusal above its bounds, exact
private save/backup/restore, fresh-process latency/memory, actual terminal choice
and resize/return. Keep legacy schemas byte-identical. Observations and coverage
limits belong to the existing execution plan.

## Supersession

None. Extends ADR 0024 with a new retention envelope and completes its scoped
compound-origin review, without changing that ADR's historical formats or the
protected authority contracts.
