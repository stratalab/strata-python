"""Multi-process IPC: transparent brokering to a same-machine owner.

A durable open defaults to ``ipc="host"`` — the first opener owns the store and
hosts a Unix-domain socket; later opens (same or another process) broker to the
owner instead of colliding on the writer lock (strata-core #2840-#2843; the SDK
side of the exclusive-open gap #66 / core #2759). ``db.admin.ipc_status()``
reports the live topology.

IPC is unix-only; these are skipped elsewhere.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time

import pytest

import stratadb
from stratadb import errors

pytestmark = pytest.mark.skipif(os.name != "posix", reason="multi-process IPC is unix-only")


@pytest.fixture()
def durable_path(tmp_path):
    return str(tmp_path / "db")


# --- single-process topology -------------------------------------------------


def test_host_default_hosts_a_socket(durable_path):
    db = stratadb.open(durable_path)  # ipc="host" is the default
    try:
        status = db.admin.ipc_status()
        assert status.is_owner is True
        assert status.hosting is True
        assert status.owner_pid == os.getpid()
        assert status.socket_path  # a real socket path
    finally:
        db.close()


def test_off_mode_does_not_host(durable_path):
    db = stratadb.open(durable_path, ipc="off")
    try:
        status = db.admin.ipc_status()
        assert status.is_owner is True
        assert status.hosting is False
    finally:
        db.close()


def test_cache_never_brokers():
    db = stratadb.open(cache=True)
    try:
        status = db.admin.ipc_status()
        assert status.hosting is False
        assert status.client_count == 0
    finally:
        db.close()


def test_same_process_second_open_brokers_in(durable_path):
    owner = stratadb.open(durable_path)  # host
    try:
        owner.kv.put("k", "owner")
        client = stratadb.open(durable_path)  # brokers in rather than colliding
        try:
            assert client.admin.ipc_status().is_owner is False
            assert client.kv.get("k") == b"owner"  # reads through the broker
            client.kv.put("k2", "client")
            assert owner.kv.get("k2") == b"client"  # owner sees the client's write
        finally:
            client.close()
    finally:
        owner.close()


def test_off_mode_is_exclusive(durable_path):
    first = stratadb.open(durable_path, ipc="off")
    try:
        with pytest.raises(errors.StrataError):
            stratadb.open(durable_path, ipc="off")
    finally:
        first.close()


def test_ipc_stop_unhosts_but_keeps_store_usable(durable_path):
    db = stratadb.open(durable_path)  # host
    try:
        assert db.admin.ipc_status().hosting is True
        assert db.admin.ipc_stop().stopped is True  # a running host was stopped
        assert db.admin.ipc_status().hosting is False
        assert db.admin.ipc_stop().stopped is False  # nothing left to stop
        # Unhosting only stops brokering; the store is still usable in-process.
        db.kv.put("k", "v")
        assert db.kv.get("k") == b"v"
    finally:
        db.close()


def test_ipc_stop_when_not_hosting_is_false(durable_path):
    db = stratadb.open(durable_path, ipc="off")  # never hosts
    try:
        assert db.admin.ipc_stop().stopped is False
    finally:
        db.close()


def test_stopped_host_no_longer_accepts_new_clients(durable_path):
    owner = stratadb.open(durable_path)  # host
    try:
        owner.admin.ipc_stop()  # drop the socket; owner keeps the writer lock
        # A new opener can neither broker (no socket) nor win the lock (held).
        with pytest.raises(errors.StrataError):
            stratadb.open(durable_path, ipc="off")
    finally:
        owner.close()


def test_invalid_ipc_mode_is_typed(durable_path):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open(durable_path, ipc="sometimes")
    assert excinfo.value.code == "invalid_argument.sdk.command"


def test_ipc_with_cache_is_rejected():
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open(cache=True, ipc="host")
    assert excinfo.value.code == "invalid_argument.sdk.command"


# --- cross-process brokering -------------------------------------------------

_HOST = textwrap.dedent(
    """
    import sys, time
    import stratadb
    db = stratadb.open(sys.argv[1], ipc="host")
    db.kv.put("from_host", "H")
    status = db.admin.ipc_status()
    print(f"READY {status.owner_pid}", flush=True)
    time.sleep(60)
    """
)


def test_client_brokers_to_a_separate_host_process(durable_path):
    host = subprocess.Popen(
        [sys.executable, "-c", _HOST, durable_path],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = host.stdout.readline().strip()
        assert line.startswith("READY"), f"host failed to start: {line!r}"
        host_pid = int(line.split()[1])

        client = stratadb.open(durable_path, ipc="client")
        try:
            status = client.admin.ipc_status()
            assert status.is_owner is False  # the other process owns it
            assert status.hosting is True  # a socket is being hosted (by the owner)
            assert status.owner_pid == host_pid
            # Read the host's write, and write back through the broker.
            assert client.kv.get("from_host") == b"H"
            client.kv.put("from_client", "C")
            assert client.kv.get("from_client") == b"C"
        finally:
            client.close()
    finally:
        host.terminate()
        host.wait()
