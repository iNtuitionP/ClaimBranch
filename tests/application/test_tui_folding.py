"""Folded projections share canonical identity and never author science."""
from copy import deepcopy
import unittest
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example


class FoldProjectionTests(unittest.TestCase):
    def setUp(self):
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history)

    def test_experiment_root_exposes_multiple_results_and_typed_claim_paths(self):
        self.app.switch_lens('evidence', evidence_id='run-accuracy')
        rows = self.app.folded_rows()
        self.assertEqual('run-accuracy', rows[0].node_id)
        self.assertEqual({'obs-1', 'obs-2'}, {row.node_id for row in rows if row.depth == 1})
        self.assertTrue(all(edge['type'] == 'produced' for row in rows if row.depth == 1 for edge in row.edges))
        self.app.collapsed.clear()
        self.assertIn('thesis', {row.node_id for row in self.app.folded_rows()})
        self.assertEqual(self.original, self.history.manifest())

    def test_observation_root_keeps_producer_anchor_and_shared_uses_accessible(self):
        self.app.switch_lens('evidence', evidence_id='obs-1')
        direct = {row.node_id for row in self.app.folded_rows() if row.depth == 1}
        self.assertTrue({'run-accuracy', 'claim-comparison', 'claim-pruning-detail'} <= direct)
        self.assertIn('anchor', self.app._paths)
        self.assertEqual(1, sum(not row.reference and row.node_id == 'obs-1' for row in self.app._outline_rows))
        self.assertEqual(self.original, self.history.manifest())

    def test_experiment_only_branch_and_unrun_plan_are_roots_without_fake_results(self):
        app = self.app
        app.nodes = {key: node for key, node in app.nodes.items() if node['kind'] != 'observation'}
        app.view = {**app.view, 'nodes': list(app.nodes.values()),
                    'relations': [edge for edge in app.view['relations'] if edge['source_id'] in app.nodes and edge['target_id'] in app.nodes]}
        app._build_outline()
        app.switch_lens('evidence', evidence_id='run-accuracy')
        self.assertEqual(['run-accuracy'], [row.node_id for row in app.folded_rows()])
        app.cycle_evidence(1)
        self.assertIn(app.evidence_root, app.entry_ids())
        plan = next(key for key in app.entry_ids() if app.nodes[key]['kind'] == 'experiment-plan')
        app.switch_lens('evidence', evidence_id=plan)
        self.assertFalse(any(edge['type'] == 'produced' for edge in app.view['relations'] if edge['source_id'] == plan))

    def test_cycles_parallel_directions_and_shared_references_are_finite(self):
        app = self.app
        app.view['relations'].extend([
            dict(key='reverse-challenge', source_id='claim-pruning', target_id='claim-pruning-detail', type='challenges', scientific=True, rationale='Synthetic challenge hop'),
            dict(key='qualify-back', source_id='claim-comparison', target_id='claim-pruning', type='qualifies', scientific=True, rationale='Synthetic cross link')])
        app.switch_lens('evidence', evidence_id='obs-1')
        self.assertLessEqual(len(app._outline_rows), len(app.nodes) + len(app.view['relations']))
        self.assertEqual(len(app._paths), sum(not row.reference for row in app._outline_rows))
        self.assertEqual(len(app._outline_rows), len(app._row_by_path))
        shown = {edge['key'] for row in app._outline_rows for edge in row.edges}
        self.assertEqual({edge['key'] for edge in app.view['relations']}, shown)

    def test_fold_inventory_counts_record_identities_and_exact_edge_directions(self):
        app = self.app
        app.switch_lens('evidence', evidence_id='run-accuracy')
        inventory = app.fold_inventory('obs-1')
        owned = set(inventory['records'])
        internal = [edge for edge in app.view['relations'] if edge['source_id'] in owned and edge['target_id'] in owned]
        boundary = [edge for edge in app.view['relations'] if (edge['source_id'] in owned) != (edge['target_id'] in owned)]
        self.assertEqual(len(owned), len(inventory['records']))
        self.assertEqual(len(internal), sum(inventory['internal'].values()))
        self.assertEqual(len(boundary), sum(inventory['boundary'].values()))

    def test_lens_fold_state_and_stale_navigation_restore_after_graph_revision(self):
        app = self.app
        app.switch_lens('evidence', evidence_id='run-accuracy')
        app.select('claim-pruning-detail')
        cached = app._navigation()
        cached['selected_path'] = ('run-accuracy', 'removed-old-path', 'claim-pruning-detail')
        cached['_revision'] = 'stale'
        app.view['nodes'] = deepcopy(app.view['nodes'])
        app._restore_navigation(cached)
        self.assertEqual('claim-pruning-detail', app.selected_id)
        self.assertEqual(app._paths[app.selected_id], app.selected_path)
        app.switch_lens('argument'); app.switch_lens('evidence', evidence_id='run-accuracy')
        self.assertEqual('run-accuracy', app.evidence_root)
        self.assertEqual('claim-pruning-detail', app.selected_id)
        self.assertEqual(app._paths['claim-pruning-detail'], app.selected_path)
        self.assertIn(app.selected_path, app._row_by_path)
        self.assertEqual(self.original, self.history.manifest())

    def test_switching_roots_restores_each_saved_selection_and_folds(self):
        app = self.app
        app.switch_lens('evidence', evidence_id='run-accuracy')
        app.select('claim-pruning-detail')
        saved = app._navigation()
        app.switch_lens('evidence', evidence_id='obs-2')
        app.select('claim-comparison')
        app.switch_lens('evidence', evidence_id='run-accuracy')
        self.assertEqual(saved['selected_id'], app.selected_id)
        self.assertEqual(saved['selected_path'], app.selected_path)
        self.assertEqual(saved['collapsed'], app.collapsed)
        app.switch_lens('evidence', evidence_id='obs-2')
        self.assertEqual('claim-comparison', app.selected_id)


class FoldTerminalTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from claimbranch.application.tui import Terminal
        self.history = replay_example('manual', paper=True)
        self.original = self.history.manifest()
        self.app = TerminalWorkspace(self.history, ai_off=True)
        self.t = Terminal.__new__(Terminal)
        self.t.app, self.t.modal, self.t.buffers, self.t.field = self.app, None, [], 0
        self.size = (42, 144)
        self.t.screen = SimpleNamespace(getmaxyx=lambda: self.size, clearok=lambda value: None)

    def test_default_folds_explicit_activation_and_all_routes_when_unfolded(self):
        from claimbranch.application.tui_graph import graph_scene
        app = self.app
        self.assertLess(len(graph_scene(app).boxes), len(app.nodes))
        app.select('claim-comparison')
        self.assertIn(app.selected_id, app.collapsed)
        self.t.key('enter')
        self.assertNotIn(app.selected_id, app.collapsed)
        self.assertEqual('outline', app.focus)
        self.t.key(' ')
        self.assertIn(app.selected_id, app.collapsed)
        self.t.key('*')
        scene = graph_scene(app)
        self.assertEqual(set(app.nodes), set(scene.boxes))
        self.assertEqual({edge['key'] for edge in app.view['relations']}, {route.edge['key'] for route in scene.routes})
        self.assertEqual(self.original, self.history.manifest())

    def test_experiment_chooser_search_resize_cancel_and_full_text(self):
        from claimbranch.application.tui import Frame
        from claimbranch.application.tui_view_ui import graph_browse_ui
        self.t.key('2')
        self.assertEqual('run-accuracy', self.app.evidence_root)
        before = self.app._navigation()
        self.t.key('2')
        self.assertEqual('graph-browse', self.t.modal)
        self.t.key(('paste', 'Quantizing'))
        ui = graph_browse_ui(self.t)
        self.assertEqual(['obs-2'], [key for key, _ in ui.items()])
        self.t.key('tab')
        for w, h in ((144, 42), (120, 32), (80, 24)):
            self.size = (h, w)
            self.assertIn('Full text', ui.draw(Frame(w, h)).plain())
        self.t.key('escape')
        self.assertEqual(before, self.app._navigation())
        self.t.key('2'); self.t.key(('paste', 'Quantizing')); self.t.key('enter')
        self.assertEqual('obs-2', self.app.evidence_root)
        self.assertEqual(self.original, self.history.manifest())

    def test_hidden_challenge_and_corrected_status_are_inspectable_separately(self):
        from claimbranch.application.tui import Frame
        from claimbranch.application.tui_view_ui import graph_browse_ui
        app = self.app
        app.view['relations'].append(dict(key='test-challenge', source_id='obs-1', target_id='claim-comparison', type='challenges', scientific=True, rationale='Synthetic counterevidence'))
        app.nodes['obs-1']['content']['status'] = 'corrected'
        app._build_outline(); app.select('thesis'); app.collapsed.add('thesis')
        inventory = app.fold_inventory()
        self.assertEqual(('obs-1',), inventory['statuses']['corrected'])
        self.assertEqual(1, sum(count for group in ('internal', 'boundary') for (kind, _), count in inventory[group].items() if kind == 'challenges'))
        ui = graph_browse_ui(self.t); ui.open('inventory')
        rows = ui.items()
        self.assertTrue(any('corrected / 1' in text for _, text in rows))
        ui.index = next(i for i, (key, _) in enumerate(rows) if isinstance(key, dict) and key['key'] == 'test-challenge')
        self.t.key('tab')
        self.assertIn('--challenges-->', ui.draw(Frame(144, 42)).plain())
        self.t.key('enter')
        self.assertEqual('test-challenge', app.links()[app.link_index].key)
        self.assertTrue(app.reading_relation)
        self.assertEqual(self.original, self.history.manifest())

    def test_search_reveals_folded_match_and_empty_search_never_crashes(self):
        from claimbranch.application.tui import render_snapshot
        from claimbranch.application.tui_graph import graph_scene
        app = self.app
        folds = set(app.collapsed)
        self.t.key('/'); self.t.key(('paste', 'interpretation')); self.t.key('enter')
        self.assertEqual('interpretation', app.selected_id)
        self.assertIn(app.selected_id, graph_scene(app).boxes)
        render_snapshot(app, 80, 24)
        self.assertEqual(folds, app.collapsed)  # temporary reveal, not an unfold
        self.t.key('escape')
        self.t.key('/'); self.t.key(('paste', 'no-such-record-987654')); self.t.key('enter')
        self.assertIn('No matching records', render_snapshot(app, 80, 24))
        for key in ('j', 'k', 'up', 'down', 'left', 'right'):
            self.t.key(key)
        self.t.key('escape')
        self.assertIn(app.selected_id, graph_scene(app).boxes)
        self.assertEqual(self.original, self.history.manifest())

    def test_switching_back_without_explicit_root_restores_last_result_and_writing(self):
        app = self.app
        app.switch_lens('evidence', evidence_id='obs-2')
        app.keep_draft('검토한 두 번째 관찰', '그 조건에서만 해석한다.')
        app.switch_lens('argument')
        self.assertEqual('thesis', app.selected_id)
        app.switch_lens('evidence')
        self.assertEqual('obs-2', app.evidence_root)
        self.assertEqual('obs-2', app.selected_id)
        self.assertEqual('검토한 두 번째 관찰', app.draft()['text'])

    def test_fold_inventory_cache_changes_with_lens_and_record_revision(self):
        app = self.app
        first = app.fold_inventory('claim-comparison')
        app.switch_lens('evidence', evidence_id='obs-1')
        second = app.fold_inventory('claim-comparison')
        self.assertNotEqual(first['records'], second['records'])
        self.assertNotIn('corrected', second['statuses'])
        app.nodes['obs-2']['content']['status'] = 'corrected'
        app.view['relations'].append(dict(key='after-cached-challenge', source_id='obs-2', target_id='claim-comparison', type='challenges', scientific=True, rationale='Updated projection'))
        app._build_outline()
        third = app.fold_inventory('claim-comparison')
        self.assertIn('obs-2', third['statuses']['corrected'])
        self.assertEqual(1, sum(count for group in ('internal', 'boundary') for (kind, _), count in third[group].items() if kind == 'challenges'))
        self.assertEqual(self.original, self.history.manifest())

    def test_root_full_text_reading_does_not_silently_change_search(self):
        from claimbranch.application.tui_view_ui import graph_browse_ui
        ui = graph_browse_ui(self.t); ui.open('roots')
        self.t.key(('paste', 'Quantizing')); self.t.key('tab')
        before = ui.items()
        self.t.key(('paste', 'ignored')); self.t.key('x')
        self.assertEqual('Quantizing', ui.query)
        self.assertEqual(before, ui.items())

    def test_selected_draft_type_remains_whole_at_compact_readability_floor(self):
        from claimbranch.application.tui import render_snapshot
        from claimbranch.application.tui_graph import graph_scene, node_heading
        from claimbranch.application.tui_model import cell_width
        app = self.app
        app.nodes['interpretation']['draft'] = True
        app.select('interpretation')
        app.graph_size = (40, 20)
        scene = graph_scene(app)
        for key, box in scene.boxes.items():
            self.assertLessEqual(cell_width('›' + node_heading(app, key)), box.width - 2)
        self.assertIn('I1 DRAFT READING', render_snapshot(app, 80, 24))

    def test_compact_note_does_not_overwrite_fold_overflow_indicator(self):
        from unittest.mock import patch
        from claimbranch.application.tui import render_snapshot
        app = self.app
        app.notes[app.context_key()] = 'A separate personal note'
        app.collapsed.add('thesis')
        inventory = dict(records=tuple(range(512)), reference_positions=2,
                         internal={('challenges', 'out'): 512, ('qualifies', 'out'): 1},
                         boundary={}, statuses={})
        with patch.object(app, 'fold_inventory', return_value=inventory):
            text = render_snapshot(app, 80, 24)
        line = next(line for line in text.splitlines() if '✎' in line)
        self.assertIn('…', line)
        self.assertNotIn('challenge✎', line)
        self.assertEqual(self.original, self.history.manifest())


class NamedFoldGuardTests(unittest.TestCase):
    def test_action_cannot_fold_while_search_temporarily_reveals_records(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_actions import ActionsUI
        app=TerminalWorkspace(replay_example('manual',paper=True),ai_off=True)
        app.search='pruning';before=set(app.collapsed)
        terminal=SimpleNamespace(app=app,modal='actions',screen=SimpleNamespace(getmaxyx=lambda:(32,120)))
        ui=ActionsUI(terminal);ui.index=next(i for i,a in enumerate(ui.items()) if a.key=='fold:collapse');ui.key('enter')
        self.assertEqual(before,app.collapsed);self.assertIn('Clear search',ui.notice)
