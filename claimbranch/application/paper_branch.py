"""Pure assembly of existing v3 commands for an explicitly reviewed draft.

No command schema, accepted store or authority is added. The history reducer
independently validates the resulting branch, provenance and selected basis.
"""
from dataclasses import asdict
from functools import lru_cache

from claimbranch.core.canonical import ContractError, bounded_text, decode, identifier
from claimbranch.core.review import Contribution, Judgment, Proposal


def judgment_value(value):
    return Judgment(value["project_id"], value["episode_id"], value["text"], value["rationale"],
                    tuple(Contribution(**item) for item in value["history"]))


def continue_judgment(source, draft):
    """Keep the recorded prefix, then reparent only the unrecorded suffix.

    Draft contribution content/author/trace is preserved. Its parent links may
    change when joining an independently started draft to recorded reasoning.
    Already shared contributions are kept once; no rationale is invented.
    """
    if not isinstance(draft, Judgment):
        raise ContractError("a typed complete draft judgment is required")
    bounded_text(draft.text)
    bounded_text(draft.rationale)
    if source is None:
        return draft
    source = judgment_value(source)
    if (source.project_id, source.episode_id) != (draft.project_id, draft.episode_id):
        raise ContractError("draft contribution chains must share a research context")
    shared = 0
    for before, after in zip(source.history, draft.history):
        if before != after:
            break
        shared += 1
    if shared == len(source.history):
        return draft
    result = source
    for item in draft.history[shared:]:
        if item.contributor == "human":
            result = result.edit(item.text, item.rationale)
        else:
            result = result.use_proposal(Proposal(item.proposal_id, draft.project_id, draft.episode_id,
                                                 item.text, item.trace_digest))
    if (result.text, result.rationale) != (draft.text, draft.rationale):
        raise ContractError("draft was superseded; refine it before recording the new reading")
    return result


def build_branch(history, request, judgment, *, operation_id, created_at, source_node_id=None):
    if history.schema_version in (5, 14):
        from claimbranch.core.paper_capacity import encode, decode
        candidate, raw = _imported_branch(history, encode(request, purpose='history'), judgment, operation_id, created_at, source_node_id)
        return candidate, decode(raw, purpose='manifest')
    return _build_branch(history, request, judgment, operation_id=operation_id, created_at=created_at, source_node_id=source_node_id)


@lru_cache(maxsize=16)
def _imported_branch(history, raw, judgment, operation_id, created_at, source_node_id):
    from claimbranch.core.paper_capacity import encode, decode
    candidate, domain = _build_branch(history, decode(raw, purpose='history'), judgment,
        operation_id=operation_id, created_at=created_at, source_node_id=source_node_id)
    return candidate, encode(domain, purpose='manifest')


def _build_branch(history, request, judgment, *, operation_id, created_at, source_node_id=None):
    """Return a new history and scientific preview, leaving the source intact."""
    from .paper_service import PaperService
    identifier(operation_id)
    if history.schema_version < 3:
        raise ContractError("draft recording requires the version-three paper profile")
    episode = request["episode_id"]
    if not any(item["id"] == episode and item["status"] == "active" for item in history.episodes()):
        raise ContractError("draft recording requires the explicit active episode")
    ref = request["ref"]
    has_branch = "alternative" in dict(history.heads)
    if ref != ("alternative" if has_branch else "main"):
        raise ContractError("draft on the existing alternative before recording; main cannot replace it")
    source = history.view(ref, episode_id=episode)
    joined = continue_judgment(source["judgment"] if has_branch else None, judgment)
    domain = (PaperService(history)._decode)(history.preview_paper_changes(ref, request["amendments"], request["selected_ids"],
                                                  joined, episode_id=episode, source_node_id=source_node_id).payload)
    selected = [item["after"] for item in domain["amendments"] if item["disposition"] != "omitted"]

    def command(current, kind, payload, key):
        return {"schema_version": history.schema_version, "id": key, "project_id": request["project_id"], "episode_id": episode,
                "created_at": created_at, "operation_type": kind, "expected_heads": dict(current.heads),
                "evidence_watermark": current.watermark, "payload": payload}

    candidate = history
    if not has_branch:
        candidate = candidate.append(command(candidate, "create-imported-reasoning-branch" if history.schema_version in (5, 14) else "create-reasoning-branch", {}, operation_id + "-branch"))
    payload = {"changes": selected, "judgment": asdict(joined)}
    if history.schema_version in (5, 14):
        payload.update(source_node_id=domain['source_node_id'], source_refs=domain['imported_sources'])
    candidate = candidate.append(command(candidate, "record-imported-interpretation" if history.schema_version in (5, 14) else "record-interpretation", payload, operation_id))
    return candidate, domain
