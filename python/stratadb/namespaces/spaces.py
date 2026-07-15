"""``db.spaces`` — product-space management."""

from __future__ import annotations

from typing import Any, Iterator

from .base import Namespace


class SpacesNamespace(Namespace):
    """Named product spaces (isolated namespaces within a branch).

    A fresh database has one space, ``default``.

    Examples:
        >>> db.spaces.list()
        ['default']
        >>> _ = db.spaces.create("analytics")
        >>> sorted(db.spaces.list())
        ['analytics', 'default']
        >>> db.spaces.exists("analytics")
        True
    """

    def list(self) -> list:
        """Lists the spaces.

        Examples:
            >>> _ = db.spaces.create("app")
            >>> sorted(db.spaces.list())
            ['app', 'default']
        """
        return list(self._c.space_list(branch=self._branch).items)

    def create(self, name: str) -> Any:
        """Creates a space.

        Examples:
            >>> _ = db.spaces.create("app")
            >>> sorted(db.spaces.list())
            ['app', 'default']
        """
        return self._c.space_create(name, branch=self._branch)

    def exists(self, name: str) -> bool:
        """Whether the space exists.

        Examples:
            >>> _ = db.spaces.create("app")
            >>> db.spaces.exists("app")
            True
            >>> db.spaces.exists("nope")
            False
        """
        return self._c.space_exists(name, branch=self._branch)

    def delete(self, name: str, *, force: bool = False) -> Any:
        """Deletes a space. Refuses a non-empty space unless ``force=True``.

        Examples:
            >>> _ = db.spaces.create("temp")
            >>> _ = db.spaces.delete("temp")
            >>> db.spaces.exists("temp")
            False
        """
        return self._c.space_delete(name, force=force, branch=self._branch)

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._c.space_list(branch=self._branch).items)
