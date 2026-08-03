# ClaimBranch agent guide

This file is the shared instruction source for Codex, Claude Code, and other
repository agents. Keep it short: it is a map and a set of non-negotiable
workflow rules, not the project encyclopedia.

## Start every task

1. Inspect `git status --short`; preserve unrelated and user-authored changes.
2. Read [docs/README.md](docs/README.md) and the canonical documents relevant
   to the task.
3. If documentation may change, read [docs/AGENTS.md](docs/AGENTS.md) and
   [the documentation policy](docs/_meta/documentation-policy.md).
4. For work inside a subtree, follow the closest `AGENTS.md` as well as this
   file. A direct user instruction takes precedence.

## Repository map

- [README.md](README.md): product introduction and current repository status.
- [docs/README.md](docs/README.md): canonical documentation map and reading
  paths.
- [ARCHITECTURE.md](ARCHITECTURE.md): concise target architecture; it is not
  implemented truth while its status is draft.
- `docs/product/`: intended product behavior and release scopes.
- `docs/architecture/`: accepted constraints and decision records.
- `docs/validation/`: executable or observable acceptance cases.
- `docs/designs/`: substantial proposals, including the draft domain model,
  that are not implemented truth.
- `docs/plans/`: active and completed multi-session execution plans.
- `docs/development/`: durable contributor commands and workflows.

## Documentation contract

- `docs/` is the version-controlled system of record. Chats, hidden memory,
  issue comments, and local notes are not project truth.
- One fact has one canonical home. Summaries must link to it instead of copying
  its detail.
- Classify documentation impact for every behavior or architecture change and
  update affected docs in the same change. If there is no impact, report that
  explicitly; do not create a summary file.
- Update living documents in place. Do not create `v2`, `final`, handoff, or
  session-transcript Markdown files.
- Record a durable, significant decision as an ADR. Do not rewrite an accepted
  ADR to reverse it; create a superseding ADR.
- For work spanning multiple sessions, subsystems, risky unknowns, or schema
  and architecture changes, create or update an ExecPlan under
  `docs/plans/active/` following [docs/PLANS.md](docs/PLANS.md).
- Before adding, moving, or retiring a document, update the nearest index and
  keep it reachable from `docs/README.md`.
- Before finishing, run `python scripts/check_docs.py` and all task-relevant
  tests. Do not claim a check passed unless it was run.

## Current project facts

The following are short safety summaries. The
[product specification](docs/product/product-spec.md) and
[decision index](docs/architecture/decisions/README.md) remain canonical.

- The repository is in specification and validation-design stage; no usable
  application or settled implementation stack exists yet.
- Accepted evidence is global and append-only; reasoning may branch.
- AI output is proposal-only. It cannot confirm evidence, merge a semantic
  branch, modify the manuscript, or resolve debt.
- Repository operations and accepted state must remain usable with AI disabled.

When this file grows beyond a quick scan, move explanation into `docs/` and
leave a precise link and trigger here.
