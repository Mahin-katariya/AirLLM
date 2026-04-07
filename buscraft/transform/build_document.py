"""Merge ingest + wave into ReasoningDocument."""

from __future__ import annotations

from pathlib import Path

from buscraft.ingest.assertions import parse_assertion_blocks
from buscraft.ingest.scoreboard import parse_scoreboard_lines
from buscraft.ingest.uvm import parse_uvm_log
from buscraft.models.reasoning_document import (
    CoverageMetrics,
    ProvenanceEntry,
    ProtocolContext,
    ReasoningDocument,
)
from buscraft.wave.correlation import correlate_log_wave_times, apply_correlation_to_coverage
from buscraft.wave.slicer import default_window_around_anchor
from buscraft.wave.vcd_reader import extract_wave_slice_from_vcd


def build_reasoning_document(
    log_path: Path | str,
    *,
    vcd_path: Path | str | None = None,
    protocol_profile: str = "NONE",
    signal_paths: list[str] | None = None,
    pre_ps: int = 100_000,
    post_ps: int = 100_000,
) -> ReasoningDocument:
    lp = Path(log_path)
    events, anchors = parse_uvm_log(lp)
    assertions = parse_assertion_blocks(lp)
    scoreboard = parse_scoreboard_lines(lp)

    provenance = [ProvenanceEntry(source=str(lp.resolve()), detail="log")]
    wave_slices = []
    cov = CoverageMetrics(
        log_parse_confidence=0.85 if events else 0.3,
        wave_completeness=0.0,
    )

    align, notes = correlate_log_wave_times(events)
    cov = apply_correlation_to_coverage(cov, align, notes)

    if vcd_path and anchors and signal_paths:
        vp = Path(vcd_path)
        provenance.append(ProvenanceEntry(source=str(vp.resolve()), detail="wave"))
        a0 = anchors[0]
        start, end = default_window_around_anchor(a0, pre_ps=pre_ps, post_ps=post_ps)
        ws = extract_wave_slice_from_vcd(
            vp,
            slice_id="ws1",
            anchor_id=a0.id,
            start_ps=start,
            end_ps=end,
            signal_paths=signal_paths,
        )
        wave_slices.append(ws)
        cov = cov.model_copy(update={"wave_completeness": 0.65})

    return ReasoningDocument(
        provenance=provenance,
        failure_anchors=anchors,
        events=events,
        assertions=assertions,
        scoreboard_mismatches=scoreboard,
        wave_slices=wave_slices,
        protocol_context=ProtocolContext(profile=protocol_profile),
    )
