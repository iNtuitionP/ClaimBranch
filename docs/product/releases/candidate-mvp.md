---
kind: release-scope
status: proposed
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: candidate first-release scope
---

# Candidate MVP release scope

Basis: product hypothesis carried forward from the design conversation

This document preserves the complete first-release scope proposed at the end of
the ClaimBranch design conversation. The user did not approve each technical
item independently, so this is a candidate release contract, not a locked set of
requirements.

Implementation starts with the smaller
[validation prototype](validation-prototype.md). Capabilities below enter the
MVP only if prior increments preserve the user's top constraint: a fast,
comfortable workflow that does not replace research with bookkeeping.

## 1. Release outcome

The candidate MVP completes the full experiment-to-manuscript loop on the
[saturation acceptance case](../../validation/cases/saturation.md):

```text
Real result import
-> expected/observed mismatch
-> reasoning branch
-> scoped evidence relationships
-> follow-up experiment plans
-> manuscript impact
-> semantic partial merge
-> reviewed patch
-> local compile
-> verified or explicitly deferred debt
```

The product remains usable without an AI provider. AI enriches the loop through
reviewed proposals rather than controlling it.

## 2. Candidate capabilities

### 2.1 Local repository

- Connect an existing Git repository and initialize durable ClaimBranch state.
- Support one `main.tex`, separate figures, and a user-supplied local compile
  command.
- Store accepted state in a human-readable, portable form.
- Maintain a disposable local search and graph projection.
- Expose Git status and connect relevant domain decisions to Git history.

The exact `.claimbranch` object/event/ref format is a provisional implementation
choice, not part of the product contract.

### 2.2 Flexible evidence intake

- Capture an aggregate result at Experiment level or optional Run-level detail.
- Import JSON through drag-and-drop.
- Preview and map fields to identity, parameters, metrics, and artifacts.
- Save a mapping template for subsequent files of the same shape.
- Preserve the original content hash and source reference.
- Present normalized results in a comparable table.
- Require human confirmation before a proposed Observation becomes accepted
  evidence.

The user is never required to decompose an aggregate result into Runs.

The candidate release also exposes a focused CLI over the same kernel:

```text
claimbranch init
claimbranch ingest results.json
claimbranch status
claimbranch branch create joint-distortion-sensitivity
claimbranch diff
claimbranch merge
```

The CLI does not need parity with every visual review surface, but it MUST read
and update the same accepted state rather than creating a second workflow.

### 2.3 Research graph

- Create Nodes progressively, beginning with an untyped Note if desired.
- Represent Claims, Interpretations, Scenarios, Experiment Plans, Observations,
  manuscript locations, and other types from the draft domain model.
- Create first-class relationships with scope, conditions, strength, rationale,
  review state, and provenance.
- Preserve global accepted evidence while reasoning state branches.
- Show a focused one- or two-hop context rather than requiring full-graph use.

### 2.4 Semantic version control

- Record auditable domain changes.
- Create and switch reasoning branches.
- Show semantic diff for Claims, relationships, narratives, Experiment Plans,
  manuscript impact, decisions, and debt.
- Perform partial merge with referential-integrity closure and reviewable
  semantic dependency warnings.
- Revert reasoning changes by appending history rather than erasing it.
- Optionally materialize an accepted manuscript patch on a Git branch.

The precise commit/ref/LCA algorithm remains an implementation hypothesis until
the validation prototype demonstrates that semantic branching is useful.

### 2.5 Manuscript integration

- Link a Claim to a section, paragraph, sentence, table, figure, or caption.
- Prefer an existing LaTeX label and support application-managed comment
  markers when finer anchors are needed.
- Keep a sidecar fingerprint and require human review for uncertain relocation.
- Detect affected or stale locations and group them into Debt Bundles.
- Review a bounded patch with evidence and old/new text side by side.
- Apply only an explicitly accepted exact patch.
- Run the configured local compile command and preserve failures for review.
- Allow a human to mark debt verified, waived, or explicitly deferred.

Impact notification is the mandatory product value. Patch generation and Git
branch materialization remain optional user actions even when supported.

### 2.6 Daily local workspace

