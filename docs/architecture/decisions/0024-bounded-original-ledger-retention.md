---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0024: Bound exact original-ledger retention separately from scientific records

## Context

[ADR 0023](0023-personal-argument-import-and-sharing.md) requires exact private
originals, mappings and reviewed historical registration without invented approval.
The [original-ledger plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#original-ledger-migration-implementation-plan)
finds that its frozen 430-record envelope exceeds 8 MiB, while raw originals are
1.4 MiB. Repeating mappings in the scientific seed exceeds its 4 MiB boundary.

## Decision drivers

Preserve exact source bytes, deterministic source-checked replay and old format
bytes. Fit the selected finite workload without widening legacy storage codecs,
truncating sources or conferring research authority.

## Options considered

- Raise every legacy codec bound: unnecessary compatibility and memory risk.
- Retain only extracted science: loses original mappings and unsupported meaning.
- Repeat the entire envelope in every scientific record: exceeds existing bounds.
- Retain one lossless private snapshot plus source-checked compact records: selected.

## Decision

Use imported seed/ordinary command v14, workspace v16, work v24, project v20 and
personal/backup frame 12. Command v14 freezes source-reference v2, explicitly
binding envelope digest scope and H/A/U flags; I03 owns compound-origin review.
The seed retains a `zlib-argument/v1` snapshot: exact
raw envelope digest/length and compressed bytes represented by the existing
bounded source chunk codec. Raw input is at most 16 MiB, compressed data at most
4 MiB, and the complete seed must still fit 4 MiB. Manifest/project remain 8/16
MiB. Compression is a storage encoding, never encryption or trusted authority.

Bound decompression to declared raw length plus one byte; require exact length,
EOF, no trailing/concatenated stream and both compressed/raw digests. Decode the
original envelope and recompute its selected science, origin flags, unresolved
pointers and preview commitment. Compact scientific records must match exactly.
The project binds the input digest but does not repeat the full input in its
source registry. New formats reject old frame/profile combinations; old formats
cannot acquire these records by implicit conversion.

`initial_argument.source_sha256` on seed v14 identifies the entire v2 envelope;
each original file's digest remains in its snapshot. This differs from seed v5's
single-source digest scope. Source readers disclose that distinction. A stored
`registered_at` is the candidate-preparation timestamp sealed before foreground
review, not a measured filesystem commit timestamp or historical app receipt.

The preview distinguishes extraction validity from seed fit. Actual registration
preflights complete project, graph, checkpoint/archive and restore before exact
`import` confirmation, then rechecks input/source/destination before create-only
publication. Every later append still checks current capacities independently.
No fixed number of future operations is guaranteed by positive headroom.

## Consequences

Exact original files and mapping recipes survive private restart and backup;
unsupported source remains inspectable. Imported table observations need no
fabricated scalar or new confirmation. Cell corrections name the initial import
event and append. Public selected sharing omits snapshots, source paths/hashes
and mapping recipes; an absent scalar is `null` in its existing nullable public
contract. Explicit full private export/backup can contain the snapshot and is
never a public projection. No additional provider is enabled.

A valid preview may still fail a later complete save preflight. Compression ratio
is input-dependent; report the failed bound instead of claiming every 16 MiB
input is storable. Fresh processes must revalidate retained input; in-process
memoization is an optimization, not benchmark evidence. I03 separately owns new
origin-reference semantics and retained-consequence capacity.

## Validation

Check exact 54-cell import/correction, deterministic replay, private writing and
fresh open/backup/restore; corrupt/trailing/concatenated/oversized snapshots;
source/selection/origin tampering, stale/cancelled/duplicate publication and frame
mismatch. Check representative full-paper serialization and cold timings,
legacy schemas/goldens and selected sharing/provider refusal. Evidence and
remaining release coverage belong to the existing execution plan.

## Supersession

None. This implements ADR 0023 within ADR 0017's ordinary private storage.
It supplies no protected writer, scientific verification or manuscript mutation.
