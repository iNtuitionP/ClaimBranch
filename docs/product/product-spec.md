---
kind: product-spec
status: draft
owners: maintainers
last_reviewed: 2026-10-11
canonical_for: intended product behavior and boundaries
---

# ClaimBranch product specification

Version: 0.7

Basis: user-approved office-hours direction, accepted architecture decisions,
the finite validation plan, and the 2026-09-22 paper-graph and usable-delivery
requirements. A synthetic application exists; the intended product below is
not yet available. See the [implementation status](../../README.md).

Implementation and validation sequencing is owned by the
[validation prototype](releases/validation-prototype.md), the conditional
[candidate MVP](releases/candidate-mvp.md), and the
[active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md).

The user selected the key-free personal terminal alpha on 2026-10-07 under
[ADR 0017](../architecture/decisions/0017-personal-terminal-alpha.md).
The [current alpha scope](releases/validation-prototype.md#55-source-delivery-readiness)
retains human construction, append-only evidence history and durable return
using ordinary private local files and explicit terminal confirmation. This is
the completed implementation baseline; show its manual loop for local feedback.
The protected authority, provider, manuscript and H0/H1/V0 contracts below
remain later targets, not alpha completion gates. Alpha history cannot confer
protected accepted authority. Public personal init/open now retains human-authored
notes, partial judgments and unfinished writing using the existing terminal.
Explicit personal result confirmation, append-only correction, selected manual
reasoning and a later research question reuse that workspace and original reason;
see the [working entry and its limits](../development/workflow.md#personal-project-writing-in-the-terminal).
Public saved-work status, create-only local backup/export and fresh-destination
restore now preserve that saved workspace. The
[personal source artifact](../development/workflow.md#personal-terminal-alpha-source)
now runs this manual loop from independent extraction on the available Mac.
It is experimental alpha behavior, not protected product or live-value validation.

The user selected an optional personal-AI continuation on 2026-10-09 under
[ADR 0018](../architecture/decisions/0018-optional-personal-ai.md).
On 2026-10-10 they required working optional AI before GitHub publication.
On 2026-10-11 they explicitly directed publication of the current source now;
the manual alpha may be published with live AI honestly unavailable. The
[release milestone](releases/validation-prototype.md#ai-connected-github-publication-milestone)
owns the later AI-connected delivery criterion, not a prerequisite for this
newly authorized current-source preview.
It retains ordinary private files, manual work and explicit human recording,
while requiring selective proposal comparison, complete item/judgment origin,
independent explanation choice and durable return before live enablement.
Partial explanation stays editable on its original cause after review expiry or
changed current science. Return opens the latest partial writing, separately
from the immutable recorded review choice; it cannot overwrite newer text with
an older recorded explanation or restore recording authority.
Actual provider and exact outbound consent remain separate gates. The current
public personal app is still AI-off. The portable typed-input/response subset is
available as an [offline contributor exercise](../development/workflow.md#typed-proposal-ingress-exercise),
without staging or a live request. The separate
[offline selective-staging and origin-return backend](../development/workflow.md#selective-proposal-staging-and-origin-return)
now carries chosen/required item origins through human edits, explicit personal
recording, correction, restart and backup/restore. Personal explanation choice
and partial causal writing remain separate from AI origin. The separate [offline terminal rehearsal](../development/workflow.md#selective-ai-items-in-the-terminal)
now connects these APIs to contextual item selection/editing, graph comparison,
explicit personal explanation choice and saved-origin return on an invented
cache study. [Personal LLM connection preparation](../development/workflow.md#personal-llm-configuration-and-unsent-preview)
now lets each user configure an API format, endpoint, model and credential
reference and inspect the complete unsent request on their own saved science.
It reads no credential, creates no consent or proposal attempt and does not
qualify a provider. Actual provider integration remains unavailable; public
personal projects remain AI-off.
The [internal asynchronous transport](../development/workflow.md#internal-asynchronous-transport)
now exercises bounded requests, cancellation and untrusted typed returns with
owned test peers. It adds no public live switch, recording or provider verdict;
its [checked API retention controller](../development/workflow.md#checked-api-proposal-retention)
now carries owned returns through selective edits, personal recording and
save/restart/backup. No live capability restores. Public init/open can explicitly
select a private profile for exact contextual unsent previews. The existing
terminal now connects owned asynchronous returns, selective editing and return;
its live qualification gate refuses before key lookup or I/O. Manual work remains
available and no configuration/consent is restored with research. Actual provider
qualification, live enablement and useful human assistance remain the missing outcome.
An explicit Codex ChatGPT-login profile now prepares selected application input
in that same graph context, with no API key or copied login cache. This preview
distinguishes application input from unverified CLI-generated HTTP content and
destinations; it creates no request, consent or trace. A separate
[internal app-server adapter](../development/workflow.md#internal-codex-app-server-adapter)
now checks bounded owned replies through the existing typed contract. Its separate
[checked Codex origin controller](../development/workflow.md#checked-codex-proposal-retention)
connects owned returns to selective editing, personal recording and save/restart/
backup with complete origin and independent explanation choice. Actual
authenticated access/egress and useful live assistance remain unavailable;
these internal components do not qualify a provider or enable public AI.

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

The intended human outcome is a researcher who can use substantial AI
assistance while remaining able to explain and own their scientific judgment:

- distinguish what was observed, what is an interpretation, and what remains
  uncertain;
- reconstruct why evidence changed the scope of a claim and their own reason
  for choosing an interpretation;
- inspect, question, edit or reject AI contributions without losing where
  those contributions entered the argument;
- return to unfinished research with the decision context and remaining
  obligations intact; and
- bring the manuscript into alignment with that judgment through their existing
  tools, without maintaining a second narrative for the system.

Plan backward from these outcomes. Every near-term capability must name the
researcher action it improves and how that action will be observed. Graphs,
receipts, retained history and model connectivity are mechanisms serving those
outcomes. Technical safety remains necessary, while a successful check alone
does not demonstrate better research or human understanding. The finite first
release tests this larger ambition in one complete research loop; it does not
replace the ambition with the size of today's fixture or implementation.

For an eligible result-to-paper episode, ClaimBranch is the intended primary
workspace for forming and recording the judgment, not a mandatory second pass
after deciding elsewhere. The researcher must not first complete a separate
decision log to use it. This does not expand the finite episode scope into a
replacement for experiment execution, general note-taking, or the LaTeX editor.

Starting an episode requires source context, not an already-completed
interpretation. As the researcher judges, review reuses the entered context
and rationale rather than requiring a second retrospective form. Changed
meaning, evidence, or scope still requires the applicable new review and
authorization; reuse never carries old consent forward. Necessary audit
history remains inspectable without requiring the researcher to author it as
another narrative. The contributor Notion journal is not part of this workflow.

The mnemonic remains:

> **Evidence stays. Claims branch. The researcher remains the author.**

## 2. Target user and support setting

The first product user and repository operator are one solo empirical AI
researcher-builder who:

- maintains a Git-tracked LaTeX paper on the supported local workstation;
- can clone a repository, run documented commands, read a relative
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

Delivery must reach other researchers through GitHub: a declared supported
checkout or release must let an unfamiliar researcher set up the app, create
their own compatible project, preserve judgments and evidence, quit and resume,
and recover from a failed operation without editing application internals. A
source-based release is acceptable; a public installer is not implied. A demo
limited to bundled synthetic data does not meet this product-delivery target.
The [source-delivery gate](releases/validation-prototype.md#55-source-delivery-readiness)
owns the required release evidence. Publishing to GitHub is a separate action
from implementing and validating this target.

The completed source baseline supplies the complete manual own-project
workflow: human graph/research authoring, explicit personal recording, private
save, restart and local backup/recovery, without application encryption or
hardware keys. The release scope defines this boundary under
[ADR 0017](../architecture/decisions/0017-personal-terminal-alpha.md).
The owner now authorizes publishing that current manual baseline for feedback.
The [AI-connected publication milestone](releases/validation-prototype.md#ai-connected-github-publication-milestone)
still requires its actual live checks before a release advertises working AI.
Automatic manuscript changes and protected replacement-device continuation
remain later capabilities. This preserves the intended human outcome without
calling a synthetic preview a usable research app.

For the personal alpha, use the available Mac and the portable terminal path;
declare Linux support only after its applicable checks run. No graphical login
or native Mac approval is part of its daily flow. The following platform scope
belongs to the deferred protected product.

The first protected implementation target is the available Apple Silicon macOS machine;
Windows 11 x64 is the deferred second target under
[ADR 0010](../architecture/decisions/0010-macos-first-platform-adapters.md).
Each target uses a standard user, a local Git repository, one LaTeX root and
marked block, one supported review surface, and one pinned noninteractive
compile workflow. Exact OS/filesystem/runtime versions and authority, path and
recovery guarantees are proven on that target before H0 is accepted. Mac
evidence does not establish Windows support. Linux, WSL, network/synced roots,
other architectures, non-LaTeX manuscripts, collaboration and unattended
authorization remain outside this support hypothesis.

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

The finite wedge validates scientific and authority rules. The paper argument
graph is also the primary user workspace under
[ADR 0011](../architecture/decisions/0011-paper-argument-graph-workspace.md).
Neither requirement selects a universal ontology, graph database, unrestricted
canvas or complete semantic VCS.

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

F0 remains the single-claim regression baseline, not the complete paper-level
representation. The required thesis/main-claim/subclaim and shared-evidence
extension must receive explicit semantics, bounds and versioned fixtures in the
domain design before persistence or a revised prospective protocol uses it.
Do not present a renamed C-01 or a synthetic root node as completed paper-level
support. User-approved graph requirements are admitted now; their implementation
does not establish that the extended foundation or live-use gates have passed.

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

The following sequence is the original F0 regression journey. Its exact three
observations and single claim are not a universal research-capture template;
the paper workspace uses the separately versioned argument model. Its live
episode bounds and prospective protocol must be frozen before real evaluation,
as required by section 5 and the release scope.

In the original F0 journey, the researcher:

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

Paper context preserves the selected claim scope, measurement definition/unit/
baseline, experimental conditions and explicit scientific relationship rationale.
A structural parent is not evidence of support. Source references do not imply
that an artifact was opened or its fidelity verified. Selected observations and
plans retain their current status, including retraction and not-yet-run status.
Including the current draft is an explicit choice, available before a complete
judgment exists; missing rationale stays missing and AI influence stays visible.
Changing that draft or paper state invalidates its prior request review.

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

Inference, any tool execution, and accepted writing are separate responsibilities
under [ADR 0009](../architecture/decisions/0009-external-inference-and-local-authority.md).
API compatibility is not a protection verdict. A live provider becomes usable
for the protected workflow only after its deployment satisfies the authority
and privacy gates; an unrestricted same-user server is not made safe by
isolating its connector or acknowledging a warning. Unknown or unsupported
protection leaves manual work available and accepted state unchanged. There is
no new model-server manager, general tool executor, or second journal form.

### 6.5 Review, authorize, defer, and resume

The command-launched workspace starts with the paper argument graph described
in section 7. Episode Review keeps the selected claim, evidence and proposed
consequence in that graph context. It provides:

1. the paper thesis, relevant argument and changed evidence;
2. contextual AI suggestions labeled **Not accepted**, when present;
3. visual scientific before/after, dependency closure and omitted changes;
4. affected and unchanged paths, with reasons available at their nodes/links;
5. manuscript consequence and exact source diff when applicable;
6. the researcher's reused rationale and contextual teach-back or deferral;
7. action-specific authorization controls; and
8. inspectable contribution and audit details.

This is an information and authority contract, not a required vertical sequence
of text sections. Node-local or contextual editing must preserve a complete
human rationale without requiring a second narrative outside the graph.

Scientific change review distinguishes explicit selections, required amended
dependencies, retained references and omitted amendments. Before/after impact
uses explicit scientific relations, including the old path when an edge moves;
structural containment alone cannot imply a scientific consequence. The review
retains source and new-draft contributions, and manual edits cannot erase
inherited AI influence. A changed draft, paper state or selection invalidates
its previous review. Inspecting effects precedes any explanation disposition or
authorization; an unaccepted preview or deferral creates no accepted record or
debt. Missing manuscript source remains unresolved rather than becoming a diff.

Persistent context states which branch/ref, evidence watermark, Claim, marked
block, and manuscript file an action would affect. There is no generic
“Accept.” Labels describe the actual effect, such as recording an
interpretation, merging selected reasoning, or applying a manuscript patch.

A small Review Pending list groups unaccepted proposals and accepted work with
open UnderstandingDebt. It shows consequence and age without scores or shame,
restores the exact episode context, and distinguishes understanding debt from
manuscript debt.

A later result opens a new episode in the same paper, preserving the current
argument, global evidence and prior judgments. Its draft and selected effects
remain distinct from earlier episodes. A researcher can inspect an earlier
interpretation against current corrected evidence or deliberately return to its
historical state. Closing that episode must not imply that its manuscript or
understanding obligations have been resolved.

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

The paper argument graph is the primary research and review surface. A
researcher should be able to read what the paper argues, inspect its basis,
and explore what an experiment could change from this surface. Detailed prose,
AI assistance and manuscript comparison stay attached to the selected argument.

The user selected an actual-terminal workflow on 2026-09-23 to remain in the
server environment where experiments run. The primary daily workspace must
therefore operate through the terminal, including SSH, without requiring a
browser, graphical login or forwarded web port. A TUI provides persistent
reading/review context; command output supports noninteractive inspection.
[ADR 0012](../architecture/decisions/0012-terminal-research-workspace.md)
records this presentation decision and its separate server-authority limits.

The user established the argument outcomes on 2026-09-22; the later terminal
selection adapts their presentation while preserving scientific meaning:

| ID | Required experience |
|---|---|
| PG-1 | Each node communicates its scientific content without relying on an ID or vague caption. Name the relevant operations, terms, conditions, comparisons and measurement definitions; show missing source information honestly. Details may expand, but the visible node must make its subject understandable. |
| PG-2 | Navigate from paper thesis to main claims, optional subclaims, observations/evidence and experiment records or follow-up experiments, retaining the argument path and return context. A claim may lead directly to evidence. Reading or pane order does not reverse scientific edge meaning. |
| PG-3 | Represent the paper's argument from its thesis, beyond the current single-claim episode. Keep distinct claims and their basis identifiable, including evidence shared by several claims. The graph should support understanding the paper, not only inspecting internal records. |
| PG-4 | Focusing a node reveals its typed connections and related content, with keyboard access to those nodes and a return path. Emphasis must preserve readable scientific content and orientation. A graphical view may additionally provide hover/touch behavior. |
| PG-5 | Show the possible reach of a follow-up experiment and the affected/outside-path parts of a judgment alongside the argument structure. Marks and relationship paths must remain inspectable without relying only on a separate prose report, and must not imply that reach determines scientific truth. |

Scientific support, challenge and qualification remain distinct from structural
references. Actual observations, interpretations, unrun plans, hypothetical
results, unaccepted AI suggestions and selected/omitted changes must remain
visibly distinguishable. Merely highlighting a path cannot certify that a
claim is true or false. A scenario neither creates evidence nor changes accepted
state; consequential scientific and manuscript changes still require review
and human authorization.

Researchers must be able to construct the paper argument themselves with AI
disabled: define the thesis during project setup, add main/subclaims,
interpretations and planned experiments, and connect valid endpoints with typed
scientific relations and a rationale. This is a primary authoring workflow,
beyond editing existing example nodes or importing hand-written JSON. Creating
a draft does not require authorization on every keystroke. Accepting its
scientific changes still uses exact review and human authorization. Observations
and completed experiment records enter through explicit source/record/confirmation
paths; drawing a node or edge cannot manufacture confirmed evidence.

Draft construction must work before a judgment/reason is complete. Its graph
shows valid kept candidates independently of final review selection or expiry;
unkept/invalid input remains editable and cannot masquerade as validated science.
Creation names an owning work, and navigation provides an explicit return to it.
Kept candidate edits, removal and selection changes revoke dependent reviews.
Removing a draft and omitting it from review are distinct, with dependent drafts
identified before removal. Following a new draft node cannot silently create
another judgment or migrate an existing one. Exact review still requires a
complete judgment and current source binding.

Manual interpretation authoring starts with blank text and explicit links to
recorded observations, whose status remains visible. An empty basis remains
unlinked; it does not imply verified evidence. The finite episode/ref limit is
explained before creating another interpretation, with routes to existing
scientific or draft editing. A kept new interpretation can explicitly supply the
owning judgment text after comparison, retaining its reason and AI contributions.
Changed source/work or unresolved candidate edits block reuse without losing
writing. Reuse does not accept science or restore review authority. Existing
recorded interpretation text cannot be relabeled manual by this shortcut.

Unconfirmed result capture may start from an existing recorded subject before
an interpretation is complete. Keep run/source references, observed text,
conditions, measurements and optional tentative judgment/reason together as
provisional writing. Missing fields remain missing. Retain original context and
its contribution history separately from the new writing; references never
imply artifact access or confirmation. Kept fields and unfinished edits remain
distinct. Source changes or unavailability preserve the original basis and text
without silently rebinding. Independent results and episodes do not share drafts.
An unconfirmed result must not enter graph evidence, AI requests or scientific
review through this capture surface. Its judgment stays available with the
result for the later legitimate confirmation integration, rather than replacing
an existing source-node judgment. Session-only prototypes disclose loss on quit
and exclude this work from manual graph-note checkpoints.

One judgment may explicitly serve several related source nodes. Choosing that
work preserves its original owner, rationale, contribution history and authored
changes; it does not copy or merge independent judgments. The researcher can
return to a node's separate judgment. Show the original owner and currently
viewed source while editing; personal notes stay on the viewed node. These
working references create no scientific edges. Changed membership revokes the
owner's change reviews, and switching episode/ref cannot borrow another
context's work or authority. Retention must distinguish shared text from the
references used to reach it.

Terminal reading must distinguish hierarchy, selection and scientific type
through spacing and text as well as color. Changing visual density or panel
layout preserves research context. Full statements and relationship rationale
remain keyboard-accessible even when navigation previews are shortened.

A contextual action list names manual writing, inspection and review before
optional AI assistance; shortcuts remain accelerators. Unavailable creation or
AI actions explain the missing capability before opening a form or request
picker. Disabling assistance leaves manual writing/review and recorded source
AI history intact. A fixed demonstration response is labeled as an example,
never a live provider or automatic graph construction.

Before replacing a judgment with an AI proposal, compare the existing judgment
and reason with the complete proposed replacement in its owning context.
Opening or cancelling that comparison changes no writing or adoption state.
Explicit replacement preserves the reason, prior buffer and AI contribution
history; later human edits cannot erase that origin. Changed judgment, proposal,
owner or expired proposal blocks replacement under the earlier comparison.
This whole-judgment operation must not imply selective node/link incorporation.
Returning to pre-adoption text also compares it with newer kept writing before
explicit restoration; cancelling retains newer text. Unkept judgment edits stay
separate from either kept replacement or restoration.

While writing a judgment, keep its recorded subject and available conditions
visible beside or above the editable text. Expanding the full source context
and returning preserves text, cursor and undo state. Display source references
without implying the artifact was opened or verified; a plan is not a measured
result. Episode/current-global-evidence context, hypothetical assumptions, draft AI
influence and failed draft saves remain identifiable during writing and source
inspection. A terminal too small to show the controls pauses editing and offers
a predictable return that retains unfinished text. A context view never creates
evidence, changes draft ownership or proves the researcher's understanding.

Directly stacked connected cards leave a visible connector shaft before its
arrowhead. A short viewport must not collapse the route to one cell merely to
fit every node. View settings group spacing, card detail and reader pinning;
changes preview immediately, explicit keep retains them for the session and
cancel restores prior settings/position. Changing presentation preserves the
selected research context, notes, judgments and review bindings. Clipped-node
counts and the route to their relationship reader remain visible on short
screens. Comparison graphs inherit spacing and card detail.

The primary terminal navigation is a spatial graph: each record occupies one
box, and recorded connections appear as lines with arrowheads toward their
actual targets. Shared evidence connects to several claims from that one box.
Selecting a node keeps that node, its direct neighbors and incident connections
bright; other nodes and edges remain readable with subdued contrast. Focus
does not propagate transitively or move/filter the graph. Selecting a
relationship concentrates emphasis on its two endpoints and exact edge, and
reveals its type and rationale. Crossed lines are not new
nodes or inferred relations. Full directional relationship phrases belong in
connected node headers beside the title, readable without a code key or color;
words must not compete with crossing lines. Parallel types have separate
phrases. Wording that cannot fit beside the title continues in a reserved
header band above source text. Selection must not resize cards or displace their
source preview.
Inspecting one relation reveals its actual type and prioritizes that trace.
Visual occlusion cannot delete a relation or replace its recorded direction. Full graph, contextual reading and
an outline alternative retain the same selection, drafts and hypothetical state.

Opening a reading view and following a graph edge are distinct navigation
steps. Closing the reader restores the same selected node and viewport before
returning along earlier node traversals. The default overview gives the graph
the full panel, with small cards and selected-source context below it. Reading
opens on demand, beside the graph on wide terminals and in a dedicated pane
on narrow terminals; the reader can be pinned. Switching focus within an open
wide composition keeps its geometry stable. Partially visible nodes have named
offscreen connections instead of broken card fragments. Stable short aliases
disambiguate claims; compact captions distinguish scientific subjects/results,
while full statements and conditions remain available in reading.
An evidence reader prioritizes its measurement, conditions and named uses.

Fit changes card density and spacing within a legibility floor; it must not
pretend an oversized graph fits. Visible/in-scope counts distinguish clipping
from nodes and edges deliberately hidden by a local neighborhood. Local scope
is an explicit action rooted at a chosen node, with adjustable connection
depth; selecting another visible node does not re-root or rearrange that scope.
Returning to all nodes preserves evidence identity. Following a connection
outside local scope reveals its target, and back restores the previous scope.
Typed labels must remain whole, with exact endpoints/rationale reachable when
there is no room for an inline label. Connection counts are not evidence strength.

Nodes can carry editable personal notes. Compact overview cards mark their
presence without displacing the scientific subject or result; source-density
cards show a labeled preview and the reader shows the complete note. Notes stay
bound to their node and reasoning branch across views, shared occurrences and
follow/return. A personal note does not replace a recorded measurement, claim
statement or reviewed Judgment. Enter in its editor adds a line; navigation
input must not leak into terminal output or scroll the whole display. Resize
and redraw preserve the active text buffer.

A failed writing checkpoint preserves live text and gives an appropriate next
action for input refusal, unavailable storage/encryption or uncertain/external
checkpoint state. Complete guidance remains keyboard-readable on narrow screens;
inspection cannot silently retry, rebind writing or restore review authority.
Do not advise shortening valid writing to fix an encryption failure, or claim
that prior saved bytes survived an uncertain replacement.

Undo/redo applies to unaccepted editor text. Cancelling leaves kept text
unchanged and offers explicit recovery of unfinished writing. Character limits
must be visible. Shell suspend/resume preserves the current editing context.
Optional private prototype checkpoints recover notes and unfinished drafts
after process exit, under [ADR 0013](../architecture/decisions/0013-terminal-draft-recovery.md).
Recovery never implies accepted evidence or a reviewed Judgment.

Unfinished scientific-change fields and review explanations must remain bound
to their episode, branch and selected node. The unfinished-writing picker names
their kind, context and retention boundary. Merely reading a prefilled editor
creates no pending work; unkept edits remain separate from staged or reviewed
content. A session-only prototype retains these inputs in memory, excludes them
from manual-note checkpoints and warns before normal quit. Optional encrypted
recovery also retains these inputs with their original source and authored
baseline or judgment/selection inputs. Its source comparison preserves editor
text, cursor and undo, and explicitly choosing a current field basis does not
keep the fields or authorize anything. Resuming text grants
no review authority: expired comparisons are visibly stale, and completing an
explanation requires a current exact review after explicitly refreshing scope.
Opening a different review cannot silently replace the answer's earlier basis;
explicit comparison and basis selection precede reuse under changed meaning.
Discarding a selected unfinished review input requires explicit confirmation
and leaves staged changes and completed review intact. Browsing AI context or
editing scientific amendments must not silently cancel an independent proposal;
preparing a replacement request makes that replacement explicit.

Conditional manuscript work opens a dedicated wording review from its pending
item while preserving graph position. It identifies the cause and current
paper context, starts with blank authored wording/reason, and separates source,
candidate, diff and inherited scientific basis. Exact previews require supplied
source; graph notes or argument comparisons cannot masquerade as a source diff.
Source/wording changes or expiry revoke review. Inherited AI influence remains
visible and requires explanation or explicit deferral. Wording and unfinished
editors stay bound to their work item. A session-only prototype must disclose
loss on quit even if graph-note checkpoints are enabled; completing a review
cannot imply application, compilation, acceptance or work closure.

An exact selected-merge review can open its detached manuscript consequence
directly, retaining the same scientific judgment, reason and contribution
history. This does not install the candidate or add it to recorded pending work.
Replacement wording remains deliberately authored; its editor shows the
judgment and permits explicit reason reuse with undo and confirmation before
replacing a different reason. Full basis inspection preserves editor state.
Each wording draft stays bound to its exact parent review. Parent changes,
expiration or supplied-source changes revoke child review without erasing text.
Earlier drafts remain reachable from the original work; explicitly opening a
different parent starts separate wording rather than silently transferring text
or AI influence to a new scope. Returning restores the originating review and
graph context. These drafts remain outside manual checkpoints. Optional encrypted
recovery retains wording and unfinished wording/source-path input with original
scientific history and exact supplied source bytes. Restored detached parent
reviews remain historical; editing stays available, while a new scientific
review starts separate wording. A named manuscript-draft picker reaches these
drafts without adding detached work to recorded obligations. Opening saved work
reads no source file and restores no review authority. Changed or unavailable
source retains the earlier draft rather than silently rebinding it. Manuscript
review answers and completed reviews remain explicitly session-only.

Returning to conditional explanation work restores the original judgment and
reason beside original/current science and retained AI contributions. One to
three causal topics permit blank or partial human writing and explicit reuse
of the original reason without copying it. Kept and unfinished text remain
separate by work/topic. Inspecting source preserves the editor; changed evidence
retains the earlier writing basis until an exact displayed-context refresh.
Unavailable source leaves retained writing editable but cannot establish a
current basis. No answer is graded or automatically completed. Conditional
items are not accepted UnderstandingDebt; writing or returning cannot close
them. Default session-only explanations are excluded from manual checkpoints and
disclosed on quit. Optional encrypted recovery preserves partial explanations and
their original basis without restoring a review or closing an item. Ordinary graph construction gains no mandatory explanation
form from this return workflow.

Branch candidate review separates authored changes from selected merge review.
Both expose selected/required/omitted scope, exact field effects, before/after
graphs and preserved judgment provenance. Copying judgment wording into its
Interpretation is an explicit user action. Candidate calculation must not imply
installation, accepted reasoning or new pending work. Merge review binds to a
supplied manuscript snapshot, retains earlier AI influence and requires the
service's explanation or deferral. Selection/source/parent-draft changes or
expiry revoke review; a stale parent cannot be bypassed through its child merge.
Returning restores the original graph/Work context. Session-only candidates and
unfinished editors need visible quit disclosure. A synthetic active example must
be explicit rather than silently reopening closed reasoning.

The argument outline begins at the thesis. Claims, evidence, experiment records
and follow-up plans unfold along recorded relations, whose type and direction
remain visible on the connection. Shared nodes may appear at several positions
as references to one identity. Unlinked records are identified explicitly;
presentation must not invent an edge to fit them under the thesis.

Shared evidence shows a consistent short label and the number of distinct
claims directly connected by outgoing scientific relations. Its reading view
names those claims and their exact relation types; support, challenge and
qualification are not collapsed into a generic support count. Structural
connections and repeated outline positions do not add to that count.

The default Argument view is complemented by an Evidence uses view rooted at
an observation. It shows direct claim uses first, with further recorded claim
paths available on expansion and experiment/source context reachable through
all connections. Changing the reading view does not reverse or create an edge.
Keyboard follow/return preserves occurrence and view context; evidence identity,
branch-bound drafts and hypothetical state remain shared across both views.

The user has selected the terminal medium and supported reference qualities,
and supports the prototype's revised color/spacing treatment and thesis-rooted
outline, a complementary evidence-use view and spatial graph navigation. This establishes the next
visual baseline, not approval of the entire product. Further composition and interaction choices remain in the
[living design](../designs/2026-09-22-episode-review.md); the implemented
prototype's narrower scope is described below.

The first portable model/service milestone is narrower: the
[paper candidate model and query service](../designs/2026-08-03-domain-model.md#paper-argument-extension-under-review)
exposes the argument structure and hypothetical impact using a defined
synthetic example. Those APIs alone establish no accepted authority, durable
project or completed graph interaction. The connected terminal and personal
workspace described below supply the current interaction and local-return
behavior; the older browser conversion is separate work.

The public [personal project entry](../development/workflow.md#personal-project-writing-in-the-terminal)
now starts from human-written thesis/question and retains notes, judgment/reason
and separate unfinished writing across process restart without native keys. It
uses ordinary private local files and restores no protected authority. Explicit
personal result confirmation, append-only correction, selected manual reasoning
and a next question now reuse that same workspace and original judgment/reason.
Public backup/export and fresh restore preserve the saved contents; the declared
source artifact now includes and checks that same manual loop. The synthetic status below concerns
the older demo and its encrypted recovery path.

The [synthetic TUI](../development/workflow.md#terminal-paper-prototype) now
projects that service into a terminal graph/reader and optional outline panes, shared-evidence navigation,
hypothetical impact, personal notes and node-bound judgments. Its Work reader
connects scoped offline-example proposals and selected scientific change review
through the paper services, retaining AI/human contributions and exact
before/after comparisons. Completion remains an unaccepted review. Manual
claim/subclaim, scientific-connection and follow-up-plan forms project an independent
draft graph over existing synthetic sources before judgment completion. Their
owner is the original episode/ref/existing node; new candidates are not separate
judgment/checkpoint targets. Candidate fields and graphs remain unaccepted; the optional encrypted checkpoint
retains their kept/unfinished content and original source binding.
New plans require an explicit target claim, question, conditions and measurement
name/definition/unit/comparison. They remain unrun, with no measured result;
missing fields stay editable without fabricated scientific defaults. The graph
shows their tests relationship, and selected review includes required draft
claims. Explicit judgment reuse now connects up to 16 existing source nodes in
the same episode/ref, retaining the original owner and separate alternatives.
Links and choices are session-only by default; existing manual checkpoints retain text
at its original node without restoring those associations. The optional encrypted
judgment checkpoint for cumulative examples also restores those links and choices. A bounded provisional
result-entry form now retains source/measurement text and a tentative judgment
beside an existing subject, with original/current context and unfinished input.
It creates no confirmed evidence or graph relationship. This older synthetic
capture route does not itself provide the separate public personal confirmation
and complete local return described above. Optional
private UI checkpoints recover manual text. A separate Mac-only encrypted
judgment checkpoint now restores partial judgments, adopted AI contribution chains,
pre-adoption text, notes, work links and unfinished judgment/note editors across
process restart, against exact cumulative-example history. It restores no current
request, consent, proposal-adoption capability or scientific review. Argument candidates and provisional results also retain original source context,
identities, selection/omission and unfinished input through the versioned encrypted
checkpoint. Partial conditional explanations also recover their original judgment,
rationale links, source contributions, writing basis and separate unfinished text.
They remain open and unaccepted after return. Unfinished scientific-change
fields and review answers now also retain their original source and writing
basis; restored answers require a fresh exact review. Identical original sessions
may share checkpoint bytes, while each input retains independently validated
context and separate restored state. Different past judgments remain distinct.
Manuscript wording also
recovers its original recorded/detached science and exact supplied source,
including unfinished wording/source-path editors. Manuscript review answers and
completed scientific reviews remain visibly session-only; the UI names exclusions and refuses
oversized saves instead of truncating origin.
See the [bounded recovery workflow](../development/workflow.md#encrypted-terminal-judgment-recovery).
Interpretation construction now selects recorded observations explicitly and
supports explicit reuse of its kept wording as the owning judgment. It obeys
the existing one-interpretation-per-episode/ref bound, leaving previous episodes
intact. Candidate construction and this reuse remain unaccepted work; current reviews
are session-only even when encrypted writing recovery is enabled.
Existing selected synthetic projects with no episode now ask for a human-written
first question before entering the graph. Explicit preview/start preserves the
retained thesis and source association; cancel leaves the checkpoint unchanged.
This is unaccepted work under the
[terminal project entry](../development/workflow.md#selected-synthetic-project-in-the-terminal),
not public lifecycle readiness or evidence confirmation.
The default run is volatile and opens no browser or listener. The cumulative
example adds explicit episode/ref selection, context-bound draft sessions and
conditional pending-work navigation. Closed reasoning views still expose
current global evidence; browsing must not imply a historical evidence snapshot
or discharge work. Detached branch candidates, selected merge review and supplied-source
manuscript review are connected as unaccepted session work. Live providers and
protected acceptance/project storage remain unfinished TUI connections. Local PTY evidence
does not establish supported production server use or human understanding.

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

Chat, a broad Inbox home, an unrestricted graph editor, dashboards, command
palette and background daemon remain post-V0 hypotheses. The bounded paper
argument workspace above is part of current product development.

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
- Research records default to a user-owned, project-specific private workspace
  outside application and paper/code Git trees. Initialization shows the paper
  and workspace locations separately. Publishing or cloning code does not
  publish or back up those records; sharing requires a separately approved
  export. [ADR 0008](../architecture/decisions/0008-private-research-workspaces.md)
  owns placement and association. The selected device-replacement policy in
  [ADR 0014](../architecture/decisions/0014-device-replacement-recovery.md)
  restores an encrypted research backup with a separately retained recovery key
  and requires explicit new-device approval-key enrollment before continued
  accepted writing. Database, encrypted format and recovery implementation
  remain unfinished; the policy is not a working-custody claim.
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
- An outstanding request does not block drafting or manual review. Cancellation,
  timeout, changed context or a replacement request prevents adoption; a late
  response retains its trace without overwriting newer work. Refused/malformed
  results remain visible and consume their dispatched attempt, requiring a new
  explicit request to try again. The current
  [offline adapter](../development/workflow.md#paper-context-and-offline-drafting)
  exercises this boundary without a live provider.
- Operational logs and measurements are local, bounded, redacted, previewable,
  and never transmitted automatically.

## 10. Product gates and success

The owner-selected current GitHub publication is the manual personal source
preview in [release section 5.5](releases/validation-prototype.md#55-source-delivery-readiness).
It declares live AI unavailable. The later
[AI-connected milestone](releases/validation-prototype.md#ai-connected-github-publication-milestone)
must pass actual provider and own-project origin-return checks before that
capability is advertised. Neither release claims complete H0/H1 or V0 below.

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
- the paper argument workspace meets PG-1 through PG-5, and contextual Episode
  Review makes accepted versus proposed, impact, target, manuscript phase and
  debt legible;
- forged, stale, replayed, cross-project, and model-originated authorization
  fail;
- deterministic stub and already-running local endpoint exercises change no
  accepted state; and
- an unfamiliar researcher completes the gated journey without coaching.

### Live-paper V0

Compare complete first-pass workflows: from starting interpretation of an
eligible result through recording the decision and its manuscript consequence,
using equivalent boundaries for ClaimBranch and Markdown/checklist work. Do not
use a second judgment of an already-decided episode as first-pass timing.
The comparison protocol is not yet frozen; the
[release scope](releases/validation-prototype.md#62-baseline-and-observation)
owns the required user approval before V0. The protocol
records trace completeness, active and wait time, human rationale/edits,
accepted AI contribution, debt, false alarms, manuscript outcome, and any
attested material omission surfaced before the final decision.

V0 may show directional utility and workflow noninferiority; it does not prove
causal prevention. The
[validation prototype](releases/validation-prototype.md) owns the exact outcome
rule. Only VALIDATED opens ordinary candidate product expansion. Its
[bounded hypothesis-revision rule](releases/validation-prototype.md#64-bounded-revision-after-a-failed-hypothesis)
allows the user to authorize a minimum evidence-backed correction to a failed
initial shape, without erasing the failure or waiving safety gates.

## 11. Explicit non-goals before validated V0

- autonomous research decisions or accepted model writes;
- a general semantic VCS, arbitrary/nested merges, or automatic conflict solver;
- universal scientific ontology, an unrestricted graph editor, graph database,
  embeddings or GraphRAG without measured need; the bounded paper argument
  workspace is explicitly in scope under ADR 0011;
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
- per-platform process isolation and user-presence adapters, macOS first;
- browser versus native/CLI authorization helper;
- exact supported macOS/Windows, shell, Git, browser, filesystem and LaTeX
  versions;
- marker behavior and compiler isolation on the real paper;
- physical serialization, canonical JSON, key storage, and signed export shape;
- supported provider deployment evidence, envelope details, and retention settings; and
- measured UI, graph traversal, recovery, and onboarding budgets.

The portable paper candidate model now defines thesis/claim roles, typed
claim-to-claim relations, shared evidence, finite bounds and hypothetical impact
in the [domain extension](../designs/2026-08-03-domain-model.md#paper-argument-extension-under-review).
The offline [paper context and draft service](../development/workflow.md#paper-context-and-offline-drafting)
now connects selected scientific fields and optional current draft text to exact
request review. It also connects a complete judgment to an unaccepted selected
change preview with before/after graphs, retained provenance and stale-review
rejection. The separate [cumulative candidate profile](../designs/2026-08-03-domain-model.md#cumulative-paper-episodes)
now retains sequential episodes and exposes their graph/history and isolated
volatile drafts to the TUI adapter. A complete draft can now construct a
[selected branch candidate](../development/workflow.md#draft-to-branch-candidate)
in the active episode without changing evidence or main. Its recorded alternative can be reviewed as
an exact selected-merge candidate with retained source contributions and graph
effects, using the [volatile review adapter](../development/workflow.md#exact-cumulative-merge-review).
The [conditional work and manuscript adapter](../development/workflow.md#conditional-work-and-manuscript-review)
now reconstructs unfinished consequences across candidate episodes and reviews
explicit wording against supplied marked-source bytes. It retains source AI and
leaves all work unresolved after preview or Not now; supplied bytes are not a
verified original file.
Its understanding-return service now restores a conditional item's original
judgment, contributions and argument beside current paper context, with changed
evidence/head state explicit. This is a read-only adapter for later interaction;
the [partial-explanation service](../development/workflow.md#partial-understanding-explanation)
now retains unfinished explanation and explicit reuse of the original rationale
against bounded contextual topics. Changing evidence preserves that writing
while showing its earlier basis; returning or rebinding never marks an answer
complete. The TUI now connects these topics, partial writing, rationale reuse
and original/current context through conditional pending work. The adapter
remains non-authoritative; the optional encrypted TUI checkpoint can now retain
its partial writing and original context. There is no accepted debt or human
closure, and this does not establish production custody.
The separate [versioned closure-candidate contract](../development/workflow.md#versioned-understanding-closure-review)
now checks exact cause-review and current evidence/topic/context bindings. It
still requires an accepted source-loading and human-authorization integration
before any application item can actually close.
The separate [proportional-review service](../development/workflow.md#proportional-paper-review)
now distinguishes quiet drafting, rationale-based alternative recording and
contextual high-impact merge review. It retains amendment source revisions and
inherited AI while allowing explicit reuse of the existing reason. These are
candidate APIs; typed AI graph adoption, TUI connection and authorization-bound
acceptance still need their owning integrations.
The [exact operation-review API](../development/workflow.md#exact-paper-operation-review)
now retains the selected scientific effects, full contribution sources and
explanation disposition in one versioned request. Rechecking rejects changed
research/manuscript/session context or expiry; loading an earlier review cannot
replace current work or grant approval. This completes the portable request
boundary. Its separate conditional transaction-effect API now retains that same
review, forecast reasoning heads and exact-cause manuscript/understanding
obligations together, preserving amendment-only AI and original topic/reason
references. This is unaccepted preparation with no receipt or durable accepted
write; it does not complete the gateway/storage requirement.
Its separate record-transition API now calculates and replays a new unaccepted
alternative from that exact review, retaining the original judgment and all
amendment origins for further candidate review. Main and evidence stay unchanged;
first branch creation and interpretation remain one returned transition. Merge
replay and native accepted storage remain unfinished. The enclosing review and
origin history must remain alongside the legacy scientific commands.
An independent [encrypted work checkpoint](../development/workflow.md#encrypted-unaccepted-work-checkpoint)
now preserves unaccepted source history, amendment origins, Judgment, exact
review and partial explanation across process restart. It reconstructs sources
without restoring approval. Its [device work-key adapter](../development/workflow.md#device-work-key-reopening-and-recovery)
now reopens encrypted work on this Mac without retaining the plaintext data key
between runs. A separate recovery key restores an encrypted copy into a fresh
destination and a new device-key identity, preserving the original. This is a
synthetic backend API; actual replacement-device validation, complete TUI retention,
protected acceptance and production signing custody remain unfinished.
The synthetic source preview also exposes explicit checkpoint inspection and
create-only encrypted backup/restore commands. They preserve the same
unaccepted authority and remain separate from TUI retention and own-project
initialization; see the [command contract](../development/workflow.md#encrypted-work-commands).
The [paper/work association API](../development/workflow.md#paper-and-work-association)
now initializes a legitimate empty candidate paper and retains its selected Git
root, marked source and complete encrypted work together. Explicit relocation
requires the same source bytes; a missing paper leaves saved work readable.
Its separate initialization-review API binds the entered title/thesis, exact
source/workspace and empty initial head before returning that candidate. Changed
source, session or expired review refuses continuation; imported reviews cannot
install a seal. It remains unaccepted and does not initialize protected history.
Its separate enrolled native attestation now reuses those initial fields and
checks the empty seed/root before private signature verification. The app
rechecks source and destination before/after success. Both native roles now
independently check the exact Git/file identities, marked manuscript bytes and
private external workspace, refusing observed changes before signed success.
Initial signing refuses an enrolled protected target with existing or pending
record state, retaining those files. The native binding and target identity are
checked independently from the candidate-work location; this read-only check
does not reserve storage or authorize a write.
Scientific source fidelity and actual initial OS approval/cancellation remain
unverified; repeated filesystem checks are not atomic acceptance. Protected genesis
and atomic accepted storage remain unfinished.
An explicit backend source-association refresh now retains changed manuscript
identity/digests alongside prior snapshots, keeping all writing and historical
review inputs unchanged. It does not confirm scientific agreement or revive
consent; a fresh exact review is still required for any later protected action.
Its bounded synthetic terminal connection now previews a selected paper and
human-written working thesis/first question, explicitly creates a candidate
episode, and reopens encrypted writing with its association intact. Changed or
missing source remains visible without automatic refresh or reconciliation.
A named Paper connection action now explicitly previews same-content relocation
or changed-source refresh through that backend. It preserves earlier writing,
graph context and review authority boundaries; source/work changes require a fresh
preview. Refreshing the connection does not rebase scientific writing.
This older encrypted path does not provide protected own-project acceptance
or scientific source reconciliation. The separate personal alpha above supplies
public initialization and local return without conferring protected authority.
This still supplies no accepted writer. Protected persistence/migration, durable reuse across research episodes,
live provider integration and the live evaluation shape remain unfinished. A candidate
schema alone is not a complete research workflow or permission to invent
accepted facts in the UI.

The [source-built Mac runtime preflight](../development/workflow.md#source-built-mac-runtime-preflight)
now provides repeatable local build and separately pinned identity inspection.
Its separate synthetic review transport now checks exact running peer identities
and preserves candidate review bytes without issuing authority. A separate
synthetic key-preparation API now binds a new device signing-key candidate to
the project and exact runtime, with explicit native review and a fresh-process
reopening check. Native local enrollment now independently binds the exact
approval roles, retained device key, restricted worker and minted resource under
[ADR 0015](../architecture/decisions/0015-native-local-enrollment.md).
Synthetic foreground enrollment, fresh-process registered signing, native
authentication cancellation, resource denial and revocation have been observed.
Atomic accepted operations and production research custody remain separate
requirements described in the linked workflow.
A synthetic exact-review signing connection now reuses the existing judgment,
reason, selected effects and explanation disposition in foreground native review.
The adapter also handles origin-bound record reviews, signing their complete
registry commitment while preserving candidate authority. Omitted origin content
is not independently verified by that window; actual foreground v2 observations
remain separate from native parser/software-signature checks.
Its private gateway verifies the complete review's device signature without
returning a portable receipt. Cancellation preserves research and key material;
changed or expired current context cannot report signing success. This does
not establish accepted storage or understanding-debt creation. Its registered
route independently reloads the local enrollment rather than trusting caller pins.
Successful build/check or delivery must remain
visibly separate from protected research readiness.

Technology choices must preserve the accepted human-owned, AI-optional,
three-plane contract rather than redefine it.

A source-built restricted proposal worker now connects bounded response handling
to the existing offline proposal broker. It receives no research/key handle and
uses no file/network exception. Its result remains proposal-only and explicit
adoption remains separate; manual work stays independent. The component's
synthetic resource-denial observations do not establish a supported external
provider topology or accepted research custody. The
[developer workflow](../development/workflow.md#source-built-mac-runtime-preflight)
owns its build, application-container lifecycle, commands and limits.
