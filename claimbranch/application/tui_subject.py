"""Read-only, recorded subject context shared by Work and judgment editing."""
from .tui_model import clip, wrap


def subject_sections(app):
    node = app.nodes[app.selected_id]
    content, kind = node['content'], node['kind']
    label = {'observation': 'RECORDED OBSERVATION', 'claim': 'CLAIM',
             'experiment-plan': 'EXPERIMENT PLAN', 'experiment-record': 'RECORDED RUN',
             'interpretation': 'INTERPRETATION', 'manuscript-anchor': 'MANUSCRIPT CONNECTION'}[kind]
    status = content.get('status')
    heading = label + ' / ' + app.node_label(app.selected_id) + (' · ' + status if status else '')
    statement = (content.get('statement') or content.get('objective') or content.get('question')
                 or 'No recorded subject text available.')
    sections = [('SUBJECT', statement, 'body')]
    metric = content.get('metric') or {}
    if kind == 'observation':
        value = content.get('value')
        sections.append(('Recorded value', (str(value) + ' ' + metric.get('unit', '')
                         + ' · ' + metric.get('name', '')) if value is not None
                         else 'No current recorded value.', 'evidence'))
    if kind == 'experiment-plan':
        sections.append(('Plan', str(status or 'status unavailable') + ' · not a measured result', 'plan'))
    if content.get('conditions'):
        sections.append(('Conditions', content['conditions'], 'muted'))
    if content.get('scope'):
        sections.append(('Scope', content['scope'], 'muted'))
    for label, key in (('Method', 'method'),):
        if content.get(key):
            sections.append((label, content[key], 'body'))
    for label, key in (('Measurement', 'name'), ('Definition', 'definition'), ('Comparison', 'comparison')):
        if metric.get(key):
            sections.append((label, metric[key], 'body'))
    sections.append(('Source reference (not opened)', content.get('source_ref')
                     or 'No artifact reference on this node.', 'muted'))
    links = [link for link in app.links() if link.scientific]
    if not links:
        sections.append(('Connections', 'No scientific connections recorded.', 'muted'))
    for link in links:
        direction = link.kind + ' → ' if link.outgoing else '← ' + link.kind + ' '
        sections.append((direction + app.node_label(link.target_id), app.title(link.target_id), link.kind))
        if link.rationale:
            sections.append(('Relation reason', link.rationale, 'muted'))
    return heading, sections


def subject_summary(app, width):
    heading, sections = subject_sections(app)
    result = [(clip(heading, width), 'heading')]
    statement = wrap(sections[0][1], width)
    if len(statement) > 2:
        statement[1] = clip(statement[1], width - 1, ellipsis=False).rstrip() + '…'
    result.extend((line, 'body') for line in statement[:2])
    context = [item for item in sections if item[0] in ('Recorded value', 'Plan', 'Conditions', 'Scope')]
    for label, value, style in context[:2]:
        result.append((clip(label + ': ' + value, width), style))
    return result


def subject_lines(app, width):
    heading, sections = subject_sections(app)
    rows = [(line, 'heading') for line in wrap(heading, width)]
    for label, value, style in sections:
        rows.append(('', 'body'))
        if label != 'SUBJECT':
            rows.extend((line, 'heading') for line in wrap(label, width))
        rows.extend((line, style) for line in wrap(value, width))
    return rows
