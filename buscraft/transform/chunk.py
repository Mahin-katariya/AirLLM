"""Token-budget style trimming (heuristic by JSON size and event counts)."""

from __future__ import annotations

import json

from buscraft.models.reasoning_document import LogEvent, ReasoningDocument


def trim_document_for_context(
    doc: ReasoningDocument,
    *,
    max_events: int = 200,
    max_json_bytes: int = 512_000,
    max_transitions_per_signal: int = 100,
) -> ReasoningDocument:
    ev = doc.events
    if len(ev) > max_events:
        fatal = [e for e in ev if e.severity in ("FATAL", "ERROR")]
        tail = ev[-max(0, max_events - len(fatal)) :]
        merged: list[LogEvent] = fatal + [e for e in tail if e not in fatal]
        merged = merged[:max_events]
        doc = doc.model_copy(update={"events": merged})

    ws = []
    for w in doc.wave_slices:
        sigs = []
        for s in w.signals:
            tr = s.transitions[:max_transitions_per_signal]
            sigs.append(s.model_copy(update={"transitions": tr}))
        ws.append(w.model_copy(update={"signals": sigs}))
    doc = doc.model_copy(update={"wave_slices": ws})

    raw = json.dumps(doc.model_dump(by_alias=True), default=str)
    while len(raw.encode()) > max_json_bytes and doc.events:
        doc = doc.model_copy(update={"events": doc.events[1:]})
        raw = json.dumps(doc.model_dump(by_alias=True), default=str)

    return doc
