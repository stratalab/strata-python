"""Runs the doctest Examples in each curated namespace against the built
extension. Agents copy these examples out of site-packages, so a stale example
is worse than none — CI keeps them honest."""
import doctest
import importlib
import pytest
import stratadb

NAMESPACES = ["kv", "json", "vectors", "events", "graphs", "branches", "spaces", "admin", "arrow", "ai"]
OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE


@pytest.mark.parametrize("name", NAMESPACES)
def test_namespace_doctests(name):
    module = importlib.import_module(f"stratadb.namespaces.{name}")
    runner = doctest.DocTestRunner(optionflags=OPTIONFLAGS)
    finder = doctest.DocTestFinder()
    found = 0
    for test in finder.find(module, module.__name__):
        if not test.examples:
            continue
        found += 1
        db = stratadb.Strata(cache=True)          # fresh, isolated db per docstring
        test.globs.update({"db": db, "stratadb": stratadb})
        runner.run(test)
        db.close()
    results = runner.summarize(verbose=False)
    assert results.failed == 0, f"{name}: {results.failed} doctest failure(s)"
    assert found > 0, f"{name}: no doctest Examples found"
