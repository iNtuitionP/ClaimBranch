---
kind: exec-plan
status: completed
owners: maintainers
last_reviewed: 2026-08-20
---

# ExecPlan: deployable Notion journal skills

This plan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose and big picture

Add three repository-scoped Codex skills that make the existing ClaimBranch
Notion journal workflow discoverable and repeatable without weakening its
local-first, approval-gated trust boundary. A contributor can explicitly or
implicitly invoke normal recording and diagnosis, while setup and rollback
remain explicit-only. Repository tests and CI verify the package structure,
activation metadata, safety rules, and canonical documentation links.

## Progress

- [x] 2026-08-19 23:46+09:00 - Confirmed the approved three-skill boundary,
  official `.agents/skills` repository discovery path, and current journal
  CLI, hook, documentation, and Git state.
- [x] 2026-08-19 23:48+09:00 - Established failing structural and adversarial
  contract tests. The baseline run failed only because all three expected
  skill packages were absent (`FAILED (errors=7)`).
- [x] 2026-08-19 23:52+09:00 - Implemented `record-notion-journal`; five
  focused adversarial contracts and the official skill validator pass. Removed
  non-ASCII punctuation after the validator exposed a Windows cp949 failure.
- [x] 2026-08-19 23:55+09:00 - Implemented
  `diagnose-notion-journal`; three read-only classification and routing
  contracts plus the official skill validator pass.
- [x] 2026-08-19 23:58+09:00 - Implemented `setup-notion-journal`; four
  explicit-intent and non-destructive setup contracts plus the official
  validator pass. The first integrated run caught a 563-word body; refactoring
  below the 500-word budget produced a passing integrated baseline.
- [x] 2026-08-20 00:08+09:00 - Closed the fresh-session routing gap with a
  read-only `record-notion-journal` script. Eight subprocess tests prove its
  parameterized query, pre-write-compatible create/update payloads, bounded
  disclosure, no live-state mutation, locked tool roles, and fail-closed
  page-ID validation.
- [x] 2026-08-20 00:11+09:00 - Integrated CI and contributor documentation.
  All 27 skill tests, 75 journal tests, three official skill validators, 49
  Markdown checks, four YAML parses, hook JSON parsing, and whitespace checks
  passed without contacting Notion.

## Surprises & Discoveries

- Official Codex documentation loads repository skills from
  `.agents/skills`; a plugin is unnecessary for a workflow coupled to this
  repository's helper and policy.
- The untracked `.vscode/` directory predates this work and remains outside
  scope.
- A fresh hook context supplies a pending key but the deliberately redacted
  `pending` command excludes data-source routing. A bundled read-only script is
  required to expose only the exact MCP input without reading raw local JSON.
- The documentation checker originally rejected every `SKILL.md` outside
  `docs/`. A regression test now permits only the standard
  `.agents/skills/<name>/SKILL.md` shape while retaining the general ban.
- The bundled script initially allowed a configured search/move/delete-like
  tool name to stand in for a journal role and could quarantine malformed live
  state while reading it. Adversarial tests now require exact role tokens and
  validate temporary copies so live state remains byte-for-byte unchanged.

## Decision Log

- 2026-08-19 - Keep three focused skills: record, diagnose, and setup. Do not
  split drafting from synchronization because their handoff is one retryable
  operation; do not encode maintenance enforcement as a fourth skill because
  hooks, tests, CI, and `AGENTS.md` own mechanical constraints.
- 2026-08-19 - Store the skills in `.agents/skills` with `agents/openai.yaml`.
  This makes them versioned and auto-discoverable from ClaimBranch without
  installing or mutating a user's global skill directory.
- 2026-08-19 - Keep setup implicit invocation disabled. Normal recording and
  read-only diagnosis may use narrow implicit triggers, but every remote write
  still requires its own approval.
- 2026-08-20 - Bundle deterministic query/create/update projection generation
  only with `record-notion-journal`. This keeps fragile payload construction
  aligned with the existing hook guard without modifying trusted hook sources.

## Outcomes & Retrospective

The repository now ships three focused, auto-discoverable skills with UI
metadata and explicit invocation policy. Normal recording uses one tested
bundled script to recover bounded routing and generate parameterized query or
hook-compatible write input; diagnosis remains non-repairing, and setup is
explicit-only and stage-scoped.

