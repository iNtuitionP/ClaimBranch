"""Incremental, unconfirmed result capture beside the original subject."""
from .tui_retention import recovery_copy, personal
from .tui_work_recovery import enabled as encrypted_writing
from claimbranch.core.canonical import ContractError
from .paper_intake import FIELDS
from .tui_model import wrap


def field_label(app, field):
    return 'Run reference / method (how produced)' if personal(app) and field=='run_ref' else FIELDS[field]


def subject(item, view=None):
    view = item['source'] if view is None else view
    node = next((node for node in view['nodes'] if node['id'] == item['owner'][2]), None)
    if node is None:
        return 'Original subject unavailable.'
    content = node['content']
    return (content.get('statement') or content.get('objective') or content.get('question')
            or 'Manuscript connection')


class IntakeUI:
    fields = tuple(FIELDS)

    def __init__(self, terminal):
        self.terminal = terminal
        self.index = self.scroll = 0
        self.list_index = 0
        self.notice = ''
        self.entry_id = None
        self.expanded = False
        self.basis = False

    @property
    def service(self):
        return self.terminal.app.intake

    def open(self, mode):
        if mode == 'list':
            keys = [item['id'] for item in self.service.items()]
            self.index = (keys.index(self.entry_id) if self.entry_id in keys else
                          min(self.list_index, max(0, len(keys) - 1)))
            self.list_index = self.index
        self.terminal.modal = 'intake-' + mode
        self.scroll = 0
        self.notice = ''

    def enter(self, action):
        self.index = 0
        if action == 'new':
            app = self.terminal.app
            self.entry_id = self.service.create((app.episode_id, app.ref, app.selected_id))
            self.open('form')
        else:
            self.open('list')

    def dispatch(self, event):
        try:
            self.key(event)
        except ContractError as error:
            self.notice = str(error)

    def key(self, event):
        t = self.terminal
        mode = t.modal.removeprefix('intake-')
        if event == 'escape':
            if mode == 'text':
                if self.expanded:
                    self.expanded = False
                    return
                buffer = t.buffers[0]
                if buffer.text != buffer.initial:
                    self.service.retain(self.entry_id, self.editing, buffer.text)
                self.open('form')
            elif mode == 'form':
                self.service.drop_empty(self.entry_id)
                self.index = 0
                self.open('list')
            elif mode in ('read', 'remove'):
                self.open('form' if mode == 'read' else 'list')
            else:
                t.modal = None
            return
        h, w = t.screen.getmaxyx()
        if w < 48 or h < 18:
            return
        if mode == 'text':
            if event == 'source':
                self.expanded = not self.expanded
                self.scroll = 0
                self.basis = False
            elif self.expanded:
                if event == 'tab':
                    self.basis = not self.basis
                    self.scroll = 0
                else:
                    self.scroll_key(event)
            elif event == 'keep':
                self.service.keep(self.entry_id, self.editing, t.buffers[0].text)
                self.open('form')
                self.notice = (recovery_copy(self.terminal.app, 'Kept; included in encrypted checkpoints. Still unconfirmed.') if encrypted_writing(t.app) else 'Kept in this session. Nothing confirmed or saved to disk.')
            else:
                self.notice = ''
                t.buffers[0].key(event, self.geometry(w, h)[2] - 4)
            return
        if mode == 'read':
            if event == 'tab':
                self.basis = not self.basis
                self.scroll = 0
            else:
                self.scroll_key(event)
            return
        if mode == 'remove':
            if event == 'enter':
                self.service.remove(self.entry_id)
                self.index = 0
                self.open('list')
            return
        items = self.service.items() if mode == 'list' else self.fields
        if event in ('up', 'k', 'down', 'j', 'home', 'end', 'page-up', 'page-down'):
            self.index = (0 if event == 'home' else max(0, len(items) - 1) if event == 'end' else
                          max(0, min(len(items) - 1, self.index + {
                              'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -5, 'page-down': 5}[event])))
            self.notice = ''
            if mode == 'list':
                self.list_index = self.index
        elif mode == 'form':
            if personal(t.app) and event=='v':
                recorded=self.service.recorded_copy(self.entry_id)
                if recorded:
                    item=self.service.get(self.entry_id)
                    t.app.switch_context(*item['owner'][:2], refresh=True)
                    t.app.select(recorded['id']); t.modal=None
                else:
                    self.notice='No recorded copy. This result remains unconfirmed writing.'
                return
            if personal(t.app) and event in ('c','a'):
                from .tui_personal import personal_ui
                personal_ui(t).enter('confirm' if event=='c' else 'correct',item_id=self.entry_id)
                return
            if event == 'enter':
                from .tui import Buffer
                item = self.service.get(self.entry_id)
                self.editing = self.fields[self.index]
                value = item['unfinished'].get(self.editing, item['kept'][self.editing])
                t.buffers, t.field = [Buffer(value)], 0
                self.expanded = False
                self.open('text')
            elif event == 'r':
                self.basis = False
                self.open('read')
        elif mode == 'list' and items:
            self.index = min(self.index, len(items) - 1)
            if event in ('enter', 'd'):
                self.entry_id = items[self.index]['id']
                self.index = 0
                self.open('form' if event == 'enter' else 'remove')

    def scroll_key(self, event):
        if event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
            self.scroll = (0 if event == 'home' else 10**6 if event == 'end' else max(0, self.scroll + {
                'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -8, 'page-down': 8}[event]))

    def rows(self, item, width, *, basis=False, active=None):
        rows = []

        def add(title, value, style='body'):
            rows.extend([('', 'body'), (title, 'heading')])
            rows.extend((line, style) for line in wrap(value, width))

        if not basis:
            add('ORIGINAL SUBJECT / recorded context', subject(item))
        context = self.service.context(item['id'])
        add('CONTEXT STATUS', context['status'], 'warning' if context['current'] is None or
            context['current']['digest'] != item['source']['digest'] else 'muted')
        if basis:
            for title, source in (('ORIGINAL', item['source']), ('CURRENT', context['current'])):
                if source is None:
                    continue
                if title == 'CURRENT' and source['digest'] == item['source']['digest']:
                    add('CURRENT CONTEXT', 'Matches the original context shown above.', 'muted')
                    continue
                add(title + ' SUBJECT', subject(item, source))
                add(title + ' SCOPE', source['project_id'] + ' / ' + source['episode_id'] + ' / ' + source['ref'])
                add(title + ' EVIDENCE WATERMARK', str(source['evidence_watermark']), 'muted')
                node = next(node for node in source['nodes'] if node['id'] == item['owner'][2])
                for name, label in (('conditions', 'CONDITIONS'), ('scope', 'SCOPE / CONDITIONS'),
                                    ('status', 'RECORDED STATUS'), ('source_ref', 'SOURCE REFERENCE / NOT OPENED'),
                                    ('value', 'RECORDED VALUE')):
                    if node['content'].get(name) is not None:
                        add(title + ' ' + label, str(node['content'][name]))
                metric = node['content'].get('metric', {})
                for name in ('name', 'definition', 'unit', 'comparison'):
                    if metric.get(name):
                        add(title + ' MEASUREMENT ' + name.upper(), metric[name])
                judgments = source.get('judgments') or ([source['judgment']] if source.get('judgment') else [])
                add(title + ' RECORDED JUDGMENTS / AI HISTORY',
                    'Recorded context only; separate from this new tentative judgment.' if judgments
                    else 'No recorded judgment in this scope.', 'muted')
                for judgment in judgments:
                    add('JUDGMENT / ' + judgment['episode_id'], judgment['text'])
                    add('RECORDED REASON', judgment['rationale'])
                    for i, contribution in enumerate(judgment['history'], 1):
                        add(f"CONTRIBUTION {i} / {contribution['contributor'].upper()}", contribution['text'])
                        if contribution['rationale']:
                            add('CONTRIBUTION REASON', contribution['rationale'], 'muted')
                        if contribution['proposal_id']:
                            add('ORIGINAL PROPOSAL', contribution['proposal_id'], 'muted')
            add('RESULT DRAFT BOUNDARY', 'References have not been opened. This capture is unconfirmed and cannot enter scientific review yet.', 'warning')
        else:
            for field, title in FIELDS.items():
                add(title.upper() + ' / KEPT', item['kept'][field] or 'Not written yet.')
                if active is not None and field == active[0]:
                    add('IN EDITOR / not kept', active[1] or '(empty edit)', 'warning')
                elif field in item['unfinished']:
                    add('UNFINISHED INPUT / not kept', item['unfinished'][field] or '(empty edit)', 'warning')
        return rows

    @staticmethod
    def geometry(width, height):
        return ((min(58, width * 2 // 5) + 3, 4, width - min(58, width * 2 // 5) - 5, height - 8)
                if width >= 120 else (1, 8, width - 2, height - 12))

    def draw(self, frame):
        from .tui import Frame
        w, h = frame.width, frame.height
        frame = Frame(w, h)
        mode = self.terminal.modal.removeprefix('intake-')
        if w < 48 or h < 18:
            frame.put(1, 1, 'Result capture paused', 'top_warning', w - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Esc retains input.', 'top_muted', w - 2)
            return frame
        title = {'list': 'RESULT DRAFTS', 'form': 'DRAFT A RESULT', 'text': 'WRITE RESULT DRAFT',
                 'read': 'READ RESULT DRAFT', 'remove': 'DISCARD RESULT DRAFT?'}[mode]
        frame.put(0, 2, title + ' / UNCONFIRMED', 'brand', w - 4)
        frame.put(1, 2, (getattr(self.terminal.app, 'recovery_error', None) or recovery_copy(self.terminal.app, 'Synthetic draft · encrypted recovery · unconfirmed')) if encrypted_writing(self.terminal.app) else recovery_copy(self.terminal.app, 'Synthetic session · lost on quit · not checkpointed'), 'top_warning', w - 4)
        if mode == 'list':
            items = self.service.items()
            frame.put(3, 2, 'Separate drafts / original subject and context', 'heading', w - 4)
            visible = max(1, (h - 10) // 3)
            self.index = min(self.index, max(0, len(items) - 1))
            start = max(0, self.index - visible + 1)
            for row, item in enumerate(items[start:start + visible]):
                y = 5 + row * 3
                style = 'selected' if row + start == self.index else 'body'
                for dy in range(2):
                    frame.fill(y + dy, 2, w - 4, style)
                texts = {**item['kept'], **item['unfinished']}
                preview = next((texts[field] for field in ('observation', 'judgment', 'source_ref', 'run_ref') if texts[field]), None)
                preview = preview or next((value for value in texts.values() if value), 'Empty edit retained')
                frame.put(y, 3, f"{'› ' if row + start == self.index else ''}Result {item['number']} · " + preview, style, w - 6)
                frame.put(y + 1, 3, ' / '.join(item['owner'][:2]) + ' · ' + subject(item), style, w - 6)
            if not items:
                frame.put(5, 2, 'No result writing. ; → Draft a result and source starts one.', 'muted', w - 4)
            footer = '↑↓ choose · Enter resume · d discard · Esc graph'
        else:
            item = self.service.get(self.entry_id)
            if personal(self.terminal.app) and self.service.recorded_copy(self.entry_id):
                frame.put(0,2,'RESULT DRAFT / RECORDED COPY EXISTS','brand',w-4)
                frame.put(3,2,'Edited capture stays separate. v opens the recorded observation.','top_warning',w-4)
            frame.put(2, 2, f"Result {item['number']} · " + ' / '.join(item['owner']), 'top_muted', w - 4)
            if mode in ('form', 'remove'):
                frame.put(4, 2, 'Original subject: ' + subject(item), 'body', w - 4)
            if mode == 'form':
                count = max(1, (h - 10) // 2)
                start = max(0, self.index - count + 1)
                for row, field in enumerate(self.fields[start:start + count]):
                    y = 6 + row * 2
                    style = 'selected' if start + row == self.index else 'body'
                    frame.fill(y, 2, w - 4, style)
                    frame.put(y, 3, ('› ' if start + row == self.index else '  ') + field_label(self.terminal.app,field), style, w - 6)
                    unfinished = field in item['unfinished']
                    value = item['unfinished'].get(field, item['kept'][field])
                    frame.put(y + 1, 5, ('UNFINISHED · ' if unfinished else '') + (value or '(empty edit)' if unfinished else value or 'Not written yet'),
                              'warning' if unfinished else 'muted', w - 8)
                footer = '↑↓ fields · Enter edit · r read · Esc drafts'
                self_hint = f'{self.index + 1}/{len(self.fields)} · Partial writing is welcome; references stay unopened.'
                frame.put(h - 3, 2, self.notice or self_hint, 'top_muted', w - 4)
            elif mode == 'remove':
                for row, line in enumerate(wrap('Discard kept and unfinished writing for Result ' + str(item['number']) + '? This cannot be undone.', w - 4)):
                    frame.put(6 + row, 2, line, 'warning', w - 4)
                footer = 'Enter discard this result · Esc keep it'
            elif mode == 'text' and not self.expanded:
                x, y, width, height = self.geometry(w, h)
                if w >= 120:
                    rows = [('ORIGINAL SUBJECT', 'heading')]
                    rows += [(line, 'body') for line in wrap(subject(item), x - 7)]
                    rows += [('', 'body'), ('CAPTURED RESULT / KEPT', 'heading')]
                    rows += [(line, 'body') for line in wrap(item['kept']['observation'] or 'Not written yet.', x - 7)]
                    for field in ('conditions', 'metric_name', 'metric_definition', 'value', 'unit', 'comparison'):
                        if item['kept'][field]:
                            rows += [('', 'body'), (FIELDS[field].upper(), 'heading')]
                            rows += [(line, 'body') for line in wrap(item['kept'][field], x - 7)]
                    rows += [(line, 'muted') for line in wrap(self.service.context(self.entry_id)['status'], x - 7)]
                    for row, (line, style) in enumerate(rows[:h - 9]):
                        frame.put(4 + row, 3, line, style, x - 7)
                    frame.put(h - 4, 3, 'Ctrl+O full context', 'accent', x - 7)
                else:
                    frame.put(4, 2, 'Subject: ' + subject(item), 'heading', w - 4)
                    frame.put(5, 2, 'Kept result: ' + (item['kept']['observation'] or 'Not written yet.'), 'body', w - 4)
                    frame.put(6, 2, self.service.context(self.entry_id)['status'], 'muted', w - 4)
                frame.box(x, y, width, height, field_label(self.terminal.app,self.editing).upper(), True)
                buffer = self.terminal.buffers[0]
                lines, row, column = buffer.position(width - 4)
                offset = max(0, row - height + 3)
                for n, (line, _, _) in enumerate(lines[offset:offset + height - 2]):
                    frame.put(y + 1 + n, x + 2, line, 'body', width - 4)
                frame.cursor = (y + 1 + row - offset, min(x + width - 2, x + 2 + column))
                frame.put(h - 3, 2, self.notice or buffer.notice or f'{len(buffer.text):,}/12,000 · Ctrl+_ undo · Ctrl+Y redo', 'top_muted', w - 4)
                footer = 'Ctrl+S keep · Ctrl+O context · Esc unfinished'
            else:
                active = (self.editing, self.terminal.buffers[0].text) if mode == 'text' else None
                rows = self.rows(item, w - 6, basis=self.basis, active=active)
                count = h - 8
                self.scroll = min(self.scroll, max(0, len(rows) - count))
                for row, (line, style) in enumerate(rows[self.scroll:self.scroll + count]):
                    frame.put(4 + row, 3, line, style, w - 6)
                frame.put(h - 3, 2, f'{self.scroll + 1}–{min(len(rows), self.scroll + count)}/{len(rows)} · Read only', 'top_muted', w - 4)
                footer = ('Tab result/source · Esc/Ctrl+O editor' if mode == 'text' else
                          'PgUp/PgDn · Tab result/source history · Esc fields')
        frame.put(h - 2, 2, footer, 'top_accent', w - 4)
        frame.put(h - 1, 2, ('v recorded copy · r read draft' if personal(self.terminal.app) and mode=='form' and self.service.recorded_copy(self.entry_id) else
                  'c confirm new · a append correction · r read' if personal(self.terminal.app) and mode=='form' else
                  'Provisional writing; personal confirmation is separate.' if personal(self.terminal.app) else
                  'No evidence confirmation, graph link or scientific review.'), 'top_muted', w - 4)
        if self.notice and mode not in ('form', 'text'):
            frame.put(h - 3, 2, self.notice, 'top_warning', w - 4)
        return frame


def intake_ui(terminal):
    if not hasattr(terminal, '_intake_ui'):
        terminal._intake_ui = IntakeUI(terminal)
    return terminal._intake_ui
