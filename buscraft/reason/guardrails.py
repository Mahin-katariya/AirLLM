"""Insufficient data detection and confidence composition."""

from __future__ import annotations

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument
from buscraft.models.validation import validate_hypothesis_evidence


def evaluate_insufficient_data(doc: ReasoningDocument, bundle: HypothesisBundle) -> HypothesisBundle:
    reasons: list[str] = []
    if doc.coverage.wave_completeness < 0.4 and any("wave" in h.statement.lower() for h in bundle.hypotheses):
        reasons.append("wave_completeness_low_for_wave_claims")
    if doc.coverage.time_alignment_confidence < 0.5:
        reasons.append("time_alignment_uncertain")
    ok, errs = validate_hypothesis_evidence(doc, bundle)
    if not ok:
        reasons.extend(errs[:5])
    if reasons:
        return bundle.model_copy(
            update={
                "insufficient_data": True,
                "insufficiency_reasons": list(dict.fromkeys(bundle.insufficiency_reasons + reasons)),
            }
        )
    return bundle


def composite_confidence(
    *,
    classifier_margin: float,
    doc: ReasoningDocument,
    bundle: HypothesisBundle,
) -> dict[str, float]:
    w1, w2, w3, w4, w5 = 0.25, 0.25, 0.2, 0.2, 0.1
    evidence_strength = min(1.0, max(len(h.evidence_ids) for h in bundle.hypotheses) / 5.0) if bundle.hypotheses else 0.0
    contradiction = 1.0 if bundle.insufficient_data else 0.0
    base = (
        w1 * classifier_margin
        + w2 * evidence_strength
        + w3 * doc.coverage.time_alignment_confidence
        + w4 * doc.coverage.log_parse_confidence
        - w5 * contradiction
    )
    return {
        "classifier_margin": classifier_margin,
        "evidence_strength": evidence_strength,
        "time_alignment": doc.coverage.time_alignment_confidence,
        "log_parse": doc.coverage.log_parse_confidence,
        "contradiction_penalty": contradiction,
        "composite": max(0.0, min(1.0, base)),
    }
