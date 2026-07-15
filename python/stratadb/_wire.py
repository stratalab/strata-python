"""Hand-written wire helpers shared by the generated core.

These are stable primitives the generated ``models``/``commands`` modules lean
on: base64 for the ``Bytes`` wire type, and a light attribute-accessible
mapping for the structural envelopes (``Maybe``, page, batch) that specialize
per command and so are decoded inline rather than as named models.
"""

from __future__ import annotations

import base64
from typing import Any


def b64e(value: str | bytes | bytearray) -> str:
    """Encodes a key/value to the base64 ``Bytes`` wire form (str -> UTF-8)."""
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, (bytes, bytearray)):
        raise TypeError(f"expected str or bytes, got {type(value).__name__}")
    return base64.b64encode(bytes(value)).decode("ascii")


def b64d(value: str) -> bytes:
    """Decodes a base64 ``Bytes`` wire value to Python ``bytes``."""
    return base64.b64decode(value)


class Record:
    """An attribute- and item-accessible view over a structural wire payload.

    Deliberately not a ``dict`` subclass: wire fields like ``items``, ``keys``,
    and ``values`` would otherwise be shadowed by dict methods. Access fields
    with ``record.field`` or ``record["field"]``; iterate keys with ``in`` /
    ``iter``; ``to_dict()`` returns the underlying mapping.
    """

    __slots__ = ("_fields",)

    def __init__(self, fields: dict[str, Any]):
        object.__setattr__(self, "_fields", fields)

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, "_fields")[name]
        except KeyError:
            raise AttributeError(name) from None

    def __getitem__(self, name: str) -> Any:
        return self._fields[name]

    def __contains__(self, name: str) -> bool:
        return name in self._fields

    def __iter__(self):
        return iter(self._fields)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._fields)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Record):
            return self._fields == other._fields
        if isinstance(other, dict):
            return self._fields == other
        return NotImplemented

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}={v!r}" for k, v in self._fields.items())
        return f"Record({inner})"
