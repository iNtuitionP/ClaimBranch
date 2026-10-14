"""Owned migration inputs; no private paper or provider request."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from claimbranch.core.argument_import import preview_import, import_schema, _leaves
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode, source_record, source_bytes
from claimbranch.core.research_schema import normalize
from claimbranch.application.cli import main


def fixture():
    metric = dict(name='Quality', definition='Blind pairwise quality preference', unit='fraction', comparison='Baseline writer')
    bodies = [
        ('T', 'thesis', dict(statement='Rubric gains alone do not guarantee better writing.')),
        ('C', 'claim', dict(role='main', statement='A rubric can reward superficial features.', scope='Synthetic writing task', parent_ids=['T'], status='supported', basis_ids=['E'])),
        ('X', 'experiment', dict(question='Does rubric optimization improve blind preference?', method='Synthetic blind comparison', conditions='Same prompts, baseline and optimized model', metric=metric, source_ref='synthetic/result.json')),
        ('O', 'observation', dict(experiment_id='X', statement='Rubric gain accompanied a blind preference decline.', value='0.35', status='confirmed')),
        ('E', 'scientific-edge', dict(edge_type='supports', source_id='O', target_id='C', rationale='The two measurements disagree on this task.')),
        ('D', 'historical-decision', dict(group_id=None, rationale='Retain both measurements and narrow the claim.', record_ids=['C', 'O'])),
    ]
    original = {'entries': [deepcopy(body) for _, _, body in bodies]}
    original['entries'][1]['banned_terms'] = ['guarantees']
    original['entries'][3]['values'] = {'seed1': 0.35, 'seed2': 0.4}
    records = []
    for index, (key, kind, body) in enumerate(bodies):
        records.append(dict(id=key, kind=kind, body=body, source_pointer='/entries/' + str(index),
            origin=dict(contributor='ai' if key == 'C' else 'unknown', detail=None),
            recorded_at='2026-09-01T00:00:00Z' if key == 'D' else None,
            mappings=[dict(target=pointer, source='/entries/' + str(index) + pointer, transformation=None)
                      for pointer, _ in _leaves(body)]))
    raw = json.dumps(original, ensure_ascii=False, indent=2).encode()
    return dict(schema='claimbranch.argument-import/v1', profile='paper', project_id='synthetic-paper',
                title='Synthetic rubric study', source=source_record(raw), records=records, selected_ids=['C', 'D'])


def preview(value):
    return preview_import(encode(value, purpose='project'))


class ArgumentImportTests(unittest.TestCase):
    def test_complete_dependency_closure_origin_chronology_and_exact_raw_source(self):
        value = fixture(); raw = encode(value, purpose='project'); result = preview_import(raw)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(['C', 'D'], result['selected'])
        self.assertEqual(['E', 'O', 'T', 'X'], result['required'])
        self.assertEqual([], result['omitted'])
        self.assertEqual(1, result['counts']['historical-decision']['used'])
        retained = {record['id']: record for record in result['records']}
        self.assertEqual('ai', retained['C']['origin']['contributor'])
        self.assertEqual('unknown', retained['O']['origin']['contributor'])
        self.assertEqual('2026-09-01T00:00:00Z', retained['D']['recorded_at'])
        unresolved = sum(result['unresolved_source_pointers'], [])
        self.assertEqual(['/entries/1/banned_terms/0', '/entries/3/values/seed1', '/entries/3/values/seed2'], unresolved)
        self.assertEqual(source_bytes(value['source']), source_bytes(result['source']))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result['envelope_sha256'])
        self.assertFalse(result['writes']); self.assertFalse(result['registration_available'])
        self.assertFalse(result['source_fidelity_verified'])
        self.assertEqual(result, preview_import(raw))
        normalize(value, import_schema(), profile='paper')

    def test_source_only_omission_is_visible_and_missing_authorship_never_defaults(self):
        value = fixture(); value['selected_ids'] = ['T']
        result = preview(value)
        self.assertTrue(result['valid'])
        self.assertEqual(['C', 'D', 'E', 'O', 'X'], result['omitted'])
        self.assertGreater(result['unresolved_source_leaf_count'], 3)
        del value['records'][0]['origin']
        result = preview(value)
        self.assertFalse(result['valid'])
        self.assertIn('/records/0/origin', [error['pointer'] for error in result['errors']])

    def test_errors_across_records_are_reported_without_coercion_or_partial_success(self):
        value = fixture()
        value['records'][1]['body']['scope'] = ''
        value['records'][2]['body']['metric']['unit'] = 2
        value['records'][3]['body']['value'] = 0.35
        # Floating mapped numbers are rejected by the finite parser itself.
        with self.assertRaises(ContractError): preview_import(json.dumps(value).encode())
        value['records'][3]['body']['value'] = 35
        result = preview(value)
        paths = {error['pointer'] for error in result['errors']}
        self.assertTrue({'/records/1/body/scope', '/records/2/body/metric/unit', '/records/3/body/value'} <= paths)
        self.assertFalse(result['valid'])

    def test_identity_collision_invalid_endpoint_and_role_are_reported(self):
        for mutate, message in (
            (lambda v: v['records'][3].update(id='X'), 'duplicate record identity'),
            (lambda v: v['records'][4]['body'].update(target_id='X'), 'invalid scientific endpoints'),
            (lambda v: v['records'][1]['body'].update(role='subclaim'), 'invalid structural parents')):
            value = fixture(); mutate(value)
            result = preview(value)
            self.assertFalse(result['valid'])
            self.assertTrue(any(message in error['error'] for error in result['errors']))

    def test_source_digest_mismatch_duplicate_json_and_nonfinite_original_refuse(self):
        value = fixture(); value['source']['sha256'] = 'a' * 64
        with self.assertRaisesRegex(ContractError, 'digest'): preview(value)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{} trailing'):
            value = fixture(); value['source'] = source_record(raw)
            with self.assertRaises(ContractError): preview(value)
        with self.assertRaises(ContractError): preview_import(b'{"schema":1,"schema":2}')

    def test_explicit_mapping_and_transformation_never_verify_source_fidelity(self):
        value = fixture(); value['records'][0]['body']['statement'] = 'Human narrowed claim'
        result = preview(value)
        self.assertFalse(result['valid'])
        value['records'][0]['mappings'][0]['transformation'] = 'Narrowed by the importing researcher; compare with original.'
        self.assertTrue(preview(value)['valid'])
        self.assertFalse(preview(value)['source_fidelity_verified'])
        value['records'][0]['mappings'][0]['source'] = '/entries/1/statement'
        self.assertFalse(preview(value)['valid'])
        value = fixture(); value['records'][2]['mappings'].pop()
        self.assertTrue(any('missing explicit source mapping' in item['error'] for item in preview(value)['errors']))

    def test_no_thesis_and_deselected_dependency_are_not_silent_pruning(self):
        value = fixture(); value['selected_ids'] = ['D']; value['records'][5]['body']['record_ids'] = []
        value['records'][5]['mappings'] = [dict(target=pointer, source='/entries/5', transformation='Synthetic source-only decision without current references') for pointer, _ in _leaves(value['records'][5]['body'])]
        self.assertFalse(preview(value)['valid'])
        value = fixture(); value['records'] = [record for record in value['records'] if record['id'] != 'O']
        result = preview(value)
        self.assertFalse(result['valid'])
        self.assertTrue(any('missing dependency: O' in item['error'] for item in result['errors']))
        value['selected_ids'] = ['T']
        self.assertTrue(preview(value)['valid'])

    def test_unicode_original_preserved_but_normalized_pointers_are_unambiguous(self):
        value = fixture(); source = json.loads(source_bytes(value['source']))
        source['entries'][0]['statement'] = 'e\u0301 연구'
        value['records'][0]['body']['statement'] = 'é 연구'
        raw = json.dumps(source, ensure_ascii=False).encode(); value['source'] = source_record(raw)
        result = preview(value)
        self.assertTrue(result['valid']); self.assertEqual(raw, source_bytes(result['source']))
        value['source'] = source_record(br'{"e\u0301":1,"\u00e9":2}')
        with self.assertRaisesRegex(ContractError, 'colliding'): preview(value)

    def test_unresolved_pointers_are_partitioned_above_generic_collection_limit(self):
        value = fixture(); source = json.loads(source_bytes(value['source']))
        source['unmapped'] = [[str(index)] for index in range(2048)]
        value['source'] = source_record(json.dumps(source).encode())
        result = preview(value)
        self.assertTrue(result['valid'])
        self.assertEqual(2051, result['unresolved_source_leaf_count'])
        self.assertTrue(all(len(page) <= 128 for page in result['unresolved_source_pointers']))
        encode(result, purpose='project')

    def test_container_summary_leaves_unsupported_children_unresolved(self):
        value = fixture(); mapping = value['records'][1]['mappings'][1]
        mapping.update(source='/entries/1', transformation='Summarized this source record.')
        result = preview(value)
        self.assertTrue(result['valid'])
        self.assertIn('/entries/1/banned_terms/0', sum(result['unresolved_source_pointers'], []))

    def test_cycle_and_per_type_capacity_fail_before_registration(self):
        value = fixture()
        value['records'].append(deepcopy(value['records'][4]))
        value['records'][-1].update(id='F')
        value['records'][-1]['body'].update(source_id='C', target_id='T')
        value['selected_ids'].append('F')
        # The claim-only scientific DAG has just one link; add the return link.
        other = deepcopy(value['records'][-1]); other.update(id='G')
        other['body'].update(source_id='T', target_id='C')
        value['records'].append(other); value['selected_ids'].append('G')
        self.assertTrue(any('cyclic' in error['error'] for error in preview(value)['errors']))
        value = fixture()
        for index in range(63):
            record = deepcopy(value['records'][1]); record.update(id='extra-' + str(index))
            record['body'].update(status='proposed', basis_ids=[])
            # Source transformation is declared for the changed status/list.
            record['mappings'] = [dict(target=pointer, source='/entries/1', transformation='Synthetic transformed field') for pointer, _ in _leaves(record['body'])]
            value['records'].append(record); value['selected_ids'].append(record['id'])
        result = preview(value)
        self.assertTrue(any('capacity claim: 64 / 63' in error['error'] for error in result['errors']))

    def test_historical_reference_and_source_depth_are_checked(self):
        value = fixture(); value['records'][5]['body']['record_ids'].append('absent')
        value['records'][5]['mappings'].append(dict(target='/record_ids/2', source='/entries/5', transformation='Synthetic missing reference'))
        self.assertTrue(any('historical reference: absent' in error['error'] for error in preview(value)['errors']))
        nested = 'x'
        for _ in range(18): nested = [nested]
        value = fixture(); value['source'] = source_record(json.dumps(nested).encode())
        with self.assertRaisesRegex(ContractError, 'nesting'): preview(value)

    def test_untrusted_kind_reports_error_instead_of_typeerror(self):
        for kind in ([], {}, None, 1):
            value = fixture(); value['records'][0]['kind'] = kind
            result = preview(value)
            self.assertFalse(result['valid'])
            self.assertTrue(any('unknown record kind' in item['error'] for item in result['errors']))

    def test_raw_source_pointer_and_leaf_growth_stop_before_amplification(self):
        for source, message in (
            ({'k' * 2049: 1}, 'pointer exceeds 2048'),
            ({'k' * 1500: [0] * 1000}, 'pointer inventory exceeds 1 MiB'),
            ([[0] * 2048 for _ in range(5)], 'leaf-pointer limit exceeds 8192')):
            value = fixture(); value['source'] = source_record(json.dumps(source).encode())
            with self.assertRaisesRegex(ContractError, message): preview(value)

    def test_many_diagnostics_remain_bounded_with_explicit_count_and_refusal(self):
        value = fixture(); value['records'] = [dict(kind='claim') for _ in range(2048)]
        result = preview(value)
        self.assertFalse(result['valid']); self.assertTrue(result['diagnostics_truncated'])
        self.assertEqual(512, len(result['errors']))
        self.assertGreater(result['error_count'], 10000)
        encode(result, purpose='project')
        value = fixture(); value['selected_ids'] = ['T', 'T']; value['extra'] = 'refused'
        result = preview(value)
        self.assertFalse(result['valid']); self.assertFalse(result['diagnostics_truncated'])
        self.assertEqual(2, result['error_count'])

    def test_selected_historical_references_are_disclosed_required_records(self):
        value = fixture(); value['selected_ids'] = ['T', 'D']
        result = preview(value)
        self.assertTrue(result['valid'])
        self.assertEqual(['C', 'E', 'O', 'X'], result['required'])
        self.assertEqual([], result['omitted'])

    def test_import_status_needs_matching_active_basis_without_determining_truth(self):
        for mutate, message in (
            (lambda v: v['records'][4]['body'].update(edge_type='challenges'), 'supported requires an explicit supports'),
            (lambda v: v['records'][1]['body'].update(status='contested'), 'contested requires an explicit challenges'),
            (lambda v: v['records'][3]['body'].update(status='retracted'), 'inactive observation')):
            value = fixture(); mutate(value)
            result = preview(value)
            self.assertFalse(result['valid'])
            self.assertTrue(any(message in item['error'] for item in result['errors']))

    def test_impossible_source_timestamp_is_not_accepted_by_pattern_alone(self):
        value = fixture(); value['records'][5]['recorded_at'] = '2026-02-31T25:61:61Z'
        result = preview(value)
        self.assertFalse(result['valid'])
        self.assertTrue(any(item['pointer'] == '/records/5/recorded_at' for item in result['errors']))

    def test_claim_to_claim_basis_is_declared_reasoning_not_inferred_observational_proof(self):
        value = fixture(); value['selected_ids'] = ['C']
        value['records'][4]['body']['source_id'] = 'T'
        value['records'][4]['mappings'][1]['transformation'] = 'Synthetic explicit thesis-to-claim reasoning.'
        result = preview(value)
        self.assertTrue(result['valid'])
        self.assertEqual(['D', 'O', 'X'], result['omitted'])
        self.assertFalse(result['source_fidelity_verified'])
        self.assertEqual(0, result['counts']['observation']['used'])


class ArgumentImportEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.path = self.root / 'argument.json'; self.path.write_bytes(encode(fixture(), purpose='project'))
        self.path.chmod(0o600)

    def run_cli(self, *extra):
        output = io.StringIO(); error = io.StringIO()
        with patch('sys.stdout', output), patch('sys.stderr', error):
            code = main(['project', 'import-argument', '--input', str(self.path), *extra])
        return code, output.getvalue(), error.getvalue()

    def test_public_dry_run_and_actual_source_entry_have_no_writes(self):
        before = self.path.read_bytes(); names = set(self.root.iterdir())
        code, output, error = self.run_cli('--dry-run', '--json')
        self.assertEqual(0, code, error); self.assertTrue(json.loads(output)['valid'])
        process = subprocess.run([sys.executable, '-m', 'claimbranch', 'project', 'import-argument',
                                  '--input', str(self.path), '--dry-run', '--json'], capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertEqual(json.loads(output), json.loads(process.stdout))
        self.assertEqual(before, self.path.read_bytes()); self.assertEqual(names, set(self.root.iterdir()))

    def test_public_plain_preview_contains_originals_and_disabled_registration_refuses(self):
        code, output, error = self.run_cli('--dry-run')
        self.assertEqual(0, code, error); self.assertIn('COMPLETE ORIGINAL JSON', output)
        self.assertIn('banned_terms', output); self.assertIn('"contributor": "unknown"', output)
        with patch('claimbranch.application.project_commands.os.open', side_effect=AssertionError('must refuse before reads')):
            code, _, error = self.run_cli()
        self.assertEqual(1, code); self.assertIn('registration is not yet available', error)

    def test_private_regular_input_required_before_preview(self):
        self.path.chmod(0o644)
        code, _, error = self.run_cli('--dry-run'); self.assertEqual(1, code)
        self.assertIn('owner-private', error)
        self.path.chmod(0o600); linked = self.root / 'link.json'; linked.symlink_to(self.path)
        self.path = linked
        self.assertEqual(1, self.run_cli('--dry-run')[0])

    def test_actual_pty_can_leave_paged_preview_without_creating_any_work(self):
        master, slave = os.openpty()
        process = subprocess.Popen([sys.executable, '-m', 'claimbranch', 'project', 'import-argument',
                                    '--input', str(self.path), '--dry-run'], stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        output = b''; deadline = time.monotonic() + 10
        try:
            while b'next page / q' not in output and time.monotonic() < deadline:
                if select.select([master], [], [], 0.2)[0]: output += os.read(master, 16384)
            self.assertIn(b'next page / q', output)
            os.write(master, b'q\n')
            self.assertEqual(0, process.wait(timeout=5))
            self.assertEqual(['argument.json'], [path.name for path in self.root.iterdir()])
        finally:
            if process.poll() is None: process.kill(); process.wait()
            os.close(master)

    def test_invalid_actual_pty_preview_still_exits_nonzero_when_leaving_pages(self):
        value = fixture(); value['records'][1]['body']['scope'] = ''
        self.path.write_bytes(encode(value, purpose='project'))
        master, slave = os.openpty()
        process = subprocess.Popen([sys.executable, '-m', 'claimbranch', 'project', 'import-argument',
                                    '--input', str(self.path), '--dry-run'], stdin=slave, stdout=slave, stderr=slave)
        os.close(slave); output = b''; deadline = time.monotonic() + 10
        try:
            while b'next page / q' not in output and time.monotonic() < deadline:
                if select.select([master], [], [], 0.2)[0]: output += os.read(master, 16384)
            self.assertIn(b'next page / q', output); os.write(master, b'q\n')
            self.assertEqual(1, process.wait(timeout=5))
        finally:
            if process.poll() is None: process.kill(); process.wait()
            os.close(master)

    def test_fresh_source_artifact_contains_public_import_preview(self):
        from scripts.build_source import build_source
        import zipfile
        archive = self.root / 'source.zip'; build_source(archive)
        extraction = self.root / 'extracted'; extraction.mkdir()
        with zipfile.ZipFile(archive) as source: source.extractall(extraction)
        env = dict(os.environ); env.pop('PYTHONPATH', None)
        result = subprocess.run([sys.executable, '-m', 'claimbranch', 'project', 'import-argument',
            '--input', str(self.path), '--dry-run', '--json'], cwd=extraction, env=env,
            capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])
        self.assertFalse(json.loads(result.stdout)['registration_available'])

    def test_pager_interrupts_are_handled_without_traceback_or_registration(self):
        class TTY(io.StringIO):
            def isatty(self): return True
        for raised, expected in ((EOFError, 1), (KeyboardInterrupt, 130)):
            output = TTY()
            with patch('sys.stdout', output), patch('sys.stdin.isatty', return_value=True), patch('builtins.input', side_effect=raised) as prompt:
                code = main(['project', 'import-argument', '--input', str(self.path), '--dry-run'])
            self.assertEqual(expected, code)
            self.assertEqual(1, prompt.call_count)
            self.assertIn('Preview interrupted; no records registered.', output.getvalue())
            self.assertEqual(['argument.json'], [path.name for path in self.root.iterdir()])


if __name__ == '__main__': unittest.main()
