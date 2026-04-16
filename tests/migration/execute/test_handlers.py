"""Tests for operation handlers — pure functions mapping canonical data to API requests."""

import pytest
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_call_forwarding_configure,
    handle_monitoring_list_configure,
    handle_device_layout_configure,
    handle_softkey_config_configure,
    handle_line_key_template_create,
    handle_location_create,
    handle_location_enable_calling,
    handle_trunk_create,
    handle_route_group_create,
    handle_route_list_create,
    handle_route_list_configure_numbers,
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
    handle_snr_configure,
    handle_device_create_activation_code,
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
            "canonical_id": "location:hq",
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
        assert body["localGateways"][0]["id"] == "wx-trunk-aaa"
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
        data = {"canonical_id": "workspace:lobby", "phone_number": "+15559998888"}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_assign_number(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-ws-aaa" in url
        assert body["phoneNumbers"][0]["value"] == "+15559998888"

    def test_no_phone_number_returns_empty(self):
        data = {"canonical_id": "workspace:lobby"}
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_assign_number(data, deps, {})
        assert result == []

    def test_no_workspace_dep_returns_skipped(self):
        """Wave 2A: missing workspace webex_id is a hard prerequisite miss
        — handler returns SkippedResult so the engine records it as
        status='skipped' rather than silently completing."""
        from wxcli.migration.execute.handlers import SkippedResult

        data = {"display_name": "Lobby", "phone_number": "+15559998888"}
        deps = {}
        result = handle_workspace_assign_number(data, deps, {})
        assert isinstance(result, SkippedResult)


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

    def test_phoneos_model_strips_dms_prefix(self):
        """PhoneOS 9841 arriving as 'Cisco 9841' → 'Cisco 9841' (no DMS prefix)."""
        data = {
            "mac": "AABBCCDDEE04",
            "model": "Cisco 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_model_verbose_form_normalizes_without_dms(self):
        """'Cisco IP Phone 9841' → 'Cisco 9841' (strips IP Phone, no DMS prefix)."""
        data = {
            "mac": "AABBCCDDEE05",
            "model": "Cisco IP Phone 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_model_strips_preexisting_dms_prefix(self):
        """'DMS Cisco 9841' (should never be emitted but be defensive) → 'Cisco 9841'."""
        data = {
            "mac": "AABBCCDDEE06",
            "model": "DMS Cisco 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_8875_strips_dms_prefix(self):
        """8875 is PhoneOS-class; strip DMS prefix."""
        data = {
            "mac": "AABBCCDDEE07",
            "model": "Cisco 8875",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 8875"

    def test_classic_mpp_model_still_gets_dms_prefix(self):
        """'Cisco 8851' (classic MPP) → 'DMS Cisco 8851' (with DMS prefix)."""
        data = {
            "mac": "AABBCCDDEE08",
            "model": "Cisco 8851",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "DMS Cisco 8851"

    def test_classic_mpp_verbose_form_collapses_and_gets_dms_prefix(self):
        """'Cisco IP Phone 8851' → 'DMS Cisco 8851'."""
        data = {
            "mac": "AABBCCDDEE09",
            "model": "Cisco IP Phone 8851",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "DMS Cisco 8851"

    def test_phoneos_9841_end_to_end_integration(self):
        """End-to-end: planner-shaped canonical 9841 → handle_device_create → POST body.

        Proves the full data flow: a realistic PhoneOS 9841 canonical payload with
        `device_id_surface='cloud'` produces a `POST /v1/devices` with the exact
        model string `"Cisco 9841"` (no `DMS ` prefix), the expected MAC, the
        resolved Webex personId, and the orgId injected as a query param.
        """
        data = {
            "mac": "AABBCC000001",
            "model": "Cisco 9841",
            "owner_canonical_id": "user:test.user",
            "device_id_surface": "cloud",
        }
        deps = {"user:test.user": "wx-person-testuser-id"}
        ctx = {"orgId": "org-integration-test"}

        result = handle_device_create(data, deps, ctx)

        # Exactly one API call emitted.
        assert isinstance(result, list)
        assert len(result) == 1

        method, url, body = result[0]

        # Method + URL shape.
        assert method == "POST"
        assert "/v1/devices" in url
        assert "orgId=org-integration-test" in url

        # Body: exact model string (no DMS prefix), MAC preserved, personId resolved.
        assert body["model"] == "Cisco 9841"
        assert body["mac"] == "AABBCC000001"
        assert body["personId"] == "wx-person-testuser-id"
        assert "workspaceId" not in body

    @pytest.mark.parametrize(
        "model",
        [
            "Cisco 9811",
            "Cisco 9821",
            "Cisco 9841",
            "Cisco 9851",
            "Cisco 9861",
            "Cisco 9871",
            "Cisco 8875",
        ],
    )
    def test_phoneos_models_end_to_end_no_dms_prefix(self, model):
        """All 7 PhoneOS models (9811/9821/9841/9851/9861/9871/8875) must keep
        the exact `Cisco <model>` string with NO `DMS ` prefix when routed
        through handle_device_create."""
        data = {
            "mac": "AABBCC000099",
            "model": model,
            "owner_canonical_id": "user:test.user",
            "device_id_surface": "cloud",
        }
        deps = {"user:test.user": "wx-person-testuser-id"}
        ctx = {"orgId": "org-integration-test"}

        result = handle_device_create(data, deps, ctx)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "/v1/devices" in url
        assert "orgId=org-integration-test" in url
        assert body["model"] == model
        assert not body["model"].startswith("DMS ")
        assert body["mac"] == "AABBCC000099"
        assert body["personId"] == "wx-person-testuser-id"


class TestNormalizeDeviceModel:
    """Unit tests for the _normalize_device_model helper."""

    def test_normalize_empty_model_returns_empty(self):
        """Empty input must short-circuit — not fall through to the
        classic-MPP branch and produce the invalid string 'DMS '."""
        from wxcli.migration.execute.handlers import _normalize_device_model

        assert _normalize_device_model("") == ""


class TestDeviceCreateActivationCode:
    def test_person_owner_with_dms_prefix(self):
        data = {
            "model": "DMS Cisco 8851",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create_activation_code(data, deps, {})
        method, url, body = result[0]
        assert method == "POST"
        assert url.startswith(f"{BASE}/devices/activationCode")
        assert body["model"] == "DMS Cisco 8851"
        assert body["personId"] == "wx-person-alice"
        assert "workspaceId" not in body
        assert "mac" not in body

    def test_model_prefix_added_when_missing(self):
        data = {
            "model": "Cisco 8865",
            "owner_canonical_id": "user:bob",
        }
        deps = {"user:bob": "wx-person-bob"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "DMS Cisco 8865"

    def test_workspace_owner(self):
        data = {
            "model": "DMS Cisco 7841",
            "owner_canonical_id": "workspace:lobby",
        }
        deps = {"workspace:lobby": "wx-ws-lobby"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["workspaceId"] == "wx-ws-lobby"
        assert "personId" not in body

    def test_unresolved_owner_omitted(self):
        data = {
            "model": "DMS Cisco 8851",
            "owner_canonical_id": "user:ghost",
        }
        deps = {}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "DMS Cisco 8851"

    def test_no_model_no_body_model_field(self):
        data = {"owner_canonical_id": "user:alice"}
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert "model" not in body
        assert body["personId"] == "wx-person-alice"

    def test_org_id_injected_into_url(self):
        data = {"model": "DMS Cisco 8851", "owner_canonical_id": "user:alice"}
        deps = {"user:alice": "wx-person-alice"}
        ctx = {"orgId": "org-xyz"}
        result = handle_device_create_activation_code(data, deps, ctx)
        _, url, _ = result[0]
        assert "orgId=org-xyz" in url

    def test_model_ip_phone_verbose_form_is_normalized(self):
        """`Cisco IP Phone 8845` → `DMS Cisco 8845` (strips 'IP Phone')."""
        data = {
            "canonical_id": "device:verbose",
            "model": "Cisco IP Phone 8845",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-alice"}
        ctx = {"orgId": "org-1"}
        result = handle_device_create_activation_code(data, deps, ctx)
        assert len(result) == 1
        method, url, body = result[0]
        assert body["model"] == "DMS Cisco 8845"

    def test_phoneos_model_strips_dms_prefix(self):
        """PhoneOS 9841 arriving as 'Cisco 9841' stays non-DMS in activation body."""
        data = {
            "model": "Cisco 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_model_verbose_form_normalizes_without_dms(self):
        """'Cisco IP Phone 9841' → 'Cisco 9841' in activation body (no DMS prefix)."""
        data = {
            "model": "Cisco IP Phone 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_model_strips_preexisting_dms_prefix(self):
        """Defensive: if 'DMS Cisco 9841' slips in, strip the prefix for activation body."""
        data = {
            "model": "DMS Cisco 9841",
            "owner_canonical_id": "user:alice",
        }
        deps = {"user:alice": "wx-person-alice"}
        result = handle_device_create_activation_code(data, deps, {})
        _, _, body = result[0]
        assert body["model"] == "Cisco 9841"

    def test_phoneos_9841_end_to_end_integration(self):
        """End-to-end: PhoneOS 9841 canonical payload → activation code POST.

        Same normalization (no `DMS ` prefix) must apply on the activation-code
        path — Webex rejects `DMS Cisco 9841` with "Device model is not
        supported." on both `/devices` and `/devices/activationCode`.
        """
        data = {
            "model": "Cisco 9841",
            "owner_canonical_id": "user:test.user",
            "device_id_surface": "cloud",
        }
        deps = {"user:test.user": "wx-person-testuser-id"}
        ctx = {"orgId": "org-integration-test"}

        result = handle_device_create_activation_code(data, deps, ctx)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "/v1/devices/activationCode" in url
        assert "orgId=org-integration-test" in url
        assert body["model"] == "Cisco 9841"
        assert not body["model"].startswith("DMS ")
        assert body["personId"] == "wx-person-testuser-id"
        assert "workspaceId" not in body
        assert "mac" not in body


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
            "canonical_id": "user:alice",
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
        data = {"canonical_id": "user:alice", "call_settings": {}}
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert result == []

    def test_no_user_dep_returns_skipped(self):
        """Wave 2A: missing user webex_id is a hard prerequisite miss."""
        from wxcli.migration.execute.handlers import SkippedResult

        data = {
            "canonical_id": "user:alice",
            "call_settings": {"callForwarding": {"always": {"enabled": False}}},
        }
        deps = {}
        result = handle_user_configure_settings(data, deps, {})
        assert isinstance(result, SkippedResult)

    def test_feature_in_url(self):
        data = {
            "canonical_id": "user:alice",
            "call_settings": {"doNotDisturb": {"enabled": True}},
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert len(result) == 1
        _, url, _ = result[0]
        assert "doNotDisturb" in url

    def test_call_recording_emits_get_then_put(self):
        """callRecording uses read-before-write: GET current, then PUT with merge sentinel."""
        data = {
            "canonical_id": "user:alice",
            "call_settings": {
                "callRecording": {"enabled": True, "record": "Always"},
            },
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert len(result) == 2
        # First call is GET to read current state
        method0, url0, body0 = result[0]
        assert method0 == "GET"
        assert "/people/wx-alice/features/callRecording" in url0
        assert body0 is None
        # Second call is PUT with merge sentinel
        method1, url1, body1 = result[1]
        assert method1 == "PUT"
        assert "/people/wx-alice/features/callRecording" in url1
        assert body1["_merge_from_previous"] is True
        assert body1["enabled"] is True
        assert body1["record"] == "Always"

    def test_call_recording_mixed_with_other_features(self):
        """callRecording GET+PUT coexists with other features' plain PUTs."""
        data = {
            "canonical_id": "user:alice",
            "call_settings": {
                "doNotDisturb": {"enabled": True},
                "callRecording": {"enabled": True, "record": "Always"},
                "callerId": {"externalCallerIdNamePolicy": "DIRECT_LINE"},
            },
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        # doNotDisturb: 1 PUT, callRecording: 1 GET + 1 PUT, callerId: 1 PUT = 4 total
        assert len(result) == 4
        methods = [m for m, _, _ in result]
        assert methods.count("GET") == 1
        assert methods.count("PUT") == 3

    def test_non_recording_features_single_put(self):
        """Non-callRecording features still produce a single PUT each."""
        data = {
            "canonical_id": "user:alice",
            "call_settings": {
                "callForwarding": {"always": {"enabled": False}},
                "callerId": {"externalCallerIdNamePolicy": "DIRECT_LINE"},
            },
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert len(result) == 2
        for method, url, body in result:
            assert method == "PUT"
            assert "_merge_from_previous" not in (body or {})

    def test_picks_correct_user_among_multiple_deps(self):
        """Regression: with multiple user:* entries in deps, the handler must
        resolve by data['canonical_id'] (this op's target), not by scan-first.
        Before the fix, the loop picked the first user:* in dict-iteration
        order and silently PUT bob's settings on alice — especially dangerous
        now that callRecording does GET + merge + PUT."""
        data = {
            "canonical_id": "user:bob",
            "call_settings": {"doNotDisturb": {"enabled": True}},
        }
        # alice is inserted first on purpose — on CPython's insertion-ordered
        # dicts this guarantees the old scan-first code path would have
        # picked wx-alice. The canonical_id-based resolution picks wx-bob.
        deps = {"user:alice": "wx-alice", "user:bob": "wx-bob"}
        result = handle_user_configure_settings(data, deps, {})
        assert len(result) == 1
        _, url, _ = result[0]
        assert "wx-bob" in url
        assert "wx-alice" not in url


class TestUserConfigureVoicemail:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_user_configure_voicemail
        data = {
            "canonical_id": "user:alice",
            "voicemail": {"enabled": True, "sendAllCalls": {"enabled": False}},
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_voicemail(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/voicemail" in url
        assert "wx-alice" in url

    def test_no_user_returns_skipped(self):
        """Wave 2A: missing user webex_id is a hard prerequisite miss."""
        from wxcli.migration.execute.handlers import (
            SkippedResult,
            handle_user_configure_voicemail,
        )
        data = {"canonical_id": "user:alice", "voicemail": {"enabled": True}}
        result = handle_user_configure_voicemail(data, {}, {})
        assert isinstance(result, SkippedResult)

    def test_picks_correct_user_among_multiple_deps(self):
        """Same regression as TestUserConfigureSettings — multiple user:*
        deps must route to the canonical_id target, not scan-first."""
        from wxcli.migration.execute.handlers import handle_user_configure_voicemail

        data = {"canonical_id": "user:bob", "voicemail": {"enabled": True}}
        deps = {"user:alice": "wx-alice", "user:bob": "wx-bob"}
        result = handle_user_configure_voicemail(data, deps, {})
        assert len(result) == 1
        _, url, _ = result[0]
        assert "wx-bob" in url
        assert "wx-alice" not in url


class TestDeviceConfigureSettings:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_device_configure_settings
        data = {
            "canonical_id": "device:d1",
            "device_settings": {"allowThirdPartyControl": True},
        }
        deps = {"device:d1": "wx-dev-111"}
        result = handle_device_configure_settings(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-dev-111" in url
        assert "/settings" in url

    def test_no_settings_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_device_configure_settings
        data = {"canonical_id": "device:d1", "device_settings": {}}
        deps = {"device:d1": "wx-dev-111"}
        result = handle_device_configure_settings(data, deps, {})
        assert result == []

    def test_no_device_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import (
            SkippedResult,
            handle_device_configure_settings,
        )
        data = {
            "canonical_id": "device:d1",
            "device_settings": {"allowThirdPartyControl": True},
        }
        result = handle_device_configure_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device" in result.reason


class TestWorkspaceConfigureSettings:
    def test_basic(self):
        from wxcli.migration.execute.handlers import handle_workspace_configure_settings
        data = {
            "canonical_id": "workspace:lobby",
            "call_settings": {"callForwarding": {"always": {"enabled": False}}},
        }
        deps = {"workspace:lobby": "wx-ws-aaa"}
        result = handle_workspace_configure_settings(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-ws-aaa" in url
        assert "/telephony/config/workspaces/" in url

    def test_no_settings_returns_empty(self):
        from wxcli.migration.execute.handlers import handle_workspace_configure_settings
        data = {"canonical_id": "workspace:lobby", "call_settings": {}}
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
    def test_two_owners_produces_two_puts(self):
        """Each owner gets a PUT with the other owner as a shared line member."""
        data = {
            "owner_canonical_ids": ["user:alice", "user:bob"],
            "device_canonical_ids": ["device:d1", "device:d2"],
        }
        deps = {"user:alice": "wx-alice", "user:bob": "wx-bob",
                "device:d1": "wx-dev-1", "device:d2": "wx-dev-2"}
        result = handle_shared_line_configure(data, deps, {})
        assert len(result) == 2
        # First PUT: alice's app gets bob as member
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-alice" in url
        assert "/applications/members" in url
        assert len(body["members"]) == 1
        assert body["members"][0]["memberId"] == "wx-bob"
        assert body["members"][0]["lineType"] == "SHARED_CALL_APPEARANCE"
        # Second PUT: bob's app gets alice as member
        method2, url2, body2 = result[1]
        assert "wx-bob" in url2
        assert body2["members"][0]["memberId"] == "wx-alice"

    def test_three_owners_each_gets_two_members(self):
        """With 3 owners, each gets the other 2 as shared line members."""
        data = {
            "owner_canonical_ids": ["user:a", "user:b", "user:c"],
            "device_canonical_ids": [],
        }
        deps = {"user:a": "wx-a", "user:b": "wx-b", "user:c": "wx-c"}
        result = handle_shared_line_configure(data, deps, {})
        assert len(result) == 3
        for _, _, body in result:
            assert len(body["members"]) == 2

    def test_unresolved_owner_excluded(self):
        """If one of 3 owners is unresolved, the remaining 2 still configure."""
        data = {
            "owner_canonical_ids": ["user:a", "user:missing", "user:c"],
            "device_canonical_ids": [],
        }
        deps = {"user:a": "wx-a", "user:c": "wx-c"}
        result = handle_shared_line_configure(data, deps, {})
        assert len(result) == 2

    def test_single_owner_returns_skipped(self):
        """A shared line with only 1 resolved owner is missing-dep — skip."""
        from wxcli.migration.execute.handlers import SkippedResult
        data = {
            "owner_canonical_ids": ["user:alice"],
            "device_canonical_ids": [],
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_shared_line_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "2+" in result.reason or "requires" in result.reason
        assert "1" in result.reason

    def test_no_resolved_owners_returns_skipped(self):
        """If no owners resolve, return skipped (per issue #17)."""
        from wxcli.migration.execute.handlers import SkippedResult
        data = {
            "owner_canonical_ids": ["user:gone1", "user:gone2"],
            "device_canonical_ids": [],
        }
        deps = {}
        result = handle_shared_line_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "0 of 2" in result.reason

    def test_primary_owner_flag(self):
        """First owner in the list is marked as primaryOwner on other owners' member lists."""
        data = {
            "owner_canonical_ids": ["user:primary", "user:secondary"],
            "device_canonical_ids": [],
        }
        deps = {"user:primary": "wx-primary", "user:secondary": "wx-secondary"}
        result = handle_shared_line_configure(data, deps, {})
        # On secondary's member list, primary should have primaryOwner=True
        _, _, body_secondary = result[1]
        assert body_secondary["members"][0]["primaryOwner"] is True
        # On primary's member list, secondary should have primaryOwner=False
        _, _, body_primary = result[0]
        assert body_primary["members"][0]["primaryOwner"] is False


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
        data = {
            "canonical_id": "virtual_line:vl1",
            "settings": {"callerIdName": "Shared Line"},
        }
        deps = {"virtual_line:vl1": "wx-vl-aaa"}
        result = handle_virtual_line_configure(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-vl-aaa" in url
        assert "/virtualLines/" in url

    def test_no_settings_returns_empty(self):
        data = {"canonical_id": "virtual_line:vl1", "settings": {}}
        deps = {"virtual_line:vl1": "wx-vl-aaa"}
        result = handle_virtual_line_configure(data, deps, {})
        assert result == []

    def test_no_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = {"canonical_id": "virtual_line:vl1", "settings": {"callerIdName": "VL"}}
        result = handle_virtual_line_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "virtual" in result.reason.lower()


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

    def test_no_user_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = {"user_canonical_id": "user:jsmith", "always_enabled": True,
                "always_destination": "+1234", "busy_enabled": False, "no_answer_enabled": False}
        result = handle_call_forwarding_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jsmith" in result.reason


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

    def test_9861_15_keys_all_fit_in_line_keys(self):
        """9861 has 16 physical line keys. A template with 15 line keys must keep
        all 15 as lineKeys — none should be split to kemKeys. Regression test for
        the _PHONEOS_LINE_KEY_MAX drift where 9861 was incorrectly set to 10."""
        data = {
            "name": "9861 15-key template",
            "device_model": "DMS Cisco 9861",
            "line_keys": [
                {"index": i, "key_type": "SPEED_DIAL", "label": f"SD{i}", "value": f"100{i}"}
                for i in range(1, 16)  # indices 1..15
            ],
            "kem_keys": [],
        }
        result = handle_line_key_template_create(data, {}, {})
        assert len(result) == 1
        _, _, body = result[0]
        # PhoneOS model name rewrite
        assert body["deviceModel"] == "Cisco 9861"
        # All 15 line keys must land in lineKeys, none in kemKeys
        assert len(body["lineKeys"]) == 15
        indices = [k["lineKeyIndex"] for k in body["lineKeys"]]
        assert indices == list(range(1, 16))
        # No kemKeys should be present (none in input, none split from overflow)
        assert "kemKeys" not in body


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

    def test_no_user_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = {
            "user_canonical_id": "user:jsmith",
            "call_park_notification_enabled": False,
            "monitored_members": [{"target_canonical_id": "user:alice"}],
        }
        result = handle_monitoring_list_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jsmith" in result.reason

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


class TestDeviceLayoutConfigure:
    def _base_data(self):
        return {
            "device_canonical_id": "device:SEPAA112233",
            "device_id_surface": "cloud",
            "template_canonical_id": None,
            "owner_canonical_id": "user:jsmith",
            "line_members": [
                {"port": 1, "member_canonical_id": "user:jsmith", "line_type": "PRIMARY"},
                {"port": 2, "member_canonical_id": "user:jdoe", "line_type": "SHARED_LINE"},
            ],
            "resolved_line_keys": [
                {"index": 1, "key_type": "PRIMARY_LINE"},
                {"index": 2, "key_type": "SHARED_LINE", "label": "Shared"},
            ],
            "resolved_kem_keys": [],
        }

    def test_three_calls_members_layout_apply(self):
        data = self._base_data()
        deps = {
            "device:SEPAA112233": "wx-dev-bbb",
            "user:jsmith": "wx-person-aaa",
            "user:jdoe": "wx-person-ccc",
        }
        result = handle_device_layout_configure(data, deps, {})
        assert len(result) == 3
        method1, url1, body1 = result[0]
        assert method1 == "PUT"
        assert "wx-dev-bbb" in url1
        assert "/members" in url1
        assert {"id": "wx-person-aaa", "port": 1} in body1["members"]
        assert {"id": "wx-person-ccc", "port": 2} in body1["members"]
        method2, url2, body2 = result[1]
        assert method2 == "PUT"
        assert "/layout" in url2
        assert body2["layoutMode"] == "CUSTOM"
        keys = {k["lineKeyIndex"]: k for k in body2["lineKeys"]}
        # PRIMARY_LINE is filtered (Webex auto-assigns at index 1)
        # SHARED_LINE re-indexed to start at 2
        assert 1 not in keys, "PRIMARY_LINE should be filtered out"
        assert keys[2]["lineKeyType"] == "SHARED_LINE"
        assert keys[2]["lineKeyLabel"] == "Shared"
        method3, url3, body3 = result[2]
        assert method3 == "POST"
        assert "applyChanges" in url3
        assert body3 is None

    def test_no_members_two_calls(self):
        """No line_members → skip PUT members; still do layout + applyChanges."""
        data = self._base_data()
        data["line_members"] = []
        deps = {"device:SEPAA112233": "wx-dev-bbb"}
        result = handle_device_layout_configure(data, deps, {})
        assert len(result) == 2
        assert "/layout" in result[0][1]
        assert "applyChanges" in result[1][1]

    def test_no_device_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = self._base_data()
        result = handle_device_layout_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device" in result.reason.lower()

    def test_partial_member_resolution(self):
        data = self._base_data()
        deps = {
            "device:SEPAA112233": "wx-dev-bbb",
            "user:jsmith": "wx-person-aaa",
        }
        result = handle_device_layout_configure(data, deps, {})
        assert len(result) == 3
        _, _, body1 = result[0]
        assert len(body1["members"]) == 1
        assert body1["members"][0]["id"] == "wx-person-aaa"

    def test_default_layout_mode_no_keys(self):
        data = self._base_data()
        data["resolved_line_keys"] = []
        data["template_canonical_id"] = "line_key_template:tmpl1"
        data["line_members"] = []
        deps = {"device:SEPAA112233": "wx-dev-bbb"}
        result = handle_device_layout_configure(data, deps, {})
        _, _, body = result[0]  # first call is PUT layout (no members)
        assert body["layoutMode"] == "DEFAULT"
        assert "lineKeys" not in body

    def test_kem_keys_included_in_layout(self):
        data = self._base_data()
        data["line_members"] = []
        data["kem_supported"] = True
        data["resolved_kem_keys"] = [
            {"module_index": 1, "index": 1, "key_type": "SPEED_DIAL", "label": "Lab"},
            {"module_index": 1, "index": 2, "key_type": "SPEED_DIAL"},
        ]
        deps = {"device:SEPAA112233": "wx-dev-bbb"}
        result = handle_device_layout_configure(data, deps, {})
        _, _, body = result[0]  # PUT layout (no members)
        assert "kemKeys" in body
        assert body["kemKeys"][0] == {"kemModuleIndex": 1, "kemKeyIndex": 1, "kemKeyType": "SPEED_DIAL", "kemKeyLabel": "Lab"}
        assert body["kemKeys"][1] == {"kemModuleIndex": 1, "kemKeyIndex": 2, "kemKeyType": "SPEED_DIAL"}

    def test_orgid_injected(self):
        data = self._base_data()
        data["line_members"] = []
        deps = {"device:SEPAA112233": "wx-dev-bbb"}
        result = handle_device_layout_configure(data, deps, {"orgId": "ORG999"})
        for _, url, _ in result:
            assert "orgId=ORG999" in url


class TestSoftkeyConfigConfigure:
    def test_basic(self):
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001122334455",
            "psk_mappings": [
                {"psk_slot": "PSK1", "keyword": "park"},
                {"psk_slot": "PSK2", "keyword": "hold"},
            ],
            "state_key_lists": {
                "idle": ["redial", "newcall", "cfwd"],
                "connected": ["hold", "endcall", "xfer"],
            },
        }
        deps = {"device:SEP001122334455": "wx-dev-aaa"}
        result = handle_softkey_config_configure(data, deps, {})
        assert len(result) == 2

        method1, url1, body1 = result[0]
        assert method1 == "PUT"
        assert "wx-dev-aaa" in url1
        assert "dynamicSettings" in url1
        settings = {s["key"]: s["value"] for s in body1["settings"]}
        assert settings["softKeyLayout.psk.psk1"] == "park"
        assert settings["softKeyLayout.psk.psk2"] == "hold"
        assert settings["softKeyLayout.softKeyMenu.idleKeyList"] == "redial;newcall;cfwd"
        assert settings["softKeyLayout.softKeyMenu.connectedKeyList"] == "hold;endcall;xfer"

        method2, url2, body2 = result[1]
        assert method2 == "POST"
        assert "applyChanges" in url2
        assert body2 is None

    def test_not_psk_target_returns_empty(self):
        data = {
            "is_psk_target": False,
            "device_canonical_id": "device:SEP001122334455",
            "psk_mappings": [{"psk_slot": "PSK1", "keyword": "park"}],
            "state_key_lists": {},
        }
        deps = {"device:SEP001122334455": "wx-dev-aaa"}
        result = handle_softkey_config_configure(data, deps, {})
        assert result == []

    def test_no_device_dep_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001122334455",
            "psk_mappings": [{"psk_slot": "PSK1", "keyword": "park"}],
            "state_key_lists": {},
        }
        result = handle_softkey_config_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device:SEP001122334455" in result.reason

    def test_empty_settings_returns_empty(self):
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001122334455",
            "psk_mappings": [],
            "state_key_lists": {},
        }
        deps = {"device:SEP001122334455": "wx-dev-aaa"}
        result = handle_softkey_config_configure(data, deps, {})
        assert result == []

    def test_orgid_injected(self):
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001122334455",
            "psk_mappings": [{"psk_slot": "PSK1", "keyword": "park"}],
            "state_key_lists": {},
        }
        deps = {"device:SEP001122334455": "wx-dev-aaa"}
        result = handle_softkey_config_configure(data, deps, {"orgId": "ORG777"})
        for _, url, _ in result:
            assert "orgId=ORG777" in url


class TestSNRConfigure:
    def test_basic_snr(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "enabled": True,
            "alert_click_to_dial": False,
            "numbers": [
                {"phone_number": "+14155551234", "enabled": True, "name": "Mobile", "answer_confirmation": False},
            ],
        }
        deps = {"user:jdoe": "wx-person-111"}
        result = handle_snr_configure(data, deps, {})
        # 1 PUT enable + 1 POST number = 2 calls
        assert len(result) == 2
        assert result[0][0] == "PUT"
        assert "singleNumberReach" in result[0][1]
        assert result[1][0] == "POST"
        assert "singleNumberReach/numbers" in result[1][1]

    def test_no_person_returns_skipped(self):
        from wxcli.migration.execute.handlers import SkippedResult
        data = {"user_canonical_id": "user:jdoe", "numbers": [{"phone_number": "+1"}]}
        result = handle_snr_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jdoe" in result.reason

    def test_no_numbers_returns_empty(self):
        data = {"user_canonical_id": "user:jdoe", "numbers": []}
        result = handle_snr_configure(data, {"user:jdoe": "wx-1"}, {})
        assert result == []

    def test_multiple_numbers(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "enabled": True,
            "numbers": [
                {"phone_number": "+14155551111", "enabled": True},
                {"phone_number": "+14155552222", "enabled": True},
            ],
        }
        deps = {"user:jdoe": "wx-person-111"}
        result = handle_snr_configure(data, deps, {})
        # 1 PUT + 2 POST = 3 calls
        assert len(result) == 3

    def test_orgid_injected(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "enabled": True,
            "numbers": [{"phone_number": "+14155551234", "enabled": True}],
        }
        deps = {"user:jdoe": "wx-1"}
        result = handle_snr_configure(data, deps, {"orgId": "ORG123"})
        for _, url, _ in result:
            assert "orgId=ORG123" in url


class TestRouteListCreate:
    def test_basic(self):
        data = {
            "name": "US-West-RL",
            "location_id": "location:HQ",
            "route_group_id": "route_group:US-West-RG",
        }
        deps = {
            "location:HQ": "wx-loc-123",
            "route_group:US-West-RG": "wx-rg-456",
        }
        result = handle_route_list_create(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "/telephony/config/premisePstn/routeLists" in url
        assert body["name"] == "US-West-RL"
        assert body["locationId"] == "wx-loc-123"
        assert body["routeGroupId"] == "wx-rg-456"

    def test_missing_route_group_returns_skipped(self):
        """Wave 2A: missing route group webex_id is a hard prerequisite miss."""
        from wxcli.migration.execute.handlers import SkippedResult

        data = {
            "name": "US-West-RL",
            "location_id": "location:HQ",
            "route_group_id": "route_group:US-West-RG",
        }
        deps = {"location:HQ": "wx-loc-123"}
        result = handle_route_list_create(data, deps, {})
        assert isinstance(result, SkippedResult)

    def test_missing_location_falls_back_to_deps(self):
        data = {
            "name": "US-West-RL",
            "route_group_id": "route_group:US-West-RG",
        }
        deps = {
            "location:HQ": "wx-loc-123",
            "route_group:US-West-RG": "wx-rg-456",
        }
        result = handle_route_list_create(data, deps, {})
        assert len(result) == 1
        _, _, body = result[0]
        assert body["locationId"] == "wx-loc-123"

    def test_orgid_injected(self):
        data = {
            "name": "US-West-RL",
            "location_id": "location:HQ",
            "route_group_id": "route_group:US-West-RG",
        }
        deps = {
            "location:HQ": "wx-loc-123",
            "route_group:US-West-RG": "wx-rg-456",
        }
        result = handle_route_list_create(data, deps, {"orgId": "org-789"})
        _, url, _ = result[0]
        assert "orgId=org-789" in url


class TestRouteListConfigureNumbers:
    def test_basic(self):
        data = {
            "canonical_id": "route_list:US-West-RL",
            "numbers": ["+14085551000", "+14085551001"],
        }
        deps = {"route_list:US-West-RL": "wx-rl-abc"}
        result = handle_route_list_configure_numbers(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-rl-abc/numbers" in url
        assert len(body["numbers"]) == 2
        assert body["numbers"][0] == {"number": "+14085551000", "action": "ADD"}
        assert body["numbers"][1] == {"number": "+14085551001", "action": "ADD"}

    def test_no_numbers_returns_empty(self):
        data = {"canonical_id": "route_list:US-West-RL", "numbers": []}
        deps = {"route_list:US-West-RL": "wx-rl-abc"}
        result = handle_route_list_configure_numbers(data, deps, {})
        assert result == []

    def test_no_webex_id_returns_skipped(self):
        """Wave 2A: missing route list webex_id is a hard prerequisite miss."""
        from wxcli.migration.execute.handlers import SkippedResult

        data = {
            "canonical_id": "route_list:US-West-RL",
            "numbers": ["+14085551000"],
        }
        deps = {}
        result = handle_route_list_configure_numbers(data, deps, {})
        assert isinstance(result, SkippedResult)


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

    def test_device_create_activation_code_registered(self):
        """device:create_activation_code must have a tier and API call estimate."""
        from wxcli.migration.execute import TIER_ASSIGNMENTS, API_CALL_ESTIMATES
        assert ("device", "create_activation_code") in TIER_ASSIGNMENTS
        assert TIER_ASSIGNMENTS[("device", "create_activation_code")] == 3
        assert API_CALL_ESTIMATES.get("device:create_activation_code") == 1
