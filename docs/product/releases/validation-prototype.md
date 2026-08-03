---
kind: release-scope
status: proposed
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: smallest product-validation release scope
---

# Validation prototype: one saturation reasoning loop

Scope: smallest product-validation slice before the candidate MVP release

## 1. Goal

Validate one narrow promise before building the full local research platform:

> A researcher can review an unexpected result, explore one competing
> reasoning branch, see the resulting manuscript debt, and selectively merge
> only the changes they understand and want.

The prototype uses the fixed
[saturation acceptance case](../../validation/cases/saturation.md).
It is intentionally not a generic experiment importer, complete domain VCS,
manuscript editor, daemon, or AI platform.

## 2. Product question

Does this workflow reduce lost reasoning and manuscript omissions enough to
justify its structure, without turning the researcher's work into graph
bookkeeping?

The prototype must answer that question with an interactive flow. A schema, graph
canvas, JSON viewer, or chat demo by itself is insufficient.

## 3. Fixed fixture, flexible real product

The fixture contains a Research Question, Hypothesis, expected Scenario,
original Claim, three confirmed Observations, candidate Interpretations,
follow-up Experiment Plans, and manuscript locations. These objects exist to
exercise the workflow; the prototype does **not** require a real user to enter every
type or adopt this granularity.

The eventual product must allow:

- a one-line Note before any structure;
- experiment-level or run-level evidence;
- anchors ranging from a sentence to a section, table, or figure; and
- progressive structuring only when it creates value.

## 4. Required end-to-end flow

### 4.1 Open the case

The application opens one local project containing the preloaded saturation
fixture and a `main` paper state. A researcher sees a concise Inbox item:

```text
Real-operator result needs review
2 expected outcomes differ; 1 matches
```

Required:

- state persists locally across restart;
- accepted Observations are clearly distinguished from reasoning proposals;
- no AI or network call is needed to open or navigate the case.

Not required:

- generic repository discovery;
- five-minute onboarding automation;
- arbitrary project creation; or
- user-authored RQ/Hypothesis/Scenario forms.

### 4.2 Review the mismatch

Show expected and observed results for pruning, quantization, and compression.
The user confirms the fixture's two mismatches and one match, then reviews
proposed relationships to the saturation-only Claim.

Required:

- rejecting a proposal does not alter accepted state;
- accepted evidence remains visible in every branch; and
- relationship scope and rationale are visible, not reduced to a colored line.

Not required:

- arbitrary JSON mapping;
- real result parsing;
- automatic Observation generation; or
- run-table visualization.

### 4.3 Explore one reasoning branch

The user opens `joint-distortion-sensitivity`, reviews fixture-provided
Interpretations and follow-up Experiment Plans, and may edit or remove them.

Required:

- the branch references global evidence instead of copying it;
- the joint factorization is labeled conceptual rather than a proven equation;
- prior evidence can be scoped to `sensitivity component only`; and
- the UI does not force the user to visit or complete every fixture object.

Not required:

- arbitrary branch creation;
- nested branches;
- a complete event-sourced implementation;
- revert; or
- generalized conflict resolution.

### 4.4 Review manuscript impact

One grouped Debt Bundle shows that the accepted challenge to the old Claim may
affect Abstract, Introduction, Results, Discussion, Conclusion, and related
figures or captions.

Required:

- the bundle traces back to the result and reviewed Claim relationships;
- individual locations can be accepted, rejected, or deferred as impacts;
- AI-proposed impact is visibly distinct from human-reviewed impact; and
- one result does not create an alert storm.

Not required:

- inserting markers into a real `.tex` file;
- producing or applying manuscript patches;
- running LaTeX; or
- closing verified manuscript debt.

The user explicitly made impact notification essential; automated prose and
patch application are later optional capabilities.

### 4.5 Perform one partial merge

The user reviews a semantic diff from the fixture branch to `main` and chooses:

```text
[x] Mark the saturation-only Claim contested
[x] Keep reviewed challenge/support relationships
[x] Keep selected follow-up Experiment Plans
[x] Open the grouped manuscript Debt Bundle
[ ] Adopt the joint-factorization Claim as central
[ ] Accept proposed manuscript prose
```

