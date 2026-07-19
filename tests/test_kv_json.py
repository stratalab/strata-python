"""P3 behavior tests for the curated db.kv and db.json namespaces.

Assertions are on values, types, codes, and classes — never on message text.
Every test runs on an in-memory database.
"""

from __future__ import annotations

import pytest

import stratadb
from stratadb import errors


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


# --- kv -------------------------------------------------------------------


def test_kv_put_get_roundtrip_str_and_bytes(db):
    db.kv.put("greeting", "hello")
    assert db.kv.get("greeting") == b"hello"
    db.kv.put(b"binkey", b"\x00\x01\x02")
    assert db.kv.get(b"binkey") == b"\x00\x01\x02"


def test_kv_miss_is_none(db):
    assert db.kv.get("absent") is None
    assert db.kv.get_entry("absent") is None


def test_kv_get_entry_carries_version(db):
    db.kv.put("k", "v")
    entry = db.kv.get_entry("k")
    assert entry.value == b"v"
    assert entry.version > 0 and entry.timestamp > 0


def test_kv_exists_and_count(db):
    db.kv.put("a", "1")
    db.kv.put("b", "2")
    assert db.kv.exists("a") is True
    assert db.kv.exists("nope") is False
    assert db.kv.count() == 2


def test_kv_pagination_iterates_all(db):
    for i in range(20):
        db.kv.put(f"k{i:02d}", str(i))
    assert sorted(db.kv.iter_keys()) == sorted(k.encode() for k in (f"k{i:02d}" for i in range(20)))
    rows = list(db.kv.iter_rows())
    assert len(rows) == 20


def test_kv_keys_page_shape(db):
    db.kv.put("a", "1")
    page = db.kv.keys()
    assert list(page) == [b"a"]
    assert page.has_more is False


def test_kv_sample_reports_total(db):
    for i in range(5):
        db.kv.put(f"k{i}", str(i))
    sample = db.kv.sample()
    assert sample.total_count == 5
    assert len(sample) >= 1


def test_kv_batch_ops(db):
    ack = db.kv.put_many({"x": "1", "y": "2"})
    assert ack.status == "ok"
    assert len(ack) == 2
    assert db.kv.get_many(["x", "absent", "y"]) == [b"1", None, b"2"]
    assert db.kv.exists_many(["x", "absent"]) == [True, False]
    assert db.kv.delete_many(["x"]).status == "ok"
    assert db.kv.get("x") is None


def test_kv_history_and_miss(db):
    db.kv.put("k", "1")
    db.kv.put("k", "2")
    history = db.kv.history("k")
    assert len(history) == 2
    assert db.kv.history("never") is None


def test_kv_time_travel(db):
    first = db.kv.put("k", "v1")
    at = first.commit.timestamp
    db.kv.put("k", "v2")
    assert db.kv.get("k") == b"v2"
    assert db.kv.get("k", as_of=at) == b"v1"


# --- json -----------------------------------------------------------------


def test_json_set_get_and_path(db):
    db.json.set("doc", "$", {"name": "note", "n": 5})
    assert db.json.get("doc") == {"name": "note", "n": 5}
    assert db.json.get("doc", "$.name") == "note"


def test_json_miss_is_none(db):
    assert db.json.get("absent") is None
    assert db.json.get_entry("absent") is None


def test_json_exists_count_keys(db):
    db.json.set("a", "$", {"x": 1})
    db.json.set("b", "$", {"y": 2})
    assert db.json.exists("a") is True
    assert db.json.count() == 2
    assert sorted(db.json.keys()) == ["a", "b"]


def test_json_batch_ops(db):
    db.json.set_many({"m1": {"a": 1}, "m2": {"b": 2}})
    assert db.json.get_many(["m1", "absent", "m2"]) == [{"a": 1}, None, {"b": 2}]
    assert db.json.delete_many(["m1"]).status in {"ok", "partial"}
    assert db.json.get("m1") is None


def test_json_indexes(db):
    db.json.create_index("byname", "$.name", index_type="tag")
    names = [idx.name for idx in db.json.list_indexes()]
    assert "byname" in names
    db.json.drop_index("byname")
    assert "byname" not in [idx.name for idx in db.json.list_indexes()]


def test_json_time_travel(db):
    first = db.json.set("d", "$", {"v": 1})
    at = first.commit.timestamp
    db.json.set("d", "$", {"v": 2})
    assert db.json.get("d") == {"v": 2}
    assert db.json.get("d", as_of=at) == {"v": 1}


def test_json_history_and_miss(db):
    db.json.set("d", "$", {"v": 1})
    db.json.set("d", "$", {"v": 2})
    history = db.json.history("d")
    assert [item.value for item in history] == [{"v": 2}, {"v": 1}]
    assert db.json.history("never") is None


def test_state_namespace_still_reserved(db):
    with pytest.raises(errors.UnsupportedError):
        _ = db.state
