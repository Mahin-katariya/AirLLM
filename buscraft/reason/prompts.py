"""Prompt packs for RCA, correlation, assertion explanation."""

from __future__ import annotations

import json

from buscraft.models.reasoning_document import ReasoningDocument


SYSTEM_BUSCRAFT = """You are a hardware verification assistant. Use ONLY the JSON facts provided.
Output a single JSON object matching HypothesisBundle schema keys:
failure_class, insufficient_data, insufficiency_reasons, hypotheses (array of objects with
id, statement, evidence_ids, confidence 0-1, recommended_next_checks).
Every evidence_ids entry MUST be an id from the document. No invented signal paths."""


def pack_root_cause(doc: ReasoningDocument) -> str:
    payload = doc.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(payload, indent=2, default=str)[:200_000]


def user_rca(class_name: str, checklist: list[str]) -> str:
    lines = "\n".join(f"- {c}" for c in checklist[:30])
    return (
        f"Failure class (hint): {class_name}\n"
        f"Protocol checklist:\n{lines}\n"
        "Produce HypothesisBundle JSON. Max 5 hypotheses. Cite evidence_ids only."
    )


def user_assertion_explanation(assertion_id: str, snippet: str) -> str:
    return f"Explain assertion failure {assertion_id} using only:\n{snippet}"


def user_signal_correlation(doc_slice: str) -> str:
    return "Correlate wave_slices and protocol transactions; output HypothesisBundle JSON.\n" + doc_slice
