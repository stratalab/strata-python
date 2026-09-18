"""Typed error hierarchy for Strata.

Every engine failure carries a stable code ``<class>.<area>.<detail>`` and the
same structured status the CLI and MCP surfaces emit. The binding raises a
single native error carrying that status as JSON; this module maps it to a
typed exception whose class is the code's first segment.

**Match on** :attr:`StrataError.code` **or** :attr:`StrataError.error_class` —
never on the human ``message`` text, which is not part of the contract.

Codes come from two registries: the engine's, published by
``strata agents errors``, and the SDK's own client-side ones — a closed
handle, a bad ``limit``, a ``datetime`` handed to ``as_of`` — which
:func:`catalog` publishes and the wheel ships as ``sdk-errors.json``.

Misses (a key that is absent) are **not** errors: reads return ``None``.
Out-of-range time travel raises :class:`HistoryUnavailableError`, distinct from
:class:`NotFoundError`.
"""

from __future__ import annotations

import json
from typing import Any

from ._catalog import catalog as _catalog
from ._catalog import entry as _entry


class StrataError(Exception):
    """Base for every Strata error. Carries the full structured status.

    Attributes:
        code: Stable ``<class>.<area>.<detail>`` identifier. Match on this.
        error_class: The code's first segment (e.g. ``"not_found"``).
        message: Human-readable text. **Never** match on this.
        hint: Suggested fix, often with a concrete next step.
        ref: Documentation URL, always ``https://stratadb.org/e/<code>``.
        reference_id: Per-occurrence identifier for correlating logs.
        retry_policy: One of ``never``/``after_state_change``/``same_request``/
            ``idempotent_only``/``unknown``.
        retryable: Whether retrying the same request may succeed.
        commit_outcome: For writes, whether the mutation committed.
        details: Structured detail records, when present.
        hints: Additional hint lines, when present.
        trace_id: Distributed-trace correlation id, when present.
    """

    def __init__(self, status: dict[str, Any]):
        self.code: str = status.get("code", "")
        self.error_class: str = status.get("class") or (
            self.code.split(".", 1)[0] if self.code else ""
        )
        self.message: str = status.get("message", "")
        self.hint: str = status.get("suggested_fix", "")
        self.ref: str = status.get("docs_url", "")
        self.reference_id: str = status.get("reference_id", "")
        self.retry_policy: str = status.get("retry_policy", "unknown")
        self.retryable: bool = bool(status.get("retryable", False))
        self.commit_outcome: str = status.get("commit_outcome", "")
        self.details: list[Any] = status.get("details", []) or []
        self.hints: list[str] = status.get("hints", []) or []
        self.trace_id: str | None = status.get("trace_id")
        self.status: dict[str, Any] = status
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = [f"{self.code}: {self.message}" if self.code else self.message]
        if self.hint:
            lines.append(f"  hint: {self.hint}")
        if self.ref:
            lines.append(f"  ref: {self.ref}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r})"


# --- One subclass per public error class (the ErrorClass enum, #[non_exhaustive]) ---


class NotFoundError(StrataError):
    """A requested branch, space, collection, graph, document, key, or model does not exist."""


class AlreadyExistsError(StrataError):
    """A resource that must be created fresh already exists."""


class InvalidArgumentError(StrataError):
    """The request contains structurally invalid input."""


class FailedPreconditionError(StrataError):
    """The database is not in a state that permits the operation."""


class AccessDeniedError(StrataError):
    """The operation is not permitted."""


class ConflictError(StrataError):
    """A concurrent change prevents the operation from completing."""


class AmbiguousCommitError(StrataError):
    """A write's commit outcome cannot be determined; inspect state before retrying."""


class HistoryUnavailableError(StrataError):
    """The requested point in time is outside the retained history window."""


class UnsupportedError(StrataError):
    """The operation or capability is not supported in this build."""


class ResourceExhaustedError(StrataError):
    """A quota, budget, or capacity limit was reached."""


class UnavailableError(StrataError):
    """A transient condition prevented the operation; retrying may succeed."""


class IoError(StrataError):
    """An underlying I/O operation failed."""


class CorruptionError(StrataError):
    """On-disk data failed an integrity check."""


class DataLossError(StrataError):
    """Durable state that should exist cannot be reconstructed.

    Distinct from :class:`CorruptionError` (an integrity violation was
    detected) in that the data is unrecoverable, not merely inconsistent.
    The ``data_loss.*`` codes reported ``class = "corruption"`` before
    engine 1.2.0.
    """


class SerializationError(StrataError):
    """A value could not be serialized or deserialized on the wire."""


class InternalError(StrataError):
    """An unexpected internal invariant was violated."""


_ERROR_CLASSES: dict[str, type[StrataError]] = {
    "not_found": NotFoundError,
    "already_exists": AlreadyExistsError,
    "invalid_argument": InvalidArgumentError,
    "failed_precondition": FailedPreconditionError,
    "access_denied": AccessDeniedError,
    "conflict": ConflictError,
    "ambiguous_commit": AmbiguousCommitError,
    "history_unavailable": HistoryUnavailableError,
    "unsupported": UnsupportedError,
    "resource_exhausted": ResourceExhaustedError,
    "unavailable": UnavailableError,
    "io": IoError,
    "corruption": CorruptionError,
    "data_loss": DataLossError,
    "serialization": SerializationError,
    "internal": InternalError,
}


def error_from_status(status: dict[str, Any]) -> StrataError:
    """Builds the typed error for an error-status dict.

    An unknown class (the enum is ``#[non_exhaustive]``) maps to the
    :class:`StrataError` base.
    """
    cls = status.get("class") or (status.get("code", "").split(".", 1)[0])
    return _ERROR_CLASSES.get(cls, StrataError)(status)


def error_from_payload(payload: str) -> StrataError:
    """Builds the typed error from the native binding's JSON payload string."""
    try:
        status = json.loads(payload)
    except (ValueError, TypeError):
        status = {"code": "", "message": payload}
    if not isinstance(status, dict):
        status = {"code": "", "message": str(status)}
    return error_from_status(status)


def require_field(entry: Any, field: str) -> Any:
    """Fetches ``entry[field]`` for a batch entry, raising a typed error if absent.

    Batch helpers accept caller-shaped dicts; a missing required field should
    surface as :class:`InvalidArgumentError` (``invalid_argument.sdk.entry``),
    not a bare ``KeyError`` that ``except StrataError`` would miss.
    """
    try:
        return entry[field]
    except (KeyError, TypeError, IndexError):
        raise client_error(
            InvalidArgumentError,
            "invalid_argument.sdk.entry",
            f"batch entry is missing required field {field!r}",
            "pass each entry as a dict (or tuple) carrying the required fields",
        ) from None


def client_error(
    error_cls: type[StrataError], code: str, message: str, hint: str = ""
) -> StrataError:
    """Builds a client-side (SDK-raised, non-engine) error with a full status.

    Used for guards the engine never sees — e.g. opening with no target. The
    retry policy and commit outcome come from :data:`~stratadb._catalog.SDK_ERRORS`
    so they are stated once and published; ``message`` and ``hint`` stay the
    call site's own, which can name the offending argument and its value.
    """
    row = _entry(code)
    retry_policy = row["retry_policy"]
    return error_cls(
        {
            "class": row["class"],
            "code": code,
            "message": message or row["message"],
            "suggested_fix": hint or row["hint"],
            "docs_url": row["ref"],
            "reference_id": "",
            "retry_policy": retry_policy,
            "retryable": retry_policy not in ("never", "unknown"),
            "commit_outcome": row["commit_outcome"],
        }
    )


def catalog() -> list:
    """Every error code the SDK raises itself, in the engine registry's shape.

    The engine publishes its codes through ``strata agents errors``; these are
    the client-side ones it never sees, which is why they are catalogued here
    (stratalab/strata-python#87). The wheel also ships them as
    ``sdk-errors.json`` beside the command index.

    Examples:
        >>> rows = stratadb.errors.catalog()
        >>> len(rows)
        13
        >>> {row["area"] for row in rows} == {"sdk", "cli"}
        True
    """
    return _catalog()


__all__ = [
    "StrataError",
    "NotFoundError",
    "AlreadyExistsError",
    "InvalidArgumentError",
    "FailedPreconditionError",
    "AccessDeniedError",
    "ConflictError",
    "AmbiguousCommitError",
    "HistoryUnavailableError",
    "UnsupportedError",
    "ResourceExhaustedError",
    "UnavailableError",
    "IoError",
    "CorruptionError",
    "DataLossError",
    "SerializationError",
    "InternalError",
    "error_from_status",
    "error_from_payload",
    "client_error",
    "catalog",
    "require_field",
]
