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


class GraphBrowseUI:
    """Read-only chooser/inspector; opening and cancelling never change research."""
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = 0
        self.query = ''

    @property
    def app(self):
        return self.terminal.app

    def open(self, mode):
        self.mode, self.index, self.query = mode, 0, ''
        self.reading, self.scroll = False, 0
        self.root = self.app.selected_id
        self.terminal.modal = 'graph-browse'

    def items(self):
        from claimbranch.core.graph_vocabulary import EDGE_KINDS
        app = self.app
        if self.mode == 'roots':
            return [(key, app.title(key) + ' / ' + app.kind(key) + ' / ' + app.node_label(key))
                    for key in app.entry_ids()
                    if self.query.casefold() in (app.title(key) + ' ' + key).casefold()]
        if self.mode == 'legend':
            return [(None, key + ' / ' + item.label + ' / ' + item.definition)
                    for key, item in EDGE_KINDS.items()]
        inventory = app.fold_inventory(self.root)
        rows = [(None, f"{len(inventory['records'])} unique owned records; {inventory['reference_positions']} reference positions, not extra evidence.")]
        if app.scenario:
            reached = set(inventory['records']) & set(app.scenario['potentially_affected_claim_ids'])
            rows.append((None, f'{len(reached)} hidden claims potentially reached by the hypothetical outcome; not a truth judgment.'))
        for group in ('internal', 'boundary'):
            rows.append((None, group.upper() + ' EDGES / recorded direction relative to owned records'))
            rows += [(None, kind + ' ' + direction + ' / ' + str(count))
                     for (kind, direction), count in inventory[group].items()]
        rows.append((None, 'RECORD STATUS / separate from scientific edge types'))
        rows += [(None, status + ' / ' + str(len(keys))) for status, keys in inventory['statuses'].items()]
        for key in (self.root, *inventory['records']):
            node = app.nodes[key]; content = node['content']
            status = content.get('status', content.get('resolution', ''))
            origin = content.get('imported_source', {})
            unresolved = any(origin.get('unresolved_pointer_pages', []))
            rows.append((key, app.title(key) + ' / ' + app.kind(key) + ' / ' + app.node_label(key)
                         + (' / ' + status if status else '') + (' / unresolved source' if unresolved else '')))
        rows.append((None, 'RECORDED LINKS / Enter follows the exact edge; not inferred support'))
        owned = set(inventory['records']) | {self.root}
        for edge in app.view['relations']:
            if edge['source_id'] in owned or edge['target_id'] in owned:
                rows.append((edge, app.title(edge['source_id']) + ' --' + edge['type'] + '--> '
                             + app.title(edge['target_id']) + ' / ' + (edge.get('rationale') or 'No rationale recorded')))
        outside = app.view.get('reporting_dependencies_outside_view', [])
        if outside:
            rows.append((None, 'Reporting companions outside this view: ' + ', '.join(outside)))
        return rows

    def key(self, event):
        if event == 'escape':
            self.terminal.modal = None
            return
        h, w = self.terminal.screen.getmaxyx()
        if w < 48 or h < 18:
            return
        items = self.items()
        if event == 'tab':
            self.reading = not self.reading
            self.scroll = 0
            return
        if self.reading and event in ('up', 'down', 'home', 'end', 'page-up', 'page-down'):
            lines = wrap(items[self.index][1], max(2, w - 6)) if items else []
            self.scroll = (0 if event == 'home' else max(0, len(lines) - h + 8) if event == 'end'
                           else max(0, min(max(0, len(lines) - h + 8), self.scroll +
                                           {'up': -1, 'down': 1, 'page-up': -5, 'page-down': 5}[event])))
            return
        if event in ('up', 'down', 'home', 'end', 'page-up', 'page-down'):
            self.index = (0 if event == 'home' else max(0, len(items) - 1) if event == 'end'
                          else max(0, min(len(items) - 1, self.index +
                                          {'up': -1, 'down': 1, 'page-up': -5, 'page-down': 5}[event])))
        elif event == 'enter' and items:
            target = items[self.index][0]
            if target is None:
                return
            self.terminal.modal = None
            if self.mode == 'roots':
                self.app.switch_lens('evidence', evidence_id=target)
            elif isinstance(target, dict):
                self.app.select(target['source_id'])
                self.app.link_scope = 'all'
                index = next((i for i, link in enumerate(self.app.links()) if link.key == target['key']), None)
                if index is None:
                    self.app.message = 'Connection changed. Reopen the folded-record inspector; writing retained.'
                    return
                self.app.link_index = index
                self.app.reading_relation = True
                self.app.open_view()
            else:
                self.app.select(target)
        elif self.mode == 'roots' and not self.reading:
            if event == 'backspace':
                self.query = self.query[:-1]
            elif isinstance(event, tuple) and event[0] == 'paste':
                self.query = (self.query + event[1])[:256]
            elif isinstance(event, str) and len(event) == 1 and event.isprintable():
                self.query = (self.query + event)[:256]
            self.index = 0

    def draw(self, frame):
        from .tui_model import clip
        for row in range(frame.height):
            frame.fill(row, 0, frame.width, 'canvas')
        if frame.width < 48 or frame.height < 18:
            frame.put(0, 0, 'Graph inspection paused / enlarge to 48 x 18 / Esc returns', 'top_warning', frame.width)
            return frame
        measure = frame.width - 6
        title = {'roots': 'CHOOSE EXPERIMENT / OBSERVATION / UNRUN PLAN',
                 'legend': 'DEFINED EDGE TYPES / NO FREE-TEXT CATEGORIES',
                 'inventory': 'FOLDED RECORDS AND TYPED CONNECTIONS'}[self.mode]
        frame.put(0, 3, title, 'brand', measure)
        frame.put(2, 3, ('Search: ' + self.query if self.mode == 'roots' else self.app.title(self.root)), 'body', measure)
        items = self.items()
        if self.reading and items:
            lines = wrap(items[self.index][1], measure)
            self.scroll = min(self.scroll, max(0, len(lines) - frame.height + 8))
            for row, text in enumerate(lines[self.scroll:self.scroll + frame.height - 8]):
                frame.put(4 + row, 3, text, 'body', measure)
            frame.put(frame.height - 2, 3, 'Full text / arrows and pages read / Tab list / Esc returns', 'accent', measure)
            return frame
        visible = max(1, (frame.height - 8) // 2)
        self.index = min(self.index, max(0, len(items) - 1))
        offset = max(0, self.index - visible + 1)
        for row, (_, text) in enumerate(items[offset:offset + visible]):
            active = row + offset == self.index
            lines = wrap(text, measure - 2)
            for line, value in enumerate(lines[:2]):
                frame.put(4 + 2 * row + line, 3, ('› ' if active and line == 0 else '  ') + value,
                          'selected' if active else 'body', measure)
        # Tab reads the complete selected entry without changing selection.
        if not items:
            frame.put(5, 3, 'No matching records. No results are invented.', 'muted', measure)
        frame.put(frame.height - 3, 3, f'{self.index + 1 if items else 0}/{len(items)} / arrows choose / PgUp PgDn / Enter follows / Esc returns', 'accent', measure)
        frame.put(frame.height - 2, 3, 'Tab reads full text / titles precede IDs / original types and directions.', 'muted', measure)
        return frame


def graph_browse_ui(terminal):
    if not hasattr(terminal, '_graph_browse_ui'):
        terminal._graph_browse_ui = GraphBrowseUI(terminal)
    return terminal._graph_browse_ui
