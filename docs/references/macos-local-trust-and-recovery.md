---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-09-29
canonical_for: external macOS authority and isolation inputs
---

# macOS trust and recovery references

These primary sources inform the Mac-first work authorized in
[ADR 0010](../architecture/decisions/0010-macos-first-platform-adapters.md).
API availability is not proof of a complete ClaimBranch authority boundary.
Measured results and cleanup outcomes belong to the
[active plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#mac-authority-and-isolation-increment).

## Foreground authentication and protected keys

- [LocalAuthentication](https://developer.apple.com/documentation/localauthentication)
  exposes device-owner and biometric authentication.
- [Protecting keys with the Secure Enclave](https://developer.apple.com/documentation/security/protecting-keys-with-the-secure-enclave)
  explains hardware-backed private-key operations and access control.
- [TN3137: Mac keychain APIs and implementations](https://developer.apple.com/documentation/technotes/tn3137-on-mac-keychains)
  distinguishes file-based keychains from the data-protection keychain.

The installed SDK's `SecAccessControl.h`, `SecItem.h` and LocalAuthentication
error definitions were also checked. A fresh context, an exact review-bound
challenge and terminal cancellation/deadline handling are separate requirements.
Key signing may block for user interaction and must not freeze the review's
cancellation controls. Interpret cancellation codes with their error domain;
an unrelated domain's numeric code cannot establish user cancellation.

The foreground authentication experiment uses a non-persistent Secure Enclave key. Its result
cannot establish durable key custody, restart recovery, application identity,
private receipt delivery or cross-device recovery. Those require additional
implementation and explicit evidence, not an ordinary authentication Boolean.

R2 preparation review, 2026-09-23: rechecked the primary sources above and the
installed macOS SDK. `SecBase.h` names `-34018` as
`errSecMissingEntitlement`. This identifies the error class; the earlier failed
experiment did not identify a complete working entitlement/profile combination.
[TN3137](https://developer.apple.com/documentation/technotes/tn3137-on-mac-keychains)
explains that data-protection keychain access groups come from signing
entitlements authorized by a provisioning profile, carried in an app-like
bundle running in the user's login context. Secure Enclave and biometric
keychain protection use that implementation. A signed app/helper configuration
is therefore a concrete next investigation, not evidence that folder cleanup
or changing one key attribute will fix custody. No signing identity or profile
has been selected or inspected for reuse.

[Apple's Secure Enclave guide](https://developer.apple.com/documentation/security/protecting-keys-with-the-secure-enclave)
also makes the key device-bound and prevents
export/import of its plaintext. A copy of the research store cannot therefore
be described as a backup of the signing authority. Preservation of historical
verification keys, recovery of encrypted research, and authority for future
operations need distinct answers in R2/R4. The user selected replacement-device
restoration and explicit new-key enrollment in
[ADR 0014](../architecture/decisions/0014-device-replacement-recovery.md).
That policy does not implement or validate an authority-transition protocol.

R2 reconstruction inputs, rechecked 2026-09-24:

- [Storing CryptoKit keys in the keychain](https://developer.apple.com/documentation/cryptokit/storing-cryptokit-keys-in-the-keychain)
  describes a Secure Enclave key's `dataRepresentation` as an encrypted block
  usable by that same Secure Enclave. Obtaining this representation and storing
  it in a Keychain item are separate operations; it is not a plaintext private
  key export or a cross-device recovery method.
- [Reconstructing a signing key](https://developer.apple.com/documentation/cryptokit/secureenclave/p256/signing/privatekey/init(datarepresentation:authenticationcontext:))
  accepts that representation and an authentication context. The installed
  CryptoKit Swift interface confirms the constructor.
- [Disallowing authentication interaction](https://developer.apple.com/documentation/localauthentication/lacontext/interactionnotallowed)
  and the installed `LAContext.h` describe noninteractive Keychain access.
  `SecBase.h` identifies `errSecInteractionNotAllowed` as `-25308`;
  `LAError.notInteractive` is separately classified by its error domain.

These APIs justify an independent, disposable reconstruction measurement without
creating another App Sandbox container. Reading a public identity after restart
does not establish signing authority, application-private custody or integrity
of all bytes in the opaque representation. The implementation records both a
changed representation that still reconstructs and an unclassified constructor
failure as incomplete integrity evidence. Authentication denial is not tamper
detection. See the [R2 execution evidence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r2-preparation-tied-to-durable-research-use)
for measured outcomes and the remaining product gates.

Foreground reconstruction inputs, rechecked 2026-09-25:

- [Secure Enclave P-256 signing keys](https://developer.apple.com/documentation/cryptokit/secureenclave/p256/signing/privatekey)
  expose reconstruction with an authentication context and signing of data
  using SHA-256. The fixed review binds its own text and fresh challenge to the
  expected key; this binding is ClaimBranch's implementation responsibility.
- [Invalidating an authentication context](https://developer.apple.com/documentation/localauthentication/lacontext/invalidate())
  stops pending policy evaluations with the LocalAuthentication app-cancel
  error. A native error still needs its domain checked. Context invalidation
  does not replace terminal application state that rejects a late result.
- The installed SDK's `mach/mach_time.h` defines `mach_continuous_time()` as
  advancing during sleep. The bounded review uses it for its deadline;
  timer delivery alone is insufficient if the machine sleeps or the main
  loop is delayed.

Independent public-signature verification proves only a signature/message/key
match. It cannot establish a human's scientific understanding, authentic IPC
peers or an entire application's custody. The native experiment keeps those
product authority claims false.

Explicit-evaluation inputs, rechecked 2026-09-27:

- [Policy evaluation](https://developer.apple.com/documentation/localauthentication/lacontext/evaluatepolicy(_:localizedreason:reply:))
  supplies an asynchronous success/error callback. UI depends on the policy,
  device and configuration; the callback is not evidence that a window appeared.
- [Authentication reuse duration](https://developer.apple.com/documentation/localauthentication/lacontext/touchidauthenticationallowablereuseduration)
  concerns recent biometric device unlock. The installed `LAContext.h` also
  explicitly excludes reuse of biometric matches within/between applications
  from that property's scope. Setting it to zero does not prove every implicit
  key operation opens a fresh dialog.
- The reopened-key probe now requests explicit device-owner evaluation, then
  uses the same context for the access-controlled key with implicit interaction
  disabled. Failure, cancellation and expiry reject entry into signing. This
  preserves protected key use instead of treating an authentication Boolean
  as an authorization receipt. Actual prompt/cancellation observations remain
  in the execution plan.

## Distribution and product identity

These are inputs for optional native binary distribution and a candidate key
custody mechanism. The existing [GitHub source-delivery target](../product/product-spec.md#2-target-user-and-support-setting)
does not select Developer ID, notarization, an Apple publisher account or a
public installer. The [execution proposal](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#mac-package-and-custody-decision-packet)
that recommended that distribution path was withdrawn after the user's scope
correction. External API requirements do not determine product scope.

Deployment inputs, checked 2026-09-28:

- [Developer ID](https://developer.apple.com/developer-id/)
  supports signing Mac applications distributed outside the Mac App Store and
  submitting them for notarization. [Developer ID certificates](https://developer.apple.com/help/glossary/developer-id-certificate/)
  are issued to developer-program members. This is publisher-side program
  identity, not a researcher's device approval credential.
- [Apple Developer Program](https://developer.apple.com/programs/)
  lists a USD 99 annual membership; local pricing and eligibility may differ.
  Free developer accounts permit development/testing but are not equivalent
  to Developer ID distribution. A recipient does not become the publisher by
  installing its signed artifact.
- [TN3137](https://developer.apple.com/documentation/technotes/tn3137-on-mac-keychains)
  requires a user login context for the data-protection Keychain. Its access
  groups come from signing entitlements authorized by a provisioning profile,
  which needs an app-like host bundle. Notarization/Developer ID and Keychain
  entitlement authorization are separate requirements; neither establishes
  ClaimBranch's full custody or private peer boundary by itself.

These facts do not authorize an account action or credential reuse. If a
specific custody implementation selects provisioned Keychain access, its
profile requirements and source-build feasibility need evidence; that profile
is not a universal requirement for source distribution. Product key custody,
trusted launch and update/recovery behavior remain unproven by a source ZIP or
an ad-hoc signature alone.

## Local peer identity

Private-delivery inputs, checked 2026-09-27:

- The installed `sys/un.h` supplies `LOCAL_PEERTOKEN` for connected Unix
  sockets. The experiment obtains the kernel's audit token, not a role or PID
  offered by the remote message.
- [Guest audit attributes](https://developer.apple.com/documentation/security/ksecguestattributeaudit)
  and [dynamic guest lookup](https://developer.apple.com/documentation/security/seccodecopyguestwithattributes(_:_:_:_:))
  inform the Security framework check. The installed `SecCode.h` describes
  dynamic validity/requirement checking and signing information. Its C API
  accepts a dynamic `SecCode` for signing information despite the Swift-imported
  static parameter type; dynamic information requires the dynamic object.
- `CSCommon.h` supplies the hardened-runtime signature flag. Signing
  information distinguishes on-disk flags from current running status. The
  probe requires both and tests rejection with an exactly pinned but unhardened
  binary, instead of equating a matching CDHash with runtime hardening.

These APIs identify executing code; they do not establish a foreground human
decision or prevent an unconstrained same-user process from launching that code.
Temporary ad-hoc signatures and caller-configured pins are experimental inputs,
not the product's identity/enrollment or worker boundary. Measured evidence and
remaining gates belong in the execution plan.

## Authenticated recovery artifacts

Recovery-mechanism inputs, checked 2026-09-25:

- [CryptoKit AES.GCM](https://developer.apple.com/documentation/cryptokit/aes/gcm)
  supplies authenticated encryption and decryption. The installed SDK and an
  actual compiled helper verify availability; that is not a claim about a
  packaged app, secret custody or a supported replacement device.
- [RFC 5116](https://www.rfc-editor.org/rfc/rfc5116.html#section-5.2)
  defines the AES-256-GCM AEAD profile. Associated data is authenticated, and
  nonce/key reuse must be avoided. AEAD does not supply application access
  control or replay protection. ClaimBranch's experiment authenticates its
  versioned header, derives a per-artifact key with fresh salt and uses a
  fresh nonce; a separately supplied expected manifest pins the known snapshot.
- [RFC 5869, Appendix A.1](https://www.rfc-editor.org/rfc/rfc5869.html#appendix-A.1)
  supplies an independent HKDF-SHA256 known-answer vector. The experiment's
  recovery input is a random 32-byte key, not a human password; this use of
  HKDF is not password hardening.
- [OpenSSL AES cipher test vectors](https://github.com/openssl/openssl/blob/master/test/recipes/30-test_evp_data/evpciph_aes_common.txt)
  supply AES-256-GCM zero-key/nonce expected ciphertexts and tags for empty and
  one-block plaintexts. These public vectors check the native crypto calls;
  they do not certify the enclosing backup format or prove worker isolation.

The implementation uses these APIs for a bounded candidate-history mechanism
experiment. Data recovery neither exports a device signing key nor confers
scientific authority. The complete authenticated history/authority manifest,
product key custody and new-device enrollment remain separate work under
[ADR 0014](../architecture/decisions/0014-device-replacement-recovery.md).

Signed candidate inputs, checked 2026-09-27:

- [CryptoKit P256.Signing](https://developer.apple.com/documentation/cryptokit/p256/signing)
  exposes ECDSA signing and public verification keys. The bounded native
  experiment uses the uncompressed public-key representation and DER signature
  with SHA-256; successful SDK compilation and an independent verifier check
  those exact calls. Its software signing fixture is test material, not a
  replacement for a protected device approval key.
- [OpenSSL dgst](https://docs.openssl.org/3.0/man1/openssl-dgst/)
  documents verifying a supplied signature against a public key and input data.
  The test explicitly selects SHA-256, supplies only public key/signature files,
  and pipes the candidate checkpoint message. This checks signature agreement;
  it does not determine whether that signer is a trusted project authority.

The caller's external signer and checkpoint expectations, canonical history
binding, and refusal of an unsigned downgrade are ClaimBranch responsibilities.
The implemented signed candidate profile preserves a verified fixture signature
through reencrypted restoration. It does not authenticate an accepted operation
chain or implement old-device revocation/new-device enrollment. The
[R2 evidence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r2-preparation-tied-to-durable-research-use)
records the exact scope and observed tests.

## Restricted workers and private delivery

Source-worker implementation inputs, rechecked 2026-09-29:
[Apple's App Sandbox entitlement reference](https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/EntitlementKeyReference/Chapters/EnablingAppSandbox.html)
describes application restrictions and separate child-inheritance entitlements.
The finite source-built proposal component is itself a sandboxed app executable,
not an inherited unrestricted interpreter or a model-server launcher. Its exact
one-entitlement manifest and actual file/IPC/network denial are independently
checked. Reusing one stable application identifier keeps its OS-managed container
separate from temporary test resources. Identifier/container continuity is not
trusted code identity: exact pinned source, bundle and CDHash checks remain
required, and no authority is stored in that writable container. Observed
results remain in the active plan; no publisher/provisioning requirement is
inferred from the independently built component.

- [App Sandbox](https://developer.apple.com/documentation/security/app-sandbox)
  limits file, network and device access through application entitlements.
- [XPC](https://developer.apple.com/documentation/xpc) provides process-separated
  services and communication.
- [XPC peer requirements](https://developer.apple.com/documentation/xpc/xpcsession/setpeerrequirement(_:))
  bind a connection to a code-signing requirement.

A sandboxed worker's denial does not prove confinement of an unrestricted
external provider. The actual process topology, scoped input, private channel
and store/key permissions must satisfy ADR 0009. App-container creation and
cleanup are OS-managed lifecycle concerns; report incomplete cleanup and stop
repeating experiments instead of accumulating containers or broadening the
user’s system permissions.

The installed `sandbox-exec(1)` manual marks that command deprecated and
recommends App Sandbox. It is not silently selected as the production boundary
when the App Sandbox experiment has a cleanup problem.

The rechecked Swift `XPCSession.setPeerRequirement(_:)` reference declares macOS
26 availability. It requires setting the peer requirement before activation and
checks received messages against that requirement. Selecting it would need an
explicit deployment minimum; the presence of this API in the current SDK does
not promise support on older Macs. Installed `xpc/connection.h` also declares
C peer code-signing requirement APIs. These are implementation inputs, not a
measured connection between ClaimBranch processes. Pinning a generic Python
interpreter or trusting a caller's role field does not establish which
application code owns a request; the proposed role-specific boundary must be
tested with the actual packaged peers.
