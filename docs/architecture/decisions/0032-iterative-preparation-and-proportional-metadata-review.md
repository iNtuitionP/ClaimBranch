---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0032: Iterate preparation and review metadata without mechanical scrolling

## Context

The owner authorizes IM06 in the [existing import-usability plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-history-and-versioning-detail).
They select overwrite/save-as/cancel at preparation time. IM05 finds126 pages in
the direct protocol reader. Remaining reports need useful diagnostics, same-batch
critique connections and a way to explain literal-lint false alarms. These are
personal workflow repairs under ADR0017, not protected authority or understanding.

## Decision drivers

Preserve original ledgers, existing history and the person's original reason.
Reading is not comprehension; show a useful summary and complete details on demand.
Keep new input, source influence and confirming actor distinct. Do not silently
merge interpretations or suppress scientific/coverage uncertainty.

## Options considered

- Delete/recreate outputs or require scrolling every field: unsafe or impractical.
- Automatically archive every preparation: not the owner's selected policy.
- Infer scientific equivalence or use AI to dismiss warnings: rejected.
- Exact private-file selection, summary/detail review and scoped explicit metadata:
  selected within IM06.

## Decision

Preparation remains create-only unless a collision is explicitly reviewed. Offer
unchanged-target overwrite, a fresh save-as path or cancel. Noninteractive overwrite
requires both an explicit flag and the expected prior SHA-256. Recognize existing
prepared argument envelopes by their closed format and validation; this is not
producer attestation. Exclude the current manifest and source identities, project/
backup files, links, nonprivate files and Git locations. Preserve the old file
until atomic replacement; recheck source/output/directory identities before publish.
Failure before publish preserves the old output. Failure after publish reports
uncertain durability without claiming rollback. No archive or second store is added.

Interactive metadata review starts with bounded counts, operation list and warning
summary; complete per-entry operations, graphs, context and lint remain on demand.
Detail exit returns to summary. A separate fresh terminal transition and typed word
records only the exact candidate after existing input/source/head checks. TUI `r`
is that transition and pasted confirmation is refused. Neither rendering nor
scrolling asserts comprehension. Machine-readable dry-run output remains available.

Metadata-batch/v4 adds an ordered `critique-link` entry referencing an earlier
selected capture by entry ID. Resolve it to the prepared stable critique identity
before constructing the existing link command. Retain the actual batch privately;
linking creates no fabricated private original. Missing/failed/unselected references
refuse the whole save. Private critique originals remain absent from review/share.

Command20 adds a bounded `acknowledge-wording-warning` operation. It pins one claim
policy, one registered anchor and one exact literal rule/phrase, with a reason.
Acknowledgement annotates the warning; it never removes it or certifies wording,
science, manuscript alignment or debt closure. Changed policy/anchor makes it stale.
Negation, hyphen compounds and inflections remain explicit lexical limits. There is
no model-language evaluator. Up to128 acknowledgements use unchanged aggregate
budgets. Work32/project28/personal+backup frame20 require command20, compose with
prior formats and preserve old prefixes. Acknowledgements remain private metadata.

Co-report edges from distinct interpretations retain their distinct endpoints,
basis, reasons and origin. An observation-to-claim edge cannot stand in for an
interpretation-to-claim edge. Edge-count growth alone does not authorize deduplication;
no generic semantic merge or provenance-erasing reuse is introduced.

## Consequences

Researchers can iterate on prepared inputs and inspect consequential changes
without paging through entire source/graph copies. Exact personal confirmation
remains required, while old sources and accepted history remain untouched. File
checks detect observed conflicts; ordinary same-user storage is not an adversarial
filesystem transaction or protected authority. New frames require a current build;
retain a private backup for older-build rollback. Release, private-paper fidelity
and actual user usefulness remain separate.

## Validation

Exercise all three collision choices, aliases, nonprivate inputs, concurrent edits,
flush/replace failures and uncertain post-publish state. Exercise summary/detail/
back/fresh confirmation, queued/pasted input, resize, cancellation and stale reviews.
Check exact field/prerequisite diagnostics, one-batch critique capture/link with
private-original omission, warning acknowledgements and stale bindings, old schema/
golden stability, private reopening/backup/share and an extracted-source journey.
Use pinned Opus review and the full declared personal-alpha scope; the existing
plan records observations and outstanding real-source/hosted limitations.

## Supersession

None. Extends ADR0031's personal metadata paths. Existing science, origin,
protected authority and manuscript boundaries remain unchanged.
