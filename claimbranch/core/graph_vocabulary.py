"""Closed paper graph vocabulary shared by schemas and presentation.

These descriptors confer no authority. Non-scientific links are projections of
specific records; listing one here does not authorize drawing it into history.
"""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class NodeKind:
    label: str
    alias: str
    order: int


@dataclass(frozen=True)
class EdgeKind:
    label: str
    reverse: str
    definition: str
    sources: frozenset[str]
    targets: frozenset[str]
    scientific: bool = False


CLAIM_ROLES = MappingProxyType({'thesis': 'THESIS', 'main': 'MAIN', 'subclaim': 'SUBCLAIM'})

NODE_KINDS = MappingProxyType({
    'claim': NodeKind('CLAIM', 'C', 0),
    'observation': NodeKind('EVIDENCE', 'E', 1),
    'experiment-record': NodeKind('RUN', 'R', 2),
    'experiment-plan': NodeKind('PLAN', 'P', 3),
    'interpretation': NodeKind('READING', 'I', 4),
    'manuscript-anchor': NodeKind('WRITING', 'W', 5),
    'critique-question': NodeKind('QUESTION', 'Q', 6),
})


def _edge(label, reverse, definition, sources, targets, scientific=False):
    return EdgeKind(label, reverse, definition, frozenset(sources), frozenset(targets), scientific)


_SOURCES = ('claim', 'interpretation', 'observation')
EDGE_KINDS = MappingProxyType({
    'supports': _edge('supports', 'supported by', 'Provides a recorded basis for the target claim; count is not strength.', _SOURCES, ('claim',), True),
    'challenges': _edge('challenges', 'challenged by', 'Raises a recorded objection to the target claim; does not prove it false.', _SOURCES, ('claim',), True),
    'qualifies': _edge('qualifies', 'qualified by', 'Limits the scope, conditions or strength of the target claim.', _SOURCES, ('claim',), True),
    'part-of': _edge('part of', 'contains', 'Claim hierarchy; not scientific support.', ('claim',), ('claim',)),
    'replaces': _edge('replaces record', 'replacement record', 'Explicit observation replacement context; neither status nor evidence eligibility changes.', ('observation',), ('observation',)),
    'produced': _edge('produced', 'produced by', 'A recorded experiment produced this observation; not a planned result.', ('experiment-record',), ('observation',)),
    'interprets': _edge('interprets', 'interpreted by', 'An interpretation reads these recorded observations.', ('interpretation',), ('observation',)),
    'tests': _edge('tests', 'tested by', 'An unrun experiment plan tests a claim.', ('experiment-plan',), ('claim',)),
    'expresses': _edge('expresses', 'expressed by', 'A declared manuscript anchor expresses a claim; manuscript stays read-only.', ('manuscript-anchor',), ('claim',)),
    'plots': _edge('declares data from', 'declared in', 'A registered anchor declares use of an observation; no artifact verification implied.', ('manuscript-anchor',), ('observation',)),
    'caption-of': _edge('caption for', 'has caption', 'A registered caption belongs to a figure or table anchor.', ('manuscript-anchor',), ('manuscript-anchor',)),
    'revises-reading': _edge('revises reading', 'original of reading', 'A retained reading revises an earlier interpretation.', ('interpretation',), ('interpretation',)),
    'co-reported-with': _edge('co-reported with', 'co-reported with', 'Interpretations selected for reporting together, not competing alternatives.', ('interpretation',), ('interpretation',)),
    'questions': _edge('questions', 'questioned by', 'A sourced non-empirical research question about this claim; not scientific counterevidence.', ('critique-question',), ('claim',)),
    'addressed-by': _edge('addressed by', 'addresses question', 'Declared experiment, plan or exact claim consequence addressing a question; does not resolve it automatically.', ('critique-question',), ('claim','experiment-record','experiment-plan')),
    'must-co-report': _edge('must be reported with', 'requires companion', 'A declared reporting dependency, not a scientific support edge.', tuple(NODE_KINDS), tuple(NODE_KINDS)),
})
SCIENTIFIC_EDGE_TYPES = tuple(key for key, value in EDGE_KINDS.items() if value.scientific)


def scientific_choices(source_kind=None, target_kind=None):
    """Allowed type choices; full domain/authority validation remains mandatory."""
    return tuple(key for key in SCIENTIFIC_EDGE_TYPES
                 if (source_kind is None or source_kind in EDGE_KINDS[key].sources)
                 and (target_kind is None or target_kind in EDGE_KINDS[key].targets))


def relation_label(kind, outgoing=True):
    item = EDGE_KINDS.get(kind)
    if item is None:
        return 'unrecognized type: ' + str(kind)
    return item.label if outgoing else item.reverse


def node_order(kind):
    item = NODE_KINDS.get(kind)
    return item.order if item else len(NODE_KINDS)
