"""End-to-end test: raw common-area phones → mapped workspaces → planned ops."""
from datetime import datetime, timezone

from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.models import (
    MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _phone(name: str, state_extra: dict) -> MigrationObject:
    base = {
        "name": name,
        "description": f"{name} desc",
        "is_common_area": True,
        "model": "Cisco 7841",
        "cucm_device_pool": "DP_ConfRooms",
    }
    base.update(state_extra)
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=base,
    )


class TestWorkspacePipelineIntegration:
    def test_three_common_area_phones_produce_gated_settings(self):
        """Basic lobby (Workspace tier), pro conf (Professional), pro lobby w/ forwarding."""
        store = MigrationStore(":memory:")

        # Phone A: basic lobby with DND only — infers Workspace tier
        store.upsert_object(_phone("lobby-a", {
            "dndStatus": "true",
            "dndOption": "Call Reject",
            "lines": [{"index": 1, "dirn": {"pattern": "5001"}}],
        }))

        # Phone B: conference room, privacy + outgoing permissions → Professional
        store.upsert_object(_phone("conf-b", {
            "privacy": "On",
            "outgoing_call_permissions": True,
            "lines": [{"index": 1, "dirn": {"pattern": "5002"}}],
        }))

        # Phone C: pro lobby with CFNA → reception + no voicemail
        store.upsert_object(_phone("lobby-c", {
            "outgoing_call_permissions": True,
            "lines": [{
                "index": 1,
                "dirn": {"pattern": "5003"},
                "callForwardNoAnswer": {
                    "destination": "2000",
                    "duration": "24",
                },
            }],
        }))

        # Run the mapper
        result = WorkspaceMapper().map(store)
        assert result.objects_created == 3

        # Check call_settings on each workspace
        ws_a = store.get_object("workspace:lobby-a")
        ws_b = store.get_object("workspace:conf-b")
        ws_c = store.get_object("workspace:lobby-c")

        assert ws_a["license_tier"] == "Workspace"
        assert ws_a["call_settings"]["doNotDisturb"]["enabled"] is True
        assert "voicemail" not in ws_a["call_settings"]
        assert "callForwarding" not in ws_a["call_settings"]

        assert ws_b["license_tier"] == "Professional Workspace"
        assert ws_b["call_settings"]["privacy"] == {"enabled": True}
        assert ws_b["call_settings"]["voicemail"] == {"enabled": False}

        assert ws_c["license_tier"] == "Professional Workspace"
        cf = ws_c["call_settings"]["callForwarding"]
        assert cf["noAnswer"]["destination"] == "2000"
        assert cf["noAnswer"]["numberOfRings"] == 4
        assert ws_c["call_settings"]["voicemail"] == {"enabled": False}

        # The mapper already upserted workspaces with status=ANALYZED, so
        # expand_to_operations picks them up directly. No status patching needed.
        ops = expand_to_operations(store)
        configure_cids = {
            op.canonical_id
            for op in ops
            if op.resource_type == "workspace" and op.op_type == "configure_settings"
        }
        assert configure_cids == {
            "workspace:lobby-a",
            "workspace:conf-b",
            "workspace:lobby-c",
        }

        # The runtime attaches data at dispatch time via store.get_object().
        # Simulate that lookup and verify each workspace carries its call_settings.
        for cid in configure_cids:
            obj = store.get_object(cid)
            assert obj is not None
            assert obj.get("call_settings"), f"{cid} missing call_settings in store"

        # Spot-check license-gated content one more time through the store path
        assert store.get_object("workspace:lobby-a")["call_settings"] == {
            "doNotDisturb": {"enabled": True, "ringSplashEnabled": False}
        }
