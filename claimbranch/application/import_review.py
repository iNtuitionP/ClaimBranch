"""Private import review projection; never changes the scientific preview."""
from collections import Counter
import json
import os
import sys
import textwrap
import shutil
import hashlib
from claimbranch.core.paper_capacity import encode

from claimbranch.core.paper_capacity import source_bytes, PROJECT_BYTES
from .tui_model import clean


def _short(value, limit=160):
    text = clean(str(value)).replace('\n', ' ')
    return text if len(text) <= limit else text[:limit] + ' [open detail]'


def unresolved_items(result):
    """Complete address inventory, independently of display pagination."""
    for record in result.get('records', []):
        for item in record.get('coverage', []):
            if item['state'] in ('transformed', 'declared-without-source','not-recorded'):
                yield dict(record_id=record['id'], **item)
        if record.get('replacement') is not None:
            yield dict(record_id=record['id'],state='declared-without-source',target='/replacement',record_metadata=True,normalized=record['replacement'])
    for page in result.get('unresolved_source_pointers', []):
        for pointer in page:
            yield dict(state='unmapped-source', source_pointer=pointer)


def summary_lines(result, preflight=None):
    records = result.get('records', [])
    origins = Counter()
    declarations = Counter()
    for record in records:
        origin = record.get('effective_origin') or record.get('origin', {})
        origins[origin.get('contributor', 'unknown')] += 1
        if origin.get('unknown') or origin.get('contributor') == 'unknown':
            declarations[origin.get('declaration', 'record')] += 1
    unresolved = Counter(item['state'] for item in unresolved_items(result))
    lines = ['PRIOR ARGUMENT / private personal registration review',
        'Historical source claims; extraction equality is not scientific validity or understanding.',
        'No manuscript writes, protected approval, or records registered by this preview.',
        'Valid: %s / errors: %s' % (result['valid'], result.get('error_count', 0)),
        'Title: ' + _short(result.get('title', '(unavailable)')),
        'Selection: %s explicit / %s required / %s omitted' % tuple(len(result.get(k, [])) for k in ('selected', 'required', 'omitted')),
        'Records by kind: ' + _short(dict(Counter(r['kind'] for r in records))),
        'Origins: ' + str(dict(origins)),
        'Unknown-origin declarations: ' + str(dict(declarations)),
        'Coverage: ' + str(result.get('coverage', dict(mapped=result.get('mapped_source_leaf_count', 0)))),
        'Unresolved: %s / categories: %s (all addresses: unresolved)' % (sum(unresolved.values()), dict(unresolved)),
        'Envelope SHA-256: ' + result.get('envelope_sha256', '(unavailable)'),
        'Preview digest (not consent): ' + result.get('preview_digest', '(unavailable)')]
    if 'replacement_links' in result:lines.append('Explicit replacement links: %s / status effect: none; inspect records or unresolved' % len(result['replacement_links']))
    for kind, budget in result.get('counts', {}).items():
        lines.append('Capacity %s: %s / %s' % (kind, budget['used'], budget['limit']))
    for name, budget in result.get('budgets', {}).items():
        lines.append('Budget %s: %s / %s' % (name, budget['used'], budget['limit']))
    for file in result.get('files', []):
        lines.append('Source %s: %s bytes / SHA-256 %s' % (file['id'], file['source']['bytes'], file['source']['sha256']))
    if 'source' in result:
        lines.append('Source original: %s bytes / SHA-256 %s' % (result['source']['bytes'], result['source']['sha256']))
    if 'registration_failure' in result:
        lines.append('Seed preparation refused: ' + _short(result['registration_failure']))
    if preflight is None:
        lines.append('Full preflight: NOT RUN (seed validation only; supply --dry-run --preflight and project options).')
    else:
        lines += ['Full preflight: passed / no destination reserved',
            'Destination: ' + _short(preflight['destination']),
            'Prepared at (not commit time): ' + preflight['prepared_at'],
            'First local question: ' + _short(preflight['first_local_question']),
            'Representation: ' + preflight['representation'],
            'Project bytes: %s / %s; archive bytes: %s / %s' % (preflight['saved_bytes'], PROJECT_BYTES, preflight['archive_bytes'], preflight['archive_limit']),
            'Result SHA-256: ' + preflight['result_sha256'],
            'Source status: ' + preflight['source_status']]
        for kind, budget in preflight['capacity']['resources'].items():
            lines.append('Saved capacity %s: %s / %s' % (kind, budget['used'], budget['limit']))
        if preflight['audit_encoding_review'] is not None:
            lines.append('Shared audit: explicit lossless shared-values/v1; adds one command, preserves prior science/prefix.')
    lines.append('Details: selection | records | record ID | graph | sources | source ID | unresolved | item N | errors | capacity')
    return [clean(line) for line in lines]


