"""Align log times to waveform dump timescale; emit notes."""

from __future__ import annotations

from buscraft.models.reasoning_document import CoverageMetrics, LogEvent


def correlate_log_wave_times(
    events: list[LogEvent],
    *,
    vcd_timescale: str | None = None,
    log_claims_ps: bool = True,
) -> tuple[float, list[str]]:
    """
    Return (time_alignment_confidence, notes).
    Heuristic: if we have events with t_ps and vcd uses same order of magnitude, high confidence.
    """
    notes: list[str] = []
    if vcd_timescale:
        notes.append(f"dump timescale: {vcd_timescale}")
    with_t = [e for e in events if e.t_ps is not None]
    if not with_t:
        notes.append("no parsed log times; alignment unknown")
        return 0.4, notes
    if log_claims_ps:
        notes.append("log times interpreted as ps/ns where marked")
        return 0.78, notes
    return 0.55, notes


def apply_correlation_to_coverage(cov: CoverageMetrics, alignment: float, wave_notes: list[str]) -> CoverageMetrics:
    return cov.model_copy(
        update={
            "time_alignment_confidence": alignment,
            "notes": list(cov.notes) + wave_notes,
        }
    )
