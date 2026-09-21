"""Read-only, fixture-backed research graph walkthrough; not the product CLI.

Run from the checkout: python -B -m scripts.graph_demo --help
No accepted store, real refs, model, approval, manuscript write, or journal.
The dictionaries below are disposable display projections, not a new schema.
"""

import argparse
from copy import deepcopy
import json
import sys

from scripts.check_truth_packet import DEFAULT_PACKET, TruthPacketValidator


RELATIONS = {'challenges': '반박', 'qualifies': '조건부 지지 / 범위 제한'}
STATUSES = {'supported': '지지됨(예제의 초기 상태)', 'contested': '재검토 필요'}


def load_packet():
    """Consume the existing checker's verified bytes, never a second file read."""
    validator = TruthPacketValidator(DEFAULT_PACKET)
    validator.validate()
    if validator.errors:
        raise ValueError('예제 무결성 검사 실패. python scripts/check_truth_packet.py 로 확인하세요.')
    return json.loads(validator.verified_bytes['truth-packet.json'].decode('utf-8'))


def project(packet, view):
    """Project two hypothetical views of the fixed case; no canonical refs."""
    if view not in ('main', 'candidate'):
        raise ValueError('view must be main or candidate')
    claim = packet['claim']
    candidate = view == 'candidate'
    return deepcopy({
        'view': view,
        'claim': {'id': claim['id'], 'statement': claim['statement'],
                  'scope': claim['scope'],
                  'status': (packet['expected_impact']['claim_status_after']
                             if candidate else claim['initial_status'])},
        'observations': [
            {key: observation[key] for key in ('id', 'run_id', 'operator', 'expected')}
            for observation in packet['observations']
        ],
        'interpretation': packet['unaided_human_interpretation'] if candidate else None,
        'relationships': [
            {'source': observation['id'], 'target': claim['id'],
             'type': observation['relationship_to_claim'],
             'condition': observation['operator'], 'rationale': observation['rationale']}
            for observation in packet['observations']
        ] if candidate else [],
        'anchor': {'id': packet['manuscript']['anchor_id'],
                   'claim_id': packet['manuscript']['claim_id'],
                   'marker': packet['manuscript']['marker_id']},
    })


def compare(packet):
    """Compute changes between fixture projections; not a generic merge engine."""
    base, candidate = project(packet, 'main'), project(packet, 'candidate')
    changes = []
    if base['claim']['status'] != candidate['claim']['status']:
        changes.append({'id': 'claim-status', 'target': base['claim']['id'],
                        'before': base['claim']['status'], 'after': candidate['claim']['status'],
                        'requires': [base['claim']['id']]})
    if base['interpretation'] != candidate['interpretation']:
        interpretation = candidate['interpretation']
        changes.append({'id': 'interpretation', 'target': interpretation['id'],
                        'before': base['interpretation'], 'after': interpretation,
                        'requires': interpretation['observation_ids'][:]})
    for relation in candidate['relationships']:
        changes.append({'id': 'relation:' + relation['source'], 'target': relation['source'],
                        'before': None, 'after': relation,
                        'requires': [relation['source'], relation['target']]})
    return changes


def _impact_paths(view, starts):
    """Follow only displayed interpretation/evidence/claim/anchor links.

    Interpretation -> Observation -> Claim -> manuscript anchor
    No links from model proposals or an assumed scientific inference.
    """
    adjacency = {}
    for edge in view['relationships']:
        adjacency.setdefault(edge['source'], []).append(edge['target'])
    interpretation = view['interpretation']
    if interpretation:
        adjacency[interpretation['id']] = interpretation['observation_ids'][:]
    anchor = view['anchor']
    adjacency.setdefault(anchor['claim_id'], []).append(anchor['id'])
    paths = []

    def visit(path):
        if path[-1] == anchor['id']:
            paths.append(path)
            return
        for target in sorted(set(adjacency.get(path[-1], []))):
            if target not in path:
                visit([*path, target])

    for start in sorted(set(starts)):
        visit([start])
    return paths


def preview(packet, selected):
    """Return hypothetical partial adoption and dependencies; never apply it."""
    selected = list(selected)
    changes = compare(packet)
    known = {change['id'] for change in changes}
    if any(not isinstance(key, str) or key not in known for key in selected):
        raise ValueError('알 수 없는 변경 ID입니다. diff 명령에서 선택 가능한 ID를 확인하세요.')
    if len(set(selected)) != len(selected):
        raise ValueError('같은 변경 ID를 중복 선택할 수 없습니다.')
    chosen = [change for change in changes if change['id'] in selected]
    result = project(packet, 'main')
    existing = {result['claim']['id'], *(o['id'] for o in result['observations'])}
    required = sorted({key for change in chosen for key in change['requires']})
    if not set(required).issubset(existing):
        raise ValueError('필수 근거 또는 대상이 예제에 없습니다. 반영 미리보기를 중단합니다.')
    for change in chosen:
        if change['id'] == 'claim-status':
            result['claim']['status'] = change['after']
        elif change['id'] == 'interpretation':
            result['interpretation'] = deepcopy(change['after'])
        else:
            result['relationships'].append(deepcopy(change['after']))
    return {'selected': [change['id'] for change in chosen],
            'omitted': [change['id'] for change in changes if change['id'] not in selected],
            'required_existing': required,
            'impact_paths': _impact_paths(result, [change['target'] for change in chosen]),
            'result': result}


