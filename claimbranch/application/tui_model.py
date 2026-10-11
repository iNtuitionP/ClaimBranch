"""Disposable terminal projection of the synthetic paper, never a scientific writer."""
from .tui_retention import recovery_copy
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
import difflib
import hashlib
import json
import unicodedata

from .paper_workspace import PaperWorkspace
from .tui_cards import overview_copy
from .tui_review import TerminalReview, FROZEN_CRITIQUE


def clean(text):
    """Render text as data, including when it contains terminal escape controls."""
    return "".join(c for c in unicodedata.normalize("NFC", str(text))
                   if c in "\n\t" or not unicodedata.category(c).startswith("C")).expandtabs(4)


@lru_cache(maxsize=4096)
def char_width(char):
    return 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in "WF" else 1


def cell_width(text):
    return sum(char_width(c) for c in clean(text))


def clip(text, width, *, ellipsis=True):
    text = clean(text).replace("\n", " ")
    if width <= 0:
        return ""
    if cell_width(text) <= width:
        return text
    budget = width - (1 if ellipsis else 0)
    result, used = [], 0
    for c in text:
        size = char_width(c)
        if used + size > budget:
            break
        result.append(c)
        used += size
    return "".join(result) + ("…" if ellipsis else "")


def wrap(text, width):
    width = max(2, width)
    lines = []
    for paragraph in clean(text).split("\n"):
        current = ""
        for word in paragraph.split():
            if current and cell_width(current + " " + word) <= width:
                current += " " + word
                continue
            if current:
                lines.append(current)
                current = ""
            while cell_width(word) > width:
                chunk = clip(word, width, ellipsis=False)
                lines.append(chunk)
                word = word[len(chunk):]
            current = word
        lines.append(current)
    return lines or [""]


@dataclass(frozen=True)
class Row:
    node_id: str
    depth: int = 0
    path: tuple = ()
    parent_id: str | None = None
    edges: tuple = ()
    reference: bool = False
    unlinked: bool = False


@dataclass(frozen=True)
class Link:
    target_id: str
    kind: str
    outgoing: bool
    scientific: bool
    rationale: str
    key: str = ""
    draft: bool = False


KINDS = {"claim": "CLAIM", "observation": "EVIDENCE", "experiment-plan": "PLAN",
         "experiment-record": "RUN", "interpretation": "READING", "manuscript-anchor": "WRITING"}


