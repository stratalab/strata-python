"""``db.branches.diff`` / ``preview`` / ``merge`` — compare, preview, promote.

strata-core v1.1.0 (M12): a fork's changes can be compared against, previewed
against, and promoted into the branch it came from. Key-value, JSON, and vector
data promote; event streams and graphs are compare-only. ``strict`` refuses on
any conflict with zero target mutation; ``source_wins`` applies the source side.
"""

from __future__ import annotations

import pytest

import stratadb
from stratadb import PromotionStrategy, errors


@pytest.fixture()
def db():
    handle = stratadb.open(cache=True)
    yield handle
    handle.close()


def by_capability(comparison, space="default"):
    """{capability: SpaceComparisonItem} for one space of a comparison."""
    return {s.capability.value: s for s in comparison.spaces if s.space == space}


def identities(entities):
    return sorted(e.identity for e in entities)


# --- diff ---------------------------------------------------------------------


def test_diff_reports_added_removed_modified_per_capability(db):
    db.kv.put("keep", "base")
    db.kv.put("gone", "base")
    db.json.set("doc-1", "$", {"title": "base"})
    db.vectors.create_collection("notes", 2)
    db.vectors.upsert("notes", "n1", [0.1, 0.2])
    db.branches.fork("default", "experiment")

    exp = db.at(branch="experiment")
    exp.kv.put("keep", "tuned")  # modified
    exp.kv.put("new", "only-on-fork")  # added
    exp.kv.delete("gone")  # removed
    exp.json.set("doc-2", "$", {"title": "fork"})
    exp.vectors.upsert("notes", "n2", [0.3, 0.4])

    forward = db.branches.diff("default", "experiment")
    assert forward.branch_a == "default" and forward.branch_b == "experiment"
    caps = by_capability(forward)
    kv = caps["key_value"]
    assert identities(kv.added) == [b"new"]
    assert identities(kv.removed) == [b"gone"]
    assert identities(kv.modified) == [b"keep"]
    assert all(e.version > 0 for e in kv.added + kv.removed + kv.modified)
    assert identities(caps["json"].added) == [b"doc-2"]
    assert caps["json"].modified == [] and caps["json"].removed == []
    (vector_added,) = identities(caps["vector"].added)
    assert b"n2" in vector_added

    # Directional: A -> B flips added and removed.
    backward = by_capability(db.branches.diff("experiment", "default"))
    assert identities(backward["key_value"].added) == [b"gone"]
    assert identities(backward["key_value"].removed) == [b"new"]
    assert identities(backward["key_value"].modified) == [b"keep"]

    # Diff is read-only.
    assert db.kv.get("keep") == b"base"
    assert exp.kv.get("keep") == b"tuned"


def test_diff_of_identical_branches_is_empty(db):
    db.kv.put("k", "v")
    db.branches.fork("default", "twin")
    assert db.branches.diff("default", "twin").spaces == []


def test_diff_as_of_compares_both_branches_at_a_commit(db):
    # Mirrors strata-core's branch_diff_reports_changes_and_honors_as_of.
    db.branches.fork("default", "feature")
    first = db.at(branch="feature").kv.put("k", "same")
    db.kv.put("k", "same")
    db.kv.put("k", "changed")

    now = by_capability(db.branches.diff("default", "feature"))
    assert identities(now["key_value"].modified) == [b"k"]
    assert now["key_value"].added == []
    # As of the feature write, default had no `k` yet -> added, not modified.
    then = by_capability(db.branches.diff("default", "feature", as_of=first.commit.timestamp))
    assert identities(then["key_value"].added) == [b"k"]
    assert then["key_value"].modified == []


def test_diff_as_of_must_lie_within_both_branches_history(db):
    # An as_of newer than a branch's latest commit is outside its retained
    # history (the same rule every as_of read follows), so a diff at a
    # timestamp only the *other* branch has reached is refused.
    db.kv.put("seed", "v")
    db.branches.fork("default", "quiet-target")
    later = db.at(branch="quiet-target").kv.put("a", "1")
    with pytest.raises(errors.HistoryUnavailableError) as excinfo:
        db.branches.diff("default", "quiet-target", as_of=later.commit.timestamp)
    assert excinfo.value.code == "history_unavailable.engine.persistence_history"


def test_diff_spans_spaces(db):
    db.branches.fork("default", "experiment")
    db.at(branch="experiment", space="tenant-a").kv.put("k", "v")
    comparison = db.branches.diff("default", "experiment")
    assert [(s.space, s.capability.value) for s in comparison.spaces] == [
        ("tenant-a", "key_value")
    ]


def test_diff_missing_branch(db):
    with pytest.raises(errors.NotFoundError) as excinfo:
        db.branches.diff("default", "ghost")
    assert excinfo.value.code == "not_found.engine.branch"


