"""OpenAI-compatible HTTP chat completions (remote inference)."""

from __future__ import annotations

from typing import Any

import httpx

from buscraft.models.inference import InferenceRequest, InferenceResponse, Message
from buscraft.runtime.backend import InferenceBackend


class OpenAICompatibleBackend(InferenceBackend):
    backend_id = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, req: InferenceRequest) -> InferenceResponse:
        url = f"{self.base_url}/v1/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [m.model_dump() for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(url, json=body, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            return InferenceResponse(
                text=text,
                finish_reason="stop",
                usage={
                    "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                    "completion_tokens": int(usage.get("completion_tokens", 0)),
                },
                raw=data,
            )
        except Exception as e:
            return InferenceResponse(text=f'{{"error":"{e!s}"}}', finish_reason="error")
