"""DeviceLayoutMapper must not emit layouts for CONVERTIBLE devices.

Rationale: CONVERTIBLE devices (8845/8851/8865/7821/7841/7861) register via
activation code and auto-configure post-registration. The execution pipeline
skips layout/softkey ops for them — applying templates at scale happens via
a post-registration bulk job, not the main pipeline.
"""
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    DeviceCompatibilityTier,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.device_layout_mapper import DeviceLayoutMapper


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _insert_raw_phone(store, name, model):
    phone = MigrationObject(
        canonical_id=f"phone:{name}",
        object_type="phone",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={
            "class": "Phone",
            "name": name,
            "model": model,
            "ownerUserName": {"_value_1": "owner1"},
            "lines": [],
        },
    )
    store.upsert_object(phone)


def _insert_device(store, name, tier):
    device = CanonicalDevice(
        canonical_id=f"device:{name}",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        mac="AA" * 6,
        model="Cisco 8851",
        compatibility_tier=tier,
        owner_canonical_id="user:owner1",
    )
    store.upsert_object(device)


def test_convertible_device_gets_no_layout(store):
    """DeviceLayoutMapper must skip CONVERTIBLE devices entirely."""
    _insert_raw_phone(store, "SEP001122AABBCC", "Cisco 8851")
    _insert_device(store, "SEP001122AABBCC", DeviceCompatibilityTier.CONVERTIBLE)

    mapper = DeviceLayoutMapper()
    mapper.map(store)

    layouts = store.get_objects("device_layout")
    assert layouts == [], (
        "CONVERTIBLE devices must not get device_layout objects — "
        "layout is deferred to post-registration bulk job"
    )


def test_native_mpp_device_still_gets_layout(store):
    """NATIVE_MPP devices still get device_layout objects (regression guard)."""
    _insert_raw_phone(store, "SEP001122DDEEFF", "Cisco 9861")
    _insert_device(store, "SEP001122DDEEFF", DeviceCompatibilityTier.NATIVE_MPP)

    mapper = DeviceLayoutMapper()
    mapper.map(store)

    layouts = store.get_objects("device_layout")
    assert len(layouts) == 1
    assert layouts[0]["canonical_id"] == "device_layout:SEP001122DDEEFF"
