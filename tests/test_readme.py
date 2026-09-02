"""Executes the README's Python code blocks against the built SDK.

The README doubles as the PyPI landing page — the first code a new user
copies. Nothing else runs it, so a surface change can silently strand the
published example (strata-core #2752; this caught a fork-from-"main" crash on
its first run). Same drift-guard spirit as test_agent_guide.py.

Each block runs in a fresh namespace with a pre-opened in-memory ``db`` (so
later sections work standalone), durable-open calls rewritten to a tmp path,
and cloud-key-gated blocks (``db.ai``) skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import stratadb

README = Path(__file__).resolve().parent.parent / "README.md"

BLOCKS = re.findall(r"```python\n(.*?)```", README.read_text(encoding="utf-8"), re.DOTALL)


def test_readme_has_python_blocks():
    assert len(BLOCKS) >= 4, "README lost its Python examples"


@pytest.mark.parametrize("index", range(len(BLOCKS)))
def test_readme_block_runs(index, tmp_path, monkeypatch, request):
    source = BLOCKS[index]
    if "db.ai" in source:
        pytest.skip("inference examples need a provider API key")
    if "db.hub" in source or "stratadb.clone(" in source:
        # Runs for real against the live hub (skips when none is reachable).
        monkeypatch.setenv("STRATA_HUB_URL", request.getfixturevalue("live_hub_url"))
    # The quickstart opens a durable path; run it against a tmp dir instead.
    source = source.replace('"./app-data"', repr(str(tmp_path / "app-data")))
    source = source.replace('"./titanic"', repr(str(tmp_path / "titanic")))

    db = stratadb.open(cache=True)
    # Sections after the quickstart assume prior state; provide the minimum.
    db.kv.put("k", "v0")
    namespace = {"stratadb": stratadb, "db": db}
    try:
        exec(compile(source, f"README.md block {index}", "exec"), namespace)
    finally:
        db.close()
        # A block that opened its own handle must not leak it.
        opened = namespace.get("db")
        if isinstance(opened, stratadb.Strata) and opened is not db:
            opened.close()
