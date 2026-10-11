---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-07
---

# ADR 0014: Recover research after device replacement with a separate recovery key

## Context

[ADR 0008](0008-private-research-workspaces.md) selected private, project-specific
research storage outside Git, while leaving the device/key-loss policy for the
user. On 2026-09-25 the user selected encrypted backup plus a separately held
recovery key, with new-device approval-key registration to continue research.
This records that product policy; it does not claim implemented or validated
backup, custody, recovery or native authorization.

## Decision drivers

- Research and its scientific provenance must outlive one laptop.
- Restoring data must preserve prior judgments and their original authority.
- A hardware-bound signing key must not become a portable plaintext credential.
- The manual/offline workflow must remain available without AI or a service.

## Options considered

- Bind future accepted writing exclusively to the original device key: simpler,
  but losing that key prevents continued accepted work under that identity.
- Use an encrypted backup with a separately held recovery key and explicit
  new-device enrollment: selected; supports replacement at the cost of recovery
  key custody and a separately validated authority transition.
- Delegate recovery to a hosted account or cloud service: not selected; it
  introduces a dependency and authority not authorized by this decision.

## Decision

The intended product supports restoring research onto a replacement device
using an encrypted project backup and a recovery key retained separately by
the researcher. This recovers the project records and their provenance/pending
work; original external experiment artifacts remain references unless they
were explicitly included under the backup boundary.

Research-data recovery and signing authority are distinct. Device signing keys
remain non-exportable within the selected OS-backed boundary. A restored project
retains the original historical records, public verification keys and signatures.
After verified restoration, the researcher explicitly enrolls a new device
approval key before new accepted operations can continue. Record the authority
transition; do not re-sign old history or silently treat an unsigned import as
accepted history. Possessing readable data alone does not grant write authority.

The recovery key must stay outside Git, provider context, ordinary diagnostics
and contributor journals. Researcher-controlled local backup is the default;
this policy adds no automatic upload, account enrollment or cloud synchronization.

## Consequences

- The researcher must retain the encrypted backup and its separate recovery
  key. If all applicable unlock/recovery methods are lost, the data cannot be
  recovered. Exposure of the recovery key together with the backup exposes the
  research and compromises the recovery boundary.
- A source checkout, readable export or terminal draft checkpoint is not this
  verified project backup. ADR 0013 continues to govern unaccepted UI drafts.
- The encrypted format, key wrapping, authenticated history/authority manifest,
  safe restoration, key rotation and treatment of old-device authority still
  need implementation review and executable tests. No encryption algorithm,
  database, installer or production identity is selected by this policy alone.
- R2 native custody, private delivery and worker isolation remain prerequisites
  for protected storage and enrollment. This decision resolves the user-owned
  policy choice; it does not waive those gates or the private-source gate.

## Validation

Before promising private research custody, demonstrate:

1. restoring an approved encrypted backup into a fresh private destination with
   the correct recovery key preserves records, provenance and pending work;
2. wrong/missing keys, altered or incomplete backups and unsupported versions
   fail without replacing an existing project or inventing accepted records;
3. historical signatures verify under their original public keys after restore;
4. data restoration alone cannot authorize a new accepted write; explicit
   native enrollment creates a distinguishable new authority transition;
5. cancellation/interruption of restoration or enrollment preserves the original
   data and permits diagnosis without AI, a provider or an account service;
6. an actual supported replacement device can continue the verified project;
   a same-host disposable round trip is not cross-device evidence.

## Supersession

Partially superseded by [ADR 0016](0016-own-project-source-release.md) for
validation timing: the first tested same-device source release may precede
replacement-device continuation. That capability remains unavailable until
its actual-device proof; the recovery policy and authority separation remain.

This ADR originally supersedes no earlier decision. It fills the recovery-policy
checkpoint left open by ADR 0008 and
preserves its placement, privacy and authority constraints. It does not change
the limited UI checkpoint decision in ADR 0013.
