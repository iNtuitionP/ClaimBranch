"""Manual reasoning construction, bound to an explicit existing-node work."""
from .tui_retention import recovery_copy
from copy import deepcopy

from .tui_work_recovery import enabled as encrypted_writing
from claimbranch.core.canonical import ContractError
from .tui_model import TerminalWorkspace, wrap
from .tui_review import EDIT_FIELDS, FIELD_LABELS as LABELS


FORM_FIELDS = {'claim': ('role', 'parent_ids', 'statement', 'scope'),
               'scientific-edge': ('source_id', 'target_id', 'edge_type', 'rationale'),
               'interpretation': ('statement', 'observation_ids'),
               'experiment-plan': ('claim_id', 'objective', 'conditions', 'metric.name',
                                   'metric.definition', 'metric.unit', 'metric.comparison')}


def field_value(body, field):
    """Address a form field without flattening the canonical metric record."""
    for part in field.split('.'):
        body = body[part]
    return body


def set_field(body, field, value):
    parts = field.split('.')
    for part in parts[:-1]:
        body = body[part]
    body[parts[-1]] = value


class CandidatesUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = 0
        self.notice = ''
        self.owner_key = None

    @property
    def app(self):
        return self.terminal.app

    @property
    def work(self):
        return self.app.review.candidate_works[self.owner_key]

    @property
    def inputs(self):
        return self.app.review.candidate_inputs.setdefault(self.owner_key, {})

    def open(self, mode):
        self.index, self.notice = 0, ''
        self.terminal.modal = 'candidate-' + mode

    def enter(self, action):
        if action == 'owners':
            self.owners = [key for key, work in self.app.review.candidate_works.items()
                           if work.records or self.app.review.candidate_inputs.get(key)]
            self.open('owners')
            return
        self.owner_key = self.app.review.key
        self.app.review.candidates()
        if action in ('claim', 'scientific-edge', 'experiment-plan', 'interpretation'):
            self.new(action)
        else:
            self.open('list')

    def owner_text(self, key=None):
        owner = self.app.review.candidate_works[key or self.owner_key].owner
        if (self.app.episode_id, self.app.ref) == owner[:2]:
            node = self.app.nodes[owner[2]]
        else:
            view = self.app.paper.service.query(owner[1], episode_id=owner[0])
            node = next(item for item in view['nodes'] if item['id'] == owner[2])
        content = node['content']
        return owner[0] + ' / ' + owner[1] + ' / ' + (content.get('statement') or content.get('objective') or content.get('question') or owner[2])

    def new(self, kind):
        if len(set(self.inputs) | set(self.work.records)) >= 64:
            raise ContractError('Work holds at most 64 candidates/unfinished forms; remove one before adding.')
        if kind == 'interpretation':
            from .paper_candidates import interpretation_unavailable
            reason = interpretation_unavailable(self.app.paper, self.work.owner,
                [*self.work.records.values(), *self.inputs.values()])
            if reason:
                raise ContractError(reason)
        body = {'claim': {'role': '', 'parent_ids': [], 'statement': '', 'scope': ''},
                'interpretation': {'statement': '', 'observation_ids': []},
                'scientific-edge': {'source_id': '', 'target_id': '', 'edge_type': '', 'rationale': ''},
                'experiment-plan': {'claim_id': '', 'objective': '', 'status': 'planned', 'conditions': '',
                                    'metric': {'name': '', 'definition': '', 'unit': '', 'comparison': ''}}}[kind]
        self.record = {'id': self.work.allocate_id(), 'kind': kind, 'body': body}
        self.fields = FORM_FIELDS[kind]
        self.open('form')

    def retain(self):
        # Browsing a pristine form creates no pending text.
        prior = self.work.records.get(self.record['id'])
        blank = all(not field_value(self.record['body'], field) for field in FORM_FIELDS[self.record['kind']])
        if self.record == prior:
            self.inputs.pop(self.record['id'], None)
        elif prior is not None or not blank or self.record['id'] in self.inputs:
            self.inputs[self.record['id']] = deepcopy(self.record)

    def items(self):
        return {**self.work.records, **self.inputs}

    def nodes(self):
        binding = (self.work, self.app.paper.history, self.work.revision)
        if getattr(self, '_nodes_binding', None) == binding:
            return self._nodes_cache
        episode, ref, _ = self.work.owner
        source = self.app.paper.service.query(ref, episode_id=episode)['nodes']
        nodes = {node['id']: node for node in source}
        for record in self.work.records.values():
            if record['kind'] in ('claim', 'experiment-plan', 'interpretation'):
                nodes[record['id']] = {'id': record['id'], 'kind': record['kind'], 'content': record['body'], 'draft': True}
        self._nodes_binding, self._nodes_cache = binding, nodes
        return nodes

    def node_text(self, key):
        node = self.nodes().get(key)
        if not node:
            return 'Choose a record' if not key else 'Missing endpoint / repair this choice'
        text = node['content'].get('statement') or node['content'].get('objective') or node['content'].get('question') or key
        alias = self.app.node_label(key) + ' ' if key in self.app.nodes else self.work.alias(key) + ' '
        return alias + ('DRAFT / ' if node.get('draft') else '') + text

    def record_text(self, record):
        body = record['body']
        if record['kind'] == 'scientific-edge':
            return self.node_text(body['source_id']) + ' ' + (body['edge_type'] or '?') + ' → ' + self.node_text(body['target_id'])
        if record['kind'] == 'experiment-plan':
            target = body['claim_id']
            endpoint = (self.app.node_label(target) if target in self.app.nodes else self.work.alias(target)) if target in self.nodes() else self.node_text(target)
            return 'Tests ' + endpoint + ' · ' + (body['objective'] or 'Unfinished plan')
        return body.get('statement') or ('Unfinished interpretation' if record['kind'] == 'interpretation' else 'Unfinished claim')

    def field_text(self, field):
        value = field_value(self.record['body'], field)
        if field == 'observation_ids':
            return ' / '.join(self.node_text(key) for key in value) or 'No observations linked. Choose explicitly; this is not confirmed evidence.'
        if field == 'parent_ids':
            return ' / '.join(self.node_text(key) for key in value) or 'Choose a parent; this is hierarchy, not support.'
        if field in ('source_id', 'target_id', 'claim_id'):
            return self.node_text(value)
        return value or 'Not written yet'

    def field_label(self, field):
        if field == 'statement' and self.record['kind'] == 'interpretation':
            return 'Interpretation statement'
        return LABELS.get(field, field)

    def dependencies(self, key):
        # Include both kept and unfinished references; neither version vanishes.
        return self.work.dependent_ids(list(self.work.records.values()) + list(self.inputs.values()), key)

    def edit_field(self):
        from .tui import Buffer
        self.editing = self.fields[self.index]
        self.form_index = self.index
        body, field = self.record['body'], self.editing
        nodes = self.nodes()
        if field == 'role':
            self.choices = [('main', 'Main claim under the thesis'), ('subclaim', 'Subclaim under another claim')]
        elif field == 'edge_type':
            self.choices = [(value, value.capitalize() + ' the target claim') for value in ('supports', 'challenges', 'qualifies')]
        elif field == 'observation_ids':
            self.choices = [(key, self.node_text(key) + ' / ' + node['content']['status'])
                            for key, node in nodes.items() if node['kind'] == 'observation']
            self.picked = set(body[field])
        elif field in ('parent_ids', 'source_id', 'target_id', 'claim_id'):
            if field == 'parent_ids' and not body['role']:
                raise ContractError('Choose the claim level first, then its parent.')
            def eligible(node):
                if node['id'] == self.record['id']:
                    return False
                if field == 'parent_ids':
                    return node['kind'] == 'claim' and ((node['content']['role'] == 'thesis') == (body['role'] == 'main'))
                if field == 'source_id':
                    return node['kind'] in ('claim', 'interpretation', 'observation')
                return node['kind'] == 'claim' and node['id'] != body.get('source_id')
            self.choices = [(key, self.node_text(key)) for key, node in nodes.items() if eligible(node)]
        else:
            self.terminal.buffers, self.terminal.field = [Buffer(field_value(body, field) or '')], 0
            self.open('text')
            return
        self.open('pick')
        current = field_value(body, field)
        if field == 'parent_ids':
            current = current[0] if current else None
        self.index = next((i for i, choice in enumerate(self.choices) if choice[0] == current), 0)

    def graph_open(self):
        projection = self.project()
        self.source_ai = projection['source_ai_influenced']
        self.source_ai |= any(origin.ai_influenced for origin in self.work.origins.values())
        episode, ref, node = self.work.owner
        base = self.app.paper.service.query(ref, episode_id=episode)
        graph = TerminalWorkspace(self.app.paper.history, ai_off=not self.app.paper.ai_available)
        graph.ref, graph.view = ref, {**base, **projection['graph']}
        graph.nodes = {item['id']: item for item in graph.view['nodes']}
        graph.projection_only = True
        # Original aliases must not change merely because draft IDs sort earlier.
        graph._label_overrides = {key: self.app.node_label(key) for key in self.app.nodes if key in graph.nodes}
        for key, item in self.work.records.items():
            if key not in graph._label_overrides and key in graph.nodes:
                graph._label_overrides[key] = self.work.alias(key)
        graph.graph_spacing, graph.density = self.app.graph_spacing, self.app.density
        graph._build_outline()
        graph.selected_id, graph.selected_path = node, graph._paths[node]
        self.graph = graph
        self.open('graph')

    def project(self):
        for key, record in self.work.records.items():
            missing = [('Interpretation statement' if field == 'statement' and record['kind'] == 'interpretation' else LABELS[field]) for field in FORM_FIELDS[record['kind']]
                       if field != 'observation_ids' and (not field_value(record['body'], field) or
                       (isinstance(field_value(record['body'], field), str) and not field_value(record['body'], field).strip()))]
            if missing:
                raise ContractError(self.app.review.label(key) + ' needs: ' + ', '.join(missing) + '. Enter edits; d removes the draft.')
        return self.work.project()

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, ValueError) as error:
            self.notice = str(error)
            self.app.message = str(error)

    def observation_lines(self):
        node = self.observation
        content, metric = node['content'], node['content'].get('metric', {})
        return [self.app.node_label(node['id']) + ' / ' + content['statement'],
                'Status: ' + content['status'],
                'Value: ' + str(content.get('value', 'Not supplied')) + ' ' + metric.get('unit', ''),
                'Conditions: ' + content.get('conditions', 'Not supplied'),
                'Measurement: ' + metric.get('name', 'Not supplied'),
                'Definition: ' + metric.get('definition', 'Not supplied'),
                'Comparison: ' + metric.get('comparison', 'Not supplied'),
                'Source reference (not opened): ' + content.get('source_ref', 'Not supplied')]

    @staticmethod
    def require_reusable(record, draft):
        for label, text in (('interpretation', record['body']['statement']), ('reason', draft['rationale'])):
            if len(text) > 12000 or len(text.encode('utf-8')) > 16384:
                raise ContractError('Shorten the ' + label + ' to 12,000 characters / 16,384 UTF-8 bytes before reuse. Existing judgment retained.')

    def key(self, event):
        t, mode = self.terminal, self.terminal.modal.removeprefix('candidate-')
        if event == 'escape':
            if mode == 'observation':
                self.open('pick')
                self.index = self.observation_index
            elif mode == 'text':
                if t.buffers[0].text != t.buffers[0].initial:
                    set_field(self.record['body'], self.editing, t.buffers[0].text)
                self.retain()
                self.open('form')
                self.index = self.form_index
            elif mode == 'pick':
                self.open('form')
                self.index = self.form_index
            elif mode == 'form':
                self.retain()
                self.open('list')
            elif mode in ('graph', 'remove', 'source', 'judgment'):
                if mode == 'graph' and self.graph.focus != 'outline':
                    self.graph.focus, self.graph.scroll = 'outline', 0
                    self.graph.reading_relation = False
                else:
                    self.open('list')
                    if mode == 'judgment':
                        self.index = self.return_index
            else:
                t.modal = None
            return
        height, width = t.screen.getmaxyx()
        if width < 48 or height < 18:
            return
        if mode == 'text':
            if event == 'keep':
                self.key('escape')
            else:
                t.buffers[0].key(event, width - 8)
            return
        if mode == 'graph':
            return self.graph_key(event)
        if mode in ('remove', 'source', 'judgment', 'observation') and event in ('up', 'down', 'page-up', 'page-down'):
            self.index = max(0, self.index + (-1 if event == 'up' else 1 if event == 'down' else -8 if event == 'page-up' else 8))
            return
        if mode == 'observation':
            return
        if mode == 'judgment':
            if event == 'enter':
                self.work.require_current()
                if (self.reuse_record != self.work.records.get(self.reuse_record['id'])
                        or self.app.review.key != self.owner_key
                        or self.reuse_draft != self.app.draft()
                        or self.reuse_revision != self.work.session.state()['revision']):
                    raise ContractError('Work changed. Cancel and inspect the interpretation and judgment again.')
                self.require_reusable(self.reuse_record, self.reuse_draft)
                self.app.keep_draft(self.reuse_record['body']['statement'], self.reuse_draft['rationale'])
                self.open('list')
                self.index = self.return_index
                self.notice = 'Interpretation reused as this work\'s judgment. Reason retained; review again.'
            return
        length = (len(self.owners) if mode == 'owners' else len(self.fields) if mode == 'form' else
                  len(self.choices) if mode == 'pick' else len(self.items()))
        if event in ('up', 'k', 'down', 'j', 'home', 'end', 'page-up', 'page-down'):
            self.index = (0 if event == 'home' else max(0, length - 1) if event == 'end' else
                          max(0, min(length - 1, self.index + {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -5, 'page-down': 5}[event])))
            self.notice = ''
            return
        if mode == 'owners' and event == 'enter' and self.owners:
            self.owner_key = self.owners[self.index]
            self.app.open_work_key(self.owner_key)
            self.open('list')
        elif mode == 'form':
            if event == 'enter':
                self.edit_field()
            elif event == 'keep':
                self.work.put(self.record)
                self.inputs.pop(self.record['id'], None)
                self.open('list')
                self.index = list(self.items()).index(self.record['id'])
                try:
                    self.project()
                    self.notice = (recovery_copy(self.app, 'Draft kept; included in encrypted checkpoints. g shows the graph.') if encrypted_writing(self.app) else 'Draft kept for this session. g shows the draft graph.')
                except ContractError as error:
                    self.notice = 'Draft kept. Graph unavailable: ' + str(error)
        elif mode == 'pick':
            if self.editing == 'observation_ids' and event == 'r' and self.choices:
                self.observation_index = self.index
                self.observation = deepcopy(self.nodes()[self.choices[self.index][0]])
                self.open('observation')
            elif self.editing == 'observation_ids' and event == ' ' and self.choices:
                value = self.choices[self.index][0]
                self.picked.symmetric_difference_update({value})
            elif event == 'enter' and (self.choices or self.editing == 'observation_ids'):
                if self.editing == 'observation_ids':
                    value = sorted(self.picked)
                else:
                    value = self.choices[self.index][0]
                self.record['body'][self.editing] = [value] if self.editing == 'parent_ids' else value
                self.retain()
                self.open('form')
                self.index = self.form_index
        elif mode == 'remove':
            if event in ('1', '2'):
                ids = {self.remove_id, *(self.dependencies(self.remove_id) if event == '2' else [])}
                for key in ids:
                    if key in self.work.records:
                        self.work.remove(key)
                    self.inputs.pop(key, None)
                    self.work.discard_identity(key)
                self.open('list')
                self.notice = 'Removed from this work. Any retained dependent draft needs repair.'
        elif mode == 'source' and event == 'enter':
            self.work.refresh_source(expected_changes=self.refresh_changes, unfinished=list(self.inputs.values()))
            self.open('list')
            self.notice = 'Source refreshed. Retained draft values may replace newer source values; inspect final review.'
        elif mode == 'list':
            records = self.items()
            self.index = min(self.index, max(0, len(records) - 1))
            key = list(records)[self.index] if records else None
            if event == 'n':
                self.new('claim')
            elif event == 'l':
                self.new('scientific-edge')
            elif event == 'p':
                self.new('experiment-plan')
            elif event == 'i':
                self.new('interpretation')
            elif key and event == 'J':
                record = self.work.records.get(key)
                if not record and records[key]['kind'] == 'interpretation':
                    raise ContractError('Keep this interpretation first: Enter edits the form; Ctrl+S keeps it.')
                if not record or record['kind'] != 'interpretation' or key in self.app.review.records():
                    raise ContractError('Choose a kept new interpretation. Existing source text keeps its own provenance; edit your judgment in Work.')
                if self.inputs.get(key):
                    raise ContractError('Keep or discard the unfinished interpretation edits before reusing its wording.')
                if not record['body']['statement'].strip():
                    raise ContractError('Write the interpretation before reusing it as a judgment.')
                self.work.require_current()
                if self.app.review.key != self.owner_key:
                    raise ContractError('Return to this owning work before reusing its interpretation.')
                self.return_index = self.index
                self.reuse_record, self.reuse_draft = record, self.app.draft()
                self.require_reusable(record, self.reuse_draft)
                self.reuse_revision = self.work.session.state()['revision']
                self.open('judgment')
            elif event == 'g':
                self.graph_open()
            elif event == 'b':
                self.app.open_work_key(self.owner_key)
                t.modal = None
                t.key('w')
            elif event == 's':
                self.refresh_changes = self.work.source_changes(list(self.inputs.values()))
                if self.refresh_changes:
                    self.open('source')
                else:
                    self.work.refresh_source()
                    self.notice = 'Source binding refreshed. Drafts retained; validate graph and review again.'
            elif event == 'R':
                self.app.open_work_key(self.owner_key)
                self.app.review.prepare_changes()
                t.modal = None
                t.key('w')
            elif key and event == 'enter':
                self.record = deepcopy(records[key])
                self.fields = (EDIT_FIELDS if key in self.app.review.records() else FORM_FIELDS)[self.record['kind']]
                self.open('form')
            elif key and event == 'u':
                if key in self.work.records:
                    kept = self.work.unkeep(key)
                    self.inputs.setdefault(key, kept)
                self.notice = 'Retained as unfinished text; excluded from graph/review. Dependent kept drafts may need repair.'
            elif key and event == ' ':
                self.work.toggle(key)
            elif key and event == 'd':
                self.remove_id = key
                self.open('remove')

    def graph_key(self, event):
        from .tui_graph import move_graph
        graph = self.graph
        self.work.require_current()
        if event == 'enter':
            if graph.focus == 'links' and graph.links():
                graph.select(graph.links()[graph.link_index].target_id)
            graph.open_view(mode='detail')
        elif event == 'tab' and graph.focus == 'links':
            graph.reading_relation = True
            graph.open_view(mode='detail')
        elif event == 'r':
            graph.focus, graph.link_index = 'links', 0
            graph.reading_relation = False
        elif event == 'f':
            graph.fit_graph()
        elif event in ('up', 'down', 'left', 'right', 'j', 'k'):
            if graph.focus == 'links':
                graph.link_index = max(0, min(len(graph.links()) - 1, graph.link_index + (-1 if event in ('up', 'k') else 1)))
            elif graph.focus == 'detail':
                graph.scroll = max(0, graph.scroll + (-1 if event in ('up', 'k') else 1))
            else:
                move_graph(graph, {'j': 'down', 'k': 'up'}.get(event, event))
        elif event in ('page-up', 'page-down'):
            graph.scroll = max(0, graph.scroll + (-8 if event == 'page-up' else 8))
        elif event in ('H', 'J', 'K', 'L'):
            dx, dy = {'H': (-8, 0), 'J': (0, 4), 'K': (0, -4), 'L': (8, 0)}[event]
            graph.graph_pan = graph.graph_pan[0] + dx, graph.graph_pan[1] + dy
            graph.graph_follow = False

    def draw(self, frame):
        from .tui import Frame, compose
        t, mode = self.terminal, self.terminal.modal.removeprefix('candidate-')
        w, h = frame.width, frame.height
        frame = Frame(w, h)
        if w < 48 or h < 18:
            frame.put(1, 1, 'Authoring paused', 'top_warning', w - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Esc retains text.', 'top_muted', w - 2)
            return frame
        if mode == 'graph':
            try:
                self.work.require_current()
            except ContractError as error:
                frame.put(2, 2, str(error), 'warning', w - 4)
                frame.put(h - 2, 2, 'Esc to work, then s refreshes source.', 'accent', w - 4)
                return frame
            frame = compose(self.graph, w, h)
            frame.fill(1, 0, w, 'canvas')
            frame.put(1, 2, (recovery_copy(self.app, 'DRAFT GRAPH / encrypted draft recovery') if encrypted_writing(self.app) else 'DRAFT GRAPH / all kept candidates · session only'), 'top_warning', w - 4)
            frame.fill(2, 0, w, 'canvas')
            episode, ref, node = self.work.owner
            frame.put(2, 2, 'Owner ' + self.graph.node_label(node) + ' / ' + episode + ' / ' + ref + ' · current global evidence', 'top_muted', w - 4)
            if h >= 36:
                frame.fill(3, 0, w, 'canvas')
                frame.put(3, 2, 'Kept reasoning drafts · unkept forms excluded · plans are unrun', 'top_muted', w - 4)
            for y in range(h - 3, h):
                frame.fill(y, 0, w, 'canvas')
            frame.put(h - 3, 2, 'Arrows · Enter read/follow · r links · Tab reason', 'top_accent', w - 4)
            frame.put(h - 2, 2, 'Esc ' + ('map' if self.graph.focus != 'outline' else 'owning work') + ' · edit candidates in owning work', 'top_muted', w - 4)
            frame.put(h - 1, 2, 'Not accepted · f fit · HJKL pan' + (' · source AI influence retained' if self.source_ai else ''), 'top_warning', w - 4)
            return frame
        x, measure = (3, w - 6) if w < 100 else ((w - 96) // 2, 96)
        kind = getattr(self, 'record', {}).get('kind')
        titles = {'owners': 'RETURN TO AUTHORED WORK', 'list': 'YOUR ARGUMENT DRAFTS',
                  'form': {'claim': 'WRITE A CLAIM', 'interpretation': 'WRITE AN INTERPRETATION', 'experiment-plan': 'PLAN A FOLLOW-UP / UNRUN'}.get(kind, 'WRITE A SCIENTIFIC CHANGE'),
                  'pick': self.field_label(getattr(self, 'editing', 'CHOOSE')).upper() if hasattr(self, 'record') else 'CHOOSE',
                  'text': self.field_label(getattr(self, 'editing', 'WRITE')).upper() if hasattr(self, 'record') else 'WRITE', 'remove': 'REMOVE CANDIDATE?',
                  'source': 'SOURCE CHANGED / COMPARE RETAINED DRAFTS',
                  'observation': 'READ OBSERVATION / READ ONLY',
                  'judgment': 'USE INTERPRETATION AS JUDGMENT?'}
        frame.put(0, x, titles[mode], 'brand', measure)
        frame.put(1, x, (getattr(self.app, 'recovery_error', None) or recovery_copy(self.app, 'DRAFT / encrypted recovery · NOT ACCEPTED')) if encrypted_writing(self.app) else 'DRAFT / SESSION ONLY · NOT ACCEPTED', 'top_warning', measure)
        origin = ((self.work.origins.get(self.record['id']) or self.app.paper.origin_for(self.record['id'])) if mode in ('form','text') else None)
        if origin and origin.ai_influenced:
            frame.put(1,x,'AI ITEM ORIGIN RETAINED / human edits do not erase its source','top_warning',measure)
        if mode != 'owners':
            for row, text in enumerate(wrap('Owning work: ' + self.owner_text(), measure)[:2]):
                frame.put(2 + row, x, text, 'top_muted', measure)
        if kind == 'experiment-plan' and mode in ('form', 'text', 'pick'):
            frame.put(4, x, 'UNRUN PLAN · no measured result', 'top_warning', measure)
        if mode == 'text':
            buffer = t.buffers[0]
            frame.box(x, 5, measure, h - 9, self.field_label(self.editing), True)
            rows, row, column = buffer.position(measure - 6)
            offset = max(0, row - (h - 12))
            for number, (text, _, _) in enumerate(rows[offset:offset + h - 11]):
                frame.put(6 + number, x + 2, text, 'body', measure - 6)
            frame.cursor = 6 + row - offset, min(w - 4, x + 2 + column)
            footer = 'Esc or Ctrl+S returns to form · Enter new line'
            detail = buffer.notice or f'{len(buffer.text)}/12000 chars · {len(buffer.text.encode("utf-8"))}/16384 UTF-8 bytes'
        elif mode == 'observation':
            wrapped = [line for text in self.observation_lines() for line in wrap(text, measure)]
            self.index = min(self.index, max(0, len(wrapped) - h + 12))
            for row, line in enumerate(wrapped[self.index:self.index + h - 12]):
                frame.put(5 + row, x, line, 'body', measure)
            footer, detail = '↑↓ / PgUp/PgDn read · Esc observations', 'Reading changes no choices or evidence.'
        elif mode == 'judgment':
            lines = ['Kept interpretation: ' + self.reuse_record['body']['statement'],
                     'Current judgment: ' + (self.reuse_draft['text'] or 'Not written yet'),
                     'Reason retained: ' + (self.reuse_draft['rationale'] or 'Not written yet'),
                     'Your earlier AI contributions remain. This edit invalidates review and any pending AI reply.',
                     'No accepted science changes. Other judgments and unfinished writing remain separate.']
            wrapped = [line for text in lines for line in wrap(text, measure)]
            self.index = min(self.index, max(0, len(wrapped) - h + 12))
            for row, line in enumerate(wrapped[self.index:self.index + h - 12]):
                frame.put(5 + row, x, line, 'body', measure)
            footer, detail = '↑↓ / PgUp/PgDn read · Enter reuse · Esc cancel', 'Replace only this work\'s judgment text. Keep its reason.'
        elif mode == 'source':
            lines = ['The source changed after this writing began. Retaining these draft values can propose reversing newer source values.',
                     'Enter keeps your draft values against this source. Esc leaves the old binding and text intact.']
            for change in self.refresh_changes:
                lines.append(self.app.review.label(change['id']) + ' / ' + change['layer'])
                current = change['current'] or {}
                for field in sorted(set(change['previous']) | set(current)):
                    if change['previous'].get(field) != current.get(field):
                        lines += [LABELS.get(field, field), 'Previous source: ' + str(change['previous'].get(field)),
                                  'Current source: ' + str(current.get(field)), 'Your draft: ' + str(change['candidate'].get(field))]
            wrapped = [line for text in lines for line in wrap(text, measure)]
            self.index = min(self.index, max(0, len(wrapped) - h + 12))
            for row, line in enumerate(wrapped[self.index:self.index + h - 12]):
                frame.put(5 + row, x, line, 'body', measure)
            footer, detail = '↑↓ / PgUp/PgDn read · Enter retain drafts · Esc cancel', 'Refresh grants no acceptance. Review must be prepared again.'
        elif mode == 'remove':
            deps = self.dependencies(self.remove_id)
            lines = ['Remove: ' + self.record_text(self.items()[self.remove_id]),
                     'This removes draft text, not an accepted record.',
                     '1 Remove only this draft; keep dependents for repair.',
                     '2 Remove this draft and the listed dependent drafts.']
            lines += ['Dependent: ' + self.record_text(self.items()[key]) for key in deps]
            # Full dependent inventory is scrollable before an explicit choice.
            wrapped = [line for text in lines for line in wrap(text, measure)]
            self.index = min(self.index, max(0, len(wrapped) - h + 12))
            for row, line in enumerate(wrapped[self.index:self.index + h - 12]):
                frame.put(5 + row, x, line, 'body', measure)
            footer, detail = '1 remove only · 2 remove listed · Esc cancel', f'{len(deps)} dependent drafts · ↑↓ read'
        else:
            if mode == 'owners':
                items = [('Work / ' + str(i + 1), self.owner_text(key)) for i, key in enumerate(self.owners)]
                footer, detail = '↑↓ choose · Enter return to work · Esc map', 'Candidate fields stay with their original work.'
            elif mode == 'form':
                items = [(self.field_label(field), self.field_text(field)) for field in self.fields]
                footer, detail = f'{self.index + 1}/{len(self.fields)} · ↑↓ field · Enter edit · Ctrl+S keep · Esc retain', 'Incomplete writing is allowed; graph/review require valid fields.'
            elif mode == 'pick':
                multiple = self.editing == 'observation_ids'
                items = [((('[x] ' if key in self.picked else '[ ] ') + self.app.node_label(key) + ' / ' + self.nodes()[key]['content']['status'],
                           self.nodes()[key]['content']['statement']) if multiple else (text, '')) for key, text in self.choices]
                footer = '↑↓ choose · Space toggle · Enter use · Esc cancel · r read' if multiple else '↑↓ choose · Enter use · Esc form'
                detail = (f'{len(self.picked)} observations linked · No selection is allowed; no evidence is invented.'
                          if multiple else 'Choose explicitly. No scientific connection is inferred.')
            else:
                items = []
                for key, record in self.items().items():
                    status = ('SELECTED' if key in self.work.selected else 'OMITTED') if key in self.work.records else 'UNKEPT FORM'
                    if key in self.inputs and key in self.work.records:
                        status += ' · UNKEPT EDITS'
                    kind_label = 'UNRUN PLAN' if record['kind'] == 'experiment-plan' else record['kind'].upper()
                    items.append((status + ' / ' + kind_label, self.record_text(record)))
                footer = 'Enter edit · n claim · i interpretation · l link · p plan · g graph · Esc map'
                selected = list(self.items().values())[min(self.index, len(items) - 1)] if items else None
                if selected and selected['kind'] == 'interpretation':
                    footer = 'Enter edit · J reuse as judgment · g graph · Esc map'
                detail = 'Space select · d remove · u unkeep\nb judgment · R reviews kept · s refresh'
            visible = max(1, (h - 12) // 3)
            offset = max(0, self.index - visible + 1)
            for row, (label, text) in enumerate(items[offset:offset + visible]):
                active, y = row + offset == self.index, 5 + row * 3
                frame.fill(y, x, measure, 'selected' if active else 'body')
                frame.put(y, x, ('› ' if active else '  ') + label, 'selected_meta' if active else 'heading', measure)
                preview = wrap(text, measure - 3)
                for line, value in enumerate(preview[:2]):
                    frame.put(y + 1 + line, x + 3, value, 'body', measure - 3)
            if not items:
                frame.put(5, x, 'No drafts yet. n claim; i interpretation; l link; p plan.' if mode == 'list' else 'No available choices.', 'body', measure)
        if self.notice:
            # Errors remain readable on narrow terminals, with field text intact.
            for row, line in enumerate(wrap(self.notice, measure)[:2]):
                frame.fill(h - 6 + row, x, measure, 'canvas')
                frame.put(h - 6 + row, x, line, 'top_warning', measure)
        for row, line in enumerate(wrap(footer, measure)[:2]):
            frame.put(h - 4 + row, x, line, 'top_accent', measure)
        for row, line in enumerate(wrap(detail, measure)[:2]):
            frame.put(h - 2 + row, x, line, 'top_muted', measure)
        return frame


def candidates_ui(terminal):
    if not hasattr(terminal, '_candidates_ui'):
        terminal._candidates_ui = CandidatesUI(terminal)
    return terminal._candidates_ui
