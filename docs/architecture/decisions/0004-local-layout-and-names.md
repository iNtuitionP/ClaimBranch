---
kind: adr
status: proposed
owners: maintainers
last_reviewed: 2026-08-03
---

# ADR 0004: Normalize local repository names for the schema spike

Basis: implementation hypothesis for the version-1 contract spike

## Context

The design conversation used temporary names such as `.research/`,
`.research-cache/`, `config.yaml`, and `% rg:*` or `% rv:*` manuscript markers.
The product name was decided afterward. Leaving these aliases in the first
implementation would create avoidable migration and collision risk.

## Decision drivers

- Durable and disposable state must be visibly different to prevent accidental
  data loss.
- Repository names should be product-specific and consistent across fixtures,
  docs, CLI output, and future migration tools.
- Configuration and marker syntax must be explicit enough to version safely.
- Stored relationship direction must be unambiguous even when UI copy reverses
  the phrasing.

## Options considered

- Keep the temporary `.research/` names and short markers. Rejected because
  they are generic, collide easily, and preserve vocabulary that predates the
  product contract.
- Rename only the directories while retaining YAML and abbreviated markers.
  Rejected because it leaves one contract spread across mixed naming schemes.
- Adopt product-specific directories, TOML configuration, full marker names,
  and one stored `motivates` direction. This is the proposed choice.

## Decision

The first contract spike uses:

- `.claimbranch/` for durable repository state;
- `.claimbranch-cache/` for disposable local projections;
- `.claimbranch/config.toml` for project configuration;
- `% claimbranch:start id=...` and `% claimbranch:end id=...` for LaTeX
  comment markers; and
- `motivates` in the stored edge direction `cause -> planned action`; UI copy may
  render the reverse direction as `motivated by`.

These names are versioned contract choices, not a commitment to a particular
programming language or database binding.

## Consequences

- Early fixtures and documentation use one vocabulary.
- Cache deletion is visibly distinct from deleting durable project state.
- Marker syntax is unlikely to collide with another research tool.
- A future format migration must be explicit and preserve repository history.

## Validation

The contract spike must initialize the proposed durable and cache directories,
rebuild state after deleting only the cache, parse and round-trip
`config.toml`, insert markers without changing rendered LaTeX, and serialize a
`motivates` edge in the documented direction.

## Supersession

None.
