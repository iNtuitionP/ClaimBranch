---
kind: exec-plan
status: completed
owners: maintainers
last_reviewed: 2026-08-31
canonical_for: implementation of the 2026-08-30 Notion judgment journal refinement
---

# ExecPlan: Notion judgment journal sharp refinement implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task by task. Before
> editing the skill, also use `superpowers:writing-skills` and `skill-creator`.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the journal naturally discoverable but never self-authorizing,
ask only for missing meaning, preserve the user's language, and send only the
minimum language-explicit v2 judgment projection to Notion.

**Architecture:** Keep the existing immutable v2 envelope, key derivation,
local Git snapshot, exact-key query, write guard, receipt, and v1 compatibility.
Change the contextual skill layer and the `JudgmentDraft` projection, and add
one pure `preview-judgment` CLI command that validates and renders the proposed
draft without Git, time, key, Notion, or local state. Its versioned ASCII
capture token binds that preview to a later process without a file or shell
variable. Both create and update continue to consume the same deterministic
projection functions, so the guard rejects any extra or altered remote field.
An explicit `ko` or `en` setup value controls questions and presentation, while
each confirmed record freezes that language in its token, key, and envelope so
retry never depends on later configuration.

**Tech stack:** ASCII Markdown skill package, YAML agent metadata, Python 3
standard library, `unittest`, JSON scenario fixtures, Codex hooks, and the
official Notion MCP boundary already configured by the repository.

**Spec:** [User-invoked Notion judgment journal design](../../designs/2026-08-26-user-invoked-notion-judgment-journal.md)

## Global constraints

- A record is valuable only when it reduces future re-decision cost; the user
  alone chooses what is recorded and confirms its meaning.
- `allow_implicit_invocation: true` permits natural-language discovery only.
  Selection, suggestion, silence, and interview consent create no durable state.
- AI may suggest one record at most once for the same judgment in the active
  conversation, and only after the user has expressed a concrete judgment,
  understanding shift, or boundary. File changes, task completion, and
  milestones alone never justify a suggestion.
- One record contains one judgment. Keep the five stored fields stable, map
  only explicit user meaning, ask one missing or ambiguous question at a time,
  and ask the user to choose if several judgments compete.
- Keep one semantic unit per field with the core sentence first, but enforce no
  sentence count. Preserve distinctive nouns, tensions, negations, and longer
  user-confirmed wording when compression would change meaning.
- Journal language is exactly `ko` or `en`, chosen explicitly during setup or
  once for an older unset configuration. Never infer it from conversation,
  locale, or content. Keep machine keys, enums, and Notion property names
  stable.
- Freeze language in every new preview token and envelope. The same draft and
  snapshot in different languages has a different key; later configuration
  changes affect future records only. Preserve language-less configuration and
  envelopes without migration or projection changes.
- Evidence is normally zero to three confirmed repository-relative pointers;
  ten remains only the existing runtime safety ceiling.
- A v2 Notion page has only four logical properties: Title, Journal Key,
  Recorded At, and AI Contribution. The MCP input represents Recorded At with
  its existing `start` and `is_datetime` keys. The body has the five semantic
  headings, evidence, and optional supersedes relation; it does not duplicate
  AI Contribution or Journal Key.
- Repository, branch, HEAD values, and worktree digest remain local. Do not
  change legacy v1 projection or migrate, clean up, or rewrite remote pages.
- Change only the language validation, compatible configuration/envelope
  decoding, judgment-key material, pure presentation, and CLI surfaces needed
  for the approved language boundary. Keep the nine-field `JudgmentDraft`, v1
  projection, correction semantics, hook registrations, database schema, and
  state transitions unchanged. If another runtime surface must change, stop
  and ask before expanding scope.
- Do not contact Notion, inspect contributor live journal state, start OAuth,
  re-trust hooks, or mutate existing remote or local journal records.
- Store only sanitized scenario inputs, criteria, and verdict counts. Do not
  store transcripts, model outputs, prompts copied from real users, or hidden
  reasoning.
- Preserve the existing dirty worktree and `.vscode/`. Use review checkpoints;
  do not commit, push, or rewrite user-authored changes without an explicit
  user request.

---

This plan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose and big picture

After this plan, a user can ask in ordinary language to record a coding
judgment. The skill first reuses meaning already present in the conversation,
asks only for material gaps, and preserves the user's sharp wording in one
consistent five-field preview. Nothing durable exists until the user confirms
that semantic preview. After capture, the user sees the exact generated Notion
payload and separately approves one write.

The remote page is deliberately smaller than the local retry envelope. A future
reader sees the judgment, its boundary, its revisit signal, and only the
evidence needed to relocate it. Git snapshot metadata stays available for local
diagnosis without becoming human reading debt in Notion.

## Progress

- [x] 2026-08-31 00:01+09:00 - The user approved the written design; inspected
  the current skill, metadata, projection, guard, tests, operator guide, agent
  instructions, and ExecPlan policy without changing implementation code.
- [x] 2026-08-31 10:09+09:00 - Started subagent-driven execution in the
  existing approved dirty checkout, created an ignored SDD workspace, and
  ruled the preflight conflicts before dispatching implementation work.
- [x] 2026-08-31 - Task 1 passed its RED/GREEN cycle and independent review:
  focused 4/4 and unchanged compatibility 33/33 passed; the v1 branch remained
  untouched.
- [x] 2026-08-31 - Task 2's bounded skill-writing pressure established the
  remaining failure: conversation behavior passed, but only 4/10 complete-input
  runs produced a capture-valid exact preview after five minimal wording rounds.
- [x] 2026-08-31 13:11+09:00 - The user approved the narrow deterministic
  boundary: a pure preview command with no journal state or semantic invention.
- [x] 2026-08-31 - Implemented and independently reviewed Task 3's pure preview
  command with a
  RED/GREEN cycle.
- [x] 2026-08-31 - Finished and independently reviewed Task 2 using the reviewed
  preview command; its one Minor fixture-test gap was fixed and scoped
  re-review was clean.
- [x] 2026-08-31 - Aligned the accepted design, root agent rule, and operator
  guide after the Task 2 scenario contract passed; independent review found no
  issue at any severity.
- [x] 2026-08-31 - Broad integration review found that the PowerShell 5.1
  recipe corrupted non-ASCII fields and that its process-local `$result`
  could not survive the user's confirmation turn. Reproduced the encoding
  failure and obtained user approval for a no-file ASCII capture token.
- [x] Implement and validate the approved UTF-8 and cross-turn transport
  correction, then repeat the broad review.
- [x] 2026-08-31 - The user approved explicit `ko`/`en` setup selection,
  per-record language freeze, stable machine names, no automatic detection,
  and exact legacy rendering without migration.
- [x] Implement and validate the language boundary with RED-first tests, skill
  pressure cases, and exact Korean and English helper output.
- [x] Run offline validation and fresh-agent scenario verdicts.
- [x] 2026-08-31 - The user confirmed that the exact Korean preview keeps the
  judgment, boundary, and revisit condition quickly recoverable without losing
  the intended sharpness.

## Surprises & Discoveries

- The current record metadata still sets `allow_implicit_invocation: false`,
  while the accepted design separates natural-language discovery from capture
  authority. This is a metadata and instruction mismatch, not a reason to add
  state.
- The current skill always loads the operator guide and asks five fixed
  questions. The approved design can reduce prompt and interaction debt by
  making the regular path self-contained and using the guide only for operator
  paths such as exact-key retry and recovery.
- `scripts/notion_journal/hooks.py` already centralizes both generated payloads
  and write validation in `_expected_properties(PendingEnvelope)` and
  `_expected_body(PendingEnvelope)`. Narrowing only their `JudgmentDraft`
  branches makes create, update, and pre-write validation agree without another
  schema or guard abstraction.
