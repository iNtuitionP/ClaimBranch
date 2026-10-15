"""A cell-based graph canvas over the existing read-only paper projection."""
from dataclasses import dataclass

from .tui_model import cell_width, char_width, clip, wrap
from .tui_cards import overview_copy


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int
    relation_rows: int = 0

    @property
    def center(self):
        return self.x + self.width // 2, self.y + self.height // 2

    def beside(self, x, y):
        return ((x in (self.x - 1, self.x + self.width) and self.y < y < self.y + self.height - 1)
                or (y in (self.y - 1, self.y + self.height) and self.x < x < self.x + self.width - 1))

    def outward(self, point):
        x, y = point
        return ((-1, 0) if x < self.x else (1, 0) if x >= self.x + self.width else
                (0, -1) if y < self.y else (0, 1))


@dataclass(frozen=True)
class Route:
    edge: dict
    points: tuple
    label_x: int
    label_width: int


def relation_phrase(edge, node_id, other_label):
    """Read the recorded edge from the card owner's perspective."""
    from claimbranch.core.graph_vocabulary import relation_label
    active = relation_label(edge['type'], node_id == edge['source_id'])
    return f"{active} {other_label}" + (' · draft' if edge.get('draft') else '')


def node_heading(app, key):
    label = app.evidence_label(key) if app.nodes[key]['kind'] == 'observation' else app.node_label(key) + ' ' + app.kind(key)
    if app.nodes[key]['kind'] == 'experiment-plan':
        label = app.node_label(key) + ' UNRUN PLAN'
    if app.nodes[key].get('draft'):
        label = app.node_label(key) + ' DRAFT ' + ('UNRUN PLAN' if app.nodes[key]['kind'] == 'experiment-plan' else app.kind(key))
    if app._row_by_path[app._paths[key]].unlinked:
        label = ('! ' if app.density == 'compact' else 'UNLINKED / ') + label
    fold = '▸ ' if key in app.collapsed and app.children(key) and not app.search else ''
    return ' ' + app.marker(key) + fold + label


def header_relations(heading, phrases, width):
    """Keep whole phrases beside the title, or in its reserved continuation band."""
    placements, row = [], 0
    for index, (text, style) in enumerate(phrases):
        if index == 0 and cell_width(heading + ' · ' + text) <= width:
            placements.append((cell_width(heading), 0, ' · ' + text, style))
        else:
            for line in wrap(text, width):
                row += 1
                placements.append((0, row, line, style))
    return placements


def relation_lines(app, scene, node_id, focused_edges):
    """Preserve full phrases and each recorded parallel relation."""
    if node_id == app.selected_id:
        return []
    lines = []
    for route in scene.routes:
        edge = route.edge
        if edge['key'] not in focused_edges or node_id not in (edge['source_id'], edge['target_id']):
            continue
        other = edge['target_id'] if node_id == edge['source_id'] else edge['source_id']
        style = edge['type'] if edge['scientific'] else 'accent'
        lines.append((relation_phrase(edge, node_id, app.node_label(other)), style))
    return lines


def shared_stubs(scene, bounds):
    """Only a common recorded port's first leg can form a visible fork."""
    px, py, width, height = bounds
    groups = {}
    for route in scene.routes:
        for key, points in ((route.edge['source_id'], route.points),
                            (route.edge['target_id'], tuple(reversed(route.points)))):
            groups.setdefault((key, points[0]), []).append((route.edge['key'], points))
    shared = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        cells = {}
        for key, points in members:
            a = points[0]
            b = next((point for point in points if point != a), a)
            for x in range(max(px, min(a[0], b[0])), min(px + width - 1, max(a[0], b[0])) + 1):
                for y in range(max(py, min(a[1], b[1])), min(py + height - 1, max(a[1], b[1])) + 1):
                    cells.setdefault((x, y), set()).add(key)
        for point, keys in cells.items():
            if len(keys) > 1:
                shared.setdefault(point, []).append(frozenset(keys))
    return shared


