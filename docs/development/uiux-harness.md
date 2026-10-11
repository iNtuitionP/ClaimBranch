---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-10-07
canonical_for: ClaimBranch UI and UX design workflow
---

# UI/UX design harness

Turn a researcher task into a concrete design that can be compared, exercised
and refined. This is the UI/UX extension of the user-selected
[native implementation harness](implementation-harness.md), informed by the
[YC source assessment](../references/yc-design-with-ai.md). It uses canonical
context, reference selection, small prototypes and checks in the target medium.
It installs no tooling and does not require Superpowers or parallel agents.

The procedure is active; the terminal prototype has graph/outline comparison,
adaptive graph/reader composition, density controls and optional private UI
draft recovery. Its exact behavior belongs to the terminal workflow below.
A reversible view-settings panel now exposes spacing, card detail and reader
pinning; the final visual system remains unfinished. The current synthetic paper fixtures and query service supply
comparison content; see the
[paper model extension](../designs/2026-08-03-domain-model.md#paper-argument-extension-under-review).
The [living workspace design](../designs/2026-09-22-episode-review.md#uiux-baseline-and-next-exploration)
owns the first application. A request to research ends with grounded findings
and next design work; a request to implement continues through its review and
verification without another routine plan approval.

## Load the design context

Start with Git status and the [documentation map](../README.md), then read only
the changed/relevant sources. Reuse context already verified in the session.
After every compaction, follow the mandatory
[canonical resumption reading path](implementation-harness.md#resume-after-context-compaction)
before implementation; a summary does not replace the philosophy and goals.

| Question | Canonical input |
|---|---|
| Who acts, and what should they understand or decide? | [Product definition and journeys](../product/product-spec.md) |
| What is fixed about the graph experience? | [PG-1–PG-5](../product/product-spec.md#7-interaction-and-visual-character), [ADR 0011](../architecture/decisions/0011-paper-argument-graph-workspace.md), [terminal adaptation](../architecture/decisions/0012-terminal-research-workspace.md) |
| What remains a design hypothesis? | [Workspace proposal](../designs/2026-09-22-episode-review.md) |
| What scientific meaning may the UI represent? | [Domain design](../designs/2026-08-03-domain-model.md), source fixtures and current core |
| What works now? | [Terminal prototype](workflow.md#terminal-paper-prototype), [browser baseline](workflow.md#interactive-synthetic-episode-review) and observed checks |
| What proves the user outcome? | [Graph oracles](../validation/cases/saturation.md#102-paper-argument-workspace-oracles), [release gates](../product/releases/validation-prototype.md) |
| Where does work resume? | [Existing ExecPlan amendment](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#paper-graph-and-usable-delivery-amendment) |

Write the slice's brief in the existing design: researcher action, initial
state, content/source, intended outcome, fixed constraints, open questions and
observable failure. Link canonical facts rather than copying a product spec
into a new context file. Resolve ordinary presentation choices locally; ask
only when missing user meaning or a product/authority choice changes the result.

## Explore and compare

1. **Inspect the baseline.** Run the existing view when available and inspect
   wide and narrow layouts in its actual host. Separate observed behavior, code-only
   findings, usability hypotheses and checks that could not run. Preserve
   unrelated work; a passing older storyboard is not proof of a new interaction.
2. **Assemble a small reference board.** Use user-provided references and
   directly inspected public examples. For each reference retain its URL,
   relevant view, what to borrow, what to avoid and the task it serves. Separate
   typography/density references from navigation/interaction references. Put
   the distilled selection in the living design; keep raw research temporary.
   Missing taste preferences can be stated as hypotheses while work continues.
   For this workspace exploration, the user explicitly chose to inspect and
   select references personally on 2026-09-23. Supply candidates, direct viewing
   links and comparison questions; keep adoption pending until that selection.
   The living design records the user's subsequent reference feedback and
   confirmed preference for doing most work inside an actual terminal. Use
   that preference for the next prototypes; do not reopen the medium question
   or treat a terminal-styled web page as an actual-terminal prototype.
   This does not add approval steps for unrelated implementation mechanics.
3. **Make comparable alternatives.** For substantial exploration, start with
   two or three meaningfully different compositions over the same content,
   initial state, tasks and viewport. This is a local working budget, not a YC
   rule. Label the question each variation tests; color swaps alone do not test
   information architecture. Small established-component edits need no gallery.
4. **Compare real interactions.** Use a local comparison page or a terminal
   prototype switcher if it makes switching candidates materially easier. Keep it outside product
   navigation. Inspect long Korean/English content, expanded detail, shared
   evidence, uncertainty and failure states as well as the first viewport.
   Record which elements to retain, revise or discard and the task-based reason.
5. **Tune the chosen composition.** Expose a disposable control only when
   repeated adjustment warrants it: node width, text measure, density, spacing,
   link emphasis or motion. Keep semantics, source text and authority outside
   those controls. Move selected values into the host's shared style/components;
   discard unused variations and controls after their useful comparison ends.
6. **Integrate and verify.** Reuse the existing query/command boundaries,
   exercise the affected research journey, and update its documentation and
   ExecPlan evidence. Human feedback changes the next iteration; it is not a
   mandatory permission gate for routine implementation.

Reference URLs are attribution, not permission to copy arbitrary assets. Do not
send private research to design services. New tools, installations, remote
writes and publishing retain the native harness's existing authority rules.

## Content and implementation discipline

Use source-grounded content early. A node must say enough to understand its
scientific subject; test the visible wording and the available definitions.
Do not fill a missing measurement or claim relation with a plausible invention.
An illustrative paper dataset must be separately labeled synthetic, leaving
the integrity-checked F0 source intact. Synthetic projection experiments may
precede model integration; persistent semantics require the domain review.

Reuse the existing Python query/command boundaries for terminal exploration;
the current HTML/CSS/JavaScript adapters remain the browser baseline. Select
any new presentation library proportionally to the prototype, without changing
the scientific core to accommodate layout. Compare interaction in running
code. Raster mockups can inform an aesthetic but cannot prove reading order,
focus, graph navigation, editable rationale or state transitions. Keep generated
storyboards reproducible through their source/template. The application and
its core own behavior; presentation must not duplicate scientific state rules.

Make shared visual values explicit as they are selected: typography, spacing,
surfaces, content density, semantic status, focus and motion. Preserve text and
structural cues for distinct scientific relationships and actual/proposed/
hypothetical state. A reference palette never overrides those distinctions.
The detailed [product authority and manuscript contract](../product/product-spec.md)
continues to govern every candidate.

## Evaluate the design

Use the existing graph oracles as acceptance criteria. For each relevant task,
record the observed result, remaining friction and next change. At minimum the
paper-workspace comparison should let a reviewer:

- explain a visible node and follow the paper argument to its evidence;
- find another use of shared evidence without treating it as a new fact;
- inspect a hypothetical result's reach and the support that remains;
- form one judgment in context and locate AI influence after editing; and
- distinguish a preview, accepted reasoning and unfinished manuscript work.

Automated checks can establish rendered state and invariants. Agent inspection
can identify likely friction. Neither certifies an unfamiliar researcher's
understanding. Collect human task observations before claiming usability or
closing the release's human gates; do not replace them with taste scores.

For changed interactions, check desktop and narrow reflow, keyboard/focus,
text independent of color, long content, reduced motion and relevant pending,
stale, cancelled and resumed states. Use the existing Chrome smoke for its
documented coverage; add behavior checks when new interactions require them.
Screen-reader and supported-platform coverage remain explicit separate checks.

For TUI work, exercise the real terminal, resize, pane/focus restoration,
Korean input and character width, paste, scrolling, interruption and clean exit.
Automated widget checks and browser screenshots alone do not establish those
results. Record the host terminal and its observed coverage. Map the graph
oracles to terminal interactions explicitly under ADR 0012; local terminal
checks do not substitute for scientific-comprehension or remote-host evidence.

## Run and record checks

Existing browser-baseline and documentation checks, from the repository root
with the existing Python 3.13 installation:

```sh
python3.13 -m claimbranch demo review --example
python3.13 -m scripts.check_review_browser --chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
python3.13 scripts/verify.py --scope docs
```

The browser path is the available Mac example; use an existing executable on
the host. The [browser command reference](workflow.md#interactive-synthetic-episode-review)
owns its prerequisites, optional screenshot directory and limitations.
For an ordinary terminal interaction increment, run the affected portable
domain/application tests and relevant actual-PTY path, plus `--scope docs`.
Select checks from the changed dependencies rather than requiring every native
key/enrollment/recovery test after each UI edit. A change to those adapters or
their actual callers still requires the affected native checks. Run complete
applicable integration/regression at a release milestone and before a readiness
claim, following the [current source-release order](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#github-manual-release-implementation-order).
`--scope core` retains its full coverage; a selected test run is not a core pass.
The explicit `--scope alpha` now selects portable personal/TUI/actual-PTY and
source-artifact dependencies; native methods stay in core/all. Selected skips
still report incomplete coverage.
Select existing scopes according to the
[verification scope table](implementation-harness.md#run-verification).
The name `harness` covers verification-runner tests, not UX acceptance.
The [terminal command reference](workflow.md#terminal-paper-prototype) owns
`demo tui`, snapshot mode and the actual-PTY checks. The browser commands above
do not verify a terminal interface.

Documentation impact for this harness is contributor workflow, design method
and dependency-specific verification sequencing. It changes no scientific
behavior, accepted ADR or release gate, and does not erase earlier failures.
For later behavior changes, update the relevant product, design and validation
sources in the same change. Finish with actual check results, failed attempts,
coverage gaps and the next concrete action in the existing ExecPlan. Do not
create session reports, duplicate plans or automatic journal entries.
