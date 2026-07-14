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
    match = re.search(r"^strata-executor = \{ (?P<body>.*) \}$", text, flags=re.M)
    if match is None:
        print("error: strata-executor dependency line not found", file=sys.stderr)
        return 1
    # Preserve the feature set from Cargo.toml (its single source of truth) and
    # only swap the local path source for the pinned git rev. Hardcoding the
    # features here silently drops any the dev build ships (this is how the
    # release wheel once lost `inference`/`hub`).
    feat = re.search(r"features = \[[^\]]*\]", match.group("body"))
    features = feat.group(0) if feat else 'features = ["localfs", "arrow"]'
    git_line = (
        'strata-executor = { git = "https://github.com/stratalab/strata-core", '
        f'rev = "{rev}", default-features = false, {features} }}'
    )
    cargo.write_text(text[: match.start()] + git_line + text[match.end() :])
    print(f"pinned strata-executor to strata-core rev {rev} with {features}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
