"""Concurrency & process-safety tests for one shared handle (WS1: #31, #32).

#31: two overlapping native calls on one handle used to deadlock and freeze the
whole interpreter (GIL/mutex lock-order inversion). The binding now takes the
lock inside ``allow_threads`` (GIL released), so callers serialize without
wedging the process. Each threaded test joins with a timeout and asserts the
thread finished — a hang is a regression, not an infinite wait.

#32: a handle inherited across ``os.fork()`` used to acknowledge child writes
that never persisted. It now raises ``FailedPreconditionError`` in the child.
"""

from __future__ import annotations

import os
import threading
import time

import pytest

import stratadb


def test_concurrent_writes_one_handle():
    db = stratadb.open(cache=True)
    errors: list[Exception] = []

    def worker(t: int) -> None:
        try:
            for i in range(50):
                db.kv.put(f"k-{t}-{i}", "v")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=30)
        assert not th.is_alive(), "thread hung — #31 GIL/mutex deadlock regression"
    assert not errors, errors
    assert db.kv.count() == 8 * 50
    db.close()


def test_concurrent_reads_one_handle():
    db = stratadb.open(cache=True)
    db.kv.put("k", "v")
    errors: list[Exception] = []

    def reader() -> None:
        try:
            for _ in range(300):
                assert db.kv.get("k") == b"v"
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(2)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=30)
        assert not th.is_alive(), "reader hung — #31 is not write-specific"
    assert not errors, errors
    db.close()


def test_gil_released_during_native_calls():
    # A pure-Python thread must keep making progress while native calls run —
    # proof the GIL is released across the engine call, not held (#31).
    db = stratadb.open(cache=True)
    stop = threading.Event()
    ticks = [0]

    def watchdog() -> None:
        while not stop.is_set():
            ticks[0] += 1
            time.sleep(0.001)

    wd = threading.Thread(target=watchdog)
    wd.start()
    baseline = ticks[0]

    def writer() -> None:
        for i in range(300):
            db.kv.put(f"w{i}", "x")

    writers = [threading.Thread(target=writer) for _ in range(4)]
    for w in writers:
        w.start()
    for w in writers:
        w.join(timeout=30)
        assert not w.is_alive()
    stop.set()
    wd.join(timeout=5)
    assert ticks[0] > baseline, "watchdog frozen — GIL held across native call (#31)"
    db.close()


def test_close_racing_an_operation():
    # close() racing in-flight reads must not deadlock or crash; a "handle is
    # closed" error on the losing calls is acceptable.
    db = stratadb.open(cache=True)
    db.kv.put("k", "v")

    def spin() -> None:
        for _ in range(2000):
            try:
                db.kv.get("k")
            except Exception:  # noqa: BLE001
                pass  # RuntimeError("database handle is closed") is fine

    t = threading.Thread(target=spin)
    t.start()
    time.sleep(0.01)
    db.close()
    t.join(timeout=30)
    assert not t.is_alive(), "close() racing an op hung — #31"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="os.fork() is POSIX-only")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")  # fork() with threads — the hazard under test
def test_fork_child_write_raises(tmp_path):
    # A handle used in a forked child must raise, not silently drop the write
    # (#32). Assertions cannot cross the fork, so the child reports via a pipe
    # and exits with os._exit to skip finally/close in the child.
    db = stratadb.open(str(tmp_path / "db"))
    try:
        db.kv.put("parent", "v")
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:  # child
            os.close(read_fd)
            code = 1  # 1 == BUG: silent success
            try:
                db.kv.put("child", "v")
            except stratadb.errors.FailedPreconditionError as exc:
                code = 0 if exc.code == "failed_precondition.sdk.fork_not_supported" else 2
            except Exception:  # noqa: BLE001
                code = 3
            os.write(write_fd, bytes([code]))
            os.close(write_fd)
            os._exit(0)
        os.close(write_fd)
        got = os.read(read_fd, 1)
        os.close(read_fd)
        os.waitpid(pid, 0)
        assert got == bytes([0]), f"child did not raise the fork error (code={got!r})"
        assert db.kv.get("child") is None, "child write must not reach storage"
        assert db.kv.get("parent") == b"v"
    finally:
        db.close()
