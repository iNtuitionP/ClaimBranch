---
kind: product-spec
status: draft
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: intended product behavior and boundaries
---

# ClaimBranch product specification

Version: 0.3
Basis: consolidated design draft

Implementation planning is split between the smallest
[validation prototype](releases/validation-prototype.md) and the broader
[candidate MVP release](releases/candidate-mvp.md).

## 1. Product definition

ClaimBranch is a local-first semantic version-control system that helps an
empirical researcher track how experimental results change interpretations,
claims, follow-up experiments, and manuscript text.

The product is built around one principle:

> **Evidence stays. Claims branch.**

It is not primarily a place to run experiments or write prose. It records the
reasoning transition between an experimental result and the paper that should
eventually express it.

## 2. Target user and initial setting

The first user is a solo empirical AI researcher who:

- keeps code, results, figures, and a LaTeX manuscript in a Git repository;
- receives results as JSON or similar local files;
- may use Overleaf through Git sync but compiles the manuscript locally;
- often explores several explanations and experiments in parallel;
- needs AI assistance without delegating scientific judgment to AI; and
- values fast, polished daily interaction more than broad feature coverage.

Multi-author collaboration, cloud hosting, and generalized laboratory
workflows are later concerns.

## 3. Problem statement

A paper begins with hypotheses and expected scenarios. Real results can match
some expectations and contradict others. The researcher then has to remember:

- which observations support, challenge, or qualify which claims;
- which alternative interpretations remain plausible;
- why each follow-up experiment was created;
- which existing experiments support only part of a revised claim;
- which sentences, sections, figures, and tables are now stale; and
- which changes were considered, adopted, deferred, or reverted.

These obligations accumulate as **manuscript debt**: a traceable mismatch
between the currently accepted research state and the state expressed by the
manuscript.

Git tracks textual history but not this scientific meaning. Experiment trackers
answer how a metric was produced, not how it changes the paper's argument.

## 4. Product promise

When a result differs from an expected scenario, a researcher should be able to
complete the following loop without losing provenance:

```text
Result
-> Mismatch
-> Reasoning branch
-> Competing interpretations
-> Revised or contested claims
-> Discriminating follow-up experiments
-> Manuscript impact
-> Human rationale
-> Selective merge
-> Verified manuscript update
```

For the [canonical saturation case](../validation/cases/saturation.md), this
loop should take no more than ten minutes once the scientific judgment and any
required experiments are complete.

## 5. Decision provenance

This specification distinguishes three levels of confidence:

- **User-confirmed constraint:** explicitly chosen in the design interview and
  treated as stable unless the user revises it.
- **Product hypothesis:** a recommended behavior that must be validated in the
  saturation workflow and usability testing.
- **Implementation hypothesis:** a reversible technical choice for an early
  contract spike, not a user requirement.

| Decision | Provenance |
|---|---|
| Global immutable evidence and branchable reasoning | User-confirmed constraint |
| `damage = delta-logit distortion × sensitivity` as conceptual factorization | User-confirmed constraint |
| Semantic partial merge | User-confirmed constraint |
| AI suggestions require human understanding and approval | User-confirmed constraint |
| Solo, local-first initial product with optional AI | User-confirmed constraint |
| Application-managed LaTeX comment markers are allowed | User-confirmed constraint |
| JSON drag-and-drop, then CLI, form, and reviewed chat | User-confirmed priority |
| Soft rationale for ordinary proposals and stronger review for central changes | User-confirmed direction |
| Exact Node, Edge, status, and debt taxonomy | Product hypothesis |
| Inbox-first information architecture | Product hypothesis |
| Separate domain commits and semantic refs | Implementation hypothesis |
| `.claimbranch/`, `config.toml`, and marker spelling | Implementation hypothesis |

### 5.1 Evidence and reasoning are separate

Decision level: **user-confirmed constraint**.

Completed runs, raw artifacts, and human-confirmed observations are global and
append-only. Branches contain interpretations of evidence, not alternative
versions of what happened.

Reasoning objects can branch: scenarios, interpretations, claims, narratives,
planned experiments, evidence relations, decisions, and manuscript patches.

### 5.2 ClaimBranch branches are semantic

Decision level: **implementation hypothesis**, derived from the confirmed
evidence/reasoning separation.

A ClaimBranch branch is a versioned research narrative stored in
`.claimbranch/refs`. It is not required to be a Git branch. Git remains the
transport and audit layer for repository files; ClaimBranch provides domain
commits, semantic diff, partial merge, and revert.

An accepted manuscript patch may optionally be materialized on a Git branch.

### 5.3 Merge belongs to the researcher

Decision level: **user-confirmed constraint**.

Lifecycle and maturity labels help the user judge state. They never become a
mandatory evidence gate that prevents a merge. A user may override an advisory
gate by recording a reason.

Partial merge is mandatory. A researcher may, for example:

- mark an old claim contested;
- merge new follow-up experiment plans;
- open manuscript debt;
- postpone the replacement central claim; and
- reject or defer all proposed prose.

### 5.4 AI is a proposal engine

Decision level: **user-confirmed constraint**.

