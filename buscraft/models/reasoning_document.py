"""ReasoningDocument v1 — structured artifact for LLM and graph builder."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProvenanceEntry(BaseModel):
    source: str
    detail: str = ""


class FailureAnchor(BaseModel):
    id: str
    sim_time_ps: int | None = None
    source: str
    component: str = ""
    summary: str = ""


class LogEvent(BaseModel):
    id: str
    t_ps: int | None = None
    wall_time: str | None = None
    severity: str = "INFO"
    component: str = ""
    text: str = ""
    line_no: int | None = None


class AssertionRecord(BaseModel):
    id: str
    name: str = ""
    property_expr: str = ""
    t_ps: int | None = None
    component: str = ""
    text: str = ""
    signal_values: dict[str, str] = Field(default_factory=dict)


class ScoreboardMismatch(BaseModel):
    id: str
    t_ps: int | None = None
    component: str = ""
    field: str = ""
    expected: str = ""
    actual: str = ""
    text: str = ""
    line_no: int | None = None


class WaveWindow(BaseModel):
    start_ps: int
    end_ps: int


class SignalTrace(BaseModel):
    path: str
    transitions: list[list[int | float]] = Field(default_factory=list)


class WaveSlice(BaseModel):
    id: str
    anchor_id: str = ""
    window: WaveWindow
    signals: list[SignalTrace] = Field(default_factory=list)
    correlation_notes: list[str] = Field(default_factory=list)


class ProtocolTransaction(BaseModel):
    id: str
    kind: str = ""
    addr: str = ""
    beats: int = 0
    resp_observed: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class ProtocolContext(BaseModel):
    profile: str = "NONE"
    transactions: list[ProtocolTransaction] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)


class CoverageMetrics(BaseModel):
    log_parse_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    time_alignment_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    wave_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    notes: list[str] = Field(default_factory=list)


class ReasoningDocument(BaseModel):
    """Single merged artifact; LLM consumes this + KB snippets only."""

    schema_uri: str = Field(
        default="https://buscraft.local/schemas/reasoning-document-v1.json",
        alias="$schema",
    )
    version: int = 1
    build_id: str = "buscraft++-0.1.0"
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    failure_anchors: list[FailureAnchor] = Field(default_factory=list)
    events: list[LogEvent] = Field(default_factory=list)
    assertions: list[AssertionRecord] = Field(default_factory=list)
    scoreboard_mismatches: list[ScoreboardMismatch] = Field(default_factory=list)
    wave_slices: list[WaveSlice] = Field(default_factory=list)
    protocol_context: ProtocolContext = Field(default_factory=ProtocolContext)
    deterministic_summaries: dict[str, Any] = Field(default_factory=dict)
    coverage: CoverageMetrics = Field(default_factory=CoverageMetrics)

    model_config = {"populate_by_name": True}

    @field_validator("version")
    @classmethod
    def version_one(cls, v: int) -> int:
        if v != 1:
            raise ValueError("Only version 1 supported")
        return v

    def all_evidence_ids(self) -> set[str]:
        ids: set[str] = set()
        for a in self.failure_anchors:
            ids.add(a.id)
        for e in self.events:
            ids.add(e.id)
        for a in self.assertions:
            ids.add(a.id)
        for s in self.scoreboard_mismatches:
            ids.add(s.id)
        for w in self.wave_slices:
            ids.add(w.id)
        for t in self.protocol_context.transactions:
            ids.add(t.id)
        return ids
