---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0030: Retain partial historical meaning without invented completeness

## Context

The owner authorizes IM04 in the [import-usability plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-history-and-versioning-detail).
Per-leaf bookkeeping and required full experiment metrics encourage fabricated
fields during migration. Original ledger tokens and day-only dates also do not
fit existing internal-ID and timestamp contracts. The owner already selected
honest partial migration, source preservation and defaults with record exceptions
under [ADR0023](0023-personal-argument-import-and-sharing.md).

## Decision drivers

Keep the original reason and minimum useful context; do not manufacture methods,
metrics, dates, historical approval or understanding. Separate incomplete imported
meaning from claims about what the original ledger did or did not contain. Retain
independent known AI and uncertain authorship, old bytes and manual continuation.

## Options considered

- Require complete re-entry: repeats bookkeeping and encourages invented science.
- Fill missing science with templated strings: falsely suggests completeness.
- Put every incomplete record outside the graph: prevents useful partial migration.
- Use new nullable historical records and explicit absence/identity contracts:
  selected within the approved IM04 boundary.

## Decision

Argument-import/v4 and source-manifest/v3 select scientific seed18/ordinary
command18. Historical experiment question, method, conditions, metric/source
reference and individual metric fields may be absent or null. Compact replay
retains nulls plus explicit not-recorded pointers. This means not recorded in the
import, not proof that no value exists in the original. Original files remain
retained. Source-claimed incomplete experiments are not fresh completed-run
confirmation, and the UI distinguishes their missing information. Dependencies
keep unresolved pointers and H/A/U; operations requiring unavailable semantics
refuse explicitly instead of filling them or blocking unrelated graph reading.

An optional per-kind structural_defaults declaration covers only checked app
identities, declared column-order bindings, empty basis for proposed claims,
empty artifact-reference lists, absent tool/commit metadata and absent historical
grouping. Count structural-default separately from science extraction. Scientific
role, parents, scope, units, measurement value/type and conditions are never
silently sourced by an empty/null allowlist. Missing historical experiment fields
have a separate not-recorded category. Swapped column bindings require source
mapping; structural default cannot certify them.

Source-free authored fields use an independent origin declaration, unknown when
omitted, with a reason and no dummy locator. A record assertion cannot clear an
explicit independent/source_origins AI contribution; joint declarations cannot
clear known AI either. File/bundle origin_default remains a replaceable fallback,
with retained explicit record exceptions. Do not reinterpret those defaults as
non-overridable assertions or add an import-wide explanation waiver.

Source-free observation science cannot become a prior result, including invented
non-null artifact provenance. A source-free changed statement/scope cannot inherit
supported/contested status. AI/mixed/unknown source-free writing cannot supply a
completed experiment or historical decision reason; retain a proposed claim or
unrun plan, or map the genuine retained record. Human historical recollections
remain explicitly declared-without-source, not verified source or old app approval.
The same checks apply to the older dummy-file source_silent spelling inside v4.

Retain original tokens/display labels and map unsafe tokens deterministically to
safe internal IDs. Check original, display and internal names across all records
for collisions; references retain one identity. Original day-only dates remain
calendar dates, not invented UTC midnight; decision display titles remain separate
from their original rationale. Raw source and the full recipe bind exact replay.

Work30/project26 and personal/backup frame18 retain seed18 only; older schemas and
frames cannot acquire it. Shared-audit/v2 carries seed18 with the same lossless
algorithm/bounds, while canonical-share/v3 permits explicit null historical fields
and retains the existing selected/redacted projection boundary. Labels/private
source paths do not become default public identities. No implicit migration,
provider capability, protected authority or manuscript writer is added.

## Consequences

A person can bring useful prior experiments into the graph without inventing
missing scientific fields or repeating structural maps. Original labels, date
precision, reasons and source influence survive save/return. Incomplete metadata
stays visible during further work. Older builds refuse new formats; take an
explicit private backup for older-build rollback. Storage remains ordinary and
unencrypted, and successful registration does not establish scientific fidelity.

## Validation

Check narrow defaults and refusal of unsupported scientific defaults, column
binding permutations, independent/unknown/AI and joint origin retention, duplicate
identities, calendar precision and decision-title/rationale separation. Exercise
partial graph reading, fresh judgment and grouped explanation disposition, source
inspection, correction boundaries, selected canonical projection, new-frame
mismatches, fresh saved return and exact backup restore. Preserve all older
schema/golden bytes. Use actual public preparation/registration from an independent
source ZIP and a pinned Opus review; the [existing plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#actual-paper-import-usability-implementation-plan)
owns measured evidence and remaining private-source qualification.

## Supersession

Extends [ADR0029](0029-versioned-original-source-comparisons.md) with separately
versioned partial scientific records. Prior resolver, seed, command, frame,
compression, authority and origin-default semantics remain unchanged.
