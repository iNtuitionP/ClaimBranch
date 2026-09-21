---
kind: design
status: accepted
owners: maintainers
last_reviewed: 2026-09-11
canonical_for: user-invoked human-confirmed Notion judgment journal for repository agents
---

# Design: user-invoked Notion judgment journal

## Purpose

The ClaimBranch contributor journal must preserve a small number of useful
human judgments without turning automatic AI summaries into a reading backlog.
One entry should let a future person recover the central judgment and its
boundary quickly. It must not become a task log, agent handoff, transcript, or
second source of repository truth.

A record earns its reading cost only when it reduces the cost of making the
same judgment again. The user alone chooses what is worth recording and
confirms its meaning; AI may help elicit and compress that meaning but may not
silently create information debt.

This design supersedes the automatic material-task capture in the
[original coding-journal design](2026-08-15-notion-coding-journal-automation.md).
It changes contributor automation, not the ClaimBranch product or its accepted
scientific state.

## Context and current state

At design time, the implemented workflow captured a redacted pending envelope
whenever a `Stop` hook saw a material worktree delta. The agent could then infer
and attach a task-level draft containing purpose, outcome, decisions,
verification, risks, and a next action. A remote create or update still needed
approval, but the local record and its retry debt already existed before the
user chose to record it.

Five fresh-agent pressure runs on 2026-08-26 all treated the hook-created key as
authorization to compose a draft. Their common rationale was that explicit
user intent was required only for no-change decisions and that remote write
approval was sufficient human control. That behavior contradicts the desired
boundary: approval of transmission is not approval of semantic content or of
creating a durable record.

The existing redaction, exact-key query, synchronous projection, receipt, and
failure isolation remain valuable. The change should replace semantic capture
and invocation while preserving those deterministic safety mechanisms.

## Goals and non-goals

Goals:

- create no key, envelope, pending item, dismissal marker, or Notion page before
  explicit user intent and exact semantic confirmation;
- make one entry represent one central human judgment or understanding shift;
- keep a stable six-field semantic form while asking only the questions needed
  to resolve missing or ambiguous meaning, one at a time;
- preserve the user's distinctive nouns, tensions, and negations instead of
  smoothing them into generic project prose;
- keep missing, unknown, skipped, and not-applicable answers explicit instead
  of letting AI fill them;
- let natural-language record requests select the skill without treating skill
  selection as consent to capture or write;
- attach only human-confirmed evidence pointers, never an automatic task delta
  as claimed relevant evidence;
- persist the confirmed draft before remote access so denial or outage can be
  retried without a transcript;
- preserve legacy `cbj-v1` envelopes and receipts without rewriting or deleting
  them; and
- keep every journal page create separately approval-gated and preserve human
  edits to existing pages by never updating them through journal automation.

Non-goals:

- proving that a chat response came from a cryptographically authenticated
  foreground human;
- automatically deciding that every material task deserves a record;
- recording every changed path, command, action, alternative, or AI proposal;
- adding tags, scores, candidate queues, background suppression state, or a
  journal lifecycle beyond the existing pending and receipt boundary;
- automatically cleaning up, migrating, or rewriting existing Notion pages;
- implementing the deeper P0, V0, and P5 milestone-review skill in this change;
- changing ClaimBranch product authority or accepted scientific state; and
- mutating the live Notion database or existing pages during repository
  implementation and offline validation.

## Decision drivers

- The journal is read by a person; reducing future re-decision cost matters more
  than preserving exhaustive task context.
- Fixed fields should stabilize navigation without requiring fixed questions,
  equal verbosity, or invented content.
- AI may propose that a judgment is worth recording, but only the user chooses
  whether an interview begins and whether the exact result is durable.
- AI proposal is useful only after the user has expressed an actual judgment,
  shift, or boundary; task completion and file changes alone are not grounds.
- A hook or skill trigger is not evidence of human semantic approval.
- The fragile Notion write path needs low freedom and deterministic payloads;
  the interview needs limited contextual freedom.
