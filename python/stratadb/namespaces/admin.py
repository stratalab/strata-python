"""``db.admin`` — database introspection and diagnostics."""

from __future__ import annotations

from typing import Any

from .base import Namespace


class AdminNamespace(Namespace):
    """Read-only database status, health, and configuration."""

    def ping(self) -> Any:
        """A liveness check; returns the engine version."""
        return self._c.admin_ping()

    def info(self) -> Any:
        """Database info (target, durability, branch/space counts, version)."""
        return self._c.admin_info()

    def health(self) -> Any:
        """Control-plane health across the branch/space catalogs and registry."""
        return self._c.admin_health()

    def metrics(self) -> Any:
        """Operational metrics."""
        return self._c.admin_metrics()

    def describe(self) -> Any:
        """A structured description of the database's capabilities and layout."""
        return self._c.admin_describe()

    def config(self) -> Any:
        """The effective open configuration."""
        return self._c.admin_config()

    def config_value(self, key: str) -> Any:
        """One configuration value by key."""
        return self._c.admin_config_key(key)
