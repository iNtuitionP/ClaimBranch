import ast
import importlib
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from claimbranch.application.cli import main
from claimbranch.core.canonical import ContractError


class CliTests(unittest.TestCase):
    def test_bootstrap_remains_parseable_before_modern_application_imports(self):
        root = Path(__file__).resolve().parents[2]
        for name in ('__init__.py', '__main__.py', 'runtime.py'):
            ast.parse((root / 'claimbranch' / name).read_text(), feature_version=(3, 8))

    def test_old_runtime_refuses_before_application_import_or_research_access(self):
        root = Path(__file__).resolve().parents[2]
        program = """import runpy, sys
sys.version_info = (3, 9, 6)
class DenyApplication:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('claimbranch.application') or fullname.startswith('claimbranch.core'):
            raise AssertionError('application imported before version check')
sys.meta_path.insert(0, DenyApplication())
sys.argv = ['claimbranch', 'project', 'open', '--directory', '/never-open', '--json']
runpy.run_module('claimbranch', run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-c', program], cwd=root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual((3, ''), (result.returncode, result.stderr))
        report = json.loads(result.stdout)
        self.assertEqual('not-run', report['synthetic_replay'])
        self.assertEqual('3.13', report['supported_python'])
        self.assertIn('python-3.13', report['missing_prerequisites'])
        self.assertEqual({'conda', 'uv'}, {x['tool'] for x in
            report['prerequisite_guidance'][0]['alternatives']})

    def test_broken_curses_extension_is_unavailable_with_guidance_and_no_install(self):
        real_import = importlib.import_module
        def broken(name, *args, **kwargs):
            if name == 'curses':
                raise ImportError('missing _curses')
            return real_import(name, *args, **kwargs)
        with patch('claimbranch.runtime.importlib.import_module', side_effect=broken), \
             patch('subprocess.run', side_effect=AssertionError('installer launched')):
            code, out, err = self.invoke(['doctor', '--json'])
        self.assertEqual((3, ''), (code, err))
        report = json.loads(out)
        self.assertIn('unix-curses', report['missing_prerequisites'])
        guide = next(x for x in report['prerequisite_guidance'] if x['prerequisite']=='unix-curses')
        self.assertIn('_curses', guide['message'])
        self.assertIn('conda/uv check command', report['next_action'])

    def test_text_doctor_explains_fixed_git_path_instead_of_offering_project_init(self):
        with patch('claimbranch.runtime.shutil.which', return_value='/conda/bin/git'), \
             patch('claimbranch.runtime.os.access', return_value=False):
            code, out, err = self.invoke(['doctor'])
        self.assertEqual((3, ''), (code, err))
        self.assertIn('/usr/bin/git', out)
        self.assertIn('PATH', out)
        self.assertNotIn('project init --help', out)

    def test_mac_git_shim_without_developer_tools_is_not_ready(self):
        with patch('claimbranch.runtime.sys.platform', 'darwin'), \
             patch('claimbranch.runtime.shutil.which', return_value='/usr/bin/git'), \
             patch('claimbranch.runtime.os.access', return_value=True), \
             patch('claimbranch.runtime.os.path.isfile', return_value=False), \
             patch('subprocess.run', side_effect=AssertionError('shim launched')):
            code, out, err = self.invoke(['doctor', '--json'])
        self.assertEqual((3, ''), (code, err))
        report = json.loads(out)
        self.assertIn('git', report['missing_prerequisites'])
        self.assertIn('installer shims', report['prerequisite_guidance'][0]['message'])

    def test_mac_git_uses_selected_developer_root_before_installed_fallback(self):
        from claimbranch.runtime import _mac_developer_git
        clt = '/Library/Developer/CommandLineTools/usr/bin/git'
        with patch('claimbranch.runtime.os.path.lexists', return_value=True), \
             patch('claimbranch.runtime.os.path.realpath', return_value='/missing-selected-tools'), \
             patch('claimbranch.runtime.os.path.isfile', side_effect=lambda path: path == clt), \
             patch('claimbranch.runtime.os.access', return_value=True):
            self.assertFalse(_mac_developer_git())
        with patch('claimbranch.runtime.os.path.lexists', return_value=False), \
             patch('claimbranch.runtime.os.path.isfile', side_effect=lambda path: path == clt), \
             patch('claimbranch.runtime.os.access', return_value=True):
            self.assertTrue(_mac_developer_git())

    def test_unsupported_python_does_not_probe_another_interpreters_curses(self):
        from claimbranch.runtime import prerequisite_report
        with patch('claimbranch.runtime.sys.version_info', (3, 9, 6)), \
             patch('claimbranch.runtime.importlib.import_module', side_effect=AssertionError('old curses probed')):
            report = prerequisite_report()
        self.assertIsNone(report['prerequisites']['unix-curses'])
        self.assertNotIn('unix-curses', report['missing_prerequisites'])

    def test_doctor_handles_missing_curses_before_all_parser_imports(self):
        program = """import runpy, sys