- Notion remains a convenience projection. Git and version-controlled `docs/`
  remain authoritative.
- Existing local `cbj-v1` state may outlive this deployment and must remain
  diagnosable and explicitly retryable.

## Options considered

### Retain automatic capture and improve only the prose template

Replace the task-summary fields with six judgment fields while leaving the
`Stop` hook and pending queue intact. This improves page shape but still creates
records and debt without user intent. It is rejected.

### Keep automatic evidence capture but delay AI prose

Let `Stop` persist a key and Git delta, then ask whether to attach semantic
content. This avoids inferred prose but still leaves invisible durable state
after rejection or silence. It also makes worktree changes, rather than human
judgment, the unit of record. It is rejected.

### User-invoked adaptive interview followed by deterministic sync

Let AI make at most a non-authoritative suggestion. After explicit acceptance
or a direct user request, map what the user already said, ask only what remains
materially missing or ambiguous, show one exact semantic preview, and persist
only after confirmation. Then show the exact generated write payload and reuse
the deterministic query, approval, receipt, and retry boundary. This is
selected.

## Proposed design

### Representative invariant

> A record does not replace judgment; it preserves only the minimum context a
> future human needs to understand that judgment again.

The skill metadata may make the skill discoverable from a natural-language
request, but discovery grants no authority. This invariant leads the skill body
and shapes the executable tests.

### Authority sequence

The sequence is:

1. The user explicitly requests a record, or AI proposes one candidate after
   the user has expressed a concrete judgment, understanding shift, or boundary.
2. The user request or acceptance authorizes an interview and creates no state.
3. The agent maps only meaning already explicit in the active conversation.
4. If several judgments are present, the agent asks the user to choose one. It
   never bundles them for convenience.
5. The agent asks only for a missing or ambiguous semantic field, one question
   at a time. If all six fields are already clear, it asks none.
6. The agent reads the explicitly configured journal language. Setup asks the
   user to choose `ko` or `en`; conversation language is never treated as the
   choice. An older configuration with no language causes one explicit choice
   before preview and no automatic default.
7. The agent proposes a short searchable title and the smallest useful evidence
   set, then passes that proposed JSON to the pure `preview-judgment` command.
   The command validates the ten-field `JudgmentDraft` input contract and
   returns JSON only, with exactly `preview` and a versioned ASCII
   `capture_token`.
   The agent shows the returned preview verbatim: title, six answers, evidence
   pointers, AI contribution label, and optional superseded key.
8. The user confirms or corrects that exact preview.
9. Only then may the agent send the exact helper-emitted `capture_token` through
   standard input to `record-judgment --input-token -`, which may create a
   durable `cbj-v2` envelope.
10. The deterministic sync path queries the configured data source by exact key.
    An existing page is preserved. Without verified local success, pause for
    user inspection without changing the pending record or fabricating a receipt.
11. Only when no matching page exists does the agent display the exact generated
    Notion properties and body, including Journal Key and Recorded At, and the
    user separately approves that one create.

