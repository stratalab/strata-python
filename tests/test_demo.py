"""Smoke test for the runnable tour (`stratadb.demo()` / `python -m stratadb.demo`).

The tour exercises every primitive against a fresh in-memory database, so running
it to completion is itself a broad smoke test of the SDK surface (#26).
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys

import stratadb


SECTIONS = (
    "Key-value — db.kv",
    "JSON documents — db.json",
    "Vectors — db.vectors",
    "Events — db.events",
    "Graph — db.graphs",
    "Branches & time travel",
)


def test_demo_is_a_callable():
    assert callable(stratadb.demo)


def test_demo_runs_and_covers_every_section():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        stratadb.demo()
    text = out.getvalue()
    for section in SECTIONS:
        assert section in text, f"demo output missing section: {section}"
    assert "Done" in text
    # A few concrete results the tour prints, proving it really ran keyless.
    assert "b'hello'" in text  # kv.get
    assert "['grace', 'linus']" in text  # graph neighbors via .node_id
    assert "on-branch" in text  # branch isolation


def test_demo_module_runs_cleanly_via_dash_m():
    # `python -m stratadb.demo` must exit 0 with no RuntimeWarning (the submodule
    # is not pre-imported by the package, so runpy runs it fresh).
    result = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-m", "stratadb.demo"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
