---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-22
---

# ADR 0011: Make the paper argument graph the primary research workspace

Basis: the user reviewed the running graph on 2026-09-22, required a paper-level
reading path and visual impact review, and requested that these requirements be
recorded for continued implementation. Detailed interaction proposals are not
thereby visually approved.

## Context

The previous product direction made a linear Episode Review primary and the
graph optional. The implemented eight-node synthetic projection exposes the
limits of that choice: terse captions need outside explanation, experiments
precede the claim in the layout, and consequence review lives in separate text
sections. A single-claim fixture also cannot represent the user's intended
paper thesis, main claims and optional subclaims.

The [product contract](../../product/product-spec.md#7-interaction-and-visual-character)
owns the requirements. The [existing design](../../designs/2026-09-22-episode-review.md)
owns unresolved approaches and the [ExecPlan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns implementation gaps and sequencing.

## Decision drivers

- A researcher must understand an argument and the reach of a changed result
  from the graph, without reconstructing it from IDs or a second written log.
- Navigation starts at the paper's thesis and can reach the observations and
  experiments behind an individual claim.
- Visual scenarios must retain the distinction between observations,
  interpretation, proposed changes and hypothetical outcomes.
- Human authority, AI contribution history, safe manuscript changes and durable
  resumption remain necessary regardless of presentation.

## Options considered

- Keep the editorial sheet primary and improve only captions. Smaller change,
  but leaves the user-requested paper reading and impact workflow unserved.
- Make a general canvas or graph platform first. Offers arbitrary diagrams but
  adds ontology, layout and editing scope unrelated to the required research
  workflow; not selected.
- Make a bounded paper argument graph primary, with contextual detail and
  review controls. Selected; requires a reviewed model extension and revised
  validation, without selecting a graph database or frontend framework.

## Decision

Use the paper argument graph as the primary research workspace. Episode Review
is the contextual review of selected research within that workspace. Admit the
required paper hierarchy, readable nodes, relationship emphasis and visual
impact comparison during current product development; they do not wait for the
old post-V0 graph-canvas admission threshold.

Preserve ADR 0006's three planes and provider boundary. Layout, hover and
scenario calculation are projections, not accepted scientific operations.
Connectivity alone does not establish logical implication or causal certainty.
Keep actual observation, unrun plan and hypothetical result distinct, and
require existing human authorization for accepted changes.

The current F0 fixtures remain regression evidence. Extending the single-claim
model needs explicit relationship semantics, finite resource limits, schema
versioning, replay and migration rules before persistent implementation. This
decision does not declare an extended schema, usable product, live-value result,
or final interaction design complete.

## Consequences

Revise the product/release scopes, living design and execution plan in place.
Keep the earlier storyboard and optional graph labeled as prior implementation
evidence until replaced through their generators or application sources.
Preserve the manuscript saga, private workspace, proposal-only AI and separate
platform proof. The graph's primacy does not authorize automatic experiment
execution, arbitrary ingestion, general semantic merging or unbounded canvases.

## Validation

The [graph workspace oracles](../../validation/cases/saturation.md#102-paper-argument-workspace-oracles)
must exercise a thesis, multiple claims, an optional subclaim, shared evidence,
an unrun experiment and affected/unaffected paths. Check node comprehension,
reading order, keyboard/touch equivalents, scenario provenance and unchanged
accepted state. The separate source-delivery gate still requires installation,
durable restart, recovery and unfamiliar-user evidence.

## Supersession

Its graphical presentation assumptions are subsequently adapted by
[ADR 0012](0012-terminal-research-workspace.md); the paper argument and
scientific-authority decisions below remain in force.

Partially supersedes [ADR 0006](0006-three-graph-planes-and-provider-boundary.md):
its requirement that a graph canvas wait for numeric post-validation triggers
no longer applies to the bounded paper argument workspace required here. Its
three-plane separation, authority, provider, retrieval and storage constraints
remain accepted. No other ADR is superseded.
