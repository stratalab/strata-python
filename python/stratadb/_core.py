"""The thin core over the native binding.

One :class:`Core` wraps one ``_stratadb.Handle`` and speaks the executor's
serialized command wire: a command ``dict`` in, an output ``dict`` out, with
domain failures raised as the typed :mod:`stratadb.errors` hierarchy. This is
the single canonical path every namespace method funnels through.
"""

from __future__ import annotations

import json
from typing import Any

from . import _stratadb  # native extension
from .errors import error_from_payload

_NativeError = _stratadb.StrataNativeError


class Core:
    """A single open database, over the native handle."""

    __slots__ = ("_handle",)

    def __init__(self, handle: Any):
        self._handle = handle

    @classmethod
    def open_durable(cls, path: str) -> "Core":
        return cls(_stratadb.Handle.open_durable(path))

    @classmethod
    def open_cache(cls) -> "Core":
        return cls(_stratadb.Handle.open_cache())

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        """Runs one command, returning its ``{"type", "data"}`` output envelope.

        Raises the typed :class:`~stratadb.errors.StrataError` on a domain
        failure, and ``ValueError`` when the command is not a valid command
        object.
        """
        try:
            raw = self._handle.execute(json.dumps(command))
        except _NativeError as exc:
            raise error_from_payload(exc.args[0] if exc.args else "{}") from None
        return json.loads(raw)

    def data(self, command: dict[str, Any]) -> Any:
        """Runs one command and returns just the ``data`` payload of its output."""
        return self.execute(command).get("data")

    def set_scope(self, branch: str | None = None, space: str | None = None) -> None:
        self._handle.set_scope(branch, space)

    @property
    def default_branch(self) -> str:
        return self._handle.default_branch()

    @property
    def default_space(self) -> str:
        return self._handle.default_space()

    def close(self) -> None:
        self._handle.close()
