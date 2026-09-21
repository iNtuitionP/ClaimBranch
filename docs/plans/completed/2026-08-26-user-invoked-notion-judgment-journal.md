---
kind: exec-plan
status: completed
owners: maintainers
last_reviewed: 2026-08-28
canonical_for: implementation of the user-invoked Notion judgment journal
---

# ExecPlan: user-invoked Notion judgment journal

This plan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose and big picture

After this plan, ClaimBranch repository agents create no coding-journal debt
merely because files changed. A user explicitly starts one judgment interview,
confirms one compact five-part entry and its evidence pointers, and only then
receives a durable retry key and a separately approval-gated Notion write.
Existing v1 records remain readable and explicitly retryable.

The observable proof is offline: lifecycle hooks create no pending envelope;
the CLI creates one stable `cbj-v2` envelope only from exact confirmed input;
the deterministic projection has the five fixed headings; current v1 fixtures
still pass; and fresh agents stop treating a pending hook key as semantic
authorization.

## Progress

- [x] 2026-08-26 20:00+09:00 - Inspected the current skill, hook, local store,
  projection, tests, accepted design, operator guide, and human-authority ADRs.
- [x] 2026-08-26 20:20+09:00 - Ran five fresh-agent RED pressure samples. All
  five chose automatic draft attachment and said a hook-created pending key
  independently authorized material-task recording.
- [x] 2026-08-26 20:30+09:00 - Fixed the design direction: one human judgment,
  explicit interview and preview confirmation, confirmed evidence pointers,
  immutable v2 capture, and superseding corrections.
- [x] 2026-08-28 - Wrote and observed focused RED tests for the
  explicit v2 model, immutable store, CLI capture, projection, lifecycle no-op,
  skill trigger, correction, and hook contracts.
- [x] 2026-08-28 - Implemented `JudgmentDraft`, deterministic
  `cbj-v2` capture, v1/v2 parsing and projection, exact receipt handling, and
  no-op legacy lifecycle paths without touching contributor live state.
- [x] 2026-08-28 - Rewrote the record skill and metadata, retained
  only write guard/receipt hook registrations, and aligned `AGENTS.md`, the
  operator guide, setup, and diagnosis with explicit human invocation.
- [x] 2026-08-28 - Ran five no-guidance controls, five revised-skill
  pressure samples, and forward samples for a sparse new judgment, correction,
  and legacy retry. Revised-skill pressure samples all refused local and remote
  mutation without user authority.
- [x] 2026-08-28 - Ran the full repository suite: 167 tests passed and one
  Windows symlink-privilege case was skipped. The packaged skill, hook JSON,
  52-file documentation check, Python compilation, and whitespace check all
  passed. Independent re-review found no Critical or Important issue.

## Surprises & Discoveries

- The current workflow's remote approval did not protect semantic capture. In
  five of five independent samples, agents explicitly reasoned that a pending
  hook key authorized composing a draft even while the user was offline.
- The existing model already has a useful immutable explicit-decision path.
  The v2 implementation can reuse its snapshot-derived key, atomic envelope,
  deterministic payload, receipt, and retry mechanics while leaving automatic
  session capture dormant.
- The live Notion property schema need not change for the first v2 projection.
  New pages can omit legacy task-only properties and use the existing identity,
  snapshot, and provenance properties.
- Five no-guidance controls also chose to preserve the unrequested key. The
  sharper comparison is therefore the old-skill result (five automatic draft
  choices) against the revised-skill result (five explicit refusals): the old
  instructions overrode otherwise conservative agent behavior.
- The first correction forward sample inserted a redundant interview-consent
  question after an explicit correction request. Stating that the request or
  accepted suggestion is already interview consent removed that fourth gate;
  the fresh retest asked `why_now` directly and preserved the intended three
  decisions.
- One forward-test prompt prohibited all tools while also asking the agent to
  read the skill file. Correcting the harness to permit that single read
  produced the expected immutable legacy-retry sequence; this was a harness
  failure, not a skill failure.
- Independent review found that a v1 rollback enumerates every file in its
  legacy state directories and quarantines unknown envelopes. V2 therefore
  needs a physical directory boundary, not only a key prefix and parser branch.
- The review also reproduced a sanitizer asymmetry: UNC and common private
  POSIX paths, extended credential-variable names, and credential-bearing URL
  userinfo were accepted, while an ordinary HTTPS URL was rejected as a
  Windows drive path. Boundary-aware regression cases now define both sides.

