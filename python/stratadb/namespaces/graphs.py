"""``db.graphs`` — the property-graph namespace (nodes, edges, traversal)."""

from __future__ import annotations

from typing import Any, Optional

from .._results import Page
from .base import Namespace


class GraphsNamespace(Namespace):
    """Named property graphs with typed nodes and directed, typed edges."""

    # --- graphs ---

    def create(self, name: str) -> Any:
        """Creates an empty graph."""
        return self._c.graph_create(name, **self._scope)

    def delete(self, name: str) -> Any:
        """Deletes a graph and all its nodes and edges."""
        return self._c.graph_delete(name, **self._scope)

    def list(self) -> list:
        """Lists the graphs (with node/edge counts)."""
        return list(self._c.graph_list(**self._scope).items)

    def meta(self, name: str) -> Any:
        """Returns a graph's metadata (node/edge counts, timestamps)."""
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
        """Adds or replaces a node."""
        return self._c.graph_node_add(
            graph,
            node_id,
            properties=properties,
            object_type=object_type,
            binding=binding,
            **self._scope,
        )

    def get_node(self, graph: str, node_id: str, *, as_of: Optional[int] = None) -> Any:
        """Returns a node, or ``None`` if absent."""
        result = self._c.graph_node_get(graph, node_id, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def remove_node(self, graph: str, node_id: str) -> Any:
        """Removes a node (and its incident edges)."""
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
        """One page of a graph's nodes."""
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
        """Adds or replaces a directed, typed edge from ``src`` to ``dst``."""
        return self._c.graph_edge_add(
            graph, src, edge_type, dst, weight=weight, properties=properties, **self._scope
        )

    def get_edge(
        self, graph: str, src: str, edge_type: str, dst: str, *, as_of: Optional[int] = None
    ) -> Any:
        """Returns an edge, or ``None`` if absent."""
        result = self._c.graph_edge_get(graph, src, edge_type, dst, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def remove_edge(self, graph: str, src: str, edge_type: str, dst: str) -> Any:
        """Removes an edge."""
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
        """A page of a node's neighbors (``direction`` is outgoing/incoming/both)."""
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
