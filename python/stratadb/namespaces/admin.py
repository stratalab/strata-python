"""``db.admin`` — database introspection and diagnostics."""

from __future__ import annotations

from typing import Any, Optional

from .base import Namespace


class AdminNamespace(Namespace):
    """Read-only database status, health, and configuration.

    Examples:
        >>> db.admin.ping()  # doctest: +ELLIPSIS
        AdminPing(version=...)
        >>> db.admin.info().durable
        False
    """

    def ping(self) -> Any:
        """A liveness check; returns the engine version.

        Examples:
            >>> isinstance(db.admin.ping().version, str)
            True
        """
        return self._c.admin_ping()

    def info(self) -> Any:
        """Database info: target, durability, branch/space counts, version, and
        the resolved storage memory budget.

        ``memory_budget`` reports what the database is sized to run on:
        ``total_bytes`` and a ``source`` of ``explicit`` (a budget you set via
        ``stratadb.open(path, memory_budget=...)``),
        ``derived_from_host`` (auto-derived at open — 25% of usable host
        memory, capped at 8 GiB — with ``usable_host_bytes`` showing what was
        detected), or ``fixed_default`` (the fallback when the host cannot be
        probed).

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

    def storage(self, *, audit: bool = False) -> Any:
        """What the database occupies on disk, and what the last reclaim did.

        Two tiers (engine 1.2.6). The default is the cheap one: live table
        objects and their bytes, the WAL's retained/active bytes and retention
        watermark, and ``.reclaim`` — the ledger of reclaim passes, including
        the last snapshot prune's outcome.

        ``audit=True`` adds the listing-backed facts, which cost a scan:
        unreferenced and quarantined objects, snapshots and the segments a
        prune would drop, the WAL's reclaimable-versus-tail split — and
        ``total_bytes``, the sum across every family. **``total_bytes`` is
        ``None`` without ``audit=True``**, since it cannot be known without
        that listing.

        Durable databases only: a ``cache=True`` database holds no durable
        objects and raises :class:`~stratadb.errors.UnsupportedError`
        (``unsupported.engine.persistence_capability``).

        Examples:
            >>> with stratadb.open(tmp_dir + "/store") as durable:
            ...     _ = durable.kv.put("k", "v")
            ...     durable.admin.storage().reclaim.total_passes >= 0
            True
            >>> with stratadb.open(tmp_dir + "/store") as durable:
            ...     durable.admin.storage(audit=True).total_bytes > 0
            True
        """
        return self._c.admin_storage(audit=audit)

    def describe(self, *, space: Optional[str] = None) -> Any:
        """A structured description of the database's capabilities and layout.

        ``space`` describes that space rather than the default one; engine
        1.2.4 made it honored, where it previously always reported ``default``.

        Examples:
            >>> db.admin.describe().default_branch
            'default'
        """
        return self._c.admin_describe(space=space)

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

    def ipc_status(self) -> Any:
        """This process's multi-process IPC state.

        Reports whether this handle owns the store (``is_owner``), whether it
        hosts a broker socket others can attach to (``hosting``, with
        ``socket_path`` and ``client_count``), and the owner's pid when known.
        Durable opens default to ``ipc="host"``; cache databases never broker.

        Examples:
            >>> db.admin.ipc_status().hosting
            False
        """
        return self._c.admin_ipc_status()

    def ipc_stop(self) -> Any:
        """Stop hosting the multi-process broker socket.

        The store stays open and usable in-process; it simply stops accepting
        new brokered clients. ``.stopped`` is ``True`` when a running host was
        stopped, ``False`` when this process was not hosting.

        Examples:
            >>> db.admin.ipc_stop().stopped
            False
        """
        return self._c.admin_ipc_stop()
