"""Behavior tests for db.arrow — the typed import/export wrapper.

Covers the graph and event import targets exposed on top of kv/json/vector
(strata-core #2691). Assertions are on restored state, never message text.
Every test runs on an in-memory database and a tmp Parquet file.
"""

from __future__ import annotations

import pytest

import stratadb


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


def test_kv_roundtrip(db, tmp_path):
    path = str(tmp_path / "kv.parquet")
    db.kv.put("greeting", "hello")
    db.arrow.export("kv", path)
    db.kv.delete("greeting")
    db.arrow.import_("kv", path)
    assert db.kv.get("greeting") == b"hello"


def test_graph_roundtrip_uses_graph_param(db, tmp_path):
    path = str(tmp_path / "social.parquet")
    db.graphs.create("social")
    for node in ("ada", "grace", "linus"):
        db.graphs.add_node("social", node)
    db.graphs.add_edge("social", "ada", "follows", "grace")
    db.graphs.add_edge("social", "ada", "follows", "linus")

    db.arrow.export("graph", path, graph="social")
    db.graphs.create("restored")
    db.arrow.import_("graph", path, graph="restored")

    meta = db.graphs.meta("restored")
    assert meta.node_count == 3
    assert meta.edge_count == 2


def test_event_roundtrip_rederives_log(db, tmp_path):
    path = str(tmp_path / "events.parquet")
    db.events.append("signup", {"user": "ada"})
    db.events.append("login", {"user": "ada"})

    db.arrow.export("event", path)
    before = db.events.len()
    db.arrow.import_("event", path)  # re-derives: appends onto the log

    assert db.events.len() == before + 2
    # sequence/timestamp/hash are reassigned by the append, so the chain still verifies.
    assert db.events.verify_chain().valid
