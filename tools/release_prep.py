#!/usr/bin/env python3
"""Pin the engine dependency to a published git rev for a release build.

Local development uses a path dependency to a sibling ``../strata-core``
checkout (fast, no auth). A release build has no sibling, so this rewrites the
``strata-executor`` dependency in ``Cargo.toml`` to the git rev recorded in
``idl/v1/STRATA_CORE_REV``. CI then only needs git auth for the private repo.

Idempotent-ish: run once before ``maturin build`` in the release workflow.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    rev = (ROOT / "idl" / "v1" / "STRATA_CORE_REV").read_text().strip()
    cargo = ROOT / "Cargo.toml"
    text = cargo.read_text()
    git_line = (
        'strata-executor = { git = "https://github.com/stratalab/strata-core", '
        f'rev = "{rev}", default-features = false, features = ["localfs", "arrow"] }}'
    )
    new, count = re.subn(
        r"^strata-executor = \{ (?:path|git) = .*\}$", git_line, text, flags=re.M
    )
    if count != 1:
        print(f"error: expected one strata-executor dependency line, matched {count}", file=sys.stderr)
        return 1
    cargo.write_text(new)
    print(f"pinned strata-executor to strata-core rev {rev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
