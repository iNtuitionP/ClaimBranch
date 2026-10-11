"""Session-only manuscript work; file access is bounded and strictly read-only."""
import hashlib
import os
from pathlib import Path
import stat

from claimbranch.core.canonical import ContractError
from .paper_manuscript import PaperManuscriptSession
from .paper_service import PaperService


def read_source(path):
    descriptor = os.open(Path(path).expanduser(), os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ContractError('Choose a regular UTF-8 manuscript file.')
        value = b''
        while len(value) < 65537:
            chunk = os.read(descriptor, 65537 - len(value))
            if not chunk:
                break
            value += chunk
    finally:
        os.close(descriptor)
    if not value or len(value) > 65536:
        raise ContractError('Manuscript source must be nonempty and at most 64 KiB.')
    try:
        value.decode('utf-8')
    except UnicodeError as error:
        raise ContractError('Manuscript source must be UTF-8.') from error
    return value


class TerminalManuscript:
    def __init__(self, app, *, clock=None):
        self.app, self.clock = app, clock
        self.sessions, self.paths, self.buffers = {}, {}, {}
        self.parents = {}
        self.positions, self.restored = {}, {}
        self.work_id = None

    def open(self, work_id):
        if work_id not in self.sessions:
            session = PaperManuscriptSession(self.app.paper.history, work_id=work_id, clock=self.clock)
            self.make_room(candidate=False)
            self.sessions[work_id] = session
        self.work_id = work_id
        return self.session

    @property
    def session(self):
        return self.sessions[self.work_id]

    def candidate_items(self, flow):
        return [key for key, binding in self.parents.items() if binding['owner'] == flow.owner_key]

    def make_room(self, *, candidate):
        # Candidate exploration cannot consume W's recorded-work capacity.
        keys = [key for key in self.sessions if (key in self.parents) == candidate]
        if len(keys) < 16:
            return
        if candidate:
            for key in keys:
                draft = self.sessions[key].state()['draft']['draft']
                if not (draft['text'] or draft['rationale'] or draft['contributions']
                        or any(owner == key for owner, _ in self.buffers)):
                    for values in (self.sessions, self.parents, self.paths):
                        values.pop(key, None)
                    return
        raise ContractError('Manuscript draft limit reached; all existing writing is retained.')

    def open_candidate(self, flow):
        if flow.owner_key is None:
            raise ContractError('Choose the owning branch review first.')
        flow.refresh()
        review = flow.review()
        if not review:
            raise ContractError('Complete the current selected merge review first; earlier wording remains available below.')
        key = 'candidate-' + review['digest']
        if key in self.sessions:
            self.work_id = key
            return self.session
        prepared = flow.preview()
        if not prepared or prepared['digest'] != review['preview_digest']:
            raise ContractError('Scientific review expired; prepare and inspect it again.')
        history, _ = flow.build_candidate(review['digest'])
        item = next(item for item in PaperService(history).pending_work()['items']
                    if item['kind'] == 'manuscript' and item['cause_operation_id'] == review['command']['id'])
        source = read_source(flow.path)
        expected = prepared['manuscript']['digest']
        if hashlib.sha256(source).hexdigest() != expected:
            raise ContractError('Source changed; re-review the selected merge before wording.')
        session = PaperManuscriptSession(history, work_id=item['id'], source=source, clock=self.clock)
        current = flow.review()
        if not current or current['digest'] != review['digest']:
            raise ContractError('Scientific review expired; earlier wording is retained. Prepare a new review.')
        self.make_room(candidate=True)
        self.sessions[key] = session
        self.paths[key] = flow.path
        self.parents[key] = {'flow': flow, 'owner': flow.owner_key, 'review_digest': review['digest'],
                             'source_digest': expected, 'history': history, 'science': prepared['preview']}
        self.work_id = key
        return session

    def check_parent(self, *, refresh=False):
        binding = self.parents.get(self.work_id)
        if binding:
            try:
                flow = binding['flow']
                if flow is None:
                    raise ContractError('Restored earlier scientific review. Keep editing here; prepare new science for a separate wording review.')
                if refresh:
                    flow.refresh()
                review = flow.review()
                if (not review or review['digest'] != binding['review_digest']
                        or sorted(flow.selected) != review['command']['payload']['selected_ids']):
                    raise ContractError('Scientific review changed or expired. Earlier wording is retained; m from merge opens its drafts.')
            except (OSError, ValueError):
                self.session.not_now()
                raise

    def source_history(self, source):
        binding = self.parents.get(self.work_id)
        if binding:
            self.check_parent(refresh=True)
            if source is None or hashlib.sha256(source).hexdigest() != binding['source_digest']:
                self.session.not_now()
                raise ContractError('Source differs from the selected merge review. Re-review science before this wording.')
            return binding['history']
        return self.app.paper.history

    def load_source(self, path):
        if self.work_id in self.parents and self.parents[self.work_id]['flow'] is None:
            self.check_parent()
        path = str(Path(path).expanduser().absolute())
        source = read_source(path)
        self.check_restored_source(source)
        self.session.update_source(self.source_history(source), source=source)
        self.paths[self.work_id] = path

    def refresh(self):
        if self.work_id in self.parents and self.parents[self.work_id]['flow'] is None:
            self.check_parent()
        path = self.paths.get(self.work_id)
        try:
            source = read_source(path) if path else None
            self.check_restored_source(source)
            history = self.source_history(source)
        except (OSError, ValueError):
            self.session.not_now()
            raise
        self.session.update_source(history, source=source)

    def check_restored_source(self, source):
        if self.work_id not in self.restored:
            return
        original = self.restored[self.work_id]
        if ((original is not None and (source is None or hashlib.sha256(source).hexdigest() != original))
                or (self.work_id not in self.parents and self.session._history != self.app.paper.history)):
            self.session.not_now()
            raise ContractError('Source or science differs from this restored draft. Original writing is retained; choose the matching source before review.')

    def prepare(self):
        self.refresh()
        return self.session.prepare()

    def finish(self, preview_digest, disposition, answers):
        self.refresh()
        return self.session.finish(preview_digest, disposition=disposition, answers=answers)

    def volatile_work(self):
        return bool(self.buffers) or any(
            state['draft']['draft']['text'] or state['draft']['draft']['rationale'] or state['preview_digest']
            for session in self.sessions.values() for state in (session.state(),))