class DenyCurses:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('curses', '_curses'):
            raise ImportError('curses missing')
sys.meta_path.insert(0, DenyCurses())
sys.argv = ['claimbranch', 'doctor', '--json']
runpy.run_module('claimbranch', run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-c', program],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=15)
        self.assertEqual((3, ''), (result.returncode, result.stderr))
        self.assertIn('unix-curses', json.loads(result.stdout)['missing_prerequisites'])

    def test_runtime_error_guidance_uses_commands_shipped_in_the_artifact(self):
        with patch('claimbranch.application.cli.replay_fixture',side_effect=ContractError('invalid resource')):
            code,_,errors=self.invoke(['doctor','--json'])
        self.assertEqual(1,code)
        next_action=json.loads(errors)['next_action']
        self.assertIn('-m claimbranch doctor',next_action)
        self.assertNotIn('scripts/',next_action)

    def test_doctor_checks_the_git_binary_used_for_project_inspection(self):
        with patch('claimbranch.runtime.shutil.which',return_value='/custom/bin/git'), \
             patch('claimbranch.runtime.os.access',return_value=False):
            code,out,err=self.invoke(['doctor','--json'])
        self.assertEqual(3,code); self.assertEqual('',err)
        self.assertIn('git',json.loads(out)['missing_prerequisites'])

    def test_terminal_ai_off_launch_and_snapshot(self):
        with patch('claimbranch.application.tui.run_terminal', return_value=0) as run:
            self.assertEqual(0, self.invoke(['demo', 'tui', '--ai-off'])[0])
            self.assertTrue(run.call_args.kwargs['ai_off'])
            self.assertEqual(0, self.invoke(['demo', 'tui'])[0])
            self.assertFalse(run.call_args.kwargs['ai_off'])
        code, output, errors = self.invoke(['demo', 'tui', '--ai-off', '--snapshot'])
        self.assertEqual((0, ''), (code, errors))
        self.assertIn('AI OFF', output)

    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(args)
        return code, output.getvalue(), errors.getvalue()

    def test_doctor_reports_incomplete_readiness_without_native_or_provider_execution(self):
        with patch("subprocess.run", side_effect=AssertionError("process launched")):
            code, output, errors = self.invoke(["doctor", "--json"])
        self.assertEqual(0, code)
        self.assertEqual("", errors)
        value = json.loads(output)
        self.assertEqual('personal-alpha-ready',value['status'])
        self.assertEqual('ready',value['personal_workspace'])
        self.assertFalse(value['storage']['encrypted'])
        self.assertEqual("ready", value["synthetic_replay"])
        self.assertEqual("unavailable", value["protected_acceptance"])
        self.assertFalse(value["authorization_verified"])

    def test_doctor_identifies_missing_alpha_prerequisite_without_native_work(self):
        with patch('claimbranch.runtime.shutil.which',return_value=None):
            code,out,err=self.invoke(['doctor','--json'])
        self.assertEqual((3,''),(code,err))
        self.assertIn('git',json.loads(out)['missing_prerequisites'])

    def test_both_offline_variants_and_non_authoritative_audit(self):
        code, output, errors = self.invoke(["demo", "saturation", "--json"])
        self.assertEqual((0, ""), (code, errors))
        manual, recorded = json.loads(output)
        self.assertFalse(manual["ai_influenced"])
        self.assertTrue(recorded["ai_influenced"])
        self.assertTrue(all(item["golden_match"] and not item["authorization_verified"] for item in (manual, recorded)))
        audit = json.loads(self.invoke(["demo", "saturation", "--audit", "recorded"])[1])
        self.assertEqual("unverified-candidate", audit["authority"])

    def test_module_entrypoint_and_unknown_real_project_command(self):
        root = Path(__file__).resolve().parents[2]
        version = subprocess.run([sys.executable, "-m", "claimbranch", "--version"], cwd=root, capture_output=True, timeout=10)
        self.assertEqual(0, version.returncode)
        self.assertIn(b"unreleased", version.stdout)
        rejected = subprocess.run([sys.executable, "-m", "claimbranch", "project", "import", "/tmp/no-import"], cwd=root, capture_output=True, timeout=10)
        self.assertEqual(2, rejected.returncode)
        self.assertEqual(b"", rejected.stdout)

    def test_paper_context_and_complete_offline_draft_routes(self):
        code, output, errors = self.invoke(["demo", "paper", "--context", "--json"])
        self.assertEqual((0, ""), (code, errors))
        self.assertEqual(2, json.loads(output)["schema_version"])
        for variant in ("manual", "recorded"):
            code, output, errors = self.invoke(["demo", "paper", "--workflow", "--variant", variant, "--json"])
            self.assertEqual((0, ""), (code, errors))
            value = json.loads(output)
            self.assertTrue(value["source_unchanged"])
            self.assertTrue(value["initial_draft_blank"])
            self.assertTrue(value["scripted_example"])
            self.assertEqual(0, value["state"]["accepted_writes"])
            self.assertEqual(variant == "recorded", value["state"]["draft"]["ai_influenced"])
            self.assertEqual(1 if variant == "recorded" else 0, len(value["state"]["traces"]))
            self.assertEqual(["claim-pruning", "claim-pruning-detail", "thesis"], value["scenario"]["potentially_affected_claim_ids"])
            preview = value["changes_preview"]["preview"]
            self.assertEqual(["edge-pruning", "interpretation"], preview["selection"]["selected"])
            self.assertEqual(["claim-pruning-detail"], preview["selection"]["required"])
            self.assertEqual(["replication"], preview["selection"]["omitted"])
            self.assertEqual(variant == "recorded", preview["provenance"]["ai_influenced"])
            self.assertFalse(preview["manuscript"]["write_available"])
            self.assertEqual(value["changes_preview"]["digest"], value["changes_review"]["preview_digest"])
            self.assertEqual("deferred" if variant == "recorded" else "not-required", value["changes_review"]["disposition"])
            self.assertFalse(value["changes_review"]["acceptance_available"])
            self.assertEqual(["human"], [item["contributor"] for item in preview["provenance"]["source_judgment"]["history"]])
            self.assertIsNone(value["state"]["changes_review"])

    def test_paper_workflow_names_selected_review_in_the_cli(self):
        code, output, errors = self.invoke(["demo", "paper", "--workflow"])
        self.assertEqual((0, ""), (code, errors))
        self.assertIn("선택한 과학적 변경 검토", output)
        self.assertIn("edge-pruning, interpretation", output)
        self.assertIn("claim-pruning-detail", output)
        self.assertIn("replication", output)

    def test_repeated_episode_example_retains_original_evidence_and_ai(self):
        for variant in ("manual", "recorded"):
            code, output, errors = self.invoke(["demo", "paper", "--episodes", "--variant", variant, "--json"])
            self.assertEqual((0, ""), (code, errors))
            value = json.loads(output)
            self.assertTrue(value["golden_match"])
            self.assertTrue(value["earlier_draft_retained"])
            self.assertTrue(value["new_draft_blank"])
            self.assertTrue(value["reviewed_candidate_matches_example"])
            self.assertTrue(value["merge_review_cleared"])
            self.assertTrue(value["branch_draft_started_blank"])
            self.assertTrue(value["branch_source_unchanged"])
            self.assertTrue(value["branch_draft_retained"])
            followup = value["followup"]
            for key in ("replayed_work_matches", "wording_started_blank", "postimage_matches_review", "work_unchanged", "wording_retained", "review_cleared"):
                self.assertTrue(followup[key], key)
            self.assertEqual(2 if variant == "manual" else 4, len(followup["pending_work"]["items"]))
            self.assertEqual(followup["current"]["history_digest"], followup["pending_work"]["history_digest"])
            self.assertEqual(followup["preview"]["history_digest"], followup["pending_work"]["history_digest"])
            self.assertFalse(followup["preview"]["source_verified"])
            self.assertFalse(followup["review"]["write_available"])
            self.assertEqual(["create-reasoning-branch", "record-interpretation"],
                [cmd["operation_type"] for cmd in value["branch_preview"]["commands"]])
            self.assertEqual(["edge-pruning", "interpretation-two"], value["branch_preview"]["preview"]["selection"]["required"])
            self.assertFalse(value["branch_preview"]["acceptance_available"])
            self.assertEqual(["status-pruning"], value["merge_preview"]["preview"]["selection"]["selected"])
            self.assertEqual("deferred" if variant == "recorded" else "not-required", value["merge_review"]["sealed_review"]["disposition"])
            self.assertFalse(value["merge_review"]["acceptance_available"])
            self.assertFalse(value["authorization_verified"])
            self.assertEqual(2, len(value["timeline"]["episodes"]))
            now = {node["id"]: node for node in value["current"]["nodes"]}
            then = {node["id"]: node for node in value["at_first_close"]["nodes"]}
            self.assertEqual("1.2", now["obs-1"]["content"]["value"])
            self.assertEqual("0.4", then["obs-1"]["content"]["value"])
            self.assertEqual("contested", now["claim-pruning-detail"]["content"]["status"])
            self.assertEqual(["episode", "episode-two"], [item["episode_id"] for item in value["current"]["judgments"]])
            self.assertEqual(variant == "recorded", any(item["contributor"] == "ai" for item in value["current"]["judgments"][0]["history"]))

    def test_conditional_work_can_be_inspected_without_opening_any_ui(self):
        code, output, errors = self.invoke(["demo", "paper", "--pending", "--variant", "recorded", "--json"])
        self.assertEqual((0, ""), (code, errors))
        work = json.loads(output)
        self.assertEqual(["manuscript", "understanding", "manuscript", "understanding"], [item["kind"] for item in work["items"]])
        self.assertEqual(0, work["accepted_debts_created"])
        self.assertFalse(work["authorization_verified"])

    def test_tui_merge_example_opens_active_prefix_without_changing_closed_series(self):
        code, active, errors = self.invoke(['demo', 'tui', '--merge-example', '--snapshot'])
        self.assertEqual((0, ''), (code, errors))
        self.assertIn('active reasoning', active)
        self.assertIn('episode-two', active)
        code, closed, errors = self.invoke(['demo', 'tui', '--series', '--snapshot'])
        self.assertEqual((0, ''), (code, errors))
        self.assertIn('closed reasoning', closed)
        with self.assertRaises(SystemExit):
            self.invoke(['demo', 'tui', '--merge-example', '--series', '--snapshot'])

    def test_offline_provider_exercise_is_available_without_ui_or_endpoint(self):
        code, output, errors = self.invoke(["demo", "paper", "--provider", "--json"])
        self.assertEqual((0, ""), (code, errors))
        result = json.loads(output)
        self.assertEqual(5, len(result["cases"]))
        self.assertTrue(result["source_unchanged"])
        self.assertFalse(result["authorization_verified"])
        code, output, errors = self.invoke(["demo", "paper", "--provider"])
        self.assertEqual((0, ""), (code, errors))
        for label in ("제안 채택 후 수정", "요청 취소", "초안 수정", "시간 초과", "응답 거절", "수동"):
            self.assertIn(label, output)


if __name__ == "__main__":
    unittest.main()
