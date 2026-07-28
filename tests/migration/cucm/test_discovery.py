"""Tests for the CUCM discovery orchestrator.

Covers:
- run_discovery: extractor execution order, version detection, error handling
- DiscoveryResult: to_summary output
- Collection status: telling an empty section apart from an uncollected one
"""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.discovery import (
    COLLECTION_STATUS_KEY,
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


# Extractor name -> the class discovery.py imports for it.
_EXTRACTOR_CLASSES = {
    "locations": "LocationExtractor",
    "users": "UserExtractor",
    "devices": "DeviceExtractor",
    "routing": "RoutingExtractor",
    "features": "FeatureExtractor",
    "voicemail": "VoicemailExtractor",
    "templates": "TemplateExtractor",
    "informational": "InformationalExtractor",
    "tier4": "Tier4Extractor",
    "remote_destinations": "RemoteDestinationExtractor",
    "e911": "E911Extractor",
    "device_profiles": "DeviceProfileExtractor",
    "moh": "MOHExtractor",
    "announcements": "AnnouncementExtractor",
}


def _patch_extractors(mocks):
    """Patch all 14 extractor classes to return the given instances."""
    return patch.multiple(
        "wxcli.migration.cucm.discovery",
        **{
            _EXTRACTOR_CLASSES[name]: MagicMock(return_value=inst)
            for name, inst in mocks.items()
        },
    )


def _make_mock_conn():
    """Mock AXLConnection using the REAL dropped-tag snapshot/delta logic."""
    conn = MagicMock()
    conn.get_version.return_value = "14.0.1.11900(132)"
    conn.dropped_tags = {}
    conn.dropped_tags_snapshot.side_effect = (
        lambda: AXLConnection.dropped_tags_snapshot(conn)
    )
    conn.dropped_tags_since.side_effect = (
        lambda snap: AXLConnection.dropped_tags_since(conn, snap)
    )
    return conn


def _dropping(conn, method, tag, result):
    """Extractor side effect that drops a returnedTag the way _call_list does."""
    def extract():
        conn.dropped_tags.setdefault(method, []).append(tag)
        return result
    return extract


# ======================================================================
# run_discovery tests
# ======================================================================


class TestRunDiscovery:
    """run_discovery: orchestrates all extractors in order."""

    @patch("wxcli.migration.cucm.discovery.AnnouncementExtractor")
    @patch("wxcli.migration.cucm.discovery.MOHExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceProfileExtractor")
    @patch("wxcli.migration.cucm.discovery.E911Extractor")
    @patch("wxcli.migration.cucm.discovery.RemoteDestinationExtractor")
    @patch("wxcli.migration.cucm.discovery.Tier4Extractor")
    @patch("wxcli.migration.cucm.discovery.InformationalExtractor")
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
        MockInformational,
        MockTier4,
        MockRemoteDestination,
        MockE911,
        MockDeviceProfile,
        MockMOH,
        MockAnnouncement,
    ):
        """All 14 extractors run in order, journal entry written."""
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
            "informational": _make_mock_extractor("informational", total=1),
            "tier4": _make_mock_extractor("tier4", total=6),
            "remote_destinations": _make_mock_extractor("remote_destinations", total=3),
            "e911": _make_mock_extractor("e911", total=2),
            "device_profiles": _make_mock_extractor("device_profiles", total=4),
            "moh": _make_mock_extractor("moh", total=1),
            "announcements": _make_mock_extractor("announcements", total=2),
        }

        MockLocation.return_value = mock_extractors["locations"]
        MockUser.return_value = mock_extractors["users"]
        MockDevice.return_value = mock_extractors["devices"]
        MockRouting.return_value = mock_extractors["routing"]
        MockFeature.return_value = mock_extractors["features"]
        MockVoicemail.return_value = mock_extractors["voicemail"]
        MockTemplate.return_value = mock_extractors["templates"]
        MockInformational.return_value = mock_extractors["informational"]
        MockTier4.return_value = mock_extractors["tier4"]
        MockRemoteDestination.return_value = mock_extractors["remote_destinations"]
        MockE911.return_value = mock_extractors["e911"]
        MockDeviceProfile.return_value = mock_extractors["device_profiles"]
        MockMOH.return_value = mock_extractors["moh"]
        MockAnnouncement.return_value = mock_extractors["announcements"]

        result = run_discovery(mock_conn, mock_store)

        # All 14 extractors should have been called
        for name in EXTRACTOR_ORDER:
            mock_extractors[name].extract.assert_called_once()

        # Result should contain all 14 extractor results
        assert len(result.extractor_results) == len(EXTRACTOR_ORDER)
        for name in EXTRACTOR_ORDER:
            assert name in result.extractor_results

        # Total objects should be sum of all extractors
        assert result.total_objects == 3 + 10 + 20 + 15 + 8 + 2 + 4 + 1 + 6 + 3 + 2 + 4 + 1 + 2

        # Journal entry should have been written
        mock_store.add_journal_entry.assert_called_once()
        call_kwargs = mock_store.add_journal_entry.call_args
        assert call_kwargs[1]["entry_type"] == "discovery_complete" or \
            call_kwargs.kwargs.get("entry_type") == "discovery_complete"

        # Run ID should be set from store
        assert result.run_id == "20260322T120000-abc12345"

    @patch("wxcli.migration.cucm.discovery.AnnouncementExtractor")
    @patch("wxcli.migration.cucm.discovery.MOHExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceProfileExtractor")
    @patch("wxcli.migration.cucm.discovery.E911Extractor")
    @patch("wxcli.migration.cucm.discovery.RemoteDestinationExtractor")
    @patch("wxcli.migration.cucm.discovery.Tier4Extractor")
    @patch("wxcli.migration.cucm.discovery.InformationalExtractor")
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
        MockInformational,
        MockTier4,
        MockRemoteDestination,
        MockE911,
        MockDeviceProfile,
        MockMOH,
        MockAnnouncement,
    ):
        """get_version() is called and result stored."""
        mock_conn = MagicMock()
        mock_conn.get_version.return_value = "12.5.1.15000"
        mock_store = _make_mock_store()

        # Set up extractors to return minimal results
        for MockClass in [MockLocation, MockUser, MockDevice, MockRouting, MockFeature, MockVoicemail, MockTemplate, MockInformational, MockTier4, MockRemoteDestination, MockE911, MockDeviceProfile, MockMOH, MockAnnouncement]:
            ext = _make_mock_extractor("test")
            MockClass.return_value = ext

        result = run_discovery(mock_conn, mock_store)

        mock_conn.get_version.assert_called_once()
        assert result.cucm_version == "12.5.1.15000"

    @patch("wxcli.migration.cucm.discovery.AnnouncementExtractor")
    @patch("wxcli.migration.cucm.discovery.MOHExtractor")
    @patch("wxcli.migration.cucm.discovery.DeviceProfileExtractor")
    @patch("wxcli.migration.cucm.discovery.E911Extractor")
    @patch("wxcli.migration.cucm.discovery.RemoteDestinationExtractor")
    @patch("wxcli.migration.cucm.discovery.Tier4Extractor")
    @patch("wxcli.migration.cucm.discovery.InformationalExtractor")
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
        MockInformational,
        MockTier4,
        MockRemoteDestination,
        MockE911,
        MockDeviceProfile,
        MockMOH,
        MockAnnouncement,
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
            ("informational", MockInformational),
            ("tier4", MockTier4),
            ("remote_destinations", MockRemoteDestination),
            ("e911", MockE911),
            ("device_profiles", MockDeviceProfile),
            ("moh", MockMOH),
            ("announcements", MockAnnouncement),
        ]:
            MockClass.return_value = _make_mock_extractor(name, total=5)

        result = run_discovery(mock_conn, mock_store)

        # All extractors should still have results (locations with error)
        assert len(result.extractor_results) == len(EXTRACTOR_ORDER)

        # The failing extractor should have error captured
        loc_result = result.extractor_results["locations"]
        assert loc_result.failed == 0  # ExtractionResult created with defaults
        assert len(loc_result.errors) == 1
        assert "AXL connection lost" in loc_result.errors[0]

        # Other extractors should have succeeded
        for name in ["users", "devices", "routing", "features", "voicemail", "templates", "informational", "tier4", "remote_destinations", "e911", "device_profiles", "moh", "announcements"]:
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


