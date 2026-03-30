"""Model runtime manager: presets, RAM, download, backend selection."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from buscraft.models.inference import InferenceRequest, InferenceResponse
from buscraft.runtime.backend import InferenceBackend
from buscraft.runtime.download import ensure_model_file
from buscraft.runtime.llamacpp import LlamaCppSubprocessBackend, find_llama_binary
from buscraft.runtime.manifest import ModelEntry, load_manifest
from buscraft.runtime.ram_tier import available_ram_bytes, recommend_ctx_and_threads
from buscraft.runtime.remote_openai import OpenAICompatibleBackend


class QualityPreset(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"


_PRESET_TO_ENTRY_ID = {
    QualityPreset.FAST: "fast-3b-q4",
    QualityPreset.BALANCED: "balanced-7b-q4",
    QualityPreset.HIGH: "high-7b-q5",
}


class ModelRuntimeManager:
    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        manifest_path: Path | None = None,
        remote_base_url: str | None = None,
        remote_api_key: str | None = None,
    ) -> None:
        self.cache_dir = cache_dir or Path(
            os.environ.get("BUSCRAFT_MODEL_DIR", Path.home() / ".cache" / "buscraft" / "models")
        )
        self.manifest_path = manifest_path
        self.remote_base_url = remote_base_url or os.environ.get("BUSCRAFT_REMOTE_URL")
        self.remote_api_key = remote_api_key or os.environ.get("BUSCRAFT_REMOTE_API_KEY")
        self._local_backend: InferenceBackend | None = None

    def preset_config(self, preset: QualityPreset) -> dict:
        ram = available_ram_bytes()
        tier = recommend_ctx_and_threads(preset.value, ram)
        entry_id = _PRESET_TO_ENTRY_ID[preset]
        return {"entry_id": entry_id, **tier}

    def resolve_local_model(self, preset: QualityPreset) -> Path | None:
        entries = load_manifest(self.manifest_path)
        entry_id = _PRESET_TO_ENTRY_ID[preset]
        entry = next((e for e in entries if e.id == entry_id), None)
        if not entry:
            return None
        p = ensure_model_file(entry, self.cache_dir)
        if p:
            return p
        override = os.environ.get(f"BUSCRAFT_MODEL_PATH_{preset.value.upper()}")
        if override and Path(override).exists():
            return Path(override)
        return None

    def get_backend(
        self,
        preset: QualityPreset,
        *,
        prefer_remote: bool = False,
    ) -> InferenceBackend:
        if prefer_remote and self.remote_base_url:
            return OpenAICompatibleBackend(
                base_url=self.remote_base_url,
                api_key=self.remote_api_key,
                model=os.environ.get("BUSCRAFT_REMOTE_MODEL", "gpt-4o-mini"),
            )
        model_path = self.resolve_local_model(preset)
        cfg = self.preset_config(preset)
        if model_path and find_llama_binary():
            self._local_backend = LlamaCppSubprocessBackend(
                model_path,
                n_ctx=cfg["n_ctx"],
            )
            return self._local_backend
        if self.remote_base_url:
            return OpenAICompatibleBackend(
                base_url=self.remote_base_url,
                api_key=self.remote_api_key,
                model=os.environ.get("BUSCRAFT_REMOTE_MODEL", "gpt-4o-mini"),
            )
        # Stub backend for dev without model
        return _StubBackend()

    def complete(self, preset: QualityPreset, req: InferenceRequest, **kwargs) -> InferenceResponse:
        return self.get_backend(preset, **kwargs).complete(req)


class _StubBackend(InferenceBackend):
    backend_id = "stub"

    def complete(self, req: InferenceRequest) -> InferenceResponse:
        return InferenceResponse(
            text=(
                '{"failure_class":"UNKNOWN","insufficient_data":true,'
                '"insufficiency_reasons":["No local model or remote URL configured"],'
                '"hypotheses":[]}'
            ),
            finish_reason="stop",
        )
