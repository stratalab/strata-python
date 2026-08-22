"""Durable (on-disk) database pathway — the cache-mode suite does not exercise
persistence across a close/reopen. These run unconditionally (no network)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap

import pytest

import stratadb
from stratadb import errors


def test_durable_persistence_round_trips(tmp_path):
    dest = tmp_path / "db"
    db = stratadb.open(dest)
    db.kv.put("k", "v1")
    db.json.set("doc:1", "$", {"a": 1, "b": [2, 3]})
    receipt = db.kv.put("k", "v2")
    db.close()

    # Reopen the same path: committed state survived the close.
    reopened = stratadb.open(dest)
    try:
        assert reopened.kv.get("k") == b"v2"
        assert reopened.json.get("doc:1") == {"a": 1, "b": [2, 3]}
        # Time travel still resolves across the reopen.
        assert reopened.kv.get("k", as_of=receipt.commit.timestamp) == b"v2"
    finally:
        reopened.close()


def test_durable_branches_persist(tmp_path):
    dest = tmp_path / "db"
    db = stratadb.open(dest)
    db.branches.create("feature")
    db.at(branch="feature").kv.put("only", "on-feature")
    db.close()

    reopened = stratadb.open(dest)
    try:
        assert "feature" in [b.name for b in reopened.branches.list()]
        assert reopened.at(branch="feature").kv.get("only") == b"on-feature"
        # The write stayed isolated to its branch.
        assert reopened.kv.get("only") is None
    finally:
        reopened.close()


# --- commit durability attestation (strata-core #2756) ----------------------
# receipt.commit.durability reports what storage attested at ack time:
# "not_durable" (cache), "standard" (durable at the next sync point — the
# documented crash-loss window), "always" (synced before every ack).


def test_receipt_durability_per_mode(tmp_path):
    db = stratadb.open(cache=True)
    assert db.kv.put("k", "v").commit.durability == "not_durable"
    db.close()

    db = stratadb.open(tmp_path / "std")
    assert db.kv.put("k", "v").commit.durability == "standard"
    db.close()

    db = stratadb.open(tmp_path / "alw", durability="always")
    assert db.kv.put("k", "v").commit.durability == "always"
    db.close()


def test_open_durability_validation(tmp_path):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open(tmp_path / "db", durability="sometimes")
    assert excinfo.value.code == "invalid_argument.sdk.command"
    with pytest.raises(errors.InvalidArgumentError):
        stratadb.open(cache=True, durability="always")
    # Explicit "standard" is accepted and means the default.
    db = stratadb.open(tmp_path / "db", durability="standard")
    assert db.kv.put("k", "v").commit.durability == "standard"
    db.close()


def test_open_memory_budget_explicit(tmp_path):
    budget = 64 * 1024 * 1024
    db = stratadb.open(tmp_path / "db", memory_budget=budget)
    try:
        info = db.admin.info().memory_budget
        assert info.source == "explicit"
        assert info.total_bytes == budget
        assert info.usable_host_bytes is None
    finally:
        db.close()
    # Per open, not persisted: a plain reopen derives a budget again.
    db = stratadb.open(tmp_path / "db")
    try:
        info = db.admin.info().memory_budget
        assert info.source in ("derived_from_host", "fixed_default")
        assert info.total_bytes > 0
    finally:
        db.close()


@pytest.mark.skipif(os.name != "posix", reason="multi-process IPC is unix-only")
def test_open_memory_budget_belongs_to_the_owner(tmp_path):
    owner = stratadb.open(tmp_path / "db", memory_budget=64 * 1024 * 1024)
    try:
        # A second open brokers to the owner; its own budget is not applied.
        client = stratadb.open(tmp_path / "db", memory_budget=128 * 1024 * 1024)
        try:
            assert client.admin.ipc_status().is_owner is False
            assert client.admin.info().memory_budget.total_bytes == 64 * 1024 * 1024
            assert client.admin.info().memory_budget.source == "explicit"
        finally:
            client.close()
    finally:
        owner.close()


def test_open_memory_budget_validation(tmp_path):
    # SDK-side guard: a positive int of bytes, never a bool.
    for bad in (0, -1, True, 1.5, "64MiB"):
        with pytest.raises(errors.InvalidArgumentError) as excinfo:
            stratadb.open(tmp_path / "db", memory_budget=bad)
        assert excinfo.value.code == "invalid_argument.sdk.command", bad
    # Cache databases take no budget in this SDK.
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open(cache=True, memory_budget=1 << 20)
    assert excinfo.value.code == "invalid_argument.sdk.command"
    # The engine is the authority on the minimum (1 MiB) and answers typed.
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open(tmp_path / "tiny", memory_budget=1)
    assert excinfo.value.code == "invalid_argument.engine.persistence"


_SIGKILL_WRITER = textwrap.dedent(
    """
    import sys, time
    import stratadb
    db = stratadb.open(sys.argv[1], durability="always")
    for i in range(int(sys.argv[2])):
        receipt = db.kv.put(f"k:{i}", f"v:{i}")
        assert receipt.commit.durability == "always"
    print("ACKNOWLEDGED", flush=True)
    time.sleep(300)  # parent SIGKILLs here; no close()
    """
)


def test_always_mode_acks_survive_sigkill(tmp_path):
    # The #2756 acceptance criterion: every commit acknowledged as "always"
    # survives an immediate SIGKILL (no clean close, no flush opportunity).
    path = str(tmp_path / "db")
    writes = 25
    proc = subprocess.Popen(
        [sys.executable, "-c", _SIGKILL_WRITER, path, str(writes)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "ACKNOWLEDGED"
    finally:
        proc.send_signal(signal.SIGKILL)
        proc.wait()
    reopened = stratadb.open(path)
    try:
        assert reopened.kv.count(prefix="k:") == writes
        assert reopened.kv.get("k:0") == b"v:0"
        assert reopened.kv.get(f"k:{writes - 1}") == f"v:{writes - 1}".encode()
    finally:
        reopened.close()
