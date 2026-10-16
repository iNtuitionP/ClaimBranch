---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-16
---

# ADR 0031: Retain completed-work protocols and explicit result replacements

## Context

Actual-paper report #22 needs historical preregistration on completed experiments
without fake unrun plans, and a direct link from a corrected result to its replay.
The owner approves link-only replacement in the
[IM05 plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-history-and-versioning-detail):
changing observation status or eligibility requires a separate explicit review.
ADRs0023/0030 require honest source claims, partial meaning and date precision.

## Decision drivers

Keep original predictions, failures, reasons and current evidence inspectable.
Do not infer preregistration from a commit reference or app ingestion time. Keep
link provenance separate from measured-value provenance, and preserve old bytes.

## Options considered

- Carrier planned experiments: misrepresents completed work as unrun; rejected.
- Reuse evidence-event supersession: confuses value events with observation
  identities and can imply automatic invalidation; rejected.
- Widen old contracts: changes historical interpretation; rejected.
- New completed-target protocol and link-only replacement contracts: selected.

## Decision

Protocol-input/v2 adds `register-experiment-protocol` and
`record-observation-replacement`, carried by command19. Metadata-batch/v3 admits
these alongside existing protocol operations. Completed registration pins the
scientific experiment digest and creates its explicit association in one reviewed
operation. It creates no plan or experiment execution. Missing historical metrics
stay missing; comparison with a nonexistent plan is null, not a passing match.
Original and revised gates/outcomes use the same association. Source-claimed
commitment, before/after-result disclosure and contradictions remain unverified.

Argument-import/v5/source-manifest/v4 permits an observation's optional replacement
declaration. Compact seed18/ordinary command18 retain their existing shape; replay
derives the typed registry from the exact retained snapshot. Selecting a replacement
requires its prior observation. Initial relations have source dates/pointers, not
fabricated past app operations or timestamps. New current links pin both latest
observation revisions and carry their original reason and independent new-input
origin. At most512 links fit within unchanged aggregate storage limits.

Both endpoints must exist. Refuse self-links, a second successor for the same
prior observation, cycles and a provably earlier replacement date. A chain may
continue through another explicit link. Compare only like date precision; missing
or mixed day/timestamp precision stays unknown. App record order is not proof of
outside experimental chronology. Preserve both observations' original values,
status, eligibility and event histories. A separate evidence review is necessary
to change those; a replacement does not become scientific support automatically.

Graph readers show a closed non-scientific `replaces` relation and dependent-path
context. The declaration's origin/unresolved field belongs to the link, separately
from observation values; source-aware judgment review retains both influences.
The exact source reader can inspect that declaration. New-input contribution
origin is separate from the personal confirming actor, as in existing metadata.
No understanding waiver or per-record explanation form is added.

Work31/project27 and personal/backup frame19 are mandatory for import/v5 or
command19. They compose with old scientific seeds, selectors and shared audit
without rewriting earlier prefixes. Canonical-share/v4 uses opaque endpoint IDs,
retains declaration origin/coverage and omits source context/commit references;
reasons remain separately opt-in. Old schemas, formats and golden histories stay
unchanged. No provider, protected writer or manuscript mutation is enabled.

## Consequences

Completed work remains completed while preregistration and replacement lineage
are inspectable. The app does not attest to a source's historical truth. New
formats need a current build; keep a private backup for older-build rollback.
Ordinary private storage remains unencrypted. This does not verify the private
paper, researcher usefulness or release readiness.

## Validation

Register six completed protocols with zero added plans; inspect original failure,
after-result amendment and incomplete historical metrics. Check exact target/basis
mismatches, self/cycle/duplicate/date refusal, declaration versus value origin,
unchanged evidence/status and old prefixes. Exercise graph/source/review/share,
fresh personal save/reopen and exact backup restore from an extracted source ZIP.
Run affected contracts and pinned Opus review; the existing plan owns evidence.

## Supersession

None. Extends ADRs0023/0030 with separately versioned historical relationships;
legacy plan protocols, evidence corrections, origin and authority rules remain.
