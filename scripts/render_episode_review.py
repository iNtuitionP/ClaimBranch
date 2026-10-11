"""Generate a fixed offline R1 design storyboard, never a product review UI.

python -B -m scripts.render_episode_review [--check]
Inputs and output are repository-owned. No user paths, network, authority,
research store or manuscript mutation are exposed.
"""

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import sys

from scripts.check_truth_packet import DEFAULT_PACKET, TruthPacketValidator


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "tests/fixtures/ui/episode-review.json"
TEMPLATE = ROOT / "scripts/templates/episode-review.html"
ARTIFACT = ROOT / "docs/designs/assets/episode-review.html"
ACTIONS = {
    "save_draft": "판단 초안 이어 쓰기",
    "request_ai": "이 근거로 AI 의견 요청", "not_now": "지금은 결정하지 않기",
    "authorize": "선택한 연구 변경 5개 승인", "defer": "선택한 변경 승인 · 설명은 나중에 검토",
    "refresh_review": "바뀐 내용을 읽고 다시 검토", "resume": "남은 검토 이어가기",
    "inspect_patch": "원고 변경안 확인", "close_understanding": "설명 검토 완료 승인",
    "inspect": "현재 기록과 복구 자료 확인", "retry_source": "원본 연결 다시 확인",
    "cancel_request": "AI 요청 취소", "compare_response": "이전 제안과 현재 판단 비교",
    "verify_compile": "컴파일 검증 진행", "export": "복구 자료 내보내기 검토",
    "restore": "복구 가능한 원본 확인", "send_request": "이 내용만 보내기",
    "edit_request": "보낼 내용 수정", "continue_manual": "AI 없이 판단 이어가기",
}
REVIEW = {"draft": "판단 작성 중", "reviewable": "채택 전 · 검토 중", "stale": "맥락 변경 · 다시 검토 필요",
          "pending": "미결정 · 검토 보류", "accepted": "선택한 연구 변경 반영됨"}
MANUSCRIPT = {"unchanged": "원고 변경 없음", "debt_open": "원고 반영 필요",
              "applied_unverified": "반영됨 · 컴파일 검증 전", "recovery_required": "복구 확인 필요 · 새 변경 중단"}
PROVIDER = {"off": "AI 사용 안 함", "proposal": "제안 도착 · 자동 채택 없음",
            "pending": "응답 기다리는 중", "stale": "이전 맥락의 응답", "outbound": "보내기 전 검토"}
CHANGE_NAMES = {"claim-status": "기존 주장을 재검토 필요로 표시", "interpretation": "위에 작성한 해석 선택",
                "relation:O-01": "Pruning 관찰의 반박 관계", "relation:O-02": "Quantization 관찰의 반박 관계",
                "relation:O-03": "Compression 조건에 한정된 지지 관계"}


def validate(examples):
    """Check meaningful contradictions in design examples, not a product schema."""
    if examples["classification"] != "synthetic-design" or examples["schema_version"] != 1:
        raise ValueError("unsupported design examples")
    ids = set()
    for scene in examples["scenes"]:
        name = scene["id"]
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyz_" for c in name) or name in ids:
            raise ValueError("unique safe scene IDs required")
        ids.add(name)
        draft = examples["drafts"][scene["draft"]]
        if (draft["interpretation"] is None) != (draft["rationale"] is None):
            raise ValueError("judgment and reason must be present together")
        if scene["review"] not in REVIEW or scene["provider"] not in PROVIDER or scene["manuscript"] not in MANUSCRIPT:
            raise ValueError("unknown design state")
        if scene["proposal"] not in ("none", "frozen", "edited") or scene["source"] not in ("available", "unavailable"):
            raise ValueError("unknown context state")
        if (len(set(scene["selected"])) != len(scene["selected"])
                or not set(scene["selected"]).issubset(CHANGE_NAMES)
                or not set(scene["actions"]).issubset(ACTIONS)):
            raise ValueError("unknown or duplicate selection/action")
        if scene["understanding_open"] and (scene["review"] != "accepted" or scene["proposal"] == "none"):
            raise ValueError("explanation deferral requires accepted AI-influenced work")
        if scene["manuscript"] != "unchanged" and scene["review"] != "accepted":
            raise ValueError("manuscript consequence requires a recorded decision")
        if {"authorize", "defer"}.intersection(scene["actions"]):
            if (scene["review"] != "reviewable" or scene["source"] != "available"
                    or draft["rationale"] is None or scene["change"] is not None
                    or len(scene["selected"]) != 5):
                raise ValueError("approval example requires a complete current selection")
        if scene["manuscript"] == "recovery_required" and set(scene["actions"]) != {"inspect", "export", "restore"}:
            raise ValueError("recovery must expose only inspect/export/restore")


