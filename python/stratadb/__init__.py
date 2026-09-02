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

import json
import os
from typing import Any, Callable

from . import _stratadb  # native extension
from . import errors, filters
from ._core import Core
from ._generated import Commands
from ._generated.models import HubCloneProgress, HubDatasetSort, PromotionStrategy
from .errors import InvalidArgumentError, UnsupportedError, client_error, error_from_payload
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
from .namespaces.hub import HubNamespace
from ._demo import demo
from ._scaffold import init

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
    namespaces (``db.kv``/``json``/``vectors``/``events``/``graphs``/``ai``/``hub``),
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
        durability: str | None = None,
        ipc: str | None = None,
        memory_budget: int | None = None,
    ):
        if durability not in (None, "standard", "always"):
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.command",
                f"invalid durability {durability!r}",
                'use "standard" (durable at the next sync point) or "always" '
                "(synced before every acknowledgement)",
            )
        if ipc not in (None, "host", "client", "off"):
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.command",
                f"invalid ipc mode {ipc!r}",
                'use "host" (default: own or broker, host a socket when owning), '
                '"client" (broker on contention, never host), or "off" (exclusive open)',
            )
        if ipc in ("host", "client") and os.name != "posix":
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.command",
                "multi-process IPC is unix-only",
                'on this platform open with ipc="off" (or omit ipc=); '
                "a durable database is exclusively owned by one handle",
            )
        if memory_budget is not None and (
            isinstance(memory_budget, bool)
            or not isinstance(memory_budget, int)
            or memory_budget <= 0
        ):
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.command",
                f"invalid memory_budget {memory_budget!r}",
                "pass the total storage memory budget as a positive int of bytes "
                "(at least 1 MiB), or omit it to derive one from host memory",
            )
        if cache:
            if durability is not None or ipc is not None or memory_budget is not None:
                raise client_error(
                    InvalidArgumentError,
                    "invalid_argument.sdk.command",
                    "durability=/ipc=/memory_budget= apply only to durable databases",
                    "an in-memory (cache=True) database has neither a durability "
                    "mode nor multi-process brokering, and the SDK does not size "
                    "one explicitly",
                )
            self._core = Core.open_cache()
        elif path is not None:
            self._core = Core.open_durable(str(path), durability, ipc, memory_budget)
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

        Raises the typed :class:`~stratadb.errors.StrataError` hierarchy: a
        domain failure carries the engine's ``code``; invalid input raises
        :class:`~stratadb.errors.InvalidArgumentError`.
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

    @property
    def hub(self) -> HubNamespace:
        """The StrataHub browse namespace — datasets, cards, refs, and the yank
        list of a hub (read-only; never touches this database's data)."""
        ns = self.__dict__.get("_hub_ns")
        if ns is None:
            ns = HubNamespace(self._commands, self._core, self._branch, self._space)
            self.__dict__["_hub_ns"] = ns
        return ns

    def at(self, *, branch: str | None = None, space: str | None = None) -> "Strata":
        """Returns a lightweight scoped view over the same database.

        Each axis you pass **rebinds** that axis for the view; an axis you omit
        inherits this view's scope. Chained ``at()`` calls therefore re-scope
        freely — ``db.at(space="a").at(space="b")`` targets ``b`` — so branch
        and space isolation is a routing convenience, **not** a security
        sandbox: don't hand a scoped view to less-trusted code expecting
        containment.

        The view shares the underlying handle, so it needs no separate close.
        (The raw ``execute`` escape hatch is not rescoped — pass
        ``branch``/``space`` in the command for that path.)
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
        """This view's effective branch (the ``at()`` override, else the session default)."""
        return self._branch if self._branch is not None else self._core.default_branch

    @property
    def space(self) -> str:
        """This view's effective product space (the ``at()`` override, else the session default)."""
        return self._space if self._space is not None else self._core.default_space

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
    """The ``strata-python`` agent skill, embedded in the wheel.

    Returns the SKILL.md markdown (YAML frontmatter + the Python playbook),
    vendored verbatim from stratalab/strata-agent-skills at the rev in
    ``STRATA_AGENT_SKILLS_REV`` — one agent-facing surface, so the wheel and
    the skills repo cannot disagree. Write it to
    ``.claude/skills/strata-python/SKILL.md`` (``stratadb.init()`` does exactly
    that) and install the rest of the set — ``strata``, ``strata-branching``,
    ``strata-time-travel`` — with ``npx skills add stratalab/strata-agent-skills``.
    """
    import importlib.resources

    resource = importlib.resources.files("stratadb").joinpath("_data", "skill.md")
    return resource.read_text(encoding="utf-8")


