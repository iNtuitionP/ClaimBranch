# ClaimBranch

**Evidence stays. Claims branch.**

This README is a concise orientation. Start at the
[documentation map](docs/README.md) for canonical status, product,
architecture, validation, and decision sources.

ClaimBranch is a local-first semantic version-control system for the changing
argument of empirical papers. It is designed to help researchers track how an
experimental result changes interpretations, claims, follow-up experiments,
and manuscript text.

> Status: specification and first vertical-slice design. There is no usable
> application in this repository yet.

## The problem

An empirical paper rarely evolves as `experiment -> result -> finished text`.
Unexpected results create competing explanations, invalidate parts of the
current story, motivate new experiments, and leave manuscript edits easy to
forget. Git records file changes, while experiment trackers record runs and
metrics; neither records why the scientific argument changed or whether that
change reached the paper.

ClaimBranch focuses on one workflow:

```text
Result
-> Mismatch
-> Branch
-> Interpretation
-> Claim
-> Follow-up Experiment
-> Manuscript Impact
-> Human Review
-> Partial Merge
-> Verified Paper
```

## Product contract

This is a safety-oriented summary. The
[product specification](docs/product/product-spec.md) and
[decision index](docs/architecture/decisions/README.md) own the detail and
status.

- Completed runs, raw artifacts, and confirmed observations are global,
  append-only evidence. A reasoning branch cannot hide or delete them.
- Interpretations, claims, narratives, follow-up plans, and manuscript patches
  can branch.
- A merge adopts a scientific interpretation into the current paper state; it
  does not decide whether an observation happened.
- Merge is semantic and selective: a researcher can accept a follow-up plan
  while postponing a claim or manuscript patch.
- AI may only propose structure, conflicts, experiments, and patches. It never
  confirms evidence, merges a branch, writes the manuscript, or resolves debt.
  Deterministic code may apply an exact patch only after explicit human
  acceptance.
- The graph is the source model, but the daily starting point is a focused
  decision and debt inbox rather than a full graph canvas.

## Scope

ClaimBranch is not intended to be another experiment scheduler, artifact host,
Overleaf replacement, autonomous AI scientist, or general-purpose Research OS.
Its narrow job is experiment-to-manuscript synchronization.

The first end-to-end slice is specified against a real motivating case: an
expected saturation-only explanation is challenged by pruning and quantization
results, leading to a competing distortion-and-sensitivity claim, new
experiments, and manuscript debt.

## Design documents

- [Documentation map](docs/README.md)
- [Product specification](docs/product/product-spec.md)
- [Draft domain and versioning design](docs/designs/2026-08-03-domain-model.md)
- [Smallest validation prototype](docs/product/releases/validation-prototype.md)
- [Candidate MVP release scope](docs/product/releases/candidate-mvp.md)
- [Saturation acceptance case](docs/validation/cases/saturation.md)
- [Architecture decision index](docs/architecture/decisions/README.md)

## Implementation status

The implementation stack and code layout are deliberately not locked until the
on-disk domain contract and saturation vertical slice have been exercised. See
the [target architecture map](ARCHITECTURE.md),
[draft domain model](docs/designs/2026-08-03-domain-model.md), and
[local-layout decision](docs/architecture/decisions/0004-local-layout-and-names.md)
instead of treating an illustrative folder tree as a contract.
