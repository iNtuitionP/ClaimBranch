# Validation documentation

Validation cases turn product claims into observable end-to-end outcomes. Each
case defines its fixture or preconditions, user actions, expected semantic
state, failure boundaries, and time or quality target.

## Active cases

- [Saturation and operator damage](cases/saturation.md) — the canonical finite
  evidence-to-reasoning-to-manuscript case, with separate AI-off and recorded-
  proposal histories, human authority, debt, replay, and recovery oracles.

Unit and integration tests may later implement parts of a case. Keep the case
at product-observable level and link tests rather than copying their internals.