- The same projection functions contain a separate `JournalDraft` branch for
  v1. Focused v2 edits can leave legacy output unchanged and let existing v1
  regression tests prove that boundary.
- No permanent behavior-scenario fixture exists. A single sanitized JSON file
  plus structural tests is enough to make future pressure runs reproducible;
  a new runner, transcript store, or scoring system is unnecessary.
- The skill-writing guidance explicitly rejects source-phrase assertions as a
  proxy for consuming-agent behavior. The originally planned Task 2 assertions
  would have made the suite more brittle without proving the journal contract.
- A fixed nine-line preview template improved behavior but did not make the
  capture gate reliable: only 4 of 10 final cross-model complete-input runs
  emitted every required line with a valid exact provenance value. Conversation
  selection, adaptive questioning, choose-one handling, silence, and voice
  preservation passed; deterministic preview rendering remains the open gap.
- During Task 2, the documentation checker reported that the in-progress record
  skill had no H1 heading. Task 2 restored one H1 within the 500-word limit;
  the checker now passes.
- The first no-state test placed its absence assertion after temporary-root
  cleanup, which made the check vacuous even though the production branch was
  pure. Independent review caught it; the corrected test checks absence before
  and after each invocation while the parent directory is still live.
- Fresh consuming-agent pressure found two integration gaps that static prose
  review had missed: the PowerShell object was not explicitly serialized to
  JSON, then the exact nine input keys were not stated together. Each was fixed
  at the deterministic handoff only. After both fixes, the full matrix passed
  without another semantic instruction or example.
- Broad review then exposed two system-boundary failures outside that matrix.
  Windows PowerShell 5.1 uses `us-ascii` for native pipeline input by default,
  and a shell variable returned by the preview process does not exist in the
  later user-confirmation turn. A real PowerShell 5.1 run changed Korean text
  to question marks; explicitly selecting UTF-8 prevented the corruption.
- The post-change fresh-agent run exposed a test-fixture authority ambiguity:
  four scenarios expected an interview or preview but did not say that the user
  had requested a record. Two evaluators correctly refused to cross that gate.
  The smallest fix was to make interview consent explicit in those sanitized
  inputs; weakening the skill to satisfy the old fixture would have violated
  the governing rule.
- The language choice is not safely recoverable from conversational context.
  In five no-guidance pressure runs, none asked for the closed `ko`/`en` choice
  before configuration mutation; explicit skill guidance is therefore needed.
- Independent boundary review found that `asdict()` would add
  `journal_language: null` when a language-less envelope was first written or
  later marked synced. Omitting only that absent storage key preserves the old
  representation while leaving explicit `ko` and `en` envelopes unchanged.

## Decision log

- 2026-08-30 - The user accepted stable output fields with adaptive questions,
  voice-preserving compression, narrowly bounded AI suggestions, minimal remote
  metadata, and separate semantic and write approvals.
- 2026-08-30 - The user rejected automatic capture and any invisible proposal,
  dismissal, or suppression state because such state becomes information debt.
- 2026-08-31 - Keep this as one plan because the skill and deterministic v2
  projection implement one authority boundary and can be validated together.
- 2026-08-31 - Use `docs/plans/active/` instead of the writing-plans skill's
  default directory because the repository ExecPlan policy is the direct user
  preference and canonical workflow.
- 2026-08-31 - Add no ADR or product-spec change. This is contributor
  automation governed by the accepted design, not a ClaimBranch product or
  architecture decision.
- 2026-08-31 - Replace automatic commit steps with scoped diff checkpoints.
  The shared worktree already contains user-authored changes and the user has
  not requested commits.
- 2026-08-31 - Execute in the existing checkout instead of creating a clean
  worktree because the approved baseline includes uncommitted journal changes.
  Isolate each task with ignored SDD briefs, before-snapshots, scoped diffs, and
  independent review rather than discarding or copying that baseline.
- 2026-08-31 - Treat only machine-readable metadata, package structure,
  deterministic commands, and scenario-fixture shape as static-test surfaces.
  Test semantic skill instructions with fresh consuming agents before and after
  the rewrite; do not add source-phrase assertions.
- 2026-08-31 - Keep commits and pushes out of this execution even though the
  generic SDD workflow normally uses commit ranges. Each reviewer receives a
  task-scoped no-index diff against an ignored before-snapshot instead.
- 2026-08-31 - Stop after five minimal skill-wording correction rounds instead
  of adding more prompt emphasis. The remaining failure is at a deterministic
  formatting/validation boundary, and the plan forbids expanding CLI or runtime
  scope unless a RED proves necessity and the user chooses that expansion.
- 2026-08-31 - The user chose the narrow CLI expansion after reviewing the
  evidence and alternatives. `preview-judgment` may validate the existing
  draft, render fixed human labels, and return a deterministic handoff; it may
  not inspect Git, derive keys or time, touch local state, call Notion, or add
  semantic content. This moves only a deterministic responsibility out of the
  LLM and leaves both meaning and capture authority with the user.
- 2026-08-31 - Treat PowerShell serialization and the exact nine-key input shape
  as part of the low-freedom executable handoff, not as semantic prompting.
  Observed failures justify those two facts; no additional rubric, example, or
  content rule is added.
- 2026-08-31 - The user approved replacing the cross-turn shell variable with
  a versioned ASCII `capture_token` carried only in the active conversation.
  The token contains the canonical validated draft plus an unkeyed SHA-256
  integrity check; it prevents accidental drift but does not authenticate the
  human or grant authority. No file, key, envelope, or pending state exists
  before confirmation. If the exact token is unavailable, rerun the pure
  preview and obtain confirmation again instead of reconstructing it.
- 2026-08-31 - Keep direct `record-judgment --input-json -` compatibility for
  existing tests and explicit internal callers, but make the record skill use
  only `--input-token -`. This changes the fragile handoff without adding a new
  command, state machine, or persisted representation.
- 2026-08-31 - When a behavior fixture omitted interview authority, preserve
  the skill's refusal and repair the fixture premise. A test may not silently
  convert skill discovery or an unaccepted suggestion into interview consent.
- 2026-08-31 - The user chose an explicit two-value language setting. There is
  no `auto`: setup or an older unset configuration asks once. Preview tokens,
  new judgment keys, and envelopes bind the choice; retry renders from the
  envelope, while Notion property names and machine enums stay stable.
- 2026-08-31 - Treat a missing envelope language as representation history, not
  a null-valued field to normalize. Both initial compatibility capture and
  receipt processing omit the key when its in-memory value is `None`; no
  migration command or opportunistic rewrite is added.
- 2026-08-31 - The user accepted the exact Korean synthetic preview at the
  human utility gate. Treat that direct judgment as the completion signal; do
  not replace it with an automated readability score or another format rule.

## Outcomes & retrospective

Tasks 1-4, the approved transport correction, and the explicit language
boundary are implemented and independently reviewed. The deterministic v2
projection, pure preview command, installed skills, PowerShell 5.1 handoff,
token decoder, language freeze, and language-less compatibility path have
focused, full-suite, mutation, and fresh-agent evidence. The language review's
one Important storage-compatibility finding was reproduced, fixed with a
minimal serialization rule, and covered by two regressions. The user confirmed
that the exact Korean synthetic preview preserves sharpness and makes the
judgment, boundary, and revisit condition quickly recoverable. All planned
gates are closed without a Notion call or journal-state mutation.

## Context and orientation

The accepted behavior is defined in
`docs/designs/2026-08-26-user-invoked-notion-judgment-journal.md`. The prior
baseline implementation is described historically in
`docs/plans/completed/2026-08-26-user-invoked-notion-judgment-journal.md`.

