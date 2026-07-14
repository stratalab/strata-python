"""``db.graphs`` — the property-graph namespace (nodes, edges, traversal)."""

from __future__ import annotations

from typing import Any, Optional

from .._results import Page
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
        >>> [hit.dst for hit in db.graphs.neighbors("social", "ada")]
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

        Each hit exposes ``.dst`` (the neighbor id) plus ``.edge`` and ``.node``.

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
        """Graph nodes bound to a product entity (``primitive`` is kv/json/vector/event/graph)."""
        target = {
            "primitive": primitive,
            "key": key,
            "space": space if space is not None else (self._space or "default"),
        }
        if self._branch is not None:
            target["branch"] = self._branch
        return Page.from_wire(self._c.graph_bindings(target, **self._scope))

    def batch_write(self, graph: str, operations: list) -> Any:
        """Applies a batch of node/edge operations atomically."""
        return self._c.graph_batch_write(graph, operations, **self._scope)
