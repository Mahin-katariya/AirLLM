"""Local SQLite knowledge base for recurring failure patterns."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from buscraft.models.hypothesis import HypothesisBundle
from buscraft.models.reasoning_document import ReasoningDocument


def failure_signature(doc: ReasoningDocument, bundle: HypothesisBundle | None = None) -> str:
    parts: list[str] = []
    for a in doc.failure_anchors[:3]:
        parts.append(a.summary[:120])
    fc = bundle.failure_class if bundle else "UNKNOWN"
    parts.append(fc)
    for t in doc.protocol_context.transactions[:5]:
        parts.append(f"{t.kind}:{t.resp_observed}:{t.addr}")
    raw = "|".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:32]


class PatternKnowledgeBase:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS patterns (
                    sig TEXT PRIMARY KEY,
                    failure_class TEXT,
                    fix_text TEXT,
                    created REAL,
                    hits INTEGER DEFAULT 0
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sig TEXT,
                    doc_json TEXT,
                    ts REAL
                )
                """
            )

    def record_occurrence(self, sig: str, doc: ReasoningDocument) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO occurrences(sig, doc_json, ts) VALUES (?,?,?)",
                (sig, doc.model_dump_json()[:50_000], time.time()),
            )
            c.execute(
                "INSERT INTO patterns(sig, failure_class, fix_text, created, hits) VALUES (?,?,?,?,1)"
                " ON CONFLICT(sig) DO UPDATE SET hits = patterns.hits + 1",
                (sig, "", "", time.time()),
            )

    def suggest(self, sig: str, *, limit: int = 5) -> list[dict]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT sig, failure_class, fix_text, hits FROM patterns WHERE sig = ? LIMIT ?",
                (sig, limit),
            )
            rows = cur.fetchall()
        out = []
        for row in rows:
            out.append(
                {
                    "sig": row[0],
                    "failure_class": row[1],
                    "fix_text": row[2],
                    "hits": row[3],
                    "similarity": 1.0 if row[0] == sig else 0.3,
                }
            )
        return out

    def save_resolution(self, sig: str, failure_class: str, fix_text: str) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO patterns(sig, failure_class, fix_text, created, hits)
                VALUES (?,?,?,?,1)
                ON CONFLICT(sig) DO UPDATE SET
                    failure_class = excluded.failure_class,
                    fix_text = excluded.fix_text
                """,
                (sig, failure_class, fix_text, time.time()),
            )

    def export_bundle(self, dest: Path) -> None:
        with self._conn() as c:
            pats = c.execute("SELECT * FROM patterns").fetchall()
            occ = c.execute("SELECT * FROM occurrences").fetchall()
        dest.write_text(json.dumps({"patterns": pats, "occurrences": occ}, default=str), encoding="utf-8")
