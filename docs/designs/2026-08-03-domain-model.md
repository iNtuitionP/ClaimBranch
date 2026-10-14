---
kind: design
status: draft
owners: maintainers
last_reviewed: 2026-10-14
canonical_for: proposed finite F0 domain records relationships operations states and resource bounds
---

# Finite F0 domain and versioning model

Version: 0.4

This document is the canonical logical contract proposed for the first
ClaimBranch spike. It defines a finite saturation-shaped graph, authority,
provenance, state, replay, and resource boundary. The full protected schema is
not implemented; the candidate-only subsets below have executable contracts.
This document does not settle the production database, wire framework or UI
storage.

The [product specification](../product/product-spec.md) owns intended behavior,
the [target architecture](../../ARCHITECTURE.md) owns component and trust
boundaries, the [saturation case](../validation/cases/saturation.md) owns
observable content, and the
[active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)
owns sequencing and planned test commands.

## Purpose

Make the first graph-first foundation closed enough that an implementation can:

- accept only known records, edges, operations, states, and resource sizes;
- keep evidence global and reasoning branchable;
- preserve complete AI/human Contribution provenance;
- prove human authorization without trusting caller data;
- distinguish scientific acceptance from manuscript progress;
- replay deterministic histories without AI;
- reject out-of-F0 live cases visibly; and
- test every allowed and forbidden path before broadening the model.

“Complete” means complete for this fixture-bounded contract, not complete for
science or future ClaimBranch.

## Context and current state

