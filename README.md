# stratadb — Strata for Python

The Python SDK for [Strata](https://stratadb.org): an **embedded** multi-model
database for AI agents. SQLite-shaped, not a server — it links the engine in
process and opens a file-backed (or in-memory) database directly.

Five primitives — key-value, JSON documents, vectors, an event log, and a graph
— share one branch-aware, time-travelling storage substrate. The SDK speaks the
exact same command surface, value shapes, and error codes as the `strata` CLI
and MCP server, so learning one channel is learning all of them.

## For coding agents — start here

Install with `uv add stratadb` (or `pip install stratadb`), then call
**`stratadb.agents_guide()`** first.
It returns the complete offline Python usage guide (every namespace, `db.ai`,
provider keys, branches / time-travel, errors — all runnable Python), so you can
learn the whole surface without probing it:

```python
import stratadb
db = stratadb.open(cache=True)      # ephemeral; or open("./app-data") for durable
print(stratadb.agents_guide())      # the entire surface, offline — read this first
```

- `python -m stratadb.demo` — a runnable, zero-setup tour that prints every
  primitive's real return shape (doubles as a smoke test).
- `stratadb.init("path/to/repo")` — scaffold the `strata-python` agent skill and
  an `AGENTS.md` stanza into a repo so the next agent starts warm.
- `npx skills add stratalab/strata-agent-skills` — install the full Strata
  skill set (usage, branching, time travel) for Claude Code, Cursor, Codex,
  and friends. The same repo
  ([strata-agent-skills](https://github.com/stratalab/strata-agent-skills))
  carries the one-command workspace setup (CLI + MCP registration + skills);
  its npm publish is pending, so use the skills command today.

### Names & surfaces

Strata appears under a few names; here is what each string is and where it's used:

| Surface | Value | Notes |
| --- | --- | --- |
| PyPI package | `stratadb` | `pip install stratadb` |
| Python import | `import stratadb` | the SDK this README documents |
| CLI | `strata` | a separate binary (strata-core); **not** installed by this wheel |
| MCP server | `strata <db> mcp serve` | snippet via `stratadb.mcp_config(path)` |
| Agent skills | `npx skills add stratalab/strata-agent-skills` | one-command setup lives in the same repo (npm publish pending) |
| GitHub repo | `stratalab/strata-python` | this SDK |
| GitHub org | `stratalab` | |
| Website / docs | `stratadb.org` | |

## Install

```bash
uv add stratadb        # or: pip install stratadb
```

No Rust toolchain required — wheels are prebuilt (`abi3`, one per platform,
Python 3.9+).

## Quickstart

```python
import stratadb

db = stratadb.open("./app-data")      # durable (creates if absent)
# db = stratadb.open(cache=True)      # ephemeral, in-memory

# Key-value — values are str | bytes (reads return bytes; misses return None)
db.kv.put("greeting", "hello")
db.kv.get("greeting")                    # b"hello"

# Structured data belongs in the JSON primitive (or json.dumps it into kv)
db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
db.json.get("user:1", "$.name")          # "Ada"

# Listing methods return a Page: iterate (auto-paginates) or collect with .all()
db.json.keys(prefix="user:").all()       # ["user:1"]

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
db.graphs.add_node("social", "grace")
db.graphs.add_edge("social", "ada", "follows", "grace")

db.close()   # or: with stratadb.open("./app-data") as db: ...
```

`stratadb.open()` never opens the current directory implicitly: pass a path, set
`STRATA_DB` (`stratadb.from_env()`), or use `cache=True`.

### Upgrading from pre-V1 (0.x)

V1 namespaced the flat 0.x methods. If an example uses `Strata.open` or
`db.kv_put`, it predates V1 — the current equivalents:

| pre-V1 (0.x) | V1 (this SDK) |
|---|---|
| `Strata.open("/path")` | `stratadb.open("/path")` |
| `db.kv_put` / `kv_get` / `kv_delete` / `kv_list` | `db.kv.put` / `.get` / `.delete` / `.keys()` |
| `db.json_set` / `json_get` / `json_delete` | `db.json.set` / `.get` / `.delete` |
| `db.event_append` / `event_get` / `event_list` | `db.events.append` / `.get` / `.list` |
| `db.vector_create_collection` / `vector_upsert` / `vector_search` | `db.vectors.create_collection` / `.upsert` / `.query` |
| `db.state_set` / `state_get` / `state_cas` | removed — use `db.kv` or `db.json` (raises `unsupported.sdk.state_removed`) |
| `db.transaction()` / `begin()` / `commit()` | removed — writes commit individually; use `*_many` batches for multi-write commits |

## Inference — `db.ai`

Chat, embeddings, and reranking over cloud providers (OpenAI, Anthropic, Google)
or local GGUF models — an OpenAI-shaped surface. Strata is embedded and ships no
keys: set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`, or
`strata config set openai.api_key sk-...`.

```python
r = db.ai.chat("Explain embeddings in one sentence.",
               model="openai:gpt-4o-mini", max_tokens=60)
print(r.content)

# Structured output (JSON Schema)
r = db.ai.chat("Capital of France and its population?",
               model="anthropic:claude-haiku-4-5-20251001",
               json_schema={"type": "object",
                            "properties": {"capital": {"type": "string"},
                                           "population": {"type": "integer"}},
                            "required": ["capital", "population"]})

# Tool / function calling
r = db.ai.chat("What's the weather in Paris?", model="google:gemini-2.5-flash",
               tools=[{"type": "function",
                       "function": {"name": "get_weather",
                                    "parameters": {"type": "object",
                                                   "properties": {"city": {"type": "string"}},
                                                   "required": ["city"]}}}],
               tool_choice="required")
r.tool_calls          # [{'id': ..., 'function': {'name': 'get_weather', 'arguments': '{"city":"Paris"}'}}]

# Embeddings
e = db.ai.embed(["hello", "world"], model="openai:text-embedding-3-small")
e.vectors             # [[...], [...]]

# A model handle sets load params once
qwen = db.ai.model("local:qwen3", n_ctx=8192)
qwen.chat("Summarize: ...")

db.ai.capability("openai:gpt-4o-mini")   # supported features; no network call
```

## Branches, spaces, and time travel

```python
db.branches.fork("default", "experiment")   # copy-on-write branch
exp = db.at(branch="experiment")          # a scoped view over the same handle
exp.kv.put("k", "only-on-experiment")

db.branches.diff("default", "experiment")      # what differs, per space and primitive (A → B)
db.branches.preview("experiment", "default")   # the conflicts a merge would hit; mutates nothing
db.branches.merge("experiment", "default")     # promote as one atomic commit — strict by default;
                                               # strategy="source_wins" lets the source win conflicts

receipt = db.kv.put("k", "v1")
db.kv.put("k", "v2")
db.kv.get("k", as_of=receipt.commit.timestamp)   # b"v1" — every read takes as_of
```

`merge` carries the key-value, JSON, and vector changes a fork made since its
fork point; event streams and graphs are compared but never merged. A `strict`
merge that hits a conflict raises `errors.ConflictError`
(`conflict.engine.promotion`) and writes nothing — `preview` first.

## StrataHub — browse and clone datasets

```python
page = db.hub.list_datasets(tasks="classification", sort="downloads", limit=5)  # default hub: hub.stratahub.io
[d.name for d in page.items]                    # ['titanic', 'iris']; page.total counts every match
card = db.hub.get_dataset("titanic")            # the full card: .readme, .license, .primitives, .clone_command
db.hub.list_refs("titanic").refs                # cloneable branches, each with its manifest hash

titanic = stratadb.clone("titanic", "./titanic",           # a new durable database, cloned from the hub
                         progress=lambda e: print(e.stage.value, e.index, e.object_count))
titanic.json.get("passenger:1")["name"]         # "Braund, Mr. Owen Harris"
titanic.close()
```

`db.hub` only reads the hub — it never touches the handle's own data, so any
handle (even `stratadb.open(cache=True)`) can browse. Pass `hub_url=` or set
`STRATA_HUB_URL` to target another hub; `db.hub.info()` reports its limits, and
`db.hub.list_yanked()` its takedown list.

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

- `stratadb.agents_guide()` — the complete offline **Python** usage guide bundled
  in the wheel (the SDK-native counterpart to `strata agents guide`).
- `python -m stratadb.demo` / `stratadb.demo()` — a runnable, zero-setup tour of
  every primitive with real printed output.
- `stratadb.init(repo_path=".")` — scaffold `.claude/skills/strata-python/SKILL.md` and
  an `AGENTS.md` stanza into a repo (idempotent).
- `stratadb.agents_skill()` — the `strata-python` skill markdown, vendored verbatim from
  [strata-agent-skills](https://github.com/stratalab/strata-agent-skills)
  (`tools/vendor_skill.py` pins the rev in `STRATA_AGENT_SKILLS_REV`).
- `stratadb.command_index()` — the full command catalog bundled in the wheel.
- `stratadb.mcp_config(path)` — the MCP client-config snippet (`strata <path> mcp
  serve`; needs the `strata` binary, a separate strata-core install).
- `db.execute(command: dict) -> dict` — the raw command escape hatch (the same
  wire the CLI and MCP speak); the typed namespaces build on it.

## Architecture

Three layers: handwritten ergonomic **namespaces** over a **generated core**
(one typed method + model per command, generated from the engine's IDL) over a
tiny **PyO3 binding** that links the engine in process. Generated fresh from
the IDL (only `db.ai`'s inference family is hand-written), drift-guarded in CI.

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
