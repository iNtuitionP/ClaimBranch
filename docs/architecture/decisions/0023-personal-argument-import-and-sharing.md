---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-13
---

# ADR 0023: Preserve prior argument meaning during personal import and sharing

## Context

The owner requests an implementation plan for the
[real-paper migration reports](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-issue-review).
The reports describe hundreds of prior records whose reasons, limitations,
conditions and source identities must not be lost. The current personal alpha
cannot import that argument or express all its fields. Planning does not make
these capabilities available or establish the reported private source's fidelity.

On 2026-10-13 the owner explicitly selected: reviewed batch registration of
prior records; partial migration with original source preservation; selected
scientific records for sharing with reasons separately selected; and private
retention of critique originals. These product choices are settled; exact
versioned schemas, capacities and implementation remain planned in the
[issue execution order](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan).

## Decision drivers

- Preserve the existing researcher's reason instead of requiring transcription
  and a second retrospective narrative.
- Distinguish original source claims, known/unknown authorship and present local
  registration without inventing historical approval or source verification.
- Permit useful partial migration without silently discarding important meaning.
- Keep private research canonical and make sharing an explicit projection.

## Options considered

- Reconfirm each imported item individually before any use: retains a small
  review scope but repeats work across hundreds of prior records; not selected.
- Reject the entire import until every source field is represented: avoids
  partial coverage but prevents the selected early feedback; not selected.
- Infer unsupported fields or label all imported text human-authored: rejected
  because it can manufacture meaning or erase AI influence.
- Register the exact reviewed selection in one personal operation, retaining
  unsupported source and unresolved meaning: selected.
- Share all history/reasons by default or omit all critique originals: not
  selected. Explicitly selected scientific content and private originals are
  separate surfaces.

## Decision

A new personal argument-import path previews the source digest, mapped records,
historical dates/reasons, known or unknown origins, unresolved fields, selection
and resulting graph. One explicit foreground confirmation registers only that
exact selection in personal history. Importing is not a new experiment, a new
historical judgment, a prior app receipt or protected scientific approval.
Local ingestion time/operation is separate from source-claimed chronology.
Transport origin is independent of human/AI/mixed/unknown contribution claims;
missing authorship must never default to human or AI-free.

Keep unsupported fields and their source pointers in bounded, retained private
source records. Mark them unresolved in nodes, source readers, change review
and selected AI context. Complete mapped records can be used without waiting
for unrelated unsupported records. Required typed-field, endpoint, capacity,
schema or consistency failures still refuse publication of the batch. Any
operation needing a semantic field the app cannot validate refuses that
operation while preserving other work; unresolved source cannot become an
automatic supported status, passing gate or fully checked scope. Later mapping
appends an explicitly reviewed transformation without erasing the original or
overwriting newer work. No generic accepted-science extension bag is introduced.

The imported argument's personal history is the working canonical record.
External ledgers remain sources; further external edits require explicit
comparison and source-bound amendments, never background synchronization.
Existing user tools remain usable and no second judgment log is mandatory.

A separate Git-share export includes only explicitly selected scientific
records and their disclosed required dependencies. Judgment reasons are opt-in.
Personal notes, private paths, credentials and critique originals/identities
are excluded. Preserve referential integrity with stable non-content-derived
redacted placeholders when a selected record refers to private source.
Verification compares this declared projection with its specific saved private
revision; it neither validates the full private history from public bytes nor
makes the export a backup or a second authority. Do not overwrite edited exports,
publish automatically or synchronize them back.

Critique originals may be retained in ordinary private local files under
ADR 0017, including normal private saved-work backup. Their human-written
neutral questions and source associations are distinct from empirical
observations. Raw critique and reviewer identity are excluded from share output
and AI context by default; a source citation alone does not authorize their
transmission. No encryption, confidentiality-policy verdict or new provider
permission is inferred from private retention.

## Consequences

The new contracts must represent imported/unknown origins and retained source
without changing legacy bytes or restoring authority. Partial import is honest
about its coverage; completeness cannot be inferred from successful saving.
Capacity, backup, AI-origin return, source availability and redacted projection
need versioned schemas and independent checks before release claims change.

The private originals consume the same declared saved-work budget and survive
verified restart/backup return. A public projection may deliberately omit
content; its omission manifest must state coverage without exposing private
text. The current personal alpha remains unencrypted. This decision does not
enable a protected writer, manuscript mutation, runtime migration or live AI.

## Validation

These are required future checks, not implemented passes:

- Exact batch selection/source changes invalidate confirmation; cancel, malformed
  input, capacity refusal, stale destination and interrupted publication retain
  original files and do not leave partially registered records.
- Known AI and explicit unknown origin survive batch registration, edits,
  correction, restart and backup. Missing origins cannot silently become human.
- Unsupported source survives partial migration and later mapping; relevant
  unresolved fields stay visible, and unsupported dependent operations refuse.
- Identical source/selection retries are idempotent or refused without duplicate
  science; changed sources cannot replace later app reasoning.
- Selected share output excludes private content even through origin chains,
  derived labels, identifiers, diagnostics and required source references.
- The same projection verifies against the saved source revision; source, policy,
  selection or output changes do not verify under a previous commitment.
- Critique remains distinct from evidence and raw originals never enter a default
  export or provider request. AI-off manual work remains complete.

## Supersession

None. This defines a separate personal research-argument import and sharing
path within ADR 0017's ordinary private storage. ADR 0021 still governs external
AI-response import and does not register science. ADRs 0005/0008 retain protected
authority and private canonical placement; no imported record receives protected
approval or becomes a trusted restore through this decision.
