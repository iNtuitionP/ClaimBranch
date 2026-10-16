---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0027: Share repeated audit values through explicit versioned opt-in

## Context

The combined I05 fixture fits initial private storage but its first comparison
needs8,570,177 audit bytes, exceeding the unchanged8MiB manifest bound. Each
full branch repeats large evidence and imported-record fields. The owner requests
continued implementation after the measured stop. Earlier manifests, source bytes,
understanding context and scientific capacity must remain intact.

## Decision drivers

Make a new judgment possible at paper scale without discarding exact measurements
or hiding provenance. Preserve old bytes, retain deterministic complete audit
reading/source replay, bound memory before expansion, and avoid silent upgrades
or new authority. This is representation work within ADRs0023–0026.

## Options considered

- Increase the8MiB bound or reduce the fixture: rejected; changes the acceptance
  contract without fixing repeated representation.
- Remove derived views from audits: smaller but loses independently inspectable
  audit content and changes the logical contract.
- Compress or replace all existing manifests implicitly: changes old bindings.
- Explicit opt-in to a shared-value envelope retaining the full logical audit:
  selected.

## Decision

Imported seed14 histories may append command16 `set-audit-encoding` once, with
`shared-values/v1`. This changes no scientific head/value/relationship. Preserve
all original seed/command bytes and the manifests of all earlier prefixes.
Only opted-in histories emit `shared-audit-manifest/v1`; ordinary view/graph APIs
remain expanded. Old formats and old source imports do not change by loading.

Keep seed, commands, global evidence events, selected merges and episode metadata
in the envelope. Each view field uses an explicit inline/ref wrapper; canonical
values of at least1KiB reside once in a SHA-256 keyed shared-value map. Tagging is
at the field boundary, so user data named ref/inline remains literal. Private
sources/provenance remain complete and are not implicitly shared with a provider
or public export. This format is not a protected receipt or restore authority.

Stored manifests remain bounded at8MiB. Expanded logical JSON is bounded at16MiB
using the existing project codec and its NFC/string/depth/collection limits.
This transient bound is distinct from stored capacity; it promises no unlimited
history or compressibility. Before materializing repeated references, predict
exact expanded byte length. Reject missing/unused/badly hashed references,
noncanonical inline/sharing choices, invalid closed wrappers and length/digest
mismatch. A separate verified reader expands the full logical audit, replays its
seed/commands with original-source checks and requires the exact shared manifest;
lossless decoding alone does not validate science or authority.

Work27/project23/personal+backup frame15 retain this opt-in only for seed14.
Older formats reject the new command/frame. New `import-argument --shared-audit`
includes it in the full original import preview/confirmation. Existing work uses
`enable-shared-audit --dry-run`, then explicit terminal `convert`; no background
conversion occurs. Cancel/failure preserves saved work. Earlier causes/writing
keep their original prefix and byte commitments; no consent or explanation is
restored. Take a private backup before conversion for older-build rollback.

## Consequences

Repeated view fields consume one stored copy, while their full logical audit
remains independently readable and source-replay checked. New large distinct data
can still hit the same limits and must refuse before publication. The encoding
is an engineering repair, not a guarantee of every paper's fit or research benefit.
No new evidence confirmation, AI capability, manuscript writer, device key,
understanding closure or protected operation is enabled.

## Validation

Check literal expanded logical equality, deterministic replay, old-prefix/golden
bytes, reference tampering, forged-view rejection against replay and hostile
expansion refusal before allocation. Check old-format/new-frame mismatches,
explicit actual-terminal conversion cancel/confirm and private backup return.
Re-run the frozen combined fixture under the unchanged operation/time/memory
bounds and source/privacy/return checks; retain the original failure and every
remaining gate in the existing ExecPlan. Passing codec tests alone does not
complete I05 or authorize publication.

## Supersession

None. Adds a separately selected audit encoding within ADR0024's existing
stored bounds and ADR0017's personal unprotected authority boundary. It does not
rewrite earlier physical formats or protected migration policy.
