"""Contextual typed proposal views; the L02 service alone owns incorporation."""
import json
import time

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.paper_context import FIELDS
from .paper_proposal_work import PaperProposalWork, ProviderProposalWork, CodexProposalPreview, CodexProposalWork, RetainedProposalReview
from .tui_model import TerminalWorkspace, wrap


def available(app):
    connection = getattr(app, 'provider_connection', None)
    if connection is not None:
        return connection.enabled
    return bool(getattr(app, 'offline_assistance', lambda: False)())


class ProposalsUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.controllers = {}
        self.readers = {}
        self.pending = []
        self.index = self.scroll = 0
        self.notice = ''
        self.seen_end = self.painted = False
        self.prompt_buffers = {}
        self.dismissed_advice = set()
        self.edit_mode = False

    @property
    def app(self):
        return self.terminal.app

    def open(self, kind):
        self.terminal.modal = 'proposal-'+kind
        self.scroll = 0
        self.seen_end = self.painted = False
        self.notice = ''

    def local_actions_available(self):
        return self.entry['payload_availability']=='available' and self.entry['request_id'] not in self.dismissed_advice

    def response_history(self):
        """Saved metadata plus still-owned session payloads, never old consent."""
        from claimbranch.core.canonical import digest
        rows = self.app.paper.proposal_history()
        for entry in rows:
            reader = self.readers.get(entry['request_id'])
            if reader is None or entry['result'] is not None or entry['payload_availability'] != 'not-retained':
                continue
            source = next((e for e in reader.historical() if e['request_id']==entry['request_id']), None)
            if source is not None and source['result'] is not None and digest(source['result']) == entry['normalized_digest']:
                entry['result'] = source['result']
                entry['notice'] = 'Session only; this answer is not in the saved checkpoint.'
        return rows

    def enter(self, action):
        self.owner = self.app.work_key()
        if action in ('disable', 'enable'):
            connection = getattr(self.app, 'provider_connection', None)
            if connection is None:
                raise ContractError('No personal LLM profile selected for this session.')
            if action == 'disable':
                connection.enabled = False
                self.shutdown()
            else:
                connection.enabled = True
                try: connection.current_profile()
                except BaseException:
                    connection.enabled = False
                    raise
            self.terminal.modal = None
            self.app.message = ('AI OFF. Manual work and earlier origins retained.' if action == 'disable' else
                connection.connection_notice())
            if action == 'disable' and self.notice: self.app.message += ' '+self.notice
            return
        if action in ('ask', 'discuss', 'edit'):
            if not available(self.app):
                raise ContractError('AI OFF. Select a personal provider profile or use the separate offline rehearsal; manual work remains available.')
            self.connection = getattr(self.app, 'provider_connection', None)
            if self.connection is not None: self.connection.current_profile()
            self.discussion_mode = action in ('discuss','edit')
            self.edit_mode = action == 'edit'
            if self.discussion_mode:
                from .provider_profile import CodexProfile
                if (self.connection is None or type(self.connection.current_profile()) is not CodexProfile
                        or self.connection.codex_worker_type(self.connection.current_profile()) is not CodexProposalWork):
                    raise ContractError('Discussion requires the selected Mac Codex gpt-6-sol connection; manual work remains available.')
                from .tui import Buffer
                self.prompt_buffer = self.prompt_buffers.setdefault((self.owner,'edit') if self.edit_mode else self.owner, Buffer())
                self.previous_requests = set()
            self.source = self.app.service.query(self.app.ref, episode_id=self.app.episode_id)
            self.rows = [(n['id'], n['kind'], n['content']) for n in self.source['nodes'] if n['kind'] in FIELDS]
            self.rows += [(e['record_id'], 'scientific-relation', {k: e[k] for k in FIELDS['scientific-relation']})
                          for e in self.source['relations'] if e['scientific']]
            self.checked = {self.app.selected_id} & {r[0] for r in self.rows}
            self.include_draft = False
            self.purpose = 'critique-interpretation'
            self.index = 0
            self.open('prompt' if self.discussion_mode else 'context')
        elif action == 'current':
            self.worker = self.controllers.get(self.owner)
            if self.worker is None:
                raise ContractError('No live response for this judgment. Saved responses open as history.')
            self.entry = next((e for e in self.worker.historical() if e['request_id'] == self.worker._current), None)
            if self.entry is None or self.entry['result'] is None:
                raise ContractError('Response unavailable; inspect retained history or make a new request.')
            if 'discussion' in self.entry:
                self.open('advice')
                return
            if 'edit' in self.entry and not self.entry['result']['items']:
                self.open('clarification'); return
            self.items = self.entry['result']['items']
            self.chosen = set()
            self.index = 0
            self.open('items')
        else:
            self.history = self.response_history()
            self.index = 0
            self.open('history' if action == 'history' else 'origins')

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, ValueError, OSError) as error:
            self.notice = self.app.message = str(error)

    def poll(self):
        changed = False
        for worker, request_id, deadline in list(self.pending):
            if time.monotonic() < deadline:
                continue
            try:
                worker.complete(request_id)
                entry = next((e for e in worker.historical() if e['request_id']==request_id), None)
                if entry is None:
                    raise ContractError('Response history view unavailable')
                if entry['trace_digest'] is None:
                    continue  # A wire job is asynchronous; keep polling its owned attempt.
            except (ContractError, ValueError, OSError):
                if (worker, request_id, deadline) in self.pending:
                    self.pending.remove((worker, request_id, deadline))
                # Completion commits its trace before projecting the item view.
                # A projection failure cannot revoke that completed proposal.
                retained = next((e for e in worker.workspace._proposal_entries if e['request_id']==request_id), None)
                if retained is not None and retained['trace_digest'] is not None:
                    self.retained_notice(worker)
                    changed = True
                    continue
                try: worker.cancel()
                except OSError: pass  # Revocation is independent of a failed child kill.
                self.notice = self.app.message = ('Response trace unavailable; manual writing retained. '
                    'Inspect AI response history. This attempt is spent; no response or outcome is fabricated.')
                changed = True
                continue
            self.pending.remove((worker, request_id, deadline))
            changed = True
            try:
                current = entry['disposition']=='proposed' and worker._current==request_id
                label = 'Codex' if type(worker) is CodexProposalWork else 'API' if isinstance(worker, ProviderProposalWork) else 'Offline typed'
                self.app.message = (label+(' advice ready. ; opens the readable answer; no graph changed.' if 'discussion' in entry else
                    ' response ready. ; opens item selection; no writing or science changed.') if current else
                    'Response retained as history ('+entry['disposition']+'); manual writing remains unchanged.')
                failure=getattr(worker,'_live_failure',None)
                if failure is not None and failure['request_id']==request_id:
                    self.notice=self.app.message=('Codex request failed: '+failure['phase']+' / '+failure['category']+
                        '. Attempt spent; manual writing retained.')
                if self.terminal.modal == 'proposal-wait' and self.worker is worker:
                    if current and worker.owner == self.app.full_context(self.app.work_key()) and available(self.app):
                        self.enter('current')
                    else:
                        self.entry=entry; self.open('history-detail')
            except (ContractError, ValueError, OSError):
                self.retained_notice(worker)
        return changed

    def retained_notice(self, worker):
        self.notice = self.app.message = 'Response retained; item view unavailable. Reopen from actions; manual writing retained.'
        if self.terminal.modal == 'proposal-wait' and self.worker is worker:
            self.terminal.modal = None

    def shutdown(self):
        """Cancel/reap before the terminal's final checkpoint; preserve all writing."""
        workers = set(self.controllers.values()) | set(self.readers.values()) | {row[0] for row in self.pending}
        for worker in workers:
            try: worker.cancel()
            except OSError: self.notice = 'Request cleanup not confirmed; manual writing retained.'
        transports = getattr(getattr(self.app, 'provider_connection', None), 'transports', {})
        for transport in transports.values():
            try: transport.close()
            except OSError: self.notice = 'Request cleanup not confirmed; manual writing retained.'
        deadline = time.monotonic()+2
        for owner,transport in tuple(transports.items()):
            if not transport.wait_closed(max(0,deadline-time.monotonic())):
                self.notice = (transport.cleanup_notice() if hasattr(transport,'cleanup_notice') else
                    'Request cleanup not confirmed; manual writing retained. Close this session before another request.')
                self.app.message = self.notice
            else:
                del transports[owner]
        connection=getattr(self.app,'provider_connection',None)
        if connection is not None: connection.cleanup_pending=bool(transports)
        self.pending = [(worker, request_id, -1) for worker, request_id, _ in self.pending]
        self.poll()

    def key(self, event):
        mode = self.terminal.modal.removeprefix('proposal-')
        if event == 'escape':
            if mode in ('context-detail', 'prompt', 'previous'): self.open('context')
            elif mode in ('item', 'compare'): self.open('items')
            elif mode in ('passages','passage-preview'): self.open('advice')
            elif mode == 'passage-text': self.open('passages')
            elif mode == 'graph': self.open('compare')
            elif mode == 'retained-basis':
                self.worker.cancel(); self.open('history-detail')
            elif mode == 'history-detail':
                self.history = self.response_history()
                self.index = min(self.index,max(0,len(self.history)-1))
                self.open('history')
            else:
                if mode in ('outbound', 'wait') or isinstance(getattr(self,'worker',None), RetainedProposalReview):
                    self.worker.cancel()
                self.terminal.modal = None
            return
        height, width = self.terminal.screen.getmaxyx()
        if width < 48 or height < 18:
            return
        if mode == 'prompt':
            if event == 'keep':
                from claimbranch.core.advisory import discussion_input
                discussion_input({'prompt':self.prompt_buffer.text, 'previous':[]})
                self.open('context')
            else:
                self.prompt_buffer.key(event, width-8)
            return
        if mode == 'advice' and event == 'x':
            self.dismissed_advice.add(self.entry['request_id'])
            self.notice = 'Local action offers dismissed for this reply in this session.'
            return
        if mode == 'advice' and event in ('1','2','3') and self.local_actions_available():
            from .paper_advisory import AdviceEdits
            if tuple(self.entry['owner']) != self.app.full_context(self.app.work_key()):
                raise ContractError('Return to the answer owner before preparing an edit')
            self.advice_editor=AdviceEdits(self.app.paper,tuple(self.entry['owner']),self.entry['request_id'])
            self.passage_kind={'1':'claim','2':'experiment-plan','3':'scientific-edge'}[event]
            self.passages=[]; offset=0
            for line in self.entry['result']['text'].splitlines(keepends=True):
                end=offset+len(line.rstrip())
                start=offset+len(line)-len(line.lstrip())
                if start<end: self.passages.append((start,end,line[start-offset:end-offset]))
                offset+=len(line)
            self.index=0; self.open('passages')
            return
        if mode == 'passages':
            if event in ('up','down','home','end'):
                self.index=(0 if event=='home' else len(self.passages)-1 if event=='end' else
                    max(0,min(len(self.passages)-1,self.index+(-1 if event=='up' else 1))))
            elif event == 'enter' and self.passages:
                start,end,_=self.passages[self.index]
                self.passage_comparison=self.advice_editor.preview(self.passage_kind,start,end)
                self.open('passage-preview')
            elif event == 's' and self.passages:
                from .tui import Buffer
                self.excerpt_source=self.passages[self.index]
                self.excerpt_buffer=Buffer(self.excerpt_source[2])
                self.open('passage-text')
            return
        if mode == 'passage-text':
            if event == 'keep':
                start,_,text=self.excerpt_source;passage=self.excerpt_buffer.text
                found=text.find(passage)
                if not passage.strip() or found<0 or text.find(passage,found+1)>=0:
                    raise ContractError('Keep one exact, uniquely located excerpt; edit its wording later in the draft')
                self.passage_comparison=self.advice_editor.preview(self.passage_kind,start+found,start+found+len(passage))
                self.open('passage-preview')
            else: self.excerpt_buffer.key(event,width-8)
            return
        if mode == 'passage-preview' and event == 'enter':
            self.require_read()
            if self.advice_editor.owner != self.app.full_context(self.app.work_key()):
                raise ContractError('Return to the original judgment before creating its draft')
            key=self.advice_editor.prefill(self.passage_comparison)
            from .tui_candidates_ui import candidates_ui
            ui=candidates_ui(self.terminal);ui.enter('list')
            ui.index=list(ui.items()).index(key);ui.key('enter')
            ui.notice='AI passage retained. Complete missing fields; graph and personal recording are separate.'
            return
        if mode == 'previous':
            if event in ('up','down'):
                self.previous_index=max(0,min(len(self.previous_rows)-1,self.previous_index+(-1 if event=='up' else 1)))
            elif event == ' ' and self.previous_rows:
                key=self.previous_rows[self.previous_index]['request_id']
                if key not in self.previous_requests and len(self.previous_requests)>=2:
                    raise ContractError('Select at most two earlier replies')
                self.previous_requests.symmetric_difference_update({key})
            elif event == 'enter': self.open('context')
            return
        if mode in ('advice','clarification') and event == 'f':
            if tuple(self.entry['owner']) != self.app.full_context(self.app.work_key()):
                raise ContractError('Return to this reply\'s original judgment before starting a follow-up.')
            self.enter('edit' if mode=='clarification' else 'discuss')
            return
        if mode in ('advice','clarification') and event == 'o':
            self.open('history-detail')
            return
        if mode == 'wait' and event == 'm':
            self.terminal.modal = None
            self.app.message = 'Request still pending. Continue writing; ; opens its items after arrival. Esc in the wait panel cancels.'
            return
        if mode not in ('context','items','history','graph') and event in ('up','down','page-up','page-down','home','end'):
            self.scroll = (0 if event == 'home' else 10**6 if event == 'end' else
                max(0,self.scroll+{'up':-1,'down':1,'page-up':-8,'page-down':8}[event]))
            return
        if mode in ('context', 'items', 'history'):
            values = self.rows if mode == 'context' else self.items if mode == 'items' else self.history
            if event in ('up', 'down', 'home', 'end', 'page-up', 'page-down'):
                self.index = (0 if event == 'home' else max(0, len(values)-1) if event == 'end' else
                    max(0, min(len(values)-1, self.index+{'up':-1, 'down':1, 'page-up':-5, 'page-down':5}[event])))
            elif mode == 'context':
                if event == ' ' and values: self.checked.symmetric_difference_update({values[self.index][0]})
                elif event == 'q' and self.discussion_mode: self.open('prompt')
                elif event == 'h' and self.discussion_mode:
                    self.previous_rows=[e for e in self.app.paper.proposal_history()
                        if tuple(e['owner'])==self.app.full_context(self.owner) and e['result'] is not None and e['provider_disposition']=='proposed'
                        and ('discussion' in e or 'edit' in e and not e['result']['items'] and e['result']['critique'])]
                    self.previous_index=0; self.open('previous')
                elif event == 'd': self.include_draft = not self.include_draft
                elif event == 'p':
                    purposes = ('critique-interpretation','plan-experiment','compare-evidence')
                    self.purpose = purposes[(purposes.index(self.purpose)+1)%len(purposes)]
                elif event == 'r' and values: self.open('context-detail')
                elif event == 'enter':
                    if self.owner != self.app.work_key() or not available(self.app):
                        raise ContractError('Selected judgment or assistance changed; reopen the request. Writing retained.')
                    if any(worker.owner == self.app.full_context(self.owner) for worker, _, _ in self.pending):
                        raise ContractError('A request for this judgment is pending. Continue writing and open its items after arrival, or disable AI to cancel.')
                    previous = self.controllers.get(self.owner)
                    if (previous is not None and previous._current is not None
                            and previous._entry is not None and previous._entry['disposition']=='proposed'
                            and 'discussion' not in previous._entry
                            and not ('edit' in previous._entry and previous._entry['result'] is not None
                                and not previous._entry['result']['items'])):
                        raise ContractError('This judgment already has AI items. Reopen them from actions and explicitly decline (x), or disable AI, before preparing another request. Writing and staged origins retained.')
                    request = {'schema_version':1, 'project_id':self.source['project_id'],
                        'episode_id':self.source['episode_id'], 'ref':self.app.ref, 'view_digest':self.source['digest'],
                        'purpose':self.purpose,
                        'selections':[{'record_id':key, 'fields':list(FIELDS[kind])}
                            for key,kind,_ in self.rows if key in self.checked and kind != 'scientific-relation'],
                        'scientific_edge_ids':[key for key,kind,_ in self.rows if key in self.checked and kind == 'scientific-relation']}
                    self.app.review.candidates()
                    if self.connection is not None:
                        from .provider_profile import CodexProfile
                        profile = self.connection.current_profile()
                        worker_type = self.connection.codex_worker_type(profile) if type(profile) is CodexProfile else ProviderProposalWork
                        worker = worker_type(self.app.paper, self.app.full_context(self.owner))
                        options = ({'prompt':self.prompt_buffer.text, 'previous_requests':sorted(self.previous_requests), 'edit':self.edit_mode}
                            if self.discussion_mode else {})
                        outbound = worker.prepare(request, profile=profile, include_draft=self.include_draft, **options)
                        self.http_outbound = worker.http_preview(outbound,profile) if type(worker) is CodexProposalWork else None
                    else:
                        worker = PaperProposalWork(self.app.paper, self.app.full_context(self.owner),
                            frozen_result=self.app.offline_assistance_result(request))
                        outbound = worker.prepare(request, include_draft=self.include_draft)
                    self.worker, self.outbound = worker, outbound
                    self.open('outbound')
            elif mode == 'items':
                if event=='v' and values:
                    if self.owner!=self.app.work_key():raise ContractError('Return to the response owner before editing')
                    item=values[self.index]
                    self.worker.compare([item['id']]) # Existing freshness/scope check; no staging or write.
                    from .graph_edits import proposal_edit
                    from .tui_graph_edit import graph_edit_ui
                    self.app.recovery.save(self.app)
                    record,source=proposal_edit(self.app.recovery.project,self.entry,item['id'])
                    graph_edit_ui(self.terminal).open(record['id'],proposal=record,proposal_source=source)
                    return
                if event == ' ' and values: self.chosen.symmetric_difference_update({values[self.index]['id']})
                elif event == 'enter' and values: self.open('item')
                elif event == 'c':
                    if self.owner != self.app.work_key(): raise ContractError('Return to the response\'s original judgment.')
                    self.comparison = self.worker.compare(sorted(self.chosen))
                    self.before = self.worker.work.project()
                    self.open('compare')
                elif event == 'x':
                    self.worker.cancel(); self.terminal.modal = None
                    self.app.message = 'Response declined; prior writing and staged drafts retained. Saved response is historical.'
                elif event == 'e':
                    if self.owner != self.app.work_key(): raise ContractError('Return to the original judgment before editing its drafts.')
                    from .tui_candidates_ui import candidates_ui
                    candidates_ui(self.terminal).enter('list')
            elif event == 'enter' and values:
                self.entry = values[self.index]
                self.open('advice' if 'discussion' in self.entry and self.entry['result'] is not None else
                    'clarification' if 'edit' in self.entry and self.entry['result'] is not None and not self.entry['result']['items'] else 'history-detail')
            return
        if mode == 'history-detail' and event == 'r':
            if 'discussion' in self.entry:
                raise ContractError('This saved reply is advice; it contains no graph items to stage.')
            self.require_read()
            if self.owner != self.app.work_key():
                raise ContractError('Judgment owner changed; reopen history')
            worker = RetainedProposalReview(self.app.paper, self.app.full_context(self.owner), self.entry['request_id'])
            self.worker = worker
            self.controllers[self.owner] = worker
            self.open('retained-basis')
        elif mode == 'retained-basis' and event == 'enter':
            self.require_read(); self.worker._fresh()
            if self.owner != self.app.work_key():
                raise ContractError('Judgment owner changed; reopen history')
            self.enter('current')
        elif mode == 'outbound' and event == 'enter':
            self.require_read()
            if self.owner != self.app.work_key() or not available(self.app):
                raise ContractError('Context changed. Reopen the exact request; writing is retained.')
            if isinstance(self.worker, ProviderProposalWork):
                if self.connection is not getattr(self.app,'provider_connection',None):
                    raise ContractError('Personal connection changed; review a new exact request.')
                if type(self.worker) is CodexProposalWork:
                    self.connection.begin(self.worker,self.outbound,confirmed_http_digest=self.http_outbound['body_sha256'])
                else:
                    self.connection.begin(self.worker, self.outbound)
                request_id, delay = self.outbound.review.request_id, 0
                if type(self.worker) is CodexProposalWork and self.outbound.discussion is not None:
                    from .tui import Buffer
                    self.prompt_buffers[(self.owner,'edit') if self.outbound.edit else self.owner] = Buffer()
            else:
                self.worker.begin(self.outbound)
                request_id, delay = self.outbound.request_id, .7
            self.controllers[self.owner] = self.worker
            self.readers[request_id] = self.worker
            self.pending.append((self.worker, request_id, time.monotonic()+delay))
            self.open('wait')
        elif mode == 'compare':
            if event == 'c' and isinstance(self.worker, RetainedProposalReview):
                self.comparison = self.worker.compare(sorted(self.chosen)); self.open('compare')
            elif event == 'G':
                self.graphs = {phase:self.graph(projection) for phase,projection in
                    (('before', self.before), ('after', self.comparison['graph']))}
                self.phase = 'after'; self.open('graph')
            elif event == 'enter':
                self.require_read()
                if self.owner != self.app.work_key(): raise ContractError('Judgment owner changed; compare again.')
                self.worker.stage(self.comparison)
                self.open('items')
                self.notice = 'Selected batch staged, AI origin retained. e opens existing draft editors; nothing recorded.'
        elif mode == 'graph':
            if event == 'tab': self.phase = 'before' if self.phase == 'after' else 'after'
            elif event == 'f': self.graphs[self.phase].fit_graph()
            elif event in ('up','down','left','right'):
                from .tui_graph import move_graph
                move_graph(self.graphs[self.phase], event)
        elif event in ('up','down','page-up','page-down','home','end'):
            self.scroll = (0 if event == 'home' else 10**6 if event == 'end' else
                max(0,self.scroll+{'up':-1,'down':1,'page-up':-8,'page-down':8}[event]))

    def require_read(self):
        if not self.painted or not self.seen_end:
            raise ContractError('Read the complete comparison first. End reaches its last page.')

    def graph(self, projection):
        projection = projection.get('graph', projection)
        graph = TerminalWorkspace(self.app.paper.history, ai_off=True)
        graph.projection_only = True
        graph.graph_spacing, graph.density = self.app.graph_spacing, self.app.density
        graph.view = {**self.app.view, **projection}
        graph.nodes = {n['id']:n for n in projection['nodes']}
        graph._build_outline()
        graph.selected_id = self.app.selected_id if self.app.selected_id in graph._paths else graph.view['thesis_id']
        graph.selected_path = graph._paths[graph.selected_id]
        return graph

    def content(self, mode):
        app = self.app
        def rendered(value): return json.dumps(value,ensure_ascii=False,indent=2)
        wire = isinstance(getattr(self,'worker',None), ProviderProposalWork)
        codex = isinstance(getattr(self,'worker',None), CodexProposalPreview)
        exact_codex = type(getattr(self,'worker',None)) is CodexProposalWork
        retained = isinstance(getattr(self,'worker',None), RetainedProposalReview)
        common = [('REVIEW SAVED AI ITEMS / no new request; original origin retained' if retained else
                   'CODEX PROPOSAL / untrusted, not recorded; manual writing retained' if exact_codex else
                   'CODEX INPUT PREVIEW / unsent; runtime access and remote wrapper unverified' if codex else
                   'PERSONAL API PROPOSAL / untrusted, not recorded, no verified measurement' if wire else
                   'OFFLINE FIXED EXAMPLE / no network, no verified measurement'),
                  'Judgment owner: '+' / '.join(self.owner),
                  'Your judgment: '+(app.draft()['text'] or '(unfinished)'),
                  'Your original reason: '+(app.draft()['rationale'] or '(unfinished)')]
        if mode == 'clarification':
            return ['AI CLARIFICATION / no graph items or changes',
                'YOUR EDIT INSTRUCTION',self.entry['edit']['prompt'],
                'CLARIFICATION',self.entry['result']['critique'] or 'No edit supplied.',
                'f writes a revised instruction; h explicitly selects this clarification for that request.',
                'A new request uses the remaining attempt budget. o reads original context and origin.']
        if mode == 'passage-preview':
            value=self.passage_comparison
            return ['PREPARE AN EDITABLE DRAFT / no request or science recorded',
                'EXACT SELECTED AI PASSAGE',value['passage'],
                'DRAFT / '+value['kind'],rendered(value['body']),
                'Blank fields need your choices. Plans are unrun; no support or evidence is inferred.',
                'The source answer and selected passage remain with this draft after edits and save.',
                'Enter prepares this one unaccepted form. Complete fields, then g inspects the draft graph.',
                'Esc returns to the answer without creating a draft.']
        if mode == 'advice':
            return ['AI ADVICE / not evidence or a recorded judgment',
                *(['SESSION ONLY / this answer is not in the saved checkpoint; keep this session open to read it.']
                    if self.entry['payload_availability']=='not-retained' else []),
                'Original work: '+' / '.join(self.entry['owner']),
                'YOUR QUESTION',self.entry['discussion']['prompt'],
                'ANSWER',self.entry['result']['text'],
                'No graph changes. Read, question or reject this advice.',
                *(['APPLICATION ACTIONS / choose a passage first: 1 claim · 2 unrun plan · 3 connection · x dismiss']
                    if self.local_actions_available() else []),
                'f starts a follow-up; choose earlier replies explicitly. o reads the original graph input.',
                'ORIGIN',rendered({k:self.entry[k] for k in ('request_id','destination','context_digest',
                    'request_digest','response_digest','normalized_digest','disposition','payload_availability')}),
                'Selected previous replies: '+(', '.join(m['request_id'] for m in self.entry['discussion']['previous']) or 'None'),
                'Saved reading restores no request or recording permission.']
        if mode == 'retained-basis':
            return common + ['ORIGINAL AND CURRENT INPUT', rendered(self.worker.basis),
                *(['EXTERNAL AI SOURCE / imported claims, not a verified application request',rendered(self.worker._entry['external'])]
                  if 'external' in self.worker._entry else []),
                'Enter opens item selection for this new local review. Esc keeps history unchanged.',
                'Reading has no time limit. A selected-item comparison lasts 120 seconds; c compares again.',
                'No request is sent, no old consent restored, and no scientific judgment is recorded.']
        if mode == 'outbound':
            if exact_codex:
                return common + ['COMPLETE HTTP REQUEST / unsent',rendered(self.http_outbound),
                    'Application input digest: '+self.outbound.digest,
                    'HTTP body SHA-256: '+self.http_outbound['body_sha256'],
                    'Read all content before Enter sends this request. Supported Mac runtime and login are checked first.',
                    'Existing Codex login only; account usage may apply. No login values in the preview.',
                    'One request, no redirects or retries. At most three attempts per judgment.',
                    'Retained minimal trace and available response; no live request restores. Esc cancels.']
            return common + ['EXACT APPLICATION INPUT / not CLI-generated HTTP content or consent' if codex else
                'EXACT INPUT / destination, task, selected fields, redactions, optional draft and request digest',
                rendered(self.outbound.preview() if wire else decode(self.outbound.payload)), 'Request digest: '+self.outbound.digest,
                *(['Actual Codex client not qualified. Enter explains the missing runtime/return; no client is launched.',
                   'No attempt, response, trace or consent is saved by this Codex preview.'] if codex else [
                    *(['Actual provider not qualified. Enter checks the live gate; no request can be sent in this build.'] if wire else []),
                    'Retained minimal trace and available response in this private checkpoint; no live request restores.',
                    'At most three dispatched attempts per judgment. No retry or automatic incorporation.'])]
        if mode == 'context-detail': return [self.rows[self.index][1].upper(), rendered(self.rows[self.index][2])]
        if mode == 'item': return common + ['ADVISORY CRITIQUE / not a fact',self.entry['result']['critique'] or 'None',
            *(['EXTERNAL AI SOURCE / imported claims, not a verified application request',rendered(self.entry['external'])] if 'external' in self.entry else []),
            'RESPONSE ORIGIN',rendered({k:self.entry[k] for k in ('request_id','request_digest','context_digest','destination','response_digest','trace_digest')}),
            *(['API REQUEST AND OUTCOME / reported model is not verified served identity',rendered(self.entry['provider'])] if 'provider' in self.entry else []),
            'NOT RECORDED / original AI item',rendered(self.items[self.index])]
        if mode == 'compare':
            value = self.comparison
            omitted = sorted({i['id'] for i in self.items}-set(value['item_ids'])-set(value['required_item_ids']))
            source_records = self.app.paper.history.view(self.app.ref,episode_id=self.app.episode_id)['changes']
            before = {r['id']:r for r in [*source_records,*value['previous_records']]}
            rows = common + ['CHOSEN: '+', '.join(value['item_ids']),
                'REQUIRED: '+(', '.join(value['required_item_ids']) or 'None'),
                'OMITTED RESPONSE ITEMS: '+(', '.join(omitted) or 'None')]
            if retained:
                rows += ['Local comparison remaining: '+str(max(0,value['expires_at']-int(self.worker.clock())))+
                    ' seconds. c compares again without a request.']
            for record in value['records']:
                rows += ['BEFORE / '+record['kind'],rendered(before.get(record['id'])) if record['id'] in before else 'New unrecorded candidate',
                         'AFTER / '+('EXTERNAL UNVERIFIED AI origin retained' if 'external' in self.worker._entry else 'AI origin retained'),rendered(record)]
            return rows + ['G inspects both draft graphs. Evidence identities remain unchanged.',
                'Enter stages only this batch. Edit it through Open argument drafts before personal recording.',
                'Staging does not change your judgment/reason, confirm evidence, write a manuscript or require explanation.']
        if mode == 'history-detail':
            from .paper_proposal_work import _bundle
            failure=next((getattr(worker,'_live_failure',None) for worker in self.controllers.values()
                if getattr(worker,'_live_failure',None) is not None
                and worker._live_failure['request_id']==self.entry['request_id']),None)
            return ['HISTORICAL RESPONSE / reading only until a new local review; no restored consent',
                'Read the original context, then r opens a new local review of retained items.',
                *(['CURRENT SESSION DIAGNOSTIC / not saved with research',rendered(failure),
                   'Attempt spent; manual writing retained.'] if failure is not None else []),
                *(['No terminal response trace recovered. This dispatched attempt remains spent; no live request restores.']
                  if self.entry['trace_digest'] is None else []),
                ('LOCAL IMPORT CONTEXT / not proof of originally transmitted input; EXTERNAL UNVERIFIED SOURCE' if 'external' in self.entry else
                 'ORIGINAL SELECTED INPUT / reconstructed from its original recorded prefix'),
                rendered(decode(_bundle(app.paper.history,self.entry).payload)),rendered(self.entry)]
        if mode == 'origins':
            rows = ['SAVED AI ORIGIN / remains after human edits; no protected authority']
            shown_sources = set()
            attempts = {e['request_id']:e for e in app.paper.proposal_history()}
            def source_details(request_id):
                if request_id in shown_sources:
                    return ['SOURCE ABOVE / '+request_id]
                shown_sources.add(request_id)
                entry = attempts.get(request_id)
                if entry is None:
                    return ['SOURCE UNAVAILABLE / '+request_id]
                from .paper_proposal_work import _bundle
                result = ['REQUEST / '+request_id, 'REQUESTED MODEL / '+entry['destination']['model']]
                reported = (entry.get('codex') or entry.get('provider') or {}).get('outcome') or {}
                if reported.get('reported_model'):
                    result += ['REPORTED MODEL / '+reported['reported_model']+' / provider-reported, not independently verified']
                if 'external' in entry:
                    result += ['EXTERNAL UNVERIFIED AI SOURCE / '+request_id+' / '+rendered(entry['external'])]
                discussion = entry.get('discussion',entry.get('edit'))
                if discussion:
                    result += [('ORIGINAL QUESTION / ' if 'discussion' in entry else 'ORIGINAL EDIT INSTRUCTION / ')+discussion['prompt']]
                response = entry['result']
                if response is not None:
                    result += ['ORIGINAL ANSWER / untrusted AI text',
                        response['text'] if 'discussion' in entry else rendered(response)]
                else:
                    result += ['ORIGINAL PAYLOAD UNAVAILABLE / '+entry['payload_availability']+
                        '; adopted item content remains in its revisions below.']
                result += ['ORIGINAL SELECTED GRAPH CONTEXT / historical, not current science',
                    rendered(decode(_bundle(app.paper.history,entry).payload))]
                for message in (discussion or {}).get('previous',[]):
                    result += ['EXPLICITLY INCLUDED EARLIER REPLY / '+message['request_id'],
                        'INCLUDED QUESTION / '+message['prompt'], 'INCLUDED TEXT',message['text'],
                        *source_details(message['request_id'])]
                return result
            def source_labels(value):
                ids=set(); passages=[]
                def visit(item):
                    if isinstance(item,dict):
                        if item.get('proposal_origin'): ids.add(item['proposal_origin']['request_id'])
                        if item.get('advisory_origin'):
                            origin=item['advisory_origin']; ids.add(origin['request_id'])
                            passages.extend(['SELECTED AI PASSAGE / '+origin['action_id'],origin['passage']])
                        for child in item.values(): visit(child)
                    elif isinstance(item,list):
                        for child in item: visit(child)
                visit(value)
                return passages+[line for key in sorted(ids) for line in source_details(key)]
            for revision in app.paper.history.view('main').get('graph_revisions',[]):
                source=revision.get('proposal_source')
                if source:
                    rows += ['DIRECT GRAPH REVISION / personal recorded contribution',
                        *source_details(source['request_id']),rendered(revision)]
                elif revision['origin'] in ('ai','mixed','unknown'):
                    rows += ['DIRECT GRAPH REVISION / declared origin, no inferred provider request',rendered(revision)]
            for owner,work in sorted(app.paper._candidates.items()):
                for lineage in work.origins.values():
                    value=decode(lineage.payload)
                    rows += ['UNRECORDED / '+' / '.join(owner),*source_labels(value),rendered(value)]
            for record in app.paper.recorded_origins():
                rows += ['PERSONALLY RECORDED / original reason and explanation choice',
                    'ORIGINAL HUMAN REASON / '+record['cause']['judgment']['rationale'],
                    'RECORDED EXPLANATION CHOICE / '+record['explanation']['state'],
                    *source_labels(record),rendered(record)]
            return rows if len(rows)>1 else rows+['No adopted item origin. Unused responses are in proposal history.']
        return common+['Waiting for the Codex response. m continues writing; Esc cancels.' if exact_codex else
                       'Waiting for the API response. m continues writing; Esc cancels.' if wire else
                       'Waiting for the offline example. m continues writing; Esc cancels.']

    def draw(self, original):
        from .tui import Frame, compose
        width,height = original.width,original.height
        frame = Frame(width,height)
        mode = self.terminal.modal.removeprefix('proposal-')
        if width<48 or height<18:
            frame.put(1,1,'Proposal controls paused','top_warning',width-2)
            frame.put(3,1,'Enlarge to 48 x 18. Esc returns with writing retained.','body',width-2)
            return frame
        if mode == 'graph':
            frame = compose(self.graphs[self.phase],width,height)
            frame.fill(1,0,width,'canvas')
            frame.put(1,2,'AI ITEM COMPARISON / '+self.phase.upper()+' / UNRECORDED','top_warning',width-4)
            frame.put(height-2,2,'Tab before/after · arrows focus · f fit · Esc comparison','top_accent',width-4)
            return frame
        if mode == 'prompt':
            frame.put(0,2,'PREPARE A SMALL GRAPH EDIT' if self.edit_mode else 'DISCUSS THE SELECTED ARGUMENT','brand',width-4)
            frame.put(2,3,'Your question · 4096 UTF-8 bytes · sends nothing','body',width-6)
            frame.box(2,4,width-4,height-8,'QUESTION',True)
            rows,row,column=self.prompt_buffer.position(width-8)
            offset=max(0,row-(height-12))
            for i,(text,_,_) in enumerate(rows[offset:offset+height-10]):
                frame.put(5+i,4,text,'body',width-8)
            frame.cursor=(5+row-offset,min(width-4,4+column))
            frame.put(height-3,2,'Ctrl+S choose context · Enter new line · Esc keep here','top_accent',width-4)
            frame.put(height-2,2,'Unsent question stays in this session; sent questions/replies use project save.','top_warning',width-4)
            frame.put(height-1,2,self.notice or self.prompt_buffer.notice,'top_warning',width-4)
            return frame
        if mode == 'passage-text':
            frame.put(0,2,'CHOOSE A SHORTER EXACT EXCERPT','brand',width-4)
            frame.put(2,3,'Remove surrounding words; rewrite later in the candidate.','body',width-6)
            frame.box(2,4,width-4,height-8,'SOURCE EXCERPT',True)
            rows,row,column=self.excerpt_buffer.position(width-8);offset=max(0,row-(height-12))
            for i,(text,_,_) in enumerate(rows[offset:offset+height-10]):frame.put(5+i,4,text,'body',width-8)
            frame.cursor=(5+row-offset,min(width-4,4+column))
            frame.put(height-2,2,'Ctrl+S compare exact excerpt · Esc passages','top_accent',width-4)
            frame.put(height-1,2,self.notice or self.excerpt_buffer.notice,'top_warning',width-4)
            return frame
        if mode == 'passages':
            frame.put(0,2,'SELECT AN EXACT ANSWER PASSAGE','brand',width-4)
            visible=max(1,(height-7)//3);offset=max(0,self.index-visible+1)
            for i,(_,_,passage) in enumerate(self.passages[offset:offset+visible]):
                for row,text in enumerate(wrap(passage,width-8)[:2]):
                    frame.put(3+i*3+row,3,('› ' if i+offset==self.index and row==0 else '  ')+text,'body',width-6)
            frame.put(height-2,2,'Up/Down choose · Enter compare · s shorter excerpt · Esc cancel','top_accent',width-4)
            frame.put(height-1,2,self.notice,'top_warning',width-4)
            return frame
        if mode == 'previous':
            frame.put(0,2,'SELECT EARLIER REPLIES / NOTHING INCLUDED BY DEFAULT','brand',width-4)
            frame.put(1,2,'Included text is retained with the next request; referenced replies cannot be erased.','top_warning',width-4)
            visible=max(1,(height-7)//3);offset=max(0,self.previous_index-visible+1)
            for i,entry in enumerate(self.previous_rows[offset:offset+visible]):
                frame.put(3+i*3,2,('› ' if i+offset==self.previous_index else '  ')+
                    ('[x] ' if entry['request_id'] in self.previous_requests else '[ ] ')+entry.get('discussion',entry.get('edit'))['prompt'],
                    'selected_meta' if i+offset==self.previous_index else 'heading',width-4)
                frame.put(4+i*3,4,entry['result'].get('text',entry['result'].get('critique','')),'body',width-8)
            if not self.previous_rows: frame.put(3,3,'No retained advice for this judgment.','body',width-6)
            frame.put(height-2,2,'Up/Down choose · Space include · Enter or Esc context','top_accent',width-4)
            frame.put(height-1,2,self.notice,'top_warning',width-4)
            return frame
        titles = {'context':'SELECT EXACT AI CONTEXT', 'items':'SELECT AI ITEMS / NOT RECORDED',
            'outbound':'REVIEW EXACT OFFLINE INPUT', 'compare':'COMPARE SELECTED AI ITEMS',
            'item':'READ AI ITEM', 'history':'AI RESPONSE HISTORY', 'history-detail':'HISTORICAL AI RESPONSE',
            'origins':'AI ITEM ORIGINS', 'wait':'OFFLINE EXAMPLE PENDING', 'context-detail':'RECORDED CONTEXT',
            'retained-basis':'REVIEW ORIGINAL AND CURRENT CONTEXT', 'advice':'READ AI ADVICE', 'passage-preview':'COMPARE AI PASSAGE AND DRAFT', 'clarification':'READ AI CLARIFICATION'}
        if isinstance(getattr(self,'worker',None), ProviderProposalWork):
            titles.update(outbound='REVIEW EXACT API REQUEST',wait='PERSONAL API REQUEST PENDING')
        if isinstance(getattr(self,'worker',None), CodexProposalPreview):
            titles['outbound'] = 'REVIEW CODEX APPLICATION INPUT / UNSENT'
        if type(getattr(self,'worker',None)) is CodexProposalWork:
            titles.update(outbound='REVIEW COMPLETE CODEX HTTP REQUEST / UNSENT',wait='CODEX REQUEST PENDING')
        frame.put(0,2,titles[mode],'brand',width-4)
        if mode in ('context','items','history'):
            values = self.rows if mode == 'context' else self.items if mode == 'items' else self.history
            intro = ('Task '+self.purpose+'. Only checked recorded science enters. Draft '+('ON' if self.include_draft else 'OFF') if mode == 'context' else
                self.entry['result']['critique'] or 'No advisory critique.' if mode == 'items' else
                'Read a saved response, then explicitly review its current context to select items.')
            if mode=='context' and self.discussion_mode:
                session=self.app.paper.draft(*self.app.full_context(self.owner))
                remaining=max(0,3-session._prior_dispatches-len(session._broker.dispatched))
                intro=('Edit request: ' if self.edit_mode else 'Discuss: ')+self.prompt_buffer.text+' · Earlier replies '+str(len(self.previous_requests))+' · Requests left '+str(remaining)
            for i,line in enumerate(wrap(intro,width-6)[:3]): frame.put(2+i,3,line,'body',width-6)
            visible = max(1,(height-11)//3); offset=max(0,self.index-visible+1)
            for i,value in enumerate(values[offset:offset+visible]):
                index=offset+i
                if mode=='context':
                    key,kind,body=value; chosen=key in self.checked
                    text=body.get('statement') or body.get('objective') or body.get('question') or rendered_relation(body)
                elif mode=='items':
                    key,kind,body=value['id'],value['kind'],value['body']; chosen=key in self.chosen
                    text=body.get('statement') or body.get('objective') or rendered_relation(body)
                else:
                    key,kind=value['request_id'],value['disposition']; chosen=False
                    text=('EXTERNAL IMPORT / ' if 'external' in value else '')+value['destination']['model']+' / payload '+value['payload_availability']
                frame.put(6+3*i,2,('› ' if index==self.index else '  ')+('[x] ' if chosen else '[ ] ')+kind+' / '+key,'selected_meta' if index==self.index else 'heading',width-4)
                frame.put(7+3*i,6,text,'body',width-10)
            if not values: frame.put(6,3,'No retained items. Manual work remains available.','body',width-6)
            hints = ('Space select · r read · d draft · p task · Enter preview' if mode=='context' else
                     'Space select · Enter read · c compare · v edit recorded item · e drafts · x decline' if mode=='items' else
                     '↑↓ choose · Enter read historical response · Esc graph')
            if mode=='context' and self.discussion_mode:
                hints='Space select · r read · d draft · q question · h history · Enter preview'
            frame.put(height-3,2,'Esc returns to the same work; ; opens draft editors and origins.','top_muted',width-4)
        else:
            lines = [line for text in self.content(mode) for line in [*wrap(text,width-6),'']]
            count=height-7; self.scroll=min(self.scroll,max(0,len(lines)-count))
            for i,line in enumerate(lines[self.scroll:self.scroll+count]): frame.put(3+i,3,line,'body',width-6)
            if not self.painted and hasattr(self.terminal.curses,'flushinp'): self.terminal.curses.flushinp()
            self.painted=True; self.seen_end |= self.scroll+count>=len(lines)
            frame.put(height-3,2,f'{self.scroll+1}–{min(len(lines),self.scroll+count)}/{len(lines)} · no science recorded','top_muted',width-4)
            hints = (('Enter send reviewed request · End read · Esc cancel' if type(getattr(self,'worker',None)) is CodexProposalWork else
                'Enter check live gate · End read · Esc cancel' if isinstance(getattr(self,'worker',None),ProviderProposalWork) else
                       'Enter request example · End read · Esc cancel') if mode=='outbound' else
                'Enter stage batch · G graphs · End read · Esc keep mine' if mode=='compare' else
                'm continue writing · Esc cancel request' if mode=='wait' else
                'r new local review · End read · Esc return' if mode=='history-detail' else
                'Enter select items · End read · Esc cancel review' if mode=='retained-basis' else
                'f revised instruction · o original input · Esc graph' if mode=='clarification' else
                ('f follow-up · o input · 1/2/3 local edits · x dismiss · Esc graph' if self.local_actions_available()
                    else 'f follow-up · o original input · PgUp/PgDn read · Esc graph') if mode=='advice' else
                'Enter prepare editable draft · End read · Esc cancel' if mode=='passage-preview' else
                'PgUp/PgDn · Home/End read · Esc return')
        frame.put(height-2,2,hints,'top_accent',width-4)
        frame.put(height-1,2,getattr(self.app,'recovery_error',None) or self.notice,'top_warning',width-4)
        return frame


def rendered_relation(body):
    return str(body.get('source_id',''))+' '+body.get('edge_type','')+' → '+str(body.get('target_id',''))+' / '+body.get('rationale','')


def proposals_ui(terminal):
    if not hasattr(terminal,'_proposals_ui'): terminal._proposals_ui=ProposalsUI(terminal)
    return terminal._proposals_ui
