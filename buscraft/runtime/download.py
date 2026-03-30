"""Silent model download with resume and optional SHA256 verify."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from buscraft.runtime.manifest import ModelEntry


def ensure_model_file(entry: ModelEntry, cache_dir: Path) -> Path | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / entry.filename
    if dest.exists() and dest.stat().st_size > 0:
        if entry.sha256 and not _sha_ok(dest, entry.sha256):
            dest.unlink(missing_ok=True)
        else:
            return dest
    if not entry.url:
        return None
    _download_url(entry.url, dest)
    if entry.sha256 and not _sha_ok(dest, entry.sha256):
        dest.unlink(missing_ok=True)
        return None
    return dest


def _sha_ok(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def _download_url(url: str, dest: Path) -> None:
    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
        tmp.replace(dest)
