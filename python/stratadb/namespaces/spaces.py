"""``db.spaces`` — product-space management."""

from __future__ import annotations

from typing import Any, Iterator

from .base import Namespace


class SpacesNamespace(Namespace):
    """Named product spaces (isolated namespaces within a branch)."""

    def list(self) -> list:
        """Lists the spaces."""
        return list(self._c.space_list(branch=self._branch).items)

    def create(self, name: str) -> Any:
        """Creates a space."""
        return self._c.space_create(name, branch=self._branch)

    def exists(self, name: str) -> bool:
        """Whether the space exists."""
        return self._c.space_exists(name, branch=self._branch)

    def delete(self, name: str, *, force: bool = False) -> Any:
        """Deletes a space. Refuses a non-empty space unless ``force=True``."""
        return self._c.space_delete(name, force=force, branch=self._branch)

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._c.space_list(branch=self._branch).items)
