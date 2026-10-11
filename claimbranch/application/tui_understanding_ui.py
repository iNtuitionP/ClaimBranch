"""Return to causal science and unfinished explanation, never grade or close debt."""
from .tui_retention import recovery_copy
import unicodedata

from claimbranch.core.canonical import ContractError
from .paper_understanding import ENTRY
from .tui_work_recovery import enabled as encrypted_writing
from .tui_model import clip, wrap


TOPICS = {'claim-scope': 'Claim scope', 'evidence-interpretation': 'Evidence and interpretation',
          'followup-experiment': 'Follow-up experiment', 'manuscript-consequence': 'Manuscript consequence'}
VIEWS = ('explanation', 'original', 'current', 'draft basis', 'AI history')
TEXT_BYTES = ENTRY['properties']['text']['x-utf8-maxBytes']


def node_lines(node):
    content = node['content']
    rows = [(node['kind'].replace('-', ' ').upper() + ' / ' + node['id'], 'heading')]
    for label, key in (('Statement', 'statement'), ('Question', 'objective'), ('Question', 'question'),
                       ('Status', 'status'), ('Conditions', 'conditions'), ('Scope', 'scope'),
                       ('Recorded value', 'value'), ('Method', 'method')):
        if key in content:
            value = str(content[key])
            if key == 'value':
                value += ' ' + content.get('metric', {}).get('unit', '')
            rows.append((label + ': ' + value, 'evidence' if key == 'value' else 'body'))
    for key, value in content.get('metric', {}).items():
        rows.append(('Measurement ' + key + ': ' + value, 'body'))
    if node['kind'] == 'experiment-plan':
        rows.append(('Unrun plan; no measured result.', 'plan'))
    if node['kind'] == 'manuscript-anchor':
        rows.append(('Manuscript connection; exact source wording is not supplied here.', 'writing'))
    rows.append(('Source reference (not opened): ' + (content.get('source_ref') or 'not supplied'), 'muted'))
    return rows


class UnderstandingUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = self.scroll = 0
        self.view, self.notice, self.source_error = 'explanation', '', ''

    @property
    def work(self):
        return self.terminal.app.understanding

    def open(self, item):
        if item['kind'] != 'understanding':
            raise ContractError('Choose an explanation item; manuscript wording uses m.')
        self.work.open(item['id'])
        self.index = self.work.positions.get(item['id'], 0)
        self.scroll, self.view, self.notice = 0, 'explanation', ''
        self.terminal.modal = 'understanding-topics'

    def state(self):
        try:
            state = self.work.refresh()
            self.source_error = ''
            return state
        except (ContractError, ValueError) as error:
            self.source_error = 'Source unavailable; earlier context retained. ' + str(error)
            return self.work.session.state()

    def buffer_key(self, state):
        return self.work.work_id, state['topics'][self.index]['id']

    def retain_editor(self, state):
        buffer = self.terminal.buffers[0]
        if buffer.text != buffer.initial:
            key = self.buffer_key(state)
            if unicodedata.normalize('NFC', buffer.text) == state['draft']['entries'][self.index]['text']:
                self.work.buffers.pop(key, None)
            else:
                self.work.buffers[key] = buffer.text

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, ValueError, UnicodeError) as error:
            self.notice = str(error)

    def key(self, event):
        t, work = self.terminal, self.work
        mode = t.modal.removeprefix('understanding-')
        h, w = t.screen.getmaxyx()
        tiny = w < 48 or h < 18
        if event == 'escape':
            if mode == 'edit' or (mode == 'source' and tiny):
                self.retain_editor(work.session.state())
                t.buffers = []
                t.modal = 'understanding-read'
                self.notice = 'Unfinished input retained separately. e resumes; nothing completed.'
            elif mode == 'source':
                t.modal = 'understanding-edit'
            else:
                t.modal = {'topics': 'context-work-detail', 'read': 'understanding-topics',
                           'rebind': 'understanding-read'}[mode]
                self.notice = ''
            self.scroll = 0
            return
        if tiny:
            return
        state = self.state()
        topic, entry = state['topics'][self.index], state['draft']['entries'][self.index]
        if mode == 'edit':
            if event == 'source':
                self.view, self.scroll, t.modal = 'current', 0, 'understanding-source'
            elif event == 'keep':
                if len(unicodedata.normalize('NFC', t.buffers[0].text).encode('utf-8')) > TEXT_BYTES:
                    raise ContractError('This topic exceeds 16 KiB UTF-8. Shorten it; your input is retained.')
                work.session.edit(topic['id'], t.buffers[0].text)
                work.buffers.pop(self.buffer_key(state), None)
                t.buffers = []
                t.modal, self.view, self.scroll = 'understanding-read', 'explanation', 0
                self.notice = (recovery_copy(self.terminal.app, 'Explanation kept; included in encrypted checkpoints. The item remains open.') if encrypted_writing(t.app) else 'Explanation kept for this session; the item remains open.')
            else:
                t.buffers[0].key(event, max(2, self.editor_rect(w, h)[2] - 4))
            return
        if mode == 'topics':
            if event in ('up', 'k', 'down', 'j', 'home', 'end'):
                self.index = (0 if event == 'home' else len(state['topics']) - 1 if event == 'end'
                              else max(0, min(len(state['topics']) - 1, self.index + (-1 if event in ('up', 'k') else 1))))
                work.positions[work.work_id] = self.index
            elif event == 'enter':
                t.modal, self.view, self.scroll = 'understanding-read', 'explanation', 0
            return
        if event in ('up', 'k', 'down', 'j', 'page-up', 'page-down', 'home', 'end'):
            self.scroll = (0 if event == 'home' else 10**9 if event == 'end' else max(0, self.scroll +
                           {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -8, 'page-down': 8}[event]))
        elif mode == 'rebind':
            if event == 'enter':
                work.refresh()
                work.session.rebind_context(self.displayed_digest)
                t.modal, self.view, self.scroll = 'understanding-read', 'explanation', 0
                self.notice = 'Writing now uses the displayed basis. No review completed or item closed.'
        elif event in ('tab', 'backtab'):
            self.view = VIEWS[(VIEWS.index(self.view) + (1 if event == 'tab' else -1)) % len(VIEWS)]
            self.scroll = 0
        elif mode == 'source':
            if event == 'source':
                t.modal = 'understanding-edit'
        elif event in ('[', ']'):
            self.index = (self.index + (-1 if event == '[' else 1)) % len(state['topics'])
            work.positions[work.work_id] = self.index
            self.scroll, self.notice = 0, ''
        elif event == 'e':
            from .tui import Buffer
            t.buffers = [Buffer(work.buffers.get(self.buffer_key(state), entry['text']))]
            t.field, t.modal, self.notice = 0, 'understanding-edit', ''
        elif event == 'r':
            work.session.edit(topic['id'], entry['text'], reuse_rationale=not entry['reuse_rationale'])
            self.notice = 'Original reason ' + ('unlinked.' if entry['reuse_rationale'] else 'linked without copying or completing the answer.')
        elif event == 's':
            if self.source_error:
                self.notice = 'Current source unavailable; writing keeps its earlier basis.'
                return
            if state['context_current']:
                self.notice = 'Writing basis is already current.'
                return
            self.displayed_digest = state['context']['digest']
            self.rebind_state = state
            t.modal, self.scroll, self.notice = 'understanding-rebind', 0, ''

    @staticmethod
    def editor_rect(w, h):
        x = max(48, w * 2 // 5) if w >= 120 else 1
        top = 8 if w >= 120 else 9
        return x, top, w - x - 1, h - top - 4

    def science(self, state, view, topic):
        nodes = {node['id']: node for node in view['nodes']}
        rows = [('Episode ' + view['episode_id'] + ' / main / evidence revision ' + str(view['evidence_watermark']), 'muted')]
        for key in topic['node_ids']:
            rows += [('', 'body')]
            rows += node_lines(nodes[key]) if key in nodes else [(key + ': absent from this view.', 'warning')]
        relations = {edge.get('record_id'): edge for edge in view['relations']}
        for key in topic['relation_ids']:
            edge = relations.get(key)
            rows += [('', 'body')]
            if edge is None:
                rows += [(key + ': connection absent from this view.', 'warning')]
            else:
                rows += [('CONNECTION / ' + edge['source_id'] + ' ' + edge['type'] + ' → ' + edge['target_id'], 'heading'),
                         (edge.get('rationale') or 'No relation reason supplied.', 'body')]
        return rows

    def lines(self, state):
        topic, entry = state['topics'][self.index], state['draft']['entries'][self.index]
        context, item = state['context'], state['context']['work']
        rows = [(topic['prompt'], 'heading'), ('', 'body')]
        if self.view == 'explanation':
            rows += [('ORIGINAL JUDGMENT', 'heading'), (item['judgment']['text'], 'body'),
                     ('ORIGINAL REASON / ' + ('linked to this topic' if entry['reuse_rationale'] else 'r links this reason'), 'heading'),
                     (item['judgment']['rationale'], 'body'), ('', 'body'),
                     ('YOUR PARTIAL EXPLANATION', 'heading'), (entry['text'] or 'Not written yet; leaving this blank is allowed.', 'body')]
            if self.buffer_key(state) in self.work.buffers:
                rows += [('UNFINISHED EDIT / e resumes; kept text above is unchanged', 'warning')]
            rows += [('', 'body'), ('No answer is graded or marked complete. This conditional item remains open.', 'muted')]
            rows += [('Editor: 12,000 characters; kept text: 16 KiB UTF-8 per topic and 64 KiB encoded draft across topics.', 'muted')]
        elif self.view == 'AI history':
            for index, judgment in enumerate([item['judgment'], *item['source_judgments']]):
                label = ('THIS JUDGMENT / ' + item['cause_operation_id'] if index == 0 else 'SOURCE JUDGMENT ' + str(index))
                rows += [(label + ' / ' + judgment['episode_id'], 'heading')]
                if not judgment['history']:
                    rows += [('No contributions recorded.', 'muted')]
                for contribution in judgment['history']:
                    rows += [(contribution['contributor'].upper(), 'accent'), (contribution['text'], 'body'),
                             (contribution['rationale'] or 'No reason recorded at this step.', 'muted')]
        else:
            view = state['draft_basis'] if self.view == 'draft basis' else context[self.view]
            rows += self.science(state, view, topic)
        return rows

    def draw(self, frame):
        from .tui import Frame
        frame = Frame(frame.width, frame.height)
        w, h = frame.width, frame.height
        mode = self.terminal.modal.removeprefix('understanding-')
        state = self.state()
        if w < 48 or h < 18:
            frame.put(1, 1, 'Explanation controls paused', 'top_warning', w - 2)
            frame.put(3, 1, '48 x 18 needed. Esc retains and returns.', 'top_muted', w - 2)
            frame.put(h - 2, 1, 'Session only; no closure.', 'top_warning', w - 2)
            return frame
        topic = state['topics'][self.index]
        frame.put(0, 2, 'EXPLANATION / ' + state['context']['work']['episode_id'], 'brand', w - 4)
        frame.put(1, 2, (recovery_copy(self.terminal.app, 'encrypted recovery · ') if encrypted_writing(self.terminal.app) else 'SESSION ONLY · ') + ('AI origin retained' if state['source_ai_influenced'] else 'manual source'), 'top_warning', w - 4)
        status = ('CURRENT DRAFT BASIS' if state['context_current'] else 'EARLIER DRAFT BASIS / s inspects current context')
        if self.source_error:
            status = 'LAST AVAILABLE CONTEXT / writing basis retained'
        frame.put(2, 2, status, 'top_warning' if self.source_error or not state['context_current'] else 'top_muted', w - 4)
        item = state['context']['work']
        changes = ('evidence changed' if item['evidence_changed_since_merge'] else 'same evidence') + ' · ' + (
            'reasoning changed' if item['main_changed_since_merge'] else 'same reasoning')
        frame.put(3, 2, 'Since judgment: ' + changes, 'top_muted', w - 4)
        if mode == 'topics':
            y = 4
            for index, candidate in enumerate(state['topics']):
                chosen = self.index == index
                entry = state['draft']['entries'][index]
                text = ('› ' if chosen else '  ') + TOPICS[candidate['kind']]
                frame.put(y, 2, text, 'selected_meta' if chosen else 'heading', w - 4)
                detail = 'Partial writing retained' if entry['text'] or entry['reuse_rationale'] else 'No explanation written yet'
                if (self.work.work_id, candidate['id']) in self.work.buffers:
                    detail += ' / unfinished edit'
                frame.put(y + 1, 4, detail, 'muted', w - 6)
                y += 3
            footers = ['↑↓ topic · Enter read/write', 'Esc work · leaving keeps this item open']
        elif mode == 'edit':
            prompt = wrap(topic['prompt'], w - 4)
            if len(prompt) > 2:
                prompt[1] = clip(prompt[1], w - 5, ellipsis=False).rstrip() + '…'
            for row, line in enumerate(prompt[:2]):
                frame.put(4 + row, 2, line, 'heading', w - 4)
            x, y, width, height = self.editor_rect(w, h)
            frame.box(x, y, width, height, 'YOUR PARTIAL EXPLANATION', True)
            buffer = self.terminal.buffers[0]
            lines, row, column = buffer.position(width - 4)
            offset = max(0, row - height + 3)
            for n, (text, _, _) in enumerate(lines[offset:offset + height - 2]):
                frame.put(y + 1 + n, x + 2, text, 'body', width - 4)
            frame.cursor = y + 1 + row - offset, min(x + width - 2, x + 2 + column)
            if w >= 120:
                source = [('ORIGINAL JUDGMENT / Ctrl+O full context', 'heading'),
                          (state['context']['work']['judgment']['text'], 'body'),
                          ('ORIGINAL REASON', 'heading'), (state['context']['work']['judgment']['rationale'], 'body')]
                rows = [(line, style) for text, style in source for line in wrap(text, x - 5)]
                for n, (text, style) in enumerate(rows[:h - 12]):
                    frame.put(8 + n, 2, text, style, x - 5)
            else:
                summary = wrap('Original judgment: ' + state['context']['work']['judgment']['text'], w - 4)
                if len(summary) > 2:
                    summary[1] = clip(summary[1], w - 5, ellipsis=False).rstrip() + '…'
                for n, text in enumerate(summary[:2]):
                    frame.put(6 + n, 2, text, 'body', w - 4)
            frame.put(7 if w >= 120 else 8, 2, 'Original reason ' + ('linked' if state['draft']['entries'][self.index]['reuse_rationale'] else 'not linked') + ' · Ctrl+O source', 'top_accent', w - 4)
            size = len(unicodedata.normalize('NFC', buffer.text).encode('utf-8'))
            footers = ['Ctrl+S keep · Ctrl+O source · Esc retain', f'{len(buffer.text):,}/12,000 chars · {size:,}/{TEXT_BYTES:,} B']
        else:
            if mode == 'rebind':
                shown = self.rebind_state
                rows = [('UPDATE WRITING BASIS / text remains unchanged', 'heading'),
                        ('This affects every explanation topic in this item; it completes no review.', 'warning')]
                for selected in shown['topics']:
                    rows += [(TOPICS[selected['kind']] + ' / EARLIER BASIS', 'heading')]
                    rows += self.science(shown, shown['draft_basis'], selected)
                    rows += [('CURRENT SCIENCE', 'heading')]
                    rows += self.science(shown, shown['context']['current'], selected)
                footers = ['Enter use displayed basis · Esc cancel', 'PgUp/PgDn read · no review or closure']
            else:
                label = 'LAST AVAILABLE' if self.source_error and self.view == 'current' else self.view.upper()
                rows = [(TOPICS[topic['kind']] + ' / ' + label, 'accent'), *self.lines(state)]
                footers = (['Tab view · PgUp/PgDn read', 'Esc / Ctrl+O return to editor'] if mode == 'source' else
                           ['e write · r reuse reason · Tab view', '[ ] topic · s update basis · Esc topics'])
            lines = [(line, style) for text, style in rows for line in wrap(text, w - 6)]
            count = h - 9
            self.scroll = min(self.scroll, max(0, len(lines) - count))
            for i, (text, style) in enumerate(lines[self.scroll:self.scroll + count]):
                frame.put(4 + i, 3, text, style, w - 6)
            frame.put(h - 4, 2, f'{self.scroll + 1}–{min(len(lines), self.scroll + count)} / {len(lines)} · PgUp/PgDn read', 'top_muted', w - 4)
        for i, text in enumerate(footers):
            frame.put(h - 3 + i, 2, text, 'top_accent', w - 4)
        warning = getattr(self.terminal.app, 'recovery_error', None) or self.source_error or self.notice or (self.terminal.buffers[0].notice if mode == 'edit' else '')
        if not warning and mode == 'rebind' and self.rebind_state['context']['digest'] != state['context']['digest']:
            warning = 'Context changed. Esc, then s to inspect again.'
        frame.put(h - 1, 2, warning or ('Unaccepted · explanation remains open' if encrypted_writing(self.terminal.app) else 'Unaccepted · no checkpoint or closure'), 'top_warning' if warning else 'top_muted', w - 4)
        return frame


def understanding_ui(terminal):
    if not hasattr(terminal, '_understanding_ui'):
        terminal._understanding_ui = UnderstandingUI(terminal)
    return terminal._understanding_ui
