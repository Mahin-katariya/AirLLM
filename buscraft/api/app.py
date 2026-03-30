"""FastAPI: analyze, GTKWave helpers, interactive session, stateless inference proxy."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from buscraft.kb.patterns import PatternKnowledgeBase, failure_signature
from buscraft.models.wave_contracts import GTKWaveCommand
from buscraft.reason.orchestrator import ReasoningOrchestrator
from buscraft.runtime.fallback import FallbackBackend
from buscraft.runtime.manager import ModelRuntimeManager, QualityPreset
from buscraft.session.store import SessionStore
from buscraft.transform.build_document import build_reasoning_document
from buscraft.viz.dot import to_graphviz_dot
from buscraft.viz.ranker import rank_root_causes
from buscraft.wave.gtkwave import build_fallback_instructions, build_gtkwave_tcl


class AnalyzeRequest(BaseModel):
    log_path: str
    vcd_path: str | None = None
    protocol_profile: str = "NONE"
    signals: list[str] = Field(default_factory=list)
    preset: str = "balanced"
    use_critique: bool = False


class FollowUpRequest(BaseModel):
    session_id: str
    question: str
    preset: str = "balanced"


class InferenceProxyBody(BaseModel):
    """Stateless OpenAI-style chat; server does not persist document (client sends snippets)."""

    messages: list[dict]
    max_tokens: int = 1024
    temperature: float = 0.2
    model: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Buscraft++", version="0.1.0")
    store = SessionStore()
    kb_path = Path(os.environ.get("BUSCRAFT_KB_PATH", Path.home() / ".cache" / "buscraft" / "patterns.db"))
    kb = PatternKnowledgeBase(kb_path)
    manager = ModelRuntimeManager()

    @app.post("/v1/analyze")
    def analyze(body: AnalyzeRequest) -> dict:
        preset = _preset(body.preset)
        doc = build_reasoning_document(
            body.log_path,
            vcd_path=body.vcd_path,
            protocol_profile=body.protocol_profile,
            signal_paths=body.signals or None,
        )
        orch = ReasoningOrchestrator(FallbackBackend(manager, preset))
        result = orch.run(doc, use_critique=body.use_critique)
        sig = failure_signature(result.document, result.bundle)
        kb.record_occurrence(sig, result.document)
        suggestions = kb.suggest(sig)
        ranked = rank_root_causes(result.document, result.bundle)
        dot = to_graphviz_dot(result.document, result.bundle)
        sid = store.create(result.document, result)
        gtk = None
        if body.vcd_path and result.document.failure_anchors:
            t = result.document.failure_anchors[0].sim_time_ps or 0
            sigs: list[str] = list(body.signals)
            cmd = GTKWaveCommand(dump_path=body.vcd_path, jump_time_ps=t, add_signals=sigs)
            gtk = {
                "tcl": build_gtkwave_tcl(cmd),
                "fallback_instructions": build_fallback_instructions(cmd),
            }
        return {
            "session_id": sid,
            "failure_signature": sig,
            "kb_suggestions": suggestions,
            "classifier_class": result.classifier_class,
            "confidence_breakdown": result.confidence_breakdown,
            "bundle": result.bundle.model_dump(),
            "ranked_root_causes": [{"node": n, "score": s, "trace": tr} for n, s, tr in ranked],
            "graphviz_dot": dot,
            "gtkwave": gtk,
        }

    @app.post("/v1/session/follow_up")
    def follow_up(body: FollowUpRequest) -> dict:
        preset = _preset(body.preset)
        text = store.follow_up(body.session_id, body.question, manager, preset)
        return {"answer": text}

    @app.get("/v1/session/{session_id}/events")
    def session_events(session_id: str, start_ps: int | None = None, end_ps: int | None = None) -> dict:
        ev = store.query_events(session_id, start_ps=start_ps, end_ps=end_ps)
        return {"events": [e.model_dump() for e in ev]}

    @app.get("/v1/session/{session_id}/evidence/{evidence_id}")
    def session_evidence(session_id: str, evidence_id: str) -> dict:
        return store.explain_evidence(session_id, evidence_id)

    @app.post("/v1/inference")
    def inference_proxy(body: InferenceProxyBody) -> dict:
        from buscraft.models.inference import InferenceRequest, Message

        preset = QualityPreset.BALANCED
        msgs = [Message(role=m["role"], content=m["content"]) for m in body.messages]
        req = InferenceRequest(messages=msgs, max_tokens=body.max_tokens, temperature=body.temperature)
        resp = FallbackBackend(manager, preset).complete(req)
        return {"text": resp.text, "finish_reason": resp.finish_reason, "usage": resp.usage}

    return app


def _preset(name: str) -> QualityPreset:
    try:
        return QualityPreset(name.lower())
    except ValueError:
        return QualityPreset.BALANCED


def run_uvicorn() -> None:
    import uvicorn

    host = os.environ.get("BUSCRAFT_API_HOST", "127.0.0.1")
    port = int(os.environ.get("BUSCRAFT_API_PORT", "8765"))
    uvicorn.run(create_app(), host=host, port=port)