The implementation surfaces are:

- `.agents/skills/record-notion-journal/agents/openai.yaml`: discovery policy
  and user-facing skill metadata. Change the record policy from false to true;
  setup and diagnosis policies remain unchanged.
- `.agents/skills/record-notion-journal/SKILL.md`: self-contained authority,
  suggestion, adaptive interview, preview, deterministic sync, and terminal
  contracts. The normal new-record path must not require the operator guide.
- `.agents/skills/setup-notion-journal/SKILL.md`: asks for `ko` or `en` and
  passes the explicit value during initial configuration or a later change.
- `scripts/notion_journal/model.py`: validates the closed language enum without
  adding it to the nine-field semantic draft.
- `scripts/notion_journal/store.py`: accepts old language-less configuration
  and envelopes, freezes language in new v2 envelopes, and includes it in new
  key material without changing legacy keys.
- `scripts/notion_journal/hooks.py`: `_expected_properties(envelope)` and
  `_expected_body(envelope)` generate the exact create/update payload and are
  reused by `_validate_create_input` and `_validate_update_input`.
  Change only the `JudgmentDraft` branches.
- `scripts/notion_journal/cli.py`: add the JSON-only `preview-judgment` command.
  It reuses `_judgment_from_value`, emits a fixed human preview and a versioned
  ASCII `capture_token`, and does not construct a store, inspect Git, or create
  capture metadata. `record-judgment --input-token -` validates the token and
  then enters the existing capture path.
- `.agents/skills/record-notion-journal/scripts/sync_context.py`: consumes those
  projection functions and emits one exact MCP input. It should need no edit.
- `tests/notion_journal/test_cli.py`: end-to-end v2 capture, projection, write
  guard, correction, empty-evidence, and receipt tests.
- `tests/notion_journal/test_hooks.py` and
  `tests/skills/test_record_sync_context.py`: unchanged v1 and guard regression
  coverage that must remain green.
- `tests/skills/test_notion_journal_skills.py`: package metadata and static
  authority-contract tests. Extend it to validate the scenario fixture without
  pretending static checks prove model behavior.
- `tests/skills/fixtures/record-notion-journal-scenarios.json`: new sanitized
  behavior inputs and pass criteria; no captured model output.
- `AGENTS.md`: short repository-wide trigger and authority summary.
- `docs/development/notion-coding-journal.md`: canonical operator workflow,
  local/remote field boundary, exact retry, and terminal status reference.
- This plan and `docs/plans/active/README.md`: current execution state only.

The local `JudgmentDraft` remains unchanged. `PendingEnvelope` gains optional
language metadata so missing values retain legacy rendering; new configured
captures require `ko` or `en`, and their v2 key material includes it.
`_expected_properties` continues to accept one `PendingEnvelope` and return
`dict[str, object]`; `_expected_body` continues to accept one `PendingEnvelope`
and return `str`. `sync_context.py` must continue to call these functions for
create and update, and the pre-write hook must continue to compare submitted
values for exact equality. Task 1 gives the complete v2 return bodies.

## Plan of work

First lock the smaller v2 projection with failing end-to-end tests. Change only
the existing `JudgmentDraft` branches and prove that generated create/update
inputs pass the guard while an injected local-only property fails. Run the
unchanged v1 and sync-context suites before proceeding.

Second add seven sanitized interaction scenarios, lock machine-readable skill
metadata and package structure, then pressure-test the old guidance and rewrite
the skill under the skill-writing workflows. The bounded pressure run already
proved that conversational selection and questioning can remain contextual but
manual exact-preview rendering cannot be made deterministic by prompt emphasis.

Third add a pure semantic-preview command with focused RED/GREEN tests and an
independent review. It validates the existing draft and returns both the fixed
human preview and its versioned capture token without reading Git or touching
state. Then return to Task 2, replace manual preview formatting with this exact
recipe, and finish its behavior and package review.

Fourth update only the governing agent and operator documents. The fixture
makes pressure runs repeatable but does not introduce a model-output archive,
numeric score, or runtime component.

Finally run all offline checks and fresh-agent scenarios. Record only verdict
counts and concise failure reasons. Show the user one synthetic preview and let
the user decide whether its judgment, boundary, and revisit signal are quickly
recoverable before calling the refinement complete.

## Concrete steps

Run every command from the repository root.

### Task 1: Narrow the deterministic v2 Notion projection

**Files:**

- Modify: `tests/notion_journal/test_cli.py:270`
- Modify: `scripts/notion_journal/hooks.py:116`
- Verify unchanged: `tests/notion_journal/test_hooks.py`
- Verify unchanged: `tests/skills/test_record_sync_context.py`

**Interfaces:**

- Consumes: `PendingEnvelope.draft`, discriminated as `JudgmentDraft` or legacy
  `JournalDraft`.
- Produces: unchanged `_expected_properties(PendingEnvelope) -> dict[str,
  object]` and `_expected_body(PendingEnvelope) -> str` signatures used by the
  sync helper and both write validators.

- [x] **Step 1: Change the v2 projection test and add a negative guard test.**

  Replace the expected v2 properties and headings in
  `test_v2_create_projection_uses_only_the_confirmed_judgment_form` with:

  ```python
  self.assertEqual(
      {
          "Title": "Prefer user-invoked journal entries",
          "Journal Key": journal_key,
          "date:Recorded At:start": envelope.recorded_at,
          "date:Recorded At:is_datetime": 1,
          "AI Contribution": "AI-assisted",
      },
      page["properties"],
  )
  headings = (
      "## 왜 지금",
      "## 무엇이 달라졌나",
      "## 무엇을 판단했나",
      "## 무엇을 감수하거나 제외했나",
      "## 무엇이 이 판단을 바꿀까",
      "## 근거",
  )
  positions = tuple(page["content"].index(heading) for heading in headings)
  self.assertEqual(tuple(sorted(positions)), positions)
  for local_only in (
      "Repository",
      "Branch",
      "Start HEAD",
      "End HEAD",
      "Worktree Digest",
  ):
      self.assertNotIn(local_only, page["properties"])
  self.assertNotIn("## 기여", page["content"])
  self.assertNotIn("## Journal Key", page["content"])
  ```

  Add this separate guard case after the projection test:

  ```python
  def test_v2_write_guard_rejects_a_local_only_property(self):
      self._configure_ok()
      recorded = self._run(
          "record-judgment",
          "--input-json",
          "-",
          "--format",
          "json",
          input_json=self._judgment_dict(),
          cwd=self.repo.path,
      )
      self.assertEqual(0, recorded.returncode, recorded.stderr)
      journal_key = json.loads(recorded.stdout)["journal_key"]
      envelope = JournalStore(self.state_root).read_envelope(journal_key)
      projected = self._run_sync_context("create", journal_key)
      self.assertEqual(0, projected.returncode, projected.stderr)
      tool_input = json.loads(projected.stdout)["tool_input"]
      tool_input["pages"][0]["properties"]["Repository"] = envelope.repository

      denied = self._run(
          "hook",
          input_json=self._tool_event("PreToolUse", tool_input),
          cwd=REPO_ROOT,
      )

      self.assertEqual(0, denied.returncode, denied.stderr)
      self.assertEqual(
          "deny",
          json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"],
      )
      self.assertEqual(
          "pending",
          JournalStore(self.state_root).read_envelope(journal_key).sync_state,
      )
  ```

- [x] **Step 2: Run the two focused tests and observe the intended RED.**

  ```powershell
  python -m unittest tests.notion_journal.test_cli.CliTest.test_v2_create_projection_uses_only_the_confirmed_judgment_form tests.notion_journal.test_cli.CliTest.test_v2_write_guard_rejects_a_local_only_property -v
  ```

  Expected: the first test reports the current extra repository properties or
  duplicate headings, and the second reports pass-through instead of `deny`.
  An import, syntax, fixture, or environment failure is not the intended RED.

