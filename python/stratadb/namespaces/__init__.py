"""Curated, handwritten namespaces — the ergonomic public API.

Each namespace is a lossless wrapper over the generated core: it adds Python
affordances (``str | bytes`` coercion, ``as_of`` reads, ``iter_*`` pagination,
``Maybe`` -> ``None``) but never invents behavior the engine does not have.
"""

from .kv import KVNamespace
from .json import JSONNamespace

__all__ = ["KVNamespace", "JSONNamespace"]
