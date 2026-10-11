from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from claimbranch.application.cli import main
from claimbranch.application.work_commands import recovery_key
from claimbranch.application.work_archive import WorkArchive
from claimbranch.core.canonical import ContractError


class WorkCommandTests(unittest.TestCase):
    def test_work_help_exposes_lifecycle_without_loading_native_helper(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exit_status:
            main(['demo', 'work', '--help'])
        self.assertEqual(0, exit_status.exception.code)
        for action in ('init', 'status', 'show', 'backup', 'restore'):
            self.assertIn(action, output.getvalue())

    def test_stdin_keys_are_bounded_and_never_interpreted_as_passwords(self):
        for raw in (b'', b'secret', b'f' * 63, b'f' * 65, b'f' * 64 + b'\nextra', b'g' * 64, b'f' * 64 + b'\r\n'):
            stdin = io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8')
            with patch('sys.stdin', stdin), self.assertRaises(ContractError):
                recovery_key(from_stdin=True)
        with patch('sys.stdin', io.TextIOWrapper(io.BytesIO(b'AB' * 32 + b'\n'))):
            self.assertEqual(bytes.fromhex('ab' * 32), recovery_key(from_stdin=True))
        with patch('sys.stdin', None), self.assertRaises(ContractError):
            recovery_key(from_stdin=True)

    def test_interactive_stdin_and_missing_controlling_terminal_refuse_without_echo(self):
        with patch('sys.stdin.isatty', return_value=True), self.assertRaises(ContractError):
            recovery_key(from_stdin=True)
        with patch('builtins.open', side_effect=OSError('private-path')), patch('getpass.getpass') as prompt:
            with self.assertRaises(ContractError):
                recovery_key(from_stdin=False, create=True)
            prompt.assert_not_called()

    def test_completed_save_and_broken_output_are_distinct(self):
        from claimbranch.application import work_commands as commands
        output = MagicMock()
        output.write.side_effect = BrokenPipeError()
        errors = io.StringIO()
        args = SimpleNamespace(work_action='init', directory='not-opened', variant='manual',
                               recovery_key_stdin=True, json=True)
        with patch.object(commands, 'recovery_key', return_value=bytes(32)), \
                patch.object(commands, 'MacWorkCipher'), patch.object(commands.DevicePaperWorkStore, 'create') as create, \
                patch('sys.stdout', output), redirect_stderr(errors):
            self.assertEqual(1, commands.run_work_command(args))
            self.assertTrue(create.return_value.__enter__.return_value.save.called)
        result = json.loads(errors.getvalue())
        self.assertEqual('work-output-failed', result['code'])
        self.assertTrue(result['operation_completed'])

    def test_archive_and_work_must_be_separate_before_key_entry(self):
        from claimbranch.application import work_commands as commands
        with tempfile.TemporaryDirectory() as directory, patch.object(commands, 'recovery_key') as key:
            args = SimpleNamespace(work_action='restore', directory=directory, archive_directory=directory)
            with self.assertRaises(ContractError):
                commands.execute(args)
            key.assert_not_called()

    def test_real_broken_pipe_preserves_completed_result_and_exit_code(self):
        code = '''from claimbranch.application.work_commands import run_work_command
from types import SimpleNamespace
from unittest.mock import patch
with patch('claimbranch.application.work_commands.execute',return_value={'authorization_verified':False}):
    raise SystemExit(run_work_command(SimpleNamespace(work_action='init',json=True)))
'''
        read, write = os.pipe()
        os.close(read)
        try:
            result = subprocess.run([sys.executable, '-B', '-c', code], stdout=write,
                                    stderr=subprocess.PIPE, timeout=10)
        finally:
            os.close(write)
        self.assertEqual(1, result.returncode)
        self.assertTrue(json.loads(result.stderr)['operation_completed'])

    def test_wrong_terminal_confirmation_and_invalid_encoding_fail_before_cipher(self):
        from contextlib import nullcontext
        from claimbranch.application import work_commands as commands
        for entry in ('ff' * 32, 'not hex', UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid')):
            terminal = io.StringIO()
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch('builtins.open', return_value=nullcontext(terminal)), \
                    patch('secrets.token_hex', return_value='ab' * 32), \
                    patch('getpass.getpass', **({'side_effect': entry} if isinstance(entry, Exception) else {'return_value': entry})), \
                    patch.object(commands, 'MacWorkCipher') as cipher, redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(1, main(['demo', 'work', 'init', '--directory', '/unused']))
            cipher.assert_not_called()
            self.assertEqual(1, terminal.getvalue().count('ab' * 32))
            self.assertNotIn('ab' * 32, stdout.getvalue() + stderr.getvalue())

    def test_malformed_secret_and_cancel_never_launch_cipher_or_emit_input(self):
        from claimbranch.application import work_commands
        for error, expected in ((ContractError('sensitive-secret'), 1), (KeyboardInterrupt(), 130)):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(work_commands, 'recovery_key', side_effect=error), \
                    patch.object(work_commands, 'MacWorkCipher') as cipher, \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(['demo', 'work', 'init', '--directory', '/unused-private-path'])
            self.assertEqual(expected, result)
            cipher.assert_not_called()
            self.assertEqual('', stdout.getvalue())
            self.assertNotIn('sensitive-secret', stderr.getvalue())
            self.assertNotIn('/unused-private-path', stderr.getvalue())

    @unittest.skipUnless(sys.platform == 'darwin', 'Mac terminal key entry')
    def test_actual_terminal_generation_requires_hidden_exact_confirmation(self):
        import pty
        import re
        import select
        import time
        pid, master = pty.fork()
        if pid == 0:
            code = ('from claimbranch.application.work_commands import recovery_key; '
                    'key=recovery_key(from_stdin=False,create=True); print("CONFIRMED" if len(key)==32 else "BAD")')
            try:
                os.execv(sys.executable, [sys.executable, '-B', '-c', code])
            finally:
                os._exit(127)
        output, sent = b'', False
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                if not select.select([master], [], [], 0.1)[0]:
                    continue
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                match = re.search(rb'[0-9a-f]{64}', output)
                if match and not sent and '표시되지 않음'.encode() in output:
                    os.write(master, match.group() + b'\n')
                    sent = True
                if b'CONFIRMED' in output:
                    break
            self.assertTrue(sent)
            self.assertIn(b'CONFIRMED', output)
            self.assertEqual(1, len(re.findall(rb'[0-9a-f]{64}', output)))
        finally:
            os.close(master)
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)


@unittest.skipUnless(os.name == 'posix', 'POSIX private directory checks')
class ArchiveFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claimbranch-archive-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        envelope = b'CBKY\x00\x01' + bytes(226) + b'\x00\x01' + bytes(153)
        self.raw = b'CBWD\x00\x01' + len(envelope).to_bytes(4, 'big') + envelope + b'CBWK\x00\x01' + bytes(61)

    def test_copy_is_create_only_private_and_bounded(self):
        with WorkArchive(self.root) as archive:
            archive.write(self.raw)
            self.assertEqual(self.raw, archive.read())
            with self.assertRaises(ContractError):
                archive.write(self.raw)
        self.assertEqual(0o600, (self.root / 'backup.cbw').stat().st_mode & 0o777)
        from claimbranch.application.device_work_store import MAX_DEVICE_BYTES
        (self.root / 'backup.cbw').write_bytes(self.raw + bytes(MAX_DEVICE_BYTES + 1 - len(self.raw)))
        with WorkArchive(self.root) as archive, self.assertRaises(ContractError):
            archive.read()

    def test_link_and_git_paths_never_replace_or_follow_targets(self):
        target = self.root / 'target'
        target.write_bytes(b'keep')
        (self.root / 'backup.cbw').symlink_to(target)
        with WorkArchive(self.root) as archive:
            with self.assertRaises(ContractError):
                archive.write(self.raw)
            with self.assertRaises(ContractError):
                archive.read()
        self.assertEqual(b'keep', target.read_bytes())
        (self.root / '.git').mkdir()
        with self.assertRaises(ContractError):
            with WorkArchive(self.root):
                pass

    def test_sync_failure_has_no_success_and_never_replaces_retry_destination(self):
        with WorkArchive(self.root) as archive:
            with patch.object(archive, '_sync', side_effect=OSError('disk-full')), self.assertRaises(ContractError):
                archive.write(self.raw)
            retained = (self.root / 'backup.cbw').read_bytes()
            with self.assertRaises(ContractError):
                archive.write(self.raw)
            self.assertEqual(retained, (self.root / 'backup.cbw').read_bytes())

    def test_competing_create_partial_and_public_copy_refuse(self):
        with WorkArchive(self.root) as first, WorkArchive(self.root) as second:
            first.write(self.raw)
            with self.assertRaises(ContractError):
                second.write(self.raw)
        target = self.root / 'backup.cbw'
        target.write_bytes(self.raw[:40])
        target.chmod(0o600)
        with WorkArchive(self.root) as archive, self.assertRaises(ContractError):
            archive.read()
        target.write_bytes(self.raw)
        target.chmod(0o644)
        with WorkArchive(self.root) as archive, self.assertRaises(ContractError):
            archive.read()

    def test_read_does_not_write_lock_or_remove_staging_even_when_writes_are_denied(self):
        backup = self.root / 'backup.cbw'
        backup.write_bytes(self.raw)
        backup.chmod(0o600)
        staging = self.root / ('.work-' + 'a' * 32)
        staging.write_bytes(b'preserve unrelated source file')
        staging.chmod(0o600)
        original = {p.name: p.read_bytes() for p in self.root.iterdir()}
        native_open = os.open

        def read_only(path, flags, *args, **kwargs):
            if flags & (os.O_CREAT | os.O_WRONLY | os.O_RDWR):
                raise OSError('read-only volume')
            return native_open(path, flags, *args, **kwargs)

        with patch('os.open', side_effect=read_only), WorkArchive(self.root) as archive:
            self.assertEqual(self.raw, archive.read())
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.root.iterdir()})


