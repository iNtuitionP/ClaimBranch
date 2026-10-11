"""Keyboard presentation for volatile paper work, with exact service-bound actions."""
from .tui_retention import recovery_copy
import json

from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_context import FIELDS
from .tui_review import EDIT_FIELDS


from .tui_review_writing import ReviewWritingUI


class ReviewUI(ReviewWritingUI):
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = self.scroll = 0
        self.notice = ''

    def writing_key(self, mode):
        return (*self.work.key, mode)

    def open_fields(self, record_id):
        from .tui import Buffer
        self.record_id = record_id
        source = self.work.amendments.get(self.work.key, {}).get(record_id) or self.work.records().get(record_id)
        if source is None:
            raise ContractError('This change is unavailable; unfinished text remains in U.')
        self.setup_input('change:' + record_id, record=source)
        source = self.input_basis['record']
        self.fields = EDIT_FIELDS[source['kind']]
        texts = self.work.unfinished.get(self.writing_key('change:' + record_id),
                                         [source['body'][key] or '' for key in self.fields])
        self.terminal.buffers = [Buffer(text) for text in texts]
        self.open('fields')

    def open_answer(self, *, resumed=False):
        from .tui import Buffer
        self.setup_input('explanation')
        texts = self.work.unfinished.get(self.writing_key('explanation'), [self.app.draft()['rationale']])
        self.terminal.buffers = [Buffer(text) for text in texts]
        self.open('answer')
        if not resumed:
            from .paper_review_writing_snapshot import capture_basis
            if self.input_basis != capture_basis(self.app):
                self.notice = 'Earlier writing basis. Ctrl+O compares; r then Enter chooses this review.'

    def resume(self, mode):
        self.app.open_view(mode='work')
        self.app.reading_relation = False
        if mode.startswith('change:'):
            self.items = list(self.work.records())
            self.open_fields(mode.removeprefix('change:'))
        else:
            self.prepared = None
            self.open_answer(resumed=True)
            current = self.work.session().get_changes_preview()
            if current:
                from .paper_review_writing_snapshot import capture_basis
                if capture_basis(self.app) == self.input_basis:
                    self.prepared = current

    def current_review(self):
        current = self.work.session().get_changes_preview()
        return bool(self.prepared and current and current['digest'] == self.prepared['digest'])

    def require_review(self):
        if not self.current_review():
            raise ContractError('Review expired or changed. Esc keeps text; R in Work refreshes scope, then Enter continues.')

    def adoption_binding(self):
        if not self.restoring:
            self.work.require_current_draft()
        state = self.work.session().state()
        proposal = state['before_proposal'] if self.restoring else state['proposal']
        if not proposal or (not self.restoring and proposal['adopted']):
            raise ContractError('No retained earlier text to compare.' if self.restoring else
                                'No current unused proposal to compare.')
        return (self.work.key, state['draft_id'], state['revision'], state['paper'],
                {**state['draft'], **self.app.draft()}, proposal)

    def current_adoption(self):
        if self.work.key != self.adoption[0]:
            return False
        try:
            return self.adoption_binding() == self.adoption
        except ContractError:
            return False

    @property
    def app(self):
        return self.terminal.app

    @property
    def work(self):
        return self.app.review

    def open(self, kind):
        self.terminal.modal = 'review-' + kind
        self.index = self.scroll = 0
        self.notice = ''

    def return_to_changes(self):
        self.open('changes')
        self.index = self.items.index(self.record_id)

    def dispatch(self, event):
        """Return whether the contextual action consumed this key."""
        try:
            return self.key(event)
        except (ContractError, ValueError) as error:
            self.notice = str(error)
            self.app.message = str(error)
            return True

    def key(self, event):
        terminal, app, work = self.terminal, self.app, self.work
        modal = terminal.modal
        if modal and modal.startswith('review-'):
            if modal == 'review-writing-source' and event in ('escape', 'source'):
                self.source_key(event)
                return True
            if event == 'escape':
                if modal in ('review-fields', 'review-answer'):
                    self.retain_input()
                    terminal.buffers = []
                    app.message = 'U resumes unfinished text; unkept edits are outside the review.'
                if modal == 'review-fields':
                    self.return_to_changes()
                else:
                    if modal == 'review-outbound':
                        work.session().cancel_request()
                    if modal == 'review-graph':
                        app._restore_navigation(self.compare_return)
                    terminal.modal = None
                return True
            height, width = terminal.screen.getmaxyx()
            if width < 48 or height < 18:
                return True
            if modal == 'review-adoption':
                if event == 'enter':
                    if not self.current_adoption():
                        raise ContractError('Comparison changed or expired. Esc returns; reopen a comparison of current writing.')
                    if self.restoring:
                        work.restore_before_ai()
                        app.message = 'Earlier text restored after comparison. Contribution history and AI origin remain visible.'
                    else:
                        work.adopt_ai(self.adoption[-1]['id'])
                        from .tui_work_recovery import enabled
                        app.message = ('Adopted; judgment and AI origin will be checkpointed. w reviews contributions.' if enabled(app) else
                                       'Adopted for this session; AI origin is retained. e edits; w reviews contributions.')
                    terminal.modal = None
                    app.scroll = 0
                elif event in ('page-up', 'up', 'page-down', 'down', 'home', 'end'):
                    self.scroll = (0 if event == 'home' else 100000 if event == 'end' else
                                   max(0, self.scroll + (-8 if event in ('page-up', 'up') else 8)))
                return True
            if modal == 'review-writing-source':
                self.source_key(event)
                return True
            if modal == 'review-fields' or modal == 'review-answer':
                if event == 'source':
                    self.open_input_source()
                elif event in ('tab', 'backtab'):
                    terminal.field = (terminal.field + (1 if event == 'tab' else -1)) % len(terminal.buffers)
                    if self.input_key in work.unfinished_basis:
                        work.unfinished_basis[self.input_key]['field'] = terminal.field
                elif event == 'keep':
                    if modal == 'review-fields':
                        if not self.fields_current():
                            raise ContractError('Original context changed. Ctrl+O compares; r then Enter chooses the current basis.')
                        values = {key: buffer.text.strip() or (None if key == 'scope' else '')
                                  for key, buffer in zip(self.fields, terminal.buffers)}
                        work.stage(self.record_id, values)
                        self.forget_input()
                        terminal.buffers = []
                        self.return_to_changes()
                        self.notice = 'Change kept. Review selection retained; Space includes/omits it.'
                    else:
                        self.require_review()
                        from .paper_review_writing_snapshot import capture_basis
                        if capture_basis(app) != self.input_basis:
                            raise ContractError('Answer has an earlier basis. Ctrl+O compares; r then Enter chooses this review.')
                        work.finish_changes(self.prepared['digest'], 'answered', [terminal.buffers[0].text])
                        self.forget_input()
                        terminal.buffers = []
                        terminal.modal = None
                        app.scroll = 0
                else:
                    terminal.buffers[terminal.field].key(event, max(2, terminal.screen.getmaxyx()[1] - 8))
                return True
            if modal == 'review-graph':
                self.require_review()
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
                return True
            if modal in ('review-context', 'review-changes'):
                self.index = min(self.index, max(0, len(self.items) - 1))
                if event in ('up', 'k', 'down', 'j'):
                    self.index = max(0, min(len(self.items) - 1, self.index + (-1 if event in ('up', 'k') else 1)))
                elif modal == 'review-context':
                    if event == ' ' and self.items:
                        key = self.items[self.index]
                        self.context.remove(key) if key in self.context else self.context.add(key)
                    elif event == 'd':
                        self.include_draft = not self.include_draft
                    elif event == 'enter':
                        self.outbound = work.prepare_ai(sorted(self.context), include_draft=self.include_draft)
                        self.open('outbound')
                elif event == 'J' and self.items:
                    work.stage_judgment(self.items[self.index])
                    self.notice = 'Judgment wording staged and included for this interpretation. Space omits it.'
                elif event == ' ' and self.items:
                    work.toggle(self.items[self.index])
                elif event in ('enter', 'e') and self.items:
                    self.open_fields(self.items[self.index])
                elif event == 'R':
                    work.prepare_changes()
                    terminal.modal = None
                    app.open_view(mode='work')
                    app.scroll = 0
                return True
            if modal == 'review-outbound' and event == 'enter':
                work.begin_ai(self.outbound)
                terminal.modal = None
                app.open_view(mode='work')
                app.message = 'Offline example pending. e keeps manual drafting available; x cancels.'
            elif modal == 'review-complete':
                self.require_review()
                if event == '1':
                    self.open_answer()
                elif event == '2':
                    work.finish_changes(self.prepared['digest'], 'deferred', [])
                    terminal.modal = None
                    app.scroll = 0
            elif event in ('page-up', 'up', 'page-down', 'down'):
                self.scroll = max(0, self.scroll + (-8 if event in ('page-up', 'up') else 8))
            return True
        if event == 'w':
            app.open_view(mode='work')
            app.reading_relation = False
            return True
        if app.mode != 'work' or app.focus != 'detail':
            return False
        if event == 'A':
            if not app.paper.ai_available:
                app.message = 'AI OFF. Manual writing remains available; e writes a judgment.'
                return True
            available = {key for key, node in app.nodes.items() if node['kind'] in FIELDS}
            nearby = {app.selected_id, *(link.target_id for link in app.links())} & available
            self.items = sorted(nearby, key=lambda key: (key != app.selected_id, key)) + sorted(available - nearby)
            self.context = {app.selected_id} if app.selected_id in self.items else set()
            self.include_draft = False
            self.open('context')
        elif event == 'c':
            self.items = list(work.records())
            self.open('changes')
            if app.selected_id in self.items:
                self.index = self.items.index(app.selected_id)
        elif event == 'C':
            from .tui_branch_ui import branch_ui
            branch_ui(terminal).open(draft=True)
        elif event == 'R':
            from .tui_retention import personal
            candidates = work.candidate_works.get(work.key)
            if personal(app) and candidates and any(origin.ai_influenced for origin in candidates.origins.values()):
                from .tui_personal import personal_ui
                personal_ui(terminal).enter('reasoning')
            else:
                work.prepare_changes()
                app.scroll = 0
        elif event in ('y', 'B'):
            self.restoring = event == 'B'
            self.adoption = self.adoption_binding()
            self.open('adoption')
        elif event == 'x':
            work.not_now()
            app.message = 'Not now. Your draft and authored changes remain; request/review cancelled.'
            app.scroll = 0
        elif event in ('enter', 'G'):
            self.prepared = work.session().get_changes_preview()
            if not self.prepared:
                raise ContractError('Write a judgment and reason, edit/select changes with c, then R to review.')
            if event == 'G':
                self.open_graphs()
            elif self.prepared['preview']['provenance']['ai_influenced']:
                self.open('complete')
            else:
                work.finish_changes(self.prepared['digest'], 'not-required', [])
                app.scroll = 0
                app.message = 'Review complete for this session. Scientific acceptance remains unavailable.'
        else:
            return False
        return True

    def open_graphs(self):
        from .tui_model import TerminalWorkspace
        self.compare_return = self.app._navigation()
        self.graphs = {}
        for phase, projection in self.prepared['preview']['graphs'].items():
            graph = TerminalWorkspace(self.work.history, ai_off=not self.app.paper.ai_available)
            graph.projection_only = True
            graph.graph_spacing, graph.density = self.app.graph_spacing, self.app.density
            graph.ref = self.app.ref
            graph.view = {**self.app.view, **projection}
            graph.nodes = {node['id']: node for node in projection['nodes']}
            graph._label_overrides = {key: self.work.label(key) for key in graph.nodes}
            graph._build_outline()
            graph.selected_id = self.app.selected_id
            graph.selected_path = graph._paths[graph.selected_id]
            self.graphs[phase] = graph
        self.phase = 'after'
        self.open('graph')

    def draw(self, frame):
        from .tui import Frame, compose
        from .tui_model import wrap
        terminal, app, work = self.terminal, self.app, self.work
        width, height = frame.width, frame.height
        if width < 48 or height < 18:
            frame = Frame(width, height)
            frame.put(1, 1, 'Review controls paused', 'warning', width - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Esc returns.', 'body', width - 2)
            frame.put(5, 1, 'Editing text stays in this session.', 'muted', width - 2)
            return frame
        modal = terminal.modal
        if modal == 'review-adoption' and not self.current_adoption():
            frame = Frame(width, height)
            frame.put(2, 2, 'COMPARISON CHANGED OR EXPIRED', 'warning', width - 4)
            frame.put(4, 2, 'Esc returns; reopen a comparison of current writing.', 'body', width - 4)
            frame.put(6, 2, 'Your newer writing has not been replaced.', 'muted', width - 4)
            return frame
        if modal in ('review-graph', 'review-complete') and not self.current_review():
            frame = Frame(width, height)
            frame.put(2, 2, 'REVIEW EXPIRED OR CHANGED', 'warning', width - 4)
            frame.put(4, 2, 'Esc returns to Work. R refreshes the review scope.', 'body', width - 4)
            frame.put(6, 2, 'Unfinished text remains available in U.', 'muted', width - 4)
            return frame
        if modal == 'review-writing-source':
            return self.draw_source(Frame(width, height))
        if modal == 'review-graph':
            frame = compose(self.graphs[self.phase], width, height)
            frame.fill(1, 0, width, 'canvas')
            frame.put(1, 2, 'UNACCEPTED COMPARISON / ' + self.phase.upper() + ' · source history unchanged', 'top_warning', width - 4)
            for row in range(height - 3, height):
                frame.fill(row, 0, width, 'canvas')
            frame.put(height - 3, 2, 'Tab before/after · Arrows select · HJKL pan · f fit · Esc review', 'top_accent', width - 4)
            frame.put(height - 2, 2, 'This compares the selected changes; it accepts no scientific change.', 'top_muted', width - 4)
            return frame
        frame = Frame(width, height)
        if modal in ('review-fields', 'review-answer'):
            title = ('EDIT CHANGE / ' + self.record_id if modal == 'review-fields'
                     else 'YOUR EXPLANATION / revise or reuse your reason')
            frame.put(0, 2, title, 'brand', width - 4)
            fields = self.fields if modal == 'review-fields' else ('What is established, and what remains untested?',)
            available = height - 5
            h = available // len(fields)
            for index, (name, buffer) in enumerate(zip(fields, terminal.buffers)):
                y = 2 + index * h
                frame.box(1, y, width - 2, h, name.upper(), terminal.field == index)
                rows, row, column = buffer.position(width - 8)
                offset = max(0, row - h + 3)
                for number, (text, _, _) in enumerate(rows[offset:offset + h - 2]):
                    frame.put(y + 1 + number, 3, text, 'body', width - 8)
                if terminal.field == index:
                    frame.cursor = y + 1 + row - offset, min(width - 4, 3 + column)
            frame.put(height - 2, 2, 'Tab field · Ctrl+S keep · Ctrl+O context · Esc retain', 'accent', width - 4)
            help_text = ('Relation types: supports / challenges / qualifies' if modal == 'review-fields' and 'edge_type' in fields
                         else self.retention())
            if modal == 'review-answer' and not self.current_review():
                help_text = 'Review stale. Esc retains text; R in Work refreshes scope.'
            warning = getattr(app, 'recovery_error', None) or self.notice or terminal.buffers[terminal.field].notice
            frame.put(height - 1, 2, warning or help_text, 'warning' if warning else 'muted', width - 4)
            return frame
        titles = {'review-context': 'OFFLINE AI / CHOOSE CONTEXT', 'review-outbound': 'REVIEW EXACT OFFLINE REQUEST',
                  'review-changes': 'YOUR SCIENTIFIC CHANGES / SESSION ONLY', 'review-complete': 'COMPLETE REVIEW / AI ORIGIN RETAINED',
                  'review-adoption': 'COMPARE AI PROPOSAL / NOT ACCEPTED'}
        frame.put(0, 2, titles[modal], 'brand', width - 4)
        if modal in ('review-context', 'review-changes'):
            context = modal == 'review-context'
            frame.put(1, 2, ('Only checked nodes and scientific links between them enter the request.' if context
                            else 'Enter edits a change; Space includes/omits an authored change.'), 'muted', width - 4)
            visible = max(1, (height - 6) // 2)
            offset = max(0, self.index - visible + 1)
            for row, key in enumerate(self.items[offset:offset + visible]):
                selected = key in (self.context if context else work.selected.get(work.key, set()))
                active = row + offset == self.index
                staged = key in work.amendments.get(work.key, {})
                label = app.node_label(key) + ' / ' + app.kind(key) if key in app.nodes else key
                if context:
                    text = app.title(key)
                else:
                    body = (work.amendments.get(work.key, {}).get(key) or work.records()[key])['body']
                    text = (work.label(body['source_id']) + ' ' + body['edge_type'] + ' → ' + work.label(body['target_id']) + ' · ' + body['rationale']
                            if 'edge_type' in body else body.get('statement', body.get('objective', '')))
                frame.put(3 + 2 * row, 2, ('› ' if active else '  ') + ('[x] ' if selected else '[ ] ') + label
                          + (' · edited' if staged and not context else '')
                          + (' · unfinished' if not context and self.writing_key('change:' + key) in work.unfinished else ''), 'selected_meta' if active else 'heading', width - 4)
                frame.put(4 + 2 * row, 8, text, 'selected' if active else 'body', width - 10)
            hints = ('↑↓ choose · Space toggle · d draft ' + ('ON' if self.include_draft else 'OFF') + ' · Enter review' if context
                     else '↑↓ choose · Enter edit · Space include · J use judgment · R review')
            frame.put(height - 2, 2, hints, 'accent', width - 4)
            frame.put(height - 1, 2, self.notice or ('Enter replaces the prior request/proposal; Esc keeps it. Notes excluded.' if context
                      else 'Changes are session-only; Esc closes. Your source stays unchanged.'), 'warning' if self.notice else 'muted', width - 4)
            return frame
        content = []
        if modal == 'review-adoption':
            frame.put(0, 2, 'COMPARE EARLIER TEXT / AI ORIGIN RETAINED' if self.restoring else
                      'COMPARE AI PROPOSAL / NOT ACCEPTED', 'brand', width - 4)
            owner, _, _, paper, draft, proposal = self.adoption
            from .tui_work_recovery import enabled
            content = [('RETAINED PRIOR BUFFER / NOT ACCEPTED' if self.restoring else
                        'FIXED OFFLINE EXAMPLE / NO LIVE MODEL', 'heading'),
                       (paper['episode_id'] + ' / ' + paper['ref'] + ' / judgment ' + app.node_label(owner[-1]), 'muted'),
                       ('YOUR JUDGMENT / KEPT BEFORE', 'heading'), (draft['text'] or '(empty judgment)', 'body'),
                       ('YOUR CURRENT REASON' if self.restoring else 'YOUR REASON / KEPT UNCHANGED', 'heading'), (draft['rationale'] or '(empty reason)', 'body'),
                       ('EARLIER TEXT / AFTER' if self.restoring else 'PROPOSED REPLACEMENT / AFTER', 'heading'), (proposal['text'] or '(empty judgment)', 'body')]
            if self.restoring:
                content += [('EARLIER REASON / AFTER', 'heading'), (proposal['rationale'] or '(empty reason)', 'body')]
            content += [
                       ('AI ORIGIN / RETAINED AFTER HUMAN EDITS', 'heading'),
                       ('This restores the earlier judgment and reason, replacing current kept writing; AI origin remains.' if self.restoring else
                        'This replaces the whole kept judgment, not individual nodes or links. B compares prior text before restoring it; AI origin remains.', 'body'),
                       ('Unkept judgment writing remains separate in U; this changes kept writing only.', 'muted'),
                       (recovery_copy(app, 'Judgment and adopted AI origin are included in encrypted checkpoints.') if enabled(app) else
                        'SESSION ONLY: adopted AI writing is not in manual draft-file checkpoints.', 'warning'),
                       ('No scientific acceptance, evidence confirmation or manuscript write.', 'muted')]
            hints = 'Enter restore earlier · Esc keep mine' if self.restoring else 'Enter replace judgment · Esc keep mine'
            frame.put(1, 2, 'PgUp/PgDn read · Home/End', 'muted', width - 4)
        elif modal == 'review-outbound':
            request = self.outbound['request']
            content = [('FIXED EXAMPLE / NO NETWORK', 'heading'),
                       ('Destination: ' + request['destination']['url'] + ' / ' + request['destination']['model'], 'body'),
                       ('Retention: this running session. Full selected content follows.', 'muted')]
            for record in request['context']['records']:
                content.extend([('', 'body'), (record['kind'].upper() + ' / ' + record['id'], 'heading'),
                                (json.dumps(record['fields'], ensure_ascii=False, indent=2), 'body')])
            hints = 'PgUp/PgDn read · Enter request example · Esc cancel'
        else:
            content = [('Your judgment or selected source includes AI contributions.', 'body'),
                       ('1 · Explain the result and its limits', 'heading'),
                       ('Reuse or revise your existing reason; no second judgment is needed.', 'body'),
                       ('2 · Defer understanding', 'heading'),
                       ('If accepted later, understanding work would remain open. This review accepts nothing.', 'body')]
            hints = '1 explain · 2 defer · Esc return to review'
        lines = [(line, style) for text, style in content for line in wrap(text, width - 6)]
        self.scroll = min(self.scroll, max(0, len(lines) - height + 6))
        for row, (line, style) in enumerate(lines[self.scroll:self.scroll + height - 6]):
            frame.put(3 + row, 3, line, style, width - 6)
        frame.put(height - 2, 2, hints, 'accent', width - 4)
        frame.put(height - 1, 2, self.notice, 'warning', width - 4)
        return frame


def review_ui(terminal):
    if not hasattr(terminal, '_review_ui'):
        terminal._review_ui = ReviewUI(terminal)
    return terminal._review_ui
