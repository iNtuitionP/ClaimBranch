"""Detached branch and merge previews; never replace the workspace's history."""
import hashlib

from claimbranch.core.canonical import ContractError
from .paper_merge import PaperMergeSession
from .tui_manuscript import read_source


class BranchFlow:
    def __init__(self, app, *, branch_session=None, branch_preview=None, clock=None):
        self.app, self.origin, self.episode = app, app.paper.history, app.episode_id
        self.history = self.origin
        self.branch_session, self.branch = branch_session, branch_preview
        self.clock = clock
        self.selected, self.buffers = set(), {}
        self.path = ''
        self.merge = self.candidate = None
        self.materialized = branch_session is None
        self.owner_key = None

    def guard(self):
        valid = self.origin == self.app.paper.history
        if self.branch_session:
            current = self.branch_session.get_branch_preview()
            valid = valid and current is not None and current['digest'] == self.branch['digest']
        if not valid:
            self.clear()
            raise ContractError('Source draft or history changed/expired. Return and prepare a new candidate.')

    def clear(self):
        if self.merge:
            self.merge.not_now()
        self.candidate = None

    def restore_inputs(self, previous):
        if previous:
            self.buffers = {name: list(values) for name, values in previous.buffers.items()}
            if previous.origin == self.origin:
                self.path = previous.path
            previous.clear()

    def materialize(self):
        self.guard()
        if not self.materialized:
            self.history = self.branch_session.branch_candidate(self.branch['digest'])
            self.selected = set(self.branch['preview']['selection']['selected'])
            self.materialized = True
        return self.history

    def choices(self):
        self.guard()
        before = {item['id']: item for item in self.history.view('main', episode_id=self.episode)['changes']}
        return {item['id']: item for item in self.history.view('alternative', episode_id=self.episode)['changes']
                if before.get(item['id']) != item}

    def toggle(self, key):
        if key not in self.choices():
            raise ContractError('Choose a changed alternative record.')
        self.clear()
        self.selected.remove(key) if key in self.selected else self.selected.add(key)

    def load_source(self, path):
        self.guard()
        source = read_source(path)
        fingerprint = hashlib.sha256(source).hexdigest()
        if self.merge:
            self.merge.update_source(self.history, manuscript_digest=fingerprint)
        self.path = path
        self.candidate = None

    def refresh(self):
        self.guard()
        if not self.materialized:
            raise ContractError('Inspect the branch preview and continue to its candidate first.')
        if not self.path:
            raise ContractError('s chooses a read-only manuscript file before exact merge review.')
        try:
            fingerprint = hashlib.sha256(read_source(self.path)).hexdigest()
        except (OSError, ValueError):
            self.clear()
            raise
        if self.merge:
            self.merge.update_source(self.history, manuscript_digest=fingerprint)
        else:
            self.merge = PaperMergeSession(self.history, episode_id=self.episode,
                                            manuscript_digest=fingerprint, clock=self.clock)
        if not self.merge.get_review():
            self.candidate = None

    def prepare_merge(self):
        self.refresh()
        prepared = self.merge.prepare(sorted(self.selected))
        self.candidate = None
        return prepared

    def preview(self):
        self.guard()
        return self.merge.get_preview() if self.merge else None

    def review(self):
        self.guard()
        value = self.merge.get_review() if self.merge else None
        if not value:
            self.candidate = None
        return value

    def finish(self, preview_digest, disposition, answers):
        self.refresh()
        self.candidate = None
        return self.merge.finish(preview_digest, disposition=disposition, answers=answers)

    def build_candidate(self, review_digest):
        self.refresh()
        self.candidate = self.merge.candidate(review_digest)
        return self.candidate


class TerminalBranches:
    def __init__(self, app, *, clock=None):
        self.app, self.clock = app, clock
        self.flows = {}

    def active(self):
        if not self.app.series or self.app.service.episodes()['active_episode_id'] != self.app.episode_id:
            raise ContractError('Choose an active episode. Try demo tui --merge-example for the synthetic rehearsal.')

    def open_recorded(self):
        self.active()
        key = ('recorded', self.app.episode_id)
        previous = self.flows.get(key)
        if previous is None or previous.origin != self.app.paper.history:
            flow = BranchFlow(self.app, clock=self.clock)
            flow.owner_key = key
            flow.restore_inputs(previous)
            self.flows[key] = flow
        return self.flows[key]

    def prepare_branch(self):
        self.active()
        if 'alternative' in dict(self.app.paper.history.heads) and self.app.ref != 'alternative':
            raise ContractError('b opens the alternative. Write/edit the draft there before making its candidate.')
        work = self.app.review
        request = work.changes_request()
        session = work.session()
        try:
            preview = session.prepare_branch(request)
        except ContractError as error:
            if str(error) == 'reasoning and judgment text must agree':
                raise ContractError('c selects this episode interpretation; J stages your judgment there. Then C previews the branch.') from error
            raise
        flow = BranchFlow(self.app, branch_session=session, branch_preview=preview, clock=self.clock)
        key = ('draft', *work.key)
        flow.owner_key = key
        flow.restore_inputs(self.flows.get(key))
        self.flows[key] = flow
        return flow

    def volatile_work(self):
        return any(flow.branch or flow.merge or flow.selected or any(any(v) for v in flow.buffers.values())
                   for flow in self.flows.values())