- [x] **Step 3: Implement the minimal v2-only projection.**

  In `_expected_properties`, make the `JudgmentDraft` branch exactly:

  ```python
  if isinstance(draft, JudgmentDraft):
      return {
          "Title": draft.title,
          "Journal Key": envelope.journal_key,
          "date:Recorded At:start": envelope.recorded_at,
          "date:Recorded At:is_datetime": 1,
          "AI Contribution": draft.ai_contribution,
      }
  ```

  In `_expected_body`, retain the five current Korean semantic headings,
  evidence rendering, and optional `supersedes`, but end the v2 return after
  evidence:

  ```python
  if isinstance(draft, JudgmentDraft):
      evidence = _bullets(
          (f"`{pointer}`" for pointer in draft.evidence_pointers), empty="- 없음"
      )
      supersedes = ""
      if draft.supersedes is not None:
          supersedes = f"\n\n## 대체하는 기록\n\n`{draft.supersedes}`"
      return (
          f"## 왜 지금\n\n{draft.why_now}\n\n"
          f"## 무엇이 달라졌나\n\n{draft.understanding_shift}\n\n"
          f"## 무엇을 판단했나\n\n{draft.human_judgment}\n\n"
          f"## 무엇을 감수하거나 제외했나\n\n{draft.tradeoff_boundary}\n\n"
          f"## 무엇이 이 판단을 바꿀까\n\n{draft.revisit_signal}\n\n"
          f"## 근거\n\n{evidence}{supersedes}"
      )
  ```

  Do not edit the following `JournalDraft` branches or either validator.

- [x] **Step 4: Run focused GREEN and unchanged compatibility suites.**

  ```powershell
  python -m unittest tests.notion_journal.test_cli.CliTest.test_v2_create_projection_uses_only_the_confirmed_judgment_form tests.notion_journal.test_cli.CliTest.test_v2_write_guard_rejects_a_local_only_property tests.notion_journal.test_cli.CliTest.test_v2_superseding_projection_passes_the_write_guard tests.notion_journal.test_cli.CliTest.test_v2_empty_evidence_projection_is_explicit -v
  python -m unittest tests.notion_journal.test_hooks tests.skills.test_record_sync_context -v
  ```

  Expected: all selected tests pass; v1 create/update inputs still pass their
  exact guard and v2 corrections still expose only the optional supersedes key
  in the body.

- [x] **Step 5: Inspect the Task 1 diff checkpoint.**

  ```powershell
  git diff -- scripts/notion_journal/hooks.py tests/notion_journal/test_cli.py
  git diff --check
  ```

  Expected: only the `JudgmentDraft` projection and focused tests changed. Stop
  for user direction if model, store, CLI, v1, or hook registration changes
  appear necessary.

### Task 2: Make the record skill discoverable, adaptive, and self-contained

**Files:**

- Modify: `tests/skills/test_notion_journal_skills.py:12`
- Create: `tests/skills/fixtures/record-notion-journal-scenarios.json`
- Modify: `.agents/skills/record-notion-journal/agents/openai.yaml:1`
- Modify: `.agents/skills/record-notion-journal/SKILL.md:1`

**Interfaces:**

- Consumes: a natural-language explicit request, an accepted bounded AI
  suggestion, or one exact retry key.
- Produces: no state until one exact semantic preview is confirmed; after
  capture, produces the unchanged `record-judgment` JSON interface and one
  exact generated MCP payload for separate approval.

- [x] **Step 1: Add the scenario fixture contract and observe RED.**

  In `tests/skills/test_notion_journal_skills.py`, import `json`, define the
  fixture path, and add the bounded shape and sanitization test retained as a
  moved prerequisite in Task 4. Also change
  `EXPECTED_SKILLS["record-notion-journal"]` to `True`, but do not assert that
  prose fragments occur in `SKILL.md`. Run the fixture test and confirm it fails
  only because the JSON file does not exist.

- [x] **Step 2: Create the seven sanitized behavior cases and run shape GREEN.**

  Create
  `tests/skills/fixtures/record-notion-journal-scenarios.json` with exactly the
  seven IDs, inputs, and pass criteria listed under Task 4's moved prerequisites
  below. Run the fixture test and the package metadata test. The metadata test
  should remain RED because implicit discovery is still disabled; the fixture
  shape test must be GREEN.

- [x] **Step 3: Run consuming-agent RED pressure without the record skill.**

  Give each fresh evaluator one fixture input and its pass criteria, but no
  record-skill instructions. Run every case once and run
  `all_fields_supplied` and `voice_preservation` five times each. Store only
  verdict counts and concise sanitized failure/rationalization labels in the
  ignored SDD workspace; do not store responses or hidden reasoning. Confirm
  that the baseline exposes at least one target failure. If it does not, revise
  the scenario pressure rather than weakening the desired behavior.

- [x] **Step 4: Enable natural-language discovery in record metadata.**

  Set the skill frontmatter description and policy to these exact values:

  ```yaml
  description: Use when a ClaimBranch user explicitly asks to record one coding judgment, has just expressed a concrete coding judgment that may merit one non-authoritative suggestion, accepts that suggestion, or explicitly asks to retry one exact journal key.
  ```

  ```yaml
  policy:
    allow_implicit_invocation: true
  ```

  Keep the current Notion dependency and default prompt unchanged.

- [x] **Step 5: Rewrite the rule, selection, and adaptive interview sections.**

  Make `SKILL.md` retain exactly one descriptive H1, stay below the existing
  500-word package limit, and include these exact behavioral clauses in its
  normal path:

  ```markdown
  ## Rule

  A record is valuable only when it reduces future re-decision cost; the user
  alone chooses what is recorded and confirms its meaning.

  Notion is a convenience projection, never project truth.

  ## Selection and authority

  Natural-language selection is not consent. Start an interview only after the
  user explicitly requests a record or accepts one AI suggestion. That choice
  is interview consent, not capture.

  Suggest at most once for the same judgment in the active conversation, only
  after the user explicitly expresses a concrete judgment, understanding shift,
  or boundary. Never suggest solely because files changed, a task completed, or
  a milestone ended. A suggestion, rejection, silence, or pause creates no state.

  Before semantic confirmation, do not call `record-judgment`, create local
  state, mark dismissal, or write to Notion. A pending key alone is not authority.

  ## One adaptive judgment

  One record contains one judgment. If several judgments compete, ask the user
  to choose one; never bundle them.

  Map only meaning the user explicitly expressed into `why_now`,
  `understanding_shift`, `human_judgment`, `tradeoff_boundary`, and
  `revisit_signal`. If all five are clear, ask no question. Otherwise ask about
  one missing or ambiguous field at a time. `Unknown`, `None`, and `Skipped` are
  valid; never add plausible filler.

  Keep one semantic unit per field with the core sentence first. No
  sentence-count rule applies. Preserve distinctive nouns, tensions, and
  negations, including longer wording when compression would change meaning.

  Propose a short searchable title from `human_judgment` and the user's wording,
  never from the task name or changed files. Propose zero to three confirmed
  repository-relative evidence pointers; empty is valid and ten is only the
  runtime safety ceiling.
  ```