CI runs 27 offline skill and adversarial tests. The final pre-close gate also
passed all 75 existing journal tests, three official skill validators, 49
Markdown checks, four YAML parses, hook JSON parsing, and whitespace checks.
No test contacted Notion or used live journal state. A separate fresh-agent
activation evaluation was not dispatched because this session did not have
authorization to delegate; trigger boundaries instead have deterministic
metadata contracts and should be observed again during ordinary use.

## Context and orientation

The implemented automation lives in `.codex/hooks.json`,
`.codex/hooks/notion_journal.py`, and `scripts/notion_journal/`. Its canonical
operator guide is `docs/development/notion-coding-journal.md`; the accepted
trust boundary is in `docs/designs/2026-08-15-notion-coding-journal-automation.md`.
The root `AGENTS.md` requires redacted local envelopes, per-write approval,
untrusted Notion reads, and exactly one terminal journal state.

The new skill directories are `.agents/skills/record-notion-journal`,
`.agents/skills/diagnose-notion-journal`, and
`.agents/skills/setup-notion-journal`. They teach agents to use the existing
deterministic helper and MCP tools; they do not replace the hook as the policy
enforcement boundary.

## Plan of work

First add a standard-library test suite that describes the expected skill
folders, metadata, activation policy, command vocabulary, output contract, and
adversarial stop conditions. Run it and retain the expected missing-skill
failure. Then initialize each skill with the official `skill-creator` script,
replace the template with concise imperative instructions, generate UI
metadata, run focused tests and `quick_validate.py`, and only then proceed to
the next skill. Add a tested read-only bundled script when integrated review
shows that instructions alone cannot safely recover routing state.

Finally add the skill suite to CI and the repository check guide, update the
canonical journal guide with invocation boundaries, run the journal helper
suite plus skill, documentation, YAML/JSON, and whitespace checks, inspect the
scoped diff, and move this plan to completed.

## Concrete steps

Run all commands from the repository root:

```powershell
python -m unittest discover -s tests/skills -p "test_*.py" -v
python -m unittest discover -s tests/notion_journal -p "test_*.py" -v
python scripts/check_docs.py
git diff --check
```

The first skill-suite run must fail because the skill directories do not yet
exist. Final runs must exit zero without contacting Notion or reading the
contributor's live journal state.

## Validation and acceptance

- Codex can discover all three skills from `.agents/skills` and each folder
  passes `quick_validate.py`.
- Descriptions cover positive triggers and avoid workflow shortcuts; setup has
  `allow_implicit_invocation: false`.
- Recording selects at most one key, uses only public redacted state, refuses
  workspace search and duplicates, requests approval immediately before every
  create/update, and emits exactly one terminal state.
- Its bundled script emits only a parameterized exact-key query or one locked
  create/update input and those write inputs pass the existing hook guard.
- Diagnosis is read-only and classifies local state, MCP/OAuth, hook trust,
  schema/tool drift, duplicate, and acknowledgement failures.
- Setup uses only the official endpoint, never overwrites a conflicting MCP
  entry, keeps writes approval-gated, minimizes tools, and never deletes local
  or Notion data during rollback.
- CI, journal tests, documentation checks, skill contracts, frontmatter
  validation, and whitespace checks pass.

## Idempotence and recovery

Installing the skills performs no operation. The record skill's bundled script
is read-only and emits one deterministic payload; it never calls MCP or writes
state. Re-running validation is offline. If scaffolding stops partway through,
inspect the exact skill directory and continue by patching it; do not delete
unrelated files or overwrite user-global skills. Failed tests do not touch
Notion, OAuth credentials, hooks trust, or live journal state.

Rollback is removal of only the three newly tracked skill directories, their
tests, CI step, and documentation references. It must not disable the existing
hook, remove MCP configuration, delete journal state, or delete Notion pages.

## Artifacts and notes

- Baseline commit: `85375f2`.
- Official discovery evidence was read from the current Codex manual on
  2026-08-19; repository-scoped skills use `.agents/skills`.
- The pre-existing untracked `.vscode/` directory is intentionally untouched.
- Final pre-close validation: 27 skill tests and 75 journal tests passed; all
  three skill packages, 49 Markdown files, four YAML files, hook JSON, and the
  whitespace check validated successfully.