@unittest.skipUnless(sys.platform == 'darwin', 'macOS Secure Enclave required')
class NativeWorkCommandTests(unittest.TestCase):
    def test_separate_process_save_read_backup_restore_keeps_provenance(self):
        with tempfile.TemporaryDirectory(prefix='claimbranch-work-cli-') as temporary:
            root = Path(temporary).resolve()
            from scripts.build_source import build_source
            artifact = root / 'source.zip'
            build_source(artifact)
            runtime = root / 'runtime'
            with zipfile.ZipFile(artifact) as source:
                source.extractall(runtime)
            work, archive, restored = (root / name for name in ('원래 작업', 'backup', 'restored'))
            for directory in (work, archive, restored):
                directory.mkdir(mode=0o700)
            key = os.urandom(32).hex().encode()

            def run(action, directory, *options, secret=b'', expected=0):
                result = subprocess.run([sys.executable, '-B', '-m', 'claimbranch', 'demo', 'work',
                    action, '--directory', str(directory), '--json', *options],
                    input=secret, capture_output=True, timeout=90, cwd=runtime)
                self.assertNotIn(key, result.stdout + result.stderr)
                self.assertEqual(expected, result.returncode, result.stderr)
                return json.loads(result.stdout if expected == 0 else result.stderr)

            created = run('init', work, '--variant', 'recorded', '--recovery-key-stdin', secret=key)
            self.assertFalse(created['authorization_verified'])
            before = (work / 'work.cbw').read_bytes()
            run('init', work, '--recovery-key-stdin', secret=key, expected=1)
            self.assertEqual(before, (work / 'work.cbw').read_bytes())
            status = run('status', work)
            self.assertEqual(created['work_digest'], status['work_digest'])
            view = run('show', work)
            self.assertTrue(view['pending_work']['items'])
            self.assertFalse(view['authorization_verified'])
            wrong_key = os.urandom(32).hex().encode()
            run('backup', work, '--archive-directory', str(archive), '--recovery-key-stdin', secret=wrong_key, expected=1)
            self.assertEqual([], list(archive.iterdir()))
            run('backup', work, '--archive-directory', str(archive), '--recovery-key-stdin', secret=key)
            self.assertEqual(before, (archive / 'backup.cbw').read_bytes())
            run('backup', work, '--archive-directory', str(archive), '--recovery-key-stdin', secret=key, expected=1)
            self.assertEqual(before, (archive / 'backup.cbw').read_bytes())
            run('restore', restored, '--archive-directory', str(archive), '--recovery-key-stdin', secret=wrong_key, expected=1)
            run('restore', restored, '--archive-directory', str(archive), '--project-id', 'different',
                '--recovery-key-stdin', secret=key, expected=1)
            self.assertEqual([], list(restored.iterdir()))
            run('restore', work, '--archive-directory', str(archive), '--recovery-key-stdin', secret=key, expected=1)
            self.assertEqual(before, (work / 'work.cbw').read_bytes())
            (archive / 'backup.cbw').write_bytes(before[:-1] + bytes([before[-1] ^ 1]))
            run('restore', restored, '--archive-directory', str(archive), '--recovery-key-stdin', secret=key, expected=1)
            self.assertEqual([], list(restored.iterdir()))
            (archive / 'backup.cbw').write_bytes(before)
            recovered = run('restore', restored, '--archive-directory', str(archive),
                            '--recovery-key-stdin', secret=key)
            self.assertEqual(created['work_digest'], recovered['work_digest'])
            self.assertEqual(view, run('show', restored))
            self.assertEqual(before, (work / 'work.cbw').read_bytes())
            self.assertNotEqual(before, (restored / 'work.cbw').read_bytes())
            for directory in (work, archive, restored):
                for path in directory.iterdir():
                    self.assertNotIn(bytes.fromhex(key.decode()), path.read_bytes())
