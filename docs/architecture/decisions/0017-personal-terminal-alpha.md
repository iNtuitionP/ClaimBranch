---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-07
---

# ADR 0017: Deliver a personal terminal alpha before protected research custody

## Context

The user explicitly accepted the proposed first version without device keys:
ordinary private local storage outside Git, with no application encryption or
OS-backed approval. They want a working version quickly, followed by feedback
and another implementation cycle. ADR 0016's first-release protected Mac path
kept native keys, receipts and custody recovery on that critical path.
The [release scope](../../product/releases/validation-prototype.md#55-source-delivery-readiness)
owns the selected alpha's acceptance; the existing ExecPlan owns execution.

## Decision drivers

- Make human argument construction and durable return useful before expansion.
- Stay in the experiment terminal and reuse the existing Python/curses UI.
- Preserve observed versus interpreted content, append-only evidence and origin.
- Spend effort on the complete manual journey and observed feedback.

## Options considered

- Protected Mac acceptance first: retains stronger technical authority, but
  delays feedback behind native custody/signing integration; deferred.
- Portable encrypted storage first: removes hardware keys but adds encryption
  dependencies, passphrase and recovery work; deferred.
- Ordinary private personal workspace first: selected by the user; smaller,
  portable manual workflow with an explicitly weaker protection promise.

## Decision

The first deliverable is a personal terminal workspace obtained as GitHub
source, with human-written thesis, claims, result/source references, typed
relations, judgments, notes, unfinished work, quit/restart and local backup.
It uses ordinary private files outside Git, explicit terminal confirmation,
bounded validation, exclusive sessions and interruption-safe saves. No Mac
device key, native enrollment, signed receipt or application encryption is
required. It records personal scientific history, not protected accepted state.

AI is off by default; no live provider runs in this release. Retained AI origin
is never erased by editing or imports. Source confirmation is the person's
explicit decision, never inferred from a reference, graph arrow or model output.
Global evidence corrections append; reasoning may retain alternatives.
Manuscript source remains read-only with a deliberate wording/follow-up view.
No formal protected debt closure or automatic manuscript mutation is enabled.

## Consequences

File ownership and permissions reduce accidental disclosure; they do not stop
an unrestricted same-user program or encrypt disk/backup contents. UI/help must
state this once clearly and distinguish saving from protected approval.
Existing encrypted/native records remain unchanged; no automatic decryption,
conversion, re-signing or authority upgrade occurs. A personal workspace uses
an explicit distinct format/destination and cannot confer protected authority.

The historical P0 private-case mapping remains a protected H0/H1/V0 gate. It
does not block this alpha's unrelated own-project feedback: the person supplies
and checks their own source, while missing/unverified fields stay visible.
Alpha use does not validate that old case, scientific truth or understanding.
Do not claim custody for irreplaceable data before tested save/recovery exists.
Publishing and license selection remain separate owner actions.

## Validation

Use novel content to create a paper, author a manual argument/result/judgment,
quit and reopen in a fresh process without native keys. Verify correction
history, shared identity, preserved writing/origin, failed saves, corrupt input,
competing sessions and fresh-destination backup restore. Verify wide/narrow
actual terminal input, resize and clean shell return, then the clean source
artifact. Gather user task feedback as soon as that manual loop is runnable;
unavailable SSH/IME/independent-user observations do not become invented passes
or delay showing the local version. Support claims name the tested hosts.

## Supersession

Partially superseded by [ADR 0018](0018-optional-personal-ai.md) on 2026-10-09
for the next personal version's optional live-AI sequencing. The first manual
alpha and its storage/authority boundaries remain unchanged; live enablement
still requires its own implementation and provider/egress evidence.

Partially supersedes [ADR 0016](0016-own-project-source-release.md)'s requirement
that the first usable source release deliver protected Mac acceptance/custody.
That protected program remains deferred. ADRs 0005/0006/0009/0014/0015 still
govern protected acceptance, providers and encrypted authority recovery when
those capabilities are implemented; ordinary personal records cannot satisfy
their guarantees. Human authorship, proposal-only AI, append-only evidence,
private placement and terminal presentation remain in force.
