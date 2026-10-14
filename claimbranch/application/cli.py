"""Personal terminal alpha and separate synthetic/protected development paths."""
import argparse
import json
import os
import sys
import webbrowser

from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example as replay_fixture
from claimbranch.runtime import prerequisite_report, print_guidance


def replay_paper(variant):
    return replay_fixture(variant, paper=True)


def doctor(directory=None):
    # No native prompt, dependency installation or endpoint; project reads are explicit.
    replay_fixture("manual")
    replay_fixture("recorded")
    replay_paper("manual")
    replay_paper("recorded")
    runtime = prerequisite_report()
    missing = runtime['missing_prerequisites']
    result = {"status": "personal-alpha-unavailable" if missing else "personal-alpha-ready",
            "personal_workspace":"unavailable" if missing else "ready",
            **runtime, "host":sys.platform,
            "storage":{"encrypted":False,"placement":"owner-private directory outside Git",
                "authority":"personal history; no signed protected approval"},
            "synthetic_replay": "ready", "paper_replay": "ready",
            "protected_acceptance": "unavailable", "live_provider": "unavailable",
            "manuscript_write_and_compile": "unavailable", "protected_research": "unavailable",
            "authorization_verified": False,
            "reason": "Resolve declared prerequisites: "+', '.join(missing) if missing else
                      "Personal terminal work/save/recovery available; native custody, live AI and manuscript automation are deferred.",
            }
    from claimbranch.core.paper_capacity import LIMITS, HISTORY_BYTES, MANIFEST_BYTES, PROJECT_BYTES
    from claimbranch.core.research_schema import PAPER_SERIES_LIMITS
    result['capacity_profiles'] = {'episode': dict(PAPER_SERIES_LIMITS),
        'paper': {**LIMITS,'history_bytes':HISTORY_BYTES,'manifest_bytes':MANIFEST_BYTES,'project_bytes':PROJECT_BYTES}}
    if directory is not None:
        from .personal_project import PersonalProjectStore
        from .project_commands import saved_summary
        with PersonalProjectStore(directory) as store:
            result['capacity'] = saved_summary(store.load(),'capacity')['capacity']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="ClaimBranch personal terminal alpha — local files, AI off; protected features unavailable")
    parser.add_argument("--version", action="version", version="ClaimBranch personal terminal alpha (unreleased)")
    commands = parser.add_subparsers(dest="command", required=True)
    from .project_commands import add_personal_project_commands
    add_personal_project_commands(commands)
    from .provider_commands import add_provider_commands
    add_provider_commands(commands)
    from .mac_runtime import add_runtime_commands
    add_runtime_commands(commands)
    check = commands.add_parser("doctor", help="Read-only readiness; no native prompts or network",
        description="Check Python 3.13, importable Unix curses, Git on PATH and /usr/bin/git. "
                    "Missing prerequisites include manual setup guidance; nothing is installed.")
    check.add_argument("--directory", help="Explicit saved private personal project for used/limit/remaining; close its TUI first")
    check.add_argument("--json", action="store_true")
    demo = commands.add_parser("demo", help="Explore the committed synthetic example")
    demos = demo.add_subparsers(dest="demo", required=True)
    from .work_commands import add_work_commands
    add_work_commands(demos)
    from .tui_project import add_project_commands
    add_project_commands(demos)
    from .paper_assistance_example import add_command
    add_command(demos)
    saturation = demos.add_parser("saturation", help="Verify and replay both frozen candidate histories")
    saturation.add_argument("--json", action="store_true")
    saturation.add_argument("--audit", choices=("manual", "recorded"), help="Emit one unverified candidate manifest as JSON")
    paper = demos.add_parser("paper", help="Query the synthetic paper argument or a hypothetical experiment outcome")
    paper.add_argument("--variant", choices=("manual", "recorded"), default="manual")
    paper.add_argument("--json", action="store_true")
    paper_action = paper.add_mutually_exclusive_group()
    paper_action.add_argument("--scenario", choices=("supports", "challenges", "inconclusive"))
    paper_action.add_argument("--context", action="store_true", help="Inspect selected scientific context; no dispatch")
    paper_action.add_argument("--workflow", action="store_true", help="Run a scripted manual/offline-AI draft journey")
    paper_action.add_argument("--episodes", action="store_true", help="Replay two cumulative synthetic paper episodes")
    paper_action.add_argument("--pending", action="store_true", help="Inspect conditional explanation/manuscript work in the synthetic series")
    paper_action.add_argument("--provider", action="store_true", help="Exercise five independent frozen AI response paths; no endpoint or UI")
    tui = demos.add_parser("tui", help="Explore the synthetic paper in your terminal; no browser or listener")
    tui.add_argument("--layout", choices=("two", "three"), default="two")
    tui.add_argument("--navigation", choices=("graph", "outline"), default="graph")
    tui.add_argument("--variant", choices=("manual", "recorded"), default="manual")
    tui.add_argument("--ai-off", action="store_true", help="Disable fixed AI assistance; keep manual drafting and recorded source history")
    tui_example = tui.add_mutually_exclusive_group()
    tui_example.add_argument("--merge-example", action="store_true", help="Open the synthetic active episode just before its selected merge")
    tui_example.add_argument("--series", action="store_true", help="Explore cumulative synthetic episodes and conditional pending work")
    tui.add_argument("--snapshot", action="store_true", help="Print one plain-text frame without a TTY")
    tui.add_argument("--work-dir", help="Encrypted judgment/AI-origin, notes, links, argument/result drafts, partial explanations and unfinished review input in an existing private directory (macOS, cumulative examples)")
    tui.add_argument("--create-work", action="store_true", help="Explicitly create --work-dir checkpoint; prompts for a separately retained recovery key")
    tui.add_argument("--draft-file", help="Recover private UI drafts in this external file; must be outside Git")
    review = demos.add_parser("review", help="Open one volatile, loopback-only synthetic Episode Review")
    review.add_argument("--no-open", action="store_true", help="Print the local URL without opening a browser")
    review.add_argument("--example", action="store_true", help="Open the recorded synthetic judgment and experiment graph")
    args = parser.parse_args(argv)
    if args.command == 'provider':
        from .provider_commands import run_provider_command
        return run_provider_command(args)
    if args.command == 'project':
        from .project_commands import run_personal_project_command
        return run_personal_project_command(args)
    if args.command == 'demo' and args.demo == 'project':
        from .tui_project import run_project_command
        return run_project_command(args)
    if args.command == 'runtime':
        from .mac_runtime import run_runtime_command
        return run_runtime_command(args)
    if args.command == 'demo' and args.demo == 'work':
        from .work_commands import run_work_command
        return run_work_command(args)
    try:
        if args.command == 'demo' and args.demo == 'proposals':
            from .paper_assistance_example import run
            return run(args)
        if args.command == "doctor":
            result = doctor(args.directory)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                print('개인 프로젝트: '+ ('사용 가능' if result['personal_workspace']=='ready' else '준비 필요'))
                print('저장·재개·백업·복원: 개인 로컬 파일, 암호화 없음. AI는 꺼져 있습니다.')
                print('보호된 승인 / 원고 적용·컴파일 / 실시간 AI: 후속 기능')
                if result['missing_prerequisites']: print('필요한 환경: '+', '.join(result['missing_prerequisites']))
                print_guidance(result)
                if "capacity" in result:
                    print("Capacity: " + json.dumps(result["capacity"],ensure_ascii=False,sort_keys=True))
                print("다음 동작: " + result["next_action"])
            return 0 if result['personal_workspace']=='ready' else 3
        if args.demo == "paper":
            from .paper_service import PaperService
            from .paper_example import context_request, scenario_request, workflow
            service = PaperService(replay_paper(args.variant))
            result = service.query("main")
            if args.scenario:
                result = service.scenario(scenario_request(service, args.scenario))
            elif args.context:
                from claimbranch.core.canonical import decode
                result = decode(service.compile_context(context_request(service)).payload)
            elif args.workflow:
                result = workflow(args.variant)
            elif args.episodes:
                from .paper_episode_example import workflow as episode_workflow
                result = episode_workflow(args.variant)
            elif args.pending:
                result = PaperService(replay_fixture(args.variant, series=True)).pending_work()
            elif args.provider:
                from .paper_provider_example import workflow as provider_workflow
                result = provider_workflow(args.variant)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif args.scenario:
                print("합성 가정의 검토 대상 주장: " + ", ".join(result["potentially_affected_claim_ids"]))
                print("영향 경로 밖의 주장: " + ", ".join(result["unaffected_claim_ids"]))
                print("실제 관찰과 주장 상태는 바뀌지 않았습니다. 과학적 판단과 승인이 필요합니다.")
            elif args.context:
                print("선택한 주장·관찰·실험과 연결의 AI 요청 문맥입니다. 전송하지 않았습니다.")
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            elif args.provider:
                print("합성 논문의 고정 응답으로 다섯 개의 독립 예제를 실행했습니다.")
                print("연구 질문: Model A의 20% 가지치기에서 마스크 42의 정확도 손실 0.4 퍼센트포인트가 마스크 43에도 성립하나요?")
                labels = {"adopted": "제안 채택 후 수정", "cancelled": "요청 취소", "edited": "초안 수정 후 응답 도착",
                          "expired": "시간 초과", "refused": "응답 거절"}
                for case in result["cases"]:
                    action = "AI 원문과 사람 수정 보존" if case["name"] == "adopted" else "응답 채택 없이 수동 판단 유지"
                    print(labels[case["name"]] + ": " + action)
                print("논문 이력은 그대로이며, 실제 모델 호출·과학적 승인·저장은 없습니다. --json으로 문맥과 기록을 확인하세요.")
            elif args.episodes:
                print("합성 반복 연구: 첫 판단 → 같은 관찰의 정정 → 두 번째 판단")
                print("Model A의 20% 가중치 가지치기(마스크 42): 같은 2,000개 예제의 정확도 손실이 0.4 → 1.2 퍼센트포인트로 정정됩니다.")
                print("최초 값과 두 해석·기여 이력이 보존됩니다.")
                print("이전 에피소드 초안은 유지되고, 다음 에피소드 초안은 별도로 시작합니다.")
                print("두 번째 병합의 선택·그래프 전후·기여 이력을 검토하고, 검토한 변경과 계산된 후보가 일치하는지 확인합니다.")
                print("남은 설명·원고 작업을 다시 구성하고, 합성 원고의 변경 후보를 검토합니다. 원고 파일과 완료 상태는 바뀌지 않습니다.")
                print("--json으로 에피소드 목록·현재 논문·과거 시점을 확인하세요. 실제 승인·영구 저장은 없습니다.")
            elif args.pending:
                print("합성 후보가 승인될 경우 남는 설명·원고 검토 항목입니다.")
                for item in result["items"]:
                    label = "원고 영향 검토" if item["kind"] == "manuscript" else "판단 설명 검토"
                    print(f"{item['episode_id']} · {label}: {item['judgment']['text']}")
                print("에피소드를 닫아도 이 작업은 완료되지 않습니다. 실제 승인된 부채나 파일 변경은 없습니다.")
            elif args.workflow:
                route = "고정 AI 예제 검토·채택 → 사람 수정" if args.variant == "recorded" else "AI 없이 수동 초안 작성"
                print("합성 절차 예시: 논문 문맥 선택 → " + route + " → 선택한 과학적 변경 검토 → Not now")
                selection = result["changes_preview"]["preview"]["selection"]
                print("선택: " + ", ".join(selection["selected"]) + " / 필수 변경: " + ", ".join(selection["required"]))
                print("제외하여 유지되는 실험 계획: " + ", ".join(selection["omitted"]))
                print("AI 기여 보존: " + ("있음" if result["state"]["draft"]["ai_influenced"] else "없음"))
                print("원본 논문 이력은 유지되며, 실제 승인·저장·모델 호출은 없습니다.")
                print("--json으로 그래프 전후 차이·영향 경로·기여 이력·검토 결과를 확인하세요.")
            else:
                print(result["title"])
                print(f"합성 논문: 노드 {len(result['nodes'])}개 · 연결 {len(result['relations'])}개")
                print("핵심 논지, 주요·하위 주장, 공유 근거와 후속 실험을 조회했습니다.")
                print("--json으로 전체 내용을, --scenario challenges로 가정한 결과의 영향을 확인하세요.")
            return 0
        if args.demo == "tui":
            from .tui import run_terminal
            from claimbranch.fixtures import replay_merge_example
            history = (replay_merge_example(args.variant) if args.merge_example else
                       replay_fixture(args.variant, series=True) if args.series else replay_paper(args.variant))
            return run_terminal(history, layout=args.layout,
                                navigation=args.navigation, snapshot=args.snapshot, draft_file=args.draft_file,
                                ai_off=args.ai_off, work_dir=args.work_dir, create_work=args.create_work)
        if args.demo == "saturation":
            if args.audit:
                print(replay_fixture(args.audit).manifest().decode("utf-8"))
                return 0
            results = []
            for variant in ("manual", "recorded"):
                history = replay_fixture(variant)
                view = history.view("main")
                results.append({"variant": variant, "golden_match": True, "authority": "unverified-candidate",
                                "claim_status": view["claim"]["status"], "observations": len(view["evidence"]),
                                "interpretation": view["judgment"]["text"],
                                "ai_influenced": any(c["contributor"] == "ai" for c in view["judgment"]["history"]),
                                "authorization_verified": False})
            if args.json:
                print(json.dumps(results, ensure_ascii=False, sort_keys=True))
            else:
                print("수동 판단과 기록된 AI 제안 경로가 각각 고정된 예제 기록과 일치합니다.")
                print("관찰 3개 → 해석과 근거 연결 → 주장 재검토 → 원고 영향 후보")
                print("실제 승인, 저장, 원고 변경은 실행하지 않았습니다.")
                print("화면에서 이어보기: python3.13 -m claimbranch demo review")
            return 0
        from .server import ReviewServer
        with ReviewServer(example=args.example) as server:
            print("합성 자료만 사용하세요. 초안은 이 실행 중에만 유지됩니다.", flush=True)
            print("15분 세션 · Ctrl+C로 종료 · 주소의 초기 연결 정보는 한 번만 사용됩니다.", flush=True)
            url = server.launch_url
            print(url, flush=True)
            if not args.no_open:
                try:
                    webbrowser.open(url)
                except webbrowser.Error:
                    print("브라우저를 열지 못했습니다. 위 주소를 직접 열어 주세요.", file=sys.stderr)
            server.serve_forever(poll_interval=0.2)
        return 0
    except KeyboardInterrupt:
        print("체험을 종료했습니다. 실제 연구 기록은 변경하지 않았습니다.", file=sys.stderr)
        return 130
    except (ContractError, OSError) as error:
        value = {"status": "unavailable", "reason": str(error), "authorization_verified": False,
                 "next_action": "re-extract the verified personal alpha source, then run python3.13 -m claimbranch doctor"}
        print(json.dumps(value, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
