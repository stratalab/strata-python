"""Server-side embedding: a collection declares a model, reads and writes take text.

Engine 1.2.2 lets ``vector.collection.create`` / ``set_embedding_model`` record
which model a collection's vectors come from, and ``upsert`` / ``query`` accept
``text=`` where a vector would go. The embedding itself needs a ready model, so
the round trip skips unless one is; everything around it — the declaration, the
guards, the failure modes — runs everywhere.
"""

from __future__ import annotations

import pytest

import stratadb
from stratadb import errors

EMBEDDING_MODEL = "miniLM"  # catalogued local model; 384-d


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


def _embedding_ready() -> bool:
    """Whether this build can actually embed text (local runtime + model file)."""
    try:
        with stratadb.open(cache=True) as probe:
            if not probe.ai.status()["local_execution"]:
                return False
            probe.ai.tokenize("ping", model=EMBEDDING_MODEL)
            return True
    except Exception:
        return False


needs_embedding = pytest.mark.skipif(
    not _embedding_ready(), reason="no ready embedding model (base wheel is cloud-only)"
)


# --- declaring the model ---------------------------------------------------


def test_collection_carries_its_embedding_model(db):
    db.vectors.create_collection("declared", 384, embedding_model=EMBEDDING_MODEL)
    db.vectors.create_collection("plain", 3)

    assert db.vectors.stats("declared").embedding_model == EMBEDDING_MODEL
    assert db.vectors.stats("plain").embedding_model is None
    listed = {c.name: c.embedding_model for c in db.vectors.list_collections()}
    assert listed == {"declared": EMBEDDING_MODEL, "plain": None}


def test_set_embedding_model_declares_it_after_the_fact(db):
    db.vectors.create_collection("late", 384)
    assert db.vectors.stats("late").embedding_model is None

    db.vectors.set_embedding_model("late", EMBEDDING_MODEL)
    assert db.vectors.stats("late").embedding_model == EMBEDDING_MODEL


def test_a_collection_holds_one_models_output(db):
    # Re-declaring a different model is refused: two models' vectors in one
    # collection have distances that cannot be compared. (Declaring where
    # there was none always succeeds, even on a collection with vectors.)
    db.vectors.create_collection("fixed", 384, embedding_model=EMBEDDING_MODEL)
    with pytest.raises(errors.FailedPreconditionError) as excinfo:
        db.vectors.set_embedding_model("fixed", "nomic-embed")
    assert excinfo.value.code == "failed_precondition.engine.embedding_model_mismatch"

    db.vectors.create_collection("undeclared", 3)
    db.vectors.upsert("undeclared", "k", [1.0, 0.0, 0.0])
    db.vectors.set_embedding_model("undeclared", EMBEDDING_MODEL)
    assert db.vectors.stats("undeclared").embedding_model == EMBEDDING_MODEL


# --- the guards, which cost no model ---------------------------------------


def test_text_without_a_declared_model_says_so(db):
    db.vectors.create_collection("plain", 3)
    for call in (
        lambda: db.vectors.upsert("plain", "a", text="hello"),
        lambda: db.vectors.query("plain", text="hello"),
    ):
        with pytest.raises(errors.FailedPreconditionError) as excinfo:
            call()
        assert excinfo.value.code == "failed_precondition.engine.embedding_model_missing"


@pytest.mark.parametrize(
    "call, label",
    [
        (lambda db: db.vectors.upsert("plain", "a", [1.0, 0.0, 0.0], text="hi"), "upsert both"),
        (lambda db: db.vectors.upsert("plain", "a"), "upsert neither"),
        (lambda db: db.vectors.query("plain", [1.0, 0.0, 0.0], text="hi"), "query both"),
        (lambda db: db.vectors.query("plain"), "query neither"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_vector_and_text_are_alternatives(db, call, label):
    # Caught in the SDK, so the caller is told which argument they meant
    # instead of spending a round trip on invalid_argument.executor.vector_input.
    db.vectors.create_collection("plain", 3)
    with pytest.raises(errors.InvalidArgumentError) as excinfo:
        call(db)
    assert excinfo.value.code == "invalid_argument.sdk.command"
    assert "text=" in str(excinfo.value)


# --- the round trip, when a model is actually there ------------------------


@needs_embedding
def test_text_upsert_and_query_round_trip(db):
    db.vectors.create_collection("notes", 384, embedding_model=EMBEDDING_MODEL)
    db.vectors.upsert("notes", "cat", text="a small domestic cat", metadata={"kind": "animal"})
    db.vectors.upsert("notes", "engine", text="a diesel locomotive engine")

    assert db.vectors.count("notes") == 2
    matches = db.vectors.query("notes", text="kitten", k=2)
    assert [m.key for m in matches][0] == "cat"  # nearer than the locomotive
    assert db.vectors.get("notes", "cat").metadata == {"kind": "animal"}


@needs_embedding
def test_a_literal_vector_still_works_on_a_declared_collection(db):
    # Declaring a model does not take the explicit path away.
    db.vectors.create_collection("notes", 384, embedding_model=EMBEDDING_MODEL)
    db.vectors.upsert("notes", "manual", [0.0] * 384)
    assert db.vectors.exists("notes", "manual")
