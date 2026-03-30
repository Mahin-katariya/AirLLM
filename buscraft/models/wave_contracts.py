"""Wave slice request/response (GTKWave / reader abstraction)."""

from pydantic import BaseModel, Field


class WaveSliceRequest(BaseModel):
    dump_path: str
    start_ps: int
    end_ps: int
    signals: list[str] = Field(default_factory=list)
    timescale_hint: str | None = None


class WaveSliceResponse(BaseModel):
    slice_id: str
    signals: list[str] = Field(default_factory=list)
    format: str = "transitions"
    payload: str = ""
    error: str | None = None


class GTKWaveCommand(BaseModel):
    """Abstract jump/highlight for GTKWave automation."""

    dump_path: str
    jump_time_ps: int | None = None
    add_signals: list[str] = Field(default_factory=list)
    save_path: str | None = None
    tcl_script_path: str | None = None
