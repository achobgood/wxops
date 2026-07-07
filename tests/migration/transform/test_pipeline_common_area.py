# tests/migration/transform/test_pipeline_common_area.py
"""Test that common-area phones get is_common_area flag in pre_migration_state."""
from datetime import datetime, timezone
from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def test_common_area_phone_gets_is_common_area_flag():
    """Phone objects for common-area devices must have is_common_area=True in pre_migration_state."""
    store = MigrationStore(":memory:")

    # Raw discovery data with one common-area phone (no owner, class=Phone)
    raw_data = {
        "devices": {
            "phones": [
                {
                    "name": "SEP_LOBBY",
                    "pkid": "pk-lobby",
                    "class": "Phone",
                    "model": "Cisco 8841",
                    "ownerUserName": None,
                    "description": "Lobby Phone",
                    "devicePoolName": {"_value_1": "DP-HQ"},
                    "lines": [{"index": "1", "dirn": {"pattern": "9999"}}],
                },
                {
                    "name": "SEP_USER",
                    "pkid": "pk-user",
                    "class": "Phone",
                    "model": "Cisco 8845",
                    "ownerUserName": {"_value_1": "jdoe"},
                    "description": "John Doe - 8845",
                    "devicePoolName": {"_value_1": "DP-HQ"},
                    "lines": [{"index": "1", "dirn": {"pattern": "1001"}}],
                },
            ],
        },
        "users": {
            "users": [
                {
                    "pkid": "pk-jdoe",
                    "userid": "jdoe",
                    "firstName": "John",
                    "lastName": "Doe",
                    "mailid": "jdoe@test.com",
                },
            ],
        },
    }

    normalize_discovery(raw_data, store)

    # Common-area phone should have is_common_area=True
    lobby = store.get_object("phone:SEP_LOBBY")
    assert lobby is not None
    state = lobby.get("pre_migration_state") or {}
    assert state.get("is_common_area") is True, (
        "Common-area phone must have is_common_area=True in pre_migration_state"
    )

    # User-owned phone should NOT have is_common_area=True
    user_phone = store.get_object("phone:SEP_USER")
    assert user_phone is not None
    user_state = user_phone.get("pre_migration_state") or {}
    assert user_state.get("is_common_area") is not True, (
        "User-owned phone must not have is_common_area=True"
    )
