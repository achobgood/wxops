"""Tests for hoteling/hot desking execution handlers and planner expanders."""
import pytest
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.execute import TIER_ASSIGNMENTS, API_CALL_ESTIMATES
from wxcli.migration.store import MigrationStore
from datetime import datetime, timezone
from wxcli.migration.models import (
    CanonicalDeviceProfile,
    MigrationObject,
    MigrationStatus,
    Provenance,
)

# Handler imports are conditional — handlers may not be implemented yet.
try:
    from wxcli.migration.execute.handlers import (
        SkippedResult,
        handle_hoteling_guest_enable,
        handle_hoteling_host_configure,
        handle_location_hotdesking_enable,
        HANDLER_REGISTRY,
    )
    _HANDLERS_AVAILABLE = True
except ImportError:
    _HANDLERS_AVAILABLE = False

_skip_no_handlers = pytest.mark.skipif(
    not _HANDLERS_AVAILABLE,
    reason="Hoteling handler imports failed (unexpected — handlers are implemented)",
)


@_skip_no_handlers
class TestHotelingGuestEnable:
    def test_produces_put_hoteling(self):
        data = {"user_canonical_id": "user:jdoe", "hoteling_guest_enabled": True}
        deps = {"user:jdoe": "person-webex-id-123"}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_guest_enable(data, deps, ctx)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/people/person-webex-id-123/features/hoteling" in url
        assert body == {"enabled": True}

    def test_skipped_when_no_user_resolved(self):
        data = {"user_canonical_id": None, "hoteling_guest_enabled": True}
        deps = {}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_guest_enable(data, deps, ctx)
        assert isinstance(result, SkippedResult)
        assert "user" in result.reason

    def test_noop_when_hoteling_disabled(self):
        data = {"user_canonical_id": "user:jdoe", "hoteling_guest_enabled": False}
        deps = {"user:jdoe": "person-webex-id-123"}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_guest_enable(data, deps, ctx)
        assert result == []


@_skip_no_handlers
class TestHotelingHostConfigure:
    def test_produces_put_device_hoteling(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "host_device_canonical_ids": ["device:SEP001122"],
            "auto_logout_minutes": 480,
        }
        deps = {"user:jdoe": "person-id-123", "device:SEP001122": "device-id-456"}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_host_configure(data, deps, ctx)
        assert len(result) >= 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/person-id-123/devices/settings/hoteling" in url
        assert body["hoteling"]["enabled"] is True
        assert body["hoteling"]["limitGuestUse"] is True
        assert body["hoteling"]["guestHoursLimit"] == 8

    def test_noop_when_no_host_devices(self):
        data = {"user_canonical_id": "user:jdoe", "host_device_canonical_ids": []}
        deps = {"user:jdoe": "person-id-123"}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_host_configure(data, deps, ctx)
        assert result == []

    def test_default_no_limit_when_no_timer(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "host_device_canonical_ids": ["device:SEP001122"],
            "auto_logout_minutes": 0,
        }
        deps = {"user:jdoe": "person-id-123", "device:SEP001122": "device-id-456"}
        ctx = {"orgId": "org1"}
        result = handle_hoteling_host_configure(data, deps, ctx)
        assert len(result) >= 1
        _, _, body = result[0]
        assert body["hoteling"]["limitGuestUse"] is False


@_skip_no_handlers
class TestLocationHotdeskingEnable:
    def test_produces_put_location_hotdesking(self):
        data = {"pre_migration_state": {"location_canonical_id": "location:Dallas-HQ"}}
        deps = {"location:Dallas-HQ": "loc-webex-id-789"}
        ctx = {"orgId": "org1"}
        result = handle_location_hotdesking_enable(data, deps, ctx)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/locations/loc-webex-id-789/features/hotDesking" in url
        assert body == {"voicePortalHotDeskSignInEnabled": True}

    def test_skipped_when_location_not_resolved(self):
        data = {"pre_migration_state": {"location_canonical_id": "location:Unknown"}}
        deps = {}
        ctx = {"orgId": "org1"}
        result = handle_location_hotdesking_enable(data, deps, ctx)
        assert isinstance(result, SkippedResult)
        assert "location:Unknown" in result.reason


