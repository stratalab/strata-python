"""``python -m stratadb.init [repo_path]`` — scaffold Strata into a repo.

Thin entry-point shim. The logic lives in :mod:`stratadb._scaffold` so that
``stratadb.init`` remains a callable (``stratadb.init(repo_path)``) rather than
being shadowed by this module.
"""

from __future__ import annotations

import sys

from ._scaffold import init


def _main() -> None:
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    for path, action in init(repo_path):
        print(f"  {action:9} {repo_path.rstrip('/')}/{path}")
    print("Strata scaffolding done — the next agent starts warm.")


if __name__ == "__main__":
    _main()
