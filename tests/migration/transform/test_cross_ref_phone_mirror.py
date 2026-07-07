"""Test that device_owned_by_user cross-ref is mirrored from phone:{name}."""
from datetime import datetime, timezone
from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def test_device_owned_by_user_mirrored_to_phone():
    """Cross-ref builder must create device_owned_by_user from BOTH device: and phone: canonical IDs."""
    store = MigrationStore(":memory:")

    # Device object (CanonicalDevice from normalizer)
    store.upsert_object(MigrationObject(
        canonical_id="device:SEP001122334455",
        provenance=_prov("SEP001122334455"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "cucm_device_pool": "DP-HQ",
            "cucm_owner_user": "jdoe",
        },
    ))

    # Raw phone object (raw AXL from pipeline)
    store.upsert_object(MigrationObject(
        canonical_id="phone:SEP001122334455",
        provenance=_prov("SEP001122334455"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEP001122334455",
            "ownerUserName": {"_value_1": "jdoe"},
            "devicePoolName": {"_value_1": "DP-HQ"},
        },
    ))

    # User + device pool
    store.upsert_object(MigrationObject(
        canonical_id="user:jdoe", provenance=_prov("jdoe"),
        status=MigrationStatus.NORMALIZED,
    ))
    store.upsert_object(MigrationObject(
        canonical_id="device_pool:DP-HQ", provenance=_prov("DP-HQ"),
        status=MigrationStatus.NORMALIZED,
    ))

    builder = CrossReferenceBuilder(store)
    builder.build()

    # Original: device: → user: (already works)
    device_refs = store.find_cross_refs("device:SEP001122334455", "device_owned_by_user")
    assert device_refs == ["user:jdoe"]

    # NEW: phone: → user: (this is what CallForwardingMapper and MonitoringMapper use)
    phone_refs = store.find_cross_refs("phone:SEP001122334455", "device_owned_by_user")
    assert phone_refs == ["user:jdoe"], (
        "device_owned_by_user must be mirrored from phone:{name} for "
        "CallForwardingMapper and MonitoringMapper"
    )
