"""P5 behavior tests: db.graphs, db.branches, db.spaces, db.admin, db.arrow, db.at()."""

from __future__ import annotations

import pytest

import stratadb


@pytest.fixture()
def db():
    database = stratadb.Strata(cache=True)
    yield database
    database.close()


# --- graphs ---------------------------------------------------------------


def test_graph_nodes_and_edges(db):
    db.graphs.create("g")
    db.graphs.add_node("g", "n1", properties={"label": "start"})
    db.graphs.add_node("g", "n2")
    db.graphs.add_edge("g", "n1", "knows", "n2", weight=0.5)

    node = db.graphs.get_node("g", "n1")
    assert node.node_id == "n1"
    assert node.properties == {"label": "start"}
    assert db.graphs.get_node("g", "absent") is None

    edge = db.graphs.get_edge("g", "n1", "knows", "n2")
    assert edge.weight == 0.5
    assert db.graphs.get_edge("g", "n1", "knows", "absent") is None

    meta = db.graphs.meta("g")
    assert meta.node_count == 2 and meta.edge_count == 1
    listed = db.graphs.list()
    names = [g if isinstance(g, str) else g.graph for g in listed]
    assert "g" in names


def test_graph_neighbors_and_nodes(db):
    db.graphs.create("g")
    db.graphs.add_node("g", "a")
    db.graphs.add_node("g", "b")
    db.graphs.add_edge("g", "a", "to", "b")
    neighbors = list(db.graphs.neighbors("g", "a", direction="outgoing"))
    assert [n.node_id for n in neighbors] == ["b"]
    assert sorted(n.node_id for n in db.graphs.list_nodes("g")) == ["a", "b"]


def test_graph_remove(db):
    db.graphs.create("g")
    db.graphs.add_node("g", "a")
    db.graphs.remove_node("g", "a")
    assert db.graphs.get_node("g", "a") is None


# --- branches -------------------------------------------------------------


def test_branch_lifecycle(db):
    assert "default" in [b.name for b in db.branches.list()]
    assert db.branches.get("default").name == "default"
    assert db.branches.get("ghost") is None

    db.branches.create("empty")
    assert "empty" in db.branches

    forked = db.branches.fork("default", "feature")
    assert forked.name == "feature"
    assert forked.parent.name == "default"

    db.branches.delete("empty")
    assert "empty" not in db.branches


def test_branch_isolation(db):
    db.kv.put("k", "on-default")
    db.branches.fork("default", "feature")
    feature = db.at(branch="feature")
    feature.kv.put("k", "on-feature")
    assert db.kv.get("k") == b"on-default"
    assert feature.kv.get("k") == b"on-feature"


def test_fork_rejects_both_anchors(db):
    with pytest.raises(ValueError):
        db.branches.fork("default", "x", version=1, timestamp=1)


# --- spaces ---------------------------------------------------------------


def test_space_lifecycle(db):
    assert "default" in db.spaces
    db.spaces.create("tenant_a")
    assert db.spaces.exists("tenant_a")
    assert "tenant_a" in [s for s in db.spaces]
    db.spaces.delete("tenant_a")
    assert not db.spaces.exists("tenant_a")


def test_space_isolation(db):
    db.spaces.create("s2")
    db.kv.put("k", "default-space")
    s2 = db.at(space="s2")
    s2.kv.put("k", "s2-space")
    assert db.kv.get("k") == b"default-space"
    assert s2.kv.get("k") == b"s2-space"


# --- admin ----------------------------------------------------------------


def test_admin_surface(db):
    assert db.admin.ping().version == "1.0.0"
    assert db.admin.info().default_branch == "default"
    assert db.admin.health().status == "healthy"
    assert db.admin.config().target == "cache"


# --- db.at() scoping ------------------------------------------------------


def test_at_returns_scoped_view_sharing_handle(db):
    view = db.at(branch="default", space="default")
    view.kv.put("shared", "value")
    assert db.kv.get("shared") == b"value"
    assert view.version == db.version
