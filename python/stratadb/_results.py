"""Curated, stable result types returned by the namespace layer.

The generated core returns faithful per-command decodes; these thin wrappers
give the ergonomic surface the docs promise — iterable pages, samples, and a
single ``BatchResult`` shape (the generated batch classes are named per item
payload, e.g. ``BatchResult2``; this normalizes them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, List, Optional


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


@dataclass
class Page:
    """One page of a listing, plus an opaque cursor for the next page.

    Iterable and indexable over ``items``; pass ``cursor`` back verbatim to
    continue, or use the namespace's ``iter_*`` to auto-paginate.
    """

    items: List[Any]
    has_more: bool
    cursor: Optional[Any] = None

    def __iter__(self) -> Iterator[Any]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Any:
        return self.items[index]

    @classmethod
    def from_wire(cls, record: Any) -> "Page":
        return cls(items=list(record.items), has_more=bool(record.has_more), cursor=record.cursor)


@dataclass
class Sample:
    """A representative sample of rows plus the total population size."""

    items: List[Any]
    total_count: int

    def __iter__(self) -> Iterator[Any]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Any:
        return self.items[index]

    @classmethod
    def from_wire(cls, record: Any) -> "Sample":
        return cls(items=list(record.items), total_count=int(record.total_count))


@dataclass
class BatchItem:
    """One positional result within a batch."""

    index: int
    status: str
    applied: bool
    result: Any = None
    error: Any = None
    commit: Any = None
    effect: Any = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class BatchResult:
    """The outcome of a batch command: a batch-level status and per-item results."""

    status: str
    mode: str
    applied: bool
    items: List[BatchItem] = field(default_factory=list)
    commit: Any = None

    def __iter__(self) -> Iterator[BatchItem]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> BatchItem:
        return self.items[index]

    @classmethod
    def from_wire(cls, generated: Any) -> "BatchResult":
        items = [
            BatchItem(
                index=item.index,
                status=_enum_value(item.status),
                applied=item.applied,
                result=item.result,
                error=item.error,
                commit=item.commit,
                effect=item.effect,
            )
            for item in sorted(generated.items, key=lambda i: i.index)
        ]
        return cls(
            status=_enum_value(generated.status),
            mode=_enum_value(generated.mode),
            applied=generated.applied,
            items=items,
            commit=generated.commit,
        )


__all__ = ["Page", "Sample", "BatchItem", "BatchResult"]
