---
kind: adr
status: superseded
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0026: Connect read-only manuscript spans through literal LaTeX labels

## Context

The owner selected I04 in the
[original-ledger plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#i04-bounded-label-resolution-and-source-freshness).
Existing figures/sections already have labels. Requiring extra marker comments
adds manuscript work without helping the researcher align claims and passages.
The current personal alpha remains read-only under ADR 0017; protected marker
replacement has a distinct, unchanged authority contract.

## Decision drivers

Reuse existing identifiers, keep stable internal graph IDs, preserve exact source
bytes and historical bindings, and refuse ambiguous structure without executing
TeX, expanding macros or opening includes. Preserve all old schema bytes.

## Options considered

- Marker blocks alone: exact and retained for arbitrary passages/caption slices,
  but insufficient for the reported existing-paper workflow.
- Execute or fully expand TeX: too broad and grants unnecessary file/tool access.
- Literal bounded structural scanning with a new selector/binding version:
  selected for manual personal paper and imported profiles.

## Decision

A tex-selector/v1 identifies a literal label or the abstract environment. Read
standard sectioning commands and figure/table environments, including starred
forms; figures/tables include captions. Section labels immediately follow their
heading; spans include child sections and stop before the next same/higher rank
or end of document. Labels inside subfigures/other nested environments are
unsupported. Multiple figure labels can name the same span, but duplicate literal
label values refuse. No relationship is inferred from textual containment.

Comments, inline verb and supported literal code environments are excluded.
Literal environments require an exact standalone closing line; comment closing
starts at column zero. Unhandled inline-code forms, dynamic/conditional structure,
structural redefinition, malformed groups and ambiguous/unclosed environments
refuse. This is bounded literal inspection, not a TeX rendering/fidelity verdict.
Missing/unsupported selectors remain visibly unresolved. Existing LF-exact marker
parsing and protected replacement preview are unchanged.

Source binding v2 adds the selector and exact span digest beside full-file digest
and identity. Initial association preview v2 and refresh review v2 retain these
bindings without source writes. Internal anchor ID remains distinct from the
LaTeX label. Command15 registers the read-only span, kind, explicit declared
origin and scientific associations. Work26/project22 and personal/backup frame14
retain these new bindings. Manual seed4 and imported seed5/14 use the new
formats; their underlying scientific and explanation limits are unchanged.
Old envelopes/commands remain byte-identical and readable; no old schema acquires
new optional source fields. Whole files remain bounded at2 MiB and spans at64 KiB.

## Consequences

Moving an unchanged figure preserves its span digest while file freshness changes.
Changing its caption changes the span; deleting/duplicating a label makes it
unresolved. Refresh/relocation preserves the selector and historical writing;
no consent revives. Figure/table registration must match the literal span kind.
Caption-only slices still require marker blocks. Private save/backup retains
bindings; selected public output omits manuscript text and private source paths.
Older builds refuse frame14. Take a private backup before registration/first save
if older-build rollback is needed; restore into a fresh compatible destination.
No provider, native key, scientific confirmation or manuscript writer is enabled.

## Validation

Check label-only initial CLI/PTY use, section hierarchy, caption and CRLF bytes,
move/change/delete/duplicate cases, fake labels in comments/code, spaced tokens,
exact literal closing semantics, malformed/dynamic TeX refusal, byte limits,
kind/span mismatch, fresh save/backup/restore and unchanged old schemas/markers.
Check source refresh in an existing personal workspace without weakening the
actual encrypted/personal store exclusivity. Current execution evidence and
remaining connected release checks belong to the existing ExecPlan.

## Supersession

Partially superseded by [ADR0028](0028-conditional-aware-manuscript-selectors.md)
for new conditional-aware v2 selectors and explicit legacy-binding upgrade;
v1 semantics remain unchanged. Adds a separate read-only source selector to
ADRs0017/0023/0024; protected
marker-writing and personal origin/retention contracts remain in force.
