"""Shared namespace machinery."""

from __future__ import annotations

from typing import Any

# Internal page size for ``iter_*`` auto-pagination.
PAGE_SIZE = 256


class Namespace:
    """Base for a capability namespace bound to a command core and a scope.

    ``branch``/``space`` are the scope injected into every call (both ``None``
    on the base handle, meaning "use the session default"); ``db.at(...)``
    creates a namespace with an overriding scope.
    """

    __slots__ = ("_c", "_core", "_branch", "_space")

    def __init__(
        self,
        commands: Any,
        core: Any,
        branch: str | None = None,
        space: str | None = None,
    ):
        self._c = commands
        self._core = core  # for the few reads that must interpret the raw envelope
        self._branch = branch
        self._space = space

    @property
    def _scope(self) -> dict[str, Any]:
        return {"branch": self._branch, "space": self._space}
