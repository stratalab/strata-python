# stratadb — Python SDK agent guide

Strata is an **embedded** multi-model database (like SQLite/DuckDB — in-process,
no server). One database exposes six primitives over one branch-aware,
time-travelling store: **key-value, JSON documents, vectors, an event log,
graphs**, plus **inference** (`db.ai`). This guide is the offline, Python-native
usage reference for the installed version; it is returned by
`stratadb.agents_guide()`.

Conventions in this guide: every snippet is real, runnable Python. Reads return
`None` on a miss (never raise); domain failures raise a typed
`stratadb.errors.StrataError` you match on `.code`, never on message text.

## Install & open

```python
import stratadb

db = stratadb.open("./app-data")     # durable (created if absent)
db = stratadb.open(cache=True)       # ephemeral, in-memory (nothing persists)
db = stratadb.from_env()              # path from $STRATA_DB
with stratadb.open(cache=True) as db:
    ...                                # context manager closes it
```

`stratadb.open()` never opens the current directory implicitly — pass a path, set
`STRATA_DB`, or use `cache=True`, or it raises `InvalidArgumentError`.

## Key-value — `db.kv`

Keys and values are `str` (UTF-8) or `bytes`; reads return `bytes` or `None`.

```python
db.kv.put("greeting", "hello")
db.kv.get("greeting")                  # b'hello'
db.kv.get("absent")                    # None
db.kv.exists("greeting")               # True
db.kv.put_many({"a": "1", "b": "2"})
db.kv.get_many(["a", "b", "x"])        # [b'1', b'2', None]
db.kv.count()                          # int; count(prefix=...) to scope
for key in db.kv.iter_keys(prefix="user:"):   # auto-paginates
    ...
```

## JSON documents — `db.json`

```python
db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})  # -> Record(.commit, .effect, .key)
db.json.get("user:1", "$.name")        # 'Ada'
db.json.get("user:1")                  # {'name': 'Ada', 'roles': ['admin']}  (bare value; None on miss)
db.json.exists("user:1")               # True
db.json.set_many({"a": {"x": 1}, "b": {"x": 2}})   # -> BatchResult(.status, .items)
```

## Vectors — `db.vectors`

```python
from stratadb import filters
db.vectors.create_collection("notes", dimension=3, metric="cosine")
db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3], metadata={"kind": "note"})
hits = db.vectors.query("notes", [0.1, 0.2, 0.3], k=5,
                        filter=filters.eq("kind", "note"))   # AND-of-equality; -> list[VectorMatch]
for h in hits:
    h.key, h.score, h.metadata         # VectorMatch(.key: str, .score: float, .metadata)
```

Pair with `db.ai.embed(...)` to build a semantic index: embed text, upsert the
vector, then query with an embedded query.

## Event log — `db.events` (append-only, hash-chained)

```python
db.events.append("signup", {"user": "ada"})   # -> Record(.commit, .effect, .event_type, .sequence)
db.events.len()                        # 1
ev = db.events.get(0)                  # -> EventVersionedData(.event, .timestamp, .version)
ev.event.event_type, ev.event.payload  # ('signup', {'user': 'ada'})
for e in db.events.range(start=0):     # ordered replay (a Page of EventVersionedData)
    ...
db.events.verify_chain().valid         # True — integrity check
```

## Graph — `db.graphs`

```python
db.graphs.create("social")
db.graphs.add_node("social", "ada")
db.graphs.add_node("social", "grace")
db.graphs.add_edge("social", "ada", "follows", "grace")
db.graphs.list()                       # -> ['social']  (list[str] of graph names)
for n in db.graphs.neighbors("social", "ada"):   # each -> GraphNeighborHit
    n.node_id                          # 'grace' — the neighbor, in any direction
```

Use `n.node_id` for the neighbor: it is the other endpoint for both `direction="outgoing"`
and `direction="incoming"`. `n.dst` is the edge's dst, which for `direction="incoming"` is the
node you queried, not the neighbor — copying `.dst` verbatim gives the wrong node on incoming
traversal.

## Inference — `db.ai` (OpenAI-shaped; cloud + local)

Cloud specs are `openai:MODEL` / `anthropic:MODEL` / `google:MODEL`; a bare
`MODEL` (or `local:MODEL`) is a local GGUF. Cloud needs a key (below).

```python
r = db.ai.chat("Explain embeddings in one sentence.",
               model="openai:gpt-4o-mini", max_tokens=60)
r.content                              # the text

# Multi-turn: messages is a list of {"role","content"} dicts
db.ai.chat([{"role": "system", "content": "Be terse."},
            {"role": "user", "content": "hi"}], model="openai:gpt-4o-mini")

# Structured output (JSON Schema)
r = db.ai.chat("Capital of France and its population?",
               model="anthropic:claude-haiku-4-5-20251001",
               json_schema={"type": "object",
                            "properties": {"capital": {"type": "string"},
                                           "population": {"type": "integer"}},
                            "required": ["capital", "population"]})
# r.content is a JSON string matching the schema

# Tool / function calling
r = db.ai.chat("Weather in Paris?", model="google:gemini-2.5-flash",
               tools=[{"type": "function",
                       "function": {"name": "get_weather",
                                    "parameters": {"type": "object",
                                                   "properties": {"city": {"type": "string"}},
                                                   "required": ["city"]}}}],
               tool_choice="required")
r.tool_calls                           # [{'id':..,'function':{'name':'get_weather','arguments':'{"city":"Paris"}'}}]

# Embeddings
e = db.ai.embed(["hello", "world"], model="openai:text-embedding-3-small")
e.vectors                              # [[...], [...]];  e.vector for one input

# Reuse load params: db.ai.model(spec, **load_config)
qwen = db.ai.model("local:qwen3", n_ctx=8192)
qwen.chat("Summarize: ...")

db.ai.capability("openai:gpt-4o-mini") # supported features; no network call
```

