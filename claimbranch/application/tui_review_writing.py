"""Inspect unfinished review writing against its original and current context."""
from .tui_retention import recovery_copy
from copy import deepcopy

from claimbranch.core.canonical import ContractError
from .paper_review_writing_snapshot import capture_basis, baseline, same_text, original_history, query
from .tui_work_recovery import enabled


class ReviewWritingUI:
    def setup_input(self, mode, *, record=None):
        self.input_key = self.writing_key(mode)
        meta = self.work.unfinished_basis.get(self.input_key)
        self.input_basis = (deepcopy(meta['basis']) if meta
                            else capture_basis(self.app, record=record))
        self.terminal.field = meta['field'] if meta else 0

    def input_snapshot(self):
        t = self.terminal
        return (self.input_key, deepcopy(self.input_basis), [b.text for b in t.buffers], t.field)

    def retain_input(self):
        t = self.terminal
        if any(b.text != b.initial for b in t.buffers):
            key, basis, texts, field = self.input_snapshot()
            if same_text(texts, baseline(basis)):
                self.forget_input()
            else:
                self.work.unfinished[key] = texts
                self.work.unfinished_basis[key] = {'basis': basis, 'field': field}
        elif self.input_key in self.work.unfinished_basis:
            self.work.unfinished_basis[self.input_key]['field'] = t.field

    def forget_input(self):
        self.work.unfinished.pop(self.input_key, None)
        self.work.unfinished_basis.pop(self.input_key, None)

    def current_record(self):
        return self.work.amendments.get(self.work.key, {}).get(self.record_id) or self.work.records().get(self.record_id)

    def fields_current(self):
        owner = self.app.full_context(self.work.key)
        return (query(self.app.paper.history, owner)['digest'] == self.input_basis['source']['digest']
                and self.current_record() == self.input_basis['record'])

    def open_input_source(self):
        from .tui_understanding_ui import node_lines
        t, basis = self.terminal, self.input_basis
        self.input_return = t.modal
        self.source_rows, self.scroll = [], 0
        owner = self.app.full_context(self.work.key)
        original = query(original_history(self.app.paper.history, basis), owner)
        current = query(self.app.paper.history, owner)
        self.refresh_basis = (capture_basis(self.app, record=self.current_record()) if basis['record']
                              else capture_basis(self.app) if self.current_review() else None)
        session = basis['session']
        for label, text, reason in (
            ('ORIGINAL JUDGMENT', session['text'] if session else '', session['rationale'] if session else ''),
            ('CURRENT JUDGMENT', self.app.draft()['text'], self.app.draft()['rationale'])):
            self.source_rows.extend([(label, 'heading'), (text or 'No judgment written.', 'body'),
                                     ('Reason: ' + (reason or 'Not supplied.'), 'body'), ('', 'body')])
        self.source_rows.extend([('ORIGINAL WRITING BASIS', 'heading'),
                                ('\n'.join(baseline(basis)), 'body')])
        if self.refresh_basis:
            self.source_rows.extend([('CURRENT WRITING BASIS', 'heading'),
                                     ('\n'.join(baseline(self.refresh_basis)), 'body')])
        if basis['record']:
            for label, record in (('ORIGINAL UNACCEPTED RECORD', basis['record']),
                                  ('CURRENT UNACCEPTED RECORD', self.refresh_basis['record'])):
                self.source_rows.append((label, 'heading'))
                self.source_rows.extend((name.replace('_', ' ') + ': ' + str(value), 'body')
                                        for name, value in record['body'].items())
        if basis['request']:
            request = basis['request']
            self.source_rows.append(('Selected changes: ' + ', '.join(request['selected_ids']), 'accent'))
            for record in request['amendments']:
                self.source_rows.append((record['kind'].upper() + ' / ' + record['id'], 'heading'))
                self.source_rows.extend((key.replace('_', ' ') + ': ' + str(value), 'body')
                                        for key, value in record['body'].items())
        for label, view in (('ORIGINAL SCIENCE', original), ('CURRENT SCIENCE', current)):
            self.source_rows.extend([('', 'body'), (label, 'heading')])
            for node in view['nodes']:
                self.source_rows.extend(node_lines(node))
            for edge in view['relations']:
                self.source_rows.append((edge['source_id'] + ' → ' + edge['target_id'] + ' / ' +
                    edge['type'] + ': ' + (edge.get('rationale') or ''), 'body'))
        judgments = list(original.get('judgments', []))
        if session: judgments.append(session['judgment'])
        self.source_rows.append(('ORIGINAL AI / HUMAN CONTRIBUTIONS', 'heading'))
        for judgment in judgments:
            for contribution in judgment['history']:
                self.source_rows.extend([(contribution['contributor'].upper(), 'heading'),
                                         (contribution['text'] or '', 'body'),
                                         (contribution['rationale'] or '', 'muted')])
        self.refresh_confirm = False
        t.modal, self.notice = 'review-writing-source', ''

    def source_key(self, event):
        if event in ('escape', 'source'):
            self.terminal.modal = self.input_return
            self.scroll = 0
        elif event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
            self.scroll = (0 if event == 'home' else 10**9 if event == 'end' else max(0, self.scroll +
                {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -8, 'page-down': 8}[event]))
        elif event == 'r' and self.refresh_basis is not None:
            self.refresh_confirm = True
            self.notice = 'Enter uses this displayed basis. No text is kept or review completed yet.'
        elif event == 'enter' and self.refresh_confirm:
            if self.input_basis['record'] is None and not self.current_review():
                raise ContractError('Review expired or changed. Prepare the exact scope again; writing is retained.')
            current = capture_basis(self.app, record=self.current_record() if self.input_basis['record'] else None)
            if current != self.refresh_basis:
                raise ContractError('Context changed again. Return and inspect it before reusing this text.')
            self.input_basis = deepcopy(current)
            if self.input_key in self.work.unfinished:
                self.work.unfinished_basis[self.input_key] = {'basis': deepcopy(current), 'field': self.terminal.field}
            self.refresh_confirm = False
            self.terminal.modal = self.input_return
            self.notice = 'Current basis chosen. Ctrl+S explicitly keeps fields or completes the current review.'

    def draw_source(self, frame):
        from .tui_model import wrap
        frame.put(0, 2, 'WRITING CONTEXT / read only · original and current', 'brand', frame.width - 4)
        lines = [(line, style) for text, style in self.source_rows for line in wrap(text, frame.width - 6)]
        count = frame.height - 5
        self.scroll = min(self.scroll, max(0, len(lines) - count))
        for row, (line, style) in enumerate(lines[self.scroll:self.scroll + count]):
            frame.put(2 + row, 3, line, style, frame.width - 6)
        frame.put(frame.height - 2, 2, 'PgUp/PgDn read · Esc editor' + (' · r use current basis' if self.refresh_basis else ''),
                  'accent', frame.width - 4)
        warning = getattr(self.app, 'recovery_error', None) or self.notice
        frame.put(frame.height - 1, 2, warning or self.retention(), 'warning' if warning else 'muted', frame.width - 4)
        return frame

    def retention(self):
        return (recovery_copy(self.app, 'Unfinished text: encrypted recovery · no restored review') if enabled(self.app)
                else 'Session-only working text; source history stays unchanged.')
