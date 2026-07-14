"""``db.events`` — the append-only, hash-chained event log.

Records are immutable and expose ``previous_hash``/``hash``. Sequence numbers
are dense and monotonic. ``range_by_time`` is the one wall-clock (occurrence
time) axis; everything else is sequence-addressed.
"""

from __future__ import annotations

from typing import Any, Optional

from .._results import BatchResult, Page
from .base import Namespace


def _event_entries(entries: Any) -> list[dict]:
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append({"event_type": entry["event_type"], "payload": entry["payload"]})
        else:
            event_type, payload = entry
            out.append({"event_type": event_type, "payload": payload})
    return out


def _direction(reverse: bool) -> str:
    return "reverse" if reverse else "forward"


class EventsNamespace(Namespace):
    """The hash-chained event log.

    Events are sequence-addressed (dense, monotonic, starting at 0) and
    immutable once appended.

    Examples:
        >>> _ = db.events.append("login", {"user": "ada"})
        >>> _ = db.events.append("logout", {"user": "ada"})
        >>> db.events.len()
        2
        >>> db.events.get(0).event.payload
        {'user': 'ada'}
        >>> db.events.types()
        ['login', 'logout']
    """

    def append(self, event_type: str, payload: Any) -> Any:
        """Appends one event; returns its sequence + commit receipt.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> db.events.len()
            1
        """
        return self._c.event_append(event_type, payload, **self._scope)

    def append_many(self, entries: Any) -> BatchResult:
        """Appends many events in one commit. Each entry is (event_type, payload) or a dict.

        Examples:
            >>> _ = db.events.append_many([{"event_type": "user.created", "payload": {"id": 1}}, {"event_type": "user.updated", "payload": {"id": 2}}])
            >>> db.events.len()
            2
        """
        return BatchResult.from_wire(
            self._c.event_batch_append(_event_entries(entries), **self._scope)
        )

    def get(self, sequence: int, *, as_of: Optional[int] = None) -> Any:
        """Returns the event at ``sequence``, or ``None`` if out of range.

        The event carries a nondeterministic ``timestamp``/``hash``; access
        stable sub-fields such as ``.event.event_type`` and ``.event.payload``.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> db.events.get(0).event.payload
            {'id': 1}
            >>> db.events.get(999) is None
            True
        """
        result = self._c.event_get(sequence, as_of=as_of, **self._scope)
        return result.value if result.found else None

    def exists(self, sequence: int) -> bool:
        """Whether an event exists at ``sequence``.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> db.events.exists(0)
            True
            >>> db.events.exists(999)
            False
        """
        return self._c.event_exists(sequence, **self._scope)

    def len(self, *, as_of: Optional[int] = None) -> int:
        """Number of events in the log.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> _ = db.events.append("user.updated", {"id": 2})
            >>> db.events.len()
            2
        """
        return self._c.event_count(as_of=as_of, **self._scope).count

    def __len__(self) -> int:
        return self.len()

    def range(
        self,
        start: int,
        *,
        end: Optional[int] = None,
        limit: Optional[int] = None,
        reverse: bool = False,
        event_type: Optional[str] = None,
    ) -> Page:
        """A page of events by sequence, from ``start`` (to ``end`` if given).

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> _ = db.events.append("user.updated", {"id": 2})
            >>> [e.event.payload for e in db.events.range(0)]
            [{'id': 1}, {'id': 2}]
        """
        return Page.from_wire(
            self._c.event_range(
                start,
                _direction(reverse),
                end_seq=end,
                event_type=event_type,
                limit=limit,
                **self._scope,
            )
        )

    def range_by_time(
        self,
        start_ts: int,
        *,
        end_ts: Optional[int] = None,
        limit: Optional[int] = None,
        reverse: bool = False,
        event_type: Optional[str] = None,
    ) -> Page:
        """A page of events by **occurrence time** (the one wall-clock axis).

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> _ = db.events.append("user.updated", {"id": 2})
            >>> [e.event.payload for e in db.events.range_by_time(0)]
            [{'id': 1}, {'id': 2}]
        """
        return Page.from_wire(
            self._c.event_range_time(
                start_ts,
                _direction(reverse),
                end_ts=end_ts,
                event_type=event_type,
                limit=limit,
                **self._scope,
            )
        )

    def list(
        self,
        event_type: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        after_sequence: Optional[int] = None,
        as_of: Optional[int] = None,
    ) -> Page:
        """A page of events, optionally filtered by type / after a sequence.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> _ = db.events.append("user.updated", {"id": 2})
            >>> [e.event.payload for e in db.events.list()]
            [{'id': 1}, {'id': 2}]
        """
        return Page.from_wire(
            self._c.event_list(
                event_type=event_type,
                limit=limit,
                after_sequence=after_sequence,
                as_of=as_of,
                **self._scope,
            )
        )

    def types(self, *, as_of: Optional[int] = None) -> list:
        """The distinct event types present in the log.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> _ = db.events.append("user.updated", {"id": 2})
            >>> db.events.types()
            ['user.created', 'user.updated']
        """
        return self._c.event_types(as_of=as_of, **self._scope).items

    def verify_chain(self) -> Any:
        """Verifies the hash chain; returns its length, validity, and first invalid link.

        Examples:
            >>> _ = db.events.append("user.created", {"id": 1})
            >>> db.events.verify_chain().valid
            True
        """
        return self._c.event_verify_chain(**self._scope)
