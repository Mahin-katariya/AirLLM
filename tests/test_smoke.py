from pathlib import Path

import pytest

from buscraft.ingest.uvm import parse_uvm_log
from buscraft.kb.patterns import PatternKnowledgeBase, failure_signature
from buscraft.models.hypothesis import Hypothesis, HypothesisBundle
from buscraft.models.validation import validate_hypothesis_evidence
from buscraft.protocols.loader import hydrate_protocol_context, load_protocol_template
from buscraft.reason.orchestrator import ReasoningOrchestrator
from buscraft.runtime.fallback import FallbackBackend
from buscraft.runtime.manager import ModelRuntimeManager, QualityPreset
from buscraft.transform.build_document import build_reasoning_document
from buscraft.viz.graph import build_edges_from_document
from buscraft.viz.ranker import rank_root_causes


def test_uvm_parse(tmp_path: Path) -> None:
    p = tmp_path / "l.log"
    p.write_text("UVM_ERROR @ 10 ns: [env] bad\nUVM_FATAL @ 20 ns: [dut] die\n")
    ev, fa = parse_uvm_log(p)
    assert len(ev) >= 2
    assert any(a.source.startswith("uvm_") for a in fa)


def test_protocol_template() -> None:
    t = load_protocol_template("AXI4_LITE")
    assert t is not None
    assert "AXI" in t.name


def test_orchestrator_stub(tmp_path: Path) -> None:
    p = tmp_path / "l.log"
    p.write_text("UVM_FATAL @ 1000 ns: [tb] SLVERR on write\n")
    doc = build_reasoning_document(p, protocol_profile="AXI4_LITE")
    doc = hydrate_protocol_context(doc)
    orch = ReasoningOrchestrator(FallbackBackend(ModelRuntimeManager(), QualityPreset.FAST))
    r = orch.run(doc)
    assert r.bundle.hypotheses
    ok, err = validate_hypothesis_evidence(r.document, r.bundle)
    assert ok, err


def test_graph_ranker(tmp_path: Path) -> None:
    p = tmp_path / "l.log"
    p.write_text("UVM_FATAL @ 5 ns: [x] y\n")
    doc = build_reasoning_document(p)
    eid = doc.failure_anchors[0].id if doc.failure_anchors else "fa1"
    b = HypothesisBundle(
        failure_class="UVM_FATAL_ERROR",
        hypotheses=[
            Hypothesis(
                id="h1",
                statement="test",
                evidence_ids=[eid],
                confidence=0.5,
            )
        ],
    )
    edges = build_edges_from_document(doc, b)
    assert isinstance(edges, list)
    ranked = rank_root_causes(doc, b)
    assert isinstance(ranked, list)


def test_kb(tmp_path: Path) -> None:
    db = tmp_path / "k.db"
    kb = PatternKnowledgeBase(db)
    p = tmp_path / "l.log"
    p.write_text("UVM_ERROR @ 1 ns: [a] b\n")
    doc = build_reasoning_document(p)
    sig = failure_signature(doc, None)
    kb.record_occurrence(sig, doc)
    assert kb.suggest(sig)
