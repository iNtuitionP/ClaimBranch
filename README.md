# ClaimBranch

**Evidence stays. Claims branch. The researcher remains the author.**

ClaimBranch is a planned local-first personal research agent for empirical
papers. When an unexpected result challenges an important claim, it preserves
the lineage from evidence through AI contribution and human judgment to the
manuscript consequence, and accepts only changes the researcher knowingly
authorizes.

> Status: specification, architecture, and validation design. There is no
> usable application or settled implementation stack in this repository yet.

Start at the [documentation map](docs/README.md) for canonical product,
architecture, validation, decision, and execution sources.

## Why it exists

Git records file history. Experiment trackers record runs and metrics. Neither
reliably records why an unexpected result changed a scientific argument,
which alternatives remain, how AI influenced the decision, what the researcher
actually authorized, or whether the paper now disagrees with accepted research
state.

ClaimBranch focuses on one loop:

    unexpected result
      -> confirmed evidence
      -> competing interpretation on one reasoning branch
      -> human decision and selected merge
      -> manuscript consequence
      -> exact patch, compile, recovery, and human debt closure

Semantic branching is a mechanism, not the product identity. The daily product
is a calm, focused review of a research situation and its consequence.

## Human-owned AI assistance

AI may be available throughout the workflow, but it remains proposal-only.

- AI cannot confirm evidence, authorize an accepted operation, merge reasoning,
  write the manuscript, or close understanding or manuscript debt.
- An accepted AI-influenced change retains an ordered contribution chain;
  human editing does not erase AI provenance.
- High-impact work asks one to three contextual teach-back questions. The
  researcher may explicitly defer them, but doing so opens visible
  understanding debt that only a human can close.
- “Not now” changes no accepted state.
- The repository, deterministic checks, review history, and manuscript
  recovery must remain usable with AI disabled.

The accepted decisions are recorded in
[ADR 0003](docs/architecture/decisions/0003-ai-proposals.md) and
[ADR 0005](docs/architecture/decisions/0005-human-authority-provenance-and-understanding-debt.md).

## Graph-first, with three kinds of graph

The first foundation is a finite graph contract for one saturation case, not a
universal ontology or graph platform:

1. canonical scientific state: accepted evidence, branchable reasoning,
   decisions, provenance, debt, anchors, and authorized operations;
2. disposable context/retrieval projections for the UI and models; and
3. append-only provider and tool execution traces.

Only the first plane is scientific source of truth. GraphRAG, embeddings,
graph-native storage, a full canvas, and generalized merge behavior require
measured post-validation triggers. See
[ADR 0006](docs/architecture/decisions/0006-three-graph-planes-and-provider-boundary.md).

## First validation wedge

The closed first case contains one research episode, one result artifact, one
run, three confirmed observations, one central claim, one competing
interpretation branch, one selected merge, one marked LaTeX block, one
recoverable compile path, and one human debt closure.

It is exercised in three stages:

- H0: deterministic AI-off and frozen-proposal histories replay to their own
  byte-identical audit goldens; a supported Windows checkout also reaches a
  disposable offline demo in at most five minutes.
- H1: a command-launched local Episode Review adds real foreground
  authorization, teach-back/defer UX, a small pending-review list, and an
  optional bring-your-own OpenAI-compatible endpoint learning path.
- V0: the first three qualifying episodes on the next real paper are compared
  with a preregistered Markdown/checklist baseline.

Passing fixtures validates a foundation, not product success. The candidate
release and integrations remain gated by the live-paper result.

## What ClaimBranch is not

It is not an autonomous scientist, experiment scheduler, artifact host,
Overleaf replacement, general Research OS, model manager, OpenClaw clone,
GraphRAG product, or graph database project. Public packaging, cross-platform
support, collaboration, broad UI, and model-serving operations are deliberately
deferred.

## Canonical sources

- [Product specification](docs/product/product-spec.md)
- [Validation prototype](docs/product/releases/validation-prototype.md)
- [Saturation acceptance case](docs/validation/cases/saturation.md)
- [Target architecture](ARCHITECTURE.md)
- [Draft finite domain model](docs/designs/2026-08-03-domain-model.md)
- [Architecture decision index](docs/architecture/decisions/README.md)
- [Active execution plan](docs/plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md)

The only executable repository check today is documented in
[the contributor workflow](docs/development/workflow.md). Do not publish
planned ClaimBranch commands as working setup instructions until H0 implements
and verifies them.
