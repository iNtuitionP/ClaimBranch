"""Read-only episode and conditional-work navigation over paper services."""
from .tui_retention import recovery_copy
from .tui_work_recovery import enabled as encrypted_writing
from claimbranch.core.canonical import ContractError
from .tui_model import wrap


class ContextUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = self.scroll = self.target_index = 0
        self.notice = ''

    @property
    def app(self):
        return self.terminal.app

    def dispatch(self, event):
        try:
            return self.key(event)
        except (ContractError, ValueError) as error:
            self.notice = self.app.message = str(error)
            return True

    def key(self, event):
        terminal, app = self.terminal, self.app
        modal = terminal.modal
        if modal and not modal.startswith('context-'):
            return False
        if modal is None:
            if event not in ('t', 'W'):
                return False
            if not app.series:
                app.message = 'Single-episode example. b switches branch; --series opens episodes and pending work.'
                return True
            self.notice, self.scroll = '', 0
            if event == 't':
                self.episodes = app.service.episodes()['episodes']
                self.index = next(i for i, item in enumerate(self.episodes) if item['id'] == app.episode_id)
                self.ref = app.ref
                terminal.modal = 'context-episodes'
            else:
                self.items = app.service.pending_work()['items']
                self.index = min(getattr(self, 'work_index', 0), max(0, len(self.items) - 1))
                terminal.modal = 'context-work'
            return True
        if event == 'escape':
            if modal == 'context-targets':
                terminal.modal = 'context-work-detail'
            elif modal == 'context-work-detail':
                terminal.modal = 'context-work'
            else:
                terminal.modal = None
            return True
        height, width = terminal.screen.getmaxyx()
        if width < 48 or height < 18:
            return True
        if modal == 'context-work-detail':
            if event in ('up', 'k', 'down', 'j', 'page-up', 'page-down'):
                self.scroll = max(0, self.scroll + {'up': -1, 'k': -1, 'down': 1, 'j': 1,
                                                  'page-up': -8, 'page-down': 8}[event])
            elif event == 'm':
                from .tui_manuscript_ui import manuscript_ui
                manuscript_ui(terminal).open(self.items[self.index])
            elif event == 'e':
                from .tui_understanding_ui import understanding_ui
                understanding_ui(terminal).open(self.items[self.index])
            elif event == 'g':
                item = self.items[self.index]
                self.target_view = app.service.query('main', episode_id=item['episode_id'])
                nodes = {node['id']: node for node in self.target_view['nodes']}
                ids = set(item['potentially_affected_claim_ids'] + item['potentially_affected_anchor_ids'])
                self.targets = [nodes[key] for key in sorted(ids) if key in nodes]
                self.target_index = 0
                terminal.modal = 'context-targets'
            return True
        rows = self.episodes if modal == 'context-episodes' else self.targets if modal == 'context-targets' else self.items
        attr = 'target_index' if modal == 'context-targets' else 'index'
        index = getattr(self, attr)
        if event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
            index = (0 if event == 'home' else len(rows) - 1 if event == 'end' else
                     index + {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -5, 'page-down': 5}[event])
            setattr(self, attr, max(0, min(len(rows) - 1, index)))
        elif event in ('tab', 'backtab', 'left', 'right') and modal == 'context-episodes':
            self.ref = 'alternative' if self.ref == 'main' else 'main'
        elif event == 'enter' and rows:
            if modal == 'context-episodes':
                app.switch_context(rows[index]['id'], self.ref)
                terminal.modal = None
            elif modal == 'context-work':
                self.work_index, self.scroll = index, 0
                terminal.modal = 'context-work-detail'
            else:
                app.switch_context(self.items[self.index]['episode_id'], 'main')
                app.select(rows[index]['id'], remember=False)
                app.open_view()
                app.reading_relation = False
                app.message = 'Related argument; nothing resolved. W returns to pending work.'
                terminal.modal = None
        return True

    def work_lines(self):
        item = self.items[self.index]
        lines = []

        def section(title, text, style='body'):
            lines.extend([(title, 'heading'), (str(text), style), ('', 'body')])

        section('PENDING IF ACCEPTED / ' + item['kind'].upper(),
                'No accepted debt. No closure action. Reading this item does not complete it.', 'warning')
        section('ORIGIN', item['episode_id'] + ' / ' + item['cause_operation_id'])
        section('JUDGMENT AT THAT CHANGE', item['judgment']['text'])
        section('REASON', item['judgment']['rationale'])
        section('SOURCE FRESHNESS',
                ('Changed main reasoning since this change. ' if item['main_changed_since_merge'] else 'Same main reasoning. ')
                + ('Changed global evidence since this change.' if item['evidence_changed_since_merge'] else 'Same global evidence.'), 'warning')
        section('AI ORIGIN', 'Retained in this work, including earlier source judgments.' if item['ai_influenced']
                else 'No AI influence recorded in this work.', 'accent')
        section('EXPLANATION', item['explanation_disposition'] +
                ('\n' + '\n'.join(item['explanation_answers']) if item['explanation_answers'] else ''))
        if self.app.understanding.has_writing(item['id']):
            section('YOUR EXPLANATION DRAFT', 'Session-only writing retained; e returns to its topics.', 'accent')
        section('SCIENTIFIC SELECTION', '\n'.join(label + ': ' + (', '.join(item['selection'][field]) or 'None')
                for label, field in (('Selected', 'selected'), ('Required', 'required'), ('Omitted', 'omitted'))))
        section('POTENTIALLY AFFECTED CLAIMS', ', '.join(item['potentially_affected_claim_ids']) or 'None')
        section('POTENTIALLY AFFECTED WRITING', ', '.join(item['potentially_affected_anchor_ids']) or
                'No affected anchor recorded; this is an impact check, not a proposed manuscript edit.')
        section('NEXT', 'g chooses a related node. ' + ('m opens source and wording review.' if item['kind'] == 'manuscript' else 'e opens context and unfinished explanation. Writing leaves this item open.'), 'accent')
        return lines

    def draw(self, frame):
        width, height = frame.width, frame.height
        if width < 48 or height < 18:
            return frame
        modal, app = self.terminal.modal, self.app
        x, y, w, h = 2, 1, width - 4, height - 3
        title = {'context-episodes': 'EPISODES', 'context-work': 'PENDING WORK',
                 'context-work-detail': 'PENDING WORK / READ', 'context-targets': 'RELATED ARGUMENT'}[modal]
        x, y, w, h = frame.panel(x, y, w, h, title, True)
        y, h = y + 3, h - 3
        left, measure = x + 2, w - 4
        if modal == 'context-work-detail':
            lines = [(line, style) for text, style in self.work_lines() for line in wrap(text, measure)]
            available = max(1, h - 3)
            self.scroll = min(self.scroll, max(0, len(lines) - available))
            for row, (line, style) in enumerate(lines[self.scroll:self.scroll + available]):
                frame.put(y + row, left, line, style, measure)
            hints = 'PgUp/PgDn · g related · ' + ('m wording · ' if self.items[self.index]['kind'] == 'manuscript' else 'e explain · ') + 'Esc list'
        else:
            if modal == 'context-episodes':
                intro = 'Tab branch: ' + self.ref + ' / current global evidence'
                rows = [(item['title'], item['id'] + ' / ' + item['status'] + ' / ' + item['question'], 'claim')
                        for item in self.episodes]
                selected = self.index
                hints = 'Up/Down episode · Tab branch · Enter open · Esc cancel'
            elif modal == 'context-work':
                intro = 'Conditional on acceptance / no accepted debt or closure'
                titles = {item['id']: item['title'] for item in app.service.episodes()['episodes']}
                rows = [(('Writing impact' if item['kind'] == 'manuscript' else 'Explain AI-influenced reasoning')
                         + ' / ' + item['episode_id'], titles[item['episode_id']] + ' · pending if accepted'
                         + ((recovery_copy(app, ' · explanation draft / encrypted recovery') if encrypted_writing(app) else ' · explanation draft / session only') if app.understanding.has_writing(item['id']) else ''),
                         'writing' if item['kind'] == 'manuscript' else 'plan') for item in self.items]
                selected = self.index
                hints = 'Up/Down select · Enter read · Esc graph'
            else:
                intro = self.items[self.index]['episode_id'] + ' / main / current global evidence'
                rows = [(node['content'].get('statement') or node['content'].get('objective') or 'Manuscript connection',
                         node['id'] + ' / ' + node['kind'], 'claim') for node in self.targets]
                selected = self.target_index
                hints = 'Up/Down node · Enter graph · Esc work'
            frame.put(y, left, intro, 'accent', measure)
            available = max(1, (h - 5) // 4)
            offset = max(0, selected - available + 1)
            if not rows:
                frame.put(y + 3, left, 'No items recorded for this view.', 'muted', measure)
            for row, (heading, detail, style) in enumerate(rows[offset:offset + available]):
                chosen = row + offset == selected
                at = y + 2 + row * 4
                frame.put(at, left, ('› ' if chosen else '  ') + heading, 'selected_meta' if chosen else style, measure)
                for line, text in enumerate(wrap(detail, max(2, measure - 2))[:2]):
                    frame.put(at + 1 + line, left + 2, text, 'body' if chosen else 'muted', measure - 2)
            frame.put(y + h - 2, left, f'{selected + 1 if rows else 0} / {len(rows)}', 'muted', measure)
        frame.put(height - 2, 3, hints, 'top_accent', width - 6)
        frame.put(height - 1, 3, self.notice or 'Synthetic candidate history · no scientific or manuscript writes',
                  'top_warning' if self.notice else 'top_muted', width - 6)
        return frame


def context_ui(terminal):
    if not hasattr(terminal, '_context_ui'):
        terminal._context_ui = ContextUI(terminal)
    return terminal._context_ui
