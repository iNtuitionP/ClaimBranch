---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-08-14
---

# ADR 0005: Preserve human authority, contribution provenance, and understanding debt

Basis: user-confirmed product constraint

## Context

ADR 0003 establishes that AI output is proposal-only, but a proposal flag alone
does not answer three different questions:

- who contributed to an accepted change;
- who was technically allowed to authorize that change; and
- whether the researcher has reviewed the explanation deeply enough for the
  change's scientific impact.

Erasing AI provenance after a human edit would misrepresent authorship. Blocking
all high-impact work until a quiz is completed would make AI unavailable at the
moments it is most useful. Letting AI grade or close its own understanding check
would make the safeguard circular.

## Decision drivers

- The manuscript and scientific judgment remain human-authored even when AI is
  available throughout the workflow.
- Accepted state must not depend on a caller claiming to be human.
- Provenance and understanding are independent and must not collapse into one
  “AI generated” boolean.
- Review friction must increase with impact without punishing routine capture.
- The full accepted repository remains usable with AI disabled.

## Options considered

- Prohibit AI for high-impact work. Rejected because it conflicts with the
  always-available assistant goal and removes useful critique.
- Attach only an “AI generated” tag to final nodes or edges. Rejected because it
  loses edits, adoption, derivation, and correction history and says nothing
  about understanding.
- Let AI generate and grade a mandatory quiz before acceptance. Rejected because
  it delegates the safeguard to the system whose influence is being reviewed.
- Keep an ordered contribution chain, enforce a human capability boundary, and
  track deferrable understanding debt independently. Selected.

## Decision

Every AI result begins as a non-authoritative Proposal. When proposal content
influences an accepted operation, the accepted history retains an ordered
Contribution chain covering AI proposal, human edits, human adoption,
deterministic derivations, and later corrections. Human editing does not erase
AI influence.

Accepted scientific or manuscript-affecting operations require a sealed review
and a short-lived, single-use authorization receipt issued only after a
foreground human gesture. A request field such as actor_class=human never
confers authority. Model-facing processes receive neither signing material nor
a writable accepted-state handle.

Impact controls review:

- low-impact non-authoritative capture stays quiet;
- medium-impact AI-influenced acceptance requires a concise human rationale;
- high-impact AI-influenced acceptance requires one to three contextual
  teach-back prompts or an explicit choice to defer explanation review.

Deferral may permit the scoped accepted operation, but it atomically opens
visible UnderstandingDebt. Only a later foreground human decision may close
that debt. AI may propose questions, summarize context, or point out
inconsistency; it cannot score understanding, declare comprehension, authorize
the operation, or close the debt.

“Not now” is different from deferral: it makes no accepted-state change and
leaves the proposal pending or rejected.

## Consequences

- Proposal provenance remains inspectable even when the final prose is human
  edited.
- High-impact work can continue without hiding the resulting review obligation.
- UI and CLI must state exactly whether accepted state changed and whether debt
  opened.
- Authorization requires a technical trust boundary and negative tests, not
  convention.
- The system can prove recorded lineage and authorization, but not scientific
  truth or actual human understanding.

## Validation

The finite saturation contract must demonstrate:

1. an AI-off history with no Proposal, AI Contribution, trace, or
   UnderstandingDebt;
2. a recorded-proposal history whose accepted operation retains the complete
   contribution chain;
3. forged, stale, replayed, cross-project, model-originated, and
   caller-asserted-human authorization failures;
4. “Not now” leaving accepted state unchanged;
5. high-impact deferral opening visible debt atomically; and
6. only a separately authorized human operation closing that exact debt.

## Supersession

None. This ADR extends ADR 0003.