class TestExtractionResultStatus:
    """A total of 0 has four meanings; status must keep them apart."""

    def test_found_nothing_and_nothing_went_wrong_is_ok(self):
        assert ExtractionResult(extractor="moh", total=0).status == "ok"

    def test_found_things_cleanly_is_ok(self):
        assert ExtractionResult(extractor="moh", total=7).status == "ok"

    def test_errored_with_nothing_collected_is_failed(self):
        r = ExtractionResult(extractor="moh", total=0)
        r.errors.append("listMohAudioSource failed: Unknown fault occured")
        assert r.status == "failed"

    def test_errored_with_some_collected_is_partial(self):
        r = ExtractionResult(extractor="moh", total=3)
        r.errors.append("getMohAudioSource failed: timeout")
        assert r.status == "partial"

    def test_failed_count_alone_is_enough_to_be_failed(self):
        assert ExtractionResult(extractor="moh", total=0, failed=2).status == "failed"

    def test_only_unsupported_work_is_unsupported_not_failed(self):
        r = ExtractionResult(extractor="features", total=0)
        r.record_unsupported("executiveassistant SQL query unsupported — skipped")
        assert r.status == "unsupported"

    def test_unsupported_alongside_real_data_is_partial(self):
        r = ExtractionResult(extractor="features", total=12)
        r.record_unsupported("executiveassistant SQL query unsupported — skipped")
        assert r.status == "partial"

    def test_a_real_error_outranks_an_unsupported_note(self):
        r = ExtractionResult(extractor="features", total=0)
        r.record_unsupported("executiveassistant SQL query unsupported — skipped")
        r.errors.append("hunt pilot query failed: connection reset")
        assert r.status == "failed"

    def test_dropped_tags_make_a_clean_run_partial(self):
        r = ExtractionResult(extractor="tier4", total=40)
        r.dropped_tags = {"listCallingPartyTransformationPattern": ["callingSearchSpaceName"]}
        assert r.status == "partial"

    def test_record_unsupported_does_not_touch_failed(self):
        r = ExtractionResult(extractor="features", total=0)
        r.record_unsupported("note")
        assert r.failed == 0
        # Also lands in errors, so consumers that predate `unsupported` still see it.
        assert r.errors == ["note"]
        assert r.unsupported == ["note"]

    def test_to_status_carries_every_field(self):
        r = ExtractionResult(extractor="tier4", total=40, failed=1)
        r.errors.append("boom")
        r.record_unsupported("skipped-thing")
        r.dropped_tags = {"listCalledPartyTransformationPattern": ["callingSearchSpaceName"]}
        assert r.to_status() == {
            "name": "tier4",
            "total": 40,
            "failed": 1,
            "status": "partial",
            "errors": ["boom", "skipped-thing"],
            "unsupported": ["skipped-thing"],
            "dropped_tags": {
                "listCalledPartyTransformationPattern": ["callingSearchSpaceName"]
            },
        }

    def test_to_status_copies_its_mutable_fields(self):
        r = ExtractionResult(extractor="moh", total=1)
        r.dropped_tags = {"listMohAudioSource": ["isDefault"]}
        status = r.to_status()
        r.errors.append("late error")
        r.dropped_tags["listMohAudioSource"].append("late tag")
        assert status["errors"] == []
        assert status["dropped_tags"] == {"listMohAudioSource": ["isDefault"]}


