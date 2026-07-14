"""``db.json`` — the JSON-document namespace.

Document ids are ``str``. Paths are JSONPath-lite (``$``, ``$.field``,
``$.arr[0]``); reads and writes default to the whole document (``$``).
"""

from __future__ import annotations

from typing import Any, Iterator, Optional, Sequence

from .._results import BatchResult, Page, Sample
from .base import PAGE_SIZE, Namespace


def _set_entries(entries: Any) -> list[dict]:
    if isinstance(entries, dict):
        return [{"key": k, "path": "$", "value": v} for k, v in entries.items()]
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append({"key": entry["key"], "path": entry.get("path", "$"), "value": entry["value"]})
        elif len(entry) == 3:
            key, path, value = entry
            out.append({"key": key, "path": path, "value": value})
        else:
            key, value = entry
            out.append({"key": key, "path": "$", "value": value})
    return out


def _kp_entries(entries: Any) -> list[dict]:
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append({"key": entry["key"], "path": entry.get("path", "$")})
        elif isinstance(entry, str):
            out.append({"key": entry, "path": "$"})
        else:
            key = entry[0]
            path = entry[1] if len(entry) > 1 else "$"
            out.append({"key": key, "path": path})
    return out


class JSONNamespace(Namespace):
    """JSON documents addressed by ``str`` id and JSONPath-lite path.

    Examples:
        >>> _ = db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
        >>> db.json.get("user:1", "$.name")
        'Ada'
        >>> db.json.get("user:1")
        {'name': 'Ada', 'roles': ['admin']}
        >>> db.json.exists("user:1")
        True
    """

    # --- single-record ---

    def set(self, key: str, path: str, value: Any) -> Any:
        """Sets ``value`` at ``path`` in document ``key``. Returns a write result.

        Examples:
            >>> _ = db.json.set("user:1", "$", {"name": "Ada"})
            >>> _ = db.json.set("user:1", "$.roles", ["admin"])   # patch a field
            >>> db.json.get("user:1")
            {'name': 'Ada', 'roles': ['admin']}
        """
        return self._c.json_set(key, path, value, **self._scope)

    def get(self, key: str, path: str = "$", *, as_of: Optional[int] = None) -> Any:
        """Returns the JSON value at ``path``, or ``None`` if absent.

        (``None`` is also returned for a stored JSON ``null``; use ``get_entry``
        with its ``found`` flag to distinguish the two.)

        Examples:
            >>> _ = db.json.set("user:1", "$", {"name": "Ada", "roles": ["admin"]})
            >>> db.json.get("user:1", "$.name")
            'Ada'
            >>> db.json.get("user:1")
            {'name': 'Ada', 'roles': ['admin']}
            >>> db.json.get("absent") is None
            True
        """
        found, value, _versioned = self._read(key, path, as_of)
        return value if found else None

    def get_entry(self, key: str, path: str = "$", *, as_of: Optional[int] = None) -> Any:
        """Returns the value with its commit metadata, or ``None`` if absent.

        Time-travel (``as_of``) reads carry no version metadata (the engine's
        raw-value envelope), so this returns the bare value in that case.
        """
        found, value, versioned = self._read(key, path, as_of)
        if not found:
            return None
        return versioned if versioned is not None else value

    def _read(self, key: str, path: str, as_of: Optional[int]) -> tuple:
        """Runs json_get, tolerating its two output shapes.

        json_get is the documented JSON exception: the latest read returns a
        versioned envelope (``json_versioned_value``), while an ``as_of`` read
        returns the raw document (``json_value`` / MaybeJsonValue). Returns
        ``(found, value, versioned_or_None)``.
        """
        cmd = {"type": "json_get", "key": key, "path": path}
        if as_of is not None:
            cmd["as_of"] = as_of
        if self._branch is not None:
            cmd["branch"] = self._branch
        if self._space is not None:
            cmd["space"] = self._space
        envelope = self._core.execute(cmd)
        data = envelope["data"]
        if not data.get("found"):
            return False, None, None
        value = data["value"]
        if envelope["type"] == "json_versioned_value":
            from .._generated import models

            versioned = models.JsonVersionedValue.from_wire(value)
            return True, versioned.value, versioned
        return True, value, None

    def delete(self, key: str, path: str = "$") -> Any:
        """Deletes ``path`` in document ``key`` (whole document by default)."""
        return self._c.json_delete(key, path, **self._scope)

    def exists(self, key: str) -> bool:
        """Whether the document currently exists."""
        return self._c.json_exists(key, **self._scope)

    def history(self, key: str) -> Optional[list]:
        """Full version history, or ``None`` if the document never existed."""
        result = self._c.json_history(key, **self._scope)
        return result.items if result is not None else None

    def count(self, prefix: Optional[str] = None, *, as_of: Optional[int] = None) -> int:
        """Number of documents, optionally under an id prefix."""
        return self._c.json_count(prefix=prefix, as_of=as_of, **self._scope)

    # --- listing / pagination ---

    def keys(
        self,
        prefix: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        cursor: Optional[Any] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """One page of document ids (``str`` each)."""
        return Page.from_wire(
            self._c.json_list(prefix=prefix, limit=limit, cursor=cursor, as_of=as_of, **self._scope)
        )

    def iter_keys(self, prefix: Optional[str] = None, *, as_of: Optional[int] = None) -> Iterator[str]:
        """Iterates every document id under ``prefix``, paginating internally."""
        cursor = None
        while True:
            page = self._c.json_list(
                prefix=prefix, limit=PAGE_SIZE, cursor=cursor, as_of=as_of, **self._scope
            )
            yield from page.items
            if not page.has_more:
                return
            cursor = page.cursor

    def sample(self, prefix: Optional[str] = None, *, count: Optional[int] = None) -> Sample:
        """A deterministic representative sample plus the total count."""
        return Sample.from_wire(self._c.json_sample(prefix=prefix, count=count, **self._scope))

    # --- batch ---

    def set_many(self, entries: Any) -> BatchResult:
        """Writes many documents. Accepts a dict, or list of (key, value)/(key, path, value)."""
        return BatchResult.from_wire(self._c.json_batch_set(_set_entries(entries), **self._scope))

    def get_many(self, entries: Any) -> list[Any]:
        """Reads many documents; returns the JSON value or ``None`` per entry, in order.

        Each entry is a document id, a ``(key, path)`` pair, or ``{"key", "path"}``.

        Examples:
            >>> _ = db.json.set("user:1", "$", {"name": "Ada"})
            >>> _ = db.json.set("user:2", "$", {"name": "Grace"})
            >>> db.json.get_many(["user:1", "user:2", "user:404"])
            [{'name': 'Ada'}, {'name': 'Grace'}, None]
        """
        result = self._c.json_batch_get(_kp_entries(entries), **self._scope)
        out: list[Any] = [None] * len(result.items)
        for item in result.items:
            payload = item.result
            if payload is not None and getattr(payload, "found", False):
                out[item.index] = payload.value
        return out

    def delete_many(self, entries: Any) -> BatchResult:
        """Deletes many documents/paths."""
        return BatchResult.from_wire(self._c.json_batch_delete(_kp_entries(entries), **self._scope))

    # --- indexes ---

    def create_index(self, name: str, field_path: str, *, index_type: str = "tag") -> Any:
        """Creates a secondary index over ``field_path``."""
        return self._c.json_index_create(name, field_path, index_type, **self._scope)

    def drop_index(self, name: str) -> Any:
        """Drops a secondary index."""
        return self._c.json_index_drop(name, **self._scope)

    def list_indexes(self) -> list:
        """Lists the defined secondary indexes."""
        return self._c.json_index_list(**self._scope).items
