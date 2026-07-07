"""Tests for Tier 4 appendix sections S-V."""

import os

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="t", source_name="t",
        extracted_at="2026-01-01T00:00:00Z",
    )


def _store_with_tier4(tmp_path):
    """Build a store with Tier 4 data for appendix testing."""
    store = MigrationStore(os.path.join(str(tmp_path), "t4.db"))

    # Recording data: 2 phones, 1 with recording enabled
    store.upsert_object(MigrationObject(
        canonical_id="phone:SEP001",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={
            "name": "SEP001", "ownerUserName": "jsmith",
            "lines": [{"dirn": {"pattern": "1001"},
                        "recordingFlag": "Automatic Call Recording Enabled",
                        "recordingProfileName": {"_value_1": "RecProfile-Default"}}],
        },
    ))
    store.upsert_object(MigrationObject(
        canonical_id="phone:SEP002",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={
            "name": "SEP002", "ownerUserName": "jdoe",
            "lines": [{"dirn": {"pattern": "1002"},
                        "recordingFlag": "Call Recording Disabled"}],
        },
    ))

    # Remote destinations
    store.upsert_object(MigrationObject(
        canonical_id="remote_destination:jsmith:Mobile",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={"name": "Mobile", "ownerUserId": "jsmith", "destination": "+15551234567"},
    ))

    # Transformation patterns
    store.upsert_object(MigrationObject(
        canonical_id="info_calling_xform:9.!",
        provenance=_prov(),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": "9.!", "callingPartyTransformationMask": "1XXX",
                             "routePartitionName": "PT-Internal", "description": "Strip 9"},
    ))
    store.upsert_object(MigrationObject(
        canonical_id="info_called_xform:+1!",
        provenance=_prov(),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": "+1!", "calledPartyTransformationMask": "",
                             "routePartitionName": "", "description": "US norm"},
    ))

    # Extension Mobility profiles
    store.upsert_object(MigrationObject(
        canonical_id="info_device_profile:DP-jsmith",
        provenance=_prov(),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "DP-jsmith", "product": "Cisco 8845", "description": "John EM"},
    ))

    return store


class TestRecordingInventorySection:
    def test_section_present(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert 'id="recording-inventory"' in html
        assert "Call Recording" in html

    def test_shows_recording_users(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert "jsmith" in html
        assert "Automatic" in html


class TestSNRSection:
    def test_section_present(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert 'id="snr-inventory"' in html

    def test_shows_remote_destinations(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert "Mobile" in html or "jsmith" in html


class TestTransformationSection:
    def test_section_present(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert 'id="caller-id-xforms"' in html

    def test_shows_patterns(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert "9.!" in html


class TestExtensionMobilitySection:
    def test_section_present(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert 'id="extension-mobility"' in html

    def test_shows_profiles(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = _store_with_tier4(tmp_path)
        html = generate_appendix(store)
        assert "DP-jsmith" in html


class TestEmptyTier4Sections:
    def test_no_tier4_sections_when_empty(self, tmp_path):
        from wxcli.migration.report.appendix import generate_appendix
        store = MigrationStore(os.path.join(str(tmp_path), "empty.db"))
        html = generate_appendix(store)
        assert 'id="recording-inventory"' not in html
        assert 'id="snr-inventory"' not in html
        assert 'id="caller-id-xforms"' not in html
        assert 'id="extension-mobility"' not in html