def _show(view):
    claim = view['claim']
    print(f"주장 {claim['id']} | {STATUSES.get(claim['status'], claim['status'])}")
    print('  원문: ' + claim['statement'])
    print('  적용 범위: ' + ', '.join(claim['scope']))
    print('근거 — 두 보기에서 동일한 관찰을 참조합니다:')
    for observation in view['observations']:
        outcome = '예상과 일치' if observation['expected'] else '예상과 불일치'
        print(f"  {observation['id']} [{observation['operator']}] {outcome}")
    print('주장과의 연결:')
    if not view['relationships']:
        print('  초기 보기에는 새 관계 해석을 아직 포함하지 않았습니다.')
    for edge in view['relationships']:
        print(f"  {edge['source']} -- {RELATIONS[edge['type']]} [{edge['condition']}] --> {edge['target']}")
        print('    이유(원문): ' + edge['rationale'])
    interpretation = view['interpretation']
    if interpretation:
        print(f"대안 해석 {interpretation['id']} (예제에 기록된 해석; 현재 사용자의 채택 아님):")
        print('  원문: ' + interpretation['statement'])
        print('  해석하는 근거: ' + ', '.join(interpretation['observation_ids']))
    else:
        print('대안 해석: 이 보기에는 포함하지 않았습니다.')
    print(f"논문 연결: {view['anchor']['claim_id']} --> {view['anchor']['id']} "
          f"[{view['anchor']['marker']}]")


def _describe(change):
    if change['id'] == 'claim-status':
        return f"주장 상태: {STATUSES[change['before']]} → {STATUSES[change['after']]}"
    if change['id'] == 'interpretation':
        return '대안 해석 추가: ' + change['after']['statement']
    edge = change['after']
    return (f"연결 추가: {edge['source']} -- {RELATIONS[edge['type']]} "
            f"[{edge['condition']}] --> {edge['target']} | 이유: {edge['rationale']}")


def main(argv=None):
    # Include help and parser failures in the UTF-8 stream contract.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(
        description='합성 연구 그래프 조회·비교·선택 미리보기. 저장하거나 적용하지 않습니다.',
        epilog='예: python -B -m scripts.graph_demo preview --select relation:O-03')
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in (('show', '근거·주장·대안 해석 연결 보기'),
                            ('diff', '초기 보기와 후보 보기의 변경 비교'),
                            ('preview', '선택한 변경만 반영한 가상 결과 보기')):
        command = commands.add_parser(name, help=help_text)
        command.add_argument('--format', choices=('human', 'json'), default='human')
        if name == 'show':
            command.add_argument('--view', choices=('main', 'candidate'), default='candidate')
        if name == 'preview':
            command.add_argument('--select', action='append', default=[], metavar='CHANGE_ID')
    args = parser.parse_args(argv)
    try:
        packet = load_packet()
        if args.command == 'show':
            data = project(packet, args.view)
        elif args.command == 'diff':
            data = compare(packet)
        else:
            data = preview(packet, args.select)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.format == 'json':
        print(json.dumps({'schema_version': 'claimbranch.graph-demo/v1',
                          'mode': 'synthetic-read-only', 'applied': False,
                          'source': packet['packet_id'], 'data': data},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print('합성 예제 · 읽기 전용 · 실제 연구/논문 변경 없음 · AI 호출 없음')
    print('배경: 민감도로 설명하려던 손상이 가지치기·양자화·압축에서 서로 다르게 관찰된 예제입니다.')
    print('초기(main)와 후보(candidate)는 실제 연구 분기가 아닌 계산된 보기입니다. 원자료 확인은 미완료입니다.\n')
    if args.command == 'show':
        print('보기: ' + args.view)
        _show(data)
    elif args.command == 'diff':
        print('초기 → 후보 변경 (모두 미적용):')
        for change in data:
            print(f"  {change['id']}: {_describe(change)}")
        print('관찰 자체는 변하지 않으며, 새 중심 주장이나 논문 문구를 채택하지 않습니다.')
    else:
        print('선택: ' + (', '.join(data['selected']) or '없음 — 초기 보기 유지'))
        print('제외: ' + (', '.join(data['omitted']) or '없음'))
        print('필요한 기존 근거/대상(복사하지 않음): ' + (', '.join(data['required_existing']) or '없음'))
        print('선택 후 가상 결과:')
        _show(data['result'])
        print('명시된 연결을 따라 찾은 논문 재검토 경로:')
        for path in data['impact_paths']:
            print('  ' + ' → '.join(path))
        if not data['impact_paths']:
            print('  없음 — 기록된 경로가 없다는 뜻이며, 과학적 영향이 없다는 판정은 아닙니다.')
        print('미리보기만 했습니다. 실제 반영·승인·부채 생성·파일 저장은 하지 않았습니다.')
    print('\n다음 확인: python -B -m scripts.graph_demo ' +
          ('diff' if args.command == 'show' else 'preview --select relation:O-03'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
