"""Load YAML protocol templates and hydrate checklist + default signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from buscraft.models.reasoning_document import ProtocolContext, ProtocolTransaction, ReasoningDocument


@dataclass
class ProtocolTemplate:
    name: str
    profile: str
    required_signals: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    decode_hints: dict = field(default_factory=dict)


def _pkg_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def load_protocol_template(profile: str) -> ProtocolTemplate | None:
    key = profile.upper().replace("-", "_")
    fname = f"{key.lower()}.yaml"
    for base in (_pkg_templates_dir(), Path.cwd() / "protocol_templates"):
        p = base / fname
        if p.exists():
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return ProtocolTemplate(
                name=raw.get("name", profile),
                profile=raw.get("profile", profile),
                required_signals=list(raw.get("required_signals", [])),
                failure_modes=list(raw.get("failure_modes", [])),
                checklist=list(raw.get("checklist", [])),
                decode_hints=dict(raw.get("decode_hints", {})),
            )
    return None


def hydrate_protocol_context(doc: ReasoningDocument) -> ReasoningDocument:
    prof = doc.protocol_context.profile
    tpl = load_protocol_template(prof)
    if not tpl:
        return doc
    pc = doc.protocol_context
    merged_check = list(dict.fromkeys(pc.checklist + tpl.checklist))
    txns = list(pc.transactions)
    # Heuristic AXI SLVERR from log text
    for ev in doc.events:
        t = ev.text.upper()
        if "SLVERR" in t or "SLAVE ERROR" in t:
            txns.append(
                ProtocolTransaction(
                    id=f"txn_from_{ev.id}",
                    kind="WRITE" if "WRITE" in t else "READ",
                    resp_observed="SLVERR",
                    evidence_ids=[ev.id],
                )
            )
    return doc.model_copy(
        update={
            "protocol_context": pc.model_copy(
                update={"checklist": merged_check, "transactions": txns}
            ),
            "deterministic_summaries": {
                **doc.deterministic_summaries,
                "protocol_template": tpl.name,
                "failure_mode_hints": tpl.failure_modes[:10],
            },
        }
    )
