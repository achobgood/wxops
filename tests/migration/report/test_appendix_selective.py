"""Tests for selective call handling appendix section."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.report.appendix import generate_appendix
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _make_selective_decision(
    decision_id: str,
    pattern: str,
    user_id: str,
    feature: str,
) -> Decision:
    return Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity="MEDIUM",
        summary=f"selective {pattern} for {user_id}",
        context={
            "selective_call_handling_pattern": pattern,
            "recommended_webex_feature": feature,
            "_affected_objects": [user_id],
            "partitions": ["PT_Test"],
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[user_id],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )


def _seed_selective_decisions(
    store: MigrationStore,
    decisions: list[Decision],
) -> None:
    """Seed all decisions in a single merge to avoid staling earlier entries."""
    store.merge_decisions(
        [decision_to_store_dict(d) for d in decisions],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestSelectiveAppendix:
    def test_section_omitted_when_no_candidates(self, tmp_path):
        store = _store(tmp_path)
        html = generate_appendix(store)
        assert "AB. Selective Call Handling" not in html

    def test_section_rendered_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_selective_decisions(store, [
            _make_selective_decision("d1", "multi_partition_dn", "user:alice", "Selective Forward"),
            _make_selective_decision("d2", "low_membership_partition", "user:bob", "Selective Accept"),
            _make_selective_decision("d3", "naming_convention", "user:carol", "Priority Alert"),
        ])

        html = generate_appendix(store)

        assert "AB. Selective Call Handling" in html
        assert "Selective Forward" in html
        assert "Selective Accept" in html
        assert "Priority Alert" in html
        # Pattern type column
        assert "Multi-Partition DN" in html
        assert "Low-Membership Partition" in html
        assert "Naming Convention" in html
        # Affected user names rendered (without canonical_id prefix)
        assert "alice" in html
        assert "bob" in html
        assert "carol" in html
