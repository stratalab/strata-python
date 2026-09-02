"""``db.hub`` — browse a StrataHub: datasets, dataset cards, refs, and yanks.

A StrataHub is a content-addressed dataset registry; :func:`stratadb.clone`
pulls a dataset out of one into a new durable database. This namespace is the
read-only browse side of the same protocol (``GET /v1/...``). Like every
command it dispatches through the executor, so it lives on an open handle —
but it never reads or writes that handle's data, and any handle will do:
``stratadb.open(cache=True).hub`` browses without a database of your own.

Every method takes ``hub_url=``. When omitted, the engine's layered resolver
selects the hub: ``STRATA_HUB_URL``, then the project and global Strata config
files, then the built-in default (``https://hub.stratahub.io``). A malformed
URL raises ``InvalidArgumentError`` (``invalid_argument.executor.hub_url``); a
hub that cannot be reached raises ``UnavailableError``
(``unavailable.executor.hub_transport``, retryable). The hub's own 400/404
answers surface as ``InvalidArgumentError`` / ``NotFoundError`` with the codes
each method documents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Union

from .._generated.models import HubDatasetSort
from ..errors import InvalidArgumentError, client_error
from .base import Namespace

_SORT_VALUES = tuple(sort.value for sort in HubDatasetSort)


def _sort_value(sort: Any) -> str:
    if isinstance(sort, HubDatasetSort):
        return sort.value
    if isinstance(sort, str) and sort in _SORT_VALUES:
        return sort
    raise client_error(
        InvalidArgumentError,
        "invalid_argument.sdk.command",
        f"invalid dataset sort {sort!r}",
        "pass one of "
        + ", ".join(repr(value) for value in _SORT_VALUES)
        + " (or a stratadb.HubDatasetSort)",
    )


def _string_list(name: str, value: Any) -> list[str]:
    """A single string or an iterable of strings -> the wire's repeatable filter."""
    if isinstance(value, str):
        return [value]
    items = None
    if not isinstance(value, (bytes, dict)):
        try:
            items = list(value)
        except TypeError:
            items = None
    if items is None or not all(isinstance(item, str) for item in items):
        raise client_error(
            InvalidArgumentError,
            "invalid_argument.sdk.command",
            f"{name} must be a string or an iterable of strings, got {value!r}",
            f'pass e.g. {name}="classification" or {name}=["classification", "tabular"]',
        )
    return items


def _since_value(since: Any) -> str:
    if isinstance(since, datetime):
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return since.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(since, str):
        return since
    raise client_error(
        InvalidArgumentError,
        "invalid_argument.sdk.command",
        f"since must be an RFC 3339 string or a datetime, got {since!r}",
        'pass e.g. since="2026-09-01T00:00:00Z"',
    )


