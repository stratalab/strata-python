"""``python -m stratadb.demo`` — run the zero-setup end-to-end tour.

Thin entry-point shim. The tour itself lives in :mod:`stratadb._demo` so that
``stratadb.demo`` remains a callable (``stratadb.demo()``) rather than being
shadowed by this module.
"""

from __future__ import annotations

from ._demo import demo

if __name__ == "__main__":
    demo()
