"""Minimal VCD reader — transition lists for selected signals in a time window."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from buscraft.models.reasoning_document import SignalTrace, WaveSlice, WaveWindow

_VAR = re.compile(
    r"\$var\s+(?P<width>\d+)\s+(?P<type>\w+)\s+(?P<id>\S+)\s+(?P<path>[\S]+)\s+\$end"
)
_SCOPE = re.compile(r"\$scope\s+(\S+)\s+\$end")
_UP = re.compile(r"\$upscope\s+\$end")


def _parse_header(lines: iter[str]) -> tuple[dict[str, str], list[str]]:
    """Map var id -> hierarchical path; consume until $enddefinitions."""
    id_to_path: dict[str, str] = {}
    stack: list[str] = []
    for line in lines:
        if line.startswith("$var"):
            m = _VAR.match(line.strip())
            if m:
                rel = m.group("path")
                hier = ".".join(stack + [rel]) if stack else rel
                id_to_path[m.group("id")] = hier
        elif line.startswith("$scope"):
            m = _SCOPE.match(line.strip())
            if m:
                stack.append(m.group(1))
        elif line.startswith("$upscope"):
            if stack:
                stack.pop()
        elif line.startswith("$enddefinitions"):
            break
    return id_to_path, []


def extract_wave_slice_from_vcd(
    dump_path: Path | str,
    *,
    slice_id: str,
    anchor_id: str,
    start_ps: int,
    end_ps: int,
    signal_paths: list[str],
    max_transitions_per_signal: int = 500,
) -> WaveSlice:
    """
    Scan VCD once; collect transitions for signals whose hierarchical path matches.
    Times in VCD are typically in simulation units; caller must align scale to ps.
    """
    path = Path(dump_path)
    transitions: dict[str, list[list[int | float]]] = defaultdict(list)

    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines_iter = iter(f)
        id_to_path, _ = _parse_header(lines_iter)

    path_to_id: dict[str, str] = {}
    for vid, pth in id_to_path.items():
        path_to_id[pth] = vid
        if "." in pth:
            path_to_id[pth.split(".")[-1]] = vid

    wanted_ids: set[str] = set()
    for sp in signal_paths:
        vid = path_to_id.get(sp) or path_to_id.get(sp.split(".")[-1])
        if vid:
            wanted_ids.add(vid)

    current_time = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                try:
                    current_time = int(line[1:])
                except ValueError:
                    pass
                continue
            if line.startswith("$"):
                continue
            if len(line) >= 2 and line[0] in "01xzXZ":
                vid = line[1:]
                if vid not in wanted_ids:
                    continue
                if start_ps <= current_time <= end_ps:
                    p = id_to_path.get(vid, vid)
                    tr = transitions[p]
                    if len(tr) < max_transitions_per_signal:
                        val = 1 if line[0] == "1" else 0 if line[0] == "0" else line[0]
                        tr.append([current_time, val])
            elif len(line) >= 2 and line[-1] in id_to_path:
                # Alternate format: value without separator
                pass

    traces = [
        SignalTrace(path=sp, transitions=transitions.get(sp, transitions.get(sp.split(".")[-1], [])))
        for sp in signal_paths
    ]
    return WaveSlice(
        id=slice_id,
        anchor_id=anchor_id,
        window=WaveWindow(start_ps=start_ps, end_ps=end_ps),
        signals=traces,
        correlation_notes=[f"VCD scalar samples; times in dump units (often ps)"],
    )
