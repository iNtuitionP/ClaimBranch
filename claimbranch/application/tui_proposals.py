"""Contextual typed proposal views; the L02 service alone owns incorporation."""
import json
import time

from claimbranch.core.canonical import ContractError, decode
from claimbranch.core.paper_context import FIELDS
from .paper_proposal_work import PaperProposalWork, ProviderProposalWork, CodexProposalPreview
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
        self.pending = []
        self.index = self.scroll = 0
        self.notice = ''
        self.seen_end = self.painted = False

    @property
    def app(self):
        return self.terminal.app

    def open(self, kind):
        self.terminal.modal = 'proposal-'+kind
        self.scroll = 0
        self.seen_end = self.painted = False
        self.notice = ''

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
                'Personal LLM previews enabled; actual provider not qualified. No request sent.')
            if action == 'disable' and self.notice: self.app.message += ' '+self.notice
            return
        if action == 'ask':
            if not available(self.app):
                raise ContractError('AI OFF. Select a personal provider profile or use the separate offline rehearsal; manual work remains available.')
            self.connection = getattr(self.app, 'provider_connection', None)
            if self.connection is not None: self.connection.current_profile()
            self.source = self.app.service.query(self.app.ref, episode_id=self.app.episode_id)
            self.rows = [(n['id'], n['kind'], n['content']) for n in self.source['nodes'] if n['kind'] in FIELDS]
            self.rows += [(e['record_id'], 'scientific-relation', {k: e[k] for k in FIELDS['scientific-relation']})
                          for e in self.source['relations'] if e['scientific']]
            self.checked = {self.app.selected_id} & {r[0] for r in self.rows}
            self.include_draft = False
            self.purpose = 'critique-interpretation'
            self.index = 0
            self.open('context')
        elif action == 'current':
            self.worker = self.controllers.get(self.owner)
            if self.worker is None:
                raise ContractError('No live response for this judgment. Saved responses open as history.')
            self.entry = next((e for e in self.worker.historical() if e['request_id'] == self.worker._current), None)
            if self.entry is None or self.entry['result'] is None:
                raise ContractError('Response unavailable; inspect retained history or make a new request.')
            self.items = self.entry['result']['items']
            self.chosen = set()
            self.index = 0
            self.open('items')
        else:
            self.history = self.app.paper.proposal_history()
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
                label = 'API' if isinstance(worker, ProviderProposalWork) else 'Offline typed'
                self.app.message = (label+' response ready. ; opens item selection; no writing or science changed.' if current else
                    'Response retained as history ('+entry['disposition']+'); manual writing remains unchanged.')
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
        workers = set(self.controllers.values()) | {row[0] for row in self.pending}
        for worker in workers:
            try: worker.cancel()
            except OSError: self.notice = 'Request cleanup not confirmed; manual writing retained.'
        transports = getattr(getattr(self.app, 'provider_connection', None), 'transports', {})
        for transport in transports.values():
            try: transport.close()
            except OSError: self.notice = 'Request cleanup not confirmed; manual writing retained.'
        deadline = time.monotonic()+2
        for transport in transports.values():
            if not transport.wait_closed(max(0,deadline-time.monotonic())):
                self.notice = 'Request cleanup not confirmed; manual writing retained.'
        transports.clear()
        self.pending = [(worker, request_id, -1) for worker, request_id, _ in self.pending]
        self.poll()

    def key(self, event):
        mode = self.terminal.modal.removeprefix('proposal-')
        if event == 'escape':
            if mode == 'context-detail': self.open('context')
            elif mode in ('item', 'compare'): self.open('items')
            elif mode == 'graph': self.open('compare')
            elif mode == 'history-detail':
                self.history = self.app.paper.proposal_history()
                self.index = min(self.index,max(0,len(self.history)-1))
                self.open('history')
            else:
                if mode in ('outbound', 'wait'): self.worker.cancel()
                self.terminal.modal = None
            return
        height, width = self.terminal.screen.getmaxyx()
        if width < 48 or height < 18:
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
                            and previous._entry is not None and previous._entry['disposition']=='proposed'):
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
                        worker_type = CodexProposalPreview if type(profile) is CodexProfile else ProviderProposalWork
                        worker = worker_type(self.app.paper, self.app.full_context(self.owner))
                        outbound = worker.prepare(request, profile=profile, include_draft=self.include_draft)
                    else:
                        worker = PaperProposalWork(self.app.paper, self.app.full_context(self.owner),
                            frozen_result=self.app.offline_assistance_result(request))
                        outbound = worker.prepare(request, include_draft=self.include_draft)
                    self.worker, self.outbound = worker, outbound
                    self.controllers[self.owner] = worker
                    self.open('outbound')
            elif mode == 'items':
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
                self.entry = values[self.index]; self.open('history-detail')
            return
        if mode == 'outbound' and event == 'enter':
            self.require_read()
            if self.owner != self.app.work_key() or not available(self.app):
                raise ContractError('Context changed. Reopen the exact request; writing is retained.')
            if isinstance(self.worker, ProviderProposalWork):
                if self.connection is not getattr(self.app,'provider_connection',None):
                    raise ContractError('Personal connection changed; review a new exact request.')
                self.connection.begin(self.worker, self.outbound)
                request_id, delay = self.outbound.review.request_id, 0
            else:
                self.worker.begin(self.outbound)
                request_id, delay = self.outbound.request_id, .7
            self.pending.append((self.worker, request_id, time.monotonic()+delay))
            self.open('wait')
        elif mode == 'compare':
            if event == 'G':
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
        common = [('CODEX INPUT PREVIEW / unsent; runtime access and remote wrapper unverified' if codex else
                   'PERSONAL API PROPOSAL / untrusted, not recorded, no verified measurement' if wire else
                   'OFFLINE FIXED EXAMPLE / no network, no verified measurement'),
                  'Judgment owner: '+' / '.join(self.owner),
                  'Your judgment: '+(app.draft()['text'] or '(unfinished)'),
                  'Your original reason: '+(app.draft()['rationale'] or '(unfinished)')]
        if mode == 'outbound':
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
            for record in value['records']:
                rows += ['BEFORE / '+record['kind'],rendered(before.get(record['id'])) if record['id'] in before else 'New unrecorded candidate',
                         'AFTER / AI origin retained',rendered(record)]
            return rows + ['G inspects both draft graphs. Evidence identities remain unchanged.',
                'Enter stages only this batch. Edit it through Open argument drafts before personal recording.',
                'Staging does not change your judgment/reason, confirm evidence, write a manuscript or require explanation.']
        if mode == 'history-detail':
            from .paper_proposal_work import _bundle
            return ['HISTORICAL RESPONSE / reading only; no consent or staging capability',
                *(['No terminal response trace recovered. This dispatched attempt remains spent; no live request restores.']
                  if self.entry['trace_digest'] is None else []),
                'ORIGINAL SELECTED INPUT / reconstructed from its original recorded prefix',
                rendered(decode(_bundle(app.paper.history,self.entry).payload)),rendered(self.entry)]
        if mode == 'origins':
            rows = ['SAVED AI ORIGIN / remains after human edits; no protected authority']
            for owner,work in sorted(app.paper._candidates.items()):
                for lineage in work.origins.values(): rows += ['UNRECORDED / '+' / '.join(owner),rendered(decode(lineage.payload))]
            for record in app.paper.recorded_origins(): rows += ['PERSONALLY RECORDED / original reason and explanation choice',rendered(record)]
            return rows if len(rows)>1 else rows+['No adopted item origin. Unused responses are in proposal history.']
        return common+['Waiting for the API response. m continues writing; Esc cancels.' if wire else
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
        titles = {'context':'SELECT EXACT AI CONTEXT', 'items':'SELECT AI ITEMS / NOT RECORDED',
            'outbound':'REVIEW EXACT OFFLINE INPUT', 'compare':'COMPARE SELECTED AI ITEMS',
            'item':'READ AI ITEM', 'history':'AI RESPONSE HISTORY', 'history-detail':'HISTORICAL AI RESPONSE',
            'origins':'AI ITEM ORIGINS', 'wait':'OFFLINE EXAMPLE PENDING', 'context-detail':'RECORDED CONTEXT'}
        if isinstance(getattr(self,'worker',None), ProviderProposalWork):
            titles.update(outbound='REVIEW EXACT API REQUEST',wait='PERSONAL API REQUEST PENDING')
        if isinstance(getattr(self,'worker',None), CodexProposalPreview):
            titles['outbound'] = 'REVIEW CODEX APPLICATION INPUT / UNSENT'
        frame.put(0,2,titles[mode],'brand',width-4)
        if mode in ('context','items','history'):
            values = self.rows if mode == 'context' else self.items if mode == 'items' else self.history
            intro = ('Task '+self.purpose+'. Only checked recorded science enters. Draft '+('ON' if self.include_draft else 'OFF') if mode == 'context' else
                self.entry['result']['critique'] or 'No advisory critique.' if mode == 'items' else
                'Saved responses are read-only. Origin and manual editing remain available.')
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
                    text=value['destination']['model']+' / payload '+value['payload_availability']
                frame.put(6+3*i,2,('› ' if index==self.index else '  ')+('[x] ' if chosen else '[ ] ')+kind+' / '+key,'selected_meta' if index==self.index else 'heading',width-4)
                frame.put(7+3*i,6,text,'body',width-10)
            if not values: frame.put(6,3,'No retained items. Manual work remains available.','body',width-6)
            hints = ('Space select · r read · d draft · p task · Enter preview' if mode=='context' else
                     'Space select · Enter read · c compare · e edit drafts · x decline' if mode=='items' else
                     '↑↓ choose · Enter read historical response · Esc graph')
            frame.put(height-3,2,'Esc returns to the same work; ; opens draft editors and origins.','top_muted',width-4)
        else:
            lines = [line for text in self.content(mode) for line in [*wrap(text,width-6),'']]
            count=height-7; self.scroll=min(self.scroll,max(0,len(lines)-count))
            for i,line in enumerate(lines[self.scroll:self.scroll+count]): frame.put(3+i,3,line,'body',width-6)
            if not self.painted and hasattr(self.terminal.curses,'flushinp'): self.terminal.curses.flushinp()
            self.painted=True; self.seen_end |= self.scroll+count>=len(lines)
            frame.put(height-3,2,f'{self.scroll+1}–{min(len(lines),self.scroll+count)}/{len(lines)} · no science recorded','top_muted',width-4)
            hints = (('Enter check live gate · End read · Esc cancel' if isinstance(getattr(self,'worker',None),ProviderProposalWork) else
                       'Enter request example · End read · Esc cancel') if mode=='outbound' else
                'Enter stage batch · G graphs · End read · Esc keep mine' if mode=='compare' else
                'm continue writing · Esc cancel request' if mode=='wait' else
                'PgUp/PgDn · Home/End read · Esc return')
        frame.put(height-2,2,hints,'top_accent',width-4)
        frame.put(height-1,2,getattr(self.app,'recovery_error',None) or self.notice,'top_warning',width-4)
        return frame


def rendered_relation(body):
    return str(body.get('source_id',''))+' '+body.get('edge_type','')+' → '+str(body.get('target_id',''))+' / '+body.get('rationale','')


def proposals_ui(terminal):
    if not hasattr(terminal,'_proposals_ui'): terminal._proposals_ui=ProposalsUI(terminal)
    return terminal._proposals_ui
