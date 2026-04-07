# Buscraft++

Local-first AI debugging assistant for hardware verification. See `buscraft` package and `buscraft api` / `buscraft analyze` CLI.

## Install

```bash
pip install -e .
```

## Quick start

```bash
buscraft analyze --log sim.log --preset fast
buscraft api --host 127.0.0.1 --port 8765
```

Set `BUSCRAFT_LLAMA_CPP` to your `llama-cli` or `llama-server` binary for local inference.
