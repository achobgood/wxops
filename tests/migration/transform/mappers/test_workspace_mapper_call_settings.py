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


def _common_area_phone_with_lines(
    name: str,
    *,
    lines: list[dict],
    license_tier: str = "Professional Workspace",
    voicemail_profile: str | None = None,
) -> MigrationObject:
    """Common-area phone fixture with explicit line entries for forwarding/VM tests."""
    state: dict = {
        "name": name,
        "description": f"{name}",
        "is_common_area": True,
        "model": "Cisco 7841",
        "cucm_device_pool": "DP_ConfRooms",
        "lines": lines,
    }
    if voicemail_profile:
        state["voiceMailProfile"] = voicemail_profile
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


class TestVoicemailExtraction:
    def test_no_voicemail_profile_emits_explicit_disabled(self):
        """Most common-area phones have no VM profile — explicitly disable VM on Webex."""
        store = MigrationStore(":memory:")
        store.upsert_object(_common_area_phone_with_lines(
            "lobby-north",
            lines=[{"index": 1, "dirn": {"pattern": "5000"}, "display": "Lobby"}],
        ))

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:lobby-north")
        # This phone has no feature-requiring indicators, so it infers to Workspace tier
        # → only DND + MOH survive the license gate. VM is stripped even though we
        # generated it. Assert that by checking call_settings has no voicemail key.
        assert "voicemail" not in (ws.get("call_settings") or {})

    def test_professional_tier_no_vm_profile_emits_disabled(self):
        """Professional-tier workspace with no VM profile still gets explicit disabled."""
        store = MigrationStore(":memory:")
        # Force Professional tier by setting outgoing_call_permissions (see _infer_license_tier)
        phone = _common_area_phone_with_lines(
            "conf-pro",
            lines=[{"index": 1, "dirn": {"pattern": "5100"}}],
        )
        phone.pre_migration_state["outgoing_call_permissions"] = True
        store.upsert_object(phone)

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-pro")
        assert ws["license_tier"] == "Professional Workspace"
        assert ws["call_settings"]["voicemail"] == {"enabled": False}

    def test_professional_tier_with_vm_profile_emits_enabled(self):
        """Professional-tier workspace with a Unity VM profile gets enabled voicemail."""
        store = MigrationStore(":memory:")
        phone = _common_area_phone_with_lines(
            "conf-vm",
            lines=[{
                "index": 1,
                "dirn": {"pattern": "5200"},
                "callForwardNoAnswer": {
                    "forwardToVoiceMail": "true",
                    "duration": "24",
                },
            }],
            voicemail_profile="Default VM",
        )
        phone.pre_migration_state["outgoing_call_permissions"] = True
        store.upsert_object(phone)

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-vm")
        vm = ws["call_settings"]["voicemail"]
        assert vm["enabled"] is True
        assert vm["sendUnansweredCalls"]["enabled"] is True
        assert vm["sendUnansweredCalls"]["numberOfRings"] == 4  # 24s / 6s per ring


class TestCallForwardingExtraction:
    def test_cfna_to_reception_after_n_rings(self):
        """Lobby phone: forward unanswered to reception after 4 rings."""
        store = MigrationStore(":memory:")
        phone = _common_area_phone_with_lines(
            "lobby-main",
            lines=[{
                "index": 1,
                "dirn": {"pattern": "5000"},
                "callForwardNoAnswer": {
                    "destination": "2000",
                    "duration": "24",  # 24s / 6s = 4 rings
                },
            }],
        )
        # Force Professional tier so the gate keeps callForwarding
        phone.pre_migration_state["outgoing_call_permissions"] = True
        store.upsert_object(phone)

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:lobby-main")
        cf = ws["call_settings"]["callForwarding"]
        assert cf["noAnswer"]["enabled"] is True
        assert cf["noAnswer"]["destination"] == "2000"
        assert cf["noAnswer"]["numberOfRings"] == 4
        # Always and busy must be explicitly disabled so Webex doesn't retain platform default
        assert cf["always"]["enabled"] is False
        assert cf["busy"]["enabled"] is False

    def test_cfa_to_reception(self):
        """Conference room with unconditional forward."""
        store = MigrationStore(":memory:")
        phone = _common_area_phone_with_lines(
            "conf-forward",
            lines=[{
                "index": 1,
                "dirn": {"pattern": "5300"},
                "callForwardAll": {"destination": "1000"},
            }],
        )
        phone.pre_migration_state["outgoing_call_permissions"] = True
        store.upsert_object(phone)

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-forward")
        cf = ws["call_settings"]["callForwarding"]
        assert cf["always"]["enabled"] is True
        assert cf["always"]["destination"] == "1000"

    def test_no_forwarding_omits_key(self):
        """Phones without any forwarding destination don't emit callForwarding at all."""
        store = MigrationStore(":memory:")
        phone = _common_area_phone_with_lines(
            "conf-plain",
            lines=[{"index": 1, "dirn": {"pattern": "5400"}}],
        )
        phone.pre_migration_state["outgoing_call_permissions"] = True
        store.upsert_object(phone)

        WorkspaceMapper().map(store)

        ws = store.get_object("workspace:conf-plain")
        assert "callForwarding" not in (ws.get("call_settings") or {})