def open(  # noqa: A001 — deliberate builtin shadow at module scope (gzip.open precedent)
    path: str | os.PathLike[str] | None = None,
    *,
    cache: bool = False,
    branch: str | None = None,
    space: str | None = None,
    durability: str | None = None,
    ipc: str | None = None,
    memory_budget: int | None = None,
) -> Strata:
    """Opens a Strata database — the canonical entry point.

    ``stratadb.open("./mydb")`` opens (creating if absent) a durable database
    at a directory path; ``stratadb.open(cache=True)`` opens a volatile
    in-memory one. ``branch``/``space`` set the session defaults for commands
    that omit their own.

    ``durability`` selects the commit-durability mode for a durable database:
    ``"standard"`` (the default — commits become durable at the next sync
    point; an unclean process death can lose the acknowledged tail) or
    ``"always"`` (every commit is synced before acknowledgement). Each write
    receipt reports what actually held: ``receipt.commit.durability`` is one of
    ``"not_durable"``, ``"standard"``, ``"always"``, or ``"uncertain"``.

    ``ipc`` selects the multi-process policy for a durable database (unix):
    ``"host"`` (the default) owns the store when the path is free — hosting a
    socket other processes can broker to — and transparently brokers to the
    existing owner otherwise, so several processes (or handles) share one
    durable database; ``"client"`` brokers on contention but never hosts;
    ``"off"`` is a raw exclusive open with no brokering (a second open then
    raises). ``db.admin.ipc_status()`` reports the live topology.

    ``memory_budget`` sizes the storage memory budget of a durable database, in
    bytes (at least 1 MiB; the engine rejects smaller with
    ``invalid_argument.engine.persistence``). When omitted the engine derives
    one at open — 25% of usable host memory, capped at 8 GiB. It applies to
    the handle that *owns* the store for this open (per open, not persisted);
    a handle that brokers to an existing owner inherits the owner's budget.
    ``db.admin.info().memory_budget`` reports what held (``total_bytes`` and a
    ``source`` of ``"explicit"``, ``"derived_from_host"``, or
    ``"fixed_default"``).

    Never opens the current directory implicitly: with neither ``path`` nor
    ``cache=True`` it raises
    :class:`~stratadb.errors.InvalidArgumentError`.
    """
    return Strata(
        path,
        cache=cache,
        branch=branch,
        space=space,
        durability=durability,
        ipc=ipc,
        memory_budget=memory_budget,
    )


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
    progress: Callable[[HubCloneProgress], Any] | None = None,
) -> Strata:
    """Clones a dataset from a StrataHub into a new durable database.

    Fetches ``dataset`` from the hub (``hub_url``, or the layered resolver's
    choice when omitted — ``STRATA_HUB_URL``, then the project and global
    Strata config files, then ``https://hub.stratahub.io``), materializes it
    as a durable database at ``dest`` (which must not exist or be empty), and
    returns an open handle to it. ``branch`` selects the dataset branch to
    fetch (the dataset's default when omitted); ``db.hub.list_refs(dataset)``
    lists them. Browse first with ``db.hub`` — on any handle, even
    ``stratadb.open(cache=True)``.

    ``progress``, when given, is called with one :class:`stratadb.HubCloneProgress`
    per event as the clone advances. ``.stage`` runs ``resolved`` (``.branch``,
    ``.manifest_hash``) → ``manifest_fetched`` (``.object_count``,
    ``.total_bytes``) → ``object_fetched`` once per object (``.index`` of
    ``.object_count``, ``.bytes``) → ``importing`` → ``done``. The callback runs
    on the calling thread between fetches. It cannot cancel the clone: if it
    raises, the remaining events are dropped, the clone completes, and its
    exception is then raised from ``clone()`` (the database at ``dest`` is
    complete but left unopened).

    A ``dest`` that exists and is not empty raises ``FailedPreconditionError``
    (``failed_precondition.executor.hub_clone``). A dataset or branch the hub
    does not have surfaces as the hub's 404 through the clone transport —
    ``UnavailableError`` (``unavailable.executor.hub_transport``), the same as
    an unreachable hub — so browse with ``db.hub`` first, whose lookups raise
    ``NotFoundError``. The StrataHub client ships in the standard wheel.
    """
    if progress is not None and not callable(progress):
        raise client_error(
            InvalidArgumentError,
            "invalid_argument.sdk.command",
            f"progress must be callable, got {type(progress).__name__}",
            "pass a function taking one stratadb.HubCloneProgress event, or omit it",
        )

    report = None
    if progress is not None:
        callback = progress

        def report(envelope_json: str) -> None:
            callback(HubCloneProgress.from_wire(json.loads(envelope_json)["data"]))

    # Clone is a standalone operation that creates the database at `dest`; the
    # binding runs it on a scratch executor, so no handle is involved.
    try:
        _stratadb.hub_clone(dataset, str(dest), branch, hub_url, report)
    except _stratadb.StrataNativeError as exc:
        raise error_from_payload(exc.args[0] if exc.args else "{}") from None
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
    "demo",
    "init",
    "PromotionStrategy",
    "HubDatasetSort",
    "HubCloneProgress",
    "__version__",
]
