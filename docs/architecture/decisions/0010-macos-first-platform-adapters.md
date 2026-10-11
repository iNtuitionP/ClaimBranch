---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-22
---

# ADR 0010: Implement on macOS first with separate platform authority adapters

Basis: the user explicitly requested macOS replacement work for R1–R9 and
will resume the Windows work on their home machine.

## Context

The initial support hypothesis targeted Windows 11. Its WebAuthn, AppContainer,
private-delivery and filesystem experiments therefore require Windows. The
researcher currently has only a Mac; the research workflow and accepted
human-authority requirements do not intrinsically require Windows.

## Decision drivers

- Deliver the researcher's evidence → judgment → manuscript workflow on the
  available machine, without waiting for an unrelated OS adapter.
- Reuse the scientific rules, fixtures and result semantics on both platforms.
- Preserve explicit human authorization, proposal-only AI, private storage,
  complete provenance and recovery requirements.
- Report only measured platform guarantees; retain the Windows work for later.

## Options considered

- Wait for Windows before all R implementation: delays portable work and the
  user's present workflow; no longer selected.
- Treat a synthetic Mac approval as Windows authority: rejected; it establishes
  neither platform's enforcement.
- Implement shared contracts plus a real macOS adapter first, then complete the
  Windows adapter on Windows: selected; adds a second platform verification
  track but preserves common research behavior.

## Decision

macOS on the available Apple Silicon host is the first implementation and
validation target. Windows 11 x64 remains a deferred target with its own
approval, worker-isolation, IPC, path and durability evidence. macOS results
cannot close Windows-specific checks.

Separate portable domain operations, canonical serialization and projection
contracts from OS presence, signing-key access, private delivery, file I/O and
worker isolation. Continue executable portable R3 contracts while the R2
adapter is being proven; R2 is a gate on protected writes and platform readiness,
not on all unrelated implementation. R1 feedback concerns the final experience
and does not block domain rules or a reversible synthetic interaction prototype.

Use the existing Python 3.13 toolchain for portable contract work and the
installed Swift/macOS SDK for bounded native experiments. This choice does not
freeze a production store, recovery format, distributed signing identity or
installer. The Mac adapter must demonstrate real foreground presence bound to
the exact reviewed operation, cancellation/expiry, non-reusable authorization,
restricted worker access and authenticated private delivery before claiming
protected acceptance. A plain authentication Boolean is not that proof.

LocalAuthentication, Security/Keychain, App Sandbox and XPC are candidate
mechanisms, not guarantees merely because their APIs exist. Real provider
topology remains independently constrained by ADR 0009. Private-source and
key-loss/cross-device recovery gates remain required before real research use.

## Consequences

The current R sequence can make progress on Mac. The living ExecPlan separates
portable work, Mac observations and deferred Windows observations. Existing
Windows probes remain reusable and are not relabeled as Mac tests. User-visible
readiness must name the actual supported host and unavailable capabilities.
No dependency installation, account change, existing-key access, model server
operation or real research import follows automatically from this decision.

## Validation

- Run identical portable scientific and serialization fixtures on both hosts.
- Compile and execute bounded Mac probes with owned disposable synthetic data;
  distinguish capability discovery from actual human presence and isolation.
- Reject changed, stale, cancelled, replayed and cross-project approval paths.
- Verify the actual worker and private delivery boundary; a helper's denial
  alone does not establish confinement of an external model server.
- Preserve Windows-only checks as pending until run on the Windows target.

## Supersession

None. This changes the living support hypothesis and execution order; it does
not reverse ADRs 0005, 0007, 0008 or 0009.
