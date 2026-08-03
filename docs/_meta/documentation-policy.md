---
kind: policy
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: repository documentation governance
---

# Documentation policy

This policy makes the repository understandable to people and LLM agents over
many sessions. The goal is not maximum documentation. The goal is a small set
of discoverable, current, non-overlapping sources with explicit authority and
lifecycle.

## Choose the source by the question

There is no single precedence order for unlike questions. Use the source that
is canonical for the question being answered.

| Question | Canonical source |
|---|---|
| What should the product do, and what is out of scope? | `docs/product/product-spec.md` |
| What belongs in a particular candidate release? | `docs/product/releases/` |
| What does the implementation do now? | Code, tests, schemas, fixtures, and generated reference |
| What target boundaries should the first implementation test? | Draft `ARCHITECTURE.md` and `docs/designs/` |
| Which architectural constraints are already accepted? | Accepted ADRs in `docs/architecture/decisions/` |
| Why was a significant choice made? | Accepted ADR in `docs/architecture/decisions/` |
| What substantial design is being considered? | `docs/designs/` |
| What work is underway and how will it be validated? | `docs/plans/active/` |
| What outcome must pass end to end? | `docs/validation/` |
| How does a contributor build, test, or release? | `docs/development/` |
| How does a user learn or operate the product? | Future `docs/user/` topics |
| Which external fact or method informed a choice? | `docs/references/` |

When two sources disagree, first decide whether they answer different
questions. Current code may differ from an intended product contract; that is
an implementation gap, not permission to overwrite either silently. For a
same-question conflict, report it and reconcile the canonical source. Never
pick whichever file makes the current task easier.

## Document types and boundaries

| Type | Location | Contains | Must not become |
|---|---|---|---|
| Index/map | `README.md` files | Navigation and reading paths | A second copy of status, commands, or linked documents |
| Product spec | `product/` | Intended behavior, users, boundaries, acceptance | Implementation progress log |
| Release scope | `product/releases/` | Outcome and gates for one candidate release | Day-to-day task list or promise of dates |
| Target architecture | `ARCHITECTURE.md` | Explicitly unimplemented boundaries and quality constraints to validate | A claim about current code while status is draft |
| Accepted architecture | `architecture/` | Accepted constraints and decision history; later, verified current views | Unresolved implementation hypotheses |
| ADR | `architecture/decisions/` | One significant decision, context, alternatives, consequences | A living architecture overview |
| Design proposal | `designs/` | A substantial unresolved approach and trade-offs | Current truth before acceptance and implementation |
| ExecPlan | `plans/` | Self-contained execution, discoveries, decisions, validation | Product requirements or permanent rationale |
| Validation case | `validation/` | Observable end-to-end input, action, and expected outcome | A vague example with no pass condition |
| Developer guide | `development/` | Durable setup, build, test, release, troubleshooting | Personal machine notes |
| User documentation | future `user/` | Tutorials, how-to, reference, explanation | Product planning or internal design |
| Generated reference | future `generated/` | Reproducible schemas and API surfaces | A hand-edited source |
| Research reference | `references/` | External evidence, access date, applicability | Product truth merely because a source said it |

Create a new area only when the first useful document exists. Do not pre-create
an arc42 section, C4 level, Diátaxis folder, runbook, glossary, or changelog
solely to fill a template.

## Required front matter

Every state-bearing Markdown document, other than an index, agent instruction,
or template, begins with:

```yaml
---
kind: product-spec
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: intended product behavior and boundaries
---
```

- `kind` determines purpose and allowed states.
- `status` must match the lifecycle below.
- `owners` is a durable role, not necessarily an individual.
- `last_reviewed` changes only after the document was checked against its
  canonical inputs. Dates use Asia/Seoul calendar days. Formatting-only edits
  do not refresh it.
- `canonical_for` is required on documents that claim a unique source-of-truth
  role and optional elsewhere.

Allowed lifecycle states:

| Kind family | States |
|---|---|
| Living spec, target/current architecture, domain model, policy, reference, development | `draft`, `active`, `deprecated` |
| ADR | `proposed`, `accepted`, `rejected`, `superseded` |
| Design proposal | `draft`, `in-review`, `accepted`, `rejected`, `withdrawn`, `superseded` |
| ExecPlan | `planned`, `active`, `completed`, `abandoned` |
| Validation case | `draft`, `active`, `retired` |
| Release scope | `draft`, `proposed`, `active`, `retired` |
| Generated document | `generated` |

## Lifecycle rules

- Update living documents in place. Git stores their old versions; do not make
  `-v2`, `-new`, or `-final` copies.
