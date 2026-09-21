---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-11
---

# ADR 0008: Keep research records in private workspaces outside Git by default

Basis: user-approved storage direction; this is a decision, not implemented
storage or a migration of existing user data.

## Context

ClaimBranch's public source distribution must be independent of its users'
private research histories. The earlier topology placed durable metadata under
the paper Git root. The user's real experiment artifacts are on a remote
server, so placing all inputs beside the application is also inappropriate.

## Decision drivers

- Users form a judgment once, without maintaining a second narrative or log.
- Publishing code must not implicitly publish research records or credentials.
- Accepted history remains readable and recoverable without AI or the network.
- Raw experiment data need not move just to record a research judgment.
- Default privacy must not depend solely on remembering Git ignore rules.

## Options considered

- Store canonical records inside the paper repository with ignore rules:
  convenient co-location, but easier to accidentally stage private history.
- Use Notion or a hosted service as the canonical store: adds an account,
  network, and synchronization dependency to the core workflow. Not selected.
- Use a private, project-specific local workspace outside Git by default:
  selected. It separates distribution from research, at the cost of explicit
  project association, backup, and relocation handling.

## Decision

The default canonical research workspace is local, user-owned, and outside
the application checkout and paper/code Git working trees. It is associated
with one research project, not derived from the application's install path.
Initialization previews the resolved paper and workspace locations separately.
The physical directory name, association format, and database remain P1
implementation choices; this decision does not authorize an in-repository
storage mode or a cloud synchronization service.

The workspace owns accepted judgments, evidence references, contribution and
authorization history, and recovery state. Raw artifacts stay at their linked
source unless explicitly imported. An inaccessible source must not become
verified merely because its reference or a human-written description exists.
Remote artifact references do not imply an SSH client or ingestion platform.

Human-readable views expose the same canonical records, not another required
form. Sharing is a separate, user-approved export; a readable export is not a
second mutable authority or automatically a complete restore backup. Do not
overwrite human-edited exports or synchronize them back implicitly. The
contributor Notion journal remains independent and user-invoked.

Credentials and signing keys stay in the OS-backed credential boundary;
disposable caches remain distinguishable from durable data. Moving records
outside Git reduces accidental publication, not same-user process access.
ADR 0005/0006 authority, read-scope, and egress protections still apply.

## Consequences

- Cloning or publishing the paper no longer carries private research history
  by default. Conversely, cloning it is not a research-record backup.
- Moving a paper needs a verified association to its existing workspace; a
  missing or ambiguous association must not silently create replacement history.
- Backup, portable export, and key-loss recovery must be distinguished. P1
  must present the remaining recovery trade-off for user approval before
  promising safe custody of irreplaceable research; no recovery algorithm is
  selected here. Public source availability alone makes no such promise.
- Database transactions and manuscript writes still use separate authority
  and recovery paths under ADR 0007. Co-location or a shared drive is not
  required for correctness; unsupported cross-volume behavior must fail safely.
- No existing app data exists to migrate in this repository. Contributor
  journal state and the private source fixture are not migration targets.

## Validation

P1 defines concrete interfaces and fixtures; H0/H1 must demonstrate:

1. initialization from inside either Git tree selects an external default
   workspace, resolving path aliases before writes;
2. dry-run creates no workspace or accepted state and reports both locations;
3. paper relocation cannot silently fork or lose the accepted history;
4. source unavailability preserves existing readable records without claiming
   fresh source verification;
5. cache rebuild preserves the accepted manifest, and model-originated direct
   writes remain denied at the new location;
6. export never publishes automatically or replaces a human-edited file, and
   a restore exercise verifies the complete approved backup boundary.

## Supersession

None. ADR 0004 remains a naming proposal and is reconciled with this placement
decision. No accepted authority or manuscript-safety decision is reversed.
