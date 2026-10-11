"""Scripted, explicitly synthetic paper journey; not a human-value evaluation."""
from copy import deepcopy

from claimbranch.core.canonical import ContractError, decode
from claimbranch.fixtures import replay_example
from .paper_draft import PaperDraftSession
from .paper_service import PaperService


def context_request(service):
    view = service.query("main")
    claim_fields = ["statement", "status", "role", "scope", "parent_ids"]
    return {"schema_version": 1, "project_id": view["project_id"], "episode_id": view["episode_id"],
            "ref": "main", "view_digest": view["digest"], "purpose": "plan-experiment",
            "selections": [
                *({"record_id": key, "fields": claim_fields} for key in ("thesis", "claim-pruning", "claim-pruning-detail")),
                {"record_id": "obs-1", "fields": ["statement", "status", "value", "run_id", "metric", "conditions", "source"]},
                {"record_id": "run-accuracy", "fields": ["question", "method", "conditions", "metric", "source", "status"]},
                {"record_id": "replication", "fields": ["claim_id", "objective", "status", "conditions", "metric"]}],
            "scientific_edge_ids": ["edge-pruning", "edge-detail", "edge-thesis"]}


def scenario_request(service, outcome):
    view = service.query("main")
    return {"schema_version": 1, "project_id": view["project_id"], "episode_id": view["episode_id"],
            "ref": "main", "view_digest": view["digest"], "plan_id": "replication", "outcome": outcome,
            "assumed_observation": {
                "supports": "Assume the stated pruning replication remains within 1 percentage point accuracy loss.",
                "challenges": "Assume the stated pruning replication exceeds 1 percentage point accuracy loss.",
                "inconclusive": "Assume the stated pruning replication cannot determine accuracy loss."}[outcome],
            "rationale": "Synthetic conditional example; no experiment was executed or evidence accepted."}


def workflow(variant):
    if variant not in ("manual", "recorded"):
        raise ContractError("unknown scripted workflow variant")
    # Both routes start from the same paper and a separate blank working draft.
    history = replay_example("manual", paper=True)
    before = history.manifest()
    service = PaperService(history)
    response = None
    if variant == "recorded":
        recorded = replay_example("recorded", paper=True).view("main")["judgment"]
        response = next(item["text"] for item in recorded["history"] if item["contributor"] == "ai")
    session = PaperDraftSession(service, frozen_response=response)
    initial = session.state()
    request = context_request(service)
    context = decode(service.compile_context(request).payload)
    outbound = proposal = None
    if response is not None:
        outbound = session.prepare_request(request)["outbound"]
        proposal = session.request_proposal(outbound["request"]["request_id"], outbound["digest"])["proposal"]
        session.use_proposal(proposal["id"])
    session.edit(
        "The measured 0.4 percentage-point accuracy loss applies to Model A with 20 percent pruning, mask seed 42, on these 2000 synthetic examples; mask seed 43 remains untested.",
        "A single pruning mask meets the 1 percentage-point loss budget, but cannot establish the same result for another mask.")
    review = session.review_draft()
    records = {item["id"]: deepcopy(item) for item in history.view("main")["changes"]}
    records["claim-pruning-detail"]["body"].update(
        statement="For Model A with 20 percent pruning and mask seed 42, measured accuracy loss is 0.4 percentage points on 2000 synthetic examples.",
        scope="Mask seed 42 only; the result does not establish performance for seed 43.")
    records["edge-pruning"]["body"].update(
        edge_type="qualifies", rationale="One measured pruning mask limits the scope; another mask has not been observed.")
    records["interpretation"]["body"].update(statement=review["judgment"]["text"], observation_ids=["obs-1"])
    records["replication"]["body"]["objective"] = "Repeat the 20 percent pruning evaluation with mask seed 43 against the same baseline before generalizing the claim."
    state = session.state()
    changes = session.prepare_changes({
        "schema_version": 1, **state["paper"], "draft_id": state["draft_id"], "draft_revision": state["revision"],
        "amendments": [records[key] for key in ("claim-pruning-detail", "edge-pruning", "interpretation", "replication")],
        "selected_ids": ["edge-pruning", "interpretation"]})
    changes_review = session.finish_changes_review(
        changes["digest"], disposition="deferred" if changes["preview"]["provenance"]["ai_influenced"] else "not-required", answers=[])
    return {"schema": "claimbranch.paper-workflow/v1", "classification": "synthetic-example",
            "scripted_example": True, "variant": variant,
            "initial_draft_blank": initial["draft"]["text"] == "" and initial["draft"]["contributions"] == [],
            "context": context, "outbound": outbound, "proposal": proposal, "review": review,
            "changes_preview": changes, "changes_review": changes_review,
            "scenario": service.scenario(scenario_request(service, "challenges")),
            "state": session.not_now(), "source_unchanged": history.manifest() == before,
            "authorization_verified": False}
