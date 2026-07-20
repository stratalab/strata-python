"""``db.vectors`` — the vector namespace (collections, upserts, similarity search)."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from .. import filters as _filters
from .._results import BatchResult, Page
from ..errors import require_field
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
            row = {"key": require_field(entry, "key"), "vector": list(require_field(entry, "vector"))}
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
    """Vector collections with metadata-filtered similarity search.

    Examples:
        >>> _ = db.vectors.create_collection("notes", 3)
        >>> _ = db.vectors.upsert("notes", "n1", [0.1, 0.2, 0.3])
        >>> _ = db.vectors.upsert("notes", "n2", [0.9, 0.8, 0.7])
        >>> [hit.key for hit in db.vectors.query("notes", [0.1, 0.2, 0.3], k=2)]
        ['n1', 'n2']
        >>> db.vectors.count("notes")
        2
    """

    # --- collections ---

    def create_collection(self, name: str, dimension: int, *, metric: str = "cosine") -> Any:
        """Creates a collection of ``dimension``-d vectors under ``metric``.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> db.vectors.stats("docs").dimension
            3
        """
        return self._c.vector_collection_create(name, dimension, metric, **self._scope)

    def delete_collection(self, name: str) -> Any:
        """Deletes a collection and all its vectors.

        Examples:
            >>> _ = db.vectors.create_collection("temp", 3, metric="cosine")
            >>> _ = db.vectors.delete_collection("temp")
            >>> [c.name for c in db.vectors.list_collections()]
            []
        """
        return self._c.vector_collection_delete(name, **self._scope)

    def list_collections(self) -> Page:
        """Lists the collections.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> [c.name for c in db.vectors.list_collections()]
            ['docs']
        """
        return Page.from_wire(self._c.vector_collection_list(**self._scope))

    def stats(self, name: str) -> Any:
        """Returns a collection's info (dimension, metric, count), or ``None``.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> db.vectors.stats("docs").dimension
            3
        """
        page = self._c.vector_collection_stats(name, **self._scope)
        for info in page.items:
            if info.name == name:
                return info
        return page.items[0] if page.items else None

    def count(self, name: str, *, as_of: Optional[int] = None) -> int:
        """Number of vectors in a collection.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.upsert("docs", "b", [0.0, 1.0, 0.0])
            >>> db.vectors.count("docs")
            2
        """
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
        """Inserts or replaces a vector (with optional metadata).

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0], metadata={"tag": "x"})
            >>> db.vectors.exists("docs", "a")
            True
        """
        return self._c.vector_upsert(collection, key, list(vector), metadata=metadata, **self._scope)

    def get(self, collection: str, key: str, *, as_of: Optional[int] = None) -> Any:
        """Returns the stored vector + metadata, or ``None`` if absent.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> db.vectors.get("docs", "a").key
            'a'
            >>> db.vectors.get("docs", "absent") is None
            True
        """
        result = self._c.vector_get(collection, key, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def history(self, collection: str, key: str) -> Optional[list]:
        """Full version history for a key, or ``None`` if it never existed.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> db.vectors.history("docs", "absent") is None
            True
        """
        result = self._c.vector_history(collection, key, **self._scope)
        return result.items if result is not None else None

    def exists(self, collection: str, key: str) -> bool:
        """Whether the key currently has a visible vector.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> db.vectors.exists("docs", "a")
            True
            >>> db.vectors.exists("docs", "absent")
            False
        """
        return self._c.vector_exists(collection, key, **self._scope)

    def keys(
        self,
        collection: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """One page of keys in a collection (``str`` each).

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.upsert("docs", "b", [0.0, 1.0, 0.0])
            >>> db.vectors.keys("docs").items
            ['a', 'b']
        """
        return Page.from_wire(
            self._c.vector_keys(collection, limit=limit, cursor=cursor, as_of=as_of, **self._scope)
        )

    def update_metadata(self, collection: str, key: str, metadata: dict) -> Any:
        """Patches the metadata of an existing vector.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0], metadata={"tag": "x"})
            >>> _ = db.vectors.update_metadata("docs", "a", {"tag": "z"})
            >>> db.vectors.get("docs", "a").data.metadata
            {'tag': 'z'}
        """
        return self._c.vector_metadata_update(collection, key, metadata, **self._scope)

    def delete(self, collection: str, key: str) -> Any:
        """Deletes one vector.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.delete("docs", "a")
            >>> db.vectors.exists("docs", "a")
            False
        """
        return self._c.vector_delete(collection, key, **self._scope)

    def delete_all(self, collection: str) -> Any:
        """Deletes every vector in a collection.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.delete_all("docs")
            >>> db.vectors.count("docs")
            0
        """
        return self._c.vector_delete_all(collection, **self._scope)

    def delete_by_filter(self, collection: str, filter: Any) -> Any:
        """Deletes every vector whose metadata matches ``filter``.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0], metadata={"tag": "keep"})
            >>> _ = db.vectors.upsert("docs", "b", [0.0, 1.0, 0.0], metadata={"tag": "drop"})
            >>> _ = db.vectors.delete_by_filter("docs", stratadb.filters.eq("tag", "drop"))
            >>> db.vectors.count("docs")
            1
        """
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
        """Returns the ``k`` nearest matches, optionally metadata-filtered.

        Each match exposes ``.key``, ``.score``, and ``.metadata``.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.upsert("docs", "b", [0.0, 1.0, 0.0])
            >>> [m.key for m in db.vectors.query("docs", [1.0, 0.0, 0.0], k=2)]
            ['a', 'b']
        """
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
        """Like ``query`` but also returns index diagnostics: ``(matches, diagnostics)``.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert("docs", "a", [1.0, 0.0, 0.0])
            >>> _ = db.vectors.upsert("docs", "b", [0.0, 1.0, 0.0])
            >>> [m.key for m in db.vectors.index_query("docs", [1.0, 0.0, 0.0], k=2)[0]]
            ['a', 'b']
        """
        result = self._c.vector_index_query(
            collection, list(vector), k, filter=_filter_wire(filter), as_of=as_of, **self._scope
        )
        return result.matches, result.diagnostics

    # --- batch ---

    def upsert_many(self, collection: str, entries: Any) -> BatchResult:
        """Upserts many vectors. Each entry is (key, vector[, metadata]) or a dict.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert_many("docs", [{"key": "a", "vector": [1.0, 0.0, 0.0]}, {"key": "b", "vector": [0.0, 1.0, 0.0]}])
            >>> db.vectors.count("docs")
            2
        """
        return BatchResult.from_wire(
            self._c.vector_batch_upsert(collection, _vector_entries(entries), **self._scope)
        )

    def get_many(self, collection: str, keys: Sequence[str]) -> BatchResult:
        """Reads many vectors positionally.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert_many("docs", [{"key": "a", "vector": [1.0, 0.0, 0.0]}, {"key": "b", "vector": [0.0, 1.0, 0.0]}])
            >>> [i.result.value.key for i in db.vectors.get_many("docs", ["a", "b"]).items]
            ['a', 'b']
        """
        return BatchResult.from_wire(
            self._c.vector_batch_get(collection, list(keys), **self._scope)
        )

    def delete_many(self, collection: str, keys: Sequence[str]) -> BatchResult:
        """Deletes many vectors.

        Examples:
            >>> _ = db.vectors.create_collection("docs", 3, metric="cosine")
            >>> _ = db.vectors.upsert_many("docs", [{"key": "a", "vector": [1.0, 0.0, 0.0]}, {"key": "b", "vector": [0.0, 1.0, 0.0]}])
            >>> _ = db.vectors.delete_many("docs", ["a", "b"])
            >>> db.vectors.count("docs")
            0
        """
        return BatchResult.from_wire(
            self._c.vector_batch_delete(collection, list(keys), **self._scope)
        )
