"""Scoreboard mismatch extraction from logs."""

from __future__ import annotations

import re
from pathlib import Path

from buscraft.models.reasoning_document import ScoreboardMismatch

# expected: ... actual: ... OR EXP= / GOT=
_PAIR = re.compile(
    r"(?P<field>\w+)\s*:\s*(?:expected|exp)[=:]\s*(?P<exp>[^\s,]+).*"
    r"(?:actual|got|rcv)[=:]\s*(?P<act>[^\s,]+)",
    re.IGNORECASE,
)
_SIMPLE = re.compile(
    r"SCOREBOARD|MISMATCH|mismatch",
    re.IGNORECASE,
)


def parse_scoreboard_lines(
    path: Path | str,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> list[ScoreboardMismatch]:
    p = Path(path)
    lines = p.read_text(encoding=encoding, errors=errors).splitlines()
    out: list[ScoreboardMismatch] = []
    sc = 0
    for i, line in enumerate(lines):
        if not _SIMPLE.search(line):
            continue
        m = _PAIR.search(line)
        sc += 1
        if m:
            out.append(
                ScoreboardMismatch(
                    id=f"sb{sc}",
                    field=m.group("field"),
                    expected=m.group("exp"),
                    actual=m.group("act"),
                    text=line[:1500],
                    line_no=i + 1,
                )
            )
        else:
            out.append(
                ScoreboardMismatch(
                    id=f"sb{sc}",
                    text=line[:1500],
                    line_no=i + 1,
                )
            )
    return out
