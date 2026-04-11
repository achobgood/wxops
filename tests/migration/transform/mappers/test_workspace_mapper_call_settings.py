# tests/migration/transform/mappers/test_workspace_mapper_call_settings.py
"""Tests for WorkspaceMapper call_settings extraction."""
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalWorkspace, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


class TestCanonicalWorkspaceCallSettings:
    def test_call_settings_field_roundtrips_through_store(self):
        """CanonicalWorkspace accepts call_settings dict and stores it."""
        store = MigrationStore(":memory:")
        ws = CanonicalWorkspace(
            canonical_id="workspace:conf-room-3a",
            provenance=_prov("conf-room-3a"),
            status=MigrationStatus.ANALYZED,
            display_name="Conf Room 3A",
            is_common_area=True,
            license_tier="Professional Workspace",
            call_settings={"doNotDisturb": {"enabled": True, "ringSplashEnabled": False}},
        )
        store.upsert_object(ws)
        got = store.get_object("workspace:conf-room-3a")
        assert got is not None
        assert got.get("call_settings") == {
            "doNotDisturb": {"enabled": True, "ringSplashEnabled": False}
        }


def _common_area_phone(
    name: str = "conf-3a",
    *,
    dnd_status: str | bool | None = None,
    dnd_option: str | None = None,
) -> MigrationObject:
    """Build a raw phone MigrationObject matching the shape saved by the normalizer."""
    state: dict = {
        "name": name,
        "description": f"Conference Room {name}",
        "is_common_area": True,
        "model": "Cisco 7841",
        "cucm_device_pool": "DP_ConfRooms",
    }
    if dnd_status is not None:
        state["dndStatus"] = dnd_status
    if dnd_option is not None:
        state["dndOption"] = dnd_option
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


class TestDNDExtraction:
    def test_dnd_enabled_call_reject(self):
        """dndStatus=true, dndOption='Call Reject' → doNotDisturb enabled, ringSplash off."""
        store = MigrationStore(":memory:")
        store.upsert_object(_common_area_phone(
            "conf-3a", dnd_status="true", dnd_option="Call Reject",
        ))

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-3a")
        assert ws is not None
        assert ws["call_settings"]["doNotDisturb"] == {
            "enabled": True,
            "ringSplashEnabled": False,
        }

    def test_dnd_enabled_ringer_off(self):
        """dndOption='Ringer Off' → ringSplashEnabled=True (closest Webex analogue)."""
        store = MigrationStore(":memory:")
        store.upsert_object(_common_area_phone(
            "conf-3b", dnd_status=True, dnd_option="Ringer Off",
        ))

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-3b")
        assert ws["call_settings"]["doNotDisturb"]["enabled"] is True
        assert ws["call_settings"]["doNotDisturb"]["ringSplashEnabled"] is True

    def test_dnd_disabled_emits_explicit_off(self):
        """dndStatus=false → doNotDisturb enabled=False (explicit override of Webex default)."""
        store = MigrationStore(":memory:")
        store.upsert_object(_common_area_phone("lobby-1", dnd_status="false"))

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:lobby-1")
        assert ws["call_settings"]["doNotDisturb"] == {
            "enabled": False,
            "ringSplashEnabled": False,
        }
