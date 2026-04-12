"""Tests for VoicemailGroupMapper."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    CanonicalVoicemailGroup,
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.voicemail_group_mapper import (
    VoicemailGroupMapper,
)


def _prov(name: str, system: str = "cucm") -> Provenance:
    return Provenance(
        source_system=system,
        source_id=f"uuid-{name}",
        source_name=name,
        cluster="lab",
        extracted_at=datetime.now(timezone.utc),
    )


def _seed_voicemail_group(
    store: MigrationStore,
    name: str,
    extension: str,
    greeting_type: str = "DEFAULT",
    object_id: str | None = None,
) -> None:
    store.upsert_object(MigrationObject(
        canonical_id=f"voicemail_group:{name}",
        provenance=_prov(name, system="unity_connection"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "extension": extension,
            "cucm_object_id": object_id or f"uc-{name}",
            "greeting_type": greeting_type,
            "notification_destination": None,
            "language_code": "en_us",
        },
    ))


def _seed_location(store: MigrationStore, canonical_id: str, name: str) -> None:
    store.upsert_object(CanonicalLocation(
        canonical_id=canonical_id,
        provenance=_prov(name),
        status=MigrationStatus.ANALYZED,
        name=name,
    ))


def _seed_user(
    store: MigrationStore,
    canonical_id: str,
    extension: str,
    location_id: str,
) -> None:
    store.upsert_object(CanonicalUser(
        canonical_id=canonical_id,
        provenance=_prov(canonical_id.split(":", 1)[-1]),
        status=MigrationStatus.ANALYZED,
        extension=extension,
        location_id=location_id,
    ))


class TestBasicMapping:
    def test_single_mailbox_single_location(self):
        """One voicemail group, one location -> canonical object with location."""
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            _seed_voicemail_group(store, "Sales Voicemail", "5896")

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            assert result.objects_created == 1
            vg = store.get_object("voicemail_group:Sales Voicemail")
            # After upsert, the object retrieved is the CanonicalVoicemailGroup
            # dict with the mapper's enrichments.
            assert vg is not None
            assert vg.get("name") == "Sales Voicemail"
            assert vg.get("extension") == "5896"
            assert vg.get("location_id") == "location:HQ"
            assert vg.get("passcode") == "293847"
            assert vg.get("language_code") == "en_us"
            # Should emit MISSING_DATA passcode decision (always)
            passcode_decisions = [
                d for d in result.decisions
                if d.type == DecisionType.MISSING_DATA
                and d.context.get("reason") == "voicemail_group_passcode"
            ]
            assert len(passcode_decisions) == 1
        finally:
            store.close()

    def test_custom_greeting_emits_audio_asset_decision(self):
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            _seed_voicemail_group(
                store, "Sales Voicemail", "5896", greeting_type="CUSTOM"
            )

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            audio_decisions = [
                d for d in result.decisions
                if d.type == DecisionType.AUDIO_ASSET_MANUAL
            ]
            assert len(audio_decisions) == 1
            assert "Sales Voicemail" in audio_decisions[0].summary
        finally:
            store.close()

    def test_extension_conflict_with_user(self):
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            _seed_user(store, "user:jsmith", "5896", "location:HQ")
            _seed_voicemail_group(store, "Sales Voicemail", "5896")

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            ext_conflicts = [
                d for d in result.decisions
                if d.type == DecisionType.EXTENSION_CONFLICT
                and d.context.get("reason") == "voicemail_group_extension_taken"
            ]
            assert len(ext_conflicts) == 1
            ctx = ext_conflicts[0].context
            assert ctx["voicemail_group_id"] == "voicemail_group:Sales Voicemail"
            assert "user:jsmith" in ctx.get("conflicting_user_id", "")
        finally:
            store.close()

    def test_location_ambiguous_multiple_locations_no_user_match(self):
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            _seed_location(store, "location:BR1", "Branch 1")
            _seed_voicemail_group(store, "Sales Voicemail", "5896")

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            loc_ambig = [
                d for d in result.decisions
                if d.type == DecisionType.LOCATION_AMBIGUOUS
            ]
            assert len(loc_ambig) == 1
            vg = store.get_object("voicemail_group:Sales Voicemail")
            # location_id may be None until decision is resolved
            assert vg.get("location_id") in (None, "")
        finally:
            store.close()

    def test_user_extension_match_resolves_location(self):
        """Extension match on a user in one of multiple locations wins."""
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            _seed_location(store, "location:BR1", "Branch 1")
            _seed_user(store, "user:alice", "5000", "location:BR1")
            _seed_voicemail_group(store, "Branch VM", "5000")

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            vg = store.get_object("voicemail_group:Branch VM")
            assert vg is not None
            # Even with extension conflict, location should resolve via user match
            assert vg.get("location_id") == "location:BR1"
        finally:
            store.close()

    def test_notification_destination_plumbed(self):
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")
            store.upsert_object(MigrationObject(
                canonical_id="voicemail_group:Sales Voicemail",
                provenance=_prov("Sales Voicemail", system="unity_connection"),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={
                    "name": "Sales Voicemail",
                    "extension": "5896",
                    "cucm_object_id": "uc-sales",
                    "greeting_type": "DEFAULT",
                    "notification_destination": "sales@example.com",
                    "language_code": "en_us",
                },
            ))

            mapper = VoicemailGroupMapper()
            mapper.map(store)

            vg = store.get_object("voicemail_group:Sales Voicemail")
            assert vg["notifications"] == {
                "enabled": True,
                "destination": "sales@example.com",
            }
        finally:
            store.close()

    def test_no_voicemail_groups_no_decisions(self):
        store = MigrationStore(":memory:")
        try:
            _seed_location(store, "location:HQ", "HQ")

            mapper = VoicemailGroupMapper()
            result = mapper.map(store)

            assert result.objects_created == 0
            assert result.decisions == []
        finally:
            store.close()


class TestEngineRegistration:
    def test_voicemail_group_mapper_exported(self):
        """VoicemailGroupMapper is exported from the mappers package."""
        from wxcli.migration.transform.mappers import VoicemailGroupMapper as Imported
        from wxcli.migration.transform.mappers.voicemail_group_mapper import (
            VoicemailGroupMapper,
        )
        assert Imported is VoicemailGroupMapper

    def test_voicemail_group_mapper_in_order(self):
        """VoicemailGroupMapper runs after FeatureMapper in MAPPER_ORDER."""
        from wxcli.migration.transform.engine import MAPPER_ORDER
        from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper
        from wxcli.migration.transform.mappers.voicemail_group_mapper import (
            VoicemailGroupMapper,
        )

        assert VoicemailGroupMapper in MAPPER_ORDER
        assert MAPPER_ORDER.index(VoicemailGroupMapper) > MAPPER_ORDER.index(FeatureMapper)
