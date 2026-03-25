"""Tests for operation handlers — pure functions mapping canonical data to API requests."""

import pytest
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_location_create,
    handle_location_enable_calling,
    handle_trunk_create,
    handle_route_group_create,
    handle_operating_mode_create,
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
