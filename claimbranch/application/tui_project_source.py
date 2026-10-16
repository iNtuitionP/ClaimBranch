"""Explicit source-association controls; scientific writing keeps its old basis."""
from .tui_retention import recovery_copy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import unicodedata

from claimbranch.core.canonical import ContractError, decode
from .project_work import ASSOCIATION_LIMIT, AssociationPreview, ProjectWork, SourceRefreshReview, preview_association, preview_source_refresh
from .tui_project import ProjectRecovery, source_notice
from .tui_model import wrap


@dataclass(frozen=True)
class SourceChange:
    original: bytes
    project: ProjectWork
    preview: AssociationPreview
    review: SourceRefreshReview | None
    before: dict
    after: dict
    kind: str


def prepare_source_change(project, directory, kind, *, paper_root=None, manuscript=None):
    before = project.source_location()
    if kind not in ('relocate', 'refresh'):
        raise ContractError('Choose relocation or source refresh.')
    if kind == 'refresh':
        paper_root, manuscript = before['paper_root'], before['manuscript']
    elif not paper_root or not Path(paper_root).is_absolute() or not manuscript:
        raise ContractError('Enter an absolute paper Git root and a relative manuscript path.')
    preview = preview_association(paper_root, manuscript, before['anchor_id'], directory,selector=before.get('selector'))
    review = preview_source_refresh(project, preview) if kind == 'refresh' else None
    candidate = project.refresh_source(review) if review else project.relocate(preview)
    return SourceChange(project.payload, candidate, preview, review, before, candidate.source_location(), kind)


def apply_source_change(app, change):
    recovery = app.recovery
    if not isinstance(recovery, ProjectRecovery) or recovery.project.payload != change.original:
        raise ContractError('Saved writing changed. Return and prepare another source preview.')
    change.preview.recheck()
    # The exact nested work must be the work saved before the preview.
    recovery.save(app)
    if recovery.project.payload != change.original:
        raise ContractError('Writing changed. Return and prepare another source preview.')
    if change.review:
        change.review.recheck(recovery.project)
        recovery.store.save(change.project, source_review=change.review)
    else:
        recovery.store.save(change.project, preview=change.preview)
    recovery.project = change.project
    app.project_source_status = change.project.source_status()
    app.project_source_notice = source_notice(app.project_source_status)
    app.project_source_checked = True
    app.message = 'Paper connection updated. Writing and its earlier source basis are retained.'


def quoted(value):
    # Escapes remain visible even when the regular terminal renderer cleans text.
    text = json.dumps(str(value), ensure_ascii=False)
    return ''.join(json.dumps(c, ensure_ascii=True)[1:-1] if (unicodedata.category(c).startswith('C') or
                   unicodedata.category(c) in ('Zl', 'Zp') or (unicodedata.category(c) == 'Zs' and c != ' ')) else c
                   for c in text)


def input_width(width):
    return min(100, width - 6)


class ProjectSourceUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.scroll = 0
        self.notice = ''
        self.change = None
        self.seen_end = False

    @property
    def app(self):
        return self.terminal.app

    def open(self):
        if not isinstance(self.app.recovery, ProjectRecovery):
            raise ContractError('Open a selected project with demo project open to manage its paper connection.')
        self.app.recovery.save(self.app)
        self.location = self.app.recovery.project.source_location()
        self.app.project_source_status = self.app.recovery.project.source_status()
        self.app.project_source_notice = self.status = source_notice(self.app.project_source_status)
        self.app.project_source_checked = True
        self.notice, self.scroll, self.change = '', 0, None
        self.terminal.modal = 'project-source'

    def preview(self, kind):
        self.app.recovery.save(self.app)
        root, manuscript = (b.text for b in self.paths) if kind == 'relocate' else (None, None)
        self.change = prepare_source_change(self.app.recovery.project, self.app.recovery.store._path,
                                           kind, paper_root=root, manuscript=manuscript)
        self.scroll, self.seen_end, self.notice = 0, False, ''
        self.flush_on_paint = True
        self.terminal.modal = 'project-source-preview'

    def dispatch(self, event):
        try:
            self.key(event)
        except (ContractError, OSError, ValueError) as error:
            self.notice = 'Connection change not confirmed: ' + str(error)
            # A failed/uncertain apply cannot be retried with this old preview.
            if self.terminal.modal == 'project-source-preview':
                self.change = None

    def key(self, event):
        mode = self.terminal.modal
        if event == 'escape':
            if mode == 'project-source':
                self.terminal.modal = None
            else:
                self.terminal.modal = 'project-source'
                self.change, self.scroll, self.notice = None, 0, ''
            return
        height, width = self.terminal.screen.getmaxyx()
        if width < 48 or height < 18:
            return
        if mode == 'project-source-location':
            if event in ('tab', 'backtab'):
                self.field = 1 - self.field
            elif event == 'enter':
                self.preview('relocate')
            else:
                self.paths[self.field].key(event, input_width(width))
            return
        if event in ('up', 'down', 'page-up', 'page-down', 'home', 'end'):
            self.scroll = (0 if event == 'home' else 100000 if event == 'end' else
                           max(0, self.scroll + {'up': -1, 'down': 1, 'page-up': -10, 'page-down': 10}[event]))
            return
        if mode == 'project-source':
            if event == 'r':
                self.paths = [exact_path_buffer(''), exact_path_buffer(str(self.location['manuscript']))]
                self.field, self.notice = 0, ''
                self.terminal.modal = 'project-source-location'
            elif event == 'f':
                self.preview('refresh')
            elif event == 'c':
                self.open()
        elif mode == 'project-source-preview' and event == 'a':
            if self.change is None:
                self.notice = 'Return with Esc and prepare another preview.'
            elif not self.seen_end:
                self.notice = 'Read the full preview with PgDn/End before applying.'
            else:
                apply_source_change(self.app, self.change)
                self.location = self.change.after
                self.status = self.app.project_source_notice
                self.change, self.scroll = None, 0
                self.terminal.modal = 'project-source'
                self.notice = 'Connection saved. Earlier writing basis retained.'

    def content(self):
        mode = self.terminal.modal
        if mode == 'project-source-preview' and self.change:
            change = self.change
            rows = [('RELOCATE / same exact source bytes' if change.kind == 'relocate' else
                     'REFRESH / changed bytes at the saved location'), '', 'BEFORE']
            for label, field in (('Paper', 'paper_root'), ('Manuscript', 'manuscript'), ('SHA-256', 'source_digest')):
                rows.append(label + ': ' + quoted(change.before[field]))
            rows += ['', 'AFTER']
            for label, field in (('Paper', 'paper_root'), ('Manuscript', 'manuscript'), ('SHA-256', 'source_digest')):
                rows.append(label + ': ' + quoted(change.after[field]))
            rows += ['', recovery_copy(self.terminal.app, 'Only the encrypted paper connection changes.'),
                     'Notes, judgments, drafts and their earlier source basis stay unchanged.',
                     'No manuscript write, evidence confirmation or renewed review authority.']
            if change.kind == 'refresh' and decode(change.original)['schema'] == 'claimbranch.project-work/v1':
                rows += ['Older v1-only project readers cannot open this updated connection.']
            elif decode(change.project.payload)['schema'] == 'claimbranch.project-work/v3':
                rows += ['This connection requires a v3 project reader; v1/v2 readers cannot reopen it.']
            rows += ['Source changes remaining after this: ' + str(ASSOCIATION_LIMIT - len(decode(change.project.payload)['associations']))]
            return rows
        if mode == 'project-source-preview':
            return ['This preview is no longer usable.', 'Esc returns to the connection. Prepare a fresh preview.']
        return [recovery_copy(self.terminal.app, 'SYNTHETIC / saved writing remains unaccepted'), '',
                'Paper: ' + quoted(self.location['paper_root']),
                'Manuscript: ' + quoted(self.location['manuscript']),
                'Marker: ' + self.location['anchor_id'], '', 'SOURCE CHECK: ' + self.status, '',
                'r  Relocate the same source to a new paper location',
                'f  Refresh changed source at the saved location',
                'c  Check source status again', '',
                'Moved AND edited files are not supported in one change.',
                'Existing writing keeps its earlier source basis. No file is edited.']

    def draw(self, frame):
        from .tui import Frame
        frame = Frame(frame.width, frame.height)
        w, h = frame.width, frame.height
        if w < 48 or h < 18:
            frame.put(1, 1, 'Paper connection paused', 'top_warning', w - 2)
            frame.put(3, 1, 'Resize to 48 x 18. Esc returns.', 'top_muted', w - 2)
            return frame
        measure, x = input_width(w), 3
        if self.terminal.modal == 'project-source-preview' and getattr(self, 'flush_on_paint', False):
            if hasattr(self.terminal, 'curses'):
                self.terminal.curses.flushinp()
            if hasattr(self.terminal, 'pending'):
                self.terminal.pending.clear()
            self.flush_on_paint = False
        frame.put(0, x, 'PAPER CONNECTION', 'brand', measure)
        if self.terminal.modal == 'project-source-location':
            frame.put(2, x, 'New location / same source bytes and marker', 'top_accent', measure)
            frame.put(3, x, 'Exact paths; no shell quotes or escaping.', 'top_muted', measure)
            for index, label in enumerate(('Paper Git root (absolute path)', 'Manuscript (relative .tex path)')):
                buffer = self.paths[index]
                frame.put(4 + index * 5, x, ('> ' if index == self.field else '  ') + label, 'heading', measure)
                lines, cursor_row, cursor_column = buffer.position(measure)
                offset = max(0, cursor_row - 2) if index == self.field else 0
                for row, (line, _, _) in enumerate(lines[offset:offset + 3]):
                    frame.put(5 + index * 5 + row, x, line, 'accent' if index == self.field else 'body', measure)
                if index == self.field:
                    frame.cursor = 5 + index * 5 + cursor_row - offset, min(w - 4, x + cursor_column)
            notice = self.paths[self.field].notice or self.notice
            keys = 'Tab field · Enter preview · Esc cancel'
            frame.put(h - 1, x, 'Paths are session-only. Pasted controls are rejected.', 'top_muted', measure)
        else:
            lines = [line for item in self.content() for line in (wrap(item, measure) or [''])]
            visible = h - 7
            self.scroll = min(self.scroll, max(0, len(lines) - visible))
            for row, line in enumerate(lines[self.scroll:self.scroll + visible]):
                frame.put(2 + row, x, line, 'body', measure)
            if self.terminal.modal == 'project-source-preview' and self.scroll + visible >= len(lines):
                self.seen_end = True
            notice = self.notice
            keys = (('a apply connection · Esc cancel' if self.seen_end and self.change else
                     'PgDn/End read preview · Esc cancel') if self.terminal.modal == 'project-source-preview' else
                    'r relocate · f refresh · c check · Esc')
            frame.put(h - 1, x, f'{self.scroll + 1}-{min(len(lines), self.scroll + visible)}/{len(lines)} · PgUp/PgDn', 'top_muted', measure)
        for row, line in enumerate(wrap(notice, measure)[:2]):
            frame.put(h - 4 + row, x, line, 'top_warning', measure)
        frame.put(h - 2, x, keys, 'top_accent', measure)
        return frame


def exact_path_buffer(text):
    from .tui import Buffer
    class PathBuffer(Buffer):
        def __init__(self, text):
            super().__init__('')
            self.text, self.initial, self.cursor = text, text, len(text)

        def insert(self, value):
            # Scientific prose normalizes Unicode; filesystem paths must not.
            bidi = '\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'
            if any(unicodedata.category(c) in ('Cc', 'Cs', 'Zl', 'Zp') or c in bidi for c in value):
                self.notice = 'Path input contains controls; nothing was inserted.'
                return
            if len(os.fsencode(self.text + value)) > 4096:
                self.notice = 'Path exceeds 4096 bytes; nothing was inserted.'
                return
            self.checkpoint()
            self.text = self.text[:self.cursor] + value + self.text[self.cursor:]
            self.cursor += len(value)
            self.notice = ''

        def key(self, event, width):
            if isinstance(event, str) and len(event) == 1 and unicodedata.category(event) == 'Cf':
                self.insert(event)
            else:
                super().key(event, width)
    return PathBuffer(text)


def project_source_ui(terminal):
    if not hasattr(terminal, '_project_source_ui'):
        terminal._project_source_ui = ProjectSourceUI(terminal)
    return terminal._project_source_ui
