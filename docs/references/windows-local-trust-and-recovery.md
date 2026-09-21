---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-09-19
canonical_for: external research on native-Windows isolation, loopback-browser security, and local durability
---

# Native-Windows trust and recovery references

Process-profile lifecycle sources rechecked 2026-09-19; other source summaries
retain their 2026-08-14 review. These are inputs to bounded platform spikes, not claims
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
