"""``db.branches`` — branch management (create, fork, delete).

Branches are database-global (not scoped to a branch/space), so these methods
ignore the namespace scope.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from ..errors import NotFoundError
from .base import Namespace


class BranchesNamespace(Namespace):
    """Named branches with copy-on-write forks and time-anchored history.

    A fresh database has one branch, ``default``. Each listed branch is a
    ``BranchItem`` exposing ``.name``, ``.generation``, ``.status``, ....

    Examples:
        >>> [b.name for b in db.branches.list()]
        ['default']
        >>> _ = db.branches.create("feature")
        >>> sorted(b.name for b in db.branches.list())
        ['default', 'feature']
        >>> "feature" in db.branches
        True
    """

    def list(self) -> list:
        """Lists the branches.

        Examples:
            >>> _ = db.branches.create("feature")
            >>> sorted(b.name for b in db.branches.list())
            ['default', 'feature']
        """
        return list(self._c.branch_list().items)

    def get(self, name: str) -> Any:
        """Returns a branch's info, or ``None`` if it does not exist.

        Examples:
            >>> _ = db.branches.create("feature")
            >>> db.branches.get("feature").name
            'feature'
        """
        try:
            return self._c.branch_get(name)
        except NotFoundError:
            return None

    def create(self, name: str) -> Any:
        """Creates an empty branch rooted at an empty state.

        Examples:
            >>> _ = db.branches.create("feature")
            >>> sorted(b.name for b in db.branches.list())
            ['default', 'feature']
        """
        return self._c.branch_create(name)

    def fork(
        self,
        source: str,
        name: str,
        *,
        version: Optional[int] = None,
        timestamp: Optional[int] = None,
    ) -> Any:
        """Forks ``name`` from ``source`` — at its current head, a version, or a timestamp.

        ``version`` and ``timestamp`` are mutually exclusive; omit both to fork
        from the source's current head.

        Examples:
            >>> _ = db.branches.fork("default", "experiment")
            >>> sorted(b.name for b in db.branches.list())
            ['default', 'experiment']
        """
        if version is not None and timestamp is not None:
            raise ValueError("fork accepts version or timestamp, not both")
        if version is not None:
            return self._c.branch_fork_at_version(source, name, version)
        if timestamp is not None:
            return self._c.branch_fork_at_timestamp(source, name, timestamp)
        return self._c.branch_fork(source, name)

    def delete(self, name: str) -> Any:
        """Deletes a branch.

        Examples:
            >>> _ = db.branches.create("temp")
            >>> _ = db.branches.delete("temp")
            >>> sorted(b.name for b in db.branches.list())
            ['default']
        """
        return self._c.branch_delete(name)

    def __contains__(self, name: str) -> bool:
        return self.get(name) is not None

    def __iter__(self) -> Iterator[str]:
        return iter(branch.name for branch in self._c.branch_list().items)
