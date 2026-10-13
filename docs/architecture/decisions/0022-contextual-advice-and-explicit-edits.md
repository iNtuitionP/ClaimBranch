---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-12
---

# ADR 0022: Separate contextual advice from explicit graph-edit proposals

## Context

The owner requested implementation of the
[contextual assistance plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#l04-contextual-assistance-implementation-order)
after reviewing its philosophical fit. A researcher should discuss selected
science without requiring the entire answer to become graph items. The current
v2 validator permits critique alone, but couples it to any returned typed items.
An actual public response failed that validation; its precise cause was not
retained. This decision does not relabel that failure or prove its repair.

## Decision drivers

- Help the person form their judgment in the paper graph, with minimal bookkeeping.
- Keep useful advice readable independently of a malformed edit proposal.
- Preserve AI origin and human authority through explicit selection and return.
- Reuse manual construction, provider boundaries and personal storage.

## Options considered

- Require the existing whole typed result for every discussion: simple reuse,
  but advice availability still depends on unrelated graph-item correctness.
- Parse every natural-language answer into graph operations automatically:
  ambiguous and contrary to human-led construction; rejected.
- Separate bounded discussion from explicit edit preparation: selected. It
  needs a versioned origin/retention contract, but allows useful prose and
  narrowly validated actions without a general agent runtime.

## Decision

Offer optional contextual discussion in the existing terminal graph. The exact
request contains explicitly selected recorded science, an optional draft, the
person's question and any explicitly selected earlier replies. A model returns
bounded plain text, locally wrapped as `claimbranch.provider-advice/v1`. It has
no graph items or staging interface. Keep its original request/model/context,
answer identity and human question in the existing private workspace.

A person can subsequently request a small typed edit, or locally select a
passage into an editable claim/plan/connection form. Preparing an edit is not
recording science. The application validates targets/dependencies and shows
the graph effect; recording reuses the person's reason and independent
explanation choice. Preserve selected advisory/action origins through human
edits and return. A planned experiment tests its target claim; it cannot supply
an observation or support merely because it was proposed.

AI may recommend a next step in prose. Application action controls must remain
distinct from model recommendations. No hidden extraction request, background
request, automatic scientific write or model tool is introduced. Retain the
fixed relay's empty tool list, actual deployment checks and exact one-shot
outbound choice. Changing modes never resets the existing three-attempt budget
per owning judgment, including failures and saved history.

New advice and selected-message inputs have closed versioned schemas. Reading
legacy typed responses keeps their original validators and meaning. Retained
advice restores no send, staging or recording authority. Prior messages included
in a new request retain their original source identity; they do not silently
expand the selected graph. Retained action reuse keeps ADR 0020's identical-
context rule; changed-context model editing requires a new reviewed request.
External imports keep ADR 0021's unverified-source label and cannot manufacture
an app-owned request.

## Consequences

The first discussion slice uses a 4,096-byte question, at most two selected
earlier replies and a 16,384-byte answer, within the existing input and total
checkpoint limits. Refuse oversized input without truncating it. Optional
unsaved response payload may remain only in session when the checkpoint cannot
fit it, with availability stated. Sent questions and retained answers survive
restart/backup; an unsent question is explicitly session-only in this first
slice and participates in quit-loss disclosure. No consent or credential saves.
Selecting an earlier reply retains its text as part of the follow-up input,
as shown in the selection and outbound views. Such a referenced reply is not
eligible for separate payload erasure while that retained input depends on it;
refuse the operation instead of claiming its copies were removed.

Use explicit new workspace/work/project versions and existing atomic saves;
old checkpoints remain readable and no destructive conversion runs on open.
The implementation plan distinguishes discussion, action preparation, complete
recorded origin return and actual use. Implementing this decision is not L04
completion, live usefulness, comprehension evidence or protected authority.

## Validation

Exercise prose with no JSON/items, owned completion, controls/size refusal,
question/selected-message tampering, cancellation, stale input, shared request
budget, manual fallback and fresh-process/backup return. Then verify selective
action origin and human recording before claiming the complete connected loop.
Use actual terminal input and an exact-approved actual provider request;
fixtures cannot replace the latter. Each behavior increment receives the
owner-required pinned Opus review.

## Supersession

Partially amends [ADR 0018](0018-optional-personal-ai.md)'s typed-response and
item-origin assumptions for this new advisory path. Its personal storage,
human recording and provider/privacy requirements remain. ADRs 0003, 0005,
0019, 0020 and 0021 retain their authority and historical-format boundaries.
This does not admit a general chat home or an autonomous graph editor.
