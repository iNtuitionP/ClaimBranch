"""Independent frozen provider exercises, not model-quality or release evidence."""
import hashlib

from claimbranch.core.canonical import canonical_bytes
from claimbranch.fixtures import replay_example
from .paper_draft import PaperDraftSession
from .paper_example import context_request
from .paper_service import PaperService


QUESTION = "Does the 0.4 percentage-point loss for Model A with 20% pruning and mask seed 42 justify the same claim for seed 43?"
RESPONSE = ("obs-1 reports a 0.4 percentage-point accuracy loss for run-accuracy with mask seed 42. "
            "That meets the 1 percentage-point budget for the measured mask, but replication with seed 43 is still unrun. "
            "Limit claim-pruning-detail to the observed mask until that replication supplies evidence.")
HUMAN_TEXT = "The measured 0.4 percentage-point loss supports the claim for seed 42 only; seed 43 remains untested."
HUMAN_REASON = "One measured pruning mask cannot establish replication. The planned seed-43 result is still unknown."


def workflow(variant="manual"):
    history = replay_example(variant, paper=True)
    before = history.manifest()
    service = PaperService(history)
    request = context_request(service)
    request["purpose"] = "critique-interpretation"
    request["selections"].append({"record_id": "interpretation", "fields": ["statement", "observation_ids"]})
    cases = []
    # Each is a fresh independent exercise, not five calls in one attempt budget.
    for name in ("adopted", "cancelled", "edited", "expired", "refused"):
        now = [1000]
        raw = canonical_bytes({"schema": "claimbranch.provider-result/v1",
                               "status": "refused" if name == "refused" else "ok",
                               "text": None if name == "refused" else RESPONSE})
        session = PaperDraftSession(service, frozen_result=raw, clock=lambda: now[0])
        # The question is explicit unfinished writing, not an accepted claim.
        # Include it in the same screened, bounded, digest-bound request.
        session.edit(QUESTION, "")
        outbound = session.prepare_request(request, include_draft=True)["outbound"]
        key = outbound["request"]["request_id"]
        session.begin_proposal(key, outbound["digest"])
        if name == "cancelled":
            session.cancel_request()
        elif name == "edited":
            session.edit(HUMAN_TEXT, HUMAN_REASON)
        elif name == "expired":
            now[0] = 1120
        arrival = session.complete_proposal(key)
        if name == "adopted":
            session.use_proposal(arrival["proposal"]["id"])
        session.edit(HUMAN_TEXT, HUMAN_REASON)
        review = session.review_draft()
        trace_digest = session.state()["traces"][0]["digest"]
        session.erase_trace(key)
        state = session.not_now()
        cases.append({"name": name, "question": QUESTION, "outbound": outbound,
                      "arrival": {"attempt": arrival["attempt"], "proposal": arrival["proposal"]},
                      "review": review, "state": state,
                      "manual_review_available": review["judgment"]["text"] == HUMAN_TEXT,
                      "trace_identity_retained": state["traces"][0]["digest"] == trace_digest})
    return {"schema": "claimbranch.paper-provider-example/v1", "classification": "synthetic-example",
            "scripted_example": True, "independent_runs": True, "variant": variant,
            "history_digest": hashlib.sha256(before).hexdigest(), "cases": cases,
            "source_unchanged": history.manifest() == before, "authorization_verified": False}
