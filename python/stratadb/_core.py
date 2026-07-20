"""The thin core over the native binding.

One :class:`Core` wraps one ``_stratadb.Handle`` and speaks the executor's
serialized command wire: a command ``dict`` in, an output ``dict`` out, with
domain failures raised as the typed :mod:`stratadb.errors` hierarchy. This is
the single canonical path every namespace method funnels through.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import _stratadb  # native extension
from .errors import (
    FailedPreconditionError,
    InvalidArgumentError,
    client_error,
    error_from_payload,
)

_NativeError = _stratadb.StrataNativeError

_BAD_COMMAND_CODE = "invalid_argument.sdk.command"
_FORK_CODE = "failed_precondition.sdk.fork_not_supported"
_FORK_HINT = (
    "open a fresh Strata handle after os.fork(); a database handle must not be "
    "shared across a fork() (Python itself warns fork() with threads is unsafe)"
)


class Core:
    """A single open database, over the native handle."""

    __slots__ = ("_handle", "_pid")

    def __init__(self, handle: Any):
        self._handle = handle
        # Record the owning process so we can reject use from a forked child,
        # where the inherited handle acknowledges writes that never persist
        # (issue #32). fork() with the engine's threads is unsafe by POSIX rules.
        self._pid = os.getpid()

    def _forked(self) -> bool:
        return os.getpid() != self._pid

    def _guard(self) -> None:
        if self._forked():
            raise client_error(
                FailedPreconditionError,
                _FORK_CODE,
                "database handle used in a forked child process",
                _FORK_HINT,
            )

    @classmethod
    def open_durable(cls, path: str) -> "Core":
        try:
            return cls(_stratadb.Handle.open_durable(path))
        except _NativeError as exc:
            raise error_from_payload(exc.args[0] if exc.args else "{}") from None

    @classmethod
    def open_cache(cls) -> "Core":
        try:
            return cls(_stratadb.Handle.open_cache())
        except _NativeError as exc:
            raise error_from_payload(exc.args[0] if exc.args else "{}") from None

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        """Runs one command, returning its ``{"type", "data"}`` output envelope.

        Raises the typed :class:`~stratadb.errors.StrataError` hierarchy: a
        domain failure carries the engine's ``code``; invalid input — an unknown
        command, an out-of-range or wrong-typed argument, or an unserializable
        payload — raises :class:`~stratadb.errors.InvalidArgumentError`
        (``invalid_argument.sdk.command``).
        """
        self._guard()
        try:
            raw = self._handle.execute(json.dumps(command))
        except _NativeError as exc:
            raise error_from_payload(exc.args[0] if exc.args else "{}") from None
        except (TypeError, ValueError) as exc:
            # Our-side encode failure (e.g. a bytes/NaN payload) or the binding's
            # ValueError for a serde-rejected command/argument. Surface a typed
            # error instead of leaking a bare TypeError/ValueError.
            raise client_error(InvalidArgumentError, _BAD_COMMAND_CODE, str(exc)) from exc
        # json.loads stays OUTSIDE the try: a decode failure here is a corrupt
        # engine envelope, not caller input, and must not be mistyped.
        return json.loads(raw)

    def data(self, command: dict[str, Any]) -> Any:
        """Runs one command and returns just the ``data`` payload of its output."""
        return self.execute(command).get("data")

    def set_scope(self, branch: str | None = None, space: str | None = None) -> None:
        self._guard()
        self._handle.set_scope(branch, space)

    @property
    def default_branch(self) -> str:
        self._guard()
        return self._handle.default_branch()

    @property
    def default_space(self) -> str:
        self._guard()
        return self._handle.default_space()

    def close(self) -> None:
        # In a forked child the handle's fds/mmaps are shared with the parent;
        # running the engine's teardown here could flush or truncate the
        # parent's files. Skip the native close in a child — the parent still
        # owns and will close it. Idempotent; never raises.
        if not self._forked():
            self._handle.close()
