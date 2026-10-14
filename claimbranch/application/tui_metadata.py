"""Extended-record entry from the current graph using the existing review surface."""
from claimbranch.core.canonical import ContractError
from .metadata_batch import prepare_batch,recheck_batch
from .canonical_share import display_json
from .tui_model import wrap


class MetadataUI:
    def __init__(self,terminal):
        self.terminal=terminal;self.path=None;self.candidate=None;self.review=None;self.raw=None
        self.notice='';self.scroll=0;self.seen_end=False

    def open(self):
        from .personal_project import PersonalProjectRecovery
        from .tui_project_source import exact_path_buffer
        if not isinstance(self.terminal.app.recovery,PersonalProjectRecovery) or self.terminal.app.paper.history.schema_version not in (4,5):
            raise ContractError('Extended records require a saved personal paper profile')
        self.path=exact_path_buffer('');self.notice='Choose an existing owner-private metadata-batch/v1 JSON file. Origins belong to each entry.'
        self.candidate=self.review=None;self.terminal.modal='metadata-input'

    def dispatch(self,event):
        try:self.key(event)
        except (ContractError,OSError) as error:
            self.notice=str(error);self.candidate=None;self.review=None;self.terminal.modal='metadata-input'

    def key(self,event):
        app=self.terminal.app
        if event=='escape':self.terminal.modal=None;self.candidate=self.review=None;return
        height,width=self.terminal.screen.getmaxyx()
        if width<48 or height<18:return
        if self.terminal.modal=='metadata-input':
            if event=='enter':
                from .project_commands import _read_argument_input
                app.recovery.save(app)
                self.raw=_read_argument_input(self.path.text)
                self.candidate,self.review=prepare_batch(app.recovery.project,self.raw)
                self.scroll=0;self.seen_end=False;self.terminal.modal='metadata-preview'
                if hasattr(self.terminal,'curses'):self.terminal.curses.flushinp()
                if hasattr(self.terminal,'pending'):self.terminal.pending.clear()
            else:self.path.key(event,min(100,width-6))
        elif self.terminal.modal=='metadata-preview' and event in ('up','down','page-up','page-down','home','end'):
            self.scroll=0 if event=='home' else 100000 if event=='end' else max(0,self.scroll+{'up':-1,'down':1,'page-up':-10,'page-down':10}[event])
        elif self.terminal.modal=='metadata-preview' and event=='r':
            if self.candidate is None or not self.review['valid']:raise ContractError('Fix the listed entries and prepare a new preview')
            if not self.seen_end:self.notice='Read the complete selected-record preview with PgDn/End first.';return
            self.terminal.modal='metadata-confirm'
            from .tui_project_source import exact_path_buffer
            self.confirmation=exact_path_buffer('')
        elif self.terminal.modal=='metadata-confirm':
            if event=='enter':
                if self.confirmation.text!='register':self.notice='Type register exactly, or Esc to cancel.';return
                from .project_commands import _read_argument_input
                from .personal_research import _install
                from .tui_project import project_workspace
                if _read_argument_input(self.path.text)!=self.raw:raise ContractError('Input changed; prepare a fresh preview')
                app.recovery.save(app);recheck_batch(app.recovery.project,self.review);app.recovery.store.verify_unchanged()
                project_workspace(self.candidate) # Candidate must reconstruct before the only saved write.
                app.recovery.store.save(self.candidate);app.recovery.project=self.candidate
                _install(app,self.candidate.work.history,app.episode_id,app.ref,app.selected_id)
                self.terminal.modal=None;app.message='Extended records saved together; declared origins retained. Manuscript unchanged.'
                self.candidate=self.review=None
            else:self.confirmation.key(event,min(100,width-6))

    def draw(self,frame):
        from .tui import Frame
        frame=Frame(frame.width,frame.height);w,h=frame.width,frame.height
        if w<48 or h<18:
            frame.put(2,1,'Extended record input paused. Resize to 48 x 18; Esc returns.','top_warning',w-2);return frame
        frame.put(0,3,'EXTENDED RECORDS / HUMAN REVIEW','brand',w-6)
        mode=self.terminal.modal
        if mode=='metadata-input':
            frame.put(3,3,'Private metadata batch path (not a command):','heading',w-6)
            frame.put(5,3,self.path.text,'body',w-6)
            frame.put(h-2,3,'Enter: preview / Esc: return. No file read before preview.','top_accent',w-6)
        elif mode=='metadata-confirm':
            frame.put(3,3,'Type register to save the exact selected batch; Esc cancels.','heading',w-6)
            frame.put(5,3,self.confirmation.text,'body',w-6)
        else:
            shown={k:v for k,v in self.review.items() if k!='project_digest'}
            lines=[]
            for line in display_json(shown,indent=2).splitlines():lines.extend(wrap(line,w-6))
            visible=h-7;self.scroll=min(self.scroll,max(0,len(lines)-visible))
            for i,line in enumerate(lines[self.scroll:self.scroll+visible]):frame.put(2+i,3,line,'body',w-6)
            if self.scroll+visible>=len(lines):self.seen_end=True
            frame.put(h-2,3,'PgDn/End: read / r: review recording / Esc: cancel','top_accent',w-6)
        frame.put(h-4,3,self.notice,'top_warning',w-6)
        return frame


def metadata_ui(terminal):
    if not hasattr(terminal,'_metadata_ui'):terminal._metadata_ui=MetadataUI(terminal)
    return terminal._metadata_ui
