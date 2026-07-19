"""``db.graphs`` — the property-graph namespace (nodes, edges, traversal)."""

from __future__ import annotations

from typing import Any, Optional

from .._results import Page, Sample
from .base import Namespace


class GraphsNamespace(Namespace):
    """Named property graphs with typed nodes and directed, typed edges.

    Examples:
        >>> _ = db.graphs.create("social")
        >>> _ = db.graphs.add_node("social", "ada")
        >>> _ = db.graphs.add_node("social", "grace")
        >>> _ = db.graphs.add_edge("social", "ada", "knows", "grace")
        >>> db.graphs.list()
        ['social']
        >>> [hit.node_id for hit in db.graphs.neighbors("social", "ada")]
        ['grace']
    """

    # --- graphs ---

    def create(self, name: str) -> Any:
        """Creates an empty graph.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> db.graphs.list()
            ['social']
        """
        return self._c.graph_create(name, **self._scope)

    def delete(self, name: str) -> Any:
        """Deletes a graph and all its nodes and edges.

        Examples:
            >>> _ = db.graphs.create("temp")
            >>> _ = db.graphs.delete("temp")
            >>> db.graphs.list()
            []
        """
        return self._c.graph_delete(name, **self._scope)

    def list(self) -> list:
        """Lists the graphs (with node/edge counts).

        Examples:
            >>> _ = db.graphs.create("social")
            >>> db.graphs.list()
            ['social']
        """
        return list(self._c.graph_list(**self._scope).items)

    def meta(self, name: str) -> Any:
        """Returns a graph's metadata (node/edge counts, timestamps).

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> db.graphs.meta("social").node_count
            2
        """
        return self._c.graph_meta(name, **self._scope)

    # --- nodes ---

    def add_node(
        self,
        graph: str,
        node_id: str,
        *,
        properties: Optional[dict] = None,
        object_type: Optional[str] = None,
        binding: Optional[dict] = None,
    ) -> Any:
        """Adds or replaces a node.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice", properties={"age": 30}, object_type="person")
            >>> db.graphs.get_node("social", "alice").properties
            {'age': 30}
        """
        return self._c.graph_node_add(
            graph,
            node_id,
            properties=properties,
            object_type=object_type,
            binding=binding,
            **self._scope,
        )

    def get_node(self, graph: str, node_id: str, *, as_of: Optional[int] = None) -> Any:
        """Returns a node, or ``None`` if absent.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice", properties={"age": 30}, object_type="person")
            >>> db.graphs.get_node("social", "alice").properties
            {'age': 30}
            >>> db.graphs.get_node("social", "absent") is None
            True
        """
        result = self._c.graph_node_get(graph, node_id, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def remove_node(self, graph: str, node_id: str) -> Any:
        """Removes a node (and its incident edges).

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.remove_node("social", "alice")
            >>> db.graphs.get_node("social", "alice") is None
            True
        """
        return self._c.graph_node_remove(graph, node_id, **self._scope)

    def list_nodes(
        self,
        graph: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
        prefix: Optional[str] = None,
    ) -> Page:
        """One page of a graph's nodes.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> [n.node_id for n in db.graphs.list_nodes("social")]
            ['alice', 'bob']
        """
        return Page.from_wire(
            self._c.graph_node_list(
                graph, limit=limit, cursor=cursor, as_of=as_of, prefix=prefix, **self._scope
            )
        )

    # --- edges ---

    def add_edge(
        self,
        graph: str,
        src: str,
        edge_type: str,
        dst: str,
        *,
        weight: Optional[float] = None,
        properties: Optional[dict] = None,
    ) -> Any:
        """Adds or replaces a directed, typed edge from ``src`` to ``dst``.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> _ = db.graphs.add_edge("social", "alice", "knows", "bob")
            >>> db.graphs.get_edge("social", "alice", "knows", "bob").edge_type
            'knows'
        """
        return self._c.graph_edge_add(
            graph, src, edge_type, dst, weight=weight, properties=properties, **self._scope
        )

    def get_edge(
        self, graph: str, src: str, edge_type: str, dst: str, *, as_of: Optional[int] = None
    ) -> Any:
        """Returns an edge, or ``None`` if absent.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> _ = db.graphs.add_edge("social", "alice", "knows", "bob")
            >>> db.graphs.get_edge("social", "alice", "knows", "bob").edge_type
            'knows'
            >>> db.graphs.get_edge("social", "alice", "knows", "absent") is None
            True
        """
        result = self._c.graph_edge_get(graph, src, edge_type, dst, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def remove_edge(self, graph: str, src: str, edge_type: str, dst: str) -> Any:
        """Removes an edge.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> _ = db.graphs.add_edge("social", "alice", "knows", "bob")
            >>> _ = db.graphs.remove_edge("social", "alice", "knows", "bob")
            >>> db.graphs.get_edge("social", "alice", "knows", "bob") is None
            True
        """
        return self._c.graph_edge_remove(graph, src, edge_type, dst, **self._scope)

    # --- traversal ---

    def neighbors(
        self,
        graph: str,
        node_id: str,
        *,
        direction: str = "outgoing",
        edge_type: Optional[str] = None,
        limit: Optional[int] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """A page of a node's neighbors (``direction`` is outgoing/incoming/both).

        Each hit exposes ``.node_id`` (the neighbor, in any direction), plus
        ``.edge`` and ``.node``. Prefer ``.node_id``: ``.dst`` is the edge's dst,
        which for ``direction="incoming"`` is the queried node, not the neighbor.

        Examples:
            >>> _ = db.graphs.create("social")
            >>> _ = db.graphs.add_node("social", "alice")
            >>> _ = db.graphs.add_node("social", "bob")
            >>> _ = db.graphs.add_edge("social", "alice", "knows", "bob")
            >>> [n.node_id for n in db.graphs.neighbors("social", "alice", direction="outgoing")]
            ['bob']
        """
        return Page.from_wire(
            self._c.graph_neighbors(
                graph,
                node_id,
                direction,
                edge_type=edge_type,
                limit=limit,
                as_of=as_of,
                **self._scope,
            )
        )

    def bindings_for_entity(
        self, primitive: str, key: str, *, space: Optional[str] = None
    ) -> Page:
        """Graph nodes bound to a product entity (``primitive`` is kv/json/vector/event/graph).

        Examples:
            >>> _ = db.graphs.create("kb")
            >>> _ = db.graphs.add_node("kb", "ada", binding={"target": {"primitive": "kv", "space": "default", "key": "user:1"}})  # Bind the node to a KV entity so retrieval can cross primitives.
            >>> [h.node_id for h in db.graphs.bindings_for_entity("kv", "user:1")]
            ['ada']
        """
        target = {
            "primitive": primitive,
            "key": key,
            "space": space if space is not None else (self._space or "default"),
        }
        if self._branch is not None:
            target["branch"] = self._branch
        return Page.from_wire(self._c.graph_bindings(target, **self._scope))

    def batch_write(self, graph: str, operations: list) -> Any:
        """Applies a batch of node/edge operations atomically.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.batch_write("g", [{"type": "upsert_node", "node_id": "a", "data": {"object_type": "person"}}, {"type": "upsert_node", "node_id": "b", "data": {"object_type": "person"}}, {"type": "upsert_edge", "src": "a", "edge_type": "knows", "dst": "b", "data": {}}])  # All operations land in one engine commit, or none do.
            >>> db.graphs.meta("g").node_count
            2
        """
        return self._c.graph_batch_write(graph, operations, **self._scope)

    def apply_delete_policy(
        self, primitive: str, key: str, policy: str, *, space: Optional[str] = None
    ) -> Any:
        """Apply a delete policy to the graph facts bound to a product entity.

        ``policy`` is ``"cascade"`` (delete the bound nodes and their incident
        edges), ``"detach"`` (keep the nodes, drop their entity bindings), or
        ``"keep_dangling"`` (keep the bindings; traversal reports the status).

        Examples:
            >>> _ = db.graphs.create("kb")
            >>> _ = db.graphs.add_node("kb", "ada", binding={"target": {"primitive": "kv", "space": "default", "key": "user:1"}})
            >>> _ = db.graphs.apply_delete_policy("kv", "user:1", "cascade")  # cascade removes the bound node and its incident edges.
            >>> db.graphs.get_node("kb", "ada") is None
            True
        """
        target = {
            "primitive": primitive,
            "key": key,
            "space": space if space is not None else (self._space or "default"),
        }
        if self._branch is not None:
            target["branch"] = self._branch
        return self._c.graph_apply_delete_policy(target, policy, **self._scope)

    # --- bulk / typed listing / sample ---

    def bulk_insert(
        self,
        graph: str,
        *,
        nodes: Optional[list] = None,
        edges: Optional[list] = None,
        chunk_size: Optional[int] = None,
    ) -> Any:
        """Insert many nodes and edges in one commit.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.bulk_insert("g", nodes=[{"node_id": "a", "object_type": "person"}, {"node_id": "b", "object_type": "person"}], edges=[{"src": "a", "edge_type": "knows", "dst": "b"}])
            >>> db.graphs.meta("g").node_count
            2
        """
        return self._c.graph_bulk_insert(
            graph, nodes=nodes, edges=edges, chunk_size=chunk_size, **self._scope
        )

    def nodes_by_type(
        self,
        graph: str,
        object_type: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """A page of nodes of a given object type.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a", object_type="person")
            >>> _ = db.graphs.add_node("g", "b", object_type="person")
            >>> [n.node_id for n in db.graphs.nodes_by_type("g", "person")]
            ['a', 'b']
        """
        return Page.from_wire(
            self._c.graph_nodes_by_type(
                graph, object_type, limit=limit, cursor=cursor, as_of=as_of, **self._scope
            )
        )

    def sample(self, graph: str, *, count: Optional[int] = None) -> Sample:
        """A representative sample of nodes plus the total count.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> db.graphs.sample("g").total_count
            2
        """
        return Sample.from_wire(self._c.graph_sample(graph, count=count, **self._scope))

    # --- analytics + ontology sub-namespaces ---

    @property
    def analytics(self) -> "GraphAnalytics":
        """Graph algorithms (PageRank, BFS, SSSP, WCC, CDLP, LCC)."""
        ns = self.__dict__.get("_analytics")
        if ns is None:
            ns = GraphAnalytics(self._c, self._core, self._branch, self._space)
            self.__dict__["_analytics"] = ns
        return ns

    @property
    def ontology(self) -> "GraphOntology":
        """The graph's typed schema (object and link types)."""
        ns = self.__dict__.get("_ontology")
        if ns is None:
            ns = GraphOntology(self._c, self._core, self._branch, self._space)
            self.__dict__["_ontology"] = ns
        return ns


class GraphAnalytics(Namespace):
    """``db.graphs.analytics`` — algorithms over a named graph.

    Each method returns a typed result carrying the algorithm's per-node output
    plus its metadata (e.g. PageRank's ``.ranks`` + ``.iterations``).
    """

    def pagerank(
        self,
        graph: str,
        *,
        damping: Optional[float] = None,
        max_iterations: Optional[int] = None,
        tolerance: Optional[float] = None,
        personalization: Optional[dict] = None,
        budget: Optional[dict] = None,
        as_of: Optional[int] = None,
    ) -> Any:
        """PageRank importance scores (``.ranks`` maps node id to score).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> sorted(db.graphs.analytics.pagerank("g").ranks)
            ['a', 'b', 'c']
        """
        return self._c.graph_analytics_pagerank(
            graph,
            damping=damping,
            max_iterations=max_iterations,
            tolerance=tolerance,
            personalization=personalization,
            budget=budget,
            as_of=as_of,
            **self._scope,
        )

    def bfs(
        self,
        graph: str,
        start: str,
        *,
        direction: Optional[str] = None,
        edge_types: Optional[list] = None,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        budget: Optional[dict] = None,
        as_of: Optional[int] = None,
    ) -> Any:
        """Breadth-first traversal from ``start`` (``.visited``, ``.depths``, ``.edges``).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> db.graphs.analytics.bfs("g", "a").visited
            ['a', 'b', 'c']
        """
        return self._c.graph_analytics_bfs(
            graph,
            start,
            direction=direction,
            edge_types=edge_types,
            max_depth=max_depth,
            max_nodes=max_nodes,
            budget=budget,
            as_of=as_of,
            **self._scope,
        )

    def sssp(
        self,
        graph: str,
        source: str,
        *,
        direction: Optional[str] = None,
        budget: Optional[dict] = None,
        as_of: Optional[int] = None,
    ) -> Any:
        """Single-source shortest paths from ``source`` (``.distances``).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> sorted(db.graphs.analytics.sssp("g", "a").distances)
            ['a', 'b', 'c']
        """
        return self._c.graph_analytics_sssp(
            graph, source, direction=direction, budget=budget, as_of=as_of, **self._scope
        )

    def wcc(self, graph: str, *, budget: Optional[dict] = None, as_of: Optional[int] = None) -> Any:
        """Weakly-connected components (``.components`` maps node id to component).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> db.graphs.analytics.wcc("g").component_count
            1
        """
        return self._c.graph_analytics_wcc(graph, budget=budget, as_of=as_of, **self._scope)

    def cdlp(
        self,
        graph: str,
        *,
        direction: Optional[str] = None,
        max_iterations: Optional[int] = None,
        budget: Optional[dict] = None,
        as_of: Optional[int] = None,
    ) -> Any:
        """Community detection by label propagation (``.labels``).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> sorted(db.graphs.analytics.cdlp("g").labels)
            ['a', 'b', 'c']
        """
        return self._c.graph_analytics_cdlp(
            graph,
            direction=direction,
            max_iterations=max_iterations,
            budget=budget,
            as_of=as_of,
            **self._scope,
        )

    def lcc(self, graph: str, *, budget: Optional[dict] = None, as_of: Optional[int] = None) -> Any:
        """Local clustering coefficient per node (``.coefficients``).

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.add_node("g", "a")
            >>> _ = db.graphs.add_node("g", "b")
            >>> _ = db.graphs.add_node("g", "c")
            >>> _ = db.graphs.add_edge("g", "a", "knows", "b")
            >>> _ = db.graphs.add_edge("g", "b", "knows", "c")
            >>> sorted(db.graphs.analytics.lcc("g").coefficients)
            ['a', 'b', 'c']
        """
        return self._c.graph_analytics_lcc(graph, budget=budget, as_of=as_of, **self._scope)


class GraphOntology(Namespace):
    """``db.graphs.ontology`` — the graph's typed schema (object + link types)."""

    def define_object_type(
        self, graph: str, name: str, *, properties: Optional[dict] = None
    ) -> Any:
        """Define an object (node) type, optionally with a property schema.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> [o.name for o in db.graphs.ontology.summary("g").object_types]
            ['person']
        """
        return self._c.graph_ontology_define_object_type(
            graph, name, properties=properties, **self._scope
        )

    def define_link_type(
        self,
        graph: str,
        name: str,
        source: str,
        target: str,
        *,
        cardinality: Optional[str] = None,
        properties: Optional[dict] = None,
    ) -> Any:
        """Define a link (edge) type from a ``source`` to a ``target`` object type.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> _ = db.graphs.ontology.define_link_type("g", "knows", "person", "person")
            >>> [l.name for l in db.graphs.ontology.get("g").link_types]
            ['knows']
        """
        return self._c.graph_ontology_define_link_type(
            graph,
            name,
            source,
            target,
            cardinality=cardinality,
            properties=properties,
            **self._scope,
        )

    def delete_object_type(self, graph: str, name: str) -> Any:
        """Remove an object type from the ontology.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> _ = db.graphs.ontology.define_object_type("g", "company")
            >>> _ = db.graphs.ontology.delete_object_type("g", "company")
            >>> [o.name for o in db.graphs.ontology.summary("g").object_types]
            ['person']
        """
        return self._c.graph_ontology_delete_object_type(graph, name, **self._scope)

    def delete_link_type(self, graph: str, name: str) -> Any:
        """Remove a link type from the ontology.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> _ = db.graphs.ontology.define_link_type("g", "knows", "person", "person")
            >>> _ = db.graphs.ontology.delete_link_type("g", "knows")
        """
        return self._c.graph_ontology_delete_link_type(graph, name, **self._scope)

    def freeze(self, graph: str) -> Any:
        """Freeze the ontology so its types can no longer change.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> _ = db.graphs.ontology.freeze("g")
            >>> db.graphs.ontology.get("g").status
            'frozen'
        """
        return self._c.graph_ontology_freeze(graph, **self._scope)

    def get(self, graph: str, *, as_of: Optional[int] = None) -> Any:
        """The full ontology, or ``None`` if none is defined.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> db.graphs.ontology.get("g").status
            'draft'
        """
        return self._c.graph_ontology_get(graph, as_of=as_of, **self._scope)

    def summary(self, graph: str, *, as_of: Optional[int] = None) -> Any:
        """A summary of the ontology (types and their node counts), or ``None``.

        Examples:
            >>> _ = db.graphs.create("g")
            >>> _ = db.graphs.ontology.define_object_type("g", "person")
            >>> [o.name for o in db.graphs.ontology.summary("g").object_types]
            ['person']
        """
        return self._c.graph_ontology_summary(graph, as_of=as_of, **self._scope)