The user owns the remote page after creation; it is not a machine-owned mirror.
Journal updates are denied even with a receipt. A retry must not duplicate an
existing page, import its human edits into confirmed local content, or infer
success from inspection. The [operator guide](../development/notion-coding-journal.md#exact-sync-and-retry)
owns the bounded pause and terminal-state procedure. No new sync state,
comparison engine, automatic reminder, or acknowledgement-repair command is added.

The first user response authorizes an interview, not capture. The exact preview
confirmation authorizes local capture. The MCP approval authorizes only the
displayed remote write. The pre-capture preview is exact for semantic content;
the post-capture write preview makes the generated key and timestamp visible
before transmission. Neither preview hides values that its confirmation or
approval authorizes.

`preview-judgment` is deliberately non-mutating. It accepts one explicitly
UTF-8 PowerShell-serialized JSON object with exactly `title`, `background`,
`why_now`, `understanding_shift`,
`human_judgment`, `tradeoff_boundary`, `revisit_signal`, `evidence_pointers`,
`ai_contribution`, and `supersedes`, then returns only `preview` and
`capture_token`. The caller supplies exactly one supported language, `ko` or
`en`. The `cbj-capture-v3` token is a deterministic base64url encoding of the
canonical validated draft and that language, with a version and unkeyed SHA-256
integrity check.
It is ASCII so it can cross a later process without locale-dependent damage.
It detects accidental substitution or truncation; it is not a secret,
cryptographic human authentication, durable approval receipt, or new source of
authority. It does not inspect Git or Notion, read or create journal state,
derive a journal key, add a recorded time, or emit repository metadata. The
same valid input produces byte-identical JSON output. Its fixed human labels
make the gate consistent; it has no authority to invent, rank, shorten, or
complete semantic content. This leaves semantic taste with the user while
moving only validation and presentation out of probabilistic skill prose.

### Language selection and presentation

Language is an explicit user setting, not an inference. Initial setup asks once
for `ko` or `en` and stores only that closed enum in local configuration. An
existing configuration without the field remains valid but unset; the next
record flow asks once and writes the setting only after the user chooses. There
is no `auto` mode, locale fallback, or conversation-language detection.

The selected language controls interview questions, AI-authored summaries,
fixed semantic-preview labels, and new Notion body headings. It does not rename
machine JSON keys, enum values such as `AI-assisted`, or the existing Notion
database properties. Distinctive user nouns, quoted phrases, and established
project terms remain in their original form when translation would blunt or
change the judgment.

The preview token binds the validated draft and selected language. Capture
copies that language into the immutable envelope, and the judgment key includes
it; therefore the same draft and Git snapshot in `ko` and `en` are distinct
records. Later configuration changes affect only future records. Retry and
Notion projection render from the envelope, never from current configuration.

Language-less configurations and envelopes are legacy inputs, not evidence of
a default. Existing pending envelopes retain their exact old rendering and are
never migrated or rewritten. A `cbj-capture-v2` or older transient token is
rejected after the background change; it requires a new pure preview and
confirmation, which creates no durable debt.

The token remains only in the active tool result or conversation until the
user responds. It is never written to a candidate file, key, queue, dismissal
marker, or pending envelope. The capture command reads it from standard input,
not a process argument. If the exact token is unavailable after interruption or
context loss, the agent must rerun the pure preview and obtain confirmation of
that preview again; it must not reconstruct a token from memory. This chooses
visible re-confirmation over hidden recovery debt.

AI may make at most one proposal for a given judgment in the active
conversation. Silence, rejection, or a pause creates no candidate, dismissal,
or suppression record. The proposal is never triggered solely by changed files,
a completed task, or a milestone label.

The repository helper cannot cryptographically authenticate a chat response.
The proportional contributor boundary is removal of automatic capture,
`allow_implicit_invocation: true` for natural-language discovery, the separation
of discovery from authority, immutable confirmed input, and the independent
remote approval. ClaimBranch-grade human receipts remain a product concern and
are out of scope here.

### One judgment and six stable fields

One record contains one central judgment. A task may produce zero, one, or
multiple records. Independent judgments are never bundled merely because they
occurred in one coding task.

The stored semantic fields and rendered headings are stable. The example
questions describe their meaning; they are not a mandatory questionnaire:

| Internal field | Human question |
|---|---|
| `background` | What situation produced this judgment, and what project-specific terms must a future reader decode? |
| `why_now` | Why now? What tension, broken assumption, or new observation made this worth recording? |
| `understanding_shift` | What changed? What was understood before and what is understood now? |
| `human_judgment` | What did the human decide, including an intentional non-decision? |
| `tradeoff_boundary` | What was sacrificed, accepted, or kept out of scope? |
| `revisit_signal` | What observation would support, reopen, or reverse this judgment? |

Every field is present in each new preview and page. The agent first maps the
user's explicit statements and asks only about a field whose missing or
ambiguous meaning would weaken the record. Background is one compact decoding
key: it states the situation that produced the judgment and briefly expands
opaque internal labels such as `P0`. It is not a task summary, implementation
inventory, transcript, or generated project history. The user, not a heuristic,
decides whether the proposed background is sufficient.

`Unknown`, `None`, `Skipped`, or an equivalent user-confirmed value is valid,
including for background, but AI may not silently choose absence or create a
plausible answer solely to complete the form. Existing background-less records
are a compatibility case, not a model for new capture.

Each field carries one semantic unit with its core sentence first and is usually
concise. This is a writing target, not a sentence-count validator. If
compression would remove a distinction, tension, or intentional qualification,
the preview preserves the longer user-confirmed expression. In particular, AI
does not replace the user's distinctive nouns, boundaries, or negations with
generic management language.

The background field uses the same 1,000-character safety ceiling as the other
semantic fields, while the complete canonical draft remains limited to 6,000
bytes. Adding context therefore reallocates a fixed reading budget rather than
authorizing longer records.

The title is a short searchable proposal derived from `human_judgment` and the
user's distinctive wording, never from changed files or the task name. It is
part of the exact preview. A separate title question is needed only if the user
rejects that proposal.

### Evidence and provenance

The agent proposes the smallest set of repository-relative evidence pointers
needed to relocate the judgment, normally zero to three. The user may remove,
replace, or add pointers in the exact preview. An empty list is valid. The
runtime maximum of ten remains a safety ceiling, not a completeness target. The
page does not copy source, raw diffs, transcripts, command output, or
automatically claim every changed path as relevant.

The helper records the repository, branch, current HEAD, and worktree digest at
capture time as local deterministic metadata. This snapshot supports exact-key
retry and local diagnosis; it is not projected to Notion and does not claim
that every worktree change caused or implemented the judgment.

`AI-assisted` remains the conservative provenance value whenever AI proposed,
elicited, summarized, or materially rewrote the entry. `Human-only` applies
only when the agent transports exact human-authored semantic content and
deterministic metadata.

### Terminal status boundary

Waiting for an interview answer, preview correction, semantic confirmation, or
remote-write approval is not a terminal result and emits no journal status.
Once the flow actually terminates, the public status is determined by the
durable boundary:

- cancellation before capture is `not required`;
- failure before a key exists is `error`;
- after a key exists, remote denial, external failure, duplicate ambiguity, or
  receipt failure is `pending`; and
- only a valid local receipt is `synced`.

This vocabulary reports recoverable state without manufacturing state merely
to explain a paused conversation.

### Durable state and legacy compatibility

New confirmed judgments use a `cbj-v2-<digest>` key derived from repository
identity, current snapshot digest, the canonical confirmed draft, and the
record's language. The outer local configuration format remains compatible
with the configured database and accepts the older missing-language shape as
explicitly unset.
The parser and sync guard accept both legacy task drafts under `cbj-v1` and new
judgment drafts under `cbj-v2`.

The immutable local v2 envelope retains the confirmed title, six semantic
fields, evidence pointers, AI contribution, optional supersedes key, journal
language, journal key, and deterministic repository snapshot. It is the
complete retry input; the active conversation is not.

V2 envelopes and receipts use `v2/pending/` and `v2/receipts/`, separate from
the v1 directories. This is a rollback boundary, not a second semantic store:
old code never scans or quarantines v2 files, while forward code combines both
versions for status, exact lookup, and receipt validation.

The `SessionStart` and `Stop` hook registrations are removed. Their legacy
handlers become no-op compatibility paths so an old trusted hook definition
cannot create new state after the code update. Existing `cbj-v1` state is not
deleted, migrated, or automatically retried. A user may explicitly request an
exact-key retry, which reuses its immutable legacy projection.
The public `draft` and `record-decision` CLI routes are removed so current code
cannot attach newly inferred v1 content or create another v1 semantic record.

### Notion projection

The existing database can accept the new projection without a live schema
mutation. A v2 page writes only four properties: Title, Journal Key, Recorded
At, and AI Contribution. Repository, branch, Start/End HEAD, and Worktree Digest
remain in the local envelope for retry and diagnosis. Legacy task-only Status,
Change Type, and Verification properties remain absent for v2 entries.

The page body renders the six stable semantic headings in the language frozen
in the envelope, followed by evidence pointers and an optional supersedes key.
It does not repeat AI Contribution or Journal Key because those values already
exist as properties. Stable property names are not localized. Existing
background-less v2 envelopes, whether language-less or language-bound, omit the
Background section and remain byte-compatible. Reads, receipt updates, and
retries add no null field, placeholder, or inferred context. An explicit stored
`background: null` is not legacy absence and fails closed. Legacy v1 projection
is also unchanged.

### Instruction footprint

The regular record skill contains the complete authority flow, six-field
contract, preview boundary, and write boundary needed for an ordinary entry. It
does not require the longer operator guide on every invocation. The guide is
loaded only for setup, diagnosis, recovery, exact-key retry, or another
operator-only path. This keeps prompt context from becoming another form of
reading debt without weakening the write guard.

### Refinement scope

The 2026-08-30 refinement is deliberately narrow. Implementation may change the
record skill metadata and instructions, the v2 projection and its write guard,
the governing repository and operator documentation, and focused tests. A
failing fresh-agent test showed that exact semantic-preview rendering remained
probabilistic after five bounded skill-wording corrections, and the user
approved one exception on 2026-08-31: add the pure `preview-judgment` CLI command
described above. A later broad review reproduced PowerShell 5.1 non-ASCII
corruption and proved that the process-local preview variable could not cross
the confirmation turn. The user approved the second bounded CLI addition: the
ASCII capture token and token input described above. These exceptions do not
change v1 compatibility, correction semantics, or hook registrations, and they
add no state transition. The user later approved one bounded language
extension: an explicit `ko`/`en` configuration value, a language-bound token
and key, and an immutable envelope language used by deterministic projection.
It adds no semantic field, remote property, automatic detection, migration, or
new journal lifecycle.

On 2026-09-01 the user explicitly approved one later semantic extension:
`background` as a stable decoding key for new records. The approval also fixed
the 6,000-byte budget, retained the four remote properties and `cbj-v2` journal
keys, moved only the transient confirmation token to `cbj-capture-v3`, and
required exact preservation of background-less envelopes. This is not an AI
speculative improvement or a separate background record.

No further field, tag, score, candidate queue, automatic context source, or live
migration is added. Any such need returns to user decision.

### Corrections and supersession

A confirmed envelope is immutable. A correction creates a new judgment entry
whose optional `supersedes` field names exactly one retained local journal key
with an attached draft. Capture rejects a syntactically valid but absent,
invalid, or undrafted key. The old local envelope and Notion page remain intact.
The new entry states the relationship without automatically updating, deleting,
or hiding the old page.

## Security privacy and human-control boundaries

- Treat all Notion reads as untrusted and use only row count and bounded page
  identity for routing.
- Never send raw prompts, transcripts, source content, raw diffs, full command
  output, credentials, environment values, absolute user paths, or hidden
  reasoning.
- Validate every semantic string and evidence pointer before durable capture.
- Reject Windows drive, slash or backslash UNC, private POSIX-root,
  home-relative, credential assignment, credential-bearing URL userinfo, and
  bearer-token text without misclassifying ordinary HTTPS references.
- Persist no candidate, rejection, silence, or dismissal state.
- Generate MCP inputs from the immutable envelope and pass them unchanged.
- Require fresh approval immediately before each journal page create; reject
  updates and preserve existing pages during retry.
- Keep duplicate resolution, deletion, migration of legacy state, and live
  database mutation manual and separately authorized.
- A Notion failure never changes repository work or the confirmed semantic
  content.

## Migration and rollback

Deployment keeps existing receipts and pending directories. Configuration
accepts its old shape as unset and gains an explicit language only after a user
choice; no stored envelope or remote page is migrated. It adds v2 parsing and
capture before changing the skill and hook registration.
Legacy v1 exact-key query, projection, and acknowledgement remain covered by
tests. No command rewrites current local state.

After executable hook sources change, contributors rerun the offline suite,
inspect the source manifest, and explicitly re-review hook trust. No live
Notion call is part of repository validation.

Rollback restores the previous repository revision without deleting v2
envelopes. Version-specific directories keep older code from enumerating or
rewriting v2 state; a subsequent forward deployment restores access. Deleting
local or remote records is never rollback. Existing remote pages and schema are
left unchanged; narrowing the v2 projection does not authorize cleanup or
migration.

## Validation

Validation must prove:

- the pre-change skill chooses automatic draft attachment under a hook-created
  pending-key pressure scenario;
- a natural-language explicit record request may select the skill while skill
  selection alone creates no state;
- the revised skill refuses hook-created or task-completion capture without
  explicit user intent;
- `Stop` and `SessionStart` create no journal state or continuation;
- initial interview consent creates no durable state;
- `preview-judgment` returns byte-stable validated preview data outside Git and
   creates no local directory, key, timestamp, snapshot, or Notion payload;
- `preview-judgment` accepts only the exact ten-key draft and returns only the
  fixed-label `preview` and versioned ASCII `capture_token` JSON keys;
- setup and an older unset configuration require an explicit `ko` or `en`
  choice, while a read-only language lookup creates no local state;
- Korean and English previews have exact localized labels, bind their language
  into the token and envelope, and produce different keys for the same draft
  and snapshot;
- changing configuration after capture does not change an existing pending
  projection, and a language-less envelope retains its exact legacy rendering;
- a fresh process can capture the exact Korean and ASCII semantic values from
  that token, while a changed, truncated, non-canonical, or wrong-version token
  fails before journal state exists;
- only exact confirmed v2 input creates a stable envelope;
- sparse user-confirmed fields and empty evidence are accepted without AI
  filler;
- v2 properties contain only Title, Journal Key, Recorded At, and AI
  Contribution;
- new v2 bodies contain the six headings in order, omit duplicated property
  values, and contain no task-summary sections, while old background-less v2
  bodies retain their exact five-heading form;
- legacy v1 envelopes still parse, project, query, and acknowledge;
- corrections create a distinct v2 key with one validated supersedes pointer;
- correction capture rejects a well-formed key with no retained original;
- v2 envelopes and receipts remain byte-identical and reachable across a v1
  directory scan and forward reopen;
- legacy `draft` and `record-decision` CLI commands fail without mutation;
- unsafe text, absolute paths, mismatched payloads, duplicates, and unknown MCP
  results fail closed; and
- all journal tests, skill package tests, skill validation, hook JSON parsing,
  documentation checks, and fresh-agent pressure scenarios pass offline.

In addition to deterministic unit and integration tests, a small sanitized
behavior suite covers these interaction shapes:

- a natural-language record request;
- all six fields already present in the user's words;
- only some fields present;
- opaque project labels in an otherwise complete background;
- several judgments competing for one record;
- task completion with no expressed judgment;
- rejection or pause before confirmation; and
- a title and body that preserve distinctive user wording.

The suite stores reproducible inputs and explicit pass criteria, not chat
transcripts or model-output dumps. A final human utility check uses one
synthetic preview to verify that a reader can quickly find the judgment,
boundary, and revisit signal. That observation is reported honestly and is not
presented as automated proof.

## Open questions

None for the regular judgment-recording skill. The deeper independent
human/AI comparison at P0, V0, and P5 remains a separately designed skill that
must reuse this six-field stored form.

## Outcome

The user accepted the one-judgment unit, proposal-only AI role, human semantic
confirmation, stable six-field form with adaptive questions, voice-preserving
compression, minimal remote projection, and non-destructive supersession. The
baseline implementation and offline validation are tracked in the
[completed ExecPlan](../plans/completed/2026-08-26-user-invoked-notion-judgment-journal.md).
The localized-preview refinement is tracked in its
[completed ExecPlan](../plans/completed/2026-08-31-notion-judgment-journal-refinement.md),
and the approved background extension is tracked in the
[completed ExecPlan](../plans/completed/2026-09-01-notion-judgment-background.md).