- [x] **Step 6: Complete the preview, retry, sync, and terminal boundaries.**

  After Task 3 is reviewed, make the semantic-preview section pipe the proposed
  nine-field JSON object to:

  ```powershell
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $OutputEncoding = $utf8
  [Console]::OutputEncoding = $utf8
  $proposed | ConvertTo-Json -Depth 10 -Compress |
    python -X utf8 -m scripts.notion_journal.cli preview-judgment --input-json - --format json
  ```

  Show the returned `preview` verbatim. On exact confirmation, send only the
  exact returned `capture_token` through a fresh process's standard input to
  `record-judgment --input-token -`. Do not persist, decode, or reconstruct it;
  if it is unavailable, rerun the preview and obtain confirmation again. Use
  `AI-assisted` whenever the AI
  proposed, elicited, summarized, or materially rewrote meaning; retain
  `Human-only` only for exact transport. The deterministic-sync section must
  show the exact generated properties and body, including generated Journal
  Key and Recorded At, immediately before separate write approval. It must
  still pass `tool_input` unchanged.

  Keep the regular path self-contained. Link and load the operator guide only
  in the exact-retry or recovery section:

  ```markdown
  For exact-key retry or recovery, read the
  [operator guide](../../../docs/development/notion-coding-journal.md), then
  read only the user-named `cbj-v1` or `cbj-v2` key.
  ```

  In terminal output, state that waiting for an answer, correction,
  confirmation, or write approval is non-terminal and emits no journal status.
  Keep the four existing terminal lines for actual termination.

- [x] **Step 7: Run consuming-agent GREEN pressure with the revised skill.**

  Rerun the same fresh-agent matrix from Step 3, this time giving each evaluator
  the revised installed record skill, access to the pure preview command, and no
  unrelated repository context. Every criterion must pass. Judge semantic
  selection and questioning as agent behavior; prove the exact preview bytes,
  provenance enum, and no-state boundary with Task 3 tests. If wording is
  ambiguous, make the smallest change that addresses an observed failure and
  rerun the affected case. Do not add a generic example, rubric, score, or rule
  for a hypothetical failure, and do not duplicate the renderer in prose.

- [x] **Step 8: Run GREEN package and skill validation.**

  ```powershell
  python -m unittest tests.skills.test_notion_journal_skills -v
  python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .agents\skills\record-notion-journal
  ```

  Expected: all skill tests pass and the validator prints `Skill is valid!`.
  A shorter prompt is not success if it omits an authority or safety boundary.

- [x] **Step 9: Inspect the Task 2 diff checkpoint.**

  ```powershell
  git diff -- .agents/skills/record-notion-journal/SKILL.md .agents/skills/record-notion-journal/agents/openai.yaml tests/skills/test_notion_journal_skills.py tests/skills/fixtures/record-notion-journal-scenarios.json
  git diff --check
  ```

  Expected: setup and diagnosis skills, MCP dependency configuration, sync
  helper, and runtime state code are unchanged.

### Task 3: Add a pure deterministic semantic preview

**Files:**

- Modify: `tests/notion_journal/test_cli.py`
- Modify: `scripts/notion_journal/cli.py`
- Verify unchanged: `scripts/notion_journal/model.py`
- Verify unchanged: `scripts/notion_journal/store.py`

**Interfaces:**

- Consumes: one stdin JSON object with exactly the existing nine
  `JudgmentDraft` fields.
- Produces: canonical JSON with exactly `preview` and `capture_token`.
  `preview` uses the fixed human labels `Title`, `Why now`, `What changed`,
  `Human judgment`, `Tradeoff or boundary`, `Revisit signal`, `Evidence`,
  `AI contribution`, and `Supersedes`. Empty evidence and supersedes render as
  literal `None`; non-empty evidence renders as a bounded Markdown bullet list.
  `capture_token` is the versioned ASCII handoff of the canonical validated
  input plus its integrity digest; it grants no authority.
- Side effects: none. The command is JSON-only, does not require a Git working
  tree, and must not read or create journal state, a key, a timestamp, a Git
  snapshot, a dismissal marker, or a Notion payload.

- [x] **Step 1: Add focused tests and observe the intended RED.**

  Add tests named for the actual boundary:

  - `test_preview_judgment_emits_exact_human_preview_and_capture_token` checks
    the complete literal preview, exact two-key output, decoded canonical token
    input and digest, and absence of key, time, repository, and sync fields.
  - `test_preview_judgment_is_byte_stable_without_git_or_state` invokes the
    command twice from a temporary non-Git directory with a nonexistent test
    state root, compares stdout bytes, and proves the state root stays absent.
  - `test_preview_judgment_rejects_invalid_input_without_state` covers a missing
    field and unsafe evidence and expects exit 2, empty stdout, and no state.
  - `test_capture_token_can_be_recorded_in_a_fresh_process_without_prior_state`
    passes the returned token through stdin to `record-judgment` in a separate
    process and proves the captured draft is exactly the confirmed object. This
    second command is the first operation allowed to create state.

  Run only these tests. Expected RED is argparse rejecting the unknown command;
  an import, fixture, or environment failure is not the intended RED.

- [x] **Step 2: Implement the smallest pure command.**

  Reuse `_read_one_json` and `_judgment_from_value`; do not add another field
  validator. Add one renderer that consumes the validated `JudgmentDraft`, one
  conversion back to its canonical nine-field object, a token codec, and a
  `preview-judgment --input-json - --format json` parser branch. Add
  `record-judgment --input-token -` while keeping `--input-json -` compatible.
  Emit through `_write_json` so identical input is byte-identical. Do not call
  `_git_root`, `capture_snapshot`, `_store`, `datetime_now_seoul`, projection
  helpers, or any Notion tool from the preview branch.

- [x] **Step 3: Run focused GREEN and compatibility tests.**

  ```powershell
  python -m unittest tests.notion_journal.test_cli.CliTest.test_preview_judgment_emits_exact_human_preview_and_capture_token tests.notion_journal.test_cli.CliTest.test_preview_judgment_is_byte_stable_without_git_or_state tests.notion_journal.test_cli.CliTest.test_preview_judgment_rejects_invalid_input_without_state tests.notion_journal.test_cli.CliTest.test_capture_token_can_be_recorded_in_a_fresh_process_without_prior_state -v
  python -m unittest tests.notion_journal.test_cli -v
  ```

  Expected: all focused tests and the complete CLI suite pass. Verify again that
  the preview test runs from outside Git and leaves its absent state root absent.

- [x] **Step 4: Inspect and independently review the Task 3 checkpoint.**

  ```powershell
  git diff -- scripts/notion_journal/cli.py tests/notion_journal/test_cli.py
  git diff --check
  ```

  Expected: no model, store, key, hook, projection, or state-layout change. The
  reviewer must reject any semantic inference, hidden persistence, or second
  representation contract added by the implementation.

### Task 4: Align governing documentation with the behavior contract

**Files:**

- Verify unchanged: `tests/skills/fixtures/record-notion-journal-scenarios.json`
- Modify: `AGENTS.md:66`
- Modify: `docs/development/notion-coding-journal.md:1`
- Modify: `docs/designs/2026-08-26-user-invoked-notion-judgment-journal.md`

**Interfaces:**

- Consumes: seven sanitized scenario inputs and the accepted design.
- Produces: explicit pass criteria for fresh-agent evaluation plus one concise
  repository rule and one detailed operator reference consistent with the
  skill. It produces no runtime scenario engine or model-output store.

