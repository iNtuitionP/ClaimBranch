# ClaimBranch documentation map

This is the required starting point for repository knowledge. It maps a
question to its canonical source and makes draft, current, historical, and
in-progress material visibly different.

## Fast reading paths

- Product or UX work: [product map](product/README.md) ->
  [product specification](product/product-spec.md) -> relevant
  [validation case](validation/README.md); use the
  [UI/UX harness](development/uiux-harness.md) for design exploration and review.
- Current scope and sequencing: [active execution plans](plans/active/README.md)
  -> [alpha feedback and publication sequence](plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#alpha-feedback-and-publication-sequence).
  For the requested next LLM capability, read the
  [optional AI follow-up proposal](plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#optional-ai-follow-up-implementation-plan);
  it preserves the completed manual alpha and separates portable preparation
  from live scope/deployment decisions.
  The [GitHub manual own-project release order](plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#github-manual-release-implementation-order)
  retains the completed first-alpha implementation sequence.
  The [selected key-free personal-workspace boundary](plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#key-free-personal-workspace-alternative)
  prioritizes implementation, early feedback and correction before the protected
  product's native work.
  The [paper-graph amendment](plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#paper-graph-and-usable-delivery-amendment)
  retains the broader product direction.
- Domain or architecture work: [target architecture](../ARCHITECTURE.md) ->
  [architecture status](architecture/README.md) ->
  [draft domain design](designs/2026-08-03-domain-model.md) -> relevant ADR.
- Substantial unresolved change: [design proposal rules](designs/README.md) ->
  [active execution plans](plans/active/README.md) after a direction is chosen.
- Contributor workflow: [development map](development/README.md) ->
  [repository checks](development/workflow.md).
- Documentation work: [documentation policy](_meta/documentation-policy.md) ->
  [templates](_meta/templates/README.md) -> [ExecPlan policy](PLANS.md) when
  applicable.

## Canonical catalog

| Area | Source | Owns |
|---|---|---|
| Product | [Product map](product/README.md) | Product contracts and candidate release scopes |
| Product | [Product specification](product/product-spec.md) | Intended behavior and boundaries |
| Architecture | [Target architecture](../ARCHITECTURE.md) | Draft pre-implementation boundaries and quality constraints |
| Architecture | [Architecture documents](architecture/README.md) | Accepted constraints and decision history |
| Validation | [Validation map](validation/README.md) | End-to-end observable acceptance |
| Designs | [Design proposal index](designs/README.md) | Substantial approaches that are not current truth |
| Plans | [Execution plan index](plans/README.md) | Multi-session execution state and history |
| Development | [Development map](development/README.md) | Contributor procedures and their canonical sources |
| Development | [Repository checks](development/workflow.md) | Durable repository commands and enforcement limits |
| Governance | [Documentation policy](_meta/documentation-policy.md) | Document authority, lifecycle, and update rules |
| Governance | [ExecPlan policy](PLANS.md) | When and how durable plans are maintained |
| Evidence | [Reference index](references/README.md) | External research and its applicability |

The linked document's front matter is the status source of truth. Status words
are scoped by document kind: `draft` or `proposed` is not
implemented truth; `accepted` on an ADR records a decision; `active` on a plan
means work is still in progress. The full lifecycle is defined in the
[documentation policy](_meta/documentation-policy.md).

## Repository status

See the [root README](../README.md) for implementation status. Add generated
reference, user documentation, a changelog, or runbooks when the first real
artifact needs them, not to complete a preconceived folder tree.

The root README uses a [repository banner](assets/claimbranch-banner.svg) and
an [actual synthetic terminal snapshot](assets/terminal-preview.svg). The latter
is rendered from `demo tui --snapshot --ai-off`, not a live-AI observation.

## Rules that keep the map trustworthy

- One fact has one canonical home; other documents summarize and link.
- Living truth is updated in place; Git preserves its old revisions.
- Decisions use ADRs, unresolved substantial approaches use design documents,
  and execution progress uses ExecPlans.
- Every state-bearing document declares its kind, status, owners, and review
  date in front matter.
- Every document is linked from its nearest index and transitively from this
  map.
- `python scripts/check_docs.py` must pass before documentation work is complete.

Codex reads the root `AGENTS.md`; Claude Code imports the same source through
`CLAUDE.md`. Documentation-scoped rules live in `docs/AGENTS.md` and are also
imported by `docs/CLAUDE.md` when Claude enters this tree.