AI can suggest observations, interpretations, relationships, conflicts,
follow-up experiments, affected manuscript locations, and patches. Every such
change enters an AI Proposal Inbox and must be confirmed or edited by a human.

AI cannot independently:

- alter raw results;
- confirm an observation;
- accept a claim or relationship;
- merge or revert a branch;
- modify the active manuscript;
- close manuscript debt; or
- assert that a researcher does or does not understand a decision.

### 5.5 Capture first, structure progressively

Decision level: **product hypothesis** motivated by the user's UX priority and
request for flexible granularity.

The quick path accepts an untyped note such as:

```text
Pruning did not follow the saturation prediction.
```

The user can structure it later, or review an AI proposal that splits it into
an Observation, Interpretation, and Follow-up Experiment. Rich internal types
must not become mandatory form-filling at capture time.

### 5.6 The inbox is home

Decision level: **product hypothesis** based on the user's preference for a
task/approval inbox and polished control-plane UX.

The full graph is an advanced view. The default screen is a combined Task,
Debt, and Approval Inbox showing decisions that need attention. Other screens
are projections of the same graph rather than independent sources of truth.

## 6. Core concepts

### 6.1 Evidence layer

The evidence layer records what occurred:

- ExperimentSpec version
- Run
- raw Artifact
- Metric
- Observation
- code reference
- environment reference

Accepted evidence is not edited in place. Corrections create a new object or
version with a `supersedes` relationship. Invalid runs remain recorded and are
marked invalid with a reason.

### 6.2 Reasoning and publication layer

This layer records how evidence is interpreted and used:

- Research Question
- Hypothesis
- Expected Scenario
- Interpretation
- Claim
- Narrative
- Decision
- Follow-up Experiment Plan
- Manuscript Anchor
- Patch Proposal
- Debt Bundle and independently resolvable Debt Item
- Literature Item and relation
- AI Proposal

The detailed contract is defined in the
[draft domain and versioning design](../designs/2026-08-03-domain-model.md).

## 7. Primary user journeys

### 7.1 Initialize an existing paper

1. Select an existing Git repository.
2. Confirm the root manuscript, initially `main.tex`.
3. Confirm the existing local compile command.
4. Create `.claimbranch/` without reorganizing the user's project.
5. Add or import the first Research Question and Claim.
6. Select manuscript text and link it to the Claim.
7. Enter the Inbox.

The target onboarding time is under five minutes for a compatible repository.

### 7.2 Import an experiment result

1. Drag a JSON file into the application.
2. Preview its structure and content hash.
3. Map fields to experiment identity, optional run parameters, metrics, and
   artifact paths.
4. Save the mapping as a reusable adapter template.
5. Review the proposed Experiment-level result, optional Runs, and Observations.
6. Confirm the observations; store the original file unchanged.

Input priority is JSON drag-and-drop, then CLI, structured web form, and
reviewed natural-language capture.

### 7.3 Respond to an unexpected result

1. Compare the expected and observed scenarios.
2. Confirm a match or mismatch; semantic comparison may be AI-proposed.
3. Review affected claims and evidence relationships.
4. Create a reasoning branch.
5. Record competing interpretations and discriminating experiments.
6. Review a derived manuscript-impact bundle.
7. Open a semantic merge request against `main`.
8. Select individual changes and record a merge rationale.

### 7.4 Synchronize the manuscript

1. Open a Debt Bundle caused by an accepted research change.
2. Review linked evidence, claim scope, and affected anchors side by side.
3. Request or write a bounded patch.
4. Accept, edit, reject, or defer the patch.
5. Apply an accepted patch deterministically.
6. Run the configured compile command.
7. Verify or explicitly waive the debt item.

## 8. Manuscript integration

ClaimBranch initially supports a single root LaTeX manuscript and local compile
command. The user's existing directory structure remains intact.

Anchors use a hybrid strategy:

1. existing LaTeX `\label{...}` for sections, figures, and tables;
2. automatically managed comment markers for paragraphs or sentences;
3. sidecar metadata containing content hash and surrounding context; and
4. AI-proposed relocation followed by human confirmation as a last resort.

Example marker:

```latex
% claimbranch:start id=anchor-central-claim
Saturation determines the damage induced by efficiency operators.
% claimbranch:end id=anchor-central-claim
```

Markers occupy their own comment lines, never affect the rendered PDF, and are
inserted by the application rather than typed by the user. The application must
run the configured compile check after insertion and must not silently relink a
missing or moved marker.

Overleaf API control is out of scope. Overleaf Git sync can continue to work as
normal.

## 9. Manuscript debt

Debt is derived from accepted graph changes, not merely entered as a TODO. A
Debt Bundle groups related effects so that one observation does not generate a
storm of independent alerts.

Initial debt reasons include:

- stale claim wording;
- missing result update;
- evidence-scope mismatch;
- numeric drift;
- unlinked evidence;
- unresolved contradiction;
- orphaned anchor;
- unapplied or unverified patch;
- related-work gap; and
- follow-up experiment without rationale.

