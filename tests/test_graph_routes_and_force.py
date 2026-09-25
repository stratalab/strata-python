"""Engine 1.2.5's graph surface: routes out of sssp, and deletes that refuse.

Two additions a caller meets directly. `sssp` now reports where each node's
cheapest walk arrived from, so the route is recoverable rather than just its
cost, and it can be restricted to particular edge types. Dropping a graph or a
vector collection that still holds data now takes `force=True` — the kind of
change that is better met in a test than in production.
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


@pytest.fixture()
def roads(db):
    """a -hop-> b -hop-> c -hop-> d, plus a direct a -jump-> c."""
    db.graphs.create("road")
    for node in "abcd":
        db.graphs.add_node("road", node)
    db.graphs.add_edge("road", "a", "hop", "b")
    db.graphs.add_edge("road", "b", "hop", "c")
    db.graphs.add_edge("road", "c", "hop", "d")
    db.graphs.add_edge("road", "a", "jump", "c")
    return db


# --- routes ----------------------------------------------------------------


def test_sssp_reports_the_route_not_only_the_cost(roads):
    # strata-core #3471: predecessors make the walk recoverable. The cheap way
    # to d is the jump, and path_to says so rather than leaving the caller to
    # rebuild it from distances.
    result = roads.graphs.analytics.sssp("road", "a")

    assert result.distances["d"] == 2.0  # a -> c (jump) -> d, not three hops
    assert result.predecessors["d"] == "c"
    assert result.path_to("d") == ["a", "c", "d"]
    assert result.source == "a" and result.graph == "road"


def test_path_to_handles_the_source_and_the_unreachable(roads):
    roads.graphs.add_node("road", "island")  # no edges at all
    result = roads.graphs.analytics.sssp("road", "a")

    assert result.path_to("a") == ["a"]  # the source is a walk of one
    assert result.path_to("island") is None  # unreachable, not an empty list
    assert result.path_to("not-a-node") is None


def test_edge_types_restricts_every_relaxation(roads):
    # strata-core #3456: without the jump, the only way to c is through b, so
    # both the distance and the route change.
    unrestricted = roads.graphs.analytics.sssp("road", "a")
    hops_only = roads.graphs.analytics.sssp("road", "a", edge_types=["hop"])

    assert unrestricted.path_to("c") == ["a", "c"]
    assert hops_only.path_to("c") == ["a", "b", "c"]
    assert hops_only.distances["d"] > unrestricted.distances["d"]


def test_graph_meta_reports_whether_an_import_is_pending(roads):
    # strata-core #3464: a multi-commit bulk_insert sets this on its first
    # commit and clears it on its last, so an interrupted import stays visible.
    assert roads.graphs.meta("road").import_pending is False


# --- deletes that refuse ---------------------------------------------------


def test_deleting_a_graph_with_data_needs_force(roads):
    with pytest.raises(errors.FailedPreconditionError) as excinfo:
        roads.graphs.delete("road")
    assert excinfo.value.code == "failed_precondition.engine.graph_not_empty"
    assert "road" in roads.graphs.list()  # nothing happened

    roads.graphs.delete("road", force=True)
    assert "road" not in roads.graphs.list()


def test_deleting_an_empty_graph_needs_nothing(db):
    db.graphs.create("empty")
    db.graphs.delete("empty")
    assert db.graphs.list() == []


def test_deleting_a_collection_with_vectors_needs_force(db):
    db.vectors.create_collection("docs", 2)
    db.vectors.upsert("docs", "k", [1.0, 0.0])

    with pytest.raises(errors.FailedPreconditionError) as excinfo:
        db.vectors.delete_collection("docs")
    assert excinfo.value.code == "failed_precondition.engine.vector_collection_not_empty"
    assert [c.name for c in db.vectors.list_collections()] == ["docs"]

    db.vectors.delete_collection("docs", force=True)
    assert [c.name for c in db.vectors.list_collections()] == []
