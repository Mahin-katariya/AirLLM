"""Inference request/response contracts for all backends."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class InferenceRequest(BaseModel):
    messages: list[Message]
    max_tokens: int = 1024
    temperature: float = 0.2
    json_mode: bool = False
    grammar: str | None = None
    backend_id: str = "local_llamacpp"


class InferenceResponse(BaseModel):
    text: str
    finish_reason: str = "stop"
    usage: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None
