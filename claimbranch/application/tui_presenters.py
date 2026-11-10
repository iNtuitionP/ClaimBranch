"""Read-only scientific presentation. Exact source/audit remains an explicit view."""
import base64


def label(key):
    text = str(key).replace('_', ' ').replace('-', ' ')
    return text if str(key) in ('AI', 'H/A/U') else text[:1].upper() + text[1:]


def scalar(value):
    if value is None: return 'Not recorded'
    if value is True: return 'Yes'
    if value is False: return 'No'
    if value == '': return '(empty string)'
    return str(value)  # Decimal strings remain strings, including trailing zeros.


def fields(value, prefix=''):
    """Fallback covers new metadata fields without guessing their meaning."""
    if isinstance(value, dict):
        if not value: yield prefix + 'None recorded', 'muted'
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                yield prefix + label(key), 'heading'
                yield from fields(item, prefix + '  ')
            else:
                shown = '(whole JSON document)' if key == 'json_pointer' and item == '' else scalar(item)
                yield prefix + label(key) + ': ' + shown, 'body'
    elif isinstance(value, list):
        if not value: yield prefix + 'None recorded', 'muted'
        for i, item in enumerate(value, 1):
            if isinstance(item, (dict, list)):
                yield prefix + str(i) + '.', 'muted'
                yield from fields(item, prefix + '  ')
            else:
                yield prefix + '• ' + scalar(item), 'body'
    else:
        yield prefix + scalar(value), 'body'


def cell_value(cell):
    value = cell['value']
    if value['type'] == 'missing': return 'Missing: ' + value['reason']
    if value['type'] == 'text': return 'Text: ' + value['value']
    return scalar(value['value'])


def conditions(values):
    return ' · '.join(str(v['key']) + '=' + str(v['value']) for v in values) or 'None recorded'


def measurement(table, width):
    from .tui_model import cell_width
    columns = {c['id']: c for c in table['columns']}
    yield f"EXACT MEASUREMENT TABLE / {table['id']} / {len(table['rows'])} rows × {len(columns)} columns", 'heading'
    yield 'Estimand: ' + scalar(table.get('estimand')), 'body'
    yield 'Conditions: ' + conditions(table.get('conditions', [])), 'body'
    for col in columns.values():
        yield (f"{col['name']} / {col['id']} · {col['type']} · raw unit: {col['raw_unit']}"
               + (' · display label: ' + col['display_unit'] if col.get('display_unit') else '')), 'muted'
    # A row's exact values never disappear through clipping. Narrow or unusually
    # long values use the same row-detail form instead of a partial wide table.
    headers = {key: col['name'] + ' [' + key + '; ' + col['raw_unit'] + ']' for key, col in columns.items()}
    widths = {key: cell_width(headers[key]) for key in columns}
    row_width = max([3, *(cell_width(row['id']) for row in table['rows'])])
    for row in table['rows']:
        for cell in row['cells']:
            widths[cell['column_id']] = max(widths[cell['column_id']], cell_width(cell_value(cell)))
    wide = (row_width + sum(widths.values()) + 3 * len(columns) <= width
            and all(text.isprintable() and '│' not in text for text in headers.values())
            and all(c['value']['type'] != 'text' and cell_value(c).isprintable() and '│' not in cell_value(c)
                    for row in table['rows'] for c in row['cells']))
    def padded(text, count): return text + ' ' * max(0, count - cell_width(text))
    if wide:
        yield padded('Row', row_width) + ' │ ' + ' │ '.join(padded(headers[key], widths[key]) for key, c in columns.items()), 'table'
    for row in table['rows']:
        if wide:
            cells = {c['column_id']: c for c in row['cells']}
            yield padded(row['id'], row_width) + ' │ ' + ' │ '.join(
                padded(cell_value(cells[key]), widths[key]) if key in cells else padded('Not recorded', widths[key])
                for key in columns), 'table'
        else:
            yield 'ROW / ' + row['id'], 'heading'
            for cell in row['cells']:
                col = columns[cell['column_id']]
                yield col['name'] + ' [' + col['id'] + ']: ' + cell_value(cell) + (' ' + col['raw_unit'] if cell['value']['type'] in ('decimal', 'integer') else ''), 'body'
                yield 'Cell ' + cell['id'] + ' · ' + cell['value']['type'], 'muted'
        if row.get('conditions'): yield '  ' + conditions(row['conditions']), 'muted'
    yield 'ARTIFACT REFERENCES / declared, not opened or verified', 'heading'
    yield from fields(table.get('artifact_refs', []))
    yield 'Original record / audit in ; actions shows cell identities and retained history.', 'muted'


