"""Exercise public personal actions in the runtime located in the current folder.

The artifact checker sends this script as code to a fresh extracted runtime. It
imports no repository tests/scripts and uses only disposable, novel content.
"""
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import tempfile
import time


class Terminal:
    def __enter__(self):
        import fcntl, pty, termios
        self.fcntl,self.termios=fcntl,termios
        self.master,self.slave=pty.openpty()
        self.original=termios.tcgetattr(self.slave)
        self.process=None; self.output=b''
        self.resize(132,38)
        return self

    def __exit__(self,*_):
        if self.process is not None and self.process.poll() is None:
            self.process.kill(); self.process.wait(timeout=5)
        os.close(self.master); os.close(self.slave)

    def resize(self,width,height):
        self.fcntl.ioctl(self.slave,self.termios.TIOCSWINSZ,struct.pack('HHHH',height,width,0,0))

    def launch(self,*arguments):
        self.output=b''
        self.process=subprocess.Popen([sys.executable,'-E','-s','-B','-m','claimbranch','project',*arguments],
            stdin=self.slave,stdout=self.slave,stderr=self.slave,
            env={**os.environ,'TERM':'xterm-256color','PYTHONUTF8':'1'})

    def expect(self,text,after=0):
        deadline=time.monotonic()+12; expected=text.encode()
        while expected not in self.output[after:] and time.monotonic()<deadline:
            if select.select([self.master],[],[],.05)[0]: self.output+=os.read(self.master,65536)
            elif self.process.poll() is not None: break
        if expected not in self.output[after:] or b'Traceback' in self.output:
            raise ValueError('Personal artifact terminal did not reach '+text+': '+self.output[-1200:].decode(errors='replace'))

    def send(self,text,expected=None):
        position=len(self.output); os.write(self.master,text.encode())
        if expected: self.expect(expected,position)
        elif text=='\x1b':
            deadline=time.monotonic()+.2
            while time.monotonic()<deadline:
                if select.select([self.master],[],[],.02)[0]: self.output+=os.read(self.master,65536)

    def close_app(self):
        self.send('q'); self.expect('ClaimBranch closed')
        deadline=time.monotonic()+5
        while self.process.poll() is None and time.monotonic()<deadline:
            if select.select([self.master],[],[],.01)[0]: self.output+=os.read(self.master,65536)
        if self.process.wait(timeout=5)!=0: raise ValueError('Personal terminal failed to exit')
        os.write(self.master,b'shell-inputX\x7f\n')
        if not select.select([self.slave],[],[],1)[0] or os.read(self.slave,1024)!=b'shell-input\n':
            raise ValueError('Personal terminal did not restore shell input')
        if self.termios.tcgetattr(self.slave)!=self.original: raise ValueError('Terminal modes changed')


