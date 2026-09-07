"""Shared namespace machinery."""

from __future__ import annotations

from typing import Any, Callable

from .._results import Page
from ..clock import TimeLike, to_micros
from ..errors import InvalidArgumentError, client_error

# Page size used when auto-paginating a listing that was called without an
# explicit ``limit``.
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

    def _temporal(self, as_of: Any, as_of_time: Any) -> dict[str, Any]:
        """The time-travel arguments for one call, as wire kwargs.

        Keeps Strata's two clocks apart (see :mod:`stratadb.clock`): ``as_of``
        is a position on the logical commit timeline (an int), ``as_of_time`` a
        wall-clock instant, coerced here from a ``datetime``/``date``/ISO
        string. A ``datetime`` handed to ``as_of`` is the confusing mistake
        worth naming, so it is rejected with a pointer rather than a serde
        failure. Supplying both is the engine's call to refuse
        (``invalid_argument.executor.as_of_conflict``), so both go on the wire.
        """
        if as_of is not None and (not isinstance(as_of, int) or isinstance(as_of, bool)):
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.as_of_kind",
                f"as_of takes a commit timestamp (an int), got {type(as_of).__name__}",
                "as_of is a position on the commit timeline, not a date — pass "
                "as_of_time= for a wall-clock instant",
            )
        return {"as_of": as_of, "as_of_time": to_micros(as_of_time)}

    def _check_limit(self, limit: Any) -> None:
        """Rejects a non-positive ``limit`` (#41).

        ``limit=0`` used to return an empty page reporting ``has_more=False``,
        so a ``while has_more`` loop exited at once over a non-empty store.
        """
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.limit",
                f"limit must be a positive integer, got {limit!r}",
                "omit limit to page through everything, or pass a value >= 1",
            )

    def _listing(
        self,
        fetch_page: Callable[[Any, "int | None"], Any],
        *,
        limit: Any,
        start: Any = None,
    ) -> Page:
        """Builds a :class:`Page` from ``fetch_page(cursor, limit) -> wire record``.

        With an explicit ``limit`` returns a single bounded page. Without one,
        the returned page auto-paginates ``PAGE_SIZE`` at a time from ``start``
        (the initial cursor/seek), so ``for x in db.kv.keys()`` walks the whole
        store instead of silently stopping at the first page (#40).
        """
        self._check_limit(limit)
        if limit is not None:
            return Page.from_wire(fetch_page(start, limit))

        def fetch(cursor: Any) -> Page:
            return Page.from_wire(fetch_page(cursor, PAGE_SIZE), fetch)

        return fetch(start)
