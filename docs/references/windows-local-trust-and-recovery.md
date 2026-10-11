---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-09-22
canonical_for: external research on native-Windows isolation, loopback-browser security, and local durability
---

# Native-Windows trust and recovery references

WebAuthn capability sources checked 2026-09-21 and assertion/cancellation sources
checked 2026-09-22; process-profile lifecycle sources
rechecked 2026-09-19; other source summaries retain their 2026-08-14 review.
These are inputs to bounded platform spikes, not claims
that ClaimBranch already enforces the described guarantees.

## Process and IPC isolation

Primary sources:

- [AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)
- [Implementing an AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer)
- [CreateAppContainerProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-createappcontainerprofile)
- [DeleteAppContainerProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteappcontainerprofile)
- [Windows application IPC](https://learn.microsoft.com/en-us/windows/apps/develop/communication/interprocess-communication)

Windows provides sandbox identities, capability-scoped resources, and IPC
mechanisms that may support denying a model/provider process access to the
canonical store, authorization key, and private receipt channel. The P1 spike
must prove the exact standard-user denial and user-presence path on the
supported Windows build. Merely encrypting a key with the current user or
checking a request's actor field does not prove a foreground human gesture.

An AppContainer profile creates per-user/per-app folders and registry storage.
Deletion targets the exact profile name and should follow closing its storage
handles; a failed deletion leaves undetermined state. The
[disposable isolation probe](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#windows-isolation-probe)
uses this lifecycle without adopting or deleting existing profiles. Its
observed results belong to that plan, not to these general API descriptions.

## Foreground authorization candidate

Primary sources checked 2026-09-21:

- [WebAuthn API version](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthngetapiversionnumber)
- [Platform-authenticator availability](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthnisuserverifyingplatformauthenticatoravailable)
- [Assertion operation](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthnauthenticatorgetassertion)
- [Delete a platform credential](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthndeleteplatformcredential)
- [Microsoft WebAuthn header and API-version inventory](https://github.com/microsoft/webauthn/blob/master/webauthn.h)

The two discovery calls report API version and whether a user-verifying
platform authenticator is available. Neither verifies a gesture or an exact
review. The assertion operation takes client data and a parent UI window; the
deletion operation targets an explicit credential ID. Microsoft's header lists
credential deletion as an API-version-4 addition.

The [A2 capability check](../development/workflow.md#a2-windows-authorization-capability-check)
therefore investigates API version 4 plus platform-authenticator availability
without invoking assertion or credential operations. This is a candidate
screen, not evidence of private-key custody, foreground consent, broker IPC,
single-use receipt consumption, cleanup, or product support. A later native
experiment must prove those separately; no account/device enrollment or
existing credential modification follows from an availability result.

Assertion and cancellation sources checked for the A2 plan review:

- [WebAuthn assertion verification](https://www.w3.org/TR/webauthn-3/#sctn-verifying-assertion)
- [Windows assertion options](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/ns-webauthn-webauthn_authenticator_get_assertion_options)
- [Windows assertion result](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/ns-webauthn-webauthn_assertion)
- [Cancel an operation](https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthncancelcurrentoperation)
- [OpenSSL digest signing and verification](https://docs.openssl.org/3.6/man1/openssl-dgst/)

WebAuthn assertion verification checks the expected challenge, credential,
origin/RP context, presence and required verification flags, and signature.
The Windows result contains authenticator data, credential identity, and a
signature; a successful API return alone does not define an application-level
review authorization. The Windows assertion timeout is guidance that the
platform may override. Cancellation identifies a specific operation and has
no effect if that operation is no longer in progress. The A2 plan therefore
requires an application deadline and terminal cancellation state, plus a
fresh review check before delivering an authorization result. Those application
requirements are an inference for ClaimBranch's contract, not guarantees made
by the discovery APIs or the synthetic attempt model.

The portable assertion increment uses OpenSSL only as an independent native
test oracle for a public synthetic ES256 fixture. WebAuthn authenticators sign
the authenticator data followed by the hash of the original client data;
reserializing equivalent JSON changes the signed message. The probe checks
those exact bytes and pins credential/RP/origin context before invoking crypto.
Its restricted ES256/no-extension/no-backup profile is an experimental choice,
not full WebAuthn interoperability or evidence of non-exportable Windows keys.

## Browser-loopback boundary

Primary sources:

- [Secure cookie guidance](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies)
- [Cross-site request forgery](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/CSRF)
- [Clickjacking](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Clickjacking)
- [Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts)

A loopback review UI still needs an unguessable bootstrap, strict Host and
Origin validation, a secure HttpOnly same-site session cookie, CSRF defense,
frame denial, referrer control, and no browser access to signing material or a
portable authorization receipt. The broker must independently reload the
sealed review and deliver the receipt through a private OS-authorized path. If
the browser route cannot prove that contract, H1 falls back to a native or CLI
foreground helper rather than weakening authority.

## File replacement and durable stores

Primary sources:

- [ReplaceFile](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilea)
- [FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html)
- [SQLite write-ahead logging](https://www.sqlite.org/wal.html)

The APIs and SQLite documentation explain relevant replacement, flush,
transaction, journal, and checkpoint behavior. They do not prove that a
particular ClaimBranch call order survives power loss, antivirus sharing,
external edits, disk full, or filesystem differences. The contract therefore
requires fault-injected Windows tests, expected pre/postimage digests, a
write-ahead encrypted patch saga, file and parent durability evidence,
isolated compiler output, and a recovery-only hard stop when exact state cannot
be proved.

SQLite remains the first storage-spike baseline because it can provide local
transactions and WAL behavior. It becomes an implementation choice only after
replay, crash, concurrency, size, and migration fixtures pass. A logical graph
does not by itself justify a graph database.

## Decision impact

These sources inform:

- [ADR 0005](../architecture/decisions/0005-human-authority-provenance-and-understanding-debt.md);
- [ADR 0007](../architecture/decisions/0007-research-episode-and-manuscript-saga.md);
- the trust and recovery boundaries in the
  [target architecture](../../ARCHITECTURE.md); and
- the native-Windows spikes in the
  [active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md).