@dataclass(frozen=True)
class Scene:
    boxes: dict
    routes: tuple
    width: int
    height: int

    def endpoint_counts(self):
        counts = {}
        for route in self.routes:
            for key, point in ((route.edge['source_id'], route.points[0]),
                               (route.edge['target_id'], route.points[-1])):
                counts[(key, point)] = counts.get((key, point), 0) + 1
        return counts

    def focus(self, node_id, edge_key=None):
        """Only recorded, direct connections brighten; focus never changes layout."""
        nodes, edges = {node_id}, set()
        for route in self.routes:
            edge = route.edge
            if (edge["key"] == edge_key if edge_key is not None else
                    node_id in (edge["source_id"], edge["target_id"])):
                nodes.update((edge["source_id"], edge["target_id"]))
                edges.add(edge["key"])
        return nodes, edges

    def neighbor(self, node_id, direction):
        x, y = self.boxes[node_id].center
        vx, vy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[direction]
        candidates = []
        for key, box in self.boxes.items():
            dx, dy = box.center[0] - x, box.center[1] - y
            if dx * vx + dy * vy > 0:
                candidates.append(((dx / 2) ** 2 + dy ** 2, key))
        return min(candidates)[1] if candidates else node_id


def _track_overlap(index,cache,fixed,low,high):
    """Sum inclusive overlap lengths with earlier tracks on this one axis.

    Piecewise coverage integration preserves the prior routing score without
    rescanning every unrelated route for each candidate bend.
    """
    from bisect import bisect_right
    intervals=index.get(fixed,())
    if not intervals:return 0
    cached=cache.get(fixed)
    if cached is None or cached[0]!=len(intervals):
        events={}
        for start,end in intervals:
            events[start]=events.get(start,0)+1;events[end+1]=events.get(end+1,0)-1
        positions=sorted(events);areas=[];levels=[];area=level=0;last=positions[0]
        for pos in positions:
            area+=(pos-last)*level;areas.append(area);level+=events[pos];levels.append(level);last=pos
        cached=(len(intervals),positions,areas,levels);cache[fixed]=cached
    _,positions,areas,levels=cached
    def integral(point):
        i=bisect_right(positions,point)-1
        return 0 if i<0 else areas[i]+levels[i]*(point-positions[i])
    return integral(high+1)-integral(low)


