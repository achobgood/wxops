"""Tests for intercept candidate normalizer and cross-references."""
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.normalizers import normalize_intercept_candidate


class TestNormalizeInterceptCandidate:
    def test_blocked_partition_candidate(self):
        raw = {
            "userid": "jsmith", "dn": "1001", "partition": "Blocked_PT",
            "signal_type": "blocked_partition", "forward_destination": "",
            "voicemail_enabled": False,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:1001:Blocked_PT"
        assert obj.pre_migration_state["signal_type"] == "blocked_partition"
        assert obj.pre_migration_state["userid"] == "jsmith"
        assert obj.pre_migration_state["dn"] == "1001"

    def test_cfa_voicemail_candidate(self):
        raw = {
            "userid": "jdoe", "dn": "2001", "partition": "Internal_PT",
            "signal_type": "cfa_voicemail", "forward_destination": "+14155550000",
            "voicemail_enabled": True,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:2001:Internal_PT"
        assert obj.pre_migration_state["signal_type"] == "cfa_voicemail"
        assert obj.pre_migration_state["forward_destination"] == "+14155550000"
        assert obj.pre_migration_state["voicemail_enabled"] is True

    def test_no_partition(self):
        raw = {
            "userid": "u1", "dn": "3001", "partition": "",
            "signal_type": "blocked_partition", "forward_destination": "",
            "voicemail_enabled": False,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:3001:<None>"

    def test_registry_contains_intercept_candidate(self):
        from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY
        assert "intercept_candidate" in NORMALIZER_REGISTRY

    def test_raw_data_mapping_contains_intercept(self):
        from wxcli.migration.transform.normalizers import RAW_DATA_MAPPING
        matches = [t for t in RAW_DATA_MAPPING if t[1] == "intercept_candidates"]
        assert len(matches) == 1
        assert matches[0] == ("tier4", "intercept_candidates", "intercept_candidate")


def _prov():
    return Provenance(
        source_system="cucm", source_id="test", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


class TestInterceptCrossRefs:
    def test_user_has_intercept_signal_cross_ref(self):
        """CrossReferenceBuilder links users to their intercept candidates."""
        from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

        store = MigrationStore(":memory:")
        store.upsert_object(CanonicalUser(
            canonical_id="user:jsmith", provenance=_prov(),
            status=MigrationStatus.NORMALIZED,
            emails=["jsmith@test.com"], cucm_userid="jsmith",
        ))
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "jsmith", "dn": "1001", "partition": "Blocked_PT",
                "signal_type": "blocked_partition", "forward_destination": "",
                "voicemail_enabled": False,
            },
        ))
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("user:jsmith", "user_has_intercept_signal")
        assert len(refs) == 1
        assert refs[0] == "intercept_candidate:1001:Blocked_PT"

    def test_no_cross_ref_for_unknown_user(self):
        """Intercept candidates for non-existent users don't create cross-refs."""
        from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

        store = MigrationStore(":memory:")
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:9999:OOS_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "ghost_user", "dn": "9999", "partition": "OOS_PT",
                "signal_type": "blocked_partition",
            },
        ))
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("user:ghost_user", "user_has_intercept_signal")
        assert len(refs) == 0
