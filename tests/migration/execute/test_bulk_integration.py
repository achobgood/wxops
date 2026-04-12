"""End-to-end integration tests: expand + optimize + partition at scale."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute.batch import partition_into_batches
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    LocationAddress,
    MigrationStatus,
    Provenance,
)

_TEST_PROVENANCE = Provenance(
    source_system="cucm",
    source_id="test-integration",
    source_name="test",
    extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


def _seed_location(store, cid="location:loc-1"):
    store.upsert_object(CanonicalLocation(
        canonical_id=cid,
        provenance=_TEST_PROVENANCE,
        name="Loc",
        address=LocationAddress(
            address1="1 Main", city="SF", state="CA",
            postal_code="94105", country="US",
        ),
        time_zone="America/Los_Angeles",
        preferred_language="en_us",
        announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    ))


def _seed_user(store, cid):
    u = CanonicalUser(
        canonical_id=cid,
        provenance=_TEST_PROVENANCE,
        emails=[f"{cid.split(':')[-1]}@example.com"],
        display_name=cid,
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(u)


def test_1000_devices_produces_bulk_ops(store, device_factory):
    loc = "location:loc-1"
    _seed_location(store, loc)
    for i in range(1000):
        _seed_user(store, f"user:u{i}")
        d = device_factory(f"device:d{i}", location_cid=loc, owner_cid=f"user:u{i}")
        d.status = MigrationStatus.ANALYZED
        store.upsert_object(d)

    ops = expand_to_operations(store, bulk_device_threshold=100)

    # Per-device settings ops fully replaced.
    per_dev = [o for o in ops
               if o.resource_type == "device" and o.op_type == "configure_settings"]
    assert per_dev == []

    # 1 bulk settings op.
    bulk_settings = [o for o in ops if o.resource_type == "bulk_device_settings"]
    assert len(bulk_settings) == 1

    # 1 bulk rebuild op at tier 8.
    rebuild = [o for o in ops if o.resource_type == "bulk_rebuild_phones"]
    assert len(rebuild) == 1
    assert rebuild[0].tier == 8

    # Device creates preserved.
    creates = [o for o in ops
               if o.resource_type == "device" and o.op_type == "create"]
    assert len(creates) == 1000


def test_50_devices_stays_per_device(store, device_factory):
    loc = "location:loc-1"
    _seed_location(store, loc)
    for i in range(50):
        _seed_user(store, f"user:u{i}")
        d = device_factory(f"device:d{i}", location_cid=loc, owner_cid=f"user:u{i}")
        d.status = MigrationStatus.ANALYZED
        store.upsert_object(d)

    ops = expand_to_operations(store, bulk_device_threshold=100)

    per_dev_settings = [
        o for o in ops
        if o.resource_type == "device" and o.op_type == "configure_settings"
    ]
    assert len(per_dev_settings) == 50

    bulk_any = [o for o in ops if o.resource_type.startswith("bulk_")]
    assert bulk_any == []


def test_tier_ordering_bulk_settings_before_templates_before_rebuild(
    store, device_factory,
):
    from wxcli.migration.models import CanonicalDeviceLayout

    loc = "location:loc-1"
    _seed_location(store, loc)
    for i in range(120):
        _seed_user(store, f"user:u{i}")
        d = device_factory(f"device:d{i}", location_cid=loc, owner_cid=f"user:u{i}")
        d.status = MigrationStatus.ANALYZED
        store.upsert_object(d)
        layout = CanonicalDeviceLayout(
            canonical_id=f"device_layout:d{i}",
            provenance=_TEST_PROVENANCE,
            device_canonical_id=f"device:d{i}",
            template_canonical_id="line_key_template:tpl-a",
            resolved_line_keys=[{"lineKeyIndex": 1}],
            status=MigrationStatus.ANALYZED,
        )
        store.upsert_object(layout)

    ops = expand_to_operations(store, bulk_device_threshold=100)
    G = build_dependency_graph(ops, store)
    batches = partition_into_batches(G)

    tiers_seen: dict[str, int] = {}
    for b in batches:
        for node_id in b.operations:
            rt = G.nodes[node_id].get("resource_type", "")
            if rt == "bulk_device_settings" and "device_settings_first" not in tiers_seen:
                tiers_seen["device_settings_first"] = b.tier
            if rt == "bulk_line_key_template" and "line_key_first" not in tiers_seen:
                tiers_seen["line_key_first"] = b.tier
            if rt == "bulk_rebuild_phones" and "rebuild_first" not in tiers_seen:
                tiers_seen["rebuild_first"] = b.tier

    # Settings run at tier 5, templates at 7, rebuild at 8.
    assert tiers_seen["device_settings_first"] == 5
    assert tiers_seen["line_key_first"] == 7
    assert tiers_seen["rebuild_first"] == 8
