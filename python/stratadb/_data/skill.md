---
name: strata-python
description: >-
  Use Strata from Python with the stratadb SDK — the embedded, branch-native
  database for AI agents: KV, JSON documents, vectors, event logs, and graphs
  in one local directory, with branching and time travel. Use when a project
  imports stratadb or lists it in pyproject/requirements, when the user
  mentions stratadb, stratadb.open, db.kv/db.json/db.vectors/db.events/
  db.graphs, or wants to store agent state, memory, embeddings, events, or
  graphs from Python without a server. Covers opening databases (durable,
  in-memory, durability and IPC modes, memory budget), every db.<namespace>,
  return shapes (None on miss, receipts, Page), branches via db.at() and
  db.branches (fork, diff, preview, merge), time travel on both clocks
  (as_of, as_of_time, committed_at), StrataHub browse and clone, typed errors
  matched on .code, db.ai inference, and the sharp edges that trip agents.
license: MIT
metadata:
  strata-core-rev: "6fc481c33473efd7d1724284107b67be08625dcd"
  cli-version-range: "1.x"
  stratadb-version-range: "1.x"
---

# Strata from Python (`stratadb`)

`stratadb` links the Strata engine into your process: `stratadb.open("./app-data")`
opens a directory — no server, no port, no API key. It speaks the exact same
commands, value shapes, and error codes as the `strata` CLI and the `strata_*`
MCP tools, so the `strata`, `strata-branching`, and `strata-time-travel` skills
apply unchanged; this skill is their Python face. If you reach Strata through
MCP tools rather than code, use the `strata` skill instead.

**Version-matched truth is one call away:** `stratadb.agents_guide()` returns
the complete offline guide for the installed wheel — every namespace, runnable
snippets, error codes. Call it first when unsure; this skill teaches the shapes
and the traps.

## Install & open

```bash
uv add stratadb          # or: pip install stratadb   (prebuilt wheels, Python 3.9+)
```

```python
import stratadb

db = stratadb.open("./app-data")            # durable directory, created if absent
db.close()
with stratadb.open(cache=True) as db:       # in-memory; nothing persists
    ...
db = stratadb.from_env()                    # path from $STRATA_DB
```

Open options apply to durable databases only (`cache=True` rejects them):

| Option | Values | What it does |
|---|---|---|
| `durability=` | `"standard"` (default), `"always"` | `"standard"` syncs at the next sync point — an unclean process death can lose the acknowledged tail. `"always"` syncs every commit before acknowledgement. Receipts report what held: `receipt.commit.durability`. |
| `ipc=` | `"host"` (default), `"client"`, `"off"` | unix only. `"host"`: own the store, or broker to the existing owner over a socket — so several handles or processes share one database. `"client"`: broker, never host. `"off"`: raw exclusive open (a second open raises `UnavailableError`). |
| `memory_budget=` | bytes, ≥ 1 MiB | Storage memory budget for the handle that *owns* the store on this open. Omitted: derived from host memory (25% of usable, capped at 8 GiB). Read back with `db.admin.info().memory_budget`. |

`stratadb.open()` with neither a path nor `cache=True` raises
`InvalidArgumentError` (`invalid_argument.cli.no_database`) — Strata never
opens the current directory implicitly.

## The handle

One namespace per primitive, plus the control plane and the escape hatch:

| Namespace | For | Key calls |
|---|---|---|
| `db.kv` | opaque values by key (`str`/`bytes` in, `bytes` out) | `put`, `get`, `exists`, `delete`, `put_many`, `get_many`, `keys(prefix=)`, `history` |
| `db.json` | structured documents, addressed by path | `set(key, "$", doc)`, `get(key, "$.field")`, `set_many`, `keys(prefix=)`, `scan`, `history` |
| `db.vectors` | embeddings + metadata, similarity search | `create_collection(name, dimension=, metric=, embedding_model=)`, `upsert(coll, key, vec \| text=)`, `query(coll, vec \| text=, k=, filter=)`, `set_embedding_model`, `keys`, `history` |
| `db.events` | append-only, hash-chained log | `append(type, payload)`, `get(seq)`, `range(start=)`, `range_by_time`, `len()`, `verify_chain()` |
| `db.graphs` | typed nodes and edges, traversal, analytics | `create`, `add_node`, `add_edge`, `neighbors`, `list_nodes`, graph analytics (PageRank, BFS, …) |
| `db.branches`, `db.spaces`, `db.at(...)` | isolation and scoping | `fork`, `create`, `list`, `fork_at_version`, `fork_at_timestamp`; `db.at(branch=, space=)` |
| `db.admin`, `db.arrow` | control plane; bulk Arrow/Parquet | `ping`, `info`, `health`, `ipc_status`; `export`, `import_` |
| `db.hub` | browse StrataHub (read-only; never touches your data) | `info`, `list_datasets(tasks=, tags=, sort=)`, `get_dataset`, `list_refs`, `list_yanked`; `stratadb.clone(name, dest)` downloads one |
| `db.ai` | inference, OpenAI-shaped | `chat`, `embed`, `rank`, `capability`, `status` |
| `db.execute({...})` | the raw wire — every cataloged command | `stratadb.command_index()` lists them |

