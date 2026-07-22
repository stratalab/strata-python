"""Pagination & namespace-gap tests (WS3: #40, #41, #39, #59, #61)."""

from __future__ import annotations

import pytest

import stratadb
from stratadb import errors, filters
from stratadb.namespaces.base import PAGE_SIZE


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


def _seed_kv(db, n):
    db.kv.put_many({f"k{i:04d}": "v" for i in range(n)})


# --- #40: Page auto-paginates on iteration --------------------------------


def test_keys_iterate_all_pages(db):
    _seed_kv(db, 600)
    page = db.kv.keys()
    assert len(list(page)) == 600  # iteration walks every page
    assert page.all() == list(page)
    assert len(page.items) == PAGE_SIZE  # first page only
    assert page.has_more is True


def test_explicit_limit_is_a_bounded_page(db):
    _seed_kv(db, 600)
    page = db.kv.keys(limit=10)
    assert len(list(page)) == 10  # explicit limit does not auto-paginate


def test_len_and_getitem_are_first_page(db):
    _seed_kv(db, 600)
    page = db.kv.keys()
    assert len(page) == len(page.items) == PAGE_SIZE  # first page
    assert page[0] == b"k0000"
    assert len(list(page)) == 600  # but iteration is everything


def test_pages_walks_page_objects(db):
    _seed_kv(db, 600)
    pages = list(db.kv.keys().pages())
    assert len(pages) >= 2
    assert sum(len(p.items) for p in pages) == 600


def test_small_result_back_compat(db):
    _seed_kv(db, 3)
    page = db.kv.keys()
    assert len(page) == len(list(page)) == 3
    assert page.has_more is False


def test_json_keys_and_scan_paginate(db):
    db.json.set_many({f"d{i:04d}": {"v": i} for i in range(600)})
    assert len(list(db.json.keys())) == 600
    assert len(list(db.json.scan())) == 600


def test_vectors_keys_paginate(db):
    db.vectors.create_collection("c", 2)
    db.vectors.upsert_many("c", [{"key": f"v{i:04d}", "vector": [1.0, 0.0]} for i in range(600)])
    assert len(list(db.vectors.keys("c"))) == 600
    assert len(list(db.vectors.iter_keys("c"))) == 600


def test_graph_list_nodes_paginate(db):
    db.graphs.create("g")
    db.graphs.bulk_insert("g", nodes=[{"node_id": f"n{i:04d}"} for i in range(600)])
    assert len(list(db.graphs.list_nodes("g"))) == 600


def test_events_list_paginates_and_is_bounded_first_page(db):
    for i in range(600):
        db.events.append("e", {"i": i})
    page = db.events.list()
    assert len(page.items) <= PAGE_SIZE  # not the whole log in one page
    assert page.has_more is True
    assert len(list(page)) == 600


# --- #41: limit<=0 rejected -----------------------------------------------


@pytest.mark.parametrize("bad", [0, -1])
def test_non_positive_limit_rejected(db, bad):
    _seed_kv(db, 5)
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.kv.keys(limit=bad)
    assert excinfo.value.code == "invalid_argument.sdk.limit"


def test_limit_guard_is_shared_across_namespaces(db):
    db.json.set("d", "$", {"v": 1})
    with pytest.raises(errors.InvalidArgumentError):
        db.json.keys(limit=0)
    with pytest.raises(errors.InvalidArgumentError):
        db.events.range(0, limit=0)


def test_limit_none_still_works(db):
    _seed_kv(db, 3)
    assert len(db.kv.keys(limit=None).items) == 3


# --- #39: neighbors accepts the cursor it hands out -----------------------


def test_neighbors_cursor_roundtrip(db):
    db.graphs.create("g")
    db.graphs.add_node("g", "hub")
    for i in range(10):
        db.graphs.add_node("g", f"n{i}")
        db.graphs.add_edge("g", "hub", "rel", f"n{i}")
    p1 = db.graphs.neighbors("g", "hub", limit=4)
    assert len(p1.items) == 4 and p1.has_more
    p2 = db.graphs.neighbors("g", "hub", limit=4, cursor=p1.cursor)
    assert {h.node_id for h in p1.items}.isdisjoint(h.node_id for h in p2.items)
    # no-limit auto-paginates to every neighbor
    assert len([n.node_id for n in db.graphs.neighbors("g", "hub")]) == 10


# --- #59: db.json.scan() exists (seek, not prefix) ------------------------


def test_json_scan_is_a_seek(db):
    db.json.set_many({"a": {"v": 1}, "b": {"v": 2}, "c": {"v": 3}})
    assert [r.value for r in db.json.scan()] == [{"v": 1}, {"v": 2}, {"v": 3}]
    assert [r.value for r in db.json.scan(start="b")] == [{"v": 2}, {"v": 3}]
    assert [r.value for r in db.json.iter_rows()] == [{"v": 1}, {"v": 2}, {"v": 3}]


# --- #61: metadata dict guard + metric aliases ----------------------------


@pytest.mark.parametrize("bad", [[1, 2, 3], "x", 5])
def test_metadata_must_be_dict(db, bad):
    db.vectors.create_collection("c", 2)
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.vectors.upsert("c", "a", [1.0, 0.0], metadata=bad)
    assert excinfo.value.code == "invalid_argument.sdk.vector_metadata"


def test_metadata_guard_in_batch(db):
    db.vectors.create_collection("c", 2)
    with pytest.raises(errors.InvalidArgumentError):
        db.vectors.upsert_many("c", [{"key": "a", "vector": [1.0, 0.0], "metadata": [1, 2]}])


def test_metric_aliases(db):
    db.vectors.create_collection("euc", 2, metric="l2")
    db.vectors.create_collection("dot", 2, metric="dot")
    assert _metric_name(db.vectors.stats("euc").metric) == "euclidean"
    assert _metric_name(db.vectors.stats("dot").metric) == "dot_product"


def test_unknown_metric_raises_typed(db):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.vectors.create_collection("bad", 2, metric="bogus")
    assert excinfo.value.code == "invalid_argument.sdk.vector_metric"


def _metric_name(metric):
    return getattr(metric, "value", metric)
