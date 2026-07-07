"""Tests for Tier 4 feature gap extractor."""

from unittest.mock import MagicMock

from wxcli.migration.cucm.extractors.tier4 import Tier4Extractor


def _mock_conn():
    """Create a mock AXL connection."""
    conn = MagicMock()
    return conn


class TestTier4ExtractorRecordingProfiles:
    """Item 1: Recording profiles extraction."""

    def test_extracts_recording_profiles(self):
        conn = _mock_conn()
        conn.paginated_list.return_value = [
            {"name": "RecordingProfile-Default", "recordingCssName": "CSS-Recording"},
            {"name": "RecordingProfile-Compliance", "recordingCssName": "CSS-Compliance"},
        ]
        ext = Tier4Extractor(conn)
        ext.extract()
        profiles = ext.results.get("recording_profiles", [])
        assert len(profiles) == 2
        assert profiles[0]["name"] == "RecordingProfile-Default"

    def test_handles_empty_recording_profiles(self):
        conn = _mock_conn()
        conn.paginated_list.return_value = []
        ext = Tier4Extractor(conn)
        ext.extract()
        assert ext.results.get("recording_profiles", []) == []


class TestTier4ExtractorRemoteDestinations:
    """Item 2: Remote destination profiles (SNR)."""

    def test_extracts_remote_destination_profiles(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [],  # recording profiles
            [   # remote destination profiles
                {"name": "RDP-jsmith", "description": "John mobile"},
                {"name": "RDP-jdoe", "description": "Jane home"},
            ],
            [],  # calling party transformations
            [],  # called party transformations
            [],  # device profiles (EM)
        ]
        ext = Tier4Extractor(conn)
        ext.extract()
        rdps = ext.results.get("remote_destination_profiles", [])
        assert len(rdps) == 2
        assert rdps[0]["name"] == "RDP-jsmith"

    def test_handles_extraction_failure(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [],  # recording profiles
            Exception("AXL error"),  # remote destination profiles
            [],  # calling party
            [],  # called party
            [],  # device profiles
        ]
        ext = Tier4Extractor(conn)
        result = ext.extract()
        assert len(result.errors) >= 1
        assert "remote_destination_profiles" in ext.results


class TestTier4ExtractorTransformationPatterns:
    """Item 4: Calling/Called party transformation patterns."""

    def test_extracts_calling_party_transformations(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [],  # recording profiles
            [],  # remote destination profiles
            [   # calling party transformations
                {"pattern": "9.!", "callingSearchSpaceName": "CSS-Internal",
                 "callingPartyTransformationMask": "1XXX"},
            ],
            [],  # called party transformations
            [],  # device profiles
        ]
        ext = Tier4Extractor(conn)
        ext.extract()
        calling = ext.results.get("calling_party_transformations", [])
        assert len(calling) == 1
        assert calling[0]["pattern"] == "9.!"

    def test_extracts_called_party_transformations(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [],  # recording profiles
            [],  # remote destination profiles
            [],  # calling party transformations
            [   # called party transformations
                {"pattern": "+1!", "description": "US normalization"},
            ],
            [],  # device profiles
        ]
        ext = Tier4Extractor(conn)
        ext.extract()
        called = ext.results.get("called_party_transformations", [])
        assert len(called) == 1


class TestTier4ExtractorExtensionMobility:
    """Item 6: Extension Mobility device profiles."""

    def test_extracts_device_profiles(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [],  # recording profiles
            [],  # remote destination profiles
            [],  # calling party
            [],  # called party
            [   # device profiles
                {"name": "DP-jsmith", "description": "John's EM profile"},
                {"name": "DP-jdoe", "description": "Jane's EM profile"},
            ],
        ]
        ext = Tier4Extractor(conn)
        ext.extract()
        profiles = ext.results.get("device_profiles", [])
        assert len(profiles) == 2

    def test_total_count_across_all_types(self):
        conn = _mock_conn()
        conn.paginated_list.side_effect = [
            [{"name": "RP1"}],      # 1 recording profile
            [{"name": "RDP1"}],     # 1 remote destination
            [{"pattern": "9.!"}],   # 1 calling party
            [{"pattern": "+1!"}],   # 1 called party
            [{"name": "DP1"}],      # 1 device profile
        ]
        ext = Tier4Extractor(conn)
        result = ext.extract()
        assert result.total == 5


class TestDeviceExtractorRecordingFields:
    """Item 1: recording fields captured from getLine enrichment."""

    def test_recording_fields_merged_into_line_entry(self):
        """Verify that _enrich_line_with_forwarding also grabs recording fields."""
        from wxcli.migration.cucm.extractors.devices import DeviceExtractor

        conn = _mock_conn()
        ext = DeviceExtractor(conn)

        # Simulate getLine response with recording fields
        conn.get_detail.return_value = {
            "pattern": "1001",
            "recordingProfileName": {"_value_1": "RecProfile-Default"},
            "recordingFlag": "Automatic Call Recording Enabled",
            "callForwardAll": {"forwardToVoiceMail": "false", "destination": ""},
        }

        line_entry = {
            "dirn": {"pattern": "1001", "routePartitionName": {"_value_1": "PT-Internal"}},
        }
        ext._enrich_line_with_forwarding(line_entry, "1001", "PT-Internal")

        assert line_entry.get("recordingProfileName") is not None
        assert line_entry.get("recordingFlag") == "Automatic Call Recording Enabled"


class TestTier4Normalizers:
    """Test that tier4 raw data normalizes into MigrationObjects."""

    def test_normalize_recording_profile(self):
        from wxcli.migration.transform.normalizers import normalize_recording_profile
        raw = {"name": "RecProfile-Default", "recordingCssName": "CSS-Rec"}
        obj = normalize_recording_profile(raw, cluster="test")
        assert obj.canonical_id == "info_recording:RecProfile-Default"
        assert obj.pre_migration_state["name"] == "RecProfile-Default"

    def test_normalize_calling_party_xform(self):
        from wxcli.migration.transform.normalizers import normalize_calling_party_xform
        raw = {"pattern": "9.!", "callingSearchSpaceName": "CSS-Int",
               "callingPartyTransformationMask": "1XXX"}
        obj = normalize_calling_party_xform(raw, cluster="test")
        assert obj.canonical_id == "info_calling_xform:9.!"

    def test_normalize_called_party_xform(self):
        from wxcli.migration.transform.normalizers import normalize_called_party_xform
        raw = {"pattern": "+1!", "description": "US norm"}
        obj = normalize_called_party_xform(raw, cluster="test")
        assert obj.canonical_id == "info_called_xform:+1!"

    def test_normalize_info_device_profile(self):
        from wxcli.migration.transform.normalizers import normalize_info_device_profile
        raw = {"name": "DP-jsmith", "description": "John EM", "product": "Cisco 8845"}
        obj = normalize_info_device_profile(raw, cluster="test")
        assert obj.canonical_id == "info_device_profile:DP-jsmith"
        assert obj.pre_migration_state["product"] == "Cisco 8845"
