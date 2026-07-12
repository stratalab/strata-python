"""Strata — an embedded multi-model database for AI agents.

Strata is embedded, not a server: ``stratadb.Strata("./app-data")`` opens a
durable database in-process (SQLite-shaped), and ``Strata(cache=True)`` opens a
volatile in-memory one. Six primitives — key-value, JSON, vectors, an event
log, and a graph — share one branch-aware, time-travelling storage substrate.

The SDK speaks the exact same command surface, value shapes, and error codes as
the ``strata`` CLI and MCP server. After install, run ``stratadb.agents_guide()``
(or ``strata agents guide``) for the full offline usage guide.

    import stratadb

    db = stratadb.Strata("./app-data")          # durable (creates if absent)
    db = stratadb.Strata(cache=True)            # ephemeral, in-memory
    with stratadb.Strata(cache=True) as db:
        db.execute({"type": "kv_put", "key": "aGk=", "value": "dGhlcmU="})
"""

from __future__ import annotations

import os
from typing import Any

from . import _stratadb  # native extension
from . import errors, filters
from ._core import Core
from .errors import InvalidArgumentError, UnsupportedError, client_error

__version__: str = _stratadb.version()

# Reuse the shared D2 targeting contract's registered code and class.
_NO_DB_CODE = "invalid_argument.cli.no_database"
_NO_DB_HINT = (
    "pass a path (stratadb.Strata('./mydb')), set STRATA_DB "
    "(stratadb.Strata.from_env()), or use cache=True for ephemeral"
)


def agents_guide() -> str:
    """The complete offline agent usage guide, embedded in the wheel.

    Byte-identical to ``strata agents guide`` for the same version.
    """
    return _stratadb.agents_guide()


def mcp_config(db_path: str | os.PathLike[str]) -> dict[str, Any]:
    """The MCP client-config snippet that serves ``db_path`` over stdio."""
    return {"command": "strata", "args": [str(db_path), "mcp", "serve"]}


class Strata:
    """An open Strata database.

    Args:
        path: Filesystem path to a durable database (created if absent).
            Omit only with ``cache=True``.
        cache: Open a volatile in-memory database instead. Nothing persists.
        branch: Session default branch for commands that omit their own.
        space: Session default product space for commands that omit their own.

    Raises:
        InvalidArgumentError: When neither ``path`` nor ``cache=True`` is given
            (the D2 targeting contract — Strata never opens the cwd implicitly).
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        cache: bool = False,
        branch: str | None = None,
        space: str | None = None,
    ):
        if cache:
            self._core = Core.open_cache()
        elif path is not None:
            self._core = Core.open_durable(str(path))
        else:
            raise client_error(
                InvalidArgumentError, _NO_DB_CODE, "no database specified", _NO_DB_HINT
            )
        self._closed = False
        if branch is not None or space is not None:
            self._core.set_scope(branch, space)

    @classmethod
    def from_env(cls, *, branch: str | None = None, space: str | None = None) -> "Strata":
        """Opens the database named by the ``STRATA_DB`` environment variable.

        Mirrors the CLI's D2 targeting contract exactly.
        """
        path = os.environ.get("STRATA_DB")
        if not path:
            raise client_error(
                InvalidArgumentError, _NO_DB_CODE, "STRATA_DB is not set", _NO_DB_HINT
            )
        return cls(path, branch=branch, space=space)

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        """Runs one raw command on the wire, returning its output envelope.

        The permanent escape hatch to the full command surface::

            db.execute({"type": "kv_scan", "limit": 10})
            # -> {"type": "kv_scan_result", "data": {...}}

        Raises the typed :class:`~stratadb.errors.StrataError` on a domain
        failure.
        """
        return self._core.execute(command)

    @property
    def version(self) -> str:
        """The engine/SDK version this database is running."""
        return __version__

    @property
    def branch(self) -> str:
        """The session default branch."""
        return self._core.default_branch

    @property
    def space(self) -> str:
        """The session default product space."""
        return self._core.default_space

    @property
    def state(self) -> Any:
        """Removed in V1. Raises a teaching :class:`UnsupportedError`."""
        raise client_error(
            UnsupportedError,
            "unsupported.sdk.state_removed",
            "the state-cell primitive (db.state) was removed in V1",
            "use db.kv for keyed values, or db.json for structured documents",
        )

    def close(self) -> None:
        """Closes the database. Idempotent."""
        if not self._closed:
            self._core.close()
            self._closed = True

    def __enter__(self) -> "Strata":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        self.close()
        return False


__all__ = [
    "Strata",
    "errors",
    "filters",
    "agents_guide",
    "mcp_config",
    "__version__",
]
