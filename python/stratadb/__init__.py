"""Strata — an embedded multi-model database for AI agents.

Strata is embedded, not a server: ``stratadb.open("./app-data")`` opens a
durable database in-process (SQLite-shaped), and ``stratadb.open(cache=True)``
opens a volatile in-memory one. Six primitives — key-value, JSON, vectors, an
event log, and a graph — share one branch-aware, time-travelling storage
substrate.

The SDK speaks the exact same command surface, value shapes, and error codes as
the ``strata`` CLI and MCP server. **For agents: call ``stratadb.agents_guide()``
for the complete offline Python usage guide** (every namespace, ``db.ai``,
keys, branches/time-travel, errors — all runnable Python).

    import stratadb

    db = stratadb.open("./app-data")            # durable (creates if absent)
    db = stratadb.open(cache=True)              # ephemeral, in-memory
    with stratadb.open(cache=True) as db:
        db.execute({"type": "kv_put", "key": "aGk=", "value": "dGhlcmU="})

``open()`` returns a :class:`Strata` handle (the class is public for typing,
the way ``gzip.open`` returns a public ``GzipFile``).
"""

from __future__ import annotations

import os
from typing import Any

from . import _stratadb  # native extension
from . import errors, filters
from ._core import Core
from ._generated import Commands
from .errors import InvalidArgumentError, UnsupportedError, client_error
from .namespaces.kv import KVNamespace
from .namespaces.json import JSONNamespace
from .namespaces.vectors import VectorsNamespace
from .namespaces.events import EventsNamespace
from .namespaces.graphs import GraphsNamespace
from .namespaces.branches import BranchesNamespace
from .namespaces.spaces import SpacesNamespace
from .namespaces.admin import AdminNamespace
from .namespaces.arrow import ArrowNamespace
from .namespaces.ai import AiNamespace

__version__: str = _stratadb.version()

# Reuse the shared D2 targeting contract's registered code and class.
_NO_DB_CODE = "invalid_argument.cli.no_database"
_NO_DB_HINT = (
    "pass a path (stratadb.open('./mydb')), set STRATA_DB "
    "(stratadb.from_env()), or use cache=True for ephemeral"
)


def agents_guide() -> str:
    """The complete offline **Python SDK** usage guide, embedded in the wheel.

    A single self-contained reference for coding agents: opening a database, all
    namespaces (``db.kv``/``json``/``vectors``/``events``/``graphs``/``ai``),
    provider keys, branches/time-travel, errors, and the escape hatch — every
    snippet real, runnable Python. (For the CLI-oriented guide instead, run
    ``strata agents guide``.)
    """
    import importlib.resources

    resource = importlib.resources.files("stratadb").joinpath("_data", "agent-guide.md")
    return resource.read_text(encoding="utf-8")


def mcp_config(db_path: str | os.PathLike[str]) -> dict[str, Any]:
    """The MCP client-config snippet that serves ``db_path`` over stdio."""
    return {"command": "strata", "args": [str(db_path), "mcp", "serve"]}