class TerminalWorkspace:
    def __init__(self, history, layout="two", *, navigation="graph", ai_off=False):
        self.history_digest = hashlib.sha256(history.manifest()).hexdigest()
        self.paper = PaperWorkspace(history, frozen_response=None if ai_off else FROZEN_CRITIQUE)
        self.paper._checkpoint_app = self
        from .paper_intake import PaperResultIntake
        self.intake = PaperResultIntake(self.paper)
        self.service = self.paper.service
        self.series = history.schema_version == 3
        self._contexts = {}
        self.ref = "main"
        self.layout = layout
        self.navigation = navigation
        self.graph_view = "overview"
        self.graph_pinned = False
        self.graph_spacing = "balanced"
        self.graph_fullscreen = False
        self.graph_root = None
        self.graph_depth = 1
        self.graph_size = (130, 23)
        self.graph_pan = (0, 0)
        self.graph_follow = True
        self.density = "compact" if navigation == "graph" else "comfortable"
        self.lens = "argument"
        self.evidence_root = None
        self._evidence_labels = {}
        self._lens_contexts = {}
        self.view = self.service.query(self.ref)
        self.nodes = {node["id"]: node for node in self.view["nodes"]}
        self.selected_id = self.view["thesis_id"]
        self._build_outline()
        self.selected_path = self._paths[self.selected_id]
        # Open one argument path. Sibling branches and experiment detail stay
        # foldable so a spaced first viewport still exposes the thesis structure.
        expanded, key = set(), self.selected_id
        while key not in expanded:
            expanded.add(key)
            claims = [child for child in self.children(key) if self.nodes[child]["kind"] == "claim"]
            if not claims:
                break
            key = claims[0]
        self.collapsed = {key for key in self.nodes if self.children(key) and key not in expanded}
        self.search = ""
        self.trail = []
        self.drafts = {}
        self.review = TerminalReview(self, history)
        from .tui_manuscript import TerminalManuscript
        self.manuscript = TerminalManuscript(self)
        from .tui_understanding import TerminalUnderstanding
        self.understanding = TerminalUnderstanding(self)
        from .tui_branch import TerminalBranches
        self.branches = TerminalBranches(self)
        self.notes = {}
        self.unfinished = {}
        self.recovery = None
        self.scenario = None
        self.mode = "detail"
        self.focus = "outline"
        self.reading_relation = False
        self.link_scope = "all"
        self.link_index = 0
        self.scroll = 0
        self.nav_scroll = 0
        self.message = "Arrows move spatially. r follows edges. f fits the map; l shows a neighborhood."

    def title(self, node_id):
        node = self.nodes[node_id]
        content = node["content"]
        if node["kind"] == "manuscript-anchor":
            return "Manuscript connection to the paper thesis"
        return content.get("statement") or content.get("objective") or content.get("question") or node_id

    def kind(self, node_id):
        node = self.nodes[node_id]
        if node["kind"] == "claim":
            return node["content"].get("role", "claim").upper()
        return KINDS[node["kind"]]

    def node_label(self, node_id):
        """Stable aliases over this fixture, independent of lens or selection."""
        if node_id in getattr(self, '_label_overrides', {}):
            return self._label_overrides[node_id]
        kind = self.nodes[node_id]["kind"]
        if self.kind(node_id) == "THESIS":
            return "T"
        keys = sorted(key for key, node in self.nodes.items()
                      if node["kind"] == kind and self.kind(key) != "THESIS")
        prefix = {"claim": "C", "observation": "E", "experiment-plan": "P",
                  "experiment-record": "R", "interpretation": "I", "manuscript-anchor": "W"}[kind]
        return prefix + str(keys.index(node_id) + 1)

    def caption(self, node_id):
        """A visibly abbreviated source excerpt, never an inferred proposition."""
        title = self.title(node_id)
        if title.startswith(("On ", "With ")) and ", " in title:
            return "…" + title.split(", ", 1)[1]
        return title

    def evidence_ids(self):
        return sorted(key for key, node in self.nodes.items() if node["kind"] == "observation")

    def evidence_label(self, node_id):
        for key in self.evidence_ids():
            if key not in self._evidence_labels:
                self._evidence_labels[key] = f"E{len(self._evidence_labels) + 1}"
        count = len({link.target_id for link in self.claim_uses(node_id)})
        return f"{self._evidence_labels[node_id]} · {count} claim{'s' if count != 1 else ''}"

    def claim_uses(self, node_id=None):
        key = node_id or self.selected_id
        if self.nodes[key]["kind"] != "observation":
            return []
        return [link for link in self.links(key) if link.scientific and link.outgoing
                and self.nodes[link.target_id]["kind"] == "claim"]

    def _build_outline(self):
        """Unfold recorded links, retaining cross-links as finite references.

        Placement is a reading projection: relation dictionaries and their
        source/target direction are never changed to fit the outline.
        """
        groups = {}
        for edge in self.view["relations"]:
            pair = tuple(sorted((edge["source_id"], edge["target_id"])))
            groups.setdefault(pair, []).append(edge)
        oriented = {}
        for pair, edges in groups.items():
            edges.sort(key=lambda edge: (not edge["scientific"], edge["type"], edge["key"]))
            structural = next((edge for edge in edges if edge["type"] == "part-of"), edges[0])
            if self.lens == "evidence":
                use = next((edge for edge in edges if edge["source_id"] == self.evidence_root
                            and edge["scientific"] and self.nodes[edge["target_id"]]["kind"] == "claim"), None)
                if use:
                    oriented[pair] = (self.evidence_root, use["target_id"])
                elif all(self.nodes[key]["kind"] == "claim" for key in pair):
                    oriented[pair] = (structural["source_id"], structural["target_id"])
            else:
                oriented[pair] = (structural["target_id"], structural["source_id"])

        def reachable():
            seen, pending = set(), [self.view["thesis_id"]]
            while pending:
                key = pending.pop()
                if key in seen:
                    continue
                seen.add(key)
                pending.extend(child for parent, child in oriented.values() if parent == key)
            return seen

        # An outgoing-only attachment is still visible. Reverse *placement*,
        # not the stored edge; its visible arrow then points down to the child.
        seen = reachable()
        while self.lens == "argument":
            attachment = next(((pair, parent, child) for pair, (parent, child) in oriented.items()
                               if child in seen and parent not in seen), None)
            if attachment is None:
                break
            pair, parent, child = attachment
            oriented[pair] = (child, parent)
            seen = reachable()

        self._children = {key: [] for key in self.nodes}
        self._edge_groups = {}
        for pair, (parent, child) in oriented.items():
            self._children[parent].append(child)
            self._edge_groups[(parent, child)] = tuple(groups[pair])
        order = {"claim": 0, "observation": 1, "experiment-record": 2,
                 "experiment-plan": 3, "interpretation": 4, "manuscript-anchor": 5}

        def priority(key):
            nested_claim = any(self.nodes[child]["kind"] == "claim" for child in self._children[key])
            return (order[self.nodes[key]["kind"]], not nested_claim, key)

        for children in self._children.values():
            children.sort(key=priority)
        self._outline_rows, self._paths = [], {}
        root = self.evidence_root if self.lens == "evidence" else self.view["thesis_id"]
        primary_paths = {root: (root,)}
        if self.lens == "evidence":
            # A direct use owns its first-level position even if an earlier
            # branch also reaches that claim through a longer argument path.
            pending = deque([root])
            while pending:
                key = pending.popleft()
                for child in self.children(key):
                    if child not in primary_paths:
                        primary_paths[child] = primary_paths[key] + (child,)
                        pending.append(child)

        def add(key, path, *, unlinked=False):
            parent = path[-2] if len(path) > 1 else None
            reference = path != primary_paths[key] if self.lens == "evidence" else key in self._paths
            self._outline_rows.append(Row(key, len(path) - 1, path, parent,
                                          self._edge_groups.get((parent, key), ()), reference, unlinked))
            if reference:
                return
            self._paths[key] = path
            for child in self.children(key):
                add(child, path + (child,), unlinked=unlinked)

        add(root, (root,))
        if self.lens == "argument":
            for key in sorted(self.nodes):
                if key not in self._paths:
                    add(key, (key,), unlinked=True)
        self._row_by_path = {row.path: row for row in self._outline_rows}
        self.occurrences = {key: sum(row.node_id == key for row in self._outline_rows) for key in self.nodes}

    def children(self, node_id):
        return self._children[node_id]

    def matching_ids(self):
        if self.search in self.nodes:
            return {self.search}
        needle = self.search.casefold()
        return {key for key, node in self.nodes.items()
                if needle in json.dumps(node, ensure_ascii=False).casefold() or needle in self.note(key).casefold()
                or needle in ' '.join(overview_copy(self, key) or ()).casefold()}

    def rows(self):
        if self.search:
            matches = self.matching_ids()
            paths = {row.path[:index] for row in self._outline_rows if row.node_id in matches
                     for index in range(1, len(row.path) + 1)}
            return [row for row in self._outline_rows if row.path in paths]
        return [row for row in self._outline_rows if not any(key in self.collapsed for key in row.path[:-1])]

    def selected_row(self):
        return self._row_by_path[self.selected_path]

    def graph_rows(self):
        return self._outline_rows

    def graph_ids(self):
        """Explicit neighborhood; moving selection never moves its root."""
        available = {row.node_id for row in self.graph_rows()}
        if self.graph_root not in available:
            return available
        result = {self.graph_root}
        for _ in range(self.graph_depth):
            result |= {other for edge in self.view['relations']
                       if edge['source_id'] in result or edge['target_id'] in result
                       for other in (edge['source_id'], edge['target_id']) if other in available}
        return result

    def scope_graph(self, root=None, depth=1):
        if (root, depth) == (self.graph_root, self.graph_depth) and self.focus == 'outline':
            return
        self.trail.append(self._navigation())
        self.graph_root, self.graph_depth = root, depth
        self.graph_view, self.focus = 'overview', 'outline'
        self.graph_pan, self.graph_follow = (0, 0), True
        if self.selected_id not in self.graph_ids():
            self.select(root, remember=False)
        self.message = ("Local view stays rooted here. +/- changes depth; a shows all. Esc restores the map."
                        if root else "All nodes in this lens. f fits; Esc restores the neighborhood.")

    def fit_graph(self):
        previous = self._navigation()
        self.graph_view, self.graph_fullscreen = 'overview', True
        self.navigation, self.focus, self.density = 'graph', 'outline', 'compact'
        self.graph_pan, self.graph_follow = (0, 0), True
        if previous != self._navigation():
            self.trail.append(previous)
        self.message = "Fit current scope. If clipped, l opens a neighborhood; a shows all. Esc restores your view."

    def _navigation(self):
        names = ("navigation", "lens", "evidence_root", "selected_id", "selected_path", "search", "focus",
                 "mode", "reading_relation", "link_scope", "link_index", "scroll", "nav_scroll",
                 "graph_pan", "graph_follow", "graph_view", "graph_fullscreen", "graph_root", "graph_depth", "density")
        return {**{name: getattr(self, name) for name in names}, "collapsed": set(self.collapsed)}

    def _restore_navigation(self, context):
        for name, value in context.items():
            setattr(self, name, set(value) if name == "collapsed" else value)
        self._build_outline()

    def switch_lens(self, lens, *, evidence_id=None):
        if lens not in ("argument", "evidence"):
            raise ValueError("Unknown reading view")
        root = None
        if lens == "evidence":
            evidence = self.evidence_ids()
            if not evidence:
                self.message = "No observations in this branch. Argument view stays open."
                return
            root = evidence_id
            if root is None:
                root = self.selected_id if self.selected_id in evidence else self.evidence_root
                if root not in evidence:
                    root = next((key for key in evidence if any(link.target_id == self.selected_id
                                for link in self.claim_uses(key))), evidence[0])
            if root not in evidence:
                raise ValueError("Evidence view needs an observation")
        if (lens, root) == (self.lens, self.evidence_root):
            return
        previous = self._navigation()
        self._lens_contexts[(self.lens, self.evidence_root)] = previous
        cached = self._lens_contexts.get((lens, root))
        if cached:
            self._restore_navigation(cached)
        else:
            self.lens, self.evidence_root = lens, root
            self.graph_root, self.graph_depth, self.graph_pan = None, 1, (0, 0)
            self._build_outline()
            self.collapsed = {key for key in self.nodes if self.children(key) and key != root}
        # Keep the same node wherever the destination view represents it.
        # Cached occurrence paths distinguish repeated evidence on return.
        target = (root if evidence_id or lens == "evidence" and
                  self.nodes[previous["selected_id"]]["kind"] != "observation" else previous["selected_id"])
        if target not in self._paths:
            target = root or self.view["thesis_id"]
        path = self.selected_path if cached and self.selected_id == target else None
        self.select(target, path=path, remember=False)
        self.focus, self.mode = previous["focus"], previous["mode"]
        self.nav_scroll = 0 if not cached else self.nav_scroll
        self.trail.append(previous)
        self.message = ("Evidence uses · direct claims first; expand for further argument paths."
                        if lens == "evidence" else "Argument view · same records and drafts. Esc returns.")
        if lens == "evidence" and self.navigation == "graph":
            self.message = "Evidence graph · one observation and its recorded claim paths. Enter reads; r inspects edges."

    def cycle_evidence(self, amount):
        evidence = self.evidence_ids()
        if self.lens != "evidence" or not evidence:
            return
        index = evidence.index(self.evidence_root)
        self.switch_lens("evidence", evidence_id=evidence[(index + amount) % len(evidence)])

    def select(self, node_id, *, path=None, remember=True, reveal=True):
        if node_id not in self.nodes:
            return
        previous = self._navigation()
        if node_id not in self._paths:
            self._lens_contexts[(self.lens, self.evidence_root)] = previous
            self.lens, self.evidence_root = "argument", None
            self._build_outline()
            cached = self._lens_contexts.get(("argument", None))
            if cached:
                self.collapsed = set(cached["collapsed"])
        path = path if path in self._row_by_path and path[-1] == node_id else self._paths[node_id]
        if remember and (previous["lens"], previous["selected_path"]) != (self.lens, path):
            previous["search"] = ""  # Following a result leaves its temporary search.
            self.trail.append(previous)
        if node_id not in self.graph_ids():
            self.graph_root, self.graph_depth, self.graph_pan = None, 1, (0, 0)
        self.selected_id = node_id
        self.selected_path = path
        self.graph_follow = True
        self.reading_relation = False
        self.link_scope = "uses" if self.nodes[node_id]["kind"] == "observation" else "all"
        if reveal:
            self.search = ""
            self.collapsed.difference_update(path[:-1])
        self.link_index = self.scroll = 0

    def move(self, amount):
        rows = self.rows()
        if not rows:
            return
        paths = [row.path for row in rows]
        index = paths.index(self.selected_path) if self.selected_path in paths else -1
        row = rows[max(0, min(len(rows) - 1, index + amount))]
        self.select(row.node_id, path=row.path, remember=False, reveal=False)

    def toggle_collapsed(self):
        if self.search:
            self.message = "Search keeps matching paths open. Esc clears it before folding."
            return
        if self.children(self.selected_id) and not self.selected_row().reference:
            if self.selected_id in self.collapsed:
                self.collapsed.remove(self.selected_id)
            else:
                self.collapsed.add(self.selected_id)

    def left(self):
        row = self.selected_row()
        if not self.search and self.children(row.node_id) and not row.reference and row.node_id not in self.collapsed:
            self.collapsed.add(row.node_id)
        elif row.parent_id:
            self.select(row.parent_id, path=row.path[:-1], reveal=not bool(self.search))

    def right(self):
        row = self.selected_row()
        if row.reference:
            self.jump_to_original()
        elif self.search:
            child = next((item for item in self.rows() if item.path[:-1] == row.path), None)
            if child:
                self.select(child.node_id, path=child.path, reveal=False)
        elif self.children(row.node_id):
            if row.node_id in self.collapsed:
                self.collapsed.remove(row.node_id)
            else:
                child = self.children(row.node_id)[0]
                self.select(child, path=row.path + (child,))

    def jump_to_original(self):
        if self.selected_row().reference:
            self.select(self.selected_id)
            self.collapsed.discard(self.selected_id)
            self.message = "Same record, primary occurrence. Esc returns to the shared reference."

    def inspect_parent_edge(self):
        row = self.selected_row()
        self.link_scope = "all"
        if row.edges:
            self.link_index = next(i for i, link in enumerate(self.links()) if link.key == row.edges[0]["key"])
        self.reading_relation, self.mode, self.scroll = True, "detail", 0
        self.focus = "detail" if row.edges else "links"

    def links(self, node_id=None):
        node_id = node_id or self.selected_id
        result = []
        for edge in self.view["relations"]:
            if node_id not in (edge["source_id"], edge["target_id"]):
                continue
            outgoing = edge["source_id"] == node_id
            target = edge["target_id"] if outgoing else edge["source_id"]
            result.append(Link(target, edge["type"], outgoing, edge["scientific"], edge["rationale"] or "", edge["key"], edge.get('draft', False)))
        return sorted(result, key=lambda link: (not link.scientific, link.kind, link.target_id))

    def display_links(self):
        return self.claim_uses() if self.link_scope == "uses" else self.links()

    def follow(self, link):
        self.select(link.target_id)
        self.message = "Followed the same node. Esc returns to the previous selection."

    def back(self):
        if (self.trail and self.trail[-1]["selected_id"] == self.selected_id and
                any(self.trail[-1][name] != getattr(self, name) for name in
                    ('focus', 'graph_view', 'graph_root', 'graph_depth', 'graph_pan',
                     'graph_follow', 'graph_fullscreen', 'density', 'navigation'))):
            self._restore_navigation(self.trail.pop())
        elif self.search:
            self.select(self.selected_id, path=self.selected_path, remember=False)
        elif self.trail:
            self._restore_navigation(self.trail.pop())

    def open_view(self, focus="detail", mode="detail"):
        if (self.focus, self.mode) != (focus, mode) or self.graph_view == "overview":
            self.trail.append(self._navigation())
        self.graph_view = "workspace"
        self.focus, self.mode, self.scroll = focus, mode, 0

    def switch_ref(self):
        self.switch_context(self.episode_id, "alternative" if self.ref == "main" else "main")

    @property
    def episode_id(self):
        return self.view['episode_id']

    def context_key(self, node_id=None):
        suffix = (self.ref, node_id or self.selected_id)
        return (self.episode_id, *suffix) if self.series else suffix

    def open_context_key(self, key):
        episode, ref, node = key if self.series else (self.episode_id, *key)
        self.switch_context(episode, ref)
        self.select(node, remember=False)

    def full_context(self, key):
        return tuple(key) if self.series else (self.episode_id, *key)

    def work_key(self):
        owner = self.paper.work_owner(self.episode_id, self.ref, self.selected_id)
        return owner if self.series else owner[1:]

    def writing_key(self, mode):
        return self.work_key() if mode == 'edit' else self.context_key()

    def open_work_key(self, key):
        owner = self.full_context(key)
        changed = self.paper.work_owner(*owner) != owner
        self.paper.activate_work(owner, owner[2])
        self.open_context_key(key)
        if changed:
            self.message = 'Returned to judgment ' + self.node_label(owner[2]) + '; this node now shows it. Other judgments remain in ; actions.'

    def work_labels(self):
        owner = self.full_context(self.work_key())
        return ', '.join(self.node_label(key) + (' (different judgment)' if self.paper.work_owner(*owner[:2], key) != owner else '')
                         for key in self.paper.work_nodes(owner))

    def switch_context(self, episode_id, ref, *, refresh=False):
        # Query before mutating state so an invalid target cannot lose context.
        view = self.service.query(ref, episode_id=episode_id)
        if not refresh and (episode_id, ref) == (self.episode_id, self.ref):
            return
        self._contexts[(self.episode_id, self.ref)] = (self._navigation(), list(self.trail), dict(self._lens_contexts))
        self.ref, self.view = ref, view
        self.nodes = {node["id"]: node for node in self.view["nodes"]}
        self._lens_contexts = {}
        if self.lens == "evidence" and self.evidence_root not in self.evidence_ids():
            self.lens, self.evidence_root = "argument", None
        self._build_outline()
        if self.graph_root not in self.nodes:
            self.graph_root = None
        if self.selected_id not in self.nodes:
            self.selected_id = self.view["thesis_id"]
        self.select(self.selected_id, path=self.selected_path, remember=False)
        self.scenario = None
        self.trail.clear()
        self.search = ""
        self.scroll = self.link_index = 0
        cached = self._contexts.get((episode_id, ref))
        if cached:
            context, self.trail, self._lens_contexts = cached
            self.trail, self._lens_contexts = list(self.trail), dict(self._lens_contexts)
            self._restore_navigation(context)
        self.message = "Context changed; what-if cleared. Notes and judgments stay with their episode / branch / node."

    def draft(self):
        if self.review.key in self.review.buffers:
            return dict(self.review.buffers[self.review.key])
        session = self.review.sessions.get(self.review.key)
        if session:
            draft = session.state()['draft']
            return {key: draft[key] for key in ('text', 'rationale')}
        return dict(self.drafts.get(self.work_key(), {"text": "", "rationale": ""}))

    def note(self, node_id=None):
        return self.notes.get(self.context_key(node_id), "")

    def keep_note(self, text):
        if len(text) > 12000:
            raise ValueError("Keep a node note within 12,000 characters.")
        self.notes[self.context_key()] = clean(text)
        self.message = "Note kept in this session. ✎ marks its card; n edits, z changes card density."
        self.mode, self.scroll, self.reading_relation = "detail", 0, False

    def keep_draft(self, text, rationale):
        if len(text) > 12000 or len(rationale) > 12000:
            raise ValueError("Keep each draft field within 12,000 characters.")
        value = {"text": clean(text), "rationale": clean(rationale)}
        reviewable = self.review.edit_draft(value)
        if not self.review.influenced():
            self.drafts[self.work_key()] = value
        self.message = ("AI-influenced draft kept for this session only; w reviews its contributions."
                        if self.review.influenced() else "Draft kept. w connects it to AI and scientific change review.")
        if not reviewable:
            self.message = self.review.buffer_notices[self.review.key]
        self.mode = "draft"
        self.scroll = 0

    def preview_scenario(self, plan_id, outcome):
        plan = self.nodes[plan_id]["content"]
        assumption = {"supports": "Assume the unrun experiment supports its target claim under the stated conditions.",
                      "challenges": "Assume the unrun experiment challenges its target claim under the stated conditions.",
                      "inconclusive": "Assume the unrun experiment cannot resolve its target claim."}[outcome]
        self.scenario = self.service.scenario({"schema_version": 1,
            "project_id": self.view["project_id"], "episode_id": self.view["episode_id"],
            "ref": self.ref, "view_digest": self.view["digest"], "plan_id": plan_id,
            "outcome": outcome, "assumed_observation": assumption,
            "rationale": "Synthetic conditional exploration: " + plan["objective"]})
        self.mode = "impact"
        self.scroll = 0
        self.message = "~ possible review path; = outside this path. No experiment ran and no evidence changed."

    def marker(self, node_id):
        if not self.scenario:
            return ""
        if node_id in self.scenario["potentially_affected_claim_ids"]:
            return "~ "
        if node_id in self.scenario["unaffected_claim_ids"]:
            return "= "
        return ""

    def relationship_detail(self):
        links = self.display_links()
        if not links:
            return [("NO CLAIM USES" if self.link_scope == "uses" else "NO CONNECTIONS", "heading"),
                    ("No direct scientific claim uses. Press r for all connections."
                     if self.link_scope == "uses" else "This node has no recorded relationships.", "muted")]
        link = links[max(0, min(self.link_index, len(links) - 1))]
        source = self.selected_id if link.outgoing else link.target_id
        target = link.target_id if link.outgoing else self.selected_id
        return [(link.kind.upper() + (' / DRAFT' if link.draft else ''), "heading"),
                ("Scientific relation" if link.scientific else "Structural reference · not scientific support", "muted"),
                ("", "body"), ("FROM / " + self.node_label(source), "heading"), (self.title(source), "body"),
                ("", "body"), ("TO / " + self.node_label(target), "heading"), (self.title(target), "body"),
                ("", "body"), ("RATIONALE", "heading"),
                (link.rationale or "No rationale supplied.", "body"),
                ("", "body"), ("Enter follows the connected node. Esc returns along your path.", "muted")]

    def detail(self, mode=None, *, include_links=True, width=72):
        mode = mode or self.mode
        if mode == 'work':
            return self.review.lines(width)
        node = self.nodes[self.selected_id]
        content = node["content"]
        lines = []

        def section(title, body, style="body"):
            lines.extend([(title, "heading"), (str(body), style), ("", "body")])

        if mode == "impact":
            if not self.scenario:
                section("WHAT IF?", "Press s to choose a hypothetical result for an unrun experiment.")
                section("No preview active", "Accepted evidence and reasoning remain unchanged.", "muted")
                return lines
            value = self.scenario
            section("HYPOTHETICAL / " + value["assumption"]["outcome"].upper(), value["assumption"]["observation"], "warning")
            section("UNRUN EXPERIMENT", self.title(value["assumption"]["plan_id"]))
            for path in value["witness_paths"]:
                section("~ POSSIBLE REVIEW PATH", "\n  → ".join(self.title(key) for key in path), "warning")
            section("= OUTSIDE THIS PATH", "\n\n".join(self.title(key) for key in value["unaffected_claim_ids"]) or "None")
            section("EVIDENCE STAYS", "Existing observations are unchanged. Reach identifies what to review; it does not establish a claim's truth.", "muted")
            return lines
        if mode == "provenance":
            judgment = self.view.get("judgment")
            section("RECORDED EPISODE JUDGMENT", "Frozen example history; this is separate from your local node draft.", "muted")
            if judgment:
                for index, entry in enumerate(judgment["history"], 1):
                    section(f"{index} / {entry['contributor'].upper()}", entry["text"])
                    section("RATIONALE", entry["rationale"], "muted")
                    if entry.get("proposal_id"):
                        section("PROPOSAL", entry["proposal_id"], "accent")
            else:
                section("No recorded judgment", "The example has no judgment on this branch.")
            return lines
        if mode in ("draft", "writing"):
            if len(self.paper.work_nodes(self.full_context(self.work_key()))) > 1:
                section('JUDGMENT OWNER / ' + self.node_label(self.work_key()[-1]),
                        'Linked: ' + self.work_labels() + ' · session-only links', 'accent')
            draft = self.draft()
            if mode == "writing":
                section("MANUSCRIPT CONNECTION", "The example links the paper thesis to an anchor. No manuscript source or exact file patch is supplied in this paper fixture.", "muted")
            section("YOUR SESSION DRAFT" + (" / AI-INFLUENCED" if self.review.influenced() else ""),
                    draft["text"] or "Press e to write a judgment about this node.")
            section("YOUR REASON", draft["rationale"] or "No rationale entered.", "muted")
            from .tui_work_recovery import enabled
            section("STATUS", getattr(self, 'recovery_error', None) or
                    (recovery_copy(self, "Encrypted judgment recovery enabled. Not accepted; origin retained.") if enabled(self) else
                     "In memory only. Not accepted; leaves original AI/human contribution history intact."), "warning")
            if self.review.influenced():
                section("CURRENT CONTRIBUTIONS", "w shows this draft's AI/human origin. " +
                        (recovery_copy(self, "Judgment and adopted AI origin are included in encrypted checkpoints.") if enabled(self) else
                         "This AI-influenced draft is not checkpointed."), "warning")
            if draft["text"]:
                section("TEXT COMPARISON / NOT A FILE PATCH", "\n".join(difflib.unified_diff(
                    wrap(self.title(self.selected_id), 58), wrap(draft["text"], 58),
                    fromfile="selected-argument", tofile="your-session-draft", lineterm="")))
            return lines
        lines.append((self.node_label(self.selected_id) + " / " + self.kind(self.selected_id), "heading"))
        if node["kind"] == "observation":
            lines.append((content["value"] + " " + content["metric"]["unit"] + " · " + content["metric"]["name"], "accent"))
        if content.get("conditions"):
            label = 'Run conditions: ' if node['kind'] == 'observation' else 'Conditions: '
            lines.append((label + content["conditions"], "muted"))
        if node["kind"] == "observation":
            uses = self.claim_uses()
            lines.extend([("", "body"), ("CLAIM USES / " + self.evidence_label(self.selected_id) + " · u choose", "heading")])
            for link in uses:
                lines.append((link.kind + " → " + self.node_label(link.target_id) + " · " +
                              clip(self.caption(link.target_id), 42), link.kind))
                if include_links:
                    lines.append((self.title(link.target_id), "body"))
            if not uses:
                lines.extend([("No direct scientific claim uses recorded.", "muted"), ("", "body")])
        lines.append(("", "body"))
        section('DRAFT STATEMENT / NOT ACCEPTED' if node.get('draft') else "SOURCE STATEMENT", self.title(self.selected_id))
        if self.note().strip():
            section("MY NOTE · n edit", self.note())
        elif not getattr(self, 'projection_only', False):
            lines.extend([("n writes a personal note for this node.", "muted"), ("", "body")])
        if content.get("scope"):
            section("SCOPE", content["scope"])
        if content.get("method"):
            section("METHOD", content["method"])
        if content.get("metric"):
            metric = content["metric"]
            section("MEASUREMENT / " + metric["name"], metric["definition"])
            section("UNIT", metric["unit"])
            section("COMPARISON", metric["comparison"])
        if content.get("source_ref"):
            section("SOURCE REFERENCE", content["source_ref"] + " (example reference; no artifact opened)", "muted")
        if node["kind"] == "experiment-plan":
            section("NOT RUN", ("No measured result. Scenarios on this draft graph are unavailable."
                               if getattr(self, 'projection_only', False) else
                               "Press s to explore a possible result. This app does not execute experiments."), "warning")
        if node["kind"] == "manuscript-anchor":
            section("SOURCE UNAVAILABLE", "No manuscript source or file patch is included in this paper example. Press m to inspect the connection.", "muted")
        for link in self.links() if include_links else []:
            direction = "→" if link.outgoing else "←"
            section(direction + " " + link.kind.upper(), self.title(link.target_id), "accent" if link.scientific else "muted")
            if link.rationale:
                lines.extend([(link.rationale, "muted"), ("", "body")])
        if not include_links:
            section("CONNECTIONS", f"{len(self.links())} typed connections · r to inspect their direction and rationale.", "muted")
        section("RECORD", self.selected_id + recovery_copy(self, " / synthetic, unverified candidate"), "muted")
        return lines
