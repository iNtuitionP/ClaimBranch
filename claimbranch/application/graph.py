"""Read-only, bounded episode graph. Labels are presentation, never new science.

Node bodies and relationships derive from verified fixture data and candidate
history. Korean captions summarize the one committed example; the inspector
retains source prose. Structural references are kept distinct from scientific
edges, and excluded branch work stays visibly excluded.
"""
OBSERVATION_CAPTIONS = {
    "pruning": ("가지치기", "예상한 손상 순서와 다르다"),
    "quantization": ("양자화", "여기서도 예상한 손상 순서와 다르다"),
    "compression": ("압축", "이 조건에서는 예상과 부합한다"),
}


def project_graph(history, packet, *, selection):
    view = history.view("alternative")
    changes = {item["id"]: item for item in view["changes"]}
    chosen = set(selection.closure)
    selected = set(selection.selected)
    nodes, edges = [], []

    def node(node_id, kind, label, caption, body, status, change_id=None):
        scope = "context" if change_id is None else "selected" if change_id in selected else "required" if change_id in chosen else "omitted"
        nodes.append({"id": node_id, "kind": kind, "label": label, "caption": caption,
                      "body": body, "status": status, "scope": scope})

    def edge(edge_id, source, target, kind, label, detail, *, change_id=None, scientific=False):
        edges.append({"id": edge_id, "source": source, "target": target, "kind": kind,
                      "label": label, "detail": detail, "scientific": scientific,
                      "included": change_id is None or change_id in chosen})

    claim, run, anchor = packet["claim"], packet["run"], packet["manuscript"]
    claim_change = next((item for item in changes.values() if item["kind"] == "claim-status"), None)
    contested = claim_change and claim_change["id"] in chosen and claim_change["body"]["status"] == "contested"
    node(run["id"], "run", "기록된 실험", "세 연산의 손상을 비교", " / ".join(claim["scope"]), "완료된 예제 기록")
    node(claim["id"], "claim", "검토하는 주장", "민감도만으로 손상을 설명할 수 있다", claim["statement"],
         "재검토 후보" if contested else "기존 주장 유지", claim_change["id"] if claim_change and claim_change["id"] in chosen else None)
    for observation in view["evidence"]:
        source = next(item for item in packet["observations"] if item["id"] == observation["id"])
        label, caption = OBSERVATION_CAPTIONS[source["operator"]]
        node(observation["id"], "observation", label, caption, observation["statement"], "예제 관찰")
        edge("produced-" + observation["id"], run["id"], observation["id"], "produced", "관찰을 얻음",
             "완료된 예제 실험에서 얻은 관찰입니다. 후속 실험의 결과가 아닙니다.")
    for item in changes.values():
        body = item["body"]
        if item["kind"] == "interpretation":
            caption = ("민감도 외에 변형의 구조와 효과도 검토해야 한다"
                       if body["statement"] == packet["unaided_human_interpretation"]["statement"] else body["statement"])
            node(item["id"], "interpretation", "검토하는 해석", caption, body["statement"], "판단 후보", item["id"])
            for observation in body["observation_ids"]:
                # Inverse of Interpretation.interprets(Observation), for reading left-to-right.
                edge("basis-" + observation, observation, item["id"], "interpreted-by", "해석의 근거",
                     "관찰을 읽고 해석을 형성합니다. 관찰 자체를 수정하는 연결은 아닙니다.", change_id=item["id"])
        elif item["kind"] == "scientific-edge":
            label = {"challenges": "반박", "qualifies": "조건부", "supports": "지지"}[body["edge_type"]]
            edge(item["id"], body["source_id"], body["target_id"], body["edge_type"], label,
                 body["rationale"], change_id=item["id"], scientific=True)
        elif item["kind"] == "experiment-plan":
            node(item["id"], "experiment", "다음 실험", "연산별 차이를 분리해 검증", body["objective"], "계획 · 미실행", item["id"])
            edge("tests-" + item["id"], item["id"], body["claim_id"], "tests", "검증할 계획",
                 "아직 실행하지 않은 계획입니다. 주장을 지지하거나 반박하는 결과로 세지 않습니다.", change_id=item["id"])
        elif item["kind"] == "claim-status":
            for basis in body["basis_ids"]:
                if changes[basis]["kind"] == "interpretation":
                    edge("reconsiders-" + basis, basis, body["claim_id"], "claim-basis", "재검토 근거",
                         "선택한 주장 상태 변경이 참조하는 해석입니다. 새 실험 결과를 뜻하지 않습니다.", change_id=item["id"])
    node(anchor["anchor_id"], "manuscript", "원고의 주장 문장", "이 판단이 논문의 문장에 닿는 곳", anchor["marker_id"], "원고 영향 확인")
    # Inverse of ManuscriptAnchor.expresses(Claim); this is not an applied patch.
    edge("expressed-by", claim["id"], anchor["anchor_id"], "expressed-by", "원고에 표현", "기존 원고가 이 주장을 표현합니다. 연결만으로 원고가 바뀌지 않습니다.")
    order = {"run": 0, "observation": 1, "claim": 2, "interpretation": 3, "manuscript": 4, "experiment": 5}
    nodes.sort(key=lambda item: (order[item["kind"]], item["id"]))
    return {"authority": "unverified-candidate", "nodes": nodes, "edges": edges}
