---
kind: adr
status: accepted
owners: maintainers
last_reviewed: 2026-09-24
---

# ADR 0013: Recover private terminal drafts separately from research history

## Context

The user requested implementation of the terminal UX review, including editing
and session continuity. Losing a personal note when a terminal process ends
breaks the intended experiment-host workflow. The synthetic TUI still lacks
production research custody; its text cannot become accepted history through
an autosave feature. ADR 0008 already requires private research state outside
Git, and ADR 0012 selects the actual terminal as the primary workspace.

## Decision drivers

- Keep uncommitted writing recoverable without changing scientific authority.
- Preserve Ctrl+S/keep and Esc/cancel as different user intentions.
- Avoid private text entering the source or paper repository implicitly.
- Keep the default synthetic demo disposable and dependency-free.

## Options considered

- Volatile buffers alone: simplest, but process loss erases all writing.
- Save into accepted research history or the checkout: mixes authorities or
  contradicts the private-workspace boundary; rejected.
- Explicit private UI checkpoint outside Git: selected for this prototype.
  It does not select the production research database or backup format.

## Decision

The synthetic terminal may accept an explicit external draft-file path. It
stores personal notes, unaccepted judgment/reason drafts, unfinished editor
text and the last selected branch/node, bound to the exact bundled history.
Kept text and unfinished text remain separate: cancelling an edit must not
apply its text to the node. Resuming unfinished text requires an explicit
editing action. Snapshot mode creates no recovery state.

The adapter rejects paths within Git trees, symbolic-link files, non-private
or non-owned files, competing sessions, malformed data and history mismatch.
It uses private regular files, an exclusive session lock and atomic replacement.
Validation precedes changing the in-memory projection. An unsuccessful save
is visible, retains the buffer and does not report successful custody.

This checkpoint is unaccepted UI state, not evidence, a reviewed Judgment,
provenance, an authorization receipt, a manuscript write or a backup of a
research project. No AI, network, experiment execution or journal write is
involved. It neither initializes nor migrates the production workspace.

## Consequences

Default runs remain volatile. Opt-in runs recover their last completed local
checkpoint; abrupt failure can lose text newer than that checkpoint. File
privacy does not protect against the same user, a privileged process, disk
failure or loss of the host. Undo history, viewport history and hypothetical
scenarios remain session-local. Production custody and SSH usability remain
separate validation work.

The [terminal workflow](../../development/workflow.md#terminal-paper-prototype)
owns commands, keys, checkpoint timing and recovery errors. It must distinguish
an application keep operation from successful persistence and acceptance.

## Validation

- Restart with the same fixture restores branch-bound notes and unfinished
  edits separately, with the research manifest unchanged.
- A second session, wrong fixture, corrupt file, symbolic link or in-Git path
  fails without replacing existing text.
- Injected replacement failure preserves the prior checkpoint.
- A real PTY process-loss/restart exercise recovers unfinished Korean text;
  Ctrl+Z/resume preserves the live editor and restores terminal modes.

## Supersession

None. This adds a bounded prototype recovery adapter under ADRs 0008 and 0012;
it does not supersede accepted research custody or authority decisions.
