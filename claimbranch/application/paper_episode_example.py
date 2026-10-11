"""Frozen two-episode synthetic journey, not an import or acceptance path."""
from datetime import datetime
import hashlib

from claimbranch.core.canonical import decode
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.marked_text import tex_text
from claimbranch.fixtures import replay_example
from .paper_workspace import PaperWorkspace
from .paper_merge import PaperMergeSession
from .paper_service import PaperService
from .paper_manuscript import PaperManuscriptSession


def manuscript_followup(history, *, clock):
    """Explicit scripted wording over an illustrative source, never a file read."""
    service = PaperService(history)
    work = service.pending_work()
    replayed = PaperService(ResearchHistory.replay(history.seed, history.commands)).pending_work()
    current = service.query()
    item = next(item for item in work["items"] if item["kind"] == "manuscript" and item["episode_id"] == current["episode_id"])
    earlier = history.view("main", episode_id=history.episodes()[0]["id"])["judgment"]
    source = ("% Synthetic source illustration; not a verified original file\n\\section{Results}\n"
              f"% claimbranch:start id={item['anchor_id']}\n{tex_text(earlier['text'])}\n"
              f"% claimbranch:end id={item['anchor_id']}\n% Keep this surrounding text.\n").encode("utf-8")
    session = PaperManuscriptSession(history, work_id=item["id"], source=source, clock=clock)
    blank = session.draft.state()["draft"]["text"] == ""
    # A scripted human edit, not automatic wording chosen by the adapter.
    session.draft.edit(current["judgment"]["text"], current["judgment"]["rationale"])
    prepared = session.prepare()
    reviewed = session.finish(prepared["digest"], disposition="deferred" if prepared["ai_influenced"] else "not-required", answers=[])
    after = session.postimage(reviewed["digest"])
    session.not_now()
    return {"source": "calculated-merge-candidate", "current": current, "pending_work": work,
            "replayed_work_matches": replayed == work, "wording_started_blank": blank,
            "source_kind": "synthetic-generated-marked-text", "preview": prepared, "review": reviewed,
            "postimage_matches_review": hashlib.sha256(after).hexdigest() == reviewed["postimage_digest"],
            "work_unchanged": service.pending_work() == work,
            "wording_retained": session.draft.state()["draft"]["text"] == current["judgment"]["text"],
            "review_cleared": session.get_review() is None, "accepted_writes": 0, "authorization_verified": False}


def workflow(variant):
    history = replay_example(variant, series=True)
    first_close = next(index for index, raw in enumerate(history.commands)
                       if decode(raw)["operation_type"] == "close-episode")
    first = ResearchHistory(history.seed, history.commands[:first_close + 1])
    workspace = PaperWorkspace(first)
    prior_id, next_id = (item["id"] for item in history.episodes())
    draft = workspace.draft(prior_id, "main", "obs-1")
    text, reason = "Revisit the recorded pruning result.", "The seed-43 plan has not been run."
    draft.edit(text, reason)
    workspace.update_history(history)
    service = workspace.service
    merge_index = max(index for index, raw in enumerate(history.commands)
                      if decode(raw)["operation_type"] == "apply-selected-merge")
    merge = decode(history.commands[merge_index])
    now = int(datetime.fromisoformat(merge["created_at"].replace("Z", "+00:00")).timestamp())
    branch_index = max(index for index, raw in enumerate(history.commands[:merge_index])
                       if decode(raw)["operation_type"] == "create-reasoning-branch")
    before_branch = ResearchHistory(history.seed, history.commands[:branch_index])
    recording = decode(history.commands[merge_index - 1])["payload"]
    drafting = PaperWorkspace(before_branch, clock=lambda: now)
    current_draft = drafting.draft(next_id, "main", "obs-1")
    blank = current_draft.state()["draft"]["text"] == ""
    current_draft.edit(recording["judgment"]["text"], recording["judgment"]["rationale"])
    state = current_draft.state()
    branch = current_draft.prepare_branch({"schema_version": 1, **state["paper"],
        "draft_id": state["draft_id"], "draft_revision": state["revision"], "amendments": recording["changes"],
        "selected_ids": merge["payload"]["selected_ids"]})
    before_merge = current_draft.branch_candidate(branch["digest"])
    source_unchanged = drafting.history == before_branch
    drafting.update_history(before_merge)
    session = PaperMergeSession(before_merge, episode_id=next_id, manuscript_digest="b" * 64, clock=lambda: now)
    prepared = session.prepare(merge["payload"]["selected_ids"])
    reviewed = session.finish(prepared["digest"], disposition=merge["payload"]["disposition"], answers=merge["payload"]["answers"])
    candidate, _ = session.candidate(reviewed["digest"])
    candidate_view = PaperService(candidate).query()
    final_view = service.query()
    matches = all(candidate_view[key] == final_view[key] for key in ("nodes", "relations", "judgments"))
    session.not_now()
    return {"schema": "claimbranch.paper-episode-workflow/v1", "classification": "synthetic-example",
            "variant": variant, "scripted_example": True, "golden_match": True,
            "timeline": service.episodes(), "current": service.query(),
            "previous_with_current_evidence": service.query(episode_id=prior_id),
            "at_first_close": service.query(episode_id=prior_id, at_operation=decode(first.commands[-1])["id"]),
            "earlier_draft_retained": workspace.draft(prior_id, "main", "obs-1").state()["draft"]["text"] == text,
            "new_draft_blank": workspace.draft(next_id, "main", "obs-1").state()["draft"]["text"] == "",
            "branch_preview": branch, "branch_draft_started_blank": blank,
            "branch_source_unchanged": source_unchanged,
            "branch_draft_retained": current_draft.state()["draft"]["text"] == recording["judgment"]["text"],
            "merge_preview": prepared, "merge_review": reviewed, "reviewed_candidate_matches_example": matches,
            "merge_review_cleared": session.get_review() is None,
            "followup": manuscript_followup(candidate, clock=lambda: now),
            "accepted_writes": 0, "authorization_verified": False}
