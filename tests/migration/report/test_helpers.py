"""Tests for report helper utilities."""
import pytest
from wxcli.migration.report.helpers import strip_canonical_id, friendly_site_name


class TestStripCanonicalId:
    def test_css_prefix(self):
        assert strip_canonical_id("css:Standard-Employee-CSS") == "Standard-Employee-CSS"

    def test_device_prefix(self):
        assert strip_canonical_id("device:SEP001122334455") == "SEP001122334455"

    def test_dn_prefix_with_partition(self):
        assert strip_canonical_id("dn:1001:Internal-PT") == "1001 (Internal-PT)"

    def test_voicemail_profile_prefix(self):
        assert strip_canonical_id("voicemail_profile:Default") == "Default"

    def test_location_prefix(self):
        assert strip_canonical_id("location:DP-HQ-Phones") == "DP-HQ-Phones"

    def test_no_prefix(self):
        assert strip_canonical_id("plain-string") == "plain-string"

    def test_empty_string(self):
        assert strip_canonical_id("") == ""

    def test_partition_prefix(self):
        assert strip_canonical_id("partition:Internal-PT") == "Internal-PT"

    def test_unknown_prefix_with_colon(self):
        # Unknown prefixes: strip the prefix
        assert strip_canonical_id("trunk:sip-trunk-1") == "sip-trunk-1"


class TestFriendlySiteName:
    def test_strip_dp_prefix_and_phones_suffix(self):
        assert friendly_site_name("DP-HQ-Phones") == "HQ"

    def test_strip_dp_prefix_and_softphones_suffix(self):
        assert friendly_site_name("DP-HQ-Softphones") == "HQ"

    def test_strip_dp_prefix_and_commonarea_suffix(self):
        assert friendly_site_name("DP-CommonArea") == "CommonArea"

    def test_dp_prefix_only(self):
        assert friendly_site_name("DP-Branch") == "Branch"

    def test_no_prefix_no_suffix(self):
        assert friendly_site_name("MainOffice") == "MainOffice"

    def test_empty_string(self):
        assert friendly_site_name("") == ""

    def test_just_dp(self):
        assert friendly_site_name("DP-") == ""

    def test_multi_segment_name(self):
        assert friendly_site_name("DP-Austin-Branch-Phones") == "Austin-Branch"
