"""Behavior tests for the graph entity-binding trio: atomic batch_write,
bindings_for_entity, and apply_delete_policy (cascade vs detach)."""

from __future__ import annotations

import pytest

import stratadb

KV_TARGET = {"primitive": "kv", "space": "default", "key": "user:1"}


@pytest.fixture()
def db():
    handle = stratadb.Strata(cache=True)
    yield handle
    handle.close()


def _bind_ada(graphs):
    graphs.create("kb")
    graphs.add_node("kb", "ada", binding={"target": KV_TARGET})


def test_batch_write_is_atomic(db):
    db.graphs.create("g")
    db.graphs.batch_write(
        "g",
        [
            {"type": "upsert_node", "node_id": "a", "data": {"object_type": "person"}},
            {"type": "upsert_node", "node_id": "b", "data": {"object_type": "person"}},
            {"type": "upsert_edge", "src": "a", "edge_type": "knows", "dst": "b", "data": {}},
        ],
    )
    meta = db.graphs.meta("g")
    assert meta.node_count == 2
    assert meta.edge_count == 1


def test_bindings_for_entity_lists_bound_node(db):
    _bind_ada(db.graphs)
    assert [h.node_id for h in db.graphs.bindings_for_entity("kv", "user:1")] == ["ada"]
    # An unbound entity has no hits.
    assert list(db.graphs.bindings_for_entity("kv", "absent")) == []


def test_apply_delete_policy_cascade_removes_bound_node(db):
    _bind_ada(db.graphs)
    db.graphs.apply_delete_policy("kv", "user:1", "cascade")
    assert db.graphs.get_node("kb", "ada") is None
    assert list(db.graphs.bindings_for_entity("kv", "user:1")) == []


def test_apply_delete_policy_detach_keeps_node_drops_binding(db):
    _bind_ada(db.graphs)
    db.graphs.apply_delete_policy("kv", "user:1", "detach")
    assert db.graphs.get_node("kb", "ada") is not None
    assert list(db.graphs.bindings_for_entity("kv", "user:1")) == []
