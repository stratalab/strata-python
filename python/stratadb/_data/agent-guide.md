# stratadb — Python SDK agent guide

Strata is an **embedded** multi-model database (like SQLite/DuckDB — in-process,
no server). One database exposes five primitives over one branch-aware,
time-travelling store: **key-value, JSON documents, vectors, an event log,
graphs** — plus **inference** (`db.ai`) on the same handle. This guide is the offline, Python-native
usage reference for the installed version; it is returned by
`stratadb.agents_guide()`.

Conventions in this guide: every snippet is real, runnable Python. Reads return
`None` on a miss (never raise); domain failures raise a typed
`stratadb.errors.StrataError` you match on `.code`, never on message text.

## Install & open

```python
import stratadb

db = stratadb.open("./app-data")     # durable (created if absent)
db.close()                            # close what you open (or use the context manager)
db = stratadb.open(cache=True)       # ephemeral, in-memory (nothing persists)
db.close()
db = stratadb.from_env()              # path from $STRATA_DB
db.close()
with stratadb.open(cache=True) as db:
    ...                                # context manager closes it

# Commit durability: "standard" (default) syncs at the next sync point — an
# unclean process death can lose the acknowledged tail; "always" syncs every
# commit before acknowledgement.
db = stratadb.open("./app-data", durability="always")
db.kv.put("k", "v").commit.durability   # "always" — what storage attested at ack
db.close()

# Storage memory budget (bytes, >= 1 MiB). Omitted: derived at open from host
# memory (25% of usable, capped at 8 GiB). Per open, not persisted — and it
# belongs to the handle that owns the store (see gotchas), so open it fresh.
db = stratadb.open("./app-data", memory_budget=256 * 1024 * 1024)
db.admin.info().memory_budget.source    # "explicit" (else "derived_from_host")
db.admin.info().memory_budget.total_bytes
db.close()
```

`stratadb.open()` never opens the current directory implicitly — pass a path, set
`STRATA_DB`, or use `cache=True`, or it raises `InvalidArgumentError`.

A durable database has **one owner process at a time**, but you are not limited
to one handle. On unix, `open()` defaults to `ipc="host"`: the first opener owns
the store and hosts a Unix-domain socket, and later opens — another handle in
the same process, or a whole separate process — transparently broker to that
owner over the socket. So a notebook, a web app's workers, and a one-off script
can all `stratadb.open("./app-data")` the same path and share one database; the
owner serializes every writer. `db.admin.ipc_status()` reports the topology
(`is_owner`, `hosting`, `owner_pid`). Within one process, still prefer sharing a
single handle across threads (it is concurrency-safe). Pass `ipc="off"` for a
raw exclusive open (a second open then raises `UnavailableError`); `ipc="client"`
brokers to an existing owner but never hosts. IPC is unix-only. The owner's
lifetime bounds its clients: when the owner handle closes, brokered handles
raise `UnavailableError` until they reopen (see gotchas).

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
db.kv.keys(prefix="user:").all()       # listing methods return a Page: iterate (auto-paginates) or .all()
for key in db.kv.iter_keys(prefix="user:"):   # plain iterator over keys
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