# --- preview ------------------------------------------------------------------


def test_preview_is_clean_when_only_the_source_changed(db):
    db.kv.put("k", "base")
    db.branches.fork("default", "experiment")
    db.at(branch="experiment").kv.put("k", "tuned")

    preview = db.branches.preview("experiment", "default")
    assert preview.source == "experiment" and preview.target == "default"
    assert preview.strategy == "strict"
    assert preview.conflicts == []
    assert preview.branch_point > 0
    covered = {c.value for c in preview.capabilities_covered}
    unsupported = {c.value for c in preview.capabilities_unsupported}
    assert {"key_value", "json", "vector"} <= covered
    assert {"event", "graph_metadata", "graph_node", "graph_edge", "graph_ontology"} <= unsupported
    assert covered.isdisjoint(unsupported)


def test_preview_reports_conflicts_without_mutating(db):
    db.kv.put("k", "base")
    db.branches.fork("default", "experiment")
    db.at(branch="experiment").kv.put("k", "fork-side")
    db.kv.put("k", "main-side")

    strict = db.branches.preview("experiment", "default")
    (conflict,) = strict.conflicts
    assert conflict.capability == "key_value" and conflict.space == "default"
    assert conflict.identity == b"k"
    assert conflict.kind == "value_divergence"
    assert conflict.source_value == b"fork-side"
    assert conflict.target_value == b"main-side"
    assert conflict.strategy_result == "refused"

    lenient = db.branches.preview("experiment", "default", strategy="source_wins")
    assert lenient.strategy == "source_wins"
    assert [c.strategy_result for c in lenient.conflicts] == ["source_wins"]

    # Preview mutates neither branch and records no lineage.
    assert db.kv.get("k") == b"main-side"
    assert db.at(branch="experiment").kv.get("k") == b"fork-side"
    assert db.branches.get("default").merge_parent is None


def test_preview_modify_delete_divergence(db):
    db.kv.put("k", "base")
    db.branches.fork("default", "experiment")
    db.at(branch="experiment").kv.delete("k")
    db.kv.put("k", "main-side")
    (conflict,) = db.branches.preview("experiment", "default").conflicts
    assert conflict.kind == "modify_delete_divergence"
    assert conflict.source_value is None
    assert conflict.target_value == b"main-side"


# --- merge --------------------------------------------------------------------


def test_merge_applies_the_fork_atomically(db):
    db.kv.put("k", "base")
    db.kv.put("stale", "base")
    db.json.set("doc", "$", {"v": 1})
    db.vectors.create_collection("notes", 2)
    db.branches.fork("default", "experiment")
    exp = db.at(branch="experiment")
    exp.kv.put("k", "tuned")
    exp.kv.delete("stale")
    exp.json.set("doc", "$", {"v": 2})
    exp.vectors.upsert("notes", "n1", [0.5, 0.5])

    outcome = db.branches.merge("experiment", "default")
    assert outcome.source == "experiment" and outcome.target == "default"
    assert outcome.strategy == "strict" and outcome.conflicts == []
    applied = {(e.capability.value, e.identity) for e in outcome.applied}
    assert ("key_value", b"k") in applied
    assert ("json", b"doc") in applied
    assert any(cap == "vector" for cap, _ in applied)
    assert identities(outcome.deleted) == [b"stale"]
    assert outcome.target_version is not None
    assert outcome.target_timestamp is not None

    # The target sees the promoted state as one commit...
    assert db.kv.get("k") == b"tuned"
    assert db.kv.get("stale") is None
    assert db.json.get("doc") == {"v": 2}
    assert db.vectors.get("notes", "n1") is not None
    assert db.kv.get("k", as_of=outcome.target_version) == b"tuned"
    # ...the source is unchanged, and the target records the lineage.
    assert exp.kv.get("k") == b"tuned"
    lineage = db.branches.get("default").merge_parent
    assert lineage is not None
    assert lineage.source_name == "experiment"
    assert lineage.merged_at == outcome.target_version


def test_merge_strict_refuses_and_mutates_nothing(db):
    db.kv.put("k", "base")
    db.kv.put("other", "base")
    db.branches.fork("default", "experiment")
    exp = db.at(branch="experiment")
    exp.kv.put("k", "fork-side")
    exp.kv.put("other", "fork-only-change")
    db.kv.put("k", "main-side")

    with pytest.raises(errors.ConflictError) as excinfo:
        db.branches.merge("experiment", "default")
    assert excinfo.value.code == "conflict.engine.promotion"
    assert excinfo.value.retryable is False

    # Zero target mutation: not even the non-conflicting entry moved.
    assert db.kv.get("k") == b"main-side"
    assert db.kv.get("other") == b"base"
    assert db.branches.get("default").merge_parent is None
    assert db.branches.diff("default", "experiment").spaces != []


