---
kind: product-spec
status: draft
owners: maintainers
last_reviewed: 2026-08-14
canonical_for: intended product behavior and boundaries
---

# ClaimBranch product specification

Version: 0.4

Basis: user-approved office-hours direction, accepted architecture decisions,
and the reviewed finite validation plan. ClaimBranch still has no usable
application or settled implementation stack.

Implementation and validation sequencing is owned by the
[validation prototype](releases/validation-prototype.md), the conditional
[candidate MVP](releases/candidate-mvp.md), and the
[active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md).

## 1. Product definition

ClaimBranch is a local-first personal research agent that preserves human
authorship while making AI available throughout empirical research.

Its product promise is:

> When an unexpected result challenges an important claim, ClaimBranch
> preserves the lineage from evidence through AI contribution and human
> judgment to manuscript consequence, and accepts only changes that the
> researcher knowingly authorizes.

Semantic version control is a mechanism for competing interpretations and
selective adoption. It is not the product identity. The product is the focused
decision workflow that helps a researcher understand what changed, decide what
they believe, keep AI influence legible, and bring the paper back into alignment.

The mnemonic remains:

> **Evidence stays. Claims branch. The researcher remains the author.**

## 2. Target user and support setting

The first product user and repository operator are one solo empirical AI
researcher-builder who:

- maintains a Git-tracked LaTeX paper on a native-Windows workstation;
- can clone a repository, run documented PowerShell commands, read a relative
  path, and make scientific judgments;
- records local result artifacts and may compile the manuscript locally;
- wants AI critique and drafting without delegating evidence acceptance,
  scientific decisions, or authorship;
- is willing to capture one important result-to-paper decision when the value is
  visible; and
- values a calm, fast daily workflow more than broad platform coverage.

They are not expected to manage a language runtime environment, inspect a
database, edit ClaimBranch internals, configure OS ACLs, debug provider JSON, or
understand graph traversal syntax.

An unfamiliar researcher with the same scientific context is the secondary H1
usability persona. The implementation maintainer is separate and may use
internal validation commands that never appear in normal product help.

The initial support hypothesis is one standard-user Windows 11 x64 machine, a
local NTFS Git repository, one LaTeX root and marked block, one supported
browser, and one pinned noninteractive compile workflow. Exact versions and
unsupported path/security combinations are frozen by platform spikes before
H0 is accepted. macOS, Linux, WSL, network/synced roots, ARM64, non-LaTeX
manuscripts, collaboration, and unattended authorization are not implied.

## 3. Problem

Unexpected results create obligations that ordinary tools split apart:

- which accepted observations support, challenge, or qualify a claim;
- which alternative interpretation remains plausible;
- why a follow-up experiment was planned;
- where existing evidence supports only one component of a compound claim;
- how an AI suggestion influenced the accepted reasoning;
- what the researcher actually authorized and why;
- which explanations the researcher deliberately deferred reviewing; and
- which manuscript sentence is now inconsistent with accepted research state.

Git tracks file history but not scientific meaning. Experiment trackers explain
how a metric was produced, not how it changed the paper. A chat transcript can
contain useful reasoning but is not a durable authority model. The result is
lost lineage, hidden AI contribution, understanding debt, and manuscript debt.

## 4. Product principles

### 4.1 Evidence is global and append-only; reasoning may branch

Completed runs, raw artifact references, and human-confirmed observations are
accepted evidence visible from every reasoning branch. Corrections,
invalidations, and retractions append events; they never rewrite or hide the
prior record.

Interpretations, Claims, selected scientific relationships, Decisions,
Experiment Plans, manuscript impact, and debt may differ between reasoning
branches. A selected merge adopts an explicit dependency-closed set of
reasoning changes; it never decides whether an Observation happened.

The accepted boundary is [ADR 0001](../architecture/decisions/0001-evidence-and-reasoning.md).
The finite first merge is deliberately smaller than the general behavior still
proposed in [ADR 0002](../architecture/decisions/0002-semantic-branches.md).

### 4.2 AI is always available as an assistant, never as accepted authority

AI may help capture, compare, critique, interpret, propose follow-up experiments,
find manuscript impact, draft bounded changes, and formulate teach-back
questions. Every AI result is a non-authoritative Proposal.

AI cannot:

- confirm, correct, invalidate, or retract evidence;
- accept a Claim, Interpretation, relationship, or Decision;
- create a human authorization receipt;
- merge reasoning into the accepted branch;
- apply a manuscript patch;
- mark compile verification;
- close understanding or manuscript debt; or
- assert that the researcher understands a decision.

