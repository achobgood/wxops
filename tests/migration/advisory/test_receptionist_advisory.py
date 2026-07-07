"""Tests for advisory pattern 29: receptionist workflow impact."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.advisory.advisory_patterns import detect_receptionist_workflow_impact


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _receptionist(user_name: str, blf_count: int = 25, score: int = 4) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"receptionist_config:{user_name}",
        provenance=_prov(user_name),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={
            "user_canonical_id": f"user:{user_name}",
            "location_canonical_id": "location:HQ",
            "blf_count": blf_count,
            "has_kem": False,
            "detection_score": score,
            "detection_reasons": [f"{blf_count} BLF entries (20+)"],
        },
    )


def _setup(objects: list) -> MigrationStore:
    store = MigrationStore(":memory:")
    for obj in objects:
        store.upsert_object(obj)
    return store


class TestReceptionistAdvisory:

    def test_fires_when_receptionist_detected(self):
        store = _setup([_receptionist("jdoe@example.com")])
        findings = detect_receptionist_workflow_impact(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "receptionist_workflow_impact"
        assert findings[0].severity == "MEDIUM"
        assert findings[0].category == "rebuild"
        assert "1 receptionist" in findings[0].summary

    def test_does_not_fire_when_no_receptionists(self):
        store = _setup([])
        findings = detect_receptionist_workflow_impact(store)
        assert len(findings) == 0

    def test_multiple_receptionists_counted(self):
        store = _setup([
            _receptionist("jdoe@example.com"),
            _receptionist("front.desk@example.com", blf_count=30, score=5),
        ])
        findings = detect_receptionist_workflow_impact(store)
        assert len(findings) == 1
        assert "2 receptionist" in findings[0].summary

    def test_affected_objects_includes_config_ids(self):
        store = _setup([_receptionist("jdoe@example.com")])
        findings = detect_receptionist_workflow_impact(store)
        assert "receptionist_config:jdoe@example.com" in findings[0].affected_objects
