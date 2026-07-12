"""P6 packaging tests: bundled IDL, guide-drift guard, public surface."""

from __future__ import annotations

from pathlib import Path

import stratadb

ROOT = Path(__file__).resolve().parent.parent


def test_command_index_is_bundled():
    index = stratadb.command_index()
    assert index["schema_version"] == "strata.idl.v1"
    assert len(index["commands"]) == 126


def test_agents_guide_matches_vendored():
    # The guide compiled into the binding must match the vendored source
    # (byte-identical to `strata agents guide` for the pinned version).
    vendored = (ROOT / "idl" / "v1" / "agents-guide.md").read_text()
    assert stratadb.agents_guide() == vendored


def test_version_is_engine_version():
    assert stratadb.__version__ == "1.0.0"


def test_public_namespaces_present():
    with stratadb.Strata(cache=True) as db:
        for name in (
            "kv",
            "json",
            "vectors",
            "events",
            "graphs",
            "branches",
            "spaces",
            "admin",
            "arrow",
        ):
            assert hasattr(db, name), f"missing namespace db.{name}"


def test_module_exports():
    for name in ("Strata", "errors", "filters", "agents_guide", "mcp_config", "command_index"):
        assert hasattr(stratadb, name)