Provider failure, cancellation, malformed output, deletion, or total absence
leaves accepted state unchanged and the manual path usable. These constraints
are accepted in [ADR 0003](../architecture/decisions/0003-ai-proposals.md).

### 4.3 Provenance and understanding are independent

An accepted AI-influenced operation retains an ordered Contribution chain:
proposal, human edits, human adoption, deterministic derivations, and later
corrections. Editing AI text does not erase its influence.

Review burden follows impact:

- low-impact non-authoritative capture remains quiet;
- medium-impact AI-influenced acceptance requires a concise human rationale;
- high-impact AI-influenced acceptance asks one to three contextual teach-back
  questions.

For high-impact work, the researcher may:

- answer and authorize;
- edit the proposal or rationale;
- choose **Not now**, which changes no accepted state; or
- choose **Authorize now; review explanation later**, which permits only the
  displayed operation and atomically opens visible UnderstandingDebt.

AI can help the researcher work through debt, but only a later foreground human
decision can close it. There are no comprehension scores, shame mechanics, or
AI grades. The accepted contract is
[ADR 0005](../architecture/decisions/0005-human-authority-provenance-and-understanding-debt.md).

### 4.4 Human authority is technical

Accepted mutations require an exact sealed review, an explicit foreground human
gesture, a short-lived single-use receipt, and unchanged expected research and
file state. A request field claiming to be human is not authority.

Model-facing processes receive scoped read/proposal capabilities, no signing
material, no portable receipt, no human export capability, and no writable
accepted-state handle. The researcher must see exactly which operation and
consequences are authorized.

### 4.5 The graph has three authority planes

ClaimBranch projects one experience from:

1. canonical accepted scientific state;
2. disposable context and retrieval derivations; and
3. append-only provider/tool execution traces.

Only the first is scientific source of truth. Similarity, extraction, community
summaries, model memory, and tool traces never become accepted science
implicitly. The architecture and expansion rules are in
[ADR 0006](../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md).

### 4.6 Manuscript progress is not one transaction

An accepted graph decision may open manuscript debt before any file is changed.
Patch preparation, application, compile verification, exact restoration, and
human debt closure are distinct, visible phases. ClaimBranch never reports
global success merely because the graph operation committed.

If it cannot prove current manuscript bytes, it stops accepted and manuscript
mutation and enters a recovery-only surface. It never guesses or overwrites a
divergent external edit. See
[ADR 0007](../architecture/decisions/0007-research-episode-and-manuscript-saga.md).

## 5. Closed first foundation

“Graph-first” means the logical contract for one finite wedge is complete before
the product UI is generalized. It does not mean a universal ontology, graph
database, full graph canvas, or complete semantic VCS is built first.

The F0 saturation episode contains:

- one ResearchEpisode;
- one result ArtifactRef and one manuscript ArtifactRef;
- one completed Run and three confirmed Observations;
- one central Claim;
- one competing Interpretation on one non-nested reasoning branch;
- a small closed set of typed scientific relationships;
- zero or one ExperimentPlan;
- one selected dependency-closed merge into main;
- one marked ManuscriptAnchor, one PatchIntent, one ManuscriptDebt;
- separate AI-off and frozen-proposal histories; and
- bounded Decisions, Contributions, reviews, receipts, attempts, traces, and
  resource sizes.

The [draft domain model](../designs/2026-08-03-domain-model.md) owns exact
records, edges, operations, cardinalities, state machines, and resource limits.
A valid live episode outside those bounds is recorded as out-of-F0 and counts
against the product; it does not silently expand the contract during V0.

## 6. Primary journeys

Planned commands below describe intended product behavior, not working
instructions in the current repository.

### 6.1 Discover and learn without risk

From a clean supported checkout with declared prerequisites, the researcher:

1. runs one standard-user repository bootstrap;
2. runs ClaimBranch doctor and sees core, manuscript, authorization, and
   optional-provider readiness separately; and
3. runs the disposable saturation demo with AI off and network denied.

Within five minutes, the demo shows three observations challenging one central
Claim and one marked manuscript consequence, verifies its audit manifest, and
states that no project or manuscript file changed. It requires no provider,
credential, browser, LaTeX installation, or graph knowledge.

### 6.2 Initialize one compatible paper

The researcher first previews project initialization. The dry run reports:

- resolved paper root and planned ClaimBranch paths;
- Git and dirty-worktree state;
- durable, secret, projection, temporary, and demo locations;
- root manuscript and marker status;
- exact compiler configuration/readiness;
- browser and authorization readiness;
- AI and network state; and
- what would change or how failure leaves the paper untouched.

The real operation initializes only after review. The researcher can generate a
human-readable episode template and add or verify the one F0 marker without
editing internal storage.

