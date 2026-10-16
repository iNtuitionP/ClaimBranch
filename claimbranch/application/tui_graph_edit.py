"""Direct selected-record editing with closed choices and detached comparison."""
from copy import deepcopy
from claimbranch.core.canonical import ContractError
from claimbranch.core.graph_vocabulary import SCIENTIFIC_EDGE_TYPES,NODE_KINDS
from .graph_edits import editable_record,prepare_edits,recheck_edits
from .tui_project_source import exact_path_buffer
from .tui_model import wrap


def flatten(body,prefix=''):
    result=[]
    for key,value in body.items():
        path=prefix+key
        if isinstance(value,dict):result.extend(flatten(value,path+'.'))
        else:result.append((path,', '.join(value) if isinstance(value,list) else '' if value is None else str(value)))
    return result


class GraphEditUI:
    def __init__(self,terminal):
        self.terminal=terminal;self.sessions={};self.notice='';self.scroll=0;self.field=0;self.candidate=None

    def open(self,record_id=None,*,proposal=None,proposal_source=None):
        from .personal_project import PersonalProjectRecovery
        app=self.terminal.app
        if not isinstance(app.recovery,PersonalProjectRecovery) or app.paper.history.schema_version not in (4, 5, 14):
            raise ContractError('Direct recording requires a saved personal paper profile; manual candidate creation remains available')
        if app.ref!='main' or app.view['episode']['status']!='active':raise ContractError('Choose active main before recording a revision')
        app.recovery.save(app)
        target_key=(app.episode_id,record_id or app.selected_id)
        if proposal is not None:
            self.record=deepcopy(proposal);self.proposed=deepcopy(proposal);self.proposal_source=deepcopy(proposal_source);self.origin='ai';self._fields()
        elif target_key in self.sessions:
            self.record,self.fields,self.origin,self.relinks,self.base_history,self.proposed,self.proposal_source=self.sessions[target_key]
        else:
            self.record=editable_record(app.recovery.project,target_key[1]);self.origin='human';self.proposed=None;self.proposal_source=None;self._fields()
        self.key=target_key
        if self.key not in self.sessions or proposal is not None:
            self.relinks=[];self.base_history=app.history_digest
        self.field=0;self.candidate=None;self.notice='Tab: next / Enter: choices / Ctrl+O: full text / Ctrl+K: replace kind / Ctrl+R: re-links / Ctrl+S: compare / Esc: keep input and return'
        self.terminal.modal='graph-edit-fields'

    def _fields(self):
        from .tui import Buffer
        self.fields=[('title',Buffer(self.record['title']))]
        self.fields.extend((k,Buffer(v)) for k,v in flatten(self.record['body']))
        self.fields.append(('reason',Buffer('')))

    def retain(self):self.sessions[self.key]=(deepcopy(self.record),self.fields,self.origin,deepcopy(self.relinks),self.base_history,deepcopy(self.proposed),deepcopy(self.proposal_source))

    def choices(self):
        name=self.fields[self.field][0];app=self.terminal.app
        try:body=self.value()[0]['body']
        except (KeyError,ValueError):body=self.record['body']
        if name=='status':return ['planned']
        if name=='edge_type':return list(SCIENTIFIC_EDGE_TYPES)
        if name=='role':return ['main','subclaim']
        if name=='kind':return ['text','figure','table','caption']
        if name=='source_id':return [k for k,n in sorted(app.nodes.items()) if n['kind'] in ('claim','observation','interpretation') and k!=body.get('target_id')]
        if name in ('target_id','claim_id','parent_ids','expresses'):
            result=[k for k,n in sorted(app.nodes.items()) if n['kind']=='claim' and (name!='target_id' or k!=body.get('source_id')) and (name!='parent_ids' or k!=self.record['id'])]
            if name=='parent_ids':result=[k for k in result if (k==app.view['thesis_id'])==(body.get('role')=='main')]
            return result
        if name=='observation_ids' or name=='plots':return [k for k,n in sorted(app.nodes.items()) if n['kind']=='observation']
        return []

    def value(self):
        record=deepcopy(self.record);values={k:b.text for k,b in self.fields};record['title']=values.pop('title');reason=values.pop('reason')
        for path,text in values.items():
            keys=path.split('.');target=record['body']
            for k in keys[:-1]:target=target[k]
            old=target[keys[-1]]
            target[keys[-1]]=[v.strip() for v in text.split(',') if v.strip()] if isinstance(old,list) else None if old is None and not text else text
        return record,reason

    def dispatch(self,event):
        try:self.key_event(event)
        except (ContractError,OSError,ValueError) as error:
            self.notice=str(error);self.candidate=None;self.terminal.modal='graph-edit-fields';self.retain()

    def key_event(self,event):
        if isinstance(event,str):event={'keep':'ctrl-s','source':'ctrl-o','reuse-reason':'ctrl-r','\x0b':'ctrl-k','\x0e':'ctrl-n','\x06':'ctrl-f'}.get(event,event)
        term=self.terminal;app=term.app;mode=term.modal
        if event=='escape':
            self.retain();self.candidate=None
            term.modal='graph-edit-fields' if mode in ('graph-edit-choice','graph-edit-kind','graph-edit-relinks','graph-edit-text') else None
            return
        h,w=term.screen.getmaxyx()
        if w<48 or h<18:return
        if mode=='graph-edit-fields':
            if event in ('tab','backtab','shift-tab'):
                self.field=(self.field+(1 if event=='tab' else -1))%len(self.fields)
            elif event=='enter' and self.fields[self.field][0]=='title':
                self.notice='Titles use one line. Tab selects content; Ctrl+O opens full prose.'
            elif event=='ctrl-o' and not self.choices() and self.fields[self.field][0]!='status':term.modal='graph-edit-text'
            elif event=='ctrl-n' and getattr(self,'edge_ids',None) and self.record['kind']=='scientific-edge':
                self.retain();self.edge_index=(self.edge_index+1)%len(self.edge_ids);self.open(self.edge_ids[self.edge_index])
            elif event=='ctrl-k':
                self.options=[k for k in ('claim','interpretation','experiment-plan') if k!=self.record['kind'] and (k!='interpretation' or not any(n['kind']=='interpretation' and n['content'].get('episode_id')==app.episode_id for n in app.nodes.values()))];self.option=0;term.modal='graph-edit-kind'
            elif event=='ctrl-r' and self.record['replaces']:
                self.options=[r['record_id'] for r in app.view['relations'] if r['scientific'] and self.record['replaces'] in (r['source_id'],r['target_id'])];self.option=0
                if self.options:term.modal='graph-edit-relinks'
                else:self.notice='No incident scientific edges; original structural links remain on the original identity'
            elif event=='ctrl-f':
                self.base_history=app.history_digest;self.notice='Current history selected explicitly; Ctrl+S compares your retained fields against it.'
            elif event=='ctrl-s':
                if app.history_digest!=self.base_history:raise ContractError('Graph changed during editing. Input retained; Ctrl+F explicitly re-bases for a fresh full comparison.')
                app.recovery.save(app);record,reason=self.value()
                self.candidate,self.review=prepare_edits(app.recovery.project,[record]+self.relinks,reason,'mixed' if self.proposed is not None and record!=self.proposed else self.origin,self.proposal_source)
                self.scroll=0;self.seen_end=False;term.modal='graph-edit-preview'
            elif event=='enter' and self.choices():
                self.options=self.choices();self.option=0;term.modal='graph-edit-choice'
            else:
                # Closed categories cannot be typed into free text.
                if self.fields[self.field][0] not in ('role','edge_type','kind','status'):self.fields[self.field][1].key(event,w-8)
            self.retain()
        elif mode=='graph-edit-text':
            self.fields[self.field][1].key(event,w-6);self.retain()
        elif mode in ('graph-edit-kind','graph-edit-relinks'):
            if event in ('up','down'):self.option=(self.option+(1 if event=='down' else -1))%len(self.options)
            elif mode=='graph-edit-kind' and event=='enter':
                import secrets
                old=self.record;kind=self.options[self.option]
                text=old['body'].get('statement') or old['body'].get('objective') or old['body'].get('question') or ''
                root=app.view['thesis_id']
                body=dict(role='main',statement=text,scope='',parent_ids=[root]) if kind=='claim' else dict(statement=text,observation_ids=[]) if kind=='interpretation' else dict(claim_id=root,objective=text,status='planned',conditions='',metric=dict(name='',definition='',unit='',comparison=''))
                self.record=dict(id='replacement-'+secrets.token_hex(8),kind=kind,body=body,title=old['title'],replaces=old['replaces'] or old['id']);self.relinks=[];self._fields();self.field=0;term.modal='graph-edit-fields';self.retain()
                self.notice='Original retained. Ctrl+R explicitly selects scientific re-links; all other links stay on original. Complete fields, then Ctrl+S.'
            elif mode=='graph-edit-relinks' and event==' ':
                key=self.options[self.option];existing=next((r for r in self.relinks if r['id']==key),None)
                if existing:self.relinks.remove(existing)
                else:
                    edge=editable_record(app.recovery.project,key)
                    for field in ('source_id','target_id'):
                        if edge['body'][field]==self.record['replaces']:edge['body'][field]=self.record['id']
                    self.relinks.append(edge)
            elif mode=='graph-edit-relinks' and event=='enter':term.modal='graph-edit-fields'
        elif mode=='graph-edit-choice':
            if event in ('up','down'):self.option=(self.option+(1 if event=='down' else -1))%len(self.options)
            elif event=='enter':
                key,buf=self.fields[self.field];v=self.options[self.option]
                # List fields are editable comma-separated and chooser toggles membership.
                existing=[s.strip() for s in buf.text.split(',') if s.strip()]
                if isinstance(self.record['body'].get(key),list):
                    existing.remove(v) if v in existing else existing.append(v);v=', '.join(existing)
                self.fields[self.field]=(key,exact_path_buffer(v));term.modal='graph-edit-fields';self.retain()
        elif mode=='graph-edit-preview':
            if event in ('up','down','page-up','page-down','home','end'):
                self.scroll=0 if event=='home' else 100000 if event=='end' else max(0,self.scroll+{'up':-1,'down':1,'page-up':-10,'page-down':10}[event])
            elif event=='e':term.modal='graph-edit-fields';self.candidate=None
            elif event=='r':
                if not self.seen_end:self.notice='Read the complete comparison with PgDn/End before recording';return
                self.confirmation=exact_path_buffer('');term.modal='graph-edit-confirm'
        elif mode=='graph-edit-confirm':
            if event=='enter':
                if self.confirmation.text!='record':self.notice='Type record exactly; Esc retains input';return
                app.recovery.save(app);recheck_edits(app.recovery.project,self.review);app.recovery.store.verify_unchanged()
                from .tui_project import project_workspace
                from .personal_research import _install
                project_workspace(self.candidate)
                app.recovery.store.save(self.candidate);app.recovery.project=self.candidate
                key=self.record['id'];_install(app,self.candidate.work.history,app.episode_id,'main',key)
                self.sessions.pop(self.key,None);self.candidate=None;term.modal=None
                app.message='Graph revision recorded. Originals and origins retained; dependencies need fresh review.'
            else:self.confirmation.key(event,w-8)

    def draw(self,frame):
        from .tui import Frame
        from .canonical_share import display_json
        out=Frame(frame.width,frame.height);w,h=out.width,out.height
        if w<48 or h<18:out.put(1,1,'Graph editor paused; resize to 48x18. Esc retains input.','top_warning',w-2);return out
        out.put(0,2,'EDIT RECORDED GRAPH / '+self.record['kind']+' / '+self.record['id'],'brand',w-4)
        mode=self.terminal.modal
        if mode=='graph-edit-fields':
            start=max(0,self.field-(h-9)//2)
            for i,(name,buf) in enumerate(self.fields[start:start+h-8],start):
                out.put(3+i-start,2,('> ' if i==self.field else '  ')+name+': '+buf.text,'accent' if i==self.field else 'body',w-4)
            # Full current field is readable/editable even when its row is abbreviated.
            current=self.fields[self.field];out.put(h-4,2,current[1].text[-(w-4):],'body',w-4)
        elif mode=='graph-edit-text':
            name,buf=self.fields[self.field];lines,row,col=buf.position(w-6);start=max(0,row-(h-8));out.put(2,2,name+' / Esc returns to fields','heading',w-4)
            for i,(text,_,_) in enumerate(lines[start:start+h-7]):out.put(4+i,3,text,'body',w-6)
            out.cursor=(4+row-start,3+col)
        elif mode in ('graph-edit-choice','graph-edit-kind','graph-edit-relinks'):
            start=max(0,self.option-(h-8)//2)
            for i,value in enumerate(self.options[start:start+h-7],start):
                label=value
                if mode=='graph-edit-kind':label=NODE_KINDS[value].label
                if mode=='graph-edit-relinks':label=('checked / ' if any(r['id']==value for r in self.relinks) else 'kept original / ')+value
                if value in self.terminal.app.nodes:label=self.terminal.app.title(value)+' / '+value
                out.put(3+i-start,2,('> ' if i==self.option else '  ')+label,'accent' if i==self.option else 'body',w-4)
        elif mode=='graph-edit-confirm':
            out.put(3,2,'Type record to save this exact revision. Esc retains input.','heading',w-4)
            out.put(5,2,self.confirmation.text,'body',w-4)
        else:
            lines=[]
            for line in display_json({k:v for k,v in self.review.items() if k!='project_digest'},indent=2).splitlines():lines+=wrap(line,w-4)
            visible=h-6;self.scroll=min(self.scroll,max(0,len(lines)-visible))
            for i,line in enumerate(lines[self.scroll:self.scroll+visible]):out.put(2+i,2,line,'body',w-4)
            if self.scroll+visible>=len(lines):self.seen_end=True
        if self.notice:out.put(h-3,2,self.notice,'top_warning',w-4)
        out.put(h-2,2,self.notice if mode=='graph-edit-fields' else 'PgDn/End read / e edit / r review / Esc keep input and return to graph','top_warning',w-4)
        return out


def graph_edit_ui(terminal):
    if not hasattr(terminal,'_graph_edit_ui'):terminal._graph_edit_ui=GraphEditUI(terminal)
    return terminal._graph_edit_ui
