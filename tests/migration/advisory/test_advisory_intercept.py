"""Tests for call intercept candidates advisory pattern."""
import os
from datetime import datetime, timezone

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="test", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))


class TestDetectCallInterceptCandidates:
    def test_pattern_fires_with_candidates(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "jsmith", "dn": "1001", "partition": "Blocked_PT",
                "signal_type": "blocked_partition",
            },
        ))
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert "1" in findings[0].summary
        assert findings[0].severity == "MEDIUM"
        assert findings[0].category == "out_of_scope"

    def test_pattern_silent_no_candidates(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 0

    def test_pattern_groups_by_signal_type(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u1", "dn": "1001",
                                 "signal_type": "blocked_partition"},
        ))
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1002:OOS_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u2", "dn": "1002",
                                 "signal_type": "blocked_partition"},
        ))
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:2001:Internal_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u3", "dn": "2001",
                                 "signal_type": "cfa_voicemail"},
        ))

        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert "3" in findings[0].summary
        assert "blocked partition" in findings[0].detail.lower()
        assert "cfa" in findings[0].detail.lower()

    def test_pattern_recommendation_accept(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u1", "dn": "1001",
                                 "signal_type": "blocked_partition"},
        ))
        findings = detect_call_intercept_candidates(store)
        assert findings[0].recommendation == "accept"

    def test_pattern_registered(self):
        from wxcli.migration.advisory.advisory_patterns import (
            ALL_ADVISORY_PATTERNS, detect_call_intercept_candidates,
        )
        assert detect_call_intercept_candidates in ALL_ADVISORY_PATTERNS
