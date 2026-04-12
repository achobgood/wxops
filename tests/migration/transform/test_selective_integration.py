"""End-to-end integration: pipeline detects + reports selective candidates."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline


def _prov(name="t"):
    return Provenance(
        source_system="cucm", source_id="t", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path):
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_vip_environment(store: MigrationStore) -> None:
    # User in HQ with a DN in two partitions, one VIP-named
    user_id = "user:ceo"
    store.upsert_object(
        CanonicalUser(
            canonical_id=user_id,
            provenance=_prov("ceo"),
            status=MigrationStatus.ANALYZED,
            cucm_userid="ceo",
            location_id="loc:hq",
            extension="1000",
        )
    )
    for pt in ("PT_VIP_Direct", "PT_Standard"):
        store.upsert_object(
            MigrationObject(
                canonical_id=f"partition:{pt}",
                provenance=_prov(pt),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"partition_name": pt},
            )
        )
        dn_id = f"dn:1000:{pt}"
        # DN object must exist before cross_refs can reference it (FK constraint)
        store.upsert_object(
            MigrationObject(
                canonical_id=dn_id,
                provenance=_prov(f"1000-{pt}"),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"dn": "1000", "partition": pt},
            )
        )
        store.add_cross_ref(dn_id, f"partition:{pt}", "dn_in_partition")
        store.add_cross_ref(user_id, dn_id, "user_has_primary_dn")
    for css, partitions in (
        ("CSS_Internal", ["PT_Standard"]),
        ("CSS_VIP", ["PT_VIP_Direct"]),
    ):
        css_id = f"css:{css}"
        store.upsert_object(
            MigrationObject(
                canonical_id=css_id,
                provenance=_prov(css),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"css_name": css, "partitions": []},
            )
        )
        store.add_cross_ref(user_id, css_id, "user_has_css")
        for pt in partitions:
            store.add_cross_ref(css_id, f"partition:{pt}", "css_contains_partition")


class TestSelectiveIntegration:
    def test_full_pipeline_with_vip_pattern(self, tmp_path):
        store = _store(tmp_path)
        _seed_vip_environment(store)

        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        # The selective analyzer ran
        assert "selective_call_handling" in result.stats
        assert result.stats["selective_call_handling"] >= 1

        # And the advisory pattern produced an ARCHITECTURE_ADVISORY decision
        all_decisions = store.get_all_decisions()
        sch_advisory = [
            d for d in all_decisions
            if d.get("type") == "ARCHITECTURE_ADVISORY"
            and (d.get("context", {}) or {}).get("pattern_name")
            == "selective_call_handling_opportunities"
        ]
        assert len(sch_advisory) == 1

    def test_full_pipeline_clean_environment_no_advisory(self, tmp_path):
        store = _store(tmp_path)
        # Empty store: nothing for the analyzer to find
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        all_decisions = store.get_all_decisions()
        sch = [
            d for d in all_decisions
            if (d.get("context", {}) or {}).get("selective_call_handling_pattern")
        ]
        assert sch == []

    def test_pipeline_does_not_break_existing_decisions(self, tmp_path):
        """Adding the new analyzer must not break any other analyzer."""
        store = _store(tmp_path)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        # All analyzers ran without raising
        for name, count in result.stats.items():
            assert count >= 0, f"Analyzer {name} failed (count={count})"