```python
db.kv.put("greeting", "hello");  db.kv.get("greeting")                        # b'hello'
db.json.set("user:1", "$", {"name": "Ada"});  db.json.get("user:1", "$.name")  # 'Ada'
db.vectors.create_collection("notes", dimension=3, metric="cosine")
db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3], metadata={"kind": "note"})
db.vectors.query("notes", [0.1, 0.2, 0.3], k=5)                               # list[VectorMatch]
db.vectors.create_collection("docs", dimension=384, embedding_model="miniLM")  # stratadb >= 1.2.2
db.vectors.upsert("docs", "d1", text="a small domestic cat")                  # engine embeds it
db.vectors.query("docs", text="kitten", k=5)                                  # and on the way in
db.events.append("deploy", {"ok": True});  db.events.len()                    # 1
db.graphs.create("g"); db.graphs.add_node("g", "a"); db.graphs.add_node("g", "b")
db.graphs.add_edge("g", "a", "link", "b")                                     # both endpoints must exist
```

Choosing: config, flags, checkpoints → KV; records you update field by field →
JSON; things that happened → Events; similarity recall → Vectors; entities and
relationships → Graph. A good default for agent memory: JSON for the working
record, Events for the decision log, Vectors for semantic recall, KV for
checkpoints and flags.

## Return shapes that matter

- **A miss is `None`, never an exception.** `db.kv.get("absent") is None`;
  `db.json.get("absent")` too; `history()` of a never-written key is `None`.
- **Every write returns a receipt** (`Record`): `r.commit.version` and
  `r.commit.timestamp` (the same logical commit counter — not wall-clock),
  `r.commit.committed_at` (the real UTC instant, epoch µs, or `None` on a
  commit written before engine 1.2.1), `r.commit.durability`, and `r.effect`
  (`.applied`, `.kind`). Keep `r.commit.timestamp` whenever you may need to
  look back; format `committed_at` with `stratadb.to_datetime(...)`.
- **Listing methods return a `Page`** — `db.kv.keys()`, `db.json.keys()`,
  `db.events.range()`, `db.graphs.neighbors()`, `db.vectors.keys()`, … Iterating
  auto-paginates across every page; `.all()` collects; `page.has_more` /
  `page.cursor` paginate by hand. Never treat the first page as the whole result.
- **Batches return `BatchResult`** (`.status`, `.items[i].status`) — a batch can
  partially apply, so check per-item status.
- `db.vectors.query()` returns `list[VectorMatch]` (`.key`, `.score`,
  `.metadata`). `db.graphs.neighbors()` rows are `GraphNeighborHit` — use
  `.node_id` for the neighbour; `.dst` is the edge's dst, which on
  `direction="incoming"` is the node you queried.
- KV values come back as `bytes` even when written as `str`; structured data
  belongs in `db.json`.

## Branches and time travel

```python
db.branches.fork("default", "experiment")     # copy-on-write fork; create() makes an EMPTY branch
exp = db.at(branch="experiment")               # scoped view over the same handle
exp.kv.put("k", "risky")
db.kv.get("k")                                 # None on default — isolated

db.branches.diff("default", "experiment").spaces   # per space + capability: .added / .removed / .modified
p = db.branches.preview("experiment", "default")   # read-only three-way; p.conflicts, p.capabilities_unsupported
out = db.branches.merge("experiment", "default")   # strict (default): ConflictError on divergence, target untouched
out = db.branches.merge("experiment", "default", strategy="source_wins")  # out.applied / .deleted / .target_version

r = db.kv.put("k", "v1"); db.kv.put("k", "v2")
db.kv.get("k", as_of=r.commit.timestamp)            # b'v1' — the logical commit timeline
db.kv.get("k", as_of_time=r.commit.committed_at)    # b'v1' — real UTC time
stratadb.to_datetime(r.commit.committed_at)         # -> aware UTC datetime; .astimezone() for local
db.branches.fork_at_timestamp("default", "as-it-was", r.commit.timestamp)  # anchors take as_of only
```

