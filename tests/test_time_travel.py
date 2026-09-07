"""Wall-clock time travel: ``as_of_time``, ``committed_at``, and the two clocks.

Engine 1.2.1 (strata-core #3112) added a real UTC instant to every commit and a
wall-clock input to the 31 temporal commands. The whole point of the epic is
that the two clocks stay distinct — ``timestamp``/``as_of`` is a position on the
logical commit timeline, ``committed_at``/``as_of_time`` is when it happened —
so these tests pin the distinction, not just the plumbing.
"""

from __future__ import annotations

import inspect
import time
from pathlib import Path
from datetime import date, datetime, timezone

import pytest

import stratadb
from stratadb import errors

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


@pytest.fixture()
def two_commits(db):
    """A key written twice, with a measurable gap between the instants."""
    first = db.kv.put("k", "v1")
    time.sleep(0.01)
    second = db.kv.put("k", "v2")
    return first, second


# --- committed_at: the instant, beside the counter -------------------------


def test_write_ack_carries_both_clocks(db):
    receipt = db.kv.put("k", "v").commit
    # The counter starts near 1; the instant is epoch micros. Conflating them is
    # what made fresh databases look like they were created in 1969.
    assert receipt.timestamp < 1_000_000
    assert receipt.committed_at > 1_700_000_000_000_000
    moment = stratadb.to_datetime(receipt.committed_at)
    assert moment.tzinfo is timezone.utc
    assert abs((datetime.now(timezone.utc) - moment).total_seconds()) < 60


@pytest.mark.parametrize("primitive", ["kv", "json", "vectors"])
def test_history_rows_carry_committed_at(db, primitive):
    if primitive == "kv":
        db.kv.put("k", "v1"), db.kv.put("k", "v2")
        rows = db.kv.history("k")
    elif primitive == "json":
        db.json.set("d", "$", {"n": 1}), db.json.set("d", "$", {"n": 2})
        rows = db.json.history("d")
    else:
        db.vectors.create_collection("c", 2)
        db.vectors.upsert("c", "k", [1.0, 0.0]), db.vectors.upsert("c", "k", [0.0, 1.0])
        rows = db.vectors.history("c", "k")
    assert len(rows) >= 2
    for row in rows:
        assert stratadb.to_datetime(row.committed_at) is not None
        assert row.timestamp != row.committed_at  # different clocks, never equal


# --- as_of_time resolves to the commit at or before ------------------------


def test_as_of_time_reads_the_commit_at_or_before(db, two_commits):
    first, second = two_commits
    assert db.kv.get("k", as_of_time=first.commit.committed_at) == b"v1"
    assert db.kv.get("k", as_of_time=second.commit.committed_at) == b"v2"
    # Anywhere strictly between the two instants still sees the older commit.
    midpoint = (first.commit.committed_at + second.commit.committed_at) // 2
    assert db.kv.get("k", as_of_time=midpoint) == b"v1"
    # ...and the logical clock reaches the same commit by its own address.
    assert db.kv.get("k", as_of=first.commit.timestamp) == b"v1"


def test_as_of_time_accepts_every_documented_form(db, two_commits):
    first, _ = two_commits
    micros = first.commit.committed_at
    moment = stratadb.to_datetime(micros)
    forms = {
        "micros": micros,
        "aware datetime": moment,
        "naive local datetime": moment.astimezone().replace(tzinfo=None),
        "iso string": moment.isoformat(),
        "zulu string": moment.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
    }
    for label, when in forms.items():
        assert db.kv.get("k", as_of_time=when) == b"v1", label


def test_as_of_time_reaches_every_namespace(db):
    db.json.set("d", "$", {"n": 1})
    db.vectors.create_collection("c", 2)
    db.vectors.upsert("c", "k", [1.0, 0.0])
    db.graphs.create("g")
    db.graphs.add_node("g", "a")
    receipt = db.events.append("tick", {"n": 1}).commit
    when = receipt.committed_at
    # Reads on each primitive accept the wall clock and see the state as of it.
    assert db.json.get("d", "$", as_of_time=when) == {"n": 1}
    assert db.json.count(as_of_time=when) == 1
    assert db.kv.count(as_of_time=when) == 0
    assert db.vectors.count("c", as_of_time=when) == 1
    assert db.graphs.get_node("g", "a", as_of_time=when) is not None
    assert db.events.len(as_of_time=when) == 1
    assert db.events.get(0, as_of_time=when).event.payload == {"n": 1}


def test_a_calendar_date_is_local_midnight_at_the_wire(db, two_commits):
    # A bare date coerces to local midnight, the same instant as the datetime
    # spelling — and reaches the engine identically. (On a database seconds old
    # both fall outside the dated window, which is the engine's call to make,
    # not the coercion's.)
    day = stratadb.to_datetime(two_commits[0].commit.committed_at).astimezone().date()
    midnight = datetime(day.year, day.month, day.day)
    assert stratadb.to_micros(day) == stratadb.to_micros(midnight)

    outcomes = []
    for form in (day, midnight):
        try:
            outcomes.append(("value", db.kv.get("k", as_of_time=form)))
        except errors.HistoryUnavailableError as exc:
            outcomes.append(("refused", exc.code))
    assert outcomes[0] == outcomes[1]


