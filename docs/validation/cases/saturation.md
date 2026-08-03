---
kind: validation-case
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: saturation workflow acceptance criteria
---

# Canonical acceptance case: saturation and operator damage

This anonymized case is the first ClaimBranch validation fixture. It is not a
scientific conclusion; it is a product scenario derived from the motivating
research workflow.

## 1. Initial `main` state

### Research Question `RQ-01`

Can saturation predict the damage caused by an efficiency operator?

### Hypothesis `H-01`

Saturated paths receive greater damage under pruning, quantization, and
compression.

### Claim `C-01`

```text
Saturation-based sensitivity determines operator damage.
```

Initial status:

```text
lifecycle = active
scientific_maturity = supported
```

### Expected Scenario `S-01`

| Operator | Expected result |
|---|---|
| Pruning | Saturated path has greater damage |
| Quantization | Saturated path has greater damage |
| Compression | Saturated path has greater damage |

### Manuscript bindings

`C-01` is expressed in at least these anchors:

- Abstract central claim;
- Introduction contribution;
- main Results interpretation;
- Discussion;
- Conclusion; and
- any figure or table caption that generalizes across operators.

## 2. Imported evidence

One real-operator experiment produces global evidence:

| Observation | Operator | Expected? | Initial relationship proposal |
|---|---|---:|---|
| `O-01` | Pruning | No | `challenges C-01` |
| `O-02` | Quantization | No | `challenges C-01` |
| `O-03` | Compression | Yes | `supports C-01` |

The source JSON is retained unchanged as an Artifact. Runs and confirmed
Observations are visible from all branches. The three scientific relationships
remain proposals until reviewed by the researcher.

## 3. Competing interpretations

A new semantic branch named `joint-distortion-sensitivity` contains:

- `I-01`: the magnitude of `delta logit` can exceed the local range measured by
  saturation-based sensitivity;
- `I-02`: an operator may shift scores largely in one direction while preserving
  detection ranking, producing little AP damage;
- `I-03`: operators differ in distortion direction, structure, correlation, and
  rank effects; and
- `I-04`: sensitivity is real but insufficient without the distortion induced by
  the operator.

The working Claim `C-02` is:

```text
Operator damage is jointly determined by operator-induced logit distortion
and score sensitivity.
```

`jointly determined` is a conceptual factorization in this fixture. It MUST NOT
be serialized or displayed as a proven multiplicative equation.

## 4. Evidence scope review

Existing synthetic-noise experiments may support the sensitivity component of
`C-02`, but do not establish the operator-distortion component.

The reviewed relationship must therefore retain qualification:

```yaml
relation: supports
source: observation_controlled_endpoint_noise
target: C-02
scope: sensitivity component only
conditions:
  - controlled endpoint perturbation
strength: partial
rationale: >
  The experiment establishes different score sensitivity under controlled
  noise, not the magnitude or structure produced by real operators.
```

Displaying this simply as `supports C-02` is an acceptance failure.

## 5. Follow-up Experiment Plans

The branch records at least:

1. measure operator-specific `delta logit` magnitude;
2. compare paths under fixed absolute logit noise;
3. compare under fixed `||delta logit||`;
4. compare under fixed score-space distortion;
5. measure rank change against AP damage; and
6. apply synthetic perturbation only at the endpoint logit.

Each plan:

- is the target of an incoming `motivates` edge from the Observation or
  Interpretation that caused it;
- the Claim or competing Interpretations it tests;
- `tests.intent`, usually `discrimination` or `measurement`;
- a one-sentence human rationale; and
- the result pattern that would distinguish the alternatives.

## 6. Expected Debt Bundle

Accepting the reviewed challenges to `C-01` creates one bundle rather than many
unrelated notifications.

```text
Debt Bundle: saturation-only claim no longer holds across all operators

Central issue
  Pruning and quantization challenge the scope currently expressed by C-01,
  while compression still supports it under at least one condition.

Affected
  C-01
  Abstract central claim
  Introduction contribution
  Results interpretation
  Discussion alternatives
  Conclusion generalization
  related figure/table captions

Suggested actions
  qualify or contest C-01
  preserve the compression support relationship
  create C-02 as provisional
  reassess the scope of existing evidence
  run discriminating experiments
  review manuscript language
```

Each affected manuscript location is an independently resolvable Debt Item
inside this bundle; resolving the Abstract must not hide an open Conclusion
item.

## 7. Expected semantic diff

```diff
Claims
~ C-01 lifecycle: active (unchanged)
~ C-01 scientific maturity: supported -> contested
+ C-02: provisional

Evidence relationships
+ O-01 challenges C-01
+ O-02 challenges C-01
+ O-03 supports C-01
+ controlled-noise observation supports C-02
  scope: sensitivity component only

Interpretations
+ I-01 delta-logit magnitude
+ I-02 rank-preserving distortion
+ I-03 operator-specific error structure

Experiment Plans
+ fixed absolute noise
+ fixed norm
+ fixed score-space distortion
+ rank-change analysis
+ endpoint-only perturbation

Manuscript
~ Abstract, Introduction, Results, Discussion, Conclusion may be stale

Debt
+ grouped central-claim synchronization bundle
```

## 8. Required partial merge

The acceptance test merges:

```text
[x] C-01 becomes contested on main
[x] reviewed challenge/support relationships
[x] follow-up Experiment Plans
[x] manuscript Debt Bundle
[ ] C-02 becomes the active central claim
[ ] proposed manuscript prose
```

Expected properties:

- `main` and the source branch still see `O-01`, `O-02`, and `O-03`;
- `C-02` remains available on the source branch but is not active on `main`;
- follow-up plans on `main` keep their motivations and target alternatives;
- the omitted patch remains a reviewable proposal; and
- the merge commit records the user's reason for deferring `C-02`.

## 9. Explain-back record

Before a central narrative merge, ClaimBranch asks the researcher to record:

- which scope of `C-01` is challenged;
- why compression does not erase the pruning/quantization mismatch;
- which component of `C-02` existing evidence supports;
- which components remain hypotheses;
- which experiment distinguishes magnitude from ranking explanations; and
- which manuscript locations need revision.

The product stores the response as a Decision. An override is allowed and
recorded. AI may point out inconsistency but cannot grade the researcher's
understanding or complete the merge itself.

## 10. Final verification path

After additional evidence is available, the user may adopt or reject `C-02` and
review a bounded manuscript patch:

```text
review -> edit -> accept -> apply -> compile -> verify debt
```

The flow fails safely if an anchor moved, the source text changed, or LaTeX does
not compile. Debt remains open until a human marks it verified, waived, or
explicitly deferred.

## 11. Acceptance time box

With fixture data already available and scientific judgment already made, a
trained user should complete result import, mismatch confirmation, branch
review, partial merge, and debt triage in ten minutes or less. Time spent running
new experiments is excluded.
