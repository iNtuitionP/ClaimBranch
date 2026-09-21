---
kind: exec-plan
status: completed
owners: maintainers
last_reviewed: 2026-09-01
canonical_for: implementation of the Notion judgment journal background field
---

# ExecPlan: Add grounded background to Notion judgment records

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` for runtime changes and
> `superpowers:writing-skills` plus `skill-creator` for the installed skill.
> Use `superpowers:verification-before-completion` before reporting success.

**Goal:** Make every new judgment record self-decoding for a future human by
adding one concise, user-confirmed `background` field without rewriting old
records or increasing reading debt.

**Architecture:** Extend `JudgmentDraft` with a legacy-optional background.
New preview input requires ten exact keys and produces a `cbj-capture-v3`
token. Existing nine-key envelopes remain readable, serialize without a new
null field, keep their v2 journal keys, and render the exact former five-section
body. New records keep the v2 envelope and Notion property schema but render a
localized Background section before Why now. The existing 6,000-byte draft
limit remains unchanged.

**Tech stack:** ASCII Markdown skill package, YAML agent metadata, Python 3
standard library, `unittest`, JSON behavior fixtures, and the existing Notion
journal outbox and projection boundary.

**Spec:** [User-invoked Notion judgment journal design](../../designs/2026-08-26-user-invoked-notion-judgment-journal.md)

## Global constraints

- The user approved one stable background field for new records and exact
  preservation of every existing background-less record.
- Background is the minimum context needed to decode the judgment: what
  situation produced it and what project-specific terms mean. It is not a task
  transcript, implementation inventory, tutorial, or generated project summary.
- AI may propose background from explicit conversation and canonical project
  context, but cannot silently infer or capture it. One missing or ambiguous
  field is asked per turn, and the exact preview remains the semantic authority
  gate.
- A new preview cannot silently omit background. A literal absence value such
  as `None` or `해당 없음` is valid only when the user explicitly confirms it.
- Keep one stable six-field presentation order: background, why now,
  understanding shift, human judgment, tradeoff boundary, revisit signal.
- Preserve distinctive user language. Explain opaque internal labels briefly
  in background instead of expanding every later field.
- Do not increase the per-field 1,000-character limit, total 6,000-byte draft
  limit, evidence limit, remote properties, state machine, or write authority.
- Keep journal keys at `cbj-v2-*`; the persisted envelope architecture and
  projection version do not change. Only the transient confirmation token moves
  from `cbj-capture-v2` to `cbj-capture-v3`.
- Reject old transient tokens and require re-preview plus reconfirmation. Tokens
  are non-durable and may never be reconstructed or persisted.
- Do not migrate, normalize, rewrite, or add `background: null` to existing
  envelopes. Explicit-language and language-less old envelopes both retain
  their former bodies and key material.
- Do not add a Notion database property. Background appears only as the first
  localized body heading and in the exact semantic preview.
- Do not contact Notion, inspect live journal state, create an envelope, commit,
  push, or touch the user-owned `.vscode/` tree during this implementation.
- Preserve the existing dirty worktree. Change only files needed for this
  approved refinement and report unrelated changes untouched.

---

This plan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose and big picture

The current five semantic fields can preserve a sharp decision while still
leaving a future reader unable to decode terms such as “P0,” “saturation,” or a
named fixture. Adding explanation to every field would repeat context and create
more text debt. The background field is one stable decoding key placed first,
so the remaining fields can stay terse and specific.

A new user-approved record will show Background before Why now in both the pure
preview and the Notion body. The deterministic runtime checks structure,
sanitization, and size; the user judges whether the proposed background is
actually sufficient. Existing pending and synced records remain immutable and
continue to project exactly as before.

## Progress

- [x] 2026-09-01 - The user approved a separate background field, exact legacy
  preservation, no automatic reconstruction, and the written design covering
  v3 transient tokens and unchanged v2 journal keys.
- [x] 2026-09-01 - Added focused RED tests for the model, CLI/token, envelope
  compatibility, localized presentation, payload guard, and skill behavior
  contract.
- [x] 2026-09-01 - Implemented the smallest runtime and skill changes that make
  the focused tests pass.
- [x] 2026-09-01 - Updated the accepted design, operator guide, root agent rule,
  and document indexes without rewriting the completed historical plan.
- [x] 2026-09-01 - Closed independent code review with no Critical, Important,
  or Minor issue. Post-change full discovery, skill validators, documentation
  checks, whitespace checks, and four fresh skill-consumer scenarios passed.
- [x] 2026-09-01 - Marked this plan completed for relocation to
  `docs/plans/completed/` after every gate passed.

## Surprises & discoveries

- `JudgmentDraft` currently has nine serialized keys, and the same exact parser
  serves pure preview, token decoding, and the legacy direct-JSON capture path.
  The implementation needs an explicit legacy parsing branch rather than
  weakening the new preview contract.
- Existing envelopes embed the draft directly. A dataclass default alone would
  make `asdict()` add `background: null` during public output, receipt updates,
  and key derivation, so compatible serialization must omit the absent field.
- The token version and journal-key version represent different boundaries.
  The token changes because its exact semantic input changes; the journal key
  stays v2 because the append-only judgment envelope and remote projection
  architecture remain the same.
- An explicit `background: null` initially decoded as if the key were absent.
  That would make a malformed new-shape record silently normalize into the old
  shape on its next write. A focused RED now distinguishes missing from null,
  and the decoder fails closed on null.

## Decision log

- 2026-09-01 - Choose an independent stable field instead of prefixing Why now.
  Mixing the two would conflate decoding context with the trigger for recording.
- 2026-09-01 - Reject AI-derived body-only context. Hidden derivation would let
  unconfirmed text accumulate and violate the no-debt authority boundary.
- 2026-09-01 - Require background for new preview and token flows, while model
  and storage decoding allow absence only to preserve existing records.
- 2026-09-01 - Keep total size at 6,000 bytes. The new field reallocates a fixed
  reading budget rather than licensing longer records.
- 2026-09-01 - Preserve old five-section bodies byte-for-byte and omit an absent
  background from public and storage dictionaries. No placeholder or migration
  is permitted.
- 2026-09-01 - Treat only a missing background key as the old nine-key shape.
  An explicit null key is neither new confirmed content nor legacy absence and
  therefore fails closed instead of being normalized.
- 2026-09-01 - Keep the remote database properties and `cbj-v2-*` keys stable;
  bump only the non-durable semantic confirmation token to v3.

## Outcomes & retrospective

The bounded implementation and review are complete. The initial RED failed
because the model and skill did not recognize background and
the preview still accepted the old shape. Focused model, store, skill, and CLI
tests then passed. Removing the legacy storage omission caused
both targeted compatibility tests to fail on `background: null`; restoring it
returned both to green. Four fresh consuming agents passed complete-background,
missing-background, opaque-term, and background-less-retry scenarios without
storing responses. The post-change full discovery run passed 190 tests with one
Windows privilege-dependent skip before the literal-envelope test was added; the final
run passed 191 tests with the same one skip. Independent code review found no
issue at any severity and returned `Ready: Yes` after 133 relevant tests.

## Context and orientation

The semantic model is `JudgmentDraft` in
`scripts/notion_journal/model.py`. Exact CLI parsing and token generation live
in `scripts/notion_journal/cli.py`. Envelope decoding, key material, public
output, and disk serialization live in `scripts/notion_journal/store.py`.
Localized preview and Notion body rendering live in
`scripts/notion_journal/presentation.py`; both create and update guards consume
that body through `scripts/notion_journal/hooks.py`.

The consuming-agent contract is
`.agents/skills/record-notion-journal/SKILL.md`, with discovery metadata in its
`agents/openai.yaml`. Runtime tests are under `tests/notion_journal/`; structural
and sanitized behavior-fixture tests are under `tests/skills/`. The accepted
design and operator procedure are respectively
`docs/designs/2026-08-26-user-invoked-notion-judgment-journal.md` and
`docs/development/notion-coding-journal.md`.

## Plan of work

Specify compatibility in tests, implement the bounded model and projection
change, rewrite and pressure-test the skill, align canonical documentation, and
then verify the complete offline boundary.

## Concrete steps

### Task 1: Specify the new model and compatibility boundary with RED tests

Edit `tests/notion_journal/test_model.py`, `test_cli.py`, `test_store.py`, and
`test_hooks.py` first.

- Require a non-empty, sanitized `background` in new ten-key preview input.
- Assert Korean and English preview/body order with Background first.
- Assert new tokens start with `cbj-capture-v3` and v2 tokens are rejected
  before Git or state access.
- Assert a fresh token capture retains background in public and stored draft.
- Add literal old nine-key envelope fixtures for both explicit language and no
  language. Read and rewrite them without adding a background key, changing a
  key, or changing their former body.
- Assert new background changes key material, while legacy background absence
  retains the former digest representation.
- Assert the 6,000-byte total limit is unchanged.
- Assert generated and guarded Notion bodies add Background only for new drafts
  and introduce no fifth remote property.

Run the focused tests and record the expected failures before production edits:

    python -m unittest tests.notion_journal.test_model tests.notion_journal.test_cli tests.notion_journal.test_store tests.notion_journal.test_hooks

### Task 2: Implement the bounded runtime change

Edit `scripts/notion_journal/model.py`, `cli.py`, `store.py`, and
`presentation.py`.

- Add a legacy-optional `background` value to `JudgmentDraft`; sanitize it with
  the same 1,000-character boundary as the five existing semantic fields.
- Calculate size and serialized draft material with background omitted when it
  is absent, preserving legacy acceptance and bytes.
- Split exact parsing so preview and v3 token payloads require all ten keys,
  while only the retained direct-JSON compatibility path and store decoder may
  accept the old nine-key form.
- Generate and accept only canonical `cbj-capture-v3` tokens.
- Render Background first when present and no Background line or heading when
  absent.
- Keep key prefixes, envelope version, remote properties, guards, evidence,
  supersedes, language freeze, and state transitions unchanged.

Rerun Task 1 tests until green. Temporarily mutate or locally reverse the new
background requirement and old-envelope omission in turn to prove the tests
fail for the intended reason, then restore the implementation.

### Task 3: Rewrite and pressure-test the skill contract

Add RED expectations in `tests/skills/test_notion_journal_skills.py` and update
the sanitized scenarios in
`tests/skills/fixtures/record-notion-journal-scenarios.json` before editing the
skill.

- Change the stable form from five to six semantic fields and the exact CLI
  handoff from nine to ten keys.
- Define background as a minimum decoding key, not a task summary. Require a
  brief plain-language expansion of opaque project terms.
- Map explicit context before asking, ask only one material gap per turn, and
  make background omission an explicit user choice rather than an AI default.
- Keep the exact-preview confirmation, stdin-only token transport, separate
  exact-payload write approval, and no-state authority boundaries unchanged.
- Keep the package concise and avoid examples or extra rubrics beyond the one
  distinction needed to prevent ungrounded labels.

Run:

    python -m unittest tests.skills.test_notion_journal_skills
    python C:\Users\parkj\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\record-notion-journal

Use fresh consuming agents as required by `superpowers:writing-skills` against
sanitized complete-input, missing-background, opaque-term, and legacy-retry
cases. Store only pass counts and short sanitized failure categories, never
responses or transcripts.

### Task 4: Align canonical documentation

Update the accepted design in place, the operator guide, root `AGENTS.md`, and
the nearest indexes.

- Describe six stable fields, ten exact input keys, v3 transient tokens, first
  Background body heading, fixed total budget, and the user semantic gate.
- State that semantic sufficiency is user-confirmed; deterministic code checks
  only shape, safety, canonical transport, and size.
- State explicit legacy preservation for language-less and language-bound
  background-less envelopes.
- Preserve the former completed plan as historical evidence rather than editing
  its five-field account.

Run:

    python scripts/check_docs.py
    git diff --check

### Task 5: Verify the complete offline boundary

Run all task-relevant and repository-required checks without a Notion call:

    python -m unittest discover -s tests -p "test_*.py"
    python C:\Users\parkj\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\record-notion-journal
    python C:\Users\parkj\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\diagnose-notion-journal
    python -m json.tool .codex\hooks.json > $null
    python scripts/check_docs.py
    git diff --check

Inspect the scoped diff and obtain an independent read-only review. Fix only
findings that are evidenced and within the approved design. If a finding would
add another field, score, migration, automatic context source, or remote
property, stop and ask the user instead of expanding scope.

After every gate passes, update this plan's outcomes, mark it completed, move
it to `docs/plans/completed/`, and update both plan indexes.

## Validation and acceptance

Acceptance requires all of the following:

- A new preview accepts exactly ten keys including background, displays all six
  semantic values in the stable order, and creates no state.
- Background answers the situation/term-decoding role in the skill contract;
  no AI rule silently converts a task summary or repository scan into confirmed
  background.
- Exact user confirmation precedes capture, and exact generated payload approval
  still precedes every Notion create or update.
- The v3 token binds draft plus language and is rejected if old, changed,
  malformed, non-canonical, oversized, or missing background.
- New Notion bodies begin with localized Background and retain the existing four
  logical properties.
- Old nine-key envelopes remain readable, keep their original storage shape and
  key, and render the former body without a placeholder Background section.
- Draft size remains capped at 6,000 bytes and evidence behavior remains
  unchanged.
- Full unit tests, skill validation, hook JSON, documentation checks, whitespace
  checks, and fresh-agent behavior pressure pass offline.

## Idempotence and recovery

All automated tests use temporary state and are safe to rerun. No migration or
live journal operation exists. If work stops after runtime changes, old
envelopes remain readable and new capture is still protected by exact preview
confirmation. If a v2 transient token is encountered, discard it, rerun the
pure preview, and obtain confirmation again.

Rollback means reverting only this plan's scoped runtime, skill, test, and
documentation changes through normal version control after user authorization.
It never means deleting pending envelopes, receipts, or Notion pages.

## Artifacts and notes

Record only focused failure names, pass counts, mutation verdicts, fresh-agent
scenario counts, and short sanitized findings. Do not store model responses,
prompts, journal content, Notion identifiers, credentials, absolute user paths,
or live state.

Observed evidence so far:

- model, store, and skill focus: 68/68 before the final null regression;
- CLI: 39/39;
- final full discovery: 191 passed with one platform skip;
- legacy omission mutation: 0/2 as expected, then 2/2 after restoration;
- fresh consumer behavior: 4/4;
- both skill validators, hook JSON parsing, 54-file documentation checks, and
  whitespace validation exited zero after final review.
- independent code review: 133 relevant tests passed, no issue at any severity,
  `Ready: Yes`.
