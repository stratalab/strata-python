"""Curated, handwritten namespaces — the ergonomic public API.

Each namespace is a lossless wrapper over the generated core: it adds Python
affordances (``str | bytes`` coercion, ``as_of`` reads, ``iter_*`` pagination,
``Maybe`` -> ``None``) but never invents behavior the engine does not have.
"""

from .kv import KVNamespace
from .json import JSONNamespace
from .vectors import VectorsNamespace
from .events import EventsNamespace
from .graphs import GraphsNamespace
from .branches import BranchesNamespace
from .spaces import SpacesNamespace
from .admin import AdminNamespace
from .arrow import ArrowNamespace

__all__ = [
    "KVNamespace",
    "JSONNamespace",
    "VectorsNamespace",
    "EventsNamespace",
    "GraphsNamespace",
    "BranchesNamespace",
    "SpacesNamespace",
    "AdminNamespace",
    "ArrowNamespace",
]