- Start at a Task, Debt, and Approval Inbox.
- Provide focused Graph, Branch, Claim, Manuscript Impact, and Scenario
  projections over the same data.
- Provide a context inspector for evidence, proposals, history, and actions.
- Provide command-palette access to common operations.
- Show Git, import, compile, and AI background progress without blocking the UI.
- Run as a local server with a browser UI; a desktop wrapper is later work.

Inbox-first navigation and exact screen structure are product hypotheses to
validate, not immutable user requirements.

### 2.7 Reviewed AI assistance

- Propose mismatch classifications, Observation wording, Interpretations,
  relationships, follow-up experiments, manuscript impact, semantic conflicts,
  related-work relationships, and bounded patches.
- Put every structured change in a Proposal Inbox.
- Preserve provider, model, referenced inputs, output, human edits, and final
  disposition for every proposal.
- Support local and explicitly opted-in remote providers through one boundary.
- Keep deterministic checks separate from semantic AI suggestions.
- Request a short rationale for ordinary accepted proposals and a tested
  explain-back flow for high-impact central changes.

AI cannot confirm evidence, accept relationships, merge branches, apply patches,
or resolve debt.

### 2.8 Initial related-work boundary

- Import `.bib` metadata as Literature Items.
- Relate literature to a current Claim with citation intent.
- Create related-work debt.

Full PDF analysis, generalized RAG, and automatic literature review remain out
of scope.

## 3. Progressive delivery gates

The candidate MVP is delivered as increments, not a single breadth-first build.

### Gate 0: workflow validation

Complete the fixed-fixture [validation prototype](validation-prototype.md).

Exit: the user can review mismatch, branch reasoning, inspect manuscript impact,
and partially merge in ten minutes without excessive structure.

### Gate 1: durable kernel

Freeze versioned object and relationship contracts, local persistence, general
semantic branch/diff/merge/revert behavior, the focused CLI surface, and cache
rebuild tests.

Exit: the canonical state and golden semantic diff replay deterministically.

### Gate 2: real evidence and manuscript

Add flexible JSON intake, Experiment/optional-Run granularity, real anchors,
Debt Bundles, patch review, exact application, and compile verification.

Exit: the full canonical case operates on fixture files rather than preloaded
application state.

### Gate 3: polished daily workspace

Add local daemon/browser UI, Inbox, focused projections, command palette,
watchers, and non-blocking task progress.

Exit: the workflow requires no hand-editing of ClaimBranch storage and remains
responsive during imports and compile tasks.

### Gate 4: AI and comprehension study

Add provider adapters, audited proposals, privacy controls, semantic checks, and
explain-back experiments.

Exit: disabling AI leaves the complete deterministic loop usable, and user
testing shows that proposal review adds value without unacceptable fatigue.

## 4. MVP acceptance criteria

The candidate release passes when:

1. accepted evidence cannot be hidden or removed by branch operations;
2. Experiment-level results work without mandatory Run decomposition;
3. free capture can be structured progressively;
4. evidence relationships retain their scientific scope and rationale;
5. a user can partially merge follow-up plans and debt while deferring a new
   central Claim and manuscript prose;
6. affected manuscript locations are not silently missed in the canonical case;
7. accepted patches require exact anchors and compile successfully before debt
   verification;
8. every AI change is reviewed and every proposal disposition is auditable;
9. the core workflow works offline with AI disabled; and
10. the CLI and browser UI observe the same repository state; and
11. the full case can be triaged and synchronized in roughly ten minutes once
    required scientific judgment and experiments are complete.

## 5. Explicit non-goals

- real-time coauthor collaboration;
- cloud SaaS or mobile clients;
- an experiment scheduler;
- checkpoint hosting or artifact synchronization;
- replacing DVC, W&B, or MLflow;
- direct Overleaf API control;
- autonomous or unapproved research agents;
- automatic manuscript merge;
- generalized related-work PDF analysis;
- simultaneous support for every manuscript format;
- a plugin marketplace; and
- a broad Research OS.

## 6. Scope-control rule

No capability advances to the next gate merely because it appears in this
candidate list. It advances when it helps the saturation workflow and preserves
or improves capture time, alert load, proposal review time, and the researcher's
ability to explain the accepted scientific state.
