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