class TestCollectionStatus:
    """DiscoveryResult.to_collection_status: the raw_data.json record."""

    @staticmethod
    def _result():
        dr = DiscoveryResult()
        dr.run_id = "20260322T120000-abc12345"
        dr.cucm_version = "14.0.1.11900(132)"
        dr.started_at = "2026-03-22T12:00:00+00:00"
        dr.completed_at = "2026-03-22T12:05:00+00:00"
        return dr

    def test_empty_and_failed_are_distinguishable(self):
        """The whole point: both extracted 0, for opposite reasons."""
        genuinely_empty = ExtractionResult(extractor="remote_destinations", total=0)
        could_not_look = ExtractionResult(extractor="moh", total=0)
        could_not_look.errors.append("listMohAudioSource failed: Unknown fault occured")

        dr = self._result()
        dr.extractor_results = {
            "remote_destinations": genuinely_empty,
            "moh": could_not_look,
        }
        extractors = dr.to_collection_status()["extractors"]

        assert extractors["remote_destinations"]["total"] == 0
        assert extractors["moh"]["total"] == 0
        assert extractors["remote_destinations"]["status"] == "ok"
        assert extractors["moh"]["status"] == "failed"
        assert extractors["moh"]["errors"] == [
            "listMohAudioSource failed: Unknown fault occured"
        ]

    def test_carries_the_run_envelope_and_totals(self):
        dr = self._result()
        dr.extractor_results = {
            "users": ExtractionResult(extractor="users", total=50, failed=3),
            "devices": ExtractionResult(extractor="devices", total=30),
        }
        status = dr.to_collection_status()

        assert status["run_type"] == "discovery"
        assert status["run_id"] == "20260322T120000-abc12345"
        assert status["cucm_version"] == "14.0.1.11900(132)"
        assert status["started_at"] == "2026-03-22T12:00:00+00:00"
        assert status["completed_at"] == "2026-03-22T12:05:00+00:00"
        assert status["total_objects"] == 80
        assert status["total_failed"] == 3

    def test_records_dropped_tags(self):
        r = ExtractionResult(extractor="tier4", total=40)
        r.dropped_tags = {
            "listCallingPartyTransformationPattern": ["callingSearchSpaceName"]
        }
        dr = self._result()
        dr.extractor_results = {"tier4": r}
        tier4 = dr.to_collection_status()["extractors"]["tier4"]

        # Collected, but not in full — and that is now machine-readable.
        assert tier4["status"] == "partial"
        assert tier4["dropped_tags"] == {
            "listCallingPartyTransformationPattern": ["callingSearchSpaceName"]
        }

    def test_journal_summary_shape_is_unchanged(self):
        """to_summary feeds the journal; only to_collection_status is enriched."""
        dr = self._result()
        dr.extractor_results = {
            "users": ExtractionResult(extractor="users", total=50, failed=3),
        }
        assert dr.to_summary()["extractors"] == {"users": {"total": 50, "failed": 3}}

    def test_run_discovery_writes_it_into_raw_data(self):
        """End-to-end: the record lands in what discover dumps to disk."""
        conn = _make_mock_conn()
        store = _make_mock_store()
        mocks = {
            name: _make_mock_extractor(name, total=2) for name in EXTRACTOR_ORDER
        }
        # tier4 collects rows, but the schema rejected one of its fields.
        mocks["tier4"].extract.side_effect = _dropping(
            conn,
            "listCallingPartyTransformationPattern",
            "callingSearchSpaceName",
            ExtractionResult(extractor="tier4", total=2),
        )
        # moh could not look at all; remote_destinations looked and found none.
        moh_failed = ExtractionResult(extractor="moh", total=0)
        moh_failed.errors.append("listMohAudioSource failed: Unknown fault occured")
        mocks["moh"].extract.return_value = moh_failed
        mocks["remote_destinations"].extract.return_value = ExtractionResult(
            extractor="remote_destinations", total=0
        )

        with _patch_extractors(mocks):
            result = run_discovery(conn, store)

        status = result.raw_data[COLLECTION_STATUS_KEY]
        extractors = status["extractors"]

        # Two zeros, two different reasons.
        assert extractors["moh"]["total"] == 0
        assert extractors["moh"]["status"] == "failed"
        assert extractors["remote_destinations"]["total"] == 0
        assert extractors["remote_destinations"]["status"] == "ok"

        # The dropped tag is attributed to the extractor that provoked it.
        assert extractors["tier4"]["dropped_tags"] == {
            "listCallingPartyTransformationPattern": ["callingSearchSpaceName"]
        }
        assert extractors["tier4"]["status"] == "partial"
        assert all(
            not e["dropped_tags"]
            for name, e in extractors.items()
            if name != "tier4"
        )

        # Everything else is untouched and still keyed by extractor name.
        assert extractors["users"]["status"] == "ok"
        assert status["cucm_version"] == "14.0.1.11900(132)"

    def test_collection_status_key_does_not_shadow_an_extractor(self):
        assert COLLECTION_STATUS_KEY not in EXTRACTOR_ORDER
        assert COLLECTION_STATUS_KEY.startswith("_")

    def test_raw_data_still_keyed_by_extractor_name(self):
        """Backward compatibility: the new key is additive."""
        conn = _make_mock_conn()
        mocks = {
            name: _make_mock_extractor(name, total=1) for name in EXTRACTOR_ORDER
        }
        with _patch_extractors(mocks):
            result = run_discovery(conn, _make_mock_store())

        for name in EXTRACTOR_ORDER:
            assert result.raw_data[name] == {name: [{"mock": True}]}
        assert set(result.raw_data) == set(EXTRACTOR_ORDER) | {COLLECTION_STATUS_KEY}

    def test_is_json_serializable(self):
        r = ExtractionResult(extractor="tier4", total=40, failed=1)
        r.record_unsupported("skipped")
        r.dropped_tags = {"listX": ["y"]}
        dr = self._result()
        dr.extractor_results = {"tier4": r}
        assert json.loads(json.dumps(dr.to_collection_status())) == \
            dr.to_collection_status()
