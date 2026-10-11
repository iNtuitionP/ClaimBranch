"""Run a new-content offline typed proposal exercise; no personal AI enablement."""
from dataclasses import asdict
import json

from claimbranch.core.canonical import canonical_bytes, decode
from claimbranch.core.context import Destination, OfflineBroker, review_outbound
from claimbranch.core.research_history import ResearchHistory
from .paper_draft import PaperDraftSession
from .paper_service import PaperService


def _reference(key, domain='context'):
    return {'domain': domain, 'id': key}


def workflow(*, include_draft=True):
    history = ResearchHistory.start_paper('cache-study', 'episode-a', 'Synthetic cache latency study',
        'thesis', 'Caching improves latency on CPU-A and CPU-B.', 'anchor')
    def append(kind, body):
        nonlocal history
        history = history.append({'schema_version': 2, 'id': f'op-{len(history.commands)+1}',
            'project_id': 'cache-study', 'episode_id': 'episode-a', 'created_at': '2026-10-09T00:00:00Z',
            'operation_type': kind, 'expected_heads': dict(history.heads),
            'evidence_watermark': history.watermark, 'payload': body})
    metric = {'name': 'mean latency', 'definition': 'Arithmetic mean of ten elapsed times',
              'unit': 'ms', 'comparison': 'Caching versus no caching on the same CPU and workload'}
    append('record-experiment', {'id': 'run-a', 'question': 'Does caching reduce CPU-A latency?',
        'method': 'Compare ten synthetic runs with caching and ten without.',
        'conditions': 'CPU-A, fixed workload, ten runs', 'metric': metric,
        'source_ref': 'synthetic:cache-cpu-a'})
    append('record-evidence-event', {'event_id': 'event-a', 'target_id': 'obs-a', 'run_id': 'run-a',
        'action': 'confirm', 'statement': 'The CPU-A mean was 6 ms versus 15 ms without caching.',
        'value': '6', 'rationale': 'Invented fixture data, not an actual experiment.', 'supersedes_id': None})
    service = PaperService(history)
    session = PaperDraftSession(service)
    session.edit('CPU-A is faster, but can this justify the CPU-B claim?', '')
    before_science, before_writing = service.query('main')['digest'], session.state()
    request = {'schema_version': 1, 'project_id': 'cache-study', 'episode_id': 'episode-a',
        'ref': 'main', 'view_digest': service.query('main')['digest'], 'purpose': 'critique-interpretation',
        'selections': [
            {'record_id': 'thesis', 'fields': ['statement', 'role']},
            {'record_id': 'obs-a', 'fields': ['statement', 'status', 'value', 'metric', 'conditions', 'source']}],
        'scientific_edge_ids': []}
    bundle = session.compile_proposal_context(request, include_draft=include_draft)
    raw = canonical_bytes({'schema': 'claimbranch.provider-result/v2', 'status': 'ok',
        'critique': 'CPU-B is unmeasured; do not generalize the CPU-A result.', 'items': [
            {'id': 'narrow', 'action': 'create', 'kind': 'claim', 'target_id': None,
             'body': {'role': 'main', 'statement': 'Caching reduced the measured CPU-A latency from 15 to 6 ms.',
                'scope': 'CPU-A and the tested workload only', 'parent_ids': [_reference('thesis')]}},
            {'id': 'limit', 'action': 'create', 'kind': 'scientific-edge', 'target_id': None,
             'body': {'source_id': _reference('obs-a'), 'target_id': _reference('thesis'),
                'edge_type': 'qualifies', 'rationale': 'The CPU-B part remains unmeasured.'}},
            {'id': 'repeat', 'action': 'create', 'kind': 'experiment-plan', 'target_id': None,
             'body': {'claim_id': _reference('narrow', 'item'), 'objective': 'Test caching on CPU-B.',
                'status': 'planned', 'conditions': 'CPU-B, same workload and ten runs', 'metric': metric}}]})
    destination = Destination('offline://frozen', 'cache-typed-fixture-v1')
    review = review_outbound(bundle, destination, request_id='typed-example-request', nonce='typed-example-nonce', now=100,
                             result_format='typed')
    broker = OfflineBroker()
    broker.begin(bundle, destination, review, now=101, result_format='typed')
    proposal = broker.complete_typed(review.request_id, raw)
    trace = broker.sent[0]
    # The original incomplete writing stays manual and the recorded fixture is
    # unchanged. This broker exercise grants no session adoption capability.
    return {'schema': 'claimbranch.paper-typed-example/v1', 'classification': 'synthetic-offline-example',
        'input': decode(review.payload), 'include_draft': include_draft,
        'proposal': {**{key: value for key, value in asdict(proposal).items() if key != 'payload'},
                     'result': decode(proposal.payload), 'staging_available': False},
        'trace': {**{key: value for key, value in asdict(trace).items() if key != 'payload'}, 'digest': trace.digest},
        'manual_draft': session.state()['draft'], 'source_unchanged': before_science == service.query('main')['digest'],
        'manual_writing_unchanged': before_writing == session.state(),
        'authorization_verified': service.query('main')['authorization_verified'],
        'live_provider': any(dispatch.destination.remote_capable for dispatch in broker.dispatched)}


if __name__ == '__main__':
    print(json.dumps(workflow(), ensure_ascii=False, indent=2))
