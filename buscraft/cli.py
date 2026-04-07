"""CLI: analyze logs, export schemas, run API server."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from buscraft.kb.patterns import PatternKnowledgeBase, failure_signature
from buscraft.models.schema_export import write_schemas_dir
from buscraft.reason.orchestrator import ReasoningOrchestrator
from buscraft.runtime.fallback import FallbackBackend
from buscraft.runtime.manager import ModelRuntimeManager, QualityPreset
from buscraft.transform.build_document import build_reasoning_document
from buscraft.viz.dot import to_graphviz_dot
from buscraft.viz.ranker import rank_root_causes
from buscraft.wave.gtkwave import build_fallback_instructions, build_gtkwave_tcl
from buscraft.models.wave_contracts import GTKWaveCommand


def cmd_analyze(args: argparse.Namespace) -> int:
    preset = QualityPreset(args.preset.lower())
    manager = ModelRuntimeManager()
    signals = [s.strip() for s in args.signals.split(",") if s.strip()] if args.signals else []
    doc = build_reasoning_document(
        args.log,
        vcd_path=args.vcd,
        protocol_profile=args.protocol,
        signal_paths=signals or None,
    )
    orch = ReasoningOrchestrator(FallbackBackend(manager, preset))
    result = orch.run(doc, use_critique=args.critique)
    if args.kb:
        kb = PatternKnowledgeBase(args.kb)
        sig = failure_signature(result.document, result.bundle)
        kb.record_occurrence(sig, result.document)
    out = {
        "classifier_class": result.classifier_class,
        "confidence_breakdown": result.confidence_breakdown,
        "bundle": result.bundle.model_dump(),
        "ranked_root_causes": [
            {"node": n, "score": s, "trace": tr} for n, s, tr in rank_root_causes(result.document, result.bundle)
        ],
    }
    if args.dot:
        Path(args.dot).write_text(to_graphviz_dot(result.document, result.bundle), encoding="utf-8")
    if args.vcd and doc.failure_anchors:
        t = doc.failure_anchors[0].sim_time_ps or 0
        cmd = GTKWaveCommand(dump_path=str(Path(args.vcd).resolve()), jump_time_ps=t, add_signals=signals)
        tcl_path = Path(args.gtkwave_tcl) if args.gtkwave_tcl else Path("buscraft_gtkwave.tcl")
        tcl_path.write_text(build_gtkwave_tcl(cmd), encoding="utf-8")
        print(build_fallback_instructions(cmd))
    print(json.dumps(out, indent=2))
    return 0


def cmd_export_schemas(args: argparse.Namespace) -> int:
    d = Path(args.out)
    write_schemas_dir(d)
    print(f"Wrote schemas to {d}")
    return 0


def cmd_api(args: argparse.Namespace) -> int:
    from buscraft.api.app import run_uvicorn

    import os

    os.environ["BUSCRAFT_API_HOST"] = args.host
    os.environ["BUSCRAFT_API_PORT"] = str(args.port)
    run_uvicorn()
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="buscraft")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("analyze", help="Build ReasoningDocument and run orchestrator")
    pa.add_argument("--log", required=True, help="Path to simulation log")
    pa.add_argument("--vcd", default=None, help="Optional VCD path")
    pa.add_argument("--protocol", default="NONE", help="Protocol profile e.g. AXI4_LITE")
    pa.add_argument("--signals", default="", help="Comma-separated hierarchical signal paths")
    pa.add_argument("--preset", default="balanced", choices=["fast", "balanced", "high"])
    pa.add_argument("--critique", action="store_true")
    pa.add_argument("--dot", default=None, help="Write Graphviz DOT file")
    pa.add_argument("--gtkwave-tcl", default=None, help="Write GTKWave TCL script path")
    pa.add_argument("--kb", default=None, help="SQLite KB path to record occurrence")
    pa.set_defaults(func=cmd_analyze)

    pe = sub.add_parser("export-schemas", help="Write JSON Schema files")
    pe.add_argument("--out", default="schemas", help="Output directory")
    pe.set_defaults(func=cmd_export_schemas)

    ps = sub.add_parser("api", help="Run FastAPI server")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8765)
    ps.set_defaults(func=cmd_api)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
