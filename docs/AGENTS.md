# Documentation agent guide

These instructions apply to documentation work. The root `AGENTS.md` remains
the shared top-level contract.

## Before editing

1. Read [README.md](README.md) to identify the canonical document for the
   question.
2. Read [_meta/documentation-policy.md](_meta/documentation-policy.md).
3. Read the nearest area index and every source that the change depends on.
4. If the work meets an ExecPlan trigger, follow [PLANS.md](PLANS.md).

## Rules

- Put intended behavior in `product/`, verified implemented structure in
  `architecture/`, rationale in `architecture/decisions/`, acceptance in
  `validation/`, target or proposed designs in `ARCHITECTURE.md` and `designs/`,
  and execution state in `plans/`.
- Never present a draft design or active plan as implemented behavior.
- Use the required front matter on every state-bearing document. Change
  `last_reviewed` only after checking the content against its canonical inputs.
- Link rather than duplicate. When two canonical documents conflict, preserve
  the distinction, report the mismatch, and update the correct source instead
  of silently choosing one.
- Accepted ADRs are historical records. Limit later edits to typo/link repairs
  and status or supersession metadata.
- A new or moved document must be linked from its area index and remain
  transitively reachable from `docs/README.md`.
- Use relative repository links and lowercase kebab-case filenames, except the
  reserved `README.md`, `AGENTS.md`, `CLAUDE.md`, and `PLANS.md` names.
- Do not hand-edit generated documentation. Change its generator or source.
- Do not store raw research dumps, chat transcripts, agent handoffs, or private
  chain-of-thought in the repository.

## Finish

Run `python scripts/check_docs.py`. Update the relevant product, architecture,
validation, developer, and user documentation in the same change as the code
that invalidated it.
