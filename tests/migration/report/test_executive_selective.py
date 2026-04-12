"""Tests for selective call handling stat in executive summary."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.report.executive import generate_executive_summary
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _make_selective_decision(decision_id: str) -> Decision:
    return Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity="MEDIUM",
        summary="selective",
        context={
            "selective_call_handling_pattern": "multi_partition_dn",
            "_affected_objects": [f"user:{decision_id}"],
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[f"user:{decision_id}"],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )


def _seed_selective_decisions(store: MigrationStore, ids: list[str]) -> None:
    """Seed all decisions in a single merge to avoid staling earlier entries."""
    store.merge_decisions(
        [decision_to_store_dict(_make_selective_decision(d)) for d in ids],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestExecutiveSelective:
    def test_stat_omitted_when_no_candidates(self, tmp_path):
        store = _store(tmp_path)
        html = generate_executive_summary(store, brand="Acme", prepared_by="SE")
        assert "Selective Call Handling" not in html

    def test_stat_rendered_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_selective_decisions(store, ["d1", "d2", "d3"])
        html = generate_executive_summary(store, brand="Acme", prepared_by="SE")

        assert "Selective Call Handling" in html
        assert "3" in html  # 3 candidates