### Provider API keys (bring your own — Strata ships none)

Resolution order is **environment variable, then the stored config**:

```bash
export OPENAI_API_KEY=sk-...           # or ANTHROPIC_API_KEY / GOOGLE_API_KEY
strata config set openai.api_key sk-...   # persisted (0600); env still wins
```

A cloud call with no key raises `FailedPreconditionError` with code
`inference.missing_api_key` and a message naming the env var and where to get a
key.

## Branches & time travel

Every write returns a receipt. `commit.version` and `commit.timestamp` are the
same small **logical** commit counter (not wall-clock time) — pass either to a
read's `as_of` to see that historical state:

```python
receipt = db.kv.put("k", "v1")         # -> Record; receipt.commit.version == receipt.commit.timestamp (a logical counter)
db.kv.put("k", "v2")
db.kv.get("k", as_of=receipt.commit.timestamp)   # b'v1' — as_of takes the logical commit value, not wall-clock µs

# fork() copies the source branch (copy-on-write); create() makes an EMPTY branch.
db.branches.fork("default", "feature")  # feature starts as a copy of default
db.branches.list()
feature = db.at(branch="feature")       # a scoped view; writes target the branch
feature.kv.put("k", "on-feature")       # diverges from default without touching it
```

Prefer `fork` when the new branch should start from existing data;
`db.branches.create(name)` makes an **empty** branch. Fork a point in history
with `db.branches.fork_at_version(source, name, receipt.commit.version)` or
`db.branches.fork_at_timestamp(source, name, receipt.commit.timestamp)`.
(`event.timestamp` is the one wall-clock value, in microseconds;
`db.events.range_by_time(...)` is the only API that takes wall-clock µs.)

`db.spaces` manages product spaces (isolated namespaces); `db.at(space=...)`
scopes a view.

## Errors

Every domain failure raises a `stratadb.errors.StrataError` subclass. Match on
the stable `.code` (`<class>.<area>.<detail>`), never on message text:

```python
from stratadb import errors
try:
    db.at(branch="ghost").kv.get("k")     # reading a nonexistent branch raises
except errors.NotFoundError as e:
    e.code           # "not_found.engine.branch"
    e.hint, e.ref    # actionable hint + a docs URL
```

## Gotchas / known sharp edges

Exact failure modes worth recognizing up front (match on the `.code`, not the message):

- **`open()` needs an explicit target.** `stratadb.open()` with neither a path nor
  `cache=True` raises `InvalidArgumentError` (`invalid_argument.cli.no_database`) —
  Strata never opens the current directory implicitly. Pass a path, set `STRATA_DB`
  (`stratadb.from_env()`), or use `cache=True`.
- **Cloud `db.ai.*` needs a provider key.** A keyless cloud call raises
  `FailedPreconditionError` (`inference.missing_api_key`), and the message names the
  env var — it's a setup issue, not a bug. Set `OPENAI_API_KEY` (or the provider's).
- **Embeddings need a key too.** `db.ai.embed(...)` is a cloud call; there is no
  bundled offline/keyless embedder yet. For keyless vector search, upsert literal
  vectors (`db.vectors.upsert(coll, key, [0.1, 0.2, ...])`), as `python -m stratadb.demo`
  does.
- **`db.state` was removed in V1.** Accessing it raises `UnsupportedError`
  (`unsupported.sdk.state_removed`) — use `db.kv` for keyed values or `db.json` for
  structured documents.

## Admin & Arrow — `db.admin`, `db.arrow`

`db.admin` reads control-plane facts (never writes): `db.admin.ping()`
(liveness), `db.admin.info()` (identity + catalog summary), plus
`db.admin.health()`, `db.admin.metrics()`, `db.admin.describe()`, and
`db.admin.config()`.

`db.arrow` bulk-moves a primitive to and from an Arrow/Parquet file:

```python
db.arrow.export("kv", "backup.parquet")     # a primitive -> Arrow file
db.arrow.import_("kv", "backup.parquet")    # Arrow file -> primitive (note the trailing _)
```

## Escape hatch & introspection

```python
db.execute({"type": "kv_scan", "limit": 10})   # raw command wire -> {"type","data"}
stratadb.command_index()               # full offline command catalog (ids, kinds, docs)
stratadb.agents_guide()                # this guide
stratadb.demo()                        # a runnable, zero-setup tour (or: python -m stratadb.demo)
stratadb.init("path/to/repo")          # scaffold the agent skill + AGENTS.md into a repo
stratadb.__version__                   # the SDK version (engine version: db.admin.ping().version)
```

`db.execute(...)` is the permanent, lossless escape hatch to the full command
surface (the same wire the CLI and MCP server speak); the typed namespaces above
build on it.
