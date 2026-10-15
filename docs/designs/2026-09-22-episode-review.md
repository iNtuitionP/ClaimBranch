---
kind: design
status: in-review
owners: maintainers
last_reviewed: 2026-10-15
---

# Design: a research judgment that remains understandable

## Purpose

Make R1's intended research experience concrete enough to review before building
the product UI. The [product definition](../product/product-spec.md#1-product-definition)
owns the intended researcher outcome: use AI substantially while explaining
and owning scientific judgment, and preserve the link from evidence through
reasoning to the paper.

The design question is whether a researcher can read a paper's argument, inspect
its evidence, form a judgment, identify AI influence, and return to the decision
and its unfinished consequences. The graph is the primary workspace under
[ADR 0011](../architecture/decisions/0011-paper-argument-graph-workspace.md).
The product's [PG-1 through PG-5](../product/product-spec.md#7-interaction-and-visual-character)
are user requirements; the interaction mechanisms proposed below remain in
review. A rendered screen does not establish understanding or live product value.

## Foldable two-entry graph and direct editing

Owner-selected requirements, 2026-10-15. G01 vocabulary and G02/G03 folded
projection/terminal controls and G04–G06 direct revisions, optional proposal
prefill and private view return are implemented in the current checkout. The
existing plan records final verification and publication status separately.
The researcher should recognize a large paper's argument, enter through either
its thesis or an experiment/result, inspect omitted qualifications, and edit
the actual records without relying on node IDs or editing personal notes alone.
The [product graph requirements](../product/product-spec.md#7-interaction-and-visual-character)
own the behavior; the [six-outcome implementation plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#foldable-two-entry-graph-implementation-plan)
owns sequencing and evidence.

### Two entry views over one graph

| Entry | Initially visible | Expand one level | Retain while navigating |
|---|---|---|---|
| `1 Argument` | Thesis and principal claims; deeper arguments folded | Subclaims and direct recorded basis; then observations and experiment/source context | Thesis path, cross-branch uses and scientific directions |
| `2 Experiments` | Searchable experiment/result chooser and selected root's immediate recorded context | Experiment -> produced observations -> claims using them; for an observation root, direct claim uses plus experiment/source access; higher claims/thesis can expand afterwards | Selected experiment/result, conditions, actual relation types and return path |

The planning baseline `2 Evidence uses` accepted observation roots only. G02
now supports recorded experiments, observations and distinctly unrun plans; G03
connects the chooser and fold controls. G04 adds direct recorded revisions and
G06 adds validated private presentation return. Completed experiments
with no observations remain selectable, with an explicit empty result state.
Unrun plans may be inspected but must remain visibly planned and cannot acquire
produced observations by being expanded. Multiple observations from one
experiment retain separate identities; one may serve several claims or experiments
only where the stored relationships actually say so.

Keep fold/root/viewport state independently per project, episode/ref, lens and
root. Switching `1`/`2` restores the prior view without losing writing, selection
or undo. Following a link outside the projection reveals the destination with a
return path, without silently switching to the thesis view. Persist supported
presentation state across reopen with identity/context validation; never restore
an authorization or review merely because a view was restored.

Stamp cached/persisted navigation with the graph revision. After edits, rebuild
and validate root, selected occurrence/path and fold ownership against canonical
IDs before restoring. A missing path falls back to the same record's current
occurrence, then the root with an explanation; never discard its draft. Ownership
changes invalidate the old occurrence fold rather than moving it elsewhere.
Persist only view preferences/IDs in an atomically written private workspace UI
sidecar, separate from scientific history, canonical sharing and research backup
payloads. A missing/invalid sidecar resets presentation, not writing or science.
The finite sidecar fields are its format version, project/episode/ref, lens,
canonical root ID, selected canonical ID/occurrence, fold ownership keys, viewport
and graph revision. Concurrent windows may use last-writer-wins for these
presentation fields only; every load validates revision/context, and this policy
never governs scientific history or writing checkpoints.

### Folding and exact connections

Activation (an explicit expand key or click) of a folded card reveals one level;
keyboard and pointer equivalents must be visible. Moving focus or hovering alone emphasizes
connections without unfolding, resizing or moving cards. An explicit collapse
action folds an open group; repeated selection does not unexpectedly close it.
Keyboard focus/activation is mandatory; hover is optional where the terminal
already supports it and must not introduce a platform-capability prerequisite.
Keep unaffected positions stable where possible and reveal expansion near its
origin. Preserve the existing pan, explicit neighborhood and outline alternatives.

Folding is a disposable reading projection, not a new parent/child scientific
relationship. Deterministic finite ownership of display groups handles DAGs,
cycles and shared evidence with references to canonical identities. A reference
must not look like another observation or increment a scientific record count.
If all endpoints are visible, their actual links stay inspectable even across
display groups. Collapsed group boundary bundles are marked as bundles with
underlying edge counts and source/target access, never drawn as one new support.

Separate exact counts of hidden internal edges from boundary edges, by canonical
type/direction; distinguish unique records from references and viewport clipping
from deliberate folding/filtering. Define membership and deduplication before
rendering so nested folds cannot double-count a shared record. Do not infer
transitive support. Preserve parallel edges and rationale. Search reveals the
path to a match temporarily and can return to the prior folds.
Canonical IDs, not session aliases such as E1 or outline occurrence counts,
identify edits, proposals and unique records. Render every arrow from its own
stored endpoints, including opposite-direction parallel edges; placement cannot
choose one direction for the pair. A result -> claim -> challenge -> claim path
must show the challenge hop, never imply that the result supports the last claim.

Qualifications/challenges, mandatory companions, evidence corrections or
retractions, unresolved imported content and explanation-review obligations
remain discoverable on folded boundaries. Relation types and record/work status
use separate visual sections. Inspecting an indicator reveals its exact source
and path. An impact lens propagates recorded dependencies beyond folds and
filters, marks affected anchors, and distinguishes structural reach from a
scientific truth judgment. No all-clear indicator is inferred from hidden data.

### Content and relationship vocabulary

A node's editable one-line title communicates its scientific content; kind and
stable ID are secondary. A folded group's optional one-line description says
what it contains. Keep original statements, conditions and measurement definitions
accessible. Missing captions use a visibly abbreviated source excerpt, not
invented facts. AI caption/group-description suggestions require explicit
adoption and retained origin; no background provider call is needed to browse.

One shared registry supplies node kinds, permitted endpoint pairs, canonical edge
types, fixed display labels, directional rendering and definitions to creation,
editing, graph, legend and readers. Scientific `supports`/`challenges`/`qualifies`
must not drift into arbitrary generated phrases. Other recorded structural,
experiment, manuscript and companion relations remain separately classified.
The editor lists only valid choices for its context and explains unavailable
ones. A reading-order reversal changes layout, not the stored edge direction.
Replace the local relation phrase and outline kind-order tables together. Closed
schema validation still refuses unknown authored kinds/types before scientific
state changes. Do not invent an accepted unknown-kind history fixture. Preserve
unsupported imported source as explicitly unresolved source, inspectable outside
the accepted graph; a defensive renderer diagnostic must not silently admit it.

### Direct TUI editing and history

Provide named create/edit actions for node kind, title, content and kind-specific
fields, plus edge type, endpoints and rationale. Free text is editable; kinds
and edge types come from the closed registry. Personal notes remain separate.
Draft input can be incomplete and freely revised. Compare the entire resulting
change, affected dependencies and origin before recording it. Cancel, stale
context and save failure preserve writing and accepted state.

Published evidence is not overwritten: observation content/value changes use
append-only corrections; historical experiment records retain prior versions.
Changing a kind may require explicit conversion/replacement with a new identity
and historical link, rather than retagging an observation as a claim or a plan
as a completed experiment. Retargeting/retyping a recorded edge retains the old
relationship in history and requires revalidation of dependent reviews and
companion rules. Every title edit on a reviewed record follows its content-edit
review/revalidation path; do not rely on an AI or heuristic meaning-change detector.
Replacement leaves original edges on the original identity; the comparison offers
explicit, validated per-edge re-link choices, with historical/superseded state
and impact visible. It never silently clones or moves links to the new record.
Manuscript-anchor metadata may be edited, but manuscript blocks stay read-only.
Imported originals and AI contribution remain visible after human edits.

Reuse optional AI discussion and bounded edit proposals for user-requested
titles, content, kind and connections. Preview exact selected changes, validate
them through the same manual path, and permit editing/rejection before adoption.
Do not require free-form replies to parse into graphs. Add unsupported proposal
fields only through a reviewed versioned contract, preserving legacy replies.
New transmissions still require their existing exact consent; this plan does
not authorize a live request or make providers available to unsupported profiles.

### G01 edit coverage and durable-field contract

The shared registry is implemented in `claimbranch/core/graph_vocabulary.py`.
It supplies closed scientific enums to history/context/import/proposal schemas,
labels/order to the graph and kind picker, and endpoint choices to candidate
creation. Schema bytes remain unchanged. This is not the completed editor.

| Record/field | Existing path verified during G01 | Implemented G04 path / limit |
|---|---|---|
| Claim statement/scope | Candidate/review amendments | Direct title/content editor; validated role/parent revision |
| Interpretation statement | Candidate/review amendments | Direct title/statement and explicit observation membership revision; earlier/co-reported readings require replacement |
| Unrun plan objective | Existing edit; full conditions/metric on creation | Complete objective/conditions/metric/claim/title revision; status remains planned |
| Scientific edge type/rationale | Existing edit; endpoints on creation | Direct incident-edge entry; closed type/endpoints/rationale revision with dependent-basis validation |
| Observation statement/value | Append-only evidence events | Direct append-only text/value correction; title-only leaves evidence watermark unchanged; typed tables retain their existing correction path |
| Completed experiment question/method/conditions/metric/source | Create-only `record-experiment` | Versioned descriptive revision; measured metric/conditions stay fixed after results; previous commands remain immutable |
| Manuscript anchor associations/source registration | Existing reviewed metadata paths | Direct registered metadata/title editor; no manuscript file writes |
| Node kind | Fixed identity/kind checks | Fresh reasoning replacement, originals retained; explicit scientific re-link selection with complete validation |

The implemented durable title is a separate bounded text field, not an alias or a replacement
for full source content. Keep group descriptions in presentation data only;
if they assert new science, use the reviewed content path. Missing titles use
source excerpts. G04 records title/revision fields through command v13 and new explicit personal
work/frame versions; imported original bodies remain unchanged. Title/origin
survive private backup, readable queries and selected sharing. G05 uses existing
checked typed proposals to prefill the same direct editor; legacy provider
context fields stay explicitly bounded and do not automatically acquire titles. Old records are not rewritten or assigned human
origin on read. Every recorded title edit follows content review; invalid
unfinished writing can be retained but is excluded from valid graph/review.

### Reference applicability and validation

The inspected official references support different mechanisms:
[Kialo navigation](https://support.kialo-edu.com/en/hc/discussion-minimap/) retains
the thesis path; [Obsidian local graphs](https://obsidian.md/help/plugins/graph)
vary neighborhood depth; [Kumu views](https://docs.kumu.io/guides/views) separate
views from records; [yFiles folding](https://live.yworks.com/demos/application-features/folding/)
demonstrates explicit group expansion; [GraphMaps](https://arxiv.org/abs/1506.06745)
motivates stable geometry. These are reference mechanisms, not evidence that
this composition works for ClaimBranch or an adoption of their dependency stacks.

Compare the same large synthetic argument in both entry views: find a shared
observation, a hidden challenge and mandatory companion, follow a correction to
all declared manuscript uses, edit a claim/edge and return after reopen.
The [folded graph oracles](../validation/cases/saturation.md#folded-two-entry-graph-oracles-planned)
define observable acceptance. Terminal screenshots and test passes alone do not
prove human comprehension. Prefer one-level explicit folding over a full
shrink-to-fit map or auto-reflow on hover; retain whole-map inspection as an
alternative. Presentation values and chooser wording remain prototype choices.

## Context and current state

The current primary prototype is the Python/curses terminal graph with contextual
reading, manual notes/judgments, offline proposals, selected-change comparisons,
episode navigation, conditional manuscript review, partial explanation return
and unfinished-text recovery.
It loads bundled synthetic histories or an explicitly selected synthetic project
through the [terminal project entry](../development/workflow.md#selected-synthetic-project-in-the-terminal).
The separate public [personal entry](../development/workflow.md#personal-project-writing-in-the-terminal)
now opens a human-written thesis/question with local save/restart, AI off and
personal retention labels. This finishes the S01 entry/writing connection.
Personal result confirmation/correction, selected manual reasoning using the
same reason and a later question now connect through contextual controls and
before/after graphs. This remains a personal alpha, with no protected authority.
The [personal source artifact](../development/workflow.md#personal-terminal-alpha-source)
now runs the manual journey independently; protected accepted writes and live AI remain
unconnected. The
[intent audit](#product-intent-audit-and-next-complete-loop) below distinguishes
implemented presentation from the missing complete research journey.

The 2026-10-14 metadata follow-up adds an existing-graph action for
private-file selection, complete detached typed-record review and literal batch
confirmation. It preserves graph/writing context and separates input origin from
confirming actor. This is a file-based bridge, not approval of a per-type form
suite or user-usability proof; its [registration workflow](../development/workflow.md#extended-metadata-registration)
and existing plan own focused checks, actual Mac terminal coverage and release limits.

The following browser/storyboard description records the September 22 baseline;
it must not be used to infer the current terminal implementation's completeness.

The [execution plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r1-make-the-intended-research-experience-reviewable-p1h1-design)
places R1 after the disposable A integration and before native authority and
product implementation. No product frontend or framework has been selected.

The [offline storyboard](assets/episode-review.html) records the earlier
sheet-centered proposal, before the user's graph-workspace feedback. Open it
in a browser; its scene navigation and reading-style selector work locally.
There are no remote assets, server, login, analytics or network requests. Every
product action is disabled, and text fields are read-only. These are 14
independent design snapshots, not a functioning approval or persistence flow.

A separate [interactive synthetic implementation](../development/workflow.md#interactive-synthetic-episode-review)
now exercises the editorial layout against the portable core. It supports
blank entry, a fixed AI reply with human edits, selection, manuscript candidate
review and same-process resume. This does not change the storyboard's design
status or provide protected approval, durable drafts or H1 accessibility proof.

The user's requested argument/evidence/experiment example is also available as
an optional episode relationship view in that running application. Its eight
nodes and twelve named relationships derive from the current candidate branch
and selection. A node inspector shows original prose and connected records;
the three mixed observations retain two challenges and one qualification. The
example includes one unrun follow-up plan with an explicitly illustrative
objective. Node captions may summarize the fixture in Korean; the inspector
keeps its source wording. Desktop uses connected cards and SVG arrows; narrow
layouts stack the same nodes with explicit relationship navigation. Editing
the judgment or selection invalidates the drawing until re-review. A fresh
`--example` launch opts into the populated illustration; ordinary entry is
still undecided. This is a read projection, with no graph editing or authority.

The user reviewed that running graph on 2026-09-22 and found its node language
insufficient, requested thesis/claim-first left-to-right reading, paper-wide
argument structure, related-node hover enlargement and impact review on the
graph. This is a substantive revision of the earlier information architecture.
The current eight-node graph and fourteen storyboard scenes do not implement
or validate those new requirements. Their scientific distinctions, provenance,
source comparison and failure examples remain reusable.

Sources:

- [view examples](../../tests/fixtures/ui/episode-review.json), including empty,
  entered and edited judgments;
- the existing integrity-checked saturation source fixture for observation
  conditions, AI source text and exact before/after manuscript bytes;
- [operator oracles](../validation/cases/saturation.md#10-operator-experience-oracle);
- [product journeys](../product/product-spec.md#6-primary-journeys) and
  [interaction character](../product/product-spec.md#7-interaction-and-visual-character).

## Goals and non-goals

The researcher should be able to:

- distinguish observations, their interpretation and unresolved explanations;
- inspect why mixed evidence changes the scope of the existing claim;
- compare an AI suggestion with their edited judgment and reason;
- see exactly which reasoning is selected and which consequences remain open;
- return to the same judgment without writing a second account; and
- recognize when source changes, unavailable evidence or file uncertainty
  require a different next action.

These actions must be reachable in the paper argument context, with a readable
path between thesis, claims, evidence and experiments. See the product contract
for the confirmed requirements rather than treating the old sheet order as a
constraint on the new workspace.

R1 provides a reviewable experience proposal and synthetic examples. It does
not implement approval, a research database, live providers, manuscript writes,
compiler verification, a browser security boundary, or H1 accessibility proof.
It introduces no chat home, unrestricted graph editor, scoring, universal
ontology or second journal. A bounded paper-level model extension is required
and still under design; per-platform R2 and the existing safety gates remain
separate.

## Decision drivers

1. An undecided entry must be useful before any AI response or final judgment.
2. Scientific content and consequence must be readable before audit machinery.
3. Reuse one judgment and reason; a new authorization concerns changed scope,
   not repeated transcription.
4. Keep AI influence visible after editing without treating its explanation as
   an established observation.
5. A decision, explanation review and manuscript verification can be at different
   stages; the view must preserve those distinctions when returning later.
6. Make ordinary work keyboard-accessible and legible in a narrow split screen.

## Options considered

| Option | Benefit | Cost | Current disposition |
|---|---|---|---|
| A. Editorial research sheet | Gives evidence, human prose and consequence room to be read | Impact and paper structure require reading separate sections | Earlier primary proposal; reuse appropriate content in contextual details |
| B. Compact working document | Denser prose and source comparisons | Does not address the requested graph reading experience | Earlier storyboard alternative, not a competing product direction |
| C. Bounded paper argument workspace | Makes the thesis, basis and reach of a result inspectable together | Needs model, layout, accessibility and scenario work | Selected product direction; detailed interaction proposal remains in review |
| Transcript home or unrestricted canvas | Flexible conversation or diagramming | Does not supply bounded scientific semantics or the required argument workflow by itself | Outside this slice |

The two previously rendered alternatives change reading treatment, not
authority, fields or information order. They are historical implementation
evidence. The user has not fixed typography, colors or frontend technology;
ordinary styling choices can follow the required UX without a new branding
approval step.

## Proposed design


### Personal terminal alpha boundary

Selected 2026-10-07: ordinary private local storage without device keys under
[ADR 0017](../architecture/decisions/0017-personal-terminal-alpha.md).
The [release scope](../product/releases/validation-prototype.md#55-source-delivery-readiness)
owns capability limits; the [S01–S04 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#first-release-outcome-ledger)
owns work and the early feedback checkpoint. No storage approval remains pending.

Retain the selected spatial graph, compact cards, color plus text, full edge
phrases, direct-neighbor focus and contextual writing. Previously selected
Heptabase/Obsidian references support construction and return; Kialo supports
hierarchy/shared identity; VISAR supports text/argument correspondence. Do not
start another palette, layout or framework exploration before completing the loop.

S01 now connects public `project init/open` to the existing graph and full writing
checkpoint using a distinct personal store. The context strip says **PERSONAL**;
work/editor/link retention labels say local recovery, while scientific source and
user text remain untouched. Explicit setup discloses the unencrypted boundary;
quit reports saved personal writing without claiming protected research was
accepted. Notes, partial judgment and separate unfinished text reopen against the
same source association. The [workflow](../development/workflow.md#personal-project-writing-in-the-terminal)
owns commands and observed terminal coverage. S02 now connects personal result
confirmation/correction and selected reasoning to the same saved workspace;
S03 rescue and S04 source delivery are connected. Further interaction changes
follow concrete task feedback; local checks do not establish unfamiliar-user understanding.

Recovery uses the same validated writing/history envelope rather than a second
editable record. Close the terminal before inspecting or backing up saved work;
the output identifies its saved digest and excludes newer unsaved input. Backup
and readable export have distinct formats; both create private files exclusively
without overwriting existing copies. Restoration leaves the original and its
paper source intact, and changed/missing source stays explicit. Retained AI origin,
unfinished writing and open follow-up cannot become approval through restore.
The public commands and retention boundary live in the existing workflow.

The result preview separates the confirmed fields/limitations from tentative
judgment writing. Source references are explicitly unopened. A retained capture
names its recorded copy and cannot confirm it twice; correction drafts record
only statement/value/reason and are consumed after successful saving. Changed
units or conditions require a separate run/result. The reasoning preview shows
selected/required/omitted changes, impact, original reason and retained origin,
with before/after graphs. Cancel/failure returns to writing. The next-question
editor retains cancelled input for this session; preview warns that closing the
episode prevents confirming its earlier unfinished results. These controls
improve recorded continuity; they do not certify human understanding.

Show **Personal workspace** and actual persistence status in the context strip.
Manual actions come first: add claim, attach result, connect, write judgment.
Label provisional versus personally confirmed observations; confirmation does
not certify source fidelity or scientific truth. One shared observation has one
identity, and scientific relations retain their type, direction and rationale.
Use record/keep action names, never protected approval/signature success.

Begin from the person's thesis/question, with no AI-prefilled graph. Keep node
notes separate from scientific text. Reuse the same judgment/reason in its selected
consequence and manuscript follow-up. Partial explanation is unfinished writing,
not formal protected debt or a comprehension score. AI is off by default; imports
and later edits cannot erase retained origin. Manuscript source remains read-only.

Return after exit to the same writing and graph with changed/unavailable source
explicit. Keep/cancel and kept/unfinished input remain distinct; a save failure
preserves live text and never reports certainty it cannot establish. A recovered
comparison grants no approval. Local files/backups are unencrypted and outside
Git; disclose that boundary clearly in setup/help without repeating a security
form during ordinary authoring. Existing encrypted work is unchanged.

First feedback exercises one human-authored paper/result, a chosen connection and
judgment, then quit/reopen. Ask what was hard to locate, read, understand or retain;
fix that observed friction before optional features. Unknown SSH/physical IME/
independent-user evidence stays unknown and does not delay showing the local loop.

### Optional AI follow-up proposal

Proposed 2026-10-08 after the user asked whether LLMs can read or modify this
research and requested the next implementation plan. The
[four-unit follow-up](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#optional-ai-follow-up-implementation-plan)
owns execution; the
[acceptance proposal](../validation/cases/saturation.md#131-optional-ai-follow-up-acceptance-proposal)
owns observable checks. This section selects no provider and enables no live
personal feature. The manual alpha boundary above remains current.

**Researcher action.** From an unfinished judgment in the argument graph,
request a counterargument, missing condition, alternative interpretation or
discriminating experiment. Inspect and edit suggestions, choose only the
consequences they want, record through the appropriate app route using the
same reason, and later inspect both their thinking and AI influence. A
complete judgment or separate decision log is not required to ask for help.

For the selected `gpt-6-sol` Codex continuation, the contextual reader now shows
the complete unsent HTTP body and digest rather than only the application input.
Its read/confirmation checks remain on the same judgment owner. The separate
[exact relay](../architecture/decisions/0019-reviewed-codex-http-relay.md) discards
generated agent wrapper content; qualification still refuses public dispatch
before login or an attempt. Existing item comparison/editing and reason/origin
return are connected for owned replies, without new screens or save formats.
Actual service acceptance and useful novel-task assistance remain L04 gates.

| Approach | Assessment |
|---|---|
| Give a filesystem agent the whole project and let it edit saved JSON | Ordinary same-user tools can do this today, but it bypasses the app's review, source bindings and origin contract. Human export/backup is not scoped model context. Excluded from this product integration. |
| Replace the whole judgment with one AI reply | Already available in the synthetic example with explicit comparison and prior-buffer recovery. Retain as a named action; it cannot select a suggested node or relationship independently. |
| Scoped context → typed proposal → human selection/edit → exact consequence review | Selected follow-up. Portable typed adoption/origin and the offline contextual terminal rehearsal now reuse existing services and keep the evolving human argument primary. Actual provider connection remains gated. |

**Working composition.** Keep assistance attached to the selected claim/result
and its existing judgment owner. Use the same contextual action list, editor,
graph and reader rather than add a chat home. Request preview names the task,
destination, exact scientific content and optional draft. Separate advisory
critique from suggested scientific changes. Show each suggested item's full
content, references and AI source before incorporation; current writing remains
available alongside it. Selecting dependencies must show the resulting scope,
including required and omitted items, before staging/recording. Visual
before/after effects use recorded scientific direction and preserve shared
evidence identity. A proposal cannot create a measured observation or certify
an existing source merely by linking it.

Incorporation stages unaccepted candidates. A person's subsequent explicit
recording is a separate action, preserving their original reason and ordered
AI/human contributions. Editing, copying recorded adoption into a later
candidate, returning to earlier text or opening a new episode cannot erase
known AI influence. The app cannot detect arbitrary unreported outside-AI
typing and must not claim it can. Candidate origins must come from owned
proposal items, not fabricated human judgments or model-supplied actor flags.
Restore original basis and writing without restoring consent, an adoptable
expired response or a current review. Payload erasure retains its availability
marker/digest and any contribution material required to explain recorded work.

#### Contextual conversation and small edit proposals

Review requested 2026-10-12. The owner proposes reading the selected argument,
discussing it in natural language, and explicitly asking for a claim, planned
experiment or connection. AI may also suggest a concrete next graph action.
This section assesses that direction; it does not implement a new response
contract, supersede accepted ADRs or close L04. External observations and their
limits are in the [reference comparison](../references/research-agent-runtime-and-graph.md#contextual-conversation-and-selected-graph-actions).

**Finding.** This serves the existing human outcome: form the judgment in
context, retain chosen AI influence, and resume without a second decision log.
The current `provider-result/v2` already permits advisory critique with zero
items. It does not require every sentence to become a node. However, the current
live path validates critique and all proposed items as one typed result; an
invalid item can reject the whole return. Separate readable advice from edit
validation explicitly rather than silently salvaging a failed legacy envelope.
The previous live rejection remains unresolved; the new design is not its proven
fix.

| Contract | Assessment of the proposed flow |
|---|---|
| Graph as primary workspace, contextual help | Keep conversation attached to the selected argument/episode and show the affected graph. The product's broad deferred-chat wording needs clarification for this bounded surface; a general chat home remains outside scope. |
| Proposal-only AI and human construction | A model describes a candidate operation. Trusted application code prepares the candidate; only a human selects/stages and separately records a scientific consequence. No model-facing writer or arbitrary tool execution. |
| Provenance and understanding | Preserve originating reply/selected passage, request/model/input basis and human edits. Pressing a button is not proof of understanding. Quiet drafting needs no quiz; consequential recording keeps the existing reason and explicit explanation/deferral choice. |
| Evidence and planned experiments | Reuse the existing experiment-plan type and its target-claim association, projected as `tests`. A planned experiment supplies no result and cannot itself `support` a claim. Do not add a generic config node or fabricate measurements. |
| Scoped input and exact outbound review | Readable context retains selected types, roles, scope, relation direction/rationale and experiment/observation status. Additional nodes, previous messages or a draft must be selected into the actual reviewed request; mention of B does not authorize silently reading its files. |
| Return and current state | Reading a saved reply restores no action permission. Revalidate targets/current source before preparing an edit. Existing ADR 0020/0021 identical-context and external-source limits remain; a changed-context conversation-to-edit binding needs its own explicit design. |

**Selected bounded flow (discussion, edit preparation and personal return locally checked; actual connected use pending).**

1. Read selected graph context and discuss it in the existing terminal workspace.
   Return bounded, safely rendered advisory text without requiring graph items.
   Retain an owned response identity independently of any edit candidate.
2. Offer a small optional action card only when useful: create a claim, prepare
   an unrun experiment, or connect explicitly identified existing records. The
   user can also invoke these directly. Suppress repeated dismissed suggestions;
   no background request or automatic edit is implied by offering a card.
3. Resolve natural-language aliases to current visible identities; clarify an
   ambiguous target/type/direction. Show missing scientific fields as missing.
   A user-selected passage may prefill an editable candidate locally; a separate
   model interpretation is another explicitly reviewed request, not a free retry.
4. Show the exact candidate content, typed connection, source passage and graph
   effect. Confirming creates unaccepted draft work through existing services.
   Keep no-op/cancel/manual continuation available. Validate independent small
   actions separately; an inseparable node-plus-connection group stays atomic.
5. Reuse the existing personal reasoning review for actual recording, with the
   person's reason and complete AI origin. Saving and reopening retain advice,
   unfinished candidates and origins, never a pending approval capability.

An action schema is data, not permission to execute a tool. The selected Codex
relay has no model tools under ADR 0019; this proposal can retain that boundary
and translate bounded action data inside the trusted app. Exposing real model
function/tool execution would require a separate authority review, not a renamed
`create_node` command. Automatic experiment execution and manuscript edits remain
excluded.

**Contract work before implementation.** Define a versioned advisory-message
and selected-action origin binding rather than relabeling text as an old checked
item. Bound conversation retention/context inclusion and preserve existing saved
formats. Clarify the product's contextual-chat scope, amend response/return
acceptance and L04's existing outcome, and record a new ADR for the new contract
without rewriting accepted history. Reuse graph/query, candidate, validation,
personal recording and save/backup services; no new agent framework is required.

**Selected implementation choice (2026-10-12).** [ADR 0022](../architecture/decisions/0022-contextual-advice-and-explicit-edits.md)
records the owner's implementation instruction. The requested
[four-batch L04 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#l04-contextual-assistance-implementation-order)
separates two explicit modes. Discussion returns bounded advisory text without
graph JSON. Preparing an edit returns a small typed action proposal in response
to the person's instruction; it may ask for clarification or leave scientific
fields incomplete in an editable form. It never runs automatically after each
answer. Direct edit requests need no preceding conversation. The existing
whole-result v2 contract remains readable and is not silently weakened.

The quickest passage-to-graph route is local: select retained text, open the
existing claim/plan/connection form, edit and inspect its graph effect. If model
interpretation would help, the person explicitly requests it and reviews that
new outbound content. AI may recommend a next action in its prose; adjacent
context-valid application controls must not pretend to be parsed model intent.
This first version does not need a second provider call or an executable action
block embedded in every advisory response to offer useful next steps.

Retain the original reply and its selected passage independently from action
validation. The new origin variant binds their exact text and request/model/
context to the candidate and later human revisions. Saved advice is readable
without granting staging authority. Fresh identical-context comparison is
required for a retained action; changed-context AI editing requires a new
request under the existing retention decision. Product/acceptance wording and
the ADR distinguish local implementation from actual connected use. Local controls offer claim, unrun plan
and connection forms; the person selects an exact source line or shorter excerpt
before comparison. These quiet controls can be dismissed for the session and
never open another request automatically. A separate explicit instruction uses
the existing typed result v2 with a four-item limit or critique-only clarification.
Personal recording reuses the reason and independent explanation choice. The
existing origin reader now joins a selected passage or typed item to its
original question/instruction, requested/reported model, answer and selected
historical graph context. Explicitly included earlier messages retain their
source links, without suggesting that those older graphs were all transmitted
again. Partial explanation and recorded choice remain separate after correction
and backup return. Required source erasure checks apply after restart as well
as during a live request. Owned terminal/save/return checks are not actual
live-provider observations.

**Observable checks.** A readable answer with no edit must succeed; a malformed
optional action must not erase independently validated advice; ambiguity must not
pick an arbitrary node; planned work must create no evidence/support; cancellation,
duplicate activation and stale graph state must not apply an unintended change;
selected passage and human edits must survive recording/restart/backup with AI
off. Check Korean natural-language requests and the same path in wide/narrow
terminals. Actual provider usefulness and human understanding remain distinct
from parser or fixture success.

#### Typed proposal and return contract

These interface choices resolve the 2026-10-08 cross-review findings. L01 input/
typed response and the L02 owned selective-staging/origin-return backend now
have portable code and generated schemas. The separate L03 [offline terminal
rehearsal](../development/workflow.md#selective-ai-items-in-the-terminal) now
connects explicit input review, individual selection, graph comparison, existing
candidate editing and personal explanation/return. Actual provider integration
remains L04 work; the public own-project entry remains AI-off. The
[ingress exercise](../development/workflow.md#typed-proposal-ingress-exercise) and
[staging/return API](../development/workflow.md#selective-proposal-staging-and-origin-return)
own their available interfaces and limitations; backend checks do not establish
live usefulness, human understanding or completed visual interaction.

1. **Separate typed output.** Introduce a closed `provider-result/v2` contract;
   keep the current v1 `{schema,status,text}` decoder and text callers unchanged.
   Allow typed suggestions only for `compare-evidence`,
   `critique-interpretation` and `plan-experiment`. `draft-manuscript` stays on
   the existing text-only route. Provider/model/request/context identities are
   broker-owned metadata, never authority asserted by model fields. Map context
   `scientific-relation` to amendment `scientific-edge` explicitly. Advisory
   critique has no staging effect.
2. **Selected references only.** Initially send selected recorded science and
   an explicitly included current judgment draft, which may be unfinished.
   Candidate graph context is deferred; no hidden neighborhood or provisional
   result is added. References may name selected nodes/relations in the exact
   request or proposal-local dependencies. A selected relation's endpoint
   context must be explicitly selected rather than silently fetched. Distinguish
   creating a candidate from suggesting an edit to an existing selected record:
   allocate new IDs locally only for creation, preserve the selected target ID
   for edits, and validate kind/identity before staging. A model item ID is not
   a scientific record ID or an accepted command.
   A context reference cannot ambiguously alias a target edited by the same
   response; refer to that proposed edit by its item ID so its dependency is
   explicit. L01 binds the expected typed format in the exact outbound review,
   and a wrong local completion route preserves the pending dispatch.
   Creation/edit targets are claims, interpretations, scientific relations and
   unrun plans only; an edit stages a replacement candidate, never an in-place
   source mutation. Runs, observations, measurements, source references,
   confirmation/correction events and manuscript bytes stay outside this route.
3. **One response, multiple selections.** Bind item comparison to immutable
   response/input identities, the owner/current scientific source, the exact
   item and proposed dependency revisions. Stage each displayed
   dependency-closed batch atomically: validate capacity, identities, cycles and
   origins before publishing any of its items. Staging/omitting one independent
   item from that response does not invalidate its siblings or an unrelated
   request. Editing a referenced proposed dependency revokes comparisons that
   use it. Distinguish owner/judgment identity from editor revision: identity or
   recorded-view changes revoke applicable adoption. If the request explicitly
   included the judgment, editing that included draft invalidates request review
   and response adoption; the earlier response remains readable. If it omitted
   that draft, continued typing changes neither its scientific input nor consent:
   reopen a fresh item comparison against current writing before staging.
   Comparisons always bind the displayed editor/item revisions; old confirmation
   never applies to newer writing. Whole-judgment replacement retains its
   stricter existing draft-revision binding. Changed selection revokes the
   consequence review. Changed included context never silently regains adoption.
4. **Owned origin beyond the judgment.** Version amendment-origin representation
   for immutable proposal/item/context/response references plus ordered kept
   human edits, keeping v1 reading. Do not fabricate a source Judgment or insert
   many item contributions into a single judgment merely to reuse prose adoption.
   Personal recording must carry selected and required item origins, source
   judgment origins and current judgment origins together; compute inherited AI
   from that complete set. The current `personal_research.py` judgment-only
   `inherited_ai` calculation cannot implement this contract. Test a manual
   judgment with one AI relationship through preview, record, history refresh,
   later correction and fresh open. Never record an omitted item as a chosen
   scientific change or erase AI inherited by a selected derivation.
5. **One workspace retention path.** Place typed origins and minimal trace
   metadata inside the versioned authoring/workspace representation. Current
   `PaperWork` forbids mixing a workspace with its separate singular `origins`
   registry; passing both is not an integration. Reuse existing checked source
   pooling where applicable, keeping old formats readable and refusing newer
   unsupported writes without conversion. Register each new workspace version
   explicitly in `PaperWork.create` and its reader/validator; an unknown version
   must not fall through to the current default v2 mapping. Preserve distinct response counts:
   multiple items from one response are not several dispatched requests. Test
   the existing restore contribution-count invariant before changing it.
6. **Bounded edits and total storage.** Keystrokes remain editor writing;
   append an origin revision only on a meaningful explicit keep/stage. At the
   origin/contribution/candidate/whole-checkpoint limit, retain live and
   unfinished text plus the last valid candidate and origin, and refuse the new
   keep/stage/save with precise guidance. Do not merge, drop or reset earlier
   immutable AI/human contributions to fit. Check the entire dependency batch
   and checkpoint against the existing 256 KiB canonical envelope; response and
   item limits alone do not prove it fits. Shared immutable sources may be
   referenced once instead of copied into every item; no new persistence system.
7. **History survives without live capability.** L02 owns minimal durable
   attempt/response/context metadata, digests, disposition and payload
   availability (`available`, `not-retained`, `erased`), together with selected
   contribution material required to explain the work. Retention duration is
   frozen with the actual L04 endpoint. Save received but unstaged suggestions
   as bounded read-only historical material when available. Opening them does
   not install an attempt, consent, current comparison or staging capability;
   further AI incorporation may start an explicit local review under
   [ADR 0020](../architecture/decisions/0020-retained-proposal-review.md), comparing
   original and current context without another request. Already staged
   candidates remain editable/reviewable with their origins without asking AI
   again. Raw-payload erasure cannot delete the origin of recorded work.
   Minimal trace metadata and required adopted-item origins take precedence
   over optional unstaged response payloads. Check/reserve minimal attempt
   capacity before dispatch. Under the declared retention policy, a newly
   received unstaged payload that cannot fit remains session-readable but is
   saved as `not-retained` with its digest/disposition and visible notice; it
   cannot prevent an otherwise valid human-writing checkpoint. Do not truncate
   scientific text, erase recorded contribution material or silently evict an
   earlier saved payload. Apply the same quota in the offline rehearsal. Raw
   retention duration/budget and explicit erasure remain distinct from origin.
8. **Preserve explanation choice.** Quiet drafting/advisory help/staging creates
   no explanation requirement or formal debt. At personal consequence review,
   reuse the original reason and the existing contextual impact/source review
   to expose what AI changed and what remains uncertain. A consequential
   explanation can stay partial or be explicitly left for later; retain the
   original/current basis and that human choice. Do not silently translate
   `ai_influenced=True` into a claimed human deferral, a comprehension verdict
   or an accepted UnderstandingDebt. The existing protected impact/receipt/debt
   program is not pulled into this follow-up; its closure remains unavailable.
   Freeze a separate personal `explanation_state`: `not-reviewed` by default,
   `partial`, `reviewed` or `leave-for-later`. AI origin is calculated separately.
   Editing partial topics keeps writing but cannot claim reviewed understanding;
   `reviewed` records a human review act, not comprehension. For consequential
   AI recording, expose the existing contextual review and require an explicit
   review/leave-for-later choice; reuse the original reason without a new log.
   Keep this personal state with its cause, original/current context and partial
   writing. Remove the inference `AI -> human deferred` from the newly enabled
   route: a legacy `deferred` command may encode only a compatible explicit human
   leave-for-later choice, never the AI Boolean. Preserve old histories unchanged
   and do not inject personal values into protected/F0 disposition enums.

**Personal-live scope selected.** The user explicitly chose the optional
personal-AI continuation on 2026-10-09 under
[ADR 0018](../architecture/decisions/0018-optional-personal-ai.md), retaining
ordinary local storage, weaker file protection and AI off by default. The
release boundary is resolved before dependent personal-record/persistence
implementation. Before enabling live use, still resolve the actual provider/
egress choice and complete the origin/return/interaction checks. The current
manual app remains AI-off. This decision does not waive ADR 0009. An unrestricted same-user inference
server is not supported merely because its connector is isolated. Hosted or
separate-host APIs are candidate environments requiring actual access and
egress evidence. Protected B11 remains separately gated after B09/G2; planning
an earlier personal route does not complete that program.

**Personal connection preparation, 2026-10-10.** The user clarified that each
researcher supplies their own LLM, rather than choosing one fixed provider for
the product. Borrow OpenClaw's endpoint/API/model/secret-reference separation
from the [inspected sources](../references/research-agent-runtime-and-graph.md#personal-provider-configuration).
The [working preparation commands](../development/workflow.md#personal-llm-configuration-and-unsent-preview)
now save a private profile and preview the complete unsent wire body on selected
saved science, including system instruction and typed schema. They confer no
consent, live request or topology verdict. Explicit `project init/open
--provider-directory` now attaches that profile to the existing contextual
picker and complete wire preview. Task selection, optional unfinished judgment,
disable/enable-preview controls, asynchronous owned response selection/editing
and shutdown/return reuse the existing proposal UI. The public live gate refuses
before key lookup or transport creation; owned tests replace only that gate and
cannot establish provider support. Profiles and credential references stay
outside research recovery. The connected TUI shows actual wire content;
provider setup cannot become a chat home or mandatory project onboarding.
No fixed model/server installation or automatic reading of another app's keys.

The same picker now accepts an explicit Codex ChatGPT-login profile. Its panel
shows exact selected application input and schema, with CLI-generated wrapper/
destinations unverified and the stored CLI version labeled a supported candidate,
not an observed client. It creates no request, consent, trace or response; the
Codex route refuses before client/API transport independently of the API test
qualification hook. Esc retains writing, and return defaults to AI off. This is
connection preparation, not an implemented Codex execution/return adapter.

**Retention and failure.** Extend the existing versioned workspace for missing
typed origins and traces; keep old readers and refuse unsupported data without
replacement. No second store, automatic migration or native key is introduced
for portable preparation. Waiting, cancelling, refusal, invalid output, changed
paper/draft/selection and late replies preserve manual writing. No model tools,
automatic retry, manuscript mutation, evidence confirmation, comprehension
grade or protected debt closure is enabled. Consequential explanation review
reuses the original reason and contextual topics; unfinished explanation stays
unfinished. Ordinary capture and unused suggestions gain no mandatory quiz.

Rehearse on new invented scientific content with context-matched frozen replies
before live use. Show the running offline selection/restart checkpoint for
feedback, then test one permitted live endpoint under the resolved boundary.
At that live checkpoint also observe one researcher-authored new project/task
beyond the frozen cache fixture, with explicit source and outbound choice.
It may use disposable novel content; private research is neither required nor
accessed automatically. Report when the suggestions do not help. Reuse existing
manual regression rather than requiring the person to repeat all six tasks
at every AI checkpoint.
Agent-operated PTY/retention evidence establishes wiring and preservation;
human task observations are still needed to assess usefulness and understanding.
The separate UI session owns detailed presentation; backend integration must
use the same public interfaces and does not redesign graph layout.

### Product-intent audit and next complete loop

Reviewed 2026-09-27 at the user's request to check drift after repeated context
compaction. The cause of any drift cannot be established from this audit.
The observable imbalance is substantial progress on inspecting/reviewing a
populated example, without a connected entry or durable exit for the researcher's
own unresolved result. Preserve the approved terminal graph and scientific
boundaries; prioritize the complete research action over another isolated UI
control. This is a design assessment and proposed sequencing, not a new approved
schema, platform, persistence policy or evidence of human usability.

**Intent to preserve.** The [product definition](../product/product-spec.md#1-product-definition)
and the [original Dream state](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#0c---dream-state)
describe a researcher who can form a judgment with optional AI, explain its
evidence and uncertainty, retain human/AI contribution history, see the paper
consequence and resume later. The graph organizes that work. A complete argument
or interpretation is not an entry requirement, and authoring a second narrative
for the system is not the goal. Later thesis-first graph and server-terminal
requirements adapt this intent; they do not replace it with a general canvas.

| Outcome | Current evidence | Remaining gap |
|---|---|---|
| Stay near experiments | Actual terminal input, navigation, suspend and shell restoration | Live Linux/SSH/tmux and physical Korean IME; protected server deployment is not covered by macOS authority experiments |
| Understand the argument | Thesis/claim/evidence paths, one shared identity, typed connections, focus, local scope and exact relation reader | Novel content and unfamiliar-user comprehension; large synthetic bounds checks do not establish readability |
| Start before knowing the answer | Blank node-bound judgment and manual continuation are available on the example | No public project initialization, new result/run/observation capture, or typed node/link creation in the TUI |
| Write the judgment once | Draft rationale can be reused in explanation review; provenance stays visible | Context-bound drafts and separate change/wording editors still require the user to coordinate one decision across surfaces |
| Obtain useful optional AI help | Explicit context/outbound review, adoption, cancellation and retained origin | Fixed response only; no measured real critique, alternative interpretation or experiment suggestion |
| Return after leaving | U resumes same-session text; optional checkpoints recover manual graph drafts/notes | AI-influenced writing, scientific changes, explanations and branch/manuscript work remain volatile |
| Align the paper with the decision | Exact supplied-source wording/diff and detached merge review | Accepted changes, actual manuscript application/compile/recovery and human work closure remain separate integrations |

**Concrete observations.** Public CLI actions remain `demo` and `doctor`;
`doctor --json` reports `prototype-only`. In a recorded-series adapter check,
E1 → Work → changes → Enter opened `claim-comparison`; the mutable-record picker
spans the episode rather than only the selected node. A judgment written at E1
did not appear as the draft at its linked `claim-pruning-detail`, consistent with
the episode/ref/node key. Neither is data loss or a contract defect; together
they expose a design question about one decision affecting several nodes.
At 80×24 the blank Work snapshot displayed several command lists and blank
judgment/reason prompts, without the selected observation's scientific content
in that same pane. Keeping the selected subject and source context present
during reasoning is more valuable than adding another global mode.

The [compact-card copy](../../claimbranch/application/tui_cards.py) contains
authored captions matched to frozen source statements; other content falls back
to source excerpts. This is honest prototype behavior, but a polished seed-42
example does not establish usable captions for a different paper. The
[workspace](../../claimbranch/application/paper_workspace.py) also has a bounded
16-session drafting capacity; manual fallbacks are not general durable project
support. These are tested prototype limits to revisit with a bounded real-use
model, not reasons to silently remove resource or provenance constraints.

**Reference reassessment.** Official pages and the VISAR paper were revisited;
the [YC transcript/storyboard assessment](../references/yc-design-with-ai.md)
was reread. YC/YouTube pages exposed no usable transcript in this audit, so this
does not claim a fresh full video playback or independent retranscription.

| Reference | Relevant interaction | ClaimBranch assessment |
|---|---|---|
| [Heptabase](https://heptabase.com/) | Cards, sources, editing and linked reading support thinking on a board | Preserve the map/reader relationship; connect capture and revision to it, rather than copying a marketing palette or broad knowledge-base scope |
| [Kialo](https://www.kialo.com/tour) | Thesis-based argument tree, linked arguments reused across locations, comments separate from arguments, change catch-up | Hierarchy and shared identity are well represented; add research change/resume context. Ratings or a pro/con tree cannot determine scientific truth |
| [Obsidian Canvas](https://obsidian.md/canvas) | Existing notes edited in place, direct card/connection authoring, local durable files | Creation and return continuity are missing. Reuse the interaction principle without copying arbitrary links or its storage format into accepted research state |
| [VISAR](https://arxiv.org/html/2304.07810v2) | User-written text and visual arguments correspond; manual nodes coexist with optional AI elaboration and critique | Improve text/graph correspondence and selective proposals. Its writing-study results and generated evidence suggestions do not validate empirical observations in ClaimBranch |
| [Posting navigation](https://posting.sh/guide/navigation/) and [Lazygit](https://github.com/jesseduffield/lazygit) | Contextual keyboard help and acting on a selected object | Expose a small named local action list before requiring key memorization. This is not a proposal to add the deferred general command palette |

Our application of the YC method should compare complete researcher journeys
with actual content, then tune the selected one. Recent spacing/label changes
were responsive to explicit user feedback and remain useful. Continuing that
local polish alone would not establish the original product outcome.

**Recommended next slice.** Demonstrate one unresolved result-to-judgment loop,
with both manual entry and a selected-context AI proposal route, initially using
explicitly synthetic disposable data. Start from a minimal paper question or
claim, with an incomplete graph permitted. Let the researcher reference a run
and bounded source artifact, draft an observation with conditions/metric, and
connect its possible consequence to a claim. Keep draft observation and actual
evidence confirmation distinct. No automatic directory scan, arbitrary ingestion
or experiment execution follows from this proposal.

Author graph objects through research actions such as add a claim, attach a
result, record an alternative interpretation, plan a discriminating experiment
or explain a scientific connection. Generic node creation is a supporting
mechanism. Show generated records/links for review and reuse the same writing;
the researcher should not have to maintain an additional graph description.
Personal node notes remain separate. Whether a multi-node decision reuses an
episode-scoped draft or explicitly links existing node-bound drafts needs a
bounded model/UX comparison before changing draft identity or recovery schema.

Keep the selected content, human judgment, optional proposal and changed
claim/paper consequence reachable in one contextual workspace. Label draft,
reviewed, accepted, applied and verified states in user language while preserving
their existing separate gates. AI can propose typed nodes/links from permitted
context and retain its source; neither generated text nor a graph arrow confirms
an observation. Manual completion must remain possible with AI off.

The first complete acceptance demonstration must then close and reopen the
process with the same draft/decision, source references, human/AI history and
unfinished consequence. This depends on R2/R4 custody and recovery, not on
serializing everything into the existing note checkpoint. R5 owns real manuscript
application/verification/recovery; R8 owns a permitted live provider. Native
preparation may proceed independently, but it cannot be presented as completed
TUI integration or protected server support.

**Evidence for the next review.** Compare entry from an unresolved result and
entry from an existing claim using the same new synthetic scientific content,
not only the authored compact-caption fixture. Ask whether an unfamiliar
researcher can name the observation, remaining uncertainty, reason for the
claim change, AI contribution and affected wording without being coached through
shortcut keys. Exercise 144×42 and 80×24, then a real available Linux/SSH/tmux
host. Record navigation/retyping friction and restart continuity. Source-fidelity
and deployment gates still precede private research use. A safe synthetic stub
can verify an interaction while its unavailable backend remains explicitly gated.

### Human-led construction and understanding review

Alignment checked 2026-09-27 after the user reiterated the original concern:
too much AI involvement can leave the researcher without an understanding of
the argument they are building. This concern is already explicit in accepted
[ADR 0005](../architecture/decisions/0005-human-authority-provenance-and-understanding-debt.md)
and the [product authorship and understanding contract](../product/product-spec.md#43-provenance-and-understanding-are-independent).
The [optional-assistance journey](../product/product-spec.md#64-request-optional-ai-help-and-learn-serving)
also excludes mandatory AI onboarding and a chat home. Making incremental human
construction the default interaction below is a design response to those
constraints and this clarification, not a new ban on AI-assisted drafting.

Current code only partly realizes that experience:

| Concern | Current TUI evidence | Remaining design work |
|---|---|---|
| Human starts and owns the judgment | `tui_review.py` exposes an empty human judgment and reason; AI request and adoption are explicit actions. | Complete creation of typed nodes and scientific relationships from an unresolved result, rather than only navigating an existing fixture and editing its records. |
| AI assists a person's evolving argument | `paper_draft.py:use_proposal` replaces judgment text on explicit adoption; the prior buffer and contribution history are retained. | Compare the existing judgment with suggestions and offer bounded incorporation. Whole-text replacement should remain a clearly named choice rather than the sole adoption action. |
| Explanation remains connected to the decision | The review UI reuses rationale and offers explanation or explicit deferral; it does not grade comprehension. | Keep the source, relationship reason and unresolved limitation visible while writing and reviewing, including at narrow terminal sizes. |
| Understanding obligations are honest | `finish_changes_review` reports conditional consequences with `acceptance_available: false`; this prototype review does not create accepted debt. | Connect accepted deferral and later human closure through the existing protected authorities; do not label every unfinished note or unused AI proposal as UnderstandingDebt. |

These are source-code findings and design hypotheses, not evidence that current
users have accumulated cognitive debt. Manual typing, graph construction and
clicking an explanation checkbox cannot prove comprehension either.

The proposed default is a researcher-built argument: record a result, add a
claim or tentative interpretation, choose how a source supports/challenges/
qualifies it and state why, then record what remains unknown or a follow-up
plan. Each step may remain unfinished. Quiet notes and provisional capture
must not acquire a mandatory explanation form; require scientific rationale
when forming the corresponding complete relationship/review, without inventing
missing meaning. Reuse the authored rationale at later review.

AI is a secondary, explicit contextual action available even before a complete
human draft: ask for counterarguments, missing conditions, alternative
interpretations or a discriminating experiment. Do not prefill a thesis,
connect sources, complete a graph or invoke a provider in the background.
Display a proposal separately from the current human work. Compare selective
incorporation with explicit replacement; preserve the original proposal,
human edits and contribution lineage in either case. The exact bounded adoption
contract needs implementation review before promising partial-text provenance.
The U8 comparison increment now places the current judgment and unchanged reason
before the complete proposed replacement in a scrollable terminal view. Esc
keeps both current writing and the proposal; Enter explicitly replaces the whole
judgment through the existing service. Bind confirmation to the displayed owner,
draft revision, paper context and unused proposal. Changed or expired content
requires a fresh comparison; tiny terminals pause confirmation. State AI origin,
prior-buffer recovery and checkpoint exclusions before replacement. Returning
to pre-adoption text is a comparison too, preserving newer kept writing on
cancel. Unkept judgment input remains separate in U. This makes
the existing replacement deliberate. The L02 backend now carries independently
selected item origin through staging, edits, personal review and return even
under a human-written judgment. The L03 offline rehearsal now connects its
selection and return through existing controls; useful live assistance still
needs L04. Keep unincorporated suggestions separate from
recorded science. No stage-from-AI
control may treat adopted content as manual; retyping or editing recorded
adoption does not remove origin. The system cannot detect unreported influence
from arbitrary manual typing and must not claim to prove its absence.

Validate the manual journey first with new content and AI disabled, then repeat
with requested assistance. Observe whether a researcher can explain why a
relationship exists, what the result does not establish and what AI changed.
Record task observations and uncertainty, never a comprehension score or an AI
verdict. Formal UnderstandingDebt follows ADR 0005's accepted-operation rules;
routine capture and optional help do not themselves open it.

### Planned terminal working composition

U9 save-failure guidance distinguishes writing validation before storage from
storage/encryption failure and a checkpoint requiring reopen. Prefer keeping the
researcher's current writing visible to closing the session as the first remedy.
Input/size refusal asks for correction; its cause and ordinary storage errors
appear beside the status prefix so narrow editor footers still name the cause.
Storage failure reports unconfirmed
saving without suggesting shorter scientific text. Uncertain durability or an
external checkpoint change blocks further terminal saves in that session and
asks the person to copy newer writing before exiting with Ctrl+C and reopening
for inspection. Normal q still refuses to leave while saving has failed.
A named **Inspect writing save status** action opens complete, scrollable guidance;
Esc returns to the same graph. Small screens pause the details without losing
writing. Error wording is not proof that prior ciphertext survived replacement.
This changes no acceptance, source-rebinding or custody boundary.

U4 source controls keep the researcher in the graph: a named Paper connection
panel shows the retained paper and its observed status. Prefer a contextual
panel over asking the researcher to edit metadata or leave the TUI for a second
workflow. Separate relocation (same exact bytes, new location) from source
refresh (changed bytes at the same location). Preview before/after paths and
fingerprints, preserved writing and reader compatibility before explicit apply.
Cancel returns to the same graph; stale source or work requires another preview.
Refresh updates association only, never the scientific basis of existing writing
or review authority. A missing paper still leaves saved writing available.
Location input is temporary control state, not a new research draft or key flow.

U4 first connects a researcher-selected synthetic paper to the existing graph.
Compare another populated example with an explicit setup preview containing only
the person's title, working thesis and first research question: choose the latter.
The initial argument has no observations, runs, AI prose or completed judgment.
Preview the paper, marked source and separate private workspace before creation;
cancel and dry-run write nothing. An explicitly requested first candidate episode
supplies the existing authoring context without claiming scientific acceptance.
Open the same encrypted project through its typed association store and retain
that association on later terminal saves. Missing/changed source is visible while
saved writing remains available; opening does not relocate, refresh or reconcile
it. Reuse named manual actions and writing recovery. Keep this entry under the
synthetic demo command until public lifecycle and real-use gates are met.
For an already saved project with no episode, compare implicit automatic opening
with asking for the person's unresolved question: choose explicit question,
preview, revise/cancel and start. Reuse the retained thesis and association;
starting adds one candidate episode, with no evidence or completed judgment.
The prompt discloses that writing is not saved until start. Reopen must bypass
this prompt after a successful start. Keep file status visible even when source
is unavailable, and refuse store conflicts without replacing existing work.

U3 compares copying wording onto a new review with restoring the original
recorded/detached scientific history and exact supplied bytes: choose the latter.
An encrypted wording draft retains its human text/reason, contribution history,
separate unfinished wording/source-path input and original parent identity.
Opening saved work performs no file access and restores no current review.
Use a named Resume manuscript drafts picker alongside W's recorded work; do not
insert detached candidates into recorded obligations. Source/context divergence
keeps earlier writing readable/editable and blocks fresh review under that old
basis. A restored detached parent remains historical, so a new scientific review
opens separate wording. Manual checkpoints stay narrow. Manuscript review answers
and live branch/merge reviews remain session-only and disclosed; U3 preserves
wording rather than promising whole-session custody. Check byte-exact CRLF/NFD
source, empty unfinished edits, source disappearance, malformed owners/history,
old formats, narrow screens and actual terminal interruption/reopen. Reuse exact
source bytes by digest across drafts; retain all-or-nothing save failure when
distinct content exceeds the bound. The picker offers d then Enter to explicitly
discard one draft, preserving its scientific cause and source file. Never silently
save only a subset. Source-only browsing is not saved writing.

U2 restores U's unfinished scientific fields and review answers. Store original
source-prefix bindings and the typed original record or judgment/selection inputs,
not just text rebound to the current graph, and never restore an expiring seal.
The existing U picker names encrypted recovery; Ctrl+O compares original/current
science, authored baseline and judgment/AI origin without losing the editor.
Reading alone creates no pending work. Empty edits stay distinct from kept fields.
After restore an answer needs explicit fresh scope review before completion.
Opening the new editor keeps the earlier basis; changed answer or field context
requires an explicit comparison/basis choice before reuse. Source
inspection is read-only, keeps cursor/undo and pauses hidden actions on tiny
terminals. Discard removes only the chosen unfinished text and its basis.
Malformed owner/source/field/selection inputs fail before workspace installation;
save failure retains live writing. Default/manual-checkpoint behavior remains
session-only. Manuscript/branch review editors remain outside U2.

The U1 retention increment now covers W's conditional explanation topics. Restore
partial kept writing, explicit reuse of the original rationale and separate
unfinished text, including active source-inspection buffers and empty deletion.
Compare copying explanation text into a new current-context answer with restoring
the owned explanation service snapshot and its original source prefix: choose the
latter. It reconstructs original/current/writing-basis science and retained source
AI without inventing a new human explanation or declaring comprehension. Keep W
as the entry, preserve the selected topic, and label encrypted recovery versus
ordinary session-only use. A saved explanation remains open; U2 separately
retains scientific review input, while U3 separately retains manuscript wording. Bind
all topics/owners before installing a restored workspace; old files still read.


The T5b recovery increment extends the existing encrypted device checkpoint to
manual argument drafts and provisional results. Compare restoring field text
against today's source with restoring its original source-history prefix: choose
the latter. Original/current comparison remains meaningful after source changes;
reopening never silently rebinds a candidate or confirms a result. The v3 work
envelope adds a closed authoring-workspace/v2, retaining old v1/v2 readers.
Store history once and reconstruct original source/contributions from checked
prefix and query-digest references, avoiding copied projections as authority.

Retain kept and unfinished candidate bodies separately, stable IDs/aliases,
selection/omission, revisions, original owners, independent result numbering and
partial measurement/judgment fields. Live editor text becomes unfinished input,
including empty deletions, without keeping it into the graph. Restore no request,
consent or current scientific review. Continue through named Open argument drafts,
Return to authored work and Resume result drafts actions. The existing graph,
forms and source comparison remain the working surfaces; add no second Save form.

The status now identifies writing recovery, including conditional explanations;
manuscript review answers and completed scientific reviews remain specifically excluded on quit.
U2 additionally retains unfinished scientific fields and review answers. Default and --draft-file sessions keep their
existing narrower retention. Unknown/malformed formats and oversize writing fail
without truncation or a fallback store. Native save failures remain visibly
unconfirmed, including uncertain post-replacement outcomes. The Mac-only synthetic
path does not establish experiment-server custody or full T5b. The
[workflow](../development/workflow.md#encrypted-terminal-judgment-recovery)
owns commands, timing, supported versions and remaining exclusions.


The next T2a slice connects manual interpretation construction to the existing
candidate graph. Compare silently filling an interpretation from the selected
observation with a blank statement and explicit observation picker: choose the
latter. Recorded observations keep their current status and identity; choosing
none leaves the interpretation unlinked rather than inventing evidence. The
existing one-interpretation-per-episode/ref limit is visible before creation.
An occupied source directs to scientific editing, while an existing kept or
unfinished candidate directs to its argument drafts. A previous episode's
interpretation is not overwritten to make room for new work.

The researcher may reuse a kept new interpretation as the owning judgment
through a full comparison and explicit confirmation. Preserve the reason and
existing judgment contributions; changed work/source invalidates the comparison.
Existing source interpretations cannot enter through this manual reuse path,
and unfinished candidate edits must be kept or resolved first. The candidate's
observation links describe what is interpreted; scientific support/challenge/
qualification still requires an explicit claim connection and rationale. Exact
review continues to require the same interpretation/judgment text and a complete
reason. Quiet construction itself needs neither completed reasoning nor AI.
Exercise blank/partial entry, multi-selection/cancel, wide/narrow/tiny screens,
unchanged evidence, dependency selection, retained AI, stale work and real PTY.
This slice changes no schema or storage; candidate writing remains session-only.
Keep observation status ahead of the excerpt on narrow pickers, with a full
read-only source view that returns to the same choices. Agent inspection caught
status lost after a long statement; test that status at 48 columns explicitly.
Preserve independent work rather than imposing a global lock on exploratory
interpretations: the domain bounds each projected episode/ref argument, not
all alternative working drafts. Omitted kept interpretation text still follows
the existing judgment-equality rule; explain reuse/edit/unkeep without changing
that domain contract. All reuse fields must fit the judgment's existing limits
before replacing text, including a previously oversized human reason.

The first T2b slice now opens provisional result capture from an existing recorded subject.
Compare a long mandatory completed-result form with incremental capture beside
that subject: choose incremental capture, permitting source, observation and
judgment fields to remain blank. Run and artifact references are text only;
missing conditions or measurement values are never inferred from the selected
node. The application owns bounded session drafts with distinct identities,
original episode/ref/node and source snapshot, plus separate kept/unfinished
fields. A result's tentative judgment stays with that capture; it does not
replace the existing node's judgment or join its scientific review without the
missing evidence-confirmation integration. Original source AI remains readable
as source history, with no new proposal or assertion that typing proves human
understanding. This is a provisional entry surface, not a second canonical log.

Name the entry and return actions, show the original subject during editing,
and keep full result/source context reachable without losing cursor or undo.
At narrow widths use a compact subject strip and a dedicated editor. Kept and
unfinished text, source changes and session-only retention remain explicit.
List retained results across contexts by subject and original episode/ref;
resuming changes neither the graph's selected work nor its scientific state.
Deletion requires a named confirmation. Missing source leaves writing readable.
No checkpoint, provider context, graph edge, accepted run/observation, review or
pending Debt is created from these fields. Empty-project intake and an actual
source/confirmation-to-argument transition remain the owning service work.
The terminal workflow owns controls and retention; the ExecPlan records checks.

The T4 wording increment connects completed selected-merge review to deliberate
wording review in the same graph context. Compare routing through the global W
list with opening the exact detached candidate's manuscript consequence: choose
the latter, because installing a candidate merely to expose pending work would
misstate acceptance. The existing merge/manuscript services own scientific
selection, source bytes, provenance and expiration. The researcher explicitly
opens wording, writes replacement text and can reuse the displayed judgment
reason without retyping it. Wording stays blank until authored; judgment text
is not automatically a manuscript sentence. Keep judgment/reason visible during
writing and allow full basis inspection without losing editor state.

Bind each wording draft to its exact parent review and original work. Parent
edit/reselection/expiry or source changes revoke child review, preserving text.
A changed parent creates a separately labeled draft only on explicit action;
earlier drafts remain reachable from the same work, with their original AI and
scientific basis. Do not silently transfer wording or provenance to a different
selection. Return restores the original merge/graph context. All candidate work
remains session-only and outside W's recorded obligations and manual checkpoints.
Check authored and recorded/manual/AI routes, reason reuse, old-draft access,
stale-parent/file rejection, narrow/contextual writing, actual PTY input and
unchanged workspace/history/source bytes. Protected manuscript application and
cross-basis draft transfer remain separate service/custody work. The synthetic
connection is implemented; its [terminal controls](../development/workflow.md#terminal-paper-prototype)
and acceptance case own current behavior. Actual check results and remaining
work belong to the execution plan.

The 2026-09-28 T4 increment returns from a conditional understanding item to its
original judgment and current science, using `PaperUnderstandingSession`.
Comparing another retrospective form with a topic-focused reader/editor selects
the latter so one to three existing causal topics retain the original
reason as an explicit reusable reference. W remains the return entry; manual
graph writing never acquires a mandatory explanation step. Read original/current
science, the draft's earlier basis and AI contributions through named views;
keep topic/source context visible while editing and offer complete source
inspection without losing cursor/undo state. Blank and partial text is valid.
Kept explanation and cancelled editor text stay separate, bound to the work
and topic rather than the graph's currently selected judgment. Source changes
retain both and require an explicit displayed-basis refresh; editing cannot
silently rebind. Leave-open retains session work and resolves nothing.
This surface adds no AI grades, provider call, accepted Debt mapping or closure
button: v3 conditional work lacks the accepted cause authority needed by the
new closure contract. Existing manual checkpoints exclude this explanation,
and normal quit discloses its loss. Verify two distinct work items, rationale
reuse, evidence-only changes, stale refresh, Unicode/limits, narrow/tiny input,
graph return and actual terminal editing. Human comprehension and durable
resumption remain separate gates. This bounded increment is now implemented;
the [terminal workflow](../development/workflow.md#terminal-paper-prototype)
owns its controls and limits. Wide/narrow source reading preserves the active
editor; unavailable source permits manual continuation on explicitly retained
context while blocking a new binding. UTF-8 limits and distinct contribution
origins remain readable. The execution plan owns actual verification and the
remaining coherent manuscript/accepted-closure integrations.

The 2026-09-28 T3b increment explicitly links an existing judgment to several
source nodes in the same episode/ref. Comparing a new independent work ID with
reuse of the existing owner selects explicit reuse for this bounded increment because
the existing session already has a stable draft ID, contribution chain and
candidate/review lifecycle. A new identity would require migrating those
objects without improving this first reuse action. The original episode/ref/node
remains the immutable owner; linked nodes are working references, not scientific
edges or selected amendments. At most 16 source nodes may link to a work.
The user chooses which existing judgment to use at a linked node, or returns
to that node's separate judgment. Existing text, unfinished fields and AI history
are never merged or copied. Linking shows the chosen owner and preserved
alternative work before applying; Esc changes no association. Adding references
activates only newly linked nodes, retaining choices at existing references.
Labels identify linked nodes currently showing a different judgment. Selecting
already-linked or separate manual work allocates no review session; a new
multi-node work still obeys the existing capacity bound. Link membership
changes invalidate the owner's scientific/branch reviews while preserving text
and pending proposals. Episode/ref changes cannot select foreign work. Notes
stay attached to the viewed node; judgment editors show both their owner and
the viewed source. Existing manual checkpoints retain text at the original
owner, but link choices remain session-only and quit discloses their loss.
Validation must cover shared evidence and two claims, an independent judgment,
AI edits, incomplete writing, stale source, invalid links/capacity, return and
restart without restored links or authority. This does not supply T2b's missing
initialization/evidence adapter or T5b's durable work recovery.

The follow-up-plan authoring slice lets a researcher with an unresolved result or claim
plan a follow-up without first completing a judgment. Reuse the existing
candidate form, explicitly choose the target claim, and leave objective,
conditions and metric name/definition/unit/comparison blank for the researcher.
Compared with copying the nearest experiment's fields, blank entry avoids
silently carrying a measurement or baseline into a different question. Planned
status is fixed and visible; it never means execution or a measured result.
Keep unfinished fields editable, label the draft graph's plan and tests link,
and use existing selection/dependency review. Failure means lost input, an
invented scientific field, a misleading execution state or implicit ownership
change. This slice retains the session-only boundary and existing plan editing
policy; project/result intake and scenarios on new draft plans remain later work.

The 2026-09-28 authoring increment implements bounded claim/connection/plan forms and a
separate draft graph before a complete judgment exists. Capture the original
episode/ref/node as the owner when entering authoring; viewing a candidate or
another source never silently changes that owner. A named authored-work picker
returns to it. Compare this interim reuse of node-bound work with a new linked
judgment identity: reuse preserves existing drafts/recovery without an implicit
migration; the T3b references above extend that choice. The initial graph
shows all valid authored changes, including those omitted from final review,
with explicit draft labels. Invalid/incomplete text stays editable with its
validation error; it cannot be shown as a valid scientific graph. Removal names
dependent candidates separately from omission. No candidate becomes a checkpoint
target or accepted observation. Keyboard/service checks cover new claim/link
creation, invalid partial text, owner return, review expiry and invalidation,
source refresh, checkpoint exclusion and an actual PTY Korean-paste journey.
This is synthetic interaction evidence; durable recovery, live SSH and human
understanding remain unverified.

| Ownership option | Result for this increment |
|---|---|
| Explicitly reuse existing episode/ref/node work | Selected interim boundary. Keeps current judgment/provenance/checkpoint identities compatible. Candidate revision/source binding lives outside review snapshots; a named picker returns to the owner. New candidate nodes expose inspection, not independent judgments. |
| Introduce an independent multi-node work ID | Not needed for the bounded T3b reference links above. It would require identity and recovery migration; silently merging old node drafts would erase distinct work. Durable linked recovery remains T5b. |

The form separates structural parentage from a scientific connection. Choose
level/endpoints/type by name, write the scientific text, then keep the candidate.
Incomplete work has a visible validation error and remains repairable. The
draft graph shows all valid kept candidates; final comparison still shows
selected dependency closure. Inspecting a draft cannot initiate AI or create a
new checkpoint target. Plans show their complete authored measurement and explicit
unrun status; new source intake remains unavailable. The
[terminal workflow](../development/workflow.md#terminal-paper-prototype) owns
controls and retention details.

Recovery contract for this initial slice: keep candidate/unfinished input in
the running work, bounded by 16 existing-node sessions and 64 candidate/form
identities per work. Preserve old note/judgment checkpoint format unchanged;
candidate fields are excluded and normal quit discloses their loss. Changed
history retains fields and invalidates review, with explicit source refresh;
missing owner or capacity refuses new work without eviction. T5b must restore
exact project/history/work identities, candidate IDs/revisions/selection,
separate unfinished forms and contribution lineage under a versioned custody
adapter. Reopening must never restore review authority. This is the interim
boundary, not completion of durable linked-work recovery.

Implementation planning date: 2026-09-27. This translates the preceding audit
into a proposed interaction composition. The
[TUI implementation sequence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#tui-result-to-judgment-implementation-sequence)
owns milestones, dependencies and completion evidence; this section owns the
presentation and writing choices to test. None of the new controls or working
draft relationships below is implemented by documenting them.

Preserve the existing spatial graph, compact cards, semantic palette, full
relationship names, shared-evidence identity, selection emphasis, view settings
and reliable back behavior. At wide sizes, place the active writing workspace
beside the graph. At narrow sizes, keep a compact selected-subject/source strip
above the workspace and return to the same map position. Do not substitute a
left-hand tab list for the user's chosen visual graph or force two narrow panes.
Source context must also remain visible while the judgment editor is open.
Expanding/collapsing the source from the editor preserves text, cursor and undo
state. Recorded observation content and a source reference are distinct from
an artifact that was actually opened or verified. Claims and plans show their
own content/scope/status with named evidence/link follow actions; absence is
explicit, not replaced with an inferred supporting source.

Apply the [human-led construction criteria](#human-led-construction-and-understanding-review)
throughout. Manual research actions are the primary entry surface; AI is
explicit contextual assistance. The working composition has three stable regions:

- A context strip names project, episode, reasoning branch and the active work's
  actual persistence/review state. Session retention, durable draft save and
  scientific acceptance must not share an ambiguous Saved label.
- The graph shows current argument and explicitly marked proposed changes.
  An unresolved observation or AI suggestion has a text state as well as visual
  treatment; it cannot look like confirmed evidence. Distinguish structural
  parentage from scientific support/challenge/qualification.
- The contextual workspace starts with the selected source content/conditions,
  then the active human judgment and reason, then proposed claim/manuscript
  consequences. Optional AI critique and provenance expand in this context.
  A compact named action list exposes relevant actions; existing shortcuts
  remain accelerators. A general command palette is not required.

There are two entry paths into the same workspace: start from an unresolved
result, or start from an existing claim and attach a result. A minimal paper
question/working thesis is sufficient; a completed interpretation or fully
drawn graph is never an onboarding prerequisite. An empty project offers these
actions instead of showing a fabricated argument. Project/source selection and
draft creation must disclose unavailable storage capabilities honestly.
AI-off capability is visible before a request flow opens; it never blocks
manual writing or implies that an offline example is a live provider.

Creation is expressed as add a claim/subclaim, attach a result and its source,
record an alternative interpretation, plan a follow-up experiment, or connect
existing records with a named scientific relationship and rationale. Preview
the new/changed objects before staging them. Adding another use of an existing
observation reuses its identity. Source observations and completed runs retain
their separate evidence-confirmation path; a free-form note cannot become
evidence merely by changing its card type.
Candidate work needs a stable, visible owner and a draft graph independent of
the completed-judgment review. Editing a judgment or expiring its review must
not erase authored candidates. Removing a candidate is distinct from omitting
it in review. The [delivery sequence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#delivery-order-and-first-implementation-slice)
owns the interim candidate editing/identity boundary before full linked-work
and recovery support is available.

The preferred draft hypothesis is one explicitly created working judgment with
several related node references. Following a linked node keeps that active work
visible with its scope named. Starting a distinct judgment creates distinct work;
an episode may contain several judgments. Existing node-bound drafts remain
separate until the researcher explicitly chooses which to reuse/link. No silent
concatenation, AI-origin flattening or blanket episode-wide replacement is
permitted. The bounded T3b comparison above selects explicit references to an
existing owner; versioned durable recovery remains separate. Node notes remain
independently editable. Without an explicit link/choice, navigation continues
to select each node's own judgment. No automatic episode-wide pinning is added.

Reuse the judgment and rationale in exact change review; request additional
explanation only when required information is missing. Manuscript wording remains
a deliberate edit with a source-bound diff, while the existing judgment is
available as its basis without retyping. Graph comparison, explanation review,
acceptance, manuscript application and verification remain distinct phases.

After capabilities are connected, resume should identify the active work,
what changed since review, and the next unfinished consequence. U remains local
unfinished writing; W remains scientific/wording work. Present clearly named
entry actions for both without treating conditional work as accepted debt.
Unavailable source, expired review, interrupted save and provider failure retain
authored text and offer the relevant safe next action.

### UI/UX baseline and next exploration

The [UI/UX harness](../development/uiux-harness.md) owns the working method;
the [YC assessment](../references/yc-design-with-ai.md) owns its external basis.
The first application now includes a runnable synthetic terminal prototype,
not a chosen final composition or usable protected product. ADR 0011 owns the
paper argument direction; [ADR 0012](../architecture/decisions/0012-terminal-research-workspace.md)
adapts its presentation to the user's terminal workflow.

Reference-selection ownership, 2026-09-23: the user will personally inspect and
choose the references. The assistant supplies candidates and explains their
potential relevance; a recommendation is not an adopted design direction.
The user subsequently responded positively to the proposed reference qualities,
explicitly naming [Heptabase's board](https://heptabase.com/),
[Kialo's hierarchy](https://www.kialo.com/tour),
[VISAR's argument/writing interface](https://arxiv.org/abs/2304.07810) and
[Obsidian Canvas](https://obsidian.md/canvas). Retain these as supported
inspirations; their combination and exact visual treatment remain unselected.

Medium preference confirmed, 2026-09-23: the user wants to perform most work
inside an actual terminal. Use this as the next design constraint; a graphical
app with command-like styling does not satisfy it. Explore a persistent,
keyboard-operated TUI for claim navigation, evidence inspection, judgment
drafting and manuscript-change review. A separate local graph or rich-document
viewer remains an optional proposal, not a selected dependency for that loop.
The user then clarified the purpose: run ClaimBranch in the experiment host's
server/SSH terminal, alongside the shell used for experiments. The prototype
therefore needs no browser, graphical login or forwarded web port. Standard
Python curses is the bounded prototype renderer; this does not select a
production framework or establish protected server deployment.

Preserve the scientific outcomes behind ADR 0011 and PG-1–PG-5: readable
arguments, shared-evidence identity, typed relationships and contextual impact.
A hierarchy alone must not hide cross-claim connections. Product and validation
sources now express focus/navigation equivalents under ADR 0012.
This preference does not itself prove equivalent
usability or waive any scientific, authority or release gate.

Feasibility basis, 2026-09-23: the
[paper query/scenario service](../../claimbranch/application/paper_service.py)
is independent of layout; adding a terminal adapter need not duplicate scientific
state. The runnable projection uses this service; protected writes remain absent.
[Lazygit](https://github.com/jesseduffield/lazygit) and
[Posting](https://posting.sh/) provide public terminal interaction references;
[Textual](https://textual.textualize.io/) documents Python terminal UI support.
The prototype uses the existing Python runtime without installing Textual or
other packages. Model/CLI and actual-PTY tests cover shared evidence, scenario
immutability, branch-bound drafts, layout/resize, injected Korean text/paste and
shell-mode restoration. Physical IME use, live Linux/SSH, screen readers and
human graph comprehension remain untested; the ExecPlan owns run evidence.

Baseline inspected on 2026-09-22 in the running app at 1440 and 390 pixels:

| Evidence | Design implication |
|---|---|
| The [page](../../claimbranch/application/web/index.html) opens with the episode introduction and evidence cards; the graph is a context toggle | Test a paper argument opening where the researcher can orient before entering a judgment |
| The [projection](../../claimbranch/application/graph.py) contains one claim, eight nodes and twelve relationships, ordered from run to observations | Paper-wide reading needs a separately defined example; changing coordinates cannot create missing thesis/shared-evidence semantics |
| Visible captions omit the comparison behind “expected damage order”; the original source lacks a damage metric | Test self-contained scientific wording and honest missing-definition states before polishing node surfaces |
| The [graph interaction](../../claimbranch/application/web/graph.js) emphasizes incident edges on selection; related-node hover enlargement and scenarios are absent | Compare relationship emphasis and possible-result inspection against the graph oracles |
| At narrow width the nodes stack and relationship navigation follows below; judgment and manuscript review remain later sections | Test whether context can stay identifiable while reading and editing, rather than requiring a long round trip |

These are observed implementation gaps and design questions, not measured
human-usability outcomes. Existing provenance, exact manuscript candidates,
blank entry and preserved drafts remain useful behavior to carry forward.
The [ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
records browser results and the reload-related test-driver failure.

**First comparison task.** A researcher encountering an unexpected result
should locate the paper's claim, inspect its basis, explore what a follow-up
could change, and form one judgment with its manuscript consequence in view.
Use the separately identified synthetic paper example required by the
[graph oracles](../validation/cases/saturation.md#102-paper-argument-workspace-oracles).
It must define its terms and measurements and include both direct-evidence and
subclaim paths, shared evidence and an unrun experiment. Since the baseline,
the [paper model extension](2026-08-03-domain-model.md#paper-argument-extension-under-review)
has added synthetic paper fixtures and a query/scenario service. Reuse those
inputs; the two terminal variations below now consume that same example.

The prototype implements two actual-terminal candidates, switchable with `v`.
Their usability remains a design hypothesis:

| Candidate to explore | Question it tests |
|---|---|
| Two panes: collapsible thesis/claim outline and a wide contextual inspector, with explicit related-item and impact views | Can long Korean/English evidence and judgments remain readable while shared-evidence paths are easy to follow and return from? |
| Three panes: argument path, selected node with typed adjacent relationships, and evidence/judgment/manuscript detail | Does keeping relationships visible reduce navigation without making the scientific text too narrow? |

Both keep the selected reasoning branch and draft/proposal/hypothetical state
visible. Use the same fixture to find evidence, navigate to another claim using
that evidence, preview affected/unchanged paths and inspect a manuscript
connection. The fixture contains no manuscript source; a session draft diff
is an argument-text comparison, not a file patch. Arrow/Tab navigation, Enter
to inspect, Escape to return and search are implemented comparison controls.
Returning restores selection and context;
ordinary navigation never authorizes a scientific or manuscript operation.
At smaller terminal sizes, collapse a pane while preserving context and text.
The PTY checks exercise injected Korean text, paste, wrapping and resize.
Physical Korean composition still needs a human terminal observation.

Prototype review: at 80 columns the two-pane view gives the selected scientific
text more reading room; at 132 columns the three-pane view keeps typed
relationships visible but truncates more adjacent-node previews. Both expose
full content on selection. These are observed layout trade-offs, not a measured
human-usability preference. The [launch guide](../development/workflow.md#terminal-paper-prototype)
owns commands, keys, pane thresholds, volatility and missing capabilities.

Readability iteration, 2026-09-23: the user's first visual review found the
prototype too dense and difficult to read, citing color, line spacing and
whitespace in the supported references. The revised prototype keeps the same source
and keyboard journey, and tests quieter panel surfaces, spaced node previews,
visible hierarchy connectors, semantic color plus text, and a bounded reading
measure. Full relationship direction/rationale remains inspectable with `r`
without repeating every adjacent statement in the initial reading pane.
Comfortable and compact density are presentation alternatives over identical
content; neither changes scientific meaning. The terminal owns font metrics;
the application controls cell padding and blank rows between items/sections.
Failure means clipped scientific content cannot be reached, color becomes the
only state cue, or density/layout changes lose selection, scenario or drafts.

Current presentation choices: dark canvas and slightly lighter panels, violet
claims, cyan observations, amber plans, blue experiment records, rose writing
anchors, green support and rose challenge labels. Type words and arrows remain
visible without color. A selection uses both a filled surface and `›`; `▸`
marks pane focus. Comfortable spacing separates cards and section headings;
compact spacing keeps more context visible. The reader is limited to 72 terminal
cells, with centered side padding when space permits. Initial node reading
shows scientific content and a connection count; the relation reader exposes
the complete recorded endpoints and rationale on selection.

Observed on macOS Terminal at 144 × 42: colored type labels, distinct panel
surfaces and separated previews render in the real application. The first
inspection exposed inherited `NO_COLOR=1`, so the color preview explicitly
unsets it for that process; the application still respects the environment by
default. PTY checks cover smaller viewports and all three color capabilities.
This is rendering/input evidence, not confirmation that the revised design is
easy to understand. The user's subsequent screenshot review supports this
visual treatment as the baseline; it is not a complete comprehension study.

Graph hierarchy iteration, 2026-09-23: the user supported the revised visual
treatment but found the flat evidence/experiment rows beside the thesis obscured
the graph. Preserve the palette and spacing; make the thesis the normal outline
root and project the recorded claim, evidence, experiment and follow-up links
beneath it. Label each connection with its exact type and direction. Parallel
structural/scientific edges stay distinct; placement alone asserts no support.
Repeated evidence/records are references to the same identity, not copies.
The first argument path opens initially; other branches can unfold on demand.
Selection and return must distinguish occurrences without duplicating drafts.
Unconnected records must be identified explicitly rather than attached through
invented edges. Validate all relation keys when unfolded, shared identities,
search ancestry, fold/navigation continuity and the unchanged source manifest.

Implemented projection: each pair's recorded edge types appear on its connector,
with `↑` for child-to-parent and `↓` for parent-to-child. This orientation is
independent of the reading path. A repeated node becomes a finite `↪`
reference; it cannot create another observation or branch-bound draft. The
first occurrence can unfold its adjacent basis and records, and `g`/`Esc`
navigate between occurrences. The two-pane outline has more width for these
labels; long narrow/deep paths wrap edges and shorten the displayed indent,
while the selected path and complete endpoints remain inspectable. Search
shows matching ancestors and keeps them visibly open without changing stored
fold state. No service, schema, fixture or scientific relation was changed.

Panel spacing refinement, 2026-09-23: retain the user-supported composition and
give its gray surfaces room inside the black canvas. At 100 columns and above,
outer side gutters grow from one to three cells and the inter-panel gap grows
from two to three. Panels at least 34 cells wide gain two cells of inner side
padding. At 30 rows and above, add a blank gray row above and below the panel
content and another black row above and below the panel group. Smaller
viewports reclaim those extra cells/rows. Selection, edge labels and footers
remain inside the padded surface; content stays reachable through existing
navigation and scrolling. This is a presentation adjustment, not a graph or
interaction-contract change.

Shared-evidence iteration, 2026-09-23 (user-selected and implemented in the
synthetic TUI): the
researcher should be able to identify every claim using one observation and
inspect each relationship's own rationale. The current example's `obs-1`
supports both `claim-pruning-detail` and `claim-comparison`; a `shared` badge
alone does not communicate those destinations. Keep one evidence identity and
show a compact count of distinct directly connected claims, followed on
selection by a named destination list with exact relation types and direction.
Distinguish `supports`, `challenges` and other scientific relations; never count
tree occurrences, `produced` or structural links as supported claims. Repeated
outline appearances should use the same short evidence label and reference
mark; highlight visible appearances together without expanding the entire
outline. Selecting a destination should inspect/follow its specific edge, with
return to the same occurrence. Color supplements labels and reference marks.

Two task-based reading views share the same graph:

| View | Starting point and question |
|---|---|
| Argument | Default thesis outline: what claims and evidence make up this paper's reasoning? |
| Evidence uses | Selected observation first: which claims use this result, and through which recorded relations? |

In the evidence view, present a local fan-out to direct claim destinations,
with experiment/source context separately reachable and further argument paths
expandable. Label indirect paths as paths, never as new direct support. An
explicit view switch and visible focus/path should preserve selection, branch,
draft and return context; they do not reparent stored nodes or change edge
direction. Prefer testing these two purposeful views before adding an arbitrary
root-setting menu. Their usability remains to be evaluated with the researcher.
Failure would be mistaking a repeated
appearance for another observation, missing a second use, conflating structural
links with support, or losing orientation when returning to the argument.

Implemented presentation: the top selector exposes `1 Argument` and `2 Evidence
uses`, with `[`/`]` to change the focused observation. Evidence gets a stable
session label such as `E1 · 2 claims`; its READ pane names every direct claim
use and retains each scientific type. `u` selects a use, `Tab` reads that edge's
full rationale, and `Enter` follows it; `r` includes source/experiment links.
The evidence outline starts with direct claims folded at their further paths.
Following a record outside that projection returns to its argument location;
navigation history restores the evidence view, occurrence, folds and pane.
The same draft and hypothetical state survive view changes. Visible repeated
evidence uses `↔` when another occurrence is selected and `↪` for references;
text cues survive monochrome. No scientific record or relation was changed.
Actual macOS Terminal inspection at 144 × 46 shows both named destinations and
their `supports` labels together with the shared observation. PTY checks cover
view switching, typed-edge follow/return, Korean draft retention and resize;
they do not establish a human-comprehension or Linux/SSH result.

Spatial terminal graph iteration, 2026-09-23: the user requested visible nodes
and edges instead of relying on the outline. The default navigation now draws
one box per record, with orthogonal lines and arrowheads following the recorded
source/target direction. Shared evidence has several connections from one box;
parallel scientific/structural types remain distinct. Existing Argument and
Evidence uses views determine the graph's scope. The graph projects all records
and paths in that scope independently of the outline's fold state, rather than
copying its repeated occurrences into duplicate graph nodes.

Compare this canvas with the retained outline using `o`. The focused graph uses
the full panel; `Enter` opens node reading and `r` exposes exact edge selection
and rationale. `f` returns to the full graph. Arrow keys select spatially,
`j`/`k` visit every node and `HJKL` pans when the terminal cannot show the whole
scene. Selection brings its card into view; very short viewports prioritize the
card's identity before its clipped body. The approved outer gutters and gray
panel padding remain. Node text comes from the source, with full statements in
the reader; these are previews, not newly generated scientific summaries.

Connected cards show full relationship phrases relative to the selected node;
selecting an individual relation emphasizes its exact path. Other connections
stay quiet. The relationship-text iteration below replaces the earlier crossing X marks with drawing priority
without creating a node or relation. The footer also names incident
types/directions. This cell-based layout uses keyboard navigation rather than
pixel positioning or dragging. No new package, graphical server or accepted
state is introduced. Failures include duplicated shared evidence, invented
connections, reversed arrows, routes through node boxes, unreachable text, or
loss of drafts/view context. Graph geometry and PTY journeys check those
mechanics; reader comprehension and large real-paper layouts remain open.
Actual Mac Terminal inspection at 144 × 46 shows the evidence-to-claims fan-out
and subsequent argument paths, with the same color/spacing treatment.

Neighborhood focus iteration, 2026-09-23: the user chose the visual graph and
requested brighter connected nodes and edges with quieter surrounding context.
The selected box keeps its selection surface; direct neighbors retain their
type colors and readable body text. Other cards use muted text and borders on
the same panel surface. Only incident edges brighten, not every edge between
neighbors or the transitive path to the thesis. Exact relation inspection
narrows emphasis to that edge and its endpoints; a relation outside the current
lens leaves the selected node visible and names the view limitation. Focus
changes no layout, record, draft or scenario. Monochrome retains dim attributes,
the selection marker, directed arrows and explicit relationship text.

The observable task is to select E1 and distinguish its two claim uses plus
the producing run and interpretation from nearby E2 and indirect ancestors.
Mac Terminal inspection at 156 × 48 shows this separation while retaining the
whole example. Automated checks cover direct versus indirect scope, parallel
edge identity, an out-of-view edge, visible dimmed card text and stable geometry.
This verifies the presentation mechanics, not a human comprehension result.

#### Node reading panel reference study

The same request asks what prose, personal writing, AI opinions and connected
context should occupy the right panel. The following is a proposed next slice;
the neighborhood emphasis above is implemented. The selected references were
revisited on 2026-09-23 through their official pages/help, Heptabase's published
board/backlink screenshots and the VISAR paper's interface descriptions
(sections 4.3.2–4.3.3). Reference products were not exercised in an account.

| Inspected reference | Relevant pattern | Proposed ClaimBranch adaptation |
|---|---|---|
| [Heptabase board and editor](https://heptabase.com/) | The published board image keeps a large reading pane beside the card map; the backlink example includes surrounding text | Give the selected node a spacious prose page, with readable context beside its graph and excerpts explaining its connections |
| [Obsidian Canvas](https://obsidian.md/help/plugins/canvas) | Note/text cards support editing, and directed connections have labels and source/target navigation | Let a short graph card open its full content and personal writing; label and follow existing typed edges. Do not equate an arbitrary note link with scientific support |
| [Kialo tour](https://www.kialo.com/tour) | Claims retain one identity when linked in multiple places; comments are separate from the argument | Show a shared observation once, with a separate explanation for each claim use; keep questions and personal notes distinguishable from recorded claims/results |
| [VISAR, sections 4.3.2–4.3.3](https://arxiv.org/pdf/2304.07810) | Text and visual outlines highlight corresponding items; selected text can request counterarguments, possible fallacies or evidence suggestions | Keep the graph selection tied to the reading heading, and offer focused AI critique on demand. Generated evidence suggestions never become recorded observations |

Design recommendation: use a node page with **Content**, **Connections** and
**AI suggestions** as secondary reading modes. Content is the default, with
the researcher's editable note close to the source paragraph, rather than
requiring a separate note tab before writing. This is an application of the
references to the research task, not a claim that they prescribe this layout.
Compared with a single long inspector, the three modes keep AI/history from
pushing the scientific subject below the fold. Compared with a separate chat
pane, scoped suggestions preserve which node or edge is being discussed.

- **Content:** lead with the full proposition, experimental question or result.
  A claim presents its statement, scope and explanation. An observation
  presents the measured value, unit, comparison, conditions and source. A run
  presents the actual experiment description, method and recorded outcomes;
  a plan presents the question and still-unrun test. Show command/log/artifact
  references only when the source supplies them. Metadata and provenance can
  be disclosed below the reading, rather than displacing it.
- **My note, within Content:** optional free writing for interpretation,
  uncertainty, questions and a next action. Keep it with the current node and
  reasoning context, reuse an existing judgment/reason when entering review,
  and preserve it across focus changes. Editing a draft does not overwrite an
  accepted observation or apply manuscript prose. A note preview can remain
  beside the source, with editing using the existing terminal editor initially.
- **Connections:** show the other node's readable statement, exact type and
  direction, then the recorded reason for that particular connection. Group
  scientific uses separately from experiment/source links. For E1, both claim
  destinations need their own rationale; a generic “shared” paragraph cannot
  explain two different uses. Missing rationale stays explicit. Choosing a row
  focuses that exact edge; following it keeps a return path to this note.
- **AI suggestions:** on explicit request, help identify a counterargument,
  a missing control, a scope limitation or a possible follow-up experiment.
  Keep referenced records separate from inferred suggestions. Bind the result
  to its requested node/edge and source snapshot; do not silently retarget it
  when the selection changes. Taking text into a human draft preserves the
  original suggestion and human edits. Asking AI is optional and must not
  overwrite an unfinished note or delay manual reading/writing.

The TUI now supplies source reading with an editable personal note, a separate
node/ref-bound manual judgment editor, exact connection rationale and frozen
episode provenance. It does not yet provide the complete proposed reading-mode
composition or node-scoped AI requests.
The existing episode provenance is not an AI opinion about every selected node.
The next prototype should refine Content/My note/Connections over those
existing values, then connect AI/provenance through the candidate episode
adapters with their own scope and authority rules. Persistent notes and
manuscript editing remain separate integration work.

Node-note iteration, 2026-09-23: the user requested editable writing inside the
nodes. Each card now reserves a final `✎` preview line when a note exists; its
source excerpt and full source reader remain available. The reader shows the
complete personal note after the statement/result. `n` opens a single-field
editor in that pane, keeping the graph alongside it where space permits. This
avoids turning free notes into a required Judgment/reason form. Enter adds a
line, Ctrl+S keeps the note for this session, and Esc returns without applying
that edit. A note belongs to one node and branch, including across repeated
outline occurrences, lenses, focus changes and search. The note is not an
accepted source edit, recorded Judgment, AI contribution or manuscript patch.

The accompanying display investigation reproduced oversized cursor addressing
with stale `LINES`/`COLUMNS` and ordinary shortcut execution from an unknown
CSI sequence. An ordinary isolated Enter did not reproduce the reported
overlap on the inspected Mac terminal. The renderer now reconciles actual TTY
size, finishes each frame despite pending input, clears on composition changes,
and parks the hidden cursor at the top rather than at the bottom-right.
`Ctrl+L` explicitly rebuilds a frame. Unknown terminal sequences are consumed
without replaying their bytes as commands. The implementation follows the
[Python curses display/input contract](https://docs.python.org/3.13/library/curses.html);
these repairs do not establish coverage of every terminal host or IME.

Evaluate that next slice by reading one claim and one experiment, writing a
Korean note, following both uses of E1 and returning to the same draft. The
reader must distinguish source content, personal interpretation and an AI
suggestion without relying on color. An AI-disabled journey must retain the
same reading and writing controls. Loss of the note, stale AI shown as current,
fabricated connection explanations, or a second mandatory prose entry fails
the proposed design.

The following graphical compositions were proposed before the medium was
clarified. Retain them as sources of interaction ideas or optional-view studies,
not a change back to a browser as the primary workspace:

| Earlier graphical candidate | Question it tests |
|---|---|
| Continuous left-to-right argument graph with a contextual inspector | Can the paper remain legible as selected scientific detail expands? |
| Progressive argument graph with a persistent path back to the thesis | Can focused work reduce density without hiding sibling claims or shared evidence? |
| Argument graph with an in-place current/possible comparison and anchored manuscript detail | Can a reviewer see affected and unchanged support while retaining the actual state? |

Compare the same scientific content, authority states and tasks in every
candidate. Carry forward the supported reference qualities and use the terminal
references for interaction mechanics. Review the running TUI alternatives and
keep this exploration small; combine useful
elements after comparison and record the reason here. The questions above do
not prescribe new scientific relationships, a graph library, colors, fonts or
an approved scenario vocabulary. Exact semantic/model questions remain in the
domain design; routine presentation choices can proceed as explicit hypotheses.

### TUI responsiveness investigation

The U9 larger-writing increment shares current source-node membership only
within one workspace validation, keyed by exact episode and branch/ref. Compare
notes, manual judgment text, fallback buffers and both unfinished editor kinds
with independent owner checks. Each row and the selected source must still belong
to its own graph; duplicate owners and incorrect editor shapes still refuse the
whole checkpoint. Historical judgment sessions and other writing subsystems
validate separately. The next save starts fresh; no persistent cache, new format
or larger/truncated checkpoint is introduced. Native complete-save evidence and
remaining integrated/host validation belong to the ExecPlan.

The U9 cross-branch prefix increment replays one immutable earlier history per
command count within a review-writing validation. Different branches/episodes
still query separate projections, and each row validates its fingerprint and
restores an independent historical session. Compare interleaved earlier/current
fields and an explanation answer with independent validation; forged branch or
prefix digests and counts outside the saved history refuse the whole restore.
No history or projection persists between validations. Complete native save
timing belongs to the ExecPlan; removing a replay is not evidence that every
mixed workload or host becomes faster.

The U9 original-session increment removes the throwaway workspace lookup
after the existing owner/source checks. Each row constructs its own standard
PaperDraftSession and PaperService, queries its original science independently
and restores only historical writing through restore_session. Compare those
sessions with the earlier workspace construction, including separate brokers
and no revived consent/review. This reduces redundant reading without sharing
mutable sessions or changing the checkpoint contract. The ExecPlan owns the
controlled native timing and regression/review evidence.

The U9 original-source query increment shares scientific-writing queries within one
checkpoint validation, keyed by exact source prefix, episode and branch/ref.
Share the original graph and editable-record lookup; keep each input's owner,
saved fingerprint, session restoration and request/field validation independent.
Earlier prefixes and different refs remain separate. The mapping ends with that
call; the next save queries again. Standalone basis validation remains independent.
This reduces repeated reading while resuming unfinished writing, without a new
checkpoint format, background save or retained source cache. The existing plan
owns controlled complete-save measurements and cross-review/check evidence.

The 2026-09-29 U9 increment profiles encrypted explanation checkpoint preparation.
Its next increment groups explanation drafts by exact source prefix within one
validation, sharing the source service's pending-work projection while retaining
independent text, source/basis checks and detached session state. The 2026-10-03
increment also shares a reconstructed earlier-basis service when several drafts
in that batch retain the same exact prefix. Each work still reconstructs its
own return context and verifies its saved fingerprint; different earlier bases
remain separate. Singular construction, including custom histories, remains
independent. No service or cache survives the batch. Measure the entire synthetic device save separately
from checkpoint preparation; the store portion also performs validation, so it
must not be described as encryption-only time. Repeated saves and restart must
remain byte-equivalent and stale/failed saves remain visible.
Repeatedly reconstructing the same current and retained basis dominated changed
save time. Reuse that reconstruction within one validation when the draft's
bound operation is the last command in the exact current history; still compare
the saved context digest. An older basis reconstructs its exact prefix, shared only within that batch. This
keeps source, text, provenance and stale-save checks unchanged, without a
persistent cache or asynchronous durability promise. The ExecPlan's U9 evidence
records the bounded before/after timing separately from native I/O and host
usability; this improvement is not a claim that all terminal delays are resolved.

The U9 original-review size drill, recorded in the
[ExecPlan findings](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#surprises-discoveries),
identifies repeated original writing-session bytes as a material capacity cost.
The v7 checkpoint increment pools identical canonical original sessions by
verified digest instead of repeating them in every input. Source,
record and selected-review inputs remain independently bound for every row.
Two different earlier judgments at the same owner cannot share one identity.
Reject missing, duplicate, unused or forged pool entries; validate every expanded
row before UI installation and give restored rows independent session copies.
Keep old-format reading and refusal at unchanged limits. Selected-paper wrappers
explicitly version this new nested work while preserving source transitions.
Never restore an expiring review or drop writing to make a save fit. The existing
ExecPlan records review, capacity measurements and native/regression evidence;
this representation change does not establish server or whole-product readiness.

On 2026-09-23 the user asked whether the prototype uses Rust and reported slow
interaction. The TUI and its portable domain/application services use Python;
the repository has no Rust source or Cargo project. Production framework
selection remains open under [ADR 0012](../architecture/decisions/0012-terminal-research-workspace.md).
This investigation changed no application behavior or selected framework.

Local macOS measurements used Python 3.13.15, `xterm-256color` private PTYs and
the existing manual synthetic fixture (10 nodes, 15 edges). Instrumentation
measured input written to the PTY through completion of curses refresh; it
does not measure terminal-emulator painting or SSH latency. The existing
user-owned preview was not driven by the probe.

| Interaction | 156 × 48 terminal | 271 × 66 terminal |
|---|---:|---:|
| Node selection, median of 24 inputs | 14.3 ms | 22.7 ms |
| Short Korean note typing, median of 13 inputs | 14.8 ms | 29.8 ms |
| Typing after 10,000 note characters, median of six inputs | 22.0 ms | 39.6 ms |
| Esc to cancel, two observations per size | 1.17 s | 1.18 s |

The measured curses escape delay is 1,000 ms, followed by the application's
150 ms suffix wait. That explains most of the Esc delay. An isolated process
with `ESCDELAY=25` reduced cancellation to about 200 ms, with the application's
suffix wait still present. This identifies an input policy to improve, not a
production timeout choice validated over remote connections. See the
[Python escape-delay contract](https://docs.python.org/3.13/library/curses.html#curses.set_escdelay).

For ordinary navigation, composing the Python frame dominates. Profiling finds
repeated text cleaning and cell-width calculation, including for blank panel
fills. Graph geometry itself has a 0.05 ms median over 100 calls. Composing a
271 × 66 frame has a 20.5 ms median over 30 calls after five warmups; a temporary
in-process bulk space-fill experiment reduced it to 8.9 ms over 30 calls, with
identical frame cells for the inspected scene. This was not applied to source.
Each key currently triggers composition even while a note is being edited;
40 navigation keys queued at once took 913 ms to finish at that larger size.
Curses already compares screen state, so rebuilding the Python frame is not
equivalent to transmitting every cell on every normal refresh.

The next proposed increment is to reduce redundant escape waiting, avoid
repeated work for blank/unchanged content, and check input ordering and partial
sequences before changing redraw scheduling. Preserve Unicode, paste, resize
and terminal-restoration behavior. A Rust presentation experiment using
[Ratatui](https://ratatui.rs/) remains a candidate for a later comparison with
the same graph and interaction tasks; these measurements neither benchmark
Rust nor justify rewriting the domain core. Larger graph and actual SSH
measurements remain outstanding.

### Comparative TUI review

Assessment date: 2026-09-23. The user requested an outside assessment against
well-regarded TUIs, the earlier visual references and the server-terminal
research goal, with an actual Claude Opus cross-review. This section records
findings and proposals, not an implemented redesign or framework decision.

The comparison used upstream documentation, original public demonstrations and
selected source at fixed commits. It did not install or benchmark those apps.
Positive firsthand reports for [Lazygit](https://news.ycombinator.com/item?id=37009879),
[Posting](https://news.ycombinator.com/item?id=40926211) and
[btop](https://community.linuxmint.com/software/view/btop) support their inclusion;
[Harlequin's site](https://harlequin.sh/) also collects positive user comments,
which are a curated sample. This is a candidate reference board, not a
representative popularity ranking or evidence of scientific usability.

| Candidate and view | Implementation inspected | Useful quality and adaptation limit |
|---|---|---|
| [Lazygit](https://github.com/jesseduffield/lazygit), selected item and detail/diff | Go; repository-local gocui and tcell. [GUI source](https://github.com/jesseduffield/lazygit/blob/5fcbdadc67dc6bb8b60d2c095306d9ba21bc62c6/pkg/gui/gui.go) and [layout](https://github.com/jesseduffield/lazygit/blob/5fcbdadc67dc6bb8b60d2c095306d9ba21bc62c6/pkg/gui/layout.go) retain contexts and handle view origins during loading/resizing. | Borrow stable object/detail context and local command hints. Do not copy its number of panels or treat scientific adoption like an ordinary Git shortcut. |
| [Yazi](https://yazi-rs.github.io/features/), selection and preview | Rust with Ratatui components and Tokio in [Cargo.toml](https://github.com/sxyazi/yazi/blob/0ea4c5d9ef75d7165c2e3b4eb8d713fc11f26c96/Cargo.toml); [rendering](https://github.com/sxyazi/yazi/blob/0ea4c5d9ef75d7165c2e3b4eb8d713fc11f26c96/yazi-fm/src/app/render.rs) distinguishes partial, normal and forced work. | Borrow responsive preview scheduling, not file-tree navigation as a replacement for the user's graph. Image-protocol support is not a prerequisite for argument reading. |
| [Posting](https://posting.sh/), request/response and focused editor | Python/Textual; [app source](https://github.com/darrenburns/posting/blob/56703a11513e8e74e681b4f859f31945b71e746f/src/posting/app.py) connects bindings, jump overlays, reactive state and an exclusive async request worker. | Borrow keyboard-visible targets, contextual help and a clear edit state. Its broad command palette remains outside ClaimBranch's current V0 scope. |
| [Harlequin](https://harlequin.sh/), catalog, editor and result | Python/Textual; [app source](https://github.com/tconbeer/harlequin/blob/8c4b1850c91085db98ffdafe6c85e52d5d1897c4/src/harlequin/app.py) separates threaded query work/cancellation from the UI. | Borrow generous prose/edit space, deliberate pane expansion and result context. Do not expand ClaimBranch into a general IDE or assume SQL execution maps to experiment authority. |
| [btop](https://github.com/aristocratos/btop#screenshots), resource overview | C++ with its own drawing/output path; [runner](https://github.com/aristocratos/btop/blob/612e18f5bd598fe987b30d041b39e5d7b3e0794f/src/btop.cpp) distinguishes collection/redraw work and optionally brackets output with terminal synchronization. | Borrow clear region hierarchy and restrained semantic emphasis. Its dense, continuously refreshed telemetry is a poor default for scientific prose. |

The implementations show several mechanisms behind perceived responsiveness.
Yazi's author describes [cancelable previews, visible-content work, caching and
merged renders](https://yazi-rs.github.io/blog/why-is-yazi-fast/). Posting exposes
[jump targets and focus-specific help](https://posting.sh/guide/navigation/).
These are concrete design/engineering references; their existence does not
establish a speed ranking between languages or make a framework migration a UX
repair by itself.

Retain the existing spatial graph, shared-evidence identity, typed arrowheads,
one-hop emphasis and readable dim context. The earlier references still inform
the task: Heptabase/Obsidian contribute stable objects and contextual reading;
Kialo contributes legible argumentative relationships; VISAR contributes the
link between argument and writing. Their useful qualities are not a mandate
to fit a desktop canvas and a long document into every terminal size.

The current prototype remains stronger at showing a graph than supporting a
complete reading/writing session. Specific findings:

1. **Reading changes the available map.** The synthetic scene is 130 × 28
   cells. At 156 × 48, opening the reader reduces the graph pane to 62 columns;
   selecting E1 and composing both modes moves its viewport pan from `(0, 0)`
   to `(40, 0)`. Geometry is unchanged, but neighboring cards become fragments.
   At 100 × 32 the pane is only 43 columns. Propose a stable reading workspace
   where minimum content widths permit it, explicit full-graph expansion, and
   named endpoints for off-screen connections. Small terminals need an
   explicit reading mode with reliable return, not an unreadable miniature
   map. Do not silently filter/rearrange the approved graph or replace it with
   the outline. No universal split ratio has been validated.
2. **Cards lose scientific distinctions.** Comfortable cards are 23 columns
   wide with a 19-column text measure. Four source rows become three when a
   note preview exists. Long units, conditions and introductions displace
   comparison values and conclusions; multiple cards are titled only `MAIN`.
   Propose stable short claim labels, source-grounded concise fact lines and
   enough width for identifying content. Preserve full originals in the reader
   and keep notes visibly separate. AI-generated scientific summaries must not
   silently become source labels.
3. **Shared evidence needs named destinations at reading time.** Claim uses
   already exist in the reader. With E1 and a short Korean note, their heading
   is below the first viewport at 100 × 32 and 80 × 24; at 80 × 24 the note
   heading is also below it. Put the selected fact and named scientific uses
   ahead of long optional prose. Keep exact source/type/target and rationale
   accessible, with a local neighbor-selection aid as a candidate. An AI
   suggestion must not substitute for the recorded edge rationale.
4. **Some lines appear joined without a shared endpoint.** The stroke merger
   combines different edges into `┬/┤/┴` glyphs; only four-way crossings become
   `╳`. Independent calculation finds `interpretation → obs-1` (`interprets`)
   and `run-accuracy → obs-2` (`produced`) sharing `┴` at scene cell `(98, 23)`.
   They have no common endpoint. Another mixed junction occurs at `(98, 14)`.
   Improve routing/ports and preserve each edge's identity in overlap. The
   ambiguous glyph is code-backed; actual human misinterpretation is untested.
5. **Back mixes viewing with traversing.** Calling the actual key handlers
   from the initial thesis with `j`, Enter, Esc selects `claim-pruning`, reads
   it, then returns to `thesis`. Opening the reader did not save a separate
   return state. Propose distinguishing closing a reading view from returning
   along node traversal; test selection, occurrence, scroll and pan together.
6. **Small screens devote too much space to framing.** An 80 × 24 graph has
   only 11 drawable content rows. Comfortable reader spacing inserts blanks
   after headings and existing section separators. Retain the user's approved
   padding where useful, but compress repeated instructions, headings and
   empty lines on short viewports. Keep a few local actions visible and other
   existing actions reachable through contextual help. A global command
   palette remains a post-V0 proposal under the product specification.
7. **Input and session continuity precede daily-use readiness.** The measured
   Esc/rendering costs above remain actionable. The small editor lacks undo
   and silently bounds insertion at 12,000 characters. Keep the existing
   Enter/newline, Ctrl+S/session-keep, Esc/cancel contract; consider clearer
   edit state, recoverable uncommitted text and explicit discard handling.
   Raw mode does not currently suspend on Ctrl+Z. Shell suspend/resume is a
   separate proposed interaction to test with the host, not permission to
   execute experiments. Persistent draft recovery across exit or SSH loss is
   a larger integration boundary; current volatile notes are an explicit
   prototype limitation, not an implemented daily-use guarantee.

**Cross-review outcome.** Claude Code 2.1.280 ran an actual pinned
`claude-opus-5-5` against a fixed source copy, the two prior Mac Terminal
captures, six current text views and selected upstream source. Its tools were
read-only, customizations/MCP were disabled and session persistence was off.
Runtime metadata reported that canonical model, success and no permission
denials. Opus did not run the app or perform a human usability study.

Independent assessments agreed on clipping, scientific labels, small-screen
framing and editor limitations. The parent reproduced the junction and
Enter/Esc cases above. A bounded second Opus call, reasoning over those
reported checks with tools disabled, withdrew five overbroad claims: a fixed
60/40 layout, an unqualified navigation-stack endorsement, treating 14–40 ms as
proof of satisfactory responsiveness, changing Esc to save implicitly, and
inferring Python 3.10 support from syntax. Both runtime results identified
`claude-opus-5-5`. These corrections matter: AI agreement does not replace
direct observation or the current user contract.

**Framework implication.** Repair the bounded input/rendering defects in the
current prototype. Textual is a credible next comparison because mature text
editing, focus/binding widgets and workers fit the existing Python services
and research reading/writing work. A bounded graph/editor spike still needs
Unicode, paste, SSH, resize and latency checks. Rust/Ratatui remains credible
for a native frontend, but retaining the Python core still requires a runtime
and an integration boundary. No Rust speedup or whole-product single-binary
deployment has been demonstrated. Avoid indefinitely rebuilding editor and
widget infrastructure in custom curses; choose the production framework from
the measured interaction, host and maintenance requirements.

**Follow-up slice accepted for implementation on 2026-09-24:** read E1, inspect both distinct claim uses and write a
short note while preserving orientation. Compare a stable wide reading layout
with an explicit compact reading mode, over the same records and selection.
Acceptance should observe: (a) the researcher names both uses and their actual
directions without treating shared evidence as two observations; (b) viewing,
following and returning preserve the intended node and viewport at 156 × 48,
100 × 32 and the small-screen fallback; (c) a mixed Korean/English note remains
distinct from source and judgment, and keep/cancel, paste and resize behave
predictably with AI off. Add a larger 40–60-node synthetic task before claiming
paper-scale legibility. Human task observation, actual SSH/tmux, physical IME,
screen readers and production research custody remain unverified. The private
prototype checkpoint described below is narrower than production recovery.

### Terminal workflow refinement

The 2026-10-11 publication repair preserves active writing under an unrecognized
Alt/Option chord, including Alt+Backspace; standalone Esc still cancels. This
changes no composition, argument meaning or authority. The observable task is
to keep a note editable after those chords, then keep it explicitly with Ctrl+S.
Its [input contract](../development/workflow.md#terminal-paper-prototype) and
[terminal oracle](../validation/cases/saturation.md#103-terminal-prototype-oracle)
own command details and acceptance; the existing ExecPlan owns test/CI evidence.

The user requested implementation of the comparative review and documentation
on 2026-09-24. The task remains reading E1, identifying both scientific uses,
writing a personal note and returning to experiments in the same terminal.
The input is the unchanged synthetic paper projection; AI and protected writes
are outside this slice. The [terminal workflow](../development/workflow.md#terminal-paper-prototype)
owns exact commands and keys; [terminal oracles](../validation/cases/saturation.md#103-terminal-prototype-oracle)
own observable outcomes.

The September 24 increment compared a stable wide graph/reader workspace and
an explicit full-graph overview. The September 25 density iteration below
changes the default to the overview with optional reading. An open workspace retains the same
graph width when focus enters reading; the overview gives routing more room.
Below 140 columns, reading takes a full pane and closes back to the same graph
position. This avoids making the prior fixed-width scene into two unreadable
miniatures. That iteration compacted framing and cards on short terminals;
the current density control is described below. The
user-approved palette and roomy gray-panel treatment remain on taller screens.

Stable claim aliases disambiguate formerly identical MAIN headers. Card text
is a visibly shortened source excerpt, never an AI reconstruction. Evidence
keeps its value even with a note preview. Reading prioritizes the recorded
measurement, conditions and named claim destinations; source statements,
personal notes and full methodological context follow. Frozen episode AI
history remains separately labeled; no node-scoped AI opinion is invented.

Routing ports follow opposite endpoints' vertical order and adjacent-column
trunks minimize shared intervals. That iteration introduced crossing/shared-
routing glyphs and shared-port counts. The later contact-badge iteration below
replaces those marks and mid-route words while the relation picker retains
exact typed edges and rationales. Incomplete
cards are omitted with named offscreen direct neighbors; hiding a partial
card does not hide its record or create an edge. Source-length captions,
overlapping routes and offscreen neighbors still require task observation;
these changes do not establish that 50 nodes are easy to understand.

Editor undo/redo, a visible text limit, explicit recovery of cancelled buffers,
and shell suspend/resume address terminal continuity without changing Esc into
save. [ADR 0013](../architecture/decisions/0013-terminal-draft-recovery.md)
allows an opt-in private checkpoint, separate from scientific authority. The
default demo remains volatile. The implementation stays Python/curses while
the production framework comparison remains open; source-level comparison of
Textual and Ratatui above is not a completed widget/SSH benchmark or migration.

Validation exercises reading versus traversal return, stable wide composition,
the short-screen E1 task, exact relation identity, Unicode editing, limits,
cancel/recover, real-PTY resize and suspend, and process-loss recovery. A
50-node/75-edge projection checks bounds and identities without altering the
canonical fixture. A genuine Mac Terminal capture exposed excessive framing
at 120 × 30; automatic compact framing/cards address that concrete observation.
Performance and independent review evidence belong to the existing ExecPlan;
human task observation, Linux/SSH/tmux, physical IME and assistive technology
remain separate checks.

### Graph overview density review

On 2026-09-25 the user requested a review of smaller nodes and further TUI
improvements before another implementation. The task is to recognize the paper's
structure, locate shared E1 and follow its two scientific uses while remaining
in the experiment terminal. The existing palette, panel padding, one-hop
emphasis, single evidence identity and editable notes remain useful. The
problem is that document-sized cards and persistent reading compete for the
space needed to understand the graph.

**Observed geometry.** The unchanged 10-node/15-edge manual synthetic paper was
rendered at 144 × 42, 120 × 30 and 80 × 24, selecting both T and E1. E1 carried
a labeled example personal note. An isolated, temporary renderer experiment
changed only card dimensions and gaps; it changed neither application files
nor the source/history. Counts below are wholly visible cards with E1 selected,
not comprehension scores. Dimensions are terminal columns × rows.

| Composition at 144 × 42 | Card; horizontal/vertical gap | Graph viewport | Complete cards |
|---|---|---|---|
| Current workspace | 23 × 6; 12/4 | 71 × 25 | 4/10 |
| Existing compact workspace | 21 × 5; 12/2 | 71 × 25 | 6/10 |
| Existing full graph | 23 × 6; 12/4 | 130 × 25 | 7/10 |
| Temporary smaller cards and gaps, workspace | 18 × 4; 8/2 | 71 × 25 | 6/10 |
| Temporary smaller cards and gaps, full graph | 18 × 4; 8/2 | 130 × 25 | 10/10 |

The current scene is 130 × 28 cells; the temporary small scene is 98 × 18.
With T selected, the current workspace shows 3/10 cards. At 120 × 30 the
existing single-pane layout shows 5/10 cards for either selection; the small
scene shows 10/10. At 80 × 24, E1 still shows only 4/10 in both geometries.
The small full graph contains all 15 route geometries at the two larger sizes,
but this does not establish that people can trace or distinguish those routes.
The existing `f` command widens the graph pane; it does not fit the scene.

**Why uniform shrinking is insufficient.** Inspection of the actual prior
144 × 42 Terminal capture and fresh deterministic frames confirms that the
reader, horizontal lanes and vertical spacing all affect coverage. The small
experiment exposes the next failure: sibling claim excerpts have nearly
identical beginnings, E1's note displaces its source excerpt, `supports` wraps
inside a word, and the plan's `UNRUN` header truncates. A card fitting inside
the screen is not evidence that it meets PG-1. The existing offscreen legend
names only hidden direct neighbors, not every hidden node; total counts alone
do not explain how much of the paper is currently visible.

**Implemented overview.** The user authorized this direction after the review.
The map now starts full width with compact cards, two source-preview rows and
reserved header continuation rows, selected-source
context and grouped typed destinations below it. Authored captions distinguish
the frozen example's scientific subjects/results and match complete source
statements, not IDs. Changed/unknown content uses an abbreviated source excerpt;
the reader always retains the original. This is a bounded synthetic adapter,
not an AI summarizer or a durable title model. Compact notes use a presence
mark so personal text cannot displace a result. Comfortable source cards and
the reader retain labeled note text and full editing. Reading opens on demand
and can be pinned on wide terminals. Pin preference survives traversal and
temporary full-map expansion; closing reading restores map context. Selection
does not enlarge a box or rearrange its neighbors.

Compact dimensions and gaps adapt to available cells within a readable floor.
Fit opens the full map at that density and resets panning without promising
that arbitrarily large graphs fit. Original outer-panel padding remains.
Selected connection types now use full phrases beside connected card titles, as
specified below. Structural links retain their actual targets and do not become
scientific support. Adjacent same-column links use vertical ports unless the
pair has a reverse connection; reciprocal pairs keep distinct target arrows
through side routing. Incoming and outgoing routes never share a port.
Visible/in-scope counts distinguish viewport clipping from nodes and edges
hidden by an explicit neighborhood.
The [terminal workflow](../development/workflow.md#terminal-paper-prototype)
owns keys, limits and return behavior.

Local scope stays rooted at the explicitly chosen node with one to three hops;
selection alone does not filter away more context. The user can return to all
nodes in the current lens. Following an outside edge reveals its target and
back restores the prior scope. [Obsidian's official graph guide](https://obsidian.md/help/plugins/graph)
documents global/local views and adjustable local depth. That is a useful
reference for explicit scope, not permission to copy unlabeled dots or
force-directed movement into an argument map. Hidden content retains counts
and shared evidence identity. With the later user-requested vertical spacing,
the ten-node overview fits at 144 × 42 and 120 × 32; E1's five-node local scope
fits at 80 × 26. Shorter views preserve the connector and report clipped cards. These are rendering
outcomes, not proof of comprehension.

Validation combines full-card coverage with distinguishing sibling claims,
identifying E1's two named uses and edge types, distinguishing an unrun plan,
reading measurement conditions, editing a personal note and returning without
losing position. Korean/English text, monochrome cues and terminal resizing
remain part of that comparison. The original 50-node test duplicates five
disconnected copies and checks bounds/identity. A new connected 50-node/83-edge
projection adds root bridges and cross-branch shared evidence; it checks scope,
counts and identities, not paper-scale legibility. Horizontal legs
participate in route reservation; a detour can separate one route's source
leg from another's target leg. Relationship words occupy the reserved card header band;
they do not overwrite route strokes. Human task completion and
actual SSH/tmux remain separate from deterministic rendering and model critique.
The execution record owns independent review and check evidence.

### Read connection types at node contacts

The user found mid-route words and repeated crossing X marks unreadable on
2026-09-26, then rejected the replacement S/C/Q codes because the map required
learning a separate key. The current slice serves a researcher selecting shared
evidence and asking what each neighboring record actually does with it. The
initial state is the existing synthetic graph, preserving its source content,
recorded direction, compact overview and exact relationship reader.

The user subsequently requested title-adjacent labels rather than relationship
text in the body. Use a regular-weight phrase beside the title when it fits,
for example `R1 RUN · produced E1`. Terminal cells have one font size, so weight,
placement and semantic color make the phrase secondary. Long or additional
parallel phrases continue directly below the title within the header band;
source previews start after that band. Never shorten the phrase to a code or
hide its direction to squeeze it beside a title.

Full directional phrases retain the previous perspective: evidence
E1 makes its claim say `supported by E1` or `challenged by E1`; its run says
`produced E1`. Selecting the claim reverses the perspective to `supports C1`
on the evidence card. Structural containment has its own `contains C3` / `part
of C1` wording. Parallel relationships receive separate rows. Exact-edge focus
shows only the selected relation. The source preview and personal note remain
separate. Reserve the maximum header continuation rows needed for any one neighbor
before selection, so focus never moves or enlarges boxes. A card needing only
inline labels needs no extra row. The tradeoff for longer labels is modestly
taller cards; adaptive gaps and reclaimed legend space preserve the tested
small-graph overview. Oversized maps retain explicit scope and panning.

Route lanes contain strokes and recorded target arrows, with no letter codes,
mid-route words or crossing X marks. Paint one recorded stroke through each
overlap, prioritizing the inspected edge, then incident edges, then background.
Actual common-port first legs retain their fork unless one exact edge is being
traced; independent crossings cannot acquire that exception. This is visual
occlusion, not deletion or a new relation. The exact reader preserves full
endpoint/type/rationale, including relationships outside the current lens.

Failure means a reversed phrase, a hidden parallel type, overwritten source
text, label/line collision, moving cards on selection, lost small-map coverage,
or needing color/a code key to decode meaning. Check wide/narrow and monochrome
frames, long aliases, shared/parallel/reciprocal edges, real PTY resize and the
retained scientific manifests. Unfamiliar-reader understanding remains a human
validation question; rendering tests and model critique cannot establish it.

### Connect judgment to scientific review

T1a implemented 2026-09-28: Work now starts with source-grounded subject content,
then the node's judgment and reason; actionable status precedes long text.
The editor keeps source beside writing at wide sizes and as a bounded strip at
narrow sizes. Full source inspection is read-only and retains the same edit
buffers, cursor and undo history on return. The
[terminal workflow](../development/workflow.md#terminal-paper-prototype)
owns exact keys and limits; the
[terminal oracle](../validation/cases/saturation.md#103-terminal-prototype-oracle)
owns observable checks. This implements the contextual-writing slice, not the
planned authoring, cross-node identity or durable-scientific-work
milestones.

T1b adds a named contextual action list from the selected node and an actual
AI-off launch. The brief is to find manual writing and review without memorizing
`c/R/C/M`, while retaining the recorded subject and graph return position.
Use one scrollable list with the selected action's explanation, manual actions
first and optional fixed-example assistance last. Creation entries explain
their missing adapters before opening forms. At narrow sizes a full contextual
surface leaves names and availability legible; this reuses the established
picker pattern rather than introducing a general command palette. The header
discloses AI availability before selection. A disabled service supplies no
response, even after changing episodes or opening comparison projections.
See the linked workflow for exact commands; this creates no scientific object,
new ownership model or persistent research store.

Composition comparison used the same manual example and a test-only cooling
history: retaining the graph beside an embedded editor at 144×42 leaves the
editor in a narrow reader-sized pane with a shortened source strip; focusing
writing provides a readable source column and wider judgment/reason fields.
Choose focused writing while an editor is open, retaining the graph for
navigation and the same return context. At 80×24 the compact strip leaves both
fields editable and signals truncation; full recorded definitions and context
remain one explicit source action away. These are agent-observed comparisons,
not measured human usability. No source fixture or caption table was rewritten.

The two planned entry stories were walked through using that cooling example:
an unresolved result needs a draft source/observation owner before a claim
exists; an existing claim needs explicit reuse of the same observation plus a
relationship reason. Neither requires a completed judgment or an AI response.
Actual entry controls remain T2b, while stable candidate ownership and a
judgment-free domain projection remain prerequisites of T2a/T3a. No product
initialization controls or automatic evidence confirmation were added.

The remaining TUI work is functional, beyond density tuning. Starting from the
same synthetic node, a researcher should write one judgment/reason, optionally
inspect a scoped offline proposal, select authored changes and inspect their
exact before/after meaning. The paper services own context, contributions,
selection closure, freshness and review; the terminal only adapts those contracts.
No claim wording is inferred from a personal note or silently copied from a
judgment. Change fields and their inclusion require explicit editing/selection.

The bounded implementation uses a contextual work reader and keyboard
pickers/editors over the current paper. Proposal adoption is distinct from
request review and scientific review. Manual editing remains usable while a
response is pending; stale or cancelled arrivals cannot replace it. Closing or
deferring review preserves draft text. The existing checkpoint stores text-only
manual drafts, so AI-influenced work, proposal history and scientific selections
remain visibly session-only and require a quit-loss notice even with that
checkpoint enabled. They must never reopen as a provenance-free manual draft.
Production resumption belongs to the separate storage integration.

The adapter now connects manual and offline-proposal journeys to an unaccepted
selected-change review, with exact effects and preserved origin visible in the
terminal. Field differences precede contribution history in the review reader;
an explicit graph comparison shows the service's before/after projections and
returns to the prior viewport. Full-screen work pickers do not redraw or move
the covered argument map. Existing long Unicode buffers remain writable when
they exceed a narrower service byte limit; requests/reviews wait for shortening
rather than silently using an older draft. The
[terminal workflow](../development/workflow.md#terminal-paper-prototype) owns
the exact keys and persistence limits. Cumulative episode navigation, pending work,
branch/merge and manuscript review are connected below; actual project storage
and live AI remain separate unfinished connections. The existing
ExecPlan records this implementation and its observed checks.

### Navigate cumulative research work

The cumulative terminal slice lets a researcher choose an episode and its
main/alternative reasoning view, then inspect work reconstructed from that
synthetic history. An explicit episode picker (`t`) and conditional work list
(`W`) leave the graph as the primary view. Escape dismisses a picker without
moving the map; returning to an episode/ref restores its reading position.
Each note, judgment, cancelled buffer and proposal belongs to its exact
episode/ref/node. Older reasoning still reads current global evidence; the
UI must identify that distinction instead of implying a historical snapshot.

Pending items show their originating judgment, affected claims/anchors,
retained AI influence and changed-source flags before offering graph navigation.
They remain conditional on acceptance, with no accepted debt or closure action.
The list is separate from unfinished local text (`U`); opening a closed episode
or reading a consequence cannot resolve either. Only actual reconstructed
work kinds are shown; no follow-up experiment is invented as an obligation.
The existing paper workspace owns draft sessions. Private text checkpoints may
carry episode identity, but AI-influenced work remains session-only. Observable
failures include context leakage, stale source wording, lost buffers after
switching, a misleading completed badge, or a picker that shifts its covered
map. Manuscript wording review is connected below; real project opening remains
a later connection.

### Resume unfinished review writing

The terminal slice lets a researcher cancel a scientific-change or review
explanation editor, move to another node/ref/episode, then find and resume that
text through U. Use the existing unfinished-writing surface; W remains
conditional scientific work. Keep local review text in a separate session-only
registry, outside graph-note checkpoints. Merely reading and cancelling a
prefilled editor must not create unfinished work. Changed text, including an
intentional empty edit, remains distinct from staged changes/completed review.

Resumption identifies the original context and text kind before opening it.
It does not prepare or complete a new review automatically. Expired comparisons
must stop displaying an apparently current before/after graph; the researcher
returns to Work, refreshes the selected scope, and can reuse their explanation.
Exact service digests remain the completion gate. Validate cross-context return,
failed/expired completion, quit disclosure with checkpoints, Korean text and
readable wide/narrow unfinished lists. No accepted or durable research write is
introduced. The implemented picker separates kind, original context and preview
on three lines with a blank row between entries, and sizes its box to the item
count. At 144×42 and 80×24 the two-entry example keeps kind, context and the
session-only label visible. Below 48×18 review controls pause with an Escape
hint. This supports the earlier drafting/navigation integration review; its
observed verification and remaining gaps belong in the ExecPlan.
The picker offers `x`, then `x` again, to discard only the selected unfinished
review input; Esc cancels that confirmation. Kept/staged/reviewed content is
unaffected. Context browsing preserves the current AI proposal; amendment
editing revokes scientific comparisons independently of optional AI requests.

### Tune graph spacing and reading

The user requests more vertical room for upward challenge arrows and selects
view settings as the next UI implementation. Preserve compact cards and full
header relations, but reserve at least three route cells between directly
stacked connected cards, even in short viewports. Arrow visibility takes
priority over squeezing the last card into a short overview; clipped counts,
follow/pan and local scope must remain honest. Wide overviews remain available.

A reversible view-settings panel (`,`) groups node spacing,
card detail and reader pinning. Changes preview in the current graph, Enter keeps them and Escape
restores the prior settings/position. Spacing and reader preference are
session-only; no scientific content, draft, relation or review binding changes.
Compare balanced versus spacious spacing at 144×42, 120×30 and 80×24, including
selected upward challenge, shared evidence, reading return and resize. Never
shrink a lane back to a zero-length connector to satisfy a fit count.

### Inspect branch candidates and selected merges

The terminal slice connects an authored node-bound draft to a detached alternative
candidate, then to selected merge review. Use the existing branch/merge services;
keep the graph workspace's history unchanged. `C` from Work previews the draft's
selected/required/omitted changes; an explicit continuation computes the branch
candidate. `M` from the graph reviews the recorded alternative directly.
The merge picker starts with explicit choices, shows closure and exact field
effects, and offers before/after graphs plus original/current AI contributions.
A supplied read-only manuscript fingerprint is required for exact merge review;
file change, selection change, draft/source change or expiry invalidates it.
Explanation or deferral follows the service's inherited-AI rule. A separate
candidate action computes a value without updating the workspace or storing it.

The full series fixture is closed. An explicit `--merge-example` entry replays
the golden-verified series prefix immediately before its last selected merge;
it does not silently reopen a closed episode or fabricate new research. Preserve
all previous evidence at that prefix, label it synthetic and active, and keep
ordinary `--series` behavior. Branch and merge review state remains session-only,
with quit disclosure and cancelled explanation/source buffers. Escape restores
the original work/graph context. Validate exact choices, stale parent branch
reviews, inherited AI, source refresh, narrow graph traversal and real PTY return.

### Review wording from pending manuscript work

The manuscript slice starts with an existing conditional Writing impact
item. A researcher opens its manuscript review without changing graph context,
supplies a local UTF-8 source file read-only, writes replacement wording and a
reason, then inspects diff/before/after and the inherited scientific basis.
The existing `PaperManuscriptSession` owns marker targeting, exact source-byte
binding, TeX escaping, expiration and AI explanation requirements. No wording is
invented or copied from a graph note. The UI never writes the source file.

Source entry reads only a regular file, bounded to 64 KiB; invalid/missing
sources retain wording. Preparation and completion re-read the file; a changed
source revokes the previous exact review. Screen text is a terminal-safe
projection, while service digests and candidate bytes retain the exact supplied
source. Loading a file does not establish trusted file identity. Tabs separate
the diff, complete original, candidate and causal basis. Inherited AI origin
still requires explanation or explicit deferral even for manually written text.

Work ID owns kept wording and unfinished source/wording/explanation buffers.
Escape returns to the originating pending item and graph without moving its
viewport; Not now clears the review while retaining wording. Everything here
remains session-only, including with private manual-note checkpoints. Normal
quit names that loss. Completing review cannot close pending work, accept
reasoning, apply text or claim compilation. Observable failures are stale diff
completion, source-byte changes, cross-item text leakage, lost cancelled buffers,
hidden AI influence, or a completion label implying an applied manuscript.
Validate both manual and AI-origin paths, malformed markers, changed/deleted
source, expiry, bounded file reads, narrow/colorless frames and a real PTY
Korean-paste/resize/return journey. Human/SSH gates remain separate.

### Paper argument workspace

This section proposes mechanisms for the confirmed product direction. It does
not record user acceptance of every mechanism or imply that they are built.
Argument/content semantics apply across hosts. The zoom/hover mechanics below
are earlier graphical hypotheses; the terminal design above owns the next
primary-workspace iteration under ADR 0012.

**Overview and reading.** Begin with the thesis and main claims. Expand a chosen
claim to its optional subclaims, observations and experiment records, retaining
its path back to the thesis. Claims with direct evidence skip the subclaim
level. Shared evidence keeps one identity with multiple named connections.
Progressive expansion is the proposed way to limit visual load; exact density,
zoom, navigation and layout need a real-paper-sized synthetic example. Spatial
order is a reading aid, not a reversal of support/challenge direction or proof
of logical implication.

**Node content.** Put the scientific proposition, result or experimental question
ahead of the internal ID. Keep enough subject, condition and comparison in the
visible text to understand it independently. Open longer method, metric, source
and provenance details in context. For the existing R-01, a source-grounded
caption could be “가지치기·양자화·압축의 손상 순서를 포화도 기반 민감도로 예측할 수
있는지 비교”. This still cannot define damage: the redacted source contains
categorical outcomes but no measurement definition or numeric results. Do not
invent an accuracy-loss or output-error metric as historical fact. The next
illustrative fixture needs explicitly defined terms, units, baseline and
conditions, labeled synthetic and separate from the integrity-checked original.

**Connection emphasis.** Propose modest enlargement of related nodes without
layout reflow, stronger direct connections, lighter indirect paths and subdued
unrelated context. Clicking may pin the focus. Keyboard focus and touch must
provide the same information, and reduced-motion mode must retain emphasis.
The exact traversal depth and animation values remain implementation proposals.
Show the relationship type; visual proximity or reachability cannot create a
new scientific relationship.

**Possible outcomes and impact.** Selecting a follow-up experiment should make
its tested claim and upstream argument visible. Proposed scenario controls are
“consistent with the hypothesis”, “opposing result” and “inconclusive”. These
are not yet a frozen state vocabulary. Each scenario must name its assumed
observation and mapping to the argument; an operationally failed experiment is
not automatically contradicting evidence. Show affected paths, alternative
remaining support, unchanged nodes and manuscript consequences on the graph.
Keep current and hypothetical states visibly distinct and require a fresh
review after source, selection or assumptions change. A highlighted dependency
is a candidate for review, not an automatic verdict that an ancestor is false.

**Judgment, AI and manuscript.** Select a node or relationship to inspect/edit
its meaning and human rationale, ask for a scoped AI proposal or compare the
relevant source wording. Reuse that input for exact review and provenance.
Before/after and included/omitted state should be visible in the graph; detailed
reason and diff may open beside the selection. Teach-back/deferral and exact
authorization remain available in context without a second mandatory judgment
form. The authority and manuscript-phase distinctions below still apply.

### Earlier sheet storyboard

The remaining storyboard description explains existing generated artifacts for
regression and reusable content; it is not the new primary layout specification.

The primary object is the research episode. A context strip identifies the
reasoning target and affected manuscript block. The main reading order is:

1. **What was observed?** Existing claim, three observations and each condition.
   Compression support is visibly limited to compression.
2. **What does AI suggest?** Optional original proposal, clearly unaccepted.
   Human edits remain distinguishable from that original.
3. **My judgment.** The researcher's interpretation and reason. Both start empty
   in the undecided example. Contextual explanation prompts reuse the reason
   already entered; there is no second summary form or AI grade.
4. **What changes?** Explicit selected/omitted changes and their existing
   evidence dependencies. Global observations remain present.
5. **What remains in the paper?** Exact source comparison when a consequence is
   selected, with its own application/verification/recovery status.
6. **Next action.** The specific operation or safe continuation, followed by
   optional provenance detail.

The storyboard's “five changes” is the existing fixture's status, interpretation
and three relationships; it is not a product-wide operation count. It excludes
new strong claims and automatic manuscript application. Production selection
closure is owned by the finite domain contract, not the storyboard renderer.

### State-by-state review

| Scene | Inspectable outcome | Detail to challenge during review |
|---|---|---|
| 01 Undecided | source context with blank interpretation/reason and no selection | Can work begin without knowing the final answer? |
| 02 Manual review | observations, human reason, chosen interpretation and source consequence | Is the reason for weakening the claim clear? |
| 03 AI comparison | fixed AI original alongside the human judgment | Can uncertainty be located without treating the AI text as evidence? |
| 04 Edited proposal | original, edited interpretation and human reason | Does the AI contribution remain visible after editing? |
| 05 Stale review | reviewed/current context and preserved draft | Is re-review understandable without asking for the same prose again? |
| 06 Not now | no accepted change; existing draft remains pending | Is this distinguishable from accepted work with explanation review open? |
| 07 Explanation deferred | assumed accepted research change, two separate open obligations | Can the researcher name what remains unfinished? |
| 08 Resume | same draft/reason as 07, specific pending work | Can work resume without reconstructing a transcript? |
| 09 Source unavailable | preserved observations, no fresh-source claim | Is the unavailable original clearly different from lost history? |
| 10 Provider pending | long Korean reason, manual work and cancellation | Does waiting for AI avoid blocking the researcher's draft? |
| 11 Late response | previous request context beside the newer judgment | Is the old suggestion clearly separate from current approval scope? |
| 12 Applied, unverified | manuscript changed in the example, verification still open | Is file application distinguishable from a finished manuscript task? |
| 13 Recovery | unknown file state, only inspection/export/verified-restore choices | Is stopping new changes clear and actionable? |
| 14 Outbound review | exact synthetic destination, content and excluded materials | Can the researcher inspect what leaves before choosing to send? |

Scenes 07, 08, 12 and 13 assume earlier human-approved operations solely to
show their presentation. Selecting a scene does not perform those operations.
Scene 14 uses a reserved example destination and makes no actual request.
Its displayed UTF-8 request, destination, exclusions, unknown retention
expectation and content digest make the example reviewable. Edit, cancel and
manual continuation remain visible. The digest identifies this example; it is
not an implemented provider envelope or consent receipt.

### Draft continuity and explanation review

The snapshot fixture points related scenes at the same draft. In particular,
edited review, Not now, explanation deferral and resume retain one judgment and
reason. The future product must achieve that continuity through the R4 draft
policy and R7 view model; the HTML retains no browser storage.

The existing interactive browser's recovery repair covers one narrower task:
after adopting an AI suggestion over an unfinished human draft, expand
**AI 제안을 가져오기 전 초안** to read/copy the most recently displaced text and
reason. Reuse the existing disclosure styling beside the editor; its source is
the volatile pre-adoption buffer, not accepted provenance. Empty or incomplete
human text must not be relabeled as a completed Judgment, and copying it back
must not erase AI influence. Keyboard disclosure and long Korean text at desktop
and narrow widths are checked by the browser smoke; this adds no terminal
layout/key choice or durable recovery claim.

Only AI-influenced high-impact review shows the contextual prompts. The two
examples ask which observation challenges which scope and what remains an
interpretation. Existing rationale can already answer them. Their usefulness
is a human design question; a checkmark, text length or AI answer cannot prove
understanding. A later product must allow the separately defined Not now and
debt-opening deferral actions with correct authorization.

### Rendering and accessibility boundaries

The design viewer, visibly outside the product sheet, selects one snapshot and
one reading style. With JavaScript disabled all snapshots remain readable.
The product sheet uses semantic headings, labels, disclosure controls and source
regions. Scene navigation updates the selected link and focuses its heading.
Text accompanies every state; the page adapts to a narrow width and source text
wraps. There is no decorative motion.

This provides a concrete review artifact, not a WCAG/NVDA or keyboard-completion
claim for the future product. Read-only fields and disabled actions cannot test
actual editing, approval, provider cancellation or persistent resume behavior.
Those require the R7 interaction tests and target-platform human checks.

## Security privacy and human-control boundaries

All content is synthetic, using the committed redacted fixture and explicitly
hypothetical view examples. No private original is opened or inferred. The
renderer consumes the source validator's verified bytes rather than reopening
the manuscript. It HTML-escapes text and emits no remote scripts, fonts or
assets. Its content policy denies network connections and form submission.

The only script changes scene visibility, focus and reading style. No approval
receipt, secret, store connection, browser storage or external API is present.
The product's native broker and private IPC are still unimplemented. A pleasant
screen or disabled button is not an enforcement mechanism.

## Migration and rollback

There is no real accepted product data to migrate. Keep the original single-
claim fixture and its goldens stable while reviewing the
[paper model extension](2026-08-03-domain-model.md#paper-argument-extension-under-review).
An additional synthetic paper example must identify itself as an illustration,
not fill gaps in the original source. Persistent schema changes need versioning,
replay and migration evidence before storage integration.

The source examples and template regenerate the checked-in HTML. Do not hand-
edit that generated artifact. Update the generator or app when implementing
the revised workspace; old screenshot/storyboard success does not validate it.
Presentation changes cannot roll back or advance accepted research state.

## Validation

The earlier storyboard's regression commands, from the repository root, are:

```sh
python3.13 -B -m scripts.render_episode_review
python3.13 -B -m scripts.render_episode_review --check
python3.13 -m unittest tests.contract.test_episode_review_design -v
python3.13 scripts/verify.py --scope docs
```

The contract tests check undecided entry, distinct deferral semantics, retained
reason/proposal provenance, restricted recovery/approval examples, escaped
content, inert product actions, absence of external assets and exact generated
artifact consistency. They do not assess human comprehension or live usability.

The revised workspace must additionally satisfy the
[paper argument oracles](../validation/cases/saturation.md#102-paper-argument-workspace-oracles)
in the actual target terminal at wide and narrow sizes; check an optional
graphical adapter in its browser separately. Check readable node content,
paper-to-experiment navigation, related-node emphasis, scenario/current-state
separation, AI edits, persistence/resume and unchanged accepted state for
inspection. Record observations and unavailable checks in the existing ExecPlan.
Do not claim those checks pass from the earlier storyboard tests.

## Open questions

- Which thesis/claim and relationship representation supports the paper without
  confusing a navigation parent with a scientific premise?
- Which bounded synthetic paper example defines every metric and demonstrates
  both direct evidence and subclaims without fabricating the original source?
- How much context stays expanded at each scale, including narrow/keyboard use?
- Which exact assumptions and relationship rules determine scenario impact,
  remaining support and uncertainty?
- Where do rationale, AI contributions and precise manuscript review fit beside
  the graph while retaining the complete human-authority contract?

The product direction is settled by the user's requirements; these details need
implementation review and observable UX checks. An agent cannot certify human
understanding. Mac-first execution follows
[ADR 0010](../architecture/decisions/0010-macos-first-platform-adapters.md).
This context review does not block portable domain/native work; R2 authority,
stack and custody evidence remains required before protected writes.

## Outcome

In review after user feedback. The paper-graph direction is required, while the
proposed detailed interactions and model extension are not implemented or
visually accepted. Earlier R1 artifacts and checks remain available as bounded
evidence; the revised experience needs new result review. The
[active execution plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns test results, the stop point and the next authorized step.


The [external import decision](../architecture/decisions/0021-external-proposal-import.md)
also permits explicitly unverified external typed responses in this same local
review. History, comparison and saved-origin reading retain that distinction;
local import context cannot imply original application dispatch. Reading is
untimed and each staging comparison is refreshed explicitly after expiration.
