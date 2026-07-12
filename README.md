# stratadb — Strata for Python

The Python SDK for [Strata](https://stratadb.org): an **embedded** multi-model
database for AI agents. SQLite-shaped, not a server — it links the engine in
process and opens a file-backed (or in-memory) database directly.

Six primitives — key-value, JSON documents, vectors, an event log, and a graph
— share one branch-aware, time-travelling storage substrate. The SDK speaks the
exact same command surface, value shapes, and error codes as the `strata` CLI
and MCP server.

> **V1 rebuild in progress.** This branch is a ground-up rebuild on the V1
> engine, generated from the executor's IDL. The public typed namespaces
> (`db.kv`, `db.json`, …) are landing incrementally; today the foundation — the
> native binding, the typed error model, and the raw command escape hatch — is
> in place.

## Install

```bash
pip install stratadb
```

No Rust toolchain required — wheels are prebuilt (`abi3`, one per platform).

## Quickstart

```python
import stratadb

db = stratadb.Strata("./app-data")     # durable (creates if absent)
db = stratadb.Strata(cache=True)       # ephemeral, in-memory

with stratadb.Strata(cache=True) as db:
    db.execute({"type": "kv_put", "key": "Z3JlZXRpbmc=", "value": "aGVsbG8="})
    db.execute({"type": "kv_get", "key": "Z3JlZXRpbmc="})
```

`Strata()` never opens the current directory implicitly: pass a path, set
`STRATA_DB` (`stratadb.Strata.from_env()`), or use `cache=True`.

### The command escape hatch

`db.execute(command: dict) -> dict` runs any command on the executor's wire —
the same one the CLI and MCP server speak — and returns its `{"type", "data"}`
output envelope. It is the permanent, complete surface; the typed namespaces
build on it. KV keys and values are base64 on the wire.

### Errors

Every failure raises a typed `stratadb.errors.StrataError` subclass carrying a
stable `code`, `message`, `hint`, and `ref`. Match on `code`, never on message:

```python
from stratadb import errors

try:
    db.execute({"type": "kv_get", "key": "aGk=", "branch": "ghost"})
except errors.NotFoundError as e:
    assert e.code == "not_found.engine.branch"
    print(e.ref)  # https://stratadb.org/e/not_found.engine.branch
```

Misses are not errors — reads return `None`.

## For AI agents

`stratadb.agents_guide()` returns the complete offline usage guide (identical to
`strata agents guide`). `stratadb.mcp_config(path)` returns the MCP client-config
snippet.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install maturin pytest
maturin develop          # builds the native binding into the venv
pytest
```

The binding depends on the `strata-core` workspace's `strata-executor` crate
(data-plane features only). Local builds use a path dependency to a sibling
`../strata-core` checkout; releases pin a published rev.

## License

MIT