def command_index() -> dict[str, Any]:
    """The resolved IDL command index bundled in this wheel.

    The full command catalog (ids, kinds, docs, errors) for the installed
    version — for offline introspection of the surface.
    """
    import importlib.resources
    import json

    resource = importlib.resources.files("stratadb").joinpath("_data", "command-index.json")
    with resource.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class Strata:
    """An open Strata database — the handle type :func:`stratadb.open` returns.

    Public for typing and ``isinstance``; construct via :func:`stratadb.open`,
    :func:`stratadb.from_env`, or :func:`stratadb.clone`.

    Args:
        path: Filesystem path to a durable database (created if absent).
            Omit only with ``cache=True``.
        cache: Open a volatile in-memory database instead. Nothing persists.
        branch: Session default branch for commands that omit their own.
        space: Session default product space for commands that omit their own.

    Raises:
        InvalidArgumentError: When neither ``path`` nor ``cache=True`` is given
            (the D2 targeting contract — Strata never opens the cwd implicitly).
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        cache: bool = False,
        branch: str | None = None,
        space: str | None = None,
    ):
        if cache:
            self._core = Core.open_cache()
        elif path is not None:
            self._core = Core.open_durable(str(path))
        else:
            raise client_error(
                InvalidArgumentError, _NO_DB_CODE, "no database specified", _NO_DB_HINT
            )
        self._closed = False
        if branch is not None or space is not None:
            self._core.set_scope(branch, space)
        self._commands = Commands(self._core)
        # Scope override for db.at(...) views; None means "use the session default".
        self._branch: str | None = None
        self._space: str | None = None

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        """Runs one raw command on the wire, returning its output envelope.

        The permanent escape hatch to the full command surface::

            db.execute({"type": "kv_scan", "limit": 10})
            # -> {"type": "kv_scan_result", "data": {...}}

        Raises the typed :class:`~stratadb.errors.StrataError` on a domain
        failure.
        """
        return self._core.execute(command)

    @property
    def kv(self) -> KVNamespace:
        """The key-value namespace."""
        ns = self.__dict__.get("_kv_ns")
        if ns is None:
            ns = KVNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_kv_ns"] = ns
        return ns

    @property
    def json(self) -> JSONNamespace:
        """The JSON-document namespace."""
        ns = self.__dict__.get("_json_ns")
        if ns is None:
            ns = JSONNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_json_ns"] = ns
        return ns

    @property
    def vectors(self) -> VectorsNamespace:
        """The vector namespace."""
        ns = self.__dict__.get("_vectors_ns")
        if ns is None:
            ns = VectorsNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_vectors_ns"] = ns
        return ns

    @property
    def events(self) -> EventsNamespace:
        """The event-log namespace."""
        ns = self.__dict__.get("_events_ns")
        if ns is None:
            ns = EventsNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_events_ns"] = ns
        return ns

    @property
    def graphs(self) -> GraphsNamespace:
        """The property-graph namespace."""
        ns = self.__dict__.get("_graphs_ns")
        if ns is None:
            ns = GraphsNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_graphs_ns"] = ns
        return ns

    @property
    def branches(self) -> BranchesNamespace:
        """The branch-management namespace."""
        ns = self.__dict__.get("_branches_ns")
        if ns is None:
            ns = BranchesNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_branches_ns"] = ns
        return ns

    @property
    def spaces(self) -> SpacesNamespace:
        """The product-space namespace."""
        ns = self.__dict__.get("_spaces_ns")
        if ns is None:
            ns = SpacesNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_spaces_ns"] = ns
        return ns

    @property
    def admin(self) -> AdminNamespace:
        """The admin / diagnostics namespace."""
        ns = self.__dict__.get("_admin_ns")
        if ns is None:
            ns = AdminNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_admin_ns"] = ns
        return ns

    @property
    def arrow(self) -> ArrowNamespace:
        """The Arrow / Parquet import-export namespace."""
        ns = self.__dict__.get("_arrow_ns")
        if ns is None:
            ns = ArrowNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_arrow_ns"] = ns
        return ns

    @property
    def ai(self) -> AiNamespace:
        """The inference namespace — chat, embeddings, reranking, and model
        management (OpenAI-shaped, cloud + local)."""
        ns = self.__dict__.get("_ai_ns")
        if ns is None:
            ns = AiNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_ai_ns"] = ns
        return ns

    def at(self, *, branch: str | None = None, space: str | None = None) -> "Strata":
        """Returns a lightweight scoped view over the same database.

        Every namespace on the view targets ``branch``/``space``; unspecified
        axes inherit this view's scope. The view shares the underlying handle,
        so it needs no separate close. (The raw ``execute`` escape hatch is not
        rescoped — pass ``branch``/``space`` in the command for that path.)
        """
        view = object.__new__(Strata)
        view._core = self._core
        view._commands = self._commands
        view._closed = self._closed
        view._branch = branch if branch is not None else self._branch
        view._space = space if space is not None else self._space
        return view

    @property
    def version(self) -> str:
        """The engine/SDK version this database is running."""
        return __version__

    @property
    def branch(self) -> str:
        """The session default branch."""
        return self._core.default_branch

    @property
    def space(self) -> str:
        """The session default product space."""
        return self._core.default_space

    @property
    def state(self) -> Any:
        """Removed in V1. Raises a teaching :class:`UnsupportedError`."""
        raise client_error(
            UnsupportedError,
            "unsupported.sdk.state_removed",
            "the state-cell primitive (db.state) was removed in V1",
            "use db.kv for keyed values, or db.json for structured documents",
        )

    def close(self) -> None:
        """Closes the database. Idempotent."""
        if not self._closed:
            self._core.close()
            self._closed = True

    def __enter__(self) -> "Strata":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        self.close()
        return False


def agents_skill() -> str:
    """The Claude Code skill for Strata, embedded in the wheel.

    Returns the version-stamped SKILL.md markdown (YAML frontmatter + the
    condensed Python/CLI playbook). Write it to
    ``.claude/skills/strata/SKILL.md`` in a repo so agent sessions load it
    automatically — or run ``strata agents skill --write``, which does the
    same from the CLI. The template is vendored from strata-core at the
    pinned rev, so the two surfaces cannot drift.
    """
    import importlib.resources

    resource = importlib.resources.files("stratadb").joinpath("_data", "skill.md")
    return resource.read_text(encoding="utf-8").replace("{version}", __version__)


def open(  # noqa: A001 — deliberate builtin shadow at module scope (gzip.open precedent)
    path: str | os.PathLike[str] | None = None,
    *,
    cache: bool = False,
    branch: str | None = None,
    space: str | None = None,
) -> Strata:
    """Opens a Strata database — the canonical entry point.

    ``stratadb.open("./mydb")`` opens (creating if absent) a durable database
    at a directory path; ``stratadb.open(cache=True)`` opens a volatile
    in-memory one. ``branch``/``space`` set the session defaults for commands
    that omit their own.

    Never opens the current directory implicitly: with neither ``path`` nor
    ``cache=True`` it raises
    :class:`~stratadb.errors.InvalidArgumentError`.
    """
    return Strata(path, cache=cache, branch=branch, space=space)


def from_env(*, branch: str | None = None, space: str | None = None) -> Strata:
    """Opens the database named by the ``STRATA_DB`` environment variable.

    Mirrors the CLI's D2 targeting contract exactly.
    """
    path = os.environ.get("STRATA_DB")
    if not path:
        raise client_error(
            InvalidArgumentError, _NO_DB_CODE, "STRATA_DB is not set", _NO_DB_HINT
        )
    return Strata(path, branch=branch, space=space)


def clone(
    dataset: str,
    dest: str | os.PathLike[str],
    *,
    hub_url: str | None = None,
    branch: str | None = None,
) -> Strata:
    """Clones a dataset from a StrataHub into a new durable database.

    Fetches ``dataset`` from the hub (``hub_url``, or the resolver default
    when omitted), materializes it as a durable database at ``dest`` (which
    must not exist or be empty), and returns an open handle to it. ``branch``
    selects the dataset branch to fetch (the dataset's default when omitted).

    The StrataHub client ships in the standard wheel. A minimal build
    compiled without the hub client instead raises
    :class:`~stratadb.errors.FailedPreconditionError`
    (``failed_precondition.executor.hub_clone``).
    """
    # Clone is a standalone operation that creates the database at `dest`; a
    # transient cache handle only carries the command to the executor.
    opener = Strata(cache=True)
    try:
        command: dict[str, Any] = {
            "type": "hub_clone",
            "dataset": dataset,
            "dest": str(dest),
        }
        if hub_url is not None:
            command["hub_url"] = hub_url
        if branch is not None:
            command["branch"] = branch
        opener.execute(command)
    finally:
        opener.close()
    return Strata(dest)


__all__ = [
    "open",
    "from_env",
    "clone",
    "Strata",
    "errors",
    "filters",
    "agents_guide",
    "agents_skill",
    "mcp_config",
    "command_index",
    "__version__",
]
