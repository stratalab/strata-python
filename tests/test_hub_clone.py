"""StrataHub clone -> durable open pathway.

The hub client ships in the standard wheel; these run against the hub named by
``STRATA_HUB_URL`` (else the public default) and skip when it is unreachable —
see ``conftest.live_hub_url``. Point them at a local hub with, e.g.::

    STRATA_HUB_URL=http://127.0.0.1:7431 .venv/bin/python -m pytest tests/test_hub_clone.py

The ``titanic`` dataset is a stable demo fixture on the hub (json + kv).
"""

from __future__ import annotations

import stratadb


def test_clone_titanic_into_durable_db(tmp_path, live_hub_url):
    HUB_URL = live_hub_url
    dest = tmp_path / "titanic.strata"
    db = stratadb.clone("titanic", dest, hub_url=HUB_URL)
    try:
        # KV metadata cloned verbatim.
        assert db.kv.get("meta:rows") == b"30"
        assert db.kv.get("meta:source") == b"openml:40945"

        # JSON passenger records are the canonical Titanic rows.
        p1 = db.json.get("passenger:1")
        assert p1["name"] == "Braund, Mr. Owen Harris"
        assert p1["survived"] == 0
        assert db.json.count() == 30

        # The clone recorded its provenance (origin tracking ref).
        origin = db.execute({"type": "remote_get"})["data"]["origin"]
        assert origin["dataset"] == "titanic"
        assert origin["remote_url"] == HUB_URL
        assert origin["manifest_hash"].startswith("blake3:")
    finally:
        db.close()


def test_cloned_db_persists_across_reopen(tmp_path, live_hub_url):
    dest = tmp_path / "titanic.strata"
    stratadb.clone("titanic", dest, hub_url=live_hub_url).close()

    # A fresh open of the cloned path still reads the data (durable, on disk).
    reopened = stratadb.open(dest)
    try:
        assert reopened.json.get("passenger:1")["name"] == "Braund, Mr. Owen Harris"
    finally:
        reopened.close()
