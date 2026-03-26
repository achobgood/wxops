"""Tests for operation handlers — pure functions mapping canonical data to API requests."""

import pytest
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_call_forwarding_configure,
    handle_monitoring_list_configure,
    handle_line_key_template_create,
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
    handle_hunt_group_create,
    handle_call_queue_create,
    handle_auto_attendant_create,
    handle_call_park_create,
    handle_pickup_group_create,
    handle_paging_group_create,
    handle_user_configure_settings,
    handle_user_configure_voicemail,
    handle_device_configure_settings,
    handle_workspace_configure_settings,
    handle_calling_permission_assign,
    handle_virtual_line_create,
    handle_virtual_line_configure,
    handle_shared_line_configure,
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
        # Create takes plain strings, not {"dialPattern": ...} objects
        assert body["dialPatterns"] == ["+1!"]

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
        assert "+44!" in body["dialPatterns"]

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


class TestHuntGroupCreate:
    def test_with_agents(self):
        data = {
            "name": "Sales HG", "extension": "3001",
            "policy": "CIRCULAR", "location_id": "location:hq",
            "agents": ["user:alice", "user:bob"],
            "no_answer_rings": 5,
        }
        deps = {"location:hq": "wx-loc-123", "user:alice": "wx-alice",
                "user:bob": "wx-bob"}
        result = handle_hunt_group_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/huntGroups" in url
        assert "wx-loc-123" in url  # location in path
        assert body["name"] == "Sales HG"
        assert body["extension"] == "3001"
        assert len(body.get("agents", [])) == 2

    def test_missing_agent_excluded(self):
        data = {"name": "HG", "extension": "3001", "location_id": "location:hq",
                "agents": ["user:alice", "user:bob"]}
        deps = {"location:hq": "wx-loc-123", "user:alice": "wx-alice"}
        # Bob not in deps (failed) — should be excluded, not error
        result = handle_hunt_group_create(data, deps, {})
        _, _, body = result[0]
        assert len(body.get("agents", [])) == 1

    def test_call_policies_no_answer(self):
        data = {
            "name": "HG", "extension": "3001", "location_id": "location:hq",
            "policy": "CIRCULAR", "no_answer_rings": 4,
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_hunt_group_create(data, deps, {})
        _, _, body = result[0]
        assert body["callPolicies"]["policy"] == "CIRCULAR"
        assert body["callPolicies"]["noAnswer"]["numberOfRings"] == 4


class TestCallQueueCreate:
    def test_basic(self):
        data = {
            "name": "Support Queue", "extension": "4001",
            "location_id": "location:hq",
            "policy": "CIRCULAR", "routing_type": "PRIORITY_BASED",
            "agents": ["user:alice"],
        }
        deps = {"location:hq": "wx-loc-123", "user:alice": "wx-alice"}
        result = handle_call_queue_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/queues" in url
        assert body["callPolicies"]["policy"] == "CIRCULAR"

    def test_routing_type_included(self):
        data = {
            "name": "Queue", "extension": "4002", "location_id": "location:hq",
            "routing_type": "SKILL_BASED", "policy": "CIRCULAR",
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_call_queue_create(data, deps, {})
        _, _, body = result[0]
        assert body["callPolicies"]["routingType"] == "SKILL_BASED"


class TestAutoAttendantCreate:
    def test_basic(self):
        data = {
            "name": "Main AA", "extension": "5000",
            "location_id": "location:hq",
            "business_hours_menu": {"greeting": "DEFAULT", "extensionEnabled": True},
            "after_hours_menu": {"greeting": "DEFAULT", "extensionEnabled": True},
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_auto_attendant_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/autoAttendants" in url
        assert body["businessHoursMenu"] is not None
        assert body["afterHoursMenu"] is not None

    def test_no_menu_omitted(self):
        data = {"name": "Bare AA", "extension": "5001", "location_id": "location:hq"}
        deps = {"location:hq": "wx-loc-123"}
        result = handle_auto_attendant_create(data, deps, {})
        _, _, body = result[0]
        assert "businessHoursMenu" not in body
        assert "afterHoursMenu" not in body


class TestCallParkCreate:
    def test_basic(self):
        data = {"name": "Park 1", "extension": "6001", "location_id": "location:hq"}
        deps = {"location:hq": "wx-loc-123"}
        result = handle_call_park_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/callParks" in url
        assert "wx-loc-123" in url
        assert body["name"] == "Park 1"
        assert body["recall"]["option"] == "ALERT_PARKING_USER_ONLY"


class TestPickupGroupCreate:
    def test_basic(self):
        data = {
            "name": "Pickup G1", "location_id": "location:hq",
            "agents": ["user:alice"],
        }
        deps = {"location:hq": "wx-loc-123", "user:alice": "wx-alice"}
        result = handle_pickup_group_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/callPickups" in url
        assert body["name"] == "Pickup G1"
        # Call Pickup takes plain string array, not [{"id": ...}]
        assert body["agents"] == ["wx-alice"]

    def test_no_agents_omitted(self):
        data = {"name": "Empty PG", "location_id": "location:hq", "agents": []}
        deps = {"location:hq": "wx-loc-123"}
        result = handle_pickup_group_create(data, deps, {})
        _, _, body = result[0]
        assert "agents" not in body


class TestPagingGroupCreate:
    def test_with_targets(self):
        data = {
            "name": "Paging 1", "extension": "7001",
            "targets": ["user:alice"],
            "originators": ["user:bob"],
        }
        deps = {
            "location:hq": "wx-loc-123",
            "user:alice": "wx-alice",
            "user:bob": "wx-bob",
        }
        result = handle_paging_group_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/paging" in url
        # Paging Group takes plain string arrays, not [{"id": ...}]
        assert body["targets"] == ["wx-alice"]
        assert body["originators"] == ["wx-bob"]
        assert body["originatorCallerIdEnabled"] is True

    def test_fallback_location_from_deps(self):
        # PagingGroup has no location_id field — location resolved from deps
        data = {"name": "Paging No Loc", "extension": "7002"}
        deps = {"location:hq": "wx-loc-999"}
        result = handle_paging_group_create(data, deps, {})
        _, url, _ = result[0]
        assert "wx-loc-999" in url


class TestUserConfigureSettings:
    def test_returns_multiple_calls(self):
        data = {
            "call_settings": {
                "callForwarding": {"always": {"enabled": False}},
                "callerId": {"externalCallerIdNamePolicy": "DIRECT_LINE"},
            },
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        # Should return one PUT per setting
        assert len(result) >= 1
        for method, url, body in result:
            assert method == "PUT"
            assert "wx-alice" in url

    def test_no_settings_returns_empty(self):
        data = {"call_settings": {}}
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert result == []

    def test_no_user_dep_returns_empty(self):
        data = {"call_settings": {"callForwarding": {"always": {"enabled": False}}}}
        deps = {}
        result = handle_user_configure_settings(data, deps, {})
        assert result == []

    def test_feature_in_url(self):
        data = {"call_settings": {"doNotDisturb": {"enabled": True}}}
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert len(result) == 1
        _, url, _ = result[0]
        assert "doNotDisturb" in url


class TestUserConfigureVoicemail:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_user_configure_voicemail
        data = {"voicemail": {"enabled": True, "sendAllCalls": {"enabled": False}}}
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_voicemail(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/voicemail" in url
        assert "wx-alice" in url

    def test_no_user_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_user_configure_voicemail
        data = {"voicemail": {"enabled": True}}
        result = handle_user_configure_voicemail(data, {}, {})
        assert result == []


class TestDeviceConfigureSettings:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_device_configure_settings
        data = {"device_settings": {"allowThirdPartyControl": True}}
        deps = {"device:d1": "wx-dev-111"}
        result = handle_device_configure_settings(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-dev-111" in url
        assert "/settings" in url

    def test_no_settings_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_device_configure_settings
        data = {"device_settings": {}}
        deps = {"device:d1": "wx-dev-111"}
        result = handle_device_configure_settings(data, deps, {})
        assert result == []

    def test_no_device_dep_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_device_configure_settings
        data = {"device_settings": {"allowThirdPartyControl": True}}
        result = handle_device_configure_settings(data, {}, {})
        assert result == []


class TestWorkspaceConfigureSettings:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_workspace_configure_settings
        data = {"call_settings": {"callForwarding": {"always": {"enabled": False}}}}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_configure_settings(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-ws-aaa" in url
        assert "/features/" in url

    def test_no_settings_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_workspace_configure_settings
        data = {"call_settings": {}}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_configure_settings(data, deps, {})
        assert result == []


class TestCallingPermissionAssign:
    def test_per_user_puts(self):
        data = {
            "calling_permissions": [
                {"call_type": "INTERNATIONAL", "action": "BLOCK"},
            ],
            "assigned_users": ["user:alice", "user:bob"],
            "use_custom_enabled": True,
        }
        deps = {"user:alice": "wx-alice", "user:bob": "wx-bob"}
        result = handle_calling_permission_assign(data, deps, {})
        assert len(result) == 2  # one PUT per user
        for method, url, body in result:
            assert method == "PUT"
            assert "/outgoingPermission" in url

    def test_unresolved_user_excluded(self):
        data = {
            "calling_permissions": [{"call_type": "INTERNATIONAL", "action": "BLOCK"}],
            "assigned_users": ["user:alice", "user:missing"],
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_calling_permission_assign(data, deps, {})
        assert len(result) == 1

    def test_permission_body_structure(self):
        data = {
            "calling_permissions": [
                {"call_type": "NATIONAL", "action": "ALLOW"},
                {"call_type": "INTERNATIONAL", "action": "BLOCK"},
            ],
            "assigned_users": ["user:alice"],
            "use_custom_enabled": True,
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_calling_permission_assign(data, deps, {})
        _, _, body = result[0]
        assert body["useCustomEnabled"] is True
        assert len(body["callingPermissions"]) == 2
        assert body["callingPermissions"][0]["callType"] == "NATIONAL"


class TestSharedLineConfigure:
    def test_stub_returns_put_per_device(self):
        data = {"device_canonical_ids": ["device:d1", "device:d2"]}
        deps = {"device:d1": "wx-dev-111", "device:d2": "wx-dev-222"}
        result = handle_shared_line_configure(data, deps, {})
        assert len(result) == 2
        for method, url, body in result:
            assert method == "PUT"
            assert "/members" in url

    def test_unresolved_device_excluded(self):
        data = {"device_canonical_ids": ["device:d1", "device:missing"]}
        deps = {"device:d1": "wx-dev-111"}
        result = handle_shared_line_configure(data, deps, {})
        assert len(result) == 1

    def test_no_devices_returns_empty(self):
        data = {"device_canonical_ids": []}
        result = handle_shared_line_configure(data, {}, {})
        assert result == []


class TestVirtualLineCreate:
    def test_basic(self):
        data = {
            "display_name": "Reception VL",
            "extension": "8001",
            "location_id": "location:hq",
        }
        deps = {"location:hq": "wx-loc-123"}
        result = handle_virtual_line_create(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert "/virtualLines" in url
        assert body["firstName"] == "Reception VL"
        assert body["lastName"] == "Line"
        assert body["locationId"] == "wx-loc-123"
        assert body["extension"] == "8001"

    def test_default_name(self):
        data = {"extension": "8002", "location_id": "location:hq"}
        deps = {"location:hq": "wx-loc-123"}
        result = handle_virtual_line_create(data, deps, {})
        _, _, body = result[0]
        assert body["firstName"] == "Virtual"


class TestVirtualLineConfigure:
    def test_basic(self):
        data = {"settings": {"callerIdName": "Shared Line"}}
        deps = {"virtual_line:vl1": "wx-vl-aaa"}
        result = handle_virtual_line_configure(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-vl-aaa" in url
        assert "/virtualLines/" in url

    def test_no_settings_returns_empty(self):
        data = {"settings": {}}
        deps = {"virtual_line:vl1": "wx-vl-aaa"}
        result = handle_virtual_line_configure(data, deps, {})
        assert result == []

    def test_no_dep_returns_empty(self):
        data = {"settings": {"callerIdName": "VL"}}
        result = handle_virtual_line_configure(data, {}, {})
        assert result == []


class TestCallForwardingConfigure:
    def test_all_enabled(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": True,
            "always_destination": "+12223334444",
            "always_to_voicemail": False,
            "busy_enabled": True,
            "busy_destination": "+15556667777",
            "busy_to_voicemail": False,
            "no_answer_enabled": True,
            "no_answer_destination": "+18889990000",
            "no_answer_to_voicemail": False,
            "no_answer_ring_count": 5,
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_call_forwarding_configure(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-person-aaa" in url
        assert "/features/callForwarding" in url
        cf = body["callForwarding"]
        assert cf["always"]["enabled"] is True
        assert cf["always"]["destination"] == "+12223334444"
        assert cf["busy"]["enabled"] is True
        assert cf["noAnswer"]["numberOfRings"] == 5
        assert body["businessContinuity"]["enabled"] is False

    def test_all_disabled_returns_empty(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": False,
            "busy_enabled": False,
            "no_answer_enabled": False,
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_call_forwarding_configure(data, deps, {})
        assert result == []

    def test_voicemail_destination(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": True,
            "always_destination": None,
            "always_to_voicemail": True,
            "busy_enabled": False,
            "no_answer_enabled": False,
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_call_forwarding_configure(data, deps, {})
        _, _, body = result[0]
        assert body["callForwarding"]["always"]["destinationVoicemailEnabled"] is True
        assert "destination" not in body["callForwarding"]["always"]

    def test_partial_only_no_answer(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": False,
            "busy_enabled": False,
            "no_answer_enabled": True,
            "no_answer_destination": "+19998887777",
            "no_answer_to_voicemail": False,
            "no_answer_ring_count": 3,
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_call_forwarding_configure(data, deps, {})
        assert len(result) == 1
        _, _, body = result[0]
        cf = body["callForwarding"]
        assert cf["always"]["enabled"] is False
        assert cf["noAnswer"]["enabled"] is True
        assert cf["noAnswer"]["numberOfRings"] == 3

    def test_no_user_dep_returns_empty(self):
        data = {"user_canonical_id": "user:jsmith", "always_enabled": True,
                "always_destination": "+1234", "busy_enabled": False, "no_answer_enabled": False}
        result = handle_call_forwarding_configure(data, {}, {})
        assert result == []


class TestLineKeyTemplateCreate:
    def test_basic(self):
        data = {
            "name": "Standard 8845",
            "device_model": "DMS Cisco 8845",
            "line_keys": [
                {"index": 1, "key_type": "PRIMARY_LINE"},
                {"index": 2, "key_type": "SPEED_DIAL", "label": "Front Desk", "value": "1000"},
            ],
            "kem_keys": [],
        }
        result = handle_line_key_template_create(data, {}, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "/telephony/config/devices/lineKeyTemplates" in url
        assert body["templateName"] == "Standard 8845"
        assert body["deviceModel"] == "DMS Cisco 8845"
        assert len(body["lineKeys"]) == 2
        assert body["lineKeys"][0] == {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"}
        assert body["lineKeys"][1] == {
            "lineKeyIndex": 2, "lineKeyType": "SPEED_DIAL",
            "lineKeyLabel": "Front Desk", "lineKeyValue": "1000",
        }

    def test_unmapped_keys_filtered(self):
        data = {
            "name": "T",
            "device_model": "DMS Cisco 8845",
            "line_keys": [
                {"index": 1, "key_type": "PRIMARY_LINE"},
                {"index": 2, "key_type": "UNMAPPED"},
                {"index": 3, "key_type": "SPEED_DIAL", "label": "X", "value": "2000"},
            ],
            "kem_keys": [],
        }
        result = handle_line_key_template_create(data, {}, {})
        _, _, body = result[0]
        types = [k["lineKeyType"] for k in body["lineKeys"]]
        assert "UNMAPPED" not in types
        assert len(body["lineKeys"]) == 2

    def test_with_kem(self):
        data = {
            "name": "KEM Template",
            "device_model": "DMS Cisco 9861",
            "line_keys": [{"index": 1, "key_type": "PRIMARY_LINE"}],
            "kem_module_type": "KEM_14_KEYS",
            "kem_keys": [
                {"module_index": 1, "index": 1, "key_type": "SPEED_DIAL", "label": "Lab", "value": "3000"},
            ],
        }
        result = handle_line_key_template_create(data, {}, {})
        _, _, body = result[0]
        assert body["kemModuleType"] == "KEM_14_KEYS"
        assert body["kemKeys"][0] == {
            "kemModuleIndex": 1, "kemKeyIndex": 1, "kemKeyType": "SPEED_DIAL",
            "kemKeyLabel": "Lab", "kemKeyValue": "3000",
        }

    def test_orgid_injected(self):
        data = {"name": "T", "device_model": "DMS Cisco 8845", "line_keys": [], "kem_keys": []}
        result = handle_line_key_template_create(data, {}, {"orgId": "ORG123"})
        _, url, _ = result[0]
        assert "orgId=ORG123" in url


class TestMonitoringListConfigure:
    def test_basic(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": True,
            "monitored_members": [
                {"target_canonical_id": "user:alice"},
                {"target_canonical_id": "user:bob"},
            ],
        }
        deps = {
            "user:jsmith": "wx-person-aaa",
            "user:alice": "wx-person-bbb",
            "user:bob": "wx-person-ccc",
        }
        result = handle_monitoring_list_configure(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-person-aaa" in url
        assert "/features/monitoring" in url
        assert body["enableCallParkNotification"] is True
        assert body["monitoredMembers"] == [
            {"id": "wx-person-bbb"},
            {"id": "wx-person-ccc"},
        ]

    def test_empty_members_returns_empty(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": False,
            "monitored_members": [],
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_monitoring_list_configure(data, deps, {})
        assert result == []

    def test_partial_resolution(self):
        """Members that fail to resolve are silently omitted."""
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": False,
            "monitored_members": [
                {"target_canonical_id": "user:alice"},
                {"target_canonical_id": "user:missing"},
                {"target_canonical_id": None},
            ],
        }
        deps = {"user:jsmith": "wx-person-aaa", "user:alice": "wx-person-bbb"}
        result = handle_monitoring_list_configure(data, deps, {})
        assert len(result) == 1
        _, _, body = result[0]
        assert len(body["monitoredMembers"]) == 1
        assert body["monitoredMembers"][0] == {"id": "wx-person-bbb"}

    def test_no_user_dep_returns_empty(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": False,
            "monitored_members": [{"target_canonical_id": "user:alice"}],
        }
        result = handle_monitoring_list_configure(data, {}, {})
        assert result == []

    def test_orgid_injected(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": False,
            "monitored_members": [{"target_canonical_id": "user:alice"}],
        }
        deps = {"user:jsmith": "wx-person-aaa", "user:alice": "wx-person-bbb"}
        result = handle_monitoring_list_configure(data, deps, {"orgId": "ORG123"})
        _, url, _ = result[0]
        assert "orgId=ORG123" in url


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
