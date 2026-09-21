---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-08-14
---

# ADR 0006: Separate canonical, context, and execution graph planes

Basis: user-confirmed graph-first direction refined by architecture review

## Context

“Graph” can refer to accepted scientific state, retrieval links assembled for a
model, or an agent's execution history. Treating these as one graph would let
similarity, extraction, tool activity, or provider output acquire scientific
authority accidentally. It would also make AI availability or a particular
graph database a prerequisite for reading accepted research.

The user wants graph engineering to support the product and wants local LLM
serving to be a learning path, while retaining a human-owned paper and an
AI-disabled core.

## Decision drivers

- Accepted science needs stable semantics, append-only history, and explicit
  human authority.
- Retrieval context must be aggressively rebuildable and replaceable.
- Provider and tool traces need audit retention without becoming claims.
- Local and hosted models must share one proposal boundary.
- OpenClaw, MCP, GraphRAG, embeddings, and graph-native storage must remain
  optional integrations justified by observed need.

## Options considered

- Store every scientific, retrieval, and execution relationship in one graph.
  Rejected because authority and retention become ambiguous.
- Keep only files and reconstruct every relationship for each model request.
  Rejected because scientific lineage, impact closure, and replay need an
  explicit durable contract.
- Separate three logical planes with one-way, typed derivation boundaries.
  Selected.

## Decision

ClaimBranch has three logical graph planes:

1. **Canonical scientific plane** — accepted evidence events, branchable
   reasoning, human decisions, provenance, debt, manuscript anchors, and
   authorization-bound operations. This is the only scientific source of truth.
2. **Context/retrieval plane** — deterministic neighborhoods, full-text indexes,
   summaries, embeddings, communities, or other model/UI projections. It is
   disposable, versioned by its inputs and rules, and never accepted merely
   because a model or algorithm derived it.
3. **Execution-trace plane** — Proposal requests and responses, tool attempts,
   provider/model identity, timing, cancellation, payload availability, and
   retention metadata. It is append-only audit context, not scientific
   endorsement.

Only the trusted kernel command gateway writes accepted canonical operations.
The model boundary receives field-, sensitivity-, count-, and byte-scoped
context and can append only bounded non-authoritative Proposal/trace records
through a narrow ingress. Human export is a separate capability. Every
remote-capable egress passes an exact digest-bound review; a loopback endpoint
is “local-only” only when address, redirects, DNS, and external-network denial
are proven.

AI providers are replaceable. H1 may connect to an already-running
OpenAI-compatible endpoint and expose compatibility/timing education, but
ClaimBranch does not download, quantize, supervise, route, update, or choose a
default model. OpenClaw or MCP may later call least-privilege proposal/query
tools; neither becomes the kernel or gains human-only capabilities.

Typed neighborhood plus optional full-text search is the first retrieval
baseline. Embeddings, GraphRAG, graph-native storage, and a graph canvas require
the numeric triggers in the active ExecPlan.

## Consequences

- A single UI may project all three planes but must label authority and
  retention differences.
- Projection deletion or provider loss cannot make accepted state unreadable.
- Local inference is a valuable learning and privacy option, not a correctness
  dependency.
- The design has more explicit adapters and manifests, but fewer implicit trust
  paths.
- Graph technology is selected by measured semantics and workload, not by the
  word “graph.”

## Validation

The first slice must prove:

- deleting and rebuilding every context projection leaves the accepted manifest
  unchanged;
- model/provider processes cannot obtain a canonical store handle, human export,
  signing key, or human-only command;
- provider failure, cancellation, malformed output, and payload erasure leave
  accepted state unchanged and keep an auditable unavailable marker;
- exact egress preview invalidation blocks a changed request;
- AI-off and frozen-proposal histories replay without a live provider; and
- storage or retrieval expansion occurs only after its preregistered trigger.

## Supersession

None. This ADR elaborates ADRs 0001 and 0003.
