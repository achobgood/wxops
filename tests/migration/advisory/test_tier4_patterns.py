"""Tests for Tier 4 feature gap advisory patterns."""

import os
from datetime import datetime, timezone

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))


class TestDetectRecordingEnabledUsers:
    def test_detects_users_with_recording(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_recording_enabled_users

        store = _store(tmp_path)
        # Store a phone object with a line that has recording enabled
        store.upsert_object(MigrationObject(
            canonical_id="phone:SEP001",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "name": "SEP001",
                "ownerUserName": "jsmith",
                "lines": [
                    {"dirn": {"pattern": "1001"},
                     "recordingFlag": "Automatic Call Recording Enabled",
                     "recordingProfileName": {"_value_1": "RecProfile-Default"}},
                ],
            },
        ))
        store.upsert_object(MigrationObject(
            canonical_id="phone:SEP002",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "name": "SEP002",
                "ownerUserName": "jdoe",
                "lines": [
                    {"dirn": {"pattern": "1002"},
                     "recordingFlag": "Call Recording Disabled"},
                ],
            },
        ))
        findings = detect_recording_enabled_users(store)
        assert len(findings) == 1
        assert "1" in findings[0].summary  # 1 user with recording
        assert findings[0].category == "migrate_as_is"

    def test_no_findings_when_no_recording(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_recording_enabled_users

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="phone:SEP001",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "name": "SEP001",
                "lines": [{"dirn": {"pattern": "1001"}, "recordingFlag": "Call Recording Disabled"}],
            },
        ))
        findings = detect_recording_enabled_users(store)
        assert len(findings) == 0


class TestDetectSNRConfiguredUsers:
    def test_detects_snr_profiles(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_snr_configured_users

        store = _store(tmp_path)
        for i in range(3):
            store.upsert_object(MigrationObject(
                canonical_id=f"remote_destination:user{i}:RDP{i}",
                provenance=_prov(),
                status=MigrationStatus.ANALYZED,
                pre_migration_state={"name": f"RDP{i}", "ownerUserId": f"user{i}"},
            ))
        findings = detect_snr_configured_users(store)
        assert len(findings) == 1
        assert "3" in findings[0].summary
        assert findings[0].category == "rebuild"

    def test_no_findings_when_no_snr(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_snr_configured_users
        store = _store(tmp_path)
        findings = detect_snr_configured_users(store)
        assert len(findings) == 0


class TestDetectTransformationPatterns:
    def test_detects_transformation_patterns(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_transformation_patterns

        store = _store(tmp_path)
        for i in range(2):
            store.upsert_object(MigrationObject(
                canonical_id=f"info_calling_xform:9.{i}!",
                provenance=_prov(),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"pattern": f"9.{i}!", "callingPartyTransformationMask": "1XXX"},
            ))
        store.upsert_object(MigrationObject(
            canonical_id="info_called_xform:+1!",
            provenance=_prov(),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"pattern": "+1!", "calledPartyTransformationMask": ""},
        ))
        findings = detect_transformation_patterns(store)
        assert len(findings) == 1
        assert "3" in findings[0].summary  # 2 calling + 1 called
        assert findings[0].category == "rebuild"

    def test_no_findings_when_empty(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_transformation_patterns
        store = _store(tmp_path)
        findings = detect_transformation_patterns(store)
        assert len(findings) == 0


class TestDetectExtensionMobilityUsage:
    def test_detects_em_profiles(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_extension_mobility_usage

        store = _store(tmp_path)
        for i in range(5):
            store.upsert_object(MigrationObject(
                canonical_id=f"info_device_profile:DP-user{i}",
                provenance=_prov(),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"name": f"DP-user{i}", "product": "Cisco 8845"},
            ))
        findings = detect_extension_mobility_usage(store)
        assert len(findings) == 1
        assert "5" in findings[0].summary
        assert findings[0].category == "rebuild"

    def test_no_findings_when_empty(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_extension_mobility_usage
        store = _store(tmp_path)
        findings = detect_extension_mobility_usage(store)
        assert len(findings) == 0