Each item records the source change, affected objects and anchors, severity,
resolution condition, status, and history. Closing a debt requires `verified`,
`waived`, or `explicitly_deferred`; AI cannot choose that state.

## 10. Explain-back checkpoints

ClaimBranch preserves human ownership by requesting rationale at high-impact
transitions, not by placing quizzes on routine actions.

Soft checkpoints require a one-sentence rationale for ordinary AI proposals or
new follow-up plans.

Hard checkpoints apply to central-claim changes, narrative merges, central
manuscript patches, and waiving important debt. Prompts cover:

- what evidence changed the previous claim;
- which part of the new claim is supported;
- which alternatives remain;
- what experiment could discriminate between them;
- what would falsify the new claim; and
- where the manuscript must change.

The user can override a checkpoint, but the reason is recorded. Product copy
uses `Merge rationale`, `Decision note`, and `Human review pending`, never an
unsupported assertion that the user failed to understand.

## 11. Information architecture

### 11.1 Inbox

The home screen groups work such as:

```text
1 central claim challenged
3 manuscript locations may be stale
2 AI proposals await review
1 follow-up experiment lacks rationale
1 manuscript anchor needs relinking
```

### 11.2 Focused Graph

Shows the selected object and its one- or two-hop neighborhood. Full-graph mode
is optional and advanced.

### 11.3 Branches

Shows active claims, experiment plans, evidence relationships, manuscript
patches, and debt differences between semantic branches.

### 11.4 Claim Dashboard

Shows support, challenge, qualification, scientific maturity, human review,
and manuscript integration for each Claim.

### 11.5 Manuscript Impact

Projects research changes onto affected sentences, sections, tables, figures,
and captions.

### 11.6 Scenario Board

Places expected outcomes, observed outcomes, competing explanations, and
discriminating experiments together.

### 11.7 Context inspector

Evidence, proposal history, actions, and provenance appear beside the current
object. Chat is a contextual capture and query surface, not the source of truth.

## 12. Local-first behavior and performance

- Graph navigation, search, branch switching, and deterministic checks work
  without an AI provider or network connection.
- AI work runs asynchronously, is cancellable and retryable, and never blocks
  the core UI.
- Repository files are the durable source of truth.
- `.claimbranch-cache/index.sqlite` is a rebuildable index and is not committed.
- Raw evidence remains in the user's repository or an explicitly linked
  artifact store.
- Remote AI providers are opt-in per project. Before a request, the product
  shows which nodes or files will leave the machine, excludes configured secret
  paths, and records the provider, model, and input references with the
  resulting proposal. A local provider can implement the same interface.

Initial design targets for a paper project are 100 experiments, 5,000 runs,
2,000 observations, 200 claims, 1,000 anchors, 500 literature items, and 50,000
edges. These are stress-test targets, not measured promises.

Interaction targets are approximately 100 ms for ordinary navigation, 300 ms
for a focused graph, 150 ms to first search results, 500 ms for a basic branch
diff, and one second for a 10,000-row JSON import preview. They must be measured
and revised during implementation.

The candidate daily workspace uses a local daemon to watch configured result
paths, manuscript anchors, and Git state; execute compile and background tasks;
and report cancellable progress to the browser UI. This is a product and
architecture hypothesis to validate after the smallest workflow prototype.

## 13. Non-goals for the first release

- real-time coauthor collaboration;
- cloud SaaS and remote access;
- experiment execution or scheduling;
- checkpoint hosting or artifact synchronization;
- replacing DVC, W&B, or MLflow;
- direct Overleaf API control;
- autonomous or unapproved AI actions;
- automatic manuscript merge;
- generalized PDF RAG and related-work automation;
- simultaneous support for every manuscript format;
- mobile clients or a plugin marketplace; and
- a broad Research OS.

Related work begins with `.bib` import, Literature Items, claim relationships,
and related-work debt. Full-paper analysis comes after the kernel is stable.

## 14. Product success measures

### Scientific synchronization

- Every accepted central-claim change is compile-verified, waived, or explicitly
  deferred at a submission tag.
- The median time from a human-confirmed observation to resolved manuscript
  debt falls from the user's current baseline toward ten minutes, excluding the
  time needed to run new experiments.
- Every active Experiment Plan has a motivation relationship, rationale, and
  target claim or interpretation.
- Open debt count, central debt count, debt age, and verified resolution rate
  improve over a paper's lifecycle.

### UX guardrails

- time to import and confirm one result;
- alerts generated per result and the bundling ratio;
- AI proposals accepted, edited, rejected, or ignored;
- median proposal review time;
- manual anchor repair count; and
- instances where background AI work blocks the UI.

## 15. Open implementation questions

The product semantics above are fixed enough to implement. The following remain
engineering inputs rather than product ambiguities:

- representative anonymized JSON fixtures and mapping patterns;
- the user's exact LaTeX compile command and failure modes;
- implementation stack for the daemon, web application, and shared core;
- event and object serialization details after replay/profiling spikes;
- default AI provider interfaces and privacy disclosure; and
- measured ergonomics of markers and explain-back checkpoints.

Technology choices must preserve the domain invariants and the offline,
human-owned core rather than redefining them.
