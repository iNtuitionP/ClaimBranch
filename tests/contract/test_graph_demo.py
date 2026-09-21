"""A human can inspect a synthetic graph without granting any write authority."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'tests/fixtures/saturation/truth-packet'


class GraphDemoTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.graph_demo'),
                             'Missing read-only graph demo')
        from scripts import graph_demo
        self.demo = graph_demo
        self.packet = json.loads((PACKET / 'truth-packet.json').read_text(encoding='utf-8'))

    def test_candidate_preserves_typed_conditions_and_global_evidence(self):
        main = self.demo.project(self.packet, 'main')
        candidate = self.demo.project(self.packet, 'candidate')
        self.assertEqual(main['observations'], candidate['observations'])
        self.assertEqual('supported', main['claim']['status'])
        self.assertEqual('contested', candidate['claim']['status'])
        self.assertEqual([], main['relationships'])
        self.assertEqual(['challenges', 'challenges', 'qualifies'],
                         [edge['type'] for edge in candidate['relationships']])
        self.assertEqual(['pruning', 'quantization', 'compression'],
                         [edge['condition'] for edge in candidate['relationships']])
        self.assertEqual(self.packet['observations'][2]['rationale'],
                         candidate['relationships'][2]['rationale'])
        self.assertEqual(['O-01', 'O-02', 'O-03'],
                         candidate['interpretation']['observation_ids'])

    def test_diff_computes_before_after_not_a_canned_research_summary(self):
        changes = self.demo.compare(self.packet)
        self.assertEqual(['claim-status', 'interpretation', 'relation:O-01',
                          'relation:O-02', 'relation:O-03'], [c['id'] for c in changes])
        self.assertEqual(('supported', 'contested'),
                         (changes[0]['before'], changes[0]['after']))
        altered = copy.deepcopy(self.packet)
        altered['claim']['initial_status'] = 'contested'
        self.assertNotIn('claim-status', [c['id'] for c in self.demo.compare(altered)])
        altered['unaided_human_interpretation']['statement'] = '별도의 합성 해석'
        self.assertEqual('별도의 합성 해석', self.demo.compare(altered)[0]['after']['statement'])

    def test_empty_selection_is_noop_with_no_impact(self):
        result = self.demo.preview(self.packet, [])
        self.assertEqual([], result['selected'])
        self.assertEqual(5, len(result['omitted']))
        self.assertEqual([], result['required_existing'])
        self.assertEqual([], result['impact_paths'])
        self.assertEqual(self.demo.project(self.packet, 'main'), result['result'])

    def test_global_observations_do_not_leak_unselected_relationship_judgments(self):
        for view in (self.demo.project(self.packet, 'main'),
                     self.demo.project(self.packet, 'candidate'),
                     self.demo.preview(self.packet, ['relation:O-03'])['result']):
            for observation in view['observations']:
                self.assertNotIn('relationship_to_claim', observation)
                self.assertNotIn('rationale', observation)
                self.assertEqual({'id', 'run_id', 'operator', 'expected'}, set(observation))

    def test_partial_selection_keeps_unselected_interpretation_and_claim_out(self):
        result = self.demo.preview(self.packet, ['relation:O-03'])
        self.assertEqual(['relation:O-03'], result['selected'])
        self.assertEqual(['C-01', 'O-03'], result['required_existing'])
        self.assertEqual('supported', result['result']['claim']['status'])
        self.assertIsNone(result['result']['interpretation'])
        self.assertEqual('qualifies', result['result']['relationships'][0]['type'])
        self.assertEqual([['O-03', 'C-01', 'A-01']], result['impact_paths'])
        self.assertIn('interpretation', result['omitted'])

    def test_interpretation_dependencies_reference_existing_observations(self):
        result = self.demo.preview(self.packet, ['interpretation'])
        self.assertEqual(['O-01', 'O-02', 'O-03'], result['required_existing'])
        self.assertEqual(3, len(result['result']['observations']))
        self.assertEqual([], result['impact_paths'])
        self.assertEqual([], result['result']['relationships'])

    def test_full_selection_follows_explicit_paths_without_applying(self):
        keys = [c['id'] for c in self.demo.compare(self.packet)]
        result = self.demo.preview(self.packet, reversed(keys))
        candidate = self.demo.project(self.packet, 'candidate')
        candidate['view'] = 'main'
        self.assertEqual(candidate, result['result'])
        self.assertEqual([], result['omitted'])
        self.assertIn(['I-01', 'O-03', 'C-01', 'A-01'], result['impact_paths'])
        self.assertIn(['C-01', 'A-01'], result['impact_paths'])
        self.assertEqual(keys, result['selected'])

    def test_unknown_duplicate_and_nonchange_selections_reject(self):
        for keys in (['unknown'], ['O-01'], ['relation:O-03', 'relation:O-03']):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                self.demo.preview(self.packet, keys)
        with self.assertRaises(ValueError):
            self.demo.project(self.packet, 'unknown')

    def test_missing_evidence_dependency_rejects(self):
        self.packet['unaided_human_interpretation']['observation_ids'].append('missing')
        with self.assertRaises(ValueError):
            self.demo.preview(self.packet, ['interpretation'])

    def test_operations_do_not_mutate_input(self):
        before = copy.deepcopy(self.packet)
        result = self.demo.preview(self.packet, ['interpretation', 'relation:O-03'])
        result['result']['observations'][0]['operator'] = 'changed output'
        self.assertEqual(before, self.packet)
        self.assertEqual(before, self.demo.load_packet())

    def run_cli(self, *args, cwd=ROOT, io_encoding='utf-8'):
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8='1',
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING=io_encoding)
        return subprocess.run([sys.executable, '-B', '-m', 'scripts.graph_demo', *args],
                              cwd=cwd, env=env, capture_output=True, text=True,
                              encoding='utf-8', timeout=30)

    def test_json_is_deterministic_and_marks_non_authority(self):
        first = self.run_cli('preview', '--select', 'relation:O-03', '--format', 'json')
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual('', first.stderr)
        payload = json.loads(first.stdout)
        self.assertEqual('synthetic-read-only', payload['mode'])
        self.assertFalse(payload['applied'])
        self.assertEqual(['relation:O-03'], payload['data']['selected'])
        self.assertEqual(first.stdout, self.run_cli('preview', '--select',
                         'relation:O-03', '--format', 'json').stdout)

    def test_human_graph_and_help_are_readable_without_ai(self):
        result = self.run_cli('show')
        self.assertEqual(0, result.returncode, result.stderr)
        for text in ('합성', '반박', '조건부', 'compression', 'O-03', 'C-01', 'A-01'):
            self.assertIn(text, result.stdout)
        self.assertNotIn('3 confirmed observations challenge', result.stdout)
        help_result = self.run_cli('--help')
        self.assertEqual(0, help_result.returncode)
        self.assertIn('preview', help_result.stdout)

    def test_bad_commands_and_write_options_fail_without_success(self):
        for args in (('apply',), ('show', '--project', '.'), ('preview', '--apply'),
                     ('preview', '--select', 'unknown'), ('show', '--select', 'claim-status')):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(2, result.returncode)
                self.assertEqual('', result.stdout)
                self.assertTrue(result.stderr)

    def test_help_and_parser_errors_are_utf8_even_with_ascii_environment(self):
        result = self.run_cli('--help', io_encoding='ascii')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('합성 연구 그래프', result.stdout)
        invalid = self.run_cli('알수없는명령', io_encoding='ascii')
        self.assertEqual(2, invalid.returncode, invalid.stderr)
        self.assertIn('알수없는명령', invalid.stderr)
        self.assertNotIn('Traceback', invalid.stderr)

    def test_run_from_empty_directory_writes_nothing_and_preserves_fixture(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in PACKET.iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory(prefix='claimbranch-graph-cli-') as temporary:
            result = self.run_cli('preview', '--select', 'claim-status', cwd=temporary)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([], list(Path(temporary).iterdir()))
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in PACKET.iterdir() if p.is_file()})


if __name__ == '__main__':
    unittest.main()
