"""Reversible, session-only presentation settings over the current graph."""
from .tui_model import wrap


OPTIONS = (
    ('graph_spacing', 'Node spacing', ('balanced', 'spacious'), ('Balanced', 'Spacious'),
     'Keep vertical arrows readable; Spacious adds more room.'),
    ('density', 'Card detail', ('compact', 'comfortable'), ('Brief', 'Source'),
     'Brief keeps small cards; Source shows longer excerpts.'),
    ('graph_pinned', 'Reading panel', (False, True), ('On demand', 'Pinned'),
     'Pinned stays beside the graph at 140+ columns.'),
)


class ViewUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = 0

    @property
    def app(self):
        return self.terminal.app

    def open(self):
        self.before = self.app._navigation()
        self.preferences = self.app.graph_spacing, self.app.graph_pinned
        self.index = 0
        self.usable = True
        self.terminal.modal = 'view-settings'

    def key(self, event):
        if event == 'escape':
            self.app._restore_navigation(self.before)
            self.app.graph_spacing, self.app.graph_pinned = self.preferences
            self.terminal.modal = None
            self.app.message = 'View settings cancelled; previous view restored.'
        elif not self.usable:
            return
        elif event == 'enter':
            self.terminal.modal = None
            self.app.message = 'View settings kept for this session. , opens settings.'
        elif event in ('up', 'down', 'k', 'j', 'tab', 'backtab'):
            self.index = (self.index + (-1 if event in ('up', 'k', 'backtab') else 1)) % len(OPTIONS)
        elif event in ('left', 'right', ' '):
            field, _, values, _, _ = OPTIONS[self.index]
            current = values.index(getattr(self.app, field))
            setattr(self.app, field, values[(current + (-1 if event == 'left' else 1)) % len(values)])
            if field == 'graph_pinned':
                self.app.graph_fullscreen = self.before['graph_fullscreen'] if self.app.graph_pinned == self.preferences[1] else False
            self.app.graph_follow = True
        elif event == 'r':
            self.app.graph_spacing, self.app.density, self.app.graph_pinned = 'balanced', 'compact', False
            self.app.graph_fullscreen = self.before['graph_fullscreen'] if not self.preferences[1] else False
            self.app.graph_follow = True

    def draw(self, frame):
        self.usable = frame.width >= 48 and frame.height >= 18
        if not self.usable:
            frame.put(2, 0, 'VIEW SETTINGS · resize to 48 × 18', 'top_accent', frame.width)
            frame.put(3, 0, 'Esc cancel · controls paused', 'top_muted', frame.width)
            return frame
        w, h = min(frame.width - 2, 66), min(frame.height - 2, 20)
        x, y = (frame.width - w) // 2, (frame.height - h) // 2
        frame.box(x, y, w, h, 'VIEW SETTINGS', True)
        frame.put(y + 2, x + 2, 'Live preview · session only', 'muted', w - 4)
        for index, (field, label, values, names, description) in enumerate(OPTIONS):
            row = y + 4 + index * 3
            chosen = index == self.index
            frame.put(row, x + 2, ('› ' if chosen else '  ') + label + ' · ' + names[values.index(getattr(self.app, field))],
                      'selected_meta' if chosen else 'heading', w - 4)
            for line, text in enumerate(wrap(description, w - 8)[:2]):
                frame.put(row + 1 + line, x + 4, text, 'body', w - 8)
        frame.put(y + h - 3, x + 2, '↑↓ choose · ←→ / Space change · r defaults', 'accent', w - 4)
        frame.put(y + h - 2, x + 2, 'Enter keep · Esc cancel', 'accent', w - 4)
        return frame


def view_ui(terminal):
    if not hasattr(terminal, '_view_ui'):
        terminal._view_ui = ViewUI(terminal)
    return terminal._view_ui
