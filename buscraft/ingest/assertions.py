"""Assertion failure blocks from simulation logs."""

from __future__ import annotations

import re
from pathlib import Path

from buscraft.models.reasoning_document import AssertionRecord

_ASSERT_START = re.compile(
    r"(?P<name>[\w$.]+)\s*:\s*assertion\s+failed|"
    r"AssertionError|"
    r"SVA\s*:\s*(?P<sva2>[^\n]+failed)",
    re.IGNORECASE,
)

_TIME_AT = re.compile(r"@\s*([^\s:]+)")


def parse_assertion_blocks(
    path: Path | str,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> list[AssertionRecord]:
    p = Path(path)
    lines = p.read_text(encoding=encoding, errors=errors).splitlines()
    out: list[AssertionRecord] = []
    ac = 0
    buf: list[str] = []
    in_block = False

    def flush() -> None:
        nonlocal ac, buf, in_block
        if not buf:
            in_block = False
            return
        text = "\n".join(buf)
        ac += 1
        tm = _TIME_AT.search(text)
        t_ps = None
        if tm:
            try:
                raw = tm.group(1).strip()
                if raw.lower().endswith("ns"):
                    t_ps = int(float(raw[:-2].strip()) * 1000)
                elif raw.lower().endswith("ps"):
                    t_ps = int(float(raw[:-2].strip()))
            except ValueError:
                t_ps = None
        m = _ASSERT_START.search(text)
        name = (m.group("name") if m and m.groupdict().get("name") else "") or (
            m.group("sva2")[:80] if m and m.groupdict().get("sva2") else "assertion"
        )
        out.append(
            AssertionRecord(
                id=f"as{ac}",
                name=name.strip()[:200],
                text=text[:2000],
                t_ps=t_ps,
            )
        )
        buf = []
        in_block = False

    for line in lines:
        if _ASSERT_START.search(line) or "assertion failed" in line.lower():
            if buf:
                flush()
            in_block = True
            buf.append(line)
            continue
        if in_block:
            buf.append(line)
            if len(buf) > 30:
                flush()

    if buf:
        flush()

    return out
