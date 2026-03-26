"""Tests for the CUCM discovery orchestrator.

Covers:
- run_discovery: extractor execution order, version detection, error handling
- DiscoveryResult: to_summary output
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from wxcli.migration.cucm.discovery import (
    EXTRACTOR_ORDER,
    DiscoveryResult,
    run_discovery,
)
from wxcli.migration.cucm.extractors.base import ExtractionResult


def _make_mock_store():
    """Create a mock MigrationStore with required properties."""
    store = MagicMock()
    type(store).current_run_id = PropertyMock(return_value="20260322T120000-abc12345")
    return store


def _make_mock_extractor(name, total=5, failed=0, errors=None):
    """Create a mock extractor that returns a controlled ExtractionResult."""
    mock = MagicMock()
    mock.name = name
    mock.results = {name: [{"mock": True}]}
    mock.extract.return_value = ExtractionResult(
        extractor=name,
        total=total,
        failed=failed,
        errors=errors or [],
    )
    return mock


# ======================================================================
# run_discovery tests
# ======================================================================


class TestRunDiscovery:
    """run_discovery: orchestrates all extractors in order."""

    @patch("wxcli.migration.cucm.discovery.TemplateExtractor")
    @patch("wxcli.migration.cucm.discovery.VoicemailExtractor")
    @patch("wxcli.migration.cucm.discovery.FeatureExtractor")
    @patch("wxcli.migration.cucm.discovery.RoutingExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceExtractor")
    @patch("wxcli.migration.cucm.discovery.UserExtractor")
    @patch("wxcli.migration.cucm.discovery.LocationExtractor")
    def test_run_discovery_all_extractors(
        self,
        MockLocation,
        MockUser,
        MockDevice,
        MockRouting,
        MockFeature,
        MockVoicemail,
        MockTemplate,
    ):
        """All 7 extractors run in order, journal entry written."""
        mock_conn = MagicMock()
        mock_conn.get_version.return_value = "14.0.1.12345"
        mock_store = _make_mock_store()

        # Each mock constructor returns a mock extractor instance
        mock_extractors = {
            "locations": _make_mock_extractor("locations", total=3),
            "users": _make_mock_extractor("users", total=10),
            "devices": _make_mock_extractor("devices", total=20),
            "routing": _make_mock_extractor("routing", total=15),
            "features": _make_mock_extractor("features", total=8),
            "voicemail": _make_mock_extractor("voicemail", total=2),
            "templates": _make_mock_extractor("templates", total=4),
        }

        MockLocation.return_value = mock_extractors["locations"]
        MockUser.return_value = mock_extractors["users"]
        MockDevice.return_value = mock_extractors["devices"]
        MockRouting.return_value = mock_extractors["routing"]
        MockFeature.return_value = mock_extractors["features"]
        MockVoicemail.return_value = mock_extractors["voicemail"]
        MockTemplate.return_value = mock_extractors["templates"]

        result = run_discovery(mock_conn, mock_store)

        # All 7 extractors should have been called
        for name in EXTRACTOR_ORDER:
            mock_extractors[name].extract.assert_called_once()

        # Result should contain all 7 extractor results
        assert len(result.extractor_results) == 7
        for name in EXTRACTOR_ORDER:
            assert name in result.extractor_results

        # Total objects should be sum of all extractors
        assert result.total_objects == 3 + 10 + 20 + 15 + 8 + 2 + 4

        # Journal entry should have been written
        mock_store.add_journal_entry.assert_called_once()
        call_kwargs = mock_store.add_journal_entry.call_args
        assert call_kwargs[1]["entry_type"] == "discovery_complete" or \
            call_kwargs.kwargs.get("entry_type") == "discovery_complete"

        # Run ID should be set from store
        assert result.run_id == "20260322T120000-abc12345"

    @patch("wxcli.migration.cucm.discovery.TemplateExtractor")
    @patch("wxcli.migration.cucm.discovery.VoicemailExtractor")
    @patch("wxcli.migration.cucm.discovery.FeatureExtractor")
    @patch("wxcli.migration.cucm.discovery.RoutingExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceExtractor")
    @patch("wxcli.migration.cucm.discovery.UserExtractor")
    @patch("wxcli.migration.cucm.discovery.LocationExtractor")
    def test_run_discovery_version_detection(
        self,
        MockLocation,
        MockUser,
        MockDevice,
        MockRouting,
        MockFeature,
        MockVoicemail,
        MockTemplate,
    ):
        """get_version() is called and result stored."""
        mock_conn = MagicMock()
        mock_conn.get_version.return_value = "12.5.1.15000"
        mock_store = _make_mock_store()

        # Set up extractors to return minimal results
        for MockClass in [MockLocation, MockUser, MockDevice, MockRouting, MockFeature, MockVoicemail, MockTemplate]:
            ext = _make_mock_extractor("test")
            MockClass.return_value = ext

        result = run_discovery(mock_conn, mock_store)

        mock_conn.get_version.assert_called_once()
        assert result.cucm_version == "12.5.1.15000"

    @patch("wxcli.migration.cucm.discovery.TemplateExtractor")
    @patch("wxcli.migration.cucm.discovery.VoicemailExtractor")
    @patch("wxcli.migration.cucm.discovery.FeatureExtractor")
    @patch("wxcli.migration.cucm.discovery.RoutingExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceExtractor")
    @patch("wxcli.migration.cucm.discovery.UserExtractor")
    @patch("wxcli.migration.cucm.discovery.LocationExtractor")
    def test_run_discovery_extractor_failure(
        self,
        MockLocation,
        MockUser,
        MockDevice,
        MockRouting,
        MockFeature,
        MockVoicemail,
        MockTemplate,
    ):
        """One extractor raises exception — others still run, error captured."""
        mock_conn = MagicMock()
        mock_conn.get_version.return_value = "14.0"
        mock_store = _make_mock_store()

        # locations extractor raises an exception
        failing_extractor = MagicMock()
        failing_extractor.name = "locations"
        failing_extractor.extract.side_effect = RuntimeError("AXL connection lost")
        failing_extractor.results = {}
        MockLocation.return_value = failing_extractor

        # All others succeed
        for name, MockClass in [
            ("users", MockUser),
            ("devices", MockDevice),
            ("routing", MockRouting),
            ("features", MockFeature),
            ("voicemail", MockVoicemail),
            ("templates", MockTemplate),
        ]:
            MockClass.return_value = _make_mock_extractor(name, total=5)

        result = run_discovery(mock_conn, mock_store)

        # All 7 extractors should still have results (locations with error)
        assert len(result.extractor_results) == 7

        # The failing extractor should have error captured
        loc_result = result.extractor_results["locations"]
        assert loc_result.failed == 0  # ExtractionResult created with defaults
        assert len(loc_result.errors) == 1
        assert "AXL connection lost" in loc_result.errors[0]

        # Other extractors should have succeeded
        for name in ["users", "devices", "routing", "features", "voicemail", "templates"]:
            assert result.extractor_results[name].total == 5
            assert result.extractor_results[name].failed == 0

        # Journal entry should still be written despite the failure
        mock_store.add_journal_entry.assert_called_once()


# ======================================================================
# DiscoveryResult tests
# ======================================================================


class TestDiscoveryResult:
    """DiscoveryResult: to_summary produces correct structure."""

    def test_discovery_result_summary(self):
        """Manually create DiscoveryResult, verify to_summary output."""
        dr = DiscoveryResult()
        dr.run_id = "20260322T120000-abc12345"
        dr.cucm_version = "14.0.1.12345"
        dr.started_at = "2026-03-22T12:00:00+00:00"
        dr.completed_at = "2026-03-22T12:05:00+00:00"

        dr.extractor_results = {
            "locations": ExtractionResult(extractor="locations", total=10, failed=1),
            "users": ExtractionResult(extractor="users", total=50, failed=3),
            "devices": ExtractionResult(extractor="devices", total=30, failed=0),
        }

        summary = dr.to_summary()

        assert summary["run_type"] == "discovery"
        assert summary["run_id"] == "20260322T120000-abc12345"
        assert summary["cucm_version"] == "14.0.1.12345"
        assert summary["started_at"] == "2026-03-22T12:00:00+00:00"
        assert summary["completed_at"] == "2026-03-22T12:05:00+00:00"

        # Verify extractors section
        extractors = summary["extractors"]
        assert len(extractors) == 3

        assert extractors["locations"] == {"total": 10, "failed": 1}
        assert extractors["users"] == {"total": 50, "failed": 3}
        assert extractors["devices"] == {"total": 30, "failed": 0}

        # Verify aggregate properties
        assert dr.total_objects == 90  # 10 + 50 + 30
        assert dr.total_failed == 4   # 1 + 3 + 0
