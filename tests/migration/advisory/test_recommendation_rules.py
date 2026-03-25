"""Tests for per-decision recommendation rules.

Each DecisionType gets a function that examines context + options and returns
(option_id, reasoning) or None.

Reference: spec section 5 for expected behavior per type.
"""
from wxcli.migration.advisory.recommendation_rules import (
    recommend_device_firmware_convertible,
    recommend_missing_data,
    recommend_number_conflict,
    recommend_duplicate_user,
    recommend_workspace_license_tier,
    recommend_hotdesk_dn_conflict,
    recommend_device_incompatible,
    recommend_dn_ambiguous,
    recommend_extension_conflict,
    recommend_location_ambiguous,
    recommend_workspace_type_uncertain,
    recommend_feature_approximation,
    recommend_shared_line_complex,
    recommend_css_routing_mismatch,
    recommend_calling_permission_mismatch,
    recommend_voicemail_incompatible,
)


class TestDeviceFirmwareConvertible:
    def test_always_recommends_convert(self):
        r = recommend_device_firmware_convertible({"cucm_model": "8845"}, [])
        assert r is not None
        assert r[0] == "convert"
        assert "8845" in r[1]

    def test_srst_adds_warning(self):
        r = recommend_device_firmware_convertible(
            {"cucm_model": "8845", "has_srst": True}, [])
        assert r[0] == "convert"
        assert "Survivable Gateway" in r[1]

    def test_no_srst_no_warning(self):
        r = recommend_device_firmware_convertible(
            {"cucm_model": "7841"}, [])
        assert "Survivable" not in r[1]


class TestMissingData:
    def test_trunk_password_generates(self):
        r = recommend_missing_data({"subtype": "trunk_password"}, [])
        assert r[0] == "generate"

    def test_missing_fields_skips(self):
        r = recommend_missing_data({"missing_fields": ["email", "location"]}, [])
        assert r[0] == "skip"
        assert "email" in r[1]

    def test_no_context_skips(self):
        r = recommend_missing_data({}, [])
        assert r[0] == "skip"


class TestNumberConflict:
    def test_same_owner_auto_resolves(self):
        r = recommend_number_conflict({"same_owner": True}, [])
        assert r[0] == "auto_resolve"

    def test_different_owner_keeps_existing(self):
        r = recommend_number_conflict({
            "existing_owner": "alice@co.com", "cucm_owner": "bob@co.com"
        }, [])
        assert r[0] == "keep_existing"
        assert "alice" in r[1]


class TestDuplicateUser:
    def test_email_match_merges(self):
        r = recommend_duplicate_user({"email_match": True, "email": "a@b.com"}, [])
        assert r[0] == "merge"
        assert "a@b.com" in r[1]

    def test_name_only_keeps_both(self):
        r = recommend_duplicate_user({"email_match": False}, [])
        assert r[0] == "keep_both"

    def test_userid_match_merges(self):
        r = recommend_duplicate_user(
            {"userid_match": True, "email_match": False}, [])
        assert r[0] == "merge"


class TestWorkspaceLicenseTier:
    def test_basic_features_only(self):
        r = recommend_workspace_license_tier(
            {"features_detected": ["musicOnHold", "doNotDisturb"]}, [])
        assert r[0] == "basic"

    def test_professional_features(self):
        r = recommend_workspace_license_tier(
            {"features_detected": ["callForwarding", "monitoring"]}, [])
        assert r[0] == "professional"

    def test_empty_defaults_basic(self):
        r = recommend_workspace_license_tier({"features_detected": []}, [])
        assert r[0] == "basic"


class TestHotdeskDnConflict:
    def test_always_keep_primary(self):
        r = recommend_hotdesk_dn_conflict({}, [])
        assert r[0] == "keep_primary"


class TestDeviceIncompatible:
    def test_7811_recommends_9841(self):
        r = recommend_device_incompatible({"cucm_model": "7811"}, [])
        assert r is not None
        assert r[0] == "replace"
        assert "9841" in r[1]

    def test_7832_recommends_conference(self):
        r = recommend_device_incompatible({"cucm_model": "7832"}, [])
        assert r[0] == "replace"
        assert "conference" in r[1].lower() or "Room" in r[1]

    def test_unknown_model_returns_none(self):
        r = recommend_device_incompatible({"cucm_model": "XYZZY_9999"}, [])
        assert r is None


class TestDnAmbiguous:
    def test_single_owner_assigns(self):
        r = recommend_dn_ambiguous({"owner_count": 1, "owner_name": "Alice"}, [])
        assert r[0] == "assign"
        assert "Alice" in r[1]

    def test_primary_owner_assigns(self):
        r = recommend_dn_ambiguous({"owner_count": 3, "primary_owner": "Bob"}, [])
        assert r[0] == "assign"
        assert "Bob" in r[1]

    def test_no_primary_returns_none(self):
        r = recommend_dn_ambiguous({"owner_count": 3}, [])
        assert r is None


