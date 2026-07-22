"""P1 foundation tests: native bridge, escape hatch, error model, lifecycle.

These assert the whole stack end-to-end on an in-memory database, matching on
error codes and classes — never on message text.
"""

from __future__ import annotations

import base64

import pytest

import stratadb
from stratadb import errors


def b(text: str) -> str:
    """The base64 KV wire encoding for a string."""
    return base64.b64encode(text.encode()).decode()


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


# --- module surface -------------------------------------------------------


def test_version_matches_engine():
    assert stratadb.__version__ == "1.0.2"


def test_agents_guide_is_embedded():
    guide = stratadb.agents_guide()
    assert guide.startswith("# stratadb")
    assert "db.ai.chat" in guide  # SDK-native Python guide, not the CLI guide
    assert len(guide) > 1000


def test_mcp_config_snippet():
    assert stratadb.mcp_config("./app") == {
        "command": "strata",
        "args": ["./app", "mcp", "serve"],
    }


# --- escape hatch round-trip ---------------------------------------------


def test_put_get_round_trip(db):
    put = db.execute({"type": "kv_put", "key": b("greeting"), "value": b("hello")})
    assert put["type"] == "write_result"
    assert "commit" in put["data"]

    got = db.execute({"type": "kv_get", "key": b("greeting")})
    assert got["data"]["found"] is True
    assert got["data"]["value"]["value"] == b("hello")


def test_miss_is_a_normal_output_not_an_error(db):
    got = db.execute({"type": "kv_get", "key": b("absent")})
    assert got["data"]["found"] is False
    assert got["data"]["value"] is None


# --- typed errors ---------------------------------------------------------


def test_branch_miss_raises_typed_not_found(db):
    with pytest.raises(errors.NotFoundError) as excinfo:
        db.execute({"type": "kv_get", "key": b("greeting"), "branch": "ghost"})
    error = excinfo.value
    assert error.code == "not_found.engine.branch"
    assert error.error_class == "not_found"
    assert error.ref == "https://stratadb.org/e/not_found.engine.branch"
    assert isinstance(error, errors.StrataError)


def test_error_str_renders_code_hint_ref(db):
    with pytest.raises(errors.StrataError) as excinfo:
        db.execute({"type": "kv_get", "key": b("greeting"), "branch": "ghost"})
    rendered = str(excinfo.value)
    assert rendered.startswith("not_found.engine.branch:")
    assert "ref: https://stratadb.org/e/" in rendered


def test_malformed_command_raises_invalid_argument(db):
    # Invalid escape-hatch input now raises a typed StrataError (was a bare
    # ValueError) — see #52.
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        db.execute({"type": "not_a_real_command"})
    assert excinfo.value.code == "invalid_argument.sdk.command"


# --- lifecycle and guards -------------------------------------------------


def test_no_target_without_cache_raises_invalid_argument():
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        stratadb.open()
    assert excinfo.value.code == "invalid_argument.cli.no_database"


def test_from_env_without_var_raises(monkeypatch):
    monkeypatch.delenv("STRATA_DB", raising=False)
    with pytest.raises(errors.InvalidArgumentError):
        stratadb.from_env()


def test_state_namespace_is_reserved_with_teaching_error(db):
    with pytest.raises(errors.UnsupportedError) as excinfo:
        _ = db.state
    assert excinfo.value.code == "unsupported.sdk.state_removed"


def test_context_manager_closes(db_path=None):
    with stratadb.open(cache=True) as database:
        database.execute({"type": "kv_put", "key": b("k"), "value": b("v")})
    # A closed handle rejects further calls.
    with pytest.raises(Exception):
        database.execute({"type": "kv_get", "key": b("k")})


def test_scope_defaults_are_reported():
    database = stratadb.open(cache=True, branch="main")
    try:
        assert database.branch == "main"
        assert isinstance(database.space, str)
    finally:
        database.close()


def test_durable_open_round_trip(tmp_path):
    path = tmp_path / "db"
    database = stratadb.open(str(path))
    try:
        database.execute({"type": "kv_put", "key": b("k"), "value": b("v")})
    finally:
        database.close()
    # Reopen: the value persists.
    reopened = stratadb.open(str(path))
    try:
        got = reopened.execute({"type": "kv_get", "key": b("k")})
        assert got["data"]["found"] is True
    finally:
        reopened.close()
