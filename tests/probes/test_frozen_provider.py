"""One proposal response can never become an accepted operation."""

from dataclasses import replace
import unittest

from scripts.contracts.first_pass import ContractError, start_draft
from scripts.probes.frozen_provider import PendingProposal


class FrozenProviderTests(unittest.TestCase):
    def setUp(self):
        self.draft = start_draft("synthetic", "episode", "evidence", "claim")
        self.payload = {"operation": "propose", "text": "Frozen suggestion"}

    def test_valid_response_is_proposal_only_and_can_arrive_once(self):
        request = PendingProposal("request-one", self.draft)
        result = request.deliver("request-one", self.payload, current=self.draft)
        self.assertFalse(result.accepted)
        self.assertEqual("Frozen suggestion", result.text)
        with self.assertRaises(ContractError):
            request.deliver("request-one", self.payload, current=self.draft)

    def test_hostile_or_oversize_payloads_are_rejected(self):
        for payload in (
            {"operation": "accept", "text": "override"},
            {**self.payload, "tool": "write_file"},
            {**self.payload, "authorization_verified": True},
            {"operation": "propose", "text": "가" * 3000},
            {"operation": "propose", "text": "\ud800"},
            None,
        ):
            with self.subTest(payload_type=type(payload).__name__):
                request = PendingProposal("request-one", self.draft)
                with self.assertRaises(ContractError):
                    request.deliver("request-one", payload, current=self.draft)

    def test_cancelled_late_wrong_request_and_stale_draft_fail(self):
        for mode in ("cancelled", "wrong-request", "stale"):
            request = PendingProposal("request-one", self.draft)
            if mode == "cancelled":
                request.cancel()
            with self.assertRaises(ContractError):
                request.deliver("different" if mode == "wrong-request" else "request-one",
                    self.payload, current=replace(self.draft, revision=1) if mode == "stale" else self.draft)


