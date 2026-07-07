"""Tests for workspace_mapper: CUCM Common-area Phones -> Webex Workspaces.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper


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


def _common_area_phone(
    name: str = "SEPCA001122AABB",
    model: str = "Cisco 6841",
    protocol: str = "SIP",
    description: str | None = None,
    cucm_device_pool: str = "Lobby-Phones",
    enable_extension_mobility: bool = False,
    call_recording_enabled: bool = False,
    voicemail_enabled: bool = False,
    custom_greetings: bool = False,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "model": model,
        "protocol": protocol,
        "is_common_area": True,
        "cucm_device_pool": cucm_device_pool,
        "enableExtensionMobility": enable_extension_mobility,
        "call_recording_enabled": call_recording_enabled,
        "voicemail_enabled": voicemail_enabled,
        "custom_greetings": custom_greetings,
    }
    if description:
        state["description"] = description

    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_location_chain(store: MigrationStore, dp_name: str = "Lobby-Phones") -> str:
    """Seed a device pool and location for common-area phones."""
    dp = MigrationObject(
        canonical_id=f"device_pool:{dp_name}",
        provenance=_provenance(source_id=f"uuid-dp-{dp_name}", name=dp_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"device_pool_name": dp_name},
    )
    store.upsert_object(dp)

    loc = CanonicalLocation(
        canonical_id=f"location:{dp_name}",
        provenance=_provenance(source_id=f"uuid-loc-{dp_name}", name=dp_name),
        status=MigrationStatus.ANALYZED,
        name=dp_name,
        address=LocationAddress(country="US"),
    )
    store.upsert_object(loc)
    store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
    return loc.canonical_id


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestWorkspaceMapperHappyPath:
    """Common-area phone -> CanonicalWorkspace."""

    def test_common_area_phone_produces_workspace(self):
        store = _make_store()
        loc_id = _seed_location_chain(store)
        phone = _common_area_phone(description="Lobby Phone 1")
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        workspaces = store.get_objects("workspace")
        assert len(workspaces) == 1

        ws = workspaces[0]
        assert ws["display_name"] == "Lobby Phone 1"
        assert ws["location_id"] == loc_id
        assert ws["calling_type"] == "webexCalling"
        assert ws["is_common_area"] is True
        assert ws["status"] == "analyzed"

    def test_calling_type_always_webex_calling(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone()
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["calling_type"] == "webexCalling"

    def test_supported_devices_phones_for_mpp(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone(model="Cisco 6841")
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["supported_devices"] == "phones"

    def test_supported_devices_collaboration_for_room_device(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone(
            name="TelePresence-Room-1",
            model="Cisco Webex Room Kit",
        )
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["supported_devices"] == "collaborationDevices"

    def test_non_common_area_phones_skipped(self):
        """Non-common-area phones should NOT be processed by workspace_mapper."""
        store = _make_store()
        _seed_location_chain(store)
        phone = MigrationObject(
            canonical_id="phone:SEP001122AABBCC",
            provenance=_provenance("uuid-phone-1", "SEP001122AABBCC"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SEP001122AABBCC",
                "model": "Cisco 6841",
                "is_common_area": False,
            },
        )
        store.upsert_object(phone)

        mapper = WorkspaceMapper()
        result = mapper.map(store)

        assert result.objects_created == 0


# ---------------------------------------------------------------------------
# Tests — decisions
# ---------------------------------------------------------------------------


class TestWorkspaceMapperDecisions:
    """Decision generation for workspace edge cases."""

    def test_hotdesk_dn_conflict_decision(self):
        """Device with both DN and hoteling -> HOTDESK_DN_CONFLICT."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone(
            name="SEP_HOTDESK",
            enable_extension_mobility=True,
        )
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )
        # Add a DN cross-ref so the phone has an extension
        dn = MigrationObject(
            canonical_id="dn:1001:<None>",
            provenance=_provenance("uuid-dn-1001", "1001"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"pattern": "1001"},
        )
        store.upsert_object(dn)
        store.add_cross_ref(phone.canonical_id, dn.canonical_id, "device_has_dn")

        mapper = WorkspaceMapper()
        result = mapper.map(store)

        # Should have HOTDESK_DN_CONFLICT among decisions
        decision_types = [d.type.value for d in result.decisions]
        assert "HOTDESK_DN_CONFLICT" in decision_types

    def test_workspace_license_tier_decision_always_generated(self):
        """WORKSPACE_LICENSE_TIER decision is always generated."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone()
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        result = mapper.map(store)

        decision_types = [d.type.value for d in result.decisions]
        assert "WORKSPACE_LICENSE_TIER" in decision_types

    def test_workspace_type_uncertain_for_generic_pool(self):
        """Generic device pool name -> WORKSPACE_TYPE_UNCERTAIN decision."""
        store = _make_store()
        # Use a generic pool name that doesn't match any hints
        _seed_location_chain(store, dp_name="Default")
        phone = _common_area_phone(
            name="SEP_GENERIC",
            cucm_device_pool="Default",
            description="Phone 42",
        )
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Default", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        result = mapper.map(store)

        decision_types = [d.type.value for d in result.decisions]
        assert "WORKSPACE_TYPE_UNCERTAIN" in decision_types

        # Workspace type defaults to "other" when uncertain
        workspaces = store.get_objects("workspace")
        assert workspaces[0]["workspace_type"] == "other"

    def test_meeting_room_inferred_from_description(self):
        """'Conference' in description -> workspace_type = meetingRoom."""
        store = _make_store()
        _seed_location_chain(store, dp_name="Conference-Rooms")
        phone = _common_area_phone(
            name="SEP_CONFROOM",
            cucm_device_pool="Conference-Rooms",
            description="Conference Room A",
        )
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Conference-Rooms", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["workspace_type"] == "meetingRoom"

    def test_professional_tier_for_recording_enabled(self):
        """Call recording enabled -> Professional Workspace license tier."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone(call_recording_enabled=True)
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["license_tier"] == "Professional Workspace"

    def test_workspace_tier_for_simple_phone(self):
        """Simple phone with no advanced features -> Workspace license tier."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _common_area_phone()
        store.upsert_object(phone)
        store.add_cross_ref(
            phone.canonical_id, "device_pool:Lobby-Phones", "common_area_device_in_pool"
        )

        mapper = WorkspaceMapper()
        mapper.map(store)

        workspaces = store.get_objects("workspace")
        assert workspaces[0]["license_tier"] == "Workspace"
