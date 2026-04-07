"""UVM log line parser — deterministic regex + state machine."""

from __future__ import annotations

import re
from pathlib import Path

from buscraft.models.reasoning_document import FailureAnchor, LogEvent

# Common UVM severity lines (simulator-specific prefixes may precede)
_UVM_SEV = re.compile(
    r"UVM_(?P<sev>FATAL|ERROR|WARNING|INFO|DEBUG)\s+"
    r"(?:@\s*(?P<time>[^\s:]+)\s*:\s*)?"
    r"(?:\[(?P<comp>[^\]]+)\]\s*)?"
    r"(?P<rest>.*)",
    re.IGNORECASE,
)

_UVM_ALT = re.compile(
    r"UVM_(?P<sev>FATAL|ERROR|WARNING|INFO|DEBUG)\s+"
    r"(?P<path>[^\s]+\.sv\(\d+\))?\s*"
    r"(?:@\s*(?P<time>[^\s:]+)\s*)?"
    r"(?P<rest>.*)",
    re.IGNORECASE,
)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)


def _parse_time_to_ps(time_str: str | None) -> int | None:
    if not time_str:
        return None
    t = time_str.strip().lower().replace(" ", "")
    mult = 1
    if t.endswith("ps"):
        mult, t = 1, t[:-2]
    elif t.endswith("ns"):
        mult, t = 1000, t[:-2]
    elif t.endswith("us"):
        mult, t = 1_000_000, t[:-2]
    elif t.endswith("ms"):
        mult, t = 1_000_000_000, t[:-2]
    elif t.endswith("fs"):
        mult, t = 1 / 1000, t[:-2] 
    elif t.endswith("s") and not (t.endswith("ns") or t.endswith("us") or t.endswith("ms") or t.endswith("fs") or t.endswith("ps")):
        mult, t = int(1e12), t[:-1]
    try:
        return int(float(t) * mult)
    except ValueError:
        return None


def parse_uvm_log(
    path: Path | str,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> tuple[list[LogEvent], list[FailureAnchor]]:
    """Parse a text log; return events and failure anchors (FATAL/ERROR)."""
    p = Path(path)
    text = p.read_text(encoding=encoding, errors=errors)
    lines = text.splitlines()
    events: list[LogEvent] = []
    anchors: list[FailureAnchor] = []
    ev_counter = 0

    for i, raw in enumerate(lines, start=1):
        line = strip_ansi(raw).strip()
        if "UVM_" not in line:
            continue
        m = _UVM_SEV.search(line) or _UVM_ALT.search(line)
        if not m:
            continue
        sev = m.group("sev").upper()
        comp = (m.groupdict().get("comp") or "").strip()
        time_raw = m.groupdict().get("time")
        rest = (m.group("rest") or "").strip()
        t_ps = _parse_time_to_ps(time_raw) if time_raw else None
        ev_counter += 1
        eid = f"ev{ev_counter}"
        events.append(
            LogEvent(
                id=eid,
                t_ps=t_ps,
                severity=sev,
                component=comp,
                text=rest or line,
                line_no=i,
            )
        )
        if sev in ("FATAL", "ERROR"):
            aid = f"fa{len(anchors) + 1}"
            anchors.append(
                FailureAnchor(
                    id=aid,
                    sim_time_ps=t_ps,
                    source="uvm_" + sev.lower(),
                    component=comp,
                    summary=(rest or line)[:500],
                )
            )

    return events, anchors
