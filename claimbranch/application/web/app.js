"use strict";
const $ = id => document.getElementById(id);
let current = null;
let busy = false;
let localDirty = false;
let reviewDirty = false;
let graphVisible = false;
const labels = {"claim-status":"주장 C-01: 재검토 필요", "I-01":"작성한 해석 I-01",
  "edge-O-01":"가지치기 관찰 → 주장", "edge-O-02":"양자화 관찰 → 주장",
  "edge-O-03":"압축 관찰 → 주장", "optional-experiment":"후속 실험 계획", "A-01":"원고 문장 A-01"};
function list(id, values) {
  $(id).replaceChildren(...values.map(value => {const item = document.createElement("li"); item.textContent = value; return item;}));
}
function focus(id) { requestAnimationFrame(() => $(id).focus()); }
function status(message) { $("status").textContent = message; }
function showContextGraph(show) {
  graphVisible = show;
  $("show-evidence").setAttribute("aria-pressed", String(!show));
  $("show-graph").setAttribute("aria-pressed", String(show));
  $("evidence").hidden = show;
  $("graph-panel").hidden = !show;
  if (show) requestAnimationFrame(ClaimBranchGraph.draw);
}
function restoreReviewInputs(review) {
  if (!review) return;
  $("select-claim").checked = review.selected.includes("claim-status");
  $("select-experiment").checked = review.selected.includes("optional-experiment");
  const choice = [...document.querySelectorAll("input[name=explanation]")].find(input => input.value === review.disposition);
  if (choice) choice.checked = true;
  $("answer").value = review.answers.join("\n");
}
function render(data, syncDraft = false) {
  current = data;
  const state = data.state;
  $("workspace").hidden = false;
  $("claim").textContent = state.claim.statement;
  $("evidence").replaceChildren(...state.observations.map(observation => {
    const card = document.createElement("article"); card.className = "evidence-card";
    const heading = document.createElement("h3"); heading.textContent = observation.operator;
    const relationship = document.createElement("p"); relationship.className = "relationship";
    relationship.textContent = observation.relationship_to_claim === "challenges" ? "기존 주장에 반하는 관찰" : "해당 조건에서만 부합";
    const body = document.createElement("p"); body.textContent = observation.rationale;
    const id = document.createElement("p"); id.className = "muted"; id.textContent = observation.id + " · 예제 관찰";
    card.append(heading, relationship, body, id); return card;
  }));
  if (syncDraft) { $("draft").value = state.draft.text; $("rationale").value = state.draft.rationale; localDirty = false; }
  const previous = state.before_proposal;
  $("before-proposal").hidden = !previous || !(previous.text || previous.rationale);
  $("before-proposal-text").textContent = previous ? previous.text : "";
  $("before-proposal-rationale").textContent = previous ? previous.rationale : "";
  $("load-example").hidden = Boolean(state.draft.text || state.draft.rationale || state.proposal || state.outbound || state.draft.ai_influenced);
  ClaimBranchGraph.render(!localDirty && !reviewDirty && state.review ? state.review.graph : null);
  showContextGraph(graphVisible);
  $("explanation").hidden = !state.draft.ai_influenced;
  $("outbound").hidden = !state.outbound || localDirty;
  if (state.outbound) $("outbound-json").textContent = JSON.stringify(state.outbound, null, 2);
  $("proposal").hidden = !state.proposal;
  if (state.proposal) {
    $("proposal-text").textContent = state.proposal.text;
    $("proposal-state").textContent = state.proposal.adopted ? "초안에 가져왔습니다. 수정한 뒤 판단의 이유를 남겨 주세요." : state.proposal.state === "proposed" ? "아직 초안이나 판단에 반영되지 않았습니다." : "이 제안은 취소되었거나 유효하지 않습니다. 직접 작성을 계속할 수 있습니다.";
  }
  $("review").hidden = !state.review || localDirty || reviewDirty;
  if (state.review) {
    const review = state.review;
    for (const key of ["selected", "required", "omitted"]) list(key, review[key].length ? review[key].map(id => labels[id] || id) : ["없음"]);
    $("review-text").textContent = review.text;
    $("review-rationale").textContent = "판단의 이유: " + review.rationale;
    list("impact", review.impact_paths.map(path => path.map(id => labels[id] || id).join(" → ")));
    $("changes").textContent = JSON.stringify(review.changes, null, 2);
    $("before").textContent = review.manuscript_before;
    $("after").textContent = review.manuscript_after;
    $("manuscript-note").textContent = review.has_manuscript_candidate ? "선택한 해석을 원고와의 연결에 따라 문장 후보로 옮겼습니다. 실제 원고를 수정하거나 컴파일하지 않습니다." : "이번 선택에는 원고에 연결된 해석이 없어 문장 후보를 만들지 않았습니다. 현재 원고를 그대로 보여 줍니다.";
    list("contributions", review.contributions.map(item => (item.contributor === "ai" ? "AI 원문: " : "사람의 작성·수정: ") + item.text));
  }
  $("result").hidden = !state.result || localDirty || reviewDirty;
  if (state.result) {
    $("result-text").textContent = "주장 C-01의 상태: " + (state.result.claim_status === "contested" ? "재검토 필요" : "기존 상태 유지");
    list("candidate-debts", state.result.candidate_debts.map(kind => kind === "manuscript" ? (state.result.has_manuscript_candidate ? "원고 반영과 컴파일 확인이 남습니다." : "원고 영향 검토가 남습니다. 이번 선택에서는 수정 문장을 만들지 않았습니다.") : "AI가 관여한 판단을 내 말로 설명하는 일이 남습니다."));
  }
  updateControls();
}
function updateControls() {
  for (const button of document.querySelectorAll("button[id]")) button.disabled = busy || !current;
  if (!current) return;
  const state = current.state, now = Math.floor(Date.now() / 1000);
  $("proposal-use").disabled = busy || localDirty || !state.proposal || state.proposal.adopted || state.proposal.state !== "proposed" || now >= state.proposal.expires_at;
  $("preview-result").disabled = busy || localDirty || reviewDirty || !state.review || now >= state.review.expires_at;
  $("request-send").disabled = busy || localDirty || !state.outbound || now >= state.outbound.expires_at;
  if (state.review) $("review-expiry").textContent = now >= state.review.expires_at ? "검토 시간이 지났습니다. 선택한 변경을 다시 검토해 주세요. 초안은 남아 있습니다." : "검토 유효 시간: " + Math.max(0, state.review.expires_at - now) + "초. 입력이나 선택을 바꾸면 다시 검토해야 합니다.";
}
async function request(path, value) {
  const headers = {"Content-Type":"application/json"};
  if (current) headers["X-ClaimBranch-CSRF"] = current.csrf;
  const response = await fetch(path, {method:"POST", headers, credentials:"same-origin", cache:"no-store", body:JSON.stringify(value)});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 409) throw new Error("다른 탭에서 세션이 바뀌었습니다. 현재 입력을 따로 보관한 뒤 새로고침해 주세요. 자동으로 덮어쓰지 않았습니다.");
    if (response.status === 401) throw new Error("세션이 끝났습니다. 화면의 입력을 보관한 뒤 체험을 다시 실행해 주세요.");
    throw new Error(result.error || "요청을 처리하지 못했습니다. 초안은 화면에 남아 있습니다.");
  }
  return result;
}
async function command(action, fields = {}, syncDraft = false) {
  const data = await request("/api/" + action, {revision:current.revision, ...fields});
  render(data, syncDraft); return data;
}
async function save() { await command("edit", {text:$("draft").value, rationale:$("rationale").value}, true); }
function action(id, run) {
  $(id).addEventListener("click", async () => {
    if (busy || !current) return;
    busy = true; $("error").hidden = true; updateControls();
    // Freeze inputs while the local command is in flight so a reply cannot
    // overwrite typing that happened after its exact submitted draft.
    const inputs = [...document.querySelectorAll("textarea,input")];
    inputs.forEach(input => { input.disabled = true; });
    try { await run(); }
    catch (error) { $("error").textContent = error.message; $("error").hidden = false; }
    finally { busy = false; inputs.forEach(input => { input.disabled = false; }); updateControls(); }
  });
}
for (const id of ["draft", "rationale"]) $(id).addEventListener("input", () => {
  localDirty = true; $("review").hidden = $("result").hidden = $("outbound").hidden = true;
  ClaimBranchGraph.render(null);
  status("작성 중입니다. 초안을 유지하거나 다음 동작을 누르면 이 세션에 반영됩니다."); updateControls();
});
for (const input of document.querySelectorAll("#selection-heading ~ input, #select-claim, #select-experiment, #explanation input, #answer")) input.addEventListener("input", () => {
  reviewDirty = true; $("review").hidden = $("result").hidden = true; ClaimBranchGraph.render(null); updateControls();
});
$("show-evidence").addEventListener("click", () => showContextGraph(false));
$("show-graph").addEventListener("click", () => showContextGraph(true));
action("load-example", async () => {
  if ($("draft").value || $("rationale").value) throw new Error("작성 중인 초안을 보존했습니다. 예시는 새 빈 세션에서 열어 주세요.");
  await command("load-example", {}, true);
  restoreReviewInputs(current.state.review);
  showContextGraph(true);
  status("기록된 합성 예시를 불러왔습니다. 노드를 선택해 근거·해석·후속 실험의 연결을 확인해 보세요.");
  $("graph-panel").scrollIntoView({block:"start"});
});
action("save", async () => { await save(); status("초안을 이 실행 중에 유지했습니다. 아직 판단을 확정하지 않았습니다."); });
action("request-preview", async () => { await save(); await command("preview-request"); status("예제 요청에 포함할 내용을 확인해 주세요."); focus("outbound"); });
action("request-send", async () => { await command("request-proposal", {request_id:current.state.outbound.request_id}); status("예제 AI 제안이 도착했습니다. 아직 반영되지 않았습니다."); focus("proposal"); });
action("request-cancel", async () => { await command("cancel-request"); status("요청을 취소했습니다. 직접 작성을 계속할 수 있습니다."); focus("draft"); });
action("proposal-reject", async () => { await command("cancel-request"); status("제안을 더 사용하지 않습니다. 이미 가져와 수정한 기여 이력은 유지됩니다."); focus("draft"); });
action("proposal-use", async () => { await command("use-proposal", {}, true); status("제안을 초안에 가져왔습니다. 당신의 해석과 이유를 확인해 주세요."); focus("draft"); });
action("prepare", async () => {
  await save();
  const selected = [];
  if ($("select-claim").checked) selected.push("claim-status");
  if ($("select-experiment").checked) selected.push("optional-experiment");
  let disposition = "not-required", answers = [];
  if (current.state.draft.ai_influenced) {
    const choice = document.querySelector("input[name=explanation]:checked");
    if (!choice) throw new Error("AI가 관여한 판단을 설명할지, 나중에 확인할지 직접 선택해 주세요.");
    disposition = choice.value;
    if (disposition === "answered") answers = [$("answer").value];
  }
  const data = await request("/api/prepare", {revision:current.revision, selected, disposition, answers});
  reviewDirty = false; render(data); status("선택한 변경과 원고 후보를 확인해 주세요. 실제 승인은 아직 실행되지 않습니다."); focus("review");
});
action("preview-result", async () => { await command("preview-result"); status("반영 후 상태를 미리 보았습니다. 실제 저장과 원고 변경은 없습니다."); focus("result"); });
action("not-now", async () => { await command("not-now"); status("판단을 미뤘습니다. 초안은 남아 있고, 새 미완료 작업은 만들지 않았습니다."); focus("draft"); });
async function start() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const token = fragment.get("bootstrap");
  history.replaceState(null, "", "/");
  try {
    let data;
    if (token) data = await request("/api/session", {bootstrap:token});
    else { const response = await fetch("/api/state", {credentials:"same-origin", cache:"no-store"}); if (!response.ok) throw new Error("체험 세션이 없습니다. 터미널에서 안내한 새 체험 주소로 접속해 주세요."); data = await response.json(); }
    restoreReviewInputs(data.state.review);
    graphVisible = data.state.example_loaded;
    render(data, true); status(data.state.draft.text ? "이 실행에서 유지한 초안을 다시 열었습니다. 실제 확정된 변경은 없습니다." : "아직 정해진 판단이 없습니다. 관찰을 읽고 당신의 해석을 적어 주세요.");
    if (data.state.example_loaded) {status("기록된 합성 예시입니다. 그래프의 노드를 선택해 근거와 다음 실험을 살펴보세요."); $("graph-panel").scrollIntoView({block:"start"});}
  } catch (error) { status("체험을 열지 못했습니다."); $("error").textContent = error.message; $("error").hidden = false; }
}
setInterval(updateControls, 1000);
window.addEventListener("beforeunload", event => { if (localDirty) {event.preventDefault(); event.returnValue = "";} });
start();
