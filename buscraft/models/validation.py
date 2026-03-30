"""Validate HypothesisBundle against ReasoningDocument evidence IDs."""

from buscraft.models.hypothesis import Hypothesis, HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument


def validate_hypothesis_evidence(doc: ReasoningDocument, bundle: HypothesisBundle) -> tuple[bool, list[str]]:
    valid_ids = doc.all_evidence_ids()
    errors: list[str] = []
    for h in bundle.hypotheses:
        for eid in h.evidence_ids:
            if eid not in valid_ids:
                errors.append(f"hypothesis {h.id}: unknown evidence_id {eid!r}")
    return len(errors) == 0, errors


def strip_invalid_evidence(bundle: HypothesisBundle, doc: ReasoningDocument) -> HypothesisBundle:
    valid = doc.all_evidence_ids()
    new_h: list[Hypothesis] = []
    for h in bundle.hypotheses:
        kept = [e for e in h.evidence_ids if e in valid]
        new_h.append(h.model_copy(update={"evidence_ids": kept}))
    return bundle.model_copy(update={"hypotheses": new_h})
