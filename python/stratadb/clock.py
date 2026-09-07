"""Strata's two clocks — the logical commit timeline and wall-clock time.

Every commit records two different things, and they are **not**
interchangeable:

``timestamp`` → read it back with ``as_of``
    A position on the *logical commit timeline*: a per-commit counter that
    starts near 1. It orders commits and reproduces a read exactly. It is not
    microseconds and **never** a calendar date — a fresh database's first
    commit is ``timestamp=1``, not 1970.

``committed_at`` → read it back with ``as_of_time``
    The *wall-clock instant* the commit was applied, in UTC epoch
    microseconds. This is the one to format as a date. It is ``None`` when
    unknown: a commit written before engine 1.2.1, or one replayed from an
    artifact import. It stays an ``int`` on the result types, which mirror the
    wire faithfully — :func:`to_datetime` is the one-liner that makes it a
    ``datetime``, and it tolerates the ``None``.

So::

    receipt = db.kv.put("k", "v1")
    db.kv.get("k", as_of=receipt.commit.timestamp)         # exactly that commit
    db.kv.get("k", as_of_time="2026-09-05 15:00")          # what it was then
    stratadb.to_datetime(receipt.commit.committed_at)      # when it happened

``as_of_time`` accepts raw epoch microseconds, a ``datetime``, a ``date``, or an
ISO 8601 string — :func:`to_micros` is the conversion, and it is applied for
you. Passing both clocks to one call raises ``InvalidArgumentError``
(``invalid_argument.executor.as_of_conflict``).

Three caveats before you reach for wall clock:

- **It does not clamp.** An instant outside the branch's dated history is
  refused with :class:`~stratadb.errors.HistoryUnavailableError`, at *both*
  ends — so ``as_of_time=datetime.now()`` raises, because now is past the
  newest commit. To read the latest state, pass no clock at all. The window is
  only as wide as the database's own history: on one created a minute ago,
  yesterday is outside it.
- **It is best-effort and non-monotonic** (the host clock can step). Use
  ``as_of`` where exact reproducibility matters.
- **Commits written before engine 1.2.1 have no instant**, so they report
  ``committed_at=None`` and are invisible to a wall-clock query.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional, Union

from .errors import InvalidArgumentError, client_error

#: What ``as_of_time`` accepts: epoch microseconds, a ``datetime``, a ``date``,
#: or an ISO 8601 string.
TimeLike = Union[int, datetime, date, str]

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

_KIND_HINT = (
    "pass epoch microseconds, a datetime, a date, or an ISO 8601 string "
    '(e.g. "2026-09-05" or "2026-09-05T15:00:00Z")'
)


def _aware(moment: datetime) -> datetime:
    """Attaches the local zone to a naive datetime.

    A naive value is read as **local** time — matching ``datetime.now()``, the
    way it is almost always produced, and the CLI's ``--as-of-time``. Pass an
    aware datetime when you mean UTC.
    """
    return moment if moment.tzinfo is not None else moment.astimezone()


def to_micros(when: Optional[TimeLike]) -> Optional[int]:
    """Converts a wall-clock value to UTC epoch microseconds.

    Accepts what ``as_of_time`` accepts — epoch microseconds (returned
    unchanged), a ``datetime``, a ``date`` (local midnight), or an ISO 8601
    string (a trailing ``Z`` is fine). ``None`` passes through, so this can
    wrap an optional argument.

    Naive datetimes and strings without an offset are read as local time.

    Examples:
        >>> from datetime import datetime, timezone
        >>> stratadb.to_micros(datetime(2026, 9, 5, tzinfo=timezone.utc))
        1788566400000000
        >>> stratadb.to_micros(1788566400000000)   # raw micros pass through
        1788566400000000
    """
    if when is None or (isinstance(when, int) and not isinstance(when, bool)):
        return when
    if isinstance(when, str):
        text = when.strip()
        try:
            when = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        except ValueError:
            raise client_error(
                InvalidArgumentError,
                "invalid_argument.sdk.as_of_time",
                f"as_of_time string is not an ISO 8601 date or timestamp: {when!r}",
                _KIND_HINT,
            ) from None
    if isinstance(when, datetime):
        delta = _aware(when).astimezone(timezone.utc) - _EPOCH
    elif isinstance(when, date):
        delta = _aware(datetime(when.year, when.month, when.day)).astimezone(timezone.utc) - _EPOCH
    else:
        raise client_error(
            InvalidArgumentError,
            "invalid_argument.sdk.as_of_time",
            f"as_of_time must be a wall-clock instant, got {type(when).__name__}",
            _KIND_HINT,
        )
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def to_datetime(micros: Optional[int]) -> Optional[datetime]:
    """Converts UTC epoch microseconds to an aware ``datetime`` (UTC).

    ``None`` passes through, so ``to_datetime(receipt.commit.committed_at)``
    is safe on a commit whose instant is unknown. Call ``.astimezone()`` on the
    result to render it in local time.

    Examples:
        >>> stratadb.to_datetime(1788566400000000).isoformat()
        '2026-09-05T00:00:00+00:00'
        >>> stratadb.to_datetime(None) is None
        True
    """
    if micros is None:
        return None
    if not isinstance(micros, int) or isinstance(micros, bool):
        raise client_error(
            InvalidArgumentError,
            "invalid_argument.sdk.committed_at",
            f"expected epoch microseconds (an int), got {type(micros).__name__}",
            "pass a committed_at value, or None",
        )
    return _EPOCH + timedelta(microseconds=micros)


__all__ = ["TimeLike", "to_micros", "to_datetime"]
