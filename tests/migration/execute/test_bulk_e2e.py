"""End-to-end test: planner -> save -> get_next_batch -> handler for bulk ops.

Validates that bulk op payloads flow through the plan pipeline so
handlers receive non-empty data dicts in production.
"""

from __future__ import annotations

from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.execute.handlers import HANDLER_REGISTRY
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.execute.runtime import get_next_batch
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    LocationAddress,
    MigrationStatus,
    Provenance,
)


_PROV = Provenance(
    source_system="cucm",
    source_id="test",
    source_name="test",
    extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


def _seed(store, device_factory, n=120, loc_cid="location:loc-1"):
    store.upsert_object(CanonicalLocation(
        canonical_id=loc_cid, name="Loc 1",
        address=LocationAddress(
            address1="1 Main", city="SF", state="CA",
            postal_code="94105", country="US",
        ),
        time_zone="America/Los_Angeles",
        preferred_language="en_us",
        announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
        provenance=_PROV,
    ))
    for i in range(n):
        u = CanonicalUser(
            canonical_id=f"user:u{i}",
            emails=[f"u{i}@example.com"],
            display_name=f"User {i}",
            status=MigrationStatus.ANALYZED,
            provenance=_PROV,
        )
        store.upsert_object(u)
        dev = device_factory(
            f"device:d{i}", location_cid=loc_cid, owner_cid=f"user:u{i}",
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)


def test_bulk_device_settings_handler_receives_payload(store, device_factory):
    """Planner -> save -> get_next_batch -> handler produces non-empty body."""
    _seed(store, device_factory, n=120)

    ops = expand_to_operations(store, bulk_device_threshold=100)
    G = build_dependency_graph(ops, store)
    save_plan_to_store(G, store)

    # Mark all non-bulk ops as completed so bulk ops become ready.
    conn = store.conn
    conn.execute(
        """UPDATE plan_operations SET status = 'completed', webex_id = 'fake'
           WHERE resource_type NOT LIKE 'bulk_%'"""
    )
    conn.commit()

    batch = get_next_batch(store)
    assert batch, "Expected at least one bulk op to be ready"

    bulk_settings_ops = [
        op for op in batch
        if op["resource_type"] == "bulk_device_settings"
    ]
    assert len(bulk_settings_ops) >= 1

    op = bulk_settings_ops[0]
    data = op["data"]
    assert data, f"data should not be empty, got: {data}"
    assert "location_canonical_id" in data

    handler = HANDLER_REGISTRY[("bulk_device_settings", "submit")]
    calls = handler(data, op["resolved_deps"], {})
    assert len(calls) == 1
    method, url, body = calls[0]
    assert method == "POST"
    assert "/telephony/config/jobs/devices/callDeviceSettings" in url
    assert body.get("locationCustomizationsEnabled") is True
