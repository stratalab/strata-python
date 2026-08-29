"""P6 packaging tests: bundled IDL, guide-drift guard, public surface."""

from __future__ import annotations

from pathlib import Path

import stratadb

ROOT = Path(__file__).resolve().parent.parent


def test_command_index_is_bundled():
    index = stratadb.command_index()
    assert index["schema_version"] == "strata.idl.v1"
    assert len(index["commands"]) == 127


def test_agents_guide_matches_bundled():
    # agents_guide() returns the bundled Python SDK guide (drift guard). This is
    # SDK-native Python usage, not the CLI-oriented `strata agents guide`.
    bundled = (ROOT / "python" / "stratadb" / "_data" / "agent-guide.md").read_text(
        encoding="utf-8"
    )
    assert stratadb.agents_guide() == bundled
    assert "db.ai.chat" in bundled and "import stratadb" in bundled


def test_version_is_engine_version():
    assert stratadb.__version__ == "1.0.4"


def test_public_namespaces_present():
    with stratadb.open(cache=True) as db:
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


def test_agents_skill_is_the_vendored_strata_python_skill():
    # agents_skill() serves the strata-agent-skills `strata-python` skill verbatim
    # (tools/vendor_skill.py pins the rev in STRATA_AGENT_SKILLS_REV).
    bundled = (ROOT / "python" / "stratadb" / "_data" / "skill.md").read_text(encoding="utf-8")
    skill = stratadb.agents_skill()
    assert skill == bundled
    assert skill.startswith("---\nname: strata-python\ndescription: ")
    assert 'stratadb-version-range: "1.x"' in skill and stratadb.__version__.startswith("1.")
    assert "stratadb.open(" in skill
    assert "{version}" not in skill
    rev = (ROOT / "STRATA_AGENT_SKILLS_REV").read_text(encoding="utf-8").strip()
    assert len(rev) == 40 and all(c in "0123456789abcdef" for c in rev)
