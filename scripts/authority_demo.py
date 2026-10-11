"""Fixed synthetic A1–A4 integration on disposable copies; no OS authorization.

Run: python -B -m scripts.authority_demo [--format json]
No user project/path, provider endpoint, compiler or network is used. The
simulated approval callback is explicitly forgeable and never proves presence.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from scripts.check_truth_packet import DEFAULT_PACKET, TruthPacketValidator
from scripts.contracts.first_pass import (
    EvidenceLedger, EvidenceRevision, ManuscriptTarget, append_evidence,
    prepare_review, record_judgment, start_draft,
)
from scripts.graph_demo import compare, preview
from scripts.probes.authority_flow import Operation, SyntheticAuthorityFlow
from scripts.probes.frozen_provider import PendingProposal
from scripts.probes.workspace_storage import ProbeError
from scripts.verify import build_environment


def _history(root, mode, packet, fixtures):
    project_id = "synthetic-" + mode
    paper = root / project_id
    paper.mkdir()
    (paper / ".git").mkdir()  # Demonstrate the separate external probe workspace.
    manuscript = paper / "manuscript.tex"
    before, after = fixtures["manuscript-before.tex"], fixtures["manuscript-after.tex"]
    manuscript.write_bytes(before)
    flow = SyntheticAuthorityFlow.for_project(root, root / "workspaces", paper, project_id)
    flow.initialize(project_id)
    flow.start_session(project_id)

    evidence = EvidenceLedger(project_id)
    for observation in packet["observations"]:
        evidence = append_evidence(evidence, EvidenceRevision(
            "synthetic-" + observation["id"], observation["id"],
            json.dumps(observation, sort_keys=True, ensure_ascii=False)))
    draft = start_draft(project_id, "synthetic-episode",
        json.dumps(packet["observations"], sort_keys=True, ensure_ascii=False),
        packet["claim"]["statement"])
    proposal = None
    if mode == "frozen":
        frozen = json.loads(fixtures["frozen-proposal.json"])
        pending = PendingProposal("fixed-offline-request", draft)
        proposal = pending.deliver("fixed-offline-request",
            {"operation": "propose", "text": frozen["normalized_text"]}, current=draft)

    # Fixture's unaided judgment is an explicit synthetic human step, never an
    # automatic promotion of proposal text. Preserve its rationale once.
    rationale = "\n".join(item["rationale"] for item in packet["observations"])
    draft = record_judgment(draft, packet["unaided_human_interpretation"]["statement"], rationale)

    def load_review():
        return prepare_review(draft, evidence=evidence, manuscript_target=ManuscriptTarget(
            packet["manuscript"]["anchor_id"], hashlib.sha256(manuscript.read_bytes()).hexdigest()))

    selected = tuple(change["id"] for change in compare(packet))
    operation = Operation("synthetic-judgment", 0, load_review(), before, after, selected, proposal)
    attempt_id = flow.begin(operation, load_review=load_review,
        verify_response=lambda request, response: response == request.challenge,
        clock=lambda: 1, expires_at=10, nonce=b"S" * 32)
    outcome = flow.respond(attempt_id, flow.request(attempt_id).challenge)
    if outcome.status != "matched" or outcome.authorization_verified:
        raise ProbeError("synthetic attempt did not match its bounded contract")
    recorded = flow.commit(operation, attempt_id)

    reopened = SyntheticAuthorityFlow.for_project(root, root / "workspaces", paper, project_id)
    reopened.start_session(project_id)
    retry_same = reopened.commit(operation, attempt_id) == recorded
    reopened.apply(operation.key)
    applied = manuscript.read_bytes() == after
    reopened.restore(operation.key)
    restored = manuscript.read_bytes() == before
    if not (retry_same and applied and restored):
        raise ProbeError("synthetic reopen/apply/restore verification failed")
    records = reopened.records()
    return {"mode": mode, "record_count": len(records), "record": records[0],
            "rationale": rationale, "retry_same_record": retry_same,
            "manuscript_applied": applied, "manuscript_restored": restored,
            "graph_after": preview(packet, records[0]["payload"]["selected"])["result"]}


def run_demo():
    validator = TruthPacketValidator(DEFAULT_PACKET)
    validator.validate()
    if validator.errors:
        raise ProbeError("fixture verification failed; run scripts/check_truth_packet.py")
    fixtures = validator.verified_bytes
    packet = json.loads(fixtures["truth-packet.json"])
    # Fail before creating anything if the caller's temporary root is in Git.
    temporary_root = build_environment(needs_probe=True)["TMPDIR"]
    with tempfile.TemporaryDirectory(prefix="claimbranch-storage-probe-", dir=temporary_root) as scratch:
        root = Path(scratch).resolve()
        (root / "workspaces").mkdir()
        histories = [_history(root, mode, packet, fixtures) for mode in ("manual", "frozen")]
    return {"synthetic": True, "authorization_verified": False, "compile_verified": False,
            "debt_closed": False, "provider_calls": 0, "histories": histories}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        result = run_demo()
    except (OSError, ValueError, RuntimeError):
        print("합성 통합 실행 실패. 원본 예제와 임시 디렉터리 설정을 확인하세요.", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("A1–A4 합성 통합 실행 — OS 승인·격리 미검증 / 네트워크 사용 없음")
        for history in result["histories"]:
            label = "AI 끔" if history["mode"] == "manual" else "고정 AI 제안 (Not accepted)"
            print(f"{label}: 검토 → 모의 승인 → 기록 1개 → 재열기·재시도 → 원고 반영·복구 확인")
        print("합성 주장 상태: contested / 근거 관계 3개 / 입력 근거 보존")
        print("원본 파일 변경 없음. 임시 데이터 정리 완료. 컴파일·debt 종료 미검증.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
