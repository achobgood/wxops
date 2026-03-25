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
