"""Tests for CallSettingsMapper intercept detection extension."""
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


def _setup_user_with_intercept(store, userid="jsmith", signal_type="blocked_partition"):
    """Create a user + intercept candidate + cross-ref in the store."""
    store.upsert_object(CanonicalUser(
        canonical_id=f"user:{userid}", provenance=_prov(userid),
        status=MigrationStatus.ANALYZED,
        emails=[f"{userid}@test.com"], cucm_userid=userid,
    ))
    store.upsert_object(MigrationObject(
        canonical_id="intercept_candidate:1001:Blocked_PT",
        provenance=_prov("ic"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": userid,
            "dn": "1001",
            "partition": "Blocked_PT",
            "signal_type": signal_type,
            "forward_destination": "+14155550000",
            "voicemail_enabled": signal_type == "cfa_voicemail",
        },
    ))
    store.add_cross_ref(
        f"user:{userid}",
        "intercept_candidate:1001:Blocked_PT",
        "user_has_intercept_signal",
    )


class TestInterceptDetection:
    def test_intercept_detection_blocked_partition(self):
        """User with intercept cross-ref gets call_settings.intercept populated."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jsmith", "blocked_partition")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jsmith")
        assert user_data is not None
        intercept = user_data.get("call_settings", {}).get("intercept")
        assert intercept is not None
        assert intercept["detected"] is True
        assert intercept["signal_type"] == "blocked_partition"

    def test_intercept_detection_cfa_voicemail(self):
        """CFA-to-voicemail signal detected."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jdoe", "cfa_voicemail")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jdoe")
        intercept = user_data.get("call_settings", {}).get("intercept")
        assert intercept is not None
        assert intercept["signal_type"] == "cfa_voicemail"
        assert intercept["forward_destination"] == "+14155550000"
        assert intercept["voicemail_enabled"] is True

    def test_no_intercept_signal(self):
        """User without intercept cross-ref has no intercept in call_settings."""
        store = MigrationStore(":memory:")
        store.upsert_object(CanonicalUser(
            canonical_id="user:clean", provenance=_prov("clean"),
            status=MigrationStatus.ANALYZED,
            emails=["clean@test.com"], cucm_userid="clean",
        ))

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:clean")
        call_settings = user_data.get("call_settings") or {}
        assert "intercept" not in call_settings

    def test_intercept_does_not_override_other_settings(self):
        """Intercept detection coexists with DND, call waiting, etc."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jsmith", "blocked_partition")

        # Also add a phone with DND enabled for the same user
        store.upsert_object(MigrationObject(
            canonical_id="phone:SEP001",
            provenance=_prov("SEP001"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SEP001",
                "dndStatus": "true",
                "dndOption": "Call Reject",
                "lines": [{"index": "1", "dirn": {"pattern": "1001"}}],
            },
        ))
        store.add_cross_ref("phone:SEP001", "user:jsmith", "device_owned_by_user")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jsmith")
        call_settings = user_data.get("call_settings", {})
        # Both DND and intercept should be present
        assert "doNotDisturb" in call_settings
        assert call_settings["doNotDisturb"]["enabled"] is True
        assert "intercept" in call_settings
        assert call_settings["intercept"]["detected"] is True
