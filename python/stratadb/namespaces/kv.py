"""``db.kv`` — the key-value namespace."""

from __future__ import annotations

from typing import Any, Iterator, Optional, Sequence

from .._results import BatchResult, Page, Sample
from .base import PAGE_SIZE, Namespace


def _kv_entries(entries: Any) -> list[dict]:
    """Normalizes a dict / list-of-(k, v) / list-of-dict into wire entries."""
    if isinstance(entries, dict):
        return [{"key": k, "value": v} for k, v in entries.items()]
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append({"key": entry["key"], "value": entry["value"]})
        else:
            key, value = entry
            out.append({"key": key, "value": value})
    return out


class KVNamespace(Namespace):
    """Binary key-value storage. Keys and values accept ``str`` (UTF-8) or ``bytes``.

    Examples:
        >>> _ = db.kv.put("greeting", "hello")
        >>> db.kv.get("greeting")
        b'hello'
        >>> db.kv.exists("greeting")
        True
        >>> _ = db.kv.put_many({"a": "1", "b": "2"})
        >>> db.kv.get_many(["a", "b", "missing"])
        [b'1', b'2', None]
    """

    # --- single-record ---

    def put(self, key: str | bytes, value: str | bytes) -> Any:
        """Stores or replaces a value. Returns a write result (receipt + effect).

        Examples:
            >>> _ = db.kv.put("setting", "v1")
            >>> _ = db.kv.put("setting", "v2")  # replaces the visible value
            >>> db.kv.get("setting")
            b'v2'
        """
        return self._c.kv_put(key, value, **self._scope)

    def get(self, key: str | bytes, *, as_of: Optional[int] = None) -> Optional[bytes]:
        """Returns the value bytes, or ``None`` if absent.

        Pass ``as_of`` (a commit timestamp) to read a historical value.

        Examples:
            >>> _ = db.kv.put("greeting", "hello")
            >>> db.kv.get("greeting")
            b'hello'
            >>> db.kv.get("absent") is None
            True
        """
        result = self._c.kv_get(key, as_of=as_of, **self._scope)
        return result.value.value if result.found else None

    def get_entry(self, key: str | bytes, *, as_of: Optional[int] = None) -> Any:
        """Returns the value with its commit metadata (version, timestamp), or ``None``."""
        result = self._c.kv_get(key, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def delete(self, key: str | bytes) -> Any:
        """Deletes a key. Returns a write result.

        Examples:
            >>> _ = db.kv.put("temp", "scratch")
            >>> _ = db.kv.delete("temp")
            >>> db.kv.exists("temp")
            False
        """
        return self._c.kv_delete(key, **self._scope)

    def exists(self, key: str | bytes) -> bool:
        """Whether the key currently has a visible value.

        Examples:
            >>> _ = db.kv.put("k", "v")
            >>> db.kv.exists("k")
            True
            >>> db.kv.exists("absent")
            False
        """
        return self._c.kv_exists(key, **self._scope)

    def history(self, key: str | bytes) -> Optional[list]:
        """Full version history (tombstones included), or ``None`` if the key never existed."""
        result = self._c.kv_history(key, **self._scope)
        return result.items if result is not None else None

    def count(self, prefix: Optional[str | bytes] = None, *, as_of: Optional[int] = None) -> int:
        """Number of visible keys, optionally under a prefix.

        Examples:
            >>> _ = db.kv.put("a", "1")
            >>> _ = db.kv.put("b", "2")
            >>> db.kv.count()
            2
        """
        return self._c.kv_count(prefix=prefix, as_of=as_of, **self._scope)

    # --- listing / pagination ---

    def keys(
        self,
        prefix: Optional[str | bytes] = None,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """One page of keys under ``prefix`` (``bytes`` each)."""
        return Page.from_wire(
            self._c.kv_list(prefix=prefix, limit=limit, cursor=cursor, as_of=as_of, **self._scope)
        )

    def iter_keys(
        self, prefix: Optional[str | bytes] = None, *, as_of: Optional[int] = None
    ) -> Iterator[bytes]:
        """Iterates every key under ``prefix``, paginating internally."""
        cursor = None
        while True:
            page = self._c.kv_list(
                prefix=prefix, limit=PAGE_SIZE, cursor=cursor, as_of=as_of, **self._scope
            )
            yield from page.items
            if not page.has_more:
                return
            cursor = page.cursor

    def scan(
        self,
        start: Optional[str | bytes] = None,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
    ) -> Page:
        """One page of full rows (key + value + version) from ``start``/``cursor``."""
        begin = cursor if cursor is not None else start
        return Page.from_wire(self._c.kv_scan(start=begin, limit=limit, **self._scope))

    def iter_rows(self, start: Optional[str | bytes] = None) -> Iterator[Any]:
        """Iterates every row from ``start``, paginating internally."""
        begin = start
        while True:
            page = self._c.kv_scan(start=begin, limit=PAGE_SIZE, **self._scope)
            yield from page.items
            if not page.has_more:
                return
            begin = page.cursor

    def sample(self, prefix: Optional[str | bytes] = None, *, count: Optional[int] = None) -> Sample:
        """A deterministic representative sample plus the total count."""
        return Sample.from_wire(self._c.kv_sample(prefix=prefix, count=count, **self._scope))

    # --- batch ---

    def put_many(self, entries: Any) -> BatchResult:
        """Writes many entries in one commit. Accepts a dict or a list of (key, value)."""
        return BatchResult.from_wire(self._c.kv_batch_put(_kv_entries(entries), **self._scope))

    def get_many(self, keys: Sequence[str | bytes]) -> list[Optional[bytes]]:
        """Reads many keys; returns value bytes or ``None`` per key, in order.

        Examples:
            >>> _ = db.kv.put_many({"a": "1", "b": "2"})
            >>> db.kv.get_many(["a", "b", "missing"])
            [b'1', b'2', None]
        """
        result = self._c.kv_batch_get(list(keys), **self._scope)
        out: list[Optional[bytes]] = [None] * len(result.items)
        for item in result.items:
            out[item.index] = (
                item.result.value if item.result is not None and item.result.found else None
            )
        return out

    def delete_many(self, keys: Sequence[str | bytes]) -> BatchResult:
        """Deletes many keys in one commit."""
        return BatchResult.from_wire(self._c.kv_batch_delete(list(keys), **self._scope))

    def exists_many(self, keys: Sequence[str | bytes]) -> list[bool]:
        """Presence of many keys, in order."""
        result = self._c.kv_batch_exists(list(keys), **self._scope)
        out: list[bool] = [False] * len(result.items)
        for item in result.items:
            out[item.index] = bool(item.result.exists) if item.result is not None else False
        return out
