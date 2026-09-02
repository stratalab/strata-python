"""``db.hub`` — StrataHub browsing — and ``stratadb.clone(progress=...)``.

The offline half pins the SDK-side surface (namespace, exports, argument
coercion and validation). The live half runs against a real hub (see
``conftest.live_hub_url``): the ``titanic`` dataset is a stable demo fixture
there (json + kv, 3 objects, one ``main`` branch).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import stratadb
from stratadb import HubCloneProgress, HubDatasetSort, errors
from stratadb._generated import Commands, models
from stratadb.namespaces.hub import HubNamespace

# --- offline: surface and SDK-side validation -------------------------------


@pytest.fixture()
def db():
    database = stratadb.open(cache=True)
    yield database
    database.close()


def test_hub_namespace_and_exports(db):
    assert isinstance(db.hub, HubNamespace)
    assert db.hub is db.hub  # cached like every namespace
    assert db.at(branch="default").hub is not None
    assert stratadb.HubDatasetSort is models.HubDatasetSort
    assert stratadb.HubCloneProgress is models.HubCloneProgress
    assert [sort.value for sort in HubDatasetSort] == ["downloads", "recent", "name", "size"]
    for method in ("hub_info", "hub_list_datasets", "hub_get_dataset", "hub_list_refs", "hub_list_yanked"):
        assert hasattr(Commands, method)


def test_list_datasets_rejects_unknown_sort(db):
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.list_datasets(sort="popular")
    assert info.value.code == "invalid_argument.sdk.command"
    assert "'downloads'" in info.value.hint


@pytest.mark.parametrize("bad", [[1, 2], 42, {"a": "b"}, b"tabular"])
def test_list_datasets_rejects_non_string_filters(db, bad):
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.list_datasets(tasks=bad)
    assert info.value.code == "invalid_argument.sdk.command"


def test_list_yanked_rejects_non_time_since(db):
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.list_yanked(since=20260901)
    assert info.value.code == "invalid_argument.sdk.command"


def test_engine_validates_the_query_before_any_network(db):
    # These fail in the executor (no hub contacted), so they run offline.
    for kwargs in ({"limit": 0}, {"limit": 201}, {"size_min_bytes": 2, "size_max_bytes": 1}):
        with pytest.raises(errors.InvalidArgumentError) as info:
            db.hub.list_datasets(hub_url="http://127.0.0.1:9", **kwargs)
        assert info.value.code == "invalid_argument.executor.hub_filter"
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.get_dataset("Not A Slug!", hub_url="http://127.0.0.1:9")
    assert info.value.code == "invalid_argument.executor.hub_dataset"
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.list_yanked(since="yesterday", hub_url="http://127.0.0.1:9")
    assert info.value.code == "invalid_argument.executor.hub_since"
    with pytest.raises(errors.InvalidArgumentError) as info:
        db.hub.info(hub_url="not a url")
    assert info.value.code == "invalid_argument.executor.hub_url"


def test_unreachable_hub_is_a_retryable_unavailable(db):
    with pytest.raises(errors.UnavailableError) as info:
        db.hub.info(hub_url="http://127.0.0.1:9")  # nothing listens on the discard port
    assert info.value.code == "unavailable.executor.hub_transport"
    assert info.value.retryable is True


def test_clone_rejects_non_callable_progress(tmp_path):
    with pytest.raises(errors.InvalidArgumentError) as info:
        stratadb.clone("titanic", tmp_path / "t", progress=42)
    assert info.value.code == "invalid_argument.sdk.command"
    assert not (tmp_path / "t").exists()


# --- live: against a real StrataHub ------------------------------------------


@pytest.fixture()
def hub(live_hub_url, monkeypatch):
    """A hub namespace whose default resolver lands on the live hub."""
    monkeypatch.setenv("STRATA_HUB_URL", live_hub_url)
    database = stratadb.open(cache=True)
    yield database.hub
    database.close()


def test_info(hub, live_hub_url):
    info = hub.info()
    assert isinstance(info, models.HubInfo)
    assert info.protocol_version == "v1"
    assert info.hash_algorithm == "blake3"
    assert info.max_object_size_bytes > 0 and info.max_dataset_size_bytes > 0
    assert isinstance(info.supported_object_content_types, list)
    # An explicit hub_url takes precedence over the resolver.
    assert hub.info(hub_url=live_hub_url) == info


def test_list_datasets_default_page(hub):
    page = hub.list_datasets()
    assert isinstance(page, models.HubDatasetPage)
    assert page.offset == 0 and page.limit >= 1
    assert page.total >= len(page.items) >= 1
    assert all(isinstance(item, models.HubDatasetSummary) for item in page.items)
    titanic = next(item for item in page.items if item.name == "titanic")
    assert "json" in titanic.primitives and titanic.default_branch == "main"
    assert titanic.size_bytes > 0 and titanic.license == "CC0-1.0"


def test_list_datasets_filters_sort_and_pages(hub):
    classification = hub.list_datasets(tasks="classification", sort="downloads")
    assert classification.total >= 1
    assert all("classification" in item.tasks for item in classification.items)
    downloads = [item.downloads for item in classification.items]
    assert downloads == sorted(downloads, reverse=True)
    # A single string and a one-element list are the same filter.
    assert hub.list_datasets(tags="demo").total == hub.list_datasets(tags=["demo"]).total

    by_size = hub.list_datasets(sort=HubDatasetSort.SIZE, limit=3)
    assert by_size.limit == 3 and len(by_size.items) <= 3
    sizes = [item.size_bytes for item in by_size.items]
    assert sizes == sorted(sizes, reverse=True)

    by_name = hub.list_datasets(sort="name")
    names = [item.name for item in by_name.items]
    assert names == sorted(names)

    # Offset pagination walks every dataset exactly once.
    seen: list[str] = []
    offset = 0
    while True:
        page = hub.list_datasets(limit=5, offset=offset, sort="name")
        seen.extend(item.name for item in page.items)
        offset = page.offset + page.limit
        if offset >= page.total or not page.items:
            break
    assert len(seen) == page.total and len(set(seen)) == len(seen)

    assert hub.list_datasets(size_max_bytes=0).total == 0


def test_get_dataset_card(hub):
    card = hub.get_dataset("titanic")
    assert isinstance(card, models.HubDatasetCard)
    assert card.name == "titanic" and card.default_branch == "main"
    assert card.manifest_hash.startswith("blake3:")
    assert "titanic" in card.clone_command
    assert card.readme and card.summary_excerpt
    assert card.engine_version_required and card.format_version
    assert card.quick_start_snippets is None or isinstance(card.quick_start_snippets, dict)
    assert card.provenance is None or isinstance(card.provenance, models.HubProvenance)


def test_get_dataset_missing(hub):
    with pytest.raises(errors.NotFoundError) as info:
        hub.get_dataset("does-not-exist-xyz")
    assert info.value.code == "not_found.executor.hub_dataset"


def test_list_refs(hub):
    refs = hub.list_refs("titanic")
    assert isinstance(refs, models.HubRefList)
    assert refs.dataset == "titanic" and refs.default_branch == "main"
    main = next(ref for ref in refs.refs if ref.branch == "main")
    assert isinstance(main, models.HubRefEntry)
    assert main.manifest_hash == hub.get_dataset("titanic").manifest_hash
    assert main.last_updated
    with pytest.raises(errors.NotFoundError) as info:
        hub.list_refs("does-not-exist-xyz")
    assert info.value.code == "not_found.executor.hub_dataset"


def test_list_yanked(hub):
    yanked = hub.list_yanked()
    assert isinstance(yanked, models.HubYankedList)
    assert yanked.total == len(yanked.items) and yanked.generated_at
    assert all(isinstance(item, models.HubYankedEntry) for item in yanked.items)
    # `since` narrows (never widens): as a string, an aware datetime, or a naive one (UTC).
    assert hub.list_yanked(since="2026-01-01T00:00:00Z").total <= yanked.total
    assert hub.list_yanked(since=datetime(2026, 1, 1, tzinfo=timezone.utc)).total <= yanked.total
    assert hub.list_yanked(since=datetime(2026, 1, 1)).total <= yanked.total


def test_clone_reports_progress(hub, tmp_path):
    events: list[HubCloneProgress] = []
    db = stratadb.clone("titanic", tmp_path / "titanic", progress=events.append)
    try:
        assert db.json.get("passenger:1")["name"] == "Braund, Mr. Owen Harris"
        origin = Commands(db._core).admin_remote().origin
        assert origin.dataset == "titanic" and origin.branch == "main"
    finally:
        db.close()

    assert all(isinstance(event, HubCloneProgress) for event in events)
    assert all(event.dataset == "titanic" for event in events)
    stages = [event.stage for event in events]
    assert stages[0] == models.HubCloneProgressStage.RESOLVED
    assert events[0].branch == "main" and events[0].manifest_hash.startswith("blake3:")
    manifest = events[1]
    assert manifest.stage == models.HubCloneProgressStage.MANIFEST_FETCHED
    assert manifest.object_count >= 1 and manifest.total_bytes > 0
    fetched = [event for event in events if event.stage == models.HubCloneProgressStage.OBJECT_FETCHED]
    assert [event.index for event in fetched] == list(range(1, manifest.object_count + 1))
    assert sum(event.bytes for event in fetched) == manifest.total_bytes
    assert stages[-2:] == [
        models.HubCloneProgressStage.IMPORTING,
        models.HubCloneProgressStage.DONE,
    ]


def test_clone_progress_callback_error_is_raised_after_completion(hub, tmp_path):
    seen: list[str] = []

    def boom(event: HubCloneProgress) -> None:
        seen.append(event.stage.value)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        stratadb.clone("titanic", tmp_path / "titanic", progress=boom)
    # The hook cannot cancel: one event reached the callback, the clone finished.
    assert seen == ["resolved"]
    db = stratadb.open(tmp_path / "titanic")
    try:
        assert db.json.count() == 30
    finally:
        db.close()


def test_clone_unknown_dataset_and_occupied_dest(hub, tmp_path):
    with pytest.raises(errors.UnavailableError) as info:
        stratadb.clone("does-not-exist-xyz", tmp_path / "nope")
    assert info.value.code == "unavailable.executor.hub_transport"  # the hub's 404, via the clone transport
    assert not (tmp_path / "nope").exists()

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep").write_text("x")
    with pytest.raises(errors.FailedPreconditionError) as info:
        stratadb.clone("titanic", occupied)
    assert info.value.code == "failed_precondition.executor.hub_clone"
    assert (occupied / "keep").read_text() == "x"
