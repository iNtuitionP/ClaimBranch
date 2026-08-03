---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: rationale and sources for the repository documentation system
---

# Documentation-system research

Reviewed 2026-08-03. The structure was derived from primary product and method
documentation, then reduced for a pre-implementation, LLM-assisted repository.
It is intentionally not a verbatim copy of any one framework.

## Findings

### Agent instructions should be maps

OpenAI's [harness engineering report](https://openai.com/index/harness-engineering/)
describes a large `AGENTS.md` as a context and maintenance problem. Its working
pattern is a short map into a structured, versioned `docs/` system of record,
first-class active/completed plans, and automated structure, link, and freshness
checks. ClaimBranch therefore keeps durable knowledge in `docs/` and leaves only
reading triggers and invariants in `AGENTS.md`.

The official [Codex `AGENTS.md` guide](https://developers.openai.com/codex/agent-configuration/agents-md)
documents root-to-working-directory discovery, closer-file precedence, and a
default 32 KiB project-instruction limit. A Codex process started at the root
does not automatically discover deeper instructions merely because it later
edits a file, so the root guide explicitly tells it when to read
`docs/AGENTS.md`.

Anthropic's [Claude Code memory guide](https://code.claude.com/docs/en/memory)
recommends concise, specific project instructions, supports `@path` imports,
and specifically recommends importing an existing `AGENTS.md`; on Windows the
import is preferable to a symlink. It also distinguishes guidance from
mechanical enforcement. `CLAUDE.md` and `docs/CLAUDE.md` therefore import the
corresponding `AGENTS.md` instead of duplicating policy.

### Plans need a separate lifecycle

OpenAI's [ExecPlan guidance](https://developers.openai.com/cookbook/articles/codex_exec_plans)
treats complex plans as self-contained living documents with continuously
updated progress, discoveries, decisions, outcomes, concrete commands,
recovery, and observable acceptance. ClaimBranch adopts those requirements for
multi-session or risky work and keeps `active/` separate from `completed/`.
Small tasks do not receive ceremonial plans.

### Document authority matters more than one universal taxonomy

[Diátaxis](https://diataxis.fr/) separates tutorials, how-to guides, reference,
and explanation by user need. This is adopted for future user and contributor
learning material, not forced onto product specs, ADRs, design proposals, or
plans, which have different authority and lifecycles.

[arc42](https://arc42.org/overview) covers goals, constraints, context, solution
strategy, building blocks, runtime and deployment views, cross-cutting concepts,
decisions, quality, risks, and glossary. Its own
[technical-documentation principles](https://arc42.org/principles-of-technical-documentation)
stress correctness, currency, relevance, findability, version control, and
continuous updates. ClaimBranch uses these as a lean architecture checklist in
one overview and splits sections only when real complexity warrants it; it does
not pre-create twelve empty files.

The official [C4 model diagram guidance](https://c4model.com/diagrams) says most
teams obtain enough value from system-context and container views and advises
adding diagrams only when they provide value. ClaimBranch therefore postpones
component and code diagrams until implemented boundaries create recurring
questions; code-level diagrams should normally be generated rather than kept as
manual truth.

[The ADR project](https://adr.github.io/) defines an ADR as a record of one
significant decision with its context and consequences. ClaimBranch numbers
ADRs, keeps accepted records stable, and reverses them through explicit
supersession rather than rewriting history.

### Docs-as-code requires mechanical checks

GitLab treats documentation as a continuously updated
[single source of truth](https://docs.gitlab.com/development/documentation/styleguide/)
and runs [documentation tests](https://docs.gitlab.com/development/documentation/testing/)
for Markdown structure, relative links, diagrams, and related integrity. This
supports keeping documentation beside code and running the same checker locally
and in CI.

The workflow follows the current official releases shown by GitHub's
[Actions workflow example](https://docs.github.com/en/actions/tutorials/create-an-example-workflow)
and [Python workflow guide](https://docs.github.com/en/actions/tutorials/build-and-test-code/python):
`actions/checkout` 6.0.2 and `actions/setup-python` 6.2.0. CI pins their full
release commit SHAs rather than mutable major tags.

## Applied structure

| Research conclusion | ClaimBranch choice |
|---|---|
| Give agents a map, not an encyclopedia | Short root `AGENTS.md`; detail in indexed `docs/` |
| Avoid tool-specific duplication | `CLAUDE.md` imports the canonical `AGENTS.md` |
| Separate different authority and lifecycles | Product, target architecture, accepted decisions, draft designs, plans, validation, development, references |
| Preserve current truth and historical rationale differently | Living docs update in place; accepted ADRs and completed plans preserve history |
| Treat a proposal as a proposal | Design and plan statuses never imply implementation |
| Organize user learning by reader need | Introduce Diátaxis folders only when real user documentation exists |
| Keep architecture proportional | One arc42-lite/C4 context map now; deeper views only when useful |
| Make structure testable | Front matter, internal-link, index-reachability, ADR, and ExecPlan checks in CI |

## Deliberate exclusions

- No full arc42 folder skeleton before there is architecture to describe.
- No four-folder Diátaxis taxonomy for internal engineering records.
- No duplicate Codex and Claude policy files.
- No generic archive, raw chat log, LLM handoff, or `final-v2.md` convention.
- No hand-maintained component or code diagrams that duplicate a changing
  implementation.
- No changelog until a user-visible application or release exists.
- No roadmap until priorities need a canonical home distinct from candidate
  release scopes.

These exclusions reduce stale surface area while leaving explicit triggers for
adding each artifact when it becomes useful.
