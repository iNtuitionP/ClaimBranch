"""Keyboard branch/merge rehearsal over detached service previews."""
from pathlib import Path

from claimbranch.core.canonical import ContractError
from .tui_model import wrap


def preview_lines(preview, *, basis=False):
    result = []
    def section(title, text, style='body'):
        result.extend([(title, 'heading'), (text, style), ('', 'body')])
    if not basis:
        for field in ('selected', 'required', 'omitted'):
            section(field.upper(), ', '.join(preview['selection'][field]) or 'None')
        for change in preview['amendments']:
            before = change['before']['body'] if change['before'] else {}
            after = change['after']['body'] if change['after'] else {}
            text = '\n'.join(name.replace('_', ' ') + '\nBefore: ' + str(before.get(name)) +
                             '\nAfter: ' + str(after.get(name))
                             for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name))
            section(change['disposition'].upper() + ' / ' + change['id'], text or 'No field difference.')
        for title, key in (('MAY NEED CLAIM REVIEW', 'potentially_affected_claim_ids'),
                           ('OUTSIDE THIS PATH', 'outside_impact_claim_ids'),
                           ('UNCHANGED EVIDENCE', 'unchanged_evidence_ids'),
                           ('POTENTIALLY AFFECTED WRITING', 'potentially_affected_anchor_ids')):
            section(title, ', '.join(preview['impact'][key]) or 'None')
    else:
        provenance = preview['provenance']
        section('AI ORIGIN', 'AI influence is retained; explanation or deferral is required.' if provenance['ai_influenced']
                else 'No AI influence recorded in this selection.', 'accent')
        judgments = [('CURRENT JUDGMENT', provenance['judgment'])]
        judgments += [('SOURCE JUDGMENT', value) for value in provenance.get('source_judgments', [])]
        if not provenance.get('source_judgments') and provenance.get('source_judgment'):
            judgments.append(('SOURCE JUDGMENT', provenance['source_judgment']))
        for label, judgment in judgments:
            section(label + ' / ' + judgment['episode_id'], judgment['text'])
            section('REASON', judgment['rationale'])
            for entry in judgment['history']:
                section(entry['contributor'].upper(), entry['text'])
                if entry.get('rationale'):
                    section('CONTRIBUTION REASON', entry['rationale'], 'muted')
    return result


class BranchUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.flow = None
        self.scroll = self.index = 0
        self.basis = False
        self.notice = ''

    @property
    def app(self):
        return self.terminal.app

    def open(self, draft=False):
        flow = self.app.branches.prepare_branch() if draft else self.app.branches.open_recorded()
        self.flow = flow
        self.scroll = self.index = 0
        self.basis, self.notice = False, ''
        self.terminal.modal = 'branch-preview' if draft else 'branch-select'

    def dispatch(self, event):
        try:
            self.key(event)
        except (OSError, ValueError) as error:
            self.notice = str(error)

    def edit(self, mode):
        from .tui import Buffer
        if mode == 'source':
            default = self.flow.path
        else:
            prepared = self.flow.preview()
            if not prepared or prepared['digest'] != self.preview_digest:
                self.terminal.modal = 'branch-review'
                raise ContractError('The preview expired or changed. R prepares a new merge preview.')
            default = prepared['preview']['provenance']['judgment']['rationale']
        self.terminal.buffers = [Buffer(self.flow.buffers.get(mode, [default])[0])]
        self.terminal.field = 0
        self.terminal.modal = 'branch-' + mode
        self.notice = ''

    def key(self, event):
        terminal, flow = self.terminal, self.flow
        mode = terminal.modal.removeprefix('branch-')
        if event == 'escape':
            if mode in ('source', 'answer'):
                flow.buffers[mode] = [terminal.buffers[0].text]
                terminal.modal = 'branch-select' if mode == 'source' else 'branch-review'
                self.notice = 'Unfinished editor retained; it is not included in the reviewed content.'
            elif mode == 'graph':
                terminal.modal = self.graph_return
            elif mode in ('review', 'change'):
                terminal.modal = 'branch-select'
            elif mode == 'complete':
                terminal.modal = 'branch-review'
            else:
                terminal.modal = None
            self.scroll = 0
            return
        if mode in ('source', 'answer'):
            if event == 'keep':
                text = terminal.buffers[0].text
                if mode == 'source':
                    flow.load_source(text)
                    terminal.modal = 'branch-select'
                else:
                    flow.finish(self.preview_digest, 'answered', [text])
                    terminal.modal = 'branch-review'
                flow.buffers.pop(mode, None)
                self.notice = 'Kept for this session; workspace history remains unchanged.'
            else:
                terminal.buffers[0].key(event, max(2, terminal.screen.getmaxyx()[1] - 8))
            return
        if mode == 'review' and event == 'm':
            from .tui_manuscript_ui import manuscript_ui
            manuscript_ui(terminal).choose_candidate(flow)
            return
        flow.guard()
        if mode == 'graph':
            if self.graph_return == 'branch-review':
                current = flow.preview()
                if not current or current['digest'] != self.graph_digest:
                    terminal.modal = 'branch-review'
                    raise ContractError('Comparison expired. R prepares a new merge preview.')
            from .tui_graph import move_graph
            if event == 'tab':
                self.phase = 'after' if self.phase == 'before' else 'before'
            elif event in ('up', 'down', 'left', 'right'):
                move_graph(self.graphs[self.phase], event)
            elif event in ('H', 'J', 'K', 'L'):
                graph = self.graphs[self.phase]
                dx, dy = {'H': (-8, 0), 'J': (0, 4), 'K': (0, -4), 'L': (8, 0)}[event]
                graph.graph_pan = graph.graph_pan[0] + dx, graph.graph_pan[1] + dy
                graph.graph_follow = False
            elif event == 'f':
                self.graphs[self.phase].fit_graph()
            return
        if mode == 'preview':
            if event == 'enter':
                flow.materialize()
                flow.selected &= flow.choices().keys()
                terminal.modal = 'branch-select'
                self.scroll = 0
                self.notice = 'Detached alternative candidate. Choose changes for its separate merge review.'
            elif event == 'G':
                self.open_graphs(flow.branch, mode)
            elif event == 'tab':
                self.basis, self.scroll = not self.basis, 0
        elif mode == 'select':
            items = list(flow.choices())
            if event in ('up', 'k', 'down', 'j'):
                self.index = max(0, min(len(items) - 1, self.index + (-1 if event in ('up', 'k') else 1)))
            elif event == ' ' and items:
                flow.toggle(items[self.index])
                self.notice = 'Selection changed; prior merge review cleared.'
            elif event == 'enter' and items:
                self.record_id, self.scroll = items[self.index], 0
                terminal.modal = 'branch-change'
            elif event == 's':
                self.edit('source')
            elif event == 'R':
                flow.prepare_merge()
                terminal.modal = 'branch-review'
                self.scroll, self.basis, self.notice = 0, False, ''
        elif mode == 'review':
            if event == 'R':
                flow.prepare_merge()
                self.scroll, self.notice = 0, ''
            elif event == 's':
                self.edit('source')
            elif event == 'x':
                flow.clear()
                terminal.modal = 'branch-select'
                self.notice = 'Review cleared; selection and drafts remain.'
            elif event == 'tab':
                self.basis, self.scroll = not self.basis, 0
            elif event == 'G':
                prepared = flow.preview()
                if not prepared:
                    raise ContractError('R prepares a current merge preview.')
                self.open_graphs(prepared, mode)
            elif event == 'enter':
                prepared = flow.preview()
                if not prepared:
                    raise ContractError('R prepares a current merge preview.')
                self.preview_digest = prepared['digest']
                if prepared['preview']['provenance']['ai_influenced']:
                    terminal.modal = 'branch-complete'
                else:
                    flow.finish(self.preview_digest, 'not-required', [])
                    self.notice = 'Unaccepted merge review complete. v calculates the candidate.'
            elif event == 'v':
                reviewed = flow.review()
                if not reviewed:
                    raise ContractError('Complete the exact current merge review first with Enter.')
                flow.build_candidate(reviewed['digest'])
                self.scroll = 0
                self.notice = 'Candidate calculated in memory. The workspace and pending work are unchanged.'
        elif mode == 'complete':
            if event == '1':
                self.edit('answer')
            elif event == '2':
                flow.finish(self.preview_digest, 'deferred', [])
                terminal.modal = 'branch-review'
                self.notice = 'Review complete; understanding would remain pending if accepted.'
        if mode in ('preview', 'review', 'change') and event in ('up', 'down', 'page-up', 'page-down', 'home'):
            self.scroll = 0 if event == 'home' else max(0, self.scroll + {'up': -1, 'down': 1, 'page-up': -8, 'page-down': 8}[event])

    def open_graphs(self, prepared, mode):
        from .tui_model import TerminalWorkspace
        self.graphs = {}
        for phase, projection in prepared['preview']['graphs'].items():
            graph = TerminalWorkspace(self.flow.history, ai_off=not self.app.paper.ai_available)
            graph.graph_spacing, graph.density = self.app.graph_spacing, self.app.density
            if mode == 'preview':
                graph.switch_context(self.flow.episode, self.app.ref)
            graph.view = {**graph.view, **projection}
            graph.nodes = {node['id']: node for node in projection['nodes']}
            graph._build_outline()
            graph.selected_id = self.app.selected_id if self.app.selected_id in graph._paths else graph.view['thesis_id']
            graph.selected_path = graph._paths[graph.selected_id]
            self.graphs[phase] = graph
        self.graph_return, self.graph_digest = 'branch-' + mode, prepared['digest']
        self.phase = 'after'
        self.terminal.modal = 'branch-graph'

    def content(self, mode):
        flow = self.flow
        flow.guard()
        if mode == 'preview':
            return [('DETACHED BRANCH PREVIEW / NOT RECORDED', 'warning'),
                    ('Enter calculates an alternative candidate; the workspace stays unchanged.', 'body')
                    ] + preview_lines(flow.branch['preview'], basis=self.basis)
        if mode == 'change':
            record = flow.choices()[self.record_id]
            return [(self.record_id + ' / ' + record['kind'], 'heading')] + [
                (field.replace('_', ' ').upper() + '\n' + str(value), 'body') for field, value in record['body'].items()]
        if mode == 'complete':
            return [('AI influence survives manual edits and earlier source judgments.', 'body'),
                    ('1 Explain the result and limits', 'heading'),
                    ('Reuse or revise the recorded reason.', 'body'),
                    ('2 Defer understanding', 'heading'),
                    ('If accepted later, understanding work would remain open.', 'body')]
        prepared, reviewed = flow.preview(), flow.review()
        if not prepared:
            return [('No current merge preview. R prepares one; Esc returns to selection.', 'warning')]
        lines = [('SUPPLIED SOURCE SNAPSHOT / ' + Path(flow.path).name, 'heading'),
                 ('R, completion and candidate calculation re-read the file; file identity is unverified.', 'muted')]
        if reviewed:
            lines += [('REVIEW COMPLETE / UNACCEPTED · ' + reviewed['sealed_review']['disposition'], 'accent')]
            lines += [('m Continue to manuscript wording / reuse this judgment and reason', 'accent')]
            lines += [('PENDING IF ACCEPTED / ' + item['kind'], 'warning') for item in reviewed['consequences_if_accepted']['debts']]
        if flow.candidate:
            lines += [('CANDIDATE CALCULATED / NOT INSTALLED', 'accent'),
                      ('Workspace history and pending work remain unchanged; no authorization verified.', 'body')]
        if any(any(values) for values in flow.buffers.values()):
            lines += [('Unfinished source/explanation edits retained; not included in this review.', 'warning')]
        return lines + preview_lines(prepared['preview'], basis=self.basis)

    def draw(self, frame):
        from .tui import compose
        width, height = frame.width, frame.height
        if width < 48 or height < 18:
            return frame
        mode = self.terminal.modal.removeprefix('branch-')
        if mode == 'graph':
            try:
                self.flow.guard()
                if self.graph_return == 'branch-review':
                    prepared = self.flow.preview()
                    if not prepared or prepared['digest'] != self.graph_digest:
                        raise ContractError('Comparison expired; Esc returns to review, R prepares again.')
            except ContractError as error:
                frame.put(2, 2, str(error), 'warning', width - 4)
                frame.put(height - 2, 2, 'Esc returns to ' + self.graph_return.removeprefix('branch-'), 'accent', width - 4)
                return frame
            frame = compose(self.graphs[self.phase], width, height)
            frame.fill(1, 0, width, 'canvas')
            frame.put(1, 2, 'UNACCEPTED ' + self.graph_return.removeprefix('branch-').upper() + ' / ' + self.phase.upper(), 'top_warning', width - 4)
            for y in range(height - 3, height):
                frame.fill(y, 0, width, 'canvas')
            frame.put(height - 3, 2, 'Tab before/after · Arrows move · HJKL pan · f fit', 'top_accent', width - 4)
            frame.put(height - 2, 2, 'Esc ' + self.graph_return.removeprefix('branch-') + ' · Workspace history unchanged', 'top_muted', width - 4)
            return frame
        frame.put(0, 2, 'BRANCH / ' + mode.upper() + ' · SYNTHETIC / SESSION ONLY', 'brand', width - 4)
        if mode in ('source', 'answer'):
            buffer = self.terminal.buffers[0]
            frame.box(1, 2, width - 2, height - 6, 'Read-only manuscript path' if mode == 'source' else 'Your explanation', True)
            rows, row, column = buffer.position(width - 8)
            offset = max(0, row - height + 10)
            for dy, (text, _, _) in enumerate(rows[offset:offset + height - 8]):
                frame.put(3 + dy, 3, text, 'body', width - 8)
            frame.cursor = 3 + row - offset, min(width - 4, 3 + column)
            hints, actions = 'Ctrl+S keep · Esc retain unfinished edit', 'Enter inserts a line. No file is written.'
            self.notice = self.notice or buffer.notice
        elif mode == 'select':
            for y in range(2, height - 4):
                frame.fill(y, 2, width - 4, 'body')
            try:
                items = list(self.flow.choices().values())
                self.index = min(self.index, max(0, len(items) - 1))
                frame.put(2, 3, 'Alternative → main / ' + self.flow.episode, 'heading', width - 6)
                frame.put(3, 3, 'SOURCE / ' + (Path(self.flow.path).name if self.flow.path else 's chooses a manuscript file'), 'muted', width - 6)
                count = max(1, (height - 10) // 3)
                offset = max(0, self.index - count + 1)
                if not items:
                    frame.put(5, 3, 'No changed alternative records.', 'muted', width - 6)
                for index, record in enumerate(items[offset:offset + count], offset):
                    y, chosen = 5 + 3 * (index - offset), index == self.index
                    checked = record['id'] in self.flow.selected
                    frame.put(y, 3, ('› ' if chosen else '  ') + ('[x] ' if checked else '[ ] ') + record['id'] + ' / ' + record['kind'],
                              'selected_meta' if chosen else 'heading', width - 6)
                    body = record['body']
                    text = body.get('statement', body.get('rationale', body.get('status', body.get('objective', ''))))
                    frame.put(y + 1, 7, text, 'body', width - 10)
            except ContractError as error:
                frame.put(4, 3, str(error), 'warning', width - 6)
            hints, actions = '↑↓ choose · Space include · Enter read', 's source · R review selection · Esc return'
        else:
            try:
                content = self.content(mode)
            except ContractError as error:
                content = [(str(error), 'warning')]
            lines = [(line, style) for text, style in content for line in wrap(text, width - 6)]
            self.scroll = min(self.scroll, max(0, len(lines) - height + 7))
            for y in range(2, height - 4):
                frame.fill(y, 2, width - 4, 'body')
            for y, (line, style) in enumerate(lines[self.scroll:self.scroll + height - 7], 2):
                frame.put(y, 3, line, style, width - 6)
            if mode == 'preview':
                hints, actions = 'Tab effects/basis · G graphs · PgUp/PgDn', 'Enter candidate · Esc Work'
            elif mode == 'complete':
                hints, actions = '1 explain · 2 defer · Esc review', 'No merge or pending work is accepted.'
            elif mode == 'change':
                hints, actions = 'PgUp/PgDn read · Esc selection', 'Scientific source remains unchanged.'
            else:
                hints, actions = 'm wording · Tab effects/basis · G graphs', 'Enter finish · v candidate · R refresh · x clear · Esc'
        frame.put(height - 3, 2, hints, 'top_accent', width - 4)
        frame.put(height - 2, 2, actions, 'top_accent', width - 4)
        frame.put(height - 1, 2, self.notice or 'Unaccepted rehearsal · No workspace or manuscript write', 'top_warning' if self.notice else 'top_muted', width - 4)
        return frame


def branch_ui(terminal):
    if not hasattr(terminal, '_branch_ui'):
        terminal._branch_ui = BranchUI(terminal)
    return terminal._branch_ui
