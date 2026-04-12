"""Tests for selective call handling advisory pattern."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.advisory.advisory_patterns import (
    ALL_ADVISORY_PATTERNS,
    detect_selective_call_handling_opportunities,
)
from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm", source_id="t", source_name="t",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_decision(
    store: MigrationStore,
    decision_id: str,
    pattern: str,
    severity: str = "MEDIUM",
) -> None:
    decision = Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity=severity,
        summary=f"selective: {pattern}",
        context={
            "selective_call_handling_pattern": pattern,
            "_affected_objects": [f"user:test_{decision_id}"],
            "recommended_webex_feature": "Selective Forward",
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[f"user:test_{decision_id}"],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )
    store.merge_decisions(
        [decision_to_store_dict(decision)],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestSelectiveAdvisoryPattern:
    def test_pattern_silent_no_decisions(self, tmp_path):
        store = _store(tmp_path)
        findings = detect_selective_call_handling_opportunities(store)
        assert findings == []

    def test_pattern_silent_no_selective_context(self, tmp_path):
        store = _store(tmp_path)
        # Create a non-selective FEATURE_APPROXIMATION decision
        decision = Decision(
            decision_id="d1",
            type=DecisionType.FEATURE_APPROXIMATION,
            severity="MEDIUM",
            summary="hunt pilot",
            context={"feature_type": "hunt_group"},
            options=[],
            affected_objects=["hunt_group:HG1"],
            fingerprint="fp1",
            run_id="run1",
        )
        store.merge_decisions(
            [decision_to_store_dict(decision)],
            decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
        )
        findings = detect_selective_call_handling_opportunities(store)
        assert findings == []

    def test_pattern_fires_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_decision(store, "d1", "multi_partition_dn")
        _seed_decision(store, "d2", "multi_partition_dn")
        _seed_decision(store, "d3", "low_membership_partition")
        _seed_decision(store, "d4", "naming_convention")

        findings = detect_selective_call_handling_opportunities(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.pattern_name == "selective_call_handling_opportunities"
        assert f.severity == "MEDIUM"
        assert f.category == "out_of_scope"
        assert "4" in f.summary  # 4 candidates total
        assert "multi_partition_dn" in f.detail or "multi-partition" in f.detail.lower()
        assert "selective forward" in f.detail.lower()

    def test_pattern_groups_by_type(self, tmp_path):
        store = _store(tmp_path)
        _seed_decision(store, "d1", "multi_partition_dn")
        _seed_decision(store, "d2", "low_membership_partition")
        _seed_decision(store, "d3", "low_membership_partition")
        _seed_decision(store, "d4", "naming_convention")

        findings = detect_selective_call_handling_opportunities(store)
        assert len(findings) == 1
        # Detail should reference each pattern type
        detail = findings[0].detail.lower()
        assert "multi" in detail
        assert "low" in detail or "vip" in detail or "membership" in detail
        assert "naming" in detail

    def test_pattern_registered(self):
        assert detect_selective_call_handling_opportunities in ALL_ADVISORY_PATTERNS
