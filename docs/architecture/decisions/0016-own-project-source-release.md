---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-07
---

# ADR 0016: Deliver the manual own-project workflow through GitHub first

## Context

On 2026-10-07 the user asked to plan implementation around GitHub delivery,
then explicitly retained the goal that other researchers can save and resume
their own projects. Publishing only the existing synthetic preview would not
meet that instruction. The previous source-delivery checklist also required
live AI, manuscript application and actual replacement-device recovery, making
the first source release depend on the complete research product.

The [release scope](../../product/releases/validation-prototype.md#55-source-delivery-readiness)
owns feature-level acceptance; the existing ExecPlan owns the execution order.

## Decision drivers

- Deliver a complete useful research action before adding more prerequisites.
- Preserve the thesis-to-evidence graph, human judgment and durable return.
- Keep scientific acceptance distinct from draft retention and source publication.
- Validate enabled features without requiring unfinished features to ship.
- Reuse measured native work without making machine access a universal blocker.

## Options considered

- Require every H0/H1/V0 and recovery feature before any usable source release:
  preserves the earlier checklist but delays the user's delivery goal.
- Publish the existing synthetic preview as the finished app: rejected because
  it cannot retain another researcher's accepted own-project work.
- Release the manual own-project workflow first, with explicit unavailable
  later capabilities: selected. It needs real local custody and authority,
  but neither live inference nor automatic manuscript writing.

## Decision

The first usable GitHub release supports a declared Mac source checkout or
artifact, project setup, human-authored graph/research work, exact authorized
scientific acceptance, durable quit/restart and same-device failure recovery.
It retains the original reason, source context, contribution history and
unfinished writing outside Git. This is a delivery milestone, not H0/H1/V0
completion or evidence of improved scientific understanding.

Live providers and AI-influenced accepted changes, automatic manuscript writes,
accepted understanding-debt closure, replacement-device continuation and schema/
approval-runtime migration follow as separately validated capabilities. They
remain unavailable until their owning gates pass. The first release must not
silently erase existing AI influence, discharge an obligation, claim a portable
backup, or accept an untrusted history to avoid those gates. Read-only inspection
of retained history remains distinct from a newly authorized mutation.

ADRs 0005 and 0015 still govern accepted writes. The existing Mac implementation
requires its native key/custody checks when those features are used; GitHub
distribution itself requires no Apple publishing account or device enrollment.
Native integration and foreground observations are grouped at the relevant
milestone, rather than repeated for unrelated documentation or packaging edits.
An unavailable test host blocks the dependent verification, not all implementation.

## Consequences

Keep the B ledger and unfinished product gates truthful. Execute complete
own-project outcomes using the existing backends rather than adding isolated
mechanisms without a named missing condition. Reuse the separate TUI session;
do not introduce a second editor, journal or provider runtime.

Same-device custody, tested backup/recovery boundaries, source fidelity before
real use and exact authority still gate the first usable release. A release
without cross-device evidence must state that replacement-device continuation
is unavailable. It must preserve original data and reject unsupported restore,
version or executable changes, rather than silently migrate or grant authority.

For first-release same-device recovery, retain the original approval key and
trusted enrollment and verify the backed-up checkpoint. Protect backup data
with the separately held recovery key under the selected policy. A damaged work
store may be restored to a fresh resource only through a separately reviewed
same-key resource transition; initial duplicate-key enrollment still refuses.
This bounded B05 integration is required before promising resumed accepted
writing after restore. Key/enrollment loss or unverifiable recency cannot grant
write authority; independently verified readable recovery/export stays distinct.
The release promises the verified backup's contents, not unsaved or newer data.

A newer build must retain compatible read-only diagnosis/export. Accepted
writing after code replacement remains unavailable until its explicit upgrade
transition passes; help must say so rather than strand work without guidance.

The selected encrypted-backup/separate-recovery-key/new-device-enrollment policy
remains the eventual recovery contract. Its cross-device proof is required
before that capability is promised, not before shipping a declared same-device
manual workflow. No encryption, store or weaker authority mechanism is selected
by this release decision. License selection and publication remain separate
user-owned actions; this instruction authorizes planning and implementation.

## Validation

Require a clean-source own-project journey, manual graph authoring, actual
protected save/restart, preserved provenance/writing, interrupted-save and
same-device recovery checks, relevant hostile authority cases, and an unfamiliar
researcher's rehearsal on the declared supported host. Demonstrate unavailable
later capabilities cannot mutate research or manufacture evidence/debt closure.
Check the exact shipped source and required resources; a synthetic preview or
software-key fixture alone cannot close this milestone.

Preserve failing/skipped results. Run actual native custody/presence checks on
a usable Mac for enabled features; portable CI and packaging checks do not
substitute for them. Cross-device tests remain required for the later recovery
claim under ADR 0014. The release scope owns the exact current checklist.

## Supersession

Partially superseded by [ADR 0017](0017-personal-terminal-alpha.md) on
2026-10-07 for the first release's protected Mac custody/acceptance requirement.
The immediate deliverable is now a key-free personal terminal alpha; the
protected workflow below remains deferred history and future scope.

Partially supersedes [ADR 0014](0014-device-replacement-recovery.md)'s validation
timing: a tested same-device release may precede actual replacement-device
continuation, which remains unavailable until validated. Its recovery policy,
historical signatures, key separation and explicit new-device enrollment remain
accepted. No other architectural authority or privacy decision is superseded.
