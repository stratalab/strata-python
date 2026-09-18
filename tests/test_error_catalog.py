"""The SDK's own error codes are catalogued, and cannot be raised without it.

The engine publishes its registry through ``strata agents errors``; the SDK's
client-side codes had no catalog, so stratadb.org had nothing to generate
``/e/<code>`` pages from and every ``.sdk.`` ref 404'd (#87).

A catalog is only worth publishing if it is complete, and the reason the site
could not build one by scraping is the reason these tests exist: three of the
codes are raised through module constants, so a literal-only scan finds ten of
thirteen and reports that as the whole set — silently. The sweep below walks
the AST for *every* code-shaped string in the hand-written package, so a new
code cannot be added without landing in the table.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

import stratadb
from stratadb import errors
from stratadb._catalog import SDK_ERRORS

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "python" / "stratadb"
CODE_SHAPE = re.compile(r"^[a-z_]+\.[a-z_]+\.[a-z_0-9]+$")
STATUS_FIELDS = {
    "code",
    "class",
    "area",
    "message",
    "hint",
    "retry_policy",
    "commit_outcome",
    "ref",
}


def _codes_in_source() -> dict[str, set[str]]:
    """Every code-shaped literal in the hand-written package, by file.

    Finds them wherever they appear — a ``client_error`` argument, a module
    constant, a dict value — because the point is completeness, not a
    convention about how a code reaches its raise site.
    """
    found: dict[str, set[str]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        if "_generated" in path.parts or path.name == "_catalog.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if CODE_SHAPE.match(node.value):
                    found.setdefault(node.value, set()).add(path.name)
    return found


def test_every_code_the_package_raises_is_catalogued():
    raised = _codes_in_source()
    missing = sorted(set(raised) - set(SDK_ERRORS))
    assert not missing, (
        "codes raised but not catalogued (add them to python/stratadb/_catalog.py): "
        + ", ".join(f"{code} [{', '.join(sorted(raised[code]))}]" for code in missing)
    )


def test_the_catalog_has_no_codes_the_package_never_raises():
    # The other direction: a code deleted from the source leaves a page on the
    # site describing something that cannot happen.
    raised = _codes_in_source()
    stale = sorted(set(SDK_ERRORS) - set(raised))
    assert not stale, f"catalogued but never raised: {stale}"


def test_the_catalog_is_not_only_sdk_area():
    # invalid_argument.cli.no_database is the CLI's code, reused because
    # from_env() implements the same targeting contract. Any consumer (or fix)
    # filtering on ".sdk." drops it — which is how it went unlisted in #87.
    areas = {row["area"] for row in errors.catalog()}
    assert areas == {"sdk", "cli"}
    assert "invalid_argument.cli.no_database" in SDK_ERRORS


@pytest.mark.parametrize("row", errors.catalog(), ids=lambda row: row["code"])
def test_each_entry_is_publishable(row):
    # The shape stratadb.org renders from: the engine registry's fields, so
    # the site can merge the two sources without special-casing ours.
    assert set(row) == STATUS_FIELDS
    assert row["class"] == row["code"].split(".", 1)[0]
    assert row["ref"] == f"https://stratadb.org/e/{row['code']}"
    assert row["message"].endswith("."), "message reads as a sentence"
    assert row["hint"].endswith("."), "hint reads as a sentence"
    assert row["retry_policy"] in (
        "never",
        "after_state_change",
        "same_request",
        "idempotent_only",
        "unknown",
    )
    assert row["commit_outcome"] in (
        "not_started",
        "definitely_not_committed",
        "maybe_committed",
        "not_applicable",
    )


def test_a_raised_error_agrees_with_its_catalog_row():
    with stratadb.open(cache=True) as db:
        with pytest.raises(errors.InvalidArgumentError) as excinfo:
            db.kv.keys(limit=0)
    raised = excinfo.value
    row = next(r for r in errors.catalog() if r["code"] == raised.code)
    assert raised.error_class == row["class"]
    assert raised.retry_policy == row["retry_policy"]
    assert raised.ref == row["ref"]
    # The raise site's message is the specific one; the catalog's is generic.
    assert "0" in raised.message and raised.message != row["message"]


def test_bundled_json_matches_the_table():
    # tools/export_errors.py writes it; the wheel ships it beside the command
    # index so a consumer (stratadb.org) can read it without running Python.
    bundled = json.loads(
        (PACKAGE / "_data" / "sdk-errors.json").read_text(encoding="utf-8")
    )
    assert bundled == {"count": len(SDK_ERRORS), "errors": errors.catalog()}
