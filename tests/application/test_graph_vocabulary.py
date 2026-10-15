"""The registry is descriptive; schemas and history remain authority."""
import unittest
from claimbranch.core.graph_vocabulary import (EDGE_KINDS, NODE_KINDS,
    SCIENTIFIC_EDGE_TYPES, relation_label, scientific_choices)
from claimbranch.core.canonical import ContractError
from claimbranch.core.research_schema import command_schema, normalize
from claimbranch.fixtures import replay_example
from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.application.tui_graph import relation_phrase


class GraphVocabularyTests(unittest.TestCase):
    def test_every_projected_type_uses_the_registered_directional_labels(self):
        app = TerminalWorkspace(replay_example('manual', paper=True))
        for edge in app.view['relations']:
            item = EDGE_KINDS[edge['type']]
            self.assertEqual(edge['scientific'], item.scientific)
            self.assertIn(app.nodes[edge['source_id']]['kind'], item.sources)
            self.assertIn(app.nodes[edge['target_id']]['kind'], item.targets)
            self.assertEqual(item.label + ' target', relation_phrase(edge, edge['source_id'], 'target'))
            self.assertEqual(item.reverse + ' source', relation_phrase(edge, edge['target_id'], 'source'))
        self.assertEqual(set(app.kind(key) for key in app.nodes if app.nodes[key]['kind'] != 'claim'),
                         {NODE_KINDS[node['kind']].label for key, node in app.nodes.items() if node['kind'] != 'claim'})

    def test_scientific_choices_exclude_structural_types_and_invalid_endpoints(self):
        self.assertEqual(('supports', 'challenges', 'qualifies'), SCIENTIFIC_EDGE_TYPES)
        self.assertEqual(SCIENTIFIC_EDGE_TYPES, scientific_choices('observation', 'claim'))
        self.assertEqual((), scientific_choices('experiment-plan', 'claim'))
        self.assertEqual((), scientific_choices('claim', 'observation'))
        self.assertNotIn('part-of', scientific_choices())
        self.assertIn('not strength', EDGE_KINDS['supports'].definition)
        self.assertIn('does not prove', EDGE_KINDS['challenges'].definition)

    def test_unknown_renderer_diagnostic_does_not_extend_schema_vocabulary(self):
        self.assertIn('unrecognized type', relation_label('made-up'))
        schema = command_schema(3)
        self.assertNotIn('made-up', str(schema))
        from claimbranch.core.research_schema import BODIES
        with self.assertRaises(ContractError):
            normalize({'edge_type': 'made-up', 'source_id': 'a', 'target_id': 'b', 'rationale': 'x'}, BODIES['scientific-edge'])
        with self.assertRaises(TypeError):
            EDGE_KINDS['made-up'] = EDGE_KINDS['supports']

    def test_invalid_editable_candidates_never_project_as_science(self):
        from copy import deepcopy
        for variant in ('self-edge', 'wrong-parent', 'parent-cycle'):
            with self.subTest(variant=variant):
                history = replay_example('manual', paper=True)
                original = history.manifest()
                app = TerminalWorkspace(history)
                work = app.review.candidates()
                if variant == 'self-edge':
                    work.create('scientific-edge', dict(source_id='claim-pruning', target_id='claim-pruning', edge_type='supports', rationale='Invalid self link'))
                elif variant == 'wrong-parent':
                    work.create('claim', dict(role='subclaim', parent_ids=['thesis'], statement='Invalid parent', scope='Synthetic'))
                else:
                    a = work.create('claim', dict(role='subclaim', parent_ids=['claim-pruning'], statement='A', scope='Synthetic'))
                    b = work.create('claim', dict(role='subclaim', parent_ids=[a], statement='B', scope='Synthetic'))
                    revised = deepcopy(work.records[a]); revised['body']['parent_ids'] = [b]; work.put(revised)
                submitted = deepcopy(work.records)
                expected = {'self-edge': 'self-support', 'wrong-parent': 'roles disagree',
                            'parent-cycle': 'cyclic claim'}[variant]
                self.assertIn('thesis', app.nodes)
                with self.assertRaisesRegex(ContractError, expected):
                    work.project()
                self.assertEqual(submitted, work.records)  # exact invalid writing retained
                self.assertEqual(original, history.manifest())


class CritiqueVocabularyTests(unittest.TestCase):
    def test_existing_critique_relations_are_descriptive_and_defined(self):
        self.assertEqual(('supports','challenges','qualifies'),SCIENTIFIC_EDGE_TYPES)
        for kind in ('questions','addressed-by'):
            edge=EDGE_KINDS[kind];self.assertFalse(edge.scientific);self.assertIn('critique-question',edge.sources)
            self.assertEqual(edge.label,relation_label(kind));self.assertTrue(edge.definition)
