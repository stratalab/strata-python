# Strata 1.0.0 — agent usage guide

Strata is an embedded multi-model database: one binary, one file-backed
database, no server. Six primitives share one storage substrate with
branches and time travel: key-value, JSON documents, vectors, an event log,
graphs, and product spaces. This guide is generated from the installed
binary's own metadata, so it cannot drift from what `strata 1.0.0` does.

## Targeting a database

1. Explicit path or `--db <path>` — always wins: `strata ./my-db kv get k`
2. `STRATA_DB=<path>` — set once per session, used when no path is passed
3. `--cache` — explicit in-memory database (nothing persisted)

One-shot commands with no target refuse with
`invalid_argument.cli.no_database` — Strata never opens the current
directory implicitly. `strata <path>` with no command opens a REPL.

## Quickstart

```
strata ./my-db kv put greeting hello
strata ./my-db kv get greeting
strata --cache
strata agents guide
```

Branches fork cheaply and isolate writes; every primitive is branch-aware:

```
strata ./my-db branch fork default experiment
strata ./my-db kv put city tokyo --branch experiment
strata ./my-db kv get city --branch experiment   # tokyo
strata ./my-db kv get city                       # unchanged on default
```

Time travel: every write receipt carries a commit `timestamp`; pass it back
with `--as-of` on reads (kv/json/vector/event/graph alike):

```
strata --json ./my-db kv put k v1        # note data.commit.timestamp
strata ./my-db kv put k v2
strata ./my-db kv get k --as-of <t1>     # v1
```

## Output contract

- `--json`: one compact envelope per command — `{"type": ..., "data": ...}`.
  KV keys/values and cursors are base64 strings on the wire.
- `--raw`: script-friendly bare values.
- default: human-readable; binary values decode to text when valid UTF-8.
- Continuation cursors are opaque base64 tokens: pass the printed cursor
  back verbatim via `--cursor`.
- Raw serialized commands (the programmatic path):
  `strata <db> command run --command-json '{"type":"kv_get","key":"a2V5"}'`

## Errors teach

Failures carry a stable code (`<class>.<area>.<detail>`), a one-line hint,
and a per-code ref (`https://stratadb.org/e/<code>`). `--json` failures emit
the full envelope on stderr. Recover by code and class, never by message
text. Full registry: `strata agents errors --json`.

## Diagnostics

`strata doctor [--json] [path]` checks the installation and (optionally) a
database, reporting coded issues with hints; it exits non-zero when
anything needs attention.

## MCP

`strata <db> mcp serve` speaks Model Context Protocol over stdio — ~20
curated tools plus `strata_guide` (this guide) and `strata_command` (any
cataloged command as raw wire JSON). Same envelopes, same error codes.
Client config: {"command":"strata","args":["<db-path>","mcp","serve"]}.

## Command catalog

125 commands carry full metadata today (catalog JSON: `strata agents commands --json`); every command documents itself via `--help`.

### admin

- `clone` — Clone a dataset from a hub into a new local database.
- `config get` — Read sanitized configuration facts.
- `config get-key` — Read one sanitized configuration value by key.
- `describe` — Read a compact description of the database.
- `health` — Read control-plane health facts.
- `info` — Read database identity and a catalog summary.
- `metrics` — Read lightweight database metrics.
- `ping` — Check that the database handle is live.
- `remote` — Read where this database was cloned from.

### arrow

- `arrow export` — Export a product primitive to an Arrow-compatible file.
- `arrow import` — Import an Arrow-compatible file into a product primitive.

### branch

- `branch create` — Create a new empty root branch.
- `branch delete` — Delete an active branch and release its storage claims.
- `branch fork` — Fork a new branch from the current head of a source branch.
- `branch fork-at-timestamp` — Fork a new branch from a retained source timestamp.
- `branch fork-at-version` — Fork a new branch from a retained source commit version.
- `branch get` — Read one branch summary by name.
- `branch list` — List active branches with their lineage facts.

### event

- `event append` — Append one event to the branch event log.
- `event batch-append` — Append multiple events in one commit.
- `event count` — Count visible events in the log.
- `event exists` — Check whether an event sequence exists.
- `event get` — Read one event by sequence number.
- `event list` — List events with optional type filter and cursor.
- `event range` — Read a range of events by sequence number.
- `event range-time` — Read a range of events by occurrence time.
- `event types` — List distinct event types in the log.
- `event verify-chain` — Verify event log density and hash linkage.

### graph

