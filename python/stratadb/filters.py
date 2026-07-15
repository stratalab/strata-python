"""Metadata filter builder for vector queries.

V1 supports AND-composed equality only. This helper produces the tagged wire
shape so callers never hand-write it::

    from stratadb import filters
    filters.eq("kind", "note") & filters.eq("rank", 5)
    # -> {"conditions": [
    #      {"field": "kind", "op": "eq", "value": {"type": "string", "value": "note"}},
    #      {"field": "rank", "op": "eq", "value": {"type": "integer", "value": 5}},
    #    ]}
"""

from __future__ import annotations

from typing import Any


def _tag(value: Any) -> dict[str, Any]:
    # bool is a subclass of int — check it first.
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    raise TypeError(
        f"unsupported filter value type {type(value).__name__}; "
        "expected str, int, float, or bool"
    )


class Filter:
    """An AND-composed set of equality conditions."""

    __slots__ = ("conditions",)

    def __init__(self, conditions: list[dict[str, Any]] | None = None):
        self.conditions: list[dict[str, Any]] = conditions or []

    def __and__(self, other: "Filter") -> "Filter":
        if not isinstance(other, Filter):
            return NotImplemented
        return Filter(self.conditions + other.conditions)

    def to_wire(self) -> dict[str, Any]:
        return {"conditions": self.conditions}

    def __repr__(self) -> str:
        return f"Filter({self.conditions!r})"


def eq(field: str, value: Any) -> Filter:
    """A single ``field == value`` equality condition."""
    return Filter([{"field": field, "op": "eq", "value": _tag(value)}])


__all__ = ["Filter", "eq"]
