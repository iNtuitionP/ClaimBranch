---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-09-22
canonical_for: YC design-with-AI source assessment and applicability
---

# YC design with AI

## Source and inspection

Reviewed 2026-09-22: [YC Library article](https://www.ycombinator.com/library/So-yc-s-head-of-design-shows-you-how-to-design-with-ai)
and its [30:55 video](https://www.youtube.com/watch?v=VbqaL_eHhKY), published
2026-07-10 with Eve Bouffard and Aaron Epstein. The article embeds a short
introduction, full transcript and chapter metadata. Read the entire transcript
and inspected YouTube storyboard frames from the demonstrations; continuous
audiovisual playback and demonstrated tools were not tested. Transcript names
and speaker labels contain inconsistencies. Links below use YC's chapter markers.

## Observed method

These are paraphrases of demonstrations, not a validated universal process.

| Source | Observation |
|---|---|
| [00:00](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=0s) | Conductor, Paper, voice input and visual references support creation. |
| [04:13–05:23](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=253s) | Paxel explains its purpose; custom controls tune visual parameters. |
| [07:13–08:31](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=433s) | Agent-readable content and feature-request PRs serve different audiences. |
| [12:53–14:34](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=773s) | SOTA combines human-made artwork with rich project context in Markdown. |
| [16:57–21:50](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=1017s) | Moodboards inform sixteen rough website variations, compared in a private gallery. |
| [25:17 onward](https://www.youtube.com/watch?v=VbqaL_eHhKY&t=1517s) | Startup School reuses parameterized templates across visual assets. |

## ClaimBranch interpretation

Our application of this source is owned by the
[UI/UX harness](../development/uiux-harness.md). The demonstration motivates
context, exploration and reusable controls; it does not select ClaimBranch's
style, tools, iteration count or research model.

Keep project context in the existing canonical documents under the
[documentation policy](../_meta/documentation-policy.md). Record distilled
requirements and links, with uncertainties marked; do not introduce a competing
`soul.md` or repository transcript archive. The retrieved transcript and video
images are research scratch, not checked-in assets.

Use deliberate references and scientific content to evaluate design choices.
ClaimBranch's [interaction requirements](../product/product-spec.md#7-interaction-and-visual-character)
take precedence over a marketing-site aesthetic. A shader, animated background,
image generator, voice service, gallery application or automatic PR workflow
needs an actual task benefit; none is a dependency of the method.

The [existing workspace design](../designs/2026-09-22-episode-review.md#uiux-baseline-and-next-exploration)
owns the current audit and first comparison proposal. These conclusions are
design hypotheses until tested with that work and its researcher tasks.
