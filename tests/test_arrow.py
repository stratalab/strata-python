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


# --- engine 1.2.1's import/export corrections, from the SDK's side ---------


def test_nested_documents_survive_a_round_trip(db, tmp_path):
    # strata-core #3063/#3075/#3091: nested objects, lists and map/dictionary
    # columns used to come back as the Display string of the Arrow cell
    # ("{n: 1}"), not as data. This is the user-visible half of that fix.
    document = {
        "name": "ada",
        "tags": ["analytical", "engine"],
        "meta": {"born": 1815, "notes": {"fields": [1, 2, 3]}},
    }
    path = str(tmp_path / "json.parquet")
    db.json.set("doc", "$", document)
    db.arrow.export("json", path)
    db.json.delete("doc")
    db.arrow.import_("json", path)

    assert db.json.get("doc", "$") == document
    assert db.json.get("doc", "$.meta.notes.fields") == [1, 2, 3]


def test_vector_export_to_csv_is_refused_up_front(db, tmp_path):
    # strata-core #3082: CSV cannot carry an embedding, and the export used to
    # loop writing a truncated file instead of saying so.
    db.vectors.create_collection("docs", 2)
    db.vectors.upsert("docs", "k", [1.0, 0.0])
    with pytest.raises(stratadb.errors.InvalidArgumentError) as excinfo:
        db.arrow.export("vector", str(tmp_path / "docs.csv"), format="csv", collection="docs")
    assert excinfo.value.code == "invalid_argument.executor.arrow_format"


def test_csv_import_keeps_text_keys_as_text(db, tmp_path):
    # strata-core #3077: CSV import re-inferred column types, so a zero-padded
    # text key ("007") arrived as the integer 7 and the row was unfindable.
    path = tmp_path / "kv.csv"
    path.write_text("key,value\n007,hello\n042,world\n")
    db.arrow.import_("kv", str(path), format="csv")

    assert db.kv.get("007") == b"hello"
    assert db.kv.get("042") == b"world"
