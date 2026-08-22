"""Phase 4 consistency guard: the SDK agent guide, the CLI agents guide, and
the IDL catalog must cover the same command surface. This side checks that the
curated SDK guide (``stratadb.agents_guide()``) mentions every command family
in the IDL catalog — so a new primitive/namespace cannot silently be missing
from the guide an agent reads. The prose stays hand-written; only its coverage
is guarded.
"""

import json
import re
from pathlib import Path

import pytest

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


# --- the guide's Python blocks must run (same drift guard as test_readme.py) ---

GUIDE = ROOT / "python" / "stratadb" / "_data" / "agent-guide.md"
BLOCKS = re.findall(r"```python\n(.*?)```", GUIDE.read_text(encoding="utf-8"), re.DOTALL)


def test_agent_guide_has_python_blocks():
    assert len(BLOCKS) >= 8, "agent guide lost its Python examples"


@pytest.mark.parametrize("index", range(len(BLOCKS)))
def test_agent_guide_block_runs(index, tmp_path, monkeypatch):
    """Every snippet in the guide agents read *first* executes against the built
    SDK. Caught on its first run: the Install & open sequence orphaned a brokered
    handle by rebinding the owner (unavailable.executor.ipc_transport)."""
    source = BLOCKS[index]
    if "db.ai.chat" in source or "db.ai.embed" in source:
        pytest.skip("inference examples need a provider API key")
    # Durable opens ("./app-data") and Arrow files land in a scratch cwd;
    # from_env() needs a target.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STRATA_DB", str(tmp_path / "env-db"))
    source = source.replace("    ...", "    pass")

    db = stratadb.open(cache=True)
    # Later sections assume prior state; provide the minimum without colliding
    # with a block that creates the same thing itself.
    db.kv.put("k", "v0")
    if 'graphs.create("social")' not in source:
        db.graphs.create("social")
    namespace = {"stratadb": stratadb, "db": db}
    try:
        exec(compile(source, f"agent-guide.md block {index}", "exec"), namespace)
    finally:
        for value in list(namespace.values()):
            if isinstance(value, stratadb.Strata):
                value.close()
        db.close()
