from .tui_retention import recovery_copy
from .tui_work_recovery import enabled
"""Explicit judgment reuse; working references never become scientific edges."""
from claimbranch.core.canonical import ContractError
from .tui_model import wrap


class WorkLinksUI:
    def __init__(self, terminal):
        self.terminal = terminal

    @property
    def app(self):
        return self.terminal.app

    def enter(self, action):
        app = self.app
        self.target = app.context_key()
        self.history, self.revision = app.paper.history, app.paper.work_revision
        self.index, self.scroll, self.notice = 0, 0, ''
        self.action = action
        self.current = app.review.key
        if action == 'edit':
            app.review.session()
            self.owner = self.current
            self.items = list(app.nodes)
            self.selected = set(app.paper.work_nodes(app.full_context(self.owner)))
            self.terminal.modal = 'work-links-nodes'
        else:
            keys = {self.target, *app.review.sessions, *app.drafts, *app.review.buffers}
            self.items = sorted(key for key in keys if app.full_context(key)[:2] == (app.episode_id, app.ref))
            self.index = self.items.index(self.current) if self.current in self.items else 0
            self.terminal.modal = 'work-links-choose'

    def draft(self, key):
        app = self.app
        if key in app.review.buffers:
            return app.review.buffers[key]
        session = app.review.sessions.get(key)
        return session.state()['draft'] if session else app.drafts.get(key, {'text': '', 'rationale': ''})

    def owner_label(self, key):
        return 'Judgment ' + self.app.node_label(key[-1])

    def ensure_current(self):
        if (self.target != self.app.context_key() or self.history is not self.app.paper.history
                or self.revision != self.app.paper.work_revision):
            raise ContractError('Context or links changed. Esc returns; reopen the action. Existing writing is retained.')

    def activating(self):
        if self.action == 'choose':
            return {self.target[-1]}
        return self.selected - set(self.app.paper.work_nodes(self.app.full_context(self.owner)))

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, ValueError) as error:
            self.notice = str(error)

    def key(self, event):
        mode = self.terminal.modal
        if event == 'escape':
            self.terminal.modal = ('work-links-nodes' if self.action == 'edit' else 'work-links-choose') if mode == 'work-links-confirm' else None
            self.notice, self.scroll = '', 0
            return
        h, w = self.terminal.screen.getmaxyx()
        if w < 48 or h < 18:
            return
        self.ensure_current()
        if event in ('up', 'down', 'j', 'k', 'page-up', 'page-down', 'home', 'end'):
            step = {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -5, 'page-down': 5}.get(event, 0)
            if mode == 'work-links-confirm':
                limit = max(0, len(self.confirm_lines(w - 6)) - (h - 10))
                self.scroll = 0 if event == 'home' else limit if event == 'end' else min(limit, max(0, self.scroll + step))
            else:
                self.index = 0 if event == 'home' else len(self.items) - 1 if event == 'end' else min(len(self.items) - 1, max(0, self.index + step))
            self.notice = ''
        elif mode == 'work-links-nodes' and event == ' ':
            key = self.items[self.index]
            if key == self.owner[-1]:
                self.notice = 'The original owner stays linked; its judgment identity does not move.'
            elif key in self.selected:
                self.selected.remove(key)
            elif len(self.selected) < 16:
                self.selected.add(key)
            else:
                self.notice = 'A judgment links to at most 16 source nodes.'
        elif event == 'enter':
            if mode == 'work-links-choose':
                self.owner = self.items[self.index]
                self.selected = set(self.app.paper.work_nodes(self.app.full_context(self.owner))) | {self.target[-1]}
                if len(self.selected) > 16:
                    self.notice = self.owner_label(self.owner) + ' already links 16 nodes; unlink one first.'
                    return
                self.scroll, self.terminal.modal = 0, 'work-links-confirm'
            elif mode == 'work-links-nodes':
                self.scroll, self.terminal.modal = 0, 'work-links-confirm'
            else:
                self.app.paper.link_work(self.app.full_context(self.owner), sorted(self.selected),
                    activate_ids=sorted(self.activating()),
                    expected_history=self.history, expected_revision=self.revision)
                self.app.open_view(mode='work')
                self.app.message = self.owner_label(self.app.review.key) + ' selected. Other judgments and node notes stay separate.'
                self.terminal.modal = None

    def confirm_lines(self, width):
        draft = self.draft(self.owner)
        lines = [self.owner_label(self.owner) + ' / original owner ' + self.app.title(self.owner[-1]),
                 'AI-influenced judgment; contribution history stays attached.' if self.app.review.influenced(self.owner) else 'Manual judgment draft.',
                 'Judgment: ' + (draft['text'] or '(not written yet)'),
                 'Reason: ' + (draft['rationale'] or '(not written yet)'),
                 'Linked nodes / judgment choice after applying:']
        active = self.activating()
        for key in sorted(self.selected):
            old = self.app.paper.work_owner(self.app.episode_id, self.app.ref, key)
            different = old != self.app.full_context(self.owner)
            lines.append(self.app.node_label(key) + (' / keeps its different judgment' if different and key not in active else ' / uses this judgment')
                         + ' / ' + self.app.title(key))
            if different and key in active:
                lines.append('Previous judgment ' + self.app.node_label(old[-1]) + ' stays separate; choose it again from actions.')
        if self.action == 'edit':
            removed = set(self.app.paper.work_nodes(self.app.full_context(self.owner))) - self.selected
            for key in sorted(removed):
                lines.append('Unlink ' + self.app.node_label(key) + '; its own judgment remains available.')
        lines += ['Linking creates no scientific edge or accepted change. Changed membership invalidates this judgment\'s change reviews.',
                  (recovery_copy(self.app, 'Encrypted checkpoints include links, choices and adopted AI contributions.') if enabled(self.app) else 'Links and choices last for this session. Manual checkpoints retain text at its original owner; AI work is not checkpointed.')]
        return [line for text in lines for line in wrap(text, width)]

    def draw(self, frame):
        from .tui import Frame
        frame = Frame(frame.width, frame.height)
        w, h = frame.width, frame.height
        if w < 48 or h < 18:
            frame.put(1, 1, 'Judgment links paused', 'top_warning', w - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Esc returns.', 'top_muted', w - 2)
            return frame
        mode = self.terminal.modal
        x, measure = 3, w - 6
        frame.put(0, x, {'work-links-nodes': 'LINK THIS JUDGMENT TO NODES',
                          'work-links-choose': 'CHOOSE A JUDGMENT FOR THIS NODE',
                          'work-links-confirm': 'REVIEW JUDGMENT LINKS'}[mode], 'brand', measure)
        frame.put(1, x, (recovery_copy(self.app, 'ENCRYPTED LINKS / no scientific edges or acceptance') if enabled(self.app) else 'SESSION ONLY / no scientific edges or acceptance'), 'top_warning', measure)
        frame.put(2, x, 'Viewing ' + self.app.node_label(self.target[-1]) + ' / ' + self.app.episode_id + ' / ' + self.app.ref, 'top_muted', measure)
        if mode == 'work-links-confirm':
            rows = self.confirm_lines(measure)
            count = h - 10
            self.scroll = min(self.scroll, max(0, len(rows) - count))
            for i, text in enumerate(rows[self.scroll:self.scroll + count]):
                frame.put(4 + i, x, text, 'body', measure)
            footer = 'Enter use displayed links · Esc back · PgUp/PgDn read'
            detail = f'{self.scroll + 1}–{min(len(rows), self.scroll + count)} / {len(rows)} · Other judgments remain separate.'
        else:
            visible = max(1, (h - 10) // 3)
            offset = max(0, self.index - visible + 1)
            for i, key in enumerate(self.items[offset:offset + visible]):
                active = i + offset == self.index
                if mode == 'work-links-nodes':
                    title = ('[x] ' if key in self.selected else '[ ] ') + self.app.node_label(key) + (' / OWNER' if key == self.owner[-1] else '')
                    text = self.app.title(key)
                else:
                    title = self.owner_label(key) + (' / this node\'s separate judgment' if key == self.target else '')
                    title += ' / AI-INFLUENCED' if self.app.review.influenced(key) else ''
                    text = self.draft(key)['text'] or 'No judgment written yet.'
                y = 4 + 3 * i
                frame.fill(y, x, measure, 'selected' if active else 'body')
                frame.put(y, x, ('› ' if active else '  ') + title, 'selected_meta' if active else 'heading', measure)
                for n, line in enumerate(wrap(text, measure - 3)[:2]):
                    frame.put(y + 1 + n, x + 3, line, 'body', measure - 3)
            footer = 'Space link/unlink · Enter preview · Esc cancel' if mode == 'work-links-nodes' else 'Enter preview judgment · Esc cancel'
            detail = ((self.owner_label(self.owner) + f' · {len(self.selected)}/16 linked · ') if mode == 'work-links-nodes' else '') + f'{self.index + 1}/{len(self.items)} · ↑↓ choose'
        if self.notice:
            for i, line in enumerate(wrap(self.notice, measure)[:2]):
                frame.fill(h - 6 + i, x, measure, 'canvas')
                frame.put(h - 6 + i, x, line, 'top_warning', measure)
        for i, line in enumerate(wrap(footer, measure)[:2]):
            frame.put(h - 4 + i, x, line, 'top_accent', measure)
        for i, line in enumerate(wrap(detail, measure)[:2]):
            frame.put(h - 2 + i, x, line, 'top_muted', measure)
        return frame


def work_links_ui(terminal):
    if not hasattr(terminal, '_work_links_ui'):
        terminal._work_links_ui = WorkLinksUI(terminal)
    return terminal._work_links_ui
