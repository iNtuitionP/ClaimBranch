"""Personal record controls using the same editors, graph and saved writing."""
from copy import deepcopy
import json
from claimbranch.core.canonical import ContractError
from .personal_research import PersonalResearch
from .tui_model import TerminalWorkspace, wrap


class PersonalUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.service = PersonalResearch(terminal.app)
        self.notice = ''
        self.preview = None
        self.editor_return = self.preview_return = None
        self.scroll = 0
        self.painted = self.seen_end = False
        self.graphs = {}
        self.next_text = {}
        self.next_context = None

    def enter(self, kind, *, item_id=None):
        self.preview_return = self.terminal.modal if (self.terminal.modal or '').startswith('intake-') else None
        if kind == 'explanations':
            self.contexts = self.service.explanation_contexts()
            self.context_index = 0
            self.terminal.modal = 'personal-explanations'
            self.scroll = 0
        elif kind == 'next':
            from .tui import Buffer
            self.editor_return = self.preview_return
            self.next_context = self.terminal.app.episode_id
            self.terminal.buffers = [Buffer(self.next_text.get(self.next_context, ''))]
            self.terminal.modal = 'personal-next'
            self.notice = ''
        else:
            self.prepare(kind,item_id=item_id)

    def prepare(self, kind, **args):
        self.preview = self.service.prepare(kind,**args)
        self.terminal.modal = 'personal-preview'
        self.scroll = 0
        self.painted = self.seen_end = False
        self.notice = ''
        self.graphs = {}

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError,OSError,ValueError) as error:
            self.notice = str(error)

    def key(self, event):
        t = self.terminal
        if event == 'escape':
            if t.modal == 'personal-explanation-edit':
                self.checkpoint_explanation()
                t.modal = 'personal-topics'
            elif t.modal == 'personal-explanation-source':
                t.modal = self.explanation_return
            elif t.modal == 'personal-topics':
                self.checkpoint_explanation()
                if self.historical_explanation:
                    self.contexts = self.service.explanation_contexts()
                    self.context_index = min(self.context_index,max(0,len(self.contexts)-1))
                    t.modal = 'personal-explanations'
                else:
                    try:
                        self.refresh_explanation_preview('partial')
                    except (ContractError,ValueError):
                        self.service.cancel(); t.modal=None
                        self.terminal.app.message='Original partial explanation retained. Prepare another consequence comparison for changed scope.'
            elif t.modal == 'personal-explanations':
                self.service.cancel(); t.modal = None
            elif t.modal == 'personal-graph':
                t.modal = 'personal-preview'
            else:
                self.service.cancel()
                if t.modal=='personal-next':
                    self.next_text[self.next_context] = t.buffers[0].text
                    t.modal = self.editor_return
                else:
                    t.modal = self.preview_return
            return
        h,w = t.screen.getmaxyx()
        if h<18 or w<48:
            return
        if t.modal == 'personal-explanations':
            if event in ('up','down'):
                self.context_index = max(0,min(len(self.contexts)-1,self.context_index+(-1 if event=='up' else 1)))
            elif event == 'enter' and self.contexts:
                cause = self.contexts[self.context_index]['cause']
                self.contexts = self.service.explanation_contexts()
                entry = next(e for e in self.contexts if e['cause']==cause)
                self.start_explanation(entry['cause'],entry['topics'],entry['explanation']['entries'],historical=True)
            return
        if t.modal in ('personal-topics','personal-explanation-edit','personal-explanation-source'):
            self.explanation_key(event,w)
            return
        if t.modal == 'personal-next':
            if event == 'keep':
                self.next_text[self.next_context] = t.buffers[0].text
                self.preview_return='personal-next'
                self.prepare('next',question=t.buffers[0].text)
            else:
                t.buffers[0].key(event,w-8)
            return
        if t.modal == 'personal-graph':
            if event == 'tab': self.phase = 'before' if self.phase == 'after' else 'after'
            elif event == 'f': self.graphs[self.phase].fit_graph()
            else:
                graph = self.graphs[self.phase]
                if event in ('up','down','left','right'):
                    from .tui_graph import move_graph
                    move_graph(graph,event)
            return
        if self.preview is None:
            return
        if event in ('up','down','page-up','page-down','home','end'):
            self.scroll = (0 if event=='home' else 10**6 if event=='end' else max(0,self.scroll+{
                'up':-1,'down':1,'page-up':-8,'page-down':8}[event]))
        elif event in ('g','G') and self.preview.graphs:
            for phase, projection in self.preview.graphs.items():
                graph = TerminalWorkspace(t.app.paper.history,ai_off=True)
                graph.projection_only = True
                graph.graph_spacing,graph.density = t.app.graph_spacing,t.app.density
                graph.view = {**t.app.view,**projection}
                graph.nodes = {n['id']:n for n in projection['nodes']}
                graph._build_outline()
                graph.selected_id = t.app.selected_id if t.app.selected_id in graph._paths else graph.view['thesis_id']
                graph.selected_path = graph._paths[graph.selected_id]
                self.graphs[phase] = graph
            self.phase = 'after'; t.modal = 'personal-graph'
        elif event in ('1','2') and self.preview.kind=='reasoning' and self.preview.display['ai_origin_retained']:
            if not self.painted or not self.seen_end:
                self.notice = 'Read the complete consequence first; End reaches its last page.'
                return
            if event == '2':
                self.prepare('reasoning',explanation_state='leave-for-later',
                    explanation_entries=self.preview.display['explanation']['entries'])
            else:
                cause = self.preview.origin_record['cause']
                saved = next((e for e in self.service.explanation_contexts() if e['cause']==cause),None)
                self.start_explanation(cause,self.preview.display['explanation_topics'],
                    saved['explanation']['entries'] if saved else self.preview.display['explanation']['entries'])
        elif event == 'enter':
            if not self.painted or not self.seen_end:
                self.notice = 'Read the complete personal record preview first; End reaches its last page.'
                return
            if self.preview.kind=='reasoning' and not self.preview.display['recording_available']:
                self.notice = 'Choose 1 to review explanation or 2 to leave it for later. No science recorded.'
                return
            try:
                self.service.commit(self.preview)
            except (ContractError,OSError) as error:
                self.preview = None
                self.notice = str(error) + ' Esc returns to retained writing; prepare a new comparison.'
                return
            t.app.recovery_error = None
            if self.preview.kind=='next': self.next_text.pop(self.next_context, None)
            t.modal = None

    def start_explanation(self,cause,topics,entries,historical=False):
        self.cause = deepcopy(cause)
        self.topics = deepcopy(topics)
        self.entries = {e['topic_id']:deepcopy(e) for e in entries}
        self.historical_explanation = historical
        self.topic_index = self.scroll = 0
        self.terminal.modal = 'personal-topics'
        self.notice = ''

    def checkpoint_explanation(self):
        if not hasattr(self,'entries'): return
        if (self.terminal.modal == 'personal-explanation-edit' or
                self.terminal.modal == 'personal-explanation-source' and self.explanation_return == 'personal-explanation-edit'):
            topic = self.topics[self.topic_index]['id']
            prior = self.entries.get(topic, {'topic_id':topic,'text':'','reuse_rationale':False})
            self.entries[topic] = {**prior,'text':self.terminal.buffers[0].text}
        entries = [self.entries[t['id']] for t in self.topics if t['id'] in self.entries]
        if not entries: return
        known = next((e for e in self.terminal.app.paper._personal_explanations if e['cause']==self.cause),None)
        if known and known['explanation'] == {'state':'partial','entries':entries}: return
        if self.preview is not None and self.service.pending is self.preview and self.preview.origin_record and self.preview.origin_record['cause']==self.cause:
            self.service.keep_explanation(self.preview,entries=entries)
        else:
            self.service.keep_retained_explanation(self.cause,entries=entries)

    def refresh_explanation_preview(self,state):
        entries = [self.entries[t['id']] for t in self.topics if t['id'] in self.entries]
        try:
            self.prepare('reasoning',explanation_state=state,explanation_entries=entries)
            if self.preview.origin_record['cause'] != self.cause:
                raise ContractError('Scientific scope changed. Original partial writing remains saved; reopen a consequence comparison.')
        except (ContractError,ValueError):
            self.service.cancel()
            self.preview = None
            self.terminal.modal = 'personal-topics'
            raise

    def explanation_key(self,event,width):
        t = self.terminal
        if t.modal=='personal-explanation-source':
            if event in ('up','down','page-up','page-down','home','end'):
                self.scroll=(0 if event=='home' else 10**6 if event=='end' else max(0,self.scroll+{'up':-1,'down':1,'page-up':-8,'page-down':8}[event]))
            return
        if event=='source':
            self.explanation_return=t.modal; self.scroll=0; t.modal='personal-explanation-source'; return
        if t.modal=='personal-explanation-edit':
            if event=='keep':
                self.checkpoint_explanation(); t.modal='personal-topics'; self.notice='Partial writing retained with its original cause; no science or debt closure.'
            else: t.buffers[0].key(event,width-8)
            return
        if event in ('up','down'):
            self.topic_index=max(0,min(len(self.topics)-1,self.topic_index+(-1 if event=='up' else 1)))
        elif event=='enter':
            from .tui import Buffer
            topic=self.topics[self.topic_index]['id']
            t.buffers=[Buffer(self.entries.get(topic,{}).get('text',''))]
            t.modal='personal-explanation-edit'
        elif event=='r':
            topic=self.topics[self.topic_index]['id']
            prior=self.entries.get(topic,{'topic_id':topic,'text':'','reuse_rationale':False})
            self.entries[topic]={**prior,'reuse_rationale':not prior['reuse_rationale']}
            self.checkpoint_explanation()
        elif event=='v' and not self.historical_explanation:
            self.checkpoint_explanation(); self.refresh_explanation_preview('reviewed')

    def draw_explanation(self,frame):
        t=self.terminal; w,h=frame.width,frame.height
        mode=t.modal
        if mode=='personal-explanations':
            frame.put(0,2,'RETURN TO PERSONAL EXPLANATIONS','brand',w-4)
            count=max(1,(h-7)//3); offset=max(0,self.context_index-count+1)
            for i,entry in enumerate(self.contexts[offset:offset+count]):
                frame.put(3+3*i,2,('› ' if offset+i==self.context_index else '  ')+' / '.join(entry['cause']['owner']),'heading',w-4)
                recorded = entry.get('recorded_explanation')
                state = entry['explanation']['state']+(' / recorded '+recorded['state'] if recorded else '')
                frame.put(4+3*i,4,state+' / '+('changed science' if entry['changed_context'] else 'original science')+' / no closure','body',w-6)
            frame.put(h-2,2,'↑↓ choose · Enter original topics · Esc graph','top_accent',w-4)
            return frame
        frame.put(0,2,'PERSONAL EXPLANATION / unfinished writing' if mode!='personal-explanation-source' else 'ORIGINAL / CURRENT EXPLANATION BASIS','brand',w-4)
        if mode=='personal-explanation-source':
            from .paper_proposal_work import cause_science
            original=cause_science(t.app.paper.history,self.cause)
            current=t.app.service.query(self.cause['owner'][1],episode_id=self.cause['owner'][0])
            rows=['Original judgment: '+self.cause['judgment']['text'],'Original reason: '+self.cause['judgment']['rationale'],
                'ORIGINAL SCIENCE / '+json.dumps(original,ensure_ascii=False,indent=2),
                'CURRENT SCIENCE / '+json.dumps(current,ensure_ascii=False,indent=2),
                'Writing stays on the original cause. No automatic rebinding, comprehension verdict or debt closure.']
            lines=[line for text in rows for line in wrap(text,w-6)]
            count=h-7; self.scroll=min(self.scroll,max(0,len(lines)-count))
            for i,line in enumerate(lines[self.scroll:self.scroll+count]): frame.put(3+i,3,line,'body',w-6)
            frame.put(h-2,2,'End/PgDn read · Esc same editor and cursor','top_accent',w-4)
        elif mode=='personal-explanation-edit':
            topic=self.topics[self.topic_index]
            for i,line in enumerate(wrap(topic['prompt'],w-6)[:3]): frame.put(2+i,3,line,'body',w-6)
            frame.put(5,3,'Original reason: '+self.cause['judgment']['rationale'],'top_muted',w-6)
            frame.box(2,7,w-4,h-11,'PARTIAL TEXT / private checkpoint',True)
            buffer=t.buffers[0]; rows,row,col=buffer.position(w-8); offset=max(0,row-h+14)
            for i,(line,_,_) in enumerate(rows[offset:offset+h-13]): frame.put(8+i,4,line,'body',w-8)
            frame.cursor=(8+row-offset,min(w-5,4+col))
            frame.put(h-2,2,'Ctrl+S / Esc retain partial · Ctrl+O source · undo available','top_accent',w-4)
        else:
            for i,line in enumerate(wrap('Original reason: '+self.cause['judgment']['rationale'],w-6)[:2]): frame.put(2+i,3,line,'body',w-6)
            for i,topic in enumerate(self.topics):
                entry=self.entries.get(topic['id'],{})
                y=5+4*i
                frame.put(y,2,('› ' if i==self.topic_index else '  ')+topic['kind'],'heading',w-4)
                frame.put(y+1,4,topic['prompt'],'body',w-6)
                frame.put(y+2,4,'[original reason reused] ' if entry.get('reuse_rationale') else entry.get('text') or '(unfinished)','top_muted',w-6)
            frame.put(h-3,2,'AI origin stays separate. No score or accepted debt.','top_muted',w-4)
            frame.put(h-2,2,'Enter write · r reuse reason · Ctrl+O source · '+('Esc return' if self.historical_explanation else 'v reviewed · Esc partial'),'top_accent',w-4)
        frame.put(h-1,2,getattr(t.app,'recovery_error',None) or self.notice,'top_warning',w-4)
        return frame

    def draw(self, frame):
        from .tui import Frame, compose
        w,h = frame.width,frame.height
        frame = Frame(w,h)
        if w<48 or h<18:
            frame.put(1,1,'Personal controls paused','top_warning',w-2)
            frame.put(3,1,'Enlarge to 48 x 18. Esc returns.','top_muted',w-2)
            return frame
        mode = self.terminal.modal
        if mode in ('personal-explanations','personal-topics','personal-explanation-edit','personal-explanation-source'):
            return self.draw_explanation(frame)
        if mode == 'personal-next':
            frame.put(0,2,'NEXT RESEARCH QUESTION','brand',w-4)
            frame.put(2,2,'Earlier evidence, judgments and unfinished work stay available.','body',w-4)
            frame.box(2,4,w-4,h-8,'YOUR QUESTION / not saved until recording',True)
            buffer = self.terminal.buffers[0]
            rows,row,column = buffer.position(w-8)
            offset = max(0,row-h+11)
            for i,(line,_,_) in enumerate(rows[offset:offset+h-10]): frame.put(5+i,4,line,'body',w-8)
            frame.cursor = (5+row-offset,min(w-5,4+column))
            frame.put(h-2,2,'Ctrl+S preview next question · Esc cancel','top_accent',w-4)
            frame.put(h-1,2,self.notice,'top_warning',w-4)
            return frame
        if mode == 'personal-graph':
            frame = compose(self.graphs[self.phase],w,h)
            frame.fill(1,0,w,'canvas')
            frame.put(1,2,'PERSONAL COMPARISON / '+self.phase.upper()+' · nothing recorded yet','top_warning',w-4)
            frame.put(h-2,2,'Tab before/after · Arrows focus · f fit · Esc preview','top_accent',w-4)
            return frame
        frame.put(0,2,'PERSONAL RECORD PREVIEW','brand',w-4)
        frame.put(1,2,'No device approval. Enter records only the displayed personal history.','top_warning',w-4)
        if self.preview is None:
            frame.put(4,2,self.notice,'body',w-4)
            frame.put(h-2,2,'Esc returns; prepare another comparison.','top_accent',w-4)
            return frame
        rows = self.rows(w-6)
        count = h-7
        self.scroll = min(self.scroll,max(0,len(rows)-count))
        for i,line in enumerate(rows[self.scroll:self.scroll+count]): frame.put(3+i,3,line,'body',w-6)
        if not self.painted and hasattr(self.terminal.curses,'flushinp'):
            self.terminal.curses.flushinp()
        self.painted = True
        self.seen_end |= self.scroll+count>=len(rows)
        frame.put(h-3,2,self.notice or f'{self.scroll+1}–{min(len(rows),self.scroll+count)}/{len(rows)} · manuscript unchanged','top_muted',w-4)
        frame.put(h-2,2,('1 explain · 2 later · ' if self.preview.kind=='reasoning' and self.preview.display['ai_origin_retained'] else '')+'Enter record · G graph · End read · Esc cancel','top_accent',w-4)
        return frame

    def rows(self,width):
        app,display = self.terminal.app,self.preview.display
        rows = []
        def add(title,text):
            rows.extend(['',title]); rows.extend(wrap(text,width))
        add('DISPLAYED PERSONAL EFFECT',display['effect'])
        add('EPISODE / BRANCH',display['scope'])
        if 'result' in display:
            from .paper_intake import FIELDS
            for field,text in display['result'].items():
                if text:
                    label = (('CORRECTED STATEMENT' if self.preview.kind=='correct' else 'OBSERVATION TO RECORD') if field=='observation' else 'RUN REFERENCE / METHOD' if field=='run_ref' else 'CORRECTION REASON' if field=='rationale' and self.preview.kind=='correct' else FIELDS[field].upper())
                    add(label,text)
            add('SOURCE BOUNDARY',display['references'])
            add('ORIGINAL / CURRENT CONTEXT',display['current_context'])
            if 'previous' in display:
                previous=display['previous']
                add('EARLIER OBSERVATION / retained',previous['statement']+'\nValue: '+previous['value'])
            if 'question' in display: add('EXPERIMENT QUESTION',display['question'])
            if 'confirmation_note' in display: add('RECORDED CONFIRMATION / LIMITATIONS',display['confirmation_note'])
            for f,v in display.get('tentative_writing',{}).items():
                if v: add('TENTATIVE '+f.upper()+' / retained writing, not confirmed evidence',v)
            if 'unchanged_run' in display:
                run=display['unchanged_run']
                add('UNCHANGED RUN / source, method and conditions',run['source_ref']+'\n'+run['method']+'\n'+run['conditions'])
                add('UNCHANGED MEASUREMENT', '\n'.join(k.upper()+': '+v for k,v in run['metric'].items()))
        if 'changes' in display:
            for change in display['changes']:
                after=change['after']
                add(change['disposition'].upper()+' / '+after['kind'].upper(),app.review.change_text(change,self.preview.graphs))
            add('YOUR EXISTING JUDGMENT',display['judgment']['text'])
            add('YOUR EXISTING REASON',display['judgment']['rationale'])
            nodes={n['id']:n for n in self.preview.graphs['after']['nodes']}
            for title,field in (('MAY NEED CLAIM REVIEW','potentially_affected_claim_ids'),
                                ('OUTSIDE THIS PATH','outside_impact_claim_ids'),
                                ('UNCHANGED EVIDENCE','unchanged_evidence_ids')):
                add(title,'\n'.join(nodes.get(key,{}).get('content',{}).get('statement') or nodes.get(key,{}).get('content',{}).get('objective') or key
                                    for key in display['impact'][field]) or 'None')
            add('POTENTIALLY AFFECTED WRITING', ', '.join(display['impact']['potentially_affected_anchor_ids']) or 'None')
            add('AI ORIGIN', 'Retained AI influence in judgment and/or chosen items.'
                if display['ai_origin_retained'] else 'No AI influence recorded in this selection.')
            if display['ai_origin_retained']:
                add('PERSONAL EXPLANATION / separate choice',display['explanation']['state']+'; no comprehension verdict or accepted debt.')
                for entry in display['explanation']['entries']:
                    add('PARTIAL TOPIC / '+entry['topic_id'],entry['text']+ ('\nExplicit reuse of original reason.' if entry['reuse_rationale'] else ''))
                for lineage in display['item_origins']:
                    add('CHOSEN / REQUIRED ITEM ORIGIN',json.dumps(lineage,ensure_ascii=False,indent=2))
            if display.get('judgment_reuse'): add('JUDGMENT REUSE',display['judgment_reuse'])
            add('CONTRIBUTIONS / retained', '\n'.join(c['contributor'].upper()+': '+c['text'] for c in display['judgment']['history']))
            for judgment in display.get('source_judgments',[]):
                if judgment != display['judgment']:
                    add('EARLIER SOURCE JUDGMENT / '+judgment['episode_id'],judgment['text'])
                    add('EARLIER SOURCE REASON',judgment['rationale'])
                    add('EARLIER SOURCE CONTRIBUTIONS', '\n'.join(c['contributor'].upper()+': '+c['text'] for c in judgment['history']))
            add('FOLLOW-UP / unresolved',display['follow_up'])
        if self.preview.kind=='next':
            add('YOUR NEXT QUESTION',display['question'])
            add('UNFINISHED RESULTS',display['unfinished_results'])
        add('STORAGE / AUTHORITY',display['storage'])
        return rows


def personal_ui(terminal):
    if not hasattr(terminal,'_personal_ui'):
        terminal._personal_ui = PersonalUI(terminal)
    return terminal._personal_ui