The default branch is `default` (not `main`). Promotion (`stratadb >= 1.1.0`)
merges key-value, JSON, and vector data; events and graphs are compared but
never merged (they show up in `capabilities_unsupported`), and only branches
with shared fork lineage can be merged (`invalid_argument.engine.branch_point`
otherwise). `preview()` first when the outcome matters — `strict` refuses on
any conflict and changes nothing.

**Two clocks, and they are not interchangeable** (`stratadb >= 1.2.1`).
`timestamp` is a position on
the logical commit timeline (a counter starting near 1, never a date) and its
values are ones you were *given* — receipts, history rows — never computed.
`committed_at` is the real UTC instant, in epoch µs, and it is the one you may
compute: every read taking `as_of` also takes `as_of_time`, which accepts a
`datetime`, a `date`, an ISO 8601 string, or raw µs (naive values are read as
local time). Passing both raises `InvalidArgumentError`
(`invalid_argument.executor.as_of_conflict`); passing a `datetime` to `as_of`
raises `invalid_argument.sdk.as_of_kind`, which names the argument you wanted.
History rows carry `committed_at` too, and `stratadb.to_micros` /
`stratadb.to_datetime` convert in both directions (`None` passes through).

`as_of_time` **does not clamp**: an instant outside the branch's dated history
raises `HistoryUnavailableError`
(`history_unavailable.engine.persistence_history`) at *both* ends — so
`as_of_time=datetime.now()` is an error, not "latest". Read current state by
passing no clock at all. The dated window is only as wide as the database's own
history, and pre-1.2.1 commits report `committed_at is None`. Separately,
`event.timestamp` is the event's own **occurrence** time (µs) and the axis
`db.events.range_by_time()` walks — a third thing again, not a commit clock.
Patterns: the `strata-branching` and `strata-time-travel` skills.

## Errors: match `.code`, never the message

Every domain failure raises a `stratadb.errors.StrataError` subclass
(`NotFoundError`, `AlreadyExistsError`, `InvalidArgumentError`,
`FailedPreconditionError`, `ConflictError`, `UnavailableError`,
`HistoryUnavailableError`, `DataLossError`, …)
carrying `.code` (`<class>.<area>.<detail>`), `.hint`, `.ref`
(`https://stratadb.org/e/<code>`), `.retryable`, and `.retry_policy`. Invalid
Python-side input raises the same hierarchy (`invalid_argument.sdk.*`), so one
`except errors.StrataError` covers everything.

```python
from stratadb import errors

try:
    db.branches.fork("default", "experiment")
except errors.AlreadyExistsError:
    pass                                   # idempotent setup
except errors.StrataError as e:
    if not e.retryable:
        raise                              # change the request instead of repeating it
```

Codes you will actually meet:

| Code | Meaning |
|---|---|
| `invalid_argument.cli.no_database` | `open()` had no target — pass a path, set `STRATA_DB`, or use `cache=True` |
| `invalid_argument.sdk.command` | a malformed argument: bad `durability=`/`ipc=`/`memory_budget=`, a wrong type, an unserializable payload |
| `invalid_argument.sdk.entry` | a batch entry (e.g. `graphs.bulk_insert`) missing a required field |
| `failed_precondition.sdk.handle_closed` | any call after `db.close()` (`close()` itself is idempotent) |
| `failed_precondition.sdk.fork_not_supported` | the handle was used after `os.fork()` — open a fresh handle in the child |
| `not_found.engine.branch` | `db.at(branch=...)` names a branch that does not exist — check `db.branches.list()` |
| `already_exists.engine.branch` | the fork/create name is taken |
| `history_unavailable.engine.persistence_history` | `as_of`, `as_of_time`, history, or a fork anchor outside the retained/dated window — including `as_of_time=now` |
| `invalid_argument.executor.as_of_conflict` | both clocks in one call — pass `as_of` or `as_of_time`, not both |
| `invalid_argument.sdk.as_of_kind` | a `datetime` passed to `as_of` — that is `as_of_time`'s argument |
| `conflict.engine.promotion` | a `strict` `merge()` hit a conflict and changed nothing — `preview()`, resolve on the source, or `strategy="source_wins"`. `retry_policy` is `after_state_change`: retry only after resolving, never as a loop |
| `invalid_argument.engine.branch_point` | `preview()`/`merge()` between branches with no shared fork lineage (e.g. a `create()`d root) |
| `failed_precondition.engine.writer_lock` | `ipc="off"` open of a path another handle owns — close it, or open with the default `ipc="host"` and broker in (engine 1.2.3; it was `unavailable.engine.persistence`) |
| `failed_precondition.engine.branch_has_children` | `db.branches.delete()` on a branch another branch was forked from — delete the fork first (durable databases) |
| `unavailable.executor.ipc_transport` | the owner this handle brokered to has closed — reopen the database (see below) |
| `inference.missing_api_key` | a cloud `db.ai` call with no provider key (`FailedPreconditionError`) |
| `unsupported.sdk.state_removed` | `db.state` was removed in V1 — use `db.kv` or `db.json` |

