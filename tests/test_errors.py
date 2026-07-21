"""Error-contract tests (WS2: #51, #52).

Every failure the SDK surfaces must be a ``stratadb.errors.StrataError`` subclass
with a stable ``.code`` — never a bare ``ValueError``/``TypeError``/``KeyError``
that ``except StrataError`` would miss. Assertions match on ``.code``/class,
never on message text.
"""

from __future__ import annotations

import pytest

import stratadb
from stratadb import errors


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


# --- #51: open() surfaces typed errors, not raw StrataNativeError ----------


def test_open_regular_file_raises_typed_error(tmp_path):
    regular_file = tmp_path / "not-a-db"
    regular_file.write_text("i am a file, not a database")
    with pytest.raises(errors.StrataError) as excinfo:
        stratadb.open(str(regular_file))
    exc = excinfo.value
    assert isinstance(exc, errors.StrataError)  # not a raw _stratadb.StrataNativeError
    assert exc.code  # populated, matchable code
    assert not isinstance(exc, ValueError)


def test_double_open_same_durable_path_raises_typed_error(tmp_path):
    path = str(tmp_path / "db")
    first = stratadb.open(path)  # holds the exclusive process lock
    try:
        with pytest.raises(errors.StrataError):
            stratadb.open(path)
    finally:
        first.close()


# --- #52: invalid input raises typed errors, not serde leaks ---------------

# Bucket (a)/(b): serde-rejected args + unserializable payloads → the central
# invalid_argument.sdk.command code.
COMMAND_CASES = [
    ("negative dimension", lambda db: db.vectors.create_collection("x", dimension=-1)),
    ("negative sequence", lambda db: db.events.get(-1)),
    ("negative as_of", lambda db: db.kv.get("k", as_of=-1)),
    ("unknown enum variant", lambda db: db.graphs.analytics.sssp("g", "a", direction="sideways")),
    ("nan in json", lambda db: db.json.set("d", "$", {"x": float("nan")})),
    ("bytes event payload", lambda db: db.events.append("t", b"bytes")),
    ("bogus escape-hatch command", lambda db: db.execute({"type": "not_a_real_command"})),
]


@pytest.mark.parametrize("label, call", COMMAND_CASES, ids=[c[0] for c in COMMAND_CASES])
def test_invalid_input_raises_invalid_argument(db, label, call):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        call(db)
    assert excinfo.value.code == "invalid_argument.sdk.command"


# Bucket (c): batch entries missing a required field → invalid_argument.sdk.entry.
ENTRY_CASES = [
    ("vector entry missing key", lambda db: db.vectors.upsert_many("c", [{"vector": [1.0, 0.0]}])),
    ("json entry missing key", lambda db: db.json.set_many([{"value": 1}])),
    ("event entry missing type", lambda db: db.events.append_many([{"payload": 1}])),
]


@pytest.mark.parametrize("label, call", ENTRY_CASES, ids=[c[0] for c in ENTRY_CASES])
def test_batch_entry_missing_field_raises(db, label, call):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        call(db)
    assert excinfo.value.code == "invalid_argument.sdk.entry"


# Bucket (d): SDK-side argument guard.
def test_fork_version_and_timestamp_is_ambiguous(db):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.branches.fork("default", "x", version=1, timestamp=1)
    assert excinfo.value.code == "invalid_argument.sdk.fork_ambiguous"


# --- regression guards: don't over-catch --------------------------------


def test_valid_command_still_round_trips(db):
    db.kv.put("k", "v")
    assert db.kv.get("k") == b"v"


def test_domain_error_keeps_engine_code(db):
    # A genuine engine error must keep its engine code, not be rewritten to
    # invalid_argument.sdk.command.
    with pytest.raises(errors.NotFoundError) as excinfo:
        db.at(branch="ghost").kv.get("k")
    assert excinfo.value.code == "not_found.engine.branch"


def test_miss_is_not_an_error(db):
    assert db.kv.get("absent") is None


# --- oversized JSON integers rejected at the wire boundary -----------------
# strata-core #2687: the bridge calls guard_json_integers before from_str, so an
# integer outside i64/u64 is rejected instead of being silently coerced to f64.

BIG_INT_CASES = [
    ("json value", lambda db: db.json.set("d", "$", {"n": 2**64})),
    ("event payload", lambda db: db.events.append("e", {"n": 2**100})),
    ("raw execute", lambda db: db.execute({"type": "json_set", "key": "d", "path": "$", "value": {"n": -(2**63) - 1}})),
]


@pytest.mark.parametrize("label, call", BIG_INT_CASES, ids=[c[0] for c in BIG_INT_CASES])
def test_oversized_json_integer_rejected(db, label, call):
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        call(db)
    assert excinfo.value.code == "invalid_argument.executor.json_number"


def test_in_range_int_and_float_survive(db):
    db.json.set("ok", "$", {"n": 2**63 - 1, "f": 1e20})
    assert db.json.get("ok", "$.n") == 2**63 - 1
    assert db.json.get("ok", "$.f") == 1e20
