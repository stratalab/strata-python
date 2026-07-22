"""P4 behavior tests for db.vectors and db.events."""

from __future__ import annotations

import pytest

import stratadb
from stratadb import filters


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


# --- vectors --------------------------------------------------------------


@pytest.fixture()
def vdb(db):
    db.vectors.create_collection("v", 3, metric="cosine")
    return db


@pytest.mark.parametrize("meta_val, filt_val", [(5, 5), (1.5, 1.5), (True, True), ("note", "note")])
def test_eq_filter_all_value_types(vdb, meta_val, filt_val):
    # #46: filters.eq must work for int/float/bool, not just str.
    vdb.vectors.upsert("v", "match", [1.0, 0.0, 0.0], metadata={"m": meta_val})
    vdb.vectors.upsert("v", "other", [0.0, 1.0, 0.0], metadata={"m": "different"})
    hits = vdb.vectors.query("v", [1.0, 0.0, 0.0], k=5, filter=filters.eq("m", filt_val))
    assert [h.key for h in hits] == ["match"]


def test_eq_filter_wire_tags():
    assert filters.eq("n", 9).to_wire()["conditions"][0]["value"] == {"type": "number", "value": 9}
    assert filters.eq("f", 1.5).to_wire()["conditions"][0]["value"] == {"type": "number", "value": 1.5}
    assert filters.eq("b", True).to_wire()["conditions"][0]["value"] == {"type": "bool", "value": True}
    assert filters.eq("s", "x").to_wire()["conditions"][0]["value"] == {"type": "string", "value": "x"}


def test_collection_lifecycle(db):
    db.vectors.create_collection("v", 4)
    names = [c.name for c in db.vectors.list_collections()]
    assert "v" in names
    assert db.vectors.stats("v").dimension == 4
    assert db.vectors.count("v") == 0
    db.vectors.delete_collection("v")
    assert "v" not in [c.name for c in db.vectors.list_collections()]


def test_upsert_get_exists(vdb):
    vdb.vectors.upsert("v", "k1", [1.0, 0.0, 0.0], metadata={"kind": "note"})
    entry = vdb.vectors.get("v", "k1")
    assert entry is not None
    assert list(entry.data.embedding) == [1.0, 0.0, 0.0]
    assert entry.data.metadata == {"kind": "note"}
    assert vdb.vectors.exists("v", "k1") is True
    assert vdb.vectors.get("v", "absent") is None
    assert vdb.vectors.exists("v", "absent") is False


def test_query_and_filter(vdb):
    vdb.vectors.upsert("v", "a", [1.0, 0.0, 0.0], metadata={"kind": "note"})
    vdb.vectors.upsert("v", "b", [0.0, 1.0, 0.0], metadata={"kind": "task"})
    matches = vdb.vectors.query("v", [1.0, 0.0, 0.0], k=2)
    assert matches[0].key == "a"
    filtered = vdb.vectors.query("v", [1.0, 0.0, 0.0], k=5, filter=filters.eq("kind", "task"))
    assert [m.key for m in filtered] == ["b"]


def test_index_query_returns_diagnostics(vdb):
    vdb.vectors.upsert("v", "a", [1.0, 0.0, 0.0])
    matches, diagnostics = vdb.vectors.index_query("v", [1.0, 0.0, 0.0], k=1)
    assert matches[0].key == "a"
    assert diagnostics.collection == "v"


def test_update_metadata_and_delete(vdb):
    vdb.vectors.upsert("v", "k", [1.0, 0.0, 0.0], metadata={"kind": "a"})
    vdb.vectors.update_metadata("v", "k", {"kind": "b"})
    assert vdb.vectors.get("v", "k").data.metadata == {"kind": "b"}
    vdb.vectors.delete("v", "k")
    assert vdb.vectors.get("v", "k") is None


def test_delete_by_filter(vdb):
    vdb.vectors.upsert("v", "a", [1.0, 0.0, 0.0], metadata={"kind": "drop"})
    vdb.vectors.upsert("v", "b", [0.0, 1.0, 0.0], metadata={"kind": "keep"})
    vdb.vectors.delete_by_filter("v", filters.eq("kind", "drop"))
    assert vdb.vectors.exists("v", "a") is False
    assert vdb.vectors.exists("v", "b") is True


def test_vector_batch(vdb):
    ack = vdb.vectors.upsert_many("v", [("a", [1.0, 0.0, 0.0]), ("b", [0.0, 1.0, 0.0], {"kind": "x"})])
    assert ack.status in {"ok", "partial"}
    assert vdb.vectors.count("v") == 2
    vdb.vectors.delete_many("v", ["a"])
    assert vdb.vectors.exists("v", "a") is False


def test_vector_keys_page(vdb):
    vdb.vectors.upsert("v", "a", [1.0, 0.0, 0.0])
    page = vdb.vectors.keys("v")
    assert list(page) == ["a"]


# --- events ---------------------------------------------------------------


def test_append_get_and_len(db):
    appended = db.events.append("signup", {"user": "alice"})
    assert appended.sequence == 0
    event = db.events.get(0)
    assert event.event.payload == {"user": "alice"}
    assert db.events.get(999) is None
    assert db.events.exists(0) is True
    assert db.events.len() == 1
    assert len(db.events) == 1


def test_hash_chain(db):
    db.events.append("a", {"n": 1})
    db.events.append("b", {"n": 2})
    e0 = db.events.get(0)
    e1 = db.events.get(1)
    assert e0.event.previous_hash == "0" * 64
    assert e1.event.previous_hash == e0.event.hash
    chain = db.events.verify_chain()
    assert chain.valid is True
    assert chain.length == 2


def test_range_and_list_and_types(db):
    db.events.append("signup", {"n": 1})
    db.events.append("login", {"n": 2})
    db.events.append("signup", {"n": 3})
    forward = list(db.events.range(0))
    assert [e.event.sequence for e in forward] == [0, 1, 2]
    reverse = list(db.events.range(2, reverse=True))
    assert reverse[0].event.sequence == 2
    signups = list(db.events.list(event_type="signup"))
    assert all(e.event.event_type == "signup" for e in signups)
    assert sorted(db.events.types()) == ["login", "signup"]


def test_append_many(db):
    db.events.append_many([("a", {"n": 1}), ("b", {"n": 2})])
    assert db.events.len() == 2
