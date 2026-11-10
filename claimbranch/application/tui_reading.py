"""One disposable, lazily wrapped reader per workspace; never saved science."""
from .tui_model import wrap, clip


class Reading:
    def __init__(self, content, width, *, relation=False):
        self.rows = []
        self.done = False
        self.pending = self._rows(content, width, relation)

    @staticmethod
    def _rows(content, width, relation):
        for index, (text, style) in enumerate(content):
            if index == 1 and style == 'body':
                style = 'lead'
            preview = not relation and style in ('supports','challenges','qualifies','inconclusive') and any(text.startswith(kind + ' → ') for kind in
                          ('supports', 'challenges', 'qualifies', 'inconclusive'))
            if style == 'table':
                from .tui_model import clean
                yield clean(text), 'body'
                continue
            if preview:
                yield clip(text, width), style
                continue
            for paragraph in text.split('\n'):
                for line in wrap(paragraph, width):
                    yield line, style

    def ensure(self, count=None):
        while not self.done and (count is None or len(self.rows) < count):
            try:
                self.rows.append(next(self.pending))
            except StopIteration:
                self.done = True

    def clamp(self, offset, visible):
        self.ensure(max(0, offset) + visible + 1)
        return max(0, min(offset, max(0, len(self.rows) - visible)))


def reader(app, width):
    relation = app.reading_relation and app.mode == 'detail'
    node = app.nodes[app.selected_id]
    # Queries replace the projection at each scientific revision. Local notes
    # are separate; manuscript freshness and volatile review views are uncached.
    key = (app.graph_revision, app.episode_id, app.selected_id,
           app.ref, app.mode, app.reading_relation, app.link_index, app.link_scope, width,
           app.note(), bool(app.recovery), getattr(app.recovery, 'personal_project', False))
    cached = getattr(app, '_reading', None)
    cacheable = app.mode in ('detail', 'raw') and node['kind'] != 'manuscript-anchor'
    if cacheable and cached and cached[0] == key:
        return cached[1]
    content = app.relationship_detail() if relation else app.detail(include_links=False, width=width)
    result = Reading(content, width, relation=relation)
    app._reading = (key if cacheable else None, result)
    app._reading_context = (app.episode_id, app.ref, app.selected_id, app.mode, relation, app.link_index, width)
    return result


def scroll(app, amount=0, *, end=False, home=False):
    width, visible = getattr(app, '_reader_size', (66, 15))
    # Volatile/freshness views are rebuilt at paint, not once per queued wheel.
    cached = getattr(app, '_reading', None)
    context = (app.episode_id, app.ref, app.selected_id, app.mode, app.reading_relation and app.mode == 'detail', app.link_index, width)
    document = cached[1] if cached and cached[0] is None and getattr(app, '_reading_context', None) == context else reader(app, width)
    before = app.scroll
    if end:
        document.ensure()
        app.scroll = max(0, len(document.rows) - visible)
    else:
        app.scroll = document.clamp(0 if home else app.scroll + amount, visible)
    return before != app.scroll
