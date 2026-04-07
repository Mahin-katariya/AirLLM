"""Hybrid failure classification: rules first, optional LLM enum."""

from __future__ import annotations

from buscraft.models.reasoning_document import ReasoningDocument

FAILURE_CLASSES = (
    "UNKNOWN",
    "UVM_FATAL_ERROR",
    "ASSERTION_FAILURE",
    "SCOREBOARD_MISMATCH",
    "BUS_PROTOCOL_RESPONSE_ERROR",
    "TIMEOUT_OR_STALL",
    "RESET_OR_CLOCK",
)


def classify_deterministic(doc: ReasoningDocument) -> tuple[str, float]:
    """Return (class, margin 0-1)."""
    if doc.assertions:
        return "ASSERTION_FAILURE", 0.9
    if doc.scoreboard_mismatches:
        return "SCOREBOARD_MISMATCH", 0.85
    for e in doc.events:
        u = e.text.upper()
        if "SLVERR" in u or "DECERR" in u or "BRESP" in u or "RRESP" in u:
            return "BUS_PROTOCOL_RESPONSE_ERROR", 0.8
        if "TIMEOUT" in u or "STALL" in u or "HANG" in u:
            return "TIMEOUT_OR_STALL", 0.75
        if "RESET" in u or "CLOCK" in u:
            return "RESET_OR_CLOCK", 0.65
    for a in doc.failure_anchors:
        if "fatal" in a.source.lower() or "error" in a.source.lower():
            return "UVM_FATAL_ERROR", 0.7
    return "UNKNOWN", 0.3
