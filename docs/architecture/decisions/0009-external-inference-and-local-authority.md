---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-21
---

# ADR 0009: Separate external inference from local research authority

Basis: the user accepted the recommended direction on 2026-09-21.

## Context

[ADR 0005](0005-human-authority-provenance-and-understanding-debt.md) requires
human authorization and denies model-originated accepted writes.
[ADR 0006](0006-three-graph-planes-and-provider-boundary.md) keeps providers
replaceable and their operation outside ClaimBranch. A choice between managing
every model server and trusting unrestricted servers conflates operational
ownership with permission to act on research.

The disposable Windows probe demonstrated denial of direct access by its small
restricted helper, not confinement of a real model server. Its measured results
remain in the [execution plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#windows-isolation-probe).

## Decision drivers

- Preserve human authorship without a second explanation or recording workflow.
- Keep model-server administration out of the research product.
- Enforce the authority boundary rather than treating model wording as consent.
- Prefer a narrow supported topology to an unsupported security promise.
- Keep manual work independent of provider availability and setup.

## Options considered

- Launch and manage all inference under ClaimBranch isolation: more control,
  but adds runtime/GPU compatibility and server lifecycle responsibilities.
- Trust any existing server: easy integration, but cannot establish raw-write
  denial for an unrestricted same-user process with access to research files.
- Separate inference, any tool execution, and authorized writing: selected.
  Keeps operational scope small while requiring evidence for each permission
  boundary. A connector sandbox alone does not contain its external server.
- Protect all state under another account/service, or require a VM: possible
  later mechanisms, not selected now; deployment and recovery costs remain.

## Decision

ClaimBranch does not install, launch, stop, supervise, or update inference
servers. External inference receives only approved scoped context and returns
untrusted, non-authoritative proposals. It receives no accepted-state write,
human export, approval key, or human-only operation capability. If tools become
necessary, their execution is a separate least-privilege responsibility, not
automatic execution of model-supplied commands. A general tool runtime is not
part of this decision.

The trusted local gateway and foreground authorization broker remain the only
path to accepted changes. Build and validate the AI-off and frozen-proposal
paths before live-provider integration; reuse the existing judgment and
rationale rather than adding a journal form or automatic recording workflow.

A live topology must satisfy the existing authority and privacy gates. Being
on localhost, returning compatible JSON, or receiving a user trust label does
not prove confinement. An unrestricted same-user server with relevant file
access has no demonstrated raw-write boundary; the initial plan does not add
a warning-based bypass of that gate. Unknown topology leaves the protected
live workflow unavailable while manual work remains available.

A separate host or security identity may supply isolation, but neither is
approved merely by its name: shared paths, credentials, IPC, network reach,
and the actual runtime still require evidence. Integrity and outbound privacy
are separate: even a file-isolated provider requires exact consent for
remote-capable egress. No cloud service, remote server, account, VM, or
production runtime is selected by this decision.

## Consequences

The first supported AI environment may be narrower than the compatible API
surface. Setup must distinguish compatibility from verified protection and
offer manual continuation rather than asking users to administer hidden ACLs.
Local-only classification still requires the network-denial evidence in ADR
0006. Deployment choices, broker presence, storage/toolchain, and private-data
recovery remain unresolved; this is not P1 completion or permission for real
research use. OS/administrator compromise is not covered by the small probe.

## Validation

Use the [provider authority oracle](../../validation/cases/saturation.md#13-provider-authority-and-support-oracle)
for unsupported topology, malicious output, protected-resource denial,
consent changes, provider loss, and AI-off continuation. Tests of pure binding
values are not evidence of OS presence, signing-key custody, or authorization.
Do not issue a supported-provider claim before the actual deployment passes.

## Supersession

None. This narrows implementation of ADRs 0005 and 0006 without replacing their
authority rules or rewriting their accepted history.