class ReviewInput:
    """Read directly from a TTY, without Python/readline read-ahead across phases.

    Each prompt discards queued input; emitted bracketed-paste markers are rejected. This is a
    personal foreground control, not an OS identity or presence guarantee.
    """
    def __enter__(self):
        import termios
        import tty
        self.fd = sys.stdin.fileno()
        self.original = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd, termios.TCSAFLUSH)
        print('\x1b[?2004h', end='', flush=True)
        return self

    def __exit__(self, *_):
        import termios
        try:
            termios.tcsetattr(self.fd, termios.TCSANOW, self.original)
            termios.tcflush(self.fd, termios.TCIFLUSH)
        finally:
            print('\x1b[?2004l', end='', flush=True)

    def __call__(self, prompt):
        import select
        import termios
        termios.tcflush(self.fd, termios.TCIFLUSH)
        print(prompt, end='', flush=True)
        value = bytearray()
        rejected = False
        while True:
            char = os.read(self.fd, 1)
            if char in (b'', b'\x04'):
                raise EOFError
            if char == b'\x1b' and not select.select([self.fd],[],[],0.05)[0]:
                termios.tcflush(self.fd,termios.TCIFLUSH);print(flush=True);return '\x1b'
            if char == b'\x03':
                raise KeyboardInterrupt
            if char in (b'\r', b'\n'):
                # A second queued line cannot become the next prompt's answer.
                queued = bool(select.select([self.fd], [], [], 0)[0])
                termios.tcflush(self.fd, termios.TCIFLUSH)
                print(flush=True)
                return '[queued or pasted input rejected]' if rejected or queued else value.decode('utf-8', errors='replace')
            if char in (b'\x7f', b'\x08'):
                if value:
                    value.pop()
                    print('\b \b', end='', flush=True)
            elif char < b' ' or len(value) >= 4096:
                rejected = True
            else:
                value.extend(char)
                # Commands/IDs are ASCII; UTF-8 remains intact for exact lookup.
                if char.isascii():
                    print(char.decode('ascii'), end='', flush=True)


def _pages(lines, read, *, pause_at_end=False):
    width = max(20, min(100, shutil.get_terminal_size().columns - 1))
    lines = [part for line in lines for part in (textwrap.wrap(clean(str(line)), width=width, replace_whitespace=False, drop_whitespace=False) or [''])]
    for start in range(0, len(lines), 40):
        print('\n'.join(clean(str(line)) for line in lines[start:start + 40]), flush=True)
        if start + 40 < len(lines) or pause_at_end:
            prompt='Enter: next detail page / q: back to summary: ' if start+40<len(lines) else 'Enter/q/Escape: back to summary: '
            if read(prompt).strip().lower() in ('q','\x1b'):
                return


def review(result, preflight=None, *, read, registration=False):
    """Return true only after a separate transition and a fresh exact import."""
    records = {r['id']: r for r in result.get('records', [])}
    files = {f['id']: f['source'] for f in result.get('files', [])}
    if 'source' in result:
        files['original'] = result['source']
    items = list(unresolved_items(result))
    while True:
        print('\n'.join(summary_lines(result, preflight)), flush=True)
        command = read('Review: details / continue to confirmation / cancel: ' if registration else 'Review: details / q: leave preview: ').strip()
        if command == 'cancel' or (not registration and command == 'q'):
            return False
        if command == 'continue' and registration:
            answer = read('Type import to register this exact selection; Enter: back to summary / cancel: ')
            if answer == 'import':
                return True
            if answer == 'cancel':
                return False
            continue
        name, _, key = command.partition(' ')
        value = None
        if command == 'selection':
            value = {k: result.get(k, []) for k in ('selected', 'required', 'omitted')}
        elif command == 'records':
            value = [dict(id=r['id'], kind=r['kind'], title=_short(r['body'].get('statement', r['body'].get('question', r['body'].get('rationale', ''))))) for r in records.values()]
        elif name == 'record' and key in records:
            value = {k: v for k, v in records[key].items() if k != 'mappings' or 'coverage' not in records[key]}
        elif command == 'graph':
            value = [dict(id=r['id'], kind=r['kind'], body=r['body']) for r in records.values() if r['kind'] in ('thesis', 'claim', 'scientific-edge', 'experiment-plan')]
        elif command == 'sources':
            value = [dict(id=k, bytes=v['bytes'], sha256=v['sha256']) for k, v in files.items()]
        elif name == 'source' and key in files:
            try:
                original = source_bytes(files[key]).decode('utf-8')
            except UnicodeError:
                print('Source is not UTF-8; use the retained raw source in private JSON output.', flush=True)
                continue
            _pages(original.splitlines(), read)
            continue
        elif command == 'unresolved':
            value = [dict(index=i + 1, **{k: v for k, v in item.items() if k not in ('original', 'normalized')}) for i, item in enumerate(items)]
        elif name == 'item' and key.isascii() and key.isdigit() and 1 <= int(key) <= len(items):
            item = items[int(key) - 1]
            value = dict(item)
            if 'record_id' in item:
                from claimbranch.core.argument_import import _at
                value['target_value'] = _at(records[item['record_id']] if item.get('record_metadata') else records[item['record_id']]['body'], item['target'])
            elif 'source_pointer' in item and 'original' in files:
                from claimbranch.core.argument_import import _original, _at
                from claimbranch.core.argument_import_v2 import _display
                original, _ = _original(source_bytes(files['original']))
                value['original'] = _display(_at(original, item['source_pointer']))
                value['reason'] = 'Retained original leaf without an identity-covered scientific mapping.'
        elif command == 'errors':
            value = {k: result.get(k) for k in ('errors', 'error_count', 'diagnostics_truncated')}
        elif command == 'capacity':
            value = preflight or dict(counts=result.get('counts'), budgets=result.get('budgets'), full_preflight='not run')
        if value is not None:
            _pages(json.dumps(value, ensure_ascii=False, indent=2).splitlines(), read)
        elif command:
            print('Unknown command; use the named details or cancel.', flush=True)