class HubNamespace(Namespace):
    """Read-only browsing of a StrataHub's datasets, refs, and yank list.

    Browse, then :func:`stratadb.clone` what you want::

        page = db.hub.list_datasets(tasks="classification", sort="downloads")
        card = db.hub.get_dataset(page.items[0].name)
        titanic = stratadb.clone(card.name, "./titanic")

    Examples:
        >>> from stratadb import HubDatasetSort
        >>> [sort.value for sort in HubDatasetSort]        # the list_datasets sort keys
        ['downloads', 'recent', 'name', 'size']
        >>> db.hub.info().protocol_version                  # doctest: +SKIP
        'v1'
    """

    def info(self, *, hub_url: Optional[str] = None) -> Any:
        """The hub's V1 capability advertisement (``GET /v1/info``).

        A ``HubInfo``: ``.protocol_version``, ``.server_implementation`` /
        ``.server_version``, ``.hash_algorithm``, the size caps
        (``.max_object_size_bytes``, ``.max_manifest_size_bytes``,
        ``.max_dataset_size_bytes``), ``.supported_object_content_types``, and
        ``.telemetry_endpoint_enabled``. The cheapest way to check that a hub
        is reachable.

        Examples:
            >>> db.hub.info().hash_algorithm                # doctest: +SKIP
            'blake3'
        """
        return self._c.hub_info(hub_url=hub_url)

    def list_datasets(
        self,
        *,
        tasks: Union[str, Iterable[str], None] = None,
        tags: Union[str, Iterable[str], None] = None,
        primitives: Union[str, Iterable[str], None] = None,
        license: Optional[str] = None,
        size_min_bytes: Optional[int] = None,
        size_max_bytes: Optional[int] = None,
        sort: Any = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        hub_url: Optional[str] = None,
    ) -> Any:
        """Lists the hub's datasets, filtered and sorted (``GET /v1/datasets``).

        Returns a ``HubDatasetPage``: ``.items`` (each a ``HubDatasetSummary``
        — ``.name``, ``.description``, ``.size_bytes``, ``.downloads``,
        ``.primitives``, ``.tasks``, ``.tags``, ``.license``,
        ``.default_branch``, ``.last_updated``, ``.badge``), ``.total``
        matches, and the ``.offset`` / ``.limit`` the hub applied. Pages are
        offset-based: pass ``offset=page.offset + page.limit`` while it is
        below ``page.total``.

        ``tasks``, ``tags``, and ``primitives`` each take a string or a list of
        strings and match any of the values given (OR within a dimension, AND
        across dimensions). ``license`` matches an SPDX identifier;
        ``size_min_bytes`` / ``size_max_bytes`` bound the default branch's
        bundle size. ``sort`` is ``"downloads"``, ``"recent"``, ``"name"``, or
        ``"size"`` (or a :class:`stratadb.HubDatasetSort`); ``limit`` is
        1..200. A bad query raises ``InvalidArgumentError``
        (``invalid_argument.executor.hub_filter``).

        Examples:
            >>> page = db.hub.list_datasets(tasks="classification", sort="downloads", limit=5)  # doctest: +SKIP
            >>> [dataset.name for dataset in page.items]                                        # doctest: +SKIP
            ['titanic', 'iris']
        """
        return self._c.hub_list_datasets(
            hub_url=hub_url,
            license=license,
            limit=limit,
            offset=offset,
            primitives=None if primitives is None else _string_list("primitives", primitives),
            size_max_bytes=size_max_bytes,
            size_min_bytes=size_min_bytes,
            sort=None if sort is None else _sort_value(sort),
            tags=None if tags is None else _string_list("tags", tags),
            tasks=None if tasks is None else _string_list("tasks", tasks),
        )

    def get_dataset(self, name: str, *, hub_url: Optional[str] = None) -> Any:
        """One dataset's full card (``GET /v1/datasets/{name}``).

        A ``HubDatasetCard``: everything the listing summary has, plus
        ``.owner``, ``.readme`` (CommonMark), ``.summary_excerpt``,
        ``.created``, ``.manifest_hash`` (of the default branch),
        ``.clone_command``, ``.engine_version_required``, ``.format_version``,
        ``.quick_start_snippets`` (language -> snippet), the ``.schema`` and
        ``.sample_preview`` blocks, ``.strata_features`` (branch highlights,
        time-travel and multi-primitive demos), ``.provenance``, and
        ``.citation``. An unknown dataset raises ``NotFoundError``
        (``not_found.executor.hub_dataset``); a malformed slug raises
        ``InvalidArgumentError`` (``invalid_argument.executor.hub_dataset``).

        Examples:
            >>> card = db.hub.get_dataset("titanic")        # doctest: +SKIP
            >>> card.primitives, card.license               # doctest: +SKIP
            (['json', 'kv'], 'CC0-1.0')
        """
        return self._c.hub_get_dataset(name, hub_url=hub_url)

    def list_refs(self, dataset: str, *, hub_url: Optional[str] = None) -> Any:
        """A dataset's live, cloneable refs (``GET /v1/datasets/{name}/refs``).

        A ``HubRefList``: ``.dataset``, ``.default_branch``, and ``.refs`` —
        one ``HubRefEntry`` per branch with ``.branch``, ``.manifest_hash``,
        and ``.last_updated``. Yanked refs are already filtered out by the
        hub. Pass a ref's ``.branch`` as ``stratadb.clone(..., branch=...)``.
        An unknown dataset raises ``NotFoundError``
        (``not_found.executor.hub_dataset``).

        Examples:
            >>> [ref.branch for ref in db.hub.list_refs("titanic").refs]   # doctest: +SKIP
            ['main']
        """
        return self._c.hub_list_refs(dataset, hub_url=hub_url)

    def list_yanked(
        self,
        *,
        since: Union[str, datetime, None] = None,
        hub_url: Optional[str] = None,
    ) -> Any:
        """The hub's yank deny-list — refs taken down (``GET /v1/yanked``).

        A ``HubYankedList``: ``.generated_at``, ``.total``, and ``.items`` —
        each a ``HubYankedEntry`` with ``.dataset``, ``.branch``,
        ``.manifest_hash``, ``.yanked_at``, and ``.reason``. ``since`` narrows
        the list to yanks at or after an instant: an RFC 3339 string such as
        ``"2026-09-01T00:00:00Z"``, or a ``datetime`` (a naive one is taken as
        UTC). A string the engine cannot parse raises ``InvalidArgumentError``
        (``invalid_argument.executor.hub_since``).

        Examples:
            >>> db.hub.list_yanked(since="2026-09-01T00:00:00Z").total   # doctest: +SKIP
            0
        """
        return self._c.hub_list_yanked(
            hub_url=hub_url, since=None if since is None else _since_value(since)
        )