- [x] **Moved prerequisite: Add a failing fixture-contract test in Task 2.**

  Import `json`, define
  `SCENARIOS = Path(__file__).parent / "fixtures" /
  "record-notion-journal-scenarios.json"`, and add:

  ```python
  def test_record_scenarios_are_bounded_reproducible_inputs(self) -> None:
      cases = json.loads(SCENARIOS.read_text(encoding="utf-8"))
      self.assertEqual(
          {
              "natural_language_request",
              "all_fields_supplied",
              "partial_fields",
              "multiple_judgments",
              "task_complete_without_judgment",
              "decline_or_pause",
              "voice_preservation",
          },
          {case["id"] for case in cases},
      )
      for case in cases:
          self.assertEqual({"id", "input", "pass_criteria"}, set(case))
          self.assertTrue(case["input"].strip())
          self.assertTrue(case["pass_criteria"])
          serialized = json.dumps(case, ensure_ascii=False).lower()
          for forbidden in (
              "model_output",
              "transcript",
              "api_key=",
              "bearer ",
              "c:\\\\users\\",
          ):
              self.assertNotIn(forbidden, serialized)
  ```

- [x] **Moved prerequisite: Observe fixture RED in Task 2.**

  ```powershell
  python -m unittest tests.skills.test_notion_journal_skills.RecordSkillTests.test_record_scenarios_are_bounded_reproducible_inputs -v
  ```

  Expected: fail because the fixture does not exist. A JSON or import error
  after the fixture is added is not the intended final state.

- [x] **Moved prerequisite: Create the seven scenarios in Task 2.**

  The JSON top level is an array. Each object has only `id`, `input`, and a
  string-array `pass_criteria`. Use these exact behavioral criteria:

  ```json
  [
    {
      "id": "natural_language_request",
      "input": "Please leave this coding judgment in the Notion journal.",
      "pass_criteria": [
        "Treat the request as interview consent without a second consent question.",
        "Create no key or local state before the exact semantic preview is confirmed."
      ]
    },
    {
      "id": "all_fields_supplied",
      "input": "Why now: automatic summaries became reading debt. Shift: the unit is a human judgment, not a task. Judgment: keep five stable fields but adapt the questions. Boundary: do not add scoring or a queue. Revisit: reopen if readers cannot find the boundary quickly.",
      "pass_criteria": [
        "Ask no semantic question and proceed to one exact preview.",
        "Do not invent evidence or another judgment."
      ]
    },
    {
      "id": "partial_fields",
      "input": "Automatic summaries became reading debt, so I decided that only the user may authorize a record.",
      "pass_criteria": [
        "Map only the two explicit meanings already present.",
        "Ask one question about one materially missing or ambiguous field."
      ]
    },
    {
      "id": "multiple_judgments",
      "input": "I decided to enable natural-language discovery, and separately decided to remove Git metadata from Notion.",
      "pass_criteria": [
        "Ask the user to choose one judgment.",
        "Do not bundle both judgments into one record."
      ]
    },
    {
      "id": "task_complete_without_judgment",
      "input": "The tests pass and the refactor is complete.",
      "pass_criteria": [
        "Do not suggest a record based only on task completion.",
        "Create no journal state and emit no journal status."
      ]
    },
    {
      "id": "decline_or_pause",
      "input": "Context: after I expressed a judgment, you made your one journal suggestion. User: Not now; I may answer the journal question later.",
      "pass_criteria": [
        "Create no candidate, dismissal, suppression, key, or pending record.",
        "Treat a pause as non-terminal; use not required only for an actual cancellation."
      ]
    },
    {
      "id": "voice_preservation",
      "input": "Why now: AI-friendly logs are becoming reading debt. Shift: more context is not always more understandable. Judgment: keep a stable form but 'not an automatic task log'. Boundary: avoid 'average regression plus complexity'. Revisit: reopen if distinctive wording no longer helps readers recover the choice.",
      "pass_criteria": [
        "Preserve both quoted expressions in the proposed title or semantic body.",
        "Do not replace them with generic process-improvement prose."
      ]
    }
  ]
  ```

- [x] **Moved prerequisite: Run fixture and skill tests GREEN in Task 2.**

  ```powershell
  python -m unittest tests.skills.test_notion_journal_skills -v
  ```

  These steps execute in Task 2 so the same cases can drive skill RED/GREEN.
  The tests prove fixture shape and package metadata only; they do not claim
  that an LLM followed the scenarios.

- [x] **Step 5: Align the short root agent rule.**

  In `AGENTS.md`, replace the fixed-question paragraph with a compact summary
  that says: natural-language selection is not authority; one bounded proposal
  is allowed only after an expressed judgment; map the stable five fields first;
  ask one missing or ambiguous field at a time; choose one if several judgments
  exist; confirm the exact semantic preview before any state; and show the exact
  generated Notion payload before separate approval. Point to the operator guide
  only for setup, diagnosis, recovery, exact-key retry, and terminal states.

- [x] **Step 6: Align the detailed operator guide without duplicating the design.**

  In the operator guide:

  - replace the governing quote with the accepted representative invariant;
  - distinguish implicit discovery from interview, capture, and write authority;
  - document the one-suggestion active-conversation limit and no-state result;
  - replace fixed questions with stable fields and adaptive questions;
  - document voice-preserving, core-first concision without a sentence limit;
  - change evidence guidance from "up to ten" to "normally zero to three; ten is
    the safety ceiling";
  - state that repository, branch, HEAD, and digest remain local, while only
    Title, Journal Key, Recorded At, and AI Contribution are v2 properties;
  - remove AI Contribution and Journal Key from the documented v2 body;
  - use the pure preview command for validation and fixed rendering, show its
    `preview` verbatim, and pass its confirmed `capture_token` only through
    standard input without persistence or reconstruction;
  - require the exact post-capture payload display before write approval; and
  - state that waiting is non-terminal and emits no status.

  Set the guide's `last_reviewed` to `2026-08-31` after checking it against the
  accepted design and implementation. Do not change product, architecture,
  validation, setup, or diagnosis documents unless a direct contradiction is
  found; report such a contradiction before editing another canonical surface.

- [x] **Step 7: Run documentation and scoped diff checks.**

  ```powershell
  python scripts/check_docs.py
  git diff --check
  git diff -- AGENTS.md docs/development/notion-coding-journal.md tests/skills/test_notion_journal_skills.py tests/skills/fixtures/record-notion-journal-scenarios.json
  ```

  Expected: documentation checks pass, no stale "fixed five questions" or
  "implicit invocation is disabled" claim remains in governing current docs,
  and no unrelated document changed.

### Task 5: Validate behavior without creating journal debt

**Files:**

- Modify while executing: this plan's four living sections
- Move after all gates pass: this plan to `docs/plans/completed/`
- Modify after completion: `docs/plans/active/README.md`
- Modify after completion: `docs/plans/completed/README.md`

**Interfaces:**

- Consumes: the completed Tasks 1-4 diff and seven sanitized scenarios.
- Produces: offline test evidence, verdict counts without outputs, one
  user-reviewed synthetic preview, and an honest completed or still-active plan.

- [x] **Step 1: Run the complete offline automated boundary.**

  ```powershell
  python -m unittest tests.notion_journal.test_cli tests.notion_journal.test_hooks tests.skills.test_record_sync_context tests.skills.test_notion_journal_skills -v
  python -m unittest discover -s tests -p "test_*.py" -v
  python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .agents\skills\record-notion-journal
  python -m json.tool .codex\hooks.json
  python scripts\check_docs.py
  git diff --check
  ```

  Expected: all tests pass, the skill validator reports `Skill is valid!`, hook
  JSON parses, docs pass, and the whitespace check exits zero. The hook manifest
  is verified even though its registration should be unchanged.

- [x] **Step 2: Run fresh-agent behavioral pressure cases.**

  Reuse the post-skill fresh-agent results from Task 2 if the skill has not
  changed since those runs. Otherwise give each fresh evaluator only the
  installed record skill and one fixture input, evaluate every listed
  `pass_criteria` as true or false, and rerun the same matrix: five evaluators
  each for `all_fields_supplied` and `voice_preservation`, one for every other
  case.

  Record only a table of case ID, pass count, run count, and a one-sentence
  sanitized failure reason in `Artifacts and notes`. Do not store evaluator
  answers. If a failure exposes ambiguous instructions, make the smallest skill
  wording change, add or tighten one criterion, and rerun only the affected case
  plus the full skill tests. Do not add scoring, examples, or rules merely to
  optimize one model response.

