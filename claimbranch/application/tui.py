"""Actual-terminal prototype; no listener, browser, provider or accepted writes."""
from collections import deque
import locale
import os
import signal
import sys
import time

from claimbranch.core.canonical import ContractError
from .tui_model import TerminalWorkspace, cell_width, char_width, clean, clip, wrap
from .tui_graph import graph, graph_scene, move_graph
from .tui_work_recovery import enabled as encrypted_judgments, excluded_work, save_failure_message
from .tui_retention import recovery_copy, personal


class Frame:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.cells = [[(" ", "canvas") for _ in range(width)] for _ in range(height)]
        self.cursor = None

    def put(self, y, x, text, style="body", width=None):
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return
        limit = min(self.width - x, width if width is not None else self.width - x)
        visible = text if len(text) == 1 and text.isprintable() and char_width(text) <= limit else clip(text, limit)
        for char in visible:
            size = char_width(char)
            if not size:
                if x > 0:
                    previous = x - 1
                    if not self.cells[y][previous][0] and previous > 0:
                        previous -= 1
                    old, attr = self.cells[y][previous]
                    self.cells[y][previous] = (old + char, attr)
                continue
            self.cells[y][x] = (char, style)
            if size == 2:
                self.cells[y][x + 1] = ("", style)
            x += size

    def fill(self, y, x, width, style):
        if 0 <= y < self.height:
            start, end = max(0, x), min(self.width, x + max(0, width))
            if end > start:
                self.cells[y][start:end] = [(" ", style)] * (end - start)

    def box(self, x, y, width, height, title, focused=False):
        for row in range(y, y + height):
            self.fill(row, x, width, "body")
        style = "accent" if focused else "border"
        self.put(y, x, "┌" + "─" * (width - 2) + "┐", style)
        self.put(y + height - 1, x, "└" + "─" * (width - 2) + "┘", style)
        for row in range(y + 1, y + height - 1):
            self.put(row, x, "│", style)
            self.put(row, x + width - 1, "│", style)
        self.put(y, x + 2, " " + title + " ", style, width - 4)

    def panel(self, x, y, width, height, title, focused):
        for row in range(y, y + height):
            self.fill(row, x, width, "body")
        # Keep the gray surface around its content, including the footer.
        # Give short/narrow terminals their reading room back on resize.
        pad_x = 2 if self.width >= 100 and width >= 34 else 0
        pad_y = 1 if self.height >= 36 else 0
        x, y = x + pad_x, y + pad_y
        width, height = width - 2 * pad_x, height - 2 * pad_y
        self.put(y, x + 2, f"{'▸' if focused else ' '} {title}",
                 "accent" if focused else "heading", width - 4)
        self.put(y + 1, x + 2, "─" * (width - 4), "border")
        return x, y, width, height

    def plain(self):
        return "\n".join("".join(char for char, _ in row) for row in self.cells)


