"""``db.admin`` — database introspection and diagnostics."""

from __future__ import annotations

from typing import Any

from .base import Namespace


class AdminNamespace(Namespace):
    """Read-only database status, health, and configuration.

    Examples:
        >>> db.admin.ping()  # doctest: +ELLIPSIS
        Record(version=...)
        >>> db.admin.info().durable
        False
    """

    def ping(self) -> Any:
        """A liveness check; returns the engine version.

        Examples:
            >>> db.admin.ping().version == stratadb.__version__
            True
        """
        return self._c.admin_ping()

    def info(self) -> Any:
        """Database info (target, durability, branch/space counts, version).

        Examples:
            >>> db.admin.info().branch_count
            1
        """
        return self._c.admin_info()

    def health(self) -> Any:
        """Control-plane health across the branch/space catalogs and registry.

        Examples:
            >>> db.admin.health().status.value
            'healthy'
        """
        return self._c.admin_health()

    def metrics(self) -> Any:
        """Operational metrics.

        Examples:
            >>> db.admin.metrics().branch_count
            1
        """
        return self._c.admin_metrics()

    def describe(self) -> Any:
        """A structured description of the database's capabilities and layout.

        Examples:
            >>> db.admin.describe().default_branch
            'default'
        """
        return self._c.admin_describe()

    def config(self) -> Any:
        """The effective open configuration.

        Examples:
            >>> db.admin.config().default_branch
            'default'
        """
        return self._c.admin_config()

    def config_value(self, key: str) -> Any:
        """One configuration value by key.

        Examples:
            >>> db.admin.config_value("missing") is None
            True
        """
        return self._c.admin_config_key(key)
