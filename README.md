# stratadb — Strata for Python

The Python SDK for [Strata](https://stratadb.org): an **embedded** multi-model
database for AI agents. SQLite-shaped, not a server — it links the engine in
process and opens a file-backed (or in-memory) database directly.

Six primitives — key-value, JSON documents, vectors, an event log, and a graph
— share one branch-aware, time-travelling storage substrate. The SDK speaks the
exact same command surface, value shapes, and error codes as the `strata` CLI
and MCP server, so learning one channel is learning all of them.

## Install

```bash
pip install stratadb
```

No Rust toolchain required — wheels are prebuilt (`abi3`, one per platform,
Python 3.9+).

## Quickstart

```python
import stratadb

db = stratadb.Strata("./app-data")      # durable (creates if absent)
# db = stratadb.Strata(cache=True)      # ephemeral, in-memory

# Key-value
db.kv.put("greeting", "hello")
db.kv.get("greeting")                    # b"hello"

# JSON documents
db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
db.json.get("user:1", "$.name")          # "Ada"

# Vectors (similarity search with metadata filters)
from stratadb import filters
db.vectors.create_collection("notes", dimension=3)
db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3], metadata={"kind": "note"})
hits = db.vectors.query("notes", [0.1, 0.2, 0.3], k=5,
                        filter=filters.eq("kind", "note"))

# Events (append-only, hash-chained)
db.events.append("signup", {"user": "ada"})

# Graph
db.graphs.create("social")
db.graphs.add_node("social", "ada")
db.graphs.add_edge("social", "ada", "follows", "grace")

db.close()   # or: with stratadb.Strata("./app-data") as db: ...
```

`Strata()` never opens the current directory implicitly: pass a path, set
`STRATA_DB` (`stratadb.Strata.from_env()`), or use `cache=True`.

## Branches, spaces, and time travel

```python
db.branches.fork("main", "experiment")   # copy-on-write branch
exp = db.at(branch="experiment")          # a scoped view over the same handle
exp.kv.put("k", "only-on-experiment")

receipt = db.kv.put("k", "v1")
db.kv.put("k", "v2")
db.kv.get("k", as_of=receipt.commit.timestamp)   # b"v1" — every read takes as_of
```

## Errors

Every failure raises a typed `stratadb.errors.StrataError` subclass carrying a
stable `code`, `message`, `hint`, and `ref`. Match on `code`, never on message:

```python
from stratadb import errors

try:
    db.at(branch="ghost").kv.get("k")
except errors.NotFoundError as e:
    assert e.code == "not_found.engine.branch"
    print(e.ref)   # https://stratadb.org/e/not_found.engine.branch
```

Misses are not errors — reads return `None`.

## For AI agents

- `stratadb.agents_guide()` — the complete offline usage guide (identical to
  `strata agents guide`).
- `stratadb.command_index()` — the full command catalog bundled in the wheel.
- `stratadb.mcp_config(path)` — the MCP client-config snippet.
- `db.execute(command: dict) -> dict` — the raw command escape hatch (the same
  wire the CLI and MCP speak); the typed namespaces build on it.

## Architecture

Three layers: handwritten ergonomic **namespaces** over a **generated core**
(one typed method + model per command, generated from the engine's IDL) over a
tiny **PyO3 binding** that links the engine in process. Data-plane only —
generated fresh from the IDL, drift-guarded in CI.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install maturin pytest
maturin develop            # builds the native binding into the venv
python tools/generate.py   # regenerates the typed core from idl/v1/
pytest
```

Local builds use a path dependency to a sibling `../strata-core` checkout;
releases pin the git rev in `idl/v1/STRATA_CORE_REV` (`tools/release_prep.py`).

## License

MIT
