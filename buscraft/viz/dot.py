"""Graphviz DOT emission."""

from __future__ import annotations

from buscraft.viz.graph import CausalGraphBuilder, build_edges_from_document
from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument


def to_graphviz_dot(doc: ReasoningDocument, bundle: HypothesisBundle | None = None) -> str:
    edges = build_edges_from_document(doc, bundle)
    b = CausalGraphBuilder(edges)
    lines = ["digraph Buscraft {", "  rankdir=LR;", "  node [shape=box];"]
    for u, v, data in b.g.edges(data=True):
        kind = data.get("kind", "")
        w = data.get("weight", 1.0)
        lines.append(f'  "{u}" -> "{v}" [label="{kind}", weight="{w}"];')
    lines.append("}")
    return "\n".join(lines)
