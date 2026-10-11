"""Real PTY coverage; this is not a human IME, SSH or screen-reader certification."""
import importlib.util
import os
from pathlib import Path
import re
import select
import signal
import shlex
import struct
import subprocess
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

if os.name == "posix":
    import fcntl
    import pty
    import termios


ROOT = Path(__file__).resolve().parents[2]
SUPPORTED = os.name == "posix" and importlib.util.find_spec("curses") is not None


@unittest.skipUnless(SUPPORTED, "requires a Unix PTY and Python curses")
class TerminalProcessTests(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.original = termios.tcgetattr(self.slave)
        self.process = None
        self.job_group = None
        self.output = b""
        self.resize(132, 38)

    def tearDown(self):
        if self.process is not None and self.process.poll() is None:
            if self.job_group is not None:
                try: os.killpg(self.job_group, signal.SIGKILL)
                except ProcessLookupError: pass
            self.process.kill()
        os.close(self.master)
        os.close(self.slave)
        if self.process is not None:
            self.process.wait(timeout=5)

    def launch(self, *, term="xterm-256color", monochrome=False, navigation="outline", draft_file=None, no_job_control=False, series=False, merge_example=False, ai_off=False, work_dir=None, project_dir=None, personal_arguments=None):
        env = {**os.environ, "TERM": term, "PYTHONUTF8": "1"}
        env.pop("NO_COLOR", None)
        if monochrome:
            env["NO_COLOR"] = "1"
        arguments = ([sys.executable, '-m', 'claimbranch', 'demo', 'project', 'open',
                      '--directory', str(project_dir), '--project-id', 'new-paper'] if project_dir else
                     [sys.executable, "-m", "claimbranch", "demo", "tui", "--layout", "three",
                                         "--navigation", navigation] + (["--draft-file", str(draft_file)] if draft_file else [])
                                        + (["--merge-example" if merge_example else "--series", "--variant", "recorded"] if series or merge_example else [])
                                        + (["--ai-off"] if ai_off else [])
                                        + (["--work-dir", str(work_dir)] if work_dir else []))
        if personal_arguments is not None:
            arguments = [sys.executable, '-B', '-m', 'claimbranch', 'project', *personal_arguments]
        self.process = subprocess.Popen(arguments,
                                        cwd=ROOT, env=env, stdin=self.slave, stdout=self.slave, stderr=self.slave,
                                        **({'start_new_session': True} if no_job_control else {'process_group': 0}))

    def test_personal_init_writing_resize_restart_without_device_keys(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        with tempfile.TemporaryDirectory() as folder:
            paper, directory = Path(folder) / 'paper', Path(folder) / 'personal'
            paper.mkdir(); directory.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True)
            source = b'% claimbranch:start id=anchor\nUndecided.\n% claimbranch:end id=anchor\n'
            path = paper / 'paper.tex'; path.write_bytes(source)
            self.launch(personal_arguments=['init', '--directory', str(directory),
                '--paper-root', str(paper), '--manuscript', 'paper.tex',
                '--title', 'New research', '--thesis', '측정 조건에 따라 범위를 정한다.',
                '--question', '어떤 조건을 더 확인할까?'])
            self.expect('Type create')
            self.send('create\r', 'ARGUMENT GRAPH')
            self.expect('PERSONAL'); self.expect('AI OFF')
            self.send('e', 'YOUR JUDGMENT')
            self.send('\x1b[200~아직 판단 중이다.\x1b[201~\t조건을 더 확인한다.\x13', 'Draft kept')
            self.send('n', 'MY NOTE')
            self.send('\x1b[200~직접 쌓아가는 논지\x1b[201~\r둘째 줄\x13', 'Note kept')
            self.resize(80, 24); self.send('\x0c', 'PERSONAL')
            self.send('q'); self.assert_restored(0)
            with PersonalProjectStore(directory) as store:
                saved = store.load(); app = project_workspace(saved)
                self.assertEqual('아직 판단 중이다.', app.draft()['text'])
                self.assertEqual('조건을 더 확인한다.', app.draft()['rationale'])
                self.assertIn('직접 쌓아가는 논지\n둘째 줄', app.notes.values())
                self.assertFalse(app.paper.ai_available)
                original = saved.work.history.manifest()
            self.output = b''
            self.launch(personal_arguments=['open', '--directory', str(directory)])
            self.expect('PERSONAL'); self.expect('ARGUMENT GRAPH')
            self.send('e\x0c', '아직 판단 중이다.')
            self.resize(132, 38); self.send('\x0c', 'YOUR JUDGMENT')
            self.send('\x1b[200~ 추가 확인\x1b[201~')
            self.send('\x03'); self.assert_restored(130)
            with PersonalProjectStore(directory) as store:
                saved = store.load(); app = project_workspace(saved)
                self.assertEqual(original, saved.work.history.manifest())
                self.assertEqual('아직 판단 중이다.', app.draft()['text'])
                self.assertIn('추가 확인', app.unfinished[(*app.work_key(), 'edit')][0])
            self.assertEqual(source, path.read_bytes())

    def test_personal_public_backup_restore_reopens_saved_and_unfinished_writing(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project import project_workspace
        with tempfile.TemporaryDirectory() as folder:
            paper, work, archive, restored = [Path(folder)/name for name in ('paper','work','backup','restored')]
            paper.mkdir()
            for path in (work,archive,restored): path.mkdir(mode=0o700)
            subprocess.run(['git','init','-q',str(paper)],check=True)
            manuscript=paper/'paper.tex'
            source=b'% claimbranch:start id=anchor\nUndecided.\n% claimbranch:end id=anchor\n'
            manuscript.write_bytes(source)
            self.launch(personal_arguments=['init','--directory',str(work),'--paper-root',str(paper),
                '--manuscript','paper.tex','--title','Restore study','--thesis','측정 조건이 논지의 범위를 정한다.',
                '--question','어떤 조건을 더 확인할까?'])
            self.expect('Type create'); self.send('create\r','ARGUMENT GRAPH')
            self.send('e','YOUR JUDGMENT')
            self.send('\x1b[200~판단을 한 번 쓴다.\x1b[201~\t조건은 아직 검토 중이다.\x13','Draft kept')
            self.send('e\x0c','판단을 한 번 쓴다.')
            self.send('\x1b[200~ 미완성 입력\x1b[201~')
            self.send('\x03'); self.assert_restored(130)
            original=(work/'personal.cbp').read_bytes()
            def command(*arguments):
                result=subprocess.run([sys.executable,'-B','-m','claimbranch','project',*arguments],
                    cwd=ROOT,capture_output=True,text=True,timeout=30)
                self.assertEqual(0,result.returncode,result.stderr)
                return result
            command('backup','--directory',str(work),'--archive-directory',str(archive),'--json')
            command('restore','--directory',str(restored),'--archive-directory',str(archive),'--dry-run','--json')
            self.assertEqual([],list(restored.iterdir()))
            command('restore','--directory',str(restored),'--archive-directory',str(archive),'--json')
            self.assertEqual(original,(work/'personal.cbp').read_bytes())
            self.assertEqual(source,manuscript.read_bytes())
            self.output=b''; self.resize(80,24)
            self.launch(personal_arguments=['open','--directory',str(restored)])
            self.expect('PERSONAL'); self.send('e\x0c','판단을 한 번 쓴다.')
            self.send('\x1b'); self.send('q'); self.assert_restored(0)
            with PersonalProjectStore(restored) as store:
                app=project_workspace(store.load())
                self.assertEqual('판단을 한 번 쓴다.',app.draft()['text'])
                self.assertIn('미완성 입력',app.unfinished[(*app.work_key(),'edit')][0])
                self.assertFalse(app.paper.ai_available)

    def test_personal_result_record_correction_next_question_and_restart(self):
        from claimbranch.application.personal_project import PersonalProjectStore
        with tempfile.TemporaryDirectory() as folder:
            paper,directory=Path(folder)/'paper',Path(folder)/'work'
            paper.mkdir(); directory.mkdir(mode=0o700)
            subprocess.run(['git','init','-q',str(paper)],check=True)
            source=b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
            (paper/'paper.tex').write_bytes(source)
            self.launch(personal_arguments=['init','--directory',str(directory),'--paper-root',str(paper),
                '--manuscript','paper.tex','--title','Novel paper','--thesis','입력 잡음은 지연에 영향을 준다.',
                '--question','어떤 입력 조건에서 지연이 바뀌는가?'])
            self.expect('Type create'); self.send('create\r','ARGUMENT GRAPH')
            self.send(';'+ '\x1b[B'*5+'\n','DRAFT A RESULT')
            fields=['잡음에서 지연은 24 ms였다.','run-47; ten repeats','ssh://lab/run47.csv','fixed hardware',
                'latency','elapsed input to output','24','ms','clean inputs: 20 ms','other devices unmeasured',
                '이 환경에서는 잡음이 지연을 늘렸다.','입력 이외의 조건을 고정했다.']
            for i,value in enumerate(fields):
                self.send('\x1b[H'+'\x1b[B'*i+'\n','Ctrl+S keep')
                self.send('\x1b[200~'+value+'\x1b[201~\x13','Still unconfirmed')
            self.send('c','PERSONAL RECORD PREVIEW')
            self.send('\x1b[F\x0c','Enter record')
            self.send('\n','Personal research recorded and saved')
            self.send(';'+'\x1b[H'+'\x1b[B'*2+'\n','WRITE A CLAIM')
            self.send('\n','CLAIM LEVEL'); self.send('\n','WRITE A CLAIM')
            self.send('\x1b[B\n','PARENT'); self.send('\n','WRITE A CLAIM')
            for index, value in ((2,'잡음 입력에서 지연이 늘어난다.'),(3,'Measured hardware only.')):
                self.send('\x1b[H'+'\x1b[B'*index+'\n','Ctrl+S returns')
                self.send('\x1b[200~'+value+'\x1b[201~\x13','WRITE A CLAIM')
            self.send('\x13','YOUR ARGUMENT DRAFTS')
            for target, relationship, rationale in (('claim','supports','24 ms exceeds the clean 20 ms baseline.'),
                                                     ('thesis','qualifies','Only the measured hardware is covered.')):
                self.send('l','WRITE A SCIENTIFIC CHANGE')
                self.send('\n','FROM / SOURCE'); self.send('\x1b[B\n','WRITE A SCIENTIFIC CHANGE')
                self.send('\x1b[B\n','TO / CLAIM')
                self.send(('\x1b[F' if target=='claim' else '\x1b[H')+'\n','WRITE A SCIENTIFIC CHANGE')
                self.send('\x1b[H\x1b[B\x1b[B\n','SCIENTIFIC RELATIONSHIP')
                self.send(('\x1b[F' if relationship=='qualifies' else '\x1b[H')+'\n','WRITE A SCIENTIFIC CHANGE')
                self.send('\x1b[H'+'\x1b[B'*3+'\n','Ctrl+S returns')
                self.send('\x1b[200~'+rationale+'\x1b[201~\x13','WRITE A SCIENTIFIC CHANGE')
                self.send('\x13','YOUR ARGUMENT DRAFTS')
            self.send('\x1b')
            self.send(';\x1b[F\x1b[A\x1b[A\n','PERSONAL RECORD PREVIEW')
            self.send('G','PERSONAL COMPARISON'); self.send('\t\x0c','BEFORE')
            self.send('\x1b'); self.send('\x1b[F\x0c','Enter record')
            self.send('\n','Personal research recorded and saved')
            self.send(';'+ '\x1b[B'*5+'\n','DRAFT A RESULT')
            for i,value in ((0,'보정 후 지연은 23 ms였다.'),(6,'23'),(11,'Timer offset was 1 ms.')):
                self.send('\x1b[H'+'\x1b[B'*i+'\n','Ctrl+S keep')
                self.send('\x1b[200~'+value+'\x1b[201~\x13','Still unconfirmed')
            self.send('a','PERSONAL RECORD PREVIEW'); self.send('\x1b[F\x0c','Enter record')
            self.send('\n','Personal research recorded and saved')
            self.send(';\x1b[F\x1b[A\n','NEXT RESEARCH QUESTION')
            self.send('\x1b[200~다른 장치에서도 재현되는가?\x1b[201~\x13','PERSONAL RECORD PREVIEW')
            self.send('\x1b','NEXT RESEARCH QUESTION'); self.send('\x1b')
            self.send(';\x1b[F\x1b[A\n','NEXT RESEARCH QUESTION')
            self.send('\x13','PERSONAL RECORD PREVIEW')
            self.resize(80,24); self.send('\x1b[F\x0c','Enter record')
            self.send('\n','Personal research recorded and saved'); self.send('q'); self.assert_restored(0)
            with PersonalProjectStore(directory) as store:
                saved=store.load(); history=saved.work.history
                self.assertEqual(2,len(history.episodes()))
                self.assertEqual(['24','23'],[e['value'] for e in history.view('main')['evidence'][0]['history']])
                self.assertEqual('입력 이외의 조건을 고정했다.',history.view('main')['judgments'][0]['rationale'])
                links = [change for change in history.view('main')['changes'] if change['kind']=='scientific-edge']
                self.assertEqual({'supports','qualifies'}, {edge['body']['edge_type'] for edge in links})
                self.assertEqual(1,len({edge['body']['source_id'] for edge in links}))
            self.output=b''; self.launch(personal_arguments=['open','--directory',str(directory)])
            self.expect('PERSONAL'); self.send('q'); self.assert_restored(0)
            self.assertEqual(source,(paper/'paper.tex').read_bytes())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_external_checkpoint_failure_details_and_live_writing_in_real_terminal(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.fixtures import replay_example
        app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        app.keep_note('Earlier saved note')
        with tempfile.TemporaryDirectory() as directory:
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher,
                        project_id=app.view['project_id'], recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(app))
            path = Path(directory) / 'work.cbw'; earlier = path.read_bytes()
            self.launch(navigation='graph', series=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.send('n', 'MY NOTE')
            self.send('\x1b[200~ / 최신 글은 메모리에 남는다\x1b[201~\x13', 'Note kept')
            deadline = time.monotonic() + 8
            while path.read_bytes() == earlier and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertNotEqual(earlier, path.read_bytes())
            path.write_bytes(earlier)  # An external writer returns the earlier valid ciphertext.
            self.expect('DRAFT SAVE FAILED', after=len(self.output), timeout=8)
            self.send(';', 'Inspect writing save status')
            self.send('\r', 'WRITING SAVE')
            self.resize(80, 24); self.send('\x0c', 'copy newer writing')
            self.expect('Saving is blocked')
            self.resize(44, 16); self.send('\x0c', 'Save details paused')
            self.resize(48, 18); self.send('\x0c', 'WRITING SAVE')
            self.send('\x1b[6~', 'work changed outside')
            self.resize(132, 38); self.send('\x0c', 'WRITING SAVE')
            self.send('\x1b')
            self.send('\x0c', '; actions')
            self.send('n\x0c', '최신 글은')
            self.expect('메모리에 남는다')
            self.send('\x1b')
            self.send('q'); self.expect('DRAFT SAVE FAILED')
            self.assertIsNone(self.process.poll())
            self.assertEqual(earlier, path.read_bytes())
            self.send('\x03'); self.assert_restored(130)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=app.view['project_id']) as store:
                    saved = store.load()
            again = TerminalWorkspace(saved.history, ai_off=True); restore(again, saved)
            self.assertEqual('Earlier saved note', again.note())
            self.assertEqual(app.paper.history.manifest(), saved.history.manifest())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_project_connection_relocation_refresh_and_restart_in_terminal(self):
        from claimbranch.application.project_work import ProjectWorkStore, preview_association
        from claimbranch.application.tui_project import prepare_project, project_workspace
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.core.canonical import decode
        with tempfile.TemporaryDirectory() as folder:
            paper, directory = Path(folder) / 'paper', Path(folder) / 'work'
            paper.mkdir(); directory.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True)
            source = b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
            (paper / 'paper.tex').write_bytes(source)
            preview = preview_association(paper, 'paper.tex', 'anchor', directory)
            project = prepare_project(preview, project_id='new-paper', title='Unfinished study',
                                      thesis='A tentative claim', question='What conditions matter?')
            with MacWorkCipher() as cipher:
                with ProjectWorkStore.create(directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                    store.save(project, preview=preview)
            self.launch(project_dir=directory)
            self.expect('ARGUMENT GRAPH', timeout=30)
            self.send('n', 'MY NOTE')
            self.send('\x1b[200~연결을 바꿔도 유지할 노트\x1b[201~\x13', 'Note kept')
            moved = Path(folder) / 'moved paper'; paper.rename(moved)
            self.send(';', 'ACTIONS /')
            self.send('\x1b[F\x1b[A\r', 'PAPER CONNECTION')
            self.send('r', 'New location')
            self.send('\x1b[200~' + str(moved) + '\x1b[201~\r', 'RELOCATE')
            self.send('\x1b', 'PAPER CONNECTION')
            self.send('r', 'New location')
            self.send('\x1b[200~' + str(moved) + '\x1b[201~\r', 'RELOCATE')
            self.resize(80, 24); self.send('\x0c', 'PAPER CONNECTION')
            self.send('\x1b[F', 'No manuscript write')
            self.send('a', 'Connection saved')
            self.send('\x1b', 'Paper connection updated')
            self.send('q'); self.assert_restored(0)
            (moved / 'paper.tex').write_bytes(source + b'% edited source\n')
            self.output = b''
            self.launch(project_dir=directory)
            self.expect('SOURCE AT OPEN:', timeout=30)
            self.send(';', 'ACTIONS /')
            self.send('\x1b[F\x1b[A\r', 'PAPER CONNECTION')
            self.resize(144, 42); self.send('\x0c', 'PAPER CONNECTION')
            before = (directory / 'work.cbw').read_bytes()
            self.send('fa', 'REFRESH')
            self.send('\x0c', 'REFRESH')
            self.assertEqual(before, (directory / 'work.cbw').read_bytes())
            self.send('\x1b', 'PAPER CONNECTION')
            self.resize(80, 24); self.send('\x0c', 'PAPER CONNECTION')
            self.send('f', 'REFRESH')
            self.send('\x1b[F', 'v3 project reader')
            self.send('a', 'Connection saved')
            self.send('\x1b', 'ARGUMENT GRAPH')
            self.send('q'); self.assert_restored(0)
            with MacWorkCipher() as cipher:
                with ProjectWorkStore(directory, cipher=cipher, project_id='new-paper') as store:
                    saved = store.load()
            self.assertEqual('연결을 바꿔도 유지할 노트', project_workspace(saved).note())
            self.assertEqual(project.work.history.manifest(), saved.work.history.manifest())
            self.assertEqual(3, len(decode(saved.payload)['associations']))
            self.assertEqual('unchanged-since-refresh', saved.source_status())
            self.assertEqual(source + b'% edited source\n', (moved / 'paper.tex').read_bytes())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_empty_project_first_question_cancel_start_and_reopen(self):
        from claimbranch.application.project_work import ProjectWorkStore, preview_association, initialize_project
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.core.canonical import decode
        with tempfile.TemporaryDirectory() as folder:
            paper, directory = Path(folder) / 'paper', Path(folder) / 'work'
            paper.mkdir(); directory.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True)
            source = b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
            path = paper / 'paper.tex'; path.write_bytes(source)
            preview = preview_association(paper, 'paper.tex', 'anchor', directory)
            project = initialize_project(preview, project_id='new-paper', title='Unfinished experiment',
                                         thesis_id='thesis', thesis='A tentative working thesis')
            with MacWorkCipher() as cipher:
                with ProjectWorkStore.create(directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                    store.save(project, preview=preview)
            before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
            for interruption, code in (('eof', 0), ('interrupt', 130)):
                self.output = b''
                self.launch(project_dir=directory)
                self.expect('First unresolved research question:', timeout=30)
                if interruption == 'eof':
                    self.send('\x04')
                else:
                    self.process.send_signal(signal.SIGINT)
                self.expect('No question was saved; the existing project is unchanged.')
                self.assertEqual(code, self.process.wait(timeout=5))
                self.assertEqual(self.original, termios.tcgetattr(self.slave))
                self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()})
            self.output = b''
            self.launch(project_dir=directory)
            self.expect('First unresolved research question:', timeout=30)
            self.send('취소하는 질문\r', 'First question preview')
            self.send('\r', 'Cancelled. Existing project')
            self.assertEqual(0, self.process.wait(timeout=5))
            self.assertEqual(self.original, termios.tcgetattr(self.slave))
            self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()})
            self.output = b''
            self.launch(project_dir=directory)
            self.expect('First unresolved research question:', timeout=30)
            self.send('어떤 조건을 확인할까?\r', 'First question preview')
            self.send('start\r', 'ARGUMENT GRAPH')
            self.expect('AI OFF')
            self.resize(80, 24); self.send('\x0c', 'ARGUMENT GRAPH')
            self.send('q'); self.assert_restored(0)
            self.output = b''
            self.launch(project_dir=directory)
            self.expect('ARGUMENT GRAPH', timeout=30)
            self.assertNotIn(b'First unresolved research question:', self.output)
            self.send('q'); self.assert_restored(0)
            with MacWorkCipher() as cipher:
                with ProjectWorkStore(directory, cipher=cipher, project_id='new-paper') as store:
                    saved = store.load()
            self.assertEqual(1, len(saved.work.history.episodes()))
            self.assertEqual('어떤 조건을 확인할까?', decode(saved.work.history.commands[-1])['payload']['question'])
            self.assertEqual(project.work.history.seed, saved.work.history.seed)
            self.assertEqual(source, path.read_bytes())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_selected_project_manual_writing_and_restart_in_real_terminal(self):
        from claimbranch.application.project_work import ProjectWorkStore, preview_association
        from claimbranch.application.tui_project import prepare_project, project_workspace
        from claimbranch.application.work_cipher import MacWorkCipher
        with tempfile.TemporaryDirectory() as folder:
            paper, directory = Path(folder) / 'paper', Path(folder) / 'work'
            paper.mkdir(); directory.mkdir(mode=0o700)
            subprocess.run(['git', 'init', '-q', str(paper)], check=True)
            source = b'% claimbranch:start id=anchor\nUnfinished.\n% claimbranch:end id=anchor\n'
            path = paper / 'paper.tex'; path.write_bytes(source)
            preview = preview_association(paper, 'paper.tex', 'anchor', directory)
            project = prepare_project(preview, project_id='new-paper', title='New experiment',
                                      thesis='An unresolved working thesis', question='Which conditions matter?')
            with MacWorkCipher() as cipher:
                with ProjectWorkStore.create(directory, cipher=cipher, project_id='new-paper', recovery_key=os.urandom(32)) as store:
                    store.save(project, preview=preview)
            self.launch(project_dir=directory)
            self.expect('ARGUMENT GRAPH', timeout=30)
            self.expect('AI OFF')
            self.send('e', 'YOUR JUDGMENT')
            self.send('\x1b[200~아직 판단 중이다.\x1b[201~\t조건을 더 확인한다.\x13', 'Draft kept')
            self.send('n', 'MY NOTE')
            self.send('\x1b[200~직접 쌓아가는 논지\x1b[201~\x13', 'Note kept')
            self.send('q'); self.assert_restored(0)
            path.write_bytes(source + b'% external edit\n')
            self.launch(project_dir=directory)
            self.expect('SOURCE AT OPEN:', timeout=30)
            self.send('e\x0c', '아직 판단 중이다.')
            self.resize(80, 24); self.send('\x0c', 'YOUR JUDGMENT')
            self.send('\x1b')
            self.send('\x03'); self.assert_restored(130)
            with MacWorkCipher() as cipher:
                with ProjectWorkStore(directory, cipher=cipher, project_id='new-paper') as store:
                    saved = store.load()
                    app = project_workspace(saved)
                    self.assertEqual('아직 판단 중이다.', app.draft()['text'])
                    self.assertIn('직접 쌓아가는 논지', app.notes.values())
                    self.assertEqual(project.work.history.manifest(), saved.work.history.manifest())
                    self.assertEqual('source-changed-reconciliation-required', saved.source_status())
            self.assertEqual(source + b'% external edit\n', path.read_bytes())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_judgment_reopens_in_actual_terminal(self):
        self.encrypted_judgment_roundtrip()

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_checkpoint_interrupt_retains_active_result_editor(self):
        self.encrypted_judgment_roundtrip(interrupt_during_result=True)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_checkpoint_interrupt_retains_active_claim_editor(self):
        self.encrypted_judgment_roundtrip(interrupt_during_claim=True)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_review_answer_interrupt_keeps_original_context(self):
        self.encrypted_review_writing_roundtrip(answer=True)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_scientific_field_interrupt_keeps_unstaged_input(self):
        self.encrypted_review_writing_roundtrip(answer=False)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_wording_interrupt_retains_original_source(self):
        from types import SimpleNamespace
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_actions import ActionsUI
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.fixtures import replay_example
        from tests.application.test_tui_wording_recovery import SOURCE
        app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        item = next(x for x in app.service.pending_work()['items'] if x['kind'] == 'manuscript')
        session = app.manuscript.open(item['id'])
        session.update_source(app.paper.history, source=SOURCE)
        session.draft.edit('이전 문구', 'Original reason.')
        index = next(i for i, a in enumerate(ActionsUI(SimpleNamespace(app=app)).items())
                     if a.title == 'Resume manuscript drafts')
        with tempfile.TemporaryDirectory() as directory:
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher, project_id=app.view['project_id'],
                                                recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(app))
            self.launch(navigation='graph', series=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.send(';', 'ACTIONS')
            self.send('j' * index + '\n', 'MANUSCRIPT DRAFTS')
            self.send('\ne', 'YOUR WORDING')
            self.send('\x1b[200~ / 미완성 문구\x1b[201~\x0f', 'SCIENTIFIC BASIS')
            self.resize(80, 24); self.send('\x0c', 'SCIENTIFIC BASIS')
            self.send('\x03'); self.assert_restored(130)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=app.view['project_id']) as store:
                    saved = store.load()
            reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
            again = reopened.manuscript.sessions[item['id']]
            self.assertEqual('이전 문구 / 미완성 문구', reopened.manuscript.buffers[item['id'], 'wording'][0])
            self.assertEqual(SOURCE, again._source)
            self.assertEqual(session.state()['work'], again.state()['work'])
            self.assertIsNone(again.get_preview()); self.assertIsNone(again.get_review())
            self.assertEqual(app.paper.history.manifest(), reopened.paper.history.manifest())

    def encrypted_review_writing_roundtrip(self, *, answer):
        from types import SimpleNamespace
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui import Terminal
        from claimbranch.application.tui_review_ui import review_ui
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.fixtures import replay_example
        app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        app.select('obs-1')
        t = Terminal.__new__(Terminal)
        t.app, t.modal, t.buffers, t.field = app, None, [], 0
        t.screen = SimpleNamespace(getmaxyx=lambda: (42, 144))
        t.key('w')
        if answer:
            app.keep_draft('A bounded judgment.', 'The unrun mask remains uncertain.')
            app.review.stage('claim-pruning-detail', {'statement': 'A limited claim.', 'scope': 'This split.'})
            app.review.prepare_changes(); t.key('w'); t.key('enter'); t.key('1')
        else:
            t.key('c'); review_ui(t).open_fields('claim-pruning-detail')
        t.key(('paste', ' 이전 작성')); t.key('escape')
        if not answer: t.key('escape')
        key = next(iter(app.review.unfinished)); prior = app.review.unfinished[key][0]
        original_basis = app.review.unfinished_basis[key]['basis']
        with tempfile.TemporaryDirectory() as directory:
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher, project_id=app.view['project_id'],
                                                recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(app))
            self.launch(navigation='graph', series=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.send('U', 'encrypted recovery')
            self.send('\n', 'YOUR EXPLANATION' if answer else 'EDIT CHANGE')
            self.send('\x1b[200~ / 새 미완성 글\x1b[201~\x0f', 'WRITING CONTEXT')
            self.resize(80, 24); self.send('\x0c', 'read only')
            self.send('\x03'); self.assert_restored(130)
            self.assertNotIn(b'unfinished research editor text', self.output)
            self.assertNotIn(b'unfinished review writing', self.output)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=app.view['project_id']) as store:
                    saved = store.load()
            reopened = TerminalWorkspace(saved.history, ai_off=True); restore(reopened, saved)
            self.assertEqual(prior + ' / 새 미완성 글', reopened.review.unfinished[key][0])
            self.assertEqual(original_basis, reopened.review.unfinished_basis[key]['basis'])
            for session in reopened.review.sessions.values():
                self.assertIsNone(session.get_changes_preview())
                self.assertIsNone(session.get_changes_review())
            self.assertEqual(app.paper.history.manifest(), reopened.paper.history.manifest())

    def encrypted_judgment_roundtrip(self, *, interrupt_during_result=False, interrupt_during_claim=False):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot
        from claimbranch.fixtures import replay_merge_example
        app = TerminalWorkspace(replay_merge_example('recorded'), ai_off=True)
        app.select('obs-1')
        app.keep_draft('다시 열어볼 판단', 'The original reason')
        with tempfile.TemporaryDirectory() as directory:
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher,
                        project_id=app.view['project_id'], recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(app, ('edit', ['미완성 판단', ''])))
            self.launch(navigation='graph', merge_example=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.send('E\x0c', '미완성 판단')
            self.resize(80, 24)
            self.send('\x0c', 'judgment + AI origin recovery')
            self.send('\x13', 'Draft kept')
            if interrupt_during_claim:
                self.send(';' + '\x1b[B' * 2 + '\n', 'WRITE A CLAIM')
                self.send('\x1b[B' * 2 + '\n', 'CLAIM STATEMENT')
                self.send('\x1b[200~미완성 주장 입력\x1b[201~\x03')
                self.assert_restored(130)
                self.assertNotIn(b'unfinished research editor text', self.output)
            elif interrupt_during_result:
                self.send(';' + '\x1b[B' * 5 + '\n', 'DRAFT A RESULT')
                self.send('\n', 'OBSERVED CONTENT')
                self.send('\x1b[200~미완성 결과 입력\x1b[201~\x03')
                self.assert_restored(130)
                self.assertNotIn(b'unfinished research editor text', self.output)
            else:
                self.send('q')
                self.assert_restored(0)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=app.view['project_id']) as store:
                    value = store.load()
                    from claimbranch.application.tui_work_recovery import restore
                    reopened = TerminalWorkspace(value.history, ai_off=True)
                    restore(reopened, value)
                    self.assertEqual('미완성 판단', reopened.draft()['text'])
                    self.assertEqual('', reopened.draft()['rationale'])
                    if interrupt_during_claim:
                        records = reopened.review.candidate_inputs[reopened.work_key()]
                        self.assertEqual('미완성 주장 입력', next(iter(records.values()))['body']['statement'])
                        self.assertFalse(reopened.review.candidates().records)
                    if interrupt_during_result:
                        result = reopened.intake.items()[0]
                        self.assertEqual('', result['kept']['observation'])
                        self.assertEqual('미완성 결과 입력', result['unfinished']['observation'])

    def test_named_manual_actions_from_ai_off_cli_survive_resize_and_exit(self):
        self.launch(navigation='graph', ai_off=True)
        self.expect('AI OFF')
        self.send(';', 'ACTIONS /')
        self.expect('Write a judgment')
        self.send('\x1b[F', 'OPTIONAL AI')
        self.send('\n\x0c', 'No request will be prepared.')
        self.resize(80, 24)
        self.send('\x0c', 'AI OFF')
        self.send('\x1b[H\n', 'YOUR JUDGMENT')
        self.send('\x1b[200~직접 기록한 판단\x1b[201~\t측정한 조건만 해석한다.\x13', 'Draft kept')
        self.send('wA', 'AI OFF. Manual writing remains available')
        self.send('e\x0c', '직접 기록한 판단')
        self.send('\x1b')
        self.send('q', 'LEAVE SESSION?')
        self.send('y')
        self.assert_restored(0)

    def test_manual_claim_creation_and_draft_graph_in_real_terminal(self):
        self.launch(navigation='graph', ai_off=True)
        self.expect('AI OFF')
        self.send(';\x1b[B\x1b[B\n', 'WRITE A CLAIM')
        self.send('\n\n', 'Main claim')
        self.send('\x1b[B\n\n', 'Parent in the argument')
        self.send('\x1b[B\n', 'CLAIM STATEMENT')
        self.send('\x1b[200~다른 mask는 아직 측정하지 않았다.\x1b[201~')
        self.send('\x1b')
        self.send('\x1b[B\n', 'SCOPE / CONDITIONS')
        self.send('\x1b[200~Only the measured mask.\x1b[201~')
        self.send('\x1b')
        self.send('\x13', 'YOUR ARGUMENT DRAFTS')
        self.send('g', 'DRAFT GRAPH')
        self.expect('D1 DRAFT MAIN')
        self.resize(80, 24)
        self.send('\x0c', 'DRAFT GRAPH')
        self.send('\x1b')
        self.send('\x1b')
        self.send('q', 'LEAVE SESSION?')
        self.send('y')
        self.assert_restored(0)

    def test_unconfirmed_result_capture_and_resume_in_real_terminal(self):
        self.launch(navigation='graph', ai_off=True)
        self.expect('AI OFF')
        self.send(';' + '\x1b[B' * 5 + '\n', 'DRAFT A RESULT')
        self.send('\n', 'OBSERVED CONTENT')
        self.send('\x1b[200~새 조건에서 관찰한 미확정 결과\x1b[201~\x13', 'Kept in this session')
        self.send('\x1b[B' * 3 + '\n', 'EXPERIMENTAL CONDITIONS')
        self.send('\x1b[200~Different split; source not yet checked.\x1b[201~\x13', 'Kept in this session')
        self.send('\x1b[B' * 7 + '\n', 'TENTATIVE JUDGMENT')
        self.send('\x1b[200~해석은 아직 진행 중이다.\x1b[201~')
        self.send('\x0f', 'Read only')
        self.send('\t\x0c', 'ORIGINAL SUBJECT')
        self.resize(80, 24)
        self.send('\x0c', 'UNCONFIRMED')
        self.send('\x1b')
        self.send('\x0c', '해석은 아직 진행 중이다.')
        self.send('\x1b', 'UNFINISHED')
        self.send('\x1b', 'RESULT DRAFTS')
        self.send('\x1b')
        self.send(';' + '\x1b[B' * 6 + '\n', 'RESULT DRAFTS')
        self.send('\n', 'DRAFT A RESULT')
        self.send('\x1b[F\x1b[A\n\x0c', '해석은 아직 진행 중이다.')
        self.send('\x13', 'Kept in this session')
        self.send('r', 'READ RESULT DRAFT')
        self.send('\x1b')
        self.send('\x1b')
        self.send('\x1b')
        self.send('q', 'LEAVE SESSION?')
        self.expect('result drafts')
        self.send('y')
        self.assert_restored(0)

    def resize(self, width, height):
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        if self.process is not None and self.process.poll() is None:
            os.kill(self.process.pid, signal.SIGWINCH)

    def test_manual_follow_up_plan_measurement_in_real_terminal(self):
        self.launch(navigation='graph', ai_off=True)
        self.expect('AI OFF')
        self.send(';' + '\x1b[B' * 4 + '\n', 'PLAN A FOLLOW-UP / UNRUN')
        self.send('\n\n', 'Claim to test')
        for title, text in (
            ('EXPERIMENT QUESTION / OBJECTIVE', '새 mask에서도 결과가 유지되는가?'),
            ('EXPERIMENTAL CONDITIONS', 'Model A, mask seed 100, same split.'),
            ('METRIC NAME', 'Accuracy loss'),
            ('MEASUREMENT DEFINITION', '100 times correct-count difference divided by 2000.'),
            ('MEASUREMENT UNIT', 'percentage points'),
            ('COMPARISON / BASELINE', 'Unchanged Model A on the same split.')):
            self.send('\x1b[B\n', title)
            self.send('\x1b[200~' + text + '\x1b[201~')
            self.send('\x1b')
        self.resize(80, 24)
        self.send('\x0c', 'UNRUN PLAN')
        self.send('\x13', 'YOUR ARGUMENT DRAFTS')
        self.send('g', 'DRAFT GRAPH')
        self.resize(144, 42)
        self.send('\x0c', 'DRAFT GRAPH')
        self.send('\x1b')
        self.send('\x1b')
        self.send('q', 'LEAVE SESSION?')
        self.send('y')
        self.assert_restored(0)

    def test_manual_interpretation_and_judgment_reuse_in_real_terminal(self):
        self.launch(navigation='graph', merge_example=True, ai_off=True)
        self.expect('AI OFF')
        self.send(';' + '\x1b[B' * 7 + '\n', 'WRITE AN INTERPRETATION')
        self.send('\n', 'INTERPRETATION STATEMENT')
        self.send('\x1b[200~측정한 조건 안에서 해석한다.\x1b[201~')
        self.send('\x1b')
        self.send('\x1b[B\n', 'OBSERVATIONS INTERPRETED')
        self.send(' \x1b[B \n', 'WRITE AN INTERPRETATION')
        self.resize(80, 24)
        self.send('\x0c', 'Observations interpreted')
        self.send('\x13', 'YOUR ARGUMENT DRAFTS')
        self.send('J', 'USE INTERPRETATION AS JUDGMENT?')
        self.send('\n', 'Interpretation reused')
        self.send('g', 'DRAFT GRAPH')
        self.resize(144, 42)
        self.send('\x0c', 'D1 DRAFT READING')
        self.send('\x1b')
        self.send('b', 'JUDGMENT')
        self.send('e\x0c', '측정한 조건 안에서 해석한다.')
        self.send('\t\x1b[200~측정 범위를 넘어서는 결론은 보류한다.\x1b[201~\x13', 'Draft kept')
        self.send('wR', 'SCIENTIFIC CHANGE REVIEW')
        self.send('q', 'LEAVE SESSION?')
        self.send('y')
        self.assert_restored(0)

    def test_linked_judgment_reuse_and_notes_in_real_terminal(self):
        self.launch(navigation='graph', ai_off=True)
        self.expect('AI OFF')
        self.send('/obs-1\n', 'obs-1')
        self.send('\x1b')
        self.send('e', 'YOUR JUDGMENT')
        self.send('\x1b[200~직접 작성한 공유 판단\x1b[201~\tOne measured mask only.\x13', 'Draft kept')
        self.send(';' + '\x1b[B' * 13 + '\n', 'LINK THIS JUDGMENT TO NODES')
        self.send('\x1b[B \x1b[B \n', 'REVIEW JUDGMENT LINKS')
        self.send('\n', 'LINKED JUDGMENT / E1')
        self.resize(80, 24)
        self.send('\x0c', 'LINKED JUDGMENT')
        self.send('/claim-pruning\n', 'claim-pruning')
        self.send('\x1b')
        self.send('e\x0c', 'JUDGMENT / E1')
        self.expect('직접 작성한 공유 판단')
        self.expect('Linked:')
        self.send('\x1b')
        self.send('n', 'MY NOTE')
        self.send('\x1b[200~이 주장만의 노트\x1b[201~\x13', 'Note kept')
        self.send('q', 'LEAVE SESSION?')
        self.expect('judgment links')
        self.send('y')
        self.assert_restored(0)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS device work key required')
    def test_encrypted_explanation_interrupt_and_reopen_in_actual_terminal(self):
        from claimbranch.application.device_work_store import DevicePaperWorkStore
        from claimbranch.application.work_cipher import MacWorkCipher
        from claimbranch.application.tui_model import TerminalWorkspace
        from claimbranch.application.tui_work_recovery import snapshot, restore
        from claimbranch.fixtures import replay_example
        app = TerminalWorkspace(replay_example('recorded', series=True), ai_off=True)
        item = next(item for item in app.service.pending_work()['items'] if item['kind'] == 'understanding')
        session = app.understanding.open(item['id'])
        topic = session.state()['topics'][0]['id']
        session.edit(topic, '이전 설명', reuse_rationale=True)
        with tempfile.TemporaryDirectory() as directory:
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore.create(directory, cipher=cipher,
                        project_id=app.view['project_id'], recovery_key=os.urandom(32)) as store:
                    store.save(snapshot(app))
            self.launch(navigation='graph', series=True, ai_off=True, work_dir=directory)
            self.expect('writing recovery', timeout=30)
            self.send('W', 'PENDING WORK')
            self.send('\x1b[B\ne\ne\x0c', '이전 설명')
            self.send('\x1b[200~ / 추가 작성 중\x1b[201~\x0f', 'CURRENT')
            self.resize(80, 24)
            self.send('\x0c', 'encrypted recovery')
            self.send('\x03')
            self.assert_restored(130)
            self.assertNotIn(b'unfinished research editor text', self.output)
            with MacWorkCipher() as cipher:
                with DevicePaperWorkStore(directory, cipher=cipher, project_id=app.view['project_id']) as store:
                    saved = store.load()
                    again = TerminalWorkspace(saved.history, ai_off=True)
                    restore(again, saved)
                    restored = again.understanding.open(item['id']).state()
                    self.assertEqual('이전 설명', restored['draft']['entries'][0]['text'])
                    self.assertTrue(restored['draft']['entries'][0]['reuse_rationale'])
                    self.assertEqual('이전 설명 / 추가 작성 중', again.understanding.buffers[(item['id'], topic)])
                    self.assertFalse(restored['closure_available'])

    def test_conditional_explanation_return_in_real_terminal(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'manual.json'
        self.launch(navigation='graph', series=True, ai_off=True, draft_file=path)
        self.expect('AI OFF')
        self.send('W', 'PENDING WORK')
        self.send('\x1b[B\n', 'PENDING WORK / READ')
        self.send('e', 'EXPLANATION / episode')
        self.send('\n', 'YOUR PARTIAL EXPLANATION')
        self.send('r', 'linked without copying')
        self.send('e', 'Ctrl+S keep')
        self.send('\x1b[200~아직 확인할 조건을 남긴다.\x1b[201~')
        self.send('\x0f', 'CURRENT')
        self.resize(80, 24)
        self.send('\x0c', 'EXPLANATION')
        self.send('\x1b', 'Ctrl+S keep')
        self.send('\x13', 'Explanation kept for this session')
        for _ in range(4):
            self.send('\x1b')
        self.send('q', 'LEAVE SESSION?')
        self.expect('explanation drafts')
        self.send('n')
        self.send('W\n', 'PENDING WORK / READ')
        self.send('e\ne\x0c', '아직 확인할 조건을 남긴다.')
        for _ in range(5):
            self.send('\x1b')
        self.send('qy')
        self.assert_restored(0)
        self.assertNotIn('아직 확인할 조건을 남긴다.', path.read_text())

    def launch_job_shell(self):
        # A real interactive shell owns this private controlling PTY. Keep a
        # waiting wrapper in the job so stopping only Python cannot pass.
        env = {**os.environ, 'TERM': 'xterm-256color', 'PS1': 'CB_TEST_SHELL> ', 'PYTHONUTF8': '1'}
        env.pop('ENV', None)
        bootstrap = 'import fcntl,termios,os; fcntl.ioctl(0,termios.TIOCSCTTY,0); os.execv("/bin/sh",["/bin/sh","-i"])'
        self.process = subprocess.Popen([sys.executable, '-c', bootstrap], start_new_session=True,
                                        cwd=ROOT, env=env, stdin=self.slave, stdout=self.slave, stderr=self.slave)
        self.expect('CB_TEST_SHELL> ')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        marker = Path(temporary.name) / 'job-group'
        code = ('import os; from pathlib import Path; Path(' + repr(str(marker)) + ').write_text(str(os.getpgrp())); '
                'from claimbranch.application.cli import main; raise SystemExit(main(["demo","tui"]))')
        command = shlex.quote(sys.executable) + ' -c ' + shlex.quote(code) + '; exit $?'
        self.send('/bin/sh -c ' + shlex.quote(command) + '\n', 'ARGUMENT GRAPH')
        self.job_group = int(marker.read_text())

    def expect(self, text, *, after=0, timeout=6):
        expected = text.encode("utf-8")
        deadline = time.monotonic() + timeout
        while expected not in self.output[after:] and time.monotonic() < deadline:
            ready, _, _ = select.select([self.master], [], [], 0.05)
            if ready:
                self.output += os.read(self.master, 65536)
            elif self.process.poll() is not None:
                break
        self.assertIn(expected, self.output[after:], self.output[-4000:].decode("utf-8", errors="replace"))
        self.assertNotIn(b"Traceback", self.output)

    def send(self, text, expect=None):
        position = len(self.output)
        os.write(self.master, text.encode("utf-8"))
        if expect:
            self.expect(expect, after=position)
        elif text == '\x1b':
            # A standalone Escape must be distinguishable from an intentional
            # Alt+key. Drain repaint output too: a child blocked on a full PTY
            # cannot start its Escape timer while the fake terminal sleeps.
            deadline = time.monotonic() + .2
            while time.monotonic() < deadline:
                if select.select([self.master], [], [], .02)[0]:
                    self.output += os.read(self.master, 65536)

    def assert_restored(self, code):
        self.expect("ClaimBranch closed")
        # Keep behaving like a terminal while a wrapping shell emits its last
        # prompt/exit text. Waiting without reading can fill a Darwin PTY.
        deadline = time.monotonic() + 5
        while self.process.poll() is None and time.monotonic() < deadline:
            if select.select([self.master], [], [], .01)[0]:
                self.output += os.read(self.master, 65536)
        self.assertEqual(code, self.process.wait(timeout=5))
        self.assertIn(b"\x1b[?2004l", self.output)
        if self.job_group is not None:
            # The real shell already executed a command after suspend. Its
            # exit hangs up its controlling PTY, so another read is invalid.
            return
        # Darwin sets PENDIN when canonical mode returns, even for a minimal
        # tty.setraw/tcsetattr round trip. A shell's next read clears that kernel
        # state. Exercise actual canonical line editing before comparing every
        # mode, instead of mistaking PENDIN for a changed user setting.
        os.write(self.master, b"shell-inputX\x7f\n")
        self.assertTrue(select.select([self.slave], [], [], 1)[0])
        self.assertEqual(b"shell-input\n", os.read(self.slave, 1024))
        self.assertEqual(self.original, termios.tcgetattr(self.slave))

    def test_offline_proposal_workflow_uses_real_terminal_keys_without_leaking_input(self):
        self.launch(navigation='graph')
        self.expect('ARGUMENT GRAPH')
        self.send('w', 'WORK / REVIEW')
        self.send('A', 'CHOOSE CONTEXT')
        self.send('\r', 'REVIEW EXACT OFFLINE REQUEST')
        self.send('\r', 'Offline example pending')
        self.expect('ready: w to inspect')
        self.send('y', 'COMPARE AI PROPOSAL')
        self.resize(48, 18)
        self.send('\x0c', 'YOUR JUDGMENT')
        self.send('\x1b[F', 'AI ORIGIN')
        self.send('\x1b', 'WORK / REVIEW')
        self.resize(132, 38)
        self.send('y', 'COMPARE AI PROPOSAL')
        self.send('\r', 'Adopted for this session')
        self.send('e', 'AI-influenced')
        self.send('\t\x1b[200~측정한 조건만 판단합니다.\x1b[201~\x13', 'draft kept for this session')
        self.send('w', 'WORK / REVIEW')
        self.resize(80, 24)
        self.send('\x0c', 'WORK / REVIEW')
        self.send('B', 'COMPARE EARLIER TEXT')
        self.expect('측정한 조건만 판단합니다.')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('x', 'Not now.')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_source_peek_preserves_judgment_during_resize_and_returns_to_shell(self):
        self.resize(144, 42)
        self.launch(navigation='graph')
        self.expect('ARGUMENT GRAPH')
        self.send('/obs-1\r', 'E1')
        self.send('w', 'RECORDED OBSERVATION')
        self.send('e', 'Ctrl+O')
        self.send('\x1b[200~측정 범위를 확인합니다.\x1b[201~', '측정 범위를 확인합니다.')
        # Source and editor keep a common header suffix. Force a full repaint
        # before matching the complete phrase in the incremental PTY stream.
        self.send('\x0f\x0c', 'SOURCE / E1')
        self.send('\x1b[6~')
        self.resize(80, 24)
        self.send('\x0c', 'Read only; your draft is retained.')
        self.send('q\x13\x1b[200~DO_NOT_INSERT\x1b[201~')
        self.send('\x1b')
        self.send('\x0c', 'YOUR JUDGMENT / E1')
        self.expect('측정 범위를 확인합니다.')
        self.send('\t\x1b[200~이 조건에서만 관찰했습니다.\x1b[201~\x13', 'Draft kept.')
        self.send('e', '이 조건에서만 관찰했습니다.')
        self.send('\x0f\x0c', 'SOURCE / E1')
        self.send('\x0f\x0c', 'YOUR JUDGMENT / E1')
        self.send('\x1b')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_episode_and_pending_work_journey_in_a_colored_terminal(self):
        self.launch(navigation='graph', series=True)
        self.expect('ARGUMENT GRAPH')
        self.assertIn(b'38;5;', self.output)
        self.send('t', 'EPISODES')
        self.send('k\t', 'alternative')
        self.send('\r', 'Context changed')
        self.send('n', 'MY NOTE')
        self.send('\x1b[200~첫 단계의 노트\x1b[201~\x13', 'Note kept')
        self.send('W', 'PENDING WORK')
        self.send('\r', 'PENDING IF ACCEPTED')
        self.resize(80, 24)
        self.send('\x0c', 'PENDING WORK / READ')
        self.send('g', 'RELATED ARGUMENT')
        self.send('\r', 'nothing resolved')
        self.send('t', 'EPISODES')
        self.send('j\r', 'Context changed')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_view_settings_keep_cancel_and_resize_in_a_real_terminal(self):
        self.launch(navigation='graph', series=True)
        self.expect('ARGUMENT GRAPH')
        self.send('/obs-1\r', 'challenged by E1')
        self.send(',', 'VIEW SETTINGS')
        self.send(' ', 'Spacious')
        self.resize(80, 24)
        self.send('\x0c', 'VIEW SETTINGS')
        self.resize(44, 16)
        self.send('\x0c', 'controls paused')
        self.send(' r\r\x0c', 'controls paused')
        # SIGWINCH and Ctrl+L can queue identical frames. Drain while still
        # small so input is consumed before the fake terminal changes size.
        deadline = time.monotonic() + .25
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], .02)[0]:
                self.output += os.read(self.master, 65536)
        self.resize(80, 24)
        self.send('\x0c', 'Spacious')
        self.send('\x1b', 'previous view restored')
        self.send(',', 'Balanced')
        self.send(' ', 'Spacious')
        self.send('\r', 'View settings kept')
        self.send(',', 'Spacious')
        self.send('r', 'Balanced')
        self.send('\r', 'View settings kept')
        self.send('q')
        self.assert_restored(0)

    def test_manuscript_diff_explanation_resize_and_return_in_a_real_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'paper.tex'
            original = b'% claimbranch:start id=anchor\nOld wording.\n% claimbranch:end id=anchor\n'
            source.write_bytes(original)
            self.launch(navigation='graph', series=True)
            self.expect('ARGUMENT GRAPH')
            self.send('W', 'PENDING WORK')
            self.send('\r', 'PENDING WORK / READ')
            self.send('m', 'MANUSCRIPT / REVIEW')
            self.send('s', 'SOURCE FILE')
            self.send(str(source) + '\x13', 'SOURCE / paper.tex')
            self.send('e', 'YOUR WORDING')
            self.send('\x1b[200~한글: pruning exceeds the measured budget.\x1b[201~')
            self.send('\tThe corrected count covers only this split.\x13', 'MANUSCRIPT / REVIEW')
            self.send('R', '-Old wording.')
            self.resize(80, 24)
            self.send('\x0c', 'DIFF / BEFORE')
            self.send('\r', 'AI ORIGIN')
            self.send('1', 'YOUR EXPLANATION')
            self.send('\x13', 'REVIEW COMPLETE')
            self.send('\x1b', 'PENDING WORK / READ')
            self.send('\x1b', 'PENDING WORK')
            self.send('\x1b', 'ARGUMENT GRAPH')
            self.send('q', 'UNSAVED DRAFTS')
            self.send('y')
            self.assert_restored(0)
            self.assertEqual(original, source.read_bytes())

    def test_selected_merge_graphs_completion_resize_and_return_in_a_real_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'paper.tex'
            original = b'Synthetic source snapshot.\r\n'
            source.write_bytes(original)
            self.launch(navigation='graph', merge_example=True)
            self.expect('ARGUMENT GRAPH')
            self.send('M', 'BRANCH / SELECT')
            self.send('jj ', 'Selection changed')
            self.send('s', 'Read-only manuscript path')
            self.send(str(source) + '\x13', 'SOURCE / paper.tex')
            self.send('R', 'REQUIRED')
            self.send('G', 'UNACCEPTED REVIEW / AFTER')
            self.send('\t', 'BEFORE')
            self.resize(80, 24)
            self.send('\x0c', 'UNACCEPTED REVIEW / BEFORE')
            self.send('\x1b', 'BRANCH / REVIEW')
            self.send('\r', 'BRANCH / COMPLETE')
            self.send('2', 'REVIEW COMPLETE / UNACCEPTED')
            self.send('v', 'CANDIDATE CALCULATED')
            self.send('\x1b', 'BRANCH / SELECT')
            self.send('\x1b', 'ARGUMENT GRAPH')
            self.send('q', 'UNSAVED DRAFTS')
            self.send('y')
            self.assert_restored(0)
            self.assertEqual(original, source.read_bytes())

    def test_selected_science_to_wording_and_reason_reuse_in_real_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'paper.tex'
            source=b'% claimbranch:start id=anchor\nOld wording.\n% claimbranch:end id=anchor\n'
            path.write_bytes(source)
            self.launch(navigation='graph', merge_example=True, ai_off=True)
            self.expect('ARGUMENT GRAPH')
            self.send('Mjj ', 'Selection changed')
            self.send('s', 'Read-only manuscript path')
            self.send(str(path)+'\x13', 'SOURCE / paper.tex')
            self.send('R\n2', 'REVIEW COMPLETE / UNACCEPTED')
            self.send('m', 'FROM SELECTED SCIENCE')
            self.send('\n', 'DETACHED CANDIDATE')
            self.send('e', 'Ctrl+R reuse reason')
            self.send('\x1b[200~한글: the conclusion remains limited.\x1b[201~')
            self.send('\x12', 'Judgment reason reused')
            self.send('\x0f', 'SCIENTIFIC BASIS')
            self.resize(80,24)
            self.send('\x0c', 'SCIENTIFIC JUDGMENT')
            self.send('\x1b', 'YOUR WORDING')
            self.send('\x13', 'Wording kept.')
            self.send('R', '+한글:')
            self.send('\n1\x13', 'REVIEW COMPLETE / UNACCEPTED')
            self.send('\x1b', 'BRANCH / REVIEW')
            self.send('\x1b', 'BRANCH / SELECT')
            self.send('\x1b', 'ARGUMENT GRAPH')
            self.send('qy')
            self.assert_restored(0)
            self.assertEqual(source,path.read_bytes())

    def check_full_relationships(self, monochrome):
        self.launch(navigation='graph', series=True, monochrome=monochrome)
        self.expect('ARGUMENT GRAPH')
        self.send('/obs-1\r', 'challenged by E1')
        self.assertNotIn('╳'.encode(), self.output)
        if monochrome:
            self.assertNotIn(b'38;5;', self.output)
        else:
            self.assertIn(b'38;5;', self.output)
        self.send('r', 'RELATIONS')
        self.send('\t', 'FROM')
        self.resize(80, 24)
        self.send('\x0c', 'CONNECTION')
        self.send('q')
        self.assert_restored(0)

    def test_full_relationships_and_exact_reader_in_color(self):
        self.check_full_relationships(False)

    def test_full_relationships_and_exact_reader_without_color(self):
        self.check_full_relationships(True)

    def test_manual_scientific_change_can_be_edited_and_reviewed_in_a_real_terminal(self):
        self.launch(navigation='graph')
        self.expect('ARGUMENT GRAPH')
        self.send('e', 'YOUR JUDGMENT')
        self.send('\x1b[200~Limit this claim to measured conditions.\x1b[201~\tOnly one mask was measured.\x13', 'Draft kept')
        self.send('w', 'WORK / REVIEW')
        self.send('c', 'YOUR SCIENTIFIC CHANGES')
        self.send('\r', 'EDIT CHANGE')
        self.send('\x1b[200~ Restricted to the measured split.\x1b[201~\x13', 'YOUR SCIENTIFIC CHANGES')
        self.send('R', 'SCIENTIFIC CHANGE REVIEW')
        self.send('G', 'UNACCEPTED COMPARISON')
        self.send('\t', 'BEFORE')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('\r', 'REVIEW COMPLETE')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_unfinished_review_resumes_after_context_change_and_resize(self):
        self.launch(navigation='graph', series=True)
        self.expect('ARGUMENT GRAPH')
        self.send('/obs-1\r', 'challenged by E1')
        self.send('e', 'YOUR JUDGMENT')
        self.send('Limit to measured conditions.\tOnly one split.\x13', 'Draft kept')
        self.send('w', 'WORK / REVIEW')
        self.send('c', 'YOUR SCIENTIFIC CHANGES')
        self.send('\r', 'EDIT CHANGE')
        self.send('\x1b[200~ 한글 변경 초안\x1b[201~', '한글 변경 초안')
        self.send('\x1b', 'unfinished')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('t', 'EPISODES')
        self.send('k\t\r', 'Context changed')
        self.send('U', 'Scientific change')
        self.resize(80, 24)
        self.send('\x0c', 'Session only')
        self.send('\r', '한글 변경 초안')
        self.send('\x13', 'YOUR SCIENTIFIC CHANGES')
        self.send('R', 'SCIENTIFIC CHANGE REVIEW')
        self.send('\r', 'COMPLETE REVIEW')
        self.send('1', 'YOUR EXPLANATION')
        self.send('\x1b[200~ 설명을 이어 씁니다\x1b[201~', '설명을 이어 씁니다')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('U', 'Review explanation')
        self.send('\r', '설명을 이어 씁니다')
        self.send('\x13', 'REVIEW COMPLETE')
        self.send('c', 'YOUR SCIENTIFIC CHANGES')
        self.send('\r', 'EDIT CHANGE')
        self.send(' Discard this unfinished revision.\x0c', 'Discard this')
        self.send('\x1b', 'unfinished')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('U', 'Scientific change')
        self.send('x', 'x again')
        self.send('\x1b', 'x discard')
        self.send('x', 'x again')
        self.send('x', 'No unfinished writing')
        self.send('\x1b', 'WORK / REVIEW')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_resize_bracketed_unicode_draft_and_return_to_shell(self):
        self.launch()
        self.expect("RELATIONS")
        self.send("e", "YOUR JUDGMENT")
        self.send("\x1b[200~한글 근거\nq s b are pasted text\x1b[201~", "한글 근거")
        self.send("\t두 주장에 연결됩니다.\x13", "Draft kept")
        self.resize(62, 24)
        self.expect("YOUR SESSION DRAFT")
        self.send("e", "WHY / EVIDENCE")
        self.send("\x1b")
        self.send("q", "UNSAVED DRAFTS")
        self.send("n")
        self.send("s", "HYPOTHETICAL")
        self.send("2", "HYPOTHETICAL / CHALLENGES")
        self.send("\x1b[6~", "POSSIBLE REVIEW PATH")
        self.resize(132, 38)
        self.send("q", "UNSAVED DRAFTS")
        self.send("y")
        self.assert_restored(0)

    def test_paste_outside_input_cannot_trigger_actions_and_interrupt_restores(self):
        self.launch(monochrome=True)
        self.expect("ARGUMENT")
        self.send("\x1b[200~q s2 e\x1b[201~", "Pasted text does not run shortcuts")
        self.assertIsNone(self.process.poll())
        self.send("\x03")
        self.assert_restored(130)

    def test_color_density_and_relationship_reader_on_eight_and_256_color_terminals(self):
        for term in ("xterm", "xterm-256color"):
            with self.subTest(term=term):
                self.output = b""
                self.launch(term=term)
                self.expect("RELATIONS")
                if term == "xterm-256color":
                    self.assertIn(b"38;5;", self.output)
                else:
                    self.assertRegex(self.output, rb"\x1b\[3[1-6]m")
                self.send("z", "compact")
                self.send("r", "CONNECTION")
                self.expect("FROM")
                self.expect("TO")
                self.send("\t\x1b[6~")
                self.expect("RATIONALE")
                self.send("d", "typed connections")
                self.send("q")
                self.assert_restored(0)

    def test_dumb_terminal_fails_without_changing_terminal_modes(self):
        self.launch(term="dumb")
        self.expect("--snapshot")
        self.assertEqual(2, self.process.wait(timeout=5))
        self.assertEqual(self.original, termios.tcgetattr(self.slave))
        self.assertNotIn(b"\x1b[?1049h", self.output)

    def test_outline_edges_folding_search_and_shared_return_in_a_real_terminal(self):
        self.launch()
        self.expect("ARGUMENT")
        self.send("/replication\n", "tests →")
        self.send("\x1b", "THESIS › MAIN › SUBCLAIM › PLAN")
        self.send("\n", "CONNECTION")
        self.expect("TESTS")
        self.expect("FROM")
        self.send("\t")
        self.send("/obs-1\n", "EVIDENCE")
        self.send("\x1b")
        self.send("\x1b[C\x1b[C", "produced")
        self.send("/obs-1\n")
        self.send("jj")
        self.send("g", "primary occurrence. Esc returns")
        self.send("\x1b")
        self.resize(62, 24)
        self.expect("E1 · 2 claims")
        self.send("\n", "CONNECTION")
        self.send("q")
        self.assert_restored(0)

    def test_evidence_views_usage_picker_draft_and_return_in_a_real_terminal(self):
        self.launch()
        self.expect("Argument")
        self.send("/obs-1\n", "2 claims")
        self.send("\x1b")
        self.send("2", "Evidence uses · direct claims first")
        self.send("u", "CONNECTION")
        self.expect("SUPPORTS")
        self.send("\t\n", "Followed the same node")
        self.send("\x1b", "Pruning 20 percent")
        self.send("e", "YOUR JUDGMENT")
        self.send("\x1b[200~같은 근거의 판단\x1b[201~\t두 주장 사용처\x13", "Draft kept")
        self.send("1", "Argument view · same records and drafts")
        self.resize(62, 24)
        self.send("d", "0.4 percentage points")
        self.send("2", "Evidence uses · direct claims first")
        self.send("]", "Quantizing Model A weights")
        self.send("[\x0c", "0.4 percentage points")
        self.send("e", "같은 근거의 판단")
        self.send("\x1b")
        self.resize(144, 46)
        self.send("q", "UNSAVED DRAFTS")
        self.send("y")
        self.assert_restored(0)

    def test_visual_graph_navigation_edge_reading_resize_and_draft(self):
        self.launch(navigation="graph", monochrome=True)
        self.expect("ARGUMENT GRAPH")
        self.expect("10/10 visible · 15 edges")
        self.send("/obs-1\n", "obs-1")
        self.send("\x1b")
        self.send("\n", "CLAIM USES")
        self.send("u", "CLAIM USES")
        self.send("\t", "CONNECTION")
        self.expect("SUPPORTS")
        self.send("\n", "Followed the same node")
        self.send("\x1b")
        self.send("f", "Fit current scope")
        position = len(self.output)
        self.send("2\x0c", "5/5 visible")
        self.expect("8 edges", after=position)
        self.resize(62, 24)
        self.expect("E1 · 2 claims")
        self.send("HJKLf")
        self.send("e", "YOUR JUDGMENT")
        self.send("\x1b[200~그래프에서 검토한 판단\x1b[201~\t공유 근거 하나\x13", "Draft kept")
        self.send("f1o", "Navigation: outline")
        self.send("e", "그래프에서 검토한 판단")
        self.send("\x1b")
        self.resize(144, 46)
        self.send("q", "UNSAVED DRAFTS")
        self.send("y")
        self.assert_restored(0)

    def test_overview_local_scope_pin_fit_and_return_in_real_terminal(self):
        self.launch(navigation='graph')
        self.expect('10/10 visible')
        self.send('/obs-1\n', 'obs-1')
        self.send('\x1b')
        self.send('l\x0c', '5/5 visible')
        self.resize(80, 24)
        self.expect('Local E1')
        self.send('\n', 'READ')
        self.send('P', 'Reader pinned')
        self.send('\x1b')
        self.resize(144, 42)
        self.send('\x0c', 'READ')
        self.send('P\x0c', '1 pane')
        self.send('a\x0c', '10/10 visible')
        self.send('\x1b')
        self.send('\x0c', '5/5 visible')
        self.send('f\x0c', 'Fit current scope')
        self.send('q')
        self.assert_restored(0)

    def test_terminal_uses_actual_size_even_with_stale_size_environment(self):
        with patch.dict(os.environ, {"LINES": "60", "COLUMNS": "200"}):
            self.launch(navigation="graph")
        self.expect("10/10 visible · 15 edges")
        addresses = [(int(y), int(x)) for y, x in re.findall(rb"\x1b\[(\d+);(\d+)H", self.output)]
        self.assertTrue(addresses)
        self.assertTrue(all(y <= 38 and x <= 132 for y, x in addresses), addresses)
        self.send("\r", "READ")
        self.resize(62, 24)
        self.expect("PgUp/PgDn")
        self.send("q")
        self.assert_restored(0)

    def test_unknown_terminal_sequences_do_not_run_shortcuts_and_redraw_recovers(self):
        self.launch(navigation="graph")
        self.expect("10/10 visible · 15 edges")
        self.send("\x1b[" + "9" * 80 + "q")
        self.send("\x1b[999q\x1b[999s\x1b[9992~\r\n\r!@#$%")
        self.expect("READ")
        self.send("\x0c", "ClaimBranch")  # Redraw must repaint unchanged content.
        self.assertIsNone(self.process.poll())
        self.assertNotIn(b"HYPOTHETICAL / nothing runs", self.output)
        self.assertNotIn(b"ClaimBranch closed", self.output)
        self.send("q")
        self.assert_restored(0)

    def test_edit_node_note_enter_stays_in_editor_cancel_and_resize_preserve_it(self):
        self.launch(navigation="graph")
        self.expect("ARGUMENT GRAPH")
        self.send("/obs-1\n", "obs-1")
        self.send("n", "MY NOTE")
        # Ordinary typing is repainted incrementally, so ask for a full frame
        # before asserting the complete phrase on the terminal wire.
        self.send("재현 메모\r다른 시드 확인\x0c", "다른 시드 확인")
        self.resize(62, 24)
        self.expect("재현 메모")
        self.send("\x13", "Note kept")
        self.send("n", "Ctrl+S")
        self.send("추가 입력\x0c", "추가 입력")
        self.send("\x1b", "Editing cancelled")
        self.send("n", "MY NOTE")
        self.send("\x13", "Note kept")
        self.resize(156, 48)
        self.send("f", "Fit current scope")
        self.send("z", "✎ 재현 메모")
        self.send("q", "UNSAVED DRAFTS")
        self.send("n", "ARGUMENT GRAPH")
        self.send("q", "UNSAVED DRAFTS")
        self.send("y")
        self.assert_restored(0)

    def test_bare_escape_is_prompt_and_editing_suspend_resumes_after_resize(self):
        self.launch_job_shell()
        self.send("n", "MY NOTE")
        self.send("shell continuity\x0c", "shell continuity")
        position = len(self.output)
        os.write(self.master, b"\x1a")
        self.expect('CB_TEST_SHELL> ', after=position)
        # Interactive shells may enable their own noncanonical line editor.
        # Execute a real command rather than mistaking readline for TUI modes.
        self.send("printf 'CB_%s\\n' SHELL_OK\n", 'CB_SHELL_OK')
        self.resize(80, 24)
        self.send('fg\n')
        self.expect("shell continuity", after=position)
        start = time.monotonic()
        self.send("\x1b", "Editing cancelled")
        self.assertLess(time.monotonic() - start, .65)
        self.send("N", "shell continuity")
        self.send("\x1f\x0c", "shell continuity")  # recovered text has a fresh undo stack
        position = len(self.output)
        self.send("\x03", 'ClaimBranch closed')
        self.expect('CB_TEST_SHELL> ', after=position)
        self.send('exit 130\n')
        self.assert_restored(130)

    def test_private_draft_survives_abrupt_process_loss_without_becoming_kept_note(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "drafts.json"
            self.launch(navigation="graph", draft_file=checkpoint)
            self.expect("ARGUMENT GRAPH")
            self.send("n", "MY NOTE")
            self.send("\x1b[200~복구할 미완성 메모\x1b[201~", "복구할 미완성 메모")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if checkpoint.exists() and "복구할 미완성 메모" in checkpoint.read_text():
                    break
                time.sleep(.02)
            self.assertIn("복구할 미완성 메모", checkpoint.read_text())
            self.process.kill()
            self.process.wait(timeout=3)
            termios.tcsetattr(self.slave, termios.TCSANOW, self.original)
            self.output = b""
            self.launch(navigation="graph", draft_file=checkpoint)
            self.expect("Private drafts restored")
            self.send("N", "복구할 미완성 메모")
            self.send("\x13", "Note kept")
            self.send("q")
            self.assert_restored(0)

    def test_modified_keys_and_pasted_control_bytes_never_become_commands(self):
        self.launch(navigation='graph')
        self.expect('ARGUMENT GRAPH')
        self.send('n', 'MY NOTE')
        self.send('\x1b[200~literal\x03q\ntext\x1b[201~\x0c', 'literalq')
        self.send('\x1bb\x1bf\x1bq\x1b\x7f\x0c', 'MY NOTE')
        self.assertIsNone(self.process.poll())
        self.send('\x13', 'Note kept')
        self.send('q', 'UNSAVED DRAFTS')
        self.send('y')
        self.assert_restored(0)

    def test_no_job_control_session_refuses_suspend_without_freezing_editor(self):
        self.launch(navigation='graph', no_job_control=True)
        self.expect('ARGUMENT GRAPH')
        self.send('\x1a', 'No job-control shell')
        self.send('n', 'MY NOTE')
        self.send('still editable\x0c', 'still editable')
        self.send('\x03')
        self.assert_restored(130)


if __name__ == "__main__":
    unittest.main()