BASE_FIELDS = {'id', 'title', 'statement', 'objective', 'question', 'conditions',
               'metric', 'value', 'scope', 'method', 'source_ref', 'display_label',
               'not_recorded', 'experiment_not_recorded'}
AUDIT_FIELDS = {'history', 'graph_revisions', 'original_statement'}
CAPTIONS = {
    'graph_revisions': 'RECORDED REVISIONS / FRESH REVIEW REQUIRED',
    'companion_dependencies': 'REPORTING COMPANIONS / NOT SCIENTIFIC SUPPORT',
    'historical_decisions': 'HISTORICAL SOURCE DECISIONS / NOT LOCAL EPISODES',
    'co_report': 'CO-REPORTED / SHARED REASON AND ORIGINS',
    'metadata_contributions': 'DECLARED CONTENT ORIGIN / CONFIRMING ACTOR IS SEPARATE',
    'wording_policy': 'HUMAN WORDING LIMITS / SEPARATE FROM CLAIM STATUS',
    'replacement_context': 'RESULT REPLACEMENTS / STATUS UNCHANGED',
}



def metadata(app, width):
    """All non-base content is presented or explicitly reachable in audit."""
    content = app.nodes[app.selected_id]['content']
    if app.nodes[app.selected_id]['kind'] == 'critique-question':
        yield 'SOURCED RESEARCH QUESTION / NOT EMPIRICAL EVIDENCE', 'warning'
        yield 'Associated work proves neither motivation nor resolution.', 'warning'
        yield 'Private original excluded here; project critique-original reads it locally. No confidentiality or anonymity is implied.', 'muted'
    if content.get('measurement'):
        yield '', 'body'
        yield from measurement(content['measurement'], width)
    if content.get('imported_source'):
        source = content['imported_source']
        yield 'IMPORTED SOURCE / ' + source['contributor'].upper(), 'heading'
        yield 'Source-claimed authorship/date; no prior app approval. ' + ('Recorded at: ' + source['recorded_at'] if source.get('recorded_at') else 'Original date unknown.'), 'warning'
        if source.get('origin_flags'):
            yield 'RETAINED SOURCE INFLUENCE', 'warning'
            yield ', '.join(key.upper() for key, present in source['origin_flags'].items() if present) + '. Authorship uncertainty is retained independently of known contribution.', 'warning'
        for key, value in source.items():
            if key in ('original_body', 'contributor', 'recorded_at', 'origin_flags'): continue
            if key == 'unresolved_pointer_pages':
                paths = [p for page in value for p in page]
                yield f'UNRESOLVED SOURCE FIELDS / {len(paths)}', 'warning'
                for path in paths: yield path or '(whole source record)', 'warning'
            else:
                yield from fields({key: value})
        yield 'Original mapped content and retained ledger: ; actions → Original record / audit.', 'muted'
    if content.get('protocol_context'):
        yield 'REGISTERED RULES / original results and amendments', 'heading'
        yield 'Chronology is source-claimed or unknown; record order does not prove results were unseen.', 'warning'
        yield from fields(content['protocol_context'])
    for key, value in content.items():
        if key in BASE_FIELDS or key in ('measurement', 'imported_source', 'protocol_context'): continue
        if key in CAPTIONS: yield CAPTIONS[key], 'warning'
        if key in AUDIT_FIELDS:
            count = len(value) if isinstance(value, list) else 1
            yield label(key) + f': {count} retained · ; actions → Original record / audit', 'muted'
        elif key == 'block':
            from .manuscript_anchors import inspect_anchor
            yield 'REGISTERED MANUSCRIPT / READ ONLY', 'heading'
            yield b''.join(base64.b64decode(part) for part in value).decode('utf-8'), 'body'
            yield 'SOURCE FRESHNESS / NOT SCIENTIFIC FIDELITY', 'heading'
            yield from fields(inspect_anchor(content))
        else:
            if key not in CAPTIONS: yield label(key).upper(), 'heading'
            yield from fields(value)
        yield '', 'body'
