#!/usr/bin/env python3
"""Write the SDK's own error catalog to ``_data/sdk-errors.json``.

The engine's codes reach consumers through ``strata agents errors --json``;
the SDK's client-side codes had no equivalent, so stratadb.org had nothing to
generate ``/e/<code>`` pages from and every ``.sdk.`` ref 404'd
(stratalab/strata-python#87, stratalab/stratadb.org#23).

The table in ``python/stratadb/_catalog.py`` is the source of truth; this
renders it to the same JSON envelope the engine emits (``{count, errors}``),
shipped in the wheel beside the command index.

  python tools/export_errors.py            # write
  python tools/export_errors.py --check    # fail if the committed file is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from stratadb._catalog import catalog  # noqa: E402

OUT = ROOT / "python" / "stratadb" / "_data" / "sdk-errors.json"


def render() -> str:
    rows = catalog()
    return json.dumps({"count": len(rows), "errors": rows}, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    rendered = render()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"stale {OUT.relative_to(ROOT)} (run python tools/export_errors.py)",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT.name}: fresh, {json.loads(rendered)['count']} code(s)")
        return 0
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {json.loads(rendered)['count']} code(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
