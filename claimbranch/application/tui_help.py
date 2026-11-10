"""Short contextual bindings plus the complete, separately chosen help topics."""
from .tui_model import wrap, clip

# Shared with dispatch: labels don't invent an alternate set of read shortcuts.
READ_VIEWS = {'d': ('Read record', 'detail'), 'i': ('What if', 'impact'),
              'm': ('Writing', 'writing'), 'p': ('Contributions', 'provenance')}
ENTRY_VIEWS = {'1': 'argument', '2': 'evidence'}


def topics(app):
    from .tui import HELP
    from .tui_retention import personal
    if not personal(app): return HELP
    return [('PERSONAL WRITING',
        'Kept and unfinished writing is checkpointed in this private directory. '
        'q saves before leaving; project open resumes it. Local files have no '
        'application encryption. Saving does not authorize scientific changes '
        'or write the manuscript. Reviews remain session-only.')] + HELP


def bindings(app):
    graph = app.focus == 'outline'
    return [
        ('↑ ↓ ← →' if graph else '↑ ↓', 'Move between nodes' if graph else 'Read / choose a connection'),
        ('Enter' if graph or app.reading_relation else 'Home End', 'Expand branch / read' if graph else 'Follow connection' if app.reading_relation else 'First / last page'),
        ('Space' if graph else 'PgUp PgDn', 'Fold / unfold branch' if graph else 'Page through content'),
        ('1 / 2', 'Argument / experiments; 2 choose'),
        ('d', READ_VIEWS['d'][0]),
        ('r', 'Inspect typed connections'),
        (';', 'All actions and availability'),
        ('n / e', 'Write note / judgment'),
        ('/', 'Find a node'),
        ('f', 'Fit current graph'),
        (',', 'Spacing, cards, mouse / copy'),
        ('Tab', 'Change focused pane'),
        ('Esc', 'Return to previous view'),
        ('q', 'Save and quit' if app.recovery else 'Leave session'),
    ]


class HelpUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.page, self.index, self.scroll = 'keys', 0, 0

    def open(self):
        self.page, self.index, self.scroll = 'keys', 0, 0
        self.terminal.modal = 'help'

    def key(self, event):
        HELP = topics(self.terminal.app)
        if event in ('?', 'q'):
            self.terminal.modal = None
        elif event == ';':
            self.terminal.modal = None
            self.terminal.key(';')
        elif event == 'escape':
            if self.page == 'topic': self.page, self.scroll = 'topics', 0
            elif self.page == 'topics': self.page = 'keys'
            else: self.terminal.modal = None
        elif event == 'tab':
            self.page, self.scroll = ('topics' if self.page == 'keys' else 'keys'), 0
        elif event == 'enter':
            if self.page == 'topics': self.page, self.scroll = 'topic', 0
            elif self.page == 'keys': self.terminal.modal = None
        elif event in ('up', 'down', 'page-up', 'page-down', 'home', 'end'):
            amount = {'up': -1, 'down': 1, 'page-up': -8, 'page-down': 8}.get(event, 0)
            if self.page == 'topics':
                self.index = (0 if event == 'home' else len(HELP) - 1 if event == 'end'
                              else max(0, min(len(HELP) - 1, self.index + amount)))
            elif self.page == 'topic':
                self.scroll = 0 if event == 'home' else 100000 if event == 'end' else max(0, self.scroll + amount)

    def wheel(self, dy):
        if self.page != 'keys': self.key('down' if dy > 0 else 'up')

    def draw(self, frame):
        HELP = topics(self.terminal.app)
        from .tui_retention import recovery_copy
        w, h = max(10, frame.width - 4), max(6, frame.height - 2)
        x, y = 2, 1
        if frame.width < 48 or frame.height < 21:
            page = 'KEYS' if self.page == 'keys' else 'HELP TOPICS'
            frame.put(1, 1, '? ' + page + ' · enlarge to 48 × 21', 'heading', frame.width - 2)
            frame.put(3, 1, 'Esc back · ; all actions', 'accent', frame.width - 2)
            return frame
        frame.box(x, y, w, h, 'KEYS' if self.page == 'keys' else 'HELP TOPICS', True)
        room = h - 5
        if self.page == 'keys':
            rows = bindings(self.terminal.app)
            columns = 2 if w >= 104 else 1
            per_column = (len(rows) + columns - 1) // columns
            for i, (key, action) in enumerate(rows):
                column, row = divmod(i, per_column)
                if row >= room: break
                cell = (w - 4) // columns
                left = x + 2 + column * cell
                frame.put(y + 2 + row, left, key, 'accent', 13)
                frame.put(y + 2 + row, left + 14, action, 'body', cell - 15)
            frame.put(y + h - 2, x + 2, 'Tab topics · ; all actions · Esc / ? close', 'muted', w - 4)
        elif self.page == 'topics':
            offset = max(0, self.index - room + 1)
            for row, (title, _) in enumerate(HELP[offset:offset + room]):
                frame.put(y + 2 + row, x + 2, ('› ' if offset + row == self.index else '  ') + title,
                          'selected' if offset + row == self.index else 'body', w - 4)
            frame.put(y + h - 2, x + 2, '↑↓ choose · Enter read · Tab keys · Esc back', 'muted', w - 4)
        else:
            title, text = HELP[self.index]
            lines = wrap(recovery_copy(self.terminal.app, text), w - 6)
            self.scroll = min(self.scroll, max(0, len(lines) - room + 1))
            frame.put(y + 1, x + 2, clip(title, w - 4), 'heading', w - 4)
            for row, text in enumerate(lines[self.scroll:self.scroll + room - 1]):
                frame.put(y + 3 + row, x + 3, text, 'body', w - 6)
            frame.put(y + h - 2, x + 2, '↑↓ / PgUp PgDn read · Esc topics · ? close', 'muted', w - 4)
        return frame


def help_ui(terminal):
    if not hasattr(terminal, '_help_ui'): terminal._help_ui = HelpUI(terminal)
    return terminal._help_ui
