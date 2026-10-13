"""Scoped typed ingress; no provider, staging, scientific writes or native keys."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.context import ContextRecord, ContextSelection, Destination, OfflineBroker, compile_context, review_outbound, provider_result
from claimbranch.core.paper_proposals import provider_typed_result, result_schema


def reference(key, domain='context'):
    return {'domain': domain, 'id': key}


def context(purpose='critique-interpretation'):
    rows = [
        ('thesis', 'claim', {'statement': 'Caching improves latency on CPU-A and CPU-B.', 'role': 'thesis'}),
        ('main', 'claim', {'statement': 'Caching improves latency on CPU-A.', 'role': 'main', 'parent_ids': ['thesis']}),
        ('obs-a', 'observation', {'statement': 'The CPU-A mean was 6 ms versus 15 ms without caching.', 'status': 'confirmed',
            'value': '6', 'conditions': 'CPU-A, fixed workload, ten runs',
            'metric': {'name': 'mean latency', 'definition': 'Arithmetic mean of ten elapsed times',
                'unit': 'ms', 'comparison': '15 ms without caching'}}),
    ]
    records = tuple(ContextRecord.create('cache-study', key, kind, 'private', fields, schema_version=2)
                    for key, kind, fields in rows)
    selection = ContextSelection('cache-study', 'episode-a', purpose,
        tuple((key, tuple(fields)) for key, _, fields in rows), schema_version=2,
        binding=canonical_bytes({'ref': 'main', 'view_digest': 'a' * 64}))
    return compile_context(records, selection)


def response():
    return {'schema': 'claimbranch.provider-result/v2', 'status': 'ok',
        'critique': 'CPU-B is unmeasured; do not generalize the CPU-A result.',
        'items': [
            {'id': 'narrow', 'action': 'create', 'kind': 'claim', 'target_id': None,
             'body': {'role': 'main', 'statement': 'Caching reduced the measured CPU-A latency from 15 to 6 ms.',
                'scope': 'CPU-A and the tested workload only', 'parent_ids': [reference('thesis')]}},
            {'id': 'limit', 'action': 'create', 'kind': 'scientific-edge', 'target_id': None,
             'body': {'source_id': reference('obs-a'), 'target_id': reference('thesis'),
                'edge_type': 'qualifies', 'rationale': 'The CPU-B part remains unmeasured.'}},
            {'id': 'repeat', 'action': 'create', 'kind': 'experiment-plan', 'target_id': None,
             'body': {'claim_id': reference('narrow', 'item'), 'objective': 'Test caching on CPU-B.',
                'status': 'planned', 'conditions': 'CPU-B, same workload and ten runs',
                'metric': {'name': 'mean latency', 'definition': 'Arithmetic mean of ten elapsed times',
                    'unit': 'ms', 'comparison': 'Caching versus no caching on CPU-B'}}},
        ]}


class TypedProposalTests(unittest.TestCase):
    def test_explicit_edit_bound_and_unrun_plan_cannot_supply_support(self):
        from claimbranch.core.paper_proposals import provider_edit_result
        value=response()
        for number in range(2):
            extra=deepcopy(value['items'][0]);extra['id']='extra-'+str(number);value['items'].append(extra)
        with self.assertRaisesRegex(ContractError,'four'):provider_edit_result(canonical_bytes(value),context())
        value=response();value['items'][1]['body']['source_id']=reference('repeat','item')
        with self.assertRaises(ContractError):provider_edit_result(canonical_bytes(value),context())

    def test_typed_response_keeps_context_refs_local_dependencies_and_no_record_ids(self):
        value = provider_typed_result(canonical_bytes(response()), context())
        self.assertEqual(response(), value)
        self.assertEqual({'domain': 'item', 'id': 'narrow'}, value['items'][2]['body']['claim_id'])
        self.assertTrue(all(item['target_id'] is None for item in value['items']))
        self.assertEqual('claimbranch.provider-result/v2', result_schema()['properties']['schema']['const'])

    def test_text_v1_and_typed_v2_are_separate_and_manuscript_stays_text_only(self):
        raw = canonical_bytes({'schema': 'claimbranch.provider-result/v1', 'status': 'ok', 'text': 'Manual text route.'})
        self.assertEqual('Manual text route.', provider_result(raw)['text'])
        with self.assertRaises(ContractError): provider_result(canonical_bytes(response()))
        with self.assertRaises(ContractError): provider_typed_result(raw, context())
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(response()), context('draft-manuscript'))
        for purpose in ('compare-evidence', 'critique-interpretation', 'plan-experiment'):
            provider_typed_result(canonical_bytes(response()), context(purpose))

    def test_unknown_fields_commands_evidence_and_forged_origin_are_rejected(self):
        variants = []
        for key, value in (('tools', ['confirm']), ('actor', 'human'), ('project_id', 'another'),
                           ('proposal_id', 'owned'), ('trace_digest', 'b' * 64)):
            variants.append(dict(response(), **{key: value}))
        for kind in ('observation', 'experiment-record', 'claim-status', 'manuscript', 'record-evidence-event'):
            value = response(); value['items'][0]['kind'] = kind; variants.append(value)
        value = response(); value['items'][2]['body']['status'] = 'recorded'; variants.append(value)
        value = response(); value['items'][2]['body']['value'] = '6'; variants.append(value)
        value = response(); value['items'][0]['body']['statement'] += '\x1b[2J'; variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(value), context())

    def test_unselected_wrong_kind_duplicate_and_unresolved_refs_refuse_the_whole_result(self):
        variants = []
        for ref in (reference('obs-hidden'), reference('obs-a', 'item'), reference('repeat', 'item'), reference('obs-a')):
            value = response(); value['items'][2]['body']['claim_id'] = ref; variants.append(value)
        value = response(); value['items'][1]['body']['source_id'] = reference('thesis'); value['items'][1]['body']['target_id'] = reference('thesis'); variants.append(value)
        value = response(); value['items'][0]['body']['parent_ids'] *= 2; variants.append(value)
        value = response(); value['items'][1]['id'] = 'narrow'; variants.append(value)
        value = response(); value['items'][0]['action'] = 'edit'; variants.append(value)
        value = response(); value['items'][0]['target_id'] = 'main'; variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(value), context())

    def test_edit_targets_preserve_selected_identity_and_cannot_edit_the_thesis(self):
        value = response(); value['items'][0].update(action='edit', target_id='main')
        decoded = provider_typed_result(canonical_bytes(value), context())
        self.assertEqual('main', decoded['items'][0]['target_id'])
        for target in ('thesis', 'obs-a', 'unselected'):
            bad = deepcopy(value); bad['items'][0]['target_id'] = target
            with self.subTest(target=target), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(bad), context())
        bad = deepcopy(value); bad['items'].append(deepcopy(bad['items'][0])); bad['items'][-1]['id'] = 'second-edit'
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(bad), context())

    def test_dependency_structural_and_scientific_cycles_are_refused(self):
        value = response()
        value['items'][0]['body'].update(role='subclaim', parent_ids=[reference('narrow', 'item')])
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())
        value = response(); value['items'] = [value['items'][1]]
        value['items'][0]['body'].update(source_id=reference('main'), target_id=reference('thesis'))
        backwards = deepcopy(value['items'][0]); backwards['id'] = 'backwards'
        backwards['body'].update(source_id=reference('thesis'), target_id=reference('main'))
        value['items'].append(backwards)
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())

    def test_empty_refusals_failures_and_limits_do_not_supply_substitute_suggestions(self):
        for status in ('refused', 'failed'):
            value = dict(response(), status=status, critique=None, items=[])
            self.assertEqual(value, provider_typed_result(canonical_bytes(value), context()))
            value['critique'] = 'Use this instead'
            with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())
        variants = [dict(response(), critique=None, items=[]), dict(response(), status='unknown')]
        value = response(); value['items'] *= 22; variants.append(value)
        value = response(); value['critique'] = '가' * 5462; variants.append(value)
        for value in variants:
            with self.subTest(status=value['status']), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(value), context())
        for raw in (b'x' * 65537, b'\xff', b'{"schema":"a","schema":"b"}', 'not bytes'):
            with self.assertRaises(ContractError): provider_typed_result(raw, context())

    def test_broker_owns_identity_consumes_one_arrival_and_records_exact_bytes(self):
        bundle = context(); destination = Destination('offline://frozen', 'cache-fixture')
        outbound = review_outbound(bundle, destination, request_id='r1', nonce='n1', now=100, result_format='typed')
        broker = OfflineBroker(); broker.begin(bundle, destination, outbound, now=101, result_format='typed')
        raw = canonical_bytes(response())
        with patch('socket.socket', side_effect=AssertionError('network')), patch('subprocess.run', side_effect=AssertionError('execution')):
            proposed = broker.complete_typed('r1', raw)
        self.assertEqual(('cache-study', 'episode-a', bundle.digest, outbound.digest),
            (proposed.project_id, proposed.episode_id, proposed.context_digest, proposed.request_digest))
        self.assertEqual(response(), decode(proposed.payload))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), broker.sent[0].response_digest)
        self.assertEqual(proposed.trace_digest, broker.sent[0].digest)
        self.assertNotIn('authorization_verified', decode(proposed.payload))
        with self.assertRaises(ContractError): broker.complete_typed('r1', raw)
        broker.erase_payload('r1')
        self.assertEqual(proposed.trace_digest, broker.sent[0].digest)

    def test_bad_typed_arrival_is_traced_and_cannot_retry_under_old_consent(self):
        bundle = context(); destination = Destination('offline://frozen', 'cache-fixture')
        for raw, expected in ((b'broken', 'malformed'),
            (canonical_bytes(dict(response(), status='refused', critique=None, items=[])), 'refused')):
            broker = OfflineBroker(); outbound = review_outbound(bundle, destination, request_id='r', nonce='n', now=100, result_format='typed')
            broker.begin(bundle, destination, outbound, now=101, result_format='typed')
            self.assertIsNone(broker.complete_typed('r', raw))
            self.assertEqual(expected, broker.sent[0].disposition)
            with self.assertRaises(ContractError): broker.complete_typed('r', canonical_bytes(response()))

    def test_selected_relation_edit_uses_the_context_kind_mapping_and_current_endpoints(self):
        bundle = context()
        record = ContextRecord.create('cache-study', 'existing-edge', 'scientific-relation', 'private',
            {'source_id': 'obs-a', 'target_id': 'thesis', 'edge_type': 'supports', 'rationale': 'Earlier broad reading.'}, schema_version=2)
        from dataclasses import replace
        bundle = compile_context((*bundle.records, record), replace(bundle.selection,
            fields=(*bundle.selection.fields, (record.id, ('source_id', 'target_id', 'edge_type', 'rationale')))))
        value = response(); value['items'][1].update(action='edit', target_id='existing-edge')
        self.assertEqual('existing-edge', provider_typed_result(canonical_bytes(value), bundle)['items'][1]['target_id'])
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())

    def test_kind_limits_and_long_dependency_paths_are_rejected_before_staging(self):
        value = response(); plan = value['items'][2]
        value['items'] = [dict(deepcopy(plan), id=f'plan-{i}') for i in range(9)]
        for item in value['items']: item['body']['claim_id'] = reference('main')
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())
        value = response(); claim = value['items'][0]
        value['items'] = [dict(deepcopy(claim), id=f'claim-{i}') for i in range(9)]
        for index, item in enumerate(value['items'][1:], 1):
            item['body'].update(role='subclaim', parent_ids=[reference(f'claim-{index-1}', 'item')])
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())

    def test_interpretation_basis_cannot_be_a_plan_or_a_proposed_observation(self):
        value = dict(response(), items=[{'id': 'reading', 'action': 'create', 'kind': 'interpretation', 'target_id': None,
            'body': {'statement': 'Only CPU-A has measured support.', 'observation_ids': [reference('obs-a')]}}])
        provider_typed_result(canonical_bytes(value), context())
        value['items'][0]['body']['observation_ids'] = []
        provider_typed_result(canonical_bytes(value), context())
        value['items'][0]['body']['observation_ids'] = [reference('main')]
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())

    def test_changed_forged_context_and_live_destination_do_not_dispatch(self):
        from dataclasses import replace
        bundle = context()
        with self.assertRaises(ContractError):
            provider_typed_result(canonical_bytes(response()), replace(bundle, digest='b' * 64))
        destination = Destination('https://example.org/v1', 'unverified')
        review = review_outbound(bundle, destination, request_id='r', nonce='n', now=100)
        broker = OfflineBroker()
        with self.assertRaises(ContractError): broker.begin(bundle, destination, review, now=101)
        self.assertEqual((), broker.dispatched)

    def test_offline_new_content_example_preserves_unfinished_manual_writing_and_science(self):
        from claimbranch.application.paper_proposal_example import workflow
        for include in (False, True):
            with self.subTest(include=include):
                example = workflow(include_draft=include)
                self.assertTrue(example['source_unchanged'])
                self.assertFalse(example['live_provider'])
                self.assertTrue(example['manual_writing_unchanged'])
                self.assertEqual('', example['manual_draft']['rationale'])
                self.assertFalse(example['manual_draft']['ai_influenced'])
                records = example['input']['context']['records']
                self.assertEqual(include, any(row['kind'] == 'draft' for row in records))
                self.assertEqual({'thesis', 'obs-a'}, {row['id'] for row in records if row['kind'] != 'draft'})
                self.assertEqual('planned', example['proposal']['result']['items'][2]['body']['status'])
                self.assertNotIn('value', example['proposal']['result']['items'][2]['body'])

    def test_context_read_does_not_replace_consent_or_require_a_complete_judgment(self):
        from claimbranch.application.paper_draft import PaperDraftSession
        from claimbranch.application.paper_service import PaperService
        from tests.application.test_paper_context import selection
        from tests.contract.test_paper_history import paper
        history, _ = paper(); service = PaperService(history)
        session = PaperDraftSession(service, ref='alternative', frozen_response='Existing text caller.')
        session.edit('Still considering this result.', '')
        before = session.prepare_request(selection(service))
        for include in (False, True):
            bundle = session.compile_proposal_context(selection(service), include_draft=include)
            self.assertEqual(include, any(row['kind'] == 'draft' for row in decode(bundle.payload)['records']))
            self.assertEqual(before, session.state())
        with self.assertRaises(ContractError): session.compile_proposal_context(selection(service), include_draft=1)

    def test_wrong_completion_route_preserves_dispatch_for_its_correct_reader(self):
        bundle = context(); destination = Destination('offline://frozen', 'fixture')
        broker = OfflineBroker(); review = review_outbound(bundle, destination, request_id='text', nonce='t', now=100)
        broker.begin(bundle, destination, review, now=101)
        with self.assertRaises(ContractError): broker.complete_typed('text', canonical_bytes(response()))
        self.assertEqual((), broker.sent)
        text = canonical_bytes({'schema': 'claimbranch.provider-result/v1', 'status': 'ok', 'text': 'Text-only response.'})
        self.assertEqual('Text-only response.', broker.complete('text', text).text)
        typed = review_outbound(bundle, destination, request_id='typed', nonce='y', now=100, result_format='typed')
        with self.assertRaises(ContractError): broker.begin(bundle, destination, typed, now=101)
        broker.begin(bundle, destination, typed, now=101, result_format='typed')
        with self.assertRaises(ContractError): broker.complete('typed', text)
        proposed = broker.complete_typed('typed', canonical_bytes(response()))
        from claimbranch.core.review import Judgment
        with self.assertRaises(ContractError): Judgment.start('cache-study', 'episode-a').use_proposal(proposed)
        self.assertEqual('claimbranch.provider-result/v2', decode(typed.payload)['result_schema'])

    def test_context_references_cannot_hide_a_proposed_edit_dependency(self):
        for kind in ('parent', 'plan', 'edge'):
            value = response(); value['items'][0].update(action='edit', target_id='main')
            if kind == 'parent':
                value['items'].append({'id': 'child', 'action': 'create', 'kind': 'claim', 'target_id': None,
                    'body': {'role': 'subclaim', 'statement': 'A narrower condition.', 'scope': 'CPU-A',
                        'parent_ids': [reference('main'), reference('narrow', 'item')]}})
            elif kind == 'plan': value['items'][2]['body']['claim_id'] = reference('main')
            else: value['items'][1]['body']['target_id'] = reference('main')
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(value), context())

    def test_example_checks_live_owner_state_rather_than_its_original_immutable_history(self):
        from claimbranch.application.paper_draft import PaperDraftSession
        from claimbranch.application.paper_proposal_example import workflow
        original = PaperDraftSession.compile_proposal_context
        def changing_reader(owner, *args, **kwargs):
            bundle = original(owner, *args, **kwargs)
            owner.edit('A change during reading.', '')
            return bundle
        with patch.object(PaperDraftSession, 'compile_proposal_context', changing_reader):
            self.assertFalse(workflow()['manual_writing_unchanged'])

    def test_typed_review_rejects_text_context_or_manuscript_before_using_consent(self):
        destination = Destination('offline://frozen', 'fixture')
        with self.assertRaises(ContractError):
            review_outbound(context('draft-manuscript'), destination, request_id='r', nonce='n', now=100, result_format='typed')
        legacy = compile_context((ContextRecord.create('p', 'c', 'claim', 'private', {'statement': 'A claim.'}),),
            ContextSelection('p', 'e', 'critique-interpretation', (('c', ('statement',)),)))
        with self.assertRaises(ContractError):
            review_outbound(legacy, destination, request_id='r', nonce='n', now=100, result_format='typed')
        bundle = context(); broker = OfflineBroker()
        review = review_outbound(bundle, destination, request_id='r', nonce='n', now=100)
        broker.begin(bundle, destination, review, now=101)
        self.assertIsNone(broker.complete('r', canonical_bytes(response())))
        self.assertEqual('malformed', broker.sent[0].disposition)

    def test_current_interpretation_and_unrun_plan_edits_are_bound_to_selected_status_and_origin(self):
        from dataclasses import replace
        bundle = context()
        rows = [('reading', 'interpretation', {'statement': 'An earlier reading.', 'episode_id': 'episode-a'}),
                ('planned', 'experiment-plan', {'status': 'planned', 'claim_id': 'main'})]
        records = tuple(ContextRecord.create('cache-study', key, kind, 'private', fields, schema_version=2)
                        for key, kind, fields in rows)
        bundle = compile_context((*bundle.records, *records), replace(bundle.selection,
            fields=(*bundle.selection.fields, *((key, tuple(fields)) for key, _, fields in rows))))
        value = dict(response(), items=[{'id': 'revise-reading', 'action': 'edit', 'kind': 'interpretation', 'target_id': 'reading',
            'body': {'statement': 'The measurement covers CPU-A only.', 'observation_ids': [reference('obs-a')]}}])
        provider_typed_result(canonical_bytes(value), bundle)
        old = ContextRecord.create('cache-study', 'reading', 'interpretation', 'private',
            {'statement': 'Historical reading.', 'episode_id': 'earlier-episode'}, schema_version=2)
        previous = compile_context(tuple(old if row.id == 'reading' else row for row in bundle.records), bundle.selection)
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), previous)
        value = response(); value['items'] = [value['items'][2]]
        value['items'][0].update(action='edit', target_id='planned')
        value['items'][0]['body']['claim_id'] = reference('main')
        provider_typed_result(canonical_bytes(value), bundle)
        with self.assertRaises(ContractError):
            ContextRecord.create('cache-study', 'planned', 'experiment-plan', 'private',
                {'status': 'recorded', 'claim_id': 'main'}, schema_version=2)

    def test_selected_scientific_path_and_new_reverse_edge_form_a_rejected_cycle(self):
        from dataclasses import replace
        bundle = context()
        relation = ContextRecord.create('cache-study', 'old-path', 'scientific-relation', 'private',
            {'source_id': 'main', 'target_id': 'thesis', 'edge_type': 'supports', 'rationale': 'A recorded relation.'}, schema_version=2)
        bundle = compile_context((*bundle.records, relation), replace(bundle.selection,
            fields=(*bundle.selection.fields, (relation.id, ('source_id', 'target_id', 'edge_type', 'rationale')))))
        value = response(); value['items'] = [value['items'][1]]
        value['items'][0]['body'].update(source_id=reference('thesis'), target_id=reference('main'))
        with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), bundle)

    def test_exact_kind_and_response_boundaries_include_normalized_only_overflow(self):
        from claimbranch.core.research_schema import normalize
        for kind, maximum, template in (('claim', 15, response()['items'][0]),
            ('scientific-edge', 32, response()['items'][1]), ('experiment-plan', 8, response()['items'][2]),
            ('interpretation', 1, {'id': 'reading', 'action': 'create', 'kind': 'interpretation', 'target_id': None,
                'body': {'statement': 'CPU-A only.', 'observation_ids': [reference('obs-a')]}})):
            value = dict(response(), items=[dict(deepcopy(template), id=f'item-{i}') for i in range(maximum)])
            if kind == 'experiment-plan':
                for item in value['items']: item['body']['claim_id'] = reference('main')
            with self.subTest(kind=kind):
                provider_typed_result(canonical_bytes(value), context())
                value['items'].append(dict(deepcopy(value['items'][0]), id='one-extra'))
                with self.assertRaises(ContractError): provider_typed_result(canonical_bytes(value), context())
        # Isolate the envelope's absolute item cap; runtime identity/kind limits
        # are intentionally stricter than this shape-only boundary.
        shaped = dict(response(), items=response()['items'][:1] * 64)
        normalize(shaped, result_schema())
        shaped['items'].append(shaped['items'][0])
        with self.assertRaises(ContractError): normalize(shaped, result_schema())
        value = response(); expanded = '\u0344' * 4000
        value['critique'] = expanded
        for key in ('statement', 'scope'): value['items'][0]['body'][key] = expanded
        for key in ('objective', 'conditions'): value['items'][2]['body'][key] = expanded
        import json
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.assertLess(len(raw), 65536)
        self.assertGreater(len(canonical_bytes(decode(raw))), 65536)
        with self.assertRaises(ContractError): provider_typed_result(raw, context())

    def test_directional_display_controls_are_rejected_without_banning_joined_script_text(self):
        for char in ('\u202e', '\u2066', '\u200e', '\u2028', '\u2029'):
            value = dict(response(), critique='Before' + char + 'after')
            with self.subTest(char=repr(char)), self.assertRaises(ContractError):
                provider_typed_result(canonical_bytes(value), context())
        value = dict(response(), critique='한글 👩\u200d🔬 می\u200cدانم\nCPU-B remains unmeasured.')
        self.assertEqual(value, provider_typed_result(canonical_bytes(value), context()))


if __name__ == '__main__':
    unittest.main()