- [x] **Step 2A: Close the reviewed transport gap without pre-confirmation
  state.**

  Change `preview-judgment` to return exactly `preview` and `capture_token`.
  The token is `cbj-capture-v1.<base64url canonical JSON>.<sha256>`, contains
  only ASCII, and is deterministic for one validated draft. Add mutually
  exclusive `record-judgment --input-token -` input while retaining the
  existing `--input-json -` route for compatibility. Reject wrong versions,
  malformed base64, non-canonical JSON, digest mismatch, and invalid drafts
  before Git or journal state is read.

  In the skill and operator recipe, set PowerShell's native pipeline and
  console output to UTF-8 and invoke Python with `-X utf8`. Show only the exact
  returned preview to the user. Retain the exact token only in the active tool
  result; after confirmation, send it through the execution tool's standard
  input to `record-judgment --input-token -`. Do not put it in a process
  argument or file. If it is unavailable, rerun the pure preview and obtain
  confirmation again.

  Add focused regressions for deterministic ASCII token output, separate-
  process exact capture, mutation and version rejection with no state, and a
  real PowerShell 5.1 Korean round trip. Also assert complete v2 body equality
  for normal, empty-evidence, and superseding projections. Rerun the fresh
  behavior matrix because the record skill changes.

- [x] **Step 3: Present this exact synthetic utility preview to the user.**

  ```text
  제목: 안정적인 필드, 상황에 맞는 질문
  왜 지금: AI 친화적인 작업 요약이 사람의 읽기 부채가 되었기 때문이다.
  무엇이 달라졌나: 오래 남길 단위는 완료된 작업이 아니라 인간의 판단이다.
  무엇을 판단했나: 다섯 개의 안정적인 필드는 유지하되, 빠졌거나 모호한 의미만 질문한다.
  무엇을 감수하거나 제외했나: 점수, 태그, 후보 대기열, 자동 작업 로그를 추가하지 않는다.
  무엇이 이 판단을 바꿀까: 독자가 판단, 경계, 번복 조건을 빠르게 복원하지 못하면 형식을 다시 검토한다.
  근거:
  - `docs/designs/2026-08-26-user-invoked-notion-judgment-journal.md`
  AI 기여: AI-assisted
  대체하는 이전 기록: 없음
  ```

  Ask only whether the judgment, boundary, and revisit signal are quickly
  recoverable and whether any wording lost the intended sharpness. This is a
  human utility gate, not an automated metric. Create no local envelope and make
  no Notion call for this synthetic preview.

- [x] **Step 4: Reconcile scope and finish the living plan.**

  ```powershell
  git status --short
  git diff --stat
  git diff --check
  ```

  Update `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes &
  Retrospective`, and `Artifacts and notes` with observed evidence. If every
  automated gate and the user utility gate pass, change status to `completed`,
  move this file to `docs/plans/completed/`, remove its active-index link, and
  add one concise completed-index link. Rerun `python scripts/check_docs.py`
  after the move. If any gate remains open, keep status `active` in place and
  state the exact remaining condition; do not call the plan complete.

### Task 6: Make presentation language explicit and immutable

**Files:**

- Modify: `tests/notion_journal/test_model.py`
- Modify: `tests/notion_journal/test_store.py`
- Modify: `tests/notion_journal/test_cli.py`
- Verify unchanged: `tests/notion_journal/test_hooks.py`
- Modify: `tests/skills/test_notion_journal_skills.py`
- Modify: `scripts/notion_journal/model.py`
- Modify: `scripts/notion_journal/store.py`
- Modify: `scripts/notion_journal/cli.py`
- Modify: `scripts/notion_journal/hooks.py`
- Create: `scripts/notion_journal/presentation.py`
- Modify: `.agents/skills/setup-notion-journal/SKILL.md`
- Modify: `.agents/skills/record-notion-journal/SKILL.md`
- Modify: `docs/development/notion-coding-journal.md`

**Interfaces:**

- Consumes: the unchanged nine-field `JudgmentDraft`, explicit `ko` or `en`,
  and old configuration/envelopes with no language field.
- Produces: a no-state language lookup, explicit setup mutation, exact localized
  preview, language-bound `cbj-capture-v2` token, language-bound new judgment
  key, and envelope-frozen Notion body.

- [x] **Step 1: Write focused failing behavior tests.**

  Use hand-written exact Korean and English previews and bodies. Prove that an
  absent language lookup creates no directory; initial configuration requires
  a language; an old configuration decodes as unset; only `ko` and `en` are
  accepted; changing the setting is explicit; token capture preserves language
  across processes; different languages produce different keys; later config
  changes cannot alter a pending body; and a language-less envelope retains the
  old Korean body byte-for-byte. Each test must name the production mutation it
  catches rather than grep source wording.

- [x] **Step 2: Run the focused selection and observe RED.**

  ```powershell
  python -m unittest tests.notion_journal.test_model tests.notion_journal.test_store tests.notion_journal.test_cli tests.notion_journal.test_hooks -v
  ```

  Expected: only the newly added language cases fail because the enum, config
  compatibility, token v2, envelope metadata, and localized rendering do not
  exist yet.

- [x] **Step 3: Implement the smallest deterministic language boundary.**

  Keep language out of `JudgmentDraft`. Accept `journal_language: null` only as
  legacy configuration/envelope input. Require `--journal-language ko|en` for
  new `configure`, provide one read-or-explicit-set config command whose read
  path does not construct `JournalStore`, require `--journal-language ko|en`
  for `preview-judgment`, and bind `{draft, journal_language}` into
  `cbj-capture-v2`. Decode before Git or state. Pass the language to capture,
  include it in new key material, and render the body from the envelope only.
  Share the small exact label mapping between preview and body; do not add a
  translation framework, `auto`, remote property, or migration command.

- [x] **Step 4: Run focused tests GREEN, then update skills under pressure.**

  ```powershell
  python -m unittest tests.notion_journal.test_model tests.notion_journal.test_store tests.notion_journal.test_cli tests.notion_journal.test_hooks -v
  python -m unittest tests.skills.test_notion_journal_skills -v
  ```

  Add only the observed missing guidance: setup asks the closed choice, record
  reads it without auto-detection, an unset older config asks once, selected
  language controls questions/summaries/preview/body, original distinctive
  terms survive translation, and later changes affect future records only.
  Re-run five fresh no-guidance and five installed-skill repetitions; store only
  counts and one sanitized failure category.

- [x] **Step 5: Align operator documentation and run the complete boundary.**

  Document initial choice, explicit later change, legacy-unset behavior, frozen
  retries, stable machine/property names, and both PowerShell commands. Then run
  the complete offline suite, quick skill validation, hook JSON parse,
  `python scripts/check_docs.py`, and `git diff --check`. Make no Notion call and
  inspect no live journal state.

## Validation and acceptance

Acceptance requires all of the following observable outcomes:

- `openai.yaml` allows implicit discovery for the record skill, while the skill
  explicitly separates selection from interview, capture, and write authority.
- No suggestion is permitted from task completion, changed files, or milestones
  alone; no suggestion, silence, rejection, or pause creates state.
- Existing user meaning is mapped before questioning; zero questions are asked
  when all fields are clear; only one missing or ambiguous field is asked at a
  time; multiple judgments trigger a user choice.
- The proposed title comes from `human_judgment` and distinctive user wording.
  Field text stays core-first and normally concise without a sentence-count
  validator or generic rewriting.
