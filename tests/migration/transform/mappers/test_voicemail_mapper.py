"""Tests for voicemail_mapper: Unity Connection VM -> Webex per-person voicemail.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.voicemail_mapper import VoicemailMapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _user(
    name: str = "jdoe",
    cucm_userid: str | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "cucm_userid": cucm_userid or name,
    }
    return MigrationObject(
        canonical_id=f"user:{name}",
        provenance=_provenance(source_id=f"uuid-user-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _voicemail_profile(
    name: str = "VM-Standard",
    **settings: object,
) -> MigrationObject:
    state: dict = {"voicemail_profile_name": name, **settings}
    return MigrationObject(
        canonical_id=f"voicemail_profile_cucm:{name}",
        provenance=_provenance(source_id=f"uuid-vmp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _vm_settings_object(
    profile_name: str = "VM-Standard",
    **settings: object,
) -> MigrationObject:
    state: dict = {"voicemail_profile_name": profile_name, **settings}
    return MigrationObject(
        canonical_id=f"vm_settings:{profile_name}",
        provenance=_provenance(source_id=f"uuid-vms-{profile_name}", name=profile_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _unity_vm(
    userid: str = "jdoe",
    **settings: object,
) -> MigrationObject:
    state: dict = {**settings}
    return MigrationObject(
        canonical_id=f"unity_vm:{userid}",
        provenance=_provenance(source_id=f"uuid-uvm-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_user_with_vm(
    store: MigrationStore,
    user_name: str = "jdoe",
    profile_name: str = "VM-Standard",
    profile_settings: dict | None = None,
    vm_detail_settings: dict | None = None,
    unity_vm_settings: dict | None = None,
) -> str:
    """Seed a user with voicemail profile, settings, and optional unity_vm.

    Returns the user canonical_id.
    """
    user = _user(user_name, cucm_userid=user_name)
    store.upsert_object(user)

    vm_profile = _voicemail_profile(profile_name, **(profile_settings or {}))
    store.upsert_object(vm_profile)
    store.add_cross_ref(user.canonical_id, vm_profile.canonical_id, "user_has_voicemail_profile")

    if vm_detail_settings:
        vm_settings = _vm_settings_object(profile_name, **vm_detail_settings)
        store.upsert_object(vm_settings)
        store.add_cross_ref(
            vm_profile.canonical_id, vm_settings.canonical_id, "voicemail_profile_settings"
        )

    if unity_vm_settings:
        unity_vm = _unity_vm(user_name, **unity_vm_settings)
        store.upsert_object(unity_vm)

    return user.canonical_id


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestVoicemailMapperHappyPath:
    """Basic voicemail profile mapping."""

    def test_user_with_vm_profile_produces_canonical_voicemail(self):
        """User with voicemail profile -> CanonicalVoicemailProfile created."""
        store = _make_store()
        _seed_user_with_vm(store, "jdoe", "VM-Standard")

        mapper = VoicemailMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert len(mapped) == 1
        assert mapped[0]["enabled"] is True
        assert mapped[0]["user_canonical_id"] == "user:jdoe"

    def test_user_without_vm_profile_skipped(self):
        """User without voicemail profile -> no VM object created."""
        store = _make_store()
        user = _user("noprofile")
        store.upsert_object(user)

        mapper = VoicemailMapper()
        result = mapper.map(store)

        assert result.objects_created == 0

    def test_cfna_18_seconds_produces_3_rings(self):
        """CFNA timeout 18 seconds -> numberOfRings=3 (18/6=3)."""
        store = _make_store()
        _seed_user_with_vm(
            store, "alice", "VM-Standard",
            unity_vm_settings={"cfnaTimeout": 18},
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["send_unanswered_calls"]["numberOfRings"] == 3

    def test_cfna_30_seconds_produces_5_rings(self):
        """CFNA timeout 30 seconds -> numberOfRings=5 (30/6=5)."""
        store = _make_store()
        _seed_user_with_vm(
            store, "bob", "VM-Standard",
            unity_vm_settings={"cfnaTimeout": 30},
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["send_unanswered_calls"]["numberOfRings"] == 5

    def test_cfna_clamps_to_max_20_rings(self):
        """CFNA timeout 180 seconds -> clamped to 20 rings (not 30)."""
        store = _make_store()
        _seed_user_with_vm(
            store, "carol", "VM-Standard",
            unity_vm_settings={"cfnaTimeout": 180},
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["send_unanswered_calls"]["numberOfRings"] == 20

    def test_cfna_clamps_minimum_1_ring(self):
        """CFNA timeout 2 seconds -> minimum 1 ring (2/6 < 1, clamped to 1)."""
        store = _make_store()
        _seed_user_with_vm(
            store, "dan", "VM-Standard",
            unity_vm_settings={"cfnaTimeout": 2},
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["send_unanswered_calls"]["numberOfRings"] == 1

    def test_profile_settings_joined_with_unity_vm(self):
        """Profile settings + unity_vm per-user settings are merged."""
        store = _make_store()
        _seed_user_with_vm(
            store, "eve", "VM-Standard",
            profile_settings={"notificationEnabled": True},
            unity_vm_settings={
                "cfnaTimeout": 24,
                "notificationEmail": "eve@example.com",
            },
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["notifications"]["enabled"] is True
        assert mapped[0]["notifications"]["destination"] == "eve@example.com"
        assert mapped[0]["send_unanswered_calls"]["numberOfRings"] == 4  # 24/6


class TestVoicemailMapperTransferAndStorage:
    """Transfer-to-number and message storage settings."""

    def test_transfer_to_zero(self):
        """Unity Connection transfer-to-zero -> transferToNumber."""
        store = _make_store()
        _seed_user_with_vm(
            store, "frank", "VM-Standard",
            unity_vm_settings={
                "transferToZero": True,
                "transferToZeroDestination": "5000",
            },
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["transfer_to_number"]["enabled"] is True
        assert mapped[0]["transfer_to_number"]["destination"] == "5000"

    def test_external_storage_with_email(self):
        """External storage with email -> storageType=EXTERNAL + externalEmail."""
        store = _make_store()
        _seed_user_with_vm(
            store, "grace", "VM-Standard",
            unity_vm_settings={
                "storageType": "EXTERNAL",
                "externalEmail": "grace@hosted.com",
            },
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["message_storage"]["storageType"] == "EXTERNAL"
        assert mapped[0]["message_storage"]["externalEmail"] == "grace@hosted.com"

    def test_external_storage_without_email_falls_back_to_internal(self):
        """External storage without externalEmail -> falls back to INTERNAL.

        (from 03b-transform-mappers.md §9: edge case)
        """
        store = _make_store()
        _seed_user_with_vm(
            store, "hank", "VM-Standard",
            unity_vm_settings={"storageType": "EXTERNAL"},
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert mapped[0]["message_storage"]["storageType"] == "INTERNAL"


# ---------------------------------------------------------------------------
# Tests — gap analysis (13-row table from §11)
# ---------------------------------------------------------------------------


class TestVoicemailMapperGapDetection:
    """Gap detection from §11: Unity Connection features without Webex equivalent."""

    def test_caller_input_rules_produces_incompatible_decision(self):
        """callerInputRules configured -> VOICEMAIL_INCOMPATIBLE."""
        store = _make_store()
        _seed_user_with_vm(
            store, "iris", "VM-Standard",
            unity_vm_settings={"callerInputRules": [{"key": "1", "dest": "5001"}]},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gaps = vm_decisions[0].context["gaps"]
        gap_keys = [g["feature"] for g in gaps]
        assert "caller_input_rules" in gap_keys

    def test_pager_sms_notification_produces_incompatible_decision(self):
        """Pager/SMS notification -> VOICEMAIL_INCOMPATIBLE."""
        store = _make_store()
        _seed_user_with_vm(
            store, "jack", "VM-Standard",
            unity_vm_settings={"pagerNotification": True},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gap_keys = [g["feature"] for g in vm_decisions[0].context["gaps"]]
        assert "pager_sms_notification" in gap_keys

    def test_multiple_gaps_produce_single_decision(self):
        """Multiple UC features -> single VOICEMAIL_INCOMPATIBLE with all gaps listed."""
        store = _make_store()
        _seed_user_with_vm(
            store, "kate", "VM-Standard",
            unity_vm_settings={
                "callerInputRules": [{"key": "1"}],
                "pagerNotification": True,
                "liveRecord": True,
            },
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gaps = vm_decisions[0].context["gaps"]
        assert len(gaps) >= 3
        gap_keys = {g["feature"] for g in gaps}
        assert "caller_input_rules" in gap_keys
        assert "pager_sms_notification" in gap_keys
        assert "live_record" in gap_keys

    def test_fax_with_internal_storage_produces_incompatible(self):
        """Fax enabled + internal storage -> VOICEMAIL_INCOMPATIBLE."""
        store = _make_store()
        _seed_user_with_vm(
            store, "leon", "VM-Standard",
            unity_vm_settings={
                "faxEnabled": True,
                "storageType": "INTERNAL",
            },
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gap_keys = [g["feature"] for g in vm_decisions[0].context["gaps"]]
        assert "fax_internal_storage" in gap_keys

    def test_fax_with_external_storage_no_fax_gap(self):
        """Fax enabled + external storage -> no fax gap (fax works with external)."""
        store = _make_store()
        _seed_user_with_vm(
            store, "mia", "VM-Standard",
            unity_vm_settings={
                "faxEnabled": True,
                "storageType": "EXTERNAL",
                "externalEmail": "mia@hosted.com",
                "faxPhoneNumber": "+15551234567",
            },
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        # Should be no fax-specific gap (might be 0 decisions total)
        for d in vm_decisions:
            gap_keys = [g["feature"] for g in d.context["gaps"]]
            assert "fax_internal_storage" not in gap_keys

    def test_no_gaps_no_incompatible_decision(self):
        """Basic VM with no UC-only features -> no VOICEMAIL_INCOMPATIBLE decision."""
        store = _make_store()
        _seed_user_with_vm(
            store, "nate", "VM-Standard",
            unity_vm_settings={
                "cfnaTimeout": 18,
                "notificationEnabled": True,
                "notificationEmail": "nate@example.com",
            },
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 0

    def test_alternate_extensions_detected(self):
        """Alternate extensions -> VOICEMAIL_INCOMPATIBLE."""
        store = _make_store()
        _seed_user_with_vm(
            store, "olga", "VM-Standard",
            unity_vm_settings={"alternateExtensions": ["5501", "5502"]},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gap_keys = [g["feature"] for g in vm_decisions[0].context["gaps"]]
        assert "alternate_extensions" in gap_keys

    def test_vpim_networking_detected(self):
        """VPIM enabled -> VOICEMAIL_INCOMPATIBLE."""
        store = _make_store()
        _seed_user_with_vm(
            store, "pete", "VM-Standard",
            unity_vm_settings={"vpimEnabled": True},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) == 1
        gap_keys = [g["feature"] for g in vm_decisions[0].context["gaps"]]
        assert "vpim_networking" in gap_keys


# ---------------------------------------------------------------------------
# Tests — custom greeting MISSING_DATA decisions
# ---------------------------------------------------------------------------


class TestVoicemailMapperCustomGreetings:
    """Custom greeting handling."""

    def test_custom_greeting_produces_missing_data_decision(self):
        """Custom greeting -> MISSING_DATA decision."""
        store = _make_store()
        _seed_user_with_vm(
            store, "quinn", "VM-Standard",
            unity_vm_settings={"customBusyGreeting": "busy_greeting.wav"},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        missing = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "custom_greeting_not_extractable"
        ]
        assert len(missing) == 1

    def test_no_custom_greeting_no_missing_data(self):
        """No custom greeting -> no MISSING_DATA decision for greetings."""
        store = _make_store()
        _seed_user_with_vm(
            store, "rachel", "VM-Standard",
            unity_vm_settings={"cfnaTimeout": 18},
        )

        mapper = VoicemailMapper()
        result = mapper.map(store)

        missing = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "custom_greeting_not_extractable"
        ]
        assert len(missing) == 0


# ---------------------------------------------------------------------------
# Tests — read-only field stripping
# ---------------------------------------------------------------------------


class TestVoicemailMapperReadOnlyFields:
    """Verify read-only fields are not in the canonical output."""

    def test_read_only_fields_not_in_output(self):
        """voiceMessageForwardingEnabled, greetingUploaded, systemMaxNumberOfRings stripped."""
        store = _make_store()
        _seed_user_with_vm(
            store, "sam", "VM-Standard",
            profile_settings={
                "voiceMessageForwardingEnabled": True,
                "greetingUploaded": True,
                "systemMaxNumberOfRings": 20,
            },
        )

        mapper = VoicemailMapper()
        mapper.map(store)

        vms = store.get_objects("voicemail_profile")
        mapped = [v for v in vms if v["status"] == "analyzed"]
        assert len(mapped) == 1
        vm = mapped[0]

        # The canonical model should NOT have these read-only fields at the top level
        # (they're not fields on CanonicalVoicemailProfile)
        assert "voiceMessageForwardingEnabled" not in vm
        assert "voice_message_forwarding_enabled" not in vm
        assert "greetingUploaded" not in vm
        assert "greeting_uploaded" not in vm
        assert "systemMaxNumberOfRings" not in vm
        assert "system_max_number_of_rings" not in vm

        # But the standard fields ARE present
        assert vm["enabled"] is True
        assert "send_unanswered_calls" in vm
        assert "send_busy_calls" in vm