class CodexBoundaryObservationTests(unittest.TestCase):
    """Observed custom-peer compatibility is never dispatch authority."""

    def test_file_access_exit_requires_positive_controls_every_denial_and_cleanup(self):
        from contextlib import redirect_stdout
        from copy import deepcopy
        import io
        from unittest.mock import patch
        from scripts.probes.codex_boundary import main
        valid={'startup_fixed':True,'baseline_startup_exit':-6,'read_control':True,
            'write_control':True,'spawn_control':True,'canary_unchanged':True,'cleanup_failed':False,
            'protected_directory_unchanged':True,
            'dispatch_supported':False,'inference_performed':False,
            'resource_denials':dict.fromkeys(('direct_read','direct_write','symlink_read',
                'symlink_write','directory_read','shell_spawn'),True)}
        cases=[(valid,0)]
        for field,value in [('read_control',False),('write_control',False),('spawn_control',False),('baseline_startup_exit',0),
                ('cleanup_failed',True),('canary_unchanged',False),('dispatch_supported',True),
                ('inference_performed',True),('protected_directory_unchanged',False)]:
            bad=deepcopy(valid);bad[field]=value;cases.append((bad,1))
        for field in valid['resource_denials']:
            for value in (False,1):
                bad=deepcopy(valid);bad['resource_denials'][field]=value;cases.append((bad,1))
        bad=deepcopy(valid);del bad['resource_denials']['direct_read'];cases.append((bad,1))
        for observed,expected in cases:
            with self.subTest(observed=observed), redirect_stdout(io.StringIO()), \
                    patch('scripts.probes.codex_boundary.observe_file_access',return_value=observed), \
                    patch('scripts.probes.codex_boundary.observe') as inference_peer:
                self.assertEqual(expected,main(['--client','unused','--file-access']))
                inference_peer.assert_not_called()

    def test_host_file_replies_reject_malformed_shapes_as_structured_failure(self):
        from scripts.probes.codex_boundary import _file_reply
        for message in ({'id':2,'error':'x'}, {'id':2,'result':None},
                {'id':2,'result':{} ,'error':{}}, {'id':True,'result':{}},
                {'id':2,'error':{'code':-32603,'message':None}}):
            with self.subTest(message=message),self.assertRaises(ValueError):
                _file_reply(message,2)
        self.assertEqual({'id':2,'result':{}},_file_reply({'id':2,'result':{}},2))

    def test_file_access_failure_never_reports_a_supported_provider(self):
        from contextlib import redirect_stdout
        import io,json
        from unittest.mock import patch
        from scripts.probes.codex_boundary import main
        output=io.StringIO()
        with patch('scripts.probes.codex_boundary.observe_file_access',side_effect=ValueError('private marker')), \
                redirect_stdout(output):
            self.assertEqual(2,main(['--client','unused','--file-access']))
        self.assertFalse(json.loads(output.getvalue())['dispatch_supported'])
        self.assertNotIn('private marker',output.getvalue())

    def test_file_probe_uncertain_termination_still_reaps_and_closes_pipes(self):
        import subprocess
        from unittest.mock import Mock,patch
        from scripts.probes.codex_boundary import _close_file_probe
        for kill_error,wait_error in [(PermissionError('owned denial'),None),
                (None,subprocess.TimeoutExpired('owned process',5)),
                (OSError('owned error'),OSError('owned wait error')),
                (RuntimeError('owned kill error'),None),(None,RuntimeError('owned wait error'))]:
            process=Mock(pid=12345)
            process.wait.side_effect=wait_error
            with self.subTest(kill=kill_error,wait=wait_error), \
                    patch('scripts.probes.codex_boundary.os.killpg',side_effect=kill_error):
                self.assertFalse(_close_file_probe(process))
            process.wait.assert_called_once_with(timeout=5)
            process.stdin.close.assert_called_once()
            process.stdout.close.assert_called_once()

    def test_file_probe_close_error_cannot_skip_the_other_pipe(self):
        from unittest.mock import Mock,patch
        from scripts.probes.codex_boundary import _close_file_probe
        process=Mock(pid=12345)
        process.stdin.close.side_effect=RuntimeError('owned close error')
        with patch('scripts.probes.codex_boundary.os.killpg'):
            self.assertFalse(_close_file_probe(process))
        process.stdout.close.assert_called_once()

    def test_request_metadata_discards_input_and_never_qualifies(self):
        from scripts.probes.codex_boundary import request_summary
        raw = b'{"tools":[],"input":[{"text":"private-input-marker"}],"secret":"credential-marker"}'
        result = request_summary(raw, credential_present=False)
        self.assertTrue(result['tool_free_request'])
        self.assertFalse(result['dispatch_supported'])
        self.assertFalse(result['inference_performed'])
        self.assertNotIn('private-input-marker', repr(result))
        self.assertNotIn('credential-marker', repr(result))

    def test_remaining_tools_and_credentials_do_not_pass(self):
        from scripts.probes.codex_boundary import request_summary
        tool = request_summary(b'{"tools":[{"type":"function","name":"request_user_input"}]}',
                               credential_present=False)
        self.assertEqual(['request_user_input'], tool['tool_names'])
        self.assertFalse(tool['tool_free_request'])
        self.assertFalse(request_summary(b'{"tools":[]}', credential_present=True)['tool_free_request'])

    def test_missing_ambiguous_or_hostile_tool_observation_refuses(self):
        from scripts.probes.codex_boundary import request_summary
        for raw in (b'{}', b'{"tools":{}}', b'{"tools":[{}]}', b'{"tools":[],"input":null}',
                    b'[' * 100_000,
                    br'{"tools":[{"name":"\u001b[2J"}]}',
                    b'{"tools":[{"name":"shell"}],"tools":[]}'):
            with self.subTest(raw_prefix=raw[:80], bytes=len(raw)):
                with self.assertRaises(ValueError):
                    request_summary(raw, credential_present=False)

    def test_observation_exit_requires_exact_client_exit_and_tool_set(self):
        from contextlib import redirect_stdout
        from copy import deepcopy
        import io
        from unittest.mock import patch
        from scripts.probes.codex_boundary import main
        valid = {'timed_out': False, 'inspection_errors': [], 'client_exit': 1,
                 'requests': [{'credential_present': False, 'tool_names': ['request_user_input']}
                              for _ in range(2)],
                 'tool_call_denials': {'shell': True, 'request_user_input': True},
                 'canary_unchanged': True}
        cases = [(valid, 0)]
        for field, value in (('client_exit', 0), ('client_exit', -9), ('canary_unchanged', False)):
            changed = deepcopy(valid); changed[field] = value; cases.append((changed, 1))
        changed = deepcopy(valid); changed['requests'][0]['tool_names'] = ['shell']
        cases.append((changed, 1))
        changed = deepcopy(valid); changed['tool_call_denials']['shell'] = False
        cases.append((changed, 1))
        for field, value in (('timed_out', True), ('cleanup_failed', True), ('inspection_errors', ['failed']),
                             ('requests', valid['requests'][:1]),
                             ('requests', valid['requests'] * 2)):
            changed = deepcopy(valid); changed[field] = value; cases.append((changed, 1))
        changed = deepcopy(valid); changed['requests'][1]['credential_present'] = True
        cases.append((changed, 1))
        changed = deepcopy(valid); changed['tool_call_denials']['request_user_input'] = False
        cases.append((changed, 1))
        for observed, expected in cases:
            with self.subTest(observed=observed), patch('scripts.probes.codex_boundary.observe',
                    return_value=observed), redirect_stdout(io.StringIO()):
                self.assertEqual(expected, main(['--client', 'unused']))

    def test_missing_or_binary_canary_is_a_failed_observation(self):
        from pathlib import Path
        import tempfile
        from scripts.probes.codex_boundary import _canary_unchanged, CANARY_BYTES
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'owned-canary'
            self.assertFalse(_canary_unchanged(path))
            path.write_bytes(b'\xff')
            self.assertFalse(_canary_unchanged(path))
            path.write_bytes(CANARY_BYTES)
            self.assertTrue(_canary_unchanged(path))

    def test_cleanup_failure_preserves_completed_observation(self):
        import shutil
        from unittest.mock import patch
        from scripts.probes.codex_boundary import _scratch
        result = {}
        with patch('scripts.probes.codex_boundary.shutil.rmtree', side_effect=OSError('owned failure')):
            with _scratch(result) as root:
                result['observed'] = True
        try:
            self.assertEqual({'observed': True, 'cleanup_failed': True}, result)
        finally:
            shutil.rmtree(root)

    def test_sigterm_cancellation_restores_the_previous_handler(self):
        from contextlib import redirect_stdout
        import io
        import signal
        from unittest.mock import patch
        from scripts.probes.codex_boundary import main
        previous = signal.getsignal(signal.SIGTERM)
        def interrupted(client, **kwargs):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            self.assertTrue(kwargs['cancelled']())
            return {}
        with patch('scripts.probes.codex_boundary.observe', side_effect=interrupted), redirect_stdout(io.StringIO()):
            self.assertEqual(128 + signal.SIGTERM, main(['--client', 'unused']))
        self.assertIs(previous, signal.getsignal(signal.SIGTERM))

    def test_cleanup_failure_does_not_replace_cancellation(self):
        import shutil
        from unittest.mock import patch
        from scripts.probes.codex_boundary import _scratch
        root = None
        try:
            with patch('scripts.probes.codex_boundary.shutil.rmtree', side_effect=OSError('owned failure')):
                with self.assertRaises(KeyboardInterrupt) as raised:
                    with _scratch({}) as root:
                        raise KeyboardInterrupt()
            self.assertTrue(raised.exception.cleanup_failed)
        finally:
            if root is not None:
                shutil.rmtree(root)

    def test_failed_startup_keeps_cleanup_failure_in_diagnostic(self):
        from contextlib import redirect_stdout
        import io
        import json
        import shutil
        from unittest.mock import patch
        from scripts.probes.codex_boundary import _scratch, main
        roots = []
        def failed(client, **kwargs):
            with _scratch({}) as root:
                roots.append(root)
        output = io.StringIO()
        try:
            with patch('scripts.probes.codex_boundary.observe', side_effect=failed), \
                 patch('scripts.probes.codex_boundary.shutil.rmtree', side_effect=OSError('owned failure')), \
                 redirect_stdout(output):
                self.assertEqual(2, main(['--client', 'unused']))
            result = json.loads(output.getvalue())
            self.assertTrue(result['cleanup_failed'])
            self.assertFalse(result['dispatch_supported'])
            self.assertNotIn('owned failure', output.getvalue())
        finally:
            for root in roots:
                shutil.rmtree(root)