def test_merge_source_wins_applies_and_reports_each_conflict(db):
    db.kv.put("k", "base")
    db.kv.put("d", "base")
    db.branches.fork("default", "experiment")
    exp = db.at(branch="experiment")
    exp.kv.put("k", "fork-side")
    exp.kv.delete("d")
    db.kv.put("k", "main-side")
    db.kv.put("d", "main-touched")

    outcome = db.branches.merge("experiment", "default", strategy="source_wins")
    assert outcome.strategy == "source_wins"
    conflicts = {c.identity: c for c in outcome.conflicts}
    assert set(conflicts) == {b"k", b"d"}
    assert conflicts[b"k"].kind == "value_divergence"
    assert conflicts[b"d"].kind == "modify_delete_divergence"
    assert {c.strategy_result for c in outcome.conflicts} == {"source_wins"}
    assert b"k" in identities(outcome.applied)
    assert identities(outcome.deleted) == [b"d"]
    assert db.kv.get("k") == b"fork-side"
    assert db.kv.get("d") is None
    assert outcome.target_version is not None


def test_merge_with_nothing_to_apply_writes_no_commit(db):
    db.kv.put("k", "base")
    db.branches.fork("default", "experiment")
    outcome = db.branches.merge("experiment", "default")
    assert outcome.applied == [] and outcome.deleted == [] and outcome.conflicts == []
    assert outcome.target_version is None and outcome.target_timestamp is None
    assert db.kv.get("k") == b"base"


def test_events_and_graphs_are_compared_but_never_promoted(db):
    db.graphs.create("g")
    db.branches.fork("default", "experiment")
    exp = db.at(branch="experiment")
    exp.events.append("fork.event", {"n": 1})
    exp.graphs.add_node("g", "node-1")
    exp.kv.put("k", "carried")

    diffed = by_capability(db.branches.diff("default", "experiment"))
    assert len(diffed["event"].added) == 1
    (node_added,) = identities(diffed["graph_node"].added)
    assert b"node-1" in node_added

    outcome = db.branches.merge("experiment", "default")
    unsupported = {c.value for c in outcome.capabilities_unsupported}
    assert {"event", "graph_node"} <= unsupported
    assert {e.capability.value for e in outcome.applied} == {"key_value"}
    assert db.kv.get("k") == b"carried"
    assert db.events.len() == 0  # compare-only: not carried over
    assert db.graphs.get_node("g", "node-1") is None
    assert exp.events.len() == 1  # and the source is untouched


def test_repeated_promotion_uses_the_source_frontier(db):
    # strata-core's pre-release audit: a second promotion's merge base is the
    # source frontier, so target-only rows written since are not deleted.
    db.kv.put("k", "base")
    db.branches.fork("default", "experiment")
    exp = db.at(branch="experiment")
    exp.kv.put("k", "first")
    db.branches.merge("experiment", "default")
    db.kv.put("target-only", "kept")
    exp.kv.put("k", "second")

    outcome = db.branches.merge("experiment", "default")
    assert identities(outcome.applied) == [b"k"] and outcome.deleted == []
    assert db.kv.get("k") == b"second"
    assert db.kv.get("target-only") == b"kept"


def test_preview_and_merge_need_shared_fork_lineage(db):
    db.branches.create("island")  # an empty root: no fork lineage with default
    for op in (db.branches.preview, db.branches.merge):
        with pytest.raises(errors.InvalidArgumentError) as excinfo:
            op("island", "default")
        assert excinfo.value.code == "invalid_argument.engine.branch_point"


def test_merge_missing_branch(db):
    with pytest.raises(errors.NotFoundError) as excinfo:
        db.branches.merge("ghost", "default")
    assert excinfo.value.code == "not_found.engine.branch"


def test_strategy_accepts_enum_and_cli_spelling_rejects_garbage(db):
    db.branches.fork("default", "experiment")
    preview = db.branches.preview
    assert preview("experiment", "default", strategy=PromotionStrategy.SOURCE_WINS).strategy == "source_wins"
    assert preview("experiment", "default", strategy="source-wins").strategy == "source_wins"
    assert preview("experiment", "default", strategy=PromotionStrategy.STRICT).strategy == "strict"
    for bad in ("bogus", "", None, 1):
        with pytest.raises(errors.InvalidArgumentError) as excinfo:
            db.branches.merge("experiment", "default", strategy=bad)
        assert excinfo.value.code == "invalid_argument.sdk.command"
    assert stratadb.PromotionStrategy is PromotionStrategy
