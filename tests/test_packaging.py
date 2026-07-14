"""P6 packaging tests: bundled IDL, guide-drift guard, public surface."""

from __future__ import annotations

from pathlib import Path

import stratadb

ROOT = Path(__file__).resolve().parent.parent


def test_command_index_is_bundled():
    index = stratadb.command_index()
    assert index["schema_version"] == "strata.idl.v1"
    assert len(index["commands"]) == 125


def test_agents_guide_matches_bundled():
    # agents_guide() returns the bundled Python SDK guide (drift guard). This is
    # SDK-native Python usage, not the CLI-oriented `strata agents guide`.
    bundled = (ROOT / "python" / "stratadb" / "_data" / "agent-guide.md").read_text(
        encoding="utf-8"
    )
    assert stratadb.agents_guide() == bundled
    assert "db.ai.chat" in bundled and "import stratadb" in bundled


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