- `graph add-edge` — Add or replace a graph edge.
- `graph add-node` — Add or replace a graph node.
- `graph apply-delete-policy` — Apply a delete policy to bound graph facts.
- `graph batch-write` — Apply graph mutations atomically.
- `graph bfs` — Run a bounded breadth-first traversal.
- `graph bindings` — Find graph nodes bound to an entity.
- `graph bulk-insert` — Bulk-load nodes and edges in chunks.
- `graph cdlp` — Detect communities via label propagation.
- `graph create` — Create a named graph.
- `graph delete` — Delete a graph and its visible data.
- `graph get-edge` — Read one graph edge.
- `graph get-node` — Read one graph node.
- `graph lcc` — Compute local clustering coefficients.
- `graph list` — List graph names.
- `graph list-nodes` — List graph nodes.
- `graph meta` — Read graph metadata and counts.
- `graph neighbors` — List a node's neighbors.
- `graph nodes-by-type` — List nodes declaring an object type.
- `graph ontology define-link-type` — Define a graph link type.
- `graph ontology define-object-type` — Define a graph object type.
- `graph ontology delete-link-type` — Delete a draft link type.
- `graph ontology delete-object-type` — Delete a draft object type.
- `graph ontology freeze` — Freeze the graph ontology.
- `graph ontology get` — Read the graph ontology.
- `graph ontology summary` — Read the ontology with usage counts.
- `graph pagerank` — Compute PageRank importance scores.
- `graph remove-edge` — Remove a graph edge.
- `graph remove-node` — Remove a graph node and its edges.
- `graph sample` — Sample graph nodes.
- `graph sssp` — Compute shortest-path distances from a source.
- `graph wcc` — Compute weakly connected components.

### inference

- `inference cache-status` — Report loaded model cache state.
- `inference capability` — Report capabilities for a model spec.
- `inference detokenize` — Detokenize token ids with a local model.
- `inference embed` — Embed one or more texts into vectors.
- `inference generate` — Generate text with an inference model.
- `inference models list` — List catalog inference models.
- `inference models local` — List locally downloaded inference models.
- `inference models pull` — Download an inference model locally.
- `inference rank` — Rank passages against a query.
- `inference tokenize` — Tokenize text with a local model.
- `inference unload` — Unload cached inference models.

### json

- `json batch-delete` — Delete multiple JSON documents or paths in one itemwise batch.
- `json batch-exists` — Check existence for multiple JSON documents.
- `json batch-get` — Read multiple JSON values by document and path.
- `json batch-set` — Set multiple JSON values in one itemwise batch.
- `json count` — Count visible JSON documents.
- `json delete` — Delete a whole JSON document or one path inside it.
- `json exists` — Check whether one JSON document exists.
- `json get` — Read the current or historical JSON value at a document path.
- `json history` — Read retained version history for one JSON document.
- `json index create` — Create a JSON secondary index on a field path.
- `json index drop` — Drop a JSON secondary index by name.
- `json index list` — List JSON secondary indexes.
- `json list` — List JSON document keys with optional prefix filtering.
- `json sample` — Sample visible JSON documents.
- `json scan` — Scan JSON documents with values and version facts.
- `json set` — Set a JSON value at a document path, creating the document when missing.

### kv

- `kv batch-delete` — Delete multiple KV keys in one itemwise batch.
- `kv batch-exists` — Check existence for multiple KV keys.
- `kv batch-get` — Read multiple KV values by key.
- `kv batch-put` — Store multiple KV values in one itemwise batch.
- `kv count` — Count visible KV keys.
- `kv delete` — Delete one visible KV key.
- `kv exists` — Check whether one KV key exists.
- `kv get` — Read the current or historical value for one KV key.
- `kv history` — Read retained version history for one KV key.
- `kv list` — List KV keys with optional prefix filtering.
- `kv put` — Store or replace a KV value by key.
- `kv sample` — Sample visible KV rows.
- `kv scan` — Scan KV rows with values and version facts.

### space

- `space create` — Create a product space on a branch.
- `space delete` — Delete a product space from a branch.
- `space exists` — Check whether a product space exists on a branch.
- `space list` — List product spaces on a branch.

### vector

- `vector batch-delete` — Delete multiple vectors by key.
- `vector batch-exists` — Check existence for multiple vector keys.
- `vector batch-get` — Read multiple vectors by key.
- `vector batch-upsert` — Upsert multiple vectors in one itemwise batch.
- `vector collection create` — Create a vector collection with a dimension and metric.
- `vector collection delete` — Delete a vector collection.
- `vector collection list` — List vector collections.
- `vector collection stats` — Read facts for one vector collection.
- `vector count` — Count visible vectors in a collection.
- `vector delete` — Delete one vector key.
- `vector delete-all` — Delete all vectors in a collection.
- `vector delete-by-filter` — Delete vectors matching a metadata filter.
- `vector exists` — Check whether one vector key exists.
- `vector get` — Read one vector by key.
- `vector history` — Read retained vector history for one key.
- `vector index query` — Search vectors and return index diagnostics.
- `vector keys` — List vector keys in a collection.
- `vector query` — Search a vector collection.
- `vector sample` — Sample vectors with values and version facts.
- `vector scan` — Scan vectors with values and version facts.
- `vector update-metadata` — Patch metadata for one vector.
- `vector upsert` — Insert or replace one vector.

## Repo onboarding

`strata agents init` writes `.strata/AGENTS.md` into the current repo; `--apply` also appends a short pointer block to the repo's `AGENTS.md`/`CLAUDE.md` so every future agent session here starts oriented.

