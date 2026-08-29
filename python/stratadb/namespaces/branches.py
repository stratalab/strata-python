"""``db.branches`` — branch management (create, fork, compare, promote, delete).

Branches are database-global (not scoped to a branch/space), so these methods
ignore the namespace scope.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from .._generated.models import PromotionStrategy
from ..errors import InvalidArgumentError, NotFoundError, client_error
from .base import Namespace

# Accepted spellings of a promotion strategy -> wire value. The wire (and the
# generated ``PromotionStrategy`` enum) spell it ``source_wins``; the CLI flag
# spells it ``source-wins``, so that is accepted too.
_STRATEGIES = {
    "strict": "strict",
    "source_wins": "source_wins",
    "source-wins": "source_wins",
}


def _strategy_value(strategy: Any) -> str:
    if isinstance(strategy, PromotionStrategy):
        return strategy.value
    if isinstance(strategy, str) and strategy in _STRATEGIES:
        return _STRATEGIES[strategy]
    raise client_error(
        InvalidArgumentError,
        "invalid_argument.sdk.command",
        f"invalid promotion strategy {strategy!r}",
        'pass "strict" (refuse on any conflict) or "source_wins" '
        "(the source side's value or tombstone wins each conflict)",
    )


class BranchesNamespace(Namespace):
    """Named branches with copy-on-write forks, time-anchored history, and promotion.

    A fresh database has one branch, ``default``. Each listed branch is a
    ``BranchItem`` exposing ``.name``, ``.generation``, ``.status``, ``.parent``
    (fork lineage), ``.merge_parent`` (the last promotion into it), ....
    Bring a fork's work back with :meth:`diff` → :meth:`preview` → :meth:`merge`.

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
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.fork_ambiguous",
                "fork accepts version or timestamp, not both",
            )
        if version is not None:
            return self._c.branch_fork_at_version(source, name, version)
        if timestamp is not None:
            return self._c.branch_fork_at_timestamp(source, name, timestamp)
        return self._c.branch_fork(source, name)

    def fork_at_version(self, source: str, name: str, version: int) -> Any:
        """Forks ``name`` from ``source`` at a specific retained commit version.

        The version comes from a write receipt (``receipt.commit.version``); the
        fork sees ``source``'s history up to and including that commit.

        Examples:
            >>> base = db.kv.put("greeting", "original")  # The receipt carries this commit's version.
            >>> _ = db.kv.put("greeting", "updated")
            >>> _ = db.branches.fork_at_version("default", "snapshot", base.commit.version)  # snapshot forks default's history at that version.
            >>> db.at(branch="snapshot").kv.get("greeting")
            b'original'
        """
        return self.fork(source, name, version=version)

    def fork_at_timestamp(self, source: str, name: str, timestamp: int) -> Any:
        """Forks ``name`` from ``source`` as of a commit timestamp (microseconds).

        The timestamp comes from a write receipt (``receipt.commit.timestamp``).

        Examples:
            >>> base = db.kv.put("greeting", "original")  # The receipt carries this commit's timestamp (microseconds).
            >>> _ = db.kv.put("greeting", "updated")
            >>> _ = db.branches.fork_at_timestamp("default", "snapshot", base.commit.timestamp)  # snapshot forks default's history as of that instant.
            >>> db.at(branch="snapshot").kv.get("greeting")
            b'original'
        """
        return self.fork(source, name, timestamp=timestamp)

    def delete(self, name: str) -> Any:
        """Deletes a branch.

        Examples:
            >>> _ = db.branches.create("temp")
            >>> _ = db.branches.delete("temp")
            >>> sorted(b.name for b in db.branches.list())
            ['default']
        """
        return self._c.branch_delete(name)

    def diff(self, branch_a: str, branch_b: str, *, as_of: Optional[int] = None) -> Any:
        """Compares two branches and reports what differs, across every primitive.

        Directional ``branch_a`` → ``branch_b``. The result's ``.spaces`` holds
        one ``SpaceComparisonItem`` per (space, capability) that differs, each
        with ``.added`` (only on B), ``.removed`` (only on A), and ``.modified``
        (on both, with different values). Capabilities are ``key_value``,
        ``json``, ``vector``, ``vector_collection``, ``event``,
        ``graph_metadata``, ``graph_node``, ``graph_edge``, and
        ``graph_ontology``; an entity's ``.identity`` is its space-relative key
        as ``bytes``. Read-only. Pass ``as_of`` (a receipt's commit value) to
        compare both branches as of that commit. A missing branch raises
        ``NotFoundError`` (``not_found.engine.branch``).

        Examples:
            >>> _ = db.vectors.create_collection("notes", 2, metric="cosine")
            >>> _ = db.kv.put("config", "base")
            >>> _ = db.branches.fork("default", "experiment")
            >>> _ = db.at(branch="experiment").kv.put("config", "tuned")  # diverge the key-value entry on the fork
            >>> _ = db.at(branch="experiment").vectors.upsert("notes", "n1", [0.1, 0.2])  # add a vector on the fork
            >>> _ = db.branches.diff("default", "experiment")  # reports the key-value change and the new vector, grouped by capability
        """
        return self._c.branch_diff(branch_a, branch_b, at_timestamp=as_of)

    def preview(self, source: str, target: str, *, strategy: Any = "strict") -> Any:
        """Previews promoting ``source`` into ``target`` without mutating either.

        Derives the branch point from the fork lineage, runs the three-way
        comparison :meth:`merge` would, and reports its ``.conflicts`` — the
        entities both branches changed differently since the branch point —
        each with ``.kind``, ``.source_value`` / ``.target_value``, and what
        ``strategy`` would do with it (``.strategy_result``: ``"refused"``
        under ``"strict"``, ``"source_wins"`` under ``"source_wins"``). An
        empty ``.conflicts`` means a strict merge will apply.
        ``.capabilities_unsupported`` lists what a promotion never carries
        (event streams and graphs are compare-only). Branches with no shared
        fork lineage raise ``InvalidArgumentError``
        (``invalid_argument.engine.branch_point``).

        Examples:
            >>> _ = db.kv.put("config", "base")
            >>> _ = db.branches.fork("default", "experiment")
            >>> _ = db.at(branch="experiment").kv.put("config", "tuned")  # change on the fork
            >>> _ = db.branches.preview("experiment", "default", strategy="strict")  # a clean preview — no conflicting changes on default
        """
        return self._c.branch_preview(source, target, strategy=_strategy_value(strategy))

    def merge(self, source: str, target: str, *, strategy: Any = "strict") -> Any:
        """Promotes ``source``'s changes into ``target`` as one atomic commit.

        Applies every key-value, JSON, and vector change ``source`` made since
        the branch point; ``source`` itself is left unchanged. Event streams and
        graphs are compared but never merged (see ``.capabilities_unsupported``).
        Under ``"strict"`` (the default) any conflict raises ``ConflictError``
        (``conflict.engine.promotion``) and nothing is written; under
        ``"source_wins"`` the source's value or tombstone is applied for each
        conflict, and each overwritten or deleted target entry is reported.
        The outcome lists the ``.applied`` and ``.deleted`` entities, the
        ``.conflicts`` it resolved, and the target's new ``.target_version``
        (``None`` when nothing applied — no commit is written). ``strategy``
        accepts the strings or :class:`stratadb.PromotionStrategy`. Branches
        with no shared fork lineage raise ``InvalidArgumentError``
        (``invalid_argument.engine.branch_point``); :meth:`preview` first when
        the outcome matters.

        Examples:
            >>> _ = db.kv.put("config", "base")
            >>> _ = db.branches.fork("default", "experiment")
            >>> _ = db.at(branch="experiment").kv.put("config", "tuned")  # change on the fork
            >>> _ = db.branches.merge("experiment", "default", strategy="strict")  # applies the fork's change onto default
        """
        return self._c.branch_merge(source, target, strategy=_strategy_value(strategy))

    def __contains__(self, name: str) -> bool:
        return self.get(name) is not None

    def __iter__(self) -> Iterator[str]:
        return iter(branch.name for branch in self._c.branch_list().items)
