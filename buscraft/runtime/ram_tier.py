"""Map system RAM to quality preset capabilities."""

from __future__ import annotations

import sys


def available_ram_bytes() -> int:
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullAvailPhys)
        except Exception:
            return 8 * (1 << 30)
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    return int(parts[1]) * 1024
    except OSError:
        pass
    return 8 * (1 << 30)


def recommend_ctx_and_threads(preset: str, ram_bytes: int | None = None) -> dict:
    ram = ram_bytes if ram_bytes is not None else available_ram_bytes()
    gb = ram / (1 << 30)
    threads = 4 if gb >= 8 else 2
    if preset == "fast":
        return {"n_ctx": 4096, "n_threads": threads, "note": None}
    if preset == "balanced":
        if gb < 8:
            return {"n_ctx": 4096, "n_threads": threads, "note": "downgraded ctx: low RAM"}
        return {"n_ctx": 8192, "n_threads": threads, "note": None}
    # high
    if gb < 12:
        return {"n_ctx": 8192, "n_threads": threads, "note": "High preset downgraded: need ~12GB+ free for 16k ctx"}
    return {"n_ctx": 16384, "n_threads": threads, "note": None}