# Bring it back: compare -> preview -> promote. Events and graphs are compare-only.
db.branches.diff("default", "feature").spaces        # per space + primitive: .added / .removed / .modified (A -> B)
db.branches.preview("feature", "default").conflicts  # [] here — default has not changed k since the fork
outcome = db.branches.merge("feature", "default")    # strict (default): one atomic commit; the source is untouched
outcome.applied, outcome.target_version              # what landed, and the target's new commit version
db.kv.get("k")                                       # b'on-feature'
```

Prefer `fork` when the new branch should start from existing data;
`db.branches.create(name)` makes an **empty** branch. Fork a point in history
with `db.branches.fork_at_version(source, name, receipt.commit.version)` or
`db.branches.fork_at_timestamp(source, name, receipt.commit.timestamp)`.
(`event.timestamp` is the one wall-clock value, in microseconds;
`db.events.range_by_time(...)` is the only API that takes wall-clock µs.)

`merge(source, target)` promotes the key-value, JSON, and vector changes the
source made since its fork point, as one commit, leaving the source unchanged;
event streams and graphs are **compared but never merged** (they are listed in
the outcome's `capabilities_unsupported`). `strategy="strict"` (the default)
raises `ConflictError` (`conflict.engine.promotion`) when both branches changed
the same entity differently and writes nothing; `strategy="source_wins"`
applies the source's value or tombstone per conflict and reports each
overwritten/deleted target entry in `.applied`/`.deleted`. Only branches that
share fork lineage can be merged — an empty `create()`d branch raises
`InvalidArgumentError` (`invalid_argument.engine.branch_point`). `preview` runs
the same three-way comparison read-only, so check its `.conflicts` first when
the outcome matters.

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
- **Durable opens share, they don't collide (unix).** By default (`ipc="host"`)
  a second `stratadb.open(path)` — another handle or another process — brokers to
  the first as the owner rather than raising; `db.admin.ipc_status()` shows who
  owns it. Opt out with `ipc="off"` for an exclusive open, where a second open
  raises `UnavailableError` (`unavailable.engine.persistence`) until the owner
  closes. On non-unix platforms IPC is unavailable and durable opens are always
  exclusive (`ipc="host"/"client"` raise `InvalidArgumentError`).
- **Default durability is `"standard"`, not fsync-per-commit.** A commit
  acknowledged with `receipt.commit.durability == "standard"` becomes durable at
  the *next sync point* (close, buffer threshold, rotation) — a crash/SIGKILL
  before then loses the acknowledged tail. Open with
  `stratadb.open(path, durability="always")` when every acknowledgement must
  survive process death; then receipts report `"always"`.
- **Keep the owner alive.** When the owner handle closes — `close()`, its last
  reference dropped, process exit — every handle that brokered to it raises
  `UnavailableError` (`unavailable.executor.ipc_transport`, retryable; the hint
  says to reopen). A fresh `stratadb.open(path)` recovers as the new owner. Share
  one handle across threads rather than reopening, and never rebind the only
  reference to the owner while clients depend on it.
- **`memory_budget=` belongs to the owner.** It sizes storage for the handle
  that owns the store on this open; a handle that brokers to an existing owner
  (the `ipc="host"` default on a busy path) inherits the owner's budget and its
  own `memory_budget=` is ignored — check `db.admin.info().memory_budget`.
  Budgets below 1 MiB raise `InvalidArgumentError`
  (`invalid_argument.engine.persistence`); `cache=True` takes no budget.
- **A strict merge that conflicts changes nothing.** `db.branches.merge()`
  raises `ConflictError` (`conflict.engine.promotion`, not retryable) if any
  entity diverged on both branches since the fork point, and applies *none* of
  the changes — not even the clean ones. Resolve on the source and retry, or
  pass `strategy="source_wins"` deliberately. Events and graphs never merge
  (compare-only), and a branch made with `create()` has no fork lineage to
  merge along (`invalid_argument.engine.branch_point`).
- **A closed handle raises typed errors.** Any call after `db.close()` raises
  `FailedPreconditionError` (`failed_precondition.sdk.handle_closed`); `close()`
  itself is idempotent.
- **`db.state` was removed in V1.** Accessing it raises `UnsupportedError`
  (`unsupported.sdk.state_removed`) — use `db.kv` for keyed values or `db.json` for
  structured documents.

## Admin & Arrow — `db.admin`, `db.arrow`

`db.admin` reads control-plane facts (never writes): `db.admin.ping()`
(liveness), `db.admin.info()` (identity + catalog summary), plus
`db.admin.health()`, `db.admin.metrics()`, `db.admin.describe()`, and
`db.admin.config()`. `db.admin.ipc_status()` reports the multi-process topology
— `.is_owner`, `.hosting`, `.owner_pid`, `.socket_path`, `.client_count` (see
Install & open for `ipc=`); `db.admin.ipc_stop()` stops hosting the broker
socket (`.stopped`) while the store stays usable in-process.

`db.arrow` bulk-moves a primitive to and from an Arrow/Parquet file. `target`
is one of `kv`, `json`, `vector`, `graph`, or `event` — vector imports take
`collection=`, graph imports take `graph=`, and event imports re-derive the log
(sequence/timestamp/hash are reassigned):

```python
db.arrow.export("kv", "backup.parquet")                  # a primitive -> Arrow file
db.arrow.import_("kv", "backup.parquet")                 # Arrow file -> primitive (note the trailing _)
db.arrow.export("graph", "g.parquet", graph="social")    # graph and event targets too
db.arrow.import_("graph", "g.parquet", graph="social")
```

## Escape hatch & introspection

```python
db.execute({"type": "kv_scan", "limit": 10})   # raw command wire -> {"type","data"}
stratadb.command_index()               # full offline command catalog (ids, kinds, docs)
stratadb.agents_guide()                # this guide
stratadb.demo()                        # a runnable, zero-setup tour (or: python -m stratadb.demo)
stratadb.init("path/to/repo")          # scaffold the strata-python skill + AGENTS.md into a repo
stratadb.__version__                   # the SDK version (engine version: db.admin.ping().version)
```

`db.execute(...)` is the permanent, lossless escape hatch to the full command
surface (the same wire the CLI and MCP server speak); the typed namespaces above
build on it.
