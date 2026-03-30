"""Export JSON Schema for ReasoningDocument and HypothesisBundle."""

import json
from pathlib import Path

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument


def reasoning_document_schema() -> dict:
    return ReasoningDocument.model_json_schema(by_alias=True)


def hypothesis_bundle_schema() -> dict:
    return HypothesisBundle.model_json_schema()


def write_schemas_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reasoning-document-v1.json").write_text(
        json.dumps(reasoning_document_schema(), indent=2),
        encoding="utf-8",
    )
    (out_dir / "hypothesis-bundle-v1.json").write_text(
        json.dumps(hypothesis_bundle_schema(), indent=2),
        encoding="utf-8",
    )
