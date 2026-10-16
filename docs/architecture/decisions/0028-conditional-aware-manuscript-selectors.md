---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0028: Resolve provably disjoint literal manuscript labels

## Context

Actual-paper report #19 finds that ADR0026's whole-file conditional refusal
prevents reading otherwise independent figures and sections. The owner authorizes
IM02 in the [existing import-usability plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-history-and-versioning-detail).
Saved selectors must keep their original interpretation; manuscripts remain
read-only and no TeX execution or scientific verification is introduced.

## Decision drivers

Reuse maintained labels without manuscript edits, refuse uncertain selection,
preserve exact historical fingerprints and origin, and keep all prior schemas
and replay bytes unchanged. Support selected metadata registration together.

## Options considered

- Remove conditional checks from v1: silently changes saved interpretation.
- Execute TeX or expand macros: adds an unnecessary tool/file boundary.
- Keep whole-file refusal forever: prevents the reported ordinary paper use.
- Add a bounded independent lexer version and explicit old-binding upgrade:
  selected within the owner-approved IM02 scope.

## Decision

New tex-selector/v2 recognizes balanced primitive conditionals and literal
newif-declared switches after comment/code masking. A literal false archive with
no else is excluded only when its conditional boundaries are provable. Unknown
switches, ambiguous declarations, dynamic structure and malformed nesting refuse.
Possible branches must be structurally self-contained. Masking literal code or
macro bodies cannot hide conditional terminators in uncertain branches; refuse
those ambiguous cases. No switch value, macro or include is evaluated.

A label outside every conditional may resolve. A selected span inside, overlapping
or enclosing a conditional refuses with a source line. Unknown-branch occurrences
of the selected label remain ambiguous; dormant false-archive duplicates do not
become active labels. Exact original bytes, figure/table captions, full-file and
span digests retain their separate meaning. Maximum source/span bytes stay2MiB/
64KiB; nesting/region ceilings are32/2,048. Supported labels and abstract selection
retain the existing structural subset; this is not a TeX rendering verdict.

Keep tex-selector/v1 resolution and refresh unchanged. New CLI label connections
use v2; explicit label-version1 retains legacy behavior. Saved v1 connections
upgrade only through a reviewed source-refresh retaining the same label/kind,
prior association, history and writing. Upgrade cannot switch labels, relocate
and edit together, restore review authority or silently occur on load.

Source binding/association preview/refresh v3, command17, work28/project24 and
personal/backup frame16 carry the new contract. Metadata-batch/v2 admits explicit
versioned anchor selectors alongside marker entries; v1 stays closed. Existing
scientific and H/A/U origin rules and atomic selected-batch publication remain.
Project24 accepts existing work and shared-audit history so connection upgrade
does not rewrite science. Earlier frames and schemas remain unchanged.

For v2 registered spans, report one file-level literal-TeX coverage notice.
Recognized structural wrappers alone do not produce a warning on every anchor;
unsupported commands within a span still produce its local warning. No lexical
warning or absence of warnings certifies scientific validity or rendered coverage.

## Consequences

The researcher can register existing main-text labels without inserting marker
comments. Ambiguous or unsupported source remains unresolved and writing stays
readable. Marker-based caption slices and protected replacement are unchanged.
Older builds refuse the new frame; retain a private backup before upgrade or
first new-format save for rollback. No native key, provider permission,
scientific confirmation, manuscript writer or release authorization is added.

## Validation

Check disjoint/inside/enclosing conditions, false/nested archives, declarations,
malformed/cross-branch structures, code/definition masking and conditional-token
ambiguity. Check v1 refusal and unchanged exported schemas, exact CRLF/caption
bytes, move/delete/duplicate/source refresh, command/selector/frame mismatch,
selected batch atomic refusal, independent origin, shared-audit upgrade and
save/backup/fresh return. Exercise actual terminal cancel/confirm and source ZIP.
The [existing execution plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#actual-paper-import-usability-implementation-plan)
owns measured evidence and remaining private-paper/release qualification.

## Supersession

Partially supersedes [ADR0026](0026-literal-label-manuscript-associations.md) only
for new v2 selectors and explicitly upgraded bindings. Its v1 semantics, marker
contract, read-only boundary, exact identities and origin/retention rules remain.
