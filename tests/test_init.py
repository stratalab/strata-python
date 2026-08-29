"""Tests for repo scaffolding (`stratadb.init()` / `python -m stratadb.init`) (#21)."""

from __future__ import annotations

import stratadb


SKILL_REL = ".claude/skills/strata-python/SKILL.md"
LEGACY_REL = ".claude/skills/strata/SKILL.md"


def test_init_creates_breadcrumbs(tmp_path):
    results = dict(stratadb.init(str(tmp_path)))
    assert results == {SKILL_REL: "created", "AGENTS.md": "created", "CLAUDE.md": "created"}

    skill = (tmp_path / SKILL_REL).read_text(encoding="utf-8")
    assert skill == stratadb.agents_skill()  # the vendored strata-python skill, verbatim
    assert skill.startswith("---\nname: strata-python\n")
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "stratadb.agents_guide()" in agents
    assert "python -m stratadb.demo" in agents


def test_init_is_idempotent(tmp_path):
    stratadb.init(str(tmp_path))
    second = dict(stratadb.init(str(tmp_path)))
    assert set(second.values()) == {"unchanged"}


def test_init_preserves_existing_agents_md(tmp_path):
    existing = "# My project\n\nSome existing agent notes.\n"
    (tmp_path / "AGENTS.md").write_text(existing, encoding="utf-8")

    results = dict(stratadb.init(str(tmp_path)))
    assert results["AGENTS.md"] == "updated"

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert existing.strip() in agents  # original content kept
    assert "## Strata (`stratadb`)" in agents  # stanza appended


def test_init_refreshes_stanza_in_place(tmp_path):
    stratadb.init(str(tmp_path))
    # Simulate a stale stanza body; the managed markers must let init refresh it.
    agents = tmp_path / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    begin = text.index("<!-- strata:begin")
    end = text.index("<!-- strata:end -->")
    tampered = text[:begin] + "<!-- strata:begin (managed by stratadb.init — edits inside are overwritten) -->\nstale\n" + text[end:]
    agents.write_text(tampered, encoding="utf-8")

    results = dict(stratadb.init(str(tmp_path)))
    assert results["AGENTS.md"] == "updated"
    refreshed = agents.read_text(encoding="utf-8")
    assert "stale" not in refreshed
    assert refreshed.count("<!-- strata:begin") == 1  # no duplication


def test_init_can_skip_claude_md(tmp_path):
    results = dict(stratadb.init(str(tmp_path), include_claude_md=False))
    assert "CLAUDE.md" not in results
    assert not (tmp_path / "CLAUDE.md").exists()


def test_init_is_a_callable():
    assert callable(stratadb.init)


def test_init_retires_the_legacy_sdk_strata_skill(tmp_path):
    # A pre-1.0.4 SDK/CLI wrote a version-stamped `strata` skill with no provenance.
    legacy = tmp_path / LEGACY_REL
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        "---\nname: strata\ndescription: old\n---\n\n# StrataDB 1.0.3\n\nThis skill matches strata 1.0.3.\n",
        encoding="utf-8",
    )
    results = dict(stratadb.init(str(tmp_path)))
    assert results[LEGACY_REL] == "removed"
    assert not legacy.exists() and not legacy.parent.exists()
    assert (tmp_path / SKILL_REL).exists()
    # Idempotent: nothing to retire the second time.
    assert LEGACY_REL not in dict(stratadb.init(str(tmp_path)))


def test_init_leaves_the_canonical_strata_skill_alone(tmp_path):
    # The strata-agent-skills `strata` skill carries a pinned strata-core-rev; it is not ours.
    canonical = tmp_path / LEGACY_REL
    canonical.parent.mkdir(parents=True)
    text = "---\nname: strata\ndescription: canonical\nmetadata:\n  strata-core-rev: \"abc\"\n---\n\n# Strata\n"
    canonical.write_text(text, encoding="utf-8")
    results = dict(stratadb.init(str(tmp_path)))
    assert LEGACY_REL not in results
    assert canonical.read_text(encoding="utf-8") == text
