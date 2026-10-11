---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-23
---

# ADR 0012: Keep research work in the experiment host's terminal

## Context

The user selected an actual terminal for most work on 2026-09-23, then
explicitly requested a prototype and explained why: experiments run through a
server terminal, and ClaimBranch should run in that environment without a
switch to a browser or graphical desktop. This is a workflow requirement,
not only a visual preference for command-like styling.

[ADR 0011](0011-paper-argument-graph-workspace.md) established paper-wide
argument understanding and contextual review. Its initial graphical
presentation assumptions need a terminal interpretation. The
[living design](../../designs/2026-09-22-episode-review.md#uiux-baseline-and-next-exploration)
owns the alternatives and observed prototype limitations.

## Decision drivers

- Remain in the experiment host's terminal, including an SSH session.
- Read scientific content and follow shared evidence without rebuilding the
  argument mentally from IDs or command output alone.
- Inspect an experiment's possible reach before recording a judgment.
- Preserve the surrounding shell's input modes and return predictably.
- Keep scientific authority independent of presentation and deployment host.

## Options considered

- Keyboard-oriented browser workspace: retains a broad canvas, but does not
  satisfy the user's actual-terminal requirement.
- Command/output CLI alone: useful for structured queries and automation,
  but requires repeated reconstruction of reading and review context.
- Persistent TUI with command-line entry: selected for daily interaction.
  Pane navigation can retain context, at the cost of less spatial overview
  and additional Unicode, terminal-size and remote-session testing.

## Decision

Use an actual-terminal workspace as the primary daily interaction. Keep the
paper argument as the organizing structure; represent its relationships with
keyboard-reachable projections, explicit shared-node identity and contextual
impact. Selecting a node replaces pointer hover as the required way to inspect
related content. A separate graphical viewer remains optional and unselected.

The selected experience does not choose a production TUI framework. The first
synthetic prototype may use standard-library Python curses and the existing
paper query/scenario service without a listener, provider or graphical login.
Command output remains available for noninteractive inspection.

## Consequences

Adapt product and validation wording from mandatory spatial/hover mechanics
to observable argument reading and focus navigation. Retain the references'
useful hierarchy, contextual detail and text/argument correspondence.

This does not authorize experiment execution, arbitrary ingestion or protected
writes on a server. ADR 0010's currently scoped macOS authority work is not
server-platform proof. Production server custody, authorization, storage and
recovery remain separate unresolved integration work; a portable synthetic TUI
must not imply they are implemented. No additional machine configuration or
framework installation is required by this decision.

## Validation

Follow the [terminal prototype oracle](../../validation/cases/saturation.md#103-terminal-prototype-oracle)
and the paper argument oracles. Check actual PTY input, resize, Unicode/paste,
state preservation across layouts, shared-evidence traversal, hypothetical
impact, and return to a usable shell. Keep live SSH/Linux, physical IME,
screen-reader and unfamiliar-researcher observations distinct from local
automated evidence. Verify the prototype leaves source history and manuscripts
unchanged.

## Supersession

Partially supersedes ADR 0011's graphical presentation assumptions: a spatial
canvas and pointer hover are not mandatory primary interaction mechanisms.
Its paper-wide argument, contextual review, shared evidence, scenario meaning
and scientific-authority constraints remain accepted. No platform authority
decision is superseded.