- A proposed ADR may change during review. Once accepted, preserve its decision
  and reasoning. Reverse it with a new ADR whose metadata or body names the
  superseded ADR.
- A design becomes current only after its accepted parts are implemented and
  reflected in product and architecture docs. Acceptance alone is not proof of
  implementation.
- An active ExecPlan is a living working document. On completion, record the
  outcome, distill durable truth into the proper spec, architecture doc, or ADR,
  then move it to `plans/completed/`.
- Plans and ADRs preserve useful history. Obsolete tutorials, how-to guides,
  and references should normally be removed after fixing links; Git is their
  archive. Do not create a generic dumping-ground `archive/`.
- A generated file is changed through its source or generator. Its header must
  identify both once generated documentation exists.

## Change impact matrix

| Change | Documentation updated in the same change |
|---|---|
| User-visible behavior, product boundary, or invariant | Product spec and affected validation case |
| Candidate release scope or gate | Relevant release scope; roadmap when one exists |
| Proposed component, storage, interface, invariant, or trust boundary | Target architecture or design; ADR when the choice becomes significant and accepted |
| Implemented structure or behavior diverges from the target | Code/tests remain current-behavior evidence; reconcile the target/design and create a verified current view when useful |
| Large unresolved design or risky cross-cutting proposal | Design document; do not present it as current architecture |
| Multi-session implementation work | Active ExecPlan |
| CLI, configuration, setup, test, or release command | Developer guide and later user reference as applicable |
| Schema or API that can be derived | Generator/source and generated reference, not a manual copy |
| User workflow | Appropriate tutorial, how-to, reference, or explanation topic once user docs exist |
| No durable behavior or knowledge change | No new document; report `Documentation impact: none` |

## Agent and contributor workflow

Before work:

1. Start at `docs/README.md`, not directory search results or an old chat.
2. Read the canonical sources and their status.
3. State whether the task changes a contract, current behavior, architecture,
   decision, validation, operations, or none.
4. Create an ExecPlan when `docs/PLANS.md` requires one.

During work:

1. Keep accepted facts, proposals, and observations visibly distinct.
2. Update an active plan at each stopping point, especially its progress,
   discoveries, decision log, and acceptance evidence.
3. If implementation contradicts a canonical document, investigate rather than
   silently editing the document to match an accidental behavior.

Before completion:

1. Update canonical documents and indexes in the same change.
2. Check that every new statement is grounded in code/tests, an accepted
   decision, a user-confirmed requirement, a cited external source, or an
   explicitly labeled proposal/hypothesis with a validation path.
3. Run `python scripts/check_docs.py` and task-relevant tests.
4. Report document impact and any intentionally unresolved drift.

## Writing and linking rules

- One document has one primary audience and purpose. Split it when its sections
  have different lifecycles or sources of truth, not merely because it is long.
- Prefer direct, observable statements and acceptance criteria. Label
  hypotheses and proposed numbers; do not turn estimates into measured claims.
- Explain why a constraint exists, but keep historical deliberation in ADRs.
- Use repository-relative Markdown links with descriptive link text. Do not use
  machine-specific absolute paths.
- Put a document in its closest domain folder and link it from the nearest
  `README.md`. It must remain transitively reachable from `docs/README.md`.
- Index membership requires a visible inline Markdown link. Links shown only in
  comments, code examples, or unused reference definitions do not count.
- Keep indexes navigational. If an index repeats status for scanning, CI must
  compare it with the linked document's front matter.
- Use lowercase kebab-case filenames. ADRs use `NNNN-kebab-case.md`; plans use
  `YYYY-MM-DD-kebab-case.md`.
- Raw chat transcripts, prompt dumps, private chain-of-thought, agent handoffs,
  and unexplained research dumps are not project documentation. Distill their
  durable result into the correct document.
- Apply Diátaxis only to user and contributor learning material: tutorial,
  how-to, reference, and explanation answer different reader needs. It is not a
  taxonomy for ADRs, product specs, or plans.

## Automation and gardening

`python scripts/check_docs.py` checks repository-owned Markdown headings and
links plus canonical-document structure, front matter, kind/location,
nearest-index membership, reachability, ADR shape/status parity, and ExecPlan
shape. CI runs the same command. The checker can prove form and discoverability,
not semantic truth. Repository administrators must make `Documentation / check`
a required branch-protection check if a failure must block merge. During related
work, review documents whose `last_reviewed` is old and update the date only
after real verification.

The research and trade-offs behind this policy are recorded in
[the documentation-system research](../references/documentation-system-research.md).
