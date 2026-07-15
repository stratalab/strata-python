"""P2 tests: the IDL-generated core, its guards, and typed round-trips.

- Coverage guard: every catalog command is generated or explicitly allowlisted.
- Drift guard: regenerating produces byte-identical output.
- Round-trips: representative commands per kind decode into typed models.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import stratadb
from stratadb._generated import Commands, catalog, models

ROOT = Path(__file__).resolve().parent.parent
GEN_DIR = ROOT / "python" / "stratadb" / "_generated"


@pytest.fixture()
def commands():
    db = stratadb.open(cache=True)
    yield Commands(db._core)
    db.close()


# --- guards ---------------------------------------------------------------


def test_coverage_accounts_for_every_command():
    index = json.loads((ROOT / "idl" / "v1" / "command-index.json").read_text())
    ids = {c["id"] for c in index["commands"]}
    covered = set(catalog.GENERATED_COMMANDS)
    uncovered = set(catalog.UNCOVERED_COMMANDS)
    assert covered.isdisjoint(uncovered)
    assert covered | uncovered == ids, "some command is neither generated nor allowlisted"
    for cid in covered:
        assert hasattr(Commands, cid.replace(".", "_")), f"missing method for {cid}"


def test_uncovered_is_only_inference_and_hub():
    for cid in catalog.UNCOVERED_COMMANDS:
        assert cid.startswith("inference.") or cid in {"admin.hub_clone", "admin.remote"}


def test_generator_output_is_deterministic():
    before = {p.name: p.read_bytes() for p in GEN_DIR.glob("*.py")}
    subprocess.run([sys.executable, str(ROOT / "tools" / "generate.py")], check=True, cwd=ROOT)
    after = {p.name: p.read_bytes() for p in GEN_DIR.glob("*.py")}
    assert before == after, "regeneration changed output — commit the regenerated _generated/"


# --- typed round-trips ----------------------------------------------------


def test_mutation_and_read_get(commands):
    put = commands.kv_put("greeting", "hello")
    assert isinstance(put.commit, models.CommitReceipt)
    assert put.effect.kind == models.MutationEffectKind.CREATED

    got = commands.kv_get("greeting")
    assert got.found is True
    assert isinstance(got.value, models.VersionedValue)
    assert got.value.value == b"hello"

    assert commands.kv_get("absent").found is False


def test_read_status_scalar(commands):
    commands.kv_put("k", "v")
    assert commands.kv_count() == 1
    assert commands.kv_exists("k") is True


def test_read_page(commands):
    commands.kv_put("a", "1")
    commands.kv_put("b", "2")
    page = commands.kv_scan(limit=1)
    assert len(page.items) == 1
    assert isinstance(page.items[0], models.ScanItem)
    assert page.has_more is True
    assert isinstance(page.cursor, bytes)


def test_read_history(commands):
    commands.kv_put("k", "1")
    commands.kv_put("k", "2")
    hist = commands.kv_history("k")
    assert len(hist.items) == 2
    assert all(isinstance(i, models.HistoryItem) for i in hist.items)


def test_batch(commands):
    batch = commands.kv_batch_put([{"key": "x", "value": "1"}, {"key": "y", "value": "2"}])
    assert batch.status == models.BatchStatus.OK
    assert len(batch.items) == 2
    assert batch.items[0].status == models.BatchItemStatus.OK
    assert batch.items[0].result.key == b"x"


def test_json_and_events_and_graph(commands):
    commands.json_set("doc", "$", {"name": "note", "n": 5})
    jget = commands.json_get("doc", "$")
    assert jget.found is True
    assert jget.value.value == {"name": "note", "n": 5}

    appended = commands.event_append("signup", {"user": "alice"})
    assert appended.sequence == 0
    got = commands.event_get(0)
    assert got.value.event.payload == {"user": "alice"}
    # Events are hash-chained.
    assert got.value.event.previous_hash == "0" * 64

    commands.graph_create("g")
    commands.graph_node_add("g", "n1", properties={"label": "x"})
    node = commands.graph_node_get("g", "n1")
    assert node.found is True
    assert node.value.node_id == "n1"


def test_vector_query_typed(commands):
    commands.vector_collection_create("v", 3, "cosine")
    commands.vector_upsert("v", "k1", [1.0, 0.0, 0.0], metadata={"kind": "note"})
    matches = commands.vector_query("v", [1.0, 0.0, 0.0], 5)
    assert len(matches) == 1
    assert isinstance(matches[0], models.VectorMatch)
    assert matches[0].key == "k1"
