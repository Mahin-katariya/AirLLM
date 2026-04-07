"""HypothesisBundle — constrained LLM output."""

from pydantic import BaseModel, Field, field_validator


class Hypothesis(BaseModel):
    id: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    recommended_next_checks: list[str] = Field(default_factory=list)
    protocol_context: str = ""
    insufficiency_flags: list[str] = Field(default_factory=list)


class HypothesisBundle(BaseModel):
    failure_class: str = "UNKNOWN"
    insufficient_data: bool = False
    insufficiency_reasons: list[str] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)

    @field_validator("hypotheses")
    @classmethod
    def cap_hypotheses(cls, v: list[Hypothesis]) -> list[Hypothesis]:
        if len(v) > 8:
            return v[:8]
        return v
