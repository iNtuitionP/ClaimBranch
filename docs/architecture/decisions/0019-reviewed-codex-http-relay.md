---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-10-11
---

# ADR 0019: Send exactly reviewed Codex HTTP content through a one-shot broker

## Context

The owner selected their existing Codex ChatGPT login for the optional personal
AI continuation in [ADR 0018](0018-optional-personal-ai.md). Actual local controls
found that the CLI adds tools, developer/environment messages and metadata beyond
the application-input preview. Empty top-level tools and a domain-filtered TLS
tunnel cannot prove that only reviewed research content leaves the app.
The [existing L04 plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#ai-connected-github-publication-order)
owns observations, reviews and remaining qualification. This decision selects a
mechanism, not a supported-provider verdict or permission for another request.

## Decision drivers

- Show and send identical selected content, without ambient agent instructions.
- Reuse the owner's login without extracting credentials into configuration,
  saved research, diagnostics or a second account.
- Keep model output proposal-only, without tools or research/key operations.
- Bound one explicit attempt, cancellation and cleanup; preserve manual work.
- Reuse current contextual comparison, origin retention and personal storage.

## Options considered

- Forward the CLI request through opaque CONNECT: already observed to include
  unreviewed wrapper content; insufficient for exact outbound review.
- Describe every generated wrapper as consented research context: not selected;
  unnecessary instructions/tools would still leave the application boundary.
- Buy a separate API key or export a login token into application settings:
  not selected by the owner and unnecessary for this mechanism.
- Replace the generated request with independently compiled reviewed bytes at
  a fixed one-shot HTTP broker: selected, subject to actual qualification.

## Decision

Use a trusted deterministic stdlib broker for one exact HTTPS POST to
`https://chatgpt.com/backend-api/codex/responses`. It receives the frozen body
through a private process pipe, consumes and discards the complete CLI-generated
body, and forwards only fixed headers plus the CLI's opaque Bearer and optional
account header. No model-supplied destination, tools, cookies, environment or
client metadata is forwarded. Validated TLS, bounded framing/streaming, zero
redirects/retries and one counted upstream attempt remain fixed.

On the selected Mac, independently inspect the installed executable/login file
identities and private permissions without reading login content. A bounded
no-authentication `--version` preflight requires CLI 0.158.0 before creating an
ephemeral login-file alias. The actual CLI runs with an empty configuration home,
exact executable/library/scratch reads, only that credential-file read, scratch
writes and one owned loopback port. Deny other files, network, preference value
read/write, authorization rights, signal, fork, IOKit and POSIX IPC. Exact
CFpreferences Mach services and two exact OS shared-memory read-data names are
required for this client's managed-preference synchronization; no service/name
prefix, shared-memory write or semaphore allowance is permitted. SecurityServer
and trustd lookup remain denied. These target-specific exceptions require actual
positive/negative controls, and provide no blanket OS-compromise guarantee.

Use a bounded local capability catalog with no agent instructions or tools to
avoid remote catalog startup requests. Check ChatGPT authentication without token
export or refresh. Metadata establishes no account/model entitlement. The first
route explicitly selects `gpt-6-sol`; no fallback or automatic model selection.

The application owns the current preview, independently recompiled context,
HTTP digest, trusted clock and spent request/nonce. Return only a matching
one-shot wire outcome plus a checked owned typed CLI result to the existing
Codex origin controller. Neither imported history nor configuration restores
dispatch capability. Public launch remains unavailable until the actual provider
and contextual live-return checkpoint pass.

## Consequences

The broker is trusted application code running as the owner's OS user. Python
isolated mode is not an OS sandbox; confinement claims apply to the CLI and its
model/tool-facing path, not arbitrary same-user programs or the trusted parent.
ClaimBranch does not open the login file or persist token values; the broker
carries opaque authentication headers in its memory. Transient files created
by the CLI are not assumed credential-free. Normal exit removes the owned scratch.
Unconfirmed cleanup revokes its login alias where possible, retains potentially
live files, reports the exact owned directory, keeps the unclosed transport owner
and refuses another request. Never remove the user's original login or research.

`store: false` and an empty encrypted-reasoning inclusion are requested behavior,
not evidence of the service's retention duration. The exact preview must say that
actual retention remains unknown. Old approved diagnostics are spent and cannot
be rebound to another project's request. The legacy CONNECT diagnostic remains
internal and unqualified. No protected key, device enrollment, manuscript write,
new research store or model-server manager is added.

## Validation

Check exact body/header replacement, fixed TLS destination, hostile framing,
credential echo, expiry/current-input/replay refusal, async cancellation, version
preflight, uncertain cleanup and owned return. Actual CLI controls must pair
permitted scratch access with outside direct/symlink/read/write/directory and
process denials. Owned native API controls must pair preference access before
confinement with read/write denial and intact canaries, key-service denial and
fork refusal afterward. Separate whole-supervisor local peers from actual service
evidence; neither local SSE nor model metadata is inference qualification.

Obtain fresh exact outbound choice, then receive a checked owned service reply
and exercise selective human comparison/recording, reason/origin return, backup
and manual fallback. Run affected tests and the source/terminal milestone checks.
The [provider oracle](../../validation/cases/saturation.md#131-optional-ai-follow-up-acceptance-proposal)
still owns public enablement. Current observations and missing checks remain in
the existing plan; this ADR does not declare L04 complete.

## Supersession

None. Implements a narrow mechanism within ADRs 0009 and 0018 without changing
their actual-provider, exact-consent or human-authorship requirements.