def load_inputs():
    validator = TruthPacketValidator(DEFAULT_PACKET)
    validator.validate()
    if validator.errors:
        raise ValueError("source fixture integrity failed")
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    validate(examples)
    data = validator.verified_bytes
    source = {"packet": json.loads(data["truth-packet.json"]), "proposal": json.loads(data["frozen-proposal.json"]),
              "before": data["manuscript-before.tex"].decode("utf-8"), "after": data["manuscript-after.tex"].decode("utf-8")}
    if examples["source_packet"] != source["packet"]["packet_id"]:
        raise ValueError("design examples must name the verified source fixture")
    return examples, source


def text(value):
    return escape(str(value), quote=True)


def block(title, content, css=""):
    return f'<section class="sheet-section {css}"><h3>{text(title)}</h3>{content}</section>'


def _scene(scene, examples, source):
    draft = examples["drafts"][scene["draft"]]
    name = scene["id"]
    packet = source["packet"]
    accepted = scene["review"] == "accepted"
    heading = {
        "not_now": "지금은 결정을 보류했습니다. 작성한 이유에서 이어갈 수 있습니다.",
        "deferred": "연구 판단을 반영했습니다. 설명 검토와 원고 반영이 남아 있습니다.",
        "resume": "지난 판단으로 돌아왔습니다. 남겨 둔 설명과 원고를 검토합니다.",
        "source_unavailable": "원본 연결을 확인해야 합니다. 보존된 관찰과 판단은 읽을 수 있습니다.",
        "applied_unverified": "원고를 반영했습니다. 컴파일 검증과 최종 검토가 남아 있습니다.",
        "recovery": "원고 상태를 먼저 확인해야 합니다. 기록과 복구 자료에서 시작합니다.",
        "outbound_review": "AI에 보낼 연구 내용을 확인합니다.",
    }.get(name, "결과가 예상과 다릅니다. 주장의 어느 범위를 다시 봐야 할까요?")
    parts = [f'<article id="{name}" class="scene" aria-labelledby="title-{name}">',
             f'<aside class="annotation"><b>이 장면의 검토 기준</b><p>{text(scene["intent"])}</p><p>{text(scene["annotation"])}</p></aside>',
             '<div class="sheet"><header class="sheet-header"><p class="eyebrow">CLAIMBRANCH / 합성 연구 사례</p>',
             f'<h2 id="title-{name}" tabindex="-1">{text(scene["title"])}</h2>',
             f'<p class="lead">{text(heading)}</p>',
             f'<p class="status">{REVIEW[scene["review"]]} · {PROVIDER[scene["provider"]]}</p>',
             '<p class="context">선택 대상: 대안 해석 → 현재 논문 판단 · 원고의 중심 주장 문단</p></header>']
    if scene["manuscript"] == "recovery_required":
        parts.append('<div class="notice danger"><strong>먼저 원고 상태를 확인해야 합니다.</strong><p>예상과 다른 내용이 발견되었습니다. 새 연구 변경과 원고 쓰기를 중단하고 복구 자료를 확인합니다.</p></div>')
    if scene["change"]:
        parts.append('<div class="notice"><strong>검토한 맥락이 바뀌었습니다.</strong><dl><dt>검토 기준</dt><dd>'
                     + text(scene["change"]["reviewed"]) + '</dd><dt>현재 맥락</dt><dd>'
                     + text(scene["change"]["current"]) + '</dd></dl><p>입력한 판단과 이유는 보존합니다.</p></div>')
    evidence = '<p class="label">검토 중인 기존 주장</p><blockquote>' + text(packet["claim"]["statement"]) + '</blockquote>'
    if scene["source"] == "unavailable":
        evidence += '<p class="notice">원본에 접근할 수 없습니다. 아래 내용은 보존된 관찰 기록이며, 방금 원본을 재확인한 결과가 아닙니다.</p>'
    else:
        evidence += '<p class="subtle">합성 예시: 세 관찰의 확인이 끝난 뒤 해석을 시작하는 장면입니다.</p>'
    evidence += '<ol class="evidence">'
    for observation in packet["observations"]:
        relation = "압축 조건에서 예상과 일치" if observation["operator"] == "compression" else "예상과 불일치 · 기존 주장에 반박"
        evidence += f'<li><b>{text(observation["operator"].capitalize())}</b><span>{relation}</span><p>{text(observation["rationale"])}</p></li>'
    evidence += '</ol><p class="question">Compression에서의 일치가 다른 두 관찰의 불일치를 지우지는 않습니다.</p>'
    parts.append(block("1. 무엇이 관찰되었나요?", evidence))
    if scene["provider"] == "pending":
        parts.append(block("2. AI 의견", '<p class="notice">응답을 기다리고 있습니다. 아래 판단은 계속 작성할 수 있습니다. 취소 후 늦게 온 응답도 자동 반영되지 않습니다.</p>'))
    elif scene["provider"] == "outbound":
        payload = {"destination": "https://provider.example.invalid",
                   "claim": packet["claim"]["statement"], "observations": packet["observations"],
                   "question": "어떤 주장의 범위가 도전받으며, 관찰과 아직 검증하지 않은 해석을 어떻게 구분할까요?"}
        normalized = json.dumps(payload, ensure_ascii=False, indent=2)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        parts.append(block("2. AI에 보낼 내용", '<p>선택한 관찰·기존 주장·질문만 포함합니다. 원본 파일, 비밀정보, 전체 원고는 제외했습니다.</p>'
                           '<p>목적지는 설명용 주소이며 실제 연결은 없습니다. 제공자의 보관 정책은 확인되지 않은 상태를 보여 주는 예시입니다. 내용을 수정하거나 전송을 취소하고 수동으로 이어갈 수 있습니다.</p><pre class="source">'
                           + text(normalized) + '</pre><details><summary>이 요청을 구별하는 식별자</summary><p class="subtle">위에 표시한 UTF-8 내용 전체에 대한 SHA-256입니다. 내용이나 목적지가 달라지면 식별자도 달라집니다.</p><pre class="source">'
                           + digest + '</pre></details>'))
    elif scene["proposal"] != "none":
        suffix = " · 이전 맥락의 응답" if scene["provider"] == "stale" else ""
        ai = '<p class="proposal-label">AI 원문 · Not accepted' + suffix + '</p><blockquote>' + text(source["proposal"]["normalized_text"]) + '</blockquote>'
        ai += '<p>이 설명은 검토할 후보입니다. 관찰로 확인된 범위와 추가 검증이 필요한 부분을 구분해 주세요.</p>'
        if scene["proposal"] == "edited":
            ai += '<p class="label">내가 고친 해석</p><p class="human-edit">' + text(draft["interpretation"]) + '</p><p class="subtle">AI 제안 → 사람의 수정. 원문과 수정 이유를 함께 보존합니다.</p>'
        parts.append(block("2. AI 제안을 어떻게 볼까요?", ai))
    else:
        parts.append(block("2. AI 의견", '<p class="subtle">AI 의견을 요청하지 않았습니다. 지금 가진 근거로 판단을 이어갈 수 있습니다.</p>'))
    judgment = '<p class="subtle">관찰에 대한 나의 해석입니다. 확정된 사실과 구분하고, 미해결 부분을 남길 수 있습니다.</p>'
    for field, label, placeholder in (("interpretation", "나의 해석", "아직 해석을 정하지 않았습니다."),
                                       ("rationale", "그렇게 판단한 이유", "판단을 만들면서 이유를 한 번 작성합니다.")):
        judgment += f'<label for="{field}-{name}">{label}</label><textarea id="{field}-{name}" readonly rows="{5 if field == "rationale" else 3}" placeholder="{placeholder}">{text(draft[field] or "")}</textarea>'
    if scene["proposal"] != "none" and scene["review"] in ("reviewable", "accepted"):
        judgment += '<details class="explanation"' + (' open' if scene["understanding_open"] else '') + '><summary>이 판단에서 더 검토할 설명</summary><p>기존 이유로 충분하면 다시 쓰지 않습니다. 추가 설명이 필요한 항목만 다룹니다.</p><ul><li>어느 관찰이 기존 주장의 어떤 범위를 흔드나요?</li><li>선택한 해석에서 아직 확인되지 않은 부분은 무엇인가요?</li></ul><p>설명 검토를 미루고 변경을 승인하면, 남은 검토 항목이 따로 표시됩니다. 이해 점수나 AI 채점은 없습니다.</p></details>'
    parts.append(block("3. 내 판단", judgment))
    changes = '<p class="label">' + ('반영한 연구 변경' if accepted else '선택한 연구 변경') + '</p><ul class="selections">'
    for key, label in CHANGE_NAMES.items():
        picked = key in scene["selected"]
        changes += '<li><span>' + ('☑ 선택' if picked else '☐ 미선택') + '</span> ' + text(label) + '</li>'
    changes += '</ul><p class="subtle">관찰 기록은 모든 해석에서 유지됩니다. 선택한 해석은 연결된 세 관찰을 참조합니다. 새 강한 주장과 원고 문장 자동 변경은 이번 연구 변경에 포함되지 않습니다.</p>'
    if not scene["selected"]:
        changes += '<p class="notice">아직 반영할 변경을 선택하지 않았습니다. 해석을 작성한 뒤 범위를 검토합니다.</p>'
    parts.append(block("4. 어떤 부분을 바꾸나요?", changes))
    manuscript = '<p class="status">' + MANUSCRIPT[scene["manuscript"]] + '</p>'
    if scene["selected"]:
        manuscript += '<p>연구 판단과 원고 반영은 별도 단계입니다. 아래는 정확한 문장 변경을 검토하기 위한 고정 예시이며, 이 화면에서 원고에 적용되지 않습니다.</p><div class="diff"><div><p class="label">변경 전</p><pre class="source">'
        manuscript += text(source["before"]) + '</pre></div><div><p class="label">검토할 변경안</p><pre class="source">' + text(source["after"]) + '</pre></div></div>'
    else:
        manuscript += '<p>현재 대상은 원고의 중심 주장 문단입니다. 판단과 변경 범위를 정한 뒤 정확한 문장 차이를 검토합니다.</p>'
    parts.append(block("5. 원고에는 무엇이 남나요?", manuscript))
    decision = ''
    if scene["receipt"]:
        decision += '<p class="receipt">' + text(scene["receipt"]) + '</p>'
    if scene["understanding_open"]:
        decision += '<ul class="pending"><li><b>설명 검토 예정</b> — 당시 판단의 근거와 미확인 부분을 이어서 검토</li><li><b>원고 반영 필요</b> — 문장 변경과 컴파일 검증은 별도로 진행</li></ul>'
    decision += '<div class="actions">' + ''.join(f'<button class="product-action" type="button" disabled>{text(ACTIONS[action])}</button>' for action in scene["actions"]) + '</div><p class="prototype-note">설계 시안의 동작 예시입니다. 버튼은 실행되지 않으며 입력·승인·저장·전송은 발생하지 않습니다.</p>'
    parts.append(block("6. 다음 행동", decision))
    parts.append('<details class="audit"><summary>판단과 기여 이력 보기</summary><p>근거 기록 → '
                 + ('AI 고정 제안 → 사람의 검토·수정 → ' if scene["proposal"] != "none" else '')
                 + '현재 해석과 이유 → 선택한 연구 변경 → 원고 검토. 이 시안에는 실제 승인 기록이 없습니다.</p></details></div></article>')
    return '\n'.join(parts)


def render(examples, source):
    validate(examples)
    navigation = ''.join(f'<a href="#{scene["id"]}">{text(scene["title"])}</a>' for scene in examples["scenes"])
    scenes = '\n'.join(_scene(scene, examples, source) for scene in examples["scenes"])
    return TEMPLATE.read_text(encoding="utf-8").replace("{{NAVIGATION}}", navigation).replace("{{SCENES}}", scenes)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the generated artifact without writing")
    args = parser.parse_args(argv)
    try:
        output = render(*load_inputs())
        if args.check:
            if not ARTIFACT.is_file() or ARTIFACT.read_text(encoding="utf-8") != output:
                raise ValueError("storyboard is outdated; run python -B -m scripts.render_episode_review")
            print("R1 storyboard matches its verified fixture and design examples.")
        else:
            ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
            ARTIFACT.write_text(output, encoding="utf-8")
            print("Generated docs/designs/assets/episode-review.html (offline design only).")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"R1 storyboard error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
