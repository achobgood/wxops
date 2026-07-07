"""Tests for appendix section W: DECT Networks."""

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.report.appendix import generate_appendix
from wxcli.migration.store import MigrationStore


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="cucm", source_id=name, source_name=name,
        extracted_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )


def _dect_device(
    idx: int, model: str = "Cisco 6825",
    owner_id: str | None = "user:jsmith",
    device_pool: str = "DP-Warehouse",
    extension: str = "1001",
) -> CanonicalDevice:
    mac = f"DECT0000{idx:04d}"
    return CanonicalDevice(
        canonical_id=f"device:SEP{mac}",
        provenance=_prov(f"SEP{mac}"),
        status=MigrationStatus.ANALYZED,
        model=model,
        compatibility_tier=DeviceCompatibilityTier.DECT,
        mac=mac,
        owner_canonical_id=owner_id,
        cucm_device_name=f"SEP{mac}",
        line_appearances=[{"dirn": {"pattern": extension}}],
        pre_migration_state={
            "name": f"SEP{mac}", "model": model,
            "cucm_device_pool": device_pool,
            "ownerUserName": "jsmith" if owner_id else None,
        },
    )


class TestDECTAppendixSection:
    def test_section_w_present_with_dect(self, tmp_path):
        """Section W appears when DECT devices exist."""
        store = MigrationStore(tmp_path / "dect.db")
        store.upsert_object(_dect_device(1))

        html = generate_appendix(store)
        assert 'id="dect-networks"' in html
        assert "DECT Networks" in html

    def test_section_w_absent_without_dect(self, tmp_path):
        """Section W is omitted when no DECT devices exist."""
        store = MigrationStore(tmp_path / "no_dect.db")
        store.upsert_object(CanonicalDevice(
            canonical_id="device:desk-phone",
            provenance=_prov("desk"),
            status=MigrationStatus.ANALYZED,
            model="Cisco 8845",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            mac="AABB00001111",
        ))

        html = generate_appendix(store)
        assert "DECT Networks" not in html

    def test_section_w_inventory_table(self, tmp_path):
        """Inventory table lists each DECT handset."""
        store = MigrationStore(tmp_path / "dect_inv.db")
        store.upsert_object(_dect_device(1, model="Cisco 6825"))
        store.upsert_object(_dect_device(2, model="Cisco 6823"))

        html = generate_appendix(store)
        assert "Cisco 6825" in html
        assert "Cisco 6823" in html
        assert "DECT Handset Inventory" in html

    def test_section_w_coverage_zones(self, tmp_path):
        """Coverage zones are grouped by device pool."""
        store = MigrationStore(tmp_path / "dect_zones.db")
        for i in range(1, 4):
            store.upsert_object(_dect_device(i, device_pool="DP-Warehouse"))
        for i in range(4, 6):
            store.upsert_object(_dect_device(i, device_pool="DP-Lobby"))

        html = generate_appendix(store)
        assert "Coverage Zone Analysis" in html
        assert "DP-Warehouse" in html
        assert "DP-Lobby" in html

    def test_section_w_unowned_warning(self, tmp_path):
        """Warning appears for DECT handsets with no owner."""
        store = MigrationStore(tmp_path / "dect_unowned.db")
        store.upsert_object(_dect_device(1, owner_id="user:jsmith"))
        store.upsert_object(_dect_device(2, owner_id=None))
        store.upsert_object(_dect_device(3, owner_id=None))

        html = generate_appendix(store)
        assert "no owner" in html.lower() or "unowned" in html.lower()
        assert "2" in html

    def test_section_w_design_recommendation_large_zone(self, tmp_path):
        """Zones with >30 handsets recommend DBS-210."""
        store = MigrationStore(tmp_path / "dect_large.db")
        for i in range(1, 36):
            store.upsert_object(_dect_device(i, device_pool="DP-BigWarehouse"))

        html = generate_appendix(store)
        assert "DBS-210" in html