## Decision Log

- 2026-08-26 - One journal entry represents one central human judgment or
  understanding shift, not one task or milestone bundle. This preserves a
  sharp semantic unit and permits zero, one, or multiple records per task.
- 2026-08-26 - AI may propose a record but cannot create semantic or durable
  state. Explicit interview consent and exact preview confirmation are separate
  human decisions; remote write approval is a third boundary.
- 2026-08-26 - Evidence consists of user-confirmed bounded pointers plus a
  deterministic capture snapshot. Automatic changed paths are not represented
  as relevant evidence.
- 2026-08-26 - Confirmed records are immutable. Corrections create a distinct
  entry naming one superseded key; no local or remote record is overwritten.
- 2026-08-26 - Preserve v1 state and sync behavior, add v2 judgment records,
  and remove automatic lifecycle capture rather than migrate or delete history.
- 2026-08-28 - Store v2 envelopes and receipts below a separate `v2/` subtree
  so rolling back cannot reinterpret or quarantine them. Current readers merge
  the versioned views without moving existing files.
- 2026-08-28 - Remove public `draft` and `record-decision` routes. Legacy
  compatibility means immutable read, projection, retry, guard, and receipt;
  it does not include creating or completing new v1 semantic content.
- 2026-08-28 - Require `supersedes` to resolve to a retained local v1 or v2
  envelope before correction capture.
- 2026-08-28 - Do not add an ADR. This contributor workflow applies the
  accepted human-authority constraints in ADRs 0003 and 0005 and changes no
  ClaimBranch product behavior or architecture; the accepted design and
  operator guide are its canonical homes.

## Outcomes & Retrospective

The repository workflow now creates no journal state from ordinary coding or
lifecycle events. An explicit request or accepted suggestion starts a
one-question-at-a-time interview; exact preview confirmation creates one
immutable v2 envelope; and every Notion create or update still requires a
separate approval. Corrections supersede retained records rather than editing
them, while v1 retry, projection, guards, and receipts remain compatible.

Behavioral pressure tests changed from five of five old-skill agents attaching
an inferred draft to five of five revised-skill agents preserving the key and
creating no state. Five no-guidance controls were also conservative. Forward
tests covered a sparse new judgment, a correction, and an unchanged legacy
retry without storing transcripts.

Fresh offline evidence on 2026-08-28 was:

- `python -m unittest discover -s tests -p "test_*.py" -v`: 167 tests passed;
  one unrelated Windows symlink test skipped because the process lacked the
  operating-system privilege to create a symlink.
- the system skill validator reported `Skill is valid!`;
- `python -m json.tool .codex/hooks.json`, Python compilation,
  `python scripts/check_docs.py` over 52 Markdown files, and
  `git diff --check` exited zero;
- independent re-review found no remaining Critical or Important issue.

No test or agent sample contacted Notion, read contributor live journal state,
or changed hook trust. After landing, a contributor must inspect the executable
hook changes and re-approve trust before enabling them; live OAuth/write
validation remains a separately authorized operational step, not evidence
needed for this offline repository implementation.

## Context and orientation

The accepted design is
`docs/designs/2026-08-26-user-invoked-notion-judgment-journal.md`. It supersedes
the automatic semantic-capture behavior in
`docs/designs/2026-08-15-notion-coding-journal-automation.md` while preserving
that design's MCP safety boundary.

The user-facing workflow is in
`.agents/skills/record-notion-journal/SKILL.md`; its generated MCP input helper
is `.agents/skills/record-notion-journal/scripts/sync_context.py`. Runtime
models, state, CLI, projections, and hook decisions live under
`scripts/notion_journal/`. Hook registration is `.codex/hooks.json`, with the
launcher at `.codex/hooks/notion_journal.py`. Offline behavior tests live under
`tests/notion_journal/`; skill packaging and contract tests live in
`tests/skills/test_notion_journal_skills.py`.

`SCHEMA_VERSION` currently covers v1 configuration and state. Do not rewrite
that live configuration. Add a v2 journal-key and draft variant while accepting
legacy v1 envelopes at all read, query, validation, acknowledgement, and
diagnosis boundaries.

## Plan of work