def graph_scene(app):
    rows = app.graph_rows()
    allowed = app.graph_ids()
    ranks = {}
    records = {}
    for row in rows:
        if row.node_id not in allowed:
            continue
        ranks[row.node_id] = min(ranks.get(row.node_id, row.depth), row.depth)
    # Display ownership cannot suppress a cross-link between visible endpoints.
    records = {edge['key']: edge for edge in app.view['relations']
               if edge['source_id'] in ranks and edge['target_id'] in ranks}
    levels = {rank: index for index, rank in enumerate(sorted(set(ranks.values())))}
    ranks = {key: levels[rank] for key, rank in ranks.items()}
    columns = {}
    for key, rank in ranks.items():
        columns.setdefault(rank, []).append(key)
    available_w, available_h = app.graph_size
    extra_gap = 2 if app.graph_spacing == 'spacious' else 0
    minimum_vertical_gap = 3 + extra_gap
    if app.density == 'compact':
        # Reserve readable relation text inside cards, keeping route lanes clear.
        count = max(1, len(columns))
        gap_x = 8
        card_w = max(18, min(26, (available_w - (count - 1) * gap_x - 2) // count))
        card_h = 4
    else:
        card_w, card_h, gap_x = 26, 6, 12
    labels = {key: app.node_label(key) for key in ranks}
    headings = {key: node_heading(app, key) for key in ranks}
    # Canonical type/draft labels are never clipped to force a nominal fit.
    # The readability floor depends on content, never on selected/focused state.
    card_w = max(card_w, max((cell_width(text) + 3 for text in headings.values()), default=0))
    scene_key = (tuple(ranks.items()), card_w, card_h, gap_x, available_h, app.graph_spacing, tuple(labels.items()), tuple(headings.items()),
                 tuple((key, id(edge), edge['source_id'], edge['target_id'], edge['type'], edge['scientific'])
                       for key, edge in records.items()))
    if getattr(app, '_scene_key', None) == scene_key:
        return app._scene
    neighbors = {key: {} for key in ranks}
    for edge in sorted(records.values(), key=lambda edge: (not edge['scientific'], edge['key'])):
        for key, other in ((edge['source_id'], edge['target_id']), (edge['target_id'], edge['source_id'])):
            neighbors[key].setdefault(other, []).append((relation_phrase(edge, key, labels[other]), ''))
    reserved = {key: max((row for phrases in groups.values()
                         for _, row, _, _ in header_relations(headings[key], phrases, card_w - 2)), default=0)
                for key, groups in neighbors.items()}
    stacked_pairs = {frozenset((edge['source_id'], edge['target_id'])) for edge in records.values()
                     if edge['source_id'] != edge['target_id'] and ranks[edge['source_id']] == ranks[edge['target_id']]}
    def between(first, second, gap):
        return max(gap, minimum_vertical_gap) if frozenset((first, second)) in stacked_pairs else gap
    def group_height(keys, gap, *, bound=False):
        base = sum(card_h + reserved[key] for key in keys)
        if bound:
            # Alignment may reorder a column; reserve enough room before its
            # neighbors are placed, without changing geometry on selection.
            count = min(len(keys) - 1, sum(pair <= set(keys) for pair in stacked_pairs))
            return base + (len(keys) - 1) * gap + count * max(0, minimum_vertical_gap - gap)
        return base + sum(between(a, b, gap) for a, b in zip(keys, keys[1:]))
    gap_y = ((2 if max((group_height(keys, 2, bound=True) for keys in columns.values()), default=0) + 2 <= available_h
              else 1) if app.density == 'compact' else 4) + extra_gap
    area_h = max((group_height(keys, gap_y, bound=True) for keys in columns.values()), default=0)
    boxes = {}
    for rank, keys in sorted(columns.items()):
        def alignment(key):
            adjacent = [boxes[other].center[1] for edge in records.values()
                        if key in (edge["source_id"], edge["target_id"])
                        for other in (edge["source_id"], edge["target_id"])
                        if other != key and other in boxes]
            return sum(adjacent) / len(adjacent) if adjacent else area_h / 2
        keys.sort(key=alignment)
        group_h = group_height(keys, gap_y)
        next_y = (1 if area_h + 2 <= available_h else 0) + (area_h - group_h) // 2
        for index, key in enumerate(keys):
            node_h = card_h + reserved[key]
            boxes[key] = Box(1 + rank * (card_w + gap_x), next_y, card_w, node_h, reserved[key])
            next_y += node_h + (between(key, keys[index + 1], gap_y) if index + 1 < len(keys) else 0)

    # Match the vertical order of the opposite endpoints before allocating
    # ports. Parallel types still get individual routes/identities.
    ports, groups, vertical = {}, {}, set()
    directions = {(edge['source_id'], edge['target_id']) for edge in records.values()}
    for edge in records.values():
        source, target = boxes[edge['source_id']], boxes[edge['target_id']]
        if (source.x == target.x and (edge['target_id'], edge['source_id']) not in directions and not any(
                box.x == source.x and min(source.y, target.y) < box.y < max(source.y, target.y)
                for box in boxes.values())):
            vertical.add(edge['key'])
        for key, other in ((edge["source_id"], edge["target_id"]), (edge["target_id"], edge["source_id"])):
            if edge['key'] in vertical:
                side = 'bottom' if boxes[key].y < boxes[other].y else 'top'
            else:
                side = 'right' if boxes[key].x <= boxes[other].x else 'left'
            groups.setdefault((key, side), []).append((boxes[other].center[1], edge['key'], key == edge['target_id']))
    for (key, side), edges in groups.items():
        extent = boxes[key].width if side in ('top', 'bottom') else boxes[key].height
        positions = list(range(1, extent - 1))
        if side in ('top', 'bottom'):
            size = min(len(positions), max(1, 2 * len(edges) - 1))
            start = (len(positions) - size) // 2
            positions = positions[start:start + size]
        # A shared port may combine parallel routes, but never opposing
        # directions: its target arrow must not hide an outgoing connection.
        incoming = [edge for edge in edges if edge[2]]
        outgoing = [edge for edge in edges if not edge[2]]
        batches = [(edges, positions)]
        if incoming and outgoing:
            halves = sorted((incoming, outgoing), key=lambda items: sum(e[0] for e in items) / len(items))
            split = len(positions) // 2
            batches = [(halves[0], positions[:split]), (halves[1], positions[split:])]
        for batch, slots in batches:
            for index, (_, edge_key, _) in enumerate(sorted(batch)):
                offset = slots[index * (len(slots) - 1) // max(1, len(batch) - 1)]
                box = boxes[key]
                ports[(key, edge_key)] = {
                    'left': (box.x - 1, box.y + offset), 'right': (box.x + box.width, box.y + offset),
                    'top': (box.x + offset, box.y - 1), 'bottom': (box.x + offset, box.y + box.height),
                }[side]
    pairs, routes = {}, []
    horizontal_tracks,vertical_tracks,h_cache,v_cache={},{},{},{}
    for edge in sorted(records.values(), key=lambda edge: (not edge["scientific"], edge["key"])):
        source, target = boxes[edge["source_id"]], boxes[edge["target_id"]]
        pair = tuple(sorted((edge["source_id"], edge["target_id"])))
        lane = pairs.get(pair, 0)
        pairs[pair] = lane + 1
        points = []
        for key, box, other in ((edge["source_id"], source, target), (edge["target_id"], target, source)):
            points.append(ports[(key, edge['key'])])
        start, end = points
        if edge['key'] in vertical:
            mid_y = (start[1] + end[1]) // 2
            path = (start, end) if start[0] == end[0] else (start, (start[0], mid_y), (end[0], mid_y), end)
            label_x, label_width = min(start[0], end[0]) + 2, card_w // 2
        elif source.x == target.x:
            trunk = source.x + source.width + 3 + lane % 3
            path = (start, (trunk, start[1]), (trunk, end[1]), end)
            label_x, label_width = source.x + source.width + 1, gap_x - 2
        elif abs(ranks[edge["source_id"]] - ranks[edge["target_id"]]) == 1:
            low, high = sorted((start[0], end[0]))
            middle = (low + high) // 2
            def congestion(candidate):
                # Reserve horizontal legs too: overlapping one route's final
                # leg with another's source leg suggests a false direct edge.
                horizontal = vertical_overlap = 0
                for first, last in zip(candidate, candidate[1:]):
                    if first == last:
                        continue
                    if first[1]==last[1]:
                        low,high=sorted((first[0],last[0]));horizontal+=_track_overlap(horizontal_tracks,h_cache,first[1],low,high)
                    else:
                        low,high=sorted((first[1],last[1]));vertical_overlap+=_track_overlap(vertical_tracks,v_cache,first[0],low,high)
                return horizontal, vertical_overlap, len(candidate), sum(abs(x - middle) for x, _ in candidate[1:-1])
            choices = [(start, (column, start[1]), (column, end[1]), end)
                       for column in range(low + 1, high)]
            path = min(choices, key=congestion)
            if congestion(path)[0] and abs(start[1] - end[1]) > 1:
                middle_y = (start[1] + end[1]) // 2
                detours = [(start, (sx, start[1]), (sx, middle_y), (tx, middle_y), (tx, end[1]), end)
                           for sx in range(low + 1, high) for tx in range(low + 1, high) if sx != tx]
                path = min([path, *detours], key=congestion)
            label_x = min(source.x, target.x) + card_w + 1
            label_width = gap_x - 2
        else:
            # Long connections travel outside the node rows, never through an
            # intermediate box. The endpoints and direction remain recorded.
            lower = area_h + 3 + len(routes) % 4
            sx = start[0] + (2 if start[0] > source.x else -2)
            tx = end[0] + (2 if end[0] > target.x else -2)
            path = (start, (sx, start[1]), (sx, lower), (tx, lower), (tx, end[1]), end)
            label_x, label_width = min(sx, tx), max(2, abs(tx - sx))
        routes.append(Route(edge, path, label_x, label_width))
        for a,b in zip(path,path[1:]):
            if a==b:continue
            horizontal=a[1]==b[1];index=horizontal_tracks if horizontal else vertical_tracks
            fixed=a[1] if horizontal else a[0];start,end=sorted((a[0],b[0]) if horizontal else (a[1],b[1]))
            index.setdefault(fixed,[]).append((start,end))
    width = max([box.x + box.width + 1 for box in boxes.values()] +
                [x + 2 for route in routes for x, _ in route.points], default=1)
    height = max([box.y + box.height + 1 for box in boxes.values()] +
                 [y + 2 for route in routes for _, y in route.points], default=1)
    app._scene_key = scene_key
    app._scene = Scene(boxes, tuple(routes), width, height)
    return app._scene


def move_graph(app, direction):
    scene = graph_scene(app)
    if app.selected_id in scene.boxes:
        app.select(scene.neighbor(app.selected_id, direction))


def stroke_glyph(bits):
    return {1: "│", 4: "│", 5: "│", 2: "─", 8: "─", 10: "─",
            3: "└", 6: "┌", 9: "┘", 12: "┐", 7: "├", 11: "┴", 13: "┤", 14: "┬", 15: "┼"}.get(bits, "·")


def visible_stroke(contributions, focused_edges, selected_edge, shared=()):
    """One real route passes over others; independent turns never form a junction."""
    key = max(contributions, key=lambda key: (key == selected_edge, key in focused_edges,
              contributions[key] in (2, 8, 10), key))
    active = set(contributions) & focused_edges or set(contributions)
    if selected_edge not in contributions and len(active) > 1 and any(active <= group for group in shared):
        bits = 0
        for member in active:
            bits |= contributions[member]
        return key, stroke_glyph(bits)
    return key, stroke_glyph(contributions[key])


def graph(frame, app, x, y, width, height):
    title = ("EVIDENCE" if app.lens == "evidence" else "ARGUMENT") + " GRAPH"
    title += f' · Local {app.node_label(app.graph_root)} ({app.graph_depth})' if app.graph_root else ' · All'
    x, y, width, height = frame.panel(x, y, width, height, title, app.focus == "outline")
    left, top, visible_w, visible_h = x + 2, y + 2, width - 4, height - 5
    app.graph_size = (visible_w, visible_h)
    scene = graph_scene(app)
    if app.selected_id not in scene.boxes:
        frame.put(y + 2, x + 2, 'No matching records in this scope. Esc returns; / changes search.', 'muted', width - 4)
        return
    chosen = scene.boxes[app.selected_id]
    px, py = app.graph_pan
    if app.graph_follow:
        gutter = min(6, max(0, (visible_w - chosen.width) // 2))
        px = max(chosen.x + chosen.width + gutter - visible_w, min(px, chosen.x - gutter))
        py = (chosen.y if chosen.height > visible_h else
              max(chosen.y + chosen.height - visible_h, min(py, chosen.y - 1)))
    px = max(0, min(px, max(0, scene.width - visible_w)))
    py = max(0, min(py, max(0, scene.height - visible_h)))
    app.graph_pan = (px, py)
    # Center a fitting map; panning coordinates remain world coordinates.
    offset_x = max(0, (visible_w - scene.width) // 2)
    offset_y = max(0, (visible_h - scene.height) // 2)

    def put(wx, wy, text, style):
        if not 0 <= offset_y + wy - py < visible_h:
            return
        position = wx
        for char in text:
            size = char_width(char)
            if size and 0 <= offset_x + position - px and offset_x + position + size - px <= visible_w:
                frame.put(top + offset_y + wy - py, left + offset_x + position - px, char, style)
            elif not size and 0 < offset_x + position - px <= visible_w:
                frame.put(top + offset_y + wy - py, left + offset_x + position - px, char, style)
            position += size

    links = app.display_links()
    selected_edge = (links[app.link_index].key if app.reading_relation and
                     0 <= app.link_index < len(links) else None)
    focused_nodes, focused_edges = scene.focus(app.selected_id, selected_edge)
    complete = {key for key, box in scene.boxes.items() if px <= box.x and py <= box.y and
                box.x + box.width <= px + visible_w and box.y + box.height <= py + visible_h}
    hidden = sorted(focused_nodes - complete)
    outside = {link.target_id for link in app.links()} - scene.boxes.keys()
    def edge_style(route):
        edge = route.edge
        emphasized = edge["key"] in focused_edges
        return (edge["type"] if edge["scientific"] else "accent") if emphasized else "border"

    # Rasterize only the visible cells. Distant parts of a large graph allocate
    # no off-screen frame, and line crossings never create domain junctions.
    strokes = {}
    for route in scene.routes:
        for a, b in zip(route.points, route.points[1:]):
            horizontal = a[1] == b[1]
            start, end = sorted((a[0], b[0]) if horizontal else (a[1], b[1]))
            if start == end:
                continue
            fixed = a[1] if horizontal else a[0]
            if not (py <= fixed < py + visible_h if horizontal else px <= fixed < px + visible_w):
                continue
            low, high = (px, px + visible_w - 1) if horizontal else (py, py + visible_h - 1)
            for value in range(max(start, low), min(end, high) + 1):
                point = (value, fixed) if horizontal else (fixed, value)
                bits = ((8 if value > start else 0) | (2 if value < end else 0)) if horizontal else (
                    (1 if value > start else 0) | (4 if value < end else 0))
                contributions = strokes.setdefault(point, {})
                key = route.edge['key']
                contributions[key] = contributions.get(key, 0) | bits
    routes = {route.edge['key']: route for route in scene.routes}
    stubs = shared_stubs(scene, (px, py, visible_w, visible_h))
    for (wx, wy), contributions in strokes.items():
        key, glyph = visible_stroke(contributions, focused_edges, selected_edge, stubs.get((wx, wy), ()))
        put(wx, wy, glyph, edge_style(routes[key]))

    matches = app.matching_ids() if app.search else set()
    for key, box in scene.boxes.items():
        if key not in complete:
            continue  # No broken card fragments at the viewport boundary.
        selected = key == app.selected_id
        style = "selected_meta" if selected else "warning" if key in matches or app.marker(key) == "~ " else {
            "claim": "claim", "observation": "evidence", "experiment-record": "run", "experiment-plan": "plan",
            "interpretation": "interpretation", "manuscript-anchor": "writing","critique-question":"interpretation"}[app.nodes[key]["kind"]]
        body = "selected" if selected else "body"
        if key not in focused_nodes:
            style, body = "graph_dim_border", "graph_dim"
        for dy in range(box.height):
            put(box.x, box.y + dy, " " * box.width, body)
        put(box.x, box.y, "╭" + "─" * (box.width - 2) + "╮", style)
        put(box.x, box.y + box.height - 1, "╰" + "─" * (box.width - 2) + "╯", style)
        for dy in range(1, box.height - 1):
            put(box.x, box.y + dy, "│", style)
            put(box.x + box.width - 1, box.y + dy, "│", style)
        note = app.note(key).strip()
        compact = app.density == 'compact'
        heading = node_heading(app, key)
        header = '›' + heading if selected else heading
        put(box.x + 1, box.y, clip(header + (' ' if cell_width(header) < box.width - 2 else ''), box.width - 2), style)
        if key in app.collapsed and app.children(key) and not app.search:
            inventory = app.fold_inventory(key)
            flags = []
            for kind in ('challenges', 'qualifies', 'must-co-report'):
                count = sum(count for group in ('internal', 'boundary')
                            for (edge_type, _), count in inventory[group].items() if edge_type == kind)
                if count:
                    flags.append(kind + ' ' + str(count))
            statuses = ' · '.join(status + ' ' + str(len(keys)) for status, keys in inventory['statuses'].items())
            if app.scenario:
                reached = set(inventory['records']) & set(app.scenario['potentially_affected_claim_ids'])
                if reached:
                    statuses = '~' + str(len(reached)) + ' hypothetical reach' + (' · ' + statuses if statuses else '')
            parts = ['▸ ' + str(len(inventory['records']))]
            parts += flags + ([statuses] if statuses else [])
            if inventory['reference_positions']:
                parts.append(str(inventory['reference_positions']) + ' refs')
            if not flags and not statuses and not inventory['reference_positions']:
                parts.append('records')
            badge_width = box.width - 2 - (2 if compact and note else 0)
            badge = parts[0]
            for index, part in enumerate(parts[1:], 1):
                candidate = badge + ' / ' + part
                reserve = 2 if index < len(parts) - 1 else 0
                if cell_width(candidate) + reserve > badge_width:
                    badge += ' …'
                    break
                badge = candidate
            put(box.x + 1, box.y + box.height - 1, badge, 'warning' if flags or statuses else style)
        if compact and note:
            put(box.x + box.width - 3, box.y + box.height - 1, '✎', style)
        copy = overview_copy(app, key) if compact else None
        lines = list(copy) if copy else wrap(app.caption(key), box.width - 4)
        if not copy and app.nodes[key]["kind"] == "observation":
            content = app.nodes[key]["content"]
            unit = "pp" if content["metric"]["unit"] == "percentage points" else content["metric"]["unit"]
            lines = wrap(content["value"] + " " + unit, box.width - 4) + lines
        source_rows = box.height - 2 - box.relation_rows - bool(note and not compact)
        if len(lines) > source_rows:
            lines[source_rows - 1] = clip(lines[source_rows - 1], box.width - 5, ellipsis=False).rstrip() + "…"
        for dy, line in enumerate(lines[:source_rows], 1 + box.relation_rows):
            put(box.x + 2, box.y + dy, clip(line, box.width - 4), body)
        if note and not compact:
            note_style = "selected_meta" if selected else "accent" if key in focused_nodes else "graph_dim"
            put(box.x + 2, box.y + box.height - 2, clip("✎ " + note, box.width - 4), note_style)

        phrases = relation_lines(app, scene, key, focused_edges)
        for dx, dy, text, relation_style in header_relations(heading, phrases, box.width - 2):
            put(box.x + 1 + dx, box.y + dy, text, 'relation_' + relation_style)

    # Arrowheads remain on recorded targets; words stay in the header band.
    for route in sorted(scene.routes, key=lambda route: (route.edge['key'] in focused_edges,
                                                        route.edge['key'] == selected_edge)):
        edge = route.edge
        if edge['target_id'] in complete:
            target = scene.boxes[edge['target_id']]
            end = route.points[-1]
            glyph = {(-1, 0): '▶', (1, 0): '◀', (0, -1): '▼', (0, 1): '▲'}[target.outward(end)]
            put(*end, glyph, edge_style(route))
    # Keep selected source and typed destinations beside the map without a
    # permanent document pane. Personal writing never substitutes for source.
    context = app.node_label(app.selected_id) + ' / ' + app.kind(app.selected_id) + ' · ' + app.title(app.selected_id)
    if app.selected_row().unlinked:
        context = 'UNLINKED · ' + context
    frame.put(y + height - 3, x + 2, clip(context, width - 4), 'body', width - 4)
    grouped = {}
    for link in app.links():
        grouped.setdefault((link.kind, link.outgoing), []).append(app.node_label(link.target_id))
    summary = " · ".join(f"{kind} {'→' if outgoing else '←'} {','.join(targets)}"
                         for (kind, outgoing), targets in grouped.items())
    if app.selected_id in app.collapsed and not app.search:
        inventory = app.fold_inventory()
        hidden_types = ' · '.join(f'{kind} {direction} {count}'
                                  for (kind, direction), count in inventory['boundary'].items())
        summary = 'Owned boundary / ' + hidden_types + ' | Direct / ' + summary
    frame.put(y + height - 2, x + 2, ("Connection outside this view · r follows" if selected_edge and not focused_edges else summary) or "No recorded connections.", "muted", width - 4)
    more = (" ←" if px else "") + (" →" if px + visible_w < scene.width else "") + (
        " ↑" if py else "") + (" ↓" if py + visible_h < scene.height else "")
    all_ids = set(app._paths)
    all_edges = {edge['key'] for edge in app.view['relations']
                 if edge['source_id'] in all_ids and edge['target_id'] in all_ids}
    folded_count = len(all_ids - {row.node_id for row in app.graph_rows()})
    lens_count = len(app.nodes) - len(all_ids)
    scope = f'Local {app.node_label(app.graph_root)} / {app.graph_depth} hop' if app.graph_root else 'All'
    hidden_count = len({row.node_id for row in app.graph_rows()}) - len(scene.boxes)
    counts = f'{len(complete)}/{len(scene.boxes)} visible'
    if hidden_count:
        counts += f' · {hidden_count} hidden by scope / {len(all_edges) - len(scene.routes)} edges'
    else:
        counts += f' · {len(scene.routes)} edges'
    footer = f'{counts} · {scope}{more}'
    if hidden or outside:
        unavailable = ('Offscreen: ' + ' '.join(app.node_label(key) for key in hidden) if hidden else '')
        if outside:
            unavailable += (' · ' if unavailable else '') + 'Outside scope: ' + ' '.join(app.node_label(key) for key in sorted(outside))
        visibility = f'{len(complete)}/{len(scene.boxes)} visible' + (f' · {hidden_count} hidden' if hidden_count else '')
        footer = visibility + more + ' · r follows · ' + unavailable + ' · ' + counts.split(' · ', 1)[-1]
    footer = f"{folded_count} {'filtered' if app.search else 'folded'} · " + footer
    if lens_count:
        footer += f' · {lens_count} outside lens'
    frame.put(y + height - 1, x + 2, footer, 'muted', width - 4)
