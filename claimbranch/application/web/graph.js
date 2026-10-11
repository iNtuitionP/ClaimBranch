"use strict";
// Episode-local projection: interaction selects a node, never edits the graph.
window.ClaimBranchGraph = (() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const kinds = {run:"실험 기록", observation:"관찰 · 근거", claim:"주장", interpretation:"해석", experiment:"후속 실험", manuscript:"원고"};
  const scopes = {context:"공통 맥락", selected:"직접 선택", required:"함께 필요한 변경", omitted:"이번에 제외"};
  const colors = {challenges:"#ad563d", qualifies:"#9d792c", supports:"#34764d", tests:"#76619e",
    "claim-basis":"#176b59", "expressed-by":"#176b59", "interpreted-by":"#8a9c8a", produced:"#a5ada2"};
  let graph = null, selectedId = null;
  const get = id => document.getElementById(id);
  const make = (tag, className, text) => { const el = document.createElement(tag); if (className) el.className = className; if (text !== undefined) el.textContent = text; return el; };
  const svg = (tag, attrs) => { const el = document.createElementNS(svgNS, tag); for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value); return el; };

  function select(id, moveFocus = false) {
    if (!graph) return;
    const node = graph.nodes.find(item => item.id === id);
    if (!node) return;
    selectedId = id;
    for (const button of get("graph-nodes").children) {
      const active = button.dataset.nodeId === id;
      button.classList.toggle("is-selected", active);
      button.setAttribute("aria-pressed", String(active));
      if (active && moveFocus) button.focus();
    }
    get("graph-detail-kind").textContent = kinds[node.kind] + " / " + (node.id === "optional-experiment" ? "EP-01" : node.id);
    get("graph-detail-title").textContent = node.caption;
    get("graph-detail-body").textContent = node.body;
    get("graph-detail-status").textContent = node.status + " · " + scopes[node.scope] + " · 합성 자료의 원문";
    const links = graph.edges.filter(edge => edge.source === id || edge.target === id);
    get("graph-detail-links").replaceChildren(...links.map(edge => {
      const otherId = edge.source === id ? edge.target : edge.source;
      const other = graph.nodes.find(item => item.id === otherId);
      const item = make("li");
      const button = make("button", "graph-link", (edge.source === id ? "→ " : "← ") + edge.label + " · " + other.label + (edge.included ? "" : " · 제외"));
      button.type = "button";
      button.title = edge.detail;
      button.addEventListener("click", () => select(otherId, true));
      item.append(button);
      return item;
    }));
    draw();
  }

  function draw() {
    const surface = get("graph-surface"), wires = get("graph-wires");
    if (!graph || !surface.getBoundingClientRect().width || innerWidth <= 720) return;
    const bounds = surface.getBoundingClientRect();
    wires.setAttribute("viewBox", `0 0 ${bounds.width} ${bounds.height}`);
    const definitions = svg("defs", {});
    for (const [kind, color] of Object.entries(colors)) {
      const marker = svg("marker", {id:"arrow-" + kind, viewBox:"0 0 10 10", refX:9, refY:5, markerWidth:6, markerHeight:6, orient:"auto-start-reverse"});
      marker.append(svg("path", {d:"M 1 1 L 9 5 L 1 9 z", fill:color}));
      definitions.append(marker);
    }
    const paths = [], labels = [];
    for (const edge of graph.edges) {
      const source = get("graph-nodes").querySelector(`[data-node-id="${CSS.escape(edge.source)}"]`).getBoundingClientRect();
      const target = get("graph-nodes").querySelector(`[data-node-id="${CSS.escape(edge.target)}"]`).getBoundingClientRect();
      let sx, sy, tx, ty, d;
      if (edge.kind === "claim-basis") {
        sx = source.x + source.width * .5 - bounds.x; sy = source.y - bounds.y;
        tx = target.x + target.width * .5 - bounds.x; ty = target.bottom - bounds.y;
        d = `M ${sx} ${sy} L ${tx} ${ty + 4}`;
      } else if (edge.kind === "tests") {
        sx = source.x - bounds.x; sy = source.y + source.height * .35 - bounds.y;
        tx = target.right - bounds.x; ty = target.bottom - bounds.y - 18;
        const bend = (sx + tx) / 2;
        d = `M ${sx} ${sy} C ${bend} ${sy}, ${bend} ${ty}, ${tx + 4} ${ty}`;
      } else {
        sx = source.right - bounds.x; sy = source.y + source.height * .5 - bounds.y;
        tx = target.x - bounds.x; ty = target.y + target.height * .5 - bounds.y;
        if (edge.scientific) ty += (graph.nodes.filter(n => n.kind === "observation").findIndex(n => n.id === edge.source) - 1) * 32;
        if (edge.kind === "interpreted-by") ty += (graph.nodes.filter(n => n.kind === "observation").findIndex(n => n.id === edge.source) - 1) * 28;
        const bend = (sx + tx) / 2;
        d = `M ${sx} ${sy} C ${bend} ${sy}, ${bend} ${ty}, ${tx - 4} ${ty}`;
      }
      const adjacent = edge.source === selectedId || edge.target === selectedId;
      const group = svg("g", {"data-edge-id":edge.id, opacity:edge.included ? (adjacent ? 1 : .4) : .22});
      group.append(svg("path", {d, fill:"none", stroke:colors[edge.kind], "stroke-width":adjacent ? 2.1 : 1.4,
        "stroke-dasharray":edge.kind === "tests" || !edge.included ? "6 5" : "none", "marker-end":"url(#arrow-" + edge.kind + ")"}));
      const title = svg("title", {}); title.textContent = edge.label + ": " + edge.detail; group.append(title);
      paths.push(group);
      if (edge.scientific || edge.kind === "claim-basis" || edge.kind === "tests") {
        let x = (sx + tx) / 2, y = (sy + ty) / 2;
        if (edge.kind === "claim-basis") x += 31;
        const text = svg("text", {x, y:y - 7, "text-anchor":"middle", fill:colors[edge.kind], class:"graph-edge-label", opacity:edge.included ? 1 : .35});
        text.textContent = edge.label;
        labels.push(text);
      }
    }
    wires.replaceChildren(definitions, ...paths, ...labels);
  }

  function render(value) {
    graph = value;
    get("graph-content").hidden = !graph;
    get("graph-empty").hidden = Boolean(graph);
    get("graph-count").textContent = graph ? `${graph.nodes.length}개 노드 · ${graph.edges.length}개 연결` : "검토 전";
    if (!graph) {get("graph-nodes").replaceChildren(); get("graph-wires").replaceChildren(); return;}
    let observationIndex = 0;
    get("graph-nodes").replaceChildren(...graph.nodes.map(node => {
      const button = make("button", "graph-node graph-" + node.kind + " scope-" + node.scope);
      button.type = "button";
      button.dataset.nodeId = node.id;
      if (node.kind === "observation") button.dataset.order = observationIndex++;
      button.setAttribute("aria-label", kinds[node.kind] + ": " + node.caption + ". " + node.status + ". " + scopes[node.scope]);
      button.append(make("span", "node-kicker", node.label + " · " + (node.id === "optional-experiment" ? "EP-01" : node.id)),
        make("strong", "node-caption", node.caption), make("span", "node-status", node.scope === "omitted" ? "이번에 제외" : node.status));
      button.addEventListener("click", () => select(node.id));
      return button;
    }));
    if (!graph.nodes.some(node => node.id === selectedId)) selectedId = graph.nodes.find(node => node.kind === "claim").id;
    select(selectedId);
    requestAnimationFrame(draw);
  }
  new ResizeObserver(() => requestAnimationFrame(draw)).observe(document.getElementById("graph-surface"));
  return {render, draw};
})();