def panes(app, width, height):
    margin = 3 if width >= 100 else 1
    gap = 3 if width >= 100 else 2
    y = 5 if height >= 36 else 3
    h = height - y - (5 if height >= 36 else 3)
    available = width - 2 * margin
    if app.navigation == "graph":
        if (app.focus == "outline" and (not app.graph_pinned or app.graph_fullscreen)) or width < 140:
            return [(app.focus, margin, y, available, h)]
        right = min(72, max(56, available * 2 // 5))
        left = available - gap - right
        return [("outline", margin, y, left, h),
                ("links" if app.focus == "links" else "detail", margin + left + gap, y, right, h)]
    if width < 76:
        return [(app.focus, margin, y, available, h)]
    if app.layout == "three" and width >= 118:
        left, middle = min(42, width // 4), min(38, width // 4 - 1)
        return [("outline", margin, y, left, h),
                ("links", margin + left + gap, y, middle, h),
                ("detail", margin + left + middle + 2 * gap, y,
                 available - left - middle - 2 * gap, h)]
    left = min(62, max(27, width * 43 // 100))
    return [("outline", margin, y, left, h),
            ("links" if app.focus == "links" else "detail", margin + left + gap, y,
             available - left - gap, h)]


def node_style(app, node_id):
    return {"claim": "claim", "observation": "evidence", "experiment-plan": "plan",
            "experiment-record": "run", "interpretation": "interpretation",
            "manuscript-anchor": "writing"}[app.nodes[node_id]["kind"]]


def excerpt(text, width, count):
    lines = wrap(text, width)
    if len(lines) > count:
        lines[count - 1] = clip(lines[count - 1], width - 1, ellipsis=False).rstrip() + "…"
    return lines[:count]


def edge_segments(row):
    segments = []
    for edge in row.edges:
        if segments:
            segments.append((" · ", "muted"))
        direction = "↑" if edge["source_id"] == row.node_id else "↓"
        segments.append((direction + " " + edge["type"], edge["type"] if edge["scientific"] else "muted"))
    return segments


def outline(frame, app, x, y, width, height):
    if app.navigation == "graph":
        graph(frame, app, x, y, width, height)
        return
    title = "EVIDENCE USES" if app.lens == "evidence" else "ARGUMENT"
    x, y, width, height = frame.panel(x, y, width, height, title, app.focus == "outline")
    frame.put(y + 2, x + 2, "↑ to parent · ↓ from parent", "muted", width - 4)
    lines, selected_start, selected_end = [], 0, 0
    rows = app.rows()
    roomy = app.density == "comfortable"
    last_child = {row.path[:-1]: row.path for row in rows if row.depth}
    visible_parents = set(last_child)
    for index, row in enumerate(rows):
        key, start = row.node_id, len(lines)
        chosen = row.path == app.selected_path
        same_evidence = (not chosen and key == app.selected_id and app.nodes[key]["kind"] == "observation")
        # Keep enough text measure at deep/narrow paths; the header and reader
        # still expose the whole selected path and exact recorded endpoints.
        depth_limit = max(1, (width - 26) // 3)
        ancestors = ["│  " if last_child.get(row.path[:level]) != row.path[:level + 1] else "   "
                     for level in range(1, row.depth)]
        if len(ancestors) >= depth_limit:
            ancestors = ["…  "] + ancestors[-(depth_limit - 1):] if depth_limit > 1 else ["…  "]
        trunk = "".join(ancestors)
        last = last_child.get(row.path[:-1]) == row.path
        branch = trunk + ("└─ " if last else "├─ ") if row.depth else ""
        body_prefix = "  " + trunk + ("   " if last else "│  ") if row.depth else "  "
        toggle = "↪ " if row.reference else ("▾ " if row.path in visible_parents else "▸ ") if app.children(key) else ""
        meta = toggle + app.marker(key) + app.kind(key)
        if app.nodes[key]["kind"] == "observation":
            meta += " " + app.evidence_label(key)
        elif app.occurrences[key] > 1:
            meta += " [same]" if row.reference else " [shared]"
        if row.unlinked and not row.depth:
            meta = "UNLINKED / " + meta
        style = "warning" if app.marker(key) == "~ " else node_style(app, key)
        prefix = [("› " if chosen else "↔ " if same_evidence else "  ",
                   "selected_meta" if chosen else "evidence" if same_evidence else "muted"), (branch, "border")]
        edges = edge_segments(row)
        kind_segment = (meta, "selected_meta" if chosen else style)
        combined = prefix + edges + ([("  ", "body")] if edges else []) + [kind_segment]
        if cell_width("".join(text for text, _ in combined)) <= width - 4:
            lines.append((combined, chosen))
        else:
            # Never drop an edge type to make a badge fit. Each type may wrap;
            # full endpoints and rationale remain reachable with Enter.
            edge_width = max(6, width - 4 - cell_width(body_prefix))
            for edge_index, (label, edge_style) in enumerate(segment for segment in edges if segment[0] != " · "):
                for part_index, part in enumerate(wrap(label, edge_width)):
                    leader = prefix if edge_index == 0 and part_index == 0 else [(body_prefix, "border")]
                    lines.append((leader + [(part, edge_style)], chosen))
            for part_index, part in enumerate(wrap(meta, edge_width)):
                leader = prefix if not edges and part_index == 0 else [(body_prefix, "border")]
                lines.append((leader + [(part, kind_segment[1])], chosen))
        measure = max(6, width - 4 - cell_width(body_prefix))
        for line in excerpt(app.title(key), measure, (3 if chosen else 2) if roomy else 1):
            lines.append(([(body_prefix, "border"), (line, "selected" if chosen else "body")], chosen))
        if app.note(key).strip():
            lines.append(([(body_prefix, "border"),
                           (clip("✎ " + app.note(key), measure), "selected_meta" if chosen else "accent")], chosen))
        if chosen:
            selected_start, selected_end = start, len(lines)
        if roomy:
            lines.append(([(body_prefix, "border")], False))
    visible = height - 5
    if selected_start < app.nav_scroll:
        app.nav_scroll = selected_start
    if selected_end > app.nav_scroll + visible:
        app.nav_scroll = selected_end - visible
    app.nav_scroll = max(0, min(app.nav_scroll, max(0, len(lines) - visible)))
    if not lines:
        lines = [([("No matching nodes.", "muted")], False), ([("Esc clears the search.", "muted")], False)]
    for index, (segments, chosen) in enumerate(lines[app.nav_scroll:app.nav_scroll + visible]):
        if chosen:
            frame.fill(y + 3 + index, x + 1, width - 2, "selected")
        column = x + 2
        for text, style in segments:
            remaining = x + width - 2 - column
            if remaining <= 0:
                break
            frame.put(y + 3 + index, column, text, "selected" if chosen and style == "border" else style, remaining)
            column += cell_width(clip(text, remaining))
    selected = next((i + 1 for i, row in enumerate(rows) if row.path == app.selected_path), 0)
    more = " ↓" if app.nav_scroll + visible < len(lines) else ""
    frame.put(y + height - 1, x + 2, f"{selected} / {len(rows)} positions{more}  ·  {len(app.nodes)} nodes", "muted", width - 4)


def relationships(frame, app, x, y, width, height):
    title = "CLAIM USES" if app.link_scope == "uses" else "RELATIONS"
    x, y, width, height = frame.panel(x, y, width, height, title, app.focus == "links")
    links = app.display_links()
    app.link_index = max(0, min(app.link_index, len(links) - 1))
    lines, end = [], 0
    for index, link in enumerate(links):
        chosen = index == app.link_index and (app.focus == "links" or app.reading_relation)
        label = ((link.kind + " → ") if link.outgoing else ("← " + link.kind + " ")) + app.node_label(link.target_id)
        if link.draft:
            label += ' / DRAFT'
        lines.append((("› " if chosen else "  ") + label,
                      "selected_meta" if chosen else link.kind if link.scientific else "muted", chosen))
        for line in excerpt(app.caption(link.target_id), width - 6, 2 if app.density == "comfortable" else 1):
            lines.append(("  " + line, "selected" if chosen else "body", chosen))
        if index == app.link_index:
            end = len(lines)
        if app.density == "comfortable":
            lines.append(("", "body", False))
    visible = height - 5
    offset = max(0, end - visible)
    if not links:
        lines = [("No direct claim uses." if app.link_scope == "uses" else "No related nodes.", "muted", False),
                 ("r shows all connections.", "muted", False)]
    for index, (text, style, chosen) in enumerate(lines[offset:offset + visible]):
        if chosen:
            frame.fill(y + index + 3, x + 1, width - 2, "selected")
        frame.put(y + index + 3, x + 2, text, style, width - 4)
    frame.put(y + height - 1, x + 2, f"{app.link_index + 1 if links else 0} / {len(links)}   Enter follow", "muted", width - 4)


def inspector(frame, app, x, y, width, height):
    title = {"detail": "READ", "draft": "YOUR JUDGMENT", "impact": "WHAT IF",
             "writing": "WRITING", "provenance": "CONTRIBUTIONS", "work": "WORK / REVIEW"}[app.mode]
    relation = app.reading_relation and app.mode == "detail"
    x, y, width, height = frame.panel(
        x, y, width, height, "CONNECTION" if relation else title, app.focus == "detail")
    measure = min(72, width - 6)
    inset = max(3, (width - measure) // 2)
    content = app.relationship_detail() if relation else app.detail(include_links=False, width=measure)
    lines = []
    for index, (text, style) in enumerate(content):
        if style == "heading":
            style = node_style(app, app.selected_id) if index == 0 and app.mode == "detail" and not relation else "heading"
        elif index == 1 and style == "body":
            style = "lead"
        preview = (not relation and any(text.startswith(kind + " → ") for kind in
                                       ("supports", "challenges", "qualifies", "inconclusive")))
        lines.extend((line, style) for line in ([clip(text, measure)] if preview else wrap(text, measure)))
    visible = height - 5
    app.scroll = max(0, min(app.scroll, max(0, len(lines) - visible)))
    for index, (text, style) in enumerate(lines[app.scroll:app.scroll + visible]):
        frame.put(y + index + 3, x + inset, text, style, measure)
    frame.put(y + height - 1, x + 2,
              f"{app.scroll + 1}–{min(len(lines), app.scroll + visible)} / {len(lines)}   PgUp/PgDn",
              "muted", width - 4)


def compose(app, width, height):
    app.viewport_height = height
    frame = Frame(width, height)
    frame.put(0, 2, "◆ ClaimBranch", "brand")
    actual_panes = len(panes(app, width, height))
    density = app.density
    from .tui_proposals import available
    ai_label = ('AI preview' if getattr(app,'provider_connection',None) and available(app) else
                'AI example' if app.paper.ai_available or available(app) else 'AI OFF')
    badge = ai_label + ' · ' + (f"{actual_panes} pane{'s' if actual_panes != 1 else ''} · " if width >= 100 else '') + density
    context_width = width - len(badge) - 23 if width >= 76 else width - 21
    frame.put(0, 19, "⑂ " + app.ref + (" / " + app.episode_id if app.series else ""), "top_accent", max(0, context_width))
    if width >= 76:
        frame.put(0, width - len(badge) - 2, badge, "top_muted")
    recovery_error = getattr(app, "recovery_error", None)
    state = "DRAFT SAVE FAILED / ; actions for details" if recovery_error else "private draft recovery" if app.recovery else "session only"
    if encrypted_judgments(app) and not recovery_error:
        state = "writing recovery / reviews session-only"
    elif app.recovery and app.review.influenced() and not recovery_error:
        state = 'AI draft session-only / notes checkpointed'
    workspace_kind = 'PERSONAL' if getattr(app.recovery, 'personal_project', False) else 'SYNTHETIC'
    frame.put(1, 2, workspace_kind + "  /  " + state, "top_warning" if recovery_error else "top_muted", width - 4)
    status = workspace_kind + " / " + (ai_label + ' / ' if width < 76 else '') + state
    if app.series:
        status += " / " + app.view["episode"]["status"] + " reasoning / current global evidence"
    if app.scenario:
        status += " / HYPOTHETICAL " + app.scenario["assumption"]["outcome"]
    if app.search:
        status += " / Search: " + app.search
    if width < 76 and encrypted_judgments(app) and not recovery_error:
        status = workspace_kind + " / writing recovery"
        frame.put(0, max(19, width - len(ai_label) - 2), ai_label, "top_muted", len(ai_label))
    source_status = getattr(app, 'project_source_status', None)
    source_warning = source_status and not source_status.startswith('unchanged')
    if source_status in ('unchanged-since-refresh', 'unchanged-content-since-refresh') and not recovery_error:
        status = workspace_kind + ' / source association refreshed; earlier writing basis retained / ' + state
    if source_warning and not recovery_error:
        status = ('SOURCE CHECK: ' if getattr(app, 'project_source_checked', False) else 'SOURCE AT OPEN: ') + app.project_source_notice
    frame.fill(1, 0, width, "canvas")
    frame.put(1, 2, status, "top_warning" if recovery_error or app.scenario or source_warning else "top_muted", width - 4)
    if width < 48 or height < 18:
        frame.put(4, 2, "Enlarge to at least 48 columns × 18 rows.", "top_accent", width - 4)
        frame.put(6, 2, "Resize to continue. Ctrl+C exits to the shell.", "top_muted", width - 4)
        return frame
    context = " › ".join(app.kind(key) for key in app.selected_path) if len(app.selected_path) > 1 else app.view["title"]
    if app.lens == "evidence":
        context = app.evidence_label(app.evidence_root) + " / " + context
    if height >= 36:
        frame.put(2, 2, "Search: " + app.search if app.search else context, "top_muted", width - 4)
    tabs_y = 3 if height >= 36 else 2
    frame.put(tabs_y, 2, "[1 Argument]" if app.lens == "argument" else " 1 Argument ",
              "top_accent" if app.lens == "argument" else "top_muted", width - 4)
    frame.put(tabs_y, 17, "[2 Evidence uses]" if app.lens == "evidence" else " 2 Evidence uses ",
              "top_accent" if app.lens == "evidence" else "top_muted", width - 19)
    if app.lens == "evidence" and (62 <= width < 80 or width >= 104):
        frame.put(tabs_y, 38, "[ / ] change evidence", "top_muted", width - 40)
    if width >= 80 and app.series:
        frame.put(tabs_y, width - 32, "t Episodes   W Pending work", "top_accent", 30)
    for kind, x, y, w, h in panes(app, width, height):
        {"outline": outline, "links": relationships, "detail": inspector}[kind](frame, app, x, y, w, h)
    if width < 76:
        hints = "↑↓ move   Tab pane   ? help   q quit"
        actions = "n note  e draft  r links  ? more"
    else:
        hints = {"outline": "↑↓ select   ← parent/fold   → expand   Enter edge   r all links   / search",
                 "links": "↑↓ select   Enter follow   Tab read rationale   Esc back",
                 "detail": "↑↓ scroll   PgUp/PgDn page   d read   r relations"}[app.focus]
        actions = "n note   e draft   Tab pane   s what if   v layout   z density"
        if app.search and app.focus == "outline":
            hints = "↑↓ select   ← parent   → child   Enter edge   Esc clear search"
        if app.selected_row().reference:
            hints = "↪ Same record   g original   Enter edge   r all links   Esc back"
        if app.nodes[app.selected_id]["kind"] == "observation" and app.focus == "detail" and not app.reading_relation:
            hints = "u choose claim   r all connections   PgUp/PgDn read   Esc back"
    if app.navigation == "graph" and app.focus == "outline":
        hints = "Arrows move   Enter read   r follow edge   / search"
        if app.search:
            hints = "Arrows select   Enter read   Esc clear search"
        actions = "n note   f fit   l local   a all   z cards   P pin"
    elif app.navigation == "graph":
        actions = "n note   e draft   f fit graph   P pin   Esc back"
    unfinished = app.review.unfinished or bool(app.unfinished)
    proposal = None
    if app.mode == 'work' and app.focus == 'detail':
        hints = '; actions · e judgment · c changes · R review · Esc back'
        actions = 'C branch candidate · M merge · Enter finish · G graphs · x not now'
        session = app.review.sessions.get(app.review.key)
        proposal = session.state()['proposal'] if session else None
        if proposal and not proposal['adopted']:
            actions = ('y compare · retains AI origin · x reject · PgDn read' if encrypted_judgments(app) else
                       'y compare SESSION ONLY · x reject · PgDn read')
    elif width >= 76:
        actions = 'w work   M merge   , view   ' + actions
    if width < 76:
        hints = ('; actions · e write · Esc back' if app.mode == 'work' and app.focus == 'detail' else
                 {'outline': '; actions · Arrows move · Enter read',
                  'links': '; actions · Enter follow · Esc back',
                  'detail': '; actions · ↑↓ read · Esc back'}[app.focus])
        actions = ('U unfinished · ' if unfinished else '') + '? help · q quit'
    else:
        actions = '? help   q quit   ' + ('U unfinished   ' if unfinished else '') + actions
        if app.mode != 'work' or app.focus != 'detail':
            actions = '; actions   ' + actions
    if proposal and not proposal['adopted']:
        hints = '; actions · ' + ('U unfinished · ' if unfinished else '') + '? help · q quit'
        actions = ('y compare · keep AI origin · x reject' if encrypted_judgments(app) else
                   'y compare SESSION ONLY · x reject' if width < 76 else
                   'y compare SESSION ONLY · x reject · PgDn read')
    frame.put(height - 3, 2, hints, "top_accent", width - 4)
    frame.put(height - 2, 2, actions, "top_muted", width - 4)
    frame.put(height - 1, 2, app.message, "top_muted", width - 4)
    return frame


def render_snapshot(app, width=132, height=38):
    return compose(app, width, height).plain()


class Buffer:
    def __init__(self, text=""):
        text = clean(text)
        self.text, self.cursor = text, len(text)
        self.initial = text
        self.undo, self.redo = deque(maxlen=100), deque(maxlen=100)
        self.notice = ""

    def checkpoint(self):
        self.undo.append((self.text, self.cursor))
        self.redo.clear()

    def insert(self, value):
        value = clean(value)
        self.notice = "12,000 character limit; remaining input was not inserted." if len(value) + len(self.text) > 12000 else ""
        value = value[:12000 - len(self.text)]
        if value:
            self.checkpoint()
        self.text = self.text[:self.cursor] + value + self.text[self.cursor:]
        self.cursor += len(value)

    def segments(self, width):
        result, start, used = [], 0, 0
        for index, char in enumerate(self.text):
            if char == "\n":
                result.append((self.text[start:index], start, index))
                start, used = index + 1, 0
                continue
            size = char_width(char)
            if used + size > width:
                result.append((self.text[start:index], start, index))
                start, used = index, 0
            used += size
        result.append((self.text[start:], start, len(self.text)))
        return result

    def position(self, width):
        lines = self.segments(width)
        row = max(i for i, (_, start, _) in enumerate(lines) if start <= self.cursor)
        return lines, row, sum(char_width(c) for c in self.text[lines[row][1]:self.cursor])

    def key(self, event, width):
        if event in ("undo", "redo"):
            source, target = (self.undo, self.redo) if event == "undo" else (self.redo, self.undo)
            if source:
                target.append((self.text, self.cursor))
                self.text, self.cursor = source.pop()
                self.notice = ""
        elif isinstance(event, tuple) and event[0] == "paste":
            self.insert(event[1])
        elif event == "left":
            self.cursor = max(0, self.cursor - 1)
        elif event == "right":
            self.cursor = min(len(self.text), self.cursor + 1)
        elif event in ("up", "down", "home", "end"):
            lines, row, column = self.position(width)
            if event in ("up", "down"):
                row = max(0, min(len(lines) - 1, row + (-1 if event == "up" else 1)))
                text, start, _ = lines[row]
                self.cursor = start + len(clip(text, column, ellipsis=False))
            else:
                self.cursor = lines[row][1 if event == "home" else 2]
        elif event == "backspace" and self.cursor:
            self.checkpoint()
            self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
            self.cursor -= 1
        elif event == "delete":
            self.checkpoint()
            self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
        elif event == "enter":
            self.insert("\n")
        elif isinstance(event, str) and len(event) == 1 and event.isprintable():
            self.insert(event)


HELP = [
    ("PAPER CONNECTION", "; → Paper connection is available for demo project init/open. r previews a new location with identical source bytes; f previews changed source at the saved location; c checks status again. Read the complete preview with PgDn/End, then a applies only the encrypted association. Esc cancels and returns to the same graph/reader. Notes, judgments and earlier source basis remain unchanged. Temporary path input is not saved; no manuscript file or accepted evidence is written."),
    ("RESULT CAPTURE", "; → Draft a result and source starts separate, unconfirmed writing beside the selected subject. Each field is optional. Enter edits; Ctrl+S keeps the field, Esc retains unfinished input separately. --work-dir also checkpoints both. Ctrl+O inspects original/current context without losing the editor. Resume result drafts lists original subjects across contexts; d then Enter discards one. This cannot confirm evidence, enter scientific review, call AI or join the graph. Result drafts are excluded from --draft-file; without --work-dir they are lost on quit."),
    ("NAMED ACTIONS", "; opens actions for the selected node. Arrows choose; Enter opens; Esc returns. Manual writing comes first. Unavailable creation and AI actions explain their limits before a form opens. --ai-off disables fixed assistance while keeping manual work and recorded source history."),
    ("WRITE WITH CONTEXT", "e edits the selected judgment beside recorded source content at wide sizes, or below a compact source strip at narrow sizes. The title names its original owner. Ctrl+O opens full read-only source context; PgUp/PgDn scroll, Esc or Ctrl+O returns to the same text, cursor and undo history. Another Esc retains unfinished writing. Below 48x18 writing pauses. Source references are not opened or verified."),
    ("REUSE A JUDGMENT", "; → Link this judgment to nodes selects existing source nodes with Space, then Enter previews and another Enter applies. Choose a judgment for this node switches between existing work and this node's separate judgment. Text and AI history stay with their original owner; notes stay on the viewed node. Links create no scientific edges. --work-dir retains them; otherwise they last only this session. Manual checkpoints retain text at its original owner, without the links."),
    ("BRANCH / MERGE", "--merge-example opens an active synthetic episode before its last merge. M opens recorded alternative selection; Space includes a changed record, s loads a read-only manuscript fingerprint, R previews exact merge effects. Tab shows inherited judgments, G compares graphs, Enter completes unaccepted review and v calculates an uninstalled candidate. In Work, C previews your authored branch changes; Enter makes its detached candidate before merge selection. Escape returns without moving the original graph. All candidates/reviews remain session-only and no workspace history is replaced."),
    ("SCIENCE TO WORDING", "m in merge review opens wording for the current exact reviewed selection or a retained earlier draft. The judgment and reason stay visible while e edits wording. Ctrl+R reuses the judgment reason with undo and confirms replacement of different text; Ctrl+O reads the full basis and returns to the same editor. Parent/source changes invalidate review but retain text. A different reviewed scope starts a separate blank draft; nothing installs into the graph or W. --work-dir retains wording and original sources; actions resume saved manuscript drafts. Reviews remain session-only."),
    ("EPISODES / PENDING", "t chooses an episode and main/alternative (Tab), then Enter opens it. b toggles branches within the same episode. W lists conditional pending work across episodes; Enter reads its judgment and impact, g chooses a related node. m in a Writing impact item opens manuscript review: s loads a read-only source, e edits wording/reason, R previews, Tab changes view and Enter completes unaccepted review. --work-dir retains wording/source input; manuscript review answers remain session-only. U is separate unfinished local text. Older reasoning still uses current global evidence. --series enables the cumulative example."),
    ("GRAPH", "One box per record. Arrows select spatially; j/k visits every node in scope. Enter reads; r inspects an edge and its direction. f fits the current scope. HJKL pans. o switches graph/outline without changing drafts."),
    ("GRAPH EDGES", "Arrowheads point to recorded targets. Beside each connected card title, a label spells out its relationship to the selected node: supported by E1, produced E1, or part of C1. Long or parallel phrases continue directly below the title, above source text. Color reinforces these words. Independent lines overlap without a junction; r selects one exact edge and draws its route over crossing context."),
    ("NAVIGATE", "Arrow keys or j/k move. Tab changes pane; Shift-Tab goes back."),
    ("OUTLINE", "← folds or moves to parent; → unfolds. Space toggles a branch. Enter reads its edge. / searches with ancestry."),
    ("OUTLINE EDGES", "↑ means this node → its parent; ↓ means parent → this node. Each type is recorded, including parallel structural links."),
    ("VIEWS", "1 Argument starts at the thesis. 2 Evidence uses starts at an observation; [ / ] changes evidence. Esc returns with your context."),
    ("SHARED", "E1/E2 labels identify the same evidence across views; counts mean distinct directly linked claims. ↪ is a reference; ↔ marks another visible occurrence of the selected evidence. g jumps to its primary occurrence."),
    ("CLAIM USES", "Select evidence to read its named claim uses. u chooses a use; Enter follows it, Tab reads the rationale, Esc returns. r includes source/experiment connections too."),
    ("RELATIONS", "Enter follows a connection. Esc returns to the previous node."),
    ("READ", "d reads; PgUp/PgDn scroll. r focuses relationships."),
    ("LAYOUT", "Start with the full map. Enter opens reading beside it at 140+ columns, or a full reader on smaller screens. Esc restores the map. P pins/unpins the reader; the preference survives resizing. f fits the current scope using compact cards and restores the full pane. z switches compact/source cards. v changes outline layouts."),
    ("GRAPH SCOPE", "l roots a local neighborhood at the selected node; +/- changes its depth (1–3 hops). Selecting within it does not re-root it. a restores all nodes in the current Argument/Evidence lens. Counts distinguish offscreen cards from nodes/edges hidden by scope. r lists every recorded connection; following outside the scope reveals the target. Esc returns to the previous scope/position."),
    ("VIEW SETTINGS", ", opens spacing, card detail and reading-panel preferences. Arrows choose/change; Enter keeps the live preview, Esc restores the previous view. r previews defaults. Settings remain session-only. Vertical connectors retain at least three cells; use local scope or pan when a short screen cannot show all cards."),
    ("DENSITY", "z switches compact map cards and comfortable source cards. Short captions identify the subject; Enter reads the full statement and conditions. pp means percentage points. ! marks an unlinked record. Color and text identify node/relation types."),
    ("WHAT IF", "s selects an unrun experiment and a possible result. i shows impact."),
    ("DRAFT", "e edits. Tab changes field; Ctrl+S keeps the draft; Esc cancels."),
    ("WORK", "w connects the selected node's judgment to paper services. A chooses exact offline-example context; Enter reviews then requests it. y compares your judgment with the proposal; Enter explicitly replaces it, Esc keeps yours. e edits with AI origin retained, B compares before restoring the replaced text. c edits/selects scientific changes, R prepares their review, G compares before/after graphs, Enter finishes the unaccepted review, x is Not now. No live provider or accepted write is available. Change reviews remain session-only. --work-dir retains adopted judgment AI origin; --draft-file does not."),
    ("NODE NOTE", "n edits a free-form note beside the graph. Enter adds a line; Ctrl+S keeps it; Esc cancels changes. ✎ marks notes on compact cards; source cards and the reader show their text. N recovers a cancelled note; E recovers a cancelled judgment; U lists unfinished writing across nodes and branches. Ctrl+_ undoes, Ctrl+Y redoes. Kept text changes only with Ctrl+S."),
    ("RETURN TO REVIEW WRITING", "U resumes unfinished scientific fields and review answers. Ctrl+O compares original/current science, authored baseline and judgment/AI contributions without changing text. --work-dir preserves this input; --draft-file excludes it. Answers require a freshly prepared review. Changed field context requires Ctrl+O, r and Enter to choose the displayed current basis before keeping. Restoring text grants no review authority."),
    ("RETURN TO EXPLANATION", "W → explanation item → Enter → e opens its causal topics. Enter reads one topic; e writes partial text, r links/unlinks the original reason, Tab reads original/current science, the earlier draft basis and AI history. [ and ] change topic. Ctrl+O in the editor inspects source without losing writing; Ctrl+S keeps and Esc retains unfinished input separately. s previews an explicit basis update. --work-dir retains this writing and original context; --draft-file excludes it. Without encrypted recovery it is session-only. Returning never grades understanding or closes an item."),
    ("CONTEXT", "m shows writing context; p shows human/AI history; b changes branch."),
    ("SHELL", "Ctrl+Z suspends to your shell; fg resumes. q exits; volatile notes/drafts need a discard choice. --draft-file enables manual recovery; --work-dir encrypts judgments, AI origin, notes, links and argument/result drafts on Mac. Wording and scientific reviews remain session-only. Ctrl+C exits immediately. Ctrl+L redraws."),
    ("PROTOTYPE", "Synthetic only. Optional private UI draft file; no research/manuscript writes, experiment execution, listener or model calls."),
]


class Terminal:
    def __init__(self, screen, app, curses):
        self.screen, self.app, self.curses = screen, app, curses
        self.modal, self.buffers, self.field = None, [], 0
        self.pending = deque()
        self.discard_sequence = False
        self.plan_index = self.help_scroll = 0
        self._paint_layout = None
        self.setup_styles()

    def setup_styles(self):
        c = self.curses
        self.styles = {"body": 0, "canvas": 0, "brand": c.A_BOLD, "heading": c.A_BOLD,
                       "lead": c.A_BOLD, "accent": c.A_BOLD, "muted": 0, "border": c.A_DIM,
                       "graph_dim": c.A_DIM, "graph_dim_border": c.A_DIM,
                       "top_muted": 0, "top_accent": c.A_BOLD, "top_warning": c.A_BOLD,
                       "warning": c.A_BOLD, "selected": c.A_REVERSE | c.A_BOLD,
                       "selected_meta": c.A_REVERSE | c.A_BOLD}
        for name in ("claim", "evidence", "plan", "run", "interpretation", "writing",
                     "supports", "challenges", "qualifies", "inconclusive"):
            self.styles[name] = c.A_BOLD
        if c.has_colors() and not os.environ.get("NO_COLOR"):
            try:
                # Fixed surfaces keep contrast independent of the host profile;
                # no terminal palette, font or global preference is changed.
                if c.COLORS >= 256 and c.COLOR_PAIRS >= 32:
                    canvas, surface, selection = 233, 235, 238
                    palette = {"canvas": (252, canvas), "body": (253, surface),
                               "brand": (183, canvas), "heading": (250, surface),
                               "lead": (255, surface), "muted": (246, surface),
                               "border": (240, surface), "accent": (117, surface),
                               "graph_dim": (245, surface), "graph_dim_border": (242, surface),
                               "warning": (222, surface), "selected": (255, selection),
                               "selected_meta": (189, selection), "top_muted": (246, canvas),
                               "top_accent": (117, canvas), "top_warning": (222, canvas),
                               "claim": (183, surface), "evidence": (116, surface),
                               "plan": (222, surface), "run": (111, surface),
                               "interpretation": (180, surface), "writing": (218, surface),
                               "supports": (114, surface), "challenges": (210, surface),
                               "qualifies": (222, surface), "inconclusive": (222, surface)}
                    for pair, (name, (foreground, background)) in enumerate(palette.items(), 1):
                        c.init_pair(pair, foreground, background)
                        weight = 0 if name in ("body", "canvas", "muted", "border", "top_muted", "selected",
                                              "graph_dim", "graph_dim_border") else c.A_BOLD
                        self.styles[name] = c.color_pair(pair) | weight
                else:
                    c.use_default_colors()
                    colors = {"claim": c.COLOR_MAGENTA, "evidence": c.COLOR_CYAN,
                              "plan": c.COLOR_YELLOW, "run": c.COLOR_BLUE,
                              "interpretation": c.COLOR_YELLOW, "writing": c.COLOR_MAGENTA,
                              "supports": c.COLOR_GREEN, "challenges": c.COLOR_RED,
                              "qualifies": c.COLOR_YELLOW, "inconclusive": c.COLOR_YELLOW,
                              "brand": c.COLOR_MAGENTA, "accent": c.COLOR_CYAN,
                              "top_accent": c.COLOR_CYAN, "warning": c.COLOR_YELLOW,
                              "top_warning": c.COLOR_YELLOW}
                    for pair, color in enumerate(sorted(set(colors.values())), 1):
                        c.init_pair(pair, color, -1)
                        for name, value in colors.items():
                            if value == color:
                                self.styles[name] = c.color_pair(pair) | c.A_BOLD
            except c.error:
                pass  # Monochrome retains the same text and focus cues.

        for name in ("supports", "challenges", "qualifies", "accent"):
            self.styles["relation_" + name] = self.styles[name] & ~c.A_BOLD

    def read(self):
        c = self.curses
        controls = {"\n": "enter", "\r": "enter", "\t": "tab", "\x7f": "backspace", "\b": "backspace",
                    "\x03": "interrupt", "\x13": "keep", "\x0c": "redraw",
                    "\x1f": "undo", "\x19": "redo", "\x1a": "suspend", "\x0f": "source", "\x12": "reuse-reason"}
        if self.pending:
            event = self.pending.popleft()
            return controls.get(event, event)
        try:
            event = self.screen.get_wch()
        except c.error:
            return None
        keys = {c.KEY_UP: "up", c.KEY_DOWN: "down", c.KEY_LEFT: "left", c.KEY_RIGHT: "right",
                c.KEY_HOME: "home", c.KEY_END: "end", c.KEY_BACKSPACE: "backspace", c.KEY_DC: "delete",
                c.KEY_NPAGE: "page-down", c.KEY_PPAGE: "page-up", c.KEY_BTAB: "backtab",
                c.KEY_ENTER: "enter", c.KEY_RESIZE: "resize"}
        if isinstance(event, int):
            return keys.get(event)
        if self.discard_sequence:
            if event == "\x03":
                self.discard_sequence = False
                return "interrupt"
            if event != "\x1b":
                if "@" <= event <= "~":
                    self.discard_sequence = False
                return None
            self.discard_sequence = False
        if event != "\x1b":
            return controls.get(event, event)
        # Decode bracketed paste as a single text event: its contents must never
        # become navigation keys, a scenario selection or an exit command.
        suffix = ""
        received_suffix = False
        # curses already waited ESCDELAY to distinguish a bare Escape. Drain
        # buffered suffixes immediately; only an actual prefix needs a wait.
        self.screen.timeout(0)
        try:
            for _ in range(64):
                part = self.screen.get_wch()
                received_suffix = True
                if not isinstance(part, str):
                    break
                suffix += part
                self.screen.timeout(100)
                if len(suffix) == 1 and part not in "[O":
                    break
                if len(suffix) > 1 and ((suffix[0] in "[O" and "@" <= part <= "~") or
                                       (suffix[0] not in "[O" and part.isalpha())):
                    break
        except c.error:
            pass
        finally:
            self.screen.timeout(100)
        if suffix == "[200~":
            data, ending, deadline = [], "", time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    part = self.screen.get_wch()
                except c.error:
                    continue
                if not isinstance(part, str):
                    continue
                deadline = time.monotonic() + 5
                ending += part
                if ending.endswith("\x1b[201~"):
                    return ("paste", "".join(data))
                while ending and not "\x1b[201~".startswith(ending):
                    if len(data) < 24000:
                        data.append(ending[0])
                    ending = ending[1:]
            self.app.message = "Paste interrupted; received text stays in the active input."
            return ("paste", "".join(data))
        decoded = {"[A": "up", "[B": "down", "[C": "right", "[D": "left", "[H": "home", "[F": "end",
                   "[5~": "page-up", "[6~": "page-down", "[3~": "delete", "[Z": "backtab",
                   "OA": "up", "OB": "down", "OC": "right", "OD": "left", "OH": "home", "OF": "end"}
        if suffix in decoded:
            return decoded[suffix]
        if suffix.startswith(("[", "O")):
            # An overlong or truncated sequence can finish on a later read.
            # Its trailing letters still belong to that key, not to q/s/etc.
            self.discard_sequence = len(suffix) < 2 or not "@" <= suffix[-1] <= "~"
            return None  # Unknown terminal sequences are one key, never application shortcuts.
        # Alt/Option arrives as ESC + a character. Replaying that character as
        # a command could cancel editing, switch branch or quit unintentionally.
        return None if received_suffix else "escape"

    def draw_modal(self, frame):
        if self.modal.startswith('proposal-'):
            from .tui_proposals import proposals_ui
            return proposals_ui(self).draw(frame)
        if self.modal.startswith('personal-'):
            from .tui_personal import personal_ui
            return personal_ui(self).draw(frame)
        if self.modal == 'save-status' and (frame.width < 48 or frame.height < 18):
            frame.put(3, 1, 'Save details paused. Enlarge to 48 x 18.', 'top_warning', frame.width - 2)
            frame.put(5, 1, 'Esc returns. Writing stays in memory.', 'top_muted', frame.width - 2)
            return frame
        if self.modal.startswith('project-source'):
            from .tui_project_source import project_source_ui
            return project_source_ui(self).draw(frame)
        if self.modal.startswith('intake-'):
            from .tui_intake_ui import intake_ui
            return intake_ui(self).draw(frame)
        if self.modal.startswith('understanding-'):
            from .tui_understanding_ui import understanding_ui
            return understanding_ui(self).draw(frame)
        if self.modal.startswith('work-links-'):
            from .tui_work_links_ui import work_links_ui
            return work_links_ui(self).draw(frame)
        if self.modal.startswith('candidate-'):
            from .tui_candidates_ui import candidates_ui
            return candidates_ui(self).draw(frame)
        if self.modal == 'actions':
            from .tui_actions import actions_ui
            return actions_ui(self).draw(frame)
        if self.modal == 'edit':
            from .tui_judgment_ui import judgment_ui
            return judgment_ui(self).draw(frame)
        if self.modal == 'view-settings':
            from .tui_view_ui import view_ui
            return view_ui(self).draw(frame)
        if self.modal.startswith('review-'):
            from .tui_review_ui import review_ui
            return review_ui(self).draw(frame)
        width, height = frame.width, frame.height
        if width < 48 or height < 18:
            if self.modal.startswith('context-') or self.modal == 'recovery':
                frame = Frame(width, height)
                frame.put(1, 1, 'Navigation controls paused', 'warning', width - 2)
                frame.put(3, 1, 'Enlarge to 48 x 18. Esc returns.', 'body', width - 2)
            return frame
        if self.modal.startswith('branch-'):
            from .tui_branch_ui import branch_ui
            return branch_ui(self).draw(frame)
        if self.modal.startswith('manuscript-'):
            from .tui_manuscript_ui import manuscript_ui
            return manuscript_ui(self).draw(frame)
        if self.modal.startswith('context-'):
            from .tui_context_ui import context_ui
            return context_ui(self).draw(frame)
        if self.modal == "note":
            _, x, y, w, h = next(pane for pane in panes(self.app, width, height) if pane[0] == "detail")
            x, y, w, h = frame.panel(x, y, w, h, "MY NOTE / " + ("private draft" if self.app.recovery else "session only"), True)
            frame.put(y + 2, x + 2, self.app.title(self.app.selected_id), "muted", w - 4)
            buffer = self.buffers[0]
            measure, visible = w - 4, h - 6
            lines, row, column = buffer.position(measure)
            offset = max(0, row - visible + 1)
            for n, (text, _, _) in enumerate(lines[offset:offset + visible]):
                frame.put(y + 4 + n, x + 2, text, "body", measure)
            frame.cursor = (y + 4 + row - offset, min(x + w - 2, x + 2 + column))
            frame.put(y + h - 1, x + 2, "Enter new line · Ctrl+S keep · Esc cancel", "accent", w - 4)
            for row in range(height - 3, height):
                frame.fill(row, 0, width, "canvas")
            frame.put(height - 3, 2, "Editing this node's note · Ctrl+S keep · Esc cancel", "top_accent", width - 4)
            state = "modified" if buffer.text != buffer.initial else "unchanged"
            frame.put(height - 2, 2, f"{len(buffer.text):,}/12,000 · {state} · Ctrl+_ undo · Ctrl+Y redo", "top_muted", width - 4)
            warning = getattr(self.app, "recovery_error", None) or buffer.notice
            frame.put(height - 1, 2, warning or "Esc leaves kept note unchanged · N recovers cancelled editing", "top_warning" if warning else "top_muted", width - 4)
            return frame
        if self.modal == "search":
            frame.fill(height - 3, 1, width - 2, "body")
            frame.put(height - 3, 2, "/ " + self.buffers[0].text, "accent", width - 4)
            frame.put(height - 2, 2, "Search content · Enter apply · Esc cancel", "muted", width - 4)
            frame.cursor = (height - 3, min(width - 3, 4 + cell_width(self.buffers[0].text[:self.buffers[0].cursor])))
            return frame
        if self.modal == "recovery":
            w, h = min(width - 4, 96), min(height - 4, 24, max(8, 4 * len(self.recovery_items) + 3))
            x, y = (width - w) // 2, (height - h) // 2
            frame.box(x, y, w, h, "UNFINISHED / Enter resume · Esc close", True)
            if getattr(self, 'recovery_discard', False):
                frame.put(y + h - 2, x + 2, 'x again discards selected unfinished text · Esc cancels', 'warning', w - 4)
            elif self.recovery_items and self.recovery_items[self.recovery_index] in self.app.review.unfinished:
                frame.put(y + h - 2, x + 2, 'x discard unfinished text · staged/reviewed content stays', 'accent', w - 4)
            visible = max(1, (h - 3) // 4)
            offset = max(0, self.recovery_index - visible + 1)
            if not self.recovery_items:
                frame.put(y + 2, x + 2, "No unfinished writing.", "muted", w - 4)
            for row, key in enumerate(self.recovery_items[offset:offset + visible]):
                *context, mode = key
                chosen = row + offset == self.recovery_index
                review_text = key in self.app.review.unfinished
                kind = ('Scientific change / ' + mode.removeprefix('change:') if mode.startswith('change:')
                        else {'note': 'Note', 'edit': 'Judgment', 'explanation': 'Review explanation'}[mode])
                text = ((recovery_copy(self.app, 'encrypted recovery · ') if encrypted_judgments(self.app) else 'Session only · ') if review_text else '') + kind
                frame.put(y + 1 + 4 * row, x + 2, ("› " if chosen else "  ") + text, "selected_meta" if chosen else "heading", w - 4)
                frame.put(y + 2 + 4 * row, x + 4, ' / '.join(context), 'muted', w - 6)
                texts = (self.app.review.unfinished if review_text else self.app.unfinished)[key]
                preview = " · ".join(texts) if any(texts) else '(empty edit)'
                frame.put(y + 3 + 4 * row, x + 4, preview, "selected" if chosen else "body", w - 6)
            return frame
        if self.modal == "help":
            title, content = "KEYS / Esc closes · PgUp/PgDn", [(title, recovery_copy(self.app, text)) for title, text in HELP]
            if personal(self.app):
                content = [('PERSONAL WRITING', 'Kept and unfinished writing is checkpointed in this private directory. q saves before leaving; project open resumes it. Local files have no application encryption. No protected approval, live AI or manuscript writing. Reviews remain session-only.')] + content
        elif self.modal == 'save-status':
            title = 'WRITING SAVE / Esc closes · PgUp/PgDn'
            content = [('WRITING CHECKPOINT' if getattr(self.app, 'recovery_error', None) else 'WRITING SAVED', getattr(self.app, 'recovery_error', None) or
                        'The latest writing checkpoint succeeded. Nothing accepted.'),
                       ('RETURN TO WRITING', 'Esc returns to the same graph. Saving never confirms evidence or accepts science.')]
        elif self.modal == "quit":
            title = "LEAVE SESSION?"
            content = [("UNSAVED DRAFTS / SESSION WORK", ("Manual judgments/notes are checkpointed at their original nodes. Unconfirmed result drafts, judgment links, explanation drafts, unfinished change/explanation text, AI work, scientific changes/reviews, manuscript wording and branch/merge candidates will be discarded."
                        if self.app.recovery else "Your session drafts, result drafts, judgment links, explanation drafts, notes, proposals, change reviews, manuscript wording and branch/merge candidates will be discarded.")),
                       ("y / discard and exit", "n or Esc / return to your work")]
            if encrypted_judgments(self.app):
                content = [("WRITING SAVED", "Judgments, AI origin, notes, links, argument/result drafts, partial explanations, unfinished scientific-review input and manuscript wording/source input are checkpointed."),
                           ("SESSION-ONLY WORK WILL BE DISCARDED", ', '.join(excluded_work(self.app))),
                           ("y / discard listed work and exit", "n or Esc / return to your work")]
        else:
            title = "HYPOTHETICAL / nothing runs"
            plans = [node for node in self.app.view["nodes"] if node["kind"] == "experiment-plan"]
            self.plan_index %= len(plans)
            plan = plans[self.plan_index]
            content = [("UNRUN PLAN", self.app.title(plan["id"])), ("CONDITIONS", plan["content"]["conditions"]),
                       ("1 supports   2 challenges   3 inconclusive", "0 clears · ↑↓ selects a plan · Esc cancels")]
        w, h = min(width - 4, 96), min(height - 4, 30 if self.modal in ('help', 'save-status') else 19)
        x, y = (width - w) // 2, (height - h) // 2
        frame.box(x, y, w, h, title, True)
        lines = []
        for heading, text in content:
            lines.extend([(line, "heading") for line in wrap(heading, w - 4)])
            lines.extend([(line, "body") for line in wrap(text, w - 4)])
            lines.append(("", "body"))
        offset = 0
        if self.modal == "help":
            self.help_scroll = min(self.help_scroll, max(0, len(lines) - h + 2))
            offset = self.help_scroll
        elif self.modal == 'save-status':
            self.save_scroll = min(self.save_scroll, max(0, len(lines) - h + 2))
            offset = self.save_scroll
        body_height = h - 5 if self.modal == "scenario" else h - 2
        for index, (text, style) in enumerate(lines[offset:offset + body_height]):
            frame.put(y + 1 + index, x + 2, text, style, w - 4)
        if self.modal == "scenario":
            frame.put(y + h - 3, x + 2, "1 supports  2 challenges  3 inconclusive", "accent", w - 4)
            frame.put(y + h - 2, x + 2, "0 clear · ↑↓ plan · Esc cancel", "muted", w - 4)
        return frame

    def paint(self):
        # The terminal, not exported shell dimensions or a delayed resize event,
        # owns the drawable area. Reconcile before any cursor addressing.
        try:
            width, height = os.get_terminal_size(sys.stdin.fileno())
            if width > 0 and height > 0 and self.screen.getmaxyx() != (height, width):
                self.curses.resizeterm(height, width)
        except (OSError, ValueError):
            pass
        height, width = self.screen.getmaxyx()
        frame = (Frame(width, height) if self.modal in ('edit', 'actions') or (self.modal and self.modal.startswith(('personal-', 'review-', 'context-', 'manuscript-', 'branch-', 'candidate-', 'understanding-', 'intake-')) and width >= 48 and height >= 18)
                 else compose(self.app, width, height))
        if self.modal:
            frame = self.draw_modal(frame)
        self.screen.erase()
        layout = (width, height, tuple(panes(self.app, width, height)), self.modal)
        if layout != self._paint_layout:
            self.screen.clearok(True)
            self._paint_layout = layout
        c = self.curses
        for y, row in enumerate(frame.cells):
            x = 0
            while x < width:
                start, style = x, row[x][1]
                chars = []
                while x < width and row[x][1] == style:
                    chars.append(row[x][0])
                    x += 1
                text = "".join(chars)
                if y == height - 1:
                    text = clip(text, width - start - 1, ellipsis=False)
                if text:
                    try:
                        self.screen.addstr(y, start, text, self.styles.get(style, 0))
                    except c.error:
                        if self.screen.getmaxyx() == (height, width):
                            raise
                        return  # A resize invalidated coordinates; rebuild next frame.
        try:
            c.curs_set(1 if frame.cursor else 0)
            self.screen.move(*(frame.cursor or (0, 0)))
        except c.error:
            pass
        self.screen.refresh()

    def modal_key(self, event):
        if self.modal.startswith('proposal-'):
            from .tui_proposals import proposals_ui
            proposals_ui(self).dispatch(event)
            return None
        if self.modal.startswith('personal-'):
            from .tui_personal import personal_ui
            personal_ui(self).dispatch(event)
            return None
        if self.modal.startswith('project-source'):
            from .tui_project_source import project_source_ui
            project_source_ui(self).dispatch(event)
            return None
        if self.modal.startswith('intake-'):
            from .tui_intake_ui import intake_ui
            intake_ui(self).dispatch(event)
            return None
        if self.modal.startswith('understanding-'):
            from .tui_understanding_ui import understanding_ui
            understanding_ui(self).dispatch(event)
            return None
        if self.modal.startswith('work-links-'):
            from .tui_work_links_ui import work_links_ui
            work_links_ui(self).dispatch(event)
            return None
        if self.modal.startswith('candidate-'):
            from .tui_candidates_ui import candidates_ui
            candidates_ui(self).dispatch(event)
            return None
        if self.modal == 'actions':
            from .tui_actions import actions_ui
            actions_ui(self).key(event)
            return None
        if self.modal == 'edit':
            from .tui_judgment_ui import judgment_ui
            if judgment_ui(self).key(event):
                return None
        if self.modal == 'recovery' and event != 'escape':
            height, width = self.screen.getmaxyx()
            if width < 48 or height < 18:
                return None
        if self.modal == 'recovery' and getattr(self, 'recovery_discard', False) and event == 'escape':
            self.recovery_discard = False
            return None
        if self.modal == 'view-settings':
            from .tui_view_ui import view_ui
            view_ui(self).key(event)
            return None
        if self.modal.startswith('branch-'):
            from .tui_branch_ui import branch_ui
            branch_ui(self).dispatch(event)
            return None
        if self.modal.startswith('manuscript-'):
            from .tui_manuscript_ui import manuscript_ui
            manuscript_ui(self).dispatch(event)
            return None
        if self.modal.startswith('context-'):
            from .tui_context_ui import context_ui
            context_ui(self).dispatch(event)
            return None
        if self.modal.startswith('review-'):
            from .tui_review_ui import review_ui
            review_ui(self).dispatch(event)
            return None
        if event == "escape":
            if self.modal in ("note", "edit"):
                if any(b.text != b.initial for b in self.buffers):
                    self.app.unfinished[(*self.app.writing_key(self.modal), self.modal)] = [b.text for b in self.buffers]
                self.app.message = "Editing cancelled; kept text unchanged. N recovers note; E recovers judgment."
            if self.modal == "note":
                self.app._restore_navigation(self.note_return_context)
                del self.app.trail[self.note_return_depth:]
            self.modal = None
        elif self.modal == "note":
            if event == "keep":
                self.app.keep_note(self.buffers[0].text)
                self.app.unfinished.pop((*self.app.context_key(), "note"), None)
                self.app.focus, self.modal = "detail", None
            elif event == "tab":
                self.buffers[0].insert("    ")
            else:
                width, height = self.screen.getmaxyx()[::-1]
                _, _, _, w, _ = next(pane for pane in panes(self.app, width, height) if pane[0] == "detail")
                measure = w - 8 if width >= 100 and w >= 34 else w - 4
                self.buffers[0].key(event, max(2, measure))
        elif self.modal == "edit":
            if event in ("tab", "backtab"):
                self.field = 1 - self.field
            elif event == "keep":
                self.app.keep_draft(self.buffers[0].text, self.buffers[1].text)
                self.app.unfinished.pop((*self.app.work_key(), "edit"), None)
                self.app.focus, self.modal = "detail", None
            else:
                from .tui_judgment_ui import editor_geometry
                height, width = self.screen.getmaxyx()
                self.buffers[self.field].key(event, editor_geometry(width, height)[2] - 4)
        elif self.modal == "search":
            if event == "enter":
                self.app.search = self.buffers[0].text.strip()
                rows = self.app.rows()
                if rows:
                    matches = self.app.matching_ids()
                    row = next(row for row in rows if row.node_id in matches)
                    self.app.select(row.node_id, path=row.path, reveal=False)
                self.app.focus, self.modal = "outline", None
            else:
                self.buffers[0].key(event, max(2, self.screen.getmaxyx()[1] - 6))
        elif self.modal == "help":
            if event in ("?", "enter", "q"):
                self.modal = None
            elif event in ("page-up", "up", "page-down", "down"):
                self.help_scroll = max(0, self.help_scroll + (-8 if event in ("page-up", "up") else 8))
        elif self.modal == 'save-status':
            if event in ('enter', 'q'):
                self.modal = None
            elif event in ('page-up', 'up', 'page-down', 'down'):
                self.save_scroll = max(0, self.save_scroll + (-8 if event in ('page-up', 'up') else 8))
        elif self.modal == "recovery":
            if event in ("up", "down"):
                self.recovery_discard = False
                self.recovery_index = max(0, min(len(self.recovery_items) - 1,
                                                self.recovery_index + (-1 if event == "up" else 1)))
            elif event == 'x' and self.recovery_items:
                key = self.recovery_items[self.recovery_index]
                if key in self.app.review.unfinished:
                    if getattr(self, 'recovery_discard', False):
                        self.app.review.unfinished.pop(key)
                        self.app.review.unfinished_basis.pop(key, None)
                        self.recovery_items.remove(key)
                        self.recovery_index = min(self.recovery_index, max(0, len(self.recovery_items) - 1))
                        self.recovery_discard = False
                        self.app.message = 'Unfinished text discarded. Staged changes and completed reviews stay unchanged.'
                    else:
                        self.recovery_discard = True
            elif event == "enter" and self.recovery_items:
                self.recovery_discard = False
                *context, mode = self.recovery_items[self.recovery_index]
                if mode == 'note':
                    self.app.open_context_key(context)
                else:
                    self.app.open_work_key(context)
                self.modal = None
                if mode in ('note', 'edit'):
                    self.key("N" if mode == "note" else "E")
                else:
                    from .tui_review_ui import review_ui
                    try:
                        review_ui(self).resume(mode)
                    except (ContractError, ValueError) as error:
                        self.app.message = str(error)
        elif self.modal == "quit":
            if event == "y":
                return 0
            if event == "n":
                self.modal = None
        elif self.modal == "scenario":
            plans = [node for node in self.app.view["nodes"] if node["kind"] == "experiment-plan"]
            if event in ("up", "down"):
                self.plan_index = (self.plan_index + (-1 if event == "up" else 1)) % len(plans)
            elif event in ("1", "2", "3"):
                self.app.preview_scenario(plans[self.plan_index]["id"],
                                          {"1": "supports", "2": "challenges", "3": "inconclusive"}[event])
                self.app.focus, self.modal = "detail", None
            elif event == "0":
                self.app.scenario = None
                self.app.message = "Preview cleared. Evidence and reasoning are unchanged."
                self.modal = None
        return None

    def key(self, event):
        app = self.app
        if event == "interrupt":
            return 130
        if event == "suspend":
            try:
                foreground = os.tcgetpgrp(sys.stdin.fileno()) == os.getpgrp()
            except (OSError, ValueError):
                foreground = False
            if not foreground or os.getpgrp() == os.getsid(0) or signal.getsignal(signal.SIGTSTP) == signal.SIG_IGN:
                app.message = "No job-control shell: suspend unavailable. Use an interactive shell or a terminal multiplexer."
                if self.modal in ("note", "edit"):
                    self.buffers[0 if self.modal == "note" else self.field].notice = app.message
                return None
            if not self.checkpoint():
                return None
            self.curses.def_prog_mode()
            sys.stdout.write("\x1b[?2004l")
            sys.stdout.flush()
            self.curses.endwin()
            # Stop the whole foreground job, including a waiting launcher.
            # Stopping only Python can strand a wrapper with no shell prompt.
            os.killpg(os.getpgrp(), signal.SIGSTOP)
            self.curses.reset_prog_mode()
            self.curses.raw()
            sys.stdout.write("\x1b[?2004h")
            sys.stdout.flush()
            self.screen.clearok(True)
            return None
        if event in ("redraw", "resize"):
            self.screen.clearok(True)
            return None
        if self.modal:
            return self.modal_key(event)
        if isinstance(event, tuple):
            app.message = "Paste into a draft (e) or search (/). Pasted text does not run shortcuts."
            return None
        if event == ';':
            from .tui_actions import actions_ui
            actions_ui(self).open()
            return None
        if event == 'A':
            from .tui_proposals import available, proposals_ui
            if available(app):
                try: proposals_ui(self).enter('ask')
                except (ContractError, ValueError) as error: app.message = str(error)
                return None
        if event == 'M':
            from .tui_branch_ui import branch_ui
            try:
                branch_ui(self).open()
            except ValueError as error:
                app.message = str(error)
            return None
        from .tui_context_ui import context_ui
        if context_ui(self).dispatch(event):
            return None
        from .tui_review_ui import review_ui
        if review_ui(self).dispatch(event):
            return None
        if event == "q":
            if app.recovery:
                if self.checkpoint():
                    if (excluded_work(app) if encrypted_judgments(app) else app.review.volatile_work()):
                        self.modal = 'quit'
                    else:
                        return 0
            elif app.review.volatile_work() or any(app.notes.values()) or any(any(texts) for texts in app.unfinished.values()) or any(draft["text"] or draft["rationale"] for draft in app.drafts.values()):
                self.modal = "quit"
            else:
                return 0
        elif event == ',':
            from .tui_view_ui import view_ui
            view_ui(self).open()
        elif event == "?":
            self.modal = "help"
        elif event == "U":
            self.recovery_items = sorted(set(app.unfinished) | set(app.review.unfinished))
            self.recovery_index, self.modal = 0, "recovery"
            self.recovery_discard = False
        elif event in ("tab", "backtab"):
            order = ["outline", "links", "detail"]
            target = order[(order.index(app.focus) + (-1 if event == "backtab" else 1)) % len(order)]
            if app.navigation == "graph":
                app.open_view(target, app.mode)
            else:
                app.focus = target
            if app.focus == "links":
                app.reading_relation, app.mode, app.scroll = True, "detail", 0
        elif event in ("up", "k", "down", "j"):
            amount = -1 if event in ("up", "k") else 1
            if app.focus == "outline":
                if app.navigation == "graph":
                    if event in ("j", "k"):
                        keys = list(graph_scene(app).boxes)
                        app.select(keys[max(0, min(len(keys) - 1, keys.index(app.selected_id) + amount))])
                    else:
                        move_graph(app, event)
                else:
                    app.move(amount)
            elif app.focus == "links":
                app.link_index = max(0, min(len(app.display_links()) - 1, app.link_index + amount))
                app.reading_relation, app.mode, app.scroll = True, "detail", 0
            else:
                app.scroll = max(0, app.scroll + amount)
        elif event in ("page-up", "page-down"):
            app.scroll = max(0, app.scroll + (-10 if event == "page-up" else 10))
        elif event in ("home", "end") and app.focus == "outline":
            rows = ([row for row in app.graph_rows() if row.node_id in app.graph_ids()]
                    if app.navigation == "graph" else app.rows())
            if rows:
                row = rows[0 if event == "home" else -1]
                app.select(row.node_id, path=row.path, reveal=False)
        elif event == "enter":
            if app.focus == "links" and app.display_links():
                app.follow(app.display_links()[app.link_index])
            elif app.focus == "detail" and app.reading_relation and app.display_links():
                app.follow(app.display_links()[app.link_index])
            elif app.focus == "outline":
                if app.navigation == "graph":
                    app.open_view()
                    app.reading_relation = False
                else:
                    app.inspect_parent_edge()
        elif event == " " and app.focus == "outline":
            if app.navigation == "outline":
                app.toggle_collapsed()
        elif event == "left" and app.focus == "outline":
            move_graph(app, event) if app.navigation == "graph" else app.left()
        elif event == "right" and app.focus == "outline":
            move_graph(app, event) if app.navigation == "graph" else app.right()
        elif event == "o":
            app.navigation = "outline" if app.navigation == "graph" else "graph"
            app.graph_follow = True
            app.message = "Navigation: " + app.navigation + ". Same selection, evidence, drafts and scenario."
        elif event == "f":
            app.fit_graph()
        elif event == "P" and app.navigation == "graph":
            app.graph_pinned = app.graph_fullscreen or not app.graph_pinned
            app.graph_fullscreen = False
            app.message = ("Reader pinned at 140+ columns. P unpins; Enter reads."
                           if app.graph_pinned else "Reader unpinned. Esc returns to the map.")
        elif event == "l" and app.navigation == "graph":
            app.scope_graph(app.selected_id)
        elif event == "a" and app.navigation == "graph":
            app.scope_graph()
        elif event in ("+", "-", "=") and app.navigation == "graph" and app.graph_root:
            app.scope_graph(app.graph_root, max(1, min(3, app.graph_depth + (-1 if event == "-" else 1))))
        elif event in ("H", "J", "K", "L") and app.navigation == "graph":
            dx, dy = {"H": (-8, 0), "J": (0, 4), "K": (0, -4), "L": (8, 0)}[event]
            app.graph_pan = (app.graph_pan[0] + dx, app.graph_pan[1] + dy)
            app.graph_follow = False
        elif event == "g":
            app.jump_to_original()
        elif event in ("1", "2"):
            app.switch_lens("argument" if event == "1" else "evidence")
        elif event in ("[", "]"):
            app.cycle_evidence(-1 if event == "[" else 1)
        elif event == "escape":
            app.back()
        elif event == "v":
            app.layout = "three" if app.layout == "two" else "two"
            app.message = "Layout changed; context preserved. Three panes need 118 columns."
        elif event == "z":
            app.density = "compact" if app.density == "comfortable" else "comfortable"
            app.message = "Spacing: " + app.density + ". Selection, scenario and drafts preserved."
        elif event == "b":
            app.switch_ref()
        elif event == "r":
            app.open_view("links")
            links = app.display_links()
            key = links[app.link_index].key if 0 <= app.link_index < len(links) else None
            app.link_scope = "all"
            app.link_index = next((i for i, link in enumerate(app.links()) if link.key == key), 0)
            app.focus = "links"
            app.reading_relation, app.mode, app.scroll = True, "detail", 0
        elif event == "u":
            if app.nodes[app.selected_id]["kind"] == "observation":
                app.open_view("links")
                app.link_scope, app.link_index = "uses", 0
                app.focus = "links"
                app.reading_relation, app.mode, app.scroll = True, "detail", 0
            else:
                app.message = "Select evidence to inspect its direct claim uses. 2 opens evidence view."
        elif event in ("d", "i", "m", "p"):
            app.open_view(mode={"d": "detail", "i": "impact", "m": "writing", "p": "provenance"}[event])
            app.reading_relation = False
        elif event == "s":
            plans = [node for node in app.view["nodes"] if node["kind"] == "experiment-plan"]
            if plans:
                self.plan_index = next((i for i, node in enumerate(plans) if node["id"] == app.selected_id), 0)
                self.modal = "scenario"
        elif event in ("e", "E"):
            draft = app.draft()
            values = app.unfinished.get((*app.work_key(), "edit")) if event == "E" else None
            self.buffers, self.field, self.modal = [Buffer(t) for t in (values or [draft["text"], draft["rationale"]])], 0, "edit"
        elif event in ("n", "N"):
            self.note_return_context, self.note_return_depth = app._navigation(), len(app.trail)
            app.open_view()
            values = app.unfinished.get((*app.context_key(), "note")) if event == "N" else None
            self.buffers, self.modal = [Buffer((values or [app.note()])[0])], "note"
        elif event == "/":
            self.buffers, self.modal = [Buffer(app.search)], "search"
        return None

    def checkpoint(self):
        covered = (None, 'note', 'edit', 'search', 'save-status', 'help', 'actions', 'quit', 'recovery', 'project-source', 'project-source-location', 'project-source-preview', 'personal-preview', 'personal-graph') + (('candidate-text', 'intake-text', 'review-fields', 'review-answer', 'review-writing-source') if encrypted_judgments(self.app) else ())
        covered_authoring = encrypted_judgments(self.app) and bool(self.modal and (
            self.modal.startswith(('candidate-', 'intake-', 'understanding-')) or self.modal in
            ('manuscript-wording', 'manuscript-source', 'manuscript-basis', 'manuscript-reason')))
        covered_personal = personal(self.app) and self.modal in (
            'personal-explanation-edit','personal-explanation-source')
        self.app.uncheckpointed_editor = (self.modal not in covered and not covered_authoring and not covered_personal and
                                         any(b.text != b.initial for b in self.buffers))
        if not self.app.recovery:
            return True
        active = ((self.modal, [b.text for b in self.buffers]) if self.modal in ("note", "edit") and
                  any(b.text != b.initial for b in self.buffers) else None)
        try:
            if self.modal == 'personal-explanation-edit' or (self.modal == 'personal-explanation-source' and self._personal_ui.explanation_return == 'personal-explanation-edit'):
                from .tui_personal import personal_ui
                personal_ui(self).checkpoint_explanation()
            if encrypted_judgments(self.app) and self.modal == 'candidate-text':
                from copy import deepcopy
                from .tui_candidates_ui import set_field
                ui = self._candidates_ui
                if self.buffers[0].text != self.buffers[0].initial:
                    record = deepcopy(ui.record)
                    set_field(record['body'], ui.editing, self.buffers[0].text)
                    active = ('candidate', (ui.owner_key, record))
            elif encrypted_judgments(self.app) and self.modal == 'intake-text':
                ui = self._intake_ui
                if self.buffers[0].text != self.buffers[0].initial:
                    active = ('intake', (ui.entry_id, ui.editing, self.buffers[0].text))
            elif encrypted_judgments(self.app) and self.modal in ('understanding-edit', 'understanding-source'):
                ui = self._understanding_ui
                if self.buffers[0].text != self.buffers[0].initial:
                    key = ui.buffer_key(ui.work.session.state())
                    active = ('understanding', (*key, self.buffers[0].text))
            elif encrypted_judgments(self.app) and self.modal in ('review-fields', 'review-answer', 'review-writing-source'):
                if any(b.text != b.initial for b in self.buffers):
                    active = ('review', self._review_ui.input_snapshot())
            elif encrypted_judgments(self.app) and self.modal in ('manuscript-wording', 'manuscript-source', 'manuscript-basis', 'manuscript-reason'):
                if any(b.text != b.initial for b in self.buffers):
                    mode = 'source' if self.modal == 'manuscript-source' else 'wording'
                    active = ('manuscript', (self.app.manuscript.work_id, mode, [b.text for b in self.buffers], self.field))
            self.app.recovery.save(self.app, active)
            if getattr(self.app, "recovery_error", None):
                self.app.message = "Private draft checkpoint saved. Nothing accepted."
            self.app.recovery_error = None
            return True
        except (OSError, ValueError) as error:
            previous = getattr(self.app, 'recovery_error', None)
            self.app.recovery_error = (recovery_copy(self.app, save_failure_message(error)) if encrypted_judgments(self.app) else
                "Draft save failed. Text remains in memory; q retries. Ctrl+C exits with the last checkpoint. " + str(error))
            if previous != self.app.recovery_error:
                self.app.message = self.app.recovery_error
            return False

    def loop(self):
        try:
            escape_delay = max(1, min(2000, int(os.environ.get("ESCDELAY", "35"))))
        except ValueError:
            escape_delay = 35
        self.curses.set_escdelay(escape_delay)
        self.curses.raw()  # Receive Ctrl+S without SSH flow-control freezing output.
        self.curses.typeahead(-1)  # Finish each frame even when unused keys are queued.
        self.screen.scrollok(False)
        self.screen.keypad(True)
        self.screen.timeout(100)
        sys.stdout.write("\x1b[?2004h")
        sys.stdout.flush()
        try:
            self.paint()
            last_checkpoint = time.monotonic()
            while True:
                event = self.read()
                if self.app.review.poll():
                    self.paint()
                if hasattr(self, '_proposals_ui') and self._proposals_ui.poll():
                    self.paint()
                if event is None:
                    previous = getattr(self.app, "recovery_error", None)
                    if self.app.recovery and (not encrypted_judgments(self.app) or time.monotonic() - last_checkpoint >= 1):
                        self.checkpoint()
                        last_checkpoint = time.monotonic()
                        if bool(previous) != bool(getattr(self.app, "recovery_error", None)):
                            self.paint()
                    continue
                if (not self.modal and isinstance(event, str) and event not in
                        {"interrupt", "suspend", "redraw", "resize", "tab", "backtab", "up", "down", "left", "right",
                         "page-up", "page-down", "home", "end", "enter", "escape", *"q?jk ofHJKLg12[]vzbru dimpsenNEU/Pla+-=wAcRyxGBtWCM,;"}):
                    continue
                code = self.key(event)
                if code is not None:
                    return code
                if event in ("keep", "escape") or (not encrypted_judgments(self.app) and time.monotonic() - last_checkpoint >= .25):
                    self.checkpoint()
                    last_checkpoint = time.monotonic()
                if encrypted_judgments(self.app):
                    last_checkpoint = time.monotonic()
                self.paint()
        finally:
            try:
                try:
                    if hasattr(self, '_proposals_ui'): self._proposals_ui.shutdown()
                finally:
                    self.checkpoint()
            finally:
                sys.stdout.write("\x1b[?2004l")
                sys.stdout.flush()


def run_terminal(history, *, layout="two", navigation="graph", snapshot=False, draft_file=None, ai_off=False,
                 work_dir=None, create_work=False, workspace=None):
    if (create_work and not work_dir) or (work_dir and (draft_file or snapshot or history.schema_version != 3)):
        print("Use --work-dir with --series or --merge-example, without --draft-file/--snapshot; --create-work requires --work-dir.", file=sys.stderr)
        return 2
    if workspace is not None and (work_dir or draft_file or create_work or snapshot):
        raise ValueError('A prepared project workspace owns its recovery connection.')
    app = workspace if workspace is not None else TerminalWorkspace(history, layout, navigation=navigation, ai_off=ai_off)
    if snapshot:
        if draft_file:
            print("--draft-file requires the interactive terminal; snapshots never write drafts.", file=sys.stderr)
            return 2
        print(render_snapshot(app))
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("A TTY is required. Run inside your terminal/SSH session (ssh -t), or use --snapshot for plain text.", file=sys.stderr)
        return 2
    if os.environ.get("TERM", "dumb") in ("", "dumb", "unknown"):
        print("A cursor-addressable TERM is required. Use --snapshot for this terminal.", file=sys.stderr)
        return 2
    try:
        import curses
    except ImportError:
        print("This prototype needs Python with curses (Linux/macOS). Use --snapshot for plain text.", file=sys.stderr)
        return 2
    import termios
    if draft_file:
        from .tui_recovery import DraftRecovery
        try:
            app.recovery = DraftRecovery(draft_file, app)
        except (OSError, ValueError) as error:
            print("Draft recovery unavailable: " + str(error), file=sys.stderr)
            return 2
    if work_dir:
        from .tui_work_recovery import JudgmentRecovery
        try:
            app.recovery = JudgmentRecovery.open(work_dir, app, create=create_work)
        except (OSError, ValueError, EOFError) as error:
            print("Judgment recovery unavailable: " + str(error), file=sys.stderr)
            return 2
    descriptor = sys.stdin.fileno()
    original_modes = termios.tcgetattr(descriptor)
    size_environment = {key: os.environ.pop(key) for key in ("LINES", "COLUMNS") if key in os.environ}
    try:
        try:
            locale.setlocale(locale.LC_ALL, "")
            code = curses.wrapper(lambda screen: Terminal(screen, app, curses).loop())
        finally:
            os.environ.update(size_environment)
            # Restore caller-selected modes even on a rendering error. Darwin's
            # transient PENDIN state clears on the surrounding shell's next read.
            termios.tcsetattr(descriptor, termios.TCSANOW, original_modes)
            if app.recovery:
                app.recovery.close()
    except (curses.error, locale.Error) as error:
        print("Terminal initialization/rendering failed: " + str(error) + ". Try --snapshot.", file=sys.stderr)
        return 2
    state = ("Private drafts saved." if not getattr(app, "recovery_error", None) else "Draft save failed; last checkpoint retained.") if app.recovery else "Session drafts and notes discarded."
    if app.recovery and app.review.volatile_work() and not getattr(app, 'recovery_error', None):
        state = 'Manual graph judgments and notes saved at their original nodes. Unconfirmed result drafts, judgment links, explanation drafts, unfinished change/explanation text, session-only AI work, change reviews, manuscript wording and branch/merge candidates discarded.'
    if encrypted_judgments(app) and getattr(app, 'recovery_error', None):
        state = 'Judgment save not confirmed. Reopen to inspect saved writing; later input may be lost.'
    if encrypted_judgments(app) and not getattr(app, 'recovery_error', None):
        state = 'Judgments, AI origin, notes, links, argument/result drafts, partial explanations, unfinished scientific-review input and manuscript wording/source input saved.'
        excluded = excluded_work(app)
        if excluded:
            state += ' Session-only work discarded: ' + ', '.join(excluded) + '.'
    boundary = (' Personal work uses local files without application encryption; manuscript files were not changed.'
                if personal(app) else ' Research records and manuscript files were not changed.')
    print("ClaimBranch closed. " + state + boundary)
    return code