# --- the edges the engine refuses rather than clamping ---------------------


def test_as_of_time_past_the_newest_commit_raises(db, two_commits):
    # The trap worth naming: "now" is past the newest commit, so the most
    # natural-looking call raises instead of returning the latest value.
    for when in (datetime.now(timezone.utc), two_commits[1].commit.committed_at + 1_000_000):
        with pytest.raises(errors.HistoryUnavailableError) as excinfo:
            db.kv.get("k", as_of_time=when)
        assert excinfo.value.code == "history_unavailable.engine.persistence_history"
    assert db.kv.get("k") == b"v2"  # omitting both clocks is how you read latest


def test_as_of_time_before_the_dated_history_raises(db, two_commits):
    with pytest.raises(errors.HistoryUnavailableError):
        db.kv.get("k", as_of_time=0)


# --- the two clocks stay apart ---------------------------------------------


def test_supplying_both_clocks_is_the_engines_refusal(db, two_commits):
    first, _ = two_commits
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.kv.get("k", as_of=first.commit.timestamp, as_of_time=first.commit.committed_at)
    assert excinfo.value.code == "invalid_argument.executor.as_of_conflict"


def test_a_datetime_handed_to_as_of_is_taught_not_serde_rejected(db):
    # Without the guard this is a bare `invalid_argument.sdk.command` from the
    # serializer, which teaches nothing about which clock the caller wanted.
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.kv.get("k", as_of=datetime.now(timezone.utc))
    assert excinfo.value.code == "invalid_argument.sdk.as_of_kind"
    assert "as_of_time" in excinfo.value.hint


@pytest.mark.parametrize(
    "when", ["not-a-date", "2026-13-45", 3.5, b"2026-09-05", object()], ids=str
)
def test_unparseable_as_of_time_is_typed(db, when):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.kv.get("k", as_of_time=when)
    assert excinfo.value.code == "invalid_argument.sdk.as_of_time"


# --- conversions ------------------------------------------------------------


def test_to_micros_round_trips_and_passes_none_through():
    moment = datetime(2026, 9, 5, 15, 30, 45, 123456, tzinfo=timezone.utc)
    assert stratadb.to_datetime(stratadb.to_micros(moment)) == moment
    assert stratadb.to_micros(None) is None
    assert stratadb.to_datetime(None) is None


def test_to_micros_reads_naive_values_as_local_time():
    naive = datetime(2026, 9, 5, 15, 0)
    assert stratadb.to_micros(naive) == stratadb.to_micros(naive.astimezone())
    # A date is local midnight, i.e. the same instant as that day's 00:00 local.
    assert stratadb.to_micros(date(2026, 9, 5)) == stratadb.to_micros(datetime(2026, 9, 5))


def test_to_datetime_rejects_a_non_instant():
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.to_datetime("1788566400000000")
    assert excinfo.value.code == "invalid_argument.sdk.committed_at"


# --- drift guard: the curated layer keeps pace with the IDL ----------------


def test_every_temporal_command_gets_the_wall_clock_from_the_curated_layer():
    # Stronger than the signature check below: every generated command that
    # accepts as_of_time must actually be *called* with it, or the curated
    # method advertises a clock the wire never sees. (This is how db.graphs
    # list/meta/bindings_for_entity were found dropping both clocks.)
    import re

    from stratadb._generated import Commands

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "python" / "stratadb" / "namespaces").glob("*.py")
    )
    gaps = []
    for name, member in inspect.getmembers(Commands, inspect.isfunction):
        if "as_of_time" not in inspect.signature(member).parameters:
            continue
        calls = re.findall(rf"self\._c\.{name}\((?:[^()]|\([^()]*\))*\)", source, re.S)
        if calls and not all("_temporal(as_of, as_of_time)" in call for call in calls):
            gaps.append(name)
    assert not gaps, f"curated call sites drop the wall clock: {gaps}"


def test_every_curated_as_of_method_also_takes_as_of_time(db):
    # The engine gives as_of and as_of_time to exactly the same 31 commands.
    # A curated method that grew one but not the other is a gap a caller meets
    # as a TypeError, so pin the pairing rather than the count.
    exceptions = {
        # branch diff takes no wall clock upstream yet (strata-core #3186).
        ("branches", "diff"),
    }
    checked = 0
    for namespace in ("kv", "json", "vectors", "events", "graphs", "branches"):
        target = getattr(db, namespace)
        for name, member in inspect.getmembers(type(target), inspect.isfunction):
            if name.startswith("_"):
                continue
            params = inspect.signature(member).parameters
            if "as_of" not in params:
                continue
            checked += 1
            if (namespace, name) in exceptions:
                continue
            assert "as_of_time" in params, f"db.{namespace}.{name} takes as_of but not as_of_time"
    assert checked >= 20  # the sweep actually found the temporal surface
