---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-12
---

# ADR 0020: Review retained proposals without another inference request

## Context

The owner explicitly selected local re-review of an existing AI response on
2026-10-12. Requiring another funded request merely to select saved suggestions
creates avoidable friction and may return different advice. The previous design
required a fresh request after restart even when complete proposal origin remained.

## Decision drivers

- Preserve human selection and complete AI origin without redundant inference.
- Show original and current research context before staging retained items.
- Never restore outbound consent or silently revive an old comparison.
- Retain manual editing, ordinary storage and existing scientific review.

## Options considered

- Require new inference after every restart: rejected for retained valid items.
- Automatically revive old review and selection: rejected.
- Explicit short-lived local review against current context: selected.

## Decision

A retained, originally checked proposal may enter a new explicit local review
for its original judgment owner. Show original input, current input and original
request/model/response/trace identity. Require byte-identical canonical original/current context and equal digests,
then revalidate typed items against that context. Changed science, even if the
old items are structurally compatible, requires a new proposal. Retain old history unchanged. Failed,
erased, missing or incompatible responses cannot stage.

New comparison and dependency-closed human selection precede staging. The local
review expires after 120 seconds and is invalidated by changed source, included
draft, payload or active owner. Reopening creates no request, consumes no network
budget and restores no old authorization. Staging remains unaccepted writing;
personal recording still requires the researcher's judgment/reason and explicit
review. Repeated reviews reuse existing item identities and preserve human edits.

The first implementation uses complete proposal histories already retained by
the app. A separate operator diagnostic lacks that persisted origin envelope;
it must not be forged into a historical application attempt. Importing such a
response requires a separately implemented, explicitly labeled source binding.

## Consequences

Previously saved proposals can be useful with AI off. Stored formats need not
change: the new local review capability is ephemeral, while item origins refer
to the unchanged original trace. History inspection alone remains read-only.
This finite implementation refuses changed context rather than inventing a new
provenance record. Identical context does not certify scientific correctness or
understanding. Changed-context reuse requires an explicit durable basis design.

## Validation

Check explicit original/current reading, no transport or additional attempt,
unchanged trace/history, context/payload/owner/expiry refusal, dependency closure,
repeat-selection identity, preserved human edits, checkpoint/restart and backup
origin. Reopen must restore no active review. Keep public live qualification
separate from these local operations.

## Supersession

None of the accepted authority ADRs is reversed. Refines the historical-response
interaction under ADR 0018; supersedes the former design rule that every new
incorporation from retained history requires another provider request.
