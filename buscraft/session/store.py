"""Interactive debug session: document, graph, hypotheses in memory."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import LogEvent, ReasoningDocument
from buscraft.reason.orchestrator import OrchestratorResult
from buscraft.runtime.manager import ModelRuntimeManager, QualityPreset


@dataclass
class SessionState:
    session_id: str
    document: ReasoningDocument
    last_result: OrchestratorResult | None = None
    history: list[dict] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self, doc: ReasoningDocument, result: OrchestratorResult | None = None) -> str:
        sid = str(uuid.uuid4())
        self._sessions[sid] = SessionState(session_id=sid, document=doc, last_result=result)
        return sid

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def query_events(self, session_id: str, *, start_ps: int | None = None, end_ps: int | None = None) -> list[LogEvent]:
        s = self._sessions.get(session_id)
        if not s:
            return []
        out: list[LogEvent] = []
        for e in s.document.events:
            if e.t_ps is None:
                continue
            if start_ps is not None and e.t_ps < start_ps:
                continue
            if end_ps is not None and e.t_ps > end_ps:
                continue
            out.append(e)
        return out

    def query_hypotheses(self, session_id: str) -> HypothesisBundle | None:
        s = self._sessions.get(session_id)
        if not s or not s.last_result:
            return None
        return s.last_result.bundle

    def explain_evidence(self, session_id: str, evidence_id: str) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"error": "unknown session"}
        d = s.document
        for coll, name in [
            (d.failure_anchors, "failure_anchor"),
            (d.events, "event"),
            (d.assertions, "assertion"),
            (d.scoreboard_mismatches, "scoreboard"),
            (d.wave_slices, "wave_slice"),
        ]:
            for x in coll:
                if x.id == evidence_id:
                    return {"kind": name, "payload": x.model_dump()}
        for t in d.protocol_context.transactions:
            if t.id == evidence_id:
                return {"kind": "transaction", "payload": t.model_dump()}
        return {"error": "evidence not found", "id": evidence_id}

    def follow_up(
        self,
        session_id: str,
        question: str,
        manager: ModelRuntimeManager,
        preset: QualityPreset,
    ) -> str:
        from buscraft.models.inference import InferenceRequest, Message

        s = self._sessions.get(session_id)
        if not s:
            return "Unknown session"
        scratch = s.document.model_dump_json()[:24_000]
        hy = ""
        if s.last_result:
            hy = s.last_result.bundle.model_dump_json()[:8000]
        backend = manager.get_backend(preset)
        req = InferenceRequest(
            messages=[
                Message(role="system", content="Answer using only the JSON context. If unknown, say insufficient data."),
                Message(role="user", content=f"Context:\n{scratch}\n\nHypotheses:\n{hy}\n\nQuestion: {question}"),
            ],
            max_tokens=512,
        )
        resp = backend.complete(req)
        s.history.append({"q": question, "a": resp.text})
        return resp.text
