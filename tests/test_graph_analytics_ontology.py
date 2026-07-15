"""Behavior tests for the curated graph analytics + ontology sub-namespaces."""

from __future__ import annotations

import pytest

import stratadb


@pytest.fixture()
def graph():
    db = stratadb.open(cache=True)
    db.graphs.create("g")
    for node in ("a", "b", "c"):
        db.graphs.add_node("g", node, object_type="person")
    db.graphs.add_edge("g", "a", "knows", "b")
    db.graphs.add_edge("g", "b", "knows", "c")
    yield db
    db.close()


# --- analytics ------------------------------------------------------------


def test_pagerank_scores_every_node(graph):
    result = graph.graphs.analytics.pagerank("g")
    assert set(result.ranks) == {"a", "b", "c"}
    assert result.iterations > 0
    assert abs(sum(result.ranks.values()) - 1.0) < 1e-6


def test_wcc_single_component(graph):
    result = graph.graphs.analytics.wcc("g")
    assert result.component_count == 1
    assert set(result.components) == {"a", "b", "c"}


def test_bfs_and_sssp_from_source(graph):
    assert graph.graphs.analytics.bfs("g", "a").visited == ["a", "b", "c"]
    assert set(graph.graphs.analytics.sssp("g", "a").distances) == {"a", "b", "c"}


def test_cdlp_and_lcc_cover_nodes(graph):
    assert set(graph.graphs.analytics.cdlp("g").labels) == {"a", "b", "c"}
    assert set(graph.graphs.analytics.lcc("g").coefficients) == {"a", "b", "c"}


# --- ontology -------------------------------------------------------------


def test_ontology_object_and_link_types(graph):
    graph.graphs.ontology.define_object_type("g", "person")
    graph.graphs.ontology.define_link_type("g", "knows", "person", "person")
    summary = graph.graphs.ontology.summary("g")
    assert [o.name for o in summary.object_types] == ["person"]
    assert [link.name for link in graph.graphs.ontology.get("g").link_types] == ["knows"]


def test_ontology_freeze(graph):
    graph.graphs.ontology.define_object_type("g", "person")
    graph.graphs.ontology.freeze("g")
    assert graph.graphs.ontology.get("g").status == "frozen"


def test_ontology_absent_is_none():
    db = stratadb.open(cache=True)
    db.graphs.create("empty")
    assert db.graphs.ontology.get("empty") is None
    db.close()


# --- bulk / typed listing / sample ---------------------------------------


def test_bulk_insert_and_nodes_by_type():
    db = stratadb.open(cache=True)
    db.graphs.create("g")
    db.graphs.bulk_insert(
        "g",
        nodes=[{"node_id": "a", "object_type": "person"}, {"node_id": "b", "object_type": "person"}],
        edges=[{"src": "a", "edge_type": "knows", "dst": "b"}],
    )
    assert db.graphs.meta("g").node_count == 2
    assert sorted(n.node_id for n in db.graphs.nodes_by_type("g", "person")) == ["a", "b"]
    assert db.graphs.sample("g").total_count == 2
    db.close()


def test_analytics_sub_namespace_honors_scope(graph):
    # A scoped view (db.at) reaches the sub-namespace with the same scope.
    scoped = graph.at(branch=None)
    assert scoped.graphs.analytics.wcc("g").component_count == 1
