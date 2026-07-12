"""``db.vectors`` — the vector namespace (collections, upserts, similarity search)."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from .. import filters as _filters
from .._results import BatchResult, Page
from .base import Namespace


def _filter_wire(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, _filters.Filter):
        return value.to_wire()
    return value


def _vector_entries(entries: Any) -> list[dict]:
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            row = {"key": entry["key"], "vector": list(entry["vector"])}
            if entry.get("metadata") is not None:
                row["metadata"] = entry["metadata"]
        else:
            key, vector = entry[0], list(entry[1])
            row = {"key": key, "vector": vector}
            if len(entry) > 2 and entry[2] is not None:
                row["metadata"] = entry[2]
        out.append(row)
    return out


class VectorsNamespace(Namespace):
    """Vector collections with metadata-filtered similarity search."""

    # --- collections ---

    def create_collection(self, name: str, dimension: int, *, metric: str = "cosine") -> Any:
        """Creates a collection of ``dimension``-d vectors under ``metric``."""
        return self._c.vector_collection_create(name, dimension, metric, **self._scope)

    def delete_collection(self, name: str) -> Any:
        """Deletes a collection and all its vectors."""
        return self._c.vector_collection_delete(name, **self._scope)

    def list_collections(self) -> Page:
        """Lists the collections."""
        return Page.from_wire(self._c.vector_collection_list(**self._scope))

    def stats(self, name: str) -> Any:
        """Returns a collection's info (dimension, metric, count), or ``None``."""
        page = self._c.vector_collection_stats(name, **self._scope)
        for info in page.items:
            if info.name == name:
                return info
        return page.items[0] if page.items else None

    def count(self, name: str, *, as_of: Optional[int] = None) -> int:
        """Number of vectors in a collection."""
        return self._c.vector_count(name, as_of=as_of, **self._scope)

    # --- vectors ---

    def upsert(
        self,
        collection: str,
        key: str,
        vector: Sequence[float],
        *,
        metadata: Optional[dict] = None,
    ) -> Any:
        """Inserts or replaces a vector (with optional metadata)."""
        return self._c.vector_upsert(collection, key, list(vector), metadata=metadata, **self._scope)

    def get(self, collection: str, key: str, *, as_of: Optional[int] = None) -> Any:
        """Returns the stored vector + metadata, or ``None`` if absent."""
        result = self._c.vector_get(collection, key, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def history(self, collection: str, key: str) -> Optional[list]:
        """Full version history for a key, or ``None`` if it never existed."""
        result = self._c.vector_history(collection, key, **self._scope)
        return result.items if result is not None else None

    def exists(self, collection: str, key: str) -> bool:
        """Whether the key currently has a visible vector."""
        return self._c.vector_exists(collection, key, **self._scope)

    def keys(
        self,
        collection: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """One page of keys in a collection (``str`` each)."""
        return Page.from_wire(
            self._c.vector_keys(collection, limit=limit, cursor=cursor, as_of=as_of, **self._scope)
        )

    def update_metadata(self, collection: str, key: str, metadata: dict) -> Any:
        """Patches the metadata of an existing vector."""
        return self._c.vector_metadata_update(collection, key, metadata, **self._scope)

    def delete(self, collection: str, key: str) -> Any:
        """Deletes one vector."""
        return self._c.vector_delete(collection, key, **self._scope)

    def delete_all(self, collection: str) -> Any:
        """Deletes every vector in a collection."""
        return self._c.vector_delete_all(collection, **self._scope)

    def delete_by_filter(self, collection: str, filter: Any) -> Any:
        """Deletes every vector whose metadata matches ``filter``."""
        return self._c.vector_delete_by_filter(collection, _filter_wire(filter), **self._scope)

    # --- search ---

    def query(
        self,
        collection: str,
        vector: Sequence[float],
        *,
        k: int = 10,
        filter: Any = None,
        as_of: Optional[int] = None,
    ) -> list:
        """Returns the ``k`` nearest matches, optionally metadata-filtered."""
        return self._c.vector_query(
            collection, list(vector), k, filter=_filter_wire(filter), as_of=as_of, **self._scope
        )

    def index_query(
        self,
        collection: str,
        vector: Sequence[float],
        *,
        k: int = 10,
        filter: Any = None,
        as_of: Optional[int] = None,
    ) -> Tuple[list, Any]:
        """Like ``query`` but also returns index diagnostics: ``(matches, diagnostics)``."""
        result = self._c.vector_index_query(
            collection, list(vector), k, filter=_filter_wire(filter), as_of=as_of, **self._scope
        )
        return result.matches, result.diagnostics

    # --- batch ---

    def upsert_many(self, collection: str, entries: Any) -> BatchResult:
        """Upserts many vectors. Each entry is (key, vector[, metadata]) or a dict."""
        return BatchResult.from_wire(
            self._c.vector_batch_upsert(collection, _vector_entries(entries), **self._scope)
        )

    def get_many(self, collection: str, keys: Sequence[str]) -> BatchResult:
        """Reads many vectors positionally."""
        return BatchResult.from_wire(
            self._c.vector_batch_get(collection, list(keys), **self._scope)
        )

    def delete_many(self, collection: str, keys: Sequence[str]) -> BatchResult:
        """Deletes many vectors."""
        return BatchResult.from_wire(
            self._c.vector_batch_delete(collection, list(keys), **self._scope)
        )