### 6.3 Record an unexpected result manually

The researcher:

1. starts one ResearchEpisode;
2. references the original result artifact and completed Run;
3. confirms exactly three Observations through append-only evidence events;
4. sees how they support, challenge, or qualify the central Claim;
5. opens one competing reasoning branch and records one Interpretation;
6. optionally records one discriminating ExperimentPlan;
7. reviews the exact impact closure and human rationale;
8. authorizes one selected merge; and
9. sees one manuscript debt for the marked block.

The AI-off path is complete. No empty “ask AI” state blocks the workflow.

### 6.4 Request optional AI help and learn serving

AI is an explicit action inside the current episode, not a mandatory onboarding
step or chat home.

Before any remote-capable request, ClaimBranch shows the destination, exact
normalized content, redactions, retention expectation, and request digest. The
researcher may send, edit, cancel, or continue manually.

H1 supports a deterministic stub plus one already-running OpenAI-compatible
endpoint. Add, probe, test, and explain actions teach:

- endpoint reachability and redirect behavior;
- local-only versus external-network-capable trust classification;
- model identity and context ceiling;
- structured-output compatibility;
- cancellation and visible failure;
- time to first token, token usage, and throughput when the endpoint exposes
  them; and
- that the returned Proposal remains **Not accepted**.

ClaimBranch does not install, download, quantize, start, stop, route, update, or
benchmark model servers. A local model is not automatically the default.

### 6.5 Review, authorize, defer, and resume

The command-launched Episode Review is one linear decision sheet:

1. situation and what changed;
2. AI suggestion labeled **Not accepted**, when present;
3. scientific before/after and evidence basis;
4. exact dependency closure and omitted items;
5. manuscript consequence and exact source diff when applicable;
6. human rationale and contextual teach-back or deferral;
7. action-specific authorization controls; and
8. collapsed audit details.

Persistent context states which branch/ref, evidence watermark, Claim, marked
block, and manuscript file an action would affect. There is no generic
“Accept.” Labels describe the actual effect, such as recording an
interpretation, merging selected reasoning, or applying a manuscript patch.

A small Review Pending list groups unaccepted proposals and accepted work with
open UnderstandingDebt. It shows consequence and age without scores or shame,
restores the exact episode context, and distinguishes understanding debt from
manuscript debt.

### 6.6 Apply and verify one manuscript consequence

The researcher reviews the exact marked block, expected source hash, proposed
replacement, compile configuration, and plain-language consequence before
authorizing patch preparation or application.

The UI and receipts distinguish:

- graph decision accepted;
- manuscript debt open;
- patch prepared;
- applying;
- applied but unverified;
- compiling;
- verified;
- restored after failure;
- recovery required; and
- human manuscript-debt closure.

Compile failure restores exact prior bytes when provable and leaves debt open.
Only a human closure bound to the exact verified source, output, compiler,
PatchIntent, debt, and graph head resolves manuscript debt.

### 6.7 Diagnose, recover, export, and migrate

Every handled failure states:

- a stable code and plain title;
- what changed and what did not;
- what work was preserved;
- one safe next command;
- a copyable diagnostic ID; and
- a version-matched help topic.

Read-only diagnosis, audit export, and recovery status remain available when
normal mutation is locked. The product never tells the researcher to edit its
database, journal, encrypted snapshot, or project metadata manually.

Before a schema upgrade, ClaimBranch checks compatibility and space, creates a
verified export, builds and verifies a new store, atomically selects it, and
retains the original. Nothing uploads automatically; a redacted diagnostic
bundle is previewed locally and sharing it is a separate human act.

## 7. Interaction and visual character

The first H1 surface is a quiet editorial laboratory notebook, not a command
console, chat application, graph dashboard, or control-room UI. Scientific
evidence, decision consequence, and manuscript diff receive the strongest
hierarchy. AI provenance and graph machinery stay visible but secondary.

Required interaction qualities:

- progressive disclosure follows orient me, show what matters, inspect evidence,
  confirm my judgment, reassure me what happened, return me to the paper;
- long operations expose phase, cancellation, late-result, stale, and resume
  behavior;
- success receipts say exactly what changed and what remains open;
- corrections append history rather than presenting destructive undo;
- every state is keyboard reachable and meaningful without color;
- focus is restored after async changes; errors associate with their control;
- status changes use appropriate live regions; and
- reflow, contrast, target size, reduced motion, and NVDA behavior are verified
  before V0.

Chat, a broad Inbox home, full graph canvas, dashboards, command palette, and
background daemon are post-V0 hypotheses.

## 8. Authority matrix

