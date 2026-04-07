"""Policy-driven inference: try local first, then remote."""

from __future__ import annotations

import os

from buscraft.models.inference import InferenceRequest, InferenceResponse
from buscraft.runtime.backend import InferenceBackend
from buscraft.runtime.llamacpp import LlamaCppSubprocessBackend
from buscraft.runtime.manager import ModelRuntimeManager, QualityPreset
from buscraft.runtime.remote_openai import OpenAICompatibleBackend


def complete_with_fallback(
    manager: ModelRuntimeManager,
    preset: QualityPreset,
    req: InferenceRequest,
    *,
    prefer_remote: bool = False,
) -> InferenceResponse:
    env_policy = os.environ.get("BUSCRAFT_INFERENCE_POLICY", "local_first")
    if prefer_remote or env_policy == "remote_first":
        if manager.remote_base_url:
            remote = OpenAICompatibleBackend(
                base_url=manager.remote_base_url,
                api_key=manager.remote_api_key,
                model=os.environ.get("BUSCRAFT_REMOTE_MODEL", "gpt-4o-mini"),
            )
            r = remote.complete(req)
            if r.finish_reason != "error" and '"error"' not in r.text[:120]:
                return r
        return manager.get_backend(preset).complete(req)

    local = manager.get_backend(preset, prefer_remote=False)
    if isinstance(local, LlamaCppSubprocessBackend) and local.health_check():
        r = local.complete(req)
        if r.finish_reason != "error" and "model not found" not in r.text.lower():
            return r
    if manager.remote_base_url:
        return OpenAICompatibleBackend(
            base_url=manager.remote_base_url,
            api_key=manager.remote_api_key,
            model=os.environ.get("BUSCRAFT_REMOTE_MODEL", "gpt-4o-mini"),
        ).complete(req)
    return local.complete(req)


class FallbackBackend(InferenceBackend):
    backend_id = "fallback_chain"

    def __init__(self, manager: ModelRuntimeManager, preset: QualityPreset) -> None:
        self.manager = manager
        self.preset = preset

    def complete(self, req: InferenceRequest) -> InferenceResponse:
        return complete_with_fallback(self.manager, self.preset, req)
