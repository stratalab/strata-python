"""Phase 4 consistency guard: the SDK agent guide, the CLI agents guide, and
the IDL catalog must cover the same command surface. This side checks that the
curated SDK guide (``stratadb.agents_guide()``) mentions every command family
in the IDL catalog — so a new primitive/namespace cannot silently be missing
from the guide an agent reads. The prose stays hand-written; only its coverage
is guarded.
"""

import json
from pathlib import Path

import stratadb

ROOT = Path(__file__).resolve().parent.parent

# IDL command family -> the curated SDK namespace attribute that surfaces it.
FAMILY_TO_NAMESPACE = {
    "kv": "kv",
    "json": "json",
    "vector": "vectors",
    "event": "events",
    "graph": "graphs",
    "branch": "branches",
    "space": "spaces",
    "admin": "admin",
    "arrow": "arrow",
    "inference": "ai",
}


def _families() -> set[str]:
    index = json.loads((ROOT / "idl" / "v1" / "command-index.json").read_text())
    return {command["family"] for command in index["commands"]}


def test_family_namespace_map_covers_the_catalog():
    # A newly added IDL family must be mapped to a namespace explicitly, not
    # silently skipped by the coverage guard below.
    unmapped = _families() - set(FAMILY_TO_NAMESPACE)
    assert not unmapped, f"IDL families with no namespace mapping: {sorted(unmapped)}"


def test_mapped_namespaces_exist_on_the_handle():
    db = stratadb.open(cache=True)
    missing = [ns for ns in FAMILY_TO_NAMESPACE.values() if not hasattr(db, ns)]
    db.close()
    assert not missing, f"guide map names namespaces absent from Strata: {missing}"


def test_agent_guide_covers_every_family():
    guide = stratadb.agents_guide()
    missing = [
        f"{family} -> db.{FAMILY_TO_NAMESPACE[family]}"
        for family in sorted(_families())
        if f"db.{FAMILY_TO_NAMESPACE[family]}" not in guide
    ]
    assert not missing, f"agent guide does not cover: {missing}"
