"""Synthetic checkpoint lifecycle commands; no accepted writer or TUI mutation."""
import getpass
import hashlib
import hmac
import json
import re
import secrets
import sys
from pathlib import Path

from claimbranch.core.canonical import ContractError, decode
from claimbranch.fixtures import replay_example
from .device_work_store import DevicePaperWorkStore
from .paper_service import PaperService
from .paper_work_store import PaperWork
from .work_archive import WorkArchive
from .work_cipher import MacWorkCipher


def add_work_commands(demos):
    work = demos.add_parser('work', help='Save, reopen and recover a synthetic encrypted paper on Mac')
    actions = work.add_subparsers(dest='work_action', required=True)
    for name in ('init', 'status', 'show', 'backup', 'restore'):
        action = actions.add_parser(name)
        action.add_argument('--directory', required=True, help='Existing private directory outside Git')
        action.add_argument('--json', action='store_true')
        if name == 'init':
            action.add_argument('--variant', choices=('manual', 'recorded'), default='manual')
        else:
            action.add_argument('--project-id', default='project', help='Expected project identity (example: project)')
        if name in ('backup', 'restore'):
            action.add_argument('--archive-directory', required=True, help='Separate private directory containing backup.cbw')
        if name in ('init', 'backup', 'restore'):
            action.add_argument('--recovery-key-stdin', action='store_true',
                                help='Read 64 hex characters and EOF from private synthetic-test stdin; never a command argument')


def _decode_key(raw):
    if type(raw) is not bytes or re.fullmatch(rb'[0-9a-fA-F]{64}\n?', raw) is None:
        raise ContractError('recovery key must be exactly 64 hexadecimal characters')
    return bytes.fromhex(raw.decode('ascii'))


def recovery_key(*, from_stdin, create=False):
    if from_stdin:
        try:
            if sys.stdin.isatty():
                raise ContractError('key stdin mode requires private input, not an echoing terminal')
            return _decode_key(sys.stdin.buffer.read(66))
        except (AttributeError, OSError, ValueError):
            raise ContractError('recovery key input is unavailable or malformed') from None
    # getpass can otherwise fall back to echoing input. Require an actual
    # controlling terminal and treat its warning as failure before fallback.
    import warnings
    try:
        with open('/dev/tty', 'w', encoding='utf-8') as terminal:
            generated = secrets.token_hex(32) if create else None
            if generated:
                terminal.write('합성 작업 복구 키입니다. 백업과 별도로 보관하세요.\n' + generated + '\n')
                terminal.flush()
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                entered = getpass.getpass('복구 키를 입력하세요 (표시되지 않음): ', stream=terminal)
            key = _decode_key(entered.encode('utf-8'))
            if generated and not hmac.compare_digest(key, bytes.fromhex(generated)):
                raise ContractError('recovery key confirmation did not match; no work was initialized')
            return key
    except (OSError, EOFError, UnicodeError, getpass.GetPassWarning):
        raise ContractError('terminal key entry failed; no work was initialized by this entry step') from None


def summary(work, action):
    history = work.history
    return {'status': action, 'kind': 'synthetic-encrypted-work', 'project_id': work.project_id,
            'work_digest': hashlib.sha256(work.payload).hexdigest(),
            'history_digest': hashlib.sha256(history.manifest()).hexdigest(),
            'saved_commands': len(history.commands), 'authority': 'unaccepted-work',
            'authorization_verified': False, 'resumed_authorization': False}


def execute(args):
    key = None
    action = args.work_action
    if action in ('backup', 'restore') and Path(args.directory).samefile(args.archive_directory):
        raise ContractError('work and backup require separate directories')
    if action in ('init', 'backup', 'restore'):
        key = recovery_key(from_stdin=args.recovery_key_stdin, create=action == 'init')
    try:
        with MacWorkCipher() as cipher:
            if action == 'init':
                work = PaperWork.create(replay_example(args.variant, series=True))
                with DevicePaperWorkStore.create(args.directory, cipher=cipher,
                        project_id=work.project_id, recovery_key=key) as store:
                    store.save(work)
            elif action == 'restore':
                with WorkArchive(args.archive_directory) as archive:
                    raw = archive.read()
                work = DevicePaperWorkStore.restore_backup(raw, args.directory, cipher=cipher,
                    project_id=args.project_id, recovery_key=key)
            else:
                with DevicePaperWorkStore(args.directory, cipher=cipher, project_id=args.project_id) as store:
                    work = store.load()
                    if work is None:
                        raise ContractError('saved work is missing; no replacement was created')
                    if action == 'backup':
                        raw = store.backup(verify_recovery_key=key)
                        with WorkArchive(args.archive_directory) as archive:
                            archive.write(raw)
            result = summary(work, action)
            if action == 'show':
                service = PaperService(work.history)
                result.update(graph=service.query('main'), pending_work=service.pending_work())
            return result
    finally:
        key = None  # Release the reference; no memory-zeroization claim.


def _emit(args, result):
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    else:
        labels = {'init': '합성 작업 저장 완료', 'status': '저장된 합성 작업을 다시 읽었습니다',
                  'show': '저장된 논증과 조건부 후속 작업', 'backup': '암호화 백업 저장 완료',
                  'restore': '새 위치에 합성 작업 복원 완료'}
        print(labels[args.work_action])
        print('기록 ' + str(result['saved_commands']) + '개 · 검토/이력 보존 · 승인 권한 없음')
        if args.work_action == 'show':
            print(json.dumps({'graph': result['graph'], 'pending_work': result['pending_work']},
                             ensure_ascii=False, indent=2))
        print('재확인: python3.13 -m claimbranch demo work status --directory <작업 폴더>', flush=True)


def _report(value):
    try:
        print(json.dumps(value), file=sys.stderr, flush=True)
    except OSError:
        try:
            sys.stderr.close()
        except OSError:
            pass


def run_work_command(args):
    try:
        result = execute(args)
    except KeyboardInterrupt:
        _report({'status': 'interrupted', 'authorization_verified': False,
                 'next_action': 'Inspect saved work with status; retry backup only in a new directory.'})
        return 130
    except (ContractError, OSError):
        # Do not expose paths, input secrets or platform exception contents.
        value = {'status': 'unavailable', 'code': 'work-operation-failed',
                 'authorization_verified': False,
                 'reason': 'Work could not be completed. Existing work was not deliberately replaced; a new output may be incomplete.',
                 'next_action': 'Reopen existing work with demo work status. Check the private paths, expected project and recovery key; retry backup or restore in a new directory.'}
        _report(value)
        return 1
    try:
        _emit(args, result)
    except (OSError, KeyboardInterrupt) as error:
        if isinstance(error, OSError):
            # A buffered broken pipe otherwise fails again during interpreter
            # shutdown and changes the promised exit code to 120.
            try:
                sys.stdout.close()
            except OSError:
                pass
        _report({'status': 'output-unavailable', 'code': 'work-output-failed',
                 'operation': args.work_action, 'operation_completed': True,
                 'authorization_verified': False,
                 'next_action': 'The operation completed. Keep its recovery key; inspect existing work with status before any retry.'})
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    return 0
