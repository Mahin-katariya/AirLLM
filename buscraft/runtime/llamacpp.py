"""llama.cpp via subprocess (llama-cli) — no GPU assumed."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from buscraft.models.inference import InferenceRequest, InferenceResponse, Message
from buscraft.runtime.backend import InferenceBackend


def find_llama_binary() -> str | None:
    for name in ("llama-cli", "llama-cli.exe", "main", "main.exe"):
        p = shutil.which(name)
        if p:
            return p
    env = os.environ.get("BUSCRAFT_LLAMA_CPP")
    if env and Path(env).exists():
        return env
    return None


class LlamaCppSubprocessBackend(InferenceBackend):
    """Invoke llama-cli -p prompt (single-turn); for chat, concatenates messages."""

    backend_id = "local_llamacpp"

    def __init__(
        self,
        model_path: Path | str,
        *,
        n_ctx: int = 4096,
        n_threads: int | None = None,
        binary: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads or max(1, (os.cpu_count() or 2) // 2)
        self.binary = binary or find_llama_binary()

    def complete(self, req: InferenceRequest) -> InferenceResponse:
        if not self.binary:
            return InferenceResponse(
                text='{"error":"llama-cli not found; set BUSCRAFT_LLAMA_CPP"}',
                finish_reason="error",
            )
        if not self.model_path.exists():
            return InferenceResponse(
                text=json.dumps({"error": f"model not found: {self.model_path}"}),
                finish_reason="error",
            )
        prompt = _messages_to_prompt(req.messages)
        args = [
            self.binary,
            "-m",
            str(self.model_path),
            "-n",
            str(req.max_tokens),
            "--ctx-size",
            str(self.n_ctx),
            "--threads",
            str(self.n_threads),
            "-p",
            prompt,
        ]
        if req.temperature <= 0.01:
            args.extend(["--temp", "0"])
        else:
            args.extend(["--temp", str(req.temperature)])
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=600,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return InferenceResponse(text="", finish_reason="timeout")
        out = (proc.stdout or "") + (proc.stderr or "")
        return InferenceResponse(text=out.strip(), finish_reason="stop" if proc.returncode == 0 else "error")

    def health_check(self) -> bool:
        return self.binary is not None and Path(self.binary).exists() and self.model_path.exists()


def _messages_to_prompt(messages: list[Message]) -> str:
    parts: list[str] = []
    for m in messages:
        parts.append(f"{m.role.upper()}:\n{m.content}")
    return "\n\n".join(parts)
