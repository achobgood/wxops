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
