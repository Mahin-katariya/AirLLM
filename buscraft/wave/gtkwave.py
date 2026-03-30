"""GTKWave automation: TCL script generation and fallback instructions."""

from __future__ import annotations

from buscraft.models.wave_contracts import GTKWaveCommand


def build_gtkwave_tcl(cmd: GTKWaveCommand) -> str:
    """Generate a minimal GTKWave TCL script (3.3.x style; may need tweaks per install)."""
    lines = [
        "# Buscraft++ generated GTKWave script",
        f'gtkwave::loadFile "{_escape_tcl(cmd.dump_path)}"',
    ]
    if cmd.jump_time_ps is not None:
        lines.append(f'gtkwave::setWindowStartTime {_escape_num(cmd.jump_time_ps)}')
    for sig in cmd.add_signals:
        lines.append(f'gtkwave::addSignalsFromList "{_escape_tcl(sig)}"')
    if cmd.save_path:
        lines.append(f'gtkwave::saveFile "{_escape_tcl(cmd.save_path)}"')
    return "\n".join(lines) + "\n"


def _escape_tcl(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _escape_num(n: int) -> str:
    return str(n)


def build_fallback_instructions(cmd: GTKWaveCommand) -> str:
    sigs = "\n".join(cmd.add_signals)
    t = cmd.jump_time_ps
    return (
        "GTKWave manual steps:\n"
        f"1. Open dump: {cmd.dump_path}\n"
        f"2. Jump to time: {t}\n"
        "3. Add signals (copy-paste):\n"
        f"{sigs}\n"
    )