ADRs 0001, 0003, 0005, 0006, and 0007 accept the evidence/reasoning,
proposal-only AI, human-authority, three-plane, episode, and manuscript-saga
constraints. The portable [review core](../../claimbranch/core/review.py) now
implements a bounded subset: immutable human/AI contribution history, reasoning
selection with dependency closure and global evidence references, exact review
binding, and acceptance/debt candidates. The [debt core](../../claimbranch/core/debt.py)
checks separate closure reviews against the current debt and supplied compile
observation. Its [versioned understanding-closure path](../development/workflow.md#versioned-understanding-closure-review)
also reconstructs the exact sealed cause and binds current evidence watermark,
topic rules/set and displayed context at preparation and candidate recheck.
Legacy head/time-only helpers remain separate; no old history is upgraded into
accepted authority. These are candidate values, not accepted operations or proof of
human authorization. The full versioned F0 schemas, operation inventory,
production store/gateway, provider adapter, protected authorization broker,
durable projections, and protected manuscript saga remain unimplemented. Existing disposable
probes are validation evidence, not those product components.

The [portable research history](../../claimbranch/core/research_history.py) adds
immutable candidate commands, project-global evidence events, current/historical
views, one non-nested reasoning branch and one selected merge. Corrections carry
an explicit replacement statement and reference the latest event; originals,
invalidation/retraction reasons and every prior event remain visible. This
command-level correction payload does not silently amend an Observation record.
Retraction is terminal in this bounded increment. Claim-status basis references,
typed edges and interpretation references determine selected dependencies and
paths to the manuscript anchor. Human edits retain the source Contribution
chain; complete change bodies and history are bound into merge review.

Its [generated input schema](../../schemas/research-command-v1.json) closes four
candidate commands: evidence event, branch creation, interpretation and selected
merge. Command timestamps use the whole-second RFC 3339 UTC subset. Runtime
checks additionally enforce UTF-8 byte bounds, scientific relationships, current
heads/watermarks and provenance. The finite local schema validator is not a
general JSON Schema implementation. Histories contain at most 32 commands,
three observation identities and six evidence events; a 256 KiB manifest limit
is checked before returning a new history. This deliberately lowers aggregate
capacity for the portable increment, not a product capacity claim.

Manual and recorded-AI fixture histories replay to separate byte-exact goldens
without a provider. Replay remains labeled `unverified-candidate`: it checks
structure and deterministic transitions, not signatures or trusted restoration.
These fixtures exclude episode lifecycle, protected append, receipt consumption,
compile/saga operations and committed debt closure; they do not close H0 or the
full R3 inventory. Commands and limits are documented in the
[contributor workflow](../development/workflow.md#portable-r3-review-and-debt-contracts).

The [portable lifecycle rules](../../claimbranch/core/lifecycle.py) additionally
bound episode starts/replacements, proposal cancellation/staleness/expiry, and
manuscript phase transitions against supplied head/fence/hash observations.
Restoration never counts as compilation or debt closure. These values are not
durable episode records or proof that a compiler or writer ran. The
[context compiler](../../claimbranch/core/context.py) permits only selected
project/field/sensitivity-bounded prose, excluding raw artifacts and human
export. Secret/path screening supplements trusted classification; it does not
certify arbitrary prose as public. One-shot request review binds destination,
content and lifetime; only an in-memory frozen response can dispatch. Split
dispatch/arrival retains consumed attempts while the researcher edits or
cancels. Bounded neutral response envelopes cannot supply tools or authority;
old/late responses never replace a newer draft or proposal. These volatile
[provider/draft APIs](../development/workflow.md#paper-context-and-offline-drafting)
do not implement live transport or durable trace ingress. Trace
payload erasure retains identity/digests and original contribution linkage.

The [synthetic workspace](../../claimbranch/application/workspace.py) connects
these rules to direct judgment entry, AI proposal adoption/editing, selected
merge review and escaped TeX text candidates. It reads only verified repository
fixtures, keeps drafts in process memory, and always reports zero accepted
writes. Prepared reviews expire after 120 seconds. The thin application does
not select a production store, protected gateway or manuscript adapter.
Wording candidates derive only from an interpretation in the selected closure
that has an impact path to the anchor. Omitting that interpretation, or its
connection to the claim, retains the original manuscript bytes. A conservative
anchor-review debt candidate is separate from the existence of a wording edit.

The implemented [review encoding](../../claimbranch/core/canonical.py) uses
compact sorted-key UTF-8 JSON with NFC text, safe 53-bit integers, no floats,
unambiguous ASCII identifiers, a depth limit of 16, at most 128 collection
members, and at most 256 KiB per encoded value. Research prose may be Unicode;
artifact/manuscript bytes are not normalized. Its explicit integer review times
and two supported operation types are internal to this increment; they do not
freeze the complete record envelope or replace the proposed schemas below.
The earlier broad domain draft has been narrowed to one approved saturation
wedge so the first complete contract can be exhaustive rather than nominally
general.

## Goals and non-goals

Goals:

- close every F0 semantic type, relationship, command, state, cardinality, and
  resource boundary;
- make accepted authority and AI Contribution provenance executable;
- make replay, import, projection, migration, and manuscript recovery
  falsifiable; and
- preserve a clear path to record out-of-F0 live evidence without expanding the
  contract during evaluation.

Non-goals:

- universal scientific ontology or arbitrary extension fields;
- general semantic VCS, nested branches, LCA merge, revert, or conflict solver;
- graph database or event-sourcing framework commitment;
- embeddings, GraphRAG, model memory or unrestricted graph editing;
- multi-file manuscript editing;
- collaboration or multi-user authority; and
- model/provider management.

## Decision drivers

- The first foundation must be finite enough for exhaustive positive, negative,
  crash, replay, and resource tests.
- Accepted evidence must remain global while one competing interpretation can
  branch and merge selectively.
- Human authority must not depend on untrusted request metadata or provider
  behavior.
- AI influence and understanding obligations must survive human editing.
- External manuscript writes must not inherit false atomicity from graph
  commits.
- Physical storage and UI technology must remain replaceable until spikes pass.

## Options considered

- Keep the earlier broad ontology and general semantic-VCS model. Rejected
  because exhaustive authority, recovery, and live-evaluation outcomes would
  remain undefined.
- Build a minimal agent flow first and let the schema emerge from UI behavior.
  Rejected because authority and provenance would become accidental interface
conventions.
- Freeze every future scientific type before implementation. Rejected because
  it would substitute speculation for real episode evidence.
- Close only the saturation-shaped F0 contract and count valid live cases
  outside it as product failures. Selected.

## Proposed design

### Paper argument extension under review

The [paper workspace requirements](../product/product-spec.md#7-interaction-and-visual-character)
and [ADR 0011](../architecture/decisions/0011-paper-argument-graph-workspace.md)
require more than F0's single Claim and Observation/Interpretation-to-Claim
edges. The inventory below remains the original bounded contract and regression
baseline. It does not already model a whole paper; adding a visual parent to
C-01 cannot supply that missing semantic contract.

The portable v2 candidate subset is now implemented by the same
`ResearchHistory` owner. The [seed schema](../../schemas/paper-seed-v2.json)
and [command schema](../../schemas/research-command-v2.json) are generated from
the code; cross-record constraints below are enforced during every replay:

- The seeded Claim is the single thesis. Additional Claim changes have a
  `main` or `subclaim` role, statement, scope and structural `parent_ids`.
  Main claims belong directly to the thesis; subclaims have one to three
  existing non-thesis parents. Structural containment is not scientific support.
- Explicit `supports`, `challenges` and `qualifies` edges run from an Observation,
  Interpretation or Claim to a Claim, retaining a rationale. Structural and
  claim-to-claim scientific relations must each be acyclic. Shared evidence
  retains one global observation identity. Dependency closure includes required
  claims and parents; an omitted sibling is not selected implicitly.
- `record-experiment` introduces immutable question, method, conditions,
  source reference and metric name/definition/unit/comparison. It records
  supplied metadata; it does not execute an experiment. An observation requires
  such an experiment and a measured-value string. Correction retains the run
  identity and original event/value; invalidation/retraction retains history.
- A paper may be drafted with no evidence. New claims start `proposed`;
  only an explicit candidate claim-status change sets supported/contested.
  Distinct status changes cannot target the same claim, and a contested merge
  requires a selected challenge to that particular claim. None of these values
  is an accepted research record or human-authorization proof.
- An unrun plan contains its target claim, question, conditions and metric.
  [PaperService](../../claimbranch/application/paper_service.py) derives
  `claimbranch.paper-view/v1` nodes and typed relations without layout fields.
  Its [scenario request](../../schemas/paper-scenario-v1.json) names the project,
  episode, ref, exact view digest, plan, assumed observation, rationale and
  supporting/challenging/inconclusive outcome. These are service capabilities,
  not a frozen choice of UI controls.
- Scenario reach follows only explicit scientific claim relations. It returns
  potentially affected and unaffected claims, existing basis, unchanged evidence,
  possible anchor impact and deterministic witness paths. It does not infer
  truth or negate every ancestor. Inconclusive adds no scientific relation.
  The digest binds the entire candidate history, including added experiment
  metadata even when reasoning heads and evidence watermark stay unchanged.
  Stale or cross-context assumptions are rejected; all outputs remain hypothetical.

`ResearchHistory.preview_paper_changes` additionally derives an unaccepted
before/after view from typed amendments and a complete working Judgment. Its
[request schema](../../schemas/paper-changes-request-v1.json) is a projection
contract, not a v3 history command. Dependency closure runs over the proposed
argument, distinguishing changed dependencies from retained records; omitted
amendments do not apply. The selected result is revalidated because a valid
whole proposal may have an invalid partial selection. Active evidence and
same-claim challenge requirements also apply to retained statuses whose basis
changes. Source Judgment and working Judgment keep separate provenance chains;
the current branch-level model conservatively carries any source AI influence
into review. New per-record authorship cannot be inferred from it.

`ResearchHistory.project_paper_draft` validates/projects all supplied candidate
amendments without a Judgment. It reuses the same amendment schema, identity,
endpoint, hierarchy, cycle, dependency, active-evidence and cardinality rules;
an empty amendment list is a read-only source projection. It returns the
unaccepted `claimbranch.paper-draft-projection/v1`, preserving source Judgment/AI
lineage separately rather than fabricating a new judgment. `PaperService.project_draft`
adds a digest-bound `claimbranch.paper-draft-graph/v1` with explicit draft flags.
Neither appends a command nor relaxes final selected-review completeness.
Incomplete forms remain in the application, outside a valid domain projection.

The initial session authoring owner reuses the existing
`PaperWorkspace` episode/ref/source-node draft. `PaperCandidates` holds copied
candidate records, selection, stable IDs/aliases, a mutation revision and exact
source binding separately from expiring review snapshots. Every kept candidate
mutation/reselection invalidates its session's scientific/branch reviews and
guarded child merge; it leaves independent AI proposals intact. Missing owners
are rejected, the 16-session limit never evicts previous work, and source changes
require explicit refresh/revalidation while retaining text. A changed amended
source record requires an exact previous/current/draft comparison before
rebinding; the retained draft is not silently rebased. Candidate deletion
is not an accepted operation; dependent candidates are either explicitly removed
or retained for repair. Unkeep removes a candidate from projection/selection
while retaining its text separately; ordinary edits preserve omission. The
terminal workflow owns these session-only controls.
Manual creation also covers the existing experiment-plan body: claim, objective,
conditions and complete metric, with planned status. It uses the same dependency
closure and plan cardinalities; no new evidence, execution or scenario contract
is introduced. Existing-record edits retain their narrower field policy.
No new candidate is a node-bound Judgment or ADR 0013 checkpoint target.

`PaperWorkspace` now owns explicit session references from one original
episode/ref/source-node draft to at most 16 existing nodes in the same context.
An explicit per-node choice resolves which judgment to show; the original owner,
draft ID, contributions and candidates do not move or merge. Unlinking restores
the node's own work when it was displaying that judgment. Membership changes
invalidate the owner's scientific/branch/child review while retaining independent
proposals. Link previews bind to source history and association revision;
invalid endpoints or new linked-work capacity fail before changing references.
Choosing an existing association or separate manual work allocates no review
session. Adding a reference preserves choices at previously linked nodes.
Source refresh validates
all linked endpoints before updating owned sessions. These references are not
ScientificEdges, selected amendments or accepted records. Old checkpoints still
serialize manual text at its original owner; associations remain volatile.
Provenance-preserving durable work recovery needs its separate versioned storage
contract; this increment migrates no old drafts or checkpoint schema.

The service returns potential impact along explicit scientific paths in both
graphs, with a bounded deterministic witness per reached claim per phase.
Unchanged evidence, unchanged claims and claims outside those paths are separate
outputs. No status is inferred from reach, no plan becomes evidence, and anchor
reach supplies neither source verification nor a manuscript patch. This can
inspect a merged candidate, but does not append a second merge/episode or relax
the cardinalities below. Record deletion, thesis-seed rewriting, observation/run
mutation and protected acceptance are absent from this preview API.

The v2 profile permits at most 64 commands, 32 evidence events, 16 observations,
8 completed experiment records, 16 claims including the thesis, 32 scientific
edges, 8 unrun plans and 64 branch changes. Each claim DAG has at most 8 nodes
along a path. The existing one alternative, one selected merge, one
Interpretation, one manuscript anchor, eight Contributions and 256 KiB history/
manifest bounds remain. Cardinality limits do not guarantee that every maximum
fits simultaneously within the byte budget. The source of executable limits is
`PAPER_LIMITS` in [research_schema.py](../../claimbranch/core/research_schema.py).

The separately classified synthetic [paper fixture](../../tests/fixtures/paper-argument/manual.json)
uses Model A weight pruning/quantization with defined accuracy loss against an
unchanged baseline. Its manual and recorded-AI variants have separate byte-exact
goldens and preserve original AI text/human revisions. The original saturation
fixtures, v1 schema and goldens are unchanged. There is no implicit v1-to-v2
migration: a v1 history stays v1, unknown/mixed versions fail, and a paper
candidate starts explicitly with v2. Protected-store migration/rollback,
multi-episode persistence and multiple manuscript anchors remain unresolved.

The [workspace design](2026-09-22-episode-review.md#paper-argument-workspace)
owns presentation. This increment exposes a Python service and CLI; the current
web app still uses its original single-claim example. The full production
extension remains under review before protected persistence. Human-authority,
provenance, scientific-plane and manuscript-saga invariants apply unchanged.

#### Cumulative paper episodes

The portable v3 candidate profile extends the same `ResearchHistory` owner with
sequential paper episodes. Its generated [seed](../../schemas/paper-seed-v3.json)
contains paper/project identity, thesis and the existing anchor, but no implicit
episode. Its [commands](../../schemas/research-command-v3.json) add explicit
`open-episode` and `close-episode` to the paper operations. The first is a new
candidate history, not an automatic migration of v1/v2 or an accepted store.
The older schemas, histories and frozen goldens remain byte-identical.

The separate [empty-project review preparation](../development/workflow.md#paper-and-work-association)
now retains that seed/root and the exact paper/workspace association together,
with zero operations/evidence and no implicit episode. Candidate continuation
requires the same transient owner and current association; imports cannot
install its seal. This supplies no accepted genesis or receipt, and does not
change the existing v3 seed/command or checkpoint formats.
Its separate enrolled native attestation now binds the full initial review and
derived empty effect without adopting any imported history. Closed native
parsing and the initial root/anchor checks remain candidate integrity, not
accepted genesis/source authority. Native roles now independently recheck the
associated Git directories, exact marked-file bytes/identity and private external
workspace before reporting signed success. This is read-only filesystem
validation, not scientific fidelity or authoritative accepted-history loading.
The enrolled protected target must also retain its original identity/binding
and contain no scientific/store entry. Existing or pending state is preserved
and refuses another initialization. This read-only precondition does not reserve
the target or provide the later atomic create-only publication.
Actual initial user-presence and protected
log publication remain unfinished; the linked developer API owns its use.

- Opening requires a new episode identity, title/question, current heads and
  evidence watermark, with no other active episode. It retains the current
  main reasoning, captures baseline heads/watermark and the operation clock,
  and supplies one new alternative slot. Every subsequent operation names
  that active episode. Operation, episode and research-record identities cannot
  alias each other in v3.
- Each episode permits one alternative, one Interpretation identity and one
  selected candidate merge. The alternative starts from the inherited main
  argument with a separate current Judgment chain. Selected IDs must identify
  actual amendments; dependency closure can require inherited records. The
  selected graph and retained status bases are validated again. Historical
  retracted evidence cannot supply a new selected basis, but does not prevent
  an unrelated new plan from being reviewed.
- Past Interpretations are retained with their episode identities and cannot
  be rewritten by another episode. Later episodes append their own
  Interpretations and may explicitly amend claims, relationships, status and
  plans. Prior episode Judgment chains remain separate and inspectable. A
  fresh manual Judgment does not erase inherited AI influence; the bounded
  model conservatively carries any retained source AI into explanation review.
- Closing records final heads/watermark and `merged` or `unmerged`, then freezes
  that episode's two reasoning views. Omitted alternative records stay
  inspectable and do not enter the next main implicitly. Re-adopting an archived
  omitted proposal is not an implemented transition. Closure does not claim
  experiment completion, manuscript verification, debt closure or a V0 outcome.
- Evidence remains one global append-only stream. Browsing an old episode
  shows its frozen reasoning against current evidence with a changed-watermark
  indicator. An explicit `at_operation` query reconstructs the historical
  evidence and reasoning at that command instead. Completed experiment metadata
  is never rewritten, and an unrun plan is not auto-completed by nearby evidence.

The v3 profile allows at most eight sequential episodes and eight retained
Interpretations; all other v2 limits, including 64 commands, 64 branch records
and the 256 KiB input/manifest budgets, remain. Not every maximum fits together.
`PAPER_SERIES_LIMITS` in the schema source owns these bounds. These are explicit
candidate-profile limits, not a production daily-use promise or the separate
three-valid-start/invalid-replacement V0 `EpisodeLedger` protocol.

The two frozen [manual](../../tests/fixtures/paper-series/manual.json) and
[recorded-AI](../../tests/fixtures/paper-series/recorded.json) histories recount
the same synthetic pruning observation from 0.4 to 1.2 percentage points in
episode two. Both original and corrected values survive, the original
Interpretation remains, and only the selected challenge/status/Interpretation
changes reach main. The source remains synthetic. Commands compute unverified
candidates. The v3 selected-merge review now binds the exact command, seed and
history revision, heads/watermark, before/after scientific projection, supplied
manuscript fingerprint, session and five-minute maximum lifetime. Its
`paper-review-v3` profile retains typed source Judgments from every contributing
episode as well as the current Judgment; inherited AI requires an answer or
explicit deferral. Required amendments are distinguished from references to
unchanged inherited records. The after-view is hypothetical and leaves evidence
and source heads intact.

Reconstruct the sealed review from the owned history before calculating its
candidate transition. Removing source provenance, changing selection, rationale,
answers or any history command, or using an expired review must fail. A public
digest or caller-built review is not authority. Conditional manuscript and
understanding obligations remain uncommitted candidate values. The
[volatile merge adapter](../development/workflow.md#exact-cumulative-merge-review)
does not read/verify manuscript bytes, stage an unrecorded draft, issue a receipt,
save a project or mutate its owned source. Protected persistence/recovery,
existing-project migration and multiple anchors are still unimplemented.

The separate [draft-to-branch adapter](../development/workflow.md#draft-to-branch-candidate)
now constructs the existing v3 branch/interpretation commands from an exact
active-episode draft review. It records selected amendments and required
dependencies, preserving the current recorded Contribution prefix and all prior
episode Judgments. Independent draft contributions retain their content, authors
and trace identities with newly linked parents; the combined chain is disclosed
before returning the candidate. Unselected amendments cannot silently enter the
branch. The reducer rechecks the complete Interpretation, graph and evidence
basis. Historical overlays remain hypothetical, and the adapter neither merges
main nor approves, persists or migrates history. No command schema or finite
limit changes for this connection.

The [conditional work and manuscript adapter](../development/workflow.md#conditional-work-and-manuscript-review)
reconstructs causal manuscript/understanding consequences from each recorded
candidate merge. It uses the full before/after scientific graph, including
unchanged inherited paths, rather than relying on the older finite path list.
An episode close or a later merge does not resolve or implicitly supersede prior
items. Stable work identities and source Judgments survive replay; changed
current head/evidence is explicit. These derived `pending-if-accepted` items
are not accepted Debt records and have no closure operation in v3. The owned
history remains the sole scientific source.

The understanding-return projection now resolves one existing conditional item
within an explicit project. It returns the item's causal Judgment and source
contributions, the argument immediately after that merge, and current main as
separate views. The original view is rebuilt from the causal history prefix,
so later corrections do not rewrite its observations or fingerprint. Current
main follows the latest episode; a closed cause episode does not freeze today's
paper reasoning. Head/evidence changes and any later history are distinguishable.
The projection never constructs an accepted Debt or a sealed cause review from
candidate commands. Its digest binds each bounded component's content hash and
the response metadata; it does not impose one storage-record limit on the two
full views combined. Closure and acceptance remain unavailable. Returned values are detached, and replay restores
the same projection. The [developer API](../development/workflow.md#conditional-work-and-manuscript-review)
owns its version and invocation.

The [partial-explanation adapter](../development/workflow.md#partial-understanding-explanation)
now adds a separate versioned draft to that conditional item. A deterministic
catalog binds one-to-three topics to the causal graph, selected effects and
rule version. It does not classify new accepted operations or judge answers.
Partial text and explicit references to the original rationale remain distinct
from completed answers or accepted deferral. Source changes retain the text and
its old graph basis; explicit rebinding names the current return fingerprint
without restoring any review authority. A closed bounded snapshot contains only
draft text/references and source/topic bindings, reconstructed against the owned
history on return. Blank text is admitted only by the explicit draft schema;
required scientific text keeps its nonblank constraint. This provides in-memory
reconstruction, not durable storage, a TUI control or accepted debt closure.

The separate wording review binds one manuscript item to current paper context,
a complete draft and the exact hashes of supplied UTF-8 source/postimage bytes.
It retains current source AI, requires explicit explanation/deferral where
applicable and returns only an expiring candidate. Supplying bytes does not
verify their file identity or scientific fidelity. Native authorization,
durable debt, real apply/compile/restore and human closure remain unimplemented;
no command/manifest schema or old golden changes for these projections.

#### Finite review policy and amendment lineage

The separate `claimbranch.paper-review-policy/v1` candidate profile implements
proportional review over an active cumulative paper episode. It does not
reinterpret v1–v3 commands or their older sealed explanation rules.

| Admitted action | Target | Impact | Candidate review requirement |
|---|---|---|---|
| `capture-draft` | none | low | No completed judgment or explanation required |
| `record-interpretation` | alternative | medium | Reuse the human rationale; no teach-back or UnderstandingDebt |
| `apply-selected-merge` | main | high | With AI influence, one to three contextual topics answered by text or an explicit reference to the existing rationale, or deferred; wholly manual history needs no AI explanation |

These are fixed action rules, not caller-selected risk labels. Evidence
acceptance, manuscript operations and debt closure are outside this profile.
When an alternative exists, recording must review that source; a main-based
draft cannot bypass its retained contributions. The assessment alone neither
constructs a legal accepted command nor grants authority.

`AmendmentLineage` records exact typed amendments with parent-linked revisions
and complete source Judgment snapshots, including Proposal/trace identities.
It admits the same claim, interpretation, scientific-edge, claim-status and
unrun experiment-plan shapes as paper amendments. A source may lack a completed
human rationale. The project/episode/record/kind stays fixed across revisions;
source judgments from earlier episodes in the same project remain distinguishable.
Bounds are eight revisions, eight sources per revision and 256 KiB canonical
JSON per lineage; these maxima need not fit simultaneously. Invalid changes
leave the prior value intact. Later manual edits retain earlier sources.
Restoring a hash-consistent lineage validates candidate structure, not actual
provider adoption, scientific truth or accepted provenance.

The application adapter owns registered lineages and derives selected/required
closure from `ResearchHistory`. Included amendments contribute origin; omitted
new amendments do not. Existing source AI remains a conservative inherited
floor, including when the current judgment is manual or AI is off. This does
not retrospectively narrow legacy branch-level attribution. A known lineage
must match the exact reviewed record; unrecorded edits cannot stand in for the
recorded alternative at merge review. Assessments bind the full history/view,
scientific preview, selected scope, judgment/source fingerprints, included
lineage digests, policy and contextual topics. Final disposition recomputes
those values, rejecting changed selection, relevant lineage or evidence even
at unchanged reasoning heads.
Capture has no acceptance selection: its authored scope is bound through the
registered lineages and draft projection. Recording reuses the branch adapter's
contribution join, so its judgment fingerprint includes the recorded prefix and
new human/AI suffix without duplicating shared history.
An earlier human reason may remain beside later adopted AI wording. Review
retains both exactly and never invents a human edit or grades their semantic
agreement. Preparing this candidate is not human adoption authority; eventual
foreground authorization must cover the displayed text/reason and full lineage.

Not now and every unfinished draft leave debt absent. High-impact AI deferral
reports only `opens-if-accepted`; protected acceptance must later create the
actual debt atomically. Answers are not graded and need not rephrase an existing
reason. This is an in-memory API with generated
[lineage](../../schemas/paper-amendment-lineage-v1.json),
[assessment](../../schemas/paper-review-assessment-v1.json) and
[decision](../../schemas/paper-review-decision-v1.json) schemas. The
[exact operation review](#exact-versioned-paper-operation-review) now carries
these values into a versioned request. TUI/typed proposal adoption and retained
accepted origin remain separate integration work. The [developer workflow](../development/workflow.md#proportional-paper-review)
owns invocation and limits.

#### Exact versioned paper operation review

The portable [operation](../../schemas/paper-operation-v1.json) and
[review](../../schemas/paper-operation-review-v1.json) formats are separate from
v1–v3 candidate history. Only recording an interpretation into the alternative
and merging selected reasoning into main are admitted. Capture and Not now
cannot produce an executable request. Old history readers refuse the new
format; existing fixtures are neither migrated nor relabeled as accepted.

An operation binds project/episode, a fresh operation ID, seal-derived UTC time,
expected heads, evidence watermark and source-history fingerprint. Its effect
retains exact selected/required typed changes and the actual joined Judgment.
Recording identifies a required branch-creation operation when no alternative
exists and passes the existing branch reducer's legality checks. Merge uses
the owned alternative's explicit selection and Judgment. Policy, decision and
provenance fingerprints bind those effects to the containing review.
Both operation identities must avoid recorded and registered draft identities;
branch creation also consumes its slot in the bounded candidate history.

The review keeps the full assessment and explanation decision, included
amendment lineage revisions, source judgments and original preparation scope.
It also binds a supplied manuscript digest, session nonce and a seal lifetime
of at most 300 seconds. The entire canonical NFC envelope is at most 256 KiB;
individually valid sources may exceed the combined limit, which rejects rather
than drops provenance. An optional parent-review digest is only a supplied
revision reference, not accepted history or reusable consent.

Restoration rederives every effect, source and policy value from the owner's
current candidate history and independently registered origins. It cannot
register origins embedded in imported review bytes or replace the current
assessment. An earlier intact review can be inspected while newer work remains
current. Returning an operation candidate additionally requires that exact
preparation scope and seal to remain current. Not now, a changed explanation
decision or a successful replacement seal revokes the earlier request. A failed
preparation preserves the last valid seal. A new session must explicitly prepare
the assessment and seal from its sources first; restoration reinstates neither.
Invalid replacement selection does not install a new scope or destroy the
previous valid one; a successful scope change revokes the prior seal.
Changed evidence, origins, source
history, manuscript/session bindings, expired seals and inconsistent values fail.
Schema/hash consistency alone does not prove that a person saw the review.

This is an in-memory input/recheck boundary, with authorization always required
and unverified. It writes no records and creates/closes no debt. R2/R4 still
need trusted source loading, native authorization and atomic storage of the
exact review, matching receipt consumption, accepted operation and deferred debt.
The new contextual decision must not pass through the legacy seal, which lacks
these topic and lineage bindings. Manuscript bytes remain supplied, not verified
against an original file. [Developer usage](../development/workflow.md#exact-paper-operation-review)
describes the entrypoints.

The separate [commit candidate](../../schemas/paper-commit-candidate-v1.json)
now retains that exact review with forecast resulting heads and at most two
conditional debt openings. A record advances alternative, including first
branch creation when necessary, without changing main or evidence. A merge
advances main and retains the existing single-anchor manuscript obligation;
only explicit contextual deferral adds understanding work. Each debt identity
binds kind, project, episode, causal operation and exact review digest. Its cause
head and evidence watermark remain inspectable; manuscript context and original
understanding topics have distinct bindings. These are transaction effects
awaiting acceptance, not open Debt records. The canonical envelope has the same
256 KiB bound and is rederived under the owning policy lock from the current
seal. Restore grants no authority or source adoption. No legacy command is
produced: flattening this review would lose amendment-only AI or explicit reason
references. This checkpoint selects no physical store or native trust extension.

The separate [record-transition envelope](../../schemas/paper-record-transition-v1.json)
now binds that full review to an actual unaccepted alternative-record replay,
including first branch creation when needed. Existing v3 record semantics can
represent its scientific effect; the enclosing review and full origin registry
are still retained separately rather than discarded. Before/after manifest
digests bind the derived commands to independently held source history. Main and
evidence are unchanged, omitted drafts remain unrecorded, and amendment-only AI
remains available to the next merge review. Merge replay is deliberately not
supported by this envelope: legacy explanation rules cannot express its complete
policy. No source import, seal restoration, receipt or accepted log is created.
The [developer API](../development/workflow.md#exact-paper-operation-review)
owns use and its 256 KiB/replay limits.
The transition budget and complete registry snapshot are calculated before the
seal is installed. Subsequent omitted-draft changes cannot change retry bytes.
Opt-in [v2 operation review](../../schemas/paper-operation-review-v2.json)
binds that entire snapshot digest, including unselected AI origins, while v1
review/operation formats remain unchanged and readable. The native signing
adapter now handles this record-only review as synthetic unaccepted attestation,
including its registry commitment in the full signed packet. That digest does
not establish independent origin/source authenticity; actual v2 foreground
approval and cancellation remain unobserved, and no accepted authority is granted.
Bound continuation rederives the full original review and scientific result,
rejecting missing/substituted origins; a bare legacy history is not this source.
Continuation also requires an independently retained expected review digest;
internally consistent imported hashes cannot establish that expectation.
Historical verification restores neither a current seal nor accepted authority.

#### Unaccepted work checkpoint

The [project-work envelope](../../schemas/project-work-v1.json) adds bounded
paper association snapshots around the existing unaccepted work formats.
It preserves the embedded scientific records and source history, rather than
introducing another scientific operation. The [adapter contract](../development/workflow.md#paper-and-work-association)
owns path identity, preview/recheck, explicit relocation and recovery behavior.
Association is neither source fidelity nor accepted authority.

The separately versioned [paper-work format](../../schemas/paper-work-v1.json)
now preserves the existing source history, independently retained amendment
lineages, optional Judgment, exact review and partial-explanation drafts as one
bounded encrypted checkpoint. It is not a new accepted command schema or an
implicit migration of candidate history. The loader replays sources and checks
all review/origin and explanation/cause bindings before returning work. Earlier
reviews remain inspectable but never restore current consent or an owned seal.

The portable format retains an explicit `unaccepted-work` classification and
false authorization. Physical encryption, private-file replacement and
restart behavior belong to the [developer adapter contract](../development/workflow.md#encrypted-unaccepted-work-checkpoint).
The optional [device-key adapter](../development/workflow.md#device-work-key-reopening-and-recovery)
adds a separate binary `CBWD` v1 outer profile, never a new scientific command.
It stores `CBKY` v1 wrapped data-key material and `CBWK` v1 encrypted work
atomically. The key header binds the external project fingerprint, device and
ephemeral P-256 public keys, independent salts and bounded encrypted device
representation. Device and recovery AES-GCM wraps use separate HKDF purposes;
a separately derived HMAC covers both wraps and the header. Either unwrap must
authenticate the complete envelope before exposing the data key. Work-content
encryption uses a further purpose-separated HKDF key bound to the
complete outer prefix/envelope digest, so key and content from different
restored copies cannot be spliced. Whole-checkpoint rollback is not prevented.
Ordinary
reopen requires the original device; explicit recovery creates a new device
wrap in a fresh destination while retaining unaccepted source authority.
Old raw-key readers reject the new profile. Same-host native evidence does not
establish actual device replacement or protected approval custody.

The 256 KiB aggregate bound may reject combinations of otherwise valid inputs;
no provenance is trimmed to fit. Protected accepted storage, trusted source
loading, key custody and migrations remain separate unfinished integrations.

#### Personal paper lifecycle extension (planned)

The owner requests plans for the real-paper migration issues. The selected
import/sharing policies are in [ADR 0023](../architecture/decisions/0023-personal-argument-import-and-sharing.md);
per-issue work, dependencies and checks belong to the
[existing implementation plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan).
The personal import/revision/sharing contracts implemented below do not supply
a protected schema, replace F0 or complete live validation. Initial import retains
unsupported new-type source fields; subsequent typed registration is separate.

**01 contract frozen/implemented 2026-10-13; result and Opus cross-review passed.**
The explicit `paper` profile uses research seed/commands v4, paper work v14,
project work v10, workspace v13 and `CBPP`/`CBPB` frame version 2. V1–v3
histories and legacy profile encoding remain separate. Storage uses registered
4/8/16 MiB history/derived-manifest/project budgets and at most 2,048 JSON
collection members; legacy canonical JSON remains 256 KiB/128 members. Graph
depth remains 8. The count fixture covers 64 claims (one thesis), 256 observations,
256 experiments, 512 scientific edges, 64 unrun plans, 32 episodes/Interpretations,
1,024 evidence events and 1,439 commands together; a separate 2,048-command
fixture covers operation headroom. These are synthetic capacity cases, not
scientific fidelity or user-benefit evidence. Measured performance belongs to
[the execution record](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan).

New personal projects opt in with `--profile paper`; the existing episode
profile remains the public default while later import/provider contracts advance.
The paper profile supports manual research and scoped AI-readable context, but
public provider attachment refuses before dispatch because its larger-history
origin/return integration is not yet qualified. Retained legacy AI Contribution
chains are not relabeled during a supported conversion. This does not change
current episode-profile AI behavior or widen any provider/native-review budget.

Working-state limits are explicit: 32 judgment sessions/work links, 16 nodes
per shared judgment, 64 locally selected draft amendments, three parents per
claim, eight Contributions per judgment, 1,024 notes/draft buffers and 2,048
unfinished editor entries; scientific/editor text remains 16/12 KiB respectively.
New authoring/personal-cause source references may name 2,048 history commands;
older source-reference contracts retain 64. Up to 1,024 retained byte sources
have digest/length-bound 12 KiB raw chunks; each original is at most 4 MiB, and
base64 overhead counts against the project budget. Up to 2,048 stable opaque
public-ID mappings are allocated in the saved revision and retained on later
saves; selected sharing below reuses these mappings without allocation. Store only seed/commands,
writing, original sources and mappings; manifest/graphs are derived.

Read-only registered anchors and descriptive wording/companion restrictions
are implemented below. Typed observations are implemented below; protocol/gate records are implemented below; private critiques are implemented below; selected Git-share export is implemented below. Co-report
decisions are implemented below.
Historical source decisions and imported-origin personal reasoning are available
under the v5 contract below. Their proposed counts are not supported types
merely because the storage codec can hold their bytes. The base source association retains its single original marked anchor;
additional named bindings are registered separately below. Conversion requires a fresh private
destination, preserves the original checkpoint as an exact retained byte source
and changes no scientific content. Source-bound unfinished scientific work,
retained proposals and conditional work that cannot be losslessly rebound refuse
conversion before publication; ordinary notes/judgments retain their Contribution
chains and never restore prior consent. The source project remains usable.

**04 implemented personal reporting contract (2026-10-14).** Commands v7
`set-claim-wording`, `set-claim-companion`, `set-anchor-context` append to existing
seed4/5 histories without rewriting prior bytes or changing scientific support
status. Current-main human descriptive policies carry grade, limitation, allowed
wording, required caveat text, banned phrases, allowed placements and reason.
One canonical companion record carries target claim, companion claim/global
observation, anchor/paragraph scope, active/retired disposition and reason;
endpoints/scope are immutable, reviewed retirement/reactivation appends history.
These reporting constraints are not branch-local evidence or scientific support.
Unknown/AI imported source references remain separate from local confirmation.

Anchor contexts bind explicit placement and blank-line paragraph declarations
to the exact registered anchor/source commitment. Re-registration/relocation
requires new classification; stale context does not retain a passing placement.
The read-only literal lint and graph readers disclose incomplete source/TeX/
paragraph coverage, and no result closes debt. Missing branch endpoints are
reported without dangling reporting relations. Work17/project13 and personal
frame5 preserve these commands; existing workspace13–15 fields remain unchanged.
Budgets are 64 policies, 256 companions, 64 contexts; co-report decisions
are implemented below. See the [authoring and lint workflow](../development/workflow.md#human-wording-limits-and-reporting-companions).

**07 implemented personal co-report contract (2026-10-14).** Command8
`record-co-report` directly records one explicit current-main personal disposition
in an active episode without a staged alternative/earlier selected transaction.
Two to four selected Interpretation identities carry scoped statements, active
global observation basis, explicitly authored scientific relationships and
original-reading references. One human judgment/reason and 04's canonical
companion identities bind the whole selection; omitted candidates remain
unadopted input with reserved identities. Relevant companion membership and
current context are checked before append. Group links are non-scientific.

A later edit creates new identities referencing the immutable earlier reading;
original AI/unknown influence is retained from recorded source lineages and
archived episode judgments. Main support status/evidence values remain unchanged.
The outcome `co-reported` is distinct from legacy `merged`. The new extension
admits 128 local Interpretations and 32 co-report decisions; old histories and
single-reading rules remain unchanged. Work18/project14/frame6 retain exact
commands while workspace13–15 fields stay unchanged. Graph readers disclose
scope, shared reason, membership/origins, explanation choice and unresolved
manuscript work. This neither certifies understanding nor supplies protected
approval/provider capability. See the [co-report workflow](../development/workflow.md#co-reported-interpretations).

**Version and budget approach.** Keep v1–v3 seed/command/manifest/golden bytes
unchanged. Introduce a new explicit version with a registered personal paper
profile; never add profile fields to an old frozen seed or accept a caller's
arbitrary numeric limits. Use a purpose-bound bounded encoding/decoder with the
same canonical text/key/number semantics, separate from the legacy encoder.
Old operation/review/provider budgets do not grow merely because storage grows.
New personal checkpoint and backup frames have distinct version prefixes from
legacy `CBPP`/`CBPB` version 1 (implemented version 2), even for small files. The actual
shipped old readers must reject minimal, large and backup new-format samples
without changing source/canonical records; transient lock cleanup is checked.
Normal newly created personal paper projects select the registered lifecycle
profile after its release checks; synthetic commands and existing projects retain
their frozen profiles. Unknown versions/profiles refuse before installation. Any old personal project
conversion is previewed, create-only and retains its source; protected/encrypted
stores are not converted by this path.

Registered 01 ceilings and explicitly deferred type budgets (synthetic combined
validation does not establish scientific fidelity or user benefit):

| Resource | Initial personal-paper ceiling |
|---|---:|
| claims, including one thesis | 64 |
| observations | 256 |
| completed experiment records | 256 |
| scientific edges | 512 |
| unrun plans | 64 |
| sequential local episodes | 32 |
| retained local Interpretations before co-report extension | 32, still one per local episode |
| historical source decisions | 256, separate from local merge commands |
| manuscript anchors after anchor extension | 64 |
| commands / evidence events | 2,048 / 1,024 |
| reasoning changes | 1,024 |
| scientific/structural graph path depth | 8 |
| normalized history input / derived manifest | 4 MiB / 8 MiB |
| total saved private project, including retained source and critique | 16 MiB |
| individual normalized scientific text | 16 KiB; larger originals retained in bounded source storage |
| generic new-profile collection/object members | 2,048; narrower per-field limits still apply |
| canonical JSON nesting | retain 16 unless a concrete new wrapper proves a required change |

Persist normalized seed/commands, retained source/origin registry and working
state; compute the manifest/views from them and retain only their commitments,
not a second full persisted manifest. Original source bytes are distinct
from normalized science: digest-bound base64 chunks of at most 12 KiB raw bytes
(16 KiB encoded ASCII) retain raw byte digests and exact reconstruction. Encoding
overhead counts against total saved storage. A retained blob is stored once and
referenced by source identity; unmapped pointers cannot duplicate its full bytes.
The history-input budget covers normalized commands/seed, the derived-manifest
budget covers its output, and the total-project budget covers every saved field,
including encoded originals and editor/origin overhead.

The combined 01 inventory is frozen above. Additional later-type
ceilings are 1,024 retained source records, 8,192 unresolved pointers total with
at most 128 per source record, 256 cells and 16 condition keys per observation,
2,048 anchor associations, 256 companion records, four readings per co-report
Decision, and 128 private critiques/questions. Partition pointer indexes into
bounded source records so no individual 2,048-member collection is exceeded.
Export selections cannot exceed the eligible saved profile and their declared
closure. Parent/contribution/session limits are individually audited and frozen;
unimplemented type counts remain proposed engineering bounds, not evidence of capacity.
Each later type increment extends the same combined fixture and rechecks project
bytes/time/RSS, save/fsync and backup/restore instead of relying on 01-only data.

The implemented co-report extension admits up to four local Interpretation
identities per reviewed decision and at most 128 per project. Raw source, corrections, origins,
editor buffers, views and enclosing envelopes compete for the saved byte budget.
A maximum record count does not guarantee all maxima fit together. Report each
used/limit dimension and the first overflow before publishing. Count historical
source groups, local episodes, experiments versus inventory IDs, structural
parents versus scientific edges, and decisions versus judgments separately.
Additional draft/parent/contribution/selection/reference limits are inventoried
and frozen before implementing the new profile; no silent inheritance or
truncation resolves a mismatch.

**Import and origin.** A closed interchange envelope identifies its version,
source bytes/digest, explicit ID/type/field mapping, mapped science, source
chronology and complete retained/unmapped pointers. Unknown source fields can
remain inert data inside bounded source retention; unknown scientific command
fields, invalid endpoints, malformed values and impossible mappings cannot.
Use a bounded JSON parser with duplicate-key/encoding/depth/count checks before
normalization. Preserve original bytes independently of canonical NFC mapping.
No model, executable converter, recursive scan or artifact read is triggered.

The first 02 slice now implements `claimbranch.argument-import/v1` and its
read-only preview. The [generated schema](../../schemas/argument-import-v1.json)
and [operator procedure](../development/workflow.md#prior-argument-mapping-preview)
own the executable input and command. Each mapped body leaf names an explicit
source pointer and optional transformation; declared origins remain separate
from imported transport and local authority. Original JSON admits inert finite
numeric tables while mapped science stays under closed typed fields. All original
bytes remain in the envelope's digest-bound source, and untouched source leaves
are exposed in 128-pointer pages (maximum 8,192 leaves). A container summary does
not resolve its children. Traversal checks 2,048 bytes per pointer and 1 MiB of
total pointer text before collecting another leaf. Diagnostic storage retains
512 errors with an exact total/truncation flag; any error refuses registration.
The inspection digest binds exact envelope/source bytes and selection/counts,
without duplicating a near-limit input into another saved-project envelope.
Selected historical decisions disclose mapped referenced records as dependencies;
they still create no historical app episode. Preview errors refuse registration, with no store,
artifact or provider access. Current schema-v4 histories/checkpoints are unchanged;
research v1–v4 bytes stay unchanged. The next 02 slice now adds research v5,
work v15, project v11, workspace v14 and personal/backup frame version 3.
V5 seeds a source-claimed current argument without synthesizing past commands,
human Contributions, receipts or local episodes. Source decisions retain reasons,
dates and known/unknown authorship separately. The foreground registration starts
only one new local question. Project v11 retains the exact input (at most 4 MiB)
as a digest-bound source; reopening compares seeded records with that input.
The inner original remains exactly reconstructable. A two-entry process-local
cache retains immutable source re-derivation, never consent or writable state.
Only identity mappings count as covered; declared transformations stay unresolved.
Views/nodes expose source-claimed status, origin, original body and paged unresolved
pointers; graph/workspace budgets are checked before publication. Private save,
writing, independent evidence/correction and backup return preserve these fields.
V5 adds explicit create-imported-reasoning-branch, record-imported-interpretation
and apply-imported-merge operations. Their exact source subject and dependency
references (source digest, declared contributor and unresolved count) are
recomputed during replay. Selected and required source ancestry survives human
rewriting; omitted independent candidates add no origin. Foreign AI/mixed/unknown
sources are separate from actual local human Contributions. Known AI influence
and unknown authorship require an explicit personal explanation choice; this
does not certify understanding. Up to 32 recorded explanation consequences and
64 partial causal writings survive return. Legacy semantic operations remain
refused on v5 so they cannot bypass this origin contract. Public provider/context
and protected authority remain unavailable. Later revision/sharing types are
planned. Immutable prefix/cause/branch calculations have bounded 16-entry caches;
science results return detached copies, never consent. Private originals are
read on demand at unresolved nodes, outside scientific/provider projections.

The current human/AI-only Contribution schema is unchanged for old versions.
New historical-source origin distinguishes declared human, AI, mixed and unknown
contributors from transport (`imported`) and the present human's local import
confirmation. A reviewed personal batch may register the selected mapped
observations/reasoning without individual retyping. Retain original reasons and
source-claimed dates/closed episode groups; do not synthesize former app commands,
receipts, source checks, protected approval or a comprehension verdict. Missing
historical snapshots stay missing. New local episodes start from the current
imported argument under normal current-state checks.

A selected mapped record failing its required typed/endpoint/consistency checks
refuses the batch. The person can explicitly deselect it into retained source-only
state; the next preview shows which dependent edges/statuses must also be omitted
or repaired, then requires confirmation of that new closed selection. Unsupported
fields outside the mapped scientific contract can remain inert retained fields;
malformed selected science cannot silently downgrade itself during publication.
Foreign AI declarations remain historical-source record types, not fabricated
owned Proposal/ExecutionTrace records with absent IDs or invented digests.

Partial migration retains the whole bounded input and unresolved field pointers
through restart/backup. Review and node/source readers expose relevant unresolved
meaning; supported status, protocol validity or scientific scope cannot be
inferred from it. An operation requiring unsupported typed semantics refuses
that operation without blocking independent complete records. Later typed mapping
is an append-only, reviewed transformation of the retained source revision;
re-import cannot overwrite later app edits. Ordinary import origins and private
retained fields do not automatically become eligible AI context or share data.

**03 source/replay contract (implemented subset, 2026-10-14).** Keep
existing seed v4/v5 and every prior command byte. Registration uses the separate
v6 command contract, admitted only in personal v4/v5 histories; it cannot carry
scientific or protected operations. Retain stable anchor id/kind, exact private
file/root/Git identity and revision, full file digest, exact bounded marked-block
bytes/digest, explicit expresses/plots/caption-parent references and human reason.
Only current main claims and globally recorded observations may be referenced;
plots is a reference, never support. One caption may reference a registered
figure/table. The legacy seed has no typed kind; its first explicit registration
assigns one, and subsequent registrations preserve it. Registration revisions append; removal of all associations retains
the earlier record and old impact reach. No scientific/evidence head is advanced.

New workspace v15/work v16/project v12 and personal/backup frame v4 retain mixed
old commands and v6 registration without rebasing prior reasons or origin source
prefixes. Old readers reject the new envelope/frame before writing. Support both
manual paper and imported paper histories. Legacy single-anchor projections
remain identical until explicit registration. At most 64 anchors (including the
initial one), 2,048 current associations, 2 MiB per selected TeX file and 64 KiB
per marked block; existing history/manifest/project budgets still apply. Named
source inspection traverses no includes and certifies no graphic fidelity.

Scientific reach plus inverse expresses/plots/caption-parent uses supplies bounded
deterministic witnesses across old/new views. Structural part-of never implies
scientific impact. Freshness distinguishes unchanged file, unchanged block with
changed file revision, changed block, identity substitution and unavailable
source. Source status is separately inspected, not injected into deterministic
replay. Foreground personal comparison binds registered-source status and rejects
an intervening source change. Missing source remains unresolved with writing
intact; no manuscript write or protected authorization is introduced.

**Revision semantics to implement in later steps.** Anchor records have stable
identities, explicit text/figure/table/caption kind and declared source location;
marked-block digests determine block freshness, while file/root identity and file
revision remain explicit path-substitution/coverage inputs. An unrelated text edit
does not pretend every block's bytes changed. Source/selection changes still
revoke dependent exact reviews, and no protected whole-file guarantee is relaxed.
`expresses` and `plots` associations are references, not support strength.
Impact uses scientific reach plus inverse anchor associations and both old/new
paths. Structural containment alone cannot infer a scientific consequence.
One companion-dependency record holds the target, referenced companion,
anchor/paragraph scope and human reason; wording policies and co-report
Decisions reference it instead of maintaining competing obligation stores.
Grades remain descriptive human-authored limitations, distinct from status or
understanding scores.

**06 contract frozen/implemented 2026-10-14 — personal structured measurements.**
Strict command9 appends `declare-condition` and `record-measurement` to seed4/5
histories. Work19/project15/personal-checkpoint and backup frame7 preserve old
seed/command bytes, workspace fields and ordinary private authority. The input
is `claimbranch.measurement-input/v1`, generated from its closed owned schema.
No arbitrary observation metadata, scheduler or provider mode is enabled.

Up to 32 immutable condition keys declare 1–64 opaque values and up to 16 named
ascending groups. Group order is human-declared protocol order, not lexical
sorting or scientific verification. Tables have a new measurement ID, an
estimand, flat declared condition tags, 1–32 typed columns with raw/display unit
labels, 1–256 rows and at most 2,048 cells, at most 256 KiB per table. Every row
contains exactly one stable-ID cell per column; explicit missingness includes
its reason. Integer/decimal values use bounded exact strings (no floats or
exponents); text and missing are separate variants. Decimal precision and sign
are retained as written. Display units label intended presentation, without
implicit numerical conversion. Table/row tags cannot conflict. Row and column
IDs are local to the table; cell IDs retain their meaning within an observation's
entire recorded measurement history. Changed estimand, column definition or
combined conditions requires fresh cell IDs as well as a new measurement ID.
No old cell can be reintroduced under a different meaning after retirement.

An explicit personal confirmation creates a new observation. `transform` attaches
a reviewed table to an existing active text/imported observation without inventing
an experiment or resolving original unmapped fields. `correct-cells` appends
only named value changes against the latest evidence-event revision and retains
all other cells, conditions, units and statement. `transition` appends a new
measurement identity and explicit changed meaning. Both retain the prior table,
reason, source context and source-claimed origin. Generic text-only corrections
refuse on structured observations; invalidation/retraction retains the last table
and marks its basis inactive. Neither table editing nor transform revives inactive
observations. Existing 1,024-event/4 MiB history and 8/16 MiB manifest/project
limits also apply; not every independent table maximum fits simultaneously.

Supporting-evidence queries follow declared support and Interpretation basis,
return matching rows with exact units, estimand and source references, disclose
unstructured/inactive/hidden basis, and preserve one observation identity. Their
local graph and derived condition coverage never rewrite human claim scope.
`dose=max` requires a named declared ascending group; no universal dose hierarchy
or lexicographic maximum is inferred. Conditions do not become graph nodes.

At most 16 artifact references retain declared path/hash/JSON pointer plus
optional tool hash and commit. These remain source claims. An optional explicit
check opens only one selected regular single-link file (at most 1 MiB), walking
without symlinks, checks read/path revision and hash, then one declared JSON
pointer against one named cell. JSON numbers compare exactly; bounded depth,
duplicate-key and nonfinite checks fail visibly. It writes no file/evidence,
follows no links, certifies no units/conditions/estimand/source fidelity and caches
no scientific-verification verdict. Changed/missing/mismatching bytes stay visible.
The existing TUI source reader exposes complete measurement/history; the public
CLI owns exact paged table registration and condition/local-graph queries.
**05 contract frozen/implemented 2026-10-14 — personal protocols and rule-bound assessments.**
Strict command10 adds `register-protocol`, `associate-experiment`,
`amend-gate-rule`, `record-gate-result`, `record-outcome`; work20/project16 and
personal/backup frame8 preserve older bytes and unchanged workspace fields.
The closed `claimbranch.protocol-input/v1` schema owns all input fields. A
protocol freezes a current main plan's scientific digest/snapshot, prediction,
falsifier, prewritten pass/fail wording, optional commitment reference/claimed
time, seen/unseen/unknown disclosure, declared origin/source context and up to
16 named gates (tolerance/reference text). Commit/chronology is source-claimed,
never proof that outside results were unseen. Imported annotations do not alter
its scientific plan digest; unsupported original fields are not marked resolved.

Protocol versions explicitly supersede their plan's latest version. Prior
versions remain inspectable; a superseded version cannot gain a fresh completed
association or gate amendment. Existing associated original rules can still have
explicitly version-bound historical assessments. One completed record is
explicitly associated per protocol version, with exact current registered-plan
digest. This executes no experiment. Metric mismatch, already-recorded results
and an unseen claim beside preexisting app observations stay visible rather than
becoming validated preregistration. App record order is not outside chronology.

Gate amendments append against the exact latest gate-rule version with new
reference/tolerance, one human reason/source and before/after/unknown disclosure.
Their local operation is the decision ID, separate from any imported past decision
or protected approval. Original registered failure/rule remains. App-recorded
results preceding amendment are explicit, including a conflict discovered when
a completed record is associated after the amendment; a conflicting before-result claim is
flagged, never silently repaired. Gate results name one exact gate/rule revision,
completed association and latest active observation-event revisions. Outcome
assessments select exactly one version for every gate, retain the same exact
observation basis, and optionally cite one matching assessment per gate.

Prediction consistency (`consistent`, `not-consistent`, `inconclusive`,
`stopped-at-gate`), discrimination and gate validity are independent. Stopped-at-
gate requires a recorded failed gate on this basis; a non-discriminating outcome
requires its limitation. Consistent prediction cannot certify a valid result:
failed/incomplete/unknown/reported-pass/no-declared-gates status and unassessed
IDs are separately visible, always with `validity_verified: false`. Partial gate
reports and zero-declared-gate protocols disclose coverage instead of fabricating
passes. No arbitrary evaluator or automatic claim status is introduced.

Up to 128 protocols/associations, 256 gate amendments/outcomes and 512 gate
results fit only within the existing aggregate 2,048 commands and 4/8/16 MiB
history/manifest/project budgets. Independent maxima are not a simultaneous
capacity promise. All record/gate identities are reserved. Metadata advances the
main context head and invalidates old exact review without changing evidence,
claim status or prior judgment. Corrected/retracted basis marks earlier assessment
stale while retaining its snapshot; newer rules are shown beside original rules,
not as an overwrite of their outcome. Current plan mutation is compared against main at the requested history prefix.
The displayed branch separately reports plan visibility and its match to the
registration, including an absent or older plan; neither becomes a false mutation. Plans and scientific-path/Interpretation
basis expose original/current protocol context. Structural containment alone is
excluded. Protocol registries remain global like evidence in closed reasoning
views; `at_operation` selects an exact history prefix, not source-claimed time.

Known AI/mixed/unknown declared protocol or imported-plan origin remains separate
from local human Contributions and cannot become AI-free by writing a new human
judgment. The current conservative branch-wide review policy may require a fresh
explanation choice for later independent manual work; this is no understanding
score or debt closure. Private save/open/backup retains context and unfinished
writing. New-profile provider use remains refused before credentials/dispatch;
this extends manual/AI-readable graph context, not a qualified provider field
set or permission to transmit raw protocol/source content.

**08-critique contract frozen/implemented 2026-10-14 — private sourced questions.**
Command11 records private critique questions, bounded revisions and non-empirical
associations in personal seed4/5 histories. Work21/project17/personal and backup
frame9 preserve old bytes/authoring fields. Closed `claimbranch.critique-input/v1`
capture includes one human-written question, review/colleague/self-audit source
classification, separate question/source human/AI/mixed/unknown origin, raw
original (up to 256 KiB UTF-8) and optional identity/private label. Retain the
exact capture-input bytes only in project17 `critique_sources`, with the existing
bounded digest/chunk format; raw original fields are never automatically copied into scientific commands,
graph, TUI default source reader or provider fields. Owner-authored question
prose is separate and remains uncertified for anonymity. This is ordinary unencrypted private
storage, not a confidentiality/anonymity verdict. Opaque random critique/source
IDs are not derived from text; opaque public mappings remain distinct.

Up to 128 private questions, 32 revisions per question and 512 associations are
bounded by existing 2,048-command/4 MiB history/8 MiB manifest/16 MiB project and
2,048 public-mapping limits. Independently specified maxima need not fit together.
Normalized-equivalent capture retries refuse despite different JSON formatting;
exact original bytes remain preserved. Registry validation checks exact reference
coverage, original hash/content association and normalized duplicate identity.
Private originals cannot be dropped, replaced or added as unreferenced records.
Question revisions append against the expected previous revision, retaining every
question/origin/reason and original. Known/unknown source influence stays separate
from local Contributions and follows the conservative branch-wide explanation
policy without fake AI Proposals or any understanding/resolution claim.

`questions` links reference current claims. `addressed-by` links reference a
current unrun plan, a recorded experiment or an exact selected/required accepted
claim/status amendment or current wording consequence. Unchanged dependencies
in a merge are not claim changes. References remain non-scientific, never support,
confirmed observations or automatic resolution. Explicit references to preexisting
work are valid: association metadata separates change-before/after-app-capture,
unknown and ordinary existing-record reference. App order cannot prove when a
private critique existed outside the app or what motivated an experiment. Main
context head changes revoke prior exact review without rewriting science.

Only explicit `critique-original` reads the private capture input. Neutral listing
and graph/preview omit private labels/identities/source hashes/source handles;
owner-authored question/reason prose is not automatically certified anonymous.
The default critique-reference projection emits only saved opaque public IDs,
non-scientific relation kinds and omission markers; it excludes all questions,
reasons, origins, private source handles/hashes, originals and identity/path text,
even if the person pasted a known secret into a question or rationale. It is a
small safe-reference projection, distinct from the selected canonical-share mode below.
Full readable project JSON export refuses critique-containing histories before
writing a file; explicitly private backup/restore still retains originals. Provider
attachment already refuses paper profiles before lookup, and the context compiler
independently refuses critique-bearing histories before preparing model content.
These restrictions do not enable new egress or imply protected authority.

**Personal origin/batch extension.** Command12 reuses the closed
metadata payload set with a separate required `contribution_origin`. Prior command
versions retain their old bytes/replay meaning. Work22/project18 and private frame10
carry the new history; workspace13–15 fields remain unchanged. A derived bounded
metadata-origin registry retains source-independent declared origin, subject IDs,
operation/time and a separate, explicitly unverified personal confirming actor. AI/unknown influence enters
later review without fabricated AI proposals or human Contributions. New co-report
input checks that influence before admission. Public source summaries retain these
origins while their raw input/operation source stays private.

Metadata-batch/v1 prepares at most256 explicitly selected ordered entries through
existing type validators. Prerequisites are explicit/current, no inference or
silent promotion. Any invalid selected entry blocks the entire candidate save;
unchanged base originals/unresolved pointers remain. Raw batch source stays in
private retained storage, including omitted requests; readable complete exports
refuse this new history, private backup and selected sharing stay distinct. The
existing terminal action connects file entry and complete foreground review to
one saved-write boundary; it is not automatic historical ingestion or a full
per-type editor. No new runtime/provider/protected permission is introduced.
The [registration workflow](../development/workflow.md#extended-metadata-registration)
and existing ExecPlan own observed checks and remaining release limitations.

**Implemented selected sharing contract.** `canonical-share/v1` projects seed4/5
current-main records through saved public-ID mappings with strict per-kind field
allowlists. Explicit selection plus disclosed dependency closure includes incoming
science, parents, mandatory companions/co-report membership and linked protocol
failures/amendments. Separate record-level reason IDs opt in; raw critique prose
has no reason opt-in. Current cells/units/conditions and human scientific limitations
stay readable. Table-local row/column joins are numeric coordinates; scientific
condition labels remain selected prose, not public record-reference IDs. Registered
anchors share structure only. Origin summaries retain adopted-record AI/unknown
and unresolved
counts. A separate branch-AI-context flag cannot change individual origins;
unmerged or omitted alternatives confer no main-record influence. Omitted originals
are not verified. The omission manifest excludes old
value/decision history, source/payloads, private paths/artifacts, manuscript bytes,
notes and unselected writing. Known private literals in allowed scientific prose
refuse rather than silently redact its meaning.

The pure projection allocates no mapping or private state. A keyed commitment over
the exact public projection using the private saved-revision digest allows
recomputation with that specific private source without publishing raw source
hashes. Exact bytes, selection, policy or saved-source changes cannot verify under
an older commitment. It is neither a signature nor standalone public verification.
Create-only publication binds the reviewed destination parent, rechecks private
saved state/selection and never replaces an existing file. Git is an allowed
sharing destination, with no commit/upload/import-back authority. Private backups
are separate. The [sharing workflow](../development/workflow.md#selected-canonical-git-sharing)
owns commands, field coverage and operational limits.

**Sharing and private critique.** Critique/source-question records are not
empirical observations. The selected private-original policy retains raw content
only within ordinary private saved-work storage/backup. Public and provider
projections use explicit field allowlists, exclude originals/identities/private
paths by default, and preserve redacted references with non-content-derived
stable identifiers. An explicitly selected reason is allowed in share output;
private source exclusion wins even through nested origin, derived text, labels
or diagnostics. The export commitment binds schema, saved source revision,
selection/dependency closure, redaction policy and output digest. Verification
recomputes that projection, not a purported full restore from public data.
Allocate opaque public record/reference IDs when a record is created or explicitly
converted, and save the mapping in that revision. Export/verification allocate no
IDs and mutate no private state. Every structured ID/reference is projected through
that mapping, including selected records with content-bearing internal IDs.
User-provided labels/prose remain explicitly reviewed content; the system cannot
certify anonymization of unreported private wording. Selected AI context carries
only safe opaque unresolved flags/counts, not raw source bytes, private pointer
names or direct quotes. Eligible unmapped scientific content would require its own
explicit selection and exact wire review; raw critique stays outside this planned
provider field set.

Freeze exact record/command/retention schemas and their generated resources at
each implementation increment. These proposed records do not alter legacy
meaning or receive protected authority through their existence.

## 1. Logical planes

The model uses the three planes accepted by
[ADR 0006](../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md).

### 1.1 Canonical scientific plane

Accepted append-only evidence events, branchable reasoning, Decisions,
Contributions, ReviewBundle/receipt references, debt, anchors, patch-saga
results, refs, and DomainOperations. This plane alone defines accepted research
state.

### 1.2 Context/retrieval plane

Rebuildable current/historical views, typed neighborhoods, full-text indexes,
summaries, and future retrieval derivations. It contains no independent
accepted fact.

### 1.3 Execution-trace plane

Non-authoritative Proposals, revisions, request/response/tool manifests,
attempts, timing, cancellation, retention, and payload availability. This
plane is auditable but does not endorse its content.

## 2. Global invariants

### INV-1: accepted evidence is branch-independent

Every accepted ArtifactRef, Run, Observation, and EvidenceEvent is visible from
every reasoning ref at the applicable evidence watermark. Branch creation,
archive, or selected merge cannot hide or delete it.

### INV-2: evidence changes append events

Confirmation, correction, invalidation, and retraction append EvidenceEvents.
No command edits an accepted artifact, Run, Observation, or prior event in
place.

### INV-3: accepted state changes only through a closed operation

The trusted gateway validates and atomically appends a known DomainOperation.
No raw record write, caller-selected actor, provider output, projection, import,
or internal field update is an alternate accepted-write path.

### INV-4: relationships are typed records

Every scientific relationship uses the closed table in section 5 and retains
its source, target, rationale, conditions implicit in the typed fixture fields,
creation operation, and evidence watermark. Topology or similarity alone cannot
create an accepted edge.

### INV-5: AI influence is never erased

Every AI-influenced accepted DomainOperation references the immutable Proposal
and a gap-free ordered Contribution chain. Human edits add Contributions; they
do not relabel the result purely human.

### INV-6: human authority is cryptographic and state-bound

Every human-only accepted action consumes one unexpired, single-use receipt
bound to the sealed review, project, episode, expected heads/file state,
operation, impact, provenance, rationale, and teach-back disposition. Request
metadata never substitutes for the receipt.

### INV-7: selected merge is explicit and dependency closed

F0 copies one named selection plus its mandatory dependencies from one
non-nested branch to main. It records omitted work and does not mutate the
source branch.

### INV-8: graph acceptance and manuscript verification are distinct

A graph operation may open ManuscriptDebt. Patch preparation, file application,
compile verification, restoration, and human closure remain separate durable
phases.

### INV-9: projections and providers are disposable dependencies

Deleting every projection or disabling every provider cannot alter or make
accepted state unreplayable.

### INV-10: import cannot inherit authority implicitly

Untrusted history is verify-only in a new isolated store. Trusted restore
targets a new empty store and verifies a signed manifest chain, enrolled public
key, known schema/rules, hashes, and every receipt. F0 has no import-to-live-
project merge or promotion path.

## 3. Common record contract

Every canonical record has:

| Field | Rule |
|---|---|
| id | stable unique string within the project |
| kind | closed enum selecting its schema |
| schema_version | known version; unknown versions fail before append |
| project_id | exact project authority boundary |
| created_operation_id | immutable creating DomainOperation |
| created_at | RFC 3339 UTC supplied by the deterministic clock port |

Every record and command payload validates against versioned JSON Schema with
additional properties forbidden. Schemas close primitive types, enums,
nullability, numeric ranges, strings, collections, and cross-record
invariants. Indexes may add physical fields outside canonical serialization;
they cannot add semantic fields.

Canonical JSON uses fixed UTF-8 normalization, object-key order, number format,
enum spelling, null treatment, and hash exclusions. Tests inject clock, IDs,
nonces, signing key, compiler fingerprint, schema/rule versions, and production
entropy recordings. Replay never regenerates them.

The immutable operation/event log is authoritative. Ref heads and lifecycle
values are deterministic projections, not mutable fields inside prior hashed
records.

## 4. Closed record inventory and cardinality

| Record kind | Required type-specific fields | H0 exact / V0 per-valid-episode bound |
|---|---|---|
| ResearchEpisode | eligibility_rule_version, baseline_ref_heads, baseline_evidence_watermark, opened_at | H0 exactly 1; V0 project 0-6 total, first 3 valid starts when available and at most 3 invalidated replacements |
| ArtifactRef | uri_or_relpath, sha256, media_type, sensitivity | exactly 2: result and manuscript |
| Run | run_key, method_ref, started_at, completed_at, status | exactly 1 completed |
| Observation | statement, value_or_category, units, run_id | exactly 3 |
| EvidenceEvent | action, target_id, rationale, nullable supersedes_id | exactly 3 confirmations plus at most 3 correction/invalidation/retraction events; total 3-6 |
| Claim | statement, scope, status | exactly 1 central Claim |
| Interpretation | statement, branch_ref, evidence_watermark | exactly 1 |
| ScientificEdge | edge_type, source_id, target_id, rationale | 3-6 from the closed edge table |
| ExperimentPlan | objective, claim_id, status | zero or one |
| Decision | decision_type, selected_ids, rationale, branch_ref | 1-3 including selected-merge Decision |
| ManuscriptAnchor | file_relpath, marker_id, fingerprint, expected_file_hash | exactly 1 |
| PatchIntent | anchor_id, expected_file_hash, replacement_digest, reason | exactly 1 |
| PatchAttempt | patch_intent_id, snapshot_digest, result_file_hash, compile_config_id | 1-3; happy path has exactly one verified result |
| ManuscriptDebt | anchor_id, cause_id | exactly 1 identity; lifecycle is projected |
| UnderstandingDebt | accepted_operation_id, review_bundle_id | manual 0; recorded exactly 1; lifecycle is projected |
| DomainOperation | episode_id, operation_type, actor_class, expected_ref_heads, evidence_watermark, payload, idempotency_key | 1-32 accepted transitions, at most 24 receipt-authorized |
| Ref | name | exactly 2: main and one non-nested branch |
| SelectedMerge | source_ref, target_ref, base_operation_id, selected_ids, closure_ids, expected_heads | exactly 1 |
| Proposal | episode_id, nullable parent_proposal_id, intended_command, normalized_payload, trace_manifest_id | manual 0; recorded 1 root/0 revisions; H1/V0 0-3 total, one root plus at most 2 human-requested revisions |
| Contribution | target_operation_id, sequence, contributor_class, action, nullable proposal_id | 1-64 per episode, at most 8 per target; proposal_id required for AI influence |
| ReviewBundle | episode_id, revision, nullable parent_bundle_id, draft_operation_digest, expected_heads, impact_digest, provenance_digest, rationale, teachback_disposition, sealed_at | one immutable sealed revision per authorization; at most 3 revisions per command and 72 per episode |
| AuthorizationReceipt | review_digest, project_id, episode_id, session_nonce, authorized_operation_id, expected_heads, issued_at, expires_at, signature | exactly one per authorized command, at most 24; unique operation proves single consumption |
| ExecutionTraceManifest | request_digest, response_digest, model_identity, tool_context_digest, payload_availability, retention_class | manual 0; recorded 1; H1/V0 0-3, exactly one per provider-produced Proposal/revision |

Cardinality counts identities created by an episode, not preexisting records it
references or append-only transition attempts. Every DomainOperation carries
episode_id and every canonical record derives its episode from
created_operation_id.

Start-episode atomically creates the preallocated ResearchEpisode ID and its
root operation, avoiding circular identity. H0 variants use separate stores.
V0 uses one cumulative live project, at most one active episode, and recorded
starting refs/watermark. An episode may reference an earlier Claim without
recreating it.

The fixture may omit ExperimentPlan. No other record kind or extra branch is
admitted. A valid episode exceeding any maximum is out-of-F0, incomplete, and
not eligible for replacement.

## 5. Closed relationship inventory

Every relationship is a ScientificEdge or a named structural reference on its
owning record. Free-form labels are invalid.

| Relationship | Source -> target | Cardinality and invariant |
|---|---|---|
| uses_artifact | Run -> ArtifactRef | one or more; result artifact has one incoming use |
| produced | Run -> Observation | exactly 3; each Observation has one producer |
| evidence_targets | EvidenceEvent -> ArtifactRef, Run, or Observation | exactly one target per event |
| interprets | Interpretation -> Observation | 1-3, resolved at its watermark |
| supports, challenges, qualifies | Observation or Interpretation -> Claim | at least one challenges; rationale required |
| tests | ExperimentPlan -> Claim | exactly one when plan exists |
| decides | Decision -> Claim, Interpretation, SelectedMerge, or PatchIntent | one or more selected targets |
| expresses | ManuscriptAnchor -> Claim | exactly one |
| patch_targets | PatchIntent -> ManuscriptAnchor | exactly one |
| attempts | PatchAttempt -> PatchIntent | exactly one; ordered |
| debt_concerns | ManuscriptDebt or UnderstandingDebt -> accepted record/operation | exactly one direct cause; transitive impact derived |
| proposes | Proposal -> draft DomainOperation | exactly one intended operation |
| contributes_to | Contribution -> DomainOperation | exactly one target; sequence gap-free |
| reviews | ReviewBundle -> draft DomainOperation | exactly one digest-bound draft |
| authorizes | AuthorizationReceipt -> ReviewBundle | exactly one; single use |
| records | ExecutionTraceManifest -> Proposal | exactly one root Proposal/revision |
| selects | SelectedMerge -> accepted reasoning record | explicit IDs plus mandatory closure |

The operator conditions in the saturation case live in Observation statements
and edge rationale. F0 does not add a generic condition-node taxonomy.

## 6. Closed operation and capability inventory

| Operation | Capability | Canonical effect |
|---|---|---|
| inspect, compute-impact, diagnose | human read or scoped model query | none; model receives bounded redacted fields, no raw artifact bytes/general paths |
| export | human-only out-of-band export | none in source; creates bounded manifest outside model reach |
| rebuild-projection | maintenance | replaces disposable projection only |
| capture-proposal, revise-proposal, reject-proposal, cancel-proposal | model proposal ingress or human | appends bounded non-authoritative Proposal/trace/disposition data |
| start-episode, close-episode, invalidate-episode | foreground human or frozen V0 runner | changes bounded episode lifecycle; invalidation needs preregistered protocol reason |
| import-truth-packet | human authorization | creates the bounded initial accepted records |
| record-evidence-event | human authorization | appends confirmation/correction/invalidation/retraction |
| create-reasoning-branch, record-interpretation, record-decision | human authorization | changes only branchable reasoning state |
| prepare-review, seal-review | foreground review session | creates/seals ReviewBundle; no accepted mutation |
| authorize-review | human authorization broker only | issues one short-lived receipt after foreground presence |
| materialize-proposal | kernel plus matching unconsumed receipt | creates accepted DomainOperation and Contribution chain |
| apply-selected-merge | kernel plus matching unconsumed receipt | copies the explicit dependency closure into main |
| answer-teachback, defer-teachback, close-understanding-debt | human authorization | records answer/deferral or human-only closure |
| derive-manuscript-debt | deterministic kernel inside accepted operation | atomically opens/updates debt from accepted impact; no public standalone write |
| prepare-patch, apply-patch | human authorization | starts/runs bounded fenced manuscript saga |
| verify-compile, restore-patch | bounded saga with prior human authority | records pinned result or exact restore/hard stop |
| close-manuscript-debt | kernel plus closure-specific receipt | closes exact verified debt/patch/compile tuple |
| replay, import, verify-manifest | maintenance on new isolated destination | reconstructs/verifies trusted or untrusted history, never appends to source/live project |

Anything else is forbidden. The gateway assigns actor, project, episode, schema,
and allowed operation; proposal callers cannot choose a canonical table,
operation type, or human class.

## 7. ResearchEpisode lifecycle

Projected states:

    allocated -> active -> closed
                      `-> invalidated

Only one episode is active per V0 project. Invalidation is allowed only for a
preregistered eligibility error discovered after start or corrupted timing.
Product failure, abandonment, provider failure, anchor failure, authorization
failure, resource overflow, or out-of-F0 after a valid start cannot invalidate
or replace it.

At most three protocol-invalid replacements exist. Attempting a fourth ends V0
as inconclusive without unbounded event append.

## 8. Evidence and temporal views

EvidenceEvent actions are:

    confirm | correct | invalidate | retract

Correction requires supersedes_id. Invalidation/retraction retains reason and
target. Current view resolves a ref against the latest accepted evidence
watermark. Historical view resolves a stored ref/head at its stored watermark.
Re-evaluating historical reasoning with current evidence creates a new
operation; it does not rewrite the historical view.

## 9. Proposal, Contribution, and trace

Proposal disposition is projected from operations:

    pending | revised | rejected | cancelled | selected_for_review | expired

Proposal content is never moved in place into accepted storage. Materialization
creates a new accepted DomainOperation and immutable Contribution sequence.

Contribution contributor_class is:

    human | ai | deterministic

Contribution action is a closed enum covering proposal, edit, adoption,
derivation, and correction. An operation is AI-influenced when any Contribution
in its transitive source chain references a Proposal. That derived status is
not a mutable tag.

ExecutionTraceManifest retains digests, model identity, tool-context digest,
retention class, and payload availability even when raw provider content is
eligible for erasure. Missing payload is explicit and does not prevent accepted
operation replay.

## 10. Review, authorization, and debt

A ReviewBundle is mutable only before sealing. Sealing creates an immutable
revision bound to:

- project and episode;
- exact draft operation digest;
- expected ref heads and evidence watermark;
- expected manuscript file hash when relevant;
- schema and rule versions;
- impact and Contribution/provenance digests;
- human rationale;
- teach-back answer or deferral;
- session nonce and expiry; and
- previous revision identity.

Any bound change makes it stale and requires a new revision. The broker
independently reloads the sealed bundle, recomputes these values, obtains
foreground user presence, and sends the receipt privately to the gateway.
Receipt consumption and accepted operation append share one transaction.

UnderstandingDebt states:

    open -> closed_by_human
        `-> superseded

It exists only when a high-impact AI-influenced accepted operation defers
teach-back. Not now creates no accepted operation and no debt. Closure requires
a separate receipt for the exact debt/cause review and current accepted context,
including the head, evidence watermark, topic rules/set and displayed-context
identity. The gateway reloads those values rather than trusting caller-supplied
objects; evidence changes with the same head invalidate a prepared closure.
Partial explanation survives stale review and needs no mandatory rephrasing.
AI cannot grade or close it. The portable closure contract checks supplied
bindings only; accepted loading and atomic receipt consumption remain unfinished.

ManuscriptDebt states:

    open -> patch_prepared -> applied_unverified -> verified -> closed_by_human
      |           |                 |
      `-----------+-----------------+-> superseded

Restore does not close debt. Closure binds debt ID, PatchIntent, PatchAttempt,
source/output/compiler/config digests, graph head, fencing token, and
non-restored saga state.

## 11. Ref and selected-merge contract

Refs are main and one non-nested branch. Heads are projections over
DomainOperations. F0 does not compute a general LCA, nested ancestry, rebase,
conflict resolution, or revert.

SelectedMerge contains:

- source and target refs;
- frozen base operation and expected heads;
- explicit selected IDs;
- deterministic mandatory closure IDs;
- omitted IDs;
- evidence watermark;
- Decision/rationale; and
- resulting target head.

Mandatory closure includes referenced new Interpretation/ExperimentPlan,
required ScientificEdges, their endpoints, and resulting ManuscriptDebt. Global
evidence already exists and is referenced, not copied. Higher-level scientific
advice cannot add undeclared records automatically.

## 12. Impact closure

Impact is the deterministic transitive set reachable from a changed F0 record
through the allowed edge/reference directions to:

- the one Claim;
- Decisions and SelectedMerge;
- the ManuscriptAnchor and ManuscriptDebt; and
- applicable UnderstandingDebt.

The traversal uses the sealed ref heads and evidence watermark, returns typed
paths and omitted/blocked items, and never follows Proposal, similarity, or
execution-trace links as accepted science. The saturation truth set requires
100% recall and at most one false-positive debt bundle at fixture scale.

## 13. Manuscript saga

PatchIntent and PatchAttempt project these phases:

    debt_open
      -> patch_prepared
      -> applying
      -> applied_unverified
      -> compiling
      -> verified

Failure from applying, applied_unverified, or compiling moves to
restored_after_failure only after exact byte equality is proved, otherwise to
recovery_required. Recovery_required dominates all other surfaces and permits
only inspect, export, and evidence-backed restore.

One active saga exists per project/canonical-file/anchor. A monotonic fencing
token, expected file identity/hash, ref heads, debt, PatchIntent, and compiler
fingerprint are rechecked before every side effect and finalization. The
write-ahead record is durable before mutation and includes authenticated
encrypted preimage metadata plus expected full postimage digest. Compile uses a
pinned argument vector in an isolated output copy; verified outputs alone may
be promoted.

Detailed platform ordering is owned by
[ADR 0007](../architecture/decisions/0007-research-episode-and-manuscript-saga.md)
and must be proven on each supported filesystem. The current macOS-first
execution order is defined by
[ADR 0010](../architecture/decisions/0010-macos-first-platform-adapters.md).

## 14. Resource limits

These are safety limits for the contract spike, not measured product capacity.
Schemas and ingress enforce them before allocation or append. A spike may lower
them but cannot silently raise them.

| Resource | F0 maximum |
|---|---:|
| stable ID / enum / hash text | 128 UTF-8 bytes / 64 bytes / 128 bytes |
| normalized relative path or URI | 1,024 UTF-8 bytes |
| statement, rationale, answer, diagnostic message | 16,384 UTF-8 bytes |
| semantic collection | 128 items unless a smaller count is specified |
| canonical DomainOperation JSON | 262,144 bytes |
| truth-packet manifest | 1 MiB |
| normalized Proposal or outbound context | 256 KiB each |
| retained provider request/response blob | 2 MiB each; 8 MiB per revision; 24 MiB per episode |
| manuscript source, encrypted snapshot, or postimage | 16 MiB each; one marked file |
| provider calls | 2 attempts per revision, at most 6 per episode |
| patch/compile attempts | at most 3 per PatchIntent |
| rejected validation/authorization diagnostics | first 128 detailed attempts; then saturating per-code counters without payload append |
| V0 project ResearchEpisodes | 6 total: at most 3 valid and 3 invalid replacements |
| non-authoritative trace/snapshot ledger | 256 MiB per project |

ResourceLimitError is the single overflow result. After a detailed-attempt or
ledger cap, repeated untrusted calls update only a saturating counter and cannot
grow retained payloads. Overflow rejects the new proposal/patch work without
accepted-state change. Artifact bytes remain external references and are never
silently copied into the store.

## 15. Public state derivation

Product UI state is derived, not canonical. Four orthogonal projections cover:

- workspace review phase;
- provider attempt phase;
- manuscript saga phase; and
- projection health.

Legal events generate the reachable tuples. Impossible combinations are
rejected during load and render; no raw Cartesian-product flags are persisted.
Authorization cannot precede a sealed review, remote loading cannot precede
exact consent, accepted-review-pending requires open UnderstandingDebt,
manuscript progress requires an accepted PatchIntent, and verified requires the
matching pinned compile record.

The product specification owns the visible copy and ordering. Model-based tests
own exhaustive transition reachability.

## 16. Projection, import, and migration

Current, historical, search, context, and UI projections rebuild from canonical
operations plus retained non-authoritative trace references. Rebuild writes
beside the last valid projection and swaps only after verification. Failure
keeps the prior valid projection readable and cannot write accepted state.

Trusted export contains a signed manifest chain and project-authority public
key, never private key material. Trusted restore verifies the full chain in a
new empty store. Untrusted import remains labeled historical claims in a new
isolated store. F0 cannot merge either into an existing live project.

Schema migration is copy-on-write to a new store: compatibility and space check,
exclusive lock, verified export, destination build, full manifest
verification, atomic selected-store change, and retained original. Every
durable boundary has an interruption fixture. Older readers may offer read-only
status, diagnosis, and export for newer stores but cannot mutate them.

## Validation

The design advances only when named fixtures prove:

1. every record, edge, operation, enum, field, bound, and cross-invariant accepts
   its valid cases and rejects unknown/invalid cases;
2. H0-manual and H0-recorded each replay to their own full-audit golden without
   a provider call;
3. evidence watermarks and current/historical views are deterministic;
4. selected merge is dependency closed and preserves global evidence;
5. Proposal/Contribution/trace and both debts retain exact authority;
6. model query/export/egress/proposal ingress/accepted store boundaries fail
   under hostile inputs;
7. every reachable UI tuple and legal event is generated and all others reject;
8. every manuscript crash/concurrency/supersession state restores exactly or
   reaches the sole hard stop;
9. projection rebuild, import, restore, and migration preserve the expected
   manifest and trust label; and
10. 1x and 10x seeded workloads meet the active plan's explicit resource and
    latency budgets or fail visibly without expanding technology automatically.

## Migration and rollback

There is no existing ClaimBranch user data. This draft may still change before
the contract spike, but every fixture and schema is versioned. Once an
implementation stores live accepted state, changes follow the copy-on-write
migration contract above; deleting the old store is a separate human action
outside F0. Evidence correction and scientific correction always append history
rather than destructive rollback.

## Open questions

- Which runtime/package implements the public CLI and generated schemas?
- Does SQLite pass the accepted operation, traversal, concurrency, replay, and
  copy-on-write migration spikes?
- Which canonical JSON and signing libraries preserve the specified bytes?
- Which native-Windows presence, process isolation, credential, IPC, and browser
  path proves the authority boundary?
- Which marker/compile configuration survives the real paper's filesystem and
  toolchain behavior?
- Can the short-lived browser surface satisfy the broker contract, or is a
  native/CLI helper required?

These questions may change adapters and physical layout. They cannot weaken the
logical invariants without a superseding ADR and updated validation contract.

## Outcome

Pending. The design remains draft until P1 fixtures and spikes pass. An accepted
ADR may constrain implementation before code exists; this draft is still not
proof that the schema or storage works.
