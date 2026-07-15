"""Local (on-device) inference via ``db.ai`` against a downloaded GGUF.

Requires a wheel built with the ``local`` feature — the ``stratadb[cuda]`` /
``[gpu]`` companion wheel, or ``maturin develop --features local`` on a box
where the static llama.cpp links (CPU, PIC). The base cloud wheel refuses local
ops with ``inference.unsupported_operation``, so these skip unless the runtime
is compiled in *and* a local model is present.

Assertions were verified end to end through the ``strata`` CLI (same executor
wire) against TinyLlama + MiniLM on an RTX 4070; the SDK response unwrapping is
shared with the cloud path, which the cloud tests already exercise.
"""

from __future__ import annotations

import pytest

import stratadb

GEN = "local:tinyllama"
EMB = "local:miniLM"


def _local_ready() -> bool:
    try:
        db = stratadb.open(cache=True)
        try:
            # provider_feature_enabled is True only when the local runtime is
            # compiled in; tokenize then also needs the model file present.
            if not db.ai.capability(GEN)["provider_feature_enabled"]:
                return False
            db.ai.tokenize("ping", model=GEN)
            return True
        finally:
            db.close()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _local_ready(),
    reason="local inference runtime + model not available (base wheel is cloud-only)",
)


@pytest.fixture()
def db():
    handle = stratadb.open(cache=True)
    yield handle
    handle.close()


def test_capability_reports_local_runtime(db):
    cap = db.ai.capability(GEN)
    assert cap["provider"] == "local"
    assert cap["provider_feature_enabled"] is True
    assert cap["can_generate"] and cap["can_tokenize"]
    assert cap["requires_api_key"] is False


def test_tokenize_is_deterministic(db):
    assert db.ai.tokenize("Hello, world", model=GEN) == [15043, 29892, 3186]


def test_detokenize_round_trips(db):
    ids = db.ai.tokenize("Hello, world", model=GEN)
    assert db.ai.detokenize(ids, model=GEN) == "Hello, world"


def test_generate_runs_on_device(db):
    result = db.ai.chat("Say hello.", model=GEN, temperature=0.0, max_tokens=8)
    assert isinstance(result.content, str) and result.content
    assert result.finish_reason in {"stop", "length"}


def test_embed_has_model_dimension(db):
    assert len(db.ai.embed("hello", model=EMB).vector) == 384
