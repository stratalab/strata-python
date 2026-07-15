"""Drift guard: every bound curated docstring's ``Examples:`` block must match
what the vendored canonical example spec renders. The examples are authored
once in strata-core (``idl/v1/examples/<id>.yaml``); do not hand-edit the
generated blocks — run ``python tools/generate_examples.py --write`` after the
spec changes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import generate_examples  # noqa: E402


def test_example_docstrings_match_specs():
    assert generate_examples.process(write=False) == 0, (
        "curated example docstrings are stale; run "
        "`python tools/generate_examples.py --write`"
    )
