---
kind: policy
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: ExecPlan creation lifecycle and required content
---

# ClaimBranch execution plans

An ExecPlan is a self-contained, living implementation document for work that
cannot be safely held in one short session. It lets a contributor or agent with
only the repository and the plan continue the work and verify the outcome.

## When a plan is required

Create `docs/plans/active/YYYY-MM-DD-short-name.md` when any of these apply:

- work is expected to span more than one meaningful session;
- multiple subsystems or packages must change together;
- storage, schema, security boundary, architecture, or core invariant changes;
- an important unknown requires a spike or prototype;
- migration, rollback, or partial failure needs explicit handling; or
- the user explicitly requests a durable plan.

A typo, isolated documentation repair, mechanical refactor, or small
well-understood change does not need an ExecPlan.

## Non-negotiable properties

Every plan must be:

- self-contained for a repository newcomer;
- written around observable outcomes rather than code volume;
- explicit about repository-relative paths, commands, working directories, and
  expected evidence;
- safe to resume, including idempotence and recovery notes;
- updated as reality changes instead of preserved as an obsolete prediction;
  and
- clear about what is proposed, implemented, validated, and still unknown.

Use the [ExecPlan template](_meta/templates/exec-plan.md). The following sections
are required and remain current throughout execution:

- `Progress`
- `Surprises & Discoveries`
- `Decision Log`
- `Outcomes & Retrospective`

Record timestamps in progress entries. Include evidence for surprising claims.
Capture decisions in the plan while work is active, then create an ADR only for
decisions that remain architecturally significant.

## Lifecycle

1. Create the plan under `plans/active/` with status `planned` or `active` and
   link it from the active-plan index.
2. Update it at every stopping point and whenever validation changes the
   approach.
3. Do not wait until the end to reconstruct discoveries or decisions.
4. When all acceptance criteria pass, write the outcomes and remaining work,
   change status to `completed`, move it to `plans/completed/`, and update both
   indexes.
5. If stopped intentionally, use status `abandoned` and explain the reusable
   outcome and unresolved risks. Do not mark incomplete work completed.

Completed plans are execution history, not current product or architecture
truth. Before moving a plan, update the canonical documents and ADRs that now
own its durable conclusions.

## Prototypes and parallel approaches

A plan may include a bounded spike when it reduces uncertainty. State what the
spike tests, how long it may live, what evidence selects an approach, and how
to remove or integrate it. It is acceptable to keep two paths temporarily when
the plan explains how tests distinguish them and how the losing path is cleaned
up.
