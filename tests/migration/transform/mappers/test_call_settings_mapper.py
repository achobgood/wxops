# tests/migration/transform/mappers/test_call_settings_mapper.py
"""Test that CallSettingsMapper extracts DND/call-waiting from phone data."""
from datetime import datetime, timezone
from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def test_extracts_dnd_from_phone():
    """DND enabled on primary line should populate call_settings.doNotDisturb."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:jdoe", provenance=_prov("jdoe"),
        status=MigrationStatus.ANALYZED,
        emails=["jdoe@test.com"], cucm_userid="jdoe",
    )
    store.upsert_object(user)

    phone = MigrationObject(
        canonical_id="phone:SEP001122334455",
        provenance=_prov("SEP001122334455"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEP001122334455",
            "dndStatus": "true",
            "dndOption": "Ringer Off",
            "lines": [{"index": "1", "dirn": {"pattern": "1001"}}],
        },
    )
    store.upsert_object(phone)

    # Cross-ref: phone → user
    store.add_cross_ref("phone:SEP001122334455", "user:jdoe", "device_owned_by_user")

    mapper = CallSettingsMapper()
    result = mapper.map(store)

    # Re-read user
    user_data = store.get_object("user:jdoe")
    assert user_data is not None
    cs = user_data.get("call_settings")
    assert cs is not None, "call_settings should be populated"
    assert cs.get("doNotDisturb") is not None
    assert cs["doNotDisturb"]["enabled"] is True


def test_no_settings_means_no_call_settings():
    """Phone with all default settings should not populate call_settings."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:bob", provenance=_prov("bob"),
        status=MigrationStatus.ANALYZED,
        emails=["bob@test.com"], cucm_userid="bob",
    )
    store.upsert_object(user)

    phone = MigrationObject(
        canonical_id="phone:SEPDEFAULT",
        provenance=_prov("SEPDEFAULT"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEPDEFAULT",
            "lines": [{"index": "1", "dirn": {"pattern": "1002"}}],
        },
    )
    store.upsert_object(phone)
    store.add_cross_ref("phone:SEPDEFAULT", "user:bob", "device_owned_by_user")

    mapper = CallSettingsMapper()
    mapper.map(store)

    user_data = store.get_object("user:bob")
    assert user_data is not None
    cs = user_data.get("call_settings")
    assert not cs, "Default settings should not produce call_settings"


def test_common_area_phone_skipped():
    """Common-area phones should not enrich any user."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:carol", provenance=_prov("carol"),
        status=MigrationStatus.ANALYZED,
        emails=["carol@test.com"],
    )
    store.upsert_object(user)

    phone = MigrationObject(
        canonical_id="phone:SEPCOMMON",
        provenance=_prov("SEPCOMMON"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEPCOMMON",
            "is_common_area": True,
            "dndStatus": "true",
        },
    )
    store.upsert_object(phone)
    store.add_cross_ref("phone:SEPCOMMON", "user:carol", "device_owned_by_user")

    mapper = CallSettingsMapper()
    mapper.map(store)

    user_data = store.get_object("user:carol")
    assert user_data is not None
    assert not user_data.get("call_settings"), "Common-area phone should not produce call_settings"


def test_multi_device_user_uses_first_phone():
    """For a user with multiple phones, only the first phone with settings enriches the user."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:dave", provenance=_prov("dave"),
        status=MigrationStatus.ANALYZED,
        emails=["dave@test.com"],
    )
    store.upsert_object(user)

    # First phone: DND enabled
    phone1 = MigrationObject(
        canonical_id="phone:SEP111111111111",
        provenance=_prov("SEP111111111111"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "SEP111111111111", "dndStatus": "true", "dndOption": "Call Reject"},
    )
    store.upsert_object(phone1)
    store.add_cross_ref("phone:SEP111111111111", "user:dave", "device_owned_by_user")

    # Second phone: recording enabled
    phone2 = MigrationObject(
        canonical_id="phone:SEP222222222222",
        provenance=_prov("SEP222222222222"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "SEP222222222222", "builtInBridgeStatus": "On"},
    )
    store.upsert_object(phone2)
    store.add_cross_ref("phone:SEP222222222222", "user:dave", "device_owned_by_user")

    mapper = CallSettingsMapper()
    mapper.map(store)

    user_data = store.get_object("user:dave")
    assert user_data is not None
    cs = user_data.get("call_settings")
    assert cs is not None, "call_settings should be populated from first phone"


def test_phone_without_owner_skipped():
    """Phone with no device_owned_by_user cross-ref should be silently skipped."""
    store = MigrationStore(":memory:")

    phone = MigrationObject(
        canonical_id="phone:SEPORPHAN",
        provenance=_prov("SEPORPHAN"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "SEPORPHAN", "dndStatus": "true"},
    )
    store.upsert_object(phone)
    # No cross-ref added

    mapper = CallSettingsMapper()
    result = mapper.map(store)

    assert result.objects_updated == 0


def test_dnd_call_reject_option():
    """DND with Call Reject option should set ringSplashEnabled=False."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:eve", provenance=_prov("eve"),
        status=MigrationStatus.ANALYZED,
        emails=["eve@test.com"],
    )
    store.upsert_object(user)

    phone = MigrationObject(
        canonical_id="phone:SEPEVE",
        provenance=_prov("SEPEVE"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEPEVE",
            "dndStatus": "true",
            "dndOption": "Call Reject",
        },
    )
    store.upsert_object(phone)
    store.add_cross_ref("phone:SEPEVE", "user:eve", "device_owned_by_user")

    mapper = CallSettingsMapper()
    mapper.map(store)

    user_data = store.get_object("user:eve")
    cs = user_data.get("call_settings")
    assert cs is not None
    assert cs["doNotDisturb"]["ringSplashEnabled"] is False


def test_recording_enabled():
    """builtInBridgeStatus=On should produce callRecording settings."""
    store = MigrationStore(":memory:")

    user = CanonicalUser(
        canonical_id="user:frank", provenance=_prov("frank"),
        status=MigrationStatus.ANALYZED,
        emails=["frank@test.com"],
    )
    store.upsert_object(user)

    phone = MigrationObject(
        canonical_id="phone:SEPFRANK",
        provenance=_prov("SEPFRANK"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": "SEPFRANK",
            "builtInBridgeStatus": "On",
        },
    )
    store.upsert_object(phone)
    store.add_cross_ref("phone:SEPFRANK", "user:frank", "device_owned_by_user")

    mapper = CallSettingsMapper()
    mapper.map(store)

    user_data = store.get_object("user:frank")
    cs = user_data.get("call_settings")
    assert cs is not None
    assert cs["callRecording"]["enabled"] is True
    assert cs["callRecording"]["record"] == "Always"
