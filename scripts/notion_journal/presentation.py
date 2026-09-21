"""Exact human-facing rendering for confirmed journal judgments."""

from __future__ import annotations

from .model import JudgmentDraft, validate_journal_language


_LABELS = {
    "ko": {
        "title": "제목",
        "background": "배경",
        "why_now": "왜 지금",
        "understanding_shift": "무엇이 달라졌나",
        "human_judgment": "무엇을 판단했나",
        "tradeoff_boundary": "무엇을 감수하거나 제외했나",
        "revisit_signal": "무엇이 이 판단을 바꿀까",
        "evidence": "근거",
        "ai_contribution": "AI 기여",
        "supersedes": "대체하는 이전 기록",
        "none": "없음",
    },
    "en": {
        "title": "Title",
        "background": "Background",
        "why_now": "Why now",
        "understanding_shift": "What changed",
        "human_judgment": "Human judgment",
        "tradeoff_boundary": "Tradeoff or boundary",
        "revisit_signal": "Revisit signal",
        "evidence": "Evidence",
        "ai_contribution": "AI contribution",
        "supersedes": "Supersedes",
        "none": "None",
    },
}


def render_judgment_preview(draft: JudgmentDraft, journal_language: str) -> str:
    """Render the exact semantic confirmation preview."""

    language = validate_journal_language(journal_language)
    labels = _LABELS[language]
    lines = [f"{labels['title']}: {draft.title}"]
    if draft.background is not None:
        lines.append(f"{labels['background']}: {draft.background}")
    lines.extend(
        [
            f"{labels['why_now']}: {draft.why_now}",
            f"{labels['understanding_shift']}: {draft.understanding_shift}",
            f"{labels['human_judgment']}: {draft.human_judgment}",
            f"{labels['tradeoff_boundary']}: {draft.tradeoff_boundary}",
            f"{labels['revisit_signal']}: {draft.revisit_signal}",
        ]
    )
    if draft.evidence_pointers:
        lines.append(f"{labels['evidence']}:")
        lines.extend(f"- `{pointer}`" for pointer in draft.evidence_pointers)
    else:
        lines.append(f"{labels['evidence']}: {labels['none']}")
    lines.extend(
        (
            f"{labels['ai_contribution']}: {draft.ai_contribution}",
            f"{labels['supersedes']}: {draft.supersedes or labels['none']}",
        )
    )
    return "\n".join(lines)


def render_judgment_body(
    draft: JudgmentDraft, journal_language: str | None
) -> str:
    """Render a new localized body or the exact language-less legacy body."""

    language = validate_journal_language(journal_language, allow_legacy=True)
    labels = _LABELS[language or "ko"]
    evidence = "\n".join(f"- `{pointer}`" for pointer in draft.evidence_pointers)
    evidence = evidence or f"- {labels['none']}"
    sections = []
    if draft.background is not None:
        sections.append((labels["background"], draft.background))
    sections.extend(
        [
            (labels["why_now"], draft.why_now),
            (labels["understanding_shift"], draft.understanding_shift),
            (labels["human_judgment"], draft.human_judgment),
            (labels["tradeoff_boundary"], draft.tradeoff_boundary),
            (labels["revisit_signal"], draft.revisit_signal),
            (labels["evidence"], evidence),
        ]
    )
    body = "\n\n".join(f"## {heading}\n\n{value}" for heading, value in sections)
    if draft.supersedes is not None:
        supersedes_heading = (
            "대체하는 기록" if journal_language is None else labels["supersedes"]
        )
        body += f"\n\n## {supersedes_heading}\n\n`{draft.supersedes}`"
    return body


__all__ = ["render_judgment_body", "render_judgment_preview"]