## Sharp edges

- **Keep the owner alive.** With the `ipc="host"` default, the first open of a
  path owns the store and later opens broker to it. When the owner closes —
  `close()`, its last reference dropped, process exit — every brokered handle
  fails with `UnavailableError` (`unavailable.executor.ipc_transport`,
  retryable). A fresh `stratadb.open(path)` recovers as the new owner. Within
  one process, share one handle across threads (it is concurrency-safe) rather
  than reopening, and never rebind the only reference to the owner.
- **`memory_budget=` belongs to the owner.** A handle that brokers in inherits
  the owner's budget and its own value is ignored;
  `db.admin.info().memory_budget.source` says which rule applied.
- **Default durability is `"standard"`, not fsync-per-commit.** Acknowledged
  commits become durable at the next sync point; a SIGKILL before then loses
  them. Use `durability="always"` when every acknowledgement must survive.
- **Graph edges need both endpoints first.** `add_edge` to a missing node
  raises `invalid_argument.engine.graph_edge_endpoint`.
- **`text=` needs a declared model.** `db.vectors.upsert(...,  text=)` and
  `query(..., text=)` embed through the collection's `embedding_model`
  (`create_collection(embedding_model=)` or `set_embedding_model()`); without
  one it is `failed_precondition.engine.embedding_model_missing`, and a model
  whose dimension disagrees with the collection is
  `embedding_model_mismatch`. Pass a vector or `text=`, never both. The
  embedding is a real inference call, so it carries the `inference.*` failures
  — `db.ai.status()` tells you up front whether this build runs local models,
  which provider keys are present, and (engine 1.2.3) whether the config file
  those keys live in is `absent`, `readable`, `unreadable` or `malformed` —
  the difference between "no key was set" and "one was set in a file I cannot
  read", which used to look identical.
- **Cloud `db.ai` needs your key** (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` /
  `GOOGLE_API_KEY`, or `strata config set <provider>.api_key …`); Strata ships
  none, and there is no bundled offline embedder yet — for keyless vector
  search, upsert literal vectors.
- **`commit.timestamp` is a logical counter**, not microseconds; never compare
  it with wall-clock time. `commit.committed_at` is the microseconds — use that
  (via `stratadb.to_datetime`) whenever a human will read the answer, and
  remember it is `None` for commits written before engine 1.2.1.
- **`db.events.range()` windows are half-open `[start, end)`**, in both
  directions; `reverse=True` walks that same window newest-first, so
  `db.events.range(0, reverse=True, limit=5)` is "the newest 5".
  `range_by_time()` is half-open on the event's own occurrence time.

## Inference (`db.ai`)

```python
r = db.ai.chat("Summarize this.", model="openai:gpt-4o-mini", max_tokens=100);  r.content
e = db.ai.embed(["hello"], model="openai:text-embedding-3-small")
db.vectors.upsert("notes", "n1", e.vector)     # embed → upsert → query is the RAG loop
db.ai.capability("openai:gpt-4o-mini")         # offline: what a model supports
```

Model specs are `openai:MODEL` / `anthropic:MODEL` / `google:MODEL`; a bare
`MODEL` (or `local:MODEL`) is a local GGUF.

## Scaffolding and deeper reference

- `stratadb.init("path/to/repo")` writes this skill to
  `.claude/skills/strata-python/SKILL.md` plus an `AGENTS.md` stanza;
  `npx skills add stratalab/strata-agent-skills` installs the full set
  (`strata`, `strata-branching`, `strata-time-travel`, `strata-python`).
- `python -m stratadb.demo` — a runnable, zero-setup tour that prints every
  primitive's real return shape.
- `stratadb.agents_guide()` — the complete guide; `stratadb.command_index()` —
  the full catalog; `db.execute({"type": "kv_scan", "limit": 10})` — the raw
  wire, `{"type": ..., "data": ...}` envelopes in and out.
- CLI equivalents: `strata ./app-data kv get greeting`, `strata --json …`,
  `strata <db> mcp serve`. The `strata` binary is a separate strata-core
  install; `stratadb.mcp_config(path)` returns the MCP client snippet.
