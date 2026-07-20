"""Implementation of the Strata tour (``stratadb.demo()`` / ``python -m stratadb.demo``).

Opens an ephemeral in-memory database and exercises every primitive (key-value,
JSON, vectors, events, graph) plus branches and time-travel, printing each call's
real result and return shape. Needs no API key and no config, so it doubles as a
smoke test and as a copy-paste source of working snippets.

The one primitive it skips is ``db.ai`` (chat / embeddings), which needs a cloud
provider key — see ``stratadb.agents_guide()`` for that surface.

The runnable ``python -m stratadb.demo`` entry point is the thin :mod:`stratadb.demo`
shim; this private module holds the logic so ``stratadb.demo`` stays a callable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Strata


def demo() -> None:
    """Run the end-to-end tour against a fresh in-memory database."""
    import stratadb

    print(f"stratadb {stratadb.__version__} — end-to-end tour (in-memory, zero setup)\n")
    with stratadb.open(cache=True) as db:
        _kv(db)
        _json(db)
        _vectors(db)
        _events(db)
        _graph(db)
        _branches_and_time_travel(db)

    print("Done — every call ran against an ephemeral database; nothing persisted.")
    print("Next: stratadb.agents_guide() for the full guide; set OPENAI_API_KEY for db.ai.")


def _section(title: str) -> None:
    print(f"\n── {title} " + "─" * max(2, 60 - len(title)))


def _kv(db: "Strata") -> None:
    _section("Key-value — db.kv")
    receipt = db.kv.put("greeting", "hello")
    print("put('greeting', 'hello') ->", f"Record(effect.kind={receipt.effect.kind})")
    print("get('greeting')          ->", db.kv.get("greeting"))
    print("get('absent')            ->", db.kv.get("absent"), "(misses return None)")
    print("count()                  ->", db.kv.count())


def _json(db: "Strata") -> None:
    _section("JSON documents — db.json")
    db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
    print("get('user:1')            ->", db.json.get("user:1"))
    print("get('user:1', '$.name')  ->", db.json.get("user:1", "$.name"))
    print("exists('user:1')         ->", db.json.exists("user:1"))
    print("history('user:1')        ->", [h.value for h in db.json.history("user:1")])


def _vectors(db: "Strata") -> None:
    _section("Vectors — db.vectors (literal vectors, no API key)")
    db.vectors.create_collection("notes", dimension=3, metric="cosine")
    db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3], metadata={"kind": "note"})
    db.vectors.upsert("notes", "n2", [0.9, 0.1, 0.0], metadata={"kind": "task"})
    print("query([0.1, 0.2, 0.3], k=2) -> list[VectorMatch]:")
    for hit in db.vectors.query("notes", [0.1, 0.2, 0.3], k=2):
        print(f"    key={hit.key!r} score={hit.score:.4f} metadata={hit.metadata}")


def _events(db: "Strata") -> None:
    _section("Events — db.events (append-only, hash-chained)")
    db.events.append("signup", {"user": "ada"})
    db.events.append("login", {"user": "ada"})
    print("len()                    ->", db.events.len())
    event = db.events.get(0)
    print("get(0)                   ->", f"{event.event.event_type} {event.event.payload}")
    print("verify_chain().valid     ->", db.events.verify_chain().valid)


def _graph(db: "Strata") -> None:
    _section("Graph — db.graphs")
    db.graphs.create("social")
    for node in ("ada", "grace", "linus"):
        db.graphs.add_node("social", node)
    db.graphs.add_edge("social", "ada", "follows", "grace")
    db.graphs.add_edge("social", "ada", "follows", "linus")
    print("list()                   ->", db.graphs.list())
    print("meta('social').node_count ->", db.graphs.meta("social").node_count)
    neighbors = [hit.node_id for hit in db.graphs.neighbors("social", "ada")]
    print("neighbors('ada')         ->", neighbors, "(use .node_id, not .dst)")


def _branches_and_time_travel(db: "Strata") -> None:
    _section("Branches & time travel")
    receipt = db.kv.put("counter", "1")
    db.kv.put("counter", "2")
    print("get('counter')                 ->", db.kv.get("counter"))
    print("get('counter', as_of=<v1 time>)->", db.kv.get("counter", as_of=receipt.commit.timestamp))
    db.branches.fork("default", "experiment")  # copy-on-write from default
    experiment = db.at(branch="experiment")     # a scoped view; writes target the branch
    print("counter on experiment (forked) ->", experiment.kv.get("counter"), "(inherited from default)")
    experiment.kv.put("counter", "on-branch")
    print("branches.list()                ->", [b.name for b in db.branches.list()])
    print("counter on default             ->", db.kv.get("counter"))
    print("counter on experiment          ->", experiment.kv.get("counter"))
