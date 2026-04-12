"""Tests for CanonicalVoicemailGroup model and registry."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.models import (
    CANONICAL_TYPE_REGISTRY,
    CanonicalVoicemailGroup,
    MigrationObject,
    MigrationStatus,
    Provenance,
)


def _prov() -> Provenance:
    return Provenance(
        source_system="unity_connection",
        source_id="uc-obj-123",
        source_name="Sales Voicemail",
        cluster="lab",
        extracted_at=datetime.now(timezone.utc),
    )


class TestCanonicalVoicemailGroup:
    def test_model_defaults(self):
        vg = CanonicalVoicemailGroup(
            canonical_id="voicemail_group:sales",
            provenance=_prov(),
            status=MigrationStatus.NORMALIZED,
            name="Sales Voicemail",
            extension="5896",
        )
        assert vg.name == "Sales Voicemail"
        assert vg.extension == "5896"
        assert vg.language_code == "en_us"
        assert vg.enabled is True
        assert vg.message_storage == {"storageType": "INTERNAL"}
        assert vg.notifications == {"enabled": False}
        assert vg.fax_message == {"enabled": False}
        assert vg.transfer_to_number == {"enabled": False}
        assert vg.email_copy_of_message == {"enabled": False}
        assert vg.location_id is None
        assert vg.phone_number is None
        assert vg.passcode is None
        assert vg.caller_id_name is None
        assert vg.cucm_object_id is None
        assert vg.referring_features == []
        assert vg.greeting_type == "DEFAULT"

    def test_model_is_migration_object(self):
        vg = CanonicalVoicemailGroup(
            canonical_id="voicemail_group:support",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
        )
        assert isinstance(vg, MigrationObject)

    def test_registry_contains_voicemail_group(self):
        assert "voicemail_group" in CANONICAL_TYPE_REGISTRY
        assert CANONICAL_TYPE_REGISTRY["voicemail_group"] is CanonicalVoicemailGroup
