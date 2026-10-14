"""Volatile adapter for episode/ref/node drafts over one immutable history.

No UI controls, command submission, accepted writes or persistence live here.
An owner may supply a later candidate history; drafts never migrate contexts.
"""
from threading import RLock

from claimbranch.core.canonical import ContractError
from claimbranch.core.research_history import ResearchHistory
from .paper_draft import PaperDraftSession
from .paper_service import PaperService


DRAFT_LIMIT = 16


def _work_owner(owner):
    if (not isinstance(owner, (tuple, list)) or len(owner) != 3
            or any(not isinstance(value, str) or not value for value in owner)):
        raise ContractError('Choose an existing episode/ref/node judgment owner.')
    return tuple(owner)


class PaperWorkspace:
    def __init__(self, history, *, frozen_response=None, clock=None):
        self._service = PaperService(history)
        self._history = history
        self._drafts = {}
        self._candidates = {}
        self._proposal_entries = []
        self._recorded_origins = []
        self._personal_explanations = []
        self._checkpoint_app = None
        self._saved_proposal_payloads = set()
        self._proposal_active = {}
        self._work_links, self._work_choices = {}, {}
        self.work_revision = 0
        self._response, self._clock = frozen_response, clock
        self._lock = RLock()

    @property
    def ai_available(self):
        return self._response is not None

    @property
    def history(self):
        return self._history

    @property
    def service(self):
        return self._service

    def draft(self, episode_id, ref, node_id):
        with self._lock:
            view = self._service.query(ref, episode_id=episode_id)
            if not any(node["id"] == node_id for node in view["nodes"]):
                raise ContractError("draft context requires an existing paper node")
            key = (view["episode_id"], ref, node_id)
            if key not in self._drafts:
                if len(self._drafts) >= (32 if self._history.schema_version in (4, 5) else DRAFT_LIMIT):
                    raise ContractError("volatile workspace draft limit reached; existing drafts are retained")
                self._drafts[key] = PaperDraftSession(self._service, ref=ref, episode_id=view["episode_id"],
                    frozen_response=self._response, clock=self._clock)
            session = self._drafts[key]
            if self._history.schema_version == 5:
                session._imported_subject = node_id
            return session

    def work_owner(self, episode_id, ref, node_id):
        key = (episode_id, ref, node_id)
        return self._work_choices.get(key, key)

    def work_nodes(self, owner):
        owner = _work_owner(owner)
        return tuple(sorted(self._work_links.get(owner, {owner[2]})))

    @property
    def volatile_links(self):
        return any(len(nodes) > 1 for nodes in self._work_links.values())

    def link_work(self, owner, node_ids, *, activate_ids=None, expected_history=None, expected_revision=None):
        """Link references, never copy text or infer a scientific relationship."""
        with self._lock:
            owner = _work_owner(owner)
            if expected_history is not None and expected_history is not self.history:
                raise ContractError('Source changed. Reopen judgment links; existing work is retained.')
            if expected_revision is not None and expected_revision != self.work_revision:
                raise ContractError('Work links changed. Reopen the selection; no links were applied.')
            if (not isinstance(node_ids, (list, tuple)) or any(not isinstance(key, str) for key in node_ids)
                    or not 1 <= len(node_ids) <= 16 or len(set(node_ids)) != len(node_ids) or owner[2] not in node_ids):
                raise ContractError('Choose 1–16 distinct source nodes, including the original owner.')
            nodes = set(node_ids)
            if activate_ids is not None and (not isinstance(activate_ids, (tuple, list))
                    or any(not isinstance(key, str) for key in activate_ids)
                    or len(set(activate_ids)) != len(activate_ids)):
                raise ContractError('Choose distinct linked nodes to activate this judgment.')
            active = nodes if activate_ids is None else set(activate_ids)
            if not active <= nodes:
                raise ContractError('Activate only a node linked to this judgment.')
            view = self.service.query(owner[1], episode_id=owner[0])
            if not nodes <= {node['id'] for node in view['nodes']}:
                raise ContractError('Links require existing source nodes in the same episode and branch.')
            old = set(self.work_nodes(owner))
            if old != nodes:
                # A new linked work requires a bounded session, while selecting
                # already-linked or separate manual work allocates nothing.
                session = self.draft(*owner)
                session.invalidate_change_reviews()
                self._work_links[owner] = frozenset(nodes)
            choices = {key: value for key, value in self._work_choices.items()
                       if value != owner or key[2] in nodes}
            choices.update({(*owner[:2], key): owner for key in active})
            if old != nodes or choices != self._work_choices:
                self.work_revision += 1
            self._work_choices = choices

    def activate_work(self, owner, node_id):
        with self._lock:
            owner = _work_owner(owner)
            if node_id not in self.work_nodes(owner):
                raise ContractError('Link this node explicitly before using the judgment here.')
            view = self.service.query(owner[1], episode_id=owner[0])
            if owner[2] not in {node['id'] for node in view['nodes']}:
                raise ContractError('Choose an existing source-node judgment.')
            # Returning to manual work must not allocate a scarce review session.
            key = (*owner[:2], node_id)
            if self.work_owner(*key) != owner:
                self._work_choices[key] = owner
                self.work_revision += 1

    def update_history(self, history):
        with self._lock:
            if (not isinstance(history, ResearchHistory) or history.seed != self._history.seed
                    or history.commands[:len(self._history.commands)] != self._history.commands):
                raise ContractError("workspace refresh requires an append-only extension of the same history")
            service = PaperService(history)
            # Validate every context before changing any owned source/draft.
            for episode_id, ref, node_id in self._drafts:
                view = service.query(ref, episode_id=episode_id)
                if not set(self.work_nodes((episode_id, ref, node_id))) <= {node['id'] for node in view['nodes']}:
                    raise ContractError("history refresh lost a draft's paper context")
            for session in self._drafts.values():
                session.update_source(service)
            self._history, self._service = history, service

    def candidates(self, episode_id, ref, node_id):
        """Return stable authored work; new candidate IDs are never draft owners."""
        from .paper_candidates import PaperCandidates
        with self._lock:
            session = self.draft(episode_id, ref, node_id)
            key = (episode_id, ref, node_id)
            if key not in self._candidates:
                self._candidates[key] = PaperCandidates(self, key, session)
            return self._candidates[key]

    def proposal_history(self):
        from .paper_proposal_work import historical_entries
        return historical_entries(self)

    def recorded_origins(self):
        from copy import deepcopy
        return deepcopy(self._recorded_origins)

    def origin_for(self, record_id):
        from claimbranch.core.canonical import canonical_bytes
        from claimbranch.core.paper_changes import AmendmentLineage
        for record in reversed(self._recorded_origins):
            for raw in record['lineages']:
                origin = AmendmentLineage.restore(canonical_bytes(raw))
                if origin.amendment['id'] == record_id:
                    return origin
        return None

    def erase_proposal_payload(self, request_id):
        """Explicit historical erasure retains adopted origin and trace hashes."""
        with self._lock:
            entry = next((e for e in self._proposal_entries if e['request_id'] == request_id), None)
            if entry is None or entry['trace_digest'] is None:
                raise ContractError('Choose a received historical payload')
            from .paper_proposal_work import check_payload_erasure
            check_payload_erasure(self, request_id)
            for worker in self._proposal_active.values():
                if request_id in worker._owned_requests:
                    worker.erase_payload(request_id)
                    return
            entry['result'] = None
            entry['payload_availability'] = 'erased'
