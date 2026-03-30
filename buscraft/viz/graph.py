"""Causal graph from ReasoningDocument + HypothesisBundle."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument


@dataclass
class CausalEdge:
    src: str
    dst: str
    kind: str
    weight: float = 1.0


def build_edges_from_document(doc: ReasoningDocument, bundle: HypothesisBundle | None = None) -> list[CausalEdge]:
    edges: list[CausalEdge] = []
    anchors = {a.id: a for a in doc.failure_anchors}
    for e in doc.events:
        for aid, a in anchors.items():
            if e.t_ps is not None and a.sim_time_ps is not None and e.t_ps <= a.sim_time_ps:
                edges.append(CausalEdge(src=e.id, dst=aid, kind="log_precedes", weight=0.8))
    for asr in doc.assertions:
        for aid in anchors:
            edges.append(CausalEdge(src=asr.id, dst=aid, kind="assert_fails_at", weight=0.9))
    for sb in doc.scoreboard_mismatches:
        for aid in anchors:
            edges.append(CausalEdge(src=sb.id, dst=aid, kind="scoreboard_to_anchor", weight=0.85))
    for ws in doc.wave_slices:
        for aid in anchors:
            if ws.anchor_id == aid:
                edges.append(CausalEdge(src=ws.id, dst=aid, kind="wave_supports", weight=0.7))
    if bundle:
        for h in bundle.hypotheses:
            for aid in anchors:
                edges.append(
                    CausalEdge(
                        src=h.id,
                        dst=aid,
                        kind="hypothesis_supports",
                        weight=max(0.2, min(1.0, h.confidence)),
                    )
                )
    return edges


class CausalGraphBuilder:
    def __init__(self, edges: list[CausalEdge]) -> None:
        self.edges = edges
        self.g = nx.DiGraph()
        for e in edges:
            self.g.add_edge(e.src, e.dst, kind=e.kind, weight=e.weight)

    def top_anchor_nodes(self, anchors: list[str]) -> list[str]:
        return [n for n in self.g.nodes if n in anchors]
