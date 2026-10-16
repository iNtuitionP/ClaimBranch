---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0029: Version original-source comparisons without rewriting retained history

## Context

The owner authorizes IM03 in the [import-usability plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-history-and-versioning-detail).
Routine JSON numbers, signed ledger decimals and line endings currently need
transformation declarations even when copied faithfully. Whole Markdown sections
need stable heading/occurrence selection. Changing old normalization or locator
contracts would silently change retained preview commitments and source replay.

## Decision drivers

Distinguish faithful extraction from deliberate rounding or rewriting, retain exact
original bytes and independent H/A/U influence, and keep all historical schema,
preview and replay bytes unchanged. Do not infer scientific truth or understanding.

## Options considered

- Widen the old enums/resolver: changes existing commitments; rejected.
- Compare numbers by value: loses precision and negative-zero meaning; rejected.
- Duplicate scientific records and commands for extraction changes: unnecessary;
  their meaning and shape stay unchanged.
- Version the source envelope/resolver and outer storage: selected.

## Decision

Argument-import/v3 and argument-source-manifest/v2 select original-source/v2 and
preview/v3. V2 import/manifest-v1 keep original-source/v1. New named policies are
opt-in; old schemas stay closed. Decimal comparisons preserve sign, digits and
exponent, including negative zero. Expanding notation cannot discard scale;
rounding and precision loss remain unresolved transformations. Boolean text has
its own policy. Sign/grouping and single-terminal-newline policies are narrow,
explicit transformations of representation, never scientific meaning.

Markdown sections identify an exact heading path and optional occurrence, required
when ambiguous. Their span includes the heading and descendants, ending at the
next same/higher-rank heading or EOF. The bounded literal parser ignores code and
comments; it executes no Markdown or TeX. Original byte spans and file digests,
not a guessed structural equivalence across edits, bind the preview. Extraction
remains at most16KiB, with at most65,536 indexed sections across the input.

The compact scientific seed14/ordinary command14, source-reference/v2 and
zlib-argument/v1 snapshot shape remain unchanged. The exact nested envelope
version chooses source semantics during replay. Existing `argument-envelope/v2`
is the whole-envelope digest-scope contract, not a claim that the nested envelope
has schema version2. It never denotes an individual file digest. Work29/project25
and personal/backup frame17 are mandatory for nested v3; both directions of
work/envelope, project/work and frame/profile mismatch refuse. Shared-audit opt-in
and conditional-aware manuscript selectors compose without downgrading this frame.
Earlier formats do not acquire new source semantics by opening or saving them.

## Consequences

People can import faithful numeric cells and ledger sections without invented
transformation explanations. Raw/normalized values, policy names, origins and
unresolved changes remain inspectable after save/restart/backup. Originals are
ordinary private files, not encrypted or scientifically verified. Older builds
refuse the new envelope/frame. No implicit migration, provider request, manuscript
write, evidence confirmation, explanation waiver or release authority is added.

## Validation

Check exact Decimal tuples, signed zero, precision loss, separate booleans, narrow
sign/group rules and one-line-ending removal. Check Unicode/CRLF byte spans,
heading duplicates and explicit occurrences, descendants, fenced/commented code,
source edits, extraction/index bounds and cache reuse. Verify legacy schemas,
preview commitments, deterministic source replay, typed-table origin/corrections,
closed version/frame mismatches and shared-audit/label composition. Exercise
public preparation/registration from a clean source ZIP, fresh return and exact
backup restore; the [existing plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#actual-paper-import-usability-implementation-plan)
owns observed checks and Opus findings. Private scientific fidelity remains separate.

## Supersession

Extends [ADR0024](0024-bounded-original-ledger-retention.md) to a separately versioned
original-source interpretation and outer storage. Its historical v2 envelope,
compact science, compression, limits and authority rules remain unchanged.
