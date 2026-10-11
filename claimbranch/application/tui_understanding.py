"""Conditional explanation work; optional encrypted retention grants no closure."""
from claimbranch.core.canonical import ContractError, decode
from .paper_understanding import PaperUnderstandingSession


class TerminalUnderstanding:
    def __init__(self, app):
        self.app = app
        self.sessions, self.sources, self.buffers, self.positions = {}, {}, {}, {}
        self.work_id = None

    def open(self, work_id):
        if work_id not in self.sessions:
            if len(self.sessions) >= 16:
                raise ContractError('Explanation session limit reached; existing writing is retained.')
            session = PaperUnderstandingSession(self.app.paper.history,
                project_id=self.app.service.pending_work()['project_id'], work_id=work_id)
            self.sessions[work_id] = session
            self.sources[work_id] = self.app.paper.history
        session = self.sessions[work_id]
        if self.sources[work_id] is not self.app.paper.history:
            session.update_source(self.app.paper.history)
            self.sources[work_id] = self.app.paper.history
        self.work_id = work_id
        return session

    @property
    def session(self):
        return self.sessions[self.work_id]

    def refresh(self):
        return self.open(self.work_id).state()

    def volatile_work(self):
        return any(self.has_writing(key) for key in self.sessions)

    def has_writing(self, work_id):
        session = self.sessions.get(work_id)
        return any(key[0] == work_id for key in self.buffers) or bool(session and any(
            entry['text'] or entry['reuse_rationale'] for entry in decode(session.snapshot())['entries']))
