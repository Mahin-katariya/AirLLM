"""Model manifest for silent download (URLs are placeholders; override via env or file)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelEntry:
    id: str
    url: str
    sha256: str
    filename: str


DEFAULT_MANIFEST: list[ModelEntry] = [
    ModelEntry(
        id="fast-3b-q4",
        url=os.environ.get("BUSCRAFT_MODEL_FAST_URL", ""),
        sha256="",
        filename="fast-3b-q4.gguf",
    ),
    ModelEntry(
        id="balanced-7b-q4",
        url=os.environ.get("BUSCRAFT_MODEL_BALANCED_URL", ""),
        sha256="",
        filename="balanced-7b-q4.gguf",
    ),
    ModelEntry(
        id="high-7b-q5",
        url=os.environ.get("BUSCRAFT_MODEL_HIGH_URL", ""),
        sha256="",
        filename="high-7b-q5.gguf",
    ),
]


def load_manifest(path: Path | None) -> list[ModelEntry]:
    if not path or not path.exists():
        return DEFAULT_MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ModelEntry(**x) for x in data.get("models", [])]
