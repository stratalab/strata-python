"""``db.arrow`` — Apache Arrow / Parquet import and export."""

from __future__ import annotations

from typing import Any, Optional

from .base import Namespace


class ArrowNamespace(Namespace):
    """Bulk import/export of a primitive's rows via Arrow-backed files.

    Export writes one file per primitive (Parquet by default); import reads it
    back into a primitive. Both take a filesystem path.

    Examples:
        >>> _ = db.kv.put("greeting", "hello")
        >>> _ = db.arrow.export("kv", tmp_dir + "/kv.parquet")
        >>> _ = db.arrow.import_("kv", tmp_dir + "/kv.parquet")
        >>> db.kv.get("greeting")
        b'hello'
    """

    def import_(
        self,
        target: str,
        path: str,
        *,
        format: Optional[str] = None,
        collection: Optional[str] = None,
        graph: Optional[str] = None,
        key_column: Optional[str] = None,
        value_column: Optional[str] = None,
    ) -> Any:
        """Imports rows from ``path`` into ``target``.

        ``target`` is one of ``"kv"``, ``"json"``, ``"vector"``, ``"graph"``, or
        ``"event"``. Vector imports take ``collection=`` (the target collection);
        graph imports take ``graph=`` (the target graph). Event imports re-derive
        the log from the file's payload/type columns, so each appended event is
        assigned a fresh sequence, timestamp, and hash.

        Examples:
            >>> _ = db.kv.put("greeting", "hello")
            >>> _ = db.arrow.export("kv", tmp_dir + "/kv.parquet", format="parquet")
            >>> _ = db.kv.delete("greeting")
            >>> _ = db.arrow.import_("kv", tmp_dir + "/kv.parquet")  # Rows are keyed by their source column; kv restores greeting=hello.
            >>> db.kv.get("greeting")
            b'hello'
        """
        return self._c.arrow_import(
            path,
            target,
            format=format,
            collection=collection,
            graph=graph,
            key_column=key_column,
            value_column=value_column,
            **self._scope,
        )

    def export(
        self,
        primitive: str,
        path: str,
        *,
        format: str = "parquet",
        collection: Optional[str] = None,
        event_type: Optional[str] = None,
        graph: Optional[str] = None,
        limit: Optional[int] = None,
        prefix: Optional[str] = None,
    ) -> Any:
        """Exports a primitive's rows to ``path`` (Parquet by default).

        Examples:
            >>> _ = db.kv.put("greeting", "hello")
            >>> _ = db.arrow.export("kv", tmp_dir + "/kv.parquet", format="parquet")  # One file per primitive; Parquet by default.
            >>> _ = db.kv.delete("greeting")
            >>> _ = db.arrow.import_("kv", tmp_dir + "/kv.parquet")
            >>> db.kv.get("greeting")
            b'hello'
        """
        return self._c.arrow_export(
            primitive,
            format,
            path,
            collection=collection,
            event_type=event_type,
            graph=graph,
            limit=limit,
            prefix=prefix,
            **self._scope,
        )
