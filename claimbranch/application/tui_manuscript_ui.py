"""Terminal wording review over the exact manuscript service; no apply controls."""
from .tui_retention import recovery_copy
from pathlib import Path

from claimbranch.core.canonical import ContractError
from .tui_model import clip, wrap


class ManuscriptUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.scroll = 0
        self.tab = 'diff'
        self.notice = ''
        self.return_modal = 'context-work-detail'

    @property
    def work(self):
        return self.terminal.app.manuscript

    def open(self, item):
        if item['kind'] != 'manuscript':
            raise ContractError('Choose a Writing impact item for manuscript review.')
        self.work.open(item['id'])
        self.return_modal = 'context-work-detail'
        self.notice, self.scroll, self.tab = '', 0, 'diff'
        self.terminal.modal = 'manuscript-read'

    def open_saved(self):
        self.saved_keys = list(self.work.sessions)
        self.choice, self.scroll, self.notice = 0, 0, ''
        self.discard_saved = False
        self.return_modal = 'manuscript-saved'
        self.terminal.modal = 'manuscript-saved'

    def retention(self):
        from .tui_work_recovery import enabled
        return (recovery_copy(self.terminal.app, 'Wording: encrypted recovery · reviews must be prepared again') if enabled(self.terminal.app)
                else 'Session only · no file write or acceptance')

    def choose_candidate(self, flow):
        self.flow = flow
        try:
            reviewed = flow.review()
        except (OSError, ValueError):
            reviewed = None
        self.current_key = 'candidate-' + reviewed['digest'] if reviewed else None
        self.choices = [None, *[key for key in reversed(self.work.candidate_items(flow)) if key != self.current_key]]
        self.choice = self.scroll = 0
        self.notice, self.return_modal = '', 'branch-review'
        self.terminal.modal = 'manuscript-choose'

    def basis_lines(self):
        state = self.work.session.state()
        item = state['work']
        rows = [('SCIENTIFIC JUDGMENT / ' + item['episode_id'], 'heading'),
                (item['judgment']['text'], 'body'), ('JUDGMENT REASON / Ctrl+R reuses while writing', 'heading'),
                (item['judgment']['rationale'], 'body'),
                ('SELECTED SCIENCE', 'heading'), (', '.join(item['selection']['selected']), 'body')]
        for index, judgment in enumerate([item['judgment'], *item['source_judgments']]):
            rows += [(('THIS JUDGMENT' if index == 0 else 'SOURCE JUDGMENT ' + str(index)) + ' / ' + judgment['episode_id'], 'heading')]
            for contribution in judgment['history']:
                rows += [(contribution['contributor'].upper(), 'accent'), (contribution['text'], 'body'),
                         (contribution['rationale'] or '', 'muted')]
        binding = self.work.parents.get(self.work.work_id)
        if binding:
            from .tui_branch_ui import preview_lines
            rows += [('EXACT SCIENTIFIC SELECTION', 'heading'), *preview_lines(binding['science'])]
        return rows

    def reuse_reason(self):
        from .tui import Buffer
        value = Buffer(self.work.session.state()['work']['judgment']['rationale']).text
        if len(value) > 12000:
            raise ContractError('The judgment reason exceeds this editor limit; inspect it with Ctrl+O and write a shorter wording reason.')
        buffer = self.terminal.buffers[1]
        if buffer.text != value:
            buffer.checkpoint()
            buffer.text, buffer.cursor = value, len(value)
        self.terminal.field = 1
        self.notice = 'Judgment reason reused. Ctrl+_ in the reason field undoes; Ctrl+S keeps.'

    def edit(self, kind):
        from .tui import Buffer
        state = self.work.session.state()
        defaults = {'source': [self.work.paths.get(self.work.work_id, '')],
                    'wording': [state['draft']['draft']['text'], state['draft']['draft']['rationale']],
                    'answer': [state['draft']['draft']['rationale']]}
        self.editor_defaults = defaults[kind]
        values = self.work.buffers.get((self.work.work_id, kind), defaults[kind])
        self.terminal.buffers = [Buffer(text) for text in values]
        self.terminal.field = self.work.positions.get((self.work.work_id, kind), 0)
        self.terminal.modal = 'manuscript-' + kind
        self.notice = ''

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, OSError, ValueError, UnicodeError) as error:
            self.notice = str(error)

    def key(self, event):
        terminal, work = self.terminal, self.work
        mode = terminal.modal.removeprefix('manuscript-')
        h, w = terminal.screen.getmaxyx()
        if (w < 48 or h < 18) and event != 'escape':
            return
        if mode == 'saved':
            if event == 'escape':
                if self.discard_saved:
                    self.discard_saved, self.notice = False, ''
                else: terminal.modal = None
            elif event in ('up', 'k', 'down', 'j'):
                self.discard_saved, self.notice = False, ''
                self.choice = max(0, min(len(self.saved_keys) - 1, self.choice + (-1 if event in ('up', 'k') else 1)))
            elif event == 'd' and self.saved_keys:
                self.discard_saved = True
                self.notice = 'Enter discards this wording draft only. Esc cancels; science and source files stay unchanged.'
            elif event == 'enter' and self.saved_keys:
                if self.discard_saved:
                    key = self.saved_keys[self.choice]
                    for values in (work.sessions, work.paths, work.parents, work.restored): values.pop(key, None)
                    for values in (work.buffers, work.positions):
                        for pair in [pair for pair in values if pair[0] == key]: del values[pair]
                    if work.work_id == key: work.work_id = None
                    self.open_saved()
                    self.notice = 'Wording draft discarded. Recorded work and source files stay unchanged.'
                    return
                work.work_id = self.saved_keys[self.choice]
                terminal.modal, self.scroll, self.tab = 'manuscript-read', 0, 'diff'
            return
        if mode == 'choose':
            if event == 'escape':
                terminal.modal = self.return_modal
            elif event in ('up', 'k', 'down', 'j', 'home', 'end'):
                self.choice = (0 if event == 'home' else len(self.choices) - 1 if event == 'end' else
                               max(0, min(len(self.choices) - 1, self.choice + (-1 if event in ('up', 'k') else 1))))
            elif event == 'enter':
                key = self.choices[self.choice]
                if key is None:
                    work.open_candidate(self.flow)
                else:
                    work.work_id = key
                terminal.modal, self.scroll, self.tab, self.notice = 'manuscript-read', 0, 'diff', ''
            return
        if mode in ('basis', 'reason'):
            if event in ('escape', 'source'):
                terminal.modal = 'manuscript-wording'
                self.scroll = 0
            elif mode == 'reason' and event == 'enter':
                self.reuse_reason()
                terminal.modal = 'manuscript-wording'
            elif event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
                self.scroll = (0 if event == 'home' else 10**9 if event == 'end' else max(0, self.scroll +
                               {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -8, 'page-down': 8}[event]))
            return
        if mode in ('source', 'wording', 'answer'):
            if event == 'escape':
                key = work.work_id, mode
                if any(b.text != b.initial for b in terminal.buffers):
                    values = [b.text for b in terminal.buffers]
                    if values == self.editor_defaults:
                        work.buffers.pop(key, None)
                    else:
                        work.buffers[key] = values
                terminal.modal = 'manuscript-read'
                work.positions[key] = terminal.field
                terminal.buffers = []
                self.notice = ('Unfinished edit retained for this item; it is not included in the preview.'
                               if key in work.buffers else 'Kept wording and source unchanged.')
            elif event in ('tab', 'backtab'):
                terminal.field = (terminal.field + 1) % len(terminal.buffers)
                if (work.work_id, mode) in work.buffers:
                    work.positions[work.work_id, mode] = terminal.field
            elif mode == 'wording' and event == 'source':
                self.scroll = 0
                terminal.modal = 'manuscript-basis'
            elif mode == 'wording' and event == 'reuse-reason':
                from .tui import Buffer
                if terminal.buffers[1].text and terminal.buffers[1].text != Buffer(work.session.state()['work']['judgment']['rationale']).text:
                    terminal.modal, self.scroll = 'manuscript-reason', 0
                else:
                    self.reuse_reason()
            elif event == 'keep':
                values = [b.text for b in terminal.buffers]
                if mode == 'source':
                    work.load_source(values[0])
                elif mode == 'wording':
                    work.session.draft.edit(*values)
                else:
                    work.finish(self.preview_digest, 'answered', values)
                work.buffers.pop((work.work_id, mode), None)
                work.positions.pop((work.work_id, mode), None)
                terminal.buffers = []
                terminal.modal = 'manuscript-read'
                self.scroll = 0
                self.notice = ('Source loaded; retained alongside written wording.' if mode == 'source' else
                               'Wording kept.' if mode == 'wording' else 'Review complete for this session.')
                self.notice += ' No manuscript file was written.'
            else:
                terminal.buffers[terminal.field].key(event, max(2, terminal.screen.getmaxyx()[1] - 8))
            return
        if event == 'escape':
            terminal.modal = self.return_modal if mode == 'read' else 'manuscript-read'
            self.notice = ''
        elif mode == 'complete':
            if event == '1':
                self.edit('answer')
            elif event == '2':
                work.finish(self.preview_digest, 'deferred', [])
                terminal.modal = 'manuscript-read'
                self.notice = 'Review complete; understanding would remain pending if accepted.'
        elif event == 's':
            self.edit('source')
        elif event == 'e':
            self.edit('wording')
        elif event == 'R':
            work.prepare()
            self.scroll, self.notice, self.tab = 0, '', 'diff'
        elif event == 'enter':
            preview = work.session.get_preview()
            if not preview:
                raise ContractError('Use s to load source, e to write wording/reason, then R to inspect the exact diff.')
            self.preview_digest = preview['digest']
            if preview['ai_influenced']:
                terminal.modal = 'manuscript-complete'
            else:
                work.finish(self.preview_digest, 'not-required', [])
                self.notice = 'Review complete for this session. Source file and pending work are unchanged.'
        elif event == 'x':
            work.session.not_now()
            self.notice = 'Review cleared. Wording and unfinished edits remain for this item.'
        elif event in ('tab', 'backtab'):
            tabs = ('diff', 'before', 'after', 'basis')
            self.tab = tabs[(tabs.index(self.tab) + (1 if event == 'tab' else -1)) % len(tabs)]
            self.scroll = 0
        elif event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
            self.scroll = 0 if event == 'home' else 10**9 if event == 'end' else max(0, self.scroll + {
                'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -8, 'page-down': 8}[event])

    def lines(self):
        session = self.work.session
        parent_error = ''
        try:
            self.work.check_parent()
        except (OSError, ValueError) as error:
            parent_error = str(error)
        state = session.state()
        preview, reviewed = session.get_preview(), session.get_review()
        item = state['work']
        target = 'candidate main' if self.work.work_id in self.work.parents else 'current main'
        lines = [('WRITING / ' + item['episode_id'] + ' → ' + target + ' / ' + state['draft']['paper']['episode_id'], 'heading'),
                 (self.retention(), 'warning')]
        if self.work.work_id in self.work.parents:
            lines += [('DETACHED CANDIDATE / workspace and W unchanged', 'warning')]
        if parent_error:
            lines += [('EARLIER SCIENTIFIC BASIS / review unavailable', 'warning'), (parent_error, 'warning')]
        if not preview and self.tab == 'before' and session._source is not None:
            lines += [('ORIGINAL SUPPLIED SOURCE / retained bytes, not a current file check', 'heading')]
            lines += [(line, 'body', True) for line in session._source.decode('utf-8').splitlines()]
            return lines
        if reviewed:
            lines.append(('REVIEW COMPLETE / UNACCEPTED · ' + reviewed['disposition'], 'accent'))
        if any(key[0] == self.work.work_id and any(value) for key, value in self.work.buffers.items()):
            lines.append(('Unfinished edits retained; current preview uses kept wording/source only.', 'warning'))
        if preview:
            lines.extend([('Tab: DIFF / BEFORE / AFTER / BASIS · viewing ' + self.tab.upper(), 'heading'),
                          ('Source is a supplied snapshot; R and completion re-read the file.', 'muted')])
            if self.tab in ('diff', 'before', 'after'):
                for line in preview['source'][self.tab].splitlines():
                    style = 'supports' if self.tab == 'diff' and line.startswith('+') else 'challenges' if self.tab == 'diff' and line.startswith('-') else 'body'
                    lines.append((line, style, True))
                return lines
        if not preview:
            lines.extend([('No current preview. s source; e wording; R review; Tab original source/basis.', 'accent'),
                          ('SOURCE / ' + (Path(self.work.paths[self.work.work_id]).name if self.work.work_id in self.work.paths else 'retained snapshot' if session._source is not None else 'not supplied'), 'heading'),
                          ('Supply a UTF-8 file (≤64 KiB). Its target block must have these markers:', 'body'),
                          ('% claimbranch:start id=' + item['anchor_id'], 'body'),
                          ('% claimbranch:end id=' + item['anchor_id'], 'body'),
                          ('YOUR WORDING', 'heading'), (state['draft']['draft']['text'] or '(blank)', 'body'),
                          ('YOUR REASON', 'heading'), (state['draft']['draft']['rationale'] or '(blank)', 'body')])
        lines.extend([('WHY THIS WORK EXISTS', 'heading'), (item['judgment']['text'], 'body'),
                      (item['judgment']['rationale'], 'body'),
                      ('AI ORIGIN', 'heading'),
                      ('Recorded source judgments include AI contributions; explanation or explicit deferral is required.'
                       if (preview['ai_influenced'] if preview else item['ai_influenced']) else 'No recorded AI influence in this item.', 'body'),
                      ('SOURCE BINDING / supplied bytes, file identity unverified', 'heading'),
                      (state['source_digest'] or 'No source loaded.', 'muted')])
        if preview:
            lines.extend([('CANDIDATE BYTE DIGEST', 'heading'), (preview['postimage_digest'], 'muted'),
                          ('WORDING REASON', 'heading'), (preview['draft']['judgment']['rationale'], 'body')])
            for judgment in preview['source_judgments']:
                lines.extend([('SOURCE JUDGMENT / ' + judgment['episode_id'], 'heading'),
                              (judgment['text'], 'body'), (judgment['rationale'], 'body')])
                for contribution in judgment['history']:
                    lines.extend([(contribution['contributor'].upper(), 'accent'),
                                  (contribution['text'], 'body'), (contribution['rationale'] or '', 'body')])
        return lines

    def draw(self, frame):
        app = self.terminal.app
        width, height = frame.width, frame.height
        if width < 48 or height < 18:
            return frame
        mode = self.terminal.modal.removeprefix('manuscript-')
        if mode == 'saved':
            frame.put(0, 2, 'MANUSCRIPT DRAFTS / original scientific basis', 'brand', width - 4)
            count = max(1, (height - 6) // 3)
            start = max(0, self.choice - count + 1)
            if not self.saved_keys:
                frame.put(3, 3, 'No manuscript drafts. W opens recorded writing impact.', 'body', width - 6)
            for i, key in enumerate(self.saved_keys[start:start + count], start):
                state = self.work.sessions[key].state()
                title = ('› ' if i == self.choice else '  ') + state['work']['episode_id']
                title += ' / earlier candidate' if key in self.work.parents else ' / recorded cause'
                y = 3 + (i - start) * 3
                frame.put(y, 2, title, 'selected_meta' if i == self.choice else 'heading', width - 4)
                frame.put(y + 1, 4, state['draft']['draft']['text'] or 'Unfinished wording / source input', 'body', width - 8)
            frame.put(height - 3, 2, '↑↓ choose · Enter open · d discard · Esc graph', 'accent', width - 4)
            frame.put(height - 2, 2, self.retention(), 'muted', width - 4)
            frame.put(height - 1, 2, getattr(self.terminal.app, 'recovery_error', None) or self.notice, 'warning', width - 4)
            return frame
        if mode == 'choose':
            frame.put(0, 2, 'MANUSCRIPT / FROM SELECTED SCIENCE', 'brand', width - 4)
            continuing = self.current_key in self.work.sessions
            rows = [('CURRENT REVIEW → ' + ('continue wording' if continuing else 'open wording'),
                     'Continue the same reviewed wording.' if continuing else 'New scope starts blank; earlier wording below stays separate.')]
            for index, key in enumerate(self.choices[1:], 1):
                state = self.work.sessions[key].state()
                rows.append(('RETAINED DRAFT ' + str(len(self.choices) - index) + ' / ' + state['work']['episode_id'],
                             state['draft']['draft']['text'] or state['work']['judgment']['text']))
            count = max(1, (height - 7) // 4)
            start = max(0, self.choice - count + 1)
            for n, (title, detail) in enumerate(rows[start:start + count], start):
                y = 3 + (n - start) * 4
                frame.put(y, 2, ('› ' if n == self.choice else '  ') + title, 'selected_meta' if n == self.choice else 'heading', width - 4)
                for i, line in enumerate(wrap(detail, width - 8)[:2]):
                    frame.put(y + 1 + i, 4, line, 'body', width - 8)
            frame.put(height - 3, 2, '↑↓ choose · Enter open · Esc merge', 'top_accent', width - 4)
            frame.put(height - 2, 2, self.retention(), 'top_muted', width - 4)
            frame.put(height - 1, 2, self.notice or f'{self.choice + 1}/{len(rows)} · Previous writing keeps its original basis', 'top_warning', width - 4)
            return frame
        frame.put(0, 2, 'MANUSCRIPT / ' + {'read': 'REVIEW', 'source': 'SOURCE FILE', 'wording': 'YOUR WORDING',
                                       'answer': 'YOUR EXPLANATION', 'complete': 'AI ORIGIN',
                                       'basis': 'SCIENTIFIC BASIS', 'reason': 'REUSE JUDGMENT REASON'}[mode] + recovery_copy(app, ' · SYNTHETIC WORK'), 'brand', width - 4)
        if mode in ('basis', 'reason'):
            rows = self.basis_lines() if mode == 'basis' else [
                ('REPLACE THIS EDITOR REASON?', 'heading'), (self.terminal.buffers[1].text, 'body'),
                ('WITH THE JUDGMENT REASON', 'heading'), (self.work.session.state()['work']['judgment']['rationale'], 'body'),
                ('Wording is unchanged. This edits only the buffer; undo remains available.', 'muted')]
            lines = [(line, style) for text, style in rows for line in wrap(text, width - 6)]
            self.scroll = min(self.scroll, max(0, len(lines) - height + 6))
            for i, (text, style) in enumerate(lines[self.scroll:self.scroll + height - 6]):
                frame.put(2 + i, 3, text, style, width - 6)
            frame.put(height - 3, 2, 'PgUp/PgDn read · Esc editor', 'top_accent', width - 4)
            frame.put(height - 2, 2, 'Ctrl+O returns to writing' if mode == 'basis' else 'Enter reuse · Esc cancel', 'top_accent', width - 4)
            frame.put(height - 1, 2, getattr(self.terminal.app, 'recovery_error', None) or self.retention(), 'top_muted', width - 4)
            return frame
        if mode in ('source', 'wording', 'answer'):
            fields = ('Read-only source path',) if mode == 'source' else ('Replacement wording', 'Reason / scope') if mode == 'wording' else ('What is established and what remains untested?',)
            start = 6 if mode == 'wording' else 2
            if mode == 'wording':
                item = self.work.session.state()['work']
                context = wrap('Judgment: ' + item['judgment']['text'], width - 6)
                if len(context) > 2:
                    context[1] = clip(context[1], width - 7, ellipsis=False).rstrip() + '…'
                for i, line in enumerate(context[:2]):
                    frame.put(1 + i, 3, line, 'body', width - 6)
                frame.put(3, 3, 'Reason: ' + item['judgment']['rationale'], 'muted', width - 6)
                frame.put(4, 3, 'Ctrl+R reuse reason · Ctrl+O full basis', 'accent', width - 6)
            h = (height - start - 4) // len(fields)
            for index, (field, buffer) in enumerate(zip(fields, self.terminal.buffers)):
                y = start + index * h
                frame.box(1, y, width - 2, h, field, index == self.terminal.field)
                rows, row, column = buffer.position(width - 8)
                offset = max(0, row - h + 3)
                for dy, (text, _, _) in enumerate(rows[offset:offset + h - 2]):
                    frame.put(y + 1 + dy, 3, text, 'body', width - 8)
                if index == self.terminal.field:
                    frame.cursor = y + 1 + row - offset, min(width - 4, 3 + column)
            hints = 'Tab field · Ctrl+S keep · Esc retain edit'
            actions = 'Enter inserts a line; returning keeps the editor buffer.'
            footer = self.terminal.buffers[self.terminal.field].notice or ('Review answers: session only' if mode == 'answer' else self.retention())
        else:
            content = self.lines() if mode == 'read' else [
                ('This wording or its scientific basis includes AI contributions.', 'body'),
                ('1 Explain the result and its limits', 'heading'),
                ('Reuse or revise your wording reason.', 'body'),
                ('2 Defer understanding', 'heading'),
                ('Understanding work would remain if accepted. This completes no pending work.', 'body')]
            from .tui import Buffer
            lines = []
            for text, style, *source_text in content:
                chunks = ([line for line, _, _ in Buffer(text).segments(width - 6)]
                          if source_text else wrap(text, width - 6))
                lines.extend((line, style) for line in chunks)
            for row in range(2, height - 3):
                frame.fill(row, 2, width - 4, 'body')
            self.scroll = min(self.scroll, max(0, len(lines) - height + 6))
            for row, (line, style) in enumerate(lines[self.scroll:self.scroll + height - 6]):
                frame.put(2 + row, 3, line, style, width - 6)
            hints = ('s source · e wording · R preview · Tab view'
                     if mode == 'read' else '1 explain · 2 defer · Esc preview')
            actions = 'Enter review · x not now · Esc work · PgUp/PgDn' if mode == 'read' else 'Review does not apply text or close pending work.'
            footer = self.retention()
        frame.put(height - 3, 2, hints, 'top_accent', width - 4)
        frame.put(height - 2, 2, actions, 'top_accent', width - 4)
        warning = getattr(self.terminal.app, 'recovery_error', None) or self.notice
        frame.put(height - 1, 2, warning or footer, 'top_warning' if warning else 'top_muted', width - 4)
        return frame


def manuscript_ui(terminal):
    if not hasattr(terminal, '_manuscript_ui'):
        terminal._manuscript_ui = ManuscriptUI(terminal)
    return terminal._manuscript_ui
