"""Durable (on-disk) database pathway — the cache-mode suite does not exercise
persistence across a close/reopen. These run unconditionally (no network)."""

from __future__ import annotations

import stratadb


def test_durable_persistence_round_trips(tmp_path):
    dest = tmp_path / "db"
    db = stratadb.Strata(dest)
    db.kv.put("k", "v1")
    db.json.set("doc:1", "$", {"a": 1, "b": [2, 3]})
    receipt = db.kv.put("k", "v2")
    db.close()

    # Reopen the same path: committed state survived the close.
    reopened = stratadb.Strata(dest)
    try:
        assert reopened.kv.get("k") == b"v2"
        assert reopened.json.get("doc:1") == {"a": 1, "b": [2, 3]}
        # Time travel still resolves across the reopen.
        assert reopened.kv.get("k", as_of=receipt.commit.timestamp) == b"v2"
    finally:
        reopened.close()


def test_durable_branches_persist(tmp_path):
    dest = tmp_path / "db"
    db = stratadb.Strata(dest)
    db.branches.create("feature")
    db.at(branch="feature").kv.put("only", "on-feature")
    db.close()

    reopened = stratadb.Strata(dest)
    try:
        assert "feature" in [b.name for b in reopened.branches.list()]
        assert reopened.at(branch="feature").kv.get("only") == b"on-feature"
        # The write stayed isolated to its branch.
        assert reopened.kv.get("only") is None
    finally:
        reopened.close()
