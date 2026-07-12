"""``db.arrow`` — Apache Arrow / Parquet import and export."""

from __future__ import annotations

from typing import Any, Optional

from .base import Namespace


class ArrowNamespace(Namespace):
    """Bulk import/export of a primitive's rows via Arrow-backed files."""

    def import_(
        self,
        target: str,
        path: str,
        *,
        format: Optional[str] = None,
        collection: Optional[str] = None,
        key_column: Optional[str] = None,
        value_column: Optional[str] = None,
    ) -> Any:
        """Imports rows from ``path`` into ``target`` (e.g. ``"kv"``, ``"vector"``)."""
        return self._c.arrow_import(
            path,
            target,
            format=format,
            collection=collection,
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
        """Exports a primitive's rows to ``path`` (Parquet by default)."""
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
