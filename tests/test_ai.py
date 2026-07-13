"""Phase F tests: the ``db.ai`` namespace — request building, result wrappers,
provider-key resolution, and no-network integration.

Live cloud calls are exercised separately (they need real API keys); these run
offline and assert on codes/classes, never message text.
"""

from __future__ import annotations

import pytest

import stratadb
from stratadb import errors
from stratadb.namespaces import ai as ai_mod


@pytest.fixture()
def db():
    database = stratadb.Strata(cache=True)
    yield database
    database.close()


@pytest.fixture(autouse=True)
def _reset_key_cache():
    # The config->env load runs once per process; reset it so key tests are
    # independent.
    ai_mod._keys_loaded = False
    yield
    ai_mod._keys_loaded = False


# --- request building (pure) ----------------------------------------------


def test_chat_request_messages_and_knobs():
    req = ai_mod._build_chat_request(
        "hello", None, None, None, {"temperature": 0.7, "max_tokens": 10, "top_k": 40}
    )
    assert req["messages"] == [{"role": "user", "content": "hello"}]
    assert req["temperature"] == 0.7 and req["max_tokens"] == 10 and req["top_k"] == 40
    assert "prompt" not in req
    # None-valued knobs are dropped.
    assert "seed" not in req


def test_chat_request_prompt_and_tools():
    req = ai_mod._build_chat_request(
        None,
        "once upon",
        None,
        None,
        {"tools": [{"type": "function", "function": {"name": "f"}}], "tool_choice": "auto"},
    )
    assert req["prompt"] == "once upon"
    assert req["tools"][0]["function"]["name"] == "f"
    assert req["tool_choice"] == "auto"
    assert "messages" not in req


def test_response_format_variants():
    bare = ai_mod._response_format(None, {"type": "object"})
    assert bare == {"type": "json_schema", "json_schema": {"name": "response", "schema": {"type": "object"}}}
    named = ai_mod._response_format(None, {"name": "person", "schema": {"type": "object"}})
    assert named["json_schema"]["name"] == "person"
    assert ai_mod._response_format("json_object", None) == {"type": "json_object"}
    assert ai_mod._response_format(None, None) is None


def test_message_normalization():
    assert ai_mod._normalize_messages("hi") == [{"role": "user", "content": "hi"}]
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert ai_mod._normalize_messages(msgs) == msgs


# --- result wrappers ------------------------------------------------------


def test_chat_completion_wrapper():
    r = ai_mod.ChatCompletion._from(
        {
            "model": "m",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "hi", "tool_calls": [{"x": 1}]},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 3},
        }
    )
    assert r.content == "hi"
    assert r.finish_reason == "stop"
    assert r.tool_calls == [{"x": 1}]
    assert str(r) == "hi"
    assert r.usage["total_tokens"] == 3


def test_embeddings_wrapper_orders_by_index():
    e = ai_mod.Embeddings._from(
        {
            "model": "m",
            "data": [{"index": 1, "embedding": [9.0]}, {"index": 0, "embedding": [1.0]}],
            "dimension": 1,
            "usage": {},
        }
    )
    assert e.vectors == [[1.0], [9.0]]
    assert e.vector == [1.0]
    assert len(e) == 2
    assert e[0] == [1.0]
    assert list(e) == [[1.0], [9.0]]


# --- key resolution -------------------------------------------------------


def test_read_config_keys(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[hub]\nurl = "https://example.com"\n\n'
        '[providers.openai]\napi_key = "sk-x"\n\n'
        '[providers.google]\napi_key = "g-y"\n'
    )
    keys = ai_mod._read_config_keys(str(path))
    assert keys == {"openai": "sk-x", "google": "g-y"}


def test_env_overrides_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "strata"
    cfg.mkdir()
    (cfg / "config.toml").write_text('[providers.openai]\napi_key = "from-config"\n')
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    ai_mod._keys_loaded = False
    ai_mod._ensure_provider_keys()
    # Env var was already set → config must not clobber it.
    import os

    assert os.environ["OPENAI_API_KEY"] == "from-env"


# --- integration (no network) ---------------------------------------------


def test_capability_no_network(db):
    cap = db.ai.capability("openai:gpt-4o-mini")
    assert cap["provider"] == "openai"
    assert cap["supports_tools"] is True
    assert cap["requires_api_key"] is True


def test_missing_key_raises_typed_error(db, monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # empty config
    ai_mod._keys_loaded = False
    with pytest.raises(errors.StrataError) as excinfo:
        db.ai.chat("hi", model="openai:gpt-4o-mini", max_tokens=5)
    assert excinfo.value.code == "inference.missing_api_key"
    assert isinstance(excinfo.value, errors.FailedPreconditionError)


def test_model_handle_injects_config():
    class FakeAi:
        def chat(self, messages, *, model, **kwargs):
            return messages, model, kwargs

    handle = ai_mod.AiModel(FakeAi(), "local:qwen", {"n_ctx": 8192})
    messages, model, kwargs = handle.chat("hi")
    assert model == "local:qwen"
    assert kwargs["model_config"] == {"n_ctx": 8192}
