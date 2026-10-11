# Validation documentation

Validation cases turn product claims into observable end-to-end outcomes. Each
case defines its fixture or preconditions, user actions, expected semantic
state, failure boundaries, and time or quality target.

## Active cases

- [Saturation and operator damage](cases/saturation.md) — the canonical finite
  evidence-to-reasoning-to-manuscript case, with separate AI-off and recorded-
  proposal histories, human authority, debt, replay, and recovery oracles.
- [Personal-alpha feedback tasks](cases/saturation.md#personal-alpha-feedback-tasks)
  — six connected new-content tasks for human argument construction, shared
  evidence, one judgment, hypothetical impact, correction and saved-work return.
- [Optional AI follow-up acceptance proposal](cases/saturation.md#131-optional-ai-follow-up-acceptance-proposal)
  — future scoped-context, selective incorporation, preserved-origin and live
  provider checks; does not enable AI in the current personal release.

Unit and integration tests may later implement parts of a case. Keep the case
at product-observable level and link tests rather than copying their internals.
