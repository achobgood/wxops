"""Tests for the normalization pipeline (normalize_discovery entry point).

Verifies that DiscoveryResult.raw_data flows correctly through normalizers
into the store, and that CrossReferenceBuilder runs as pass 2.
"""

import pytest

from wxcli.migration.models import MigrationStatus
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery
from tests.migration.cucm.fixtures import (
    CSS_FIXTURE,
    DATETIME_GROUP_FIXTURE,
    DEVICE_POOL_FIXTURE,
    END_USER_FIXTURE,
    HUNT_PILOT_FIXTURE,
    PHONE_FIXTURE,
    COMMON_AREA_PHONE_FIXTURE,
    ROUTE_PATTERN_FIXTURE,
    VOICEMAIL_PROFILE_FIXTURE,
)


@pytest.fixture
def store():
    s = MigrationStore(":memory:")
    yield s
    s.close()


def _make_raw_data() -> dict:
    """Build a raw_data dict matching DiscoveryResult.raw_data structure."""
    return {
        "locations": {
            "device_pools": [DEVICE_POOL_FIXTURE],
            "datetime_groups": [DATETIME_GROUP_FIXTURE],
            "cucm_locations": [],
        },
        "users": {
            "users": [END_USER_FIXTURE],
        },
        "devices": {
            "phones": [PHONE_FIXTURE, COMMON_AREA_PHONE_FIXTURE],
        },
        "routing": {
            "partitions": [
                {"pkid": "{PT1}", "name": "Internal-PT", "description": "Internal"},
                {"pkid": "{PT2}", "name": "Local-PSTN-PT", "description": "PSTN"},
                {"pkid": "{PT3}", "name": "International-Block-PT", "description": "Block"},
            ],
            "css_list": [CSS_FIXTURE],
            "route_patterns": [ROUTE_PATTERN_FIXTURE],
            "gateways": [],
            "sip_trunks": [],
            "route_groups": [],
            "route_lists": [],
            "translation_patterns": [],
        },
        "features": {
            "hunt_pilots": [HUNT_PILOT_FIXTURE],
            "hunt_lists": [],
            "line_groups": [],
            "cti_route_points": [],
            "call_parks": [],
            "pickup_groups": [],
            "time_schedules": [],
            "time_periods": [],
        },
        "voicemail": {
            "voicemail_profiles": [VOICEMAIL_PROFILE_FIXTURE],
            "voicemail_pilots": [
                {"pkid": "{VP1}", "dirn": "8000", "description": "Main VM pilot"},
            ],
        },
    }


class TestNormalizeDiscovery:
    def test_basic_pipeline(self, store):
        raw_data = _make_raw_data()
        summary = normalize_discovery(raw_data, store)

        # Pass 1 should have normalized objects
        assert summary["pass1"]["total"] > 0
        assert summary["pass1"]["locations/device_pools"] == 1
        assert summary["pass1"]["locations/datetime_groups"] == 1
        assert summary["pass1"]["users/users"] == 1
        assert summary["pass1"]["devices/phones"] == 2  # 1 user phone + 1 common-area
        assert summary["pass1"]["routing/partitions"] == 3
        assert summary["pass1"]["routing/css_list"] == 1
        assert summary["pass1"]["routing/route_patterns"] == 1
        assert summary["pass1"]["features/hunt_pilots"] == 1
        assert summary["pass1"]["voicemail/voicemail_profiles"] == 1
        assert summary["pass1"]["voicemail/voicemail_pilots"] == 1

    def test_workspace_classification(self, store):
        raw_data = _make_raw_data()
        summary = normalize_discovery(raw_data, store)

        # Common-area phone should also be classified as workspace
        assert summary["pass1"]["workspaces_classified"] == 1
        workspaces = store.query_by_type("workspace")
        assert len(workspaces) == 1

    def test_objects_in_store(self, store):
        raw_data = _make_raw_data()
        normalize_discovery(raw_data, store)

        # Spot-check key object types exist in store
        assert store.count_by_type("device_pool") == 1
        assert store.count_by_type("user") == 1
        assert store.count_by_type("device") == 2
        assert store.count_by_type("css") == 1
        assert store.count_by_type("partition") == 3
        assert store.count_by_type("voicemail_profile") == 1

    def test_cross_refs_built(self, store):
        raw_data = _make_raw_data()
        summary = normalize_discovery(raw_data, store)

        # Pass 2 should have built cross-refs
        assert summary["pass2"]["device_has_dn"] > 0
        assert summary["pass2"]["css_contains_partition"] == 3
        assert summary["pass2"]["phones_classified"] > 0

    def test_unity_vm_settings(self, store):
        raw_data = _make_raw_data()
        raw_data["voicemail"]["unity_user_settings"] = {
            "jdoe": {
                "uc_object_id": "uc-obj-1",
                "vm_enabled": True,
                "call_handler_id": "ch-1",
                "notification_enabled": True,
                "notification_destination": "jdoe@acme.com",
                "send_all_calls": False,
                "send_busy_calls": True,
                "send_unanswered_calls": True,
                "unanswered_rings": 4,
                "busy_greeting_type": "DEFAULT",
                "storage_type": "INTERNAL",
                "mwi_enabled": True,
                "external_email": None,
                "email_copy_enabled": False,
                "transfer_to_zero_enabled": True,
                "transfer_to_zero_destination": "0",
                "fax_enabled": False,
                "fax_number": None,
            },
        }
        summary = normalize_discovery(raw_data, store)

        assert summary["pass1"]["unity_vm_settings"] == 1

        # Verify the Unity VM object is in the store
        obj = store.get_object("unity_vm:jdoe")
        assert obj is not None
        state = obj["pre_migration_state"]
        assert state["vm_enabled"] is True
        assert state["notification_destination"] == "jdoe@acme.com"
        assert state["transfer_to_zero_enabled"] is True

    def test_empty_raw_data(self, store):
        """Pipeline handles empty raw_data gracefully."""
        summary = normalize_discovery({}, store)
        assert summary["pass1"]["total"] == 0

    def test_missing_sub_keys(self, store):
        """Pipeline handles missing sub-keys without errors."""
        raw_data = {"locations": {}}  # No device_pools key
        summary = normalize_discovery(raw_data, store)
        assert summary["pass1"].get("locations/device_pools", 0) == 0
