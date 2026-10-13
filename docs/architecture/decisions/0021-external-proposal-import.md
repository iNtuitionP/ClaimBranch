---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-12
---

# ADR 0021: Import external AI responses without inventing application history

## Context

The owner explicitly approved importing the successful external RLVR diagnostic
as an external AI response. Its model and reported HTTP/response hashes remain,
but the original application request envelope does not. Reconstructing that
missing envelope as an owned live attempt would misrepresent provenance.

## Decision drivers

Reuse useful advice without another transmission; keep origin honest and human
selection separate from importing. Preserve manual work, request limits and
ordinary private storage under ADRs 0017 and 0018.

## Options considered

- Discard the response and require another inference: unnecessary transmission.
- Fabricate an application-owned attempt: rejected.
- Explicit unverified external import, followed by local review: selected.

## Decision

A bounded private regular JSON file may supply a typed response, selected current
context and declared external model/request/body/response identities. Preview the
complete local import and require explicit confirmation. Mark its source
`external-diagnostic / unverified-import`. Reported original hashes are source
claims; the independently computed normalized-response and local-import hashes
are separate. No original outbound consent or service trace is reconstructed.

Import creates no inference request, evidence, judgment, candidate selection or
manuscript change. One external response per judgment and at most sixteen per
workspace occupy separate slots from the existing forty-eight attempt slots.
They neither consume nor reset the three-request judgment budget. If the full
saved workspace cannot retain the imported payload, refuse without saving it.

A fresh local review shows original/current context and external status before
selection. Retain identical-context restrictions and original AI influence under
ADR 0020. Reading has no countdown: each comparison permits staging for 120
seconds and can be explicitly refreshed. Failed replacement review preserves
the existing review. Reopening restores history, never consent.

## Consequences

External imports use workspace v10, paper-work v11 and project-work v7; older
closed formats remain unchanged. Their explicit source survives staging, saved
origin and backup/restore. Unverified source claims do not qualify a provider,
prove scientific truth or demonstrate human understanding. Changed-context reuse
and general chat/text ingestion remain outside this bounded typed import.

## Validation

Check dry-run/cancellation without checkpoint changes, no network, source/hash
replay, duplicate/owner limits, exhausted request budget, full-storage refusal,
selection/expiry, unchanged science, restart and fresh-destination backup restore.
Obtain an actual pinned Opus review; keep live enablement separate.

## Supersession

Refines [ADR 0020](0020-retained-proposal-review.md): comparison validity is
short-lived, while reading is untimed. Adds the separately labeled external
source binding anticipated there. No accepted-authority boundary is reversed.
