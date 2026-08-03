# Product documentation

These documents describe intended outcomes and boundaries. They may be ahead of
the implementation, so read their front-matter status and validate current
behavior against code and tests once implementation exists.

## Product contract

- [ClaimBranch product specification](product-spec.md) — the canonical intended
  behavior, users, invariants, journeys, non-goals, and success measures.

## Candidate releases

- [Smallest validation prototype](releases/validation-prototype.md) — the first
  narrow product-validation slice.
- [Candidate MVP release scope](releases/candidate-mvp.md) — a broader staged
  release hypothesis, conditional on the prototype.

The [saturation validation case](../validation/cases/saturation.md) supplies the
observable end-to-end fixture used by both release scopes.

Create a single `roadmap.md` only when prioritization must be expressed outside
the release scopes. It should track outcomes and validation gates, not issue
checklists or speculative delivery dates.
