"""The catalog of codes the SDK raises itself, and the errors built from it.

The engine publishes its codes through ``strata agents errors``; these are the
client-side ones the engine never sees — a closed handle, a bad ``limit``, a
``datetime`` handed to ``as_of``. They carry the same ``<class>.<area>.<detail>``
shape and the same status fields, so a caller matches on them exactly as on an
engine code.

Until this table existed, the codes were string literals spread across the
package with no way to enumerate them: a source scan found ten of the thirteen
(three are raised through module constants) and *silently* reported that as the
whole set — which is how ``invalid_argument.cli.no_database`` went unlisted
(stratalab/strata-python#87). The table is the source of truth,
``tools/export_errors.py`` writes it to ``_data/sdk-errors.json`` for the wheel
and for stratadb.org to render ``/e/`` pages from, and
``tests/test_error_catalog.py`` walks the package's AST so a code cannot be
raised without appearing here.

``area`` is not always ``sdk``: ``invalid_argument.cli.no_database`` is the
CLI's code, reused deliberately because ``from_env()`` implements the same
targeting contract. Anything filtering on ``.sdk.`` misses it.
"""

from __future__ import annotations

from typing import Any, Dict

#: One entry per code the SDK raises. ``message`` and ``hint`` are the
#: *documentation* text — the generic statement of the condition, as the
#: engine's registry carries. A raise site passes its own specific message
#: (``"limit must be a positive integer, got 0"``); this is what a reader gets
#: when they look the code up.
SDK_ERRORS: Dict[str, Dict[str, Any]] = {
    "failed_precondition.sdk.fork_not_supported": {
        "message": "The handle was inherited across a fork and cannot be used.",
        "hint": "Open a fresh handle in the child process; a handle cannot cross os.fork().",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "failed_precondition.sdk.handle_closed": {
        "message": "The database handle is closed.",
        "hint": "Open a new handle; close() is final for the one you have (and idempotent).",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.cli.no_database": {
        "message": "No database was specified.",
        "hint": (
            "Pass a path to stratadb.open(), set STRATA_DB for stratadb.from_env(), "
            "or use cache=True for an in-memory database."
        ),
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.as_of_kind": {
        "message": "The as_of argument is not a commit timestamp.",
        "hint": (
            "as_of takes a position on the commit timeline (an int); pass as_of_time "
            "for a wall-clock instant."
        ),
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.as_of_time": {
        "message": "The as_of_time argument is not a wall-clock instant.",
        "hint": (
            "Pass epoch microseconds, a datetime, a date, or an ISO 8601 string "
            '(e.g. "2026-09-05T15:00:00Z").'
        ),
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.command": {
        "message": "The request contains invalid input.",
        "hint": "Correct the argument the message names and retry.",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.committed_at": {
        "message": "The value is not a commit instant.",
        "hint": "Pass a committed_at value (epoch microseconds), or None.",
        "retry_policy": "never",
        "commit_outcome": "not_applicable",
    },
    "invalid_argument.sdk.entry": {
        "message": "A batch entry is missing a required field.",
        "hint": "Pass each entry as a dict (or tuple) carrying the required fields.",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.fork_ambiguous": {
        "message": "A fork anchor was given twice.",
        "hint": "Fork at a version or at a timestamp, not both.",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.limit": {
        "message": "The limit is not a positive integer.",
        "hint": "Omit limit to page through everything, or pass a value >= 1.",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.vector_metadata": {
        "message": "The vector metadata is not a mapping.",
        "hint": "Pass metadata as a dict of scalar values, or omit it.",
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "invalid_argument.sdk.vector_metric": {
        "message": "The distance metric is not one this collection supports.",
        "hint": 'Use "cosine", "euclidean", or "dot".',
        "retry_policy": "never",
        "commit_outcome": "not_started",
    },
    "unsupported.sdk.state_removed": {
        "message": "The state-cell primitive was removed in V1.",
        "hint": "Use db.kv for keyed values, or db.json for structured documents.",
        "retry_policy": "never",
        "commit_outcome": "not_applicable",
    },
}


def entry(code: str) -> Dict[str, Any]:
    """The catalog row for ``code`` as it is published, ``ref`` included.

    An unknown code (one raised before it was catalogued — the drift guard
    exists so that cannot ship) still yields a usable row rather than raising
    inside error construction.
    """
    row = SDK_ERRORS.get(code, {})
    return {
        "code": code,
        "class": code.split(".", 1)[0],
        "area": code.split(".")[1] if code.count(".") >= 2 else "",
        "message": row.get("message", ""),
        "hint": row.get("hint", ""),
        "retry_policy": row.get("retry_policy", "never"),
        "commit_outcome": row.get("commit_outcome", "not_started"),
        "ref": f"https://stratadb.org/e/{code}",
    }


def catalog() -> list:
    """Every code the SDK itself raises, in the engine registry's shape.

    The engine's codes come from ``strata agents errors``; these are the
    client-side ones, which no engine build knows about. Sorted by code, one
    dict per entry with ``code``, ``class``, ``area``, ``message``, ``hint``,
    ``retry_policy``, ``commit_outcome`` and ``ref``.

    Examples:
        >>> rows = stratadb.errors.catalog()
        >>> len(rows)
        13
        >>> rows[0]["code"]
        'failed_precondition.sdk.fork_not_supported'
        >>> {row["area"] for row in rows} == {"sdk", "cli"}
        True
    """
    return [entry(code) for code in sorted(SDK_ERRORS)]


__all__ = ["SDK_ERRORS", "catalog", "entry"]