class TestExtensionConflict:
    def test_more_appearances_keeps(self):
        r = recommend_extension_conflict({
            "ext_a": "1001", "ext_a_appearances": 5, "owner_a": "Alice",
            "ext_b": "1001", "ext_b_appearances": 2, "owner_b": "Bob",
        }, [])
        assert r[0] == "keep_a"
        assert "Alice" in r[1]

    def test_b_more_appearances(self):
        r = recommend_extension_conflict({
            "ext_a": "1001", "ext_a_appearances": 1, "owner_a": "Alice",
            "ext_b": "1001", "ext_b_appearances": 4, "owner_b": "Bob",
        }, [])
        assert r[0] == "keep_b"

    def test_equal_returns_none(self):
        r = recommend_extension_conflict({
            "ext_a_appearances": 2, "ext_b_appearances": 2,
        }, [])
        assert r is None


class TestLocationAmbiguous:
    def test_same_tz_region_consolidates(self):
        r = recommend_location_ambiguous({
            "timezone": "America/Chicago", "region": "US-Central",
            "site_code": "DAL", "dp_names": ["DP_DAL1", "DP_DAL2"],
        }, [])
        assert r[0] == "consolidate"

    def test_different_region_returns_none(self):
        r = recommend_location_ambiguous({
            "same_timezone": True, "same_region": False,
        }, [])
        assert r is None

    def test_all_match_consolidates(self):
        r = recommend_location_ambiguous({
            "timezone": "US/Eastern", "region": "US-East",
            "site_code": "NYC",
        }, [])
        assert r[0] == "consolidate"


class TestWorkspaceTypeUncertain:
    def test_conference_phone_recommends_conference_room(self):
        r = recommend_workspace_type_uncertain({"cucm_model": "7832"}, [])
        assert r[0] == "conference_room"

    def test_desk_phone_no_owner_recommends_common_area(self):
        r = recommend_workspace_type_uncertain(
            {"cucm_model": "8841", "has_owner": False}, [])
        assert r[0] == "common_area"

    def test_ambiguous_returns_none(self):
        r = recommend_workspace_type_uncertain(
            {"cucm_model": "8841", "has_owner": True}, [])
        assert r is None


class TestFeatureApproximation:
    def test_queue_features_recommends_call_queue(self):
        r = recommend_feature_approximation(
            {"has_queue_features": True, "agent_count": 12}, [])
        assert r[0] == "call_queue"

    def test_many_agents_no_queue_still_recommends_cq(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 10}, [])
        assert r[0] == "call_queue"

    def test_small_group_no_queue_recommends_hg(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 3,
             "algorithm": "Top Down"}, [])
        assert r[0] == "hunt_group"

    def test_ambiguous_returns_none(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 6}, [])
        assert r is None

    def test_cti_rp_simple_recommends_accept(self):
        r = recommend_feature_approximation(
            {"classification": "AUTO_ATTENDANT", "complex_script": False}, [])
        assert r[0] == "accept"

    def test_cti_rp_complex_returns_none(self):
        r = recommend_feature_approximation(
            {"classification": "AUTO_ATTENDANT", "complex_script": True}, [])
        assert r is None


class TestSharedLineComplex:
    def test_low_count_shared_line(self):
        r = recommend_shared_line_complex({"appearance_count": 5}, [])
        assert r[0] == "shared_line"

    def test_monitoring_labels_virtual_extension(self):
        r = recommend_shared_line_complex({
            "appearance_count": 4,
            "secondary_labels": ["BLF-Sales", "Monitor-Support"]
        }, [])
        assert r[0] == "virtual_extension"

    def test_mixed_high_count_returns_none(self):
        r = recommend_shared_line_complex({
            "appearance_count": 15,
            "secondary_labels": ["Line2", "BLF-Admin"]
        }, [])
        assert r is None


class TestCssRoutingMismatch:
    def test_partition_ordering_dep_manual(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "partition_ordering",
            "pattern": "9.XXXX",
        }, [])
        assert r[0] == "manual"
        assert "partition ordering" in r[1].lower()

    def test_scope_diff_use_union(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "scope_difference",
        }, [])
        assert r[0] == "use_union"

    def test_pattern_conflict_manual(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "pattern_conflict",
            "pattern": "9011!",
            "route_a": "GW1", "route_b": "GW2",
            "dp_a": "DP-Intl", "dp_b": "DP-Domestic",
        }, [])
        assert r[0] == "manual"


class TestCallingPermissionMismatch:
    def test_international_pattern(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "011!"
        }, [])
        assert r[0] == "INTERNATIONAL_CALL"

    def test_toll_pattern(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "1900!"
        }, [])
        assert r[0] == "PREMIUM_SERVICES_NUMBER_ONE"

    def test_unknown_pattern_returns_none(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "5551234"
        }, [])
        assert r is None


class TestVoicemailIncompatible:
    def test_cfna_timeout_maps_ring_count(self):
        r = recommend_voicemail_incompatible({"cfna_timeout": 18}, [])
        assert r[0] == "webex_voicemail"
        assert "3" in r[1]  # 18s / 6s per ring = 3 rings

    def test_unity_settings_in_reasoning(self):
        r = recommend_voicemail_incompatible({
            "unity_features": ["greeting", "mwi"]
        }, [])
        assert r[0] == "webex_voicemail"
        assert "greeting" in r[1]

    def test_no_data_defaults(self):
        r = recommend_voicemail_incompatible({}, [])
        assert r[0] == "webex_voicemail"
        assert "default" in r[1].lower()
