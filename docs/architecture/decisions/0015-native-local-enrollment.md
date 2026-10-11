---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-03
---

# ADR 0015: Establish approval bindings through native local enrollment

## Context

Source-built Mac approval roles can verify an exact synthetic review privately,
but imported candidate records and caller-supplied hashes cannot establish
local authority. The researcher should reuse their existing judgment and reason.
The authorized B01 implementation and independent Opus reviews select a local
enrollment mechanism within the boundaries of ADRs 0005, 0008 and 0009.
Observed checks and unfinished acceptance belong to the
[execution plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#remaining-non-ui-implementation-ledger).

## Decision drivers

- Independently reload the exact approved code, key and protected resource.
- Deny authority from imports, self-signatures and confined proposal workers.
- Preserve existing scientific writing and separate registration from acceptance.
- Support a GitHub source distribution without a publisher account requirement.

## Options considered

- Trust caller pins or a signed imported file: rejected; neither proves local
  foreground enrollment.
- Add a separate OS account or privileged service now: not selected; expands
  deployment and recovery beyond the scoped confined-worker boundary.
- Use a fixed native-owned enrollment namespace and measured resource denial:
  selected for this Mac integration. Keychain protection alone is not creator
  provenance and does not replace the native creation path.

## Decision

Native code resolves the OS user's home independently of environment variables
and uses `Library/Application Support/ClaimBranch/enrollments-v1` outside Git.
Fresh foreground authentication creates a random local identity, an immutable
signed entry, a newly identified protected directory, and an unchanged encrypted
representation of the selected hardware-bound key in a native-minted directory.
The original candidate remains intact; no plaintext signing key is exported.

The entry binds project, exact runtime roles, restricted worker, key and resource
identities. Both native peers independently reload it. Its signature establishes
integrity; trust additionally requires the fixed native creation namespace and
the scoped worker/import write boundary. No arbitrary imported entry is adopted.

Publication is exclusive and atomic. Interrupted reservations remain inert;
uncertain publication is reported as indeterminate, never as proof of no effect.
Reserved diagnostic scratch files carry no authority. Native housekeeping and
resource-denial diagnostics share an exclusive coordination lock.

Explicit foreground revocation retains key and history while disabling future
use. It can validate the enrolled key and resource even after old executable
files are unavailable. Signing still requires the enrolled current code.

## Consequences

This boundary covers the confined proposal worker and untrusted imports. It
does not protect against arbitrary unrestricted same-user programs, administrator
or OS compromise, and does not qualify an external inference server. ADR 0009
continues to gate actual provider deployments.

Code replacement invalidates normal use. This initial API refuses enrolling an
already registered key, including a revoked one. Upgrade and replacement-device
transitions remain B05 work under ADR 0014. Public enumeration and diagnosis of
an indeterminate publication remain B08 work. Enrollment alone accepts no science,
consumes no receipt and opens no debt; B03 owns the atomic accepted-state path.

## Validation

Require native namespace/path and resource-identity checks, create-only crash
publication, concurrent diagnostic cleanup, foreign/import refusal, and actual
worker denial on the entry, key and protected binding. Observe foreground
registration, fresh-process registered signing, separate OS cancellation and
revocation. Preserve exact judgment, contributions and original candidate bytes.
Document pending observations rather than infer them from unit tests.

## Supersession

None. This implements a bounded Mac enrollment choice without changing the
accepted scientific, recovery or provider constraints.