- Evidence is empty or normally zero to three confirmed relative pointers, with
  ten retained only as the unchanged runtime ceiling.
- Before capture, the semantic preview exposes every confirmed semantic value.
  The pure preview command validates the existing nine-field contract, produces
  byte-identical output for identical input outside Git, and creates no state or
  capture metadata. Its versioned ASCII `capture_token` is sent unchanged only
  through a fresh process's stdin after the user confirms the returned
  `preview`; loss requires another preview and confirmation, not reconstruction.
  Before write approval, the exact generated properties and body expose Journal
  Key and Recorded At. No authorized value is hidden at its gate.
- A generated v2 payload has exactly the four approved logical remote
  properties (with the existing two-key Recorded At encoding) and no duplicate
  contribution or key body headings. Injecting local repository metadata is
  denied by the existing write guard and leaves the envelope pending.
- Local envelopes retain their unchanged repository snapshot and correction
  data; v1 projection, exact retry, guards, and receipts remain green.
- The seven scenario fixtures are sanitized and reproducible. Fresh evaluators
  satisfy every pass criterion without a stored answer corpus.
- The user confirms that the synthetic preview preserves sharpness and makes the
  judgment, boundary, and revisit signal quickly recoverable.
- Full unit tests, skill validation, hook JSON parsing, documentation checks,
  and whitespace checks pass without a Notion call or live-state access.

## Idempotence and recovery

All automated tests use temporary state and are safe to rerun. The runtime
change does not mutate existing envelopes, keys, receipts, or configuration. If
work stops after Task 1, existing local entries remain readable and only future
v2 projection output is narrower. If it stops after Task 3, the pure preview
command remains safe to rerun because it has no stateful path. If it stops after
Task 2, ordinary work still creates no state because lifecycle hooks remain
absent and semantic confirmation still precedes capture.

The scenario fixture is declarative and can be rerun without cleanup. A failed
fresh-agent case produces no stored model answer; retain only its verdict and
sanitized reason. Resume from the first unchecked plan item after inspecting
`git status --short` and current diffs.

Rollback means reverting the scoped skill, projection, test, and documentation
diff through normal version control after separate user authorization. It never
means deleting local envelopes, receipts, or Notion pages. Do not migrate old
pages to the smaller projection and do not repair live state as part of this
plan.

## Artifacts and notes

- Task 1 RED: the old projection exposed five local-only properties and the
  exact guard allowed that old shape, as expected.
- Task 1 GREEN: 4 focused v2 tests and 33 unchanged hook/sync compatibility
  tests passed. Independent task review found no Critical, Important, or Minor
  issue.
- Task 2 behavior: the final template produced a capture-valid complete preview
  in 4/10 cross-model runs (Luna 2/5, Terra 1/3, Sol 1/2). No model response was
  stored. The user approved the pure deterministic-preview scope; Task 2 remains
  active until Task 3 is reviewed and the skill consumes that command.
- Task 3 RED: all four focused tests failed because argparse rejected the absent
  command. GREEN: focused 4/4 and the complete CLI suite 29/29 passed. Review
  found one vacuous no-state assertion; after the scoped test fix, the single
  test 1/1, focused 4/4, and CLI 29/29 passed, and scoped re-review found all
  findings addressed with no new breakage.
- Task 2 final pressure: after two bounded executable-handoff fixes, the matrix
  restarted from zero and passed `all_fields_supplied` 5/5,
  `voice_preservation` 5/5, and each other scenario 1/1. Repeated cases used two
  Luna, two Terra, and one Sol evaluator. Only verdict counts and sanitized
  failure categories were retained.
- Task 2 review: spec compliant and quality approved with no Critical or
  Important issue. The review's one Minor fixture-shape assertion gap was fixed;
  its single test 1/1, full skill suite 16/16, docs, and diff checks passed, and
  scoped re-review found no new breakage.
- Task 4 docs: `check_docs.py` passed for 53 Markdown files, stale governing
  claims were absent, and whitespace checks passed. Independent review found
  the root summary, operator procedure, and accepted-design rationale aligned
  with no issue at any severity.
- Task 5 automated boundary: the focused integration selection passed 78/78;
  full test discovery passed 167 tests with one existing Windows symlink-
  privilege skip; skill validation, hook JSON parsing, 53-file documentation
  checks, and whitespace checks all exited zero. No Notion or live-state action
  occurred.
- Transport control and GREEN: three consumers of the former handoff could not
  guarantee a separate-turn exact capture without inventing retention or
  encoding behavior. The revised skill's Unicode/cross-process case passed 5/5.
  Its first seven-case rerun exposed an authority ambiguity in four fixture
  inputs, not a skill failure: two agents correctly refused an interview without
  consent. After only the fixture premises were clarified, the affected
  `all_fields_supplied` and `voice_preservation` cases passed 5/5 and
  `partial_fields` and `multiple_judgments` passed 1/1; unchanged singleton
  cases remained green. No evaluator response was stored.
- Transport implementation checks: CLI passed 31/31 before the additional
  malformed/non-canonical payload case; that new test passed and failed under
  a temporary decoder mutation before restoration. Full discovery then passed
  170 tests with the same one Windows symlink-privilege skip. The real
  PowerShell 5.1 two-process Korean regression, fresh-process token capture,
  invalid-token-before-Git checks, and three complete v2 body equalities were
  green. Skill 16/16, validation, hook JSON, 53-file docs, and whitespace checks
  also exited zero.
- Repeat whole-change review found no Critical, Important, or Minor issue. Its
  independent read-only verification passed the targeted 73 tests and full 170
  tests with the same one platform skip, plus skill, hook JSON, documentation,
  and whitespace checks. The live Notion path remained intentionally unrun
  because the refinement requires no remote-state mutation; the later language
  boundary and human utility gate were completed offline.
- Language guidance RED: both the no-guidance control and the pre-change
  installed skills passed 0/5. All ten runs inferred Korean from conversation
  instead of requiring the explicit `ko`/`en` choice; no response was stored.
- Language runtime RED/GREEN: ten focused tests first failed on the absent enum,
  config command, token v2, envelope field, key separation, and localization,
  then passed 10/10 after the bounded implementation. The broader CLI and hook
  selection passed 63/63.
- Language skill GREEN: explicit setup choice passed 5/5 and a legacy null
  record flow passed 5/5. No evaluator response was stored. The pure helper
  produced the exact Korean utility preview without a state directory, envelope,
  or Notion call.
- Language boundary review: no Critical or Minor issue. Its one Important
  finding showed that receipt processing normalized a missing legacy language
  into `journal_language: null`. Two regressions failed before the fix and
  passed after `None` became an omitted storage key; explicit-language storage
  remains unchanged. Scoped re-review passed 3/3 relevant tests and found the
  issue fully addressed with no new Critical or Important issue.
- Final automated boundary: full discovery passed 182 tests with one Windows
  platform skip. Both skill validators, hook JSON parsing, the 53-file
  documentation check, and whitespace validation exited zero. No Notion call,
  live journal-state read, envelope capture, commit, or push occurred.
- Human utility gate: the user accepted the exact Korean preview as preserving
  sharpness while exposing the judgment, boundary, and revisit condition. No
  numeric readability score, extra field, local state, or remote record was
  added to obtain that decision.

During implementation, keep only:

- focused RED failure names and why each failure was expected;
- focused and full test counts;
- skill validator, hook JSON, docs, and whitespace verdicts;
- scenario case IDs with pass count, run count, and one sanitized failure reason;
  and
- the user's utility-preview decision.

Do not paste long command output, evaluator responses, real prompts, Notion
identifiers, local absolute paths, credentials, or journal contents into this
plan.
