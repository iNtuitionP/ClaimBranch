"""Authored display copy for the frozen synthetic example, never new research.

Match the complete source statement, not a node ID: edited/new content falls
back to a visibly clipped source excerpt. The reader always uses the source.
These compact captions are not a general summarizer or persisted node titles.
"""

CAPTIONS = {
    ('claim', 'On a fixed synthetic 2000-example split, pruning 20 percent of Model A weights or quantizing them to 8 bits loses at most 1 percentage point of accuracy against unchanged Model A.'):
        ('20%prune /8bit', 'loss ≤ 1 pp'),
    ('claim', 'On the fixed synthetic split, Model A loses less accuracy with 20 percent weight pruning than with 8-bit weight quantization: 0.4 versus 0.7 percentage points.'):
        ('Prune vs 8-bit', '0.4 vs 0.7 pp'),
    ('claim', 'Pruning 20 percent of Model A weights with mask seed 42 stays within 1 percentage point of unchanged accuracy on the fixed synthetic split.'):
        ('prune seed 42', 'loss ≤ 1 pp'),
    ('claim', 'With pruning-mask seed 42, removing 20 percent of Model A weights causes 8 fewer correct classifications out of 2000, an accuracy loss of 0.4 percentage points.'):
        ('20% pruning', '8 fewer / 2000'),
    ('observation', 'Pruning 20 percent of Model A weights with mask seed 42 lost 0.4 percentage points of accuracy against unchanged Model A on the fixed synthetic 2000-example split.'):
        ('20% pruning', 'loss 0.4 pp'),
    ('observation', 'Quantizing Model A weights to 8 bits lost 0.7 percentage points of accuracy against unchanged Model A on the fixed synthetic 2000-example split.'):
        ('8-bit quantize', 'loss 0.7 pp'),
    ('experiment-plan', 'Does pruning 20 percent of Model A weights with mask seed 43 still lose at most 1 percentage point of accuracy?'):
        ('prune seed 43', 'loss ≤ 1 pp?'),
    ('experiment-record', 'Do 20 percent weight pruning and 8-bit weight quantization keep Model A within 1 percentage point of its unchanged accuracy?'):
        ('Prune / 8-bit', 'accuracy test'),
    ('interpretation', 'The recorded 20 percent weight pruning and 8-bit weight quantization of Model A each lost less than 1 percentage point of accuracy on the fixed synthetic split; another pruning seed remains untested.'):
        ('Each loss <1pp', 'new seed unrun'),
}


def overview_copy(app, node_id):
    node = app.nodes[node_id]
    content = node['content']
    if content.get('title'):return None
    if node['kind'] == 'manuscript-anchor':
        target = content.get('claim_id')
        return (f'To {app.node_label(target)} · paper' if target in app.nodes else 'Manuscript link',
                'Applied' if content.get('applied') else 'Not applied')
    result = CAPTIONS.get((node['kind'], app.title(node_id)))
    if result and node['kind'] == 'observation':
        # A changed value/metric must not retain a frozen measurement caption.
        unit = content['metric']['unit']
        if unit != 'percentage points' or content['metric']['name'] != 'classification accuracy loss':
            return None
        result = (result[0], f"loss {content['value']} pp")
    return result