| Action | AI/model | Deterministic kernel | Foreground human |
|---|---|---|---|
| inspect scoped context | allowed through bounded query capability | allowed | allowed |
| export project/audit data | forbidden | prepares only | authorizes destination |
| create/revise/cancel Proposal | allowed through bounded ingress | validates and records as non-authoritative | allowed |
| confirm or correct evidence | propose wording only | validates append-only event | authorizes |
| record Interpretation/Decision | propose only | validates operation | authorizes |
| merge selected reasoning | forbidden | computes closure and consumes receipt | authorizes exact selection |
| answer teach-back | suggest question/context only | records answer/deferral | answers or defers |
| close UnderstandingDebt | forbidden | validates exact debt transition | authorizes |
| prepare/apply manuscript patch | propose patch only | runs fenced saga after receipt | authorizes exact patch |
| mark compile verified | forbidden | records pinned observed result | reviews result |
| close ManuscriptDebt | forbidden | validates exact closure receipt | authorizes |
| rebuild disposable projection | no authority effect | allowed | may request |

## 9. Local-first, privacy, and availability

- Accepted state, refs, review history, deterministic impact, replay, export,
  and manuscript recovery work without AI or network access.
- Provider work is asynchronous, cancellable, bounded, and never blocks manual
  work.
- Human export is separate from model-readable context.
- Raw artifacts remain at their linked source unless the researcher explicitly
  imports them; model context excludes raw bytes and secrets by default.
- Remote-capable requests require exact one-shot review and record provider,
  model, normalized input digest, redaction manifest, timing, disposition, and
  payload availability.
- Hard erasure applies only to eligible raw provider payloads. The immutable
  trace retains a payload-unavailable marker and digest.
- Operational logs and measurements are local, bounded, redacted, previewable,
  and never transmitted automatically.

## 10. Product gates and success

### Foundation H0

- canonical docs agree on the promise and finite F0 contract;
- AI-off and frozen-proposal histories each replay to their own byte-identical
  full-audit golden;
- unauthorized mutation, read/export bypass, and provider egress fail closed;
- exact manuscript restoration or the sole recovery hard stop is proven;
- clean supported checkout reaches the offline demo within five minutes; and
- migration and restore drills retain authority and the original store.

### Minimum experience H1

- one real-paper initialization and manual episode complete without internal
  edits;
- Episode Review makes accepted versus proposed, impact, target, manuscript
  phase, and debt legible;
- forged, stale, replayed, cross-project, and model-originated authorization
  fail;
- deterministic stub and already-running local endpoint exercises change no
  accepted state; and
- an unfamiliar researcher completes the gated journey without coaching.

### Live-paper V0

The first three consecutive qualifying result-to-decision episodes within eight
weeks are compared with a frozen Markdown/checklist baseline. The protocol
records trace completeness, active and wait time, human rationale/edits,
accepted AI contribution, debt, false alarms, manuscript outcome, and any
attested material omission surfaced before the final decision.

V0 may show directional utility and workflow noninferiority; it does not prove
causal prevention. The
[validation prototype](releases/validation-prototype.md) owns the exact outcome
rule. Only VALIDATED opens candidate product expansion.

## 11. Explicit non-goals before validated V0

- autonomous research decisions or accepted model writes;
- a general semantic VCS, arbitrary/nested merges, or automatic conflict solver;
- universal scientific ontology, graph canvas, graph database, embeddings, or
  GraphRAG without measured need;
- full paper/repository rewriting or multi-file atomic manuscript editing;
- experiment scheduling, artifact hosting, checkpoint management, or direct
  Overleaf control;
- related-work/PDF automation;
- public installer, automatic update, daemon, hosted telemetry, SaaS, mobile,
  collaboration, or multi-tenant permissions;
- OpenClaw clone, channel runtime, MCP integration, plugin marketplace, or
  provider marketplace;
- model download, quantization, supervision, routing, fallback, rental, or broad
  serving benchmarks; and
- a v1.0 claim based only on retrospective fixtures.

## 12. Open implementation questions

The following are engineering hypotheses with explicit spikes, not unresolved
product authority:

- package/runtime and public CLI implementation;
- canonical store after SQLite replay, crash, concurrency, and migration tests;
- native-Windows process isolation and user-presence primitive;
- browser versus native/CLI authorization helper;
- exact supported Windows, PowerShell, Git, browser, filesystem, and LaTeX
  versions;
- marker behavior and compiler isolation on the real paper;
- physical serialization, canonical JSON, key storage, and signed export shape;
- provider envelope details and retention settings; and
- measured UI, graph traversal, recovery, and onboarding budgets.

Technology choices must preserve the accepted human-owned, AI-optional,
three-plane contract rather than redefine it.
