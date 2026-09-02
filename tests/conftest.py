"""Shared fixtures.

The StrataHub tests (``db.hub`` browsing, ``stratadb.clone``) need a reachable
hub. They target ``STRATA_HUB_URL`` when set and the engine's built-in default
(the public https://hub.stratahub.io) otherwise, and skip — not fail — when that
hub cannot be reached, so an offline run stays green.
"""

from __future__ import annotations

import os

import pytest

import stratadb

DEFAULT_HUB_URL = "https://hub.stratahub.io"
HUB_URL = os.environ.get("STRATA_HUB_URL") or DEFAULT_HUB_URL


@pytest.fixture(scope="session")
def live_hub_url() -> str:
    """The hub the network tests run against; skips the test when unreachable."""
    try:
        with stratadb.open(cache=True) as probe:
            probe.hub.info(hub_url=HUB_URL)
    except stratadb.errors.StrataError as exc:
        pytest.skip(f"StrataHub at {HUB_URL} is not reachable ({exc.code})")
    return HUB_URL
