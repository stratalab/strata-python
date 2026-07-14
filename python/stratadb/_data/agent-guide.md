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

db = stratadb.Strata("./app-data")     # durable (created if absent)
db = stratadb.Strata(cache=True)       # ephemeral, in-memory (nothing persists)
db = stratadb.Strata.from_env()        # path from $STRATA_DB
with stratadb.Strata(cache=True) as db:
    ...                                # context manager closes it
```

`Strata()` never opens the current directory implicitly — pass a path, set
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
db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
db.json.get("user:1", "$.name")        # 'Ada'
db.json.get("user:1")                  # {'name': 'Ada', 'roles': ['admin']}
db.json.exists("user:1")               # True
db.json.set_many({"a": {"x": 1}, "b": {"x": 2}})
```

## Vectors — `db.vectors`

```python
from stratadb import filters
db.vectors.create_collection("notes", dimension=3, metric="cosine")
db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3], metadata={"kind": "note"})
hits = db.vectors.query("notes", [0.1, 0.2, 0.3], k=5,
                        filter=filters.eq("kind", "note"))   # AND-of-equality
for h in hits:
    h.key, h.score
```

Pair with `db.ai.embed(...)` to build a semantic index: embed text, upsert the
vector, then query with an embedded query.

## Event log — `db.events` (append-only, hash-chained)

```python
db.events.append("signup", {"user": "ada"})
db.events.len()                        # 1
db.events.get(0)                       # the event at sequence 0
for e in db.events.range(start=0):     # ordered replay
    ...
db.events.verify_chain()               # integrity check
```

## Graph — `db.graphs`

```python
db.graphs.create("social")
db.graphs.add_node("social", "ada")
db.graphs.add_node("social", "grace")
db.graphs.add_edge("social", "ada", "follows", "grace")
for n in db.graphs.neighbors("social", "ada"):
    n.dst                              # 'grace'
```

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

Every write returns a receipt whose commit timestamp you can read `as_of`:

```python
receipt = db.kv.put("k", "v1")
db.kv.put("k", "v2")
db.kv.get("k", as_of=receipt.commit.timestamp)   # b'v1' — as_of on every read

db.branches.create("feature")
db.branches.list()
feature = db.at(branch="feature")      # a scoped view; writes target the branch
feature.kv.put("k", "on-feature")
```

`db.spaces` manages product spaces (isolated namespaces); `db.at(space=...)`
scopes a view.

## Errors

Every domain failure raises a `stratadb.errors.StrataError` subclass. Match on
the stable `.code` (`<class>.<area>.<detail>`), never on message text:

```python
from stratadb import errors
try:
    db.branches.get("nope")
except errors.NotFoundError as e:
    e.code           # e.g. "not_found.engine.branch"
    e.hint, e.ref    # actionable hint + a docs URL
```

## Escape hatch & introspection

```python
db.execute({"type": "kv_scan", "limit": 10})   # raw command wire -> {"type","data"}
stratadb.command_index()               # full offline command catalog (ids, kinds, docs)
stratadb.agents_guide()                # this guide
stratadb.__version__                   # == engine version
```

`db.execute(...)` is the permanent, lossless escape hatch to the full command
surface (the same wire the CLI and MCP server speak); the typed namespaces above
build on it.