First add RED tests. Skill tests require explicit invocation metadata, the
representative invariant, the fixed interview/preview recipe, and exact retry
behavior. Hook tests require `SessionStart` and `Stop` to return without state.
Model and CLI tests define the exact v2 input, sparse values, evidence bounds,
supersedes validation, and stable key. Projection tests define the property
subset and five-heading body while retaining a real v1 fixture.

Then implement a `JudgmentDraft` beside the legacy `JournalDraft`, extend key
and envelope validation to v1 and v2, add `capture_explicit_judgment` and a
`record-judgment` CLI command, and branch deterministic projection by draft
type. Keep the existing legacy draft parser and projection unchanged.

Next remove lifecycle capture registrations and make legacy SessionStart/Stop
handlers no-op. Rewrite the record skill around explicit new-record and
explicit retry paths, set implicit invocation false, and keep the exact-query,
single-write, receipt, untrusted-input, and terminal-state contracts.

Finally update canonical documentation and the root agent instruction, run
fresh-agent pressure samples with the revised skill, address only observed
rationalizations, run full offline validation, inspect the diff, and complete
this plan.

## Concrete steps

Run all commands from `C:\dev\ClaimBranch`.

1. Add tests without changing implementation, then run focused RED commands:

   ```powershell
   python -m unittest tests.notion_journal.test_model -v
   python -m unittest tests.notion_journal.test_store -v
   python -m unittest tests.notion_journal.test_hooks -v
   python -m unittest tests.notion_journal.test_cli -v
   python -m unittest tests.skills.test_notion_journal_skills -v
   ```

   Each new test must fail because the desired behavior is absent, not because
   of an import, fixture, or syntax error.

2. Implement the minimum production behavior for each failing test and rerun
   that exact command until GREEN before taking the next behavior.

3. Validate the packaged skill using the system validator and the repository
   suite:

   ```powershell
   python C:\Users\parkj\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\record-notion-journal
   python -m unittest discover -s tests\skills -p "test_*.py" -v
   ```

4. Run the complete offline boundary:

   ```powershell
   python -m unittest discover -s tests\notion_journal -p "test_*.py" -v
   python -m json.tool .codex\hooks.json
   python scripts\check_docs.py
   git diff --check
   ```

5. Re-run at least five fresh-agent versions of the automatic-pending pressure
   scenario with the revised skill. Every agent must refuse to compose, attach,
   delete, or sync a key without explicit user intent. Run separate application
   scenarios for a new sparse judgment, a confirmed correction, and an explicit
   legacy retry. Do not contact Notion or contributor live state.

6. Inspect `git status --short` and the scoped diff. Preserve `.vscode/` and all
   unrelated branch work. Do not commit, push, trust hooks, migrate live state,
   or call Notion without a separate user request.

## Validation and acceptance

Acceptance requires all of the following:

- no registered lifecycle hook creates or reminds about an unrequested entry;
- the public skill cannot invoke implicitly and a pending key alone does not
  authorize any local or remote action;
- a new v2 envelope cannot exist before exact preview confirmation in the
  documented workflow;
- v2 capture accepts explicit sparse values and no evidence pointers, rejects
  unsafe or malformed fields, and is idempotent for identical confirmed input;
- v2 correction keys differ and name exactly one valid superseded key;
- v2 projection contains the fixed five headings in order, confirmed evidence
  pointers, provenance, and key, with no Purpose, Outcome, Changed paths,
  Verification, Risks, or Next safe action sections;
- v1 parsing, projection, exact query, write guard, receipt, and retry tests stay
  green;
- no test or forward run contacts Notion or reads contributor live journal
  state; and
- full journal, skill, hook JSON, docs, and whitespace checks pass.

## Idempotence and recovery

Tests use temporary Git repositories and test-only journal state. Commands are
safe to repeat. New capture keys are content-derived, so identical confirmed
input at an identical snapshot reuses the same envelope. A different correction
or evidence selection creates a different key.

If implementation stops after adding v2 state but before skill deployment,
existing v1 behavior remains readable and no live state was mutated. If an
unknown v2 envelope reaches older code, it fails closed; retain it and resume
with the forward version. Do not edit, quarantine deliberately, migrate, or
delete contributor state as cleanup.

## Artifacts and notes

Keep only concise test counts, failure reasons, and pressure-test verdicts in
this plan. Do not store raw agent transcripts, prompts, live identifiers, or
Notion results in Git.
