"""Orchestrator: classify → hydrate template → LLM → validate → guardrails."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from buscraft.models.hypothesis import Hypothesis, HypothesisBundle
from buscraft.models.inference import InferenceRequest, Message
from buscraft.models.reasoning_document import ReasoningDocument
from buscraft.models.validation import strip_invalid_evidence, validate_hypothesis_evidence
from buscraft.protocols.loader import hydrate_protocol_context
from buscraft.reason.classifier import FAILURE_CLASSES, classify_deterministic
from buscraft.reason.guardrails import composite_confidence, evaluate_insufficient_data
from buscraft.reason.prompts import SYSTEM_BUSCRAFT, pack_root_cause, user_rca
from buscraft.runtime.backend import InferenceBackend
from buscraft.transform.chunk import trim_document_for_context


@dataclass
class OrchestratorResult:
    document: ReasoningDocument
    bundle: HypothesisBundle
    classifier_class: str
    confidence_breakdown: dict[str, float]
    raw_llm: str


_JSON_OBJ = re.compile(r"\{[\s\S]*\}")


def _parse_bundle(text: str) -> HypothesisBundle | None:
    m = _JSON_OBJ.search(text)
    if not m:
        return None
    try:
        return HypothesisBundle.model_validate_json(m.group(0))
    except Exception:
        return None


class ReasoningOrchestrator:
    def __init__(self, backend: InferenceBackend) -> None:
        self.backend = backend

    def run(
        self,
        doc: ReasoningDocument,
        *,
        use_critique: bool = False,
        max_tokens: int = 1024,
    ) -> OrchestratorResult:
        doc = hydrate_protocol_context(doc)
        doc = trim_document_for_context(doc)
        cls, margin = classify_deterministic(doc)
        protocol_hint = (
            doc.protocol_context.profile if doc.protocol_context.profile != "NONE" else ""
        )

        checklist = doc.protocol_context.checklist
        user = user_rca(cls, checklist)
        if protocol_hint:
            user += f"\nProtocol profile (context only): {protocol_hint}"
        req = InferenceRequest(
            messages=[
                Message(role="system", content=SYSTEM_BUSCRAFT),
                Message(role="user", content=pack_root_cause(doc)),
                Message(role="user", content=user + f"\nAllowed failure_class values: {FAILURE_CLASSES}"),
            ],
            max_tokens=max_tokens,
            temperature=0.15,
            json_mode=True,
        )
        resp = self.backend.complete(req)
        bundle = _parse_bundle(resp.text)
        if bundle is None:
            bundle = HypothesisBundle(
                failure_class=cls if cls in FAILURE_CLASSES else "UNKNOWN",
                insufficient_data=True,
                insufficiency_reasons=["llm_output_unparseable"],
                hypotheses=[
                    Hypothesis(
                        id="h_fallback",
                        statement="Could not parse model output; inspect events and anchors manually.",
                        evidence_ids=[doc.failure_anchors[0].id] if doc.failure_anchors else [],
                        confidence=0.2,
                    )
                ],
            )
        else:
            if bundle.failure_class == "UNKNOWN" and cls != "UNKNOWN" and cls in FAILURE_CLASSES:
                bundle = bundle.model_copy(update={"failure_class": cls})
            if not bundle.hypotheses and doc.failure_anchors:
                bundle = bundle.model_copy(
                    update={
                        "hypotheses": [
                            Hypothesis(
                                id="h_stub",
                                statement="No model output; review failure_anchors and events in the ReasoningDocument.",
                                evidence_ids=[doc.failure_anchors[0].id],
                                confidence=0.25,
                            )
                        ]
                    }
                )

        ok, _ = validate_hypothesis_evidence(doc, bundle)
        if not ok:
            bundle = strip_invalid_evidence(bundle, doc)
        bundle = evaluate_insufficient_data(doc, bundle)

        if use_critique:
            req2 = InferenceRequest(
                messages=[
                    Message(role="system", content=SYSTEM_BUSCRAFT),
                    Message(
                        role="user",
                        content=json.dumps(
                            {
                                "hypotheses": [h.model_dump() for h in bundle.hypotheses],
                                "coverage": doc.coverage.model_dump(),
                            }
                        ),
                    ),
                    Message(
                        role="user",
                        content="Critique: set insufficient_data true if any hypothesis contradicts coverage.",
                    ),
                ],
                max_tokens=512,
                json_mode=True,
            )
            r2 = self.backend.complete(req2)
            b2 = _parse_bundle(r2.text)
            if b2:
                bundle = b2

        breakdown = composite_confidence(classifier_margin=margin, doc=doc, bundle=bundle)
        return OrchestratorResult(
            document=doc,
            bundle=bundle,
            classifier_class=cls,
            confidence_breakdown=breakdown,
            raw_llm=resp.text,
        )