def run_personal_smoke():
    import claimbranch
    from claimbranch.application.personal_project import PersonalProjectStore
    if not Path(claimbranch.__file__).resolve().is_relative_to(Path.cwd()):
        raise ValueError('Personal smoke imported another checkout')
    with tempfile.TemporaryDirectory(prefix='claimbranch-personal-새 연구-') as folder:
        root=Path(folder); paper=root/'paper'; work=root/'work'
        paper.mkdir(); work.mkdir(mode=0o700)
        subprocess.run(['git','init','-q',str(paper)],check=True)
        source=b'% claimbranch:start id=anchor\nUnfinished paper.\n% claimbranch:end id=anchor\n'
        manuscript=paper/'paper.tex'; manuscript.write_bytes(source)
        def command(*arguments):
            run=subprocess.run([sys.executable,'-E','-s','-B','-m','claimbranch','project',*arguments],
                               capture_output=True,text=True,encoding='utf-8',timeout=30)
            if run.returncode: raise ValueError('Personal artifact command failed: '+run.stderr[-1200:])
            return run
        init=['init','--directory',str(work),'--paper-root',str(paper),'--manuscript','paper.tex',
            '--title','Noise study','--thesis','입력 잡음은 지연에 영향을 준다.',
            '--question','어떤 입력 조건에서 지연이 바뀌는가?']
        command(*init,'--dry-run')
        if list(work.iterdir()): raise ValueError('Dry run wrote personal work')
        with Terminal() as t:
            t.launch(*init); t.expect('Type create'); t.send('create\r','ARGUMENT GRAPH')
            t.send(';'+ '\x1b[B'*5+'\n','DRAFT A RESULT')
            fields=['잡음에서 지연은 24 ms였다.','run-47; ten repeats','ssh://lab/run47.csv','fixed hardware',
                'latency','elapsed input to output','24','ms','clean inputs: 20 ms','other devices unmeasured',
                '이 환경에서는 잡음이 지연을 늘렸다.','입력 이외의 조건을 고정했다.']
            for i,value in enumerate(fields):
                t.send('\x1b[H'+'\x1b[B'*i+'\n','Ctrl+S keep')
                t.send('\x1b[200~'+value+'\x1b[201~\x13','Still unconfirmed')
            t.send('c','PERSONAL RECORD PREVIEW'); t.send('\x1b[F\x0c','Enter record')
            t.send('\n','Personal research recorded and saved')
            t.send(';'+'\x1b[H'+'\x1b[B'*2+'\n','WRITE A CLAIM')
            t.send('\n','CLAIM LEVEL'); t.send('\n','WRITE A CLAIM')
            t.send('\x1b[B\n','PARENT'); t.send('\n','WRITE A CLAIM')
            for i,value in ((2,'잡음 입력에서 지연이 늘어난다.'),(3,'Measured hardware only.')):
                t.send('\x1b[H'+'\x1b[B'*i+'\n','Ctrl+S returns')
                t.send('\x1b[200~'+value+'\x1b[201~\x13','WRITE A CLAIM')
            t.send('\x13','YOUR ARGUMENT DRAFTS')
            for target,kind,reason in (('claim','supports','24 ms exceeds 20 ms.'),('thesis','qualifies','Only measured hardware is covered.')):
                t.send('l','WRITE A SCIENTIFIC CHANGE')
                t.send('\n','FROM / SOURCE'); t.send('\x1b[B\n','WRITE A SCIENTIFIC CHANGE')
                t.send('\x1b[B\n','TO / CLAIM')
                t.send(('\x1b[F' if target=='claim' else '\x1b[H')+'\n','WRITE A SCIENTIFIC CHANGE')
                t.send('\x1b[H'+'\x1b[B'*2+'\n','SCIENTIFIC RELATIONSHIP')
                t.send(('\x1b[F' if kind=='qualifies' else '\x1b[H')+'\n','WRITE A SCIENTIFIC CHANGE')
                t.send('\x1b[H'+'\x1b[B'*3+'\n','Ctrl+S returns')
                t.send('\x1b[200~'+reason+'\x1b[201~\x13','WRITE A SCIENTIFIC CHANGE')
                t.send('\x13','YOUR ARGUMENT DRAFTS')
            t.send('\x1b'); t.send(';\x1b[F\x1b[A\x1b[A\n','PERSONAL RECORD PREVIEW')
            t.send('G','PERSONAL COMPARISON'); t.send('\t\x0c','BEFORE'); t.send('\x1b')
            t.send('\x1b[F\x0c','Enter record'); t.send('\n','Personal research recorded and saved')
            t.send(';'+ '\x1b[B'*5+'\n','DRAFT A RESULT')
            for i,value in ((0,'보정 후 지연은 23 ms였다.'),(6,'23'),(11,'Timer offset was 1 ms.')):
                t.send('\x1b[H'+'\x1b[B'*i+'\n','Ctrl+S keep')
                t.send('\x1b[200~'+value+'\x1b[201~\x13','Still unconfirmed')
            t.send('a','PERSONAL RECORD PREVIEW'); t.send('\x1b[F\x0c','Enter record')
            t.send('\n','Personal research recorded and saved')
            t.send(';\x1b[F\x1b[A\n','NEXT RESEARCH QUESTION')
            t.send('\x1b[200~다른 장치에서도 재현되는가?\x1b[201~\x13','PERSONAL RECORD PREVIEW')
            t.resize(80,24); t.send('\x1b[F\x0c','Enter record')
            t.send('\n','Personal research recorded and saved'); t.close_app()
            t.launch('open','--directory',str(work)); t.expect('PERSONAL'); t.close_app()
        with PersonalProjectStore(work) as store:
            project=store.load(); saved=project.payload; view=project.work.history.view('main')
            if len(project.work.history.episodes())!=2: raise ValueError('Later question not retained')
            if [e['value'] for e in view['evidence'][0]['history']]!=['24','23']: raise ValueError('Correction history lost')
            if view['judgments'][0]['rationale']!='입력 이외의 조건을 고정했다.': raise ValueError('Original reason lost')
            links=[r['body'] for r in view['changes'] if r['kind']=='scientific-edge']
            if len({r['source_id'] for r in links})!=1 or {r['edge_type'] for r in links}!={'supports','qualifies'}:
                raise ValueError('Shared evidence identity or relation meaning lost')
        original=(work/'personal.cbp').read_bytes()
        backup,export,restored=root/'backup',root/'export',root/'restored'
        for d in (backup,export,restored): d.mkdir(mode=0o700)
        command('backup','--directory',str(work),'--archive-directory',str(backup),'--json')
        command('export','--directory',str(work),'--archive-directory',str(export),'--json')
        command('restore','--directory',str(restored),'--archive-directory',str(backup),'--dry-run','--json')
        if list(restored.iterdir()): raise ValueError('Restore preview wrote work')
        command('restore','--directory',str(restored),'--archive-directory',str(backup),'--json')
        with PersonalProjectStore(restored) as store:
            if store.load().payload!=saved: raise ValueError('Restored saved content differs')
        if original!=(work/'personal.cbp').read_bytes() or source!=manuscript.read_bytes(): raise ValueError('Original changed')
        with Terminal() as t:
            t.resize(80,24); t.launch('open','--directory',str(restored)); t.expect('PERSONAL'); t.close_app()
    return ['personal-pty','personal-rescue']


if __name__=='__main__':
    print(json.dumps(run_personal_smoke()))
