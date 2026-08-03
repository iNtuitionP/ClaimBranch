# Validation documentation

Validation cases turn product claims into observable end-to-end outcomes. Each
case defines its fixture or preconditions, user actions, expected semantic
state, failure boundaries, and time or quality target.

## Active cases

- [Saturation and operator damage](cases/saturation.md) — the canonical first
  experiment-to-manuscript reasoning loop and partial-merge acceptance case.

Unit and integration tests may later implement parts of a case. Keep the case
at product-observable level and link tests rather than copying their internals.
