"""Rank likely root causes via PageRank on reversed graph + boosts."""

from __future__ import annotations

import networkx as nx

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument
from buscraft.viz.graph import CausalGraphBuilder, build_edges_from_document


def rank_root_causes(
    doc: ReasoningDocument,
    bundle: HypothesisBundle,
    *,
    top_k: int = 5,
    kb_boost: float = 0.05,
) -> list[tuple[str, float, list[str]]]:
    """
    Return list of (node_id, score, trace) where node_id is preferred root candidate.
    """
    edges = build_edges_from_document(doc, bundle)
    builder = CausalGraphBuilder(edges)
    g = builder.g
    if g.number_of_nodes() == 0:
        return []

    anchor_ids = [a.id for a in doc.failure_anchors]
    rev = g.reverse(copy=True)
    for u, v, data in rev.edges(data=True):
        if data.get("kind") == "wave_supports" and doc.coverage.wave_completeness > 0.5:
            rev[u][v]["weight"] = data.get("weight", 1.0) * 1.2
        if data.get("kind") == "log_precedes":
            rev[u][v]["weight"] = data.get("weight", 1.0) * 1.1

    personalization = {n: 0.0 for n in rev.nodes}
    for a in anchor_ids:
        if a in personalization:
            personalization[a] = 1.0
    s = sum(personalization.values())
    if s > 0:
        personalization = {k: v / s for k, v in personalization.items()}
    else:
        personalization = None

    try:
        scores = nx.pagerank(rev, weight="weight", personalization=personalization)
    except Exception:
        scores = {n: 1.0 / max(1, g.number_of_nodes()) for n in g.nodes}

    for h in bundle.hypotheses:
        if h.id in scores:
            scores[h.id] = scores.get(h.id, 0) + kb_boost * min(1.0, h.confidence)

    candidates = [n for n in scores if n not in anchor_ids]
    ranked = sorted(((n, scores[n]) for n in candidates), key=lambda x: -x[1])[:top_k]
    out: list[tuple[str, float, list[str]]] = []
    for nid, sc in ranked:
        trace: list[str] = []
        for aid in anchor_ids:
            try:
                if nx.has_path(rev, nid, aid):
                    trace = nx.shortest_path(rev, nid, aid)[:12]
                    break
            except Exception:
                pass
        out.append((nid, float(sc), trace))
    return out
