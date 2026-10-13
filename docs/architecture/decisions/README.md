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
| [0006](0006-three-graph-planes-and-provider-boundary.md) | accepted | Separate canonical, context, and execution graph planes; UI admission amended by ADR 0011 |
| [0007](0007-research-episode-and-manuscript-saga.md) | accepted | Bind one research episode to a fenced manuscript saga |
| [0008](0008-private-research-workspaces.md) | accepted | Keep research records in private workspaces outside Git by default |
| [0009](0009-external-inference-and-local-authority.md) | accepted | Keep inference externally operated and enforce research authority locally |
| [0010](0010-macos-first-platform-adapters.md) | accepted | Implement on macOS first with shared research contracts and separate OS authority adapters |
| [0011](0011-paper-argument-graph-workspace.md) | accepted | Make the paper argument graph the primary research workspace; preserve scientific authority boundaries |
| [0012](0012-terminal-research-workspace.md) | accepted | Keep daily research interaction in the experiment host's terminal; adapt argument navigation to keyboard focus |
| [0013](0013-terminal-draft-recovery.md) | accepted | Recover opt-in private terminal drafts without creating accepted research state |
| [0014](0014-device-replacement-recovery.md) | accepted | Restore encrypted research backups with a separately held recovery key and enroll a new device signing key; validation timing amended by ADR 0016 |
| [0015](0015-native-local-enrollment.md) | accepted | Establish local approval bindings through foreground native enrollment in a fixed private namespace |
| [0016](0016-own-project-source-release.md) | accepted | Manual own-project source delivery; first-release protected-custody requirement superseded by ADR 0017 |
| [0017](0017-personal-terminal-alpha.md) | accepted | Deliver a key-free personal terminal workspace, get feedback, then iterate |
| [0018](0018-optional-personal-ai.md) | accepted | Add optional proposal-only AI to the personal workspace after typed origin and return checks; qualify the actual provider separately |
| [0019](0019-reviewed-codex-http-relay.md) | accepted | Replace the CLI-generated request with exactly reviewed HTTP bytes through a one-shot trusted broker; actual service qualification remains separate |
| [0020](0020-retained-proposal-review.md) | accepted | Explicitly review retained AI items against current context without another provider request |
| [0021](0021-external-proposal-import.md) | accepted | Import explicitly unverified external AI responses and review locally without another inference |
| [0022](0022-contextual-advice-and-explicit-edits.md) | accepted | Separate readable contextual advice from explicit, human-selected graph-edit proposals |

Numbers are never reused. A proposed ADR may change during review. After
acceptance, repair only wording, links, metadata, or explicit supersession;
reverse the decision with a new ADR that names the one it supersedes.

ADRs 0001 and 0003 predate the current template and are explicitly marked
`legacy-minimal`; their accepted reasoning is not reconstructed after the fact.
New and still-proposed ADRs must include decision drivers, options, validation,
and supersession in addition to context, decision, and consequences.
