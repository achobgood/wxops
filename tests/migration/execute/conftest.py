"""Shared fixtures for execute-layer tests."""

from __future__ import annotations

import pytest

from wxcli.migration.models import CanonicalDevice, DeviceCompatibilityTier
from wxcli.migration.store import MigrationStore


@pytest.fixture
def store(tmp_path):
    """In-memory-ish MigrationStore backed by tmp_path."""
    db_path = tmp_path / "migration.db"
    s = MigrationStore(db_path)
    yield s
    s.close()


@pytest.fixture
def device_factory():
    """Factory for CanonicalDevice objects with sane defaults."""

    def _make(
        cid: str,
        location_cid: str = "location:loc-1",
        model: str = "Cisco 9861",
        compatibility_tier: DeviceCompatibilityTier = DeviceCompatibilityTier.NATIVE_MPP,
        owner_cid: str | None = None,
    ) -> CanonicalDevice:
        return CanonicalDevice(
            canonical_id=cid,
            mac=cid.replace(":", "").upper()[:12].ljust(12, "0"),
            model=model,
            compatibility_tier=compatibility_tier,
            display_name=cid,
            owner_canonical_id=owner_cid,
            location_canonical_id=location_cid,
        )

    return _make