Required:

- `main` receives exactly the selected changes needed by this fixture;
- omitted changes remain on the source branch;
- the user records a short merge rationale;
- a dangling relationship cannot be created; and
- the resulting state is understandable as a semantic summary, without reading
  raw storage files.

Not required:

- a general lowest-common-ancestor merge algorithm;
- arbitrary property-level conflict handling;
- Git branch or commit materialization; or
- patch merge.

## 5. Minimal UI

Only four focused surfaces are required:

1. **Inbox item** with a clear next decision.
2. **Mismatch review** with evidence and relationship proposals.
3. **Branch workspace** with the local reasoning context and manuscript impact.
4. **Semantic merge review** with selectable changes and rationale.

A simple context inspector may support these surfaces. A full graph canvas,
chat home, command palette, dashboard suite, system tray, and background-task
control plane are post-prototype work. Visual clarity and responsiveness still
matter;
the smaller scope is intended to make polish achievable.

## 6. Minimal technical contract

The prototype needs only enough deterministic core behavior to prove:

- global accepted evidence cannot disappear when branch state changes;
- one reasoning branch can differ from `main`;
- first-class relationships retain scope and rationale;
- one fixed semantic diff can be computed;
- one selected merge can be applied without dangling references;
- one Debt Bundle can be traced to its accepted source change; and
- state can be saved and reopened locally.

The storage representation is deliberately replaceable. The prototype may use
a snapshot or simple operation log; it does not need to settle the complete
object/event/ref format or SQLite replay design.

AI behavior uses deterministic fixture proposals. A real provider is not part
of the prototype, but the review UI must preserve the proposal-versus-accepted
boundary.

## 7. Acceptance test

The prototype passes when a user unfamiliar with its internal storage can:

1. identify which outcomes matched or differed;
2. explain why the original Claim is contested rather than simply deleted;
3. inspect at least two competing interpretations;
4. see that existing evidence supports only part of the replacement Claim;
5. retain at least one motivated follow-up Experiment Plan;
6. find all fixture-provided manuscript impact groups;
7. merge the follow-up plan and debt while deferring the new central Claim; and
8. reopen the project and see the same accepted state.

The target is ten minutes once the scientific judgment is already made. The
test also records friction: confusing terms, unnecessary fields, alert count,
click count, and moments where the user reaches for external notes.

## 8. Explicitly outside this prototype

- arbitrary JSON ingestion and reusable mapping templates;
- mandatory Run creation or a generalized experiment/run hierarchy;
- automatic project onboarding;
- CLI parity;
- daemon, file watchers, background queue, or system tray;
- real LLM provider integrations;
- arbitrary branch/diff/merge/revert semantics;
- LaTeX marker insertion, patch application, and compile verification;
- related-work import;
- full graph, Claim Dashboard, or Scenario Board products;
- collaboration, cloud, mobile, or autonomous agents; and
- performance stress testing at the proposed design scale.

## 9. Next increments, if the prototype validates the workflow

### Increment A: durable kernel

Freeze versioned object/edge storage, branch refs, operation replay, semantic
diff/merge, revert, and a rebuildable index. Encode the fixture as golden tests.

### Increment B: real evidence intake

Add manual capture plus JSON drag-and-drop, preview, experiment-level or
run-level mapping, artifact hashes, idempotency, and result comparison.

### Increment C: manuscript adapter

Add real anchors, impact scanning, bounded patch review, deterministic apply,
local compile verification, and debt resolution.

### Increment D: daily local workspace

Add daemon and browser UI, repository watchers, command palette, background task
status, focused graph projections, and polished onboarding.

### Increment E: reviewed AI assistance

Add provider adapters, privacy controls, proposal audit history, semantic
conflict checks, follow-up suggestions, patches, and selectively tested
explain-back checkpoints.

Each increment is conditional on the prior workflow remaining faster and easier
than the researcher's existing memory-and-notes process.
