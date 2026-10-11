"""Contextual writing, with a read-only source peek over the same edit buffers."""
from .tui_retention import recovery_copy
from .tui_subject import subject_lines, subject_summary
from .tui_model import cell_width


def editor_geometry(width, height):
    if width >= 120:
        source_width = min(58, width * 2 // 5)
        return source_width + 3, 3, width - source_width - 5, height - 6
    return 1, 9, width - 2, height - 12


class JudgmentUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.buffers = terminal.buffers
        self.expanded = False
        self.scroll = 0

    def key(self, event):
        """Consume source controls only; ordinary editor input stays with Terminal."""
        height, width = self.terminal.screen.getmaxyx()
        if width < 48 or height < 18:
            if event == 'escape':
                self.expanded = False
                return False
            return True
        if event == 'source' or (self.expanded and event == 'escape'):
            self.expanded = not self.expanded
            return True
        if not self.expanded:
            return False
        count = max(1, height - 7)
        limit = max(0, len(subject_lines(self.terminal.app, width - 6)) - count)
        movement = {'up': -1, 'k': -1, 'down': 1, 'j': 1,
                    'page-up': -count, 'page-down': count, 'home': -limit, 'end': limit}
        self.scroll = min(limit, max(0, self.scroll + movement.get(event, 0)))
        return True  # Reading cannot keep, cancel, paste into or otherwise edit a draft.

    def draw(self, frame):
        from .tui import Frame
        terminal, app = self.terminal, self.terminal.app
        width, height = frame.width, frame.height
        frame = Frame(width, height)
        warning = getattr(app, 'recovery_error', None)
        if width < 48 or height < 18:
            frame.put(1, 1, 'Writing controls paused', 'top_warning', width - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Text is retained.', 'top_muted', width - 2)
            frame.put(5, 1, warning or 'Esc retains writing and returns.', 'top_warning' if warning else 'top_muted', width - 2)
            return frame
        from .tui_work_recovery import enabled
        state = ('judgment + AI origin recovery' if enabled(app) else
                 'AI-influenced · session only' if app.review.influenced() else
                 'private draft recovery' if app.recovery else 'session draft')
        context = ('SYNTHETIC / current global evidence · ' + app.view['episode']['status']
                   + ' episode / ' + app.episode_id + ' / ' + app.ref if app.series
                   else 'SYNTHETIC / ' + app.ref)
        frame.put(1, 2, recovery_copy(app, context), 'top_muted', width - 4)
        frame.put(2, 2, ('HYPOTHETICAL ' + app.node_label(app.scenario['assumption']['plan_id'])
                        + ' ' + app.scenario['assumption']['outcome'] + ' · recorded source shown')
                  if app.scenario else ('Esc / Ctrl+O returns to draft' if self.expanded else 'Ctrl+O full source · Esc returns'),
                  'top_warning' if app.scenario else 'top_muted', width - 4)
        if not app.scenario and not self.expanded and len(app.paper.work_nodes(app.full_context(app.work_key()))) > 1:
            frame.put(2, 2, 'Linked: ' + app.work_labels() + (recovery_copy(app, ' · encrypted links') if enabled(app) else ' · session-only links'), 'top_accent', width - 4)
        if self.expanded:
            frame.put(0, 2, 'SOURCE / ' + app.node_label(app.selected_id) + ' · judgment ' + app.node_label(app.work_key()[-1]) + ' · ' + state, 'brand', width - 4)
            for row in range(3, height - 2):
                frame.fill(row, 1, width - 2, 'body')
            rows = subject_lines(app, width - 6)
            count = height - 7
            self.scroll = min(self.scroll, max(0, len(rows) - count))
            for i, (text, style) in enumerate(rows[self.scroll:self.scroll + count]):
                frame.put(4 + i, 3, text, style, width - 6)
            frame.put(height - 2, 2, 'Esc / Ctrl+O return to draft · PgUp/PgDn read', 'top_accent', width - 4)
            frame.put(height - 1, 2, warning or f'{self.scroll + 1}–{min(len(rows), self.scroll + count)} / {len(rows)} · Read only; your draft is retained.', 'top_warning' if warning else 'top_muted', width - 4)
            return frame
        title = 'YOUR JUDGMENT / ' + app.node_label(app.work_key()[-1]) + ' · ' + state
        if cell_width(title) > width - 4:
            title = title.removeprefix('YOUR ')
        frame.put(0, 2, title, 'brand', width - 4)
        x, y, w, available = editor_geometry(width, height)
        if width >= 120:
            for row in range(3, height - 3):
                frame.fill(row, 1, x - 3, 'body')
            rows = subject_lines(app, x - 7)
            count = height - 7
            for i, (text, style) in enumerate(rows[:count]):
                frame.put(3 + i, 3, text, style, x - 7)
            if len(rows) > count:
                frame.put(height - 4, 3, 'More context · Ctrl+O', 'accent', x - 7)
        else:
            for row in range(3, 9):
                frame.fill(row, 1, width - 2, 'body')
            for i, (text, style) in enumerate(subject_summary(app, width - 6)):
                frame.put(3 + i, 3, text, style, width - 6)
        upper = available // 2
        for index, (top, h, label) in enumerate(((y, upper, 'JUDGMENT'), (y + upper, available - upper, 'WHY / EVIDENCE'))):
            frame.box(x, top, w, h, label, terminal.field == index)
            buffer = terminal.buffers[index]
            lines, row, column = buffer.position(w - 4)
            offset = max(0, row - h + 3)
            for n, (text, _, _) in enumerate(lines[offset:offset + h - 2]):
                frame.put(top + 1 + n, x + 2, text, 'body', w - 4)
            if terminal.field == index:
                frame.cursor = (top + 1 + row - offset, min(x + w - 2, x + 2 + column))
        frame.put(height - 2, 2, 'Tab field · Ctrl+S keep · Ctrl+O source · Enter new line', 'top_accent', width - 4)
        buffer = terminal.buffers[terminal.field]
        notice = ('Draft save failed · ' + buffer.notice) if warning and buffer.notice else warning or buffer.notice
        frame.put(height - 1, 2, notice or f'{len(buffer.text):,}/12,000 · Ctrl+_ undo · Ctrl+Y redo · Esc retains unfinished text', 'top_warning' if warning else 'top_muted', width - 4)
        return frame


def judgment_ui(terminal):
    ui = getattr(terminal, '_judgment_ui', None)
    if ui is None or ui.buffers is not terminal.buffers:
        terminal._judgment_ui = ui = JudgmentUI(terminal)
    return ui
