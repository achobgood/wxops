# tests/migration/transform/mappers/test_voicemail_enrichment.py
"""Test that VoicemailMapper enriches user objects with voicemail_profile_id."""
from datetime import datetime, timezone
from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.voicemail_mapper import VoicemailMapper


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def test_voicemail_mapper_sets_voicemail_profile_id_on_user():
    """After VoicemailMapper runs, user object must have voicemail_profile_id set."""
    store = MigrationStore(":memory:")

    # User with a voicemail profile
    user = CanonicalUser(
        canonical_id="user:jdoe", provenance=_prov("jdoe"),
        status=MigrationStatus.ANALYZED,
        emails=["jdoe@test.com"], cucm_userid="jdoe",
    )
    store.upsert_object(user)

    # Voicemail profile object
    vm_profile = MigrationObject(
        canonical_id="voicemail_profile:Standard VM",
        provenance=_prov("Standard VM"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"voicemail_profile_name": "Standard VM"},
    )
    store.upsert_object(vm_profile)

    # Cross-ref: user → voicemail profile
    store.add_cross_ref("user:jdoe", "voicemail_profile:Standard VM", "user_has_voicemail_profile")

    mapper = VoicemailMapper()
    mapper.map(store)

    # Re-read user from store — should have voicemail_profile_id
    user_data = store.get_object("user:jdoe")
    assert user_data is not None
    assert user_data.get("voicemail_profile_id") is not None, (
        "VoicemailMapper must set voicemail_profile_id on the user object"
    )