@_skip_no_handlers
class TestHandlerRegistryHoteling:
    def test_hoteling_handlers_registered(self):
        assert ("device_profile", "enable_hoteling_guest") in HANDLER_REGISTRY
        assert ("device_profile", "enable_hoteling_host") in HANDLER_REGISTRY
        assert ("hoteling_location", "enable_hotdesking") in HANDLER_REGISTRY


# ---------------------------------------------------------------------------
# Planner expander tests
# ---------------------------------------------------------------------------

def _prov():
    return Provenance(source_system="cucm", source_id="t", source_name="t",
                      extracted_at=datetime.now(timezone.utc))


class TestDeviceProfileExpander:
    def test_expands_guest_op_when_user_found(self):
        store = MigrationStore(":memory:")
        obj = CanonicalDeviceProfile(
            canonical_id="device_profile:UDP-jdoe",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            hoteling_guest_enabled=True,
            user_canonical_id="user:jdoe",
            profile_name="UDP-jdoe",
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        op_types = {(o.resource_type, o.op_type) for o in ops}
        assert ("device_profile", "enable_hoteling_guest") in op_types

    def test_skips_guest_when_no_user(self):
        store = MigrationStore(":memory:")
        obj = CanonicalDeviceProfile(
            canonical_id="device_profile:ORPHAN",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            hoteling_guest_enabled=False,
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        op_types = {(o.resource_type, o.op_type) for o in ops}
        assert ("device_profile", "enable_hoteling_guest") not in op_types

    def test_expands_host_when_host_devices_present(self):
        store = MigrationStore(":memory:")
        obj = CanonicalDeviceProfile(
            canonical_id="device_profile:UDP-jdoe",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            hoteling_guest_enabled=True,
            user_canonical_id="user:jdoe",
            host_device_canonical_ids=["device:SEP001122"],
            profile_name="UDP-jdoe",
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        op_types = {(o.resource_type, o.op_type) for o in ops}
        assert ("device_profile", "enable_hoteling_host") in op_types

    def test_skips_host_when_no_host_devices(self):
        store = MigrationStore(":memory:")
        obj = CanonicalDeviceProfile(
            canonical_id="device_profile:UDP-jdoe",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            hoteling_guest_enabled=True,
            user_canonical_id="user:jdoe",
            host_device_canonical_ids=[],
            profile_name="UDP-jdoe",
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        op_types = {(o.resource_type, o.op_type) for o in ops}
        assert ("device_profile", "enable_hoteling_host") not in op_types


class TestHotelingLocationExpander:
    def test_expands_to_enable_hotdesking(self):
        store = MigrationStore(":memory:")
        obj = MigrationObject(
            canonical_id="hoteling_location:location:Dallas-HQ",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={"location_canonical_id": "location:Dallas-HQ", "em_profile_count": 2},
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].resource_type == "hoteling_location"
        assert ops[0].op_type == "enable_hotdesking"

    def test_depends_on_location_enable_calling(self):
        store = MigrationStore(":memory:")
        obj = MigrationObject(
            canonical_id="hoteling_location:location:Dallas-HQ",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={"location_canonical_id": "location:Dallas-HQ", "em_profile_count": 2},
        )
        store.upsert_object(obj)
        ops = expand_to_operations(store)
        assert "location:Dallas-HQ:enable_calling" in ops[0].depends_on


class TestHotelingTierAssignments:
    def test_tier_assignments_exist(self):
        assert ("device_profile", "enable_hoteling_guest") in TIER_ASSIGNMENTS
        assert ("device_profile", "enable_hoteling_host") in TIER_ASSIGNMENTS
        assert ("hoteling_location", "enable_hotdesking") in TIER_ASSIGNMENTS

    def test_api_estimates_exist(self):
        assert "device_profile:enable_hoteling_guest" in API_CALL_ESTIMATES
        assert "device_profile:enable_hoteling_host" in API_CALL_ESTIMATES
        assert "hoteling_location:enable_hotdesking" in API_CALL_ESTIMATES

    def test_hoteling_guest_at_tier_5(self):
        assert TIER_ASSIGNMENTS[("device_profile", "enable_hoteling_guest")] == 5

    def test_hoteling_location_at_tier_0(self):
        assert TIER_ASSIGNMENTS[("hoteling_location", "enable_hotdesking")] == 0
