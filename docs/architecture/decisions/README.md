# Architecture decision records

An ADR captures one significant decision, the forces that led to it, credible
alternatives, and consequences. Use the [ADR template](../../_meta/templates/adr.md).

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-evidence-and-reasoning.md) | accepted | Separate immutable evidence from branchable reasoning |
| [0002](0002-semantic-branches.md) | proposed | Keep semantic branches distinct from Git branches |
| [0003](0003-ai-proposals.md) | accepted | AI produces proposals, never accepted state |
| [0004](0004-local-layout-and-names.md) | proposed | Normalize local names for the schema spike |
| [0005](0005-human-authority-provenance-and-understanding-debt.md) | accepted | Preserve human authority, contribution provenance, and understanding debt |
| [0006](0006-three-graph-planes-and-provider-boundary.md) | accepted | Separate canonical, context, and execution graph planes |
| [0007](0007-research-episode-and-manuscript-saga.md) | accepted | Bind one research episode to a fenced manuscript saga |

Numbers are never reused. A proposed ADR may change during review. After
acceptance, repair only wording, links, metadata, or explicit supersession;
reverse the decision with a new ADR that names the one it supersedes.

ADRs 0001 and 0003 predate the current template and are explicitly marked
`legacy-minimal`; their accepted reasoning is not reconstructed after the fact.
New and still-proposed ADRs must include decision drivers, options, validation,
and supersession in addition to context, decision, and consequences.
