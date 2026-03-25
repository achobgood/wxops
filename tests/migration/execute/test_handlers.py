"""Tests for operation handlers — pure functions mapping canonical data to API requests."""

import pytest
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_location_create,
    handle_location_enable_calling,
    handle_trunk_create,
    handle_route_group_create,
    handle_operating_mode_create,
    handle_user_create,
    handle_workspace_create,
    handle_workspace_assign_number,
    handle_device_create,
    handle_dial_plan_create,
    handle_translation_pattern_create,
)

BASE = "https://webexapis.com/v1"


class TestLocationCreate:
    def test_basic(self):
        data = {
            "name": "HQ Office",
            "time_zone": "America/New_York",
            "preferred_language": "en_US",
            "announcement_language": "en_us",
            "address": {
                "address1": "123 Main St",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "country": "US",
            },
        }
        result = handle_location_create(data, {}, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert url == f"{BASE}/locations"
        assert body["name"] == "HQ Office"
        assert body["timeZone"] == "America/New_York"
        assert body["address"]["address1"] == "123 Main St"
        assert body["address"]["postalCode"] == "10001"

    def test_with_org_id(self):
        data = {"name": "HQ", "time_zone": "America/New_York",
                "preferred_language": "en_US", "announcement_language": "en_us",
                "address": {"address1": "123 Main", "city": "NY", "state": "NY",
                            "postal_code": "10001", "country": "US"}}
        result = handle_location_create(data, {}, {"orgId": "org-123"})
        _, url, _ = result[0]
        assert "orgId=org-123" in url or url.endswith("org-123")  # query param


class TestLocationEnableCalling:
    def test_basic(self):
        data = {
            "name": "HQ Office",
            "time_zone": "America/New_York",
            "preferred_language": "en_US",
            "announcement_language": "en_us",
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_location_enable_calling(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert url == f"{BASE}/telephony/config/locations"
        assert body["id"] == "wx-loc-123"
        assert body["announcementLanguage"] == "en_us"


class TestTrunkCreate:
    def test_registering(self):
        data = {
            "name": "SBC Trunk",
            "location_id": "location:hq",
            "trunk_type": "REGISTERING",
            "password": "SecurePass123!",
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_trunk_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert url == f"{BASE}/telephony/config/premisePstn/trunks"
        assert body["name"] == "SBC Trunk"
        assert body["locationId"] == "wx-loc-123"
        assert body["trunkType"] == "REGISTERING"
        assert body["password"] == "SecurePass123!"


class TestRouteGroupCreate:
    def test_with_trunks(self):
        data = {
            "name": "Primary RG",
            "local_gateways": [
                {"trunk_canonical_id": "trunk:sbc1", "priority": 1},
            ],
        }
        deps = {"trunk:sbc1": "wx-trunk-aaa"}
        result = handle_route_group_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert url == f"{BASE}/telephony/config/premisePstn/routeGroups"
        assert body["name"] == "Primary RG"
        assert body["localGateways"][0]["trunkId"] == "wx-trunk-aaa"
        assert body["localGateways"][0]["priority"] == 1


class TestOperatingModeCreate:
    def test_basic(self):
        data = {"name": "Business Hours", "level": "ORGANIZATION",
                "schedule_type": "SAME_HOURS_DAILY"}
        result = handle_operating_mode_create(data, {}, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/operatingModes" in url or "/schedules" in url


class TestScheduleCreate:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_schedule_create
        data = {
            "name": "Business Hours",
            "schedule_type": "businessHours",
            "location_id": "location:hq",
            "events": [{"name": "Monday", "startDay": "MONDAY"}],
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_schedule_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "wx-loc-123" in url
        assert "/schedules" in url
        assert body["name"] == "Business Hours"
        assert body["type"] == "businessHours"


class TestUserCreate:
    def test_basic(self):
        data = {
            "emails": ["alice@acme.com"],
            "first_name": "Alice",
            "last_name": "Smith",
            "display_name": "Alice Smith",
            "location_id": "location:hq",
            "extension": "1001",
        }
        deps = {"location:hq": "wx-loc-123"}
        ctx = {"CALLING_LICENSE_ID": "wx-lic-pro"}
        result = handle_user_create(data, deps, ctx)
        method, url, body = result[0]
        assert method == "POST"
        assert "callingData=true" in url or body.get("callingData")
        assert body["emails"] == ["alice@acme.com"]
        assert body["firstName"] == "Alice"
        assert body["locationId"] == "wx-loc-123"
        assert body["extension"] == "1001"
        assert "wx-lic-pro" in body.get("licenses", [])

    def test_with_phone_numbers(self):
        data = {
            "emails": ["bob@acme.com"], "first_name": "Bob", "last_name": "Jones",
            "location_id": "location:hq", "extension": "1002",
            "phone_numbers": [{"type": "work", "value": "+15551234567"}],
        }
        deps = {"location:hq": "wx-loc-123"}
        ctx = {"CALLING_LICENSE_ID": "wx-lic-pro"}
        result = handle_user_create(data, deps, ctx)
        _, _, body = result[0]
        assert body["phoneNumbers"][0]["value"] == "+15551234567"


class TestWorkspaceCreate:
    def test_basic(self):
        data = {
            "display_name": "Lobby Phone",
            "location_id": "location:hq",
            "supported_devices": "phones",
            "extension": "5001",
            "calling_type": "webexCalling",
            "workspace_type": "other",
            "hotdesking_status": "off",
        }
        deps = {"location:hq": "wx-loc-123"}
        ctx = {"WORKSPACE_LICENSE_ID": "wx-lic-ws"}
        result = handle_workspace_create(data, deps, ctx)
        method, url, body = result[0]
        assert method == "POST"
        assert url.startswith(f"{BASE}/workspaces")
        assert body["displayName"] == "Lobby Phone"
        assert body["calling"]["type"] == "webexCalling"
        assert body["calling"]["webexCalling"]["locationId"] == "wx-loc-123"

    def test_hotdesking_status_included(self):
        data = {
            "display_name": "Hot Desk",
            "location_id": "location:hq",
            "calling_type": "webexCalling",
            "hotdesking_status": "on",
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_workspace_create(data, deps, {})
        _, _, body = result[0]
        assert body["hotdeskingStatus"] == "on"


class TestWorkspaceAssignNumber:
    def test_with_did(self):
        data = {"phone_number": "+15559998888"}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_assign_number(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-ws-aaa" in url
        assert body["phoneNumbers"][0]["value"] == "+15559998888"

    def test_no_phone_number_returns_empty(self):
        data = {}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_assign_number(data, deps, {})
        assert result == []

    def test_no_workspace_dep_returns_empty(self):
        data = {"phone_number": "+15559998888"}
        deps = {}
        result = handle_workspace_assign_number(data, deps, {})
        assert result == []


class TestDeviceCreate:
    def test_by_mac(self):
        data = {
            "mac": "AABBCCDDEE01",
            "model": "Cisco 8845",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert url.startswith(f"{BASE}/devices")
        assert body["mac"] == "AABBCCDDEE01"
        assert body["personId"] == "wx-person-alice"

    def test_workspace_owner(self):
        data = {
            "mac": "AABBCCDDEE02",
            "model": "Cisco 8845",
            "owner_canonical_id": "workspace:lobby",
        }
        deps = {"workspace:lobby": "wx-ws-bbb"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["workspaceId"] == "wx-ws-bbb"
        assert "personId" not in body

    def test_unresolved_owner_excluded(self):
        data = {"mac": "AABBCCDDEE03", "owner_canonical_id": "user:missing"}
        deps = {}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert "personId" not in body
        assert "workspaceId" not in body


class TestDialPlanCreate:
    def test_basic(self):
        data = {
            "name": "US Dial Plan",
            "dial_patterns": ["+1!"],
            "route_id": "trunk:sbc1",
            "route_type": "TRUNK",
        }
        deps = {"trunk:sbc1": "wx-trunk-aaa"}
        result = handle_dial_plan_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/premisePstn/dialPlans" in url
        assert body["name"] == "US Dial Plan"
        assert body["routeId"] == "wx-trunk-aaa"
        assert body["routeType"] == "TRUNK"
        assert body["dialPatterns"] == [{"dialPattern": "+1!"}]

    def test_multiple_patterns(self):
        data = {
            "name": "Multi Pattern",
            "dial_patterns": ["+1!", "+44!"],
            "route_id": "trunk:sbc1",
            "route_type": "TRUNK",
        }
        deps = {"trunk:sbc1": "wx-trunk-aaa"}
        result = handle_dial_plan_create(data, deps, {})
        _, _, body = result[0]
        assert len(body["dialPatterns"]) == 2
        assert {"dialPattern": "+44!"} in body["dialPatterns"]

    def test_unresolved_route(self):
        data = {"name": "No Route", "dial_patterns": ["+1!"], "route_id": "trunk:missing"}
        result = handle_dial_plan_create(data, {}, {})
        _, _, body = result[0]
        assert body["routeId"] is None


class TestTranslationPatternCreate:
    def test_basic(self):
        data = {
            "name": "Strip 9",
            "matching_pattern": "9.!",
            "replacement_pattern": "+1!",
        }
        result = handle_translation_pattern_create(data, {}, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/translationPatterns" in url
        assert body["matchingPattern"] == "9.!"
        assert body["replacementPattern"] == "+1!"

    def test_name_included(self):
        data = {"name": "My Pattern", "matching_pattern": "9!", "replacement_pattern": "1!"}
        result = handle_translation_pattern_create(data, {}, {})
        _, _, body = result[0]
        assert body["name"] == "My Pattern"


class TestHandlerRegistry:
    def test_all_operation_types_have_handlers(self):
        """Every (resource_type, op_type) in TIER_ASSIGNMENTS must have a handler."""
        from wxcli.migration.execute import TIER_ASSIGNMENTS
        missing = []
        for (rt, op) in TIER_ASSIGNMENTS:
            if (rt, op) not in HANDLER_REGISTRY:
                # calling_permission:create has 0 API calls — no handler needed
                from wxcli.migration.execute import API_CALL_ESTIMATES
                if API_CALL_ESTIMATES.get(f"{rt}:{op}", 1) == 0:
                    continue
                missing.append(f"{rt}:{op}")
        assert missing == [], f"Missing handlers: {missing}"
