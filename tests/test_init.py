"""Tests for repo scaffolding (`stratadb.init()` / `python -m stratadb.init`) (#21)."""

from __future__ import annotations

import stratadb


SKILL_REL = ".claude/skills/strata/SKILL.md"


def test_init_creates_breadcrumbs(tmp_path):
    results = dict(stratadb.init(str(tmp_path)))
    assert results == {SKILL_REL: "created", "AGENTS.md": "created", "CLAUDE.md": "created"}

    skill = (tmp_path / SKILL_REL).read_text(encoding="utf-8")
    assert skill == stratadb.agents_skill()  # version-stamped skill, verbatim
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
