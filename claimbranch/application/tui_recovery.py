"""Opt-in, private UI drafts. This is not a research-history writer or backup."""
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile


class DraftRecovery:
    def __init__(self, path, app):
        requested = Path(path).expanduser().absolute()
        self.path = requested.parent.resolve() / requested.name
        self.lock = None
        self.previous = None
        if any((parent / '.git').exists() for parent in self.path.parents):
            raise ValueError('Keep draft recovery outside Git working trees.')
        if requested.is_symlink():
            raise ValueError('Draft recovery cannot be a symbolic link.')
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = self.path.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
            raise ValueError('Use an owned directory without group/other write access.')
        self.history = app.history_digest
        self.version = 2 if app.series else 1
        self.key_size = 3 if app.series else 2
        contexts = [(item['id'], ref) for item in app.service.episodes()['episodes']
                    for ref in ('main', 'alternative')] if app.series else [(ref,) for ref in ('main', 'alternative')]
        self.allowed = {key: {node['id'] for node in app.service.query(
            key[-1], episode_id=key[0] if app.series else None)['nodes']} for key in contexts}
        try:
            self.lock = self._open(self.path.with_suffix(self.path.suffix + '.lock'), create=True)
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('This draft file is already open in another session.') from None
            if self.path.exists() or self.path.is_symlink():
                descriptor = self._open(self.path)
                with os.fdopen(descriptor, 'r', encoding='utf-8') as file:
                    raw = file.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise ValueError('Draft recovery file exceeds its size limit.')
                try:
                    data = json.loads(raw)
                except (RecursionError, ValueError):
                    raise ValueError('Malformed draft file; preserve it and choose another path.') from None
                self.restore(app, data)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _open(path, *, create=False):
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0), 0o600)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                info.st_nlink != 1 or info.st_mode & 0o077):
            os.close(descriptor)
            raise ValueError('Draft files must be owned, private regular files (mode 600).')
        return descriptor

    def restore(self, app, data):
        if (not isinstance(data, dict) or data.get('version') != self.version or data.get('history') != self.history or
                set(data) != {'version', 'history', 'notes', 'drafts', 'unfinished', 'selection'}):
            raise ValueError('Draft file is invalid or belongs to a different synthetic history.')
        restored = {}
        for name, fields in (('notes', 1), ('drafts', 2), ('unfinished', None)):
            entries = data[name]
            if not isinstance(entries, list) or len(entries) > sum(map(len, self.allowed.values())) * 2:
                raise ValueError('Invalid draft entries.')
            values = {}
            for entry in entries:
                if not isinstance(entry, list) or len(entry) != self.key_size + (2 if name == 'unfinished' else 1):
                    raise ValueError('Invalid draft entry.')
                context, node = tuple(entry[:self.key_size - 1]), entry[self.key_size - 1]
                if (not all(isinstance(value, str) for value in (*context, node)) or
                        context not in self.allowed or node not in self.allowed[context]):
                    raise ValueError('Unknown draft branch or node.')
                count = fields
                if name == 'unfinished':
                    if entry[-2] not in ('note', 'edit'):
                        raise ValueError('Unknown editing mode.')
                    count = 1 if entry[-2] == 'note' else 2
                texts = entry[-1]
                if not isinstance(texts, list) or len(texts) != count or any(
                        not isinstance(t, str) or len(t) > 12000 for t in texts):
                    raise ValueError('Invalid draft text.')
                key = tuple(entry[:-1])
                if key in values:
                    raise ValueError('Duplicate draft entry.')
                values[key] = (texts[0] if name == 'notes' else
                               dict(zip(('text', 'rationale'), texts)) if name == 'drafts' else texts)
            restored[name] = values
        selection = data['selection']
        if (not isinstance(selection, list) or len(selection) != self.key_size or
                not all(isinstance(value, str) for value in selection) or
                tuple(selection[:-1]) not in self.allowed or selection[-1] not in self.allowed[tuple(selection[:-1])]):
            raise ValueError('Invalid draft selection.')
        # Validate the whole file before changing even the in-memory projection.
        for name, values in restored.items():
            setattr(app, name, values)
        app.open_context_key(selection)
        app.message = 'Private drafts restored. N resumes note editing; E resumes judgment. Nothing accepted.'

    def save(self, app, active=None):
        unfinished = {key: value for key, value in app.unfinished.items()
                      if key[-1] != 'edit' or not app.review.influenced(key[:-1])}
        if active and active[0] == 'edit' and app.review.influenced():
            active = None
        if active:
            mode, texts = active
            unfinished[(*app.writing_key(mode), mode)] = texts
        data = {'version': self.version, 'history': self.history,
                'notes': [[*key, [value]] for key, value in sorted(app.notes.items())],
                'drafts': [[*key, [value['text'], value['rationale']]] for key, value in sorted(app.drafts.items())],
                'unfinished': [[*key, value] for key, value in sorted(unfinished.items())],
                'selection': list(app.context_key())}
        serialized = json.dumps(data, ensure_ascii=False, sort_keys=True)
        if serialized == self.previous:
            return
        if len(serialized) > 8_000_000:
            raise ValueError('Draft recovery exceeds its size limit.')
        if self.path.exists() or self.path.is_symlink():
            os.close(self._open(self.path))
        descriptor, temporary = tempfile.mkstemp(prefix='.draft-', dir=self.path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
                file.write(serialized)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            self.previous = serialized
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def close(self):
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None