def operation_summary(preview):
    """Bounded orientation; complete operations/graphs remain independently readable."""
    entries=preview.get('entries')
    operations=[dict(id=e['id'],kind=e['kind'],operation=e['review'].get('operation',{})) for e in entries] if entries is not None else [dict(id=preview.get('operation',{}).get('id','operation'),kind=preview.get('operation',{}).get('operation_type','metadata'),operation=preview.get('operation',{}))]
    lines=['PERSONAL METADATA REVIEW / exact candidate; no manuscript writes',
        'Reading does not establish understanding. Confirmation records only this candidate.',
        'Operations: '+str(len(operations))+' / kinds: '+_short(dict(Counter(o['kind'] for o in operations))),
        'Selected: '+str(len(preview.get('selected_ids',operations)))+' / omitted: '+str(len(preview.get('omitted_ids',[]))),
        'Input SHA-256: '+preview.get('input_digest','bound to the selected private input'),
        'Candidate review SHA-256: '+hashlib.sha256(encode(dict(operations=[o['operation'] for o in operations],source=preview.get('project_digest'),input=preview.get('input_digest')),purpose='project')).hexdigest()]
    for phase in ('before','after'):
        graph=preview.get(phase) or {}
        if 'nodes' in graph:lines.append(phase.title()+' graph: '+str(len(graph['nodes']))+' nodes / '+str(len(graph.get('relations',[])))+' connections')
        else:lines.append(phase.title()+' metadata: '+('available in details' if graph else 'none'))
    lines.append('Operation list (full text: entries / entry ID / operation):')
    for operation in operations[:20]:
        payload=operation['operation'].get('payload',{})
        subjects=[str(payload[k]) for k in ('claim_id','anchor_id','target_id','experiment_id','protocol_id') if k in payload]
        if not subjects and 'id' in payload:subjects=[str(payload['id'])]
        lines.append(_short(operation['id']+' / '+operation['kind']+' / '+', '.join(subjects)))
        reason=payload.get('rationale',payload.get('judgment',{}).get('rationale'))
        if reason:lines.append('Reason: '+_short(reason))
    if len(operations)>20:lines.append(str(len(operations)-20)+' more operations available in entries')
    lines.append('Diagnostics: '+str(len(preview.get('errors',[])))+' errors; '+str(len(preview.get('lint',{}).get('warnings',[])))+' wording warnings / '+str(sum(bool(w.get('acknowledgement_ids')) for w in preview.get('lint',{}).get('warnings',[])))+' acknowledged (all: lint/errors)')
    lines.append('Details: entries | entry ID | operation | before | after | impact | context | lint | errors | selection | full')
    return [clean(line) for line in lines]


def review_operation(preview,word,*,read):
    entries={entry['id']:entry for entry in preview.get('entries',[])}
    while True:
        print('\n'.join(operation_summary(preview)),flush=True)
        command=read('Review: details / continue to confirmation / cancel: ').strip()
        if command in ('','q','cancel','\x1b'):return False
        if command=='continue':
            answer=read('Type '+word+' to save this exact candidate; Enter: back to summary / cancel: ')
            if answer==word:return True
            if answer in ('cancel','q'):return False
            continue
        name,_,key=command.partition(' ');value=None
        if command=='entries':value=[dict(id=e['id'],kind=e['kind'],origin=e.get('origin')) for e in entries.values()]
        elif name=='entry' and key in entries:value=entries[key]
        elif command=='selection':value={key:preview.get(key,[]) for key in ('selected_ids','omitted_ids')}
        elif command=='full':value={key:value for key,value in preview.items() if key!='project_digest'}
        elif command in ('operation','before','after','impact','context','lint','errors'):
            value=preview[command] if command in preview else [dict(entry_id=e['id'],value=e['review'][command]) for e in entries.values() if command in e['review']]
        if value is not None:_pages(json.dumps(value,ensure_ascii=False,indent=2).splitlines(),read,pause_at_end=True)
        elif command:print('Choose a named detail or continue/cancel.',flush=True)


def confirm_operation(preview,word):
    try:
        with ReviewInput() as read:return review_operation(preview,word,read=read)
    except EOFError:return False
